"""Town V1 review hardening: knowledge scope, visibility, and hostile stage edits.

Every case here exists because a first-pass implementation leaked something or accepted
something it should have refused. They are deliberately adversarial: the "generator
produced a legal town" path is covered in ``test_towns.py``; here the *stage data* is
edited the way a careless or hostile author could edit it.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import towns
from app.service import Service
from app.storage import Store
from app.town_schema import DraftRequest, TownInput
from app.towns_store import story_towns
from app.web import create_app

ROOT = Path(__file__).resolve().parents[1]


class TownCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'towns.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.towns = self.svc.towns
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, preset='wet_valley', seed='review_seed_1', **overrides):
        site_name = overrides.pop('site_name', '')
        data = towns.preset_entry(preset, seed, site_name=site_name,
                                  story_revision=self.rt.package()['id']).model_dump(mode='json')
        data.update(overrides)
        return data

    def draft(self, preset='wet_valley', seed='review_seed_1', **overrides):
        return self.towns.create(DraftRequest(input=TownInput(**self.entry(preset, seed,
                                                                          **overrides))))

    def publish(self, draft):
        return self.towns.publish(draft['id'], draft['revision'])

    def snapshot_of(self, draft):
        return self.towns.snapshot(self.towns.get_draft(draft['id']))

    def adopt_into(self, preset='cold_mountain_mine', seed='review_seed_2', location=None,
                   site_name=''):
        draft = self.draft(preset, seed, site_name=site_name)
        version = self.publish(draft)['version']
        place = location or self.rt.package()['story']['locations'][0]['id']
        self.towns.adopt(version['id'], self.rt.package()['id'], place)
        return version, place


# ---------------------------------------------------------------- knowledge scope
class KnowledgeScopeTests(TownCase):
    """A town exists somewhere in the world; the player must not learn about it for free."""

    def setUp(self):
        super().setUp()
        self.story_locations = [l['id'] for l in self.rt.package()['story']['locations']]
        self.here = self.story_locations[0]
        self.far = next(l for l in self.story_locations
                        if l not in {self.here, *self.rt.package()['story']['locations'][0]
                                     .get('neighbors', [])})
        self.near = self.rt.package()['story']['locations'][0]['neighbors'][0]
        self.version_here, _ = self.adopt_into('wet_valley', 'scope_seed_a', self.here,
                                                site_name='此处镇')
        self.version_far = self.adopt_into('cold_mountain_mine', 'scope_seed_b', self.far,
                                           site_name='远处镇')[0]
        self.version_near = self.adopt_into('arid_oasis_route', 'scope_seed_c', self.near,
                                            site_name='邻处驿')[0]
        # A town the author kept in the library without placing it anywhere.
        draft = self.draft('wet_valley', 'scope_seed_d')
        self.version_unplaced = self.publish(draft)['version']
        self.towns.adopt(self.version_unplaced['id'], self.rt.package()['id'], None)
        self.session = self.rt.new_session('范围测试', 'protagonist')

    def api(self):
        app = create_app(self.path)
        client = TestClient(app)
        token = client.get('/api/bootstrap').json()['token']
        return client, {'X-TextileDream-Token': token}

    def test_current_place_is_fully_visible(self):
        rows = story_towns(self.rt.package()['story'], self.session['revision'], self.session)
        here = next(r for r in rows if r['version_id'] == self.version_here['id'])
        self.assertEqual(here['town']['knowledge'], 'current')
        self.assertIn('population', here['town'])
        self.assertIn('districts', here['town'])

    def test_never_visited_place_is_absent_entirely(self):
        rows = story_towns(self.rt.package()['story'], self.session['revision'], self.session)
        ids = {r['version_id'] for r in rows}
        self.assertNotIn(self.version_far['id'], ids)
        # Its name must not leak through any other field either.
        blob = json.dumps(rows, ensure_ascii=False)
        far_name = self.version_far['snapshot']['skeleton']['display_name']
        self.assertNotIn(far_name, blob)

    def test_neighbour_is_only_a_rumour(self):
        rows = story_towns(self.rt.package()['story'], self.session['revision'], self.session)
        near = next((r for r in rows if r['version_id'] == self.version_near['id']), None)
        self.assertIsNotNone(near, '邻近地点应能被听说')
        self.assertEqual(near['town']['knowledge'], 'nearby')
        for detailed in ('population', 'chains', 'districts', 'facilities', 'special_sites',
                         'housing', 'style'):
            self.assertNotIn(detailed, near['town'])

    def test_unplaced_town_never_reaches_a_player(self):
        rows = story_towns(self.rt.package()['story'], self.session['revision'], self.session)
        self.assertNotIn(self.version_unplaced['id'], {r['version_id'] for r in rows})

    def test_explored_place_becomes_visible_after_travel(self):
        # Stand in the neighbour and record it as explored, exactly what `move` writes:
        # the event of the starting place must be closed first, which is ordinary play,
        # and is not what this test is about.
        moved = self.svc.store.session(self.session['id'])
        moved['location'] = self.near
        if self.near not in moved['explored']:
            moved['explored'].append(self.near)
        self.svc.store.save_session(moved)
        moved = self.svc.store.session(self.session['id'])
        rows = story_towns(self.rt.package()['story'], moved['revision'], moved)
        near = next(r for r in rows if r['version_id'] == self.version_near['id'])
        self.assertEqual(near['town']['knowledge'], 'current')
        self.assertIn('population', near['town'])

    def test_api_returns_only_known_towns_and_refuses_the_rest(self):
        client, headers = self.api()
        body = client.get(f'/api/sessions/{self.session["id"]}/towns', headers=headers).json()
        ids = {t['version_id'] for t in body['towns']}
        self.assertEqual(ids, {self.version_here['id'], self.version_near['id']})
        # Guessing a version id must not bypass the filter.
        blocked = client.get(
            f'/api/sessions/{self.session["id"]}/towns/{self.version_far["id"]}',
            headers=headers)
        self.assertEqual(blocked.status_code, 400)
        allowed = client.get(
            f'/api/sessions/{self.session["id"]}/towns/{self.version_here["id"]}',
            headers=headers)
        self.assertEqual(allowed.status_code, 200)

    def test_story_towns_without_a_session_returns_nothing(self):
        self.assertEqual(story_towns(self.rt.package()['story'], 'rev'), [])

    def test_model_context_only_summarises_the_current_place(self):
        context = self.rt.context(self.session, 'player', '看看四周', self.svc.preferences())
        summary = context.get('town_summary', '')
        here_name = self.version_here['snapshot']['skeleton']['display_name']
        self.assertIn(here_name, summary)
        for other in (self.version_far, self.version_near, self.version_unplaced):
            self.assertNotIn(other['snapshot']['skeleton']['display_name'], summary)
        self.assertLessEqual(len(summary), 1200)


# ------------------------------------------------------------------ visibility
class VisibilityTests(TownCase):
    """Knowledge, physical access and passage state are three different things."""

    def setUp(self):
        super().setUp()
        draft = self.draft('cold_mountain_mine', 'vis_seed_1')
        snapshot = self.snapshot_of(draft)
        built = snapshot['built']
        # A known private lane, a known sealed ruin, and an unknown but open shrine.
        private = copy.deepcopy(built['districts'][0])
        private.update(id='d_private_lane', name='私巷', access='secret',
                       visibility='public', kind='residential')
        built['districts'].append(private)
        hidden_quarter = copy.deepcopy(built['districts'][0])
        hidden_quarter.update(id='d_hidden', name='不为人知的地段', access='public',
                              visibility='author', kind='craft')
        built['districts'].append(hidden_quarter)
        built['facilities'].append({
            'id': 'f_in_hidden', 'name': '密室工坊', 'kind': 'forge', 'district': 'd_hidden',
            'materials': ['stone'], 'condition': 'good', 'requires_technology': [],
            'public_note': '不该出现在公开投影里的设施', 'secret_note': '',
            'visibility': 'public'})
        built['facilities'].append({
            'id': 'f_in_private', 'name': '私巷水井', 'kind': 'well',
            'district': 'd_private_lane', 'materials': ['stone'], 'condition': 'good',
            'requires_technology': [], 'public_note': '私巷里的井',
            'secret_note': '', 'visibility': 'public'})
        # A sealed site locals know about, and an open site nobody has found.
        built['special_sites'][0].update(status='sealed', visibility='public')
        built['special_sites'][1].update(status='active', visibility='author')
        self.snapshot = snapshot
        towns.validate_snapshot(snapshot)

    def test_sealed_but_known_is_described_as_sealed(self):
        view = towns.public_view(self.snapshot)
        sealed = [s for s in view['special_sites'] if s['name'] ==
                  self.snapshot['built']['special_sites'][0]['name']]
        self.assertEqual(len(sealed), 1, '已知的封闭地点仍应被听说')
        self.assertEqual(sealed[0]['status'], 'sealed')
        self.assertFalse(sealed[0]['enterable'])

    def test_open_but_unknown_site_is_absent(self):
        view = towns.public_view(self.snapshot)
        names = [s['name'] for s in view['special_sites']]
        self.assertNotIn(self.snapshot['built']['special_sites'][1]['name'], names)

    def test_private_but_known_district_is_visible_and_not_enterable(self):
        view = towns.public_view(self.snapshot)
        lane = next(d for d in view['districts'] if d['name'] == '私巷')
        self.assertFalse(lane['enterable'])
        # Its own facility is readable (the lane is known), unlike a hidden parent's.
        self.assertIn('私巷水井', [f['name'] for f in view['facilities']])

    def test_author_only_district_and_its_facilities_never_leak(self):
        view = towns.public_view(self.snapshot)
        blob = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('不为人知的地段', blob)
        self.assertNotIn('密室工坊', blob)
        self.assertNotIn('d_hidden', blob)

    def test_public_warnings_carry_no_internal_text_or_count(self):
        view = towns.public_view(self.snapshot)
        self.assertEqual(len(view['warnings']), 1)
        self.assertIn('不是普查或实测', view['warnings'][0])
        blob = json.dumps(view, ensure_ascii=False)
        for internal in self.snapshot['warnings']:
            self.assertNotIn(internal, blob)
        # An unsurveyed resource is exactly the kind of internal hint that must not show.
        self.assertNotIn('未勘探', blob)

    def test_model_context_uses_the_same_public_view(self):
        draft = self.draft('cold_mountain_mine', 'vis_seed_1')
        version = self.publish(draft)['version']
        place = self.rt.package()['story']['locations'][0]['id']
        self.towns.adopt(version['id'], self.rt.package()['id'], place)
        session = self.rt.new_session('可见性', 'protagonist')
        summary = self.rt.context(session, 'player', '四处看看',
                                  self.svc.preferences())['town_summary']
        for secret in ('不为人知的地段', '密室工坊'):
            self.assertNotIn(secret, summary)
        self.assertNotIn('未勘探', summary)


# ------------------------------------------------------------- hostile edits
class HostileStageEditTests(TownCase):
    """Stage data is author-editable, so every derived number is re-checked."""

    def edited(self, mutate):
        draft = self.draft('cold_mountain_mine', 'hostile_seed_1')
        snapshot = self.snapshot_of(draft)
        mutate(snapshot)
        return snapshot

    def assert_refused(self, snapshot, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            towns.validate_snapshot(snapshot)

    def test_fabricated_capacity_is_refused(self):
        def mutate(snapshot):
            capacity = snapshot['skeleton']['capacity']
            capacity['water_cap'] *= 10
            capacity['local_food_cap'] *= 10
            capacity['import_food_cap'] *= 10
        self.assert_refused(self.edited(mutate), '承载项')

    def test_shrunk_food_need_is_refused(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['staple_need']['amount'] = 1
        self.assert_refused(self.edited(mutate), '口粮需求与人口')

    def test_unsurveyed_resource_as_chain_input_is_refused(self):
        def mutate(snapshot):
            snapshot['input']['resources'].append({
                'id': 'res_hidden_iron', 'kind': 'iron', 'abundance': 0.9,
                'accessibility': 0.9, 'surveyed': False, 'extractable': True,
                'requires_technology': [], 'fuel': 'none'})
            chain = snapshot['socioeconomy']['chains'][1]
            chain['inputs'].append({'resource': 'res_hidden_iron', 'name': '铁矿石',
                                    'amount': 100, 'unit': 't', 'period': 'year'})
        self.assert_refused(self.edited(mutate), '没有可用来源')

    def test_prevented_mining_technology_cannot_appear_in_a_chain(self):
        def mutate(snapshot):
            snapshot['input']['technology'] = ['masonry']
            snapshot['socioeconomy']['chains'][1]['requires_technology'] = ['mine_shaft']
        self.assert_refused(self.edited(mutate), '未申报的技术')

    def test_fuel_that_was_never_surveyed_cannot_power_a_smelter(self):
        def mutate(snapshot):
            for candidate in snapshot['input']['resources']:
                if candidate['kind'] == 'coal':
                    candidate['surveyed'] = False
            snapshot['input']['materials'] = [m for m in snapshot['input']['materials']
                                              if m != 'coal']
        # The smelter chain needs fuel; with coal unsurveyed and no fuel import it dies.
        self.assert_refused(self.edited(mutate), '燃料')

    def test_export_larger_than_supply_is_refused(self):
        def mutate(snapshot):
            chain = next(c for c in snapshot['socioeconomy']['chains']
                         if c['output']['resource'] != 'grain')
            snapshot['socioeconomy']['trade'].append({
                'id': 'tr_export_bogus', 'direction': 'export',
                'resource': chain['output']['resource'], 'kind': 'other',
                'name': chain['output']['resource'],
                'amount': chain['output']['amount'] * 100,
                'unit': chain['output']['unit'], 'period': 'year', 'via': 'roads',
                'requirement': '虚构出口'})
        self.assert_refused(self.edited(mutate), '超过该资源产出')

    def test_food_export_beyond_staple_is_refused(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['trade'].append({
                'id': 'tr_grain_out', 'direction': 'export', 'resource': 'grain',
                'kind': 'grain', 'name': 'grain', 'amount': 100000, 'unit': 't',
                'period': 'year', 'via': 'roads', 'requirement': '虚构粮食出口'})
        self.assert_refused(self.edited(mutate), '出口|口粮')

    def test_unknown_import_path_is_refused(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['trade'][0]['via'] = 'teleport'
        self.assert_refused(self.edited(mutate), '路径')

    def test_import_without_a_declared_dependency_is_refused(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['trade'].append({
                'id': 'tr_import_ghost', 'direction': 'import', 'resource': 'imp_ghost',
                'kind': 'salt', 'name': '凭空来的盐', 'amount': 10, 'unit': 't',
                'period': 'year', 'via': 'roads', 'requirement': '虚构'})
        self.assert_refused(self.edited(mutate), '没有对应的进口依赖声明')

    def test_labour_record_must_match_the_chains(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['labor']['assigned_workers'] += 500
        self.assert_refused(self.edited(mutate), '已分配劳力')

    def test_available_labour_must_follow_the_population(self):
        def mutate(snapshot):
            snapshot['socioeconomy']['labor']['available_workers'] = 10 ** 8
        self.assert_refused(self.edited(mutate), '可用劳力')

    def test_duplicate_ids_in_every_group_are_refused(self):
        def run(edit, pattern):
            draft = self.draft('cold_mountain_mine', 'dup_seed_1')
            snapshot = self.snapshot_of(draft)
            edit(snapshot)
            with self.assertRaisesRegex(ValueError, pattern):
                towns.validate_snapshot(snapshot)

        run(lambda s: s['built']['districts'].append(copy.deepcopy(s['built']['districts'][0])),
            '街区 ID 重复')
        run(lambda s: s['built']['facilities'].append(
            copy.deepcopy(s['built']['facilities'][0])), '设施 ID 重复')
        run(lambda s: s['socioeconomy']['factions'].append(
            copy.deepcopy(s['socioeconomy']['factions'][0])), '势力 ID 重复')
        run(lambda s: s['socioeconomy']['chains'].append(
            copy.deepcopy(s['socioeconomy']['chains'][0])), '生产链 ID 重复')
        run(lambda s: s['built']['special_sites'].append(
            copy.deepcopy(s['built']['special_sites'][0])), '特殊地点 ID 重复')
        run(lambda s: s['story']['events'].append(
            copy.deepcopy(s['story']['events'][0])), '事件候选 ID 重复')
        run(lambda s: s['skeleton']['roads'].append(
            copy.deepcopy(s['skeleton']['roads'][0])), '道路 ID 重复')

    def test_publish_refuses_a_hostile_edit(self):
        """A fabricated capacity must never become a published version.

        Editing one stage only shape-checks that stage, because its downstream stages are
        stale and there is nothing consistent to compare against yet. The whole-snapshot
        validator is what rejects the fabrication; it runs whenever a complete snapshot
        can be assembled — a regeneration that fills the last missing stage, a publish, or
        a snapshot read. Whichever gate is reached first, no version is ever minted.
        """
        draft = self.draft('cold_mountain_mine', 'publish_guard_1')
        snapshot = self.snapshot_of(draft)
        raised = snapshot['skeleton']
        raised['capacity']['water_cap'] *= 5
        moved = self.towns.edit_stage(draft['id'], 'skeleton', raised, draft['revision'])
        refused_by_advance = False
        try:
            for _ in range(3):
                moved = self.towns.advance(draft['id'], moved['revision'])
        except ValueError as error:
            # Regenerating the last stage assembled a complete snapshot, and the
            # cross-stage validator refused the fabricated capacity right there.
            self.assertIn('承载项', str(error))
            refused_by_advance = True
        blocked = self.towns.get_draft(draft['id'])
        publish_refused = snapshot_refused = False
        try:
            self.towns.publish(draft['id'], blocked['revision'])
        except ValueError as error:
            self.assertRegex(str(error), '承载项|尚未完成或已失效')
            publish_refused = True
        try:
            self.towns.snapshot(blocked)
        except ValueError as error:
            self.assertRegex(str(error), '承载项|尚未完成或已失效')
            snapshot_refused = True
        # The fabrication was caught by a real gate, and nothing was ever published.
        self.assertTrue(refused_by_advance or publish_refused or snapshot_refused)
        self.assertTrue(publish_refused and snapshot_refused)
        self.assertEqual(self.towns.list_versions(), [])





if __name__ == '__main__':
    unittest.main()
