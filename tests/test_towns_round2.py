"""Second-round review: unit bypass, cumulative over-export, and fuel provenance.

Each test here is written to reproduce a concrete bypass that the first hardening pass
still allowed, before the implementation is changed:

* A — `staple_need` was compared only by `amount`, so switching the unit from t to kg
  kept the number but shrank the real need a thousandfold.
* B — an export was checked per row, so two rows at 60% each shipped 120% of output; and
  an import was checked only by resource id, so one declared allowance could be consumed
  several times over.
* C — "has fuel" mixed a *permission* (the material list) with an *actual surveyed
  supply*, so an unsurveyed coal seam was treated as available.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from app import towns
from app.service import Service
from app.storage import Store
from app.town_schema import DraftRequest, TownInput

ROOT = Path(__file__).resolve().parents[1]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'towns.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.towns = self.svc.towns
        self.rt = self.svc.runtime

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self, preset='cold_mountain_mine', seed='round2_seed_1', **overrides):
        data = towns.preset_entry(preset, seed,
                                  story_revision=self.rt.package()['id']).model_dump(mode='json')
        data.update(overrides)
        return self.towns.create(DraftRequest(input=TownInput(**data)))

    def snapshot(self, preset='cold_mountain_mine', seed='round2_seed_1'):
        return self.towns.snapshot(self.towns.get_draft(self.draft(preset, seed)['id']))

    def refuse(self, snapshot, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            towns.validate_snapshot(snapshot)


class UnitBypassTests(Base):
    """A: the food need must be compared in one normalised unit, not by raw numbers."""

    def test_food_need_unit_switch_is_refused(self):
        snapshot = self.snapshot()
        # Same number, kilogram unit: the real need would be 1000× smaller.
        snapshot['socioeconomy']['staple_need']['unit'] = 'kg'
        self.refuse(snapshot, '口粮需求')

    def test_food_need_period_switch_is_refused(self):
        snapshot = self.snapshot()
        # Same number, daily period: the real need would be 365× larger.
        snapshot['socioeconomy']['staple_need']['period'] = 'day'
        self.refuse(snapshot, '口粮需求')

    def test_food_need_amount_change_is_refused(self):
        snapshot = self.snapshot()
        snapshot['socioeconomy']['staple_need']['amount'] = max(
            1, snapshot['socioeconomy']['staple_need']['amount'] // 100)
        self.refuse(snapshot, '口粮需求')

    def test_local_supply_cannot_shrink_its_unit_to_look_sufficient(self):
        """The other direction: a staple in kg must not satisfy a t-denominated need."""
        snapshot = self.snapshot('wet_valley', 'round2_wet')
        staple = snapshot['socioeconomy']['staple']
        if staple['amount'] == 0:
            self.skipTest('该样本没有本地口粮')
        staple['unit'] = 'kg'
        self.refuse(snapshot, '口粮|供给|需求')


class CumulativeTradeTests(Base):
    """B: totals are what matters, not each row on its own."""

    def _export_rows(self, snapshot, share, count):
        chain = next(c for c in snapshot['socioeconomy']['chains']
                     if c['output']['resource'] != 'grain')
        rows = []
        for index in range(count):
            rows.append({'id': f'tr_split_{index}', 'direction': 'export',
                         'resource': chain['output']['resource'], 'kind': 'other',
                         'name': chain['output']['resource'],
                         'amount': int(chain['output']['amount'] * share),
                         'unit': chain['output']['unit'], 'period': chain['output']['period'],
                         'via': 'roads', 'requirement': '拆分出口'})
        return chain, rows

    def test_split_exports_cannot_exceed_output_in_total(self):
        snapshot = self.snapshot()
        chain, rows = self._export_rows(snapshot, 0.6, 2)
        snapshot['socioeconomy']['trade'].extend(rows)
        self.refuse(snapshot, '出口')

    def test_each_within_limit_but_total_over_is_still_refused(self):
        snapshot = self.snapshot()
        _, rows = self._export_rows(snapshot, 0.55, 2)
        snapshot['socioeconomy']['trade'].extend(rows)
        self.refuse(snapshot, '出口')

    def test_import_allowance_cannot_be_consumed_twice(self):
        snapshot = self.snapshot()
        declared = snapshot['input']['imports'][0]
        trade = next(t for t in snapshot['socioeconomy']['trade']
                     if t['direction'] == 'import')
        duplicate = copy.deepcopy(trade)
        duplicate['id'] = 'tr_import_duplicate'
        snapshot['socioeconomy']['trade'].append(duplicate)
        # Two rows each matching the full declared allowance add up to double of it.
        self.refuse(snapshot, '进口')

    def test_import_must_match_the_declared_unit_and_period(self):
        snapshot = self.snapshot()
        trade = next(t for t in snapshot['socioeconomy']['trade']
                     if t['direction'] == 'import')
        trade['unit'] = 'count'
        self.refuse(snapshot, '进口')

    def test_import_kind_must_match_the_declared_dependency(self):
        snapshot = self.snapshot()
        trade = next(t for t in snapshot['socioeconomy']['trade']
                     if t['direction'] == 'import')
        trade['kind'] = 'salt' if trade['kind'] != 'salt' else 'timber'
        self.refuse(snapshot, '进口')


class FuelProvenanceTests(Base):
    """C: permission to use coal is not the same as coal actually being available."""

    def test_unsurveyed_coal_cannot_be_a_fuel_source(self):
        snapshot = self.snapshot()
        for candidate in snapshot['input']['resources']:
            if candidate['kind'] == 'coal':
                candidate['surveyed'] = False
        self.refuse(snapshot, '燃料')

    def test_coal_blocked_by_technology_cannot_be_a_fuel_source(self):
        snapshot = self.snapshot()
        snapshot['input']['technology'] = [t for t in snapshot['input']['technology']
                                           if t != 'mine_shaft']
        self.refuse(snapshot, '燃料|技术')

    def test_declared_material_is_not_a_fuel_stock(self):
        """`materials` says what may be used, never that it exists in quantity."""
        snapshot = self.snapshot()
        for candidate in snapshot['input']['resources']:
            if candidate['kind'] == 'coal':
                candidate['surveyed'] = False
                candidate['extractable'] = False
        # Coal stays in the allowed-materials list, which must not rescue the fuel check.
        self.assertIn('coal', snapshot['input']['materials']) if 'coal' in \
            snapshot['input']['materials'] else None
        self.refuse(snapshot, '燃料')

    def test_fuel_import_must_carry_a_positive_amount(self):
        snapshot = self.snapshot()
        for candidate in snapshot['input']['resources']:
            if candidate['kind'] == 'coal':
                candidate['surveyed'] = False
        # A zero-amount fuel import is not a supply.
        snapshot['input']['imports'].append({
            'id': 'imp_fuel_zero', 'kind': 'fuel', 'name': '燃料', 'amount_per_period': 0,
            'unit': 't', 'period': 'year', 'via': 'road', 'note': '空头燃料'})
        self.refuse(snapshot, '燃料|进口')

    def test_circular_fuel_dependency_is_refused(self):
        """Coal that needs coal (or a two-step cycle) must not bootstrap itself."""
        snapshot = self.snapshot()
        snapshot['input']['resources'].append({
            'id': 'res_coal_cycle', 'kind': 'coal', 'abundance': 0.9, 'accessibility': 0.9,
            'surveyed': True, 'extractable': True, 'requires_technology': [],
            'fuel': 'coal'})
        self.refuse(snapshot, '燃料|循环')


if __name__ == '__main__':
    unittest.main()
