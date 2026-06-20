"""Aggregate demographics and competitors into H3 cells."""

from typing import List, Dict, Any

from backend.app.spatial.h3_indexing import (
    lat_lon_to_h3, h3_to_center, get_resolution_area_km2, DEFAULT_RESOLUTION,
)


def distribute_population_to_cells(
    region_population: float,
    region_density: float,
    cells: List[str],
    resolution: int = DEFAULT_RESOLUTION,
) -> List[Dict[str, Any]]:
    cell_area_km2 = get_resolution_area_km2(resolution)
    total_cells = len(cells)
    if total_cells == 0:
        return []

    pop_per_cell = region_population / total_cells if region_population else 0

    result = []
    for cell in cells:
        lat, lon = h3_to_center(cell)
        result.append({
            "h3_index": cell,
            "resolution": resolution,
            "center_lat": lat,
            "center_lon": lon,
            "population": round(pop_per_cell),
            "density_per_sqkm": round(region_density or pop_per_cell / cell_area_km2, 1),
            "competitor_count": 0,
        })
    return result


def count_competitors_per_cell(
    competitors: List[Dict[str, Any]],
    resolution: int = DEFAULT_RESOLUTION,
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for comp in competitors:
        lat = comp.get("latitude") or comp.get("lat")
        lon = comp.get("longitude") or comp.get("lon")
        if lat is None or lon is None:
            continue
        cell = lat_lon_to_h3(float(lat), float(lon), resolution)
        counts[cell] = counts.get(cell, 0) + 1
    return counts
