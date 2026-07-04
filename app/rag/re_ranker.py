"""Cross-encoder re-ranker using BGE model for improved retrieval precision."""

from typing import Optional
from sentence_transformers import CrossEncoder
from app.models.types import LawChunk
from app.config import settings


class ReRanker:
    """Cross-encoder re-ranker to improve retrieval precision.

    Takes top-20 from hybrid search, re-ranks by cross-encoder score,
    returns top-5 most relevant chunks. Uses BGE-reranker-v2-m3
    which runs efficiently on CPU.
    """

    _instance: Optional[CrossEncoder] = None

    def __init__(self):
        self._model = None

    def rerank(self, query: str, chunks: list[LawChunk], top_k: int = 5) -> list[LawChunk]:
        """Re-rank chunks by cross-encoder relevance score.

        Args:
            query: Original user query
            chunks: Retrieved chunks (top-20 from hybrid search)
            top_k: Number of chunks to return

        Returns:
            Top-k chunks sorted by relevance, with updated scores
        """
        if not chunks:
            return []

        model = self._load_model()

        pairs = [(query, c.text) for c in chunks]
        scores = model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk.score = float(score)

        chunks.sort(key=lambda c: c.score or 0.0, reverse=True)
        return chunks[:top_k]

    def _load_model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model on first use."""
        if self._model is None:
            self._model = CrossEncoder(
                settings.reranker_model,
                device=settings.reranker_device,
                automodel_args={"trust_remote_code": True},
            )
        return self._model
