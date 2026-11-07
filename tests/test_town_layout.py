"""Independent fixtures: no database, world state or application service."""
from collections import deque
import copy
import unittest

from app.town_layout import DISTRICT_ZONES, layout, load_catalog, site_layout

COMBINATIONS = [('west', r) for r in ('common', 'elf', 'dwarf', 'orc')] + [('east', 'common')]
FACILITIES = ('town_hall lord_hall market_hall granary cistern well mill forge smelter '
              'kiln tannery barracks watchtower city_wall gate temple academy infirmary '
              'inn caravanserai stable dock warehouse mine_head boiler_house ward_tower '
              'cemetery bridge').split()


def fixture(scale='city', town_type='port'):
    return {'town_id': 'layout_fixture',
            'skeleton': {'scale': scale, 'town_type': town_type, 'water': {'source': 'river'}},
            'built': {'districts': [{'id': k, 'kind': k, 'roof': 'gable_thatch'}
                                    for k in DISTRICT_ZONES],
                      'style': {'roof': 'gable_tile'},
                      'facilities': [{'id': 'f_' + k, 'kind': k} for k in FACILITIES]}}


class TownLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.meta = {m['id']: m for m in cls.catalog['meta']}

    def test_deterministic_and_input_unchanged(self):
        town = fixture()
        original = copy.deepcopy(town)
        a = layout(town, seed='example', catalog=self.catalog)
        self.assertEqual(a, layout(town, seed='example', catalog=self.catalog))
        self.assertNotEqual(a, layout(town, seed='different', catalog=self.catalog))
        self.assertEqual(town, original)
        self.assertEqual(layout(town), layout(town))

    def test_all_combinations_and_invariants(self):
        for style, race in COMBINATIONS:
            for scale in ('village', 'town', 'city'):
                with self.subTest(style=style, race=race, scale=scale):
                    plan = layout(fixture(scale), style, race, seed=7, catalog=self.catalog)
                    g = plan['grid']
                    roads, walls = set(map(tuple, g['roads'])), set(map(tuple, g['walls']))
                    used, owners = set(), {}
                    for b in plan['buildings']:
                        x, y = b['cell']
                        w, d = b['footprint']
                        cells = {(xx, yy) for yy in range(y, y + d) for xx in range(x, x + w)}
                        self.assertFalse(cells & (used | roads | walls))
                        self.assertEqual(b['footprint'], self.meta[b['id']]['footprint'])
                        if g['walled']:
                            self.assertTrue(x >= 2 and y >= 2)
                            self.assertTrue(x + w <= g['w'] - 2 and y + d <= g['h'] - 2)
                        used |= cells
                        for cell in cells:
                            owners[cell] = b
                    for (x, y), b in owners.items():
                        if b['facility'] is None:
                            for p in ((x + 1, y), (x, y + 1)):
                                other = owners.get(p)
                                if other and other is not b and other['facility'] is None:
                                    self.assertNotEqual(b['id'], other['id'])
                    accounted = [b['source'] for b in plan['buildings'] if b['facility']]
                    accounted += [b['source'] for b in plan['infrastructure'] if 'source' in b]
                    accounted += [b['source'] for b in plan['missing'] if 'source' in b]
                    self.assertCountEqual(accounted, ['f_' + k for k in FACILITIES])
                    seen, queue = set(), deque([next(iter(roads))])
                    while queue:
                        p = queue.popleft()
                        if p in seen:
                            continue
                        seen.add(p)
                        x, y = p
                        queue.extend(q for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                                     if q in roads and q not in seen)
                    self.assertEqual(seen, roads)
                    self.assertTrue(set(map(tuple, g['gates'])) <= seen)
                    for it in plan['ground'] + plan['items']:
                        self.assertIn(it['id'], self.meta)
                    self.assertEqual(plan['items'], sorted(plan['items'], key=lambda i: (i['key'], i['x'])))
                    for it in plan['ground']:
                        i, j = it['tile']
                        mask = sum(bit for dx, dy, bit in ((-1, -1, 8), (0, -1, 4),
                                                           (-1, 0, 2), (0, 0, 1))
                                   if (i + dx, j + dy) in roads)
                        self.assertTrue(it['id'].endswith(format(mask, '04b')))

    def test_missing_assets_and_no_water(self):
        plan = layout(fixture(), catalog={'meta': []})
        self.assertEqual(len([m for m in plan['missing'] if 'source' in m]), len(FACILITIES))
        town = fixture()
        town['skeleton'].update(town_type='town', water={'source': 'none'})
        plan = layout(town)
        self.assertEqual({m['facility'] for m in plan['missing'] if m['reason'] == 'no_water'},
                         {'dock', 'bridge'})

    def test_defaults_and_east_race(self):
        self.assertTrue(layout({})['buildings'])
        self.assertEqual(layout({}, 'east', 'elf'), layout({}, 'east', 'common'))
        with self.assertRaises(ValueError):
            layout({}, style='invalid')


    def test_gate_conventions_and_racial_fallback(self):
        for style, race in COMBINATIONS:
            with self.subTest(style=style, race=race):
                plan = layout(fixture(), style, race, catalog=self.catalog)
                gates = [i for i in plan['infrastructure'] if 'cell' in i]
                for gate in gates:
                    gx, gy = gate['cell']
                    it = next(i for i in plan['items'] if i['id'] == gate['id'] and
                              (i.get('tile') == [gx + 1, gy if gate['id'].endswith('-h') else gy + 1]
                               if race == 'orc' else i['bottom'] == (gy + 1) * 48))
                    if race == 'orc':
                        self.assertEqual(it['key'], it['bottom'])
                    else:
                        self.assertEqual(it['key'], (gy + 1) * 48 + 24.5)
                        if style == 'east' and gate['id'].endswith('-h'):
                            self.assertEqual(it['x'], gx * 48 - 48)
                if race in ('elf', 'dwarf', 'orc'):
                    forge = next(b for b in plan['buildings'] if b['facility'] == 'forge')
                    academy = next(b for b in plan['buildings'] if b['facility'] == 'academy')
                    self.assertEqual(self.meta[forge['id']]['race'], race)
                    self.assertEqual(self.meta[academy['id']]['race'], 'common')

    def test_water_placement_and_roof_preference(self):
        for style, race in COMBINATIONS:
            plan = layout(fixture(), style, race, catalog=self.catalog)
            water = set(map(tuple, plan['grid']['water']))
            for b in plan['buildings']:
                x, y = b['cell']
                fw, fd = b['footprint']
                if b['facility'] == 'bridge':
                    self.assertIn((x, y + 1), water)
                    self.assertEqual([fw, fd], [1, 3])
                if b['facility'] == 'dock':
                    self.assertTrue(any((xx, y + fd) in water for xx in range(x, x + fw)))
        houses = [m for m in self.catalog['meta'] if m['id'].startswith('west-common-house-01-')]
        other = next(m for m in self.catalog['meta']
                     if m['category'] == 'house' and m['race'] == 'common' and m['roof'] == 'steep_slate')
        plan = layout({'style': {'roof': 'gable_thatch'}}, catalog=houses + [other])
        self.assertTrue(plan['buildings'])
        self.assertTrue(all(self.meta[b['id']]['roof'] == 'gable_thatch' for b in plan['buildings']))


STYLES = ('west', 'east', 'arab')
RACES = ('common', 'human', 'elf', 'dwarf', 'orc')
DIAG = {'ne', 'se', 'sw', 'nw'}
STEP = {'n': (0, -1), 'ne': (1, -1), 'e': (1, 0), 'se': (1, 1),
        's': (0, 1), 'sw': (-1, 1), 'w': (-1, 0), 'nw': (-1, -1)}


def mask(cells, i, j):
    return sum(bit for dx, dy, bit in ((-1, -1, 8), (0, -1, 4), (-1, 0, 2), (0, 0, 1))
               if (i + dx, j + dy) in cells)


def connected(cells):
    cells = set(cells)
    if not cells:
        return True
    start = min(cells)
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q in cells and q not in seen:
                seen.add(q)
                queue.append(q)
    return seen == cells


def cells_of(b):
    x, y = b['cell']
    w, d = b['footprint']
    return {(xx, yy) for yy in range(y, y + d) for xx in range(x, x + w)}


class TownLayoutV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.meta = {m['id']: m for m in cls.catalog['meta']}
        cls.plans = {}
        for style in STYLES:
            for race in RACES:
                for scale, kind in (('city', 'city'), ('small_town', 'border_fortress'),
                                    ('town', 'port')):
                    cls.plans[style, race, scale] = layout(
                        fixture(scale, kind), style, race, seed=11, catalog=cls.catalog)

    def each(self):
        # No subTest here: a failing assert inside a generator-held subTest is swallowed.
        yield from self.plans.items()

    def test_v2_deterministic_with_new_options(self):
        town = fixture('city', 'city')
        a = layout(town, 'east', seed='v2', catalog=self.catalog, wall_shape='irregular')
        self.assertEqual(a, layout(town, 'east', seed='v2', catalog=self.catalog))
        self.assertNotEqual(a['grid']['wall_loop'],
                            layout(town, 'east', seed='v3', catalog=self.catalog)['grid']['wall_loop'])

    def test_irregular_wall_closed_connected_and_shaped(self):
        diagonal = concave = 0
        for _, plan in self.each():
            g = plan['grid']
            loop = [tuple(c) for c in g['wall_loop']]
            self.assertTrue(g['walled'])
            self.assertEqual(len(loop), len(set(loop)))
            for a, b in zip(loop, loop[1:] + loop[:1]):
                self.assertEqual(max(abs(a[0] - b[0]), abs(a[1] - b[1])), 1)
            self.assertTrue(connected(map(tuple, g['interior'])))
            self.assertFalse(set(loop) & set(map(tuple, g['water'])))
            n = len(loop)
            for i, (x, y) in enumerate(loop):
                (px, py), (nx, ny) = loop[i - 1], loop[(i + 1) % n]
                if abs(nx - x) + abs(ny - y) == 2:
                    diagonal += 1
                if (x - px) * (ny - y) - (y - py) * (nx - x) < 0:
                    concave += 1
        self.assertGreater(diagonal, 0)
        self.assertGreater(concave, 0)

    def test_gates_on_orthogonal_straight_runs(self):
        for _, plan in self.each():
            loop = [tuple(c) for c in plan['grid']['wall_loop']]
            index = {c: i for i, c in enumerate(loop)}
            gates = [i for i in plan['infrastructure'] if 'cell' in i]
            self.assertTrue(gates)
            for gate in gates:
                i = index[tuple(gate['cell'])]
                prev, nxt = loop[i - 1], loop[(i + 1) % len(loop)]
                x, y = gate['cell']
                if gate['axis'] == 'h':
                    self.assertEqual({prev[1], nxt[1]}, {y})
                    self.assertEqual({prev[0], nxt[0]}, {x - 1, x + 1})
                else:
                    self.assertEqual({prev[0], nxt[0]}, {x})
                    self.assertEqual({prev[1], nxt[1]}, {y - 1, y + 1})
                self.assertIn(tuple(gate['cell']), set(map(tuple, plan['grid']['roads'])))

    def test_lots_do_not_overlap_walls_roads_and_stay_inside(self):
        outside_ok = {'dock', 'bridge'}
        for _, plan in self.each():
            g = plan['grid']
            roads, walls = set(map(tuple, g['roads'])), set(map(tuple, g['walls']))
            interior = set(map(tuple, g['interior']))
            used = set()
            for b in plan['buildings'] + plan['landmarks']:
                cells = cells_of(b)
                self.assertFalse(cells & used, b['id'])
                self.assertFalse(cells & (roads | walls), b['id'])
                if b.get('facility') not in outside_ok:
                    self.assertLessEqual(cells, interior, b['id'])
                used |= cells
                self.assertEqual(b['footprint'], self.meta[b['id']]['footprint'])
                self.assertIn('economy', b)
            for p in plan['props']:
                self.assertNotIn(tuple(p['cell']), roads | walls | used)

    def test_road_network_connected(self):
        for _, plan in self.each():
            roads = set(map(tuple, plan['grid']['roads']))
            self.assertTrue(connected(roads))
            self.assertLessEqual(set(map(tuple, plan['grid']['gates'])), roads)

    def test_water_tiles_encode_water_cells(self):
        seen = 0
        for _, plan in self.each():
            water = set(map(tuple, plan['grid']['water']))
            for it in plan['underlay']:
                if it.get('layer') != 'water':
                    continue
                seen += 1
                self.assertTrue(it['id'].endswith(format(mask(water, *it['tile']), '04b')))
                self.assertEqual(self.meta[it['id']]['category'], 'water')
            if water:
                kind = plan['terrain']['water_kind']
                ids = [it['id'] for it in plan['underlay'] if it.get('layer') == 'water']
                if plan['style'] != 'arab':
                    self.assertTrue(all(('-quay-' if kind == 'sea' else '-bank-') in i for i in ids))
        self.assertGreater(seen, 0)

    def test_variant_pool_neighbours_differ(self):
        multi = 0
        for _, plan in self.each():
            owner = {}
            for b in plan['buildings']:
                for c in cells_of(b):
                    owner[c] = b
            for b in plan['buildings']:
                if not b['facility']:
                    continue
                multi += b['variants'] > 1
                x, y = b['cell']
                w, d = b['footprint']
                ring = {(xx, yy) for yy in range(y - 1, y + d + 1)
                        for xx in range(x - 1, x + w + 1)} - cells_of(b)
                for q in ring:
                    o = owner.get(q)
                    if o is not None and o is not b and o['facility'] == b['facility']:
                        self.assertNotEqual(o['id'], b['id'])
        self.assertGreater(multi, 0)

    def test_landmarks_in_bounds_and_cultural(self):
        count = 0
        for (style, _, _), plan in self.each():
            g = plan['grid']
            for lm in plan['landmarks']:
                count += 1
                x, y = lm['cell']
                w, d = lm['footprint']
                self.assertTrue(0 <= x and 0 <= y and x + w <= g['w'] and y + d <= g['h'])
                self.assertEqual(self.meta[lm['id']]['style'], style)
                self.assertEqual(self.meta[lm['id']]['category'], 'landmark')
            self.assertLessEqual(len(plan['landmarks']), 2)
        self.assertGreater(count, 0)

    def test_styles_races_and_fortification_levels(self):
        for (style, race, scale), plan in self.each():
            expect = race if style == 'west' and race != 'human' else 'common'
            self.assertEqual(plan['race'], expect)
            for it in plan['underlay'] + plan['ground'] + plan['items']:
                self.assertIn(it['id'], self.meta)
            if scale == 'small_town':     # border_fortress always fortified
                self.assertEqual(plan['fortification'], 'heavy', (style, race))
                self.assertTrue([f for f in plan['forts'] if f['kind'] != 'node_tower'],
                                (style, race))
        village = layout(fixture('village', 'village'), seed=3, catalog=self.catalog)
        self.assertEqual(village['fortification'], 'none')
        self.assertFalse([f for f in village['forts'] if f['kind'] != 'node_tower'])
        notes = [m for m in self.plans['west', 'elf', 'city']['missing']
                 if m['reason'] == 'racial_fallback']
        self.assertTrue(notes and all(m['note'] for m in notes))
        with self.assertRaises(ValueError):
            layout({}, wall_shape='round')

    def test_square_wall_option(self):
        plan = layout(fixture('city', 'city'), seed=4, catalog=self.catalog, wall_shape='square')
        walls = set(map(tuple, plan['grid']['walls']))
        xs, ys = [x for x, _ in walls], [y for _, y in walls]
        self.assertEqual(walls, {(x, y) for x in range(min(xs), max(xs) + 1)
                                 for y in range(min(ys), max(ys) + 1)
                                 if x in (min(xs), max(xs)) or y in (min(ys), max(ys))})
        self.assertTrue(any('-wall-1' in it['id'] or '-wall-0' in it['id'] for it in plan['items']))

    def test_terrain_parameter_is_used(self):
        water = [[x, y] for x in range(30) for y in (19, 20, 21)]
        blocked = [[10, 8], [11, 8]]
        terrain = {'water': water, 'water_kind': 'lake', 'blocked': blocked, 'source': 'test'}
        plan = layout(fixture('town', 'town'), seed=5, catalog=self.catalog, terrain=terrain)
        self.assertEqual(plan['terrain']['source'], 'test')
        self.assertEqual(set(map(tuple, plan['grid']['water'])), set(map(tuple, water)))
        used = set().union(*(cells_of(b) for b in plan['buildings'])) if plan['buildings'] else set()
        self.assertFalse(used & {(10, 8), (11, 8)})
        self.assertFalse(set(map(tuple, plan['grid']['walls'])) & set(map(tuple, water)))
        called = []

        def source(w, h, seed, skeleton):
            called.append((w, h))
            return {'source': 'callable'}
        plan = layout(fixture('town', 'town'), seed=5, catalog=self.catalog, terrain=source)
        self.assertTrue(called)
        self.assertEqual(plan['terrain']['source'], 'callable')
        self.assertFalse(plan['grid']['water'])

    def test_site_layout_every_resource(self):
        resources = sorted({m['resource'] for m in self.catalog['meta']
                            if m.get('category') == 'site' and m.get('resource')})
        self.assertTrue(resources)
        for res in resources:
            for style in STYLES:
                with self.subTest(resource=res, style=style):
                    s = site_layout(res, style, seed=2, catalog=self.catalog)
                    self.assertEqual(len(s['buildings']), 1)
                    self.assertGreaterEqual(s['grid']['w'], 10)
                    self.assertGreaterEqual(s['grid']['h'], 8)
                    roads = set(map(tuple, s['grid']['roads']))
                    self.assertTrue(connected(roads))
                    w, h = s['grid']['w'], s['grid']['h']
                    self.assertTrue(any(x in (0, w - 1) or y in (0, h - 1) for x, y in roads))
                    self.assertEqual(self.meta[s['buildings'][0]['id']]['resource'], res)
                    self.assertFalse(cells_of(s['buildings'][0]) & roads)
        subs = [m for m in self.catalog['meta'] if m.get('category') == 'site' and m.get('subtype')]
        m = subs[0]
        s = site_layout(m['resource'], m['style'], subtype=m['subtype'], seed=1, catalog=self.catalog)
        self.assertEqual(self.meta[s['buildings'][0]['id']]['subtype'], m['subtype'])
        self.assertEqual(site_layout(m, seed=1, catalog=self.catalog)['buildings'][0]['id'], m['id'])


if __name__ == '__main__':
    unittest.main()
