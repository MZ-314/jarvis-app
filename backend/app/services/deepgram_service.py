# backend/app/services/deepgram_service.py

import os
import logging
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    PrerecordedOptions,
    FileSource,
)

logger = logging.getLogger(__name__)


class DeepgramService:
    LiveTranscriptionEvents = LiveTranscriptionEvents

    def __init__(self):
        self.client = DeepgramClient(
            api_key=os.environ["DEEPGRAM_API_KEY"],
            config=DeepgramClientOptions(verbose=False),
        )
        self.model = "nova-2"
        self.language = "en-US"

    def get_live_options(self) -> LiveOptions:
        return LiveOptions(
            model=self.model,
            language=self.language,
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            punctuate=True,
            interim_results=True,
            endpointing=300,
            smart_format=True,
            vad_events=True,
        )

    def create_live_connection(self):
        return self.client.listen.asyncwebsocket.v("1")

    async def transcribe_file(self, audio_bytes: bytes, mimetype: str = "audio/wav") -> str:
        try:
            source: FileSource = {"buffer": audio_bytes, "mimetype": mimetype}
            options = PrerecordedOptions(
                model=self.model,
                language=self.language,
                punctuate=True,
                smart_format=True,
            )
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                source, options
            )
            return response.results.channels[0].alternatives[0].transcript or ""
        except Exception:
            logger.warning("Empty or failed transcript from Deepgram")
            return ""


deepgram_service = DeepgramService()