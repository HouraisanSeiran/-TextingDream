"""Generate candidate encyclopedia entries from town art metadata (no art writes)."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = Path('app/static/map-art/town')
OUTPUT = Path('docs/human-encyclopedia/town-buildings.json')
NAMESPACE = 'town-buildings'
STYLE_NAMES = {'west': '西式', 'east': '东方', 'arab': '阿拉伯'}
RACE_NAMES = {'human': '人族', 'elf': '精灵', 'dwarf': '矮人', 'orc': '兽人'}
# Metadata with Chinese names takes precedence; these cover unnamed art kinds.
KIND_NAMES = {
    'keep_square': '方形城堡主楼', 'keep_round': '圆形城堡主楼',
    'great_hall': '城堡大厅', 'chapel': '礼拜堂', 'barracks': '兵营',
    'kitchen': '城堡厨房', 'granary_raised': '架空粮仓',
    'stable_leanto': '贴墙马厩', 'forge_leanto': '铁匠棚',
    'well_windlass': '辘轳井', 'tower_round': '圆塔', 'tower_square': '方塔',
    'gatehouse': '城门楼', 'drawbridge': '吊桥', 'castle_wall': '石砌幕墙',
    'moat': '护城河', 'yard_flagstone': '内院石板地',
    'smelter_blast': '高炉冶炼坊', 'smelter_earthen': '土炉冶炼坊',
    'dock_pier': '栈桥码头', 'dock_steps': '石阶码头',
    'kiln_beehive': '蜂窝窑', 'kiln_bottle': '瓶形窑', 'kiln_dragon': '龙窑',
    'tannery_yard': '制革院', 'dyehouse_cloth': '染布坊',
    'mine_headframe': '矿井井架', 'mine_adit': '矿道口',
    'boiler_steam': '蒸汽锅炉房', 'boiler_bronze': '铜炉动力房',
    'ward_mage_tower': '法师防护塔', 'ward_pagoda': '镇护宝塔',
    'warehouse_gable_hoist': '山墙吊货仓库', 'warehouse_stone_dock': '石砌码头仓库',
    'depot_two_storey': '双层货栈', 'cemetery_churchyard': '教堂墓园',
    'graveyard_charity': '义冢', 'bridge_stone_arch': '石拱桥',
    'bridge_timber_trestle': '木栈桥', 'bridge_hump_arch': '拱背石桥',
    'bridge_covered': '廊桥', 'wall_spoke': '辐条城墙', 'wall_node': '城墙节点',
    'wall_tower_canopy': '树冠哨塔', 'vine_outpost': '藤木哨台',
    'bastion': '棱堡', 'ravelin': '半月堡', 'starfort': '星堡',
    'star_fort': '星堡', 'mamian': '马面', 'wengcheng': '瓮城',
    'wallspoke': '辐条城墙', 'wallnode': '城墙节点', 'mountain_keep': '山体堡垒主楼',
    'earthwork': '土垒工事', 'wall_tower_totem': '图腾哨塔',
    'stone_bastion': '石砌棱堡', 'terraced_mountain_city': '梯台山城',
    'canopy_fortress': '树冠要塞', 'thorn_bastion': '荆棘棱垒',
    'stake_warcamp': '尖桩战营',
}
CATEGORY_NAMES = {
    'house': '民居', 'special': '公共设施', 'road': '道路铺面',
    'wall': '城防构件', 'castle': '城堡构件', 'prop': '街区摆件',
    'water': '水岸瓦片', 'ground': '地面底纹', 'fort': '防御工事',
    'landmark': '文化地标', 'site': '资源点建筑',
}
PLACEMENTS = {
    'house': '居住街区或农家院落，入口朝向通行空间',
    'special': '公共服务或商贸街区，按具体设施保留出入口和作业空间',
    'road': '街巷或院坪的地面层，按相邻格连接关系铺设',
    'wall': '城镇边界或堡垒周界，与墙段、节点、城门共同拼装',
    'castle': '城堡内院或防御周界，注意墙体遮挡和门桥对接',
    'prop': '街边、庭院或对应作业区，不阻塞主要通路',
    'water': '河道、港池或水岸边缘的地面层',
    'ground': '院坪、空地或作业区的地面层',
    'fort': '城防周界及城门外防御带，按部件朝向拼装',
    'landmark': '文化礼仪街区或专用地标地块，预留大体量占地',
    'site': '城镇外独立资源点的小地图，按资源条件选择位置',
}
ROOF_NAMES = {
    'flat_mud': '平顶近似', 'gable_thatch': '双坡茅草顶近似',
    'gable_tile': '双坡瓦顶近似', 'steep_slate': '陡坡石板顶近似',
    'hip_tile': '四坡瓦顶近似', 'monopitch': '单坡顶近似',
    'none': '无对应屋顶或非屋顶构件',
}


def _source(source_id, path):
    return {
        'id': source_id, 'title': f'织梦城镇建筑设计资料：{path.as_posix()}',
        'url': path.as_posix(), 'access': 'read',
        'supports': '项目素材的形制、字段和拼装约定；只代表已读取本地设计资料，非历史事实核实。',
        'rights_note': '项目内部设计文档；记录路径，不复制或授权第三方参考图像。',
    }


def _name(rows, kind, category, warn):
    for field in ('name_zh', 'name'):
        for row in rows:
            value = row.get(field)
            if value and re.search(r'[\u3400-\u9fff]', value):
                # Strip variant labels, not meaningful kind distinctions in payload.
                value = re.sub(r'(?:·|\s+)\d+$', '', value).strip()
                return re.split(r'[·（(]', value)[0].strip() if len(rows) > 1 else value
    if kind in KIND_NAMES:
        return KIND_NAMES[kind]
    warn(f'未命名 kind={kind}，暂用类别中文名；请在 KIND_NAMES 补充。')
    return CATEGORY_NAMES[category]


def _values(rows, field):
    return sorted({row[field] for row in rows if row.get(field)})


def _element(key, records, warn, readme_dirs):
    style, race, kind = key
    records.sort(key=lambda pair: pair[1]['id'])
    rows = [row for _, row in records]
    categories = _values(rows, 'category')
    category = categories[0]
    base_name = _name(rows, kind, category, warn)
    race_name = RACE_NAMES[race]
    name = STYLE_NAMES[style] + ('' if base_name.startswith(race_name) else race_name) + base_name
    facilities = _values(rows, 'facility')
    tags = {f'style:{style}', f'race:{race}', 'town_art'}
    for field in ('category', 'facility', 'culture', 'resource'):
        tags.update(f'{field}:{value}' for value in _values(rows, field))
    footprints = sorted({tuple(row['footprint']) for row in rows})
    dimensions = '、'.join('×'.join(map(str, size)) for size in footprints)
    roofs = '、'.join(ROOF_NAMES.get(value, '自定义屋顶（见变体元数据）')
                     for value in _values(rows, 'roof')) or '元数据未指定屋顶'
    aliases = {base_name}
    for row in rows:
        aliases.update(value for field in ('name_zh', 'name') if (value := row.get(field)))
    if any('forge' in value for value in [kind, *facilities]):
        aliases.add('铁匠铺')
    placements = '；'.join(PLACEMENTS[value] for value in categories)
    sources = ['town_buildings_src_spec'] + sorted({
        'town_buildings_src_' + directory.replace('-', '_') for directory, _ in records
        if directory in readme_dirs})
    return {
        'id': f'town_buildings_{style}_{race}_{kind.replace("-", "_")}',
        'name': name, 'aliases': sorted(aliases - {name}), 'tags': sorted(tags),
        'summary': f'{name}：{CATEGORY_NAMES[category]}美术类型，含 {len(rows)} 个变体。',
        'details': {
            'definition': f'{name}是城镇地图的{CATEGORY_NAMES[category]}设计类型；同类型变体合并登记，不是独立规则或历史断言。',
            'mechanism': f'采用3/4斜俯视与48像素地面格；占地有{dimensions}格。屋顶标记：{roofs}。具体造型、朝向及附件见art_variants。',
            'conditions': f'建议放置：{placements}。设施映射为{ "、".join(facilities) or "未指定" }；仅沿用元数据，不推导产能、人口或资源库存。',
            'exceptions': '同一类型的占地、屋顶与设施映射可能因变体不同；透明空瓦片也保留用于拼装。facility为空不表示自动获得某项服务。',
            'story_uses': f'可作为{base_name}相关场景的可视定位和街区布置候选；作者须另定人物、事件、使用权限与运行规则。',
            'historical_scope': '这是织梦项目的美术与关卡设计约定；东西风格和种族均为游戏分类，不据此断言现实建筑的年代、地域或文化归属。',
            'evidence_and_uncertainty': '来源为项目规范、目录说明与meta.json；仅支撑素材登记。原note保留在art_variants，形制参考和已知限制须人工审阅，未进行史实核验或美术验收。',
        },
        'source_ids': sources, 'related_ids': [], 'review_status': 'needs_review',
        'detail_status': 'needs_detail', 'art_symbols': [row['id'] for row in rows],
        'footprint': [list(size) for size in footprints], 'facility': facilities,
        'art_variants': [{'directory': directory, **row} for directory, row in records],
    }


def generate_document(root=ROOT, *, warn=print):
    """Read completed metadata directories; retain all symbols, including empty tiles."""
    root = Path(root)
    groups = defaultdict(list)
    sources = [_source('town_buildings_src_spec', Path('docs/town-art-spec.md'))]
    readme_dirs = set()
    seen = set()
    for directory in sorted((root / ART_ROOT).iterdir()):
        if not directory.is_dir():
            continue
        meta = directory / 'meta.json'
        if not meta.exists():
            warn(f'跳过 {directory.name}：缺少 meta.json')
            continue
        rows = json.loads(meta.read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list):
            raise ValueError(f'{meta}: expected an array')
        readme = directory / 'README.md'
        if readme.exists():
            readme.read_text(encoding='utf-8-sig')
            readme_dirs.add(directory.name)
            sources.append(_source('town_buildings_src_' + directory.name.replace('-', '_'),
                                   readme.relative_to(root)))
        else:
            warn(f'{directory.name} 缺少 README.md，仅引用项目规范和元数据。')
        for row in rows:
            if row['id'] in seen:
                raise ValueError(f'duplicate art symbol: {row["id"]}')
            seen.add(row['id'])
            race = 'human' if row['race'] == 'common' else row['race']
            key = (row['style'], race, row['kind'])
            groups[key].append((directory.name, row))
    elements = [_element(key, records, warn, readme_dirs)
                for key, records in sorted(groups.items())]
    document = {'schema_version': 1, 'group': NAMESPACE, 'status': 'candidate',
                'sources': sources, 'elements': elements}
    from app.encyclopedia import prepare_document
    prepare_document(document)
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / OUTPUT)
    args = parser.parse_args(argv)
    document = generate_document()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Stream small chunks rather than constructing one large serialized document.
    with args.out.open('w', encoding='utf-8', newline='\n') as stream:
        for chunk in json.JSONEncoder(ensure_ascii=False, indent=2).iterencode(document):
            stream.write(chunk)
        stream.write('\n')
    count = sum(len(element['art_symbols']) for element in document['elements'])
    print(f'{args.out}: {len(document["elements"])} 条元素，{count} 个 symbol')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
