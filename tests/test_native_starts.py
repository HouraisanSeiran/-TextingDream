# -*- coding: utf-8 -*-
"""从 civ 地图 + 选定历史创建首个故事（空库 → 可 new_session）。

fixture 自含：最小 CASNAP01（map + civ），城市 id 用真实整数（上游口径）。
覆盖：预览、候选、确认、CAS/幂等、以及各类失配拒绝。
"""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import civ_atlas_snapshot
from app.web import create_app

CITY = 0
CITY_ID = 'settlement:0'


def _part(structure):
    head = json.dumps(structure, ensure_ascii=False).encode('utf-8')
    out = b'CIVSNAP1' + struct.pack('<I', len(head)) + head
    while len(out) % 8:
        out += b'\x00'
    return out


def _container(settlements):
    mesh = {'n': 1, 'width': 1, 'height': 1, 'x': [0.0], 'y': [0.0]}
    map_body = _part({'mesh': {'$$': 'o', 'v': mesh}})
    civ_body = _part({'settlements': {'$$': 's', 'v': settlements},
                      'annals': {'$$': 's', 'v': []},
                      'polities': {'$$': 's', 'v': []},
                      'people': {'$$': 's', 'v': []},
                      'regions': {'$$': 'o', 'v': {'count': 1}}})
    blobs = [{'name': 'map', 'data': map_body}, {'name': 'civ', 'data': civ_body}]

    def build(offsets):
        manifest = {'container': 'CASNAP01', 'schema': 1,
                    'exported_at': '2026-01-01T00:00:00+00:00',
                    'exported_by': {'name': 'test'},
                    'world': {'id': 'w_start', 'app': 'civ-atlas'},
                    'snapshot': {'generator': 1, 'format': 'world-v1', 'recipe': 'test'},
                    'parts': []}
        for index, part in enumerate(blobs):
            manifest['parts'].append({'name': part['name'], 'bytes': len(part['data']),
                                      'length': len(part['data']), 'zip': None,
                                      'offset': '%012d' % offsets[index]})
        head = json.dumps(manifest, ensure_ascii=False).encode('utf-8')
        prefix = b'CASNAP01' + struct.pack('<I', len(head)) + head
        while len(prefix) % 8:
            prefix += b'\x00'
        return prefix

    offsets = []
    prefix = build([0] * len(blobs))
    cursor = len(prefix)
    for part in blobs:
        offsets.append(cursor)
        cursor += len(part['data'])
        while cursor % 8:
            cursor += 1
    prefix = build(offsets)
    body = b''
    for part in blobs:
        body += part['data']
        while (len(prefix) + len(body)) % 8:
            body += b'\x00'
    return prefix + body


class NativeStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'app' / 'static').mkdir(parents=True)
        (self.root / 'assets' / 'maps').mkdir(parents=True)
        self.app = create_app(self.root / 's.sqlite3')
        self.app.state.service.provider.configure({'offline': True})
        self.client = TestClient(self.app)
        boot = self.client.get('/api/bootstrap').json()
        self.headers = {'X-TextileDream-Token': boot['token']}
        self.assertFalse(boot['can_start'])
        self.service = self.app.state.service
        self.register()

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def register(self, settlements=None):
        settlements = settlements or [
            {'id': CITY, 'cell': 0, 'region': 0, 'culture': 0,
             'name': '灰港', 'founded': 10.0},
            {'id': 1, 'cell': 0, 'region': 0, 'culture': 0,
             'name': '未来城', 'founded': 900.0},
        ]
        data = _container(settlements)
        digest = hashlib.sha256(data).hexdigest()
        directory = Path(self.service.store.path).resolve().parent / 'map_imports'
        directory.mkdir(parents=True, exist_ok=True)
        name = '%s.civsnap' % digest[:32]
        (directory / name).write_bytes(data)
        record = {'id': 'sn_' + digest[:12], 'format': civ_atlas_snapshot.FORMAT,
                  'created': '2026-01-01T00:00:00+00:00',
                  'source': {'world_id': 'w_start'}, 'file': name, 'sha256': digest,
                  'bytes': len(data), 'parts': [], 'stats': {}}
        self.service.store.put('map_import', record['id'], record)
        self.record = record
        return record

    def draft(self, **over):
        payload = {'import_id': self.record['id'],
                   'source_sha256': self.record['sha256'],
                   'world_id': 'w_start', 'branch': 'main', 'base_year': 100.0,
                   'city_id': CITY_ID, 'title': '灰港的冬天', 'premise': '港口结了冰。'}
        payload.update(over)
        return {'draft': payload}

    # ------------------------------------------------------------------ 预览
    def test_preview_lists_only_cities_alive_at_that_year(self):
        res = self.client.get('/api/inner/native-starts/%s/preview' % self.record['id'],
                              params={'base_year': 100}, headers=self.headers)
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual([row['city_id'] for row in body['settlements']], [CITY_ID])
        self.assertNotIn('未来城', json.dumps(body, ensure_ascii=False))
        self.assertEqual(body['travel'], 'unavailable_no_road_data')
        # 坐标由真实 cell 投影（本 fixture 的单格世界）
        self.assertIsNotNone(body['settlements'][0]['position'])

    def test_candidate_creates_no_package_pointer_or_session(self):
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft())
        self.assertEqual(res.status_code, 200, res.text)
        draft = res.json()['draft']
        self.assertEqual(draft['status'], 'candidate')
        store = self.service.store
        self.assertEqual(store.all('package'), [])
        self.assertIsNone(store.get('pointer', 'package'))
        self.assertEqual(store.all('session'), [])

    def test_city_must_exist_at_that_year(self):
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft(city_id='settlement:1'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('不存在', res.json()['detail'])
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft(city_id='settlement:99'))
        self.assertEqual(res.status_code, 400)

    def test_start_cell_must_be_the_city_cell(self):
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft(start_cell=7))
        self.assertEqual(res.status_code, 400)
        self.assertIn('cell', res.json()['detail'])

    def test_source_mismatch_is_refused(self):
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft(source_sha256='e' * 64))
        self.assertEqual(res.status_code, 400)
        res = self.client.post('/api/inner/native-starts', headers=self.headers,
                               json=self.draft(world_id='other'))
        self.assertEqual(res.status_code, 400)

    # ------------------------------------------------------------------ 确认
    def test_confirm_builds_one_package_and_enables_new_session(self):
        draft = self.client.post('/api/inner/native-starts', headers=self.headers,
                                 json=self.draft()).json()['draft']
        res = self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                               headers=self.headers, json={'expected_revision': 0})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()['created'])
        self.assertTrue(self.service.runtime.has_world())
        self.assertTrue(self.client.get('/api/bootstrap').json()['can_start'])
        session = self.client.post('/api/sessions', headers=self.headers,
                                   json={'title': '第一段旅程'}).json()
        self.assertIn('id', session)

    def test_second_confirm_returns_same_revision(self):
        draft = self.client.post('/api/inner/native-starts', headers=self.headers,
                                 json=self.draft()).json()['draft']
        first = self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                                 headers=self.headers, json={'expected_revision': 0}).json()
        second = self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                                  headers=self.headers, json={'expected_revision': 0}).json()
        self.assertEqual(second['revision'], first['revision'])
        self.assertFalse(second['created'])
        self.assertEqual(len(self.service.store.all('package')), 1)

    def test_stale_expected_revision_builds_nothing(self):
        draft = self.client.post('/api/inner/native-starts', headers=self.headers,
                                 json=self.draft()).json()['draft']
        res = self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                               headers=self.headers, json={'expected_revision': 5})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.service.store.all('package'), [])
        self.assertFalse(self.service.runtime.has_world())

    def test_first_package_has_real_coordinates_and_no_roads(self):
        draft = self.client.post('/api/inner/native-starts', headers=self.headers,
                                 json=self.draft()).json()['draft']
        self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                         headers=self.headers, json={'expected_revision': 0})
        story = self.service.runtime.package()['story']
        for place in story['locations']:
            self.assertEqual(place['neighbors'], [])      # 没有合法路资料：不造路
            self.assertIn('coordinates', place)            # 真实 cell 投影
            self.assertEqual(place['civ_ref']['position_source'], 'snapshot_mesh_cell')
        self.assertEqual(story['mechanics']['map']['import_id'], self.record['id'])


if __name__ == '__main__':
    unittest.main()
