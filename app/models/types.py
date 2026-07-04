from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Format(str, Enum):
    TEST = "test"
    ODI = "odi"
    T20I = "t20i"
    ALL = "all"


class Authority(str, Enum):
    ICC = "icc"
    MCC = "mcc"


class Gender(str, Enum):
    MEN = "men"
    WOMEN = "women"
    ALL = "all"


class ScenarioType(str, Enum):
    LBW = "lbw"
    RUN_OUT = "run_out"
    STUMPING = "stumping"
    HIT_WICKET = "hit_wicket"
    OBSTRUCTING = "obstructing"
    NO_BALL = "no_ball"
    WIDE = "wide"
    DRS_REVIEW = "drs_review"
    BOUNDARY_CATCH = "boundary_catch"
    CONCUSSION = "concussion"
    OVER_RATE = "over_rate"
    DLS = "dls"


class ChunkType(str, Enum):
    SECTION = "section"
    CLAUSE = "clause"
    SUBCLAUSE = "subclause"


class GuardrailName(str, Enum):
    CITATION = "citation"
    HALLUCINATION = "hallucination"
    FORMAT_CHECK = "format_check"
    CONFIDENCE = "confidence"
    SAFETY = "safety"


class QueryType(str, Enum):
    SIMPLE_LOOKUP = "simple_lookup"
    SCENARIO = "scenario"
    DEFINITION = "definition"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"


class ChunkMetadata(BaseModel):
    law_number: str
    parent_law: str
    title: str
    formats: list[Format]
    authority: Authority
    gender: str = "all"
    year: int
    effective_date: str
    page_number: int
    chunk_index: int
    chunk_type: ChunkType


class LawChunk(BaseModel):
    id: str
    text: str
    metadata: ChunkMetadata
    embedding: Optional[list[float]] = None
    score: Optional[float] = None


class ConditionCheck(BaseModel):
    id: int
    description: str
    law: str
    terminal: bool
    passed: Optional[bool] = None
    reasoning: Optional[str] = None


class ScenarioGraph(BaseModel):
    scenario_type: ScenarioType
    format: Format
    conditions: list[ConditionCheck]


class ToolResult(BaseModel):
    success: bool
    data: dict
    error: Optional[str] = None


class CitationResult(BaseModel):
    all_valid: bool
    invalid_citations: list[str]
    unsupported_claims: list[dict]


class HallucinationResult(BaseModel):
    is_consistent: bool
    failed_claims: list[dict]


class FormatResult(BaseModel):
    is_consistent: bool
    mismatches: list[str]
    note: Optional[str] = None


class SafetyResult(BaseModel):
    is_safe: bool
    reason: Optional[str] = None


class GuardrailResult(BaseModel):
    name: GuardrailName
    passed: bool
    details: Optional[dict] = None
