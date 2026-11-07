# -*- coding: utf-8 -*-
"""建筑经营接口（预设，尚未接入游戏）。

给之后的模拟经营系统预留的数据契约：每种建筑「是什么角色、开采或加工什么、
吃进什么、产出什么、要几个人、要什么技术」。本模块**不做任何模拟**：

* 不被 ``runtime`` / ``web`` 导入，不参与 app 启动，不改存档、城镇生成器或美术素材。
* 所有数量都是**设计占位值**（``calibrated=False``），只用来让接口有形状；
  正式数值等经营系统定稿时由作者校准，不能拿来当真实产量。
* 资源点的「资源潜力」仍由 ``town_schema.ResourceCandidate`` 决定（勘测、可开采、
  技术、燃料），本模块不改变那套判定，只说明「若要开采，用哪种建筑」。

查找顺序（``profile_for(meta)``，meta 是美术 ``meta.json`` 的一项）：
1. 资源点 ``category == 'site'``：按 ``(resource, subtype)``，再退到 ``(resource, None)``；
2. 有 ``facility`` 的建筑：按 FacilityKind；
3. 民居：``residence``；道路、城墙、地面、摆件等：``None``（不参与经营）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol

# --- 资源与设施枚举（与 town_schema.py、manifest.json trade_kinds、规范第 16 节对齐） ---
BASE_RESOURCES = ('grain', 'timber', 'stone', 'clay', 'iron', 'copper', 'tin', 'coal', 'salt',
                  'livestock', 'fish', 'herb', 'wool', 'gold', 'rare_metals', 'reed')
TRADE_RESOURCES = ('silver', 'gems', 'marble', 'sulfur', 'spices', 'silk', 'horses', 'ivory',
                   'amber', 'pearls', 'wine', 'dye', 'mana', 'dragonbone', 'lapis')
RESOURCES = BASE_RESOURCES + TRADE_RESOURCES
FANTASY_RESOURCES = ('mana', 'dragonbone')   # 只有世界设定声明时才出现

FACILITIES = ('town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill',
              'forge', 'smelter', 'kiln', 'tannery', 'barracks', 'watchtower', 'city_wall',
              'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock',
              'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge')

ROLES = ('extract', 'farm', 'process', 'store', 'trade', 'service', 'admin', 'defense',
         'residence', 'infrastructure')

# --- 货物 ---
GOODS = {
    # 农牧
    'wheat': '小麦', 'rice': '稻米', 'millet': '粟黍', 'vegetables': '蔬菜', 'fruit': '水果',
    'olives': '橄榄', 'olive_oil': '橄榄油', 'flax': '亚麻 / 苎麻', 'cotton': '棉花',
    'cattle': '牛', 'milk': '奶', 'cheese': '奶酪', 'pork': '猪肉', 'goat': '山羊',
    'poultry': '禽', 'eggs': '蛋', 'honey': '蜂蜜', 'wax': '蜂蜡', 'wool': '羊毛',
    'horses': '马', 'hides': '生皮', 'fodder': '草料', 'herbs': '草药', 'tea': '茶',
    'spices': '香料', 'cocoons': '蚕茧', 'grapes': '葡萄', 'fish': '鱼', 'reed': '芦苇',
    # 林矿
    'logs': '原木', 'planks': '木板', 'charcoal': '木炭', 'stone': '石料', 'marble': '大理石',
    'clay': '黏土', 'iron_ore': '铁矿石', 'copper_ore': '铜矿石', 'tin_ore': '锡矿石',
    'gold_ore': '金矿砂', 'silver_ore': '银矿石', 'rare_ore': '稀有金属矿', 'coal': '煤',
    'salt': '盐', 'brine': '卤水', 'sulfur': '硫磺', 'gems': '宝石原料', 'amber': '琥珀',
    'lapis': '青金石', 'pearls': '珍珠', 'ivory': '象牙', 'dye_plants': '染料作物',
    'mana_crystal': '魔力晶块', 'dragonbone': '龙骨',
    # 加工品
    'flour': '面粉', 'bread': '面包', 'wine': '酒', 'iron': '铁锭', 'bronze': '青铜',
    'gold': '金锭', 'silver': '银锭', 'tools': '工具', 'weapons': '兵器', 'bricks': '砖',
    'pottery': '陶器', 'leather': '皮革', 'cloth': '布', 'silk': '丝', 'dye': '染料',
    'medicine': '药材', 'jewelry': '首饰', 'pigment': '颜料',
    # 抽象量
    'labor': '劳力', 'fuel': '燃料', 'water': '水', 'coin': '钱', 'food': '口粮',
}


@dataclass(frozen=True)
class Flow:
    """一条物流：每**天**多少单位。单位由货物自身约定，接口不换算。"""
    good: str
    per_day: float


@dataclass(frozen=True)
class EconomyProfile:
    id: str
    name_zh: str
    role: str
    resource: Optional[str] = None          # 开采 / 种养的资源（RESOURCES）
    subtype: Optional[str] = None           # 规范第 16.2 节
    facility: Optional[str] = None          # FacilityKind
    inputs: tuple[Flow, ...] = ()
    outputs: tuple[Flow, ...] = ()
    workers: int = 0
    storage: tuple[tuple[str, int], ...] = ()
    requires_tech: tuple[str, ...] = ()     # town_schema.TechId
    fuel: Optional[str] = None              # ResourceCandidate.fuel 的取值
    upkeep_coin: float = 0.0
    calibrated: bool = False                # 占位值，没校准
    note: str = ''


class EconomySimulator(Protocol):
    """经营系统将来要实现的接口；本模块只声明，不实现。"""

    def production(self, building: dict, profile: EconomyProfile, state: dict) -> dict:
        """单座建筑这一时段的实际产出（受人手、库存、技术、资源潜力限制）。"""

    def tick(self, town_state: dict, hours: float) -> dict:
        """推进一个城镇的经营状态，返回新的状态（不改入参）。"""


def _f(spec):
    """'iron_ore:4,labor:2' → (Flow, ...)。"""
    if not spec:
        return ()
    out = []
    for part in spec.split(','):
        good, qty = part.split(':')
        out.append(Flow(good.strip(), float(qty)))
    return tuple(out)


def _p(pid, name, role, out='', inp='', workers=2, resource=None, subtype=None, facility=None,
       tech=(), fuel=None, upkeep=0.0, note=''):
    return EconomyProfile(id=pid, name_zh=name, role=role, resource=resource, subtype=subtype,
                          facility=facility, inputs=_f(inp), outputs=_f(out), workers=workers,
                          requires_tech=tuple(tech), fuel=fuel, upkeep_coin=upkeep, note=note)


# --- 资源点：每种资源至少一种开采 / 种养建筑；(resource, subtype) → profile ---
_SITES = [
    _p('lumber_camp', '伐木场', 'extract', 'logs:6', workers=4, resource='timber'),
    _p('quarry', '采石场', 'extract', 'stone:5', 'tools:0.05', 4, 'stone'),
    _p('marble_quarry', '大理石采场', 'extract', 'marble:2', 'tools:0.08', 5, 'marble', tech=('masonry',)),
    _p('clay_pit', '取土坑', 'extract', 'clay:6', workers=3, resource='clay'),
    _p('iron_mine', '铁矿', 'extract', 'iron_ore:4', 'tools:0.1,food:3', 6, 'iron', tech=('mine_shaft',)),
    _p('copper_mine', '铜矿', 'extract', 'copper_ore:3', 'tools:0.1,food:3', 6, 'copper', tech=('mine_shaft',)),
    _p('tin_mine', '锡矿', 'extract', 'tin_ore:2', 'tools:0.08,food:2', 5, 'tin'),
    _p('coal_mine', '煤矿', 'extract', 'coal:6', 'tools:0.1,food:3', 6, 'coal', tech=('mine_shaft',)),
    _p('gold_mine', '金矿 / 淘金场', 'extract', 'gold_ore:0.5', 'tools:0.05,food:2', 5, 'gold'),
    _p('silver_mine', '银矿', 'extract', 'silver_ore:1', 'tools:0.08,food:2', 5, 'silver', tech=('mine_shaft',)),
    _p('rare_metal_mine', '稀有金属矿', 'extract', 'rare_ore:0.3', 'tools:0.1,food:2', 5, 'rare_metals',
       tech=('mine_shaft',)),
    _p('lapis_mine', '青金石矿', 'extract', 'lapis:0.4', 'tools:0.08,food:2', 5, 'lapis',
       note='青金石原石；磨成颜料要另设加工'),
    _p('gem_pit', '宝石矿坑', 'extract', 'gems:0.3', 'tools:0.05,food:2', 4, 'gems'),
    _p('amber_dig', '琥珀挖掘', 'extract', 'amber:0.3', workers=3, resource='amber'),
    _p('sulfur_pit', '硫磺坑', 'extract', 'sulfur:2', 'tools:0.05', 3, 'sulfur'),
    _p('salt_works', '盐场', 'extract', 'salt:4', 'fuel:2', 4, 'salt', fuel='timber',
       note='海盐晒场可免燃料；熬盐与井盐要燃料'),
    _p('fishery', '渔场', 'extract', 'fish:5', workers=4, resource='fish'),
    _p('reed_bed', '芦苇荡', 'extract', 'reed:6', workers=2, resource='reed'),
    _p('pearl_bed', '采珠场', 'extract', 'pearls:0.1', 'food:2', 4, 'pearls'),
    _p('ivory_hunt', '象牙收购站', 'extract', 'ivory:0.1', 'food:2', 3, 'ivory',
       note='占位：素材未画'),
    _p('mana_vein', '魔力晶矿', 'extract', 'mana_crystal:0.5', 'tools:0.1', 4, 'mana', tech=('arcane_ward',)),
    _p('dragon_dig', '龙骨发掘场', 'extract', 'dragonbone:0.1', 'tools:0.1,food:3', 6, 'dragonbone'),
    _p('herb_garden', '药草园', 'farm', 'herbs:2', workers=2, resource='herb'),
    _p('tea_garden', '茶园', 'farm', 'tea:1.5', workers=3, resource='herb', subtype='tea_garden'),
    _p('spice_garden', '香料园', 'farm', 'spices:1', workers=3, resource='spices'),
    _p('sericulture', '蚕桑', 'farm', 'cocoons:1', 'food:1', 3, 'silk'),
    _p('dye_farm', '染料作物田', 'farm', 'dye_plants:2', workers=2, resource='dye'),
    _p('vineyard', '葡萄园', 'farm', 'grapes:4', workers=3, resource='wine'),
    # 农田细分（规范 16.2）
    _p('wheat_farm', '麦田农庄', 'farm', 'wheat:8', workers=4, resource='grain', subtype='wheat_farm'),
    _p('rice_paddy', '水稻田', 'farm', 'rice:9', 'water:6', 5, 'grain', 'rice_paddy'),
    _p('millet_farm', '粟黍旱田', 'farm', 'millet:6', workers=3, resource='grain', subtype='millet_farm'),
    _p('vegetable_farm', '菜园', 'farm', 'vegetables:6', 'water:2', 3, 'grain', 'vegetable_farm'),
    _p('orchard', '果园', 'farm', 'fruit:5', workers=3, resource='grain', subtype='orchard'),
    _p('olive_grove', '橄榄园', 'farm', 'olives:4', workers=3, resource='grain', subtype='olive_grove'),
    _p('flax_farm', '亚麻 / 麻田', 'farm', 'flax:3', workers=3, resource='grain', subtype='flax_farm'),
    _p('cotton_farm', '棉田', 'farm', 'cotton:3', 'water:2', 4, 'grain', 'cotton_farm'),
    # 牧场细分
    _p('cattle_ranch', '牛场', 'farm', 'cattle:0.3,hides:0.3', 'fodder:6', 3, 'livestock', 'cattle_ranch'),
    _p('dairy_farm', '奶牛场', 'farm', 'milk:6', 'fodder:6', 3, 'livestock', 'dairy_farm'),
    _p('pig_farm', '猪圈', 'farm', 'pork:2', 'food:2', 2, 'livestock', 'pig_farm'),
    _p('goat_farm', '山羊场', 'farm', 'goat:0.3,milk:2', 'fodder:3', 2, 'livestock', 'goat_farm'),
    _p('poultry_farm', '鸡鸭场', 'farm', 'eggs:20,poultry:1', 'food:1', 2, 'livestock', 'poultry_farm'),
    _p('apiary', '养蜂场', 'farm', 'honey:1,wax:0.2', workers=1, resource='livestock', subtype='apiary'),
    _p('sheep_station', '羊场', 'farm', 'wool:2', 'fodder:4', 3, 'wool', 'sheep_station'),
    _p('horse_stud', '种马场', 'farm', 'horses:0.05', 'fodder:8', 4, 'horses', 'horse_stud', facility='stable'),
]
# 没细分时的退路
_SITES += [
    _p('grain_farm', '农田', 'farm', 'wheat:6', workers=4, resource='grain'),
    _p('pasture', '牧场', 'farm', 'cattle:0.2,hides:0.2', 'fodder:5', 3, 'livestock'),
]
SITE_PROFILES = {(p.resource, p.subtype): p for p in _SITES}

# --- 城镇设施：28 种 FacilityKind 全覆盖 ---
_FAC = [
    _p('town_hall', '行政厅', 'admin', 'coin:4', workers=4, upkeep=2),
    _p('lord_hall', '领主府', 'admin', 'coin:6', 'food:4', 6, upkeep=4),
    _p('market_hall', '市集', 'trade', 'coin:5', workers=3),
    _p('granary', '粮仓', 'store', workers=1, note='库存见 storage'),
    _p('cistern', '蓄水池', 'infrastructure', 'water:30', workers=1),
    _p('well', '水井', 'infrastructure', 'water:10', workers=0),
    _p('mill', '磨坊', 'process', 'flour:6', 'wheat:7', 2, tech=('water_wheel',)),
    _p('forge', '铁匠铺', 'process', 'tools:1,weapons:0.3', 'iron:1.2,coal:1', 2, tech=('forge',), fuel='coal'),
    _p('smelter', '冶炼厂', 'process', 'iron:1.5', 'iron_ore:4,charcoal:3', 4, tech=('forge',), fuel='charcoal',
       note='铜锡另走 bronze，金银走各自的锭'),
    _p('kiln', '窑', 'process', 'bricks:40,pottery:4', 'clay:5,fuel:3', 3, tech=('kiln',), fuel='timber'),
    _p('tannery', '制革坊', 'process', 'leather:2', 'hides:2,water:4', 3),
    _p('barracks', '兵营', 'defense', inp='food:10,weapons:0.1', workers=10, upkeep=5),
    _p('watchtower', '瞭望塔', 'defense', inp='food:1', workers=2, upkeep=0.5),
    _p('city_wall', '城墙', 'infrastructure', upkeep=1, workers=0),
    _p('gate', '城门', 'infrastructure', 'coin:1', workers=2, note='过路税'),
    _p('temple', '神殿', 'service', inp='food:1', workers=3),
    _p('academy', '学院', 'service', inp='coin:2', workers=4),
    _p('infirmary', '医馆', 'service', inp='medicine:0.5', workers=2),
    _p('inn', '客栈', 'service', 'coin:3', 'food:4,wine:1', 3),
    _p('caravanserai', '商队驿站', 'trade', 'coin:4', 'food:5,fodder:5', 4),
    _p('stable', '马厩', 'service', inp='fodder:6', workers=2),
    _p('dock', '码头', 'trade', 'coin:4', workers=6),
    _p('warehouse', '仓库', 'store', workers=1),
    _p('mine_head', '矿井口', 'extract', 'iron_ore:3', 'tools:0.1', 5, tech=('mine_shaft',),
       note='城内矿井默认算铁矿；资源点矿井按 resource 取'),
    _p('boiler_house', '锅炉房', 'process', 'fuel:6', 'coal:4,water:6', 2, tech=('steam_boiler',)),
    _p('ward_tower', '结界塔', 'defense', inp='mana_crystal:0.1', workers=1, tech=('arcane_ward',)),
    _p('cemetery', '墓地', 'service', workers=1),
    _p('bridge', '桥', 'infrastructure', upkeep=0.5, workers=0),
]
FACILITY_PROFILES = {p.id: p for p in _FAC}
for _k, _v in FACILITY_PROFILES.items():
    object.__setattr__(_v, 'facility', _k)
RESIDENCE = _p('residence', '民居', 'residence', 'labor:3', 'food:3,water:2', workers=0,
               note='每户约 3 个劳力，按人口折算')

_STORE = {'granary': (('wheat', 400), ('rice', 400), ('millet', 400), ('flour', 200)),
          'warehouse': (('*', 600),), 'cistern': (('water', 2000),)}
for _k, _s in _STORE.items():
    object.__setattr__(FACILITY_PROFILES[_k], 'storage', _s)


def profile_for(meta: dict) -> Optional[EconomyProfile]:
    """按美术 meta 找经营档案；不参与经营的返回 None。"""
    cat = meta.get('category')
    if cat == 'site':
        res, sub = meta.get('resource'), meta.get('subtype')
        hit = SITE_PROFILES.get((res, sub)) or SITE_PROFILES.get((res, None))
        if hit is None:  # 只有细分档案、素材又没标 subtype 时，取同资源的第一个
            hit = next((p for (r, _), p in SITE_PROFILES.items() if r == res), None)
        return hit
    fac = meta.get('facility')
    if fac in FACILITY_PROFILES and cat not in ('prop', 'road', 'ground', 'water'):
        return FACILITY_PROFILES[fac]
    if cat == 'house':
        return RESIDENCE
    return None


def coverage(metas: Iterable[dict]) -> dict:
    """统计每种资源有没有对应的开采建筑档案和美术素材。"""
    art = {}
    for m in metas:
        if m.get('category') == 'site' and m.get('resource'):
            art.setdefault(m['resource'], set()).add(m.get('style'))
    profiles = {r for (r, _) in SITE_PROFILES}
    return {r: {'profile': r in profiles, 'art_styles': sorted(art.get(r, ()))} for r in RESOURCES}


def validate() -> list[str]:
    """自检：所有货物、资源、设施、角色取值合法。返回问题列表（空 = 通过）。"""
    bad = []
    for p in list(SITE_PROFILES.values()) + list(FACILITY_PROFILES.values()) + [RESIDENCE]:
        if p.role not in ROLES:
            bad.append('%s: role %s' % (p.id, p.role))
        if p.resource and p.resource not in RESOURCES:
            bad.append('%s: resource %s' % (p.id, p.resource))
        for fl in p.inputs + p.outputs:
            if fl.good not in GOODS:
                bad.append('%s: good %s' % (p.id, fl.good))
    for r in RESOURCES:
        if (r, None) not in SITE_PROFILES and not any(k[0] == r for k in SITE_PROFILES):
            bad.append('resource %s 没有开采档案' % r)
    if set(FACILITY_PROFILES) != set(FACILITIES):
        bad.append('FacilityKind 不全：%s' % sorted(set(FACILITIES) - set(FACILITY_PROFILES)))
    return bad
