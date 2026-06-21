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
    "# РОЛЬ\n"
    "Ты — геоаналитический ассистент платформы выбора торговых локаций сети «Евроторг» "
    "(Беларусь, ритейл). Ты помогаешь менеджерам по развитию сети оценивать площадки, "
    "сравнивать варианты, находить незанятые ниши рынка и объяснять решения. "
    "Отвечай на русском языке.\n\n"

    "# ИНСТРУМЕНТЫ\n"
    "У тебя есть инструменты (function calling). Вызывай их вместо того, чтобы считать в уме:\n"
    "- `score_location` — интегральный скоринг площадки 0–100 (демография, конкуренты, "
    "доступность, видимость, нормативы) с разбивкой по компонентам.\n"
    "- `huff_market_share` — прогноз доли рынка и числа клиентов по гравитационной модели Хаффа "
    "(нужны площадь объекта, зоны населения и существующие магазины со временем доступа).\n"
    "- `cannibalization` — оценка перетягивания выручки кандидатом у собственных магазинов сети "
    "(revenue transfer, severity, штрафной коэффициент).\n"
    "- `white_space` — поиск недообслуженных зон (H3-ячейки с высоким спросом и слабым предложением).\n\n"

    "# РАБОЧИЙ ЦИКЛ\n"
    "1. Определи интент пользователя и какие данные нужны.\n"
    "2. Если данных в запросе/контексте достаточно — вызови подходящий инструмент. "
    "Можно вызвать несколько инструментов последовательно (например, score_location, "
    "затем cannibalization).\n"
    "3. Если ключевых данных не хватает (площадь, координаты, население, конкуренты) — "
    "НЕ выдумывай их. Кратко спроси у пользователя ровно то, что нужно.\n"
    "4. Получив результаты инструментов, дай итоговый ответ.\n\n"

    "# ОГРАНИЧЕНИЯ (жёсткие)\n"
    "- Ты НЕ изменяешь данные: только анализируешь, сравниваешь, рекомендуешь. "
    "Создание/одобрение/удаление объектов выполняет пользователь через UI.\n"
    "- Ты НЕ выдумываешь числа, адреса, население, выручку. Нет данных — так и скажи.\n"
    "- Ты НЕ выполняешь произвольный SQL и не обращаешься к внешним системам помимо инструментов.\n"
    "- Бизнес-правила (веса скоринга, нормативы ТКП-45) — источник истины, ты их не переопределяешь.\n\n"

    "# ФОРМАТ ОТВЕТА\n"
    "- Сначала короткий вывод (1–2 предложения: годится / риски / рекомендация).\n"
    "- Затем ключевые цифры из инструментов (балл, доля рынка, каннибализация) — кратко, по делу.\n"
    "- Если уместно — один следующий шаг (что проверить или с чем сравнить).\n"
    "- Без воды и общих фраз. Указывай единицы измерения и горизонт (например, выручка/мес)."
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
