# -*- coding: utf-8 -*-
"""元素装配：本地百科库 → 作者逐条选择 → 故事包开局锁定清单。

三层边界（与 ``docs/narrative-element-library.md`` 的「开局锁定」一致）：

1. **库**（``app/encyclopedia.py`` 的独立 SQLite）：候选资料，只读。库里存在 ≠ 世界里有，
   更 ≠ 人物知道。本模块从不写库，也从不改 ``review_status`` / ``detail_status``。
2. **故事包采纳**：作者显式确认后，把 ``namespace/element_id/version/content_hash`` 与
   **完整原始 payload**、固定来源证据一起写进 ``story.mechanics.element_manifest``。
   清单随故事包导出/导入一并带走，所以空库也能读；库被删除或升级都不影响已锁定的世界。
3. **旅程**：运行期只读自己绑定的那个故事包版本里的清单快照，**不再查库**（见
   ``context_elements``），因此开局之后不会因为库新增条目而长出新的元素类型。

作者能看到完整 payload 与来源；玩家与 NPC 只看 ``disclosure`` 里**显式列出的**内容，
投影永远不读 payload——没有「字段名带 secret 就安全」这种猜测式判断。

诚实的边界（本版本明确不做）：

* 条目里的 ``requires`` / ``excludes`` / ``background`` / ``entry_modes`` 等是**自然语言条件**，
  不是机器依赖；本模块只把它们作为 ``warnings`` / ``unsupported`` 原样提示，绝不假装已校验。
* 不把百科条目编译成奖励模板、可执行法术或任何规则脚本；没有自动规则转换。
* 不做「全文语义一致性证明」：机器只校验显式 typed 规则（``requires`` / ``conflicts``）、
  版本固定、边界与引用完整性。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import encyclopedia

SCHEMA_VERSION = 1
MECHANICS_KEY = 'element_manifest'

# 库位置：只由服务端配置/环境变量决定，**任何 HTTP 接口都不接受路径参数**。
DEFAULT_DB_RELATIVE = 'artifacts/human-encyclopedia/encyclopedia.sqlite3'
ENV_DB = 'TEXTILEDREAM_ENCYCLOPEDIA_DB'
ENV_ROOTS = 'TEXTILEDREAM_ENCYCLOPEDIA_ROOTS'
BUILD_COMMAND = 'python -m tools.encyclopedia_build'

# 进程启动标识（owner token）：只用来分辨「本次进程正在提交的预留」与「上一进程崩溃留下的
# 陈旧预留」。不靠现实时间超时去抢别的进程，也不宣称支持多进程同时编辑故事包。
PROCESS_TOKEN = uuid.uuid4().hex

# 有限上限：先全量校验，再一次提交；超限直接拒绝，不截断（截断会静默损坏设定）。
MAX_ELEMENTS = 16
MAX_RULES = 64
MAX_ELEMENT_PAYLOAD_CHARS = 30000
MAX_MANIFEST_CHARS = 200000
MAX_ELEMENT_SOURCES = 16
MAX_ELEMENT_RELATIONS = 16
MAX_SOURCE_PAYLOAD_CHARS = 4000
MAX_PUBLIC_FIELDS = 8
MAX_PUBLIC_FIELD_CHARS = 600
MAX_PUBLIC_DESCRIPTION = 600
MAX_NOTE = 400
MAX_TAGS = 32
MAX_KNOWN_BY = 8
MAX_ADAPTATION_CONSTRAINTS = 8
MAX_TEXT_CHARS = 20000
MAX_ID_CHARS = 96

# 进入提示词的投影上限（「完整详情和来源不进模型」）。
CONTEXT_MAX_ENTRIES = 6
CONTEXT_MAX_CHARS = 3000
CONTEXT_ENTRY_CHARS = 400
CONTEXT_FACT_CHARS = 160
CONTEXT_MAX_FACTS = 3

STATES = ('existing', 'potential')
STATE_LABELS = {'existing': '世界中已存在', 'potential': '尚未出现（预绑定的潜在元素）'}
RULE_KINDS = ('requires', 'conflicts')
RULE_LABELS = {'requires': '依赖', 'conflicts': '互斥'}

# 公开字段白名单：七节 + 少量固定标量/列表字段。**白名单之外一律拒绝**，
# 既不做前缀猜测，也不因为字段名看起来无害就放行。
PUBLIC_FIELDS = tuple(encyclopedia.DETAIL_SECTIONS) + (
    'summary', 'variants', 'story_roles', 'background', 'entry_modes',
    'introduction_limits', 'genres', 'category',
)

# 只作为诚实提示的自然语言条件字段：不参与任何机器判定。
NATURAL_LANGUAGE_FIELDS = (
    ('requires', '自然语言前置条件'),
    ('excludes', '自然语言互斥条件'),
    ('background', '背景条件'),
    ('entry_modes', '进入方式'),
    ('introduction_limits', '引入限制'),
    ('story_roles', '剧情作用'),
    ('evidence_note', '证据说明'),
)
# 看起来像可执行规则、但本版本不转换的字段：显式记为 unsupported。
UNSUPPORTED_PAYLOAD_FIELDS = ('rule_refs', 'mechanics', 'effects', 'rewards', 'scripts', 'formula')

_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_.:-]*$')


# --------------------------------------------------------------------------- 错误
class AssemblyError(ValueError):
    """被拒绝的装配操作。所有拒绝都发生在写入之前，不留半绑定状态。"""


class LibraryUnavailable(AssemblyError):
    """库不可用（不存在 / 非法 / 越界 / schema 不符）。绝不顺手建一个空库。"""


# --------------------------------------------------------------------------- 工具
def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return uuid.uuid4().hex[:16]


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _chars(value):
    return len(json.dumps(value, ensure_ascii=False))


def payload_digest(payload):
    return hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest()


def manifest_digest(manifest):
    """内容指纹：不含 ``locked_at`` / ``note`` 等易变字段。

    同一批选择、同一库内容 → 同一 digest → 重复提交幂等（不新建故事包版本）。
    """
    body = {'version': manifest.get('version'),
            'elements': manifest.get('elements', []),
            'rules': manifest.get('rules', {})}
    return hashlib.sha256(_canonical(body).encode('utf-8')).hexdigest()


def _text(value, label, limit, allow_empty=False):
    if not isinstance(value, str):
        raise AssemblyError('%s必须是文本' % label)
    text = value.strip()
    if not text and not allow_empty:
        raise AssemblyError('%s不能为空' % label)
    if len(text) > limit:
        raise AssemblyError('%s超过 %d 字符上限（%d）' % (label, limit, len(text)))
    return text


def _bool(value, label):
    if not isinstance(value, bool):
        raise AssemblyError('%s必须是 true/false（不接受 0/1 或文本）' % label)
    return value


def _int(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssemblyError('%s必须是整数（布尔值不算）' % label)
    if not low <= value <= high:
        raise AssemblyError('%s必须在 %d..%d 之间（%r）' % (label, low, high, value))
    return value


def _check_id(value, label):
    if not isinstance(value, str) or not _ID_RE.match(value) or len(value) > MAX_ID_CHARS:
        raise AssemblyError('%s格式无效：%r' % (label, value))
    return value


def ref_of(namespace, element_id):
    return '%s/%s' % (namespace, element_id)


def _split_ref(ref):
    if not isinstance(ref, str):
        raise AssemblyError('元素引用必须是 namespace/element_id 文本')
    if '/' not in ref:
        raise AssemblyError('元素引用需要 namespace/element_id 形式：%r' % (ref,))
    namespace, element_id = ref.split('/', 1)
    _check_id(namespace, '元素引用的 namespace')
    _check_id(element_id, '元素引用的 element_id')
    if len(ref) > MAX_ID_CHARS * 2 + 1:
        raise AssemblyError('元素引用过长：%s' % ref)
    return namespace, element_id


def _str_list(value, label, limit, item_limit, allow_empty=True):
    if not isinstance(value, list):
        raise AssemblyError('%s必须是列表' % label)
    if len(value) > limit:
        raise AssemblyError('%s最多 %d 项' % (label, limit))
    result = []
    for item in value:
        text = _text(item, label + '条目', item_limit)
        if text not in result:
            result.append(text)
    if not result and not allow_empty:
        raise AssemblyError('%s不能为空' % label)
    return result


# --------------------------------------------------------------------------- 库访问
def _status_extra():
    """界面要用的常量（白名单 / 状态 / 上限）。缺库时也要能渲染表单。"""
    return {
        'read_only': True,
        'public_fields': list(PUBLIC_FIELDS),
        'states': [{'id': state, 'label': STATE_LABELS[state]} for state in STATES],
        'limits': {'elements': MAX_ELEMENTS,
                   'payload_chars': MAX_ELEMENT_PAYLOAD_CHARS,
                   'public_fields': MAX_PUBLIC_FIELDS,
                   'public_description': MAX_PUBLIC_DESCRIPTION,
                   'context_entries': CONTEXT_MAX_ENTRIES},
    }


class ElementLibrary:
    """受限的库路径解析 + 只读查询。路径只来自服务端配置，测试可显式注入。

    允许目录默认只有工作区根；``allowed_roots`` 用于测试注入临时库。
    路径不在允许目录内 → 拒绝（不允许用参数读到任意 OS 文件）。
    """

    def __init__(self, root, path=None, allowed_roots=None):
        self.root = Path(root)
        self.explicit = None if path is None else Path(path)
        self.allowed_roots = [Path(p) for p in (allowed_roots or [])]

    # ------------------------------------------------------------- 路径策略
    def _roots(self):
        roots = [self.root] + self.allowed_roots
        for extra in (os.getenv(ENV_ROOTS) or '').split(os.pathsep):
            if extra.strip():
                roots.append(Path(extra.strip()))
        return roots

    def candidate(self):
        raw = self.explicit
        if raw is None:
            env = (os.getenv(ENV_DB) or '').strip()
            raw = Path(env) if env else Path(DEFAULT_DB_RELATIVE)
        path = Path(raw)
        if not path.is_absolute():
            path = self.root / path
        return path

    def _display(self, path):
        resolved = path.resolve()
        for root in self._roots():
            try:
                base = Path(root).resolve()
            except OSError:
                continue
            if resolved == base:
                return '.'
            if base in resolved.parents:
                return resolved.relative_to(base).as_posix()
        return resolved.name

    def resolve(self):
        path = self.candidate()
        resolved = path.resolve()
        for root in self._roots():
            try:
                base = Path(root).resolve()
            except OSError:
                continue
            if resolved == base or base in resolved.parents:
                return resolved
        raise LibraryUnavailable(
            '百科库路径不在允许的目录内，已拒绝：%s' % self._display(path))

    def _sanitize(self, message):
        """错误信息里不暴露绝对路径。"""
        for text in {str(self.candidate()), str(self.candidate().resolve()),
                     self.candidate().as_posix(), self.candidate().resolve().as_posix()}:
            message = message.replace(text, self._display(self.candidate()))
        return message

    def _open(self):
        path = self.resolve()
        display = self._display(path)
        if not path.exists():
            raise LibraryUnavailable(
                '百科库不存在：%s。请先运行 %s 生成库；本页面不会自动建库或填库。'
                % (display, BUILD_COMMAND))
        if path.is_dir():
            raise LibraryUnavailable('百科库路径是目录：%s' % display)
        try:
            return encyclopedia.open_readonly(path)
        except encyclopedia.EncyclopediaError as error:
            raise LibraryUnavailable(self._sanitize('百科库不可用：' + str(error))) from error

    # ----------------------------------------------------------------- 查询
    def status(self):
        path = self.candidate()
        display = self._display(path)
        try:
            resolved = self.resolve()
        except LibraryUnavailable as error:
            return {**_status_extra(), 'exists': False, 'path': display, 'allowed': False,
                    'error': str(error), 'build_command': BUILD_COMMAND}
        if not resolved.exists():
            return {**_status_extra(), 'exists': False, 'path': display, 'allowed': True,
                    'error': '百科库不存在：%s。请运行 %s 生成；不会自动建库。'
                             % (display, BUILD_COMMAND),
                    'build_command': BUILD_COMMAND}
        try:
            data = encyclopedia.stats(resolved)
        except encyclopedia.EncyclopediaError as error:
            return {**_status_extra(), 'exists': True, 'path': display, 'allowed': True,
                    'readable': False,
                    'error': self._sanitize(str(error)), 'build_command': BUILD_COMMAND}
        return {
            **_status_extra(),
            'exists': True, 'path': display, 'allowed': True, 'readable': True,
            'schema_version': data['schema_version'],
            'totals': data['totals'],
            'groups': [{'namespace': g['namespace'], 'group_id': g['group_id'],
                        'elements': g['elements'], 'sources': g['sources']}
                       for g in data['groups']],
            'candidate': '库内条目均为待审候选（needs_review / needs_detail），采纳不改变审核状态',
            'build_command': BUILD_COMMAND,
        }

    def _query(self, call):
        """把库的领域错误翻成本模块错误，并且信息里不留绝对路径。"""
        try:
            return call()
        except encyclopedia.EncyclopediaError as error:
            raise AssemblyError(self._sanitize(str(error))) from error

    def search(self, **kwargs):
        path = self.resolve()
        self._open().close()
        return self._query(lambda: encyclopedia.search(path, **kwargs))

    def get(self, namespace, element_id, version=None):
        path = self.resolve()
        self._open().close()
        return self._query(lambda: encyclopedia.get(path, element_id, namespace=namespace,
                                                    version=version, include_payload=True))

    def versions(self, namespace, element_id):
        path = self.resolve()
        self._open().close()
        return self._query(lambda: encyclopedia.versions(path, element_id,
                                                         namespace=namespace))

    def tags(self, **kwargs):
        path = self.resolve()
        self._open().close()
        return self._query(lambda: encyclopedia.list_tags(path, **kwargs))


# --------------------------------------------------------------------- 选择清单
SELECTION_FIELDS = {'namespace', 'element_id', 'version', 'state',
                    'acknowledge_candidate', 'disclosure', 'adaptation', 'note'}
DISCLOSURE_FIELDS = {'public_description', 'public_fields', 'location_id',
                     'reveal_flag', 'known_by', 'reveal_potential', 'note'}
ADAPTATION_FIELDS = {'note', 'constraints'}
_FLAG_RE = re.compile(r'^[A-Za-z0-9_-]{1,60}$')


def _prepare_disclosure(raw):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AssemblyError('公开范围必须是对象')
    unknown = set(raw) - DISCLOSURE_FIELDS
    if unknown:
        raise AssemblyError('公开范围有未知字段：' + '、'.join(sorted(unknown)))
    # 只有白名单里的字段能公开；名字看起来安全不算理由。
    fields = raw.get('public_fields') or []
    if not isinstance(fields, list):
        raise AssemblyError('public_fields 必须是字段名列表')
    if len(fields) > MAX_PUBLIC_FIELDS:
        raise AssemblyError('公开字段最多 %d 项' % MAX_PUBLIC_FIELDS)
    for name in fields:
        if not isinstance(name, str) or name not in PUBLIC_FIELDS:
            raise AssemblyError('公开字段不在白名单内：%r（可选：%s）'
                                % (name, ', '.join(PUBLIC_FIELDS)))
    if len(set(fields)) != len(fields):
        raise AssemblyError('公开字段不能重复')
    location = raw.get('location_id')
    if location is not None:
        location = _check_id(location, '公开范围的地点 ID')
    flag = raw.get('reveal_flag')
    if flag is not None:
        if not isinstance(flag, str) or not _FLAG_RE.match(flag):
            raise AssemblyError('reveal_flag 格式无效：%r' % (flag,))
    known = raw.get('known_by') or []
    if not isinstance(known, list):
        raise AssemblyError('known_by 必须是受众 ID 列表')
    if len(known) > MAX_KNOWN_BY:
        raise AssemblyError('known_by 最多 %d 项' % MAX_KNOWN_BY)
    audiences = []
    for who in known:
        if who == 'player' or (isinstance(who, str) and _ID_RE.match(who or '')
                               and len(who) <= MAX_ID_CHARS):
            if who not in audiences:
                audiences.append(who)
        else:
            raise AssemblyError('known_by 里有无效受众 ID：%r' % (who,))
    reveal_potential = _bool(raw.get('reveal_potential', False), 'reveal_potential')
    return {
        'public_description': _text(raw.get('public_description') or '',
                                    'public_description', MAX_PUBLIC_DESCRIPTION,
                                    allow_empty=True),
        'public_fields': list(fields),
        'location_id': location,
        'reveal_flag': flag,
        'known_by': audiences,
        'reveal_potential': reveal_potential,
        'note': _text(raw.get('note') or '', '公开范围备注', MAX_NOTE, allow_empty=True),
    }


def _prepare_adaptation(raw):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AssemblyError('作者适配必须是对象')
    unknown = set(raw) - ADAPTATION_FIELDS
    if unknown:
        raise AssemblyError('作者适配有未知字段：' + '、'.join(sorted(unknown)))
    return {
        'note': _text(raw.get('note') or '', '适配说明', MAX_NOTE, allow_empty=True),
        'constraints': _str_list(raw.get('constraints') or [], '适配限制',
                                 MAX_ADAPTATION_CONSTRAINTS, MAX_NOTE),
    }


def prepare_selection(raw):
    """结构校验（不读库）。库内内容与版本存在性在 build_manifest 里核对。"""
    if not isinstance(raw, dict):
        raise AssemblyError('选择条目必须是对象')
    unknown = set(raw) - SELECTION_FIELDS
    if unknown:
        raise AssemblyError('选择条目有未知字段：' + '、'.join(sorted(unknown)))
    namespace = _check_id(raw.get('namespace'), 'namespace')
    element_id = _check_id(raw.get('element_id'), 'element_id')
    version = _int(raw.get('version'), '元素版本', 1, 10 ** 6)
    state = raw.get('state', 'existing')
    if state not in STATES:
        raise AssemblyError('元素状态只能是 existing 或 potential（得到 %r）' % (state,))
    acknowledge = _bool(raw.get('acknowledge_candidate', False), '候选确认')
    disclosure = _prepare_disclosure(raw.get('disclosure'))
    if disclosure['reveal_potential'] and state != 'potential':
        raise AssemblyError('只有潜在元素才需要 reveal_potential；已存在元素请直接选择公开字段')
    adaptation = _prepare_adaptation(raw.get('adaptation'))
    return {
        'namespace': namespace, 'element_id': element_id, 'version': version,
        'state': state, 'acknowledge_candidate': acknowledge,
        'disclosure': disclosure, 'adaptation': adaptation,
        'note': _text(raw.get('note') or '', '选择备注', MAX_NOTE, allow_empty=True),
    }


def _public_text_of(detail, field):
    """按白名单取公开文本。**超长直接拒绝**，不切片、不截断（截断会把「不能」变成「能」）。"""
    value = detail.get('details', {}).get(field)
    if value is None:
        value = detail.get('payload', {}).get(field)
    if value is None:
        return ''
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list) and all(isinstance(x, str) for x in value):
        text = '、'.join(x.strip() for x in value if x.strip())
    else:
        raise AssemblyError('公开字段 %s 不是文本或文本列表，不能作为公开说明' % field)
    if len(text) > MAX_PUBLIC_FIELD_CHARS:
        raise AssemblyError('公开字段 %s 超过 %d 字符：请改用更短的公开说明（不自动截断）'
                            % (field, MAX_PUBLIC_FIELD_CHARS))
    return text


def _bounded(value, limit, label):
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > limit:
        raise AssemblyError('%s超过 %d 字符上限（%d）' % (label, limit, len(text)))
    return text


def _sources_of(detail):
    """来源快照：固定 source_version 的**完整 payload** + 内容哈希。

    只存 title/url 不足以证明「当时看到的是哪一版证据」；来源被改、库被删之后，
    故事包自己仍能核对 hash 与 supports / rights_note。
    """
    rows = []
    for source in detail.get('sources', [])[:MAX_ELEMENT_SOURCES]:
        payload = source.get('payload')
        _bounded(payload, MAX_SOURCE_PAYLOAD_CHARS, '来源 payload')
        if payload is not None and source.get('payload_hash') \
                and payload_digest(payload) != source['payload_hash']:
            raise AssemblyError('来源 %s 的 payload 与库内哈希不一致，拒绝采纳'
                                % source.get('source_id'))
        rows.append({
            'source_id': source.get('source_id'),
            'source_namespace': source.get('source_namespace'),
            'source_version': source.get('source_version'),
            'status': source.get('status'),
            'payload_hash': source.get('payload_hash'),
            'payload': payload,
            'is_current_source_version': source.get('is_current_source_version'),
        })
    return rows


def _warnings_of(entry_payload):
    warnings, unsupported = [], []
    for field, label in NATURAL_LANGUAGE_FIELDS:
        if field not in entry_payload:
            continue
        value = entry_payload[field]
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        text = text.strip()
        if not text:
            continue
        warnings.append('%s：条目里的「%s」是自然语言条件，本版本不当机器依赖，'
                        '也没有校验它在本世界是否成立' % (label, field[:80]))
    for field in UNSUPPORTED_PAYLOAD_FIELDS:
        if field in entry_payload:
            unsupported.append('条目含「%s」字段；本版本不把百科条目编译成可执行规则、'
                               '奖励模板或法术' % field)
    return warnings, unsupported


def _element_record(detail, selection):
    payload = detail.get('payload')
    if not isinstance(payload, dict):
        raise AssemblyError('库返回的元素 payload 不是对象：%s' % detail.get('element_id'))
    payload_text = _bounded(payload, MAX_ELEMENT_PAYLOAD_CHARS, '元素完整 payload')
    digest = payload_digest(payload)
    disclosure = dict(selection['disclosure'])
    public_text = {}
    for field in disclosure['public_fields']:
        text = _public_text_of(detail, field)
        if text:
            public_text[field] = text
    disclosure['public_text'] = public_text
    warnings, unsupported = _warnings_of(payload)
    if (disclosure['public_description'] or public_text) and not disclosure['known_by']:
        warnings.append('公开内容和字段都存在，但 known_by 为空：任何人都看不到；'
                        '请显式指定玩家或角色')
    if disclosure['location_id'] is None and (disclosure['public_description'] or public_text):
        warnings.append('未限定地点：公开内容在任意地点都可能被看到')
    if selection['state'] == 'potential' and disclosure['public_description'] \
            and not disclosure['reveal_potential']:
        warnings.append('潜在元素的公开说明不会自动透露其存在（缺少 reveal_potential）')
    record = {
        'ref': ref_of(selection['namespace'], selection['element_id']),
        'namespace': selection['namespace'],
        'element_id': selection['element_id'],
        'version': selection['version'],
        'content_hash': detail.get('content_hash'),
        'schema_kind': detail.get('schema_kind'),
        'adapter': detail.get('adapter'),
        'legacy_schema': detail.get('legacy_schema'),
        'name': detail.get('name'),
        'aliases': list(detail.get('aliases') or [])[:MAX_TAGS],
        'tags': list(detail.get('tags') or [])[:MAX_TAGS],
        'summary': detail.get('summary') or '',
        # 只记录库里的原值：采纳不改变审核状态，派生逻辑也不会升格。
        'review_status': detail.get('review_status'),
        'detail_status': detail.get('detail_status'),
        'state': selection['state'],
        'details': dict(detail.get('details') or {}),
        'details_map': dict(detail.get('details_map') or {}),
        'payload': payload,
        'payload_hash': digest,
        'payload_chars': len(payload_text),
        'sources': _sources_of(detail),
        'relations': list(detail.get('relations') or [])[:MAX_ELEMENT_RELATIONS],
        'disclosure': disclosure,
        'adaptation': dict(selection['adaptation']),
        'note': selection['note'],
        'warnings': warnings,
        'unsupported': unsupported,
    }
    return record


# ------------------------------------------------------------------------- 规则
RULE_FIELDS = {'kind', 'from', 'to', 'from_version', 'to_version', 'note'}


def _prepare_rule(raw):
    if not isinstance(raw, dict):
        raise AssemblyError('规则必须是对象')
    unknown = set(raw) - RULE_FIELDS
    if unknown:
        raise AssemblyError('规则有未知字段：' + '、'.join(sorted(unknown)))
    kind = raw.get('kind')
    if kind not in RULE_KINDS:
        raise AssemblyError('规则类型只能是 requires（依赖）或 conflicts（互斥）')
    source, target = raw.get('from'), raw.get('to')
    _split_ref(source)
    _split_ref(target)
    item = {'kind': kind, 'from': source, 'to': target}
    for key in ('from_version', 'to_version'):
        value = raw.get(key)
        if value is not None:
            item[key] = _int(value, '规则里的 ' + key, 1, 10 ** 6)
    item['note'] = _text(raw.get('note') or '', '规则备注', MAX_NOTE, allow_empty=True)
    return item


def _prepare_rules(raw):
    if raw is None:
        raw = []
    if isinstance(raw, dict):
        unknown = set(raw) - {'version', 'items'}
        if unknown:
            raise AssemblyError('规则对象有未知字段：' + '、'.join(sorted(unknown)))
        if raw.get('version') not in (None, SCHEMA_VERSION):
            raise AssemblyError('规则版本只能是 %d' % SCHEMA_VERSION)
        raw = raw.get('items') or []
    if not isinstance(raw, list):
        raise AssemblyError('规则必须是列表')
    if len(raw) > MAX_RULES:
        raise AssemblyError('规则最多 %d 条' % MAX_RULES)
    return {'version': SCHEMA_VERSION, 'items': [_prepare_rule(item) for item in raw]}


def _check_rule_version(rule, ref, version):
    for end, key in (('from', 'from_version'), ('to', 'to_version')):
        if rule[end] != ref or rule.get(key) is None:
            continue
        if rule[key] != version:
            raise AssemblyError(
                '规则固定的是 %s v%d，清单里选的是 v%d；版本必须一致'
                % (ref, rule[key], version))


def _validate_rules(elements, rules):
    """显式 typed 规则校验。自然语言条件不在这里被当成依赖（见 _warnings_of）。"""
    items = rules.get('items') if isinstance(rules, dict) else rules
    if not isinstance(items, list):
        raise AssemblyError('规则 items 必须是列表')
    if len(items) > MAX_RULES:
        raise AssemblyError('规则最多 %d 条' % MAX_RULES)
    by_ref = {e['ref']: e for e in elements}
    seen = set()
    warnings = []
    for rule in items:
        kind, source, target = rule['kind'], rule['from'], rule['to']
        _split_ref(source)
        _split_ref(target)
        key = (kind, source, target)
        if key in seen:
            raise AssemblyError('重复规则：%s %s → %s' % (kind, source, target))
        seen.add(key)
        if kind == 'requires':
            missing = [ref for ref in (source, target) if ref not in by_ref]
            if missing:
                raise AssemblyError('依赖规则引用了清单外的元素（缺引用）：'
                                    + '、'.join(missing))
            _check_rule_version(rule, source, by_ref[source]['version'])
            _check_rule_version(rule, target, by_ref[target]['version'])
        elif kind == 'conflicts':
            if source == target:
                raise AssemblyError('元素不能与自己互斥：' + source)
            present = [ref for ref in (source, target) if ref in by_ref]
            if not present:
                raise AssemblyError('互斥规则两端都不在清单里，无法判断它约束什么：'
                                    '%s → %s' % (source, target))
            if len(present) == 2:
                raise AssemblyError('清单同时选中了互斥元素：%s 与 %s' % (source, target))
            _check_rule_version(rule, present[0], by_ref[present[0]]['version'])
            warnings.append('互斥规则 %s ↔ %s：%s 不在本清单里，本版本作为守卫记录，'
                            '将来加入时会被拒绝' % (source, target, present[0] == source and target or source))
        else:
            raise AssemblyError('规则类型只能是 requires 或 conflicts（得到 %r）' % (kind,))
    # 依赖环：显式报错并给出路径。
    graph = {ref: [] for ref in by_ref}
    for rule in items:
        if rule['kind'] == 'requires':
            graph[rule['from']].append(rule['to'])
    state = {}

    def visit(node, trail):
        if state.get(node) == 'done':
            return
        if state.get(node) == 'open':
            raise AssemblyError('依赖规则存在环：' + ' → '.join(trail + [node]))
        state[node] = 'open'
        for dependency in sorted(graph.get(node, [])):
            visit(dependency, trail + [node])
        state[node] = 'done'

    for node in sorted(graph):
        visit(node, [])
    return warnings


# ---------------------------------------------------------------------- 清单构建
def package_manifest(story):
    """故事包里的清单（没有就是 None）。老故事包没有这个键，行为完全不变。"""
    mechanics = (story or {}).get('mechanics') or {}
    if not isinstance(mechanics, dict):
        return None
    manifest = mechanics.get(MECHANICS_KEY)
    if manifest is None:
        return None
    if not isinstance(manifest, dict):
        raise AssemblyError('mechanics.%s 必须是对象' % MECHANICS_KEY)
    return manifest


def _validate_manifest_shape(manifest):
    """完整结构 + 上限 + 自证哈希。导入的包也走这里，所以被改过的清单会被拒绝。"""
    if not isinstance(manifest, dict):
        raise AssemblyError('元素清单必须是对象')
    if manifest.get('version') != SCHEMA_VERSION:
        raise AssemblyError('元素清单版本必须是 %d' % SCHEMA_VERSION)
    elements = manifest.get('elements')
    if not isinstance(elements, list):
        raise AssemblyError('元素清单缺少 elements 列表')
    if len(elements) > MAX_ELEMENTS:
        raise AssemblyError('元素清单最多 %d 条（V1 安全边界，不代表全世界上限）' % MAX_ELEMENTS)
    seen = set()
    for element in elements:
        if not isinstance(element, dict):
            raise AssemblyError('元素清单条目必须是对象')
        ref = element.get('ref')
        namespace, element_id = _split_ref(ref)
        if ref != ref_of(namespace, element_id):
            raise AssemblyError('元素引用不规范：%r' % (ref,))
        if ref in seen:
            raise AssemblyError('元素清单里重复出现：' + ref)
        seen.add(ref)
        if element.get('namespace') != namespace or element.get('element_id') != element_id:
            raise AssemblyError('元素引用与 namespace/element_id 不一致：' + ref)
        _int(element.get('version'), '元素版本', 1, 10 ** 6)
        if element.get('state') not in STATES:
            raise AssemblyError('元素状态无效：%r（%s）' % (element.get('state'), ref))
        payload = element.get('payload')
        if not isinstance(payload, dict):
            raise AssemblyError('元素缺少完整原始 payload：' + ref)
        _bounded(payload, MAX_ELEMENT_PAYLOAD_CHARS, '元素 payload（%s）' % ref)
        try:
            encyclopedia.check_json_value(payload)
        except encyclopedia.InvalidDocument as error:
            raise AssemblyError('元素 payload 含非法数值（NaN/Infinity）：%s（%s）'
                                % (ref, error)) from error
        if element.get('payload_hash') != payload_digest(payload):
            raise AssemblyError('元素 payload 与记录的哈希不一致（可能被手工改过）：' + ref)
        sources = element.get('sources')
        if not isinstance(sources, list) or len(sources) > MAX_ELEMENT_SOURCES:
            raise AssemblyError('元素来源快照无效：' + ref)
        for source in sources:
            if not isinstance(source, dict) or not source.get('source_id'):
                raise AssemblyError('来源快照缺少 source_id：' + ref)
            _int(source.get('source_version'), '来源版本', 1, 10 ** 6)
            if source.get('payload') is not None:
                _bounded(source['payload'], MAX_SOURCE_PAYLOAD_CHARS,
                         '来源 payload（%s）' % source.get('source_id'))
                try:
                    encyclopedia.check_json_value(source['payload'])
                except encyclopedia.InvalidDocument as error:
                    raise AssemblyError('来源 payload 含非法数值：%s'
                                        % source.get('source_id')) from error
                if source.get('payload_hash') != payload_digest(source['payload']):
                    raise AssemblyError('来源 payload 与记录的哈希不一致：'
                                        + str(source.get('source_id')))
        disclosure = element.get('disclosure')
        if not isinstance(disclosure, dict):
            raise AssemblyError('元素缺少公开范围：' + ref)
        extra = set(disclosure) - DISCLOSURE_FIELDS - {'public_text'}
        if extra:
            raise AssemblyError('公开范围有未知字段：%s（%s）'
                                % ('、'.join(sorted(extra)), ref))
        prepared = _prepare_disclosure({k: disclosure[k] for k in DISCLOSURE_FIELDS
                                        if k in disclosure})
        if prepared['public_fields'] != list(disclosure.get('public_fields') or []):
            raise AssemblyError('公开字段与白名单不一致：' + ref)
        public_text = disclosure.get('public_text') or {}
        if not isinstance(public_text, dict) or set(public_text) - set(prepared['public_fields']):
            raise AssemblyError('公开文本必须只覆盖已声明的公开字段：' + ref)
        for name, text in public_text.items():
            if not isinstance(text, str) or len(text) > MAX_PUBLIC_FIELD_CHARS:
                raise AssemblyError('公开文本 %s 无效或过长：%s' % (name, ref))
        disclosure['public_text'] = {k: v for k, v in public_text.items() if v}
        element['disclosure'] = {**prepared, 'public_text': disclosure['public_text']}
    if _chars(manifest) > MAX_MANIFEST_CHARS:
        raise AssemblyError('元素清单超过 %d 字符上限（%d）'
                            % (MAX_MANIFEST_CHARS, _chars(manifest)))
    rules = manifest.get('rules') or {'version': SCHEMA_VERSION, 'items': []}
    prepared_rules = _prepare_rules(rules)
    warnings = _validate_rules(elements, prepared_rules)
    manifest['rules'] = prepared_rules
    # 提交凭据（receipt）参与包校验，但不进入语义 digest：它证明「哪份草稿、基于哪个
    # 版本提交了这份清单」，并让索引写失败后的重试无需源库。
    receipt = manifest.get('receipt')
    if receipt is not None:
        if not isinstance(receipt, dict):
            raise AssemblyError('清单的提交凭据必须是对象')
        for key in ('draft_id', 'base_revision', 'digest'):
            if not isinstance(receipt.get(key), str) or not receipt[key]:
                raise AssemblyError('清单的提交凭据缺少 %s' % key)
        if receipt['digest'] != manifest_digest(manifest):
            raise AssemblyError('清单的提交凭据与清单内容不一致（清单被改动过）')
    return warnings


def validate_package(story, characters=None):
    """故事包内清单校验：结构、自证哈希、公开范围的 ID 必须真实存在、typed 规则。"""
    manifest = package_manifest(story)
    if manifest is None:
        return None
    _validate_manifest_shape(manifest)
    places = {place['id'] for place in (story or {}).get('locations', [])}
    audiences = {'player'}
    if characters:
        audiences |= {c['id'] for c in characters.get('characters', [])}
    for element in manifest['elements']:
        disclosure = element['disclosure']
        if disclosure.get('location_id') and disclosure['location_id'] not in places:
            raise AssemblyError('元素 %s 的公开范围绑定了不存在的地点 %s'
                                % (element['ref'], disclosure['location_id']))
        unknown = set(disclosure.get('known_by') or []) - audiences
        if unknown:
            raise AssemblyError('元素 %s 的公开受众不存在：%s'
                                % (element['ref'], '、'.join(sorted(unknown))))
    return manifest


def rebind_manifest(manifest, story, characters):
    """把一个既有清单交到**新世界**手里：解析不了的公开范围一律清空。

    生成新世界时地点/角色 ID 会重排。绝不为了让内容「还能看到」而沿用非法 ID 或
    放宽范围——清空公开说明（= 谁都看不到）并记录警告，等作者重新指定。
    """
    if manifest is None:
        return None, []
    manifest = json.loads(json.dumps(manifest))
    places = {place['id'] for place in (story or {}).get('locations', [])}
    audiences = {'player'} | {c['id'] for c in (characters or {}).get('characters', [])}
    warnings = []
    for element in manifest.get('elements', []):
        disclosure = element.get('disclosure') or {}
        resolved = list(disclosure.get('known_by') or [])
        unknown = [who for who in resolved if who not in audiences]
        if unknown:
            warnings.append('元素 %s 的公开受众 %s 在新世界里不存在，公开范围已清空，'
                            '请作者重新指定' % (element.get('ref'), '、'.join(unknown)))
            disclosure['known_by'] = []
        place = disclosure.get('location_id')
        if place and place not in places:
            warnings.append('元素 %s 的公开地点 %s 在新世界里不存在，公开范围已清空，'
                            '请作者重新指定公开范围' % (element.get('ref'), place))
            disclosure['location_id'] = None
            disclosure['known_by'] = []
        if not disclosure.get('known_by'):
            disclosure['public_description'] = ''
            disclosure['public_fields'] = []
            disclosure['public_text'] = {}
            disclosure['reveal_potential'] = False
        element['disclosure'] = disclosure
    if warnings:
        manifest['warnings'] = list(manifest.get('warnings') or []) + warnings
    # 公开范围变了 → 旧的提交凭据不再描述这份清单，必须一并移除。
    manifest.pop('receipt', None)
    # 改了 disclosure 之后必须整体重新自洽：payload/来源哈希、白名单与规则一起复验，
    # 不能只看「有警告」就当成功。
    _validate_manifest_shape(manifest)
    return manifest, warnings


# ------------------------------------------------------------------------ 投影
def author_view(manifest):
    """作者视图：完整 payload、来源证据、审核状态与所有警告。"""
    if manifest is None:
        return None
    return {
        'version': manifest.get('version'),
        'digest': manifest_digest(manifest),
        'locked_at': manifest.get('locked_at'),
        'note': manifest.get('note', ''),
        'library': manifest.get('library', {}),
        'count': len(manifest.get('elements', [])),
        'elements': manifest.get('elements', []),
        'rules': manifest.get('rules', {'version': SCHEMA_VERSION, 'items': []}),
        'warnings': manifest.get('warnings', []),
        'unsupported': manifest.get('unsupported', []),
        'candidate_notice': '库内条目是待审候选；采纳只锁定版本，不改变 review_status / detail_status',
    }


def _disclosed(element):
    disclosure = element.get('disclosure') or {}
    return bool(disclosure.get('public_description') or disclosure.get('public_text'))


def public_view(manifest, audience='player', session=None):
    """玩家 / NPC 视图：**只读 disclosure，永不读 payload**。

    potential 元素必须显式 ``reveal_potential`` 才可能被提及；location / reveal_flag /
    known_by 必须同时满足；``known_by`` 为空表示谁都看不到（不是「所有人」）。
    """
    if manifest is None:
        return []
    flags = (session or {}).get('flags') or {}
    location = (session or {}).get('location')
    rows = []
    for element in manifest.get('elements', []):
        disclosure = element.get('disclosure') or {}
        known = list(disclosure.get('known_by') or [])
        if not known or audience not in known:
            continue
        if disclosure.get('reveal_flag') and not flags.get(disclosure['reveal_flag']):
            continue
        if disclosure.get('location_id'):
            # 没有旅程就没有「现在在哪」；不猜，也不透露。
            if not location or location != disclosure['location_id']:
                continue
        if element.get('state') == 'potential' and not disclosure.get('reveal_potential'):
            continue
        if not _disclosed(element):
            continue
        facts = [{'field': name, 'text': text}
                 for name, text in (disclosure.get('public_text') or {}).items() if text]
        rows.append({
            'ref': element.get('ref'),
            'name': element.get('name'),
            'element_id': element.get('element_id'),
            'version': element.get('version'),
            'state': element.get('state'),
            'state_label': STATE_LABELS.get(element.get('state'), element.get('state')),
            'description': disclosure.get('public_description') or '',
            'facts': facts,
            'note': disclosure.get('note') or '',
        })
    return rows


def context_elements(story, audience, session):
    """进入叙事上下文的**有界**元素摘要；没有清单时返回 None（老包 prompt 一字不变）。

    * 只给作者采纳的公开说明，不塞完整详情、来源或审核标记。
    * 任何字段都**整段保留或整段丢掉**：不切片，避免把「不能」截成「能」。
    """
    manifest = package_manifest(story)
    if manifest is None:
        return None
    rows = public_view(manifest, audience, session)
    items = []
    for row in rows[:CONTEXT_MAX_ENTRIES]:
        entry = {'name': row['name'], 'when': row['state_label'],
                 'description': row['description']}
        facts = [fact['text'] for fact in row['facts']][:CONTEXT_MAX_FACTS]
        if facts:
            entry['facts'] = facts
        if not entry['description'] and not facts:
            continue
        items.append(entry)
    # 名额与总量都按「整条丢弃」收敛，宁可少给也不给出被截断的半句。
    while items and len(json.dumps({'items': items}, ensure_ascii=False)) > CONTEXT_MAX_CHARS:
        if len(items[-1].get('facts') or []) > 1:
            items[-1]['facts'] = items[-1]['facts'][:-1]
        else:
            items[-1].pop('facts', None)
            if len(json.dumps({'items': items}, ensure_ascii=False)) > CONTEXT_MAX_CHARS:
                items.pop()
    return {
        'basis': '作者为本世界采纳的元素设定：服从当前旅程状态，不等于已经发生或已被执行；'
                 '潜在元素尚未出现，不得当作已有条件',
        'items': items,
    }


# ------------------------------------------------------------------- 清单子集
def subset_manifest(manifest, refs):
    """从既有清单里取**子集**（生成草稿用），并把显式 typed 依赖闭包补全。

    硬依赖不允许「删规则通过」：选了 A 而 A 声明 `requires B` 时，B 会按清单里已固定的
    精确版本自动加入，传递依赖同样展开；展开后若出现互斥冲突就拒绝。`conflicts` 守卫
    （另一端不在子集）原样保留。整个过程只读清单快照，绝不到库里新选条目。
    """
    if manifest is None:
        return None, []
    by_ref = {element['ref']: element for element in manifest.get('elements', [])}
    rules = list((manifest.get('rules') or {}).get('items', []))
    requested, wanted = [], []
    for raw in refs or []:
        if not isinstance(raw, str):
            raise AssemblyError('生成草稿的元素引用必须是 namespace/element_id 文本')
        ref, _, version = raw.partition('@')
        _split_ref(ref)
        element = by_ref.get(ref)
        if element is None:
            raise AssemblyError('引用的元素不在当前故事包清单里：%s'
                                '（请先在元素装配页采纳，再在生成器里引用）' % ref)
        if version:
            pinned = _int(int(version) if version.isdigit() else None,
                          '引用里的版本', 1, 10 ** 6)
            if pinned != element['version']:
                raise AssemblyError('引用固定的是 %s v%d，清单里是 v%d'
                                    % (ref, pinned, element['version']))
        if ref not in requested:
            requested.append(ref)
        if ref not in [item['ref'] for item in wanted]:
            wanted.append(copy.deepcopy(element))
    if not wanted:
        raise AssemblyError('至少需要引用一个清单内的元素')
    selected = {element['ref'] for element in wanted}
    notes = []
    # requires 闭包：from 在子集里，to 必须也在；缺的按清单里的固定版本补进来。
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule.get('kind') != 'requires' or rule['from'] not in selected:
                continue
            target = rule['to']
            if target not in by_ref:
                raise AssemblyError('依赖规则 %s → %s 的目标不在清单里，无法自动展开；'
                                    '请先在元素装配页补齐这份依赖'
                                    % (rule['from'], target))
            if target not in selected:
                selected.add(target)
                wanted.append(copy.deepcopy(by_ref[target]))
                notes.append('按已声明的硬依赖自动加入 %s（v%d）'
                             % (target, by_ref[target]['version']))
                changed = True
        if len(wanted) > MAX_ELEMENTS:
            raise AssemblyError('依赖闭包超过 %d 个元素上限（V1 安全边界）：请先精简清单'
                                % MAX_ELEMENTS)
    kept_rules, warnings = [], []
    for rule in rules:
        source, target = rule['from'], rule['to']
        inside = [ref for ref in (source, target) if ref in selected]
        if rule.get('kind') == 'requires':
            if source in selected and target not in selected:
                # 闭包已经展开过，走到这里说明清单本身不一致，绝不静默删规则。
                raise AssemblyError('依赖 %s → %s 未满足，拒绝生成子集' % (source, target))
            if len(inside) == 2:
                kept_rules.append(copy.deepcopy(rule))
            # from 不在子集：这条规则约束的元素根本没被选，保留它也没有意义。
            continue
        if len(inside) == 2:
            raise AssemblyError('子集里同时出现互斥元素：%s 与 %s；请先去掉其中一个'
                                % (source, target))
        if inside:
            kept_rules.append(copy.deepcopy(rule))
            warnings.append('互斥规则 %s ↔ %s 作为守卫保留：另一端不在本子集'
                            % (source, target))
    result = json.loads(json.dumps(manifest))
    result['elements'] = wanted
    result['count'] = len(wanted)
    result['rules'] = {'version': SCHEMA_VERSION, 'items': kept_rules}
    result['requested_refs'] = requested
    # 旧的提交凭据描述的是原清单，子集内容变了：不能带着它。
    result.pop('receipt', None)
    result['warnings'] = list(result.get('warnings') or []) + warnings + notes
    result['subset_of'] = manifest_digest(manifest)
    return result, warnings + notes


# ------------------------------------------------------------------------ 服务
class ElementAssembly:
    """作者侧元素装配：库检索、选择草稿、清单校验与故事包提交。"""

    def __init__(self, service):
        self.service = service
        self._configured = False
        self._explicit = None
        self._roots = []

    # ------------------------------------------------------------------ 库
    def configure(self, db_path=None, allowed_roots=None):
        """显式注入库位置与允许目录（测试/运维用）。HTTP 接口不暴露路径参数。"""
        self._configured = True
        self._explicit = None if db_path in (None, '') else Path(db_path)
        self._roots = [Path(item) for item in (allowed_roots or [])]

    def reset(self):
        self._configured = False
        self._explicit = None
        self._roots = []

    def library(self):
        root = self.service.runtime.root
        return ElementLibrary(root, self._explicit, self._roots)

    def status(self):
        return self.library().status()

    def search(self, **kwargs):
        return self.library().search(**kwargs)

    def get(self, namespace, element_id, version=None):
        return self.library().get(namespace, element_id, version=version)

    def versions(self, namespace, element_id):
        return self.library().versions(namespace, element_id)

    def tags(self, **kwargs):
        return self.library().tags(**kwargs)

    # ---------------------------------------------------------------- 草稿
    def list_drafts(self):
        rows = self.service.store.all('element_draft')
        return sorted(rows, key=lambda d: (d.get('created', ''), d['id']))

    def get_draft(self, draft_id):
        draft = self.service.store.get('element_draft', draft_id)
        if not draft:
            raise AssemblyError('元素选择草稿不存在')
        return draft

    def save_draft(self, entries, rules=None, draft_id=None, expected_revision=None,
                   note=''):
        selections = [prepare_selection(item) for item in (entries or [])]
        if not selections:
            raise AssemblyError('清单至少需要一个元素')
        if len(selections) > MAX_ELEMENTS:
            raise AssemblyError('清单最多 %d 个元素（V1 安全边界，不代表全世界上限）'
                                % MAX_ELEMENTS)
        prepared_rules = _prepare_rules(rules)
        note = _text(note or '', '草稿备注', MAX_NOTE, allow_empty=True)
        if draft_id:
            # 读-改-写放在同一个短事务里，并在事务内做 CAS：两个写入者不会互相覆盖。
            with self.service.store.transact() as db:
                row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                 ('element_draft', draft_id)).fetchone()
                if row is None:
                    raise AssemblyError('元素选择草稿不存在')
                draft = json.loads(row[0])
                if draft.get('status') != 'draft':
                    raise AssemblyError('已提交或正在提交的清单不能修改；请另存为新草稿')
                if type(expected_revision) is not int:
                    raise AssemblyError('保存草稿需要整数 expected_revision')
                if draft.get('revision') != expected_revision:
                    raise AssemblyError('草稿已被其他操作更新（当前 %s，提交 %s），请刷新后重试'
                                        % (draft.get('revision'), expected_revision))
                draft.update(elements=selections, rules=prepared_rules, note=note,
                             updated=_now(), revision=expected_revision + 1)
                db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                           ('element_draft', draft_id,
                            json.dumps(draft, ensure_ascii=False, separators=(',', ':'))))
            return draft
        # 新建草稿时就把世界固定在创建这一刻：之后 pointer 换成别的世界也不能提交它。
        base = self.service.runtime.package()
        draft = {'id': 'ea_' + _uid(), 'created': _now(), 'updated': _now(),
                 'revision': 0, 'status': 'draft', 'elements': selections,
                 'rules': prepared_rules, 'note': note,
                 'base_story_revision': base['id'], 'base_story_id': base['story']['id'],
                 'committed_revision': None, 'manifest_digest': None}
        self.service.store.put('element_draft', draft['id'], draft)
        return draft

    # ------------------------------------------------------------ 清单构建
    def build_manifest(self, entries, rules=None, note=''):
        """从库读可信 payload → 完整清单。所有校验在这里完成，之后再提交。"""
        selections = [prepare_selection(item) for item in (entries or [])]
        if not selections:
            raise AssemblyError('清单至少需要一个元素')
        if len(selections) > MAX_ELEMENTS:
            raise AssemblyError('清单最多 %d 个元素（V1 安全边界，不代表全世界上限）'
                                % MAX_ELEMENTS)
        prepared_rules = _prepare_rules(rules)
        library = self.library()
        state = library.status()
        if not state.get('readable'):
            raise LibraryUnavailable(state.get('error') or '百科库不可用')
        unconfirmed = [ref_of(item['namespace'], item['element_id']) for item in selections
                       if not item['acknowledge_candidate']]
        if unconfirmed:
            raise AssemblyError('采纳候选资料需要作者逐条显式确认候选状态'
                                '（acknowledge_candidate=true）：' + '、'.join(unconfirmed))
        elements, seen = [], set()
        for item in selections:
            ref = ref_of(item['namespace'], item['element_id'])
            if ref in seen:
                raise AssemblyError('清单里重复选择了元素：' + ref)
            seen.add(ref)
            try:
                detail = library.get(item['namespace'], item['element_id'],
                                     version=item['version'])
            except AssemblyError as error:
                raise AssemblyError('读取 %s 的 v%d 失败：%s'
                                    % (ref, item['version'], error)) from error
            if detail['version'] != item['version']:
                raise AssemblyError('库返回的版本与所选版本不一致：%s' % ref)
            elements.append(_element_record(detail, item))
        warnings = [text for element in elements for text in element['warnings']]
        unsupported = [text for element in elements for text in element['unsupported']]
        warnings.extend(_validate_rules(elements, prepared_rules))
        manifest = {
            'version': SCHEMA_VERSION,
            'locked_at': _now(),
            'library': {'schema_version': state.get('schema_version'),
                        'path': state.get('path'),
                        'namespaces': sorted({element['namespace'] for element in elements})},
            'count': len(elements),
            'elements': elements,
            'rules': prepared_rules,
            'warnings': warnings,
            'unsupported': unsupported,
            'note': _text(note or '', '清单备注', MAX_NOTE, allow_empty=True),
        }
        if _chars(manifest) > MAX_MANIFEST_CHARS:
            raise AssemblyError('元素清单超过 %d 字符上限（%d）：请减少条目或公开字段'
                                % (MAX_MANIFEST_CHARS, _chars(manifest)))
        return manifest, warnings

    def preview(self, entries, rules=None):
        """试算（不写包，不写草稿状态）：给界面确认与警告。"""
        manifest, warnings = self.build_manifest(entries, rules)
        return {
            'ok': True,
            'digest': manifest_digest(manifest),
            'count': manifest['count'],
            'elements': [dict(
                ({k: element[k] for k in
                  ('ref', 'name', 'version', 'state', 'content_hash',
                   'review_status', 'detail_status', 'payload_chars')}),
                public_fields=element['disclosure']['public_fields'],
                public_description=element['disclosure']['public_description'],
                sources=len(element['sources']))
                for element in manifest['elements']],
            'rules': manifest['rules'],
            'warnings': warnings,
            'unsupported': manifest['unsupported'],
        }

    # -------------------------------------------------------------- 提交
    def commit(self, draft_id, *, expected_draft_revision, expected_story_revision,
               note=''):
        """把草稿锁定进故事包（一次 commit_package）。

        顺序固定：**先核对世界身份与原始基准**（草稿基于哪个版本创建，就只能基于它提交，
        不做隐式 rebase）→ 再看包里的提交凭据（receipt）做精确重试（无需源库，也能补索引）
        → 最后才要求当前版本等于基准。所有校验都在世界副作用之前完成。
        """
        draft = self.get_draft(draft_id)
        runtime = self.service.runtime
        current = runtime.package()
        world = draft.get('base_story_id')
        if world and current['story']['id'] != world:
            raise AssemblyError('当前故事包（%s）与这份清单的世界（%s）不同；'
                                '不跨世界复用同一份清单' % (current['story']['id'], world))
        base = draft.get('base_story_revision')
        if not isinstance(base, str) or not base:
            raise AssemblyError('这份草稿没有记录创建时的基准版本；请另建草稿后提交')
        # 1) 包内 receipt：同一草稿、同一基准、同一 digest → 精确重试（不读库、不新建版本）。
        carried = package_manifest(current['story'])
        receipt = (carried or {}).get('receipt') if carried is not None else None
        if isinstance(receipt, dict) and receipt.get('draft_id') == draft_id \
                and receipt.get('base_revision') == base:
            recorded = receipt.get('digest')
            if carried is None or manifest_digest(carried) != recorded:
                raise AssemblyError('故事包里的清单与它的提交凭据不一致（清单被改动过）；'
                                    '请重新装配并提交新版本')
            indexed = self._mark_committed(draft, current['id'], recorded,
                                           receipt.get('warnings'))
            return {'revision': current['id'], 'digest': recorded, 'reused': True,
                    'indexed': indexed,
                    'warnings': list(receipt.get('warnings') or []),
                    'note': '这份清单已由该草稿提交到当前故事包，本次只核对/补齐索引，'
                            '未新建版本'}
        # 2) 草稿自己的已提交记录（例如索引行丢了）：同样不读库。
        recorded = draft.get('manifest_digest')
        if draft.get('status') == 'committed' and recorded:
            if carried is None or manifest_digest(carried) != recorded:
                raise AssemblyError('已提交的清单与当前故事包不一致（故事包已被其他操作改动）；'
                                    '请重新装配并提交新版本')
            indexed = self._mark_committed(draft, current['id'], recorded,
                                           draft.get('manifest_warnings'))
            return {'revision': current['id'], 'digest': recorded, 'reused': True,
                    'indexed': indexed,
                    'warnings': list(draft.get('manifest_warnings') or []),
                    'note': '这份清单已在当前故事包中，本次只核对/补齐索引，未新建版本'}
        # 3) 基准必须既是草稿创建时固定的版本，也是当前版本（不允许隐式 rebase）。
        if not isinstance(expected_story_revision, str) or not expected_story_revision:
            raise AssemblyError('提交需要 expected_story_revision（请刷新后重新确认）')
        if base != expected_story_revision:
            raise AssemblyError('这份草稿是基于 %s 创建的，本次提交基于 %s；'
                                '世界已经变化，请刷新后另建草稿（不做隐式 rebase）'
                                % (base, expected_story_revision))
        if isinstance(expected_draft_revision, bool) or not isinstance(expected_draft_revision, int):
            raise AssemblyError('提交需要整数 expected_draft_revision')
        if draft.get('revision') != expected_draft_revision:
            raise AssemblyError('草稿已被其他操作更新（当前 r%s，提交 r%s），请刷新后重试'
                                % (draft.get('revision'), expected_draft_revision))
        if current['id'] != expected_story_revision:
            raise AssemblyError('故事包已变化（当前 %s，本次基于 %s）；请刷新后重新确认，'
                                '不会把旧清单悄悄挂到新世界上'
                                % (current['id'], expected_story_revision))
        manifest, warnings = self.build_manifest(draft['elements'], draft['rules'],
                                                 note or draft.get('note', ''))
        digest = manifest_digest(manifest)
        manifest['receipt'] = {'draft_id': draft_id, 'base_revision': base,
                               'digest': digest, 'committed_at': _now(),
                               'warnings': list(warnings)[:64]}
        # 4) 预留草稿版本：构建清单期间若有人改过草稿/抢先提交，这里直接失败，零世界副作用。
        if self._reserve_commit(draft) is None:
            raise AssemblyError('草稿在构建清单期间被其他操作更新（或正在提交中），'
                                '本次未提交；请刷新后重试')
        try:
            # 预留之后再读一次 pointer：另一个实例可能刚推进了故事包。若继续用函数开头缓存的
            # current，就会把别人的新版本覆盖回旧世界——这里必须失败且零覆盖。
            fresh = runtime.package()
            if fresh['id'] != expected_story_revision or \
                    (world and fresh['story']['id'] != world):
                raise AssemblyError('预留后故事包又被其他操作改动（当前 %s，本次基于 %s）；'
                                    '本次未提交，也不会用旧世界覆盖别人的版本'
                                    % (fresh['id'], expected_story_revision))
            story = copy.deepcopy(fresh['story'])
            characters = copy.deepcopy(fresh['characters'])
            story.setdefault('mechanics', {})[MECHANICS_KEY] = manifest
            # 公开范围的地点和受众必须真实存在；不存在就拒绝，不做静默兜底。
            validate_package(story, characters)
            revision = runtime.commit_package(
                story, characters,
                '元素装配：锁定 %d 个元素版本' % len(manifest['elements']))
        except BaseException:
            self._release_reservation(draft)
            raise
        # 世界已经改变：索引写不进去也只是「待补索引」，不是「提交失败」。
        indexed = self._mark_committed(draft, revision, digest, warnings)
        return {'revision': revision, 'digest': digest, 'reused': False,
                'indexed': indexed, 'warnings': warnings,
                'note': '' if indexed else
                        '世界已保存为 %s，但清单索引未写入；再次提交会幂等补齐索引' % revision}

    def _reserve_commit(self, draft):
        """短事务预留：并发写入者或重复提交都拿不到同一份草稿版本。返回新 revision 或 None。"""
        try:
            with self.service.store.transact() as db:
                row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                 ('element_draft', draft['id'])).fetchone()
                if row is None:
                    return None
                stored = json.loads(row[0])
                if stored.get('status') != 'draft' or stored.get('revision') != draft.get('revision'):
                    return None
                stored['status'] = 'committing'
                stored['revision'] = int(stored.get('revision') or 0) + 1
                stored['reserved_by'] = PROCESS_TOKEN
                stored['reserved_at'] = _now()
                stored['updated'] = _now()
                db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                           ('element_draft', draft['id'],
                            json.dumps(stored, ensure_ascii=False, separators=(',', ':'))))
        except (OSError, ValueError, sqlite3.Error):
            return None
        draft.update(status='committing', revision=stored['revision'],
                     updated=stored['updated'])
        return stored['revision']

    def _release_reservation(self, draft, any_owner=False):
        """把预留放回 draft。

        * 版本号**不回退**：预留时已经 +1，回退会造出 ABA（旧 revision 又能写）。
        * 默认只释放**本进程**持有的预留；启动恢复用 ``any_owner=True``。
        """
        try:
            with self.service.store.transact() as db:
                row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                 ('element_draft', draft['id'])).fetchone()
                if row is None:
                    return False
                stored = json.loads(row[0])
                if stored.get('status') != 'committing':
                    return False
                if not any_owner and stored.get('reserved_by') != PROCESS_TOKEN:
                    return False
                if stored.get('revision') != draft.get('revision'):
                    return False
                stored['status'] = 'draft'
                stored.pop('reserved_by', None)
                stored.pop('reserved_at', None)
                stored['updated'] = _now()
                db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                           ('element_draft', draft['id'],
                            json.dumps(stored, ensure_ascii=False, separators=(',', ':'))))
        except (OSError, ValueError, sqlite3.Error):
            return False
        draft.update(stored)
        return True

    def _mark_committed(self, draft, revision, digest, warnings=None):
        """短事务 CAS 写索引。

        * 已经是同一状态（同 revision、同 digest）→ **不写**：幂等重试零写，不推高版本号。
        * 状态必须是 draft / committing，且 revision 与调用方一致（不覆盖并发改动）。
        * 写索引失败只表示「待补索引」：世界已经改变，调用方据此给出提示。
        """
        try:
            with self.service.store.transact() as db:
                row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                 ('element_draft', draft['id'])).fetchone()
                if row is None:
                    return False
                stored = json.loads(row[0])
                if (stored.get('status') == 'committed'
                        and stored.get('committed_revision') == revision
                        and stored.get('manifest_digest') == digest):
                    return True
                if stored.get('status') not in ('draft', 'committing'):
                    return False
                if stored.get('revision') != draft.get('revision'):
                    return False  # 另一个写入者先改了草稿，不拿旧内容覆盖它
                stored['status'] = 'committed'
                stored['committed_revision'] = revision
                stored['manifest_digest'] = digest
                stored.pop('reserved_by', None)
                stored.pop('reserved_at', None)
                if warnings is not None:
                    stored['manifest_warnings'] = list(warnings)[:64]
                stored['updated'] = _now()
                db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                           ('element_draft', draft['id'],
                            json.dumps(stored, ensure_ascii=False, separators=(',', ':'))))
        except (OSError, ValueError, sqlite3.Error):
            return False
        draft.update(stored)
        return True

    # -------------------------------------------------------------- 恢复
    def recover_reservations(self):
        """恢复被中断的提交预留（应用启动时自动调用，作者也可显式调用）。

        * 只处理**不是本进程**持有的 ``committing`` 预留：本进程正在进行的提交不受影响，
          也不用现实时间超时去抢别的进程。
        * 若当前故事包（同一世界）里的 receipt 证明这份草稿确实已提交 → 补齐索引。
        * 否则放回 ``draft``，revision **不回退**（单调递增，避免 ABA）。
        * 包事务日志（``.package_transaction.json``）由 ``Runtime`` 初始化时先处理，本函数
          不参与包目录搬迁。不宣称支持多进程同时编辑故事包。
        """
        report = {'recovered': [], 'repaired': [], 'skipped': [], 'errors': []}
        for draft in self.list_drafts():
            if draft.get('status') != 'committing':
                continue
            if draft.get('reserved_by') == PROCESS_TOKEN:
                report['skipped'].append(draft['id'])
                continue
            try:
                runtime = self.service.runtime
                package = runtime.package()
                story = package['story']
                world = draft.get('base_story_id')
                if world and story['id'] != world:
                    report['errors'].append({'draft': draft['id'],
                                             'reason': '世界已切换，未动这条预留'})
                    continue
                carried = package_manifest(story)
                receipt = (carried or {}).get('receipt') or {}
                if isinstance(receipt, dict) and receipt.get('draft_id') == draft['id'] \
                        and receipt.get('base_revision') == draft.get('base_story_revision'):
                    digest = receipt.get('digest')
                    if digest and carried is not None and manifest_digest(carried) == digest \
                            and self._mark_committed(draft, package['id'], digest,
                                                    receipt.get('warnings')):
                        report['repaired'].append(draft['id'])
                        continue
                if self._release_reservation(draft, any_owner=True):
                    report['recovered'].append(draft['id'])
                else:
                    report['errors'].append({'draft': draft['id'],
                                             'reason': '恢复时草稿又被改动，跳过'})
            except (AssemblyError, OSError, ValueError) as error:
                report['errors'].append({'draft': draft['id'], 'reason': str(error)})
        return report

    def recover_on_startup(self):
        """启动时的恢复。永不阻断服务：失败只记录在 ``startup_report`` 里。"""
        try:
            self.startup_report = self.recover_reservations()
        except Exception as error:  # 启动恢复失败不应该让整个工作台起不来
            self.startup_report = {'recovered': [], 'repaired': [], 'skipped': [],
                                   'errors': [{'draft': '', 'reason': str(error)}]}
        return self.startup_report

    # -------------------------------------------------------------- 读取
    def manifest(self, revision=None):
        return package_manifest(self.service.runtime.package(revision)['story'])

    def author_view(self, revision=None):
        return author_view(self.manifest(revision))

    def player_view(self, revision=None, audience='player', session=None):
        return public_view(self.manifest(revision), audience, session)

    def pin_manifest(self, refs=None, base_revision=None):
        """生成草稿固定清单：缺省取当前包快照，显式 refs 只能是它的子集。"""
        story = self.service.runtime.package(base_revision)['story'] if base_revision else \
            self.service.runtime.package()['story']
        base = package_manifest(story)
        if not refs:
            if base is None:
                return None, []
            return json.loads(json.dumps(base)), []
        if base is None:
            raise AssemblyError('当前故事包还没有元素清单：请先在元素装配页采纳并提交，'
                                '生成器不会直接到库里补充新元素')
        return subset_manifest(base, refs)


# ------------------------------------------------------------- 作者侧摘要
AUTHOR_CONTEXT_MAX_CHARS = 3000
AUTHOR_SUMMARY_CHARS = 400


def author_context(manifest):
    """生成器读到的**有界**元素摘要：候选资料 + 作者设计，不是事实、不是已发生。

    不带完整 payload、来源或审核标记全文；摘要过长时整段省略（不切片）。
    """
    if manifest is None:
        return None
    items = []
    for element in manifest.get('elements', [])[:CONTEXT_MAX_ENTRIES]:
        entry = {'ref': element.get('ref'), 'name': element.get('name'),
                 'state': element.get('state')}
        summary = element.get('summary') or ''
        if summary and len(summary) <= AUTHOR_SUMMARY_CHARS:
            entry['summary'] = summary
        elif summary:
            entry['summary_omitted'] = '库摘要较长，生成时未携带；完整内容在故事包清单里'
        adaptation = element.get('adaptation') or {}
        if adaptation.get('note'):
            entry['design_note'] = adaptation['note']
        constraints = [item for item in (adaptation.get('constraints') or [])][:3]
        if constraints:
            entry['constraints'] = constraints
        items.append(entry)
    while items and len(json.dumps({'items': items}, ensure_ascii=False)) > AUTHOR_CONTEXT_MAX_CHARS:
        items.pop()
    return {
        'basis': '库内候选资料的作者侧摘要 + 作者设计说明：属于设计输入，'
                 '不是已核实的事实，也不表示世界里已经发生',
        'locked': True,
        'total': manifest.get('count', len(manifest.get('elements', []))),
        'items': items,
    }
