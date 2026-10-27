"""Deterministic single-town generation for V1: four reviewable stages, fixed rules.

Boundaries kept deliberately narrow:

* No language model is called. Every structured fact comes from authored input plus the
  fixed rule tables in this module. A model adapter may be added later; it would only
  ever *propose* candidates that the same validator has to accept, never write state.
* Determinism uses a SHA-256 counter stream keyed by the request seed and a stable
  label. No ``uuid``, no clock and no builtin ``hash`` appear in a generated value, so
  the same input, seed and base story revision reproduce the same town entity for
  entity, ids included.
* The coefficients below are **rule assumptions for a playable setting**, not
  historical measurements and not a physical or economic proof. Each stage records the
  basis it used, and the projection repeats that it is an estimate.
* One pass, no retry loop. Anything the input cannot support becomes an explicit
  warning or a refusal; the generator never invents a mine, an inventory or a
  political necessity.
"""
import hashlib
import json
import math

from .town_schema import (LABELS, Built, Capacity, Causal, ChainFlow, Clue, District,
                         EventCandidate, Facility, Faction, Governance, Housing, HousingRow,
                         Labor, Population, ProductionChain, Road, Secret,
                         Skeleton, Socioeconomy, SpecialSite, StoryInterface, Style,
                         TownInput, TownSnapshot, TradeFlow, WaterPlan)

GENERATOR_VERSION = 'town_v1'

# --- named rule coefficients (playable-setting assumptions, not measurements) --------
GRAIN_YIELD_T_PER_KM2_YEAR = 6     # one arable km² of premodern grain, one harvest
GRAIN_KG_PER_PERSON_YEAR = 180     # 0.18 t = 180 kg = 180 000 g of grain-equivalent
GRAIN_T_PER_PERSON_YEAR = GRAIN_KG_PER_PERSON_YEAR / 1000   # 0.18 t, display only
WATER_L_PER_PERSON_DAY = 25        # domestic use plus small stock, no irrigation
FARM_PERSONS_PER_KM2 = int(GRAIN_YIELD_T_PER_KM2_YEAR / GRAIN_T_PER_PERSON_YEAR)
ROAD_PERSONS_PER_OPEN_DAY = 6      # imported-food reach of one open track-day
ROAD_FACTOR = {'none': 0.0, 'track': 1.0, 'paved': 2.5, 'highway': 5.0}
WORKER_SHARE_PERMILLE = 450        # working-age share, rule of thumb
# Output per worker-year, in each unit a chain can declare. Rule assumptions only.
PER_WORKER_UNITS = {'t': 2, 'm3': 8, 'count': 30, 'kg': 40}
FOOD_KINDS = ('grain', 'fish', 'livestock')
ORE_KINDS = ('iron', 'copper', 'tin', 'gold', 'rare_metals', 'coal')
# A grain chain needs at least this much arable land, or it is not a real livelihood.
GRAIN_MIN_ARABLE_KM2 = 8

PRESETS = ('wet_valley', 'cold_mountain_mine', 'arid_oasis_route')

PERIOD_FACTOR = {'day': 365, 'week': 52, 'month': 12, 'year': 1}
UNIT_SCALE = {'t': 1.0, 'm3': 1.0, 'count': 1.0, 'kg': 0.001}
# Exact integer scales (numerator, denominator) for the same conversion. Every
# conservation check runs on integers, so there is no floating-point slack to hide behind
# and no arbitrary "one tonne" tolerance: a deficit of one gram is a deficit.
UNIT_NUM = {'t': 1, 'm3': 1, 'count': 1, 'kg': 1}
UNIT_DEN = {'t': 1, 'm3': 1, 'count': 1, 'kg': 1000}
# Grams of grain-equivalent per person per year. 0.18 t = 180 kg = 180 000 g; this is
# derived from the kilogram constant above so the two can never drift apart again.
GRAIN_G_PER_PERSON_YEAR = GRAIN_KG_PER_PERSON_YEAR * 1000   # 180 000 g
# Grams per tonne, used to keep one common denominator across mass comparisons.
G_PER_T = 1000000
SCALE_CUTOFFS = ((300, 'hamlet'), (1500, 'village'), (6000, 'small_town'), (20000, 'town'))
NAME_SUFFIX = {'mining_town': '矿镇', 'pass_fortress': '关城', 'port': '港', 'market_town': '集',
               'caravan_stop': '驿', 'farm_town': '屯', 'religious_center': '祠',
               'village': '村', 'hamlet': '舍', 'town': '镇', 'city': '城'}
HOUSEHOLD_LABEL = {'nuclear': '核心家庭', 'extended': '扩展家庭', 'communal': '共居'}


# ------------------------------------------------------------------ determinism
def _stream(seed, *parts):
    """Counted SHA-256 stream. No clock, no uuid, no builtin hash()."""
    base = '\x1f'.join([seed, *[str(p) for p in parts]]).encode('utf-8')
    counter = 0
    while True:
        block = hashlib.sha256(base + b'\x1f' + str(counter).encode('ascii')).digest()
        for offset in range(0, 32, 4):
            yield int.from_bytes(block[offset:offset + 4], 'big')
        counter += 1


def _next(seed, *parts):
    return next(_stream(seed, *parts))


def _pick(seed, rows, *parts):
    rows = list(rows)
    return None if not rows else rows[_next(seed, *parts) % len(rows)]


def _digest(value, length=16):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:length]


def _largest_remainder(weights):
    """Split 1000 permille across weights with no rounding drift."""
    total = sum(weights)
    if total <= 0:
        return [1000 // len(weights)] * len(weights)
    shares = [w * 1000 // total for w in weights]
    order = sorted(range(len(weights)), key=lambda i: (-(weights[i] * 1000 % total), i))
    index = 0
    while sum(shares) < 1000 and index < len(order):
        shares[order[index]] += 1
        index += 1
    while sum(shares) > 1000:
        shares[max(range(len(shares)), key=lambda i: (shares[i], -i))] -= 1
    return shares


# --------------------------------------------------------------- unit helpers
def to_per_year(amount, unit, period):
    """Convert one declared flow to a year, in its own unit.

    Only used for display and for same-kind comparisons; every *conservation* check
    below uses `flow_grams` on integers instead.
    """
    return amount * PERIOD_FACTOR[period] * UNIT_SCALE[unit]


def flow_grams(flow):
    """Exact grams per year for a mass flow, or None when the unit is not mass.

    Integer arithmetic throughout: `amount × factor × 1e6 / 1000` for kilograms. No
    float ever enters a comparison that can accept or reject a town.
    """
    if flow['unit'] not in ('t', 'kg'):
        return None
    return (int(flow['amount']) * PERIOD_FACTOR[flow['period']] * G_PER_T) // UNIT_DEN[flow['unit']]


def mass_flow(amount, unit, period):
    """Build the minimal flow dict `flow_grams` needs, for ad-hoc comparisons."""
    return {'amount': int(amount), 'unit': unit, 'period': period}


def food_tonnes(flow):
    """Grain-equivalent tonnes per year as a float, for reporting only.

    Never used in a pass/fail decision: use `flow_grams` there.
    """
    grams = flow_grams(flow)
    return 0.0 if grams is None else grams / G_PER_T


def need_grams(persons):
    """Exact grain requirement in grams per year for a population."""
    return int(persons) * GRAIN_G_PER_PERSON_YEAR


# --------------------------------------------------------------- stage 1: skeleton
def _arable_fraction(terrain):
    water = min(1.0, terrain['precipitation_mm'] / 700) * 0.6 + terrain['freshwater'] * 0.4
    temperature = max(0.0, min(1.0, 1 - abs(terrain['temperature_c'] - 15) / 30))
    slope = max(0.05, 1 - terrain['slope_deg'] / 40)
    flood = 1 - 0.6 * terrain['flood_risk']
    value = terrain['soil_fertility'] * water * temperature * slope * flood
    return max(0.0, min(0.9, value)), {'water': round(water, 3),
                                       'temperature': round(temperature, 3),
                                       'slope': round(slope, 3), 'flood': round(flood, 3)}


def capacities(entry):
    """Bounded carrying capacities in persons, plus the arable area behind them."""
    terrain, water, transport = entry['terrain'], entry['water'], entry['transport']
    water_cap = int(water['daily_capacity_l'] * water['reliability']) // WATER_L_PER_PERSON_DAY
    arable, factors = _arable_fraction(terrain)
    arable_km2 = terrain['area_km2'] * arable
    # Local carrying capacity only counts land that is actually worked. A patch smaller
    # than the minimum arable area produces no chain (see `_chains`), so counting it here
    # would let a town claim food it never grows and then fail its own food balance.
    local_food = int(arable_km2 * FARM_PERSONS_PER_KM2) if arable_km2 >= GRAIN_MIN_ARABLE_KM2 else 0
    open_days = max(0, 365 - transport['seasonal_closed_days'])
    lane = max(ROAD_FACTOR[transport['road']], 1.6 if transport['portage'] else 0.0)
    if transport['water_route']:
        lane = max(lane, 2.0)
    transport_cap = int(lane * open_days * ROAD_PERSONS_PER_OPEN_DAY)
    # Imported food is summed in exact grams, then converted to persons by integer
    # division: nobody eats a fraction of a person-year, and rounding up would create a
    # shortfall the validator refuses.
    imported_grams = 0
    for imported in entry['imports']:
        if imported['kind'] in FOOD_KINDS:
            grams = flow_grams(mass_flow(imported['amount_per_period'], imported['unit'],
                                         imported['period']))
            imported_grams += grams or 0
    imported_tonnes = imported_grams / G_PER_T
    imported_persons = imported_grams // GRAIN_G_PER_PERSON_YEAR
    import_cap = min(imported_persons, transport_cap)
    return {'water_cap': water_cap, 'local_food_cap': local_food, 'import_food_cap': import_cap,
            'imported_tonnes': imported_tonnes, 'imported_grams': imported_grams,
            'transport_cap': transport_cap, 'arable_fraction': arable,
            'arable_km2': round(arable_km2, 2), 'factors': factors,
            'imported_persons': imported_persons}


def positive_fuel_imports(entry):
    """Fuel kinds that arrive as an import with a volume greater than zero.

    A zero-volume fuel import is a declaration without a supply and is ignored here.
    """
    kinds = set()
    for imported in entry['imports']:
        if imported['kind'] == 'fuel' and imported['amount_per_period'] > 0:
            kinds.add('any')
            kinds.add(imported.get('name', ''))
    return kinds


def _intrinsic_ok(candidate, entry):
    """Surveyed, extractable, and its own extraction/processing technology is declared."""
    if not (candidate['surveyed'] and candidate['extractable']):
        return False
    if set(candidate['requires_technology']) - set(entry['technology']):
        return False
    if candidate['kind'] in ('iron', 'copper', 'tin', 'gold', 'rare_metals', 'coal'):
        if 'mine_shaft' not in entry['technology']:
            return False
    return True


def _fuel_requirement(candidate):
    """The fuel kind a candidate needs, or 'none'."""
    return candidate['fuel'] if candidate['fuel'] != 'none' else 'none'


def fuel_kind_available(kind, available_kinds, fuel_import):
    """Whether one fuel kind is genuinely on hand given the closure and the imports."""
    if kind == 'none':
        return True
    return kind in available_kinds or bool(fuel_import)


def resource_closure(entry, max_rounds=None):
    """Bounded fixed point: which resource candidates can actually be worked here.

    The seed set is (a) surveyed + extractable candidates whose own technology is
    declared and which need no fuel, and (b) fuel that arrives as a positive import.
    Each round adds candidates whose fuel requirement is already satisfied by the set
    built so far, so *chains* of dependency resolve (wood → coal → iron) while a cycle
    with no external start (coal needs wood, wood needs coal) never bootstraps itself.

    The round cap is one per candidate, so the loop always terminates and never
    re-derives the same work. `materials` is a permission list and is deliberately not
    consulted: being allowed to burn coal is not the same as having coal.
    """
    candidates = list(entry['resources'])
    if max_rounds is None:
        max_rounds = len(candidates) + 1
    fuel_import = bool(positive_fuel_imports(entry))
    available = set()
    kinds = set()
    for candidate in candidates:
        if _intrinsic_ok(candidate, entry) and _fuel_requirement(candidate) == 'none':
            available.add(candidate['id'])
            kinds.add(candidate['kind'])
    rounds = 0
    while rounds < max_rounds:
        rounds += 1
        added = False
        for candidate in candidates:
            if candidate['id'] in available:
                continue
            if not _intrinsic_ok(candidate, entry):
                continue
            if not fuel_kind_available(_fuel_requirement(candidate), kinds, fuel_import):
                continue
            available.add(candidate['id'])
            kinds.add(candidate['kind'])
            added = True
        if not added:
            break
    return sorted(available), sorted(kinds)


def blocked_dependencies(entry):
    """Candidates that cannot be worked and the reason, for author-facing messages."""
    available, _kinds = resource_closure(entry)
    reasons = []
    for candidate in entry['resources']:
        if candidate['id'] in available:
            continue
        if not (candidate['surveyed'] and candidate['extractable']):
            reasons.append({'id': candidate['id'], 'kind': candidate['kind'],
                            'reason': '未勘探或不可采'})
        elif set(candidate['requires_technology']) - set(entry['technology']):
            reasons.append({'id': candidate['id'], 'kind': candidate['kind'],
                            'reason': '开采/加工技术未申报'})
        elif candidate['kind'] in ('iron', 'copper', 'tin', 'gold', 'rare_metals', 'coal') \
                and 'mine_shaft' not in entry['technology']:
            reasons.append({'id': candidate['id'], 'kind': candidate['kind'],
                            'reason': '缺少矿井技术'})
        else:
            reasons.append({'id': candidate['id'], 'kind': candidate['kind'],
                            'reason': '燃料来源不可用（未勘探/未开采/循环依赖）'})
    return reasons


def gated_resource(candidate, entry):
    """A candidate is produced only if it is in the bounded resource closure.

    Singular form kept for call sites that need one answer; it delegates to the same
    closure the validator uses, so the generator and the validator can never disagree.
    """
    available, _kinds = resource_closure(entry)
    return candidate['id'] in available


def reason_label(reason):
    return {'water': '水源', 'crossroad': '十字路口', 'ore': '矿产', 'farmland': '可耕地',
            'defense': '防御', 'religious': '宗教', 'trade': '贸易', 'refuge': '避难',
            'fishing': '渔业', 'salt': '盐'}[reason]


def scale_of(population):
    for limit, name in SCALE_CUTOFFS:
        if population < limit:
            return name
    return 'city'


def _siting_reasons(entry, caps):
    reasons = []
    if entry['water']['source'] != 'none':
        reasons.append('water')
    if any(r['kind'] in ORE_KINDS for r in entry['resources'] if gated_resource(r, entry)):
        reasons.append('ore')
    if caps['arable_fraction'] > 0.35:
        reasons.append('farmland')
    if entry['transport']['road'] in ('paved', 'highway') or entry['transport']['water_route']:
        reasons.append('trade')
    if entry['terrain']['slope_deg'] > 15 or entry['transport']['road'] == 'none':
        reasons.append('defense')
    if any(b['kind'] == 'rule_template' for b in entry['bindings']):
        reasons.append('religious')
    if entry['transport']['water_route'] and entry['terrain']['elevation_m'] < 300:
        reasons.append('fishing')
    return reasons or ['water']


def _town_type(population, reasons, entry):
    """Ordered decision table. Clear precedence, no hidden scoring."""
    scale = scale_of(population)
    elevated = entry['terrain']['elevation_m'] >= 900
    if 'ore' in reasons and population < 20000:
        return 'mining_town', scale
    if 'defense' in reasons and elevated:
        return 'pass_fortress', scale
    if 'fishing' in reasons and entry['transport']['water_route']:
        return 'port', scale
    if 'religious' in reasons:
        return 'religious_center', scale
    if 'farmland' in reasons and 'trade' not in reasons:
        return 'farm_town', scale
    if 'trade' in reasons:
        return ('market_town' if population >= 1500 else 'caravan_stop'), scale
    if 'farmland' in reasons:
        return 'farm_town', scale
    return {'hamlet': 'hamlet', 'village': 'village', 'small_town': 'town', 'town': 'town',
            'city': 'city'}[scale], scale


def _founded_reason(reasons, entry):
    if 'ore' in reasons:
        return '早年因矿脉露头设采矿聚落，随后因冶炼与运输需求扩大'
    if 'defense' in reasons and entry['terrain']['elevation_m'] >= 900:
        return '为控制山口与道路而设，居住功能服从驻守与通行需要'
    if 'trade' in reasons and 'water' in reasons:
        return '因渡口与商路交汇而形成，水源让商队与定居者都能停留'
    if 'farmland' in reasons:
        return '因河谷可耕地连片而建，聚落沿灌渠与水井分布'
    return '因可取水点与季节性营地长期停留而形成'


def build_skeleton(entry):
    seed = entry['seed']
    if entry['imports'] and entry['transport']['road'] == 'none' and \
            not (entry['transport']['water_route'] or entry['transport']['portage']):
        raise ValueError('有进口需求但没有任何可用通路；无路或水路的城镇不能靠进口维持人口')
    caps = capacities(entry)
    if caps['water_cap'] <= 0:
        raise ValueError('没有可用水源，也没有引水/储水条件，无法维持人口')
    local_total = caps['local_food_cap'] + caps['import_food_cap']
    if local_total <= 0:
        raise ValueError('本地粮食承载与进口粮食承载都为零，无法维持人口')
    raw = min(caps['water_cap'], local_total)
    # Downward-only variation: the carrying capacity stays an upper bound.
    population = raw * (940 + _next(seed, 'population') % 61) // 1000 // 10 * 10
    if population <= 0:
        raise ValueError('人口承载计算为零，输入条件不足')

    reasons = _siting_reasons(entry, caps)
    town_type, scale = _town_type(population, reasons, entry)
    base = entry['site_name'].strip()
    suffix = NAME_SUFFIX.get(town_type, '镇')
    gated = [r for r in entry['resources'] if gated_resource(r, entry)]

    roads = [Road(id='road_main', name='主路',
                  kind={'none': 'trail', 'track': 'trail', 'paved': 'road',
                        'highway': 'road'}[entry['transport']['road']],
                  destination='最近市场',
                  travel_days=max(1, entry['transport']['nearest_market_days']),
                  seasonal_closed_days=entry['transport']['seasonal_closed_days'])]
    if entry['transport']['water_route']:
        roads.append(Road(id='road_river', name='水路',
                          kind='river' if entry['terrain']['elevation_m'] < 900 else 'pass',
                          destination='下游市场',
                          travel_days=max(1, entry['transport']['nearest_market_days']),
                          seasonal_closed_days=entry['transport']['seasonal_closed_days'] // 2))
    if entry['transport']['road'] == 'none' or entry['terrain']['slope_deg'] > 15:
        roads.append(Road(id='road_pass', name='山口小道', kind='pass', destination='山口外',
                          travel_days=max(2, entry['transport']['nearest_market_days'] * 2),
                          seasonal_closed_days=min(
                              365, entry['transport']['seasonal_closed_days'] + 30)))

    water_note = {'river': '河水按可取水能力计入，洪水月需要暂停取水',
                  'lake': '湖水受季节水位影响', 'spring': '泉眼流量稳定但总量有限',
                  'well_field': '井群依赖地下水位', 'aqueduct': '引水渠需要持续维护',
                  'rain_cistern': '雨水窖在旱季最先见底', 'none': '没有本地水源'}[entry['water']['source']]

    warnings = []
    if entry['water']['storage'] == 'none' and entry['water']['source'] in ('spring', 'rain_cistern'):
        warnings.append('取水点没有蓄水设施，旱季或故障时没有缓冲')
    if entry['transport']['seasonal_closed_days'] > 60:
        warnings.append(f'道路每年封闭 {entry["transport"]["seasonal_closed_days"]} 天，'
                        '进口、税收与消息都有断档')
    if caps['import_food_cap'] < caps['imported_persons']:
        warnings.append('申报的进口粮食超过运输通道能力，已按通道上限截断')
    if population > caps['local_food_cap']:
        warnings.append('本地粮食不足以供养全部人口，缺口依赖进口')
    if not gated:
        warnings.append('没有已勘探且可开采的资源，产业只能按本地生计与进口原料推断')
    for candidate in entry['resources']:
        if not candidate['surveyed']:
            warnings.append(f'资源候选 {candidate["id"]} 未勘探：存在不等于可开采')
    if entry['terrain']['flood_risk'] > 0.45:
        warnings.append('洪水风险偏高，低地街区与仓储需要防护')

    basis = [f'水源承载 = 日供水×可靠度 ÷ {WATER_L_PER_PERSON_DAY} 升 = {caps["water_cap"]} 人',
             f'本地粮食承载 = 可耕地 {caps["arable_km2"]} km² × {FARM_PERSONS_PER_KM2} 人/km² '
             f'= {caps["local_food_cap"]} 人',
             f'进口粮食承载 = min(进口口粮 {caps["imported_tonnes"]:.1f} t/年 折 '
             f'{caps["imported_persons"]} 人, 通道能力 {caps["transport_cap"]} 人) '
             f'= {caps["import_food_cap"]} 人',
             '这些系数是玩法设定假设，不是历史统计、测绘或经济证明']
    explanations = [
        Causal(claim='人口规模由水源与粮食中较小的一项决定',
               because=[f'水源上限 {caps["water_cap"]} 人', f'粮食上限 {local_total} 人',
                        '可耕地比例由降水、气温、坡度与洪水风险共同决定']),
        Causal(claim='选址理由由输入的地形与交通条件给出',
               because=[f'识别到{reason_label(r)}条件' for r in reasons]),
    ]
    return Skeleton(town_type=town_type, scale=scale, display_name=base,
                    name_candidates=[base, base + suffix, base + '旧' + suffix],
                    region=entry['region'], founded_reason=_founded_reason(reasons, entry),
                    founded_period=entry['founded_period'],
                    coordinates=tuple(entry['terrain']['coordinates'] or (0.0, 0.0)),
                    siting_reasons=reasons,
                    water=WaterPlan(source=entry['water']['source'],
                                    storage=entry['water']['storage'],
                                    daily_capacity_l=int(entry['water']['daily_capacity_l']
                                                         * entry['water']['reliability']),
                                    reliability=entry['water']['reliability'], note=water_note),
                    roads=roads,
                    capacity=Capacity(water_cap=caps['water_cap'],
                                      local_food_cap=caps['local_food_cap'],
                                      import_food_cap=caps['import_food_cap'],
                                      transport_cap=caps['transport_cap'],
                                      population=population, basis=basis),
                    explanations=explanations, warnings=warnings).model_dump(mode='json')


# ------------------------------------------------------------ stage 2: socioeconomy
# chain slug, display name, output id, storage, output unit, energy
CHAIN_RULES = {
    'grain': ('grain', '粮食种植', 'grain', '本地农田与公仓', 't', 'human'),
    'timber': ('timber', '伐木与木作', 'timber', '林地与木场', 'm3', 'human'),
    'stone': ('quarry', '采石', 'stone_block', '采石场', 't', 'human'),
    'clay': ('kiln', '制砖与烧陶', 'brick', '砖窑', 't', 'fuel'),
    'iron': ('iron', '采铁与冶炼', 'iron_bar', '矿场与炉场', 't', 'fuel'),
    'copper': ('copper', '采铜与锻造', 'copper_bar', '矿场与锻坊', 't', 'fuel'),
    'tin': ('tin', '采锡', 'tin_bar', '矿场', 't', 'human'),
    'coal': ('coal', '采煤', 'coal_lump', '煤窑', 't', 'human'),
    'salt': ('salt', '采盐', 'salt', '盐田或盐井', 't', 'fuel'),
    'fish': ('fishery', '捕捞与腌鱼', 'salt_fish', '水域与腌制作坊', 't', 'human'),
    'livestock': ('herd', '畜牧与皮革', 'hide', '牧场', 'count', 'animal'),
    'wool': ('weave', '纺织', 'cloth', '织坊', 'count', 'human'),
    'herb': ('herb', '采药与配药', 'herb_medicine', '山地与药房', 'kg', 'human'),
    'reed': ('reed', '苇编与苫盖', 'reed_mat', '湿地', 'count', 'human'),
    'gold': ('gold', '淘金', 'gold_dust', '河滩或矿脉', 'kg', 'human'),
    'rare_metals': ('rare', '稀有金属采选', 'rare_ore', '矿脉', 'kg', 'fuel'),
}


def _governance(skeleton, entry, gated):
    town_type = skeleton['town_type']
    if town_type in ('pass_fortress', 'border_fortress'):
        return ('military_governor', '驻军指挥官与上级任命的守备官',
                '由上级军政体系授予，依赖军需补给；本地居民没有独立议席')
    if town_type == 'mining_town':
        return ('company_board', '矿场主与冶炼坊主组成的董事会',
                '由矿权与冶炼设备所有权支撑，受雇劳工没有表决权')
    if town_type == 'religious_center':
        return ('temple_authority', '主祭与祠产管事',
                '由祭祀职能与土地捐赠支撑，世俗事务另设调解人')
    if town_type in ('port', 'market_town', 'caravan_stop'):
        return ('guild_board', '商团与工匠行会推举的理事会', '由市场管理与关税征收能力支撑')
    if skeleton['scale'] in ('city', 'town', 'small_town'):
        return ('council', '居民与行会分区推举的议会', '由税收分摊与公共工程维护能力支撑')
    if len(entry['peoples']) > 1:
        return ('elder_council', '各族长老与水源管理者', '由长期定居与水源分配惯例支撑')
    return ('assembly', '全体成年居民议事', '由面对面议事习惯支撑；人一多就失灵')


def _tax_basis(skeleton, gated):
    basis = ['按耕地与收成', '按市场交易额']
    if gated:
        basis.append('按矿产与冶炼产量')
    if skeleton['town_type'] in ('port', 'caravan_stop', 'market_town'):
        basis.append('按过境货物')
    return basis


def _population(entry, skeleton):
    seed, capacity = entry['seed'], skeleton['capacity']['population']
    rows, weights = [], []
    rows.append({'id': 'g_core', 'label': entry['peoples'][0]['name'] + '居民', 'role': 'majority',
                 'note': '本地出生或长期定居；不表示单一职业或统一立场'})
    weights.append(720)
    if len(entry['cultures']) > 1 or len(entry['peoples']) > 1:
        other = entry['cultures'][1] if len(entry['cultures']) > 1 else entry['peoples'][1]
        rows.append({'id': 'g_second', 'label': other['name'] + '群体', 'role': 'minority',
                     'note': '语言与建筑习惯不同；法律地位由本地制度决定，不是固定职业'})
        weights.append(140)
    if entry['imports']:
        rows.append({'id': 'g_migrant', 'label': '常来商队与移居者', 'role': 'migrant',
                     'note': '随商路到达，停留时间取决于季节与关税'})
        weights.append(80)
    if entry['transport']['seasonal_closed_days'] > 30:
        rows.append({'id': 'g_seasonal', 'label': '季节性劳工', 'role': 'seasonal',
                     'note': '农忙或开矿季到达，淡季离开，不计入常驻需求'})
        weights.append(60)
    for row, share in zip(rows, _largest_remainder(weights)):
        row['share_permille'] = share
    # Population equals the skeleton carrying capacity that bounded it: one number,
    # one authority. Socioeconomic detail never silently exceeds it.
    # Round onto the 50-person grid: 180 g/person-year is then a whole number of
    # kilograms, so the declared food need can be exact instead of rounded. The town is
    # never made *larger* by this, so it still respects the carrying capacity.
    total = (capacity // 50) * 50 or capacity
    return {'total': total, 'groups': rows,
            'basis': (f'骨架阶段承载上限 {capacity} 人；组群占比按取水、贸易与季节用工需求'
                      '分配，占比之和固定为1000‰'),
            'uncertainty': '人口是规则估计，不是普查；季节人口与流动商队会让实际在场人数'
                           '上下浮动约一成'}


def candidate_factor(candidate):
    """Abundance × accessibility, bounded. The only place a deposit's numbers are used."""
    return max(0.05, min(1.0, candidate['abundance'] * candidate['accessibility']))


def _chains(entry, skeleton, gated, population):
    """One chain per gated resource, plus grain whenever land can be farmed.

    A chain that cannot get its fuel or its technology is not created; the reason
    becomes a warning. No chain is ever created from a resource that was never
    surveyed.
    """
    chains, warnings = [], []
    caps = capacities(entry)
    arable_km2 = caps['arable_km2']
    plan = []
    # A grain chain exists only where there is land worth farming: a token row of a few
    # tonnes would be a fake claim that a mountain hamlet grows its own food.
    if arable_km2 >= GRAIN_MIN_ARABLE_KM2:
        plan.append(('grain', None))
    for candidate in gated:
        if candidate['kind'] in CHAIN_RULES and candidate['kind'] != 'grain':
            plan.append((candidate['kind'], candidate))
    if not plan:
        plan = [('grain', None)]

    weights = [200 if kind == 'grain' else 30 + int(candidate['abundance'] * 100)
               for kind, candidate in plan]
    split = _largest_remainder(weights)
    base_share = {'hamlet': 200, 'village': 240, 'small_town': 280, 'town': 300,
                  'city': 310}[skeleton['scale']]
    fuel_local = ({'timber', 'coal', 'reed'} & set(entry['materials'])) | {
        r['kind'] for r in entry['resources'] if r['kind'] in ('timber', 'coal', 'reed')}
    fuel_import = any(i['kind'] == 'fuel' for i in entry['imports'])

    for (kind, candidate), share in zip(plan, split):
        slug, name, output, stores, unit, energy = CHAIN_RULES[kind]
        fuel = candidate['fuel'] if candidate else 'none'
        if energy == 'fuel':
            if fuel == 'none' or (fuel not in fuel_local and not fuel_import):
                warnings.append(f'{name}需要燃料，但输入没有申报可得的燃料来源，未生成该生产链')
                continue
        workers = max(1, population * min(base_share, 40 + share * base_share // 300) // 1000)
        amount = _chain_amount(kind, candidate, workers, arable_km2)
        if amount <= 0:
            warnings.append(f'{name}的产量在给定条件下为零，未生成该生产链')
            continue
        inputs = []
        if energy == 'fuel':
            inputs.append(ChainFlow(resource='fuel_' + fuel, name='燃料（' + fuel + '）',
                                    amount=max(1, workers * 2), unit='t',
                                    period='year').model_dump(mode='json'))
        tech = list(candidate['requires_technology']) if candidate else []
        chains.append({'id': 'ch_' + slug, 'name': name, 'inputs': inputs,
                       'output': ChainFlow(resource=output, name=output, amount=amount,
                                           unit=unit, period='year').model_dump(mode='json'),
                       'workers': workers, 'energy': energy, 'requires_technology': tech,
                       'stores': stores, 'ships_via': [r['id'] for r in skeleton['roads'][:2]],
                       'consumers': '本地居民与附近市场',
                       'note': ('产量按规则系数与劳力推算；系数是玩法假设，不是实测；'
                                '库存只有在开采与运输实际发生后才存在')})
    if not chains:
        need = max(1, need_grams(population) * 4 // 10 // G_PER_T)
        chains.append({'id': 'ch_subsist', 'name': '自给农作', 'inputs': [],
                       'output': ChainFlow(resource='grain', name='grain', amount=need, unit='t',
                                           period='year').model_dump(mode='json'),
                       'workers': max(1, population * 200 // 1000), 'energy': 'human',
                       'requires_technology': [], 'stores': '各家自存与公仓',
                       'ships_via': [], 'consumers': '本地居民',
                       'note': '没有可生成的生产链，按自给小农生计推算；不是库存或贸易数据'})
        warnings.append('产业按自给小农推断，未生成矿产或加工链')
    return chains, warnings


def _chain_amount(kind, candidate, workers, arable_km2):
    if kind == 'grain':
        amount = arable_km2 * GRAIN_YIELD_T_PER_KM2_YEAR
        if candidate:
            amount *= candidate_factor(candidate)
        return int(amount)
    unit = CHAIN_RULES[kind][4]
    rate = PER_WORKER_UNITS[unit]
    return int(workers * rate * candidate_factor(candidate))


def _need_flow(persons):
    """The food requirement as a flow whose amount is *exactly* `need_grams(persons)`.

    Tonnes are used when they divide the gram figure evenly, otherwise kilograms —
    180 g per person-year is always a whole number of grams, and any population a
    multiple of 50 makes it a whole number of kilograms. The stored value stays
    human-readable while the gram comparison in the validator remains exact, so no
    rounding tolerance is needed anywhere.
    """
    grams = need_grams(persons)
    if grams % G_PER_T == 0:
        return ChainFlow(resource='grain', name='口粮需求', amount=max(1, grams // G_PER_T),
                         unit='t', period='year')
    kg = grams // 1000
    if kg * 1000 != grams:
        raise ValueError('口粮需求无法用整数千克精确表示，人口口径有误')
    return ChainFlow(resource='grain', name='口粮需求', amount=max(1, kg), unit='kg',
                     period='year')


def _factions(entry, skeleton, chains, governance_form, has_temple):
    rows = []
    ruling = {'military_governor': 'garrison', 'company_board': 'company',
              'temple_authority': 'temple', 'guild_board': 'council', 'elder_council': 'clan',
              'assembly': 'council', 'council': 'council', 'lord': 'lord',
              'none': 'council'}.get(governance_form, 'council')
    power = {'garrison': 'arms', 'company': 'capital', 'temple': 'faith', 'clan': 'custom',
             'lord': 'land', 'council': 'appointment'}[ruling]
    rows.append({'id': 'fa_ruling', 'name': '本地治理机构', 'kind': ruling,
                 'public_goal': '维持水源、道路与市场秩序，按惯例征收税赋',
                 'power_source': power, 'resources': ['税赋与劳役', '公共设施'],
                 'obligations': ['维护水源与道路'], 'constraints': ['人力与粮食受季节限制'],
                 'relations': [], 'evidence': ['公告与税册', '公共工程上的题名'],
                 'hidden_goal': '担心税册上的实际户口低于上报数，正在补记而未公开'})
    if chains:
        rows.append({'id': 'fa_guild',
                     'name': '、'.join(c['name'] for c in chains[:2]) + '行会', 'kind': 'guild',
                     'public_goal': '稳定原料供应与售价，限制外来竞争者',
                     'power_source': 'knowledge', 'resources': ['作坊与工具', '熟练工'],
                     'obligations': ['维持产量与质量惯例'],
                     'constraints': ['原料与燃料依赖运输'],
                     'relations': [{'faction': 'fa_ruling', 'stance': 'client',
                                    'over': '税赋与市场摊位分配'}],
                     'evidence': ['行会标记与作坊门牌'],
                     'hidden_goal': '与另一行会在原料分配上有未公开的分歧'})
    if skeleton['town_type'] in ('pass_fortress', 'border_fortress'):
        rows.append({'id': 'fa_garrison', 'name': '驻守队伍', 'kind': 'garrison',
                     'public_goal': '控制通行、查验货物并维持山口安全',
                     'power_source': 'arms', 'resources': ['武装人员', '关卡'],
                     'obligations': ['上级军需'], 'constraints': ['依赖上级补给'],
                     'relations': [{'faction': 'fa_ruling', 'stance': 'tense',
                                    'over': '通行税与优先补给'}],
                     'evidence': ['关卡队形与换岗时间'],
                     'hidden_goal': '对上级报告的人数与实际在编人数不一致'})
    if entry['imports'] or skeleton['town_type'] in ('port', 'market_town', 'caravan_stop'):
        rows.append({'id': 'fa_merchant', 'name': '外来商团', 'kind': 'merchant_house',
                     'public_goal': '取得仓储与优先卸货权，压低过境费用',
                     'power_source': 'trade_route', 'resources': ['资金', '远途商队'],
                     'obligations': ['按约缴税'], 'constraints': ['受道路季节与关卡查验限制'],
                     'relations': [{'faction': 'fa_guild', 'stance': 'rival',
                                    'over': '仓储与摊位'},
                                   {'faction': 'fa_ruling', 'stance': 'client',
                                    'over': '关税减免'}],
                     'evidence': ['仓库租约', '商队停驻的空地'],
                     'hidden_goal': '正在打听关卡的检查频率与放行价码'})
    if has_temple:
        rows.append({'id': 'fa_temple', 'name': '祠庙与执事', 'kind': 'temple',
                     'public_goal': '主持节期与救济，保管捐赠记录',
                     'power_source': 'faith', 'resources': ['捐赠与祠产'],
                     'obligations': ['节期与赈济'], 'constraints': ['不能直接征用劳役'],
                     'relations': [{'faction': 'fa_ruling', 'stance': 'ally',
                                    'over': '节期秩序'}],
                     'evidence': ['节期日程', '捐赠碑'], 'hidden_goal': ''})
    limit = 2 if skeleton['scale'] == 'hamlet' else 3 if skeleton['scale'] == 'village' else 4
    rows = rows[:limit]
    keep = {r['id'] for r in rows}
    for row in rows:
        row['relations'] = [r for r in row['relations'] if r['faction'] in keep]
        row.setdefault('hidden_goal', '')
    return rows


def _trade(entry, chains):
    rows = []
    for index, imported in enumerate(entry['imports'], start=1):
        via = {'road': 'roads', 'river': 'roads', 'sea': 'roads', 'porter': '人力背运',
               'none': '未定（无可用路径）'}[imported['via']]
        rows.append({'id': f'tr_import_{index}', 'direction': 'import',
                     'resource': imported['id'], 'kind': imported['kind'],
                     'name': imported['name'],
                     'amount': imported['amount_per_period'], 'unit': imported['unit'],
                     'period': imported['period'], 'via': via,
                     'requirement': '需要道路通行季与关卡放行；通路中断时进口量与人口都要下调'})
    # Exports are a fraction of what the chains actually produce, in the chain's own
    # unit and period, so no export can exceed its supply. Grain is never exported here:
    # a town that cannot feed itself does not ship food out.
    seen = set()
    for chain in chains:
        out = chain['output']
        if out['resource'] == 'grain' or out['resource'] in seen:
            continue
        seen.add(out['resource'])
        share = int(out['amount']) // 4
        if share <= 0:
            continue
        rows.append({'id': f'tr_export_{len(seen)}', 'direction': 'export',
                     'resource': out['resource'], 'kind': 'other',
                     'name': out['resource'], 'amount': share, 'unit': out['unit'],
                     'period': out['period'], 'via': 'roads',
                     'requirement': '只有实际运出的部分才算外销；本版不虚构出口量'})
        if len(seen) >= 4:
            break
    return rows


def _tensions(entry, skeleton, chains, gated, staple, need):
    rows = []
    if staple < need:
        rows.append(f'本地口粮约 {staple} t/年，低于需求 {need} t/年，'
                    '缺口月份取决于通路是否畅通')
    if skeleton['town_type'] in ('pass_fortress', 'border_fortress'):
        rows.append('驻守队伍与民政治理在通行税与优先补给上互相牵制')
    if entry['transport']['seasonal_closed_days'] > 30:
        rows.append(f'道路每年封闭 {entry["transport"]["seasonal_closed_days"]} 天，'
                    '仓储与借贷关系在开春前后会紧张')
    if any(not r['surveyed'] for r in entry['resources']):
        rows.append('未勘探的资源被外地商人先一步打听，本地对其价值判断不一')
    if skeleton['capacity']['water_cap'] < skeleton['capacity']['local_food_cap']:
        rows.append('水源比粮食更早成为上限，取水权因此成为实际的政治议题')
    if not gated:
        rows.append('缺少可开采资源，外出做工与留守之间的分歧逐渐明显')
    if any(c['energy'] == 'fuel' for c in chains):
        rows.append('燃料消耗与林场/煤源的可及性直接决定炉场能否整年开工')
    return rows[:6]


def _reference_note(entry):
    if entry['social_mode'] == 'realistic_reference':
        ref = entry['realistic']
        return (f'现实参考档：{ref["region"]} · {ref["period"]}（{ref["polity_scope"]}），'
                f'证据等级 {ref["evidence_level"]}；不确定性：{ref["uncertainty"]}。'
                '本工具的数值系数是规则假设，不是对真实社会或经济的精确估计，'
                '制度描述不构成历史结论；架空改动按 adaptation 标注'
                + (f'；架空改编：{ref["adaptation"]}' if ref['adaptation'] else ''))
    art = entry['artistic']
    return ('艺术夸张档：现实原型 ' + '、'.join(art['prototypes']) + '；创作归纳 '
            + '、'.join(art['inventions']) + f'；设计目标：{art["design_goal"]}。'
            '这不是历史记录，材料、能源、技术与组织成本仍按同一套硬约束校验'
            + (f'；反例说明：{art["counterexamples"]}' if art['counterexamples'] else ''))


def build_socioeconomy(entry, skeleton):
    gated = [r for r in entry['resources'] if gated_resource(r, entry)]
    population = _population(entry, skeleton)
    total = population['total']

    form, authority, legitimacy = _governance(skeleton, entry, gated)
    has_temple = ('religious' in skeleton['siting_reasons'] or
                  skeleton['town_type'] == 'religious_center' or
                  any(b['kind'] == 'rule_template' for b in entry['bindings']))
    chains, warnings = _chains(entry, skeleton, gated, total)
    available = total * WORKER_SHARE_PERMILLE // 1000
    # `assigned_workers` is the sum of the chains, nothing else: the validator compares
    # it against that sum, so an inflated headcount cannot hide idle labour.
    assigned = sum(c['workers'] for c in chains)
    if assigned > available and chains:
        # Single bounded pass, then a warning: never a loop until the numbers "fit".
        scaled = []
        for chain in chains:
            scaled.append({**chain, 'workers': max(1, chain['workers'] * available // assigned)})
        chains = scaled
        assigned = sum(c['workers'] for c in chains)
        warnings.append('劳动力不足以支撑全部产业，按可用劳力等比缩减一次，未反复迭代')

    staple_row = next((c for c in chains if c['output']['resource'] == 'grain'), None)
    # The authoritative requirement is `_need_flow(total)`, which is exact in grams.
    # `need` is only the readable figure used in tension text.
    need_model = _need_flow(total)
    need = need_model.amount
    # The staple is exactly the grain chain's output. A patch of arable land too small to
    # justify its own chain produces nothing in this model, so the town imports instead —
    # which is the honest reading of a mountain hamlet with one km² of barley.
    staple = staple_row['output']['amount'] if staple_row else 0

    factions = _factions(entry, skeleton, chains, form, has_temple)
    trade = _trade(entry, chains)
    tensions = _tensions(entry, skeleton, chains, gated, staple, need)

    explanations = [Causal(claim='主要生计由已勘探资源、可用技术与能源共同决定',
                           because=['已勘探且可加工的资源：'
                                    + (', '.join(r['kind'] for r in gated) or '无'),
                                    '可用技术：' + (', '.join(entry['technology']) or '未申报'),
                                    '能源：' + ', '.join(sorted({c['energy'] for c in chains}))]),
                    Causal(claim=f'{LABELS.get(form, form)}成为治理形式',
                           because=[f'城镇类型 '
                                    f'{LABELS.get(skeleton["town_type"], skeleton["town_type"])}',
                                    f'权力来源 {factions[0]["power_source"]} 与资源控制相关'])]
    if staple < need:
        explanations.append(Causal(claim='口粮依赖进口或存在缺口',
                                   because=[f'本地口粮 {staple} t/年', f'需求 {need} t/年',
                                            '进口量与通行季共同约束人口上限']))
    return Socioeconomy(population=Population(**population),
                        governance=Governance(form=form, authority=authority,
                                              legitimacy=legitimacy,
                                              tax_basis=_tax_basis(skeleton, gated),
                                              obligations=['维护水源与道路', '处理纠纷与税收']),
                        factions=[Faction(**f) for f in factions],
                        chains=[ProductionChain(**c) for c in chains],
                        trade=[TradeFlow(**t) for t in trade],
                        labor=Labor(available_workers=available, assigned_workers=assigned,
                                    note=(f'可用劳力 = 人口×{WORKER_SHARE_PERMILLE}‰；'
                                          '已分配含产业与行政，不含家务、育儿与季节短工')),
                        staple=ChainFlow(resource='grain', name='本地口粮', amount=int(staple),
                                         unit='t', period='year'),
                        staple_need=need_model,
                        tensions=tensions, explanations=explanations, warnings=warnings,
                        reference_note=_reference_note(entry)).model_dump(mode='json')


# ---------------------------------------------------------------- stage 3: built
WALL_TECH = {'timber': 'timber_frame', 'stone': 'masonry', 'cut_stone': 'masonry',
             'clay_brick': 'kiln', 'fired_tile': 'kiln', 'mud_brick': 'none',
             'rammed_earth': 'none', 'hide': 'none', 'felt': 'none'}
ROOF_MATERIAL = {'flat_mud': 'mud_brick', 'gable_thatch': 'thatch', 'gable_tile': 'fired_tile',
                 'steep_slate': 'slate', 'hip_tile': 'fired_tile', 'monopitch': 'timber'}
WALL_NOTE = {'stone': '石墙承重，开窗少，室内偏凉；基础按经验加深',
             'cut_stone': '条石砌筑，需要专门采石与运输，造价最高',
             'timber': '木构架承重，墙内填土或编笆，火灾时沿巷蔓延较快',
             'clay_brick': '砖砌墙体，需要窑场持续供料，潮湿地段用石砌墙脚',
             'fired_tile': '砖与瓦同窑，屋面与墙体材料统一',
             'mud_brick': '土坯墙厚实，昼夜温差被墙体缓冲，雨水会侵蚀墙脚',
             'rammed_earth': '夯土墙整体性好，但怕长期浸水，墙脚需石砌护脚'}
DISTRICT_NOTE = {'residential': '{wall} 墙体、{roof} 屋面，雨水沿街沟排走',
                 'market': '沿街敞开铺面，夜里上板；仓储抬高地面防潮',
                 'craft': '作坊与住家混用，明火集中在巷口',
                 'administration': '广场与告示墙，征税与议事都在这里',
                 'temple': '围合院落，节期才向外开放',
                 'foreign_quarter': '建筑沿用本乡做法，材料随商路带来',
                 'poor': '低洼地段，排水最差，材料最便宜',
                 'industrial': '烟尘与炉渣集中在下风侧，夜间有明火',
                 'harbor': '栈桥与货栈沿岸布置，汛期要抬高',
                 'military': '营房与库房分开，进出受查验',
                 'academy': '书坊防火，砖石为主',
                 'cemetery': '在聚落外缘，地势略高',
                 'outskirts': '菜地与畜栏，房屋稀疏'}


def _choose_wall(entry):
    terrain = entry['terrain']
    if terrain['precipitation_mm'] > 800:
        order = ['timber', 'stone', 'clay_brick', 'cut_stone']
    elif terrain['temperature_c'] < 2:
        order = ['stone', 'cut_stone', 'timber', 'rammed_earth']
    elif terrain['precipitation_mm'] < 250:
        order = ['mud_brick', 'rammed_earth', 'stone', 'clay_brick']
    else:
        order = ['timber', 'clay_brick', 'stone', 'rammed_earth']
    for material in order + list(entry['materials']):
        if material not in entry['materials']:
            continue
        tech = WALL_TECH.get(material, 'none')
        if tech != 'none' and tech not in entry['technology']:
            continue
        return material
    raise ValueError('允许材料中没有与已申报技术相容的墙体材料；请补充材料或技术')


def _choose_roof(entry, culture):
    """Hard constraints beat culture: a thatch roof beside kilns is refused."""
    terrain = entry['terrain']
    candidates = [culture['roof']]
    if terrain['precipitation_mm'] > 900:
        candidates.append('steep_slate')
    elif terrain['precipitation_mm'] > 350:
        candidates.append('gable_tile')
    elif terrain['precipitation_mm'] < 250:
        candidates.append('flat_mud')
    else:
        candidates.append('gable_thatch')
    candidates.append('monopitch')
    for roof in candidates:
        material = ROOF_MATERIAL[roof]
        if material not in entry['materials']:
            continue
        if material in ('fired_tile', 'slate') and not ({'kiln', 'masonry'}
                                                        & set(entry['technology'])):
            continue
        if terrain['temperature_c'] < 0 and roof in ('gable_thatch', 'monopitch') and \
                'snow_load_engineering' not in entry['technology']:
            continue
        return roof
    return 'none'


def _choose_drainage(entry, wall):
    precipitation = entry['terrain']['precipitation_mm']
    if precipitation > 800:
        return 'stone_channel' if wall in ('stone', 'cut_stone', 'clay_brick') else 'open_gutter'
    if precipitation > 250:
        return 'open_gutter'
    return 'soak_pit'


def _district_plan(entry, skeleton, socio, population):
    rows = [('d_residential', '居住区', 'residential', 500)]
    if socio['trade']:
        rows.append(('d_market', '市场与仓储', 'market', 130))
    if socio['chains']:
        rows.append(('d_craft', '作坊区', 'craft', 110))
    rows.append(('d_admin', '行政与广场', 'administration', 60))
    if any(f['kind'] == 'temple' for f in socio['factions']):
        rows.append(('d_temple', '祠庙区', 'temple', 50))
    if any(g['role'] in ('migrant', 'minority') for g in socio['population']['groups']):
        rows.append(('d_foreign', '外来者聚居', 'foreign_quarter', 45))
    if population > 1500:
        rows.append(('d_poor', '低地贫民区', 'poor', 40))
    if any(c['energy'] == 'fuel' for c in socio['chains']):
        rows.append(('d_industrial', '炉场与污染区', 'industrial', 40))
    if entry['transport']['water_route']:
        rows.append(('d_harbor', '码头', 'harbor', 30))
    if skeleton['town_type'] in ('pass_fortress', 'border_fortress'):
        rows.append(('d_military', '营区', 'military', 40))
    if population > 6000 and 'printing' in entry['technology']:
        rows.append(('d_academy', '学院与书坊', 'academy', 30))
    rows.append(('d_cemetery', '墓地', 'cemetery', 20))
    rows.append(('d_outskirts', '近郊田园', 'outskirts', 55))
    return rows


def _household(entry, culture):
    base = {'nuclear': 4.6, 'extended': 6.8, 'communal': 9.0}[culture['household']]
    factor = sum(p['space_factor'] for p in entry['peoples']) / len(entry['peoples'])
    return round(base * factor, 1)


def build_built(entry, skeleton, socio):
    culture = entry['cultures'][0]
    wall = _choose_wall(entry)
    roof = _choose_roof(entry, culture)
    drainage = _choose_drainage(entry, wall)
    population = socio['population']['total']
    warnings = []

    plan = _district_plan(entry, skeleton, socio, population)
    shares = _largest_remainder([w for _, _, _, w in plan])
    districts = []
    for (district_id, name, kind, _), share in zip(plan, shares):
        roof_here, drainage_here = roof, drainage
        if kind == 'poor':
            drainage_here = 'open_gutter'
            if 'thatch' in entry['materials']:
                roof_here = 'gable_thatch'
        if kind == 'industrial' and roof_here in ('gable_thatch', 'monopitch'):
            # A furnace quarter cannot keep a flammable roof beside the kilns.
            for alternative in ('gable_tile', 'steep_slate', 'flat_mud'):
                if ROOF_MATERIAL[alternative] in entry['materials']:
                    roof_here = alternative
                    break
        storeys = 3 if skeleton['scale'] in ('city', 'town') and wall in ('stone', 'cut_stone') \
            else 2 if skeleton['scale'] in ('city', 'town') else 1
        # Access is physical (can one walk in); visibility is knowledge (do people
        # know it exists). A guarded furnace quarter is known but not open; a sealed
        # ruin is unknown but, once found, not enterable. The two never substitute.
        access = 'restricted' if kind in ('industrial', 'military') else 'public'
        visibility = 'public'
        districts.append(District(
            id=district_id, name=name, kind=kind, population_share_permille=share,
            materials=[wall], roof=roof_here, drainage=drainage_here, storeys=storeys,
            access=access, visibility=visibility,
            reach_via=[r['id'] for r in skeleton['roads']],
            note=DISTRICT_NOTE[kind].format(wall=wall, roof=roof_here)).model_dump(mode='json'))

    district_ids = {d['id'] for d in districts}

    def here(*preferred):
        for candidate in preferred:
            if candidate in district_ids:
                return candidate
        return 'd_residential'

    facilities = []
    counter = {'n': 0}
    # A facility is only as visible as the district that holds it: a workshop inside a
    # restricted or secret quarter must not leak its parent's existence through its own
    # name. Access (may one walk in) is a separate field again.
    district_visibility = {d['id']: d['visibility'] for d in districts}

    def add(kind, name, district, public_note, secret='', condition='good', tech=None,
            materials=None):
        counter['n'] += 1
        facilities.append(Facility(id=f'f_{kind}_{counter["n"]}', name=name, kind=kind,
                                   district=district, materials=materials or [wall],
                                   condition=condition, requires_technology=list(tech or []),
                                   public_note=public_note, secret_note=secret,
                                   visibility=district_visibility[district]).model_dump(mode='json'))

    produced = {c['output']['resource'] for c in socio['chains']}
    if 'grain' in produced or any(t['direction'] == 'import' and t['kind'] == 'grain'
                                  for t in socio['trade']):
        add('granary', '公仓', here('d_market', 'd_craft'),
            '抬高地板、留通风缝的粮仓；按户与按行会分区存放')
    if entry['water']['storage'] != 'none':
        add('cistern', '蓄水池', here('d_admin'),
            '封闭蓄水，按街区定时开放取水；维护责任写在告示上')
    if entry['water']['source'] in ('well_field', 'spring'):
        add('well', '公共水井', here('d_residential'), '井台与排水沟相连，取水有先后秩序')
    if 'grain' in produced:
        mill_tech = 'water_wheel' if 'water_wheel' in entry['technology'] else (
            'windmill' if 'windmill' in entry['technology'] else None)
        add('mill', '磨坊', here('d_craft'),
            '按季收费磨面，量具由行会核对'
            + ('；水轮驱动' if mill_tech == 'water_wheel'
               else '；风车驱动' if mill_tech == 'windmill' else '；人力或畜力驱动'),
            tech=[mill_tech] if mill_tech else [])
    if 'iron_bar' in produced:
        add('smelter', '炉场', here('d_industrial', 'd_craft'),
            '炉渣堆在下风处，夜里火光可见', tech=['forge'])
        add('forge', '铁匠铺', here('d_craft'), '修农具与车轴，也接关卡的订件', tech=['forge'])
    if 'copper_bar' in produced:
        add('forge', '铜匠铺', here('d_craft'), '打制器皿与饰件，按件计价', tech=['forge'])
    if 'brick' in produced:
        add('kiln', '砖窑', here('d_industrial', 'd_craft'),
            '窑烟在雨季压低，靠近的人会咳嗽', tech=['kiln'])
    if 'hide' in produced:
        add('tannery', '制革坊', here('d_outskirts'), '设在下游，污水不回到取水口')
    if skeleton['town_type'] in ('pass_fortress', 'border_fortress'):
        add('city_wall', '寨墙与栅门', here('d_admin'), '以本地材料分段加高，缺口逐年补修',
            condition='fair')
        add('watchtower', '望楼', here('d_military', 'd_admin'),
            '视线沿道路方向，换岗时敲一段铁片')
        add('gate', '关卡门', here('d_admin'), '查验货单并收过境费，夜间关闭', condition='fair')
    if 'temple' in {f['kind'] for f in socio['factions']}:
        add('temple', '祠庙', here('d_temple', 'd_admin'),
            '节期开放，平日由执事打理；捐赠记录不公开')
    if 'printing' in entry['technology'] and skeleton['scale'] in ('city', 'town', 'small_town'):
        add('academy', '书坊与学堂', here('d_academy', 'd_admin'),
            '教识字与算学，抄本可以借阅', tech=['printing'])
    if 'herb_medicine' in produced:
        add('infirmary', '药房', here('d_market', 'd_craft'), '按症配方，记账可赊，年底结清')
    if socio['trade']:
        add('inn', '客店', here('d_market', 'd_admin'), '按铺位收钱，马匹另计；夜里有人守门')
        add('warehouse', '货栈', here('d_market', 'd_admin'),
            '分租给不同商团，封条样式各不相同')
        add('stable', '牲口棚', here('d_outskirts'), '换马与喂料，粪肥卖给近郊农户')
    if skeleton['town_type'] in ('caravan_stop', 'market_town') and socio['trade']:
        add('caravanserai', '商队客院', here('d_market', 'd_admin'),
            '围合院落，夜间锁门，按驮数收费')
    if entry['transport']['water_route']:
        add('dock', '码头', here('d_harbor', 'd_outskirts'),
            '枯水期只能靠小船，栈桥每年修一次')
    if 'mine_shaft' in entry['technology'] and any(
            r['kind'] in ORE_KINDS for r in entry['resources'] if gated_resource(r, entry)):
        add('mine_head', '矿口', here('d_outskirts'),
            '井口有绞盘与排水沟，进洞按班组计时',
            secret='班组私下记录过一段被略去的塌方', tech=['mine_shaft'])
    # Tech-gated facilities exist only when the author declared that technology.
    if 'steam_boiler' in entry['technology']:
        add('boiler_house', '锅炉房', here('d_industrial', 'd_craft'),
            '锅炉与安全阀由专人看守，燃料消耗单独记账', tech=['steam_boiler'])
    if 'arcane_ward' in entry['technology']:
        add('ward_tower', '护持塔', here('d_admin'),
            '作者显式申报护持技术后才存在；维持费用按季结算', tech=['arcane_ward'])
    if entry['water']['source'] == 'river' and not entry['transport']['water_route'] \
            and entry['terrain']['elevation_m'] < 400:
        add('bridge', '桥', here('d_admin'), '桥面窄，会车要让行')
    add('cemetery', '墓地', here('d_cemetery'), '按族与行会分区，低地墓穴在汛期会进水',
        condition='fair')

    household_size = _household(entry, culture)
    total_houses = max(1, math.ceil(population / household_size)) if population else 0
    rows = []
    if total_houses:
        main_houses = total_houses
        if 'thatch' in entry['materials'] and roof != 'gable_thatch' and total_houses >= 8:
            main_houses = total_houses - max(1, total_houses // 8)
            rows.append(HousingRow(
                material='timber' if 'timber' in entry['materials'] else wall,
                roof='gable_thatch', houses=total_houses - main_houses,
                household_size=household_size,
                note='低地简易房，用最便宜的可燃材料').model_dump(mode='json'))
        rows.insert(0, HousingRow(
            material=wall, roof=roof, houses=main_houses, household_size=household_size,
            note=f'{culture["name"]}的习惯：{HOUSEHOLD_LABEL[culture["household"]]}'
        ).model_dump(mode='json'))
    housing = Housing(total_houses=sum(r['houses'] for r in rows), rows=rows,
                      basis=(f'房屋数 = 人口 {population} ÷ 户均 {household_size} 人；'
                             '只做代表性汇总，不逐栋建模'))

    sites = _special_sites(entry, skeleton, socio, district_ids)
    style = Style(materials=sorted({wall} | {r['material'] for r in rows}),
                  roof=roof, drainage=drainage,
                  wall_note=WALL_NOTE.get(wall, f'{wall} 墙体，按本地可得材料建造'),
                  explanations=_style_explanations(entry, wall, roof, drainage, culture))
    if entry['terrain']['temperature_c'] < 0 and 'snow_load_engineering' not in entry['technology']:
        warnings.append('寒冷地区没有申报屋面雪载技术，屋顶角度只能按经验估计')
    if roof == 'none':
        warnings.append('允许材料里没有可用的屋面材料，屋顶按未定处理，需要作者补充')
    return Built(districts=[District(**d) for d in districts],
                 facilities=[Facility(**f) for f in facilities], housing=housing,
                 special_sites=[SpecialSite(**s) for s in sites], style=style,
                 warnings=warnings).model_dump(mode='json')


def _style_explanations(entry, wall, roof, drainage, culture):
    terrain = entry['terrain']
    rows = [Causal(claim=f'以 {wall} 为主要墙体材料',
                   because=[f'允许材料包含 {wall}',
                            '已申报技术：' + (', '.join(entry['technology']) or '无'),
                            f'降水 {terrain["precipitation_mm"]}mm、'
                            f'年均温 {terrain["temperature_c"]}℃']),
            Causal(claim=f'屋面采用 {roof}',
                   because=['降水与温差决定坡度与瓦材',
                            f'{culture["name"]}的习惯屋面是 {culture["roof"]}'
                            + ('；材料或技术不允许，已按硬约束替换'
                               if culture['roof'] != roof else '')]),
            Causal(claim=f'排水采用 {drainage}',
                   because=[f'降水 {terrain["precipitation_mm"]}mm',
                            f'洪水风险 {terrain["flood_risk"]}',
                            '坡度与街道宽度限制明沟断面'])]
    if terrain['temperature_c'] < 0:
        rows.append(Causal(claim='屋顶坡度加大并减少悬挑',
                           because=['积雪荷载', '融雪期渗水']))
    if terrain['flood_risk'] > 0.4:
        rows.append(Causal(claim='低地街区抬高地面并加挡水墙',
                           because=['洪水风险偏高', '仓储与居住都不能泡水']))
    return rows


def _special_sites(entry, skeleton, socio, district_ids):
    """Special sites may be non-residential: they carry no population and no
    administrative fields, and a sealed one never reaches the public projection."""
    seed = entry['seed']
    gated = [r for r in entry['resources'] if gated_resource(r, entry)]
    faction_ids = {f['id'] for f in socio['factions']}

    def district(*preferred):
        for candidate in preferred:
            if candidate in district_ids:
                return candidate
        return None

    options = []
    if any(r['kind'] in ORE_KINDS for r in gated):
        options.append({'id': 's_old_mine', 'name': '旧矿口', 'kind': 'old_mine',
                        'in_district': None, 'reach_via': ['road_main'],
                        'origin': '早于正式矿场的老矿道，靠人力掘进后废弃，支护早已失效',
                        'public_description': '半塌的洞口被碎石挡住一部分，风从里面出来带土腥味',
                        'secret': '旧矿道与现行矿场之间有一段未标注的连通，矿主不希望被人发现',
                        'status': 'sealed', 'risks': ['塌方', '缺氧'],
                        'related_factions': ['fa_guild', 'fa_ruling'],
                        'entry_conditions': ['需要照明与支护']})
    if skeleton['town_type'] in ('pass_fortress', 'border_fortress'):
        options.append({'id': 's_battlefield', 'name': '旧战场', 'kind': 'battlefield',
                        'in_district': None, 'reach_via': ['road_main'],
                        'origin': '山口争夺留下的战场，双方都没有立碑',
                        'public_description': '坡地上还能看出壕沟走向，雨后常有人来捡铁片',
                        'secret': '当年退却的路线与现行地图不一致，有人刻意改过',
                        'status': 'ruined', 'risks': ['残骸', '遗物归属争议'],
                        'related_factions': ['fa_ruling'],
                        'entry_conditions': ['需要当地向导']})
    if any(f['kind'] == 'temple' for f in socio['factions']):
        options.append({'id': 's_shrine', 'name': '路边小祠', 'kind': 'shrine',
                        'in_district': district('d_temple', 'd_admin'),
                        'reach_via': ['road_main'],
                        'origin': '在取水路口设立的小祠，最早由过路人捐建',
                        'public_description': '没有常驻执事，供台上有新旧两种供品',
                        'secret': '祠内石刻记着一次被官方记载略去的分配决定',
                        'status': 'active', 'risks': [], 'related_factions': ['fa_temple'],
                        'entry_conditions': []})
    if entry['terrain']['slope_deg'] > 12 or entry['terrain']['elevation_m'] > 900:
        options.append({'id': 's_cave', 'name': '山腹裂口', 'kind': 'cave_mouth',
                        'in_district': None,
                        'reach_via': ['road_pass'] if len(skeleton['roads']) > 1
                        else ['road_main'],
                        'origin': '岩层开裂形成的通道，雨季有水流出',
                        'public_description': '裂口只容两人并行，深处听得到水声',
                        'secret': '裂口通向山另一侧的季节性牧道，走私者用过',
                        'status': 'dormant', 'risks': ['迷路', '涨水'],
                        'related_factions': [], 'entry_conditions': ['旱季进入']})
    if any(c['energy'] == 'fuel' for c in socio['chains']):
        options.append({'id': 's_workshop', 'name': '废作坊', 'kind': 'abandoned_workshop',
                        'in_district': district('d_industrial', 'd_craft'),
                        'reach_via': ['road_main'],
                        'origin': '曾试图用本地燃料扩大产量，成本不合算后停工',
                        'public_description': '炉体裂了缝，地上还有没清走的矿渣',
                        'secret': '停工的真正原因是炉温上不去，不是主家说的原料短缺',
                        'status': 'dormant', 'risks': ['结构不稳'],
                        'related_factions': ['fa_guild'], 'entry_conditions': []})
    if any(f['kind'] in ('council', 'clan', 'company', 'lord') for f in socio['factions']):
        options.append({'id': 's_manor', 'name': '旧宅', 'kind': 'old_manor',
                        'in_district': district('d_admin'), 'reach_via': ['road_main'],
                        'origin': '早期管理者的宅院，后代搬走后由几家分租',
                        'public_description': '院墙比周围房屋高，门楼上的字迹被磨平',
                        'secret': '地窖里存着旧税册，与现行户口对不上',
                        'status': 'claimed', 'risks': ['产权争议'],
                        'related_factions': ['fa_ruling'], 'entry_conditions': ['需要住户允许']})
    if entry['imports'] or skeleton['town_type'] in ('caravan_stop', 'market_town', 'port'):
        options.append({'id': 's_customs', 'name': '旧关卡', 'kind': 'customs_post',
                        'in_district': district('d_admin'), 'reach_via': ['road_main'],
                        'origin': '早年的查验点，路改道后只剩房基',
                        'public_description': '石阶旁留着称重的石砣',
                        'secret': '旧关卡留下的账本记着一笔从未入账的货物',
                        'status': 'ruined', 'risks': [],
                        'related_factions': ['fa_merchant'], 'entry_conditions': []})
    if not options:
        options.append({'id': 's_ruin', 'name': '废屋基', 'kind': 'ruin', 'in_district': None,
                        'reach_via': ['road_main'],
                        'origin': '早期定居点遗留，材料被陆续拆用',
                        'public_description': '几段墙基与一口淤塞的井',
                        'secret': '井底有当年封住的物件，没人愿意下井去取',
                        'status': 'ruined', 'risks': ['塌陷'], 'related_factions': [],
                        'entry_conditions': []})
    order = list(range(len(options)))
    for index in range(len(order) - 1, 0, -1):
        swap = _next(seed, 'sites', index) % (index + 1)
        order[index], order[swap] = order[swap], order[index]
    limit = 2 if skeleton['scale'] in ('hamlet', 'village') else 3
    chosen = [options[i] for i in order[:limit]]
    for site in chosen:
        site['is_residential'] = False
        site['related_factions'] = [f for f in site['related_factions'] if f in faction_ids]
        # Knowledge and passage are different axes: these sites are known to locals
        # (visibility public) even when a given one is sealed or ruined (status).
        site.setdefault('visibility', 'public')
    return chosen


# -------------------------------------------------------------- stage 4: story
EVENT_KINDS = ['economic', 'social', 'hazard', 'conflict', 'discovery']


def build_story(entry, skeleton, socio, built):
    seed = entry['seed']
    site_ids = [s['id'] for s in built['special_sites']]
    district_ids = [d['id'] for d in built['districts']]
    faction_ids = [f['id'] for f in socio['factions']]
    events, clues, secrets = [], [], []

    for index, tension in enumerate(socio['tensions'][:4]):
        site = _pick(seed, site_ids, 'event-site', index) if site_ids else None
        district = _pick(seed, district_ids, 'event-district', index)
        events.append(EventCandidate(
            id=f'e_tension_{index + 1}', title=f'围绕「{tension[:16]}」的分歧',
            kind=EVENT_KINDS[index % len(EVENT_KINDS)], site=site,
            districts=[district] if district else [], factions=faction_ids[:2],
            trigger_conditions=[tension],
            consequences=['相关各方各自加强说法，可信度需要另行核实',
                          '作者采纳后才能写成受校验的故事事件；本版不自动生成任务与奖励']
        ).model_dump(mode='json'))
    for site in built['special_sites']:
        slug = site['id'][2:]
        events.append(EventCandidate(
            id='e_site_' + slug, title=f'{site["name"]}的传闻', kind='discovery',
            site=site['id'], districts=[site['in_district']] if site['in_district'] else [],
            factions=site['related_factions'],
            trigger_conditions=[f'玩家接近{site["name"]}并满足进入条件'],
            consequences=['公开层面只出现可观察的迹象',
                          '秘密只有在作者解封或条件满足后才成为可读事实']
        ).model_dump(mode='json'))
        clues.append(Clue(id='c_' + slug, text=site['public_description'], site=site['id'],
                          holder='').model_dump(mode='json'))
        if site['secret']:
            secrets.append(Secret(id='sk_' + slug, text=site['secret'],
                                  holders=site['related_factions']).model_dump(mode='json'))
    for faction in socio['factions']:
        if faction.get('hidden_goal'):
            secrets.append(Secret(id='sk_' + faction['id'][3:], text=faction['hidden_goal'],
                                  holders=[faction['id']]).model_dump(mode='json'))

    open_questions = []
    if skeleton['warnings']:
        open_questions.append('水源与道路的季节性缺口是否已经有人记在账册或碑上')
    if any(t['direction'] == 'import' for t in socio['trade']):
        open_questions.append('进口一旦中断，谁最先感觉到，谁手里有储备')
    for site in built['special_sites'][:2]:
        open_questions.append(f'{site["name"]}的进入条件是否已经被本地人公开承认')
    return StoryInterface(
        events=events[:8], clues=clues[:8], secrets=secrets[:6],
        open_questions=open_questions[:6],
        warnings=['候选事件不会自动变成可执行任务或奖励；需要作者按现有严格 schema '
                  '写进故事包后才可游玩',
                  '未发现地点、未鉴定资源与隐藏目标不进玩家投影']
    ).model_dump(mode='json')


# --------------------------------------------------------------- full generation
def build_stage(entry, stage, prior):
    if stage == 'skeleton':
        return build_skeleton(entry)
    if stage == 'socioeconomy':
        return build_socioeconomy(entry, prior['skeleton'])
    if stage == 'built':
        return build_built(entry, prior['skeleton'], prior['socioeconomy'])
    return build_story(entry, prior['skeleton'], prior['socioeconomy'], prior['built'])


def town_id(entry):
    return 'town_' + _digest({'seed': entry['seed'], 'site': entry['site_name'],
                              'revision': entry['story_revision'],
                              'terrain': entry['terrain'], 'water': entry['water'],
                              'mode': entry['social_mode']}, 16)


def generate_all(entry):
    """One pass through the four stages, then the cross-stage validator.

    There is no retry loop: a stage either builds from the declared input or the
    generator refuses with a reason.
    """
    if isinstance(entry, TownInput):
        entry = entry.model_dump(mode='json')
    TownInput.model_validate(entry)
    prior = {}
    for stage in ('skeleton', 'socioeconomy', 'built', 'story'):
        prior[stage] = build_stage(entry, stage, prior)
    snapshot = TownSnapshot.model_validate({'generator_version': GENERATOR_VERSION,
                                            'seed': entry['seed'], 'input': entry,
                                            **prior, 'warnings': []}).model_dump(mode='json')
    snapshot['warnings'] = validate_snapshot(snapshot)
    return snapshot


# ------------------------------------------------------------------ validation
def derived_constraints(entry):
    """What the *input* alone forces. Recomputed on every validation.

    Stage data is author-editable, so a snapshot can claim any capacity it likes. These
    numbers are therefore never trusted from the stage: they are recalculated here and
    the stage must agree. That is why "all caps raised together" cannot pass — the
    water capacity is a function of the declared supply, not of what someone typed.
    """
    caps = capacities(entry)
    return {'water_cap': caps['water_cap'], 'local_food_cap': caps['local_food_cap'],
            'import_food_cap': caps['import_food_cap'],
            'transport_cap': caps['transport_cap'],
            'arable_km2': caps['arable_km2']}


def validate_snapshot(snapshot):
    """Cross-stage consistency. Returns warnings; raises ValueError on a hard error.

    Scope, stated plainly: this is a bounded rule checker over *this* schema. It checks
    the quantities the schema declares (capacity, food, labour, per-chain inputs and
    outputs, references, uniqueness) and refuses what it cannot justify. It is not a
    general physical or economic prover, and it does not search for a feasible
    allocation — a chain that cannot be fed is an error, not something to optimise.
    """
    errors = []
    entry = snapshot['input']
    skeleton, socio, built, story = (snapshot['skeleton'], snapshot['socioeconomy'],
                                     snapshot['built'], snapshot['story'])
    cap = skeleton['capacity']
    population = socio['population']['total']

    # --- capacities are derived from the input, not authored --------------
    derived = derived_constraints(entry)
    for field in ('water_cap', 'local_food_cap', 'import_food_cap', 'transport_cap'):
        if cap[field] != derived[field]:
            errors.append(f'承载项 {field} 与输入推导值 {derived[field]} 不一致')
    if cap['water_cap'] <= 0:
        errors.append('没有水源承载能力：缺水的城镇不能正常维持人口')
    if derived['local_food_cap'] + derived['import_food_cap'] <= 0:
        errors.append('本地与进口粮食承载都为零，不能维持人口')
    if population <= 0:
        errors.append('人口为零，无法维持城镇')
    if population > cap['water_cap']:
        errors.append(f'人口 {population} 超过水源承载 {cap["water_cap"]}')
    if population > cap['local_food_cap'] + cap['import_food_cap']:
        errors.append(f'人口 {population} 超过粮食承载 '
                      f'{cap["local_food_cap"] + cap["import_food_cap"]}')
    # The need is declared once, in one fixed unit and period. Comparing only `amount`
    # let an edited unit (t → kg) or period (year → day) shrink the real need a thousand
    # or a few hundred fold while the number stayed the same.
    need_flow = socio['staple_need']
    if need_flow['period'] != 'year' or need_flow['unit'] not in ('t', 'kg'):
        errors.append('口粮需求必须是 t/year 或 kg/year，口径不能改')
    # Exact: tonnes × 1e6 grams per tonne against population × grams per person-year.
    declared_grams = (int(need_flow['amount']) * PERIOD_FACTOR[need_flow['period']]
                      * G_PER_T) // UNIT_DEN[need_flow['unit']]
    if declared_grams != need_grams(population):
        errors.append('口粮需求与人口×人均口粮不一致（按克/年精确比较）')

    # --- population groups ------------------------------------------------
    if sum(g['share_permille'] for g in socio['population']['groups']) != 1000:
        errors.append('人口组群占比之和必须为1000‰')
    if not any(g['role'] == 'majority' for g in socio['population']['groups']):
        errors.append('人口组群必须有一个多数群体')
    _unique(errors, socio['population']['groups'], '人口组群')

    # --- food balance: exact grams, no tolerance --------------------------
    # Every comparison below is integer grams per year. There is no rounding slack: a
    # deficit of a single gram is a deficit, which makes the promise the documentation
    # makes ("a shortfall is refused") literally true instead of approximately true.
    staple_grams = flow_grams(socio['staple'])
    if staple_grams is None:
        errors.append('本地口粮必须使用质量单位（t 或 kg）')
        staple_grams = 0
    produced_grams = _produced_grams(socio, 'grain')
    if staple_grams > produced_grams:
        errors.append('本地口粮数量超过粮食生产链的实际产出')
    consumed_grams = 0
    for chain in socio['chains']:
        for flow in chain['inputs']:
            if flow['resource'] in ('grain', 'chain_grain'):
                consumed_grams += flow_grams(flow) or 0
    export_grams = 0
    import_grams = 0
    for trade in socio['trade']:
        grams = flow_grams(trade)
        if grams is None:
            if trade['kind'] == 'grain':
                errors.append(f'口粮流动 {trade["id"]} 的单位不是质量单位')
            continue
        if trade['direction'] == 'export' and trade['kind'] == 'grain':
            export_grams += grams
        elif trade['direction'] == 'import' and trade['kind'] == 'grain':
            import_grams += grams
    required_grams = need_grams(population)
    if need_flow['amount'] * G_PER_T // UNIT_DEN.get(need_flow['unit'], 1) \
            * PERIOD_FACTOR[need_flow['period']] != required_grams:
        errors.append('口粮需求与人口×人均口粮不一致（按克/年精确比较）')
    available_grams = staple_grams + import_grams - export_grams - consumed_grams
    if available_grams < required_grams:
        errors.append(f'口粮可用量 {available_grams / G_PER_T:.3f} t/年 低于需求 '
                      f'{required_grams / G_PER_T:.3f} t/年'
                      '（精确比较，已扣除出口与生产投入，无取整容差）')
    if required_grams <= 0:
        errors.append('口粮需求为零，人口数据不可信')

    # --- chain inputs must be surveyed, permitted and physically available -
    # Fuel provenance. `materials` is a permission list, never a stock: coal being an
    # allowed material does not mean a seam exists. An actual fuel source is a surveyed,
    # extractable candidate whose own technology is declared and which does not need
    # itself as fuel, or an import with a positive volume.
    fuels = _fuel_sources(entry)
    fuel_import = any(i['kind'] == 'fuel' and i['amount_per_period'] > 0
                      for i in entry['imports'])
    for cycle in _fuel_cycles(entry):
        errors.append('燃料来源存在循环依赖：' + ' → '.join(cycle))
    for chain in socio['chains']:
        if set(chain['requires_technology']) - set(entry['technology']):
            errors.append(f'生产链 {chain["id"]} 要求未申报的技术')
        for flow in chain['inputs']:
            resource = flow['resource']
            if resource.startswith('fuel_'):
                fuel = resource[5:]
                if fuel not in fuels and not fuel_import:
                    errors.append(f'生产链 {chain["id"]} 需要 {fuel} 燃料，'
                                  '但它既未勘探也不可采、也没有进口')
            elif resource in ('grain', 'chain_grain'):
                continue
            elif resource not in _input_resource_ids(entry) and \
                    resource not in {i['id'] for i in entry['imports']} and \
                    resource not in {i['kind'] for i in entry['imports']}:
                errors.append(f'生产链 {chain["id"]} 的输入 {resource} 没有可用来源')
        if chain['energy'] == 'fuel' and not (fuels or fuel_import):
            errors.append(f'生产链 {chain["id"]} 声明燃料能源，却没有可用的已勘探燃料')
        if chain['energy'] == 'water' and entry['water']['source'] not in (
                'river', 'lake', 'aqueduct'):
            errors.append(f'生产链 {chain["id"]} 声明水力，但没有可用水源')
        if chain['output']['resource'] in ('iron_bar', 'copper_bar', 'tin_bar', 'brick',
                                           'salt') and not _chain_has_fuel(
                chain, fuels, fuel_import):
            errors.append(f'生产链 {chain["id"]} 需要加热加工，但没有可用燃料')

    # --- labour -----------------------------------------------------------
    assigned = sum(c['workers'] for c in socio['chains'])
    available = socio['labor']['available_workers']
    if available != population * WORKER_SHARE_PERMILLE // 1000:
        errors.append('可用劳力与人口×劳动年龄比例不一致')
    if socio['labor']['assigned_workers'] != assigned:
        errors.append(f'已分配劳力 {socio["labor"]["assigned_workers"]} '
                      f'应等于各生产链工人之和 {assigned}')
    if assigned > available:
        errors.append(f'产业劳力 {assigned} 超过可用劳力 {available}')

    # --- trade: totals per resource, not row-by-row ------------------------
    road_ids = {r['id'] for r in skeleton['roads']}
    road_kinds = {r['kind'] for r in skeleton['roads']}
    declared = {i['id']: i for i in entry['imports']}
    # Exports are accumulated per resource: three rows at 60% each are one shipment of
    # 180%, so the limit has to be applied to the sum.
    exported = {}
    # Imports are accumulated per declared dependency: one allowance cannot be eaten
    # twice, and each row must match its declaration's kind, unit, period and volume.
    imported_against = {}
    for trade in socio['trade']:
        if trade['direction'] == 'import':
            dependency = declared.get(trade['resource'])
            if dependency is None:
                errors.append(f'进口 {trade["id"]} 没有对应的进口依赖声明')
                continue
            if dependency['kind'] != trade['kind']:
                errors.append(f'进口 {trade["id"]} 的物资种类与声明不一致')
            if dependency['unit'] != trade['unit']:
                errors.append(f'进口 {trade["id"]} 的单位与声明不一致')
            if trade['kind'] == 'grain' and trade['unit'] not in ('t', 'kg'):
                errors.append(f'口粮进口 {trade["id"]} 的单位不是质量单位')
            if not _path_exists(entry, road_ids, road_kinds, trade['via']):
                errors.append(f'进口 {trade["id"]} 的路径 {trade["via"]} 不在已声明的通路中')
            if trade['kind'] == 'grain' and trade['unit'] not in ('t', 'kg'):
                errors.append(f'口粮进口 {trade["id"]} 的单位不是质量单位')
                continue
            moved = unit_units(trade)
            imported_against[trade['resource']] = \
                imported_against.get(trade['resource'], 0) + moved
        else:
            produced = _produced_units(socio, trade['resource'])
            moved = unit_units(trade)
            if produced <= 0:
                errors.append(f'出口 {trade["id"]} 的资源 {trade["resource"]} 没有本地产出')
            exported[trade['resource']] = exported.get(trade['resource'], 0) + moved
    for resource, moved in exported.items():
        produced = _produced_units(socio, resource)
        if produced > 0 and moved > produced:
            errors.append(f'出口 {resource} 合计 {moved} 超过该资源产出 {produced}'
                          '（同一单位精确比较）')
    for dependency_id, moved in imported_against.items():
        dependency = declared[dependency_id]
        allowed = unit_units(mass_flow(dependency['amount_per_period'],
                                       dependency['unit'], dependency['period']))
        if allowed <= 0:
            errors.append(f'进口声明 {dependency_id} 的额度为零，不能算作来源')
        elif moved > allowed:
            errors.append(f'进口 {dependency_id} 合计 {moved} 超过声明额度 {allowed}'
                          '（同一单位精确比较）')

    # --- technology gating on facilities ---------------------------------
    district_ids = {d['id'] for d in built['districts']}
    if len(district_ids) != len(built['districts']):
        errors.append('街区 ID 重复')
    for facility in built['facilities']:
        if facility['kind'] == 'boiler_house' and 'steam_boiler' not in entry['technology']:
            errors.append('未申报蒸汽技术却出现锅炉房')
        if facility['kind'] == 'ward_tower' and 'arcane_ward' not in entry['technology']:
            errors.append('未申报护持技术却出现护持塔')
        if set(facility['requires_technology']) - set(entry['technology']):
            errors.append(f'设施 {facility["id"]} 要求未申报的技术')
        if set(facility['materials']) - set(entry['materials']):
            errors.append(f'设施 {facility["id"]} 使用了未允许的材料')
        if facility['district'] not in district_ids:
            errors.append(f'设施 {facility["id"]} 所在街区不存在')
    _unique(errors, built['facilities'], '设施')
    _unique(errors, built['districts'], '街区')
    _unique(errors, skeleton['roads'], '道路')

    for district in built['districts']:
        if set(district['materials']) - set(entry['materials']):
            errors.append(f'街区 {district["id"]} 使用了未允许的材料')
        if set(district['reach_via']) - road_ids:
            errors.append(f'街区 {district["id"]} 的道路引用不存在')
        if not district['reach_via']:
            errors.append(f'街区 {district["id"]} 没有可达路径')

    # --- factions, sites, events, clues ----------------------------------
    faction_ids = {f['id'] for f in socio['factions']}
    _unique(errors, socio['factions'], '势力')
    for faction in socio['factions']:
        for relation in faction['relations']:
            if relation['faction'] not in faction_ids:
                errors.append(f'势力 {faction["id"]} 的关系引用了不存在的势力')
    _unique(errors, socio['chains'], '生产链')
    _unique(errors, socio['trade'], '贸易条目')
    site_ids = {s['id'] for s in built['special_sites']}
    _unique(errors, built['special_sites'], '特殊地点')
    for site in built['special_sites']:
        if site['in_district'] and site['in_district'] not in district_ids:
            errors.append(f'特殊地点 {site["id"]} 的街区不存在')
        if set(site['reach_via']) - road_ids:
            errors.append(f'特殊地点 {site["id"]} 的道路引用不存在')
        if set(site['related_factions']) - faction_ids:
            errors.append(f'特殊地点 {site["id"]} 的势力引用不存在')
        if site['is_residential']:
            errors.append(f'特殊地点 {site["id"]} 不应被当作居住区建模')
    _unique(errors, story['events'], '事件候选')
    _unique(errors, story['clues'], '线索')
    _unique(errors, story['secrets'], '秘密')
    for event in story['events']:
        if event['site'] and event['site'] not in site_ids:
            errors.append(f'事件 {event["id"]} 的特殊地点引用不存在')
        if set(event['districts']) - district_ids:
            errors.append(f'事件 {event["id"]} 的街区引用不存在')
        if set(event['factions']) - faction_ids:
            errors.append(f'事件 {event["id"]} 的势力引用不存在')
        if event['executable'] or event['status'] != 'candidate_awaiting_author':
            errors.append('V1 的候选事件不能自动变成可执行任务')
    for clue in story['clues']:
        if clue['site'] and clue['site'] not in site_ids:
            errors.append(f'线索 {clue["id"]} 的地点引用不存在')

    # --- housing ---------------------------------------------------------
    if built['housing']['total_houses'] <= 0 and population > 0:
        errors.append('有居民却没有住房汇总')
    covered = sum(row['houses'] * row['household_size'] for row in built['housing']['rows'])
    if population and covered + 0.001 < population * 0.8:
        errors.append(f'住房汇总只能容纳约 {covered:.0f} 人，明显低于人口 {population}')

    if errors:
        raise ValueError('；'.join(dict.fromkeys(errors)))
    return list(dict.fromkeys(
        list(skeleton['warnings']) + list(socio['warnings']) + list(built['warnings'])
        + list(story['warnings'])))


def _unique(errors, rows, label):
    ids = [r['id'] for r in rows]
    if len(set(ids)) != len(ids):
        errors.append(f'{label} ID 重复')


def _input_resource_ids(entry):
    """Input ids a chain may legitimately name (surveyed and extractable only)."""
    ids = set()
    for candidate in entry['resources']:
        if gated_resource(candidate, entry):
            ids.add(candidate['id'])
            ids.add(candidate['kind'])
    return ids


def _fuel_sources(entry):
    """Kinds of fuel that genuinely exist here: surveyed, extractable, technology met.

    A candidate that needs itself (coal burned to mine coal) cannot bootstrap itself and
    is not counted; `_fuel_cycles` reports it separately so the author sees why.
    """
    fuels = set()
    for candidate in entry['resources']:
        if candidate['kind'] not in ('timber', 'coal', 'reed'):
            continue
        if not gated_resource(candidate, entry):
            continue
        if candidate['fuel'] == candidate['kind']:
            continue
        fuels.add(candidate['kind'])
    return fuels


def _fuel_cycles(entry):
    """Bounded (one-hop) circular fuel declarations, reported rather than recursed."""
    cycles = []
    for candidate in entry['resources']:
        if candidate['fuel'] != 'none' and candidate['fuel'] == candidate['kind']:
            cycles.append([candidate['kind'], candidate['kind']])
    return cycles


def _chain_has_fuel(chain, fuels, fuel_import):
    if any(f['resource'].startswith('fuel_') for f in chain['inputs']):
        return True
    return chain['energy'] == 'fuel' and bool(fuels or fuel_import)


def _path_exists(entry, road_ids, road_kinds, via):
    """A declared import path must be one of the routes the town actually has."""
    text = (via or '').strip()
    if not text or text == '未定（无可用路径）':
        return False
    if text in ('roads', 'road'):
        return bool(road_kinds & {'road', 'trail', 'river'})
    if text in ('trail', 'paved', 'highway'):
        return bool(road_kinds & {'road', 'trail'})
    if text in ('river', 'water'):
        return 'river' in road_kinds or entry['transport']['water_route']
    if text == 'sea':
        return entry['transport']['water_route']
    if text in ('人力背运', 'porter'):
        return entry['transport']['portage']
    return text in road_ids


def unit_units(flow):
    """Exact integer quantity per year *in the flow's own unit*.

    Used where both sides already share a unit (exports against output); no float and no
    unit conversion is involved, so equality is exact.
    """
    return int(flow['amount']) * PERIOD_FACTOR[flow['period']]


def _produced_units(socio, resource):
    """Exact integer quantity the chains produce per year, in that resource's unit."""
    total = 0
    for chain in socio['chains']:
        if chain['output']['resource'] == resource:
            total += unit_units(chain['output'])
    return total


def _produced_grams(socio, resource):
    """Exact grams per year for a mass resource, or 0 when it is not mass."""
    total = 0
    for chain in socio['chains']:
        if chain['output']['resource'] != resource:
            continue
        grams = flow_grams(chain['output'])
        total += grams or 0
    return total

# ------------------------------------------------------------------ projections
def public_view(snapshot):
    """Whitelist projection.

    Three rules, each of which was a real leak before it was enforced:

    * ``visibility == 'author'`` never appears — a district, facility or site marked
      author-only is unknown to the town's own people and to the player.
    * ``access`` and ``status`` are *not* knowledge. A private lane is known but not
      enterable, so it stays visible; a public shrine that was never found stays hidden
      even though anyone could walk in. A sealed site is a passage state, so a *known*
      sealed site is still described as sealed.
    * internal ``warnings`` are never copied. Their text and even their count could
      reveal an unsurveyed deposit or an unfound site, so the player gets a fixed
      estimate disclaimer with no numbers.
    """
    skeleton, socio, built = snapshot['skeleton'], snapshot['socioeconomy'], snapshot['built']
    known_districts = {d['id']: d for d in built['districts'] if d['visibility'] == 'public'}
    return {
        'town_id': snapshot.get('town_id') or '',
        'name': skeleton['display_name'],
        'type': skeleton['town_type'],
        'type_label': LABELS.get(skeleton['town_type'], skeleton['town_type']),
        'scale': skeleton['scale'],
        'scale_label': LABELS.get(skeleton['scale'], skeleton['scale']),
        'region': skeleton['region'], 'founded_reason': skeleton['founded_reason'],
        'founded_period': skeleton['founded_period'],
        'siting_reasons': [reason_label(r) for r in skeleton['siting_reasons']],
        'social_mode': snapshot['input']['social_mode'],
        'population': {'total': socio['population']['total'],
                       'groups': [{'label': g['label'], 'role': g['role'],
                                   'share_permille': g['share_permille']}
                                  for g in socio['population']['groups']],
                       'basis': '规则估计，不是普查'},
        'governance': {
            'form': LABELS.get(socio['governance']['form'], socio['governance']['form']),
            'form_id': socio['governance']['form'],
            'authority': socio['governance']['authority'],
            'legitimacy': socio['governance']['legitimacy']},
        'factions': [{'name': f['name'], 'kind': f['kind'], 'public_goal': f['public_goal']}
                     for f in socio['factions']],
        'chains': [{'name': c['name'], 'output': c['output']['name'],
                    'amount': c['output']['amount'], 'unit': c['output']['unit'],
                    'period': c['output']['period'], 'consumers': c['consumers'],
                    'stores': c['stores']} for c in socio['chains']],
        'trade': [{'direction': t['direction'], 'name': t['name'], 'amount': t['amount'],
                   'unit': t['unit'], 'period': t['period'], 'via': t['via']}
                  for t in socio['trade']],
        'reference_note': socio['reference_note'],
        'districts': [{'name': d['name'], 'kind': d['kind'], 'materials': d['materials'],
                       'roof': d['roof'], 'drainage': d['drainage'], 'storeys': d['storeys'],
                       'enterable': d['access'] == 'public', 'note': d['note']}
                      for d in built['districts'] if d['visibility'] == 'public'],
        'facilities': [{'name': f['name'], 'kind': f['kind'], 'note': f['public_note']}
                       for f in built['facilities']
                       if f['condition'] != 'ruined'
                       and f['visibility'] == 'public'
                       and f['district'] in known_districts],
        'housing': {'total_houses': built['housing']['total_houses'],
                    'basis': built['housing']['basis'],
                    'rows': [{'material': r['material'], 'roof': r['roof'],
                              'houses': r['houses'],
                              'household_size': r['household_size'], 'note': r['note']}
                             for r in built['housing']['rows']]},
        'style': {'materials': built['style']['materials'], 'roof': built['style']['roof'],
                  'drainage': built['style']['drainage'],
                  'wall_note': built['style']['wall_note'],
                  'explanations': [{'claim': e['claim'], 'because': e['because']}
                                   for e in built['style']['explanations']]},
        'water': {'source': skeleton['water']['source'],
                  'source_label': LABELS.get(skeleton['water']['source'],
                                             skeleton['water']['source']),
                  'storage': skeleton['water']['storage'], 'note': skeleton['water']['note']},
        'roads': [{'name': r['name'], 'kind': r['kind'], 'destination': r['destination'],
                   'travel_days': r['travel_days'],
                   'seasonal_closed_days': r['seasonal_closed_days']}
                  for r in skeleton['roads']],
        'special_sites': [{'name': s['name'], 'kind': s['kind'],
                           'description': s['public_description'], 'status': s['status'],
                           'enterable': s['status'] not in ('sealed', 'ruined'),
                           'risks': s['risks'], 'entry_conditions': s['entry_conditions']}
                          for s in built['special_sites'] if s['visibility'] == 'public'],
        # A fixed disclaimer with no internal text and no counts: a count alone would
        # tell the player how many things the town is hiding.
        'warnings': ['人口、产量与承载都是规则估计，不是普查或实测'],
    }
def player_view(snapshot):
    """Alias kept explicit: the player projection is exactly the public whitelist."""
    return public_view(snapshot)


def author_view(snapshot):
    return {'town_id': snapshot.get('town_id') or '', 'snapshot': snapshot}


def context_summary(snapshot, limit=1200):
    """Bounded public summary for a model prompt: never the whole town, never secrets."""
    view = public_view(snapshot)
    lines = [f'{view["name"]}（{view["type_label"]}，{view["scale_label"]}）：'
             f'{view["founded_reason"]}',
             f'人口约 {view["population"]["total"]} 人；'
             + '、'.join(f'{g["label"]} {g["share_permille"] / 10:.0f}%'
                        for g in view['population']['groups'][:3]),
             f'治理：{view["governance"]["form"]} —— {view["governance"]["authority"]}']
    if view['chains']:
        lines.append('主要生计：' + '；'.join(
            f'{c["name"]}（{c["amount"]}{c["unit"]}/{c["period"]}）'
            for c in view['chains'][:3]))
    if view['trade']:
        lines.append('进出：' + '；'.join(
            f'{"进口" if t["direction"] == "import" else "外销"} {t["name"]}'
            for t in view['trade'][:3]))
    lines.append('建筑：' + '；'.join(f'{d["name"]}（{d["roof"]}）'
                                    for d in view['districts'][:4]))
    if view['special_sites']:
        lines.append('可听说的地方：' + '；'.join(s['name'] for s in view['special_sites'][:3]))
    text = '\n'.join(lines)
    return text if len(text) <= limit else text[:limit].rstrip() + '…'



# -------------------------------------------------------------------- presets
def _base(story_revision):
    return {'story_revision': story_revision,
            'map': {'input_version': 'hand_sample_v1',
                    'coordinate_system': '架空示意经纬度（经度在前、纬度在后）',
                    'scale': '1 格约 2 公里，仅作示意图，不用于计算行程',
                    'source': 'manual_sample'}}


def preset_entry(preset, seed, site_name='', story_revision='0' * 16):
    """Three authored inputs that must produce explainably different towns.

    These are examples of a complete request, not hidden defaults: every field is
    explicit so the same request can be reviewed, replayed and diffed.
    """
    if preset not in PRESETS:
        raise ValueError('未知的预置输入；可选 ' + '、'.join(PRESETS))
    base = _base(story_revision)
    if preset == 'wet_valley':
        return TownInput(**{
            **base, 'seed': seed, 'site': 'manual_sample',
            'site_name': site_name or '泽口', 'region': '湿润河谷',
            'founded_period': '第三代定居者时期（架空）',
            'terrain': {'elevation_m': 120.0, 'slope_deg': 3.0, 'precipitation_mm': 1100.0,
                        'temperature_c': 16.0, 'freshwater': 0.9, 'soil_fertility': 0.85,
                        'flood_risk': 0.45, 'area_km2': 260.0, 'coordinates': (118.2, 30.4)},
            'water': {'source': 'river', 'reliability': 0.92, 'daily_capacity_l': 900000,
                      'storage': 'tank', 'distance_km': 0.4},
            'transport': {'road': 'paved', 'water_route': True, 'portage': False,
                          'seasonal_closed_days': 12, 'nearest_market_days': 1},
            'resources': [
                {'id': 'res_grain', 'kind': 'grain', 'abundance': 0.9,
                 'accessibility': 0.9, 'surveyed': True},
                {'id': 'res_timber', 'kind': 'timber', 'abundance': 0.7,
                 'accessibility': 0.7, 'surveyed': True},
                {'id': 'res_reed', 'kind': 'reed', 'abundance': 0.8,
                 'accessibility': 0.85, 'surveyed': True},
                {'id': 'res_fish', 'kind': 'fish', 'abundance': 0.6,
                 'accessibility': 0.8, 'surveyed': True}],
            'materials': ['timber', 'stone', 'clay_brick', 'fired_tile', 'thatch', 'reed',
                          'lime_plaster'],
            'technology': ['masonry', 'timber_frame', 'kiln', 'water_wheel', 'cistern'],
            'cultures': [{'id': 'cu_river', 'name': '河岸稻作文化', 'roof': 'gable_tile',
                          'heating': 'open_hearth', 'household': 'extended',
                          'note': '沿灌渠分户，屋顶坡度按雨季排水'}],
            'peoples': [{'id': 'pe_standard', 'name': '本地人', 'average_height_cm': 168,
                         'min_ceiling_m': 2.4, 'space_factor': 1.0}],
            'social_mode': 'realistic_reference',
            'realistic': {
                'region': '东亚季风区低地河谷（类比参考）', 'period': '约12—14世纪',
                'polity_scope': '地方集市与村社惯行，不引用具体王朝法令',
                'evidence_level': 'regional_analogue',
                'uncertainty': '水利组织、税制与户口数字在史料中差异很大；本工具只用方向性'
                               '关系（水多—稻作—聚落密），不做定量复原',
                'adaptation': '地名、机构名与节期均为架空，只保留因果方向'},
            'imports': [{'id': 'imp_salt', 'name': '盐', 'kind': 'salt',
                         'amount_per_period': 40, 'unit': 't', 'period': 'year',
                         'via': 'river', 'note': '上游盐场换粮'}],
            'bindings': [{'id': 'el_irrigation_custom', 'kind': 'element', 'version': 'v1',
                          'summary': '灌渠轮水惯例：按田亩与时段分配取水'}],
            'notes': '湿河谷示例：水多、可耕地连片、水路通行；洪水风险偏高。'})

    if preset == 'cold_mountain_mine':
        return TownInput(**{
            **base, 'seed': seed, 'site': 'selected_location',
            'site_name': site_name or '黑石沟', 'site_location_id': 'place_mine',
            'region': '寒冷山地', 'founded_period': '开矿第三代（架空）',
            'terrain': {'elevation_m': 1650.0, 'slope_deg': 22.0, 'precipitation_mm': 520.0,
                        'temperature_c': -1.0, 'freshwater': 0.45, 'soil_fertility': 0.22,
                        'flood_risk': 0.12, 'area_km2': 40.0, 'coordinates': (86.1, 43.2)},
            'water': {'source': 'spring', 'reliability': 0.75, 'daily_capacity_l': 200000,
                      'storage': 'cistern', 'distance_km': 0.6},
            'transport': {'road': 'track', 'water_route': False, 'portage': True,
                          'seasonal_closed_days': 70, 'nearest_market_days': 4},
            'resources': [
                {'id': 'res_iron', 'kind': 'iron', 'abundance': 0.75, 'accessibility': 0.55,
                 'surveyed': True, 'requires_technology': ['mine_shaft', 'forge'],
                 'fuel': 'coal'},
                {'id': 'res_coal', 'kind': 'coal', 'abundance': 0.6, 'accessibility': 0.5,
                 'surveyed': True, 'requires_technology': ['mine_shaft']},
                {'id': 'res_timber', 'kind': 'timber', 'abundance': 0.35,
                 'accessibility': 0.3, 'surveyed': True}],
            'materials': ['stone', 'cut_stone', 'timber', 'slate', 'iron', 'lime_plaster'],
            'technology': ['masonry', 'timber_frame', 'forge', 'mine_shaft', 'cistern',
                           'snow_load_engineering'],
            'cultures': [{'id': 'cu_highland', 'name': '高地矿工聚居', 'roof': 'steep_slate',
                          'heating': 'stove', 'household': 'nuclear',
                          'note': '屋面陡坡排雪，院内堆料'}],
            'peoples': [
                {'id': 'pe_standard', 'name': '本地人', 'average_height_cm': 170,
                 'min_ceiling_m': 2.4, 'space_factor': 1.0},
                {'id': 'pe_stout', 'name': '山地体型', 'average_height_cm': 162,
                 'min_ceiling_m': 2.2, 'space_factor': 1.15,
                 'need_note': '层高可略低，储物与晾晒空间需要加大'}],
            'social_mode': 'artistic_extrapolation',
            'artistic': {'prototypes': ['近代早期欧洲山地矿区', '高原自给农牧'],
                         'inventions': ['矿权与水源由同一个董事会裁定'],
                         'design_goal': '让燃料、雪季与矿权成为可玩的约束，而不是装饰',
                         'counterexamples': '不采用“矿镇必然暴富”的写法'},
            'imports': [
                {'id': 'imp_grain', 'name': '粮食', 'kind': 'grain',
                 'amount_per_period': 500, 'unit': 't', 'period': 'year', 'via': 'road',
                 'note': '山口外换粮'},
                {'id': 'imp_timber', 'name': '坑木与柴', 'kind': 'timber',
                 'amount_per_period': 300, 'unit': 'm3', 'period': 'year', 'via': 'road',
                 'note': '本地林场不够用'}],
            'bindings': [{'id': 'el_mine_law', 'kind': 'rule_template', 'version': 'v2',
                          'summary': '矿口计时与配额惯例：按班组计工，超额部分由矿主抽成'}],
            'notes': '冷山矿镇示例：水少、粮少，燃料与坑木都要运进来；冬季封路。'})

    return TownInput(**{
        **base, 'seed': seed, 'site': 'manual_sample',
        'site_name': site_name or '沙垒驿', 'region': '干旱商路绿洲',
        'founded_period': '商路改道后第二代（架空）',
        'terrain': {'elevation_m': 620.0, 'slope_deg': 5.0, 'precipitation_mm': 90.0,
                    'temperature_c': 29.0, 'freshwater': 0.35, 'soil_fertility': 0.12,
                    'flood_risk': 0.05, 'area_km2': 30.0, 'coordinates': (40.2, 33.1)},
        'water': {'source': 'spring', 'reliability': 0.85, 'daily_capacity_l': 300000,
                  'storage': 'cistern', 'distance_km': 0.2},
        'transport': {'road': 'highway', 'water_route': False, 'portage': False,
                      'seasonal_closed_days': 0, 'nearest_market_days': 6},
        'resources': [
            {'id': 'res_salt', 'kind': 'salt', 'abundance': 0.7, 'accessibility': 0.8,
             'surveyed': True, 'fuel': 'timber'},
            {'id': 'res_wool', 'kind': 'wool', 'abundance': 0.5, 'accessibility': 0.6,
             'surveyed': True},
            {'id': 'res_herb', 'kind': 'herb', 'abundance': 0.4, 'accessibility': 0.5,
             'surveyed': True},
            # Present but not surveyed: it must never become output or an inventory.
            {'id': 'res_iron', 'kind': 'iron', 'abundance': 0.9, 'accessibility': 0.1,
             'surveyed': False, 'requires_technology': ['mine_shaft']}],
        'materials': ['mud_brick', 'rammed_earth', 'stone', 'timber', 'felt', 'hide',
                      'thatch'],
        'technology': ['timber_frame', 'cistern', 'kiln'],
        'cultures': [
            {'id': 'cu_oasis', 'name': '绿洲商路文化', 'roof': 'flat_mud', 'heating': 'none',
             'household': 'extended', 'note': '平屋顶作晾晒与纳凉，厚墙抵日间高温'},
            {'id': 'cu_caravan', 'name': '商队习俗', 'roof': 'monopitch', 'heating': 'none',
             'household': 'nuclear', 'note': '临时棚屋，随队移动'}],
        'peoples': [{'id': 'pe_standard', 'name': '本地人', 'average_height_cm': 170,
                     'min_ceiling_m': 2.5, 'space_factor': 1.0}],
        'social_mode': 'artistic_extrapolation',
        'artistic': {'prototypes': ['撒哈拉与中亚绿洲商站', '丝路驿站客院'],
                     'inventions': ['水源由商团与本地家族共管的双钥匙制度'],
                     'design_goal': '把水权与过境费变成日常冲突来源，同时不虚构产量',
                     'counterexamples': '不假设绿洲必然富裕或必然独立'},
        'imports': [
            {'id': 'imp_grain', 'name': '粮食', 'kind': 'grain', 'amount_per_period': 900,
             'unit': 't', 'period': 'year', 'via': 'road', 'note': '沿干道运入'},
            {'id': 'imp_timber', 'name': '木料与柴', 'kind': 'timber',
             'amount_per_period': 120, 'unit': 'm3', 'period': 'year', 'via': 'road',
             'note': '本地无林，盐灶也要烧柴'},
            # The salt works burn firewood; with no woodland this is a real fuel import,
            # not merely an allowed material standing in for a stock.
            {'id': 'imp_fuel_wood', 'name': '盐灶用柴', 'kind': 'fuel',
             'amount_per_period': 60, 'unit': 't', 'period': 'year', 'via': 'road',
             'note': '运来的柴禾，专供盐灶'}],
        'bindings': [{'id': 'el_water_keys', 'kind': 'element', 'version': 'v1',
                      'summary': '水源双钥匙：商团与本地家族各持一把，开闸需双方在场'}],
        'notes': '干旱绿洲示例：水由泉眼与蓄水决定，粮与柴都靠干道运入；'
                 '本地有一座未勘探的铁矿，不得直接写成产量。'})
