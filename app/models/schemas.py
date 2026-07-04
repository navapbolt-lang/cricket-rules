from pydantic import BaseModel, Field
from typing import Optional
from app.models.types import Format, Authority


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    format: Optional[Format] = None
    context: Optional[str] = Field(None, pattern=r"^(match|article|general)$")
    session_id: Optional[str] = None
    web_search: Optional[bool] = None


class Citation(BaseModel):
    law_number: str
    text: str
    formats: list[Format]
    authority: Authority
    year: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_questions: list[str]
    format_used: Optional[Format] = None
    guardrail_status: str


class StreamEvent(BaseModel):
    type: str = Field(..., pattern=r"^(status|token|citation|done)$")
    message: Optional[str] = None
    text: Optional[str] = None
    citation: Optional[Citation] = None
    response: Optional[ChatResponse] = None


class FeedbackRequest(BaseModel):
    session_id: str
    query: str
    response: str
    vote: str = Field(..., pattern=r"^(up|down)$")
    reason: Optional[str] = None
    correct_answer: Optional[str] = None


class SuggestionItem(BaseModel):
    question: str
    category: str


class SuggestionsResponse(BaseModel):
    suggestions: list[SuggestionItem]


class Partner(BaseModel):
    id: str
    name: str
    domain: str
    plan: str = "starter"
    monthly_quota: int = 10000
    api_key_hash: str
    active: bool = True
    created_at: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: Optional[str] = None
