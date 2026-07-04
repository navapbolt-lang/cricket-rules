"""Stats & analytics API endpoints for the admin dashboard."""

from fastapi import APIRouter, Depends, Request
from app.api.dependencies import check_rate_limit

router = APIRouter(prefix="/api/v1/stats")


@router.get("/overview")
async def stats_overview(
    request: Request,
    partner_id: str = Depends(check_rate_limit),
):
    """Dashboard overview — daily stats, quota, top formats."""
    usage = request.app.state.usage_service
    db = request.app.state.db_sessionmaker
    daily = await usage.get_daily_stats(partner_id, db_sessionmaker=db)
    top = await usage.get_top_queries(partner_id, limit=5, db_sessionmaker=db)
    return {"daily": daily, "top_queries": top}


@router.get("/daily")
async def stats_daily(
    request: Request,
    partner_id: str = Depends(check_rate_limit),
):
    """Daily usage breakdown by format."""
    usage = request.app.state.usage_service
    db = request.app.state.db_sessionmaker
    data = await usage.get_daily_stats(partner_id, db_sessionmaker=db)
    return data


@router.get("/top-queries")
async def stats_top_queries(
    request: Request,
    partner_id: str = Depends(check_rate_limit),
    limit: int = 10,
):
    """Most asked questions."""
    usage = request.app.state.usage_service
    db = request.app.state.db_sessionmaker
    data = await usage.get_top_queries(partner_id, limit=limit, db_sessionmaker=db)
    return {"queries": data}
