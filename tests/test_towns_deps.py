"""Third-round review: resource dependency must resolve as a bounded fixed point.

The earlier pass replaced a one-line fuel test with a one-hop closure: `_fuel_sources`
filtered by survey/technology, but `gated_resource` still treated `materials ∪ any
resource kind` (surveyed or not) and *any* fuel import (including a zero-volume one) as
proof of supply. So "coal needs wood, wood was never surveyed" could still be counted as
available coal, and then fuel an iron works.

These tests pin the corrected semantics: one shared bounded closure drives both the
generator and the validator, a chain of dependencies resolves, and a cycle with no
external start never bootstraps. They also pin the food balance to exact integers, so
"a shortfall is refused" is literally true rather than true to within a tonne.
"""
import tempfile
import unittest
from pathlib import Path

from app import towns
from app.service import Service
from app.storage import Store
from app.town_schema import DraftRequest, TownInput

ROOT = Path(__file__).resolve().parents[1]


def mine_entry(**overrides):
    """A cold-mountain mining town, with resources replaced per test."""
    data = towns.preset_entry('cold_mountain_mine', 'r3_seed_1',
                              story_revision='r3_story_revision_0001').model_dump(mode='json')
    data.update(overrides)
    return data


def resource(identity, kind, fuel='none', surveyed=True, extractable=True, tech=()):
    return {'id': identity, 'kind': kind, 'abundance': 0.8, 'accessibility': 0.8,
            'surveyed': surveyed, 'extractable': extractable,
            'requires_technology': list(tech), 'fuel': fuel}


class Resources:
    """A resource set with coal→iron and optional wood, for dependency tests."""

    @staticmethod
    def coal_needs_wood(wood_surveyed=True):
        return [resource('res_wood', 'timber', surveyed=wood_surveyed),
                resource('res_coal', 'coal', fuel='timber', tech=['mine_shaft']),
                resource('res_iron', 'iron', fuel='coal',
                         tech=['mine_shaft', 'forge'])]


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'r3.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.towns = self.svc.towns
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self, entry):
        return towns.generate_all(entry)

    def ids(self, available):
        return set(available)

    # ---------------------------------------------------------------- fixed point
    def test_chain_of_dependencies_resolves_when_the_chain_has_a_start(self):
        entry = mine_entry(resources=Resources.coal_needs_wood(wood_surveyed=True))
        available, kinds = towns.resource_closure(entry)
        # wood (needs nothing) → coal (needs wood) → iron (needs coal)
        self.assertIn('res_wood', available)
        self.assertIn('res_coal', available)
        self.assertIn('res_iron', available)
        self.assertIn('iron', kinds)

    def test_unsurveyed_wood_blocks_coal_and_therefore_iron(self):
        entry = mine_entry(resources=Resources.coal_needs_wood(wood_surveyed=False))
        available, _kinds = towns.resource_closure(entry)
        self.assertNotIn('res_wood', available)
        self.assertNotIn('res_coal', available)
        self.assertNotIn('res_iron', available)

    def test_allowed_material_is_not_a_resource_stock(self):
        # Coal stays an allowed material; with no surveyed coal it is still unavailable.
        entry = mine_entry(resources=[resource('res_iron', 'iron', fuel='coal',
                                               tech=['mine_shaft', 'forge'])],
                           materials=['stone', 'coal', 'timber'])
        available, _kinds = towns.resource_closure(entry)
        self.assertNotIn('res_iron', available)

    def test_zero_volume_fuel_import_does_not_count(self):
        entry = mine_entry(
            resources=[resource('res_iron', 'iron', fuel='coal',
                                tech=['mine_shaft', 'forge'])],
            imports=[{'id': 'imp_zero_fuel', 'name': '燃料', 'kind': 'fuel',
                      'amount_per_period': 0, 'unit': 't', 'period': 'year',
                      'via': 'road', 'note': '空头'}])
        self.assertFalse(towns.positive_fuel_imports(entry))
        available, _kinds = towns.resource_closure(entry)
        self.assertNotIn('res_iron', available)

    def test_positive_fuel_import_provides_the_start(self):
        entry = mine_entry(
            resources=[resource('res_iron', 'iron', fuel='coal',
                                tech=['mine_shaft', 'forge'])],
            imports=[{'id': 'imp_fuel', 'name': '燃料', 'kind': 'fuel',
                      'amount_per_period': 50, 'unit': 't', 'period': 'year',
                      'via': 'road', 'note': '运来的燃料'}])
        self.assertTrue(towns.positive_fuel_imports(entry))
        available, _kinds = towns.resource_closure(entry)
        self.assertIn('res_iron', available)

    def test_two_node_cycle_without_external_start_never_bootstraps(self):
        entry = mine_entry(resources=[
            resource('res_wood', 'timber', fuel='coal'),
            resource('res_coal', 'coal', fuel='timber', tech=['mine_shaft'])])
        available, kinds = towns.resource_closure(entry)
        self.assertEqual(available, [])
        self.assertEqual(kinds, [])
        reasons = {r['id']: r['reason'] for r in towns.blocked_dependencies(entry)}
        self.assertIn('res_wood', reasons)
        self.assertIn('res_coal', reasons)

    def test_cycle_with_an_external_start_still_resolves(self):
        entry = mine_entry(
            resources=[resource('res_wood', 'timber', fuel='coal'),
                       resource('res_coal', 'coal', fuel='timber', tech=['mine_shaft'])],
            imports=[{'id': 'imp_fuel', 'name': '燃料', 'kind': 'fuel',
                      'amount_per_period': 30, 'unit': 't', 'period': 'year',
                      'via': 'road', 'note': '外部启动燃料'}])
        available, _kinds = towns.resource_closure(entry)
        self.assertIn('res_wood', available)
        self.assertIn('res_coal', available)

    def test_closure_terminates_on_a_long_chain(self):
        # Each candidate depends on the previous one; the round cap must still terminate.
        chain = [resource('res_0', 'timber')]
        kinds = ['coal', 'iron', 'copper', 'tin', 'stone', 'clay']
        for index, kind in enumerate(kinds, start=1):
            chain.append(resource(f'res_{index}', kind, fuel='timber' if index == 1 else kinds[index - 2],
                                  tech=tuple(['mine_shaft'] if kind in
                                             ('coal', 'iron', 'copper', 'tin') else [])))
        entry = mine_entry(resources=chain)
        available, _kinds = towns.resource_closure(entry)
        self.assertEqual(len(available), len(chain))

    # ------------------------------------------------- generator/validator agreement
    def test_generator_and_validator_share_the_same_closure(self):
        entry = mine_entry(resources=Resources.coal_needs_wood(wood_surveyed=False))
        snapshot = self.snapshot(entry)
        # No iron chain may exist, because the closure excluded its ore.
        outputs = {c['output']['resource'] for c in snapshot['socioeconomy']['chains']}
        self.assertNotIn('iron_bar', outputs)
        # And the validator agrees with the generator on this very snapshot.
        towns.validate_snapshot(snapshot)

    def test_a_chain_smuggling_a_blocked_ore_is_refused(self):
        entry = mine_entry(resources=Resources.coal_needs_wood(wood_surveyed=True))
        snapshot = self.snapshot(entry)
        # Re-validate with the wood un-surveyed: the previously legal iron chain is now
        # unsupported and must be rejected.
        for candidate in snapshot['input']['resources']:
            if candidate['id'] == 'res_wood':
                candidate['surveyed'] = False
        with self.assertRaisesRegex(ValueError, '来源|燃料'):
            towns.validate_snapshot(snapshot)


class ExactFoodTests(unittest.TestCase):
    """The food balance is exact integers: no tonne of slack, no float."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'r3f.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.towns = self.svc.towns
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self, preset, seed):
        draft = self.towns.create(DraftRequest(input=TownInput(**towns.preset_entry(
            preset, seed, story_revision=self.rt.package()['id']).model_dump(mode='json'))))
        return self.towns.snapshot(self.towns.get_draft(draft['id']))

    def test_a_kilogram_sized_shortfall_is_still_refused(self):
        """The check is exact: move one kilogram of grain out and it must fail.

        The declared import allowance and the derived `import_food_cap` are left alone
        (changing them is a separate, correctly rejected inconsistency), so the only
        thing under test here is the gram-level balance itself: an export of exactly the
        surplus is accepted, one kilogram more is refused.
        """
        snapshot = self.snapshot('wet_valley', 'exact_seed_1')
        needed = towns.need_grams(snapshot['socioeconomy']['population']['total'])
        staple = towns.flow_grams(snapshot['socioeconomy']['staple']) or 0
        imported = 0
        for trade in snapshot['socioeconomy']['trade']:
            if trade['direction'] == 'import' and trade['kind'] == 'grain':
                imported += towns.flow_grams(trade) or 0
        surplus = staple + imported - needed
        self.assertGreater(surplus, 1000, '样本应有可观的余粮，边界才可测')
        # Express the grain chain and the staple in kilograms too, so every grain figure
        # in this snapshot shares one unit and the only variable is the surplus itself.
        for chain in snapshot['socioeconomy']['chains']:
            if chain['output']['resource'] == 'grain':
                chain['output']['unit'] = 'kg'
                chain['output']['amount'] = chain['output']['amount'] * 1000
        snapshot['socioeconomy']['staple'].update(unit='kg',
                                                 amount=snapshot['socioeconomy']['staple']['amount'] * 1000)
        export = {'id': 'tr_border_test', 'direction': 'export', 'resource': 'grain',
                  'kind': 'grain', 'name': 'grain', 'amount': surplus // 1000,
                  'unit': 'kg', 'period': 'year', 'via': 'roads',
                  'requirement': '边界测试'}
        snapshot['socioeconomy']['trade'].append(export)
        # Exporting exactly the surplus leaves zero slack: still accepted.
        towns.validate_snapshot(snapshot)
        # One kilogram more than the surplus: refused, because there is no tonne of slack.
        export['amount'] = surplus // 1000 + 1
        with self.assertRaisesRegex(ValueError, '口粮可用量'):
            towns.validate_snapshot(snapshot)


    def test_period_and_amount_edits_cannot_shrink_the_need(self):
        for edit in ({'period': 'day'}, {'period': 'month'}, {'amount': 1}):
            snapshot = self.snapshot('wet_valley', 'exact_seed_3')
            snapshot['socioeconomy']['staple_need'].update(edit)
            with self.assertRaisesRegex(ValueError, '口粮需求'):
                towns.validate_snapshot(snapshot)

    def test_a_kg_restatement_with_the_same_mass_is_accepted(self):
        """Changing the unit alone does not change the requirement, so it is legal.

        Only a change that alters the real quantity (period, or the number itself) is a
        bypass; expressing the same grams in kilograms is not.
        """
        snapshot = self.snapshot('wet_valley', 'exact_seed_5')
        flow = snapshot['socioeconomy']['staple_need']
        grams = towns.flow_grams(flow)
        flow['unit'] = 'kg'
        flow['amount'] = grams // 1000
        self.assertEqual(towns.flow_grams(flow), grams)
        towns.validate_snapshot(snapshot)

    def test_need_is_declared_exactly_in_whole_grams(self):
        snapshot = self.snapshot('wet_valley', 'exact_seed_4')
        flow = snapshot['socioeconomy']['staple_need']
        population = snapshot['socioeconomy']['population']['total']
        self.assertEqual(towns.flow_grams(flow), towns.need_grams(population))
        # And the population is on the grid that makes this representable.
        self.assertEqual(population % 50, 0)


if __name__ == '__main__':
    unittest.main()
