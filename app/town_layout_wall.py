"""Town wall outline: seeded orthogonal/45-degree polygons and their cell loops.

All geometry is in local cells. The polygon is built in a canonical frame where
the water side (if any) is south, then mapped to the world grid. Along the water
the wall follows the shore at a fixed gap; elsewhere it gets chamfers, notches
and dents so most seeds have concave corners.
"""
from .town_layout_art import DIR_OF, ORDER

ANGLE = {1: 45, 2: 90, 3: 135, 4: 180, 5: 135, 6: 90, 7: 45}


def _sign(v):
    return (v > 0) - (v < 0)


def simplify(points):
    """Drop repeated and collinear vertices of an 8-directional polygon."""
    pts = []
    for p in points:
        if not pts or pts[-1] != p:
            pts.append(p)
    while len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if ((_sign(b[0] - a[0]), _sign(b[1] - a[1]))
                    == (_sign(c[0] - b[0]), _sign(c[1] - b[1]))):
                pts.pop(i)
                changed = True
                break
    return pts


def raster(points):
    """Closed cell loop along the polygon; consecutive cells are 8-neighbours."""
    cells, n = [], len(points)
    for i in range(n):
        (ax, ay), (bx, by) = points[i], points[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        if dx and dy and abs(dx) != abs(dy):
            raise ValueError('wall edge is not orthogonal or 45 degrees')
        sx, sy = _sign(dx), _sign(dy)
        cells.extend((ax + sx * k, ay + sy * k) for k in range(max(abs(dx), abs(dy))))
    return cells


def valid_loop(cells):
    """Simple loop: unique cells, only loop neighbours touch (corner diagonals ok)."""
    n = len(cells)
    if n < 8 or len(set(cells)) != n:
        return False
    index = {c: i for i, c in enumerate(cells)}
    for i, (x, y) in enumerate(cells):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                j = index.get((x + dx, y + dy))
                if j is None or j == i:
                    continue
                gap = min((i - j) % n, (j - i) % n)
                if gap == 1 or (gap == 2 and dx and dy):
                    continue
                return False
    return True


def flood_inside(loop, w, h):
    """Cells enclosed by the loop (4-connected flood from outside the grid)."""
    wall, seen, stack = set(loop), set(), [(-1, -1)]
    while stack:
        p = stack.pop()
        if p in seen or p in wall or not (-1 <= p[0] <= w and -1 <= p[1] <= h):
            continue
        seen.add(p)
        x, y = p
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return {(x, y) for y in range(h) for x in range(w)} - seen - wall


def connected4(cells):
    cells = set(cells)
    if not cells:
        return True
    start = min(cells)
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q in cells and q not in seen:
                seen.add(q)
                stack.append(q)
    return seen == cells


def loop_dirs(loop):
    """cell -> (dir to previous cell, dir to next cell)."""
    n, out = len(loop), {}
    for i, (x, y) in enumerate(loop):
        (px, py), (nx, ny) = loop[i - 1], loop[(i + 1) % n]
        out[(x, y)] = (DIR_OF[(px - x, py - y)], DIR_OF[(nx - x, ny - y)])
    return out


def turn(dirs):
    """Angle in degrees between the two spokes of a wall cell (180 = straight)."""
    a, b = (ORDER.index(d) for d in dirs)
    return ANGLE[(b - a) % 8]


def convex(loop):
    """cell -> +1 convex / -1 concave / 0 straight for a clockwise (screen) loop."""
    n, out = len(loop), {}
    for i, (x, y) in enumerate(loop):
        (px, py), (nx, ny) = loop[i - 1], loop[(i + 1) % n]
        ax, ay, bx, by = x - px, y - py, nx - x, ny - y
        out[(x, y)] = _sign(ax * by - ay * bx)
    return out


def trace(boundary):
    """Order a one-cell-thick boundary clockwise, preferring orthogonal steps."""
    start = min(boundary, key=lambda p: (p[1], p[0]))
    steps = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))
    loop, seen, cur = [start], {start}, start
    while True:
        nxt = next(((cur[0] + dx, cur[1] + dy) for dx, dy in steps
                    if (cur[0] + dx, cur[1] + dy) in boundary
                    and (cur[0] + dx, cur[1] + dy) not in seen), None)
        if nxt is None:
            return loop
        loop.append(nxt)
        seen.add(nxt)
        cur = nxt


def close_region(region, w, h):
    """(loop, interior) when the region's 4-boundary is a clean wall loop, else None."""
    boundary = {(x, y) for x, y in region
                if any(q not in region for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))}
    if len(boundary) < 8:
        return None
    loop = trace(boundary)
    last, first = loop[-1], loop[0]
    if (len(loop) != len(boundary) or max(abs(last[0] - first[0]), abs(last[1] - first[1])) != 1
            or not valid_loop(loop)):
        return None
    interior = set(region) - boundary
    if len(interior) < 30 or not connected4(interior) or flood_inside(loop, w, h) != interior:
        return None
    return loop, interior


def _carve(rng, L, R, T, bottom, wet):
    """Canonical cells to remove from the base rectangle: chamfers, cuts, dents."""
    cut = set()
    width, height = R - L + 1, min(bottom[L:R + 1]) - T + 1
    corners = [(L, T, 1, 1), (R, T, -1, 1)]
    if not wet:
        corners += [(L, bottom[L], 1, -1), (R, bottom[R], -1, -1)]
    for cu, cv, su, sv in corners:
        roll = rng.random()
        if roll < .42:
            c = rng.randint(2, max(2, min(5, width // 5, height // 4)))
            cut |= {(cu + su * i, cv + sv * j) for i in range(c) for j in range(c) if i + j < c}
        elif roll < .78:
            a, b = rng.randint(3, max(3, width // 4)), rng.randint(3, max(3, height // 3))
            cut |= {(cu + su * i, cv + sv * j) for i in range(a) for j in range(b)}
    edges = [('h', T, 1, L, R), ('v', L, 1, T, None), ('v', R, -1, T, None)]
    if not wet:
        edges.append(('h', None, -1, L, R))
    for axis, fixed, inward, lo, hi in edges:
        if axis == 'v':
            hi = min(bottom[fixed], bottom[fixed]) if fixed is not None else hi
        for _ in range(rng.randint(0, 2)):
            k, d = rng.randint(4, 7), rng.randint(2, 3)
            if hi - lo - 12 - k < 0:
                continue
            start, trap = rng.randint(lo + 6, hi - 6 - k), rng.random() < .5
            for t in range(k):
                depth = min(d, t + 1, k - t) if trap else d
                for j in range(depth):
                    if axis == 'h':
                        u = start + t
                        v = (fixed if fixed is not None else bottom[u]) + inward * j
                        cut.add((u, v))
                    else:
                        cut.add((fixed + inward * j, start + t))
    return cut


def outline(terrain, margin, gap, shape, rng):
    """(loop, interior) of the town wall on the terrain grid.

    shape 'irregular' carves seeded features and follows the shoreline;
    'square' is the plain rectangle. Falls back to simpler shapes if a carving
    does not close into a clean loop.
    """
    from .town_layout_terrain import canonical
    w, h = terrain.w, terrain.h
    wet = bool(terrain.water) and terrain.side is not None
    U, V, world, _ = canonical(terrain.side if wet else 's', w, h)
    bottom = []
    for u in range(U):
        shore = next((v for v in range(V) if world(u, v) in terrain.water), None) if wet else None
        bottom.append(V - 1 - margin if shore is None else min(V - 1 - margin, shore - gap))
    L, R, T = margin, U - 1 - margin, margin
    flat = [min(bottom[L:R + 1])] * U
    plans = ([(bottom, True)] * 14 + [(bottom, False)] if shape == 'irregular' else []) + [(flat, False)]
    for low, carve in plans:
        cut = _carve(rng, L, R, T, low, wet) if carve else set()
        region = {world(u, v) for u in range(L, R + 1) for v in range(T, low[u] + 1)
                  if (u, v) not in cut}
        closed = close_region(region, w, h)
        if closed:
            return closed
    raise ValueError('town area too small for a wall')


# --- gates ---------------------------------------------------------------
AXIS = {frozenset(('e', 'w')): 'h', frozenset(('n', 's')): 'v'}


def straight_axis(dirs, cell):
    """'h' / 'v' when the wall cell is part of an orthogonal straight run."""
    return AXIS.get(frozenset(dirs.get(cell, ())))


def gate_candidates(loop, dirs, interior, region):
    """[(index, cell, axis, outward)] for cells on orthogonal straight runs.

    The gate cell and both loop neighbours must share the axis (so 3-cell gate
    houses fit), the inner neighbour must be interior and the outer one outside.
    """
    n, out = len(loop), []
    for i, (x, y) in enumerate(loop):
        axis = straight_axis(dirs, (x, y))
        if not axis or any(straight_axis(dirs, loop[(i + k) % n]) != axis for k in (-2, -1, 1, 2)):
            continue
        sides = (('n', (0, -1)), ('s', (0, 1))) if axis == 'h' else (('w', (-1, 0)), ('e', (1, 0)))
        for side, (dx, dy) in sides:
            inner = (x - dx, y - dy)
            if inner in interior and (x + dx, y + dy) not in region:
                out.append((i, (x, y), axis, side))
    return out


def choose_gates(cands, count, wet_side, rng, n):
    """Pick land gates on distinct sides (spread along the loop) plus a water gate."""
    def far(i, chosen):
        return all(min((i - j) % n, (j - i) % n) >= 6 for j, *_ in chosen)

    by_side = {}
    for c in cands:
        by_side.setdefault(c[3], []).append(c)
    chosen = []
    if wet_side and by_side.get(wet_side):
        row = by_side[wet_side]
        chosen.append(row[len(row) // 2 + rng.randint(-len(row) // 4, len(row) // 4)])
    sides = [s for s in ('s', 'n', 'e', 'w') if s != wet_side and by_side.get(s)]
    rng.shuffle(sides)
    sides.sort(key=lambda s: -len(by_side[s]))
    land = 0
    for rnd in range(2):
        for side in sides:
            if land >= count:
                break
            row = [c for c in by_side[side] if far(c[0], chosen)]
            if not row:
                continue
            mid = len(row) // 2 if rnd == 0 else rng.randrange(len(row))
            pick = row[max(0, min(len(row) - 1, mid + rng.randint(-len(row) // 5, len(row) // 5)))]
            chosen.append(pick)
            land += 1
    return chosen


# --- wall nodes ----------------------------------------------------------
def _east_open(spokes):
    m = 0
    for i in range(8):
        if not any(ORDER[(i + k) % 8] in spokes for k in (-1, 0, 1)):
            m |= 1 << i
    return m


EAST_OPEN = sorted({_east_open([d for i, d in enumerate(ORDER) if m & (1 << i)])
                    for m in range(1, 256)})


def east_node_id(spokes):
    """Port of east-fort/spoke.js nodeId(): 45 octagon variants by exposed edges."""
    k = EAST_OPEN.index(_east_open(spokes))
    return 'east-common-wallnode' + (f'-{k + 1:02d}' if k > 0 else '')


PASS = {frozenset(('e', 'w')): 'h', frozenset(('n', 's')): 'v',
        frozenset(('nw', 'se')): 'se', frozenset(('ne', 'sw')): 'ne'}


def node_id(style, race, spokes, prefer_alt=False):
    """Wall node symbol for one wall cell given its spoke directions."""
    key = frozenset(spokes)
    if style == 'east':
        return east_node_id(spokes)
    if style == 'arab':
        if key == frozenset(('e', 'w')):
            return 'arab-common-wallnode-01'
        return 'arab-common-wallnode-03' if key in PASS else 'arab-common-wallnode-02'
    if race != 'common':
        return f'west-{race}-wallnode-' + ('01' if key in PASS and not prefer_alt else '02')
    if key in PASS:
        return 'west-common-wallnode-pass-' + PASS[key]
    return 'west-common-wallnode-02' if prefer_alt else 'west-common-wallnode'


def tower_ids(style, race):
    """(corner tower ids that replace the node, overlay ids drawn above the node)."""
    if style == 'east':
        return [], ['east-common-cornertower-01']
    if style == 'arab':
        return [], ['arab-common-wall-tower']
    if race != 'common':
        return [f'west-{race}-walltower-01'], []
    return ['west-common-nodetower-round', 'west-common-nodetower-octagon'], []


def tower_cells(loop, dirs, skip, rng, spacing=9):
    """Corner cells (turns) get towers; long straight runs get one every ~spacing."""
    n, picked = len(loop), []

    def gap(i):
        return min((min((i - j) % n, (j - i) % n) for j in picked), default=99)

    corners = [i for i, c in enumerate(loop) if turn(dirs[c]) != 180 and c not in skip]
    for i in corners:
        if gap(i) >= 3:
            picked.append(i)
    for i, c in enumerate(loop):
        if c not in skip and gap(i) >= spacing + rng.randint(-1, 1):
            picked.append(i)
    return {loop[i] for i in picked}
