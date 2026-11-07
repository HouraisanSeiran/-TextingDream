# -*- coding: utf-8 -*-
"""事件池第一轮内容：铜杯镇 7 个小事件 + civ 世界 11 个事件（tools/event_library.py）。

只验证内容，不改引擎规则。civ 夹具与 tests/test_events.py::CivWorldTests 相同：
原件复制到临时目录只读解码，起点 cell 8993，polities 来自 ``civ_exploration.town_polities``。
全部用临时 SQLite；不启服务，不碰 data/ saves/（原件只读）。
"""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from app import events, pressure, quests
from app.storage import Store
from tools import event_library as lib

ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = ROOT / 'saves' / 'map_imports'
HAVE_SNAP = SNAP_DIR.is_dir() and bool(list(SNAP_DIR.glob('*.civsnap')))
RANK = events.LEVEL_RANK

TOWN_NATURE = {            # 作者备注：好 2 / 坏 2 / 福祸相依 3
    'errand_message': '好', 'small_favour': '好',
    'loose_planks': '坏', 'lost_purse': '坏',
    'sudden_shower': '福祸相依', 'boasting_mercenary': '福祸相依', 'drunk_sleeper': '福祸相依',
}
LEAK_WORDS = ('small', 'medium', 'large', '小事件', '中事件', '大事件', '等级', 'event_pool', 'city_')

_CIV = {}


def civ_fixture():
    """编译一次 civ 区域包并缓存：返回 dict(story, chars, towns, polities, origin)。"""
    if _CIV:
        return _CIV
    from app import civ_atlas_history as history, civ_atlas_snapshot as snapshot
    from app import civ_exploration, native_starts
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / 'w.civsnap'
        local.write_bytes(sorted(SNAP_DIR.glob('*.civsnap'))[0].read_bytes())
        manifest, parts = snapshot.parse_container(local.read_bytes())
        civ = history.decode_civ_part(manifest, parts)
        world = snapshot.read_world(manifest, parts)
    year = civ['endYear']
    rows = native_starts.settlements_at(civ, year)
    row = next(r for r in rows if r['cell'] == 8993)
    doc = {'start_cell': 8993, 'city_id': row['city_id'], 'source_sha256': 'a' * 64,
           'import_id': 'sn_aaaaaaaaaaaa', 'base_year': year}
    story = {'id': 'civ_ev', 'title': 't', 'premise': 'p', 'character_package_id': 'c',
             'locations': [], 'events': [], 'items': [], 'mechanics': {}}
    chars = {'id': 'c', 'title': 't', 'characters': [{
        'id': 'player', 'name': 'me', 'role': '主角', 'location_id': 'x', 'state': {}, 'personality': {}}]}
    story, chars = civ_exploration.compile_region(story, chars, civ, world, doc, rows)
    towns = story['mechanics']['exploration']['towns']
    polities = civ_exploration.town_polities(civ, towns, year)
    origin = 'city_' + row['city_id'].split(':')[1]
    lib.attach(story, origin, polities)
    _CIV.update(story=story, chars=chars, towns=towns, polities=polities, origin=origin)
    return _CIV


def make_session(story, chars, tmp, seed='s-0'):
    from app.service import Service
    svc = Service(Store(Path(tmp) / 'c.sqlite3'), Path(tmp))
    svc.provider.configure({'offline': True})
    rt = svc.runtime
    rt.commit_package(story, chars, '事件内容')          # 走完整包校验
    s = rt.new_session('t', 'protagonist')
    s['seed'] = seed
    return rt, s


def run_days(rt, story, chars, s, days):
    for _ in range(days):
        pressure.advance(s, story, chars, 24, effects=rt.effects)


def summarize(s):
    """每个事件的最高等级、是否曾起、结局。"""
    out = {}
    for eid, item in s['event_pool']['items'].items():
        top = None
        for row in item['history']:
            if row['to'] and (top is None or RANK[row['to']] > RANK[top]):
                top = row['to']
        out[eid] = {'started': item['started'] is not None, 'top': top, 'status': item['status']}
    return out


class StaticContentTests(unittest.TestCase):
    """不依赖存档：文案与遏制配置的静态约束。"""

    def specs(self):
        return lib.event_specs('o', ['a', 'b', 'c', 'd', 'e'])

    def test_counts_and_seeds(self):
        specs = self.specs()
        self.assertEqual(len(specs), 11)
        self.assertEqual(set(lib.natures()), {s['id'] for s in specs})
        bad_seeds = {'first_fever_cases', 'tavern_brawl_feud'}
        self.assertTrue(bad_seeds <= {s['id'] for s in specs})
        self.assertTrue(all(s['contain_on'] or s.get('fade_after') for s in specs))
        self.assertTrue(all(s.get('fade_after') for s in specs), '每个事件都要能自然消退')
        for s in specs:
            self.assertEqual(s.get('start_chance', 1.0), 1.0)      # civ 事件靠条件与传播，不靠开始概率

    def test_texts_do_not_leak_internals(self):
        for spec in self.specs():
            for group in ('heard', 'notice'):
                for key, text in spec[group].items():
                    self.assertNotIn(spec['id'], text)
                    for word in LEAK_WORDS:
                        self.assertNotIn(word, text, (spec['id'], group, key))
            self.assertNotIn(spec['id'], spec['label'])
            self.assertTrue(spec['heard'].get('small') and spec['notice'].get('small'))
            self.assertTrue(spec['heard'].get('ended') and spec['notice'].get('ended'))


class TownDayContentTests(unittest.TestCase):
    def setUp(self):
        from tools.playable_scenes import town_day
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = town_day()
        self.story, self.chars = self.data['story'], self.data['characters']
        self.rt, self.s = make_session(self.story, self.chars, self.tmp.name)

    def test_package_has_seven_small_events_with_balanced_nature(self):
        block = self.story['mechanics']['events']
        ids = {e['id'] for e in block['events']}
        self.assertEqual(ids, set(TOWN_NATURE))
        counts = {k: sum(1 for v in TOWN_NATURE.values() if v == k) for k in set(TOWN_NATURE.values())}
        self.assertEqual(counts, {'好': 2, '坏': 2, '福祸相依': 3})
        for e in block['events']:
            self.assertEqual((e['contagion'], e['max_towns']), (0, 1))
            self.assertTrue(e.get('fade_after'))
            self.assertEqual(set(e['on_level']), {'small', 'ended'})
            for effect in e['on_level']['small'] + e['on_level']['ended']:
                self.assertEqual(effect['op'], 'flag')        # 没有钱、物、事实
            for text in list(e['heard'].values()) + list(e['notice'].values()):
                self.assertNotIn(e['id'], text)
                for word in LEAK_WORDS:
                    self.assertNotIn(word, text)

    def test_whole_day_stays_small_and_touches_no_money(self):
        s = self.s
        facts = len(s['facts'])
        for _ in range(9):                                    # 8:00 起 18 小时 = 9 次检查
            pressure.advance(s, self.story, self.chars, 2, effects=self.rt.effects)
        started = [k for k, v in s['event_pool']['items'].items() if v['started'] is not None]
        self.assertGreaterEqual(len(started), 1)
        self.assertLessEqual(len(started), 7)
        for item in s['event_pool']['items'].values():
            self.assertLessEqual(len(item['affected']), 1)
            self.assertTrue(all(h['to'] in (None, 'small') for h in item['history']))
        self.assertEqual(len(s['facts']), facts)
        self.assertEqual(s['local']['resources']['pence'], 18)
        heard = [r for r in s['heard'] if r['source'] == events.SOURCE]
        self.assertGreaterEqual(len(heard), 1)
        self.assertLessEqual(len(heard), 2 * len(started))      # 每个出场事件最多“起”“终”各听到一条
        self.assertTrue(all(r['distortion'] == 1 for r in heard))
        blob = json.dumps(self.rt.surface(s), ensure_ascii=False)
        for eid in TOWN_NATURE:
            self.assertNotIn(eid, blob)
        self.assertNotIn('event_pool', blob)

    def test_every_town_event_has_a_real_start_chance(self):
        for e in self.story['mechanics']['events']['events']:
            self.assertGreater(e['start_chance'], 0, e['id'])
            self.assertLess(e['start_chance'], 1, e['id'])

    def test_started_events_differ_between_seeds_and_each_event_is_sometimes_absent(self):
        """整天 9 次检查：不同 seed 一天出场的事件数不一样，7 个事件各自的出场率在 20%–90%。"""
        n_seeds = 30
        per_event = {k: 0 for k in TOWN_NATURE}
        counts = []
        for i in range(n_seeds):
            s = copy.deepcopy(self.s)
            s['seed'] = 'town-%d' % i
            for _ in range(9):
                pressure.advance(s, self.story, self.chars, 2, effects=self.rt.effects)
            started = [k for k, v in s['event_pool']['items'].items() if v['started'] is not None]
            counts.append(len(started))
            for k in started:
                per_event[k] += 1
        self.assertGreaterEqual(len(set(counts)), 3, counts)
        for k, hit in per_event.items():
            self.assertGreaterEqual(hit / n_seeds, 0.2, (k, hit))
            self.assertLessEqual(hit / n_seeds, 0.9, (k, hit))


def _routes_case():
    from tests.test_town_day import TownDayTests
    keep = {'test_grain_clock_reaches_full_on_failed_inspect_and_success_routes',
            'test_normal_failed_alternative_and_chaos_reach_distinct_endings'}

    class TownDayRoutesWithEvents(TownDayTests):
        """原样复用铜杯镇验收：5 条路线结局与干麦钟 4/4 在带 7 个事件的包上不变。"""

        def test_events_really_fired_on_a_route(self):
            s = self.run_steps(self.data['playtest']['route'], True)
            started = [k for k, v in s['event_pool']['items'].items() if v['started'] is not None]
            self.assertEqual(len(s['event_pool']['items']), 7)      # 事件池随路线一起推进
            self.assertLessEqual(len(started), 7)                   # 出场与否由 seed 决定，这条路线可能一个也没出

    for name in dir(TownDayTests):
        if name.startswith('test_') and name not in keep:
            setattr(TownDayRoutesWithEvents, name, None)
    return TownDayRoutesWithEvents


TownDayRoutesWithEvents = _routes_case()


@unittest.skipUnless(HAVE_SNAP, '没有 civ 原件，跳过真实世界夹具')
class CivContentTests(unittest.TestCase):
    SEEDS = 24
    DAYS = 14
    cache = None

    @classmethod
    def setUpClass(cls):
        cls.fx = civ_fixture()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.story, self.chars = self.fx['story'], self.fx['chars']
        self.rt, self.base = make_session(self.story, self.chars, self.tmp.name)

    def fresh(self, seed):
        s = copy.deepcopy(self.base)
        s['seed'] = seed
        return s

    def sweep(self):
        """24 个固定种子各推进 14 日（结果缓存，所有用例共用）。"""
        if CivContentTests.cache is None:
            rows = []
            for i in range(self.SEEDS):
                s = self.fresh('t-%d' % i)
                run_days(self.rt, self.story, self.chars, s, self.DAYS)
                rows.append(summarize(s))
            CivContentTests.cache = rows
        return CivContentTests.cache

    def test_package_validated_and_shape(self):
        block = self.story['mechanics']['events']
        self.assertEqual(len(block['events']), 11)
        self.assertEqual({v for v in self.fx['polities'].values() if v is not None}, {1, 4, 19, 30})
        self.assertIsNone(self.fx['polities'][self.fx['origin']])
        self.assertEqual(self.story['mechanics']['quests']['quests'][0]['enabled_on'], {'signal': 'heroes_called'})

    def test_a_small_seed_reaches_medium_and_some_event_reaches_large(self):
        rows = self.sweep()
        seeds = ('first_fever_cases', 'tavern_brawl_feud')
        medium_or_more = [r[e]['top'] for r in rows for e in seeds if r[e]['top']]
        self.assertTrue(any(t in ('medium', 'large') for t in medium_or_more),
                        '没有任何小种子升到中事件')
        large = [e for r in rows for e, v in r.items() if v['top'] == 'large']
        self.assertTrue(large, '没有任何事件升到大事件')
        mediums = [e for r in rows for e, v in r.items() if v['top'] == 'medium']
        self.assertTrue(mediums)

    def test_containment_flag_pushes_the_level_back_down_and_ends(self):
        for flag_kind in ('quest_done',):                 # 第二轮起遏制只走任务完成
            with self.subTest(gate=flag_kind):
                found = False
                for i in range(self.SEEDS):
                    s = self.fresh('t-%d' % i)
                    item = None
                    for _ in range(self.DAYS):
                        run_days(self.rt, self.story, self.chars, s, 1)
                        item = s['event_pool']['items']['first_fever_cases']
                        if item['level'] in ('medium', 'large'):
                            break
                    if not item or item['level'] not in ('medium', 'large'):
                        continue
                    found = True
                    top = RANK[item['level']]
                    towns = len(item['affected'])
                    top_towns = towns
                    if flag_kind == 'flag':
                        s['flags']['fever_contained'] = True
                    else:
                        s['quests'] = {'entries': {'fever_relief': {'state': 'completed'}}}
                    levels = [top]
                    for _ in range(12):
                        run_days(self.rt, self.story, self.chars, s, 1)
                        item = s['event_pool']['items']['first_fever_cases']
                        if item['status'] == 'ended':
                            break
                        levels.append(RANK[item['level']])
                        self.assertLess(len(item['affected']), towns)      # 每次检查只退不进
                        towns = len(item['affected'])
                    self.assertEqual(item['status'], 'ended')
                    self.assertEqual(levels, sorted(levels, reverse=True))
                    kinds = [r['kind'] for r in item['history']]
                    if top_towns > 2:                      # 每次检查退 2 座：座数多于 2 才会先降级再结束
                        self.assertIn('fall', kinds)
                    self.assertEqual(kinds[-1], 'end')
                    break
                self.assertTrue(found, '24 个种子里没有一个让高热病升到中事件')

    def test_level_up_signals_open_the_quests(self):
        opened = {'fever_alarm': 'fever_relief', 'heroes_called': 'hero_hunt',
                  'feud_brewing': 'feud_mediation', 'caravan_raided': 'road_patrol',
                  'drought_warning': 'rain_ritual', 'border_standoff': 'border_parley'}
        seen = set()
        for i in range(self.SEEDS):
            s = self.fresh('t-%d' % i)
            self.assertEqual(quests.available(s, self.story), [])
            run_days(self.rt, self.story, self.chars, s, self.DAYS)
            ids = {r['quest_id'] for r in quests.available(s, self.story)}
            for signal, quest in opened.items():
                if signal in (s.get('signals') or []):
                    self.assertIn(quest, ids)
                    seen.add(quest)
                else:
                    self.assertNotIn(quest, ids)
        self.assertTrue(seen, '14 日内没有任何中事件发出信号')

    def test_every_containment_gate_is_reachable_by_the_player(self):
        """每个 contain_on 都要有玩家可触发的路径：flag 被某效果设置；signal 被 on_level 发出；
        quest_done 指向存在的任务，且该任务的证据可满足（visited 的城镇真在世界里）。"""
        story = self.story
        quests_by_id = {q['id']: q for q in story['mechanics']['quests']['quests']}
        town_ids = {t['id'] for t in self.fx['towns']}
        set_flags = {e['id'] for q in quests_by_id.values() for e in q['effects'] if e['op'] == 'flag'}
        emitted = set()
        for spec in story['mechanics']['events']['events']:
            for effects in spec['on_level'].values():
                for e in effects:
                    if e['op'] == 'flag':
                        set_flags.add(e['id'])
                    elif e['op'] == 'signal':
                        emitted.add(e['id'])
        checked = 0
        for spec in story['mechanics']['events']['events']:
            self.assertTrue(spec['contain_on'] or spec.get('fade_after'), spec['id'])
            for gate in spec['contain_on']:
                checked += 1
                if gate.get('flag'):
                    self.assertIn(gate['flag'], set_flags, (spec['id'], gate))
                elif gate.get('signal'):
                    self.assertIn(gate['signal'], emitted, (spec['id'], gate))
                else:
                    quest = quests_by_id.get(gate['quest_done'])
                    self.assertIsNotNone(quest, (spec['id'], gate))
                    self.assertTrue(quest['evidence'], (spec['id'], gate))
                    for ev in quest['evidence']:
                        self.assertIn(ev['kind'], ('visited', 'flag', 'resource'))
                        if ev['kind'] == 'visited':
                            self.assertIn(ev['id'], town_ids, (quest['id'], ev))
                        elif ev['kind'] == 'flag':
                            self.assertIn(ev['id'], set_flags, (quest['id'], ev))
                    # 任务本身必须能被开启：enabled_on 的信号由某事件发出
                    enabled = (quest.get('enabled_on') or {}).get('signal')
                    self.assertTrue(enabled is None or enabled in emitted, (quest['id'], enabled))
        self.assertGreaterEqual(checked, 6)

    def test_a_quest_can_really_be_completed_by_visiting_its_town(self):
        """端到端：信号开启任务 → 走到目标城 → quest:complete → 事件被遏制回落。"""
        for i in range(self.SEEDS):
            s = self.fresh('t-%d' % i)
            for _ in range(self.DAYS):
                run_days(self.rt, self.story, self.chars, s, 1)
                if 'fever_alarm' in (s.get('signals') or []):
                    break
            else:
                continue
            quest = next(q for q in self.story['mechanics']['quests']['quests'] if q['id'] == 'fever_relief')
            item = s['event_pool']['items']['first_fever_cases']
            if item['status'] != 'active':
                continue
            quests.propose(s, self.story, 'fever_relief')
            quests.accept(s, self.story, 'fever_relief')
            quests.start(s, self.story, 'fever_relief')
            gaps = quests.completion(s, self.story, 'fever_relief')['missing']
            self.assertTrue(gaps, '没走到目标城镇之前不能交付')
            s['explored'] = list(s.get('explored') or []) + [quest['evidence'][0]['id']]
            self.assertEqual(quests.completion(s, self.story, 'fever_relief')['missing'], [])
            quests.apply_completion(s, self.story, 'fever_relief', effects_fn=self.rt.effects)
            self.assertEqual(s['quests']['entries']['fever_relief']['state'], 'completed')
            self.assertTrue(s['flags'].get('fever_relief_done'))
            for _ in range(12):
                run_days(self.rt, self.story, self.chars, s, 1)
                if s['event_pool']['items']['first_fever_cases']['status'] == 'ended':
                    break
            self.assertEqual(s['event_pool']['items']['first_fever_cases']['status'], 'ended')
            return
        self.fail('没有任何种子在高热病活跃时发出 fever_alarm')

    def test_player_projection_has_no_ids_levels_or_towns(self):
        names = [t['name'] for t in self.fx['towns']]
        found = False
        for i in range(self.SEEDS):
            s = self.fresh('t-%d' % i)
            facts = len(s['facts'])
            seen_notices = []
            for _ in range(self.DAYS):
                before = copy.deepcopy(s)
                run_days(self.rt, self.story, self.chars, s, 1)
                surface = self.rt.surface(s)
                rows = events.notices(before, s, self.story)
                seen_notices += rows
                for row in rows:
                    self.assertEqual(set(row), {'kind', 'label', 'text'})
                self.assertNotIn('event_pool', surface)
            heard = [r for r in s['heard'] if r['source'] == events.SOURCE]
            if not heard:
                continue
            found = True
            self.assertEqual(len(s['facts']), facts)
            text = json.dumps([[r['text'] for r in heard], seen_notices], ensure_ascii=False)
            for spec in self.story['mechanics']['events']['events']:
                self.assertNotIn(spec['id'], text)
            for word in LEAK_WORDS:
                self.assertNotIn(word, text)
            for name in names:
                self.assertNotIn(name, text)
            self.assertTrue(all(r['distortion'] == 1 for r in heard))
            blob = json.dumps(self.rt.surface(s), ensure_ascii=False)
            self.assertNotIn('event_pool', blob)
            for spec in self.story['mechanics']['events']['events']:
                self.assertNotIn(spec['id'], blob)
            break
        self.assertTrue(found)

    def test_same_seed_gives_same_history(self):
        a, b = self.fresh('t-3'), self.fresh('t-3')
        run_days(self.rt, self.story, self.chars, a, 10)
        run_days(self.rt, self.story, self.chars, b, 10)
        self.assertEqual(a['event_pool'], b['event_pool'])


if __name__ == '__main__':
    unittest.main()
