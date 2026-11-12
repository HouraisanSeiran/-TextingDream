# -*- coding: utf-8 -*-
"""Habitat grid: land only, rivers and coast from the same geography, no bed writes."""
import math

import numpy as np

from app.civ_sim import CivSimError, habitat_from_arrays
from app.civ_sim.geography import full_crop_bounds
from app.terrain_source import CLOSED_BELOW_SEA, LAND, OCEAN


def _habitat(status, elevation, **kwargs):
    options = dict(
        identity="unit-habitat",
        spacing_m=1000.0,
        first_sample_xz_m=(0.0, 0.0),
        block_cells=4,
        min_land_cells=1,
        river_radius_m=0,
        coast_scale_m=20_000,
    )
    options.update(kwargs)
    return habitat_from_arrays(elevation_m=elevation, status=status, **options)


def test_full_crop_bounds_cover_the_fast_grid():
    first = (-798000.0, -798000.0)
    spacing = 4000.0
    shape = (400, 400)
    x0, z0, x1, z1 = full_crop_bounds(first, spacing, shape)
    assert math.ceil((x0 - first[0]) / spacing) == 0
    assert math.ceil((x1 - first[0]) / spacing) == 400
    assert math.ceil((z0 - first[1]) / spacing) == 0
    assert math.ceil((z1 - first[1]) / spacing) == 400


def test_ocean_and_closed_basins_are_not_provinces():
    status = np.full((8, 8), LAND, np.uint8)
    status[:, :2] = OCEAN
    status[:, 2] = CLOSED_BELOW_SEA
    elevation = np.full((8, 8), 30.0)
    elevation[:, :2] = -50.0
    original = status.copy()
    habitat = _habitat(status, elevation)
    assert np.array_equal(status, original)
    assert not habitat.status.flags.writeable
    assert not habitat.cell_region.flags.writeable
    assert np.all(habitat.cell_region[habitat.status == OCEAN] == -1)
    assert np.all(habitat.cell_region[habitat.status == CLOSED_BELOW_SEA] == -1)
    land = habitat.status == LAND
    assert habitat.habitable_cells == int(land.sum())
    assert set(np.unique(habitat.cell_region[~land])).issubset({-1})
    assert habitat.regions
    assert all(region.land_cells > 0 for region in habitat.regions)
    west = min(region.coast_m for region in habitat.regions if region.block_x == 0)
    east = min(region.coast_m for region in habitat.regions if region.block_x == 1)
    assert west < east


def test_open_ocean_has_no_regions_and_is_reproducible():
    status = np.full((6, 6), OCEAN, np.uint8)
    elevation = np.full((6, 6), -20.0)
    first = _habitat(status, elevation)
    second = _habitat(status, elevation)
    assert first.summary()["region_count"] == 0
    assert first.ocean_cells == 36
    assert first.summary() == second.summary()


def test_river_proximity_stays_on_the_crossed_cells():
    status = np.full((4, 6), LAND, np.uint8)
    elevation = np.full((4, 6), 25.0)
    rivers = [{"points_xz_m": [[0.0, 1000.0], [2000.0, 1000.0]]}]
    with_river = _habitat(status, elevation, rivers=rivers, block_cells=6, river_radius_m=0)
    without = _habitat(status, elevation, block_cells=6, river_radius_m=0)
    assert len(with_river.regions) == 1
    assert with_river.regions[0].river_millis > 0
    assert without.regions[0].river_millis == 0


def test_rejects_a_mismatched_climate_grid():
    status = np.full((4, 4), LAND, np.uint8)
    elevation = np.zeros((4, 4))
    try:
        _habitat(status, elevation, temperature_c=np.zeros((3, 3)))
    except CivSimError as error:
        assert "temperature_c" in str(error)
    else:
        raise AssertionError("expected CivSimError")
