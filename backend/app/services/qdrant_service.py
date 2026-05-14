# backend/app/services/qdrant_service.py

import os
import logging
import uuid
from typing import Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "jarvis_memory"
VECTOR_SIZE = 1536  # text-embedding-3-small compatible; swap if using a different embedder


class QdrantService:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ["QDRANT_API_KEY"],
        )
        self.collection = COLLECTION_NAME
        self.vector_size = VECTOR_SIZE
        self._collection_ready = False

    async def _ensure_ready(self) -> None:
        if not self._collection_ready:
            await self.ensure_collection()
            self._collection_ready = True

    async def ensure_collection(self) -> None:
        existing = await self.client.get_collections()
        names = [c.name for c in existing.collections]
        if self.collection not in names:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {self.collection}")

    async def upsert(
        self,
        vector: list[float],
        payload: dict,
        point_id: Optional[str] = None,
    ) -> str:
        await self._ensure_ready()
        pid = point_id or str(uuid.uuid4())
        await self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=pid, vector=vector, payload=payload)],
        )
        return pid

    async def search(
        self,
        vector: list[float],
        user_id: str,
        top_k: int = 5,
        score_threshold: float = 0.75,
    ) -> list[dict]:
        await self._ensure_ready()
        results = await self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            ),
            search_params=SearchParams(exact=False),
        )
        return [
            {"id": str(r.id), "score": r.score, "payload": r.payload}
            for r in results
        ]

    async def delete(self, point_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )

    async def delete_by_user(self, user_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            ),
        )


qdrant_service = QdrantService()