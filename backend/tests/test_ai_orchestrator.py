import asyncio

from backend.app.mcp.mcp_router import call_tool, list_tools, list_tool_names
from backend.app.orchestrator.ai_agent import classify_intent, run_agent


# ── MCP router ───────────────────────────────────────────────────────
def test_list_tools_has_schemas():
    tools = list_tools()
    assert tools
    assert all("function" in t for t in tools)
    assert "huff_market_share" in list_tool_names()


def test_call_unknown_tool_returns_error():
    env = call_tool("nope", {})
    assert env["ok"] is False
    assert "unknown" in env["error"]


def test_call_score_tool():
    env = call_tool("score_location", {
        "population_10min": 5000, "competitors_count": 2,
        "isochrone_area_sqkm": 1.0, "avg_salary": 1500,
    })
    assert env["ok"] is True
    assert 0 <= env["result"]["total_score"] <= 100


def test_call_tool_missing_required_arg():
    env = call_tool("huff_market_share", {})  # missing candidate_area_sqm
    assert env["ok"] is False


def test_white_space_tool_strips_all_cells():
    env = call_tool("white_space", {"cells": [{"population": 4000, "competitor_count": 0}]})
    assert env["ok"] is True
    assert "all_cells" not in env["result"]


# ── intent classification ────────────────────────────────────────────
def test_classify_intent():
    assert classify_intent("найди белые пятна в Минске") == "white_space"
    assert classify_intent("посчитай долю рынка Huff") == "huff_market_share"
    assert classify_intent("оцени потенциал локации") == "score_location"
    assert classify_intent("привет") == "general"


# ── agent fallback (no API key) ──────────────────────────────────────
def test_agent_fallback_without_key(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    res = asyncio.run(run_agent("оцени потенциал локации"))
    assert res["mode"] == "fallback"
    assert res["intent"] == "score_location"


def test_agent_fallback_runs_tool_with_args(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    res = asyncio.run(run_agent(
        "оцени локацию",
        context={"tool_args": {
            "population_10min": 5000, "competitors_count": 1, "isochrone_area_sqkm": 1.0,
        }},
    ))
    assert res["mode"] == "fallback"
    assert res["tool_trace"]
    assert res["tool_trace"][0]["ok"] is True
