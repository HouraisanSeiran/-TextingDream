"""Portable policy and dialogue integration tests; no model, GPU or external service."""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from app.provider import Provider
from app.storage import Store
from app.token_budget import output_tokens
from tools.local_dialogue_probe import probe


@pytest.mark.parametrize('scope,expected', [
    ('connection_test', 256), ('intent', 256), ('surface', 1024), ('player_reply', 1024),
    ('background_select', 2048), ('background_polity', 4096), ('background_history', 8192),
    ('generator_complete', 4096), ('world_stage_3', 8192), ('world_package_setting', 8192),
])
def test_wire_budget_and_local_no_auth(scope, expected):
    with tempfile.TemporaryDirectory() as directory:
        provider = Provider(Store(Path(directory) / 'test.sqlite3'))
        provider.key = ''
        provider.configure({'base_url': 'http://127.0.0.1:18083/v1', 'offline': False,
                            'max_tokens': 6000})
        def respond(request):
            assert request.url.path == '/v1/chat/completions'
            assert 'authorization' not in request.headers
            assert json.loads(request.content)['max_tokens'] == expected
            return httpx.Response(200, json={'choices': [
                {'finish_reason': 'stop', 'message': {'content': '回答'}}]})
        original = httpx.AsyncClient
        with patch('app.provider.httpx.AsyncClient', side_effect=lambda **kw:
                   original(transport=httpx.MockTransport(respond), **kw)):
            text, usage = asyncio.run(provider.complete('规则', {}, scope=scope))
        assert text == '回答'
        assert usage == {}  # Missing counts remain unknown, not synthetic zeroes.


def test_explicit_override_and_legacy_fallback():
    assert output_tokens('surface', 1500, 6000) == 1500
    assert output_tokens('unregistered', fallback=6000) == 6000
    for invalid in (0, -1, True, 1.5, '1024', 65537):
        with pytest.raises(ValueError, match='输出 token'):
            output_tokens('surface', invalid)


@pytest.mark.parametrize('mode', ['scene', 'plain'])
def test_isolated_dialogue_uses_real_turn_pipeline(mode):
    def respond(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'data': [{'id': 'local-test'}]})
        payload = json.loads(request.content)
        assert payload['max_tokens'] == 1024
        assert 'authorization' not in request.headers
        content = (json.dumps({'narration': '我听着对方的回答，暂时保留判断。', 'reactions': []},
                              ensure_ascii=False) if mode == 'scene' else '我听着对方的回答，暂时保留判断。')
        return httpx.Response(200, json={'choices': [
            {'finish_reason': 'stop', 'message': {'content': content}}],
            'usage': {'prompt_tokens': 2500, 'completion_tokens': 30}})
    original = httpx.AsyncClient
    with patch('app.provider.httpx.AsyncClient', side_effect=lambda **kw:
               original(transport=httpx.MockTransport(respond), **kw)):
        report = asyncio.run(probe('http://127.0.0.1:18083/v1', turns=6, mode=mode,
                                   context_chars=18000))
    assert report['status'] == 'transport_and_structure_passed', report.get('error')
    assert len(report['rows']) == 6
    assert report['rows'][-1]['state_version'] > report['rows'][0]['state_version']
    assert report['quality_review'] == 'pending'


def test_truncated_model_reply_does_not_advance_save():
    def respond(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'data': [{'id': 'local-test'}]})
        return httpx.Response(200, json={'choices': [
            {'finish_reason': 'length', 'message': {'content': '{"narration":"未完'}}]})
    original = httpx.AsyncClient
    with patch('app.provider.httpx.AsyncClient', side_effect=lambda **kw:
               original(transport=httpx.MockTransport(respond), **kw)):
        report = asyncio.run(probe('http://127.0.0.1:18083/v1', turns=1))
    assert report['status'] == 'error'
    assert '截断' in report['error']
    assert report['rows'][0]['save_unchanged']


def test_probe_refuses_external_address():
    with pytest.raises(ValueError, match='本机回环'):
        asyncio.run(probe('https://example.com/v1'))
