"""In-process batch runner — processes an uploaded address file without Celery.

Mirrors the Celery task but runs in a FastAPI BackgroundTask using the async
domain services (geocode → score). Used as the default dispatch path so batch
upload works in the local/dev stack where no Celery worker is running.
"""
import logging
from datetime import datetime, timezone

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.batch_job import BatchJob, BatchResult, BatchJobStatus
from backend.app.services.batch_processor import BatchProcessor
from backend.app.services.geocode import GeocodeService
from backend.app.services.scoring import ScoringService

logger = logging.getLogger(__name__)


async def run_batch_job(batch_job_id: int, file_path: str) -> None:
    """Parse the file, geocode + score each address, persist BatchResult rows."""
    processor = BatchProcessor()
    geocoder = GeocodeService()
    scorer = ScoringService()

    async with AsyncSessionLocal() as db:
        job = await db.get(BatchJob, batch_job_id)
        if job is None:
            logger.error("BatchJob %s not found", batch_job_id)
            return

        try:
            addresses = processor.parse_file(file_path)
        except Exception as e:  # noqa: BLE001
            job.status = BatchJobStatus.failed
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Batch %s parse failed: %s", batch_job_id, e)
            return

        job.total_rows = len(addresses)
        job.status = BatchJobStatus.running
        await db.commit()

        processed, failed = 0, 0
        for address in addresses:
            try:
                lon, lat = await geocoder.geocode(address)
                # Lightweight scoring with neutral defaults; full pipeline lives
                # in the per-location analysis. Batch is a first-pass ranking.
                score_data = scorer.calculate(
                    population_10min=8000,
                    avg_salary=1620.0,
                    competitors_count=0,
                    nearest_competitor_m=None,
                    isochrone_area_sqkm=3.14,
                    parking_spaces=None,
                    visibility_score=None,
                    area_sqm=None,
                )
                score = score_data["total_score"]
                db.add(BatchResult(
                    batch_job_id=job.id,
                    address=address,
                    score=score,
                    priority=processor.determine_priority(score),
                    raw_data={"latitude": lat, "longitude": lon},
                ))
                processed += 1
            except Exception as e:  # noqa: BLE001
                db.add(BatchResult(
                    batch_job_id=job.id,
                    address=address,
                    error_message=str(e)[:500],
                ))
                failed += 1

            job.processed_rows = processed
            job.failed_rows = failed
            await db.commit()

        job.status = BatchJobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Batch %s done: %d ok, %d failed", batch_job_id, processed, failed)
