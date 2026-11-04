"""Wire formats shared by connection discovery and generation."""
from urllib.parse import urlparse


def api_base(address, protocol):
    address = address.strip().rstrip('/')
    parsed = urlparse(address)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('请输入有效请求地址，不要包含密钥、查询参数或用户名')
    if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('远程 API 必须使用 HTTPS')
    suffix = '/messages' if protocol == 'anthropic' else '/chat/completions'
    if address.endswith(suffix):
        address = address[:-len(suffix)]
    if not urlparse(address).path and (protocol == 'anthropic' or parsed.hostname == 'api.openai.com'):
        address += '/v1'
    return address


def local_endpoint(address):
    return urlparse(address).hostname in ('localhost', '127.0.0.1', '::1')


def headers(protocol, key):
    if protocol == 'anthropic':
        return {'anthropic-version': '2023-06-01', **({'x-api-key': key} if key else {})}
    return {'Authorization': 'Bearer ' + key} if key else {}


def endpoint(config):
    return api_base(config['base_url'], config['protocol']) + ('/messages' if config['protocol'] == 'anthropic' else '/chat/completions')


def request_body(config, payload, json_mode):
    if config['protocol'] != 'anthropic':
        return payload
    system = payload['messages'][0]['content']
    if json_mode:
        system += '\n只返回符合要求的 JSON 对象，不要 Markdown 代码围栏或额外说明。'
    return {'model': payload['model'], 'system': system,
            'messages': payload['messages'][1:], 'max_tokens': payload['max_tokens'],
            'temperature': min(1, config['temperature'])}


def response_content(config, body):
    if config['protocol'] == 'anthropic':
        if body.get('stop_reason') == 'max_tokens':
            raise ValueError('模型输出被截断，本次未写入状态')
        raw = body.get('usage', {})
        usage = dict(raw)
        # Anthropic reports uncached input separately from cache creation/read tokens.
        if 'input_tokens' in raw:
            usage['prompt_tokens'] = raw['input_tokens'] + raw.get('cache_creation_input_tokens', 0) + raw.get('cache_read_input_tokens', 0)
        if 'output_tokens' in raw:
            usage['completion_tokens'] = raw['output_tokens']
        if 'cache_read_input_tokens' in raw:
            usage['prompt_cache_hit_tokens'] = raw['cache_read_input_tokens']
            if 'input_tokens' in raw:
                usage['prompt_cache_miss_tokens'] = raw['input_tokens'] + raw.get('cache_creation_input_tokens', 0)
        return ''.join(block['text'] for block in body['content'] if block.get('type') == 'text'), usage
    choice = body['choices'][0]
    if choice.get('finish_reason') == 'length':
        raise ValueError('模型输出被截断，请提高输出预算后重试；本次未写入状态')
    return choice['message']['content'], body.get('usage', {})
