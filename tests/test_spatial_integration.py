# -*- coding: utf-8 -*-
"""空间草稿端点专项：真实 TestClient + 临时库 + 真实 civsnap 取样转换。

守的是「别把话说大」：
- 只圈建筑范围能存能读回，但转换必须报缺项，且草稿一个字节不动；
- 客户端送 sample 在请求模型层就被拒（不是靠运行时检查）；
- 无 token / 未知 id 被挡；坏的几何被拒且不留半写；
- 有农田时服务端自己重算取样，转换出的 TownInput 真能走完城镇四阶段生成；
- 旧故事包版本变了就拒，不把旧草稿悄悄挂到新世界。

地图 fixture 直接复用 ``tests.test_civ_atlas_import.civsnap``（真实 CIVSNAP1 容器），
不另造预设替代；这里只挑一个既有网格点，数字仍由解析器读出。
"""
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import civ_atlas_snapshot, web
from tests.test_civ_atlas_import import civsnap

ROOT = Path(__file__).resolve().parents[1]

#: 8×8 网格里 cell(1,1) 的经纬度：lon = −180 + 360·1/8 = −135，lat = 90 − 180·1/8 = 67.5。
SITE_LON = -135.0
SITE_LAT = 67.5
SQUARE = [[-135.0, 67.50], [-134.95, 67.50], [-134.95, 67.55], [-135.0, 67.55]]
FARMLAND = [[-134.7, 67.4], [-134.55, 67.4], [-134.55, 67.55], [-134.7, 67.55]]
OVERLAP_FARM = [[-134.65, 67.45], [-134.5, 67.45], [-134.5, 67.6], [-134.65, 67.6]]

AUTHOR = {
    'region': '测试高地', 'climate_source': 'measured',
    'water': {'source': 'river', 'reliability': 0.8, 'daily_capacity_l': 200000,
              'storage': 'none', 'distance_km': 1.0},
    'transport': {'road': 'track', 'water_route': False, 'portage': False,
                  'seasonal_closed_days': 10, 'nearest_market_days': 2},
    'materials': ['timber', 'stone'], 'technology': ['timber_frame'],
    'confirm_template': True,
}


class SpatialEndpointCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = web.create_app(Path(self.tmp.name) / 'spatial.sqlite3')
        self.client = TestClient(self.app)
        token = self.client.get('/api/bootstrap').json()['token']
        self.headers = {'X-TextileDream-Token': token}
        self.service = self.app.state.service
        self.import_id = self._import_map()
        # 空世界是新的默认起点：这些用例需要**一个当前故事**来核对版本，
        # 所以由测试自己提交一个最小世界（不在生产启动时自动造任何包）。
        if not self.service.runtime.has_world():
            self.service.runtime.commit_package(*_minimal_world(), '测试采纳最小世界')

    # ------------------------------------------------------------------ fixtures
    def _import_map(self):
        response = self.client.post('/api/inner/map-imports', content=civsnap(),
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['id']

    def env_ref(self):
        record = self.client.get('/api/inner/map-imports/' + self.import_id,
                                 headers=self.headers).json()
        return {'import_id': record['id'], 'source_sha256': record['sha256']}

    def body(self, **over):
        data = {'site_name': '雪线上村',
                'footprint': {'vertices': SQUARE},
                'land_use': [],
                'environment_ref': self.env_ref(),
                'sampling': {'lon': SITE_LON, 'lat': SITE_LAT, 'window_px': 3}}
        data.update(over)
        return data

    def create(self, **over):
        return self.client.post('/api/inner/spatial-drafts', json={'draft': self.body(**over)},
                                headers=self.headers)

    def drafted(self, **over):
        response = self.create(**over)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['draft']

    def story_revision(self, draft):
        return draft['story_base_revision']

    # --------------------------------------------------------------------- tests
    def test_build_only_draft_saves_and_reads_back(self):
        draft = self.drafted()
        self.assertTrue(draft['id'].startswith('sd_'))
        self.assertEqual(draft['supply']['state'], 'unconfigured')
        again = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                                headers=self.headers)
        self.assertEqual(again.status_code, 200)
        payload = again.json()
        self.assertEqual(payload['site_name'], '雪线上村')
        self.assertAlmostEqual(payload['footprint']['area_km2'],
                               draft['footprint']['area_km2'], places=4)
        self.assertIn('footprint', payload)
        self.assertFalse(payload['conversion']['ready'])
        self.assertIn('farmland_or_hinterland', payload['conversion']['missing'])
        listing = self.client.get('/api/inner/spatial-drafts', headers=self.headers).json()
        self.assertEqual([row['id'] for row in listing], [draft['id']])
        # 列表不带几何像素/顶点大块，只带摘要
        self.assertNotIn('footprint', listing[0])

    def test_geometry_update_uses_revision_cas(self):
        draft = self.drafted()
        updated = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                  json={'expected_revision': draft['revision'],
                                        'draft': self.body(
                                            land_use=[{'kind': 'farmland',
                                                       'vertices': FARMLAND}])},
                                  headers=self.headers)
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['revision'], draft['revision'] + 1)
        self.assertEqual(updated.json()['supply']['state'], 'configured')

        stale = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                json={'expected_revision': draft['revision'],
                                      'draft': self.body()},
                                headers=self.headers)
        self.assertEqual(stale.status_code, 400)
        self.assertIn('已被其他操作更新', stale.json()['detail'])
        after = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                                headers=self.headers).json()
        self.assertEqual(after['revision'], draft['revision'] + 1)
        self.assertEqual(after['supply']['state'], 'configured')

    def test_expected_revision_is_mandatory_at_the_api_layer(self):
        draft = self.drafted()
        missing = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                  json={'draft': self.body()}, headers=self.headers)
        self.assertEqual(missing.status_code, 422)
        bad = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                              json={'expected_revision': '0', 'draft': self.body()},
                              headers=self.headers)
        self.assertEqual(bad.status_code, 422)

    def test_bad_geometry_is_refused_without_a_half_write(self):
        before = self.client.get('/api/inner/spatial-drafts', headers=self.headers).json()
        bodies = [
            self.body(footprint={'vertices': [[-135.0, 67.5], [-134.0, 67.5]]}),
            self.body(footprint={'vertices': [[-135.0, 67.5], [-134.9, 67.5],
                                              [-134.9, 67.6]], 'note': 'x' * 400}),
            self.body(land_use=[{'kind': 'gold_mine', 'vertices': FARMLAND}]),
            self.body(land_use=[{'kind': 'farmland', 'vertices': FARMLAND,
                                 'surveyed': True}]),
        ]
        for body in bodies:
            response = self.client.post('/api/inner/spatial-drafts', json={'draft': body},
                                        headers=self.headers)
            self.assertEqual(response.status_code, 400, response.text)
        # NaN 不是合法 JSON，要手写原文才递得进去；照样必须被拒
        raw = json.dumps({'draft': self.body(
            footprint={'vertices': [[-135.0, 67.5], [float('nan'), 67.5],
                                    [-134.9, 67.6]]})})
        nan = self.client.post('/api/inner/spatial-drafts',
                               content=raw.encode('utf-8'),
                               headers={**self.headers,
                                        'Content-Type': 'application/json'})
        self.assertEqual(nan.status_code, 400, nan.text)
        after = self.client.get('/api/inner/spatial-drafts', headers=self.headers).json()
        self.assertEqual(after, before)

    def test_unknown_request_field_is_refused(self):
        response = self.client.post(
            '/api/inner/spatial-drafts',
            json={'draft': self.body(width=None)}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('未知字段', response.json()['detail'])

    def test_token_and_unknown_id_are_refused(self):
        draft = self.drafted()
        self.assertEqual(self.client.get('/api/inner/spatial-drafts').status_code, 403)
        self.assertEqual(self.client.get('/api/inner/spatial-drafts/' + draft['id'])
                         .status_code, 403)
        missing = self.client.get('/api/inner/spatial-drafts/sd_0000000000000000',
                                  headers=self.headers)
        self.assertEqual(missing.status_code, 400)
        self.assertIn('找不到', missing.json()['detail'])
        no_supply = self.client.post('/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
                                     json={'expected_revision': draft['revision'],
                                           'author': AUTHOR}, headers=self.headers)
        self.assertEqual(no_supply.status_code, 200, no_supply.text)
        self.assertEqual(no_supply.json()['status'], 'blocked')

    def test_client_supplied_sample_is_not_part_of_the_contract(self):
        draft = self.drafted(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        response = self.client.post(
            '/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
            json={'expected_revision': draft['revision'], 'author': AUTHOR,
                  'sample': {'lon': SITE_LON, 'lat': SITE_LAT, 'window_px': 3}},
            headers=self.headers)
        self.assertEqual(response.status_code, 422)
        # 转换请求缺 expected_revision 同样拒
        response = self.client.post(
            '/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
            json={'author': AUTHOR}, headers=self.headers)
        self.assertEqual(response.status_code, 422)

    def test_overlapping_farmland_blocks_the_endpoint(self):
        draft = self.drafted(land_use=[{'kind': 'farmland', 'vertices': FARMLAND},
                                       {'kind': 'farmland', 'vertices': OVERLAP_FARM}])
        self.assertTrue(draft['overlaps'])
        response = self.client.post('/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
                                    json={'expected_revision': draft['revision'],
                                          'author': AUTHOR}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['status'], 'blocked')
        self.assertIn('overlapping_farmland', payload['missing'])
        self.assertIsNone(payload['input'])
        kept = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                               headers=self.headers).json()
        self.assertEqual(kept['revision'], draft['revision'])

    def test_conversion_recomputes_the_sample_and_feeds_the_town_flow(self):
        draft = self.drafted(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        conversion = self.client.get('/api/inner/spatial-drafts/' + draft['id'] + '/conversion',
                                     headers=self.headers)
        self.assertEqual(conversion.status_code, 200)
        self.assertTrue(conversion.json()['ready'], conversion.text)

        response = self.client.post('/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
                                    json={'expected_revision': draft['revision'],
                                          'author': AUTHOR}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        built = response.json()
        self.assertEqual(built['status'], 'ready', built)
        provenance = built['provenance']['spatial_draft']
        self.assertEqual(provenance['draft_id'], draft['id'])
        self.assertEqual(provenance['draft_revision'], draft['revision'])
        self.assertEqual(provenance['mapping_source'], 'author_spatial_draft')
        self.assertEqual(provenance['sample_source'], 'server_recomputed')
        # 地形面积来自已声明农田，不是建筑范围
        terrain = built['input']['terrain']
        self.assertAlmostEqual(terrain['area_km2'], draft['area_plan']['farmland_km2'],
                               places=3)
        self.assertNotAlmostEqual(terrain['area_km2'], draft['footprint']['area_km2'],
                                  places=2)

        # 真的建一份城镇草稿：四阶段生成（不 mock 转换）
        created = self.client.post('/api/inner/towns', json={'input': built['input']},
                                   headers=self.headers)
        self.assertEqual(created.status_code, 200, created.text)
        town = created.json()
        self.assertEqual([stage['name'] for stage in town['stages']],
                         ['skeleton', 'socioeconomy', 'built', 'story'])
        self.assertEqual(town['base_story_revision'], draft['story_base_revision'])
        # 只建草稿：没有发布、没有版本、没有绑定、没有移动指针
        self.assertEqual(town['published'], [])
        versions = self.client.get('/api/inner/town-versions', headers=self.headers).json()
        self.assertEqual(versions, [])

    def test_old_story_revision_is_refused_without_touching_the_draft(self):
        draft = self.drafted(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        runtime = self.service.runtime
        original = runtime.package
        try:
            runtime.package = lambda revision=None: {'id': 'story_rev_moved_0002'}
            response = self.client.post(
                '/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
                json={'expected_revision': draft['revision'], 'author': AUTHOR},
                headers=self.headers)
        finally:
            runtime.package = original
        self.assertEqual(response.status_code, 400)
        self.assertIn('故事包版本', response.json()['detail'])
        kept = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                               headers=self.headers).json()
        self.assertEqual(kept['revision'], draft['revision'])
        self.assertEqual(kept['story_base_revision'], draft['story_base_revision'])

    def test_story_pointer_and_user_data_are_untouched(self):
        before = self.client.get('/api/inner/package', headers=self.headers).json()['id']
        draft = self.drafted(land_use=[{'kind': 'farmland', 'vertices': FARMLAND}])
        self.client.post('/api/inner/spatial-drafts/' + draft['id'] + '/town-input',
                         json={'expected_revision': draft['revision'], 'author': AUTHOR},
                         headers=self.headers)
        after = self.client.get('/api/inner/package', headers=self.headers).json()['id']
        self.assertEqual(after, before)
        self.assertIsNone(self.service.store.get('pointer', 'spatial_draft'))


def _minimal_world():
    """最小可提交的故事+角色（只为本文件里的版本核对提供当前故事）。"""
    axes = {'talent': 50, 'strength': 50, 'agility': 50, 'wisdom': 50,
            'social': 50, 'resilience': 50}
    story = {
        'id': 'spatial-integration-world', 'title': '空间集成夹具', 'premise': '仅测试。',
        'character_package_id': 'spatial-integration-characters',
        'locations': [{'id': 'plaza', 'name': '空场', 'description': '',
                       'neighbors': [], 'scenes': []}],
        'events': [{'id': 'root', 'title': '第一步', 'location_id': 'plaza',
                    'participants': ['player'], 'player_goal': '看看',
                    'player_enters': True, 'next_events': [], 'entry_flags': {},
                    'exit_flag': 'done', 'max_turns': 8,
                    'actions': [{'id': 'look', 'label': '看看', 'ends_event': True,
                                 'success_text': '看了看。'}]}],
        'items': [], 'mechanics': {'local': {'turn_hours': 1, 'travel_hours': 2}},
    }
    characters = {'id': 'spatial-integration-characters', 'title': '夹具角色',
                  'characters': [{'id': 'player', 'name': '我', 'role': '主角',
                                  'location_id': 'plaza', 'personality': {},
                                  'state': {}, 'attributes': dict(axes)}]}
    return story, characters


class SpatialRouteContractTests(unittest.TestCase):
    """The endpoint models themselves: strict, no client sample, no geometry restated."""

    def test_convert_request_has_no_sample_field(self):
        with self.assertRaises(Exception):
            web.SpatialDraftConvertRequest(expected_revision=0, author={'a': 1},
                                           sample={'lon': 1.0})
        request = web.SpatialDraftConvertRequest(expected_revision=0, author={'a': 1})
        self.assertFalse(hasattr(request, 'sample'))

    def test_update_request_requires_a_real_int_revision(self):
        for bad in (True, '0', 1.0):
            with self.assertRaises(Exception):
                web.SpatialDraftUpdateRequest(expected_revision=bad, draft={'site_name': 'x'})
        web.SpatialDraftUpdateRequest(expected_revision=0, draft={'site_name': 'x'})


if __name__ == '__main__':
    unittest.main()
