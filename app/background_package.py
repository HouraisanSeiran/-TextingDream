"""World-background drafts and immutable publications, separate from playable packages."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

from . import element_assembly, world_setting
from .ai_drafts import DraftRejected
from .civ_sim.config import CivSimConfig, normalize_profiles
from .knowledge import atomic_text, point_document
from .map_bundle import BundleRegistry
from .prompts import stable_json
from .runtime import now, uid

KIND = 'world_package_draft'
SCHEMA = 'world_background_v1'
NOTICE = '世界背景草稿：采用的库资料仍保留候选性质；发布不启用旅程。'
CONTENT_KEYS = {'overview', 'continents', 'polities', 'history_sections', 'knowledge',
                'major_history_proposals'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def normalize_object(raw):
    return (copy.deepcopy(raw), []) if isinstance(raw, dict) else (None, ['输出必须是对象'])


class BackgroundRejected(DraftRejected):
    """Report the explicit action's failure without implying an automatic retry."""

    def __init__(self, errors):
        self.errors = list(errors)
        ValueError.__init__(self, '背景草稿未通过校验，原草稿未改变：' + '；'.join(self.errors[:8]))


def read_background(directory):
    """Read and verify a published background directory without opening its sources."""
    return BackgroundPackages._read(Path(directory) / 'background.json')


class BackgroundPackages:
    def __init__(self, service, registry=None):
        self.service = service
        self.root = Path(service.runtime.root)
        self.registry = registry or BundleRegistry(self.root)

    def get(self, draft_id):
        row = self.service.store.get(KIND, draft_id)
        if not row or row.get('target') != 'background':
            raise ValueError('世界背景草稿不存在')
        return row

    def _editable(self, draft_id, expected_revision=None):
        draft = self.get(draft_id)
        if draft['status'] != 'draft':
            raise ValueError('已发布的背景不可覆盖，请从发布版本创建新草稿')
        if expected_revision is not None and expected_revision != draft['revision']:
            raise ValueError('草稿已变化，请刷新后重试')
        return draft

    def _commit(self, draft, revision):
        draft = copy.deepcopy(draft)
        draft.update(revision=revision + 1, updated=now())
        with self.service.store.transact() as db:
            row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                             (KIND, draft['id'])).fetchone()
            current = json.loads(row[0]) if row else None
            if not current or current['revision'] != revision or current['status'] != 'draft':
                raise ValueError('草稿已变化，结果未写入，请刷新后重试')
            db.execute('UPDATE documents SET body=? WHERE kind=? AND id=?',
                       (json.dumps(draft, ensure_ascii=False), KIND, draft['id']))
        return draft

    def _geography(self, bundle_id):
        from .background_geography import build_geography
        return build_geography(self.registry.get(bundle_id))

    async def _run(self, scope, system, context, example, normalize, validate, max_tokens):
        """Each explicit background action gets one paid attempt per stage."""
        provider = self.service.provider
        offline = bool(provider.config()['offline'])
        usage = {'mode': 'offline' if offline else 'online', 'calls': 0}
        if offline:
            output = copy.deepcopy(example)
            provider.offline_trace(scope, context, output)
        else:
            try:
                output, used = await provider.complete(system, context, json_mode=True,
                                                       scope=scope, max_tokens=max_tokens)
                usage.update(calls=1, attempts=[used])
            except ValueError as error:
                raise BackgroundRejected(['模型调用失败：' + str(error)]) from error
        content, errors = normalize(output)
        if content is not None and not errors:
            errors = validate(content)
        attempts = [{'output': output, 'errors': errors}]
        if errors:
            raise BackgroundRejected(errors)
        return content, attempts, usage, offline

    @staticmethod
    def _profiles(profiles, config, refs=None):
        normalized = normalize_profiles(profiles, CivSimConfig(**config))
        identities = [row['id'] for row in normalized]
        if len(identities) != len(set(identities)):
            raise ValueError('文明偏好 ID 不得重复')
        for row in normalized:
            source = row['source']
            if isinstance(source, dict):
                source_refs = source.get('source_refs', [])
                if (not isinstance(source_refs, list) or
                        any(not isinstance(ref, str) for ref in source_refs) or
                        (refs is not None and set(source_refs) - set(refs))):
                    raise ValueError('文明偏好引用了未采用的元素')
        return normalized

    def sources(self):
        return self.registry.list()

    def _candidates(self, setting):
        rows, offset = [], 0
        while True:
            page = self.service.elements.search(limit=200, offset=offset)
            items = page.get('items') or []
            for item in items:
                tags = item.get('tags') or []
                weights = {'genre:' + g['tag']: g['weight'] for g in setting.get('genres', [])}
                score = sum(weight for tag, weight in weights.items() if tag in tags)
                if world_setting.conflicts(tags, setting) or (weights and not score):
                    continue
                rows.append({key: copy.deepcopy(item.get(key)) for key in
                             ('namespace', 'element_id', 'version', 'name', 'summary', 'tags')})
                rows[-1]['ref'] = element_assembly.ref_of(item['namespace'], item['element_id'])
                rows[-1]['score'] = score
            offset += len(items)
            if not items or not page.get('has_more'):
                break
            if offset >= 5000:
                raise ValueError('候选扫描超过 5000 项，请先缩小资料库范围')
        return sorted(rows, key=lambda r: (-r['score'], r['ref']))

    def propose(self, bundle_id, setting=None, title='', requirements='', config=None,
                year=None, polity_preferences=None):
        setting = world_setting.normalize(setting or {})
        config = CivSimConfig(**(config or {'seed': 20261112})).to_dict()
        polity_preferences = self._profiles(polity_preferences or [], config)
        year = config['end_year'] if year is None else year
        if type(year) is not int or not config['start_year'] <= year <= config['end_year']:
            raise ValueError('背景年份必须在模拟起止年内')
        geography = self._geography(bundle_id)
        candidates = self._candidates(setting)
        if not candidates:
            raise ValueError('没有符合世界设定的真实库候选，请检查资料库与题材档位')
        stamp = now()
        draft = {'id': uid(), 'world_id': 'background_' + uid(),
                 'schema': 'world_background_draft_v1', 'kind': 'background',
                 'target': 'background', 'status': 'draft', 'stage': 'proposed', 'revision': 1,
                 'created': stamp, 'updated': stamp, 'title': title.strip() or '未命名世界背景',
                 'requirements': requirements, 'bundle_id': bundle_id, 'setting': setting,
                 'source': copy.deepcopy(geography['sources']), 'source_digest': digest(geography['sources']),
                 'geography': geography, 'candidates': {'recommended': candidates, 'hinted': []},
                 'config': config, 'year': year, 'polity_preferences': polity_preferences,
                 'selection': None, 'element_manifest': None, 'simulation': None, 'content': None,
                 'approved_history_ids': [], 'usage': {}, 'attempts': {}, 'notice': NOTICE,
                 'offline': bool(self.service.provider.config()['offline']), 'published': None,
                 'parent_version': None}
        self.service.store.put(KIND, draft['id'], draft)
        return draft

    def _lock_selection(self, draft, refs):
        if not refs or len(refs) > element_assembly.MAX_ELEMENTS or len(set(refs)) != len(refs):
            raise ValueError('选择需要 1—64 个不重复的真实候选')
        pool = {row['ref']: row for row in draft['candidates']['recommended']}
        if set(refs) - pool.keys():
            raise ValueError('选择中包含候选库以外的引用')
        selected = [pool[ref] for ref in refs]
        entries = [{'namespace': r['namespace'], 'element_id': r['element_id'],
                    'version': r['version'], 'state': 'existing', 'acknowledge_candidate': True}
                   for r in selected]
        manifest, warnings = self.service.elements.build_manifest(entries, note='世界背景采用资料')
        draft.update(selection={'refs': refs, 'elements': selected}, element_manifest=manifest,
                     element_warnings=warnings, stage='selected', simulation=None, content=None,
                     approved_history_ids=[])
        profiles = [row for row in draft['polity_preferences']
                    if not (isinstance(row.get('source'), dict)
                            and row['source'].get('kind') == 'ai_design_estimate')]
        draft['polity_preferences'] = self._profiles(profiles, draft['config'], refs)
        return draft

    def select(self, draft_id, refs, expected_revision=None, acknowledge_candidates=True):
        draft = self._editable(draft_id, expected_revision)
        if acknowledge_candidates is not True:
            raise ValueError('采用前需要确认库内资料为待审候选')
        return self._commit(self._lock_selection(draft, list(refs)), draft['revision'])

    def _budget(self, system, context):
        limit = self.service.preferences().get('context_chars') or 24000
        if len(system) + len(stable_json(context)) > limit:
            raise ValueError('单项背景输入超过上下文预算，请提高上下文预算')
        return limit

    async def auto_select(self, draft_id, expected_revision=None, acknowledge_candidates=True):
        draft = self._editable(draft_id, expected_revision)
        if acknowledge_candidates is not True:
            raise ValueError('采用前需要确认库内资料为待审候选')
        system = ('根据创作要求从真实候选中选择适用于本世界的资料。只输出 {"refs":[引用]}。'
                  '只能返回候选中的 ref；优先种族、魔法、制度、文化，兼顾其他背景需求。')
        pool, chosen, usages, attempts = draft['candidates']['recommended'], [], [], []
        batches = self._batches(pool, system, {'requirements': draft['requirements'],
                                             'setting': draft['setting']}, item_key='candidates')
        for batch in batches:
            room = element_assembly.MAX_ELEMENTS - len(chosen)
            if room == 0:
                break
            allowed = {r['ref'] for r in batch}
            context = {'requirements': draft['requirements'], 'setting': draft['setting'],
                       'candidates': batch, 'remaining_slots': room}
            self._budget(system, context)
            def validate(raw, allowed=allowed, room=room):
                refs = raw.get('refs')
                if (not isinstance(refs, list) or len(refs) > room or
                        any(not isinstance(r, str) for r in refs) or
                        len(set(refs)) != len(refs) or set(refs) - allowed):
                    return ['refs 必须是本批候选中不重复的引用，且不超过剩余名额']
                return []
            output, tried, used, _ = await self._run(
                'background_select', system, context, {'refs': [r['ref'] for r in batch[:room]]},
                normalize_object, validate, 2000)
            chosen.extend(output['refs'])
            usages.append(used)
            attempts.append(tried)
        if not chosen:
            raise ValueError('AI 没有选择任何资料，请调整要求或手动选择')
        self._lock_selection(draft, chosen)
        # A separate bounded stage sees the complete payload of every adopted item.
        # These are design estimates, never claimed database facts.
        defaults = {name: draft['config'][name + '_weight']
                    for name in ('river', 'coast', 'highland', 'distance')}
        system = ('从已采用设定推导文明地理偏好，输出 {"profiles":[{"id":"...",'
                  '"source_refs":["..."],"rationale":"...","weights":{"river":0,'
                  '"coast":0,"highland":0,"distance":0}}]}。每批一个综合偏好，'
                  '四项权重均为 -1000 到 1000 的整数，不新增键。必须引用本批资料；'
                  '依据不足时保留默认值。数值是游戏设计估计，不是文献事实。')
        profiles = []
        base = {'requirements': draft['requirements'], 'default_weights': defaults}
        elements = [{'ref': row['ref'], 'name': row['name'],
                     'summary': str(row['payload'].get('summary', ''))[:1500],
                     'tags': row['payload'].get('tags', []),
                     'evidence_scope': 'bounded summary; complete payload frozen in manifest'}
                    for row in draft['element_manifest']['elements']]
        for index, batch in enumerate(self._batches(elements, system, base)):
            allowed = {row['ref'] for row in batch}
            context = {**base, 'elements': batch}
            example = {'profiles': [{'id': 'selected-%d' % index,
                                     'source_refs': [row['ref'] for row in batch],
                                     'rationale': '离线模式保留配置默认值，未由模型推导差异。',
                                     'weights': defaults}]}

            def validate_profiles(raw, allowed=allowed):
                rows = raw.get('profiles')
                if not isinstance(rows, list) or len(rows) != 1:
                    return ['每批需要一个文明偏好']
                for row in rows:
                    if not isinstance(row, dict):
                        return ['文明偏好必须为对象']
                    refs, weights = row.get('source_refs'), row.get('weights')
                    if (not isinstance(refs, list) or not refs or
                            any(not isinstance(ref, str) for ref in refs) or set(refs) - allowed):
                        return ['文明偏好必须引用本批采用的资料']
                    if (not isinstance(weights, dict) or set(weights) != set(defaults) or
                            any(type(v) is not int or not -1000 <= v <= 1000 for v in weights.values())):
                        return ['文明偏好仅允许四项有限整数权重']
                    if not isinstance(row.get('rationale'), str) or not row['rationale'].strip():
                        return ['文明偏好需要设计依据']
                return []

            output, tried, used, _ = await self._run(
                'background_profiles', system, context, example, normalize_object,
                validate_profiles, 3000)
            for j, row in enumerate(output['profiles']):
                profiles.append({'id': 'adopted-%d-%d' % (index, j), 'weights': row['weights'],
                                 'source': {'kind': 'ai_design_estimate', 'design_estimate': True,
                                            'source_refs': row['source_refs'],
                                            'rationale': row['rationale'],
                                            'offline': bool(self.service.provider.config()['offline'])}})
            usages.append(used)
            attempts.append(tried)
        draft['polity_preferences'] = self._profiles(profiles, draft['config'], chosen)
        draft['usage']['selection'], draft['attempts']['selection'] = usages, attempts
        return self._commit(draft, draft['revision'])

    def configure(self, draft_id, config=None, year=None, polity_preferences=None,
                  expected_revision=None):
        draft = self._editable(draft_id, expected_revision)
        config = CivSimConfig(**(draft['config'] if config is None else config)).to_dict()
        year = draft['year'] if year is None else year
        if type(year) is not int or not config['start_year'] <= year <= config['end_year']:
            raise ValueError('背景年份必须在模拟起止年内')
        draft.update(config=config, year=year, simulation=None, content=None, approved_history_ids=[],
                     stage='selected' if draft['selection'] else 'proposed')
        if polity_preferences is not None:
            draft['polity_preferences'] = self._profiles(
                polity_preferences, config, draft['selection']['refs'] if draft['selection'] else None)
        return self._commit(draft, draft['revision'])

    def simulate(self, draft_id, expected_revision=None):
        from .background_geography import simulate_background
        draft = self._editable(draft_id, expected_revision)
        if not draft['selection']:
            raise ValueError('请先采用背景资料')
        self._fresh(draft)
        draft['polity_preferences'] = self._profiles(
            draft['polity_preferences'], draft['config'], draft['selection']['refs'])
        result = simulate_background(self.registry.get(draft['bundle_id']), draft['config'],
                                     profiles=draft['polity_preferences'], background_year=draft['year'],
                                     geography=draft['geography'])
        result['selected_elements'] = [{key: row[key] for key in
            ('ref', 'version', 'payload_hash') if key in row}
            for row in draft['element_manifest']['elements']]
        draft.update(simulation=result, geography=result['geography'], content=None,
                     stage='simulated', approved_history_ids=[])
        return self._commit(draft, draft['revision'])

    def freshness(self, draft_id):
        from .background_geography import source_pin
        draft = self.get(draft_id)
        source = source_pin(self.registry.get(draft['bundle_id']))
        return {'stale': digest(source) != draft['source_digest'],
                'recorded': draft['source'], 'current': source}

    def _fresh(self, draft):
        if self.freshness(draft['id'])['stale']:
            raise ValueError('世界地理来源已变化，请创建新背景草稿')

    def _batches(self, items, system, base, item_key='elements'):
        batches, current = [], []
        for item in items:
            candidate = current + [item]
            try:
                self._budget(system, {**base, item_key: candidate})
            except ValueError:
                if not current:
                    raise
                batches.append(current)
                current = [item]
                self._budget(system, {**base, item_key: current})
            else:
                current = candidate
        if current:
            batches.append(current)
        return batches

    def _element_inputs(self, elements, system, base):
        """Losslessly divide oversized adopted payloads; snapshots remain intact."""
        items = []
        for row in elements:
            item = {key: copy.deepcopy(row[key]) for key in ('ref', 'name', 'payload')}
            item['adaptation'] = copy.deepcopy(row.get('adaptation', {}))
            try:
                self._budget(system, {**base, 'elements': [item]})
            except ValueError:
                serialized = stable_json({'payload': item['payload'], 'adaptation': item['adaptation']})
                shell = {'ref': item['ref'], 'name': item['name'], 'part': 99999, 'parts': 99999,
                         'payload': {'summary': item['name'], 'source_json_fragment': ''}}
                limit = self.service.preferences().get('context_chars') or 24000
                # JSON escaping can at most double these fragments' common characters.
                room = (limit - len(system) - len(stable_json({**base, 'elements': [shell]})) - 200) // 2
                if room <= 0:
                    self._budget(system, {**base, 'elements': [shell]})
                    raise ValueError('要求与元素标识已占满上下文预算')
                chunks = [serialized[start:start + room] for start in range(0, len(serialized), room)]
                for index, fragment in enumerate(chunks):
                    piece = copy.deepcopy(shell)
                    piece.update(part=index + 1, parts=len(chunks))
                    piece['payload']['source_json_fragment'] = fragment
                    self._budget(system, {**base, 'elements': [piece]})
                    items.append(piece)
            else:
                items.append(item)
        return items

    @staticmethod
    def _events(simulation):
        return [dict(row, id='sim_%06d' % index) for index, row in
                enumerate(simulation['chronicle'].get('annals', []))
                if row['year'] <= simulation['background_year']]

    @staticmethod
    def _historical_polities(simulation):
        """Include extinct kingdoms; final live borders are a different projection."""
        rows = {}
        chronicle = simulation['chronicle']
        for snapshot in chronicle.get('snapshots', []):
            if snapshot['year'] <= simulation['background_year']:
                for row in snapshot.get('polities', []):
                    rows[row['id']] = row
        for row in chronicle.get('polities', []):
            if row.get('founded', simulation['background_year']) <= simulation['background_year']:
                rows[row['id']] = row
        return [{'id': 'kingdom-%s' % identity, 'polity_id': identity, 'name': row['name']}
                for identity, row in sorted(rows.items())]

    @staticmethod
    def _event_fact(event):
        return {key: event.get(key) for key in ('id', 'year', 'kind', 'polity_a', 'polity_b')}

    def _validate_history(self, rows, events, simulation=None):
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return ['history_sections 必须为对象列表']
        errors, checker = [], None
        if simulation is not None:
            from .world_package_pipeline import NarrativeChecker
            chronicle = simulation['chronicle']
            terms = [row.get('name') for key in ('people', 'dynasties', 'faiths')
                     for row in chronicle.get(key, [])]
            # The simulator uses generic phrases such as "开国王朝". Preserve
            # source notes as recognized terms so literal facts are never rejected
            # as newly invented proper names by the legacy suffix matcher.
            terms.extend(event.get('note', '') for event in events.values())
            checker = NarrativeChecker(self._historical_polities(simulation), [
                {'event_id': event['id'], 'year': event['year'],
                 'actors': [event[key] for key in ('polity_a', 'polity_b') if event.get(key) is not None],
                 'text': event.get('note', '')} for event in events.values()], terms)
        for row in rows:
            ids = row.get('event_ids')
            if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids)
                    or len(set(ids)) != len(ids) or set(ids) - events.keys()):
                errors.append('历史段落必须引用本次模拟史事，不得重复引用')
                continue
            facts = row.get('event_facts')
            expected = [self._event_fact(events[ident]) for ident in ids]
            if facts != expected:
                errors.append('历史段落的事件 ID、年份、类型及参与国必须与模拟一致')
            if any(not isinstance(row.get(key), str) or not row[key].strip()
                   for key in ('title', 'text')):
                errors.append('历史段落需要标题与正文')
                continue
            years = {str(events[ident]['year']) for ident in ids}
            if set(re.findall(r'(?<!\d)(-?\d+)\s*年', row['text'])) - years:
                errors.append('历史正文使用了未引用的年份')
            if checker is not None:
                errors.extend(checker.check('历史正文', row['text'], ids))
        return errors

    def _validate_content(self, draft, content):
        errors = []
        if not isinstance(content, dict) or set(content) != CONTENT_KEYS:
            return ['背景内容字段必须为 ' + ', '.join(sorted(CONTENT_KEYS))]
        if not isinstance(content['overview'], str) or not content['overview'].strip():
            errors.append('世界总概不能为空')
        sim = draft['simulation']
        pids = {str(p['id']) for p in sim['kingdoms']}
        historical_pids = pids | {p['id'] for p in self._historical_polities(sim)}
        lids = {str(p['id']) for p in sim['landmasses']}
        refs = set(draft['selection']['refs'])
        geography_refs = {group + '.' + field for group, data in sim['geography'].get('groups', {}).items()
                          for field in data.get('fields', {})}
        events = {r['id']: r for r in self._events(sim)}
        for key, ids in [('polities', pids), ('continents', lids)]:
            rows = content[key]
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                errors.append(key + ' 必须为对象列表')
                continue
            got = [str(r.get('id')) for r in rows]
            if len(got) != len(set(got)) or set(got) != ids:
                errors.append(key + ' 必须恰好覆盖模拟中的对象，不能新增或删除')
        for key in ('history_sections', 'knowledge', 'major_history_proposals'):
            if not isinstance(content[key], list) or any(not isinstance(r, dict) for r in content[key]):
                errors.append(key + ' 必须为对象列表')
        if errors:
            return errors
        for row in (content['continents'] + content['polities'] + content['history_sections']
                    + content['knowledge'] + content['major_history_proposals']):
            for key in ('element_refs', 'race_refs', 'magic_refs'):
                values = row.get(key, [])
                if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or set(values) - refs:
                    errors.append('背景引用了未采用的元素')
            values = row.get('geography_refs', [])
            if (not isinstance(values, list) or any(not isinstance(v, str) for v in values)
                    or set(values) - geography_refs):
                errors.append('背景引用了不存在的冻结地理字段')
            if 'geometry' in row or 'region_ids' in row:
                errors.append('AI 背景不可改写模拟疆域')
            if 'event_ids' in row:
                event_ids = row['event_ids']
                if (not isinstance(event_ids, list) or any(not isinstance(i, str) for i in event_ids)
                        or set(event_ids) - events.keys()):
                    errors.append('背景引用了不存在的模拟史事')
        for row in content['continents'] + content['polities']:
            fixed_fields = {'geometry', 'region_ids', 'regions', 'polity_id', 'founded', 'ended',
                            'alive', 'capital', 'capital_region_id', 'background_year', 'profile_id',
                            'land_cells', 'area_m2', 'landmass_ids', 'monarch_id', 'dynasty_id', 'faith_id'}
            if fixed_fields.intersection(row):
                errors.append('背景正文对象不可写入模拟身份、年份、存亡或疆域字段；请保留在固定模拟快照中')
            if any(not isinstance(row.get(key), str) or not row[key].strip()
                   for key in ('name', 'summary')):
                errors.append('大陆与王国需要名称和背景说明')
        knowledge_ids = []
        for row in content['knowledge']:
            if any(not isinstance(row.get(key), str) or not row[key].strip()
                   for key in ('id', 'title', 'content')):
                errors.append('知识点需要 ID、标题与正文')
            knowledge_ids.append(row.get('id'))
        if all(isinstance(ident, str) for ident in knowledge_ids) and len(set(knowledge_ids)) != len(knowledge_ids):
            errors.append('知识点 ID 不得重复')
        errors.extend(self._validate_history(content['history_sections'], events, sim))
        proposals = content['major_history_proposals']
        ids = [r.get('id') for r in proposals]
        if any(not isinstance(i, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', i) for i in ids) or len(ids) != len(set(ids)):
            errors.append('新增重大史事需要不重复的有效 ID')
        for row in proposals:
            year = row.get('year')
            if type(year) is not int or not draft['config']['start_year'] <= year <= draft['year']:
                errors.append('新增重大史事年份必须在背景历史范围内')
            polity_ids = row.get('polity_ids', [])
            if (not isinstance(polity_ids, list) or any(not isinstance(p, str) for p in polity_ids)
                    or set(polity_ids) - historical_pids):
                errors.append('新增史事引用了不存在的王国')
            if not isinstance(row.get('text'), str) or not row['text'].strip():
                errors.append('新增重大史事需要内容')
        return errors

    async def generate(self, draft_id, expected_revision=None):
        draft = self._editable(draft_id, expected_revision)
        if not draft['simulation']:
            raise ValueError('请先生成文明历史骨架')
        self._fresh(draft)
        sim = draft['simulation']
        used, attempts, notes, physical_summaries = {}, {}, [], []
        physical_inputs = [dict(ref=group + '.' + field, group=group, field=field,
                           grid=data['grid'], evidence=descriptor)
                           for group, data in sim['geography'].get('groups', {}).items()
                           for field, descriptor in data.get('fields', {}).items()]
        system = ('根据冻结地理字段写自然环境知识，输出 {"knowledge":[{"id":"...",'
                  '"title":"...","content":"...","element_refs":[],"geography_refs":["..."]}],'
                  '"summary":"不超过400字的本批自然条件摘要"}。'
                  '完整覆盖本批字段。解释原单位、原网格与月度语义，保留缺测和不可查询的限制。'
                  '只解释给定统计，不添加种族、魔法、国家或历史事实；每条正文不超过 1200 字。')
        for index, batch in enumerate(self._batches(physical_inputs, system,
                                      {'year': draft['year']}, 'fields')):
            allowed = {row['ref'] for row in batch}
            example = {'summary': '本批冻结字段覆盖 ' + '、'.join(sorted({row['group'] for row in batch})) +
                       '；保留原单位、网格、月度与缺测语义，细节见自然环境知识及冻结快照。',
                       'knowledge': [{'id': 'environment_%02d_%02d' % (index, j),
                       'title': row['ref'], 'content': '冻结地理字段 %s；单位 %s；%s。完整统计见冻结地理快照。' %
                       (row['ref'], row['evidence'].get('unit', '未声明'),
                        row['evidence'].get('time_semantics') or row['evidence'].get('status', '未声明')),
                       'element_refs': [], 'geography_refs': [row['ref']]}
                       for j, row in enumerate(batch)]}

            def check_environment(raw, allowed=allowed):
                if not isinstance(raw.get('summary'), str) or not 1 <= len(raw['summary']) <= 400:
                    return ['自然环境摘要需要 1 至 400 字的文本']
                rows = raw.get('knowledge')
                if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                    return ['自然环境 knowledge 必须为对象列表']
                cited = set()
                for row in rows:
                    refs = row.get('geography_refs')
                    if (not isinstance(refs, list) or not refs or
                            any(not isinstance(ref, str) for ref in refs) or set(refs) - allowed):
                        return ['自然环境知识只能引用本批冻结地理字段']
                    if row.get('element_refs') != []:
                        return ['自然环境知识不可引入库元素']
                    if any(not isinstance(row.get(key), str) or not row[key].strip()
                           for key in ('id', 'title', 'content')) or len(row['content']) > 1200:
                        return ['自然环境知识需要 ID、标题与不超过 1200 字的正文']
                    cited.update(refs)
                return [] if cited == allowed else ['自然环境知识必须覆盖本批全部字段']

            output, tried, usage, _ = await self._run(
                'background_environment', system, {'year': draft['year'], 'fields': batch},
                example, normalize_object, check_environment, 5000)
            for j, row in enumerate(output['knowledge']):
                row['id'] = 'environment_%02d_%02d' % (index, j)
            notes.extend(output['knowledge'])
            physical_summaries.append({'fields': sorted(allowed), 'summary': output['summary']})
            used['environment_%d' % index], attempts['environment_%d' % index] = usage, tried
        system = ('你正在为世界背景整理已采用资料。只输出 {"knowledge":[{"id":"...",'
                  '"title":"...","content":"...","element_refs":["..."]}]}。'
                  '逐项覆盖所有输入元素，不新增种族、魔法、战争、建国或地理事实。')
        items = self._element_inputs(draft['element_manifest']['elements'], system,
                                     {'requirements': draft['requirements']})
        for index, batch in enumerate(self._batches(items, system, {'requirements': draft['requirements']})):
            expected_refs = {r['ref'] for r in batch}
            example = {'knowledge': [{'id': 'element_%02d_%02d' % (index, j), 'title': r['name'],
                                      'content': r['payload'].get('summary', r['name']),
                                      'element_refs': [r['ref']]} for j, r in enumerate(batch)]}
            def validate(raw, expected_refs=expected_refs):
                rows = raw.get('knowledge')
                if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                    return ['knowledge 必须为对象列表']
                got = set()
                for row in rows:
                    if any(not isinstance(row.get(key), str) or not row[key].strip()
                           for key in ('id', 'title', 'content')):
                        return ['知识点需要 ID、标题与正文']
                    refs = row.get('element_refs', [])
                    if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                        return ['element_refs 必须为引用列表']
                    got.update(refs)
                return [] if got == expected_refs else ['必须覆盖本批全部采用资料且不引用其他元素']
            context = {'requirements': draft['requirements'], 'elements': batch}
            output, tried, usage, _ = await self._run(
                'background_elements', system, context, example, normalize_object, validate, 6000)
            for j, row in enumerate(output['knowledge']):
                row['id'] = 'element_%02d_%02d' % (index, j)
            notes.extend(output['knowledge'])
            used['elements_%d' % index], attempts['elements_%d' % index] = usage, tried
        events = self._events(sim)
        content = {'overview': draft['title'] + '：依据已固定的自然环境、文明历史和采用设定形成的世界背景。',
                   'continents': [{'id': str(r['id']), 'name': r.get('name', str(r['id'])),
                                   'summary': '陆块范围依据冻结地理数据。'} for r in sim['landmasses']],
                   'polities': [{'id': str(r['id']), 'name': r['name'], 'summary': '制度与文化待作者补充。',
                                 'institution': '', 'culture': '', 'race_refs': [], 'magic_refs': [],
                                 'element_refs': []} for r in sim['kingdoms']],
                   'history_sections': [],
                   'knowledge': notes, 'major_history_proposals': []}
        historical = {row['polity_id']: row for row in self._historical_polities(sim)}
        history_inputs = [dict(event, actors=[historical[pid] for pid in
                         (event.get('polity_a'), event.get('polity_b')) if pid in historical])
                          for event in events]
        system = ('把模拟史事写成可读的世界历史背景，输出 {"history_sections":'
                  '[{"title":"...","text":"...","event_ids":["..."],"event_facts":'
                  '[{"id":"...","year":0,"kind":"...","polity_a":null,"polity_b":null}]}]}。'
                  '完整覆盖本批事件。每段 event_facts 必须按 event_ids 顺序逐项原样复制史事五个字段。'
                  '正文只叙述引用事件已明确的事实，不新增战争、建国、死亡、人物或因果。'
                  '年份和参战国不得改变，已灭亡国家仍可作为历史主体；不把历史人物当作当前在世人物。')
        for index, batch in enumerate(self._batches(history_inputs, system,
                                                   {'background_year': draft['year']}, 'events')):
            allowed = {event['id']: event for event in batch}
            example = {'history_sections': [{'title': '编年背景 %d' % (index + 1),
                       'text': '\n'.join('%s年：%s' % (event['year'], event.get('note') or event['kind'])
                                        for event in batch),
                       'event_ids': list(allowed),
                       'event_facts': [self._event_fact(event) for event in batch]}]}

            def check_history(raw, allowed=allowed):
                rows = raw.get('history_sections')
                errors = self._validate_history(rows, allowed, sim)
                if not errors and {ident for row in rows for ident in row['event_ids']} != set(allowed):
                    errors.append('历史叙述必须覆盖本批全部事件')
                return errors

            output, tried, usage, _ = await self._run(
                'background_history', system, {'background_year': draft['year'], 'events': batch},
                example, normalize_object, check_history, 7000)
            content['history_sections'].extend(output['history_sections'])
            used['history_%d' % index], attempts['history_%d' % index] = usage, tried
        # Generate each polity separately; every call sees its actual immutable background.
        for index, polity in enumerate(sim['kingdoms']):
            system = ('补充一个王国的制度、文化与族群/魔法适用背景。输出 {"polity":{...},'
                      '"major_history_proposals":[]}。保留 id 和 name；只引用允许元素。'
                      '本次只合并这一批采用资料，并保留 previous 已有的背景与引用。'
                      'simulation_* 为背景年以内的固定史事、人物与政体身份，不能改写；'
                      '死亡人物仅作历史主体，不作为当前在世人物。'
                      '不得改写模拟疆域、存亡、战争和年份；新增重大史事单列提案。'
                      'summary/institution/culture 每项不超过 1000 字。')
            base = {'requirements': draft['requirements'], 'polity': {k: polity[k] for k in
                    ('id', 'name', 'background_year', 'profile_id') if k in polity},
                    'year': draft['year'], 'previous': content['polities'][index]}
            # Reserve room for the next bounded previous-polity state.
            reserve = {**base, 'previous': dict(base['previous'], summary=' ' * 1000,
                       institution=' ' * 1000, culture=' ' * 1000)}
            local_environment = [dict(title='Native territory field ' + group + '.' + field,
                                     geography_refs=[group + '.' + field],
                                     grid=data['grid'], evidence=descriptor)
                                 for group, data in polity.get('native_environment', {}).get('groups', {}).items()
                                 for field, descriptor in data.get('fields', {}).items()]
            pid = polity['polity_id']
            historical_inputs = [dict(kind='simulation_event', event=event)
                                 for event in history_inputs if pid in
                                 (event.get('polity_a'), event.get('polity_b'))]
            for table in ('people', 'dynasties'):
                historical_inputs.extend(dict(kind='simulation_' + table, record=row)
                    for row in sim['chronicle'].get(table, []) if row.get('polity_id') == pid)
            current = next((row for row in sim['chronicle'].get('polities', []) if row['id'] == pid), {})
            historical_inputs.append(dict(kind='simulation_polity', record={key: value
                for key, value in current.items() if key != 'regions'}))
            historical_inputs.extend(dict(kind='simulation_faith', record=row)
                for row in sim['chronicle'].get('faiths', []) if row['id'] == current.get('faith_id'))
            for batch_index, batch in enumerate(self._batches(notes + local_environment + historical_inputs, system,
                                                               reserve, 'knowledge')):
                context = {**base, 'previous': content['polities'][index], 'knowledge': batch}
                self._budget(system, context)
                example = {'polity': content['polities'][index], 'major_history_proposals': []}

                def check(raw, index=index, polity=polity):
                    row = raw.get('polity')
                    if (not isinstance(row, dict) or str(row.get('id')) != str(polity['id'])
                            or row.get('name') != polity['name']):
                        return ['王国 id 与 name 必须保持模拟身份']
                    if any(not isinstance(row.get(key), str) or len(row[key]) > 1000
                           for key in ('summary', 'institution', 'culture')):
                        return ['王国 summary/institution/culture 必须为不超过 1000 字的文本']
                    candidate = copy.deepcopy(content)
                    candidate['polities'][index] = row
                    candidate['major_history_proposals'] = raw.get('major_history_proposals', [])
                    return self._validate_content(draft, candidate)

                output, tried, usage, _ = await self._run(
                    'background_polity', system, context, example, normalize_object, check, 4000)
                content['polities'][index] = output['polity']
                content['major_history_proposals'].extend(output.get('major_history_proposals', []))
                key = 'polity_%d_%d' % (index, batch_index)
                used[key], attempts[key] = usage, tried
        system = ('为陆块补充名称与人文背景，输出 {"continents":[{"id":"...",'
                  '"name":"...","summary":"..."}]}。保留本批全部 id，不新增重大史事，'
                  '不改变自然地理和模拟事实。陆块范围已固定；大陆仅为背景称谓。')
        named = []
        continent_base = {'year': draft['year'], 'native_environment': physical_summaries}
        for index, batch in enumerate(self._batches(content['continents'], system,
                                      continent_base, 'continents')):
            allowed = {row['id'] for row in batch}

            def check_continents(raw, allowed=allowed):
                rows = raw.get('continents')
                if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                    return ['continents 必须为对象列表']
                if len(rows) != len(allowed) or {row.get('id') for row in rows} != allowed:
                    return ['大陆必须恰好覆盖本批陆块']
                if any(any(not isinstance(row.get(key), str) or not row[key].strip()
                           for key in ('name', 'summary')) for row in rows):
                    return ['大陆需要名称与背景']
                if any('geometry' in row or 'region_ids' in row for row in rows):
                    return ['大陆背景不可改写自然地理']
                return []

            output, tried, usage, _ = await self._run(
                'background_continents', system, {**continent_base, 'continents': batch},
                {'continents': batch}, normalize_object, check_continents, 4000)
            named.extend(output['continents'])
            used['continents_%d' % index], attempts['continents_%d' % index] = usage, tried
        content['continents'] = named
        system = ('根据冻结背景的目录输出 {"overview":"世界总概"}。'
                  '写自然环境、文明和采用设定的总体定位，不枚举所有细节。'
                  '不新增重大史事，不改变地理和模拟事实；细节已分节保存。')
        context = {'title': draft['title'], 'requirements': draft['requirements'], 'year': draft['year'],
                   'setting': draft['setting'], 'landmass_count': len(content['continents']),
                   'polities': [{'id': row['id'], 'name': row['name']} for row in content['polities']],
                   'adopted_elements': [{'ref': row['ref'], 'name': row['name']}
                                        for row in draft['element_manifest']['elements']],
                   'history_event_count': len(events),
                   'native_environment': physical_summaries,
                   'geography_summary': sim['geography'].get('summary', {})}
        self._budget(system, context)
        def validate_summary(raw):
            candidate = dict(content, overview=raw.get('overview'))
            return self._validate_content(draft, candidate)
        output, tried, usage, offline = await self._run(
            'background_overview', system, context,
            {'overview': content['overview']},
            normalize_object, validate_summary, 4000)
        content.update(output)
        errors = self._validate_content(draft, content)
        if errors:
            raise BackgroundRejected(errors)
        used['overview'], attempts['overview'] = usage, tried
        self._fresh(draft)
        draft.update(content=content, stage='generated', approved_history_ids=[], offline=offline)
        draft['usage']['generation'], draft['attempts']['generation'] = used, attempts
        return self._commit(draft, draft['revision'])

    def edit(self, draft_id, content, expected_revision=None, approved_history_ids=None):
        draft = self._editable(draft_id, expected_revision)
        if not draft['simulation']:
            raise ValueError('请先生成历史骨架')
        errors = self._validate_content(draft, content)
        if errors:
            raise BackgroundRejected(errors)
        approved = list(draft['approved_history_ids'] if approved_history_ids is None else approved_history_ids)
        proposal_ids = {r['id'] for r in content['major_history_proposals']}
        if len(set(approved)) != len(approved) or set(approved) - proposal_ids:
            raise ValueError('批准清单引用了不存在或重复的史事提案')
        draft.update(content=copy.deepcopy(content), approved_history_ids=approved, stage='generated')
        return self._commit(draft, draft['revision'])

    def _published_document(self, draft, version_id, folder):
        content = copy.deepcopy(draft['content'])
        approved = set(draft['approved_history_ids'])
        proposals = content.pop('major_history_proposals')
        document = {'schema': SCHEMA, 'kind': 'background', 'id': draft['world_id'],
                    'version_id': version_id, 'draft_id': draft['id'],
                    'draft_revision': draft['revision'], 'title': draft['title'],
                    'folder': folder, 'created': now(), 'can_start': False,
                    'reason': '世界背景已发布；尚需下级聚落与开局内容才能开始旅程',
                    'parent_version': draft.get('parent_version'), 'bundle_id': draft['bundle_id'],
                    'source': draft['source'], 'source_digest': draft['source_digest'],
                    'setting': draft['setting'], 'element_manifest': draft['element_manifest'],
                    'geography': draft['geography'], 'simulation': draft['simulation'],
                    'background_year': draft['year'], 'content': content,
                    'approved_history': [r for r in proposals if r['id'] in approved],
                    'unapproved_history': [r for r in proposals if r['id'] not in approved],
                    'generation': {'requirements': draft['requirements'], 'usage': draft['usage'],
                                   'offline': draft['offline'], 'config': draft['config'],
                                   'polity_preferences': draft['polity_preferences']}}
        document['content_hash'] = digest(document)
        return document

    def confirm(self, draft_id, expected_revision=None):
        draft = self.get(draft_id)
        if draft['status'] == 'published':
            self.get_version(draft['published']['version_id'])
            return draft
        draft = self._editable(draft_id, expected_revision)
        if draft['stage'] != 'generated' or not draft['content']:
            raise ValueError('请先生成并审阅背景')
        self._fresh(draft)
        errors = self._validate_content(draft, draft['content'])
        if errors:
            raise BackgroundRejected(errors)
        version_id = 'bgv_' + draft['id']
        folder = '背景_' + version_id
        library = Path(self.service.runtime.library)
        target, stage = library / folder, library / ('.pending_' + version_id)
        document = self._published_document(draft, version_id, folder)
        # Deterministic folder makes a retry after publication/store interruption recoverable.
        if target.exists():
            document = self._read(target / 'background.json')
            if document['draft_id'] != draft_id or document.get('draft_revision') != draft['revision']:
                raise ValueError('背景发布目录已存在')
        else:
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir(parents=True, exist_ok=False)
            try:
                atomic_text(stage / 'background.json', json.dumps(document, ensure_ascii=False, indent=2))
                atomic_text(stage / '总概.md', document['content']['overview'] + '\n')
                for index, point in enumerate(document['content']['knowledge']):
                    normalized = {'id': 'background_%04d' % index,
                                  'title': point.get('title', '背景资料'), 'category': '世界背景',
                                  'keywords': [point.get('title', '背景资料')], 'visibility': 'author',
                                  'content': point.get('content', ''), 'status': '作者已采纳背景'}
                    atomic_text(stage / '知识点' / (normalized['id'] + '.md'), point_document(normalized))
            except BaseException:
                if stage.exists():
                    shutil.rmtree(stage)
                raise
        draft.update(status='published', stage='published', published={
            'id': document['id'], 'version_id': version_id, 'folder': folder,
            'kind': 'background', 'can_start': False})
        # Keep the final CAS, directory rename and draft transition under the same
        # short write lock. Model calls and expensive geography work happen outside.
        revision = draft['revision']
        draft.update(revision=revision + 1, updated=now())
        try:
            with self.service.store.transact() as db:
                row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                 (KIND, draft_id)).fetchone()
                current = json.loads(row[0]) if row else None
                if not current or current['revision'] != revision or current['status'] != 'draft':
                    raise ValueError('草稿已变化，背景未发布，请刷新后重试')
                if not target.exists():
                    stage.rename(target)
                db.execute('UPDATE documents SET body=? WHERE kind=? AND id=?',
                           (json.dumps(draft, ensure_ascii=False), KIND, draft_id))
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return draft

    @staticmethod
    def _read(path):
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError('背景文件不支持符号链接')
        document = json.loads(path.read_text(encoding='utf-8'))
        recorded = document.pop('content_hash', None)
        if document.get('schema') != SCHEMA or recorded != digest(document):
            raise ValueError('背景版本格式或内容哈希不符')
        document['content_hash'] = recorded
        return document

    def list_versions(self):
        result = []
        library = Path(self.service.runtime.library)
        for path in sorted(library.glob('背景_bgv_*/background.json')):
            doc = self._read(path)
            result.append({k: doc[k] for k in ('id', 'version_id', 'folder', 'title', 'created',
                                             'kind', 'can_start', 'reason', 'background_year')})
        return result

    def get_version(self, version_id):
        if not re.fullmatch(r'bgv_[A-Za-z0-9_-]{1,80}', version_id):
            raise ValueError('背景版本 ID 无效')
        path = Path(self.service.runtime.library) / ('背景_' + version_id) / 'background.json'
        if not path.is_file():
            raise ValueError('背景版本不存在')
        document = self._read(path)
        if document['version_id'] != version_id:
            raise ValueError('背景版本身份不符')
        return document

    def town_context(self, version_id, polity_id):
        doc = self.get_version(version_id)
        polity = next((r for r in doc['simulation']['kingdoms']
                       if str(polity_id) in (str(r['id']), str(r['polity_id']))), None)
        if polity is None:
            raise ValueError('王国不在该背景版本中')
        background = next(r for r in doc['content']['polities'] if str(r['id']) == str(polity['id']))
        return {'schema': 'background_town_context_v1', 'background_id': doc['id'],
                'version_id': version_id, 'background_year': doc['background_year'],
                'bundle_id': doc['bundle_id'], 'source': doc['source'],
                'polity': copy.deepcopy(polity), 'background': copy.deepcopy(background),
                'setting': doc['setting'], 'element_manifest': doc['element_manifest'],
                'geography': doc['geography'], 'approved_history': doc['approved_history'],
                'environment_query': {'bundle_id': doc['bundle_id'], 'expected_source': doc['source'],
                    'point': {'method': 'POST', 'path': '/api/inner/map-bundles/' + doc['bundle_id'] + '/point',
                              'body_fields': ['x_m', 'z_m', 'month']},
                    'window': {'method': 'POST', 'path': '/api/inner/map-bundles/' + doc['bundle_id'] + '/query',
                               'body_fields': ['fields', 'window', 'months']},
                    'coordinate_system': doc['geography'].get('coordinate_system'),
                    'grids': doc['geography']['grids'],
                    'constraint': 'Check current bundle identity against expected_source before querying; use each field native grid'},
                'historical_constraints': {'capital_region_id': polity.get('capital_region_id'),
                    'events': self._events(doc['simulation']),
                    'province_locations': [row for row in doc['simulation']['chronicle'].get('regions', [])
                        if row['id'] in polity['region_ids']],
                    'block_cells': doc['generation']['config']['block_cells'],
                    'location_semantics': 'capital and event regions are province-scale constraints, not exact town sites'},
                'settlements_generated': False, 'roads_generated': False}

    def revise(self, version_id):
        doc = self.get_version(version_id)
        stamp = now()
        content = copy.deepcopy(doc['content'])
        content['major_history_proposals'] = doc['approved_history'] + doc['unapproved_history']
        generation = doc['generation']
        elements = doc['element_manifest']['elements']
        candidates = [{'ref': r['ref'], 'namespace': r['namespace'], 'element_id': r['element_id'],
                       'version': r['version'], 'name': r['name'], 'tags': r.get('tags', [])}
                      for r in elements]
        draft = {'id': uid(), 'world_id': doc['id'], 'schema': 'world_background_draft_v1',
                 'kind': 'background', 'target': 'background', 'status': 'draft', 'stage': 'generated',
                 'revision': 1, 'created': stamp, 'updated': stamp, 'title': doc['title'],
                 'requirements': generation['requirements'], 'bundle_id': doc['bundle_id'],
                 'setting': doc['setting'], 'source': doc['source'], 'source_digest': doc['source_digest'],
                 'geography': doc['geography'], 'candidates': {'recommended': candidates, 'hinted': []},
                 'config': generation['config'], 'year': doc['background_year'],
                 'polity_preferences': generation['polity_preferences'],
                 'selection': {'refs': [r['ref'] for r in elements], 'elements': candidates},
                 'element_manifest': doc['element_manifest'], 'simulation': doc['simulation'],
                 'content': content, 'approved_history_ids': [r['id'] for r in doc['approved_history']],
                 'usage': {}, 'attempts': {}, 'notice': NOTICE, 'offline': generation['offline'],
                 'published': None, 'parent_version': version_id}
        self.service.store.put(KIND, draft['id'], draft)
        return draft
