"""Origin-Destination matrix from staypoint sequences.

Given many trips (each a chronological list of staypoints assigned to zones),
builds an OD matrix counting transitions between zones. Zones are typically H3
cells, but any hashable zone id works.
"""
import logging
from collections import defaultdict
from typing import List, Dict, Any, Callable, Optional

from backend.app.spatial.h3_indexing import lat_lon_to_h3

logger = logging.getLogger(__name__)


def assign_zone(staypoint: Dict[str, Any], resolution: int = 8) -> str:
    return lat_lon_to_h3(staypoint["lat"], staypoint["lon"], resolution)


def build_od_matrix(
    trips: List[List[Dict[str, Any]]],
    zone_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
    resolution: int = 8,
) -> Dict[str, Any]:
    """Build an OD matrix from a list of trips (each a list of staypoints).

    Returns matrix as {origin: {dest: count}} plus inflow/outflow per zone.
    """
    zone_fn = zone_fn or (lambda sp: assign_zone(sp, resolution))
    matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    outflow: Dict[str, int] = defaultdict(int)
    inflow: Dict[str, int] = defaultdict(int)

    for trip in trips:
        zones = [zone_fn(sp) for sp in trip]
        for a, b in zip(zones, zones[1:]):
            if a == b:
                continue
            matrix[a][b] += 1
            outflow[a] += 1
            inflow[b] += 1

    return {
        "matrix": {o: dict(d) for o, d in matrix.items()},
        "inflow": dict(inflow),
        "outflow": dict(outflow),
        "zones": sorted(set(outflow) | set(inflow)),
        "total_trips": sum(v for d in matrix.values() for v in d.values()),
    }


def top_flows(od: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """Largest OD pairs by count."""
    flows = [
        {"origin": o, "destination": d, "count": c}
        for o, dests in od["matrix"].items()
        for d, c in dests.items()
    ]
    flows.sort(key=lambda f: -f["count"])
    return flows[:limit]
