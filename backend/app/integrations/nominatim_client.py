"""OpenStreetMap Nominatim geocoder — free, keyless fallback for 2GIS.

Nominatim requires a descriptive User-Agent and rate-limits to ~1 req/s, which
is fine for interactive single-address geocoding. Results cached in Redis 30d.
"""
import logging
from typing import Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.exceptions import GeocodeError
from backend.app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)


class NominatimClient:
    SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    HEADERS = {"User-Agent": "RetailSiteSelection/1.0 (geo-analytics)"}

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def geocode(self, address: str) -> Tuple[float, float]:
        """Returns (lon, lat)."""
        cache_key = f"geocode:osm:{address}"
        cached = await cache_get(cache_key)
        if cached:
            return tuple(cached)

        params = {"q": address, "format": "json", "limit": 1}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(headers=self.HEADERS, timeout=timeout) as session:
            async with session.get(self.SEARCH_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        if not data:
            raise GeocodeError(f"Nominatim: address not found: {address}")

        result = (float(data[0]["lon"]), float(data[0]["lat"]))
        await cache_set(cache_key, list(result), 86400 * 30)
        logger.info("Geocoded via Nominatim: %s → %s", address, result)
        return result
