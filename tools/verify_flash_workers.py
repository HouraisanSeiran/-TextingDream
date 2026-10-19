"""Real Flash smoke/recall tests in an isolated save; synthetic history is labelled."""
import asyncio
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.service import Service
from app.storage import Store
from app.contracts import DraftRequest, Turn
from app.prompts import surface_prefix


async def main():
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1: raise SystemExit('Expected exactly one test key')
    out=ROOT/'artifacts'/('flash_workers_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        svc=Service(Store(Path(tmp)/'live.sqlite3'),ROOT)
        svc.provider.configure({'api_key':keys.pop(),'model':'deepseek-flash','dialogue_model':'deepseek-flash',
            'author_model':'deepseek-flash','offline':False,'max_tokens':8192,'thinking_mode':'enabled','max_concurrency':2})
        rt=svc.runtime
        s=rt.new_session('检索对照：合成历史，不是真实游玩','protagonist')
        s['active']['turns']=[{'input':'我第一次给你做了炒肉和白粥。你觉得好吃吗？','reply':'你说肉有些咸，白粥很香，喜欢在粥里放桂花。'}]
        s['active']['turns'] += [{'input':f'我们记录第{i}处屋檐和路面的颜色。','reply':'青瓦上有细雨，石阶显得湿润。'} for i in range(30)]
        rt.store.save_session(s)
        rows=[]
        async def probe(name,query,enabled):
            context=rt.context(s,'player',query,{**svc.preferences(),'recall_enabled':enabled})
            row={'case':name,'synthetic_history':True,'recall_enabled':enabled,'context':context}
            try:
                reply,usage=await svc.provider.complete(surface_prefix(rt.package(s['revision']),''),context,scope='surface')
                row.update(status='success',reply=reply,usage=usage)
            except ValueError as e: row.update(status='error',error=str(e))
            rows.append(row)
        async def turn_and_drafts():
            live=rt.new_session('独立对话与后台并发测试','protagonist')
            async def turn():
                try:
                    await svc.turn(live['id'],Turn(message='我准备出发，先看看眼前的情形，不拿走任何东西。请简短描述。'))
                    rows.append({'case':'service_turn','status':'success','reply':svc.store.session(live['id'])['active']['turns'][-1]['reply']})
                except ValueError as e: rows.append({'case':'service_turn','status':'error','error':str(e)})
            async def drafts():
                result=await svc.generate_batch([
                    DraftRequest(kind='fact',instruction='补充商路驿站维修传闻，明确客观真相与旅人所闻不同；不要添加新角色，公开字段留空。'),
                    DraftRequest(kind='item',instruction='生成一件平凡陶碗，绑定现有地点，完整填写名称、描述、未公开信息；公开字段留空。')])
                rows.append({'case':'batch','result':result})
            await asyncio.gather(turn(),drafts())
        await asyncio.gather(
            probe('meal_recall_on','我第1次给你做的炒肉和白粥好不好吃？回忆当时的评价，别猜测。',True),
            probe('meal_recall_off','我第1次给你做的炒肉和白粥好不好吃？回忆当时的评价，别猜测。',False),
            probe('unrelated','检查当前的通关文书，不要猜测。',True),
            turn_and_drafts())
        traces=svc.store.all('trace')
        (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2),encoding='utf-8')
        usage={k:sum(t.get('usage',{}).get(k,0) or 0 for t in traces) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')}
        summary={'requested_model':'deepseek-flash','response_models':sorted(set(t.get('response_model','') or '' for t in traces)),
                 'calls':len(traces),'successful_calls':sum(t['status']=='success' for t in traces),'usage':usage,
                 'cases':[{'case':r['case'],'status':r.get('status'),'retrieved':[x['source_id'] for x in r.get('context',{}).get('recalled_dialogue',[])],
                           'reply':r.get('reply'),'batch_statuses':[('error' if 'error' in x else 'draft') for x in r.get('result',{}).get('results',[])]} for r in rows]}
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'artifact':str(out),**summary},ensure_ascii=False),flush=True)

if __name__=='__main__':asyncio.run(main())
