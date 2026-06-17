import logging
from typing import List, Dict, Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.config import settings
from backend.app.core.exceptions import IsochroneError
from backend.app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

ISOCHRONE_CACHE_TTL = 86400 * settings.ISOCHRONE_CACHE_TTL_DAYS


class OpenRouteServiceClient:
    BASE_URL = "https://api.openrouteservice.org"

    def __init__(self):
        self.api_key = settings.OPENROUTESERVICE_API_KEY

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
    )
    async def get_isochrones(
        self,
        lon: float,
        lat: float,
        minutes: List[int],
        profile: str = "foot-walking",
    ) -> Dict[str, Any]:
        """
        Returns GeoJSON FeatureCollection with isochrone polygons.
        profile: foot-walking | driving-car | cycling-regular
        """
        cache_key = f"isochrone:{profile}:{lat:.5f}:{lon:.5f}:{'-'.join(map(str, minutes))}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            raise IsochroneError("OpenRouteService API key is not configured")

        url = f"{self.BASE_URL}/v2/isochrones/{profile}"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "locations": [[lon, lat]],
            "range": [m * 60 for m in minutes],  # ORS uses seconds
            "range_type": "time",
            "attributes": ["area", "reachfactor", "total_pop"],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise IsochroneError(f"ORS error {resp.status}: {text}")
                data = await resp.json()

        await cache_set(cache_key, data, ISOCHRONE_CACHE_TTL)
        return data

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
    )
    async def get_travel_times(
        self,
        origin: List[float],
        destinations: List[List[float]],
        profile: str = "driving-car",
    ) -> List[float]:
        """
        Returns travel times in seconds from origin to each destination.
        origin/destinations: [lon, lat]
        """
        if not self.api_key:
            raise IsochroneError("OpenRouteService API key is not configured")

        url = f"{self.BASE_URL}/v2/matrix/{profile}"
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        locations = [origin] + destinations
        payload = {
            "locations": locations,
            "sources": [0],
            "destinations": list(range(1, len(locations))),
            "metrics": ["duration"],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        return data["durations"][0]
