"""FastAPI application entry point.

Creates the FastAPI app, registers middleware,
includes routers, and manages startup/shutdown lifecycle.
"""

import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.api.routes import router
from app.api.widget_routes import router as widget_router
from app.utils.logger import setup_logging
from app.config import settings

from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import VectorStore
from app.rag.retriever import HybridRetriever
from app.rag.re_ranker import ReRanker
from app.agent.tools import CricketTools
from app.agent.agent import Agent
from app.services.chat_service import ChatService
from app.services.partner_service import PartnerService
from app.services.usage_service import UsageService
from app.api.middleware import CORSMiddleware, LoggingMiddleware
from app.api.stats_routes import router as stats_router

# Optional monitoring imports
try:
    from app.monitoring.metrics import (
        PrometheusMiddleware,
        metrics_endpoint,
        CHUNK_COUNT,
    )
    from app.monitoring.error_tracker import init_error_tracker

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    metrics_endpoint = None
    CHUNK_COUNT = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()

    if MONITORING_AVAILABLE:
        try:
            init_error_tracker(environment=os.getenv("ENVIRONMENT", "production"))
        except Exception:
            pass

    embedding_client = EmbeddingClient()

    # All RAG services - lazy initialization (setup on first request)
    vector_store = None
    retriever = None
    re_ranker = None
    agent = None
    chat_service = None
    usage_service = None
    partner_service = None

    def init_rag_services():
        nonlocal \
            vector_store, \
            retriever, \
            re_ranker, \
            agent, \
            chat_service, \
            usage_service, \
            partner_service
        if chat_service is not None:
            return  # Already initialized

        try:
            from app.rag.vector_store import VectorStore
            from app.rag.retriever import HybridRetriever
            from app.rag.re_ranker import ReRanker
            from app.agent.tools import CricketTools
            from app.agent.agent import Agent
            from app.services.chat_service import ChatService
            from app.services.partner_service import PartnerService
            from app.services.usage_service import UsageService

            vector_store = VectorStore()
            retriever = HybridRetriever(vector_store, embedding_client)
            re_ranker = ReRanker()

            tools = CricketTools(retriever, vector_store)
            agent = Agent(tools)

            usage_service = UsageService()
            partner_service = PartnerService()
            chat_service = ChatService(
                retriever,
                re_ranker,
                agent,
                usage_service=usage_service,
                partner_service=partner_service,
            )
            logger.info("RAG services initialized.")
        except Exception as e:
            logger.warning(f"RAG init failed: {e}")

    # Store init function for lazy loading
    app.state.init_rag = init_rag_services
    app.state.chat_service = None  # Will be set on first request

    logger.info("Fast startup complete. RAG services will initialize on first request.")

    # Redis - optional
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        logger.info("Redis connected.")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")

    # PostgreSQL - optional
    db_engine = None
    db_sessionmaker = None
    try:
        db_engine = create_async_engine(settings.database_url, echo=False)
        db_sessionmaker = async_sessionmaker(db_engine, expire_on_commit=False)
        logger.info("PostgreSQL connected.")
    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")

    app.state.embedding_client = embedding_client
    app.state.vector_store = vector_store
    app.state.redis = redis_client
    app.state.db_engine = db_engine
    app.state.db_sessionmaker = db_sessionmaker
    app.state.retriever = retriever
    app.state.re_ranker = re_ranker
    app.state.agent = agent
    app.state.partner_service = partner_service
    app.state.usage_service = usage_service

    logger.info("All services successfully initialized on startup.")

    yield

    if redis_client:
        await redis_client.close()
        logger.info("Closed Redis connection.")

    if db_engine:
        await db_engine.dispose()
        logger.info("Disposed database connection pool.")

    if vector_store and hasattr(vector_store, "client"):
        vector_store.client.close()
        logger.info("Closed Qdrant client connection.")


app = FastAPI(
    title="CricketGPT",
    description="B2B embeddable AI chatbot for cricket law queries",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware)
app.add_middleware(LoggingMiddleware)

if MONITORING_AVAILABLE:
    try:
        app.add_middleware(PrometheusMiddleware)
        app.add_route("/metrics", metrics_endpoint, include_in_schema=False)
    except Exception:
        pass

app.include_router(router)
app.include_router(widget_router)
app.include_router(stats_router)
