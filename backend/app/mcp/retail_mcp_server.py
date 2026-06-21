"""Custom Retail MCP tools — Huff, scoring, cannibalization, white-space.

Each tool is a pure function over JSON args returning a JSON-serialisable dict,
plus an OpenAI/OpenRouter tool schema. The orchestrator advertises these schemas
to the LLM and dispatches tool calls back here.
"""
import logging
from typing import Dict, Any, List, Callable

from backend.app.services.huff import HuffService
from backend.app.services.scoring import ScoringService
from backend.app.competition.cannibalization import estimate_cannibalization
from backend.app.competition.white_space import detect_white_space

logger = logging.getLogger(__name__)


def tool_huff_market_share(args: Dict[str, Any]) -> Dict[str, Any]:
    huff = HuffService(beta=args.get("beta"))
    return huff.calculate_market_share(
        candidate_area_sqm=args["candidate_area_sqm"],
        candidate_travel_times=args.get("candidate_travel_times", []),
        population_zones=args["population_zones"],
        all_stores=args.get("all_stores", []),
    )


def tool_score_location(args: Dict[str, Any]) -> Dict[str, Any]:
    scoring = ScoringService()
    return scoring.calculate(
        population_10min=args.get("population_10min", 0),
        avg_salary=args.get("avg_salary", 1000),
        competitors_count=args.get("competitors_count", 0),
        nearest_competitor_m=args.get("nearest_competitor_m"),
        isochrone_area_sqkm=args.get("isochrone_area_sqkm", 1.0),
        parking_spaces=args.get("parking_spaces"),
        visibility_score=args.get("visibility_score"),
        area_sqm=args.get("area_sqm"),
        has_cannibalization=args.get("has_cannibalization", False),
    )


def tool_cannibalization(args: Dict[str, Any]) -> Dict[str, Any]:
    return estimate_cannibalization(
        candidate=args["candidate"],
        own_stores=args.get("own_stores", []),
        beta=args.get("beta"),
    )


def tool_white_space(args: Dict[str, Any]) -> Dict[str, Any]:
    res = detect_white_space(
        cells=args["cells"],
        min_score=args.get("min_score", 40.0),
        limit=args.get("limit", 20),
    )
    res.pop("all_cells", None)
    return res


# name → (callable, schema)
TOOLS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "huff_market_share": tool_huff_market_share,
    "score_location": tool_score_location,
    "cannibalization": tool_cannibalization,
    "white_space": tool_white_space,
}


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "huff_market_share",
            "description": "Estimate market share / captured customers for a candidate store using the Huff gravity model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_area_sqm": {"type": "number"},
                    "population_zones": {"type": "array", "items": {"type": "object"}},
                    "all_stores": {"type": "array", "items": {"type": "object"}},
                    "beta": {"type": "number"},
                },
                "required": ["candidate_area_sqm", "population_zones"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_location",
            "description": "Compute a 0-100 retail site score with component breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "population_10min": {"type": "integer"},
                    "avg_salary": {"type": "number"},
                    "competitors_count": {"type": "integer"},
                    "nearest_competitor_m": {"type": "number"},
                    "isochrone_area_sqkm": {"type": "number"},
                    "area_sqm": {"type": "number"},
                },
                "required": ["population_10min", "competitors_count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cannibalization",
            "description": "Estimate revenue cannibalization of a candidate against existing own stores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "object"},
                    "own_stores": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["candidate"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "white_space",
            "description": "Find under-served (white-space) H3 cells with demand but weak supply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cells": {"type": "array", "items": {"type": "object"}},
                    "min_score": {"type": "number"},
                    "limit": {"type": "integer"},
                },
                "required": ["cells"],
            },
        },
    },
]
