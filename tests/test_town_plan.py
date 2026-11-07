"""Real snapshot → existing art → author API, with isolated persistence only."""
import copy
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import towns
from app.town_layout import layout, load_catalog
from app.town_plan import PlanOptions, generate_plan
from app.town_schema import DraftRequest
from tests.fixtures_world import world_app


class TownPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.snapshots = {p: towns.generate_all(towns.preset_entry(p, 'town_plan_test').model_dump(mode='json'))
                         for p in towns.PRESETS}

    def test_real_presets_and_facility_accounting(self):
        ids = {m['id'] for m in self.catalog['meta']}
        for preset, snapshot in self.snapshots.items():
            with self.subTest(preset=preset):
                original = copy.deepcopy(snapshot)
                result = generate_plan(snapshot, catalog=self.catalog)
                self.assertEqual(snapshot, original)
                self.assertEqual(result, generate_plan(snapshot, catalog=self.catalog))
                self.assertEqual(result['summary']['facilities'], len(snapshot['built']['facilities']))
                self.assertEqual({r['source'] for r in result['facilities']},
                                 {f['id'] for f in snapshot['built']['facilities']})
                self.assertGreater(result['summary']['placed'], 0)
                for row in result['facilities']:
                    if row['status'] == 'placed':
                        self.assertIn(row['art_id'], ids)
                    else:
                        self.assertTrue(any(d.get('source') == row['source'] for d in result['diagnostics']))
                for scene in [result['layout']] + [s['layout'] for s in result['resource_sites']]:
                    for layer in ('underlay', 'ground', 'items'):
                        self.assertTrue(all(item['id'] in ids for item in scene[layer]))

    def test_resource_gates_and_arab_fallback_are_visible(self):
        snapshot = self.snapshots['arid_oasis_route']
        result = generate_plan(snapshot, catalog=self.catalog)
        self.assertEqual(result['resolved']['style'], 'arab')
        available, _ = towns.resource_closure(snapshot['input'])
        self.assertEqual({r['source'] for r in result['resource_sites']}, set(available))
        self.assertNotIn('iron', {r['resource'] for r in result['resource_sites']})
        self.assertTrue(result['resource_sites'])
        for site in result['resource_sites']:
            self.assertIn('style_fallback', {d['reason'] for d in site['diagnostics']})
        entry = copy.deepcopy(snapshot['input'])
        for candidate in entry['resources']:
            candidate['extractable'] = False
        blocked = generate_plan(towns.generate_all(entry), catalog=self.catalog)
        self.assertEqual(blocked['resource_sites'], [])

    def test_choices_and_culture_fallback_are_explicit(self):
        snapshot = self.snapshots['wet_valley']
        a = generate_plan(snapshot, {'style': 'east', 'race': 'elf', 'seed': 'layout_a'}, catalog=self.catalog)
        b = generate_plan(snapshot, {'style': 'east', 'race': 'elf', 'seed': 'layout_b'}, catalog=self.catalog)
        self.assertEqual(a['resolved']['race'], 'common')
        self.assertIn('culture_fallback', {d['reason'] for d in a['diagnostics']})
        self.assertEqual(a['options']['race'], 'elf')
        self.assertNotEqual(a['layout'], b['layout'])
        self.assertEqual(a['snapshot_hash'], b['snapshot_hash'])

    def test_options_are_bounded_and_cannot_expose_unbounded_terrain(self):
        for options in ({'terrain': {'w': 100000}}, {'style': 'invalid'}, {'landmarks': True},
                        {'landmarks': 3}, {'seed': 'x'*65}, {'seed': ''}, {'race': 'unknown'}):
            with self.subTest(options=options), self.assertRaises(ValidationError):
                PlanOptions.model_validate(options)

    def test_failed_wall_is_reported(self):
        plan = layout({'scale': 'city', 'facilities': [{'id':'wall', 'kind':'city_wall'}]},
                      terrain={'w': 6, 'h': 6, 'water': [[x,y] for x in range(6) for y in range(6)]},
                      catalog=self.catalog)
        self.assertFalse(plan['grid']['walled'])
        self.assertIn('wall_terrain', {m['reason'] for m in plan['missing']})


class TownPlanApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = world_app(Path(self.tmp.name) / 'town-plan.sqlite3')
        self.svc = self.app.state.service
        self.client = TestClient(self.app)
        self.headers = {'X-TextileDream-Token': self.client.get('/api/bootstrap').json()['token']}
        entry = towns.preset_entry('cold_mountain_mine', 'api_plan_test',
                                  story_revision=self.svc.runtime.package()['id'])
        self.draft = self.svc.towns.create(DraftRequest(input=entry))
        self.url = '/api/inner/towns/' + self.draft['id'] + '/layout'

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def test_author_only_read_with_no_document_mutation_and_version_replay(self):
        self.assertEqual(self.client.post(self.url, json={}).status_code, 403)
        self.assertEqual(self.client.post(self.url, headers=self.headers,
                                         json={'terrain': {'w':99999}}).status_code, 422)
        before = self.svc.store.all('town_draft')
        result = self.client.post(self.url, headers=self.headers, json={'style':'east'})
        self.assertEqual(result.status_code, 200, result.text)
        data = result.json()
        self.assertEqual(before, self.svc.store.all('town_draft'))
        self.assertEqual(data['source']['revision'], self.draft['revision'])
        published = self.svc.towns.publish(self.draft['id'], self.draft['revision'])['version']
        url = '/api/inner/town-versions/' + published['id'] + '/layout'
        self.assertEqual(self.client.post(url, json={}).status_code, 403)
        again = self.client.post(url, headers=self.headers, json={'style':'east'})
        self.assertEqual(again.status_code, 200, again.text)
        self.assertEqual(data['layout'], again.json()['layout'])
        self.assertEqual(data['snapshot_hash'], again.json()['snapshot_hash'])
        self.assertEqual(published, self.svc.towns.get_version(published['id']))

    def test_stale_draft_and_unknown_source_are_refused(self):
        stage = self.draft['stages'][0]
        self.svc.towns.edit_stage(self.draft['id'], stage['name'], stage['data'], self.draft['revision'])
        result = self.client.post(self.url, headers=self.headers, json={})
        self.assertEqual(result.status_code, 400, result.text)
        self.assertIn('失效', result.json()['detail'])
        self.assertEqual(self.client.post('/api/inner/towns/missing/layout',
                                         headers=self.headers, json={}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
