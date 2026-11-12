"""Portable geography summaries and exact frozen-land territory contracts."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from app.background_geography import BackgroundGeography, build_geography, kingdom_environment, simulate_background, source_pin
from app.civ_sim import CivSimConfig, CivSimError, habitat_from_arrays, simulate
from app.map_bundle import MAX_VALUES
from app.terrain_source import CLOSED_BELOW_SEA, LAND, OCEAN
from tests.test_map_bundle import registered  # noqa: F401


class FrozenBundle:
    def __init__(self, shape=(4, 8)):
        self.id = 'fixture-world'
        self.groups = ('terrain', 'environment', 'climate', 'hydrology', 'ocean', 'surface_water')
        self.record = dict(sources={g: dict(identity=g + '-identity', manifest_sha256=g + '-sha') for g in self.groups})
        self.manifests = {g: dict(identity=g + '-identity', status='frozen') for g in self.groups}
        grid = dict(shape_zx=list(shape), first_xz_m=[0., 0.], spacing_m=1000., semantics='cell-centre')
        self.grids = {g: deepcopy(grid) for g in self.groups}
        self.grids['ocean'] = dict(shape_zx=[2, 2], first_xz_m=[0., 0.], spacing_m=40000.)
        status = np.full(shape, LAND, np.uint8)
        status[0, 0] = OCEAN
        status[1, 1] = CLOSED_BELOW_SEA
        status[:, 3] = OCEAN
        self.arrays = {'terrain.status': status}
        self.specs = {g: {} for g in self.groups}
        self.specs['terrain']['status'] = dict(shape=list(shape), dtype='uint8', queryable=True, unit='1')
        for group in self.groups[1:]:
            field_shape = [12, *self.grids[group]['shape_zx']]
            self.specs[group]['monthly_value'] = dict(shape=field_shape, dtype='float64', queryable=True,
                                                     unit='K', time_semantics='finite-year monthly')
            array = np.broadcast_to(np.arange(12.)[:, None, None], field_shape).copy()
            array[:, 0, 0] = np.nan
            self.arrays[group + '.monthly_value'] = array
        self.specs['hydrology']['order'] = dict(shape=[shape[0] * shape[1]], dtype='int64', queryable=False, unit='1')
        self.changed = False
        self.calls = []
        self.environment = SimpleNamespace(info=SimpleNamespace(
            shape_zx=shape, first_sample_xz_m=(0., 0.), spacing_m=1000., layers=('status', 'elevation_m'),
            vectors=(), identity='environment-identity', kind='arrays', schema='arrays', world_seed=1))
        self.environment.crop = lambda *args, **kwargs: dict(shape_zx=list(shape), status=status.copy(),
                                                             elevation_m=np.full(shape, 40.))

    def check_unchanged(self):
        if self.changed:
            raise ValueError('Source changed')

    def detail(self):
        return dict(warnings=['finite diagnostic year, no permanent lake claim'])

    def query(self, fields, window, months=(1,)):
        self.check_unchanged()
        z0, x0, z1, x1 = window
        result = {}
        count = 0
        for field in fields:
            group, _ = field.split('.')
            nz, nx = self.grids[group]['shape_zx']
            assert 0 <= z0 < z1 <= nz and 0 <= x0 < x1 <= nx
            array = self.arrays[field]
            selected = array[np.asarray(months) - 1, z0:z1, x0:x1] if array.ndim == 3 else array[z0:z1, x0:x1]
            result[field] = selected.tolist()
            count += selected.size
        assert count <= MAX_VALUES
        self.calls.append((fields, window, months))
        return dict(arrays=result)


def _mask(geometry):
    mask = np.zeros(geometry['grid']['shape_zx'], bool)
    for z, x0, x1 in geometry['spans']:
        mask[z, x0:x1] = True
    return mask


def test_all_six_native_groups_and_months_are_summarized_without_raw_arrays():
    bundle = FrozenBundle()
    before = {k: v.copy() for k, v in bundle.arrays.items()}
    geography = build_geography(bundle)
    assert set(geography['groups']) == set(bundle.groups)
    assert geography['grids']['ocean']['spacing_m'] == 40000.
    assert geography['groups']['hydrology']['fields']['order']['status'] == 'descriptor-only'
    for group in bundle.groups[1:]:
        stats = geography['groups'][group]['fields']['monthly_value']['statistics']
        assert [row['month'] for row in stats] == list(range(1, 13))
        assert [row['mean'] for row in stats] == list(range(12))
        assert all(row['missing'] == 1 for row in stats)
    assert geography['groups']['terrain']['fields']['status']['categorical']
    assert 'arrays' not in geography
    assert len(geography['landmasses']) == 2
    union = np.logical_or.reduce([_mask(row['geometry']) for row in geography['landmasses']])
    assert np.array_equal(union, bundle.arrays['terrain.status'] == LAND)
    assert [row['id'] for row in geography['landmasses']] == [row['id'] for row in build_geography(bundle)['landmasses']]
    assert all(np.array_equal(value, before[key], equal_nan=True) for key, value in bundle.arrays.items())


def test_large_monthly_fields_are_read_in_bounded_native_windows():
    bundle = FrozenBundle((90, 90))
    geography = build_geography(bundle)
    assert geography['summary']['group_count'] == 6
    assert len([call for call in bundle.calls if call[0] == ['climate.monthly_value']]) > 1


def test_source_pin_is_array_free_and_detached_and_changes_are_rejected():
    bundle = FrozenBundle()
    pin = source_pin(bundle)
    pin['sources']['terrain']['identity'] = 'mutated-copy'
    assert bundle.record['sources']['terrain']['identity'] == 'terrain-identity'
    assert not bundle.calls
    bundle.changed = True
    with pytest.raises(ValueError, match='changed'):
        build_geography(bundle)


def test_kingdom_environment_uses_native_grids_monthly_missing_and_separate_ocean():
    bundle = FrozenBundle()
    bundle.grids['climate'] = dict(shape_zx=[2, 4], first_xz_m=[0., 0.], spacing_m=2000.)
    bundle.grids['hydrology'] = dict(shape_zx=[2, 4], first_xz_m=[1000., 1000.], spacing_m=2000.)
    for group in ('climate', 'hydrology'):
        bundle.specs[group].pop('monthly_value')
        bundle.arrays.pop(group + '.monthly_value')

    def field(group, name, array, unit='mm/month', **descriptor):
        bundle.specs[group][name] = dict(shape=list(array.shape), dtype=str(array.dtype), queryable=True,
                                          unit=unit, time_semantics='finite-year monthly', **descriptor)
        bundle.arrays[group + '.' + name] = array

    values = np.arange(8., dtype=float).reshape(2, 4)
    temperatures = np.arange(12.)[:, None, None] + values
    temperatures[:, 0, 0] = 9999.  # Ocean in the terrain grid, excluded.
    temperatures[:, 0, 1] = np.nan  # Selected native sample remains unknown.
    field('climate', 'monthly_temperature_c', temperatures, unit='degC')
    rain = np.full((12, 2, 4), 10.)
    rain[:, 0, 1] = -999.
    field('climate', 'monthly_precipitation_mm', rain, nodata=-999.)
    field('climate', 'biome_id', np.array([[9, 1, 1, 1], [2, 2, 2, 2]], np.uint8), unit='1')
    field('hydrology', 'monthly_snow_swe_mm', np.full((12, 2, 4), np.nan), unit='mm')
    field('surface_water', 'wet_mask', np.ones((12, 4, 8), np.uint8), unit='1')
    bundle.specs['ocean']['monthly_sea_temperature_c'] = bundle.specs['ocean'].pop('monthly_value')
    bundle.arrays['ocean.monthly_sea_temperature_c'] = np.full((12, 2, 2), 999.)
    bundle.arrays.pop('ocean.monthly_value')
    mask = bundle.arrays['terrain.status'] == LAND
    result = kingdom_environment(bundle, mask, bundle.grids['terrain'])
    climate = result['groups']['climate']
    assert climate['grid'] == bundle.grids['climate']
    assert climate['territory_sample_count'] == 7
    temperatures = climate['fields']['monthly_temperature_c']
    assert temperatures['time_semantics'] == 'finite-year monthly'
    assert temperatures['unit'] == 'degC'
    assert [row['month'] for row in temperatures['statistics']] == list(range(1, 13))
    assert temperatures['statistics'][7] == dict(count=6, missing=1, minimum=9., maximum=14., mean=11.5, month=8)
    assert climate['fields']['monthly_precipitation_mm']['statistics'][0]['mean'] == 10.
    assert climate['fields']['monthly_precipitation_mm']['statistics'][0]['missing'] == 1
    assert climate['fields']['biome_id']['statistics']['histogram'] == {'1': 3, '2': 4}
    hydro = result['groups']['hydrology']
    assert hydro['territory_sample_count'] == 5
    assert hydro['fields']['monthly_snow_swe_mm']['statistics'][0] == dict(
        count=0, missing=5, minimum=None, maximum=None, mean=None, month=1)
    assert result['groups']['surface_water']['territory_sample_count'] == int(mask.sum())
    assert 'ocean' not in result['groups']
    assert all(not call[0][0].startswith('ocean.') for call in bundle.calls)
    world = build_geography(bundle)
    assert world['groups']['ocean']['fields']['monthly_sea_temperature_c']['statistics'][0]['mean'] == 999.


def test_territories_cover_owned_land_only_and_background_year_is_selected():
    bundle = FrozenBundle()
    config = CivSimConfig(seed=2, end_year=2, block_cells=4, min_land_cells=1, max_polities=2,
                          found_period=1, min_capital_hops=1, war_per_mille=0, expand_budget=1_000_000)
    result = simulate_background(bundle, config, background_year=0)
    assert result['background_year'] == 0
    assert result['chronicle']['end_year'] == 0
    assert [row['year'] for row in result['chronicle']['snapshots']] == [0]
    assert all(row['year'] <= 0 for row in result['chronicle']['annals'])
    assert result['kingdoms']
    for kingdom in result['kingdoms']:
        mask = _mask(kingdom['geometry'])
        assert not np.any(mask & (bundle.arrays['terrain.status'] != LAND))
        assert kingdom['land_cells'] == int(mask.sum())
        assert kingdom['landmass_ids']
        native = kingdom['native_environment']['groups']
        assert native['terrain']['territory_sample_count'] == kingdom['land_cells']
        assert 'ocean' not in native
    assert 'province connectivity' in result['chronicle']['provenance']['road_semantics']
    with pytest.raises(ValueError, match='background_year'):
        simulate_background(bundle, config, background_year=3)


def test_profile_preferences_change_foundation_and_legacy_defaults_are_identical():
    shape = (4, 8)
    habitat = habitat_from_arrays(identity='preferences', elevation_m=np.full(shape, 40.),
                                  status=np.full(shape, LAND, np.uint8), spacing_m=1000.,
                                  first_sample_xz_m=(0., 0.), block_cells=4, min_land_cells=1,
                                  river_radius_m=0, coast_scale_m=20000,
                                  rivers=[dict(points_xz_m=[[0., 1500.], [3000., 1500.]])])
    config = CivSimConfig(seed=1, end_year=0, society=False, max_polities=1, found_jitter=0,
                          expand_budget=-1_000_000_000)
    default = simulate(habitat, config)
    assert default == simulate(habitat, config, profiles=[])
    avoid = simulate(habitat, config, profiles=[dict(id='avoid-rivers', source='author', weights=dict(river=-100))])
    assert default['polities'][0]['capital'] == 0
    assert avoid['polities'][0]['capital'] == 1
    assert avoid['provenance']['polity_profiles'][0]['weights']['distance'] == config.distance_weight
    for invalid in [True, 1.2, float('nan'), 10**10]:
        with pytest.raises(CivSimError):
            simulate(habitat, config, profiles=[dict(weights=dict(river=invalid))])


def test_registry_adapter_exports_expected_contract(monkeypatch):
    bundle = FrozenBundle()
    monkeypatch.setattr('app.background_geography.BundleRegistry', lambda root: SimpleNamespace(get=lambda identity: bundle))
    geography = BackgroundGeography('unused')
    description = geography.describe(bundle.id)
    assert description['source'] == geography.source(bundle.id)
    assert np.array_equal(_mask(description['terrain_union']), bundle.arrays['terrain.status'] == LAND)
    config = dict(seed=1, end_year=0, block_cells=4, min_land_cells=1)
    result = geography.simulate(bundle.id, config, ['adopted-race-id'], [])
    assert result['selected_elements'] == ['adopted-race-id']
    assert result['polities'] == result['territories'] == result['kingdoms']


def test_real_registered_bundle_reader_integrates_with_habitat(registered):  # noqa: F811
    root, record = registered
    helper = BackgroundGeography(root)
    description = helper.describe(record['id'])
    assert description['geography']['groups']['climate']['fields']['monthly_temperature_c']['statistics'][6]['mean'] == 6
    result = helper.simulate(record['id'], dict(seed=1, end_year=2, block_cells=2, min_land_cells=1))
    assert result['chronicle']['provenance']['background_bundle'] == description['source']
    assert result['background_year'] == 2
