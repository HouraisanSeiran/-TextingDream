# -*- coding: utf-8 -*-
"""World basis: a source-pinned record of *where* a world came from, honestly labelled.

This is deliberately **not** the element/town schema. It answers one question — "which
world, which branch, which base year, pinned to which exact bytes" — so a story package
can still say what it was built on after the ``external/civ-atlas`` folder is long gone.

Three things this module refuses to overstate:

1. **Capability vs. implementation.** ``FIELD_CAPABILITY`` is what the *export format* can
   carry. Whether this code actually replayed a year is a separate flag
   (``history.state`` = ``unresolved``). A field labelled ``exact`` never means "we have
   replayed it and you can browse it".
2. **Part hashes are computed, not asserted.** The sums come from the parser hashing the
   decoded part bytes itself. A client-supplied ``sum`` is never trusted.
3. **A base year with no replay is a draft.** Until replay exists, a basis stays
   ``unresolved`` and must not be presented as a runnable historical background.

Immutability: identity is ``(world, branch, base_year, content_sha256)``. ``save`` runs
inside one IMMEDIATE transaction, and refuses to overwrite an existing identity whose
content digest differs — changed metadata is not a silent overwrite.
"""
import hashlib
import json
from datetime import datetime, timezone

#: What a field's value at the chosen base year is backed by *by the export format*.
EXACT = 'exact'                  # the export records it per year
INTERVAL = 'as_of_interval'      # bounded by start/end years recorded in the export
UNKNOWN = 'unknown'              # the export does not carry it

#: Per-field capability, read from ``src/gen/civ/types.ts`` at ``SPEC_COMMIT``.
#: This is a statement about the *format*, not about what this code implements.
FIELD_CAPABILITY = {
    'region_culture': INTERVAL,       # log/checkpoints record when a region changed
    'region_polity': INTERVAL,
    'annals': EXACT,                  # each event carries its own year
    'polity_founded': EXACT,
    'polity_capital_spans': INTERVAL,
    'settlement_lifespan': INTERVAL,  # created..ended
    'settlement_capital_spans': INTERVAL,
    'people_lifespan': INTERVAL,
    'religion_events': INTERVAL,
    'population': UNKNOWN,            # no yearly series in the export
    'resources': UNKNOWN,             # region-level 0-3 tier, not a yearly series
    'routes': UNKNOWN,
    'terrain': UNKNOWN,               # terrain only changes via eras
}

#: What this code has actually implemented. All False: capability ≠ implementation.
REPLAY_IMPLEMENTED = {field: False for field in FIELD_CAPABILITY}

SPEC_COMMIT = '0939c5f1622a5e45cfc6f645ea3845993ab3985'
SCHEMA = 1

#: ``unresolved`` = the year is recorded but history was never replayed.
STATE_UNRESOLVED = 'unresolved'
STATE_REPLAYED = 'replayed'

_MAX_TEXT = 200


def _text(value, label, limit=_MAX_TEXT):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError('%s 必须是字符串' % label)
    value = value.strip()
    if len(value) > limit:
        raise ValueError('%s 过长（上限 %d 字符）' % (label, limit))
    return value


def _year(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError('base_year 必须是整数')
    if not 0 <= value <= 200000:
        raise ValueError('base_year 必须在 0…200000 之间')
    return value


def _hex64(value, label):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError('%s 必须是 64 位十六进制' % label)
    try:
        int(value, 16)
    except ValueError:
        raise ValueError('%s 必须是十六进制' % label)
    return value.lower()


def _history_year(value):
    """The base year of a **replayed** basis: a finite, non-bool number.

    ``build()`` keeps its original integer-only contract for the pinned-metadata path
    (old callers and old tests). A basis built from a real replay uses this instead, because
    the export's own years are fractional (``511.9765625``): truncating one would move an
    entity across its founding boundary.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('base_year 必须是数字')
    if isinstance(value, float) and not (value == value and abs(value) != float('inf')):
        raise ValueError('base_year 必须是有限数')
    if not -200000 <= value <= 200000:
        raise ValueError('base_year 必须在 -200000…200000 之间')
    return value


def capability_matrix():
    """Format capability per field (a copy)."""
    return dict(FIELD_CAPABILITY)


def field_status():
    """Per-field status after combining format capability with what is implemented.

    Until replay exists every non-UNKNOWN capability collapses to ``unknown``: the
    format could carry it, this code cannot produce it.
    """
    out = {}
    for field, capability in FIELD_CAPABILITY.items():
        if capability == UNKNOWN:
            out[field] = UNKNOWN
        else:
            out[field] = EXACT if REPLAY_IMPLEMENTED.get(field) else UNKNOWN
    return out


def build(record, *, base_year, branch=None, selected_world_id=None,
          declared_commit=None, spec_commit=None, allow_fractional_year=False):
    """Assemble a world-basis document from an import record and the author's selection.

    Everything comes from the parsed record (whose part sums the parser computed) plus
    the author's explicit choices. Nothing here re-reads the large file, and nothing here
    claims history was replayed.

    ``base_year`` is an integer by default — that is the pinned-metadata contract this
    function has always had. ``allow_fractional_year=True`` is used by
    :func:`build_from_history` only, where the year comes from a real replay whose own
    years are fractional.
    """
    source = record.get('source') or {}
    year = _history_year(base_year) if allow_fractional_year else _year(base_year)
    name = _text(branch, 'branch') or 'unknown'

    parts = []
    for part in (record.get('parts') or []):
        parts.append({
            'name': _text(part.get('name'), 'part.name', 64),
            'sum': _hex64(part.get('sum'), 'part.sum'),
            'sum_verified_by': part.get('sum_verified_by'),
            'bytes': part.get('bytes'),
            'zip': part.get('zip'),
        })

    basis = {
        'schema': SCHEMA,
        'kind': 'world_basis',
        'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'world': {
            'source_world_id': _text(selected_world_id or source.get('world_id'),
                                     'world id', 64) or None,
            'generator': source.get('generator_version'),
            'snapshot_format': source.get('snapshot_format'),
            'recipe': _text(source.get('recipe'), 'recipe', 64) or None,
            'import_id': _text(record.get('id'), 'import id', 64) or None,
            # 上游 .civsnap 只带 recipe 指纹，没有明文种子；缺失写 None，不猜。
            'terrain_seed': None,
            'civ_seed': None,
            'seed_note': ('上游 .civsnap 只带 recipe 指纹，不含明文种子；'
                          '需另行从存档 params.seed / edits.civSeed 只读配对才能填'),
        },
        'source': {
            'repo': 'https://github.com/guaner-334/civ-atlas',
            'declared_commit': _text(declared_commit or source.get('commit'), 'commit', 40) or None,
            'spec_commit': _text(spec_commit or source.get('spec_commit'), 'spec commit', 40) or None,
            'content_sha256': _hex64(record.get('sha256'), 'content_sha256'),
            'bytes': record.get('bytes'),
            # 服务端真算的 part sum（解析时算的），客户端填的不被采信
            'parts': parts,
            'extractor': _text(source.get('extractor'), 'extractor'),
            'exported_at': _text(source.get('exported_at'), 'exported_at', 40) or None,
            'license_note': ('上游代码 AGPL-3.0-only；用它生成的世界数据归作者；'
                             '本记录只是引用与溯源，不主张版权'),
        },
        'selection': {
            'branch': name,
            'base_year': year,
            'branch_known': name != 'unknown',
        },
        # 格式能带什么（capability）与本工程回放过没有（history）分开写
        'capability': capability_matrix(),
        'history': {
            'state': STATE_UNRESOLVED,
            'replayed_fields': sorted(f for f, done in REPLAY_IMPLEMENTED.items() if done),
            'not_replayed_fields': sorted(f for f, done in REPLAY_IMPLEMENTED.items() if not done),
            'note': ('本记录只固定了来源与选年；历史尚未回放，'
                     '因此不能当作可运行的历史背景'),
        },
        'field_status': field_status(),
        'restorable': sorted(f for f, s in field_status().items() if s != UNKNOWN),
        'not_restorable': sorted(f for f, s in field_status().items() if s == UNKNOWN),
        'limits': [
            'capability 说的是导出格式能带什么，不代表本工程已经回放',
            'annals 按年过滤得到的是「事件清单」，不等于「那一年的完整状态」',
            'population / resources / routes 没有逐年序列',
            '早于首个 checkpoint 或超过 endYear 的年份无法回放（本版尚未实现回放）',
        ],
    }
    basis['id'] = basis_id(basis)
    basis['digest'] = digest_of(basis)
    return basis


# ======================================================== basis from a replay
def build_from_history(record, document, *, base_year, branch=None,
                       selected_world_id=None, declared_commit=None,
                       spec_commit=None):
    """A world basis whose ``history`` really was replayed, from ``civ_atlas_history``.

    This is the *only* path that fills ``STATE_REPLAYED``. It takes the same import record as
    :func:`build` **and** the document :func:`app.civ_atlas_history.build` produced for the
    same year/branch, and it takes every field status from that document instead of
    re-deriving anything. Two deliberate differences from :func:`build`:

    * ``base_year`` may be fractional (the export's own years are);
    * ``world.civ_seed`` is filled from the replay's ``identity`` with an explicit
      ``civ_seed_source`` — the real ``civ.seed`` the export carries, never a caller guess
      and never derived from the recipe fingerprint.

    A document that was replayed for a *different* year, branch or source is refused: the
    basis must describe exactly the replay it points at.
    """
    if not isinstance(document, dict):
        raise ValueError('历史回放文档不是对象')
    selection = document.get('selection') or {}
    identity = document.get('identity') or {}
    year = _history_year(base_year)
    if selection.get('base_year') != year:
        raise ValueError('回放文档的基准年（%r）与要固定的基准年（%r）不一致'
                         % (selection.get('base_year'), year))
    name = _text(branch, 'branch') or 'unknown'
    doc_branch = identity.get('branch')
    if doc_branch is not None and doc_branch != name:
        raise ValueError('回放文档的分支（%r）与要固定的分支（%r）不一致'
                         % (doc_branch, name))
    record_sha = record.get('sha256')
    pinned_sha = identity.get('content_sha256')
    if pinned_sha and record_sha and pinned_sha != record_sha:
        raise ValueError('回放文档的来源哈希与导入记录不一致，拒绝固定')

    basis = build(record, base_year=int(year) if float(year).is_integer() else year,
                  branch=branch, selected_world_id=selected_world_id,
                  declared_commit=declared_commit, spec_commit=spec_commit,
                  allow_fractional_year=True)
    statuses = document.get('field_status') or {}
    replayed = sorted(field for field, row in statuses.items()
                      if isinstance(row, dict) and row.get('status') != UNKNOWN)
    known_seed = identity.get('civ_seed')
    seed_source = identity.get('civ_seed_source')
    basis['world']['civ_seed'] = known_seed if isinstance(known_seed, int) else None
    basis['world']['civ_seed_source'] = seed_source if basis['world']['civ_seed'] is not None else None
    basis['selection']['base_year'] = year
    basis['history'] = {
        'state': STATE_REPLAYED if replayed else STATE_UNRESOLVED,
        'replayed_fields': replayed,
        'not_replayed_fields': sorted(set(FIELD_CAPABILITY) - set(replayed)),
        'reader': (document.get('provenance') or {}).get('reader'),
        'spec_commit': (document.get('provenance') or {}).get('spec_commit'),
        'data_shape': document.get('data_shape'),
        'terrain': document.get('terrain'),
        'note': ('本记录的选年已按导出数据真实回放（检查点 + 变化日志，并对 endYear 自检）；'
                 '回放结果只是作者侧候选，不自动正典'),
    }
    basis['field_status'] = {field: (statuses.get(field) or {}).get('status', UNKNOWN)
                             if isinstance(statuses.get(field), dict)
                             else UNKNOWN
                             for field in FIELD_CAPABILITY}
    basis['restorable'] = sorted(f for f, s in basis['field_status'].items() if s != UNKNOWN)
    basis['not_restorable'] = sorted(f for f, s in basis['field_status'].items()
                                     if s == UNKNOWN)
    basis['limits'] = [
        'capability 说的是导出格式能带什么；field_status 才是这次真回放出来的支持度',
        'annals 按年筛选得到的是事件清单，不等于那一年的完整状态',
        'population / resources / routes 没有逐年序列，永远是 unknown',
        '早于首个检查点的年份报 unknown；晚于 endYear 的年份直接拒收',
        '地形只在 upheaval 变；基准年早于最后一件大事时地图标 unmatched，不冒称复原',
    ]
    basis['id'] = basis_id(basis)
    basis['digest'] = digest_of(basis)
    return basis


def basis_id(basis):
    """Identity = world + branch + year + source hash. Metadata differences keep the id."""
    payload = '%s|%s|%s|%s' % (
        (basis.get('world') or {}).get('source_world_id') or '',
        (basis.get('selection') or {}).get('branch') or 'unknown',
        (basis.get('selection') or {}).get('base_year') or 0,
        (basis.get('source') or {}).get('content_sha256') or '',
    )
    return 'wb_' + hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def digest_of(basis):
    """Content digest over everything except ``id``/``digest``/``created``.

    ``created`` is excluded so rebuilding the same selection gives the same digest; a
    genuine content change (different part sums, different history state) changes it.
    """
    body = {k: v for k, v in basis.items() if k not in ('id', 'digest', 'created')}
    blob = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def save(store, basis):
    """Persist one basis, immutably, inside a single transaction.

    * the record's own ``digest``/``id`` must match its payload (forged records refused);
    * an existing identity with the **same** digest is returned unchanged (idempotent);
    * an existing identity with a **different** digest is refused — same world/branch/year
      means the same thing, so changed content needs an explicit new year.
    """
    if basis.get('digest') != digest_of(basis):
        raise ValueError('世界基础内容与其 digest 不一致，拒绝保存')
    if basis.get('id') != basis_id(basis):
        raise ValueError('世界基础 id 与其身份字段不一致，拒绝保存')
    with store.transact() as db:
        row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                         ('world_basis', basis['id'])).fetchone()
        if row:
            existing = json.loads(row[0])
            if existing.get('digest') != basis['digest']:
                raise ValueError(
                    '同一世界/分支/年份/源哈希已有内容不同的世界基础（%s），拒绝覆盖；'
                    '要改内容请换一个年份或换一个分支' % basis['id'])
            return {'basis': existing, 'created': False}
        db.execute('INSERT INTO documents(kind,id,body) VALUES(?,?,?)',
                   ('world_basis', basis['id'],
                    json.dumps(basis, ensure_ascii=False, sort_keys=True)))
    return {'basis': basis, 'created': True}


def get(store, identifier):
    if not isinstance(identifier, str) or not identifier.startswith('wb_'):
        raise ValueError('世界基础编号格式不对')
    row = store.get('world_basis', identifier)
    if not row:
        raise ValueError('找不到这个世界基础')
    return row


def list_all(store):
    return sorted(store.all('world_basis'),
                  key=lambda row: (row.get('created') or '', row.get('id') or ''))


def refuse_stale(store, basis, record):
    """Refuse to attach a basis to an import whose bytes (or part sums) changed."""
    pinned = ((basis.get('source') or {}).get('content_sha256') or '')
    actual = record.get('sha256') or ''
    if pinned != actual:
        raise ValueError('世界基础与导入内容哈希不一致（基础 %s… ≠ 导入 %s…），拒绝关联'
                         % (pinned[:12], actual[:12]))
    pinned_parts = {p.get('name'): p.get('sum')
                    for p in ((basis.get('source') or {}).get('parts') or [])}
    for part in (record.get('parts') or []):
        name = part.get('name')
        if name in pinned_parts and pinned_parts[name] != part.get('sum'):
            raise ValueError('世界基础里 part %s 的哈希与导入记录不符，拒绝关联' % name)
    return True


def dumps(basis):
    return json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
