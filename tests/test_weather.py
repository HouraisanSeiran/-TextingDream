# -*- coding: utf-8 -*-
"""Tests for app/weather.py and its JS mirror app/static/weather-fx/weather-gen.js."""
import json
import os
import shutil
import subprocess
import unittest

from app import weather as w

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'app', 'static', 'weather-fx', 'weather-gen.js')
CAL = {'start_day_of_year': 80, 'utc_offset': 8, 'axial_tilt_deg': 23.44}


class Determinism(unittest.TestCase):
    def test_same_args_same_state(self):
        a = w.weather_at(42, 10, 13.5, 'temperate')
        b = w.weather_at(42, 10, 13.5, 'temperate')
        self.assertEqual(a, b)
        self.assertNotEqual(w.forecast(1, 1, 0, 48, 'maritime'), w.forecast(2, 1, 0, 48, 'maritime'))

    def test_forecast_matches_weather_at(self):
        seq = w.forecast(7, 3, 22, 6, 'continental', lat=40, lon=116, calendar=CAL)
        for k, s in enumerate(seq):
            h = 22 + k
            self.assertEqual(s, w.weather_at(7, 3 + h // 24, h % 24, 'continental', lat=40, lon=116, calendar=CAL))

    def test_contract_fields(self):
        s = w.weather_at(12345, 120, 13.5, 'temperate')
        self.assertEqual(set(s), set(w._STATE_KEYS))
        self.assertEqual(set(s['time']), {'hour', 'day_of_year', 'sunrise', 'sunset', 'moon_phase'})
        self.assertEqual(set(s['wind']), {'dir_deg', 'speed', 'gust'})
        self.assertEqual(set(s['ground']), set(w.GROUND_NAMES))
        self.assertEqual(set(s['aurora']), {'strength', 'hue'})
        self.assertEqual(set(s['magic']), {'strength', 'hue', 'pulse'})
        self.assertEqual(set(s['precipitation']), {'type', 'rate'})
        w.validate_state(s)


class Continuity(unittest.TestCase):
    def test_kind_switches_and_smooth_intensity(self):
        for climate in w.CLIMATES:
            for seed in (0, 3, 99):
                seq = w.forecast(seed, 1, 0, 24 * 14, climate)
                switches = sum(a['kind'] != b['kind'] for a, b in zip(seq, seq[1:]))
                self.assertLessEqual(switches, 14 * 4, (climate, seed))
                for a, b in zip(seq, seq[1:]):
                    if a['kind'] == b['kind']:
                        self.assertLessEqual(abs(a['intensity'] - b['intensity']), 0.3, (climate, seed, a['kind']))
                    self.assertLessEqual(abs(a['temperature_c'] - b['temperature_c']), 3.0)
                    self.assertLessEqual(abs(a['precipitation']['rate'] - b['precipitation']['rate']), 0.35)

    def test_events_last_hours(self):
        seq = w.forecast(5, 1, 0, 24 * 30, 'maritime', season='autumn')
        runs, cur = [], 1
        for a, b in zip(seq, seq[1:]):
            if a['kind'] == b['kind']:
                cur += 1
            else:
                runs.append(cur)
                cur = 1
        self.assertGreater(sum(runs) / len(runs), 3)


class Climates(unittest.TestCase):
    def test_every_climate_and_season(self):
        for climate in w.CLIMATES:
            for season in w.SEASONS:
                seq = w.forecast(11, 1, 0, 24 * 3, climate, season=season)
                for s in seq:
                    w.validate_state(s)
                    self.assertEqual(s['season'], season)
                    self.assertEqual(s['climate'], climate)

    def test_season_from_day_and_hemisphere(self):
        north = w.weather_at(1, 1, 12, 'temperate', lat=45, calendar={'start_day_of_year': 196})
        south = w.weather_at(1, 1, 12, 'temperate', lat=-45, calendar={'start_day_of_year': 196})
        self.assertEqual(north['season'], 'summer')
        self.assertEqual(south['season'], 'winter')
        self.assertEqual(w.weather_at(1, 15, 12, 'temperate')['season'], 'winter')

    def test_climate_temperatures_differ(self):
        def mean(c, s):
            seq = w.forecast(2, 1, 0, 24 * 10, c, season=s)
            return sum(x['temperature_c'] for x in seq) / len(seq)
        self.assertGreater(mean('tropical', 'winter'), mean('polar', 'summer') + 10)
        self.assertGreater(mean('arid', 'summer'), mean('maritime', 'summer') + 8)
        self.assertLess(mean('continental', 'winter'), -5)

    def test_sandstorm_only_where_dusty(self):
        arid = [s['kind'] for s in w.forecast(1, 1, 0, 24 * 40, 'arid', season='summer')]
        wet = [s['kind'] for s in w.forecast(1, 1, 0, 24 * 40, 'maritime', season='summer')]
        self.assertIn('sandstorm', arid)
        self.assertNotIn('sandstorm', wet)

    def test_climate_for(self):
        self.assertEqual(w.climate_for('热带雨林'), 'tropical')
        self.assertEqual(w.climate_for(3), 'polar')
        self.assertEqual(w.climate_for('海洋', lat=55), 'maritime')
        self.assertEqual(w.climate_for('湿地', lat=10), 'tropical')
        self.assertEqual(w.climate_for(lat=-70), 'polar')
        self.assertEqual(w.climate_for(), 'temperate')
        for b in w.BIOMES:
            self.assertIn(w.climate_for(b, lat=30), w.CLIMATES)
        with self.assertRaises(ValueError):
            w.climate_for('火山')
        with self.assertRaises(ValueError):
            w.climate_for(16)


def _kinds_fit(test, s):
    """Field relations each kind must show (spec section 2 examples)."""
    k, p = s['kind'], s['precipitation']
    w.validate_state(s)
    test.assertIn(p['type'], w.PTYPES_OF.get(k, (w.PTYPE.get(k, 'none'),)), k)
    if k in ('snow', 'blizzard'):
        test.assertLessEqual(s['temperature_c'], 1)
    if k == 'storm':
        test.assertGreater(s['lightning'], 0)
        test.assertGreaterEqual(s['wind']['speed'], 0.4)
    else:
        test.assertEqual(s['lightning'], 0)
    if k == 'clear':
        test.assertEqual(p['rate'], 0)
        test.assertLessEqual(s['cloud_cover'], 0.3)
    if k == 'sandstorm':
        test.assertEqual(p['rate'], 0)
        test.assertLessEqual(s['visibility'], 0.5)
        test.assertGreaterEqual(s['wind']['speed'], 0.45)
    if k == 'blizzard':
        test.assertGreaterEqual(s['wind']['speed'], 0.5)
        test.assertLessEqual(s['visibility'], 0.4)
    if k == 'fog':
        test.assertGreaterEqual(s['fog'], 0.3)
        test.assertLessEqual(s['visibility'], 0.7)
    if p['type'] != 'none':
        test.assertGreater(p['rate'], 0)


class Overrides(unittest.TestCase):
    def test_every_kind_in_every_climate(self):
        for kind in w.KINDS:
            for climate in w.CLIMATES:
                for seed, day, hour in ((1, 10, 3), (8, 200, 15.5)):
                    s = w.weather_at(seed, day, hour, climate, overrides={'kind': kind})
                    self.assertEqual(s['kind'], kind)
                    _kinds_fit(self, s)

    def test_natural_states_fit_too(self):
        for climate in w.CLIMATES:
            for s in w.forecast(4, 1, 0, 24 * 20, climate, step=3):
                _kinds_fit(self, s)

    def test_fixed_fields_kept(self):
        ov = {'kind': 'rain', 'intensity': 0.8, 'wind': {'dir_deg': 90, 'speed': 0.3}, 'temperature_c': 12,
              'ground': {'puddles': 0.1}}
        s = w.weather_at(3, 50, 9, 'temperate', overrides=ov)
        self.assertEqual((s['intensity'], s['temperature_c'], s['wind']['dir_deg'], s['wind']['speed']),
                         (0.8, 12, 90, 0.3))
        self.assertEqual(s['ground']['puddles'], 0.1)
        self.assertGreater(s['precipitation']['rate'], 0.5)

    def test_partial_overrides_pick_matching_kind(self):
        s = w.weather_at(3, 50, 9, 'tropical', overrides={'precipitation': {'type': 'snow'}})
        self.assertIn(s['kind'], ('snow', 'blizzard'))
        self.assertLessEqual(s['temperature_c'], 1)
        s = w.weather_at(3, 50, 9, 'maritime', overrides={'temperature_c': -12, 'precipitation': {'rate': 0.6}})
        self.assertIn(s['kind'], ('snow', 'blizzard'))
        s = w.weather_at(3, 50, 9, 'temperate', overrides={'lightning': 0.7})
        self.assertEqual(s['kind'], 'storm')

    def test_forced_snow_has_snow_on_ground(self):
        s = w.weather_at(1, 180, 12, 'tropical', overrides={'kind': 'snow', 'intensity': 0.6})
        self.assertGreater(s['ground']['snow_cover'], 0.5)
        s = w.weather_at(1, 180, 12, 'temperate', overrides={'kind': 'rain', 'intensity': 0.6})
        self.assertGreater(s['ground']['wetness'], 0.9)
        self.assertGreater(s['ground']['puddles'], 0.5)

    def test_contradictions_raise(self):
        bad = [{'kind': 'snow', 'temperature_c': 30}, {'kind': 'clear', 'precipitation': {'type': 'rain'}},
               {'kind': 'storm', 'lightning': 0}, {'kind': 'clear', 'cloud_cover': 0.9},
               {'kind': 'sandstorm', 'visibility': 0.9}, {'kind': 'fog', 'wind': {'speed': 0.9}},
               {'precipitation': {'type': 'snow'}, 'temperature_c': 30},
               {'precipitation': {'type': 'none', 'rate': 0.5}},
               {'kind': 'hail', 'precipitation': {'type': 'rain'}}, {'kind': 'mana_storm', 'lightning': 0.5},
               {'intensity': 1.5}, {'fantasy_kind': 'x'}, {'wind': {'dir': 3}}, {'colour': 'red'}, {'temperature_c': 'hot'}]
        for ov in bad:
            with self.assertRaises(ValueError, msg=ov):
                w.weather_at(1, 1, 12, 'temperate', overrides=ov)
        with self.assertRaisesRegex(ValueError, 'temperature_c'):
            w.weather_at(1, 1, 12, 'temperate', overrides={'kind': 'snow', 'temperature_c': 30})

    def test_bad_arguments(self):
        for args in ((1.5, 1, 0, 'temperate'), (1, 1, 24, 'temperate'), (1, 1, 0, 'jungle'), (True, 1, 0, 'arid')):
            with self.assertRaises(ValueError):
                w.weather_at(*args)
        with self.assertRaises(ValueError):
            w.weather_at(1, 1, 0, 'arid', season='monsoon')
        with self.assertRaises(ValueError):
            w.validate_state({'kind': 'rain'})
        s = w.weather_at(1, 1, 0, 'arid')
        s['humidity'] = 1.2
        with self.assertRaises(ValueError):
            w.validate_state(s)


def _after(seq, ptypes, quiet):
    """Indexes k where precipitation of `ptypes` stopped at k and stays off for `quiet` hours."""
    out = []
    for k in range(1, len(seq) - quiet):
        if seq[k - 1]['precipitation']['type'] in ptypes and \
                all(s['precipitation']['type'] == 'none' for s in seq[k:k + quiet]):
            out.append(k)
    return out


class Ground(unittest.TestCase):
    def test_wetness_recedes_after_rain(self):
        events = 0
        for climate in ('temperate', 'maritime', 'tropical', 'subtropical_monsoon'):
            for seed in range(4):
                seq = w.forecast(seed, 1, 0, 24 * 14, climate)
                for k in _after(seq, ('rain', 'sleet'), 6):
                    events += 1
                    ws = [seq[k - 1]['ground']['wetness']] + [s['ground']['wetness'] for s in seq[k:k + 6]]
                    for x, y in zip(ws, ws[1:]):
                        self.assertLessEqual(y, x + 1e-12)
                    self.assertLess(ws[-1], ws[0])
                    self.assertGreater(ws[1], 0.05)  # it recedes, it does not vanish at once
        self.assertGreater(events, 10)

    def test_snow_cover_melts_when_warm(self):
        """Snow forced in a mild spring, then natural weather: cover drops over the following hours."""
        ov = {'kind': 'snow', 'intensity': 0.7}
        start = w.weather_at(3, 120, 10, 'temperate', overrides=ov)['ground']['snow_cover']
        self.assertGreater(start, 0.5)
        # the natural weather replays the window; build the after-snow sequence by integrating
        c = w._context(3, 'temperate', 'spring', None, None, None)
        cur = ('snow', 0.56, 0.0, 0.2, 0.9, 0.0)
        snow_seq = [w._ground(c, t, cur, {'kind': 'snow'})[2] for t in range(0, 3)]
        self.assertTrue(all(x > 0.5 for x in snow_seq))
        warm = ('none', 0.0, 8.0, 0.2, 0.3, 0.0)
        melted = w._ground(c, 0, warm, {'kind': 'clear'})[2]
        self.assertLess(melted, 0.05)

    def test_snow_cover_recedes_in_natural_thaw(self):
        drops = 0
        for climate in ('temperate', 'continental', 'highland'):
            for seed in range(6):
                seq = w.forecast(seed, 1, 0, 24 * 40, climate, step=1)
                for k in _after(seq, ('snow',), 12):
                    run = seq[k:k + 12]
                    if all(s['temperature_c'] > 1 for s in run):
                        drops += 1
                        self.assertLess(run[-1]['ground']['snow_cover'], seq[k - 1]['ground']['snow_cover'])
        self.assertGreater(drops, 0)

    def test_cold_dry_snow_persists(self):
        seq = w.forecast(1, 1, 0, 24 * 5, 'polar', season='winter')
        self.assertTrue(all(s['ground']['snow_cover'] > 0.8 for s in seq))
        seq = w.forecast(1, 1, 0, 24 * 5, 'arid', season='summer')
        self.assertTrue(all(s['ground']['snow_cover'] == 0 for s in seq))


class Time(unittest.TestCase):
    def test_default_sun(self):
        t = w.weather_at(1, 30, 7.25, 'temperate')['time']
        self.assertEqual((t['sunrise'], t['sunset'], t['hour']), (6.0, 18.0, 7.25))

    def test_solar(self):
        from app.geography import solar
        sun = solar(40, 116, 100, CAL)
        t = w.weather_at(1, 100, 12, 'temperate', lat=40, lon=116, calendar=CAL)['time']
        h, m = sun['sunrise']['time'].split(':')
        self.assertAlmostEqual(t['sunrise'], int(h) + int(m) / 60)
        h, m = sun['sunset']['time'].split(':')
        self.assertAlmostEqual(t['sunset'], int(h) + int(m) / 60)
        self.assertEqual(t['day_of_year'], sun['day_of_year'])
        self.assertLess(t['sunrise'], t['sunset'])

    def test_polar_day_and_night(self):
        summer = {'start_day_of_year': 172}
        day = w.weather_at(1, 1, 12, 'polar', lat=80, lon=0, calendar=summer)['time']
        night = w.weather_at(1, 1, 12, 'polar', lat=-80, lon=0, calendar=summer)['time']
        self.assertEqual((day['sunrise'], day['sunset']), (0.0, 24.0))
        self.assertEqual(night['sunrise'], night['sunset'])

    def test_moon_phase(self):
        a = w.weather_at(1, 1, 0, 'temperate')['time']['moon_phase']
        b = w.weather_at(1, 30, 12.72, 'temperate')['time']['moon_phase']  # 29.53 days after day 1 0:00
        self.assertAlmostEqual(a, 0.0)
        self.assertAlmostEqual(b, 0.0, places=6)
        self.assertAlmostEqual(w.weather_at(1, 15, 18.36, 'temperate')['time']['moon_phase'], 0.5, places=3)


class Section5(unittest.TestCase):
    """Spec section 5: hail, aurora, fantasy weathers, new ground covers, region_weather."""

    def test_hail_with_storm(self):
        seq = w.forecast(1, 1, 0, 24 * 30, 'tropical', season='summer')
        storm_hail = [s for s in seq if s['kind'] == 'storm' and s['precipitation']['type'] == 'hail']
        self.assertTrue(storm_hail)
        for s in storm_hail:
            self.assertGreater(s['lightning'], 0)
            _kinds_fit(self, s)
        s = w.weather_at(3, 50, 15, 'temperate', overrides={'kind': 'storm', 'precipitation': {'type': 'hail'}})
        self.assertEqual((s['kind'], s['precipitation']['type']), ('storm', 'hail'))
        self.assertGreater(s['lightning'], 0)
        s = w.weather_at(3, 50, 15, 'temperate', overrides={'kind': 'hail'})
        self.assertEqual(s['precipitation']['type'], 'hail')
        self.assertGreater(s['precipitation']['rate'], 0)

    def test_aurora_night_high_latitude_cloud_dims(self):
        cal = {'start_day_of_year': 280}
        seen = 0
        for lat in (60, 70):
            for s in w.forecast(1, 1, 0, 24 * 30, 'polar', lat=lat, lon=20, calendar=cal):
                a, tm = s['aurora']['strength'], s['time']
                if a > 0:
                    seen += 1
                    self.assertFalse(tm['sunrise'] <= tm['hour'] <= tm['sunset'], tm)  # only at night
                    self.assertLessEqual(a, 1 - s['cloud_cover'] + 1e-12)  # cloud in front dims it
        self.assertGreater(seen, 20)
        low = w.forecast(1, 1, 0, 24 * 30, 'polar', lat=40, lon=20, calendar=cal)
        self.assertTrue(all(s['aurora']['strength'] == 0 for s in low))
        for kind in ('rain', 'overcast', 'storm'):
            s = w.weather_at(1, 10, 2, 'polar', overrides={'kind': kind})
            self.assertEqual(s['aurora']['strength'], 0)
        clear = w.weather_at(1, 10, 2, 'polar', overrides={'kind': 'aurora', 'intensity': 0.8, 'cloud_cover': 0.1})
        cloudy = w.weather_at(1, 10, 2, 'polar', overrides={'kind': 'aurora', 'intensity': 0.8, 'cloud_cover': 0.45})
        self.assertGreater(clear['aurora']['strength'], cloudy['aurora']['strength'])

    def test_fantasy_only_when_allowed(self):
        for climate in w.CLIMATES:
            seq = w.forecast(2, 1, 0, 24 * 30, climate, step=2)
            self.assertFalse([s for s in seq if s['kind'] in w.FANTASY], climate)
            self.assertTrue(all(s['magic']['strength'] == 0 for s in seq))
        for f in w.FANTASY:
            kinds = {s['kind'] for s in w.forecast(2, 1, 0, 24 * 60, 'temperate', fantasy=(f,))}
            self.assertIn(f, kinds)
            self.assertFalse((kinds & set(w.FANTASY)) - {f})
            s = w.weather_at(2, 5, 12, 'arid', overrides={'kind': f})
            self.assertEqual(s['kind'], f)
            _kinds_fit(self, s)
        self.assertGreater(w.weather_at(2, 5, 12, 'arid', overrides={'kind': 'mana_storm'})['magic']['strength'], 0)
        with self.assertRaises(ValueError):
            w.weather_at(1, 1, 0, 'temperate', fantasy=('dragon_fire',))
        with self.assertRaises(ValueError):
            w.weather_at(1, 1, 0, 'temperate', fantasy='miasma')

    def test_new_ground_covers_accumulate(self):
        """hail_cover / ash_cover / mana_residue build up while it falls and fade over hours afterwards."""
        for kind, name in (('hail', 'hail_cover'), ('ashfall', 'ash_cover'), ('mana_storm', 'mana_residue')):
            forced = w.weather_at(1, 100, 12, 'temperate', overrides={'kind': kind, 'intensity': 0.7})['ground']
            self.assertGreater(forced[name], 0.5, kind)
            c = w._context(1, 'temperate', 'summer', None, None, None, fantasy=w.FANTASY)
            g = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            idx = w.GROUND_NAMES.index(name)
            v = list(w._core(kind, 0.7, w._natural(c, 0)))
            ups = []
            for _ in range(4):
                g = w._step(g, tuple(v))
                ups.append(g[idx])
            self.assertTrue(all(b > a for a, b in zip(ups, ups[1:])), (kind, ups))  # accumulates
            dry = ('none', 0.0, 12.0, 0.2, 0.3, 0.0, 0.0, 0.0)
            downs = [g[idx]]
            for _ in range(6):
                g = w._step(g, dry)
                downs.append(g[idx])
            self.assertTrue(all(b <= a for a, b in zip(downs, downs[1:])), (kind, downs))
            self.assertGreater(downs[1], 0.5 * downs[0], kind)  # recedes slowly, does not vanish at once
            self.assertLess(downs[-1], downs[0], kind)
        seq = w.forecast(1, 1, 0, 24 * 30, 'tropical', season='summer')
        k = next(i for i, s in enumerate(seq) if s['precipitation']['type'] == 'hail')
        self.assertGreater(seq[k]['ground']['hail_cover'], 0)
        end = next(j for j in range(k, len(seq)) if seq[j]['precipitation']['type'] != 'hail')
        self.assertGreater(seq[end]['ground']['hail_cover'], 0)  # still lies after the hail stopped
        plain = w.forecast(1, 1, 0, 24 * 10, 'temperate')
        self.assertTrue(all(s['ground']['ash_cover'] == 0 and s['ground']['mana_residue'] == 0 for s in plain))

    def test_region_weather_continuous_and_deterministic(self):
        cells = [{'id': i, 'lon': 100 + 0.5 * i, 'lat': 45, 'climate': 'temperate'} for i in range(5)]
        a = w.region_weather(9, cells, 20, 14, calendar=CAL)
        self.assertEqual(a, w.region_weather(9, cells, 20, 14, calendar=CAL))
        self.assertEqual(len(a), 5)
        for cell, s in zip(cells, a):
            self.assertEqual(s, w.weather_at(9, 20, 14, 'temperate', lon=cell['lon'], lat=cell['lat'], calendar=CAL))
        # neighbouring cells (0.5 degree apart) see the same front shifted by ~1 hour, far cells differ
        shifts = [w._context(9, 'temperate', None, c['lat'], c['lon'], None).shift for c in cells]
        for x, y in zip(shifts, shifts[1:]):
            self.assertLess(abs(x - y), 2.0)
        near, far, n = 0, 0, 0
        for h in range(0, 24 * 20, 3):
            day, hour = 1 + h // 24, h % 24
            p = [s['precipitation']['rate'] > 0 for s in
                 w.region_weather(9, [cells[0], cells[1], {'id': 'far', 'lon': 160, 'lat': -10, 'climate': 'temperate'}],
                                  day, hour)]
            n += 1
            near += p[0] == p[1]
            far += p[0] == p[2]
        self.assertGreater(near / n, 0.85)
        self.assertGreater(near, far)
        # fronts drift east with the westerlies: a place 2 degrees east sees the same rain a few hours later
        west = [s['precipitation']['rate'] for s in w.forecast(5, 1, 0, 24 * 20, 'temperate', lat=48, lon=10)]
        east = [s['precipitation']['rate'] for s in w.forecast(5, 1, 0, 24 * 20, 'temperate', lat=48, lon=12)]
        lags = range(-12, 13)
        score = [sum(west[i] * east[i + lag] for i in range(12, len(west) - 12)) for lag in lags]
        self.assertGreater(lags[score.index(max(score))], 0)
        for bad in ([{'id': 1, 'lon': 0, 'lat': 0}], [{'id': 1, 'lon': 0, 'lat': 0, 'climate': 'arid', 'x': 1}],
                    [{'id': 1, 'lon': 0, 'lat': 0, 'climate': 'arid'}, {'id': 1, 'lon': 1, 'lat': 0, 'climate': 'arid'}],
                    'cells', [{'id': 1, 'lon': 200, 'lat': 0, 'climate': 'arid'}]):
            with self.assertRaises(ValueError, msg=bad):
                w.region_weather(1, bad, 1, 0)

    def test_elevation_lapse(self):
        low = w.weather_at(4, 30, 13, 'highland', overrides={'kind': 'clear'}, elevation=3500)
        high = w.weather_at(4, 30, 13, 'highland', overrides={'kind': 'clear'}, elevation=5500)
        self.assertAlmostEqual(low['temperature_c'] - high['temperature_c'], 13.0, places=6)


NODE = shutil.which('node')
_RUNNER = r"""
const g = require(process.argv[1]);
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = cases.map(c => {
  try {
    if (c.fn === 'forecast') return {ok: g.forecast(c.seed, c.day, c.hour, c.hours, c.climate, c.opts)};
    if (c.fn === 'region') return {ok: g.regionWeather(c.seed, c.cells, c.day, c.hour, c.opts)};
    return {ok: g.weatherAt(c.seed, c.day, c.hour, c.climate, c.opts)};
  } catch (e) { return {err: String(e.message)}; }
});
process.stdout.write(JSON.stringify(out));
"""


def _mirror_cases():
    cases = []
    kinds = list(w.KINDS)
    climates = list(w.CLIMATES)
    for k in range(36):
        c = {'fn': 'at', 'seed': [0, 1, 42, 12345, 2 ** 31 + 7, -5, 987654321][k % 7] + k,
             'day': [1, 2, 37, 120, 200, 365, 800, -3][k % 8], 'hour': [0, 0.5, 6.25, 13.5, 23.75][k % 5],
             'climate': climates[k % 9], 'opts': {}}
        if k % 3 == 1:
            c['opts']['season'] = w.SEASONS[k % 4]
        if k % 4 == 2:
            c['opts'].update(lat=[45.5, -33.9, 70.2, 10][k % 4 // 2 + (k % 3)], lon=[116.4, -70, 151.2][k % 3],
                             calendar={'start_day_of_year': 1 + (k * 37) % 365, 'utc_offset': (k % 5) - 2})
        if k % 2 == 1:
            c['opts']['overrides'] = {'kind': kinds[k % len(kinds)]}
        cases.append(c)
    cases += [
        {'fn': 'at', 'seed': 3, 'day': 50, 'hour': 9, 'climate': 'temperate',
         'opts': {'overrides': {'kind': 'rain', 'intensity': 0.8, 'wind': {'dir_deg': 90, 'speed': 0.3}}}},
        {'fn': 'at', 'seed': 3, 'day': 50, 'hour': 9, 'climate': 'maritime',
         'opts': {'overrides': {'temperature_c': -12, 'precipitation': {'rate': 0.6}}}},
        {'fn': 'at', 'seed': 3, 'day': 50, 'hour': 9, 'climate': 'temperate', 'opts': {'overrides': {'lightning': 0.7}}},
        {'fn': 'at', 'seed': 1, 'day': 1, 'hour': 12, 'climate': 'polar',
         'opts': {'lat': 80, 'lon': 0, 'calendar': {'start_day_of_year': 172}}},
        {'fn': 'forecast', 'seed': 9, 'day': 10, 'hour': 20, 'hours': 72, 'climate': 'arid', 'opts': {}},
        {'fn': 'forecast', 'seed': 77, 'day': 300, 'hour': 0, 'hours': 96, 'climate': 'continental',
         'opts': {'lat': -40, 'lon': 20, 'calendar': CAL}},
        {'fn': 'forecast', 'seed': 5, 'day': 1, 'hour': 0, 'hours': 48, 'climate': 'subtropical_monsoon',
         'opts': {'season': 'summer', 'step': 2.5}},
        # section 5: hail, aurora, fantasy, elevation, region
        {'fn': 'forecast', 'seed': 2, 'day': 1, 'hour': 0, 'hours': 96, 'climate': 'tropical',
         'opts': {'season': 'summer'}},
        {'fn': 'forecast', 'seed': 1, 'day': 1, 'hour': 12, 'hours': 72, 'climate': 'polar',
         'opts': {'lat': 70, 'lon': 20, 'calendar': {'start_day_of_year': 280}}},
        {'fn': 'forecast', 'seed': 2, 'day': 1, 'hour': 0, 'hours': 120, 'climate': 'temperate',
         'opts': {'fantasy': list(w.FANTASY), 'step': 3}},
        {'fn': 'forecast', 'seed': 6, 'day': 40, 'hour': 5, 'hours': 48, 'climate': 'highland',
         'opts': {'elevation': 4800, 'lat': 30, 'lon': 90}},
        {'fn': 'at', 'seed': 3, 'day': 50, 'hour': 22, 'climate': 'temperate',
         'opts': {'overrides': {'kind': 'storm', 'precipitation': {'type': 'hail'}}}},
        {'fn': 'at', 'seed': 3, 'day': 50, 'hour': 22, 'climate': 'temperate',
         'opts': {'fantasy': ['mana_storm'], 'overrides': {'magic': {'strength': 0.6}}}},
        {'fn': 'region', 'seed': 11, 'day': 30, 'hour': 17.5, 'cells': _grid(3, 'continental'),
         'opts': {'calendar': CAL}},
    ]
    return cases


def _grid(n, climate, lon0=100.0, lat0=40.0, d=1.0):
    return [{'id': f'{i},{j}', 'lon': lon0 + i * d, 'lat': lat0 + j * d, 'climate': climate,
             'elevation': 300 + 50 * (i + j)} for j in range(n) for i in range(n)]


def _py(c):
    o = c['opts']
    if c['fn'] == 'region':
        return w.region_weather(c['seed'], c['cells'], c['day'], c['hour'], **o)
    kw = {k: o[k] for k in ('season', 'overrides', 'lat', 'lon', 'calendar', 'fantasy', 'elevation') if k in o}
    if c['fn'] == 'forecast':
        return w.forecast(c['seed'], c['day'], c['hour'], c['hours'], c['climate'], step=o.get('step', 1), **kw)
    return w.weather_at(c['seed'], c['day'], c['hour'], c['climate'], **kw)


def _same(test, a, b, path):
    if isinstance(a, dict):
        test.assertEqual(set(a), set(b), path)
        for k in a:
            _same(test, a[k], b[k], path + '.' + k)
    elif isinstance(a, list):
        test.assertEqual(len(a), len(b), path)
        for i, (x, y) in enumerate(zip(a, b)):
            _same(test, x, y, f'{path}[{i}]')
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        test.assertAlmostEqual(a, b, delta=1e-6, msg=path)
    else:
        test.assertEqual(a, b, path)


@unittest.skipIf(NODE is None, 'node 不在 PATH')
class JsMirror(unittest.TestCase):
    def test_python_and_js_agree(self):
        cases = _mirror_cases()
        self.assertGreaterEqual(len(cases), 30)
        r = subprocess.run([NODE, '-e', _RUNNER, JS], input=json.dumps(cases), capture_output=True,
                           text=True, encoding='utf-8', timeout=120, check=True)
        got = json.loads(r.stdout)
        states = 0
        for c, js in zip(cases, got):
            self.assertIn('ok', js, (c, js))
            py = _py(c)
            _same(self, py, js['ok'], json.dumps(c, ensure_ascii=False))
            states += len(py) if isinstance(py, list) else 1
        self.assertGreater(states, 300)

    def test_js_rejects_contradiction(self):
        cases = [{'fn': 'at', 'seed': 1, 'day': 1, 'hour': 0, 'climate': 'temperate',
                  'opts': {'overrides': {'kind': 'snow', 'temperature_c': 30}}}]
        r = subprocess.run([NODE, '-e', _RUNNER, JS], input=json.dumps(cases), capture_output=True,
                           text=True, encoding='utf-8', timeout=60, check=True)
        self.assertIn('矛盾', json.loads(r.stdout)[0]['err'])


if __name__ == '__main__':
    unittest.main()
