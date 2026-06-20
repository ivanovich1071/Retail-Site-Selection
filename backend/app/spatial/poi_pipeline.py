"""POI ingestion pipeline: OSM Overpass → normalize → deduplicate → competitors.

Pulls retail POIs around a point, maps OSM tags to the internal store-format
taxonomy, removes near-duplicates, and upserts them into the competitors table
with source="osm".
"""
import logging
import math
from typing import List, Dict, Any, Optional

from backend.app.integrations.overpass_client import OverpassClient

logger = logging.getLogger(__name__)

# OSM shop/amenity tag → internal store_format
TAG_TO_FORMAT = {
    "supermarket": "supermarket",
    "convenience": "convenience",
    "grocery": "convenience",
    "general": "convenience",
    "department_store": "hypermarket",
    "mall": "hypermarket",
    "wholesale": "hypermarket",
    "discount": "discounter",
    "marketplace": "market",
}

RETAIL_QL_FILTERS = (
    'node["shop"~"supermarket|convenience|grocery|general|department_store|mall|wholesale"](around:{r},{lat},{lon});'
    'way["shop"~"supermarket|convenience|grocery|general|department_store|mall|wholesale"](around:{r},{lat},{lon});'
    'node["amenity"="marketplace"](around:{r},{lat},{lon});'
)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def fetch_pois(lat: float, lon: float, radius_m: int = 1500) -> List[Dict[str, Any]]:
    """Query Overpass for retail POIs around a point. Returns raw OSM elements."""
    overpass = OverpassClient()
    filters = RETAIL_QL_FILTERS.format(r=radius_m, lat=lat, lon=lon)
    ql = f"[out:json][timeout:25];({filters});out center body;"
    data = await overpass.query(ql)
    return data.get("elements", [])


def normalize_poi(element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a raw OSM element to a competitor dict, or None if it lacks coords."""
    tags = element.get("tags", {})
    # Point coords: nodes have lat/lon; ways/relations have a `center`.
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    if lat is None or lon is None:
        return None

    shop = tags.get("shop") or tags.get("amenity", "")
    store_format = TAG_TO_FORMAT.get(shop, "other")
    name = tags.get("name") or tags.get("brand") or "Без названия"

    address_parts = [
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
        tags.get("addr:city"),
    ]
    address = ", ".join(p for p in address_parts if p) or None

    return {
        "brand_name": name.strip()[:255],
        "store_format": store_format,
        "address": address,
        "latitude": float(lat),
        "longitude": float(lon),
        "source": "osm",
        "external_id": f"{element.get('type', 'node')}/{element.get('id', '')}",
    }


def deduplicate(pois: List[Dict[str, Any]], min_dist_m: float = 50.0) -> List[Dict[str, Any]]:
    """Drop POIs with the same normalized name within min_dist_m of an earlier one."""
    kept: List[Dict[str, Any]] = []
    for poi in pois:
        key = poi["brand_name"].casefold()
        dup = False
        for k in kept:
            if k["brand_name"].casefold() == key:
                d = _haversine_m(poi["latitude"], poi["longitude"], k["latitude"], k["longitude"])
                if d < min_dist_m:
                    dup = True
                    break
        if not dup:
            kept.append(poi)
    return kept


def normalize_and_dedupe(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = [p for p in (normalize_poi(e) for e in elements) if p]
    return deduplicate(normalized)


async def ingest_pois(lat: float, lon: float, radius_m: int, db) -> Dict[str, int]:
    """Fetch, normalize, dedupe, and upsert POIs into competitors. Async session."""
    from sqlalchemy import select
    from geoalchemy2.elements import WKTElement
    from backend.app.models.competitor import Competitor

    elements = await fetch_pois(lat, lon, radius_m)
    pois = normalize_and_dedupe(elements)

    inserted, updated = 0, 0
    for poi in pois:
        result = await db.execute(
            select(Competitor).where(Competitor.external_id == poi["external_id"])
        )
        existing = result.scalar_one_or_none()
        geom = WKTElement(f"POINT({poi['longitude']} {poi['latitude']})", srid=4326)
        if existing:
            existing.brand_name = poi["brand_name"]
            existing.store_format = poi["store_format"]
            existing.address = poi["address"]
            existing.geom = geom
            updated += 1
        else:
            db.add(Competitor(
                brand_name=poi["brand_name"],
                store_format=poi["store_format"],
                address=poi["address"],
                geom=geom,
                source="osm",
                external_id=poi["external_id"],
            ))
            inserted += 1

    await db.commit()
    return {"fetched": len(elements), "deduped": len(pois), "inserted": inserted, "updated": updated}
