"""Real quality probes in isolated saves; persist visible evidence, never credentials."""
import asyncio
import argparse
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
from app.contracts import Turn
from app.prompts import surface_prefix


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='deepseek-flash')
    args=parser.parse_args()
    matches = set(re.findall(r'sk-[A-Za-z0-9_-]{16,}', Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(matches) != 1:
        raise ValueError('测试密钥数量不正确')
    key = matches.pop()
    out = ROOT/'artifacts'/('quality_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True)
    results = []
    def save(row):
        results.append(row)
        (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:row.get(k) for k in ('case','thinking','status','usage','elapsed_ms')},ensure_ascii=False),flush=True)
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        svc = Service(Store(base/'main.sqlite3'),ROOT)
        config = {'base_url':'https://api.deepseek.com','model':args.model,'offline':False,'max_tokens':8000,'api_key':key}
        svc.provider.configure(config)
        rt = svc.runtime
        system = surface_prefix(rt.package(), '')
        old = ROOT/'artifacts/long_dialogue_online_20260917_082055'
        cases = []
        for filename,name,expectation in [
            ('context_10.json','背包纠错','空背包；不能继续确认旧正文的纸笔、干粮、水囊和万言机为现有物品。'),
            ('context_13.json','转场纠错','人在西行关城；不能继续站在都城旧院子；已持有万言机。')]:
            ctx = json.loads((old/filename).read_text(encoding='utf-8'))['context']
            ctx['current_inventory'] = [] if name=='背包纠错' else ['万言机']
            ctx['current_daytime'] = '白昼' if 6<=ctx['current_time']%24<18 else '夜间'
            ctx['current_event'] = {'title':ctx['scene'],'goal':'查看眼前情况'}
            cases.append((name,ctx,expectation))
        # Obtain the real projected rumor context, including its engine resolution.
        svc.provider.configure({**config,'offline':True})
        probe = rt.new_session('传闻投影样本','protagonist')
        for action,dest in [('pack','western_pass'),('translate','crescent_oasis')]:
            await svc.turn(probe['id'],Turn(message='继续',action_id=action))
            probe=svc.store.session(probe['id']);rt.move(probe,dest)
        request=Turn(message='商人说封路九天，万言机能判定他说谎并告诉我真实天数吗？',action_id='listen')
        resolution=rt.prepare_turn(probe,request)
        ctx=rt.context(probe,'player',request.message,svc.preferences());ctx['resolved_action']=resolution
        assert '3天' not in json.dumps(ctx,ensure_ascii=False)
        cases.append(('传闻与能力边界',ctx,'只能说明商人传闻九天且未证实；万言机不能测谎；不能说实际三天。'))
        sem=asyncio.Semaphore(2)
        async def compare(index,name,context,expected,thinking):
            async with sem:
                sample=Service(Store(base/f'ab_{index}_{thinking}'/'test.sqlite3'),ROOT)
                sample.provider.configure(config)
                sample.provider.configure({'thinking_mode':'enabled' if thinking else 'disabled'})
                try:
                    reply,usage=await sample.provider.complete(system,context,scope='surface')
                    trace=sample.store.all('trace')[-1]
                    save({'case':name,'thinking':thinking,'status':'completed','expected':expected,'context':context,
                          'system':system,'reply':reply,'usage':usage,'elapsed_ms':trace['elapsed_ms']})
                except Exception as e:
                    save({'case':name,'thinking':thinking,'status':'error','error':type(e).__name__})
        await asyncio.gather(*(compare(i,n,c,e,t) for i,(n,c,e) in enumerate(cases) for t in (False,True)))
        svc.provider.configure(config)
        svc.store.put('settings','preferences',{'surface_thinking':True})
        s=rt.new_session('质量验证：连续旅程','protagonist')
        steps=[
            ('整理行装，带上万言机。','pack',None),
            ('我向关城守卫询问通关需要什么。我还没有办理通行文书。',None,'western_pass'),
            ('我请守卫只说明现在应当先办理哪一步，不替我办完。',None,None),
            ('我说自己没有担保人，问能否补保后再核验。',None,None),
            ('我想用万言机直接读出守卫内心，看看能不能跳过查验。',None,None),
            ('我问货物查验和危险法器的规矩，请用自然对话回答。',None,None),
            ('我请他说明补保和暂缓通行有什么区别。',None,None),
            ('我核对自己的行装和未办手续，不凭空添加东西。',None,None),
            ('我之前有没有担保人？请根据此前对话回答，不要替我安排一个。',None,None),
            ('使用万言机协助交谈，描述裁定结果。','translate',None),
            ('我听商人介绍道路消息，把他说的话保留为传闻。','listen','crescent_oasis'),
            ('我向港口学者转述先前商人说的封路天数，请问消息可否证实。',None,'western_port'),
        ]
        for i,(text,action,destination) in enumerate(steps,1):
            if destination:
                rt.move(svc.store.session(s['id']),destination)
            try:
                await svc.turn(s['id'],Turn(message=text,action_id=action))
                trace=svc.store.all('trace')[-1]
                body=json.loads(trace['response'])
                save({'case':f'连续旅程{i:02}','thinking':True,'status':'completed','input':text,
                      'context':json.loads(trace['request']['messages'][1]['content']),
                      'reply':body['choices'][0]['message']['content'],'usage':trace['usage'],'elapsed_ms':trace['elapsed_ms']})
            except Exception as e:
                save({'case':f'连续旅程{i:02}','thinking':True,'status':'error','error':type(e).__name__})
                break
        state=svc.store.session(s['id'])
        (out/'state_checks.json').write_text(json.dumps({'conversations':len(rt.conversations(state)),
            'turns':sum(len(g['turns']) for g in rt.conversations(state)), 'inventory':rt.surface(state)['inventory'],
            'location':rt.surface(state)['location'],'hidden_truth_in_final_context':'3天' in json.dumps(results[-1].get('context',{}),ensure_ascii=False)},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 生成质量测试原文','', '真实 DeepSeek V4 Pro；对照测试使用相同上下文和提示词，仅切换推理。单次样本不证明模型总体优劣。', '']
    for r in results:
        lines += ['## '+r['case']+' / 推理'+('开启' if r['thinking'] else '关闭'),'',r.get('expected',r.get('input','')), '', r.get('reply',r.get('error','')), '']
    (out/'生成原文.md').write_text('\n'.join(lines),encoding='utf-8')
    print('REPORT: '+str(out),flush=True)


if __name__=='__main__':
    asyncio.run(main())
