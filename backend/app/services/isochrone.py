import logging
from typing import List, Dict, Any

from backend.app.integrations.openrouteservice_client import OpenRouteServiceClient

logger = logging.getLogger(__name__)


class IsochroneService:
    def __init__(self):
        self.ors = OpenRouteServiceClient()

    async def get_isochrones(
        self,
        lon: float,
        lat: float,
        minutes: List[int] = None,
        mode: str = "walk",
    ) -> Dict[str, Any]:
        """
        Returns ORS GeoJSON FeatureCollection.
        mode: walk | drive
        """
        if minutes is None:
            minutes = [5, 10, 15]

        profile_map = {
            "walk": "foot-walking",
            "drive": "driving-car",
            "bike": "cycling-regular",
        }
        profile = profile_map.get(mode, "foot-walking")
        return await self.ors.get_isochrones(lon, lat, minutes, profile)

    async def get_travel_times_to_competitors(
        self,
        origin_lon: float,
        origin_lat: float,
        competitor_coords: List[Dict],
    ) -> List[float]:
        """
        Returns list of travel times (seconds) to each competitor.
        competitor_coords: [{"lon": ..., "lat": ...}, ...]
        """
        if not competitor_coords:
            return []
        destinations = [[c["lon"], c["lat"]] for c in competitor_coords]
        return await self.ors.get_travel_times([origin_lon, origin_lat], destinations)
