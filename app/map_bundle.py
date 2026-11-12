"""Read-only, explicitly registered same-source map bundles (author scope only).

No generation, default selection, story/saves access, or arbitrary-path endpoint.
Monthly products deliberately remain outside the two-dimensional MapCatalog.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from threading import RLock

import numpy as np

from app.map_source import load_source
from app.world_gen.world_climate_adapter import SavedClimateMap
from app.world_gen.climate_world_stage import topological_order

MAX_VALUES = 65536
MAX_VECTOR_PAGE = 500
GROUPS = ('terrain', 'environment', 'climate', 'hydrology', 'ocean')
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')
WARNINGS = [
    'Lake geometry is potential/unvalidated, not permanent water: 31356 potential cells (9.6125% of land) in this registered world; no lake storage or water balance.',
    'Finite diagnostic noleap365 year 1; potential biome is not realized ecology. No resources, civilizations or available-water inventory are inferred.',
    'Current glacier H is year-1 end and only known in selected dynamic regions. Outside support is unknown, not zero ice. Snow SWE is seasonal stock.',
    'Routing bed/surface, receiver, rivers and potential lakes retain the original frozen topology, not new-year ice geometry. Old cumulative melt is history only and is NOT an input to year 1.',
    'Ocean is a separate 40 km finite-year unconverged candidate; nearest wet-supported sample only, no climate feedback or calibrated navigation claim.',
]


class BundleMissing(FileNotFoundError):
    """Unregistered bundle or unavailable registered file."""


class BundleIdentityError(ValueError):
    """A registered immutable product or its same-source binding differs."""


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def relative_file(root, relative):
    """Registry paths are local-root-relative; never a request argument."""
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise BundleIdentityError('A root-relative POSIX registry path is required')
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise BundleIdentityError('Registry path escapes root')
    path = (Path(root) / p).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise BundleIdentityError('Registry path escapes root')
    if not path.exists():
        raise BundleMissing('Registered product is missing')
    return path


def safe_json(value):
    if isinstance(value, np.ndarray):
        return safe_json(value.tolist())
    if isinstance(value, np.generic):
        return safe_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    return value


def _stat(path):
    s = path.stat()
    return (s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _grid(spec):
    return dict(first_xz_m=list(spec.get('first_xz_m', spec.get('first_sample_xz_m'))),
                spacing_m=spec['spacing_m'], shape_zx=list(spec['shape_zx']),
                semantics='cell-centre', axes='X east, Z south; arrays [z,x]; metres; finite, no wrap')


def _extent(grid):
    x, z = grid['first_xz_m']; d = grid['spacing_m']; nz, nx = grid['shape_zx']
    return [x-d/2, z-d/2, x+(nx-.5)*d, z+(nz-.5)*d]


def _time(group, name, shape):
    if len(shape) == 1:
        return 'static topology permutation; descriptor only; no point/window semantics'
    if group == 'ocean':
        return ('finite year-1 monthly mean SST / quasi-steady monthly mean velocity; NOT converged climatology'
                if len(shape) == 3 else 'static 40 km ocean support/topology')
    if group == 'terrain':
        return 'frozen original geometry/topology; routing surface may include old H, not year-1 H'
    if len(shape) == 3:
        return ('noleap365 year-1 month-end water stock' if any(s in name for s in ('soil_water', 'snow_swe', 'ice_swe'))
                else 'noleap365 year-1 monthly mean or monthly integral, as units specify; liquid-only climate diagnostic' if group == 'climate'
                else 'noleap365 year-1 monthly mean or monthly integral, as units specify; snow/ice-liquid hydrology')
    if name.startswith('initial_'):
        return 'year-1 initial stock, not cumulative old-year melt'
    if name.startswith(('final_', 'glacier_')) or name in ('snow_swe_mm', 'soil_water_mm', 'year_end_ice_swe_mm'):
        return 'noleap365 year-1 end; glacier H only on explicit dynamic support'
    if name in ('temperature_c', 'precipitation_mm_yr', 'biome', 'biome_id', 'discharge_m3_s', 'biome_override_reason'):
        return 'noleap365 year-1 annual summary / potential class; Q = annual routed volume / 365 days'
    return 'saved static forcing, parameter or topology; no month advancement'


class MapBundle:
    """One whole registered source group; adapters verify bindings before publication.

    Files are hashed once when opened, then mmap-read-only cached. Every request
    checks cheap file signatures; any changed source is refused, never combined
    with a cached sibling. Two bundles maximum are held by BundleRegistry.
    """
    def __init__(self, root, record):
        self.root = Path(root).resolve()
        self.record = deepcopy(record)
        self.id = record['id']
        self._lock = RLock()
        self._signatures = {}
        self._arrays = {}
        self.paths = {}
        self.manifests = {}
        self.groups = GROUPS + (('surface_water',) if 'surface_water' in record['sources'] else ())
        for group in self.groups:
            ref = record['sources'][group]
            path = relative_file(self.root, ref['path'])
            mp = path / 'manifest.json'
            self._pinned(mp, ref['manifest_sha256'])
            m = read_json(mp)
            if group != 'ocean' and m.get('identity') != ref['identity']:
                raise BundleIdentityError('Registered source identity differs: ' + group)
            self.paths[group], self.manifests[group] = path, m
        src = record['sources']
        # Existing SavedClimateMap verifies actual bed/ocean/receiver/order.
        # SavedClimateHydrology's source builder also calls plan_climate, importing
        # numba even for a frozen read. Keep equivalent saved sidecar checks below,
        # without that generation dependency (no plan/compute/prepare call).
        self.climate = SavedClimateMap(self.paths['terrain'], self.paths['climate'],
            expected_source_identity=src['terrain']['identity'],
            expected_climate_identity=src['climate']['identity'])
        self.terrain = self.climate.terrain
        self._validate_hydrology()
        self.environment = load_source('world-map-product', self.paths['environment'],
                                       expected_identity=src['environment']['identity'])
        env = self.manifests['environment']
        binding = env.get('climate_environment', {})
        if (env.get('source_identity') != src['terrain']['identity']
                or binding.get('source_identity') != src['terrain']['identity']
                or binding.get('climate_identity') != src['climate']['identity']
                or binding.get('hydrology_identity') != src['hydrology']['identity']
                or _grid(env['grid']) != _grid(self.manifests['terrain']['grid'])):
            raise BundleIdentityError('Environment belongs to another source/climate/hydrology/grid')
        # Inherited topology must really be the same, not merely claim the parent ID.
        parent = self.manifests['terrain']
        for name, spec in parent['layers'].items():
            if name.startswith('glacier_'):
                continue
            if env['layers'].get(name, {}).get('sha256') != spec['sha256']:
                raise BundleIdentityError('Environment inherited terrain differs: ' + name)
        for kind, spec in parent.get('vectors', {}).items():
            if env.get('vectors', {}).get(kind, {}).get('sha256') != spec['sha256']:
                raise BundleIdentityError('Environment inherited vector differs')
        ocean = self.manifests['ocean']; ids = ocean.get('source_ids', {})
        if (ocean.get('schema') != 'dream-ocean-current-overlay-1'
                or ids.get('world') != src['terrain']['identity']
                or ids.get('climate') != src['climate']['identity']
                or ids.get('ocean_forcing') != src['ocean']['forcing_identity']
                or ocean.get('render', {}).get('atlas_environment_identity') != src['environment']['identity']
                or _grid(ocean['native_grid']) != _grid(parent['grid'])):
            raise BundleIdentityError('Ocean same-source/forcing/atlas binding differs')
        self.grids = {g: _grid(parent['grid']) for g in self.groups}
        self.grids['ocean'] = _grid(ocean['macro_grid'])
        self.specs = {
            'terrain': {n: deepcopy(s) for n, s in parent['layers'].items() if not n.startswith('glacier_')},
            'environment': deepcopy(env['layers']),
            'climate': deepcopy(self.climate.fields),
            'hydrology': deepcopy(self.manifests['hydrology']['fields']),
            'ocean': deepcopy(src['ocean']['fields']),
        }
        if 'surface_water' in self.groups:
            self.specs['surface_water'] = deepcopy(self.manifests['surface_water']['fields'])
        if set(self.specs['ocean']) != set(ocean['arrays']):
            raise BundleIdentityError('Registered ocean array set differs')
        for group, specs in self.specs.items():
            for name, spec in specs.items():
                spec.setdefault('shape', list(self.grids[group]['shape_zx']))
                spec['unit'] = spec.get('unit', spec.get('units', 'unknown'))
                spec['time_semantics'] = _time(group, name, spec['shape'])
                shape = spec['shape']; grid_shape = self.grids[group]['shape_zx']
                spec['queryable'] = (shape == grid_shape or shape == [12, *grid_shape])
                if group == 'surface_water' and (name.startswith(('mesh_', 'geometry_')) or name == 'order'):
                    spec['queryable'] = False
                if 'surface_water' in self.groups and group == 'hydrology':
                    spec['time_semantics'] += '; historical-noLake diagnostic, NOT final lake-aware discharge'
                if group == 'surface_water':
                    spec['time_semantics'] = 'finite-year month-end inventory or monthly flux; hillslope Q excludes lake interior/spill; not permanent-channel certification'
        if 'surface_water' in self.groups:
            self._validate_surface_water()
        # Track files validated by adapters too, including binding/checkpoints and vectors.
        for group in ('terrain', 'environment', 'climate', 'hydrology'):
            m = self.manifests[group]
            names = set(m.get('files', {}))
            for table in ('layers', 'fields', 'vectors', 'restart'):
                for spec in m.get(table, {}).values():
                    if isinstance(spec, dict) and 'file' in spec:
                        names.add(spec['file'])
            if group == 'climate':
                names.add('source-binding.json')
            for name in names:
                p = relative_file(self.paths[group], name)
                self._signatures[p] = _stat(p)
        # Ocean lacks a native full-file hash table: registry pins actual files,
        # without modifying source manifests. Its whole small array group is verified now.
        for name in self.specs['ocean']:
            self._array('ocean', name)
        self.routes = read_json(self._pinned_relative(src['ocean']['routes']))
        self._validate_previews()
        self.check_unchanged()

    def _validate_hydrology(self):
        """SavedClimateHydrology binding contract, purely static and read-only.

        Mirrors its saved-file/source/receiver/order/region checks, not its
        climate_source_from_map generation planner. No scientific solver here.
        """
        from terrain_pipeline.common_infra import identity, array_sha256
        m = self.manifests['hydrology']; refs = self.record['sources']
        source = self.manifests['terrain']; grid = _grid(source['grid'])
        shape = tuple(grid['shape_zx']); root = self.paths['hydrology']
        if (m.get('schema') != 'dream-climate-hydrology-year-1' or m.get('status') != 'complete'
                or m.get('identity') != identity({}, {k:v for k,v in m.items() if k != 'identity'})
                or not m.get('files') or not m.get('fields')):
            raise BundleIdentityError('Hydrology identity/schema/completion differs')
        loaded = {}
        for name, sha in m['files'].items():
            self._pinned(relative_file(root, name), sha)
        for name, spec in m['fields'].items():
            if m['files'].get(spec['file']) != spec['sha256']:
                raise BundleIdentityError('Hydrology field/file binding differs')
            a = np.load(relative_file(root, spec['file']), mmap_mode='r', allow_pickle=False)
            expected_shape = (12,*shape) if name.startswith('monthly_') else ((int(np.prod(shape)),) if name == 'order' else shape)
            if list(a.shape) != spec['shape'] or a.shape != expected_shape or str(a.dtype) != spec['dtype']:
                raise BundleIdentityError('Hydrology field descriptor/grid differs')
            loaded[name] = a
        required = {'monthly_routed_volume_m3','final_soil_water_mm','final_snow_swe_mm',
                    'final_ice_swe_mm','dynamic_glacier_mask','receiver','order'}
        if not required <= loaded.keys():
            raise BundleIdentityError('Missing hydrology publication fields')
        rec_spec = source['layers']['receiver']
        rec_path = self._pinned(relative_file(self.paths['terrain'], rec_spec['file']), rec_spec['sha256'])
        rec = np.load(rec_path, mmap_mode='r', allow_pickle=False)
        order = topological_order(rec)
        b = m['binding']
        if (b['source_identity'] != refs['terrain']['identity']
                or b['climate_identity'] != refs['climate']['identity']
                or b['climate_manifest_identity'] != self.climate.manifest_identity
                or b['world_seed'] != source['world_seed']
                or b['grid'] != dict(first_xz_m=grid['first_xz_m'], spacing_m=grid['spacing_m'], shape_zx=list(shape))
                or b['receiver_sha256'] != array_sha256(np.asarray(rec,np.int64).ravel())
                or b['order_sha256'] != array_sha256(order)
                or not np.array_equal(loaded['receiver'], rec)
                or not np.array_equal(loaded['order'], order)
                or m.get('calendar') != 'noleap365' or m.get('year') != 1
                or m.get('month_days') != self.climate.metadata['month_days']):
            raise BundleIdentityError('Hydrology source/climate/grid/receiver/calendar binding differs')
        if (m['fields']['monthly_routed_volume_m3']['units'] != 'm3/month'
                or any(m['fields'][n]['units'] != 'mm' for n in ('final_soil_water_mm','final_snow_swe_mm','final_ice_swe_mm'))
                or 'regions.json' not in m['files']):
            raise BundleIdentityError('Hydrology units/regions binding differs')
        regions = read_json(root/'regions.json')
        if [r['binding'] for r in regions] != b['regions']:
            raise BundleIdentityError('Hydrology region record binding differs')
        mask = np.zeros(shape, bool)
        for r in regions:
            rb = r['binding']; win = rb['window_zx']
            if (len(win) != 4 or any(type(i) is not int for i in win)
                    or not (0 <= win[0] < win[2] <= shape[0] and 0 <= win[1] < win[3] <= shape[1])):
                raise BundleIdentityError('Hydrology region grid differs')
            sl = np.s_[win[0]:win[2],win[1]:win[3]]
            if (mask[sl].any() or not any(v['identity'] == rb['old_identity'] and v['window_zx'] == win
                    for v in source.get('glacier_regions', []))
                    or rb['source_identity'] != refs['terrain']['identity']
                    or rb['new_climate_identity'] != refs['climate']['identity']
                    or r['metadata'].get('completed') is not True
                    or r['metadata'].get('completed_years') != 1
                    or r['ledger'].get('boundary_ice_out_m3') != 0):
                raise BundleIdentityError('Hydrology selected region source/completion differs')
            mask[sl] = True
        if loaded['dynamic_glacier_mask'].dtype != np.dtype('bool') or not np.array_equal(mask, loaded['dynamic_glacier_mask']):
            raise BundleIdentityError('Hydrology dynamic region support differs')
        for a in loaded.values():
            a._mmap.close()
        rec._mmap.close()

    def _validate_surface_water(self):
        """Static NumPy-only sixth-sidecar validation; never import lake core/TG solvers."""
        from terrain_pipeline.common_infra import identity, array_sha256
        m = self.manifests['surface_water']; b = m.get('binding', {}); refs = self.record['sources']
        grid = self.grids['surface_water']; shape = grid['shape_zx']; n = int(np.prod(shape))
        if (m.get('schema') != 'dream-climate-lake-year-1' or m.get('status') != 'finite-year-surface-water'
                or m.get('publishable') is not True or m.get('identity') != identity({}, {k:v for k,v in m.items() if k != 'identity'})
                or b.get('source_identity') != refs['terrain']['identity']
                or b.get('climate_identity') != refs['climate']['identity']
                or b.get('hydrology_identity') != refs['hydrology']['identity']
                or b.get('shape_zx') != shape or m.get('month_days') != self.climate.metadata['month_days']
                or b.get('calendar') != 'noleap365' or b.get('years') != 1 or not m.get('files')):
            raise BundleIdentityError('Surface-water identity/source/calendar binding differs')
        backend = m.get('backend')
        finite_csr = backend == 'tg-csr-reservoir-finite-conductance'
        if finite_csr:
            if (m.get('geometry_version') != 'dream-csr-finite-conductance-1'
                    or any(m.get(key) is not False for key in
                           ('channel_q_available', 'hydraulic_ready', 'natural_outlet_verified'))):
                raise BundleIdentityError('Surface-water finite-conductance backend policy differs')
        elif backend is not None or m.get('geometry_version') == 'dream-csr-finite-conductance-1':
            raise BundleIdentityError('Surface-water backend unsupported')
        if m.get('geometry_version') == 'tg-certified-single-sink-pool-dag-2':
            cert = m.get('geometry_certification', {})
            if (cert.get('status') != 'certified' or cert.get('unresolved_pool_count') != 0
                    or cert.get('unresolved_cell_count') != 0 or cert.get('unresolved_pools') != []
                    or cert.get('certified_pool_count') != cert.get('pool_count')):
                raise BundleIdentityError('Surface-water single-sink geometry not certified')
        root = self.paths['surface_water']; fields = self.specs['surface_water']; loaded = {}
        monthly_units = dict(soil_mm='mm', runoff_mm='mm/month', land_actual_et_mm='mm/month',
            lake_volume_m3='m3', lake_stage_m='m', lake_depth_m='m', wet_mask='1', lake_et_demand_m3='m3/month',
            soil_to_lake_m3='m3/month', direct_lake_liquid_m3='m3/month', terminal_overflow_m3='m3/month',
            hillslope_routed_volume_m3='m3/month', hillslope_discharge_m3_s='m3/s', hillslope_q_support='1',
            lake_actual_et_m3='m3/month', flow_wet_support='1', monthly_liquid_input_mm='mm/month',
            monthly_snow_swe_mm='mm', monthly_ice_swe_mm='mm')
        static_units = dict(receiver='1', order='1', old_no_lake_receiver='1', basin_id='1',
            mesh_node_x_m='m', mesh_node_z_m='m', annual_mean_hillslope_discharge_m3_s='m3/s',
            geometry_parent='1', geometry_birth_m='m', geometry_crest_m='m', geometry_cell_node='1',
            geometry_area_m2='m2', mesh_indptr='1', mesh_indices='1')
        if not set(monthly_units).union(static_units) <= fields.keys():
            raise BundleIdentityError('Surface-water required fields missing')
        for filename, sha in m['files'].items():
            self._pinned(relative_file(root, filename), sha)
        try:
            for name, spec in fields.items():
                if (m['files'].get(spec['file']) != spec.get('sha256')
                        or spec.get('units') != {**monthly_units, **static_units}.get(name)):
                    raise BundleIdentityError('Surface-water field hash/unit differs: ' + name)
                a = np.load(relative_file(root, spec['file']), mmap_mode='r', allow_pickle=False)
                loaded[name] = a
                expected = [12, *shape] if name in monthly_units else shape
                if name in ('order', 'mesh_node_x_m', 'mesh_node_z_m'):
                    expected = [n]
                elif name == 'mesh_indptr':
                    expected = [n+1]
                elif name in ('geometry_parent', 'geometry_birth_m', 'geometry_crest_m', 'mesh_indices'):
                    expected = spec['shape'] if len(spec['shape']) == 1 else []
                if list(a.shape) != spec['shape'] or list(a.shape) != expected or str(a.dtype) != spec['dtype']:
                    raise BundleIdentityError('Surface-water array descriptor/grid differs: ' + name)
            rec = loaded['receiver']; order = loaded['order']; r = rec.ravel()
            if (rec.dtype.kind not in 'iu' or order.dtype.kind not in 'iu' or np.any(r < -1) or np.any(r >= n)
                    or not np.array_equal(np.sort(order), np.arange(n))):
                raise BundleIdentityError('Surface-water receiver/order invalid')
            rank = np.empty(n, np.int64); rank[order] = np.arange(n); donors = np.flatnonzero(r >= 0)
            if np.any(rank[r[donors]] >= rank[donors]):
                raise BundleIdentityError('Surface-water receiver cyclic/order invalid')
            bed = self._array('terrain', 'elevation_m'); status = self._array('terrain', 'status')
            lagoon = (self._array('terrain', 'registered_lagoon').astype(bool)
                      if 'registered_lagoon' in self.specs['terrain'] else np.zeros(shape, bool))
            outlets = (status == 3) | lagoon
            if b.get('finite_boundary') is True:
                outlets[[0,-1], :] = True; outlets[:, [0,-1]] = True
            elif b.get('finite_boundary') is not False:
                raise BundleIdentityError('Surface-water finite outlet policy missing')
            geo = m.get('geometry_binding', {})
            if (b.get('mesh_seed') != 15386822478918853569 or geo.get('mesh_seed') != 15386822478918853569
                    or m.get('lagoon_binding', {}).get('origin') != 'saved registered_lagoon layer'
                    or geo.get('bed_sha256') != array_sha256(bed)
                    or geo.get('receiver_sha256') != array_sha256(r)
                    or geo.get('outlet_sha256') != array_sha256(outlets)
                    or m.get('lagoon_binding', {}).get('array_sha256') != array_sha256(lagoon)
                    or not np.array_equal(loaded['old_no_lake_receiver'], self._array('terrain', 'receiver'))
                    or np.any(r[outlets.ravel()] != -1)):
                raise BundleIdentityError('Surface-water physical bed/lagoon/outlet/receiver binding differs')
            ip, ix = loaded['mesh_indptr'], loaded['mesh_indices']
            if (ip.dtype.kind not in 'iu' or ix.dtype.kind not in 'iu' or ip[0] != 0 or ip[-1] != ix.size
                    or np.any(np.diff(ip) < 0) or np.any(ix < 0) or np.any(ix >= n)):
                raise BundleIdentityError('Surface-water CSR mesh invalid')
            for cell in donors:
                if r[cell] not in ix[ip[cell]:ip[cell+1]] or bed.ravel()[r[cell]] > bed.ravel()[cell]:
                    raise BundleIdentityError('Surface-water receiver not a bed-descending CSR edge')
            for name in ('wet_mask', 'hillslope_q_support', 'flow_wet_support'):
                if loaded[name].dtype != np.dtype('bool'):
                    raise BundleIdentityError('Surface-water support must be boolean')
            for month in range(12):
                wet = loaded['wet_mask'][month]; support = loaded['hillslope_q_support'][month]
                depth = loaded['lake_depth_m'][month]; stage = loaded['lake_stage_m'][month]
                volume = loaded['lake_volume_m3'][month]
                if (not np.isfinite(stage).all() or not np.isfinite(depth).all() or np.any(depth < 0)
                        or not np.allclose(depth, np.maximum(stage-bed, 0), rtol=0, atol=1e-8)
                        or not np.allclose(volume, depth*loaded['geometry_area_m2'], rtol=1e-10, atol=1e-6)
                        or not np.array_equal(wet, volume > 0)):
                    raise BundleIdentityError('Surface-water physical stage/depth/stock/wet differs')
                q = loaded['hillslope_discharge_m3_s'][month]
                if (np.any(support & (wet | loaded['flow_wet_support'][month]))
                        or np.any(np.isfinite(q[~support])) or np.any(~np.isfinite(q[support])) or np.any(q[support] < 0)):
                    raise BundleIdentityError('Surface-water Q/support semantics differ')
            for key in ('hillslope_draw_file', 'spill_routes_file', 'water_budget_file'):
                if m.get(key) not in m['files']:
                    raise BundleIdentityError('Surface-water vector/budget file not pinned')
            for name in ('geometry_parent', 'geometry_birth_m', 'geometry_crest_m'):
                if loaded[name].size != loaded['geometry_parent'].size:
                    raise BundleIdentityError('Surface-water lake-tree descriptor size differs')
            if (not np.isfinite(loaded['geometry_area_m2']).all() or np.any(loaded['geometry_area_m2'] <= 0)
                    or not np.isfinite(loaded['mesh_node_x_m']).all() or not np.isfinite(loaded['mesh_node_z_m']).all()):
                raise BundleIdentityError('Surface-water cell geometry invalid')
            if finite_csr:
                self._validate_csr_surface_water(m, loaded, bed, outlets)
            self.surface_rivers = read_json(root/m['hillslope_draw_file'])
            self.surface_spills = read_json(root/m['spill_routes_file'])
            if (len(self.surface_rivers.get('draw_segments', [])) != 12 or len(self.surface_spills) != 12
                    or any(not isinstance(v, list) for v in self.surface_spills)
                    or any(not isinstance(v, list) for v in self.surface_rivers['draw_segments'])):
                raise BundleIdentityError('Surface-water monthly vectors invalid')
            for month in range(12):
                for item in self.surface_rivers['draw_segments'][month] + self.surface_spills[month]:
                    coords = np.asarray(item.get('points_xz_m'), dtype=float)
                    if (item.get('month') != month+1 or coords.ndim != 2 or coords.shape[1] != 2
                            or coords.shape[0] < 2 or not np.isfinite(coords).all()):
                        raise BundleIdentityError('Surface-water vector month/coordinates differ')
        finally:
            for a in loaded.values():
                a._mmap.close()

    def _validate_csr_surface_water(self, meta, arrays, bed, outlets):
        """Saved engineering owner/face accounting only; no TG/Numba/ODE import."""
        root = self.paths['surface_water']
        owner = arrays['geometry_cell_node'].ravel()
        count = arrays['geometry_parent'].size
        if (owner.dtype.kind not in 'iu' or np.any(owner < -1) or np.any(owner >= count)
                or not np.array_equal(owner, arrays['basin_id'].ravel())
                or not np.array_equal(owner < 0, outlets.ravel())
                or np.any(arrays['geometry_parent'] != -1)):
            raise BundleIdentityError('Surface-water CSR flat owner descriptors differ')
        for key in ('face_ledger_file', 'water_budget_file'):
            if meta.get(key) not in meta['files']:
                raise BundleIdentityError('Surface-water CSR accounting file not pinned')
        ledger = read_json(relative_file(root, meta['face_ledger_file']))
        budgets = read_json(relative_file(root, meta['water_budget_file']))
        if count == 0:
            if meta.get('topology_file') is not None or ledger != [] or np.any(arrays['lake_volume_m3'] != 0):
                raise BundleIdentityError('Surface-water empty CSR owner domain differs')
            return
        if meta.get('topology_file') not in meta['files']:
            raise BundleIdentityError('Surface-water CSR topology not pinned')
        topology = read_json(relative_file(root, meta['topology_file']))
        payload = {key: topology[key] for key in ('metadata', 'arrays', 'faces', 'engineering_boundaries')}
        payload['schema'] = 'td-original-bed-overflow-topology-v1'
        topology_identity = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if topology.get('identity_sha256') != topology_identity or meta.get('geometry_identity') != topology_identity:
            raise BundleIdentityError('Surface-water CSR topology identity differs')
        tm = topology['metadata']
        if any(tm.get(key) is not False for key in ('original_source_certified', 'hydraulic_ready', 'natural_outlet_verified')):
            raise BundleIdentityError('Surface-water CSR topology is not engineering-only')
        curves = topology['arrays']
        leaves = np.asarray(curves['leaf_ids'])
        offsets = np.asarray(curves['curve_offsets'])
        levels = np.asarray(curves['curve_level_m'], float)
        areas = np.asarray(curves['curve_area_m2'], float)
        leaf_area = np.asarray(curves['leaf_area_m2'], float)
        if (leaves.shape != (count,) or leaves.dtype.kind not in 'iu' or np.any(leaves < 0)
                or np.any(leaves >= owner.size) or len(np.unique(leaves)) != count
                or not np.array_equal(owner[leaves], np.arange(count))
                or offsets.shape != (count+1,) or offsets.dtype.kind not in 'iu' or offsets[0] != 0
                or offsets[-1] != levels.size or np.any(np.diff(offsets) <= 0)
                or areas.shape != levels.shape or leaf_area.shape != (count,)
                or not np.isfinite(levels).all() or not np.isfinite(areas).all() or np.any(areas <= 0)):
            raise BundleIdentityError('Surface-water CSR owner curves invalid')
        selected = np.flatnonzero(owner >= 0)
        selected = selected[np.argsort(owner[selected], kind='stable')]
        cuts = np.r_[0, np.cumsum(np.bincount(owner[selected], minlength=count))]
        z, area = bed.ravel(), arrays['geometry_area_m2'].ravel()
        for k in range(count):
            ids = selected[cuts[k]:cuts[k+1]]
            lv, inverse = np.unique(z[ids], return_inverse=True)
            weights = np.bincount(inverse, weights=area[ids])
            sl = slice(offsets[k], offsets[k+1])
            for month in range(12):
                wet_ids = ids[arrays['wet_mask'][month].ravel()[ids]]
                if wet_ids.size:
                    stage = arrays['lake_stage_m'][month].ravel()[wet_ids]
                    expected = np.maximum(z[ids], stage[0])
                    if (not np.allclose(stage, stage[0], rtol=0, atol=1e-7)
                            or not np.allclose(arrays['lake_stage_m'][month].ravel()[ids], expected, rtol=0, atol=1e-7)):
                        raise BundleIdentityError('Surface-water CSR owner has inconsistent wet stage')
            if (not np.array_equal(lv, levels[sl]) or not np.allclose(weights, areas[sl], rtol=1e-12, atol=1e-6)
                    or not np.isclose(area[ids].sum(), leaf_area[k], rtol=1e-12, atol=1e-6)
                    or arrays['geometry_birth_m'][k] != lv[0]):
                raise BundleIdentityError('Surface-water CSR curves differ from actual owner bed/area')
        ip, ix = arrays['mesh_indptr'], arrays['mesh_indices']
        lookup = {int(leaf): k for k, leaf in enumerate(leaves)}
        first, second, boundary_owner = [], [], []
        for face in topology['faces']:
            c, j = face['cell_ids']; a, b = face['leaf_ids']
            if (not 0 <= c < owner.size or not 0 <= j < owner.size or j not in ix[ip[c]:ip[c+1]]
                    or a not in lookup or b not in lookup or a == b
                    or owner[c] != lookup[a] or owner[j] != lookup[b] or face['sill_m'] != max(z[c], z[j])):
                raise BundleIdentityError('Surface-water CSR face is not its real owner saddle edge')
            first.append(lookup[a]); second.append(lookup[b])
        for face in topology['engineering_boundaries']:
            c, j = face['cell_id'], face['receiver_cell_id']
            if (not 0 <= c < owner.size or not 0 <= j < owner.size or not outlets.ravel()[j]
                    or j not in ix[ip[c]:ip[c+1]] or face['leaf_id'] not in lookup
                    or owner[c] != lookup[face['leaf_id']] or face['sill_m'] != max(z[c], z[j])):
                raise BundleIdentityError('Surface-water CSR terminal is not a real declared boundary edge')
            boundary_owner.append(int(owner[c]))
        if len(ledger) != 12 or len(budgets) != 12:
            raise BundleIdentityError('Surface-water CSR twelve-month owner accounting required')
        def values(row, key, size, signed=False):
            value = np.asarray(row.get(key), float)
            if value.shape != (size,) or not np.isfinite(value).all() or (not signed and np.any(value < 0)):
                raise BundleIdentityError('Surface-water CSR ledger values invalid: ' + key)
            return value
        for month, row in enumerate(ledger):
            if row.get('month') != month+1 or budgets[month].get('month') != month+1:
                raise BundleIdentityError('Surface-water CSR ledger month differs')
            forward = values(row, 'face_forward_m3', len(first))
            reverse = values(row, 'face_reverse_m3', len(first))
            net = values(row, 'face_net_m3', len(first), True)
            exports = values(row, 'boundary_exports_m3', len(boundary_owner))
            initial = values(row, 'owner_initial_m3', count)
            withdrawn = values(row, 'owner_withdrawn_m3', count)
            after = values(row, 'owner_after_exchange_m3', count)
            final = values(row, 'owner_final_m3', count)
            residual = values(row, 'owner_residual_m3', count, True)
            correction = (values(row, 'roundoff_correction_by_owner_m3', count, True)
                          if 'roundoff_correction_by_owner_m3' in row else np.zeros(count))
            incoming = (np.bincount(second, weights=net, minlength=count)
                        - np.bincount(first, weights=net, minlength=count))
            boundary = np.bincount(boundary_owner, weights=exports, minlength=count)
            computed = initial - withdrawn + incoming - boundary + correction - after
            stocks = np.bincount(owner[selected], weights=arrays['lake_volume_m3'][month].ravel()[selected], minlength=count)
            received = (np.bincount(second, weights=forward, minlength=count)
                        + np.bincount(first, weights=reverse, minlength=count))
            tolerance = 1e-6 + 1e-9*np.maximum(initial + received, 1.)
            if 'owner_postexchange_soil_transfer_m3' in row:
                post_transfer = values(row, 'owner_postexchange_soil_transfer_m3', count)
                if np.any(np.abs(final - after - post_transfer) > tolerance):
                    raise BundleIdentityError('Surface-water CSR post-exchange soil transfer differs')
            if (not np.allclose(net, forward-reverse, rtol=1e-12, atol=1e-6)
                    or np.any(final < after - tolerance)
                    or np.any(withdrawn > initial) or np.any(np.abs(computed-residual) > tolerance)
                    or np.any(np.abs(residual) > tolerance) or np.any(np.abs(correction) > tolerance)
                    or not np.allclose(stocks, final, rtol=1e-9, atol=1e-6)
                    or not np.isclose(final.sum(), budgets[month].get('final_lake_m3', np.nan), rtol=1e-9, atol=1e-6)):
                raise BundleIdentityError('Surface-water CSR owner stock/face account differs')

    def _pinned(self, path, sha):
        if not path.is_file():
            raise BundleMissing('Registered file is missing')
        before = _stat(path)
        if digest(path) != sha or _stat(path) != before:
            raise BundleIdentityError('Registered file hash differs: ' + path.name)
        self._signatures[path] = before
        return path

    def _pinned_relative(self, spec):
        return self._pinned(relative_file(self.root, spec['path']), spec['sha256'])

    def check_unchanged(self):
        for path, signature in self._signatures.items():
            if not path.is_file():
                raise BundleMissing('Registered immutable source is missing')
            if _stat(path) != signature:
                raise BundleIdentityError('Immutable bundle changed; re-registration required')

    def _array(self, group, name):
        key = (group, name)
        with self._lock:
            if key not in self._arrays:
                spec = self.specs[group][name]
                p = relative_file(self.paths[group], spec['file'])
                self._pinned(p, spec['sha256'])
                a = np.load(p, mmap_mode='r', allow_pickle=False)
                if list(a.shape) != spec['shape'] or str(a.dtype) != spec['dtype'] or not a.flags.c_contiguous:
                    raise BundleIdentityError('Array descriptor differs: ' + group + '.' + name)
                a.flags.writeable = False
                self._arrays[key] = a
            return self._arrays[key]

    def _validate_previews(self):
        from PIL import Image
        # Registered provenance files prevent frame metadata drifting independently.
        for spec in self.record.get('preview_metadata', []):
            self._pinned_relative(spec)
        for spec in self.record.get('previews', []):
            for item in spec['files'].values():
                p = self._pinned_relative(item)
                with Image.open(p) as image:
                    if list(image.size) != spec['image_size'] or image.format != 'PNG':
                        raise BundleIdentityError('Preview dimensions/format differ')
            rect = spec.get('map_rect')
            if spec['georeferenced']:
                if (not rect or spec['world_extent_m'] != _extent(self.grids['terrain'])
                        or min(rect.values()) < 0 or rect['x']+rect['width'] > spec['image_size'][0]
                        or rect['y']+rect['height'] > spec['image_size'][1]):
                    raise BundleIdentityError('Preview coordinate frame differs')
            elif rect is not None or spec.get('world_extent_m') is not None:
                raise BundleIdentityError('Non-georeferenced panels cannot be sampled')

    def detail(self):
        self.check_unchanged()
        previews = []
        for p in self.record.get('previews', []):
            out = {k: deepcopy(v) for k, v in p.items() if k != 'files'}
            out['url'] = f'/api/inner/map-bundles/{self.id}/preview/{p["key"]}'
            previews.append(out)
        groups = {}
        for group in self.groups:
            fields = {}
            for name, spec in self.specs[group].items():
                fields[name] = {k: deepcopy(v) for k, v in spec.items() if k not in ('file', 'sha256')}
            groups[group] = dict(fields=fields, grid=self.grids[group], source=self.record['sources'][group]['path'],
                identity=self.record['sources'][group].get('identity'),
                status=self.manifests[group].get('status', 'frozen'),
                limitations=self.manifests[group].get('limitations', []))
            if group == 'surface_water':
                manifest = self.manifests[group]
                groups[group]['limitations'] = [manifest.get('flow_scope', 'hillslope Q only; spill paths separate'),
                    'Finite empty-stock year, NOT permanent-channel existence or long-term perennial certification',
                    manifest.get('lake_actual_et_map_semantics', 'lake_actual_et_m3 is connected-pool demand attribution, not local column extraction'),
                    'flow_wet_support is monthly maximum wet for line cutting; wet_mask is final month-end wet',
                    *manifest.get('limitations', [])]
                if manifest.get('backend') == 'tg-csr-reservoir-finite-conductance':
                    groups[group]['limitations'].extend([
                        manifest.get('splitting', 'month-start source impulse; owner-local PET; finite monthly exchange'),
                        manifest.get('lake_evaporation', 'owner-local, not whole-connected-pool withdrawal'),
                        'Engineering finite conductance; NOT instant equilibration, natural-outlet or hydraulic-ready certification'])
        return safe_json(dict(id=self.id, title=self.record['title'], status=self.record['status'], producer='Terragenesis',
            coordinate_system='metres; X east, Z south; finite no wrap; nearest saved cell (no class interpolation)',
            grid=self.grids['terrain'], world_extent_m=_extent(self.grids['terrain']), groups=groups,
            previews=previews, warnings=self.record.get('warnings', WARNINGS), history=self.record.get('history', []),
            stable_biome_ids=self.manifests['environment'].get('stable_biome_ids', {}),
            limits=dict(max_values=MAX_VALUES, max_vector_page=MAX_VECTOR_PAGE), author_only=True,
            default_story_publication=False))

    def preview(self, key, month=1):
        self.check_unchanged()
        for spec in self.record.get('previews', []):
            if spec['key'] == key:
                file = spec['files'].get(str(month) if spec['months'] else 'static')
                if file is None:
                    raise BundleMissing('No saved preview for selected month')
                return relative_file(self.root, file['path'])
        raise BundleMissing('Preview key is not registered')

    def _cell(self, group, x, z):
        grid = self.grids[group]; first = grid['first_xz_m']; d = grid['spacing_m']
        col, row = (x-first[0])/d, (z-first[1])/d
        nz, nx = grid['shape_zx']
        if not (-.5 <= row < nz-.5 and -.5 <= col < nx-.5):
            return None
        return int(math.floor(row+.5)), int(math.floor(col+.5))

    def _values(self, group, names, window, months):
        z0, x0, z1, x1 = window
        arrays = {}
        for name in names:
            spec = self.specs[group][name]
            a = self._array(group, name)
            value = a[..., z0:z1, x0:x1]
            if a.ndim == 3:
                value = value[np.asarray(months)-1]
            value = np.array(value, copy=True)
            if spec.get('nodata') is not None:
                value = np.where(value == spec['nodata'], np.nan, value)
            # Do not turn dry macro cells or fine-grid land into SST/current.
            if group == 'ocean' and name.startswith('monthly_'):
                wet = self._array('ocean', 'ocean_mask')[z0:z1, x0:x1]
                grid = self.grids['ocean']
                xs = grid['first_xz_m'][0] + np.arange(x0, x1)*grid['spacing_m']
                zs = grid['first_xz_m'][1] + np.arange(z0, z1)*grid['spacing_m']
                xx, zz = np.meshgrid(xs, zs)
                status = self.environment.sample(xx, zz, ['status'])['status']
                value = np.where(wet & (status == 3), value, np.nan)
            if group == 'surface_water' and name in ('hillslope_discharge_m3_s', 'hillslope_routed_volume_m3'):
                support = self._array(group, 'hillslope_q_support')[np.asarray(months)-1, z0:z1, x0:x1]
                value = np.where(support, value, np.nan)
            arrays[name] = value
        return arrays

    def point(self, x_m, z_m, month=1):
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError('month must be 1..12')
        if type(x_m) not in (float, int) or type(z_m) not in (float, int) or not np.isfinite([x_m, z_m]).all():
            raise ValueError('Finite metric coordinates required')
        self.check_unchanged()
        if self._cell('terrain', x_m, z_m) is None:
            raise ValueError('Point outside registered world extent')
        groups = {}
        native_cell = self._cell('terrain', x_m, z_m)
        iz, ix = native_cell
        native_ocean = bool(self._array('terrain', 'status')[iz, ix] == 3)
        for group in self.groups:
            cell = self._cell(group, x_m, z_m)
            names = [n for n, s in self.specs[group].items() if s['queryable']]
            if cell is None:
                values = {n: None for n in names}
            else:
                iz, ix = cell
                arrays = self._values(group, names, [iz, ix, iz+1, ix+1], [month])
                values = {n: safe_json(a.reshape(-1)[0]) for n, a in arrays.items()}
                if group == 'ocean' and not native_ocean:
                    values = {n: (None if n.startswith('monthly_') else v) for n, v in values.items()}
            groups[group] = dict(values=values, units={n: self.specs[group][n]['unit'] for n in names},
                cell_zx=cell, sampling='nearest saved cell; no interpolation',
                status='potential/unvalidated' if group == 'terrain' else self.manifests[group].get('status', 'frozen'))
        self.check_unchanged()
        return safe_json(dict(bundle_id=self.id, point=dict(x_m=x_m, z_m=z_m), month=month,
                              groups=groups, warnings=self.record.get('warnings', WARNINGS)))

    def query(self, fields, window, months=(1,)):
        self.check_unchanged()
        if (not fields or len(fields) > 64 or len(set(fields)) != len(fields)
                or not months or len(months) > 12
                or any(type(m) is not int or not 1 <= m <= 12 for m in months)):
            raise ValueError('Invalid fields/months selection')
        selected = []
        for field in fields:
            if not isinstance(field, str) or field.count('.') != 1:
                raise ValueError('Fields require group.field prefix')
            group, name = field.split('.')
            spec = self.specs.get(group, {}).get(name)
            if not spec or not spec['queryable']:
                raise ValueError('Field unavailable or descriptor-only: ' + field)
            selected.append((field, group, name, spec))
        grid = self.grids[selected[0][1]]
        if any(self.grids[g] != grid for _, g, _, _ in selected):
            raise ValueError('Independent ocean grid requires a separate query')
        nz, nx = grid['shape_zx']
        if (len(window) != 4 or any(type(v) is not int for v in window)
                or not (0 <= window[0] < window[2] <= nz and 0 <= window[1] < window[3] <= nx)):
            raise ValueError('Window must be [z0,x0,z1,x1] inside selected grid')
        count = (window[2]-window[0])*(window[3]-window[1])*sum(len(months) if len(s['shape']) == 3 else 1 for _, _, _, s in selected)
        if count > MAX_VALUES:
            raise ValueError('Query exceeds MAX_VALUES=65536')
        arrays = {f: self._values(g, [n], window, months)[n] for f, g, n, _ in selected}
        out_grid = deepcopy(grid)
        out_grid['first_xz_m'] = [grid['first_xz_m'][0]+window[1]*grid['spacing_m'], grid['first_xz_m'][1]+window[0]*grid['spacing_m']]
        out_grid['shape_zx'] = [window[2]-window[0], window[3]-window[1]]
        self.check_unchanged()
        return safe_json(dict(bundle_id=self.id, arrays=arrays, units={f:s['unit'] for f, _, _, s in selected},
                              grid=out_grid, months=months, window=window, value_count=count))

    def vectors(self, kind, month=1, offset=0, limit=100):
        self.check_unchanged()
        if type(month) is not int or not 1 <= month <= 12 or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= MAX_VECTOR_PAGE:
            raise ValueError('Invalid vector month/page')
        if kind == 'ocean-currents':
            items = [v for v in self.routes['routes'] if v['month'] == month]
            status = 'finite-year-candidate'
        elif kind in ('surface-rivers', 'surface-spills') and 'surface_water' in self.groups:
            items = (self.surface_rivers['draw_segments'] if kind == 'surface-rivers' else self.surface_spills)[month-1]
            status = ('finite-year hillslope supply symbols; NOT lake-interior/total Q or permanent channel existence'
                      if kind == 'surface-rivers' else 'finite-year net CSR schematic spill symbols; NOT hydraulic receiver Q')
        elif kind in ('rivers', 'lakes'):
            # Standard adapter validates and preserves topology/coordinates.
            items = self.environment.vectors(kind)
            status = 'potential/unvalidated' if kind == 'lakes' else 'frozen original topology; no vector discharge attributed'
            if 'surface_water' in self.groups:
                status += '; historical-potential, NOT current lake-aware water layer'
        else:
            raise BundleMissing('Vector kind is not registered')
        page = deepcopy(items[offset:offset+limit])
        if kind == 'lakes':
            for item in page:
                item['status'] = 'potential/unvalidated'
                item['permanent'] = False
        return safe_json(dict(bundle_id=self.id, kind=kind, month=month, items=page, total=len(items),
                              offset=offset, limit=limit, status=status))


class BundleRegistry:
    def __init__(self, root, registry='config/map-bundles.json'):
        self.root = Path(root).resolve()
        self.path = self.root / registry
        self._cache = OrderedDict()
        self._lock = RLock()

    def _records(self):
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if data.get('schema') != 'dream-map-bundles-1':
            raise BundleIdentityError('Unsupported bundle registry')
        records = data['bundles']
        ids = [r['id'] for r in records]
        if len(set(ids)) != len(ids) or any(not ID_RE.fullmatch(i) for i in ids):
            raise BundleIdentityError('Invalid registry IDs')
        return records

    def list(self):
        return dict(bundles=[{k: deepcopy(r[k]) for k in ('id', 'title', 'status')}
                             for r in self._records()])

    def get(self, bundle_id):
        if not ID_RE.fullmatch(bundle_id):
            raise BundleMissing('Bundle is not registered')
        record = next((r for r in self._records() if r['id'] == bundle_id), None)
        if record is None:
            raise BundleMissing('Bundle is not registered')
        key = json.dumps(record, sort_keys=True)
        with self._lock:
            if key not in self._cache:
                loaded = MapBundle(self.root, record)
                self._cache[key] = loaded
                while len(self._cache) > 2:
                    self._cache.popitem(last=False)
            self._cache.move_to_end(key)
            bundle = self._cache[key]
            bundle.check_unchanged()
            return bundle
