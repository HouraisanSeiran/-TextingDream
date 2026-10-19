"""Combine immutable experiment outputs and export a standalone chart/report."""
import gzip
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.analyze_million_context import content_answer
from tools.million_context_benchmark import grade

out=ROOT/'artifacts/million_context_20260917'
analysis=json.loads((out/'analysis.json').read_text(encoding='utf-8'))
with gzip.open(out/'prompts/1000000_73101.json.gz','rt',encoding='utf-8') as f:expected=json.load(f)['expected']
cache=[]
for name in ('repeat_1','repeat_2','next_turn'):
    r=json.loads((out/'cache'/(name+'.json')).read_text(encoding='utf-8'))
    r['content_checks']=grade(content_answer(r.get('answer'),expected),expected)
    cache.append(r)
totals=dict(analysis['totals'])
for r in cache:
    for k in totals:totals[k]+=r['usage'].get(k,0)
cache_summary=[{'id':r['id'],'usage':r['usage'],'elapsed_ms':r['elapsed_ms'],
                'content_correct':sum(r['content_checks'].values()),'fields':len(r['content_checks']),
                'wrong':[k for k,v in r['content_checks'].items() if not v]} for r in cache]
(out/'final_summary.json').write_text(json.dumps({'main':analysis,'cache':cache_summary,'total_calls':27,'totals':totals},ensure_ascii=False,indent=2),encoding='utf-8')

plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,3,figsize=(15,4.7),layout='constrained')
for mode,label,color in [(False,'推理关闭','#267aa8'),(True,'推理开启','#cd7532')]:
    gs=[g for g in analysis['groups'] if g['thinking']==mode]
    xs=[g['target_tokens']/1000 for g in gs]
    axes[0].plot(xs,[g['content_rate']*100 for g in gs],marker='o',label=label,color=color,linestyle='-' if not mode else '--')
    axes[1].plot(xs,[g['mean_seconds'] for g in gs],marker='o',label=label,color=color)
    axes[2].plot(xs,[g['mean_output_tokens'] for g in gs],marker='o',label=label,color=color)
for ax in axes:
    ax.set_xscale('log');ax.set_xticks([16,128,512,1000],['16k','128k','512k','1000k']);ax.grid(alpha=.2);ax.set_xlabel('目标输入 token（服务端实际量见报告）')
axes[0].set_ylim(0,105);axes[0].set_title('主测试内容正确率');axes[0].set_ylabel('%')
axes[0].text(.04,.07,'每档每模式 3 次；未检出下降\n额外缓存重放有 1 个字段遗漏',transform=axes[0].transAxes,fontsize=9)
axes[1].set_title('平均完整响应耗时');axes[1].set_ylabel('秒');axes[1].legend()
axes[2].set_title('平均输出 token（含推理）');axes[2].set_ylabel('token')
fig.suptitle('DeepSeek V4.1 Flash：合成档案长上下文实测；不是内部注意力或小说质量评测',fontsize=12)
fig.savefig(out/'百万上下文对照.png',dpi=170)
fig.savefig(out/'百万上下文对照.svg')
plt.close(fig)

lines=['# 织梦：百万上下文实测结论','',
       '2026-09-17，模型 DeepSeek V4.1 Flash（deepseek-flash）。27 次真实请求全部完成：24 次长度/推理对照 + 3 次缓存与续聊探测。','',
       '**确实测试到了百万 token 输入：998648–1002310 token。主测试未检出内容正确率随长度下降；额外一次缓存重放漏掉1个字段。不能据此宣称百万剧情绝不遗忘。**','',
       '## 长度与消耗','',
       '|目标上下文|每轮实际输入范围|关闭推理：平均输出 / 秒|开启推理：平均输出 / 秒|内容正确率（关 / 开）|',
       '|---:|---:|---:|---:|---:|']
for size in (16000,128000,512000,1000000):
    a,b=[g for g in analysis['groups'] if g['target_tokens']==size]
    lines.append(f"|{size:,}|{min(a['input_min'],b['input_min']):,}–{max(a['input_max'],b['input_max']):,}|{a['mean_output_tokens']:.0f} / {a['mean_seconds']:.1f}|{b['mean_output_tokens']:.0f} / {b['mean_seconds']:.1f}|{a['content_rate']:.1%} / {b['content_rate']:.1%}|")
lines+=['','输出包含供应商返回的推理 token；输入与输出分别统计，不把思考重复相加。请求耗时包括网络上传、排队、预填充和生成。',
        '每档3个独立种子、推理开关各一次，合计6次；每次31个检查字段。主测试744/744个内容字段正确、24/24个完整响应内容全对。五处暗号/天数/真伪/出处合计480/480正确；跨段关联、首次事件、最新事实和知情边界在本组任务中也正确。',
        '相对1.6万档，百万档内容准确率变化为0个百分点（本样本）；关闭推理耗时约增加到12.7倍，开启推理约1.9倍。开启推理没有在这组任务上提升内容正确率，却明显增加输出和等待。',
        '严格逐字分数与内容分数不同：模型会多带“肉/白粥”或省略“商人”称谓，原严格分保留在report.md。后处理只归一这三种明确前缀，规则和单元测试见tools/analyze_million_context.py、tests/test_million_benchmark.py；没有宽松匹配数字、暗号或出处。','',
        '## 百万历史重复发送与下一轮','',
        '|请求|输入 token|缓存命中|未命中|命中率|输出|耗时秒|内容正确字段|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
baseline=json.loads((out/'results/1000000_73101_False.json').read_text(encoding='utf-8'))
for label,r in [('首次该百万资料',baseline)]+list(zip(['同请求重放1','同请求重放2','追加助手回答与下一轮问题'],cache)):
    u=r['usage'];checks=r.get('content_checks',grade(content_answer(r.get('answer'),expected),expected))
    lines.append(f"|{label}|{u['prompt_tokens']:,}|{u['prompt_cache_hit_tokens']:,}|{u['prompt_cache_miss_tokens']:,}|{u['prompt_cache_hit_tokens']/u['prompt_tokens']:.3%}|{u['completion_tokens']}|{r['elapsed_ms']/1000:.2f}|{sum(checks.values())}/{len(checks)}|")
lines+=['',
        '缓存重放1把开头记录中明确的“封路4天”回答成null；暗号和来源仍正确。这是一次实际遗漏，不能隐藏，也不能断言由缓存引起：没有足够控制实验区分长上下文、服务端数值差异、解码等原因。温度0也未保证每次输出一致。',
        '追加一轮仍发送约99.9万输入token，而不是只发新增文本。缓存仅让绝大部分输入按命中价格计费。本次热前缀命中率约99.98%，不保证换模型/改前缀/过期后仍命中。长度对照阶段同内容立即切推理开关仍主要未命中，不能根据一次热缓存结果推广所有调用。','',
        '## 合计与按公开价格示例','',
        '本次27次请求服务端实际用量：'+json.dumps(totals,ensure_ascii=False),'',
        '按本次查询到的官方美元峰时单价：缓存命中$0.006/百万输入、未命中$0.30/百万输入、输出$1.20/百万；谷时为一半。仅作单价示例，不是账户扣款核对或人民币报价。',]
for label,r in [('首次百万输入',baseline),('热缓存重放',cache[1]),('追加下一轮',cache[2])]:
    u=r['usage'];peak=(u['prompt_cache_hit_tokens']*.006+u['prompt_cache_miss_tokens']*.30+u['completion_tokens']*1.20)/1000000
    lines.append(f'- {label}：峰时约 ${peak:.6f}；谷时约 ${peak/2:.6f}。')
peak=(totals['prompt_cache_hit_tokens']*.006+totals['prompt_cache_miss_tokens']*.30+totals['completion_tokens']*1.20)/1000000
lines+= [f'- 全部27次：若全部峰时约 ${peak:.4f}；若全部谷时约 ${peak/2:.4f}。实际取决于时段与账户账单。','',
         '## 对织梦的建议','',
         '1. 百万窗口可作为完整档案查证或阶段性整理的可选模式。日常对话仍保留当前状态、近期历史、按需原文检索；暂不把整份百万历史自动放进每轮。',
         '2. 如果需要超长连续聊天，稳定资料置前、严格追加新轮次，记录每次实际cache_hit而不是假定一定命中；更换推理配置可能改变缓存行为。',
         '3. 这组证据查询不需要默认高强度推理；复杂剧情冲突与角色动机再单独测试。不能把本组低推理成本优势推广到所有创作。',
         '4. “注意力”下一阶段用真实多人物长剧情、同名实体、跨章因果、隐藏知识和软约束逐项评测。这次重复句式较多且查询目标清晰，任务存在天花板效应。',
         '5. 不把缓存降低价格理解成不占上下文；输出也要保留空间，模型总窗口接近上限时需要归档/检索。','',
         '## 范围与复现','',
         '测试绕过当前应用40000字符预算，直接向同一DeepSeek接口发送完整资料；未扩大正式应用默认预算，未修改正式故事包或玩家存档。内容为合成中文记录，包含反复句式，因此不能等同百万token真实小说。API无法读取内部attention，本次只测行为代理指标。',
         '主测试各格仅3次，正确字段不是独立样本，没有足够统计功效证明无退化；额外缓存用例也不是独立的第四种子。',
         '原请求（gzip）、全部回答、推理、用量、严格判分、内容判分和CSV都在本文件同目录；不含密钥。脚本可按既有结果断点续跑，不会默默重试已记录请求。',
         '官方规格/价格：https://api-docs.deepseek.com/quick_start/pricing','',
         '![上下文长度对照](百万上下文对照.png)','']
(out/'百万上下文测试结论.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'calls':27,'totals':totals,'report':str(out/'百万上下文测试结论.md')},ensure_ascii=False))
