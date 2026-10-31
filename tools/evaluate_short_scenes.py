"""Small real local-model probe; temporary journeys, saved raw traces, no production saves."""
import asyncio
import json
import tempfile
import time
from pathlib import Path

from app import free_actions, scene_judgment
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from .playable_scenes import ROOT, scenes


async def main():
    output = ROOT / 'artifacts/playable-scenes/model-evaluation.json'
    rows = []
    with tempfile.TemporaryDirectory() as temp:
        svc = Service(Store(Path(temp) / 'test.sqlite3'), ROOT)
        def online():
            svc.provider.configure({'base_url': 'http://127.0.0.1:8082/v1', 'model': 'qwen3',
                                    'dialogue_model': 'qwen3', 'author_model': 'qwen3',
                                    'offline': False, 'api_key': 'local', 'temperature': .2,
                                    'max_concurrency': 1, 'max_tokens': 900, 'timeout_seconds': 180})
        async def act(s, id):
            a = free_actions.describe(s, svc.runtime.package(s['revision'])['story'], svc.runtime.node(s), id)
            response = await svc.turn(s['id'], Turn(message=a['label'], action_id=id, confirm=a['confirm']))
            return svc.store.session(s['id']), response
        def start(index):
            data = scenes()[index]
            svc.runtime.commit_package(data['story'], data['characters'], 'model probe')
            return svc.runtime.new_session('model probe', 'protagonist')
        async def record(name, operation):
            tick = time.perf_counter()
            try:
                result = await operation()
                rows.append({'case': name, 'status': 'accepted', 'seconds': round(time.perf_counter()-tick, 2), 'result': result})
            except Exception as error:
                rows.append({'case': name, 'status': 'rejected', 'seconds': round(time.perf_counter()-tick, 2),
                             'error': str(error)})
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({'model': 'qwen3 / Qwen3-4B-Q4_K_M', 'cases': rows,
                                          'traces': svc.store.all('trace')}, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({k: v for k, v in rows[-1].items() if k != 'result'}, ensure_ascii=False), flush=True)

        svc.provider.configure({'offline': True})
        s = start(0)
        s, _ = await act(s, 'ask_job')
        s, _ = await act(s, 'go_search')
        svc.runtime.move(s, 'yard')
        s = svc.store.session(s['id'])
        online()
        for text in ('我想偷走晾衣绳上的衬裤，然后当面炫耀', '我不偷衣服，只想慢慢找到运货单', '我要飞到月亮上'):
            async def probe(text=text):
                result = await scene_judgment.intent(svc, s, svc.runtime.package(s['revision'])['story'], svc.runtime.node(s), text)
                assert svc.store.session(s['id']) == s, '意图改变了存档'
                return result
            await record('intent: ' + text, probe)

        # Real configured actions, real original checks. No mocked model outputs.
        for index, id in ((1, 'accuse'), (2, 'poison_accusation')):
            s = start(index)
            online()
            async def probe(s=s, id=id):
                saved, _ = await act(s, id)
                return {'reply': saved['active']['turns'][-1]['reply'], 'judgment': saved['scene_judgments'][-1],
                        'balance': saved['local']['resources']['pence'], 'development': saved.get('development')}
            await record('reaction: ' + id, probe)

        # Same observation and lawful options, contrasting declared values and relationship.
        for strict in (False, True):
            data = scenes()[1]
            actor = data['story']['mechanics']['scene_judgment']['actors']['guard']
            actor['values'] = ('强烈看重公开尊严，遇到无证据的辱骂会明确要求收回。' if strict
                               else '耐心，重视消除误会；对熟人优先说明收费，不先训斥。')
            data['story']['mechanics']['start_profiles']['profiles'][0]['relations']['guard']['trust'] = .1 if strict else .9
            svc.runtime.commit_package(data['story'], data['characters'], 'synthetic contrast')
            s = svc.runtime.new_session('contrast', 'protagonist')
            async def probe(s=s):
                saved, _ = await act(s, 'accuse')
                return {'reply': saved['active']['turns'][-1]['reply'], 'judgment': saved['scene_judgments'][-1]}
            await record('contrast: ' + ('strict' if strict else 'patient'), probe)


if __name__ == '__main__':
    asyncio.run(main())
