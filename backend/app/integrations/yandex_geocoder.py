import logging
from typing import Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.app.core.config import settings
from backend.app.core.exceptions import GeocodeError
from backend.app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

CACHE_TTL = 86400 * 30  # 30 days for geocode results


class YandexGeocoder:
    BASE_URL = "https://geocode-maps.yandex.ru/1.x/"

    def __init__(self):
        self.api_key = settings.YANDEX_GEOCODER_API_KEY

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def geocode(self, address: str) -> Tuple[float, float]:
        """Returns (longitude, latitude) for the given address."""
        cache_key = f"geocode:yandex:{address}"
        cached = await cache_get(cache_key)
        if cached:
            return tuple(cached)

        if not self.api_key:
            raise GeocodeError("Yandex Geocoder API key is not configured")

        params = {
            "apikey": self.api_key,
            "geocode": address,
            "format": "json",
            "results": 1,
            "lang": "ru_RU",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                data = await resp.json()

        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            raise GeocodeError(f"Address not found: {address}")

        pos = features[0]["GeoObject"]["Point"]["pos"]
        lon_str, lat_str = pos.split()
        result = (float(lon_str), float(lat_str))

        await cache_set(cache_key, list(result), CACHE_TTL)
        return result
