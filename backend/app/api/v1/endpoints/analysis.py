import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.exceptions import GeocodeError, IsochroneError
from backend.app.schemas.analysis import (
    AnalysisByAddressRequest, AnalysisByPolygonRequest, AnalysisResult, ScoringBreakdown,
)
from backend.app.services.geocode import GeocodeService
from backend.app.services.isochrone import IsochroneService
from backend.app.services.scoring import ScoringService
from backend.app.services.huff import HuffService
from backend.app.integrations.twogis_client import TwoGISClient
from backend.app.services.demographics import get_demographics_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/by-address", response_model=AnalysisResult)
async def analyze_by_address(
    body: AnalysisByAddressRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Full synchronous analysis pipeline:
    geocode → isochrones → competitors → scoring → Huff model.
    Heavy computations are cached; typical response time: 2–8 seconds.
    """
    geocoder = GeocodeService()
    isochrone_svc = IsochroneService()
    scorer = ScoringService()
    huff = HuffService()
    twogis = TwoGISClient()
    demographics = get_demographics_service(db=db)

    # Step 1: Geocode
    try:
        lon, lat = await geocoder.geocode(body.address)
    except GeocodeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Step 2: Isochrones (walk)
    isochrones_raw = None
    isochrone_data = []
    try:
        isochrones_raw = await isochrone_svc.get_isochrones(lon, lat, body.isochrone_minutes, mode="walk")
        for feature in isochrones_raw.get("features", []):
            props = feature.get("properties", {})
            isochrone_data.append({
                "minutes": int(props.get("value", 0)) // 60,
                "geometry": feature.get("geometry"),
                "area_sqkm": props.get("area", 0) / 1_000_000,
                "population": props.get("total_pop"),
            })
    except IsochroneError as e:
        logger.warning("Isochrone calculation failed: %s", e)

    # Step 3: Competitors
    competitors_raw = []
    try:
        competitors_raw = await twogis.search_competitors(lat, lon, radius_m=1500)
    except Exception as e:
        logger.warning("Competitor search failed: %s", e)

    competitors_out = []
    for c in competitors_raw[:20]:
        point = c.get("point", {})
        if point:
            competitors_out.append({
                "id": hash(c.get("id", "")),
                "brand_name": c.get("name_ex", {}).get("primary", c.get("name", "Unknown")),
                "store_format": None,
                "distance_m": 0,
                "latitude": point.get("lat", 0),
                "longitude": point.get("lon", 0),
            })

    # Step 4: Demographics — use Belstat data when available, else isochrone estimate
    isochrone_area = sum(iz["area_sqkm"] for iz in isochrone_data if iz["minutes"] <= 10) or 3.14
    population_10min = sum(
        (iz.get("population") or 0) for iz in isochrone_data if iz["minutes"] <= 10
    )
    if not population_10min:
        # Determine likely region from coordinates (simplistic: check if inside Minsk bbox)
        if 53.80 <= lat <= 54.00 and 27.40 <= lon <= 27.75:
            # Minsk city — use density × area estimate
            population_10min = demographics.estimate_population_in_radius(
                lat, lon, radius_km=1.0, region_code="919071"
            )
        else:
            population_10min = 8000  # generic fallback

    # Average salary: Belstat doesn't expose salary via SDMX; use fixed regional estimate
    avg_salary = 1620.0  # BYN, approximate Minsk 2024

    # Step 5: Scoring
    score_data = scorer.calculate(
        population_10min=population_10min,
        avg_salary=avg_salary,
        competitors_count=len(competitors_out),
        nearest_competitor_m=500 if competitors_out else None,
        isochrone_area_sqkm=isochrone_area,
        parking_spaces=body.parking_spaces,
        visibility_score=body.visibility_score,
        area_sqm=body.area_sqm,
    )

    # Step 6: Huff model
    huff_result = None
    if body.include_huff and body.area_sqm:
        huff_raw = huff.calculate_market_share(
            candidate_area_sqm=body.area_sqm,
            candidate_travel_times=[300],
            population_zones=[{"population": population_10min, "travel_time_s": 300}],
            all_stores=[{"area_sqm": 400, "travel_time_s": 450} for _ in competitors_out[:5]],
        )
        huff_result = huff_raw.get("market_share")

    return AnalysisResult(
        address=body.address,
        latitude=lat,
        longitude=lon,
        building_polygon=None,
        isochrones=isochrone_data,
        competitors_nearby=competitors_out,
        population_in_isochrone={str(iz["minutes"]) + "min": iz.get("population") or 0 for iz in isochrone_data},
        avg_salary=avg_salary,
        scoring=ScoringBreakdown(**score_data, details={}),
        huff_market_share=huff_result,
        cannibalization_risk=None,
    )


@router.post("/by-polygon", response_model=AnalysisResult)
async def analyze_by_polygon(
    body: AnalysisByPolygonRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analysis pipeline using a hand-drawn GeoJSON polygon as the study zone.
    Centroid is used for geocoding context; isochrones are built from centroid.
    """
    import statistics

    # Compute polygon centroid from ring coordinates
    coords = body.polygon.get("coordinates", [[]])[0]
    if len(coords) < 3:
        raise HTTPException(status_code=422, detail="Polygon must have at least 3 vertices")

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    lon = statistics.mean(lons)
    lat = statistics.mean(lats)

    isochrone_svc = IsochroneService()
    scorer = ScoringService()
    huff = HuffService()
    twogis = TwoGISClient()
    demographics = get_demographics_service(db=db)

    # Isochrones from centroid
    isochrone_data = []
    try:
        isochrones_raw = await isochrone_svc.get_isochrones(lon, lat, body.isochrone_minutes, mode="walk")
        for feature in isochrones_raw.get("features", []):
            props = feature.get("properties", {})
            isochrone_data.append({
                "minutes": int(props.get("value", 0)) // 60,
                "geometry": feature.get("geometry"),
                "area_sqkm": props.get("area", 0) / 1_000_000,
                "population": props.get("total_pop"),
            })
    except IsochroneError as e:
        logger.warning("Isochrone for polygon centroid failed: %s", e)

    # Competitors near centroid
    competitors_out = []
    try:
        competitors_raw = await twogis.search_competitors(lat, lon, radius_m=1500)
        for c in competitors_raw[:20]:
            point = c.get("point", {})
            if point:
                competitors_out.append({
                    "id": hash(c.get("id", "")),
                    "brand_name": c.get("name_ex", {}).get("primary", c.get("name", "Unknown")),
                    "store_format": None,
                    "distance_m": 0,
                    "latitude": point.get("lat", 0),
                    "longitude": point.get("lon", 0),
                })
    except Exception as e:
        logger.warning("Competitor search failed: %s", e)

    # Population estimate
    isochrone_area = sum(iz["area_sqkm"] for iz in isochrone_data if iz["minutes"] <= 10) or 3.14
    population_10min = sum((iz.get("population") or 0) for iz in isochrone_data if iz["minutes"] <= 10)
    if not population_10min:
        if 53.80 <= lat <= 54.00 and 27.40 <= lon <= 27.75:
            population_10min = demographics.estimate_population_in_radius(lat, lon, 1.0, "919071")
        else:
            population_10min = 8000

    avg_salary = 1620.0

    score_data = scorer.calculate(
        population_10min=population_10min,
        avg_salary=avg_salary,
        competitors_count=len(competitors_out),
        nearest_competitor_m=500 if competitors_out else None,
        isochrone_area_sqkm=isochrone_area,
        parking_spaces=body.parking_spaces,
        visibility_score=body.visibility_score,
        area_sqm=body.area_sqm,
    )

    huff_result = None
    if body.include_huff and body.area_sqm:
        huff_raw = huff.calculate_market_share(
            candidate_area_sqm=body.area_sqm,
            candidate_travel_times=[300],
            population_zones=[{"population": population_10min, "travel_time_s": 300}],
            all_stores=[{"area_sqm": 400, "travel_time_s": 450} for _ in competitors_out[:5]],
        )
        huff_result = huff_raw.get("market_share")

    centroid_label = f"{lat:.5f},{lon:.5f} (нарисованная зона)"

    return AnalysisResult(
        address=centroid_label,
        latitude=lat,
        longitude=lon,
        building_polygon=body.polygon,
        isochrones=isochrone_data,
        competitors_nearby=competitors_out,
        population_in_isochrone={str(iz["minutes"]) + "min": iz.get("population") or 0 for iz in isochrone_data},
        avg_salary=avg_salary,
        scoring=ScoringBreakdown(**score_data, details={}),
        huff_market_share=huff_result,
        cannibalization_risk=None,
    )
