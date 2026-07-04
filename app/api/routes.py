"""API route definitions."""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest, ChatResponse, FeedbackRequest, SuggestionsResponse, SuggestionItem, StreamEvent
from app.api.dependencies import check_rate_limit, get_chat_service
from app.services.chat_service import ChatService
from app.utils.logger import get_logger


logger = get_logger("api_routes")
router = APIRouter(prefix="/api/v1")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    partner_id: str = Depends(check_rate_limit)
):
    """Main chat endpoint."""
    logger.info(f"Processing chat request for partner: {partner_id}")
    db = http_request.app.state.db_sessionmaker
    redis = http_request.app.state.redis
    response = await chat_service.process(
        request, partner_id=partner_id,
        db_sessionmaker=db, redis=redis,
    )
    return response


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    partner_id: str = Depends(check_rate_limit)
):
    """Streaming chat endpoint using Server-Sent Events."""
    logger.info(f"Processing streaming request for partner: {partner_id}")
    db = http_request.app.state.db_sessionmaker
    redis = http_request.app.state.redis
    
    async def stream_generator():
        # 1. Yield initial status event
        yield {
            "event": "status",
            "data": StreamEvent(
                type="status",
                message="Analyzing query and searching rulebooks..."
            ).model_dump_json()
        }
        await asyncio.sleep(0.2)
        
        # 2. Generate full response from chat service
        response = await chat_service.process(
            request, partner_id=partner_id,
            db_sessionmaker=db, redis=redis,
        )
        
        # 3. Stream citations first
        for citation in response.citations:
            yield {
                "event": "citation",
                "data": StreamEvent(
                    type="citation",
                    citation=citation
                ).model_dump_json()
            }
            await asyncio.sleep(0.1)
            
        # 4. Stream words token-by-token for interactive typing effect
        words = response.answer.split(" ")
        for i, word in enumerate(words):
            yield {
                "event": "token",
                "data": StreamEvent(
                    type="token",
                    text=(word + " ") if i < len(words) - 1 else word
                ).model_dump_json()
            }
            await asyncio.sleep(0.04)  # ~25 words per second typing speed
            
        # 5. Yield final done event with complete response
        yield {
            "event": "done",
            "data": StreamEvent(
                type="done",
                response=response
            ).model_dump_json()
        }

    return EventSourceResponse(stream_generator())


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(
    format: Optional[str] = None,
    context: Optional[str] = "general",
    partner_id: str = Depends(check_rate_limit)
):
    """Get suggested questions based on context."""
    logger.info(f"Retrieving suggestions for partner: {partner_id}, format: {format}, context: {context}")
    
    # Base set of cricket law questions
    items = [
        SuggestionItem(question="What is the LBW rule under Law 36?", category="LBW"),
        SuggestionItem(question="How does DRS (Decision Review System) work?", category="DRS"),
        SuggestionItem(question="When is a delivery called a Wide ball?", category="Delivery"),
        SuggestionItem(question="What happens when a ball hits the fielding team's helmet on the ground?", category="Dead Ball")
    ]
    
    # Tailor based on format context
    if format:
        fmt = format.lower()
        if fmt == "test":
            items.append(SuggestionItem(question="How many DRS reviews are allowed per innings in Test matches?", category="Test Match"))
        elif fmt in ["odi", "t20i"]:
            items.append(SuggestionItem(question="What are the powerplay restrictions in limited overs matches?", category="Powerplay"))
            
    return SuggestionsResponse(suggestions=items)


@router.post("/feedback")
async def feedback(
    request: FeedbackRequest,
    http_request: Request,
    partner_id: str = Depends(check_rate_limit)
):
    """Submit user feedback (thumbs up/down)."""
    logger.info(
        f"Feedback received - Partner: {partner_id}, Session: {request.session_id}, "
        f"Vote: {request.vote}, Query: '{request.query}'"
    )
    
    # Store feedback in PostgreSQL
    db_sessionmaker = http_request.app.state.db_sessionmaker
    try:
        async with db_sessionmaker() as session:
            from sqlalchemy import text
            
            # Create feedback table if it does not exist
            await session.execute(text(
                "CREATE TABLE IF NOT EXISTS user_feedback ("
                "  id SERIAL PRIMARY KEY,"
                "  partner_id VARCHAR(100),"
                "  session_id VARCHAR(100),"
                "  query TEXT,"
                "  response TEXT,"
                "  vote VARCHAR(10),"
                "  reason TEXT,"
                "  correct_answer TEXT,"
                "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            
            # Insert feedback record
            await session.execute(
                text(
                    "INSERT INTO user_feedback (partner_id, session_id, query, response, vote, reason, correct_answer) "
                    "VALUES (:partner_id, :session_id, :query, :response, :vote, :reason, :correct_answer)"
                ), {
                    "partner_id": partner_id,
                    "session_id": request.session_id,
                    "query": request.query,
                    "response": request.response,
                    "vote": request.vote,
                    "reason": request.reason,
                    "correct_answer": request.correct_answer
                }
            )
            await session.commit()
            logger.info("Feedback successfully stored in PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to store feedback in PostgreSQL: {e}")
        
    return {"status": "success", "message": "Feedback submitted successfully."}


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "cricket-rules-ai"}
