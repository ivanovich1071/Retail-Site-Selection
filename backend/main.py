import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1 import api_router
from backend.app.core.config import settings
from backend.app.core.database import engine, Base

logging.basicConfig(level=settings.LOG_LEVEL)
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

    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup — connecting to database")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown")

    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_application()
