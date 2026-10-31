# -*- coding: utf-8 -*-
"""冒险行动纯规则：冻结测试。

夹具全部写在本文件里（固定的地点/物品/线索/分支/路线/模板），不读仓库里的故事包，
不连网络、不开服务，唯一用到 Service 的一处是为了证明生成的 action definition 能被
**既有**校验与效果管线接受（不是 mock，也不是自制管线）。
"""
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

ROOT = Path(__file__).resolve().parents[1]
#: ``Runtime.validate_package`` 与 ``Runtime._apply_effects`` 接受的效果 op。
RUNTIME_OPS = {'flag', 'take', 'fact', 'rumor', 'status', 'resource', 'information', 'health'}


# --------------------------------------------------------------------- 夹具
def adventure_block():
    return {
        'version': 1,
        'clues': [
            {'id': 'clue_waterline', 'target': {'kind': 'place', 'id': 'plaza'},
             'effects': [{'op': 'information', 'text': '石阶上的水痕还是湿的。',
                          'known_by': ['player'], 'confirmed': True}]},
            {'id': 'clue_ledger', 'target': {'kind': 'object', 'id': 'ledger'},
             'action_kinds': ['investigate'],
             'requires': {'all_flags': {'ledger_open': True}},
             'public_obstruction': '账页扣着，翻不开。',
             'effects': [{'op': 'information', 'text': '这一页的米价被人改过。',
                          'known_by': ['player']}]},
        ],
        'topics': [
            {'id': 'ask_price', 'kind': 'ask', 'target': {'kind': 'npc', 'id': 'merchant'},
             'answers': [{'when': {}, 'success_text': '他把米价说了一遍。',
                          'effects': [{'op': 'information', 'text': '米价三日内涨了两成。',
                                       'known_by': ['player']}]}]},
            {'id': 'ask_secret', 'kind': 'ask', 'target': {'kind': 'npc', 'id': 'merchant'},
             'answers': [{'when': {'all_flags': {'trusted': True}},
                          'success_text': '他压低声音。',
                          'effects': [{'op': 'information', 'text': '仓里其实早就空了。',
                                       'known_by': ['player']}]}]},
            {'id': 'negotiate_time', 'kind': 'negotiate',
             'answers': [{'when': {}, 'effects': []}]},
        ],
        'routes': [
            {'origin': 'plaza', 'destination': 'gate', 'kind': 'causeway', 'hours': 3,
             'import_id': 'mi_abc123'},
            {'origin': 'gate', 'destination': 'plaza', 'kind': 'causeway',
             'requires': {'not_flags': ['gate_closed']},
             'public_obstruction': '闸门关着，今天过不去。'},
        ],
        'templates': [
            # 作者公开的意图别名：玩家用这些词也能命中（与 free_actions 同一套匹配）。
            {'kind': 'travel', 'target': {'kind': 'place', 'id': 'gate'},
             'label': '过闸去{target}', 'intent_aliases': ['上闸', '过闸']},
            {'kind': 'rest', 'label': '在原处歇 {hours} 小时',
             'intent_aliases': ['休息', '歇一会']},
            {'kind': 'use', 'target': {'kind': 'object', 'id': 'rope'},
             'label': '把{target}系上',
             'effects': [{'op': 'flag', 'id': 'rope_tied', 'value': True}]},
            {'kind': 'give', 'target': {'kind': 'object', 'id': 'rope'},
             'recipients': ['merchant'], 'label': '把{target}交给{npc}'},
        ],
        'rest_hours': 8, 'max_rest_hours': 168,
    }


def story_doc():
    return {
        'id': 'adv-test', 'title': '冒险行动测试', 'premise': '测试用的小世界。',
        'character_package_id': 'adv-test-characters',
        'locations': [
            {'id': 'plaza', 'name': '米市街', 'description': '', 'neighbors': ['gate', 'vault'],
             'scenes': []},
            {'id': 'gate', 'name': '上闸', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'coordinates': [120.5, 30.25]},
            {'id': 'vault', 'name': '粮仓深处', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'visibility': 'author'},
        ],
        'events': [],
        'items': [
            {'id': 'rope', 'name': '麻绳', 'description': '', 'authority': 'engine',
             'location_id': 'plaza'},
            {'id': 'ledger', 'name': '账页', 'description': '', 'authority': 'engine',
             'location_id': 'plaza'},
            {'id': 'cache', 'name': '夹层里的匣子', 'description': '', 'authority': 'engine',
             'location_id': 'plaza', 'visibility': 'author'},
            {'id': 'hammer', 'name': '木槌', 'description': '', 'authority': 'engine',
             'location_id': 'gate'},
        ],
        'mechanics': {
            'local': {'resources': [{'id': 'coin', 'name': '铜币', 'unit': '枚',
                                     'initial': 5, 'maximum': 50},
                                    {'id': 'food', 'name': '口粮', 'unit': '份',
                                     'initial': 1, 'maximum': 9}],
                      'turn_hours': 1, 'travel_hours': 2},
            'map': {'kind': 'civ_atlas', 'import_id': 'mi_abc123'},
            'adventure': adventure_block(),
        },
    }


def characters_doc():
    return {'id': 'adv-test-characters', 'title': '测试角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {'谨慎': 0.6}, 'state': {'疲劳': 0.1}},
        {'id': 'merchant', 'name': '米商', 'role': '次要角色', 'location_id': 'plaza',
         'personality': {'社交': 0.6}, 'state': {}},
        {'id': 'keeper', 'name': '守闸人', 'role': '次要角色', 'location_id': 'gate',
         'personality': {'固执': 0.7}, 'state': {}},
        {'id': 'spy', 'name': '暗处的人', 'role': '次要角色', 'location_id': 'plaza',
         'visibility': 'author', 'personality': {}, 'state': {}},
    ]}


def session_doc():
    return {'id': 's1', 'hero': 'player', 'location': 'plaza', 'time': 8,
            'explored': ['plaza'], 'inventory': [], 'flags': {}, 'completed': [],
            'characters': {'player': {'location': 'plaza'},
                           'merchant': {'location': 'plaza'},
                           'keeper': {'location': 'gate'},
                           'spy': {'location': 'plaza'}},
            'facts': [], 'beliefs': [], 'heard': [], 'state_version': 3,
            'local': {'resources': {'coin': 5, 'food': 1}},
            'active': {'actions_done': []},
            'rewards': {'items': []}}


def plans_of(plans, kind):
    return [plan for plan in plans if plan['kind'] == kind]


def dumped(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def rest_template(story):
    """夹具里第一个 rest 模板（模板顺序可能增删，按种类取更稳）。"""
    return next(t for t in story['mechanics']['adventure']['templates'] if t['kind'] == 'rest')


# ------------------------------------------------------------------ 结构/校验
class ContractTests(unittest.TestCase):
    def test_absent_block_is_a_no_op(self):
        story = story_doc()
        story['mechanics'].pop('adventure')
        self.assertIsNone(A.config(story))
        self.assertEqual(A.build(session_doc(), story, characters_doc()), [])
        self.assertEqual(A.refusals(session_doc(), story, characters_doc()), [])
        self.assertTrue(A.suggest(session_doc(), story, '看看', characters_doc())['unjudged'])

    def test_wrong_version_and_unknown_fields_are_refused(self):
        story = story_doc()
        story['mechanics']['adventure']['version'] = 2
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())
        story = story_doc()
        story['mechanics']['adventure']['clues'][0]['text'] = '白送一句'
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())

    def test_cross_references_are_checked(self):
        story = story_doc()
        story['mechanics']['adventure']['clues'][0]['target']['id'] = 'nowhere'
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())
        story = story_doc()
        story['mechanics']['adventure']['topics'][0]['answers'][0]['effects'][0]['known_by'] = ['ghost']
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())
        story = story_doc()
        story['mechanics']['adventure']['routes'][0]['origin'] = 'gate'
        story['mechanics']['adventure']['routes'][0]['destination'] = 'vault'
        story['mechanics']['adventure']['routes'][0]['import_id'] = None
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())   # 非邻接：移动管线会拒绝
        story = story_doc()
        give = next(t for t in story['mechanics']['adventure']['templates']
                    if t['kind'] == 'give')
        give['recipients'] = []
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())   # give 必须点名接收人
        story = story_doc()
        story['mechanics']['adventure']['templates'].append(
            {'kind': 'observe', 'check': {'attribute': 'magic', 'difficulty': 0.5}})
        with self.assertRaises(ValueError):
            A.validate(story, characters_doc())   # 检定必须引用六项属性

    def test_declared_plans_map_onto_the_existing_action_schema(self):
        story, session = story_doc(), session_doc()
        session['inventory'] = ['rope']
        plans, refused = A.scan(session, story, characters_doc())
        self.assertTrue(plans)
        for plan in plans:
            if plan['action'] is None:
                # 没有 action 的只有两种情况：交给既有管线（旅行/等待）或如实标缺口。
                self.assertTrue(plan.get('travel') or plan.get('wait')
                                or not plan['supported'])
                continue
            action = plan['action']
            self.assertIsInstance(action['id'], str)
            self.assertTrue(action['label'])
            for op in {effect['op'] for effect in action.get('effects', [])}:
                self.assertIn(op, RUNTIME_OPS)
            for rid in (action.get('costs') or {}):
                self.assertIn(rid, {'coin', 'food'})
            if 'duration_hours' in action:
                self.assertIsInstance(action['duration_hours'], int)
                self.assertTrue(0 <= action['duration_hours'] <= 168)
            if action.get('check'):
                self.assertIn(action['check']['attribute'],
                              ('talent', 'strength', 'agility', 'wisdom', 'social', 'resilience'))
            # 既有摘要函数能直接吃这份 action：字段就位、不带未发生的结果。
            summary = free_actions.summarise(action, story)
            self.assertEqual(summary['action_id'], action['id'])
            self.assertNotIn('success_text', summary)
            self.assertNotIn('failure_text', summary)


# ----------------------------------------------------------------- 八类方案
class PlanTests(unittest.TestCase):
    def setUp(self):
        self.story, self.session, self.characters = story_doc(), session_doc(), characters_doc()

    def scan(self):
        return A.scan(self.session, self.story, self.characters)

    def test_observe_and_investigate_reveal_only_bound_clues(self):
        plans, refused = self.scan()
        observe = plans_of(plans, 'observe')
        self.assertEqual([p['target']['id'] for p in observe], ['plaza'])
        self.assertEqual([e['text'] for e in observe[0]['action']['effects']],
                         ['石阶上的水痕还是湿的。'])
        # 调查：条件未成立 → 只有公开阻碍，不含条件名与线索正文。
        self.assertEqual(plans_of(plans, 'investigate'), [])
        blocked = [r for r in refused if r['kind'] == 'investigate']
        self.assertEqual([r['text'] for r in blocked], ['账页扣着，翻不开。'])
        self.session['flags']['ledger_open'] = True
        plans, refused = self.scan()
        investigate = plans_of(plans, 'investigate')
        self.assertEqual([p['target']['id'] for p in investigate], ['ledger'])
        self.assertEqual([e['text'] for e in investigate[0]['action']['effects']],
                         ['这一页的米价被人改过。'])

    def test_ask_and_negotiate_only_use_author_branches(self):
        plans, refused = self.scan()
        asks = plans_of(plans, 'ask')
        self.assertEqual([p['target']['id'] for p in asks], ['merchant'])
        self.assertEqual([e['text'] for e in asks[0]['action']['effects']],
                         ['米价三日内涨了两成。'])
        # 没有条件成立的分支：明确不裁定，且分支正文不出现。
        unruled = [r for r in refused if r['action_id'] == 'adventure:ask:merchant:ask_secret']
        self.assertEqual(len(unruled), 1)
        self.assertEqual(unruled[0]['reason'], 'unruled')
        self.assertNotIn('仓里其实早就空了。', dumped([A.public(p, self.story) for p in plans]
                                                     + refused))
        # 在场才谈：守闸人在上闸，不在米市街。
        self.assertEqual([p['target']['id'] for p in plans_of(plans, 'negotiate')], ['merchant'])
        self.session['characters']['keeper']['location'] = 'plaza'
        plans, _ = self.scan()
        self.assertEqual(sorted(p['target']['id'] for p in plans_of(plans, 'negotiate')),
                         ['keeper', 'merchant'])

    def test_hidden_npc_and_hidden_item_are_never_targets(self):
        plans, refused = self.scan()
        text = dumped([A.public(p, self.story) for p in plans] + refused)
        self.assertNotIn('暗处的人', text)
        self.assertNotIn('spy', text)
        self.assertNotIn('夹层里的匣子', text)
        self.assertNotIn('cache', text)

    def test_take_and_use_and_give_respect_owner_and_instance(self):
        self.session['inventory'] = ['rope']
        self.session['rewards'] = {'items': [
            {'id': 'itm_a', 'owner': 'player', 'name': '木牌'},
            {'id': 'itm_b', 'owner': 'keeper', 'name': '别人的东西'}]}
        plans, _ = self.scan()
        takes = plans_of(plans, 'take')
        self.assertEqual([p['target']['id'] for p in takes], ['ledger'])
        self.assertEqual(takes[0]['action']['effects'], [{'op': 'take', 'id': 'ledger'}])
        uses = plans_of(plans, 'use')
        by_source = {p['target']['id']: p for p in uses}
        self.assertEqual(by_source['rope']['source'], 'legacy_inventory')
        self.assertTrue(by_source['rope']['supported'])
        self.assertEqual(by_source['rope']['action']['effects'],
                         [{'op': 'flag', 'id': 'rope_tied', 'value': True}])
        # 实例：没有执行器 → 不产出 action、不虚构 op，并如实标注。
        self.assertIsNone(by_source['itm_a']['action'])
        self.assertFalse(by_source['itm_a']['supported'])
        self.assertEqual(by_source['itm_a']['unsupported'], ['instance_effect'])
        self.assertNotIn('itm_b', by_source)
        # 转交：只有作者点名的接收人，且在場；没有转移执行器。
        gives = plans_of(plans, 'give')
        self.assertEqual([(p['target']['id'], p['recipient']['id']) for p in gives],
                         [('rope', 'merchant')])
        self.assertFalse(gives[0]['supported'])
        self.assertEqual(gives[0]['unsupported'], ['inventory_handover'])
        self.assertIsNone(gives[0]['action'])

    def test_rest_advances_time_and_never_heals_by_default(self):
        plans, _ = self.scan()
        rest = plans_of(plans, 'rest')[0]
        self.assertEqual(rest['duration_hours'], 8)
        self.assertEqual(rest['action']['duration_hours'], 8)
        self.assertNotIn('effects', rest['action'])
        self.assertTrue(rest['supported'])
        self.assertEqual(rest['wait'], {'hours': 8, 'charges': False})
        self.assertEqual(A.rest(self.session, self.story, 0)['duration_hours'], 0)
        with self.assertRaises(ValueError):
            A.rest(self.session, self.story, 169)
        with self.assertRaises(ValueError):
            A.rest(self.session, self.story, -1)
        with self.assertRaises(ValueError):
            A.rest(self.session, self.story, True)
        # 声明了费用/效果的休息同样是**可执行**的：它走既有 action 管线（charge → effects
        # → pressure.advance 一个事务），所以 supported=True、没有 unsupported 标记。
        rest_template(self.story)['costs'] = {'food': 1}
        rest = plans_of(A.build(self.session, self.story, self.characters), 'rest')[0]
        self.assertTrue(rest['supported'])
        self.assertEqual(rest['unsupported'], [])
        self.assertEqual(rest['action']['costs'], {'food': 1})
        # 没声明 health 就绝不会出现回血 op。
        self.assertNotIn('health', {e['op'] for e in rest['action'].get('effects', [])})

    def test_template_condition_blocks_the_plan_instead_of_a_dead_button(self):
        # 模板自带的 requires 不成立时，不发方案（否则调用方拿到一个必被 Runtime 拒的 id）。
        self.story['mechanics']['adventure']['clues'][0]['requires'] = {'all_flags': {'wet': True}}
        self.session['flags']['wet'] = True
        self.story['mechanics']['adventure']['templates'].append(
            {'kind': 'observe', 'label': '仔细观察{target}',
             'requires': {'all_flags': {'lantern': True}},
             'public_obstruction': '太黑了，看不清。'})
        plans, refused = self.scan()
        self.assertEqual(plans_of(plans, 'observe'), [])
        blocked = [r for r in refused if r['kind'] == 'observe']
        self.assertEqual([r['text'] for r in blocked], ['太黑了，看不清。'])
        self.session['flags']['lantern'] = True
        self.assertEqual(len(plans_of(self.scan()[0], 'observe')), 1)

    def test_rest_without_food_is_refused_not_silently_free(self):
        self.session['local']['resources']['food'] = 0
        rest_template(self.story)['costs'] = {'food': 1}
        refused = [r for r in A.refusals(self.session, self.story, self.characters)
                   if r['kind'] == 'rest']
        self.assertEqual(len(refused), 1)
        self.assertIn('口粮', refused[0]['text'])
        with self.assertRaises(ValueError):
            A.rest(self.session, self.story, 8)


# ------------------------------------------------------------------- 旅行
class TravelTests(unittest.TestCase):
    def setUp(self):
        self.story, self.session, self.characters = story_doc(), session_doc(), characters_doc()

    def travel(self):
        return plans_of(A.build(self.session, self.story, self.characters), 'travel')

    def test_only_known_neighbours_become_plans(self):
        rows = self.travel()
        self.assertEqual([p['travel']['destination'] for p in rows], ['gate'])
        # 未公开的 vault 不在方案里，也不在拒绝理由里，更不计数。
        text = dumped(rows + A.refusals(self.session, self.story, self.characters))
        self.assertNotIn('vault', text)
        self.assertNotIn('粮仓深处', text)

    def test_route_declaration_drives_hours_and_says_where_they_came_from(self):
        row = self.travel()[0]
        self.assertEqual(row['duration_hours'], 3)
        self.assertEqual(row['duration_source'], 'route')
        self.assertTrue(row['travel']['route_declared'])
        self.assertEqual(row['travel']['hours_source'], 'route')
        self.assertFalse(row['travel']['charges'])
        self.assertIsNone(row['action'])       # 旅行不由 action 假装，交给 Runtime.move
        # 米市街没有 coordinates：只声明时长，不按坐标推算。
        self.assertIsNone(row['travel']['position']['from'])
        self.assertEqual(row['travel']['position_source'], 'unrecorded')
        self.assertEqual(row['travel']['position']['to'], [120.5, 30.25])

    def test_missing_route_falls_back_to_local_rules_and_says_so(self):
        self.story['mechanics']['adventure']['routes'] = []
        self.session['location'] = 'gate'
        self.session['explored'] = ['plaza', 'gate']
        rows = self.travel()
        self.assertEqual([p['travel']['destination'] for p in rows], ['plaza'])
        self.assertEqual(rows[0]['duration_hours'], 2)
        self.assertEqual(rows[0]['duration_source'], 'local.travel_hours')
        self.assertFalse(rows[0]['travel']['route_declared'])
        self.assertTrue(rows[0]['notes'])      # 「不代表这里有路」必须写在明面上

    def test_condition_blocked_route_returns_public_obstruction_only(self):
        self.session['location'] = 'gate'
        self.session['explored'] = ['plaza', 'gate']
        self.session['flags']['gate_closed'] = True
        self.assertEqual(self.travel(), [])
        refused = [r for r in A.refusals(self.session, self.story, self.characters)
                   if r['kind'] == 'travel']
        self.assertEqual([r['text'] for r in refused], ['闸门关着，今天过不去。'])
        self.assertEqual(refused[0]['reason'], 'condition')
        self.assertNotIn('gate_closed', dumped(refused))

    def test_foreign_or_unverified_world_is_refused(self):
        self.story['mechanics']['map']['import_id'] = 'mi_ffff1111'
        refused = [r for r in A.refusals(self.session, self.story, self.characters)
                   if r['kind'] == 'travel']
        self.assertEqual([r['reason'] for r in refused], ['world_mismatch'])
        self.story['mechanics'].pop('map')
        refused = [r for r in A.refusals(self.session, self.story, self.characters)
                   if r['kind'] == 'travel']
        self.assertEqual([r['reason'] for r in refused], ['world_unverified'])
        self.assertEqual(self.travel(), [])

    def test_route_with_declared_cost_is_paid_from_local_resources(self):
        # 给已有的 travel 模板加费用：作者声明的路费（只认 mechanics.local.resources）。
        next(t for t in self.story['mechanics']['adventure']['templates']
             if t['kind'] == 'travel')['costs'] = {'coin': 1}
        row = self.travel()[0]
        self.assertTrue(row['supported'])
        self.assertEqual(row['unsupported'], [])
        self.assertTrue(row['travel']['charges'])
        self.assertIsNone(row['action'])       # 不在 action 里塞第二个时钟/现金账
        self.assertEqual(row['travel']['costs'], {'coin': 1})

    def test_unaffordable_route_cost_is_refused_not_a_button(self):
        next(t for t in self.story['mechanics']['adventure']['templates']
             if t['kind'] == 'travel')['costs'] = {'coin': 1}
        self.session['local']['resources']['coin'] = 0
        self.assertEqual(self.travel(), [])
        refused = [r for r in A.refusals(self.session, self.story, self.characters)
                   if r['kind'] == 'travel']
        self.assertEqual([r['reason'] for r in refused], ['resource'])
        self.assertIn('铜币', refused[0]['text'])


# ------------------------------------------------------------ 建议与泄露边界
class SuggestTests(unittest.TestCase):
    def setUp(self):
        self.story, self.session, self.characters = story_doc(), session_doc(), characters_doc()
        self.session['inventory'] = ['rope']

    def suggest(self, text):
        return A.suggest(self.session, self.story, text, self.characters)

    def test_public_summary_hides_unhappened_results_and_hidden_text(self):
        plans, refused = A.scan(self.session, self.story, self.characters)
        public = [A.public(p, self.story) for p in plans]
        text = dumped(public + refused)
        for secret in ('石阶上的水痕还是湿的。', '米价三日内涨了两成。', '仓里其实早就空了。',
                       '这一页的米价被人改过。', '他把米价说了一遍。', '他压低声音。'):
            self.assertNotIn(secret, text)
        # 公开摘要只含白名单字段，且不泄漏内部键。
        allowed = {'action_id', 'label', 'costs', 'duration_hours', 'check', 'ends_event',
                   'intent_aliases', 'kind', 'target', 'supported', 'unsupported',
                   'duration_source', 'travel', 'wait', 'source', 'recipient'}
        for row in public:
            self.assertLessEqual(set(row), allowed)

    def test_suggestion_has_no_side_effect_on_state_or_version(self):
        before = dumped(self.session)
        result = self.suggest('前往上闸')
        self.assertTrue(result['matched'])
        self.suggest('休息')
        self.suggest('数星星')
        A.build(self.session, self.story, self.characters)
        A.refusals(self.session, self.story, self.characters)
        A.describe(self.session, self.story, 'adventure:observe:plaza', self.characters)
        self.assertEqual(before, dumped(self.session))
        self.assertEqual(self.session['state_version'], 3)

    def test_travel_and_rest_are_suggested_without_a_confirm_token(self):
        result = self.suggest('前往上闸')
        self.assertEqual(result['matched'][0]['kind'], 'travel')
        self.assertEqual(result['confirm_state'], 'pending_runtime_wiring')
        self.assertNotIn('confirm', result['matched'][0])   # 尚未接线：不签发凭据
        self.assertEqual(self.suggest('休息')['matched'][0]['kind'], 'rest')
        # 缺口方案（转交/实例）不进建议：不要给人一个会失败的确认按钮。
        self.assertNotIn('give', dumped(self.suggest('把麻绳交给米商')))

    def test_negation_and_unknown_intent_stay_unjudged(self):
        self.assertFalse(self.suggest('不去上闸')['matched'])
        unknown = self.suggest('数星星')
        self.assertEqual(unknown['matched'], [])
        self.assertTrue(unknown['unjudged'])
        self.assertIn('不裁定', unknown['note'])

    def test_describe_returns_engine_side_definition(self):
        plan = A.describe(self.session, self.story, 'adventure:observe:plaza', self.characters)
        self.assertEqual(plan['action']['effects'][0]['text'], '石阶上的水痕还是湿的。')
        with self.assertRaises(ValueError):
            A.describe(self.session, self.story, 'adventure:observe:nowhere', self.characters)
        with self.assertRaises(ValueError):
            A.describe(self.session, self.story, 'adventure:investigate:ledger', self.characters)

    def test_done_actions_are_not_offered_again(self):
        self.session['active']['actions_done'] = ['adventure:observe:plaza']
        self.assertEqual(plans_of(A.build(self.session, self.story, self.characters), 'observe'), [])
        # 可重复的类（休息/旅行）不受 actions_done 影响。
        self.assertTrue(plans_of(A.build(self.session, self.story, self.characters), 'rest'))


# ------------------------------------------------- 与既有管线的一次真实对接
class PipelineCompatibilityTests(unittest.TestCase):
    """证明方案里的 action 能被**既有** commit/校验/效果管线接受（真跑，不 mock）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        story = story_doc()
        story['events'] = [
            {'id': 'root_event', 'title': '米市街的清晨', 'location_id': 'plaza',
             'participants': ['player', 'merchant'], 'player_goal': '弄清米价',
             'player_enters': True, 'next_events': [], 'entry_flags': {},
             'exit_flag': 'done_root', 'max_turns': 6,
             'actions': [{'id': 'look', 'label': '看看街面', 'ends_event': True,
                          'success_text': '我先看了看街面。'}]}]
        folder = root / 'StoryPackage' / '玄陆'
        folder.mkdir(parents=True)
        (folder / 'story.json').write_text(json.dumps(story, ensure_ascii=False, indent=2),
                                           encoding='utf-8')
        (folder / '总概.md').write_text('# 冒险行动测试\n\n夹具世界。\n', encoding='utf-8')
        (folder / '知识点').mkdir()
        chars = root / 'character_packages'
        chars.mkdir()
        (chars / 'xuanlu_初始角色包.json').write_text(
            json.dumps(characters_doc(), ensure_ascii=False, indent=2), encoding='utf-8')
        self.root, self.story = root, story
        self.svc = Service(Store(root / 'adv.sqlite3'), root)
        self.svc.provider.configure({'offline': True})

    def tearDown(self):
        self.tmp.cleanup()

    def test_declared_block_passes_package_validation_and_dynamic_action_runs(self):
        rt = self.svc.runtime
        package = rt.package()
        story, characters = package['story'], package['characters']
        session = rt.new_session('对接', 'protagonist')
        # 声明块与既有打包校验共存：这份包能通过 commit_package 的全量校验。
        A.validate(story, characters)
        rt.commit_package(story, characters, '接入冒险行动声明')
        session = rt.new_session('对接-2', 'protagonist')
        node = rt.node(session)
        # 动态动作**不写回故事包**，只在运行时算出来；凭据用既有算法。
        plans = A.build(session, rt.package()['story'], characters)
        plan = next(p for p in plans if p['kind'] == 'observe')
        self.assertEqual([a['id'] for a in node['actions']], ['look'])
        token = free_actions.confirm_token(session, node, plan['action'],
                                           rt.package()['story'])
        # 真跑一次：效果走 Runtime._apply_effects，不经过任何自造管线。
        result = rt.prepare_turn(session, Turn(message='看看街面',
                                              action_id=plan['action']['id'],
                                              confirm=token))
        self.assertEqual(result['outcome'], plan['action']['label'])
        self.assertIn('石阶上的水痕还是湿的。',
                      [row['text'] for row in session['heard']])
        self.assertIn('石阶上的水痕还是湿的。',
                      [row['text'] for row in session['facts']])

    def test_static_action_cannot_take_the_reserved_prefix(self):
        rt = self.svc.runtime
        package = rt.package()
        story, characters = copy.deepcopy(package['story']), package['characters']
        story['events'][0]['actions'].append({'id': 'adventure:observe:plaza',
                                              'label': '假的动态动作',
                                              'ends_event': True})
        with self.assertRaises(ValueError):
            rt.validate_package(story, characters)


if __name__ == '__main__':
    unittest.main()
