"""
Celery tasks for demographics data refresh.

Schedule: 1st of every month at 03:00 (configured in celery_worker.py Beat schedule).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="demographics.refresh_all",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min retry delay
    soft_time_limit=600,
    time_limit=700,
)
def refresh_demographics_all(self):
    """
    Pull current year + 2 prior years for all registered regions from Belstat.
    Runs monthly; safe to trigger manually.
    """
    from backend.app.services.demographics import get_demographics_service

    current_year = date.today().year
    years = [current_year - 2, current_year - 1, current_year]

    service = get_demographics_service()

    try:
        result = asyncio.run(service.refresh_from_belstat(years=years))
        logger.info("Demographics refresh result: %s", result)
        return result
    except Exception as exc:
        logger.error("Demographics refresh failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    name="demographics.refresh_region",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def refresh_demographics_region(self, region_codes: list[str]):
    """Refresh a specific subset of regions (e.g., just Minsk districts)."""
    from backend.app.services.demographics import get_demographics_service

    current_year = date.today().year
    years = [current_year - 1, current_year]
    service = get_demographics_service()

    try:
        result = asyncio.run(
            service.refresh_from_belstat(region_codes=region_codes, years=years)
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)
