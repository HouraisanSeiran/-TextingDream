"""Load a user-supplied test key directly into the local server; never print it."""
from pathlib import Path
import re
import httpx


def main():
    source = Path('C:/Users/Huang/Desktop/api用后即删.txt')
    text = source.read_text(encoding='utf-8-sig')
    keys = set(re.findall(r'sk-[A-Za-z0-9_-]{16,}', text))
    if len(keys) != 1:
        raise SystemExit('Expected exactly one test key; no configuration changed.')
    key = keys.pop()
    with httpx.Client(timeout=30, trust_env=False) as remote:
        response = remote.get('https://api.deepseek.com/models', headers={'Authorization':'Bearer '+key})
        if response.status_code != 200:
            raise SystemExit('Model discovery HTTP '+str(response.status_code)+'; response omitted.')
        models = [m['id'] for m in response.json().get('data',[]) if isinstance(m.get('id'),str)]
    print('Available model IDs:', ', '.join(models), flush=True)
    selected = 'deepseek-flash' if 'deepseek-flash' in models else None
    if selected is None:
        raise SystemExit('No recognized chat model; no configuration changed.')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=10,trust_env=False) as local:
        boot = local.get('/api/bootstrap').json()
        config = {k:v for k,v in boot['api'].items() if k != 'has_key'}
        config.update(base_url='https://api.deepseek.com',model=selected,dialogue_model=selected,
                      author_model=selected,offline=False,api_key=key,max_tokens=8192,
                      thinking_mode='enabled',reasoning_effort='high',max_concurrency=2)
        r = local.put('/api/settings/api',json=config,headers={'X-TextileDream-Token':boot['token']})
        if r.status_code != 200:
            raise SystemExit('Local configuration HTTP '+str(r.status_code)+'; response omitted.')
        print('Configured:',selected,'has_key:',r.json()['has_key'],flush=True)


if __name__=='__main__':
    main()
