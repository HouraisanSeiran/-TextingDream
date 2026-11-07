# -*- coding: utf-8 -*-
"""事件池：分级、逐日检查、确定性、遏制回落、玩家/作者投影、旧包不变。

全部用临时库与真实 ``Runtime.effects`` / ``pressure.advance``；不启服务、不碰 ``data/``、``saves/``。
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import events, pressure, quests
from app.storage import Store
from tests.fixtures_world import world_service
from tests.test_quests import story_with_quests

ROOT = Path(__file__).resolve().parents[1]
CAPITAL, PASS, OASIS, PORT, LANTERN = (
    'tianchao_capital', 'western_pass', 'crescent_oasis', 'western_port', 'south_lantern_port')
POLITIES = {CAPITAL: 'A', PASS: 'A', OASIS: 'B', PORT: 'B', LANTERN: 'C'}


def plague(**over):
    spec = {
        'id': 'plague', 'label': '黑死病', 'origin': CAPITAL, 'contagion': 1, 'hours_half': 100000,
        'max_towns': 5, 'contain_on': [{'flag': 'cure_found'}],
        'heard': {'small': '听说都城里倒下了几个人。', 'medium': '听说病从都城传到了关隘。',
                  'large': '听说病已经越过边境，传到了别的国家。', 'ended': '听说病终于退了。'},
        'notice': {'small': '都城传出疫病。', 'medium': '疫病蔓延到关隘。', 'large': '疫病跨过国境。',
                   'ended': '疫病平息。'},
        'on_level': {'medium': [{'op': 'signal', 'id': 'call_heroes'}]}}
    spec.update(over)
    return spec


def events_block(*specs, **over):
    block = {'version': 1, 'graph': 'story_locations', 'polities': dict(POLITIES),
             'events': list(specs) or [plague()]}
    block.update(over)
    return block


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = world_service(Store(Path(self.tmp.name) / 'e.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.base = self.rt.package()

    def build(self, block=None, quest_gate=True):
        """故事包 = 测试世界 + 任务（可由 call_heroes 信号开启）+ 事件池。"""
        story = story_with_quests(base=self.base['story'])
        if quest_gate:
            story['mechanics']['quests']['quests'][0]['enabled_on'] = {'signal': 'call_heroes'}
            story['mechanics']['quests']['quests'][0]['location'] = ''     # 不绑定地点：任何位置都能看到
        if block is not False:
            story['mechanics']['events'] = block or events_block()
        characters = copy.deepcopy(self.base['characters'])
        story['character_package_id'] = characters['id']
        self.rt.commit_package(story, characters, '事件池夹具')
        self.story, self.characters = story, characters
        return self.rt.new_session('事件池', 'protagonist')

    def advance(self, s, hours):
        pressure.advance(s, self.story, self.characters, hours, effects=self.rt.effects)

    def item(self, s, event_id='plague'):
        return s['event_pool']['items'][event_id]

    def levels(self, s, event_id='plague'):
        return [(row['kind'], row['to']) for row in self.item(s, event_id)['history']]


class LevelTests(Base):
    def test_spreads_day_by_day_small_medium_large(self):
        s = self.build()
        self.assertEqual(self.item(s)['status'], 'pending')
        self.advance(s, 24)
        self.assertEqual((self.item(s)['level'], self.item(s)['affected']), ('small', [CAPITAL]))
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'medium')          # 2 座城、同一国家
        self.assertEqual(sorted(self.item(s)['affected']), [CAPITAL, PASS])
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'large')           # 绿洲属于另一个国家
        self.assertEqual(self.levels(s), [('start', 'small'), ('rise', 'medium'), ('rise', 'large')])

    def test_one_advance_across_several_days_checks_every_day(self):
        one, step = self.build(), None
        step = copy.deepcopy(one)
        self.advance(one, 72)
        for _ in range(3):
            self.advance(step, 24)
        self.assertEqual(self.item(one)['history'], self.item(step)['history'])
        self.assertEqual(one['event_pool']['last_check'], 3)
        self.assertEqual(self.item(one)['level'], 'large')

    def test_thresholds_are_configurable(self):
        s = self.build(events_block(medium_towns=3, large_countries=3))
        self.advance(s, 48)
        self.assertEqual(self.item(s)['level'], 'small')           # 2 座城还不到 3
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'medium')          # 3 座城、仍只有 2 国
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'medium')

    def test_missing_polity_caps_at_medium_and_author_view_says_so(self):
        s = self.build(events_block(polities={}))
        self.advance(s, 24 * 5)
        self.assertEqual(self.item(s)['level'], 'medium')
        view = events.authority_view(s, self.story)
        self.assertTrue(view['events'][0]['country_missing'])
        self.assertEqual(view['events'][0]['countries'], [])
        self.assertIn('国家归属缺失', view['graph']['note'])

    def test_containment_lowers_the_level_and_ends_the_event(self):
        s = self.build()
        self.advance(s, 72)
        self.assertEqual(self.item(s)['level'], 'large')
        s['flags']['cure_found'] = True
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'medium')
        self.advance(s, 24)
        self.assertEqual(self.item(s)['level'], 'small')
        self.advance(s, 24)
        self.assertEqual(self.item(s)['status'], 'ended')
        self.assertEqual(self.levels(s)[3:], [('fall', 'medium'), ('fall', 'small'), ('end', None)])

    def test_natural_fade(self):
        s = self.build(events_block(plague(fade_after=4, contain_on=[])))
        self.advance(s, 24 * 3)
        self.assertEqual(self.item(s)['level'], 'large')
        self.advance(s, 24 * 5)
        self.assertEqual(self.item(s)['status'], 'ended')

    def test_max_active_limits_concurrent_events(self):
        specs = [plague(id='a', label='甲'), plague(id='b', label='乙'), plague(id='c', label='丙')]
        s = self.build(events_block(*specs, max_active=2))
        self.advance(s, 24)
        status = {k: v['status'] for k, v in s['event_pool']['items'].items()}
        self.assertEqual(sorted(status.values()), ['active', 'active', 'pending'])

    def test_start_gate(self):
        s = self.build(events_block(plague(start_on={'flag': 'omen'})))
        self.advance(s, 48)
        self.assertEqual(self.item(s)['status'], 'pending')
        s['flags']['omen'] = True
        self.advance(s, 24)
        self.assertEqual(self.item(s)['status'], 'active')

    def test_start_chance_default_is_certain_and_zero_never_starts(self):
        self.assertEqual(events.EventSpec.model_fields['start_chance'].default, 1.0)
        s = self.build()
        self.advance(s, 24)
        self.assertEqual(self.item(s)['status'], 'active')          # 不写 start_chance：行为同旧版
        s = self.build(events_block(plague(start_chance=0)))
        self.advance(s, 24 * 7)
        self.advance(s, 24 * 3)
        self.assertEqual(self.item(s)['status'], 'pending')
        self.assertEqual(self.item(s)['history'], [])

    def test_start_chance_range_is_validated(self):
        for bad in (-0.1, 1.5):
            with self.subTest(value=bad), self.assertRaises(Exception):
                self.build(events_block(plague(start_chance=bad)))

    def test_start_chance_is_deterministic_and_differs_between_seeds(self):
        block = events_block(plague(start_chance=0.5, contagion=0))
        first = {}
        for i in range(24):
            s = self.build(block)
            s['seed'] = 'sc-%d' % i
            self.advance(s, 24 * 6)
            first[i] = self.item(s)['history'][0]['check'] if self.item(s)['history'] else None
            again = copy.deepcopy(self.build(block))
            again['seed'] = 'sc-%d' % i
            self.advance(again, 24 * 6)
            self.assertEqual(self.item(s)['history'], self.item(again)['history'])
        started = [v for v in first.values() if v is not None]
        self.assertTrue(0 < len(started) <= 24)
        self.assertGreater(len(set(first.values())), 1, '不同 seed 的开始时刻应有差异')

    def test_only_the_area_near_the_player_is_simulated(self):
        s = self.build(events_block(radius_hours=1.5))
        self.advance(s, 24 * 6)
        self.assertEqual(sorted(self.item(s)['affected']), [CAPITAL, PASS])   # 绿洲在 2 小时外


class DeterminismTests(Base):
    def test_same_seed_same_result_and_rollback_copy_matches(self):
        block = events_block(plague(contagion=0.5, hours_half=2))
        s = self.build(block)
        snapshot = copy.deepcopy(s)                     # 回滚点
        for _ in range(2):                              # 单次推进上限 168 小时
            self.advance(s, 96)
        again = copy.deepcopy(snapshot)
        for _ in range(2):
            self.advance(again, 96)
        self.assertEqual(s['event_pool'], again['event_pool'])
        self.assertEqual([r['text'] for r in s['heard']], [r['text'] for r in again['heard']])
        self.assertTrue(s['event_pool']['items']['plague']['history'])

    def test_roll_depends_only_on_seed_event_day_edge(self):
        a = events.roll('seed', 'plague', 3, CAPITAL, PASS)
        self.assertEqual(a, events.roll('seed', 'plague', 3, CAPITAL, PASS))
        self.assertNotEqual(a, events.roll('seed2', 'plague', 3, CAPITAL, PASS))
        self.assertNotEqual(a, events.roll('seed', 'plague', 4, CAPITAL, PASS))
        self.assertTrue(0 <= a < 1)

    def test_probability_uses_kind_and_hours(self):
        spec = events.EventSpec(id='x', label='x', origin='a', contagion=0.8, hours_half=10)
        near = events.edge_probability(spec, {'hours': 1, 'kind': 'road'})
        far = events.edge_probability(spec, {'hours': 40, 'kind': 'road'})
        trail = events.edge_probability(spec, {'hours': 1, 'kind': 'trail'})
        self.assertGreater(near, far)
        self.assertGreater(near, trail)


class ProjectionTests(Base):
    def test_player_hears_unconfirmed_news_and_never_gets_facts(self):
        s = self.build()
        facts = len(s['facts'])
        self.advance(s, 24)
        heard = [r for r in s['heard'] if r['text'] == '听说都城里倒下了几个人。']
        self.assertEqual(len(heard), 1)
        self.assertEqual(heard[0]['distortion'], 1)
        self.assertEqual(heard[0]['source'], events.SOURCE)
        self.assertEqual(len(s['facts']), facts)

    def test_notice_appears_once_and_player_surface_hides_internals(self):
        s = self.build()
        self.rt._notice_begin(s, self.story)
        self.advance(s, 48)
        self.rt._notice_end(s, self.story)
        surface = self.rt.surface(s)
        self.assertEqual([(n['kind'], n['label']) for n in surface['event_notices']],
                         [('start', '黑死病'), ('rise', '黑死病')])
        self.assertTrue(all(set(n) == {'kind', 'label', 'text'} for n in surface['event_notices']))
        self.assertNotIn('event_notices', self.rt.surface(s))          # 只出现一次
        blob = json.dumps(self.rt.surface(s), ensure_ascii=False) + json.dumps(surface, ensure_ascii=False)
        for secret in ('event_pool', 'plague', 'affected', 'contagion', 'history'):
            self.assertNotIn(secret, blob)

    def test_author_view_sees_everything(self):
        s = self.build()
        self.advance(s, 72)
        view = events.authority_view(s, self.story)
        row = view['events'][0]
        self.assertEqual((row['id'], row['level'], row['status']), ('plague', 'large', 'active'))
        self.assertEqual(sorted(t['id'] for t in row['towns']), sorted([CAPITAL, OASIS, PASS]))
        self.assertEqual(row['countries'], ['A', 'B'])
        self.assertEqual([h['kind'] for h in row['history']], ['start', 'rise', 'rise'])
        self.assertEqual(view['next_check'], 4)
        self.assertEqual(view['next_check_at_hours'], 96)
        self.assertEqual(view['graph']['source'], 'story_locations')
        self.assertEqual(len(view['news']), 3)

    def test_level_up_signal_opens_the_quest(self):
        s = self.build()
        self.advance(s, 24)
        self.assertNotIn('call_heroes', s.get('signals', []))
        self.assertEqual(quests.available(s, self.story), [])
        self.advance(s, 24)
        self.assertIn('call_heroes', s['signals'])
        self.assertIn('escort', [r['quest_id'] for r in quests.available(s, self.story)])

    def test_delayed_hearing_by_distance(self):
        s = self.build(events_block(hear_delay_hours=1.0, radius_hours=10))
        s['location'] = PORT                  # 玩家在西港：都城在 3 小时外
        self.advance(s, 24)
        self.assertFalse([r for r in s['heard'] if r['source'] == events.SOURCE])
        self.advance(s, 24 * 3)
        self.assertTrue([r for r in s['heard'] if r['text'].startswith('听说都城里')])


class ValidationTests(Base):
    def check(self, block):
        story = story_with_quests(base=self.base['story'])
        story['mechanics']['quests']['quests'][0]['enabled_on'] = {'signal': 'call_heroes'}
        story['mechanics']['events'] = block
        return self.rt.validate_package(story, copy.deepcopy(self.base['characters']))

    def test_rejects_non_whitelisted_ops_and_confirmed_information(self):
        for effect in ({'op': 'fact', 'text': '凭空事实'}, {'op': 'take', 'id': 'x'},
                       {'op': 'reward', 'entry': 'escort_pay'}):
            with self.assertRaises(ValueError):
                self.check(events_block(plague(on_level={'small': [effect]})))
        with self.assertRaises(ValueError):
            self.check(events_block(plague(on_level={'small': [
                {'op': 'information', 'text': '确认', 'known_by': ['player'], 'confirmed': True}]})))

    def test_rejects_bad_references(self):
        with self.assertRaises(ValueError):
            self.check(events_block(plague(origin='nowhere')))
        with self.assertRaises(ValueError):
            self.check(events_block(polities={'nowhere': 'A'}))
        with self.assertRaises(ValueError):
            self.check(events_block(plague(on_level={'small': [{'op': 'signal', 'id': 'nobody_listens'}]})))
        with self.assertRaises(ValueError):
            self.check(events_block(plague(contain_on=[{'quest_done': 'no_such_quest'}])))
        with self.assertRaises(ValueError):
            self.check(events_block(plague(unknown_field=1)))
        with self.assertRaises(ValueError):
            self.check(events_block(plague(), plague()))

    def test_valid_block_passes(self):
        self.check(events_block(plague(contain_on=[{'quest_done': 'escort'}])))


class OldPackageTests(Base):
    def test_package_without_events_is_unchanged(self):
        s = self.build(False)
        self.assertNotIn('event_pool', s)
        self.advance(s, 72)
        self.assertNotIn('event_pool', s)
        self.rt._notice_begin(s, self.story)
        self.advance(s, 24)
        self.rt._notice_end(s, self.story)
        surface = self.rt.surface(s)
        self.assertNotIn('event_notices', surface)
        self.assertIsNone(events.authority_view(s, self.story))
        self.assertEqual(events.notices(None, s, self.story), [])


class QuestSurfaceTests(Base):
    def test_surface_quests_only_when_declared_and_hidden_ones_stay_hidden(self):
        s = self.build(False)
        self.assertEqual(self.rt.surface(s)['quests']['quests'], [])     # 声明了任务，但被信号锁着
        blob = json.dumps(self.rt.surface(s), ensure_ascii=False)
        for secret in ('送柴去磨坊', '磨坊主在清点货物', 'escort_pay'):
            self.assertNotIn(secret, blob)
        s['signals'] = ['call_heroes']
        rows = self.rt.surface(s)['quests']['quests']
        self.assertEqual([r['title'] for r in rows], ['送柴去磨坊'])
        self.assertNotIn('磨坊主在清点货物', json.dumps(rows, ensure_ascii=False))
        self.assertNotIn('secret', json.dumps(rows))

    def test_old_package_surface_has_no_quests_key(self):
        s = self.rt.new_session('旧包', 'protagonist')
        self.assertNotIn('quests', self.rt.surface(s))


SNAP_DIR = ROOT / 'saves' / 'map_imports'


@unittest.skipUnless(SNAP_DIR.is_dir() and list(SNAP_DIR.glob('*.civsnap')), '没有 civ 原件，跳过真实世界夹具')
class CivWorldTests(unittest.TestCase):
    """真实 civ-atlas 世界：原件复制到临时目录只读解码；起点 cell 8993（最近 8 城含国家 1/4/19/30）。"""

    @classmethod
    def setUpClass(cls):
        from app import civ_atlas_history as history, civ_atlas_snapshot as snapshot
        from app import civ_exploration, native_starts
        cls.tmp = tempfile.TemporaryDirectory()
        src = sorted(SNAP_DIR.glob('*.civsnap'))[0]
        local = Path(cls.tmp.name) / 'w.civsnap'
        local.write_bytes(src.read_bytes())
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
        cls.towns = story['mechanics']['exploration']['towns']
        cls.polities = civ_exploration.town_polities(civ, cls.towns, year)
        cls.origin = 'city_' + row['city_id'].split(':')[1]
        story['mechanics']['events'] = {
            'version': 1, 'radius_hours': None,
            'polities': {k: v for k, v in cls.polities.items() if v is not None},
            'events': [{'id': 'plague', 'label': '黑死病', 'origin': cls.origin, 'contagion': 0.9,
                        'hours_half': 300, 'max_towns': 8, 'contain_on': [{'flag': 'cure'}]}]}
        cls.story, cls.chars = story, chars

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        from app.service import Service
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.svc = Service(Store(Path(tmp.name) / 'c.sqlite3'), Path(tmp.name))
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.rt.commit_package(self.story, self.chars, 'civ 夹具')
        self.s = self.rt.new_session('t', 'protagonist')
        self.s['seed'] = 'civ-0'

    def advance(self, hours=24):
        pressure.advance(self.s, self.story, self.chars, hours, effects=self.rt.effects)

    def test_polity_mapping_has_distinct_countries_and_unowned_towns(self):
        owned = {v for v in self.polities.values() if v is not None}
        self.assertEqual(owned, {1, 4, 19, 30})
        self.assertIsNone(self.polities[self.origin])          # 无人地不计入国家

    def test_small_medium_large_then_containment_falls_back(self):
        for _ in range(3):
            self.advance()
        item = self.s['event_pool']['items']['plague']
        self.assertEqual([(r['kind'], r['to']) for r in item['history']],
                         [('start', 'small'), ('rise', 'medium'), ('rise', 'large')])
        self.assertGreaterEqual(item['history'][-1]['countries'], 2)
        self.s['flags']['cure'] = True
        for _ in range(8):
            self.advance()
        item = self.s['event_pool']['items']['plague']
        kinds = [r['kind'] for r in item['history']]
        self.assertIn('fall', kinds)
        self.assertEqual(item['status'], 'ended')

class TownDayPilotTests(unittest.TestCase):
    """铜杯镇的一天：两个小事件，各限一处，只有传闻与局势提示。"""

    def setUp(self):
        from tools.playable_scenes import town_day
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        from app.service import Service
        self.svc = Service(Store(Path(self.tmp.name) / 't.sqlite3'), Path(self.tmp.name))
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.data = town_day()
        self.rt.commit_package(self.data['story'], self.data['characters'], 'pilot')
        self.story, self.chars = self.data['story'], self.data['characters']

    def test_small_events_stay_in_one_town_and_only_become_hearsay(self):
        s = self.rt.new_session('t', 'protagonist')
        facts = len(s['facts'])
        for _ in range(5):
            pressure.advance(s, self.story, self.chars, 2, effects=self.rt.effects)
        items = s['event_pool']['items']
        for row in items.values():
            self.assertLessEqual(len(row['affected']), 1)
            self.assertTrue(all(h['to'] in (None, 'small') for h in row['history']))
        self.assertEqual(len(s['facts']), facts)
        self.assertTrue(any(r['source'] == events.SOURCE and r['distortion'] == 1 for r in s['heard']))
        self.assertEqual(s['local']['resources']['pence'], 18)

    def test_pilot_package_validates_and_player_surface_hides_internals(self):
        s = self.rt.new_session('t', 'protagonist')
        pressure.advance(s, self.story, self.chars, 12, effects=self.rt.effects)
        blob = json.dumps(self.rt.surface(s), ensure_ascii=False)
        for secret in ('event_pool', 'drunk_sleeper', 'lost_purse', 'affected'):
            self.assertNotIn(secret, blob)


if __name__ == '__main__':
    unittest.main()
