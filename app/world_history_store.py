# -*- coding: utf-8 -*-
"""History adoption: a replay preview, an author decision, and an immutable snapshot.

What this layer adds on top of :mod:`app.civ_atlas_history`
----------------------------------------------------------
``civ_atlas_history`` answers "what can I honestly say about year Y". This module answers
"did the author accept it, what did they choose to reveal, and where is that now pinned".

Three documents in the existing ``Store`` namespace (no second database, no migration):

* ``history_preview`` — a **short-lived author-side draft**: the bounded replay document for
  one (import, world, branch, year), plus what the author selected from it. Never read by a
  journey.
* ``history_snapshot`` — immutable, content-addressed by its own digest. Self-contained: it
  carries the bounded candidates, the source pin (content hash + per-part sums + generator),
  the world basis it belongs to, and the author's disclosure choice. A journey reads this
  and nothing else, so deleting the original ``.civsnap`` later does not break it.
* ``history_adoption`` — immutable record that a snapshot was adopted by one story-package
  revision. Its key includes the story identity and the revision, so a retry is a no-op and
  the same snapshot may legitimately be adopted by two packages.

Three deliberate boundaries
--------------------------
1. **A preview never changes a story or a session.** Preview only writes its own draft row.
2. **Full history never goes into a prompt.** The snapshot is bounded by the same budgets as
   the replay (events / entities), and beyond that it is explicitly *paged*: ``page``
   returns one slice and says how many pages there are, instead of silently truncating.
3. **Disclosure is per item, not per category.** ``public_view`` here takes explicit entry
   refs; authorizing "polities" does not reveal every polity, and nothing marked
   ``known_by``-restricted or unrevealed reaches a player.

What this module does NOT do: it does not read the map file itself (the caller hands in an
already-validated import record), it does not mint coordinates, it does not touch
``mechanics.map``, and it does not run any upstream code.
"""
import copy
import hashlib
import json

from . import civ_atlas_history
from . import map_import as _map_import
from . import world_basis

#: ``map_import.import_dir`` bound once: this module must look where the importer writes.
map_import_import_dir = _map_import.import_dir

#: kind names in the shared ``documents`` table
PREVIEW_KIND = 'history_preview'
SNAPSHOT_KIND = 'history_snapshot'
ADOPTION_KIND = 'history_adoption'

#: ``story.mechanics`` key the adoption writes into.
MECHANICS_KEY = 'history'

#: How many candidates one snapshot may carry before it must be paged.
DEFAULT_MAX_ENTRIES = 200
MAX_ENTRIES = 2000
#: Hard ceiling on the preview document's own size, so one call cannot bloat the store.
MAX_PREVIEW_JSON = 4 * 1024 * 1024

#: What a player may see of one history entry. Per-entry, explicit, and never the future.
PUBLIC_ENTRY_FIELDS = {
    'annals': ('ref', 'year', 'kind', 'a_ref', 'b_ref', 'region', 'settlement_ref'),
    'polities': ('ref', 'display_name', 'founded'),
    'settlements': ('ref', 'display_name', 'founded', 'region', 'location_id'),
    'people': ('ref', 'display_name', 'role'),
}

#: Categories a preview can carry; also the keys ``public_view`` understands.
CATEGORIES = tuple(PUBLIC_ENTRY_FIELDS)

#: Outcome of one preview call.
STATUS_DRAFT = 'draft'
#: A base year the replay refuses (after endYear, before the first checkpoint...).
STATUS_UNSUPPORTED_YEAR = 'unsupported_year'
STATUS_SOURCE_MISMATCH = 'source_mismatch'

MECHANICS_SCHEMA = 1


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class HistoryError(ValueError):
    """A refused history operation. Never leaves a half-written document behind."""


# ======================================================================= utilities
def content_hash(snapshot):
    """Digest over the snapshot's own body (identity fields excluded)."""
    body = {key: value for key, value in snapshot.items()
            if key not in ('id', 'digest', 'created')}
    return _digest(body)


def _part_pins(record):
    """The per-part sums the server computed at import time, carried into the snapshot.

    Only ``sum_verified_by == 'server'`` entries are verified; a client-supplied sum is
    carried with its honest ``sum_verified_by`` (usually ``None``) rather than promoted.
    """
    pins = []
    for part in record.get('parts') or ():
        if not isinstance(part, dict):
            continue
        pins.append({'name': part.get('name'), 'sum': part.get('sum'),
                     'sum_verified_by': part.get('sum_verified_by'),
                     'bytes': part.get('bytes'), 'zip': part.get('zip')})
    return pins


def _terrain_from_parts(parts):
    """The minimum terrain association the ``eras`` block carries.

    The ``eras`` part is ``{'baseKey': …, 'eras': [{until, habitat, regions, places,
    routes}, …]}`` (~``src/gen/snapshot.ts:634``). Those segments are *terrain versions*, not
    history, and this reader does not need their arrays: it needs to know **whether the map
    we hold is that year's map**. So only the segment end years are extracted, and a block
    with no segment (our real export: ``eras: []``) means "no terrain event at all".

    Returns ``{'eras_block': bool, 'era_until': [...], 'upheaval_years': []}``. A part that
    is missing or undecodable returns an empty association rather than a guess, which makes
    the replay report terrain ``unknown``/``unmatched`` instead of ``matched``.
    """
    from . import civ_atlas_snapshot as _snap
    terrain = {'eras_block': False, 'era_until': [], 'upheaval_years': []}
    meta = None
    for part in parts or ():
        if isinstance(part, dict) and part.get('name') == 'eras':
            meta = part
            break
    if meta is None:
        return terrain
    blob = meta.get('_bytes')
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return terrain
    blob = bytes(blob)
    try:
        if blob[:len(_snap.PART_MAGIC)] != _snap.PART_MAGIC:
            if meta.get('zip') != 'gzip':
                return terrain
            blob = _snap._inflate(blob)
        decoded = _snap.parse_part(blob, 'eras')
    except ValueError:
        return terrain
    if not isinstance(decoded, dict):
        return terrain
    segments = decoded.get('eras')
    if not isinstance(segments, list):
        return terrain
    for entry in segments:
        if isinstance(entry, dict) and isinstance(entry.get('until'), (int, float)) \
                and not isinstance(entry.get('until'), bool):
            terrain['era_until'].append(entry['until'])
    # ``eras_block`` means "there really are earlier terrain segments", not "the key
    # exists": a real export of a world with no terrain event carries ``eras: []``, and
    # calling that "an era block" would mark every year's map as unmatched.
    terrain['eras_block'] = bool(terrain['era_until'])
    return terrain


def _entries_of(story):
    """The history entries a story revision carries (``mechanics.history.entries``)."""
    mechanics = (story or {}).get('mechanics') or {}
    block = mechanics.get(MECHANICS_KEY)
    if not isinstance(block, dict):
        return []
    entries = block.get('entries')
    return entries if isinstance(entries, list) else []


# ================================================================== preview drafts
class WorldHistoryService:
    """Author-side history adoption, on top of a ``Runtime``.

    ``runtime`` is the existing story-package runtime; this service only uses its
    ``store``, ``package()`` and ``commit_package()``. ``load_civ`` is injected so a test can
    hand in a decoded block instead of a real file, and the default reads the stored
    ``.civsnap`` through ``civ_atlas_snapshot`` (the one path that touches bytes).
    """

    def __init__(self, runtime, load_civ=None):
        self.runtime = runtime
        self.store = runtime.store
        self._load_civ = load_civ

    # ------------------------------------------------------------------ internals
    def _read_civ(self, record):
        """Decode the ``civ`` block of an already-registered import record.

        The record's file is the only file ever opened, looked up with exactly the rule the
        import side uses (``map_import.import_dir`` on ``store.path.parent`` — the same root
        ``web._import_root()`` passes when it *writes* the file), and its bytes are re-hashed
        before decoding so a swapped file cannot masquerade as the pinned source.

        Returns ``(civ, terrain)`` where ``terrain`` is the minimum the replay needs to say
        whether the held map is that year's map — the ``eras`` block's segment years, not a
        second copy of any world arrays.
        """
        if self._load_civ is not None:
            return self._load_civ(record)
        from . import civ_atlas_snapshot
        path = map_import_import_dir(self._data_root()) / record['file']
        if not path.exists():
            raise HistoryError('导入的原件已不在（%s），无法回放历史' % record['file'])
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get('sha256'):
            raise HistoryError('导入原件的哈希与记录不符，拒绝回放')
        try:
            manifest, parts = civ_atlas_snapshot.parse_container(data)
            record_terrain = _terrain_from_parts(parts)
            return civ_atlas_history.decode_civ_part(manifest, parts), record_terrain
        except ValueError as error:
            raise HistoryError('历史那块读不出来：%s' % error)

    def _story_pin(self, start_key=None):
        """回放草稿钉在哪个故事身份上：(``story_id``, ``base_revision``)。

        有故事包时：用当前包的真实身份（旧行为）。
        没有故事（空世界）时：只能用调用方显式给的开局草稿键——没有这个键就直接拒，
        绝不把无绑定的回放默认采纳到以后某个故事里。
        """
        if self.runtime.has_world():
            current = self.runtime.package()
            story_id = current['story'].get('id')
            if not isinstance(story_id, str) or not story_id:
                raise HistoryError('当前故事包没有身份，无法固定回放草稿')
            return story_id, current['id']
        if not isinstance(start_key, str) or not start_key:
            raise HistoryError('还没有故事包：请先在开局草稿里选定世界与年份，再回放历史'
                               '（不会把未绑定的回放默认采纳到之后的故事）')
        return 'start:' + start_key, None

    def _data_root(self):
        """The data root imported payloads live under — ``store.path.parent``, always.

        Identical to ``web._import_root()``, which is where :func:`map_import.create_import`
        actually *wrote* the file when it was imported. Deriving this from the runtime's
        package library instead would look in a directory the importer never writes to.
        """
        return self.store.path.resolve().parent

    def _identity_of(self, record, branch):
        return {'content_sha256': record.get('sha256'),
                'world_id': (record.get('source') or {}).get('world_id'),
                'import_id': record.get('id'),
                'branch': branch,
                'generator': (record.get('source') or {}).get('generator_version'),
                'snapshot_format': (record.get('source') or {}).get('snapshot_format')}

    # -------------------------------------------------------------------- preview
    def preview(self, record, *, base_year, branch=None, window=None,
                max_events=None, max_entities=None, start_key=None):
        """Replay one (import, year, branch) into an author-side draft.

        Writes exactly one ``history_preview`` row and nothing else: no story revision, no
        session, no ``mechanics.map`` change. The same request key returns the existing
        draft instead of minting a second one.
        """
        if not isinstance(record, dict) or not record.get('id'):
            raise HistoryError('需要一条已登记的导入记录')
        if not (record.get('sha256') or ''):
            raise HistoryError('导入记录没有内容哈希，无法回放历史')
        year = world_basis._history_year(base_year)
        limit_events = civ_atlas_history.DEFAULT_MAX_EVENTS if max_events is None else max_events
        limit_entities = (civ_atlas_history.DEFAULT_MAX_ENTITIES
                          if max_entities is None else max_entities)
        if not isinstance(limit_events, int) or limit_events <= 0:
            raise HistoryError('max_events 必须是正整数')
        if not isinstance(limit_entities, int) or limit_entities <= 0:
            raise HistoryError('max_entities 必须是正整数')

        civ, terrain = self._read_civ(record)
        identity = self._identity_of(record, branch)
        try:
            document = civ_atlas_history.build(civ, base_year=year, window=window,
                                              identity=identity, terrain=terrain,
                                              max_events=limit_events,
                                              max_entities=limit_entities)
        except ValueError as error:
            # A year the replay refuses (after endYear, before the first checkpoint...) is a
            # caller error, not a crash: surface it as this layer's own refusal.
            raise HistoryError(str(error))
        # A preview is pinned to the story package it was started from. Without this, a
        # draft begun against world A could be adopted into world B just because the caller
        # knows B's current revision id. The identity is part of the preview key, so two
        # worlds never share one draft.
        # 空世界：没有故事包就没有故事身份可钉。草稿改为钉在**开局草稿**上（由
        # ``native_starts`` 传进来的 ``start_key``），这样它仍然不会漂流到之后某个故事；
        # 有故事时行为与以前完全一样。
        story_id, base_revision = self._story_pin(start_key)
        preview_id = 'hp_' + _digest({'story': story_id,
                                      'import': record['id'], 'sha': record.get('sha256'),
                                      'branch': branch, 'year': year,
                                      'window': window, 'events': limit_events,
                                      'entities': limit_entities})[:16]
        existing = self.store.get(PREVIEW_KIND, preview_id)
        if existing is not None:
            return {'preview': existing, 'reused': True, 'document': None}
        draft = {
            'id': preview_id,
            'created': _now(),
            'status': STATUS_DRAFT,
            'revision': 0,
            'base_story_id': story_id,
            'base_story_revision': base_revision,
            'import_id': record['id'],
            'source_sha256': record.get('sha256'),
            'source': record.get('source') or {},
            'parts': _part_pins(record),
            'branch': branch,
            'base_year': year,
            'window': document['selection']['window'],
            'limits': {'max_events': limit_events, 'max_entities': limit_entities},
            'document': document,
            'reviewed': False,
            'terrain': document.get('terrain'),
            'note': ('这是作者侧回放草稿：不改故事包、不改会话、不进玩家侧；'
                     '审阅后才可固定成快照；定在本故事包（%s）上' % story_id),
        }
        blob = _canonical(draft)
        if len(blob.encode('utf-8')) > MAX_PREVIEW_JSON:
            raise HistoryError('回放草稿超过 %d 字节上限；请缩短年窗或调小预算'
                               % MAX_PREVIEW_JSON)
        self.store.put(PREVIEW_KIND, preview_id, draft)
        return {'preview': draft, 'reused': False, 'document': document}

    def get_preview(self, preview_id):
        if not isinstance(preview_id, str) or not preview_id.startswith('hp_'):
            raise HistoryError('回放草稿编号格式不对')
        draft = self.store.get(PREVIEW_KIND, preview_id)
        if draft is None:
            raise HistoryError('找不到这个回放草稿')
        return draft

    def page(self, preview_id, category, page=0, size=25):
        """One slice of one category, plus how many pages there really are.

        Full history never goes into a prompt. When a category has more entries than
        ``size``, this is how the author walks it — the total stays exact, nothing is
        silently dropped.
        """
        if category not in CATEGORIES:
            raise HistoryError('不认识的历史类别：%r' % (category,))
        if not isinstance(page, int) or page < 0:
            raise HistoryError('page 必须是非负整数')
        if not isinstance(size, int) or size <= 0:
            raise HistoryError('size 必须是正整数')
        draft = self.get_preview(preview_id)
        document = draft['document']
        items, total = _category_items(document, category)
        pages = max(1, (total + size - 1) // size)
        if page >= pages:
            raise HistoryError('第 %d 页不存在（共 %d 页）' % (page, pages))
        start = page * size
        return {'category': category, 'page': page, 'pages': pages, 'size': size,
                'total': total, 'items': items[start:start + size],
                'truncated_by_page': total > size}

    def review(self, preview_id, *, entries, disclosure=None, local_links=None,
               max_entries=None, expected_revision=None):
        """Record what the author selected from a preview: an author decision.

        ``entries`` is an explicit list of ``{category, ref, ...}`` picks. Marking a
        preview reviewed does not touch a story package; :meth:`commit` does that.
        ``local_links`` maps a civ settlement ref to an existing local location id — the
        author's explicit association, never a coordinate the server invents.

        ``expected_revision`` is a compare-and-swap on the *draft*: two author tabs that both
        read revision N cannot both write a selection, so one tab's picks are never silently
        overwritten by another's. The same holds for the package: the draft is pinned to the
        story revision it was previewed against, and a review after the story moved is refused
        rather than quietly rebased.
        """
        draft = self.get_preview(preview_id)
        if draft['status'] != STATUS_DRAFT:
            raise HistoryError('这份回放草稿已审阅过；请重新回放一次')
        if expected_revision is not None and expected_revision != draft.get('revision', 0):
            raise HistoryError('回放草稿已被其他操作更新（当前版本 %s，提交版本 %s），'
                               '请刷新后重试'
                               % (draft.get('revision', 0), expected_revision))
        # 有故事时：当前包必须就是草稿钉的那个（旧行为）。
        # 空态：草稿钉的是开局草稿键，没有当前包可比——也不去比，只要它确实是
        # 开局身份（``start:`` 前缀），不会被当成某个真实故事包。
        if self.runtime.has_world():
            current = self.runtime.package()
            if current['story'].get('id') != draft.get('base_story_id'):
                raise HistoryError('当前故事包（%s）与回放草稿固定的故事包（%s）不同；'
                                   '请对目标世界重新回放，不会静默改成新世界'
                                   % (current['story'].get('id'), draft.get('base_story_id')))
        elif not str(draft.get('base_story_id') or '').startswith('start:'):
            raise HistoryError('这份回放草稿不属于空世界开局；请先选定世界与年份重新回放')
        limit = DEFAULT_MAX_ENTRIES if max_entries is None else max_entries
        if not isinstance(limit, int) or limit <= 0 or limit > MAX_ENTRIES:
            raise HistoryError('max_entries 必须在 1…%d 之间' % MAX_ENTRIES)
        picked = _normalise_entries(draft['document'], entries, limit)
        share = _normalise_disclosure(disclosure, picked)
        links = _normalise_links(local_links, draft['document'])
        updated = copy.deepcopy(draft)
        updated['status'] = 'reviewed'
        updated['reviewed'] = True
        updated['reviewed_at'] = _now()
        updated['revision'] = int(draft.get('revision', 0)) + 1
        updated['selection'] = {'entries': picked, 'disclosure': share,
                                'local_links': links}
        updated['counts'] = {'selected': len(picked),
                             'public': len(share['public_refs']),
                             'linked': len(links)}
        self._swap_preview(preview_id, int(draft.get('revision', 0)), updated)
        return updated

    def _swap_preview(self, preview_id, expected, updated):
        """Write the draft only if it is still at ``expected``, inside one transaction.

        The CAS is re-evaluated against the row as it exists *inside* the write lock, so a
        concurrent writer that saved between our read and our write makes this fail with no
        side effects instead of overwriting that writer's selection.
        """
        with self.store.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                             (PREVIEW_KIND, preview_id)).fetchone()
            if row is None:
                raise HistoryError('找不到这个回放草稿')
            latest = json.loads(row[0])
            if int(latest.get('revision', 0)) != expected:
                raise HistoryError('回放草稿已被其他操作更新（当前版本 %s，提交版本 %s），'
                                   '请刷新后重试'
                                   % (latest.get('revision', 0), expected))
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                       (PREVIEW_KIND, preview_id, _canonical(updated)))

    # --------------------------------------------------------------------- commit
    def commit(self, preview_id, what_changed='', max_entries=None,
               expected_revision=None):
        """reviewed preview → immutable ``history_snapshot`` (author approved).

        The result is self-contained: bounded candidates + source pin + basis id +
        disclosure + the story identity the author was looking at. ``expected_revision``
        pins the exact reviewed draft, so a review that changed between read and commit
        cannot be fixed by accident.
        """
        draft = self.get_preview(preview_id)
        if draft['status'] != 'reviewed':
            raise HistoryError('回放草稿还没审阅，不能固定成历史快照')
        if expected_revision is not None \
                and expected_revision != draft.get('revision', 0):
            raise HistoryError('回放草稿已被其他操作更新（当前版本 %s，提交版本 %s），'
                               '请刷新后重试'
                               % (draft.get('revision', 0), expected_revision))
        selection = draft.get('selection') or {}
        limit = DEFAULT_MAX_ENTRIES if max_entries is None else max_entries
        if not isinstance(limit, int) or limit <= 0 or limit > MAX_ENTRIES:
            raise HistoryError('max_entries 必须在 1…%d 之间' % MAX_ENTRIES)
        picked = selection['entries']
        if len(picked) > limit:
            raise HistoryError('选中的历史条目 %d 条超过上限 %d；请分页选取'
                               % (len(picked), limit))
        basis = world_basis.build_from_history(
            {'sha256': draft['source_sha256'], 'id': draft['import_id'],
             'source': draft.get('source') or {}, 'parts': draft.get('parts') or []},
            draft['document'], base_year=draft['base_year'], branch=draft['branch'])
        body = {
            'schema': MECHANICS_SCHEMA,
            'kind': 'civ_atlas_history_snapshot',
            'created': _now(),
            'import_id': draft['import_id'],
            'preview_id': preview_id,
            'branch': draft['branch'],
            'base_year': draft['base_year'],
            'window': draft['window'],
            'story': {'story_id': draft.get('base_story_id'),
                      'base_story_revision': draft.get('base_story_revision'),
                      'reviewed_revision': draft.get('revision')},
            'world_basis': {'id': basis['id'], 'digest': basis['digest'],
                            'world_id': basis['world']['source_world_id'],
                            'civ_seed': basis['world']['civ_seed'],
                            'civ_seed_source': basis['world'].get('civ_seed_source')},
            'source': {'content_sha256': draft['source_sha256'],
                       'spec_commit': (draft['document'].get('provenance') or {})
                       .get('spec_commit'),
                       'reader': (draft['document'].get('provenance') or {}).get('reader'),
                       'parts': draft.get('parts') or []},
            'field_status': draft['document']['field_status'],
            'terrain': draft['document']['terrain'],
            'entries': picked,
            'disclosure': selection['disclosure'],
            'local_links': selection['local_links'],
            'counts': dict(draft.get('counts') or {}),
            'what_changed': str(what_changed or '')[:400],
            'for_author_review': True,
            'auto_canonical': False,
            'note': ('这份快照是作者批准的历史背景；不自带地图底图数据，'
                     '也不把未披露的条目交给玩家'),
        }
        digest = content_hash(body)
        snapshot_id = 'hs_' + digest[:16]
        stored = self.store.get(SNAPSHOT_KIND, snapshot_id)
        if stored is not None:
            return {'snapshot': stored, 'created': False,
                    'world_basis': basis, 'reused': True}
        body['id'] = snapshot_id
        body['digest'] = digest
        self.store.put(SNAPSHOT_KIND, snapshot_id, body)
        return {'snapshot': body, 'created': True, 'world_basis': basis,
                'reused': False}

    def get_snapshot(self, snapshot_id):
        if not isinstance(snapshot_id, str) or not snapshot_id.startswith('hs_'):
            raise HistoryError('历史快照编号格式不对')
        snapshot = self.store.get(SNAPSHOT_KIND, snapshot_id)
        if snapshot is None:
            raise HistoryError('找不到这份历史快照')
        return snapshot

    # ---------------------------------------------------------------------- adopt
    def adopt(self, snapshot_id, expected_story_revision, note=''):
        """Bind a snapshot into a NEW story-package revision at ``mechanics.history``.

        Order: read and verify the snapshot → look at the pinned revision → if it already
        carries this snapshot, finish the index only (a retry is not a second revision) →
        refuse a stale submission → commit the package → record the adoption.

        A commit whose package landed but whose index row did not is repaired by the next
        identical call, because the marker lives in the package itself.
        """
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot.get('digest') != content_hash(snapshot):
            raise HistoryError('历史快照内容与其 digest 不符，拒绝采纳')
        runtime = self.runtime
        runtime.reload_documents()
        current = runtime.package()
        story_id = current['story']['id']
        frozen = snapshot.get('story') or {}
        frozen_story_id = frozen.get('story_id')
        if frozen_story_id and frozen_story_id != story_id:
            raise HistoryError('这份历史快照固定在故事包（%s）上，当前是（%s）；'
                               '不把旧世界的历史挂到新世界上，请对目标世界重新回放'
                               % (frozen_story_id, story_id))
        for entry in _entries_of(current['story']):
            if entry.get('snapshot_id') == snapshot_id:
                adoption = self._write_adoption(snapshot, story_id, current['id'], note)
                return {'revision': current['id'], 'snapshot_id': snapshot_id,
                        'adoption': adoption, 'reused': True,
                        'note': '该历史快照已在该故事包中，本次只补齐索引，未新建版本'}
        # The map/world association is checked before the revision, so a genuine
        # two-worlds mistake is reported as that instead of as a stale revision.
        _check_adoptable(current['story'], snapshot)
        if current['id'] != expected_story_revision:
            raise HistoryError('故事包已变化（当前 %s，本次基于 %s）；请刷新后重新选择，'
                               '不会把旧历史悄悄挂到新世界上'
                               % (current['id'], expected_story_revision))
        # The author must submit against the revision the snapshot was reviewed on; moving
        # forward to a *newer* revision is not an implicit rebase of an older decision.
        frozen_revision = frozen.get('base_story_revision')
        if frozen_revision and frozen_revision != expected_story_revision:
            raise HistoryError('这份历史快照是在故事包版本 %s 上审阅的，本次提交基于 %s；'
                               '请回到那个版本采纳，或对该版本重新回放'
                               % (frozen_revision, expected_story_revision))
        story = copy.deepcopy(current['story'])
        characters = copy.deepcopy(current['characters'])
        mechanics = story.setdefault('mechanics', {})
        block = mechanics.get(MECHANICS_KEY)
        if block is None:
            block = {'schema': MECHANICS_SCHEMA, 'entries': []}
            mechanics[MECHANICS_KEY] = block
        if not isinstance(block, dict) or not isinstance(block.get('entries'), list):
            raise HistoryError('故事包里的 history 配置结构无效，请先修正')
        entry = {'snapshot_id': snapshot_id, 'import_id': snapshot['import_id'],
                 'base_year': snapshot['base_year'], 'branch': snapshot['branch'],
                 'digest': snapshot['digest'], 'world_basis_id': snapshot['world_basis']['id'],
                 'content_sha256': snapshot['source']['content_sha256'],
                 'story_id': story_id,
                 'adopted_from_revision': current['id'], 'note': note,
                 'snapshot': snapshot}
        entries = [item for item in block['entries']
                   if item.get('snapshot_id') != snapshot_id]
        entries.append(entry)
        block['entries'] = entries
        # mechanics.map is deliberately untouched: adopting history must not silently move
        # the map source or the world the players are already standing in.
        revision = runtime.commit_package(story, characters,
                                         '采纳历史快照 ' + snapshot_id)
        adoption = self._write_adoption(snapshot, story_id, revision, note)
        return {'revision': revision, 'snapshot_id': snapshot_id,
                'adoption': adoption, 'reused': False, 'note': ''}

    def _write_adoption(self, snapshot, story_id, revision, note):
        adoption_id = ('ha_' + _digest({'story': story_id, 'revision': revision,
                                        'snapshot': snapshot['id']})[:16])
        adoption = {'id': adoption_id, 'created': _now(), 'snapshot_id': snapshot['id'],
                    'story_id': story_id, 'revision': revision,
                    'digest': snapshot['digest'], 'note': note}
        with self.store.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                             (ADOPTION_KIND, adoption_id)).fetchone()
            if row is None:
                db.execute('INSERT INTO documents VALUES(?,?,?)',
                           (ADOPTION_KIND, adoption_id, _canonical(adoption)))
            else:
                adoption = json.loads(row[0])
        return adoption

    def adoption_for(self, snapshot_id, story_id, revision=None):
        rows = [row for row in self.store.all(ADOPTION_KIND)
                if row['snapshot_id'] == snapshot_id and row['story_id'] == story_id
                and (revision is None or row['revision'] == revision)]
        return rows[-1] if rows else None

    # ------------------------------------------------------------- map binding
    def link_start_map(self, import_id, expected_story_revision, *, fog_radius_km=300.0,
                       note=''):
        """Author's explicit action: make this import the map this package starts on.

        This is deliberately a *separate* action from adopting history. Adopting history
        never writes ``mechanics.map``; this only runs when the author asks for it, and it
        refuses when the package already carries history from a different import (that
        would put two worlds in one package).

        ``expected_story_revision`` is the revision the author is looking at; a stale value
        is refused instead of being guessed into the current package.
        """
        if not isinstance(import_id, str) or not import_id:
            raise HistoryError('需要一份已导入的地图')
        runtime = self.runtime
        runtime.reload_documents()
        current = runtime.package()
        if current['id'] != expected_story_revision:
            raise HistoryError('故事包已变化（当前 %s，本次基于 %s）；请刷新后重试'
                               % (current['id'], expected_story_revision))
        record = self.store.get('map_import', import_id)
        if not record:
            raise HistoryError('找不到这个导入记录（%s）' % import_id)
        if not record.get('sha256'):
            raise HistoryError('该导入记录没有服务端算出的内容哈希，不能当开局地图')
        mismatched = [entry.get('import_id') for entry in _entries_of(current['story'])
                      if entry.get('import_id') and entry['import_id'] != import_id]
        if mismatched:
            raise HistoryError('当前故事包里已有来自导入 %s 的历史；把地图换成 %s 会把两个世界'
                               '拼在一起。请先对这份地图重新回放历史'
                               % (mismatched[0], import_id))
        story = copy.deepcopy(current['story'])
        mechanics = story.setdefault('mechanics', {})
        existing = mechanics.get('map')
        link = {'kind': 'civ_atlas', 'import_id': import_id,
                'world_basis_id': (existing or {}).get('world_basis_id'),
                'fog': {'reveal_radius_km': float(fog_radius_km)}}
        if existing == link:
            return {'revision': current['id'], 'link': link, 'reused': True,
                    'note': '这份地图已经是当前故事包的开局地图'}
        mechanics['map'] = link
        revision = runtime.commit_package(story, copy.deepcopy(current['characters']),
                                         '关联开局地图 ' + import_id
                                         + (('：' + note[:120]) if note else ''))
        return {'revision': revision, 'link': link, 'reused': False, 'note': note}

    # --------------------------------------------------------------- projections
    def authored(self, snapshot_id):
        """Author view of a pinned snapshot: every picked entry, secrets included."""
        snapshot = self.get_snapshot(snapshot_id)
        view = {key: snapshot.get(key) for key in
                ('id', 'digest', 'base_year', 'branch', 'window', 'world_basis',
                 'source', 'field_status', 'terrain', 'counts', 'note')}
        view['items'] = snapshot['entries']
        view['disclosure'] = snapshot['disclosure']
        view['local_links'] = snapshot['local_links']
        return view

    def public_view(self, snapshot_id):
        """Player-side projection: only disclosed entries, per item, never the future.

        The disclosure list is explicit entry refs; a category being present does not
        reveal all of it. Anything not listed stays out, and a person alive at the base
        year never exposes a death year or fate (the snapshot does not carry those fields
        in the first place; this is defence in depth).
        """
        snapshot = self.get_snapshot(snapshot_id)
        share = snapshot.get('disclosure') or {}
        allowed = [ref for ref in (share.get('public_refs') or []) if isinstance(ref, str)]
        by_ref = {entry['ref']: entry for entry in snapshot['entries']
                  if isinstance(entry, dict) and entry.get('ref')}
        items = []
        for ref in allowed:
            entry = by_ref.get(ref)
            if entry is None:
                continue
            fields = PUBLIC_ENTRY_FIELDS.get(entry.get('category'), ())
            item = {field: entry.get(field) for field in fields if field in entry}
            item['category'] = entry.get('category')
            summary = share.get('summaries', {}).get(ref)
            if isinstance(summary, str) and summary:
                item['summary'] = summary[:400]
            items.append(item)
        regions = share.get('region_reveal') or {}
        return {
            'snapshot_id': snapshot['id'],
            'base_year': snapshot['base_year'],
            'items': items,
            'counts': {'public': len(items), 'withheld': len(by_ref) - len(items)},
            'region_reveal': regions if isinstance(regions, dict) else {},
            'auto_canonical': False,
        }


def _category_items(document, category):
    """``(items, total)`` for one category of a replay document, refs normalised."""
    if category == 'annals':
        items = [dict(entry, category='annals')
                 for entry in (document.get('annals') or {}).get('events') or ()]
        return items, (document.get('annals') or {}).get('counts', {}).get(
            'inside_window', len(items))
    block = document.get(category) or {}
    rows = [dict(entry, category=category) for entry in block.get('items') or ()]
    if category == 'people':
        rows = [{key: value for key, value in entry.items() if key not in ('died',)}
                for entry in rows]
    return rows, block.get('alive_at_base_year', len(rows))


def _normalise_entries(document, entries, limit):
    """Validate an author's picks against the replay document they came from."""
    if not isinstance(entries, (list, tuple)):
        raise HistoryError('选择的历史条目必须是列表')
    known = {}
    for category in CATEGORIES:
        items, _total = _category_items(document, category)
        for item in items:
            if item.get('ref'):
                known[item['ref']] = item
    picked = []
    seen = set()
    for raw in entries:
        ref = raw.get('ref') if isinstance(raw, dict) else raw
        if not isinstance(ref, str) or not ref:
            raise HistoryError('历史条目必须是 {ref} 或 ref 字符串')
        if ref in seen:
            continue
        entry = known.get(ref)
        if entry is None:
            raise HistoryError('回放文档里没有这个历史条目：%s' % ref[:120])
        seen.add(ref)
        pick = dict(entry)
        if isinstance(raw, dict):
            if raw.get('known_by') is not None:
                pick['known_by'] = _limit_text(raw['known_by'], 'known_by', 120)
            if raw.get('location_id') is not None:
                pick['location_id'] = _limit_text(raw['location_id'], 'location_id', 64)
            if raw.get('summary') is not None:
                pick['summary'] = _limit_text(raw['summary'], 'summary', 400)
        picked.append(pick)
        if len(picked) > limit:
            raise HistoryError('选中的历史条目超过上限 %d；请分页选取' % limit)
    if not picked:
        raise HistoryError('至少要选中一条历史条目')
    return picked


def _normalise_disclosure(disclosure, picked):
    """Per-entry disclosure: explicit public refs, optional per-ref summaries."""
    disclosure = disclosure if isinstance(disclosure, dict) else {}
    unknown = set(disclosure) - {'public_refs', 'summaries', 'region_reveal'}
    if unknown:
        raise HistoryError('披露配置有未知字段：%s' % '、'.join(sorted(unknown)))
    refs = disclosure.get('public_refs') or []
    if not isinstance(refs, (list, tuple)):
        raise HistoryError('public_refs 必须是列表')
    known = {entry['ref'] for entry in picked}
    public = []
    for ref in refs:
        if not isinstance(ref, str):
            raise HistoryError('public_refs 里必须是 ref 字符串')
        if ref not in known:
            raise HistoryError('披露的历史条目不在本次选中范围内：%s' % ref[:120])
        if ref not in public:
            public.append(ref)
    summaries = disclosure.get('summaries') or {}
    if not isinstance(summaries, dict):
        raise HistoryError('summaries 必须是 {ref: 文本}')
    clean = {}
    for ref, text in summaries.items():
        if ref not in set(public):
            raise HistoryError('只能给已公开的历史条目写摘要：%s' % str(ref)[:120])
        clean[ref] = _limit_text(text, 'summary', 400)
    regions = disclosure.get('region_reveal') or {}
    if not isinstance(regions, dict):
        raise HistoryError('region_reveal 必须是对象')
    return {'public_refs': public, 'summaries': clean,
            'region_reveal': {str(key)[:32]: bool(value) for key, value in regions.items()}}


def _normalise_links(local_links, document):
    """civ settlement ref → existing local location id, many-to-many-free and idempotent."""
    links = local_links if isinstance(local_links, dict) else {}
    if not links:
        return {}
    known = {entry['ref'] for entry in
             (document.get('settlements') or {}).get('items') or ()
             if isinstance(entry, dict) and entry.get('ref')}
    seen_targets = {}
    clean = {}
    for settlement_ref, location_id in links.items():
        if not isinstance(settlement_ref, str) or settlement_ref not in known:
            raise HistoryError('要关联的城镇不在这次回放结果里：%s' % str(settlement_ref)[:120])
        location_id = _limit_text(location_id, 'location_id', 64)
        if location_id in seen_targets:
            raise HistoryError('两个上游城镇不能关联到同一个本地地点（%s）：'
                               '同一来源城镇也不要重复关联'
                               % location_id)
        seen_targets[location_id] = settlement_ref
        clean[settlement_ref] = location_id
    return clean


def _limit_text(value, label, limit):
    if not isinstance(value, str):
        raise HistoryError('%s 必须是字符串' % label)
    value = value.strip()
    if not value or len(value) > limit:
        raise HistoryError('%s 必须是非空且不超过 %d 字符' % (label, limit))
    return value


# ===================================================== package-side projections
#: A ``mechanics.history`` entry may carry these keys; anything else is refused at commit
#: time so a hand-edited or imported package cannot smuggle a second history authority in.
ENTRY_KEYS = frozenset({'snapshot_id', 'import_id', 'base_year', 'branch', 'digest',
                        'world_basis_id', 'content_sha256', 'story_id',
                        'adopted_from_revision', 'note', 'snapshot'})

#: The only keys a ``mechanics.history`` block itself may carry.
BLOCK_KEYS = frozenset({'schema', 'entries'})


def package_entries(story):
    """The adopted history entries a *package* carries, or ``[]``.

    Pure read of ``story.mechanics.history``. A package that declares none returns ``[]`` —
    old packages and old journeys behave exactly as before this key existed.
    """
    return list(_entries_of(story))


def package_history_public(story, session=None, audience='player', revision=None):
    """Player-facing history, read **from the package revision only**.

    Nothing here consults the store: a deleted snapshot row, a newer global snapshot or a
    different package revision cannot change what this journey reads, because the snapshot
    was copied into ``mechanics.history`` at adoption time (same rule towns follow).

    ``session`` is the journey snapshot; it supplies the audience's reach (which places it
    has visited, which flags it has set). It is **not** used to look anything up in the
    store: the caller must hand in the story of the revision that journey is bound to
    (``runtime.package(session['revision'])['story']``), exactly like ``towns_store`` does.
    Entries adopted only into a newer revision are therefore simply absent from that story
    and cannot leak into an older journey.
    ``audience`` may be ``'player'`` or one character id; an entry restricted by
    ``known_by`` reaches only that audience.

    Disclosure is per entry (``disclosure.public_refs``). An entry is projected when it is
    listed there, and additionally must not be restricted away from this audience, must not
    be gated by a ``location_id`` the journey has not reached, and must not be behind a
    ``reveal`` flag the journey has not set. Fields stay on the whitelist above, so a death
    year, a fate or a later capital never leaves the package.
    """
    if session is None:
        return []
    rows = []
    for entry in package_entries(story):
        snapshot = entry.get('snapshot') if isinstance(entry.get('snapshot'), dict) else None
        if snapshot is None:
            continue
        adopted = entry.get('adopted_from_revision')
        share = snapshot.get('disclosure') or {}
        public = [ref for ref in (share.get('public_refs') or ()) if isinstance(ref, str)]
        if not public:
            continue
        by_ref = {item['ref']: item for item in snapshot.get('entries') or ()
                  if isinstance(item, dict) and item.get('ref')}
        summaries = share.get('summaries') or {}
        for ref in public:
            item = by_ref.get(ref)
            if item is None:
                continue
            if not _audience_allows(item, audience):
                continue
            if not _reveal_allows(item, session):
                continue
            fields = PUBLIC_ENTRY_FIELDS.get(item.get('category'), ())
            row = {field: item.get(field) for field in fields if field in item}
            row['category'] = item.get('category')
            row['snapshot_id'] = entry.get('snapshot_id')
            row['revision'] = adopted
            summary = summaries.get(ref)
            if isinstance(summary, str) and summary:
                row['summary'] = summary[:400]
            rows.append(row)
    return rows


def _audience_allows(item, audience):
    known_by = item.get('known_by')
    if not known_by:
        return True
    if isinstance(known_by, str):
        known_by = [known_by]
    if not isinstance(known_by, (list, tuple)):
        return False
    return audience in known_by


def _reveal_allows(item, session):
    """A ``location_id``-gated entry needs that place reached; a reveal flag must be set.

    The schema currently supports exactly these two gates. Anything else an author writes is
    not silently treated as "open": an unknown gate keeps the entry out.
    """
    location = item.get('location_id')
    if location is not None:
        reached = session.get('reached') or session.get('visited') or ()
        if location not in reached:
            return False
    flag = item.get('reveal')
    if flag is not None:
        if not isinstance(flag, str) or not flag:
            return False
        if not (session.get('flags') or {}).get(flag):
            return False
    return True


def _check_adoptable(story, snapshot):
    """Refuse an adoption that would mix two worlds or point at a place that is not here.

    Two concrete consumers, both real:

    * ``mechanics.map`` already links this story to an import. If the history snapshot came
      from *different bytes*, the world the players stand in and the history they are given
      would be two different worlds. That is refused: the author must re-replay against the
      linked import (no silent rebind, no map change here).
    * A disclosed settlement carries a ``location_id``. If that place does not exist in the
      package, the projection would dangle, so it is refused. Nothing is matched by name.
    """
    mechanics = (story or {}).get('mechanics') or {}
    link = mechanics.get('map')
    if isinstance(link, dict):
        linked_import = link.get('import_id')
        if linked_import and linked_import != snapshot.get('import_id'):
            raise HistoryError(
                '这份故事包的地图来自导入 %s，而历史快照来自 %s：不能把两个世界的'
                '历史与地图混在一起；请对已关联的导入重新回放，不会在这里悄悄改地图'
                % (linked_import, snapshot.get('import_id')))
    places = {item.get('id') for item in story.get('locations') or ()
              if isinstance(item, dict)}
    links = snapshot.get('local_links') or {}
    for settlement_ref, location_id in links.items():
        if location_id not in places:
            raise HistoryError('历史快照把城镇 %s 关联到本地地点 %s，但当前故事包里没有这个地点'
                               % (str(settlement_ref)[:80], location_id))


def validate_package_history(story):
    """Refuse a malformed or tampered ``mechanics.history``; absent = no-op.

    Called from the package validator path. It checks shape, the digest of every embedded
    snapshot (a hand-edited snapshot is refused), and the per-entry source pin. It does
    **not** consult the store: a package must stand on its own after import.
    """
    mechanics = (story or {}).get('mechanics') or {}
    block = mechanics.get(MECHANICS_KEY)
    if block is None:
        return True
    if not isinstance(block, dict):
        raise HistoryError('mechanics.history 必须是对象')
    extra = set(block) - BLOCK_KEYS
    if extra:
        raise HistoryError('mechanics.history 有未知字段：%s' % '、'.join(sorted(extra)))
    if block.get('schema') != MECHANICS_SCHEMA:
        raise HistoryError('mechanics.history.schema 只认 %d（收到 %r）'
                           % (MECHANICS_SCHEMA, block.get('schema')))
    entries = block.get('entries')
    if not isinstance(entries, list):
        raise HistoryError('mechanics.history.entries 必须是数组')
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise HistoryError('mechanics.history.entries[%d] 不是对象' % index)
        extra = set(entry) - ENTRY_KEYS
        if extra:
            raise HistoryError('mechanics.history.entries[%d] 有未知字段：%s'
                               % (index, '、'.join(sorted(extra))))
        snapshot_id = entry.get('snapshot_id')
        if not isinstance(snapshot_id, str) or not snapshot_id.startswith('hs_'):
            raise HistoryError('mechanics.history.entries[%d].snapshot_id 不是 hs_… 编号'
                               % index)
        if snapshot_id in seen:
            raise HistoryError('历史快照重复绑定：%s' % snapshot_id)
        seen.add(snapshot_id)
        for key in ('content_sha256', 'digest'):
            value = entry.get(key)
            if not isinstance(value, str) or len(value) != 64:
                raise HistoryError('mechanics.history.entries[%d].%s 不是 64 位十六进制'
                                   % (index, key))
        snapshot = entry.get('snapshot')
        if not isinstance(snapshot, dict):
            raise HistoryError('mechanics.history.entries[%d] 缺少自包含的 snapshot' % index)
        if snapshot.get('digest') != content_hash(snapshot):
            raise HistoryError('历史快照 %s 的内容与其 digest 不符（被篡改或损坏）'
                               % snapshot_id)
        if snapshot.get('id') != snapshot_id:
            raise HistoryError('历史快照编号与其内容不一致（%s）' % snapshot_id)
        if entry.get('digest') != snapshot.get('digest'):
            raise HistoryError('历史快照 %s 的引用 digest 与内容不符' % snapshot_id)
        share = snapshot.get('disclosure')
        if not isinstance(share, dict):
            raise HistoryError('历史快照 %s 缺少披露配置' % snapshot_id)
        refs = {item.get('ref') for item in snapshot.get('entries') or ()
                if isinstance(item, dict)}
        for ref in share.get('public_refs') or ():
            if ref not in refs:
                raise HistoryError('历史快照 %s 公开了不在快照里的条目：%s'
                                   % (snapshot_id, str(ref)[:120]))
    return True

