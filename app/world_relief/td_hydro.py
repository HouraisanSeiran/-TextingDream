"""Breach-then-lake hydrology bed for the 960 m TD world (derived layer only; elevation_m is never modified).

Rule: every priority-flood depression (a 4-connected set of cells sharing one filled level above the bed) whose depth
(spill level - lowest bed) is below ``depth_min_m`` OR whose area is below ``area_min_m2`` is *breached*: a channel
is cut from its lowest cell along the flood-parent / steepest receiver path, each cell lowered just enough
(``EPS_DROP`` per cell) to flow downhill, until the path meets a cell that is already lower.  Only depressions
that are both deep and wide stay lakes (surface = spill level).  Breaching is repeated (routing is recomputed) until
no failing depression is left, because opening one basin can merge it into a lower lake's surface.
Closed basins whose lowest cell is below sea level are kept as lakes (never carved toward the ocean).
"""
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

from . import drainage

EPS_DROP = 0.01          # m of fall per breached cell (keeps channels strictly descending)
WET_TOL = 1e-4           # m, filled-minus-bed tolerance for "depression" membership


def depression_units(bed, filled, ocean):
    """Label connected sets of equal filled level above the bed. Returns (labels[z,x] 0=none, wet bool)."""
    nz, nx = bed.shape
    wet = (filled - bed > WET_TOL) & ~ocean
    ids = np.arange(bed.size).reshape(nz, nx)
    src, dst = [], []
    # 8-connected: D8 routing crosses diagonals on a flat, so a diagonal pair at one level is ONE depression
    for sl_a, sl_b in (((slice(None), slice(0, nx - 1)), (slice(None), slice(1, nx))),
                       ((slice(0, nz - 1), slice(None)), (slice(1, nz), slice(None))),
                       ((slice(0, nz - 1), slice(0, nx - 1)), (slice(1, nz), slice(1, nx))),
                       ((slice(0, nz - 1), slice(1, nx)), (slice(1, nz), slice(0, nx - 1)))):
        both = wet[sl_a] & wet[sl_b] & (filled[sl_a] == filled[sl_b])
        src.append(ids[sl_a][both]); dst.append(ids[sl_b][both])
    src = np.concatenate(src); dst = np.concatenate(dst)
    graph = sparse.coo_matrix((np.ones(src.size, np.int8), (src, dst)), shape=(bed.size, bed.size))
    _, comp = csgraph.connected_components(graph, directed=False)
    labels = np.zeros(bed.size, np.int64)
    wet_flat = wet.ravel()
    _, inverse = np.unique(comp[wet_flat], return_inverse=True)
    labels[wet_flat] = inverse + 1
    return labels.reshape(nz, nx), wet


def unit_stats(bed, filled, labels):
    """Per-unit count, level, depth, pit (flat index of lowest bed cell). Arrays indexed by label-1."""
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
    depth = level - bed_flat[pit]
    return dict(count=count, level=level, depth=depth, pit=pit)


def classify(stats, bed, spacing, depth_min_m, area_min_m2):
    """keep = deep AND wide, or a closed basin whose lowest cell is below sea level."""
    area = stats['count'] * float(spacing) ** 2
    below_sea = bed.ravel()[stats['pit']] < 0 if stats['pit'].size else np.zeros(0, bool)
    keep = ((stats['depth'] >= depth_min_m) & (area >= area_min_m2)) | below_sea
    return keep


def breach(bed, receiver, pits, ocean):
    """Return a copy of ``bed`` with a descending channel cut from every pit along ``receiver``."""
    base = bed.ravel()
    new = base.copy()
    rec = receiver.ravel()
    ocean_flat = ocean.ravel()
    cut = 0
    for p in pits:
        cur = int(p); prof = float(base[cur]); floor = 0.0 if prof >= 0 else -np.inf
        for _ in range(base.size):
            nxt = int(rec[cur])
            if nxt == cur or ocean_flat[nxt]:
                break
            if base[nxt] < prof - EPS_DROP:
                break
            prof = max(prof - EPS_DROP, floor)
            if new[nxt] > prof:
                new[nxt] = prof; cut += 1
            cur = nxt
    return new.reshape(bed.shape), cut


def breach_and_lakes(elevation, ocean, spacing=960, depth_min_m=30.0, area_min_m2=50e6, max_passes=16, log=None,
                     router=None):
    """Derive the hydrology bed. Returns dict(bed, filled, flow, labels, lake_wet, passes, unresolved_cells...)."""
    router = router or drainage.route      # v3 passes td_flats.route_flats (convergent flats, curved breach paths)
    original = np.asarray(elevation, np.float64)
    bed = original.copy()
    passes = []
    for k in range(max_passes):
        flow = router(bed, ocean, spacing, area_mode='d8')
        filled = flow['filled_m']
        labels, wet = depression_units(bed, filled, ocean)
        st = unit_stats(bed, filled, labels)
        keep = classify(st, bed, spacing, depth_min_m, area_min_m2)
        failing = np.flatnonzero(~keep)
        passes.append(dict(pass_index=k, depressions=int(keep.size), failing=int(failing.size), kept=int(keep.sum())))
        if log:
            log(passes[-1])
        if failing.size == 0:
            break
        bed, cut = breach(bed, flow['receiver'], st['pit'][failing], ocean)
        passes[-1]['cells_lowered'] = int(cut)
        if cut == 0:
            break
    flow = router(bed, ocean, spacing, area_mode='mfd')
    filled = flow['filled_m']
    labels, wet = depression_units(bed, filled, ocean)
    st = unit_stats(bed, filled, labels)
    keep = classify(st, bed, spacing, depth_min_m, area_min_m2)
    # contiguous ids 1..K for kept lakes only
    remap = np.zeros(keep.size + 1, np.int64)
    remap[1:][keep] = np.arange(1, int(keep.sum()) + 1)
    lake_id = remap[labels]
    lake_wet = lake_id > 0
    return dict(bed=bed, filled=filled, flow=flow, lake_id=lake_id.astype(np.int32), lake_wet=lake_wet,
                passes=passes, unresolved_depression_cells=int((wet & ~lake_wet).sum()),
                unresolved_depressions=int((~keep).sum()), cells_lowered=int((bed != original).sum()),
                depth_min_m=depth_min_m, area_min_m2=area_min_m2)


def lake_vectors_labeled(lake_id, filled, first, spacing):
    """Pixel-edge lake polygons, one per kept lake id (cascading lakes at different levels stay separate)."""
    import hashlib
    from scipy import ndimage
    from .td_freeze import _rings
    lakes = []

    def signed_area(r):
        return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:])) / 2
    for label, bounds in enumerate(ndimage.find_objects(lake_id), 1):
        if bounds is None:
            continue
        lake_mask = lake_id[bounds] == label
        # an 8-connected lake can touch diagonally: emit one polygon per 4-connected part, each with its own holes/area
        parts, nparts = ndimage.label(lake_mask)  # default structure = 4-connected
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
