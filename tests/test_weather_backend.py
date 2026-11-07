"""Weather backend regression tests through the public functions and real JS mirror."""
import json
import subprocess

import pytest

from app import weather as w
from tests.test_weather import NODE, JS, _RUNNER, _same


@pytest.mark.parametrize('kind', w.BATCH4)
def test_extended_kinds_supply_art_contract(kind):
    s = w.weather_at(42, 80, 5, 'temperate', overrides={'kind': kind, 'intensity': .7})
    w.validate_state(s)
    assert set(('aerosol', 'rainbow', 'heat', 'cyclone', 'vortex')) <= s.keys()
    assert len(s['ground']) == 11  # includes accumulated graupel, consumed by ice.js
    if kind == 'typhoon':
        assert s['cyclone']['phase'] != 'none'
    if kind == 'tornado':
        assert s['vortex'] > 0


@pytest.mark.parametrize('kind,field', [('freezing_rain', 'glaze'), ('graupel', 'graupel'),
                                     ('frost', 'frost'), ('rime', 'rime'), ('dust', 'dust_cover')])
def test_extended_covers_accumulate_and_dry_or_thaw(kind, field):
    s = w.weather_at(3, 60, 4, 'continental', overrides={'kind': kind, 'intensity': .8})
    assert s['ground'][field] > .05
    # Replay actual per-hour ground evolution after the forcing stops.
    c = w._context(3, 'continental', 'summer', None, None, None)
    n = w._natural(c, 12)
    ov = w._flat_overrides({'kind': 'clear', 'temperature_c': 25, 'wind': {'speed': .8}})
    f = w._derive(c, 'clear', .1, n, ov)
    v = w._ground_input('clear', .1, n, f)
    g = tuple(s['ground'][k] for k in w.GROUND_NAMES)
    before = g[w.GROUND_NAMES.index(field)]
    for _ in range(24):
        g = w._step(g, v)
    assert g[w.GROUND_NAMES.index(field)] < before * .25


def test_dateline_continuity_and_batch_order():
    cells = [{'id': 'west', 'lon': 179.999, 'lat': 40, 'climate': 'continental'},
             {'id': 'east', 'lon': -179.999, 'lat': 40, 'climate': 'continental'}]
    a, b = w.region_weather(9, cells, 100, 7.5)
    assert abs(a['temperature_c'] - b['temperature_c']) < .02
    assert abs(a['cloud_cover'] - b['cloud_cover']) < .01
    assert w.region_weather(9, cells[::-1], 100, 7.5) == [b, a]
    opts = dict(lat=40, calendar={'start_day_of_year': 80, 'utc_offset': 8})
    assert w.weather_at(1, 2, 5, 'maritime', lon=-180, **opts) == w.weather_at(1, 2, 5, 'maritime', lon=180, **opts)


def test_coast_input_is_explicit_and_validated():
    with pytest.raises(ValueError):
        w.weather_at(1, 1, 0, 'tropical', coast_distance_km=-1)
    seq = w.forecast(8, 180, 0, 240, 'tropical', season='summer', coast_distance_km=2000)
    assert all(s['kind'] != 'typhoon' for s in seq)


def test_cache_is_bounded_detached_and_reused():
    w.clear_cache()
    a = w.weather_at(1, 2, 12, 'temperate')
    before = w.cache_info()
    a['ground']['wetness'] = 999
    b = w.weather_at(1, 2, 13, 'temperate')
    after = w.cache_info()
    assert after['natural_evaluations'] - before['natural_evaluations'] < 5
    assert b['ground']['wetness'] <= 1
    assert w.weather_at(1, 2, 12, 'temperate')['ground']['wetness'] != 999
    assert after['contexts'] <= after['max_contexts']
    for seed in range(w.MAX_CONTEXTS + 4):
        w._context(seed, 'temperate', None, None, None, None)
    assert w.cache_info()['contexts'] == w.MAX_CONTEXTS


def test_region_repeat_reuses_a_small_viewport():
    w.clear_cache()
    cells = [{'id': i, 'lat': 40 + i // 8 * .05, 'lon': 116 + i % 8 * .05,
              'climate': 'temperate'} for i in range(64)]
    first = w.region_weather(42, cells, 100, 12)
    before = w.cache_info()['natural_evaluations']
    assert first == w.region_weather(42, cells, 100, 12)
    assert w.cache_info()['natural_evaluations'] == before


@pytest.mark.parametrize('kind,seed,climate,season,t', [
    ('freezing_rain', 1, 'temperate', 'winter', 24), ('graupel', 1, 'temperate', 'spring', 1197),
    ('frost', 4, 'temperate', 'winter', 1301), ('rime', 1, 'continental', 'winter', 0),
    ('haze', 1, 'temperate', 'autumn', 261), ('dust', 1, 'continental', 'spring', 116),
    ('blowing_sand', 1, 'arid', 'spring', 0), ('typhoon', 4, 'subtropical_monsoon', 'summer', 279),
    ('tornado', 1, 'temperate', 'summer', 852), ('heatwave', 1, 'temperate', 'summer', 260),
    ('sunshower', 1, 'maritime', 'summer', 371),
])
def test_extended_weather_occurs_naturally(kind, seed, climate, season, t):
    s = w.weather_at(seed, 1 + t // 24, t % 24, climate, season=season, coast_distance_km=20)
    assert s['kind'] == kind
    w.validate_state(s)


def test_cyclone_eye_is_calmer_and_brighter_and_ends():
    params = dict(seed=4, day=12, hour=2, climate='tropical')
    wall = w.weather_at(**params, overrides={'kind': 'typhoon', 'cyclone': {'phase': 'eyewall'}})
    eye = w.weather_at(**params, overrides={'kind': 'typhoon', 'cyclone': {'phase': 'eye'}})
    assert eye['wind']['speed'] < wall['wind']['speed']
    assert eye['cloud_cover'] < wall['cloud_cover']
    assert eye['precipitation'] == {'type': 'none', 'rate': 0}
    w.validate_state(eye)
    seq = w.forecast(4, 1, 0, 600, 'tropical', season='summer', coast_distance_km=20)
    assert any(s['kind'] == 'typhoon' for s in seq)
    longest = run = 0
    for s in seq:
        run = run + 1 if s['kind'] == 'typhoon' else 0
        longest = max(longest, run)
    assert longest <= 72


def test_wind_belts_and_empty_batch_validation():
    for lat, east in ((15, False), (45, True), (75, False), (-45, True)):
        c = w._context(1, 'temperate', None, lat, 0, None)
        import math
        assert (math.sin(math.radians(w._flow_direction(c))) > 0) == east
    with pytest.raises(ValueError):
        w.region_weather(True, [], 1, 0)
    with pytest.raises(ValueError):
        w.region_weather(1, [], 1, 24)


@pytest.mark.parametrize('ov', [
    {'kind': 'freezing_rain', 'temperature_c': 20}, {'kind': 'rime', 'temperature_c': 5},
    {'kind': 'sunshower', 'cloud_cover': .9}, {'kind': 'typhoon', 'wind': {'speed': .1}},
    {'kind': 'clear', 'aerosol': {'type': 'sand', 'density': .8}},
    {'kind': 'rain', 'cyclone': {'phase': 'eye'}}, {'kind': 'snow', 'heat': .8},
    {'kind': 'clear', 'vortex': .5}, {'kind': 'rain', 'rainbow': .9},
    {'kind': 'typhoon', 'cyclone': {'category': 2.5}},
])
def test_extended_contradictions_are_rejected(ov):
    with pytest.raises(ValueError):
        w.weather_at(4, 1, 12, 'temperate', overrides=ov)


@pytest.mark.parametrize('precip', [{'type': 'rain'}, {'type': 'none'}, {'rate': .2}, {'rate': 0}])
def test_eye_precipitation_overrides_are_preserved(precip):
    s = w.weather_at(4, 1, 12, 'tropical', overrides={
        'kind': 'typhoon', 'cyclone': {'phase': 'eye'}, 'precipitation': precip})
    for key, value in precip.items():
        assert s['precipitation'][key] == value
    w.validate_state(s)


@pytest.mark.parametrize('precip', [{'type': 'rain', 'rate': 0}, {'type': 'none', 'rate': .2}])
def test_eye_rejects_contradictory_precipitation(precip):
    with pytest.raises(ValueError):
        w.weather_at(4, 1, 12, 'tropical', overrides={
            'kind': 'typhoon', 'cyclone': {'phase': 'eye'}, 'precipitation': precip})


def test_supported_extreme_elevation_stays_in_contract():
    for kind in ('clear', 'fog', 'overcast', 'snow', 'rime'):
        s = w.weather_at(8, 1, 3, 'polar', season='winter', lat=89, lon=0,
                         elevation=9000, overrides={'kind': kind})
        w.validate_state(s)
        assert -80 <= s['temperature_c'] <= 60


@pytest.mark.skipif(NODE is None, reason='Node required for the art preview mirror')
def test_extended_mirror_and_validator():
    cases = [{'fn': 'at', 'seed': 12, 'day': 70, 'hour': 4.25, 'climate': 'continental',
              'opts': {'lat': 42, 'lon': -179.999, 'coast_distance_km': 20,
                       'overrides': {'kind': kind}}} for kind in w.KINDS]
    cases += [{'fn': 'at', 'seed': 8, 'day': 190, 'hour': 3, 'climate': 'tropical',
               'opts': {'overrides': {'kind': 'typhoon', 'cyclone': {'phase': phase, 'category': 3}}}}
              for phase in ('outer', 'eyewall', 'eye')]
    cases += [{'fn': 'forecast', 'seed': 8, 'day': 180, 'hour': 0, 'hours': 80, 'climate': 'tropical',
               'opts': {'season': 'summer', 'coast_distance_km': 10, 'lon': 179.9, 'lat': 18}}]
    cases += [{'fn': 'at', 'seed': 4, 'day': 1, 'hour': 12, 'climate': 'tropical',
               'opts': {'overrides': {'kind': 'typhoon', 'cyclone': {'phase': 'eye'},
                                      'precipitation': precip}}}
              for precip in ({'type': 'rain'}, {'type': 'none'}, {'rate': .2}, {'rate': 0},
                             {'type': 'rain', 'rate': 0}, {'type': 'none', 'rate': .2})]
    cases += [{'fn': 'at', 'seed': 8, 'day': 1, 'hour': 3, 'climate': 'polar',
               'opts': {'season': 'winter', 'lat': 89, 'lon': 0, 'elevation': 9000,
                        'overrides': {'kind': 'clear'}}}]
    runner = _RUNNER.replace('return {ok: g.weatherAt(c.seed, c.day, c.hour, c.climate, c.opts)};',
                            'return {ok: g.validateState(g.weatherAt(c.seed, c.day, c.hour, c.climate, c.opts))};')
    result = subprocess.run([NODE, '-e', runner, JS], input=json.dumps(cases), text=True,
                            capture_output=True, check=True, timeout=60)
    # Use the existing recursive comparer to cover every field, not just kind.
    import unittest
    for case, actual in zip(cases, json.loads(result.stdout), strict=True):
        opts = case['opts']
        if case['fn'] == 'forecast':
            expected = w.forecast(case['seed'], case['day'], case['hour'], case['hours'], case['climate'], **opts)
        else:
            try:
                expected = w.weather_at(case['seed'], case['day'], case['hour'], case['climate'], **opts)
            except ValueError:
                assert 'err' in actual, actual
                continue
        assert 'err' not in actual, actual
        _same(unittest.TestCase(), expected, actual['ok'], case.get('fn', 'at'))
