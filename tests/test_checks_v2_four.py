"""Margin-four rules and real HTTP acceptance; isolated roots and SQLite only."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import checks, free_actions
from app.web import create_app
from tools.oracle_example import build_example, WEAKNESS, COOPERATION, MISDIRECTION
from tools.playable_scenes import town_day
from tests.test_checks_v2 import story_doc, characters_doc


class FourRuleTests(unittest.TestCase):
    def config(self, **kwargs):
        return checks.ChecksConfig.model_validate(
            {'version': 2, 'tier_mode': 'margin_four', **kwargs})

    def test_default_boundaries_and_naturals(self):
        cfg = self.config()
        for margin, tier in [(11, 'critical'), (10, 'critical'), (9, 'success'),
                             (0, 'success'), (-1, 'failure'), (-9, 'failure'),
                             (-10, 'disaster'), (-11, 'disaster')]:
            for natural in (1, 11, 20):
                self.assertEqual(checks.margin_tier(natural, margin, cfg), tier)
        override = self.config(natural_override=True)
        self.assertEqual(checks.margin_tier(20, -30, override), 'critical')
        self.assertEqual(checks.margin_tier(1, 30, override), 'disaster')

    def test_thresholds_strict_and_ordered(self):
        for raw in [{'critical': True}, {'critical': '10'}, {'success': 1.5},
                    {'critical': 0}, {'disaster': 0}, {'unknown': 2}]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.config(thresholds=raw)
        with self.assertRaises(ValueError):
            self.config(natural_override=1)
        with self.assertRaises(ValueError):
            checks.ChecksConfig.model_validate({'version': 2, 'thresholds': {}})
        cfg = self.config(thresholds={'critical': 8, 'success': 2, 'disaster': -7})
        for margin, tier in [(8, 'critical'), (2, 'success'), (1, 'failure'),
                             (-6, 'failure'), (-7, 'disaster')]:
            self.assertEqual(checks.margin_tier(11, margin, cfg), tier)

    def test_total_modifiers_position_and_frozen_rules(self):
        story = story_doc()
        story['mechanics']['checks']['tier_mode'] = 'margin_four'
        action = copy.deepcopy(story['events'][0]['actions'][0])
        action['check'].pop('auto')
        chars = characters_doc()
        session = {'hero': 'player', 'location': 'hall', 'inventory': ['manifest'],
                   'flags': {}, 'characters': {'player': {'status': {'疲劳': .5}},
                                              'broker': {'location': 'hall'}}}
        node = story['events'][0]
        planned = checks.plan(session, story, chars, node, action, 'grease')
        self.assertEqual(planned['total_mod'], 2 - 2 + 2 + 2)
        seed = next(str(i) for i in range(1000) if checks.roll_d20(str(i))['kept'] == 11)
        versions = []
        for position in checks.POSITIONS:
            action['check']['position'] = position
            row = checks.resolve(session, story, chars, node, action, 'grease', seed)
            self.assertEqual(row['total'], 15)
            self.assertEqual(row['margin'], 15 - planned['dc'])
            versions.append(row['tier'])
        self.assertEqual(len(set(versions)), 1)
        token = free_actions.confirm_token(session, node, action, story)
        story['mechanics']['checks']['thresholds'] = {'critical': 100}
        self.assertNotEqual(token, free_actions.confirm_token(session, node, action, story))
        frozen = checks.resolve(session, story, chars, node, action, seed=seed, planned=planned)
        self.assertEqual(frozen['config'].thresholds.critical, 10)
        fresh = checks.resolve(session, story, chars, node, action, seed=seed)
        self.assertEqual(fresh['config'].thresholds.critical, 100)

    def test_legacy_and_new_tier_validation(self):
        story, chars = story_doc(), characters_doc()
        self.assertEqual(checks.config(story).tier_mode, 'legacy_five')
        story['events'][0]['actions'][0]['check']['tiers'] = {'partial': {'text': '旧结果'}}
        checks.validate_all(story, chars)
        story['mechanics']['checks']['tier_mode'] = 'margin_four'
        with self.assertRaises(ValueError):
            checks.validate_all(story, chars)
        self.assertEqual(checks.tier_for('risky', 20, -30), 'critical')
        self.assertEqual(checks.tier_for('risky', 11, -1), 'partial')

    def test_dc_contract_and_legacy_pure_dc_remains_rejected(self):
        from app.runtime import Runtime
        for bad_check in ({'attribute': 'wisdom'},
                          {'attribute': 'wisdom', 'dc': True},
                          {'attribute': 'wisdom', 'dc': '15'},
                          {'attribute': 'wisdom', 'dc': 31},
                          {'attribute': 'wisdom', 'dc': 15, 'difficulty': 2},
                          {'attribute': 'wisdom', 'dc': 15, 'difficulty': float('nan')}):
            package = build_example()
            package['story']['events'][0]['actions'][0]['check'] = bad_check
            with self.subTest(check=bad_check), self.assertRaises(ValueError):
                checks.validate_all(package['story'], package['characters'])
        legacy = story_doc(no_checks=True)
        legacy['events'][0]['actions'][0]['check'] = {'attribute': 'social', 'dc': 15}
        # The unchanged v1 contract requires difficulty; no fallback into v2.
        with self.assertRaises(KeyError):
            Runtime.validate_package(None, legacy, characters_doc())

    def test_preview_probability_uses_custom_thresholds_and_natural_override(self):
        story = story_doc()
        story['mechanics']['checks'] = {'version': 2, 'tier_mode': 'margin_four',
                                       'thresholds': {'critical': 30, 'success': 5,
                                                      'disaster': -10}}
        action = {'id': 'test', 'check': {'attribute': 'wisdom', 'dc': 11}}
        chars = characters_doc()
        chars['characters'][0]['attributes']['wisdom'] = 50
        session = {'hero': 'player', 'characters': {}, 'flags': {}, 'inventory': []}
        node = {'id': 'node', 'participants': []}
        self.assertEqual(checks.plan(session, story, chars, node, action)['chance'], .25)
        action['check']['dc'] = 30
        self.assertEqual(checks.plan(session, story, chars, node, action)['chance'], 0)
        story['mechanics']['checks']['natural_override'] = True
        self.assertEqual(checks.plan(session, story, chars, node, action)['chance'], .05)
        action['check']['dc'] = 2
        chars['characters'][0]['attributes']['wisdom'] = 100
        self.assertEqual(checks.plan(session, story, chars, node, action)['chance'], .95)
        token = free_actions.confirm_token(session, node, action, story)
        story['mechanics']['checks']['natural_override'] = False
        self.assertNotEqual(token, free_actions.confirm_token(session, node, action, story))

    def test_town_day_new_export_explicit_four(self):
        data = town_day()
        cfg = checks.validate_all(data['story'], data['characters'])
        self.assertEqual(cfg.tier_mode, 'margin_four')
        self.assertEqual(checks.rules_version(cfg), 'd20_margin_v3')


class OracleHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app(Path(self.tmp.name) / 'oracle.sqlite3')
        self.svc = self.app.state.service
        self.svc.provider.configure({'offline': True})
        self.addCleanup(patch.stopall)
        patch.object(self.svc.provider, 'complete',
                     side_effect=AssertionError('network call')).start()
        self.package = build_example()
        self.svc.runtime.commit_package(**self.package, note='isolated oracle acceptance')
        self.client = TestClient(self.app)
        self.client.headers['x-textiledream-token'] = self.client.get('/api/bootstrap').json()['token']

    def start(self, seed):
        response = self.client.post('/api/sessions', json={'title': 'oracle', 'mode': 'protagonist'})
        self.assertEqual(response.status_code, 200, response.text)
        sid = response.json()['id']
        session = self.svc.store.session(sid)
        session['seed'] = seed
        self.svc.store.save_session(session)
        return sid

    def seed_for(self, face):
        return next(str(i) for i in range(2000)
                    if checks.roll_d20(f'{i}:oracle:ask')['kept'] == face)

    def confirm(self, sid):
        response = self.client.get(f'/api/sessions/{sid}/confirm/ask')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def play(self, sid, token):
        return self.client.post(f'/api/sessions/{sid}/chat', json={
            'message': '献贡询问', 'action_id': 'ask', 'confirm': token})

    def test_four_real_branches_and_tribute_replay(self):
        # Attribute 50, DC15: maximum natural20 only succeeds by default.
        # Critical is exercised with a real +10 attribute, not a patched tier.
        for tier, face, value in [('critical', 15, 100), ('success', 15, 50),
                                  ('failure', 14, 50), ('disaster', 5, 50)]:
            with self.subTest(tier=tier):
                package = copy.deepcopy(self.package)
                package['characters']['characters'][0]['attributes']['wisdom'] = value
                self.svc.runtime.commit_package(**package, note=tier)
                sid = self.start(self.seed_for(face))
                preview = self.confirm(sid)
                projected = json.dumps(preview, ensure_ascii=False)
                for secret in (WEAKNESS, COOPERATION, MISDIRECTION, '108穴说法是'):
                    self.assertNotIn(secret, projected)
                response = self.play(sid, preview['confirm'])
                self.assertEqual(response.status_code, 200, response.text)
                public = response.json()['last_check']
                saved = self.svc.store.session(sid)
                self.assertEqual(public['tier'], tier)
                self.assertEqual(public['rules_version'], 'd20_margin_v3')
                self.assertEqual(public['dc'], preview['check']['v2']['dc'])
                self.assertEqual(public['total'], public['kept'] + public['modifier'])
                self.assertEqual(public['margin'], public['total'] - public['dc'])
                self.assertEqual(saved['local']['resources']['offering'], 2)
                self.assertEqual(len(saved['checks']), 1)
                texts = [r['text'] for r in saved['heard']]
                self.assertEqual(WEAKNESS in texts, tier in ('critical', 'success'))
                self.assertEqual(COOPERATION in texts, tier == 'critical')
                self.assertEqual(MISDIRECTION in texts, tier == 'disaster')
                self.assertEqual(bool(saved['flags'].get('paris_contact_lead')), tier == 'critical')
                self.assertNotIn(MISDIRECTION, [r['text'] for r in saved['facts']])
                self.assertEqual(self.svc.runtime.package(saved['revision'])['story']['knowledge'],
                                 self.package['story']['knowledge'])
                replay = self.play(sid, preview['confirm'])
                self.assertEqual(replay.status_code, 400)
                self.assertEqual(self.svc.store.session(sid)['local']['resources']['offering'], 2)
                if tier == 'disaster':
                    heard = next(r for r in saved['heard'] if r['text'] == MISDIRECTION)
                    self.assertEqual(heard['distortion'], 1)
                    self.assertNotIn('source_fact', heard)
                    self.assertNotIn(WEAKNESS, json.dumps(response.json(), ensure_ascii=False))

    def test_old_revision_remains_five_after_new_commit(self):
        legacy = story_doc()
        self.svc.runtime.commit_package(legacy, characters_doc(), 'old five')
        sid = self.start('old')
        revision = self.svc.store.session(sid)['revision']
        self.svc.runtime.commit_package(**self.package, note='new four')
        old = self.svc.runtime.package(revision)['story']
        self.assertEqual(checks.config(old).tier_mode, 'legacy_five')
        response = self.client.get(f'/api/sessions/{sid}/confirm/pitch')
        self.assertEqual(response.json()['check']['v2']['rules_version'], 'd20_v2')

    def test_dc_takes_priority_over_supplied_valid_difficulty_over_http(self):
        package = copy.deepcopy(self.package)
        package['story']['events'][0]['actions'][0]['check']['difficulty'] = .1
        self.svc.runtime.commit_package(**package, note='dc precedence')
        sid = self.start(self.seed_for(14))
        preview = self.confirm(sid)
        self.assertEqual(preview['check']['v2']['dc'], 15)
        response = self.play(sid, preview['confirm'])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['last_check']['dc'], 15)
        self.assertEqual(response.json()['last_check']['tier'], 'failure')

    def test_real_http_refusal_is_not_a_tier_and_does_not_charge(self):
        package = copy.deepcopy(self.package)
        package['story']['mechanics']['scene_judgment'] = {
            'version': 1, 'law': '神庙规矩', 'actors': {
                'priestess': {'values': '谨慎', 'choices': {'quiet': {'line': '女祭司沉默。'}}}}}
        package['story']['mechanics']['checks']['social'] = {
            'priestess': {'boundaries': ['forbidden'], 'refusal_text': '不谈此事'}}
        package['story']['events'][0]['actions'][0]['check']['social'] = {
            'target': 'priestess', 'violates': ['forbidden']}
        self.svc.runtime.commit_package(**package, note='refusal')
        sid = self.start('refusal')
        preview = self.confirm(sid)
        self.assertEqual(preview['check']['v2']['refused'], '不谈此事')
        response = self.play(sid, preview['confirm'])
        self.assertEqual(response.status_code, 200, response.text)
        public = response.json()['last_check']
        self.assertEqual(public['status'], 'refused')
        self.assertIsNone(public['tier'])
        self.assertEqual(public['refused'], '不谈此事')
        saved = self.svc.store.session(sid)
        self.assertEqual(saved['local']['resources']['offering'], 3)
        self.assertEqual(saved['checks'], [])
        self.assertEqual(saved['active']['actions_done'], [])

    def test_real_attribute_and_fatigue_push_preview_settlement_agree(self):
        package = copy.deepcopy(self.package)
        package['characters']['characters'][0]['attributes']['wisdom'] = 80
        package['story']['mechanics']['checks']['push'] = [
            {'id': 'strain', 'label': '再努力', 'bonus': 2, 'fatigue': .5}]
        self.svc.runtime.commit_package(**package, note='frozen push')
        sid = self.start(self.seed_for(10))
        response = self.client.get(f'/api/sessions/{sid}/confirm/ask?push=strain')
        self.assertEqual(response.status_code, 200, response.text)
        preview = response.json()
        response = self.client.post(f'/api/sessions/{sid}/chat', json={
            'message': '献贡询问', 'action_id': 'ask', 'push': 'strain',
            'confirm': preview['confirm']})
        self.assertEqual(response.status_code, 200, response.text)
        public = response.json()['last_check']
        self.assertEqual(public['modifier'], 8)
        self.assertEqual(public['total'], 18)
        self.assertEqual(public['dc'], preview['check']['v2']['dc'])
        self.assertEqual(public['tier'], 'success')
        saved = self.svc.store.session(sid)
        self.assertEqual(saved['characters']['player']['status']['疲劳'], .5)

    def test_auto_has_no_dice_and_refusal_is_status(self):
        package = copy.deepcopy(self.package)
        action = package['story']['events'][0]['actions'][0]
        action['check']['auto'] = {'max_dc': 30}
        self.svc.runtime.commit_package(**package, note='auto')
        sid = self.start('auto')
        response = self.play(sid, self.confirm(sid)['confirm'])
        self.assertEqual(response.status_code, 200, response.text)
        public = response.json()['last_check']
        self.assertEqual(public['status'], 'auto')
        self.assertEqual(public['tier'], 'success')
        self.assertEqual(public['dice'], [])
        self.assertIsNone(public['kept'])
        self.assertFalse(public['rolled'])
        refusal = checks.execution_refusal(package['story'], '公开拒绝理由')
        self.assertIsNone(refusal['tier'])
        self.assertEqual(refusal['status'], 'refused')
        self.assertEqual(refusal['refused'], '公开拒绝理由')


if __name__ == '__main__':
    unittest.main()
