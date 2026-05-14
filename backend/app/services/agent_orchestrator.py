# backend/app/services/agent_orchestrator.py

import logging
import json
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field

from app.services.groq_service import groq_service
from app.services.memory_service import memory_service
from app.utils.prompt_builder import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

VOICE_SUFFIX = "\n\nIMPORTANT: This response will be spoken aloud. Keep it under 3 sentences unless detail is explicitly requested. No formatting symbols."


@dataclass
class TurnContext:
    user_id: str
    conversation_id: Optional[str] = None
    history: list[dict] = field(default_factory=list)
    is_voice: bool = False
    fast_mode: bool = False


class AgentOrchestrator:

    def _build_system_prompt(self, memories: list[str], is_voice: bool) -> str:
        prompt = SYSTEM_PROMPT
        if memories:
            memory_block = "\n".join(f"- {m}" for m in memories)
            prompt += f"\n\nWhat you remember about this user:\n{memory_block}"
        if is_voice:
            prompt += VOICE_SUFFIX
        return prompt

    def _build_messages(self, context: TurnContext, user_message: str) -> list[dict]:
        messages = list(context.history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def respond(
        self,
        context: TurnContext,
        user_message: str,
    ) -> str:
        memories = await memory_service.recall(
            user_id=context.user_id,
            query=user_message,
        )
        system_prompt = self._build_system_prompt(memories, context.is_voice)
        messages = self._build_messages(context, user_message)

        response = await groq_service.chat(
            messages=messages,
            system_prompt=system_prompt,
            fast=context.fast_mode,
        )
        return response

    async def stream_response(
        self,
        context: TurnContext,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        memories = await memory_service.recall(
            user_id=context.user_id,
            query=user_message,
        )
        system_prompt = self._build_system_prompt(memories, context.is_voice)
        messages = self._build_messages(context, user_message)

        async for chunk in groq_service.stream(
            messages=messages,
            system_prompt=system_prompt,
            fast=context.fast_mode,
        ):
            yield chunk

    async def process_turn(
        self,
        context: TurnContext,
        user_message: str,
        store_memory: bool = False,
    ) -> str:
        response = await self.respond(context, user_message)

        if store_memory:
            combined = f"User said: {user_message}\nJarvis replied: {response}"
            await memory_service.extract_and_store(
                user_id=context.user_id,
                text=combined,
                conversation_id=context.conversation_id,
            )

        return response


agent_orchestrator = AgentOrchestrator()