import logging
from datetime import datetime

from backend.celery_worker import celery_app
from backend.app.services.batch_processor import BatchProcessor
from backend.app.services.scoring import ScoringService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="batch_tasks.process_batch", max_retries=2)
def process_batch(self, batch_job_id: int, file_path: str):
    """
    Main batch processing task.
    Reads the uploaded file, geocodes each address, runs simplified scoring,
    and saves BatchResult rows.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.app.core.config import settings
    from backend.app.models.batch_job import BatchJob, BatchResult, BatchJobStatus

    engine = create_engine(settings.DATABASE_URL_SYNC)

    processor = BatchProcessor()
    scorer = ScoringService()

    with Session(engine) as db:
        job = db.get(BatchJob, batch_job_id)
        if not job:
            logger.error("BatchJob %d not found", batch_job_id)
            return

        try:
            addresses = processor.parse_file(file_path)
            job.total_rows = len(addresses)
            job.status = BatchJobStatus.running
            db.commit()
        except Exception as e:
            job.status = BatchJobStatus.failed
            db.commit()
            logger.error("Failed to parse batch file: %s", e)
            return

        for idx, address in enumerate(addresses):
            try:
                # Simplified sync geocode via httpx (no async in Celery task)
                import httpx
                from backend.app.core.config import settings as cfg

                _lon, _lat = None, None
                try:
                    r = httpx.get(
                        "https://geocode-maps.yandex.ru/1.x/",
                        params={
                            "apikey": cfg.YANDEX_GEOCODER_API_KEY,
                            "geocode": address,
                            "format": "json",
                            "results": 1,
                        },
                        timeout=10,
                    )
                    features = r.json()["response"]["GeoObjectCollection"]["featureMember"]
                    if features:
                        pos = features[0]["GeoObject"]["Point"]["pos"].split()
                        _lon, _lat = float(pos[0]), float(pos[1])
                except Exception:
                    pass

                score_data = scorer.calculate(
                    population_10min=8000,  # default without isochrone
                    avg_salary=1500,
                    competitors_count=3,
                    nearest_competitor_m=500,
                    isochrone_area_sqkm=3.14,
                    parking_spaces=10,
                    visibility_score=5.0,
                    area_sqm=250,
                )

                priority = processor.determine_priority(score_data["total_score"])

                result = BatchResult(
                    batch_job_id=batch_job_id,
                    address=address,
                    score=score_data["total_score"],
                    priority=priority,
                    raw_data=score_data,
                )
                db.add(result)
                job.processed_rows = idx + 1
                db.commit()

            except Exception as e:
                logger.warning("Error processing address '%s': %s", address, e)
                result = BatchResult(
                    batch_job_id=batch_job_id,
                    address=address,
                    error_message=str(e)[:500],
                )
                db.add(result)
                job.failed_rows += 1
                db.commit()

        job.status = BatchJobStatus.completed
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info("Batch job %d completed: %d rows", batch_job_id, len(addresses))
