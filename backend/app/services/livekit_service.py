# backend/app/services/livekit_service.py

import os
import logging
from livekit.api import LiveKitAPI, AccessToken, VideoGrants

logger = logging.getLogger(__name__)


class LiveKitService:
    def __init__(self):
        self.url = os.environ["LIVEKIT_URL"]
        self.api_key = os.environ["LIVEKIT_API_KEY"]
        self.api_secret = os.environ["LIVEKIT_API_SECRET"]

    def create_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str = "",
        ttl_seconds: int = 3600,
    ) -> str:
        token = (
            AccessToken(self.api_key, self.api_secret)
            .with_identity(participant_identity)
            .with_name(participant_name or participant_identity)
            .with_ttl(ttl_seconds)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
        )
        return token.to_jwt()

    def get_client(self) -> LiveKitAPI:
        return LiveKitAPI(
            url=self.url,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

    async def create_room(self, room_name: str, empty_timeout: int = 300) -> dict:
        async with self.get_client() as client:
            room = await client.room.create_room(
                name=room_name,
                empty_timeout=empty_timeout,
            )
            return {"name": room.name, "sid": room.sid}

    async def delete_room(self, room_name: str) -> None:
        async with self.get_client() as client:
            await client.room.delete_room(room=room_name)

    async def list_participants(self, room_name: str) -> list[dict]:
        async with self.get_client() as client:
            response = await client.room.list_participants(room=room_name)
            return [
                {"identity": p.identity, "name": p.name, "sid": p.sid}
                for p in response.participants
            ]


livekit_service = LiveKitService()