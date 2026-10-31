"""Declarative local rewards: strict Pydantic config plus deterministic generation.

Boundaries kept deliberately small:

* No arbitrary code or formulas. Every derived number (weight, durability, damage,
  value, mana capacity) comes from a fixed whitelist of integer operations:
  ``base * percent // 100`` and additions. There is no ``eval`` and no model call.
* No builtin ``hash`` call, no clock, no randomness beyond a SHA-256 counter stream
  keyed by the journey seed, the source action, the configured entry and the rules
  version. Rolling back an event and replaying the same action regenerates the very
  same item, and the identity of a generated instance never depends on list position.
* Absent ``story.mechanics.rewards`` every function here returns ``None`` and the rest
  of the engine behaves exactly as before: no extra state keys, no extra effect op.
* Rewards are an engine-side grant source. An optional ``payer`` names an author-declared
  supply account of the SAME currency whose balance is debited in the same batch; that
  account is hidden state and never appears in a player projection. No NPC treasury,
  shop stock or world scarcity model exists yet, so nothing claims an NPC paid unless
  the author declared such an account and it had the balance.
* Durability and mana capacity are static derived numbers in this version. There is no
  wear, repair or recharging yet, so no projection pretends otherwise.

State lives inside the journey snapshot (``session['rewards']``) and is therefore
saved, rolled back and reloaded by the existing Store transaction; there is no second
authority table.
"""
import copy
import hashlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

RULES_VERSION = 'rewards_v1'
ID = r'^[A-Za-z0-9_-]{1,60}$'
# Instance statistics are recomputed from config on every read; the copy stored in the
# session is an audit cache only and never trusted as authority.
DERIVATION = ('weight = template.weight or shape.base_weight * material.weight_percent // 100; '
              'durability = template.durability or shape.base_durability * quality.durability_percent // 100; '
              'damage = shape.base_damage + material.damage_bonus + 已公开附魔的 damage_per_level * level; '
              'value = (shape.base_value * quality.value_percent // 100) * material.value_percent // 100 '
              '+ 已公开附魔的 partial_value * value_percent_per_level * level // 100; '
              'mana_capacity = template.mana_capacity or shape.mana_capacity; '
              '耐久与魔力容量本版为静态数值，没有损耗、修理或充能；全部为整数运算，无公式求值器')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


def _int(low, high, default=0):
    return Field(default=default, ge=low, le=high, strict=True)


class Currency(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    unit: str = Field(default='', max_length=12)
    maximum: int = Field(default=1000000, ge=0, le=1000000000, strict=True)


class Account(Strict):
    """Author-declared supply account, e.g. a merchant's purse. Never player-visible."""
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    currency: str
    initial: int = _int(0, 1000000000)


class Material(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    damage_bonus: int = _int(-50, 50)
    value_percent: int = _int(10, 1000, 100)
    weight_percent: int = _int(10, 1000, 100)
    shapes: list[str] = Field(default_factory=list, max_length=20)


class Shape(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    base_damage: int = _int(0, 1000)
    base_value: int = _int(0, 1000000)
    base_weight: int = _int(1, 100000, 1)
    base_durability: int = _int(0, 100000, 10)
    mana_capacity: int = _int(0, 100000)


class Quality(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    value_percent: int = _int(50, 500, 100)
    durability_percent: int = _int(25, 500, 100)
    enchant_budget: int = _int(0, 20)


class Enchantment(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    group: str = Field(default='', max_length=40)
    max_level: int = _int(1, 5, 1)
    damage_per_level: int = _int(0, 100)
    value_percent_per_level: int = _int(0, 200)
    # Hidden means: never disclosed to a player projection, and its contribution is
    # excluded from the player-visible damage/value. Only the author view sees it.
    hidden: bool = False


class Ability(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default='', max_length=200)
    requires: list[str] = Field(default_factory=list, max_length=5)
    flags: list[str] = Field(default_factory=list, max_length=5)
    public: bool = False


class Template(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=40)
    material: str
    shape: str
    quality: str
    weight: int | None = Field(default=None, ge=1, le=100000, strict=True)
    durability: int | None = Field(default=None, ge=0, le=100000, strict=True)
    mana_capacity: int | None = Field(default=None, ge=0, le=100000, strict=True)
    enchantments: list[str] = Field(default_factory=list, max_length=4)
    unidentified_label: str = Field(default='未鉴定的物品', min_length=1, max_length=40)


class Reward(Strict):
    """One reward entry. Fields irrelevant to its `kind` are rejected, not ignored."""
    id: str = Field(pattern=ID)
    kind: Literal['currency', 'item', 'ability']
    currency: str = ''
    amount_min: int = _int(0, 1000000)
    amount_max: int = _int(0, 1000000)
    templates: list[str] = Field(default_factory=list, max_length=10)
    ability: str = ''
    identified: bool = True
    # Optional supply account of the same currency, debited in the same batch.
    payer: str = ''

    @model_validator(mode='after')
    def only_relevant_fields(self):
        relevant = {'id', 'kind'}
        if self.kind == 'currency':
            relevant |= {'currency', 'amount_min', 'amount_max', 'payer'}
        elif self.kind == 'item':
            relevant |= {'templates', 'identified'}
        else:
            relevant |= {'ability'}
        supplied = set()
        if self.currency:
            supplied.add('currency')
        if self.templates:
            supplied.add('templates')
        if self.ability:
            supplied.add('ability')
        if self.payer:
            supplied.add('payer')
        if self.amount_min or self.amount_max:
            supplied |= {'amount_min', 'amount_max'}
        if self.identified is not True:
            supplied.add('identified')
        extra = supplied - relevant
        if extra:
            raise ValueError('奖励条目包含与该类型无关的字段：' + '、'.join(sorted(extra)))
        return self


class TableEntry(Strict):
    reward: str
    weight: int = _int(1, 10000, 1)


class Table(Strict):
    """Weighted entry group; declaring a table id in an action draws exactly one entry."""
    id: str = Field(pattern=ID)
    entries: list[TableEntry] = Field(default_factory=list, max_length=20)


class Rewards(Strict):
    version: int = Field(default=1, strict=True)
    currencies: list[Currency] = Field(default_factory=list, max_length=8)
    accounts: list[Account] = Field(default_factory=list, max_length=10)
    materials: list[Material] = Field(default_factory=list, max_length=20)
    shapes: list[Shape] = Field(default_factory=list, max_length=20)
    qualities: list[Quality] = Field(default_factory=list, max_length=10)
    enchantments: list[Enchantment] = Field(default_factory=list, max_length=20)
    abilities: list[Ability] = Field(default_factory=list, max_length=20)
    templates: list[Template] = Field(default_factory=list, max_length=30)
    tables: list[Table] = Field(default_factory=list, max_length=10)
    rewards: list[Reward] = Field(default_factory=list, max_length=40)
    max_grants_per_event: int = _int(1, 50, 8)
    # One integer budget unit shared by item value and currency amount for one grant.
    max_value_per_grant: int = _int(0, 10000000, 100000)
    max_items: int = _int(1, 200, 40)


def rules(story):
    """Return the parsed reward config, or None when the author configured nothing."""
    raw = (story or {}).get('mechanics', {}).get('rewards')
    if raw is None:
        return None
    return Rewards.model_validate(raw)


# ---------------------------------------------------------------- config validation


def validate(story):
    cfg = rules(story)
    if cfg is None:
        _reject_unconfigured_declarations(story)
        return None
    if type(cfg.version) is not int or cfg.version != 1:
        raise ValueError('奖励配置版本必须为整数 1')
    groups = (('货币', cfg.currencies), ('账户', cfg.accounts), ('材质', cfg.materials),
              ('形制', cfg.shapes), ('品质', cfg.qualities), ('附魔', cfg.enchantments),
              ('能力', cfg.abilities), ('模板', cfg.templates), ('奖励表', cfg.tables),
              ('奖励条目', cfg.rewards))
    for label, items in groups:
        values = [x.id for x in items]
        if len(set(values)) != len(values):
            raise ValueError(f'{label}ID重复')
    currency = {x.id for x in cfg.currencies}
    accounts = {x.id: x for x in cfg.accounts}
    materials = {x.id: x for x in cfg.materials}
    shapes = {x.id: x for x in cfg.shapes}
    qualities = {x.id for x in cfg.qualities}
    enchants = {x.id: x for x in cfg.enchantments}
    abilities = {x.id: x for x in cfg.abilities}
    templates = {x.id: x for x in cfg.templates}
    entries = {x.id for x in cfg.rewards}
    table_ids = {x.id for x in cfg.tables}
    if entries & table_ids:
        # Both are declared through the same action field, so a shared name would make
        # `_resolve` shadow the table silently. Refuse it at commit time.
        raise ValueError('奖励条目与奖励表不能使用同一个ID：' + '、'.join(sorted(entries & table_ids)))
    for account in cfg.accounts:
        if account.currency not in currency:
            raise ValueError('账户引用了未知货币')
    for material in cfg.materials:
        unknown = set(material.shapes) - set(shapes)
        if unknown:
            raise ValueError('材质声明了未知形制：' + '、'.join(sorted(unknown)))
    for template in cfg.templates:
        if template.material not in materials or template.shape not in shapes or template.quality not in qualities:
            raise ValueError('物品模板引用了未知材质、形制或品质')
        material, quality = materials[template.material], next(q for q in cfg.qualities if q.id == template.quality)
        if material.shapes and template.shape not in material.shapes:
            raise ValueError('物品模板的形制不在该材质允许范围内')
        if set(template.enchantments) - set(enchants):
            raise ValueError('物品模板引用了未知附魔')
        if len(set(template.enchantments)) != len(template.enchantments):
            raise ValueError('同一模板不能重复列出同一附魔')
        used_groups, levels = set(), 0
        capacity = template.mana_capacity if template.mana_capacity is not None else shapes[template.shape].mana_capacity
        for eid in template.enchantments:
            enchant = enchants[eid]
            if enchant.group:
                if enchant.group in used_groups:
                    raise ValueError('同一互斥附魔组只能出现一次：' + enchant.group)
                used_groups.add(enchant.group)
            levels += enchant.max_level
        if levels > quality.enchant_budget:
            raise ValueError('模板附魔等级超出品质的附魔预算')
        if template.enchantments and capacity <= 0:
            raise ValueError('含附魔的物品需要正的魔力容量上限')
    for ability in cfg.abilities:
        if set(ability.requires) - set(abilities):
            raise ValueError('能力前置引用了未知能力')
        if ability.id in ability.requires:
            raise ValueError('能力不能以自身为前置')
    _reject_ability_cycles(cfg)
    for table in cfg.tables:
        if not table.entries:
            raise ValueError('奖励表需要至少一个条目')
        if {x.reward for x in table.entries} - entries:
            raise ValueError('奖励表引用了未知奖励条目')
        if len({x.reward for x in table.entries}) != len(table.entries):
            raise ValueError('同一奖励表不能重复列出同一条目')
    for reward in cfg.rewards:
        if reward.kind == 'currency':
            if reward.currency not in currency:
                raise ValueError('货币奖励需要已定义的货币')
            if reward.amount_min > reward.amount_max:
                raise ValueError('货币奖励的最小值不能大于最大值')
            if reward.amount_max > cfg.max_value_per_grant:
                raise ValueError('货币奖励超过单次奖励预算，请调整数量或预算')
        elif reward.kind == 'item':
            if set(reward.templates) - set(templates) or (not reward.templates and not cfg.templates):
                raise ValueError('物品奖励需要已定义模板')
        elif reward.kind == 'ability':
            if reward.ability not in abilities:
                raise ValueError('能力奖励需要已定义能力')
        if reward.payer:
            account = accounts.get(reward.payer)
            if account is None:
                raise ValueError('奖励付款账户需要已定义的账户')
            if reward.kind != 'currency':
                raise ValueError('只有货币奖励可以指定付款账户')
            if account.currency != reward.currency:
                raise ValueError('付款账户的币种必须与奖励币种一致')
    # A budget below any declared amount can never be satisfied; fail at commit time
    # instead of leaving an action that always refuses its own reward.
    for reward in cfg.rewards:
        if reward.kind == 'currency' and reward.amount_min > cfg.max_value_per_grant:
            raise ValueError('货币奖励的最小值超过单次奖励预算')
    for event in (story or {}).get('events', []):
        for action in event.get('actions', []):
            declared = action.get('rewards') or {}
            if not isinstance(declared, dict) or set(declared) - {'success', 'failure'}:
                raise ValueError('行动奖励只支持 success 与 failure 两个分支')
            for branch, values in declared.items():
                if not isinstance(values, list) or len(values) > 6 or any(not isinstance(x, str) for x in values):
                    raise ValueError('行动奖励条目必须是至多6个ID的列表')
                if set(values) - entries - table_ids:
                    raise ValueError('行动引用了未定义的奖励条目或奖励表')
            for effect in action.get('effects', []) + action.get('success', []) + action.get('failure', []):
                if effect.get('op') == 'reward' and effect.get('entry') not in entries | table_ids:
                    raise ValueError('奖励效果引用了未定义的奖励条目或奖励表')
    return cfg


def _reject_ability_cycles(cfg):
    graph = {x.id: list(x.requires) for x in cfg.abilities}
    state = {}

    def visit(node, trail):
        if state.get(node) == 'done':
            return
        if state.get(node) == 'open':
            raise ValueError('能力前置存在环，无法通过奖励获得：' + ' → '.join(trail + [node]))
        state[node] = 'open'
        for dependency in graph.get(node, []):
            visit(dependency, trail + [node])
        state[node] = 'done'

    for node in sorted(graph):
        visit(node, [])


def _reject_unconfigured_declarations(story):
    for event in (story or {}).get('events', []):
        for action in event.get('actions', []):
            if action.get('rewards'):
                raise ValueError('行动声明了奖励，但故事包未配置 mechanics.rewards')
            for effect in action.get('effects', []) + action.get('success', []) + action.get('failure', []):
                if effect.get('op') == 'reward':
                    raise ValueError('奖励效果需要先配置 mechanics.rewards')


# ------------------------------------------------------------- deterministic stream


class Rolls:
    """SHA-256 counter stream: same seed always yields the same sequence."""

    def __init__(self, seed):
        self.seed = seed
        self.counter = 0
        self.buffer = []

    def next32(self):
        if not self.buffer:
            block = hashlib.sha256(f'{self.seed}:{self.counter}'.encode('utf-8')).digest()
            self.counter += 1
            self.buffer = [int.from_bytes(block[i:i + 4], 'big') for i in range(0, 32, 4)]
        return self.buffer.pop(0)

    def below(self, limit):
        if type(limit) is not int or limit <= 0:
            raise ValueError('随机范围必须是正整数')
        return self.next32() % limit

    def between(self, low, high):
        if type(low) is not int or type(high) is not int or low < 0 or low > high:
            raise ValueError('随机区间无效')
        return low + self.below(high - low + 1)

    def weighted(self, entries):
        total = sum(entry.weight for entry in entries)
        if total <= 0:
            raise ValueError('加权奖励表权重必须为正')
        roll = self.below(total)
        for entry in entries:
            roll -= entry.weight
            if roll < 0:
                return entry
        return entries[-1]


# ------------------------------------------------------------------ derived numbers


def derive(cfg, material, shape, quality, levels, disclose_hidden=False):
    """Whitelisted integer derivation; never reads a value stored in the instance.

    Hidden enchantments are excluded unless ``disclose_hidden`` is set, so a player
    cannot infer one from the damage or value of an item they hold.
    """
    weight = shape.base_weight * material.weight_percent // 100
    durability = shape.base_durability * quality.durability_percent // 100
    partial = shape.base_value * quality.value_percent // 100
    value = partial * material.value_percent // 100
    damage = shape.base_damage + material.damage_bonus
    for enchant_id, level in sorted(levels.items()):
        enchant = next(x for x in cfg.enchantments if x.id == enchant_id)
        if enchant.hidden and not disclose_hidden:
            continue
        damage += enchant.damage_per_level * level
        value += partial * enchant.value_percent_per_level * level // 100
    return {'weight': max(1, weight), 'durability': max(0, durability),
            'damage': max(0, damage), 'value': max(0, value)}


def _stats(cfg, template, levels, disclose_hidden=False):
    material = next(x for x in cfg.materials if x.id == template.material)
    shape = next(x for x in cfg.shapes if x.id == template.shape)
    quality = next(x for x in cfg.qualities if x.id == template.quality)
    stats = derive(cfg, material, shape, quality, levels, disclose_hidden=disclose_hidden)
    weight = template.weight if template.weight is not None else stats['weight']
    durability = template.durability if template.durability is not None else stats['durability']
    capacity = template.mana_capacity if template.mana_capacity is not None else shape.mana_capacity
    return {'weight': weight, 'durability': durability, 'damage': stats['damage'],
            'value': stats['value'], 'mana_capacity': capacity, 'mana': 0}


def _roll_levels(cfg, template, rolls):
    """Pick enchantment levels inside the quality budget, one per exclusive group."""
    quality = next(x for x in cfg.qualities if x.id == template.quality)
    budget = quality.enchant_budget
    levels, groups = {}, set()
    for enchant_id in sorted(template.enchantments):
        enchant = next(x for x in cfg.enchantments if x.id == enchant_id)
        if enchant.group:
            if enchant.group in groups:
                continue
            groups.add(enchant.group)
        if budget <= 0:
            break
        ceiling = min(enchant.max_level, budget)
        level = 1 + rolls.below(ceiling) if ceiling > 1 else 1
        levels[enchant_id] = level
        budget -= level
    return levels


def _instance(cfg, session, template, levels, identified, origin):
    shape = next(x for x in cfg.shapes if x.id == template.shape)
    stats = _stats(cfg, template, levels, disclose_hidden=True)
    return {'id': origin['item_id'], 'template': template.id, 'name': template.name,
            'material': template.material, 'shape': template.shape, 'quality': template.quality,
            'enchantments': [{'id': k, 'level': v} for k, v in sorted(levels.items())],
            'identified': bool(identified),
            'owner': 'player', 'location': session.get('location', ''),
            'rules_version': RULES_VERSION, 'origin_result_id': origin['grant'],
            'origin_source': origin['source'], 'created_time': session.get('time', 0),
            'stats_cache': {**stats, 'authoritative': False,
                            'note': '仅供审计；读取时按固定规则重算，不信任此副本'},
            'shape_name': shape.name}


def instance_stats(cfg, instance, disclose_hidden=False):
    """Recompute from config; a mutated cache in the session cannot change anything."""
    template = next((x for x in cfg.templates if x.id == instance.get('template')), None)
    if template is None:
        raise ValueError('物品实例引用了未知模板')
    levels = {x['id']: x['level'] for x in instance.get('enchantments', [])}
    return _stats(cfg, template, levels, disclose_hidden=disclose_hidden)


# ---------------------------------------------------------------- session state


def blank(cfg):
    return {'version': 1, 'wallet': {x.id: 0 for x in cfg.currencies},
            'accounts': {x.id: x.initial for x in cfg.accounts},
            'items': [], 'abilities': [], 'grants': [], 'ledger': []}


def ensure(session, story):
    """Create the reward state on a candidate session; never called from reads."""
    cfg = rules(story)
    if cfg is None:
        return None
    current = session.get('rewards')
    if current is None:
        session['rewards'] = blank(cfg)
        return cfg
    for key, value in blank(cfg).items():
        current.setdefault(key, value)
    for currency in cfg.currencies:
        current['wallet'].setdefault(currency.id, 0)
    for account in cfg.accounts:
        current['accounts'].setdefault(account.id, account.initial)
    return cfg


def state(session, cfg):
    """Read-only view for projections; a missing block is reported empty, not written."""
    current = session.get('rewards') or {}
    return {'version': current.get('version', 1),
            'wallet': {x.id: int(current.get('wallet', {}).get(x.id, 0)) for x in cfg.currencies},
            'accounts': {x.id: int(current.get('accounts', {}).get(x.id, x.initial))
                         for x in cfg.accounts},
            'items': list(current.get('items') or []),
            'abilities': list(current.get('abilities') or []),
            'grants': list(current.get('grants') or []),
            'ledger': list(current.get('ledger') or [])}


def branch_key(session):
    """Stable identity of the current event occurrence, independent of turn count.

    Old saves whose active block predates this field derive the same value from the
    seed and the number of closed occurrences of the same node, so a rollback (which
    restores ``archives``) reproduces it exactly.
    """
    active = session.get('active') or {}
    if active.get('key'):
        return active['key']
    node = str(active.get('node') or '')
    return _branch(session, node)


def _branch(session, node):
    occurrence = sum(1 for a in session.get('archives') or [] if a.get('node') == node)
    return hashlib.sha256(f"{session.get('seed', '')}:{node}:{occurrence}".encode('utf-8')).hexdigest()[:32]


def new_branch_key(session, node):
    return _branch(session, node)


def grant_id(session, source, reward_id):
    """Stable grant identity: journey seed + source action + configured entry.

    Independent of turn counts, list position and whether the event is still open, so
    a retry, a second call after the event closed, or a duplicate declaration inside
    one action can never pay twice. Rolling back drops the grant records themselves,
    which is exactly what allows a deterministic re-gain.
    """
    text = f"{session.get('seed', '')}:{source}:{reward_id}"
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def _rolls(identifier):
    """Random stream for one grant: identity plus the rules version, nothing else."""
    return Rolls(f'{identifier}:{RULES_VERSION}')


# ------------------------------------------------------------------ batch application


def _resolve(cfg, claim):
    """Resolve a claim to (entry id, table). A table id only draws when the table exists."""
    target = claim.get('entry')
    if any(x.id == target for x in cfg.rewards):
        return str(target), None
    table = next((x for x in cfg.tables if x.id == target), None)
    if table is None:
        raise ValueError('未定义的奖励条目：' + str(target))
    if not table.entries:
        raise ValueError('奖励表没有条目：' + str(target))
    return None, table


def _draw_table(cfg, session, source, table):
    """Draw one entry from a weighted table; identity is stable per source and table."""
    text = f"{session.get('seed', '')}:{source}:table:{table.id}"
    identifier = hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]
    chosen = _rolls(identifier).weighted(sorted(table.entries, key=lambda x: x.reward))
    if not any(x.id == chosen.reward for x in cfg.rewards):
        raise ValueError('奖励表引用了未知奖励条目：' + chosen.reward)
    return chosen.reward


def apply(session, cfg, claims, source):
    """Validate and apply one batch of reward claims on a copy of the reward state.

    The whole batch is simulated in order against a deep copy; nothing is written back
    unless every claim is valid, so one failing claim cannot leave half a batch behind.
    Repeating the same grant (same source action, same entry) is a no-op instead of a
    second payout.
    """
    result = copy.deepcopy(state(session, cfg))
    audits = []
    branch = branch_key(session)
    flags = session.get('flags') or {}
    unlocked = {x['id'] for x in result['abilities']}
    in_branch = sum(1 for g in result['grants'] if g.get('branch') == branch)
    for claim in claims:
        entry_id, table = _resolve(cfg, claim)
        if table is not None:
            entry_id = _draw_table(cfg, session, source, table)
        reward = next(x for x in cfg.rewards if x.id == entry_id)
        identifier = grant_id(session, source, reward.id)
        if any(g['id'] == identifier for g in result['grants']):
            continue
        if in_branch >= cfg.max_grants_per_event:
            raise ValueError('本次事件的有效奖励已达到上限')
        if reward.kind == 'ability' and reward.ability in unlocked:
            continue
        rolls = _rolls(identifier)
        audit = {'reward': reward.id, 'kind': reward.kind, 'source': source,
                 'branch': branch, 'grant': identifier}
        if reward.kind == 'currency':
            currency = next(x for x in cfg.currencies if x.id == reward.currency)
            amount = rolls.between(reward.amount_min, reward.amount_max)
            if amount > cfg.max_value_per_grant:
                raise ValueError('货币奖励超过单次奖励预算，整批奖励已拒绝')
            if amount and reward.payer:
                account = next(x for x in cfg.accounts if x.id == reward.payer)
                funded = result['accounts'].get(account.id, 0)
                if funded < amount:
                    raise ValueError('奖励付款账户余额不足，整批奖励已拒绝')
                result['accounts'][account.id] = funded - amount
                audit['payer'] = {'id': account.id, 'currency': account.currency,
                                  'before': funded, 'after': funded - amount}
            before = result['wallet'].get(currency.id, 0)
            after = before + amount
            if after > currency.maximum:
                raise ValueError(f'{currency.name}超出配置上限，整批奖励已拒绝')
            result['wallet'][currency.id] = after
            audit.update(object=currency.id, before=before, after=after, amount=amount)
        elif reward.kind == 'item':
            if len(result['items']) >= cfg.max_items:
                raise ValueError('已持有物品数量达到上限，整批奖励已拒绝')
            candidates = sorted(reward.templates or [x.id for x in cfg.templates])
            if not candidates:
                raise ValueError('物品奖励没有可用模板，整批奖励已拒绝')
            # Draw the index exactly once: a call inside the lookup would advance the
            # stream on every iteration and make the choice depend on list traversal.
            chosen = candidates[rolls.below(len(candidates))]
            template = next((x for x in cfg.templates if x.id == chosen), None)
            if template is None:
                raise ValueError('物品奖励引用了未知模板：' + chosen)
            levels = _roll_levels(cfg, template, rolls)
            stats = _stats(cfg, template, levels, disclose_hidden=True)
            if stats['value'] > cfg.max_value_per_grant:
                raise ValueError('物品价值超过单次奖励上限，整批奖励已拒绝')
            item_id = 'itm_' + hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:16]
            instance = _instance(cfg, session, template, levels, reward.identified,
                                 {'grant': identifier, 'item_id': item_id, 'source': source})
            result['items'].append(instance)
            audit.update(object=item_id, template=template.id, value=stats['value'],
                         identified=bool(reward.identified))
        else:
            ability = next(x for x in cfg.abilities if x.id == reward.ability)
            missing = [x for x in ability.requires if x not in unlocked]
            if missing:
                raise ValueError('能力前置未满足，整批奖励已拒绝：' + '、'.join(sorted(missing)))
            if any(not flags.get(name) for name in ability.flags):
                raise ValueError('能力所需标记未满足，整批奖励已拒绝')
            result['abilities'].append({'id': ability.id, 'grant': identifier, 'source': source,
                                        'branch': branch, 'time': session.get('time', 0),
                                        'rules_version': RULES_VERSION})
            unlocked.add(ability.id)
            audit.update(object=ability.id, before=None, after=ability.id)
        # The payer's debit is an author-side ledger event, not a wallet line: it must
        # stay traceable after the batch for audit, but never reach a player projection.
        supply = dict(audit['payer']) if audit.get('payer') else None
        grant = {'id': identifier, 'reward': reward.id, 'kind': reward.kind, 'branch': branch,
                 'source': source, 'time': session.get('time', 0), 'rules_version': RULES_VERSION,
                 'seed': str(session.get('seed', ''))[:8], 'object': audit.get('object'),
                 'before': audit.get('before'), 'after': audit.get('after'),
                 'account': supply}
        result['grants'].append(grant)
        in_branch += 1
        result['ledger'].append({'time': session.get('time', 0), 'grant': identifier,
                                 'reward': reward.id, 'kind': reward.kind,
                                 'object': audit.get('object'), 'before': audit.get('before'),
                                 'after': audit.get('after'), 'source': source,
                                 'rules_version': RULES_VERSION, 'branch': branch,
                                 'account': supply})
        audits.append(audit)
    return result, audits


# ------------------------------------------------------------------ public projection


def seed_start(session, story, wallet=None, items=None, source='start:opening'):
    """开局的引擎侧发放：钱货与物品实例，**与模型正文完全无关**。

    与 ``apply`` 的区别只在意图，不在权威：同样写 ``session['rewards']``、
    同样走白名单整数、同样在深拷贝上完成——任何一条非法（未知货币/模板、
    超额、超上限）都抛错，调用方此时还没保存，因此整条开局零写入。

    ``source`` 必须以 ``start:`` 开头：这既让来源可审计，也让 ``grant_id``
    与后续事件奖励天然落在不同命名空间（同一来源动作不会重发，不同来源互不影响）。
    """
    cfg = rules(story)
    wallet = dict(wallet or {})
    items = list(items or [])
    if not wallet and not items:
        return None
    if cfg is None:
        raise ValueError('开局要发放钱货或物品实例，但故事包未配置 mechanics.rewards')
    if not isinstance(source, str) or not source.startswith('start:'):
        raise ValueError('开局发放的来源必须以 start: 开头')
    if not isinstance(wallet, dict) or not isinstance(items, list):
        raise ValueError('开局发放参数类型无效')
    ensure(session, story)
    result = copy.deepcopy(state(session, cfg))
    currencies = {x.id: x for x in cfg.currencies}
    templates = {x.id: x for x in cfg.templates}
    audits = []
    for currency_id in sorted(wallet):
        amount = wallet[currency_id]
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError('开局钱货必须是整数：%s' % currency_id)
        if currency_id not in currencies:
            raise ValueError('开局钱货引用了未声明的货币：' + currency_id)
        if amount < 0:
            raise ValueError('开局钱货不能为负：' + currency_id)
        if amount == 0:
            continue
        currency = currencies[currency_id]
        before = result['wallet'].get(currency_id, 0)
        after = before + amount
        if after > currency.maximum:
            raise ValueError('%s 超出配置上限，开局整条拒绝' % currency.name)
        result['wallet'][currency_id] = after
        identifier = grant_id(session, source, 'currency:' + currency_id)
        grant = {'id': identifier, 'reward': 'start:' + currency_id,
                 'kind': 'currency', 'branch': 'start', 'source': source,
                 'time': session.get('time', 0), 'rules_version': RULES_VERSION,
                 'seed': str(session.get('seed', ''))[:8], 'object': currency_id,
                 'before': before, 'after': after, 'account': None}
        result['grants'].append(grant)
        result['ledger'].append({'time': session.get('time', 0), 'grant': identifier,
                                 'reward': grant['reward'], 'kind': 'currency',
                                 'object': currency_id, 'before': before, 'after': after,
                                 'source': source, 'rules_version': RULES_VERSION,
                                 'branch': 'start', 'account': None})
        audits.append({'kind': 'currency', 'object': currency_id,
                       'before': before, 'after': after, 'amount': amount,
                       'source': source})
    for template_id in items:
        template = templates.get(template_id)
        if template is None:
            raise ValueError('开局物品实例引用了未定义的模板：' + str(template_id))
        if len(result['items']) >= cfg.max_items:
            raise ValueError('已持有物品数量达到上限，开局整条拒绝')
        identifier = grant_id(session, source, 'item:' + template_id)
        if any(g['id'] == identifier for g in result['grants']):
            continue
        stats = _stats(cfg, template, {}, disclose_hidden=True)
        if stats['value'] > cfg.max_value_per_grant:
            raise ValueError('开局物品价值超过单次上限，开局整条拒绝')
        item_id = 'itm_' + hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:16]
        instance = _instance(cfg, session, template, {}, True,
                             {'grant': identifier, 'item_id': item_id, 'source': source})
        result['items'].append(instance)
        result['grants'].append({'id': identifier, 'reward': 'start:' + template_id,
                                 'kind': 'item', 'branch': 'start', 'source': source,
                                 'time': session.get('time', 0),
                                 'rules_version': RULES_VERSION,
                                 'seed': str(session.get('seed', ''))[:8],
                                 'object': item_id, 'before': None, 'after': item_id,
                                 'account': None})
        result['ledger'].append({'time': session.get('time', 0), 'grant': identifier,
                                 'reward': 'start:' + template_id, 'kind': 'item',
                                 'object': item_id, 'before': None, 'after': item_id,
                                 'source': source, 'rules_version': RULES_VERSION,
                                 'branch': 'start', 'account': None})
        audits.append({'kind': 'item', 'object': item_id, 'template': template_id,
                       'value': stats['value'], 'source': source})
    # 全部通过才写回；失败路径不会留下半批。
    session['rewards'] = result
    return {'source': source, 'grants': audits,
            'note': '开局由引擎发放，与模型正文无关；命名空间 start: 与事件奖励隔离'}


def _template(cfg, instance):
    return next((x for x in cfg.templates if x.id == instance.get('template')), None)


def public_item(cfg, instance, reveal_hidden=False):
    """Player-visible view. Unidentified items disclose nothing derived, not even name.

    A hidden enchantment is author-only: it is neither listed nor folded into the
    player-visible damage or value, so it cannot be inferred from the numbers. Only the
    author view (``reveal_hidden=True``) sees the full picture, including the derived
    numbers of an unidentified instance.
    """
    template = _template(cfg, instance)
    stats = instance_stats(cfg, instance, disclose_hidden=reveal_hidden)
    identified = bool(instance.get('identified', True))
    if not identified and not reveal_hidden:
        # Nothing derived is disclosed before identification; the weight is the only
        # observable figure, and it is labelled like every other public estimate.
        return {'id': instance['id'], 'identified': False,
                'label': (template.unidentified_label if template else '未鉴定的物品'),
                'weight': stats['weight'], 'figures': 'visible_estimate',
                'figures_note': '未鉴定：只给可观察标签与重量，不含任何衍生数值。'}
    enchantments = []
    for entry in instance.get('enchantments', []):
        source = next((x for x in cfg.enchantments if x.id == entry['id']), None)
        if source is None or (source.hidden and not reveal_hidden):
            continue
        enchantments.append({'name': source.name, 'level': entry['level']})
    material = next((x for x in cfg.materials if x.id == instance.get('material')), None)
    quality = next((x for x in cfg.qualities if x.id == instance.get('quality')), None)
    shape = next((x for x in cfg.shapes if x.id == instance.get('shape')), None)
    view = {'id': instance['id'], 'identified': identified, 'label': instance.get('name', ''),
            'shape': shape.name if shape else '', 'material': material.name if material else '',
            'quality': quality.name if quality else '', 'weight': stats['weight'],
            'durability': stats['durability'], 'damage': stats['damage'], 'value': stats['value'],
            'mana': {'charge': int(instance.get('mana', 0)), 'capacity': stats['mana_capacity']},
            'enchantments': enchantments}
    if reveal_hidden:
        view['figures'] = 'authoritative'
        return view
    # damage/value here are the visible estimate only: hidden contributions are left
    # out on purpose, so the narrator must not treat them as the item's full worth.
    view['figures'] = 'visible_estimate'
    view['figures_note'] = ('这里只给可见部分，不含未披露的效果；本版没有战斗、负重或交易执行器，'
                            '这些数值仅供叙述参考，不是最终裁定结果。')
    return view


def public_state(session, story, audience='player'):
    """Audience-scoped reward projection. NPCs never inherit the author's hidden stock."""
    cfg = rules(story)
    if cfg is None:
        return None
    if audience not in ('player', 'author'):
        return None
    current = state(session, cfg)
    abilities = []
    for entry in current['abilities']:
        source = next((x for x in cfg.abilities if x.id == entry['id']), None)
        if source is None:
            continue
        if audience != 'author' and not source.public:
            continue
        abilities.append({'id': source.id, 'name': source.name,
                          'description': source.description if audience == 'author' else ''})
    if audience == 'author':
        items = []
        for instance in current['items']:
            view = public_item(cfg, instance, reveal_hidden=True)
            view['stats_cache_matches'] = instance.get('stats_cache', {}).get('value') == view['value']
            view['origin_result_id'] = instance.get('origin_result_id')
            items.append(view)
        wallet = [{'id': c.id, 'name': c.name, 'unit': c.unit,
                   'amount': current['wallet'].get(c.id, 0), 'maximum': c.maximum} for c in cfg.currencies]
        accounts = [{'id': a.id, 'name': a.name, 'currency': a.currency,
                     'amount': current['accounts'].get(a.id, a.initial)} for a in cfg.accounts]
        return {'rules_version': RULES_VERSION, 'wallet': wallet, 'items': items,
                'abilities': abilities, 'accounts': accounts,
                'note': '作者视图：含隐藏附魔、付款账户与完整实例信息'}
    items = [public_item(cfg, x) for x in current['items'] if x.get('owner') in (None, 'player')]
    wallet = [{'id': c.id, 'name': c.name, 'unit': c.unit,
               'amount': current['wallet'].get(c.id, 0)} for c in cfg.currencies]
    return {'rules_version': RULES_VERSION,
            'wallet': wallet, 'items': items, 'abilities': abilities,
            'note': '引擎已确认的持有物与余额；与 current_inventory 同为权威现状。'
                    '公开投影不含未鉴定物品的衍生属性、隐藏附魔与付款账户。'}


def public_result(cfg, audits, session):
    """Player-safe one-line summary of what this batch granted; no hidden data.

    A non-public ability produces no line at all: if the player cannot know it exists,
    naming it as "something new" would already be a disclosure.
    """
    lines = []
    for audit in audits:
        if audit['kind'] == 'currency':
            currency = next(x for x in cfg.currencies if x.id == audit['object'])
            lines.append(f"{currency.name} +{audit['amount']}{currency.unit}")
        elif audit['kind'] == 'item':
            instance = next((x for x in state(session, cfg)['items'] if x['id'] == audit['object']), None)
            view = public_item(cfg, instance) if instance else {'label': '一件物品', 'identified': True}
            lines.append('获得 ' + view['label'] + ('' if view['identified'] else '（尚未鉴定）'))
        else:
            ability = next((x for x in cfg.abilities if x.id == audit['object']), None)
            if ability is not None and ability.public:
                lines.append('学会了 ' + ability.name)
    return lines


def public_changes(session, before, story):
    """Summary diff over public projections only."""
    cfg = rules(story)
    if cfg is None:
        return []
    now = state(session, cfg)
    old = state(before, cfg)
    changes = []
    for currency in cfg.currencies:
        old_value, new_value = old['wallet'].get(currency.id, 0), now['wallet'].get(currency.id, 0)
        if old_value != new_value:
            changes.append(f'{currency.name} {old_value}→{new_value}{currency.unit}')
    old_ids = {x['id'] for x in old['items']}
    for instance in now['items']:
        if instance['id'] in old_ids:
            continue
        view = public_item(cfg, instance)
        changes.append('物品 +' + view['label'] + ('' if view['identified'] else '（未鉴定）'))
    old_ability = {x['id'] for x in old['abilities']}
    for entry in now['abilities']:
        if entry['id'] in old_ability:
            continue
        ability = next((x for x in cfg.abilities if x.id == entry['id']), None)
        if ability is None or not ability.public:
            continue
        changes.append('能力 +' + ability.name)
    return changes
