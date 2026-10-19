"""Paired, synthetic short-dialogue replay using production context assembly.

Same canonical history in each arm; responses are measured but not fed back,
so content drift does not masquerade as a caching improvement. No warmup calls.
"""
import asyncio
import copy
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.service import Service
from app.storage import Store
from app.prompts import canonical,context_json,surface_prefix


def old_context(context,scope):
    order=('mode','scene','location','description','characters','last_summary','history','knowledge','elements','memories','dialogue_knowledge','self','current_state','current_time','current_daytime','current_inventory','current_event','recalled_dialogue','current_anchor','resolved_action','input')
    keys=list(order[:-1])+sorted(set(context)-set(order))+['input']
    return json.dumps({k:canonical(context[k]) for k in keys if k in context},ensure_ascii=False,separators=(',',':'))


async def main():
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('Expected one key')
    key=keys.pop();out=ROOT/'artifacts'/('short_cache_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True)
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        services={arm:Service(Store(Path(tmp)/arm/'test.sqlite3'),ROOT) for arm in ('before','after')}
        sessions={arm:svc.runtime.new_session('短对话缓存合成回放','protagonist') for arm,svc in services.items()}
        for svc in services.values():
            svc.provider.configure({'api_key':key,'model':'deepseek-flash','offline':False,'thinking_mode':'disabled','temperature':0,'max_tokens':1200})
        history=[]
        for round in range(1,13):
            for arm in (('before','after') if round%2 else ('after','before')):
                svc=services[arm];s=copy.deepcopy(sessions[arm]);s['active']['turns']=copy.deepcopy(history)
                # Same changing current scene in both arms, history remains at actual old location.
                if round>=7:s['location']='western_pass';s['characters'][s['hero']]['location']='western_pass';s['last_scene_id']='western_pass'
                s['time']=8+round
                prefs={**svc.preferences(),'history_strategy':'sliding' if arm=='before' else 'staged'}
                query='请只回答现在的地点、白昼或夜间、确认持有的物品。不要猜测，不要做动作，限60字。'
                ctx=svc.runtime.context(s,'player',query,prefs)
                system=surface_prefix(svc.runtime.package(s['revision']), '')
                # Equal-length independent prefixes reduce between-arm cache contamination.
                system='短对话回放组 '+('A' if arm=='before' else 'B')+'\n'+system
                serializer=old_context if arm=='before' else context_json
                try:
                    with patch('app.provider.context_json',serializer):
                        reply,usage=await svc.provider.complete(system,ctx,scope='surface')
                    trace=svc.store.all('trace')[-1]
                    row={'round':round,'arm':arm,'reply':reply,'usage':usage,'status':'success',
                         'elapsed_ms':trace['elapsed_ms'],'history_turns':len(ctx['history']),
                         'expected_anchor':ctx['current_anchor'],'cache':trace['cache']}
                except ValueError as e:row={'round':round,'arm':arm,'status':'error','error':str(e)}
                rows.append(row)
                (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
                (out/(str(round)+'_'+arm+'_context.json')).write_text(json.dumps(ctx,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(row,ensure_ascii=False),flush=True)
            history.append({'input':f'第{round}次短谈，我询问身边的动静。','reply':f'我听到脚步声，停下来留意对方的回答。这是第{round}次交谈，我没有拿取物品，也没有办理任何手续。'})
        summary={}
        for arm in services:
            group=[r for r in rows if r['arm']==arm and r['status']=='success']
            totals={k:sum(r['usage'].get(k,0) for r in group) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')}
            totals['hit_rate']=totals['prompt_cache_hit_tokens']/max(1,totals['prompt_tokens'])
            totals['peak_usd_estimate']=(totals['prompt_cache_hit_tokens']*.006+totals['prompt_cache_miss_tokens']*.30+totals['completion_tokens']*1.20)/1000000
            summary[arm]={'calls':len(group),**totals}
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print('REPORT '+str(out)+' '+json.dumps(summary),flush=True)


if __name__=='__main__':asyncio.run(main())
