"""Replay identical historical contexts in two orders, measure actual provider cache usage."""
import asyncio
import json
import re
import sys
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.prompts import context_json, stable_json


async def main():
    key_text=Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',key_text))
    if len(keys)!=1:
        raise ValueError('测试凭据数量不正确')
    key=keys.pop()
    source=ROOT/'artifacts/long_dialogue_online_20260916_225308'
    out=ROOT/'artifacts/cache_ab'
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    # Same captured scene, growing history, identical prompt meaning and token content.
    # A/B labels separate cache namespaces without supplying extra world information.
    async with httpx.AsyncClient(timeout=180,trust_env=False) as client:
        for step in range(13,17):
            saved=json.loads((source/f'context_{step:02}.json').read_text(encoding='utf-8'))
            for variant in (('original','ordered') if step%2 else ('ordered','original')):
                system='缓存对照实验 '+('A' if variant=='original' else 'B')+'。\n'+saved['system']
                ctx=saved['context']
                content=stable_json(ctx) if variant=='original' else context_json(ctx,'surface')
                started=time.monotonic()
                response=await client.post('https://api.deepseek.com/chat/completions',
                    headers={'Authorization':'Bearer '+key},json={'model':'deepseek-v4-pro',
                    'messages':[{'role':'system','content':system},{'role':'user','content':content}],
                    'max_tokens':8000,'temperature':0.7})
                if response.status_code!=200:
                    raise RuntimeError('API HTTP '+str(response.status_code)+'；错误正文未输出')
                body=response.json()
                row={'variant':variant,'round':step,'model':body.get('model'),'usage':body.get('usage',{}),
                     'finish_reason':body['choices'][0].get('finish_reason'),
                     'seconds':round(time.monotonic()-started,2)}
                rows.append(row)
                (out/'usage.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
                # Save only visible reply; no credentials or internal reasoning in artifacts.
                (out/f'{variant}_{step}.txt').write_text(body['choices'][0]['message'].get('content') or '',encoding='utf-8')
                print(json.dumps(row,ensure_ascii=False),flush=True)
    lines=['# 缓存顺序 A/B 实测','',
           '模型：deepseek-v4-pro。同一组既有第13—16轮上下文，A按字母顺序序列化，B按场景/历史/动态尾部序列化；内容不删减，不增加无关设定，不冻结检索。系统提示只用等长A/B标记区分冷启动。交替请求顺序，推理配置保持一致。', '',
           '|方案|轮次|输入|缓存命中|输出|耗时秒|','|---|---:|---:|---:|---:|---:|']
    for r in rows:
        u=r['usage'];lines.append(f'|{r["variant"]}|{r["round"]}|{u.get("prompt_tokens")}|{u.get("prompt_cache_hit_tokens")}|{u.get("completion_tokens")}|{r["seconds"]}|')
    for variant in ('original','ordered'):
        group=[r for r in rows if r['variant']==variant]
        tokens=sum(r['usage']['prompt_tokens'] for r in group)
        hits=sum(r['usage'].get('prompt_cache_hit_tokens',0) for r in group)
        lines.append(f'\n{variant}：命中 {hits}/{tokens} = {hits/tokens:.1%}；未命中输入 {tokens-hits}。')
    lines += ['', '本测试只验证缓存布局，未验证新增文字约束是否降低错误率；各轮输出仍是独立生成。缓存命中受供应商调度与缓存建立时间影响，小样本结果不能保证每次复现。命中提高减少重复计算及可能的输入费用，不等于输出token减少。',
              '最近6轮窗口滑动时历史首条会变化，仍会破坏历史段命中；不为命中率而携带无限历史。跨场景资料变化也会使新场景首次缓存降低。']
    (out/'缓存对照报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('REPORT:',out/'缓存对照报告.md',flush=True)


if __name__=='__main__':
    asyncio.run(main())
