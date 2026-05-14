# backend/app/services/cartesia_service.py

import os
import logging
from typing import AsyncGenerator, Optional
import httpx

logger = logging.getLogger(__name__)

CARTESIA_API_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_STREAM_URL = "https://api.cartesia.ai/tts/sse"
CARTESIA_API_VERSION = "2024-06-10"


class CartesiaService:
    def __init__(self):
        self.api_key = os.environ["CARTESIA_API_KEY"]
        self.voice_id = "a0e99841-438c-4a64-b679-ae501e7d6091"  # Barbarian — deep, clear
        self.model_id = "sonic-english"
        self.output_format = {
            "container": "raw",
            "encoding": "pcm_f32le",
            "sample_rate": 44100,
        }
        self.headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": CARTESIA_API_VERSION,
            "Content-Type": "application/json",
        }

    def _build_payload(self, text: str) -> dict:
        return {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": self.voice_id,
            },
            "output_format": self.output_format,
        }

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                CARTESIA_API_URL,
                headers=self.headers,
                json=self._build_payload(text),
            )
            response.raise_for_status()
            return response.content

    async def stream(self, text: str) -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                CARTESIA_STREAM_URL,
                headers={**self.headers, "Accept": "text/event-stream"},
                json=self._build_payload(text),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        import json
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            event = json.loads(raw)
                            chunk = event.get("data")
                            if chunk:
                                import base64
                                yield base64.b64decode(chunk)
                        except (json.JSONDecodeError, KeyError):
                            continue


cartesia_service = CartesiaService()