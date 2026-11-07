"""Shared catalog and art helpers for the town layout generator.

Pure functions over metadata dicts; no world state, database or service access.
Pixel conventions follow docs/town-art-spec.md: CELL = 48, an item's ``x`` is
the left edge of the symbol viewBox, ``bottom`` is the anchor (front edge) y and
``key`` is the depth-sort key (front y + same-cell offset).
"""
import hashlib
import random
import re

CELL = 48
ORDER = ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw')
DIRS8 = {'n': (0, -1), 'ne': (1, -1), 'e': (1, 0), 'se': (1, 1),
         's': (0, 1), 'sw': (-1, 1), 'w': (-1, 0), 'nw': (-1, -1)}
DIR_OF = {v: k for k, v in DIRS8.items()}
OPPOSITE = {d: ORDER[(i + 4) % 8] for i, d in enumerate(ORDER)}
SORT_OFFSET = {'n': .1, 'ne': .1, 'nw': .1, 'node': .2, 'e': .3, 'w': .3,
               's': .4, 'se': .4, 'sw': .4}
DUAL_RE = re.compile(r'-[01]{4}$')
# Prop id fragments: goods suit market/craft blocks, the rest is greenery.
GOODS = ('barrel', 'crate', 'woodpile', 'hay', 'cask', 'jar', 'basket', 'cart', 'wagon',
         'trough', 'ingot', 'ore', 'sack', 'camel', 'carrypole', 'wheelbarrow', 'hitching',
         'bench', 'signpost', 'stonetable')
PROP_SKIP = ('fence', 'clothesline', 'puddle', 'stall', 'well-bits', 'campfire')
TREES = ('tree', 'bush', 'bamboo', 'pine', 'willow', 'plum', 'datepalm', 'plantain',
         'silverleaf', 'boulder', 'rock', 'grass-tuft', 'flower-clump')


def rng_for(*parts):
    """Deterministic random.Random from any printable parts."""
    digest = hashlib.sha256('|'.join(map(str, parts)).encode()).digest()
    return random.Random(int.from_bytes(digest, 'big'))


def cell_hash(seed, x, y):
    """Stable per-cell hash, used for texture variants (no global RNG drift)."""
    return int.from_bytes(hashlib.blake2b(f'{seed}:{x}:{y}'.encode(),
                                          digest_size=4).digest(), 'big')


def mask_at(cells, i, j):
    """Dual-grid corner code NW*8 + NE*4 + SW*2 + SE*1 for render tile (i, j)."""
    return sum(bit for dx, dy, bit in ((-1, -1, 8), (0, -1, 4), (-1, 0, 2), (0, 0, 1))
               if (i + dx, j + dy) in cells)


def dual_tiles(cells, prefix, meta):
    """Dual-grid tiles for a logical cell set; returns (tiles, missing ids)."""
    out, lost = [], []
    tiles = {(x + dx, y + dy) for x, y in cells for dx in (0, 1) for dy in (0, 1)}
    for i, j in sorted(tiles, key=lambda p: (p[1], p[0])):
        ident = prefix + format(mask_at(cells, i, j), '04b')
        if ident not in meta:
            lost.append(ident)
            continue
        out.append({'id': ident, 'x': i * CELL - 24, 'bottom': j * CELL + 24,
                    'key': j * CELL + 24, 'tile': [i, j]})
    return out, lost


def place(m, ax, front, key=None):
    """Item whose anchor sits at pixel (ax, front); honours viewBox[0] (pad_x)."""
    vb = m.get('viewBox') or [0, 0, 0, 0]
    return {'id': m['id'], 'x': ax - (m['anchor'][0] - vb[0]), 'bottom': front,
            'key': front if key is None else key}


def place_cells(m, x, y, offset=0.0):
    """Item for meta m whose footprint's top-left cell is (x, y)."""
    fw, fd = m['footprint']
    front = (y + fd) * CELL
    return place(m, (x + fw / 2) * CELL, front, front + offset)


def footprint_cells(x, y, fw, fd):
    return {(xx, yy) for yy in range(y, y + fd) for xx in range(x, x + fw)}


def normalize_catalog(catalog, loader):
    rows = catalog if catalog is not None else loader()
    rows = rows.get('meta', rows) if isinstance(rows, dict) else rows
    rows = list(rows.values()) if isinstance(rows, dict) else list(rows)
    return rows, {m['id']: m for m in rows}


_POOL_SKIP = ('spoke', 'node', 'gatehouse', 'drawbridge', 'moat', 'castlewall', 'yard')


def facility_pool(rows, style, race, kind):
    """All variants for one FacilityKind: town, castle-annex and per-directory art.

    Returns (pool, fallback). Racial towns use their own variants when any exist,
    otherwise fall back to the western human (common) pool with fallback=True.
    """
    def pick(st, rc):
        found = [m for m in rows if m.get('style') == st and m.get('race', 'common') == rc
                 and m.get('facility') == kind and not m.get('resource')
                 and m.get('category') in ('special', 'castle', 'prop')
                 and not any(s in m['id'] for s in _POOL_SKIP)]
        solid = [m for m in found if m['category'] != 'prop']
        # Props join the pool for wells (stand-alone well heads) or when nothing else exists.
        return sorted(found if kind == 'well' or not solid else solid, key=lambda m: m['id'])
    if race != 'common':
        own = pick(style, race)
        return (own, False) if own else (pick('west', 'common'), True)
    return pick(style, 'common'), False


def prop_pools(rows, style, race):
    """Ground props split into goods / greenery / race-specific pools."""
    props = [m for m in rows if m.get('category') == 'prop' and m.get('style') == style
             and not m.get('resource') and not m.get('facility')
             and list(m.get('footprint', [1, 1])) == [1, 1]
             and not any(s in m['id'] for s in PROP_SKIP)]
    common = sorted((m for m in props if m.get('race', 'common') == 'common'),
                    key=lambda m: m['id'])
    goods = [m for m in common if any(g in m['id'] for g in GOODS)]
    green = [m for m in common if m not in goods]
    trees = [m for m in green if any(t in m['id'] for t in TREES)]
    own = sorted((m for m in props if race != 'common' and m.get('race') == race),
                 key=lambda m: m['id'])
    return {'goods': goods, 'green': green, 'trees': trees or green, 'race': own}
