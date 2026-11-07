# -*- coding: utf-8 -*-
"""Weather generation: deterministic hourly weather states for the weather art layers.

``weather_at`` returns one state in the contract of ``docs/weather-spec.md`` (sections 1, 5 and 8,
including all 11 ``ground`` covers); ``forecast`` returns an
hourly sequence and ``region_weather`` the states of many map cells at one moment. Everything is
derived from the seed with a small integer-hash value noise (no ``random``), so the same
arguments give the same state and the JS mirror ``app/static/weather-fx/weather-gen.js``
reproduces it (float tolerance 1e-6).

Model, in short:

* Slow value noise over "signal time" drives latent fields: a front signal (periods 40 h / 13 h)
  decides precipitation, a convective signal plus an afternoon peak decides thunderstorms and
  hail, others give cloud, temperature anomaly, fog, wind, dust, aurora activity and (only when
  allowed through ``fantasy``) the fantasy weathers. Kinds are thresholds on these smooth
  signals, so fronts last hours to days and intensity rises from 0 at the edge of an event.
* With lat/lon, a periodic 3D noise field advects with the wind belts: east in mid-latitudes,
  west in tropical/polar belts, with smooth transitions and continuity across the dateline.
  Neighbouring places therefore share fronts (``region_weather``).
* Climate tables give, per season, mean daily min/max temperature and tendencies. Without an
  explicit ``season`` the tables are blended along the year (southern hemisphere shifted by half
  a year). ``elevation`` applies a 6.5 C/km lapse relative to the climate's reference height.
* ``ground`` is integrated hour by hour from an anchor 216-240 hours back (the anchor moves by
  whole days, so consecutive hours share the integration): rain wets, dry hours evaporate, snow
  accumulates when cold, melts when warm and relaxes towards the climate's baseline cover, hail
  melts fast, ash and mana residue fade slowly. Ice, frost, rime, dust and graupel also accumulate
  and decay. This finite history is a visual approximation; it does not preserve ancient deposits.
* ``overrides`` fix fields; the remaining fields are derived to fit the chosen kind. The
  overridden weather is treated as having lasted the whole look-back window (a forced ``snow``
  comes with snow on the ground). Contradictions raise ``ValueError``.
* Fourth batch (spec section 8): a second climate table ``EXTRA`` gives per-season tendencies of
  freezing rain, graupel, haze, floating dust, blowing sand, typhoons, tornadoes, heatwaves,
  sun showers and rime. Freezing rain / graupel replace part of the cold precipitation, tornadoes
  appear inside strong storms, dust and blowing sand are wider bands of the sandstorm signal,
  haze needs calm air away from fronts, frost forms in clear cold nights and melts in daylight,
  while rime needs cold humid fog. A heatwave adds a multi-day warm anomaly.
  Typhoons require explicit coast_distance_km <= 200 and a suitable climate/season. Seeded events
  last 48-72 hours, with outer / eyewall / eye phases approximated by progress and spatial offset.
* Context LRU and bounded history caches reuse nearby hours at the same place. Cache eviction
  never changes the generated value; cold queries still replay the finite ground history.

Boundaries: a worldbuilding approximation for visuals, not a meteorological model: no pressure
systems, terrain blocking, rain shadows, upper-air warm layers or pollutant transport.
Aurora activity comes from the climate table (polar / continental winter / highland); with a known
latitude it is also faded out below 65 degrees (zero below 50).
The module is not imported by ``runtime.py`` / ``web.py`` and writes nothing.
"""
import math
import json
import threading
from collections import OrderedDict

from .geography import Calendar, solar

BATCH4 = ('freezing_rain', 'graupel', 'frost', 'rime', 'haze', 'dust', 'blowing_sand', 'typhoon', 'tornado',
          'heatwave', 'sunshower')
NATURAL = ('clear', 'cloudy', 'overcast', 'fog', 'drizzle', 'rain', 'storm', 'snow', 'blizzard', 'sleet',
           'sandstorm', 'hail', 'aurora') + BATCH4
FANTASY = ('mana_storm', 'spirit_mist', 'miasma', 'ashfall')
KINDS = NATURAL + FANTASY
SEASONS = ('spring', 'summer', 'autumn', 'winter')
PRECIP_TYPES = ('none', 'rain', 'snow', 'sleet', 'hail', 'freezing_rain', 'graupel')
PTYPE = {'drizzle': 'rain', 'rain': 'rain', 'storm': 'rain', 'snow': 'snow', 'blizzard': 'snow', 'sleet': 'sleet',
         'hail': 'hail', 'freezing_rain': 'freezing_rain', 'graupel': 'graupel', 'typhoon': 'rain',
         'tornado': 'rain', 'sunshower': 'rain'}
PTYPES_OF = {'storm': ('rain', 'hail'), 'tornado': ('rain', 'hail')}  # kinds allowing several types
WET_TYPES = ('rain', 'sleet', 'hail', 'freezing_rain', 'graupel')
GROUND_NAMES = ('wetness', 'puddles', 'snow_cover', 'hail_cover', 'ash_cover', 'mana_residue',
                'glaze', 'frost', 'rime', 'dust_cover', 'graupel')
AEROSOL_TYPES = ('none', 'haze', 'dust', 'sand')
CYCLONE_PHASES = ('none', 'outer', 'eyewall', 'eye')
LIQUID_KINDS = ('drizzle', 'rain', 'storm', 'sunshower', 'tornado')  # rain that can leave a rainbow
FOGGY = ('fog', 'rime', 'spirit_mist', 'miasma')
WINDOW_HOURS = 216
ANCHOR_HOURS = 24
SNOW_RELAX = 0.02
FRONT_KMH = 35.0
LAPSE_C_PER_M = 0.0065
MOON_PERIOD_DAYS = 29.53
TAU = 2 * math.pi

# Per season: (tlo, thi, wet, cloud, storm, fog, wind, dust, snow, aurora)
#   tlo/thi = mean daily min/max temperature (C); wet = share of hours with precipitation (approx.);
#   cloud/storm/fog/wind/dust/aurora = tendencies 0-1; snow = baseline snow cover on the ground.
# dir = prevailing direction the wind blows TO (northern hemisphere; mirrored N/S in the south);
# elev = reference height (m) of the table, used by the elevation lapse.
CLIMATE_FIELDS = ('tlo', 'thi', 'wet', 'cloud', 'storm', 'fog', 'wind', 'dust', 'snow', 'aurora')
CLIMATES = {
    'temperate': {'dir': 80, 'elev': 200,
        'spring': (4, 15, .32, .55, .10, .15, .35, 0, 0, 0), 'summer': (16, 28, .30, .45, .30, .08, .25, 0, 0, 0),
        'autumn': (6, 17, .33, .55, .08, .25, .35, 0, 0, 0), 'winter': (-5, 4, .28, .60, 0, .25, .40, 0, .25, 0)},
    'continental': {'dir': 100, 'elev': 300,
        'spring': (0, 13, .25, .50, .08, .10, .45, 0, .10, 0), 'summer': (14, 28, .25, .40, .28, .05, .30, 0, 0, 0),
        'autumn': (0, 12, .22, .50, .05, .15, .40, 0, .05, 0),
        'winter': (-20, -8, .22, .55, 0, .15, .45, 0, .60, .35)},
    'maritime': {'dir': 70, 'elev': 100,
        'spring': (5, 13, .42, .70, .04, .20, .50, 0, 0, 0), 'summer': (11, 19, .38, .65, .06, .15, .40, 0, 0, 0),
        'autumn': (7, 14, .50, .75, .05, .25, .55, 0, 0, 0), 'winter': (1, 7, .50, .78, .03, .25, .60, 0, .05, 0)},
    'mediterranean': {'dir': 150, 'elev': 200,
        'spring': (10, 20, .20, .40, .06, .08, .30, 0, 0, 0), 'summer': (19, 31, .04, .15, .04, .03, .30, 0, 0, 0),
        'autumn': (13, 23, .22, .40, .10, .08, .30, 0, 0, 0), 'winter': (5, 13, .38, .60, .04, .12, .40, 0, 0, 0)},
    'subtropical_monsoon': {'dir': 330, 'elev': 200,
        'spring': (13, 22, .40, .65, .12, .20, .30, 0, 0, 0), 'summer': (25, 33, .50, .65, .40, .05, .30, 0, 0, 0),
        'autumn': (16, 25, .22, .45, .10, .10, .30, 0, 0, 0), 'winter': (3, 11, .22, .60, .02, .25, .35, 0, .02, 0)},
    'tropical': {'dir': 260, 'elev': 200,
        'spring': (23, 32, .30, .50, .35, .05, .25, 0, 0, 0), 'summer': (23, 30, .55, .75, .45, .05, .30, 0, 0, 0),
        'autumn': (23, 31, .45, .65, .40, .05, .30, 0, 0, 0), 'winter': (22, 31, .20, .40, .20, .05, .25, 0, 0, 0)},
    'arid': {'dir': 200, 'elev': 500,
        'spring': (14, 30, .04, .20, .03, .01, .45, .25, 0, 0), 'summer': (25, 42, .02, .10, .04, 0, .50, .30, 0, 0),
        'autumn': (14, 30, .04, .18, .03, .01, .40, .20, 0, 0), 'winter': (3, 18, .06, .25, 0, .03, .40, .12, 0, 0)},
    'highland': {'dir': 90, 'elev': 3500,
        'spring': (-3, 12, .20, .50, .12, .15, .55, .08, .15, .15),
        'summer': (5, 18, .35, .60, .30, .15, .45, .03, 0, .05),
        'autumn': (-3, 11, .15, .40, .08, .15, .50, .06, .10, .20),
        'winter': (-15, 0, .12, .40, 0, .10, .60, .10, .50, .30)},
    'polar': {'dir': 240, 'elev': 100,
        'spring': (-25, -12, .20, .60, 0, .15, .60, 0, .90, .60), 'summer': (-2, 5, .28, .70, 0, .30, .50, 0, .40, .10),
        'autumn': (-18, -7, .25, .65, 0, .20, .60, 0, .80, .75),
        'winter': (-38, -26, .18, .55, 0, .10, .65, 0, .95, .95)},
}
# Fourth batch, per season: (frz, grp, haze, fdust, blow, typh, torn, heat, sunsh, rime)
#   frz / grp = share of the precipitation hours inside the freezing-rain (-4..0 C) / graupel (-2..3 C)
#   window that turn into freezing rain / graupel; haze, fdust (floating dust), blow (blowing sand),
#   heat (heatwave anomaly), sunsh (sun shower) = shares of hours; typh = chance that a typhoon slot
#   (CYC_SLOT_H hours) holds a cyclone; torn = share of strong-storm hours with a tornado;
#   rime = 1 where freezing fog turns into rime.
EXTRA_FIELDS = ('frz', 'grp', 'haze', 'fdust', 'blow', 'typh', 'torn', 'heat', 'sunsh', 'rime')
_X0 = (0,) * 10


def _x(**kw):
    return tuple(kw.get(f, 0) for f in EXTRA_FIELDS)


EXTRA = {
    'temperate': {'spring': _x(grp=.25, torn=.03), 'summer': _x(torn=.03, heat=.08),
                  'autumn': _x(grp=.05, haze=.06), 'winter': _x(frz=.2, grp=.2, haze=.12)},
    'continental': {'spring': _x(grp=.25, haze=.05, fdust=.06, torn=.06), 'summer': _x(torn=.05, heat=.1),
                    'autumn': _x(grp=.1, haze=.08), 'winter': _x(frz=.1, grp=.15, haze=.15, rime=1)},
    'maritime': {'spring': _x(grp=.2, sunsh=.04), 'summer': _x(heat=.04, sunsh=.04),
                 'autumn': _x(grp=.1, sunsh=.04), 'winter': _x(grp=.3, sunsh=.02)},
    'mediterranean': {'spring': _x(grp=.1), 'summer': _x(heat=.12), 'autumn': _X0,
                      'winter': _x(grp=.15)},
    'subtropical_monsoon': {'spring': _x(haze=.06, sunsh=.04), 'summer': _x(typh=.25, heat=.1, sunsh=.06),
                            'autumn': _x(haze=.06, typh=.2, sunsh=.04),
                            'winter': _x(frz=.25, grp=.1, haze=.15)},
    'tropical': {'spring': _x(heat=.06, sunsh=.06), 'summer': _x(typh=.25, heat=.03, sunsh=.08),
                 'autumn': _x(typh=.3, sunsh=.06), 'winter': _x(sunsh=.06)},
    'arid': {'spring': _x(fdust=.12, blow=.12), 'summer': _x(fdust=.08, blow=.1, heat=.12),
             'autumn': _x(fdust=.08, blow=.1), 'winter': _x(fdust=.06, blow=.06)},
    'highland': {'spring': _x(grp=.35), 'summer': _x(grp=.3), 'autumn': _x(grp=.3), 'winter': _x(grp=.3, rime=1)},
    'polar': {'spring': _x(grp=.15), 'summer': _x(grp=.15), 'autumn': _x(grp=.15), 'winter': _x(rime=1)},
}
TYPHOON_CLIMATES = tuple(k for k, v in EXTRA.items() if any(v[s][5] > 0 for s in SEASONS))
CYC_MAX = max(v[s][5] for v in EXTRA.values() for s in SEASONS)
CYC_SLOT_H = 240.0  # at most one typhoon per slot of cyclone time
CYC_DEG = 8.0  # cell size (degrees) of the noise whose 0.5 contour is a typhoon track
CYC_TRACK = 0.12  # half-width of that contour band in noise units (lateral core radius)
# Cyclones move west at about 20 km/h: hours of cyclone-time shift per degree of longitude.
CYC_H_PER_DEG = 111.32 * 0.94 / 20.0
CYC_BAND = 1.4  # rain bands reach out to this normalised distance (core = 1)
DUST_KINDS = ('dust', 'blowing_sand', 'sandstorm')
RAINBOW_KINDS = ('clear', 'cloudy', 'sunshower')  # sun out, so a bow can show
HEAT_KINDS = ('clear', 'cloudy', 'heatwave', 'haze', 'dust')  # kinds that may carry heat shimmer
# kind -> (aerosol type, density a + b * intensity)
AEROSOL_OF = {'haze': ('haze', .2, .75), 'dust': ('dust', .15, .55), 'blowing_sand': ('sand', .3, .4),
              'sandstorm': ('sand', .55, .45)}
# Blend segments along the (northern) year, 0-based day: season centres winter 15, spring 105,
# summer 197, autumn 288; x runs 15..380 (days before 15 are shifted by +365).
_SEGMENTS = ((15, 90, 'winter', 'spring'), (105, 92, 'spring', 'summer'),
             (197, 91, 'summer', 'autumn'), (288, 92, 'autumn', 'winter'))
# Typical intensity range used when a kind is forced but the natural weather is a different kind.
DEFAULT_INTENSITY = {'clear': (.02, .25), 'cloudy': (.35, .65), 'overcast': (.75, .95), 'fog': (.4, .9),
                     'drizzle': (.08, .28), 'rain': (.35, .85), 'storm': (.3, .9), 'snow': (.2, .7),
                     'blizzard': (.65, 1.0), 'sleet': (.2, .6), 'sandstorm': (.4, .9), 'hail': (.35, .85),
                     'aurora': (.4, .9), 'mana_storm': (.3, .9), 'spirit_mist': (.3, .8), 'miasma': (.3, .8),
                     'ashfall': (.3, .8), 'freezing_rain': (.2, .7), 'graupel': (.2, .7), 'frost': (.3, .8),
                     'rime': (.3, .8), 'haze': (.3, .8), 'dust': (.3, .7), 'blowing_sand': (.3, .7),
                     'typhoon': (.4, .9), 'tornado': (.4, .9), 'heatwave': (.3, .8), 'sunshower': (.2, .6)}

# civ-atlas biome names in civ-atlas src/gen/biomes.ts order (see app/static/map-art/manifest.json).
BIOMES = ('海洋', '湖泊', '海冰', '冰原', '苔原', '针叶林', '寒漠', '温带荒漠', '草原', '温带森林',
          '温带雨林', '热带荒漠', '稀树草原', '热带季雨林', '热带雨林', '湿地')
# None = decided by latitude (see climate_for).
BIOME_CLIMATE = {'海洋': None, '湖泊': None, '海冰': 'polar', '冰原': 'polar', '苔原': 'polar',
                 '针叶林': 'continental', '寒漠': 'arid', '温带荒漠': 'arid', '草原': 'continental',
                 '温带森林': 'temperate', '温带雨林': 'maritime', '热带荒漠': 'arid', '稀树草原': 'tropical',
                 '热带季雨林': 'tropical', '热带雨林': 'tropical', '湿地': None}
CLOUD_BAND = {'clear': (0.0, 0.3), 'cloudy': (0.3, 0.7), 'overcast': (0.7, 1.0)}
# Kinds tried after the natural kind when overrides rule it out (kind not forced).
RELATED = {'clear': ('cloudy', 'overcast'), 'cloudy': ('clear', 'overcast'), 'overcast': ('cloudy', 'clear', 'drizzle'),
           'fog': ('overcast', 'cloudy', 'clear'), 'drizzle': ('rain', 'sleet', 'snow'),
           'rain': ('snow', 'sleet', 'storm', 'drizzle'), 'storm': ('rain', 'hail', 'blizzard', 'snow'),
           'snow': ('sleet', 'rain'), 'blizzard': ('snow', 'storm', 'rain'), 'sleet': ('rain', 'snow'),
           'sandstorm': ('clear', 'cloudy'), 'hail': ('storm', 'rain', 'sleet'), 'aurora': ('clear', 'cloudy'),
           'mana_storm': ('overcast', 'storm'), 'spirit_mist': ('fog', 'overcast'), 'miasma': ('fog', 'overcast'),
           'ashfall': ('overcast', 'cloudy'), 'freezing_rain': ('sleet', 'rain', 'snow'),
           'graupel': ('snow', 'sleet', 'hail'), 'frost': ('clear', 'cloudy'), 'rime': ('fog', 'frost'),
           'haze': ('fog', 'cloudy', 'clear'), 'dust': ('blowing_sand', 'haze', 'clear'),
           'blowing_sand': ('dust', 'sandstorm'), 'typhoon': ('storm', 'rain'), 'tornado': ('storm', 'hail', 'rain'),
           'heatwave': ('clear', 'cloudy'), 'sunshower': ('rain', 'drizzle', 'clear')}
OVERRIDE_FIELDS = {'kind': None, 'intensity': (0, 1), 'cloud_cover': (0, 1), 'fog': (0, 1), 'humidity': (0, 1),
                   'visibility': (0, 1), 'lightning': (0, 1), 'temperature_c': (-80, 60), 'rainbow': (0, 1),
                   'heat': (0, 1), 'vortex': (0, 1)}
# numeric (lo, hi) ranges, or tuples of allowed strings
OVERRIDE_NESTED = {'wind': {'dir_deg': (0, 360), 'speed': (0, 1), 'gust': (0, 1)},
                   'precipitation': {'type': PRECIP_TYPES, 'rate': (0, 1)},
                   'ground': {g: (0, 1) for g in GROUND_NAMES},
                   'aurora': {'strength': (0, 1), 'hue': (0, 1)},
                   'magic': {'strength': (0, 1), 'hue': (0, 1), 'pulse': (0, 1)},
                   'aerosol': {'type': AEROSOL_TYPES, 'density': (0, 1)},
                   'cyclone': {'category': (1, 5), 'phase': CYCLONE_PHASES[1:]}}

# ---------------------------------------------------------------- integer-hash value noise
M32 = 0xFFFFFFFF


def _h32(x):
    """32-bit integer mix (same constants as WeatherNoise.hash32 in noise.js)."""
    x &= M32
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & M32
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & M32
    return x ^ (x >> 16)


def _key(seed, ch):
    return _h32((seed + (ch + 1) * 0x9E3779B1) & M32)


def _lattice(key, i):
    return _h32((key + i * 0x85EBCA6B) & M32) / 4294967296.0


def _lattice2(key, i, j):
    return _h32((key + i * 0x85EBCA6B + j * 0xC2B2AE35) & M32) / 4294967296.0


def _smooth(f):
    return f * f * (3 - 2 * f)


def _vn(key, x):
    """1D value noise in [0,1): smoothstep between hashed lattice values."""
    i = math.floor(x)
    a = _lattice(key, i)
    b = _lattice(key, i + 1)
    return a + (b - a) * _smooth(x - i)


def _vn2(key, x, y):
    """2D value noise in [0,1) (smoothstep-bilinear)."""
    i = math.floor(x)
    j = math.floor(y)
    fx = _smooth(x - i)
    fy = _smooth(y - j)
    a = _lattice2(key, i, j)
    b = _lattice2(key, i + 1, j)
    c = _lattice2(key, i, j + 1)
    d = _lattice2(key, i + 1, j + 1)
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy


def _sig(seed, ch, t, p1, p2):
    """Two-octave slow signal (periods p1, p2 hours)."""
    return 0.65 * _vn(_key(seed, ch), t / p1) + 0.35 * _vn(_key(seed, ch + 50), t / p2)


# Quantiles of _sig at k/20 (measured offline over many seeds); _cdf maps _sig to ~uniform [0,1]
# so that "u > 1 - share" holds for about `share` of the hours.
_Q = (0.0, 0.1991, 0.2557, 0.2972, 0.3319, 0.3627, 0.3916, 0.4192, 0.4465, 0.4733, 0.4997,
      0.5261, 0.5529, 0.5801, 0.6083, 0.6374, 0.6687, 0.7039, 0.7455, 0.8020, 1.0)


def _cdf(x):
    q = _Q
    if x <= q[0]:
        return 0.0
    if x >= q[20]:
        return 1.0
    k = 0
    while x > q[k + 1]:
        k += 1
    return (k + (x - q[k]) / (q[k + 1] - q[k])) / 20


def _u(seed, ch, t, p1, p2):
    return _cdf(_sig(seed, ch, t, p1, p2))


def _clamp01(x):
    return min(1.0, max(0.0, x))


def _clamp(x, lo, hi):
    return min(hi, max(lo, x))


def _mod(x, m):
    r = math.fmod(x, m)
    if r < 0:
        r += m
    return r



def _params(climate, season, doy0, south):
    """Climate parameters at a 0-based fractional day of year: (tuple, season label)."""
    table = CLIMATES[climate]
    if season is not None:
        return table[season], season
    x = doy0
    if south:
        x = _mod(x + 182.5, 365)
    if x < 15:
        x += 365
    for start, length, a, b in _SEGMENTS:
        if x < start + length:
            s = _smooth((x - start) / length)
            pa, pb = table[a], table[b]
            vals = tuple(pa[i] + (pb[i] - pa[i]) * s for i in range(len(CLIMATE_FIELDS)))
            return vals, (a if x - start < length / 2 else b)
    return table['winter'], 'winter'


def _lv(u, share, floor=0.25):
    """Event level from a ~uniform signal: 0 at the edge of the top `share`, rising to 1.

    The denominator is at least `floor` so rare events cannot jump to full intensity within
    an hour; rare events stay weaker instead.
    """
    if share <= 0 or u <= 1 - share:
        return 0.0
    return min(1.0, (u - (1 - share)) / max(share, floor))


def _ramp(u, share):
    """0 -> 1 over the 0.35 band of the signal just below an event edge (clouds build up first)."""
    if share <= 0:
        return 0.0
    return _clamp01((u - (1 - share) + 0.35) / 0.35)


# Fields each kind must keep (flattened override names). Derived values are clamped into these
# ranges; overridden values outside them raise ValueError.
AURORA_KINDS = ('clear', 'cloudy', 'aurora')  # kinds that carry aurora.strength (sky overlay)
_NO_PRECIP = {'precipitation.rate': (0, 0), 'lightning': (0, 0)}
KIND_RANGE = {
    'clear': dict(_NO_PRECIP, intensity=(0, .3), cloud_cover=(0, .3), fog=(0, .3), visibility=(.5, 1)),
    'cloudy': dict(_NO_PRECIP, intensity=(.3, .7), cloud_cover=(.3, .7), fog=(0, .35)),
    'overcast': dict(_NO_PRECIP, intensity=(.7, 1), cloud_cover=(.7, 1), fog=(0, .4)),
    'fog': dict(_NO_PRECIP, fog=(.3, 1), humidity=(.7, 1), visibility=(0, .7), **{'wind.speed': (0, .35)}),
    'drizzle': {'temperature_c': (0, 60), 'precipitation.rate': (.01, .4), 'cloud_cover': (.6, 1),
                'humidity': (.6, 1), 'lightning': (0, 0)},
    'rain': {'temperature_c': (0, 60), 'precipitation.rate': (.05, 1), 'cloud_cover': (.6, 1),
             'humidity': (.6, 1), 'lightning': (0, 0)},
    'storm': {'temperature_c': (2, 60), 'precipitation.rate': (.05, 1), 'cloud_cover': (.7, 1),
              'humidity': (.6, 1), 'lightning': (.05, 1), 'wind.speed': (.4, 1)},
    'snow': {'temperature_c': (-80, 1), 'precipitation.rate': (.02, 1), 'cloud_cover': (.6, 1), 'lightning': (0, 0)},
    'blizzard': {'temperature_c': (-80, 1), 'precipitation.rate': (.3, 1), 'cloud_cover': (.7, 1),
                 'lightning': (0, 0), 'wind.speed': (.5, 1), 'visibility': (0, .4)},
    'sleet': {'temperature_c': (-3, 4), 'precipitation.rate': (.02, 1), 'cloud_cover': (.6, 1), 'lightning': (0, 0)},
    'sandstorm': dict(_NO_PRECIP, fog=(0, .2), humidity=(0, .5), visibility=(0, .5), **{'wind.speed': (.45, 1)}),
    'hail': {'temperature_c': (-5, 45), 'precipitation.rate': (.05, 1), 'cloud_cover': (.7, 1),
             'humidity': (.6, 1), 'wind.speed': (.3, 1), 'lightning': (0, 0)},
    'aurora': dict(_NO_PRECIP, intensity=(.2, 1), cloud_cover=(0, .5), fog=(0, .3), **{'aurora.strength': (0, 1)}),
    'mana_storm': dict(_NO_PRECIP, cloud_cover=(.6, 1), **{'wind.speed': (.3, 1), 'magic.strength': (.1, 1)}),
    'spirit_mist': dict(_NO_PRECIP, fog=(.3, 1), visibility=(0, .7), **{'wind.speed': (0, .4),
                                                                        'magic.strength': (.05, 1)}),
    'miasma': dict(_NO_PRECIP, fog=(.3, 1), humidity=(.6, 1), visibility=(0, .6), **{'wind.speed': (0, .35)}),
    'ashfall': dict(_NO_PRECIP, cloud_cover=(.6, 1), visibility=(0, .8)),
    'freezing_rain': {'temperature_c': (-4, 0), 'precipitation.rate': (.02, 1), 'cloud_cover': (.6, 1), 'lightning': (0, 0)},
    'graupel': {'temperature_c': (-2, 3), 'precipitation.rate': (.02, 1), 'cloud_cover': (.6, 1), 'lightning': (0, 0)},
    'frost': dict(_NO_PRECIP, temperature_c=(-80, 0), cloud_cover=(0, .3), **{'wind.speed': (0, .25)}),
    'rime': dict(_NO_PRECIP, temperature_c=(-80, -2), fog=(.3, 1), humidity=(.8, 1), **{'wind.speed': (0, .4)}),
    'haze': dict(_NO_PRECIP, **{'wind.speed': (0, .3)}),
    'dust': dict(_NO_PRECIP, humidity=(0, .5), **{'wind.speed': (.1, .6)}),
    'blowing_sand': dict(_NO_PRECIP, humidity=(0, .4), **{'wind.speed': (.35, .8)}),
    'typhoon': {'temperature_c': (15, 45), 'precipitation.rate': (.01, 1), 'wind.speed': (.7, 1), 'lightning': (0, 0)},
    'tornado': {'temperature_c': (2, 45), 'precipitation.rate': (.05, 1), 'cloud_cover': (.7, 1),
                'wind.speed': (.7, 1), 'lightning': (0, 0)},
    'heatwave': dict(_NO_PRECIP, temperature_c=(25, 60), cloud_cover=(0, .35)),
    'sunshower': {'temperature_c': (2, 45), 'precipitation.rate': (.01, .5), 'cloud_cover': (.05, .49), 'lightning': (0, 0)},
}
for _k, _r in KIND_RANGE.items():
    if _k not in AURORA_KINDS:
        _r.setdefault('aurora.strength', (0, 0))
    if _k not in FANTASY:
        _r.setdefault('magic.strength', (0, 0))
del _k, _r
for _k, _r in KIND_RANGE.items():
    _r.setdefault('vortex', (0, 1) if _k == 'tornado' else (0, 0))
    _r.setdefault('heat', (0, 1) if _k in HEAT_KINDS else (0, 0))
    _r.setdefault('rainbow', (0, 1) if _k in RAINBOW_KINDS else (0, 0))
del _k, _r
# cloud_cover = a + b * intensity; fog = a + b * intensity; wind floor = a + b * intensity.
CLOUD_OF = {'drizzle': (.7, .25), 'rain': (.8, .2), 'storm': (.85, .15), 'snow': (.75, .25),
            'blizzard': (.9, .1), 'sleet': (.8, .2), 'hail': (.85, .15), 'mana_storm': (.7, .3),
            'ashfall': (.75, .25)}
FOG_OF = {'fog': (.4, .6), 'drizzle': (.15, .2), 'rain': (.08, .1), 'storm': (.1, 0), 'snow': (.1, .25),
          'blizzard': (.35, .4), 'sleet': (.15, 0), 'hail': (.05, 0), 'spirit_mist': (.35, .6),
          'miasma': (.3, .65), 'ashfall': (.15, .25), 'mana_storm': (.1, .1)}
WIND_FLOOR = {'storm': (.45, .5), 'blizzard': (.45, .5), 'sandstorm': (.45, .5), 'hail': (.35, .4),
              'mana_storm': (.35, .5)}
RATE = {'drizzle': .3, 'rain': 1.0, 'storm': 1.0, 'snow': .8, 'blizzard': 1.0, 'sleet': .7, 'hail': .8}
VCOST = {'drizzle': .25, 'rain': .3, 'storm': .4, 'snow': .5, 'blizzard': .4, 'sleet': .35, 'hail': .35}
CLOUD_OF.update(freezing_rain=(.75, .25), graupel=(.7, .25), frost=(.05, .1), rime=(.45, .3),
                haze=(.3, .2), dust=(.2, .15), blowing_sand=(.2, .2), typhoon=(.8, .2),
                tornado=(.85, .15), heatwave=(.05, .15), sunshower=(.1, .3))
FOG_OF.update(rime=(.35, .5))
WIND_FLOOR.update(typhoon=(.7, .3), tornado=(.7, .3), blowing_sand=(.35, .35))
RATE.update(freezing_rain=.65, graupel=.7, typhoon=1., tornado=1., sunshower=.4)
VCOST.update(freezing_rain=.35, graupel=.4, typhoon=.65, tornado=.6, sunshower=.2)
# Fantasy kinds: share of hours (when allowed), magic strength a + b * i, hue (base, spread), pulse a + b * i.
FANTASY_SHARE = {'mana_storm': .06, 'spirit_mist': .08, 'miasma': .08, 'ashfall': .05}
MAGIC_OF = {'mana_storm': (.2, .8), 'spirit_mist': (.15, .6), 'miasma': (0, .3), 'ashfall': (0, .4)}
MAGIC_HUE = {'mana_storm': (.72, .25), 'spirit_mist': (.3, .35), 'miasma': (.22, .06), 'ashfall': (.05, .05)}
MAGIC_PULSE = {'mana_storm': (.4, .6), 'spirit_mist': (.15, .25), 'miasma': (.05, .1), 'ashfall': (.2, .5)}
TWILIGHT_H = 1.5
# Hours of signal shift per degree of longitude. Constant (cos 45 deg) on purpose: a latitude-dependent
# speed or direction would make the shift -lon * f(lat) shear by many hours per degree of latitude
# far from lon 0 and break the spatial continuity of fronts.
DRIFT_H_PER_DEG = 111.32 * 0.7 / FRONT_KMH
OFFSET_H = 12.0  # amplitude of the slow spatial time offset (hours)
SPATIAL_DEG = 20.0  # cell size of that offset noise (degrees)
MAX_CONTEXTS = 128
MAX_MEMO = 2048
_CONTEXTS = OrderedDict()
_CONTEXT_LOCK = threading.RLock()
_NATURAL_EVALUATIONS = 0


def _memo_put(cache, key, value, limit=MAX_MEMO):
    cache[key] = value
    if len(cache) > limit:
        cache.pop(next(iter(cache)))
    return value


def clear_cache():
    """Drop the bounded in-memory memo; weather values are independent of the cache."""
    global _NATURAL_EVALUATIONS
    with _CONTEXT_LOCK:
        _CONTEXTS.clear()
        _NATURAL_EVALUATIONS = 0


def cache_info():
    with _CONTEXT_LOCK:
        return {'contexts': len(_CONTEXTS), 'max_contexts': MAX_CONTEXTS,
                'max_entries_per_context': MAX_MEMO, 'natural_evaluations': _NATURAL_EVALUATIONS}


def _flow_direction(c):
    if c.lat is None:
        return CLIMATES[c.climate]['dir']
    # Smooth trade-wind / westerly / polar belts, shared by all nearby climate cells.
    a = abs(c.lat)
    west = _smooth(_clamp01((a - 25) / 10)) * (1 - _smooth(_clamp01((a - 55) / 10)))
    return 270 - 180 * west


def _vn3(key, x, y, z):
    """Longitude-periodic value noise. Eighteen 20-degree columns wrap the globe."""
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = _smooth(x - ix), _smooth(y - iy), _smooth(z - iz)

    def plane(kz):
        k = (key + kz * 0x27D4EB2D) & M32
        a, b = _lattice2(k, ix % 18, iy), _lattice2(k, (ix + 1) % 18, iy)
        d, e = _lattice2(k, ix % 18, iy + 1), _lattice2(k, (ix + 1) % 18, iy + 1)
        return a + (b - a) * fx + ((d + (e - d) * fx) - (a + (b - a) * fx)) * fy

    a, b = plane(iz), plane(iz + 1)
    return a + (b - a) * fz


def _signal(c, ch, t, p1, p2):
    if c.lat is None or c.lon is None:
        return _u(c.seed, ch, t, p1, p2)
    direction = math.radians(_flow_direction(c))
    east = math.sin(direction) * FRONT_KMH / (111.32 * max(.2, math.cos(math.radians(c.lat))))
    north = math.cos(direction) * FRONT_KMH / 111.32
    x, y = (c.lon - east * t) / 20, (c.lat - north * t) / 20
    return _cdf(.65 * _vn3(_key(c.seed, ch), x, y, t / (4 * p1))
                + .35 * _vn3(_key(c.seed, ch + 50), x, y, t / (4 * p2)))


def _extra_params(c, t):
    # Same season interpolation as the base climate table.
    table = EXTRA[c.climate]
    if c.season is not None:
        return table[c.season]
    x = _mod(c.start - 1 + t / 24 + (182.5 if c.south else 0), 365)
    if x < 15:
        x += 365
    for start, length, a, b in _SEGMENTS:
        if x < start + length:
            f = _smooth((x - start) / length)
            return tuple(v + (w - v) * f for v, w in zip(table[a], table[b]))
    return table['winter']


def _fit(kind, name, v):
    r = KIND_RANGE[kind].get(name, (-80, 60) if name == 'temperature_c' else None)
    return _clamp(v, r[0], r[1]) if r else v


class _Ctx:
    """Per-call constants: seed, climate, season, place, calendar, allowed fantasy kinds, memo."""

    def __init__(self, seed, climate, season, lat, lon, calendar, fantasy=(), elevation=None, coast_distance_km=None):
        self.seed = seed
        self.climate = climate
        self.season = season
        self.lat = lat
        self.lon = lon
        self.calendar = calendar
        self.fantasy = fantasy
        self.coast_distance_km = coast_distance_km
        self.lock = threading.RLock()
        self.south = lat is not None and lat < 0
        self.start = Calendar.model_validate(calendar).start_day_of_year if calendar is not None else 1
        self.lapse = 0.0 if elevation is None else (elevation - CLIMATES[climate]['elev']) * LAPSE_C_PER_M
        self.shift = 0.0
        if lat is not None and lon is not None:
            angle = math.radians(lon)
            off = _vn2(_key(seed, 30), math.cos(angle) * 3, math.sin(angle) * 3 + lat / SPATIAL_DEG)
            self.shift = OFFSET_H * (2 * off - 1)
        # aurora needs a high latitude when the place is known (fades in from 50 to 65 degrees)
        self.aurora_lat = 1.0 if lat is None else _clamp01((abs(lat) - 50) / 15)
        self.cache = {}
        self.suns = {}
        self.gcache = {}


def _clock(c):
    h, m = c['time'].split(':')
    return int(h) + int(m) / 60 + 24 * c['day_offset']


def _sun(c, day):
    """(sunrise, sunset) hours of game `day`; sunset may pass 24. Polar day (0, 24), night (12, 12)."""
    hit = c.suns.get(day)
    if hit is not None:
        return hit
    rs = (6.0, 18.0)
    if c.calendar is not None and c.lat is not None and c.lon is not None:
        sun = solar(c.lat, c.lon, day, c.calendar)
        if sun is not None:
            if sun['polar'] == 'polar_day':
                rs = (0.0, 24.0)
            elif sun['polar'] == 'polar_night':
                rs = (12.0, 12.0)
            else:
                rise, sett = _clock(sun['sunrise']), _clock(sun['sunset'])
                r0 = _mod(rise, 24.0)
                rs = (r0, r0 + (sett - rise))
    _memo_put(c.suns, day, rs, 128)
    return rs


def _dark(c, t):
    """0 in daylight, rising to 1 within TWILIGHT_H hours after sunset / before sunrise."""
    day = math.floor(t / 24) + 1
    h = t - (day - 1) * 24
    rise, sett = _sun(c, day)
    if sett - rise >= 24:
        return 0.0
    if sett <= rise:
        return 1.0
    dist = 24.0
    for x in (h - 24, h, h + 24):
        if rise <= x <= sett:
            return 0.0
        dist = min(dist, abs(x - rise), abs(x - sett))
    return _clamp01(dist / TWILIGHT_H)


def _time(c, day, hour):
    rise, sett = _sun(c, day)
    return {'hour': float(hour), 'day_of_year': (c.start + day - 2) % 365 + 1, 'sunrise': rise,
            'sunset': sett, 'moon_phase': _mod((day - 1 + hour / 24) / MOON_PERIOD_DAYS, 1.0)}


def _cyclone(c, t, tendency):
    empty = {'category': 0, 'phase': 'none'}
    if tendency <= 0 or c.coast_distance_km is None or c.coast_distance_km > 200:
        return empty
    slot = math.floor(t / CYC_SLOT_H)
    k = _key(c.seed, 70)
    if _lattice(k, slot) >= tendency:
        return empty
    duration = 48 + 24 * _lattice(k, slot + 100000)
    start = slot * CYC_SLOT_H + (CYC_SLOT_H - duration) * _lattice(k, slot + 200000)
    progress = (t - start) / duration
    if not 0 <= progress <= 1:
        return empty
    lateral = 0 if c.lon is None or c.lat is None else .7 * (2 * _signal(c, 71, t, 160, 80) - 1)
    radius = math.hypot(2 * progress - 1, lateral)
    phase = 'eye' if radius < .16 else ('eyewall' if radius < .6 else 'outer')
    return {'category': 1 + int(5 * _lattice(k, slot + 300000)), 'phase': phase}


def _natural(c, t):
    """Weather at absolute hour t without overrides (memoised per context)."""
    hit = c.cache.get(t)
    if hit is not None:
        return hit
    global _NATURAL_EVALUATIONS
    _NATURAL_EVALUATIONS += 1
    hour = _mod(t, 24)
    ts = t + c.shift
    p, label = _params(c.climate, c.season, _mod(c.start - 1 + t / 24, 365), c.south)
    tlo, thi, wet, cloud, storm, fogt, wind, dust, snowb, aur = p
    uf = _signal(c, 0, t, 40, 13)
    uc = _signal(c, 1, t, 30, 7)
    ucl = _signal(c, 2, t, 30, 9)
    ua = _signal(c, 3, t, 96, 30)
    ufg = _signal(c, 4, t, 30, 12)
    uw = _signal(c, 5, t, 24, 6)
    ud = _signal(c, 6, t, 36, 10)
    uh = _signal(c, 10, t, 20, 6)
    aft = 0.5 + 0.5 * math.cos(TAU * (hour - 16) / 24)
    night = 0.5 + 0.5 * math.cos(TAU * (hour - 5) / 24)
    sshare = storm * 0.5 * (0.3 + 0.7 * aft)
    lp = _lv(uf, wet)
    ls = _lv(uc, sshare)
    ld = _lv(ud, dust * 0.5)
    lf = _lv(ufg, fogt * (0.3 + 0.7 * night))
    near = max(_ramp(uf, wet), _ramp(uc, sshare))
    cl = _clamp01(cloud + (ucl - 0.5) * 0.7)
    cl += (max(cl, 0.85) - cl) * near
    ip = max(lp, ls)
    temp = ((tlo + thi) / 2 + (thi - tlo) / 2 * math.cos(TAU * (hour - 15) / 24) * (1 - 0.5 * cl)
            + (ua - 0.5) * 8 - 2 * ip - 1.5 * min(1.0, 8 * ip) - c.lapse)  # rain-cooled air while it falls
    ws = _clamp01(wind * 0.8 + (uw - 0.5) * 0.5 + 0.3 * lp + 0.35 * ls + 0.5 * ld)
    hail = ls > 0.3 and uh > 0.65
    dark = _dark(c, t)
    ar = _lv(_signal(c, 11, t, 30, 8), aur * 0.7, 0.3) * dark * c.aurora_lat
    fl, fk = 0.0, None
    for j, f in enumerate(FANTASY):
        if f in c.fantasy:
            lvl = _lv(_signal(c, 20 + j, t, 36, 11), FANTASY_SHARE[f])
            if lvl > fl:
                fl, fk = lvl, f
    if fk is not None and fl > 0.1:
        kind, intensity = fk, fl
    elif ip > 0:
        intensity = ip
        if temp < 0:
            kind = 'blizzard' if ip > 0.55 and ws > 0.55 else 'snow'
        elif temp < 2:
            kind = 'sleet'
        elif ls > 0.12 and ls >= 0.8 * lp:
            kind = 'hail' if hail and uh > 0.8 else 'storm'
        elif ip < 0.15:
            kind = 'drizzle'
        else:
            kind = 'rain'
    elif ld > 0.1:
        kind, intensity = 'sandstorm', ld
    elif lf > 0.15 and ws < 0.35:
        kind, intensity = 'fog', lf
    elif ar > 0.45 and cl < 0.5:
        kind, intensity = 'aurora', ar
    else:
        kind = 'clear' if cl < 0.3 else ('cloudy' if cl < 0.7 else 'overcast')
        intensity = cl
    frz, grp, haze, fdust, blow, typh, torn, heat, sunsh, rime = _extra_params(c, t)
    ux = _signal(c, 40, t, 36, 12)
    heat_level = _lv(_signal(c, 41, t, 160, 72), heat)
    temp += 10 * heat_level
    cyclone = _cyclone(c, t, typh)
    if fk is None or fl <= .1:
        if cyclone['phase'] != 'none':
            kind, intensity = 'typhoon', .45 + .1 * cyclone['category']
        elif ip > 0:
            if -4 <= temp <= 0 and ux > 1 - frz:
                kind = 'freezing_rain'
            elif -2 <= temp <= 3 and ux < grp:
                kind = 'graupel'
            elif kind == 'storm' and ls > .3 and _signal(c, 42, t, 2, .5) > 1 - torn:
                kind = 'tornado'
        elif ld <= .1 and lf <= .15:
            if temp < -2 and dark > 0 and rime > 0 and ufg > .7:
                kind, intensity = 'rime', .3 + .6 * ufg
            elif temp <= 0 and dark > 0 and ws < .25 and cl < .3:
                kind, intensity = 'frost', .2 + .6 * dark
            elif _lv(ux, blow) > .05 and ws > .35:
                kind, intensity = 'blowing_sand', _lv(ux, blow)
            elif _lv(ud, fdust) > .05:
                kind, intensity = 'dust', _lv(ud, fdust)
            elif _lv(ux, haze) > .05 and ws < .3:
                kind, intensity = 'haze', _lv(ux, haze)
            elif heat_level > .1 and temp >= 25:
                kind, intensity = 'heatwave', heat_level
            elif _lv(ux, sunsh) > .05 and temp > 2 and cl < .5:
                kind, intensity = 'sunshower', _lv(ux, sunsh)
    n = {'kind': kind, 'intensity': intensity, 'temp': temp, 'ws': ws, 'cl': cl, 'lf': lf, 'night': night,
         'p': p, 'season': label, 'hail': hail, 'ar': ar, 'dark': dark, 'ts': ts, 't': t, 'cyclone': cyclone}
    return _memo_put(c.cache, t, n)


def _ptype(kind, n, ov):
    if 'precipitation.type' in ov:
        return ov['precipitation.type']
    if kind == 'storm' and n['hail']:
        return 'hail'
    return PTYPE.get(kind, 'none')


def _core(kind, intensity, n):
    """The shared 12-field input for natural ground integration."""
    return _ground_input(kind, intensity, n)


def _conflict(kind, ov):
    """Why the overridden fields do not fit `kind` (None when they fit)."""
    if 'precipitation.type' in ov and 'precipitation.rate' in ov:
        if (ov['precipitation.type'] == 'none') != (ov['precipitation.rate'] == 0):
            return 'precipitation.type 为 none 当且仅当 rate 为 0'
    allowed = ('none', 'rain') if kind == 'typhoon' and ov.get('cyclone.phase') == 'eye' else PTYPES_OF.get(kind, (PTYPE.get(kind, 'none'),))
    if 'precipitation.type' in ov and ov['precipitation.type'] not in allowed:
        return f"kind={kind} 的降水类型应为 {'/'.join(allowed)}，覆盖值为 {ov['precipitation.type']}"
    for f, (lo, hi) in KIND_RANGE[kind].items():
        if kind == 'typhoon' and ov.get('cyclone.phase') == 'eye' and f in ('wind.speed', 'precipitation.rate'):
            lo, hi = 0, .3
        if f in ov and not lo <= ov[f] <= hi:
            return f'kind={kind} 要求 {f} 在 [{lo}, {hi}]，覆盖值为 {ov[f]}'
    if any(k.startswith('cyclone.') for k in ov) and kind != 'typhoon':
        return 'cyclone 只能用于 typhoon'
    atype = AEROSOL_OF.get(kind, ('none', 0, 0))[0]
    if 'aerosol.type' in ov and ov['aerosol.type'] != atype:
        return f'kind={kind} 的 aerosol.type 应为 {atype}'
    if atype == 'none' and ov.get('aerosol.density', 0) > 0:
        return f'kind={kind} 不支持 aerosol.density'
    return None


def _choose_kind(c, n, ov):
    """Forced kind (checked), else the natural kind or the closest allowed kind the overrides permit."""
    if 'kind' in ov:
        why = _conflict(ov['kind'], ov)
        if why:
            raise ValueError('覆盖字段互相矛盾：' + why)
        return ov['kind']
    first = None
    for k in (n['kind'],) + RELATED[n['kind']] + KINDS:
        if k in FANTASY and k not in c.fantasy:
            continue
        why = _conflict(k, ov)
        if why is None:
            return k
        first = first or why
    raise ValueError('覆盖字段没有任何天气类型能同时满足：' + first)


def _intensity(c, t, kind, n, ov):
    if 'intensity' in ov:
        return ov['intensity']
    if kind in RATE and 'precipitation.rate' in ov:
        i = ov['precipitation.rate'] / RATE[kind]
    elif kind in CLOUD_BAND and 'cloud_cover' in ov:
        i = ov['cloud_cover']
    elif kind == n['kind']:
        i = n['intensity']
    else:
        lo, hi = DEFAULT_INTENSITY[kind]
        i = lo + (hi - lo) * _u(c.seed, 8, n['ts'], 30, 10)
    return _fit(kind, 'intensity', _clamp01(i))


def _wind_dir(c, ts):
    base = _flow_direction(c)
    if c.south and c.lat is None:
        base = 180 - base
    return _mod(base + (_u(c.seed, 7, ts, 48, 12) - 0.5) * 140, 360.0)


def _derive(c, kind, i, n, ov):
    """All non-ground fields of `kind` at intensity `i`; overridden fields are kept as given."""

    def pick(name, v):
        return ov[name] if name in ov else _fit(kind, name, _clamp01(v))

    ts = n['ts']
    ptype = _ptype(kind, n, ov)
    rate = pick('precipitation.rate', RATE[kind] * i) if kind in RATE else 0.0
    temp = ov['temperature_c'] if 'temperature_c' in ov else _fit(kind, 'temperature_c', n['temp'])
    if kind in CLOUD_BAND:
        cl = i
    elif kind in CLOUD_OF:
        cl = CLOUD_OF[kind][0] + CLOUD_OF[kind][1] * i
    elif kind == 'sandstorm':
        cl = n['cl'] * 0.5
    elif kind == 'aurora':
        cl = n['cl']
    else:
        cl = max(n['cl'], 0.5)
    cl = pick('cloud_cover', cl)
    if kind in FOG_OF:
        fg = FOG_OF[kind][0] + FOG_OF[kind][1] * i
    elif kind == 'sandstorm':
        fg = 0.05
    else:
        fg = 0.3 * n['lf']
    fg = pick('fog', fg)
    windy = kind in WIND_FLOOR
    ws = n['ws']
    if windy:
        ws = max(ws, WIND_FLOOR[kind][0] + WIND_FLOOR[kind][1] * i)
    ws = pick('wind.speed', ws)
    gust = pick('wind.gust', ws * (0.25 + 0.5 * _u(c.seed, 9, ts, 6, 2)) + (0.3 * i if windy else 0.0))
    wdir = ov['wind.dir_deg'] if 'wind.dir_deg' in ov else _wind_dir(c, ts)
    # a thunderstorm with hail is kind=storm + precipitation.type=hail; kind=hail is a hail shower
    light = 0.1 + 0.9 * i if kind == 'storm' else 0.0
    light = pick('lightning', light)
    if kind in RATE:
        hum = 0.85 + 0.15 * i
    elif kind in ('fog', 'spirit_mist', 'miasma'):
        hum = 0.9 + 0.1 * i
    elif kind == 'sandstorm':
        hum = 0.15
    elif kind == 'ashfall':
        hum = 0.25 + 0.2 * cl
    else:
        hum = 0.3 + 0.35 * cl + 0.2 * n['night'] + 0.3 * n['p'][2]
    hum = pick('humidity', hum)
    if kind in RATE:
        vis = 1 - VCOST[kind] * i - 0.7 * fg
    elif kind in ('fog', 'spirit_mist', 'miasma'):
        vis = 1 - fg
    elif kind == 'sandstorm':
        vis = 0.45 - 0.4 * i
    elif kind == 'ashfall':
        vis = 0.85 - 0.5 * i - 0.3 * fg
    else:
        vis = 1 - 0.7 * fg - 0.05 * cl
    vis = pick('visibility', vis)
    # aurora: night-time activity (or the forced intensity), dimmed by the cloud in front of it
    a_base = i if kind == 'aurora' else n['ar']
    a_str = pick('aurora.strength', a_base * (1 - cl))
    a_hue = pick('aurora.hue', a_str * (0.15 + 0.6 * _u(c.seed, 12, ts, 10, 3)))
    if kind in FANTASY:
        m_str = MAGIC_OF[kind][0] + MAGIC_OF[kind][1] * i
        m_hue = MAGIC_HUE[kind][0] + MAGIC_HUE[kind][1] * (_u(c.seed, 13, ts, 12, 4) - 0.5)
        m_pulse = MAGIC_PULSE[kind][0] + MAGIC_PULSE[kind][1] * i
    else:
        m_str = m_hue = m_pulse = 0.0
    atype, abase, ascale = AEROSOL_OF.get(kind, ('none', 0, 0))
    density = ov.get('aerosol.density', abase + ascale * i)
    if atype != 'none':
        vis = ov.get('visibility', min(vis, 1 - .9 * density))
    phase, category = 'none', 0
    if kind == 'typhoon':
        category = ov.get('cyclone.category', n['cyclone']['category'] or 2)
        phase = ov.get('cyclone.phase', n['cyclone']['phase'])
        if phase == 'none':
            phase = 'outer' if i < .4 else 'eyewall'
        if phase == 'eye':
            ws = ov.get('wind.speed', .12)
            gust = ov.get('wind.gust', .08)
            cl = ov.get('cloud_cover', .2)
            rate = ov.get('precipitation.rate', .1 if ov.get('precipitation.type') == 'rain' else 0.0)
            ptype = 'rain' if rate > 0 else 'none'
    heat = pick('heat', i if kind == 'heatwave' else _clamp01((temp - 30) / 15))
    recent_rain = False
    if kind in RAINBOW_KINDS:
        recent_rain = kind == 'sunshower' or any(_natural(c, n['t'] - h)['kind'] in LIQUID_KINDS for h in (1, 2))
    tm = _time(c, math.floor(n['t'] / 24) + 1, _mod(n['t'], 24))
    low_sun = min(abs(tm['hour'] - tm['sunrise']), abs(tm['hour'] - _mod(tm['sunset'], 24))) < 3
    rainbow = pick('rainbow', .7 * (1 - cl) if recent_rain and low_sun and n['dark'] == 0 else 0)
    return {'precipitation': {'type': ptype, 'rate': rate}, 'cloud_cover': cl, 'fog': fg,
            'wind': {'dir_deg': wdir, 'speed': ws, 'gust': gust}, 'lightning': light,
            'temperature_c': temp, 'humidity': hum, 'visibility': vis,
            'aurora': {'strength': a_str, 'hue': a_hue},
            'magic': {'strength': pick('magic.strength', m_str), 'hue': pick('magic.hue', m_hue),
                      'pulse': pick('magic.pulse', m_pulse)},
            'aerosol': {'type': atype, 'density': density}, 'heat': heat, 'rainbow': rainbow,
            'cyclone': {'category': category, 'phase': phase}, 'vortex': pick('vortex', i)}


# ---------------------------------------------------------------- ground (accumulated)
# Fields whose override means "this weather has lasted the whole window" for the ground.
GROUND_KEYS = ('kind', 'intensity', 'precipitation.type', 'precipitation.rate', 'temperature_c',
               'wind.speed', 'fog', 'humidity', 'cloud_cover', 'aerosol.density', 'cyclone.phase')


def _ground_input(kind, intensity, n, fields=None):
    """A shared physical input for both historical and current ground integration."""
    if fields is None:
        ptype = _ptype(kind, n, {})
        rate = _fit(kind, 'precipitation.rate', RATE[kind] * intensity) if kind in RATE else 0.0
        temp = _fit(kind, 'temperature_c', n['temp'])
        ws = _fit(kind, 'wind.speed', max(n['ws'], sum((WIND_FLOOR.get(kind, (0, 0))[0],
                                                     WIND_FLOOR.get(kind, (0, 0))[1] * intensity))))
        cl = _fit(kind, 'cloud_cover', sum((CLOUD_OF.get(kind, (n['cl'], 0))[0],
                                          CLOUD_OF.get(kind, (0, 0))[1] * intensity)))
        fog = _fit(kind, 'fog', FOG_OF.get(kind, (0, 0))[0] + FOG_OF.get(kind, (0, 0))[1] * intensity)
        humidity = .95 if kind in FOGGY else (.9 if kind in RATE else .5)
        if kind == 'typhoon' and n['cyclone']['phase'] == 'eye':
            ptype, rate, ws, cl = 'none', 0., .12, .2
    else:
        ptype, rate = fields['precipitation']['type'], fields['precipitation']['rate']
        temp, ws, cl = fields['temperature_c'], fields['wind']['speed'], fields['cloud_cover']
        humidity, fog = fields['humidity'], fields['fog']
    dust = AEROSOL_OF.get(kind, ('none', 0, 0))
    dust_in = dust[1] + dust[2] * intensity if kind in DUST_KINDS else 0.
    if fields is not None and kind in DUST_KINDS:
        dust_in = fields['aerosol']['density']
    return (ptype, rate, temp, ws, cl, n['p'][8], intensity if kind == 'ashfall' else 0.,
            intensity if kind == 'mana_storm' else 0., n['dark'], humidity, fog, dust_in)


def _step(g, v):
    """One hour for 11 covers; legacy shorter ground/input tuples are zero-padded."""
    wet, pud, snow, hail, ash, mana, glaze, frost, rime, dust, graupel = tuple(g) + (0.,) * (len(GROUND_NAMES) - len(g))
    ptype, rate, temp, ws, cl, snowb, ash_in, mana_in, dark, humidity, fog, dust_in = tuple(v) + (0.,) * (12 - len(v))
    wetting = ptype in WET_TYPES
    if wetting:
        wet = min(1.0, wet + 0.08 + 0.5 * rate)
        pud = min(1.0, pud + 0.15 * rate)
    else:
        dry = (0.03 + 0.05 * _clamp01(temp / 30) + 0.04 * ws) * (1 - 0.4 * cl)
        if temp < 0:
            dry *= 0.3
        pud = max(0.0, pud - 0.6 * dry)
        wet = max(0.0, wet - dry)
    if ptype == 'snow' and temp <= 1:
        snow += 0.06 * rate + 0.01
    elif ptype == 'sleet' and temp < 1:
        snow += 0.015 * rate
    if snow > snowb or temp <= 0:  # settles down to the baseline; builds up to it only when freezing
        snow += SNOW_RELAX * (snowb - snow)
    if temp > 0 and snow > 0:
        m = min(snow, 0.006 * temp + (0.02 * rate if wetting else 0.0))
        snow -= m
        wet = min(1.0, wet + 0.4 * m)  # meltwater soaks in; less than the hourly drying
    snow = _clamp01(snow)
    if ptype == 'hail':
        hail = min(1.0, hail + 0.25 * rate)
    else:
        hail = max(0.0, hail - (0.02 + 0.004 * max(temp, 0.0)))  # ice lies a few hours, faster when warm
    if ash_in > 0:
        ash = min(1.0, ash + 0.06 * ash_in)
    else:
        ash = max(0.0, ash - 0.006 * ash - (0.02 * rate if wetting else 0.0))
    if mana_in > 0:
        mana = min(1.0, mana + 0.08 * mana_in)
    else:
        mana = mana * (1 - 0.012)
    thaw = .02 + .012 * max(temp, 0)
    if ptype == 'freezing_rain' and temp <= 0:
        glaze = min(1., glaze + .12 * rate)
    elif temp > 0:
        melt = min(glaze, thaw)
        glaze -= melt
        wet = min(1., wet + .4 * melt)
    else:
        glaze = max(0., glaze - .003)
    if ptype == 'graupel':
        graupel = min(1., graupel + .15 * rate)
    else:
        graupel = max(0., graupel - thaw)
    if temp <= 0 and dark > .3 and cl <= .3 and ws <= .25 and not wetting:
        frost = min(1., frost + .08 * dark)
    else:
        frost = max(0., frost - (.4 * (1 - dark) + thaw + .1 * rate))
    if temp <= -2 and fog >= .3 and humidity >= .8:
        rime = min(1., rime + .1 * fog)
    else:
        rime = max(0., rime - thaw - .05 * (1 - dark))
    if dust_in > 0:
        dust = min(1., dust + .05 * dust_in)
    else:
        dust = max(0., dust * .94 - (.3 * rate if wetting else .003))
    return (max(wet, pud), pud, snow, hail, ash, mana, glaze, frost, rime, dust, graupel)


def _ground(c, t, cur, ov):
    """Ground values at hour t: natural hours from the anchor up to t, then the current hour `cur`.

    `cur` is a _core-style tuple (a 6-tuple without the ash/mana inputs is accepted)."""
    cur = tuple(cur) + (0.0,) * (12 - len(cur))
    if any(k in ov for k in GROUND_KEYS):
        g = (0.0, 0.0, cur[5]) + (0.,) * (len(GROUND_NAMES) - 3)
        for _ in range(WINDOW_HOURS + 1):
            g = _step(g, cur)
        return g
    start = math.floor(t / 24) * 24 - WINDOW_HOURS
    end = math.ceil(t) - 1
    hit = c.gcache.get(start)
    if hit is not None and hit[0] <= end:
        h, g = hit
    else:
        h, g = start - 1, None
    while h < end:
        h += 1
        n = _natural(c, h)
        v = _core(n['kind'], n['intensity'], n)
        if g is None:
            g = (0.0, 0.0, v[5]) + (0.,) * (len(GROUND_NAMES) - 3)
        g = _step(g, v)
    _memo_put(c.gcache, start, (h, g), 32)
    return _step(g, cur)


# ---------------------------------------------------------------- argument checks
MAX_SEED = 2 ** 50  # seed + channel offsets stay below 2**53, exact in the JS mirror


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _num_in(name, v, lo, hi):
    if not _is_num(v):
        raise ValueError(f'覆盖字段 {name} 必须是有限数字')
    if not lo <= v <= hi:
        raise ValueError(f'覆盖字段 {name}={v} 超出范围 [{lo}, {hi}]')
    return v


def _flat_overrides(overrides):
    """Nested overrides -> {'kind': .., 'wind.speed': .., ...}, values checked."""
    if overrides is None:
        return {}
    if not isinstance(overrides, dict):
        raise ValueError('overrides 必须是字典')
    flat = {}
    for k, v in overrides.items():
        if k == 'kind':
            if v not in KINDS:
                raise ValueError(f'未知天气 kind={v!r}')
            flat['kind'] = v
        elif k in OVERRIDE_FIELDS:
            lo, hi = OVERRIDE_FIELDS[k]
            flat[k] = _num_in(k, v, lo, hi)
        elif k in OVERRIDE_NESTED:
            if not isinstance(v, dict):
                raise ValueError(f'覆盖字段 {k} 必须是字典')
            for sk, sv in v.items():
                if sk not in OVERRIDE_NESTED[k]:
                    raise ValueError(f'不支持覆盖字段 {k}.{sk}')
                rng = OVERRIDE_NESTED[k][sk]
                if isinstance(rng[0], str):
                    if not isinstance(sv, str) or sv not in rng:
                        raise ValueError(f'未知 {k}.{sk}={sv!r}，可选：' + ', '.join(rng))
                    flat[f'{k}.{sk}'] = sv
                else:
                    flat[f'{k}.{sk}'] = _num_in(f'{k}.{sk}', sv, rng[0], rng[1])
                    if k == 'cyclone' and sk == 'category' and not _is_int(sv):
                        raise ValueError('cyclone.category 必须是整数')
        else:
            raise ValueError(f'不支持覆盖字段 {k}')
    return flat


def _context(seed, climate, season, lat, lon, calendar, fantasy=(), elevation=None, coast_distance_km=None):
    if not _is_int(seed) or abs(seed) > MAX_SEED:
        raise ValueError(f'seed 必须是绝对值不超过 {MAX_SEED} 的整数')
    if not isinstance(climate, str) or climate not in CLIMATES:
        raise ValueError(f'未知气候 {climate!r}，可选：' + ', '.join(CLIMATES))
    if season is not None and season not in SEASONS:
        raise ValueError(f'未知季节 {season!r}，可选：' + ', '.join(SEASONS))
    if lat is not None and (not _is_num(lat) or abs(lat) > 90):
        raise ValueError('lat 必须是 [-90, 90] 内的数字')
    if lon is not None and (not _is_num(lon) or abs(lon) > 180):
        raise ValueError('lon 必须是 [-180, 180] 内的数字')
    if elevation is not None and (not _is_num(elevation) or not -500 <= elevation <= 9000):
        raise ValueError('elevation 必须是 [-500, 9000] 米内的数字')
    if coast_distance_km is not None and (not _is_num(coast_distance_km) or not 0 <= coast_distance_km <= 40075):
        raise ValueError('coast_distance_km 必须是 [0, 40075] 内的公里数')
    if isinstance(fantasy, str) or not isinstance(fantasy, (tuple, list, set, frozenset)):
        raise ValueError('fantasy 必须是奇幻天气名的列表')
    for f in fantasy:
        if f not in FANTASY:
            raise ValueError(f'未知奇幻天气 {f!r}，可选：' + ', '.join(FANTASY))
    allowed = tuple(f for f in FANTASY if f in fantasy)
    lon = -180.0 if lon == 180 else lon
    cal = Calendar.model_validate(calendar).model_dump() if calendar is not None else None
    identity = (seed, climate, season, lat, lon, json.dumps(cal, sort_keys=True), allowed, elevation, coast_distance_km)
    with _CONTEXT_LOCK:
        if identity in _CONTEXTS:
            _CONTEXTS.move_to_end(identity)
            return _CONTEXTS[identity]
        c = _Ctx(seed, climate, season, lat, lon, cal, allowed, elevation, coast_distance_km)
        _CONTEXTS[identity] = c
        if len(_CONTEXTS) > MAX_CONTEXTS:
            _CONTEXTS.popitem(last=False)
        return c


def _check_time(day, hour):
    if not _is_int(day) or abs(day) > 10 ** 6:
        raise ValueError('day 必须是绝对值不超过 1000000 的整数')
    if not _is_num(hour) or not 0 <= hour < 24:
        raise ValueError('hour 必须是 [0, 24) 内的数字')


_STATE_KEYS = ('seed', 'time', 'kind', 'intensity', 'precipitation', 'cloud_cover', 'fog', 'wind', 'lightning',
               'temperature_c', 'humidity', 'visibility', 'ground', 'aurora', 'magic', 'season', 'climate',
               'aerosol', 'rainbow', 'heat', 'cyclone', 'vortex')


def _state(c, day, hour, ov):
    t = (day - 1) * 24 + hour
    n = _natural(c, t)
    kind = _choose_kind(c, n, ov)
    i = _intensity(c, t, kind, n, ov)
    f = _derive(c, kind, i, n, ov)
    p = f['precipitation']
    cur = _ground_input(kind, i, n, f)
    g = _ground(c, t, cur, ov)
    ground = {name: ov.get('ground.' + name, g[k]) for k, name in enumerate(GROUND_NAMES)}
    return {'seed': c.seed, 'time': _time(c, day, hour), 'kind': kind, 'intensity': i, 'precipitation': p,
            'cloud_cover': f['cloud_cover'], 'fog': f['fog'], 'wind': f['wind'], 'lightning': f['lightning'],
            'temperature_c': f['temperature_c'], 'humidity': f['humidity'], 'visibility': f['visibility'],
            'ground': ground, 'aurora': f['aurora'], 'magic': f['magic'], 'season': c.season or n['season'],
            'climate': c.climate, 'aerosol': f['aerosol'], 'rainbow': f['rainbow'], 'heat': f['heat'],
            'cyclone': f['cyclone'], 'vortex': f['vortex']}


# ---------------------------------------------------------------- public API
def weather_at(seed, day, hour, climate, season=None, overrides=None, fantasy=(), lon=None, lat=None,
               elevation=None, calendar=None, coast_distance_km=None):
    """Weather state at game `day` (1-based, may be <= 0) and `hour` in [0, 24).

    fantasy: fantasy kinds allowed into the random pool (overrides.kind is never restricted).
    lon/lat: place (drives front timing and, with `calendar`, sunrise/sunset via geography.solar).
    elevation: metres, lapse 6.5 C/km relative to the climate table. calendar: geography.Calendar dict.
    coast_distance_km: explicit coast distance; None disables naturally generated typhoons.
    """
    c = _context(seed, climate, season, lat, lon, calendar, fantasy, elevation, coast_distance_km)
    _check_time(day, hour)
    ov = _flat_overrides(overrides)
    with c.lock:
        return _state(c, day, hour, ov)


def forecast(seed, start_day, start_hour, hours, climate, season=None, overrides=None, fantasy=(), lon=None,
             lat=None, elevation=None, calendar=None, step=1, coast_distance_km=None):
    """`hours` states every `step` hours from (start_day, start_hour); same values as weather_at."""
    c = _context(seed, climate, season, lat, lon, calendar, fantasy, elevation, coast_distance_km)
    _check_time(start_day, start_hour)
    if not _is_int(hours) or not 0 <= hours <= 1440:
        raise ValueError('hours 必须是 0..1440 的整数')
    if not _is_num(step) or not 0 < step <= 24:
        raise ValueError('step 必须在 (0, 24]')
    ov = _flat_overrides(overrides)
    out = []
    for k in range(hours):
        h = start_hour + k * step
        with c.lock:
            out.append(_state(c, start_day + math.floor(h / 24), _mod(h, 24), ov))
    return out


CELL_KEYS = ('id', 'lon', 'lat', 'climate', 'elevation', 'coast_distance_km')


def region_weather(seed, cells, day, hour, calendar=None, fantasy=(), season=None):
    """States of many map cells at one moment, in the order of `cells`.

    cells: [{id, lon, lat, climate, elevation?, coast_distance_km?}]. Neighbouring cells read shared
    moving signal fields (see the module docstring). The returned list preserves input order.
    """
    if not isinstance(cells, (list, tuple)):
        raise ValueError('cells 必须是列表')
    if len(cells) > 4096:
        raise ValueError('region_weather 每批最多 4096 格')
    _check_time(day, hour)
    _context(seed, 'temperate', season, None, None, calendar, fantasy)
    seen = set()
    out = []
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError('cells 的每一项必须是字典')
        extra = set(cell) - set(CELL_KEYS)
        if extra:
            raise ValueError('cell 不支持字段 ' + ', '.join(sorted(map(str, extra))))
        for k in ('id', 'lon', 'lat', 'climate'):
            if k not in cell:
                raise ValueError(f'cell 缺少字段 {k}')
        cid = cell['id']
        if isinstance(cid, bool) or not isinstance(cid, (str, int)) or cid in seen:
            raise ValueError(f'cell id {cid!r} 必须是唯一的字符串或整数')
        seen.add(cid)
        if cell['lon'] is None or cell['lat'] is None:
            raise ValueError('cell 的 lon / lat 不能为空')
        out.append(weather_at(seed, day, hour, cell['climate'], season=season, fantasy=fantasy, lon=cell['lon'],
                              lat=cell['lat'], elevation=cell.get('elevation'), calendar=calendar,
                              coast_distance_km=cell.get('coast_distance_km')))
    return out


def _climate_by_lat(lat, water):
    a = abs(lat)
    if a >= 66:
        return 'polar'
    if a >= 50:
        return 'maritime' if water else 'continental'
    if a >= 35:
        return 'maritime' if water else 'temperate'
    if a >= 23.5:
        return 'subtropical_monsoon'
    return 'tropical'


def climate_for(biome=None, lat=None):
    """Climate for a civ-atlas biome (name or index into BIOMES) and/or latitude.

    Water and wetland biomes, or no biome, are decided by latitude; nothing at all gives 'temperate'.
    """
    if _is_int(biome):
        if not 0 <= biome < len(BIOMES):
            raise ValueError(f'群系下标 {biome} 超出 0..{len(BIOMES) - 1}')
        biome = BIOMES[biome]
    if biome is not None and biome not in BIOME_CLIMATE:
        raise ValueError(f'未知群系 {biome!r}')
    if lat is not None and (not _is_num(lat) or abs(lat) > 90):
        raise ValueError('lat 必须是 [-90, 90] 内的数字')
    fixed = BIOME_CLIMATE.get(biome) if biome is not None else None
    if fixed:
        return fixed
    if lat is None:
        return 'temperate'
    return _climate_by_lat(lat, biome in ('海洋', '湖泊'))


_UNIT = ('intensity', 'cloud_cover', 'fog', 'lightning', 'humidity', 'visibility', 'heat', 'rainbow', 'vortex')


def validate_state(s):
    """Raise ValueError unless `s` follows the full state contract (spec sections 1, 5 and 8)."""

    def num(name, v, lo, hi):
        if not _is_num(v) or not lo <= v <= hi:
            raise ValueError(f'{name}={v!r} 不在 [{lo}, {hi}]')

    def keys(name, d, want):
        if not isinstance(d, dict) or set(d) != set(want):
            raise ValueError(f'{name} 字段应为 ' + ','.join(sorted(want)))

    keys('state', s, _STATE_KEYS)
    if not _is_int(s['seed']):
        raise ValueError('seed 必须是整数')
    tm = s['time']
    keys('time', tm, ('hour', 'day_of_year', 'sunrise', 'sunset', 'moon_phase'))
    num('time.hour', tm['hour'], 0, 24)
    num('time.sunrise', tm['sunrise'], 0, 24)
    num('time.sunset', tm['sunset'], 0, 48)
    num('time.moon_phase', tm['moon_phase'], 0, 1)
    if not _is_int(tm['day_of_year']) or not 1 <= tm['day_of_year'] <= 365:
        raise ValueError('time.day_of_year 必须是 1..365 的整数')
    if s['kind'] not in KINDS:
        raise ValueError(f"未知 kind {s['kind']!r}")
    if s['season'] not in SEASONS:
        raise ValueError(f"未知 season {s['season']!r}")
    if s['climate'] not in CLIMATES:
        raise ValueError(f"未知 climate {s['climate']!r}")
    for f in _UNIT:
        num(f, s[f], 0, 1)
    num('temperature_c', s['temperature_c'], -80, 60)
    p = s['precipitation']
    keys('precipitation', p, ('type', 'rate'))
    if p['type'] not in PRECIP_TYPES:
        raise ValueError(f"未知降水类型 {p['type']!r}")
    num('precipitation.rate', p['rate'], 0, 1)
    if (p['type'] == 'none') != (p['rate'] == 0):
        raise ValueError('precipitation.type 为 none 当且仅当 rate 为 0')
    keys('wind', s['wind'], ('dir_deg', 'speed', 'gust'))
    num('wind.dir_deg', s['wind']['dir_deg'], 0, 360)
    num('wind.speed', s['wind']['speed'], 0, 1)
    num('wind.gust', s['wind']['gust'], 0, 1)
    keys('ground', s['ground'], GROUND_NAMES)
    for g in GROUND_NAMES:
        num('ground.' + g, s['ground'][g], 0, 1)
    keys('aurora', s['aurora'], ('strength', 'hue'))
    keys('magic', s['magic'], ('strength', 'hue', 'pulse'))
    for name in ('aurora', 'magic'):
        for k, v in s[name].items():
            num(f'{name}.{k}', v, 0, 1)
    keys('aerosol', s['aerosol'], ('type', 'density'))
    if s['aerosol']['type'] not in AEROSOL_TYPES:
        raise ValueError('未知 aerosol.type')
    num('aerosol.density', s['aerosol']['density'], 0, 1)
    keys('cyclone', s['cyclone'], ('category', 'phase'))
    category, phase = s['cyclone']['category'], s['cyclone']['phase']
    if not _is_int(category) or phase not in CYCLONE_PHASES:
        raise ValueError('cyclone 类型或阶段不合法')
    if (phase == 'none' and category != 0) or (phase != 'none' and not 1 <= category <= 5):
        raise ValueError('cyclone 等级与阶段不一致')
    flat = _flat_overrides({k: v for k, v in s.items() if k in OVERRIDE_FIELDS or k in OVERRIDE_NESTED
                           if k != 'cyclone' or phase != 'none'})
    why = _conflict(s['kind'], flat)
    if why:
        raise ValueError(why)
    if s['kind'] == 'typhoon' and phase == 'none':
        raise ValueError('台风必须包含 cyclone 阶段')
    return s
