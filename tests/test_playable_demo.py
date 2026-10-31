# -*- coding: utf-8 -*-
"""可试玩 Demo 的严格单测：特质 / 起点 / 压力 / 自由行动 / 结局。

每条测试对应一次评审要求。全部离线、临时目录，不碰正式 data/ 与已发布包。
"""
import asyncio
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app import endings as E
from app import free_actions as F
from app import pressure as P
from app import start_profiles as SP
from app import traits as T
from app.contracts import Turn
from app.service import Service
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ('definition', 'mechanism', 'conditions', 'exceptions', 'story_uses',
            'historical_scope', 'evidence_and_uncertainty')


# --------------------------------------------------------------------- 构件
def payload(ident, name, tags=('trait', 'trait.public'), text=None, **extra):
    body = text or '%s：先问清条件再决定，说得出来的只有这些动作。' % name
    out = {'id': ident, 'name': name, 'summary': name + '的一句话摘要',
           'details': {section: body for section in SECTIONS},
           'tags': list(tags), 'aliases': [], 'review_status': 'needs_review'}
    out.update(extra)
    return out


def snapshot(items):
    return {'version': 1, 'namespace': T.NAMESPACE, 'locked_note': '测试快照',
            'templates': [T.build_template(item, 1) for item in items]}


def traits_snapshot():
    return snapshot([
        payload('trait_careful', '先问后动'),
        payload('trait_public_plain', '说话直'),
        payload('trait_secret_owe', '记着一笔旧债', tags=('trait', 'trait.hidden')),
    ])


def rewards_block():
    return {'version': 1,
            'currencies': [{'id': 'coin', 'name': '铜币', 'unit': '枚', 'maximum': 500}],
            'materials': [{'id': 'wood', 'name': '杉木', 'damage_bonus': 0,
                           'value_percent': 100, 'weight_percent': 100,
                           'shapes': ['token']}],
            'shapes': [{'id': 'token', 'name': '木牌', 'base_damage': 0, 'base_value': 10,
                        'base_weight': 1, 'base_durability': 20, 'mana_capacity': 0}],
            'qualities': [{'id': 'plain', 'name': '寻常', 'value_percent': 100,
                           'durability_percent': 100, 'enchant_budget': 0}],
            'templates': [{'id': 'pass_token', 'name': '渡口木牌', 'material': 'wood',
                           'shape': 'token', 'quality': 'plain'}],
            'rewards': [{'id': 'token_grant', 'kind': 'item',
                         'templates': ['pass_token']}],
            'max_grants_per_event': 2, 'max_value_per_grant': 500, 'max_items': 8}


def pressure_block(lift_and_burst_same_hour=True):
    stages = [
        {'id': 'warn', 'at_hours': 9, 'kind': 'warning',
         'effects': [{'op': 'flag', 'id': 'warned', 'value': True}],
         'known_by': ['player'], 'public_text': '水位一夜涨了两尺'},
        {'id': 'burst', 'at_hours': 10, 'kind': 'trigger',
         'when': {'not_flags': ['lifted']},
         'effects': [{'op': 'flag', 'id': 'convoy_lost', 'value': True}]},
        {'id': 'resolve_grain', 'at_hours': 11, 'kind': 'resolution',
         'when': {'all_flags': {'grain_secured': True}},
         'effects': [{'op': 'flag', 'id': 'grain_saved', 'value': True}]},
        {'id': 'late_note', 'at_hours': 12, 'kind': 'warning',
         'when': {'all_flags': {'late_mark': True}},
         'known_by': ['player'], 'public_text': '夜里有灯从上游下来'},
    ]
    if lift_and_burst_same_hour:
        stages.insert(2, {'id': 'lift', 'at_hours': 10, 'kind': 'lift',
                          'effects': [{'op': 'flag', 'id': 'lifted', 'value': True}]})
    return {'version': 1, 'pressures': [{'id': 'flood', 'title': '汛情',
                                        'stages': stages}]}


def endings_block():
    return {'version': 1, 'endings': [
        {'id': 'ending_saved', 'title': '保粮', 'kind': 'saved', 'priority': 50,
         'summary': '闸门压到最后一刻，下游田亩被淹。',
         'condition': {'all_flags': {'grain_secured': True},
                       'not_flags': ['sluice_opened', 'convoy_lost']}},
        {'id': 'ending_opened', 'title': '开闸', 'kind': 'traded', 'priority': 40,
         'summary': '人保住，粮损大半。',
         'condition': {'all_flags': {'sluice_opened': True},
                       'not_flags': ['grain_secured', 'convoy_lost']}},
        {'id': 'ending_lost', 'title': '全失', 'kind': 'lost', 'priority': 30,
         'summary': '粮队与仓都没保住，仍可继续收拾。',
         'condition': {'all_flags': {'convoy_lost': True},
                       'not_flags': ['grain_secured', 'sluice_opened']},
         'continue_event': 'rebuild'},
    ]}


def start_block():
    return {'version': 1, 'profiles': [
        {'id': 'townsfolk', 'title': '本地居民', 'summary': '在米市街长大的人。',
         'identity': '米市街的本地居民', 'location': 'plaza',
         'explored': ['gate'], 'items': ['rope'], 'wallet': {'coin': 30},
         'reward_items': ['pass_token'],
         'relations': {'keeper': {'trust': 0.6, 'note': '打过交道的邻居'}},
         'known': [{'id': 'k_public', 'text': '闸门去年漏过一次',
                    'source': '街坊闲聊', 'public': True},
                   {'id': 'k_private', 'text': '守闸人欠着一笔旧债',
                    'source': '私下听来的', 'public': False, 'known_by': ['keeper']}],
         'goal': '保住这一季的米',
         'traits': [{'template': 'trait_public_plain', 'version': 1,
                     'visibility': 'public', 'personal': '我说话不绕弯',
                     'evidence': ['opening']}],
         'entry_event': 'root_event'},
        {'id': 'guild_apprentice', 'title': '行会学徒', 'summary': '在行会堂打杂学徒。',
         'identity': '行会学徒', 'location': 'gate', 'items': [],
         'wallet': {'coin': 10}, 'relations': {},
         'known': [{'id': 'k_order', 'text': '行会要先把闸板压上',
                    'source': '行会堂的差事', 'public': True}],
         'goal': '把师傅交代的闸板压好',
         'flags': {'gate_ready': True}, 'entry_event': 'gate_root'},
    ]}


def story_package(lift_and_burst_same_hour=True, start=True):
    events = [
        {'id': 'root_event', 'title': '渡口封航告示', 'location_id': 'plaza',
         'participants': ['player', 'keeper'], 'player_goal': '弄清封航意味着什么',
         'next_events': ['gate_event'], 'max_turns': 6, 'exit_flag': 'done_root',
         'player_enters': True,
         'actions': [
             {'id': 'look', 'label': '看看告示上写了什么', 'ends_event': True,
              'success_text': '我把告示读了两遍。'},
             {'id': 'stack_sandbags', 'label': '把沙袋压上闸板',
              'costs': {'sandbags': 1}, 'duration_hours': 2,
              'effects': [{'op': 'flag', 'id': 'grain_secured', 'value': True}],
              'ends_event': True, 'success_text': '沙袋压住了闸板。'},
             {'id': 'open_sluice', 'label': '开闸放水',
              'costs': {'sandbags': 2}, 'duration_hours': 2,
              'check': {'attribute': 'wisdom', 'difficulty': 0.35},
              'effects': [{'op': 'flag', 'id': 'sluice_opened', 'value': True}],
              'ends_event': True, 'success_text': '闸门抬起一条缝。',
              'failure_text': '绞盘卡住了。'},
             {'id': 'abandon_convoy', 'label': '放弃粮队先走',
              'effects': [{'op': 'flag', 'id': 'convoy_lost', 'value': True}],
              'ends_event': True, 'success_text': '我转身往坡上走。'}]},
        {'id': 'gate_root', 'title': '行会堂的委托', 'location_id': 'gate',
         'participants': ['player', 'keeper'], 'player_goal': '守住闸门',
         'next_events': [], 'max_turns': 6, 'exit_flag': 'done_gate',
         'player_enters': True, 'entry_flags': {'gate_ready': True},
         'actions': [{'id': 'wait_gate', 'label': '守着闸门等水情', 'ends_event': True,
                      'success_text': '水声一直没停。'}]},
        {'id': 'gate_event', 'title': '上闸守闸人', 'location_id': 'gate',
         'participants': ['player', 'keeper'], 'player_goal': '问清该压还是该放',
         'next_events': [], 'max_turns': 6, 'exit_flag': 'done_gate_event',
         'player_enters': True,
         'actions': [{'id': 'leave_gate', 'label': '离开闸口', 'ends_event': True,
                      'success_text': '我沿坡道走开。'}]},
        {'id': 'rebuild', 'title': '善后与重建', 'location_id': 'plaza',
         'participants': ['player', 'keeper'], 'player_goal': '清点还能用的东西',
         'next_events': [], 'max_turns': 6, 'exit_flag': 'done_rebuild',
         'player_enters': True,
         'actions': [{'id': 'count_grain', 'label': '清点剩下的粮', 'ends_event': True,
                      'success_text': '能用的粮不多。'}]},
    ]
    mechanics = {'local': {'resources': [{'id': 'sandbags', 'name': '沙袋', 'unit': '袋',
                                          'initial': 4, 'maximum': 20, 'per_hour': 0}],
                           'turn_hours': 1, 'travel_hours': 2},
                 'rewards': rewards_block(),
                 'traits': traits_snapshot(),
                 'pressure': pressure_block(lift_and_burst_same_hour),
                 'endings': endings_block()}
    if start:
        mechanics['start_profiles'] = start_block()
    story = {'id': 'demo-test', 'title': '测试短篇', 'premise': '测试用的小世界。',
             'character_package_id': 'demo-test-characters',
             'locations': [{'id': 'plaza', 'name': '米市街', 'description': '',
                            'neighbors': ['gate'], 'scenes': []},
                           {'id': 'gate', 'name': '上闸', 'description': '',
                            'neighbors': ['plaza'], 'scenes': []}],
             'events': events,
             'items': [{'id': 'rope', 'name': '麻绳', 'description': '',
                        'authority': 'engine', 'location_id': 'plaza'}],
             'mechanics': mechanics}
    characters = {'id': 'demo-test-characters', 'title': '测试角色',
                  'characters': [
                      {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
                       'personality': {'谨慎': 0.6}, 'state': {'疲劳': 0.1},
                       'trait_refs': [{'template': 'trait_careful', 'version': 1,
                                       'visibility': 'public',
                                       'personal': '我总要先问清条件',
                                       'evidence': ['opening']}]},
                      {'id': 'keeper', 'name': '守闸人', 'role': '次要角色',
                       'location_id': 'gate', 'personality': {'固执': 0.7},
                       'state': {'警惕': 0.3},
                       'trait_refs': [
                           {'template': 'trait_public_plain', 'version': 1,
                            'visibility': 'public', 'personal': '他说话直',
                            'evidence': ['opening']},
                           {'template': 'trait_secret_owe', 'version': 1,
                            'visibility': 'hidden', 'aware': True,
                            'personal': '他欠着别人一笔债', 'evidence': ['opening']}]}]}
    return story, characters


def make_service(story=None, characters=None):
    """A private root with one package, so nothing is written into the repo."""
    story, characters = (story, characters) if story is not None else story_package()
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    folder = root / 'StoryPackage' / '玄陆'
    folder.mkdir(parents=True)
    (folder / 'story.json').write_text(json.dumps(story, ensure_ascii=False, indent=2),
                                       encoding='utf-8')
    (folder / '总概.md').write_text('# 测试短篇\n\n河港汛期的测试副本。\n', encoding='utf-8')
    (folder / '知识点').mkdir()
    chars = root / 'character_packages'
    chars.mkdir()
    (chars / 'xuanlu_初始角色包.json').write_text(
        json.dumps(characters, ensure_ascii=False, indent=2), encoding='utf-8')
    svc = Service(Store(root / 'demo.sqlite3'), root)
    svc.provider.configure({'offline': True})
    return tmp, svc


def fake_effects(session, effects, source):
    for effect in effects:
        if effect['op'] == 'flag':
            session.setdefault('flags', {})[effect['id']] = bool(effect.get('value', True))
        elif effect['op'] == 'resource':
            block = session.setdefault('local', {}).setdefault('resources', {})
            block[effect['id']] = block.get(effect['id'], 0) + int(effect.get('delta', 0))


# ------------------------------------------------------------------- 特质
def validate_traits(story, characters=None):
    return T.validate_package(story, characters)


class TraitTests(unittest.TestCase):
    def story(self, snap=None):
        story, _ = story_package()
        story['mechanics']['traits'] = snap if snap is not None else traits_snapshot()
        return story

    def test_outer_details_name_and_tags_tamper_are_refused(self):
        for field, value in (('details', {'definition': '改过的正文'}),
                             ('name', '被改过的名字'),
                             ('tags', ['trait']),
                             ('summary', '被改过的摘要')):
            snap = traits_snapshot()
            snap['templates'][0][field] = value
            with self.assertRaises(T.TraitError, msg=field):
                validate_traits({'mechanics': {'traits': snap}})

    def test_payload_tamper_is_refused(self):
        snap = traits_snapshot()
        snap['templates'][0]['payload']['name'] = '偷改的名字'
        with self.assertRaises(T.TraitError):
            validate_traits({'mechanics': {'traits': snap}})

    def test_unknown_fields_nan_and_boolean_versions_are_refused(self):
        snap = traits_snapshot()
        snap['extra'] = 1
        with self.assertRaises(T.TraitError):
            validate_traits({'mechanics': {'traits': snap}})
        snap = traits_snapshot()
        snap['version'] = True
        with self.assertRaises(T.TraitError):
            validate_traits({'mechanics': {'traits': snap}})
        snap = traits_snapshot()
        snap['templates'][0]['version'] = True
        with self.assertRaises(T.TraitError):
            validate_traits({'mechanics': {'traits': snap}})
        snap = traits_snapshot()
        payload_nan = copy.deepcopy(snap['templates'][0]['payload'])
        payload_nan['details']['definition'] = float('nan')
        snap['templates'][0]['payload'] = payload_nan
        with self.assertRaises(T.TraitError):
            validate_traits({'mechanics': {'traits': snap}})

    def test_manifest_and_snapshot_must_agree(self):
        story = self.story()
        template = story['mechanics']['traits']['templates'][0]
        story['mechanics']['element_manifest'] = {'version': 1, 'elements': [
            {'ref': 'character-traits/' + template['element_id'], 'version': 2,
             'payload_hash': template['payload_hash']}]}
        with self.assertRaises(T.TraitError):
            validate_traits(story)

    def test_character_ref_must_match_snapshot(self):
        story, characters = story_package()
        characters['characters'][0]['trait_refs'][0]['version'] = 2
        with self.assertRaises(T.TraitError):
            validate_traits(story, characters)
        story, characters = story_package()
        characters['characters'][0]['trait_refs'][0]['template'] = 'trait_missing'
        with self.assertRaises(T.TraitError):
            validate_traits(story, characters)
        story, characters = story_package()
        # 模板是 hidden，引用却写成 public：拒绝，否则隐藏设定会泄进玩家视图。
        characters['characters'][1]['trait_refs'][1]['visibility'] = 'public'
        with self.assertRaises(T.TraitError):
            validate_traits(story, characters)

    def test_audience_split_never_leaks_hidden(self):
        story, characters = story_package()
        keeper = characters['characters'][1]
        player_rows = T.projections(story, keeper, 'player')
        self.assertEqual([row['template'] for row in player_rows],
                         ['character-traits/trait_public_plain'])
        other_npc_rows = T.projections(story, keeper, 'player')
        self.assertNotIn('character-traits/trait_secret_owe',
                         [row['template'] for row in other_npc_rows])
        own_rows = T.projections(story, keeper, 'keeper')
        self.assertIn('character-traits/trait_secret_owe',
                      [row['template'] for row in own_rows])

    def test_context_is_bounded_and_never_sliced(self):
        story, characters = story_package()
        hero = characters['characters'][0]
        hero['trait_refs'] = [{'template': 'trait_careful', 'version': 1,
                               'visibility': 'public', 'personal': 'p%d' % i}
                              for i in range(6)]
        session = {'hero': 'player', 'location': 'plaza',
                   'characters': {'player': {'location': 'plaza'}}}
        block = T.context(story, session, 'player', characters=characters)
        self.assertLessEqual(len(block['items']), T.CONTEXT_MAX_ENTRIES)
        self.assertLessEqual(len(json.dumps(block, ensure_ascii=False)), T.CONTEXT_MAX_CHARS)

    def test_hero_package_traits_survive_without_start_profile(self):
        story, characters = story_package(start=False)
        session = {'hero': 'player', 'location': 'plaza',
                   'characters': {'player': {'location': 'plaza'}}}
        block = T.context(story, session, 'player', characters=characters)
        self.assertIsNotNone(block)
        self.assertEqual(block['items'][0]['name'], '先问后动')


# ------------------------------------------------------------------- 起点
class StartProfileTests(unittest.TestCase):
    def test_raw_types_are_strict(self):
        cases = []
        base = start_block()

        def mutate(fn):
            block = copy.deepcopy(base)
            fn(block['profiles'][0])
            return {'mechanics': {'start_profiles': block}}

        cases.append(mutate(lambda p: p['wallet'].__setitem__('coin', True)))
        cases.append(mutate(lambda p: p['wallet'].__setitem__('coin', '3')))
        cases.append(mutate(lambda p: p.update(flags={'gate_ready': 1})))
        cases.append(mutate(lambda p: p['known'][0].__setitem__('public', 'yes')))
        cases.append(mutate(lambda p: p['relations']['keeper'].__setitem__('trust', '0.6')))
        cases.append(mutate(lambda p: p.__setitem__('entry_event', 3)))
        block = copy.deepcopy(base)
        block['version'] = True
        cases.append({'mechanics': {'start_profiles': block}})
        for index, story in enumerate(cases):
            with self.assertRaises(Exception, msg='case %d' % index):
                SP.config(story)

    def test_apply_rebuilds_the_three_positions_and_explored(self):
        story, characters = story_package()
        session = {'hero': 'player', 'time': 8, 'seed': 'seed0001',
                   'location': 'gate', 'explored': ['gate', 'plaza'],
                   'characters': {'player': {'location': 'gate'}},
                   'flags': {}, 'facts': [], 'heard': [], 'beliefs': [],
                   'inventory': ['rope'], 'local': {'resources': {'sandbags': 4}}}
        profile = SP.resolve(SP.config(story), 'townsfolk')
        SP.apply(session, story, characters, profile)
        self.assertEqual(session['location'], 'plaza')
        self.assertEqual(session['characters']['player']['location'], 'plaza')
        self.assertEqual(session['explored'], ['plaza', 'gate'])

    def test_entry_event_rules(self):
        story, characters = story_package()
        # 入口带前置就必须在起点里显式声明同值
        story['events'][1]['entry_flags'] = {'gate_ready': True, 'other': True}
        with self.assertRaises(ValueError):
            SP.validate_package(story, characters)
        # 有上游的事件不能当入口（否则等于把未完成的上游默认成已完成）
        story, characters = story_package()
        story['mechanics']['start_profiles']['profiles'][0]['entry_event'] = 'gate_event'
        with self.assertRaises(ValueError):
            SP.validate_package(story, characters)
        # 时间窗不含开局第 8 小时就拒绝
        story, characters = story_package()
        story['events'][0]['time_min'] = 9
        with self.assertRaises(ValueError):
            SP.validate_package(story, characters)

    def test_entry_with_false_flag_is_legal(self):
        story, characters = story_package()
        story['events'][1]['entry_flags'] = {'gate_ready': False}
        story['mechanics']['start_profiles']['profiles'][1]['flags'] = {'gate_ready': False}
        SP.validate_package(story, characters)

    def test_known_audiences_are_unique_and_hidden_is_not_false(self):
        story, characters = story_package()
        block = story['mechanics']['start_profiles']['profiles'][0]
        block['known'].append({'id': 'k_public', 'text': '重复', 'public': True})
        with self.assertRaises(ValueError):
            SP.config(story)
        story, characters = story_package()
        block = story['mechanics']['start_profiles']['profiles'][0]
        block['known'][1]['known_by'] = ['keeper', 'keeper']
        with self.assertRaises(ValueError):
            SP.config(story)
        story, characters = story_package()
        block = story['mechanics']['start_profiles']['profiles'][0]
        block['known'][1]['known_by'] = ['keeper', 'player']
        with self.assertRaises(ValueError):
            SP.config(story)
        # 非公开信息仍然确定：distortion 为 0，不是「失真 1」
        story, characters = story_package()
        session = {'hero': 'player', 'time': 8, 'seed': 'seed0001', 'location': 'plaza',
                   'explored': [], 'characters': {'player': {'location': 'plaza'}},
                   'flags': {}, 'facts': [], 'heard': [], 'beliefs': [],
                   'inventory': [], 'local': {'resources': {'sandbags': 4}}}
        SP.apply(session, story, characters, SP.resolve(SP.config(story), 'townsfolk'))
        private = [row for row in session['beliefs'] if row['character'] == 'keeper']
        self.assertTrue(private)
        self.assertEqual({row['distortion'] for row in private}, {0})
        player_texts = [row['text'] for row in session['heard']]
        self.assertNotIn('守闸人欠着一笔旧债', player_texts)

    def test_invalid_profile_leaves_no_writes(self):
        story, characters = story_package()
        # 包本身合法，但开局发放会在应用中途被拒（单件价值超过上限）：
        # 此时开局已经在候选快照上写过位置与标记，但一行都不应该落库。
        story['mechanics']['rewards']['max_value_per_grant'] = 5
        tmp, svc = make_service(story, characters)
        try:
            before = len(svc.store.all('session'))
            with self.assertRaises(Exception):
                svc.runtime.new_session('坏起点', 'protagonist', profile_id='townsfolk')
            self.assertEqual(len(svc.store.all('session')), before)
        finally:
            tmp.cleanup()

    def test_apply_runs_before_clock_and_entry(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            self.assertEqual(s['time'], 8)
            self.assertEqual(s['location'], 'plaza')
            self.assertEqual(s['characters'][s['hero']]['location'], 'plaza')
            self.assertEqual(s['active']['node'], 'root_event')
            self.assertEqual(s['local']['applied'], {})
            self.assertEqual(s['start']['profile_id'], 'townsfolk')
        finally:
            tmp.cleanup()

    def test_start_grants_are_isolated_from_event_rewards(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            grants = s['rewards']['grants']
            self.assertTrue(grants)
            self.assertTrue(all(row['source'].startswith('start:') for row in grants))
            self.assertTrue(all(row['branch'] == 'start' for row in grants))
            self.assertEqual(s['rewards']['wallet']['coin'], 30)
            self.assertEqual(len(s['rewards']['items']), 1)
        finally:
            tmp.cleanup()

    def test_trait_version_conflict_between_character_and_profile_is_refused(self):
        story, characters = story_package()
        story['mechanics']['start_profiles']['profiles'][0]['traits'][0]['version'] = 2
        story['mechanics']['traits'] = traits_snapshot()
        session = {'hero': 'player', 'time': 8, 'seed': 'seed0001', 'location': 'plaza',
                   'explored': [], 'characters': {'player': {'location': 'plaza'}},
                   'flags': {}, 'facts': [], 'heard': [], 'beliefs': [],
                   'inventory': [], 'local': {'resources': {'sandbags': 4}}}
        profile = SP.config(story).profiles[0]
        with self.assertRaises(ValueError):
            # 角色包已有 v1，起点写 v2：必须报错，不能静默丢掉其中一条
            SP.apply(session, story, characters, profile)

    def test_surface_hides_engine_internals(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            surface = svc.runtime.surface(s)
            opening = surface['opening']
            text = json.dumps(opening, ensure_ascii=False)
            self.assertIn('米市街的本地居民', text)
            for leaked in ('引擎', '模型', 'mechanic', 'start_profiles', '不会补发'):
                self.assertNotIn(leaked, text)
            self.assertEqual([row['text'] for row in opening['known']],
                             ['闸门去年漏过一次'])
        finally:
            tmp.cleanup()


class LegacyCompatTests(unittest.TestCase):
    """没声明任何 demo 机制的包：surface 里的行动仍是旧的两字段形状。"""

    def test_old_package_keeps_two_field_actions(self):
        story, characters = story_package()
        for key in ('start_profiles', 'pressure', 'endings', 'traits'):
            story['mechanics'].pop(key, None)
        characters['characters'][0].pop('trait_refs', None)
        characters['characters'][1].pop('trait_refs', None)
        tmp, svc = make_service(story, characters)
        try:
            session = svc.runtime.new_session('旧包', 'protagonist')
            surface = svc.runtime.surface(session)
            self.assertTrue(surface['actions'])
            for action in surface['actions']:
                self.assertEqual(sorted(action), ['id', 'label'])
            self.assertNotIn('opening', surface)
            self.assertNotIn('warnings', surface)
            self.assertNotIn('ending', surface)
        finally:
            if tmp:
                tmp.cleanup()


# ------------------------------------------------------------------- 压力
class PressureTests(unittest.TestCase):
    def story(self, **kwargs):
        story, _ = story_package(**kwargs)
        return story

    def session(self):
        return {'time': 8, 'flags': {},
                'local': {'resources': {'sandbags': 4}, 'ledger': [], 'applied': {},
                          'notices': [], 'initialized_at': 8},
                'pressure': {'version': 1, 'applied': {}, 'log': [], 'lifted': {}}}

    def test_crossing_several_thresholds_applies_each_exactly_once(self):
        story = self.story(lift_and_burst_same_hour=False)
        s = self.session()
        s['flags']['grain_secured'] = True
        applied = P.advance(s, story, {}, 6, effects=fake_effects)
        self.assertEqual([row['stage'] for row in applied], ['warn', 'burst', 'resolve_grain'])
        self.assertEqual(s['flags'], {'warned': True, 'convoy_lost': True,
                                      'grain_secured': True, 'grain_saved': True})
        again = P.advance(s, story, {}, 6, effects=fake_effects)
        self.assertEqual(again, [])
        self.assertEqual(len(s['pressure']['log']), 3)

    def test_same_hour_lift_wins_over_disaster(self):
        story = self.story()
        s = self.session()
        applied = P.advance(s, story, {}, 3, effects=fake_effects)
        self.assertEqual([row['stage'] for row in applied], ['warn', 'lift'])
        self.assertTrue(s['flags']['lifted'])
        self.assertNotIn('convoy_lost', s['flags'])
        # 再推进一次也不会「补放」灾难
        later = P.advance(s, story, {}, 6, effects=fake_effects)
        self.assertEqual(later, [])
        self.assertNotIn('convoy_lost', s['flags'])

    def test_condition_met_late_fires_at_that_moment(self):
        story = self.story(lift_and_burst_same_hour=False)
        s = self.session()
        P.advance(s, story, {}, 4, effects=fake_effects)  # 到 12 小时，late_note 条件未满足
        self.assertNotIn('flood:late_note', s['pressure']['applied'])
        s['flags']['late_mark'] = True
        applied = P.advance(s, story, {}, 1, effects=fake_effects)  # 13 小时才满足
        self.assertEqual([row['stage'] for row in applied], ['late_note'])
        self.assertEqual(s['pressure']['applied']['flood:late_note'], 13)

    def test_read_paths_never_advance(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            for _ in range(3):
                svc.runtime.surface(s)
                svc.runtime.context(s, 'player', '看看水位', svc.preferences())
                P.known(s, svc.runtime.package(s['revision'])['story'], 'player')
                P.phase(s, svc.runtime.package(s['revision'])['story'])
            self.assertEqual(s['time'], 8)
            self.assertEqual(s['pressure']['applied'], {})
            self.assertNotIn('warned', s['flags'])
        finally:
            tmp.cleanup()

    def test_one_clock_only(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            start = s['time']
            asyncio.run(svc.turn(s['id'], Turn(message='看看告示', action_id='look')))
            reloaded = svc.store.session(s['id'])
            self.assertEqual(reloaded['time'] - start, 1)
        finally:
            tmp.cleanup()

    def test_player_sees_only_known_warnings(self):
        story = self.story(lift_and_burst_same_hour=False)
        s = self.session()
        P.advance(s, story, {}, 6, effects=fake_effects)
        rows = P.known(s, story, 'player')
        self.assertEqual([row['text'] for row in rows], ['水位一夜涨了两尺'])
        text = json.dumps(P.context(s, story, 'player'), ensure_ascii=False)
        for leaked in ('at_hours', 'burst', 'convoy_lost', '9', '10'):
            self.assertNotIn(leaked, text)
        self.assertIsNone(P.context(s, story, 'keeper'))

    def test_effects_without_engine_are_refused(self):
        story = self.story()
        s = self.session()
        with self.assertRaises(ValueError):
            P.advance(s, story, {}, 3, effects=None)


    # ---- 时间粒度：advance(N) 必须等于 N 次 advance(1) ----
    def timed_story(self):
        story, _ = story_package(lift_and_burst_same_hour=False)
        story['mechanics']['local'] = {
            'resources': [{'id': 'sandbags', 'name': '沙袋', 'initial': 10, 'maximum': 50,
                           'per_hour': 1}],
            'schedules': [{'id': 'sched', 'title': '石阶又没了一级', 'at': 11,
                           'effects': [{'op': 'resource', 'id': 'sandbags', 'delta': -3},
                                       {'op': 'flag', 'id': 'sched_flag', 'value': True}]},],
            'turn_hours': 1, 'travel_hours': 2}
        story['mechanics']['pressure'] = {'version': 1, 'pressures': [{
            'id': 'flood', 'title': '汛情', 'stages': [
                {'id': 'drain', 'at_hours': 10, 'kind': 'warning',
                 'effects': [{'op': 'resource', 'id': 'sandbags', 'delta': -4},
                             {'op': 'flag', 'id': 'drained', 'value': True}]},
                {'id': 'late', 'at_hours': 12, 'kind': 'trigger',
                 'when': {'all_flags': {'sched_flag': True}},
                 'effects': [{'op': 'flag', 'id': 'late_fired', 'value': True}]},
            ]}]}
        return story

    def state(self, session):
        return {'time': session['time'], 'flags': dict(session['flags']),
                'resources': dict(session['local']['resources']),
                'applied': dict(session['pressure']['applied']),
                'cancelled': dict(session['pressure'].get('cancelled') or {})}

    def test_advance_n_equals_n_hourly_steps(self):
        story = self.timed_story()
        once = self.session()
        once['local']['resources']['sandbags'] = 10
        P.advance(once, story, {}, 12, effects=fake_effects)
        hourly = self.session()
        hourly['local']['resources']['sandbags'] = 10
        for _ in range(12):
            P.advance(hourly, story, {}, 1, effects=fake_effects)
        self.assertEqual(self.state(once), self.state(hourly))
        # 10 点的压力在 10 点生效，11 点的日程看到的是它之后的余额
        self.assertEqual(once['pressure']['applied']['flood:drain'], 10)
        self.assertEqual(once['pressure']['applied']['flood:late'], 12)
        self.assertEqual(once['local']['resources']['sandbags'], 10 + 12 - 4 - 3)

    def test_late_condition_uses_the_hour_it_becomes_true(self):
        story = self.timed_story()
        s = self.session()
        P.advance(s, story, {}, 20, effects=fake_effects)
        # 即使一次推进 20 小时，late 也记在它真正满足的第 12 小时，而不是终点
        self.assertEqual(s['pressure']['applied']['flood:late'], 12)
        self.assertNotIn('late_fired', {k for k, v in s['pressure']['cancelled'].items()})
        # 后来的标记不会追溯：先把 sched_flag 真值拿掉也不会重算历史
        before = dict(s['pressure']['applied'])
        s['flags'].pop('sched_flag', None)
        P.advance(s, story, {}, 1, effects=fake_effects)
        self.assertEqual(before, s['pressure']['applied'])

    def test_lift_terminates_the_rest_of_its_pressure(self):
        story = self.timed_story()
        block = story['mechanics']['pressure']
        block['pressures'][0]['stages'].insert(1, {
            'id': 'lift', 'at_hours': 11, 'kind': 'lift',
            'effects': [{'op': 'flag', 'id': 'lifted', 'value': True}]})
        block['pressures'].append({'id': 'convoy', 'title': '粮队', 'stages': [
            {'id': 'report', 'at_hours': 14, 'kind': 'trigger',
             'effects': [{'op': 'flag', 'id': 'convoy_note', 'value': True}]}]})
        s = self.session()
        P.advance(s, story, {}, 8, effects=fake_effects)
        # 化解生效：同压力里未生效的 late 被终止，不再补放
        self.assertIn('flood:late', s['pressure']['cancelled'])
        self.assertNotIn('late_fired', s['flags'])
        cancelled = [row for row in s['pressure']['log'] if row['outcome'] == 'cancelled']
        self.assertTrue(cancelled)
        # 另一个压力的阶段不受影响（作用域限于同一压力）
        self.assertIn('convoy:report', s['pressure']['applied'])


# ------------------------------------------------------------ 自由行动确认
class FreeActionTests(unittest.TestCase):
    def fresh(self):
        tmp, svc = make_service()
        s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
        story = svc.runtime.package(s['revision'])['story']
        node = svc.runtime.node(s)
        return tmp, svc, s, story, node

    def test_suggest_changes_nothing(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            before = json.dumps({'t': s['time'], 'f': s['flags'], 'l': s['local'],
                                 'i': s['inventory']}, sort_keys=True, ensure_ascii=False)
            result = F.suggest(s, story, node, '把沙袋压上闸板')
            after = json.dumps({'t': s['time'], 'f': s['flags'], 'l': s['local'],
                                'i': s['inventory']}, sort_keys=True, ensure_ascii=False)
            self.assertEqual(before, after)
            self.assertFalse(result['unjudged'])
            self.assertEqual(result['matched'][0]['action_id'], 'stack_sandbags')
            self.assertEqual(result['matched'][0]['costs'][0]['amount'], 1)
        finally:
            tmp.cleanup()

    def test_negation_and_stopwords_do_not_execute(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            for intent in ('我不去开闸', '算了，不开闸放水了', '我不知道', '随便看看天气'):
                result = F.suggest(s, story, node, intent)
                ids = [row['action_id'] for row in result['matched']]
                self.assertNotIn('open_sluice', ids, intent)
        finally:
            tmp.cleanup()

    def test_unknown_intent_is_unjudged_and_writes_nothing(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            result = F.suggest(s, story, node, '去码头偷一条船然后远走高飞')
            self.assertEqual(result['matched'], [])
            self.assertTrue(result['unjudged'])
            self.assertNotIn('theft', json.dumps(s, ensure_ascii=False))
        finally:
            tmp.cleanup()

    def test_stale_confirm_is_refused_before_side_effects(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            token = F.confirm_token(s, node, node['actions'][1], story)
            asyncio.run(svc.turn(s['id'], Turn(message='看告示', action_id='look')))
            stored = svc.store.session(s['id'])
            sandbags = stored['local']['resources']['sandbags']
            version = stored['state_version']
            with self.assertRaises(ValueError):
                asyncio.run(svc.turn(s['id'], Turn(message='压沙袋',
                                                   action_id='stack_sandbags',
                                                   confirm=token)))
            after = svc.store.session(s['id'])
            self.assertEqual(after['local']['resources']['sandbags'], sandbags)
            self.assertEqual(after['state_version'], version)
        finally:
            tmp.cleanup()

    def test_confirm_for_another_action_is_refused(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            token = F.confirm_token(s, node, node['actions'][1], story)
            with self.assertRaises(ValueError):
                asyncio.run(svc.turn(s['id'], Turn(message='开闸', action_id='open_sluice',
                                                   confirm=token)))
            after = svc.store.session(s['id'])
            self.assertEqual(after['local']['resources']['sandbags'], 4)
        finally:
            tmp.cleanup()

    def test_valid_confirm_executes_once(self):
        tmp, svc, s, story, node = self.fresh()
        try:
            token = F.confirm_token(s, node, node['actions'][1], story)
            asyncio.run(svc.turn(s['id'], Turn(message='压沙袋', action_id='stack_sandbags',
                                               confirm=token)))
            after = svc.store.session(s['id'])
            self.assertEqual(after['local']['resources']['sandbags'], 3)
            self.assertTrue(after['flags'].get('grain_secured'))
        finally:
            tmp.cleanup()

    def test_plain_channels_still_work_without_confirm(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            for channel in ('speech', 'thought', 'note'):
                asyncio.run(svc.turn(s['id'], Turn(message='我看看四周', channel=channel)))
            stored = svc.store.session(s['id'])
            self.assertEqual(stored['local']['resources']['sandbags'], 4)
        finally:
            tmp.cleanup()


# ------------------------------------------------------------------- 结局
class EndingTests(unittest.TestCase):
    def test_overlapping_conditions_are_refused(self):
        story, characters = story_package()
        # 两个结局的条件完全相同：任意状态都会同时成立，包校验必须拒绝。
        story['mechanics']['endings']['endings'] = [
            {'id': 'a', 'title': 'A', 'kind': 'saved', 'summary': '甲',
             'condition': {'all_flags': {'grain_secured': True}}, 'priority': 50},
            {'id': 'b', 'title': 'B', 'kind': 'traded', 'summary': '乙',
             'condition': {'all_flags': {'grain_secured': True}}, 'priority': 40}]
        with self.assertRaises(ValueError):
            E.validate_package(story, characters)

    def test_unreachable_ending_is_refused(self):
        story, characters = story_package()
        story['mechanics']['endings']['endings'][2]['condition']['all_flags'] = {
            'never_set_anywhere': True}
        with self.assertRaises(ValueError):
            E.validate_package(story, characters)

    def test_any_flags_true_and_false_are_not_an_overlap(self):
        """any_flags {a:true} 与 {a:false} 不可能同时成立，不得误拒。"""
        story, characters = story_package()
        story['mechanics']['endings']['endings'] = [
            {'id': 'a', 'title': 'A', 'kind': 'saved', 'summary': '甲', 'priority': 50,
             'condition': {'any_flags': {'flag_x': True}}},
            {'id': 'b', 'title': 'B', 'kind': 'traded', 'summary': '乙', 'priority': 40,
             'condition': {'any_flags': {'flag_x': False}}}]
        # flag_x 得有来源，否则会被来源覆盖检查拒掉；这里先加一个动作效果。
        story['events'][0]['actions'][0]['effects'] = [{'op': 'flag', 'id': 'flag_x',
                                                        'value': True}]
        cfg = E.validate_package(story, characters)
        self.assertEqual(len(cfg.endings), 2)

    def test_flag_source_from_a_schedule_counts(self):
        story, characters = story_package()
        story['events'][0]['actions'][0].pop('effects', None)
        story['mechanics']['local'].setdefault('schedules', []).append(
            {'id': 'sched', 'title': '到点了', 'at': 30,
             'effects': [{'op': 'flag', 'id': 'flag_from_schedule', 'value': True}]})
        story['mechanics']['endings']['endings'][0]['condition'] = {
            'all_flags': {'flag_from_schedule': True}, 'not_flags': ['sluice_opened']}
        story['mechanics']['endings']['endings'][1]['condition'] = {
            'all_flags': {'sluice_opened': True}, 'not_flags': ['flag_from_schedule']}
        story['mechanics']['endings']['endings'][2]['condition'] = {
            'all_flags': {'convoy_lost': True}, 'not_flags': ['sluice_opened']}
        report = E.flag_sources(story)
        self.assertTrue(report['ending_saved']['documented'])

    def test_priority_and_allow_overlap_reject_coercion(self):
        for field, value in (('priority', True), ('priority', '50'), ('priority', 50.0),
                             ('allow_overlap', 'yes'), ('allow_overlap', 1)):
            story, characters = story_package()
            story['mechanics']['endings']['endings'][0][field] = value
            with self.assertRaises(Exception, msg='%s=%r' % (field, value)):
                E.config(story)

    def test_over_many_flags_is_refused_not_guessed(self):
        left = E.Condition(all_flags={'f%d' % i: True for i in range(8)})
        right = E.Condition(any_flags={'g%d' % i: True for i in range(8)})
        with self.assertRaises(ValueError) as raised:
            E.conditions_overlap(left, right)
        self.assertIn('精确枚举上限', str(raised.exception))

    def test_resolve_picks_highest_priority(self):
        story, _ = story_package()
        ending = E.resolve({'flags': {'grain_secured': True}}, story)
        self.assertEqual(ending['id'], 'ending_saved')
        self.assertIsNone(E.resolve({'flags': {}}, story))

    def test_recorded_ending_is_sticky(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            asyncio.run(svc.turn(s['id'], Turn(message='压沙袋', action_id='stack_sandbags')))
            stored = svc.store.session(s['id'])
            self.assertEqual(stored['ending']['id'], 'ending_saved')
            # 后来的状态变化（例如压力）不得覆盖已记录的结局
            stored['flags'] = {'sluice_opened': True}
            surface = svc.runtime.surface(stored)
            self.assertEqual(surface['ending']['id'], 'ending_saved')
        finally:
            tmp.cleanup()

    def test_lost_ending_continues_instead_of_soft_locking(self):
        tmp, svc = make_service()
        try:
            s = svc.runtime.new_session('本地居民', 'protagonist', profile_id='townsfolk')
            asyncio.run(svc.turn(s['id'], Turn(message='放弃粮队',
                                               action_id='abandon_convoy')))
            stored = svc.store.session(s['id'])
            self.assertEqual(stored['ending']['id'], 'ending_lost')
            self.assertEqual(stored['ending']['kind'], 'lost')
            self.assertIsNotNone(stored['active'], '失败结局之后仍应能继续玩')
            self.assertEqual(stored['active']['node'], 'rebuild')
        finally:
            tmp.cleanup()


SECRET_TEXTS = ('SECRET-OPENED-门开了', '隐藏门-LEFT-走错', '暗号-ALPHA-听潮')


def secret_service():
    """把三种隐成内容（成功/失败描述 + 叙事线索）都拷在一个动作上。"""
    story, characters = story_package()
    target = next(a for a in story['events'][0]['actions'] if a['id'] == 'open_sluice')
    target['success_text'] = SECRET_TEXTS[0]
    target['failure_text'] = SECRET_TEXTS[1]
    target['narrative_cues'] = {'success': [SECRET_TEXTS[2]]}
    target['intent_aliases'] = ['放水', '开闸']
    return make_service(story, characters)


class CandidateIsolationTests(unittest.TestCase):
    """候选只能告诉玩家“能做什么”，不能告诉玩家“做了会发生什么”。"""

    def open_session(self):
        tmp, svc = secret_service()
        session = svc.runtime.new_session('本地居民', 'protagonist',
                                         profile_id='townsfolk')
        story = svc.runtime.package(session['revision'])['story']
        return tmp, svc, session, story, svc.runtime.node(session)

    def assert_clean(self, payload, where):
        text = json.dumps(payload, ensure_ascii=False)
        for secret in SECRET_TEXTS:
            self.assertNotIn(secret, text, where)

    def test_candidates_confirm_surface_and_context_never_show_results(self):
        tmp, svc, session, story, node = self.open_session()
        try:
            suggested = F.suggest(session, story, node, '放水')
            self.assertIn('open_sluice', [row['action_id'] for row in suggested['matched']],
                          '公开别名应能命中')
            self.assert_clean(suggested, '/intent')
            row = next(r for r in suggested['matched'] if r['action_id'] == 'open_sluice')
            self.assertEqual(sorted(row), ['action_id', 'check', 'confirm', 'costs',
                                           'duration_hours', 'ends_event',
                                           'intent_aliases', 'label', 'match'])
            self.assert_clean(F.describe(session, story, node, 'open_sluice'), '/confirm')
            self.assert_clean(svc.runtime.surface(session)['actions'], 'surface')
            context = svc.runtime.context(session, 'player', '看看闸', svc.preferences())
            self.assert_clean(context, 'context')
        finally:
            if tmp:
                tmp.cleanup()

    def test_secret_words_alone_never_match(self):
        tmp, svc, session, story, node = self.open_session()
        try:
            for secret in SECRET_TEXTS:
                result = F.suggest(session, story, node, secret)
                self.assertEqual(result['matched'], [], secret)
                self.assertTrue(result['unjudged'], secret)
        finally:
            if tmp:
                tmp.cleanup()

    def test_real_execution_still_narrates_the_branch_text(self):
        tmp, svc, session, story, node = self.open_session()
        try:
            action = next(a for a in node['actions'] if a['id'] == 'open_sluice')
            token = F.confirm_token(session, node, action, story)
            asyncio.run(svc.turn(session['id'], Turn(message='开闸',
                                                     action_id='open_sluice',
                                                     confirm=token)))
            stored = svc.store.session(session['id'])
            replies = [turn['reply'] for archive in stored['archives']
                       for turn in archive['turns']]
            self.assertTrue(any(SECRET_TEXTS[0] in reply or SECRET_TEXTS[1] in reply
                                for reply in replies),
                            '真实执行后作者侧的分支文本应照常出现')
        finally:
            if tmp:
                tmp.cleanup()


class DurationAndTokenTests(unittest.TestCase):
    """有效时长（0 / 缺省 / 显式）与完整检定都要进候选与凭据。"""

    def service(self):
        story, characters = story_package()
        story['events'][0]['actions'].append({
            'id': 'instant', 'label': '伸手试一下门闩', 'ends_event': False,
            'duration_hours': 0})
        return make_service(story, characters)

    def test_duration_uses_key_presence_not_or(self):
        tmp, svc = self.service()
        try:
            session = svc.runtime.new_session('本地居民', 'protagonist',
                                              profile_id='townsfolk')
            story = svc.runtime.package(session['revision'])['story']
            node = svc.runtime.node(session)
            by_id = {a['id']: a for a in node['actions']}
            turn_hours = (story['mechanics'].get('local') or {}).get('turn_hours', 1)
            self.assertEqual(F.effective_duration(by_id['instant'], story), 0)
            self.assertEqual(F.summarise(by_id['instant'], story)['duration_hours'], 0)
            self.assertEqual(F.effective_duration(by_id['look'], story), turn_hours)
            self.assertEqual(F.summarise(by_id['look'], story)['duration_hours'], turn_hours)
            self.assertEqual(F.summarise(by_id['open_sluice'], story)['duration_hours'], 2)
            zero = F.confirm_token(session, node, by_id['instant'], story)
            without_key = {k: v for k, v in by_id['instant'].items()
                           if k != 'duration_hours'}
            self.assertNotEqual(zero, F.confirm_token(session, node, without_key, story),
                                '0 小时与缺省必须得到不同凭据（反证没被 or 吞掉）')
        finally:
            if tmp:
                tmp.cleanup()

    def test_zero_hour_action_does_not_advance_the_clock(self):
        tmp, svc = self.service()
        try:
            session = svc.runtime.new_session('本地居民', 'protagonist',
                                              profile_id='townsfolk')
            start = session['time']
            story = svc.runtime.package(session['revision'])['story']
            node = svc.runtime.node(session)
            action = next(a for a in node['actions'] if a['id'] == 'instant')
            token = F.confirm_token(session, node, action, story)
            asyncio.run(svc.turn(session['id'], Turn(message='碰一下门闩',
                                                     action_id='instant', confirm=token)))
            stored = svc.store.session(session['id'])
            self.assertEqual(stored['time'], start, '0 小时的行动不应推进时钟')
        finally:
            if tmp:
                tmp.cleanup()

    def test_token_binds_the_whole_check_not_only_difficulty(self):
        tmp, svc = self.service()
        try:
            session = svc.runtime.new_session('本地居民', 'protagonist',
                                              profile_id='townsfolk')
            story = svc.runtime.package(session['revision'])['story']
            node = svc.runtime.node(session)
            base = next(a for a in node['actions'] if a['id'] == 'open_sluice')
            same_difficulty = copy.deepcopy(base)
            same_difficulty['check']['attribute'] = 'social'
            self.assertEqual(base['check']['difficulty'],
                             same_difficulty['check']['difficulty'])
            self.assertNotEqual(F.confirm_token(session, node, base, story),
                                F.confirm_token(session, node, same_difficulty, story),
                                '同难度换检定属性也必须让旧凭据失效')
            self.assertEqual(F.summarise(base, story)['check'],
                             {'attribute': 'wisdom', 'difficulty': 0.35})
        finally:
            if tmp:
                tmp.cleanup()

    def test_intent_aliases_are_bounded_and_public(self):
        tmp, svc = make_service()
        try:
            story, characters = story_package()
            action = story['events'][0]['actions'][2]
            action['intent_aliases'] = ['开闸']
            self.assertEqual(F.validate_action_aliases(action), ['开闸'])
            self.assertEqual(F.summarise(action, story)['intent_aliases'], ['开闸'])
            for bad in (['重复', '重复'], ['', 'a'], ['x' * 31], 'not-a-list',
                        ['a', 'b', 'c', 'd', 'e', 'f', 'g'], [1]):
                broken, broken_characters = story_package()
                broken['events'][0]['actions'][2]['intent_aliases'] = bad
                with self.assertRaises(Exception, msg=repr(bad)):
                    svc.runtime.validate_package(broken, broken_characters)
        finally:
            if tmp:
                tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
