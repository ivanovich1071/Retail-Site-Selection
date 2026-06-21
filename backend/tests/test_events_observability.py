import asyncio

from backend.app.events.event_bus import EventBus, Event, emit, SCORE_CHANGED
from backend.app.observability.metrics import _FallbackMetrics


# ── event bus ────────────────────────────────────────────────────────
def test_subscribe_and_dispatch():
    bus = EventBus()
    received = []

    async def handler(ev: Event):
        received.append(ev.payload)

    bus.subscribe("test.event", handler)
    asyncio.run(bus.publish(Event(type="test.event", payload={"x": 1})))
    assert received == [{"x": 1}]


def test_recent_buffer():
    bus = EventBus()
    asyncio.run(bus.publish(Event(type="a", payload={})))
    asyncio.run(bus.publish(Event(type="b", payload={})))
    recent = bus.recent()
    assert len(recent) == 2
    assert recent[-1]["type"] == "b"


def test_handler_exception_does_not_break_publish():
    bus = EventBus()

    async def bad(ev):
        raise ValueError("boom")

    bus.subscribe("x", bad)
    # should not raise
    res = asyncio.run(bus.publish(Event(type="x")))
    assert res["published"] is True


def test_emit_helper(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "EVENTS_ENABLED", False)
    res = asyncio.run(emit(SCORE_CHANGED, location_id=1, old_score=50, new_score=60))
    assert res["type"] == SCORE_CHANGED
    assert res["transport"] == "buffer"


# ── metrics ──────────────────────────────────────────────────────────
def test_fallback_metrics_render():
    m = _FallbackMetrics()
    m.observe("GET", "/api/v1/health", 200, 0.01)
    m.observe("GET", "/api/v1/health", 200, 0.02)
    out = m.render()
    assert "http_requests_total" in out
    assert 'method="GET"' in out
    assert "http_request_duration_seconds_count" in out
