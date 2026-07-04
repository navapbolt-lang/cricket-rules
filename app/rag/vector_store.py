"""Qdrant vector database operations."""

import uuid
from app.config import settings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from app.models.types import LawChunk


COLLECTION_NAME = "icc_laws"
VECTOR_SIZE = 768  # Gemini text-embedding-004 dimension


class VectorStore:
    """Qdrant vector store wrapper."""

    def __init__(self):
        self.client = None
        self._initialized = False

    def _ensure_connected(self):
        """Connect to Qdrant on first use."""
        if self._initialized:
            return
        from app.config import settings

        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
        self._ensure_collection()
        self._initialized = True

    def _ensure_collection(self):
        """Create Qdrant collection and create payload indexes if it does not exist."""
        if not self.client.collection_exists(COLLECTION_NAME):
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            # Create payload index for gender filter
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="metadata.gender",
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def upsert(self, chunks: list[LawChunk]) -> int:
        """Upsert chunks with embeddings and metadata."""
        self._ensure_connected()
        points = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            points.append(
                PointStruct(
                    id=chunk.id,
                    vector=chunk.embedding,
                    payload={
                        "text": chunk.text,
                        "metadata": chunk.metadata.model_dump(),
                    },
                )
            )
        if points:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        return len(points)

    def delete_by_law(self, law_number: str):
        """Remove old version of a law."""
        self._ensure_connected()
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.law_number", match=MatchValue(value=law_number)
                    )
                ]
            ),
        )

    def delete_by_year(self, authority: str, year: int):
        """Remove old chunks by authority and year."""
        self._ensure_connected()
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="metadata.authority", match=MatchValue(value=authority)
                    ),
                    FieldCondition(key="metadata.year", match=MatchValue(value=year)),
                ]
            ),
        )

    def count(self) -> int:
        """Return chunk count in the collection."""
        self._ensure_connected()
        try:
            return self.client.count(COLLECTION_NAME).count
        except Exception:
            return 0

    def health(self) -> bool:
        """Check connection health."""
        self._ensure_connected()
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
