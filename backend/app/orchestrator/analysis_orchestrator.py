"""Stage-based analysis orchestrator.

Drives a single AnalysisJob through the pipeline, persisting status and
progress after every stage so clients can poll/stream the job. Reuses the
existing domain services (geocode, isochrone, scoring, huff) and the 2GIS
competitor client — the same logic as the synchronous /analysis/by-address
endpoint, but checkpointed and resumable from the DB.
"""
import logging
import statistics
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import GeocodeError
from backend.app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from backend.app.services.geocode import GeocodeService
from backend.app.services.isochrone import IsochroneService
from backend.app.services.scoring import ScoringService
from backend.app.services.huff import HuffService
from backend.app.integrations.twogis_client import TwoGISClient
from backend.app.services.demographics import get_demographics_service

logger = logging.getLogger(__name__)

MINSK_BBOX = (53.80, 54.00, 27.40, 27.75)  # lat_min, lat_max, lon_min, lon_max


class AnalysisOrchestrator:
    async def run(self, job_id: int) -> None:
        """Execute the full pipeline for a job, checkpointing each stage."""
        async with AsyncSessionLocal() as db:
            job = await db.get(AnalysisJob, job_id)
            if job is None:
                logger.error("AnalysisJob %s not found", job_id)
                return

            job.started_at = datetime.now(timezone.utc)
            params = job.input_params or {}

            try:
                geocoder = GeocodeService()
                isochrone_svc = IsochroneService()
                scorer = ScoringService()
                huff = HuffService()
                twogis = TwoGISClient()
                demographics = get_demographics_service(db=db)

                # ── Stage 1: geocoding ──────────────────────────────
                await self._update(db, job, AnalysisJobStatus.geocoding, 10, "Геокодирование")
                lat, lon, address, building = await self._resolve_location(params, geocoder)

                # ── Stage 2: routing (isochrones) ───────────────────
                await self._update(db, job, AnalysisJobStatus.routing, 30, "Изохроны")
                isochrone_data = await self._build_isochrones(isochrone_svc, lon, lat, params)

                # ── Stage 3: collecting (competitors + demography) ──
                await self._update(db, job, AnalysisJobStatus.collecting, 60, "Сбор данных")
                competitors = await self._collect_competitors(twogis, lat, lon)
                population, area = self._estimate_population(isochrone_data, lat, lon, demographics)

                # ── Stage 4: scoring ────────────────────────────────
                await self._update(db, job, AnalysisJobStatus.scoring, 85, "Скоринг")
                score_data = scorer.calculate(
                    population_10min=population,
                    avg_salary=1620.0,
                    competitors_count=len(competitors),
                    nearest_competitor_m=500 if competitors else None,
                    isochrone_area_sqkm=area,
                    parking_spaces=params.get("parking_spaces"),
                    visibility_score=params.get("visibility_score"),
                    area_sqm=params.get("area_sqm"),
                )

                huff_share = None
                if params.get("include_huff") and params.get("area_sqm"):
                    huff_raw = huff.calculate_market_share(
                        candidate_area_sqm=params["area_sqm"],
                        candidate_travel_times=[300],
                        population_zones=[{"population": population, "travel_time_s": 300}],
                        all_stores=[{"area_sqm": 400, "travel_time_s": 450} for _ in competitors[:5]],
                    )
                    huff_share = huff_raw.get("market_share")

                # ── Finalize ────────────────────────────────────────
                result = {
                    "address": address,
                    "latitude": lat,
                    "longitude": lon,
                    "building_polygon": building,
                    "isochrones": isochrone_data,
                    "competitors_nearby": competitors,
                    "population_in_isochrone": {
                        f"{iz['minutes']}min": iz.get("population") or 0 for iz in isochrone_data
                    },
                    "avg_salary": 1620.0,
                    "scoring": {**score_data, "details": {}},
                    "huff_market_share": huff_share,
                    "cannibalization_risk": None,
                }
                job.result = result
                job.completed_at = datetime.now(timezone.utc)
                await self._update(db, job, AnalysisJobStatus.completed, 100, "Готово")
                logger.info("AnalysisJob %s completed (score=%.1f)", job_id, score_data["total_score"])

            except GeocodeError as e:
                await self._fail(db, job, f"Геокодирование не удалось: {e}")
            except Exception as e:  # noqa: BLE001
                logger.exception("AnalysisJob %s failed", job_id)
                await self._fail(db, job, str(e)[:500])

    # ── Stage helpers ───────────────────────────────────────────────

    async def _resolve_location(
        self, params: Dict[str, Any], geocoder: GeocodeService
    ) -> Tuple[float, float, str, Optional[dict]]:
        if params.get("polygon"):
            coords = params["polygon"].get("coordinates", [[]])[0]
            if len(coords) < 3:
                raise ValueError("Polygon must have at least 3 vertices")
            lon = statistics.mean(c[0] for c in coords)
            lat = statistics.mean(c[1] for c in coords)
            return lat, lon, f"{lat:.5f},{lon:.5f} (нарисованная зона)", params["polygon"]

        address = params.get("address")
        if not address:
            raise ValueError("Either address or polygon is required")
        lon, lat = await geocoder.geocode(address)
        return lat, lon, address, None

    async def _build_isochrones(self, svc: IsochroneService, lon, lat, params):
        minutes = params.get("isochrone_minutes") or [5, 10, 15]
        raw = await svc.get_isochrones(lon, lat, minutes, mode="walk")
        out = []
        for feature in raw.get("features", []):
            props = feature.get("properties", {})
            out.append({
                "minutes": int(props.get("value", 0)) // 60,
                "geometry": feature.get("geometry"),
                "area_sqkm": (props.get("area") or 0) / 1_000_000,
                "population": props.get("total_pop"),
            })
        return out

    async def _collect_competitors(self, twogis: TwoGISClient, lat, lon):
        out = []
        try:
            raw = await twogis.search_competitors(lat, lon, radius_m=1500)
            for c in raw[:20]:
                point = c.get("point", {})
                if point:
                    out.append({
                        "id": hash(c.get("id", "")),
                        "brand_name": c.get("name_ex", {}).get("primary", c.get("name", "Unknown")),
                        "store_format": None,
                        "distance_m": 0,
                        "latitude": point.get("lat", 0),
                        "longitude": point.get("lon", 0),
                    })
        except Exception as e:  # noqa: BLE001
            logger.warning("Competitor search failed: %s", e)
        return out

    def _estimate_population(self, isochrone_data, lat, lon, demographics) -> Tuple[int, float]:
        area = sum(iz["area_sqkm"] for iz in isochrone_data if iz["minutes"] <= 10) or 3.14
        population = sum((iz.get("population") or 0) for iz in isochrone_data if iz["minutes"] <= 10)
        if not population:
            lat_min, lat_max, lon_min, lon_max = MINSK_BBOX
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                population = demographics.estimate_population_in_radius(lat, lon, 1.0, "919071")
            else:
                population = 8000
        return population, area

    # ── Persistence helpers ─────────────────────────────────────────

    async def _update(self, db, job, status, pct, stage):
        job.status = status
        job.progress_pct = pct
        job.current_stage = stage
        await db.commit()

    async def _fail(self, db, job, message):
        job.status = AnalysisJobStatus.failed
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def run_analysis_job(job_id: int) -> None:
    await AnalysisOrchestrator().run(job_id)
