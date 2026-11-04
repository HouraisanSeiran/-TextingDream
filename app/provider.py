"""One bounded request per generation; credentials never enter prompts or logs."""
import json
import os
import time
import uuid
import hashlib
import asyncio
from .contracts import ApiSettings
from .cache_metrics import cache_usage, context_stats
from datetime import datetime, timezone
from .prompts import context_json
from . import ai_protocols
from urllib.parse import urlparse
import httpx


class Provider:
    def __init__(self, store):
        self.store = store
        self.key = os.getenv('DEEPSEEK_API_KEY', '')
        self._condition = asyncio.Condition()
        self._active = 0

    def config(self):
        defaults = ApiSettings().model_dump(exclude={'api_key', 'clear_key'})
        defaults.update(base_url=os.getenv('DEEPSEEK_BASE_URL', defaults['base_url']),
                        model=os.getenv('DEEPSEEK_MODEL', defaults['model']), offline=not bool(self.key))
        old = self.store.get('settings', 'api', {})
        if 'thinking_mode' not in old:
            defaults['thinking_mode'] = 'enabled' if self.store.get('settings', 'preferences', {}).get('surface_thinking', True) else 'disabled'
        return {**defaults, **old}

    def public_config(self):
        return {**self.config(), 'has_key': bool(self.key)}

    def configure(self, data):
        data = ApiSettings.model_validate({**self.config(), **data}).model_dump()
        data['base_url'] = ai_protocols.api_base(data['base_url'], data['protocol'])
        if data.get('clear_key'):
            self.key = ''
        elif data.get('api_key'):
            self.key = data['api_key'].strip()
        self.store.put('settings', 'api', {k: v for k, v in data.items() if k not in ('api_key', 'clear_key')})

    def _connection(self, address, protocol, api_key):
        address = ai_protocols.api_base(address, protocol)
        old = self.config()
        same = address == ai_protocols.api_base(old['base_url'], old['protocol']) and protocol == old['protocol']
        key = api_key.strip() or (self.key if same else '')
        if not key and not ai_protocols.local_endpoint(address):
            raise ValueError('请为该请求地址填写 API Key')
        return address, key, old, same

    async def _model_ids(self, address, protocol, key):
        """Use the existing protocol and credentials for discovery without changing settings."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as client:
                response = await client.get(address + '/models', headers=ai_protocols.headers(protocol, key))
            if response.status_code != 200:
                raise ValueError(f'无法读取服务的模型列表（HTTP {response.status_code}），请核对地址、密钥和协议；配置未更改')
            data = response.json()['data']
            if not isinstance(data, list):
                raise ValueError('服务的模型列表格式无效；配置未更改')
            excluded = ('embedding', 'embed-', 'whisper', 'tts-', 'rerank', 'moderation', 'dall-e', 'image', 'audio', 'transcribe')
            models = list(dict.fromkeys(item['id'] for item in data
                      if isinstance(item, dict) and isinstance(item.get('id'), str)
                      and item['id'].strip() and len(item['id']) <= 120
                      and not any(part in item['id'].lower() for part in excluded)))
            if not models:
                raise ValueError('服务没有提供可自动识别的对话模型；配置未更改')
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError('无法自动识别模型，请检查服务是否支持所选协议的 /models 接口；配置未更改') from error
        return models

    async def discover_models(self, address, protocol, api_key):
        address, key, old, same = self._connection(address, protocol, api_key)
        models = await self._model_ids(address, protocol, key)
        return {'base_url': address, 'protocol': protocol, 'models': models,
                'selected_model': old['model'] if same and old['model'] in models else models[0]}

    async def connect(self, address, protocol, api_key, model=None):
        """Validate discovery and selection before committing the new connection."""
        previous_key = self.key
        address, key, old, same = self._connection(address, protocol, api_key)
        models = await self._model_ids(address, protocol, key)
        if self.config() != old or self.key != previous_key:
            raise ValueError('连接配置已被其他操作更新，请重新请求模型后保存')
        if model is not None and model not in models:
            raise ValueError('所选模型不在该服务的可用列表中，请重新请求模型；配置未更改')
        model = model or (old['model'] if same and old['model'] in models else models[0])
        self.configure({'base_url': address, 'protocol': protocol, 'api_key': key, 'clear_key': not bool(key),
                        'model': model, 'dialogue_model': '', 'author_model': '', 'offline': False})
        return self.public_config()

    def model_for(self, scope, config=None):
        config = config or self.config()
        role = 'dialogue_model' if scope in ('surface', 'polish', 'player_reply') else 'author_model'
        return config.get(role) or config['model']

    def trace(self, scope, request, response, status, **extra):
        trace = {'id': uuid.uuid4().hex, 'created': datetime.now(timezone.utc).isoformat(),
                 'scope': scope, 'request': request, 'response': response, 'status': status, **extra}
        # Do not store request headers. Also redact a key echoed by a remote endpoint.
        encoded = json.dumps(trace, ensure_ascii=False)
        if self.key:
            encoded = encoded.replace(self.key, '[REDACTED]')
        self.store.record_trace(json.loads(encoded))

    def offline_trace(self, scope, context, result):
        self.trace(scope, {'mode': 'offline', 'context': context}, result, 'offline',
                   note='本地模拟，未发送模型请求', elapsed_ms=0, usage={'calls': 0})

    async def complete(self, system, context, json_mode=False, scope='unspecified', max_tokens=None, thinking=None):
        config = self.config()
        if config['offline']:
            self.trace(scope, {'model': config['model']}, None, 'blocked', error='离线模式未发起远程请求', elapsed_ms=0)
            raise ValueError('当前为离线模式')
        if not self.key and not ai_protocols.local_endpoint(config['base_url']):
            self.trace(scope, {'model': config['model']}, None, 'blocked', error='未配置 API Key，未发送请求', elapsed_ms=0)
            raise ValueError('请在 API 配置中填写密钥，或启用离线模式')
        model = self.model_for(scope, config)
        key = self.key  # A configuration change must not change an in-flight credential.
        payload = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': context_json(context, scope)}], 'max_tokens': max_tokens or config['max_tokens']}
        # Vendor-specific option only for the documented official V4/flash endpoint.
        if urlparse(config['base_url']).hostname == 'api.deepseek.com' and model in ('deepseek-v4-pro', 'deepseek-flash', 'deepseek-v4-flash'):
            enabled = config['thinking_mode'] == 'enabled' if thinking is None else thinking
            payload['thinking'] = {'type': 'enabled' if enabled else 'disabled'}
            if enabled:
                payload['reasoning_effort'] = config['reasoning_effort']
            else:
                payload['temperature'] = config['temperature']
        else:
            payload['temperature'] = config['temperature']
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}
        payload = ai_protocols.request_body(config, payload, json_mode)
        endpoint = ai_protocols.endpoint(config)
        start = time.perf_counter()
        response = None
        trace_status = 'error'
        error_text = None
        body = None
        usage = {}
        try:
            async with self._condition:
                await self._condition.wait_for(lambda: self._active < self.config()['max_concurrency'])
                self._active += 1
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(config['timeout_seconds'], connect=15)) as client:
                    response = await client.post(endpoint, headers=ai_protocols.headers(config['protocol'], key), json=payload)
            finally:
                async with self._condition:
                    self._active -= 1
                    self._condition.notify_all()
            if response.status_code != 200:
                raise ValueError(f'模型服务返回 HTTP {response.status_code}，请检查密钥、余额、模型名和地址')
            body = response.json()
            content, usage = ai_protocols.response_content(config, body)
            if not isinstance(content,str) or not content.strip():
                raise ValueError('模型返回空正文，本次未写入状态')
            result = json.loads(content) if json_mode else content
            trace_status = 'success'
            return result, usage
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, TypeError) as error:
            error_text = type(error).__name__
            raise ValueError('模型连接失败或返回格式无效，本次未写入状态') from error
        except ValueError as error:
            error_text = str(error)
            raise
        finally:
            raw = response.text if response is not None else None
            if raw is not None and key:
                raw = raw.replace(key, '[REDACTED]')
            self.trace(scope, payload, raw, trace_status,
                       cache=cache_usage(usage),
                       context_stats=context_stats(context),
                       worker='dialogue' if scope in ('surface', 'polish', 'player_reply') else 'author',
                       endpoint=endpoint,
                       http_status=response.status_code if response is not None else None,
                       elapsed_ms=round((time.perf_counter()-start)*1000), error=error_text,
                       usage=usage or (body.get('usage', {}) if isinstance(body, dict) else {}),
                       response_model=body.get('model') if isinstance(body,dict) else None,
                       request_sha256=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest(),
                       prefix_sha256=hashlib.sha256(system.encode('utf-8')).hexdigest())
