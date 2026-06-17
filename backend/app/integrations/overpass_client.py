import logging
from typing import Optional, Dict, Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.config import settings
from backend.app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)


class OverpassClient:
    def __init__(self):
        self.url = settings.OVERPASS_API_URL

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def query(self, ql: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url,
                data={"data": ql},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_building_at(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch the OSM building polygon closest to a coordinate."""
        cache_key = f"osm:building:{lat:.5f}:{lon:.5f}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        ql = f"""
        [out:json][timeout:25];
        (
          way["building"](around:50,{lat},{lon});
          relation["building"](around:50,{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        data = await self.query(ql)

        if not data.get("elements"):
            return None

        result = data  # Return raw OSM data; geometry_utils will convert
        await cache_set(cache_key, result, 86400 * 7)
        return result

    async def get_nearby_parking(self, lat: float, lon: float, radius_m: int = 300) -> Dict[str, Any]:
        """Fetch parking areas and amenities near a point."""
        cache_key = f"osm:parking:{lat:.4f}:{lon:.4f}:{radius_m}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        ql = f"""
        [out:json][timeout:20];
        (
          node["amenity"="parking"](around:{radius_m},{lat},{lon});
          way["amenity"="parking"](around:{radius_m},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        data = await self.query(ql)
        await cache_set(cache_key, data, 86400 * 3)
        return data
