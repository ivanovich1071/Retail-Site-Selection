"""Fallback isochrone generation when OpenRouteService is unavailable.

Two layers, tried in order:
1. OSMnx network-based isochrone (accurate, but heavy — needs `osmnx`).
2. Radius buffer approximation (instant, always available via Shapely).

Both return a GeoJSON FeatureCollection shaped like the ORS response so the
analysis pipeline can consume them interchangeably (properties.value in
seconds, properties.area in m², geometry a Polygon).
"""
import logging
import math
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Approximate travel speeds (metres per minute).
SPEED_M_PER_MIN = {
    "walk": 83.0,    # ~5 km/h
    "drive": 500.0,  # ~30 km/h urban
    "bike": 250.0,   # ~15 km/h
}


def _circle_polygon(lon: float, lat: float, radius_m: float, n: int = 48) -> List[List[float]]:
    """Build a closed ring approximating a circle of radius_m around (lon, lat)."""
    lat_deg_per_m = 1.0 / 111_320.0
    lon_deg_per_m = 1.0 / (111_320.0 * math.cos(math.radians(lat)) or 1e-9)
    ring = []
    for i in range(n):
        theta = 2 * math.pi * i / n
        dx = radius_m * math.cos(theta) * lon_deg_per_m
        dy = radius_m * math.sin(theta) * lat_deg_per_m
        ring.append([lon + dx, lat + dy])
    ring.append(ring[0])
    return ring


def radius_isochrones(
    lon: float, lat: float, minutes: List[int], mode: str = "walk"
) -> Dict[str, Any]:
    """Circular buffer approximation. Always succeeds."""
    speed = SPEED_M_PER_MIN.get(mode, SPEED_M_PER_MIN["walk"])
    features = []
    for m in sorted(minutes):
        radius_m = speed * m
        ring = _circle_polygon(lon, lat, radius_m)
        area = math.pi * radius_m ** 2
        features.append({
            "type": "Feature",
            "properties": {"value": m * 60, "area": area, "total_pop": None, "fallback": "radius"},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    logger.info("Radius-fallback isochrones generated for %s minutes (mode=%s)", minutes, mode)
    return {"type": "FeatureCollection", "features": features}


def osmnx_isochrones(
    lon: float, lat: float, minutes: List[int], mode: str = "walk"
) -> Dict[str, Any]:
    """Network-based isochrone via OSMnx. Raises if osmnx is unavailable."""
    import osmnx as ox
    import networkx as nx
    from shapely.geometry import Point
    from shapely.ops import unary_union

    network_type = {"walk": "walk", "drive": "drive", "bike": "bike"}.get(mode, "walk")
    speed = SPEED_M_PER_MIN.get(mode, SPEED_M_PER_MIN["walk"])
    max_minutes = max(minutes)
    max_dist_m = speed * max_minutes

    graph = ox.graph_from_point((lat, lon), dist=max_dist_m * 1.3, network_type=network_type)
    center_node = ox.distance.nearest_nodes(graph, lon, lat)

    for u, v, _, data in graph.edges(keys=True, data=True):
        data["time_min"] = data.get("length", 0) / speed

    features = []
    for m in sorted(minutes):
        subgraph = nx.ego_graph(graph, center_node, radius=m, distance="time_min")
        node_points = [Point(graph.nodes[n]["x"], graph.nodes[n]["y"]) for n in subgraph.nodes]
        if len(node_points) < 3:
            continue
        hull = unary_union(node_points).convex_hull
        features.append({
            "type": "Feature",
            "properties": {"value": m * 60, "area": None, "total_pop": None, "fallback": "osmnx"},
            "geometry": hull.__geo_interface__,
        })
    if not features:
        raise RuntimeError("OSMnx produced no reachable polygons")
    logger.info("OSMnx isochrones generated for %s minutes (mode=%s)", minutes, mode)
    return {"type": "FeatureCollection", "features": features}


def fallback_isochrones(
    lon: float, lat: float, minutes: List[int], mode: str = "walk"
) -> Dict[str, Any]:
    """Try OSMnx, fall back to radius buffer."""
    try:
        return osmnx_isochrones(lon, lat, minutes, mode)
    except Exception as e:  # ImportError, network errors, empty hull
        logger.warning("OSMnx fallback unavailable (%s); using radius buffer", e)
        return radius_isochrones(lon, lat, minutes, mode)
