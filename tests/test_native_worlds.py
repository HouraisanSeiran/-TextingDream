# -*- coding: utf-8 -*-
"""原生宿主（civ-atlas CASNAP01）只读数据桥：

这里验证“交出去的东西对得上”：

* 空世界里列表为空（不报错）；
* 无 token 403；
* 登记的 CASNAP 能在列表/详情里看到，`/snapshot` 返回的字节与磁盘**逐字节相等**；
* `identity.sha256` 是完整 64 hex（spatial 的 source_sha256 要用）；列表只给前 16；
* 记录被篡改哈希 → 拒；未知 id → 拒；记录里的文件名被改成越界路径 → 拒；
* 调用不会改故事/旅程；
* 伪 `X-Dream-Mode` 不能把玩家路由升级成读原件。

容器 fixture 是本文件自己拼的最小 CASNAP01（只用于走通外壳，不代表上游全部语义）。
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


def container(parts=None, world_id='w_test'):
    """拼一个最小合法的 CASNAP01（外壳 + offset 对齐的 parts）。

    头部长度会影响 offset（offset 相对 body 起点），所以要先算两遍：
    先把 offset 写成占位，再按真实长度修正。
    """
    parts = parts if parts is not None else [
        {'name': 'world', 'data': json.dumps({'cells': 2, 'elevation': [1, 2]}).encode()},
    ]

    def build(offsets):
        manifest = {'container': 'CASNAP01', 'schema': 1,
                    'exported_at': '2026-01-01T00:00:00+00:00',
                    'exported_by': {'name': 'test'},
                    'world': {'id': world_id, 'app': 'civ-atlas'},
                    'snapshot': {'generator': 1, 'format': 'world-v1', 'recipe': 'test'},
                    'parts': []}
        for index, part in enumerate(parts):
            blob = part['data']
            manifest['parts'].append({'name': part['name'], 'bytes': len(blob),
                                      'length': len(blob), 'zip': None,
                                      'offset': '%012d' % offsets[index]})
        head = json.dumps(manifest, ensure_ascii=False).encode('utf-8')
        prefix = b'CASNAP01' + struct.pack('<I', len(head)) + head
        while len(prefix) % 8:
            prefix += b'\x00'
        return prefix, manifest

    guess = [0] * len(parts)
    prefix, _ = build(guess)
    offsets = []
    cursor = len(prefix)
    for part in parts:
        offsets.append(cursor)
        blob = part['data']
        cursor += len(blob)
        while cursor % 8:
            cursor += 1
    prefix, _ = build(offsets)
    body = b''
    for part in parts:
        body += part['data']
        while (len(prefix) + len(body)) % 8:
            body += b'\x00'
    return prefix + body


class NativeWorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.app = create_app(self.root / 'native.sqlite3')
        self.app.state.service.provider.configure({'offline': True})
        self.client = TestClient(self.app)
        # 静态目录只为 create_app 挂载需要；本测试不请求页面。
        boot = self.client.get('/api/bootstrap').json()
        self.headers = {'X-TextileDream-Token': boot['token']}

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    # ------------------------------------------------------------- 帮手
    def register(self, data=None, sha_override=None, file_override=None):
        """直接把一份 CASNAP01 登记进 map_import（不走 HTTP 上传）。"""
        data = data if data is not None else container()
        digest = hashlib.sha256(data).hexdigest()
        directory = Path(self.app.state.service.store.path).resolve().parent / 'map_imports'
        directory.mkdir(parents=True, exist_ok=True)
        name = file_override or ('%s.civsnap' % digest[:32])
        (directory / name).write_bytes(data)
        record = {'id': 'sn_' + digest[:12], 'format': civ_atlas_snapshot.FORMAT,
                  'created': '2026-01-01T00:00:00+00:00',
                  'source': {'world_id': 'w_test', 'world_app': 'civ-atlas',
                             'snapshot_format': 'world-v1', 'generator_version': 1,
                             'exported_at': '2026-01-01T00:00:00+00:00',
                             'extractor': 'test', 'spec_commit': 'abc',
                             'license': 'test'},
                  'file': name,
                  'sha256': sha_override or digest,
                  'bytes': len(data),
                  'parts': [{'name': p['name'], 'bytes': p['bytes'], 'zip': p.get('zip'),
                             'length': p['length'], 'sum': 'd' * 64,
                             'sum_verified_by': 'server'}
                            for p in civ_atlas_snapshot.parse_container(data)[0]['parts']],
                  'stats': {'cells': 2}, 'warnings': []}
        self.app.state.service.store.put('map_import', record['id'], record)
        return record, data

    # ------------------------------------------------------------- 用例
    def test_empty_world_lists_nothing(self):
        res = self.client.get('/api/inner/native-worlds', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_without_token_is_forbidden(self):
        self.assertEqual(self.client.get('/api/inner/native-worlds').status_code, 403)
        record, _ = self.register()
        self.assertEqual(self.client.get('/api/inner/native-worlds/' + record['id'])
                         .status_code, 403)
        self.assertEqual(self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'])
                         .status_code, 403)

    def test_tampered_record_hash_is_refused(self):
        record, _ = self.register(sha_override='0' * 64)
        res = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                              headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn('校验失败', res.json()['detail'])
        # metadata 本身仍可看；只有字节被拒。
        self.assertEqual(self.client.get('/api/inner/native-worlds/' + record['id'],
                                         headers=self.headers).status_code, 200)

    def test_registered_snapshot_metadata_and_exact_bytes(self):
        record, data = self.register()
        rows = self.client.get('/api/inner/native-worlds', headers=self.headers).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['import_id'], record['id'])
        # 列表形状就是约定的 ``sha256``，但值是短值（前 16）用于显示。
        self.assertEqual(rows[0]['sha256'], record['sha256'][:16])
        self.assertEqual(len(rows[0]['sha256']), 16)
        self.assertEqual(rows[0]['parts'][0]['name'], 'world')
        detail = self.client.get('/api/inner/native-worlds/' + record['id'],
                                 headers=self.headers).json()
        # identity 里的 sha256 必须是**完整 64 位十六进制**（spatial 的 source_sha256 用）。
        self.assertEqual(detail['identity']['sha256'], record['sha256'])
        self.assertEqual(len(detail['identity']['sha256']), 64)
        self.assertIsNone(detail['story_revision'])      # 空世界：没有故事版本
        self.assertIsNone(detail['story_id'])
        self.assertTrue(detail['available'])
        body = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                               headers=self.headers)
        self.assertEqual(body.status_code, 200)
        self.assertEqual(body.content, data)              # 逐字节相等
        self.assertEqual(body.headers['content-type'], 'application/octet-stream')

    def test_unrelated_world_does_not_claim_this_snapshot(self):
        """当前故事没把这条快照当世界基础时，story_revision/story_id 必须是 null。"""
        record, _ = self.register()
        service = self.app.state.service
        story, characters = _minimal_story(), _minimal_characters()
        # 故事声明了 map，但指向另一个 import_id。
        story['mechanics']['map'] = {'kind': 'civ_atlas', 'import_id': 'sn_' + 'f' * 12}
        service.runtime.commit_package(story, characters, '无关世界')
        self.assertTrue(service.runtime.has_world())
        detail = self.client.get('/api/inner/native-worlds/' + record['id'],
                                 headers=self.headers).json()
        self.assertIsNone(detail['story_revision'])
        self.assertIsNone(detail['story_id'])

    def test_linked_world_reports_the_revision_only_when_it_matches(self):
        record, _ = self.register()
        service = self.app.state.service
        story, characters = _minimal_story(), _minimal_characters()
        story['mechanics']['map'] = {'kind': 'civ_atlas', 'import_id': record['id']}
        revision = service.runtime.commit_package(story, characters, '关联世界')
        detail = self.client.get('/api/inner/native-worlds/' + record['id'],
                                 headers=self.headers).json()
        self.assertEqual(detail['story_revision'], revision)
        self.assertEqual(detail['story_id'], story['id'])

    def test_missing_original_reports_unavailable(self):
        record, data = self.register()
        path = Path(self.app.state.service.store.path).resolve().parent / 'map_imports' / record['file']
        path.unlink()
        detail = self.client.get('/api/inner/native-worlds/' + record['id'],
                                 headers=self.headers).json()
        self.assertFalse(detail['available'])          # 元数据仍可看，但原件确实不在
        res = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                              headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn('已不在', res.json()['detail'])
        self.assertEqual(self.client.get('/api/inner/native-worlds/' + record['id'],
                                         headers=self.headers).status_code, 200)

    def test_unknown_id_and_bad_format(self):
        self.assertEqual(self.client.get('/api/inner/native-worlds/sn_' + 'a' * 12,
                                         headers=self.headers).status_code, 400)
        self.assertEqual(self.client.get('/api/inner/native-worlds/nonsense',
                                         headers=self.headers).status_code, 400)
        # 高度图导入（非 CASNAP）不属于这个桥。
        self.app.state.service.store.put('map_import', 'mi_abcdef123456', {
            'id': 'mi_abcdef123456', 'format': 'heightmap_png_v1', 'file': 'x.png'})
        res = self.client.get('/api/inner/native-worlds/mi_abcdef123456',
                              headers=self.headers).json()
        self.assertIn('不是原生快照', res['detail'])
        self.assertEqual(self.client.get('/api/inner/native-worlds', headers=self.headers)
                         .json(), [])                                  # 列表也不列它

    def test_path_traversal_in_record_is_refused(self):
        record, _ = self.register(file_override='../outside.civsnap')
        res = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                              headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn('不合法', res.json()['detail'])

    def test_reads_do_not_touch_stories_or_sessions(self):
        record, _ = self.register()
        store = self.app.state.service.store
        before = (len(store.all('session')), len(store.all('package')),
                  store.get('pointer', 'package'))
        for path in ('/api/inner/native-worlds',
                     '/api/inner/native-worlds/' + record['id'],
                     '/api/inner/native-worlds/%s/snapshot' % record['id']):
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 200)
        after = (len(store.all('session')), len(store.all('package')),
                 store.get('pointer', 'package'))
        self.assertEqual(before, after)

    def test_player_cannot_upgrade_by_mode_header(self):
        record, data = self.register()
        # 没有 token 时，任何“模式”头都无效。
        for value in ('player', 'author', 'native', 'admin'):
            res = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                                  headers={'X-Dream-Mode': value})
            self.assertEqual(res.status_code, 403)
            self.assertNotEqual(res.content, data)

    def test_bytes_survive_a_second_read(self):
        record, data = self.register()
        first = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                                headers=self.headers).content
        second = self.client.get('/api/inner/native-worlds/%s/snapshot' % record['id'],
                                 headers=self.headers).content
        self.assertEqual(first, data)
        self.assertEqual(second, data)


def _minimal_story():
    """最小的合法故事包（用于测“当前世界是否真的指向这条快照”）。"""
    return {
        'id': 'native-linked', 'title': '关联世界', 'premise': '只是夹具。',
        'character_package_id': 'native-linked-characters',
        'locations': [{'id': 'plaza', 'name': '空场', 'description': '',
                       'neighbors': [], 'scenes': []}],
        'events': [{'id': 'root', 'title': '第一步', 'location_id': 'plaza',
                    'participants': ['player'], 'player_goal': '看看',
                    'player_enters': True, 'next_events': [], 'entry_flags': {},
                    'exit_flag': 'done', 'max_turns': 8,
                    'actions': [{'id': 'look', 'label': '看看', 'ends_event': True,
                                 'success_text': '看了看。'}]}],
        'items': [],
        'mechanics': {'local': {'turn_hours': 1, 'travel_hours': 2}},
    }


def _minimal_characters():
    axes = {'talent': 50, 'strength': 50, 'agility': 50, 'wisdom': 50,
            'social': 50, 'resilience': 50}
    return {'id': 'native-linked-characters', 'title': '夹具角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {}, 'state': {}, 'attributes': dict(axes)}]}


if __name__ == '__main__':
    unittest.main()
