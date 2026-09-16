"""
FastAPI application entry point.
Structured logging, CORS, lifespan (DB init, provider warmup), global error handler.
"""
import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.providers.factory import get_provider
from app.providers.base import ProviderUnavailableError
from app.routers import health, sessions, chat, artifacts

# ─── Logging setup ────────────────────────────────────────────────────────────

settings = get_settings()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.app_env == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, warm up provider. Shutdown: nothing special needed."""
    logger.info(
        "app.starting",
        env=settings.app_env,
        provider=settings.llm_provider.value,
        model=settings.active_chat_model,
    )

    # Init DB (creates tables, enables pgvector)
    try:
        await init_db()
        logger.info("app.db_ready")
    except Exception as exc:
        logger.error("app.db_init_failed", error=str(exc))
        # Don't crash on DB failure — health/ready will report degraded

    # Warm up provider (instantiates client, validates keys)
    try:
        provider = get_provider()
        logger.info("app.provider_ready", provider=provider.name)
    except ProviderUnavailableError as exc:
        logger.warning("app.provider_unavailable", error=str(exc))
    except Exception as exc:
        logger.error("app.provider_init_failed", error=str(exc))

    yield

    logger.info("app.shutdown")


# ─── App factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lenny Growth Assistant API",
    description="AI-powered Q&A and content generation grounded in Lenny's Podcast/Newsletter",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(artifacts.router)


@app.get("/")
async def root():
    return {
        "service": "Lenny Growth Assistant",
        "version": "1.0.0",
        "provider": settings.llm_provider.value,
        "model": settings.active_chat_model,
        "docs": "/docs",
    }
