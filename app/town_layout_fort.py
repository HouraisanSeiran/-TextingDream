"""Fortifications on a spoke wall: bastions, ravelins, mamian, wengcheng, towers, moat.

Works on the wall loop produced by town_layout_wall; reads only metadata
(attach_cells / joins_spokes / arms / sort_offset) and never touches art files.
Every fort entry: {id, kind, cell, footprint, facility, replaces, passable}.
"""
from .town_layout_art import CELL, DIR_OF, DIRS8, footprint_cells, place, place_cells
from .town_layout_wall import close_region, turn

LEVELS = ('none', 'light', 'normal', 'heavy')
SIDE_STEP = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0)}


def plan_level(town_type, scale, walled, rng, override=None):
    """none / light / normal / heavy. Fortress types always, cities usually, villages never."""
    if not walled:
        return 'none'
    if override is not None:
        return override if override in LEVELS else 'normal'
    if town_type in ('pass_fortress', 'border_fortress'):
        return 'heavy'
    if scale == 'city' or town_type == 'city':
        return 'normal' if rng.random() < .75 else 'light'
    if scale == 'town':
        return 'light' if rng.random() < .45 else 'none'
    return 'none'


class Fortifier:
    def __init__(self, ctx):
        self.c = ctx
        self.n = len(ctx.loop)
        self.index = {cell: i for i, cell in enumerate(ctx.loop)}
        self.gate_idx = [g['index'] for g in ctx.gates]
        self.forts, self.items, self.moat, self.missing = [], [], [], []
        self.skip, self.occupied, self.nodes_taken = set(), set(), set()
        self.reserved, self.no_tower = set(), set()

    # -- helpers ---------------------------------------------------------
    def loop_gap(self, i, j):
        return min((i - j) % self.n, (j - i) % self.n)

    def near_gate(self, i, dist=3):
        return any(self.loop_gap(i, g) < dist for g in self.gate_idx)

    def free_out(self, cell):
        c = self.c
        x, y = cell
        return (0 <= x < c.w and 0 <= y < c.h and cell not in c.region and cell not in c.roads
                and cell not in c.water and cell not in c.blocked and cell not in self.occupied)

    def add(self, m, x, y, kind, replaces=(), passable=False, offset=None):
        fw, fd = m['footprint']
        off = m.get('sort_offset', .45) if offset is None else offset
        self.items.append(place_cells(m, x, y, off))
        self.forts.append({'id': m['id'], 'kind': kind, 'cell': [x, y], 'footprint': [fw, fd],
                           'facility': m.get('facility'), 'replaces': sorted(map(list, replaces)),
                           'passable': passable})
        cells = footprint_cells(x, y, fw, fd)
        self.occupied |= cells - self.c.region
        self.skip |= set(replaces)
        return cells

    def straight_runs(self, axis_ok=('h', 'v')):
        """Loop indices on orthogonal straight cells with their outward side."""
        out = []
        for i, (x, y) in enumerate(self.c.loop):
            dirs = frozenset(self.c.dirs[(x, y)])
            axis = 'h' if dirs == {'e', 'w'} else 'v' if dirs == {'n', 's'} else None
            if axis not in axis_ok or self.near_gate(i) or (x, y) in self.skip:
                continue
            sides = ('n', 's') if axis == 'h' else ('e', 'w')
            for side in sides:
                dx, dy = SIDE_STEP[side]
                if (x - dx, y - dy) in self.c.interior and (x + dx, y + dy) not in self.c.region:
                    out.append((i, (x, y), axis, side))
        return out

    def spaced(self, cands, count, spacing):
        rng, picked = self.c.rng, []
        cands = list(cands)
        rng.shuffle(cands)
        for cand in cands:
            if len(picked) >= count:
                break
            if all(self.loop_gap(cand[0], p[0]) >= spacing for p in picked):
                picked.append(cand)
        return picked

    def budget(self, light, normal, heavy):
        return {'light': light, 'normal': normal, 'heavy': heavy}.get(self.c.level, 0)

    # -- outward helpers -------------------------------------------------
    def outward(self, cell):
        """Outward perpendicular direction of a straight wall cell (orth or diagonal)."""
        dirs = frozenset(self.c.dirs[cell])
        perp = {frozenset(('e', 'w')): ('n', 's'), frozenset(('n', 's')): ('e', 'w'),
                frozenset(('nw', 'se')): ('ne', 'sw'), frozenset(('ne', 'sw')): ('nw', 'se')}
        x, y = cell
        for d in perp.get(dirs, ()):
            dx, dy = DIRS8[d]
            if (x + dx, y + dy) not in self.c.region and (x - dx, y - dy) in self.c.interior:
                return d
        return None

    def ahead(self, cell, d, fw, fd):
        """Top-left of a fw x fd footprint just outside cell in direction d."""
        dx, dy = DIRS8[d]
        x, y = cell[0] + dx, cell[1] + dy
        return x - (fw - 1 if dx < 0 else 0), y - (fd - 1 if dy < 0 else 0)

    def meta(self, ident):
        return self.c.meta.get(ident)

    # -- west common bastions: centred on convex 90-degree corners ----------
    def west_bastions(self, count):
        by_arms = {frozenset(m['arms']): m for m in self.c.rows
                   if m['id'].startswith('west-common-bastion-') and m.get('arms')}
        cands = []
        for i, cell in enumerate(self.c.loop):
            m = by_arms.get(frozenset(self.c.dirs[cell]))
            if (not m or self.near_gate(i, 4) or cell in self.skip
                    or self.c.convex.get(cell, 0) <= 0):
                continue
            fp = footprint_cells(cell[0] - 1, cell[1] - 1, 3, 3)
            if all(q in self.c.loop_set or (q in self.c.interior and q in self.c.buildable
                                            and q not in self.c.roads)
                   or self.free_out(q) for q in fp):
                cands.append((i, cell, m))
        for i, cell, m in self.spaced(cands, count, 5):
            cells = self.add(m, cell[0] - 1, cell[1] - 1, 'bastion')
            self.reserved |= cells & self.c.interior
            self.no_tower.add(cell)

    # -- elf / dwarf bastions replacing wall cells (attach_cells, joins_spokes)
    def racial_bastions(self, prefix, count):
        metas = [m for m in self.c.rows if m['id'].startswith(prefix) and m.get('attach_cells')]
        cands = []
        for i in range(self.n):
            for m in metas:
                attach = [tuple(a) for a in m['attach_cells']]
                joins = frozenset(m.get('joins_spokes', ()))
                run = [self.c.loop[(i + t) % self.n] for t in range(len(attach))]
                if any(frozenset(self.c.dirs[c]) != joins or c in self.skip for c in run):
                    continue
                if any(self.near_gate((i + t) % self.n, 3) for t in range(len(attach))):
                    continue
                tx = min(c[0] for c in run) - min(a[0] for a in attach)
                ty = min(c[1] for c in run) - min(a[1] for a in attach)
                if {(tx + a, ty + b) for a, b in attach} != set(run):
                    continue
                fw, fd = m['footprint']
                rest = footprint_cells(tx, ty, fw, fd) - set(run)
                if rest and all(self.free_out(q) for q in rest):
                    cands.append((i, (tx, ty), m, run))
        for i, (tx, ty), m, run in self.spaced(cands, count, 6):
            if any(c in self.skip for c in run):
                continue
            self.add(m, tx, ty, 'bastion', replaces=run)
            self.no_tower |= set(run)

    # -- outworks attached to straight wall cells ---------------------------
    def attached(self, ids, count, spacing, kind, orth_only=True):
        """ids: dir -> meta id. Footprint goes just outside the wall cell."""
        cands = []
        for i, cell in enumerate(self.c.loop):
            if self.near_gate(i, 3) or cell in self.skip:
                continue
            d = self.outward(cell)
            if d is None or (orth_only and len(d) > 1) or d not in ids:
                continue
            m = self.meta(ids[d])
            if not m:
                continue
            fw, fd = m['footprint']
            if kind == 'mamian' and d == 'n' and fd == 2:      # front cell is the wall cell
                tl, need = (cell[0], cell[1] - 1), {(cell[0], cell[1] - 1)}
            else:
                tl = self.ahead(cell, d, fw, fd)
                need = footprint_cells(tl[0], tl[1], fw, fd)
            if all(self.free_out(q) for q in need):
                cands.append((i, cell, m, tl))
        for i, cell, m, tl in self.spaced(cands, count, spacing):
            if all(self.free_out(q) for q in footprint_cells(*tl, *m['footprint'])
                   if q not in self.c.loop_set):
                self.add(m, tl[0], tl[1], kind)
                self.no_tower.add(cell)

    def wall_overlays(self, ids, count, spacing):
        """East enemy towers / arrow towers sitting on straight wall nodes."""
        metas = [self.meta(i) for i in ids if self.meta(i)]
        if not metas:
            return
        cands = [(i, c) for i, c in enumerate(self.c.loop) if not self.near_gate(i, 3)
                 and c not in self.skip and c not in self.no_tower
                 and turn(self.c.dirs[c]) == 180]
        for k, (i, (x, y)) in enumerate(self.spaced(cands, count, spacing)):
            m = metas[k % len(metas)]
            self.items.append(place_cells(m, x, y, .45))
            self.forts.append({'id': m['id'], 'kind': 'wall_tower', 'cell': [x, y],
                               'footprint': list(m['footprint']), 'facility': m.get('facility'),
                               'replaces': [], 'passable': False})
            self.no_tower.add((x, y))

    # -- gate outworks: ravelins (west) and wengcheng / moon forts (east) -------
    def gate_outworks(self, make, count, kind):
        """make(gate) -> [(meta, top_left, passable)]; the first option that fits wins."""
        gates = list(self.c.gates)
        self.c.rng.shuffle(gates)
        done = 0
        for g in gates:
            if done >= count:
                break
            for m, tl, passable in make(g):
                if not m:
                    continue
                cells = footprint_cells(tl[0], tl[1], *m['footprint'])
                if all((passable and q in self.c.roads and q not in self.c.region)
                       or self.free_out(q) for q in cells):
                    self.add(m, tl[0], tl[1], kind, passable=passable)
                    done += 1
                    break

    def ravelin_options(self, g):
        (gx, gy), side = g['cell'], g['side']
        ox, oy = SIDE_STEP[side]
        lx, ly = (1, 0) if side in ('n', 's') else (0, 1)
        m = self.meta('west-common-ravelin-' + side)
        out = []
        for dist in (2, 3):
            for lat in (1, -2):
                x, y = gx + ox * dist + lx * lat, gy + oy * dist + ly * lat
                out.append((m, (x - (1 if ox < 0 else 0), y - (1 if oy < 0 else 0)), False))
        return out

    def wengcheng_options(self, g):
        (gx, gy), side = g['cell'], g['side']
        tl = {'s': (gx - 1, gy + 1), 'n': (gx - 1, gy - 2),
              'e': (gx + 1, gy - 1), 'w': (gx - 2, gy - 1)}[side]
        forms = ['square', 'moon']
        self.c.rng.shuffle(forms)
        return [(self.meta(f'east-common-wengcheng-{f}-{side}'), tl, True) for f in forms]

    # -- moat: a spoke ring one cell outside wall + outworks --------------------
    def build_moat(self):
        c = self.c
        base = set(c.region) | self.occupied
        grown = {(x + dx, y + dy) for x, y in base for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        if any(not (0 <= x < c.w and 0 <= y < c.h) for x, y in grown):
            return
        closed = close_region(grown, c.w, c.h)
        if not closed:
            return
        ring = closed[0]
        near_water = {(x + dx, y + dy) for x, y in c.water
                      for dx in range(-3, 4) for dy in range(-3, 4)}
        keep = {q for q in ring if q not in near_water and q not in c.roads
                and q not in self.occupied and q not in c.blocked}
        n = len(ring)
        spokes = {}
        for i, q in enumerate(ring):
            if q not in keep:
                continue
            ds = [DIR_OF[(r[0] - q[0], r[1] - q[1])] for r in (ring[i - 1], ring[(i + 1) % n])
                  if r in keep]
            if ds:
                spokes[q] = ds
        if c.style == 'east':
            passes = [('east-common-moatbank-', 'east-common-moatbank-node'),
                      ('east-common-moatspoke-', 'east-common-moatnode')]
        else:
            passes = [('west-common-moatspoke-', None)]
        need = [p + d for p, _ in passes for d in DIRS8] + [nd for _, nd in passes if nd]
        if any(i not in c.meta for i in need) or not spokes:
            self.missing.append({'facility': None, 'id': passes[0][0] + '*', 'reason': 'moat_asset'})
            return
        cells = sorted(spokes, key=lambda p: (p[1], p[0]))
        for step, (prefix, node) in enumerate(passes):
            for x, y in cells:
                ds = spokes[(x, y)]
                for d in ds:
                    it = place_cells(c.meta[prefix + d], x, y)
                    it['layer'], it['pass'] = 'moat', step
                    self.moat.append(it)
                ident = node or self._west_moat_node(ds)
                it = place_cells(c.meta[ident], x, y)
                it['layer'], it['pass'] = 'moat', step
                self.moat.append(it)
        self.occupied |= set(spokes)
        self.moat_cells = sorted(map(list, cells))
        self.forts.append({'id': passes[-1][0] + '*', 'kind': 'moat', 'cell': list(cells[0]),
                           'footprint': [1, 1], 'facility': None, 'replaces': [],
                           'passable': False, 'cells': len(cells)})

    def _west_moat_node(self, ds):
        key = frozenset(ds)
        name = {frozenset(('e', 'w')): 'h', frozenset(('n', 's')): 'v',
                frozenset(('nw', 'se')): 'se', frozenset(('ne', 'sw')): 'ne'}.get(key)
        ident = 'west-common-moatnode-pass-' + name if name else 'west-common-moatnode'
        return ident if ident in self.c.meta else 'west-common-moatnode'

    # -- entry -------------------------------------------------------------
    def run(self):
        c, level = self.c, self.c.level
        self.moat_cells = []
        if level == 'none' or not c.loop:
            return self
        st, rc = c.style, c.race
        if st == 'west' and rc == 'common':
            self.west_bastions(self.budget(1, 3, 6))
            self.gate_outworks(self.ravelin_options, self.budget(0, 1, 4), 'ravelin')
        elif st == 'west' and rc in ('elf', 'dwarf'):
            prefix = 'west-elf-thornbastion-' if rc == 'elf' else 'west-dwarf-bastion-'
            self.racial_bastions(prefix, self.budget(1, 2, 4))
        elif st == 'west' and rc == 'orc':
            self.attached({d: 'west-orc-earthwork-' + d for d in DIRS8},
                          self.budget(1, 3, 5), 5, 'earthwork', orth_only=False)
        elif st == 'east':
            self.attached({d: 'east-common-mamian-' + d for d in 'nsew'},
                          self.budget(2, 4, 7), 5, 'mamian')
            self.gate_outworks(self.wengcheng_options, self.budget(0, 1, 4), 'wengcheng')
            self.wall_overlays(['east-common-dilou-01', 'east-common-jianlou-01'],
                               self.budget(1, 2, 4), 6)
        elif st == 'arab':
            # arab-base has no bastions / outworks; only the shared moat applies.
            self.missing.append({'facility': None, 'id': 'arab-common-fort-*',
                                 'reason': 'fort_asset',
                                 'note': '阿拉伯风格没有棱堡/外堡素材，只加护城河（借用西式护城河辐条，水色同 west-ground）'})
        if rc != 'orc' and (level == 'heavy' or (level == 'normal' and c.rng.random() < .5)):
            self.build_moat()
        return self


def gate_item(m, cell, axis, orc, base_key=None):
    """Gate overlay item; orc gates are dual-grid replacement tiles (old convention)."""
    gx, gy = cell
    if orc:
        i, j = gx + 1, (gy if axis == 'h' else gy + 1)
        it = {'id': m['id'], 'x': i * CELL - 24 - m['viewBox'][0],
              'bottom': j * CELL + 24, 'key': j * CELL + 24, 'tile': [i, j]}
        return it
    front = (gy + 1) * CELL
    return place(m, gx * CELL + 24, front, front + 24.5 if base_key is None else base_key)
