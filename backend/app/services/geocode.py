import logging
from typing import Tuple

from backend.app.core.exceptions import GeocodeError
from backend.app.integrations.twogis_client import TwoGISClient

logger = logging.getLogger(__name__)


class GeocodeService:
    """Geocode via 2GIS API (primary and only source)."""

    def __init__(self):
        self.twogis = TwoGISClient()

    async def geocode(self, address: str) -> Tuple[float, float]:
        """Returns (longitude, latitude)."""
        try:
            return await self.twogis.geocode(address)
        except GeocodeError:
            raise GeocodeError(f"Could not geocode address: {address}")
