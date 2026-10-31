# -*- coding: utf-8 -*-
"""冒险行动的**运行期**接线：真实 Store + Service.turn + Runtime.move。

与 `test_adventure_actions.py` 的分工：那边测纯规则（夹具直接喂 session）；这里测
「接进引擎之后到底发生了什么」——时钟、成本、facts/heard/beliefs 落位、确认凭据的
CAS、旧包兼容、旅行真实推进。全部离线，私有临时库，不碰仓库里的 data/ 与已发布包。
"""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import adventure_actions as A
from app import free_actions
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from app.runtime import trim_context

STATE_LAYERS = ('facts', 'beliefs', 'heard')
REPO = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------- 夹具
def adventure_block():
    return {
        'version': 1,
        'clues': [
            {'id': 'clue_waterline', 'target': {'kind': 'place', 'id': 'plaza'},
             'action_kinds': ['observe'],
             'effects': [{'op': 'information', 'text': '石阶上的水痕还是湿的。',
                          'known_by': ['player'], 'confirmed': True}]},
            {'id': 'clue_ledger', 'target': {'kind': 'object', 'id': 'ledger'},
             'action_kinds': ['investigate'],
             'requires': {'all_flags': {'ledger_open': True}},
             'public_obstruction': '账页扣着，翻不开。',
             'effects': [{'op': 'information', 'text': '这一页的米价被人改过。',
                          'known_by': ['player']}]},
            {'id': 'clue_secret', 'target': {'kind': 'object', 'id': 'cache'},
             'action_kinds': ['investigate'],
             'public_obstruction': '没什么可看的。',
             'effects': [{'op': 'information', 'text': '夹层里藏着一张字条。',
                          'known_by': ['player'], 'confirmed': True}]},
        ],
        'topics': [
            {'id': 'ask_price', 'kind': 'ask', 'target': {'kind': 'npc', 'id': 'merchant'},
             'answers': [{'when': {}, 'success_text': '他把米价说了一遍。',
                          'effects': [{'op': 'information', 'text': '米价三日内涨了两成。',
                                       'known_by': ['player'],
                                       'confirmed': True}]}]},
            {'id': 'ask_secret', 'kind': 'ask', 'target': {'kind': 'npc', 'id': 'merchant'},
             'answers': [{'when': {'all_flags': {'trusted': True}},
                          'success_text': '他压低声音。',
                          'effects': [{'op': 'information', 'text': '仓里其实早就空了。',
                                       'known_by': ['player']}]}]},
            {'id': 'negotiate_split', 'kind': 'negotiate',
             'target': {'kind': 'npc', 'id': 'merchant'},
             'requires': {'not_flags': ['deal_closed']},
             'answers': [{'when': {}, 'success_text': '我们各让一步。',
                          'effects': [{'op': 'flag', 'id': 'deal_struck', 'value': True},
                                      {'op': 'resource', 'id': 'coin', 'delta': -2}]}]},
        ],
        'routes': [
            {'origin': 'plaza', 'destination': 'gate', 'kind': 'causeway', 'hours': 3,
             'import_id': 'mi_abc123'},
            {'origin': 'gate', 'destination': 'plaza', 'kind': 'causeway',
             'requires': {'not_flags': ['gate_closed']},
             'public_obstruction': '闸门关着，今天过不去。'},
        ],
        'templates': [
            {'kind': 'rest', 'label': '在原处歇 {hours} 小时',
             'duration_hours': 4, 'costs': {'food': 1},
             'intent_aliases': ['歇一会']},
            {'kind': 'travel', 'target': {'kind': 'place', 'id': 'gate'},
             'label': '过闸去{target}', 'intent_aliases': ['过闸']},
        ],
        # 默认休息 4 小时（模板也声明了 4）；``max_rest_hours`` 给足上限。
        'rest_hours': 4, 'max_rest_hours': 168,
    }


def story_doc(with_adventure=True):
    mechanics = {
        'local': {'resources': [{'id': 'coin', 'name': '铜币', 'unit': '枚',
                                 'initial': 10, 'maximum': 50},
                                {'id': 'food', 'name': '口粮', 'unit': '份',
                                 'initial': 3, 'maximum': 9}],
                  'turn_hours': 1, 'travel_hours': 2},
        'map': {'kind': 'civ_atlas', 'import_id': 'mi_abc123'},
    }
    if with_adventure:
        mechanics['adventure'] = adventure_block()
    return {
        'id': 'exec-test', 'title': '执行接线测试', 'premise': '测试用的小世界。',
        'character_package_id': 'exec-test-characters',
        'locations': [
            {'id': 'plaza', 'name': '米市街', 'description': '',
             'neighbors': ['gate', 'vault'], 'scenes': []},
            {'id': 'gate', 'name': '上闸', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'coordinates': [120.5, 30.25]},
            {'id': 'vault', 'name': '粮仓深处', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'visibility': 'author'},
            # 没有任何事件的空地：那里仍能休息/旅行，不靠伪造故事事件。
            {'id': 'empty_place', 'name': '仓前空地', 'description': '',
             'neighbors': ['plaza'], 'scenes': []},
        ],
        'events': [
            {'id': 'root_event', 'title': '米市街的清晨', 'location_id': 'plaza',
             'participants': ['player', 'merchant'], 'player_goal': '弄清米价',
             'player_enters': True, 'next_events': [], 'entry_flags': {},
             'exit_flag': 'done_root', 'max_turns': 30,
             'actions': [{'id': 'look', 'label': '看看街面', 'ends_event': False,
                          'success_text': '我先看了看街面。'},
                         {'id': 'done_talk', 'label': '谈完了', 'ends_event': True,
                          'success_text': '这次谈话告一段落。'}]},
        ],
        'items': [
            {'id': 'ledger', 'name': '账页', 'description': '', 'authority': 'engine',
             'location_id': 'plaza'},
            {'id': 'cache', 'name': '夹层里的匣子', 'description': '',
             'authority': 'engine', 'location_id': 'plaza', 'visibility': 'author'},
            {'id': 'hammer', 'name': '木槌', 'description': '', 'authority': 'engine',
             'location_id': 'gate'},
        ],
        'mechanics': mechanics,
    }


def characters_doc():
    # 六项属性齐全：既有 attributes.validate 要求 0..100 的六个轴。
    axes = {'talent': 50, 'strength': 45, 'agility': 55, 'wisdom': 60,
            'social': 65, 'resilience': 50}
    return {'id': 'exec-test-characters', 'title': '测试角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {'谨慎': 0.6}, 'state': {'疲劳': 0.1}, 'attributes': dict(axes)},
        {'id': 'merchant', 'name': '米商', 'role': '次要角色', 'location_id': 'plaza',
         'personality': {'社交': 0.6}, 'state': {}, 'attributes': dict(axes)},
        {'id': 'spy', 'name': '暗处的人', 'role': '次要角色', 'location_id': 'plaza',
         'visibility': 'author', 'personality': {}, 'state': {},
         'attributes': dict(axes)},
    ]}


def dumped(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def state_fingerprint(session):
    """只比游戏状态：``state_version`` 单列（它本来就该随保存变化）。"""
    return dumped({key: value for key, value in session.items() if key != 'state_version'})


class Base(unittest.TestCase):
    with_adventure = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        story = story_doc(self.with_adventure)
        self.folder = root / 'StoryPackage' / '玄陆'
        self.folder.mkdir(parents=True)
        (self.folder / 'story.json').write_text(
            json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
        (self.folder / '总概.md').write_text('# 执行接线测试\n\n夹具世界。\n', encoding='utf-8')
        (self.folder / '知识点').mkdir()
        chars = root / 'character_packages'
        chars.mkdir()
        # 角色包文件名用包自己声明的 character_package_id，避开仓库里同名旧包的 id 冲突。
        body = json.dumps(characters_doc(), ensure_ascii=False, indent=2)
        (chars / 'exec-test-characters.json').write_text(body, encoding='utf-8')
        # 空库首次初始化会固定读这个文件名（既有约定），所以也放一份，内容同样是本夹具。
        (chars / 'xuanlu_初始角色包.json').write_text(body, encoding='utf-8')
        self.store = Store(root / 'exec.sqlite3')
        self.svc = Service(self.store, root)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.root = root
        self.s = self.rt.new_session('接线', 'protagonist')

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------------- 帮手
    def reload(self):
        return self.store.session(self.s['id'])

    def plans(self, session=None):
        session = session if session is not None else self.reload()
        package = self.rt.package(session['revision'])
        return A.build(session, package['story'], package['characters'])

    def plan(self, kind, session=None, target=None):
        for plan in self.plans(session):
            if plan['kind'] == kind and (target is None or plan['target']
                                         and plan['target']['id'] == target):
                return plan
        raise AssertionError('没有 %s 方案（%s）' % (kind, target))

    def token(self, plan, session=None):
        session = session if session is not None else self.reload()
        package = self.rt.package(session['revision'])
        node = self.rt.node(session) if session['active'] else None
        return free_actions.confirm_token(session, node, plan['action'], package['story'])

    def commit(self, mutate):
        """改故事包：先写回文件夹，再走既有 commit_package（它会从磁盘重读）。"""
        package = self.rt.package()
        story, characters = copy.deepcopy(package['story']), package['characters']
        mutate(story, characters)
        (self.folder / 'story.json').write_text(
            json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
        self.rt.commit_package(story, characters, '测试改包')
        return self.rt.package()

    def turn(self, message, action_id=None, confirm=None):
        request = Turn(message=message, action_id=action_id, confirm=confirm)
        return asyncio.run(self.svc.turn(self.s['id'], request))


# ------------------------------------------------ 动作类：真实 Service.turn
class ActionExecutionTests(Base):
    def test_observe_runs_once_and_writes_confirmed_information(self):
        before = self.reload()
        plan = self.plan('observe')
        self.turn('看看街面', plan['action_id'], self.token(plan, before))
        after = self.reload()
        # 线索按既有协议分两层落位：confirmed → facts + heard。
        self.assertIn('石阶上的水痕还是湿的。',
                      [row['text'] for row in after['facts']])
        self.assertIn('石阶上的水痕还是湿的。',
                      [row['text'] for row in after['heard']])
        self.assertEqual(after['time'], before['time'] + 1)     # 缺省 turn_hours
        self.assertIn(plan['action_id'], after['active']['actions_done'])
        # 不能重做：同一个 id 第二次直接被拒，且没有任何副作用。
        with self.assertRaises(ValueError):
            self.turn('再看一次', plan['action_id'], self.token(plan, before))
        self.assertEqual(state_fingerprint(after), state_fingerprint(self.reload()))

    def test_unconfirmed_information_is_heard_only_never_fact(self):
        before = self.reload()
        # 调查：条件未成立时根本拿不到方案（只有公开阻碍）。
        self.assertFalse([p for p in self.plans(before) if p['kind'] == 'investigate'
                          and p['target']['id'] == 'ledger'])
        before['flags']['ledger_open'] = True
        self.store.save_session(before)
        before = self.reload()
        plan = self.plan('investigate', before, 'ledger')
        self.turn('翻账页', plan['action_id'], self.token(plan, before))
        after = self.reload()
        # confirmed=False → 只进 heard，不进 facts；也没有变成主角全知。
        self.assertIn('这一页的米价被人改过。', [row['text'] for row in after['heard']])
        self.assertNotIn('这一页的米价被人改过。', [row['text'] for row in after['facts']])

    def test_ask_uses_author_branch_and_advances_clock(self):
        before = self.reload()
        plan = self.plan('ask', before, 'merchant')
        self.turn('米价怎么说', plan['action_id'], self.token(plan, before))
        after = self.reload()
        self.assertIn('米价三日内涨了两成。', [row['text'] for row in after['heard']])
        self.assertEqual(after['time'], before['time'] + 1)
        # 这回合的 channel 是 action（不是 speech）：既有协议不会因此写在场者信念，
        # 交谈得到的信息只按作者声明（confirmed）进玩家可见层，不凭空变成他人已知。
        self.assertIn('米价三日内涨了两成。', [row['text'] for row in after['facts']])
        self.assertEqual(after['beliefs'], [])

    def test_negotiate_charges_declared_cost_through_existing_ledger(self):
        before = self.reload()
        plan = self.plan('negotiate', before, 'merchant')
        self.assertEqual(plan['action']['effects'][1], {'op': 'resource', 'id': 'coin',
                                                       'delta': -2})
        self.turn('我们各让一步', plan['action_id'], self.token(plan, before))
        after = self.reload()
        self.assertTrue(after['flags']['deal_struck'])
        self.assertEqual(after['local']['resources']['coin'], 8)
        # 账本仍是既有的 local.ledger，没有第二个现金账。
        entry = after['local']['ledger'][-1]
        self.assertEqual((entry['resource'], entry['delta'], entry['before'], entry['after']),
                         ('coin', -2, 10, 8))
        self.assertEqual(len([row for row in after['local']['ledger']
                              if row['resource'] == 'coin']), 1)

    def test_hidden_target_and_secret_branch_never_reach_the_player_view(self):
        view = self.rt.surface(self.reload())
        text = dumped(view['adventure'])
        for hidden in ('cache', '夹层里的匣子', '藏着一张字条', '仓里其实早就空了。'):
            self.assertNotIn(hidden, text)
        self.assertNotIn('spy', text)
        # 秘密话题的答案正文与未发生的结果不出现；未写 public_obstruction 时不泄露其存在。
        self.assertNotIn('藏着一张字条', text)
        self.assertNotIn('仓里其实早就空了。', text)
        # 被作者藏起来的地点不进入冒险行动段：没有 travel 方案，名字也不出现。
        self.assertNotIn('adventure:travel:vault', text)
        self.assertNotIn('粮仓深处', text)

    def test_stale_token_and_foreign_session_are_refused_with_zero_side_effect(self):
        before = self.reload()
        plan = self.plan('observe', before)
        token = self.token(plan, before)
        # 1) 换一个动作 id 用旧凭据：拒绝。
        with self.assertRaises(ValueError):
            self.turn('看看街面', plan['action_id'], 'deadbeef' * 4)
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))
        # 2) 状态推进后旧凭据失效（CAS 仍是 state_version）。
        self.store.save_session(copy.deepcopy(before))       # version += 1
        moved = self.reload()
        with self.assertRaises(ValueError):
            self.turn('看看街面', plan['action_id'], token)
        self.assertEqual(state_fingerprint(moved), state_fingerprint(self.reload()))
        # 3) 另一个旅程的凭据在本旅程不可用。
        other = self.rt.new_session('另一个', 'protagonist')
        other_plan = self.plan('observe', other)
        other_token = free_actions.confirm_token(
            other, self.rt.node(other), other_plan['action'], self.rt.package()['story'])
        fresh = self.reload()
        with self.assertRaises(ValueError):
            self.turn('看看街面', other_plan['action_id'], other_token)
        self.assertEqual(state_fingerprint(fresh), state_fingerprint(self.reload()))

    def test_dynamic_action_requires_a_confirm_token(self):
        before = self.reload()
        plan = self.plan('observe', before)
        with self.assertRaises(ValueError):
            self.turn('看看街面', plan['action_id'])          # 没有 confirm
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))

    def test_unknown_action_and_blocked_target_are_refused_before_side_effects(self):
        before = self.reload()
        with self.assertRaises(ValueError):
            self.turn('随便', 'adventure:investigate:ledger',
                      'x' * 32)      # 条件不成立 → 不在方案列表里 → 未知动作
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))
        with self.assertRaises(ValueError):
            self.turn('随便', 'adventure:observe:vault', 'x' * 32)
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))

    def test_retry_does_not_pay_twice(self):
        before = self.reload()
        plan = self.plan('negotiate', before, 'merchant')
        token = self.token(plan, before)
        self.turn('成交', plan['action_id'], token)
        after = self.reload()
        coin = after['local']['resources']['coin']
        # 同一事件里再执行同一个动作：拒绝（actions_done）。
        with self.assertRaises(ValueError):
            self.turn('再成交一次', plan['action_id'], token)
        self.assertEqual(self.reload()['local']['resources']['coin'], coin)
        self.assertEqual(len([row for row in self.reload()['local']['ledger']
                              if row['resource'] == 'coin']), 1)

    def test_static_event_action_still_works_without_confirm(self):
        before = self.reload()
        self.turn('看看街面', 'look')      # 旧按钮：不传 confirm
        after = self.reload()
        self.assertIn('look', after['active']['actions_done'])
        self.assertEqual(after['time'], before['time'] + 1)

    def test_unusable_dynamic_target_is_not_offered_as_a_button(self):
        # 转交/实例使用没有执行器：出现在 build 里但 supported=False，且 surface 不给 confirm。
        self.s['inventory'] = ['ledger']
        self.store.save_session(self.s)
        view = self.rt.surface(self.reload())
        offers = {row['action_id']: row for row in view['adventure']['plans']}
        self.assertTrue(offers)
        for row in offers.values():
            if not row['supported']:
                self.assertNotIn('confirm', row)
                self.assertEqual(row['execution'], 'unsupported')
            elif row['kind'] in ('observe', 'investigate', 'ask', 'negotiate'):
                self.assertIn('confirm', row)
                self.assertEqual(row['execution'], 'action')


# ------------------------------------------------------- 休息：真实 /wait 等价
class RestExecutionTests(Base):
    def test_rest_with_declared_cost_gets_a_confirm_and_runs_once(self):
        # 事件进行中 + 声明了 costs：它是**可确认**的方案，不是缺口。
        view = self.rt.surface(self.reload())
        rest = [row for row in view['adventure']['plans'] if row['kind'] == 'rest'][0]
        self.assertTrue(rest['supported'])
        self.assertEqual(rest['unsupported'], [])
        self.assertIn('confirm', rest)
        self.assertEqual(rest['costs'], [{'id': 'food', 'name': '口粮', 'amount': 1,
                                          'unit': '份'}])

    def test_rest_runs_through_chat_and_charges_declared_cost(self):
        # 夹具已声明 rest_hours=4；确认方案与模板一致。
        before = self.reload()
        plan = self.plan('rest', before)
        self.assertEqual(plan['duration_hours'], 4)
        self.turn('原地歇一会', plan['action_id'], self.token(plan, before))
        after = self.reload()
        self.assertEqual(after['local']['resources']['food'], before['local']['resources']['food'] - 1)
        self.assertEqual(after['time'], before['time'] + 4)      # 模板声明的 4 小时
        # 账本仍是既有的 local.ledger：只记这一次扣费，没有第二套账。
        coin_rows = [row for row in after['local']['ledger'] if row['resource'] == 'food']
        self.assertEqual([(row['delta'], row['source']) for row in coin_rows],
                         [(-1, 'root_event:' + plan['action_id'])])
        # 没有声明 health 效果 → 血量一分不涨。
        self.assertEqual(self.rt.surface(after)['abilities']['health']['current'],
                         self.rt.surface(before)['abilities']['health']['current'])

    def test_wait_advances_the_single_clock_and_never_heals(self):
        # 先结束事件，让 /wait 这条既有路径可用（与 web 的 wait 路由同一逻辑）。
        self.turn('谈完了', 'done_talk')
        s = self.reload()
        self.assertIsNone(s['active'])
        from app import pressure as pressure_rules
        package = self.rt.package(s['revision'])
        hp_before = self.rt.surface(s)['abilities']['health']['current']
        pressure_rules.advance(s, package['story'], package['characters'], 6,
                               effects=self.rt.effects)
        self.rt.enter(s)
        self.store.save_session(s)
        after = self.reload()
        self.assertEqual(after['time'], s['time'])
        self.assertEqual(self.rt.surface(after)['abilities']['health']['current'], hp_before)


# ------------------------------- 无事件休息：Service.turn 一次 CAS 提交
class LocalActionTests(Base):
    """事件结束后的休息：没有对话轮，但成本/时长/效果必须真实结算。"""

    def close_event(self):
        self.turn('谈完了', 'done_talk')
        session = self.reload()
        self.assertIsNone(session['active'])
        return session

    def local_token(self, plan, session):
        return free_actions.confirm_token(
            session, None, plan['action'], self.rt.package(session['revision'])['story'])

    def test_rest_after_event_charges_and_advances_once(self):
        session = self.close_event()
        plan = self.plan('rest', session)
        version_before = session['state_version']
        time_before = session['time']
        food_before = session['local']['resources']['food']
        self.turn('原地歇一会', plan['action_id'], self.local_token(plan, session))
        after = self.reload()
        self.assertEqual(after['time'], time_before + 4)
        self.assertEqual(after['local']['resources']['food'], food_before - 1)
        # 没有事件 → 不生成新事件：归档里只有刚才结束的那一个，且休息不写回复。
        self.assertIsNone(after['active'])
        self.assertEqual(len(after['archives']), 1)
        self.assertEqual(after['archives'][0]['node'], 'root_event')
        self.assertEqual(len(after['archives'][0]['turns']), 1)   # 仍只有结束那一次
        # 只保存一次：版本 +1，不是 +2。
        self.assertEqual(after['state_version'], version_before + 1)
        self.assertEqual(after['local_actions'][-1]['action'], plan['action_id'])
        self.assertEqual([(row['resource'], row['delta'])
                          for row in after['local']['ledger']], [('food', -1)])

    def test_rest_needs_a_confirm_and_leaves_no_trace_when_refused(self):
        session = self.close_event()
        plan = self.plan('rest', session)
        before = self.reload()
        with self.assertRaises(ValueError):
            self.turn('歇一会', plan['action_id'])                 # 没带 confirm
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))
        with self.assertRaises(ValueError):
            self.turn('歇一会', plan['action_id'], 'deadbeef' * 4)   # 凭据错
        self.assertEqual(state_fingerprint(before), state_fingerprint(self.reload()))

    def test_rest_refuses_when_food_is_short_and_writes_nothing(self):
        session = self.close_event()
        session['local']['resources']['food'] = 0
        self.store.save_session(session)
        session = self.reload()
        package = self.rt.package(session['revision'])
        # 口粮不足时方案本身就不成立（只给拒绝），不会变成免费休息。
        self.assertEqual([p for p in A.build(session, package['story'], package['characters'])
                          if p['kind'] == 'rest'], [])
        refused = [r for r in A.refusals(session, package['story'], package['characters'])
                   if r['kind'] == 'rest']
        self.assertEqual([r['reason'] for r in refused], ['resource'])
        before = state_fingerprint(self.reload())
        with self.assertRaises(ValueError):
            self.turn('歇一会', 'adventure:rest:4', 'x' * 32)
        self.assertEqual(before, state_fingerprint(self.reload()))

    def test_rest_does_not_bypass_observer_mode(self):
        session = self.close_event()
        session['mode'] = 'observer'
        self.store.save_session(session)
        session = self.reload()
        plan = self.plan('rest', session)
        before = state_fingerprint(self.reload())
        with self.assertRaises(ValueError) as caught:
            self.turn('歇一会', plan['action_id'], self.local_token(plan, session))
        self.assertIn('旁观', str(caught.exception))
        self.assertEqual(before, state_fingerprint(self.reload()))

    def test_travel_is_not_accepted_as_a_local_action(self):
        session = self.close_event()
        travel = self.plan('travel', session)
        with self.assertRaises(ValueError) as caught:
            self.rt.local_action(session, travel['action_id'], 'x' * 32)
        self.assertIn('旅行请用地图移动', str(caught.exception))

    def test_intent_and_confirm_work_without_an_active_event(self):
        session = self.close_event()
        plan = self.plan('rest', session)
        p = self.rt.package(session['revision'])
        suggested = free_actions.suggest(session, p['story'], None, '歇一会')
        self.assertTrue(suggested['matched'])
        self.assertEqual(suggested['matched'][0]['action_id'], plan['action_id'])
        described = free_actions.describe(session, p['story'], None, plan['action_id'])
        self.assertEqual(described['action_id'], plan['action_id'])
        self.assertTrue(described['confirm'])


# --------------------------------------------------- 旅行：真实 Runtime.move
class TravelExecutionTests(Base):
    def test_travel_requires_ending_the_event_first(self):
        before = self.reload()
        with self.assertRaises(ValueError):
            self.rt.move(before, 'gate')
        self.assertEqual(self.reload()['location'], 'plaza')

    def test_route_hours_are_honoured_by_move_not_ignored(self):
        self.turn('谈完了', 'done_talk')
        s = self.reload()
        self.assertIsNone(s['active'])
        hours, source = self.rt.travel_hours(s, 'gate')
        self.assertEqual((hours, source), (3, 'route'))     # 作者声明 3h ≠ local 2h
        time_before = s['time']
        self.rt.move(s, 'gate')
        after = self.reload()
        self.assertEqual(after['location'], 'gate')
        self.assertEqual(after['time'], time_before + 3)     # 真实推进 3h
        self.assertIn('gate', after['explored'])
        self.assertEqual(after['characters']['player']['location'], 'gate')

    def test_route_cost_is_charged_in_the_same_move(self):
        self.turn('谈完了', 'done_talk')
        self.commit(lambda story, characters: next(
            t for t in story['mechanics']['adventure']['templates']
            if t['kind'] == 'travel').update(costs={'coin': 2}))
        s = self.reload()
        s['revision'] = self.rt.package()['id']
        self.store.save_session(s)
        s = self.reload()
        coin_before = s['local']['resources']['coin']
        hours, _ = self.rt.travel_hours(s, 'gate')
        time_before = s['time']
        self.rt.move(s, 'gate')
        after = self.reload()
        # 费用、位置、时钟一次性提交；账仍是既有 local.ledger。
        self.assertEqual(after['local']['resources']['coin'], coin_before - 2)
        self.assertEqual(after['location'], 'gate')
        self.assertEqual(after['time'], time_before + hours)
        self.assertEqual([(row['resource'], row['delta'], row['source'])
                          for row in after['local']['ledger']],
                         [('coin', -2, 'move:gate')])

    def test_unaffordable_route_cost_writes_nothing_at_all(self):
        self.turn('谈完了', 'done_talk')
        self.commit(lambda story, characters: next(
            t for t in story['mechanics']['adventure']['templates']
            if t['kind'] == 'travel').update(costs={'coin': 2}))
        s = self.reload()
        s['revision'] = self.rt.package()['id']
        s['local']['resources']['coin'] = 0
        self.store.save_session(s)
        s = self.reload()
        before = state_fingerprint(s)
        with self.assertRaises(ValueError) as caught:
            self.rt.move(s, 'gate')
        self.assertIn('铜币', str(caught.exception))
        # 整次 move 零写：位置、时间、资源都没动。
        self.assertEqual(before, state_fingerprint(self.reload()))

    def test_blocked_route_cannot_be_taken_by_calling_move_directly(self):
        self.turn('谈完了', 'done_talk')
        s = self.reload()
        s['flags']['gate_closed'] = True
        self.store.save_session(s)
        s = self.reload()
        # 反方向路线带条件：已知但被封锁 → move 也走不进去，只给公开阻碍。
        gate_session = copy.deepcopy(s)
        gate_session['location'] = 'gate'
        gate_session['explored'] = ['plaza', 'gate']
        with self.assertRaises(ValueError) as caught:
            self.rt.move(gate_session, 'plaza')
        self.assertIn('闸门关着', str(caught.exception))
        self.assertEqual(gate_session['location'], 'gate')   # 没被改成目标地点

    def test_foreign_world_route_is_refused(self):
        self.turn('谈完了', 'done_talk')
        # 改包要同时写回文件夹：commit_package 从磁盘重读。
        self.commit(lambda story, characters: story['mechanics']['map'].update(
            import_id='mi_ffff1111'))
        s = self.reload()
        # 旅程仍绑定旧 revision：把它重新指到刚提交的版本（真实包更新行为）。
        s['revision'] = self.rt.package()['id']
        self.assertEqual(s['revision'], self.rt.package()['id'])
        with self.assertRaises(ValueError) as caught:
            self.rt.move(s, 'gate')
        self.assertIn('不属于这段旅程的世界', str(caught.exception))
        self.assertEqual(self.reload()['location'], 'plaza')

    def test_travel_plan_in_surface_is_not_a_button_while_event_open(self):
        view = self.rt.surface(self.reload())
        travel = [row for row in view['adventure']['plans'] if row['kind'] == 'travel'][0]
        self.assertEqual(travel['execution'], 'blocked_active_event')
        self.assertIn('先结束当前事件', travel['hint'])
        self.assertNotIn('confirm', travel)
        # 事件结束后同一段变成真实移动入口。
        self.turn('谈完了', 'done_talk')
        view = self.rt.surface(self.reload())
        travel = [row for row in view['adventure']['plans'] if row['kind'] == 'travel'][0]
        self.assertEqual(travel['execution'], 'move')
        self.assertEqual(travel['duration_hours'], 3)


# ---------------------------------------------------- /intent 与 /confirm 入口
class WebEntryTests(Base):
    """/intent 与 /confirm 只传 (session, story, node)，所以它们得在内部拿到动态候选。

    web 一行未改：靠 ``free_actions`` 的 resolver 在包声明了 ``mechanics.adventure``
    时现算方案。这里跑的是真实 FastAPI 入口，不是直接拼凭据。
    """

    def _client(self):
        """真实 FastAPI 应用，数据根指到临时目录。

        ``create_app`` 把故事包/角色包根设为模块级 ``ROOT``，所以这里只在**测试进程内**
        把它 patch 到临时目录；``StaticFiles`` 只要求目录存在，建空目录即可。
        web.py 一个字节未改。
        """
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import web
        (self.root / 'app' / 'static').mkdir(parents=True, exist_ok=True)
        (self.root / 'assets' / 'maps').mkdir(parents=True, exist_ok=True)
        patcher = patch.object(web, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        return TestClient(web.create_app(self.root / 'web.sqlite3'))

    def test_intent_and_confirm_endpoints_hand_out_a_usable_token(self):
        with self._client() as client:
            boot = client.get('/api/bootstrap').json()
            headers = {'X-TextileDream-Token': boot['token']}
            sid = client.post('/api/sessions', headers=headers,
                              json={'title': '接口', 'mode': 'protagonist'}).json()['id']
            # 弱匹配：用作者公开的意图别名（“观察”），而不是猜同义词。
            intent = client.post('/api/sessions/' + sid + '/intent', headers=headers,
                                 json={'text': '观察米市街'}).json()
            self.assertTrue(intent['matched'])
            ids = [row['action_id'] for row in intent['matched']]
            self.assertIn('adventure:observe:plaza', ids)      # 动态候选真的进来了
            row = next(r for r in intent['matched']
                       if r['action_id'] == 'adventure:observe:plaza')
            self.assertTrue(row['confirm'])                     # 且带确认凭据
            described = client.get('/api/sessions/' + sid + '/confirm/adventure:observe:plaza',
                                   headers=headers).json()
            self.assertEqual(described['action_id'], 'adventure:observe:plaza')
            self.assertEqual(described['confirm'], row['confirm'])
            # /chat 用该凭据真的执行成功。
            reply = client.post('/api/sessions/' + sid + '/chat', headers=headers,
                                json={'message': '看看街面',
                                      'action_id': 'adventure:observe:plaza',
                                      'confirm': row['confirm']})
            self.assertEqual(reply.status_code, 200, reply.text)
            body = reply.json()
            # 执行后：这个动态方案已不在候选里（actions_done），时间真的推进了。
            self.assertNotIn('adventure:observe:plaza',
                             [r['action_id'] for r in body['adventure']['plans']])
            self.assertEqual(body['local_state']['clock']['elapsed_hours'], 9)

    def test_static_confirm_endpoint_is_unchanged(self):
        with self._client() as client:
            boot = client.get('/api/bootstrap').json()
            headers = {'X-TextileDream-Token': boot['token']}
            sid = client.post('/api/sessions', headers=headers,
                              json={'title': '接口', 'mode': 'protagonist'}).json()['id']
            described = client.get('/api/sessions/' + sid + '/confirm/look',
                                   headers=headers).json()
            self.assertEqual(described['action_id'], 'look')
            self.assertTrue(described['confirm'])

# ------------------------------------------------ 旧包兼容（无 adventure 块）
# --------------------------------- 世界历史钩子（只读本 revision 的包）
class WorldHistoryContextTests(Base):
    """``current_world_history`` 与 ``history``（对话轮次）是两个不同的键。"""

    def adopt(self, disclosed=True, known_by=None, reveal=None):
        """在包里写入一份最小的 history 块（不经过 store）。"""
        from app import world_history_store as whs
        snapshot = {
            'id': 'hs_' + 'a' * 16, 'import_id': 'mi_abc123', 'base_year': 1200,
            'branch': 'main', 'created': '2026-01-01T00:00:00+00:00',
            'entries': [{'ref': 'annal:one', 'year': 1180, 'kind': 'battle',
                         'region': '上游', 'death_year': 1199, 'fate': '秘密结局'}],
            'disclosure': {'public_refs': ['annal:one'] if disclosed else [],
                           'summaries': {'annal:one': '上游打过一仗'}}}
        if known_by is not None:
            snapshot['entries'][0]['known_by'] = known_by
        if reveal is not None:
            snapshot['entries'][0]['reveal'] = reveal
        snapshot['digest'] = whs.content_hash(snapshot)
        entry = {'snapshot_id': snapshot['id'], 'import_id': 'mi_abc123',
                 'base_year': 1200, 'branch': 'main',
                 'digest': snapshot['digest'],
                 'content_sha256': 'c' * 64, 'snapshot': snapshot}
        block = {'schema': whs.MECHANICS_SCHEMA, 'entries': [entry]}
        self.commit(lambda story, characters: story['mechanics'].update(history=block))
        session = self.reload()
        session['revision'] = self.rt.package()['id']
        self.store.save_session(session)
        return self.reload()

    def test_context_gets_current_world_history_and_keeps_the_dialogue_list(self):
        session = self.adopt()
        context = self.rt.context(session, 'player', '上游', self.svc.preferences())
        self.assertIn('current_world_history', context)
        self.assertEqual(context['current_world_history']['items'][0]['summary'], '上游打过一仗')
        # 旧的 ``history`` 仍是对话轮次列表，没有被动过。
        self.assertIsInstance(context['history'], list)
        self.assertNotIn('death_year', json.dumps(context, ensure_ascii=False))
        self.assertNotIn('秘密结局', json.dumps(context, ensure_ascii=False))
        # surface 上的名字不同，避开 conversations/history 消费方。
        self.assertIn('world_history', self.rt.surface(session))

    def test_old_journey_without_history_gets_no_key(self):
        session = self.reload()
        context = self.rt.context(session, 'player', '上游', self.svc.preferences())
        self.assertNotIn('current_world_history', context)
        self.assertNotIn('world_history', self.rt.surface(session))

    def test_audience_is_honoured_and_npc_sees_only_its_own(self):
        session = self.adopt(known_by=['merchant'])
        package = self.rt.package(session['revision'])
        player = self.rt.context(session, 'player', '上游', self.svc.preferences())
        self.assertNotIn('current_world_history', player)
        npc = self.rt.context(session, 'merchant', '上游', self.svc.preferences())
        self.assertIn('current_world_history', npc)
        self.assertNotIn('world_history', self.rt.surface(session))

    def test_undisclosed_or_flag_gated_entry_stays_out(self):
        session = self.adopt(disclosed=False)
        self.assertNotIn('current_world_history',
                         self.rt.context(session, 'player', '上游', self.svc.preferences()))
        session = self.adopt(reveal='history_known')
        self.assertNotIn('current_world_history',
                         self.rt.context(session, 'player', '上游', self.svc.preferences()))
        session['flags']['history_known'] = True
        self.store.save_session(session)
        session = self.reload()
        context = self.rt.context(session, 'player', '上游', self.svc.preferences())
        self.assertIn('current_world_history', context)

    def test_trim_drops_the_whole_block_never_a_half_line(self):
        session = self.adopt()
        context = self.rt.context(session, 'player', '上游', self.svc.preferences())
        block = context['current_world_history']
        # 预算极小：整块被丢弃，``history`` 列表仍是合法列表，不会出现半句。
        trimmed = trim_context({'history': [], 'current_world_history': {
            'basis': block['basis'], 'items': [dict(block['items'][0])]}}, 10)
        self.assertNotIn('current_world_history', trimmed)
        self.assertEqual(trimmed['history'], [])

    def test_tampered_snapshot_is_refused_at_commit(self):
        self.adopt()
        package = self.rt.package()
        story, characters = copy.deepcopy(package['story']), package['characters']
        story['mechanics']['history']['entries'][0]['snapshot']['entries'][0]['year'] = 1199
        with self.assertRaises(ValueError):
            self.rt.validate_package(story, characters)


# ------------------------------------------------ 旧包兼容（无 adventure 块）
class LegacyPackageTests(Base):
    with_adventure = False

    def test_surface_and_confirm_payload_have_no_adventure_key(self):
        view = self.rt.surface(self.reload())
        self.assertNotIn('adventure', view)
        # 旧包的 /confirm 与自由意图行为不变。
        node = self.rt.node(self.reload())
        described = free_actions.describe(self.reload(), self.rt.package()['story'], node, 'look')
        self.assertEqual(described['action_id'], 'look')
        # 可用动作仍是全部静态动作（无动态方案可追加）。
        self.assertEqual([a['id'] for a in free_actions.available_with(
                         self.reload(), self.rt.package()['story'], node)],
                         [a['id'] for a in node['actions']])

    def test_move_still_uses_local_travel_hours(self):
        s = self.reload()
        self.assertEqual(self.rt.travel_hours(s, 'gate'), (2, 'local.travel_hours'))

    def test_intent_returns_only_static_candidates(self):
        s = self.reload()
        node = self.rt.node(s)
        result = free_actions.suggest(s, self.rt.package()['story'], node, '看看街面')
        self.assertTrue(result['matched'])
        self.assertTrue(all(row['action_id'] in {a['id'] for a in node['actions']}
                            for row in result['matched']))


if __name__ == '__main__':
    unittest.main()
