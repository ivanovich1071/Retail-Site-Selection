"""
Belstat SDMX-JSON API client.

Endpoint: https://dataportal.belstat.gov.by/osids-public-api/sdmx-api
- GET  /indicator/datastructure/SDMX-JSON/{id}  → dimension/region codes
- POST /indicator/values/SDMX-JSON/{id}          → observation data

SDMX-JSON key format: "region_idx:age_idx:gender_idx:area_idx:unit_idx:time_idx"
time_idx -1 = first year in the request years list.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

BELSTAT_BASE = "https://dataportal.belstat.gov.by/osids-public-api/sdmx-api"

# Indicators used
INDICATOR_POPULATION = "10101100003"   # численность населения, persons
INDICATOR_DENSITY    = "10101100012"   # плотность населения, persons/km²

# Dimension value IDs that mean "total" (all groups combined)
DIM_AGE_ALL    = "518105"  # By all age
DIM_GENDER_ALL = "517378"  # Total (both sexes)
DIM_AREA_ALL   = "507552"  # By all types


# ---------------------------------------------------------------------------
# Region code registry (key codes confirmed via live API, 2026-06-17)
# ---------------------------------------------------------------------------
REGIONS: Dict[str, str] = {
    # Republic total
    "699961": "Республика Беларусь",
    # Oblasts
    "919067": "Брестская область",
    "919068": "Витебская область",
    "919069": "Гомельская область",
    "919070": "Гродненская область",
    "919071": "г. Минск",
    "919072": "Минская область",
    "919073": "Могилёвская область",
    # Minsk city districts (919167–919175)
    "919167": "Московский район",
    "919168": "Октябрьский район",
    "919169": "Партизанский район",
    "919170": "Первомайский район",
    "919171": "Советский район",
    "919172": "Центральный район",
    "919173": "Заводской район",
    "919174": "Ленинский район",
    "919175": "Фрунзенский район",
}

# Codes used for bulk fetch (all defined regions)
DEFAULT_REGION_CODES: List[str] = list(REGIONS.keys())


class BelstatError(Exception):
    pass


class BelstatClient:
    def __init__(self, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=BELSTAT_BASE,
            timeout=timeout,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_structure(self, indicator_id: str) -> Dict[str, Any]:
        """Return the datastructure (dimensions, codes) for an indicator."""
        resp = await self._get(f"/indicator/datastructure/SDMX-JSON/{indicator_id}")
        return resp

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_population(
        self,
        region_codes: List[str],
        years: List[int],
    ) -> Dict[str, Any]:
        """
        Fetch population data for given region codes and years.

        Returns parsed dict: {region_code: {year: population_int}}.
        """
        raw = await self._post_values(INDICATOR_POPULATION, region_codes, years)
        return self._parse_observations(raw, years)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_density(
        self,
        region_codes: List[str],
        years: List[int],
    ) -> Dict[str, Any]:
        """
        Fetch population density data for given region codes and years.

        Returns parsed dict: {region_code: {year: density_float}}.
        """
        raw = await self._post_values(INDICATOR_DENSITY, region_codes, years)
        return self._parse_observations(raw, years)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> Dict[str, Any]:
        try:
            resp = await self._client.get(path)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise BelstatError(f"Belstat HTTP {e.response.status_code}: {path}") from e
        except Exception as e:
            raise BelstatError(f"Belstat request failed: {e}") from e

    async def _post_values(
        self,
        indicator_id: str,
        region_codes: List[str],
        years: List[int],
    ) -> Dict[str, Any]:
        payload = {
            "razrezCodes": region_codes,
            "years": [str(y) for y in years],
        }
        try:
            resp = await self._client.post(
                f"/indicator/values/SDMX-JSON/{indicator_id}",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise BelstatError(
                f"Belstat HTTP {e.response.status_code} for indicator {indicator_id}"
            ) from e
        except Exception as e:
            raise BelstatError(f"Belstat POST failed: {e}") from e

    def _parse_observations(
        self,
        raw: Dict[str, Any],
        years: List[int],
    ) -> Dict[str, Dict[int, Optional[float]]]:
        """
        Parse SDMX-JSON observation block into {region_code: {year: value}}.

        Key format: "region_idx:age_idx:gender_idx:area_idx:unit_idx:time_idx"
        We select rows where age=0 (all), gender=0 (total), area=0 (all), unit=0.
        time_idx: -1 = years[0], 0 = years[1], etc.
        """
        structure = raw.get("structure", {})
        obs = raw.get("dataSets", [{}])[0].get("observations", {})

        # Build region index→code map from dimensions[0]
        dims = structure.get("dimensions", {}).get("observation", [])
        if not dims:
            logger.warning("Belstat: no observation dimensions in response")
            return {}

        region_dim = dims[0]  # razrez_594
        idx_to_code: Dict[int, str] = {
            i: v["id"] for i, v in enumerate(region_dim.get("values", []))
        }

        # Build result skeleton
        result: Dict[str, Dict[int, Optional[float]]] = {
            code: {y: None for y in years} for code in idx_to_code.values()
        }

        # time_idx mapping: -1 → years[0], 0 → years[1], ...
        def time_idx_to_year(t: int) -> Optional[int]:
            if t == -1:
                return years[0] if years else None
            if 0 <= t < len(years) - 1:
                return years[t + 1]
            return None

        for key, values in obs.items():
            parts = key.split(":")
            if len(parts) != 6:
                continue
            region_idx, age_idx, gender_idx, area_idx, unit_idx, time_idx = (
                int(p) for p in parts
            )
            # Only total rows
            if age_idx != 0 or gender_idx != 0 or area_idx != 0 or unit_idx != 0:
                continue

            region_code = idx_to_code.get(region_idx)
            if region_code is None:
                continue

            year = time_idx_to_year(time_idx)
            if year is None:
                continue

            raw_val = values[0] if values else None
            try:
                value = float(raw_val) if raw_val is not None else None
            except (TypeError, ValueError):
                value = None

            if region_code in result:
                result[region_code][year] = value

        return result
