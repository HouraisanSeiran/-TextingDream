# -*- coding: utf-8 -*-
"""原生宿主前端产物托管：`/native-map/*` 与缺构建的 503。

不启动服务、不装依赖、不读生产 data：用临时库 + 临时构建目录，只验证托管契约。
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.web import create_app


class NativeMapStaticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # create_app 会挂载旧壳静态目录；这里建空目录即可（本测试不请求旧壳页面）。
        (self.root / 'app' / 'static').mkdir(parents=True)
        (self.root / 'assets' / 'maps').mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _client(self):
        return TestClient(create_app(self.root / 'native.sqlite3'))

    def test_built_dist_is_served_under_native_map(self):
        dist = self.root / 'external' / 'civ-atlas' / 'dist-dream'
        (dist / 'fonts').mkdir(parents=True)
        (dist / 'dream-host.js').write_text('/* host bundle */', encoding='utf-8')
        (dist / 'dream-host.css').write_text('body{color:#000}', encoding='utf-8')
        (dist / 'fonts' / 'x.woff2').write_bytes(b'\x00\x01')
        with patch('app.web.ROOT', self.root):
            with self._client() as client:
                js = client.get('/native-map/dream-host.js')
                self.assertEqual(js.status_code, 200)
                self.assertIn('host bundle', js.text)
                css = client.get('/native-map/dream-host.css')
                self.assertEqual(css.status_code, 200)
                self.assertIn('color', css.text)
                # 相对资源（字体）也在同一前缀下可取到。
                self.assertEqual(client.get('/native-map/fonts/x.woff2').status_code, 200)
                # 不能靠 /static 遮蔽到这个前缀。
                self.assertNotEqual(client.get('/static/dream-host.js').status_code, 200)

    def test_missing_build_gives_actionable_503(self):
        with patch('app.web.ROOT', self.root):
            with self._client() as client:
                for path in ('/native-map/dream-host.js', '/native-map/dream-host.css'):
                    res = client.get(path)
                    self.assertEqual(res.status_code, 503)
                    self.assertIn('还没有构建', res.json()['detail'])
                # 其它入口照常可用（缺前端产物不影响后端）。
                self.assertEqual(client.get('/api/bootstrap').status_code, 200)


if __name__ == '__main__':
    unittest.main()
