"""Vector ridge network for the world skeleton v3 (``dream-world-skeleton-3``, CPU only).

The mountain structure is fixed in the skeleton layer (docs/terrain-generation-rules.md section 6, last rule):

1. Main ridges follow convergent plate boundaries (``mountains.boundary_convergence``). Each connected boundary cloud is
   reduced to its graph diameter path (plus residual arms); the staircase cell path only gives the trend. The ridge line
   itself is a fractal polyline: irregularly spaced control points (40-110 km, scaled with the world size) with
   perpendicular jitter, then midpoint displacement down to the vertex spacing. Width and crest height vary along strike
   (1-D value noise), runs are broken by random gaps and by straits, a few points per run are lowered into passes.
2. Branches (level 2) leave the main ridge at 38-72 degrees, mostly on the landward side, as correlated random walks with
   midpoint displacement; level-3 spurs leave the branches the same way. Length, width and height shrink per level.
3. ``rasterize`` turns the network into a relief shape: max-union of per-segment tent profiles ``(1 - d/w)**1.5``
   (asymmetric: wide landward flank, steep seaward flank; d measured on domain-warped coordinates so the flanks are
   ragged), multiplied by a ridged multifractal (Musgrave) crest field. No Gaussian cross-section, no Gaussian blur.

All randomness is ``derive_subseed(world_seed, 'ridge-net/<purpose>')``; per-line generators are
``default_rng([subseed, chain_index])``. Noise is coordinate-addressed (fast_relief.noise_xz).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse import csgraph

from .config import derive_subseed

ALGORITHM = 'dream-ridge-network-1'
SEED_PURPOSES = ('ridge-net/main-shape', 'ridge-net/along-strike', 'ridge-net/breaks', 'ridge-net/passes',
                 'ridge-net/branches', 'ridge-net/warp', 'ridge-net/ridged', 'ridge-net/lowland')
ARRAY_NAMES = ('vertex_xz_m', 'vertex_width_wide_m', 'vertex_width_steep_m', 'vertex_amp', 'vertex_side',
               'line_offsets', 'line_level', 'line_parent', 'line_chain', 'pass_xz_m', 'pass_depth', 'pass_line')
# v4 (dream-ridge-network-2, orogen belts): per-line belt index + belt centre lines with half widths, floor and plateau weight
ARRAY_NAMES_V4 = ('line_belt', 'belt_offsets', 'belt_class', 'belt_chain', 'belt_xz_m', 'belt_half_width_m', 'belt_side',
                  'belt_floor_m', 'belt_plateau', 'gap_xz_m', 'gap_tangent', 'gap_half_m', 'gap_belt_half_m', 'gap_depth', 'gap_belt')

DEFAULTS = dict(
    ref_size_km=1600.0,
    main_half_width_wide_km=40.0, main_half_width_steep_km=17.0, landward_offset_km=8.0,
    control_spacing_km=(40.0, 110.0), control_jitter=0.20, mpd_rough=0.17, vertex_spacing_km=2.0,
    min_main_cells=6, residual_cells=5, max_arms=3,
    along_wavelengths_km=(150.0, 55.0), width_var=0.6, amp_var=0.5,
    gap_mean_km=420.0, gap_len_km=(14.0, 36.0), min_run_km=24.0, end_taper_km=30.0,
    pass_spacing_km=260.0, pass_depth=(0.5, 0.8), pass_half_km=(7.0, 15.0),
    branch_spacing_km=(26.0, 60.0), branch_angle_deg=(38.0, 72.0), branch_len_km=(50.0, 150.0), branch_landward=0.72,
    branch_width=(0.42, 0.62), branch_amp=(0.55, 0.8), branch_step_km=3.0, branch_turn_deg=10.0, branch_rough=0.12,
    sub_spacing_km=(12.0, 28.0), sub_len_frac=(0.28, 0.55),
    tip_width=0.3, tip_amp=0.12,
    profile_exp=1.5, warp_amp_km=7.0, warp_wavelengths_km=(46.0, 17.0),
    ridged_wavelengths_km=(56.0, 28.0, 14.0, 7.0), ridged_gain=2.0, ridged_offset=1.0, ridged_h=0.85,
    crest_floor=0.35, crest_gain=0.9,
)


def seeds_for(world_seed):
    return {k: derive_subseed(world_seed, k) for k in SEED_PURPOSES}


def _fr():
    from . import fast_relief as fr
    return fr


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _pdist(d, n):
    return (d + n / 2) % n - n / 2


# ------------------------------------------------------------------ main ridge traces from the boundary cloud
def _graph(cells, shape):
    nz, nx = shape
    idx = -np.ones(shape, np.int64)
    idx[cells[:, 0], cells[:, 1]] = np.arange(len(cells))
    rows, cols, w = [], [], []
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dz == 0 and dx == 0:
                continue
            nb = idx[(cells[:, 0] + dz) % nz, (cells[:, 1] + dx) % nx]
            ok = nb >= 0
            rows.append(np.flatnonzero(ok)); cols.append(nb[ok]); w.append(np.full(int(ok.sum()), math.hypot(dz, dx)))
    n = len(cells)
    return sparse.csr_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))


def _diameter(sub):
    d0 = csgraph.dijkstra(sub, indices=0)
    a = int(np.argmax(np.where(np.isfinite(d0), d0, -1)))
    d1, pred = csgraph.dijkstra(sub, indices=a, return_predecessors=True)
    b = int(np.argmax(np.where(np.isfinite(d1), d1, -1)))
    path = [b]
    while path[-1] != a:
        path.append(int(pred[path[-1]]))
    return np.array(path[::-1])


def trace_paths(sel, p):
    """Ordered cell paths (k, 2) [z, x] through every boundary cloud (diameter path + up to max_arms residual arms)."""
    cells = np.argwhere(sel)
    if not len(cells):
        return []
    g = _graph(cells, sel.shape)
    out = []

    def handle(nodes, depth):
        sub = g[nodes][:, nodes]
        ncomp, lab = csgraph.connected_components(sub, directed=False)
        for c in range(ncomp):
            comp = nodes[lab == c]
            if len(comp) < int(p['min_main_cells']):
                continue
            cs = g[comp][:, comp]
            path = _diameter(cs)
            out.append(cells[comp[path]])
            if depth >= int(p['max_arms']):
                continue
            dist = csgraph.dijkstra(cs, indices=path, min_only=True, limit=float(p['residual_cells']) + 0.5)
            rest = comp[~np.isfinite(dist)]
            if len(rest) >= int(p['min_main_cells']):
                handle(rest, depth + 1)

    handle(np.arange(len(cells)), 0)
    return out


def _unwrap_cells(path, shape, cell, origin):
    nz, nx = shape
    z = np.concatenate([[path[0, 0]], path[0, 0] + np.cumsum(_pdist(np.diff(path[:, 0]), nz))])
    x = np.concatenate([[path[0, 1]], path[0, 1] + np.cumsum(_pdist(np.diff(path[:, 1]), nx))])
    return np.stack([origin[0] + (x + 0.5) * cell, origin[1] + (z + 0.5) * cell], 1)


def _arclength(pts):
    seg = np.hypot(*np.diff(pts, axis=0).T)
    return np.concatenate([[0.0], np.cumsum(seg)])


def _resample(pts, step):
    s = _arclength(pts)
    if s[-1] <= 0:
        return pts[:1]
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], 1)


def _normals(pts):
    t = np.gradient(pts, axis=0)
    t /= np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-9)[:, None]
    return t, np.stack([-t[:, 1], t[:, 0]], 1)     # tangent, left normal


def _mpd(pts, rng, rough, max_seg):
    """Midpoint displacement: every segment is halved with a perpendicular offset N(0, rough * length) until <= max_seg."""
    pts = np.asarray(pts, np.float64)
    for _ in range(24):
        d = np.diff(pts, axis=0)
        length = np.hypot(d[:, 0], d[:, 1])
        if length.max() <= max_seg:
            break
        nrm = np.stack([-d[:, 1], d[:, 0]], 1) / np.maximum(length, 1e-9)[:, None]
        mid = 0.5 * (pts[:-1] + pts[1:]) + nrm * (rng.standard_normal(len(length)) * rough * length)[:, None]
        out = np.empty((len(pts) + len(mid), 2))
        out[0::2] = pts
        out[1::2] = mid
        pts = out
    return pts


class _Field:
    """Nearest-cell lookup of a periodic skeleton field at metric coordinates."""

    def __init__(self, a, cell, origin):
        self.a, self.cell, self.origin = a, cell, origin

    def __call__(self, x, z):
        nz, nx = self.a.shape
        ix = np.floor((np.asarray(x) - self.origin[0]) / self.cell).astype(np.int64) % nx
        iz = np.floor((np.asarray(z) - self.origin[1]) / self.cell).astype(np.int64) % nz
        return self.a[iz, ix]


def _noise1(s, seed, wavelengths):
    fr = _fr()
    s = np.asarray(s, np.float64)
    return fr.fbm_xz(s, np.full_like(s, 7919.0), seed, wavelengths, (0.65, 0.35))


# ------------------------------------------------------------------ network construction
def build_network(plate_id, velocities, land, *, cell_m, origin_xz_m, world_seed, params=None):
    """Return (net, meta). net: dict of arrays (ARRAY_NAMES) in unwrapped metric coordinates (domain is periodic)."""
    from . import mountains as mt
    p = dict(DEFAULTS); p.update(params or {})
    seeds = seeds_for(world_seed)
    nz, nx = land.shape
    extent_km = max(nz, nx) * cell_m / 1000.0
    sc = math.sqrt(extent_km / float(p['ref_size_km']))
    km = 1000.0 * sc                       # scaled kilometre for widths / lengths / spacings
    vs = float(p['vertex_spacing_km']) * 1000.0
    conv = mt.boundary_convergence(plate_id, velocities)
    strength = conv['strength']
    local_land = ndimage.uniform_filter(land.astype(np.float64), size=7, mode='wrap')
    sel = (strength > 0) & (local_land > 0.05)
    land_at = _Field(land, cell_m, origin_xz_m)
    str_at = _Field(ndimage.maximum_filter(strength, size=5, mode='wrap'), cell_m, origin_xz_m)
    paths = trace_paths(sel, p)
    lines = []          # dict(xz, ww, ws, amp, side, level, parent, chain)
    passes = []
    rng_shape = seeds['ridge-net/main-shape']
    stats = dict(boundary_paths=len(paths), main_runs=0, gaps=0, strait_breaks=0, passes=0, branches=0, spurs=0,
                 dropped_short=0)
    W_wide, W_steep = float(p['main_half_width_wide_km']) * km, float(p['main_half_width_steep_km']) * km
    for chain, path in enumerate(paths):
        rng = np.random.default_rng([rng_shape, chain])
        pts = _unwrap_cells(path, (nz, nx), cell_m, origin_xz_m)
        pts = _resample(pts, cell_m)
        if len(pts) >= 5:                   # remove the cell staircase (vector smoothing of the trend line only)
            pts = np.stack([ndimage.uniform_filter1d(pts[:, k], 5, mode='nearest') for k in (0, 1)], 1)
        _, nrm = _normals(pts)
        probe = W_wide
        lp = sum(land_at(pts[:, 0] + nrm[:, 0] * probe * f, pts[:, 1] + nrm[:, 1] * probe * f).astype(float) for f in (.5, 1, 1.5))
        lm = sum(land_at(pts[:, 0] - nrm[:, 0] * probe * f, pts[:, 1] - nrm[:, 1] * probe * f).astype(float) for f in (.5, 1, 1.5))
        side = np.sign(ndimage.uniform_filter1d(lp - lm, min(len(pts), 15), mode='nearest'))
        side[side == 0] = 1.0
        pts = pts + nrm * (side * float(p['landward_offset_km']) * km)[:, None]
        # fractal polyline: irregular control points + perpendicular jitter + midpoint displacement
        s = _arclength(pts)
        lo, hi = (v * km for v in p['control_spacing_km'])
        cs = [0.0]
        while cs[-1] + lo < s[-1]:
            cs.append(cs[-1] + rng.uniform(lo, hi))
        if s[-1] - cs[-1] < 0.4 * lo and len(cs) > 1:
            cs[-1] = s[-1]
        else:
            cs.append(s[-1])
        cs = np.array(cs)
        ctrl = np.stack([np.interp(cs, s, pts[:, 0]), np.interp(cs, s, pts[:, 1])], 1)
        if len(ctrl) > 2:
            _, cn = _normals(ctrl)
            spacing = np.gradient(cs)
            ctrl[1:-1] += cn[1:-1] * (rng.standard_normal(len(ctrl) - 2) * float(p['control_jitter']) * spacing[1:-1])[:, None]
        poly = _mpd(ctrl, rng, float(p['mpd_rough']), vs)
        sv = _arclength(poly)
        side_v = np.sign(np.interp(sv / max(sv[-1], 1.0) * s[-1], s, side))
        side_v[side_v == 0] = 1.0
        n1 = _noise1(sv + chain * 1.7e7, seeds['ridge-net/along-strike'], [v * km for v in p['along_wavelengths_km']])
        n2 = _noise1(sv + chain * 1.7e7 + 5.3e6, seeds['ridge-net/along-strike'], [v * km for v in p['along_wavelengths_km']])
        wf = np.clip(1 + float(p['width_var']) * n1 * 1.8, 0.4, 1.75)
        st = str_at(poly[:, 0], poly[:, 1])
        amp = (0.6 + 0.4 * st) * np.clip(1 + float(p['amp_var']) * n2 * 1.8, 0.4, 1.5)
        ww, ws = W_wide * wf, W_steep * wf ** 0.7
        # breaks: random gaps + straits (vertices over the sea)
        rb = np.random.default_rng([seeds['ridge-net/breaks'], chain])
        keep = land_at(poly[:, 0], poly[:, 1]).astype(bool)
        stats['strait_breaks'] += int(np.sum(np.diff(keep.astype(int)) == -1))
        g0 = rb.uniform(0.3, 1.0) * float(p['gap_mean_km']) * km
        while g0 < sv[-1] - 40 * km:
            gl = rb.uniform(*p['gap_len_km']) * km
            keep &= ~((sv >= g0) & (sv < g0 + gl))
            stats['gaps'] += 1
            g0 += gl + rb.exponential(float(p['gap_mean_km']) * km)
        runs = _runs(keep)
        for r0, r1 in runs:
            seg = slice(r0, r1)
            if sv[r1 - 1] - sv[r0] < float(p['min_run_km']) * km:
                stats['dropped_short'] += 1
                continue
            line = dict(xz=poly[seg].copy(), ww=ww[seg].copy(), ws=ws[seg].copy(), amp=amp[seg].copy(), side=side_v[seg].copy(),
                        level=1, parent=-1, chain=chain)
            _taper(line, float(p['end_taper_km']) * km)
            lines.append(line)
            stats['main_runs'] += 1
    # passes on main runs
    for li, line in enumerate(list(lines)):
        rp = np.random.default_rng([seeds['ridge-net/passes'], li])
        sv = _arclength(line['xz'])
        total = sv[-1]
        count = int(total // (float(p['pass_spacing_km']) * km)) + int(total > 0.5 * float(p['pass_spacing_km']) * km and rp.random() < 0.6)
        for k in range(count):
            f = (k + rp.uniform(0.25, 0.75)) / max(count, 1)
            s0 = f * total
            hw = rp.uniform(*p['pass_half_km']) * km
            depth = rp.uniform(*p['pass_depth'])
            bump = 0.5 * (1 + np.cos(np.pi * np.clip(np.abs(sv - s0) / hw, 0, 1)))
            line['amp'] = line['amp'] * (1 - depth * bump)
            i = int(np.argmin(np.abs(sv - s0)))
            passes.append((float(line['xz'][i, 0]), float(line['xz'][i, 1]), float(depth), li, float(s0)))
            stats['passes'] += 1
    # branches (level 2) and spurs (level 3)
    mains = len(lines)
    for li in range(mains):
        new = _grow(lines[li], li, seeds['ridge-net/branches'], p, km, vs, land_at, passes, level=2,
                    spacing=p['branch_spacing_km'], length=lambda r, L: r.uniform(*p['branch_len_km']) * km)
        stats['branches'] += len(new)
        for b in new:
            bi = len(lines)
            lines.append(b)
            L2 = _arclength(b['xz'])[-1]
            subs = _grow(b, bi, seeds['ridge-net/branches'] ^ 0x5bd1e995, p, km, vs, land_at, [], level=3,
                         spacing=p['sub_spacing_km'], length=lambda r, L, L2=L2: r.uniform(*p['sub_len_frac']) * L2)
            stats['spurs'] += len(subs)
            lines.extend(subs)
    net = _pack(lines, passes)
    meta = dict(algorithm=ALGORITHM, params={k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()},
                size_scale=sc, subseeds={k: str(v) for k, v in seeds.items()}, statistics=stats,
                boundary_cells=conv['cells'], plate_pairs=conv['pairs'],
                lines=int(len(net['line_level'])), vertices=int(len(net['vertex_amp'])),
                lines_by_level={str(l): int((net['line_level'] == l).sum()) for l in (1, 2, 3)},
                length_km_by_level={str(l): float(_level_length(net, l) / 1000.0) for l in (1, 2, 3)},
                identity=network_identity(net))
    return net, meta


def _runs(mask):
    m = np.concatenate([[0], mask.astype(np.int8), [0]])
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def _taper(line, taper):
    sv = _arclength(line['xz'])
    de = np.minimum(sv, sv[-1] - sv)
    f = _smoothstep(de / max(taper, 1.0))
    line['amp'] = line['amp'] * (0.12 + 0.88 * f)
    line['ww'] = line['ww'] * (0.5 + 0.5 * f)
    line['ws'] = line['ws'] * (0.5 + 0.5 * f)


def _grow(parent, pi, seed, p, km, vs, land_at, passes, *, level, spacing, length):
    """Side ridges leaving `parent` at an angle; correlated random walk + midpoint displacement; stop at the coast."""
    rng = np.random.default_rng([seed, pi])
    xz = parent['xz']
    sv = _arclength(xz)
    tan, nrm = _normals(xz)
    out = []
    lo, hi = (v * km for v in spacing)
    s0 = rng.uniform(0.4, 1.0) * lo
    near_pass = [q[4] for q in passes if q[3] == pi]
    step = float(p['branch_step_km']) * km
    turn = math.radians(float(p['branch_turn_deg']))
    while s0 < sv[-1] - 0.3 * lo:
        i = int(np.argmin(np.abs(sv - s0)))
        if any(abs(s0 - q) < 20 * km for q in near_pass) or parent['amp'][i] < 0.2:
            s0 += rng.uniform(lo, hi)
            continue
        landward = rng.random() < float(p['branch_landward'])
        side = parent.get('bside', parent['side'])[i] * (1 if landward else -1)
        ang = math.radians(rng.uniform(*p['branch_angle_deg'])) * side
        fwd = 1.0 if rng.random() < 0.5 else -1.0
        hx, hz = tan[i] * fwd
        head = math.atan2(hz, hx) + ang * fwd
        L = length(rng, sv[-1])
        n = max(2, int(L / step))
        pts = [xz[i].copy()]
        for _ in range(n):
            head += rng.normal(0, turn)
            q = pts[-1] + step * np.array([math.cos(head), math.sin(head)])
            if not bool(land_at(q[0], q[1])):
                break
            pts.append(q)
        if len(pts) >= 3:
            poly = _mpd(np.array(pts), rng, float(p['branch_rough']), vs)
            t = _arclength(poly)
            t = t / max(t[-1], 1.0)
            wf = rng.uniform(*p['branch_width']) * parent['ww'][i]
            af = rng.uniform(*p['branch_amp']) * parent['amp'][i]
            wcurve = 1 - (1 - float(p['tip_width'])) * t ** 0.8
            acurve = 1 - (1 - float(p['tip_amp'])) * t ** 0.9
            ratio = rng.uniform(0.65, 0.95)
            out.append(dict(xz=poly, ww=wf * wcurve, ws=wf * ratio * wcurve, amp=af * acurve,
                            side=np.full(len(poly), 1.0 if rng.random() < 0.5 else -1.0),
                            level=level, parent=pi, chain=parent['chain']))
        s0 += rng.uniform(lo, hi)
    return out


def _pack(lines, passes):
    offs = np.cumsum([0] + [len(l['xz']) for l in lines]).astype(np.int64)
    cat = lambda k, dt: (np.concatenate([np.asarray(l[k], np.float64) for l in lines]).astype(dt) if lines
                         else np.zeros((0, 2) if k == 'xz' else 0, dt))
    return dict(
        vertex_xz_m=cat('xz', np.float64).reshape(-1, 2), vertex_width_wide_m=cat('ww', np.float32),
        vertex_width_steep_m=cat('ws', np.float32), vertex_amp=cat('amp', np.float32), vertex_side=cat('side', np.int8),
        line_offsets=offs, line_level=np.array([l['level'] for l in lines], np.int8),
        line_parent=np.array([l['parent'] for l in lines], np.int32), line_chain=np.array([l['chain'] for l in lines], np.int32),
        pass_xz_m=np.array([q[:2] for q in passes], np.float64).reshape(-1, 2),
        pass_depth=np.array([q[2] for q in passes], np.float32), pass_line=np.array([q[3] for q in passes], np.int32))


def _level_length(net, level):
    total = 0.0
    o = net['line_offsets']
    for li in np.flatnonzero(net['line_level'] == level):
        v = net['vertex_xz_m'][o[li]:o[li + 1]]
        total += float(np.hypot(*np.diff(v, axis=0).T).sum()) if len(v) > 1 else 0.0
    return total


def _names(net):
    """v3 array names, plus the v4 orogen arrays when present (v3 identities are unchanged)."""
    return ARRAY_NAMES + tuple(k for k in ARRAY_NAMES_V4 if k in net)


def network_identity(net):
    h = hashlib.sha256()
    for k in _names(net):
        a = np.ascontiguousarray(net[k])
        h.update(k.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


LAYOUT = ('ridges/<name> arrays; line i owns vertices line_offsets[i]:line_offsets[i+1]; vertex_xz_m are metric X east / Z south '
          'on the periodic skeleton plane (unwrapped along a line, wrap with the skeleton extent); widths are half widths in m '
          '(wide = landward flank side given by vertex_side relative to the line direction: +1 left, -1 right); vertex_amp is the '
          'relative crest height (passes and gaps already applied); line_level 1 main ridge, 2 branch, 3 spur; line_parent = parent '
          'line index (-1 for main); pass_* lists the lowered pass points (depth = fractional crest lowering)')


def npz_arrays(net):
    return {'ridges/' + k: np.ascontiguousarray(net[k]) for k in _names(net)}


def load_network(path):
    """Read ridges/* from a v3 skeleton npz. Returns (net, manifest dict). Arrays are hash-checked against the manifest."""
    import json
    with np.load(path, allow_pickle=False) as z:
        m = json.loads(z['manifest_json'].item())
        if 'ridges/line_offsets' not in z.files:
            raise ValueError('skeleton has no ridge network (not dream-world-skeleton-3)')
        net = {k: np.asarray(z['ridges/' + k]) for k in ARRAY_NAMES + ARRAY_NAMES_V4 if 'ridges/' + k in z.files}
    for k, a in net.items():
        spec = m['arrays'].get('ridges/' + k)
        if spec is None or hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() != spec['sha256']:
            raise ValueError('ridge array hash mismatch: ' + k)
    rid = (m.get('ridge_network') or {}).get('identity')
    if rid is not None and rid != network_identity(net):
        raise ValueError('ridge network identity mismatch')
    return net, m


# ------------------------------------------------------------------ raster
def ridged_multifractal(x, z, seed, wavelengths_m, h=0.85, gain=2.0, offset=1.0):
    """Musgrave ridged multifractal on coordinate-addressed value noise; roughly in [0, 1]."""
    fr = _fr()
    total, norm, weight = 0.0, 0.0, 1.0
    for k, wl in enumerate(wavelengths_m):
        n = fr.noise_xz(x, z, (seed + 0x9E3779B97F4A7C15 * (k + 1)) % (1 << 64), wl)
        sig = (offset - np.abs(n)) ** 2 * weight
        weight = np.clip(sig * gain, 0.0, 1.0)
        f = (wavelengths_m[0] / wl) ** (-h)
        total = total + sig * f
        norm += f
    return total / norm


def rasterize(net, shape, first_xz_m, spacing_m, *, world_seed, params=None, width_scale=1.0, return_parts=False):
    """Relief shape (float32, ~0..1.3) of the network on a cell-centre grid; the grid is treated as periodic.

    shape = envelope * (crest_floor + crest_gain * R), envelope = max over segments of amp * (1 - d / w) ** profile_exp.
    """
    fr = _fr()
    p = dict(DEFAULTS); p.update(params or {})
    seeds = seeds_for(world_seed)
    nz, nx = shape
    S = float(spacing_m)
    wamp = float(p['warp_amp_km']) * 1000.0
    wwl = [v * 1000.0 for v in p['warp_wavelengths_km']]
    wx = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: wamp * fr.fbm_xz(x, z, seeds['ridge-net/warp'], wwl, (0.65, 0.35)))
    wz = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: wamp * fr.fbm_xz(x + 51413.0, z - 23071.0, seeds['ridge-net/warp'], wwl, (0.65, 0.35)))
    env, level = _segment_envelope(net, shape, first_xz_m, S, wx, wz, wamp, float(p['profile_exp']), width_scale)
    rwl = [v * 1000.0 for v in p['ridged_wavelengths_km']]
    R = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: ridged_multifractal(x, z, seeds['ridge-net/ridged'], rwl,
                                                                               float(p['ridged_h']), float(p['ridged_gain']),
                                                                               float(p['ridged_offset'])))
    out = (env * (float(p['crest_floor']) + float(p['crest_gain']) * R)).astype(np.float32)
    if return_parts:
        return out, dict(envelope=env, ridged=R, level=level)
    return out


def _segment_envelope(net, shape, first_xz_m, S, wx, wz, wamp, pe, width_scale=1.0, profile=None):
    """max-union of per-segment asymmetric tent profiles amp * (1 - d/w)**pe on warped coordinates (grid treated as periodic).
    profile: optional callable g(x), x = clip(1 - d/w, 0, 1), replacing x**pe (v4 flat-topped belt platforms)."""
    nz, nx = shape
    env = np.zeros(shape, np.float32)
    level = np.zeros(shape, np.int8)
    V = net['vertex_xz_m']; WW = net['vertex_width_wide_m'].astype(np.float64) * width_scale
    WS = net['vertex_width_steep_m'].astype(np.float64) * width_scale
    AM = net['vertex_amp'].astype(np.float64); SD = net['vertex_side'].astype(np.float64)
    o = net['line_offsets']
    x0, z0 = float(first_xz_m[0]), float(first_xz_m[1])
    for li in range(len(o) - 1):
        lev = int(net['line_level'][li])
        for j in range(int(o[li]), int(o[li + 1]) - 1):
            ax, az = V[j]; bx, bz = V[j + 1]
            reach = max(WW[j], WW[j + 1], WS[j], WS[j + 1]) + 1.5 * wamp
            i0 = int(math.floor((min(ax, bx) - reach - x0) / S)); i1 = int(math.ceil((max(ax, bx) + reach - x0) / S))
            k0 = int(math.floor((min(az, bz) - reach - z0) / S)); k1 = int(math.ceil((max(az, bz) + reach - z0) / S))
            xi = np.arange(i0, min(i1, i0 + nx - 1) + 1); zi = np.arange(k0, min(k1, k0 + nz - 1) + 1)
            ix, iz = xi % nx, zi % nz
            sub = np.ix_(iz, ix)
            px = (x0 + xi * S)[None, :] + wx[sub]
            pz = (z0 + zi * S)[:, None] + wz[sub]
            dx, dz = bx - ax, bz - az
            l2 = max(dx * dx + dz * dz, 1e-9)
            t = np.clip(((px - ax) * dx + (pz - az) * dz) / l2, 0.0, 1.0)
            d = np.hypot(px - (ax + t * dx), pz - (az + t * dz))
            cross = dx * (pz - az) - dz * (px - ax)
            wide = cross * SD[j] >= 0
            w = np.where(wide, WW[j] + (WW[j + 1] - WW[j]) * t, WS[j] + (WS[j + 1] - WS[j]) * t)
            a = AM[j] + (AM[j + 1] - AM[j]) * t
            if profile is None:
                v = (a * np.clip(1.0 - d / w, 0.0, 1.0) ** pe).astype(np.float32)
            else:
                v = (a * profile(np.clip(1.0 - d / w, 0.0, 1.0))).astype(np.float32)
            cur = env[sub]
            up = v > cur
            if up.any():
                env[sub] = np.where(up, v, cur)
                lv = level[sub]
                level[sub] = np.where(up & (v > 0.02), lev, lv)
    return env, level


def block_mean(a, k):
    nz, nx = a.shape
    return a.reshape(nz // k, k, nx // k, k).mean(axis=(1, 3))


# ------------------------------------------------------------------ skeleton mountains (v3)
def lowland_base(land, cell_m, world_seed, *, start_m=120.0, rise_m=700.0, plateau_km=350.0, relief_m=90.0, cap_m=1150.0):
    """Land base below the mountain proxy: rises with distance from the coast, plus FFT-filtered plains relief."""
    from .skeleton import periodic_noise
    pad = 16
    if land.all():
        dist = np.full(land.shape, 1e9)
    else:
        dist = ndimage.distance_transform_edt(np.pad(land, pad, mode='wrap'))[pad:-pad, pad:-pad] * cell_m
    ramp = _smoothstep(dist / (plateau_km * 1000.0))
    noise = periodic_noise(land.shape, derive_subseed(world_seed, 'ridge-net/lowland'), exponent=2.4)
    base = start_m + rise_m * ramp + relief_m * noise * np.clip(ramp * 3, 0, 1)
    return np.where(land, np.clip(base, 1.0, cap_m), 0.0)


def build_skeleton_mountains(elev, plate_id, velocities, *, cell_m, origin_xz_m, world_seed, target_fraction, proxy_m=1500.0,
                             params=None, width_scales=(1.0, 1.3, 1.7, 2.2, 2.8), pref_amp_m=5200.0, cap_amp_m=7500.0,
                             fine_m=2000.0):
    """Land elevation from the ridge network. Ocean cells and the land/sea split are untouched (asserted).

    Returns (elevation, lowland_base, net, meta). The relief shape is evaluated at `fine_m` and block-averaged to the
    skeleton cell (box mean, not a Gaussian); the uplift amplitude is bisected to hit the coverage target.
    """
    e = np.asarray(elev, np.float64)
    land = e > 0
    nz, nx = land.shape
    k = int(round(cell_m / fine_m))
    if abs(k * fine_m - cell_m) > 1e-6:
        raise ValueError('cell size must be a multiple of fine_m')
    net, meta = build_network(plate_id, velocities, land, cell_m=cell_m, origin_xz_m=origin_xz_m, world_seed=world_seed,
                              params=params)
    base = lowland_base(land, cell_m, world_seed)
    first = (origin_xz_m[0] + fine_m / 2, origin_xz_m[1] + fine_m / 2)

    def fraction(shape, amp):
        return float(((base + amp * shape) > proxy_m)[land].mean())

    def solve(shape):
        if fraction(shape, cap_amp_m) < target_fraction:
            return cap_amp_m
        lo, hi = 0.0, cap_amp_m
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if fraction(shape, mid) < target_fraction else (lo, mid)
        return hi

    trials, chosen = [], None
    for ws in width_scales:
        fine = rasterize(net, (nz * k, nx * k), first, fine_m, world_seed=world_seed, params=params, width_scale=ws)
        shape = block_mean(fine.astype(np.float64), k)
        amp = solve(shape)
        frac = fraction(shape, amp)
        trial = dict(width_scale=float(ws), amp_m=float(amp), land_fraction=frac, reached=bool(abs(frac - target_fraction) <= 0.0015))
        trials.append(trial)
        if trial['reached'] and amp <= pref_amp_m:
            chosen = (trial, shape)
            break
        trial['_shape'] = shape
    if chosen is None:
        pick = min(trials, key=lambda t: (round(abs(t['land_fraction'] - target_fraction), 4), t['amp_m']))
        chosen = (pick, pick['_shape'])
    trial, shape = chosen
    for t in trials:
        t.pop('_shape', None)
    out = np.where(land, np.maximum(base + trial['amp_m'] * shape, 1.0), e)
    assert ((out > 0) == land).all(), 'ridge mountains changed the land/sea split'
    assert (out[~land] == e[~land]).all()
    meta.update(applied=True, amp_m=trial['amp_m'], width_scale=trial['width_scale'], width_trials=trials, fine_spacing_m=fine_m,
                land_fraction_after=float(((out > proxy_m)[land]).mean()), proxy_m=float(proxy_m),
                target_land_fraction=float(target_fraction),
                raster='max-union of segment tent profiles (1-d/w)^%g on domain-warped coordinates x ridged multifractal; '
                       'evaluated at %g m and box-averaged to the skeleton cell; no Gaussian profile, no Gaussian blur'
                       % (float((params or {}).get('profile_exp', DEFAULTS['profile_exp'])), fine_m),
                lowland='120 m + 700 m * smoothstep(coast distance / 350 km) + 90 m FFT plains relief, capped 1150 m')
    return out, base, net, meta


# ====================================================================== v4: orogen belts (dream-ridge-network-2)
# Skeleton v4 (dream-world-skeleton-4). User 2026-11-05: main orogenic belts 150-400 km wide with 2-4 roughly parallel ranges,
# intermontane basins / longitudinal valleys between them, a ring of foothills outside, plateaus where the crust is thick;
# secondary belts 40-120 km; the whole mountain area (incl. hills, basins, plateaus) 20-30 % of the land. Structure:
#   belt  = smooth centre line along a convergent boundary (landward offset) with a half width W(s), floor height and plateau
#           weight per vertex; raster: flat-topped platform floor * smoothstep(x / floor_edge), x = 1 - d / W (not a Gaussian);
#   range = fractal polyline (control points + midpoint displacement) offset from the belt centre by f_k * W(s) (+ along-strike
#           noise, so ranges converge and diverge); level-1 line of the v3 layout, rasterized with the v3 tent profile x ridged
#           multifractal; water gaps lower all ranges of a belt at the same place (rivers can leave the belt there);
#   branches / spurs (levels 2 / 3) grow from the ranges as in v3; foothills = ridged-noise hill relief on the outer belt ring.
OROGEN_ALGORITHM = 'dream-ridge-network-2'
OROGEN_SEED_PURPOSES = ('orogen/belt', 'orogen/ranges', 'orogen/along-strike', 'orogen/breaks', 'orogen/water-gaps',
                        'orogen/branches', 'orogen/warp', 'orogen/belt-warp', 'orogen/ridged', 'orogen/hills')
OROGEN_DEFAULTS = dict(
    ref_size_km=1600.0, vertex_spacing_km=2.0, belt_vertex_km=5.0, min_main_cells=6, residual_cells=5, max_arms=3,
    belt_smooth_cells=9, belt_landward_km=30.0, belt_control_km=(90.0, 170.0), belt_jitter=0.08, belt_rough=0.06,
    min_belt_km=90.0, major_min_km=420.0, major_half_km=(95.0, 175.0), minor_half_km=(25.0, 55.0),
    belt_width_wavelengths_km=(280.0, 120.0), belt_width_var=0.3, belt_end_taper_km=90.0,
    major_range_km=95.0, major_ranges=(2, 4), minor_ranges=(1, 2), minor_two_ranges_km=80.0,
    range_span=0.62, range_offset_jitter=0.06, range_offset_var=0.10, range_offset_wavelengths_km=(240.0, 95.0),
    range_half_frac=0.5, range_steep_ratio=(0.55, 0.8), range_control_km=(40.0, 110.0), control_jitter=0.15, mpd_rough=0.15,
    range_amp_main=(0.88, 1.0), range_amp_other=(0.5, 0.78), minor_amp=0.6,
    along_wavelengths_km=(150.0, 55.0), amp_var=0.45, width_var=0.3,
    gap_mean_km=600.0, gap_len_km=(14.0, 32.0), min_run_km=30.0, end_taper_km=40.0,
    water_gap_spacing_km=320.0, water_gap_depth=(0.8, 0.95), water_gap_half_km=(9.0, 16.0),
    water_gap_corridor=1.4, water_gap_corridor_min_km=14.0, water_gap_cross=1.3, water_gap_meander=1.6, water_gap_floor_share=0.55,
    branch_spacing_km=(38.0, 85.0), branch_angle_deg=(35.0, 70.0), branch_len_frac=(0.3, 0.6), branch_landward=0.5,
    branch_width=(0.4, 0.6), branch_amp=(0.5, 0.75), branch_step_km=3.0, branch_turn_deg=10.0, branch_rough=0.12,
    sub_spacing_km=(14.0, 30.0), sub_len_frac=(0.3, 0.55), tip_width=0.3, tip_amp=0.12,
    floor_major_m=(650.0, 950.0), floor_minor_m=(220.0, 380.0), plateau_m=2000.0, plateau_thick_km=(44.0, 62.0),
    floor_edge=0.32, hills_m=420.0, hills_band=0.34, hills_wavelengths_km=(34.0, 13.0), basin_relief=0.3,
    belt_warp_km=16.0, belt_warp_wavelengths_km=(95.0, 38.0),
    profile_exp=1.5, warp_amp_km=6.0, warp_wavelengths_km=(46.0, 17.0),
    ridged_wavelengths_km=(56.0, 28.0, 14.0, 7.0), ridged_gain=2.0, ridged_offset=1.0, ridged_h=0.85,
    crest_floor=0.35, crest_gain=0.9, amp_m=3600.0, plateau_amp_cut=0.3,
    target_cover=0.25, cover_band=(0.20, 0.30), width_scale_range=(0.62, 1.7), footprint_min=0.02,
)


def orogen_seeds(world_seed):
    return {k: derive_subseed(world_seed, k) for k in OROGEN_SEED_PURPOSES}


def _belt_warp(shape, first, S, p, seeds):
    fr = _fr()
    amp = float(p['belt_warp_km']) * 1000.0
    wl = [v * 1000.0 for v in p['belt_warp_wavelengths_km']]
    sd = seeds['orogen/belt-warp']
    wx = fr.blocked_grid(shape, first, S, lambda x, z: amp * fr.fbm_xz(x, z, sd, wl, (0.65, 0.35)))
    wz = fr.blocked_grid(shape, first, S, lambda x, z: amp * fr.fbm_xz(x - 37171.0, z + 12011.0, sd, wl, (0.65, 0.35)))
    return wx, wz, amp


def _belt_fields(belts, shape, first, S, wx, wz, wamp, floor_edge):
    """q = max over belt segments of x = clip(1 - d / W, 0, 1); floor = max of floor_m * smoothstep(x / floor_edge);
    bid = index of the belt giving q (-1 outside). belts: list of dict(xz, W, floor)."""
    nz, nx = shape
    q = np.zeros(shape, np.float32)
    fl = np.zeros(shape, np.float32)
    bid = np.full(shape, -1, np.int16)
    x0, z0 = float(first[0]), float(first[1])
    for bi, b in enumerate(belts):
        V, W, F = b['xz'], b['W'], b['floor']
        for j in range(len(V) - 1):
            ax, az = V[j]; bx, bz = V[j + 1]
            reach = max(W[j], W[j + 1]) + 1.5 * wamp
            i0 = int(math.floor((min(ax, bx) - reach - x0) / S)); i1 = int(math.ceil((max(ax, bx) + reach - x0) / S))
            k0 = int(math.floor((min(az, bz) - reach - z0) / S)); k1 = int(math.ceil((max(az, bz) + reach - z0) / S))
            xi = np.arange(i0, min(i1, i0 + nx - 1) + 1); zi = np.arange(k0, min(k1, k0 + nz - 1) + 1)
            sub = np.ix_(zi % nz, xi % nx)
            px = (x0 + xi * S)[None, :] + wx[sub]
            pz = (z0 + zi * S)[:, None] + wz[sub]
            dx, dz = bx - ax, bz - az
            l2 = max(dx * dx + dz * dz, 1e-9)
            t = np.clip(((px - ax) * dx + (pz - az) * dz) / l2, 0.0, 1.0)
            d = np.hypot(px - (ax + t * dx), pz - (az + t * dz))
            w = W[j] + (W[j + 1] - W[j]) * t
            x = np.clip(1.0 - d / w, 0.0, 1.0).astype(np.float32)
            f = ((F[j] + (F[j + 1] - F[j]) * t) * _smoothstep(x / floor_edge)).astype(np.float32)
            cq = q[sub]
            up = x > cq
            if up.any():
                q[sub] = np.where(up, x, cq)
                bid[sub] = np.where(up & (x > 0), bi, bid[sub])
            fl[sub] = np.maximum(fl[sub], f)
    return q, fl, bid


def _belt_lines(plate_id, velocities, land, cell_m, origin_xz_m, world_seed, p, thickness):
    from . import mountains as mt
    seeds = orogen_seeds(world_seed)
    nz, nx = land.shape
    extent_km = max(nz, nx) * cell_m / 1000.0
    sc = math.sqrt(extent_km / float(p['ref_size_km']))
    km = 1000.0 * sc
    conv = mt.boundary_convergence(plate_id, velocities)
    strength = conv['strength']
    local_land = ndimage.uniform_filter(land.astype(np.float64), size=7, mode='wrap')
    sel = (strength > 0) & (local_land > 0.05)
    land_at = _Field(land, cell_m, origin_xz_m)
    str_at = _Field(ndimage.maximum_filter(strength, size=5, mode='wrap'), cell_m, origin_xz_m)
    th_at = _Field(ndimage.maximum_filter(np.asarray(thickness, np.float64), size=3, mode='wrap'), cell_m, origin_xz_m)
    paths = trace_paths(sel, p)
    belts = []
    bv = float(p['belt_vertex_km']) * 1000.0
    for chain, path in enumerate(paths):
        rng = np.random.default_rng([seeds['orogen/belt'], chain])
        pts = _resample(_unwrap_cells(path, (nz, nx), cell_m, origin_xz_m), cell_m)
        w = int(p['belt_smooth_cells'])
        if len(pts) >= w:
            pts = np.stack([ndimage.uniform_filter1d(pts[:, k], w, mode='nearest') for k in (0, 1)], 1)
        _, nrm = _normals(pts)
        probe = float(p['major_half_km'][0]) * km
        lp = sum(land_at(pts[:, 0] + nrm[:, 0] * probe * f, pts[:, 1] + nrm[:, 1] * probe * f).astype(float) for f in (.3, .7, 1.1))
        lm = sum(land_at(pts[:, 0] - nrm[:, 0] * probe * f, pts[:, 1] - nrm[:, 1] * probe * f).astype(float) for f in (.3, .7, 1.1))
        side = np.sign(ndimage.uniform_filter1d(lp - lm, min(len(pts), 21), mode='nearest'))
        side[side == 0] = 1.0
        pts = pts + nrm * (side * float(p['belt_landward_km']) * km)[:, None]
        s = _arclength(pts)
        land_len = float(np.sum(land_at(pts[:, 0], pts[:, 1]).astype(float)[:-1] * np.diff(s)))
        if land_len < float(p['min_belt_km']) * km:
            continue
        lo, hi = (v * km for v in p['belt_control_km'])
        cs = [0.0]
        while cs[-1] + lo < s[-1]:
            cs.append(cs[-1] + rng.uniform(lo, hi))
        if s[-1] - cs[-1] < 0.4 * lo and len(cs) > 1:
            cs[-1] = s[-1]
        else:
            cs.append(s[-1])
        cs = np.array(cs)
        ctrl = np.stack([np.interp(cs, s, pts[:, 0]), np.interp(cs, s, pts[:, 1])], 1)
        if len(ctrl) > 2:
            _, cn = _normals(ctrl)
            ctrl[1:-1] += cn[1:-1] * (rng.standard_normal(len(ctrl) - 2) * float(p['belt_jitter']) * np.gradient(cs)[1:-1])[:, None]
        poly = _resample(_mpd(ctrl, rng, float(p['belt_rough']), bv), bv)
        sv = _arclength(poly)
        side_v = np.sign(np.interp(sv / max(sv[-1], 1.0) * s[-1], s, side)); side_v[side_v == 0] = 1.0
        belts.append(dict(xz=poly, side=side_v, chain=chain, land_len=land_len, rng_state=chain,
                          strength=float(np.mean(str_at(poly[:, 0], poly[:, 1]))),
                          thick=th_at(poly[:, 0], poly[:, 1]).astype(np.float64)))
    if belts and not any(b['land_len'] >= float(p['major_min_km']) * km for b in belts):
        max(belts, key=lambda b: b['land_len'])['force_major'] = True
    for b in belts:
        rng = np.random.default_rng([seeds['orogen/belt'], b['chain'], 1])
        major = b['land_len'] >= float(p['major_min_km']) * km or b.get('force_major', False)
        b['cls'] = 1 if major else 2
        lo, hi = p['major_half_km'] if major else p['minor_half_km']
        if major:
            f = np.clip((b['land_len'] / km - float(p['major_min_km'])) / 1200.0, 0.0, 1.0)
            base = (lo + (hi - lo) * (0.35 + 0.65 * f) * rng.uniform(0.75, 1.0)) * km
        else:
            base = rng.uniform(lo, hi) * km
        sv = _arclength(b['xz'])
        n = _noise1(sv + b['chain'] * 2.3e7, seeds['orogen/along-strike'], [v * km for v in p['belt_width_wavelengths_km']])
        wf = np.clip(1 + float(p['belt_width_var']) * n * 1.8, 0.65, 1.35)
        de = np.minimum(sv, sv[-1] - sv)
        taper = 0.5 + 0.5 * _smoothstep(de / (float(p['belt_end_taper_km']) * km))
        b['W0'] = base * wf * taper
        t0, t1 = (v * 1000.0 for v in p['plateau_thick_km'])
        b['plateau'] = (_smoothstep((b['thick'] - t0) / (t1 - t0)) * taper * (1.0 if major else 0.0)).astype(np.float64)
        flo, fhi = p['floor_major_m'] if major else p['floor_minor_m']
        b['floor_base'] = rng.uniform(flo, fhi)
    return belts, dict(seeds=seeds, sc=sc, km=km, conv=conv, land_at=land_at, str_at=str_at, paths=len(paths))


def _belt_scale(b, scale):
    """Width scale is applied to major belts only; secondary belts keep their 40-120 km design width."""
    return scale if b['cls'] == 1 else 1.0


def _choose_width_scale(belts, land, cell_m, origin_xz_m, p, seeds):
    """Bisect the major-belt width scale so the belt footprint (q > footprint_min) covers target_cover of the land
    (evaluated on the skeleton cell grid). Secondary belts are not scaled; if the cover is still above the band at the
    lowest major scale, the shortest secondary belts are dropped first (user: rather few and wide than many and thin).
    Returns (scale, trials, dropped belt indices)."""
    shape = land.shape
    first = (origin_xz_m[0] + cell_m / 2, origin_xz_m[1] + cell_m / 2)
    wx, wz, wamp = _belt_warp(shape, first, cell_m, p, seeds)
    lo, hi = (float(v) for v in p['width_scale_range'])
    trials = []
    dropped = []

    def cover(scale):
        bl = [dict(xz=b['xz'], W=b['W0'] * _belt_scale(b, scale), floor=np.zeros(len(b['xz'])))
              for i, b in enumerate(belts) if i not in dropped]
        q, _, _ = _belt_fields(bl, shape, first, cell_m, wx, wz, wamp, float(p['floor_edge']))
        c = float((q > float(p['footprint_min']))[land].mean())
        trials.append(dict(scale=float(scale), cover=c, dropped=list(dropped)))
        return c
    target = float(p['target_cover'])
    band_hi = float(p['cover_band'][1])
    minors = sorted((i for i, b in enumerate(belts) if b['cls'] != 1), key=lambda i: belts[i]['land_len'])
    while cover(lo) > band_hi and minors:
        dropped.append(minors.pop(0))
    if cover(hi) <= target:
        return hi, trials, dropped
    if cover(lo) >= target:
        return lo, trials, dropped
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if cover(mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), trials, dropped


def build_orogen_network(plate_id, velocities, land, thickness, *, cell_m, origin_xz_m, world_seed, params=None):
    """Return (net, meta) of the v4 orogen network: v3 line arrays (ranges = level 1) + ARRAY_NAMES_V4 belt arrays."""
    p = dict(OROGEN_DEFAULTS); p.update(params or {})
    belts, ctx = _belt_lines(plate_id, velocities, land, cell_m, origin_xz_m, world_seed, p, thickness)
    seeds, km, land_at, str_at = ctx['seeds'], ctx['km'], ctx['land_at'], ctx['str_at']
    scale, trials, dropped = _choose_width_scale(belts, land, cell_m, origin_xz_m, p, seeds) if belts else (1.0, [], [])
    dropped_chains = [int(belts[i]['chain']) for i in dropped]
    belts = [b for i, b in enumerate(belts) if i not in dropped]
    vs = float(p['vertex_spacing_km']) * 1000.0
    lines, passes, gaps_out = [], [], []
    stats = dict(boundary_paths=ctx['paths'], belts=len(belts), major_belts=0, minor_belts=0, ranges=0, range_runs=0,
                 gaps=0, strait_breaks=0, water_gaps=0, passes=0, branches=0, spurs=0, dropped_short=0)
    for bi, b in enumerate(belts):
        b['W'] = b['W0'] * _belt_scale(b, scale)
        b['floor'] = b['floor_base'] + float(p['plateau_m']) * b['plateau']
        major = b['cls'] == 1
        stats['major_belts' if major else 'minor_belts'] += 1
        rng = np.random.default_rng([seeds['orogen/ranges'], b['chain']])
        Wm = float(np.median(b['W']))
        if major:
            n = int(np.clip(round(2 * Wm / (float(p['major_range_km']) * km)), *p['major_ranges']))
        else:
            n = 2 if 2 * Wm >= float(p['minor_two_ranges_km']) * km and rng.random() < 0.7 else 1
        span = float(p['range_span'])
        fk = np.linspace(-span, span, n) if n > 1 else np.zeros(1)
        fk = fk + rng.uniform(-1, 1, n) * float(p['range_offset_jitter'])
        main_k = int(np.argmin(np.abs(fk) + rng.uniform(0, 0.25, n)))
        cxz = b['xz']; csv = _arclength(cxz)
        _, cn = _normals(cxz)
        polys = []
        for k in range(n):
            nk = _noise1(csv + (b['chain'] * 11 + k) * 3.1e7, seeds['orogen/along-strike'],
                         [v * km for v in p['range_offset_wavelengths_km']])
            off = (fk[k] + float(p['range_offset_var']) * nk * 1.8) * b['W']
            pts = cxz + cn * off[:, None]
            s = _arclength(pts)
            lo, hi = (v * km for v in p['range_control_km'])
            cs = [0.0]
            while cs[-1] + lo < s[-1]:
                cs.append(cs[-1] + rng.uniform(lo, hi))
            if s[-1] - cs[-1] < 0.4 * lo and len(cs) > 1:
                cs[-1] = s[-1]
            else:
                cs.append(s[-1])
            cs = np.array(cs)
            ctrl = np.stack([np.interp(cs, s, pts[:, 0]), np.interp(cs, s, pts[:, 1])], 1)
            if len(ctrl) > 2:
                _, ccn = _normals(ctrl)
                ctrl[1:-1] += ccn[1:-1] * (rng.standard_normal(len(ctrl) - 2) * float(p['control_jitter']) * np.gradient(cs)[1:-1])[:, None]
            poly = _mpd(ctrl, rng, float(p['mpd_rough']), vs)
            sv = _arclength(poly)
            u = np.interp(sv / max(sv[-1], 1.0) * s[-1], s, csv)          # belt arclength of each range vertex
            Wv = np.interp(u, csv, b['W']); side_v = np.sign(np.interp(u, csv, b['side'])); side_v[side_v == 0] = 1.0
            plat = np.interp(u, csv, b['plateau'])
            spacing = (2 * span * Wv / (n - 1)) if n > 1 else Wv
            n1 = _noise1(sv + (b['chain'] * 7 + k) * 1.9e7, seeds['orogen/along-strike'], [v * km for v in p['along_wavelengths_km']])
            n2 = _noise1(sv + (b['chain'] * 7 + k) * 1.9e7 + 5.3e6, seeds['orogen/along-strike'], [v * km for v in p['along_wavelengths_km']])
            hw = float(p['range_half_frac']) * spacing * rng.uniform(0.85, 1.1) * np.clip(1 + float(p['width_var']) * n1 * 1.8, 0.6, 1.4)
            hw = np.minimum(hw, Wv * 0.75)
            st = str_at(poly[:, 0], poly[:, 1])
            a_lo, a_hi = p['range_amp_main'] if k == main_k else p['range_amp_other']
            amp = (rng.uniform(a_lo, a_hi) * (0.65 + 0.35 * st) * np.clip(1 + float(p['amp_var']) * n2 * 1.8, 0.45, 1.35)
                   * (1.0 if major else float(p['minor_amp'])) * (1.0 - float(p['plateau_amp_cut']) * plat))
            polys.append(dict(xz=poly, ww=hw, ws=hw * rng.uniform(*p['range_steep_ratio']), amp=amp, side=side_v,
                              u=u, gaps=[]))
            stats['ranges'] += 1
        # water gaps: all ranges of the belt are lowered at the same belt station
        rw = np.random.default_rng([seeds['orogen/water-gaps'], b['chain']])
        sp = float(p['water_gap_spacing_km']) * km
        count = int(csv[-1] // sp) + int(csv[-1] > 0.45 * sp and rw.random() < 0.7)
        _, ctan = _normals(cxz)
        for g in range(count):
            u0 = (g + rw.uniform(0.25, 0.75)) / max(count, 1) * csv[-1]
            hwg = rw.uniform(*p['water_gap_half_km']) * km
            depth = rw.uniform(*p['water_gap_depth'])
            stats['water_gaps'] += 1
            ig = int(np.argmin(np.abs(csv - u0)))
            if bool(land_at(cxz[ig, 0], cxz[ig, 1])):     # corridor across the whole belt (platform + hills + crests)
                gaps_out.append((float(cxz[ig, 0]), float(cxz[ig, 1]), float(ctan[ig, 0]), float(ctan[ig, 1]),
                                 max(float(p['water_gap_corridor']) * hwg, float(p['water_gap_corridor_min_km']) * km),
                                 float(b['W'][ig]), float(depth), bi))
            for r in polys:
                sv = _arclength(r['xz'])
                i = int(np.argmin(np.abs(r['u'] - u0)))
                bump = 0.5 * (1 + np.cos(np.pi * np.clip(np.abs(sv - sv[i]) / hwg, 0, 1)))
                r['amp'] = r['amp'] * (1 - depth * bump)
                r['gaps'].append((i, depth))
        # breaks + runs
        for k, r in enumerate(polys):
            rb = np.random.default_rng([seeds['orogen/breaks'], b['chain'], k])
            sv = _arclength(r['xz'])
            keep = land_at(r['xz'][:, 0], r['xz'][:, 1]).astype(bool)
            stats['strait_breaks'] += int(np.sum(np.diff(keep.astype(int)) == -1))
            g0 = rb.uniform(0.3, 1.0) * float(p['gap_mean_km']) * km
            while g0 < sv[-1] - 40 * km:
                gl = rb.uniform(*p['gap_len_km']) * km
                keep &= ~((sv >= g0) & (sv < g0 + gl))
                stats['gaps'] += 1
                g0 += gl + rb.exponential(float(p['gap_mean_km']) * km)
            for r0, r1 in _runs(keep):
                if sv[r1 - 1] - sv[r0] < float(p['min_run_km']) * km:
                    stats['dropped_short'] += 1
                    continue
                seg = slice(r0, r1)
                line = dict(xz=r['xz'][seg].copy(), ww=r['ww'][seg].copy(), ws=r['ws'][seg].copy(), amp=r['amp'][seg].copy(),
                            side=r['side'][seg].copy(), level=1, parent=-1, chain=b['chain'], belt=bi, Wm=Wm)
                _taper(line, float(p['end_taper_km']) * km)
                li = len(lines)
                lines.append(line)
                stats['range_runs'] += 1
                svr = _arclength(line['xz'])
                for i, depth in r['gaps']:
                    if r0 <= i < r1:
                        passes.append((float(r['xz'][i, 0]), float(r['xz'][i, 1]), float(depth), li, float(svr[i - r0])))
                        stats['passes'] += 1
    mains = len(lines)
    for li in range(mains):
        par = lines[li]
        Wm = par['Wm']
        new = _grow(par, li, seeds['orogen/branches'], p, km, vs, land_at, passes, level=2, spacing=p['branch_spacing_km'],
                    length=lambda r, L, Wm=Wm: r.uniform(*p['branch_len_frac']) * Wm)
        stats['branches'] += len(new)
        for nb in new:
            nb['belt'] = par['belt']
            bi = len(lines)
            lines.append(nb)
            L2 = _arclength(nb['xz'])[-1]
            subs = _grow(nb, bi, seeds['orogen/branches'] ^ 0x5bd1e995, p, km, vs, land_at, [], level=3,
                         spacing=p['sub_spacing_km'], length=lambda r, L, L2=L2: r.uniform(*p['sub_len_frac']) * L2)
            for s_ in subs:
                s_['belt'] = par['belt']
            stats['spurs'] += len(subs)
            lines.extend(subs)
    net = _pack(lines, passes)
    net['line_belt'] = np.array([l['belt'] for l in lines], np.int32)
    boffs = np.cumsum([0] + [len(b['xz']) for b in belts]).astype(np.int64)
    cat = lambda key, dt: (np.concatenate([np.asarray(b[key], np.float64) for b in belts]).astype(dt) if belts else np.zeros(0, dt))
    net.update(belt_offsets=boffs, belt_class=np.array([b['cls'] for b in belts], np.int8),
               belt_chain=np.array([b['chain'] for b in belts], np.int32),
               belt_xz_m=(np.concatenate([b['xz'] for b in belts]) if belts else np.zeros((0, 2))).astype(np.float64).reshape(-1, 2),
               belt_half_width_m=cat('W', np.float32), belt_side=cat('side', np.int8), belt_floor_m=cat('floor', np.float32),
               belt_plateau=cat('plateau', np.float32))
    G = np.asarray(gaps_out, np.float64).reshape(-1, 8)
    net.update(gap_xz_m=G[:, 0:2].copy(), gap_tangent=G[:, 2:4].astype(np.float32), gap_half_m=G[:, 4].astype(np.float32),
               gap_belt_half_m=G[:, 5].astype(np.float32), gap_depth=G[:, 6].astype(np.float32), gap_belt=G[:, 7].astype(np.int32))
    stats['water_gap_corridors'] = int(len(G))
    widths = {}
    for bi, b in enumerate(belts):
        on = land_at(b['xz'][:, 0], b['xz'][:, 1]).astype(bool)
        wv = 2 * b['W'][on] / 1000.0 if on.any() else 2 * b['W'] / 1000.0
        widths[str(bi)] = dict(cls='major' if b['cls'] == 1 else 'secondary', chain=int(b['chain']),
                               length_km=float(_arclength(b['xz'])[-1] / 1000.0), land_length_km=float(b['land_len'] / 1000.0),
                               design_width_km=dict(median=float(np.median(wv)), p10=float(np.percentile(wv, 10)),
                                                    p90=float(np.percentile(wv, 90))),
                               ranges=int(sum(1 for l in lines if l['level'] == 1 and l['belt'] == bi)),
                               plateau_max=float(b['plateau'].max()), floor_m_median=float(np.median(b['floor'])))
    meta = dict(algorithm=OROGEN_ALGORITHM, params={k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()},
                size_scale=ctx['sc'], subseeds={k: str(v) for k, v in seeds.items()}, statistics=stats,
                boundary_cells=ctx['conv']['cells'], plate_pairs=ctx['conv']['pairs'], width_scale=float(scale),
                width_scale_trials=trials, width_scale_applies_to='major belts only', dropped_secondary_chains=dropped_chains,
                belts=widths,
                lines=int(len(net['line_level'])), vertices=int(len(net['vertex_amp'])),
                lines_by_level={str(l): int((net['line_level'] == l).sum()) for l in (1, 2, 3)},
                length_km_by_level={str(l): float(_level_length(net, l) / 1000.0) for l in (1, 2, 3)},
                identity=network_identity(net))
    return net, meta


def _belts_of(net):
    o = net['belt_offsets']
    return [dict(xz=net['belt_xz_m'][o[i]:o[i + 1]], W=net['belt_half_width_m'][o[i]:o[i + 1]].astype(np.float64),
                 floor=net['belt_floor_m'][o[i]:o[i + 1]].astype(np.float64)) for i in range(len(o) - 1)]


def _gap_factor(net, shape, first_xz_m, S, cross, seed=0, meander=1.6, meander_wl_m=45000.0):
    """1 - depth * bump(along-strike distance / half) * fade(across-belt distance / (cross * W)) per water gap (min-combined);
    cosine bumps on the belt-aligned frame of the gap station (no Gaussian). The corridor axis meanders: its along-strike
    position is shifted by meander * half * fbm(across distance), so the gap is a winding valley, not a straight trench.
    None when the net has no gap corridors."""
    if 'gap_xz_m' not in net or not len(net['gap_xz_m']):
        return None
    fr = _fr()
    nz, nx = shape
    x0, z0 = float(first_xz_m[0]), float(first_xz_m[1])
    f = np.ones(shape, np.float32)
    for gi, ((cx, cz), (tx, tz), hw, W, dep) in enumerate(zip(net['gap_xz_m'], net['gap_tangent'].astype(np.float64),
                                                              net['gap_half_m'].astype(np.float64),
                                                              net['gap_belt_half_m'].astype(np.float64), net['gap_depth'].astype(np.float64))):
        reach = cross * W + hw * (1.0 + meander)
        i0 = int(math.floor((cx - reach - x0) / S)); i1 = int(math.ceil((cx + reach - x0) / S))
        k0 = int(math.floor((cz - reach - z0) / S)); k1 = int(math.ceil((cz + reach - z0) / S))
        xi = np.arange(i0, min(i1, i0 + nx - 1) + 1); zi = np.arange(k0, min(k1, k0 + nz - 1) + 1)
        sub = np.ix_(zi % nz, xi % nx)
        dx = (x0 + xi * S)[None, :] - cx; dz = (z0 + zi * S)[:, None] - cz
        acr = -dx * tz + dz * tx
        shift = meander * hw * fr.fbm_xz(acr, np.full_like(acr, 1.0e7 * (gi + 1)), seed, (meander_wl_m, meander_wl_m / 2.6), (0.7, 0.3))
        along = np.abs(dx * tx + dz * tz - shift); across = np.abs(acr)
        bump = 0.5 * (1 + np.cos(np.pi * np.clip(along / hw, 0, 1)))
        fade = 1.0 - _smoothstep((across - W) / max((cross - 1.0) * W, 1.0))
        g = (1.0 - dep * bump * fade).astype(np.float32)
        f[sub] = np.minimum(f[sub], g)
    return f


def rasterize_orogen(net, shape, first_xz_m, spacing_m, *, world_seed, params=None):
    """v4 relief on a cell-centre grid (periodic). Returns dict(relief_m, footprint q, floor_m, hills_m, envelope, ridged,
    level, belt_id). relief_m = floor + hills + amp_m * envelope * (crest_floor + crest_gain * R); add the lowland base."""
    fr = _fr()
    p = dict(OROGEN_DEFAULTS); p.update(params or {})
    seeds = orogen_seeds(world_seed)
    S = float(spacing_m)
    bwx, bwz, bwamp = _belt_warp(shape, first_xz_m, S, p, seeds)
    q, floor, bid = _belt_fields(_belts_of(net), shape, first_xz_m, S, bwx, bwz, bwamp, float(p['floor_edge']))
    del bwx, bwz
    wamp = float(p['warp_amp_km']) * 1000.0
    wwl = [v * 1000.0 for v in p['warp_wavelengths_km']]
    wx = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: wamp * fr.fbm_xz(x, z, seeds['orogen/warp'], wwl, (0.65, 0.35)))
    wz = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: wamp * fr.fbm_xz(x + 51413.0, z - 23071.0, seeds['orogen/warp'], wwl, (0.65, 0.35)))
    env, level = _segment_envelope(net, shape, first_xz_m, S, wx, wz, wamp, float(p['profile_exp']))
    del wx, wz
    rwl = [v * 1000.0 for v in p['ridged_wavelengths_km']]
    R = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: ridged_multifractal(x, z, seeds['orogen/ridged'], rwl, float(p['ridged_h']),
                                                                               float(p['ridged_gain']), float(p['ridged_offset'])))
    hwl = [v * 1000.0 for v in p['hills_wavelengths_km']]
    H = fr.blocked_grid(shape, first_xz_m, S, lambda x, z: fr.fbm_xz(x, z, seeds['orogen/hills'], hwl, (0.6, 0.4), ridged=True))
    t = np.clip(q / float(p['hills_band']), 0.0, 1.0)
    bump = _smoothstep(t / 0.5) * (1.0 - (1.0 - float(p['basin_relief'])) * _smoothstep((t - 0.5) / 0.5))
    bump = np.where(q > 0, bump, 0.0)
    hills = (float(p['hills_m']) * bump * (0.2 + 0.8 * H)).astype(np.float32)
    del H, t, bump
    crest = (env * (float(p['crest_floor']) + float(p['crest_gain']) * R)).astype(np.float32)
    gapf = _gap_factor(net, shape, first_xz_m, S, float(p['water_gap_cross']), seeds['orogen/water-gaps'],
                       float(p['water_gap_meander']))
    if gapf is not None:                       # water-gap corridors: crests cut to the gap depth, platform/hills partly lowered
        pf = (1.0 - float(p['water_gap_floor_share']) * (1.0 - gapf)).astype(np.float32)
        floor = (floor * pf).astype(np.float32); hills = (hills * pf).astype(np.float32); crest = (crest * gapf).astype(np.float32)
    relief = (floor + hills + float(p['amp_m']) * crest).astype(np.float32)
    return dict(relief_m=relief, footprint=q, floor_m=floor, hills_m=hills, envelope=env, ridged=R, level=level, belt_id=bid,
                crest=crest)


def build_orogen_mountains(elev, plate_id, velocities, thickness, *, cell_m, origin_xz_m, world_seed, params=None,
                           proxy_m=1500.0, fine_m=2000.0):
    """v4 land elevation = lowland base + box mean (to the skeleton cell) of the 2 km orogen relief. Ocean untouched."""
    e = np.asarray(elev, np.float64)
    land = e > 0
    nz, nx = land.shape
    k = int(round(cell_m / fine_m))
    if abs(k * fine_m - cell_m) > 1e-6:
        raise ValueError('cell size must be a multiple of fine_m')
    p = dict(OROGEN_DEFAULTS); p.update(params or {})
    net, meta = build_orogen_network(plate_id, velocities, land, thickness, cell_m=cell_m, origin_xz_m=origin_xz_m,
                                     world_seed=world_seed, params=params)
    base = lowland_base(land, cell_m, world_seed)
    first = (origin_xz_m[0] + fine_m / 2, origin_xz_m[1] + fine_m / 2)
    parts = rasterize_orogen(net, (nz * k, nx * k), first, fine_m, world_seed=world_seed, params=params)
    relief = block_mean(parts['relief_m'].astype(np.float64), k)
    foot = block_mean((parts['footprint'] > float(p['footprint_min'])).astype(np.float64), k) > 0.5
    out = np.where(land, np.maximum(base + relief, 1.0), e)
    assert ((out > 0) == land).all(), 'orogen mountains changed the land/sea split'
    assert (out[~land] == e[~land]).all()
    meta.update(applied=True, amp_m=float(p['amp_m']), fine_spacing_m=fine_m, proxy_m=float(proxy_m),
                mountain_area_land_fraction=float(foot[land].mean()),
                high_mountain_land_fraction=float((out > proxy_m)[land].mean()),
                target_cover=float(p['target_cover']), cover_band=list(p['cover_band']),
                raster='belt platform floor * smoothstep(x/%g) (x = 1 - d/W on domain-warped coordinates, flat-topped, not Gaussian) '
                       '+ foothill ring of ridged-noise hills + ranges: max-union of segment tent profiles (1-d/w)^%g x ridged multifractal; '
                       'evaluated at %g m and box-averaged to the skeleton cell; no Gaussian profile, no Gaussian blur'
                       % (float(p['floor_edge']), float(p['profile_exp']), fine_m),
                lowland='120 m + 700 m * smoothstep(coast distance / 350 km) + 90 m FFT plains relief, capped 1150 m (as v3)')
    return out, base, net, meta
