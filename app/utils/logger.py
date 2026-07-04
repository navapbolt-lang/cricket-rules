"""Structured logging using loguru."""

import sys
from loguru import logger
from app.config import settings


def setup_logging():
    """Configure structured logging with console and JSON support."""
    from pathlib import Path
    logger.remove()

    log_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"

    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logger.add(
        str(log_dir / "cricket-bot.log"),
        format=file_format,
        level="DEBUG",
        rotation="10 MB",
        retention=3,
        compression="gz",
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"Logging initialized (level={settings.log_level}, file={log_dir / 'cricket-bot.log'})")
    return logger


def get_logger(name: str):
    """Get a named child logger."""
    return logger.bind(service=name)


def log_query_event(partner_id: str, query: str, format_used: str, latency_ms: float, guardrail_status: str):
    """Log a structured query event for analytics."""
    logger.bind(event="query", partner_id=partner_id, format=format_used,
                latency_ms=round(latency_ms, 1), guardrail=guardrail_status).info(
        f"Query | partner={partner_id} format={format_used} latency={latency_ms:.0f}ms guardrail={guardrail_status}"
    )


def log_guardrail_failure(guardrail_name: str, reason: str, partner_id: str = ""):
    """Log a guardrail failure with context."""
    logger.bind(event="guardrail_failure", guardrail=guardrail_name,
                partner_id=partner_id).warning(
        f"Guardrail {guardrail_name} blocked | partner={partner_id} reason={reason}"
    )
    from app.monitoring.metrics import GUARDRAIL_FAILURES
    GUARDRAIL_FAILURES.labels(guardrail=guardrail_name).inc()


def log_error_event(error: str, context: dict | None = None):
    """Log an error event with structured context."""
    logger.bind(event="error", **(context or {})).error(f"Error: {error}")


def log_rate_limit(partner_id: str, quota: int):
    """Log a rate limit event."""
    logger.bind(event="rate_limit", partner_id=partner_id, quota=quota).warning(
        f"Rate limit hit | partner={partner_id} quota={quota}"
    )
