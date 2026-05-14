# backend/app/tasks/summary_tasks.py

import asyncio
import logging
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Conversation, Message
from app.services.groq_service import GroqService

logger = logging.getLogger(__name__)

groq_service = GroqService()

# ── constants ─────────────────────────────────────────────────────────────────

SUMMARY_TRIGGER_COUNT = 20      # summarise after every N messages
MAX_MESSAGES_FOR_SUMMARY = 40   # cap how many messages we send to LLM at once


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_transcript(messages: list[Message]) -> str:
    return "\n".join(
        f"{m.role.upper()}: {m.content}" for m in messages
    )


def _summarise_via_groq(transcript: str, existing_summary: str | None) -> str:
    context = ""
    if existing_summary:
        context = f"Previous summary:\n{existing_summary}\n\n"

    prompt = (
        f"{context}"
        f"Conversation so far:\n{transcript}\n\n"
        "Write a concise factual summary (max 200 words) of this conversation. "
        "Focus on decisions made, problems solved, and key information exchanged. "
        "Use third-person, past tense. Return only the summary text."
    )

    response = asyncio.run(groq_service.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a precise summarisation assistant. Output only the summary.",
        fast=True,
    ))
    return response.strip()


# ── task: summarise a conversation ───────────────────────────────────────────

@shared_task(
    bind=True,
    name="tasks.summarise_conversation",
    max_retries=3,
    default_retry_delay=45,
    acks_late=True,
)
def summarise_conversation(self, conversation_id: str):
    """
    Triggered when a conversation reaches SUMMARY_TRIGGER_COUNT messages,
    or manually via the memory blueprint.
    Generates/updates the conversation summary and stores it on the
    Conversation row so the LLM always has a compact context header.
    """
    try:
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            logger.warning("summarise_conversation: conversation %s not found", conversation_id)
            return {"status": "skipped", "reason": "conversation not found"}

        messages = (
            Message.query
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.asc())
            .limit(MAX_MESSAGES_FOR_SUMMARY)
            .all()
        )

        if len(messages) < 4:
            return {"status": "skipped", "reason": "too few messages"}

        transcript = _build_transcript(messages)
        new_summary = _summarise_via_groq(transcript, conversation.summary)

        conversation.summary = new_summary
        conversation.summary_updated_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info("summarise_conversation: updated summary for %s", conversation_id)
        return {"status": "ok", "conversation_id": conversation_id, "length": len(new_summary)}

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("summarise_conversation DB error: %s", exc)
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error("summarise_conversation error: %s", exc)
        raise self.retry(exc=exc)


# ── task: auto-title a conversation ──────────────────────────────────────────

@shared_task(
    bind=True,
    name="tasks.auto_title_conversation",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def auto_title_conversation(self, conversation_id: str):
    """
    Generates a short title for the conversation from its first few messages.
    Triggered once after the 3rd message in a new conversation.
    """
    try:
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            return {"status": "skipped", "reason": "conversation not found"}

        # Don't overwrite a manually set title
        if conversation.title and not conversation.title.startswith("New conversation"):
            return {"status": "skipped", "reason": "title already set"}

        first_messages = (
            Message.query
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.asc())
            .limit(6)
            .all()
        )

        if not first_messages:
            return {"status": "skipped", "reason": "no messages"}

        transcript = _build_transcript(first_messages)

        prompt = (
            f"Conversation:\n{transcript}\n\n"
            "Generate a short title (max 6 words) for this conversation. "
            "Be specific, not generic. Return only the title, no punctuation."
        )

        title = asyncio.run(groq_service.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You generate concise conversation titles. Output only the title.",
            fast=True,
        )).strip().strip('"').strip("'")

        conversation.title = title[:120]        # column max length guard
        db.session.commit()

        logger.info("auto_title_conversation: titled '%s' for %s", title, conversation_id)
        return {"status": "ok", "title": title}

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("auto_title_conversation DB error: %s", exc)
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.error("auto_title_conversation error: %s", exc)
        raise self.retry(exc=exc)


# ── task: bulk summarise all stale conversations for a user ──────────────────

@shared_task(
    bind=True,
    name="tasks.bulk_summarise_user_conversations",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def bulk_summarise_user_conversations(self, user_id: str):
    """
    Summarises all conversations for a user that have >= SUMMARY_TRIGGER_COUNT
    messages but no summary yet. Useful for backfill after migrations.
    """
    try:
        conversations = (
            Conversation.query
            .filter_by(user_id=user_id)
            .filter(Conversation.summary.is_(None))
            .all()
        )

        queued = 0
        for conv in conversations:
            count = Message.query.filter_by(conversation_id=conv.id).count()
            if count >= SUMMARY_TRIGGER_COUNT:
                summarise_conversation.delay(str(conv.id))
                queued += 1

        logger.info(
            "bulk_summarise_user_conversations: queued %d jobs for user %s",
            queued, user_id
        )
        return {"status": "ok", "queued": queued}

    except Exception as exc:
        logger.error("bulk_summarise_user_conversations error: %s", exc)
        raise self.retry(exc=exc)