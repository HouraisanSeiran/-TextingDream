"""54-turn local stress test using deterministic long replies; no network model calls."""
import asyncio
import copy
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.service import Service
from app.storage import Store
from app.contracts import Turn
from app.prompts import stable_json
from tokenizers import Tokenizer


async def run():
    tokenizer = Tokenizer.from_file(str(ROOT/'tools/tokenizers/deepseek-v3-tokenizer.json'))
    count = lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids)
    rows = []
    out = ROOT/'artifacts'/('local_long_dialogue_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        svc = Service(Store(Path(temp)/'local.sqlite3'),ROOT)
        svc.store.put('settings','preferences',{'conversation_mode':'scene'})
        svc.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':False,'max_tokens':1200})
        s = svc.runtime.new_session('本地54轮压力测试','protagonist')
        previous_contexts = []
        all_turns = []
        async def simulated_model(system, context, **kwargs):
            n = len(rows)+1
            # Deliberately keep a stable length and repeat topics to exercise note retrieval.
            paragraph = ('我站在街角，把看见的路标和听见的传闻分别写进册子。商人指着远处的道路，'
                         '说过往旅人通常会先到驿馆打听水源与通行情况，但他没有亲自走过每一条支路。'
                         '我暂且记下这句话，没有把它当成已证实的消息。风吹动摊位上的布幔，'
                         '附近有人核对货物，也有人等待同行者。我检查纸笔与行囊，保留尚未回答的问题。'
                         '万言机只能辅助理解听到的话，不能证明说话者知道全部情况。'
                         '在得到进一步证据以前，我只记录眼前的动作与对方原有的措辞，不替陌生人推断动机。')
            reply = f'第{n}轮见闻。'+paragraph+'\n\n'+paragraph
            # Counterfactual only: same context but carry all earlier raw turns.
            unbounded = copy.deepcopy(context)
            unbounded['history'] = copy.deepcopy(all_turns)
            unbounded['last_summary'] = ''
            row = {'round':n,'scene':context.get('scene'),'history_turns':len(context['history']),
                   'summary_chars':len(context['last_summary']), 'knowledge_points':len(context['knowledge']),
                   'dialogue_points':len(context['dialogue_knowledge']),
                   'input_v3_estimate':count(system)+count(stable_json(context)),
                   'unbounded_history_v3_estimate':count(system)+count(stable_json(unbounded)),
                   'reply_chars':len(reply),'reply_v3_estimate':count(reply),'system':system}
            rows.append(row)
            previous_contexts.append(copy.deepcopy(context))
            all_turns.append({'input':context['input'],'reply':reply})
            return reply, {'mode':'local_simulation','calls':0}

        with patch.object(svc.provider,'complete',simulated_model):
            for stage in range(3):
                for turn in range(18):
                    state = svc.store.session(s['id'])
                    node = svc.runtime.node(state)
                    action = next(a['id'] for a in node['actions'] if a.get('ends_event')) if turn==17 else None
                    await svc.turn(s['id'],Turn(message=f'本地测试{stage+1}-{turn+1}：我观察道路、商人和传闻，继续记录万言机译出的信息。',action_id=action))
                if stage<2:
                    state = svc.store.session(s['id'])
                    places = svc.runtime.surface(state)['places']
                    dest = next(p['id'] for p in places if p['can_move'] and not p['explored'])
                    svc.runtime.move(state,dest)
        state = svc.store.session(s['id'])
        assert len(rows)==54
        assert len(svc.runtime.conversations(state))==3
        assert max(r['history_turns'] for r in rows)<=6
        assert all(rows[i]['history_turns']==0 for i in (0,18,36))
        assert max(r['summary_chars'] for r in rows)<=1600
        assert len({r['system'] for r in rows})==1
        from app.knowledge import notebook
        assert all(n['content'] in '\n'.join(t['reply'] for t in all_turns) for n in notebook(state))
        # Old chats remain stored in full while the generation context is bounded.
        assert sum(len(c['turns']) for c in svc.runtime.conversations(state))==54
        for r in rows:
            r.pop('system')
        (out/'逐轮统计.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'边界上下文.json').write_text(json.dumps({str(i+1):previous_contexts[i] for i in (0,5,6,17,18,24,35,36,53)},ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# 本地长对话测试报告','',
             '54轮，3个主要场景，每场景18轮；每次回复为约450字的固定中文模拟文本。使用真实 Service.turn 和上下文组装代码，替换远程生成环节，无付费API调用。输入/输出均使用DeepSeek V3本地分词器估算，不是V4或线上账单；缓存命中未测。', '',
             '|轮次|历史轮数|前场景摘录字符|输入token估算|全历史反事实估算|','|---|---:|---:|---:|---:|']
    for i in (0,5,6,17,18,24,35,36,53):
        r=rows[i]
        lines.append(f'|{r["round"]}|{r["history_turns"]}|{r["summary_chars"]}|{r["input_v3_estimate"]}|{r["unbounded_history_v3_estimate"]}|')
    lines += ['',f'回复长度：{min(r["reply_chars"] for r in rows)}—{max(r["reply_chars"] for r in rows)}字符。']
    for i in (18,36):
        a,b=rows[i-1]['input_v3_estimate'],rows[i]['input_v3_estimate']
        lines.append(f'第{i+1}轮换场景：{a} → {b}，输入估算减少{(a-b)/a:.1%}。')
    lines += ['',f'54轮累计输入估算：{sum(r["input_v3_estimate"] for r in rows):,} token；模拟回复累计输出估算：{sum(r["reply_v3_estimate"] for r in rows):,} token。',
              '全历史反事实是同一提示词中改成携带全部旧轮次并去掉前场景摘录，未向模型发送。它只说明截断对长度的影响，不是同等记忆质量的成本对比。', '',
              '通过：历史上限6轮、场景切换历史归零、前场景摘录不超过1600字符、系统前缀稳定、54轮原文仍完整存档、知识点来源只取表层回复。',
              '限制：较早信息不在最近6轮时会依赖关键词摘录；前场景摘要目前是原文末尾截取，不能保证保留早期承诺、线索和人际关系。此测试证明上下文长度受控，不证明模型在长故事中不会遗忘或产生矛盾。',
              '配套浏览器测试另验证往返旧对话6次，无额外模型调用。实际在线usage与缓存消耗仍须有效API Key。']
    (out/'测试报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)
    print('REPORT:',out,flush=True)


if __name__=='__main__':
    asyncio.run(run())
