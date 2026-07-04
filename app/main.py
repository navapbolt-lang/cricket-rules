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
from app.monitoring.metrics import PrometheusMiddleware, metrics_endpoint
from app.monitoring.error_tracker import init_error_tracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()

    init_error_tracker(environment=os.getenv("ENVIRONMENT", "production"))

    embedding_client = EmbeddingClient()
    vector_store = VectorStore()

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    db_engine = create_async_engine(settings.database_url, echo=False)
    db_sessionmaker = async_sessionmaker(db_engine, expire_on_commit=False)

    retriever = HybridRetriever(vector_store, embedding_client)
    re_ranker = ReRanker()
    re_ranker._load_model()  # Pre-warm: download & load model at startup

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

    app.state.embedding_client = embedding_client
    app.state.vector_store = vector_store
    app.state.redis = redis_client
    app.state.db_engine = db_engine
    app.state.db_sessionmaker = db_sessionmaker
    app.state.retriever = retriever
    app.state.re_ranker = re_ranker
    app.state.agent = agent
    app.state.chat_service = chat_service
    app.state.partner_service = partner_service
    app.state.usage_service = usage_service

    from app.monitoring.metrics import CHUNK_COUNT

    CHUNK_COUNT.set(vector_store.count())

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
app.add_middleware(PrometheusMiddleware)

app.include_router(router)
app.include_router(widget_router)
app.include_router(stats_router)

app.add_route("/metrics", metrics_endpoint, include_in_schema=False)
