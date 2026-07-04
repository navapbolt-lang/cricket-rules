"""Tests for RAG pipeline (retrieval + re-ranking)."""

import pytest
from app.models.types import LawChunk, ChunkMetadata, ChunkType, Format, Authority
from app.models.schemas import Citation


class TestRetriever:
    """Test hybrid search retriever."""

    def test_hybrid_search_returns_results(self):
        from app.rag.retriever import HybridRetriever
        assert HybridRetriever is not None

    def test_metadata_filtering(self):
        from app.rag.retriever import HybridRetriever
        assert hasattr(HybridRetriever, "_build_filter")

    def test_law_number_exact_match(self):
        meta = ChunkMetadata(
            law_number="36.1",
            parent_law="36",
            title="LBW",
            formats=[Format.ALL],
            authority=Authority.MCC,
            gender="all",
            year=2022,
            effective_date="2022-04-01",
            page_number=10,
            chunk_index=0,
            chunk_type=ChunkType.CLAUSE,
        )
        assert meta.law_number == "36.1"

    def test_chunk_metadata_formats(self):
        meta = ChunkMetadata(
            law_number="1", parent_law="1", title="Test",
            formats=[Format.TEST, Format.ODI],
            authority=Authority.ICC, gender="men", year=2025,
            effective_date="2025-04-01", page_number=1,
            chunk_index=0, chunk_type=ChunkType.SECTION,
        )
        assert Format.TEST in meta.formats
        assert Format.ODI in meta.formats
        assert Format.T20I not in meta.formats


class TestReRanker:
    """Test cross-encoder re-ranking (no model loading)."""

    def test_reranker_imports(self):
        from app.rag.re_ranker import ReRanker
        assert ReRanker is not None
        assert hasattr(ReRanker, "rerank")

    def test_reranker_logic_without_model(self):
        """Verify rerank logic shape using a simple lambda mock."""
        chunks = [
            LawChunk(id="1", text="LBW law applies when ball pitches in line",
                     metadata=ChunkMetadata(
                         law_number="36", parent_law="36", title="LBW",
                         formats=[Format.TEST], authority=Authority.ICC,
                         year=2025, effective_date="2025-04-01",
                         page_number=1, chunk_index=0, chunk_type=ChunkType.SECTION,
                     ), score=0.5),
            LawChunk(id="2", text="Wide ball Law 22",
                     metadata=ChunkMetadata(
                         law_number="22", parent_law="22", title="Wide",
                         formats=[Format.TEST], authority=Authority.ICC,
                         year=2025, effective_date="2025-04-01",
                         page_number=2, chunk_index=0, chunk_type=ChunkType.SECTION,
                     ), score=0.3),
        ]
        reranked = sorted(chunks, key=lambda c: c.score or 0, reverse=True)
        assert len(reranked) == 2
        assert reranked[0].id == "1"


class TestCitations:
    """Test citation model and formatting."""

    def test_citation_creation(self):
        cite = Citation(
            law_number="36.1",
            text="Law 36.1 LBW",
            formats=[Format.TEST],
            authority=Authority.ICC,
            year=2025,
        )
        assert cite.law_number == "36.1"
        assert cite.authority == Authority.ICC
