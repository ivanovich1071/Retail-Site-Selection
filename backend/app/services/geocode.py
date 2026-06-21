import asyncio
import logging
from typing import Tuple

from backend.app.core.exceptions import GeocodeError
from backend.app.integrations.twogis_client import TwoGISClient
from backend.app.integrations.nominatim_client import NominatimClient

logger = logging.getLogger(__name__)


class GeocodeService:
    """Geocode via 2GIS (primary) with OpenStreetMap Nominatim fallback.

    2GIS gives the best Belarus coverage but needs a key and network access;
    when it's unconfigured or unreachable we fall back to keyless Nominatim so
    geocoding keeps working.
    """

    def __init__(self):
        self.twogis = TwoGISClient()
        self.nominatim = NominatimClient()

    async def _try(self, provider, name: str, address: str):
        """Call one geocoder; treat any failure as 'try next'.

        aiohttp implements timeouts by cancelling the current task, so a connect
        timeout surfaces as asyncio.CancelledError (a BaseException that a plain
        `except Exception` misses). We catch it here so the fallback chain works;
        the job runs in its own background task, so swallowing it is safe.
        """
        try:
            return await provider.geocode(address)
        except asyncio.CancelledError:
            asyncio.current_task().uncancel()
            logger.warning("%s geocode timed out/cancelled; trying fallback", name)
            return None
        except Exception as e:  # noqa: BLE001 — key missing, network, not found
            logger.warning("%s geocode failed (%s); trying fallback", name, e)
            return None

    async def geocode(self, address: str) -> Tuple[float, float]:
        """Returns (longitude, latitude)."""
        for provider, name in ((self.twogis, "2GIS"), (self.nominatim, "Nominatim")):
            result = await self._try(provider, name, address)
            if result:
                return result
        raise GeocodeError(f"Could not geocode address: {address}")
