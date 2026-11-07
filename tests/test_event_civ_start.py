# -*- coding: utf-8 -*-
"""civ 开局接入事件库：默认开启、随机抽取、可关闭、整包校验、不泄露。

真实 civ 原件只读地复制到临时目录；全部用临时 SQLite，不碰 data/ saves/，不启服务。
起点 cell 8993（与 tests/test_event_content.py 相同）。
"""
import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from app import civ_atlas_history, civ_atlas_snapshot, event_library, events, native_starts, pressure
from app.service import Service
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = ROOT / 'saves' / 'map_imports'
HAVE_SNAP = SNAP_DIR.is_dir() and bool(list(SNAP_DIR.glob('*.civsnap')))
LIB_IDS = [spec['id'] for spec in event_library.event_specs('o', ['a'])]
# 任务 id（hero_hunt 等）按任务契约本来就出现在玩家任务列表里，不算事件泄露；这里只查事件本身。
LEAK_WORDS = LIB_IDS + ['event_pool', 'first_fever', 'contagion', 'affected']


class PickTests(unittest.TestCase):
    """纯函数：不需要原件。"""

    def test_same_seed_same_result_and_count_in_range(self):
        for i in range(50):
            seed = 'draft-%d' % i
            a = event_library.pick_event_ids(seed)
            self.assertEqual(a, event_library.pick_event_ids(seed))
            self.assertTrue(event_library.PICK_MIN <= len(a) <= event_library.PICK_MAX, a)
            self.assertEqual(len(a), len(set(a)))
            self.assertTrue(set(a) <= set(LIB_IDS))

    def test_different_seeds_give_different_combinations(self):
        combos = Counter(tuple(event_library.pick_event_ids('draft-%d' % i)) for i in range(300))
        counts = Counter(len(c) for c in combos.elements())
        picked = Counter(e for c in combos.elements() for e in c)
        print('\n[多种子统计] 300 个种子 → %d 种不同组合；数量分布 %s' % (len(combos), dict(sorted(counts.items()))))
        print('[多种子统计] 各事件被抽中次数 %s' % dict(sorted(picked.items())))
        self.assertGreater(len(combos), 250)
        self.assertEqual(set(counts), {5, 6, 7, 8})            # 数量四档都出现
        self.assertEqual(set(picked), set(LIB_IDS))             # 每个事件都有机会
        self.assertGreater(min(picked.values()), 100)           # 不偏向少数事件

    def test_bad_count_rejected(self):
        for bad in (0, 12, True, '5'):
            with self.assertRaises(ValueError):
                event_library.pick_event_ids('s', bad)

    def test_tools_wrapper_reexports(self):
        from tools import event_library as old
        self.assertIs(old.attach, event_library.attach)
        self.assertEqual(old.natures(), event_library.natures())

    def test_product_code_does_not_import_tools(self):
        # 只检查这条线上的文件（app/ai_drafts.py 等别的模块有自己的历史依赖，不在本任务范围）。
        for name in ('event_library.py', 'events.py', 'native_starts.py', 'civ_exploration.py'):
            text = (ROOT / 'app' / name).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(?m)^\s*(from|import)\s+tools\b', name)


@unittest.skipUnless(HAVE_SNAP, '没有 civ 原件')
class CivStartTests(unittest.TestCase):
    _loaded = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        src = sorted(SNAP_DIR.glob('*.civsnap'))[0]
        data = src.read_bytes()
        directory = root / 'map_imports'
        directory.mkdir()
        import hashlib
        digest = hashlib.sha256(data).hexdigest()
        name = '%s.civsnap' % digest[:32]
        (directory / name).write_bytes(data)
        manifest, parts = civ_atlas_snapshot.parse_container(data)
        civ = civ_atlas_history.decode_civ_part(manifest, parts)
        cls.world_id = manifest['world']['id']
        cls.year = civ['endYear']
        row = next(r for r in native_starts.settlements_at(civ, cls.year) if r['cell'] == 8993)
        cls.city_id = row['city_id']
        cls.record = {'id': 'sn_' + digest[:12], 'format': civ_atlas_snapshot.FORMAT,
                      'created': '2026-01-01T00:00:00+00:00', 'source': {'world_id': cls.world_id},
                      'file': name, 'sha256': digest, 'bytes': len(data), 'parts': [], 'stats': {}}
        cls.svc = Service(Store(root / 's.sqlite3'), root)
        cls.svc.provider.configure({'offline': True})
        cls.svc.store.put('map_import', cls.record['id'], cls.record)
        cls.store = cls.svc.store

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def request(self, **over):
        body = {'import_id': self.record['id'], 'source_sha256': self.record['sha256'],
                'world_id': self.world_id, 'branch': 'main', 'base_year': self.year,
                'city_id': self.city_id, 'start_cell': 8993, 'title': '周边探索',
                'premise': '从城镇出发。', 'exploration': True}
        body.update(over)
        return body

    def build(self, **over):
        doc, _ = native_starts.build_body(self.store, self.request(**over))
        story, chars = native_starts._story_and_characters(self.store, doc)
        return doc, story, chars

    # ------------------------------------------------------------ 开关
    def test_default_is_on_and_writes_events(self):
        doc, story, _ = self.build()
        self.assertIs(doc['random_events'], True)
        block = story['mechanics']['events']
        self.assertTrue(event_library.PICK_MIN <= len(block['events']) <= event_library.PICK_MAX)
        self.assertEqual([e['id'] for e in block['events']], event_library.pick_event_ids(doc['id']))
        self.assertTrue(block['polities'])                          # 城镇→国家

    def test_explicit_true_equals_default(self):
        doc, story, _ = self.build(random_events=True)
        self.assertIs(doc['random_events'], True)
        self.assertIn('events', story['mechanics'])

    def test_false_writes_nothing(self):
        doc, story, _ = self.build(random_events=False)
        self.assertIs(doc['random_events'], False)
        for key in ('events', 'quests', 'rewards'):
            self.assertNotIn(key, story['mechanics'])
        self.assertIn('exploration', story['mechanics'])

    def test_false_equals_plain_compile_region(self):
        from app import civ_exploration
        doc, story, chars = self.build(random_events=False)
        record = native_starts._record(self.store, doc['import_id'])
        civ, world = native_starts._world_and_civ(self.store, record)
        rows = native_starts.settlements_at(civ, doc['base_year'])
        base_story, base_chars = native_starts._story_and_characters(
            self.store, {**doc, 'exploration': False})
        again, again_chars = civ_exploration.compile_region(base_story, base_chars, civ, world, doc, rows)
        self.assertEqual(json.dumps(story, sort_keys=True), json.dumps(again, sort_keys=True))
        self.assertEqual(chars, again_chars)

    def test_non_bool_rejected(self):
        for bad in ('false', 'true', 0, 1, None, [], {}):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(ValueError, 'random_events 必须是布尔值'):
                    native_starts.build_body(self.store, self.request(random_events=bad))

    def test_legacy_draft_without_key_stays_off(self):
        doc, _, _ = self.build()
        legacy = {k: v for k, v in doc.items() if k != 'random_events'}
        _, story, _ = (legacy, *native_starts._story_and_characters(self.store, legacy))
        self.assertNotIn('events', story['mechanics'])

    def test_non_exploration_start_unchanged(self):
        doc, story, _ = self.build(exploration=False)
        self.assertNotIn('events', story['mechanics'])
        self.assertNotIn('exploration', story['mechanics'])

    # ------------------------------------------------------------ 确定性
    def test_same_draft_replays_identically(self):
        doc, story, _ = self.build()
        story2, _ = native_starts._story_and_characters(self.store, doc)
        self.assertEqual(json.dumps(story, sort_keys=True), json.dumps(story2, sort_keys=True))

    def test_different_drafts_pick_different_sets(self):
        sets = set()
        for _ in range(12):
            doc, story, _ = self.build()
            sets.add(tuple(e['id'] for e in story['mechanics']['events']['events']))
        print('\n[开局统计] 12 次真实开局 → %d 种不同组合' % len(sets))
        self.assertGreaterEqual(len(sets), 8)

    # ------------------------------------------------------------ 整包校验与悬空
    def test_no_dangling_references_for_many_seeds(self):
        _, story, _ = self.build()
        origin = story['mechanics']['exploration']['towns'][0]['id']
        specs_all = {s['id']: s for s in event_library.event_specs(origin, [t['id'] for t in
                     story['mechanics']['exploration']['towns'][1:]])}
        for i in range(120):
            picked = event_library.pick_event_ids('seed-%d' % i)
            fresh = copy.deepcopy(story)
            fresh['mechanics'].pop('events', None)
            fresh['mechanics'].pop('quests', None)
            fresh['mechanics'].pop('rewards', None)
            event_library.attach(fresh, origin, {}, only=picked)
            mech = fresh['mechanics']
            self.assertEqual([e['id'] for e in mech['events']['events']], picked)
            wanted = {g['quest_done'] for p in picked for g in specs_all[p]['contain_on'] if 'quest_done' in g}
            quest_ids = {q['id'] for q in mech.get('quests', {}).get('quests', [])}
            self.assertEqual(quest_ids, wanted)
            signals = {fx['id'] for e in mech['events']['events'] for fxs in e['on_level'].values()
                       for fx in fxs if fx['op'] == 'signal'}
            for q in mech.get('quests', {}).get('quests', []):
                self.assertIn(q['enabled_on']['signal'], signals, '任务的信号没有事件发出')
                for r in q['rewards']:
                    if r['kind'] == 'currency':
                        self.assertIn('rewards', mech)
            if 'rewards' in mech:
                self.assertTrue(any(r['kind'] == 'currency' for q in mech['quests']['quests']
                                    for r in q['rewards']), '奖励声明没有被引用')

    def test_whole_package_validates_for_several_starts(self):
        for i in range(6):
            doc, story, chars = self.build()
            with tempfile.TemporaryDirectory() as tmp:
                svc = Service(Store(Path(tmp) / 'c.sqlite3'), Path(tmp))
                svc.provider.configure({'offline': True})
                svc.runtime.commit_package(story, chars, '整包校验')     # 抛错即失败
                self.assertTrue(events.enabled(story))

    def test_attach_rejects_bad_only(self):
        _, story, _ = self.build()
        origin = story['mechanics']['exploration']['towns'][0]['id']
        for bad in (set(), {'nope'}):
            with self.assertRaises(ValueError):
                event_library.attach(copy.deepcopy(story), origin, {}, only=bad)

    # ------------------------------------------------------------ 玩家投影
    def test_player_surface_does_not_leak(self):
        doc, story, chars = self.build()
        with tempfile.TemporaryDirectory() as tmp:
            svc = Service(Store(Path(tmp) / 'c.sqlite3'), Path(tmp))
            svc.provider.configure({'offline': True})
            rt = svc.runtime
            rt.commit_package(story, chars, '投影')
            s = rt.new_session('t', 'protagonist')
            town_ids = [t['id'] for t in story['mechanics']['exploration']['towns']]
            for _ in range(14):
                pressure.advance(s, story, chars, 24, effects=rt.effects)
            self.assertTrue(s['event_pool']['items'])
            blob = json.dumps(rt.surface(s), ensure_ascii=False)
            for word in LEAK_WORDS + ['"small"', '"medium"', '"large"', '小事件', '中事件', '大事件']:
                self.assertNotIn(word, blob)
            hidden = json.dumps(s.get('heard', []), ensure_ascii=False)
            for word in LIB_IDS + ['event_pool']:
                self.assertNotIn(word, hidden)
            for town in town_ids:
                self.assertNotIn(town, json.dumps(rt.surface(s).get('event_notices', []), ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
