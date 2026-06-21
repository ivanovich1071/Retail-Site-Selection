"""Event-Driven Architecture — lightweight event bus over Redis Streams.

Publishes domain events (location.created, score.changed, competitor.added,
mobility.updated) and dispatches them to registered handlers. Degrades to an
in-process buffer when Redis is unavailable so the app keeps working.
"""
from backend.app.events.event_bus import (
    EventBus, event_bus, Event,
    LOCATION_CREATED, SCORE_CHANGED, COMPETITOR_ADDED, MOBILITY_UPDATED,
)

__all__ = [
    "EventBus", "event_bus", "Event",
    "LOCATION_CREATED", "SCORE_CHANGED", "COMPETITOR_ADDED", "MOBILITY_UPDATED",
]
