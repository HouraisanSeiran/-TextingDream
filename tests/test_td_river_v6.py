"""td-world-960m-v6 river routing on the Terragenesis irregular graph (small synthetic terrain).

Needs numba (Terragenesis irregular_drainage). The Dream .venv has none, so these tests are skipped there; run them with
``D:/codexwork/山川形意Terragenesis/runtime/venv/Scripts/python.exe -m pytest tests/test_td_river_v6.py``.
"""
import numpy as np
import pytest

numba = pytest.importorskip("numba", reason="numba is not installed in this interpreter (Terragenesis irregular_drainage needs it)")

from app.world_relief import td_freeze_v6 as v6  # noqa: E402

SPACING = 960.0
FIRST = (-40 * SPACING, 25 * SPACING)
SEED = 20261020


def terrain(nz=70, nx=80):
    """Tilted plane draining to the east (ocean strip), with smooth bumps so channels must bend."""
    z, x = np.mgrid[0:nz, 0:nx].astype(np.float64)
    h = 600.0 * (1.0 - x / nx) + 40.0 * np.sin(z / 5.0) * np.cos(x / 7.0) + 25.0 * np.sin((x + 2 * z) / 9.0) + 5.0
    ocean = np.zeros((nz, nx), bool)
    ocean[:, -8:] = True
    h[ocean] = -50.0
    return h.astype(np.float32), ocean


@pytest.fixture(scope="module")
def run():
    h, ocean = terrain()
    h0 = h.copy()
    res = v6.compute_v6(h, h.copy(), ocean, FIRST, SPACING, SEED, lo_m2=20e6, hi_m2=20e6)
    return h, h0, ocean, res


def test_receivers_acyclic_and_all_reach_outlet(run):
    h, _, ocean, res = run
    rec = res["hyd"]["receiver"]
    n = rec.size
    assert (rec < n).all() and (rec >= -1).all()
    outlets = res["outlets"].ravel()
    assert ((rec == -1) == outlets).all()          # only outlets drain, every other node has a downstream node
    rank = np.empty(n, np.int64)
    rank[res["hyd"]["order"]] = np.arange(n)
    donors = np.flatnonzero(rec >= 0)
    assert (rank[rec[donors]] < rank[donors]).all()  # receivers precede donors => no cycle
    cur = np.arange(n)
    for _ in range(n):                              # pointer jumping: every node ends in an outlet
        nxt = np.where(rec[cur] >= 0, rec[cur], cur)
        if (nxt == cur).all():
            break
        cur = nxt
    assert outlets[cur].all()


def test_area_conserved(run):
    _, _, _, res = run
    rec = res["hyd"]["receiver"]
    area = res["hyd"]["area_m2"]
    assert area[rec < 0].sum() == pytest.approx(rec.size * SPACING ** 2, rel=1e-9)
    assert (area >= SPACING ** 2 - 1e-6).all()
    donors = np.flatnonzero(rec >= 0)
    inflow = np.bincount(rec[donors], weights=area[donors], minlength=rec.size)
    assert np.allclose(area, SPACING ** 2 + inflow)


def test_receiver_is_graph_edge(run):
    _, _, _, res = run
    mesh, rec = res["mesh"], res["hyd"]["receiver"]
    for node in np.flatnonzero(rec >= 0)[::7]:
        assert rec[node] in mesh.indices[mesh.indptr[node]:mesh.indptr[node + 1]]


def test_river_directions_not_eight_discrete_angles(run):
    _, _, _, res = run
    ang, ln, _ = v6.edge_table(res["rivers"], res["lake_id"], FIRST, SPACING)
    assert ang.size > 100
    # D8 would put every edge exactly on 0/45/90/135 degrees; irregular nodes spread them out
    on_octant = np.abs(((ang + 22.5) % 45.0) - 22.5) <= 1.0
    assert on_octant.mean() < 0.15
    assert v6.octant_fraction(ang, ln, 5.0)["length"] < 0.5
    assert len(np.unique(np.round(ang))) > 30


def test_rivers_end_in_outlet_and_topology_consistent(run):
    _, _, ocean, res = run
    ids = {line["id"] for line in res["rivers"]}
    assert len(ids) == len(res["rivers"])
    for line in res["rivers"]:
        assert line["downstream_id"] is None or line["downstream_id"] in ids
        assert line["outlet"] in ("ocean", "edge", "lake", "closed")


def test_elevation_not_modified_and_deterministic(run):
    h, h0, ocean, res = run
    assert np.array_equal(h, h0)
    res2 = v6.compute_v6(h0.copy(), h0.copy(), ocean, FIRST, SPACING, SEED, lo_m2=20e6, hi_m2=20e6)
    assert np.array_equal(res["hyd"]["receiver"], res2["hyd"]["receiver"])
    assert np.array_equal(res["hyd"]["area_m2"], res2["hyd"]["area_m2"])
    assert res["rivers"] == res2["rivers"]
    assert res["mesh_seed"] == v6.subseed(SEED, v6.MESH_PURPOSE)


def test_different_mesh_seed_changes_geometry():
    h, ocean = terrain(40, 50)
    a = v6.compute_v6(h, h.copy(), ocean, FIRST, SPACING, SEED, lo_m2=20e6, hi_m2=20e6)
    b = v6.compute_v6(h, h.copy(), ocean, FIRST, SPACING, SEED, mesh_seed=12345, lo_m2=20e6, hi_m2=20e6)
    assert not np.array_equal(a["mesh"].node_x_m, b["mesh"].node_x_m)


def test_node_positions_inside_own_cell(run):
    _, _, _, res = run
    mesh = res["mesh"]
    nz, nx = 70, 80
    cx = FIRST[0] + np.tile(np.arange(nx), nz) * SPACING
    cz = FIRST[1] + np.repeat(np.arange(nz), nx) * SPACING
    assert np.abs(mesh.node_x_m - cx).max() <= 0.35 * SPACING + 1e-6
    assert np.abs(mesh.node_z_m - cz).max() <= 0.35 * SPACING + 1e-6


def test_smoothing_keeps_heads_and_outlets_fixed():
    px = np.array([0., 1000., 2000., 3000., 4000.])
    pz = np.array([0., 300., -300., 300., 0.])
    rec = np.array([1, 2, 3, 4, -1])
    active = np.ones(5, bool)
    x, z, _ = v6.smooth_centerline(px, pz, rec, active)
    assert (x[0], z[0]) == (px[0], pz[0]) and (x[4], z[4]) == (px[4], pz[4])
    assert np.hypot(x - px, z - pz).max() <= v6.SMOOTH_MAX_OFFSET_M + 1e-9
    assert np.abs(z[1:4]).max() < 300.0           # bends are relaxed
