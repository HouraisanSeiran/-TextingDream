# -*- coding: utf-8 -*-
"""无预制故事的空世界启动（临时根 + 临时库）。

用户已删光旧故事包与旅程存档，所以启动不能再靠“自动复制玄陆”活着。这里验证：

* 空根 + 空库能建出 app，`/api/bootstrap` 返回明确的空态而不是假世界；
* 设置/API 配置/百科/地图导入入口仍可用（不依赖世界）；
* 新建旅程给出可操作拒绝，而不是 500 或造一个隐藏默认故事；
* 两次重启不会把旧目录重建回来；
* 世界里第一次被创建+采纳之后才能开局（用最小手动提交验证，不伪造 civ 生成端点）。
"""
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.service import Service
from app.storage import Store
from app.web import create_app


class EmptyWorldStartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def client(self):
        return TestClient(create_app(self.root / 'empty.sqlite3'))

    def head(self, client):
        boot = client.get('/api/bootstrap').json()
        return boot, {'X-TextileDream-Token': boot['token']}

    def test_startup_with_no_package_at_all(self):
        with self.client() as client:
            boot, headers = self.head(client)
            # 明确的空态：没有世界、不能开局、有可读原因。
            self.assertIsNone(boot['world'])
            self.assertEqual(boot['packages'], [])
            self.assertFalse(boot['can_start'])
            self.assertIn('还没有可用的世界', boot['world_reason'])
            self.assertEqual(boot['sessions'], [])
            # 独立于世界的入口仍然在。
            self.assertIn('api', boot)
            self.assertEqual(client.get('/api/settings/api', headers=headers).status_code, 200)
            self.assertEqual(client.get('/api/inner/corpus', headers=headers).status_code, 200)
            self.assertEqual(client.get('/api/inner/history/imports',
                                        headers=headers).status_code, 200)
            imports = client.get('/api/inner/history/imports', headers=headers).json()
            self.assertIsNone(imports['story_revision'])   # 空态下就是 null
            self.assertIsNone(imports['story_id'])

    def test_new_session_is_refused_with_a_reason(self):
        with self.client() as client:
            boot, headers = self.head(client)
            res = client.post('/api/sessions', headers=headers,
                              json={'title': '空世界', 'mode': 'protagonist'})
            self.assertEqual(res.status_code, 400)
            self.assertIn('还没有可用的世界', res.json()['detail'])
            # 被拒之后也没有偷偷多出一个旅程。
            self.assertEqual(client.get('/api/bootstrap').json()['sessions'], [])

    def test_restart_does_not_recreate_old_directories(self):
        with self.client() as client:
            self.head(client)
        library = self.root / 'StoryPackage'
        self.assertTrue(library.exists())
        self.assertEqual([p.name for p in library.iterdir() if p.is_dir()], [])
        # 第二次启动（同一个库）仍然没有世界，也不会凭空造出玄陆。
        with self.client() as client:
            boot, _ = self.head(client)
            self.assertFalse(boot['can_start'])
        self.assertEqual([p.name for p in library.iterdir() if p.is_dir()], [])
        self.assertFalse((self.root / 'world_packages').exists())

    def test_journey_becomes_possible_only_after_a_world_is_adopted(self):
        with self.client() as client:
            boot, headers = self.head(client)
            self.assertFalse(boot['can_start'])
            # 作者显式提交一个最小世界（真实 commit_package，不是伪造生成端点）。
            service = client.app.state.service
            service.runtime.commit_package(_story(), _characters(), '采纳世界')
            boot = client.get('/api/bootstrap').json()
            self.assertIsNotNone(boot['world'])
            self.assertTrue(boot['can_start'])
            res = client.post('/api/sessions', headers=headers,
                              json={'title': '第一段旅程', 'mode': 'protagonist'})
            self.assertEqual(res.status_code, 200, res.text)
            self.assertEqual(len(client.get('/api/bootstrap').json()['sessions']), 1)

    def test_service_alone_can_start_empty(self):
        service = Service(Store(self.root / 'svc.sqlite3'), self.root)
        self.assertFalse(service.runtime.has_world())
        self.assertIsNone(service.runtime.empty_state()['world'])
        with self.assertRaises(ValueError) as caught:
            service.runtime.new_session('空世界', 'protagonist')
        self.assertIn('还没有可用的世界', str(caught.exception))
        with self.assertRaises(ValueError):
            service.runtime.package()


def _story():
    return {
        'id': 'empty-test', 'title': '最小世界', 'premise': '只有必要字段的世界。',
        'character_package_id': 'empty-test-characters',
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


def _characters():
    axes = {'talent': 50, 'strength': 50, 'agility': 50, 'wisdom': 50,
            'social': 50, 'resilience': 50}
    return {'id': 'empty-test-characters', 'title': '最小角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {}, 'state': {}, 'attributes': dict(axes)}]}


if __name__ == '__main__':
    unittest.main()
