"""Paired narrative continuation from the completed journey; does not advance save."""
import asyncio
import copy
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.web import create_app
from app.prompts import surface_prefix


async def main():
    out=max(ROOT.glob('artifacts/journey_attention_*/manifest.json')).parent
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    if m['status']!='complete':raise ValueError('Main journey must finish first')
    if (out/'continuation.json').exists():raise ValueError('Continuation already exists; do not duplicate calls')
    app=create_app(out/'test.sqlite3');svc=app.state.service;rt=svc.runtime
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('Need unique test key')
    svc.provider.key=keys.pop()
    state=svc.store.session(m['session_id'])
    query='我在河城停下来，用内心独白回顾旅途：准确回忆出发暗号、临时记忆标记、最初对麦饼和豆汤的评价，再说明商驿封路的说法是谁说的、是否已经证实。最后落回当前地点和时刻。约300字；原文有记录就引用，没有记录就说不知道，不编造补全。'
    base=rt.context(state,'player',query,svc.preferences())
    # No engine action occurs; this is a labelled diagnostic continuation.
    base['resolved_action']={'input_channel':'thought','listeners':[],'outcome':'测试续写，不推进本地状态','ends':False}
    full=copy.deepcopy(base)
    full.update(history=json.loads((out/'history.json').read_text(encoding='utf-8')),last_summary='',recalled_dialogue=[])
    system=surface_prefix(rt.package(state['revision']),svc.store.get('corpus','general')['text'])
    findings=[]
    counter=max(int(p.stem) for p in (out/'calls').glob('*.json'))
    for arm,context in [('runtime',base),('full_history',full)]:
        before={t['id'] for t in svc.store.all('trace')}
        row={'arm':arm,'input':query}
        try:
            reply,usage=await svc.provider.complete(system,context,scope='surface')
            row.update(reply=reply,usage=usage,status='success')
        except ValueError as e:row.update(status='error',error=str(e))
        finally:
            for t in svc.store.all('trace'):
                if t['id'] not in before:
                    counter+=1
                    path=out/'calls'/f'{counter:03}.json'
                    path.write_text(json.dumps({'label':{'kind':'continuation','round':108,'arm':arm},'trace':t},ensure_ascii=False,indent=2),encoding='utf-8')
                    row['trace_file']=str(path.relative_to(out))
        findings.append(row)
        (out/'continuation.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(row,ensure_ascii=False),flush=True)
    lines=['# 相同输入下的剧情续写对照','',query,'']
    for row in findings:lines.extend(['## '+row['arm'],'',row.get('reply',row.get('error','')),''])
    (out/'长历史续写对照.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':asyncio.run(main())
