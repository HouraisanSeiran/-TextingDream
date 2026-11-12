"""Small graph fixtures only: no original product, full-world solve or D8."""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen.lake_basin_geometry import build_geometry, settle

IDENTITY = "a" * 64


def mesh_for(n, edges=None, reverse=False):
    edges = list(zip(range(n - 1), range(1, n))) if edges is None else edges
    neighbors = [[] for _ in range(n)]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    values = [sorted(row, reverse=reverse) for row in neighbors]
    return SimpleNamespace(indptr=np.r_[0, np.cumsum([len(v) for v in values])],
                           indices=np.array([j for row in values for j in row], np.int64))


def geometry(bed, outlets=(), area=1., edges=None):
    bed = np.array(bed, float)
    mask = np.zeros(bed.size, bool)
    mask[list(outlets)] = True
    return build_geometry(bed, mesh_for(bed.size, edges), mask, area, IDENTITY)


def water(g, **cells):
    a = np.zeros(g.bed_m.size)
    for k, value in cells.items():
        a[int(k)] = value
    return a


def checked(g, state=None, **kwargs):
    result = settle(g, state, **kwargs)
    assert result.balance_error_m3 == pytest.approx(0., abs=1e-8)
    assert result.volume_by_cell_m3.sum() == pytest.approx(result.layer_volume_by_node_m3.sum())
    return result


@pytest.mark.parametrize('bed,source', [
    ([0, 2, 0, 5, 0], [1.5, 0, 0, 0, 0]),
    ([0, 2, 0, 5, 0], [3., 0, 0, 0, 0]),
    ([0, 8, 0, 10, 0], [7., 0, 0, 0, 0]),
    ([0, 2, 0, 5, 0], [20., 0, 0, 0, 0]),
])
def test_internal_saddle_not_misrepresented_as_whole_connected_pool(bed, source):
    # Previously exercised merge/retreat with the now-known-wrong layer core.
    # Correct partial fill, later merge and retreat remain REQUIRED future work;
    # until a real saddle adapter exists this input must not yield a water state.
    from app.world_gen.lake_basin_geometry import GeometryCertificationError
    with pytest.raises(GeometryCertificationError) as caught:
        geometry(bed, outlets=[4])
    report = caught.value.report
    assert report['unresolved_pool_count'] == 1
    assert report['unresolved_pools'][0]['sink_cells'] == [0, 2]
    assert report['unresolved_cell_count'] == 3


def test_equal_height_neighbor_permutations_give_same_certified_dag():
    bed = np.array([0, 1, 1, 3, 0.])
    mask = np.arange(5) == 4
    a = build_geometry(bed, mesh_for(5), mask, 1., IDENTITY)
    b = build_geometry(bed, mesh_for(5, reverse=True), mask, 1., IDENTITY)
    for name in ('cell_node', 'parent', 'receiver', 'order', 'spill_edge', 'capacity_m3'):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))
    np.testing.assert_array_equal(checked(a, source_by_cell_m3=[3., 0, 0, 0, 0]).volume_by_cell_m3,
                                  checked(b, source_by_cell_m3=[3., 0, 0, 0, 0]).volume_by_cell_m3)
    rank = np.empty(5, int); rank[a.order] = np.arange(5)
    for cell, recv in enumerate(a.receiver):
        if recv >= 0:
            assert rank[recv] < rank[cell]
            assert recv in a.indices[a.indptr[cell]:a.indptr[cell + 1]]


def test_flat_closed_explicitly_rejected_and_open_multiple_outlets():
    from app.world_gen.lake_basin_geometry import GeometryCertificationError
    with pytest.raises(GeometryCertificationError, match='closed components unsupported'):
        geometry([0, 0, 0])
    opened = geometry([0, 0, 0], outlets=[0, 2])
    s = checked(opened, source_by_cell_m3=[0, 3, 4])
    assert s.volume_by_cell_m3.sum() == 0
    np.testing.assert_allclose(s.overflow_by_outlet_m3, [3, 0, 4])
    np.testing.assert_array_equal(opened.drain_outlet_by_cell, [0, 0, 2])


def test_disconnected_closed_components_do_not_receive_invented_outlets():
    from app.world_gen.lake_basin_geometry import GeometryCertificationError
    with pytest.raises(GeometryCertificationError):
        geometry([0, 1, 0, 1], outlets=[0], edges=[(0, 1), (2, 3)])



def test_no_source_no_lakes_and_slope_route_once():
    g = geometry([0, 1, 3, 5, 0], outlets=[4])
    assert not checked(g).wet_mask.any()
    s = checked(g, source_by_cell_m3=[0, 0, 2, 0, 0])
    assert g.receiver[2] == 1 and g.receiver[1] == 0
    assert g.drain_node_by_cell[2] == g.cell_node[0]
    assert s.volume_by_cell_m3.sum() == 2
    assert s.volume_by_cell_m3[2] == 0


def test_100_square_km_cell_units_and_tg_storage():
    g = geometry([0, 2, 0], outlets=[2], area=100_000_000.)
    s = checked(g, source_by_cell_m3=[100_000_000., 0, 0])
    assert s.stage_by_cell_m[0] == 1
    assert g.capacity_m3[g.cell_node[0]] == 200_000_000.
    storage = g.storage_by_node[g.cell_node[0]]
    assert storage is not None
    assert storage.stage_at_volume(100_000_000.) == 1


def test_inputs_immutable_restore_and_budget_rejection():
    bed = np.array([0., 2., 0.])
    area = np.array([1., 2., 3.])
    mask = np.array([False, False, True])
    mesh = mesh_for(3)
    originals = [v.copy() for v in (bed, area, mask, mesh.indptr, mesh.indices)]
    g = build_geometry(bed, mesh, mask, area, IDENTITY)
    s = checked(g, source_by_cell_m3=[1., 0., 0.])
    for old, value in zip(originals, (bed, area, mask, mesh.indptr, mesh.indices)):
        np.testing.assert_array_equal(old, value)
    assert g.check_mesh(mesh)
    assert not g.bed_m.flags.writeable and not s.layer_volume_by_node_m3.flags.writeable
    with pytest.raises(MemoryError):
        build_geometry(bed, mesh, mask, area, IDENTITY, budget_bytes=1)
    with pytest.raises(ValueError):
        settle(g, source_by_cell_m3=[-1, 0, 0])
    with pytest.raises(ValueError):
        settle(g, replace(s, source_identity="b" * 64))


def test_transfer_paths_are_lazy_continuous_crest_bounded_and_reach_outlet():
    g = geometry([0, 3, 0, 2, 0], outlets=[4])
    s = checked(g, source_by_cell_m3=[30., 0, 0, 0, 0])
    assert any(t.target_node == -1 for t in s.transfers)
    for t in s.transfers:
        path = list(t.path)
        assert len(path) == len(set(path))
        assert path[0] == g.pool_anchors[t.source_node]
        ceiling = g.crest_m[t.source_node]
        assert g.bed_m[path].max() <= ceiling
        for a, b in zip(path[:-1], path[1:]):
            assert b in g.indices[g.indptr[a]:g.indptr[a + 1]]
        if t.target_node < 0:
            assert g.outlet_mask[path[-1]]
        else:
            assert t.edge in list(zip(path[:-1], path[1:]))
    assert sum(t.volume_m3 for t in s.transfers if t.target_node < 0) == s.overflow_by_outlet_m3.sum()


def test_actual_withdrawal_by_cell_is_demand_attribution_not_local_column():
    g = geometry([0, 1, 5, 0], outlets=[3])
    s = checked(g, source_by_cell_m3=[7., 0, 0, 0])
    # Column at cell 1 has only 3 m3, but the connected pool contains 7.
    s = checked(g, s, withdrawal_by_cell_m3=[0, 4., 0, 0])
    np.testing.assert_allclose(s.actual_withdrawal_by_cell_m3, [0, 4, 0, 0])
    assert s.actual_withdrawal_m3 == 4
    s = checked(g, s, withdrawal_by_cell_m3=[4., 1., 0, 0])
    np.testing.assert_allclose(s.actual_withdrawal_by_cell_m3, [2.4, .6, 0, 0])
    assert s.actual_withdrawal_m3 == 3
    assert s.unmet_withdrawal_m3 == 2


def test_large_flat_leaf_does_not_weaken_tg_cell_limit():
    # One connected 65537-cell plateau, not a full-world solve.
    count = 65537
    bed = np.r_[np.zeros(count), 2., 0.]
    mask = np.zeros(bed.size, bool)
    mask[-1] = True
    g = build_geometry(bed, mesh_for(bed.size), mask, 1., IDENTITY)
    from terrain_pipeline.runoff import WeightedLakeGeometry
    assert isinstance(g.storage_by_node[g.cell_node[0]], WeightedLakeGeometry)
    s = checked(g, source_by_cell_m3=np.r_[float(count), np.zeros(bed.size - 1)])
    np.testing.assert_allclose(s.stage_by_cell_m[:count], 1.)
    assert g.capacity_m3[g.cell_node[0]] == 2 * count


def test_certified_leaf_actually_uses_native_stage_inversion(monkeypatch):
    g = geometry([0, 2, 0], outlets=[2], area=[2., 3., 1.])
    storage = g.storage_by_node[g.cell_node[0]]
    native = type(storage).stage_at_volume
    calls = []
    def checked_stage(self, volume):
        calls.append((self, volume))
        return native(self, volume)
    monkeypatch.setattr(type(storage), 'stage_at_volume', checked_stage)
    state = checked(g, source_by_cell_m3=[3., 0., 0.])
    assert any(obj is storage and volume == 3. for obj, volume in calls)
    assert state.stage_by_cell_m[0] == 1.5


def test_native_flood_pool_and_weighted_storage_single_connected_pool_comparison():
    # The monotone basin has NO internal split saddle. Flood receivers point
    # uphill to spill; bed receivers point down to the sink: never interchange.
    from app.world_gen import graph_hydro as gh
    drainage, _ = gh.load_terragenesis()
    from terrain_pipeline.runoff import WeightedLakeGeometry
    bed = np.array([0., 1., 3., 0.])
    area = np.array([2., 3., 1., 1.])
    mesh = mesh_for(4)
    mesh.shape = bed.shape
    mesh.edge_length_m = np.ones(mesh.indices.size)
    outlets = np.array([False, False, False, True])
    g = build_geometry(bed, mesh, outlets, area, IDENTITY)
    flood = drainage.route_graph(bed, outlets, mesh)
    labels, count = drainage.pool_labels(bed, flood.filled, mesh.indptr, mesh.indices)
    assert count == 1
    members = np.flatnonzero(labels == 0)
    assert set(members) == {0, 1}
    assert g.receiver[1] == 0 and flood.receiver[0] == 1
    lake = WeightedLakeGeometry(bed, area, labels == 0, 3.)
    anchors = np.array([members[np.argmin(flood.rank[members])]], np.int64)
    capacity = np.array([lake.capacity_m3])
    storage = np.zeros(1)
    state = None
    for amount in (1., 5., 10.):
        local = np.array([amount, 0., 0., 0.])
        previous = storage.sum()
        flow, retained = drainage.route_pool_interval(local, flood.order, flood.receiver,
                                                       labels, anchors, capacity, storage)
        state = checked(g, state, source_by_cell_m3=local)
        assert retained == pytest.approx(storage.sum() - previous)
        assert storage[0] == pytest.approx(state.layer_volume_by_node_m3.sum())
        assert flow[outlets].sum() == pytest.approx(state.overflow_by_outlet_m3.sum())
        assert previous + amount == pytest.approx(storage.sum() + flow[outlets].sum())
        level = lake.level(storage[0])
        np.testing.assert_allclose(state.volume_by_cell_m3[members],
                                   np.maximum(level - bed[members], 0.) * area[members])
    assert storage[0] == 12. and flow[outlets].sum() == 4.


def test_native_shore_step_conserves_external_forcing_but_month_start_split_differs():
    from app.world_gen import graph_hydro as gh
    gh.load_terragenesis()
    from terrain_pipeline.runoff import WeightedLakeGeometry, SeasonalConfig, _shore_step
    bed = np.array([0., 1.]); area = np.array([1000., 2000.])
    membership = np.ones(2, bool)
    lake = WeightedLakeGeometry(bed, area, membership, 10.)
    initial = 1000.1; soil = np.zeros(2)
    rain = np.array([3., 5.]); pet = np.full(2, 10.)
    after, volume, ledger, events = _shore_step(bed, membership, soil, initial,
        rain, pet, area, lake, 1., SeasonalConfig())
    assert events and events[0]['kind'] == 'real_bed_crossing'
    assert events[0]['level_m'] == 1.
    rain_total = np.sum(rain * area) / 1000.
    assert ledger['land_rain_m3'] + ledger['lake_rain_m3'] == pytest.approx(rain_total)
    actual_et = ledger['land_et_m3'] + ledger['lake_evaporation_m3']
    assert volume + np.sum(after * area) / 1000. == pytest.approx(initial + rain_total - actual_et)
    # This task charges PET on month-start wet cells for the full interval.
    # Native shoreline events switch to dry soil after retreat: valid but different.
    month_start_lake_et = np.sum(pet * area) / 1000.
    assert ledger['lake_evaporation_m3'] < month_start_lake_et


def test_native_two_serial_certified_pools_overflow_matches_core():
    from app.world_gen import graph_hydro as gh
    drainage, _ = gh.load_terragenesis()
    bed = np.array([0., 3., 0., 2., 0.])
    area = np.array([2., 1., 3., 1., 1.])
    mesh = mesh_for(5); mesh.shape = bed.shape
    mesh.edge_length_m = np.ones(mesh.indices.size)
    outlets = np.arange(5) == 4
    g = build_geometry(bed, mesh, outlets, area, IDENTITY)
    flood = drainage.route_graph(bed, outlets, mesh)
    labels, count = drainage.pool_labels(bed, flood.filled, mesh.indptr, mesh.indices)
    assert count == 2  # downstream spill is lower: no common trapped merge layer
    members = [np.flatnonzero(labels == k) for k in range(count)]
    anchors = np.array([ids[np.argmin(flood.rank[ids])] for ids in members], np.int64)
    capacity = np.array([np.sum((flood.filled[ids] - bed[ids]) * area[ids]) for ids in members])
    storage = np.zeros(count); state = None
    for amount, expected_storage, expected_outflow in ((8., [6., 2.], 0.), (10., [6., 6.], 6.)):
        local = np.array([amount, 0., 0., 0., 0.])
        flow, retained = drainage.route_pool_interval(local, flood.order, flood.receiver,
                                                       labels, anchors, capacity, storage)
        state = checked(g, state, source_by_cell_m3=local)
        np.testing.assert_allclose(storage, expected_storage)
        np.testing.assert_allclose(storage, [state.volume_by_cell_m3[ids].sum() for ids in members])
        assert flow[outlets].sum() == state.overflow_by_outlet_m3.sum() == expected_outflow
        assert retained + expected_outflow == amount


def test_equal_level_serial_saddles_cannot_skip_middle_pool():
    g = geometry([0, 2, 0, 2, 0], outlets=[0])
    state = checked(g, source_by_cell_m3=[0., 0., 0., 0., 3.])
    np.testing.assert_allclose(state.volume_by_cell_m3, [0., 0., 1., 0., 2.])
    assert state.overflow_by_outlet_m3.sum() == 0.


def test_equal_level_closed_counterexample_explicitly_unresolved():
    # Correct target remains [0,0,1,0,2], NOT the old leftmost-child gift.
    from app.world_gen.lake_basin_geometry import GeometryCertificationError
    with pytest.raises(GeometryCertificationError, match='closed components unsupported'):
        geometry([0, 2, 0, 2, 0])


def test_production_settle_calls_tg_pool_kernel_and_restore_binds_area(monkeypatch):
    from app.world_gen.graph_hydro import load_terragenesis
    drainage, _ = load_terragenesis()
    native = drainage.route_pool_interval
    calls = []
    def traced(*args):
        calls.append(args)
        return native(*args)
    monkeypatch.setattr(drainage, 'route_pool_interval', traced)
    g = geometry([0, 3, 0, 2, 0], outlets=[4], area=[2., 1., 3., 1., 1.])
    s = checked(g, source_by_cell_m3=[8., 0, 0, 0, 0])
    np.testing.assert_allclose(s.volume_by_cell_m3, [6., 0, 2., 0, 0])
    assert len(calls) == 1
    assert calls[0][1] is g.flood_order and calls[0][2] is g.flood_receiver
    changed = geometry([0, 3, 0, 2, 0], outlets=[4], area=2.)
    with pytest.raises(ValueError, match='geometry/source'):
        settle(changed, s)


def test_partial_withdrawal_never_borrows_across_serial_dry_saddle():
    g = geometry([0, 3, 0, 2, 0], outlets=[4])
    s = checked(g, source_by_cell_m3=[3., 0, 1., 0, 0])
    s = checked(g, s, withdrawal_by_cell_m3=[9., 0, 0, 0, 0])
    np.testing.assert_allclose(s.volume_by_cell_m3, [0., 0, 1., 0, 0])
    assert s.actual_withdrawal_m3 == 3 and s.unmet_withdrawal_m3 == 6
