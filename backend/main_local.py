"""
Lightweight local dev server — no PostgreSQL/Redis required.
Serves the health endpoint and returns stub data for all API routes.
Real backend needs Docker (docker-compose up).
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

logging.basicConfig(level="INFO")

app = FastAPI(
    title="Retail Site Selection API (local stub)",
    description="Stub mode — no DB. For full backend use docker-compose up.",
    version="1.0.0-local",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "mode": "local-stub", "version": "1.0.0"}


# ── Auth stub ────────────────────────────────────────────
@app.post("/api/v1/auth/token")
async def token():
    return {"access_token": "stub-token-local-dev", "token_type": "bearer"}

@app.get("/api/v1/auth/me")
async def me():
    return {"id": 1, "email": "dev@eurotor.by", "full_name": "Dev User", "role": "admin", "is_active": True}


# ── Locations stub ───────────────────────────────────────
STUB_LOCATIONS = [
    {"id": 1, "address": "пр. Независимости 95, Минск", "name": "ТЦ Galileo", "status": "approved",
     "area_sqm": 450, "parking_spaces": 60, "floor_number": 1, "visibility_score": 8.5,
     "notes": None, "photo_path": None, "latitude": 53.9234, "longitude": 27.6251,
     "created_at": "2026-06-01T10:00:00", "updated_at": "2026-06-10T12:00:00"},
    {"id": 2, "address": "ул. Притыцкого 29, Минск", "name": None, "status": "in_review",
     "area_sqm": 280, "parking_spaces": 20, "floor_number": None, "visibility_score": 6.0,
     "notes": "Требует доп. проверки", "photo_path": None, "latitude": 53.9102, "longitude": 27.5043,
     "created_at": "2026-06-05T09:00:00", "updated_at": "2026-06-12T15:30:00"},
    {"id": 3, "address": "ул. Кальварийская 17, Минск", "name": "Рядом с рынком", "status": "draft",
     "area_sqm": 320, "parking_spaces": 35, "floor_number": 0, "visibility_score": 7.2,
     "notes": None, "photo_path": None, "latitude": 53.9178, "longitude": 27.5512,
     "created_at": "2026-06-14T11:20:00", "updated_at": "2026-06-14T11:20:00"},
]

@app.get("/api/v1/locations")
async def list_locations(page: int = 1, page_size: int = 20, status: str = None):
    items = STUB_LOCATIONS if not status else [l for l in STUB_LOCATIONS if l["status"] == status]
    return {"items": items, "total": len(items), "page": page, "page_size": page_size}

@app.get("/api/v1/locations/{location_id}")
async def get_location(location_id: int):
    loc = next((l for l in STUB_LOCATIONS if l["id"] == location_id), None)
    return loc or {"detail": "Not found"}

@app.post("/api/v1/locations", status_code=201)
async def create_location(request: Request):
    body = await request.json()
    return {**STUB_LOCATIONS[0], "id": 99, "address": (body or {}).get("address", "Новый объект")}

@app.patch("/api/v1/locations/{location_id}")
async def update_location(location_id: int, request: Request):
    body = await request.json()
    return STUB_LOCATIONS[0]

@app.delete("/api/v1/locations/{location_id}", status_code=204)
async def delete_location(location_id: int):
    return None

@app.get("/api/v1/locations/{location_id}/scoring")
async def get_scoring(location_id: int):
    return {
        "id": 1, "location_id": location_id, "total_score": 74.5,
        "huff_market_share": 0.083, "cannibalization_risk": 0.0, "revenue_forecast": None,
        "score_demographics": 81.2, "score_competitors": 75.0, "score_accessibility": 68.0,
        "score_visibility": 85.0, "score_location": 70.0, "calculated_at": "2026-06-16T12:00:00",
    }


# ── Analysis stub ────────────────────────────────────────
@app.post("/api/v1/analysis/by-address")
async def analyze_by_address(request: Request):
    body = await request.json()
    address = body.get("address", "Минск")
    return {
        "address": address,
        "latitude": 53.9006,
        "longitude": 27.5615,
        "building_polygon": None,
        "isochrones": [
            {"minutes": 5,  "geometry": {"type": "Polygon", "coordinates": [[[27.55,53.89],[27.57,53.89],[27.57,53.91],[27.55,53.91],[27.55,53.89]]]}, "area_sqkm": 0.8, "population": 3200},
            {"minutes": 10, "geometry": {"type": "Polygon", "coordinates": [[[27.54,53.88],[27.58,53.88],[27.58,53.92],[27.54,53.92],[27.54,53.88]]]}, "area_sqkm": 2.5, "population": 9800},
            {"minutes": 15, "geometry": {"type": "Polygon", "coordinates": [[[27.53,53.87],[27.59,53.87],[27.59,53.93],[27.53,53.93],[27.53,53.87]]]}, "area_sqkm": 5.1, "population": 18500},
        ],
        "competitors_nearby": [
            {"id": 1, "brand_name": "Евроопт", "store_format": "supermarket", "distance_m": 320, "latitude": 53.903, "longitude": 27.565},
            {"id": 2, "brand_name": "Хит!",    "store_format": "discounter",  "distance_m": 680, "latitude": 53.897, "longitude": 27.558},
            {"id": 3, "brand_name": "Магнит",  "store_format": "supermarket", "distance_m": 950, "latitude": 53.905, "longitude": 27.572},
        ],
        "population_in_isochrone": {"5min": 3200, "10min": 9800, "15min": 18500},
        "avg_salary": 1620.0,
        "scoring": {
            "total_score": 74.5,
            "score_demographics": 81.2,
            "score_competitors": 75.0,
            "score_accessibility": 68.0,
            "score_visibility": 70.0,
            "score_location": 70.0,
            "details": {},
        },
        "huff_market_share": 0.083,
        "cannibalization_risk": None,
    }


@app.post("/api/v1/analysis/by-polygon")
async def analyze_by_polygon(request: Request):
    import statistics
    body = await request.json()
    coords = body.get("polygon", {}).get("coordinates", [[]])[0]
    lons = [c[0] for c in coords] or [27.5615]
    lats = [c[1] for c in coords] or [53.9006]
    lat = statistics.mean(lats)
    lon = statistics.mean(lons)
    return {
        "address": f"{lat:.5f},{lon:.5f} (нарисованная зона)",
        "latitude": lat, "longitude": lon,
        "building_polygon": body.get("polygon"),
        "isochrones": [
            {"minutes": 5,  "geometry": {"type": "Polygon", "coordinates": [[[lon-0.01,lat-0.01],[lon+0.01,lat-0.01],[lon+0.01,lat+0.01],[lon-0.01,lat+0.01],[lon-0.01,lat-0.01]]]}, "area_sqkm": 1.2, "population": 4500},
            {"minutes": 10, "geometry": {"type": "Polygon", "coordinates": [[[lon-0.02,lat-0.02],[lon+0.02,lat-0.02],[lon+0.02,lat+0.02],[lon-0.02,lat+0.02],[lon-0.02,lat-0.02]]]}, "area_sqkm": 3.8, "population": 11200},
            {"minutes": 15, "geometry": {"type": "Polygon", "coordinates": [[[lon-0.03,lat-0.03],[lon+0.03,lat-0.03],[lon+0.03,lat+0.03],[lon-0.03,lat+0.03],[lon-0.03,lat-0.03]]]}, "area_sqkm": 7.3, "population": 21000},
        ],
        "competitors_nearby": [
            {"id": 1, "brand_name": "Евроопт", "store_format": "supermarket", "distance_m": 420, "latitude": lat+0.003, "longitude": lon+0.004},
        ],
        "population_in_isochrone": {"5min": 4500, "10min": 11200, "15min": 21000},
        "avg_salary": 1620.0,
        "scoring": {"total_score": 71.0, "score_demographics": 78.0, "score_competitors": 70.0, "score_accessibility": 65.0, "score_visibility": 68.0, "score_location": 70.0, "details": {}},
        "huff_market_share": 0.076, "cannibalization_risk": None,
    }


# ── Batch stub ───────────────────────────────────────────
@app.get("/api/v1/batch")
async def list_batch():
    return []

@app.post("/api/v1/batch/upload", status_code=202)
async def upload_batch():
    return {"id": 1, "file_name": "addresses.xlsx", "status": "pending",
            "total_rows": 0, "processed_rows": 0, "failed_rows": 0,
            "progress_pct": 0, "created_at": "2026-06-16T12:00:00", "completed_at": None}


# ── Reports stub ─────────────────────────────────────────
@app.post("/api/v1/reports/{location_id}/generate")
async def generate_report(location_id: int):
    return {"task_id": "stub-task", "status": "queued"}


# ── Demographics stub ─────────────────────────────────────
STUB_DEMOGRAPHICS = [
    {"region_code": "699961", "region_name": "Республика Беларусь",  "population": 9255524.0, "density_per_km2": 44.6, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919067", "region_name": "Брестская область",    "population": 1358000.0, "density_per_km2": 39.8, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919068", "region_name": "Витебская область",    "population": 1123000.0, "density_per_km2": 26.7, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919069", "region_name": "Гомельская область",   "population": 1389000.0, "density_per_km2": 37.3, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919070", "region_name": "Гродненская область",  "population": 1016000.0, "density_per_km2": 36.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919071", "region_name": "г. Минск",             "population": 2060000.0, "density_per_km2": 6100.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919072", "region_name": "Минская область",      "population": 1536000.0, "density_per_km2": 52.6, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919073", "region_name": "Могилёвская область",  "population": 1020000.0, "density_per_km2": 36.5, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919167", "region_name": "Московский район",     "population": 272000.0,  "density_per_km2": 8200.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919168", "region_name": "Октябрьский район",    "population": 178000.0,  "density_per_km2": 6300.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919169", "region_name": "Партизанский район",   "population": 235000.0,  "density_per_km2": 7800.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919170", "region_name": "Первомайский район",   "population": 196000.0,  "density_per_km2": 5900.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919171", "region_name": "Советский район",      "population": 293000.0,  "density_per_km2": 9100.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919172", "region_name": "Центральный район",    "population": 131000.0,  "density_per_km2": 4400.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919173", "region_name": "Заводской район",      "population": 261000.0,  "density_per_km2": 7200.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919174", "region_name": "Ленинский район",      "population": 248000.0,  "density_per_km2": 6700.0, "last_refreshed": "2026-06-17T08:03:02"},
    {"region_code": "919175", "region_name": "Фрунзенский район",    "population": 246000.0,  "density_per_km2": 6500.0, "last_refreshed": "2026-06-17T08:03:02"},
]

@app.get("/api/v1/demographics/regions")
async def list_demo_regions():
    return STUB_DEMOGRAPHICS

@app.get("/api/v1/demographics/region/{region_code}")
async def get_demo_region(region_code: str):
    row = next((r for r in STUB_DEMOGRAPHICS if r["region_code"] == region_code), None)
    if not row:
        return {"detail": f"Region {region_code!r} not found"}, 404
    return row

@app.post("/api/v1/demographics/refresh")
async def trigger_demo_refresh():
    return {"updated": 0, "failed": 0, "message": "Stub mode: no real refresh. Run scripts/belstat_import.py instead."}
