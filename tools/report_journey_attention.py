"""Summarize persisted real API traces; no API calls and no inferred token bills."""
import csv
import json
import statistics
import sys
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.recall import vector


def recall_audit(rows, out):
    """Recompute the exact lexical score without mutating the saved index."""
    findings=[]
    for row in rows:
        if not row.get('expected_recall'):
            continue
        prior=rows[:row['round']-1]
        vs=[vector(r['message']+'\n'+r['reply']) for r in prior]
        df=Counter(term for v in vs for term in v)
        def weight(v):
            return {t:(1+math.log(n))*(1+math.log((1+len(vs))/(1+df[t]))) for t,n in v.items()}
        q=weight(vector(row['message']))
        qnorm=math.sqrt(sum(x*x for x in q.values()))
        scored=[]
        for old,v in zip(prior,vs):
            w=weight(v)
            score=sum(q[t]*w[t] for t in q.keys() & w.keys())/max(1e-12,qnorm*math.sqrt(sum(x*x for x in w.values())))
            scored.append({'round':old['round'],'score':round(score,4),
                           'contains_answer':row['expected_recall'] in old['message']+'\n'+old['reply']})
        trace=load(out/row['trace_file'])['trace']
        context=json.loads(trace['request']['messages'][1]['content'])
        findings.append({'round':row['round'],'source_scores':[x for x in scored if x['contains_answer']],
                         'top5_before_history_exclusion':sorted(scored,key=lambda x:-x['score'])[:5],
                         'actual_retrieved':context.get('recalled_dialogue',[])})
    (out/'检索诊断.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2),encoding='utf-8')
    return findings


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def totals(calls):
    traces = [c['trace'] for c in calls]
    def sumkey(k):
        return sum(t.get('usage', {}).get(k, 0) for t in traces)
    prompt = sumkey('prompt_tokens')
    completion = sumkey('completion_tokens')
    hit = sum(t.get('usage', {}).get('prompt_cache_hit_tokens',
              t.get('usage', {}).get('prompt_tokens_details', {}).get('cached_tokens', 0)) for t in traces)
    reasoning = sum(t.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens', 0) for t in traces)
    elapsed = [t.get('elapsed_ms', 0) / 1000 for t in traces]
    return dict(calls=len(calls), success=sum(t['status'] == 'success' for t in traces),
                prompt=prompt, completion=completion, reasoning=reasoning, visible=completion-reasoning,
                total=sumkey('total_tokens'), hit=hit, miss=prompt-hit, hit_rate=hit/prompt if prompt else 0,
                mean_seconds=statistics.mean(elapsed) if elapsed else 0,
                p95_seconds=sorted(elapsed)[min(len(elapsed)-1, int(len(elapsed)*.95))] if elapsed else 0,
                max_prompt=max((t.get('usage', {}).get('prompt_tokens', 0) for t in traces), default=0))


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else max(ROOT.glob('artifacts/journey_attention_*/manifest.json')).parent
    m = load(out/'manifest.json')
    calls = [load(p) for p in sorted((out/'calls').glob('*.json'))]
    rows = m['rows']
    retrieval=recall_audit(rows,out)
    narrative = [c for c in calls if c['label'].get('kind') == 'journey']
    groups = {'全部调用（含失败）': calls, '剧情生成': narrative,
              '默认记忆核对': [c for c in calls if c['label'].get('kind') == 'probe' and c['label'].get('arm') == 'runtime'],
              '完整历史核对': [c for c in calls if c['label'].get('kind') == 'probe' and c['label'].get('arm') == 'full_history'],
              '短证据对照': [c for c in calls if c['label'].get('arm') == 'short_control'],
              '终点剧情续写对照': [c for c in calls if c['label'].get('kind') == 'continuation']}
    summary = {k:totals(v) for k,v in groups.items()}
    metrics = {'status': m['status'], 'completed_turns': len(rows), 'totals': summary,
               'stages': {stage:totals([c for c in narrative if c['label'].get('stage') == stage]) for stage in m['route']}}
    (out/'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    flat = []
    for c in calls:
        t, label = c['trace'], c['label']
        u = t.get('usage', {})
        flat.append({'round':label.get('round'), 'kind':label.get('kind'), 'arm':label.get('arm',''),
                     'stage':label.get('stage',''), 'status':t['status'], 'response_model':t.get('response_model'),
                     'prompt_tokens':u.get('prompt_tokens',0), 'completion_tokens':u.get('completion_tokens',0),
                     'reasoning_tokens':u.get('completion_tokens_details',{}).get('reasoning_tokens',0),
                     'cache_hit_tokens':u.get('prompt_cache_hit_tokens',0), 'cache_miss_tokens':u.get('prompt_cache_miss_tokens',0),
                     'elapsed_ms':t.get('elapsed_ms',0), 'request_sha256':t.get('request_sha256','')})
    if flat:
        with (out/'逐次调用.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w=csv.DictWriter(f, fieldnames=flat[0]);w.writeheader();w.writerows(flat)
    lines = ['# 天朝到欧洲：长对话与上下文核对测试', '',
             f'状态：{m["status"]}；已完成 {len(rows)}/{m["planned_turns"]} 轮玩家输入。', '',
             '## 主要结论', '',
             '本次主要短板是旧记忆检索遗漏和错误叙述被反复引用，而不是已证实的“上下文越长，模型越不注意”。第108轮默认上下文核对6/10，完整历史10/10；这不代表大窗口可以消除剧情幻觉。', '',
             '六站108轮能跑通，但仍不是合格的长篇旅行体验：过去经历会被补写，多种职业的表达逐渐偏向同一套核实流程。应优先改善证据检索和事实账本，再提升角色表达与旅行时间模拟。', '',
             '## 测试方式', '',
             '- 路线：'+' → '.join(m['route'])+'。',
             '- 使用实际 FastAPI 路由、状态裁定、记忆检索和 DeepSeek 网络请求；通过 ASGI 在进程内调用接口，没有操作浏览器。',
             '- 每站18轮，由测试脚本编写玩家输入；剧情由远端模型生成，按正常流程写入独立存档。不是逐轮自适应的AI玩家，也不是伪造回复。',
             '- '+m['fixture_note'],
             '- 模型请求与响应标识：'+', '.join(sorted({str(c['trace'].get('response_model')) for c in calls}))+ '。开启思考，reasoning_effort=high，单次输出上限8192。',
             '- 默认上下文：分阶段历史、最多16轮/6000字符阶段、18000字符上下文预算、最多5条原文检索；实际发送内容以calls目录为准。',
             '- 每18轮做结构化核对；第18/54/108轮另做完整原文重放及短证据对照。对照结果不写回剧情。',
             '- 10个核对字段：出发暗号、晚饭评价、地点、游戏日、整点时间、物品、传闻天数、是否证实、守卫是否知道私密暗号、一次性记忆标记。',
             '- 暗号与晚饭在剧情中每18轮追问，成功回答会刷新记忆；一次性记忆标记不主动复习，但模型可能自发重复。',
             '- 指标是行为上的事实保持/检索表现，不能直接测量模型内部注意力；单条路线、少量对照不提供统计显著性结论。', '',
             '## 实际token与耗时', '',
             '|调用组|调用/成功|输入token|输出token|其中思考|输入缓存命中|最大单次输入|平均秒|',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,t in summary.items():
        lines.append(f'|{name}|{t["calls"]}/{t["success"]}|{t["prompt"]:,}|{t["completion"]:,}|{t["reasoning"]:,}|{t["hit_rate"]:.1%}|{t["max_prompt"]:,}|{t["mean_seconds"]:.1f}|')
    lines += ['', '输出token包含思考token，不能把两者相加再计费。缓存命中率按命中输入token/全部输入token加权；不按每次百分比取平均。失败请求如有usage也纳入统计；缺usage时无法推断是否计费。不根据未经确认的单价估算金额。', '',
              '|阶段|剧情输入token|剧情输出token|缓存命中率|平均秒|', '|---|---:|---:|---:|---:|']
    for name,t in metrics['stages'].items():
        lines.append(f'|{name}|{t["prompt"]:,}|{t["completion"]:,}|{t["hit_rate"]:.1%}|{t["mean_seconds"]:.1f}|')
    lines += ['', '## 核对结果（严格字段匹配）', '',
              '|轮次|输入方式|实际输入token|正确字段/10|错误字段|标记原文是否送入|',
              '|---:|---|---:|---:|---|---|']
    for p in m['probes']:
        scores=p.get('exact_scores',{})
        wrong='、'.join(k for k,v in scores.items() if not v) or ('—' if scores else p.get('error','失败'))
        lines.append(f'|{p["round"]}|{p["arm"]}|{p.get("usage",{}).get("prompt_tokens",0):,}|{sum(scores.values())}/10|{wrong}|{p["evidence_present"].get("once_marker")}|')
    lines += ['', '严格匹配会把合理改写也记为不匹配，需要结合下面的实际答案解释。证据是否存在使用字面检索，只能证明字符串存在，不能完整判断语义或可见性。完整历史对照使用独立的核对提示，不等于让模型在同样长的上下文中继续写故事。', '',
              '### 不匹配原始答案', '']
    for p in m['probes']:
        wrong={k:{'expected':p['expected'][k],'answer':p.get('answer',{}).get(k)} for k,v in p.get('exact_scores',{}).items() if not v}
        if wrong:lines += [f'- 第{p["round"]}轮 / {p["arm"]}：`'+json.dumps(wrong,ensure_ascii=False)+'`']
    lines += ['', '## 剧情中的实际记忆追问', '',
              '|轮次|原文已送入|回复字面命中|检索原文条数|实际历史轮数|', '|---:|---|---|---:|---:|']
    for r in rows:
        if r['expected_recall']:
            lines.append(f'|{r["round"]}|{r["evidence_in_request"]}|{r["literal_recall_in_reply"]}|{r["retrieved_records"]}|{r["history_turns"]}|')
    lines += ['', '## 规模与限制', '']
    if rows:
        lines += [f'- 剧情正文共 {sum(len(r["reply"]) for r in rows):,} 字符；实际单次最多保留 {max(r["history_turns"] for r in rows)} 轮原文历史，另有摘要与检索。',
                  f'- 本次跨越 {len({r["conversation_id"] for r in rows})} 个章节对话。最终本地时钟：`{json.dumps(rows[-1]["clock"],ensure_ascii=False)}`。',
                  '- 当前每轮推进1小时、地图移动4小时，因此这一跨洲旅程不是符合历史交通速度的连续时间模拟。',
                  '- 固定输入偏向边界核对、谨慎询问，不能据此衡量自由冒险整体趣味性；无独立人工盲评，也未穷尽职业/角色组合。',
                  '- 初始节点与新加入的欧洲节点都是架空内容，没有用现实史料逐条验证。']
    lines += ['', '## 检索定位', '',
              '按实际输入和此前每轮原文重新计算本地TF-IDF相似度；以下是含正确答案原文的分数。默认阈值0.12。完整候选排序和实际召回记录见`检索诊断.json`。', '',
              '|提问轮次|含答案原文的来源轮次与分数|', '|---:|---|']
    for r in retrieval:
        lines.append(f'|{r["round"]}|'+', '.join(f'{x["round"]}: {x["score"]:.4f}' for x in r['source_scores'])+'|')
    if (out/'continuation.json').exists():
        cont=load(out/'continuation.json')
        lines += ['', '## 同一剧情提示词下的终点续写', '',
                  '两次都使用应用的surface提示词和同一玩家输入；默认组使用正常上下文，完整组替换为108轮历史、清除原文摘录和检索重复。仅作诊断，没有推进存档时间，也没有把续写写入剧情。', '',
                  '|上下文|输入token|输出token（含思考）|思考token|', '|---|---:|---:|---:|']
        for row in cont:
            u=row.get('usage',{})
            lines.append(f'|{row["arm"]}|{u.get("prompt_tokens",0):,}|{u.get("completion_tokens",0):,}|{u.get("completion_tokens_details",{}).get("reasoning_tokens",0):,}|')
        lines += ['',
                  '- 默认组：三个出发记忆都没恢复，并把封路消息的来源含混地写成赶驮者，未准确复述商驿商人的9天说法。',
                  '- 完整历史组：恢复“苇灯四七”“灰鹭八二”“麦饼偏硬，豆汤太淡”，正确指出商驿商人说9天、仍未证实。',
                  '- 完整历史组仍把第90轮生成的“到镇口看墙”当作既往取证经历，说明扩大历史也会保留并传播旧幻觉。',
                  '- 完整组单次输入35,175 token，约为默认组4,978的7.1倍；本次不等于百万token上下文测试。',
                  '- 两组是各一次采样，不能推断准确率分布；原文见`长历史续写对照.md`。']
    lines += ['', '## 正文质量抽查与改进顺序', '',
              '以下是人工抽查到的具体样本，不是全部正文的错误率。', '',
              '|观察|可复核轮次|影响|', '|---|---|---|',
              '|最初记忆未过检索阈值，随后反复召回“记不清”|15/16，33/34，51/52，69/70|第一次漏检变成后续重复叙述；应优先召回最初输入证据|',
              '|虚构既往旅程|35说“上船”已在身后；67替玩家说“有几处收过钱”|当前状态正确，仍不能保证过去经历正确；本地没有相应乘船或付款动作|',
              '|事实被补成新发生的行动|90把“没有收到封路公告”写成玩家到镇口看墙、返回|本地只裁定记下情况，正文补写了取证过程|',
              '|角色表达收敛|守卫核凭信、学者核册页、向导要求只问一项、书记让“报一样”|职业用词有差异，但共同的谨慎核实模板过强；本测试输入也有相同倾向|',
              '|内心通道与状态锚点基本有效|61/97不把私语直接说给NPC；17/35/53/71/89核对本地时钟|只能说明这些样本；不能据此宣称没有隐私泄漏|',
              '|技术规则进入正文|17、53、71出现“归档”“时钟没说”“清单是齐的”|内部约束暴露到小说文本，影响沉浸感；状态核对提问会放大这一现象|', '',
              '建议按以下顺序改进：', '',
              '1. 查询拆分：将“回忆主题”与字数、文风要求分开；玩家原始陈述单独索引，保留日期、地点、通道和听众。',
              '2. 原始证据优先：涉及“出发前、第一次”的问题优先找最早对应记录；不要让后来的“记不清”盖过有答案的原文。可采用关键词精确匹配与语义检索结合，再重排。',
              '3. 阈值按问题类型校准：本次源记录接近0.12却被过滤，可测试低阈值回退；不能只全局降低阈值，否则无关材料也会进入上下文。',
              '4. 给旅程事件建简短事实账本：谁在何时何地执行了什么、取得什么、向谁说过什么，明确“生成叙述”与“本地已执行”。',
              '5. 将角色动机、风险偏好、表达习惯分开；允许闲谈、幽默、误解和情绪推进，减少所有人都像核验文书的倾向。',
              '6. 地图移动使用距离、交通方式与停留时间；否则6个游戏日走完跨洲旅程会破坏后续天气、补给、日程逻辑。', '',
              '本次只添加测试与报告脚本，没有在途中修改生产检索、提示词或状态规则，以保留可比较的基线。']
    lines += ['', '## 错误记录', '', '```json', json.dumps(m['errors'],ensure_ascii=False,indent=2), '```', '',
              '## 文件', '',
              '- `旅行对话全文.md`：逐轮玩家输入与实际生成正文。',
              '- `长历史续写对照.md`：终点默认与完整原文的剧情续写。',
              '- `逐次调用.csv`、`metrics.json`：可继续分析的统计。',
              '- `manifest.json`：轮次状态、对照预期与实际答案。',
              '- `calls/`：逐次请求/原始响应/usage/耗时，未保存授权请求头。',
              '- `test.sqlite3`、`StoryPackage/`：隔离测试存档和故事包。']
    (out/'测试报告.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
