"""Town drafts, immutable versions and story-package binding.

Persistence uses the existing ``Store`` documents namespace (kind/id/body), so there is
no second database and no migration. Kinds:

* ``town_draft``   mutable working copy: four stages, a monotonically increasing
                   integer ``revision`` used for optimistic concurrency, and a per-stage
                   content hash so a change upstream marks the later stages stale.
* ``town_version`` immutable snapshot: the full bounded town (author + public layers),
                   its content hash, and the input it was generated from. Never updated.
* ``town_binding`` immutable record that a version was adopted by one specific story
                   package revision at one specific location. The binding key includes
                   the story identity, so the same town can be adopted by two packages
                   and a retry of one adoption is a no-op.

Two explicit author actions, each idempotent on its own:

1. ``publish``  — draft → immutable ``town_version``. No story package is touched.
2. ``adopt``    — ``town_version`` → bound into ``mechanics.towns`` of a story package
                  revision through ``Runtime.commit_package``. The package carries the
                  complete bounded snapshot, so an exported package can be imported into
                  an empty database and the town still reads. The prefix order is:
                  validate → read the *pinned* base revision → commit the package (own
                  journal) → write the binding row in one short transaction. A crash
                  between the two leaves an unbound version, which a retry binds; it can
                  never leave a binding that points at a package revision without the
                  town, because the adoption marker is written into the package itself.

An old journey keeps its own ``session['revision']`` and therefore keeps reading the
package it started with; a later adoption creates a new revision and cannot reach it.
"""
import copy
import hashlib
import json

from . import element_assembly
from . import towns
from .town_schema import STAGE_MODELS, STAGE_NAMES, STAGE_TITLES, TownSnapshot

GENERATOR = towns.GENERATOR_VERSION
MECHANICS_KEY = 'towns'


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def content_hash(snapshot):
    body = {k: v for k, v in snapshot.items() if k not in ('town_id',)}
    return hashlib.sha256(_canonical(body).encode('utf-8')).hexdigest()[:32]


def stage_hash(stage, value):
    return hashlib.sha256((stage + '\x1f' + _canonical(value)).encode('utf-8')).hexdigest()[:16]


class TownError(ValueError):
    """A refused town operation. Never leaves a partially written document behind."""


class TownService:
    def __init__(self, service):
        self.service = service

    # ---------------------------------------------------------------- documents
    @property
    def store(self):
        return self.service.store

    def get_draft(self, draft_id):
        draft = self.store.get('town_draft', draft_id)
        if not draft:
            raise TownError('城镇草稿不存在')
        return draft

    def list_drafts(self):
        return sorted(self.store.all('town_draft'), key=lambda d: (d['created'], d['id']))

    def list_versions(self):
        return sorted(self.store.all('town_version'), key=lambda d: (d['created'], d['id']))

    def get_version(self, version_id):
        version = self.store.get('town_version', version_id)
        if not version:
            raise TownError('城镇版本不存在')
        return version

    def list_bindings(self, version_id=None):
        rows = self.store.all('town_binding')
        if version_id:
            rows = [r for r in rows if r['version_id'] == version_id]
        return sorted(rows, key=lambda r: (r['created'], r['id']))

    # ------------------------------------------------------------------- create
    def create(self, request):
        """Build all four stages in one pass and store a draft.

        Invalid input is rejected before anything is written: the request is validated,
        every stage is generated and the cross-stage validator runs, all in memory.
        """
        entry = request.input.model_dump(mode='json')
        # A package carrying a locked element manifest restricts which elements this town
        # input may bind: exactly the pinned ID + version, never a library lookup.
        binding_warnings = self._check_bindings(entry)
        snapshot = towns.generate_all(entry)
        draft_id = 'td_' + towns._digest({'seed': entry['seed'],
                                          'site': entry['site_name'],
                                          'revision': entry['story_revision']}, 16)
        stages = []
        for name in STAGE_NAMES:
            stages.append({'name': name, 'title': STAGE_TITLES[name], 'data': snapshot[name],
                           'hash': stage_hash(name, snapshot[name]), 'stale': False,
                           'source': 'generated', 'revision': 0})
        draft = {'id': draft_id, 'revision': 0, 'created': self._now(), 'updated': self._now(),
                 'status': 'draft', 'base_story_revision': entry['story_revision'],
                 'seed': entry['seed'], 'generator_version': GENERATOR,
                 'input': entry, 'stages': stages, 'published': [],
                 'warnings': list(snapshot['warnings']) + binding_warnings}
        self.store.put('town_draft', draft_id, draft)
        return draft

    def _check_bindings(self, entry):
        """TownInput.bindings must stay a faithful subset of the locked manifest.

        Without ``mechanics.element_manifest`` the old behaviour is unchanged: a binding
        proves itself inside the request. With a manifest only the exact pinned
        ID + version may be named, a declared state must match, and a potential element
        stays a pre-bound RECORD: V1 never treats it as an enabled technology, material
        or resource, and a binding never unlocks anything by itself (no implicit
        ``steam_boiler`` just because a wiki entry exists).
        """
        bindings = entry.get('bindings') or []
        if not bindings:
            return []
        try:
            story = self.service.runtime.package(entry['story_revision'])['story']
        except (ValueError, KeyError):
            return []
        manifest = element_assembly.package_manifest(story)
        if manifest is None:
            return []
        by_ref = {element['ref']: element for element in manifest.get('elements', [])}
        by_id = {element['element_id']: element for element in manifest.get('elements', [])}
        warnings = []
        for binding in bindings:
            element = by_ref.get(binding['id']) or by_id.get(binding['id'])
            if element is None:
                raise TownError('城镇输入绑定的元素不在当前故事包清单里：%s；请先在元素装配页采纳它，'
                                '不要直接使用库里的条目' % binding['id'])
            if str(element['version']) != str(binding['version']):
                raise TownError('绑定的元素版本与故事包清单不一致：%s 绑的是 v%s，清单里是 v%s'
                                % (binding['id'], binding['version'], element['version']))
            declared = binding.get('state', 'existing')
            if declared != element['state']:
                raise TownError('绑定声明的状态与清单不一致：%s 声明 %s，清单里是 %s'
                                % (binding['id'], declared, element['state']))
            if element['state'] != 'existing':
                warnings.append('元素 %s 是潜在元素：本版本只把它当作预绑定记录，'
                                '不视为已启用的技术、材料或资源' % binding['id'])
            if binding.get('kind') == 'rule_template':
                warnings.append('绑定 %s 声明为规则模板；本版本不把百科条目转换成可执行规则'
                                % binding['id'])
        return warnings

    def _now(self):
        from .runtime import now
        return now()

    # ------------------------------------------------------------------- stages
    def advance(self, draft_id, expected_revision):
        """Regenerate the next stale or missing stage. Bounded: one stage per call.

        Only the stages *before* the missing one are read, so a stale downstream stage
        never blocks regenerating it. Each call builds exactly one stage; there is no
        loop that keeps generating until everything happens to validate.
        """
        draft = self.get_draft(draft_id)
        self._check(draft, expected_revision)
        if draft['status'] != 'draft':
            raise TownError('已发布的草稿不能再推进；请新建草稿或从版本派生')
        entry = draft['input']
        available = {}
        pending = None
        for name in STAGE_NAMES:
            row = next((s for s in draft['stages'] if s['name'] == name), None)
            if pending is None and (row is None or row.get('stale') or 'data' not in row):
                pending = name
            if row is not None and not row.get('stale') and 'data' in row:
                available[name] = row['data']
        if pending is None:
            raise TownError('四个阶段都已完成，没有可推进的阶段')
        value = towns.build_stage(entry, pending, available)
        self._set_stage(draft, pending, value, 'generated')
        draft['warnings'] = self._validate(draft)
        draft['updated'] = self._now()
        draft['revision'] += 1
        self.store.put('town_draft', draft_id, draft)
        return draft

    def edit_stage(self, draft_id, stage, data, expected_revision):
        """Author edit of one stage. Later stages become stale, never silently kept."""
        if stage not in STAGE_MODELS:
            raise TownError('未知阶段')
        draft = self.get_draft(draft_id)
        self._check(draft, expected_revision)
        if draft['status'] != 'draft':
            raise TownError('已发布的草稿不可编辑；请发布新版本后另存草稿')
        model = STAGE_MODELS[stage]
        try:
            value = model.model_validate(data).model_dump(mode='json')
        except Exception as error:  # pydantic ValidationError, reported as a refusal
            raise TownError('阶段结构校验失败：' + str(error).splitlines()[0]) from error
        position = STAGE_NAMES.index(stage)
        for later in STAGE_NAMES[position + 1:]:
            current = next(s for s in draft['stages'] if s['name'] == later)
            for key in ('data', 'hash'):
                current.pop(key, None)
            current['stale'] = True
        self._set_stage(draft, stage, value, 'edited')
        draft['status'] = 'draft'
        draft['warnings'] = self._validate_partial(draft)
        draft['updated'] = self._now()
        draft['revision'] += 1
        self.store.put('town_draft', draft_id, draft)
        return draft

    def _set_stage(self, draft, name, value, source):
        rows = [s for s in draft['stages'] if s['name'] == name]
        row = rows[0] if rows else {'name': name, 'title': STAGE_TITLES[name]}
        row.update({'data': value, 'hash': stage_hash(name, value), 'stale': False,
                    'source': source})
        if not rows:
            draft['stages'].append(row)
        draft['stages'].sort(key=lambda s: STAGE_NAMES.index(s['name']))

    def _assemble(self, draft):
        snapshot = {'generator_version': draft['generator_version'], 'seed': draft['seed'],
                    'input': draft['input']}
        for name in STAGE_NAMES:
            row = next((s for s in draft['stages'] if s['name'] == name and not s.get('stale')), None)
            if row is None or 'data' not in row:
                raise TownError(f'阶段 {STAGE_TITLES[name]} 尚未完成或已失效，请先推进')
            snapshot[name] = row['data']
        return snapshot

    def snapshot(self, draft):
        """Full validated snapshot of a draft, or a refusal."""
        body = self._assemble(draft)
        snapshot = TownSnapshot.model_validate({**body, 'warnings': []}).model_dump(mode='json')
        snapshot['town_id'] = towns.town_id(draft['input'])
        return snapshot

    def _validate(self, draft):
        try:
            snapshot = self.snapshot(draft)
        except TownError:
            return list(draft.get('warnings', []))
        return towns.validate_snapshot(snapshot)

    def _validate_partial(self, draft):
        # A partially edited draft cannot be cross-validated, so it keeps the previous
        # warnings and is only fully validated on publish.
        return list(draft.get('warnings', []))

    def _check(self, draft, expected_revision):
        if type(expected_revision) is not int:
            raise TownError('乐观版本号必须是整数')
        if draft['revision'] != expected_revision:
            raise TownError(f'草稿已被其他操作更新（当前版本 {draft["revision"]}，'
                            f'提交版本 {expected_revision}），请刷新后重试')

    # ------------------------------------------------------------------ publish
    def publish(self, draft_id, expected_revision):
        """draft → immutable version, inside ONE transaction with an in-transaction CAS.

        The compare-and-swap is re-evaluated against the row as it exists *inside* the
        write lock: a concurrent writer that saved a new stage between our read and our
        commit makes this call fail with zero side effects, instead of overwriting that
        writer's stages with a stale copy.
        """
        draft = self.get_draft(draft_id)
        self._check(draft, expected_revision)
        if draft['status'] != 'draft':
            raise TownError('已发布的草稿不能再发布；请从版本派生新草稿')
        snapshot = self.snapshot(draft)
        warnings = towns.validate_snapshot(snapshot)
        digest = content_hash(snapshot)
        version_id = 'tv_' + digest[:16]
        if not draft['base_story_revision']:
            raise TownError('草稿缺少基础故事包版本')
        version = {'id': version_id, 'created': self._now(), 'content_hash': digest,
                   'generator_version': GENERATOR, 'seed': draft['seed'],
                   'draft_id': draft['id'],
                   'base_story_revision': draft['base_story_revision'],
                   'snapshot': snapshot, 'warnings': warnings,
                   'input': draft['input'], 'town_id': snapshot['town_id']}
        with self.store.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                             ('town_draft', draft_id)).fetchone()
            if row is None:
                raise TownError('城镇草稿不存在')
            latest = json.loads(row[0])
            if latest['revision'] != expected_revision:
                raise TownError(f'草稿已被其他操作更新（当前版本 {latest["revision"]}，'
                                f'提交版本 {expected_revision}），请刷新后重试')
            stored = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                ('town_version', version_id)).fetchone()
            reused = stored is not None
            if stored is not None:
                # The immutable row for this exact content already exists and is never
                # rewritten. Verify it is the same content, then only link the draft.
                version = json.loads(stored[0])
                if version['content_hash'] != digest:
                    raise TownError('城镇版本哈希冲突，已中止写入')
            else:
                db.execute('INSERT INTO documents VALUES(?,?,?)',
                           ('town_version', version_id,
                            json.dumps(version, ensure_ascii=False, separators=(',', ':'))))
            published = list(latest.get('published', []))
            if version_id not in published:
                published.append(version_id)
            latest['published'] = published
            latest['updated'] = self._now()
            # The publish itself is a draft mutation, so it advances the draft revision.
            latest['revision'] = expected_revision + 1
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                       ('town_draft', draft_id,
                        json.dumps(latest, ensure_ascii=False, separators=(',', ':'))))
        return {'version': version, 'draft': latest, 'reused': reused}

    # -------------------------------------------------------------------- adopt
    def adopt(self, version_id, expected_story_revision, location_id=None, note=''):
        """Bind an immutable version into a NEW story package revision.

        Order (nothing is written before every check passes):

        1. validate the version and its pinned base;
        2. reject a version whose base is not this package's world (V1 does not claim
           cross-world reuse — re-generate against the target world instead);
        3. if the pinned base revision ALREADY carries this exact version at this place,
           the previous call got past ``commit_package`` and only lost its index row:
           finish the index and return, without a second package revision;
        4. if the current pointer has moved past the pinned base, refuse: a stale
           request must not be guessed into some later world version;
        5. commit the package (its own journal), then write the binding row.
        """
        version = self.get_version(version_id)
        snapshot = version['snapshot']
        towns.validate_snapshot(snapshot)
        base_revision = version['base_story_revision']
        runtime = self.service.runtime
        runtime.reload_documents()
        try:
            pinned = runtime.package(base_revision)
        except ValueError:
            raise TownError('城镇版本的基础故事包版本已不在库中，无法核对世界身份')
        story_id = pinned['story']['id']
        current = runtime.package()
        if current['story']['id'] != story_id:
            raise TownError('当前故事包与城镇版本的基础世界不同；V1 不允许跨世界采纳，'
                            '请对目标世界重新生成城镇')

        # An adoption of this exact version at this place that the CURRENT package
        # already carries is a completed request: an earlier call got past
        # `commit_package` (possibly losing only its index row), or this is a repeat.
        # Either way finish the index and never mint a second revision.
        prior = next((e for e in _entries_of(current['story'])
                      if e['version_id'] == version_id
                      and e.get('location_id') == (location_id or None)), None)
        if prior is not None:
            binding = self._write_binding(version, story_id, current['id'], location_id, note)
            return {'revision': current['id'], 'version_id': version_id, 'reused': True,
                    'binding': binding,
                    'note': '该版本已在该故事包中，本次只补齐索引，未新建版本'}
        if current['id'] != expected_story_revision:
            raise TownError(f'故事包已变化（当前 {current["id"]}，本次基于 '
                            f'{expected_story_revision}）；请刷新后重新选择，'
                            '不会把旧城镇悄悄挂到新世界上')
        if expected_story_revision != base_revision:
            raise TownError('采纳必须基于城镇版本生成时固定的故事包版本；'
                            f'该版本基于 {base_revision}，本次提交基于 '
                            f'{expected_story_revision}')

        # A previously completed adoption of this exact version at this place is
        # detectable in the pinned package itself, before touching anything.
        committed = _entries_of(pinned['story'])
        prior = next((e for e in committed
                      if e['version_id'] == version_id
                      and e.get('location_id') == (location_id or None)), None)
        if prior is not None:
            binding = self._write_binding(version, story_id, base_revision, location_id, note)
            return {'revision': base_revision, 'version_id': version_id, 'reused': True,
                    'binding': binding,
                    'note': '该版本已经在该故事包版本中，本次只补齐索引，未新建版本'}

        story = copy.deepcopy(current['story'])
        characters = copy.deepcopy(current['characters'])
        mechanics = story.setdefault('mechanics', {})
        registry = mechanics.setdefault(MECHANICS_KEY, {'entries': []})
        if not isinstance(registry, dict) or not isinstance(registry.get('entries'), list):
            raise TownError('故事包里的 towns 配置结构无效，请先修正')
        places = {l['id'] for l in story.get('locations', [])}
        if location_id and location_id not in places:
            raise TownError('绑定的地点不存在')
        elsewhere = next((e for e in registry['entries'] if e['version_id'] == version_id), None)
        if elsewhere is not None:
            raise TownError('该版本已在当前故事包中绑定到另一个地点；请先解绑或改用新版本')
        entry = {'version_id': version_id, 'town_id': version['town_id'],
                 'content_hash': version['content_hash'], 'generator_version': GENERATOR,
                 'seed': version['seed'], 'location_id': location_id or None,
                 'adopted_from_revision': current['id'], 'note': note,
                 'snapshot': snapshot}
        registry['entries'].append(entry)
        revision = runtime.commit_package(story, characters, '采纳城镇版本 ' + version_id)
        # The package revision now carries the snapshot. A crash before this line leaves
        # an adoption that is already visible in the package and merely missing its
        # index row, which the branch above repairs on the next identical request.
        binding = self._write_binding(version, story_id, revision, location_id, note)
        return {'revision': revision, 'version_id': version_id, 'reused': False,
                'binding': binding, 'note': ''}

    def _write_binding(self, version, story_id, revision, location_id, note):
        binding_id = 'tb_' + sha(f'{story_id}\x1f{revision}\x1f{location_id or ""}'
                                 f'\x1f{version["id"]}')
        binding = {'id': binding_id, 'created': self._now(), 'version_id': version['id'],
                   'town_id': version['town_id'], 'story_id': story_id, 'revision': revision,
                   'location_id': location_id or None, 'note': note,
                   'content_hash': version['content_hash']}
        with self.store.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                             ('town_binding', binding_id)).fetchone()
            if row is None:
                db.execute('INSERT INTO documents VALUES(?,?,?)',
                           ('town_binding', binding_id,
                            json.dumps(binding, ensure_ascii=False, separators=(',', ':'))))
            else:
                binding = json.loads(row[0])
        return binding

    def binding_for(self, version_id, story_id, revision=None):
        rows = [r for r in self.store.all('town_binding')
                if r['version_id'] == version_id and r['story_id'] == story_id
                and (revision is None or r['revision'] == revision)]
        return rows[-1] if rows else None

    # --------------------------------------------------------------- projections
    def authored(self, draft_or_version):
        """Author view of one draft or version: every stage, secrets included."""
        if 'snapshot' in draft_or_version:
            snapshot = draft_or_version['snapshot']
        else:
            snapshot = None
        view = {'kind': 'version' if snapshot else 'draft',
                'id': draft_or_version['id'],
                'content_hash': draft_or_version.get('content_hash'),
                'warnings': draft_or_version.get('warnings', [])}
        if snapshot:
            view['snapshot'] = snapshot
        else:
            view['input'] = draft_or_version['input']
            view['stages'] = [{k: v for k, v in s.items() if k != 'data'}
                              for s in draft_or_version['stages']]
            view['snapshot'] = None
            view['can_advance'] = any(s.get('stale') or 'data' not in s
                                      for s in draft_or_version['stages'])
        return view

    # ------------------------------------------------------------- read helpers
    def version_of_document(self, document):
        """Read a version from a stored document or a package-embedded snapshot."""
        if not document:
            raise TownError('没有可用的城镇数据')
        return document


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


# --------------------------------------------------------------------- package side
def _entries_of(story):
    """Internal read of embedded town entries; tolerant of a missing key."""
    registry = (story.get('mechanics') or {}).get(MECHANICS_KEY)
    entries = registry.get('entries') if isinstance(registry, dict) else None
    return entries if isinstance(entries, list) else []


def package_entries(story):
    """Towns a story package carries, in declaration order."""
    return list(_entries_of(story))


def validate_package(story):
    """Story-package validation of embedded towns.

    An untouched package has no ``mechanics.towns`` key, so old packages and old
    journeys are unaffected. When the key exists it must be coherent: unique version
    ids, a real snapshot, and a location that exists in the same package.
    """
    entries = package_entries(story)
    if not entries:
        return
    seen = set()
    places = {l['id'] for l in story.get('locations', [])}
    for entry in entries:
        version_id = entry.get('version_id')
        if not isinstance(version_id, str) or not version_id.startswith('tv_'):
            raise ValueError('城镇条目的 version_id 无效')
        if version_id in seen:
            raise ValueError('同一故事包不能重复采纳同一城镇版本')
        seen.add(version_id)
        if entry.get('location_id') and entry['location_id'] not in places:
            raise ValueError('城镇绑定的地点不存在')
        snapshot = entry.get('snapshot')
        if not snapshot:
            raise ValueError('城镇条目缺少完整快照，导出后无法在空库中读取')
        TownSnapshot.model_validate(snapshot)
        towns.validate_snapshot(snapshot)
        if entry.get('content_hash') != content_hash(snapshot):
            raise ValueError('城镇快照与记录的内容哈希不一致')


def known_scope(session):
    """What a journey may read about towns.

    A journey knows the place it stands in plus everywhere it has actually been, and the
    immediate neighbours of the current place (a traveller can hear of the next town
    before arriving). Anything else is unknown to this journey even if the package
    carries it: the world can hold towns this player has never heard of.
    """
    explored = set(session.get('explored') or [])
    current = session.get('location')
    if current:
        explored.add(current)
    return explored


def neighbouring(story, location_id):
    """Immediate neighbours of one place, if the story package declares them."""
    for place in story.get('locations', []):
        if place['id'] == location_id:
            return set(place.get('neighbors') or [])
    return set()


def visible_entries(story, session, include_neighbours=True):
    """Town entries this journey may read, with how well it knows each one.

    Returns a list of ``(entry, knowledge)`` pairs where knowledge is ``current``,
    ``explored`` or ``nearby``. An entry with no bound location is never public: the
    author may keep a town in the library without putting it anywhere in the world.
    """
    scope = known_scope(session)
    here = session.get('location')
    near = neighbouring(story, here) if include_neighbours and here else set()
    rows = []
    for entry in package_entries(story):
        place = entry.get('location_id')
        if not place:
            continue
        if place == here:
            rows.append((entry, 'current'))
        elif place in scope:
            rows.append((entry, 'explored'))
        elif place in near:
            rows.append((entry, 'nearby'))
    return rows


def story_towns(story, revision=None, session=None):
    """Public towns for one package revision, filtered by what the journey knows.

    ``session`` is the journey snapshot. Without it nothing is returned: a caller that
    cannot say which journey is asking must not receive the whole world's towns.
    """
    if session is None:
        return []
    rows = []
    for entry, knowledge in visible_entries(story, session):
        view = towns.public_view(entry['snapshot'])
        if knowledge == 'nearby':
            # A neighbour is only a rumour: name, type and rough region, nothing about
            # its economy, districts or sites.
            view = {k: view[k] for k in ('town_id', 'name', 'type', 'type_label', 'scale',
                                         'scale_label', 'region')}
            view['knowledge'] = 'nearby'
            view['note'] = '只听说邻近有这处聚落，尚未到过，细节未知'
        else:
            view['knowledge'] = knowledge
        rows.append({'version_id': entry['version_id'], 'town_id': entry.get('town_id'),
                     'location_id': entry.get('location_id'),
                     'content_hash': entry.get('content_hash'), 'revision': revision,
                     'town': view})
    return rows


def town_for_journey(story, session, version_id, revision=None):
    """One town, still filtered by knowledge. Never a lookup by id across the library."""
    for row in story_towns(story, revision, session):
        if row['version_id'] == version_id:
            return row
    raise TownError('该旅程尚未到达或听说此城镇版本')


def context_snippet(story, location_id, limit=1200):
    """Bounded public summary for one location, or '' when there is no town."""
    for entry in package_entries(story):
        if entry.get('location_id') and entry['location_id'] == location_id:
            return towns.context_summary(entry['snapshot'], limit)
    return ''
