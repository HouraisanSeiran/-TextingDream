"""Summarize saved live-test usage, including billed failed calls and reasoning."""
import json
from pathlib import Path
import statistics
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    folders = sorted((ROOT/'artifacts').glob('long_dialogue_online_*'))
    records = []
    errors = []
    with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,timeout=10) as client:
        b = client.get('/api/bootstrap').json()
        client.headers['X-TextileDream-Token'] = b['token']
        for folder in folders:
            path = folder/'results.json'
            if not path.exists():
                continue
            report = json.loads(path.read_text(encoding='utf-8'))
            if not report['created'].startswith('20260916'):
                continue
            errors.extend(report['errors'])
            for row in report['rows']:
                trace = client.get('/api/inner/traces/'+row['trace_id']).json()
                usage = trace.get('usage',{})
                body = json.loads(trace['response'])
                message = body['choices'][0]['message']
                reasoning = usage.get('completion_tokens_details',{}).get('reasoning_tokens')
                records.append({**row,'reasoning_tokens':reasoning,
                                'nonreasoning_output_tokens':row['output_tokens']-reasoning if reasoning is not None else None,
                                'reply_chars':len(message.get('content') or ''),'session_id':report['session_id']})
        traces = client.get('/api/inner/traces').json()
        failed = []
        for t in traces:
            if t.get('scope')!='surface' or t.get('status')!='error' or not t.get('usage',{}).get('completion_tokens'):
                continue
            detail = client.get('/api/inner/traces/'+t['id']).json()
            messages = detail.get('request',{}).get('messages',[])
            if len(messages)>1 and '【测试轮' in messages[1].get('content',''):
                failed.append(t)
    target = ROOT/'artifacts/长对话真实测试汇总.md'
    lines = ['# DeepSeek V4 长对话真实测试','',
             '数据来自本地服务实际请求的 usage；模型响应标识见逐轮数据。未按价格折算费用。缓存命中计入输入总量，输出包含推理。', '',
             '|轮次|输入|缓存命中|输出总量|其中推理|正文等输出|历史轮数|上场景摘录字符|耗时秒|',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in records:
        lines.append('|'+ '|'.join(str(r[k]) for k in ['round','input_tokens','cache_hit_tokens','output_tokens','reasoning_tokens','nonreasoning_output_tokens','history_turns','summary_chars'])+f'|{r["elapsed_ms"]/1000:.1f}|')
    total_in=sum(r['input_tokens'] for r in records)
    total_out=sum(r['output_tokens'] for r in records)
    hits=sum(r['cache_hit_tokens'] or 0 for r in records)
    lines += ['',f'已完成 {len(records)} 轮。成功请求输入 {total_in:,}、输出 {total_out:,} token。']
    if total_in:
        lines.append(f'缓存命中 {hits:,} / {total_in:,} 输入 token（{hits/total_in:.1%}）。')
    for t in failed:
        u=t['usage']
        lines.append(f'另有失败请求仍产生用量：输入 {u.get("prompt_tokens")}，输出 {u.get("completion_tokens")}；原因：{t.get("error")}。')
    if len(records)>=13:
        old,new=records[11]['input_tokens'],records[12]['input_tokens']
        lines.append(f'首次换场景：输入 {old} → {new}，减少 {(old-new)/old:.1%}。')
    if len(records)>=12:
        plateau=[r['input_tokens'] for r in records[6:11]]
        lines.append(f'同场景第7—11轮已达到6轮历史上限，输入为 {min(plateau)}—{max(plateau)}，均值 {statistics.mean(plateau):.0f}。')
    lines += ['', '当前实现的含义：',
              '- 浏览旧对话只切换界面，本地浏览器已实测往返6次不新增模型请求。',
              '- 地图移动本身不调用模型；进入新场景后发送消息才产生用量。',
              '- 每次回复依然重新提交总概、相关知识、最近6轮历史等内容；上下文缓存影响计费，不代表无需提交。',
              '- 前一场景只截取末尾最多1600字符作为上下文，尚非语义摘要；早期细节可能遗失。',
              '- 当前场景触及max_turns会结束事件，本次对照在此前主动结束，不修改游戏规则。',
              '- V3本地分词估算与真实V4 usage不同，应以本报告真实usage为准。', '',
              '测试前发现1200输出上限不足以覆盖V4推理，调整为8000后继续；该上限只是单次请求生成长度，不是总费用预算。', '',
              '过程异常：'+('；'.join(errors) if errors else '无')]
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'artifacts/长对话真实测试逐轮数据.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed',len(records),'input',total_in,'output',total_out,'cache',hits)
    print(target)


if __name__=='__main__':
    main()
