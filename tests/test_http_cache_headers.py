# -*- coding: utf-8 -*-
"""Static assets are cacheable and compressed; live API/HTML responses are not."""
import pathlib
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.web import create_app


class CacheAndCompressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        db = pathlib.Path(self.tmp.name) / 'probe.sqlite3'
        self.client = TestClient(create_app(str(db)))

    def test_static_asset_is_revalidated_not_forbidden_from_cache(self):
        response = self.client.get('/static/style.css')
        self.assertEqual(response.status_code, 200)
        cache = response.headers.get('cache-control', '')
        self.assertNotIn('no-store', cache)
        self.assertIn('must-revalidate', cache)
        self.assertTrue(response.headers.get('etag'))

    def test_conditional_static_request_returns_304(self):
        first = self.client.get('/static/style.css')
        second = self.client.get('/static/style.css',
                                  headers={'If-None-Match': first.headers['etag']})
        self.assertEqual(second.status_code, 304)
        self.assertNotIn('no-store', second.headers.get('cache-control', ''))

    def test_live_html_and_api_are_never_stored(self):
        for url in ('/', '/api/bootstrap'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.headers.get('cache-control'), 'no-store', url)

    def test_text_assets_are_gzipped_when_accepted(self):
        response = self.client.get('/static/style.css',
                                   headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('content-encoding'), 'gzip')
        self.assertIn('Accept-Encoding', response.headers.get('vary', ''))


if __name__ == '__main__':
    unittest.main()
