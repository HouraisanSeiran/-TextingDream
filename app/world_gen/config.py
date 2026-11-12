"""Player world configuration (dream-world-config-v1): defaults, validation, deterministic identity.

Only standard-library imports. Everything here is CPU-only and side-effect free.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

SCHEMA = 'dream-world-config-v1'
DEFAULT_WORLD_SEED = 20260903            # terrain-generation-rules.md section 4
WORLD_TYPES = ('multi-continent', 'pangaea', 'archipelago', 'two-continents', 'inland-sea')
WORLD_TYPE_LABELS = {'multi-continent': '多大陆(默认)', 'pangaea': '泛大陆', 'archipelago': '群岛',
                     'two-continents': '双大陆', 'inland-sea': '内海'}
PRESET_PLATES = {'multi-continent': 8, 'pangaea': 6, 'archipelago': 10, 'two-continents': 8, 'inland-sea': 8}
MOUNTAIN_LEVELS = {'low': 0.06, 'medium': 0.12, 'high': 0.20}
MAP_STYLES = ('simple', 'medieval', 'eastern')
SITE_TYPES = ('town', 'special_terrain', 'story')
WORLD_SPACINGS_M = (960, 1920)
OCEAN_RANGE = (0.5, 0.8)
MAX_LOCAL_SITES = 64


class ConfigError(ValueError):
    """Raised for any invalid world configuration; the message names the offending field."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=False)


def sha256_json(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def derive_subseed(world_seed, purpose):
    """Stable per-purpose seed: SHA256(f'{world_seed}:dream-world-gen:{purpose}')[:8] little endian."""
    digest = hashlib.sha256(f'{world_seed}:dream-world-gen:{purpose}'.encode()).digest()
    return int.from_bytes(digest[:8], 'little')


def _need(cond, field, message):
    if not cond:
        raise ConfigError(f'{field}: {message}')


def _num(value, field, lo=None, hi=None):
    _need(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), field, 'finite number required')
    _need(lo is None or value >= lo, field, f'must be >= {lo}')
    _need(hi is None or value <= hi, field, f'must be <= {hi}')
    return value


def skeleton_cell_km(width_km, height_km):
    """Skeleton cell size: 10 km ≤2000, 20 km ≤6000, 40 km above (must be a multiple of 2 km).

    10000 km → 250×250 cells (same count as measured 5000 km @ 20 km). Play-start areas can
    later use a finer local skeleton without regenerating the whole world.
    """
    longest = max(width_km, height_km)
    return 10 if longest <= 2000 else 20 if longest <= 6000 else 40


def normalize_geography_features(features, world, cell_size_km, *, source='new'):
    """Validate author intent without running or importing any terrain algorithms."""
    field = 'geography_features'
    _need(isinstance(features, list) and len(features) <= 32, field, 'list of at most 32 features required')
    _need(not features or source == 'new', field, 'requires a new skeleton')
    seen, out = set(), []
    allowed = {'id', 'center_x_m', 'center_z_m', 'radius_m', 'strength', 'aspect', 'bearing_deg'}
    ox, oz = [v * 1000 for v in world['origin_km']]
    width, height = world['width_km'] * 1000, world['height_km'] * 1000
    for i, feature in enumerate(features):
        f = f'{field}[{i}]'
        _need(isinstance(feature, dict), f, 'object required')
        _need(not set(feature) - allowed, f, 'unknown feature keys')
        sid = feature.get('id')
        _need(isinstance(sid, str) and sid.strip() and len(sid) <= 64, f + '.id', 'non-empty id up to 64 characters')
        sid = sid.strip()
        _need(sid not in seen, f + '.id', 'unique id required')
        seen.add(sid)
        x = _num(feature.get('center_x_m'), f + '.center_x_m', ox)
        z = _num(feature.get('center_z_m'), f + '.center_z_m', oz)
        _need(x < ox + width and z < oz + height, f, 'centre must be inside the finite world')
        radius = _num(feature.get('radius_m'), f + '.radius_m', cell_size_km * 1000, max(width, height))
        strength = _num(feature.get('strength'), f + '.strength', -4, 4)
        aspect = _num(feature.get('aspect', 1), f + '.aspect', 1, 10)
        bearing = _num(feature.get('bearing_deg', 0), f + '.bearing_deg', 0, 360)
        out.append(dict(id=sid, center_x_m=float(x), center_z_m=float(z), radius_m=float(radius),
                        strength=float(strength), aspect=float(aspect), bearing_deg=float(bearing % 360)))
    return sorted(out, key=lambda row: row['id'])


def normalize(raw):
    """Validate a raw dict and return a fully defaulted copy. Unknown top-level keys are rejected."""
    _need(isinstance(raw, dict), 'config', 'JSON object required')
    allowed = {'schema', 'world_name', 'world_seed', 'world', 'world_layer', 'skeleton', 'local_sites', 'map_style', 'notes', 'geography_features'}
    unknown = sorted(set(raw) - allowed)
    _need(not unknown, 'config', f'unknown keys {unknown}')
    _need(raw.get('schema', SCHEMA) == SCHEMA, 'schema', f'must be {SCHEMA!r}')
    cfg = {'schema': SCHEMA}
    name = raw.get('world_name')
    _need(isinstance(name, str) and name.strip() and len(name) <= 64 and not any(c in name for c in '\\/:*?"<>|'),
          'world_name', 'non-empty name up to 64 characters without path characters')
    cfg['world_name'] = name.strip()
    seed = raw.get('world_seed', DEFAULT_WORLD_SEED)
    _need(type(seed) is int and 0 <= seed < 2 ** 63, 'world_seed', 'non-negative integer')
    cfg['world_seed'] = seed

    w = copy.deepcopy(raw.get('world', {}))
    _need(isinstance(w, dict), 'world', 'object required')
    if 'size_km' in w:
        side = _num(w.pop('size_km'), 'world.size_km', 100, 20000)
        w.setdefault('width_km', side)
        w.setdefault('height_km', side)
    width = _num(w.get('width_km', 1600), 'world.width_km', 100, 20000)
    height = _num(w.get('height_km', width), 'world.height_km', 100, 20000)
    wtype = w.get('type', 'multi-continent')
    _need(wtype in WORLD_TYPES, 'world.type', f'one of {WORLD_TYPES}')
    ocean = _num(w.get('ocean_fraction', 0.6), 'world.ocean_fraction', *OCEAN_RANGE)
    mountain = w.get('mountain_cover', 'medium')
    if isinstance(mountain, str):
        _need(mountain in MOUNTAIN_LEVELS, 'world.mountain_cover', f'one of {tuple(MOUNTAIN_LEVELS)} or a fraction 0.02-0.4')
        mountain_target = MOUNTAIN_LEVELS[mountain]
    else:
        mountain_target = _num(mountain, 'world.mountain_cover', 0.02, 0.4)
    centre = w.get('origin_km')
    if centre is None:
        origin = [-width / 2, -height / 2]
    else:
        _need(isinstance(centre, list) and len(centre) == 2, 'world.origin_km', '[x, z] required')
        origin = [_num(centre[0], 'world.origin_km[0]'), _num(centre[1], 'world.origin_km[1]')]
    cfg['world'] = dict(width_km=width, height_km=height, origin_km=origin, type=wtype, ocean_fraction=ocean,
                        mountain_cover=mountain, mountain_target_land_fraction=mountain_target)

    layer = copy.deepcopy(raw.get('world_layer', {}))
    spacing = layer.get('spacing_m', 960)
    _need(spacing in WORLD_SPACINGS_M, 'world_layer.spacing_m', f'one of {WORLD_SPACINGS_M}')
    buffer_km = _num(layer.get('coast_buffer_km', 80), 'world_layer.coast_buffer_km', 0, 400)
    cfg['world_layer'] = dict(spacing_m=spacing, coast_buffer_km=buffer_km)

    sk = copy.deepcopy(raw.get('skeleton', {'source': 'new'}))
    _need(isinstance(sk, dict), 'skeleton', 'object required')
    source = sk.get('source', 'new')
    _need(source in ('existing', 'new'), 'skeleton.source', "'existing' or 'new'")
    if source == 'existing':
        _need(isinstance(sk.get('path'), str) and sk['path'], 'skeleton.path', 'product path required')
        ident = sk.get('identity')
        _need(isinstance(ident, str) and len(ident) == 64 and all(c in '0123456789abcdef' for c in ident.lower()),
              'skeleton.identity', '64 hex characters required')
        cfg['skeleton'] = dict(source='existing', path=sk['path'], identity=ident.lower())
    else:
        plates = sk.get('plates', PRESET_PLATES[wtype])
        _need(type(plates) is int and 2 <= plates <= 64, 'skeleton.plates', 'integer 2-64')
        cell = _num(sk.get('cell_size_km', skeleton_cell_km(width, height)), 'skeleton.cell_size_km', 2, 100)
        steps = sk.get('steps', 40)
        _need(type(steps) is int and 1 <= steps <= 400, 'skeleton.steps', 'integer 1-400')
        _need(width % cell == 0 and height % cell == 0, 'skeleton.cell_size_km', 'world width/height must be whole multiples')
        cfg['skeleton'] = dict(source='new', plates=plates, cell_size_km=cell, steps=steps,
                               microcells_per_plate=int(sk.get('microcells_per_plate', 64)),
                               min_plate_cells=int(sk.get('min_plate_cells', 4)))

    features = normalize_geography_features(raw.get('geography_features', []), cfg['world'],
        cfg['skeleton'].get('cell_size_km', skeleton_cell_km(width, height)), source=source)
    if features:
        cfg['geography_features'] = features

    sites = raw.get('local_sites', [])
    _need(isinstance(sites, list) and len(sites) <= MAX_LOCAL_SITES, 'local_sites', f'list of at most {MAX_LOCAL_SITES}')
    seen, out = set(), []
    for i, s in enumerate(sites):
        f = f'local_sites[{i}]'
        _need(isinstance(s, dict), f, 'object required')
        sid = s.get('id')
        _need(isinstance(sid, str) and sid and sid not in seen, f + '.id', 'unique non-empty string')
        seen.add(sid)
        _need(s.get('type') in SITE_TYPES, f + '.type', f'one of {SITE_TYPES}')
        reason = s.get('reason')
        _need(isinstance(reason, str) and reason.strip(), f + '.reason', 'a reason is required for every 30 m site')
        cx, cz = _num(s.get('center_x_m'), f + '.center_x_m'), _num(s.get('center_z_m'), f + '.center_z_m')
        if 'radius_m' in s:
            size = 2 * _num(s['radius_m'], f + '.radius_m', 30)
        else:
            size = _num(s.get('size_m'), f + '.size_m', 30)
        out.append(dict(id=sid, type=s['type'], center_x_m=cx, center_z_m=cz, size_m=size, reason=reason.strip()))
    cfg['local_sites'] = out
    style = raw.get('map_style', 'simple')
    _need(style in MAP_STYLES, 'map_style', f'one of {MAP_STYLES}')
    cfg['map_style'] = style
    if 'notes' in raw:
        _need(isinstance(raw['notes'], str), 'notes', 'string')
        cfg['notes'] = raw['notes']
    cfg['identity'] = sha256_json({k: v for k, v in cfg.items() if k != 'identity'})
    return cfg


def load_config(path):
    from pathlib import Path
    try:
        raw = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ConfigError(f'config: cannot read {path}: {exc}') from exc
    return normalize(raw)
