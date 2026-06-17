import logging

from backend.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="huff_tasks.calculate_huff", max_retries=2)
def calculate_huff_for_location(self, location_id: int):
    """Full Huff model calculation with ORS travel times (heavy, async via Celery)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.app.core.config import settings
    from backend.app.models.location import Location
    from backend.app.models.scoring_result import ScoringResult
    from backend.app.services.huff import HuffService

    engine = create_engine(settings.DATABASE_URL_SYNC)
    huff = HuffService()

    with Session(engine) as db:
        location = db.get(Location, location_id)
        if not location:
            logger.error("Location %d not found", location_id)
            return

        # Simplified: use existing scoring result's population data
        scoring = (
            db.query(ScoringResult)
            .filter(ScoringResult.location_id == location_id)
            .order_by(ScoringResult.calculated_at.desc())
            .first()
        )

        if not scoring:
            logger.warning("No scoring result for location %d, skipping Huff", location_id)
            return

        # Placeholder population zones — in production, fetched from DemographicsZone
        population_zones = [{"population": 5000, "travel_time_s": 300}]
        all_stores = [{"area_sqm": 400, "travel_time_s": 450}]

        result = huff.calculate_market_share(
            candidate_area_sqm=location.area_sqm or 250,
            candidate_travel_times=[300],
            population_zones=population_zones,
            all_stores=all_stores,
        )

        scoring.huff_market_share = result["market_share"]
        db.commit()
        logger.info("Huff calculation complete for location %d: %.2f%%", location_id, result["market_share_pct"])
        return result
