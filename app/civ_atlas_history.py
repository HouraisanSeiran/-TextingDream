# -*- coding: utf-8 -*-
"""civ-atlas structured history → a *bounded, honest* background candidate for one year.

What this module is for
----------------------
The author generated a world in civ-atlas, simulated a few thousand years of history and
exported one ``.civsnap``. They pick that map and that simulation as the story's starting
background, then pick a **base year** and a **branch**. This module answers exactly one
question, for that year:

    "which polities / cities / people / events can I honestly hand to the author as
    background candidates for this year?"

It does **not** build a second history engine, does not run civ-atlas, and never re-derives
a value the export does not record. The output is a *candidate* for the author to review:
nothing here is canonical and nothing here reaches a player by itself.

Where the data comes from (upstream ``0939c5f1622a5e45cfc16f645ea3845993ab3985``)
----------------------------------------------------------------------------
``src/worker.ts:741`` packs the whole ``Civ`` object into the ``civ`` part, so after
``app.civ_atlas_snapshot.parse_part`` the part is a plain dict shaped like
``src/gen/civ/types.ts`` ``Civ``:

    seed               the civ simulation seed (the export does carry it)
    endYear            int, the simulated end year
    regions.count      int, how many 州 the ownership arrays index
    culture / polity    Int16Array at **endYear only** (-1 = nobody)
    checkpoints[]      {year, culture, polity} — a full array every 100 years
                       (``src/gen/civ/sim.ts:288`` CHECKPOINT_EVERY); a snapshot at year C
                       means "every change up to and including C is applied"
    log                {size, year(F32), region(I32), layer(U8), value(I16), cause(U8)};
                       layer 0 = culture, 1 = polity; value -1 = nobody; **size is the
                       valid prefix** — the typed arrays may be longer
    annals[]           {year, kind, a, b, region, settlement, war, cause?, foe?, n?,
                       ps?, by?, opt?, until?, via?}; a/b/region/war mean different things
                       per kind (the big table at ``types.ts:312-402``)
    settlements[]      {id, cell, region, culture, name, founded, ended?, capitalSpans?}
    polities[]         {id, name, culture, capital, founded, ended?, capitals?}
    people[]           {id, role, polity, name, born, died?, from?, until?}
    religion           {faiths[], events[], states[], log, checkpoints[]}
    upheavals[]        {year, kinds, region, polity, …} — terrain events

What we replay ourselves, and what we refuse to invent
------------------------------------------------------
* ``region_culture`` / ``region_polity`` at the base year = the newest checkpoint with
  ``year <= base`` plus the ``log`` entries in ``(checkpoint.year, base]``. That is the same
  *data semantics* as ``src/gen/civ/timeline.ts`` ``ownersAt``, written here from the field
  definitions — no upstream source line was copied, translated or paraphrased into code.
* ``endYear`` consistency is checked **on its own**: we replay from the checkpoints all the
  way to ``endYear`` and compare with the exported ``civ.culture`` / ``civ.polity``. That
  check never looks at the base year, so picking an early year can never make it fail.
  When it does fail, the region layer is reported ``unknown`` (the log and the checkpoints
  are then not a consistent pair) rather than guessed at.
* Before the first checkpoint there is no anchor snapshot. ``timeline.ts`` would start from
  all ``-1`` and replay the whole log; that is a *different* claim ("everything before the
  first checkpoint was empty") and is only true by construction upstream. We report
  ``unknown`` for such years instead of using it as a stand-in for history.
* ``population``, ``resources``, ``routes``, ``terrain`` and every entity's *name as of the
  base year* are ``unknown``: the export carries a growth formula, a 0–3 tier sequence,
  cell paths and only export-time names — not yearly series. Nothing is projected back from
  ``endYear``.
* The ``eras`` block is a **terrain version**, not history: when it exists, the current
  ``regions``/``places`` describe the world *after* the last terrain event. For a base year
  before that year the held map is explicitly reported ``unmatched`` — no claim of a
  faithful restoration of that year's geography.

Scope of the format we read
---------------------------
Generator 45 / snapshot format 1; ``Civ`` as defined at ``SPEC_COMMIT``. Anything we do not
know (a newer ``Annal.kind``, a missing block) is reported as ``unknown`` / ``unresolved``
with its raw values kept, never mapped onto the nearest guess.

Licence
-------
Upstream code is AGPL-3.0-only. This file is an independent Python reader written from the
field definitions in ``types.ts`` / ``snapshot.ts`` (data semantics); no upstream source
line was copied. What the export contains is the author's own generated world data; this
module only refers to it and writes nothing back.

Pure functions only: no file, URL, network, database, clock or environment access. Callers
hand in an already-validated decoded part (see :func:`load_civ`) or the decoded object.
"""
import math

from . import civ_atlas_snapshot as _snap
from .world_basis import EXACT, INTERVAL, UNKNOWN

# ======================================================================= contract
#: Upstream commit whose ``types.ts`` / ``snapshot.ts`` define the data we read.
SPEC_COMMIT = '0939c5f1622a5e45cfc16f645ea3845993ab3985'
#: The only format range this reader claims.
GENERATOR_VERSION = 45
SNAPSHOT_FORMAT = 1
SCHEMA = 1
KIND = 'civ_atlas_history_background'

#: Default size of the year window ending at the base year.
DEFAULT_WINDOW_YEARS = 150
#: How many events / entities one document may carry before it is truncated (a context
#: budget, not a data limit: exact counts stay in ``counts``).
DEFAULT_MAX_EVENTS = 240
DEFAULT_MAX_ENTITIES = 200
#: Hard caps. Beyond these the input is refused instead of silently sampled.
MAX_LOG_ENTRIES = 4_000_000
MAX_ANNALS = 400_000
MAX_REGIONS = 40_000
MAX_ENTITIES = 50_000
MAX_YEAR = 2_000_000
#: Anomaly records kept per document (the total is still counted).
MAX_ANOMALIES = 40
#: Spans kept per entity (the count stays exact).
MAX_SPANS = 12

#: Frozen limits, so a test can pin them and a caller can show them to the author.
LIMITS = {
    'generator_version': GENERATOR_VERSION,
    'snapshot_format': SNAPSHOT_FORMAT,
    'default_window_years': DEFAULT_WINDOW_YEARS,
    'default_max_events': DEFAULT_MAX_EVENTS,
    'default_max_entities': DEFAULT_MAX_ENTITIES,
    'max_log_entries': MAX_LOG_ENTRIES,
    'max_annals': MAX_ANNALS,
    'max_regions': MAX_REGIONS,
    'max_entities': MAX_ENTITIES,
    'max_year': MAX_YEAR,
    'max_anomalies': MAX_ANOMALIES,
    'max_spans': MAX_SPANS,
}

#: ``field_status`` keys, named exactly like ``world_basis.FIELD_CAPABILITY`` so the wiring
#: step can flip ``REPLAY_IMPLEMENTED`` without a translation table.
FIELDS = (
    'region_culture', 'region_polity', 'annals', 'polity_founded',
    'polity_capital_spans', 'settlement_lifespan', 'settlement_capital_spans',
    'people_lifespan', 'religion_events', 'population', 'resources', 'routes', 'terrain',
)

#: Fields that are unknown *by data shape*, with the reason, in the author's words.
UNKNOWN_BY_FORMAT = {
    'population': ('导出里没有逐年人口序列：上游按 S 形曲线现算（growth.ts 的 populationAt），'
                   '记下的只有城的上限、洗劫段与国都段；本工程不移植该公式，'
                   '所以「这一年这座城有多少人」是 unknown'),
    'resources': ('物产是州级 0–3 档储量的发展度数据，不是逐年产量，也不是库存；'
                  '本相位不读 development 块，所以是 unknown'),
    'routes': ('道路/航线只给了逐格路径与修建年份，没有逐年通行状态；本接口不读，所以是 unknown'),
    'terrain': ('地形只在 upheaval（地形大事）改变；本模块只报「当前图与该年是否匹配」，'
                '不重建该年地形，所以是 unknown'),
}

#: How ``Annal.a`` / ``Annal.b`` are to be read, from the ``types.ts`` kind table.
#: ``None`` = "not an entity id in this column" (a count, an index, or unused).
#: A kind missing here (a newer upstream) gets **no** interpretation: its columns stay raw
#: ids and the event is marked ``unresolved``.
ANNAL_AB = {
    'found': ('polity', 'polity'),       # a = new polity, b = mentor (-1 = founded alone)
    'rank': ('polity', None),
    'war': ('polity', 'polity'),
    'conquer': ('polity', 'polity'),
    'peace': ('polity', 'polity'),
    'fall': ('polity', 'polity'),        # b = -1 self-collapse / -2 terrain disaster
    'capital': ('polity', None),
    'split': ('polity', 'polity'),
    'merge': ('polity', 'polity'),
    'dynasty': ('polity', None),
    'migrate': ('culture', 'culture'),
    'assimilate': ('culture', 'culture'),
    'vanish': ('culture', 'culture'),
    'diverge': ('culture', 'culture'),
    'sack': ('polity', 'polity'),
    'ruin': ('polity', 'polity'),
    'rebuild': ('polity', None),
    'decline': ('polity', None),
    'intervene': ('polity', None),       # b depends on the intervention kind
    'battle': ('polity', 'polity'),
    'upheaval': (None, None),            # a = index into civ.upheavals
    'sunk': ('polity', None),
    'alliance': ('polity', 'polity'),
    'unally': ('polity', 'polity'),
    'submit': ('polity', 'polity'),
    'defect': ('polity', 'polity'),
    'famine': ('polity', None),
    'revolt': ('polity', 'polity'),
    'collapse': ('polity', None),
    'plague': ('polity', None),
    'warlord': ('polity', None),
    'reclaim': ('polity', None),
    'defy': ('polity', 'polity'),
    'fiscal': ('polity', None),
    'council': ('polity', 'polity'),
    'stand': ('polity', 'polity'),
    'regent': ('polity', None),
    'marry': ('polity', 'polity'),
    'pandemic': ('polity', None),
    'desolate': ('polity', None),
    'treaty': ('polity', 'polity'),
    'breach': ('polity', 'polity'),
    'expire': ('polity', 'polity'),
    'neutral': ('polity', None),
    'exile': ('polity', 'polity'),
    'keep': ('polity', None),
}

#: Columns that do **not** carry their usual meaning for a given kind (same table).
#: Anything listed here is reported as a note beside the raw value instead of being dressed
#: up as a region id, a war id or a year.
ANNAL_COLUMN_NOTES = {
    'peace': 'region 是割让的州数 n（不是州）；紧跟其前的 n 条 conquer 才是割让的',
    'council': 'war 是议题编号、n 是结果（0 办成/1 妥协/2 搁置/3 谈崩），不是战争',
    'collapse': 'war 是散出去几块，不是战争',
    'pandemic': 'n 是疫前天下人口（千人，取整）；b 是凋敝几年',
    'plague': 'war 是第几场瘟疫，不是战争',
    'desolate': 'war 是第几场瘟疫，不是战争',
    'stand': 'n 是守了几日、foe 是大军退保的那一州、cause 是守将结局',
    'regent': 'n 是哪一步、b 是哪一种掌权、war 是名义君主的位次',
    'treaty': 'war 是约的编号、n 是期限、ps 是立约各国、by 是居间的国家',
    'expire': 'war 是约的编号、ps 是还在约里的几国、n 是立约时几国',
    'breach': 'n 是约的编号，war 是紧跟着的那场战争',
    'neutral': 'war 是中立地的编号、ps 是共建的几国',
    'warlord': 'war 是地盘有几州',
    'reclaim': 'war 是割据了几年',
    'fiscal': 'war 是主因（0 连年用兵 / 1 地方拖欠）',
    'marry': 'n 是娶亲的是谁（位次 × 16 + 儿子序）',
    'defy': 'war 是那场战争；b 是它交战的国家',
    'intervene': 'b / region / settlement 的含义按干预种类变，见 types.ts 的干预清单',
    'upheaval': 'a 是第几件地形大事（civ.upheavals 的下标），不是国家',
    'sunk': 'war 是第几件地形大事',
    'exile': 'war 是中立地的编号（出奔邻国 = -1），n 是缘由/年份',
    'keep': 'war 是第几条干预',
}

LICENSE_NOTE = ('上游代码 AGPL-3.0-only；导出的世界数据归作者。本文是独立写的读取器，'
                '只按 types.ts / snapshot.ts 的字段定义取数据语义，未逐行复制上游代码。')


class HistoryError(ValueError):
    """The input is not a civ block this module can read (structure, bounds, or budget)."""


# ==================================================================== small helpers
class _Anomalies:
    """Collect bounded, non-fatal data oddities so they are reported, never swallowed."""

    __slots__ = ('items', 'count')

    def __init__(self):
        self.items = []
        self.count = 0

    def note(self, where, detail):
        self.count += 1
        if len(self.items) < MAX_ANOMALIES:
            self.items.append({'where': str(where)[:120], 'detail': str(detail)[:240]})

    def dump(self):
        return {'count': self.count, 'kept': len(self.items), 'items': list(self.items)}


def _year(value, label):
    """A year, kept at full precision.

    ``Civ`` years are ``Int32`` but the change log's ``year`` is ``Float32`` and upstream
    compares "log year <= year" numerically. A non-integral year is therefore **kept as a
    float** rather than truncated: truncating 1.5 to 1 would silently move an event into
    the wrong year. Only non-finite and out-of-range values are refused.
    """
    if isinstance(value, bool) or value is None:
        raise HistoryError('%s 不是年份' % label)
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise HistoryError('%s 是 NaN/Inf' % label)
        number = value
    else:
        raise HistoryError('%s 不是数字' % label)
    if not -MAX_YEAR <= number <= MAX_YEAR:
        raise HistoryError('%s 超出可读范围（%r）' % (label, number))
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number


def _base_year(value):
    """The author's base year, at full precision.

    This export's own years are **not** integers: ``Civ`` entities carry years like
    ``511.9765625`` (the simulation steps on fractional ticks) and 4522 of the 4549 log
    years in our own real export are fractional. So the base year is accepted as a float
    and every comparison is numeric — an entity founded at 511.9765625 does not exist at
    year 511. Truncating either side would silently move an entity across the boundary.
    """
    return _year(value, 'base_year')


def _opt_year(value, label, anomalies):
    """An optional year: missing stays ``None``; a broken one becomes ``None`` + a note."""
    if value is None:
        return None
    try:
        return _year(value, label)
    except HistoryError as error:
        anomalies.note(label, str(error))
        return None


def _int(value, label, anomalies):
    """An id/index: non-negative int, else ``-1`` ("not applicable"). Never a bool."""
    if value is None:
        return -1
    if isinstance(value, bool):
        anomalies.note(label, '是布尔值，不当编号')
        return -1
    if isinstance(value, int):
        return -1 if value < 0 else value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return -1 if value < 0 else int(value)
    anomalies.note(label, '不是整数：%r' % (value,))
    return -1


def _text(value, limit=160):
    if not isinstance(value, str):
        return None
    return value[:limit]


def _objects(value, label, anomalies):
    """A list of objects; non-object items are skipped and counted, not trusted."""
    if value is None:
        return []
    if not isinstance(value, list):
        anomalies.note(label, '不是数组')
        return []
    out = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            anomalies.note('%s[%d]' % (label, index), '不是对象')
            continue
        out.append(row)
    return out


# ======================================================================== decoding
def decode_civ_part(manifest, parts):
    """Decode the ``civ`` part of an already-parsed container.

    ``manifest``/``parts`` come from :func:`app.civ_atlas_snapshot.parse_container`; the
    container envelope and the ``CIVSNAP1`` structure decoding are reused from there. The
    stored part bytes are still gzip-compressed when the manifest says so — inflated once
    with the existing bounded inflater, and **not again** if the bytes already start with
    ``CIVSNAP1`` (a caller that pre-inflated cannot double-inflate).
    """
    by_name = {}
    for part in parts or ():
        if isinstance(part, dict):
            by_name[part.get('name')] = part
    meta = by_name.get('civ')
    if meta is None:
        raise HistoryError('这份原件里没有历史那块（parts: %s）'
                           % '、'.join(sorted(str(name) for name in by_name)))
    blob = meta.get('_bytes')
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        raise HistoryError('历史那块的字节缺失（不是 parse_container 的结果？）')
    blob = bytes(blob)
    if blob[:len(_snap.PART_MAGIC)] == _snap.PART_MAGIC:
        pass                                    # already inflated: never inflate twice
    elif meta.get('zip') == 'gzip':
        blob = _snap._inflate(blob)             # bounded inflation (existing code)
    elif meta.get('zip') not in (None, 'none'):
        raise HistoryError('历史那块的压缩方式认不出：%r' % (meta.get('zip'),))
    decoded = _snap.parse_part(blob, 'civ')
    if not isinstance(decoded, dict):
        raise HistoryError('历史那块解出来不是对象')
    return decoded


def load_civ(data):
    """Validate a whole ``.civsnap`` and return ``(decoded Civ, manifest)``.

    Wrapper over ``parse_container`` → :func:`decode_civ_part`. The caller keeps the
    manifest for its source pin (commit / part sums / world id).
    """
    manifest, parts = _snap.parse_container(data)
    return decode_civ_part(manifest, parts), manifest


def identity_from(manifest, record=None, branch=None, terrain_seed=None):
    """Build the ``identity`` argument from a manifest plus (optionally) an import record.

    Only fields that really exist are filled. ``content_sha256`` comes from the record the
    server hashed itself; ``world_id`` / ``generator`` / ``snapshot_format`` from the
    manifest. Nothing is derived from the recipe fingerprint, and **no seed is read here**
    — the civ seed comes from the data itself (``build`` reads ``civ.seed``).
    """
    manifest = manifest if isinstance(manifest, dict) else {}
    record = record if isinstance(record, dict) else {}
    world = manifest.get('world') if isinstance(manifest.get('world'), dict) else {}
    snapshot = (manifest.get('snapshot')
                if isinstance(manifest.get('snapshot'), dict) else {})
    source = record.get('source') if isinstance(record.get('source'), dict) else {}
    return {
        'content_sha256': record.get('sha256') or source.get('content_sha256'),
        'world_id': world.get('id'),
        'import_id': record.get('id'),
        'branch': branch,
        'generator': snapshot.get('generator'),
        'snapshot_format': snapshot.get('format'),
        'terrain_seed': terrain_seed,
    }


# ======================================================================= data shape
def inspect(civ):
    """What the block actually carries — counts and years only, no interpretation."""
    if not isinstance(civ, dict):
        raise HistoryError('历史块不是对象')
    anomalies = _Anomalies()
    end_year = _year(civ.get('endYear'), 'endYear')
    regions = civ.get('regions')
    region_count = _int(regions.get('count') if isinstance(regions, dict) else None,
                        'regions.count', anomalies)
    log = civ.get('log')
    log_size = 0
    log_span = None
    if isinstance(log, dict):
        log_size = _int(log.get('size'), 'log.size', anomalies)
        years = log.get('year')
        if isinstance(years, list) and years and log_size > 0:
            try:
                log_span = [_year(years[0], 'log.year[0]'),
                            _year(years[min(log_size, len(years)) - 1], 'log.year[-1]')]
            except HistoryError as error:
                anomalies.note('log.year', str(error))
    cp_years = []
    for index, row in enumerate(_objects(civ.get('checkpoints'), 'checkpoints', anomalies)):
        try:
            cp_years.append(_year(row.get('year'), 'checkpoints[%d].year' % index))
        except HistoryError as error:
            anomalies.note('checkpoints[%d]' % index, str(error))
    upheaval_years = []
    for index, row in enumerate(_objects(civ.get('upheavals'), 'upheavals', anomalies)):
        try:
            upheaval_years.append(_year(row.get('year'), 'upheavals[%d].year' % index))
        except HistoryError as error:
            anomalies.note('upheavals[%d]' % index, str(error))
    annals = civ.get('annals')
    religion = civ.get('religion')
    kinds = {}
    for row in _objects(annals, 'annals', anomalies):
        kind = row.get('kind') if isinstance(row.get('kind'), str) else '(missing)'
        kinds[kind] = kinds.get(kind, 0) + 1
    seed = civ.get('seed')
    return {
        'end_year': end_year,
        'viable': civ.get('viable') is not False,
        'region_count': region_count,
        'counts': {
            'cultures': len(civ['cultures']) if isinstance(civ.get('cultures'), list) else 0,
            'polities': len(civ['polities']) if isinstance(civ.get('polities'), list) else 0,
            'settlements': (len(civ['settlements'])
                            if isinstance(civ.get('settlements'), list) else 0),
            'annals': len(annals) if isinstance(annals, list) else 0,
            'people': len(civ['people']) if isinstance(civ.get('people'), list) else 0,
            'upheavals': (len(civ['upheavals'])
                          if isinstance(civ.get('upheavals'), list) else 0),
            'log_entries': log_size,
            'checkpoints': len(cp_years),
        },
        'annal_kinds': dict(sorted(kinds.items())),
        'unknown_annal_kinds': sorted(kind for kind in kinds if kind not in ANNAL_AB),
        'first_checkpoint_year': min(cp_years) if cp_years else None,
        'last_checkpoint_year': max(cp_years) if cp_years else None,
        'log_span': log_span,
        'upheaval_years': sorted(upheaval_years),
        'civ_seed': seed if isinstance(seed, int) and not isinstance(seed, bool) else None,
        'has_people': isinstance(civ.get('people'), list) and bool(civ['people']),
        'has_religion': isinstance(religion, dict),
        'has_development': isinstance(civ.get('development'), dict),
        'anomalies': anomalies.dump(),
    }


# ====================================================================== region replay
def _log_view(log, region_count, anomalies):
    """Validate the change log once; return plain lists honouring ``size``.

    ``log.size`` is the valid prefix (``ChangeLog``: "只用前 size 条"); the typed arrays
    may be longer, so every array is cut to ``size`` and never trusted beyond it.
    """
    if not isinstance(log, dict):
        anomalies.note('log', '没有变化日志')
        return None
    size = log.get('size')
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        anomalies.note('log.size', '不是非负整数')
        return None
    if size > MAX_LOG_ENTRIES:
        raise HistoryError('变化日志 %d 条，超过 %d 条的可读上限' % (size, MAX_LOG_ENTRIES))
    arrays = {}
    for key in ('year', 'region', 'layer', 'value'):
        rows = log.get(key)
        if not isinstance(rows, list):
            anomalies.note('log.' + key, '缺失或不是数组')
            return None
        if len(rows) < size:
            anomalies.note('log.' + key, '只有 %d 项，少于 size=%d' % (len(rows), size))
            return None
        arrays[key] = rows
    years = []
    for index in range(size):
        try:
            years.append(_year(arrays['year'][index], 'log.year[%d]' % index))
        except HistoryError as error:
            anomalies.note('log.year[%d]' % index, str(error))
            return None
    for index in range(1, size):
        if years[index] < years[index - 1]:
            anomalies.note('log.year', '不是按年份排好（第 %d 条早于前一条）' % index)
            return None
    regions = arrays['region'][:size]
    layers = arrays['layer'][:size]
    values = arrays['value'][:size]
    for index in range(size):
        region = regions[index]
        if isinstance(region, bool) or not isinstance(region, int) \
                or not 0 <= region < region_count:
            anomalies.note('log.region[%d]' % index,
                           '州编号 %r 越界（州数 %d）' % (region, region_count))
            return None
        if layers[index] not in (0, 1):
            anomalies.note('log.layer[%d]' % index, '层 %r 不是 0/1' % (layers[index],))
            return None
        if isinstance(values[index], bool) or not isinstance(values[index], int):
            anomalies.note('log.value[%d]' % index, '归属 %r 不是整数' % (values[index],))
            return None
    return {'size': size, 'year': years, 'region': list(regions),
            'layer': list(layers), 'value': list(values)}


def _log_after(log, year):
    """Index of the first log entry whose year is > ``year`` (log is sorted)."""
    low, high = 0, log['size']
    years = log['year']
    while low < high:
        mid = (low + high) // 2
        if years[mid] <= year:
            low = mid + 1
        else:
            high = mid
    return low


def _checkpoints(checkpoints, region_count, anomalies):
    """Validated checkpoints, ascending by year, as ``[(year, culture, polity)]``."""
    if not isinstance(checkpoints, list):
        anomalies.note('checkpoints', '没有检查点')
        return None
    out = []
    for index, row in enumerate(checkpoints):
        if not isinstance(row, dict):
            anomalies.note('checkpoints[%d]' % index, '不是对象')
            return None
        try:
            year = _year(row.get('year'), 'checkpoints[%d].year' % index)
        except HistoryError as error:
            anomalies.note('checkpoints[%d]' % index, str(error))
            return None
        layers = {}
        for key in ('culture', 'polity'):
            values = row.get(key)
            if not isinstance(values, list):
                anomalies.note('checkpoint.' + key, '第 %d 个检查点没有这个数组' % index)
                return None
            if len(values) < region_count:
                # Upstream pads newer arrays; for older ones it leaves the tail alone. We
                # do not guess: pad with -1 and say so. The endYear self-check decides
                # whether this pair may be trusted at all.
                anomalies.note('checkpoint.' + key,
                               '第 %d 个检查点只有 %d 个州（州数 %d），尾部按 -1 处理'
                               % (index, len(values), region_count))
                values = list(values) + [-1] * (region_count - len(values))
            layers[key] = list(values[:region_count])
        out.append((year, layers['culture'], layers['polity']))
    for index in range(1, len(out)):
        if out[index][0] < out[index - 1][0]:
            anomalies.note('checkpoints', '不是按年份递增（第 %d 个）' % index)
            return None
    return out


def _owners_at(checkpoints, log, year, region_count):
    """Ownership at ``year`` = newest checkpoint ``<= year`` + log entries up to ``year``.

    Upstream snapshots the *live* arrays at year C (``sim.ts:718-725``), so a checkpoint
    already has every change up to and including C applied: the log replay starts strictly
    after C. Written from those field definitions; no upstream source line copied.
    """
    culture = [-1] * region_count
    polity = [-1] * region_count
    low, high = 0, len(checkpoints)
    while low < high:
        mid = (low + high) // 2
        if checkpoints[mid][0] <= year:
            low = mid + 1
        else:
            high = mid
    start = 0
    if low:
        _, snapshot_culture, snapshot_polity = checkpoints[low - 1]
        culture = list(snapshot_culture)
        polity = list(snapshot_polity)
        start = _log_after(log, checkpoints[low - 1][0])
    regions, layers, values, years = (log['region'], log['layer'], log['value'],
                                      log['year'])
    for index in range(start, log['size']):
        if years[index] > year:
            break
        if layers[index] == 0:
            culture[regions[index]] = values[index]
        else:
            polity[regions[index]] = values[index]
    return culture, polity


def _end_state(civ, region_count, anomalies):
    """The exported ``civ.culture`` / ``civ.polity`` — the ground truth for endYear."""
    out = {}
    for key in ('culture', 'polity'):
        values = civ.get(key)
        if not isinstance(values, list):
            anomalies.note(key, '导出里没有终态归属数组')
            return None
        if len(values) < region_count:
            anomalies.note(key, '只有 %d 个州（州数 %d）' % (len(values), region_count))
            return None
        out[key] = list(values[:region_count])
    return out


def _end_year_check(civ, checkpoints, log, region_count, end_year, anomalies):
    """Verify the log and the checkpoints agree, **without looking at the base year**.

    A checkpoint sitting exactly on ``endYear`` would make a naive check trivial (its arrays
    are the exported end state). So the anchor is the newest checkpoint **strictly before**
    ``endYear``; the replay then has to run through the remaining log to reach the exported
    ``civ.culture`` / ``civ.polity``. Picking year 5 instead of 2999 can never change this
    verdict — the function does not take a base year at all.

    When the only checkpoints are at/after ``endYear``, the log cannot be cross-checked; that
    is reported as ``checkpoint_only`` instead of being called verified.
    """
    end_state = _end_state(civ, region_count, anomalies)
    if end_state is None:
        return {'status': UNKNOWN, 'checked_at': None, 'mode': None,
                'reason': '导出里没有终态归属数组，无法自检检查点 + 日志是否自洽'}
    anchors = [entry for entry in checkpoints if entry[0] < end_year]
    if anchors:
        anchor_year, anchor_culture, anchor_polity = anchors[-1]
        culture, polity = list(anchor_culture), list(anchor_polity)
        start = _log_after(log, anchor_year)
        regions, layers, values = log['region'], log['layer'], log['value']
        applied = 0
        for index in range(start, log['size']):
            if log['year'][index] > end_year:
                break
            if layers[index] == 0:
                culture[regions[index]] = values[index]
            else:
                polity[regions[index]] = values[index]
            applied += 1
        mismatch = []
        if culture != end_state['culture']:
            mismatch.append('culture')
        if polity != end_state['polity']:
            mismatch.append('polity')
        if mismatch:
            anomalies.note('replay', '回放到 endYear 与导出终态不一致：%s'
                           % '、'.join(mismatch))
            return {'status': UNKNOWN, 'checked_at': end_year, 'mode': 'log_replay',
                    'anchor_checkpoint_year': anchor_year,
                    'log_entries_applied': applied, 'mismatched_layers': mismatch,
                    'reason': ('从检查点 %s 起回放变化日志到 endYear %s，与导出的终态数组对不上'
                               '（%s）；这一对数据不能互相印证，政区/民族层报 unknown，不猜'
                               % (anchor_year, end_year, '、'.join(mismatch)))}
        return {'status': EXACT, 'checked_at': end_year, 'mode': 'log_replay',
                'anchor_checkpoint_year': anchor_year,
                'log_entries_applied': applied, 'mismatched_layers': [],
                'reason': ('从检查点 %s 起把 (检查点年, endYear] 的变化日志全部叠上，'
                           '与导出终态逐州一致' % anchor_year)}
    at_end = [entry for entry in checkpoints if entry[0] == end_year]
    if at_end:
        _, snapshot_culture, snapshot_polity = at_end[-1]
        mismatch = []
        if snapshot_culture != end_state['culture']:
            mismatch.append('culture')
        if snapshot_polity != end_state['polity']:
            mismatch.append('polity')
        if mismatch:
            anomalies.note('replay', 'endYear 的检查点与导出终态不一致：%s'
                           % '、'.join(mismatch))
            return {'status': UNKNOWN, 'checked_at': end_year, 'mode': 'checkpoint_only',
                    'mismatched_layers': mismatch,
                    'reason': ('endYear 的检查点与导出终态数组不一致（%s）'
                               % '、'.join(mismatch))}
        return {'status': EXACT, 'checked_at': end_year, 'mode': 'checkpoint_only',
                'mismatched_layers': [],
                'reason': ('只有 endYear 当头的检查点：与终态一致，但没有更早的检查点可用来'
                           '把日志回放到 endYear，日志与检查点的一致性**未验证**')}
    return {'status': UNKNOWN, 'checked_at': None, 'mode': None,
            'reason': '检查点全部晚于 endYear，无法自检'}


def _replay_block(civ, base_year, anomalies):
    """Replay the region layers at ``base_year``, gated by the independent endYear check."""
    regions = civ.get('regions')
    region_count = 0
    if isinstance(regions, dict):
        raw = regions.get('count')
        if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
            region_count = raw
    if not region_count:
        return {'status': UNKNOWN, 'region_count': None,
                'reason': '导出里没有 regions.count，无法按州回放',
                'end_state_check': {'status': UNKNOWN, 'reason': '没有州数'}}
    if region_count > MAX_REGIONS:
        raise HistoryError('州数 %d 超过 %d 的可读上限' % (region_count, MAX_REGIONS))
    checkpoints = _checkpoints(civ.get('checkpoints'), region_count, anomalies)
    if not checkpoints:
        return {'status': UNKNOWN, 'region_count': region_count,
                'reason': '导出里没有可用的检查点，无法锚定该年的政区/民族',
                'end_state_check': {'status': UNKNOWN, 'reason': '没有检查点'}}
    log = _log_view(civ.get('log'), region_count, anomalies)
    if log is None:
        return {'status': UNKNOWN, 'region_count': region_count,
                'reason': '变化日志不可用（缺失或结构不符），无法从检查点往后回放',
                'end_state_check': {'status': UNKNOWN, 'reason': '日志不可用'}}
    end_year = _year(civ.get('endYear'), 'endYear')
    check = _end_year_check(civ, checkpoints, log, region_count, end_year, anomalies)
    if check['status'] != EXACT:
        return {'status': UNKNOWN, 'region_count': region_count,
                'end_state_check': check, 'reason': check['reason']}
    first_checkpoint = checkpoints[0][0]
    if base_year < first_checkpoint:
        return {'status': UNKNOWN, 'region_count': region_count,
                'end_state_check': check, 'first_checkpoint_year': first_checkpoint,
                'reason': ('基准年 %s 早于第一个检查点 %s：导出没有更早的锚定快照；'
                           '上游那种「从全 -1 开始翻日志」是另一种主张，本工程不用它冒充历史'
                           % (base_year, first_checkpoint))}
    used = max(year for year, _, _ in checkpoints if year <= base_year)
    culture, polity = _owners_at(checkpoints, log, base_year, region_count)
    return {'status': INTERVAL, 'region_count': region_count,
            'end_state_check': check, 'first_checkpoint_year': first_checkpoint,
            'checkpoint_year': used,
            'log_entries_applied': _log_after(log, base_year) - _log_after(log, used),
            'culture': culture, 'polity': polity,
            'reason': ('取 year ≤ 基准年的最近检查点，再叠加 (检查点年, 基准年] 的变化日志；'
                       '同一对数据另外独立回放到 endYear 与导出终态一致（已自检）')}


# ========================================================================= refs/names
def _safe_part(value, limit=48):
    """Ref segments are ASCII and separator-free; names never enter a ref."""
    out = []
    for char in str(value)[:limit]:
        out.append(char if (char.isascii() and (char.isalnum() or char in '_.:@|-')) else '_')
    return ''.join(out) or '_'


def _ref_prefix(identity):
    iv = identity if isinstance(identity, dict) else {}
    digest = str(iv.get('content_sha256') or '')[:16] or 'unpinned'
    world = str(iv.get('world_id') or '') or 'noworld'
    branch = str(iv.get('branch') or '') or 'unknown'
    return 'casnap:%s:%s/%s' % (_safe_part(digest), _safe_part(world), _safe_part(branch))


def _ref(prefix, kind, entity_id):
    return '%s/%s/%d' % (prefix, kind, entity_id)


def _display(name):
    """Every exported name travels with the reminder that it is an export-time label."""
    return {'display_name': name,
            'display_name_basis': 'export_time',
            'display_name_note': ('名字取自导出时（endYear）的实体记录，可能晚于基准年：'
                                  '改名、改朝/国号后缀、末名都不当基准年的事实')}


# =========================================================================== the build
def build(civ, *, base_year, window=None, identity=None, terrain=None,
          hidden_refs=(), include_regions=False,
          max_events=DEFAULT_MAX_EVENTS, max_entities=DEFAULT_MAX_ENTITIES):
    """Bounded historical-background candidates for ``base_year`` (author review only).

    ``civ``          decoded ``civ`` part (see :func:`decode_civ_part`).
    ``base_year``    integer year inside ``[0, endYear]``.
    ``window``       ``(from, to)`` inclusive years for the event lists; defaults to the
                     ``DEFAULT_WINDOW_YEARS`` years ending at ``base_year``. ``to`` may not
                     exceed ``base_year``: a base year never sees its own future.
    ``identity``     source pin: ``content_sha256``, ``world_id``, ``branch``,
                     ``import_id``, ``generator``, ``snapshot_format``, ``terrain_seed``
                     (see :func:`identity_from`). A seed supplied here **never** overrides
                     the real ``civ.seed`` read from the data.
    ``terrain``      optional ``{'eras_block': bool, 'era_until': [...],
                     'upheaval_years': [...]}`` from the caller that decoded ``eras``.
    ``hidden_refs``  refs the author marked not-for-players; removed from every list and
                     only counted here on the author side.
    """
    if not isinstance(civ, dict):
        raise HistoryError('历史块不是对象')
    year = _base_year(base_year)
    if year < 0:
        raise HistoryError('基准年不能是负数（%d）' % year)
    end_year = _year(civ.get('endYear'), 'endYear')
    if year > end_year:
        raise HistoryError('基准年 %d 晚于这份历史的结束年 %s：只有过去的年份可回放'
                           % (year, end_year))
    if max_events <= 0 or max_entities <= 0:
        raise HistoryError('预算必须是正整数')

    anomalies = _Anomalies()
    shape = inspect(civ)
    prefix = _ref_prefix(identity)
    hidden = {str(item) for item in (hidden_refs or ())}

    from_year, to_year = _window(window, year, end_year)
    annals_block = _annals(civ, from_year, to_year, year, end_year, prefix, hidden,
                           anomalies, max_events)
    replay = _replay_block(civ, year, anomalies)
    polities, polity_counts = _polities(civ, year, prefix, hidden, anomalies, max_entities)
    settlements, settlement_counts = _settlements(civ, year, prefix, hidden, anomalies,
                                                 max_entities)
    people, people_counts = _people(civ, year, prefix, hidden, anomalies, max_entities)
    religion = _religion(civ, year, from_year, to_year, prefix, hidden, anomalies,
                         max_entities)
    terrain_block = _terrain(civ, terrain, year, shape, anomalies)
    field_status = _field_status(shape, replay, polity_counts, settlement_counts,
                                 people_counts, religion)

    return {
        'schema': SCHEMA,
        'kind': KIND,
        'provenance': {
            'reader': 'app/civ_atlas_history.py（独立实现的只读解析器）',
            'spec_commit': SPEC_COMMIT,
            'source_repo': 'https://github.com/guaner-334/civ-atlas',
            'format_scope': {'generator': GENERATOR_VERSION,
                             'snapshot_format': SNAPSHOT_FORMAT},
            'license_note': LICENSE_NOTE,
            'upstream_code_copied': False,
        },
        'identity': _identity(identity, shape, prefix),
        'selection': {
            'base_year': year,
            'end_year': end_year,
            'window': {'from': from_year, 'to': to_year},
            'window_years': to_year - from_year,
            'include_regions': bool(include_regions),
            'max_events': max_events,
            'max_entities': max_entities,
            'hidden_refs': sorted(ref[:200] for ref in hidden),
        },
        'data_shape': shape,
        'terrain': terrain_block,
        'region_replay': _region_block(replay, prefix, include_regions),
        'annals': annals_block,
        'polities': dict(polity_counts, items=polities),
        'settlements': dict(settlement_counts, items=settlements),
        'people': dict(people_counts, items=people),
        'religion': religion,
        'field_status': field_status,
        'unknown': [{'field': field, 'reason': field_status[field]['note']}
                    for field in FIELDS if field_status[field]['status'] == UNKNOWN],
        'anomalies': anomalies.dump(),
        'limits': _limits_text(),
        'for_author_review': True,
        'auto_canonical': False,
    }


def _window(window, base_year, end_year):
    if window is None:
        return max(0, base_year - DEFAULT_WINDOW_YEARS), base_year
    if not isinstance(window, (tuple, list)) or len(window) != 2:
        raise HistoryError('window 必须是 (起始年, 结束年)')
    start = _year(window[0], 'window.from')
    stop = _year(window[1], 'window.to')
    if start < 0 or stop < 0:
        raise HistoryError('窗口年份不能是负数')
    if start > stop:
        raise HistoryError('窗口起始年 %s 晚于结束年 %s' % (start, stop))
    if stop > base_year:
        raise HistoryError('窗口结束年 %s 晚于基准年 %s：基准年看不到自己的未来'
                           % (stop, base_year))
    if stop > end_year:
        raise HistoryError('窗口结束年 %s 晚于这份历史的结束年 %s' % (stop, end_year))
    return start, stop


def _identity(identity, shape, prefix):
    iv = identity if isinstance(identity, dict) else {}
    branch = _text(iv.get('branch'), 120) or None
    # The data's own seed wins. A seed passed in by the caller never overrides it.
    data_seed = shape.get('civ_seed')
    caller_seed = iv.get('civ_seed')
    caller_seed = (caller_seed if isinstance(caller_seed, int)
                   and not isinstance(caller_seed, bool) else None)
    terrain_seed = iv.get('terrain_seed')
    terrain_seed = (terrain_seed if isinstance(terrain_seed, int)
                    and not isinstance(terrain_seed, bool) else None)
    return {
        'content_sha256': _text(iv.get('content_sha256'), 64),
        'world_id': _text(iv.get('world_id'), 64),
        'import_id': _text(iv.get('import_id'), 64),
        'branch': branch,
        'branch_known': branch is not None,
        'civ_seed': data_seed,
        'civ_seed_source': 'civ.seed' if data_seed is not None else None,
        'civ_seed_known': data_seed is not None,
        'caller_supplied_civ_seed_ignored': (caller_seed is not None
                                             and caller_seed != data_seed),
        'terrain_seed': terrain_seed,
        'terrain_seed_known': terrain_seed is not None,
        'terrain_seed_source': ('caller (map.params.seed)' if terrain_seed is not None
                                else None),
        'generator': GENERATOR_VERSION,
        'snapshot_format': SNAPSHOT_FORMAT,
        'end_year': shape['end_year'],
        'ref_prefix': prefix,
        'ref_note': '所有稳定 ref 都带 world/branch/来源身份；名字只供显示，绝不当 id',
        'seed_note': ('civ.seed 是这份导出里真有的字段，直接采用；地形种子若原件里没有 '
                      'map.params.seed 就留 null。不从 recipe 指纹反推任何种子'),
    }


def _annals(civ, from_year, to_year, base_year, end_year, prefix, hidden, anomalies,
            max_events):
    rows = civ.get('annals')
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise HistoryError('annals 不是数组')
    if len(rows) > MAX_ANNALS:
        raise HistoryError('史事 %d 条，超过 %d 条的可读上限' % (len(rows), MAX_ANNALS))
    events = []
    before_base = in_window = after_end = unknown_kind = 0
    previous = None
    sorted_ok = True
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            anomalies.note('annals[%d]' % index, '不是对象')
            continue
        try:
            event_year = _year(row.get('year'), 'annals[%d].year' % index)
        except HistoryError as error:
            anomalies.note('annals[%d]' % index, str(error))
            continue
        if event_year > end_year:
            after_end += 1
            continue
        if previous is not None and event_year < previous:
            anomalies.note('annals', '不是按年份排好（第 %d 条早于前一条）' % index)
            sorted_ok = False
        previous = event_year
        if event_year <= base_year:
            before_base += 1
        if not from_year <= event_year <= to_year:
            continue
        in_window += 1
        kind = row.get('kind') if isinstance(row.get('kind'), str) else None
        known = kind in ANNAL_AB
        if not known:
            unknown_kind += 1
        side_a, side_b = ANNAL_AB.get(kind, (None, None))
        ref = '%s/annal/%d' % (prefix, index)
        if ref in hidden:
            continue
        item = {'ref': ref, 'index': index, 'year': event_year, 'kind': kind,
                'kind_known': known, 'provenance': 'structured_simulation',
                'disclosure': 'author_side_candidate'}
        if not known:
            item['unresolved'] = ('这个 kind 不在本读取器认识的 types.ts 表里：'
                                  'a/b/region/war 原样保留，不猜测含义')
        for column, side in (('a', side_a), ('b', side_b)):
            entity_id = _int(row.get(column), 'annals[%d].%s' % (index, column), anomalies)
            item[column + '_means'] = side
            if side is None:
                # This column is a count / index / code for this kind, not an entity id.
                item[column + '_id'] = None
                item[column + '_ref'] = None
                if column in row:
                    item[column + '_raw'] = row[column]
            else:
                item[column + '_id'] = None if entity_id < 0 else entity_id
                item[column + '_ref'] = (_ref(prefix, side, entity_id)
                                         if entity_id >= 0 else None)
        item['region_means'] = 'region id'
        item['region'] = _int(row.get('region'), 'annals[%d].region' % index, anomalies)
        settlement_id = _int(row.get('settlement'), 'annals[%d].settlement' % index,
                             anomalies)
        item['settlement_ref'] = (_ref(prefix, 'settlement', settlement_id)
                                  if settlement_id >= 0 else None)
        item['war'] = _int(row.get('war'), 'annals[%d].war' % index, anomalies)
        item['raw_columns'] = {key: row[key]
                               for key in ('a', 'b', 'region', 'settlement', 'war')
                               if key in row}
        note = ANNAL_COLUMN_NOTES.get(kind) if known else None
        if note:
            item['column_note'] = note
        for optional in ('cause', 'via'):
            value = row.get(optional)
            if value is None or isinstance(value, bool):
                continue
            if isinstance(value, str):
                item[optional] = _text(value, 40)
            elif isinstance(value, int):
                item[optional] = value
        for optional in ('n', 'foe', 'by', 'opt', 'until'):
            if optional not in row:
                continue
            value = row[optional]
            if value is None or isinstance(value, bool):
                continue
            if isinstance(value, int):
                item[optional] = value
            elif isinstance(value, float) and math.isfinite(value):
                item[optional] = value
            else:
                anomalies.note('annals[%d].%s' % (index, optional),
                               '不是数字：%r' % (value,))
        if isinstance(row.get('ps'), list):
            item['ps'] = [value for value in row['ps']
                          if isinstance(value, int) and not isinstance(value, bool)][:16]
        events.append(item)
    returned = events[:max_events]
    return {
        'window': {'from': from_year, 'to': to_year},
        'counts': {
            'total_in_export': len(rows),
            'on_or_before_base_year': before_base,
            'inside_window': in_window,
            'returned': len(returned),
            'hidden': in_window - len(events),
            'after_end_year': after_end,
            'unknown_kind': unknown_kind,
            'truncated': len(events) > len(returned),
        },
        'events': returned,
        'years_sorted': sorted_ok,
        'is_full_state': False,
        'note': ('按年筛出来的是「这一段时间里发生了哪些事」的事实清单，不是该年的完整状态；'
                 '状态请看 region_replay / polities / settlements'),
        'ai_chronicle_used': False,
        'ai_chronicle_note': ('上游的 AI 扩写史书（编年史正文）不被当作事件事实：'
                              '本接口只读结构化史事 annals'),
    }


def _polities(civ, year, prefix, hidden, anomalies, limit):
    rows = _objects(civ.get('polities'), 'polities', anomalies)
    items = []
    alive = rejected = 0
    for row in rows:
        entity_id = _int(row.get('id'), 'polity.id', anomalies)
        if entity_id < 0:
            rejected += 1
            continue
        founded = _opt_year(row.get('founded'), 'polity.founded', anomalies)
        ended = _opt_year(row.get('ended'), 'polity.ended', anomalies)
        if founded is None:
            rejected += 1
            anomalies.note('polity.founded', '国家 %d 没有立国年，不给区间' % entity_id)
            continue
        if not (founded <= year and (ended is None or year < ended)):
            continue
        alive += 1
        ref = _ref(prefix, 'polity', entity_id)
        if ref in hidden:
            continue
        spans = []
        raw_spans = row.get('capitals')
        if isinstance(raw_spans, list):
            for entry in raw_spans:
                if not isinstance(entry, dict):
                    continue
                entry_year = _opt_year(entry.get('year'), 'polity.capitals.year', anomalies)
                settlement_id = _int(entry.get('settlement'), 'polity.capitals.settlement',
                                     anomalies)
                if entry_year is None or settlement_id < 0:
                    continue
                spans.append({'year': entry_year,
                              'settlement_ref': _ref(prefix, 'settlement', settlement_id)})
        # A capital is only claimed from a *valid* capitals[] span. ``polity.capital`` alone
        # is the founding capital and says nothing about the base year.
        capital_ref = None
        capital_status = UNKNOWN
        capital_note = ('导出里没有 capitals[]：polity.capital 只是立国时的国都，'
                        '不能当基准年的国都')
        usable = [span for span in spans if span['year'] <= year]
        if usable:
            capital_ref = usable[-1]['settlement_ref']
            capital_status = INTERVAL
            capital_note = 'capitals[] 里 year ≤ 基准年的最后一条'
        elif spans:
            capital_note = 'capitals[] 有，但第一条晚于基准年：该年国都未知'
        items.append({
            'ref': ref, 'id': entity_id,
            **_display(_text(row.get('name'))),
            'culture_ref': (_ref(prefix, 'culture', row['culture'])
                            if isinstance(row.get('culture'), int)
                            and not isinstance(row.get('culture'), bool)
                            and row['culture'] >= 0 else None),
            'founded': founded, 'ended': ended,
            'alive_interval': {'from': founded, 'until': ended},
            'capital_ref': capital_ref,
            'capital_status': capital_status,
            'capital_note': capital_note,
            'capital_spans': spans[:MAX_SPANS],
            'capital_spans_truncated': len(spans) > MAX_SPANS,
            'status': 'as_of_interval',
            'evidence': ['founded', 'ended', 'capitals'],
            'not_for_public': ['ended', 'capitals_after_base_year', 'dynasties', 'titles'],
        })
    items.sort(key=lambda item: item['id'])
    return items[:limit], {'alive_at_base_year': alive, 'returned': min(len(items), limit),
                           'truncated': len(items) > limit,
                           'rejected_missing_years': rejected}


def _settlements(civ, year, prefix, hidden, anomalies, limit):
    rows = _objects(civ.get('settlements'), 'settlements', anomalies)
    items = []
    alive = rejected = 0
    for row in rows:
        entity_id = _int(row.get('id'), 'settlement.id', anomalies)
        if entity_id < 0:
            rejected += 1
            continue
        founded = _opt_year(row.get('founded'), 'settlement.founded', anomalies)
        ended = _opt_year(row.get('ended'), 'settlement.ended', anomalies)
        if founded is None:
            rejected += 1
            anomalies.note('settlement.founded', '城 %d 没有建城年' % entity_id)
            continue
        if not (founded <= year and (ended is None or year < ended)):
            continue
        alive += 1
        ref = _ref(prefix, 'settlement', entity_id)
        if ref in hidden:
            continue
        spans = []
        for entry in (row.get('capitalSpans') or ()):
            if not isinstance(entry, dict):
                continue
            start = _opt_year(entry.get('from'), 'settlement.capitalSpans.from', anomalies)
            stop = _opt_year(entry.get('until'), 'settlement.capitalSpans.until', anomalies)
            polity_id = _int(entry.get('polity'), 'settlement.capitalSpans.polity',
                             anomalies)
            if start is None:
                continue
            if not (start <= year and (stop is None or year < stop)):
                continue
            spans.append({'from': start, 'until': stop,
                          'polity_ref': (_ref(prefix, 'polity', polity_id)
                                         if polity_id >= 0 else None)})
        items.append({
            'ref': ref, 'id': entity_id,
            **_display(_text(row.get('name'))),
            'founded': founded, 'ended': ended,
            'alive_interval': {'from': founded, 'until': ended},
            'region': _int(row.get('region'), 'settlement.region', anomalies),
            'cell': _int(row.get('cell'), 'settlement.cell', anomalies),
            'capital_spans_at_year': spans[:MAX_SPANS],
            'capital_spans_truncated': len(spans) > MAX_SPANS,
            'population': UNKNOWN,
            'population_note': UNKNOWN_BY_FORMAT['population'],
            'status': 'as_of_interval',
            'evidence': ['founded', 'ended', 'capitalSpans'],
            'not_for_public': ['ended', 'sacks', 'reshaped', 'rebuilds', 'devCap'],
        })
    items.sort(key=lambda item: item['id'])
    return items[:limit], {'alive_at_base_year': alive, 'returned': min(len(items), limit),
                           'truncated': len(items) > limit,
                           'rejected_missing_years': rejected}


def _people(civ, year, prefix, hidden, anomalies, limit):
    rows = _objects(civ.get('people'), 'people', anomalies)
    if not rows:
        return [], {'available': False, 'alive_at_base_year': 0, 'returned': 0,
                    'truncated': False, 'rejected_missing_years': 0}
    items = []
    alive = rejected = 0
    for row in rows:
        entity_id = _int(row.get('id'), 'person.id', anomalies)
        if entity_id < 0:
            rejected += 1
            continue
        born = _opt_year(row.get('born'), 'person.born', anomalies)
        died = _opt_year(row.get('died'), 'person.died', anomalies)
        if born is None:
            rejected += 1
            anomalies.note('person.born', '人物 %d 没有生年' % entity_id)
            continue
        if not (born <= year and (died is None or year < died)):
            continue
        alive += 1
        ref = _ref(prefix, 'person', entity_id)
        if ref in hidden:
            continue
        role = row.get('role') if isinstance(row.get('role'), str) else None
        in_office = None
        if role in ('ruler', 'minister', 'general'):
            start = _opt_year(row.get('from'), 'person.from', anomalies)
            stop = _opt_year(row.get('until'), 'person.until', anomalies)
            in_office = {'from': start, 'until': stop,
                         'at_base_year': (start is not None and start <= year
                                          and (stop is None or year < stop))}
        polity_id = _int(row.get('polity'), 'person.polity', anomalies)
        items.append({
            'ref': ref, 'id': entity_id, 'role': role,
            **_display(_text(row.get('name'))),
            'name_is_author_placeholder': row.get('author') is not None,
            'polity_ref': (_ref(prefix, 'polity', polity_id) if polity_id >= 0 else None),
            'born': born, 'died': died,
            'in_office': in_office,
            'status': 'as_of_interval',
            'evidence': ['born', 'died'] + (['from', 'until'] if in_office else []),
            'not_for_public': ['died', 'fate', 'until', 'regencies', 'exile', 'claim'],
        })
    items.sort(key=lambda item: item['id'])
    return items[:limit], {'available': True, 'alive_at_base_year': alive,
                           'returned': min(len(items), limit),
                           'truncated': len(items) > limit,
                           'rejected_missing_years': rejected}


def _religion(civ, year, from_year, to_year, prefix, hidden, anomalies, limit):
    religion = civ.get('religion')
    if not isinstance(religion, dict):
        return {'available': False, 'events': [],
                'counts': {'in_window': 0, 'returned': 0, 'truncated': False},
                'state_faiths': [], 'note': '导出里没有信仰块（旧数据或这份历史没算）',
                'region_faith': UNKNOWN,
                'region_faith_note': ('信仰有自己的一套 log/checkpoints，本相位不回放，'
                                      '所以「某年各州信什么」是 unknown')}
    events = []
    in_window = 0
    for index, row in enumerate(_objects(religion.get('events'), 'religion.events',
                                         anomalies)):
        event_year = _opt_year(row.get('year'), 'religion.events.year', anomalies)
        if event_year is None or not from_year <= event_year <= to_year:
            continue
        in_window += 1
        ref = '%s/faith-event/%d' % (prefix, index)
        if ref in hidden:
            continue
        faith_id = _int(row.get('faith'), 'religion.events.faith', anomalies)
        polity_id = _int(row.get('polity'), 'religion.events.polity', anomalies)
        events.append({
            'ref': ref, 'year': event_year,
            'kind': row.get('kind') if isinstance(row.get('kind'), str) else None,
            'faith_ref': (_ref(prefix, 'faith', faith_id) if faith_id >= 0 else None),
            'polity_ref': (_ref(prefix, 'polity', polity_id) if polity_id >= 0 else None),
            'region': _int(row.get('region'), 'religion.events.region', anomalies),
            'provenance': 'structured_simulation',
        })
    states = []
    for entry in _objects(religion.get('states'), 'religion.states', anomalies):
        start = _opt_year(entry.get('from'), 'religion.states.from', anomalies)
        stop = _opt_year(entry.get('until'), 'religion.states.until', anomalies)
        if start is None or not (start <= year and (stop is None or year < stop)):
            continue
        polity_id = _int(entry.get('polity'), 'religion.states.polity', anomalies)
        faith_id = _int(entry.get('faith'), 'religion.states.faith', anomalies)
        states.append({'polity_ref': (_ref(prefix, 'polity', polity_id)
                                      if polity_id >= 0 else None),
                       'faith_ref': (_ref(prefix, 'faith', faith_id)
                                     if faith_id >= 0 else None),
                       'from': start, 'until': stop})
    events.sort(key=lambda item: (item['year'], item['ref']))
    return {'available': True, 'events': events[:limit],
            'counts': {'in_window': in_window, 'returned': min(len(events), limit),
                       'truncated': len(events) > limit},
            'state_faiths': states[:limit],
            'region_faith': UNKNOWN,
            'region_faith_note': ('信仰有自己的一套 log/checkpoints，本相位不回放，'
                                  '所以「某年各州信什么」是 unknown')}


def _terrain(civ, terrain, year, shape, anomalies):
    """Is the map we hold the map of ``year``? ``eras`` is terrain, not history."""
    terrain = terrain if isinstance(terrain, dict) else {}
    upheaval_years = list(shape.get('upheaval_years') or [])
    for value in terrain.get('upheaval_years') or ():
        try:
            year_value = _year(value, 'terrain.upheaval_years')
        except HistoryError as error:
            anomalies.note('terrain.upheaval_years', str(error))
            continue
        if year_value not in upheaval_years:
            upheaval_years.append(year_value)
    upheaval_years.sort()
    eras_block = bool(terrain.get('eras_block'))
    era_until = []
    for value in terrain.get('era_until') or ():
        try:
            era_until.append(_year(value, 'terrain.era_until'))
        except HistoryError as error:
            anomalies.note('terrain.era_until', str(error))
    era_until.sort()
    if not upheaval_years and not eras_block:
        return {'state': 'same_terrain_all_years',
                'current_map_year_range': {'from': None, 'to': shape['end_year']},
                'base_year_uses_current_map': True,
                'era_block_present': False,
                'upheaval_years': [],
                'last_terrain_change': None,
                'era_until': [],
                'era_block_is_terrain_not_history': True,
                'era_block_note': ('eras 块（src/gen/snapshot.ts:9）是地形演化各段，不是历史；'
                                   '不当作某年的事态'),
                'note': ('这份历史没有地形大事：当前地图在所有年份都是同一份地形。'
                         '这只说明地形没变，不代表该年的政区已复原')}
    last = max(upheaval_years[-1] if upheaval_years else float('-inf'),
               era_until[-1] if era_until else float('-inf'))
    last = None if last == float('-inf') else last
    matched = last is not None and year >= last
    return {
        'state': 'current_terrain' if matched else 'unmatched',
        'upheaval_years': upheaval_years[:40],
        'upheavals_truncated': len(upheaval_years) > 40,
        'era_block_present': eras_block,
        'era_until': era_until[:40],
        'last_terrain_change': last,
        'base_year_uses_current_map': bool(matched),
        'note': ('该年之后还有地形变更：当前 regions/places 描述的是最后一次变更以后的地形。'
                 if matched else
                 ('基准年 %s 早于最后一次地形变更（%s）：我们手上的图是变更以后的地形，'
                  '与该年的地形不匹配；本接口明确标「未关联」，不冒称把该年的地形复原了'
                  % (year, last))),
        'era_block_is_terrain_not_history': True,
        'era_block_note': ('eras 块（src/gen/snapshot.ts:9）是地形演化各段，不是历史；'
                           '不当作某年的事态'),
    }


def _region_block(replay, prefix, include_regions):
    status = replay.get('status', UNKNOWN)
    block = {
        'status': status,
        'evidence': '检查点 + 变化日志回放' if status == INTERVAL else None,
        'region_count': replay.get('region_count'),
        'first_checkpoint_year': replay.get('first_checkpoint_year'),
        'checkpoint_year_used': replay.get('checkpoint_year'),
        'log_entries_applied': replay.get('log_entries_applied'),
        'end_state_check': replay.get('end_state_check'),
        'reason': replay.get('reason'),
        'note': '这一层给的是「哪一州归谁」的硬数据；名字不参与身份判定',
        'culture': None, 'polity': None,
        'culture_legend': None, 'polity_legend': None,
    }
    if status != INTERVAL:
        return block
    culture = replay.get('culture') or []
    polity = replay.get('polity') or []
    block['counts'] = {
        'regions': len(culture),
        'culture_unowned': sum(1 for value in culture if value < 0),
        'polity_unowned': sum(1 for value in polity if value < 0),
        'distinct_cultures': len({value for value in culture if value >= 0}),
        'distinct_polities': len({value for value in polity if value >= 0}),
    }
    block['culture_legend'] = {str(value): _ref(prefix, 'culture', value)
                               for value in sorted({v for v in culture if v >= 0})[:400]}
    block['polity_legend'] = {str(value): _ref(prefix, 'polity', value)
                              for value in sorted({v for v in polity if v >= 0})[:400]}
    if include_regions:
        block['culture'] = list(culture)
        block['polity'] = list(polity)
    else:
        block['note'] = ('默认只给计数与图例；逐州数组要显式 include_regions=True '
                         '（上百个州的数组不该悄悄塞进上下文）')
    return block


def _field_status(shape, replay, polities, settlements, people, religion):
    """Per field: what the *data at hand* supports, with the evidence named."""
    region_status = replay.get('status', UNKNOWN)
    region_reason = replay.get('reason')
    counts = shape.get('counts') or {}
    status = {}
    for field in ('region_culture', 'region_polity'):
        status[field] = {
            'status': region_status,
            'evidence': ('checkpoints + log 回放；另独立回放到 endYear 与导出终态逐州一致'
                         if region_status == INTERVAL else None),
            'note': (region_reason if region_status != INTERVAL else
                     '按检查点 + 日志回放得到该年的%s归属（州级）'
                     % ('民族' if field == 'region_culture' else '国家')),
        }
    has_annals = bool(counts.get('annals'))
    status['annals'] = {
        'status': EXACT if has_annals else UNKNOWN,
        'evidence': '每条史事自带年份' if has_annals else None,
        'note': ('按年筛出窗口内事件；这是事实清单，不是该年的完整状态'
                 if has_annals else '导出里没有结构化史事'),
    }
    has_polities = bool(counts.get('polities'))
    status['polity_founded'] = {
        'status': INTERVAL if has_polities else UNKNOWN,
        'evidence': 'founded ≤ 年 < ended',
        'note': ('按立国/灭亡年过滤；缺年份的国家计入 rejected，不猜'
                 if has_polities else '导出里没有国家'),
    }
    status['polity_capital_spans'] = {
        'status': INTERVAL if has_polities else UNKNOWN,
        'evidence': 'capitals[] 里 year ≤ 基准年的最后一条（capital 只是立国时的国都）',
        'note': ('逐年国都可查；国号档位与朝代名要另算，本接口不给'
                 if has_polities else '导出里没有国家'),
    }
    has_settlements = bool(counts.get('settlements'))
    status['settlement_lifespan'] = {
        'status': INTERVAL if has_settlements else UNKNOWN,
        'evidence': 'founded ≤ 年 < ended',
        'note': ('按建城/毁废年过滤；末年的城不会投到过去'
                 if has_settlements else '导出里没有城镇'),
    }
    status['settlement_capital_spans'] = {
        'status': INTERVAL if has_settlements else UNKNOWN,
        'evidence': 'capitalSpans[] 里 from ≤ 年 < until 的那些段',
        'note': ('某年是不是国都可查；当年人口是 unknown'
                 if has_settlements else '导出里没有城镇'),
    }
    status['people_lifespan'] = {
        'status': INTERVAL if people.get('available') else UNKNOWN,
        'evidence': 'born ≤ 年 < died，在位/在朝看 from ≤ 年 < until',
        'note': ('按生卒与在位区间过滤' if people.get('available')
                 else '导出里没有人物（旧数据或这份历史没算人物）'),
    }
    status['religion_events'] = {
        'status': EXACT if religion.get('available') else UNKNOWN,
        'evidence': 'religion.events 每条自带年份' if religion.get('available') else None,
        'note': ('按年筛；各州信仰（religion.log/checkpoints）不回放，是 unknown'
                 if religion.get('available') else '导出里没有信仰块'),
    }
    for field, reason in UNKNOWN_BY_FORMAT.items():
        status[field] = {'status': UNKNOWN, 'evidence': None, 'note': reason}
    for field in FIELDS:
        status.setdefault(field, {'status': UNKNOWN, 'evidence': None,
                                  'note': '本接口没有实现这个字段'})
    return {field: status[field] for field in FIELDS}


def _limits_text():
    return [
        '只读：本模块不联网、不读文件/URL、不跑上游代码、不写回任何数据',
        '读取范围：generator %d / snapshot_format %d 的 civ 块（上游 %s）'
        % (GENERATOR_VERSION, SNAPSHOT_FORMAT, SPEC_COMMIT[:12]),
        '基准年是有限数字（可含小数），落在 [0, endYear]；晚于结束年直接拒收',
        '早于第一个检查点的年份：政区/民族层报 unknown，不从全 -1 起翻日志冒充锚定快照',
        '检查点 + 日志独立回放到 endYear 与导出终态不一致时：政区/民族层报 unknown 并记异常',
        'annals 只给窗口内事件（默认基准年往前 %d 年），计数仍精确；它不是该年的完整状态'
        % DEFAULT_WINDOW_YEARS,
        'population / resources / routes / terrain / 基准年的实体名字：unknown，不移植上游公式',
        '有地形大事时，基准年早于最后一件大事 → 地图标 unmatched（不冒称复原该年地形）',
        'eras 块是地形版本，不是历史',
        '上游 AI 扩写史书不当事件事实；事件只来自结构化 annals',
        '输出是给作者审核的候选，不自动正典、不直接改会话；公开投影走 public_view',
    ]


# ==================================================================== public view
#: What the player-side projection may carry, per entity kind. Everything else an entity
#: knows (death year, fate, dated sacks, later capitals, dynasty names, endings) stays out,
#: so authorizing a field never leaks the future.
PUBLIC_ENTITY_FIELDS = {
    'polities': ('ref', 'id', 'display_name', 'display_name_note', 'founded',
                 'capital_ref', 'capital_status'),
    'settlements': ('ref', 'id', 'display_name', 'display_name_note', 'founded', 'region'),
    'people': ('ref', 'id', 'display_name', 'display_name_note', 'role', 'born',
               'polity_ref'),
}

#: Fields ``public_view`` accepts in ``allow``.
PUBLIC_FIELDS = ('annals', 'polities', 'settlements', 'people', 'religion_events',
                 'region_culture', 'region_polity')


def public_view(document, *, allow=(), max_events=None):
    """Project the author-side document down to what players may see (pure, no IO).

    Default ``allow=()`` projects **no narrative at all**: only the year, the window,
    terrain association and per-field status. Every list of events or entities requires
    its field in ``allow``, and even then each entity goes through
    :data:`PUBLIC_ENTITY_FIELDS` — a person alive at the base year never exposes their
    death year or fate, a polity never exposes ``ended``, a capital that changed later
    stays out. Refs the author marked hidden are dropped again here, and the count of
    hidden items is **not** reported to the player side.
    """
    if not isinstance(document, dict):
        raise HistoryError('文档不是对象')
    allowed = {str(item) for item in (allow or ())}
    unknown_allow = sorted(allowed - set(PUBLIC_FIELDS))
    if unknown_allow:
        raise HistoryError('allow 里有不认识的项目：%s' % '、'.join(unknown_allow))
    hidden = {str(item) for item in ((document.get('selection') or {}).get('hidden_refs')
                                     or ())}
    selection = document.get('selection') or {}
    status = document.get('field_status') or {}
    if max_events is not None and max_events <= 0:
        raise HistoryError('max_events 必须是正整数')
    view = {
        'schema': document.get('schema'),
        'kind': (document.get('kind') or '') + '.public',
        'base_year': selection.get('base_year'),
        'window': selection.get('window'),
        'terrain': {'state': (document.get('terrain') or {}).get('state'),
                    'note': (document.get('terrain') or {}).get('note')},
        'field_status': {field: ((status.get(field) or {}).get('status')
                                 if isinstance(status.get(field), dict)
                                 else status.get(field))
                         for field in FIELDS},
        'disclosure': {'allowed': sorted(allowed)},
        'withheld': [field for field in PUBLIC_FIELDS if field not in allowed],
        'auto_canonical': False,
    }

    def visible(item):
        return isinstance(item, dict) and item.get('ref') not in hidden

    if 'annals' in allowed:
        annals = document.get('annals') or {}
        kept = []
        for item in annals.get('events') or ():
            if not visible(item):
                continue
            kept.append({key: item[key] for key in
                         ('ref', 'year', 'kind', 'kind_known', 'a_ref', 'a_means',
                          'b_ref', 'b_means', 'region', 'settlement_ref', 'war',
                          'provenance') if key in item})
        if max_events is not None:
            kept = kept[:max_events]
        view['annals'] = {'events': kept,
                          'note': '玩家侧只看到作者批准投影的事件；不是该年完整状态'}
    else:
        view['annals'] = {'events': [], 'withheld': True}

    for key in ('polities', 'settlements', 'people'):
        block = document.get(key) or {}
        if key not in allowed:
            view[key] = {'items': [], 'withheld': True}
            continue
        fields = PUBLIC_ENTITY_FIELDS[key]
        items = []
        for item in block.get('items') or ():
            if not visible(item):
                continue
            kept = {field: item.get(field) for field in fields if field in item}
            if key == 'people':
                office = item.get('in_office')
                kept['in_office_at_base_year'] = (bool(office.get('at_base_year'))
                                                  if isinstance(office, dict) else None)
            items.append(kept)
        view[key] = {'items': items}

    religion = document.get('religion') or {}
    if 'religion_events' in allowed:
        view['religion'] = {
            'events': [item for item in religion.get('events') or () if visible(item)],
            'state_faiths': list(religion.get('state_faiths') or ()),
        }
    else:
        view['religion'] = {'events': [], 'withheld': True}

    region = document.get('region_replay') or {}
    for key, field in (('culture', 'region_culture'), ('polity', 'region_polity')):
        values = region.get(key)
        if field in allowed and isinstance(values, list):
            view[key] = {'values': list(values), 'legend': region.get(key + '_legend')}
        else:
            view[key] = {'values': None, 'withheld': True}
    if 'region_culture' in allowed or 'region_polity' in allowed:
        view['counts'] = {
            'polities_alive_at_base_year': (document.get('polities') or {})
            .get('alive_at_base_year'),
            'settlements_alive_at_base_year': (document.get('settlements') or {})
            .get('alive_at_base_year'),
            'region_replay_status': region.get('status'),
        }
    return view
