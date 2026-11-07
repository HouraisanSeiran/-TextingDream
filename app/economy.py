# -*- coding: utf-8 -*-
"""经济规则：三种经济形态 + 商人配置 + 本地价格修正（全部整数铜币，无随机、无模型）。

单位约定（docs/units.md）：货币十进制，10 铜币 = 1 银币，10 银币 = 1 金币；价格一律以整数铜币
存储（1 铜币沿用原「1 便士」的数值，旧价格不用换算）。重量、长度、容量一律公制。

规格见 docs/economy-design.md。本模块只做「规则与价格」，不碰任何状态：
真正的买、卖、以物易物、讨价还价由 ``app/trade.py`` 在引擎动作里结算。

* 三种形态：``feudal`` 封建经济、``early_capitalism`` 早期资本主义、``market`` 工业资本主义。
  作者可在 ``story.mechanics.economy.regime`` 指定；没指定时按世界设定的科技档位推断。
* ``story.mechanics.economy`` 另可声明商人（地点、所卖商品及基准价、收购哪些货、对应
  rewards 付款账户）、集市日、领地关税、本地出产与缺货、季节修正表。没有商人时本模块的行为与
  上一版完全相同（只给提示词一份规矩）。
* 价格修正顺序：基准价 → 本地出产 / 缺货 → 关税（外国货）→ 季节 → 形态报价（外地货倍率、
  开价 / 底价 / 收购价）。每一步都是 ``price * 百分比 // 100``。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

REGIMES = ('feudal', 'early_capitalism', 'market')
TECH_DEFAULT = {'classical': 'feudal', 'medieval': 'feudal', 'renaissance': 'early_capitalism',
                'steam': 'market', 'early_modern': 'market'}

# 价格锚点：整数铜币（数值沿用原便士口径）。
ANCHORS = ['麦酒一杯（约 0.5 升）2 铜币', '一袋干麦（约 25 千克）12 铜币', '渡船 12 铜币', '桥费 8 铜币',
           '半日短工 6–12 铜币', '币制：10 铜币 = 1 银币，10 银币 = 1 金币（十进制）']
# 叙述与对话里的计量单位规矩。
UNITS = '重量、长度、容量一律用公制：克、千克、吨、毫米、厘米、米、公里、毫升、升；不用磅、盎司、英尺、英寸、英里、加仑、品脱'

# 商人报价（相对基准价，百分比，整数运算）。
# sell_markup：商人卖给你；buy_back：商人收你的货；floor：讨价还价最低能压到；
# imported：外地货倍率；barter：这种经济里以物易物是否常见。
REGIME_INFO = {
    'feudal': {
        'label': '封建经济',
        'traits': [
            '自给自足为主：庄园和村落自己种、自己织，市场只补缺口',
            '集市小、按集市日开，常设店铺少，外地货稀少且贵',
            '以物易物和以劳力抵账很常见，偏远处几乎见不到钱',
            '钱按金属算：银币铜币日常用，金币少见；外国钱、剪边钱按成色重量折价',
            '地租、劳役、什一税是领主和教会的固定收取，不是买卖',
            '跨领地往来少，过关卡交通行税；行会把持本地手艺与定价',
        ],
        'currency': '足值金属铸币，没有纸币、银行存款与汇率',
        'sell_markup': 130, 'buy_back': 50, 'floor': 105, 'imported': 200,
        'barter': True,
    },
    'early_capitalism': {
        'label': '早期资本主义',
        'traits': [
            '汇票与早期银行出现：大宗和远途交易可用汇票、票据结算，日常小额仍用金属铸币',
            '特许贸易公司垄断远洋贸易，殖民地货物（香料、糖、烟草、茶）进入城市，价格高昂',
            '价格革命：美洲金银流入，物价缓慢上涨，固定地租和工资吃亏',
            '行会仍在，但包买商把原料发给乡下织工、按件收货，侵蚀行会的定价权',
            '集市变成城里的常设市场和交易所，每天开门；乡村仍以集市日和以物易物为主',
            '各国铸币成色不一，兑换商按成色与汇率折算，从中抽成',
        ],
        'currency': '金银铸币为主，大额用汇票与银行票据；纸币尚未通行（个别银行券除外）',
        'sell_markup': 120, 'buy_back': 55, 'floor': 102, 'imported': 150,
        'barter': True,
    },
    'market': {
        'label': '工业资本主义',
        'traits': [
            '商品生产为主：工厂按规格大量生产，日用品便宜而统一',
            '店铺天天营业、明码标价，城市里几乎一切都能用钱买到',
            '劳动换工资，雇主与雇工按日或按周结算',
            '银行与纸币通行，有存款、借贷和利息，国与国之间有汇率',
            '铁路轮船缩小地区差价，商路中断时价格上涨',
            '以物易物只在乡下或困境里出现，多数人讨价还价的余地小',
        ],
        'currency': '银行或国家发行的纸币为主，钱币是辅币，按面额使用',
        'sell_markup': 115, 'buy_back': 60, 'floor': 100, 'imported': 125,
        'barter': False,
    },
}
MAX_NOTE = 600

# 本地修正（百分比）：本地出产的便宜、本地缺的贵。
LOCAL_PRODUCES_PCT = 85
LOCAL_LACKS_PCT = 125

# 季节：按一年 365 天的年内日序分段（与 geography.Calendar 的口径一致，默认起始第 80 天）。
SEASON_LABEL = {'spring': '春', 'summer': '夏', 'autumn': '秋', 'winter': '冬'}
# 季节修正表（百分比）：类别 → 季节 → 倍率。作者可用 ``season_pct`` 增补或覆盖整个类别。
SEASON_PCT = {
    'grain': {'spring': 125, 'summer': 110, 'autumn': 80, 'winter': 100},    # 秋收便宜、青黄不接贵
    'fuel': {'spring': 95, 'summer': 85, 'autumn': 105, 'winter': 130},
    'produce': {'spring': 105, 'summer': 85, 'autumn': 80, 'winter': 125},   # 果蔬
}
MAX_MERCHANTS = 12
MAX_GOODS = 24


class EconomyError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


_ID = r'^[A-Za-z0-9_-]{1,60}$'
_PRICE = Field(ge=0, le=10_000_000, strict=True)


class Good(_Strict):
    """一种商品。``item`` 指向故事包里的唯一物品（进背包）；否则是可数的普通货物（进货物袋）。"""
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=40)
    base: int = _PRICE                    # 基准价，整数铜币
    unit: str = Field(default='', max_length=8)
    item: str = ''
    resource: str = Field(default='', max_length=40)   # 与城镇资源 / 产出的 resource 对齐，用于出产 / 缺货
    season_class: str = Field(default='', max_length=20)
    origin: Literal['local', 'imported'] = 'local'
    origin_polity: str = Field(default='', max_length=60)
    stock: int | None = Field(default=None, ge=1, le=1000, strict=True)   # 每天现货；None = 不限
    always: bool = False                  # 封建经济里不受集市日限制（如酒馆的麦酒）


class Merchant(_Strict):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=40)
    location: str
    npc: str = ''                         # 可选：对应人物，讨价还价时作为社交目标
    account: str                          # rewards 付款账户（玩家不可见）
    sells: list[Good] = Field(default_factory=list, max_length=MAX_GOODS)
    buys: list[Good] = Field(default_factory=list, max_length=MAX_GOODS)
    barter: bool | None = None            # None = 随经济形态
    schedule: Literal['regime', 'market', 'daily'] = 'regime'
    haggle: bool = True
    haggle_difficulty: float = Field(default=0.5, ge=0, le=1)


class MarketDay(_Strict):
    every_days: int = Field(default=7, ge=2, le=30, strict=True)
    offset: int = Field(default=0, ge=0, le=29, strict=True)


class Polity(_Strict):
    customs: int = Field(default=0, ge=0, le=100, strict=True)   # 外国货关税 %


class Place(_Strict):
    polity: str = ''
    produces: list[str] = Field(default_factory=list, max_length=20)
    lacks: list[str] = Field(default_factory=list, max_length=20)
    town_location: str = ''               # 城镇数据挂在另一个地点上时指过去（如集市是城里的子地点）


class Economy(_Strict):
    regime: Literal['feudal', 'early_capitalism', 'market'] | None = None
    note: str = Field(default='', max_length=MAX_NOTE, strict=True)
    currency: str = ''
    market_day: MarketDay = Field(default_factory=MarketDay)
    polities: dict[str, Polity] = Field(default_factory=dict)
    places: dict[str, Place] = Field(default_factory=dict)
    season_pct: dict[str, dict[Literal['spring', 'summer', 'autumn', 'winter'],
                               int]] = Field(default_factory=dict)
    merchants: list[Merchant] = Field(default_factory=list, max_length=MAX_MERCHANTS)


def config(story):
    """原始配置（dict）或 None。"""
    return ((story or {}).get('mechanics') or {}).get('economy')


def model(story):
    """解析后的配置或 None；配置非法会抛 EconomyError。"""
    raw = config(story)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise EconomyError('经济配置必须是对象')
    try:
        return Economy.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = '.'.join(str(p) for p in first['loc'])
        if first['type'] == 'extra_forbidden':
            raise EconomyError('经济配置有未知字段：' + where)
        raise EconomyError('经济配置无效（%s）：%s' % (where, first['msg']))


def merchants_declared(story):
    cfg = model(story)
    return bool(cfg and cfg.merchants)


def season_table(cfg):
    table = {k: dict(v) for k, v in SEASON_PCT.items()}
    for cls, row in (cfg.season_pct if cfg else {}).items():
        table[cls] = {**table.get(cls, {}), **row}
    return table


def validate(story, characters=None):
    """故事包提交时调用；没有 economy 配置合法。商人相关引用在这里一并核对。"""
    cfg = model(story)
    if cfg is None:
        return
    if not cfg.merchants and not (cfg.places or cfg.polities or cfg.currency or cfg.season_pct):
        return
    locations = {p['id'] for p in (story or {}).get('locations') or []}
    items = {i['id'] for i in (story or {}).get('items') or []}
    chars = {c['id'] for c in (characters or {}).get('characters') or []} if characters else None
    for loc, place in cfg.places.items():
        if locations and loc not in locations:
            raise EconomyError('经济配置的地点不存在：' + loc)
        if place.polity and place.polity not in cfg.polities:
            raise EconomyError('地点 %s 的领地未声明：%s' % (loc, place.polity))
        if place.town_location and locations and place.town_location not in locations:
            raise EconomyError('地点 %s 的城镇地点不存在：%s' % (loc, place.town_location))
    for pid in cfg.polities:
        if not pid or len(pid) > 60:
            raise EconomyError('领地 id 无效')
    table = season_table(cfg)
    if not cfg.merchants:
        return
    from . import rewards
    rcfg = rewards.rules(story)
    if rcfg is None:
        raise EconomyError('声明商人需要先声明 mechanics.rewards（货币与付款账户）')
    if cfg.currency not in {c.id for c in rcfg.currencies}:
        raise EconomyError('经济配置的 currency 必须是 rewards 里声明的货币：%r' % (cfg.currency,))
    accounts = {a.id: a for a in rcfg.accounts}
    seen, kinds = set(), {}
    for m in cfg.merchants:
        if m.id in seen:
            raise EconomyError('商人 id 重复：' + m.id)
        seen.add(m.id)
        if locations and m.location not in locations:
            raise EconomyError('商人 %s 的地点不存在：%s' % (m.id, m.location))
        if m.npc and chars is not None and m.npc not in chars:
            raise EconomyError('商人 %s 的人物不存在：%s' % (m.id, m.npc))
        acct = accounts.get(m.account)
        if acct is None:
            raise EconomyError('商人 %s 的付款账户未在 rewards 声明：%s' % (m.id, m.account))
        if acct.currency != cfg.currency:
            raise EconomyError('商人 %s 的付款账户币种与经济配置的 currency 不一致' % m.id)
        for label, rows in (('sells', m.sells), ('buys', m.buys)):
            ids = [g.id for g in rows]
            if len(set(ids)) != len(ids):
                raise EconomyError('商人 %s 的 %s 里商品 id 重复' % (m.id, label))
            for g in rows:
                if g.item and (g.item not in items):
                    raise EconomyError('商品 %s 引用了不存在的物品：%s' % (g.id, g.item))
                if g.season_class and g.season_class not in table:
                    raise EconomyError('商品 %s 的季节类别未定义：%s' % (g.id, g.season_class))
                if g.origin_polity and g.origin_polity not in cfg.polities:
                    raise EconomyError('商品 %s 的来源领地未声明：%s' % (g.id, g.origin_polity))
                if g.origin == 'local' and g.origin_polity:
                    raise EconomyError('商品 %s：本地货不应声明来源领地' % g.id)
                if kinds.setdefault(g.id, g.item) != g.item:
                    raise EconomyError('商品 id %s 在不同商人处对应了不同的物品' % g.id)


def regime_of(story):
    """显式配置优先；否则按世界设定的科技档位；都没有时 None。"""
    raw = config(story) or {}
    if raw.get('regime') in REGIMES:
        return raw['regime']
    tech = (((story or {}).get('worldview') or {}).get('setting') or {}).get('tech')
    return TECH_DEFAULT.get(tech)


def quote(base, regime, imported=False):
    """一件货的买卖价边界（整数便士）。base 为基准价。

    返回 ask（商人开价）、floor（讨价还价最低成交价）、bid（商人收购价）。
    高买低卖：商人卖给你 ask ≥ floor > bid，差价是他的利润。
    """
    if regime not in REGIME_INFO:
        raise EconomyError('未知经济形态：%r' % (regime,))
    if not isinstance(base, int) or isinstance(base, bool) or base < 0:
        raise EconomyError('基准价必须是非负整数便士')
    info = REGIME_INFO[regime]
    price = base * info['imported'] // 100 if imported else base
    ask = max(price, price * info['sell_markup'] // 100)
    bid = price * info['buy_back'] // 100
    # 底价不低于基准价对应比例，也必须严格高于收购价（否则商人倒贴），且不高于开价。
    floor = min(ask, max(price * info['floor'] // 100, bid + 1 if price else 0))
    return {'ask': ask, 'floor': floor, 'bid': bid}


# ------------------------------------------------------------------ 时间：集市日与季节


def day_of(session):
    """第几天（从 1 开始）。时间是 ``session['time']``，单位游戏小时（local_rules 的口径）。"""
    return int((session or {}).get('time', 0)) // 24 + 1


def is_market_day(cfg, session):
    md = cfg.market_day if cfg else MarketDay()
    return (day_of(session) - 1 - md.offset) % md.every_days == 0


def days_to_market(cfg, session):
    md = cfg.market_day if cfg else MarketDay()
    return (md.offset - (day_of(session) - 1)) % md.every_days


def season_of(story, session):
    cal = ((story or {}).get('mechanics') or {}).get('calendar') or {}
    start = cal.get('start_day_of_year', 80)
    doy = (start + day_of(session) - 2) % 365 + 1
    if 60 <= doy < 152:
        return 'spring'
    if 152 <= doy < 244:
        return 'summer'
    if 244 <= doy < 335:
        return 'autumn'
    return 'winter'


def merchant_open(cfg, regime, merchant, session):
    """商人今天是否开门做常规生意。封建经济默认只在集市日；其余形态天天开。"""
    if merchant.schedule == 'daily':
        return True
    if merchant.schedule == 'market':
        return is_market_day(cfg, session)
    return regime != 'feudal' or is_market_day(cfg, session)


def good_available(cfg, regime, merchant, good, session):
    return good.always or merchant_open(cfg, regime, merchant, session)


# ------------------------------------------------------------------ 城镇数据（可选）


def town_profile(story, location_id):
    """从已采纳到该地点的城镇快照里取「出产 / 缺货」资源名；没有城镇数据返回空集合。

    出产 = 产业链产出 + 出口贸易品；缺货 = 进口贸易品 + 主粮缺口（产出小于需求）。
    只读故事包里随包携带的快照，不读城镇库、不联网。
    """
    produces, lacks = set(), set()
    if not location_id:
        return {'produces': produces, 'lacks': lacks, 'found': False}
    from . import towns_store
    entry = next((e for e in towns_store.package_entries(story)
                  if e.get('location_id') == location_id), None)
    if entry is None:
        return {'produces': produces, 'lacks': lacks, 'found': False}
    eco = (entry.get('snapshot') or {}).get('socioeconomy') or {}
    for chain in eco.get('chains') or []:
        key = (chain.get('output') or {}).get('resource')
        if key:
            produces.add(key)
    for flow in eco.get('trade') or []:
        key = flow.get('resource')
        if not key:
            continue
        (produces if flow.get('direction') == 'export' else lacks).add(key)
    staple, need = eco.get('staple') or {}, eco.get('staple_need') or {}
    if staple.get('resource') and need.get('amount', 0) > staple.get('amount', 0):
        lacks.add(staple['resource'])
    return {'produces': produces, 'lacks': lacks, 'found': True}


def local_sets(story, cfg, location_id):
    """作者声明与城镇数据合并后的（出产, 缺货, 领地）。作者声明在前，城镇数据补充。"""
    place = cfg.places.get(location_id) if cfg else None
    town_at = (place.town_location if place and place.town_location else location_id)
    town = town_profile(story, town_at)
    produces = set(place.produces if place else []) | town['produces']
    lacks = set(place.lacks if place else []) | town['lacks']
    return produces, lacks, (place.polity if place else ''), town['found']


def price_for(story, session, merchant, good, cfg=None, regime=None):
    """一件商品在该商人处、此刻的 ask / floor / bid 与修正说明。纯函数，不读随机。"""
    cfg = cfg or model(story)
    regime = regime or regime_of(story) or 'feudal'
    produces, lacks, polity, _ = local_sets(story, cfg, merchant.location)
    key = good.resource or good.id
    price, notes = good.base, []
    imported = good.origin == 'imported'
    if not imported and key in produces:
        price = price * LOCAL_PRODUCES_PCT // 100
        notes.append('本地出产 %d%%' % LOCAL_PRODUCES_PCT)
    elif key in lacks:
        price = price * LOCAL_LACKS_PCT // 100
        notes.append('本地缺货 %d%%' % LOCAL_LACKS_PCT)
    if imported and good.origin_polity and polity and good.origin_polity != polity:
        customs = cfg.polities[polity].customs
        if customs:
            price = price * (100 + customs) // 100
            notes.append('关税 +%d%%' % customs)
    if good.season_class:
        season = season_of(story, session)
        pct = season_table(cfg).get(good.season_class, {}).get(season, 100)
        if pct != 100:
            price = price * pct // 100
            notes.append('%s季 %d%%' % (SEASON_LABEL[season], pct))
    if good.base and price < 1:
        price = 1
    if imported:
        notes.append('外地货 %d%%' % REGIME_INFO[regime]['imported'])
    row = quote(price, regime, imported=imported)
    row['notes'] = notes
    row['imported'] = imported
    return row


def prompt_block(story, session=None):
    """进入叙事上下文的经济规矩；无法确定经济形态时 None（老包提示词不变）。

    声明了商人且给了 ``session`` 时，再附上当前地点的本地行情（商品开价 / 收购价、今天是否开市）。
    """
    regime = regime_of(story)
    if regime is None:
        return None
    info = REGIME_INFO[regime]
    pct = lambda k: '%d%%' % info[k]
    block = {
        'regime': info['label'],
        'traits': info['traits'],
        'currency': info['currency'],
        'price_anchors': ANCHORS,
        'units': UNITS,
        'trading': [
            '商人卖价约为基准价的 ' + pct('sell_markup') + '，收购价约 ' + pct('buy_back') + '（高买低卖是常态）',
            '讨价还价最多压到基准价的 ' + pct('floor') + '，再低商人宁可不卖',
            '外地货约为本地价的 ' + pct('imported'),
            '可以以物易物或以劳力抵账，按双方估值撮合' if info['barter'] else '一般只收钱，以物易物要对方愿意',
            '对话里谈成的价钱只是口头约定：钱和货是否易手以引擎结算为准',
        ],
    }
    note = (config(story) or {}).get('note')
    if note:
        block['note'] = note
    cfg = model(story)
    if cfg and cfg.merchants and session is not None:
        here = [m for m in cfg.merchants if m.location == session.get('location')]
        if here:
            block['local_market'] = _local_market(story, session, cfg, regime, here)
    return block


def _local_market(story, session, cfg, regime, here):
    """当前地点商人的行情摘要（只含玩家能在信息栏看到的开价与收购价，不含底价）。"""
    out = {'season': SEASON_LABEL[season_of(story, session)],
           'market_day_today': is_market_day(cfg, session), 'merchants': []}
    for m in here:
        row = {'name': m.name, 'open_today': merchant_open(cfg, regime, m, session), 'sells': [], 'buys': []}
        for g in m.sells[:6]:
            p = price_for(story, session, m, g, cfg, regime)
            row['sells'].append('%s 开价 %d' % (g.name, p['ask']))
        for g in m.buys[:6]:
            p = price_for(story, session, m, g, cfg, regime)
            row['buys'].append('%s 收购 %d' % (g.name, p['bid']))
        out['merchants'].append(row)
    out['rule'] = '价格单位为铜币（10 铜币 = 1 银币）；成交与否以引擎结算为准，口头谈妥不改变钱和货'
    return out
