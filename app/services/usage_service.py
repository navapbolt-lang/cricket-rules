"""Usage tracking and quota enforcement — Redis counters + Postgres audit log."""

from datetime import datetime, timezone
from sqlalchemy import text


class UsageService:
    """Track and enforce partner usage quotas."""

    async def check_quota(self, partner_id: str, redis=None) -> bool:
        if not redis:
            return True
        try:
            key = f"quota:{partner_id}:monthly"
            current = await redis.get(key)
            if current is not None:
                from app.config import settings
                if int(current) >= settings.default_monthly_quota:
                    return False
            return True
        except Exception:
            return True

    async def increment_usage(self, partner_id: str, redis=None) -> int:
        if not redis:
            return 0
        try:
            key = f"quota:{partner_id}:monthly"
            ttl = await redis.ttl(key)
            if ttl == -1:
                await redis.expire(key, 86400 * 30)
            return await redis.incr(key)
        except Exception:
            return 0

    async def log_query(
        self,
        partner_id: str,
        query: str,
        response: str,
        format_used: str = "",
        latency_ms: float = 0.0,
        guardrail_status: str = "",
        confidence: float = 0.0,
        db_sessionmaker=None,
    ):
        if not db_sessionmaker:
            return
        try:
            async with db_sessionmaker() as session:
                await session.execute(
                    text(
                        "INSERT INTO usage_log "
                        "(partner_id, query, response, format_used, latency_ms, guardrail_status, confidence, created_at) "
                        "VALUES (:pid, :query, :response, :fmt, :latency, :guardrail, :confidence, :now)"
                    ),
                    {
                        "pid": partner_id,
                        "query": query[:500],
                        "response": response[:2000],
                        "fmt": format_used,
                        "latency": round(latency_ms, 1),
                        "guardrail": guardrail_status,
                        "confidence": round(confidence, 2),
                        "now": datetime.now(timezone.utc),
                    },
                )
                await session.commit()
        except Exception:
            pass

    async def get_daily_stats(self, partner_id: str, db_sessionmaker=None) -> dict:
        if not db_sessionmaker:
            return {"total": 0, "by_format": {}, "avg_confidence": 0.0}
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text(
                        "SELECT COUNT(*) as total, "
                        "COALESCE(AVG(confidence), 0) as avg_conf, "
                        "COALESCE(AVG(latency_ms), 0) as avg_latency "
                        "FROM usage_log WHERE partner_id = :id "
                        "AND created_at >= CURRENT_DATE"
                    ),
                    {"id": partner_id},
                )
                row = result.fetchone()
                total = row.total if row else 0
                avg_conf = float(row.avg_conf) if row else 0.0
                avg_lat = float(row.avg_latency) if row else 0.0

                result = await session.execute(
                    text(
                        "SELECT format_used, COUNT(*) as cnt FROM usage_log "
                        "WHERE partner_id = :id AND created_at >= CURRENT_DATE "
                        "GROUP BY format_used"
                    ),
                    {"id": partner_id},
                )
                by_format = {row.format_used or "unknown": row.cnt for row in result.fetchall()}

                return {
                    "total": total,
                    "avg_confidence": round(avg_conf, 2),
                    "avg_latency_ms": round(avg_lat, 1),
                    "by_format": by_format,
                }
        except Exception:
            return {"total": 0, "by_format": {}, "avg_confidence": 0.0}

    async def get_top_queries(self, partner_id: str, limit: int = 10, db_sessionmaker=None) -> list[dict]:
        if not db_sessionmaker:
            return []
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text(
                        "SELECT query, COUNT(*) as cnt FROM usage_log "
                        "WHERE partner_id = :id "
                        "GROUP BY query ORDER BY cnt DESC LIMIT :lim"
                    ),
                    {"id": partner_id, "lim": limit},
                )
                return [{"query": row.query, "count": row.cnt} for row in result.fetchall()]
        except Exception:
            return []
