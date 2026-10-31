# -*- coding: utf-8 -*-
"""空间草稿专项单测：只有建筑范围也能存、CAS、只读、无供给拒不丢草稿、矿牧非粮。

这些测试守的是「不要把话说大」：
- 建筑范围/矿山/牧场/荒地都不进 ``terrain.area_km2``（那边是粮食腹地）；
- 只圈建筑范围可以保存，但转换必须报缺项并且**不动草稿**；
- 重叠只按 ``land_footprint`` 的既有筛查报告，不静默按 sum 双算；
- 源引用只认 import id + 内容哈希，id 与哈希不自洽就直接拒；
- 旧故事包版本的草稿不许挂到新世界上。

全部离线：临时数据库 + 假 resolver/假 sampler，不读 data/、不碰 artifacts。
"""
import copy
import tempfile
import unittest
from pathlib import Path

from app import land_footprint as lf
from app import map_import, spatial_draft as sd
from app.storage import Store

STORY = 'story_rev_0001'

#: ~29 km² 在纬度 20°：一个正常的城镇建筑范围（不是省）。
SQUARE = [[10.0, 20.0], [10.05, 20.0], [10.05, 20.05], [10.0, 20.05]]
FARMLAND = [[10.2, 20.2], [10.35, 20.2], [10.35, 20.35], [10.2, 20.35]]
#: 与 FARMLAND 部分重叠的另一块农田：两块都声明时不能按 sum 双算。
FARMLAND_NEAR = [[10.25, 20.25], [10.4, 20.25], [10.4, 20.4], [10.25, 20.4]]
NEAR = [[10.01, 20.01], [10.06, 20.01], [10.06, 20.06], [10.01, 20.06]]
#: 十字：两条长条农田，四个顶点全在对方环外，顶点包含筛查看不出重叠。
BAR_H = [[10.0, 20.40], [10.40, 20.40], [10.40, 20.44], [10.0, 20.44]]
BAR_V = [[10.18, 20.30], [10.22, 20.30], [10.22, 20.54], [10.18, 20.54]]

IMPORT_ID = 'mi_abcdef123456'
SOURCE_SHA = 'abcdef123456' + '0' * 52


def import_record(**over):
    record = {
        'id': IMPORT_ID,
        'format': map_import.FORMAT,
        'sha256': SOURCE_SHA,
        'bytes': 123456,
        'width': 2048,
        'height': 1024,
        'pixels': 2048 * 1024,
        'lo_m': -4000,
        'hi_m': 3000,
        'sea_gray': 20000,
        'stats': {'sea_px': 10, 'land_px': 20},
        'units': {'elevation': 'linear', 'radius_assumption_km': 6371.0088},
        'source': {'project': 'civ-atlas', 'world_id': 'wmtest'},
        'created': '2026-11-01T00:00:00+00:00',
    }
    record.update(over)
    return record


def env_ref(**over):
    ref = {'import_id': IMPORT_ID, 'source_sha256': SOURCE_SHA}
    ref.update(over)
    return ref


def sample(**over):
    data = {'lon': 10.02, 'lat': 20.02, 'window_px': 3, 'radius_km': 6371.0088,
            'area_km2': 44878.0,
            'elevation_m': {'min': 120.0, 'max': 340.0, 'mean': 210.0},
            'slope_deg': {'p50': 3.2, 'max': 9.0},
            'pixel': {'x': 1000, 'y': 400},
            'span_km': {'north_south': 210.0, 'east_west': 212.0},
            'climate': {'measured': True, 'temperature_c': 12.0, 'precipitation_mm': 800.0,
                        'biome_name': 'grassland'},
            'derived': ['elevation_m', 'area_km2'], 'warnings': []}
    data.update(over)
    return data


AUTHOR = {'region': '测试区域', 'climate_source': 'measured',
          'water': {'source': 'river', 'reliability': 0.8, 'daily_capacity_l': 200000,
                    'storage': 'none', 'distance_km': 1.0},
          'transport': {'road': 'track', 'water_route': False, 'portage': False,
                        'seasonal_closed_days': 10, 'nearest_market_days': 2},
          'materials': ['timber', 'stone'], 'technology': ['timber_frame'],
          'confirm_template': True}


class FakeRuntime:
    def __init__(self, revision):
        self.revision = revision

    def has_world(self):
        # 空态契约：没有世界时 base_revision() 必须是 None（这里 revision 为 None 即空）。
        return self.revision is not None

    def package(self, revision=None):
        return {'id': revision or self.revision}


class FakeService:
    def __init__(self, store, revision=STORY):
        self.store = store
        self.runtime = FakeRuntime(revision)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'spatial.sqlite3'
        self.store = Store(self.path)
        self.store.put('map_import', IMPORT_ID, import_record())

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------------- helpers
    def body(self, **over):
        data = {'site_name': '河湾村', 'footprint': {'vertices': SQUARE},
                'land_use': [], 'environment_ref': env_ref(),
                'sampling': {'lon': 10.02, 'lat': 20.02, 'window_px': 3}}
        data.update(over)
        return data

    def saved(self, **over):
        return sd.save(self.store, self.body(**over), story_base_revision=STORY)['draft']


class SaveTests(Base):
    def test_footprint_only_is_storable_and_supply_unconfigured(self):
        draft = self.saved()
        self.assertEqual(draft['supply']['state'], sd.SUPPLY_UNCONFIGURED)
        self.assertIsNone(draft['area_plan']['terrain_area_km2'])
        self.assertGreater(draft['footprint']['area_km2'], 0.0)
        # 建筑面积从不进粮食腹地
        self.assertNotAlmostEqual(draft['area_plan'].get('terrain_area_km2') or 0.0,
                                  draft['footprint']['area_km2'])
        self.assertIn('建筑范围', ' '.join(draft['warnings']))

    def test_draft_survives_a_restart(self):
        draft = self.saved()
        reopened = Store(self.path)
        again = sd.get(reopened, draft['id'])
        self.assertEqual(again['content_hash'], draft['content_hash'])
        self.assertEqual(again['site_name'], '河湾村')
        self.assertEqual(again['sampling']['lon'], 10.02)

    def test_two_same_named_places_do_not_swallow_each_other(self):
        first = self.saved()
        second = self.saved(footprint={'vertices': [[11.0, 21.0], [11.05, 21.0],
                                                    [11.05, 21.05], [11.0, 21.05]]})
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(first['site_name'], second['site_name'])
        self.assertEqual(len(sd.list_drafts(self.store)), 2)

    def test_request_id_makes_creation_idempotent_and_refuses_new_content(self):
        result = sd.save(self.store, self.body(request_id='req-1'), story_base_revision=STORY)
        self.assertTrue(result['created'])
        again = sd.save(self.store, self.body(request_id='req-1'), story_base_revision=STORY)
        self.assertFalse(again['created'])
        self.assertEqual(again['draft']['id'], result['draft']['id'])
        with self.assertRaises(sd.SpatialDraftError):
            sd.save(self.store, self.body(request_id='req-1',
                                          footprint={'vertices': [[12.0, 22.0], [12.05, 22.0],
                                                                  [12.05, 22.05], [12.0, 22.05]]}),
                    story_base_revision=STORY)

    def test_story_pointer_is_never_written(self):
        self.saved()
        self.assertIsNone(self.store.get('pointer', 'package'))

    def test_sampling_parameters_are_stored_so_a_restart_can_resample(self):
        draft = self.saved(sampling={'lon': 10.03, 'lat': 20.04, 'window_px': 5,
                                     'radius_km': 6000.0})
        self.assertEqual(draft['sampling'], {'lon': 10.03, 'lat': 20.04, 'window_px': 5,
                                             'radius_km': 6000.0, 'source': 'author_stated',
                                             'note': draft['sampling']['note']})

    def test_missing_sampling_falls_back_to_labelled_vertex_mean(self):
        draft = self.saved(sampling=None)
        self.assertEqual(draft['sampling']['source'], 'footprint_vertex_mean')
        self.assertAlmostEqual(draft['sampling']['lon'], 10.025, places=4)


class CasTests(Base):
    def test_stale_revision_does_not_write(self):
        draft = self.saved()
        newer = sd.update(self.store, draft['id'],
                          self.body(footprint={'vertices': [[10.0, 20.0], [10.03, 20.0],
                                                           [10.03, 20.03], [10.0, 20.03]]}),
                          expected_revision=0)
        self.assertEqual(newer['revision'], 1)
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.update(self.store, draft['id'], self.body(), expected_revision=0)
        self.assertIn('已被其他操作更新', str(ctx.exception))
        unchanged = sd.get(self.store, draft['id'])
        self.assertEqual(unchanged['revision'], 1)
        self.assertEqual(unchanged['content_hash'], newer['content_hash'])

    def test_reads_are_read_only(self):
        draft = self.saved()
        before = copy.deepcopy(draft)
        sd.get(self.store, draft['id'])
        sd.list_drafts(self.store)
        sd.prepare_conversion(draft)
        after = sd.get(self.store, draft['id'])
        self.assertEqual(after['revision'], before['revision'])
        self.assertEqual(after['updated'], before['updated'])
        self.assertEqual(after['content_hash'], before['content_hash'])

    def test_bad_revision_type_refused(self):
        draft = self.saved()
        for bad in (True, '0', 0.0, None):
            with self.assertRaises(sd.SpatialDraftError):
                sd.update(self.store, draft['id'], self.body(), expected_revision=bad)


class ConversionTests(Base):
    def test_no_supply_blocks_conversion_and_keeps_the_draft(self):
        draft = self.saved()
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('farmland_or_hinterland', result['missing'])
        self.assertIsNone(result['input'])
        kept = sd.get(self.store, draft['id'])
        self.assertEqual(kept['revision'], draft['revision'])
        self.assertEqual(kept['content_hash'], draft['content_hash'])

    def test_mine_and_pasture_are_not_grain(self):
        draft = self.saved(land_use=[{'kind': 'mine', 'vertices': FARMLAND},
                                     {'kind': 'pasture', 'vertices':
                                      [[10.5, 20.5], [10.55, 20.5], [10.55, 20.55],
                                       [10.5, 20.55]]}])
        self.assertEqual(draft['supply']['state'], sd.SUPPLY_UNCONFIGURED)
        self.assertEqual(draft['area_plan']['grain_km2'], 0.0)
        self.assertGreater(draft['area_plan']['pasture_km2'], 0.0)
        self.assertFalse(any(e['productive_now'] for e in draft['land_use']))
        mine = [e for e in draft['land_use'] if e['kind'] == 'mine'][0]
        self.assertFalse(mine['surveyed'])
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('farmland_or_hinterland', result['missing'])

    def test_overlapping_farmland_blocks_conversion(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND},
                                     {'kind': 'farmland', 'vertices': FARMLAND_NEAR}])
        self.assertEqual(len(draft['land_use_summary']['conflicts']), 1)
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('overlapping_farmland', result['missing'])
        self.assertTrue(result['spatial']['blocking_conflicts'])

    def test_footprint_overlapping_farmland_blocks_conversion(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': NEAR}])
        self.assertTrue(draft['footprint_conflicts'])
        # 面积不做差集：农田面积照它自己的环算，报告交给作者
        self.assertAlmostEqual(draft['area_plan']['farmland_km2'],
                               draft['land_use'][0]['area_km2'], places=3)
        # 草稿可以存、可以改，但转换必须断——不能把房子算成粮田
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('footprint_overlaps_land_use', result['missing'])
        self.assertIsNone(result['input'])
        self.assertEqual(sd.get(self.store, draft['id'])['revision'], draft['revision'])
        # 重画到不重叠后就能转换
        fixed = sd.update(self.store, draft['id'],
                          self.body(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}]),
                          expected_revision=draft['revision'])
        self.assertEqual(fixed['footprint_conflicts'], [])
        ok = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                              current_story_revision=STORY, sample=sample())
        self.assertEqual(ok['status'], 'ready', ok)

    def test_crossing_farmland_bars_block_conversion(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': BAR_H},
                                     {'kind': 'farmland', 'vertices': BAR_V}])
        # 顶点包含筛查看不出来，但环间边相交必须看得出来
        self.assertEqual(draft['land_use_summary']['conflicts'], [])
        self.assertEqual(len(draft['overlaps']), 1)
        self.assertEqual(draft['overlaps'][0]['methods'], ['edge_crossing'])
        self.assertTrue(draft['overlap_scan']['complete'])
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('overlapping_farmland', result['missing'])
        self.assertIsNone(result['input'])

    def test_footprint_area_never_becomes_terrain_area(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        self.assertEqual(draft['supply']['state'], sd.SUPPLY_CONFIGURED)
        self.assertAlmostEqual(draft['area_plan']['terrain_area_km2'],
                               draft['land_use'][0]['area_km2'], places=3)
        self.assertNotAlmostEqual(draft['area_plan']['terrain_area_km2'],
                                  draft['footprint']['area_km2'], places=3)

    def test_conversion_builds_a_town_input_and_still_does_not_touch_the_draft(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'ready', result)
        terrain = result['input']['terrain']
        self.assertAlmostEqual(terrain['area_km2'], draft['land_use'][0]['area_km2'], places=3)
        self.assertNotAlmostEqual(terrain['area_km2'], draft['footprint']['area_km2'], places=3)
        # 面积口径与 provenance 都是显式的
        self.assertEqual(result['provenance']['hinterland']['source'],
                         'declared_productive_land_use')
        self.assertEqual(result['provenance']['spatial_draft']['sample_source'],
                         'caller_supplied_checked_against_draft')
        self.assertTrue(result['spatial']['area_approximation']['planned_is_not_cultivated'])
        self.assertEqual(sd.get(self.store, draft['id'])['revision'], draft['revision'])

    def test_stale_story_revision_is_refused(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                             current_story_revision='story_rev_0002', sample=sample())
        self.assertIn('故事包版本', str(ctx.exception))
        report = sd.prepare_conversion(draft, current_story_revision='story_rev_0002')
        self.assertIn('story_base_revision_mismatch', report['missing'])

    def test_sample_from_another_point_is_refused(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                             current_story_revision=STORY, sample=sample(lon=30.0, lat=40.0))
        self.assertIn('取样点与草稿保存的选点不一致', str(ctx.exception))
        with self.assertRaises(sd.SpatialDraftError):
            sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                             current_story_revision=STORY, sample=sample(window_px=7))

    def test_author_cannot_smuggle_geometry(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        bad = dict(AUTHOR, hinterland_km2=900.0)
        with self.assertRaises(sd.SpatialDraftError):
            sd.to_town_input(self.store, draft['id'], author=bad,
                             current_story_revision=STORY, sample=sample())

    def test_explicit_hinterland_is_the_area_source(self):
        draft = self.saved(hinterland_km2=300.0)
        self.assertEqual(draft['supply']['state'], sd.SUPPLY_CONFIGURED)
        self.assertEqual(draft['area_plan']['area_source'], sd.AREA_SOURCE_HINTERLAND)
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sample=sample())
        self.assertEqual(result['status'], 'ready', result)
        self.assertAlmostEqual(result['input']['terrain']['area_km2'], 300.0, places=3)


class StrictnessTests(Base):
    def test_unknown_request_field_refused(self):
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint_path='D:/x.png'),
                    story_base_revision=STORY)
        self.assertIn('未知字段', str(ctx.exception))

    def test_unknown_land_use_field_refused(self):
        for extra in ({'surveyed': True}, {'yield_t': 100}):
            item = dict({'kind': 'mine', 'vertices': FARMLAND}, **extra)
            with self.assertRaises(sd.SpatialDraftError):
                sd.save(self.store, self.body(land_use=[item]), story_base_revision=STORY)

    def test_nan_and_bool_coordinates_refused(self):
        bad = [[float('nan'), 20.0], [10.05, 20.0], [10.05, 20.05]]
        with self.assertRaises(sd.SpatialDraftError):
            sd.save(self.store, self.body(footprint={'vertices': bad}),
                    story_base_revision=STORY)
        bad = [[True, 20.0], [10.05, 20.0], [10.05, 20.05]]
        with self.assertRaises(sd.SpatialDraftError):
            sd.save(self.store, self.body(footprint={'vertices': bad}),
                    story_base_revision=STORY)

    def test_out_of_range_and_too_large_area_refused(self):
        with self.assertRaises(sd.SpatialDraftError):
            sd.save(self.store, self.body(footprint={'vertices': [[181.0, 20.0], [10.0, 20.0],
                                                                  [10.0, 20.1]]}),
                    story_base_revision=STORY)
        big = [[10.0, 20.0], [11.0, 20.0], [11.0, 21.0], [10.0, 21.0]]
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint={'vertices': big}),
                    story_base_revision=STORY)
        self.assertIn('超过', str(ctx.exception))

    def test_vertex_budget_is_enforced_before_self_intersection(self):
        # 每面 200 个顶点，每面合法但总顶点超过 512：必须在 O(n²) 之前就拒
        ring = [[10.0 + i * 0.0002, 20.0] for i in range(199)] + [[10.0, 20.001]]
        self.assertEqual(len(ring), 200)
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint={'vertices': ring},
                                          land_use=[{'kind': 'farmland', 'vertices': ring},
                                                    {'kind': 'mine', 'vertices': ring}]),
                    story_base_revision=STORY)
        self.assertIn('总预算', str(ctx.exception))
        # 单面超过 256 也拒（4096 顶点的那条上限在这里不生效）
        wide = [[10.0 + i * 0.0001, 20.0] for i in range(257)]
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint={'vertices': wide}),
                    story_base_revision=STORY)
        self.assertIn('单面上限', str(ctx.exception))

    def test_normal_town_polygon_is_not_refused_for_being_small(self):
        small = [[10.0, 20.0], [10.004, 20.0], [10.004, 20.004], [10.0, 20.004]]
        draft = self.saved(footprint={'vertices': small})
        self.assertGreater(draft['footprint']['area_km2'], 0.0)
        self.assertLess(draft['footprint']['area_km2'], 1.0)

    def test_extreme_latitude_is_refused_with_a_reason(self):
        polar = [[10.0, 79.0], [10.05, 79.0], [10.05, 79.05], [10.0, 79.05]]
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint={'vertices': polar}),
                    story_base_revision=STORY)
        self.assertIn('纬带', str(ctx.exception))
        span = [[10.0, 10.0], [10.05, 10.0], [10.05, 45.0], [10.0, 45.0]]
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(footprint={'vertices': span}),
                    story_base_revision=STORY)
        self.assertIn('纬度跨度', str(ctx.exception))

    def test_environment_ref_must_be_import_id_and_hash(self):
        for bad in ({'import_id': 'D:/data/world.png', 'source_sha256': SOURCE_SHA},
                    {'import_id': 'https://example.com/x.png', 'source_sha256': SOURCE_SHA},
                    {'import_id': IMPORT_ID, 'source_sha256': 'abc'},
                    {'import_id': IMPORT_ID}):
            with self.assertRaises(sd.SpatialDraftError):
                sd.save(self.store, self.body(environment_ref=bad),
                        story_base_revision=STORY)

    def test_source_hash_conflict_is_refused(self):
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(environment_ref=env_ref(source_sha256='f' * 64)),
                    story_base_revision=STORY)
        self.assertIn('源哈希冲突', str(ctx.exception))

    def test_record_whose_id_does_not_match_its_hash_is_refused(self):
        self.store.put('map_import', 'mi_000000000000',
                       import_record(id='mi_000000000000', sha256=SOURCE_SHA))
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(environment_ref={'import_id': 'mi_000000000000',
                                                           'source_sha256': SOURCE_SHA}),
                    story_base_revision=STORY)
        self.assertIn('不自洽', str(ctx.exception))

    def test_unsupported_format_is_refused(self):
        record = import_record(id='mi_000000000001', sha256='000000000001' + '0' * 52,
                               format='azgaar_json')
        resolver = lambda identifier: record
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.save(self.store, self.body(environment_ref={'import_id': 'mi_000000000001',
                                                           'source_sha256': '000000000001' + '0' * 52}),
                    story_base_revision=STORY, resolver=resolver)
        self.assertIn('格式', str(ctx.exception))

    def test_empty_geometry_is_refused(self):
        with self.assertRaises(sd.SpatialDraftError):
            sd.save(self.store, self.body(footprint=None, land_use=[]),
                    story_base_revision=STORY)

    def test_story_base_revision_must_be_given(self):
        # 空世界允许 None（真实契约）；非法字符串/类型仍必须拒。
        for bad in ('', 'short', 12345):
            with self.assertRaises(sd.SpatialDraftError):
                sd.save(self.store, self.body(), story_base_revision=bad)
        draft = sd.save(self.store, self.body(), story_base_revision=None)['draft']
        self.assertIsNone(draft['story_base_revision'])


class WorldBasisTests(Base):
    def _basis(self, **over):
        from app import world_basis as wb
        record = import_record()
        record.update(over)
        return wb.build(record, base_year=1500, branch='main')

    def test_basis_ref_is_snapshotted_and_checked(self):
        from app import world_basis as wb
        basis = self._basis(sha256=SOURCE_SHA)
        record = import_record()
        # build() 用记录自身 id/哈希做身份，这里只需它自洽
        basis = wb.build(record, base_year=1500, branch='main')
        wb.save(self.store, basis)
        draft = self.saved(world_basis_ref=basis['id'])
        self.assertEqual(draft['world_basis_ref']['id'], basis['id'])
        self.assertEqual(draft['world_basis_ref']['base_year'], 1500)
        self.assertNotIn('capability', draft['world_basis_ref'])

    def test_basis_for_other_bytes_is_refused(self):
        from app import world_basis as wb
        other = import_record(id='mi_111111111111', sha256='1' * 28 + '2' * 36,
                              format=map_import.FORMAT)
        basis = wb.build(other, base_year=1400, branch='main')
        wb.save(self.store, basis)
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            self.saved(world_basis_ref=basis['id'])
        self.assertIn('哈希不一致', str(ctx.exception))

    def test_unknown_basis_is_refused(self):
        with self.assertRaises(sd.SpatialDraftError):
            self.saved(world_basis_ref='wb_deadbeefdeadbeef')


class ServiceWiringTests(Base):
    def test_service_shim_uses_current_package_and_own_sampler(self):
        service = sd.SpatialDraftService(FakeService(self.store))
        created = service.save(self.body(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}]))
        draft = created['draft']
        self.assertEqual(draft['story_base_revision'], STORY)
        self.assertEqual([d['id'] for d in service.list()], [draft['id']])
        self.assertEqual(service.get(draft['id'])['id'], draft['id'])
        report = service.prepare(draft['id'])
        self.assertTrue(report['ready'], report)
        self.assertEqual(service.view(draft)['site_name'], '河湾村')

    def test_service_shim_refuses_other_story_base(self):
        service = sd.SpatialDraftService(FakeService(self.store, revision='story_rev_9999'))
        with self.assertRaises(sd.SpatialDraftError):
            sd.to_town_input(self.store, self.saved()['id'], author=AUTHOR,
                             current_story_revision=service.base_revision(), sample=sample())

    def test_sampler_arguments_come_from_the_draft(self):
        calls = []

        def sampler(draft, lon, lat, window_px, radius_km):
            calls.append((draft['id'], draft['revision'], lon, lat, window_px, radius_km))
            return sample(lon=lon, lat=lat, window_px=window_px, radius_km=radius_km)

        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}],
                           sampling={'lon': 10.02, 'lat': 20.02, 'window_px': 3,
                                     'radius_km': 6371.0088})
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sampler=sampler)
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(calls, [(draft['id'], 0, 10.02, 20.02, 3, 6371.0088)])
        self.assertEqual(result['provenance']['spatial_draft']['sample_source'],
                         'server_recomputed')
        # 给了 sampler 时客户端 sample 不被采信
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sampler=sampler,
                                  sample=sample(lon=10.02, lat=20.02, window_px=3,
                                                elevation_m={'mean': 3000.0}))
        self.assertEqual(result['input']['terrain']['elevation_m'], 210.0)

    def test_old_two_arg_sampler_signature_still_works(self):
        def sampler(lon, lat, window_px, radius_km):
            return sample(lon=lon, lat=lat, window_px=window_px, radius_km=radius_km)

        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        result = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                  current_story_revision=STORY, sampler=sampler)
        self.assertEqual(result['status'], 'ready', result)

    def test_conversion_reading_a_moved_draft_is_refused(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])

        # 取样中途别人改了一版：交出 input 之前必须拒
        def sampler(draft_snapshot, lon, lat, window_px, radius_km):
            sd.update(self.store, draft['id'],
                      self.body(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}]),
                      expected_revision=draft['revision'])
            return sample(lon=lon, lat=lat, window_px=window_px, radius_km=radius_km)

        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                             current_story_revision=STORY, sampler=sampler)
        self.assertIn('转换期间', str(ctx.exception))
        self.assertEqual(sd.get(self.store, draft['id'])['revision'], draft['revision'] + 1)

    def test_expected_revision_is_checked_before_work(self):
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                             current_story_revision=STORY, sample=sample(),
                             expected_revision=draft['revision'] + 5)
        self.assertIn('已被其他操作更新', str(ctx.exception))
        ready = sd.to_town_input(self.store, draft['id'], author=AUTHOR,
                                 current_story_revision=STORY, sample=sample(),
                                 expected_revision=draft['revision'])
        self.assertEqual(ready['status'], 'ready')

    def test_service_sampler_uses_the_snapshot_not_a_reread(self):
        service = sd.SpatialDraftService(FakeService(self.store))
        draft = self.saved(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        sampler = service.sampler(draft['id'])
        # 传进去的快照指向一个不存在的导入：错误必须提到快照里的那个编号，
        # 说明取样参数与来源都来自传入的快照本身，不是重新读一遍草稿
        stale = dict(draft, environment_ref=dict(draft['environment_ref'],
                                                 import_id='mi_999999999999',
                                                 source_sha256='9' * 64))
        with self.assertRaises(sd.SpatialDraftError) as ctx:
            sampler(stale, 10.02, 20.02, 3, 6371.0088)
        self.assertIn('mi_999999999999', str(ctx.exception))


class LandFootprintReuseTests(unittest.TestCase):
    def test_parser_limits_are_reused_not_reinvented(self):
        self.assertEqual(sd.MAX_FACES, lf.MAX_LAND_USE_ITEMS)
        self.assertLess(sd.MAX_FACE_VERTICES, lf.MAX_VERTICES)
        self.assertLessEqual(sd.MAX_TOTAL_VERTICES, sd.MAX_FACE_VERTICES * 2)


if __name__ == '__main__':
    unittest.main()
