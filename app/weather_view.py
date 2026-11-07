# -*- coding: utf-8 -*-
"""Bridge between a journey's clock/place and the pure weather generator.

``app.weather`` knows nothing about journeys or story packages. This module is the one
place that turns ``session['time']``, the current location's coordinates/environment and
an optional ``story.mechanics.weather`` block into generator arguments. It is deliberately
read-only: weather never advances game time, writes a save or changes a journey version.

Author configuration (all optional)::

    mechanics.weather = {
      "seed": 12345,                 # default: stable hash of story.id
      "climate": "temperate",        # fallback for places without coordinates
      "season": "autumn",            # optional override
      "fantasy": ["spirit_mist"],    # optional, default excludes fantasy kinds
      "locations": {
        "harbour": {"climate": "maritime", "coast_distance_km": 8}
      }
    }

Unknown or invalid values are ignored rather than guessed silently; ``report`` says which
source produced the climate. The route is read-only and never changes ``state_version``.
"""
from __future__ import annotations

import hashlib

from . import weather

#: Player-facing names. The generator's ids stay stable; only display text lives here.
LABELS = {
    'clear': '晴', 'cloudy': '多云', 'overcast': '阴', 'fog': '雾', 'drizzle': '毛毛雨',
    'rain': '雨', 'storm': '雷暴', 'snow': '雪', 'blizzard': '暴风雪', 'sleet': '雨夹雪',
    'hail': '冰雹', 'freezing_rain': '冻雨', 'graupel': '霰', 'frost': '霜', 'rime': '雾凇',
    'dust': '浮尘', 'blowing_sand': '扬沙', 'sandstorm': '沙暴', 'haze': '霾',
    'heatwave': '热浪', 'sunshower': '太阳雨', 'typhoon': '台风', 'tornado': '龙卷风',
    'mana_storm': '魔力风暴', 'spirit_mist': '灵雾', 'miasma': '瘴气', 'ashfall': '灰烬雨',
}
SEASONS = set(weather.SEASONS)
CLIMATES = set(weather.CLIMATES)
MAX_FORECAST_HOURS = 72


def label(kind):
    return LABELS.get(kind, kind)


def _weather_config(story):
    mechanics = story.get('mechanics') if isinstance(story, dict) else None
    block = (mechanics or {}).get('weather')
    return block if isinstance(block, dict) else {}


def _seed(story, block):
    seed = block.get('seed')
    if isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed <= weather.MAX_SEED:
        return seed, 'config'
    text = str(story.get('id') or story.get('title') or 'textingdream')
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') % (weather.MAX_SEED + 1), 'derived'


def _place(story, session):
    location_id = session.get('location')
    for place in story.get('locations') or ():
        if place.get('id') == location_id:
            return place
    return {}


def _climate(place, block, local):
    configured = local.get('climate') or block.get('climate')
    if configured in CLIMATES:
        return configured, 'config'
    coordinates = place.get('coordinates')
    lat = coordinates[1] if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2 else None
    biome = place.get('biome')
    try:
        guessed = weather.climate_for(biome, lat)
    except ValueError:
        guessed = 'temperate'
    return guessed, 'biome' if biome is not None else ('latitude' if lat is not None else 'default')


def _arguments(story, session):
    block = _weather_config(story)
    place = _place(story, session)
    local = (block.get('locations') or {}).get(place.get('id')) or {}
    if not isinstance(local, dict):
        local = {}
    climate, climate_source = _climate(place, block, local)

    seed, seed_source = _seed(story, block)
    coordinates = place.get('coordinates')
    lon = coordinates[0] if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2 else None
    lat = coordinates[1] if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2 else None
    environment = place.get('environment') if isinstance(place.get('environment'), dict) else {}
    elevation = environment.get('elevation_m')

    fantasy = block.get('fantasy')
    if not isinstance(fantasy, (list, tuple)):
        fantasy = ()
    fantasy = tuple(kind for kind in fantasy if kind in weather.FANTASY)

    season = block.get('season')
    if season not in SEASONS:
        season = None

    coast = local.get('coast_distance_km')
    if not isinstance(coast, (int, float)) or isinstance(coast, bool) or not 0 <= coast <= 1000:
        coast = None

    time = session.get('time')
    if not isinstance(time, int) or isinstance(time, bool) or time < 0:
        time = 0
    day, hour = time // 24 + 1, time % 24
    return {
        'seed': seed, 'seed_source': seed_source, 'day': day, 'hour': hour,
        'climate': climate, 'climate_source': climate_source,
        'options': {
            'season': season,
            'fantasy': fantasy,
            'lon': lon, 'lat': lat, 'elevation': elevation,
            'calendar': (story.get('mechanics') or {}).get('calendar'),
            'coast_distance_km': coast,
        },
        'place': {'id': place.get('id'), 'name': place.get('name')},
    }


def _compact(state):
    return {
        'kind': state['kind'], 'label': label(state['kind']),
        'intensity': state['intensity'], 'temperature_c': state['temperature_c'],
        'precipitation': state['precipitation'], 'cloud_cover': state['cloud_cover'],
        'wind': state['wind'], 'humidity': state['humidity'],
        'visibility': state['visibility'], 'season': state['season'],
        'climate': state['climate'],
    }


def report(story, session, hours=0):
    """Current weather plus an optional hourly forecast.

    ``hours`` is clamped to 0..72. A zero-hour report still returns the current state so
    the UI can show it without paying for the forecast walk.
    """
    if not isinstance(hours, int) or isinstance(hours, bool):
        hours = 0
    hours = max(0, min(hours, MAX_FORECAST_HOURS))
    args = _arguments(story, session)
    current = weather.weather_at(args['seed'], args['day'], args['hour'], args['climate'],
                                 **args['options'])
    result = {
        'enabled': True,
        'place': args['place'],
        'day': args['day'], 'hour': args['hour'],
        'climate': args['climate'], 'climate_source': args['climate_source'],
        'seed_source': args['seed_source'],
        'current': _compact(current),
        'forecast': [],
        'note': '天气由本地确定性生成，不改变旅程时间、资源或存档版本。',
    }
    if hours:
        states = weather.forecast(args['seed'], args['day'], args['hour'], hours,
                                  args['climate'], **args['options'])
        result['forecast'] = [_compact(state) for state in states]
    return result
