"""Public types and vocabulary for dream-map-source v1."""
from dataclasses import dataclass, field
from typing import Protocol

from app.terrain_source import (
    TerrainSourceError,
    UNPREPARED as UNPREPARED, OUT_OF_BOUNDS as OUT_OF_BOUNDS, UNKNOWN as UNKNOWN,
    OCEAN as OCEAN, CLOSED_BELOW_SEA as CLOSED_BELOW_SEA, LAND as LAND, STATUS_NAMES as STATUS_NAMES,
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
    "groundwater_storage_m3":"m3", "groundwater_head_m":"m", "groundwater_recharge_m3":"m3",
    "groundwater_baseflow_m3":"m3", "ground_ice_m":"m", "soil_temperature_c":"degC",
    "infiltration_factor":"1", "absorbed_shortwave_j_m2":"J/m2", "geothermal_input_j_m2":"J/m2",
    "actual_et_energy_j_m2":"J/m2", "biomass_carbon_kg":"kg", "soil_salt_kg":"kg",
    "soil_nutrient_kg":"kg", "soil_organic_carbon_kg":"kg", "root_cohesion_pa":"Pa",
    "manning_n":"s/m^(1/3)", "plant_stress_factor":"1", "habitat_suitability":"1",
    "habitat_population_individuals":"individuals", "soil_salinity_kg_m3":"kg/m3",
    "geothermal_heat_w_m2":"W/m2", "sea_temperature_c":"degC", "sea_air_temperature_feedback_c":"degC",
    "native_committed_bed_change_m":"m",
    "glacier_ice_volume_m3":"m3", "glacier_coverage_fraction":"1", "glacier_ice_thickness_m":"m",
    "glacier_ice_surface_m":"m", "glacier_simulated_fraction":"1", "glacier_melt_mean_m3_s":"m3/s",
    "coastal_water_volume_m3":"m3", "coastal_salt_kg":"kg",
    "coastal_salinity_kg_m3":"kg/m3",
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
