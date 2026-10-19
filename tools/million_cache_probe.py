"""Same million-token prefix replay and one appended conversation turn."""
import asyncio
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.million_context_benchmark import request,MODEL


async def main():
    out=ROOT/'artifacts/million_context_20260917'
    with gzip.open(out/'prompts/1000000_73101.json.gz','rt',encoding='utf-8') as f:p=json.load(f)
    baseline=json.loads((out/'results/1000000_73101_False.json').read_text(encoding='utf-8'))
    if baseline['status']!='completed':raise ValueError('Million baseline was not completed')
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('Expected one key')
    key=keys.pop();destination=out/'cache';destination.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=httpx.Timeout(600,connect=30,write=180),trust_env=False) as client:
        for name in ('repeat_1','repeat_2','next_turn'):
            dest=destination/(name+'.json')
            if dest.exists():continue
            messages=list(p['messages'])
            if name=='next_turn':
                messages += [{'role':'assistant','content':baseline['content']},
                    {'role':'user','content':'再次核对同一组问题，返回同一JSON结构，保留原始证据编号。不要根据你自己的上一条回答补出档案没有的细节。'}]
            payload={'model':MODEL,'messages':messages,'max_tokens':8192,'stream':True,
                'stream_options':{'include_usage':True},'response_format':{'type':'json_object'},
                'thinking':{'type':'disabled'},'temperature':0}
            with gzip.open(destination/(name+'_request.json.gz'),'wt',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False)
            await request(client,key,payload,dest,{**p['metadata'],'id':name,'thinking':False,
                'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest()},p['expected'])
    print('CACHE COMPLETE',flush=True)


if __name__=='__main__':asyncio.run(main())
