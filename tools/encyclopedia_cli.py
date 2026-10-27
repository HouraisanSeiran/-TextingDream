# -*- coding: utf-8 -*-
"""人类生产生活百科 · 命令行工具（只读写显式指定的独立 SQLite 库）。

用法要点：

* **必须**用 ``--db`` 指定库文件路径。本工具没有默认库位置，也不在 app 启动时
  自动建库/填库；正式库由主代理验收后另行生成。
* 查询类子命令（search / get / versions / tags / stats / export）以只读方式打开
  数据库，不会顺带建库；``import`` / ``restore`` / ``init`` 才会创建文件与 schema。
* 退出码：0 成功；1 领域错误（校验失败、找不到、冲突、超限）；2 参数用法错误。

示例::

    python -m tools.encyclopedia_cli import --db temp.sqlite3 docs/human-encyclopedia/staples.json
    python -m tools.encyclopedia_cli search --db temp.sqlite3 --text 小麦 --tag cereal
    python -m tools.encyclopedia_cli get --db temp.sqlite3 staples_wheat --version 1
    python -m tools.encyclopedia_cli export --db temp.sqlite3 --out dump.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import encyclopedia as enc  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1


def _emit(payload, as_json):
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=False)
        sys.stdout.write('\n')
        return
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def _text_lines(lines):
    for line in lines:
        sys.stdout.write(line + '\n')


# --------------------------------------------------------------------------- 命令
def cmd_init(args):
    conn = enc.open_writable(args.db)
    try:
        version = enc.read_schema_version(conn)
    finally:
        conn.close()
    _emit({'db': str(args.db), 'schema_version': version, 'created': True}, args.json)
    return EXIT_OK


def cmd_import(args):
    results = []
    for path in args.files:
        result = enc.import_file(args.db, path, namespace=args.namespace, adapter=args.adapter)
        results.append(result.as_dict())
    if args.json:
        _emit(results, True)
        return EXIT_OK
    lines = []
    for item in results:
        lines.append('%s [%s] 批次 %d：元素 %d（新版本 %d / 未变 %d），来源 %d（新版本 %d / 未变 %d）'
                     % (item['namespace'], item['adapter'], item['batch_id'], item['elements'],
                        item['element_versions_written'], item['unchanged_elements'],
                        item['sources'], item['source_versions_written'], item['unchanged_sources']))
        if item['idempotent']:
            lines.append('  重复批次：零写入（批次哈希已存在）')
        if item['unresolved_relations']:
            lines.append('  未解析关联 %d 条（目标尚未入库，状态 pending）' % len(item['unresolved_relations']))
        if item['ambiguous_relations']:
            lines.append('  歧义关联 %d 条（目标存在于多个命名空间）' % len(item['ambiguous_relations']))
        if item['shared_element_ids']:
            lines.append('  与其他命名空间同 ID 的条目 %d 条（按命名空间隔离，未覆盖）' % len(item['shared_element_ids']))
    _text_lines(lines)
    return EXIT_OK


def cmd_search(args):
    page = enc.search(
        args.db,
        text=args.text,
        tags_any=args.tag,
        tags_all=args.all_tag,
        namespace=args.namespace,
        group_id=args.group,
        review_status=args.review_status,
        detail_status=args.detail_status,
        limit=args.limit,
        offset=args.offset,
        include_payload=args.with_payload,
    )
    if args.json:
        _emit(page, True)
        return EXIT_OK
    _text_lines([
        '命中 %d 条，本页 %d 条（offset=%d，limit=%d，还有更多：%s）'
        % (page['total'], page['returned'], page['offset'], page['limit'], '是' if page['has_more'] else '否')
    ])
    for item in page['items']:
        _text_lines([
            '- %s/%s v%d %s  [%s | %s]'
            % (item['namespace'], item['element_id'], item['version'], item['name'],
               item['review_status'], item['detail_status']),
            '  标签：%s' % ', '.join(item['tags']),
        ])
        if item['aliases']:
            sys.stdout.write('  别名：%s\n' % ' / '.join(item['aliases']))
    return EXIT_OK


def cmd_get(args):
    item = enc.get(args.db, args.element_id, namespace=args.namespace,
                   version=args.version, include_payload=not args.no_payload)
    if args.json:
        _emit(item, True)
        return EXIT_OK
    lines = [
        '%s/%s v%d（当前版本 v%d%s）'
        % (item['namespace'], item['element_id'], item['version'], item['current_version'],
           '' if item['is_current'] else '，非当前'),
        '名称：%s' % item['name'],
        '别名：%s' % (' / '.join(item['aliases']) if item['aliases'] else '（无）'),
        '标签：%s' % ', '.join(item['tags']),
        '状态：review_status=%s detail_status=%s（只记录原值，本工具不升格）'
        % (item['review_status'], item['detail_status']),
        '适配：adapter=%s legacy_schema=%s' % (item['adapter'], item['legacy_schema']),
        '摘要：%s' % (item['summary'] or '（无）'),
        '七节：',
    ]
    for section in enc.DETAIL_SECTIONS:
        body = item['details'].get(section)
        mapped = item['details_map'].get(section)
        note = '' if mapped in (None, section) else '（原字段 %s）' % mapped
        lines.append('  [%s]%s\n    %s' % (section, note, body or '（缺）'))
    if item['details_extra']:
        lines.append('额外分节：%s' % ', '.join(sorted(item['details_extra'])))
    lines.append('来源：')
    for source in item['sources']:
        stale = '' if source.get('is_current_source_version', True) else '，来源已有更新版本，但此证据版本固定不变'
        lines.append('  - %s v%s (%s, status=%s) %s | %s%s'
                     % (source['source_id'], source['source_version'], source['source_namespace'],
                        source['status'], source['title'] or '', source['access'] or '', stale))
    if item['relations']:
        lines.append('关联：')
        for relation in item['relations']:
            lines.append('  - %s → %s [%s]%s'
                         % (relation['rel_kind'], relation['target_id'], relation['status'],
                            '' if relation['status'] == 'resolved'
                            else '（尚未解析，不是有效关联）'))
    if args.no_payload:
        lines.append('原始 payload：未显示（--no-payload）')
    _text_lines(lines)
    return EXIT_OK


def cmd_versions(args):
    data = enc.versions(args.db, args.element_id, namespace=args.namespace)
    if args.json:
        _emit(data, True)
        return EXIT_OK
    lines = ['%s/%s 共 %d 个版本（当前 v%d）'
             % (data['namespace'], data['element_id'], len(data['versions']), data['current_version'])]
    for row in data['versions']:
        lines.append('  v%d %s hash=%s [%s | %s] 批次 %d %s'
                     % (row['version'], '←当前' if row['is_current'] else '    ', row['content_hash'][:12],
                        row['review_status'], row['detail_status'], row['batch_id'], row['created_at']))
    _text_lines(lines)
    return EXIT_OK


def cmd_tags(args):
    data = enc.list_tags(args.db, namespace=args.namespace, limit=args.limit, offset=args.offset)
    if args.json:
        _emit(data, True)
        return EXIT_OK
    _text_lines(['共 %d 个标签（本页 %d）' % (data['total'], len(data['tags']))])
    for row in data['tags']:
        sys.stdout.write('  %-32s %d\n' % (row['tag'], row['count']))
    return EXIT_OK


def cmd_stats(args):
    data = enc.stats(args.db, namespace=args.namespace)
    if args.json:
        _emit(data, True)
        return EXIT_OK
    totals = data['totals']
    lines = ['schema_version=%d 组 %d，元素 %d，元素版本 %d，来源 %d，来源版本 %d，未解析关联 %d'
             % (data['schema_version'], totals['groups'], totals['elements'], totals['element_versions'],
                totals['sources'], totals['source_versions'], totals['unresolved_relations'])]
    for group in data['groups']:
        lines.append('  %s（%s）元素 %d / 版本 %d / 来源 %d / 标签 %d / 批次 %d / 未解析关联 %d'
                     % (group['namespace'], group['adapter'], group['elements'], group['element_versions'],
                        group['sources'], group['tags'], group['batches'], group['unresolved_relations']))
        lines.append('    review_status=%s' % group['review_status'])
        lines.append('    detail_status=%s' % group['detail_status'])
    _text_lines(lines)
    return EXIT_OK


def cmd_export(args):
    document = enc.export_document(args.db, namespaces=args.namespace or None)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=1, sort_keys=False) + '\n', encoding='utf-8')
    summary = {'db': str(args.db), 'out': str(out), 'counts': document['counts']}
    if args.json:
        _emit(summary, True)
        return EXIT_OK
    _text_lines(['已导出到 %s：组 %d，来源版本 %d，元素版本 %d'
                 % (out, document['counts']['groups'], document['counts']['source_versions'],
                    document['counts']['element_versions'])])
    return EXIT_OK


def cmd_restore(args):
    result = enc.restore_file(args.db, args.file)
    if args.json:
        _emit(result.as_dict(), True)
        return EXIT_OK
    _text_lines(['已从 %s 还原：元素 %d（新版本 %d / 未变 %d），来源 %d（新版本 %d / 未变 %d）'
                 % (args.file, result.elements, result.element_versions, result.unchanged_elements,
                    result.sources, result.source_versions, result.unchanged_sources)])
    if result.unresolved_relations:
        sys.stdout.write('未解析关联 %d 条（目标不在本导出里）\n' % len(result.unresolved_relations))
    return EXIT_OK


# --------------------------------------------------------------------------- 入口
def build_parser():
    parser = argparse.ArgumentParser(
        prog='encyclopedia_cli',
        description='人类生产生活百科 · 独立 SQLite 素材库命令行（必须用 --db 指定库路径）',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    def add_db(p):
        p.add_argument('--db', required=True, help='SQLite 库文件路径（必填，无默认位置）')
        p.add_argument('--json', action='store_true', help='以 JSON 输出结果')

    p_init = sub.add_parser('init', help='显式创建空库与 schema（不导入数据）')
    add_db(p_init)
    p_init.set_defaults(func=cmd_init)

    p_import = sub.add_parser('import', help='整批原子导入采集 JSON')
    add_db(p_import)
    p_import.add_argument('files', nargs='+', help='采集 JSON 文件（docs/human-encyclopedia 或 element-catalog）')
    p_import.add_argument('--namespace', default=None, help='覆盖命名空间（默认取文档 group）')
    p_import.add_argument('--adapter', default=None, choices=list(enc.ADAPTERS),
                          help='强制 adapter（默认按元素形状识别）')
    p_import.set_defaults(func=cmd_import)

    p_search = sub.add_parser('search', help='中文名/别名 + 多标签 AND/OR 检索')
    add_db(p_search)
    p_search.add_argument('--text', default=None, help='名称或别名子串（中文可直接用）')
    p_search.add_argument('--tag', action='append', default=[], help='标签 OR 组，可重复')
    p_search.add_argument('--all-tag', action='append', default=[], help='标签 AND 组，可重复')
    p_search.add_argument('--namespace', default=None)
    p_search.add_argument('--group', default=None, help='按 group_id 过滤')
    p_search.add_argument('--review-status', default=None)
    p_search.add_argument('--detail-status', default=None)
    p_search.add_argument('--limit', type=int, default=enc.DEFAULT_PAGE_SIZE)
    p_search.add_argument('--offset', type=int, default=0)
    p_search.add_argument('--with-payload', action='store_true', help='结果里带原始 payload')
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser('get', help='单项详情（可指定历史版本）')
    add_db(p_get)
    p_get.add_argument('element_id')
    p_get.add_argument('--namespace', default=None)
    p_get.add_argument('--version', type=int, default=None)
    p_get.add_argument('--no-payload', action='store_true', help='不打印原始 payload')
    p_get.set_defaults(func=cmd_get)

    p_versions = sub.add_parser('versions', help='列出某条目的全部不可变版本')
    add_db(p_versions)
    p_versions.add_argument('element_id')
    p_versions.add_argument('--namespace', default=None)
    p_versions.set_defaults(func=cmd_versions)

    p_tags = sub.add_parser('tags', help='列出标签及条目数')
    add_db(p_tags)
    p_tags.add_argument('--namespace', default=None)
    p_tags.add_argument('--limit', type=int, default=enc.MAX_PAGE_SIZE)
    p_tags.add_argument('--offset', type=int, default=0)
    p_tags.set_defaults(func=cmd_tags)

    p_stats = sub.add_parser('stats', help='库统计')
    add_db(p_stats)
    p_stats.add_argument('--namespace', default=None)
    p_stats.set_defaults(func=cmd_stats)

    p_export = sub.add_parser('export', help='导出全部版本为 JSON')
    add_db(p_export)
    p_export.add_argument('--out', required=True, help='输出 JSON 文件路径')
    p_export.add_argument('--namespace', action='append', default=[], help='只导出指定命名空间，可重复')
    p_export.set_defaults(func=cmd_export)

    p_restore = sub.add_parser('restore', help='把导出文件再导入（保留原版本号）')
    add_db(p_restore)
    p_restore.add_argument('file')
    p_restore.set_defaults(func=cmd_restore)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except enc.Ambiguous as exc:
        sys.stderr.write('歧义：%s\n' % exc)
        return EXIT_ERROR
    except enc.EncyclopediaError as exc:
        sys.stderr.write('拒绝：%s\n' % exc)
        return EXIT_ERROR
    except FileNotFoundError as exc:
        sys.stderr.write('文件不存在：%s\n' % exc)
        return EXIT_ERROR
    except OSError as exc:
        sys.stderr.write('I/O 错误：%s\n' % exc)
        return EXIT_ERROR


if __name__ == '__main__':
    raise SystemExit(main())
