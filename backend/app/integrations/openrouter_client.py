"""OpenRouter chat-completions client (OpenAI-compatible) for the AI orchestrator.

Defaults to the Qwen model configured in settings. Supports tool/function
calling. Raises a clear error when no API key is configured so the agent can
fall back to a deterministic plan.
"""
import logging
from typing import List, Dict, Any, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, model: Optional[str] = None):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        self.model = model or settings.OPENROUTER_MODEL
        self.timeout = settings.OPENROUTER_TIMEOUT_S

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
    )
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Return the raw OpenRouter response (choices[0].message of interest)."""
        if not self.enabled:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ivanovich1071/Retail-Site-Selection",
            "X-Title": "Retail GeoAI",
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise OpenRouterError(f"OpenRouter {resp.status}: {text[:300]}")
                return await resp.json()
