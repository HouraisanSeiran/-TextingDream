# -*- coding: utf-8 -*-
"""空世界下的作者空间草稿 + civ 城市稳定引用。

两件事，两套断言：

1. **空态**（没有故事包）仍能建、读、CAS 更新空间草稿；草稿的
   ``story_base_revision`` 就是 ``None``，不会造 dummy 故事，也不会在库里冒出 package/session。
   这种草稿**不能**转换（结构化拒绝，不是沉默地绑到后来某个故事）。
2. **city_ref**：只能链接原件里真实存在的 civ 城市实体；不能只给 site_name 冒充城市，
   不能引用另一份原件，不能指向不存在的城市。

fixture 自包含：最小 CASNAP 容器（带一份只有 settlements 的 civ part）。
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

CITY_ID = 'settlement:0'


def _part(payload_structure):
    """把一个纯 JSON 结构封成合法 CIVSNAP1 part（无 typed array，payload 为空）。

    真实原件里的数组是 ``{"$$":"a",...}`` 指向 payload；这里只需要能走通外壳，
    所以每个数组都写成 ``{"$$":"s","v":[...]}``。
    """
    head = json.dumps(payload_structure, ensure_ascii=False).encode('utf-8')
    out = b'CIVSNAP1' + struct.pack('<I', len(head)) + head
    while len(out) % 8:
        out += b'\x00'
    return out


def _container(settlements):
    """拼一个最小 CASNAP01：只带 map + civ 两块。"""
    map_body = json.dumps({'mesh': {'n': 1, 'width': 1, 'height': 1,
                                    'x': [0.0], 'y': [0.0]}},
                          ensure_ascii=False).encode()
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
                    'world': {'id': 'w_city', 'app': 'civ-atlas'},
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


class EmptySpatialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.app = create_app(self.root / 'spatial.sqlite3')
        self.app.state.service.provider.configure({'offline': True})
        self.client = TestClient(self.app)
        boot = self.client.get('/api/bootstrap').json()
        self.headers = {'X-TextileDream-Token': boot['token']}
        self.assertFalse(boot['can_start'])
        self.record, self.data = self.register()

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def register(self):
        data = _container([{'id': 0, 'cell': 0, 'region': 0,
                            'culture': 0, 'name': '灰港', 'founded': -320}])
        digest = hashlib.sha256(data).hexdigest()
        directory = Path(self.app.state.service.store.path).resolve().parent / 'map_imports'
        directory.mkdir(parents=True, exist_ok=True)
        name = '%s.civsnap' % digest[:32]
        (directory / name).write_bytes(data)
        record = {'id': 'sn_' + digest[:12], 'format': civ_atlas_snapshot.FORMAT,
                  'created': '2026-01-01T00:00:00+00:00',
                  'source': {'world_id': 'w_city'}, 'file': name, 'sha256': digest,
                  'bytes': len(data), 'parts': [], 'stats': {}}
        self.app.state.service.store.put('map_import', record['id'], record)
        return record, data

    def body(self, **extra):
        payload = {'site_name': '下坡村',
                   'environment_ref': {'import_id': self.record['id'],
                                       'source_sha256': self.record['sha256']},
                   'footprint': {'vertices': [[0.1, 0.1], [0.11, 0.1], [0.11, 0.11]]}}
        payload.update(extra)
        return payload

    def wrap(self, **extra):
        """请求体是 {draft: {...}}（web 的 SpatialDraftBody）。"""
        return {'draft': self.body(**extra)}

    def test_save_get_and_cas_without_any_world(self):
        draft = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                                 json=self.wrap()).json()['draft']
        self.assertIsNone(draft['story_base_revision'])
        self.assertEqual(draft['revision'], 0)
        fetched = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                                  headers=self.headers).json()
        self.assertEqual(fetched['id'], draft['id'])
        updated = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                  headers=self.headers,
                                  json={**self.wrap(site_name='下坡村二稿'),
                                        'expected_revision': 0}).json()
        self.assertEqual(updated['revision'], 1)
        stale = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                headers=self.headers,
                                json={**self.wrap(), 'expected_revision': 0})
        self.assertEqual(stale.status_code, 400)
        store = self.app.state.service.store
        self.assertEqual(store.all('package'), [])
        self.assertEqual(store.all('session'), [])
        self.assertFalse(self.app.state.service.runtime.has_world())

    def test_null_draft_cannot_be_converted(self):
        draft = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                                 json=self.wrap(sampling={'lon': 10.0, 'lat': 20.0})
                                 ).json()['draft']
        report = self.client.get('/api/inner/spatial-drafts/%s/conversion' % draft['id'],
                                 headers=self.headers).json()
        self.assertFalse(report['ready'])
        self.assertIn('story_base_revision_missing', report['missing'])

    def test_city_ref_links_a_real_settlement(self):
        city = {'import_id': self.record['id'], 'source_sha256': self.record['sha256'],
                'city_id': CITY_ID}
        draft = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                                 json=self.wrap(city_ref=city)).json()['draft']
        resolved = draft['city_ref']
        self.assertEqual(resolved['city_id'], CITY_ID)
        self.assertEqual(resolved['name'], '灰港')
        self.assertEqual(resolved['region'], 0)
        self.assertEqual(resolved['identity_verified'], 'snapshot_civ')
        self.assertNotEqual(resolved['name'], draft['site_name'])

    def test_city_ref_without_id_is_refused(self):
        res = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                               json=self.wrap(city_ref={'import_id': self.record['id'],
                                                        'source_sha256': self.record['sha256']}))
        self.assertEqual(res.status_code, 400)
        self.assertIn('settlement:', res.json()['detail'])

    def test_city_ref_to_another_source_is_refused(self):
        res = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                               json=self.wrap(city_ref={'import_id': self.record['id'],
                                                        'source_sha256': 'e' * 64,
                                                        'city_id': CITY_ID}))
        self.assertEqual(res.status_code, 400)
        self.assertIn('同一份原件', res.json()['detail'])

    def test_city_ref_to_missing_settlement_is_refused(self):
        res = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                               json=self.wrap(city_ref={'import_id': self.record['id'],
                                                        'source_sha256': self.record['sha256'],
                                                        'city_id': 'settlement:nope'}))
        self.assertEqual(res.status_code, 400)
        self.assertIn('settlement:', res.json()['detail'])

    def test_detail_round_trips_note_and_city_ref(self):
        """GET 回来能直接 PUT 回去：note/city_ref 不丢、不需要派生值。"""
        city = {'import_id': self.record['id'], 'source_sha256': self.record['sha256'],
                'city_id': CITY_ID}
        draft = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                                 json=self.wrap(note='作者备注', city_ref=city)).json()['draft']
        detail = self.client.get('/api/inner/spatial-drafts/' + draft['id'],
                                 headers=self.headers).json()
        self.assertEqual(detail['note'], '作者备注')
        self.assertEqual(detail['city_ref']['city_id'], CITY_ID)
        # 请求只带三键（不带派生 name/region），PUT 必须能原样收下。
        listing = self.client.get('/api/inner/spatial-drafts',
                                  headers=self.headers).json()
        self.assertEqual(listing[0]['note'], '作者备注')
        self.assertEqual(listing[0]['city_ref']['city_id'], CITY_ID)
        updated = self.client.put('/api/inner/spatial-drafts/' + draft['id'],
                                  headers=self.headers,
                                  json={**self.wrap(note='作者备注', city_ref={
                                      'import_id': self.record['id'],
                                      'source_sha256': self.record['sha256'],
                                      'city_id': CITY_ID}),
                                      'expected_revision': detail['revision']}).json()
        self.assertEqual(updated['note'], '作者备注')
        self.assertEqual(updated['city_ref']['name'], '灰港')

    def test_tampered_original_never_verifies_city(self):
        """磁盘字节与记录哈希不符时，city_ref 必须在拿到身份前就被拒。"""
        record = dict(self.record)
        path = Path(self.app.state.service.store.path).resolve().parent / "map_imports" / record["file"]
        path.write_bytes(path.read_bytes() + b"\x00")   # 原件被改过一个字节
        res = self.client.post("/api/inner/spatial-drafts", headers=self.headers,
                               json=self.wrap(city_ref={"import_id": record["id"],
                                                        "source_sha256": record["sha256"],
                                                        "city_id": CITY_ID}))
        self.assertEqual(res.status_code, 400)
        self.assertIn("原件", res.json()["detail"])
        # 绝不能出现一个“已验证”的 city_ref。
        drafts = self.app.state.service.store.all("spatial_draft")
        self.assertEqual(drafts, [])

    def test_record_file_outside_map_imports_is_refused(self):
        """record.file 被改成越界路径时，不读任何文件、也不给城市身份。"""
        service = self.app.state.service
        record = dict(self.record)
        record["file"] = "../outside.civsnap"
        (self.root / "outside.civsnap").write_bytes(self.data)
        service.store.put("map_import", record["id"], record)
        res = self.client.post("/api/inner/spatial-drafts", headers=self.headers,
                               json=self.wrap(city_ref={"import_id": record["id"],
                                                        "source_sha256": record["sha256"],
                                                        "city_id": CITY_ID}))
        self.assertEqual(res.status_code, 400)
        self.assertIn("原件", res.json()["detail"])
        self.assertEqual(service.store.all("spatial_draft"), [])

    def test_city_ref_without_environment_is_refused(self):
        payload = {'site_name': '下坡村',
                   'footprint': {'vertices': [[0.1, 0.1], [0.11, 0.1], [0.11, 0.11]]},
                   'city_ref': {'import_id': self.record['id'],
                                'source_sha256': self.record['sha256'],
                                'city_id': CITY_ID}}
        res = self.client.post('/api/inner/spatial-drafts', headers=self.headers,
                               json={'draft': payload})
        self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
