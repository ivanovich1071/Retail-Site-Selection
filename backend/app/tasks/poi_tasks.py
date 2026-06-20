"""Celery tasks for POI ingestion from OpenStreetMap."""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="poi.ingest_area", bind=True, max_retries=2, default_retry_delay=120)
def ingest_area(self, lat: float, lon: float, radius_m: int = 1500):
    """Fetch, normalize, dedupe and upsert retail POIs around a point."""
    from backend.app.core.database import AsyncSessionLocal
    from backend.app.spatial.poi_pipeline import ingest_pois

    async def _run():
        async with AsyncSessionLocal() as db:
            return await ingest_pois(lat, lon, radius_m, db)

    try:
        result = asyncio.run(_run())
        logger.info("POI ingest result: %s", result)
        return result
    except Exception as exc:
        logger.error("POI ingest failed: %s", exc)
        raise self.retry(exc=exc)
