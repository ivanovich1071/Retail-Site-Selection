"""Tests for H3 spatial indexing module."""

from backend.app.spatial.h3_indexing import (
    lat_lon_to_h3,
    h3_to_center,
    h3_to_geojson,
    polygon_to_h3_cells,
    get_neighbors,
    get_resolution_area_km2,
    cells_to_geojson_features,
)
from backend.app.spatial.hex_aggregator import (
    distribute_population_to_cells,
    count_competitors_per_cell,
)


MINSK_LAT, MINSK_LON = 53.9006, 27.5615


class TestH3Indexing:
    def test_lat_lon_to_h3_returns_string(self):
        cell = lat_lon_to_h3(MINSK_LAT, MINSK_LON)
        assert isinstance(cell, str)
        assert len(cell) > 0

    def test_lat_lon_to_h3_resolution(self):
        cell_r7 = lat_lon_to_h3(MINSK_LAT, MINSK_LON, 7)
        cell_r9 = lat_lon_to_h3(MINSK_LAT, MINSK_LON, 9)
        assert cell_r7 != cell_r9

    def test_h3_to_center_roundtrip(self):
        cell = lat_lon_to_h3(MINSK_LAT, MINSK_LON, 9)
        lat, lon = h3_to_center(cell)
        assert abs(lat - MINSK_LAT) < 0.01
        assert abs(lon - MINSK_LON) < 0.01

    def test_h3_to_geojson_is_polygon(self):
        cell = lat_lon_to_h3(MINSK_LAT, MINSK_LON)
        geojson = h3_to_geojson(cell)
        assert geojson["type"] == "Polygon"
        assert len(geojson["coordinates"]) == 1
        ring = geojson["coordinates"][0]
        assert ring[0] == ring[-1]

    def test_polygon_to_h3_cells_returns_nonempty(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[27.50, 53.85], [27.60, 53.85], [27.60, 53.95], [27.50, 53.95], [27.50, 53.85]]],
        }
        cells = polygon_to_h3_cells(polygon, 7)
        assert len(cells) > 0
        assert all(isinstance(c, str) for c in cells)

    def test_get_neighbors(self):
        cell = lat_lon_to_h3(MINSK_LAT, MINSK_LON)
        neighbors = get_neighbors(cell, k=1)
        assert cell in neighbors
        assert len(neighbors) == 7  # center + 6 neighbors

    def test_resolution_area(self):
        area = get_resolution_area_km2(9)
        assert 0.05 < area < 0.2

    def test_cells_to_geojson_features(self):
        cell = lat_lon_to_h3(MINSK_LAT, MINSK_LON)
        features = cells_to_geojson_features([cell])
        assert len(features) == 1
        assert features[0]["type"] == "Feature"
        assert features[0]["geometry"]["type"] == "Polygon"


class TestHexAggregator:
    def test_distribute_population(self):
        cells = [lat_lon_to_h3(MINSK_LAT + i * 0.001, MINSK_LON, 9) for i in range(5)]
        cells = list(set(cells))
        result = distribute_population_to_cells(10000, 5000.0, cells)
        assert len(result) == len(cells)
        total_pop = sum(r["population"] for r in result)
        assert abs(total_pop - 10000) < len(cells)  # rounding tolerance

    def test_distribute_empty_cells(self):
        result = distribute_population_to_cells(10000, 5000.0, [])
        assert result == []

    def test_count_competitors(self):
        competitors = [
            {"lat": MINSK_LAT, "lon": MINSK_LON},
            {"lat": MINSK_LAT + 0.0001, "lon": MINSK_LON},
            {"lat": MINSK_LAT + 0.05, "lon": MINSK_LON + 0.05},
        ]
        counts = count_competitors_per_cell(competitors)
        assert sum(counts.values()) == 3
        assert len(counts) >= 1
