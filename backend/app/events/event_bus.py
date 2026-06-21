"""Event bus backed by Redis Streams with an in-process fallback."""
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Callable, Awaitable, Deque

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Event type constants
LOCATION_CREATED = "location.created"
SCORE_CHANGED = "score.changed"
COMPETITOR_ADDED = "competitor.added"
MOBILITY_UPDATED = "mobility.updated"

Handler = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)
        self._buffer: Deque[Event] = deque(maxlen=1000)  # in-process fallback / audit tail

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def stream_key(self, event_type: str) -> str:
        return f"{settings.EVENT_STREAM_PREFIX}:{event_type}"

    async def publish(self, event: Event) -> Dict[str, Any]:
        """Append to Redis stream (best-effort) and dispatch to handlers."""
        self._buffer.append(event)
        delivered = "buffer"

        if settings.EVENTS_ENABLED:
            try:
                from backend.app.core.redis import get_redis
                r = await get_redis()
                await r.xadd(
                    self.stream_key(event.type),
                    {"data": json.dumps(event.to_dict(), default=str)},
                    maxlen=10000, approximate=True,
                )
                delivered = "redis"
            except Exception as e:  # noqa: BLE001
                logger.debug("Event stream publish skipped (%s)", e)

        await self._dispatch(event)
        return {"published": True, "type": event.type, "transport": delivered}

    async def _dispatch(self, event: Event) -> None:
        for handler in self._handlers.get(event.type, []):
            try:
                await handler(event)
            except Exception:  # noqa: BLE001
                logger.exception("Event handler failed for %s", event.type)

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in list(self._buffer)[-limit:]]


event_bus = EventBus()


async def emit(event_type: str, **payload) -> Dict[str, Any]:
    """Convenience publisher."""
    return await event_bus.publish(Event(type=event_type, payload=payload))
