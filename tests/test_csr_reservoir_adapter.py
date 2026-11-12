"""Tiny true-CSR fixtures only; no D4/D8, world solve or product writes."""
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen.csr_reservoir_adapter import build_csr_reservoirs, _tg

MONTH = 30 * 86400.


def mesh(n, edges=None, reverse=False):
    rows = [[] for _ in range(n)]
    for a, b in (list(zip(range(n - 1), range(1, n))) if edges is None else edges):
        rows[a].append(b)
        rows[b].append(a)
    rows = [sorted(row, reverse=reverse) for row in rows]
    return SimpleNamespace(indptr=np.r_[0, np.cumsum([len(row) for row in rows])],
                           indices=np.array([v for row in rows for v in row], np.int64))


def network(bed, area=1., outlet=None, sill=None, **kwargs):
    boundaries = () if outlet is None else [dict(cell_id=outlet, receiver_cell_id=-1,
                                                sill_m=sill, width_m=1., kind="rim")]
    return build_csr_reservoirs(np.array(bed, float), mesh(len(bed)), area,
                                boundary_faces=boundaries, **kwargs)


def source(g, cell, amount):
    water = np.zeros(g.bed_m.size)
    water[cell] = amount
    return g.aggregate_cells(water)


def checked(g, volumes, supplied, **kwargs):
    result = g.advance(volumes, supplied, MONTH, **kwargs)
    budget = result["budget"]
    tolerance = max(1e-8, (budget["initial_m3"] + budget["supplied_m3"]) * 2e-13)
    assert budget["residual_m3"] == pytest.approx(0., abs=tolerance)
    np.testing.assert_allclose(budget["owner_residual_m3"], 0., atol=tolerance)
    assert (result["owner_stocks_m3"] >= 0.).all()
    assert (result["face_forward_m3"] >= 0.).all()
    assert (result["face_reverse_m3"] >= 0.).all()
    assert (result["boundary_exports_m3"] >= 0.).all()
    reconstructed = (result["depth_by_cell_m"] * g.area_m2).sum()
    assert reconstructed == pytest.approx(result["owner_stocks_m3"].sum(), rel=1e-12, abs=1e-8)
    return result


def test_three_owners_fill_receiving_pool_before_terminal_exports():
    g = network([0, 3, 0, 2, 0], [2, 1, 3, 1, 1], outlet=4, sill=8.)
    assert g.owner_count == 3
    assert sorted(f["sill_m"] for f in g.topology["faces"]) == [2., 3.]
    zeros = np.zeros(3)
    # Upstream source reaches first crest, fills middle below its next crest.
    partial = checked(g, zeros, source(g, 0, 10.))
    assert partial["owner_stages_m"][g.cell_owner[2]] < 2.
    assert partial["owner_stocks_m3"][g.cell_owner[2]] > 0.
    assert partial["owner_stocks_m3"][g.cell_owner[4]] == 0.
    assert partial["boundary_exports_m3"].sum() == 0.
    # Enough input can traverse both real faces, but the terminal pool must fill.
    below_outlet = checked(g, zeros, source(g, 0, 40.))
    assert 2. < below_outlet["owner_stages_m"][g.cell_owner[4]] < 8.
    assert below_outlet["boundary_exports_m3"].sum() == 0.
    overflowing = checked(g, zeros, source(g, 0, 100.))
    assert overflowing["boundary_exports_m3"].sum() > 0.
    assert overflowing["owner_stages_m"][g.cell_owner[4]] >= 8.
    assert overflowing["metadata"]["finite_interval_s"] == MONTH
    assert overflowing["metadata"]["instant_equilibrium"] is False


def test_equal_saddles_right_source_cannot_cross_dry_middle_to_left_outlet():
    g = network([0, 2, 0, 2, 0], outlet=0, sill=2.)
    result = checked(g, np.zeros(g.owner_count), source(g, 4, 3.))
    assert result["owner_stocks_m3"][g.cell_owner[2]] > 0.
    assert result["owner_stages_m"][g.cell_owner[2]] < 2.
    assert result["owner_stocks_m3"][g.cell_owner[0]] == 0.
    assert result["boundary_exports_m3"].sum() == 0.
    np.testing.assert_array_equal(result["wet_mask"], [False, False, True, False, True])


def test_withdraw_retreat_and_source_budget_no_created_water():
    g = network([0, 2, 0, 2, 0], outlet=0, sill=8.)
    filled = checked(g, np.zeros(g.owner_count), source(g, 4, 3.))
    withdrawal = np.full(g.owner_count, 100.)
    dry = checked(g, filled["owner_stocks_m3"], np.zeros(g.owner_count), withdrawal_m3=withdrawal)
    assert dry["withdrawn_m3"].sum() == pytest.approx(3.)
    assert not dry["wet_mask"].any()
    assert dry["owner_stocks_m3"].sum() == 0.
    again = checked(g, dry["owner_stocks_m3"], source(g, 4, 1.))
    assert again["owner_stocks_m3"].sum() == pytest.approx(1.)
    assert again["owner_stocks_m3"][g.cell_owner[2]] == 0.
    idle = checked(g, again["owner_stocks_m3"], np.zeros(g.owner_count))
    np.testing.assert_allclose(idle["owner_stocks_m3"], again["owner_stocks_m3"])


def test_plateau_downhill_real_edges_neighbor_order_invariant():
    bed = np.array([0., 2., 2., 2., 0., 3., 3.])
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6)]
    a = build_csr_reservoirs(bed, mesh(7, edges))
    b = build_csr_reservoirs(bed, mesh(7, edges, reverse=True))
    assert a.owner_count == 2
    np.testing.assert_array_equal(a.cell_owner, b.cell_owner)
    np.testing.assert_array_equal(a.receiver, b.receiver)
    for c in range(7):
        seen = set()
        while a.receiver[c] >= 0:
            assert c not in seen
            seen.add(c)
            target = a.receiver[c]
            assert tuple(sorted((c, int(target)))) in edges
            assert bed[target] <= bed[c]
            c = target
    flat = network([0, 0, 0])
    assert flat.owner_count == 1
    np.testing.assert_array_equal(flat.cell_owner, [0, 0, 0])
    # Owner IDs are bottom-height ordered, not necessarily physical-cell ordered.
    reversed_bottoms = network([1, 3, 0])
    leaves = reversed_bottoms.topology["arrays"]["leaf_ids"]
    for face in reversed_bottoms.topology["faces"]:
        assert [int(leaves[reversed_bottoms.cell_owner[c]]) for c in face["cell_ids"]] == face["leaf_ids"]


def test_identity_is_checked_and_no_d4_certification():
    g = network([0, 2, 0])
    assert isinstance(g.exchange, _tg()._RunoffExchange)
    assert g.topology["identity_sha256"] == _tg()._topology_identity(g.topology)
    assert g.topology["metadata"]["original_source_certified"] is False
    g.topology["faces"][0]["sill_m"] += 1.
    with pytest.raises(ValueError, match="identity mismatch"):
        _tg()._RunoffExchange(g.topology, SimpleNamespace(face_conductance_m_s=.6, boundary_conductance_m_s=.6))


def test_mask_cuts_are_not_exports_and_ocean_face_must_be_real():
    bed, graph = np.array([0., 3., 0., -1.]), mesh(4)
    mask = np.array([True, True, True, False])
    face = dict(cell_id=2, receiver_cell_id=3, sill_m=0., width_m=2., kind="ocean")
    g = build_csr_reservoirs(bed, graph, cell_mask=mask, boundary_faces=[face])
    assert len(g.topology["engineering_boundaries"]) == 1
    closed = build_csr_reservoirs(bed, graph, cell_mask=mask)
    assert not closed.topology["engineering_boundaries"]
    with pytest.raises(ValueError, match="terminal"):
        build_csr_reservoirs(bed, graph, cell_mask=mask, boundary_faces=[dict(face, cell_id=0)])
    with pytest.raises(ValueError, match="terminal"):
        build_csr_reservoirs(bed, graph, boundary_faces=[face])


def test_large_si_inventory_small_graph_and_bounded_work():
    g = network([0, 3, 0, 2, 0], np.array([2, 1, 3, 1, 1]) * 1e12, outlet=4, sill=8.,
                face_width_m=1e6)
    result = checked(g, np.zeros(g.owner_count), source(g, 0, 1e13))
    assert result["budget"]["supplied_m3"] == 1e13
    assert result["metadata"]["accepted_steps"] < 4096
    with pytest.raises(ValueError, match="step budget"):
        g.advance(np.zeros(g.owner_count), source(g, 0, 1e13), MONTH, subdivisions=8, max_steps=1)


def test_fixed_eight_substeps_qualitative_and_si_scale_invariance():
    g = network([0,3,0,2,0],[2,1,3,1,1],outlet=4,sill=8.)
    identity = g.topology['identity_sha256']
    one = g.advance(np.zeros(3),source(g,0,10.),MONTH)
    eight = g.advance(np.zeros(3),source(g,0,10.),MONTH,subdivisions=8)
    for result in (one,eight):
        assert 0 < result['owner_stages_m'][1] < 2.
        assert result['owner_stocks_m3'][2] == 0.
        assert result['budget']['exported_m3'] == 0.
        assert result['budget']['residual_m3'] == pytest.approx(0.,abs=1e-8)
    # Multiply areas, face widths and inventories by a physical factor: heads
    # and characteristic exchange time stay equal; no conductance coefficient change.
    factor=1e6
    scaled=network([0,3,0,2,0],np.array([2,1,3,1,1])*factor,outlet=None,face_width_m=factor)
    base=network([0,3,0,2,0],[2,1,3,1,1],outlet=None)
    a=base.advance(np.zeros(3),source(base,0,10.),MONTH)
    b=scaled.advance(np.zeros(3),source(scaled,0,10.*factor),MONTH)
    np.testing.assert_allclose(a['owner_stages_m'],b['owner_stages_m'],atol=1e-9)
    np.testing.assert_allclose(a['owner_stocks_m3']*factor,b['owner_stocks_m3'],rtol=1e-9)
    assert g.topology['identity_sha256']==identity
    assert one['metadata']['scaled_topology_identity_sha256']!=identity


def test_high_absolute_bed_tiny_inventory_keeps_relative_depth_volume():
    g=network([380.,450.,380.],area=1e8)
    inventory=source(g,0,1e-6)
    geometry=g.geometry_at_volumes(inventory)
    assert geometry['volume_by_cell_m3'].sum()==pytest.approx(1e-6,rel=1e-14)
    assert geometry['wet_mask'][0]
    assert geometry['depth_by_cell_m'][0]==pytest.approx(1e-14,rel=1e-14)
    np.testing.assert_allclose(geometry['depth_by_cell_m'],geometry['stage_by_cell_m']-g.bed_m,atol=1e-8)
