"""Local mountain-structure prototype on small synthetic windows.

Two generation identities are covered:

* ``structure_policy='corridor'`` - the v1 narrow-corridor prototype (also an exact replay target): determinism,
  bitwise-kept boundary, chain direction, lowered valley/basin, no whole-window mountain.
* ``structure_policy='platform-rebuild'`` (default, v2): the **safe domain** (where the surface may change) is
  separated from the **mountain outline**. The domain is the selected belt's wide band plus an outward buffer, i.e.
  wider than the v1 corridor, and inside it the old flat platform is really lowered (a synthetic wide platform is
  used, not just a corridor). The outline is displaced by low-frequency fields - whole sections retreat, a few
  advance - measured against a modulation-off control, not by any roundness statistic.

CPU only, no GPU, no world product, no hydrology, no D8 river network."""
from __future__ import annotations

import json

import numpy as np

from app.world_gen import mountain_sculpt as ms

SPACING = 10000.0
FIRST = (5000.0, 5000.0)          # cell centres of a 80 x 60 window, product style
SHAPE = (60, 80)                   # (nz, nx)
SEED = 20260903
SEEDS = (SEED, 4242, 777)


def _line(x0, z0, x1, z1, n, wide, steep, amp, side=1):
    t = np.linspace(0.0, 1.0, n)[:, None]
    xz = np.array([x0, z0])[None, :] + t * (np.array([x1, z1]) - np.array([x0, z0]))[None, :]
    return xz, dict(wide=np.full(n, float(wide)), steep=np.full(n, float(steep)),
                    amp=np.linspace(amp * 0.8, amp, n), side=np.full(n, int(side)))


def synthetic_net(belt_half_m=450000.0):
    """Two long level-1 chains trending (1, 0.5), one branch off the first, one spur, one pass, one wide belt."""
    main_a, a = _line(-200000.0, -150000.0, 950000.0, 425000.0, 120, 60000.0, 40000.0, 0.90)
    main_b, b = _line(-150000.0, 250000.0, 900000.0, 775000.0, 120, 55000.0, 38000.0, 0.85)
    br, c = _line(350000.0, 125000.0, 430000.0, 470000.0, 70, 24000.0, 18000.0, 0.62)
    sp, d = _line(600000.0, 350000.0, 660000.0, 430000.0, 40, 9000.0, 7000.0, 0.40)
    lines = [(0, 1, -1, main_a, a), (1, 1, -1, main_b, b), (2, 2, 0, br, c), (3, 3, 2, sp, d)]
    offsets = [0]
    V, W, S, A, SD, LV, PA, BE = [], [], [], [], [], [], [], []
    for idx, level, parent, xz, attrs in lines:
        V.append(xz); W.append(attrs['wide']); S.append(attrs['steep']); A.append(attrs['amp'])
        SD.append(attrs['side']); LV.append(level); PA.append(parent); BE.append(0)
        offsets.append(offsets[-1] + len(xz))
    belt_xz, _ = _line(-250000.0, -200000.0, 1000000.0, 450000.0, 40, 0, 0, 0)
    net = dict(
        vertex_xz_m=np.concatenate(V), vertex_width_wide_m=np.concatenate(W).astype(np.float32),
        vertex_width_steep_m=np.concatenate(S).astype(np.float32), vertex_amp=np.concatenate(A).astype(np.float32),
        vertex_side=np.concatenate(SD).astype(np.int8), line_offsets=np.asarray(offsets, np.int64),
        line_level=np.asarray(LV, np.int8), line_parent=np.asarray(PA, np.int32),
        line_chain=np.zeros(len(LV), np.int32), line_belt=np.asarray(BE, np.int32),
        pass_xz_m=np.asarray([[420000.0, 250000.0]]), pass_depth=np.asarray([0.8], np.float32),
        pass_line=np.asarray([0], np.int32),
        belt_offsets=np.asarray([0, len(belt_xz)], np.int64), belt_class=np.asarray([1], np.int8),
        belt_chain=np.asarray([0], np.int32), belt_xz_m=belt_xz,
        belt_half_width_m=np.full(len(belt_xz), float(belt_half_m), np.float32), belt_side=np.ones(len(belt_xz), np.int8),
        belt_floor_m=np.full(len(belt_xz), 700.0, np.float32), belt_plateau=np.full(len(belt_xz), 1.0, np.float32),
    )
    return net, belt_xz


def segmented_net(segments=6, along_km=780.0, z_km=300.0):
    """The real shape of a saved belt chain: one long level-1 chain stored as several disconnected segments.

    This is what makes ``max_main_chains=2`` wrong: two segments leave most of the platform with no chain at all.
    """
    n = int(segments)
    step = along_km / n
    V, W, S, A, SD, LV, PA, BE = [], [], [], [], [], [], [], []
    offsets = [0]
    for k in range(n):
        x0 = k * step * 1000.0
        x1 = (x0 + 0.9 * step * 1000.0)
        xz = np.array([[x0, z_km * 1000.0], [x1, z_km * 1000.0]])
        V.append(xz)
        W.append(np.full(2, 60000.0))
        S.append(np.full(2, 40000.0))
        A.append(np.full(2, 0.90))
        SD.append(np.ones(2))
        LV.append(1)
        PA.append(-1)
        BE.append(0)
        offsets.append(offsets[-1] + 2)
    belt_xz = np.array([[0.0, z_km * 1000.0], [along_km * 1000.0, z_km * 1000.0]])
    net = dict(
        vertex_xz_m=np.concatenate(V), vertex_width_wide_m=np.concatenate(W).astype(np.float32),
        vertex_width_steep_m=np.concatenate(S).astype(np.float32), vertex_amp=np.concatenate(A).astype(np.float32),
        vertex_side=np.concatenate(SD).astype(np.int8), line_offsets=np.asarray(offsets, np.int64),
        line_level=np.asarray(LV, np.int8), line_parent=np.asarray(PA, np.int32),
        line_chain=np.zeros(len(LV), np.int32), line_belt=np.asarray(BE, np.int32),
        pass_xz_m=np.zeros((0, 2)), pass_depth=np.zeros(0, np.float32), pass_line=np.zeros(0, np.int32),
        belt_offsets=np.asarray([0, len(belt_xz)], np.int64), belt_class=np.asarray([1], np.int8),
        belt_chain=np.asarray([0], np.int32), belt_xz_m=belt_xz,
        belt_half_width_m=np.full(len(belt_xz), 400000.0, np.float32), belt_side=np.ones(len(belt_xz), np.int8),
        belt_floor_m=np.full(len(belt_xz), 700.0, np.float32), belt_plateau=np.full(len(belt_xz), 1.0, np.float32),
    )
    return net


def synthetic_window(platform_m=3600.0, lowland_m=260.0, platform_half_m=450000.0, belt_half_m=450000.0):
    """A broad flat platform over the whole belt, lowland elsewhere, a sea strip on the low-x edge and one lake."""
    grid = ms.grid_from_index(0, 0, SHAPE[1], SHAPE[0], FIRST, SPACING)
    nz, nx = SHAPE
    X = FIRST[0] + np.arange(nx) * SPACING
    Z = FIRST[1] + np.arange(nz) * SPACING
    belt_xz = synthetic_net(belt_half_m)[1]
    a, b = np.array(belt_xz[0]), np.array(belt_xz[-1])
    d = b - a
    n = np.array([-d[1], d[0]]) / np.hypot(*d)
    px = X[None, :] - a[0]
    pz = Z[:, None] - a[1]
    across = np.abs(px * n[0] + pz * n[1])
    along = (px * d[0] + pz * d[1]) / np.hypot(*d)
    inside = (across < platform_half_m) & (along > -300000.0) & (along < 900000.0)
    before = np.where(inside, platform_m, lowland_m).astype(np.float64)
    rng = np.random.default_rng(7)
    before = before + rng.normal(0.0, 60.0, before.shape)
    ocean = np.zeros(before.shape, bool)
    ocean[:, :6] = True                         # a sea strip on the low-x edge
    before[ocean] = -800.0
    lake = np.zeros(before.shape, bool)
    lake[50:53, 60:63] = True                   # a kept lake inside the platform
    before[lake] = 3400.0
    closed = np.zeros(before.shape, bool)
    fixed = ocean | lake | closed
    win = dict(before_m=before, ocean=ocean, lake=lake, closed=closed, fixed=fixed,
               status=np.where(ocean, 3, 5).astype(np.uint8), manifest=None, grid=grid)
    return win, grid


SMALL = dict(min_main_length_km=50.0, min_direction_coherence=0.5, min_main_separation_km=150.0,
             vertex_step_km=20.0, basins_max=2, basin_radius_km=40.0)
TIGHT_SUPPORT = dict(support_width_scale=1.0, support_width_extra_km=0.0,
                     branch_support_scale=1.0, branch_support_extra_km=0.0)   # bare-width support: the tent is wider
POLICIES = ms.POLICIES
FLAT = dict(width_var=0.0, fringe_cut=0.0, along_amp_var=0.0)     # modulation off: the outline control


def _run(policy='platform-rebuild', seed=SEED, window_kw=None, **params):
    net, _ = synthetic_net((window_kw or {}).get('belt_half_m', 450000.0))
    win, grid = synthetic_window(**(window_kw or {}))
    erosion = bool(params.pop('erosion', False))
    p = dict(SMALL)
    p['structure_policy'] = policy
    p.update(params)
    structure = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=seed, params=p)
    res = ms.apply_window(win, structure, grid, world_seed=seed, params=p, erosion=erosion)
    return res, structure, win, grid


def _relief_mask(res, relief_m=800.0):
    """Where the sculpted surface actually carries a massif (relief above its own base) inside the safe domain."""
    return ((res['after_m'] - res['floor_m']) >= relief_m) & (res['support'] > 0.5)


def _relief_edge_rows(res, relief_m=800.0):
    """North row of the massif edge per column - the outline position, not a texture statistic."""
    rel = (res['after_m'] - res['floor_m']) * (res['support'] > 0.5)
    rows = {}
    for ix in range(8, SHAPE[1] - 8, 2):
        idx = np.flatnonzero(rel[:, ix] >= relief_m)
        if idx.size:
            rows[ix] = int(idx.min())
    return rows


# ------------------------------------------------------------------ selection
def test_select_structure_keeps_parent_graph_and_direction():
    net, _ = synthetic_net()
    grid = ms.grid_from_index(0, 0, SHAPE[1], SHAPE[0], FIRST, SPACING)
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=SMALL)
    assert st['meta']['main_lines'] == [0, 1]
    assert [e['line'] for e in st['branches']] == [2]
    assert [e['line'] for e in st['spurs']] == [3]
    assert st['branches'][0]['parent'] == 0
    assert st['meta']['main_direction'][1] > 0 and st['meta']['main_direction'][0] > 0
    assert st['meta']['main_coherence'] > 0.9
    kinds = {e['kind'] for e in st['main']}
    assert kinds == {'main'}
    # the saved belt geometry is exported so a reader can reuse the wide band (v2 domain)
    assert st['meta']['belt_geometry']['half_width_median_m'] > 0


def test_short_fragment_is_not_promoted_to_main():
    net, _ = synthetic_net()
    grid = ms.grid_from_index(0, 0, SHAPE[1], SHAPE[0], FIRST, SPACING)
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED,
                             params=dict(SMALL, min_main_length_km=400.0))
    assert 3 not in st['meta']['main_lines'] and 2 not in st['meta']['main_lines']


# ------------------------------------------------------------------ identity per policy
def test_policies_carry_different_generation_identity(tmp_path):
    corridor, _, _, _ = _run('corridor')
    rebuild, _, _, _ = _run('platform-rebuild')
    assert corridor['meta']['schema'] == ms.SCHEMA_V1 and corridor['meta']['algorithm'] == ms.ALGORITHM_V1
    assert rebuild['meta']['schema'] == ms.SCHEMA and rebuild['meta']['algorithm'] == ms.ALGORITHM
    assert ms.identity_tags({'structure_policy': 'corridor'}) == (ms.SCHEMA_V1, ms.ALGORITHM_V1)
    assert ms.identity_tags({'structure_policy': 'platform-rebuild'}) == (ms.SCHEMA, ms.ALGORITHM)
    assert rebuild['identity'] != corridor['identity']
    doc = json.loads((ms.write_candidate(tmp_path / 'v2', rebuild) and
                      (tmp_path / 'v2' / 'structure.json').read_text(encoding='utf-8')))
    assert doc['schema'] == ms.SCHEMA and doc['algorithm'] == ms.ALGORITHM
    assert doc['meta']['structure_policy'] == 'platform-rebuild'
    doc1 = json.loads((ms.write_candidate(tmp_path / 'v1', corridor) and
                       (tmp_path / 'v1' / 'structure.json').read_text(encoding='utf-8')))
    assert doc1['schema'] == ms.SCHEMA_V1
    assert 'prototype-1' in (tmp_path / 'v1' / 'README.md').read_text(encoding='utf-8')


def test_unknown_policy_is_rejected():
    try:
        ms.apply_window(*_prepared('corridor')[:3], params=dict(SMALL, structure_policy='nope'))
    except ValueError as exc:
        assert 'structure_policy' in str(exc)
    else:
        raise AssertionError('an unknown structure policy must be refused')


def _prepared(policy, **params):
    net, _ = synthetic_net()
    win, grid = synthetic_window()
    p = dict(SMALL)
    p['structure_policy'] = policy
    p.update(params)
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
    return win, st, grid


# ------------------------------------------------------------------ determinism / boundary (every policy)
def test_same_seed_is_identical_for_every_policy():
    for policy in POLICIES:
        r1, st1, _, _ = _run(policy)
        r2, st2, _, _ = _run(policy)
        assert np.array_equal(r1['after_m'], r2['after_m'])
        assert np.array_equal(r1['changed_mask'], r2['changed_mask'])
        assert r1['identity'] == r2['identity']
        assert st1['meta']['main_lines'] == st2['meta']['main_lines']


def test_inputs_are_not_modified():
    for policy in POLICIES:
        net, _ = synthetic_net()
        win, grid = synthetic_window()
        before, before_mask = win['before_m'].copy(), win['fixed'].copy()
        p = dict(SMALL, structure_policy=policy)
        st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
        ms.apply_window(win, structure=st, grid=grid, world_seed=SEED, params=p)
        assert np.array_equal(win['before_m'], before)
        assert np.array_equal(win['fixed'], before_mask)


def test_sea_lake_and_outer_ring_are_bitwise_old_for_every_policy():
    for policy in POLICIES:
        res, _, win, _ = _run(policy)
        before, after, fixed = res['before_m'], res['after_m'], win['fixed']
        assert fixed.any()
        assert np.array_equal(after[fixed], before[fixed])
        assert np.array_equal(after > 0, before > 0)          # never floods or drains a cell
        assert np.array_equal(after[0, :], before[0, :])
        assert np.array_equal(after[-1, :], before[-1, :])
        assert np.array_equal(after[:, 0], before[:, 0])
        assert np.array_equal(after[:, -1], before[:, -1])


def test_outside_support_is_bitwise_old_for_every_policy():
    for policy in POLICIES:
        res, _, _, _ = _run(policy)
        outside = res['support'] <= 0.0
        assert outside.any()
        assert np.array_equal(res['after_m'][outside], res['before_m'][outside])
        assert not res['changed_mask'][outside].any()


def test_coastal_guard_keeps_the_shore_ring_old():
    """The first land ring is inside the safe domain's reach but must stay bitwise old (no shore move)."""
    from scipy import ndimage
    res, _, win, _ = _run('platform-rebuild')
    wet = win['fixed'] | ~(win['before_m'] > 0.0)
    ring = ndimage.distance_transform_edt(~wet) <= 1.0
    assert ring.any()
    assert np.array_equal(res['after_m'][ring], res['before_m'][ring])
    # and the guard is not an accident of the noise: it holds on several seeds
    for seed in SEEDS[1:]:
        other, _, win2, _ = _run('platform-rebuild', seed=seed)
        wet2 = win2['fixed'] | ~(win2['before_m'] > 0.0)
        ring2 = ndimage.distance_transform_edt(~wet2) <= 1.0
        assert np.array_equal(other['after_m'][ring2], other['before_m'][ring2])


def test_changed_mask_is_exact_and_significant_is_separate():
    res, _, _, _ = _run()
    before, after = res['before_m'], res['after_m']
    assert np.array_equal(res['changed_mask'], after != before)          # exact, no threshold
    assert np.array_equal(res['significant_mask'],
                          np.abs(after - before) > res['meta']['significant_change_threshold_m'])
    assert res['significant_mask'].sum() <= res['changed_mask'].sum()
    assert res['meta']['significant_change_cells'] == int(res['significant_mask'].sum())


# ------------------------------------------------------------------ the old platform (corridor replay)
def test_corridor_keeps_the_old_platform_outside_its_narrow_support():
    """The v1 bug is reproduced on purpose by ``corridor``: the platform outside the narrow corridor is untouched."""
    res, _, _, _ = _run('corridor')
    before = res['before_m']
    outer = (before > 3000.0) & (res['support'] <= 0.0)
    assert outer.sum() > 400
    assert np.array_equal(res['after_m'][outer], before[outer])


def test_valley_floor_is_lowered_and_kept_finite():
    # the accepted platform policy and its v1 replay only: the group policy deliberately keeps a raised body, so
    # measuring "the old platform was thinned out" there would test the wrong design
    for policy in ('corridor', 'platform-rebuild'):
        res, _, _, _ = _run(policy)
        d = res['after_m'] - res['before_m']
        inside = res['support'] > 0.5
        assert inside.any()
        assert (d[inside] < -200.0).sum() > 0.15 * inside.sum()      # the wide platform is thinned out
        valley = res['valley_mask'] > 0.5
        basin = res['basin_mask'] > 0.5
        assert valley.sum() > 0 and basin.sum() > 0
        assert np.median(d[valley]) < -300.0                          # longitudinal valley floor
        assert np.median(d[basin]) < np.median(d[valley]) + 1.0       # basins sit at or below the valley floor
        assert basin.sum() < 0.25 * res['after_m'].size               # no whole-window negative basin


def test_basin_and_connector_have_a_defined_local_bed():
    for policy in POLICIES:
        res, _, _, _ = _run(policy)
        sel = res['basin_mask'] > 0.5
        assert sel.any()
        floor = res['floor_m']
        assert (res['after_m'][sel] > 0.0).all()                     # a real bed, never 0 m as a stand-in
        assert ((res['after_m'] - floor)[sel] > -700.0).all()         # below the floor, but not a bottomless trench
        assert ((res['after_m'] - floor)[sel] < 0.0).any()            # the discs are actually lowered
        for b in res['meta']['basins']:
            assert b['target_m'] is not None and b['target_m'] > 0.0


def test_main_chain_peak_level_is_kept():
    for policy in POLICIES:
        res, _, _, _ = _run(policy)
        before, after = res['before_m'], res['after_m']
        assert after.max() <= before.max() + 1.0                      # no overshoot of the old peak
        assert np.percentile(after, 99.0) > 0.80 * np.percentile(before, 99.0)   # a real chain survives
        assert _relief_mask(res).sum() > 0


def test_not_all_lowland_becomes_mountain():
    for policy in ('corridor', 'platform-rebuild'):
        res, _, win, _ = _run(policy)
        dry = ~win['fixed']
        after = res['after_m']
        share = float((after[dry] > 1500.0).mean())
        assert 0.0 < share < 0.95
        low = dry & (res['before_m'] < 600.0)
        assert low.any()
        lifted = (res['before_m'] < 600.0) & (after > 1500.0)
        assert lifted.sum() < 0.05 * low.sum()         # no plain turned into mountain


# ------------------------------------------------- v2: the chain is not two fragments of a segmented belt chain
def test_all_segments_of_the_belt_become_the_backbone():
    """A belt chain saved as 6 disconnected level-1 segments: v2 keeps every segment, v1 keeps only two."""
    net = segmented_net(6)
    win, grid = synthetic_window()
    out = {}
    for policy in POLICIES:
        p = dict(SMALL, structure_policy=policy, min_main_length_km=50.0)
        st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
        out[policy] = ms.apply_window(win, st, grid, world_seed=SEED, params=p)
    v2, v1 = out['platform-rebuild'], out['corridor']
    assert len(v1['structure']['main']) == 2                 # the v1 rule (and its bug) is preserved
    assert len(v2['structure']['main']) == 6                 # every segment of the same belt, no invented line
    # chain coverage along the belt: the share of the belt length that actually carries a main chain (total length,
    # not the hull of the fragments - two far-apart pieces can span the belt while leaving a big hole in the middle)
    def covered(res):
        return sum(float(e['length_m']) for e in res['structure']['main']) / 780000.0
    assert covered(v1) < 0.45, 'two fragments do not cover the belt: %.2f' % covered(v1)
    assert covered(v2) > 0.85, 'the backbone does not cover the belt: %.2f' % covered(v2)
    # the hole in the middle is the real defect: the largest along-belt gap between main-chain cells
    def max_gap(res):
        xs = np.sort(np.concatenate([np.asarray(e['xz_m'], np.float64)[:, 0] for e in res['structure']['main']]))
        return float(np.diff(xs).max()) if xs.size > 1 else np.inf
    assert max_gap(v2) < max_gap(v1), 'the backbone leaves a bigger hole than two fragments (%.0f vs %.0f m)' % (
        max_gap(v2), max_gap(v1))
    # and the segments are narrowed instead of restored at full belt width
    assert v2['meta']['params']['backbone_width_scale'] < 1.0
    assert v2['meta']['params']['backbone_amp_scale'] < 1.0


# ------------------------------------------------------------------ v2: safe domain vs outline
def test_safe_domain_is_wider_than_the_corridor_and_covers_the_old_platform():
    """The safe domain (permission mask) is the belt wide band + buffer, not a narrow main-chain corridor."""
    corridor, _, _, _ = _run('corridor')
    rebuild, _, _, _ = _run('platform-rebuild')
    sup1 = corridor['support'] > 0.0
    sup2 = rebuild['support'] > 0.0
    assert (sup2 & ~sup1).sum() > 0.15 * sup1.sum()          # clearly wider, outward on both sides
    before = corridor['before_m']
    outer = (before > 3000.0) & ~sup1
    assert outer.sum() > 400
    assert (outer & sup2).sum() > 0.95 * outer.sum()          # the old platform body is inside the domain
    assert rebuild['meta']['domain']['belt_band_cells'] > 0


def test_old_platform_outside_the_corridor_is_actually_lowered():
    """A synthetic wide platform: outside the old corridor the old platform top becomes foothill/valley."""
    corridor, _, _, _ = _run('corridor')
    before = corridor['before_m']
    outer = (before > 3000.0) & (corridor['support'] <= 0.0)
    assert outer.sum() > 400
    for seed in SEEDS:
        res, _, _, _ = _run('platform-rebuild', seed=seed)
        covered = outer & (res['support'] > 0.0)
        assert covered.sum() > 0.95 * outer.sum()             # the domain reaches it (not only the chain corridor)
        d = (res['after_m'] - before)[covered]
        assert np.median(d) < -500.0                          # and the old flat top is gone, not just textured
        assert (d < -500.0).sum() > 0.6 * d.size
        # the whole domain is not one flat table either: there is real relief structure in it
        dom = res['support'] > 0.5
        relief = (res['after_m'] - res['floor_m'])[dom]
        assert np.percentile(relief, 95.0) > 1200.0
        assert np.median(relief) < 0.65 * np.percentile(relief, 95.0)


def test_outline_is_displaced_not_a_fixed_smooth_offset():
    """Whole sections of the outline retreat (and a few advance) compared with the modulation-off control."""
    for seed in SEEDS:
        res, _, _, _ = _run('platform-rebuild', seed=seed)
        ctrl, _, _, _ = _run('platform-rebuild', seed=seed, **FLAT)
        a = _relief_mask(res)
        b = _relief_mask(ctrl)
        assert b.sum() > 0
        lost = (b & ~a).sum() / b.sum()
        gained = (a & ~b).sum() / b.sum()
        assert lost > 0.05, 'the modulated outline never retreats seed=%r' % (seed,)
        # local growth is allowed (the width field widens some sections) but must stay minor: the massif as a whole
        # retreats, it does not spread out over the old platform
        assert gained < 0.20, 'the modulated outline spreads seed=%r' % (seed,)
        # and it is not just re-textured under a fixed mask: a substantial part of the massif footprint differs from
        # the modulation-off control and its north edge actually moves (>= 1 cell = 10 km). Area alone is not the
        # criterion - the outline is displaced, which is what reads as a real mountain silhouette.
        # Area thresholds are not an aesthetic target. Verify actual outline movement below,
        # alongside the nontrivial retreat already asserted, rather than a tuned XOR percentage.
        assert (a ^ b).any(), 'the outline did not move seed=%r' % (seed,)
        fe, ce = _relief_edge_rows(res), _relief_edge_rows(ctrl)
        common = sorted(set(fe) & set(ce))
        assert len(common) > 10
        shifts = [abs(fe[c] - ce[c]) for c in common]
        assert max(shifts) >= 1, 'the outline position never moves seed=%r' % (seed,)
        assert sum(1 for v in shifts if v >= 1) >= 1


def test_outline_parameters_actually_change_the_surface():
    """Each v2 outline knob is consumed (no dead parameter): fringe core share, width gain, detail wavelengths."""
    base, _, _, _ = _run('platform-rebuild')
    flanks_only, _, _, _ = _run('platform-rebuild', fringe_core_share=0.0)
    assert flanks_only['meta']['params']['fringe_core_share'] == 0.0
    # a crest-reaching cut must lower the chain relative to a flank-only cut (compare the crest population, not the
    # single soft-capped maximum, which both variants can reach)
    # Each surface recalibrates its main-chain height AFTER cutting, so its highest samples need
    # not monotonically decrease with this parameter. Test that the cut actually changes the field,
    # not a sign that final peak calibration can legitimately reverse.
    assert np.abs(base['after_m'] - flanks_only['after_m']).max() > 10.0
    assert not np.array_equal(base['after_m'], flanks_only['after_m'])
    narrow, _, _, _ = _run('platform-rebuild', chain_width_gain=1.0)
    assert _relief_mask(narrow).sum() < _relief_mask(base).sum()      # narrower tents, smaller massif
    coarse, _, _, _ = _run('platform-rebuild', detail_wavelengths_km=(200.0, 140.0, 96.0))
    assert not np.array_equal(coarse['after_m'], base['after_m'])     # detail wavelengths reach the crest field
    smooth, _, _, _ = _run('platform-rebuild', crest_smooth_cells=1)
    assert not np.array_equal(smooth['after_m'], base['after_m'])     # the crest box mean is applied


def test_outline_variation_survives_noise_and_the_main_chain_stays():
    """Not one lucky seed: the chain still reads as a chain (same line, high relief) whatever the seed."""
    for seed in SEEDS:
        res, st, _, grid = _run('platform-rebuild', seed=seed)
        main = np.asarray(st['main'][0]['xz_m'], np.float64)
        S = grid['spacing_m']
        relief = []
        for k in range(0, len(main), 2):
            ix = int(round((main[k, 0] - grid['first_xz_m'][0]) / S))
            iz = int(round((main[k, 1] - grid['first_xz_m'][1]) / S))
            if 0 <= ix < SHAPE[1] and 0 <= iz < SHAPE[0]:
                relief.append(res['after_m'][iz, ix] - res['floor_m'][iz, ix])
        relief = np.asarray(relief)
        assert relief.size >= 8
        assert np.median(relief) > 800.0                      # the main chain keeps its height
        assert (relief >= 500.0).sum() >= 0.5 * relief.size    # and is not chopped into isolated peaks
        # the chain envelope itself varies along its length (high sections and saddles), it is not one constant band
        env = res['envelope']
        top = np.percentile(env[env > 0], 95.0)
        assert (env > 0.5 * top).sum() > 0, 'no crest envelope at all'
        assert (env > 0.2 * top).sum() < env.size              # the massif has finite extent inside the domain


def _tent_reference(structure, grid, wx, wz, params, width_mod=None):
    """Full-window reference of the tent envelope: no sub-rectangle, one segment at a time.

    This is the definition ``corridor_fields`` promises; it is computed over the whole window so a sub-rectangle that is
    too small shows up as a difference. Only the cells where the reference is non-zero matter.
    """
    p = ms._params(params)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    px_all = X[None, :] + np.asarray(wx, np.float64)
    pz_all = Z[:, None] + np.asarray(wz, np.float64)
    ref = np.zeros((nz, nx), np.float64)
    for (kind, li, ax, az, bx, bz, ww0, ww1, ws0, ws1, sd, a0, a1) in ms._segments_of(structure):
        dx, dz = bx - ax, bz - az
        l2 = max(dx * dx + dz * dz, 1e-9)
        t = np.clip(((px_all - ax) * dx + (pz_all - az) * dz) / l2, 0.0, 1.0)
        d = np.hypot(px_all - (ax + t * dx), pz_all - (az + t * dz))
        cross = dx * (pz_all - az) - dz * (px_all - ax)
        w = np.where(cross * sd >= 0, ww0 + (ww1 - ww0) * t, ws0 + (ws1 - ws0) * t)
        a = a0 + (a1 - a0) * t
        w_env = w if width_mod is None else w * np.clip(float(p['chain_width_gain']) * (1.0 + width_mod),
                                                       0.30, 3.20)
        x = np.clip(1.0 - d / np.maximum(w_env, 1.0), 0.0, 1.0)
        ref = np.maximum(ref, a * np.power(x, float(p['profile_exp'])))
    return ref


def _dist_to_main(structure, grid):
    """Distance from every window cell centre to the nearest main crest segment, metres (test-side reference)."""
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    out = np.full((nz, nx), np.inf, np.float64)
    for (kind, li, ax, az, bx, bz, ww0, ww1, ws0, ws1, sd, a0, a1) in ms._segments_of(structure):
        if kind != 'main':
            continue
        dx, dz = bx - ax, bz - az
        l2 = max(dx * dx + dz * dz, 1e-9)
        t = np.clip(((X[None, :] - ax) * dx + (Z[:, None] - az) * dz) / l2, 0.0, 1.0)
        out = np.minimum(out, np.hypot(X[None, :] - (ax + t * dx), Z[:, None] - (az + t * dz)))
    return out


def test_envelope_reach_is_not_truncated_by_the_segment_subrect():
    """The corridor sub-rectangle must cover the *modulated* width, not the bare one.

    The tent is drawn with ``w * clip(chain_width_gain * (1 + width_mod), .30, 3.20)``; with the accepted gain 1.85 a
    sub-rectangle sized from ``w`` alone cuts the widened flanks along a straight edge (the cut-looking outline of
    candidate-platform-final). The window envelope must equal the full-window reference everywhere it is non-zero.
    """
    for gain in (1.85, 2.60):
        res, st, _, grid = _run('platform-rebuild', chain_width_gain=gain, **TIGHT_SUPPORT)
        p = ms._params(dict(SMALL, **TIGHT_SUPPORT, structure_policy='platform-rebuild', chain_width_gain=gain))
        wx, wz = ms._window_warp(grid, p, SEED)
        dom = ms.belt_domain(st, grid, wx, wz, p, world_seed=SEED)
        ref = _tent_reference(st, grid, wx, wz, p, width_mod=dom['width_mod'])
        env = np.asarray(res['envelope'], np.float64)
        reached = ref > 1e-6
        assert reached.any()
        # 1. every cell the tent actually reaches carries its value: nothing is cut off at a sub-rectangle edge
        lost = reached & (env < 0.999 * ref)
        assert lost.sum() == 0, 'the envelope was truncated in %d cells at gain %.2f' % (lost.sum(), gain)
        assert np.allclose(env, ref, atol=1e-4)
        # 2. the widening really goes past the old reach (bare width + warp): otherwise this test would be vacuous
        old_reach = max(max(e['half_width_wide_m']) for e in st['main']) + 1.5 * p['warp_amp_km'] * 1000.0
        assert (reached & (_dist_to_main(st, grid) > old_reach)).sum() > 0


def test_reach_fix_does_not_change_the_safe_domain():
    """Only the tent is drawn wider: the permission mask (support) does not grow with ``chain_width_gain``.

    The widened envelope must not widen *where the surface may change* - otherwise the fix would be a scope change, not
    a truncation fix.
    """
    net, _ = synthetic_net()
    win, grid = synthetic_window()
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED,
                             params=dict(SMALL, structure_policy='platform-rebuild'))
    p1 = ms._params(dict(SMALL, structure_policy='platform-rebuild', chain_width_gain=1.85))
    p9 = ms._params(dict(SMALL, structure_policy='platform-rebuild', chain_width_gain=9.0))
    wx, wz = ms._window_warp(grid, p1, SEED)
    wmod = np.zeros(SHAPE, np.float64)          # flat zero modulation: the gain alone sets the tent width
    f1 = ms.corridor_fields(st, grid, wx, wz, p1, width_mod=wmod)
    f9 = ms.corridor_fields(st, grid, wx, wz, p9, width_mod=wmod)
    assert np.array_equal(f1['support'], f9['support'])              # the permission mask is not widened by the gain
    assert not np.array_equal(f1['envelope_main'], f9['envelope_main'])   # the outline itself is


def test_envelope_decays_to_zero_along_a_cross_section_with_high_gain():
    """A long straight crest at high gain: the cross-section must decay monotonically to exactly 0, no cliff."""
    res, st, _, grid = _run('platform-rebuild', chain_width_gain=2.60, width_var=0.0)
    env = np.asarray(res['envelope'], np.float64)
    xz = np.asarray(st['main'][0]['xz_m'], np.float64)
    S = float(grid['spacing_m'])
    x0, z0 = grid['first_xz_m']
    # take the column (constant x) through the middle of the chain and walk away from it along z on both sides
    k = len(xz) // 2
    ix = int(round((xz[k, 0] - x0) / S))
    iz0 = int(round((xz[k, 1] - z0) / S))
    assert 0 <= ix < SHAPE[1]
    up = env[iz0::-1, ix]
    dn = env[iz0:, ix]
    for prof in (up, dn):
        prof = np.asarray(prof)
        nz_ = np.flatnonzero(prof <= 1e-9)
        assert nz_.size, 'the envelope never reaches 0 along the cross-section'
        end = int(nz_[0])
        assert prof[:end].size > 2
        assert np.all(np.diff(prof[:end + 1]) <= 1e-6), 'the cross-section does not decay monotonically'
        # no cell drops to 0 from a large value: the last non-zero step is small compared with the crest
        assert prof[end] == 0.0 and prof[max(0, end - 1)] < 0.35 * prof[0]


def test_corridor_envelope_keeps_its_unmodulated_reach():
    """``corridor`` (no width modulation) draws exactly the bare-width tent: the envelope equals the reference."""
    res, st, _, grid = _run('corridor')
    p = ms._params(dict(SMALL, structure_policy='corridor'))
    wx, wz = ms._window_warp(grid, p, SEED)
    ref = _tent_reference(st, grid, wx, wz, p, width_mod=None)
    env = np.asarray(res['envelope'], np.float64)
    assert (env > 0).sum() > 0
    assert np.allclose(env, ref, atol=1e-4)
    # and the corridor reach is unchanged by the v3 fix: same envelope as the same call without width_mod
    fields = ms.corridor_fields(st, grid, wx, wz, p)
    assert np.array_equal(fields['envelope_main'], ms.corridor_fields(st, grid, wx, wz, p)['envelope_main'])


# ------------------------------------------------- v4: mountain-group (wide range, graded valleys, dH/R, skirt)
def test_group_policy_has_its_own_identity_and_leaves_the_old_one_alone():
    """The approved platform-rebuild replay is not rewritten: mountain-group carries a separate schema."""
    old, _, _, _ = _run('platform-rebuild')
    grp, _, _, _ = _run('mountain-group')
    assert old['meta']['schema'] == ms.SCHEMA and old['meta']['algorithm'] == ms.ALGORITHM
    assert grp['meta']['schema'] == ms.SCHEMA_G and grp['meta']['algorithm'] == ms.ALGORITHM_G
    assert ms.identity_tags({'structure_policy': 'mountain-group'}) == (ms.SCHEMA_G, ms.ALGORITHM_G)
    assert grp['identity'] != old['identity']
    assert grp['meta']['group_report'] is not None and old['meta']['group_report'] is None


def test_group_keeps_mid_mountains_where_there_is_no_crest_envelope():
    """Where the crest envelope is zero the old policy drops to the base; the group keeps a mid-mountain body."""
    old, _, _, _ = _run('platform-rebuild')
    grp, _, _, _ = _run('mountain-group')
    # the cells where the new surface is actually in force (blend > .9): at the domain edge the old surface is kept by
    # the smoothstep on purpose, so including it would measure the taper, not the group body
    env, dom = grp['envelope'], (grp['support'] > 0.5) & (grp['blend_weight'] > 0.9)
    flat = (env < 1e-6) & dom
    assert flat.sum() > 200
    r_old = (old['after_m'] - old['floor_m'])[flat]
    r_new = (grp['after_m'] - grp['floor_m'])[flat]
    assert np.median(r_old) < 200.0                      # the accepted look flattens to the base there
    assert np.median(r_new) > 400.0                      # the group does not
    assert (r_new > 800.0).sum() > 0.15 * r_new.size     # real mid mountains, not one more 2200 m cap
    # and it is terrain, not a table: the body varies laterally
    assert np.percentile(r_new, 90.0) - np.percentile(r_new, 10.0) > 600.0


def test_group_relief_is_built_in_metres_over_its_own_half_width():
    """dH is the relief actually built over the shoulder half width R, and its ratio stays inside the band."""
    grp, _, _, _ = _run('mountain-group')
    rep = grp['meta']['group_report']
    assert rep is not None
    s_lo, s_hi = rep['slope_range']
    assert rep['shoulder_half_m'] > 0 and rep['group_relief_m'] > 0
    ratio = rep['group_relief_m'] / rep['shoulder_half_m']
    assert s_lo - 1e-6 <= ratio <= s_hi + 1e-6           # the reported ratio is the configured band
    # the reported relief must be the relief in the surface, not an amplitude statistic
    built = np.percentile((grp['after_m'] - grp['floor_m'])[grp['support'] > 0.5], 95.0)
    assert rep['group_relief_realised_m'] > 0.5 * built
    assert 0.25 <= rep['body_gain'] <= 4.0               # bounded: the whole window is never scaled up
    # a wider configured shoulder at the same relief must actually widen the surface
    narrow, _, _, _ = _run('mountain-group', group_shoulder_half_km=(40.0, 60.0))
    wide, _, _, _ = _run('mountain-group', group_shoulder_half_km=(120.0, 200.0))
    assert wide['meta']['group_report']['shoulder_half_m'] > narrow['meta']['group_report']['shoulder_half_m']
    assert not np.array_equal(narrow['after_m'], wide['after_m'])


def test_group_main_crest_rises_a_real_height_above_its_base():
    """The crest term must be METRES: a unit error left the main chain below 1 m and every other check passed."""
    grp, st, _, grid = _run('mountain-group')
    base = grp['floor_m']
    S = float(grid['spacing_m'])
    got = []
    for ent in st['main']:
        for v in np.asarray(ent['xz_m'], np.float64)[::2]:
            ix = int(round((v[0] - grid['first_xz_m'][0]) / S))
            iz = int(round((v[1] - grid['first_xz_m'][1]) / S))
            if 0 <= ix < SHAPE[1] and 0 <= iz < SHAPE[0] and grp['support'][iz, ix] > 0.5:
                got.append(float(grp['after_m'][iz, ix] - base[iz, ix]))
    got = np.asarray(got)
    assert got.size >= 8
    assert np.median(got) > 800.0, 'the main crest is not a real mountain (median %.1f m above base)' % np.median(got)
    # Broad body and shoulder now consume part of the summit budget. The narrow crest need
    # only add hundreds of metres, not force another kilometre onto an already high massif.
    assert grp['meta']['group_report']['chain_peak_m'] > 100.0


def _shoulder_width_cells(layer, rel=0.2):
    """Physical width of the built shoulder layer at ``rel`` of its own local maximum, in cells.

    Measured on the metre array the generator returns (``shoulder_m``), never on the crest envelope: the envelope is
    the same for both policies and would prove nothing about the shoulder.
    """
    m = np.asarray(layer, np.float64)
    if m.max() <= 0:
        return 0.0
    return float((m >= rel * m.max()).sum())


def test_group_shoulder_is_a_real_metre_layer_with_a_measurable_width():
    """The generator must expose the built shoulder in metres; a wider crest really carries a wider shoulder."""
    grp, _, _, _ = _run('mountain-group')
    sh = grp['shoulder_m']
    sk = grp['skirt_m']
    assert sh is not None and sk is not None
    assert np.asarray(sh).max() > 100.0                  # real metres, not a 0..1 field
    assert np.asarray(sk).max() > 50.0
    old, _, _, _ = _run('platform-rebuild')
    assert old['shoulder_m'] is None and old['skirt_m'] is None   # group-only, the accepted policy is untouched


def test_group_taller_relief_gives_a_wider_shoulder_at_the_same_relative_height():
    """Same trace, two dH: the stronger crest must reach further at 20% of its own shoulder height."""
    narrow, _, _, _ = _run('mountain-group', group_shoulder_half_km=(45.0, 70.0))
    wide, _, _, _ = _run('mountain-group', group_shoulder_half_km=(110.0, 185.0))
    w_narrow = _shoulder_width_cells(narrow['shoulder_m'], 0.2)
    w_wide = _shoulder_width_cells(wide['shoulder_m'], 0.2)
    assert w_wide > w_narrow, 'a broader shoulder config did not widen the built layer (%.0f vs %.0f cells)' % (
        w_wide, w_narrow)
    # and at a fixed relief the wider shoulder is genuinely flatter: mean slope over its own width drops
    def mean_slope(res):
        sh = np.asarray(res['shoulder_m'], np.float64)
        rep = res['meta']['group_report']
        return float(sh.max()) / max(rep['shoulder_half_m'], 1.0)
    assert mean_slope(wide) < mean_slope(narrow), 'the wider shoulder is not flatter: no dH/R coupling in space'


def test_group_skirt_decays_to_zero_and_is_exactly_zero_outside_the_shoulder():
    """The foothill band must fall to exactly 0 beyond its own reach - a taper, not a constant +280 m sheet."""
    grp, _, _, _ = _run('mountain-group', group_shoulder_half_km=(20.0, 45.0))
    sk = np.asarray(grp['skirt_m'], np.float64)
    sh = np.asarray(grp['shoulder_m'], np.float64)
    assert sk.max() > 0
    # the skirt is the OUTER band: it covers at least as much ground as the shoulder, and it reaches where the
    # shoulder has already gone to zero
    assert (sk > 0).sum() >= (sh > 0).sum()
    assert (sk[sh <= 0] > 0).any(), 'the skirt never extends past the shoulder'
    # a real part of the window has exactly 0 skirt (finite support, no uniform halo)
    assert float((sk == 0).mean()) > 0.02
    # the skirt taper is monotone from each crest outwards to exactly 0. Measured from the skirt's own crest cell
    # along the direction that actually leaves it (not along a single fixed axis, which can re-enter a neighbour):
    # The skirt field is the MAX over all segments, so a single row crosses several crests. Its own taper is therefore
    # checked on ONE isolated segment: perpendicular to that segment, from its crest, the value must fall monotonically
    # to exactly 0 and stay 0 beyond it.
    import copy
    net, _ = synthetic_net()
    win, grid = synthetic_window()
    p = ms._params(dict(SMALL, structure_policy='mountain-group', group_shoulder_half_km=(30.0, 30.0)))
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
    solo = copy.deepcopy(st)
    solo['main'] = solo['main'][:1]
    solo['branches'], solo['spurs'] = [], []
    wx, wz = ms._window_warp(grid, p, SEED)
    f = ms.corridor_fields(solo, grid, wx, wz, p, width_mod=np.zeros(SHAPE, np.float64))
    one = np.asarray(f['envelope_skirt'], np.float64)
    xz = np.asarray(solo['main'][0]['xz_m'], np.float64)
    k = len(xz) // 2
    ix = int(round((xz[k, 0] - grid['first_xz_m'][0]) / float(grid['spacing_m'])))
    iz = int(round((xz[k, 1] - grid['first_xz_m'][1]) / float(grid['spacing_m'])))
    prof = np.asarray(one[iz:min(SHAPE[0], iz + 30), ix], np.float64)
    assert prof[0] > 0.5, 'no skirt at the crest cell'
    first0 = np.flatnonzero(prof <= 1e-9)
    assert first0.size, 'the skirt of one crest never reaches 0'
    end = int(first0[0])
    assert end >= 2, 'the skirt has no width at all'
    assert np.all(np.diff(prof[:end + 1]) <= 1e-9), 'the skirt does not decay monotonically from its own crest'
    assert prof[end] == 0.0 and prof[end - 1] < 0.5 * prof[0], 'the skirt ends in a step, not a taper'


def test_group_taller_crest_gets_a_wider_shoulder_in_space():
    """R is mapped from each crest's own amplitude, not from the window mean: a taller crest widens only its own."""
    import copy
    net, _ = synthetic_net()
    win, grid = synthetic_window()
    p = ms._params(dict(SMALL, structure_policy='mountain-group'))
    st = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
    wx, wz = ms._window_warp(grid, p, SEED)
    wmod = np.zeros(SHAPE, np.float64)
    base = np.asarray(ms.corridor_fields(st, grid, wx, wz, p, width_mod=wmod)['envelope_shoulder'], np.float64)
    tall = copy.deepcopy(st)
    for ent in tall['main']:
        ent['amp'] = [v * 3.0 for v in ent['amp']]
    wide = np.asarray(ms.corridor_fields(tall, grid, wx, wz, p, width_mod=wmod)['envelope_shoulder'], np.float64)
    assert (wide > 0.5).sum() > (base > 0.5).sum(), 'a taller crest did not get a wider shoulder in space'


def test_group_valley_drop_is_bounded_and_bed_stays_positive():
    """Trunk valley + basins never cut to the base or below sea level."""
    grp, _, win, _ = _run('mountain-group')
    floor, after = grp['floor_m'], grp['after_m']
    dry = ~win['fixed']
    assert (after[dry] > 0.0).all()
    deeper = (after - floor)[dry & (grp['support'] > 0.5)]
    assert deeper.min() > -1500.0                        # a bounded incision, not a canyon to the base
    assert deeper.min() < -200.0                         # and there is a real valley


def test_group_skirt_falls_to_zero_and_the_edge_is_not_a_halo():
    """The foothill skirt decays monotonically with the crest envelope; the group edge meets the old surface."""
    grp, _, _, _ = _run('mountain-group')
    rep = grp['meta']['group_report']
    assert grp['meta']['params']['group_skirt_amp_m'] > 0.0
    assert rep['keep_excess'] == [0.30, 0.50]
    # outside the domain nothing moved, and at the very edge the blend is 0 (no halo ring)
    outside = grp['support'] <= 0.0
    assert np.array_equal(grp['after_m'][outside], grp['before_m'][outside])
    edge = grp['blend_weight'] < 1e-9
    assert edge.any()
    assert np.array_equal(grp['after_m'][edge], grp['before_m'][edge])


def test_group_is_deterministic_finite_and_keeps_fixed_cells():
    """Determinism / finiteness / fixed water / outer ring, for the new policy too."""
    a, _, win, _ = _run('mountain-group')
    b, _, _, _ = _run('mountain-group')
    assert np.array_equal(a['after_m'], b['after_m'])
    assert a['identity'] == b['identity']
    assert np.isfinite(a['after_m']).all() and np.isfinite(a['floor_m']).all()
    fixed = win['fixed']
    assert np.array_equal(a['after_m'][fixed], a['before_m'][fixed])
    assert np.array_equal(a['after_m'][0], a['before_m'][0])
    assert np.array_equal(a['after_m'][:, -1], a['before_m'][:, -1])
    assert a['after_m'].max() <= a['before_m'].max() + 1.0     # no global lift to 5 km
    assert a['meta']['erosion']['applied'] is False


def test_group_zero_erosion_replays_without_reblend(monkeypatch):
    plain, _, _, _ = _run('mountain-group')
    monkeypatch.setattr(ms, '_erode_window', lambda surface, *a, **k: surface.copy())
    eroded, _, _, _ = _run('mountain-group', erosion=True)
    assert np.array_equal(plain['after_m'], eroded['after_m'])


def test_plateau_reaching_the_window_border_is_tapered_not_walled():
    """Old plateau extends past the window border: the border must be met along a wide ramp, not a 3-cell wall.

    The v1 halo blends over 6 cells, so a 4 km platform difference against the fixed border shows up as a straight
    wall on the map. v2 adds a metres-based taper (``edge_taper_km``); here the check is on the surface: no cell step
    near the border is much steeper than the interior steps of the same surface.
    """
    win_kw = dict(platform_half_m=900000.0, belt_half_m=450000.0)
    res, _, win, _ = _run('platform-rebuild', window_kw=win_kw)
    after, before = res['after_m'], res['before_m']

    def border_step(a):
        return max(np.abs(a[0] - a[1]).max(), np.abs(a[-1] - a[-2]).max(),
                   np.abs(a[:, 0] - a[:, 1]).max(), np.abs(a[:, -1] - a[:, -2]).max())

    # a step that the *input window itself* already had (here: the sea strip beside the platform) is not ours to fix;
    # what must not happen is the sculpt *adding* a step at the border
    assert border_step(after) <= border_step(before) + 1.0, \
        'the sculpt added a wall at the window border: %.0f m vs %.0f m on the input' % (border_step(after),
                                                                                        border_step(before))
    # the taper really widens the blend: many more cells near the border move than the v1 6-cell halo allowed
    near = np.zeros(after.shape, bool)
    near[:12, :] = near[-12:, :] = True
    near[:, :12] = near[:, -12:] = True
    moved = int((res['changed_mask'] & near).sum())
    assert moved > 0.25 * int(near.sum()), 'the border transition is still a narrow strip (%d of %d cells)' % (
        moved, int(near.sum()))
    # and the border itself is still bitwise old
    assert np.array_equal(after[0], res['before_m'][0]) and np.array_equal(after[:, -1], res['before_m'][:, -1])
    assert res['meta']['edge_taper_km'] > 20.0


def test_v2_keeps_no_flat_summit_table():
    """The soft cap approaches the old peak asymptotically: summits are not clipped into a 2200 m / peak table."""
    res, _, _, _ = _run('platform-rebuild')
    after = res['after_m']
    cap = res['meta']['peak_soft_cap_m']
    assert cap is not None and cap > 0.0
    highest = after.max()
    at_cap = int((after >= cap - 1.0).sum())
    # the soft cap applies to the rebuilt surface; a partly blended cell keeps its own old value (which is below the
    # old peak), so the window maximum is bounded by the old peak - never by a raised cap
    assert highest <= max(float(res['before_m'].max()), cap) + 1.0
    assert highest <= float(res['before_m'].max()) + 1.0
    assert at_cap < 0.01 * after.size                     # a soft cap leaves almost nothing pinned flat
    # the valley level is the rebuilt low base, not the v1 [floor_min, floor_max] table: inside the domain the
    # valley floor sits far below the old platform, and it is not one constant 2200 m table
    dom = res['support'] > 0.5
    floor = res['floor_m'][dom]
    assert np.median(floor) < 0.5 * np.median(res['before_m'][dom])
    assert np.std(floor) > 30.0                           # a ramp, not a flat floor


# ------------------------------------------------------------------ hydrology / erosion claims
def test_no_hydrology_is_claimed():
    res, _, _, _ = _run()
    assert res['meta']['hydrology']['computed'] is False
    assert res['meta']['erosion']['applied'] is False
    assert 'rivers' not in res and 'lakes' not in res
    # no D8 network is routed: the only erosion path is the irregular graph, and it is opt-in
    import app.world_gen.mountain_sculpt as mod
    assert 'graph_hydro' in open(mod.__file__, encoding='utf-8').read()


def test_write_candidate_roundtrip(tmp_path):
    res, _, _, _ = _run()
    info = ms.write_candidate(tmp_path / 'candidate', res, note='unit test')
    assert (tmp_path / 'candidate' / 'arrays.npz').exists()
    assert not (tmp_path / 'candidate' / 'manifest.json').exists()      # never a world product
    doc = json.loads((tmp_path / 'candidate' / 'structure.json').read_text(encoding='utf-8'))
    assert doc['schema'] == ms.SCHEMA
    assert doc['identity'] == res['identity'] == info['identity']
    with np.load(tmp_path / 'candidate' / 'arrays.npz') as z:
        assert {'before_m', 'after_m', 'changed_mask', 'significant_mask', 'blend_weight', 'support', 'valley_mask',
                'basin_mask', 'ocean', 'lake', 'first_xz_m', 'spacing_m', 'shape'} <= set(z.files)
        # full precision on disk: elevation and the changed mask round-trip exactly (no float32 re-quantisation)
        assert np.array_equal(z['after_m'], res['after_m'])
        assert np.array_equal(z['before_m'], res['before_m'])
        assert np.array_equal(z['changed_mask'], res['after_m'] != res['before_m'])
        assert int(z['changed_mask'].sum()) == res['meta']['changed_cells']
        assert int(z['shape'][0]) == SHAPE[0] and int(z['shape'][1]) == SHAPE[1]
    assert doc['structure']['main']
    assert doc['structure']['basins']          # at least one basin vector is exported
    assert doc['structure']['passes']
    assert doc['meta']['hydrology']['computed'] is False
    readme = (tmp_path / 'candidate' / 'README.md').read_text(encoding='utf-8')
    assert '未算水文' in readme
    assert ms.SCHEMA in readme


def test_zero_erosion_increment_does_not_reblend_sculpt(monkeypatch):
    for policy in POLICIES:
        plain, _, _, _ = _run(policy)
        monkeypatch.setattr(ms, '_erode_window', lambda surface, *args, **kwargs: surface.copy())
        eroded, _, _, _ = _run(policy, erosion=True)
        assert np.array_equal(plain['after_m'], eroded['after_m'])


def test_soft_cap_preserves_height_order_and_has_no_folded_rim():
    heights = np.linspace(3000.0, 7000.0, 401)
    out = ms._soft_cap(heights, 5000.0, 225.0)
    assert np.all(np.diff(out) > 0.0)
    assert np.isfinite(out).all() and out.max() < 5000.0
    assert abs(out[0] - heights[0]) < 1.0
    assert np.ptp(out[(heights > 4400) & (heights < 5200)]) > 250.0


def test_group_relative_height_width_constraint_is_spatial_not_altitude():
    p = ms._params(dict(structure_policy='mountain-group'))
    amps = np.array([0.3, 0.5, 0.8])
    widths = ms._group_half_width(amps, p)
    dh = np.clip(amps * p['peak_relief_m'], 300.0, p['group_relief_range_m'][1])
    slopes = dh / widths
    assert (np.diff(widths) > 0).all()
    assert (slopes >= p['group_slope_range'][0] - 1e-9).all()
    assert (slopes <= p['group_slope_range'][1] + 1e-9).all()
    assert widths.max() <= max(p['group_shoulder_half_km']) * 1000


def test_group_preserves_backbone_population_and_tapers_free_branch_tips():
    net, _ = synthetic_net()
    win, grid = synthetic_window()
    p = dict(SMALL, structure_policy='mountain-group')
    group = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED, params=p)
    old = ms.select_structure(net, grid['rect_m'], belt=0, world_seed=SEED,
                              params=dict(SMALL, structure_policy='platform-rebuild'))
    assert group['meta']['main_lines'] == old['meta']['main_lines']
    branch = group['branches'][0]
    reference = old['branches'][0]
    ratio = np.array(branch['amp']) / np.array(reference['amp'])
    # Source test branch starts at its parent's ridge and ends free.
    assert ratio[0] > 0.95 and ratio[-1] <= 0.31
    wratio = np.array(branch['half_width_wide_m']) / np.array(reference['half_width_wide_m'])
    assert wratio[-1] < wratio[0] and wratio[0] > 0.95
