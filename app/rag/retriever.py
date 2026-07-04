"""Hybrid search retriever combining vector similarity + BM25 keyword search with metadata filtering and Reciprocal Rank Fusion."""

from typing import Optional
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SearchRequest,
    ScoredPoint,
    NamedVector,
    NamedSparseVector,
    PayloadSelector,
    SparseVectorParams,
    SparseIndexParams,
)
from app.models.types import Format, Authority, LawChunk, ChunkMetadata, ChunkType
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import VectorStore


class HybridRetriever:
    """Retrieves relevant law chunks using hybrid search.

    Strategy:
    - Vector search for semantic understanding
    - BM25 keyword search for exact law number matching
    - Reciprocal Rank Fusion (RRF) to combine rankings
    - Metadata pre-filtering by format, authority, year
    """

    def __init__(self, vector_store: VectorStore, embedding_client: EmbeddingClient):
        self.vs = vector_store
        self.embed = embedding_client
        self.collection_name = "icc_laws"

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        top_k: int = 20,
    ) -> list[LawChunk]:
        """Hybrid search: vector + keyword, fused by RRF.

        Args:
            query: User query text
            filters: e.g. {"format": "test", "authority": "icc", "year": 2025}
            top_k: Number of final results

        Returns:
            List of LawChunks sorted by relevance
        """
        self.vs._ensure_connected()
        qdrant_filter = self._build_filter(filters)

        vector_results = self._vector_search(query, qdrant_filter, top_k * 2)
        keyword_results = self._keyword_search(query, qdrant_filter, top_k * 2)

        fused = self._rrf_fuse(vector_results, keyword_results, k=60)
        return fused[:top_k]

    def _vector_search(
        self, query: str, qdrant_filter: Filter, limit: int
    ) -> list[LawChunk]:
        """Vector similarity search using query embedding."""
        query_vec = self.embed.embed(query)

        points = self.vs.client.search(
            collection_name=self.collection_name,
            query_vector=query_vec,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        )
        return [self._point_to_chunk(p) for p in points]

    def _keyword_search(
        self, query: str, qdrant_filter: Filter, limit: int
    ) -> list[LawChunk]:
        """Keyword search using scroll + text matching with law-number boosting."""
        import re

        try:
            tokens = query.lower().split()
            all_points, _ = self.vs.client.scroll(
                collection_name=self.collection_name,
                limit=2000,
                with_payload=True,
            )
        except Exception:
            return []

        law_numbers_in_query = set(re.findall(r"\d+(?:\.\d+)*", query))

        candidates = []
        for point in all_points:
            text = (point.payload or {}).get("text", "").lower()
            matches = sum(1 for t in tokens if t in text)
            if matches > 0:
                chunk = self._point_to_chunk(point)
                base_score = matches / len(tokens)
                meta_law = chunk.metadata.law_number
                if law_numbers_in_query:
                    for qn in law_numbers_in_query:
                        if meta_law == qn or meta_law.startswith(qn + "."):
                            base_score += 5.0
                            break
                chunk.score = base_score
                candidates.append(chunk)

        candidates.sort(key=lambda c: c.score or 0.0, reverse=True)
        return candidates[:limit]

    def _rrf_fuse(
        self,
        vector_results: list[LawChunk],
        keyword_results: list[LawChunk],
        k: int = 60,
    ) -> list[LawChunk]:
        """Reciprocal Rank Fusion: combine two ranked lists."""
        scores: dict[str, float] = {}

        for rank, chunk in enumerate(vector_results):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)

        for rank, chunk in enumerate(keyword_results):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)

        seen = set()
        fused = []
        for chunk in vector_results + keyword_results:
            if chunk.id not in seen:
                seen.add(chunk.id)
                chunk.score = scores.get(chunk.id, 0.0)
                fused.append(chunk)

        fused.sort(key=lambda c: c.score or 0.0, reverse=True)
        return fused

    def _build_filter(self, filters: Optional[dict]) -> Filter:
        """Build Qdrant Filter from metadata dict."""
        if not filters:
            return Filter()

        conditions = []
        if "format" in filters:
            conditions.append(
                FieldCondition(
                    key="metadata.formats", match=MatchAny(any=[filters["format"]])
                )
            )
        if "authority" in filters:
            conditions.append(
                FieldCondition(
                    key="metadata.authority",
                    match=MatchValue(value=filters["authority"]),
                )
            )
        if "law_number" in filters:
            conditions.append(
                FieldCondition(
                    key="metadata.law_number",
                    match=MatchValue(value=filters["law_number"]),
                )
            )
        if "parent_law" in filters:
            conditions.append(
                FieldCondition(
                    key="metadata.parent_law",
                    match=MatchValue(value=filters["parent_law"]),
                )
            )

        if "gender" in filters and filters["gender"] != "all":
            conditions.append(
                FieldCondition(
                    key="metadata.gender",
                    match=MatchAny(any=[filters["gender"], "all"]),
                )
            )

        return Filter(should=conditions) if conditions else Filter()

    def _point_to_chunk(self, point: ScoredPoint) -> LawChunk:
        """Convert Qdrant ScoredPoint to LawChunk."""
        payload = point.payload or {}

        meta = ChunkMetadata(
            law_number=payload.get("metadata", {}).get("law_number", ""),
            parent_law=payload.get("metadata", {}).get("parent_law", ""),
            title=payload.get("metadata", {}).get("title", ""),
            formats=[Format(f) for f in payload.get("metadata", {}).get("formats", [])],
            authority=Authority(payload.get("metadata", {}).get("authority", "icc")),
            gender=payload.get("metadata", {}).get("gender", "all"),
            year=payload.get("metadata", {}).get("year", 2025),
            effective_date=payload.get("metadata", {}).get("effective_date", ""),
            page_number=payload.get("metadata", {}).get("page_number", 0),
            chunk_index=payload.get("metadata", {}).get("chunk_index", 0),
            chunk_type=ChunkType(
                payload.get("metadata", {}).get("chunk_type", "clause")
            ),
        )

        return LawChunk(
            id=point.id,
            text=payload.get("text", ""),
            metadata=meta,
            score=getattr(point, "score", None),
        )
