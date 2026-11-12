"""True-CSR engineering topology for TG's existing finite-conductance reservoirs.

No D4/D8 domain or natural-outlet certification is fabricated. Only explicitly
listed ocean/rim faces export water; other cuts of cell_mask are closed. Include
adjacent receiving pools (and saddle cells) in the same mask, never export to
an excluded receiving lake. Lowest actual saddle per owner pair follows TG's
_physical_faces policy; face_width_m is an engineering width, not mesh geometry.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from .terragenesis_bridge import ensure_path


def _tg():
    ensure_path()
    from terrain_pipeline import basin_storage
    return basin_storage


def _leaf_owners(bed, indptr, indices, active):
    """Equal-bed components, real downhill exits, then multi-source plateau BFS."""
    owner = np.full(bed.size, -1, np.int64)
    receiver = np.full(bed.size, -1, np.int64)
    seen = np.zeros(bed.size, bool)
    leaves = []
    for start in sorted(np.flatnonzero(active), key=lambda c: (bed[c], c)):
        if seen[start]:
            continue
        seen[start] = True
        component, todo = [], [int(start)]
        while todo:
            cell = todo.pop()
            component.append(cell)
            for other in indices[indptr[cell]:indptr[cell + 1]]:
                if active[other] and not seen[other] and bed[other] == bed[cell]:
                    seen[other] = True
                    todo.append(int(other))
        seeds = []
        for cell in sorted(component):
            lower = [int(j) for j in indices[indptr[cell]:indptr[cell + 1]]
                     if active[j] and bed[j] < bed[cell]]
            if lower:
                target = min(lower, key=lambda j: (bed[j], j))
                receiver[cell], owner[cell] = target, owner[target]
                seeds.append(cell)
        if not seeds:
            root = min(component)
            owner[root] = len(leaves)
            leaves.append(root)
            seeds = [root]
        queue = deque(seeds)
        while queue:
            cell = queue.popleft()
            for other in sorted(indices[indptr[cell]:indptr[cell + 1]]):
                if active[other] and bed[other] == bed[cell] and owner[other] < 0:
                    owner[other], receiver[other] = owner[cell], cell
                    queue.append(int(other))
    return owner, receiver, np.asarray(leaves, np.int64)


@dataclass
class CSRReservoirs:
    bed_m: np.ndarray
    area_m2: np.ndarray
    cell_owner: np.ndarray
    receiver: np.ndarray
    topology: dict
    exchange: object

    @property
    def owner_count(self):
        return self.exchange.count

    def aggregate_cells(self, volume_by_cell_m3):
        """Sum already-computed liquid inputs; no rainfall/baseflow recomputation."""
        raw = np.asarray(volume_by_cell_m3, float)
        if raw.shape != self.bed_m.shape or not np.isfinite(raw).all() or (raw < 0).any():
            raise ValueError("finite nonnegative per-cell volumes required")
        selected = self.cell_owner >= 0
        return np.bincount(self.cell_owner[selected], weights=raw[selected], minlength=self.owner_count)

    def geometry_at_volumes(self, volumes):
        """Reconstruct using TG curves only; NO hydraulic time advance or transfer."""
        stocks = np.asarray(volumes, float)
        ex = self.exchange
        if stocks.shape != (ex.count,) or not np.isfinite(stocks).all() or (stocks < 0).any():
            raise ValueError("finite nonnegative per-owner m3 required")
        depth, *_ = ex.fields(np.r_[stocks, np.zeros(2 * ex.faces + ex.boundaries)])
        stages = ex.system.bottom + depth
        selected = self.cell_owner >= 0
        cell_depth = np.zeros(self.bed_m.size)
        owners = self.cell_owner[selected]
        relative_bed = self.bed_m[selected] - ex.system.bottom[owners]
        cell_depth[selected] = np.maximum(depth[owners] - relative_bed, 0.)
        cell_stage = self.bed_m + cell_depth
        return dict(owner_stocks_m3=stocks.copy(), owner_stages_m=stages,
                    stage_by_cell_m=cell_stage, depth_by_cell_m=cell_depth,
                    volume_by_cell_m3=cell_depth * self.area_m2, wet_mask=cell_depth > 0.)

    def advance(self, volumes, supplied, dt, *, withdrawal_m3=None, subdivisions=1, max_steps=4096):
        """Fixed backward-Euler monthly substeps in scaled numerical V coordinates.

        TG owns Newton and the physical exchange. V'=V/V0, A'=A/V0,
        conductance-width'=width/V0; head/time/coefficient stay SI unchanged.
        Supply is constant in interval; withdrawals are owner-local at its start.
        """
        ex = self.exchange
        def checked(value):
            raw = np.asarray(value, float)
            if raw.shape != (ex.count,) or not np.isfinite(raw).all() or (raw < 0).any():
                raise ValueError("finite nonnegative per-owner m3 required")
            return raw.copy()
        initial, supplied = checked(volumes), checked(supplied)
        requested = np.zeros(ex.count) if withdrawal_m3 is None else checked(withdrawal_m3)
        withdrawn = np.minimum(initial, requested)
        if (not np.isfinite(dt) or dt <= 0 or not isinstance(subdivisions, int) or subdivisions < 1
                or not isinstance(max_steps, int) or subdivisions > max_steps):
            raise ValueError("positive interval/fixed subdivisions or step budget exceeded")
        # V0 is fixed for the call, a numerical unit; original SI topology stays intact.
        scale = max(float((initial + supplied).sum()), 1.)
        # Inventory-based m3 unit, fixed within this interval; no area floor:
        # a large dry catchment must not turn TG's fixed tolerance into water.
        topo = self.topology
        scaled = dict(arrays={k:v.copy() for k,v in topo['arrays'].items()}, faces=topo['faces'],
            engineering_boundaries=[dict(f, width_m=f['width_m']/scale) for f in topo['engineering_boundaries']],
            metadata=dict(topo['metadata'], spacing_m=topo['metadata']['spacing_m']/scale,
                          numerical_volume_unit_m3=scale, source_si_topology_identity=topo['identity_sha256']))
        for key in ('curve_area_m2', 'leaf_area_m2'):
            scaled['arrays'][key] /= scale
        tg = _tg()
        scaled['identity_sha256'] = tg._topology_identity(scaled)
        config = SimpleNamespace(face_conductance_m_s=topo['metadata']['face_conductance_m_s'],
                                 boundary_conductance_m_s=topo['metadata']['boundary_conductance_m_s'])
        system = tg._ReservoirSystem(scaled, config)
        previous = (initial-withdrawn)/scale
        depth = system.depth_at(previous)
        forward, reverse, exports = np.zeros(ex.faces), np.zeros(ex.faces), np.zeros(ex.boundaries)
        correction = np.zeros(ex.count)
        iterations, max_residual = 0, 0.
        for _ in range(subdivisions):
            before = previous.copy()
            previous, depth, signed, exported, count, residual = system.advance(
                previous, supplied/(scale*subdivisions), depth, dt/subdivisions)
            conservative = before + supplied/(scale*subdivisions) - (
                np.bincount(system.first,weights=signed,minlength=ex.count)
                - np.bincount(system.second,weights=signed,minlength=ex.count)
                + np.bincount(system.boundary_leaf,weights=exported,minlength=ex.count))
            correction += (previous-conservative)*scale  # TG's explicit tiny-negative max, if any.
            forward += np.maximum(signed,0.)*scale; reverse += np.maximum(-signed,0.)*scale
            exports += exported*scale
            iterations += count; max_residual = max(max_residual,residual*scale)
        stocks = previous*scale
        signed = forward-reverse
        net = (-np.bincount(system.first,weights=signed,minlength=ex.count)
               + np.bincount(system.second,weights=signed,minlength=ex.count))
        boundary = np.bincount(system.boundary_leaf,weights=exports,minlength=ex.count)
        received = (np.bincount(system.second,weights=forward,minlength=ex.count)
                    + np.bincount(system.first,weights=reverse,minlength=ex.count))
        tolerance = 1e-6 + 1e-9*np.maximum(initial+supplied+received,1.)
        residual = initial-withdrawn+supplied+net-boundary+correction-stocks
        global_residual = float(initial.sum()-withdrawn.sum()+supplied.sum()-exports.sum()+correction.sum()-stocks.sum())
        if (not np.isfinite(stocks).all() or (stocks < 0).any() or (exports < 0).any()
                or (np.abs(residual)>tolerance).any() or (np.abs(correction)>tolerance).any()
                or abs(global_residual)>float(tolerance.sum())):
            raise ValueError('TG scaled implicit independent inventory budget failed')
        return dict(**self.geometry_at_volumes(stocks), face_forward_m3=forward, face_reverse_m3=reverse,
            face_volume_m3=forward+reverse, face_net_m3=signed, boundary_exports_m3=exports,
            withdrawn_m3=withdrawn, unmet_withdrawal_m3=requested-withdrawn,
            budget=dict(initial_m3=float(initial.sum()),supplied_m3=float(supplied.sum()),withdrawn_m3=float(withdrawn.sum()),
                exported_m3=float(exports.sum()),final_m3=float(stocks.sum()),owner_residual_m3=residual,
                roundoff_correction_by_owner_m3=correction,roundoff_correction_m3=float(correction.sum()),residual_m3=global_residual),
            metadata=dict(integration='TG _ReservoirSystem.advance; fixed backward Euler; not exact transient',
                supply='externally supplied per-owner m3 / dt; no additional source',finite_interval_s=float(dt),
                instant_equilibrium=False,withdrawal='owner-local at interval start',subdivisions=subdivisions,
                accepted_steps=subdivisions,nfev=iterations,newton_iterations=iterations,max_steps=max_steps,
                numerical_volume_unit_m3=scale,volume_scale_rule='max(total initial plus supplied inventory, 1 m3)',
                geometry_numerics='TG relative owner head minus relative cell bed; absolute stage is display only',
                maximum_newton_residual_m3=max_residual,
                newton_stage_consistency_m=float(np.max(np.abs(system.depth_at(previous)-depth))),
                mass_tolerance='per owner 1e-6 + 1e-9*max(initial+supplied+gross_received,1) m3; corrections explicit',
                topology_identity_sha256=topo['identity_sha256'],scaled_topology_identity_sha256=scaled['identity_sha256']))


def build_csr_reservoirs(bed_m, mesh, area_m2=1., *, cell_mask=None, boundary_faces=(),
                         face_width_m=1., face_conductance_m_s=.6, boundary_conductance_m_s=.6):
    """Build one connected/possibly disconnected *network*, not independent pools.

    mesh.indptr/indices are undirected CSR. Full arrays retain original cell IDs;
    cell_mask restricts ownership/curves to selected pools AND saddle corridors.
    A terminal boundary record has cell_id, receiver_cell_id, sill_m, width_m,
    kind='ocean'|'rim'. receiver >= 0 must be an actual CSR neighbor outside the
    mask (ocean); -1 denotes an explicitly supplied exterior rim port. Nonterminal
    receiving pools belong inside the mask, coupled by real internal faces.
    """
    bed = np.asarray(bed_m, float).copy()
    area = np.broadcast_to(np.asarray(area_m2, float), bed.shape).copy()
    active = np.ones(bed.size, bool) if cell_mask is None else np.asarray(cell_mask, bool).copy()
    indptr, indices = np.asarray(mesh.indptr, np.int64), np.asarray(mesh.indices, np.int64)
    if (bed.ndim != 1 or not bed.size or active.shape != bed.shape or not active.any()
            or not np.isfinite(bed).all() or not np.isfinite(area).all() or (area <= 0).any()
            or indptr.shape != (bed.size + 1,) or indptr[0] != 0 or indptr[-1] != indices.size
            or (np.diff(indptr) < 0).any() or (indices < 0).any() or (indices >= bed.size).any()):
        raise ValueError("valid SI bed/area/mask and CSR required")
    if not all(np.isfinite(x) and x > 0 for x in
               (face_width_m, face_conductance_m_s, boundary_conductance_m_s)):
        raise ValueError("positive engineering widths/conductances required")
    # Only selected lake/saddle cells need Python adjacency objects, not all hillslopes.
    adjacency = {int(c): set(map(int, indices[indptr[c]:indptr[c + 1]]))
                 for c in np.flatnonzero(active)}
    if any(c == j or c not in indices[indptr[j]:indptr[j + 1]]
           for c, row in adjacency.items() for j in row):
        raise ValueError("undirected non-self CSR faces required")
    owner, receiver, leaves = _leaf_owners(bed, indptr, indices, active)
    levels, areas, offsets = [], [], [0]
    order = np.lexsort((bed[active], owner[active]))
    cells = np.flatnonzero(active)[order]
    groups = np.split(cells, np.flatnonzero(np.diff(owner[cells])) + 1)
    for group in groups:
        unique, inverse = np.unique(bed[group], return_inverse=True)
        levels.extend(unique.tolist())
        areas.extend(np.bincount(inverse, weights=area[group]).tolist())
        offsets.append(len(levels))
    candidates = {}
    for c in np.flatnonzero(active):
        for j in sorted(adjacency[c]):
            if j <= c or not active[j] or owner[c] == owner[j]:
                continue
            pair = tuple(sorted((int(owner[c]), int(owner[j]))))
            candidate = (float(max(bed[c], bed[j])), int(c), j)
            if pair not in candidates or candidate < candidates[pair]:
                candidates[pair] = candidate
    faces = [dict(leaf_ids=[int(leaves[a]), int(leaves[b])],
                  cell_ids=[c, j] if owner[c] == a else [j, c], sill_m=sill)
             for (a, b), (sill, c, j) in sorted(candidates.items())]
    boundaries = []
    for raw in boundary_faces:
        c, other = int(raw["cell_id"]), int(raw["receiver_cell_id"])
        sill, width = float(raw["sill_m"]), float(raw["width_m"])
        kind = raw["kind"]
        if (not 0 <= c < bed.size or not active[c] or kind not in ("ocean", "rim")
                or (other == -1 and kind != "rim") or other < -1
                or (other >= 0 and (other not in adjacency[c] or active[other] or kind != "ocean"))
                or not np.isfinite(sill) or sill < bed[c]
                or (other >= 0 and sill < bed[other]) or not np.isfinite(width) or width <= 0):
            raise ValueError("explicit real terminal ocean/rim boundary face required")
        boundaries.append(dict(cell_id=c, receiver_cell_id=other, leaf_id=int(leaves[owner[c]]),
                               sill_m=sill, width_m=width, kind=kind))
    arrays = dict(leaf_ids=leaves, curve_offsets=np.asarray(offsets, np.int64),
                  curve_level_m=np.asarray(levels, float), curve_area_m2=np.asarray(areas, float),
                  leaf_area_m2=np.bincount(owner[active], weights=area[active], minlength=len(leaves)))
    topology = dict(arrays=arrays, faces=faces, engineering_boundaries=boundaries,
                    metadata=dict(schema="dream-csr-reservoir-engineering-v1", spacing_m=float(face_width_m),
                                  graph="true undirected CSR; downhill/plateau leaf ownership",
                                  face_policy="lowest actual saddle face per owner pair; fixed engineering width",
                                  cut_policy="unlisted mask cuts closed; receiving pools must be included",
                                  face_conductance_m_s=float(face_conductance_m_s),
                                  boundary_conductance_m_s=float(boundary_conductance_m_s),
                                  original_source_certified=False, natural_outlet_verified=False,
                                  hydraulic_ready=False, publishable=False))
    tg = _tg()
    topology["identity_sha256"] = tg._topology_identity(topology)
    config = SimpleNamespace(face_conductance_m_s=float(face_conductance_m_s),
                             boundary_conductance_m_s=float(boundary_conductance_m_s))
    exchange = tg._RunoffExchange(topology, config)
    return CSRReservoirs(bed, area, owner, receiver, topology, exchange)
