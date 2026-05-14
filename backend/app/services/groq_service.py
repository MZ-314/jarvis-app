# backend/app/services/groq_service.py

import os
import logging
from typing import AsyncGenerator, Optional
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        self.default_model = "llama-3.3-70b-versatile"
        self.fast_model = "llama-3.1-8b-instant"
        self.max_tokens = 1024
        self.temperature = 0.7

    async def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        system_prompt: Optional[str] = None,
        stream: bool = False,
        fast: bool = False,
    ) -> str:
        model = self.fast_model if fast else self.default_model
        full_messages: list[ChatCompletionMessageParam] = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if stream:
            return await self._stream_to_string(full_messages, model)

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[ChatCompletionMessageParam],
        system_prompt: Optional[str] = None,
        fast: bool = False,
    ) -> AsyncGenerator[str, None]:
        model = self.fast_model if fast else self.default_model
        full_messages: list[ChatCompletionMessageParam] = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def _stream_to_string(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str,
    ) -> str:
        result = []
        async for chunk in await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                result.append(delta)
        return "".join(result)

    async def get_json(
        self,
        messages: list[ChatCompletionMessageParam],
        system_prompt: Optional[str] = None,
    ) -> str:
        model = self.default_model
        full_messages: list[ChatCompletionMessageParam] = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=self.max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"


groq_service = GroqService()