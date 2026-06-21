"""Events API — publish domain events and inspect the recent tail."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from backend.app.events.event_bus import event_bus, Event

router = APIRouter()


class PublishRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/publish")
async def publish_event(req: PublishRequest):
    return await event_bus.publish(Event(type=req.type, payload=req.payload))


@router.get("/recent")
async def recent_events(limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
    return {"events": event_bus.recent(limit)}
