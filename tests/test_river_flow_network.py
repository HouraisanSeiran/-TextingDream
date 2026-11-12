"""Tiny synthetic supplied receiver graphs only: no world runs or new routing."""
import numpy as np
import pytest

from app.world_gen.river_flow_network import build_flow_network


def network(q, receiver=None, **kwargs):
    q = np.asarray(q, float)
    n = q.shape[-1]
    if receiver is None:
        receiver = np.r_[np.arange(1, n), -1]
    # Every fixture uses edges toward a larger cell index (TG downstream-first).
    grid = kwargs.pop('grid', dict(shape_zx=(1, n), first_xz_m=(5000., -5000.), spacing_m=10000.))
    return build_flow_network(receiver, np.arange(n - 1, -1, -1), q.reshape((12,) + tuple(grid['shape_zx'])),
                              kwargs.pop('area_m2', np.full(n, 1e10)), grid, **kwargs)


def test_equal_area_wet_dry_and_finite_year_classes():
    q = np.zeros((12, 8))
    q[:, 0] = 1; q[:3, 2] = 1; q[:1, 4] = 1
    result = network(q, receiver=[1, -1, 3, -1, 5, -1, 7, -1])
    by_cell = {v['anchor_cell']: v for v in result['vectors']}
    assert [by_cell[i]['flow_class'] for i in (0, 2, 4, 6)] == [
        'perennial', 'seasonal', 'intermittent', 'dry_valley']
    assert [by_cell[i]['active_month_count'] for i in (0, 2, 4, 6)] == [12, 3, 1, 0]
    assert not any(v['blue'] for v in result['vectors'])
    assert not any(6 in d['edge_anchor_cells'] for month in result['draw_segments'] for d in month)
    assert 'NOT long-term' in result['classification_scope']


def test_upstream_water_crosses_dry_land_then_loss_breaks_blue_not_topology():
    q = np.tile([.01, 2., 2., 0., 3., 0.], (12, 1))
    result = network(q)
    assert len(result['vectors']) == 1
    assert result['vectors'][0]['nodes'] == list(range(6))
    assert [d['edge_anchor_cells'] for d in result['draw_segments'][0]] == [[1, 2], [4]]
    assert result['vectors'][0]['monthly_q_m3_s'] == [.01] * 12
    np.testing.assert_equal(result['vectors'][0]['edge_monthly_q_m3_s'][3], [0.] * 12)


def test_original_mesh_and_junction_topology_stable_across_months():
    q = np.zeros((12, 5)); q[:3] = 1; q[8] = 2
    rec = [2, 2, 3, 4, -1]
    coords = np.array([[5, 7], [11, 13], [22, 16], [19, 31], [45, 27]], float)
    a = network(q, rec, cell_coords_xz_m=coords)
    b = network(np.roll(q, 1, axis=0), rec, cell_coords_xz_m=coords)
    assert [v['id'] for v in a['vectors']] == [v['id'] for v in b['vectors']]
    by_id = {v['id']: v for v in a['vectors']}
    for v in a['vectors']:
        np.testing.assert_array_equal(v['points_xz_m'], coords[v['nodes']])
        assert v['monthly_q_m3_s'] == q[:, v['anchor_cell']].tolist()
        if v['downstream_id']:
            assert v['id'] in by_id[v['downstream_id']]['upstream_ids']
            assert v['nodes'][-1] == by_id[v['downstream_id']]['anchor_cell']
        for upstream in v['upstream_ids']:
            assert by_id[upstream]['downstream_id'] == v['id']
    assert all(d['parent_id'] in by_id for m in a['draw_segments'] for d in m)
    assert a['identity'] != b['identity']


def test_absolute_grid_source_ids_agree_for_shifted_window():
    a = network(np.ones((12, 4)))
    b = network(np.ones((12, 3)), grid=dict(shape_zx=(1, 3), first_xz_m=(15000., -5000.), spacing_m=10000.))
    # Compare same physical head cell after an upstream cell has no candidacy.
    c = network(np.tile([0., 1., 1., 1.], (12, 1)), area_m2=np.zeros(4))
    assert c['vectors'][0]['id'] == b['vectors'][0]['id']
    assert a['vectors'][0]['id'] != b['vectors'][0]['id']


def test_monthly_lake_cut_no_chord_and_only_actual_release():
    q = np.ones((12, 6)); q[:, 3] = 0
    wet = np.zeros((12, 1, 6), bool); wet[0, 0, 1:4] = True
    result = network(q, monthly_wet_lake=wet)
    month = result['draw_segments'][0]
    assert [d['edge_anchor_cells'] for d in month] == [[0], [4]]
    assert month[0]['to_lake'] and not month[1]['from_lake']
    assert month[0]['points_xz_m'][-1] == [10000., -5000.]
    assert len(result['draw_segments'][1]) == 2  # zero edge still splits non-lake month
    q[:, 3] = .2
    released = network(q, monthly_wet_lake=wet)
    exit_piece = next(d for d in released['draw_segments'][0] if d['from_lake'])
    assert exit_piece['edge_anchor_cells'] == [3, 4]
    assert exit_piece['edge_q_m3_s'] == [.2, 1.]
    assert exit_piece['points_xz_m'][0] == [40000., -5000.]
    assert not any(set(d['edge_anchor_cells']) & {1, 2} for d in released['draw_segments'][0])
    assert [v['id'] for v in result['vectors']] == [v['id'] for v in released['vectors']]


def test_nan_is_unknown_not_dry_and_negative_refused():
    q = np.ones((12, 3)); q[2, 0] = np.nan
    result = network(q)
    v = result['vectors'][0]
    assert v['flow_class'] == 'unknown' and v['known_months'] == 11
    assert v['monthly_q_m3_s'][2] is None and v['annual_mean_q_m3_s'] is None
    assert all(0 not in d['edge_anchor_cells'] for d in result['draw_segments'][2])
    assert q[2, 0] != q[2, 0]  # caller input untouched
    q[0, 1] = -1
    with pytest.raises(ValueError, match='nonnegative'):
        network(q)
    q[0, 1] = np.inf
    with pytest.raises(ValueError, match='nonnegative'):
        network(q)


def test_month_seconds_annual_volume_day_weighting_and_threshold_identity():
    q = np.repeat(np.arange(1., 13.)[:, None], 3, axis=1)
    days = np.array([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    r = network(q, month_days=days)
    v = r['vectors'][0]
    assert v['annual_volume_m3'] == pytest.approx(np.dot(q[:, 0], days * 86400))
    assert v['annual_mean_q_m3_s'] == pytest.approx(np.dot(q[:, 0], days) / days.sum())
    assert v['min_q_m3_s'] == 1 and v['max_q_m3_s'] == 12
    changed = network(q, month_days=days, min_active_q_m3_s=2)
    assert changed['identity'] != r['identity']
    assert changed['vectors'][0]['id'] == v['id']
    ten = np.ones((12, 2)); ten[-2:] = 0
    assert network(ten)['vectors'][0]['flow_class'] == 'seasonal'
    assert network(ten, perennial_months=10)['vectors'][0]['flow_class'] == 'perennial'


def test_no_downstream_active_forcing_ocean_suppression_and_budget_refusal():
    q = np.zeros((12, 5)); q[:, 0] = 2; q[:, 3] = 1
    r = network(q, area_m2=np.zeros(5), ocean=[False, False, False, True, True])
    assert len(r['vectors']) == 1 and r['vectors'][0]['nodes'] == [0, 1]
    assert r['vectors'][0]['downstream_id'] is None
    assert r['draw_segments'][0][0]['edge_anchor_cells'] == [0]
    with pytest.raises(ValueError, match='max_segments'):
        network(np.ones((12, 5)), [2, 2, 3, 4, -1], max_segments=1)
    with pytest.raises(ValueError, match='cycle|order'):
        network(np.ones((12, 3)), [1, 0, -1])


def test_monthly_slices_also_obey_segment_budget():
    q = np.tile([1., 0., 1., 0., 1., 0.], (12, 1))
    with pytest.raises(ValueError, match='monthly draw slices'):
        network(q, max_segments=2)


def test_zero_display_area_preserves_default_vectors_draws_and_identity():
    q=np.tile([1.,2.,0.,3.,4.,0.],(12,1))
    a=network(q)
    b=network(q,min_display_area_m2=0.)
    assert a==b


def test_display_area_omits_small_active_rivers_without_changing_q_or_width():
    q=np.tile([1.,0.,2.,0.],(12,1)); original=q.copy()
    receiver=[1,-1,3,-1]; area=np.array([1e8,1e8,2e10,2e10])
    a=network(q,receiver,area_m2=area,dry_valley_min_area_m2=1e30)
    b=network(q,receiver,area_m2=area,min_display_area_m2=1e10,dry_valley_min_area_m2=1e30)
    assert len(a['vectors'])==2 and len(b['vectors'])==1
    assert b['vectors'][0]==next(v for v in a['vectors'] if v['anchor_cell']==2)
    assert b['summary']['raw_active_edge_count']==2
    assert b['summary']['display_omitted_active_edges']==1
    assert b['draw_segments'][0][0]['edge_q_m3_s']==[2.]
    assert b['draw_segments'][0][0]['symbol_width']==1.
    np.testing.assert_array_equal(q,original)
    with pytest.raises(ValueError,match='threshold'):
        network(q,min_display_area_m2=-1.)


def test_display_filter_also_constrains_dry_valley_without_turning_it_blue():
    hidden=network(np.zeros((12,2)),area_m2=np.full(2,2e10),min_display_area_m2=1e30)
    assert not hidden['vectors']
    visible=network(np.zeros((12,2)),area_m2=np.full(2,2e10),min_display_area_m2=1e10)
    assert len(visible['vectors'])==1
    assert visible['vectors'][0]['flow_class']=='dry_valley'
    assert not visible['draw_segments'][0]


def test_tg_explicit_mask_keeps_confluence_tail_and_single_edge():
    q = np.ones((12, 5)); q[:, 3] = 0
    r = network(q, [2, 2, 3, 4, -1], area_m2=np.zeros(5), cartography_profile='all-active')
    by_head = {v['anchor_cell']: v for v in r['vectors']}
    assert by_head[0]['nodes'] == [0, 2]
    assert by_head[1]['nodes'] == [1, 2]
    assert by_head[2]['nodes'] == [2, 3]
    assert by_head[0]['downstream_id'] == by_head[2]['id']
    assert by_head[2]['end_reason'] == 'gate_cut'
    assert sorted(a for v in r['draw_segments'][0] for a in v['edge_anchor_cells']) == [0, 1, 2]
    assert all(len(v['points_xz_m']) == 2 for v in r['draw_segments'][0])
    assert not any(3 in v['edge_anchor_cells'] for v in r['vectors'])


def test_fixed_mainstem_length_restores_head_not_small_twig_or_known_zero():
    # 0->1->2->4->5 is long; 3->4 is a short tributary, 5 has known zero.
    r = network(np.tile([1., 1., 1., 1., 1., 0., 1.], (12, 1)),
        [1, 2, 4, 4, 5, 6, -1], area_m2=np.zeros(7), cartography_profile='overview-mainstem-30km')
    assert r['vectors'][0]['nodes'] == [0, 1, 2, 4, 5]
    assert r['summary']['display_candidate_edge_count'] == 4
    assert r['summary']['raw_active_edge_count'] == 5
    assert r['summary']['display_omitted_active_edges'] == 1
    assert r['vectors'][0]['end_reason'] == 'gate_cut'
    assert r['cartography']['min_mainstem_length_m'] == 30000.


def test_cartographic_profile_keeps_wet_unknown_boundary_and_input_unchanged():
    q = np.ones((12, 6)); q[:, 2:4] = np.nan
    wet = np.zeros((12, 1, 6), bool); wet[:, 0, 2:4] = True
    original = q.copy()
    r = network(q, monthly_wet_lake=wet, area_m2=np.zeros(6), cartography_profile='all-active')
    draws = sorted(r['draw_segments'][0], key=lambda d: d['anchor_cell'])
    assert [d['edge_anchor_cells'] for d in draws] == [[0, 1], [4]]
    assert draws[0]['to_lake'] and draws[0]['points_xz_m'][-1] == [20000., -5000.]
    np.testing.assert_equal(q, original)
    with pytest.raises(ValueError, match='min_display_area'):
        network(q, cartography_profile='all-active', min_display_area_m2=1.)
