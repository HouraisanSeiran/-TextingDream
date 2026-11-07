# -*- coding: utf-8 -*-
"""Location clues: "it is somewhere around here" hints that sit on top of the fog.

A clue is earned from an event action or a quest (``{'op': 'place_clue', ...}`` through
:meth:`app.runtime.Runtime.effects`). It names a story location, but what the player gets
is only a **displaced circle**: a centre that is deliberately *not* the true position, and
a radius that is guaranteed to contain it. Four rules:

1. **The true position never reaches the player.** The session stores the displaced centre
   computed once at grant time; the projection reads only that. A withheld place (author
   only / reveal flag unset) is listed without its id or real name.
2. **The circle is honest.** The offset is at most ``MAX_OFFSET_FRACTION`` of the radius,
   so the real place is always inside — vague, never wrong.
3. **Deterministic.** The offset comes from the journey seed, the place id and how many
   clues the journey already holds, so replaying the same effect gives the same circle,
   and a second clue for the same place lands somewhere else (two hints narrow it down).
4. **Fog stays fog.** A clue widens the crop box so its circle can be drawn, but never
   reveals pixels: terrain inside a clue circle is still painted fog colour by the server.

A clue is *resolved* (dropped from the projection) once the journey has stood on the place.
"""
import hashlib
import math

from . import play_map

MIN_PRECISION_KM = 10.0
MAX_PRECISION_KM = 2000.0
DEFAULT_PRECISION_KM = 150.0
#: Upper bound on how far the drawn centre may sit from the truth, as a share of the radius.
MAX_OFFSET_FRACTION = 0.8
#: Lower bound, so a clue never happens to land exactly on the place.
MIN_OFFSET_FRACTION = 0.25
MAX_TEXT = 200
MAX_LABEL = 40
MAX_CLUES = 200
UNKNOWN_LABEL = '传闻中的某处'


def _precision(effect):
    value = effect.get('precision_km', DEFAULT_PRECISION_KM)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('place_clue 的 precision_km 必须是数字')
    if not MIN_PRECISION_KM <= value <= MAX_PRECISION_KM:
        raise ValueError('place_clue 的 precision_km 必须在 %g…%g km 之间'
                         % (MIN_PRECISION_KM, MAX_PRECISION_KM))
    return float(value)


def validate_effect(effect, story):
    """Package-time check for one ``place_clue`` effect. Returns the target place."""
    target = effect.get('place')
    place = next((p for p in story.get('locations') or [] if p.get('id') == target), None)
    if place is None:
        raise ValueError('place_clue 指向的地点不存在：%r' % target)
    if play_map.location_coordinates(place) is None:
        raise ValueError('place_clue 指向的地点 %r 没有 coordinates，无法给出大致位置' % target)
    _precision(effect)
    for key, limit in (('text', MAX_TEXT), ('label', MAX_LABEL)):
        value = effect.get(key, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError('place_clue 的 %s 必须是不超过 %d 字的文本' % (key, limit))
    return place


def _unit(seed_text, salt):
    digest = hashlib.sha256(('%s|%s' % (seed_text, salt)).encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') / float(1 << 64)


def _offset(lon, lat, distance_km, bearing):
    """Point ``distance_km`` from (lon, lat) along ``bearing`` (radians), on the sphere."""
    delta = distance_km / play_map.EARTH_RADIUS_KM
    phi1, lam1 = math.radians(lat), math.radians(lon)
    phi2 = math.asin(math.sin(phi1) * math.cos(delta)
                     + math.cos(phi1) * math.sin(delta) * math.cos(bearing))
    lam2 = lam1 + math.atan2(math.sin(bearing) * math.sin(delta) * math.cos(phi1),
                             math.cos(delta) - math.sin(phi1) * math.sin(phi2))
    return ((math.degrees(lam2) + 180.0) % 360.0) - 180.0, math.degrees(phi2)


def displaced_centre(seed, place_id, ordinal, lon, lat, radius_km):
    """Where the clue circle is drawn. Always within ``MAX_OFFSET_FRACTION * r`` of truth."""
    key = '%s|%s|%d' % (seed, place_id, ordinal)
    share = MIN_OFFSET_FRACTION + (MAX_OFFSET_FRACTION - MIN_OFFSET_FRACTION) * _unit(key, 'd')
    bearing = 2.0 * math.pi * _unit(key, 'b')
    clon, clat = _offset(lon, lat, share * radius_km, bearing)
    if abs(clat) > 84.0:                       # basemap frame stops at ±84°: go the other way
        clon, clat = _offset(lon, lat, share * radius_km, bearing + math.pi)
    return clon, clat


def grant(session, story, effect, source, record_id, time):
    """Apply one ``place_clue`` effect to ``session`` (in place). Returns the clue record."""
    place = validate_effect(effect, story)
    radius = _precision(effect)
    lon, lat = play_map.location_coordinates(place)
    clues = session.setdefault('clues', [])
    if len(clues) >= MAX_CLUES:
        raise ValueError('这段旅程的线索已达上限')
    clon, clat = displaced_centre(session.get('seed') or session.get('id'), place['id'],
                                  len(clues), lon, lat, radius)
    record = {'id': record_id, 'place': place['id'], 'lon': round(clon, 5),
              'lat': round(clat, 5), 'radius_km': radius,
              'label': effect.get('label') or '', 'text': effect.get('text') or '',
              'source': source, 'time': time}
    clues.append(record)
    return record


def projection(session, story):
    """Unresolved clues as the player may see them: no true position, no hidden ids."""
    by_id = {p['id']: p for p in story.get('locations') or []}
    reached = set(session.get('explored') or []) | {session.get('location')}
    out = []
    for clue in session.get('clues') or []:
        place = by_id.get(clue.get('place'))
        if place is None or clue.get('place') in reached:
            continue
        withheld = play_map._place_withheld(place, session)
        label = clue.get('label') or (UNKNOWN_LABEL if withheld else (place.get('name') or UNKNOWN_LABEL))
        out.append({'id': clue['id'], 'label': label, 'lon': clue['lon'], 'lat': clue['lat'],
                    'radius_km': clue['radius_km'], 'text': clue.get('text') or '',
                    'source': clue.get('source') or ''})
    return out


def frame_circles(clues):
    """Clue circles for the crop box only — they never feed the reveal mask."""
    return [{'lon': c['lon'], 'lat': c['lat'], 'radius_km': c['radius_km'], 'state': 'clue'}
            for c in clues]
