import logging
from typing import List, Dict, Any, Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.config import settings
from backend.app.core.exceptions import ExternalAPIError, GeocodeError
from backend.app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)


class TwoGISClient:
    GEOCODE_URL = "https://catalog.api.2gis.com/3.0/items/geocode"
    SEARCH_URL = "https://catalog.api.2gis.com/3.0/items"

    RETAIL_RUBRICS = [
        "64",    # Продукты
        "3306",  # Супермаркеты
        "3307",  # Гипермаркеты
        "3308",  # Минимаркеты
    ]

    def __init__(self):
        self.api_key = settings.TWOGIS_API_KEY

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
    )
    async def geocode(self, address: str) -> Tuple[float, float]:
        """Geocode via 2GIS as fallback. Returns (lon, lat)."""
        cache_key = f"geocode:2gis:{address}"
        cached = await cache_get(cache_key)
        if cached:
            return tuple(cached)

        if not self.api_key:
            raise GeocodeError("2GIS API key is not configured")

        params = {"q": address, "key": self.api_key, "fields": "items.point"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.GEOCODE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        items = data.get("result", {}).get("items", [])
        if not items or "point" not in items[0]:
            raise GeocodeError(f"2GIS: address not found: {address}")

        point = items[0]["point"]
        result = (point["lon"], point["lat"])
        await cache_set(cache_key, list(result), 86400 * 30)
        return result

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
    )
    async def search_competitors(
        self,
        lat: float,
        lon: float,
        radius_m: int = 1500,
    ) -> List[Dict[str, Any]]:
        """Find retail competitors within radius around a point."""
        cache_key = f"competitors:2gis:{lat:.4f}:{lon:.4f}:{radius_m}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            raise ExternalAPIError("2GIS API key is not configured")

        all_results = []
        for rubric_id in self.RETAIL_RUBRICS:
            params = {
                "q": "магазин продукты",
                "point": f"{lon},{lat}",
                "radius": radius_m,
                "rubric_id": rubric_id,
                "key": self.api_key,
                "fields": "items.point,items.address,items.name_ex,items.rubrics,items.floor_count",
                "page_size": 50,
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(self.SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("result", {}).get("items", [])
                        all_results.extend(items)

        # Deduplicate by 2GIS ID
        seen = set()
        unique = []
        for item in all_results:
            item_id = item.get("id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                unique.append(item)

        await cache_set(cache_key, unique, 3600 * 24)  # 1 day
        return unique
