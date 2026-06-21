"""Feature vector assembly + optional Redis caching.

Combines spatial, temporal, and competition feature extractors into a single
versioned vector, validates it against the registry, and caches hot vectors in
Redis (best-effort; degrades gracefully if Redis is down).
"""
import json
import logging
from typing import Dict, Any, Optional

from backend.app.feature_store.spatial_features import extract_spatial_features
from backend.app.feature_store.temporal_features import extract_temporal_features
from backend.app.feature_store.competition_features import extract_competition_features
from backend.app.feature_store.registry import registry

logger = logging.getLogger(__name__)

FEATURE_VERSION = "1.0"
CACHE_TTL_S = 3600


def build_feature_vector(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the full feature vector from raw collected data."""
    vector: Dict[str, Any] = {}
    vector.update(extract_spatial_features(raw))
    vector.update(extract_temporal_features(raw))
    vector.update(extract_competition_features(raw))

    unknown = registry.validate(vector)
    if unknown:
        logger.warning("Feature vector contains unregistered features: %s", unknown)

    return {
        "version": FEATURE_VERSION,
        "features": vector,
        "groups": {
            "spatial": [s.name for s in registry.list("spatial") if s.name in vector],
            "temporal": [s.name for s in registry.list("temporal") if s.name in vector],
            "competition": [s.name for s in registry.list("competition") if s.name in vector],
        },
    }


def _cache_key(entity_id: str) -> str:
    return f"features:{FEATURE_VERSION}:{entity_id}"


async def get_cached_vector(entity_id: str) -> Optional[Dict[str, Any]]:
    try:
        from backend.app.core.redis import get_redis
        r = await get_redis()
        raw = await r.get(_cache_key(entity_id))
        return json.loads(raw) if raw else None
    except Exception as e:  # noqa: BLE001
        logger.debug("Feature cache read skipped (%s)", e)
        return None


async def cache_vector(entity_id: str, vector: Dict[str, Any], ttl_s: int = CACHE_TTL_S) -> bool:
    try:
        from backend.app.core.redis import get_redis
        r = await get_redis()
        await r.set(_cache_key(entity_id), json.dumps(vector), ex=ttl_s)
        return True
    except Exception as e:  # noqa: BLE001
        logger.debug("Feature cache write skipped (%s)", e)
        return False
