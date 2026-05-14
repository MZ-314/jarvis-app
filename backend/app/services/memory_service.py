# backend/app/services/memory_service.py

import logging
import json
import hashlib
from typing import Optional
from datetime import datetime, timezone

from app.services.qdrant_service import qdrant_service
from app.services.groq_service import groq_service
from app.models.memory import Memory
from app.extensions import db

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = """You are a memory extraction assistant for an AI engineering assistant called Jarvis.
Given a conversation message or summary, extract important facts, preferences, or context worth remembering about the user.
Return a JSON object with:
- "memories": list of short strings, each a distinct memory fact
- "importance": integer 1-5 (5 = most important)
Return ONLY valid JSON."""


class MemoryService:

    def _get_embedding(self, text: str) -> list[float]:
        """Simple deterministic embedding using hash. Replace with real embedding model later."""
        vector = [0.0] * 1536
        digest = hashlib.sha256(text.encode()).digest()
        for i, byte in enumerate(digest):
            vector[i % 1536] += (byte - 128) / 128.0
        magnitude = sum(x ** 2 for x in vector) ** 0.5 or 1.0
        return [x / magnitude for x in vector]

    async def extract_and_store(
        self,
        user_id: str,
        text: str,
        conversation_id: Optional[str] = None,
    ) -> list[str]:
        try:
            raw = await groq_service.get_json(
                messages=[{"role": "user", "content": text}],
                system_prompt=EXTRACT_SYSTEM_PROMPT,
            )
            data = json.loads(raw)
            facts: list[str] = data.get("memories", [])
            importance: int = int(data.get("importance", 3))
        except Exception:
            logger.warning("Failed to extract memories")
            return []

        stored_ids = []
        for fact in facts:
            vector = self._get_embedding(fact)
            payload = {
                "user_id": user_id,
                "content": fact,
                "importance": importance,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                point_id = await qdrant_service.upsert(vector=vector, payload=payload)
                memory = Memory(
                    user_id=user_id,
                    content=fact,
                    importance=importance,
                    source_conversation_id=conversation_id,
                    qdrant_id=point_id,
                )
                db.session.add(memory)
                stored_ids.append(point_id)
            except Exception:
                logger.warning(f"Failed to store memory: {fact}")

        db.session.commit()
        return stored_ids

    async def recall(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[str]:
        try:
            vector = self._get_embedding(query)
            results = await qdrant_service.search(
                vector=vector,
                user_id=user_id,
                top_k=top_k,
            )
            return [r["payload"]["content"] for r in results if r.get("payload")]
        except Exception:
            logger.exception("Memory recall failed, returning empty")
            return []

    async def forget(self, user_id: str, memory_id: str) -> bool:
        try:
            await qdrant_service.delete(point_id=memory_id)
            memory = db.session.get(Memory, memory_id)
            if memory and str(memory.user_id) == user_id:
                db.session.delete(memory)
                db.session.commit()
                return True
        except Exception:
            logger.warning(f"Failed to forget memory {memory_id}")
        return False

    async def forget_all(self, user_id: str) -> None:
        try:
            await qdrant_service.delete_by_user(user_id=user_id)
            Memory.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        except Exception:
            logger.warning("Failed to forget all memories")


memory_service = MemoryService()