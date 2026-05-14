# backend/app/tasks/memory_tasks.py

import asyncio
import json
import logging
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Memory, Message, Conversation
from app.services.memory_service import MemoryService, EXTRACT_SYSTEM_PROMPT
from app.services.groq_service import GroqService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

memory_service = MemoryService()
groq_service   = GroqService()
qdrant_service = QdrantService()


# ── extract and store memories from a conversation turn ───────────────────────

@shared_task(
    bind=True,
    name="tasks.extract_and_store_memories",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def extract_and_store_memories(self, user_id: str, conversation_id: str, message_id: str):
    """
    Triggered after each assistant reply.
    Extracts facts/preferences from the latest message pair and upserts
    them into both Postgres (Memory table) and Qdrant (vector search).
    """
    try:
        message = db.session.get(Message, message_id)
        if not message:
            logger.warning("extract_and_store_memories: message %s not found", message_id)
            return {"status": "skipped", "reason": "message not found"}

        # Grab last 6 messages for context (3 turns)
        recent = (
            Message.query
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.desc())
            .limit(6)
            .all()
        )
        recent_text = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in reversed(recent)
        )

        # Ask LLM to extract atomic facts
        try:
            raw = asyncio.run(groq_service.get_json(
                messages=[{"role": "user", "content": recent_text}],
                system_prompt=EXTRACT_SYSTEM_PROMPT,
            ))
            data = json.loads(raw)
            facts = data.get("memories", [])
            default_importance = float(data.get("importance", 3))
        except Exception:
            logger.warning("Failed to extract facts from LLM")
            facts = []
            default_importance = 3.0

        if not facts:
            return {"status": "ok", "extracted": 0}

        stored = 0
        for fact_item in facts:
            # facts can be plain strings or dicts with content/type/importance
            if isinstance(fact_item, str):
                content = fact_item.strip()
                mem_type = "fact"
                importance = default_importance
            else:
                content   = str(fact_item.get("content", "")).strip()
                mem_type  = fact_item.get("type", "fact")
                importance = float(fact_item.get("importance", default_importance))

            if not content:
                continue

            # Upsert in Postgres
            existing = Memory.query.filter_by(
                user_id=user_id, content=content
            ).first()

            if existing:
                existing.importance  = max(existing.importance, importance)
                existing.recall_count += 1
            else:
                mem = Memory(
                    user_id=user_id,
                    content=content,
                    memory_type=mem_type,
                    importance=importance,
                    source_conversation_id=conversation_id,
                )
                db.session.add(mem)
                db.session.flush()          # get mem.id before Qdrant upsert
                existing = mem

            # Upsert embedding in Qdrant
            vector = memory_service._get_embedding(content)
            asyncio.run(qdrant_service.upsert(
                vector=vector,
                payload={
                    "user_id": user_id,
                    "content": content,
                    "type": mem_type,
                    "importance": importance,
                    "conversation_id": conversation_id,
                },
                point_id=str(existing.id),
            ))
            stored += 1

        db.session.commit()
        logger.info("extract_and_store_memories: stored %d facts for user %s", stored, user_id)
        return {"status": "ok", "extracted": stored}

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("extract_and_store_memories DB error: %s", exc)
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error("extract_and_store_memories error: %s", exc)
        raise self.retry(exc=exc)


# ── prune low-importance / stale memories ────────────────────────────────────

@shared_task(
    bind=True,
    name="tasks.prune_stale_memories",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def prune_stale_memories(self, user_id: str, max_memories: int = 500):
    """
    Keeps the Memory table lean. Deletes the lowest-scoring memories
    once a user exceeds max_memories, scoring by importance × recency.
    Also removes their Qdrant vectors.
    """
    try:
        total = Memory.query.filter_by(user_id=user_id).count()
        if total <= max_memories:
            return {"status": "ok", "pruned": 0, "total": total}

        to_delete_count = total - max_memories

        # Score = importance (Postgres column); tie-break by last_recalled_at asc
        candidates = (
            Memory.query
            .filter_by(user_id=user_id)
            .order_by(Memory.importance.asc(), Memory.last_recalled_at.asc())
            .limit(to_delete_count)
            .all()
        )

        pruned_ids = []
        for mem in candidates:
            pruned_ids.append(str(mem.id))
            db.session.delete(mem)

        db.session.commit()

        # Remove from Qdrant
        for pid in pruned_ids:
            try:
                asyncio.run(qdrant_service.delete(point_id=pid))
            except Exception:
                logger.warning("Failed to delete Qdrant point %s", pid)

        logger.info("prune_stale_memories: pruned %d memories for user %s", len(pruned_ids), user_id)
        return {"status": "ok", "pruned": len(pruned_ids), "total": total - len(pruned_ids)}

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("prune_stale_memories DB error: %s", exc)
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error("prune_stale_memories error: %s", exc)
        raise self.retry(exc=exc)


# ── rebuild Qdrant vectors for a user (recovery / re-index) ──────────────────

@shared_task(
    bind=True,
    name="tasks.rebuild_user_vectors",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def rebuild_user_vectors(self, user_id: str):
    """
    Re-embeds and re-upserts every Memory row for a user.
    Use after a Qdrant collection reset or data migration.
    """
    try:
        memories = Memory.query.filter_by(user_id=user_id).all()
        if not memories:
            return {"status": "ok", "rebuilt": 0}

        rebuilt = 0
        for mem in memories:
            vector = memory_service._get_embedding(mem.content)
            asyncio.run(qdrant_service.upsert(
                vector=vector,
                payload={
                    "user_id": user_id,
                    "content": mem.content,
                    "type": mem.memory_type,
                    "importance": mem.importance,
                    "conversation_id": str(mem.source_conversation_id) if mem.source_conversation_id else None,
                },
                point_id=str(mem.id),
            ))
            rebuilt += 1

        logger.info("rebuild_user_vectors: rebuilt %d vectors for user %s", rebuilt, user_id)
        return {"status": "ok", "rebuilt": rebuilt}

    except Exception as exc:
        logger.error("rebuild_user_vectors error: %s", exc)
        raise self.retry(exc=exc)