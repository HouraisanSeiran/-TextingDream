# -*- coding: utf-8 -*-
"""HTTP surface for the geography + encyclopedia story-package pipeline.

The full pipeline is covered by ``tests/test_world_package_pipeline.py`` with a fake
source. These tests only prove the author routes are mounted, token-protected and do not
require a .civsnap just to list an empty library.
"""
import pathlib
import tempfile
import unittest

from fastapi.testclient import TestClient

from tests.fixtures_world import world_app


class WorldPackageHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = world_app(pathlib.Path(self.tmp.name) / 'world-package.sqlite3')
        self.client = TestClient(self.app)
        self.headers = {'X-TextileDream-Token':
                        self.client.get('/api/bootstrap').json()['token']}

    def test_routes_require_the_author_token(self):
        for url in ('/api/inner/world-package/imports',
                    '/api/inner/world-package/drafts'):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_empty_import_library_is_a_normal_empty_state(self):
        response = self.client.get('/api/inner/world-package/imports', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'imports': []})
        drafts = self.client.get('/api/inner/world-package/drafts', headers=self.headers)
        self.assertEqual(drafts.status_code, 200)
        self.assertEqual(drafts.json(), [])

    def test_regions_without_a_civsnap_are_a_clear_400(self):
        response = self.client.get('/api/inner/world-package/regions', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('civ-atlas', response.json()['detail'])

    def test_unknown_draft_is_404(self):
        response = self.client.get('/api/inner/world-package/drafts/missing',
                                   headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('不存在', response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
