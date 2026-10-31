# -*- coding: utf-8 -*-
"""建筑范围与用地规划校验器单测。

这些测试守的是「不要多说话」：未圈出的区域不能被当成荒地或农田、矿山不能被当成
已勘探矿藏、跨日界的环不能被算成 358° 宽、自交的环必须拒。
"""
import unittest

from app import land_footprint as lf


SQUARE = [[10.0, 20.0], [10.05, 20.0], [10.05, 20.05], [10.0, 20.05]]


class VertexTests(unittest.TestCase):
    def test_too_few_vertices_refused(self):
        with self.assertRaises(lf.FootprintError):
            lf.parse_vertices([[0.0, 0.0], [1.0, 1.0]], label='x')

    def test_bool_and_string_and_nan_refused(self):
        for bad in ([[True, 0.0], [1.0, 1.0], [2.0, 2.0]],
                    [['0', 0.0], [1.0, 1.0], [2.0, 2.0]],
                    [[float('nan'), 0.0], [1.0, 1.0], [2.0, 2.0]]):
            with self.assertRaises(lf.FootprintError):
                lf.parse_vertices(bad, label='x')

    def test_out_of_range_refused(self):
        with self.assertRaises(lf.FootprintError):
            lf.parse_vertices([[181.0, 0.0], [1.0, 1.0], [2.0, 2.0]], label='x')
        with self.assertRaises(lf.FootprintError):
            lf.parse_vertices([[0.0, 91.0], [1.0, 1.0], [2.0, 2.0]], label='x')

    def test_closing_point_is_dropped(self):
        ring = lf.parse_vertices(SQUARE + [SQUARE[0]], label='x')
        self.assertEqual(len(ring), 4)

    def test_duplicate_vertices_refused(self):
        with self.assertRaises(lf.FootprintError):
            lf.parse_vertices([[1.0, 1.0], [1.0, 1.0], [2.0, 2.0]], label='x')


class AreaTests(unittest.TestCase):
    def test_square_area_is_close_to_hand_computed_value(self):
        # 0.05° × 0.05° 在纬度 20° 处：0.05*111.32 = 5.566 km 纬向，
        # 经向 5.566*cos(20°)=5.231 km → 约 29.1 km²
        area = lf.polygon_area_km2([tuple(p) for p in SQUARE])
        self.assertAlmostEqual(area, 5.566 * 5.231, delta=0.6)

    def test_date_line_ring_is_not_358_degrees_wide(self):
        # 179 → -179 是跨日界的 2°，不是 358°；这里是一个真正有面积的跨日界四边形
        across = [[179.9, 10.0], [179.95, 10.0], [-179.95, 10.05], [179.9, 10.05]]
        area = lf.polygon_area_km2([tuple(p) for p in across])
        self.assertGreater(area, 0.0, '跨日界的四边形必须有正面积')
        self.assertLess(area, 200.0, '跨日界的窄环不应被算成横跨半个地球')


class FootprintTests(unittest.TestCase):
    def test_footprint_marks_author_planned_boundary(self):
        fp = lf.parse_footprint(SQUARE)
        self.assertEqual(fp['boundary_source'], 'author_planned_boundary')
        self.assertEqual(fp['terrain_detail'], 'coarse_mesh_reference_only')
        self.assertTrue(fp['unknown'], '必须列出未知项，不能假装精细地形已知')
        self.assertGreater(fp['area_km2'], 0.0)

    def test_footprint_area_cap_is_enforced(self):
        big = [[10.0, 20.0], [11.0, 20.0], [11.0, 21.0], [10.0, 21.0]]   # ~12000 km²
        with self.assertRaises(lf.FootprintError) as ctx:
            lf.parse_footprint(big)
        self.assertIn('超过', str(ctx.exception))

    def test_self_intersecting_ring_refused(self):
        bowtie = [[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [0.0, 1.0]]
        with self.assertRaises(lf.FootprintError) as ctx:
            lf.parse_polygon(bowtie, max_area_km2=20000.0)
        self.assertIn('自交', str(ctx.exception))


class LandUseTests(unittest.TestCase):
    def test_mine_is_intent_only(self):
        entries = lf.parse_land_use([{'kind': 'mine', 'vertices': SQUARE}])
        self.assertFalse(entries[0]['surveyed'])
        self.assertFalse(entries[0]['productive_now'])
        self.assertIn('不是已勘探', entries[0]['note_supply'])

    def test_farmland_is_declared_but_not_instant_harvest(self):
        entries = lf.parse_land_use([{'kind': 'farmland', 'vertices': SQUARE}])
        self.assertIn('仍需通过', entries[0]['note_supply'])
        # 声明了农田不等于现在就有产出
        self.assertFalse(entries[0]['productive_now'])

    def test_unknown_kind_refused(self):
        with self.assertRaises(lf.FootprintError):
            lf.parse_land_use([{'kind': 'gold_mine', 'vertices': SQUARE}])

    def test_unknown_field_refused(self):
        with self.assertRaises(lf.FootprintError):
            lf.parse_land_use([{'kind': 'farmland', 'vertices': SQUARE, 'yield_t': 100}])

    def test_too_many_items_refused(self):
        items = [{'kind': 'other', 'vertices': SQUARE} for _ in range(65)]
        with self.assertRaises(lf.FootprintError):
            lf.parse_land_use(items)

    def test_empty_is_allowed_and_nothing_is_assumed(self):
        summary = lf.summarize_land_use(lf.parse_land_use([]))
        self.assertEqual(summary['declared_km2'], 0.0)
        self.assertTrue(summary['unplanned_elsewhere'])
        self.assertIn('不当作荒地', summary['unplanned_note'])

    def test_overlap_is_reported_not_resolved(self):
        near = [[10.01, 20.01], [10.06, 20.01], [10.06, 20.06], [10.01, 20.06]]
        entries = lf.parse_land_use([{'kind': 'farmland', 'vertices': SQUARE},
                                     {'kind': 'mine', 'vertices': near}])
        summary = lf.summarize_land_use(entries)
        self.assertEqual(len(summary['conflicts']), 1)
        self.assertIn('不自动择一', summary['conflicts'][0]['note'])

    def test_non_overlapping_is_clean(self):
        far = [[11.0, 21.0], [11.05, 21.0], [11.05, 21.05], [11.0, 21.05]]
        entries = lf.parse_land_use([{'kind': 'farmland', 'vertices': SQUARE},
                                     {'kind': 'forest', 'vertices': far}])
        summary = lf.summarize_land_use(entries)
        self.assertEqual(summary['conflicts'], [])
        self.assertGreater(summary['productive_declared_km2'], 0.0)

    def test_wasteland_must_be_explicit(self):
        entries = lf.parse_land_use([{'kind': 'wasteland', 'vertices': SQUARE}])
        summary = lf.summarize_land_use(entries)
        self.assertIn('wasteland', summary['by_kind_km2'])
        # 荒地显式声明了，但它不是生产用地
        self.assertEqual(summary['productive_declared_km2'], 0.0)


if __name__ == '__main__':
    unittest.main()
