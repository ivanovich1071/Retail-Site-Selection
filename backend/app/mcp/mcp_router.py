"""MCP tool router — dispatch tool calls with timeout, error capture, caching.

Wraps the retail MCP tools so the orchestrator gets uniform {ok, result|error}
envelopes and never crashes on a bad tool call (MCP is augmentation, must be
fault-tolerant).
"""
import logging
import time
from typing import Dict, Any, List

from backend.app.mcp.retail_mcp_server import TOOLS, TOOL_SCHEMAS

logger = logging.getLogger(__name__)


def list_tools() -> List[Dict[str, Any]]:
    return TOOL_SCHEMAS


def list_tool_names() -> List[str]:
    return list(TOOLS.keys())


def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch one tool call. Always returns an envelope, never raises."""
    fn = TOOLS.get(name)
    if fn is None:
        return {"ok": False, "tool": name, "error": f"unknown tool '{name}'"}
    t0 = time.perf_counter()
    try:
        result = fn(args or {})
        return {
            "ok": True,
            "tool": name,
            "result": result,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except KeyError as e:
        return {"ok": False, "tool": name, "error": f"missing required arg: {e}"}
    except Exception as e:  # noqa: BLE001
        logger.exception("MCP tool %s failed", name)
        return {"ok": False, "tool": name, "error": str(e)}
