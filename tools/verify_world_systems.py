"""Replay original 108-turn evidence locally and run a small real-model comparison."""
import asyncio
import copy
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.service import Service
from app.storage import Store
from app.recall import dialogue_records
from app.prompts import surface_prefix


async def main():
    out=ROOT/'artifacts'/'world_systems_v1';out.mkdir(exist_ok=True)
    source=ROOT/'artifacts'/'journey_attention_20260919_215806'
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    svc=Service(Store(out/'test.sqlite3'),ROOT);rt=svc.runtime
    s=rt.new_session('原始证据回放','protagonist')
    original=Store(source/'test.sqlite3').session(manifest['session_id'])
    # Read old package through SQL Store.get only; don't initialize its Runtime/migrate it.
    p=Store(source/'test.sqlite3').get('package',original['revision'])
    records=dialogue_records(original,p)
    recall=[]
    for row in manifest['rows']:
        if not row['expected_recall']:continue
        prior=records[:row['round']-1]
        hits=rt.recall.search('replay',row['message'],prior,k=5,threshold=.12)
        recall.append({'round':row['round'],'before':row['evidence_in_request'],
            'after':row['expected_recall'] in json.dumps(hits,ensure_ascii=False),
            'first_source':hits[0]['source_id'] if hits else None,'hits':hits})
    report={'recall':recall,'model_probes':[],'note':'仅复用既有原文重放检索；不是重跑108轮生成。'}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Recall sources:',sum(r['after'] for r in recall),'/',len(recall),flush=True)
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('Need unique test key')
    svc.provider.configure({'api_key':keys.pop(),'model':'deepseek-flash','dialogue_model':'deepseek-flash','offline':False,'max_tokens':8192})
    tasks=[]
    # Narrative context with real new retrieval, retaining old contradictory replies.
    ctx=rt.context(s,'player','回忆出发前私下暗号和最初对麦饼豆汤的评价，仅引用原话。',svc.preferences())
    ctx['history']=records[-4:]
    ctx['recalled_dialogue']=rt.recall.search('replay',ctx['input'],records,k=5)
    ctx['resolved_action']={'input_channel':'thought','listeners':[],'outcome':'仅回忆，不执行新行动'}
    tasks.append(('recall',ctx))
    # Same question; distinct authored attributes/profiles, unchanged state.
    for cid in ('pass_guard','oasis_merchant','port_scholar'):
        local=copy.deepcopy(s);c=next(c for c in rt.package()['characters']['characters'] if c['id']==cid)
        local['location']=c['location_id'];local['characters'][local['hero']]['location']=c['location_id']
        event=next(e for e in rt.package()['story']['events'] if cid in e['participants'])
        local['active']['node']=event['id'];local['active']['turns']=[]
        context=rt.context(local,'player','一路奔波有点累。你遇到过什么让人忍不住笑的小事？聊两句，不替我购买物品或做决定。',svc.preferences())
        context['resolved_action']={'input_channel':'speech','listeners':[cid],'outcome':'闲谈，不进行交易'}
        tasks.append((cid,context))
    for name,context in tasks:
        before={t['id'] for t in svc.store.all('trace')}
        try:
            text,usage=await svc.provider.complete(surface_prefix(rt.package(),''),context,scope='surface')
            result={'name':name,'reply':text,'usage':usage}
        except ValueError as e:result={'name':name,'error':str(e)}
        report['model_probes'].append(result)
        for t in svc.store.all('trace'):
            if t['id'] not in before:(out/(name+'_trace.json')).write_text(json.dumps(t,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':asyncio.run(main())
