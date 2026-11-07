# -*- coding: utf-8 -*-
"""建筑经营接口（预设）的契约测试：只查数据完整，不模拟。"""
import json
import unittest
from pathlib import Path

from app import building_economy as be

TOWN = Path(__file__).resolve().parents[1] / 'app' / 'static' / 'map-art' / 'town'


class BuildingEconomyCase(unittest.TestCase):
    def test_validate_passes(self):
        self.assertEqual(be.validate(), [])

    def test_every_resource_has_extraction_profile(self):
        for r in be.RESOURCES:
            self.assertTrue(any(k[0] == r for k in be.SITE_PROFILES), r)

    def test_all_facility_kinds_profiled(self):
        self.assertEqual(set(be.FACILITY_PROFILES), set(be.FACILITIES))

    def test_farm_subtypes_present(self):
        for sub in ('wheat_farm', 'rice_paddy', 'orchard', 'cattle_ranch', 'dairy_farm',
                    'pig_farm', 'poultry_farm', 'apiary', 'sheep_station', 'horse_stud'):
            self.assertTrue(any(k[1] == sub for k in be.SITE_PROFILES), sub)

    def test_profile_lookup(self):
        self.assertEqual(be.profile_for({'category': 'site', 'resource': 'coal'}).id, 'coal_mine')
        self.assertEqual(be.profile_for({'category': 'site', 'resource': 'livestock',
                                         'subtype': 'pig_farm'}).id, 'pig_farm')
        self.assertEqual(be.profile_for({'category': 'site', 'resource': 'horses'}).id, 'horse_stud')
        self.assertEqual(be.profile_for({'category': 'special', 'facility': 'forge'}).id, 'forge')
        self.assertEqual(be.profile_for({'category': 'house'}).id, 'residence')
        self.assertIsNone(be.profile_for({'category': 'road', 'facility': None}))
        self.assertIsNone(be.profile_for({'category': 'prop', 'facility': 'market_hall'}))

    def test_all_art_sites_and_facilities_resolve(self):
        missing = []
        for meta_path in TOWN.glob('*/meta.json'):
            for m in json.loads(meta_path.read_text('utf-8')):
                if m.get('category') == 'site' or (m.get('facility') and m.get('category') not in
                                                    ('prop', 'road', 'ground', 'water')):
                    if be.profile_for(m) is None:
                        missing.append(m['id'])
        self.assertEqual(missing, [])

    def test_placeholder_numbers_flagged(self):
        for p in list(be.SITE_PROFILES.values()) + list(be.FACILITY_PROFILES.values()):
            self.assertFalse(p.calibrated, p.id)


if __name__ == '__main__':
    unittest.main()
