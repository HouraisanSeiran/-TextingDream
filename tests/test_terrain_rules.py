# -*- coding: utf-8 -*-
"""产地 DEM 判定规则（app/terrain_rules.py）。"""
import unittest

from app import terrain_rules as tr
from tools import game_fields


class VocabularyCase(unittest.TestCase):
    def test_every_terrain_has_a_rule(self):
        self.assertEqual(set(tr.RULES), set(game_fields.TERRAINS))

    def test_layer_list_matches_rules(self):
        self.assertEqual(set(tr.LAYER_NEEDED),
                         {k for k, v in tr.RULES.items() if v == 'needs_layer'})


class BiomeCase(unittest.TestCase):
    """阈值与 external/civ-atlas/src/gen/biomes.ts classifyBiome 一致。"""

    def test_thresholds_match_civ_atlas(self):
        cases = [((-10, 500), None), ((-5, 100), 'cold_desert'), ((-5, 200), 'tundra'),
                 ((0, 200), 'cold_desert'), ((0, 400), 'taiga'),
                 ((10, 200), 'temperate_desert'), ((10, 400), 'steppe'),
                 ((10, 1000), 'temperate_forest'), ((10, 2400), 'temperate_rainforest'),
                 ((25, 200), 'hot_desert'), ((25, 600), 'savanna'),
                 ((25, 1200), 'tropical_dry_forest'), ((25, 2000), 'rainforest')]
        for (t, p), expected in cases:
            self.assertEqual(tr.classify_biome(t, p), expected, (t, p))

    def test_every_candidate_is_a_climate_terrain(self):
        for t in (-20, -5, 0, 10, 25):
            for key in tr.biome_candidates(t):
                self.assertEqual(tr.RULES[key], 'climate')


class CellCase(unittest.TestCase):
    def test_sea_is_ocean_only(self):
        cell = tr.classify_cell(is_sea=True, elev_m=-200, lat_deg=10)
        self.assertEqual(cell['terrains'], ['ocean'])

    def test_high_flat_land_is_plateau_not_mountain(self):
        cell = tr.classify_cell(is_sea=False, elev_m=4200, lat_deg=32,
                                slope_deg=3, relief_m=250, dist_to_sea_km=900)
        self.assertIn('plateau', cell['terrains'])
        self.assertNotIn('mountain', cell['terrains'])

    def test_rugged_land_is_mountain_not_plateau(self):
        cell = tr.classify_cell(is_sea=False, elev_m=2500, lat_deg=46,
                                slope_deg=22, relief_m=1400, dist_to_sea_km=300)
        self.assertIn('mountain', cell['terrains'])
        self.assertNotIn('plateau', cell['terrains'])

    def test_missing_precip_gives_candidates_and_says_so(self):
        cell = tr.classify_cell(is_sea=False, elev_m=100, lat_deg=50, slope_deg=2)
        self.assertTrue(cell['candidates'])
        self.assertTrue(any('降水' in m for m in cell['missing']))
        self.assertTrue(any('估算' in a for a in cell['assumed']))
        self.assertFalse(set(cell['candidates']) & set(cell['terrains']))

    def test_lapse_rate_cools_high_ground(self):
        low = tr.estimate_temp_c(0, 0)
        high = tr.estimate_temp_c(0, 4000)
        self.assertAlmostEqual(low - high, 26.0, places=6)

    def test_layers_are_required_for_lake_river_wetland(self):
        cell = tr.classify_cell(is_sea=False, elev_m=50, lat_deg=30, slope_deg=1,
                                layers={'river': True})
        self.assertIn('river', cell['terrains'])
        self.assertTrue(any(m.startswith('lake') for m in cell['missing']))

    def test_farmland_needs_water_evidence(self):
        dry = tr.classify_cell(is_sea=False, elev_m=200, lat_deg=40, slope_deg=2, precip_mm=150)
        self.assertNotIn('farmland', dry['suitable'])
        irrigated = tr.classify_cell(is_sea=False, elev_m=200, lat_deg=40, slope_deg=2,
                                     precip_mm=150, layers={'river': True})
        self.assertIn('farmland', irrigated['suitable'])

    def test_matches_element_ignores_import_and_candidates(self):
        cell = tr.classify_cell(is_sea=False, elev_m=100, lat_deg=50, slope_deg=2)
        self.assertFalse(tr.matches_element(cell, ['import', 'workshop']))
        self.assertFalse(tr.matches_element(cell, ['temperate_forest']))
        self.assertTrue(tr.matches_element(cell, ['pasture']))

    def test_rejects_bad_numbers(self):
        with self.assertRaises(ValueError):
            tr.classify_cell(is_sea=False, elev_m=float('nan'), lat_deg=0)
        with self.assertRaises(ValueError):
            tr.classify_cell(is_sea=False, elev_m=0, lat_deg=95)


if __name__ == '__main__':
    unittest.main()
