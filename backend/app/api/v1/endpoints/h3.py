from fastapi import APIRouter
from typing import List

from backend.app.schemas.h3 import H3PolyfillRequest, H3PolyfillResponse, H3CellData
from backend.app.spatial.h3_indexing import (
    polygon_to_h3_cells, h3_to_geojson, h3_to_center,
    get_neighbors, cells_to_geojson_features,
)

router = APIRouter()


@router.post("/polyfill", response_model=H3PolyfillResponse)
async def polyfill_polygon(req: H3PolyfillRequest):
    cells = polygon_to_h3_cells(req.polygon, req.resolution)

    cell_data = []
    features = []
    for cell in cells:
        lat, lon = h3_to_center(cell)
        geom = h3_to_geojson(cell)
        cell_data.append(H3CellData(
            h3_index=cell,
            resolution=req.resolution,
            center_lat=lat,
            center_lon=lon,
            geometry=geom,
        ))
        features.append({
            "type": "Feature",
            "properties": {"h3_index": cell},
            "geometry": geom,
        })

    return H3PolyfillResponse(
        cells=cell_data,
        total_cells=len(cells),
        resolution=req.resolution,
        geojson={"type": "FeatureCollection", "features": features},
    )


@router.get("/cell/{h3_index}", response_model=H3CellData)
async def get_cell(h3_index: str):
    lat, lon = h3_to_center(h3_index)
    return H3CellData(
        h3_index=h3_index,
        resolution=len(h3_index) - 1,
        center_lat=lat,
        center_lon=lon,
        geometry=h3_to_geojson(h3_index),
    )


@router.get("/neighbors/{h3_index}", response_model=List[H3CellData])
async def get_cell_neighbors(h3_index: str, k: int = 1):
    neighbors = get_neighbors(h3_index, k)
    result = []
    for cell in neighbors:
        lat, lon = h3_to_center(cell)
        result.append(H3CellData(
            h3_index=cell,
            resolution=len(cell) - 1,
            center_lat=lat,
            center_lon=lon,
            geometry=h3_to_geojson(cell),
        ))
    return result
