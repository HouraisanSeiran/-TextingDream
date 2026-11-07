"""Convergent flat-area D8 routing (Barnes, Lehman & Mulla 2014 "flats" gradient) for the derived hydrology layer.

``drainage.route`` sends every cell of a filled flat to its flood parent, which on a flat is a breadth-first tree from the
spill cells: straight, mutually parallel one-cell lines. Here each flat (a connected set of cells sharing one filled level,
8-connected) gets an integer potential ``v = 2 * towards + (maxaway - away)``:

* ``towards`` = BFS distance (inside the flat) to the nearest *draining* cell (a cell with a strictly lower neighbour or a
  neighbouring ocean/rim cell of equal level),
* ``away``    = BFS distance to the nearest cell that touches strictly higher ground.

Water runs to the lowest-``v`` neighbour inside the flat: towards the outlet (weight 2) and away from the high ground
(weight 1), so flows concentrate in the flat's centre line and merge instead of running side by side. Along a shortest path
to a draining cell ``towards`` falls by 1 and ``away`` changes by at most 1, hence ``v`` falls strictly: no cycles and every
flat cell reaches an outlet. Cells that already have a strictly lower neighbour keep the steepest-descent receiver of
``drainage.route``. Only receivers/areas of the derived layer change; the elevation array is never touched.
"""
from __future__ import annotations

import heapq
from collections import deque

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse import csgraph

from . import drainage

NEIGHBORS = drainage.NEIGHBORS


def _shifted(a, dz, dx, fill):
    """b[z, x] = a[z + dz, x + dx] (``fill`` outside)."""
    nz, nx = a.shape
    out = np.full(a.shape, fill, a.dtype)
    zs = slice(max(0, dz), nz + min(0, dz)); xs = slice(max(0, dx), nx + min(0, dx))
    zd = slice(max(0, -dz), nz + min(0, -dz)); xd = slice(max(0, -dx), nx + min(0, -dx))
    out[zd, xd] = a[zs, xs]
    return out


MEANDER_OCTAVES = ((14400.0, 0.4), (5760.0, 0.35), (2880.0, 0.25))   # (wavelength m, weight); weights sum to 1 so the noise stays in [-1, 1]
MEANDER_AMP = 0.85                               # relative edge-cost modulation: cost = base * (1 + AMP * noise)
MEANDER_ORTHO_COST = 64                         # integer cost of an orthogonal step before modulation (diagonal: x sqrt 2)
MEANDER_AWAY_WEIGHT = 6                          # weight of the away-from-high-ground term in the perturbed potential


def meander_noise(shape, first_xz, spacing, world_seed, octaves=MEANDER_OCTAVES):
    """Smooth coordinate-addressed noise in [-1, 1] (flat, C order) used to modulate the step cost inside flats.

    Each octave uses its own stable sub-seed ``subseed(world_seed, 'flats/meander/<wavelength>m')`` and absolute coordinates, so
    the value of a cell never depends on the window, the query order or the number of cells evaluated.
    """
    from .source import subseed, spatial_noise
    total = np.zeros(shape, np.float64)
    for wavelength, weight in octaves:
        seed = subseed(world_seed, 'flats/meander/%dm' % int(wavelength))
        total += weight * spatial_noise(shape, first_xz, spacing, seed, float(wavelength))
    return np.clip(total, -1.0, 1.0).ravel()


def _meander_step_costs(amp=MEANDER_AMP, ortho=MEANDER_ORTHO_COST):
    """Integer lower bounds of the modulated step costs (orthogonal, diagonal)."""
    return int(np.floor(ortho * (1 - amp))), int(np.floor(ortho * np.sqrt(2.0) * (1 - amp)))


def resolve_flats(filled, receiver, rank, terminal, noise=None, amp=MEANDER_AMP, boost=None):
    """Return (receiver', vkey, stats). ``receiver``/``rank`` are flat int arrays from ``drainage.route``.

    ``noise`` = flat array in [-1, 1] from :func:`meander_noise`. With it the ``towards`` term is not the 8-neighbour hop count
    but a Dijkstra distance with integer step costs ``round(base * (1 + amp * mean(noise_i, noise_j)))`` and the potential is
    ``D + MEANDER_AWAY_WEIGHT * (maxaway - away)``. Every step cost is at least ``floor(base * (1 - amp))`` which exceeds the
    away weight (checked below), so along the Dijkstra predecessor the potential still falls strictly: no cycle and every flat
    cell reaches an outlet. Without ``noise`` the original ``2 * towards + (maxaway - away)`` potential is used unchanged.

    ``boost`` (optional, only with ``noise``) = ``dict(near=bool flat array, min_cells=int, amp=float, ortho=int)``: flat blocks
    (connected sets) with at least ``min_cells`` cells that contain a ``near`` cell use ``ortho``/``amp`` instead of the global
    values for their step costs (all other blocks are unchanged). The strict-descent bound ``floor(ortho * (1 - amp)) > away weight``
    is checked for the boosted values too.
    """
    f = np.asarray(filled, np.float64)
    nz, nx = f.shape
    n = f.size
    lower = np.zeros(f.shape, bool); higher = np.zeros(f.shape, bool)
    for dz, dx in NEIGHBORS:
        nf = _shifted(f, dz, dx, np.nan)
        nt = _shifted(terminal, dz, dx, False)
        valid = ~np.isnan(nf)
        lower |= valid & ((nf < f) | (nt & (nf <= f)))
        higher |= valid & ~nt & (nf > f)
    candidate = ~terminal & ~lower
    adj_candidate = np.zeros(f.shape, bool)
    for dz, dx in NEIGHBORS:
        nf = _shifted(f, dz, dx, np.nan)
        nc = _shifted(candidate, dz, dx, False)
        adj_candidate |= nc & (nf == f)
    member = candidate | (lower & ~terminal & adj_candidate)
    ids = np.arange(n).reshape(nz, nx)
    src, dst = [], []
    for sa, sb in (((slice(None), slice(0, nx - 1)), (slice(None), slice(1, nx))),
                   ((slice(0, nz - 1), slice(None)), (slice(1, nz), slice(None))),
                   ((slice(0, nz - 1), slice(0, nx - 1)), (slice(1, nz), slice(1, nx))),
                   ((slice(0, nz - 1), slice(1, nx)), (slice(1, nz), slice(0, nx - 1)))):
        both = member[sa] & member[sb] & (f[sa] == f[sb])
        src.append(ids[sa][both]); dst.append(ids[sb][both])
    src = np.concatenate(src); dst = np.concatenate(dst)
    graph = sparse.coo_matrix((np.ones(src.size, np.int8), (src, dst)), shape=(n, n))
    ncomp, comp = csgraph.connected_components(graph, directed=False)
    mem_flat = np.flatnonzero(member.ravel())
    drain_flat = member.ravel() & lower.ravel()
    high_flat = member.ravel() & higher.ravel()
    ff = f.ravel()
    mem_set = member.ravel()

    def neighbours(i):
        z, x = divmod(i, nx)
        for dz, dx in NEIGHBORS:
            zz, xx = z + dz, x + dx
            if 0 <= zz < nz and 0 <= xx < nx:
                j = zz * nx + xx
                if mem_set[j] and ff[j] == ff[i]:
                    yield j

    towards = {}
    queue = deque()
    if noise is None:
        for i in np.flatnonzero(drain_flat).tolist():
            towards[i] = 0; queue.append(i)
        while queue:
            i = queue.popleft(); d = towards[i] + 1
            for j in neighbours(i):
                if j not in towards:
                    towards[j] = d; queue.append(j)
    else:
        lo_orth, lo_diag = _meander_step_costs(amp)
        if min(lo_orth, lo_diag) <= MEANDER_AWAY_WEIGHT:
            raise ValueError('meander step cost must exceed the away weight')
        boosted = None
        if boost is not None:
            if int(np.floor(boost['ortho'] * (1 - boost['amp']))) <= MEANDER_AWAY_WEIGHT:
                raise ValueError('boosted meander step cost must exceed the away weight')
            near = np.asarray(boost['near'], bool).ravel()
            sizes = np.bincount(comp[mem_flat], minlength=ncomp)
            has_near = np.bincount(comp[mem_flat], weights=near[mem_flat].astype(np.float64), minlength=ncomp) > 0
            boosted = (sizes >= int(boost['min_cells'])) & has_near
        heap = []
        for i in np.flatnonzero(drain_flat).tolist():
            towards[i] = 0; heap.append((0, i))
        heapq.heapify(heap)
        done = set()
        while heap:
            d, i = heapq.heappop(heap)
            if i in done:
                continue
            done.add(i)
            zi, xi = divmod(i, nx)
            for j in neighbours(i):
                if j in done:
                    continue
                zj, xj = divmod(j, nx)
                if boosted is not None and boosted[comp[i]]:
                    o_cost, a_cost = boost['ortho'], float(boost['amp'])
                else:
                    o_cost, a_cost = MEANDER_ORTHO_COST, amp
                base = o_cost * (1.4142135623730951 if (zi != zj and xi != xj) else 1.0)
                c = int(round(base * (1.0 + a_cost * 0.5 * (float(noise[i]) + float(noise[j])))))
                nd = d + c
                if nd < towards.get(j, 1 << 60):
                    towards[j] = nd; heapq.heappush(heap, (nd, j))
    away = {}
    for i in np.flatnonzero(high_flat).tolist():
        away[i] = 0; queue.append(i)
    while queue:
        i = queue.popleft(); d = away[i] + 1
        for j in neighbours(i):
            if j not in away:
                away[j] = d; queue.append(j)
    maxaway = {}
    for i, a in away.items():
        c = int(comp[i])
        if a > maxaway.get(c, 0):
            maxaway[c] = a
    v = {}
    for i in mem_flat.tolist():
        if i in towards:
            c = int(comp[i])
            if noise is None:
                v[i] = 2 * towards[i] + (maxaway.get(c, 0) - away.get(i, 0))
            else:
                v[i] = towards[i] + MEANDER_AWAY_WEIGHT * (maxaway.get(c, 0) - away.get(i, 0))
    new = receiver.copy()
    no_lower = 0
    changed = 0
    # draining cells (strictly lower neighbour, or equal-level ocean/rim neighbour) must step straight out of the flat
    term_flat = terminal.ravel()
    for i in np.flatnonzero((lower & ~terminal).ravel()).tolist():
        r = int(new[i])
        if ff[r] != ff[i] or term_flat[r]:
            continue
        z, x = divmod(i, nx)
        best = None; key = None
        for dz, dx in NEIGHBORS:
            zz, xx = z + dz, x + dx
            if 0 <= zz < nz and 0 <= xx < nx:
                j = zz * nx + xx
                if ff[j] < ff[i] or (term_flat[j] and ff[j] <= ff[i]):
                    k = (ff[j], 0 if term_flat[j] else 1, j)
                    if key is None or k < key:
                        best, key = j, k
        if best is not None:
            new[i] = best; changed += 1
    for i in np.flatnonzero(candidate.ravel()).tolist():
        if i not in v:
            continue
        best = None; bv = v[i]
        for j in neighbours(i):
            vj = v.get(j)
            if vj is not None and (vj < bv or (vj == bv and best is not None and j < best and vj < v[i])):
                best, bv = j, vj
        if best is not None and bv < v[i]:
            new[i] = best; changed += 1
        else:
            no_lower += 1
    vkey = np.zeros(n, np.int64)
    for i, val in v.items():
        vkey[i] = val
    stats = dict(flat_cells=int(candidate.sum()), flat_member_cells=int(member.sum()), receivers_changed=int(changed),
                 unresolved_cells=int(sum(1 for i in np.flatnonzero(candidate.ravel()).tolist() if i not in v)),
                 no_lower_neighbour_cells=int(no_lower))
    return new, vkey, stats


def route_flats(elevation, ocean, spacing, area_mode='d8', meander=None):
    """Drop-in for ``drainage.route`` returning a single-receiver D8 tree whose flats drain convergently.

    ``area_mode`` is accepted for signature compatibility; the contributing area is always the D8 (receiver-tree) area so it
    is consistent with ``receiver`` and with the river lines extracted from it.

    ``meander`` = ``dict(world_seed=int, first_xz=(x, z)[, octaves=..., amp=...])`` makes the in-flat step costs vary with the
    deterministic coordinate-addressed noise of :func:`meander_noise`; ``None`` reproduces the unperturbed v3 routing exactly.
    """
    flow = drainage.route(elevation, ocean, spacing, area_mode='d8')
    nz, nx = flow['filled_m'].shape
    n = nz * nx
    terminal = np.asarray(ocean, bool).copy()
    terminal[0] = True; terminal[-1] = True; terminal[:, 0] = True; terminal[:, -1] = True
    order0 = flow['order']
    rank = np.empty(n, np.int64); rank[order0] = np.arange(n)
    noise = None; amp = MEANDER_AMP; boost = None
    if meander is not None:
        opts = {k: meander[k] for k in ('octaves',) if k in meander}
        amp = float(meander.get('amp', MEANDER_AMP))
        noise = meander_noise((nz, nx), meander['first_xz'], spacing, meander['world_seed'], **opts)
        b = meander.get('boost')
        if b:
            dist_km = ndimage.distance_transform_edt(~np.asarray(ocean, bool)) * float(spacing) / 1000.0
            boost = dict(near=dist_km <= float(b['max_ocean_km']), min_cells=int(b['min_cells']), amp=float(b['amp']), ortho=int(b['ortho']))
    receiver, vkey, stats = resolve_flats(flow['filled_m'], flow['receiver'].astype(np.int64), rank, terminal, noise, amp, boost)
    if noise is not None:
        stats['meander'] = dict(amp=amp, ortho_cost=MEANDER_ORTHO_COST, away_weight=MEANDER_AWAY_WEIGHT,
                                world_seed=int(meander['world_seed']), boost=(dict(meander['boost']) if meander.get('boost') else None))
        if stats['no_lower_neighbour_cells'] or stats['unresolved_cells']:
            raise ValueError('meander potential left flat cells without a lower neighbour')
    order = np.lexsort((rank, vkey, ~terminal.ravel(), flow['filled_m'].ravel()))
    pos = np.empty(n, np.int64); pos[order] = np.arange(n)
    moved = receiver != np.arange(n)
    if not np.all(pos[receiver[moved]] < pos[moved.nonzero()[0]]):
        raise ValueError('flat routing produced a non-descending receiver (cycle)')
    area = np.full(n, float(spacing) ** 2)
    rec_l = receiver.tolist(); area_l = area.tolist()
    for i in order[::-1].tolist():
        r = rec_l[i]
        if r != i:
            area_l[r] += area_l[i]
    area = np.asarray(area_l)
    f = flow['filled_m']
    return dict(area_mode='d8', receiver=receiver.astype(np.int64), order=order, area_m2=area.reshape(nz, nx),
                filled_m=f, closed_mask=(f - np.asarray(elevation)) > 1e-5, flats=stats)
