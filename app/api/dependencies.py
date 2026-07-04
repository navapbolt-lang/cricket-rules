"""FastAPI dependency injection.

Provides shared dependencies that the route handlers need:
- ChatService
- Partner authentication
- Rate limiter
"""

from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from app.config import settings
from app.services.chat_service import ChatService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_partner_id(api_key: str = Security(api_key_header)) -> str:
    """Extract and validate partner API key from header.
    
    If valid, returns partner_id.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide X-API-Key header."
        )
    # Allow quickstart "test-key", settings admin key, or dummy partner keys
    if api_key in ["test-key", settings.admin_api_key] or api_key.startswith("partner_"):
        return "test-partner-id"
        
    raise HTTPException(
        status_code=401,
        detail="Invalid API key."
    )


async def check_rate_limit(request: Request, partner_id: str = Depends(get_partner_id)) -> str:
    """Check rate limit for the partner using Redis."""
    redis = request.app.state.redis
    redis_key = f"partner_rate_limit:{partner_id}"
    
    try:
        current_usage = await redis.get(redis_key)
        if current_usage is not None and int(current_usage) >= settings.default_monthly_quota:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Monthly quota reached."
            )
        await redis.incr(redis_key)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        # If Redis is unavailable, log and pass to avoid blocking service
        pass
        
    return partner_id


async def get_chat_service(request: Request) -> ChatService:
    """Retrieve ChatService instance from app state."""
    return request.app.state.chat_service
