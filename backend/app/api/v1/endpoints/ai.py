"""AI Orchestrator API — chat, approved tool actions, location context."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.location import Location
from backend.app.models.scoring_result import ScoringResult
from backend.app.schemas.ai import (
    ChatRequest, ChatResponse, ActionRequest, ActionResponse,
)
from backend.app.orchestrator.ai_agent import run_agent
from backend.app.mcp.mcp_router import call_tool, list_tools

router = APIRouter()


@router.get("/tools")
async def get_tools():
    return {"tools": list_tools()}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.history] if req.history else None
    return await run_agent(req.message, context=req.context, history=history)


@router.post("/action", response_model=ActionResponse)
async def action(req: ActionRequest):
    """Run a single approved tool directly (no LLM)."""
    return call_tool(req.tool, req.args)


@router.get("/context/{location_id}")
async def location_context(location_id: int, db: AsyncSession = Depends(get_db)):
    """Assemble AI-ready context for a location: attributes + latest scoring."""
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    result = await db.execute(
        select(ScoringResult)
        .where(ScoringResult.location_id == location_id)
        .order_by(ScoringResult.calculated_at.desc())
        .limit(1)
    )
    scoring = result.scalar_one_or_none()

    ctx = {
        "location": {
            c.name: getattr(loc, c.name)
            for c in loc.__table__.columns
            if c.name not in ("geom", "building_polygon")
        },
    }
    if scoring:
        ctx["scoring"] = {
            "total_score": scoring.total_score,
            "calculated_at": str(scoring.calculated_at),
        }
    return ctx
