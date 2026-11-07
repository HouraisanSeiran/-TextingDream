"""Replaceable terrain layer for town layouts.

The generator only talks to this interface. A terrain is a dict, or a callable
``fn(w, h, seed, skeleton) -> dict``, with these optional keys:

  w, h        final grid size (the seeded terrain grows the grid to fit water)
  water       iterable of [x, y] water cells
  water_kind  'river' | 'sea' | 'lake' | None  (bank vs quay shore, bridges)
  water_side  'n' | 's' | 'e' | 'w'  (inferred from the water cells if absent)
  elevation   {(x, y): float}, {"x,y": float} or a list of rows, nominally 0..1
  blocked     iterable of [x, y] cells nothing may be built on (cliffs, rocks)
  source      label: 'seeded' today; later e.g. 'civ-atlas' or another algorithm

Nothing here reads world state; seeded_terrain() is only today's default source.
"""
import math

from .town_layout_art import rng_for

STEEP = 0.25   # max elevation step to a 4-neighbour that still allows building
SIDES = ('n', 's', 'e', 'w')


def _cells(values, w, h):
    return {(int(p[0]), int(p[1])) for p in values or ()
            if 0 <= int(p[0]) < w and 0 <= int(p[1]) < h}


def _elevation(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        out = {}
        for key, value in raw.items():
            if isinstance(key, str):
                key = tuple(int(v) for v in key.split(','))
            out[tuple(key)] = float(value)
        return out
    return {(x, y): float(v) for y, row in enumerate(raw) for x, v in enumerate(row)}


class Terrain:
    """Normalised terrain; all members are plain sets/dicts over grid cells."""

    def __init__(self, data, w, h):
        self.w, self.h = int(data.get('w') or w), int(data.get('h') or h)
        self.water = _cells(data.get('water'), self.w, self.h)
        self.blocked = _cells(data.get('blocked'), self.w, self.h) - self.water
        self.elev = _elevation(data.get('elevation'))
        kind = data.get('water_kind')
        self.kind = (kind or 'river') if self.water else None
        self.source = data.get('source', 'custom')
        side = data.get('water_side')
        self.side = side if side in SIDES and self.water else self._infer_side()

    def _infer_side(self):
        if not self.water:
            return None
        mx = sum(x for x, _ in self.water) / len(self.water) / max(1, self.w - 1) - .5
        my = sum(y for _, y in self.water) / len(self.water) / max(1, self.h - 1) - .5
        if abs(mx) > abs(my):
            return 'e' if mx > 0 else 'w'
        return 's' if my >= 0 else 'n'

    def elevation(self, x, y):
        return self.elev.get((x, y), 0.0)

    def steep(self, x, y):
        e = self.elevation(x, y)
        return any(abs(self.elevation(x + dx, y + dy) - e) > STEEP
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if (x + dx, y + dy) in self.elev)

    def summary(self):
        return {'source': self.source, 'water_kind': self.kind, 'water_side': self.side,
                'blocked': sorted(map(list, self.blocked))}


def load_terrain(terrain, w, h, seed, skeleton):
    """Resolve the ``terrain`` argument of layout() into a Terrain."""
    if terrain is None:
        terrain = seeded_terrain
    data = terrain(w, h, seed, skeleton) if callable(terrain) else dict(terrain)
    return Terrain(data, w, h)


def _runs(rng, n, lo, hi, start, min_run=3, max_run=6):
    """Row per column that only changes by 1 after runs of >= min_run columns."""
    out, value = [], start
    while len(out) < n:
        out.extend([value] * rng.randint(min_run, max_run))
        value = max(lo, min(hi, value + rng.choice((-1, 0, 0, 1))))
    return out[:n]


def canonical(side, w, h):
    """(U, V, to_world, to_canon) for a frame where the water side is 'south'.

    In canonical (u, v) coordinates v grows towards the water side.
    """
    if side == 'e':
        return h, w, lambda u, v: (v, u), lambda x, y: (y, x)
    if side == 'w':
        return h, w, lambda u, v: (w - 1 - v, u), lambda x, y: (y, w - 1 - x)
    if side == 'n':
        return w, h, lambda u, v: (u, h - 1 - v), lambda x, y: (x, h - 1 - y)
    return w, h, lambda u, v: (u, v), lambda x, y: (x, y)


def water_plan(seed, skeleton):
    """(kind, side) the seeded terrain will use; lets the caller size the grid."""
    water_info = skeleton.get('water') or {}
    if hasattr(water_info, 'model_dump'):
        water_info = water_info.model_dump(mode='json')
    source = water_info.get('source') if isinstance(water_info, dict) else None
    kind = ('sea' if skeleton.get('town_type') == 'port' else
            'river' if source == 'river' else 'lake' if source == 'lake' else None)
    if not kind:
        return None, None
    side = water_info.get('side') if isinstance(water_info, dict) else None
    side = 's' if kind == 'sea' else side if side in SIDES else rng_for(
        'terrain-side', seed).choice(SIDES)
    return kind, side


def seeded_terrain(w, h, seed, skeleton):
    """Today's default terrain source: a coast / river / lake band plus rocks.

    Only depends on the town skeleton (town_type, water.source, optional
    water.side). Elevation is a gentle slope that never blocks building.
    """
    rng = rng_for('terrain', seed)
    kind, side = water_plan(seed, skeleton)
    data = {'source': 'seeded', 'w': w, 'h': h, 'water_kind': kind}
    water = set()
    if kind:
        U, V, world, _ = canonical(side, w, h)
        if kind == 'river':
            tops = _runs(rng, U, V - 5, V - 4, rng.choice((V - 5, V - 4)), 5, 9)
            widths = _runs(rng, U, 1, 2, 1, 4, 8)
            for u in range(U):
                water |= {world(u, v) for v in range(tops[u], tops[u] + widths[u])}
        else:
            base = V - 3 - rng.randint(0, 1)
            shore = _runs(rng, U, base - 1, base + 1, base, 5, 9)
            for u in range(U):
                water |= {world(u, v) for v in range(shore[u], V)}
        data['water_side'] = side
    data['water'] = sorted(map(list, water))
    blocked = set()
    for _ in range(rng.randint(0, 2)):
        cx, cy = rng.randint(2, w - 3), rng.randint(2, h - 3)
        for _ in range(rng.randint(1, 3)):
            blocked.add((cx, cy))
            cx += rng.choice((-1, 0, 1))
            cy += rng.choice((-1, 0, 1))
    data['blocked'] = sorted(map(list, blocked - water))
    ax, ay, phase = rng.uniform(.5, 1.5), rng.uniform(.5, 1.5), rng.uniform(0, math.tau)
    data['elevation'] = [[round(.5 + .08 * math.sin(ax * x / w * math.pi + phase)
                                + .08 * math.cos(ay * y / h * math.pi), 3)
                          for x in range(w)] for y in range(h)]
    return data
