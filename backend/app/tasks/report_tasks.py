import logging
import os

from backend.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="report_tasks.generate_pdf", max_retries=2)
def generate_pdf_report(self, location_id: int):
    """Generate PDF report for a location and save to disk."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.app.core.config import settings
    from backend.app.models.location import Location
    from backend.app.models.scoring_result import ScoringResult
    from backend.app.services.report import ReportService
    import asyncio

    engine = create_engine(settings.DATABASE_URL_SYNC)
    reporter = ReportService()

    with Session(engine) as db:
        location = db.get(Location, location_id)
        if not location:
            logger.error("Location %d not found for PDF generation", location_id)
            return

        scoring = (
            db.query(ScoringResult)
            .filter(ScoringResult.location_id == location_id)
            .order_by(ScoringResult.calculated_at.desc())
            .first()
        )

        location_data = {
            "id": location.id,
            "address": location.address,
            "area_sqm": location.area_sqm,
            "status": location.status.value,
            "total_score": scoring.total_score if scoring else None,
            "huff_market_share": scoring.huff_market_share if scoring else None,
        }

        output_path = os.path.join(settings.UPLOAD_DIR, "reports", f"location_{location_id}.pdf")
        asyncio.run(reporter.generate_pdf(location_data, output_path))
        logger.info("PDF report for location %d saved to %s", location_id, output_path)
        return output_path
