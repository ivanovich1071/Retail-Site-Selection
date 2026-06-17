import json
from typing import Any, Optional

import redis.asyncio as aioredis

from backend.app.core.config import settings

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    value = await r.get(key)
    if value:
        return json.loads(value)
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    r = await get_redis()
    await r.setex(key, ttl_seconds, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
