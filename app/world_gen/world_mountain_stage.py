"""CPU mountain checkpoint, not a world-map product or a hydrology product.

Each belt is evaluated on the SAME complete finite source grid. This deliberately
trades CPU/memory for shared field percentiles, lowland reference and absence of
internal tile boundaries. Only extraction of finished arrays is tiled; arbitrary
independently generated/cropped worlds are NOT promised to match.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import time
from pathlib import Path

import numpy as np

from . import mountain_sculpt as ms
from . import ridge_network as rn

SCHEMA = 'dream-world-mountain-checkpoint-1'
ALGORITHM = 'world-mountain-group-immutable-belt-blend'
APPROVED_REFERENCE = '09a1faab2138d200492ab68a1bc871e4014ef3fbf856fe7ba594a208397502ba'
ARRAY_KEYS = ('before_m', 'bed_m', 'support', 'blend_weight', 'weight_sum',
              'changed_mask', 'ocean', 'closed', 'protected_mask', 'island_support')


def _images(xz, rect, period, reach):
    """Whole unwrapped polylines translated onto a finite map, never vertex modulo.

    Bounds include segment interiors, so even a segment whose two endpoints are
    outside the finite source can contribute. No false segment joins periodic images.
    """
    a = np.asarray(xz, np.float64)
    lo, hi = a.min(axis=0), a.max(axis=0)
    choices = []
    for d in range(2):
        k0 = math.ceil((rect[d] - reach - hi[d]) / period[d])
        k1 = math.floor((rect[d + 2] + reach - lo[d]) / period[d])
        choices.append(range(k0, k1 + 1))
    for kx, kz in itertools.product(*choices):
        shift = np.array([kx * period[0], kz * period[1]])
        yield a + shift, [int(kx), int(kz)]


def _reach(p, net, spacing):
    """Conservative max permission/envelope reach, used only for image culling."""
    wide = max(float(np.max(net['vertex_width_wide_m'])),
               float(np.max(net['vertex_width_steep_m'])))
    widths = max(float(p['main_width_scale']), float(p['branch_width_scale']),
                 float(p['spur_width_scale']))
    envelope = wide * widths * float(p['chain_width_gain']) * (1 + abs(float(p['width_var'])))
    support = wide * widths * max(float(p['support_width_scale']), float(p['branch_support_scale']))
    support += max(float(p['support_width_extra_km']), float(p['branch_support_extra_km'])) * 1000
    belt = float(np.max(net['belt_half_width_m'])) * float(p['belt_support_scale'])
    belt += float(p['belt_support_extra_km']) * 1000
    skirt = float(p['group_shoulder_half_km'][1]) * 1000 * float(p['group_skirt_scale'])
    return max(envelope, support, belt, skirt) + abs(float(p['warp_amp_km'])) * 1000 + 2 * spacing


def _aligned_network(net, period):
    """Put parent/child lines in one periodic chart before kernel tip tapering."""
    vertices = np.array(net['vertex_xz_m'], np.float64, copy=True)
    offsets = np.asarray(net['line_offsets'])
    for li in np.argsort(net['line_level'], kind='stable'):
        parent = int(net['line_parent'][li])
        if parent < 0:
            continue
        sl = slice(offsets[li], offsets[li+1])
        xz = vertices[sl]
        pv = vertices[offsets[parent]:offsets[parent+1]]
        centre = np.rint((pv.mean(axis=0)-xz.mean(axis=0))/period).astype(int)
        candidates = [centre+d for d in itertools.product((-1, 0, 1), repeat=2)]
        def gap(k):
            ends = xz[[0, -1]] + np.asarray(k)*period
            return float(np.min(np.sum((ends[:, None, :]-pv[None, :, :])**2, axis=2)))
        vertices[sl] += min(candidates, key=gap)*np.asarray(period)
    return dict(net, vertex_xz_m=vertices)


def finite_structure(net, belt, grid, *, world_seed, params):
    """Select complete saved lines, then retain all periodic images reaching the source.

    World selection retains even short primary segments: the prototype's 250 km
    in-window filter is inappropriate for minor complete belts. Geometry and group
    parameters otherwise use the approved kernel. Parent IDs remain source IDs.
    """
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    period = (nx*S, nz*S)
    net = _aligned_network(net, period)
    V = np.asarray(net['vertex_xz_m'], np.float64)
    pad = max(S, 1.0)
    rect = [float(V[:, 0].min() - pad), float(V[:, 1].min() - pad),
            float(V[:, 0].max() + pad), float(V[:, 1].max() + pad)]
    sel = dict(params, min_main_length_km=0.0, min_direction_coherence=0.0)
    st = ms.select_structure(net, rect, belt=belt, world_seed=world_seed, params=sel)
    reach = _reach(params, net, S)
    out = dict(main=[], branches=[], spurs=[], passes=[], meta=copy.deepcopy(st['meta']))
    for key in ('main', 'branches', 'spurs'):
        for e in st[key]:
            xz = np.asarray(e['xz_m'], np.float64)
            for pts, image in _images(xz, grid['rect_m'], period, reach):
                ent = copy.deepcopy(e)
                ent.update(xz_m=pts.tolist(), periodic_image=image, source_line=int(e['line']))
                out[key].append(ent)
    bg = st['meta']['belt_geometry']
    parts = []
    for pts, image in _images(bg['xz_m'], grid['rect_m'], period, reach):
        part = copy.deepcopy(bg)
        part.update(xz_m=pts.tolist(), periodic_image=image)
        parts.append(part)
    out['meta']['belt_geometry'] = dict(belt=int(belt), parts=parts)
    for q in st['passes']:
        for pts, image in _images([q['xz_m']], grid['rect_m'], period, reach):
            ent = dict(q, xz_m=pts[0].tolist(), periodic_image=image)
            out['passes'].append(ent)
    out['meta'].update(period_m=list(period), image_reach_m=reach,
                       selection='complete source main segments; no local length/coherence filter',
                       calibration_domain='entire finite source grid, shared across all belts',
                       selection_overrides=dict(min_main_length_km=0.0, min_direction_coherence=0.0))
    return out


def _validate_binding(source, skeleton, grid, world_seed):
    if not source.get('product_identity') or not skeleton.get('identity'):
        raise ValueError('source and skeleton identities are required')
    if source.get('source_identity') != skeleton['identity']:
        raise ValueError('source/skeleton identity mismatch')
    seed = skeleton.get('world_seed', (skeleton.get('config') or {}).get('world_seed'))
    if int(source['world_seed']) != world_seed or seed != world_seed:
        raise ValueError('source/skeleton world_seed mismatch')
    if (list(source['shape_zx']) != list(grid['shape'])
            or float(source['spacing_m']) != float(grid['spacing_m'])
            or list(source['first_sample_xz_m']) != list(grid['first_xz_m'])
            or tuple(grid['index']) != (0, 0)):
        raise ValueError('world stage requires the complete bound source grid')
    cfg = skeleton.get('config') or {}
    if cfg:
        nz, nx = cfg['shape']
        S = float(cfg['cell_size_m'])
        extent = [cfg['origin_x_m'], cfg['origin_z_m'], cfg['origin_x_m'] + nx*S, cfg['origin_z_m'] + nz*S]
        if not np.allclose(extent, grid['rect_m'], rtol=0, atol=1e-6):
            raise ValueError('skeleton periodic extent differs from finite source')


def checkpoint_identity(result):
    h = hashlib.sha256()
    for key in ARRAY_KEYS:
        a = np.ascontiguousarray(result[key])
        h.update(key.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    # Runtime measurements are deliberately not identity-bearing.
    h.update(ms.canonical(result['binding']).encode())
    return h.hexdigest()


def apply_world_mountains(before_m, status, grid, net, *, source, skeleton,
                          world_seed=20260903, params=None, belts=None,
                          reference_identity=APPROVED_REFERENCE, island_support=None, erosion=True, log=None):
    """Independent immutable-baseline proposals, deterministic single composition.

    w_i is the kernel's domain*coast*finite-border weight. Its already blended
    delta is accumulated; final delta = sum(delta_i)/max(1,sum(w_i)). Thus a lone
    belt exactly keeps its kernel result; overlaps are convex, never double-eroded.
    """
    t0 = time.perf_counter()
    before = np.array(before_m, np.float64, copy=True)
    status = np.asarray(status)
    if before.ndim != 2 or before.shape != status.shape or tuple(before.shape) != tuple(grid['shape']):
        raise ValueError('bed/status/grid shape mismatch')
    if not np.isfinite(before).all() or float(grid['spacing_m']) <= 0:
        raise ValueError('finite bed and positive spacing required')
    _validate_binding(source, skeleton, grid, int(world_seed))
    p = ms._params(dict(params or {}, structure_policy='mountain-group'))
    ids = sorted(set(int(b) for b in (belts if belts is not None else range(len(net['belt_offsets']) - 1))))
    if any(b < 0 or b + 1 >= len(net['belt_offsets']) for b in ids):
        raise ValueError('invalid belt ID')
    ocean = status == 3
    closed = status == 4
    island_support = (np.zeros(before.shape, bool) if island_support is None
                      else np.asarray(island_support, bool))
    if island_support.shape != before.shape:
        raise ValueError('island support shape mismatch')
    fixed = ocean | closed | (before <= 0) | island_support
    protected = fixed | (ms._coast_guard(before, fixed, p['coast_guard_cells']) == 0)
    win = dict(before_m=before, ocean=ocean, closed=closed, fixed=fixed,
               lake=np.zeros(before.shape, bool), status=status, source=source)
    delta = np.zeros_like(before)
    weights = np.zeros_like(before)
    support = np.zeros(before.shape, np.float32)
    reports = []
    for belt in ids:
        start = time.perf_counter()
        st = finite_structure(net, belt, grid, world_seed=world_seed, params=p)
        # All proposals read the immutable original; no previously eroded belt is input.
        r = ms.apply_window(win, st, grid, world_seed=world_seed, params=p, erosion=erosion)
        delta += r['after_m'] - before
        weights += r['blend_weight']
        np.maximum(support, r['support'], out=support)
        report = dict(belt=belt, params=p, selection_overrides=st['meta']['selection_overrides'],
                      seconds=time.perf_counter()-start,
                      main_source_lines=st['meta']['main_lines'],
                      main_images=len(st['main']), branch_images=len(st['branches']), spur_images=len(st['spurs']),
                      structure_meta=st['meta'], group=r['meta']['group_report'],
                      support_cells=r['meta']['support_cells'], changed_cells=r['meta']['changed_cells'],
                      volume_change_m3=r['meta']['volume_change_m3'], erosion=r['meta']['erosion'],
                      peak_soft_cap_m=r['meta']['peak_soft_cap_m'],
                      basins=r['meta']['basins'], proposal_identity=r['identity'])
        reports.append(report)
        if log:
            log(dict(stage='world_mountain_belt', belt=belt, seconds=report['seconds'],
                     changed_cells=report['changed_cells']))
        del r
    bed = before + delta / np.maximum(1.0, weights)
    bed[protected] = before[protected]
    binding = dict(schema=SCHEMA, algorithm=ALGORITHM, source=source,
                   skeleton_identity=skeleton['identity'], ridge_identity=rn.network_identity(net),
                   reference_identity=reference_identity, grid=grid, world_seed=int(world_seed),
                   params=p, belts=ids, erosion=bool(erosion),
                   reused={f: ms._file_sha(f) for f in ms.REUSED},
                   kernel_sha256=ms._file_sha('app/world_gen/mountain_sculpt.py'),
                   stage_sha256=ms._file_sha('app/world_gen/world_mountain_stage.py'))
    result = dict(before_m=before, bed_m=bed, support=support,
                  blend_weight=np.minimum(weights, 1.0), weight_sum=weights,
                  changed_mask=bed != before, ocean=ocean, closed=closed, protected_mask=protected,
                  island_support=island_support,
                  binding=binding)
    result['identity'] = checkpoint_identity(result)
    result['metadata'] = dict(schema=SCHEMA, algorithm=ALGORITHM, identity=result['identity'], binding=binding,
        stage='mountains-only-checkpoint', product_complete=False,
        hydrology=dict(computed=False, rivers_included=False, lake_surfaces_included=False,
                       old_lakes_protected=False, next='TG glacier then new irregular-graph hydrology'),
        composition='sum(kernel_blended_delta_i) / max(1,sum(kernel_weight_i)); sorted source belt IDs',
        support_policy='union of saved wide belts and corridor support; immutable ocean/closed/nonpositive bed and frozen island support; coastal guard',
        calibration='all belts evaluated on identical full finite source grid; per-belt complete-line cap/body/crest calibration',
        boundary='only the finite source border tapers; no internal compute windows',
        limitations=['CPU/memory scale with full grid times belt count',
                     'no arbitrary cropped-world or infinite-window equivalence claim',
                     'artistic generation, not mass-conserving geology; coarse erosion is not final hydrology'],
        belts=reports, stats=dict(seconds=time.perf_counter()-t0, changed_cells=int((bed != before).sum()),
                    overlap_cells=int((weights > 1).sum()), protected_cells=int(protected.sum()),
                    max_abs_change_m=float(np.max(np.abs(bed-before))),
                    volume_change_m3=float(np.sum(bed-before)*float(grid['spacing_m'])**2)))
    return result


def extract_checkpoint(result, ix0, iz0, nx, nz):
    """Exact output slicing ONLY: never re-evaluates or re-calibrates a belt."""
    shape = result['bed_m'].shape
    if min(ix0, iz0) < 0 or min(nx, nz) <= 0 or ix0+nx > shape[1] or iz0+nz > shape[0]:
        raise ValueError('crop outside checkpoint')
    sl = np.s_[iz0:iz0+nz, ix0:ix0+nx]
    return {k: np.asarray(result[k])[sl].copy() for k in ARRAY_KEYS}


def write_checkpoint(out_dir, result):
    """Write only a new directory, never replace a frozen/published source."""
    if checkpoint_identity(result) != result['identity']:
        raise ValueError('checkpoint identity mismatch')
    out = Path(out_dir)
    if out.exists():
        raise ValueError('checkpoint output directory already exists')
    out.mkdir(parents=True)
    g = result['binding']['grid']
    np.savez_compressed(out / 'mountains.npz', **{k: result[k] for k in ARRAY_KEYS},
                        first_xz_m=np.asarray(g['first_xz_m'], np.float64),
                        spacing_m=np.asarray([g['spacing_m']], np.float64),
                        shape_zx=np.asarray(g['shape'], np.int64))
    (out / 'mountains.json').write_text(json.dumps(result['metadata'], ensure_ascii=False,
                                                   indent=1, allow_nan=False), encoding='utf-8')
    return dict(directory=str(out), arrays='mountains.npz', metadata='mountains.json', identity=result['identity'])


def load_island_support(product, manifest, info):
    """Read feature protection, NOT the frozen source's total exposed-land fraction.

    TG ocean_islands._query_direct defines land=(source base+island relief)>=0,
    including continents. protected=(feature protection_weight>0) is feature-only.
    Raster fractions sample those predicates independently. Published feature
    support cell rectangles conservatively cover unsampled subcell/centre support;
    these are preservation masks, never an assertion that the entire cell is land.
    """
    support = np.zeros(info.shape_zx, bool)
    layers = []
    # Keep path containment, byte hashes and grid validation for all consumed extras.
    for key in ('protected_fraction', 'frozen_island_lagoon_fraction', 'registered_lagoon'):
        spec = manifest.get('layers', {}).get(key)
        if spec is not None:
            target = (Path(product) / spec['file']).resolve()
            target.relative_to(Path(product).resolve())
            if ms.fr.file_sha(target) != spec['sha256']:
                raise ValueError('island support layer hash mismatch: ' + key)
            layer = np.load(target, mmap_mode='r', allow_pickle=False)
            if layer.shape != tuple(info.shape_zx) or not np.isfinite(layer).all():
                raise ValueError('invalid island support layer: ' + key)
            support |= np.asarray(layer) > 0
            layers.append(key)
    fraction_cells = int(support.sum())
    sampling = (manifest.get('ocean_islands') or {}).get('area_sampling') or {}
    features = sampling.get('feature_support_cells') or []
    if features:
        if (list(sampling.get('shape_zx') or []) != list(info.shape_zx)
                or float(sampling.get('spacing_m', -1)) != float(info.spacing_m)):
            raise ValueError('feature support metadata grid mismatch')
        nz, nx = info.shape_zx
        S = float(info.spacing_m)
        fx, fz = info.first_sample_xz_m
        bounds = [fx-S/2, fz-S/2, fx+(nx-.5)*S, fz+(nz-.5)*S]
        if not np.allclose(sampling.get('bounds_m') or [], bounds, rtol=0, atol=1e-6):
            raise ValueError('feature support metadata bounds mismatch')
        for feature in features:
            cells = feature.get('support_cells_zx')
            if cells is None:
                continue
            if (len(cells) != 4 or any(type(v) is not int for v in cells)
                    or not 0 <= cells[0] < cells[2] <= nz
                    or not 0 <= cells[1] < cells[3] <= nx):
                raise ValueError('invalid feature support cell rectangle')
            z0, x0, z1, x1 = cells
            support[z0:z1, x0:x1] = True
    policy = dict(layers=layers, fraction_or_registered_cells=fraction_cells,
                  feature_support_rectangles=len(features), protected_cells=int(support.sum()),
                  ignored_layers=['frozen_island_land_fraction'],
                  reason='land fraction includes continental base; not an island support predicate',
                  coverage='positive feature protection/lagoon plus published conservative feature cell rectangles')
    return support, policy


def run_stage(product, skeleton_path, out_dir, *, expected_identity, reference,
              expected_reference=APPROVED_REFERENCE, erosion=True, log=None):
    """Author-only file entry; canonical source and ridge readers perform validation."""
    out = Path(out_dir)
    if out.exists():
        raise ValueError('checkpoint output directory already exists')
    doc = json.loads((Path(reference) / 'structure.json').read_text(encoding='utf-8'))
    if doc.get('identity') != expected_reference or doc.get('schema') != ms.SCHEMA_G:
        raise ValueError('mountain reference identity/schema mismatch')
    if doc['meta'].get('structure_policy') != 'mountain-group':
        raise ValueError('reference must use mountain-group')
    manifest, arrays, info = ms.load_product(product, expected_identity)
    source = ms.source_binding(manifest, info)
    if doc['meta']['source']['product_identity'] != source['product_identity']:
        raise ValueError('reference/source identity mismatch')
    island_support, island_policy = load_island_support(product, manifest, info)
    net, sk = rn.load_network(skeleton_path)
    nz, nx = info.shape_zx
    grid = ms.grid_from_index(0, 0, nx, nz, info.first_sample_xz_m, info.spacing_m)
    r = apply_world_mountains(arrays['elevation_m'], arrays['status'], grid, net,
        source=source, skeleton=sk, world_seed=info.world_seed, params=doc['meta']['params'],
        reference_identity=expected_reference, island_support=island_support, erosion=erosion, log=log)
    r['metadata']['island_support_layers'] = island_policy['layers']
    r['metadata']['island_support_policy'] = island_policy
    r['metadata']['inputs'] = dict(product=str(Path(product).resolve()), skeleton=str(Path(skeleton_path).resolve()),
                                   reference=str(Path(reference).resolve()))
    r['metadata']['reference_note'] = 'approved local identity/parameters bound; not a claim of identical full-world morphology'
    return write_checkpoint(out, r)
