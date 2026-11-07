"""Public types and vocabulary for dream-map-source v1."""
from dataclasses import dataclass, field
from typing import Protocol

from app.terrain_source import (
    TerrainSourceError,
)

MapSourceError = TerrainSourceError


class MissingLayerError(MapSourceError):
    """A selected product does not provide a requested standard layer."""


class UnsupportedSourceError(MapSourceError):
    """No adapter is registered for the literal kind/schema pair."""


STANDARD_LAYERS = {
    "status": "1", "elevation_m": "m", "water_surface_m": "m",
    "drainage_area_m2": "m2", "discharge_m3_s": "m3/s",
    "temperature_c": "degC", "precipitation_mm_yr": "mm/yr", "biome": "1",
    "rock_index": "1", "bed_hardness": "1", "permeability_m2": "m2",
    "erosion_m": "m", "deposition_m": "m", "soil_water_mm": "mm",
    "snow_swe_mm": "mm", "cover_fraction": "1",
}
DEFAULT_LAYERS = ("elevation_m", "status")


@dataclass(frozen=True)
class SourceInfo:
    kind: str
    schema: str
    identity: str
    lineage: tuple
    producer: str
    world_seed: int
    subseeds: dict
    extent_m: tuple
    spacing_m: float
    first_sample_xz_m: tuple
    shape_zx: tuple
    grid_semantics: str
    boundary: str
    layers: tuple
    vectors: tuple
    declared_generated: object
    limitations: object
    elevation_meaning: str
    algorithm_version: str = ""
    subseed_method: str = ""
    derivations: tuple = ()
    layer_metadata: dict = field(default_factory=dict)


class MapSource(Protocol):
    info: SourceInfo

    def sample(self, x_m, z_m, layers=DEFAULT_LAYERS): ...
    def crop(self, x0, z0, x1, z1, layers=DEFAULT_LAYERS, *, max_cells=16_777_216): ...
    def vectors(self, kind): ...
