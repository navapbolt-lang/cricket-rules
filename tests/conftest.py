"""Test fixtures for all test modules."""

import pytest
from app.models.types import (
    LawChunk, ChunkMetadata, ChunkType, Format, Authority, Gender,
    ConditionCheck, CitationResult, HallucinationResult, FormatResult, SafetyResult,
    GuardrailResult, GuardrailName,
)
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def sample_chunks():
    return [
        LawChunk(
            id="chunk-1",
            text="Law 36.1: The bowler's end umpire shall consider the ball-pitching zone.",
            metadata=ChunkMetadata(
                law_number="36.1",
                parent_law="36",
                title="LBW - Pitching",
                formats=[Format.ALL],
                authority=Authority.ICC,
                gender="all",
                year=2025,
                effective_date="2025-04-01",
                page_number=10,
                chunk_index=0,
                chunk_type=ChunkType.CLAUSE,
            ),
            score=0.85,
        ),
        LawChunk(
            id="chunk-2",
            text="Law 36.2: The ball must impact in line with the stumps.",
            metadata=ChunkMetadata(
                law_number="36.2",
                parent_law="36",
                title="LBW - Impact",
                formats=[Format.ALL],
                authority=Authority.ICC,
                gender="all",
                year=2025,
                effective_date="2025-04-01",
                page_number=10,
                chunk_index=1,
                chunk_type=ChunkType.CLAUSE,
            ),
            score=0.78,
        ),
        LawChunk(
            id="chunk-3",
            text="Law 36.3: The ball would have hit the stumps.",
            metadata=ChunkMetadata(
                law_number="36.3",
                parent_law="36",
                title="LBW - Trajectory",
                formats=[Format.ALL],
                authority=Authority.ICC,
                gender="all",
                year=2025,
                effective_date="2025-04-01",
                page_number=10,
                chunk_index=2,
                chunk_type=ChunkType.CLAUSE,
            ),
            score=0.72,
        ),
        LawChunk(
            id="chunk-4",
            text="Law 36.4: The batter did not hit the ball.",
            metadata=ChunkMetadata(
                law_number="36.4",
                parent_law="36",
                title="LBW - No bat",
                formats=[Format.ALL],
                authority=Authority.ICC,
                gender="all",
                year=2025,
                effective_date="2025-04-01",
                page_number=10,
                chunk_index=3,
                chunk_type=ChunkType.CLAUSE,
            ),
            score=0.65,
        ),
    ]


@pytest.fixture
def sample_scenarios():
    return [
        {
            "query": "Ball pitched outside leg, hit in front, no bat, going on to hit off stump",
            "expected": "NOT OUT",
            "law": "36.1",
            "reason": "Ball pitched outside leg - automatic NOT OUT per Law 36.1",
        },
        {
            "query": "Ball pitched on off, hits pad in front of middle, no bat, hitting middle",
            "expected": "OUT",
            "law": "36.1-36.4",
            "reason": "All LBW conditions satisfied",
        },
    ]


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
