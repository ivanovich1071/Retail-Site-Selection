"""AI Orchestrator — tool-calling agent over OpenRouter (Qwen).

Runs a bounded ReAct-style loop: the LLM may call retail MCP tools; results are
fed back until it produces a final answer. When OpenRouter is not configured (no
API key), falls back to a deterministic intent classifier + single-tool plan so
the endpoint still works offline.

The agent NEVER mutates data — tools are read/analyse only, matching the
project's "AI augments, business rules decide" principle.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from backend.app.core.config import settings
from backend.app.integrations.openrouter_client import OpenRouterClient, OpenRouterError
from backend.app.mcp.mcp_router import call_tool, list_tools, list_tool_names

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — геоаналитический ассистент для выбора локаций розничной сети «Евроторг». "
    "Используй доступные инструменты (Huff, скоринг, каннибализация, white-space) "
    "для ответа на вопросы о потенциале локаций. Объясняй результаты кратко и по делу. "
    "Никогда не выдумывай числа — если данных нет, скажи об этом. "
    "Ты не изменяешь данные, только анализируешь и рекомендуешь."
)


def classify_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("белые пятна", "white space", "white-space", "дефицит", "недостаточно")):
        return "white_space"
    if any(k in t for k in ("каннибал", "пересеч", "перетяг", "cannibal")):
        return "cannibalization"
    if any(k in t for k in ("доля рынка", "хафф", "huff", "market share")):
        return "huff_market_share"
    if any(k in t for k in ("оцен", "скоринг", "score", "балл", "потенциал")):
        return "score_location"
    return "general"


async def run_agent(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the agent for one user turn. Returns answer + tool trace."""
    context = context or {}
    client = OpenRouterClient()

    if not client.enabled:
        return await _fallback(message, context)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": f"Контекст: {json.dumps(context, ensure_ascii=False)}"})
    messages.extend(history or [])
    messages.append({"role": "user", "content": message})

    tools = list_tools()
    trace: List[Dict[str, Any]] = []

    try:
        for _ in range(settings.AI_MAX_TOOL_ITERATIONS):
            resp = await client.chat(messages, tools=tools)
            choice = resp["choices"][0]["message"]
            messages.append(choice)

            tool_calls = choice.get("tool_calls")
            if not tool_calls:
                return {
                    "answer": choice.get("content", ""),
                    "tool_trace": trace,
                    "model": client.model,
                    "mode": "llm",
                }

            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                envelope = call_tool(name, args)
                trace.append(envelope)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": json.dumps(envelope, ensure_ascii=False, default=str),
                })

        return {
            "answer": "Достигнут лимит итераций инструментов.",
            "tool_trace": trace,
            "model": client.model,
            "mode": "llm",
        }
    except OpenRouterError as e:
        logger.warning("OpenRouter failed (%s); using fallback", e)
        result = await _fallback(message, context)
        result["llm_error"] = str(e)
        return result


async def _fallback(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic plan when the LLM is unavailable."""
    intent = classify_intent(message)
    trace: List[Dict[str, Any]] = []
    answer: str

    if intent in list_tool_names() and context.get("tool_args"):
        envelope = call_tool(intent, context["tool_args"])
        trace.append(envelope)
        answer = (
            f"Выполнен инструмент «{intent}». Результат во вложении (tool_trace)."
            if envelope["ok"] else
            f"Инструмент «{intent}» не выполнен: {envelope['error']}"
        )
    else:
        answer = (
            "AI-модель не настроена (нет OPENROUTER_API_KEY). "
            f"Определён интент: «{intent}». Передайте context.tool_args с параметрами "
            "для запуска соответствующего инструмента, или настройте OpenRouter."
        )

    return {"answer": answer, "tool_trace": trace, "intent": intent, "mode": "fallback"}
