# -*- coding: utf-8 -*-
"""判定 v2 的真实 HTTP 接线测试（FastAPI TestClient）。

这一份**不 mock 规则核心**：``checks`` / ``runtime`` / ``free_actions`` 全是真实实现，
只有模型供应商（``provider.complete``）被打桩——因为 v2 从不依赖模型裁定状态。

覆盖：

* ``GET /api/sessions/{id}/confirm/{action}?push=<id>`` 的推送与凭据切换；
* 旧凭据配上新 push 必须失效，且**零副作用**（钱、时间、``checks``、``actions_done`` 都不动）；
* 加码费用不足时 ``confirm`` 直接 400，不写任何状态；
* ``POST /api/sessions/{id}/chat`` 的 ``push`` 字段与 ``Turn`` 契约；
* ``GET /api/sessions/{id}`` 的 ``clocks`` / ``last_check`` 公开投影（隐藏钟、隐藏因素、
  NPC 底线与信任数值都不出现）；
* 旧包（没有 ``mechanics.checks``）在 HTTP 上逐字节兼容：没有 ``clocks``/``last_check``、
  动作仍是两字段、仍走 ``attribute_v1``。

全部在临时根 + 临时 SQLite 里跑；不启动常驻服务，不联网。
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.test_checks_v2 import characters_doc, story_doc


class HttpBase(unittest.TestCase):
    story_kwargs = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        from app.web import create_app
        self.app = create_app(self.root / 'http.sqlite3')
        self.svc = self.app.state.service
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.story = story_doc(**self.story_kwargs)
        self.characters = characters_doc()
        self.rt.commit_package(self.story, self.characters, 'http v2 测试')
        # 供应商打桩：任何模型调用都失败，证明 v2 不靠模型裁定。
        patch.object(self.svc.provider, 'complete',
                     side_effect=AssertionError('network call')).start()
        self.addCleanup(patch.stopall)
        self.client = TestClient(self.app)
        self.token = self._token()
        self.client.headers.update({'x-textiledream-token': self.token})
        response = self.client.post('/api/sessions',
                                    json={'title': '按 HTTP 玩', 'mode': 'protagonist'})
        self.assertEqual(response.status_code, 200, response.text)
        self.surface = response.json()
        self.session_id = self.surface['id']

    def _token(self):
        # 与浏览器一致：先取 bootstrap（GET /api/bootstrap 也需要 token 头，
        # 但 guard 只对 /api/inner 与 /api/settings 的 GET 强制；bootstrap 是普通 GET）。
        first = TestClient(self.app).get('/api/bootstrap')
        self.assertEqual(first.status_code, 200, first.text)
        return first.json()['token']

    # ---- 工具
    def get_surface(self):
        response = self.client.get('/api/sessions/' + self.session_id)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def confirm(self, action_id, push=None):
        url = '/api/sessions/' + self.session_id + '/confirm/' + action_id
        if push is not None:
            url += '?push=' + push
        return self.client.get(url)

    def reload(self):
        return self.svc.store.session(self.session_id)

    def fingerprint(self):
        s = self.reload()
        return json.dumps({k: v for k, v in s.items() if k != 'state_version'},
                          ensure_ascii=False, sort_keys=True)

    def chat(self, action_id, confirm, push=None, message='做这件事'):
        body = {'message': message, 'action_id': action_id, 'confirm': confirm}
        if push is not None:
            body['push'] = push
        return self.client.post('/api/sessions/' + self.session_id + '/chat', json=body)

    def play(self, action_id, push=None):
        described = self.confirm(action_id, push)
        self.assertEqual(described.status_code, 200, described.text)
        payload = described.json()
        response = self.chat(action_id, payload['confirm'], push, payload['label'])
        self.assertEqual(response.status_code, 200, response.text)
        return payload, response.json()


class ConfirmPushTests(HttpBase):
    def test_push_query_returns_its_own_token_and_preview(self):
        plain = self.confirm('pitch')
        greasy = self.confirm('pitch', 'grease')
        self.assertEqual(plain.status_code, 200, plain.text)
        self.assertEqual(greasy.status_code, 200, greasy.text)
        plain, greasy = plain.json(), greasy.json()
        self.assertNotEqual(plain['confirm'], greasy['confirm'])
        self.assertIn('check', plain)
        block = plain['check']['v2']
        self.assertEqual(block['position'], 'risky')
        self.assertIn(block['chance'], ('大', '中', '小'))
        self.assertIn('dc', block)
        self.assertEqual([row['id'] for row in block['push_options']], ['grease', 'favor'])
        self.assertTrue(block['push_options'][0]['cost_text'])
        self.assertEqual(block['clock']['label'], '说服行会')
        self.assertNotIn('refused_text', json.dumps(block, ensure_ascii=False))

    def test_unknown_push_is_refused_without_writing(self):
        before = self.fingerprint()
        response = self.confirm('pitch', 'no-such-push')
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(before, self.fingerprint())

    def test_old_token_with_new_push_is_refused_before_any_side_effect(self):
        stale = self.confirm('pitch').json()['confirm']
        fresh = self.confirm('pitch', 'grease').json()['confirm']
        self.assertNotEqual(stale, fresh)
        before = self.fingerprint()
        response = self.chat('pitch', stale, 'grease')
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn('重新确认', response.json()['detail'])
        self.assertEqual(before, self.fingerprint())

    def test_unaffordable_push_cost_is_a_400_with_zero_side_effects(self):
        s = self.reload()
        s['local']['resources']['pence'] = 1
        self.svc.store.save_session(s)
        before = self.fingerprint()
        response = self.confirm('pitch', 'grease')
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn('加码付不起', response.json()['detail'])
        self.assertEqual(before, self.fingerprint())
        # 同一个动作在不加码时仍然可以确认与执行。
        described = self.confirm('pitch')
        self.assertEqual(described.status_code, 200, described.text)
        response = self.chat('pitch', described.json()['confirm'], None)
        self.assertEqual(response.status_code, 200, response.text)

    def test_push_cost_is_charged_and_the_chat_returns_the_settled_surface(self):
        payload, surface = self.play('pitch', 'grease')
        saved = self.reload()
        self.assertEqual(saved['local']['resources']['pence'], 16)
        self.assertEqual(saved['checks'][-1]['push'], 'grease')
        self.assertEqual(saved['checks'][-1]['rules_version'], 'd20_v2')
        check = surface['last_check']
        self.assertEqual(check['rules_version'], 'd20_v2')
        self.assertEqual(check['push']['id'], 'grease')
        self.assertEqual(check['total'], check['kept'] + check['modifier'])
        self.assertEqual(check['margin'], check['total'] - check['dc'])
        self.assertEqual([row['id'] for row in surface['clocks']], ['sway', 'suspicion'])


class ChatContractTests(HttpBase):
    def test_chat_accepts_push_and_rejects_an_unknown_one(self):
        described = self.confirm('pitch', 'favor').json()
        response = self.chat('pitch', described['confirm'], 'favor')
        self.assertEqual(response.status_code, 200, response.text)
        saved = self.reload()
        self.assertEqual(saved['checks'][-1]['push'], 'favor')
        trust = saved['development']['broker']['relationships']['player']['trust']
        self.assertAlmostEqual(trust, .4)
        # 未知加码在契约层（或动作层）被拒，且没有第二次执行。
        response = self.chat('pitch', described['confirm'], 'nope')
        self.assertIn(response.status_code, (400, 422))

    def test_chat_requires_a_confirm_token_for_v2_checks(self):
        # v2：骰子/档位/钟/目击全由引擎裁定，所以带检定的动作必须先确认拿到凭据。
        before = self.fingerprint()
        response = self.chat('pitch', None)
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn('先确认', response.json()['detail'])
        self.assertEqual(before, self.fingerprint())

    def test_boundary_refusal_is_reported_and_changes_nothing(self):
        s = self.reload()
        before_money = s['local']['resources']['pence']
        before_time = s['time']
        payload, surface = self.play('bully')
        self.assertEqual(payload['check']['v2']['refused'], '这触到了他的底线')
        check = surface['last_check']
        self.assertEqual(check['tier'], 'refused')
        self.assertFalse(check['rolled'])
        saved = self.reload()
        self.assertEqual(saved['local']['resources']['pence'], before_money)
        self.assertEqual(saved['time'], before_time)
        self.assertEqual(saved['checks'], [])
        self.assertEqual(saved['active']['actions_done'], [])

    def test_broken_confirm_is_refused(self):
        before = self.fingerprint()
        response = self.chat('pitch', '0' * 32)
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(before, self.fingerprint())


class SurfacePrivacyTests(HttpBase):
    def test_surface_exposes_clocks_and_last_check_but_no_secrets(self):
        surface = self.get_surface()
        self.assertEqual([row['id'] for row in surface['clocks']], ['sway', 'suspicion'])
        self.assertNotIn('last_check', surface)
        self._play_pitch()
        surface = self.get_surface()
        check = surface['last_check']
        self.assertEqual(check['tier_label'], '大成功' if check['tier'] == 'critical'
                         else check['tier_label'])
        dumped = json.dumps(surface, ensure_ascii=False)
        for secret in ('hidden_clock', '暗中的钟', '他知道你的秘密',
                       'boundaries', 'interests', 'trust_weight'):
            self.assertNotIn(secret, dumped)

    def _play_pitch(self):
        described = self.confirm('pitch').json()
        response = self.chat('pitch', described['confirm'])
        self.assertEqual(response.status_code, 200, response.text)

    def test_hidden_factor_never_appears_in_http_projections(self):
        s = self.reload()
        s['flags']['secret_known'] = True
        self.svc.store.save_session(s)
        confirm = self.confirm('pitch').json()
        dumped = json.dumps(confirm, ensure_ascii=False)
        self.assertNotIn('他知道你的秘密', dumped)
        self.assertEqual(confirm['check']['v2']['factors'], [])
        response = self.chat('pitch', confirm['confirm'])
        self.assertEqual(response.status_code, 200, response.text)
        dumped = json.dumps(response.json(), ensure_ascii=False)
        self.assertNotIn('他知道你的秘密', dumped)

    def test_surface_action_rows_carry_the_v2_block(self):
        rows = {row['id']: row for row in self.get_surface()['actions']}
        self.assertIn('check_v2', rows['pitch'])
        self.assertEqual(rows['bully']['check_v2']['refused'], '这触到了他的底线')
        self.assertNotIn('check_v2', rows['leave'])

    def test_intent_candidates_are_public_only(self):
        response = self.client.post('/api/sessions/' + self.session_id + '/intent',
                                    json={'text': '我想谈买卖'})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        for row in data['matched']:
            dumped = json.dumps(row, ensure_ascii=False)
            for secret in ('success_text', 'failure_text', '他知道你的秘密',
                           'boundaries', 'interests'):
                self.assertNotIn(secret, dumped)
            if row.get('check') and row['check'].get('v2'):
                self.assertIn('chance', row['check']['v2'])


class SceneJudgmentIntentTests(HttpBase):
    """scene_judgment 意图入口必须把**真实人物文档**逐层传下去。

    回归点：`scene_judgment.intent()` 曾不传 characters，v2 包的候选预览会退化成
    「主角属性按 50」的降级——确认时看到的把握与真正结算不一致。这里用**非 50**
    的主属性，把三段路径（intent 候选 / confirm 预览 / chat 审计）对齐。
    """

    def setUp(self):
        super().setUp()
        # 把主角的社交与智慧抬到 80：修正 +6，和默认 50（+0）应当明显不同。
        story = json.loads(json.dumps(self.story))
        characters = json.loads(json.dumps(self.characters))
        for actor in characters['characters']:
            if actor['id'] == 'player':
                actor['attributes']['social'] = 80
                actor['attributes']['wisdom'] = 80
        story['mechanics']['scene_judgment'] = {
            'version': 1, 'law': '当地规矩',
            'actors': {'broker': {'values': '看重利润',
                                  'choices': {'ok': {'line': '他点了头'}}}}}
        self.rt.commit_package(story, characters, 'v2 + 短篇裁定')
        self.story, self.characters = story, characters
        response = self.client.post('/api/sessions',
                                    json={'title': '短篇意图', 'mode': 'protagonist'})
        self.assertEqual(response.status_code, 200, response.text)
        self.session_id = response.json()['id']
        self.assertLessEqual(
            max(abs(v - 50) for v in
                [a for a in self.characters['characters']
                 if a['id'] == 'player'][0]['attributes'].values()), 30)

    def test_offline_intent_preview_and_confirm_agree_with_real_attributes(self):
        response = self.client.post('/api/sessions/' + self.session_id + '/intent',
                                    json={'text': '我想谈买卖'})
        self.assertEqual(response.status_code, 200, response.text)
        matched = response.json()['matched']
        self.assertTrue(matched, '离线档应该能匹配到谈买卖')
        row = next(item for item in matched if item['action_id'] == 'pitch')
        candidate = row['check']['v2']
        confirm = self.confirm('pitch').json()['check']['v2']
        # 三段必须一致：真实属性 → 把握与 DC 相同。
        self.assertEqual(candidate['chance'], confirm['chance'])
        self.assertEqual(candidate['dc'], confirm['dc'])
        # 属性 80 → 修正 +6，不是降级的 +0。
        described = self.confirm('pitch').json()
        response = self.chat('pitch', described['confirm'], None, '谈买卖')
        self.assertEqual(response.status_code, 200, response.text)
        audit = self.reload()['checks'][-1]
        self.assertEqual(audit['dc'], confirm['dc'])
        self.assertEqual(audit['modifier'], 6)
        self.assertEqual(audit['total'], audit['kept'] + 6)

    def test_online_intent_uses_the_same_preview_as_offline(self):
        # 只桩“选动作”这一步；规则核心与预览全真。
        self.svc.provider.configure({'offline': False, 'api_key': 'local-test'})
        seen = {}

        async def choose(system, data, **kwargs):
            seen['choices'] = data['choices']
            return {'action_id': 'pitch', 'reason': '玩家想谈买卖'}, {}

        with patch.object(self.svc.provider, 'complete', side_effect=choose):
            response = self.client.post('/api/sessions/' + self.session_id + '/intent',
                                        json={'text': '我想谈买卖'})
        self.assertEqual(response.status_code, 200, response.text)
        matched = response.json()['matched']
        self.assertEqual([row['action_id'] for row in matched], ['pitch'])
        # 送给模型的选项也必须带真实属性算出的把握，而不是降级值。
        offered = next(row for row in seen['choices'] if row['action_id'] == 'pitch')
        confirm = self.confirm('pitch').json()['check']['v2']
        self.assertEqual(offered['check']['v2']['chance'], confirm['chance'])
        self.assertEqual(offered['check']['v2']['dc'], confirm['dc'])
        self.assertEqual(matched[0]['check']['v2']['dc'], confirm['dc'])


def adventure_story(**kwargs):
    """在 v2 包上叠加一份**真能生出带检定动态方案**的 adventure 声明。

    ``observe`` 需要一个绑定到当前地点的线索才会出方案，模板上的 ``check`` 才会成为
    那个方案的检定（否则只有休息/取物这类无检定方案，看不出属性修正）。
    """
    story = story_doc(**kwargs)
    story['mechanics']['adventure'] = {
        'version': 1,
        'clues': [{'id': 'look_hall', 'target': {'kind': 'place', 'id': 'hall'},
                   'effects': [{'op': 'flag', 'id': 'saw_hall', 'value': True}],
                   'action_kinds': ['observe']}],
        'templates': [{'kind': 'observe', 'label': '观察{target}',
                       'check': {'attribute': 'wisdom', 'difficulty': .5},
                       'success_text': '我把厅堂看了一遍。',
                       'failure_text': '没看出什么。'}],
    }
    return story


class AdventurePreviewTests(unittest.TestCase):
    """动态方案（``Runtime.adventure_surface``）的预览也必须用真实属性。

    回归点：``adventure_actions.public(plan, story)`` 曾漏传 ``session`` / ``node`` /
    ``characters``，v2 包的动态方案预览会退化成「主角属性按 50」——与真正结算不一致。

    这里用真实可执行的 ``adventure:observe:hall``（wisdom 检定），把 80 与 50 两种属性
    分开跑，并断言三段对齐：surface 预览 = /confirm 预览 = 真实 ``checks.plan``。
    """

    def make(self, wisdom):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        from app.web import create_app
        app = create_app(root / 'adventure.sqlite3')
        svc = app.state.service
        svc.provider.configure({'offline': True})
        story = adventure_story()
        characters = characters_doc()
        for actor in characters['characters']:
            if actor['id'] == 'player':
                actor['attributes']['wisdom'] = wisdom
        svc.runtime.commit_package(story, characters, 'v2 + 动态方案')
        client = TestClient(app)
        client.headers.update({'x-textiledream-token':
                               TestClient(app).get('/api/bootstrap').json()['token']})
        response = client.post('/api/sessions',
                               json={'title': '动态方案', 'mode': 'protagonist'})
        self.assertEqual(response.status_code, 200, response.text)
        return svc, story, characters, client, response.json()['id']

    def plan_of(self, svc, story, characters, session_id, action_id):
        session = svc.store.session(session_id)
        from app import adventure_actions
        for plan in adventure_actions.scan(session, story, characters)[0]:
            if plan['action_id'] == action_id:
                return plan
        return None

    def test_observe_plan_exists_and_uses_real_attributes(self):
        action_id = 'adventure:observe:hall'
        high = self.make(80)
        low = self.make(50)
        svc_h, story_h, chars_h, client_h, sid_h = high
        svc_l, story_l, chars_l, client_l, sid_l = low

        # 1) 夹具真的生成了那个带检定的可执行方案。
        high_plan = self.plan_of(svc_h, story_h, chars_h, sid_h, action_id)
        self.assertIsNotNone(high_plan, '夹具必须生成 adventure:observe:hall 方案')
        self.assertTrue(high_plan['supported'])
        self.assertEqual(high_plan['action']['check'],
                         {'attribute': 'wisdom', 'difficulty': .5})

        # 2) surface 预览用真属性：80 → 修正 +6，50 → 0。
        def surface_v2(client, session_id):
            surface = client.get('/api/sessions/' + session_id).json()
            adventure = surface.get('adventure')
            self.assertIsNotNone(adventure, 'surface 必须带 adventure 段')
            rows = [row for row in adventure['plans']
                    if row['action_id'] == action_id]
            self.assertEqual(len(rows), 1, 'surface 里必须恰好有那个方案')
            self.assertIsNotNone(rows[0].get('check'), '这个方案必须带检定')
            return rows[0]['check']['v2']

        block_h = surface_v2(client_h, sid_h)
        block_l = surface_v2(client_l, sid_l)
        self.assertEqual(block_h['dc'], block_l['dc'])          # 同一个 DC 来源
        self.assertNotEqual(block_h['chance'], block_l['chance'],
                            '属性 80 与 50 的把握必须不同（否则就是降级成了 50）')

        # 3) surface 预览 == /confirm 预览 == 真实 checks.plan（逐属性分别校对）。
        from app import checks, free_actions
        expected_mod = {80: 6, 50: 0}
        for wisdom, block, (svc, story, chars, client, sid) in (
                (80, block_h, (svc_h, story_h, chars_h, client_h, sid_h)),
                (50, block_l, (svc_l, story_l, chars_l, client_l, sid_l))):
            session = svc.store.session(sid)
            node = svc.runtime.node(session) if session.get('active') else None
            confirm = client.get('/api/sessions/' + sid + '/confirm/' + action_id)
            self.assertEqual(confirm.status_code, 200, confirm.text)
            confirmed = confirm.json()['check']['v2']
            self.assertEqual(confirmed['chance'], block['chance'])
            self.assertEqual(confirmed['dc'], block['dc'])
            action = free_actions.resolve_action(session, story, node, action_id)
            self.assertIsNotNone(action)
            truth = checks.plan(session, story, chars, node, action)
            self.assertEqual(truth['total_mod'], expected_mod[wisdom])
            self.assertEqual(truth['dc'], block['dc'])

    def test_modifier_differs_between_wisdom_80_and_50(self):
        from app import checks, free_actions
        action_id = 'adventure:observe:hall'
        modifiers = {}
        for wisdom in (80, 50):
            svc, story, characters, client, session_id = self.make(wisdom)
            session = svc.store.session(session_id)
            node = svc.runtime.node(session) if session.get('active') else None
            action = free_actions.resolve_action(session, story, node, action_id)
            self.assertIsNotNone(action)
            planned = checks.plan(session, story, characters, node, action)
            modifiers[wisdom] = planned['total_mod']
        self.assertEqual(modifiers[80], 6)
        self.assertEqual(modifiers[50], 0)


class LegacyHttpTests(unittest.TestCase):
    """没有 ``mechanics.checks`` 的包：HTTP 接口逐字节兼容。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        from app.web import create_app
        self.app = create_app(self.root / 'legacy.sqlite3')
        self.svc = self.app.state.service
        self.svc.provider.configure({'offline': True})
        self.characters = characters_doc()
        self.svc.runtime.commit_package(story_doc(no_checks=True), self.characters, '旧包')
        patch.object(self.svc.provider, 'complete',
                     side_effect=AssertionError('network call')).start()
        self.addCleanup(patch.stopall)
        self.client = TestClient(self.app)
        token = TestClient(self.app).get('/api/bootstrap').json()['token']
        self.client.headers.update({'x-textiledream-token': token})
        self.surface = self.client.post(
            '/api/sessions', json={'title': '旧包', 'mode': 'protagonist'}).json()
        self.session_id = self.surface['id']

    def test_no_v2_keys_and_two_field_actions(self):
        surface = self.client.get('/api/sessions/' + self.session_id).json()
        self.assertNotIn('clocks', surface)
        self.assertNotIn('last_check', surface)
        self.assertEqual(set(surface['actions'][0]), {'id', 'label'})
        self.assertEqual(surface['actions'][0]['label'], '谈买卖')

    def test_confirm_and_chat_still_use_attribute_v1(self):
        response = self.client.get('/api/sessions/' + self.session_id + '/confirm/pitch')
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(set(payload['check']), {'attribute', 'difficulty'})
        self.assertNotIn('push_options', json.dumps(payload, ensure_ascii=False))
        response = self.client.post('/api/sessions/' + self.session_id + '/chat',
                                    json={'message': '谈买卖', 'action_id': 'pitch',
                                          'confirm': payload['confirm']})
        self.assertEqual(response.status_code, 200, response.text)
        saved = self.svc.store.session(self.session_id)
        self.assertEqual(saved['checks'][-1]['rules_version'], 'attribute_v1')
        self.assertNotIn('clocks', saved)
        self.assertNotIn('last_check', self.client.get(
            '/api/sessions/' + self.session_id).json())

    def test_push_query_is_ignored_by_old_packages(self):
        response = self.client.get('/api/sessions/' + self.session_id
                                   + '/confirm/pitch?push=grease')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('confirm', response.json())
        response = self.client.post('/api/sessions/' + self.session_id + '/chat',
                                    json={'message': '谈买卖', 'action_id': 'pitch',
                                          'confirm': '0' * 32})
        self.assertEqual(response.status_code, 400, response.text)


if __name__ == '__main__':
    unittest.main()
