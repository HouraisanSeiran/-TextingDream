"""Finite metre-coordinate map generation; no browser or save side effects."""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import scipy
from scipy import ndimage, sparse
from scipy.sparse.csgraph import dijkstra, minimum_spanning_tree
from pydantic import BaseModel, ConfigDict, Field

VERSION = 'dreamterra-map-1'
SPACING = 1000.0
BIOMES = ['海洋', '湖泊', '平原', '丘陵', '山地', '高原', '森林', '荒漠', '湿地', '洪泛平原']


class Parameters(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, validate_default=True)
    seed: int = Field(default=20261020, ge=0, le=2147483647, strict=True)
    size_km: int = Field(default=512, ge=128, le=1024, strict=True)
    water_fraction: float = Field(default=.38, ge=.1, le=.8)
    river_density: float = Field(default=1.5, ge=.5, le=4)
    rainfall: float = Field(default=1, ge=.3, le=2)
    mountains: float = Field(default=1, ge=.2, le=2)
    settlements: int = Field(default=48, ge=12, le=64, strict=True)
    year: int = Field(default=100, ge=0, le=10000, strict=True)


def sources():
    root = Path(os.environ.get('DREAMTERRA_SOURCE', str(Path(__file__).resolve().parents[2] / '山川形意Terragenesis')))
    if not (root / 'terrain_pipeline/world_water_layout.py').is_file():
        raise ValueError('找不到 TerraGenesis 源工程，请配置 DREAMTERRA_SOURCE')
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    names = ['terrain_pipeline.world_water_layout', 'terrain_pipeline.fictional_world_overview',
             'terrain_pipeline.surface_rivers.drainage', 'diffusion.geographic_noise']
    modules = [importlib.import_module(name) for name in names]
    hashes = {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
              for name, module in zip(names, modules)}
    return modules, hashes


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def point(cell, n):
    return [float(cell % n) + .5, float(cell // n) + .5]  # km, cell centres


def generate(p: Parameters):
    (layout, overview, drainage, noise), hashes = sources()
    n = p.size_km
    extent = n * SPACING
    axis = (np.arange(n) + .5) * SPACING
    x, z = np.meshgrid(axis, axis)
    spec = layout.LayoutSpec('archipelago', p.water_fraction, world_seed=p.seed,
                             layout_id='DreamTerra', mode='finite', frame_origin_m=(0, 0), frame_side_m=extent)
    field = layout.layout_field(spec, x, z)
    land = field > 0
    if not land.any() or land.all():
        raise ValueError('区域没有可用海陆分界，请调整水域比例或区域规模')
    request = SimpleNamespace(spacing_m=SPACING, extent_m=extent, grid_size=n, seed=p.seed)
    ledger = {}
    elevation, inland = overview._elevation(request, land, ledger)
    # Reuse the continuous ridge builder, but use this layout's land components.
    components, count = ndimage.label(land)
    ridges = []
    for component in range(1, count + 1):
        zz, xx = np.where(components == component)
        if len(xx) < n * n * .015:
            continue
        seed = layout.derive_subseed(p.seed, 'DreamTerra', 'ridge', component)
        ledger['ridge', component] = seed
        rng = np.random.default_rng(seed)
        center = np.array([(xx.mean() + .5) * SPACING, (zz.mean() + .5) * SPACING])
        span = max(np.ptp(xx), np.ptp(zz)) * SPACING * .85
        angle = float(rng.uniform(0, math.pi))
        for branch in range(3):
            vertices = overview._draw_ridge(rng, center, span * (1 if branch == 0 else .62), angle + branch * .85)
            distance = overview._distance_to_polyline(vertices, x, z)
            width = extent * (.025 if branch == 0 else .014)
            added = (2100 if branch == 0 else 1100) * p.mountains * np.exp(-(distance / width)**2)
            elevation += added * inland * (components == component)
            ridges.append({'points': [[a/1000, b/1000] for a, b in vertices], 'width_km': width/1000})
    # A stable hotspot is a terrain source, not a volcano icon added after hydrology.
    hot_seed = layout.derive_subseed(p.seed, 'DreamTerra', 'hotspot')
    ledger['hotspot', 0] = hot_seed
    hot_rng = np.random.default_rng(hot_seed)
    candidates = np.flatnonzero(land & (inland > .5))
    volcanoes = []
    if candidates.size:
        c = int(candidates[int(hot_rng.integers(candidates.size))])
        vx, vz = point(c, n)
        radius = extent * .018
        cone = np.maximum(0, 1 - np.hypot(x - vx*1000, z - vz*1000) / radius)
        elevation += cone * 1300 * p.mountains * land
        volcanoes.append({'id': 'hotspot-0', 'cell': c, 'point': [vx, vz], 'basis': 'seeded_mantle_hotspot', 'radius_km': radius/1000})
    climate_seed = layout.derive_subseed(p.seed, 'DreamTerra', 'climate')
    ledger['climate', 0] = climate_seed
    humid = noise.field(x, z, climate_seed, 0, ((extent*.28, 1), (extent*.09, .3)))
    temperature = 24 - z/extent*14 - np.maximum(elevation, 0)*.006
    precipitation = np.clip((900 + humid*650 - elevation*.06) * p.rainfall, 90, 2600)
    ocean = ~land
    outlets = ocean.copy()
    outlets[[0, -1], :] = True
    outlets[:, [0, -1]] = True
    routing = drainage.route(elevation, outlets, SPACING)
    depth = routing.routing_height - elevation
    water = np.where(ocean, 1, np.where(depth > 3, 2, 0)).astype(np.uint8)
    # m/year -> m/second; discharge is m3/s, unlike civ's cell-weighted flux.
    runoff = np.maximum(.02, (precipitation - (250 + 22*np.maximum(temperature, 0))*.45)/1000)
    runoff *= land / (365.25*86400)
    flow = drainage.accumulate(routing, runoff, SPACING)
    threshold = 1.5 / p.river_density
    channel = (flow.discharge >= threshold) & land
    dz, dx = np.gradient(elevation, SPACING)
    slope = np.hypot(dx, dz)
    river_distance = ndimage.distance_transform_edt(~channel, sampling=SPACING)
    flood = (water == 0) & (river_distance <= 2000) & (slope < .012) & (elevation < 650) & (temperature > 0)
    wet = (water == 0) & (slope < .008) & (precipitation > 650) & (temperature > 2) & (elevation < 450) & ((depth > .15) | (channel & (flow.discharge > 2)))
    biome = np.full((n, n), 2, np.uint8)
    biome[(slope > .025) | (elevation > 450)] = 3
    biome[(elevation > 1100) & (slope < .04)] = 5
    biome[(slope > .12) | (elevation > 1800)] = 4
    biome[(precipitation > 950) & (temperature > 1) & (elevation < 1700)] = 6
    biome[(precipitation < 400) & (temperature > 8)] = 7
    biome[flood] = 9
    biome[wet] = 8
    biome[water == 1] = 0
    biome[water == 2] = 1
    rivers = trace_rivers(routing, flow.discharge, channel, water, n, threshold)
    towns = settle(p, elevation, slope, water, precipitation, temperature, channel, flow.discharge, biome)
    roads = connect(towns, elevation, slope, water, biome, channel, flow.discharge, n)
    features = []
    for kind, mask, basis in [('canyon', channel & (slope > .09) & (elevation > 500), 'river_in_high_relief'),
                               ('pass', (slope < .04) & (elevation > 800) & (ndimage.maximum_filter(elevation, size=9) - elevation > 300), 'local_saddle_candidate')]:
        cells = np.flatnonzero(mask)
        # Stable candidates; passes used by roads are the gameplay-relevant subset.
        road_cells = {c for r in roads for c in r['cells']}
        cells = [int(c) for c in cells if kind != 'pass' or int(c) in road_cells]
        for c in cells[::max(1, len(cells)//24)][:24]:
            features.append({'kind': kind, 'cell': c, 'point': point(c, n), 'basis': basis})
    arrays = {'elevation': elevation.astype('float32'), 'water': water, 'water_level': routing.routing_height.astype('float32'),
              'receiver': routing.receiver.astype('int32').reshape(n, n), 'order': routing.order.astype('int32'),
              'discharge': flow.discharge.astype('float32'), 'slope': slope.astype('float32'), 'biome': biome,
              'temperature': temperature.astype('float32'), 'precipitation': precipitation.astype('float32')}
    engine = {'sources': hashes, 'numpy': np.__version__, 'scipy': scipy.__version__}
    provenance = {'generator': VERSION + '+' + digest(engine)[:12], 'parameters': p.model_dump(), 'sources': hashes,
                  'numeric_runtime': {'numpy': np.__version__, 'scipy': scipy.__version__}, 'layout': spec.parameters(),
                  'subseeds': {f'{a}:{b}': int(v) for (a,b), v in ledger.items()}, 'coordinate_system': 'finite_x_east_z_south_km',
                  'spacing_m': SPACING, 'hydrology': 'map_derived', 'boundary': 'ocean and explicit external frame outlets',
                  'array_hashes': {k: hashlib.sha256(v.tobytes()).hexdigest() for k,v in arrays.items()}}
    world = {'provenance': provenance, 'size_km': n, 'year': p.year, 'rivers': rivers, 'towns': towns, 'roads': roads,
             'volcanoes': volcanoes, 'features': features, 'ridges': ridges, 'river_threshold_m3_s': threshold,
             'biome_names': BIOMES, 'stats': {'wetland_cells': int(wet.sum()), 'floodplain_cells': int(flood.sum()),
                'lake_cells': int((water == 2).sum()), 'river_segments': len(rivers), 'towns': len(towns), 'roads': len(roads),
                'water_balance_error_m3_s': float(flow.residual)}}
    audit(world, arrays)
    world['id'] = 'dt_' + digest(world)[:24]
    return world, arrays


def trace_rivers(routing, discharge, channel, water, n, threshold):
    rec, active = routing.receiver, channel.ravel()
    donors = np.zeros(rec.size, np.int32)
    selected = np.flatnonzero(active & (rec >= 0))
    np.add.at(donors, rec[selected], 1)
    starts = np.flatnonzero(active & ((donors != 1) | (water.ravel() == 2)))
    rivers = []
    for start in starts:
        if rec[start] < 0:
            continue
        cells = [int(start)]
        c = int(start)
        while rec[c] >= 0:
            c = int(rec[c]); cells.append(c)
            if not active[c] or donors[c] != 1 or water.flat[c] == 2:
                break
        end = cells[-1]
        q = float(discharge.flat[start])
        rivers.append({'id': f'river-{start}', 'cells': cells, 'points': [point(c,n) for c in cells],
                       'discharge_m3_s': q, 'level': 3 if q >= 10 else 2 if q >= 3 else 1,
                       'downstream_cell': end, 'outlet': 'ocean' if water.flat[end] == 1 else 'lake' if water.flat[end] == 2 else 'external' if rec[end] < 0 else 'river'})
    return rivers


def settle(p, elevation, slope, water, rain, temp, channel, discharge, biome):
    n = p.size_km
    freshwater = channel | (water == 2)
    fresh_distance = ndimage.distance_transform_edt(~freshwater)
    sea_distance = ndimage.distance_transform_edt(water != 1)
    flat = ndimage.uniform_filter((slope < .04).astype(float), size=7)
    coast = (sea_distance <= 2) & (ndimage.uniform_filter((water == 1).astype(float), size=9) > .12)
    resource = ndimage.uniform_filter(((biome == 6) | (biome == 3)).astype(float), size=9)
    score = 4*np.exp(-fresh_distance/4) + 3*flat + 2*coast + resource + np.clip(rain/1000,0,1)
    valid = (water == 0) & (slope < .12) & (temp > 0) & (fresh_distance <= 12) & (biome != 8)
    score[~valid] = -np.inf
    towns = []
    names_a, names_b = '青白松云石临长风鹿月', '川溪原湾渡林谷岭浦湖'
    for index in range(p.settlements):
        c = int(np.argmax(score))
        if not np.isfinite(score.flat[c]):
            break
        px, pz = point(c,n)
        tier = 'capital' if index == 0 else 'city' if index < max(2,p.settlements//12) else 'town' if index < p.settlements//3 else 'village'
        population = int({'capital': 60000, 'city': 22000, 'town': 3500, 'village': 350}[tier] * (1+.1*math.sin(index+p.seed)))
        towns.append({'id': f'town-{c}', 'cell': c, 'point': [px,pz], 'name': names_a[(index+p.seed)%10]+names_b[(index//10+index)%10]+('城' if tier in ('capital','city') else '镇' if tier=='town' else '村'),
                      'tier': tier, 'capital': index==0, 'population': population, 'population_year': p.year,
                      'port': bool(coast.flat[c]), 'siting': {'score': float(score.flat[c]), 'freshwater_km': float(fresh_distance.flat[c]),
                         'slope': float(slope.flat[c]), 'flat_land_fraction': float(flat.flat[c]), 'resource_access': float(resource.flat[c]),
                         'floodplain': bool(biome.flat[c] == 9)}})
        yy, xx = np.ogrid[:n,:n]
        radius = 10 if tier in ('capital','city') else 6
        score[(xx-(c%n))**2+(yy-(c//n))**2 < radius**2] = -np.inf
    if len(towns) < 2:
        raise ValueError('没有足够的适居城址；请调整降雨、山脉或水域比例')
    return towns


def connect(towns, elevation, slope, water, biome, channel, discharge, n):
    valid = (water == 0) & (slope < .3)
    ids = np.arange(n*n).reshape(n,n)
    rows, cols, weights = [], [], []
    for dz, dx in [(0,1),(1,0),(1,1),(1,-1)]:
        za, zb = slice(0,n-dz), slice(dz,n)
        xa, xb = (slice(0,n-dx),slice(dx,n)) if dx>=0 else (slice(-dx,n),slice(0,n+dx))
        a,b = ids[za,xa],ids[zb,xb]
        ok = valid[za,xa] & valid[zb,xb]
        if dz and dx:
            ok &= valid[za,xb] & valid[zb,xa]  # no corner-cut across water/cliffs
            # D8 river and road diagonals must not cross between four cells without
            # visiting a channel cell, where an explicit crossing can be recorded.
            ok &= ~(channel[za,xb] | channel[zb,xa])
        length = math.hypot(dz,dx)
        grade = np.abs(elevation[za,xa]-elevation[zb,xb])/(length*1000)
        ok &= grade < .25
        cost = length*(1+grade*18 + (biome[za,xa]==8)*2 + (biome[za,xa]==9)*.3)
        cost += (channel[za,xa]|channel[zb,xb]) * (.2 + np.sqrt(np.maximum(discharge[za,xa],discharge[zb,xb]))*.12)
        rows.extend([a[ok],b[ok]]);cols.extend([b[ok],a[ok]]);weights.extend([cost[ok],cost[ok]])
    graph = sparse.csr_matrix((np.concatenate(weights),(np.concatenate(rows),np.concatenate(cols))), shape=(n*n,n*n))
    distances, predecessors = dijkstra(graph, directed=False, indices=[t['cell'] for t in towns], return_predecessors=True)
    matrix = distances[:,[t['cell'] for t in towns]]
    tree = minimum_spanning_tree(np.where(np.isfinite(matrix), matrix, 0)).tocoo()
    pairs = {(min(int(a),int(b)),max(int(a),int(b))) for a,b in zip(tree.row,tree.col)}
    # A few local alternatives; retain the established route's actual cell chain.
    for a in range(len(towns)):
        candidates = [int(b) for b in np.argsort(matrix[a]) if b!=a and np.isfinite(matrix[a,b])]
        if candidates:
            b=candidates[0];pairs.add((min(a,b),max(a,b)))
    roads=[]
    for a,b in sorted(pairs):
        cells=[towns[b]['cell']]
        while cells[-1]!=towns[a]['cell']:
            c=int(predecessors[a,cells[-1]])
            if c<0: raise ValueError('道路追踪失败')
            cells.append(c)
        cells.reverse()
        km=sum(math.dist(point(u,n),point(v,n)) for u,v in zip(cells,cells[1:]))
        crossings=[]
        previous=False
        for c in cells:
            here=bool(channel.flat[c])
            if here and not previous:
                q=float(discharge.flat[c]);kind='ford' if q<1 else 'bridge' if q<12 else 'ferry'
                crossings.append({'cell':c,'point':point(c,n),'kind':kind,'discharge_m3_s':q})
            previous=here
        hours=max(1,math.ceil(float(matrix[a,b])/5 + sum(.5 if v['kind']=='ferry' else .1 for v in crossings)))
        roads.append({'id':f'road-{a}-{b}','origin':towns[a]['id'],'destination':towns[b]['id'],'kind':'road',
                      'cells':cells,'points':[point(c,n) for c in cells], 'distance_km':km,'hours':hours,'crossings':crossings})
    connected={t for r in roads for t in (r['origin'],r['destination'])}
    for town in towns:
        town['access']='road' if town['id'] in connected else 'isolated_landmass'
    return roads


def audit(world, arrays):
    rec=arrays['receiver'].ravel();order=arrays['order'];n=len(rec)
    rank=np.empty(n,np.int32);rank[order]=np.arange(n)
    cells=np.flatnonzero(rec>=0)
    if np.any(rank[rec[cells]]>=rank[cells]):raise ValueError('水系存在循环')
    height=arrays['water_level'].ravel()
    if np.any(height[rec[cells]]>height[cells]+.001):raise ValueError('水面存在逆坡')
    for town in world['towns']:
        c=town['cell']
        if arrays['water'].flat[c] or arrays['slope'].flat[c]>=.12:raise ValueError('城址不适居')
    for road in world['roads']:
        if any(arrays['water'].flat[c] for c in road['cells']):raise ValueError('陆路穿越海湖')
        if road['hours']>168:raise ValueError('道路超过现有单次旅行一周限制，请缩小区域')
    world['audit']={'acyclic':True,'downhill_water_surface':True,'town_sites':True,'roads_land_only':True,
                    'depressions':'water_level is filled hydraulic surface; bed elevation remains stored'}
