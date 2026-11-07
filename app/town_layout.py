"""Deterministic local town plans; world placement remains the civ-atlas cell.

Accepts a TownSnapshot (or model_dump dict): skeleton.scale/town_type/water,
built.districts/facilities/style.roof, and town_id. Flat equivalents are accepted.
Missing fields default to a village, residential district and gable_tile roof.
Coordinates are local cells, not world coordinates. Buildings never occupy walls
or streets. Terrain (water, elevation, unbuildable cells) comes from a
replaceable layer, see app/town_layout_terrain.py.

Output layers, drawn in this order by app/static/town-render.js:
  underlay  base ground textures, yards, water tiles, moat (two passes for east)
  ground    road dual-grid tiles (legacy field: roads only)
  items     everything standing, sorted by (key, x)
"""
import json
from pathlib import Path

from .building_economy import profile_for
from .town_layout_art import (CELL, SORT_OFFSET, cell_hash, dual_tiles, facility_pool,
                              footprint_cells, normalize_catalog, place, place_cells,
                              prop_pools, rng_for)
from .town_layout_fort import Fortifier, gate_item, plan_level
from .town_layout_terrain import load_terrain, water_plan
from .town_layout_wall import (choose_gates, convex, gate_candidates, loop_dirs, node_id,
                               outline, tower_cells, tower_ids)

ART = Path(__file__).parent / 'static' / 'map-art' / 'town'
SIZES = {'hamlet': (14, 12), 'village': (18, 15), 'small_town': (24, 19),
         'town': (30, 23), 'city': (38, 29)}
STYLES = ('west', 'east', 'arab')
RACES = ('common', 'human', 'elf', 'dwarf', 'orc')
WALL_SHAPES = ('irregular', 'square')
FORT_TYPES = ('pass_fortress', 'border_fortress')
GATE_COUNT = {'hamlet': 1, 'village': 1, 'small_town': 2, 'town': 2, 'city': 4}
# Normalized x/y targets; southeast is the authored default downwind direction.
DISTRICT_ZONES = {
    'market': (.5, .5), 'administration': (.5, .25), 'temple': (.4, .22),
    'craft': (.7, .6), 'industrial': (.82, .8), 'harbor': (.9, .5),
    'cemetery': (.12, .12), 'military': (.5, .85), 'academy': (.25, .25),
    'storage': (.8, .65), 'foreign_quarter': (.25, .75), 'poor': (.15, .8),
    'outskirts': (.12, .55), 'residential': (.35, .5),
}
FACILITY_DISTRICTS = {
    'town_hall': 'administration', 'lord_hall': 'administration',
    'market_hall': 'market', 'temple': 'temple', 'academy': 'academy',
    'forge': 'craft', 'smelter': 'industrial', 'kiln': 'industrial',
    'tannery': 'industrial', 'boiler_house': 'industrial', 'dock': 'harbor',
    'bridge': 'harbor', 'warehouse': 'storage', 'granary': 'storage',
    'cemetery': 'cemetery', 'barracks': 'military', 'watchtower': 'military',
    'mine_head': 'outskirts', 'caravanserai': 'foreign_quarter',
}
STYLE_ART = {
    'west': {'yard': 'west-common-ground-dirt-', 'base': 'west-common-ground-grass-',
             'bank': 'west-common-water-bank-', 'quay': 'west-common-water-quay-'},
    'east': {'yard': 'east-common-ground-paving-', 'base': 'east-common-ground-earth-',
             'bank': 'east-common-water-bank-', 'quay': 'east-common-water-quay-'},
    'arab': {'yard': 'arab-common-road-tile-', 'base': None,
             'bank': 'arab-common-water-oasis-', 'quay': 'arab-common-water-oasis-'},
}
GOODS_ZONES = ('market', 'craft', 'storage', 'industrial', 'harbor', 'foreign_quarter')


def _art_dirs(root):
    return sorted(d.name for d in root.iterdir() if (d / 'meta.json').is_file()) \
        if root.is_dir() else []


DIRS = tuple(_art_dirs(ART))


def load_catalog(root=None):
    """Read every art directory's meta.json; return a TOWN_CATALOG-like dict."""
    base = Path(root) if root else ART
    rows, dirs = [], _art_dirs(base)
    for directory in dirs:
        for row in json.loads((base / directory / 'meta.json').read_text(encoding='utf-8')):
            rows.append(dict(row, dir=directory))
    return {'dirs': dirs, 'meta': rows}


def _dict(value):
    return value.model_dump(mode='json') if hasattr(value, 'model_dump') else (value or {})


def _economy(m):
    profile = profile_for(m) if m else None
    return profile.id if profile else None


def _n4(cell):
    x, y = cell
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _ring(x, y, fw, fd):
    """Cells 8-adjacent to a footprint (outside it)."""
    return footprint_cells(x - 1, y - 1, fw + 2, fd + 2) - footprint_cells(x, y, fw, fd)


def _edge(x, y, fw, fd):
    """Cells 4-adjacent to a footprint (outside it), front row first."""
    front = [(xx, y + fd) for xx in range(x, x + fw)]
    rest = ([(xx, y - 1) for xx in range(x, x + fw)] + [(x - 1, yy) for yy in range(y, y + fd)]
            + [(x + fw, yy) for yy in range(y, y + fd)])
    return front + rest


def _step(cell, side):
    dx, dy = SIDE_STEP[side]
    return cell[0] + dx, cell[1] + dy


SIDE_STEP = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0)}
LEVEL_PAD = {'none': 0, 'light': 1, 'normal': 2, 'heavy': 3}
WATER_PAD = 6


def _path(sources, targets, passable, limit=10 ** 6):
    """Shortest 4-connected path (source .. target inclusive) or None."""
    from collections import deque
    sources = sorted(set(sources))
    prev, depth = dict.fromkeys(sources), dict.fromkeys(sources, 0)
    queue = deque(sources)
    while queue:
        cur = queue.popleft()
        if cur in targets:
            out = []
            while cur is not None:
                out.append(cur)
                cur = prev[cur]
            return out[::-1]
        if depth[cur] >= limit:
            continue
        for q in _n4(cur):
            if q not in prev and (q in targets or passable(q)):
                prev[q], depth[q] = cur, depth[cur] + 1
                queue.append(q)
    return None


def _components(cells):
    cells, out = set(cells), []
    while cells:
        start = min(cells)
        comp, stack = {start}, [start]
        while stack:
            for q in _n4(stack.pop()):
                if q in cells and q not in comp:
                    comp.add(q)
                    stack.append(q)
        cells -= comp
        out.append(comp)
    return out


def layout(town, style='west', race='common', seed=None, catalog=None, *,
           wall_shape='irregular', terrain=None, fortification=None, landmarks=None):
    """Return a JSON-compatible local town plan.

    style: west / east / arab (all human cultures). race: common / human (same)
    / elf / dwarf / orc; east and arab have no racial variants and fall back to
    common. wall_shape: 'irregular' (spoke walls) or 'square' (dual-grid tiles).
    terrain: None (seeded default), a dict or a callable, see
    app/town_layout_terrain.py. fortification: None (by town type and scale) or
    none / light / normal / heavy. landmarks: None (random 0-2) or a count.

    building.facility is the source FacilityKind; source is its original id (or
    its list index). Walls/gates are infrastructure entries, not building lots.
    missing entries carry the same source, facility and a reason; notes about
    racial fallbacks use for_source so every source is accounted exactly once.
    A supplied catalog may be a metadata list, id->metadata map or {'meta': [...]}.
    """
    if style not in STYLES or race not in RACES:
        raise ValueError('unsupported style or race')
    if wall_shape not in WALL_SHAPES:
        raise ValueError('unsupported wall_shape')
    return _Town(town, style, race, seed, catalog, wall_shape, terrain,
                 fortification, landmarks).build()


class _Town:
    def __init__(self, town, style, race, seed, catalog, shape, terrain, level, landmarks):
        town = _dict(town)
        self.style = style
        self.race = 'common' if race == 'human' or style != 'west' else race
        self.shape = shape
        self.skeleton = _dict(town.get('skeleton', town))
        self.built = _dict(town.get('built', town))
        self.rows, self.meta = normalize_catalog(catalog, load_catalog)
        key = town.get('town_id') or town.get('id') or town.get('seed', 'town')
        self.seed = str(key if seed is None else seed)
        self.rng = rng_for('layout', self.seed)
        self.scale = self.skeleton.get('scale', 'village')
        self.scale = self.scale if self.scale in SIZES else 'village'
        self.town_type = self.skeleton.get('town_type')
        self.facilities = [_dict(f) for f in self.built.get('facilities', [])]
        self.districts = {}
        for d in self.built.get('districts', []):
            d = _dict(d)
            if 'id' in d:
                self.districts[d['id']] = d
        kinds = {f.get('kind') for f in self.facilities}
        self.kinds = kinds
        self.walled = (bool(kinds & {'city_wall', 'gate'}) or self.scale in ('town', 'city')
                       or self.town_type in FORT_TYPES)
        self.level = plan_level(self.town_type, self.scale, self.walled,
                                rng_for('fort-level', self.seed), level)
        self.landmark_count, self.terrain_arg = landmarks, terrain
        self.missing, self.buildings, self.items, self.props = [], [], [], []
        self.underlay, self.landmarks, self.forts, self.infrastructure = [], [], [], []
        self.roads, self.reserved, self.taken, self.fort_cells = set(), set(), set(), set()
        self.entrances, self.yard, self.moat_cells = set(), set(), set()
        self.owner, self.parcels, self.center = {}, [], None
        self.loop, self.loop_set, self.interior, self.region = [], set(), set(), set()
        self.dirs, self.convex, self.gates = {}, {}, []
        self.used, self.wall_items, self.tile_missing = {}, [], set()

    # -- terrain and wall ---------------------------------------------------
    def setup_terrain(self):
        w, h = SIZES[self.scale]
        pad = LEVEL_PAD[self.level] if self.walled else 0
        w, h = w + 2 * pad, h + 2 * pad
        self.margin = 1 + pad
        if self.terrain_arg is None:
            _, side = water_plan(self.seed, self.skeleton)
            h += WATER_PAD if side in ('n', 's') else 0
            w += WATER_PAD if side in ('e', 'w') else 0
        self.t = load_terrain(self.terrain_arg, w, h, self.seed, self.skeleton)
        self.w, self.h = self.t.w, self.t.h
        self.water, self.blocked = set(self.t.water), set(self.t.blocked)
        self.steep = ({(x, y) for y in range(self.h) for x in range(self.w) if self.t.steep(x, y)}
                      if self.t.elev else set())

    # -- wall outline and gates ---------------------------------------------
    def dock_depth(self):
        pool, _ = facility_pool(self.rows, self.style, self.race, 'dock')
        return max((m['footprint'][1] for m in pool), default=2)

    def setup_wall(self):
        t = self.t
        if self.walled:
            gap = 1
            if t.water:
                gap = 3 if t.kind in ('river', 'lake') else 2 + self.dock_depth()
            try:
                self.loop, self.interior = outline(t, self.margin, gap, self.shape,
                                                   rng_for('wall', self.seed))
            except ValueError:
                self.missing.append({'reason': 'wall_terrain', 'facility': 'city_wall'})
                self.walled, self.level = False, 'none'
        if not self.walled:
            land = {(x, y) for y in range(1, self.h - 1) for x in range(1, self.w - 1)}
            land -= self.water
            comps = _components(land - self.blocked)
            main = max(comps, key=len) if comps else set()
            self.interior = main | {c for c in self.blocked & land
                                    if any(q in main for q in _n4(c))}
            self.region = set(self.interior)
            self.buildable = self.interior - self.blocked - self.steep - self.water
            return
        self.loop_set = set(self.loop)
        self.region = self.loop_set | self.interior
        self.dirs, self.convex = loop_dirs(self.loop), convex(self.loop)
        self.buildable = self.interior - self.blocked - self.steep - self.water
        cands = [c for c in gate_candidates(self.loop, self.dirs, self.interior, self.region)
                 if self.free_land(_step(c[1], c[3]))]
        count = GATE_COUNT[self.scale]
        if self.town_type in FORT_TYPES:
            count = max(2, count)
        wet = self.t.side if self.water else None
        for index, cell, axis, side in choose_gates(cands, count, wet, rng_for('gates', self.seed),
                                                    len(self.loop)):
            self.gates.append({'index': index, 'cell': cell, 'axis': axis, 'side': side,
                               'water': side == wet})
        self.gates.sort(key=lambda g: g['index'])

    def free_land(self, cell):
        x, y = cell
        return (0 <= x < self.w and 0 <= y < self.h and cell not in self.water
                and cell not in self.blocked and cell not in self.loop_set
                and cell not in self.taken)

    # -- streets --------------------------------------------------------------
    def setup_roads(self):
        inner = self.interior - self.blocked - self.water
        if not inner:
            return
        cx = sum(x for x, _ in inner) / len(inner)
        cy = sum(y for _, y in inner) / len(inner)
        pool = sorted(self.buildable or inner)
        self.center = min(pool, key=lambda p: ((p[0] - cx) ** 2 + (p[1] - cy) ** 2, p))
        x0, y0 = self.center
        if self.walled:
            kept = []
            for g in self.gates:
                gx, gy = g['cell']
                dx, dy = SIDE_STEP[g['side']]
                path = _path([(gx - dx, gy - dy)], {self.center}, lambda q: q in inner)
                if not path:
                    continue
                kept.append(g)
                self.roads.add((gx, gy))
                self.roads |= set(path)
                x, y = gx + dx, gy + dy
                while self.free_land((x, y)) and (x, y) not in self.region:
                    self.roads.add((x, y))
                    x, y = x + dx, y + dy
            self.gates = kept
        else:
            for dx, dy in SIDE_STEP.values():
                x, y = x0, y0
                while (0 <= x < self.w and 0 <= y < self.h and (x, y) not in self.water
                       and (x, y) not in self.blocked):
                    self.roads.add((x, y))
                    x, y = x + dx, y + dy
        if self.scale in ('town', 'city') or self.town_type in ('market_town', 'city'):
            r = 1
            self.roads |= {(x, y) for y in range(y0 - r, y0 + r + 1)
                           for x in range(x0 - r, x0 + r + 1) if (x, y) in inner}

    def side_streets(self):
        inner = self.interior - self.blocked - self.water - self.taken
        if not inner or not self.center:
            return
        rng = rng_for('streets', self.seed)
        x0, y0 = self.center
        xs = [x for x, _ in inner]
        ys = [y for _, y in inner]
        lines = []
        sp = rng.choice((5, 6, 6, 7))
        for k in range(-8, 9):
            x = x0 + k * sp + rng.randint(-1, 1) * (k != 0)
            if min(xs) < x < max(xs):
                lines.append([(x, y) for y in range(min(ys), max(ys) + 1)])
        sp = rng.choice((5, 5, 6))
        for k in range(-8, 9):
            y = y0 + k * sp + rng.randint(-1, 1) * (k != 0)
            if min(ys) < y < max(ys):
                lines.append([(x, y) for x in range(min(xs), max(xs) + 1)])
        runs = []
        for line in lines:
            run = []
            for c in line + [None]:
                if c is not None and c in inner:
                    run.append(c)
                    continue
                if len(run) >= 3:
                    runs.append(run)
                run = []
        changed = True
        while changed:
            changed = False
            for run in list(runs):
                if any(c in self.roads or any(q in self.roads for q in _n4(c)) for c in run):
                    self.roads |= set(run)
                    runs.remove(run)
                    changed = True

    # -- cell predicates ------------------------------------------------------
    def in_grid(self, q):
        return 0 <= q[0] < self.w and 0 <= q[1] < self.h

    def free_cell(self, q):
        return (self.in_grid(q) and q not in self.water and q not in self.blocked
                and q not in self.loop_set and q not in self.roads and q not in self.taken
                and q not in self.entrances and q not in self.steep)

    def free_inside(self, q):
        return q in self.buildable and self.free_cell(q)

    def entrance_ok(self, x, y, fw, fd):
        e = (x + fw // 2, y + fd)
        return e in self.roads or (e in self.interior and self.free_inside(e))

    def fits_inside(self, x, y, fw, fd):
        return (all(self.free_inside(q) for q in footprint_cells(x, y, fw, fd))
                and self.entrance_ok(x, y, fw, fd))

    def bbox(self):
        cells = self.interior or {(0, 0)}
        xs, ys = [x for x, _ in cells], [y for _, y in cells]
        return min(xs), min(ys), max(xs), max(ys)

    def target(self, zone):
        x0, y0, x1, y1 = self.bbox()
        tx, ty = DISTRICT_ZONES.get(zone, DISTRICT_ZONES['residential'])
        return x0 + tx * (x1 - x0), y0 + ty * (y1 - y0)

    def connect(self, cell, passable, limit=40):
        """Lay a street from cell to the network; returns True when connected."""
        if cell in self.roads:
            return True
        path = _path([cell], self.roads, passable, limit)
        if not path:
            return False
        self.roads |= set(path)
        return True

    # -- fortifications ---------------------------------------------------------
    def fortify(self):
        self.replaced, self.no_tower, self.fort_items, self.moat_items = set(), set(), [], []
        if not self.walled:
            return
        f = Fortifier(self).run()
        self.forts, self.fort_items, self.moat_items = f.forts, f.items, f.moat
        self.moat_cells = {tuple(c) for c in f.moat_cells}
        self.missing.extend(f.missing)
        self.reserved |= f.reserved
        self.taken |= f.occupied | f.reserved
        self.replaced, self.no_tower = set(f.skip), set(f.no_tower)

    # -- landmarks ------------------------------------------------------------
    def wanted_landmarks(self):
        if self.landmark_count is not None:
            return max(0, min(2, int(self.landmark_count)))
        rng = rng_for('landmark-count', self.seed)
        base = {'hamlet': 0, 'village': .1, 'small_town': .35, 'town': .7, 'city': 1.35}
        value = base[self.scale]
        if self.town_type in ('religious_center', 'academy_town', 'city', 'pass_fortress',
                              'border_fortress') and self.scale not in ('hamlet', 'village'):
            value += .5
        return min(2, int(value) + (rng.random() < value - int(value)))

    def landmark_pool(self):
        rows = [m for m in self.rows if m.get('category') == 'landmark'
                and m.get('style') == self.style and 'aqueduct' not in m['id']
                and m.get('race', 'common') in ('common', self.race)]
        fort = {'pass_fortress': 'passfort', 'border_fortress': 'starfort'}.get(self.town_type)
        rng = rng_for('landmarks', self.seed)
        rows.sort(key=lambda m: m['id'])
        rng.shuffle(rows)
        # Racial fortresses and fortress-type landmarks first where they fit the town.
        rows.sort(key=lambda m: (not (m.get('race') == self.race != 'common'
                                      or (fort and fort in m['id'])),))
        if self.town_type not in FORT_TYPES:
            rows = [m for m in rows if 'passfort' not in m['id'] and 'starfort' not in m['id']]
        return rows

    def place_landmarks(self):
        want = self.wanted_landmarks()
        if not want or not self.interior:
            return
        x0, y0, x1, y1 = self.bbox()
        cx, cy = self.center or ((x0 + x1) / 2, (y0 + y1) / 2)
        rng = rng_for('landmark-spot', self.seed)
        for m in self.landmark_pool():
            if len(self.landmarks) >= want:
                break
            fw, fd = m['footprint']
            spots = []
            for y in range(y0, y1 - fd + 2):
                for x in range(x0, x1 - fw + 2):
                    if not self.fits_inside(x, y, fw, fd):
                        continue
                    if any(q in self.loop_set or q in self.reserved for q in _ring(x, y, fw, fd)):
                        continue
                    d = ((x + fw / 2 - cx) ** 2 + (y + fd / 2 - cy) ** 2) ** .5
                    spots.append((abs(d - 3 - fw / 2) + rng.random() * 1.5, x, y))
            if not spots:
                continue
            _, x, y = min(spots)
            entrance = (x + fw // 2, y + fd)
            cells = footprint_cells(x, y, fw, fd)
            self.taken |= cells
            if not self.connect(entrance, lambda q: self.free_inside(q) and q not in cells):
                self.taken -= cells
                continue
            self.reserved |= cells
            item = place_cells(m, x, y)
            self.items.append(item)
            self.landmarks.append({'id': m['id'], 'culture': m.get('culture'),
                                   'facility': m.get('facility'), 'cell': [x, y],
                                   'footprint': [fw, fd], 'economy': _economy(m)})
            for q in cells:
                self.owner[q] = self.landmarks[-1]

    # -- parcels (kept for compatibility: free rectangles between streets) -------
    def compute_parcels(self):
        free = {q for q in self.buildable if self.free_cell(q)}
        claimed = set()
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) not in free or (x, y) in claimed:
                    continue
                pw = 0
                while (x + pw, y) in free and (x + pw, y) not in claimed:
                    pw += 1
                pd = 1
                while all((xx, y + pd) in free and (xx, y + pd) not in claimed
                          for xx in range(x, x + pw)):
                    pd += 1
                claimed |= footprint_cells(x, y, pw, pd)
                self.parcels.append({'cell': [x, y], 'footprint': [pw, pd]})

    # -- buildings ------------------------------------------------------------
    def put(self, m, x, y, facility, district, source=None, pool=1):
        fw, fd = m['footprint']
        cells = footprint_cells(x, y, fw, fd)
        b = {'id': m['id'], 'facility': facility, 'district': district, 'cell': [x, y],
             'footprint': [fw, fd], 'source': source, 'economy': _economy(m),
             'variants': pool}
        self.buildings.append(b)
        item = place_cells(m, x, y)
        if source is not None:
            item['source'] = source
        self.items.append(item)
        self.taken |= cells
        for q in cells:
            self.owner[q] = b
        entrance = (x + fw // 2, y + fd)
        if entrance not in self.roads and self.in_grid(entrance):
            self.entrances.add(entrance)
        if facility:
            self.used.setdefault(facility, {})
            self.used[facility][m['id']] = self.used[facility].get(m['id'], 0) + 1
        return b

    def same_next_to(self, m, x, y, facility):
        """True when an 8-adjacent building of the same kind already uses m."""
        fw, fd = m['footprint']
        for q in _ring(x, y, fw, fd):
            b = self.owner.get(q)
            if b and b.get('facility') == facility and b['id'] == m['id']:
                return True
        return False

    def outside_free(self, q):
        x, y = q
        return (2 <= x < self.w - 2 and 2 <= y < self.h - 2 and q not in self.water
                and q not in self.blocked and q not in self.roads and q not in self.entrances
                and (not self.walled or q not in self.region)
                and q not in self.taken and q not in self.moat_cells)

    def try_inside(self, m, facility, zone, rng, tries=14):
        fw, fd = m['footprint']
        tx, ty = self.target(zone)
        x0, y0, x1, y1 = self.bbox()
        spots = []
        for y in range(y0, y1 - fd + 2):
            for x in range(x0, x1 - fw + 2):
                if self.fits_inside(x, y, fw, fd) and not self.same_next_to(m, x, y, facility):
                    spots.append(((x + fw / 2 - tx) ** 2 + (y + fd / 2 - ty) ** 2
                                  + rng.random() * 2, x, y))
        for _, x, y in sorted(spots)[:tries]:
            cells = footprint_cells(x, y, fw, fd)
            self.taken |= cells
            ok = self.connect((x + fw // 2, y + fd),
                              lambda q: self.free_inside(q) and q not in cells, 30)
            self.taken -= cells
            if ok:
                return x, y
        return None

    def try_dock(self, m):
        fw, fd = m['footprint']
        spots = []
        for y in range(self.h):
            for x in range(self.w):
                cells = footprint_cells(x, y, fw, fd)
                wet = sum((xx, y + fd) in self.water for xx in range(x, x + fw))
                if wet >= max(2, fw - 1) and all(self.outside_free(q) for q in cells):
                    gate = min((abs(g['cell'][0] - x) for g in self.gates), default=0)
                    spots.append((gate, x, y))
        return self._connect_outside(sorted(spots), fw, fd)

    def _connect_outside(self, spots, fw, fd):
        for _, x, y in spots[:16]:
            cells = footprint_cells(x, y, fw, fd)
            starts = [q for q in _edge(x, y, fw, fd) if q in self.roads or self.outside_free(q)]
            if any(q in self.roads for q in starts):
                return x, y
            self.taken |= cells
            path = _path([q for q in starts if q not in self.water], self.roads,
                         self.outside_free, 25)
            self.taken -= cells
            if path:
                self.roads |= set(path)
                return x, y
        return None

    def try_bridge(self, m):
        fw, fd = m['footprint']
        tags = set(m.get('tags') or ())
        ns = 'deck_ns' in tags or ('deck_ew' not in tags and fd > fw)
        span, cross = (fd, fw) if ns else (fw, fd)
        if span < 3:
            return None
        spots = []
        for y in range(self.h - fd + 1):
            for x in range(self.w - fw + 1):
                ok = True
                for c in range(cross):
                    line = [(x + c, y + k) if ns else (x + k, y + c) for k in range(span)]
                    ends, mid = (line[0], line[-1]), line[1:-1]
                    if not (all(self.outside_free(q) for q in ends)
                            and all(q in self.water for q in mid)):
                        ok = False
                        break
                if ok and 2 <= x and x + fw <= self.w - 2:
                    gate = min((abs(g['cell'][0] - x) + abs(g['cell'][1] - y)
                                for g in self.gates), default=0)
                    spots.append((gate, x, y))
        return self._connect_outside(sorted(spots), fw, fd)

    # -- facilities -------------------------------------------------------------
    def pool_area(self, kind):
        pool, _ = facility_pool(self.rows, self.style, self.race, kind)
        return max((m['footprint'][0] * m['footprint'][1] for m in pool), default=0)

    def infra_facility(self, kind, source):
        if kind == 'city_wall':
            placed = next(iter(self.wall_items), None)
        else:
            placed = next((g for g in self.infrastructure if 'cell' in g), None)
        if placed:
            self.infrastructure.append({'source': source, 'facility': kind, 'id': placed['id']})
        else:
            self.missing.append({'source': source, 'facility': kind,
                                 'reason': 'asset' if self.walled else 'unwalled'})

    def place_facilities(self):
        ordered = sorted(enumerate(self.facilities),
                         key=lambda p: (-self.pool_area(p[1].get('kind')), p[0]))
        for index, f in ordered:
            kind, source = f.get('kind'), f.get('id', str(index))
            if kind in ('city_wall', 'gate'):
                self.infra_facility(kind, source)
                continue
            if kind in ('dock', 'bridge') and not self.water:
                self.missing.append({'source': source, 'facility': kind, 'reason': 'no_water'})
                continue
            pool, fallback = facility_pool(self.rows, self.style, self.race, kind)
            if not pool:
                self.missing.append({'source': source, 'facility': kind, 'reason': 'asset'})
                continue
            district = self.districts.get(f.get('district'), {})
            zone = district.get('kind', FACILITY_DISTRICTS.get(kind, 'residential'))
            if kind == 'tannery':
                zone = 'industrial'
            rng = rng_for('facility', self.seed, index)
            used = self.used.get(kind, {})
            order = sorted(pool, key=lambda m: (used.get(m['id'], 0), rng.random()))
            spot = None
            for m in order:
                if kind == 'dock':
                    p = self.try_dock(m)
                elif kind == 'bridge':
                    p = self.try_bridge(m) if self.t.kind != 'sea' else None
                else:
                    p = self.try_inside(m, kind, zone, rng)
                if p:
                    spot = (m, p)
                    break
            if not spot:
                self.missing.append({'source': source, 'facility': kind, 'reason': 'space'})
                continue
            m, (x, y) = spot
            self.put(m, x, y, kind, district.get('id', zone), source, len(pool))
            if fallback:
                self.missing.append({'for_source': source, 'facility': kind, 'id': m['id'],
                                     'reason': 'racial_fallback',
                                     'note': f'{self.race} 无 {kind} 素材，回落西式人族版本'})

    # -- houses -----------------------------------------------------------------
    def district_at(self, x, y):
        zones = {d.get('kind') for d in self.districts.values()} & DISTRICT_ZONES.keys()
        return min(sorted(zones or {'residential'}),
                   key=lambda k: (x - self.target(k)[0]) ** 2 + (y - self.target(k)[1]) ** 2)

    def fill_houses(self):
        houses = [m for m in self.rows if m.get('category') == 'house'
                  and m.get('style') == self.style]
        own = [m for m in houses if m.get('race', 'common') == self.race]
        houses = sorted(own or [m for m in houses if m.get('race', 'common') == 'common'],
                        key=lambda m: m['id'])
        if not houses:
            return
        rng = rng_for('houses', self.seed)
        style_roof = _dict(self.built.get('style', {})).get('roof', 'gable_tile')
        reach = 1 if self.walled else 2
        near = set()
        for x, y in self.roads:
            near |= footprint_cells(x - reach, y - reach, 2 * reach + 1, 2 * reach + 1)
        x0, y0, x1, y1 = self.bbox()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if not self.free_inside((x, y)) or rng.random() > .72:
                    continue
                zone = self.district_at(x, y)
                district = next((d for d in self.districts.values() if d.get('kind') == zone), {})
                roof = district.get('roof', style_roof)
                cands = []
                for m in [h for h in houses if h.get('roof') == roof] or houses:
                    fw, fd = m['footprint']
                    cells = footprint_cells(x, y, fw, fd)
                    if not cells & near or not self.fits_inside(x, y, fw, fd):
                        continue
                    if any(self.owner.get(q, {}).get('id') == m['id'] for q in _edge(x, y, fw, fd)):
                        continue
                    cands.append(m)
                if cands:
                    preferred = [m for m in cands if m.get('roof') == roof] or cands
                    self.put(rng.choice(preferred), x, y, None, district.get('id', zone))

    # -- wall art -----------------------------------------------------------------
    def add_item(self, ident, item_fn, *args, **kw):
        m = self.meta.get(ident)
        if not m:
            self.tile_missing.add(ident)
            return None
        it = item_fn(m, *args, **kw)
        self.items.append(it)
        return it

    def spoke_key(self, m, x, y, part):
        off = m.get('sort_offset', SORT_OFFSET.get(part, .2))
        return (y + 1) * CELL + off

    def draw_gates(self, square):
        base = f'{self.style}-{self.race}'
        orc = self.race == 'orc'
        for g in self.gates:
            gx, gy = g['cell']
            ident = base + ('-gate-' if orc else '-wall-gate-') + g['axis']
            m = self.meta.get(ident)
            if not m:
                self.missing.append({'facility': 'gate', 'id': ident, 'reason': 'asset'})
                continue
            if orc and square:
                tile = [gx + 1, gy if g['axis'] == 'h' else gy + 1]
                target = next((it for it in self.items if it.get('tile') == tile), None)
                if target:
                    target['id'] = ident
            elif orc:
                # Replacement tile (h: 0011, v: 1010) centred on the gate cell's wall line;
                # the cell's own spokes and node are not drawn (draw_spoke_wall).
                horizontal = g['axis'] == 'h'
                bottom = gy * CELL + 24 if horizontal else (gy + 1) * CELL
                x = gx * CELL + (0 if horizontal else 24) - m['viewBox'][0]
                tile = [gx + 1, gy if horizontal else gy + 1]
                self.items.append({'id': ident, 'x': x, 'bottom': bottom, 'key': bottom,
                                   'tile': tile})
            else:
                self.items.append(gate_item(m, (gx, gy), g['axis'], False))
            self.infrastructure.append({'id': ident, 'facility': 'gate', 'cell': [gx, gy],
                                        'axis': g['axis'], 'side': g['side'],
                                        'water': g['water'], 'economy': None})

    def draw_square_wall(self):
        prefix = f'{self.style}-{self.race}-wall-'
        tiles, lost = dual_tiles(self.loop_set, prefix, self.meta)
        self.items.extend(tiles)
        self.wall_items = tiles
        for ident in lost:
            self.missing.append({'facility': None, 'id': ident, 'reason': 'tile_asset'})
        self.draw_gates(True)
        tower = ('west-common-wall-tower-round' if self.style == 'west' and self.race == 'common'
                 else f'{self.style}-{self.race}-wall-tower')
        if tower in self.meta:
            xs = [x for x, _ in self.loop]
            ys = [y for _, y in self.loop]
            for x, y in ((min(xs), min(ys)), (max(xs), min(ys)), (min(xs), max(ys)),
                         (max(xs), max(ys))):
                if (x, y) in self.loop_set:
                    front = (y + 1) * CELL
                    self.items.append(place(self.meta[tower], x * CELL + 24, front, front + 24.5))

    def draw_spoke_wall(self):
        st, rc = self.style, self.race
        spoke = f'{st}-{rc}-wallspoke-'
        gate_cells = {tuple(g['cell']) for g in self.gates}
        replace_ids, overlay_ids = tower_ids(st, rc)
        replace_ids = [i for i in replace_ids if i in self.meta]
        overlay_ids = [i for i in overlay_ids if i in self.meta]
        skip = self.replaced | gate_cells | self.no_tower
        towers = tower_cells(self.loop, self.dirs, skip, rng_for('towers', self.seed),
                             9 if self.scale == 'city' else 8)
        rng = rng_for('wallnodes', self.seed)
        orc_gates = gate_cells if rc == 'orc' else set()
        for x, y in self.loop:
            if (x, y) in self.replaced or (x, y) in orc_gates:
                continue
            ds = self.dirs[(x, y)]
            for d in ds:
                it = self.add_item(spoke + d, place_cells, x, y)
                if it:
                    it['key'] = self.spoke_key(self.meta[spoke + d], x, y, d)
                    self.wall_items.append(it)
            tower = (x, y) in towers
            if tower and replace_ids:
                ident = replace_ids[rng.randrange(len(replace_ids))]
            else:
                ident = node_id(st, rc, ds, prefer_alt=rng.random() < .12)
            it = self.add_item(ident, place_cells, x, y)
            if it:
                it['key'] = self.spoke_key(self.meta[ident], x, y, 'node')
            if tower and overlay_ids and not replace_ids:
                ov = overlay_ids[rng.randrange(len(overlay_ids))]
                self.add_item(ov, place_cells, x, y, .45)
            if tower:
                self.forts.append({'id': ident if replace_ids else overlay_ids[0] if overlay_ids
                                   else ident, 'kind': 'node_tower', 'cell': [x, y],
                                   'footprint': [1, 1], 'facility': 'watchtower',
                                   'replaces': [], 'passable': False})
        for ident in sorted(self.tile_missing):
            self.missing.append({'facility': 'city_wall', 'id': ident, 'reason': 'wall_asset'})
        self.tile_missing = set()
        self.draw_gates(False)

    def draw_walls(self):
        if not self.walled or not self.loop:
            return
        self.items.extend(self.fort_items)
        if self.shape == 'square':
            self.draw_square_wall()
        else:
            self.draw_spoke_wall()

    # -- ground underlay: base texture, yards, water, moat ---------------------------
    def base_variant(self, prefix, x, y):
        ids = sorted(i for i in self.meta if i.startswith(prefix) and i[len(prefix):].isdigit())
        if not ids:
            return None
        h = cell_hash(self.seed, x, y)
        # Half of the cells use the plain first variant, the rest spread over the others.
        return ids[0] if h % 2 == 0 or len(ids) == 1 else ids[1 + (h >> 1) % (len(ids) - 1)]

    def yard_cells(self):
        yard = set()
        for b in self.buildings + self.landmarks:
            if b.get('facility') is None and b in self.buildings:
                continue
            x, y = b['cell']
            fw, fd = b['footprint']
            for q in _ring(x, y, fw, fd):
                if q in self.interior and q not in self.loop_set and q not in self.water:
                    yard.add(q)
        if self.center and (self.scale in ('town', 'city')):
            x0, y0 = self.center
            yard |= {q for q in footprint_cells(x0 - 2, y0 - 2, 5, 5) if q in self.interior}
        return yard - self.taken

    def build_underlay(self):
        art = STYLE_ART[self.style]
        out = []
        if art['base']:
            for y in range(self.h):
                for x in range(self.w):
                    ident = self.base_variant(art['base'], x, y)
                    if ident:
                        it = place_cells(self.meta[ident], x, y)
                        it['layer'] = 'base'
                        out.append(it)
        self.yard = self.yard_cells()
        tiles, _ = dual_tiles(self.yard, art['yard'], self.meta)
        for it in tiles:
            it['layer'] = 'yard'
        out.extend(tiles)
        if self.water:
            prefix = art['quay'] if self.t.kind == 'sea' else art['bank']
            tiles, lost = dual_tiles(self.water, prefix, self.meta)
            for it in tiles:
                it['layer'] = 'water'
            out.extend(tiles)
            if lost:
                self.missing.append({'facility': None, 'id': prefix + '*', 'reason': 'water_asset'})
        out.extend(sorted(self.moat_items, key=lambda it: (it['pass'], it['key'], it['x'])))
        self.underlay = out

    # -- ground props ---------------------------------------------------------------
    def scatter_props(self):
        pools = prop_pools(self.rows, self.style, self.race)
        if not any(pools.values()):
            return
        rng = rng_for('props', self.seed)
        near_road = {q for c in self.roads for q in _n4(c)}
        blocked = self.roads | self.entrances | self.taken | self.water | self.loop_set
        blocked |= self.moat_cells | self.blocked
        # Keep the cell in front of every building entrance and gate clear as well.
        for g in self.gates:
            blocked |= set(_n4(tuple(g['cell'])))
        last = {}
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                q = (x, y)
                if q in blocked:
                    continue
                inside = q in self.interior
                zone = self.district_at(x, y) if inside else 'outskirts'
                if inside:
                    chance = .2 if q in self.yard else .3 if q in near_road else .42
                    pool = (pools['goods'] if zone in GOODS_ZONES and rng.random() < .65
                            else pools['green'])
                    if pools['race'] and rng.random() < .35:
                        pool = pools['race']
                else:
                    chance, pool = .12, pools['trees']
                if not pool or rng.random() > chance:
                    continue
                ident = None
                for _ in range(3):
                    m = pool[rng.randrange(len(pool))]
                    if last.get((x - 1, y)) != m['id'] and last.get((x, y - 1)) != m['id']:
                        ident = m['id']
                        break
                if not ident:
                    continue
                last[q] = ident
                self.items.append(place_cells(self.meta[ident], x, y))
                self.props.append({'id': ident, 'cell': [x, y],
                                   'race': self.meta[ident].get('race', 'common')})

    # -- assembly -------------------------------------------------------------------
    def road_prefix(self):
        kind = 'dirt-' if self.race in ('elf', 'orc') else 'stone-'
        return f'{self.style}-common-road-' + kind

    def build(self):
        self.setup_terrain()
        self.setup_wall()
        self.setup_roads()
        self.fortify()
        self.place_landmarks()
        self.side_streets()
        self.compute_parcels()
        self.draw_walls()
        self.place_facilities()
        self.fill_houses()
        self.build_underlay()
        self.scatter_props()
        ground, lost = dual_tiles(self.roads, self.road_prefix(), self.meta)
        for ident in lost:
            self.missing.append({'facility': None, 'id': ident, 'reason': 'tile_asset'})
        self.items.sort(key=lambda it: (it['key'], it['x']))
        for b in self.forts:
            b.setdefault('economy', _economy(self.meta.get(b['id'])))
        gates = [list(g['cell']) for g in self.gates]
        return {
            'grid': {'w': self.w, 'h': self.h, 'cell': CELL,
                     'roads': sorted(map(list, self.roads)),
                     'walls': sorted(map(list, self.loop_set)), 'gates': gates,
                     'water': sorted(map(list, self.water)), 'walled': self.walled,
                     'wall_shape': self.shape if self.walled else None,
                     'wall_loop': [list(c) for c in self.loop],
                     'interior': sorted(map(list, self.interior)),
                     'blocked': sorted(map(list, self.blocked)),
                     'moat': sorted(map(list, self.moat_cells)),
                     'yard': sorted(map(list, self.yard))},
            'terrain': self.t.summary(), 'fortification': self.level,
            'underlay': self.underlay, 'ground': ground, 'items': self.items,
            'buildings': self.buildings, 'landmarks': self.landmarks, 'forts': self.forts,
            'props': self.props, 'infrastructure': self.infrastructure,
            'parcels': self.parcels, 'missing': self.missing,
            'style': self.style, 'race': self.race}


from .town_layout_site import SITE_SIZE, site_layout  # noqa: E402,F401
