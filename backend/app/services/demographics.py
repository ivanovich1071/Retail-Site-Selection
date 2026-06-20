"""
Demographics service.

Fetches and stores regional population data from Belstat, then exposes
query methods used by the analysis pipeline (population near a point,
average salary proxy, etc.).

Data is stored in the `demographics_zones` table (DemographicsZone model).
Without DB (local stub mode) the service operates in memory-only mode.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from backend.app.integrations.belstat_client import (
    BelstatClient,
    BelstatError,
    DEFAULT_REGION_CODES,
    REGIONS,
)

logger = logging.getLogger(__name__)

# Minsk district codes — we always refresh these (highest spatial resolution)
MINSK_DISTRICT_CODES = [str(c) for c in range(919167, 919176)]
OBLAST_CODES = ["919067", "919068", "919069", "919070", "919071", "919072", "919073"]
ALL_CODES = DEFAULT_REGION_CODES


class DemographicsService:
    """
    Fetch population / density from Belstat and expose query helpers.

    In production (with DB) call `refresh_from_belstat()` periodically via
    Celery Beat, then query via `get_population_for_region()`.

    In stub/no-DB mode the in-memory cache populated by `refresh_from_belstat()`
    is used directly.
    """

    def __init__(self, db=None):
        self._db = db
        # In-memory cache: {region_code: {year: value}}
        self._pop_cache: Dict[str, Dict[int, Optional[float]]] = {}
        self._density_cache: Dict[str, Dict[int, Optional[float]]] = {}
        self._last_refresh: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Belstat refresh
    # ------------------------------------------------------------------

    async def refresh_from_belstat(
        self,
        region_codes: Optional[List[str]] = None,
        years: Optional[List[int]] = None,
    ) -> Dict[str, int]:
        """
        Pull latest data from Belstat and update in-memory cache (+ DB if available).

        Returns summary counts: {"updated": N, "failed": 0}.
        """
        codes = region_codes or ALL_CODES
        current_year = date.today().year
        fetch_years = years or [current_year - 2, current_year - 1, current_year]

        async with BelstatClient() as client:
            try:
                pop = await client.get_population(codes, fetch_years)
                density = await client.get_density(codes, fetch_years)
            except BelstatError as exc:
                logger.error("Belstat fetch failed: %s", exc)
                return {"updated": 0, "failed": len(codes)}

        self._pop_cache.update(pop)
        self._density_cache.update(density)
        self._last_refresh = datetime.utcnow()

        updated = sum(
            1 for code in codes
            if any(v is not None for v in pop.get(code, {}).values())
        )
        logger.info(
            "Belstat refresh complete: %d/%d regions updated for years %s",
            updated, len(codes), fetch_years,
        )

        if self._db is not None:
            await self._persist_to_db(pop, density, fetch_years)

        return {"updated": updated, "failed": len(codes) - updated}

    # ------------------------------------------------------------------
    # Query helpers used by analysis pipeline
    # ------------------------------------------------------------------

    def get_population_for_region(
        self, region_code: str, year: Optional[int] = None
    ) -> Optional[float]:
        """Return latest available population for a region code."""
        data = self._pop_cache.get(region_code, {})
        if not data:
            return None
        if year and year in data:
            return data[year]
        # Return most recent non-null value
        for y in sorted(data.keys(), reverse=True):
            if data[y] is not None:
                return data[y]
        return None

    def get_density_for_region(
        self, region_code: str, year: Optional[int] = None
    ) -> Optional[float]:
        data = self._density_cache.get(region_code, {})
        if not data:
            return None
        if year and year in data:
            return data[year]
        for y in sorted(data.keys(), reverse=True):
            if data[y] is not None:
                return data[y]
        return None

    def estimate_population_in_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float = 1.0,
        region_code: str = "919071",  # Minsk by default
    ) -> int:
        """
        Rough estimate of population within `radius_km` of the point.

        Uses district-level density when available, oblast density as fallback.
        Without DB spatial query: density × area.
        """
        density = self.get_density_for_region(region_code)
        if density is None:
            # Use Minsk oblast as fallback
            density = self.get_density_for_region("919071") or 5000.0

        import math
        area_km2 = math.pi * radius_km ** 2
        return int(density * area_km2)

    def get_all_regions_summary(self) -> List[Dict]:
        """Return list of {code, name, population, density} for all cached regions."""
        rows = []
        for code, name in REGIONS.items():
            pop = self.get_population_for_region(code)
            den = self.get_density_for_region(code)
            rows.append({
                "region_code": code,
                "region_name": name,
                "population": pop,
                "density_per_km2": den,
                "last_refreshed": self._last_refresh.isoformat() if self._last_refresh else None,
            })
        return rows

    def is_cache_empty(self) -> bool:
        return not self._pop_cache

    # ------------------------------------------------------------------
    # DB persistence (production path)
    # ------------------------------------------------------------------

    async def _persist_to_db(
        self,
        pop: Dict[str, Dict[int, Optional[float]]],
        density: Dict[str, Dict[int, Optional[float]]],
        years: List[int],
    ) -> None:
        """Upsert rows into demographics_zones table."""
        if self._db is None:
            return
        try:
            from backend.app.models.demographics import DemographicsZone
            from sqlalchemy import select

            for code, year_data in pop.items():
                for year, population in year_data.items():
                    if population is None:
                        continue
                    den_val = density.get(code, {}).get(year)
                    result = await self._db.execute(
                        select(DemographicsZone).where(
                            DemographicsZone.region_code == code,
                            DemographicsZone.data_year == year,
                        )
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.population = int(population)
                        if den_val is not None:
                            existing.population_density = den_val
                    else:
                        zone = DemographicsZone(
                            region_code=code,
                            region_name=REGIONS.get(code, code),
                            data_year=year,
                            population=int(population),
                            population_density=den_val,
                        )
                        self._db.add(zone)
            await self._db.commit()
        except Exception as exc:
            logger.error("Failed to persist demographics to DB: %s", exc)
            await self._db.rollback()


# Module-level singleton for use without DI (local stub mode)
_default_service: Optional[DemographicsService] = None


def get_demographics_service(db=None) -> DemographicsService:
    global _default_service
    if db is not None:
        return DemographicsService(db=db)
    if _default_service is None:
        _default_service = DemographicsService()
    return _default_service
