"""Feature metadata registry + versioning.

A tiny in-process registry mapping feature name → metadata (group, dtype,
source, version, description). Used to validate and document feature vectors;
the values themselves live in Redis/DuckDB later.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    group: str          # spatial | temporal | competition
    dtype: str          # int | float | bool
    source: str
    version: str = "1.0"
    description: str = ""


class FeatureRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, FeatureSpec] = {}

    def register(self, spec: FeatureSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> FeatureSpec:
        return self._specs[name]

    def list(self, group: str | None = None) -> List[FeatureSpec]:
        specs = list(self._specs.values())
        return [s for s in specs if group is None or s.group == group]

    def as_dict(self) -> List[Dict[str, Any]]:
        return [asdict(s) for s in self._specs.values()]

    def validate(self, vector: Dict[str, Any]) -> List[str]:
        """Return list of feature names present in the vector but not registered."""
        return [k for k in vector if k not in self._specs]


# Default registry populated with the v2 feature set.
registry = FeatureRegistry()

_DEFAULTS = [
    FeatureSpec("population", "spatial", "int", "belstat/h3", description="Population in catchment"),
    FeatureSpec("density_per_sqkm", "spatial", "float", "belstat/h3", description="Population density"),
    FeatureSpec("avg_income", "spatial", "float", "belstat", description="Average income"),
    FeatureSpec("walkability", "spatial", "float", "osm", description="0..1 pedestrian accessibility"),
    FeatureSpec("parking_count", "spatial", "int", "osm", description="Nearby parking facilities"),
    FeatureSpec("poi_diversity", "spatial", "float", "osm", description="Shannon diversity of nearby POIs"),
    FeatureSpec("footfall_index", "spatial", "float", "mobility", description="Relative pedestrian footfall"),
    FeatureSpec("seasonality_amp", "temporal", "float", "mobility", description="Seasonal demand amplitude"),
    FeatureSpec("weekday_peak_ratio", "temporal", "float", "mobility", description="Weekday vs weekend ratio"),
    FeatureSpec("competitor_count", "competition", "int", "2gis/osm", description="Competitors in catchment"),
    FeatureSpec("saturation_index", "competition", "float", "white_space", description="Supply/demand ratio"),
    FeatureSpec("nearest_competitor_m", "competition", "float", "2gis/osm", description="Distance to nearest competitor"),
    FeatureSpec("location_quotient", "competition", "float", "competition", description="LQ vs region average"),
    FeatureSpec("cannibalization_risk", "competition", "float", "cannibalization", description="Own-store overlap risk"),
]
for _s in _DEFAULTS:
    registry.register(_s)
