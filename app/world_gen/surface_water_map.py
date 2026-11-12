"""Render-only monthly water on the existing atlas, never a terrain/source mutation.

Bed/ocean/biome remain the environment parent's arrays. Lake surfaces are actual
monthly inventory, NOT the parent's potential filled surface. River SVG bypasses
atlas drainage-area filtering; widths are symbols, not physical river widths.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from copy import deepcopy
from html import escape
import json
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from app.world_relief import atlas
from app.map_source import load_source
from app.world_gen.river_flow_network import symbol_width

SCHEMA = 'dream-monthly-surface-water-render-1'
STYLES = {
    'perennial': ('#2477ad', '', '本年全年有流'),
    'seasonal': ('#2477ad', '7 4', '本年季节性有流'),
    'intermittent': ('#84b9d4', '1 4', '本年间歇有流'),
    'dry_valley': ('#988574', '4 5', '本年候选干谷（默认不绘）'),
    'unknown_regime': ('#628fa9', '7 3 1 3', '本月有流，年内流态未知'),
    'spill': ('#459dcc', '', 'CSR示意输水，非物理河宽'),
}


@dataclass(frozen=True)
class SurfaceMonth:
    product: atlas.Product
    month: int
    segments: tuple
    provenance: dict


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('saved surface-water path outside product or missing')
    return path


def _digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _identity(meta):
    record = dict(arrays={}, metadata={k: v for k, v in meta.items() if k != 'identity'})
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _verified(root, relative, meta):
    path = _inside(root, relative)
    if _digest(path) != meta['files'].get(relative):
        raise ValueError('saved surface-water file hash differs')
    return path


def _array(root, descriptor, meta):
    path = _verified(root, descriptor['file'], meta)
    if descriptor.get('sha256') != meta['files'][descriptor['file']]:
        raise ValueError('saved surface-water descriptor hash differs')
    a = np.load(path, mmap_mode='r', allow_pickle=False)
    if list(a.shape) != descriptor['shape'] or str(a.dtype) != descriptor['dtype']:
        raise ValueError('saved surface-water array descriptor differs')
    return a


def _month_field(root, meta, name, month, shape):
    a = _array(root, meta['fields'][name], meta)
    try:
        if a.shape != (12,) + shape:
            raise ValueError('monthly surface-water grid differs')
        result = np.array(a[month - 1], copy=True)
        if not np.isfinite(result).all() or np.any(result < 0) and name != 'lake_stage_m':
            raise ValueError('invalid monthly surface-water values')
        return result
    finally:
        a._mmap.close()


def _flow_class(series, parameters):
    q = np.asarray([np.nan if v is None else v for v in series], float)
    if q.shape != (12,) or not np.isfinite(q).all():
        return 'unknown'
    count = int((q >= parameters['min_active_q_m3_s']).sum())
    return ('perennial' if count >= parameters['perennial_months'] else
            'seasonal' if count >= parameters['seasonal_months'] else
            'intermittent' if count else 'dry_valley')


def _segments(network, spills, month):
    """Coalesce same-class original edges; missing OTHER months is not missing current Q.

    One polyline per continuous same-class run keeps dash phase continuous. The
    run's median monthly Q selects its absolute-Q symbol; every edge Q is retained.
    No merge across dry/unknown edges, lake cuts, or a topological junction.
    """
    parents = {v['id']: v for v in network['vectors']}
    params = network['parameters']
    width_recipe = network.get('cartography', {}).get('symbol_width')
    result = []
    for segment in network['draw_segments'][month - 1]:
        parent = parents[segment['parent_id']]
        lookup = dict(zip(parent['edge_anchor_cells'], parent['edge_monthly_q_m3_s']))
        points = segment['points_xz_m']
        run = None
        for i, (cell, q) in enumerate(zip(segment['edge_anchor_cells'], segment['edge_q_m3_s'])):
            series = lookup[cell]
            current = series[month - 1]
            valid = (q is not None and np.isfinite(q) and q >= params['min_active_q_m3_s']
                     and current is not None and np.isfinite(current)
                     and current >= params['min_active_q_m3_s'])
            if not valid:
                run = None
                continue
            kind = _flow_class(series, params)
            if kind == 'unknown':
                kind = 'unknown_regime'
            if kind not in ('perennial', 'seasonal', 'intermittent', 'unknown_regime'):
                run = None
                continue
            if run is None or run['kind'] != kind:
                run = dict(id=segment['id'] + ':' + str(cell), kind=kind,
                    points_xz_m=[points[i]], edge_anchor_cells=[], edge_q_m3_s=[],
                    semantics='supplied hillslope receiver-edge monthly Q; finite-year class; absolute-Q symbol NOT physical width')
                result.append(run)
            run['points_xz_m'].append(points[i + 1])
            run['edge_anchor_cells'].append(cell)
            run['edge_q_m3_s'].append(float(current))
        # Width does not depend on other rivers or the selected map window.
    for run in result:
        run['q_m3_s'] = float(np.median(run['edge_q_m3_s']))
        run['width'] = symbol_width(run['q_m3_s'], width_recipe)
    for segment in spills[month - 1]:
        if segment['net_transferred_volume_m3'] <= 0:
            continue
        result.append(dict(id=segment['id'], kind='spill', points_xz_m=segment['points_xz_m'],
            width=.9, semantics=segment['path_semantics'],
            net_transferred_volume_m3=segment['net_transferred_volume_m3']))
    return tuple(result)


def _monthly_ice(p, ice_swe, sidecar, hydrology):
    """Use original verified regions.json density; no inversion from terminal H."""
    if p.ice_thickness is None:
        return dict(ice_thickness=None, ice_surface=None, ice_coverage=None)
    mask = np.isfinite(p.simulated_mask) & (p.simulated_mask > 0)
    h = np.array(p.ice_thickness, copy=True)
    if not mask.any():
        return dict(ice_thickness=h, ice_surface=p.ice_surface, ice_coverage=p.ice_coverage)
    if hydrology is None:
        raise ValueError('explicit original hydrology directory required for saved ice density')
    root = Path(hydrology).resolve()
    manifest = _json(root / 'manifest.json')
    binding = sidecar['binding']
    if (manifest.get('schema') != 'dream-climate-hydrology-year-1' or manifest.get('status') != 'complete'
            or manifest.get('identity') != binding['hydrology_identity']
            or any(manifest['binding'].get(k) != binding[k] for k in ('source_identity', 'climate_identity'))):
        raise ValueError('original hydrology identity/parent differs')
    if _identity(manifest) != manifest['identity']:
        raise ValueError('original hydrology manifest identity changed')
    path = _inside(root, 'regions.json')
    if _digest(path) != manifest['files']['regions.json']:
        raise ValueError('original hydrology regions hash differs')
    regions = _json(path)
    original = sidecar.get('original_hydrology_regions', [])
    if [r['binding'] for r in regions] != original or manifest['binding']['regions'] != original:
        raise ValueError('original hydrology region binding differs')
    covered = np.zeros(p.shape, bool)
    for region in regions:
        z0, x0, z1, x1 = region['binding']['window_zx']
        if not (0 <= z0 < z1 <= p.shape[0] and 0 <= x0 < x1 <= p.shape[1]):
            raise ValueError('invalid saved dynamic region window')
        rho = region['metadata']['parameters']['ice_density_kg_m3']
        if not np.isfinite(rho) or rho <= 0:
            raise ValueError('invalid saved dynamic ice density')
        sl = np.s_[z0:z1, x0:x1]
        active = mask[sl]
        if np.any(covered[sl] & active):
            raise ValueError('overlapping saved dynamic regions')
        patch = h[sl].copy()
        patch[active] = ice_swe[sl][active] / rho
        h[sl] = patch
        covered[sl] |= active
    if np.any(mask & ~covered):
        raise ValueError('dynamic support not covered by saved regions')
    surface = np.array(p.ice_surface, copy=True)
    surface[mask] = p.elevation[mask] + h[mask]
    coverage = np.array(p.ice_coverage, copy=True)
    coverage[mask] = h[mask] > 0
    return dict(ice_thickness=h, ice_surface=surface, ice_coverage=coverage)


def load_surface_product(environment, surface_water, month, *, expected_environment_identity,
                         expected_surface_identity, lake_display_min_depth_m=.1, hydrology=None,
                         river_display=None):
    """Load saved fields only. Returned Product retains its ORIGINAL source identity."""
    if type(month) is not int or not 1 <= month <= 12:
        raise ValueError('month must be 1..12')
    if not np.isfinite(lake_display_min_depth_m) or lake_display_min_depth_m < 0:
        raise ValueError('nonnegative display threshold required')
    env_root, root = Path(environment).resolve(), Path(surface_water).resolve()
    env, meta = _json(env_root / 'manifest.json'), _json(root / 'manifest.json')
    if (env.get('identity') != expected_environment_identity or meta.get('identity') != expected_surface_identity
            or meta.get('schema') != 'dream-climate-lake-year-1' or meta.get('status') != 'finite-year-surface-water'
            or not meta.get('publishable')):
        raise ValueError('explicit complete environment/surface-water identities required')
    if _identity(meta) != meta['identity']:
        raise ValueError('surface-water manifest identity changed')
    finite_csr = meta.get('backend') == 'tg-csr-reservoir-finite-conductance'
    if meta.get('backend') is not None and not finite_csr:
        raise ValueError('unsupported surface-water backend')
    if finite_csr:
        if (meta.get('geometry_version') != 'dream-csr-finite-conductance-1'
                or any(meta.get(key) is not False for key in
                       ('channel_q_available', 'hydraulic_ready', 'natural_outlet_verified'))):
            raise ValueError('finite CSR engineering policy differs')
        _verified(root, meta['face_ledger_file'], meta)
        if meta.get('topology_file') is not None:
            topology = _json(_verified(root, meta['topology_file'], meta))
            payload = {k: topology[k] for k in ('metadata','arrays','faces','engineering_boundaries')}
            payload['schema'] = 'td-original-bed-overflow-topology-v1'
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            if topology.get('identity_sha256') != digest or meta.get('geometry_identity') != digest:
                raise ValueError('finite CSR topology identity differs')
    binding, climate = meta['binding'], env['climate_environment']
    if any(binding.get(k) != climate.get(k) for k in ('source_identity', 'climate_identity', 'hydrology_identity')):
        raise ValueError('surface-water/environment parent binding differs')
    source = load_source('world-map-product', env_root, expected_identity=expected_environment_identity)
    p = atlas.product_from_source(source, env_root)
    if tuple(binding['shape_zx']) != p.shape:
        raise ValueError('surface-water/environment grid differs')
    depth = _month_field(root, meta, 'lake_depth_m', month, p.shape)
    stage = _month_field(root, meta, 'lake_stage_m', month, p.shape)
    wet = _month_field(root, meta, 'wet_mask', month, p.shape).astype(bool) & ~p.ocean
    if not np.allclose((stage - p.elevation)[wet], depth[wet], atol=.01, rtol=1e-6):
        raise ValueError('monthly lake depth/stage differs from environment bed')
    surface = np.where(wet, stage, p.elevation)
    snow = _month_field(root, meta, 'monthly_snow_swe_mm', month, p.shape)
    ice = _month_field(root, meta, 'monthly_ice_swe_mm', month, p.shape)
    ice_fields = _monthly_ice(p, ice, meta, hydrology)
    product = replace(p, lake_surface=surface, rivers=[], saved_discharge=None, saved_snow_swe=snow,
                      cache={}, environment_metadata=deepcopy(p.environment_metadata), **ice_fields)
    display_record = None
    if river_display is None:
        network = _json(_verified(root, meta['hillslope_draw_file'], meta))
    else:
        display_path = Path(river_display).resolve()
        display_record = _json(display_path)
        if (display_record.get('schema') != 'dream-river-display-sidecar-1'
                or display_record.get('identity') != _identity(display_record)):
            raise ValueError('river display identity differs')
        parent = display_record['binding']
        if (parent.get('surface_water_identity') != meta['identity']
                or parent.get('physical_source_identity') != binding['source_identity']
                or parent.get('environment_identity') != expected_environment_identity
                or parent.get('surface_manifest_sha256') != _digest(root / 'manifest.json')):
            raise ValueError('river display physical parent differs')
        for name, digest in parent['source_files'].items():
            if meta['files'].get(name) != digest:
                raise ValueError('river display source file binding differs')
            _verified(root, name, meta)
        network = display_record['network']
    spills = _json(_verified(root, meta['spill_routes_file'], meta))
    segments = _segments(network, spills, month)
    shallow = wet & (depth <= lake_display_min_depth_m)
    provenance = dict(schema=SCHEMA, environment_parent_identity=p.identity,
        surface_water_identity=meta['identity'], physical_source_identity=binding['source_identity'], month=month,
        source_identity_policy='original Product identity unchanged; render provenance is independent',
        lake_display_min_depth_m=float(lake_display_min_depth_m), lake_display_min_cells=1,
        wet_cells=int(wet.sum()), displayed_wet_cells=int((wet & ~shallow).sum()),
        shallow_wet_fraction=float(shallow.sum() / max(int(wet.sum()), 1)),
        wet_area_km2=float(wet.sum() * p.spacing**2 / 1e6),
        lake_scope='whole wet coarse cells, NOT subcell wet fraction or surveyed shoreline',
        snow_ice_scope='selected month saved SWE; dynamic H from verified original hydrology regions.json density; no ice solve',
        hydrology_identity=binding['hydrology_identity'],
        river_scope='finite supplied-year class; hillslope Q separate from schematic net spill; no old river fallback',
        terrain_scope='bed/ocean/biome unchanged; parent annual climate retained, not monthly vegetation',
        flow_segments=len(segments))
    if display_record is not None:
        provenance.update(river_display_identity=display_record['identity'],
            river_display_file=str(display_path), river_display_sha256=_digest(display_path),
            river_display_recipe=display_record['recipe'],
            river_display_binding=display_record['binding'])
    if finite_csr:
        provenance.update(backend=meta['backend'], geometry_version=meta['geometry_version'],
            splitting=meta.get('splitting'), lake_evaporation=meta.get('lake_evaporation'),
            hydraulic_ready=False, natural_outlet_verified=False,
            conductance_scope='finite engineering owner-face exchange; not instant equilibration or unique lake-interior channel Q')
    return SurfaceMonth(product, month, segments, provenance)


def water_svg(surface, view, margin):
    p = surface.product
    ex = p.first[0] - p.spacing / 2 + view.x0 * p.spacing
    ez = p.first[1] - p.spacing / 2 + view.z0 * p.spacing
    out = [f'<g id="monthly-water" transform="translate({margin},{margin})" clip-path="url(#map-clip)" fill="none">']
    for segment in surface.segments:
        points = np.asarray(segment['points_xz_m'], float)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError('invalid saved draw geometry')
        px = (points - [ex, ez]) / view.mpp
        colour, dash, _ = STYLES[segment['kind']]
        coordinates = ' '.join(f'{x:.3f},{y:.3f}' for x, y in px)
        out.append(f'<polyline data-flow-class="{segment["kind"]}" points="{coordinates}" '
                   f'stroke="{colour}" stroke-width="{segment["width"]}" stroke-dasharray="{dash}" '
                   f'stroke-linecap="round"><title>{escape(segment["semantics"])}</title></polyline>')
    out.append('</g>')
    return '\n'.join(out)


def compose_month(surface, layers, base_href):
    text = atlas.compose_html(layers, surface.product, base_href)
    overlay = water_svg(surface, layers.view, layers.margin)
    # Insert before the atlas frame so frame/decorations remain on top.
    token = '<g transform="translate(%d,%d)">' % (layers.margin, layers.margin)
    text = text.replace(token, overlay + '\n' + token, 1)
    text = text.replace('雪色=年末SWE库存；非永久冰', f'雪色=第{surface.month}月SWE库存；非永久冰')
    text = text.replace('岩色与雪色为显示近似', f'雪色=第{surface.month}月保存SWE；岩色为显示近似')
    legend = ' · '.join(label for _, _, label in STYLES.values())
    threshold = surface.provenance['lake_display_min_depth_m']
    return text.replace('</body>', '<div style="position:absolute;left:10px;bottom:4px;font:11px sans-serif;'
        'background:#fff9;padding:3px">' + escape(f'第{surface.month}月 · {legend} · 线宽按绝对月Q（参考1m³/s；1.1–3.8px图符，非物理河宽） · 湖面仅显示深度>{threshold:g}m粗格') + '</div></body>')


def render_months(environment, surface_water, out_dir, *, expected_environment_identity,
                   expected_surface_identity, months=(1, 7, 12), width=1800, screenshot=None, hydrology=None,
                   river_display=None):
    """Write new PNG/HTML/source JSON only; browser callback can be supplied by CLI."""
    if not 64 <= width <= 1800 or int(width) != width:
        raise ValueError('render width must be 64..1800')
    out = Path(out_dir).resolve()
    parents = [Path(environment).resolve(), Path(surface_water).resolve()]
    if hydrology is not None:
        parents.append(Path(hydrology).resolve())
    for parent in parents:
        if out == parent or out.is_relative_to(parent):
            raise ValueError('render output must be outside immutable parents')
    if out.exists():
        raise FileExistsError('new render directory required')
    out.mkdir(parents=True)
    records = []
    for month in months:
        surface = load_surface_product(environment, surface_water, month,
            expected_environment_identity=expected_environment_identity, expected_surface_identity=expected_surface_identity,
            hydrology=hydrology, river_display=river_display)
        params = replace(atlas.AtlasParams(width_px=width), lake_min_depth_m=.1, lake_min_cells=1)
        layers = atlas.build_atlas(surface.product, params, title=f'实际月湖河 · 第{month}月',
            subtitle='保存月水账 · 有限首年 · 图符河宽非物理河宽', deco_kind='none')
        base = out / f'month-{month:02d}-base.png'
        Image.fromarray(layers.page_rgb).save(base)
        html = out / f'month-{month:02d}.html'
        html.write_text(compose_month(surface, layers, base.name), encoding='utf-8')
        if screenshot is not None:
            screenshot(html, out / f'month-{month:02d}.png', *atlas.page_size(layers))
        image_size = list(atlas.page_size(layers))
        view = layers.view
        x0 = surface.product.first[0] + (view.x0 - .5) * surface.product.spacing
        z0 = surface.product.first[1] + (view.z0 - .5) * surface.product.spacing
        record = dict(surface.provenance, source_identity=surface.product.identity, width_px=width, html=html.name,
            image=f'month-{month:02d}.png' if screenshot is not None else None,
            image_size=image_size,
            map_rect=dict(x=layers.margin, y=layers.margin, width=view.width, height=view.height),
            world_extent_m=[x0, z0, x0 + view.nx * view.spacing, z0 + view.nz * view.spacing])
        if screenshot is not None:
            image = out / record['image']
            with Image.open(image) as saved_image:
                if list(saved_image.size) != image_size:
                    raise ValueError('saved preview image size differs from atlas page')
            record['image_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
        (out / f'month-{month:02d}-source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        records.append(record)
    (out / 'surface-water-source.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    return records
