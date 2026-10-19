"""Measure actual usage through the running service, without reading API credentials.

Online run: 12 turns in the first scene and 4 after moving. No automatic retries.
--offline uses a temporary database and labels all token counts as local estimates.
"""
import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    temp = tempfile.TemporaryDirectory() if args.offline else None
    if args.offline:
        from fastapi.testclient import TestClient
        from app.web import create_app
        application = create_app(Path(temp.name)/'test.sqlite3')
        application.state.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':True,'max_tokens':1200})
        client = TestClient(application)
    else:
        client = httpx.Client(base_url=args.url, trust_env=False, timeout=90)

    def call(path, body=None):
        response = client.get('/api'+path) if body is None else client.post('/api'+path, json=body)
        if response.status_code != 200:
            raise RuntimeError(f'{path}: HTTP {response.status_code} '+response.text[:500])
        return response.json()

    boot = call('/bootstrap')
    client.headers['X-TextileDream-Token'] = boot['token']
    if not args.offline and (not boot['api']['has_key'] or boot['api']['offline']):
        raise SystemExit('BLOCKED: live service has no API key or offline mode is enabled. No paid calls made.')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = ROOT/'artifacts'/('long_dialogue_'+('offline_' if args.offline else 'online_')+stamp)
    out.mkdir(parents=True, exist_ok=True)
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT/'tools/tokenizers/deepseek-v3-tokenizer.json'))
    count = lambda value: len(tokenizer.encode(value, add_special_tokens=False).ids)
    from app.prompts import stable_json
    report = {'mode':'offline' if args.offline else 'online','configured_model':boot['api']['model'],
              'preferences':boot['preferences'],'rows':[],'errors':[],'created':stamp}
    session = call('/sessions', {'title':'长对话耗量测试 '+stamp,'mode':'protagonist'})
    report['session_id'] = session['id']
    session_path = '/sessions/'+session['id']
    seen = {t['id'] for t in call('/inner/traces')}
    report['readback_calls'] = None

    def save():
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

    def turn(index, phase, text, action=None):
        nonlocal session, seen
        session = call(session_path+'/chat',{'message':text,'action_id':action})
        traces = call('/inner/traces')
        candidates = [t for t in traces if t['id'] not in seen and t['scope']=='surface']
        seen.update(t['id'] for t in traces)
        trace = None
        for candidate in candidates:
            record = call('/inner/traces/'+candidate['id'])
            if args.offline:
                context = record['request']['context']['tail']
            else:
                context = json.loads(record['request']['messages'][1]['content'])
            if context.get('input') == text:
                trace = record
                break
        if trace is None:
            raise RuntimeError('找不到对应请求记录，停止以免生成无依据的统计')
        if args.offline:
            system = trace['request']['context']['system']
            response_model = None
        else:
            system = trace['request']['messages'][0]['content']
            response_model = json.loads(trace['response']).get('model')
        usage = trace.get('usage') or {}
        row = {'round':index,'phase':phase,'scene':session['conversation_id'],
               'input_tokens':usage.get('prompt_tokens'), 'output_tokens':usage.get('completion_tokens'),
               'cache_hit_tokens':usage.get('prompt_cache_hit_tokens',usage.get('prompt_tokens_details',{}).get('cached_tokens')),
               'cache_miss_tokens':usage.get('prompt_cache_miss_tokens'),'response_model':response_model,
               'history_turns':len(context.get('history',[])),'history_chars':len(stable_json(context.get('history',[]))),
               'summary_chars':len(context.get('last_summary','')),'knowledge_points':len(context.get('knowledge',[])),
               'prefix_sha256':trace.get('prefix_sha256'),'elapsed_ms':trace.get('elapsed_ms'),
               'v3_local_estimate':count(system)+count(stable_json(context)),'trace_id':trace['id']}
        report['rows'].append(row)
        (out/f'context_{index:02}.json').write_text(json.dumps({'system':system,'context':context,'usage':usage},ensure_ascii=False,indent=2),encoding='utf-8')
        save()
        print(json.dumps(row,ensure_ascii=False),flush=True)

    try:
        prompts = ['我先观察周围，描述出发前的环境。','我整理行装，检查纸笔和行囊。','我回想自己为什么想踏上旅途，但暂不确定结论。',
                   '我认真观察街边行人的举止。','我查看路上的标记，不擅自推断它们的含义。','我记录眼前所见，并区分看见和猜测。',
                   '我稍作休息，整理这次见闻。','我把还没有得到答案的问题记下来。','我再观察一次周围有没有新的细节。',
                   '我核对行囊中的物品，只写已确认的信息。','我回顾出发前的准备，暂不改变地点。']
        for i, prompt in enumerate(prompts,1):
            turn(i,'同场景长对话',f'【测试轮{i:02}】'+prompt+' 请用约150—250字的第一人称正文回应。')
        # Existing playable package must provide an explicit exit action.
        raw = call('/inner'+session_path)
        package = call('/inner/package?revision='+raw['revision'])
        event = next(e for e in package['story']['events'] if e['id']==raw['active']['node'])
        action = next(a for a in event['actions'] if a.get('ends_event') and a['id'] in {a['id'] for a in session['actions']})
        turn(12,'同场景结束','【测试轮12】'+action['label']+'。请用约150—250字描述已经裁定的结果。',action['id'])
        destinations = [p for p in session['places'] if p['can_move']]
        if not destinations:
            raise RuntimeError('当前场景无可前往的地点，停止测试')
        before_move = {t['id'] for t in call('/inner/traces')}
        session = call(session_path+'/move',{'location_id':destinations[0]['id']})
        report['move_api_calls'] = len({t['id'] for t in call('/inner/traces')}-before_move)
        for i in range(13,17):
            turn(i,'切换场景后',f'【测试轮{i:02}】我观察当前地点，整理眼前细节和已知信息，不替我作决定。请用约150—250字回应。')
        # Exercise actual browser conversation navigation without sending any new turn.
        if not args.offline:
            from playwright.sync_api import sync_playwright, expect
            trace_ids = {t['id'] for t in call('/inner/traces')}
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge',headless=True)
                page = browser.new_page(viewport={'width':1440,'height':1000})
                page.goto(args.url)
                page.evaluate('(id)=>localStorage.setItem("textiledream-session",id)',session['id'])
                page.reload()
                count = len(session['conversations'])
                expect(page.locator('#conversations button')).to_have_count(count)
                for _ in range(3):
                    page.locator('#conversations button').first.click()
                    if count > 1:
                        expect(page.locator('#chat-form')).to_be_hidden()
                    else:
                        expect(page.locator('#chat-form')).to_be_visible()
                    page.locator('#conversations button').last.click()
                    expect(page.locator('#chat-form')).to_be_visible()
                page.screenshot(path=str(out/'conversation-switch.png'),full_page=True)
                browser.close()
            report['readback_calls'] = len({t['id'] for t in call('/inner/traces')}-trace_ids)
    except Exception as error:
        report['errors'].append(str(error))
        print('STOPPED:',str(error),flush=True)
    finally:
        save()
        rows = report['rows']
        lines = ['# 长对话与切换场景测试', '',f'模式：{report["mode"]}；配置模型：{report["configured_model"]}。独立测试旅程：{session["id"]}。',
                 '实际 token 来自提供商 usage；V3本地估算不等于账单。未返回的用量标为 None，不当作零。', '',
                 '|轮次|阶段|实际输入|实际输出|缓存命中|历史轮数|前场景摘要字符|V3估算|', '|---|---|---:|---:|---:|---:|---:|---:|']
        for r in rows:
            lines.append('|'+ '|'.join(str(r[k]) for k in ['round','phase','input_tokens','output_tokens','cache_hit_tokens','history_turns','summary_chars','v3_local_estimate'])+'|')
        lines += ['',f'移动场景新增模型调用：{report.get("move_api_calls","未完成")}；浏览旧对话新增调用：{report["readback_calls"]}。']
        if len(rows)==16 and not args.offline:
            old,new=rows[11]['input_tokens'],rows[12]['input_tokens']
            if old and new is not None:
                lines.append(f'换场景第一轮相对上一轮输入变化：{old} → {new}，减少 {(old-new)/old:.1%}。这是本次样本，受回复长度和检索内容影响。')
            lines.append(f'输入总计：{sum(r["input_tokens"] or 0 for r in rows)}；输出总计：{sum(r["output_tokens"] or 0 for r in rows)}。未换算费用，价格取决于真实模型与缓存计费。')
        lines += ['', '限制：默认仅携带当前章节最近6轮，分章携带前一章节回复末尾最多1600字符；该字段是截取，不是语义摘要。较早信息能否保留取决于相关知识检索，不能据此保证完整长期记忆。', '', '异常：'+('；'.join(report['errors']) or '无')]
        (out/'测试报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        client.close()
        if temp:
            temp.cleanup()
        print('REPORT:',out,flush=True)
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
