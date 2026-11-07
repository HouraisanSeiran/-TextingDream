"""Author-only bridge from validated town snapshots to existing local art layouts.

No writes, model calls, economic ticks or world-coordinate assumptions. Preview
options are explicit and exportable; they do not mutate a published town version.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import towns
from .town_layout import layout, load_catalog, site_layout
from .town_schema import TownSnapshot
from .towns_store import content_hash

GENERATOR = 'town-plan-v1'


class PlanOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')

    style: Literal['auto', 'west', 'east', 'arab'] = 'auto'
    race: Literal['common', 'elf', 'dwarf', 'orc'] = 'common'
    wall_shape: Literal['irregular', 'square'] = 'irregular'
    fortification: Literal['auto', 'none', 'light', 'normal', 'heavy'] = 'auto'
    seed: str | None = Field(default=None, min_length=1, max_length=64)
    landmarks: int | None = Field(default=None, ge=0, le=2, strict=True)


REASONS = {
    'asset': '缺少对应主体素材', 'space': '没有满足占地与通路条件的位置',
    'no_water': '当前地形没有可用水域', 'unwalled': '当前布局无法形成城墙',
    'racial_fallback': '使用西式人族替代素材',
    'style_fallback': '使用其他文化的资源点素材',
    'subtype_fallback': '使用其他资源子类型素材',
    'ground_asset': '缺少专用资源地面', 'prop_asset': '缺少专用资源摆件',
    'tile_asset': '缺少道路或地面拼接瓦片', 'wall_asset': '缺少城墙拼接素材',
    'water_asset': '缺少水岸拼接瓦片', 'wall_terrain': '地形无法容纳闭合城墙，改用开放聚落',
    'culture_fallback': '当前文化没有该种族变体，使用通用素材',
    'moat_asset': '缺少护城河拼接素材', 'fort_asset': '缺少适配当前城墙的工事素材',
    'fortification_unavailable': '附加工事需要闭合城墙，当前聚落为开放布局',
    'landmark_space': '地标未全部放置，缺少满足占地与通路条件的位置或对应素材',
}
RESOURCE_NAMES = {
    'grain': '粮田', 'timber': '伐木场', 'stone': '采石场', 'clay': '黏土坑',
    'iron': '铁矿', 'copper': '铜矿', 'tin': '锡矿', 'coal': '煤场', 'salt': '盐场',
    'livestock': '牧场', 'fish': '渔场', 'herb': '药圃', 'wool': '羊毛牧场',
    'gold': '金矿', 'rare_metals': '稀有金属矿', 'reed': '芦苇场',
}


def _diagnostics(plan):
    return [dict(row, message=REASONS.get(row['reason'], row.get('note') or row['reason']))
            for row in plan['missing']]


def generate_plan(snapshot, options=None, *, catalog=None):
    """Validate the complete snapshot, then account for every authored facility.

    HTTP accepts only bounded options, never arbitrary terrain sizes or catalogs.
    Resource eligibility uses the same fuel/technology closure as rule generation.
    """
    snapshot = TownSnapshot.model_validate(snapshot).model_dump(mode='json')
    towns.validate_snapshot(snapshot)
    options = options if isinstance(options, PlanOptions) else PlanOptions.model_validate(options or {})
    catalog = catalog if catalog is not None else load_catalog()
    roof = snapshot['built']['style']['roof']
    style = options.style
    if style == 'auto':
        style = {'flat_mud': 'arab', 'hip_tile': 'east'}.get(roof, 'west')
    seed = options.seed if options.seed is not None else snapshot['seed']
    plan = layout(snapshot, style=style, race=options.race, seed=seed, catalog=catalog,
                  wall_shape=options.wall_shape, landmarks=options.landmarks,
                  fortification=None if options.fortification == 'auto' else options.fortification)
    if plan['race'] != options.race:
        plan['missing'].append({'reason': 'culture_fallback', 'note': f'{style} / {options.race} → common'})
    if options.fortification not in ('auto', 'none') and not plan['grid']['walled']:
        plan['missing'].append({'reason': 'fortification_unavailable'})
    if options.landmarks is not None and len(plan['landmarks']) < options.landmarks:
        plan['missing'].append({'reason': 'landmark_space'})
    by_source = {b['source']: b for b in plan['buildings'] + plan['infrastructure'] if b.get('source')}
    missing = {m['source']: m for m in plan['missing'] if m.get('source')}
    coverage = []
    for facility in snapshot['built']['facilities']:
        source = facility['id']
        placed = by_source.get(source)
        issue = missing.get(source)
        coverage.append({'source': source, 'name': facility['name'], 'facility': facility['kind'],
                         'status': 'placed' if placed else 'unplaced',
                         'art_id': placed['id'] if placed else None,
                         'cell': placed.get('cell') if placed else None,
                         'footprint': placed.get('footprint') if placed else None,
                         'reason': issue['reason'] if issue else None})
    names = {f['id']: f['name'] for f in snapshot['built']['facilities']}
    for item in plan['items']:
        if item.get('source') in names:
            item['name'] = names[item['source']]
    sites = []
    entry = snapshot['input']
    for candidate in entry['resources']:
        if not towns.gated_resource(candidate, entry):
            continue
        resource = candidate['kind']
        local = site_layout(resource, style=style, seed=seed + ':' + candidate['id'], catalog=catalog)
        sites.append({'source': candidate['id'], 'resource': resource,
                      'name': RESOURCE_NAMES[resource], 'layout': local,
                      'diagnostics': _diagnostics(local)})
    return {
        'generator_version': GENERATOR, 'town_id': snapshot['town_id'],
        'name': snapshot['skeleton']['display_name'], 'snapshot_hash': content_hash(snapshot),
        'options': options.model_dump(mode='json'),
        'resolved': {'style': plan['style'], 'race': plan['race'], 'seed': seed,
                     'wall_shape': plan['grid']['wall_shape'], 'fortification': plan['fortification']},
        'layout': plan, 'facilities': coverage, 'diagnostics': _diagnostics(plan),
        'resource_sites': sites,
        'summary': {'facilities': len(coverage),
                    'placed': sum(row['status'] == 'placed' for row in coverage),
                    'houses': sum(b['facility'] is None for b in plan['buildings']),
                    'reference_houses': snapshot['built']['housing']['total_houses'],
                    'resource_sites': len(sites)},
        'note': '局部示意布局；民居图标与资源地块不等于人口、实测面积或产量。经营参数尚未标定。',
    }
