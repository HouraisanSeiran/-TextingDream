"""Town V1: determinism, cross-stage validation, CAS, publication, isolation.

Every test runs on its own temporary database; ``data/`` and ``StoryPackage/玄陆``
are never touched.
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
from app.towns_store import TownError, content_hash, package_entries
from app.web import create_app

ROOT = Path(__file__).resolve().parents[1]


class TownCase(unittest.TestCase):
    """Base fixture: temp DB, offline provider, one generated draft."""

    preset = 'wet_valley'
    seed = 'town_test_seed_1'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'towns.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.towns = self.svc.towns
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------------- helpers
    def entry(self, preset=None, seed=None, **overrides):
        data = towns.preset_entry(preset or self.preset, seed or self.seed,
                                  story_revision=self.rt.package()['id']).model_dump(mode='json')
        data.update(overrides)
        return data

    def draft(self, preset=None, seed=None, **overrides):
        return self.towns.create(DraftRequest(input=TownInput(**self.entry(preset, seed,
                                                                          **overrides))))

    def publish(self, draft):
        return self.towns.publish(draft['id'], draft['revision'])

    def story(self):
        return self.rt.package()['story']

    def adopt(self, version, location=None, revision=None):
        pkg = self.rt.package()
        return self.towns.adopt(version['id'], revision or pkg['id'],
                                location or pkg['story']['locations'][0]['id'])


# --------------------------------------------------------------- determinism
class DeterminismTests(TownCase):
    def test_same_request_same_everything_including_ids(self):
        first = towns.generate_all(self.entry())
        second = towns.generate_all(self.entry())
        self.assertEqual(json.dumps(first, sort_keys=True, ensure_ascii=False),
                         json.dumps(second, sort_keys=True, ensure_ascii=False))
        self.assertEqual(towns.town_id(self.entry()), towns.town_id(self.entry()))
        # No uuid-shaped ids and no clock in a generated value.
        blob = json.dumps(first, ensure_ascii=False)
        for marker in ('uuid', '2026-', 'T00:', 'Z"'):
            self.assertNotIn(marker, blob)

    def test_different_seed_changes_detail_but_not_hard_limits(self):
        one = towns.generate_all(self.entry(seed='seed_aaaaaaaa'))
        two = towns.generate_all(self.entry(seed='seed_bbbbbbbb'))
        self.assertNotEqual(towns.town_id(self.entry(seed='seed_aaaaaaaa')),
                            towns.town_id(self.entry(seed='seed_bbbbbbbb')))
        # The carrying capacity is a function of the terrain, not of the seed.
        self.assertEqual(one['skeleton']['capacity']['water_cap'],
                         two['skeleton']['capacity']['water_cap'])

    def test_ids_are_stable_across_a_restart(self):
        draft = self.draft()
        snapshot = self.towns.snapshot(draft)
        restart = Service(Store(self.path), ROOT)
        again = restart.towns.snapshot(restart.towns.get_draft(draft['id']))
        self.assertEqual(snapshot['town_id'], again['town_id'])
        self.assertEqual(json.dumps(snapshot, sort_keys=True),
                         json.dumps(again, sort_keys=True))


# --------------------------------------------------------- environmental delta
class EnvironmentDifferenceTests(unittest.TestCase):
    """The three presets must differ in *explainable* ways, not just by name."""

    def test_three_regions_produce_different_structures(self):
        built = {}
        for preset in towns.PRESETS:
            entry = towns.preset_entry(preset, 'delta_seed_1')
            built[preset] = towns.generate_all(entry.model_dump(mode='json'))

        wet = built['wet_valley']
        mine = built['cold_mountain_mine']
        oasis = built['arid_oasis_route']

        # Population differ, and for a stated reason.
        self.assertNotEqual(wet['socioeconomy']['population']['total'],
                            mine['socioeconomy']['population']['total'])
        self.assertLess(mine['skeleton']['capacity']['local_food_cap'],
                        wet['skeleton']['capacity']['local_food_cap'])

        # Wet valley: timber walls, tiled roof, drained streets, a grain chain.
        self.assertIn('grain', {c['output']['resource'] for c in wet['socioeconomy']['chains']})
        self.assertNotIn('iron_bar', {c['output']['resource']
                                      for c in wet['socioeconomy']['chains']})
        self.assertEqual(wet['built']['style']['roof'], 'gable_tile')
        self.assertIn(wet['built']['style']['drainage'], ('open_gutter', 'stone_channel'))
        # Cold mountain: stone + steep slate, iron/coal chains, fuel input, road closure.
        self.assertEqual(mine['built']['style']['wall_note'][:2], '石墙')
        self.assertEqual(mine['built']['style']['roof'], 'steep_slate')
        self.assertIn('iron_bar', {c['output']['resource']
                                   for c in mine['socioeconomy']['chains']})
        fuel = [f for c in mine['socioeconomy']['chains'] for f in c['inputs']]
        self.assertTrue(fuel, '矿镇冶炼必须申报燃料输入')
        self.assertGreater(mine['skeleton']['roads'][0]['seasonal_closed_days'], 30)
        # A mountain town has almost no arable land, so its food is imported, not grown.
        self.assertEqual(mine['socioeconomy']['staple']['amount'], 0)
        self.assertGreater(mine['skeleton']['capacity']['import_food_cap'], 0)
        # Arid oasis: mud brick + flat roof, no grain, salt+textile, grain imported.
        self.assertEqual(oasis['built']['style']['roof'], 'flat_mud')
        self.assertIn('mud_brick', oasis['built']['style']['materials'])
        self.assertNotIn('grain', {c['output']['resource']
                                   for c in oasis['socioeconomy']['chains']})
        self.assertTrue(any(t['direction'] == 'import' and t['kind'] == 'grain'
                            for t in oasis['socioeconomy']['trade']))
        # The unsurveyed iron in the oasis never becomes output or an export.
        self.assertNotIn('iron_bar', {c['output']['resource']
                                      for c in oasis['socioeconomy']['chains']})
        self.assertFalse(any(t['direction'] == 'export' and 'iron' in t['name']
                             for t in oasis['socioeconomy']['trade']))

    def test_water_scarcity_changes_the_water_cap(self):
        wet = towns.generate_all(
            towns.preset_entry('wet_valley', 'w_seed_1').model_dump(mode='json'))
        dry = towns.preset_entry('wet_valley', 'w_seed_1').model_dump(mode='json')
        dry['water'] = {**dry['water'], 'daily_capacity_l': 2000}
        dry['imports'] = []
        scarce = towns.generate_all(dry)
        self.assertLess(scarce['skeleton']['capacity']['water_cap'],
                        wet['skeleton']['capacity']['water_cap'])
        self.assertLessEqual(scarce['socioeconomy']['population']['total'],
                             scarce['skeleton']['capacity']['water_cap'])


# ------------------------------------------------------------ invalid input
class InvalidInputTests(TownCase):
    def assert_zero_writes(self):
        self.assertEqual(self.towns.list_drafts(), [])
        self.assertEqual(self.towns.list_versions(), [])

    def test_no_water_and_no_import_is_refused_with_no_write(self):
        data = self.entry()
        data['water'] = {'source': 'none', 'reliability': 0.0, 'daily_capacity_l': 0,
                         'storage': 'none', 'distance_km': 0}
        data['imports'] = []
        with self.assertRaises(ValueError):
            self.towns.create(DraftRequest(input=TownInput(**data)))
        self.assert_zero_writes()

    def test_imports_without_any_route_is_refused(self):
        data = self.entry('cold_mountain_mine')
        data['transport'] = {**data['transport'], 'road': 'none', 'water_route': False,
                             'portage': False}
        with self.assertRaises(ValueError):
            self.towns.create(DraftRequest(input=TownInput(**data)))
        self.assert_zero_writes()

    def test_bool_nan_and_unknown_fields_are_refused(self):
        for bad in ({'elevation_m': True}, {'elevation_m': float('nan')},
                    {'slope_deg': '3'}, {'unknown_field': 1}):
            data = self.entry()
            data['terrain'] = {**data['terrain'], **bad}
            with self.assertRaises(ValueError):
                TownInput(**data)
            self.assert_zero_writes()

    def test_social_mode_evidence_is_mandatory_and_exclusive(self):
        data = self.entry()
        with self.assertRaisesRegex(ValueError, '现实参考档'):
            TownInput(**{**data, 'realistic': None})
        both = {**data, 'artistic': {'prototypes': ['x'], 'inventions': ['y'],
                                     'design_goal': 'z', 'counterexamples': ''}}
        with self.assertRaisesRegex(ValueError, '现实参考档不能同时'):
            TownInput(**both)
        art = self.entry('arid_oasis_route')
        with self.assertRaisesRegex(ValueError, '艺术夸张档'):
            TownInput(**{**art, 'artistic': None})
        self.assert_zero_writes()

    def test_surveyed_resource_without_technology_is_refused(self):
        data = self.entry('cold_mountain_mine')
        data['technology'] = ['masonry']
        with self.assertRaisesRegex(ValueError, '技术'):
            TownInput(**data)
        self.assert_zero_writes()

    def test_nonsense_edit_is_refused_and_leaves_the_draft_untouched(self):
        draft = self.draft()
        before = self.towns.get_draft(draft['id'])
        broken = copy.deepcopy(draft['stages'][0]['data'])
        broken['capacity']['population'] = -5
        with self.assertRaises(TownError):
            self.towns.edit_stage(draft['id'], 'skeleton', broken, draft['revision'])
        after = self.towns.get_draft(draft['id'])
        self.assertEqual(before['revision'], after['revision'])
        self.assertEqual(json.dumps(before, sort_keys=True), json.dumps(after, sort_keys=True))

    def test_cross_stage_inconsistency_is_caught_by_the_validator(self):
        draft = self.draft()
        snapshot = self.towns.snapshot(draft)
        tampered = copy.deepcopy(snapshot)
        tampered['socioeconomy']['population']['groups'][0]['share_permille'] = 500
        with self.assertRaisesRegex(ValueError, '1000‰'):
            towns.validate_snapshot(tampered)
        tampered = copy.deepcopy(snapshot)
        tampered['socioeconomy']['labor']['assigned_workers'] = 10 ** 7
        with self.assertRaisesRegex(ValueError, '劳力'):
            towns.validate_snapshot(tampered)
        tampered = copy.deepcopy(snapshot)
        tampered['built']['special_sites'][0]['is_residential'] = True
        with self.assertRaisesRegex(ValueError, '特殊地点'):
            towns.validate_snapshot(tampered)
        tampered = copy.deepcopy(snapshot)
        tampered['story']['events'][0]['executable'] = True
        with self.assertRaises(ValueError):
            towns.validate_snapshot(tampered)


# ------------------------------------------------------------- stage staleness
class StageInvalidationTests(TownCase):
    def test_upstream_edit_marks_every_later_stage_stale(self):
        draft = self.draft()
        self.assertTrue(all('data' in s for s in draft['stages']))
        edited = self.towns.edit_stage(draft['id'], 'skeleton', draft['stages'][0]['data'],
                                       draft['revision'])
        states = {s['name']: (s['stale'], 'data' in s) for s in edited['stages']}
        self.assertEqual(states['skeleton'], (False, True))
        for later in ('socioeconomy', 'built', 'story'):
            self.assertEqual(states[later], (True, False))
        # Publishing an incomplete draft is refused, with no version written.
        with self.assertRaisesRegex(TownError, '尚未完成或已失效'):
            self.towns.publish(draft['id'], edited['revision'])
        self.assertEqual(self.towns.list_versions(), [])

    def test_advance_regenerates_one_stage_per_call_from_the_top(self):
        draft = self.draft()
        self.towns.edit_stage(draft['id'], 'skeleton', draft['stages'][0]['data'],
                              draft['revision'])
        for expected in ('socioeconomy', 'built', 'story'):
            current = self.towns.get_draft(draft['id'])
            fresh = self.towns.advance(draft['id'], current['revision'])
            done = [s['name'] for s in fresh['stages'] if not s['stale']]
            self.assertEqual(done[-1], expected)
            self.assertEqual(len(done), ('socioeconomy', 'built', 'story').index(expected) + 2)
        with self.assertRaisesRegex(TownError, '没有可推进'):
            self.towns.advance(draft['id'], self.towns.get_draft(draft['id'])['revision'])

    def test_published_draft_cannot_be_edited_or_advanced(self):
        draft = self.draft()
        published = self.towns.publish(draft['id'], draft['revision'])
        self.assertFalse(published['reused'])
        current = self.towns.get_draft(draft['id'])
        # Publishing advances the draft revision, so the next edit uses that revision.
        self.assertEqual(current['revision'], published['draft']['revision'])
        self.assertEqual(current['status'], 'draft')
        # The frontier is closed: no stage can be advanced, and a further publish with
        # the same content reuses the immutable row instead of minting another one.
        with self.assertRaisesRegex(TownError, '没有可推进'):
            self.towns.advance(draft['id'], current['revision'])
        again = self.towns.publish(draft['id'], current['revision'])
        self.assertTrue(again['reused'])
        self.assertEqual(again['version']['id'], published['version']['id'])


# ----------------------------------------------------------- concurrency / CAS
class ConcurrencyTests(TownCase):
    def test_two_writers_on_the_same_revision_conflict_without_data_loss(self):
        draft = self.draft()
        first = copy.deepcopy(draft['stages'][0]['data'])
        second = copy.deepcopy(first)
        second['display_name'] = '另一稿'
        self.towns.edit_stage(draft['id'], 'skeleton', first, draft['revision'])
        with self.assertRaisesRegex(TownError, '已被其他操作更新'):
            # The same expected revision is now stale: nothing is written.
            self.towns.edit_stage(draft['id'], 'skeleton', second, draft['revision'])
        current = self.towns.get_draft(draft['id'])
        self.assertEqual(current['stages'][0]['data']['display_name'],
                         first['display_name'])

    def test_two_store_handles_interleaved_publish_and_edit(self):
        draft = self.draft()
        other = Service(Store(self.path), ROOT)
        # The second handle edits first, bumping the draft revision in the database.
        other.towns.edit_stage(draft['id'], 'skeleton', draft['stages'][0]['data'],
                               draft['revision'])
        with self.assertRaisesRegex(TownError, '已被其他操作更新'):
            self.towns.publish(draft['id'], draft['revision'])
        self.assertEqual(self.towns.list_versions(), [])
        # Reading the fresh revision from the other handle succeeds and is consistent.
        fresh = other.towns.get_draft(draft['id'])
        for _ in range(3):
            fresh = other.towns.advance(draft['id'], fresh['revision'])
        published = other.towns.publish(draft['id'], fresh['revision'])
        self.assertFalse(published['reused'])
        self.assertEqual(len(other.towns.list_versions()), 1)

    def test_publish_rechecks_the_row_inside_the_transaction(self):
        """A writer that saves between our read and our commit must win, not be lost."""
        draft = self.draft()
        original = self.towns.get_draft(draft['id'])
        stale_snapshot = self.towns.snapshot(original)
        # Simulate the interleaving: another writer commits a new stage first.
        moved = self.towns.edit_stage(draft['id'], 'skeleton',
                                      original['stages'][0]['data'], original['revision'])
        with self.assertRaisesRegex(TownError, '已被其他操作更新'):
            self.towns.publish(draft['id'], original['revision'])
        self.assertEqual(self.towns.list_versions(), [])
        after = self.towns.get_draft(draft['id'])
        self.assertEqual(after['revision'], moved['revision'])
        # The stale in-memory snapshot was never mistaken for the committed draft: the
        # committed draft is the one that must now be regenerated from its top.
        self.assertTrue(any(s.get('stale') for s in after['stages']))
        with self.assertRaisesRegex(TownError, '尚未完成或已失效'):
            self.towns.snapshot(after)
        self.assertEqual(after['revision'], moved['revision'])
        self.assertNotEqual(original['revision'], after['revision'])


# ---------------------------------------------------------------- publication
class PublicationTests(TownCase):
    def test_publish_is_idempotent_by_content_and_immutable(self):
        draft = self.draft()
        first = self.towns.publish(draft['id'], draft['revision'])
        self.assertFalse(first['reused'])
        version_id = first['version']['id']
        # Publishing again (same content, newer draft revision) reuses the same row.
        second = self.towns.publish(draft['id'], first['draft']['revision'])
        self.assertTrue(second['reused'])
        self.assertEqual(second['version']['id'], version_id)
        stored = self.towns.get_version(version_id)
        self.assertEqual(stored['content_hash'], first['version']['content_hash'])
        self.assertEqual(len(self.towns.list_versions()), 1)

    def test_new_edit_produces_a_new_version_not_an_overwrite(self):
        draft = self.draft()
        first = self.towns.publish(draft['id'], draft['revision'])
        current = self.towns.get_draft(draft['id'])
        edited = copy.deepcopy(current['stages'][0]['data'])
        edited['display_name'] = '改名后的泽口'
        moved = self.towns.edit_stage(draft['id'], 'skeleton', edited, current['revision'])
        for _ in range(3):
            moved = self.towns.advance(draft['id'], moved['revision'])
        second = self.towns.publish(draft['id'], moved['revision'])
        self.assertNotEqual(second['version']['id'], first['version']['id'])
        self.assertEqual(len(self.towns.list_versions()), 2)
        # The earlier version keeps its own bytes.
        self.assertEqual(self.towns.get_version(first['version']['id'])['snapshot']
                         ['skeleton']['display_name'],
                         first['version']['snapshot']['skeleton']['display_name'])

    def test_version_survives_restart(self):
        draft = self.draft()
        published = self.towns.publish(draft['id'], draft['revision'])
        restart = Service(Store(self.path), ROOT)
        again = restart.towns.get_version(published['version']['id'])
        self.assertEqual(again['content_hash'], published['version']['content_hash'])
        self.assertEqual(again['snapshot']['skeleton']['display_name'],
                         published['version']['snapshot']['skeleton']['display_name'])


# --------------------------------------------------------------------- adoption
class AdoptionTests(TownCase):
    def test_adopt_creates_one_revision_and_is_idempotent(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        base = self.rt.package()['id']
        first = self.adopt(version)
        self.assertNotEqual(first['revision'], base)
        self.assertFalse(first['reused'])
        again = self.adopt(version)
        self.assertTrue(again['reused'])
        self.assertEqual(again['revision'], first['revision'])
        # The package itself carries the complete snapshot, not a dangling id.
        entries = package_entries(self.story())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['version_id'], version['id'])
        self.assertEqual(entries[0]['content_hash'],
                         content_hash(entries[0]['snapshot']))
        self.assertTrue(entries[0]['snapshot']['story']['events'])

    def test_stale_base_revision_is_refused_before_any_write(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        base = self.rt.package()['id']
        pkg = copy.deepcopy(self.rt.package())
        self.rt.commit_package(pkg['story'], pkg['characters'], '作者先改了故事包')
        moved = self.rt.package()['id']
        self.assertNotEqual(moved, base)
        with self.assertRaisesRegex(TownError, '故事包已变化|必须基于'):
            self.towns.adopt(version['id'], base, pkg['story']['locations'][0]['id'])
        self.assertEqual(package_entries(self.story()), [])
        self.assertEqual(self.towns.list_bindings(), [])

    def test_cross_world_adoption_is_refused(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        # A separate database has its own town library, so the version is unknown there.
        other = Service(Store(Path(self.tmp.name) / 'other.sqlite3'), ROOT)
        other_pkg = other.runtime.package()
        with self.assertRaisesRegex(TownError, '城镇版本不存在'):
            other.towns.adopt(version['id'], other_pkg['id'],
                              other_pkg['story']['locations'][0]['id'])
        self.assertEqual(package_entries(other.runtime.package()['story']), [])

    def test_interrupted_adoption_is_repaired_by_the_same_request(self):
        """A crash after commit_package but before the index write must be recoverable."""
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        base = self.rt.package()['id']
        story = copy.deepcopy(self.rt.package()['story'])
        characters = copy.deepcopy(self.rt.package()['characters'])
        story['mechanics']['towns'] = {'entries': [
            {'version_id': version['id'], 'town_id': version['town_id'],
             'content_hash': version['content_hash'], 'generator_version': 'town_v1',
             'seed': version['seed'],
             'location_id': story['locations'][0]['id'],
             'adopted_from_revision': base, 'note': '',
             'snapshot': version['snapshot']}]}
        # The package revision exists; the binding row does not.
        committed = self.rt.commit_package(story, characters, '模拟提交后中断')
        self.assertEqual(self.towns.list_bindings(), [])
        repaired = self.towns.adopt(version['id'], base, story['locations'][0]['id'])
        self.assertTrue(repaired['reused'])
        self.assertEqual(repaired['revision'], committed)
        self.assertEqual(len(self.towns.list_bindings()), 1)
        self.assertEqual(len(package_entries(self.story())), 1)

    def test_same_content_bound_to_two_worlds_is_not_confused(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        first = self.adopt(version)
        # A second, independent world must not report the first world's binding as its
        # own: the binding key carries the story identity and the revision.
        bindings = self.towns.list_bindings(version['id'])
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0]['revision'], first['revision'])
        self.assertEqual(bindings[0]['story_id'], self.story()['id'])
        # A different world's package is a different story id, so its lookup is empty.
        self.assertIsNone(self.towns.binding_for(version['id'], 'some_other_world'))
        self.assertIsNotNone(self.towns.binding_for(version['id'], self.story()['id'],
                                                   first['revision']))

    def test_binding_to_a_place_that_does_not_exist_is_refused(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        with self.assertRaisesRegex(TownError, '地点不存在'):
            self.adopt(version, 'no_such_place')
        self.assertEqual(package_entries(self.story()), [])


# ------------------------------------------------------------------- isolation
class JourneyIsolationTests(TownCase):
    def test_old_journey_never_sees_a_later_adoption(self):
        old = self.rt.new_session('旧旅程', 'protagonist')
        before = self.rt.surface(old)
        self.assertNotIn('towns', before)

        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        adopted = self.adopt(version, old['location'])
        self.assertNotEqual(adopted['revision'], old['revision'])

        # The old journey keeps its own revision and its own projection.
        reloaded = self.svc.store.session(old['id'])
        self.assertEqual(reloaded['revision'], old['revision'])
        self.assertNotIn('towns', self.rt.surface(reloaded))
        self.assertNotIn('town_summary', self.rt.context(reloaded, 'player', '进城',
                                                         self.svc.preferences()))

        new = self.rt.new_session('新旅程', 'protagonist')
        self.assertEqual(new['revision'], adopted['revision'])
        surface = self.rt.surface(new)
        self.assertEqual(len(surface['towns']), 1)
        self.assertEqual(surface['towns'][0]['town']['name'],
                         version['snapshot']['skeleton']['display_name'])
        self.assertEqual(surface['towns'][0]['town']['knowledge'], 'current')

    def test_story_package_export_imports_into_an_empty_database(self):
        draft = self.draft()
        version = self.towns.publish(draft['id'], draft['revision'])['version']
        self.adopt(version)
        exported = copy.deepcopy(self.rt.package())

        empty = Service(Store(Path(self.tmp.name) / 'imported.sqlite3'), ROOT)
        empty.runtime.commit_package(copy.deepcopy(exported['story']),
                                     copy.deepcopy(exported['characters']),
                                     '导入导出包')
        self.rt = empty.runtime
        imported = package_entries(self.rt.package()['story'])
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0]['content_hash'], version['content_hash'])
        # The imported journey reads the town without any town table.
        session = self.rt.new_session('导入后旅程', 'protagonist')
        rows = self.rt.surface(session)['towns']
        self.assertEqual(rows[0]['town']['name'],
                         version['snapshot']['skeleton']['display_name'])
        self.assertIn(imported[0]['snapshot']['skeleton']['display_name'],
                      self.rt.context(session, 'player', '进城',
                                      self.svc.preferences())['town_summary'])


# ------------------------------------------------------------------ information
class ProjectionTests(TownCase):
    def setUp(self):
        super().setUp()
        draft = self.draft('cold_mountain_mine')
        self.version = self.towns.publish(draft['id'], draft['revision'])['version']
        # Adopt FIRST, then start the journey: a journey is pinned at creation time, so
        # a session created before the adoption would (correctly) never see the town.
        self.place = self.rt.package()['story']['locations'][0]['id']
        self.adopt(self.version, self.place)
        self.session = self.rt.new_session('投影测试', 'protagonist')
        self.session = self.svc.store.session(self.session['id'])

    def secrets(self):
        snapshot = self.version['snapshot']
        return ([f['hidden_goal'] for f in snapshot['socioeconomy']['factions']
                 if f['hidden_goal']]
                + [s['secret'] for s in snapshot['built']['special_sites'] if s['secret']]
                + [s['text'] for s in snapshot['story']['secrets']])

    def test_public_projection_has_no_secret_and_no_hidden_goal(self):
        view = towns.public_view(self.version['snapshot'])
        blob = json.dumps(view, ensure_ascii=False)
        for secret in self.secrets():
            self.assertTrue(secret)
            self.assertNotIn(secret, blob)
        # Sealed sites are withheld entirely; the field name never appears.
        self.assertNotIn('hidden_goal', blob)
        self.assertNotIn('secret_note', blob)
        sealed = [s['name'] for s in self.version['snapshot']['built']['special_sites']
                  if s['status'] == 'sealed']
        for name in sealed:
            self.assertNotIn(name, blob)

    def test_player_api_is_scoped_to_the_journey_revision(self):
        app = create_app(self.path)
        client = TestClient(app)
        token = client.get('/api/bootstrap').json()['token']
        headers = {'X-TextileDream-Token': token}
        body = client.get(f'/api/sessions/{self.session["id"]}/towns', headers=headers)
        self.assertEqual(body.status_code, 200)
        blob = json.dumps(body.json(), ensure_ascii=False)
        for secret in self.secrets():
            self.assertNotIn(secret, blob)
        # Asking for a version this journey never bound is a refusal.
        missing = client.get(f'/api/sessions/{self.session["id"]}/towns/tv_ffffffffffffffff',
                             headers=headers)
        self.assertEqual(missing.status_code, 400)

    def test_author_api_requires_the_token_and_returns_everything(self):
        app = create_app(self.path)
        client = TestClient(app)
        token = client.get('/api/bootstrap').json()['token']
        bare = client.get('/api/inner/town-versions')
        self.assertEqual(bare.status_code, 403)
        headers = {'X-TextileDream-Token': token}
        rows = client.get('/api/inner/town-versions', headers=headers).json()
        self.assertEqual(len(rows), 1)
        detail = client.get(f'/api/inner/town-versions/{rows[0]["id"]}',
                            headers=headers).json()
        self.assertTrue(any(f['hidden_goal'] for f in
                            detail['snapshot']['socioeconomy']['factions']))

    def test_model_context_gets_one_bounded_public_summary(self):
        context = self.rt.context(self.session, 'player', '进城', self.svc.preferences())
        summary = context['town_summary']
        self.assertLessEqual(len(summary), 1200)
        for secret in self.secrets():
            self.assertNotIn(secret, summary)
        self.assertNotIn('hidden_goal', summary)
        # An NPC viewpoint in the same place gets the same bounded public summary and
        # still no secrets.
        npc = next(c['id'] for c in self.rt.package(self.session['revision'])
                   ['characters']['characters'] if c['role'] != '主角')
        npc_context = self.rt.context(self.session, npc, '进城', self.svc.preferences())
        if 'town_summary' in npc_context:
            self.assertLessEqual(len(npc_context['town_summary']), 1200)
            for secret in self.secrets():
                self.assertNotIn(secret, npc_context['town_summary'])


# ------------------------------------------------------------------ compatibility
class LegacyCompatibilityTests(unittest.TestCase):
    """An untouched package and an untouched save must behave exactly as before."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'legacy.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    def test_unconfigured_package_adds_no_towns_key(self):
        story = self.rt.package()['story']
        self.assertNotIn('towns', (story.get('mechanics') or {}))
        session = self.rt.new_session('兼容', 'protagonist')
        self.assertNotIn('towns', self.rt.surface(session))
        context = self.rt.context(session, 'player', '四处看看', self.svc.preferences())
        self.assertNotIn('town_summary', context)
        self.assertEqual(self.svc.towns.list_bindings(), [])

    def test_untouched_save_is_not_rewritten_by_reads(self):
        session = self.rt.new_session('兼容', 'protagonist')
        before = self.svc.store.session(session['id'])
        for _ in range(3):
            self.rt.surface(session)
            self.rt.context(session, 'player', '看看', self.svc.preferences())
        after = self.svc.store.session(session['id'])
        self.assertEqual(before['state_version'], after['state_version'])

    def test_a_package_with_a_corrupt_town_entry_is_rejected(self):
        package = copy.deepcopy(self.rt.package())
        package['story'].setdefault('mechanics', {})['towns'] = {'entries': [
            {'version_id': 'tv_deadbeefdeadbeef', 'town_id': 'town_x',
             'content_hash': 'x', 'generator_version': 'town_v1', 'seed': 'abcd',
             'location_id': None, 'adopted_from_revision': 'r', 'note': '',
             'snapshot': None}]}
        with self.assertRaises(ValueError):
            self.rt.commit_package(package['story'], package['characters'], '坏的城镇条目')


if __name__ == '__main__':
    unittest.main()
