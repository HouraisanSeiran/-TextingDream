import numpy as np
from scipy import ndimage

from app.world_relief import drainage, td_hydro

SP = 960
A_MIN = 4 * SP ** 2   # tiny test area threshold (4 cells)


def _world():
    nz, nx = 40, 40
    x = np.arange(nx)[None, :].repeat(nz, 0).astype(float)
    h = np.where(x < 5, -100.0, 10.0 + 5.0 * x)
    h[20:23, 15:18] -= 20.0     # shallow 3x3 pit (spill depth ~15 m on a 5 m/cell ramp)
    h[5:13, 25:33] -= 100.0     # deep 8x8 basin (depth ~95 m)
    return h


def _run(h, depth=30.0, area=A_MIN):
    ocean = drainage.ocean_mask(h)
    return ocean, td_hydro.breach_and_lakes(h.copy(), ocean, SP, depth, area)


def test_shallow_pit_is_breached_deep_basin_stays_lake():
    h = _world()
    ocean, r = _run(h)
    assert r['lake_id'][20:23, 15:18].max() == 0, 'shallow pit must not be a lake'
    assert (r['lake_id'][5:13, 25:33] > 0).any(), 'deep wide basin must stay a lake'
    assert r['unresolved_depression_cells'] == 0
    # breached channel only lowers cells
    assert np.all(r['bed'] <= h + 1e-9) and (r['bed'] < h).any()


def test_small_but_deep_pit_is_breached_by_area_rule():
    h = _world()
    h[30:32, 30:32] -= 100.0  # 2x2 = 4 cells (< 10-cell area threshold), deep (>30 m) but lowest cell stays above sea level
    ocean = drainage.ocean_mask(h)
    r = td_hydro.breach_and_lakes(h.copy(), ocean, SP, 30.0, 10 * SP ** 2)
    assert r['lake_id'][30:32, 30:32].max() == 0


def test_original_elevation_is_not_modified():
    h = _world()
    before = h.copy()
    ocean = drainage.ocean_mask(h)
    r = td_hydro.breach_and_lakes(h, ocean, SP, 30.0, A_MIN)
    np.testing.assert_array_equal(h, before)
    assert r['bed'] is not h and (r['bed'] != h).any()


def test_receivers_are_acyclic_and_reach_outlet():
    h = _world()
    ocean, r = _run(h)
    rec = r['flow']['receiver'].ravel()
    n = rec.size
    cur = np.arange(n)
    for _ in range(n):
        nxt = rec[cur]
        if np.array_equal(nxt, cur):
            break
        cur = nxt
    # every chain ends in a self-receiving outlet (ocean or rim) -> no cycles
    assert np.array_equal(rec[cur], cur)
    assert np.all(ocean.ravel()[cur] | (rec[cur] == cur))


def test_lake_ids_unique_contiguous_and_one_component_each():
    h = _world()
    h[30:38, 5:13] += 0.0
    _, r = _run(h)
    ids = np.unique(r['lake_id'])
    ids = ids[ids > 0]
    assert ids.size >= 1
    assert np.array_equal(ids, np.arange(1, ids.size + 1))
    for i in ids:
        _, n = ndimage.label(r['lake_id'] == i, structure=np.ones((3, 3)))
        assert n == 1, f'lake {i} is split into {n} components'
