import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.provider import Provider
from app.storage import Store
from app.web import create_app


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.provider = Provider(Store(Path(self.tmp.name) / 'test.sqlite3'))
        self.provider.key = ''

    def transport(self, handler):
        original = httpx.AsyncClient
        return patch('app.provider.httpx.AsyncClient', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw))

    def test_three_fields_discover_model_and_generate_openai(self):
        def respond(request):
            self.assertEqual(request.headers['authorization'], 'Bearer test-key')
            if request.method == 'GET':
                self.assertEqual(request.url.path, '/v1/models')
                return httpx.Response(200, json={'data': [{'id': 'text-embedding-test'}, {'id': 'chat-test'}]})
            self.assertEqual(request.url.path, '/v1/chat/completions')
            self.assertEqual(json.loads(request.content)['model'], 'chat-test')
            return httpx.Response(200, json={'choices': [{'message': {'content': '连接成功'}}], 'usage': {'prompt_tokens': 5}})
        with self.transport(respond):
            cfg = asyncio.run(self.provider.connect('https://example.com/v1/chat/completions', 'openai', 'test-key'))
            self.assertEqual(cfg['model'], 'chat-test')
            self.assertFalse(cfg['offline'])
            self.assertNotIn('api_key', cfg)
            self.assertEqual(asyncio.run(self.provider.complete('hello', {}))[0], '连接成功')
        self.assertNotIn('test-key', json.dumps(self.provider.store.get('settings', 'api')))

    def test_anthropic_headers_json_response_and_usage(self):
        def respond(request):
            self.assertEqual(request.headers['x-api-key'], 'test-anthropic')
            self.assertEqual(request.headers['anthropic-version'], '2023-06-01')
            self.assertNotIn('authorization', request.headers)
            if request.method == 'GET':
                self.assertEqual(request.url.path, '/v1/models')
                return httpx.Response(200, json={'data': [{'id': 'claude-test'}]})
            self.assertEqual(request.url.path, '/v1/messages')
            payload = json.loads(request.content)
            self.assertIn('JSON', payload['system'])
            self.assertEqual(payload['messages'][0]['role'], 'user')
            self.assertNotIn('response_format', payload)
            return httpx.Response(200, json={'content': [{'type': 'thinking', 'thinking': 'hidden'}, {'type': 'text', 'text': '{"ok":true}'}],
                'stop_reason': 'end_turn', 'usage': {'input_tokens': 3, 'output_tokens': 4, 'cache_read_input_tokens': 8, 'cache_creation_input_tokens': 2}})
        with self.transport(respond):
            asyncio.run(self.provider.connect('https://api.anthropic.com', 'anthropic', 'test-anthropic'))
            result, usage = asyncio.run(self.provider.complete('system', {}, json_mode=True))
        self.assertEqual(result, {'ok': True})
        self.assertEqual(usage['prompt_tokens'], 13)
        self.assertEqual(usage['completion_tokens'], 4)

    def test_failed_discovery_preserves_existing_settings(self):
        self.provider.configure({'base_url': 'https://old.example/v1', 'api_key': 'old-key'})
        old = self.provider.public_config()
        with self.transport(lambda request: httpx.Response(404)):
            with self.assertRaisesRegex(ValueError, '配置未更改'):
                asyncio.run(self.provider.connect('https://new.example/v1', 'openai', 'new-key'))
        self.assertEqual(self.provider.public_config(), old)
        self.assertEqual(self.provider.key, 'old-key')

    def test_changed_address_does_not_receive_old_key(self):
        self.provider.configure({'base_url': 'https://old.example/v1', 'api_key': 'old-key'})
        with self.transport(lambda request: self.fail('No remote request should be sent')):
            with self.assertRaisesRegex(ValueError, 'API Key'):
                asyncio.run(self.provider.connect('https://new.example/v1', 'openai', ''))

    def test_same_service_keeps_key_and_current_model(self):
        self.provider.configure({'base_url': 'https://example.com/v1', 'model': 'chosen', 'api_key': 'old-key', 'dialogue_model': 'obsolete'})
        with self.transport(lambda request: httpx.Response(200, json={'data': [{'id': 'first'}, {'id': 'chosen'}]})):
            result = asyncio.run(self.provider.connect('https://example.com/v1/', 'openai', ''))
        self.assertEqual(result['model'], 'chosen')
        self.assertEqual(result['dialogue_model'], '')
        self.assertEqual(self.provider.key, 'old-key')

    def test_local_no_key_and_echo_trace_stays_intact(self):
        def respond(request):
            self.assertNotIn('authorization', request.headers)
            if request.method == 'GET':
                return httpx.Response(200, json={'data': [{'id': 'local-model'}]})
            return httpx.Response(200, json={'choices': [{'message': {'content': 'hello'}}]})
        with self.transport(respond):
            asyncio.run(self.provider.connect('http://127.0.0.1:8082/v1', 'openai', ''))
            self.assertEqual(asyncio.run(self.provider.complete('test', {}))[0], 'hello')
        self.assertNotIn('[REDACTED]', self.provider.store.all('trace')[-1]['response'])

    def test_connection_route_and_clear_key_preserve_settings(self):
        app = create_app(Path(self.tmp.name) / 'web.sqlite3')
        with TestClient(app) as client:
            token = client.get('/api/bootstrap').json()['token']
            headers = {'X-TextileDream-Token': token}
            with self.transport(lambda request: httpx.Response(200, json={'data': [{'id': 'auto-chat'}]})):
                response = client.put('/api/settings/connection', headers=headers,
                    json={'base_url': 'https://example.com/v1', 'api_key': 'route-key', 'protocol': 'openai'})
            self.assertEqual(response.status_code, 200, response.text)
            response = client.put('/api/settings/api', headers=headers, json={'clear_key': True})
            self.assertFalse(response.json()['has_key'])
            self.assertEqual(response.json()['model'], 'auto-chat')
            self.assertEqual(response.json()['base_url'], 'https://example.com/v1')

    def test_discovery_only_lists_models_and_preserves_connection(self):
        self.provider.configure({'base_url': 'https://example.com/v1', 'model': 'chosen',
                                 'api_key': 'saved-key', 'offline': False})
        before = self.provider.public_config()
        def respond(request):
            self.assertEqual(request.method, 'GET')
            self.assertEqual(request.headers['authorization'], 'Bearer saved-key')
            return httpx.Response(200, json={'data': [{'id': 'first'}, {'id': 'chosen'},
                                                    {'id': 'chosen'}, {'id': 'text-embedding-test'}]})
        with self.transport(respond):
            result = asyncio.run(self.provider.discover_models('https://example.com/v1', 'openai', ''))
        self.assertEqual(result['models'], ['first', 'chosen'])
        self.assertEqual(result['selected_model'], 'chosen')
        self.assertEqual(self.provider.public_config(), before)
        self.assertEqual(self.provider.store.all('trace'), [])
        self.assertNotIn('saved-key', json.dumps(result))

    def test_selected_model_is_validated_and_used_for_generation(self):
        def respond(request):
            if request.method == 'GET':
                return httpx.Response(200, json={'data': [{'id': 'first'}, {'id': 'selected'}]})
            self.assertEqual(json.loads(request.content)['model'], 'selected')
            return httpx.Response(200, json={'choices': [{'message': {'content': 'ok'}}]})
        with self.transport(respond):
            result = asyncio.run(self.provider.connect('https://example.com/v1', 'openai', 'key', 'selected'))
            self.assertEqual(result['model'], 'selected')
            self.assertEqual(asyncio.run(self.provider.complete('test', {}, scope='surface'))[0], 'ok')
            before = self.provider.public_config()
            with self.assertRaisesRegex(ValueError, '所选模型'):
                asyncio.run(self.provider.connect('https://example.com/v1', 'openai', '', 'unknown'))
            self.assertEqual(self.provider.public_config(), before)

    def test_models_route_is_protected_and_does_not_save(self):
        app = create_app(Path(self.tmp.name) / 'models.sqlite3')
        with TestClient(app) as client:
            payload = {'base_url': 'https://example.com/v1', 'protocol': 'anthropic', 'api_key': 'new-key'}
            self.assertEqual(client.post('/api/settings/connection/models', json=payload).status_code, 403)
            headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
            before = app.state.service.provider.public_config()
            def respond(request):
                self.assertEqual(request.method, 'GET')
                self.assertEqual(request.headers['x-api-key'], 'new-key')
                return httpx.Response(200, json={'data': [{'id': 'claude-first'}, {'id': 'claude-chosen'}]})
            with self.transport(respond):
                response = client.post('/api/settings/connection/models', headers=headers, json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['models'], ['claude-first', 'claude-chosen'])
                self.assertEqual(app.state.service.provider.public_config(), before)
                response = client.put('/api/settings/connection', headers=headers,
                                      json={**payload, 'model': 'claude-chosen'})
                self.assertEqual(response.json()['model'], 'claude-chosen')

    def test_concurrent_config_change_during_discovery_is_not_overwritten(self):
        def respond(request):
            self.provider.configure({'model': 'changed-during-request'})
            return httpx.Response(200, json={'data': [{'id': 'first'}]})
        with self.transport(respond):
            with self.assertRaisesRegex(ValueError, '其他操作更新'):
                asyncio.run(self.provider.connect('https://example.com/v1', 'openai', 'key'))
        self.assertEqual(self.provider.config()['model'], 'changed-during-request')


if __name__ == '__main__':
    unittest.main()
