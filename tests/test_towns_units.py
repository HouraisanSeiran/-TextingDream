"""Numeric baselines written as independent literals.

These assert the physical meaning of the food constants using numbers typed by hand, so
a wrong constant cannot make its own test pass. They exist because the gram constant was
once written as `180` instead of `180000` — a thousandfold error that made every imported
tonne feed a thousand people, and that a test computed *from* the constant could not
catch.
"""
import tempfile
import unittest
from pathlib import Path

from app import towns
from app.service import Service
from app.storage import Store
from app.town_schema import DraftRequest, TownInput

ROOT = Path(__file__).resolve().parents[1]


class GrainConstantTests(unittest.TestCase):
    """1 person = 0.18 t = 180 kg = 180 000 g of grain per year."""

    def test_one_person_year_is_one_hundred_eighty_thousand_grams(self):
        # Literal, not derived from the constant under test.
        self.assertEqual(towns.need_grams(1), 180000)

    def test_one_person_year_in_every_declared_unit(self):
        grams = towns.need_grams(1)
        self.assertEqual(grams // 1000, 180)            # 180 kg
        self.assertEqual(grams // 1000000, 0)           # less than a tonne
        # 0.18 t expressed in grams, typed as a literal.
        self.assertEqual(grams, 180 * 1000)

    def test_a_thousand_people_need_one_hundred_eighty_tonnes(self):
        # 1000 × 180 kg = 180 t. Written out, not computed from the constant.
        self.assertEqual(towns.need_grams(1000), 180000000)
        self.assertEqual(towns.need_grams(1000) // 1000000, 180)

    def test_one_hundred_eighty_tonnes_of_import_feeds_one_thousand_people(self):
        flow = {'amount': 180, 'unit': 't', 'period': 'year'}
        grams = towns.flow_grams(flow)
        self.assertEqual(grams, 180000000)
        people = grams // towns.need_grams(1)
        self.assertEqual(people, 1000)

    def test_one_hundred_eighty_kilograms_feeds_one_person_not_a_thousand(self):
        flow = {'amount': 180, 'unit': 'kg', 'period': 'year'}
        grams = towns.flow_grams(flow)
        self.assertEqual(grams, 180000)
        self.assertEqual(grams // towns.need_grams(1), 1)

    def test_one_tonne_feeds_about_five_people(self):
        # 1 t = 1 000 000 g ÷ 180 000 g = 5.55 → five whole persons.
        grams = towns.flow_grams({'amount': 1, 'unit': 't', 'period': 'year'})
        self.assertEqual(grams // towns.need_grams(1), 5)

    def test_farm_capacity_coefficient_is_unchanged(self):
        # 6 t per arable km² ÷ 0.18 t per person = 33 persons per km².
        self.assertEqual(towns.FARM_PERSONS_PER_KM2, 33)
        self.assertEqual(towns.GRAIN_YIELD_T_PER_KM2_YEAR, 6)
        self.assertEqual(towns.GRAIN_KG_PER_PERSON_YEAR, 180)

    def test_import_capacity_uses_the_correct_scale(self):
        """180 t/year of imported grain may support ~1000 people, never a million."""
        entry = towns.preset_entry('cold_mountain_mine', 'scale_seed_1').model_dump(mode='json')
        entry['imports'] = [{'id': 'imp_grain', 'name': '粮食', 'kind': 'grain',
                             'amount_per_period': 180, 'unit': 't', 'period': 'year',
                             'via': 'road', 'note': '测试用'}]
        caps = towns.capacities(entry)
        self.assertEqual(caps['imported_grams'], 180000000)
        self.assertEqual(caps['imported_persons'], 1000)
        self.assertLess(caps['imported_persons'], 2000)


class UnitScalingRegressionTests(unittest.TestCase):
    """A `kg` restatement must not shrink a real quantity by a thousandfold."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'scale.sqlite3'
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

    def test_need_unit_switch_to_kg_is_refused(self):
        snapshot = self.snapshot('cold_mountain_mine', 'scale_seed_2')
        flow = snapshot['socioeconomy']['staple_need']
        # Same number, kilogram unit: a thousandfold smaller requirement. Must be refused.
        flow['unit'] = 'kg'
        with self.assertRaisesRegex(ValueError, '口粮需求'):
            towns.validate_snapshot(snapshot)

    def test_local_staple_unit_switch_to_kg_is_refused(self):
        snapshot = self.snapshot('wet_valley', 'scale_seed_3')
        staple = snapshot['socioeconomy']['staple']
        self.assertGreater(staple['amount'], 0)
        # A tonne-denominated staple relabelled as kilograms would look 1000× plentiful.
        staple['unit'] = 'kg'
        with self.assertRaisesRegex(ValueError, '口粮|供给|需求'):
            towns.validate_snapshot(snapshot)

    def test_a_town_fed_by_a_hundred_and_eighty_tonnes_has_about_a_thousand_people(self):
        entry = towns.preset_entry('cold_mountain_mine', 'scale_seed_4').model_dump(mode='json')
        # A mountain town has no arable land, so the population is import-limited.
        entry['imports'] = [{'id': 'imp_grain', 'name': '粮食', 'kind': 'grain',
                             'amount_per_period': 180, 'unit': 't', 'period': 'year',
                             'via': 'road', 'note': '测试用'}]
        snapshot = towns.generate_all(entry)
        population = snapshot['socioeconomy']['population']['total']
        self.assertLessEqual(population, 1000)
        self.assertGreater(population, 500)


if __name__ == '__main__':
    unittest.main()
