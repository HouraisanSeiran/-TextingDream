"""Frozen bundle → bounded summaries, land components and historical territories.

All reads use registered products. This module neither generates terrain nor
claims simulated province links are surveyed roads or settlements.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import numpy as np
from scipy import ndimage

from app.civ_sim.config import CivSimConfig, normalize_profiles
from app.civ_sim.engine import simulate
from app.civ_sim.geography import habitat_from_source
from app.map_bundle import BundleRegistry, MapBundle, MAX_VALUES
from app.terrain_source import LAND


def source_pin(bundle):
    """Cheap, array-free provenance suitable for publication freshness checks."""
    bundle.check_unchanged()
    return dict(bundle_id=bundle.id, sources=deepcopy(bundle.record['sources']),
                manifest_identities={g: m.get('identity') for g, m in bundle.manifests.items()})


def _windows(grid, monthly=False):
    nz, nx = grid['shape_zx']
    side = min(128, int((MAX_VALUES // (12 if monthly else 1)) ** .5))
    for z in range(0, nz, side):
        for x in range(0, nx, side):
            yield [z, x, min(z + side, nz), min(x + side, nx)]


def _spans(mask):
    rows = []
    for z in range(mask.shape[0]):
        edges = np.flatnonzero(np.diff(np.r_[False, mask[z], False].astype(np.int8)))
        rows.extend([int(z), int(x0), int(x1)] for x0, x1 in edges.reshape(-1, 2))
    return rows


def _window_values(bundle, group, name, window, months=(1,)):
    if isinstance(bundle, MapBundle):
        # Internal bounded reader preserves the same nodata/ocean/Q-support
        # masks as query, without serializing millions of samples into JSON.
        # Caller checks the immutable source before and after the whole field.
        return bundle._values(group, [name], window, months)[name]
    field = group + '.' + name
    return bundle.query([field], window, months=months)['arrays'][field]


def _components(bundle, status):
    labels, count = ndimage.label(status == LAND)  # four neighbours, finite/no wrap
    grid = bundle.grids['terrain']
    records = []
    for label, window in enumerate(ndimage.find_objects(labels), 1):
        if window is None:
            continue
        mask = labels[window] == label
        spans = [[z + window[0].start, x0 + window[1].start, x1 + window[1].start]
                 for z, x0, x1 in _spans(mask)]
        token = json.dumps([bundle.record['sources']['terrain']['identity'], spans], separators=(',', ':'))
        identity = 'landmass-' + hashlib.sha256(token.encode()).hexdigest()[:20]
        cells = int(mask.sum())
        records.append(dict(id=identity, name='陆块 %d' % label, kind='landmass', land_cells=cells,
                            area_m2=cells * grid['spacing_m'] ** 2,
                            geometry=dict(grid=deepcopy(grid), spans=spans),
                            classification='connected dry land; continent/island naming remains authorial'))
    return records


def _field_summary(bundle, group, name, spec, support=None):
    bundle.check_unchanged()
    descriptor = {key: deepcopy(spec.get(key)) for key in ('shape', 'dtype', 'unit', 'nodata', 'time_semantics', 'queryable')}
    if not spec['queryable']:
        return dict(descriptor, status='descriptor-only')
    monthly = len(spec['shape']) == 3
    categorical = (str(spec.get('dtype')) in ('bool', '|b1') or name == 'status' or name.endswith('_id')
                   or any(token in name for token in ('biome', 'mask', 'support', 'receiver')))
    bins = [dict(count=0, missing=0, minimum=None, maximum=None, total=0., histogram={})
            for _ in range(12 if monthly else 1)]
    for window in _windows(bundle.grids[group], monthly):
        z0, x0, z1, x1 = window
        selected = None if support is None else support[z0:z1, x0:x1]
        if selected is not None and not selected.any():
            continue
        values = _window_values(bundle, group, name, window, list(range(1, 13)) if monthly else [1])
        chunks = values if monthly else [values]
        for accumulator, chunk in zip(bins, chunks):
            array = np.asarray(chunk, dtype=float)
            if selected is not None:
                array = array[selected]
            valid = np.isfinite(array)
            nodata = spec.get('nodata')
            if isinstance(nodata, (int, float)) and np.isfinite(nodata):
                valid &= array != nodata
            accumulator['missing'] += int(array.size - valid.sum())
            finite = array[valid]
            if not finite.size:
                continue
            accumulator['count'] += int(finite.size)
            if categorical:
                keys, counts = np.unique(finite, return_counts=True)
                for key, count in zip(keys, counts):
                    key = str(int(key)) if float(key).is_integer() else str(float(key))
                    accumulator['histogram'][key] = accumulator['histogram'].get(key, 0) + int(count)
            else:
                lo, hi = float(finite.min()), float(finite.max())
                accumulator['minimum'] = lo if accumulator['minimum'] is None else min(accumulator['minimum'], lo)
                accumulator['maximum'] = hi if accumulator['maximum'] is None else max(accumulator['maximum'], hi)
                accumulator['total'] += float(finite.sum())
    summaries = []
    for index, accumulator in enumerate(bins):
        total = accumulator.pop('total')
        if categorical:
            accumulator.pop('minimum'); accumulator.pop('maximum')
            histogram = accumulator['histogram']
            accumulator['category_count'] = len(histogram)
            if len(histogram) > 64:
                common = sorted(histogram, key=lambda key: (-histogram[key], key))[:64]
                accumulator['histogram'] = {key: histogram[key] for key in common}
                accumulator['other_count'] = accumulator['count'] - sum(accumulator['histogram'].values())
                accumulator['histogram_limit'] = 64
        else:
            accumulator.pop('histogram')
            accumulator['mean'] = total / accumulator['count'] if accumulator['count'] else None
        if monthly:
            accumulator['month'] = index + 1
        summaries.append(accumulator)
    bundle.check_unchanged()
    return dict(descriptor, status='summarized', categorical=categorical,
                statistics=summaries if monthly else summaries[0])


def _native_support(territory_mask, terrain_grid, native_grid):
    """Native cell centres inside a frozen fine-grid territory; finite, no wrap."""
    nz, nx = native_grid['shape_zx']
    first_x, first_z = native_grid['first_xz_m']
    spacing = native_grid['spacing_m']
    terrain_x, terrain_z = terrain_grid['first_xz_m']
    cols = np.floor((first_x + np.arange(nx) * spacing - terrain_x) / terrain_grid['spacing_m'] + .5).astype(np.int64)
    rows = np.floor((first_z + np.arange(nz) * spacing - terrain_z) / terrain_grid['spacing_m'] + .5).astype(np.int64)
    valid_x = (cols >= 0) & (cols < territory_mask.shape[1])
    valid_z = (rows >= 0) & (rows < territory_mask.shape[0])
    result = np.zeros((nz, nx), bool)
    result[np.ix_(valid_z, valid_x)] = territory_mask[np.ix_(rows[valid_z], cols[valid_x])]
    return result


def kingdom_environment(bundle, territory_mask, terrain_grid):
    """Original saved environmental observations associated with one territory.

    Each native sample is counted once. Monthly fluxes stay monthly; masked
    support remains missing. Ocean observations belong to the separate world
    ocean summary: a coarse ocean cell centre over land is not a kingdom value.
    """
    fields = {'elevation_m', 'status', 'temperature_c', 'precipitation_mm_yr', 'biome', 'biome_id',
              'monthly_temperature_c', 'monthly_precipitation_mm', 'monthly_runoff_mm',
              'monthly_soil_water_mm', 'monthly_snow_swe_mm', 'monthly_ice_swe_mm',
              'monthly_actual_et_mm', 'monthly_discharge_m3_s', 'monthly_liquid_input_mm',
              'soil_water_mm', 'snow_swe_mm', 'year_end_ice_swe_mm',
              'final_soil_water_mm', 'final_snow_swe_mm', 'final_ice_swe_mm',
              'soil_mm', 'runoff_mm', 'lake_depth_m', 'wet_mask',
              'hillslope_discharge_m3_s', 'annual_mean_hillslope_discharge_m3_s'}
    groups = {}
    for group in bundle.groups:
        if group == 'ocean':
            continue
        names = [name for name, spec in bundle.specs[group].items() if name in fields and spec['queryable']]
        if not names:
            continue
        native = bundle.grids[group]
        support = _native_support(territory_mask, terrain_grid, native)
        groups[group] = dict(grid=deepcopy(native), territory_sample_count=int(support.sum()),
                             fields={name: _field_summary(bundle, group, name, bundle.specs[group][name], support)
                                     for name in names})
    bundle.check_unchanged()
    return dict(groups=groups, semantics='saved native cell centres within LAND-clipped territory; no resampling of values; ocean remains a separate world summary',
                missing_semantics='unknown/unsupported samples excluded from statistics, counted as missing')


def _terrain_status(bundle):
    grid = bundle.grids['terrain']
    status = np.zeros(grid['shape_zx'], np.int16)
    for z0, x0, z1, x1 in _windows(grid):
        status[z0:z1, x0:x1] = _window_values(bundle, 'terrain', 'status', [z0, x0, z1, x1])
    return status


def build_geography(bundle):
    """Summarize every registered native grid, retaining monthly semantics."""
    pin = source_pin(bundle)
    groups = {}
    details = bundle.detail()
    for group in bundle.groups:
        manifest = bundle.manifests[group]
        groups[group] = dict(grid=deepcopy(bundle.grids[group]), status=manifest.get('status', 'frozen'),
                             limitations=deepcopy(details.get('groups', {}).get(group, {}).get('limitations', manifest.get('limitations', []))),
                             fields={name: _field_summary(bundle, group, name, spec)
                                     for name, spec in bundle.specs[group].items()})
    landmasses = _components(bundle, _terrain_status(bundle))
    bundle.check_unchanged()
    return dict(bundle_id=bundle.id, sources=pin, grids=deepcopy(bundle.grids), groups=groups,
                landmasses=landmasses, grid=deepcopy(bundle.grids['terrain']),
                summary=dict(group_count=len(groups), landmass_count=len(landmasses),
                             land_cells=sum(row['land_cells'] for row in landmasses)),
                limitations=deepcopy(details.get('warnings', [])),
                stable_biome_ids=deepcopy(details.get('stable_biome_ids', {})),
                coordinate_system=details.get('coordinate_system', 'metres; X east, Z south; finite no wrap'))


def simulate_background(bundle, config, profiles=None, background_year=None, geography=None):
    """Return exact LAND-clipped territories for a selected year of history."""
    if isinstance(config, dict):
        config = CivSimConfig(**config)
    if not isinstance(config, CivSimConfig):
        raise ValueError('config must be CivSimConfig or an object')
    year = config.end_year if background_year is None else background_year
    if type(year) is not int or not config.start_year <= year <= config.end_year:
        raise ValueError('background_year must be inside the simulated interval')
    selected_profiles = normalize_profiles(profiles, config)
    geography = build_geography(bundle) if geography is None else geography
    if geography['sources'] != source_pin(bundle):
        raise ValueError('Geography source pin changed')
    habitat = habitat_from_source(bundle.environment, block_cells=config.block_cells,
                                  min_land_cells=config.min_land_cells, river_radius_m=config.river_radius_m,
                                  coast_scale_m=config.coast_scale_m)
    # The selected background year is the knowledge horizon. Running only its
    # deterministic prefix also excludes future people, deaths and dynasties.
    chronicle = simulate(habitat, replace(config, end_year=year), profiles=profiles)
    snapshot = next(row for row in chronicle['snapshots'] if row['year'] == year)
    grid = geography['grid']
    if list(habitat.shape_zx) != grid['shape_zx'] or list(habitat.first_sample_xz_m) != grid['first_xz_m'] or habitat.spacing_m != grid['spacing_m']:
        raise ValueError('Habitat and frozen terrain grids differ')
    landmasses = geography['landmasses']
    kingdoms = []
    for polity in snapshot['polities']:
        if not polity['alive']:
            continue
        mask = np.isin(habitat.cell_region, polity['regions']) & (habitat.status == LAND)
        overlaps = [row['id'] for row in landmasses
                    if any(mask[z, x0:x1].any() for z, x0, x1 in row['geometry']['spans'])]
        cells = int(mask.sum())
        owned_regions = [habitat.regions[rid] for rid in polity['regions']]
        def weighted(attribute):
            known = [(getattr(region, attribute), region.land_cells) for region in owned_regions
                     if getattr(region, attribute) is not None]
            weight = sum(count for _, count in known)
            return sum(value * count for value, count in known) / weight if weight else None
        kingdoms.append(dict(id='kingdom-%d' % polity['id'], polity_id=polity['id'], name=polity['name'],
                             region_ids=list(polity['regions']), landmass_ids=overlaps,
                             geometry=dict(grid=deepcopy(grid), spans=_spans(mask)),
                             land_cells=cells, area_m2=cells * grid['spacing_m'] ** 2,
                             capital_region_id=polity['capital'], background_year=year,
                             profile_id=selected_profiles[polity['id'] % len(selected_profiles)]['id'] if selected_profiles else None,
                             environment_summary=dict(mean_elevation_m=weighted('mean_elevation_m'),
                                                      river_millis=weighted('river_millis'),
                                                      coast_millis=weighted('coast_millis'),
                                                      climate_millis=weighted('climate_millis'),
                                                      semantics='land-cell-weighted simulation province indicators, not measured resource inventory'),
                             native_environment=kingdom_environment(bundle, mask, grid),
                             boundary_semantics='simulation province ownership clipped to frozen LAND cells'))
    chronicle['provenance']['background_bundle'] = source_pin(bundle)
    chronicle['provenance']['road_semantics'] = 'province connectivity only; not generated towns or surveyed roads'
    bundle.check_unchanged()
    return dict(geography=geography, chronicle=chronicle, landmasses=landmasses,
                kingdoms=kingdoms, background_year=year, profiles=selected_profiles,
                polities=kingdoms, continents=landmasses, territories=kingdoms)


class BackgroundGeography:
    """Registry-only adapter used by the background publication pipeline."""

    def __init__(self, root):
        self.registry = BundleRegistry(root)
        self._cache = {}

    def source(self, bundle_id):
        return source_pin(self.registry.get(bundle_id))

    def describe(self, bundle_id):
        bundle = self.registry.get(bundle_id)
        pin = source_pin(bundle)
        cached = self._cache.get(bundle_id)
        if cached is None or cached['sources'] != pin:
            cached = build_geography(bundle)
            self._cache[bundle_id] = cached
        geography = deepcopy(cached)
        return dict(source=pin, geography=geography, continents=geography['landmasses'],
                    terrain_union=dict(grid=geography['grid'],
                                       spans=[span for row in geography['landmasses'] for span in row['geometry']['spans']]))

    def simulate(self, bundle_id, config, selected_elements=None, polity_preferences=None):
        bundle = self.registry.get(bundle_id)
        description = self.describe(bundle_id)
        result = simulate_background(bundle, config, profiles=polity_preferences, geography=description['geography'])
        result['selected_elements'] = deepcopy(selected_elements or [])
        return result
