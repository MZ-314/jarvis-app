from typing import Optional
from app.models.memory import Memory


SYSTEM_PROMPT = """You are Jarvis, an AI Engineering Assistant. You help software engineers with coding, architecture, debugging, system design, and technical problem-solving.

You are precise, concise, and practical. You prefer code over lengthy explanation. When asked a question, you get to the point immediately.

Voice is your primary interface — keep responses conversational and avoid markdown unless the user explicitly asks for code or structured output.

You remember context from previous conversations and use it to give personalized, relevant answers."""


def build_system_prompt(
    user_name: Optional[str] = None,
    memories: Optional[list[Memory]] = None,
    extra_context: Optional[str] = None,
) -> str:
    parts = [SYSTEM_PROMPT]

    if user_name:
        parts.append(f"\nThe user's name is {user_name}.")

    if memories:
        memory_lines = "\n".join(f"- {m.content}" for m in memories)
        parts.append(f"\nWhat you remember about this user:\n{memory_lines}")

    if extra_context:
        parts.append(f"\nAdditional context:\n{extra_context}")

    return "\n".join(parts)


def build_messages(
    conversation_history: list[dict],
    current_message: str,
    system_prompt: str,
) -> list[dict]:
    messages = []

    for turn in conversation_history:
        role = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": current_message})

    return messages


def build_memory_extraction_prompt(conversation_text: str) -> str:
    return f"""Extract factual, reusable information about the user from this conversation.
Only extract things that would be useful to remember long-term (skills, preferences, ongoing projects, tools they use, etc.).
Return a JSON array of strings. Each string is one memory fact. Return [] if nothing is worth remembering.
Return only valid JSON — no explanation, no markdown.

Conversation:
{conversation_text}"""


def build_summary_prompt(conversation_text: str) -> str:
    return f"""Summarize this conversation in 2-3 sentences from the assistant's perspective.
Focus on what was discussed, what problems were solved, and any decisions made.
Be concise and factual.

Conversation:
{conversation_text}"""


def format_conversation_for_prompt(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)