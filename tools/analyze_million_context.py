"""Post-hoc content scores alongside unchanged exact-match scores.

Only explicit noun/title prefixes normalize; no fuzzy or model-based grading.
"""
import copy
import gzip
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/million_context_20260917'


def content_answer(answer, expected):
    if not isinstance(answer,dict):return answer
    value=copy.deepcopy(answer)
    for group,key,prefix in [('chain','receiver','商人'),('first_meal','meat','肉'),('first_meal','porridge','白粥')]:
        part=value.get(group)
        if not isinstance(part,dict):continue
        got=part.get(key);want=expected[group][key]
        if isinstance(got,str) and isinstance(want,str):
            if got==prefix+want or prefix+got==want:part[key]=want
    return value


def main():
    import sys
    sys.path.insert(0,str(ROOT))
    from tools.million_context_benchmark import grade
    rows=[]
    for file in sorted((OUT/'results').glob('*.json')):
        r=json.loads(file.read_text(encoding='utf-8'))
        with gzip.open(OUT/'prompts'/f"{r['target_tokens']}_{r['seed']}.json.gz",'rt',encoding='utf-8') as f:expected=json.load(f)['expected']
        r['content_checks']=grade(content_answer(r.get('answer'),expected),expected)
        rows.append(r)
    lines=['# 百万上下文结果解读','',
        '模型：DeepSeek V4.1 Flash（deepseek-flash）。测试为合成档案，不能直接代表小说质量或内部注意力权重。','',
        '计分保留原严格逐字分数。另列内容分：仅允许签收人省略“商人”、评价多带“肉”或“白粥”前缀；这是发现基线格式差异后明确加入的后处理，所有长度同样使用，不修改原始结果。随机暗号、数字、真假、来源、链条顺序一律不宽松匹配。','',
        '|目标token|推理|请求数/成功|实际输入token范围|逐字正确率|内容正确率|内容全对请求|平均输出token|平均耗时秒|',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    groups=[]
    for target,thinking in sorted({(r['target_tokens'],r['thinking']) for r in rows}):
        rs=[r for r in rows if r['target_tokens']==target and r['thinking']==thinking]
        tokens=[r['usage']['prompt_tokens'] for r in rs if r['usage'].get('prompt_tokens')]
        outputs=[r['usage']['completion_tokens'] for r in rs if r['usage'].get('completion_tokens') is not None]
        n=sum(len(r['checks']) for r in rs);exact=sum(sum(r['checks'].values()) for r in rs);content=sum(sum(r['content_checks'].values()) for r in rs)
        g={'target_tokens':target,'thinking':thinking,'attempts':len(rs),'completed':sum(r['status']=='completed' for r in rs),
           'input_min':min(tokens) if tokens else None,'input_max':max(tokens) if tokens else None,
           'exact_correct':exact,'content_correct':content,'fields':n,'content_rate':content/n,
           'content_perfect_calls':sum(all(r['content_checks'].values()) and r['status']=='completed' for r in rs),
           'mean_output_tokens':statistics.mean(outputs) if outputs else None,'mean_seconds':statistics.mean(r['elapsed_ms']/1000 for r in rs)}
        groups.append(g)
        lines.append(f"|{target}|{thinking}|{len(rs)}/{g['completed']}|{g['input_min']}–{g['input_max']}|{exact/n:.1%}|{content/n:.1%}|{g['content_perfect_calls']}/{len(rs)}|{round(g['mean_output_tokens'] or 0)}|{g['mean_seconds']:.1f}|")
    lines+=['','## 内容错误逐项','']
    for r in rows:
        wrong=[k for k,v in r['content_checks'].items() if not v]
        if wrong:lines.append(f"- {r['id']}：{r['status']}，错误：{', '.join(wrong)}。{r.get('error','')}")
    totals={k:sum(r['usage'].get(k,0) or 0 for r in rows) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')}
    lines+=['','已报告token总量：'+json.dumps(totals,ensure_ascii=False),'',
        '所有字段正确率是描述统计，不能把同一回复的31个字段当31次独立实验。每格只有3个种子。位置、失败、原始响应和实际长度见report.md、calls.csv、results目录。',
        '模式顺序交替，可能有缓存复用；推理开启high，关闭时温度0，属于运行配置比较。时间包括上传、排队、预填充和生成，不能当纯推理延迟。',
        '不存在注意力下降的预设结论：如百万档找回率没有降低，只能说本组任务未检出下降；若短基线已答错，也需与长度效应区分。']
    (OUT/'analysis.json').write_text(json.dumps({'groups':groups,'totals':totals,'calls':len(rows)},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'结果解读.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'groups':groups,'totals':totals,'calls':len(rows)},ensure_ascii=False))


if __name__=='__main__':main()
