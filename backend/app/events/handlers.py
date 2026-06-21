"""Default event handlers — event-triggered side effects.

Kept side-effect-light and idempotent. Registered on startup via
register_default_handlers(). Heavy work (recalculation, ingestion) is logged and
delegated to Celery tasks where available.
"""
import logging

from backend.app.events.event_bus import (
    event_bus, Event,
    LOCATION_CREATED, SCORE_CHANGED, COMPETITOR_ADDED, MOBILITY_UPDATED,
)

logger = logging.getLogger(__name__)


async def on_location_created(event: Event) -> None:
    loc_id = event.payload.get("location_id")
    logger.info("Event: location.created id=%s → schedule analysis", loc_id)


async def on_score_changed(event: Event) -> None:
    logger.info(
        "Event: score.changed location=%s %s→%s",
        event.payload.get("location_id"),
        event.payload.get("old_score"),
        event.payload.get("new_score"),
    )


async def on_competitor_added(event: Event) -> None:
    logger.info(
        "Event: competitor.added near=%s → recompute affected locations",
        event.payload.get("location_id") or event.payload.get("coords"),
    )


async def on_mobility_updated(event: Event) -> None:
    logger.info("Event: mobility.updated zone=%s", event.payload.get("zone"))


def register_default_handlers() -> None:
    event_bus.subscribe(LOCATION_CREATED, on_location_created)
    event_bus.subscribe(SCORE_CHANGED, on_score_changed)
    event_bus.subscribe(COMPETITOR_ADDED, on_competitor_added)
    event_bus.subscribe(MOBILITY_UPDATED, on_mobility_updated)
    logger.info("Registered %d default event handlers", 4)
