"""Paired real API probes on labelled synthetic state/history, isolated database."""
import asyncio
import copy
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.service import Service
from app.storage import Store
from app.prompts import surface_prefix, template


async def main():
    keys = set(re.findall(r'sk-[A-Za-z0-9_-]{16,}', Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys) != 1:
        raise SystemExit('需要唯一测试密钥')
    out = ROOT / 'artifacts' / ('state_precision_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        svc = Service(Store(Path(tmp) / 'probe.sqlite3'), ROOT)
        svc.provider.configure({'api_key': keys.pop(), 'offline': False, 'model': 'deepseek-flash',
            'dialogue_model': 'deepseek-flash', 'thinking_mode': 'enabled', 'reasoning_effort': 'high', 'max_concurrency': 2})
        rt = svc.runtime
        s = rt.new_session('时空对照合成样本', 'protagonist')
        p = rt.package(s['revision'])
        system = surface_prefix(p, '')
        baseline = system.replace(template('surface'), (ROOT/'artifacts/surface_before_state_precision.txt').read_text(encoding='utf-8').strip(), 1)
        cases = []
        for name, hour, loc, channel, query in [
            ('midnight', 24, s['location'], 'action', '我停下来理清现在是游戏第几天、几点、在哪，然后斟酌出发前想说的话。简短写两段。'),
            ('travel', 30, 'jade_gate', 'speech', '我向守卫说：请告诉我还需要做什么。我想听一句明确的答复，不要替我办好手续。'),
            ('private_thought', 42, 'jade_gate', 'thought', '我心里想：暗号是青瓷七，暂时不能告诉守卫。我保持沉默。写一小段内心活动与可观察反应。'),
            ('failed_action', 9, 'jade_gate', 'action', '我尝试说服守卫让我通过；若没成功，我停下来等他说明。写两段，不替我承诺。'),
        ]:
            state = copy.deepcopy(s)
            # These are deliberately constructed fixtures, not claimed actual play.
            if not any(x['id'] == loc for x in p['story']['locations']):
                loc = next(c['location_id'] for c in p['characters']['characters'] if c['id'] == 'pass_guard')
            state['location'] = loc
            state['characters'][state['hero']]['location'] = loc
            state['time'] = hour
            event = next(e for e in p['story']['events'] if e['location_id'] == loc)
            state['active']['node'] = event['id']
            state['active']['title'] = event['title']
            state['active']['turns'] = [{'input': '此前的旅途', 'reply': '深夜，我站在都城院门后，已经拿到了通关文书。'}]
            context = rt.context(state, 'player', query, svc.preferences())
            context['resolved_action'] = {'outcome': '说服失败，尚未获得通行许可' if name == 'failed_action' else '继续对话',
                'input_channel': channel, 'listeners': ['pass_guard'] if channel == 'speech' else []}
            if name == 'failed_action':
                context['resolved_action']['narrative'] = {'result': 'failure', 'keywords': ['尝试受阻', '询问替代办法']}
            cases.append((name, context))
        rows = []
        # Sequential calls avoid queue delay in latency; alternate arm ordering.
        for repeat in range(2):
            for name, context in cases:
                for arm in (('before', 'after') if repeat == 0 else ('after', 'before')):
                    ctx = copy.deepcopy(context)
                    if arm == 'before':
                        ctx['current_anchor'] = {k:v for k,v in ctx['current_anchor'].items() if k in ('location','scene','daytime','inventory','event','confirmed_records')}
                    row = {'case': name, 'repeat': repeat, 'arm': arm, 'synthetic_fixture': True, 'context': ctx}
                    before_ids = {t['id'] for t in svc.store.all('trace')}
                    try:
                        reply, usage = await svc.provider.complete(baseline if arm == 'before' else system, ctx, scope='surface')
                        row.update(reply=reply, usage=usage, status='success')
                    except ValueError as error:
                        row.update(status='error', error=str(error))
                    trace = next(t for t in svc.store.all('trace') if t['id'] not in before_ids)
                    row['trace_id'] = trace['id']
                    row['elapsed_ms'] = trace['elapsed_ms']
                    try:
                        reasoning = json.loads(trace['response'])['choices'][0]['message'].get('reasoning_content', '')
                    except (TypeError, KeyError, ValueError):
                        reasoning = ''
                    row['returned_reasoning_chars'] = len(reasoning)
                    # Lexical count is not attention, nor a judgment of unnecessary thinking.
                    row['state_term_mentions'] = sum(len(re.findall(term, reasoning)) for term in ('时间','地点','时刻','白昼','夜间','current_anchor'))
                    rows.append(row)
                    (out/'results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(json.dumps({k:row[k] for k in ('case','repeat','arm','status','elapsed_ms','returned_reasoning_chars')}, ensure_ascii=False), flush=True)
        (out/'traces.json').write_text(json.dumps(svc.store.all('trace'), ensure_ascii=False, indent=2), encoding='utf-8')
        summary = {}
        for arm in ('before', 'after'):
            group = [r for r in rows if r['arm'] == arm]
            summary[arm] = {'calls':len(group), 'success':sum(r['status']=='success' for r in group),
                **{k:sum(r.get('usage',{}).get(k,0) or 0 for r in group) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')},
                'returned_reasoning_chars':sum(r['returned_reasoning_chars'] for r in group),
                'state_term_mentions':sum(r['state_term_mentions'] for r in group)}
            counts=[r.get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens') for r in group]
            summary[arm]['reasoning_tokens'] = sum(counts) if all(x is not None for x in counts) else None
        (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'artifact':str(out), 'summary':summary},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    asyncio.run(main())
