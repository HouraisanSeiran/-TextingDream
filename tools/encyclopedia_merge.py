# -*- coding: utf-8 -*-
"""把新采集条目“归并”到已存在元素上，而不是新建重复元素。

为什么需要它：用户要求「如果有重合的就在同一药材（美食）元素上添加对应词条」。
即西方草药、法餐、英菜里那些与已有粮食/蔬果/香料/生物重合的项，不应该多出一条
重复元素，而应该成为原元素的**补充词条**（新版本），仍可溯源。

做法（只改源 JSON，不动库，不碰引擎）：

1. 按名字/别名匹配已存在元素（全角括号内的限定语会被忽略：“胡椒（黑胡椒）”≡“胡椒”）。
2. 命中则在目标元素的指定分节末尾追加一个带标题的【补充条目】块，内容来自候选条目的
   summary 与关键分节（不含剂量、不含任何处方表述——那是采集侧的红线）。
3. 把候选条目的检索标签（仅 part:/trait:/role:/trade:/effect:/habitat: 前缀）并到目标；
   目标仍是旧 schema（元素没有 tags）时**不加标签**，因为引擎会丢弃旧 schema 的原生标签。
4. 在目标元素上追加 merged_from（形如 “组名/元素 id”）保留归并来源。
5. 未命中的候选条目不处理——它们该留在自己的新分区里。

默认 **dry-run**，只打印计划；确认后用 ``--apply`` 才写文件。写入时保留原文件的缩进风格，
避免整文件重排造成无法审阅的 diff。

退出码：0 成功（含“无需归并”）；1 领域错误；2 用法错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 允许作为“归并目标”的已有源文件（显式名单，不用通配：同目录有聚类索引与候选文件）。
TARGET_FILES = (
    'docs/human-encyclopedia/staples.json',
    'docs/human-encyclopedia/produce.json',
    'docs/human-encyclopedia/flavors.json',
    'docs/human-encyclopedia/animal-foods.json',
    'docs/human-encyclopedia/materials.json',
    'docs/human-encyclopedia/tools.json',
    'docs/human-encyclopedia/food-supplement.json',
    'docs/human-encyclopedia/craft-supplement.json',
    'docs/human-encyclopedia/cuisine.json',
    'docs/element-catalog/eastern.json',
    'docs/element-catalog/western.json',
    'docs/element-catalog/society.json',
    'docs/element-catalog/steam-horror.json',
    'docs/element-catalog/reality-physical.json',
    'docs/element-catalog/reality-human.json',
    'docs/element-catalog/fantasy-races.json',
    'docs/element-catalog/western-biology.json',
    'docs/element-catalog/eastern-biology.json',
    'docs/element-catalog/western-alchemy.json',
    'docs/element-catalog/eastern-alchemy.json',
)

# 只并这些前缀的检索标签：体裁与类别由导入器派生，traditional 维度也不能一元素标两个。
MERGE_TAG_PREFIXES = ('part:', 'trait:', 'role:', 'trade:', 'effect:', 'habitat:', 'origin:', 'taxon:', 'source_text:')
DETAIL_KEYS = ('definition', 'mechanism', 'conditions', 'exceptions',
               'story_uses', 'historical_scope', 'evidence_and_uncertainty')

_PARENS = re.compile(r'[（(][^）)]*[）)]')


def merge_key(text):
    """比较用的归一化：去全角括号限定语、去空白与间隔号、小写。"""
    if not isinstance(text, str):
        return ''
    return _PARENS.sub('', text).replace(' ', '').replace('　', '').replace('·', '').lower().strip()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def detect_indent(path, default=2):
    """看文件里第一行缩进，尽量沿用原风格，避免整文件重排。"""
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines()[1:8]:
        stripped = line.lstrip()
        if stripped and len(line) - len(stripped) in (2, 4):
            return len(line) - len(stripped)
    return default


def build_index(targets):
    """归一化名字/别名 → （文件, 元素所在列表下标）。先扫目标文件，再扫其他已有组。"""
    index = {}
    for relative in targets:
        path = ROOT / relative
        if not path.is_file():
            continue
        document = load(path)
        for position, element in enumerate(document.get('elements') or []):
            for key in [element.get('name')] + list(element.get('aliases') or []):
                normalized = merge_key(key)
                if normalized:
                    index.setdefault(normalized, []).append((relative, position, element.get('id')))
    return index


def supplement_block(candidate, group):
    """要追加到目标元素上的【补充条目】块。只取概要，不复制整篇详情。"""
    name = candidate.get('name') or candidate.get('id')
    tags = [tag for tag in (candidate.get('tags') or []) if tag.startswith('tradition:')]
    tradition = tags[0].split(':', 1)[1] if tags else 'unknown'
    summary = (candidate.get('summary') or '').strip()
    details = candidate.get('details') or {}
    lines = ['【补充条目：%s｜%s｜%s】' % (name, group, tradition)]
    if summary:
        lines.append(summary)
    for key, label in (('definition', '定义'), ('conditions', '条件'), ('exceptions', '例外')):
        text = (details.get(key) or '').strip()
        if text:
            lines.append('%s：%s' % (label, text))
    note = (details.get('evidence_and_uncertainty') or '').strip()
    if note:
        lines.append('证据与不确定性：%s' % note)
    return '\n'.join(lines)


def plan(candidate_path, section, targets):
    candidate_doc = load(candidate_path)
    group = candidate_doc.get('group') or Path(candidate_path).stem
    index = build_index(targets)
    merges, leftovers = [], []
    for element in candidate_doc.get('elements') or []:
        hit = None
        for key in [element.get('name')] + list(element.get('aliases') or []):
            matches = index.get(merge_key(key))
            if matches:
                hit = matches[0]
                break
        if hit is None:
            leftovers.append(element)
            continue
        merges.append({'candidate': element, 'target_file': hit[0],
                       'target_position': hit[1], 'target_id': hit[2], 'section': section})
    return group, merges, leftovers


def apply_merges(group, merges):
    by_file = {}
    for item in merges:
        by_file.setdefault(item['target_file'], []).append(item)
    written = []
    for relative, items in by_file.items():
        path = ROOT / relative
        document = load(path)
        elements = document.get('elements') or []
        for item in items:
            target = elements[item['target_position']]
            if target.get('id') != item['target_id']:
                raise SystemExit('目标元素位置已变：%s#%s' % (relative, item['target_id']))
            details = target.setdefault('details', {})
            key = item['section']
            if key not in details:
                key = 'story_uses' if 'story_uses' in details else (DETAIL_KEYS[-1] if DETAIL_KEYS[-1] in details else key)
            block = supplement_block(item['candidate'], group)
            current = (details.get(key) or '').rstrip()
            details[key] = (current + '\n\n' + block) if current else block
            # 别名：把候选条目的名字与其别名并进去，方便以后用同一元素检索到。
            # 归一化后与原元素名字相同的不加（否则会多一堆“几乎重复”的别名）。
            aliases = target.setdefault('aliases', [])
            target_key = merge_key(target.get('name'))
            for alias in [item['candidate'].get('name')] + list(item['candidate'].get('aliases') or []):
                if not alias or alias in aliases:
                    continue
                if merge_key(alias) == target_key:
                    continue
                aliases.append(alias)
            # 标签：旧 schema（元素没有 tags 键）不并，因为引擎会丢弃这类原生标签。
            if 'tags' in target:
                existing = list(target.get('tags') or [])
                for tag in item['candidate'].get('tags') or []:
                    if tag.startswith(MERGE_TAG_PREFIXES) and tag not in existing:
                        existing.append(tag)
                target['tags'] = existing
            merged_from = target.setdefault('merged_from', [])
            marker = '%s/%s' % (group, item['candidate'].get('id'))
            if marker not in merged_from:
                merged_from.append(marker)
        indent = detect_indent(path)
        text = json.dumps(document, ensure_ascii=False, indent=indent)
        path.write_text(text + '\n', encoding='utf-8')
        written.append((relative, len(items)))
    return written


def apply_overrides(merges, leftovers, args):
    """按命令行映射与排除表重排归并计划。

    为什么需要：纯名字匹配会把「地龙」撞到「龙」、「何首乌」撞到「灵参」这类
    **名似而实异**的条目，也会把同一实物错并到相邻但不同的元素上。所以默认计划之外
    允许两道人工闸门：

    * ``--map 候选 id=目标文件#目标id``：强制指定归并目标（可多次）。
    * ``--skip-id 候选 id``：强制保留为新元素，不归并（可多次）。

    返回（保留的 merges, 追加上来的 leftovers）。
    """
    forced = {}
    for raw in getattr(args, 'map', None) or ():
        if '=' not in raw:
            raise SystemExit('--map 格式应为 候选id=文件#目标id，得到：%s' % raw)
        source, target = raw.split('=', 1)
        if '#' not in target:
            raise SystemExit('--map 目标应为 文件#元素id，得到：%s' % target)
        relative, target_id = target.rsplit('#', 1)
        forced[source.strip()] = (relative.strip(), target_id.strip())
    skipped = {item.strip() for item in (getattr(args, 'skip_id', None) or ())}
    by_id = {item['candidate'].get('id'): item['candidate'] for item in merges}
    # 把自动计划里被 --map 或 --skip-id 点名的候选移除，再按强制映射重建。
    kept = []
    for item in merges:
        candidate_id = item['candidate'].get('id')
        if candidate_id in skipped:
            leftovers.append(item['candidate'])
            continue
        if candidate_id in forced:
            continue
        kept.append(item)
    pool = {element.get('id'): element for element in leftover_list(leftovers)}
    for candidate_id, (relative, target_id) in forced.items():
        element = by_id.get(candidate_id) or pool.get(candidate_id)
        if element is None:
            raise SystemExit('--map 里点名的候选不存在：%s' % candidate_id)
        position, real_id = locate(relative, target_id)
        kept.append({'candidate': element, 'target_file': relative,
                     'target_position': position, 'target_id': real_id,
                     'section': args.section})
        leftovers = [row for row in leftovers if row.get('id') != candidate_id]
    return kept, leftovers


def leftover_list(leftovers):
    return leftovers


def locate(relative, target_id):
    """拿目标元素在列表里的下标；找不到就报错，不猜。"""
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit('--map 指向的文件不存在：%s' % relative)
    document = load(path)
    for position, element in enumerate(document.get('elements') or []):
        if element.get('id') == target_id:
            return position, target_id
    raise SystemExit('--map 指向的元素不存在：%s#%s' % (relative, target_id))


def drop_merged(candidate_path, merges, dry_run=False):
    """从候选文件里删掉已归并的条目，否则它们在入库时仍会多出一条重复元素。"""
    merged_ids = {item['candidate'].get('id') for item in merges}
    if not merged_ids:
        return 0
    path = Path(candidate_path)
    document = load(path)
    elements = document.get('elements') or []
    kept = [element for element in elements if element.get('id') not in merged_ids]
    removed = len(elements) - len(kept)
    if not kept:
        raise SystemExit('归并后候选文件会变成空文件，拒绝写入：%s' % candidate_path)
    if dry_run:
        return removed
    document['elements'] = kept
    indent = detect_indent(path)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8')
    return removed


def build_parser():
    parser = argparse.ArgumentParser(
        prog='encyclopedia_merge',
        description='把新分区里与已有元素重合的条目，作为【补充条目】并到原元素上（默认 dry-run）')
    parser.add_argument('--candidate', required=True, help='新分区的 JSON（其 elements 会被逐条检查）')
    parser.add_argument('--section', default='story_uses',
                        help='追加到目标元素的哪个详情分节（默认 story_uses）')
    parser.add_argument('--apply', action='store_true', help='真的写入；不给就是 dry-run')
    parser.add_argument('--map', action='append', default=[],
                        help='强制归并：候选id=文件#目标id（可多次）；用于修正名似而实异的误匹配')
    parser.add_argument('--skip-id', action='append', default=[], dest='skip_id',
                        help='强制保留为新元素、不归并（可多次）')
    parser.add_argument('--extra-target', action='append', default=[], dest='extra_target',
                        help='额外的归并目标文件（可多次）')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出计划')
    return parser


def main(argv=None, targets=None):
    args = build_parser().parse_args(argv)
    path = Path(args.candidate)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        sys.stderr.write('候选文件不存在：%s\n' % args.candidate)
        return 1
    targets = tuple(targets or TARGET_FILES) + tuple(args.extra_target or ())
    group, merges, leftovers = plan(path, args.section, targets)
    merges, leftovers = apply_overrides(merges, leftovers, args)
    written = apply_merges(group, merges) if (args.apply and merges) else []
    if args.apply and merges:
        drop_merged(path, merges)
    payload = {
        'group': group,
        'merges': [{'candidate': item['candidate'].get('id'),
                    'target': '%s#%s' % (item['target_file'], item['target_id']),
                    'section': item['section']} for item in merges],
        'leftover_ids': [element.get('id') for element in leftovers],
        'written': written,
        'applied': bool(args.apply),
    }
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')
    else:
        sys.stdout.write('分区 %s：待归并 %d 条，保留为新元素 %d 条\n'
                         % (group, len(merges), len(leftovers)))
        for item in merges:
            sys.stdout.write('   %s → %s#%s（追加到 %s）\n'
                             % (item['candidate'].get('id'), item['target_file'],
                                item['target_id'], item['section']))
        if args.apply:
            for relative, count in written:
                sys.stdout.write('已写入 %s：%d 条归并\n' % (relative, count))
        elif merges:
            sys.stdout.write('（dry-run，未写文件；确认后加 --apply）\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
