import asyncio
import logging
import re
from typing import Tuple

from backend.app.core.exceptions import GeocodeError
from backend.app.integrations.twogis_client import TwoGISClient
from backend.app.integrations.nominatim_client import NominatimClient

logger = logging.getLogger(__name__)

# Russian street-type abbreviations → full form. Nominatim doesn't expand these
# (e.g. "пр. Рокоссовского" isn't found, "проспект Рокоссовского" is).
_ABBREV = {
    r"\bпр-?т\.?": "проспект",
    r"\bпр\.": "проспект",
    r"\bпросп\.": "проспект",
    r"\bул\.": "улица",
    r"\bпер\.": "переулок",
    r"\bпл\.": "площадь",
    r"\bб-?р\.?": "бульвар",
    r"\bбул\.": "бульвар",
    r"\bш\.": "шоссе",
    r"\bтракт\b": "тракт",
}


def _expand_abbreviations(address: str) -> str:
    out = address
    for pat, full in _ABBREV.items():
        out = re.sub(pat, full, out, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", out).strip()


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

    def _variants(self, address: str) -> list[str]:
        """Address variants tried in order. Users often abbreviate street types
        ("пр.") and omit the city/country, which Nominatim needs — expand the
        abbreviations and append Minsk/Belarus context as fallbacks."""
        bases = [address]
        expanded = _expand_abbreviations(address)
        if expanded.lower() != address.lower():
            bases.append(expanded)

        variants: list[str] = []
        for base in bases:
            low = base.lower()
            variants.append(base)
            if "минск" not in low and "minsk" not in low:
                variants.append(f"{base}, Минск, Беларусь")
            if "беларус" not in low and "belarus" not in low:
                variants.append(f"{base}, Беларусь")

        # Deduplicate, preserve order.
        seen, ordered = set(), []
        for v in variants:
            if v not in seen:
                seen.add(v)
                ordered.append(v)
        return ordered

    async def geocode(self, address: str) -> Tuple[float, float]:
        """Returns (longitude, latitude)."""
        providers = ((self.twogis, "2GIS"), (self.nominatim, "Nominatim"))
        for variant in self._variants(address):
            for provider, name in providers:
                result = await self._try(provider, name, variant)
                if result:
                    return result
        raise GeocodeError(f"Could not geocode address: {address}")
