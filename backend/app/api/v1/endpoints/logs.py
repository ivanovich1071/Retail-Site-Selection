"""Client log sink — frontend posts logs here so they land in the backend file."""
import logging
from typing import List, Optional, Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.core.logging_config import frontend_logger

router = APIRouter()

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class ClientLog(BaseModel):
    level: str = "info"
    message: str
    context: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    ts: Optional[str] = None


class ClientLogBatch(BaseModel):
    logs: List[ClientLog] = Field(default_factory=list)


@router.post("/client")
async def ingest_client_logs(batch: ClientLogBatch):
    for entry in batch.logs:
        level = _LEVELS.get(entry.level.lower(), logging.INFO)
        extra = ""
        if entry.url:
            extra += f" url={entry.url}"
        if entry.context:
            extra += f" ctx={entry.context}"
        frontend_logger.log(level, "%s%s", entry.message, extra)
    return {"received": len(batch.logs)}
