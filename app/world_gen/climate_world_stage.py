"""Read-only world-map seam to TG's bounded game-diagnostic climate API.

No physical-process parent is invented. The saved irregular receiver is retained;
only its downstream-first topological permutation is derived. No terrain evolves.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np

from app.map_source import load_source
from app.world_gen.terragenesis_bridge import ensure_path

SCHEMA = 'dream-climate-world-stage-1'
DEFAULT_SOURCE_IDENTITY = '6d99aafd0b11d83e6af1358195dcab5b3c437771e9f5466fa7ceb7eb8dd514e4'
DEFAULT_CONFIG = dict(atmosphere_backend='game-diagnostic', reference_latitude_deg=0.,
    reference_longitude_deg=0., center_xz_m=[0., 0.], radius_m=6371000.,
    macro_spacing_m=40000., max_macro_cells=65536, max_world_cells=1000000,
    diagnostic=dict(exterior_water_kg_m2=0., open_faces=[]), snow_ice=dict(enabled=False))


def climate_module():
    """Import TG read-only; bytecode and numba caches never land in its tree."""
    sys.dont_write_bytecode = True
    os.environ.setdefault('NUMBA_CACHE_DIR', str(Path(tempfile.gettempdir())/'dream-climate-numba'))
    ensure_path()
    from terrain_pipeline import world_climate
    return world_climate


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(_canonical(value), encoding='utf-8')
    temporary.replace(path)


def configuration(config=None):
    cfg = deepcopy(DEFAULT_CONFIG)
    for name, value in (config or {}).items():
        if name in ('diagnostic', 'snow_ice') and isinstance(value, dict):
            cfg[name].update(deepcopy(value))
        else:
            cfg[name] = deepcopy(value)
    if cfg['atmosphere_backend'] != 'game-diagnostic':
        raise ValueError('This stage requires game-diagnostic, never legacy-synthetic rain')
    if cfg.get('snow_ice', {}).get('enabled'):
        raise ValueError('Snow/ice is a separate downstream handoff; this stage is liquid diagnostic only')
    return cfg


def topological_order(receiver):
    """Kahn sort, then reverse: TG accumulate_graph requires receiver before donor."""
    raw = np.asarray(receiver)
    if raw.dtype.kind not in 'iu':
        raise ValueError('Integer receiver required')
    rec = raw.astype(np.int64).ravel()
    if np.any(rec < -1) or np.any(rec >= rec.size):
        raise ValueError('Receiver index outside source grid')
    degree = np.bincount(rec[rec >= 0], minlength=rec.size)
    queue = deque(np.flatnonzero(degree == 0).tolist())
    forward = np.empty(rec.size, np.int64)
    count = 0
    while queue:
        cell = queue.popleft()
        forward[count] = cell
        count += 1
        target = int(rec[cell])
        if target >= 0:
            degree[target] -= 1
            if degree[target] == 0:
                queue.append(target)
    if count != rec.size:
        raise ValueError('Receiver cycle; refusing to reconstruct drainage')
    return forward[::-1].copy()


def climate_source_from_map(source_map, *, expected_identity):
    """Validate actual map identity, preserve bed dtype, bind the extra receiver."""
    if not expected_identity:
        raise ValueError('Explicit expected source identity required')
    root = Path(source_map).resolve()
    mapped = load_source('world-map-product', root, expected_identity=expected_identity)
    info = mapped.info
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest['identity'] != info.identity:
        raise ValueError('Source manifest changed during load')
    if info.grid_semantics != 'cell-centre':
        raise ValueError('Climate source must use cell-centre grid semantics')
    x, z = info.first_sample_xz_m
    nz, nx = info.shape_zx
    crop = mapped.crop(x, z, x+nx*info.spacing_m, z+nz*info.spacing_m,
                       layers=('elevation_m', 'status'), max_cells=nz*nx)
    bed, status = crop['elevation_m'], crop['status']
    if bed.dtype != np.dtype('float64') or not np.isfinite(bed).all():
        raise ValueError('Actual finite float64 elevation_m terrain bed required')
    if not crop['complete'] or not np.isin(status, [3, 4, 5]).all():
        raise ValueError('Complete known ocean/closed/land support required')
    spec = manifest['layers']['receiver']
    path = (root/spec['file']).resolve()
    if not path.is_relative_to(root) or spec.get('unit') != '1' or _sha(path) != spec['sha256']:
        raise ValueError('Receiver manifest path/hash/unit differs')
    if manifest.get('files', {}).get(spec['file'], spec['sha256']) != spec['sha256']:
        raise ValueError('Receiver file binding differs')
    receiver = np.load(path, mmap_mode='r', allow_pickle=False)
    if receiver.shape != bed.shape or str(receiver.dtype) != spec['dtype']:
        raise ValueError('Receiver descriptor/grid differs')
    order = topological_order(receiver)
    source = dict(elevation_m=bed, ocean_mask=status == 3, receiver=receiver,
        order=order, first_xz_m=list(info.first_sample_xz_m), spacing_m=float(info.spacing_m),
        world_seed=info.world_seed, source_identity=info.identity, source_product_path=str(root))
    # Validates below-sea ocean, bounded coordinates, support and seed without solving.
    climate_module().plan_climate(source, configuration())
    for value in source.values():
        if isinstance(value, np.ndarray):
            value.flags.writeable = False
    return source


def plan(source, config=None, references=None):
    return climate_module().plan_climate(source, configuration(config), references)


def prepare(source, out_dir, config=None, references=None, *, recover=False):
    """Native product/checkpoint plus source binding; recover is read-only, not resume.

    TG rejects diagnostic initial_state: interrupted years must be rerun in a NEW
    directory. There is deliberately no coupled/month-level continuation claim.
    """
    climate = climate_module()
    cfg = configuration(config)
    planned = plan(source, cfg, references)
    if planned['status'] != 'ready':
        raise ValueError('Climate pending: '+str(planned['missing']))
    from terrain_pipeline.common_infra import array_sha256
    binding = dict(schema=SCHEMA, source_identity=source['source_identity'],
        world_seed=source['world_seed'], first_xz_m=source['first_xz_m'],
        spacing_m=source['spacing_m'], shape_zx=list(source['elevation_m'].shape),
        terrain_sha256=array_sha256(source['elevation_m']),
        ocean_sha256=array_sha256(source['ocean_mask']),
        receiver_sha256=array_sha256(np.asarray(source['receiver'], np.int64).ravel()),
        order_sha256=array_sha256(source['order']), config=planned['config'],
        reference_identity=planned['reference_identity'])
    root = Path(out_dir).resolve()
    parent = Path(source.get('source_product_path', root.parent/'unused')).resolve()
    if root == parent or root.is_relative_to(parent):
        raise ValueError('Climate output must not be inside frozen source')
    checkpoint = root/'source-binding.json'
    if recover:
        if not checkpoint.exists() or json.loads(checkpoint.read_text(encoding='utf-8')) != binding:
            raise ValueError('Climate recovery source/config binding differs')
        loaded = climate.query_climate(root)  # verifies all saved fields, no solve
        meta = loaded['metadata']
        if (meta['source_identity'] != binding['source_identity'] or
                meta['world_seed'] != binding['world_seed'] or
                meta['first_xz_m'] != binding['first_xz_m'] or
                meta['spacing_m'] != binding['spacing_m'] or
                meta['shape_zx'] != binding['shape_zx'] or
                not np.array_equal(loaded['arrays']['ocean_mask'], source['ocean_mask']) or
                meta['terrain_sha256'] != binding['terrain_sha256'] or
                meta['config'] != binding['config'] or
                meta['routing']['receiver_sha256'] != binding['receiver_sha256'] or
                meta['routing']['order_sha256'] != binding['order_sha256'] or
                meta['reference_identity'] != binding['reference_identity']):
            raise ValueError('Published climate differs from bound source/config')
        return json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if checkpoint.exists() or (root/'manifest.json').exists():
        raise FileExistsError('Existing stage: recover complete product or rerun interrupted year in new directory')
    root.mkdir(parents=True, exist_ok=True)
    _write_json(checkpoint, binding)
    return climate.prepare_climate(source, root, cfg, references)


def probe_source(source, window_zx):
    """Cost/field probe only; cut crossing receiver edges to explicit terminals.

    This independent cropped solve is NOT a production climate window and must
    never be tiled into the real parent. Its different source identity says so.
    """
    nz, nx = source['elevation_m'].shape
    if (len(window_zx) != 4 or any(type(n) is not int for n in window_zx)):
        raise ValueError('Integer probe window required')
    z0, x0, z1, x1 = window_zx
    if not (0 <= z0 < z1 <= nz and 0 <= x0 < x1 <= nx):
        raise ValueError('Probe window outside source')
    if (z1-z0)*(x1-x0) > 4096:
        raise ValueError('Probe is bounded to 4096 native cells')
    sl = np.s_[z0:z1, x0:x1]
    rec = np.asarray(source['receiver']).reshape(nz, nx)[sl].astype(np.int64)
    rz, rx = np.divmod(np.maximum(rec, 0), nx)
    inside = (rec >= 0) & (rz >= z0) & (rz < z1) & (rx >= x0) & (rx < x1)
    crossing = (rec >= 0) & ~inside
    rec = np.where(inside, (rz-z0)*(x1-x0)+(rx-x0), -1)
    result = dict(source)
    result.update(elevation_m=source['elevation_m'][sl].copy(), ocean_mask=source['ocean_mask'][sl].copy(),
        receiver=rec, order=topological_order(rec),
        first_xz_m=[source['first_xz_m'][0]+x0*source['spacing_m'], source['first_xz_m'][1]+z0*source['spacing_m']],
        source_identity=hashlib.sha256(_canonical(dict(parent=source['source_identity'],
            probe_window_zx=list(window_zx), crossing_edges='terminal-cut')).encode()).hexdigest())
    return result, dict(parent_source_identity=source['source_identity'], window_zx=list(window_zx),
        cut_receiver_edges=int(crossing.sum()), production_usable=False,
        semantics='independent bounded cost/field probe, not a production crop or river network')
