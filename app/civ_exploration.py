"""Playable districts and travel compiled from a pinned civ snapshot.

World roads follow the upstream cell chains, including their build/abandon dates.
Town plans are deterministic fictional street layouts, not extra terrain resolution.
All movement uses Runtime.move and the existing adventure route/time rules.
"""
import hashlib
import heapq
import math
import random

from . import play_map

VERSION = 1
TOWN_LIMIT = 8
SPEED = {'road': 5, 'trail': 3, 'sea': 12}  # gameplay km per elapsed hour


def distance(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742.0176 * math.asin(min(1, math.sqrt(h)))


def live_routes(civ, year):
    source = next((era for era in civ.get('eras', []) if year < era['until']), civ)
    return [r for r in source.get('routes', [])
            if r.get('kind') in SPEED and r.get('built', math.inf) <= year
            and year < r.get('abandoned', math.inf)]


def road_graph(civ, world, year):
    graph = {}
    for route in live_routes(civ, year):
        cells = route.get('cells', [])
        if any(type(c) is not int or not 0 <= c < world.cells for c in cells):
            raise ValueError('原件道路含越界地块，不能生成旅行路线')
        for a, b in zip(cells, cells[1:]):
            if a == b:
                continue
            km = distance((world.lon[a], world.lat[a]), (world.lon[b], world.lat[b]))
            edge = (km / SPEED[route['kind']], km, route['kind'])
            for x, y in ((a, b), (b, a)):
                old = graph.setdefault(x, {}).get(y)
                if old is None or edge[0] < old[0]:
                    graph[x][y] = edge
    return graph


def shortest(graph, origin, stops=None):
    costs, previous = {origin: 0}, {}
    queue = [(0, origin)]
    while queue:
        cost, cell = heapq.heappop(queue)
        if cost != costs[cell]:
            continue
        if stops and cell != origin and cell in stops:
            continue  # A town is a destination, never silently walked through.
        for other, edge in sorted(graph.get(cell, {}).items()):
            candidate = cost + edge[0]
            if candidate < costs.get(other, math.inf):
                costs[other], previous[other] = candidate, cell
                heapq.heappush(queue, (candidate, other))
    return costs, previous


def compile_region(story, characters, civ, world, doc, rows):
    """Compile an opt-in regional journey; existing stories remain unchanged."""
    start = doc['start_cell']
    if type(start) is not int or not 0 <= start < world.cells:
        raise ValueError('城镇探索需要原件中的有效起点地块')
    graph = road_graph(civ, world, doc['base_year'])
    costs, _ = shortest(graph, start)
    # One town site per cell. The explicitly selected settlement wins a shared site.
    by_cell = {r['cell']: r for r in reversed(rows) if type(r.get('cell')) is int}
    selected_start = next(r for r in rows if r['city_id'] == doc['city_id'])
    by_cell[start] = selected_start
    chosen = sorted((c for c in by_cell if c in costs), key=lambda c: (costs[c], c))[:TOWN_LIMIT]
    locations, towns, roads, travel = [], [], [], []
    places = {}

    def add_place(pid, name, coords, description, **extra):
        place = {'id': pid, 'name': name, 'coordinates': coords, 'description': description,
                 'neighbors': [], 'scenes': [], **extra}
        locations.append(place)
        places[pid] = place
        return place

    def connect(a, b, kind, hours, km, points, source):
        rid = 'road_%d' % len(roads)
        for x, y in ((a, b), (b, a)):
            places[x]['neighbors'].append(y)
            travel.append({'origin': x, 'destination': y, 'kind': kind, 'hours': hours,
                           'import_id': doc['import_id']})
        roads.append({'id': rid, 'origin': a, 'destination': b, 'kind': kind,
                      'hours': hours, 'distance_km': round(km, 2), 'points': points, 'source': source})

    def cid(cell):
        return 'city_' + by_cell[cell]['city_id'].split(':')[1]

    for cell in chosen:
        row = by_cell[cell]
        town_id = cid(cell)
        coords = [round(world.lon[cell], 6), round(world.lat[cell], 6)]
        name = row['name'] or row['city_id']
        seed = hashlib.sha256((doc['source_sha256'] + row['city_id']).encode()).digest()
        rng = random.Random(int.from_bytes(seed[:8], 'big'))
        raw = next(r for r in civ['settlements'] if 'settlement:%s' % r['id'] == row['city_id'])
        sites = [('gate', '城镇入口', (300, 350)), ('market', '集市广场', (300, 210)),
                 ('inn', '旅店', (140, 210)), ('workshop', '工坊街', (455, 210)),
                 ('hall', '议事厅', (300, 80))]
        if raw.get('port'):
            sites.append(('dock', '码头', (455, 350)))
        elif world.elevation and world.elevation[cell] > 1500:
            sites.append(('watch', '山路望台', (455, 80)))
        else:
            sites.append(('well', '水井广场', (140, 80)))
        nodes = []
        for index, (kind, label, point) in enumerate(sites):
            pid = town_id if index == 0 else town_id + '_' + kind
            xy = [point[0] + rng.randint(-18, 18), point[1] + rng.randint(-12, 12)]
            add_place(pid, name + '·' + label, coords, name + '的' + label + '。街道连接着附近的公共场所。',
                      town_id=town_id, town_position=xy, facility_kind=kind,
                      civ_ref={'city_id': row['city_id'], 'cell': cell})
            nodes.append({'id': pid, 'name': label, 'position': xy, 'kind': kind})
        streets = [(0, 1), (1, 2), (1, 3), (1, 4), (3 if raw.get('port') else 4, 5), (2, 4)]
        for a, b in streets:
            pa, pb = nodes[a], nodes[b]
            km = math.dist(pa['position'], pb['position']) / 500
            connect(pa['id'], pb['id'], 'street', 1, km, [], 'generated_town_plan')
        towns.append({'id': town_id, 'name': name, 'cell': cell, 'city_id': row['city_id'],
                      'nodes': nodes, 'streets': [[nodes[a]['id'], nodes[b]['id']] for a, b in streets],
                      'source': 'civ_site_generated_plan', 'coordinates': coords})

    for origin in chosen:
        reached, previous = shortest(graph, origin, set(by_cell))
        for target in chosen:
            if target <= origin or target not in reached:
                continue
            path, cell = [target], target
            while cell != origin:
                cell = previous[cell]
                path.append(cell)
            path.reverse()
            # Long journeys have explicit waystations, keeping the existing 168h limit.
            last, hours, km, points, kinds = cid(origin), 0, 0, [], set()
            points.append([world.lon[path[0]], world.lat[path[0]]])
            for a, b in zip(path, path[1:]):
                h, length, kind = graph[a][b]
                if h > 168:
                    raise ValueError('原件单段道路超过一周行程，需先细化地块')
                if hours + h > 168:
                    waypoint = 'way_%d' % len(locations)
                    add_place(waypoint, by_cell[origin]['name'] + '—' + by_cell[target]['name'] + '沿途驿站',
                              points[-1], '旅途中休整和辨认方向的路标。')
                    connect(last, waypoint, '/'.join(sorted(kinds)), max(1, math.ceil(hours)), km, points,
                            'civ_routes')
                    last, hours, km, points, kinds = waypoint, 0, 0, [points[-1]], set()
                hours += h
                km += length
                kinds.add(kind)
                points.append([world.lon[b], world.lat[b]])
            connect(last, cid(target), '/'.join(sorted(kinds)), max(1, math.ceil(hours)), km, points, 'civ_routes')

    if len(travel) > 200:
        raise ValueError('本区域路线超过现有200条规则上限，请换一个起点')
    story['locations'] = locations
    story['events'] = []
    story['mechanics']['adventure'] = {'version': 1, 'routes': travel}
    story['mechanics']['exploration'] = {'version': VERSION, 'towns': towns, 'roads': roads,
                                       'source_sha256': doc['source_sha256'], 'base_year': doc['base_year']}
    characters['characters'][0]['location_id'] = cid(start)
    return story, characters


def surface(session, story, adventure=None):
    config = story.get('mechanics', {}).get('exploration')
    if not config:
        return None
    visible = {p['id'] for p in play_map.visible_places(session, story)}
    current = next(p for p in story['locations'] if p['id'] == session['location'])
    town = next((t for t in config['towns'] if t['id'] == current.get('town_id')), None)
    if town:
        public = {p['id'] for p in story['locations'] if not play_map._place_withheld(p, session)}
        town = {**town, 'nodes': [n for n in town['nodes'] if n['id'] in public],
                'streets': [edge for edge in town['streets'] if all(pid in public for pid in edge)]}
    executable = {p['target']['id'] for p in (adventure or {}).get('plans', [])
                  if p['kind'] == 'travel' and p.get('supported') and p.get('execution') == 'move'}
    # Town layouts contain only the public generated streets of the current town.
    roads = [r for r in config['roads'] if r['origin'] in visible and r['destination'] in visible]
    return {'version': VERSION, 'state_version': session.get('state_version', 0),
            'location_id': session['location'], 'description': current.get('description', ''),
            'town': town, 'roads': roads,
            'destinations': [{'id': p['id'], 'name': p['name'],
                              'hours': next(r['hours'] for r in roads if {r['origin'], r['destination']} == {current['id'], p['id']}),
                              'can_move': p['id'] in executable}
                             for p in story['locations'] if p['id'] in current['neighbors'] and p['id'] in visible]}
