"""H3 spatial indexing — hex grid operations for retail analytics."""

from typing import List, Dict, Any, Tuple
import h3


DEFAULT_RESOLUTION = 9  # ~0.1 km2 per cell, good for urban retail


def lat_lon_to_h3(lat: float, lon: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    return h3.latlng_to_cell(lat, lon, resolution)


def h3_to_center(h3_index: str) -> Tuple[float, float]:
    lat, lon = h3.cell_to_latlng(h3_index)
    return (lat, lon)


def h3_to_geojson(h3_index: str) -> Dict[str, Any]:
    boundary = h3.cell_to_boundary(h3_index)
    coords = [[lon, lat] for lat, lon in boundary]
    coords.append(coords[0])
    return {
        "type": "Polygon",
        "coordinates": [coords],
    }


def polygon_to_h3_cells(
    geojson_polygon: Dict[str, Any],
    resolution: int = DEFAULT_RESOLUTION,
) -> List[str]:
    coords = geojson_polygon["coordinates"][0]
    polygon = h3.LatLngPoly([
        (lat, lon) for lon, lat in coords
    ])
    return list(h3.polygon_to_cells(polygon, resolution))


def get_neighbors(h3_index: str, k: int = 1) -> List[str]:
    return list(h3.grid_disk(h3_index, k))


def get_resolution_area_km2(resolution: int) -> float:
    return h3.average_hexagon_area(resolution, unit="km^2")


def cells_to_geojson_features(cells: List[str]) -> List[Dict[str, Any]]:
    features = []
    for cell in cells:
        features.append({
            "type": "Feature",
            "properties": {"h3_index": cell, "resolution": h3.get_resolution(cell)},
            "geometry": h3_to_geojson(cell),
        })
    return features
