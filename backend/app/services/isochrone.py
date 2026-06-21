import asyncio
import logging
from typing import List, Dict, Any

from backend.app.integrations.openrouteservice_client import OpenRouteServiceClient
from backend.app.services.isochrone_osmnx import fallback_isochrones

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
        Returns a GeoJSON FeatureCollection of isochrone polygons.
        Primary source is OpenRouteService; on failure (rate limit, no key,
        network error) falls back to OSMnx/radius approximation so the pipeline
        always has reachability geometry.
        mode: walk | drive | bike
        """
        if minutes is None:
            minutes = [5, 10, 15]

        profile_map = {
            "walk": "foot-walking",
            "drive": "driving-car",
            "bike": "cycling-regular",
        }
        profile = profile_map.get(mode, "foot-walking")

        try:
            return await self.ors.get_isochrones(lon, lat, minutes, profile)
        except asyncio.CancelledError:
            # aiohttp connect timeouts surface as CancelledError (BaseException).
            asyncio.current_task().uncancel()
            logger.warning("ORS isochrones timed out/cancelled; using fallback")
            return await asyncio.to_thread(fallback_isochrones, lon, lat, minutes, mode)
        except Exception as e:  # noqa: BLE001 — incl. IsochroneError, network errors
            logger.warning("ORS isochrones failed (%s); using fallback", e)
            # OSMnx / radius work is sync and CPU/IO bound — run in a thread.
            return await asyncio.to_thread(fallback_isochrones, lon, lat, minutes, mode)

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
