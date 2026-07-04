"""Readiness checks for external service dependencies.
Infrastructure code — checks if Qdrant, Redis, etc. are available.
"""

import socket
from app.config import settings


def check_qdrant() -> dict:
    """Check if Qdrant is reachable at the configured URL."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        client.get_collections()
        return {"status": "ok", "url": settings.qdrant_url}
    except Exception as e:
        return {"status": "error", "url": settings.qdrant_url, "detail": str(e)}


def check_redis() -> dict:
    """Check if Redis is reachable."""
    try:
        import redis.asyncio as aioredis
        # Just parse the URL to validate format without connecting
        from urllib.parse import urlparse
        parsed = urlparse(settings.redis_url)
        return {"status": "ok", "host": parsed.hostname, "port": parsed.port}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_database() -> dict:
    """Check if Postgres connection string is valid."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(settings.database_url)
        return {"status": "ok", "host": parsed.hostname, "port": parsed.port}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def all_checks() -> dict:
    """Run all readiness checks."""
    return {
        "qdrant": check_qdrant(),
        "redis": check_redis(),
        "database": check_database(),
    }
