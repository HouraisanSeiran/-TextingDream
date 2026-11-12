"""Certified single-sink TG pool DAG on immutable physical CSR bed.

TG positive-fill pools are NOT automatically connected at every partial stage.
A pool is usable only when all its cells descend (flat-BFS included) to ONE
bed sink within that pool. This certifies connected sublevels without guessing
internal saddles. Multi-sink pools and components without declared outlets are
unresolved and refuse publication; they need a genuine saddle/subpool adapter.

``receiver/order`` describe bed hillslopes, never the uphill flood escape map.
TG route_pool_interval handles persistent exclusive pool stocks and serial spill;
TG LakeStorage (or its existing large-column WeightedLakeGeometry) inverts V(h).
Legacy node fields remain, now as exclusive pools plus zero-capacity terminals,
not an incremental merge tree. Spill paths follow real CSR flood receivers and
are schematic volume transfers, NOT finite-rate hydraulic channel discharge.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
from scipy import sparse

VERSION = "tg-certified-single-sink-pool-dag-2"


def _readonly(value, dtype=None):
    result = np.array(value, dtype=dtype, copy=True)
    result.flags.writeable = False
    return result


@dataclass(frozen=True)
class Geometry:
    source_identity: str
    bed_m: np.ndarray
    area_m2: np.ndarray
    indptr: np.ndarray
    indices: np.ndarray
    outlet_mask: np.ndarray
    cell_node: np.ndarray
    parent: np.ndarray
    children_indptr: np.ndarray
    children: np.ndarray
    birth_m: np.ndarray
    crest_m: np.ndarray
    spill_edge: np.ndarray
    terminal_outlet: np.ndarray
    subtree_area_m2: np.ndarray
    base_capacity_m3: np.ndarray
    capacity_m3: np.ndarray
    receiver: np.ndarray
    order: np.ndarray
    drain_node_by_cell: np.ndarray
    drain_outlet_by_cell: np.ndarray
    storage_by_node: tuple
    node_anchor: np.ndarray
    forest_parent: np.ndarray
    forest_depth: np.ndarray
    estimated_peak_bytes: int
    flood_receiver: np.ndarray
    flood_order: np.ndarray
    pool_labels: np.ndarray
    pool_anchors: np.ndarray
    pool_members: tuple
    spill_target_cell: np.ndarray
    certification: dict
    geometry_identity: str
    boundary_policy: str = "declared outlets only; finite-domain engineering boundary"
    time_policy: str = "fixed supplied physical bed; non-subglacial"

    @property
    def roots(self):
        return np.flatnonzero(self.parent < 0)

    @property
    def sinks(self):
        return np.flatnonzero(np.diff(self.children_indptr) == 0)

    def check_mesh(self, mesh):
        """Exact CSR restoration check, not merely shape/seed agreement."""
        return (np.array_equal(self.indptr, mesh.indptr)
                and np.array_equal(self.indices, mesh.indices))


@dataclass(frozen=True)
class Transfer:
    source_node: int
    target_node: int
    edge: tuple[int, int]
    volume_m3: float
    path: object
    path_policy: str = "deterministic CSR schematic gross route; hide wet interior; not hydraulic Q"


@dataclass(frozen=True)
class WaterState:
    source_identity: str
    layer_volume_by_node_m3: np.ndarray
    volume_by_node_m3: np.ndarray
    volume_by_cell_m3: np.ndarray
    stage_by_cell_m: np.ndarray
    wet_mask: np.ndarray
    overflow_by_outlet_m3: np.ndarray
    spill_m3_by_node: np.ndarray
    transfer_to_child_m3: np.ndarray
    transfers: tuple[Transfer, ...]
    actual_withdrawal_m3: float
    unmet_withdrawal_m3: float
    balance_error_m3: float
    actual_withdrawal_by_cell_m3: np.ndarray
    geometry_identity: str = ""


class GeometryCertificationError(ValueError):
    """Unresolved geometry is never silently removed from the water account."""
    def __init__(self, report):
        self.report = report
        super().__init__('unresolved lake geometry; refusing publication: ' +
            str({k: v for k, v in report.items() if k != 'unresolved_pools'}))


@dataclass(frozen=True)
class ReceiverPath:
    start: int
    end: int
    receiver: np.ndarray

    def __iter__(self):
        current = self.start
        while True:
            yield current
            if current == self.end:
                return
            current = int(self.receiver[current])
            if current < 0:
                raise RuntimeError('spill path did not reach certified destination')


def _bed_routes(z, ip, ix, outlets):
    """One equal-height plateau at a time; strictly descending or flat BFS edges."""
    n = z.size
    receiver = np.full(n, -2, np.int64)
    visited = np.zeros(n, bool)
    for start in range(n):
        if visited[start]:
            continue
        stack, cells = [start], []
        visited[start] = True
        while stack:
            c = stack.pop()
            cells.append(c)
            for j in ix[ip[c]:ip[c + 1]]:
                if not visited[j] and z[j] == z[c]:
                    visited[j] = True
                    stack.append(int(j))
        queue = deque()
        for c in sorted(cells):
            lower = [int(j) for j in ix[ip[c]:ip[c + 1]] if z[j] < z[c]]
            if outlets[c] or lower:
                receiver[c] = -1 if outlets[c] else min(lower, key=lambda j: (z[j], j))
                queue.append(c)
        if not queue:
            c = min(cells)
            receiver[c] = -1
            queue.append(c)
        while queue:
            c = queue.popleft()
            for j in sorted(ix[ip[c]:ip[c + 1]]):
                if z[j] == z[c] and receiver[j] == -2:
                    receiver[j] = c
                    queue.append(int(j))
    # Linear downstream-first topological pass; height sorting alone fails flats.
    count = np.bincount(receiver[receiver >= 0], minlength=n)
    queue = deque(np.flatnonzero(count == 0).tolist())
    upstream = []
    while queue:
        c = queue.popleft()
        upstream.append(c)
        j = int(receiver[c])
        if j >= 0:
            count[j] -= 1
            if count[j] == 0:
                queue.append(j)
    order = np.asarray(upstream[::-1], np.int64)
    sink = np.empty(n, np.int64)
    for c in order:
        sink[c] = c if receiver[c] < 0 else sink[receiver[c]]
    return receiver, order, sink


def build_geometry(bed, mesh, outlet_mask, area_m2, source_identity, budget_bytes=1 << 30):
    """TG flood + certified single-sink pool DAG; O(N+E) arrays, no cell nodes.

    The estimated budget is an allowance, not an RSS cap. A missing mesh shape
    or length vector is supported for tiny abstract-graph fixtures (unit edges);
    production passes the actual TG mesh and metric edge lengths unchanged.
    """
    from app.world_gen.graph_hydro import load_terragenesis
    drainage, _ = load_terragenesis()
    raw = np.asarray(bed)
    n = raw.size
    ip0, ix0 = np.asarray(mesh.indptr), np.asarray(mesh.indices)
    estimate = 320 * n + 48 * ix0.size + 65536
    if not isinstance(budget_bytes, (int, np.integer)) or budget_bytes <= 0 or estimate > budget_bytes:
        raise MemoryError(f'lake geometry estimated peak {estimate} exceeds budget {budget_bytes}')
    if not isinstance(source_identity, str) or len(source_identity) != 64 or any(c not in '0123456789abcdef' for c in source_identity):
        raise ValueError('source_identity must be lowercase SHA256')
    if n == 0 or not np.isfinite(raw).all():
        raise ValueError('bed must be nonempty and finite')
    if (ip0.shape != (n + 1,) or ip0.dtype.kind not in 'iu' or ix0.dtype.kind not in 'iu'
            or ip0[0] != 0 or ip0[-1] != ix0.size or np.any(np.diff(ip0) < 0)
            or np.any(ix0 < 0) or np.any(ix0 >= n)):
        raise ValueError('invalid CSR mesh')
    z = np.asarray(raw, np.float64).ravel().copy()
    area = np.broadcast_to(np.asarray(area_m2, np.float64), raw.shape).ravel().copy()
    outlets = np.asarray(outlet_mask, bool).ravel().copy()
    if outlets.size != n or not np.isfinite(area).all() or np.any(area <= 0):
        raise ValueError('outlets/positive finite cell areas must match bed')
    ip, ix = ip0.astype(np.int64), ix0.astype(np.int64)
    graph = sparse.csr_matrix((np.ones(ix.size, np.int8), ix, ip), shape=(n, n))
    if (graph != graph.T).nnz or np.any(graph.diagonal()):
        raise ValueError('mesh must be undirected without self edges')
    del graph
    lengths = np.asarray(getattr(mesh, 'edge_length_m', np.ones(ix.size)), np.float64)
    if lengths.shape != ix.shape or not np.isfinite(lengths).all() or np.any(lengths <= 0):
        raise ValueError('positive finite CSR edge lengths required')
    native_mesh = SimpleNamespace(shape=raw.shape, indptr=ip, indices=ix, edge_length_m=lengths)
    try:
        flood = drainage.route_graph(z.reshape(raw.shape), outlets.reshape(raw.shape), native_mesh)
    except ValueError as exc:
        raise GeometryCertificationError(dict(status='unresolved', reason=str(exc),
            boundary_policy='declared outlets unchanged; closed components unsupported')) from exc
    filled = flood.filled.ravel()
    labels, p = drainage.pool_labels(z, filled, ip, ix)
    receiver, order, sink = _bed_routes(z, ip, ix, outlets)
    # Group ONLY positive-fill cells once, instead of O(N * pool_count) scans.
    wet_ids = np.flatnonzero(labels >= 0)
    wet_ids = wet_ids[np.argsort(labels[wet_ids], kind='stable')]
    cuts = np.r_[0, np.cumsum(np.bincount(labels[wet_ids], minlength=p))]
    members = tuple(wet_ids[cuts[k]:cuts[k + 1]] for k in range(p))
    unresolved = []
    for k, ids in enumerate(members):
        sinks = np.unique(sink[ids])
        if sinks.size != 1 or labels[sinks[0]] != k:
            unresolved.append(dict(pool_id=k, cell_count=int(ids.size),
                sink_cells=sinks.tolist(), spill_m=float(filled[ids[0]])))
    report = dict(status='certified' if not unresolved else 'unresolved', pool_count=p,
        positive_fill_cells=int(wet_ids.size), certified_pool_count=p - len(unresolved),
        unresolved_pool_count=len(unresolved), unresolved_cell_count=sum(v['cell_count'] for v in unresolved),
        unresolved_pools=unresolved,
        policy='one true-bed flat-BFS sink per equal-spill TG pool; no internal-saddle approximation')
    if unresolved:
        raise GeometryCertificationError(report)
    terminal_cells = np.flatnonzero(outlets)
    m = p + terminal_cells.size
    terminal_index = np.full(n, -1, np.int64)
    terminal_index[terminal_cells] = np.arange(p, m)
    drain_outlet = np.where(outlets[sink], sink, -1)
    drain = np.where(drain_outlet >= 0, terminal_index[sink], labels[sink])
    if np.any(drain < 0):
        raise GeometryCertificationError(dict(status='unresolved', reason='bed sink outside certified pool'))
    cell_node = np.where(labels >= 0, labels, drain)
    anchors = np.array([ids[np.argmin(flood.rank[ids])] for ids in members], np.int64)
    crest = np.r_[[filled[ids[0]] for ids in members], z[terminal_cells]]
    birth = np.r_[[z[ids].min() for ids in members], z[terminal_cells]]
    parent = np.full(m, -1, np.int64)
    spill_edge = np.full((m, 2), -1, np.int64)
    terminal = np.full(m, -1, np.int64)
    terminal[p:] = terminal_cells
    # Downstream-first flood map skips dry path only, never an unfilled pool.
    destination = np.empty(n, np.int64)
    destination_cell = np.empty(n, np.int64)
    for c in flood.order:
        destination[c] = (labels[c] if labels[c] >= 0 else
                          terminal_index[c] if outlets[c] else destination[flood.receiver[c]])
        destination_cell[c] = c if labels[c] >= 0 or outlets[c] else destination_cell[flood.receiver[c]]
    spill_target_cell = np.full(m, -1, np.int64)
    for k, anchor in enumerate(anchors):
        nxt = int(flood.receiver[anchor])
        parent[k] = destination[nxt]
        spill_target_cell[k] = destination_cell[nxt]
        spill_edge[k] = anchor, nxt
    capacity = np.zeros(m)
    storages = []
    from terrain_pipeline.lake import LakeStorage
    for k, ids in enumerate(members):
        if ids.size <= 65536:
            storage = LakeStorage(ids.astype(np.int64), z[ids], area[ids], int(sink[ids[0]]),
                float(crest[k]), source_identity, 'TG pool certified single descending sink at every sublevel')
        else:
            from terrain_pipeline.runoff import WeightedLakeGeometry
            storage = WeightedLakeGeometry(z[ids], area[ids], np.ones(ids.size, bool), crest[k])
        storages.append(storage)
        capacity[k] = storage.capacity_m3
    storages.extend([None] * terminal_cells.size)
    from terrain_pipeline.common_infra import identity, array_sha256
    binding = identity({}, dict(version=VERSION, source=source_identity,
        bed=array_sha256(z), area=array_sha256(area), outlets=array_sha256(outlets),
        indptr=array_sha256(ip), indices=array_sha256(ix), lengths=array_sha256(lengths)))
    # Exclusive DAG inventory: no nested child/subtree summation.
    empty = np.empty(0, np.int64)
    node_anchor = np.r_[[sink[ids[0]] for ids in members], terminal_cells].astype(np.int64)
    return Geometry(source_identity, *[_readonly(v) for v in
        (z, area, ip, ix, outlets, cell_node, parent, np.zeros(m + 1, np.int64), empty,
         birth, crest, spill_edge, terminal,
         np.r_[[area[ids].sum() for ids in members], np.zeros(terminal_cells.size)],
         np.zeros(m), capacity, receiver, order, drain, drain_outlet)], tuple(storages),
        _readonly(node_anchor), _readonly(flood.receiver), _readonly(flood.rank), int(estimate),
        _readonly(flood.receiver), _readonly(flood.order), _readonly(labels), _readonly(anchors),
        tuple(_readonly(ids) for ids in members), _readonly(spill_target_cell), report, binding)


def settle(g, state=None, *, source_by_cell_m3=None, withdrawal_by_cell_m3=None):
    """TG serial fill/spill once, then demand limited by its whole pool's stock."""
    from app.world_gen.graph_hydro import load_terragenesis
    drainage, _ = load_terragenesis()
    n, m, p = g.bed_m.size, g.parent.size, len(g.pool_members)
    def supplied(value):
        a = np.zeros(n) if value is None else np.asarray(value, np.float64).ravel()
        if a.size != n or not np.isfinite(a).all() or np.any(a < 0):
            raise ValueError('supplied water must be finite nonnegative m3 per original cell')
        return a
    source, demand_cell = supplied(source_by_cell_m3), supplied(withdrawal_by_cell_m3)
    if state is not None and (state.source_identity != g.source_identity
            or state.geometry_identity != g.geometry_identity
            or state.layer_volume_by_node_m3.shape != (m,)):
        raise ValueError('state does not match geometry/source')
    old = np.zeros(m) if state is None else np.array(state.layer_volume_by_node_m3, copy=True)
    if not np.isfinite(old).all() or np.any(old < 0) or np.any(old > g.capacity_m3):
        raise ValueError('invalid stored pool inventory')
    storage = old[:p].copy()
    # Hillslope rain enters its true-bed sink ONCE; direct lake water already has
    # its own pool label. Do not route new source uphill on the flood map first.
    injected = np.zeros(n)
    receiving_cell = np.where(g.pool_labels >= 0, np.arange(n), g.node_anchor[g.drain_node_by_cell])
    np.add.at(injected, receiving_cell, source)
    flow, _ = drainage.route_pool_interval(injected, g.flood_order, g.flood_receiver,
        g.pool_labels, g.pool_anchors, g.capacity_m3[:p], storage)
    overflow = np.where(g.outlet_mask, flow, 0.)
    spill = np.zeros(m)
    spill[:p] = flow[g.pool_anchors]
    transfers = []
    for k in np.flatnonzero(spill):
        target = int(g.parent[k])
        anchor = int(g.pool_anchors[k])
        end = int(g.spill_target_cell[k])
        # Start at the actual flood escape anchor, not an invented interior path.
        path = ReceiverPath(anchor, end, g.flood_receiver)
        transfers.append(Transfer(int(k), target if target < p else -1,
            tuple(map(int, g.spill_edge[k])), float(spill[k]), path))
    # Include direct terminal inputs separately; downstream spill is already in
    # its own path event and must not be duplicated as another terminal transfer.
    terminal_direct = np.bincount(g.drain_outlet_by_cell[g.drain_outlet_by_cell >= 0],
        weights=source[g.drain_outlet_by_cell >= 0], minlength=n)
    for c in np.flatnonzero(terminal_direct):
        k = int(g.cell_node[c])
        transfers.append(Transfer(k, -1, (-1, -1), float(terminal_direct[c]),
            ReceiverPath(int(c), int(c), g.flood_receiver)))
    # A demand physically on a certified pool uses that pool, not a distant sink.
    demand_node = np.where(g.pool_labels >= 0, g.pool_labels, g.drain_node_by_cell)
    demand = np.bincount(demand_node, weights=demand_cell, minlength=m)
    actual_node = np.minimum(np.r_[storage, np.zeros(m - p)], demand)
    fraction = np.divide(actual_node, demand, out=np.zeros(m), where=demand > 0)
    actual_by_cell = demand_cell * fraction[demand_node]
    storage -= actual_node[:p]
    layer = np.r_[storage, np.zeros(m - p)]
    stage, by_cell = g.bed_m.copy(), np.zeros(n)
    for k, ids in enumerate(g.pool_members):
        curve = g.storage_by_node[k]
        level = (curve.stage_at_volume(float(storage[k])) if hasattr(curve, 'stage_at_volume')
                 else curve.level(float(storage[k])))
        stage[ids] = np.maximum(g.bed_m[ids], level)
        by_cell[ids] = np.maximum(level - g.bed_m[ids], 0.) * g.area_m2[ids]
    actual = float(actual_node.sum())
    balance = float(old.sum() + source.sum() - layer.sum() - overflow.sum() - actual)
    return WaterState(g.source_identity, *[_readonly(v) for v in
        (layer, layer, by_cell, stage, by_cell > 0, overflow, spill, np.zeros(m))],
        tuple(transfers), actual, float(demand_cell.sum() - actual), balance,
        _readonly(actual_by_cell), g.geometry_identity)
