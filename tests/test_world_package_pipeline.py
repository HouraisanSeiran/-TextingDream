# -*- coding: utf-8 -*-
"""由地理 + 百科生成故事包（docs/world-package-pipeline.md）。

全部用临时目录与临时库；provider 离线或假 provider，不发真实模型请求。
真实 civsnap 用例只读 ``saves/map_imports/`` 下登记的文件与正式百科库的**副本**，文件不在则明确跳过并标记未验真。
"""
import ast
import asyncio
import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import encyclopedia as enc
from app import world_package_pipeline as wpp
from app import world_source as ws
from app.ai_drafts import DraftRejected
from app.storage import Store
from tests.fixtures_world import world_service

ROOT = Path(__file__).resolve().parents[1]
CIVSNAP = ROOT / 'saves/map_imports/989970517e07cd9f27ab0947cd7ad767.civsnap'
OFFICIAL_LIBRARY = ROOT / 'artifacts/human-encyclopedia/encyclopedia.sqlite3'
SECTIONS = {key: '文本' for key in ('definition', 'mechanism', 'conditions', 'exceptions',
                                   'story_uses', 'historical_scope', 'evidence_and_uncertainty')}
SETTING = {'genres': [{'tag': 'western_fantasy', 'weight': 3}, {'tag': 'historical', 'weight': 1}],
           'tech': 'medieval', 'magic': 'rare'}


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ 临时元素库
def el(ident, name, tags, tech=None, magic=None):
    return {'id': ident, 'name': name, 'summary': name + '的说明', 'tags': list(tags),
            'details': dict(SECTIONS), 'source_ids': ['s1'], 'tech_tier': tech,
            'magic_tier': magic}


LIB_ELEMENTS = [
    el('wheat', '冬小麦', ['kind:crop', 'genre:western_fantasy', 'terrain:farmland']),
    el('pine_resin', '松脂', ['kind:material', 'genre:historical', 'terrain:tundra']),
    el('elf', '林地精灵族', ['kind:race', 'genre:western_fantasy']),
    el('dwarf', '矮人氏族', ['kind:race', 'genre:western_fantasy', 'terrain:mountain']),
    el('steam_pump', '蒸汽泵', ['kind:machine', 'genre:western_fantasy'], tech='steam'),
    el('mage_guild', '法师行会', ['kind:organization', 'genre:western_fantasy'], magic='common'),
    el('coral', '红珊瑚', ['kind:material', 'genre:western_fantasy', 'terrain:ocean']),
    el('jade_elixir', '玉液丹', ['kind:elixir', 'genre:xianxia', 'terrain:mountain']),
    el('ale', '麦酒', ['kind:drink', 'genre:historical', 'terrain:workshop']),
]


def build_library(path):
    enc.import_document(path, {'schema_version': 1, 'status': 'candidate', 'group': 'testlib',
                               'sources': [{'id': 's1', 'title': 't', 'access': 'read'}],
                               'elements': LIB_ELEMENTS})


# ------------------------------------------------------------------ 最小假适配器
class FakeSource:
    """不依赖任何地图引擎的 WorldSource：三个国家、四块地、几条史事。"""

    def __init__(self, version='v1', extra_event=False):
        self.version = version
        self.extra_event = extra_event

    def identity(self):
        return {'engine': 'fake', 'world_id': 'fake-world', 'version': self.version,
                'content_hash': 'hash-' + self.version}

    def capabilities(self):
        return {'cells', 'terrains', 'settlements', 'polities', 'events'}

    def list_regions(self):
        return [{'region_id': 'r1', 'name': '北境三国', 'bbox': {}}]

    def region(self, region_id):
        if region_id != 'r1':
            raise ValueError('没有这个地区')
        ident = self.identity()
        cells = [
            {'cell_id': 'c1', 'lon': 10.0, 'lat': 50.0, 'is_sea': False, 'elevation_m': 120.0,
             'slope_deg': 2.0, 'relief_m': 80.0, 'dist_to_sea_km': 200.0, 'temperature_c': 10.0,
             'precipitation_mm': 700.0, 'area_km2': 1000.0, 'layers': {}, 'polity_id': 'pa'},
            {'cell_id': 'c2', 'lon': 11.0, 'lat': 51.0, 'is_sea': False, 'elevation_m': 1400.0,
             'slope_deg': 20.0, 'relief_m': 900.0, 'dist_to_sea_km': 300.0, 'temperature_c': 2.0,
             'precipitation_mm': 600.0, 'area_km2': 1000.0, 'layers': {}, 'polity_id': 'pb'},
            {'cell_id': 'c3', 'lon': 12.0, 'lat': 52.0, 'is_sea': False, 'elevation_m': 50.0,
             'slope_deg': 1.0, 'relief_m': 20.0, 'dist_to_sea_km': None, 'temperature_c': None,
             'precipitation_mm': None, 'area_km2': 1000.0, 'layers': {}, 'polity_id': 'pc'},
        ]
        polities = [
            {'polity_id': 'pa', 'name': '阿兰', 'in_region': True, 'form_hint': 'monarchy',
             'capital': {'settlement_id': 's1', 'name': '白塔城'},
             'territory': {'region_count': 3}},
            {'polity_id': 'pb', 'name': '贝罗斯', 'in_region': True, 'form_hint': 'republic',
             'capital': ws.missing('不知道'), 'territory': {'region_count': 2}},
            {'polity_id': 'pc', 'name': '卡多', 'in_region': True, 'form_hint': 'tribal',
             'capital': ws.missing('不知道'), 'territory': ws.missing('不知道')},
            {'polity_id': 'pd', 'name': '多兰', 'in_region': False, 'form_hint': ws.MISSING,
             'capital': ws.missing('外国'), 'territory': ws.missing('外国')},
        ]
        settlements = [
            {'settlement_id': 's1', 'name': '白塔城', 'level': 'capital', 'polity_id': 'pa',
             'cell_id': 'c1', 'lon': 10.0, 'lat': 50.0, 'founded': 100},
            {'settlement_id': 's2', 'name': '石桥镇', 'level': ws.MISSING, 'polity_id': 'pb',
             'cell_id': 'c2', 'lon': 11.0, 'lat': 51.0, 'founded': 300},
            {'settlement_id': 's3', 'name': '河口', 'level': ws.MISSING, 'polity_id': 'pc',
             'cell_id': 'c3', 'lon': 12.0, 'lat': 52.0, 'founded': 350},
        ]
        rows = [(120, 'found', ['pa'], '120年，阿兰立国'),
                (300, 'found', ['pb'], '300年，贝罗斯立国'),
                (412, 'war', ['pa', 'pb'], '412年，阿兰与贝罗斯开战'),
                (415, 'peace', ['pa', 'pb'], '415年，阿兰与贝罗斯议和'),
                (480, 'war', ['pc', 'pd'], '480年，卡多与多兰开战')]
        if self.extra_event:
            rows.append((500, 'famine', ['pc'], '500年，卡多发生饥荒'))
        events = [{'event_id': ws.make_event_id(ident, 'row/%d' % i), 'year': y, 'kind': k,
                   'actors': a, 'text': t, 'place': None} for i, (y, k, a, t) in enumerate(rows)]
        return ws.RegionSnapshot(
            region_id='r1', name='北境三国', bbox={}, cells=cells,
            terrains=ws.classify_cells(cells), settlements=settlements, polities=polities,
            events=events, source=ident,
            missing_fields={'cells.layers.river': '假适配器没有河网'}).validate()


class FakeProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def config(self):
        return {'offline': False, 'thinking_mode': 'disabled'}

    async def complete(self, system, context, json_mode=False, scope='', max_tokens=None,
                       thinking=None):
        self.calls += 1
        return copy.deepcopy(self.outputs.pop(0)), {'prompt_tokens': 1}

    def offline_trace(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError('online fake must not use offline trace')


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.library = self.dir / 'library.sqlite3'
        build_library(self.library)
        self.svc = world_service(Store(self.dir / 'state.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.svc.elements.configure(self.library, allowed_roots=[self.tmp.name])
        self.pipe = wpp.WorldPackagePipeline(self.svc)

    def tearDown(self):
        self.tmp.cleanup()

    def proposed(self, source=None):
        return self.pipe.propose(source or FakeSource(), 'r1', SETTING)

    def selected(self, source=None, refs=None):
        draft = self.proposed(source)
        refs = refs or [row['ref'] for row in draft['candidates']['recommended']]
        return self.pipe.select(draft['id'], refs, acknowledge_candidates=True)

    def generated(self, source=None):
        draft = self.selected(source)
        return run(self.pipe.generate(draft['id']))

    def packages(self):
        return sorted(p.name for p in self.svc.runtime.library.iterdir()
                      if p.name.startswith(('地区_', '.pending_')))


# ======================================================== 快照：确定、可复现、引擎无关
class SnapshotTests(Case):
    def test_repeated_snapshot_is_identical(self):
        a, b = FakeSource().region('r1'), FakeSource().region('r1')
        self.assertEqual(a.digest(), b.digest())
        self.assertEqual(ws.RegionSnapshot.from_dict(a.to_dict()).digest(), a.digest())
        self.assertEqual([e['event_id'] for e in a.events], [e['event_id'] for e in b.events])
        other = FakeSource(version='v2').region('r1')
        self.assertNotEqual(a.events[0]['event_id'], other.events[0]['event_id'])

    def test_missing_climate_is_marked_not_guessed(self):
        snap = FakeSource().region('r1')
        c3 = next(t for t in snap.terrains if t['cell_id'] == 'c3')
        self.assertTrue(any('降水' in m for m in c3['missing']))
        self.assertTrue(any('距海' in m for m in c3['missing']))
        self.assertTrue(ws.is_missing(snap.polities[2]['territory']))

    def test_bad_snapshot_is_refused(self):
        snap = FakeSource().region('r1')
        snap.events[0]['actors'] = ['nobody']
        with self.assertRaises(ws.SnapshotError):
            snap.validate()

    def test_pipeline_does_not_import_any_engine_module(self):
        banned = ('civ_atlas', 'map_import', 'terrain_source', 'world_source_civ_atlas',
                  'world_relief', 'map_source')
        for name in ('world_package_pipeline.py', 'world_source.py'):
            tree = ast.parse((ROOT / 'app' / name).read_text(encoding='utf-8'))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported += [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported += [(node.module or '')] + [alias.name for alias in node.names]
            hits = [m for m in imported if any(b in m for b in banned)]
            self.assertEqual(hits, [], name)


# ======================================================== 挑元素
class ElementTests(Case):
    def test_recommended_meet_tier_and_terrain(self):
        draft = self.proposed()
        rec = {row['element_id']: row for row in draft['candidates']['recommended']}
        hinted = {row['element_id'] for row in draft['candidates']['hinted']}
        union = set(draft['region']['terrain_union'])
        self.assertIn('farmland', union)
        self.assertIn('mountain', union)
        self.assertEqual(sorted(rec), ['dwarf', 'elf', 'wheat'])
        self.assertEqual(hinted, {'steam_pump', 'mage_guild'})    # 越档只提示
        for row in rec.values():
            self.assertEqual(row['tier_conflicts'], [])
            if row['terrains']:
                self.assertTrue(set(row['terrain_match']) <= union and row['terrain_match'])
        # 松脂（tundra 不在地区）、红珊瑚（ocean）、玉液丹（类型不符）、麦酒（作坊）都不推荐
        for eid in ('pine_resin', 'coral', 'jade_elixir', 'ale'):
            self.assertNotIn(eid, rec)

    def test_select_only_from_candidates_and_uses_assembly(self):
        draft = self.proposed()
        with self.assertRaises(wpp.WorldPackageError):
            self.pipe.select(draft['id'], ['testlib/coral'], acknowledge_candidates=True)
        with self.assertRaises(wpp.WorldPackageError):
            self.pipe.select(draft['id'], ['testlib/wheat'])
        out = self.pipe.select(draft['id'], ['testlib/wheat', 'testlib/steam_pump'],
                               acknowledge_candidates=True)
        self.assertEqual(out['element_manifest']['count'], 2)
        self.assertTrue(any('越档' in w for w in out['element_warnings']))

    def test_polity_templates_match_form_and_tier(self):
        draft = self.proposed()
        got = {m['polity_id']: (m['element_ref'], m['status']) for m in draft['polity_matches']}
        self.assertEqual(got['pa'], ('polities/polity_feudal_kingdom', 'matched'))
        self.assertEqual(got['pc'], ('polities/polity_tribal_confederation', 'matched'))
        # 共和国模板（工业共和国 steam、法师议会 magic:common）都越档 → 退到商业共和国
        self.assertEqual(got['pb'], ('polities/polity_merchant_republic', 'fallback'))
        self.assertNotIn('pd', got)                 # 不在地区内的国家不定政治


# ======================================================== 历史校验
class HistoryTests(Case):
    def checker(self):
        snap = FakeSource().region('r1')
        return snap, wpp.NarrativeChecker(snap.polity_list(), snap.event_list())

    def test_traceable_section_passes(self):
        snap, checker = self.checker()
        war, peace = snap.events[2]['event_id'], snap.events[3]['event_id']
        self.assertEqual(checker.check('s', '412年阿兰与贝罗斯交兵，415年两国议和。', [war, peace]),
                         [])

    def test_fake_event_id_is_refused(self):
        snap, checker = self.checker()
        errors = checker.check('s', '阿兰立国。', ['ev_doesnotexist'])
        self.assertTrue(any('不存在的事件' in e for e in errors))

    def test_country_not_in_cited_events_is_refused(self):
        snap, checker = self.checker()
        errors = checker.check('s', '412年阿兰与卡多开战。', [snap.events[2]['event_id']])
        self.assertTrue(any('卡多' in e for e in errors))

    def test_invented_year_or_dynasty_is_refused(self):
        snap, checker = self.checker()
        war = snap.events[2]['event_id']
        self.assertTrue(any('413' in e for e in checker.check('s', '413年阿兰与贝罗斯开战。', [war])))
        self.assertTrue(any('赤岩王国' in e for e in
                            checker.check('s', '412年阿兰与贝罗斯开战，赤岩王国趁机崛起。', [war])))

    def test_section_without_event_ids_is_refused(self):
        _, errors = wpp.normalize_history({'sections': [{'title': 't', 'text': '阿兰立国。',
                                                         'event_ids': []}]}, [])
        self.assertTrue(any('event_ids' in e for e in errors))

    def test_online_bad_output_retries_once_then_writes_nothing(self):
        draft = self.selected()
        before = self.svc.store.get(wpp.KIND, draft['id'])
        bad = {'sections': [{'title': '412年', 'text': '412年阿兰灭了多兰。',
                             'event_ids': ['ev_fake']}]}
        fake = FakeProvider([bad, bad])
        with patch.object(self.svc, 'provider', fake):
            with self.assertRaises(DraftRejected):
                run(self.pipe.generate(draft['id']))
        self.assertEqual(fake.calls, 2)
        self.assertEqual(self.svc.store.get(wpp.KIND, draft['id']), before)
        self.assertEqual(self.packages(), [])

    def test_online_retry_succeeds_on_second_attempt(self):
        draft = self.selected()
        events = draft['history_input']
        bad = {'sections': [{'title': '前史', 'text': '999年阿兰立国。',
                             'event_ids': [events[0]['event_id']]}]}
        good = wpp.offline_history(events)
        snap = FakeSource().region('r1')
        offline = run(self._offline_parts(draft))
        fake = FakeProvider([bad, good, offline['politics'], offline['setting']])
        with patch.object(self.svc, 'provider', fake):
            out = run(self.pipe.generate(draft['id']))
        self.assertEqual(fake.calls, 4)
        self.assertEqual(out['stage'], 'generated')
        self.assertEqual(len(out['attempts']['history']), 2)
        self.assertTrue(snap)

    async def _offline_parts(self, draft):
        other = self.pipe.select(self.proposed()['id'], draft['selection']['refs'],
                                 acknowledge_candidates=True)
        done = await self.pipe.generate(other['id'])
        return done['content']


# ======================================================== 全流程（离线）
class FlowTests(Case):
    def test_offline_end_to_end_draft_then_confirm(self):
        draft = self.generated()
        self.assertTrue(draft['offline'])
        self.assertEqual(draft['stage'], 'generated')
        self.assertEqual(draft['source'], FakeSource().identity())
        input_ids = {e['event_id'] for e in draft['history_input']}
        for section in draft['content']['history']['sections']:
            self.assertTrue(section['event_ids'])
            self.assertTrue(set(section['event_ids']) <= input_ids)
        self.assertEqual(draft['validation']['history_coverage']['share'], 1.0)
        refs = {p['polity_id']: p['element_ref'] for p in draft['content']['politics']['polities']}
        self.assertEqual(sorted(refs), ['pa', 'pb', 'pc'])
        selected = set(draft['selection']['refs'])
        for point in draft['content']['setting']['knowledge']:
            self.assertTrue(set(point['element_refs']) <= selected)
        for row in draft['content']['politics']['polities']:
            self.assertTrue(set(row['race_refs']) <= {'testlib/elf', 'testlib/dwarf'})

        self.assertEqual(self.packages(), [])          # 确认前不写故事包
        packages_before = len(self.svc.store.all('package'))
        done = self.pipe.confirm(draft['id'], FakeSource())
        self.assertEqual(done['status'], 'confirmed')
        folder = self.svc.runtime.library / done['confirmed']['folder']
        self.assertTrue((folder / 'story.json').exists())
        self.assertEqual(len(self.svc.store.all('package')), packages_before)   # 未启用
        story, characters = self.pipe.compile(done)
        self.assertEqual(story['worldview']['setting']['tech'], 'medieval')
        self.assertEqual(len(story['locations']), 3)
        history = [k for k in story['knowledge'] if k['id'].startswith('history_')]
        self.assertTrue(history and all(k['event_ids'] for k in history))

    def test_edit_with_invented_history_is_refused(self):
        draft = self.generated()
        content = copy.deepcopy(draft['content'])
        content['history']['sections'][0]['text'] += '后来阿兰建立了赤岩王朝。'
        with self.assertRaises(DraftRejected):
            self.pipe.edit(draft['id'], content)
        self.assertEqual(self.pipe.get(draft['id'])['revision'], draft['revision'])

    def test_setting_cannot_reference_unselected_element(self):
        draft = self.proposed()
        draft = self.pipe.select(draft['id'], ['testlib/wheat', 'testlib/elf'],
                                 acknowledge_candidates=True)
        draft = run(self.pipe.generate(draft['id']))
        content = copy.deepcopy(draft['content'])
        content['setting']['knowledge'][0]['element_refs'] = ['testlib/dwarf']
        with self.assertRaises(DraftRejected):
            self.pipe.edit(draft['id'], content)
        content = copy.deepcopy(draft['content'])
        content['setting']['overview'] += '山里住着矮人氏族。'
        with self.assertRaises(DraftRejected):
            self.pipe.edit(draft['id'], content)

    def test_stale_source_blocks_confirm(self):
        draft = self.generated()
        self.assertTrue(self.pipe.freshness(draft['id'], FakeSource(version='v2'))['stale'])
        self.assertTrue(self.pipe.freshness(draft['id'], FakeSource(extra_event=True))['stale'])
        with self.assertRaises(wpp.WorldPackageError):
            self.pipe.confirm(draft['id'], FakeSource(extra_event=True))
        self.assertEqual(self.packages(), [])
        self.assertFalse(self.pipe.freshness(draft['id'], FakeSource())['stale'])

    def test_offline_run_is_deterministic(self):
        a, b = self.generated(), self.generated()
        self.assertEqual(a['content'], b['content'])
        self.assertEqual(a['candidates'], b['candidates'])


# ======================================================== 真实 civsnap（本地产物缺失则明确 skip）
class RealCivAtlasTests(unittest.TestCase):
    def test_registered_world_region_end_to_end(self):
        missing=[str(path) for path in (CIVSNAP, OFFICIAL_LIBRARY) if not path.is_file()]
        if missing:
            self.skipTest('本地真实验收资料缺失（未验真）：%s' % '；'.join(missing))
        from app.world_source_civ_atlas import CivAtlasSource
        source = CivAtlasSource.from_path(CIVSNAP)
        regions = source.list_regions()
        self.assertTrue(regions)
        region_id = source.default_region_id()
        snap = source.region(region_id)
        again = CivAtlasSource.from_path(CIVSNAP).region(region_id)
        self.assertEqual(snap.digest(), again.digest())
        inside = snap.region_polities()
        self.assertTrue(2 <= len(inside) <= 4, [p['name'] for p in inside])
        self.assertTrue(snap.events)
        self.assertEqual(len({e['event_id'] for e in snap.events}), len(snap.events))

        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / 'library.sqlite3'
            shutil.copyfile(OFFICIAL_LIBRARY, library)      # 只读正式库：用副本
            svc = world_service(Store(Path(tmp) / 'state.sqlite3'), ROOT)
            svc.provider.configure({'offline': True})
            svc.elements.configure(library, allowed_roots=[tmp])
            pipe = wpp.WorldPackagePipeline(svc)
            draft = pipe.propose(source, region_id, SETTING)
            union = set(draft['region']['terrain_union'])
            self.assertTrue(draft['candidates']['recommended'])
            for row in draft['candidates']['recommended']:
                self.assertEqual(row['tier_conflicts'], [])
                if row['terrains']:
                    self.assertTrue(row['terrain_match'] and set(row['terrain_match']) <= union)
            refs = [row['ref'] for row in draft['candidates']['recommended']][:20]
            races = [row['ref'] for row in draft['candidates']['recommended']
                     if row['is_race']][:2]
            refs = list(dict.fromkeys(refs + races))
            draft = pipe.select(draft['id'], refs, acknowledge_candidates=True)
            draft = run(pipe.generate(draft['id']))
            self.assertEqual(draft['validation']['history_coverage']['share'], 1.0)
            for m in draft['polity_matches']:
                self.assertIsNotNone(m['element_ref'], m)
            story, _ = pipe.compile(draft)
            self.assertEqual(len(story['locations']), len(draft['city_plan']))
            self.__class__.report = wpp.summary(draft)
            print('\n[真实地区]', draft['region']['name'], draft['region']['counts'],
                  [p['name'] for p in inside], wpp.summary(draft))


if __name__ == '__main__':
    unittest.main()
