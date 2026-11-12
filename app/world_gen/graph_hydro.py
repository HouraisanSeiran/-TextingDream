"""Irregular-graph hydrology for the fast world layer (no D8, no 8-neighbour direction set).

Extracted from ``app/world_relief/td_freeze_v6.py`` / ``td_hydro.py`` so the fast world layer does not import any D8 module.
Routing and accumulation are Terragenesis ``terrain_pipeline.drainage`` (``grid_mesh``, ``route_graph``,
``accumulate_graph``), imported read-only. Needs numba: run with the Terragenesis venv.

Coarse-scale changes against v6: the breach-then-lake loop has a small ``max_passes`` (default 4: later passes only lower a few
shallow pits), thresholds are given by the caller in m2 and scale with the grid spacing.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse import csgraph

EPS_DROP = 0.01          # m of fall per breached node
WET_TOL = 1e-4           # m, filled-minus-bed tolerance for depression membership
SMOOTH_STRENGTH = 0.25
SMOOTH_MAX_OFFSET_FRAC = 0.2     # of the grid spacing (v6: 200 m at 960 m)
SMOOTH_PASSES = 4
TG_FILES = ('terrain_pipeline/drainage.py',)


def terragenesis_root():
    return Path(__file__).resolve().parents[3] / '山川形意Terragenesis'


def load_terragenesis(root=None):
    root = Path(root) if root else terragenesis_root()
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from terrain_pipeline import drainage
    return drainage, drainage


def build_graph(shape, first, spacing, mesh_seed):
    _, grid = load_terragenesis()
    return grid.grid_mesh(tuple(int(v) for v in shape), x0_m=float(first[0]), z0_m=float(first[1]), dx_m=float(spacing),
                          world_seed=int(mesh_seed))


# ------------------------------------------------------------------ depressions / breaching
def graph_depression_labels(mesh, bed, filled, ocean):
    n = bed.size
    wet = (filled - bed > WET_TOL) & ~ocean
    src = np.repeat(np.arange(n, dtype=np.int32), np.diff(mesh.indptr))
    dst = mesh.indices
    both = wet[src] & wet[dst] & (filled[src] == filled[dst])
    g = sparse.coo_matrix((np.ones(int(both.sum()), np.int8), (src[both], dst[both])), shape=(n, n))
    _, comp = csgraph.connected_components(g, directed=False)
    labels = np.zeros(n, np.int64)
    _, inverse = np.unique(comp[wet], return_inverse=True)
    labels[wet] = inverse + 1
    return labels, wet


def unit_stats(bed, filled, labels):
    flat = labels.ravel()
    wet_idx = np.flatnonzero(flat)
    if wet_idx.size == 0:
        e = np.zeros(0)
        return dict(count=e.astype(np.int64), level=e, depth=e, pit=e.astype(np.int64))
    lab = flat[wet_idx]
    bed_flat = bed.ravel()
    order = np.lexsort((bed_flat[wet_idx], lab))
    sorted_lab = lab[order]
    first = np.r_[0, np.flatnonzero(np.diff(sorted_lab)) + 1]
    pit = wet_idx[order[first]]
    count = np.bincount(lab - 1)
    level = filled.ravel()[pit]
    return dict(count=count, level=level, depth=level - bed_flat[pit], pit=pit)


def classify(stats, bed, spacing, depth_min_m, area_min_m2):
    """keep = deep AND wide, or a closed basin whose lowest node is below sea level."""
    area = stats['count'] * float(spacing) ** 2
    below_sea = bed.ravel()[stats['pit']] < 0 if stats['pit'].size else np.zeros(0, bool)
    return ((stats['depth'] >= depth_min_m) & (area >= area_min_m2)) | below_sea


def breach_graph(bed, receiver, pits, ocean):
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
            if base[nxt] < prof - EPS_DROP:
                break
            prof = max(prof - EPS_DROP, floor)
            if new[nxt] > prof:
                new[nxt] = prof; cut += 1
            cur = nxt
    return new.reshape(np.shape(bed)), cut


def lake_filter(keep, labels, receiver, order, spacing, drain, forbid=None, min_catch_m2=0.0):
    """v4 lake rules on top of classify: a depression touching a `forbid` node (ridge envelope) is not a lake, and a lake
    needs a contributing area of at least min_catch_m2 at its outlet. Rejected depressions are breached like shallow ones."""
    info = dict(rejected_on_ridge=0, rejected_small_catchment=0)
    if keep.size == 0 or (forbid is None and min_catch_m2 <= 0):
        return keep, info
    flat = np.asarray(labels).ravel()
    if forbid is not None:
        hit = np.bincount(flat[np.asarray(forbid).ravel() & (flat > 0)], minlength=keep.size + 1)[1:keep.size + 1] > 0
        info['rejected_on_ridge'] = int((keep & hit).sum())
        keep = keep & ~hit
    if min_catch_m2 > 0:
        area = np.asarray(drain.accumulate_graph(np.asarray(receiver, np.int64), np.asarray(order, np.int64),
                                                 np.full(flat.size, spacing * spacing))).ravel()
        catch = np.zeros(keep.size + 1)
        np.maximum.at(catch, flat, area)
        small = catch[1:] < float(min_catch_m2)
        info['rejected_small_catchment'] = int((keep & small).sum())
        keep = keep & ~small
    return keep, info


def hydrology(bed0, ocean, mesh, outlets, depth_min_m, area_min_m2, max_passes=4, log=None, forbid=None, min_catch_m2=0.0):
    """Breach-then-lake on the irregular graph. Returns dict(bed, filled, receiver, order, area_m2, lake_id, ...).

    forbid / min_catch_m2 (v4, default off = unchanged behaviour): see lake_filter."""
    drain, _ = load_terragenesis()
    spacing = float(mesh.spacing_m)
    bed = np.asarray(bed0, np.float64).copy()
    oc = np.asarray(ocean, bool).ravel()
    passes = []; route = None
    for k in range(max_passes):
        route = drain.route_graph(bed, outlets, mesh)
        filled = np.asarray(route.filled).ravel()
        labels, _ = graph_depression_labels(mesh, bed.ravel(), filled, oc)
        st = unit_stats(bed.ravel(), filled, labels)
        keep = classify(st, bed.ravel(), spacing, depth_min_m, area_min_m2)
        keep, finfo = lake_filter(keep, labels, route.receiver, route.order, spacing, drain, forbid, min_catch_m2)
        failing = np.flatnonzero(~keep)
        passes.append(dict(pass_index=k, depressions=int(keep.size), failing=int(failing.size), kept=int(keep.sum()), **finfo))
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
    st = unit_stats(bed.ravel(), filled, labels)
    keep = classify(st, bed.ravel(), spacing, depth_min_m, area_min_m2)
    keep, _ = lake_filter(keep, labels, route.receiver, route.order, spacing, drain, forbid, min_catch_m2)
    remap = np.zeros(keep.size + 1, np.int64)
    remap[1:][keep] = np.arange(1, int(keep.sum()) + 1)
    lake_id = remap[labels]
    receiver = np.array(route.receiver, np.int64)
    order = np.array(route.order, np.int64)
    area = drain.accumulate_graph(receiver, order, np.full(receiver.size, spacing * spacing))
    return dict(bed=bed, filled=filled.reshape(bed.shape), receiver=receiver, order=order, area_m2=np.asarray(area).ravel(),
                lake_id=lake_id.astype(np.int32).reshape(bed.shape), passes=passes,
                unresolved_depressions=int((~keep).sum()), kept_lakes=int(keep.sum()))


def route_area(bed, outlets, mesh):
    """One routing + accumulation (used by the optional coarse erosion). Returns (filled, receiver, order, area_m2)."""
    drain, _ = load_terragenesis()
    route = drain.route_graph(bed, outlets, mesh)
    receiver = np.asarray(route.receiver, np.int64)
    order = np.asarray(route.order, np.int64)
    sp = float(mesh.spacing_m)
    area = np.asarray(drain.accumulate_graph(receiver, order, np.full(receiver.size, sp * sp))).ravel()
    return np.asarray(route.filled).ravel(), receiver, order, area


# ------------------------------------------------------------------ river extraction
def zoned_threshold(elevation, spacing, lo, hi, split=0.015, smooth=3):
    gz, gx = np.gradient(np.asarray(elevation, np.float64), float(spacing))
    sm = ndimage.uniform_filter(np.hypot(gx, gz), smooth)
    return np.where(sm >= split, lo, hi)


def active_rivers(receiver, order, area, ocean, threshold):
    rec = np.asarray(receiver, np.int64).ravel(); oc = np.asarray(ocean, bool).ravel()
    active = ((np.asarray(area).ravel() >= np.asarray(threshold).ravel()) & ~oc)
    act = active.tolist(); r = rec.tolist(); o = oc.tolist()
    for cur in np.asarray(order)[::-1].tolist():
        if act[cur]:
            nxt = r[cur]
            if nxt >= 0 and not o[nxt]:
                act[nxt] = True
    return np.asarray(act, bool)


def _stable_id(i, first, spacing, nx):
    x = first[0] + (int(i) % nx) * spacing; z = first[1] + (int(i) // nx) * spacing
    return 'r-' + hashlib.sha256(f'{x:.3f},{z:.3f}'.encode()).hexdigest()[:20]


def trace_lines(receiver, area, active, shape, first, spacing):
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


def _crossing_nodes(x, z, ea, eb, bucket):
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


def smooth_centerline(px, pz, receiver, active, spacing, strength=SMOOTH_STRENGTH, passes=SMOOTH_PASSES):
    """Move only degree-2 channel nodes toward the donor/receiver midpoint; topology unchanged, crossings reverted."""
    max_offset_m = SMOOTH_MAX_OFFSET_FRAC * float(spacing)
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
        bad = _crossing_nodes(x, z, ea, eb, 2.0 * spacing)
        if not bad:
            break
        idx = np.fromiter(bad, np.int64)
        x[idx] = px[idx]; z[idx] = pz[idx]; reverted += idx.size
    else:
        x[:] = px; z[:] = pz
    return x, z, reverted


def standard_lines(lines, px, pz, shape, ocean, wet):
    """Raw (receiver-trace) lines and rivers-v1 lines with node positions as coordinates."""
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
    """Each maximal run of >=2 consecutive points in a kept lake becomes one chord (display/topology connection)."""
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


def _dry_runs(dry):
    m = np.concatenate([[0], np.asarray(dry, np.int8), [0]])
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def cut_lines_at_lakes(lines, px, pz, area, shape, ocean, lake_flat):
    """rivers-v1 lines cut at the lake shore (v4): every maximal run of non-lake nodes of a receiver-trace line becomes one
    piece; a piece next to a lake ends (or starts) at the midpoint between its last dry node and the first lake node, so no
    river is drawn over a lake surface and no through-lake chord exists. Pieces flowing into a lake carry to_lake (lake index),
    pieces leaving one carry from_lake. The first piece keeps the line id when the line starts dry, other pieces get
    '<id>~<k>'; downstream ids that no longer exist become None, upstream ids are rebuilt. Returns (rivers, lake_links)."""
    nz, nx = shape
    oc = np.asarray(ocean, bool).ravel(); lk = np.asarray(lake_flat).ravel(); area = np.asarray(area).ravel()
    out = []
    for line in lines:
        nodes = list(line['nodes'])
        wet = lk[nodes] > 0
        n = len(nodes)
        for k, (a, b) in enumerate(_dry_runs(~wet)):
            seg = nodes[a:b]
            coords = [[float(px[i]), float(pz[i])] for i in seg]
            from_lake = to_lake = None
            if a > 0:
                j, i = nodes[a - 1], nodes[a]
                coords.insert(0, [float(0.5 * (px[i] + px[j])), float(0.5 * (pz[i] + pz[j]))]); from_lake = int(lk[j])
            if b < n:
                i, j = nodes[b - 1], nodes[b]
                coords.append([float(0.5 * (px[i] + px[j])), float(0.5 * (pz[i] + pz[j]))]); to_lake = int(lk[j])
            if len(coords) < 2:
                continue
            e = seg[-1]; iz, ix = divmod(int(e), nx)
            if to_lake is not None:
                outlet = 'lake'
            else:
                outlet = 'ocean' if oc[e] else 'edge' if ix in (0, nx - 1) or iz in (0, nz - 1) else 'closed'
            out.append(dict(id=line['id'] if (k == 0 and a == 0) else '%s~%d' % (line['id'], k), points_xz_m=coords,
                            downstream_id=line['downstream_id'] if b == n else None, upstream_ids=[],
                            drainage_area_m2=float(area[seg[-1]]), head_drainage_area_m2=float(area[seg[0]]), outlet=outlet,
                            from_lake=from_lake, to_lake=to_lake, through_lake=False, lake_spans=[]))
    by_id = {v['id']: v for v in out}
    for v in out:
        if v['downstream_id'] is not None and v['downstream_id'] not in by_id:
            v['downstream_id'] = None
    for v in out:
        if v['downstream_id'] is not None:
            by_id[v['downstream_id']]['upstream_ids'].append(v['id'])
    for v in out:
        v['upstream_ids'].sort()
    for v in out:                                   # final outlet of every chain
        cur = v; seen = set()
        while cur['downstream_id'] is not None:
            if cur['id'] in seen:
                raise ValueError('cyclic river')
            seen.add(cur['id']); cur = by_id[cur['downstream_id']]
        v['outlet'] = cur['outlet']
    links = {int(i): dict(inflow=[], outflow=[]) for i in np.unique(lk[lk > 0]).tolist()}
    for v in out:
        if v['to_lake'] is not None:
            links.setdefault(v['to_lake'], dict(inflow=[], outflow=[]))['inflow'].append(v['id'])
        if v['from_lake'] is not None:
            links.setdefault(v['from_lake'], dict(inflow=[], outflow=[]))['outflow'].append(v['id'])
    return sorted(out, key=lambda v: v['id']), links


def river_lake_overlap(rivers, lake_id, first, spacing, samples=8, skip_chords=False):
    """Length (m) of drawn river line lying over kept lake cells: every segment is sampled at `samples` interior points
    (nearest cell). skip_chords=True leaves out through-lake chord edges (lake_spans), i.e. what the atlas draws."""
    nz, nx = lake_id.shape
    total = 0.0; over = 0.0; lines_over = 0
    t = (np.arange(samples) + 0.5) / samples
    for line in rivers:
        c = np.asarray(line['points_xz_m'], np.float64)
        if len(c) < 2:
            continue
        a, b = c[:-1], c[1:]
        seglen = np.hypot(*(b - a).T)
        use = np.ones(len(seglen), bool)
        if skip_chords and line.get('through_lake'):
            for s0, s1 in line.get('lake_spans') or ():
                lo, hi = sorted((int(s0), int(s1)))
                use[lo:hi] = False
        q = a[:, None, :] + (b - a)[:, None, :] * t[None, :, None]
        ix = np.clip(np.rint((q[..., 0] - first[0]) / spacing).astype(int), 0, nx - 1)
        iz = np.clip(np.rint((q[..., 1] - first[1]) / spacing).astype(int), 0, nz - 1)
        frac = (lake_id[iz, ix] > 0).mean(axis=1)
        o = float((frac * seglen)[use].sum())
        total += float(seglen[use].sum()); over += o; lines_over += o > 0
    return dict(river_length_km=total / 1e3, over_lake_km=over / 1e3, lines_over_lake=int(lines_over), samples_per_segment=samples)


# ------------------------------------------------------------------ lake polygons
def _rings(mask):
    """Trace directed exposed pixel edges; four-neighbour components keep diagonal lakes apart."""
    nz, nx = mask.shape; edges = {}

    def edge(a, b):
        edges.setdefault(a, []).append(b)
    for z, x in np.argwhere(mask):
        z = int(z); x = int(x)
        if z == 0 or not mask[z - 1, x]: edge((x, z), (x + 1, z))
        if x == nx - 1 or not mask[z, x + 1]: edge((x + 1, z), (x + 1, z + 1))
        if z == nz - 1 or not mask[z + 1, x]: edge((x + 1, z + 1), (x, z + 1))
        if x == 0 or not mask[z, x - 1]: edge((x, z + 1), (x, z))
    rings = []
    while edges:
        start = min(edges); current = start; previous = (start[0] - 1, start[1]); ring = [start]
        while True:
            candidates = edges[current]
            incoming = (current[0] - previous[0], current[1] - previous[1])

            def priority(p):
                v = (p[0] - current[0], p[1] - current[1])
                cross = incoming[0] * v[1] - incoming[1] * v[0]
                dot = incoming[0] * v[0] + incoming[1] * v[1]
                return (2 if cross > 0 else 1 if dot > 0 else 0 if cross < 0 else -1, p)
            nxt = max(candidates, key=priority)
            candidates.remove(nxt)
            if not candidates:
                del edges[current]
            previous, current = current, nxt; ring.append(current)
            if current == start:
                break
            if len(ring) > 4 * mask.size + 1:
                raise ValueError('lake outline did not close')
        rings.append(ring)
    return rings


def lake_vectors_labeled(lake_id, filled, first, spacing):
    """Pixel-edge lake polygons, one per kept lake id (potential priority-flood level)."""
    lakes = []

    def signed_area(r):
        return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:])) / 2
    for label, bounds in enumerate(ndimage.find_objects(lake_id), 1):
        if bounds is None:
            continue
        lake_mask = lake_id[bounds] == label
        parts, nparts = ndimage.label(lake_mask)
        for part in range(1, nparts + 1):
            mask = parts == part
            rings = _rings(mask)
            outer = [r for r in rings if signed_area(r) > 0]
            holes = [r for r in rings if signed_area(r) < 0]
            start = int(np.flatnonzero(mask)[0]); row, col = divmod(start, mask.shape[1])

            def coords(r):
                return [[float(first[0] + (x + bounds[1].start - .5) * spacing),
                         float(first[1] + (z + bounds[0].start - .5) * spacing)] for x, z in r]
            surfaces = filled[bounds][mask]
            for k, r in enumerate(outer):
                stable = hashlib.sha256(f'{first}:{spacing}:{bounds[0].start + row}:{bounds[1].start + col}:{k}'.encode()).hexdigest()[:20]
                lakes.append(dict(id='lake-' + stable, lake_index=int(label), ring_xz_m=coords(r), holes_xz_m=[coords(h) for h in holes],
                                  surface_m=float(surfaces.max()), surface_range_m=[float(surfaces.min()), float(surfaces.max())],
                                  area_m2=int(mask.sum()) * spacing ** 2,
                                  meaning='potential priority-flood lake kept after breaching (deep and wide), not permanent water or balanced lake'))
    return sorted(lakes, key=lambda v: v['id'])
