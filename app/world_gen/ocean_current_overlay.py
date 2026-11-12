"""Opt-in Terragenesis ocean scenario and land-safe cartographic streamlines.

Only this new product is written. No atmosphere solve, climate feedback, native
water inventory, default world selection, atlas rebuild or GPU is involved.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import numpy as np

SCHEMA = 'dream-ocean-current-overlay-1'
SOURCE_ID = '6d99aafd0b11d83e6af1358195dcab5b3c437771e9f5466fa7ceb7eb8dd514e4'
CLIMATE_ID = '70d36369e89eaef26b79ac19c250fff164df022f3268844b731c5325d412ae4c'
ENVIRONMENT_ID = '9fda7cc802e509c154662edcfc2e6f8c5dc4dd135d9d052527f87681cbbef0c1'
LIMITATIONS = [
    'One finite initially reference-SST year, not a converged ocean climatology; no climate feedback.',
    '40 km partial-cell upper layer; unresolved split cells and their ports excluded, so some water/straits are lost.',
    'Paths stop at original native ocean mask/closed macro faces; no smoothing across land.',
    'Warm/cold means SST anomaly relative to same-latitude monthly reference, not absolute temperature.',
    'No western-boundary intensification, upwelling, deep ocean, sea ice, tides or calibrated navigation speed claim.',
]


def _modules():
    from app.world_gen.climate_world_stage import climate_module
    climate = climate_module()
    from terrain_pipeline import ocean_circulation
    return climate, ocean_circulation


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def _array(root, descriptor, climate):
    path = (Path(root)/descriptor.get('file', descriptor.get('npy_file'))).resolve()
    if not path.is_relative_to(Path(root).resolve()) or climate._digest(path) != descriptor['sha256']:
        raise ValueError('Saved source array path/content differs')
    return np.load(path, allow_pickle=False, mmap_mode='r')


def load_inputs(world, climate_product, *, expected_source=SOURCE_ID, expected_climate=CLIMATE_ID):
    """Read native ocean/bed and exact saved macro winds, never regenerate wind."""
    from app.map_source import load_source
    climate, _ = _modules()
    mapped = load_source('world-map-product', world, expected_identity=expected_source)
    info = mapped.info
    if info.grid_semantics != 'cell-centre':
        raise ValueError('Cell-centre native terrain required')
    x, z = info.first_sample_xz_m
    nz, nx = info.shape_zx
    crop = mapped.crop(x, z, x+nx*info.spacing_m, z+nz*info.spacing_m,
                       layers=('elevation_m', 'status'), max_cells=nz*nx)
    if not crop['complete'] or not np.isin(crop['status'], [3, 4, 5]).all():
        raise ValueError('Complete known native sea/land support required')
    source = dict(elevation_m=crop['elevation_m'], ocean_mask=crop['status'] == 3,
                  first_xz_m=list(info.first_sample_xz_m), spacing_m=float(info.spacing_m),
                  source_identity=info.identity, world_seed=info.world_seed)
    manifest = json.loads((Path(climate_product)/'manifest.json').read_text(encoding='utf-8'))
    if climate._manifest_hash({k:v for k,v in manifest.items() if k != 'manifest_identity'}) != manifest['manifest_identity']:
        raise ValueError('Saved climate manifest identity differs')
    meta = manifest['metadata']
    if (manifest['identity'] != expected_climate or manifest['status'] != 'complete'
            or meta['source_identity'] != info.identity or meta['world_seed'] != info.world_seed
            or meta['shape_zx'] != list(info.shape_zx) or meta['first_xz_m'] != source['first_xz_m']
            or meta['spacing_m'] != source['spacing_m']):
        raise ValueError('Climate identity/source/grid differs')
    saved_ocean = _array(climate_product, manifest['fields']['ocean_mask'], climate)
    if not np.array_equal(saved_ocean, source['ocean_mask']):
        raise ValueError('Saved climate ocean differs from native source')
    from terrain_pipeline.common_infra import array_sha256
    if array_sha256(source['elevation_m']) != meta['terrain_sha256']:
        raise ValueError('Saved climate bed differs from native source')
    winds = tuple(_array(climate_product, manifest['diagnostics']['atmosphere'][name], climate)
                  for name in ('monthly_wind_x_m_s', 'monthly_wind_z_m_s'))
    return source, meta, winds


def prepare_context(source, climate_metadata, monthly_winds, *, references=None):
    """Restore physical wet geometry, then conservatively remove split blocks."""
    climate, _ = _modules()
    cfg = deepcopy(climate_metadata['config'])
    # Only context preparation: avoid the diagnostic majority mask/mixed bed.
    for key in ('atmosphere_backend', 'diagnostic', 'snow_ice', 'layered_atmosphere'):
        cfg.pop(key, None)
    cfg['atmosphere'] = {}
    cfg['ocean'] = {}
    context = climate.prepare_context(source, cfg, references)
    if context['reference_identity'] != climate_metadata['reference_identity']:
        raise ValueError('Reference SST bundle differs from saved climate')
    grid = climate_metadata['macro_grid']
    if (grid['shape_zx'] != list(context['ocean_mask'].shape)
            or grid['spacing_m'] != context['spacing_m'] or grid['first_xz_m'] != context['first_xz_m']):
        raise ValueError('Saved macro wind grid differs from physical ocean context')
    winds = tuple(np.asarray(value, float) for value in monthly_winds)
    if any(value.shape != (12,)+context['ocean_mask'].shape or not np.isfinite(value).all() for value in winds):
        raise ValueError('Twelve finite saved macro winds required')
    if len(winds) != 2:
        raise ValueError('Saved zonal and meridional monthly winds required')
    context['monthly_winds'] = winds
    context['native_latitude_deg'] = climate.spatial_fields(source['ocean_mask'].shape,
        source['first_xz_m'], source['spacing_m'], cfg)[0]
    wet, boundary = context['ocean_mask'], context['ocean_boundary']
    if not wet.any():
        raise ValueError('Source has no ocean')
    original_fraction = context['ocean_fraction'].copy()
    for row, col, _ in context['unresolved_split_ocean_blocks']:
        wet[row, col] = False
    if not wet.any():
        raise ValueError('No representable ocean remains after split-block exclusion')
    boundary['wet_area_fraction'] = np.where(wet, original_fraction, 0.)
    for key, width, allowed in (
        ('face_open_x', 'face_width_fraction_x', wet[:, :-1] & wet[:, 1:]),
        ('face_open_z', 'face_width_fraction_z', wet[:-1] & wet[1:]),
    ):
        boundary[key] &= allowed
        boundary[width] = np.where(boundary[key], boundary[width], 0.)
    for edge, selection in dict(west=(slice(None), 0), east=(slice(None), -1),
                                north=(0, slice(None)), south=(-1, slice(None))).items():
        entry = boundary[edge]
        opened = wet[selection] & (np.asarray(entry['kind']) == 'open')
        entry['kind'] = np.where(opened, 'open', 'closed')
        entry['open_width_fraction'] = np.where(opened, entry['open_width_fraction'], 0.)
    lost = float(original_fraction[~wet].sum()*context['spacing_m']**2)
    context['topology'] = dict(split_blocks=context['unresolved_split_ocean_blocks'],
        excluded_wet_area_m2=lost, excluded_native_wet_cells=int(round(lost/source['spacing_m']**2)),
        excluded_ocean_fraction=lost/(np.count_nonzero(source['ocean_mask'])*source['spacing_m']**2),
        method='TG native wet-mean bed/area/face support; split blocks and all incident ports closed')
    return context


def plan(source, climate_metadata, monthly_winds, *, references=None):
    context = prepare_context(source, climate_metadata, monthly_winds, references=references)
    wet = context['ocean_mask']
    return dict(schema=SCHEMA, producer='Terragenesis', device='cpu',
        macro_shape_zx=list(wet.shape), macro_spacing_m=context['spacing_m'], wet_cells=int(wet.sum()),
        macro_cells=int(wet.size), first_xz_m=context['first_xz_m'], topology=context['topology'],
        solver_config=dict(max_cycles=1, max_substeps_per_month=128, heat_advection=True),
        boundary='actual native sea edges: pressure 0m and reference SST; land closed; unlike closed moisture climate',
        limits=dict(wall_seconds=120, rss_bytes=2*1024**3),
        memory_note='Arrays roughly 150-250 MiB at 50k cells; sparse LU fill is topology dependent and NOT linearly predictable.',
        limitations=LIMITATIONS)


def solve(context, *, max_substeps_per_month=128):
    """Caller must run this CPU-only native sparse LU in a bounded subprocess."""
    _, ocean = _modules()
    u, v = context['monthly_winds']
    return ocean.solve_ocean(context['bed_m'], context['ocean_mask'], u, v,
        context['latitude_deg'], context['spacing_m'],
        monthly_reference_sst_c=context['monthly_reference_sst_c'], boundary=context['ocean_boundary'],
        config=dict(max_cycles=1, stop_on_convergence=False, max_substeps_per_month=max_substeps_per_month))


def _index(point, first, spacing):
    x, z = np.floor((np.asarray(point)-np.asarray(first))/spacing+.5).astype(int)
    return int(z), int(x)


def _inside(index, shape):
    return 0 <= index[0] < shape[0] and 0 <= index[1] < shape[1]


def segment_is_ocean(start, end, source, context):
    """Dense native-mask check plus exact grid-face crossings; no land bridges."""
    start, end = np.asarray(start), np.asarray(end)
    spacing = source['spacing_m']
    # Include every native and macro cell-edge crossing, not just uniform probes.
    delta = end-start
    times = [0., 1.]
    for first, step, shape in ((source['first_xz_m'], spacing, source['ocean_mask'].shape),
                               (context['first_xz_m'], context['spacing_m'], context['ocean_mask'].shape)):
        for axis, length in ((0, shape[1]), (1, shape[0])):
            if abs(delta[axis]) < 1e-12:
                continue
            low, high = sorted(((start[axis]-first[axis])/step+.5, (end[axis]-first[axis])/step+.5))
            for gridline in range(max(0, int(np.ceil(low))), min(length, int(np.floor(high)))+1):
                t = (first[axis]+(gridline-.5)*step-start[axis])/delta[axis]
                if 0 < t < 1:
                    times.append(float(t))
    times = sorted(set(times))
    times += [(a+b)/2 for a, b in zip(times[:-1], times[1:])]
    count = max(2, int(np.ceil(np.linalg.norm(delta)/(spacing/4)))+1)
    times = sorted(set(times+np.linspace(0, 1, count).tolist()))
    previous = None
    for t in times:
        point = start+t*delta
        native = _index(point, source['first_xz_m'], spacing)
        macro = _index(point, context['first_xz_m'], context['spacing_m'])
        if (not _inside(native, source['ocean_mask'].shape) or not source['ocean_mask'][native]
                or not _inside(macro, context['ocean_mask'].shape) or not context['ocean_mask'][macro]):
            return False
        if previous is not None and macro != previous:
            r0, c0 = previous
            r1, c1 = macro
            boundary = context['ocean_boundary']
            # Corner crossing must allow both orders, a conservative no-corner-cut rule.
            if c0 != c1:
                if abs(c1-c0) != 1 or not all(boundary['face_open_x'][r, min(c0,c1)] for r in (r0,r1)):
                    return False
            if r0 != r1:
                if abs(r1-r0) != 1 or not all(boundary['face_open_z'][min(r0,r1), c] for c in (c0,c1)):
                    return False
        previous = macro
    return True


def _velocity(point, u, v, context):
    row, col = _index(point, context['first_xz_m'], context['spacing_m'])
    if not _inside((row,col), u.shape) or not context['ocean_mask'][row,col]:
        return None
    x, z = (np.asarray(point)-context['first_xz_m'])/context['spacing_m']
    c, r = int(np.floor(x)), int(np.floor(z))
    b = context['ocean_boundary']
    # Bilinear only within a fully connected four-wet-centre stencil.
    if (0 <= r < u.shape[0]-1 and 0 <= c < u.shape[1]-1
            and context['ocean_mask'][r:r+2,c:c+2].all()
            and b['face_open_x'][r:r+2,c].all() and b['face_open_z'][r,c:c+2].all()):
        weights = np.array([[(1-(z-r))*(1-(x-c)), (1-(z-r))*(x-c)],
                            [(z-r)*(1-(x-c)), (z-r)*(x-c)]])
        vector = np.array([(u[r:r+2,c:c+2]*weights).sum(), (v[r:r+2,c:c+2]*weights).sum()])
    else:
        vector = np.array([u[row,col], v[row,col]])
    return vector if np.isfinite(vector).all() and np.linalg.norm(vector) > 1e-8 else None


def _half_trace(seed, sign, u, v, source, context, max_steps):
    points = [np.asarray(seed, float)]
    seen = set()
    step = source['spacing_m']*.75
    for _ in range(max_steps):
        vector = _velocity(points[-1], u, v, context)
        if vector is None:
            break
        direction = vector/np.linalg.norm(vector)*sign
        midpoint = points[-1]+direction*step/2
        vector_mid = _velocity(midpoint, u, v, context)
        if vector_mid is None:
            break
        end = points[-1]+vector_mid/np.linalg.norm(vector_mid)*sign*step
        if not segment_is_ocean(points[-1], end, source, context):
            break
        key = tuple(np.floor((end-np.asarray(source['first_xz_m']))/(step*.8)).astype(int))
        if key in seen:
            break
        seen.add(key)
        points.append(end)
    return points


def trace_routes(source, context, arrays, *, month=1, max_routes=18, min_length_m=400000.,
                 max_steps=350, anomaly_threshold_c=.3, source_ids=None):
    """Deterministic sparse flow-to paths; types use native-supported SST anomaly.

    Nearest macro SST is sampled on native ocean support and the zonal SST
    reference at each native latitude is subtracted (not a native heat solve).
    """
    if not 1 <= month <= 12 or max_routes < 1 or max_steps < 1 or anomaly_threshold_c <= 0:
        raise ValueError('Invalid route month/count/steps/anomaly threshold')
    u, v = (arrays[key][month-1] for key in ('monthly_current_x_m_s', 'monthly_current_z_m_s'))
    anomaly = arrays.get('monthly_sst_anomaly_c')
    candidates = []
    wet = context['ocean_mask']
    stride = max(1, int(round(max(wet.shape)/12)))
    for row in range(stride//2, wet.shape[0], stride):
        for col in range(stride//2, wet.shape[1], stride):
            if not wet[row,col]:
                continue
            seed = np.asarray(context['first_xz_m'])+np.array([col,row])*context['spacing_m']
            if not segment_is_ocean(seed, seed, source, context):
                continue
            backward = _half_trace(seed, -1, u, v, source, context, max_steps)
            forward = _half_trace(seed, 1, u, v, source, context, max_steps)
            points = np.asarray(backward[:0:-1]+forward)
            length = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
            if length >= min_length_m:
                candidates.append((length, row, col, points))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    routes, occupied, counts = [], set(), {}
    separation = context['spacing_m']*5
    for length, row, col, points in candidates:
        bins = {tuple(np.floor(p/separation).astype(int)) for p in points[::4]}
        if bins and len(bins & occupied)/len(bins) > .25:
            continue
        # Prefer different geographic sectors, not dozens of parallel threads.
        sector = (int(row*3/wet.shape[0]), int(col*4/wet.shape[1]))
        if counts.get(sector, 0) >= 2:
            continue
        indices = [_index(p, context['first_xz_m'], context['spacing_m']) for p in points]
        if 'monthly_sea_temperature_c' in arrays and 'native_latitude_deg' in context:
            native_indices = [_index(p, source['first_xz_m'], source['spacing_m']) for p in points]
            native_latitudes = [context['native_latitude_deg'][r,c] for r,c in native_indices]
            native_reference = np.interp(native_latitudes, context['reference']['latitude_deg'],
                context['reference']['monthly_zonal_sst_c'][month-1])
            values = [float(arrays['monthly_sea_temperature_c'][month-1,r,c]-ref)
                      for (r,c),ref in zip(indices,native_reference)]
        else:
            values = [] if anomaly is None else [float(anomaly[month-1,r,c]) for r,c in indices]
        mean = float(np.mean(values)) if values and np.isfinite(values).all() else None
        kind = 'unclassified' if mean is None else ('warm' if mean >= anomaly_threshold_c else 'cold' if mean <= -anomaly_threshold_c else 'neutral')
        centre = points[len(points)//2]
        xr = (centre[0]-source['first_xz_m'][0])/(source['spacing_m']*source['ocean_mask'].shape[1])
        zr = (centre[1]-source['first_xz_m'][1])/(source['spacing_m']*source['ocean_mask'].shape[0])
        position = ('北' if zr < 1/3 else '南' if zr > 2/3 else '中')+('西' if xr < 1/3 else '东' if xr > 2/3 else '部')
        type_name = dict(warm='偏暖流', cold='偏冷流', neutral='中性流', unclassified='表层流')[kind]
        number = len(routes)+1
        routes.append(dict(id=f'current-{month:02d}-{number:02d}', name=f'{position}{type_name}{number:02d}',
            type=kind, month=month, coordinates_xz_m=points.tolist(), flow_direction='coordinate order, X east/Z south, flow-to',
            length_m=length, mean_sst_anomaly_c=mean, anomaly_threshold_c=anomaly_threshold_c,
            anomaly_sampling='nearest physical macro SST on original native ocean support minus reference at native latitude; not air temperature',
            source_ids=source_ids or {}, basin_id=int(arrays.get('basin_id', np.zeros_like(wet,int))[row,col])))
        occupied |= bins
        counts[sector] = counts.get(sector,0)+1
        if len(routes) >= max_routes:
            break
    return routes


def prepare(source, climate_metadata, monthly_winds, out_dir, *, references=None,
            max_substeps_per_month=128, months=(1,7), max_routes=18):
    """Save only this independent candidate. A failed heat budget is not replaced."""
    root = Path(out_dir)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Use a new empty ocean product directory')
    context = prepare_context(source, climate_metadata, monthly_winds, references=references)
    result = solve(context, max_substeps_per_month=max_substeps_per_month)
    ids = dict(world=source['source_identity'], climate=climate_metadata['identity'],
               reference=context['reference_identity'], ocean_forcing=result['metadata']['forcing_identity'])
    routes = [route for month in months for route in trace_routes(source, context, result['arrays'],
              month=month, max_routes=max_routes, source_ids=ids)]
    root.mkdir(parents=True, exist_ok=True)
    # Small selected diagnostic set, not the full heat-ledger workspace.
    names = ('ocean_mask','basin_id','face_open_x','face_open_z','wet_area_fraction',
             'monthly_current_x_m_s','monthly_current_z_m_s','monthly_sea_temperature_c',
             'monthly_reference_sst_c','monthly_sst_anomaly_c')
    for name in names:
        np.save(root/(name+'.npy'), result['arrays'][name], allow_pickle=False)
    manifest = dict(schema=SCHEMA, producer='Terragenesis', status='finite-year-candidate', source_ids=ids,
        native_grid=dict(first_xz_m=source['first_xz_m'], spacing_m=source['spacing_m'], shape_zx=list(source['ocean_mask'].shape)),
        macro_grid=dict(first_xz_m=context['first_xz_m'], spacing_m=context['spacing_m'], shape_zx=list(context['ocean_mask'].shape)),
        topology=context['topology'], solver=result['metadata'], budgets=result['budgets'], months=list(months),
        routes_file='routes.json', arrays=list(names), limitations=LIMITATIONS,
        boundary_note='Ocean actual wet-edge pressure 0m/reference SST engineering scenario, unlike closed climate moisture boundary',
        thermal_type='length-sampled native-supported SST minus same-latitude monthly reference; threshold +/-0.3 C',
        source_paths=dict(world=climate_metadata.get('source_product_path'), climate=None))
    write_json(root/'routes.json', dict(schema=SCHEMA, routes=routes))
    write_json(root/'manifest.json', manifest)
    (root/'README.md').write_text('# 洋流图独立情景\n\nTerragenesis 二阶段旋转上层海洋；CPU，一年12月，max_cycles=1。'
        '未长期收敛，不反馈气候，不改变原海岸或默认世界。\n\n'
        f"月份{list(months)}流线按 flow-to 顺序与箭头；暖/冷为相对同纬参考SST的异常（±0.3℃），灰为中性。"
        '原10km海mask逐段检查；40km split块保守关闭，损失水域见manifest。'
        '速度不用于航海估时。\n\n'+ '\n'.join('- '+item for item in LIMITATIONS)+'\n', encoding='utf-8')
    return manifest


def atlas_geometry(metadata, image_size, *, expected_environment=ENVIRONMENT_ID):
    """Use saved atlas frame metadata, never guessed offsets or rebuilt artwork."""
    if metadata['product']['identity'] != expected_environment:
        raise ValueError('Atlas environment identity differs')
    summary = metadata['files']['simple-atlas.png']['summary']
    margin, (width, height) = summary['margin_px'], summary['map_px']
    product = metadata['product']
    grid = dict(first_xz_m=product['first_sample_xz_m'], spacing_m=product['spacing_m'], shape_zx=product['shape_zx'])
    if image_size[0] != width+2*margin or image_size[1] < height+2*margin:
        raise ValueError('Atlas image size differs from saved frame')
    return dict(origin_px=[margin,margin], map_px=[width,height], grid=grid,
                reserved_boxes=[[v+margin for v in item['box_px']] for item in summary.get('decorations',[])])


def render(product, source, atlas_png, atlas_metadata, *, font_path=None):
    """Independent PIL RGBA overlay, natural-map composite and simple depth theme."""
    from PIL import Image, ImageDraw, ImageFont, ImageChops
    root = Path(product)
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    routes = json.loads((root/'routes.json').read_text(encoding='utf-8'))['routes']
    meta = json.loads(Path(atlas_metadata).read_text(encoding='utf-8'))
    base = Image.open(atlas_png).convert('RGBA')
    geometry = atlas_geometry(meta, base.size)
    if (manifest['source_ids']['world'] != source['source_identity']
            or meta['product']['source_identity'] != source['source_identity']
            or meta['climate_environment']['climate_identity'] != manifest['source_ids']['climate']):
        raise ValueError('Overlay/atlas/source/climate identities differ')
    grid = geometry['grid']
    if grid != manifest['native_grid']:
        raise ValueError('Overlay and atlas native grid differ')
    font_path = Path(font_path or 'C:/Windows/Fonts/msyh.ttc')
    if not font_path.is_file():
        raise FileNotFoundError('Supply a Chinese font with --font')
    font, small = ImageFont.truetype(str(font_path),22), ImageFont.truetype(str(font_path),19)
    origin, size = np.asarray(geometry['origin_px']), np.asarray(geometry['map_px'])
    edge = np.asarray(grid['first_xz_m'])-grid['spacing_m']/2
    extent = np.array(grid['shape_zx'][::-1])*grid['spacing_m']
    def pixel(points):
        return (origin+(np.asarray(points)-edge)/extent*size).tolist()
    def overlaps(box, boxes):
        return any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in boxes)
    colours = dict(warm=(183,63,50,235), cold=(38,98,169,235), neutral=(91,100,106,230), unclassified=(91,100,106,230))
    sea = Image.fromarray((source['ocean_mask']*255).astype('uint8')).resize(tuple(size), Image.Resampling.NEAREST)
    mask = Image.new('L',base.size,0)
    mask.paste(sea,tuple(origin))
    saved_context = dict(first_xz_m=manifest['macro_grid']['first_xz_m'],
        spacing_m=manifest['macro_grid']['spacing_m'], ocean_mask=np.load(root/'ocean_mask.npy'),
        ocean_boundary=dict(face_open_x=np.load(root/'face_open_x.npy'),face_open_z=np.load(root/'face_open_z.npy')))
    products = []
    for month in manifest['months']:
        lines = Image.new('RGBA',base.size,(0,0,0,0))
        draw = ImageDraw.Draw(lines)
        labels = []
        reserved = list(geometry['reserved_boxes'])
        for route in [r for r in routes if r['month'] == month]:
            points = route['coordinates_xz_m']
            if not all(segment_is_ocean(a,b,source,saved_context) for a,b in zip(points[:-1],points[1:])):
                raise ValueError('Saved route crosses original ocean support')
            pixels = pixel(points)
            colour = colours[route['type']]
            draw.line([tuple(p) for p in pixels],fill=(255,251,235,210),width=7)
            draw.line([tuple(p) for p in pixels],fill=colour,width=3)
            cumulative = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(pixels,axis=0),axis=1))]
            for distance in np.arange(55,cumulative[-1],150):
                i = min(len(pixels)-1,int(np.searchsorted(cumulative,distance)))
                a,b = np.asarray(pixels[max(0,i-3)]),np.asarray(pixels[i])
                d = b-a
                if np.linalg.norm(d) < 1:
                    continue
                d /= np.linalg.norm(d)
                normal = np.array([-d[1],d[0]])
                draw.polygon([tuple(b),tuple(b-11*d+5*normal),tuple(b-11*d-5*normal)],fill=colour)
            for fraction in (.5,.35,.65,.2,.8):
                p = pixels[int((len(pixels)-1)*fraction)]
                label = route['name']
                text_box = draw.textbbox((p[0]+8,p[1]-27),label,font=small)
                box = [text_box[0]-4,text_box[1]-3,text_box[2]+4,text_box[3]+3]
                # Labels require ocean clearance and may not obscure decorations/coast.
                if (box[0] < origin[0] or box[1] < origin[1] or box[2] >= origin[0]+size[0]
                        or box[3] >= origin[1]+size[1] or overlaps(box,reserved)):
                    continue
                crop_mask = mask.crop(tuple(map(int,box)))
                if crop_mask.getextrema() != (255,255):
                    continue
                labels.append((box,(p[0]+8,p[1]-27),label,colour))
                reserved.append(box)
                break
        # Symbol width may not spill over the original sea mask. Avoid source decorations.
        alpha = ImageChops.multiply(lines.getchannel('A'),mask)
        for box in geometry['reserved_boxes']:
            ImageDraw.Draw(alpha).rectangle(box,fill=0)
        lines.putalpha(alpha)
        draw = ImageDraw.Draw(lines)
        for box,position,label,colour in labels:
            draw.rounded_rectangle(box,radius=3,fill=(255,251,239,218))
            draw.text(position,label,font=small,fill=colour)
        # Footer is outside the map; no coast or artwork is changed for the key.
        y = int(origin[1]+size[1]+12)
        draw.rectangle((0,y-5,base.width,base.height),fill=(248,245,233,245))
        draw.text((30,y),f'{month}月 · 风生表层洋流 · 一年有限情景（未长期收敛）',font=font,fill=(40,49,54,255))
        draw.text((30,y+37),'红：偏暖 ≥ +0.3℃   蓝：偏冷 ≤ -0.3℃   灰：中性；相对同纬参考SST，不代表绝对水温',font=small,fill=(40,49,54,255))
        draw.text((30,y+68),'箭头为流向；40km上层海洋，原10km海岸校验；不反馈气候、不作真实航速',font=small,fill=(40,49,54,255))
        lines.save(root/f'overlay-month-{month:02d}.png')
        Image.alpha_composite(base,lines).convert('RGB').save(root/f'natural-map-month-{month:02d}.png')
        bed = np.asarray(source['elevation_m'])
        depth = np.clip(-bed/4500,0,1)
        rgb = np.empty(bed.shape+(3,),np.uint8)
        for channel,(light,dark) in enumerate(((211,111),(230,158),(235,185))):
            rgb[...,channel] = np.where(source['ocean_mask'],light+(dark-light)*depth,225-channel*7)
        theme = Image.new('RGBA',base.size,(248,245,233,255))
        theme.paste(Image.fromarray(rgb).resize(tuple(size),Image.Resampling.NEAREST),tuple(origin))
        Image.alpha_composite(theme,lines).convert('RGB').save(root/f'ocean-theme-month-{month:02d}.png')
        products.extend([f'overlay-month-{month:02d}.png',f'natural-map-month-{month:02d}.png',f'ocean-theme-month-{month:02d}.png'])
    manifest['render'] = dict(atlas_environment_identity=meta['product']['identity'], atlas_png=str(Path(atlas_png).resolve()),
        frame=geometry, outputs=products, font=str(font_path), coast='original native mask; no source coastline alteration')
    write_json(root/'manifest.json',manifest)
    return products
