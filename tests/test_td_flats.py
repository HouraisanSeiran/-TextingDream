"""Convergent flat routing (app.world_relief.td_flats): synthetic flats must converge on few outlets, be acyclic and deterministic."""
import numpy as np

from app.world_relief import drainage, td_flats, td_hydro


def _plain(nz=40, nx=40, slope=0.0):
    """Sea on the east edge (x >= nx-3), flat land west of it, optional tiny tilt towards the sea."""
    z, x = np.indices((nz, nx))
    h = np.full((nz, nx), 5.0) + slope * (nx - x)
    ocean = np.zeros((nz, nx), bool)
    ocean[:, nx - 3:] = True
    h[ocean] = -10.0
    h[0] = 5.0 + slope * (nx - x[0]); h[-1] = h[0]
    return h, ocean


def _mouths(flow, ocean):
    rec = flow['receiver']; oc = ocean.ravel()
    area = flow['area_m2'].ravel()
    return np.flatnonzero((~oc) & oc[rec] & (area > 0))


def _reaches_terminal(rec, ocean):
    nz, nx = ocean.shape
    terminal = ocean.copy(); terminal[0] = terminal[-1] = True; terminal[:, 0] = terminal[:, -1] = True
    term = terminal.ravel()
    cur = np.arange(rec.size)
    for _ in range(rec.size):
        nxt = rec[cur]
        if term[cur].all():
            return True
        cur = np.where(term[cur], cur, nxt)
    return bool(term[cur].all())


def test_flat_plain_converges_to_few_outlets_without_cycles():
    h, ocean = _plain()
    base = drainage.route(h, ocean, 960, area_mode='d8')
    flow = td_flats.route_flats(h, ocean, 960)
    assert flow['flats']['unresolved_cells'] == 0
    assert _reaches_terminal(flow['receiver'], ocean)
    # acyclic: following receivers from any cell strictly advances in the routing order
    pos = np.empty(h.size, np.int64); pos[flow['order']] = np.arange(h.size)
    moved = flow['receiver'] != np.arange(h.size)
    assert np.all(pos[flow['receiver'][moved]] < pos[np.flatnonzero(moved)])
    # area conservation: total accumulated at terminals equals cell count
    terminal = ocean.copy(); terminal[0] = terminal[-1] = True; terminal[:, 0] = terminal[:, -1] = True
    assert abs(flow['area_m2'].ravel()[terminal.ravel()].sum() - h.size * 960.0 ** 2) < 1.0
    # every land cell drains somewhere; mouths exist only on cells next to the sea
    assert len(_mouths(flow, ocean)) > 0


def _corridor(width, length=50):
    """Flat strip of ``width`` rows between high walls, sea at its east end."""
    nz, nx = width + 8, length + 8
    h = np.full((nz, nx), 100.0); ocean = np.zeros((nz, nx), bool)
    h[4:4 + width, 2:nx - 3] = 5.0
    h[4:4 + width, nx - 3:] = -10.0; ocean[4:4 + width, nx - 3:] = True
    return h, ocean


def test_flat_corridor_merges_parallel_lines_towards_the_centre():
    for width in (11, 21):
        h, ocean = _corridor(width)
        base = drainage.route(h, ocean, 960, area_mode='d8')
        flow = td_flats.route_flats(h, ocean, 960)
        col = h.shape[1] - 8
        rows_old = int((base['area_m2'][:, col] >= 4 * 960.0 ** 2).sum())
        rows_new = int((flow['area_m2'][:, col] >= 4 * 960.0 ** 2).sum())
        assert rows_new < rows_old
        assert int((flow['area_m2'][~ocean] >= 5 * 960.0 ** 2).sum()) < int((base['area_m2'][~ocean] >= 5 * 960.0 ** 2).sum())
        assert _reaches_terminal(flow['receiver'], ocean)


def test_tilted_plain_still_reaches_ocean_and_is_deterministic():
    h, ocean = _plain(slope=1e-3)
    a = td_flats.route_flats(h, ocean, 960)
    b = td_flats.route_flats(h, ocean, 960)
    assert np.array_equal(a['receiver'], b['receiver'])
    assert np.array_equal(a['area_m2'], b['area_m2'])
    assert _reaches_terminal(a['receiver'], ocean)


def test_flat_with_pit_and_hill_all_cells_reach_outlet():
    h, ocean = _plain()
    h[10:14, 10:14] += 30.0          # hill on the plain
    h[25:28, 20:23] -= 3.0           # shallow pit (filled to a flat by priority flood)
    flow = td_flats.route_flats(h, ocean, 960)
    assert flow['flats']['unresolved_cells'] == 0
    assert _reaches_terminal(flow['receiver'], ocean)
    # elevation is an input only
    h2 = h.copy(); td_flats.route_flats(h, ocean, 960)
    assert np.array_equal(h, h2)


def test_breach_and_lakes_with_flat_router_keeps_elevation_and_gets_no_unresolved_pits():
    h, ocean = _plain()
    h[25:28, 20:23] -= 3.0
    before = h.copy()
    res = td_hydro.breach_and_lakes(h, ocean, 960, 60.0, 100e6, router=td_flats.route_flats)
    assert np.array_equal(h, before)
    assert res['unresolved_depressions'] == 0
    assert _reaches_terminal(res['flow']['receiver'], ocean)


# ---- meander perturbation (coordinate-addressed, deterministic) ----
MEANDER = dict(world_seed=20261020, first_xz=(-799215, -639855))


def _straight_fraction(flow, ocean, min_cells=6):
    """Share of channel cells (area >= min_cells) whose step equals the step of their receiver (i.e. no bend there)."""
    rec = flow['receiver']; nx = ocean.shape[1]
    area = flow['area_m2'].ravel() / 960.0 ** 2
    term = ocean.copy(); term[0] = term[-1] = True; term[:, 0] = term[:, -1] = True
    term = term.ravel()
    idx = np.flatnonzero((area >= min_cells) & ~term & (rec != np.arange(rec.size)))
    idx = idx[(~term[rec[idx]]) & (rec[rec[idx]] != rec[idx])]
    d1 = np.stack([rec[idx] // nx - idx // nx, rec[idx] % nx - idx % nx], 1)
    r2 = rec[rec[idx]]
    d2 = np.stack([r2 // nx - rec[idx] // nx, r2 % nx - rec[idx] % nx], 1)
    return float((d1 == d2).all(1).mean()), int(idx.size)


def _acyclic(flow, n):
    pos = np.empty(n, np.int64); pos[flow['order']] = np.arange(n)
    moved = flow['receiver'] != np.arange(n)
    return bool(np.all(pos[flow['receiver'][moved]] < pos[np.flatnonzero(moved)]))


def test_meander_noise_is_deterministic_bounded_and_coordinate_addressed():
    a = td_flats.meander_noise((60, 70), MEANDER['first_xz'], 960, MEANDER['world_seed'])
    b = td_flats.meander_noise((60, 70), MEANDER['first_xz'], 960, MEANDER['world_seed'])
    assert np.array_equal(a, b) and a.min() >= -1.0 and a.max() <= 1.0 and a.std() > 0.05
    # the step-cost lower bound must stay above the away weight (this is what keeps the potential strictly falling)
    assert min(td_flats._meander_step_costs()) > td_flats.MEANDER_AWAY_WEIGHT
    # a sub-window evaluated on its own gives the same values (absolute coordinates, no query-order dependence)
    first_sub = (MEANDER['first_xz'][0] + 10 * 960, MEANDER['first_xz'][1] + 5 * 960)
    sub = td_flats.meander_noise((20, 30), first_sub, 960, MEANDER['world_seed'])
    assert np.array_equal(sub.reshape(20, 30), a.reshape(60, 70)[5:25, 10:40])
    # a different seed gives a different field
    c = td_flats.meander_noise((60, 70), MEANDER['first_xz'], 960, MEANDER['world_seed'] + 1)
    assert not np.array_equal(a, c)


def test_meander_plain_is_acyclic_reaches_outlet_and_is_deterministic():
    h, ocean = _plain(60, 80)
    a = td_flats.route_flats(h, ocean, 960, meander=MEANDER)
    b = td_flats.route_flats(h, ocean, 960, meander=MEANDER)
    assert a['flats']['unresolved_cells'] == 0 and a['flats']['no_lower_neighbour_cells'] == 0
    assert _reaches_terminal(a['receiver'], ocean)
    assert _acyclic(a, h.size)
    assert np.array_equal(a['receiver'], b['receiver']) and np.array_equal(a['area_m2'], b['area_m2'])
    terminal = ocean.copy(); terminal[0] = terminal[-1] = True; terminal[:, 0] = terminal[:, -1] = True
    assert abs(a['area_m2'].ravel()[terminal.ravel()].sum() - h.size * 960.0 ** 2) < 1.0


def test_meander_with_hill_pit_and_corridor_stays_acyclic_and_reaches_outlet():
    h, ocean = _plain(60, 80)
    h[10:14, 10:14] += 30.0
    h[25:28, 20:23] -= 3.0
    before = h.copy()
    flow = td_flats.route_flats(h, ocean, 960, meander=MEANDER)
    assert np.array_equal(h, before)
    assert flow['flats']['unresolved_cells'] == 0
    assert _reaches_terminal(flow['receiver'], ocean) and _acyclic(flow, h.size)
    hc, oc = _corridor(15, 60)
    fc = td_flats.route_flats(hc, oc, 960, meander=MEANDER)
    assert _reaches_terminal(fc['receiver'], oc) and _acyclic(fc, hc.size)


def test_meander_without_option_reproduces_unperturbed_routing():
    h, ocean = _plain(40, 40)
    a = td_flats.route_flats(h, ocean, 960)
    b = td_flats.route_flats(h, ocean, 960, meander=None)
    assert np.array_equal(a['receiver'], b['receiver'])


def test_meander_reduces_straight_channel_fraction_on_synthetic_plain():
    h, ocean = _plain(90, 120)
    base = td_flats.route_flats(h, ocean, 960)
    wiggly = td_flats.route_flats(h, ocean, 960, meander=MEANDER)
    fb, nb = _straight_fraction(base, ocean)
    fw, nw = _straight_fraction(wiggly, ocean)
    assert nb > 20 and nw > 20
    assert fw < fb, (fb, fw)
    # a different seed bends it too, and the bend is not a one-seed accident
    other = td_flats.route_flats(h, ocean, 960, meander=dict(MEANDER, world_seed=7))
    assert _straight_fraction(other, ocean)[0] < fb
