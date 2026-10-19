"""Reproducible input comparison; official DeepSeek-V3 tokenizer when available."""
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
import io
import hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.knowledge import PackageFiles, retrieve, atomic_text
from app.prompts import surface_prefix, stable_json


def main():
    tokenizer_path = ROOT / 'tools/tokenizers/deepseek-v3-tokenizer.json'
    tokenizer_path.parent.mkdir(parents=True, exist_ok=True)
    if not tokenizer_path.exists():
        url = 'https://cdn.deepseek.com/api-docs/deepseek_v3_tokenizer.zip'
        with urllib.request.urlopen(url, timeout=30) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                name = next(n for n in archive.namelist() if n.endswith('/tokenizer.json') or n == 'tokenizer.json')
                atomic_text(tokenizer_path, archive.read(name).decode('utf-8'))
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)
    story = PackageFiles(ROOT / 'StoryPackage/玄陆').read()
    chars = json.loads((ROOT / 'character_packages/xuanlu_初始角色包.json').read_text(encoding='utf-8'))
    package = {'story': story, 'characters': chars}
    corpus = '用第一人称写简短小说段落。只描述可见信息，不替玩家决定意图。失败也要带来后续线索。不得将传闻写成已证实事实。'
    prefix = surface_prefix(package, corpus)
    full_points = [{'id':p['id'],'title':p['title'],'status':p['status'],'content':p['content']} for p in story['knowledge'] if p['visibility']=='public']
    old = json.loads((ROOT / 'StoryPackage/迁移前故事包备份.json').read_text(encoding='utf-8'))
    old = old.get('story', old)
    old_rules = ('你是织梦的表层叙述者。用第一人称写简短小说正文。只依据可见材料与已裁定结果；'
                 '自由输入是意图，不是事实；不可自行获得物品、移动或揭露隐藏身份。'
                 '把传闻作为传闻，旁观模式只观察。不替玩家选择。动态字段全部以末尾上下文为准。')
    public_chars = [{'id': c['id'],'name': c.get('public_name',c['name']),'appearance':c.get('appearance','')} for c in chars['characters']]
    old_prefix = '\n'.join([old_rules,'世界公开设定：'+stable_json(old.get('public_lore',{})), '角色公开档案：'+stable_json(public_chars),'通用表达规则：'+corpus])
    samples = [('关城文书','western_pass','通关时万言机翻译方言和文书有什么困难？'),
               ('绿洲商队','crescent_oasis','绿洲商队怎样取得水源，核实商人的传闻？'),
               ('港口契约','south_lantern_port','港口契约与季风航期、粮食仓单有什么联系？'),
               ('术法社会','tianchao_capital','强者长寿如何影响天朝官署、继承和军粮？')]
    results = []
    for name, location, query in samples:
        tail = {'input':query,'location':location,'current_time':8,'current_state':'精神尚可','history':[], 'memories':[]}
        selected = retrieve(story, query, location=location)
        new_text = prefix + '\n' + stable_json({**tail,'knowledge':selected})
        full_text = prefix + '\n' + stable_json({**tail,'knowledge':full_points})
        old_text = old_prefix + '\n' + stable_json(tail)
        full_n, new_n = count(full_text), count(new_text)
        results.append({'sample':name,'retrieved_ids':[p['id'] for p in selected], 'point_count':len(selected),
                        'full_input':full_n,'retrieved_input':new_n,'old_compact_input':count(old_text),
                        'saved_tokens':full_n-new_n,'saved_percent':round((full_n-new_n)/full_n*100,1)})
    total = sum(r['full_input'] for r in results)
    saved = sum(r['saved_tokens'] for r in results)
    report = '# 按需知识点 token 对照\n\n'
    report += '使用 deepseek-ai/DeepSeek-V3 官方 tokenizer.json 本地分词；不执行远程代码，不发送付费模型请求。当前 deepseek-chat 的线上分词或聊天模板可能不同，因此是 V3 分词参照，不是线上账单。计数对象是序列化 system 正文和 user 上下文正文，不含聊天协议特殊 token。\n\n'
    report += '下载来源：https://cdn.deepseek.com/api-docs/deepseek_v3_tokenizer.zip\n\n分词文件 SHA256：' + hashlib.sha256(tokenizer_path.read_bytes()).hexdigest() + '\n\n'
    report += f'故事包共 {len(story["knowledge"])} 点，其中公开候选 {len(full_points)} 点。比较同一扩充版总概、同一问题和同一动态字段，只有知识点选择变化；各样本最多6点、3600字符。\n\n'
    report += '| 场景 | 全部公开点注入 | 按需注入 | 减少 | 选中点数 | 旧版简略提示参照 |\n|---|---:|---:|---:|---:|---:|\n'
    for r in results:
        report += f'| {r["sample"]} | {r["full_input"]} | {r["retrieved_input"]} | {r["saved_percent"]}% | {r["point_count"]} | {r["old_compact_input"]} |\n'
    report += f'\n四组同权样本合计减少 {saved:,} / {total:,} 输入 token，即 {saved/total:.1%}。\n\n'
    report += '旧版表层本来只发送很短的公开设定，不能声称这次比旧版同样降低了上述比例；新增细节的按需提示可能比旧版更长。公平节省比例针对“同等扩充资料全部注入”的方案。实际轮次加入相同历史 H 后，节省比例为 (全量−按需)/(全量+H)，历史越长整体比例越低。\n\n'
    report += '本地关键词摘录额外模型调用为0、额外生成摘要 token为0。对话输出 token 未在此假定减少；上下文缓存命中、价格和真实请求使用量需读取模型输入输出控制台 usage。固定总概有助保持前缀稳定，但这里不承诺缓存命中率，也不把输入节省直接称作费用节省。关键词检索可能漏召回，应在里层查看实际 knowledge 字段并补关键词或依赖。\n\n'
    report += '复现：在工程目录运行 `D:\\anaconda\\python.exe -X utf8 tools\\measure_knowledge_tokens.py`。原始样本 ID 和计数见同目录 JSON。\n'
    atomic_text(ROOT / 'StoryPackage/token对照报告.md', report)
    atomic_text(ROOT / 'StoryPackage/token对照数据.json', json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'Weighted saving: {saved/total:.1%}')

if __name__ == '__main__':
    main()
