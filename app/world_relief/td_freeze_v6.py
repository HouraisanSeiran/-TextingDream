"""td-world-960m-v6: irregular-graph drainage (no D8) on the frozen v5 terrain.

Differences to v5 (derived hydrology layers and vectors only; ``elevation_m``, ``ocean_mask`` and the sea/land
classification are copied value for value and never modified):

* Routing / accumulation: Terragenesis ``terrain_pipeline.irregular_grid.grid_mesh`` (seeded jittered nodes, Delaunay
  edges, world-metre positions) + ``irregular_drainage.route_graph`` (priority-flood fill on the graph, steepest downhill
  graph edge by true edge length) + ``accumulate_graph``. These are the same functions ``surface_rivers.drainage.route``
  composes; the mesh is built here once because node positions are needed for the river geometry.
  Nothing from ``drainage.py`` / ``td_flats.py`` is called.
* Hydrology bed: v5 ``hydro_bed_m`` is the starting bed (already breached once). Depressions of the *irregular* graph
  that are shallower than ``depth_min_m`` or smaller than ``area_min_m2`` are breached again along the irregular
  receiver (``breach_graph``) until none is left; kept lakes follow the v5 rule.
* Rivers: slope-zoned area threshold (v4/v5 rule) + downstream closure on the irregular receivers; river points are the
  metric node positions (not cell centres), lightly smoothed by a constrained Laplace step (see ``smooth_centerline``);
  through-lake connections as in v5.

Node displacement is a finite-volume representative position, not a new terrain sample (module header of
``irregular_drainage``). The domain rim is an explicit outlet, as in v5.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy import ndimage, sparse
from scipy.sparse import csgraph
from .td_pages import file_sha, write_json
from .source import identity, subseed
from . import td_hydro            # only classify / unit_stats / EPS_DROP / WET_TOL / lake_vectors_labeled are used (no D8 call)

SCHEMA = 'td-world-960m-v6'
ROUTING = 'irregular-delaunay (terragenesis irregular_drainage)'
MESH_PURPOSE = 'rivers/irregular-mesh'
V5_IDENTITY = '3b1703739c0e16283172d74a66d4bbcceb23c89bd2ecc811a3e32b5d12d1e63f'
# river threshold rule copied from td_freeze_v4 (not imported: that module imports the D8 router)
RIVER_LO_M2 = 100e6
RIVER_HI_M2 = 300e6
SLOPE_SPLIT = 0.015
SLOPE_SMOOTH_CELLS = 5
# constrained centreline smoothing (equivalent of channel_centerline.SmoothingRecipe, applied to graph nodes)
SMOOTH_STRENGTH = 0.25
SMOOTH_MAX_OFFSET_M = 200.0
SMOOTH_PASSES = 4
TG_FILES = ('terrain_pipeline/irregular_drainage.py', 'terrain_pipeline/irregular_grid.py',
            'terrain_pipeline/surface_rivers/drainage.py')


# ------------------------------------------------------------------ Terragenesis access
def terragenesis_root():
    return Path(__file__).resolve().parents[2].parent / '山川形意Terragenesis'


def load_terragenesis(root=None):
    """Import (read only) the Terragenesis graph modules; needs numba (Terragenesis venv)."""
    root = Path(root) if root else terragenesis_root()
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from terrain_pipeline import irregular_drainage, irregular_grid
    return irregular_drainage, irregular_grid


def build_graph(shape, first, spacing, mesh_seed):
    _, grid = load_terragenesis()
    return grid.grid_mesh(tuple(int(v) for v in shape), x0_m=float(first[0]), z0_m=float(first[1]), dx_m=float(spacing),
                          world_seed=int(mesh_seed))


# ------------------------------------------------------------------ hydrology on the graph
def graph_depression_labels(mesh, bed, filled, ocean):
    """Connected sets of graph nodes sharing one filled level above the bed (flat arrays). Returns (labels, wet)."""
    n = bed.size
    wet = (filled - bed > td_hydro.WET_TOL) & ~ocean
    src = np.repeat(np.arange(n, dtype=np.int32), np.diff(mesh.indptr))
    dst = mesh.indices
    both = wet[src] & wet[dst] & (filled[src] == filled[dst])
    g = sparse.coo_matrix((np.ones(int(both.sum()), np.int8), (src[both], dst[both])), shape=(n, n))
    _, comp = csgraph.connected_components(g, directed=False)
    labels = np.zeros(n, np.int64)
    _, inverse = np.unique(comp[wet], return_inverse=True)
    labels[wet] = inverse + 1
    return labels, wet


def breach_graph(bed, receiver, pits, ocean):
    """Copy of ``bed`` with a descending channel cut from every pit along the irregular-graph ``receiver`` (-1 = outlet)."""
    base = np.asarray(bed).ravel()
    new = base.copy()
    rec = np.asarray(receiver).ravel()
    oc = np.asarray(ocean).ravel()
    cut = 0
    for p in pits:
        cur = int(p); prof = float(base[cur]); floor = 0.0 if prof >= 0 else -np.inf
        for _ in range(base.size):
            nxt = int(rec[cur])
            if nxt < 0 or oc[nxt]:
                break
            if base[nxt] < prof - td_hydro.EPS_DROP:
                break
            prof = max(prof - td_hydro.EPS_DROP, floor)
            if new[nxt] > prof:
                new[nxt] = prof; cut += 1
            cur = nxt
    return new.reshape(np.shape(bed)), cut


def hydrology(bed0, ocean, mesh, outlets, depth_min_m, area_min_m2, max_passes=16, log=None):
    """Breach-then-lake on the irregular graph. Returns dict(bed, filled, receiver, order, area_m2, lake_id, ...)."""
    drain, _ = load_terragenesis()
    spacing = float(mesh.spacing_m)
    bed = np.asarray(bed0, np.float64).copy()
    oc = np.asarray(ocean, bool).ravel()
    passes = []; route = None
    for k in range(max_passes):
        route = drain.route_graph(bed, outlets, mesh)
        filled = np.asarray(route.filled).ravel()
        labels, _ = graph_depression_labels(mesh, bed.ravel(), filled, oc)
        st = td_hydro.unit_stats(bed.ravel(), filled, labels)
        keep = td_hydro.classify(st, bed.ravel(), spacing, depth_min_m, area_min_m2)
        failing = np.flatnonzero(~keep)
        passes.append(dict(pass_index=k, depressions=int(keep.size), failing=int(failing.size), kept=int(keep.sum())))
        if log:
            log(passes[-1])
        if failing.size == 0:
            break
        bed, cut = breach_graph(bed, np.asarray(route.receiver), st['pit'][failing], oc)
        passes[-1]['cells_lowered'] = int(cut)
        route = None
        if cut == 0:
            break
    if route is None:
        route = drain.route_graph(bed, outlets, mesh)
    filled = np.asarray(route.filled).ravel()
    labels, _ = graph_depression_labels(mesh, bed.ravel(), filled, oc)
    st = td_hydro.unit_stats(bed.ravel(), filled, labels)
    keep = td_hydro.classify(st, bed.ravel(), spacing, depth_min_m, area_min_m2)
    remap = np.zeros(keep.size + 1, np.int64)
    remap[1:][keep] = np.arange(1, int(keep.sum()) + 1)
    lake_id = remap[labels]
    receiver = np.array(route.receiver, np.int64)
    order = np.array(route.order, np.int64)
    area = drain.accumulate_graph(receiver, order, np.full(receiver.size, spacing * spacing))
    return dict(bed=bed, filled=filled.reshape(bed.shape), receiver=receiver, order=order, area_m2=np.asarray(area).ravel(),
                lake_id=lake_id.astype(np.int32).reshape(bed.shape), passes=passes,
                unresolved_depressions=int((~keep).sum()), kept_lakes=int(keep.sum()))


# ------------------------------------------------------------------ river extraction
def zoned_threshold(elevation, spacing=960.0, lo=RIVER_LO_M2, hi=RIVER_HI_M2, split=SLOPE_SPLIT, smooth=SLOPE_SMOOTH_CELLS):
    gz, gx = np.gradient(np.asarray(elevation, np.float64), float(spacing))
    sm = ndimage.uniform_filter(np.hypot(gx, gz), smooth)
    return np.where(sm >= split, lo, hi)


def active_rivers(receiver, order, area, ocean, threshold):
    """area >= local threshold, plus the downstream closure along the irregular receivers (-1 = outlet)."""
    rec = np.asarray(receiver, np.int64).ravel(); oc = np.asarray(ocean, bool).ravel()
    active = ((np.asarray(area).ravel() >= np.asarray(threshold).ravel()) & ~oc)
    act = active.tolist(); r = rec.tolist(); o = oc.tolist()
    for cur in np.asarray(order)[::-1].tolist():          # donors before receivers
        if act[cur]:
            nxt = r[cur]
            if nxt >= 0 and not o[nxt]:
                act[nxt] = True
    return np.asarray(act, bool)


def _stable_id(i, first, spacing, nx):
    x = first[0] + (int(i) % nx) * spacing; z = first[1] + (int(i) // nx) * spacing
    return 'r-' + hashlib.sha256(f'{x:.3f},{z:.3f}'.encode()).hexdigest()[:20]


def trace_lines(receiver, area, active, shape, first, spacing):
    """Segments between junctions / heads along the receiver tree. Each line carries its node index path."""
    rec = np.asarray(receiver, np.int64).ravel(); area = np.asarray(area).ravel(); nx = shape[1]
    sel = rec[active]; sel = sel[sel >= 0]
    indeg = np.bincount(sel, minlength=rec.size)
    is_start = active & (indeg != 1)
    r = rec.tolist(); act = active.tolist(); ind = indeg.tolist(); st = is_start.tolist()
    lines = []
    for s in np.flatnonzero(is_start & (rec >= 0)).tolist():
        path = [s]; cur = s
        while True:
            nxt = r[cur]
            if nxt < 0:
                break
            path.append(nxt); cur = nxt
            if not act[cur] or ind[cur] != 1:
                break
        end = path[-1]
        down = _stable_id(end, first, spacing, nx) if (st[end] and r[end] >= 0) else None
        lines.append(dict(id=_stable_id(s, first, spacing, nx), downstream_id=down, nodes=path,
                          head_area_km2=float(area[s] / 1e6), outlet_area_km2=float(area[end] / 1e6)))
    upstream = {line['id']: [] for line in lines}
    for line in lines:
        if line['downstream_id'] in upstream:
            upstream[line['downstream_id']].append(line['id'])
    for line in lines:
        line['upstream_ids'] = sorted(upstream[line['id']])
    return sorted(lines, key=lambda line: line['id'])


def _crossing_nodes(x, z, ea, eb, bucket=2000.0):
    xl = x.tolist(); zl = z.tolist(); a_l = ea.tolist(); b_l = eb.tolist()
    buckets = {}; bad = set()
    for e in range(len(a_l)):
        a, b = a_l[e], b_l[e]
        ax, az, bx, bz = xl[a], zl[a], xl[b], zl[b]
        x0, x1 = int(min(ax, bx) // bucket), int(max(ax, bx) // bucket)
        z0, z1 = int(min(az, bz) // bucket), int(max(az, bz) // bucket)
        near = set()
        for ix in range(x0, x1 + 1):
            for iz in range(z0, z1 + 1):
                near.update(buckets.get((ix, iz), ()))
        for o in near:
            c, d = a_l[o], b_l[o]
            if c == a or c == b or d == a or d == b:
                continue
            cx, cz, dx, dz = xl[c], zl[c], xl[d], zl[d]
            o1 = (bx - ax) * (cz - az) - (bz - az) * (cx - ax)
            o2 = (bx - ax) * (dz - az) - (bz - az) * (dx - ax)
            o3 = (dx - cx) * (az - cz) - (dz - cz) * (ax - cx)
            o4 = (dx - cx) * (bz - cz) - (dz - cz) * (bx - cx)
            if o1 * o2 < 0 and o3 * o4 < 0:
                bad.update((a, b, c, d))
        for ix in range(x0, x1 + 1):
            for iz in range(z0, z1 + 1):
                buckets.setdefault((ix, iz), []).append(e)
    return bad


def smooth_centerline(px, pz, receiver, active, strength=SMOOTH_STRENGTH, max_offset_m=SMOOTH_MAX_OFFSET_M,
                      passes=SMOOTH_PASSES):
    """Move only degree-2 channel nodes (exactly one active donor, one receiver) toward the midpoint of donor and receiver.

    Heads, junctions and the outlet end never move; each node stays within ``max_offset_m`` of its graph position; nodes
    that would make two channel edges cross are put back (iterated). Topology is unchanged.
    """
    px = np.asarray(px, np.float64); pz = np.asarray(pz, np.float64)
    x = px.copy(); z = pz.copy(); n = x.size
    rec = np.asarray(receiver, np.int64).ravel(); act = np.flatnonzero(active)
    ok = rec[act] >= 0
    ea, eb = act[ok], rec[act[ok]]
    indeg = np.bincount(eb, minlength=n)
    donor = np.full(n, -1, np.int64); donor[eb] = ea
    mv = np.flatnonzero(active & (indeg == 1) & (rec >= 0))
    if mv.size == 0 or strength <= 0 or passes <= 0:
        return x, z, 0
    d, r = donor[mv], rec[mv]
    for _ in range(passes):
        nxx = x[mv] + strength * (0.5 * (x[d] + x[r]) - x[mv])
        nzz = z[mv] + strength * (0.5 * (z[d] + z[r]) - z[mv])
        ox, oz = nxx - px[mv], nzz - pz[mv]
        scale = np.minimum(1.0, max_offset_m / np.maximum(np.hypot(ox, oz), 1e-9))
        x[mv] = px[mv] + ox * scale; z[mv] = pz[mv] + oz * scale
    reverted = 0
    for _ in range(8):
        bad = _crossing_nodes(x, z, ea, eb)
        if not bad:
            break
        idx = np.fromiter(bad, np.int64)
        x[idx] = px[idx]; z[idx] = pz[idx]; reverted += idx.size
    else:
        x[:] = px; z[:] = pz
    return x, z, reverted


def standard_lines(lines, px, pz, shape, first, spacing, ocean, wet):
    """Raw (receiver-trace) lines and vector-schema lines with node positions as coordinates."""
    nz, nx = shape
    ocean = np.asarray(ocean, bool).ravel(); wet = np.asarray(wet, bool).ravel()
    raw = []; result = []
    for line in lines:
        coords = [[float(px[i]), float(pz[i])] for i in line['nodes']]
        raw.append(dict(id=line['id'], downstream_id=line['downstream_id'], coordinates_xz_m=coords,
                        head_area_km2=line['head_area_km2'], outlet_area_km2=line['outlet_area_km2'],
                        upstream_ids=line['upstream_ids']))
        e = line['nodes'][-1]; iz, ix = divmod(int(e), nx)
        outlet = 'ocean' if ocean[e] else 'edge' if ix in (0, nx - 1) or iz in (0, nz - 1) else 'lake' if wet[e] else 'closed'
        result.append(dict(id=line['id'], points_xz_m=coords, downstream_id=line['downstream_id'],
                           upstream_ids=line['upstream_ids'], drainage_area_m2=line['outlet_area_km2'] * 1e6,
                           head_drainage_area_m2=line['head_area_km2'] * 1e6, outlet=outlet))
    by_id = {v['id']: v for v in result}
    for item in result:
        cur = item; seen = set()
        while cur['downstream_id'] is not None:
            if cur['id'] in seen:
                raise ValueError('cyclic river')
            seen.add(cur['id']); cur = by_id[cur['downstream_id']]
        item['outlet'] = cur['outlet']
    return raw, result


def through_lake_lines(lines, lake_id, first, spacing):
    """Same rule as td_freeze_v5: each maximal run of >=2 consecutive points in a kept lake becomes one chord."""
    nz, nx = lake_id.shape
    out = []; n_through = 0; n_whole = 0; pts_before = 0; pts_after = 0
    for line in lines:
        c = np.asarray(line['points_xz_m'], np.float64)
        ix = np.clip(np.rint((c[:, 0] - first[0]) / spacing).astype(int), 0, nx - 1)
        iz = np.clip(np.rint((c[:, 1] - first[1]) / spacing).astype(int), 0, nz - 1)
        wet = lake_id[iz, ix] > 0
        item = dict(line); pts_before += len(c)
        if not wet.any():
            item.update(through_lake=False, lake_spans=[])
            out.append(item); pts_after += len(c)
            continue
        keep = np.ones(len(c), bool); runs = []; i = 0; n = len(c)
        while i < n:
            if wet[i]:
                j = i
                while j + 1 < n and wet[j + 1]:
                    j += 1
                if j > i:
                    runs.append((i, j)); keep[i + 1:j] = False
                i = j + 1
            else:
                i += 1
        new_pts = c[keep]; new_index = np.cumsum(keep) - 1
        item['points_xz_m'] = [[float(x), float(z)] for x, z in new_pts]
        item['through_lake'] = bool(runs)
        item['lake_spans'] = [[int(new_index[a]), int(new_index[b])] for a, b in runs]
        item['wholly_in_lake'] = bool(wet.all())
        item['lake_ids'] = sorted({int(v) for v in lake_id[iz, ix][wet]})
        n_through += bool(runs); n_whole += bool(wet.all()); pts_after += len(new_pts)
        out.append(item)
    return out, dict(lines=len(lines), through_lake_lines=n_through, wholly_in_lake_lines=n_whole,
                     points_before=pts_before, points_after=pts_after)


# ------------------------------------------------------------------ whole computation (arrays in, arrays out)
def compute_v6(elevation, hydro_bed, ocean, first, spacing=960.0, world_seed=20261020, mesh_seed=None,
               depth_min_m=30.0, area_min_m2=50e6, lo_m2=RIVER_LO_M2, hi_m2=RIVER_HI_M2, smooth=True, max_passes=16,
               log=None):
    """Irregular-graph routing, area, hydrology bed, lakes and river vectors for one grid. ``elevation`` is not modified."""
    elevation = np.asarray(elevation); ocean = np.asarray(ocean, bool)
    shape = elevation.shape
    if mesh_seed is None:
        mesh_seed = subseed(world_seed, MESH_PURPOSE)
    t0 = time.perf_counter()
    mesh = build_graph(shape, first, spacing, mesh_seed)
    t_mesh = time.perf_counter() - t0
    outlets = ocean.copy()
    outlets[0] = True; outlets[-1] = True; outlets[:, 0] = True; outlets[:, -1] = True     # domain rim = explicit outlet
    t0 = time.perf_counter()
    hyd = hydrology(hydro_bed, ocean, mesh, outlets, depth_min_m, area_min_m2, max_passes, log)
    t_hyd = time.perf_counter() - t0
    t0 = time.perf_counter()
    wet = (hyd['lake_id'] > 0) & ~ocean
    lake_id = np.where(wet, hyd['lake_id'], 0).astype(np.int32)
    thr = zoned_threshold(elevation, spacing, lo_m2, hi_m2)
    active = active_rivers(hyd['receiver'], hyd['order'], hyd['area_m2'], ocean, thr)
    lines = trace_lines(hyd['receiver'], hyd['area_m2'], active, shape, first, spacing)
    px = np.asarray(mesh.node_x_m, np.float64); pz = np.asarray(mesh.node_z_m, np.float64)
    if smooth:
        sx, sz, reverted = smooth_centerline(px, pz, hyd['receiver'], active)
    else:
        sx, sz, reverted = px, pz, 0
    raw, rivers0 = standard_lines(lines, sx, sz, shape, first, spacing, ocean, wet)
    rivers, tl_stats = through_lake_lines(rivers0, lake_id, first, spacing)
    t_riv = time.perf_counter() - t0
    return dict(mesh=mesh, mesh_seed=int(mesh_seed), outlets=outlets, hyd=hyd, wet=wet, lake_id=lake_id, active=active,
                raw_lines=raw, rivers=rivers, through_lake=tl_stats, smooth_reverted_nodes=int(reverted),
                timing=dict(mesh_s=t_mesh, hydrology_s=t_hyd, rivers_s=t_riv))


# ------------------------------------------------------------------ geometry metrics on vector lines
def edge_table(lines, lake_id=None, first=None, spacing=None):
    """(angle_deg in [0,180), length_m, line_index) of every polyline edge that is not a lake chord / not inside a lake."""
    ang = []; ln = []; li = []
    for k, line in enumerate(lines):
        c = np.asarray(line['points_xz_m'], np.float64)
        if len(c) < 2:
            continue
        skip = np.zeros(len(c) - 1, bool)
        for a, b in (line.get('lake_spans') or ()) if line.get('through_lake') else ():
            lo, hi = sorted((int(a), int(b))); skip[lo:max(hi, lo + 1)] = True
        if lake_id is not None:
            nz, nx = lake_id.shape
            ix = np.clip(np.rint((c[:, 0] - first[0]) / spacing).astype(int), 0, nx - 1)
            iz = np.clip(np.rint((c[:, 1] - first[1]) / spacing).astype(int), 0, nz - 1)
            w = lake_id[iz, ix] > 0
            skip |= w[:-1] | w[1:]
        d = np.diff(c, axis=0)
        keep = ~skip
        ang.append(np.degrees(np.arctan2(d[keep, 1], d[keep, 0])) % 180.0)
        ln.append(np.hypot(d[keep, 0], d[keep, 1])); li.append(np.full(int(keep.sum()), k))
    if not ang:
        return np.zeros(0), np.zeros(0), np.zeros(0, int)
    return np.concatenate(ang), np.concatenate(ln), np.concatenate(li)


def octant_fraction(angles, lengths, tol_deg=5.0):
    """Length-weighted and count fractions of edges within ``tol_deg`` of 0/45/90/135 degrees."""
    if angles.size == 0:
        return dict(length=0.0, count=0.0)
    off = np.abs(((angles + 22.5) % 45.0) - 22.5)
    near = off <= tol_deg
    return dict(length=float(lengths[near].sum() / lengths.sum()), count=float(near.mean()))


def straight_runs(points, tol_m=200.0):
    """Greedy maximal runs whose vertices all lie within ``tol_m`` of the chord first->last. Returns [(i, j, length_m)]."""
    p = np.asarray(points, np.float64); n = len(p); runs = []; i = 0
    while i < n - 1:
        j = i + 1
        while j + 1 < n:
            a, b = p[i], p[j + 1]; v = b - a; L = np.hypot(*v)
            if L == 0:
                break
            dev = np.abs(v[0] * (p[i + 1:j + 1, 1] - a[1]) - v[1] * (p[i + 1:j + 1, 0] - a[0])) / L
            if dev.max() > tol_m:
                break
            j += 1
        runs.append((i, j, float(np.hypot(*(p[j] - p[i])))))
        i = j
    return runs


# ------------------------------------------------------------------ freeze
def _memory_guard(min_available_gb):
    import psutil
    avail = psutil.virtual_memory().available / 2 ** 30
    if avail < min_available_gb:
        raise MemoryError(f'only {avail:.2f} GB available, need >= {min_available_gb} GB; nothing was started')
    return avail


def freeze_v6(v5_dir, out_name='world-960m-v6', min_available_gb=2.0, log=print):
    v5_dir = Path(v5_dir); started = time.perf_counter()
    import psutil
    avail_gb = _memory_guard(min_available_gb)
    m5 = json.loads((v5_dir / 'manifest.json').read_text(encoding='utf-8'))
    if m5['identity'] != V5_IDENTITY or m5['schema'] != 'td-world-960m-v5':
        raise ValueError('input is not the frozen td-world-960m-v5 product')
    for name in ('elevation_m', 'hydro_bed_m', 'ocean_mask', 'status', 'inland_depression_mask'):
        if file_sha(v5_dir / (name + '.npy')) != m5['files'][name + '.npy']:
            raise ValueError('v5 file hash mismatch: ' + name)
    load = lambda n: np.load(v5_dir / (n + '.npy'), allow_pickle=False)
    h = load('elevation_m'); bed0 = load('hydro_bed_m'); ocean = load('ocean_mask'); status = load('status')
    closed = load('inland_depression_mask')
    first = m5['first_sample_xz_m']; spacing = float(m5['spacing_m']); world_seed = int(m5['world_seed'])
    hy = m5['hydrology']
    depth_min_m = float(hy['depth_min_m']); area_min_m2 = float(hy['area_min_m2'])
    res = compute_v6(h, bed0, ocean, first, spacing, world_seed, None, depth_min_m, area_min_m2, log=log)
    hyd = res['hyd']; mesh = res['mesh']; wet = res['wet']; lake_id = res['lake_id']
    product = Path(out_name) if Path(out_name).is_absolute() else v5_dir.parent / out_name
    product.mkdir(parents=True, exist_ok=True)
    filled = hyd['filled'].astype(np.float32)
    water = np.where(wet, filled, np.nan).astype(np.float32)
    if not np.array_equal(status, np.where(ocean, 3, np.where(closed, 4, 5)).astype(np.uint8)):
        raise ValueError('status differs from ocean/closed masks')
    offsets = np.stack([(mesh.node_x_m - (first[0] + np.tile(np.arange(h.shape[1]), h.shape[0]) * spacing)),
                        (mesh.node_z_m - (first[1] + np.repeat(np.arange(h.shape[0]), h.shape[1]) * spacing))]
                       ).reshape(2, *h.shape).astype(np.float32)
    arrays = dict(elevation_m=h, hydro_bed_m=hyd['bed'].astype(np.float32), status=status, ocean_mask=ocean,
                  inland_depression_mask=closed, lake_id=lake_id, lake_surface_m=filled, water_surface_m=water,
                  drainage_area_m2=hyd['area_m2'].reshape(h.shape).astype(np.float32),
                  receiver=hyd['receiver'].reshape(h.shape).astype(np.int32), node_offset_m=offsets)
    for name, a in arrays.items():
        np.save(product / (name + '.npy'), a, allow_pickle=False)
    lakes = td_hydro.lake_vectors_labeled(np.where(wet, hyd['lake_id'], 0), filled, first, spacing)
    write_json(product / 'rivers.json', dict(schema='coordinate-river-segments-v1', lines=res['raw_lines']))
    (product / 'vectors').mkdir(exist_ok=True)
    write_json(product / 'vectors/rivers.json', dict(schema='rivers-v1', lines=res['rivers']))
    write_json(product / 'vectors/lakes.json', dict(schema='lakes-v1', lakes=lakes))
    layers = {}
    for name, unit, meaning in (
            ('elevation_m', 'm', m5['layers']['elevation_m']['meaning']),
            ('hydro_bed_m', 'm', 'derived hydrology bed: v5 hydro_bed_m, plus additional breach cuts along irregular-graph receivers through depressions that are shallow or small on the graph; routing only'),
            ('status', '1', '3 ocean; 4 closed below sea; 5 land'),
            ('water_surface_m', 'm', 'priority-flood surface (irregular graph) of kept lakes (deep and wide) on the breached bed; NaN dry'),
            ('drainage_area_m2', 'm2', 'contributing area on the irregular Delaunay routing graph (each node owns one 960 m cell of area), NOT discharge')):
        path = product / (name + '.npy')
        layers[name] = dict(file=path.name, sha256=file_sha(path), dtype=str(arrays[name].dtype), unit=unit, meaning=meaning, nodata=None)
    vectors = {kind: dict(file=f'vectors/{kind}.json', sha256=file_sha(product / f'vectors/{kind}.json'), schema=kind + '-v1')
               for kind in ('rivers', 'lakes')}
    tg_root = terragenesis_root()
    tg_sha = {n: file_sha(tg_root / n) for n in TG_FILES}
    here = Path(__file__).parent
    local_sha = {n: file_sha(here / n) for n in ('td_freeze_v6.py', 'td_hydro.py', 'td_pages.py', 'source.py')}
    td_source = dict(m5['td_source']); td_source['local_code_sha256'] = local_sha
    mesh_seed = res['mesh_seed']
    subseeds = {MESH_PURPOSE: str(mesh_seed)}
    ocean_cells = int(ocean.sum()); closed_cells = int(closed.sum())
    manifest = dict(schema=SCHEMA, producer='Terragenesis', algorithm_version=m5['algorithm_version'],
        lineage=list(m5['lineage']) + [m5['identity']], source_identity=m5['source_identity'], world_seed=world_seed,
        subseed_method='subseed(world_seed, purpose) = first 8 bytes (big endian) of sha256("{world_seed}:{purpose}"); the irregular mesh jitter is SplitMix64 of absolute native cell indices keyed by the subseed rivers/irregular-mesh; TD seed read from plate manifest',
        subseeds=subseeds, ready=True, routing=ROUTING,
        grid=m5['grid'], shape_zx=m5['shape_zx'], first_sample_xz_m=first, spacing_m=m5['spacing_m'], axes=m5['axes'],
        boundary=m5['boundary'], requested_domain_bounds_m=m5['requested_domain_bounds_m'], plan_identity=m5['plan_identity'],
        layers=layers, vectors=vectors,
        hydrology=dict(method='irregular-graph breach-then-lake + irregular-graph accumulation + through-lake connections',
                       routing=ROUTING, depth_min_m=depth_min_m, area_min_m2=area_min_m2, eps_drop_m=td_hydro.EPS_DROP,
                       derived_layer='hydro_bed_m', input_bed='td-world-960m-v5 hydro_bed_m (' + m5['identity'][:12] + ')',
                       mesh=dict(builder='irregular_grid.grid_mesh', spacing_m=spacing, node_jitter='central 70% of the cell',
                                 edges='Delaunay triangles with circumradius <= 2 cells, 256-cell cores with 8-cell halo',
                                 purpose=MESH_PURPOSE, seed=str(mesh_seed), nodes=int(h.size), edges_directed=int(mesh.indices.size),
                                 outlets='ocean_mask cells and the domain rim; every other node has exactly one downstream graph neighbour'),
                       terragenesis_sha256=tg_sha,
                       river_threshold=dict(rule='slope-zoned: area >= lo where 5x5 box-smoothed |grad elevation_m| >= split, else hi; plus downstream closure on irregular receivers',
                                            lo_m2=RIVER_LO_M2, hi_m2=RIVER_HI_M2, slope_split=SLOPE_SPLIT, smooth_cells=SLOPE_SMOOTH_CELLS),
                       river_geometry=dict(points='metric node positions of the routing graph (finite-volume representative positions, not terrain samples)',
                                           smoothing=dict(rule='degree-2 channel nodes move toward the midpoint of donor and receiver; heads, junctions and outlet ends fixed; no new edge crossings; equivalent of channel_centerline SmoothingRecipe, channel_centerline.build_centerline itself needs a metric-channel-plan artifact on the D8 mesh and is not used',
                                                          strength=SMOOTH_STRENGTH, max_offset_m=SMOOTH_MAX_OFFSET_M, passes=SMOOTH_PASSES,
                                                          nodes_reverted_for_crossings=res['smooth_reverted_nodes'])),
                       through_lake=dict(rule='every maximal run of >=2 consecutive river points with lake_id>0 is replaced in vectors/rivers.json by one straight chord from the entry to the exit point; flagged through_lake / lake_spans; ids, areas, topology unchanged; raw rivers.json (receiver trace) is not modified', **res['through_lake']),
                       elevation_m_modified=False,
                       area='graph receiver-tree contributing area (consistent with receiver.npy and river lines); receiver.npy holds flat node indices, -1 = outlet',
                       lake_rule='depression of the irregular graph kept as lake only if depth>=depth_min_m AND area>=area_min_m2, or closed basin whose lowest node is below sea level; others are breached along the irregular receiver path'),
        blend=m5['blend'],
        declared_generated=['Same terrain as td-world-960m-v5 (elevation_m, ocean_mask, status bit-identical)',
            'Hydrology bed: v5 bed plus extra breach cuts along irregular-graph receivers; terrain elevation_m is NOT eroded or filled',
            'Receivers, contributing area and river lines from irregular Delaunay graph routing (no D8, no 8-neighbour direction set)',
            'River vectors: metric node positions with constrained centreline smoothing; lake interiors are a single straight through-lake connection per run (flagged through_lake), not a physical channel',
            'Lake pixel-edge polygons with holes, one per kept lake id; potential level, no water balance'],
        limitations=['Graph nodes are jittered representative positions of 960 m cells, not new terrain samples; river geometry is a drawing of the routing graph, not a surveyed channel',
            'area is not discharge; no real precipitation-runoff simulation',
            'Breach cuts are 1-node cuts in a derived layer; valley widths/depths are not physical',
            'Lake surface is potential flood level of kept depressions, not permanent water. Boundary-crossing basins drain through the finite rim',
            'through_lake chords are display/topology connections; receiver.npy and drainage_area_m2.npy follow the graph path inside lakes',
            'lake polygons are raster pixel-edge outlines of the cell accounts, not of the displaced nodes'],
        statistics=dict(river_segments=len(res['rivers']), kept_lakes=len(lakes), ocean_cells=ocean_cells,
            closed_below_sea_cells=closed_cells, breach_passes=len(hyd['passes']), breach_passes_detail=hyd['passes'],
            cells_lowered_vs_v5_bed=int((arrays['hydro_bed_m'] != bed0).sum()), unresolved_depressions=hyd['unresolved_depressions'],
            river_cells=int(res['active'].sum()), through_lake=res['through_lake'],
            max_drainage_area_m2=float(hyd['area_m2'].max()),
            elevation_min_m=float(h.min()), elevation_max_m=float(h.max())),
        generation=m5['generation'], td_source=td_source,
        files={p.name: file_sha(p) for p in sorted(product.glob('*.npy'))})
    manifest['files']['rivers.json'] = file_sha(product / 'rivers.json')
    manifest['identity'] = identity(manifest)
    write_json(product / 'manifest.json', manifest)
    proc = psutil.Process()
    mi = proc.memory_info()
    write_json(product / 'runtime-stats.json', dict(
        note='run-time fields, deliberately outside manifest/identity', total_seconds=time.perf_counter() - started,
        **res['timing'], peak_working_set_mb=getattr(mi, 'peak_wset', 0) / 2 ** 20,
        available_gb_at_start=avail_gb, python=sys.version.split()[0], numpy=np.__version__,
        scipy=__import__('scipy').__version__, numba=__import__('numba').__version__))
    print('FROZEN-V6 ' + manifest['identity'], flush=True)
    return product, manifest


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='freeze td-world-960m-v6 from the frozen v5 product (run with the Terragenesis venv: needs numba)')
    ap.add_argument('--v5', default='artifacts/td-world/world-960m-v5')
    ap.add_argument('--out', default='world-960m-v6')
    ap.add_argument('--min-available-gb', type=float, default=2.0)
    a = ap.parse_args()
    freeze_v6(a.v5, a.out, a.min_available_gb)
