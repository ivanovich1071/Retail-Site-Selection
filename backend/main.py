import logging
import time

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from backend.app.api.v1 import api_router
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.logging_config import setup_logging
from backend.app.core.request_logging import RequestLoggingMiddleware
from backend.app.observability.metrics import (
    MetricsMiddleware, render_metrics, CONTENT_TYPE_LATEST,
)
from backend.app.events.handlers import register_default_handlers

setup_logging()
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Retail Site Selection API",
        description="API для автоматизации выбора торговых объектов сети Евроторг",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(RequestLoggingMiddleware)
    if settings.METRICS_ENABLED:
        app.add_middleware(MetricsMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup — connecting to database")
        register_default_handlers()

    @app.get("/metrics", tags=["System"])
    async def metrics_endpoint():
        return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown")

    _start_time = time.time()

    @app.get("/health", tags=["System"])
    async def health_check():
        checks = {"db": "unknown", "redis": "unknown"}
        healthy = True

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as e:
            checks["db"] = str(e)[:120]
            healthy = False

        try:
            from backend.app.core.redis import get_redis
            r = await get_redis()
            await r.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = str(e)[:120]
            healthy = False

        uptime = round(time.time() - _start_time)
        return {
            "status": "ok" if healthy else "degraded",
            "version": "1.0.0",
            "uptime_seconds": uptime,
            "checks": checks,
        }

    return app


app = create_application()
