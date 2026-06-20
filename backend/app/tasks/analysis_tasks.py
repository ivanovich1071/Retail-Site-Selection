"""Celery task wrapper for the analysis orchestrator.

Used when a Celery worker is available; the API can alternatively run the
orchestrator in-process via asyncio for local/dev environments.
"""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="analysis.run_job", bind=True, max_retries=1)
def run_analysis(self, job_id: int):
    from backend.app.orchestrator.analysis_orchestrator import run_analysis_job

    try:
        asyncio.run(run_analysis_job(job_id))
        return {"job_id": job_id, "status": "dispatched"}
    except Exception as exc:
        logger.error("Analysis job %s failed in worker: %s", job_id, exc)
        raise self.retry(exc=exc)
