# -*- coding: utf-8 -*-
"""人类生产生活百科 · 独立素材库（SQLite）。

这是一个**与旅程数据库完全隔离**的本地素材库：不参与 app 启动、不被运行时导入、
不出现在故事 prompt 或旧存档里。默认不创建任何文件；数据库路径一律由调用方
（CLI 的 ``--db`` 或测试）显式给出。

三层边界（详见 ``docs/human-encyclopedia/database-使用说明.md``）：

1. **原始数据不动**：``docs/human-encyclopedia/*.json`` 与
   ``docs/element-catalog/*.json`` 是采集侧的交付物，本模块只读，不改写。
   每个元素的**原对象整份**存进 ``payload_json``，可逐字节还原；提升成列的只是
   少数可查询字段，因此「原字段无损」不靠字段清单的完备性保证。
2. **版本不可变**：``element_versions`` / ``source_versions`` 只插入、不更新。
   ``content_hash`` 是原对象的 canonical JSON 哈希；同一 (namespace, id) 下同哈希
   → 不新增版本（幂等）；内容变了 → version+1，旧版本仍可读。
3. **只读查询**：``search`` / ``get`` / ``versions`` / ``tags`` / ``stats`` /
   ``export`` 一律用 ``mode=ro`` 打开连接，且不执行任何建表语句——库不存在就是
   错误，而不是顺手建一个空库。

证据固定（schema 2）
--------------------
``element_sources`` 记录 ``source_version``：每个元素版本固定「写入当时看到的
来源版本」。之后来源升级成 v2，元素 v1 仍然显示 v1 的 title/url/access/payload，
不会静默换成新证据。需要新证据就得显式新写一个元素版本（新内容 → 新版本）。
schema 1 的库不能自动升级（没有 pin 信息可恢复），会明确报错而不是猜。

命名空间
--------
主键是 ``(namespace, element_id)``：不同命名空间**允许**出现同一个 ``element_id``
（原六组 ID 自带前缀、互不相同，但未来的现实/人类分期分组可能出现同名 ID）。
因此：

* 查询按 ``namespace`` 限定；跨库按 ID 查一次时，若该 ID 在多个命名空间存在，
  ``get`` 抛 :class:`Ambiguous` 并列出候选，不猜。
* 同一命名空间内改内容是正常的新版本；**跨命名空间不会互相覆盖**。

来源
----
元素里的 ``source_ids`` 必须能解析到真实来源：同批 → 本命名空间 → 全局唯一。
找不到或全局歧义 → 整批拒绝（半批零写入）。``access: read`` 只表示采集侧声称读过
正文，**不表示已经事实核实**；``review_status`` / ``detail_status`` 只记录 payload
里显式写下的值，缺失时派生 ``needs_review`` / ``needs_detail``，绝不自动升格。

关联
----
``related_ids`` / ``related_catalog_ids`` 指向的元素可能属于后面的批次或别的组。
这类关联**原样保存**，状态在查询/导出时按「目标此刻是否存在」计算：
``resolved`` / ``pending``（找不到）/ ``ambiguous``（多个命名空间都有）。后续批次
把目标导进来之后，同一行关系自然变成 ``resolved``，不需要改写历史。

旧的 ``element-catalog`` 六组（274 元素）与新 ``human-encyclopedia`` 七节不同，
由显式 adapter 适配并记录映射（``DETAILS_MAP`` / ``element_versions.details_map_json``）；
``story_consequences → story_uses``、``adaptation_limits → historical_scope`` 只是
七节命名对齐的语义近似，原始分节名与原文都留在 payload 里。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = 2
EXPORT_FORMAT = 'human-encyclopedia-export'
EXPORT_VERSION = 2

ADAPTER_HUMAN = 'human-encyclopedia'
ADAPTER_CATALOG = 'element-catalog'
ADAPTERS = (ADAPTER_HUMAN, ADAPTER_CATALOG)

# 新 schema（human-encyclopedia）的七节；顺序即规范顺序。
DETAIL_SECTIONS = (
    'definition',
    'mechanism',
    'conditions',
    'exceptions',
    'story_uses',
    'historical_scope',
    'evidence_and_uncertainty',
)
# 旧 schema（element-catalog）七节 → 新七节。键是旧字段名，值是规范节名。
LEGACY_DETAILS_KEYS = {
    'definition': 'definition',
    'mechanism': 'mechanism',
    'conditions': 'conditions',
    'exceptions': 'exceptions',
    'story_consequences': 'story_uses',
    'adaptation_limits': 'historical_scope',
    'evidence_and_uncertainty': 'evidence_and_uncertainty',
}
# 适配说明：语义近似处必须点名，避免把「改编边界」当成现实史或把「剧情后果」当成用法。
# 查询时通过 ``LEGACY_DETAILS_KEYS`` 与 ``details_map`` 同时暴露原字段名，CLI 的 get 会打印出来。

REVIEW_STATUSES = ('needs_review', 'reviewed_detail', 'reviewed', 'rejected')
DETAIL_STATUSES = ('summary_only', 'needs_detail', 'reviewed_detail')

# 有限上限：任何一项超限都整批拒绝，不做截断（截断会静默损坏原始资料）。
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
MAX_ELEMENTS = 5000
MAX_SOURCES = 5000
MAX_ELEMENT_BYTES = 96 * 1024
MAX_TEXT_CHARS = 20000
MAX_NAME_CHARS = 200
MAX_ID_CHARS = 96
MAX_TAG_CHARS = 64
MAX_TAGS = 64
MAX_ALIASES = 64
MAX_SOURCE_IDS = 64
MAX_RELATIONS = 64
MAX_DETAIL_SECTIONS = 32
MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50

_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_.:-]*$')
_TAG_RE = re.compile(r'^[a-z0-9][a-z0-9_.:-]*$')


# --------------------------------------------------------------------------- 错误
class EncyclopediaError(ValueError):
    """百科库的统一错误基类。所有拒绝路径都保证「半批零写入」。"""


class InvalidDocument(EncyclopediaError):
    """文档结构/字段非法。整批拒绝。"""


class Conflict(EncyclopediaError):
    """与库内已有事实冲突（版本哈希不符、命名空间归属不同、批次重复但内容不同）。"""


class LimitExceeded(EncyclopediaError):
    """超过有限上限。"""


class NotFound(EncyclopediaError):
    """查不到条目/版本/库文件。"""


class Ambiguous(EncyclopediaError):
    """同一个 ID 在多个命名空间存在，必须显式指定 namespace。"""


# --------------------------------------------------------------------------- 工具
def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _reject_constant(name):
    raise InvalidDocument('JSON 含非法常量 %r：不接受 NaN / Infinity' % name)


def loads_json(text):
    """严格解析：NaN / Infinity / -Infinity 一律拒绝。"""
    if not isinstance(text, str):
        raise InvalidDocument('JSON 文本必须是字符串')
    if len(text.encode('utf-8')) > MAX_DOCUMENT_BYTES:
        raise LimitExceeded('JSON 文本超过 %d 字节上限' % MAX_DOCUMENT_BYTES)
    try:
        return json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise InvalidDocument('JSON 解析失败：%s' % exc) from exc


def check_json_value(value, path='$'):
    """递归校验：只允许 dict / list / str / int / float(bool 归入 int) / None。

    浮点必须是有限值（拒绝 NaN / inf）；字典键必须是字符串。
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidDocument('%s 的对象键必须是字符串（得到 %r）' % (path, key))
            check_json_value(item, '%s.%s' % (path, key))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            check_json_value(item, '%s[%d]' % (path, index))
        return
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str) or value is None:
        return
    if isinstance(value, float):
        if value != value or value in (float('inf'), float('-inf')):
            raise InvalidDocument('%s 是 NaN / Infinity，拒绝入库' % path)
        return
    raise InvalidDocument('%s 的类型 %s 不允许入库' % (path, type(value).__name__))


def canonical_json(value):
    """稳定序列化：排序键、紧凑分隔符、不允许 NaN。哈希与导出都基于它。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def payload_hash(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def norm_text(value):
    """检索用的归一化：NFKC、去首尾空白、casefold、压缩空白。"""
    text = unicodedata.normalize('NFKC', value).strip().casefold()
    return re.sub(r'\s+', ' ', text)


def _like_escape(text):
    return text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _check_id(value, label):
    if not isinstance(value, str) or not value:
        raise InvalidDocument('%s 必须是非空字符串' % label)
    if len(value) > MAX_ID_CHARS:
        raise LimitExceeded('%s 超过 %d 字符：%r' % (label, MAX_ID_CHARS, value))
    if not _ID_RE.match(value):
        raise InvalidDocument('%s 含非法字符（只允许小写字母/数字/下划线/点/冒号/连字符）：%r' % (label, value))
    return value


def _check_text(value, label, limit=MAX_TEXT_CHARS, allow_empty=False):
    if not isinstance(value, str):
        raise InvalidDocument('%s 必须是字符串' % label)
    if len(value) > limit:
        raise LimitExceeded('%s 超过 %d 字符' % (label, limit))
    if not allow_empty and not value.strip():
        raise InvalidDocument('%s 不能为空' % label)
    return value


def _check_tag(value):
    _check_text(value, '标签', MAX_TAG_CHARS)
    if not _TAG_RE.match(value):
        raise InvalidDocument('标签必须是英文小写 snake_case（可含点/冒号/连字符）：%r' % value)
    return value


def _str_list(value, label, limit):
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidDocument('%s 必须是数组' % label)
    if len(value) > limit:
        raise LimitExceeded('%s 超过 %d 项' % (label, limit))
    out = []
    for item in value:
        _check_text(item, label + ' 元素', MAX_NAME_CHARS)
        out.append(item)
    return out


def dedupe(values, key=norm_text):
    """保序去重（按归一化键）。标签/别名/引用都走这里。"""
    seen = set()
    out = []
    for value in values:
        key_value = key(value)
        if key_value in seen:
            continue
        seen.add(key_value)
        out.append(value)
    return out


# --------------------------------------------------------------------------- 文档适配
@dataclass
class PreparedSource:
    source_id: str
    payload: dict
    payload_json: str
    payload_hash: str
    version: int | None = None


@dataclass
class PreparedElement:
    element_id: str
    payload: dict
    payload_json: str
    content_hash: str
    name: str
    summary: str
    aliases: list
    tags: list
    details: dict
    details_map: dict
    details_extra: dict
    source_ids: list
    relations: list
    review_status: str
    detail_status: str
    version: int | None = None
    # 导出/还原时携带的证据固定点：source_id -> (source_namespace, source_version)。
    # 导入采集 JSON 时为 None（按「同批 → 本命名空间 → 全局唯一」现场解析并固定下来）。
    source_pins: dict | None = None


@dataclass
class PreparedBatch:
    namespace: str
    group_id: str
    adapter: str
    schema_kind: str
    legacy_schema: bool
    status: str
    meta: dict
    sources: list
    elements: list
    batch_hash: str
    # 还原导出文件时，元素的 pin 可能指向「本文档里另一个命名空间、稍后才写入」的来源。
    # 此时单批内不查 DB（改由 restore_document 先校验文档索引、提交前做全库完整性检查）。
    verify_pins_against_db: bool = True


@dataclass
class ImportResult:
    namespace: str
    group_id: str
    adapter: str
    batch_id: int
    batch_hash: str
    idempotent: bool
    elements: int = 0
    element_versions: int = 0
    unchanged_elements: int = 0
    sources: int = 0
    source_versions: int = 0
    unchanged_sources: int = 0
    relations: int = 0
    unresolved_relations: list = field(default_factory=list)
    ambiguous_relations: list = field(default_factory=list)
    shared_element_ids: list = field(default_factory=list)

    def as_dict(self):
        return {
            'namespace': self.namespace,
            'group_id': self.group_id,
            'adapter': self.adapter,
            'batch_id': self.batch_id,
            'batch_hash': self.batch_hash,
            'idempotent': self.idempotent,
            'elements': self.elements,
            'element_versions_written': self.element_versions,
            'unchanged_elements': self.unchanged_elements,
            'sources': self.sources,
            'source_versions_written': self.source_versions,
            'unchanged_sources': self.unchanged_sources,
            'relations': self.relations,
            'unresolved_relations': self.unresolved_relations,
            'ambiguous_relations': self.ambiguous_relations,
            'shared_element_ids': self.shared_element_ids,
        }


def detect_adapter(document):
    """按元素实际形状识别 adapter；识别不了就报错，不猜。"""
    if not isinstance(document, dict):
        raise InvalidDocument('文档必须是 JSON 对象')
    elements = document.get('elements')
    if not isinstance(elements, list) or not elements:
        raise InvalidDocument(
            '文档没有 elements 数组：只接受元素目录，不接受 shared-themes 聚类或规范文档'
        )
    sample = [item for item in elements if isinstance(item, dict)]
    if not sample:
        raise InvalidDocument('elements 里没有对象')
    if all('tags' in item for item in sample):
        return ADAPTER_HUMAN
    if all('category' in item for item in sample):
        return ADAPTER_CATALOG
    raise InvalidDocument('无法识别 schema：元素既没有 tags（新 schema）也没有 category（旧 schema）')


def _section_text(value, element_id, key):
    """规范七节之一必须是字符串。类型不对就拒绝，而不是静默转成 str。"""
    if not isinstance(value, str):
        raise InvalidDocument('元素 %s 的 details.%s 必须是字符串（得到 %s）'
                              % (element_id, key, type(value).__name__))
    _check_text(value, '元素 %s 的 details.%s' % (element_id, key))
    return value


def _prepare_details(raw, element_id, legacy):
    if not isinstance(raw, dict) or not raw:
        raise InvalidDocument('元素 %s 的 details 必须是非空对象' % element_id)
    if len(raw) > MAX_DETAIL_SECTIONS:
        raise LimitExceeded('元素 %s 的 details 分节数超过 %d' % (element_id, MAX_DETAIL_SECTIONS))
    for key in raw:
        if not isinstance(key, str):
            raise InvalidDocument('元素 %s 的 details 键必须是字符串' % element_id)
    # 规范七节必须是字符串；其余分册（如 western 的 parameter_dimensions
    # 是对象而非字符串）按原样保留到 details_extra，不强制统一类型。
    used = set()
    details = {}
    details_map = {}
    if legacy:
        for legacy_key, canonical in LEGACY_DETAILS_KEYS.items():
            if legacy_key not in raw:
                continue
            details[canonical] = _section_text(raw[legacy_key], element_id, legacy_key)
            details_map[canonical] = legacy_key
            used.add(legacy_key)
    else:
        for canonical in DETAIL_SECTIONS:
            if canonical not in raw:
                raise InvalidDocument('元素 %s 缺少必需分节 details.%s' % (element_id, canonical))
            details[canonical] = _section_text(raw[canonical], element_id, canonical)
            details_map[canonical] = canonical
            used.add(canonical)
        # 旧字段名若出现在新 schema 里，按旧映射兜底，仍记录映射来源。
        for legacy_key, canonical in LEGACY_DETAILS_KEYS.items():
            if canonical in details or legacy_key not in raw:
                continue
            details[canonical] = _section_text(raw[legacy_key], element_id, legacy_key)
            details_map[canonical] = legacy_key
            used.add(legacy_key)
    missing = [section for section in DETAIL_SECTIONS if section not in details]
    if missing:
        raise InvalidDocument('元素 %s 的 details 缺少七节：%s' % (element_id, ', '.join(missing)))
    extra = {}
    for key, value in raw.items():
        if key in used:
            continue
        extra[key] = value
    return details, details_map, extra


def _prepare_element(raw, legacy, adapter):
    if not isinstance(raw, dict):
        raise InvalidDocument('elements 的每一项必须是对象')
    element_id = _check_id(raw.get('id'), '元素 id')
    name = _check_text(raw.get('name'), '元素 %s 的 name' % element_id, MAX_NAME_CHARS)
    check_json_value(raw, '元素 %s' % element_id)
    payload_json = canonical_json(raw)
    if len(payload_json.encode('utf-8')) > MAX_ELEMENT_BYTES:
        raise LimitExceeded('元素 %s 超过 %d 字节' % (element_id, MAX_ELEMENT_BYTES))

    aliases = dedupe(_str_list(raw.get('aliases'), '元素 %s 的 aliases' % element_id, MAX_ALIASES))
    if len(aliases) > MAX_ALIASES:
        raise LimitExceeded('元素 %s 的别名超过 %d 项' % (element_id, MAX_ALIASES))

    # 标签：新 schema 自带 tags（原样保留）；两组都追加命名空间化的 category:/genre:。
    raw_tags = _str_list(raw.get('tags'), '元素 %s 的 tags' % element_id, MAX_TAGS) if not legacy else []
    tags = list(raw_tags)
    category = raw.get('category')
    if category is not None:
        tags.append('category:' + _check_tag(category))
    genres = raw.get('genres')
    if genres is not None:
        if not isinstance(genres, list):
            raise InvalidDocument('元素 %s 的 genres 必须是数组' % element_id)
        for genre in genres:
            tags.append('genre:' + _check_tag(_check_text(genre, '元素 %s 的 genre' % element_id, MAX_TAG_CHARS)))
    tags = dedupe([_check_tag(tag) for tag in tags])
    if len(tags) > MAX_TAGS:
        raise LimitExceeded('元素 %s 的标签超过 %d 项' % (element_id, MAX_TAGS))

    details, details_map, details_extra = _prepare_details(raw.get('details'), element_id, legacy)

    summary = raw.get('summary')
    if summary is None:
        summary = ''
    _check_text(summary, '元素 %s 的 summary' % element_id, allow_empty=True)

    source_ids = dedupe(_str_list(raw.get('source_ids'), '元素 %s 的 source_ids' % element_id, MAX_SOURCE_IDS))
    for source_id in source_ids:
        _check_id(source_id, '元素 %s 的 source_id' % element_id)

    relations = []
    for key, rel_kind in (('related_ids', 'related'), ('related_catalog_ids', 'catalog_related')):
        for target in _str_list(raw.get(key), '元素 %s 的 %s' % (element_id, key), MAX_RELATIONS):
            _check_id(target, '元素 %s 的关联目标' % element_id)
            relations.append((rel_kind, target))
    relations = dedupe(relations, key=lambda pair: (pair[0], norm_text(pair[1])))
    if len(relations) > MAX_RELATIONS:
        raise LimitExceeded('元素 %s 的关联超过 %d 项' % (element_id, MAX_RELATIONS))

    review_status = raw.get('review_status')
    if review_status is None:
        review_status = 'needs_review'
    if review_status not in REVIEW_STATUSES:
        raise InvalidDocument('元素 %s 的 review_status 非法：%r' % (element_id, review_status))
    detail_status = raw.get('detail_status')
    if detail_status is None:
        detail_status = 'needs_detail'
    if detail_status not in DETAIL_STATUSES:
        raise InvalidDocument('元素 %s 的 detail_status 非法：%r' % (element_id, detail_status))

    return PreparedElement(
        element_id=element_id,
        payload=raw,
        payload_json=payload_json,
        content_hash=hashlib.sha256(payload_json.encode('utf-8')).hexdigest(),
        name=name,
        summary=summary,
        aliases=aliases,
        tags=tags,
        details=details,
        details_map=details_map,
        details_extra=details_extra,
        source_ids=source_ids,
        relations=relations,
        review_status=review_status,
        detail_status=detail_status,
    )


def _prepare_source(raw):
    if not isinstance(raw, dict):
        raise InvalidDocument('sources 的每一项必须是对象')
    source_id = _check_id(raw.get('id'), '来源 id')
    check_json_value(raw, '来源 %s' % source_id)
    payload_json = canonical_json(raw)
    if len(payload_json.encode('utf-8')) > MAX_ELEMENT_BYTES:
        raise LimitExceeded('来源 %s 超过 %d 字节' % (source_id, MAX_ELEMENT_BYTES))
    for key in ('title', 'url', 'access', 'supports', 'rights_note'):
        if key in raw:
            _check_text(raw[key], '来源 %s 的 %s' % (source_id, key), allow_empty=True)
    access = raw.get('access')
    if access is not None and access not in ('read', 'search_only', 'unavailable'):
        raise InvalidDocument('来源 %s 的 access 非法：%r' % (source_id, access))
    return PreparedSource(
        source_id=source_id,
        payload=raw,
        payload_json=payload_json,
        payload_hash=hashlib.sha256(payload_json.encode('utf-8')).hexdigest(),
    )


def prepare_document(document, *, namespace=None, adapter=None):
    """把一份采集侧 JSON 变成可原子写入的批次。只验不改：原始 payload 原样保留。"""
    if not isinstance(document, dict):
        raise InvalidDocument('文档必须是 JSON 对象')
    resolved_adapter = adapter or detect_adapter(document)
    if resolved_adapter not in ADAPTERS:
        raise InvalidDocument('未知 adapter：%r（可选 %s）' % (resolved_adapter, ', '.join(ADAPTERS)))
    legacy = resolved_adapter == ADAPTER_CATALOG

    group_id = document.get('group')
    if group_id is None and namespace is None:
        raise InvalidDocument('文档缺少 group，且未显式指定 namespace')
    if group_id is not None:
        _check_id(group_id, '文档 group')
    resolved_namespace = _check_id(namespace or group_id, '命名空间')

    raw_elements = document.get('elements')
    if not isinstance(raw_elements, list) or not raw_elements:
        raise InvalidDocument('文档没有 elements 数组，拒绝导入')
    if len(raw_elements) > MAX_ELEMENTS:
        raise LimitExceeded('单批元素数超过 %d' % MAX_ELEMENTS)
    raw_sources = document.get('sources') or []
    if not isinstance(raw_sources, list):
        raise InvalidDocument('sources 必须是数组')
    if len(raw_sources) > MAX_SOURCES:
        raise LimitExceeded('单批来源数超过 %d' % MAX_SOURCES)

    sources = []
    seen_sources = {}
    for raw in raw_sources:
        source = _prepare_source(raw)
        if source.source_id in seen_sources:
            raise InvalidDocument('同一文档内来源 id 重复：%s' % source.source_id)
        seen_sources[source.source_id] = source
        sources.append(source)

    elements = []
    seen_elements = {}
    for raw in raw_elements:
        element = _prepare_element(raw, legacy, resolved_adapter)
        if element.element_id in seen_elements:
            raise InvalidDocument('同一文档内元素 id 重复：%s' % element.element_id)
        seen_elements[element.element_id] = element
        elements.append(element)

    meta = {key: value for key, value in document.items() if key not in ('elements', 'sources')}
    status = document.get('status')
    if status is not None:
        _check_text(status, '文档 status', MAX_NAME_CHARS)
    schema_kind = 'human' if not legacy else 'element-catalog'
    batch_hash = payload_hash({
        'namespace': resolved_namespace,
        'adapter': resolved_adapter,
        'document': document,
    })
    return PreparedBatch(
        namespace=resolved_namespace,
        group_id=_check_id(group_id or resolved_namespace, '命名空间'),
        adapter=resolved_adapter,
        schema_kind=schema_kind,
        legacy_schema=legacy,
        status=status,
        meta=meta,
        sources=sources,
        elements=elements,
        batch_hash=batch_hash,
    )


# --------------------------------------------------------------------------- 数据库
_DDL = (
    """CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS groups (
        namespace TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        schema_kind TEXT NOT NULL,
        adapter TEXT NOT NULL,
        legacy_schema INTEGER NOT NULL,
        status TEXT,
        meta_json TEXT NOT NULL,
        first_batch_id INTEGER,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sources (
        namespace TEXT NOT NULL,
        source_id TEXT NOT NULL,
        current_version INTEGER NOT NULL,
        title TEXT,
        url TEXT,
        access TEXT,
        payload_json TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (namespace, source_id)
    )""",
    """CREATE TABLE IF NOT EXISTS source_versions (
        namespace TEXT NOT NULL,
        source_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        batch_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (namespace, source_id, version)
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS source_versions_hash
        ON source_versions (namespace, source_id, payload_hash)""",
    """CREATE TABLE IF NOT EXISTS elements (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        group_id TEXT NOT NULL,
        current_version INTEGER NOT NULL,
        name TEXT NOT NULL,
        review_status TEXT NOT NULL,
        detail_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id)
    )""",
    """CREATE TABLE IF NOT EXISTS element_versions (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        schema_kind TEXT NOT NULL,
        adapter TEXT NOT NULL,
        legacy_schema INTEGER NOT NULL,
        name TEXT NOT NULL,
        summary TEXT,
        review_status TEXT NOT NULL,
        detail_status TEXT NOT NULL,
        details_json TEXT NOT NULL,
        details_map_json TEXT NOT NULL,
        details_extra_json TEXT NOT NULL,
        batch_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id, version)
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS element_versions_hash
        ON element_versions (namespace, element_id, content_hash)""",
    """CREATE TABLE IF NOT EXISTS element_tags (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        tag TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id, version, tag)
    )""",
    """CREATE INDEX IF NOT EXISTS element_tags_lookup ON element_tags (namespace, tag)""",
    """CREATE TABLE IF NOT EXISTS element_names (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        kind TEXT NOT NULL,
        value TEXT NOT NULL,
        norm TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id, version, kind, value)
    )""",
    """CREATE INDEX IF NOT EXISTS element_names_norm ON element_names (namespace, norm)""",
    """CREATE TABLE IF NOT EXISTS element_sources (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        source_namespace TEXT NOT NULL,
        source_version INTEGER NOT NULL,
        status TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id, version, source_id)
    )""",
    """CREATE INDEX IF NOT EXISTS element_sources_pin
        ON element_sources (source_namespace, source_id, source_version)""",
    """CREATE TABLE IF NOT EXISTS element_relations (
        namespace TEXT NOT NULL,
        element_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        rel_kind TEXT NOT NULL,
        target_id TEXT NOT NULL,
        PRIMARY KEY (namespace, element_id, version, rel_kind, target_id)
    )""",
    """CREATE TABLE IF NOT EXISTS import_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        namespace TEXT NOT NULL,
        group_id TEXT NOT NULL,
        batch_hash TEXT NOT NULL,
        kind TEXT NOT NULL,
        adapter TEXT NOT NULL,
        schema_kind TEXT NOT NULL,
        legacy_schema INTEGER NOT NULL,
        element_count INTEGER NOT NULL,
        source_count INTEGER NOT NULL,
        element_versions INTEGER NOT NULL,
        source_versions INTEGER NOT NULL,
        unchanged_elements INTEGER NOT NULL,
        unresolved_relations INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (namespace, batch_hash)
    )""",
)


def _table_exists(conn, name):
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def read_schema_version(conn):
    if not _table_exists(conn, 'meta'):
        return None
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    return None if row is None else int(row[0])


def schema_mismatch(version):
    """schema 版本不符时的明确拒绝理由（不隐式升级、不猜）。"""
    message = '数据库 schema_version=%d，本模块只支持 %d' % (version, SCHEMA_VERSION)
    if version == 1:
        message += ('：schema 1 不记录来源固定版本（element_sources.source_version），'
                    '无法反推历史证据，因此不支持就地升级。请用新路径重建库后重新导入采集 JSON。')
    return Conflict(message)


def initialize_schema(conn):
    for statement in _DDL:
        conn.execute(statement)
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('created_at', ?)", (_now(),))
    conn.commit()


def open_writable(db_path):
    """导入/建库用连接。会按需创建文件与 schema；读路径不走这里。"""
    path = Path(db_path)
    if path.exists() and path.is_dir():
        raise EncyclopediaError('数据库路径是目录：%s' % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        version = read_schema_version(conn)
        if version is None:
            if _table_exists(conn, 'elements'):
                raise Conflict('数据库缺少 meta 表但已有元素表：不是本模块建的库，拒绝写入')
            initialize_schema(conn)
        elif version != SCHEMA_VERSION:
            raise schema_mismatch(version)
    except BaseException:
        conn.close()
        raise
    return conn


def open_readonly(db_path):
    """查询用只读连接：库不存在就报错，绝不隐式建库。"""
    path = Path(db_path)
    if not path.exists():
        raise NotFound('数据库不存在：%s' % path)
    if path.is_dir():
        raise EncyclopediaError('数据库路径是目录：%s' % path)
    uri = 'file:%s?mode=ro' % quote(path.resolve().as_posix(), safe='/:')
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        conn.execute('PRAGMA query_only=1')
        version = read_schema_version(conn)
        if version is None:
            raise Conflict('不是百科库（缺少 meta.schema_version）：%s' % path)
        if version != SCHEMA_VERSION:
            raise schema_mismatch(version)
    except BaseException:
        # 只读连接出错也必须先关掉，否则 Windows 上文件会被锁住。
        conn.close()
        raise
    return conn


# --------------------------------------------------------------------------- 写入
def _group_row(conn, namespace):
    return conn.execute(
        'SELECT namespace, group_id, schema_kind, adapter, legacy_schema, status, meta_json FROM groups WHERE namespace=?',
        (namespace,),
    ).fetchone()


def _ensure_group(conn, batch, batch_id):
    row = _group_row(conn, batch.namespace)
    meta_json = canonical_json(batch.meta)
    if row is None:
        conn.execute(
            'INSERT INTO groups (namespace, group_id, schema_kind, adapter, legacy_schema, status, meta_json, first_batch_id, created_at)'
            ' VALUES (?,?,?,?,?,?,?,?,?)',
            (batch.namespace, batch.group_id, batch.schema_kind, batch.adapter,
             1 if batch.legacy_schema else 0, batch.status, meta_json, batch_id, _now()),
        )
        return
    if row[1] != batch.group_id:
        raise Conflict('命名空间 %s 已属于 group %s，不能改挂到 %s' % (batch.namespace, row[1], batch.group_id))
    if row[3] != batch.adapter:
        raise Conflict('命名空间 %s 已按 adapter=%s 导入，不能改用 %s' % (batch.namespace, row[3], batch.adapter))
    conn.execute('UPDATE groups SET status=?, meta_json=? WHERE namespace=?', (batch.status, meta_json, batch.namespace))


def _current_source(conn, namespace, source_id):
    return conn.execute(
        'SELECT current_version, payload_hash FROM sources WHERE namespace=? AND source_id=?',
        (namespace, source_id),
    ).fetchone()


def _source_hash_exists(conn, namespace, source_id, digest):
    row = conn.execute(
        'SELECT version FROM source_versions WHERE namespace=? AND source_id=? AND payload_hash=?',
        (namespace, source_id, digest),
    ).fetchone()
    return None if row is None else int(row[0])


def _max_source_version(conn, namespace, source_id):
    row = conn.execute(
        'SELECT MAX(version) FROM source_versions WHERE namespace=? AND source_id=?',
        (namespace, source_id),
    ).fetchone()
    return 0 if row is None or row[0] is None else int(row[0])


def _insert_sources(conn, batch, batch_id, result):
    for source in batch.sources:
        existing = _source_hash_exists(conn, batch.namespace, source.source_id, source.payload_hash)
        if existing is not None:
            result.unchanged_sources += 1
            if source.version is not None and source.version != existing:
                raise Conflict('来源 %s/%s 的指定版本 %d 与同哈希已有版本 %d 不符'
                               % (batch.namespace, source.source_id, source.version, existing))
            continue
        if source.version is None:
            version = _max_source_version(conn, batch.namespace, source.source_id) + 1
        else:
            taken = conn.execute(
                'SELECT payload_hash FROM source_versions WHERE namespace=? AND source_id=? AND version=?',
                (batch.namespace, source.source_id, source.version),
            ).fetchone()
            if taken is not None:
                raise Conflict('来源 %s/%s 的版本 %d 已存在且内容不同'
                               % (batch.namespace, source.source_id, source.version))
            version = source.version
        conn.execute(
            'INSERT INTO source_versions (namespace, source_id, version, payload_json, payload_hash, batch_id, created_at)'
            ' VALUES (?,?,?,?,?,?,?)',
            (batch.namespace, source.source_id, version, source.payload_json, source.payload_hash, batch_id, _now()),
        )
        payload = source.payload
        conn.execute(
            'INSERT INTO sources (namespace, source_id, current_version, title, url, access, payload_json, payload_hash, created_at)'
            ' VALUES (?,?,?,?,?,?,?,?,?)'
            ' ON CONFLICT(namespace, source_id) DO UPDATE SET'
            ' current_version=excluded.current_version, title=excluded.title, url=excluded.url,'
            ' access=excluded.access, payload_json=excluded.payload_json, payload_hash=excluded.payload_hash',
            (batch.namespace, source.source_id, version,
             payload.get('title'), payload.get('url'), payload.get('access'),
             source.payload_json, source.payload_hash, _now()),
        )
        result.source_versions += 1


def resolve_source(conn, own_namespace, source_id, batch_sources):
    """解析来源**并固定版本**：返回 (source_namespace, source_version, status)。

    证据不可变的关键在第三项：元素版本一旦写入，就把「当时看到的来源版本」记进
    ``element_sources.source_version``，之后来源再更新也不会改变旧元素版本的证据。

    解析顺序：同批 → 本命名空间 → 全局唯一。歧义或缺失都是拒绝。
    """
    prepared = batch_sources.get(source_id)
    if prepared is not None:
        # 同批写入：按内容哈希精确定位刚写入的版本，不拿 current_version 猜。
        row = conn.execute(
            'SELECT version FROM source_versions WHERE namespace=? AND source_id=? AND payload_hash=?',
            (own_namespace, source_id, prepared.payload_hash),
        ).fetchone()
        if row is None:
            raise Conflict('来源 %s/%s 在本批次里没有写入版本（内部顺序错误）' % (own_namespace, source_id))
        return own_namespace, int(row[0]), 'batch'
    row = conn.execute(
        'SELECT current_version FROM sources WHERE namespace=? AND source_id=?', (own_namespace, source_id)
    ).fetchone()
    if row is not None:
        return own_namespace, int(row[0]), 'resolved'
    rows = conn.execute(
        'SELECT namespace, current_version FROM sources WHERE source_id=? ORDER BY namespace', (source_id,)
    ).fetchall()
    if len(rows) == 1:
        return rows[0][0], int(rows[0][1]), 'resolved_external'
    if not rows:
        raise InvalidDocument('来源 %s 在批次、本命名空间与库内都找不到' % source_id)
    raise InvalidDocument('来源 %s 在多个命名空间存在（%s），无法唯一解析'
                          % (source_id, ', '.join(row[0] for row in rows)))


def pin_exists(conn, source_namespace, source_id, source_version):
    """固定的来源版本必须真实存在，否则该批次整批拒绝。"""
    row = conn.execute(
        'SELECT 1 FROM source_versions WHERE namespace=? AND source_id=? AND version=?',
        (source_namespace, source_id, source_version),
    ).fetchone()
    return row is not None


def _relation_status(conn, own_namespace, target_id):
    rows = conn.execute('SELECT namespace FROM elements WHERE element_id=? ORDER BY namespace', (target_id,)).fetchall()
    namespaces = [row[0] for row in rows]
    if own_namespace in namespaces:
        return own_namespace, 'resolved'
    if len(namespaces) == 1:
        return namespaces[0], 'resolved'
    if not namespaces:
        return None, 'pending'
    return None, 'ambiguous'


def _max_element_version(conn, namespace, element_id):
    row = conn.execute(
        'SELECT MAX(version) FROM element_versions WHERE namespace=? AND element_id=?',
        (namespace, element_id),
    ).fetchone()
    return 0 if row is None or row[0] is None else int(row[0])


def _element_hash_exists(conn, namespace, element_id, digest):
    row = conn.execute(
        'SELECT version FROM element_versions WHERE namespace=? AND element_id=? AND content_hash=?',
        (namespace, element_id, digest),
    ).fetchone()
    return None if row is None else int(row[0])


def _insert_element_version(conn, batch, element, batch_id, version):
    conn.execute(
        'INSERT INTO element_versions (namespace, element_id, version, content_hash, payload_json, schema_kind,'
        ' adapter, legacy_schema, name, summary, review_status, detail_status, details_json, details_map_json,'
        ' details_extra_json, batch_id, created_at)'
        ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (batch.namespace, element.element_id, version, element.content_hash, element.payload_json,
         batch.schema_kind, batch.adapter, 1 if batch.legacy_schema else 0, element.name, element.summary,
         element.review_status, element.detail_status, canonical_json(element.details),
         canonical_json(element.details_map), canonical_json(element.details_extra), batch_id, _now()),
    )
    now = _now()
    conn.execute(
        'INSERT INTO elements (namespace, element_id, group_id, current_version, name, review_status, detail_status,'
        ' created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)'
        ' ON CONFLICT(namespace, element_id) DO UPDATE SET'
        ' current_version=excluded.current_version, name=excluded.name,'
        ' review_status=excluded.review_status, detail_status=excluded.detail_status, updated_at=excluded.updated_at',
        (batch.namespace, element.element_id, batch.group_id, version, element.name,
         element.review_status, element.detail_status, now, now),
    )
    conn.executemany(
        'INSERT OR IGNORE INTO element_tags (namespace, element_id, version, tag) VALUES (?,?,?,?)',
        [(batch.namespace, element.element_id, version, tag) for tag in element.tags],
    )
    name_rows = [(batch.namespace, element.element_id, version, 'name', element.name, norm_text(element.name))]
    for alias in element.aliases:
        name_rows.append((batch.namespace, element.element_id, version, 'alias', alias, norm_text(alias)))
    conn.executemany(
        'INSERT OR IGNORE INTO element_names (namespace, element_id, version, kind, value, norm) VALUES (?,?,?,?,?,?)',
        name_rows,
    )


def _insert_element_sources(conn, batch, element, version, batch_sources):
    """写入该元素版本引用的来源，并**固定当时的来源版本**（pin）。

    给了 ``element.source_pins``（导出/还原）就用它，并逐项验证版本存在；
    否则按同批 → 本命名空间 → 全局唯一的顺序现场解析并固定。
    """
    rows = []
    for source_id in element.source_ids:
        if element.source_pins is not None:
            source_namespace, source_version, status = element.source_pins[source_id]
            if batch.verify_pins_against_db and not pin_exists(
                    conn, source_namespace, source_id, source_version):
                raise InvalidDocument('元素 %s 固定的来源 %s/%s v%s 不存在'
                                      % (element.element_id, source_namespace, source_id, source_version))
        else:
            source_namespace, source_version, status = resolve_source(
                conn, batch.namespace, source_id, batch_sources)
        rows.append((batch.namespace, element.element_id, version, source_id,
                     source_namespace, source_version, status))
    conn.executemany(
        'INSERT OR IGNORE INTO element_sources'
        ' (namespace, element_id, version, source_id, source_namespace, source_version, status)'
        ' VALUES (?,?,?,?,?,?,?)',
        rows,
    )
    return rows


def _insert_element_relations(conn, batch, element, version):
    rows = [(batch.namespace, element.element_id, version, rel_kind, target) for rel_kind, target in element.relations]
    conn.executemany(
        'INSERT OR IGNORE INTO element_relations (namespace, element_id, version, rel_kind, target_id)'
        ' VALUES (?,?,?,?,?)',
        rows,
    )
    return rows


def _ingest(conn, batch, *, kind='import', own_transaction=True):
    """写入一个批次。默认自带事务：任何异常都 rollback，半批零写入。

    ``own_transaction=False`` 用于「多个命名空间一起提交」的恢复路径：此时事务
    由调用方托开，本函数只负责「全部成功或全部抛错」。
    """
    if own_transaction:
        conn.execute('BEGIN IMMEDIATE')
    try:
        existing = conn.execute(
            'SELECT id FROM import_batches WHERE namespace=? AND batch_hash=?',
            (batch.namespace, batch.batch_hash),
        ).fetchone()
        if existing is not None:
            if own_transaction:
                conn.rollback()
            result = ImportResult(
                namespace=batch.namespace, group_id=batch.group_id, adapter=batch.adapter,
                batch_id=int(existing[0]), batch_hash=batch.batch_hash, idempotent=True,
                elements=len(batch.elements), sources=len(batch.sources),
                unchanged_elements=len(batch.elements), unchanged_sources=len(batch.sources),
            )
            return result

        # 预检 A：未固定的来源必须在「同批 / 本命名空间 / 全局唯一」中可解析，否则整批拒绝。
        # 预检 B：已固定的来源版本必须已经存在（库里，或本批将要写入的版本），否则整批拒绝。
        batch_sources = {source.source_id: source for source in batch.sources}
        for element in batch.elements:
            if element.source_pins is None:
                for source_id in element.source_ids:
                    if source_id in batch_sources:
                        # 同批来源此时还没写入 source_versions（_insert_sources 在后面），
                        # 写入时再按内容哈希精确定位版本即可。
                        continue
                    resolve_source(conn, batch.namespace, source_id, batch_sources)
            else:
                if sorted(element.source_pins) != sorted(element.source_ids):
                    raise InvalidDocument('元素 %s 的来源固定点与 source_ids 不一致'
                                          % element.element_id)
                for source_id in element.source_ids:
                    source_namespace, source_version, _ = element.source_pins[source_id]
                    if not batch.verify_pins_against_db:
                        continue
                    if pin_exists(conn, source_namespace, source_id, source_version):
                        continue
                    pending = batch_sources.get(source_id)
                    if (pending is not None and source_namespace == batch.namespace
                            and pending.version == source_version):
                        continue
                    raise InvalidDocument('元素 %s 固定的来源 %s/%s v%s 不存在'
                                          % (element.element_id, source_namespace, source_id, source_version))
        # 预检：显式版本号在库内不得被不同内容占用。
        for element in batch.elements:
            if element.version is None:
                continue
            taken = conn.execute(
                'SELECT content_hash FROM element_versions WHERE namespace=? AND element_id=? AND version=?',
                (batch.namespace, element.element_id, element.version),
            ).fetchone()
            if taken is not None and taken[0] != element.content_hash:
                raise Conflict('元素 %s/%s 的版本 %d 已存在且内容不同'
                               % (batch.namespace, element.element_id, element.version))

        cursor = conn.execute(
            'INSERT INTO import_batches (namespace, group_id, batch_hash, kind, adapter, schema_kind, legacy_schema,'
            ' element_count, source_count, element_versions, source_versions, unchanged_elements,'
            ' unresolved_relations, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (batch.namespace, batch.group_id, batch.batch_hash, kind, batch.adapter, batch.schema_kind,
             1 if batch.legacy_schema else 0, len(batch.elements), len(batch.sources), 0, 0, 0, 0, _now()),
        )
        batch_id = int(cursor.lastrowid)
        result = ImportResult(
            namespace=batch.namespace, group_id=batch.group_id, adapter=batch.adapter,
            batch_id=batch_id, batch_hash=batch.batch_hash, idempotent=False,
            elements=len(batch.elements), sources=len(batch.sources),
        )
        _ensure_group(conn, batch, batch_id)
        _insert_sources(conn, batch, batch_id, result)

        written = []
        for element in batch.elements:
            existing_version = _element_hash_exists(conn, batch.namespace, element.element_id, element.content_hash)
            if existing_version is not None:
                result.unchanged_elements += 1
                if element.version is not None and element.version != existing_version:
                    raise Conflict('元素 %s/%s 的指定版本 %d 与同哈希已有版本 %d 不符'
                                   % (batch.namespace, element.element_id, element.version, existing_version))
                # 同哈希版本已存在：不重写、不重复计入关联统计。
                continue
            if element.version is None:
                version = _max_element_version(conn, batch.namespace, element.element_id) + 1
            else:
                version = element.version
            _insert_element_version(conn, batch, element, batch_id, version)
            _insert_element_sources(conn, batch, element, version, batch_sources)
            _insert_element_relations(conn, batch, element, version)
            result.element_versions += 1
            written.append((element, version))

        # 关联状态是「目标此刻是否存在」的投影，不写死；这里只为报告统计一次。
        for element, version in written:
            for rel_kind, target_id in element.relations:
                result.relations += 1
                target_namespace, status = _relation_status(conn, batch.namespace, target_id)
                if status == 'pending':
                    result.unresolved_relations.append({'element_id': element.element_id,
                                                        'rel_kind': rel_kind, 'target_id': target_id})
                elif status == 'ambiguous':
                    result.ambiguous_relations.append({'element_id': element.element_id,
                                                       'rel_kind': rel_kind, 'target_id': target_id})

        shared = []
        for element in batch.elements:
            others = conn.execute(
                'SELECT namespace FROM elements WHERE element_id=? AND namespace<>? ORDER BY namespace',
                (element.element_id, batch.namespace),
            ).fetchall()
            if others:
                shared.append({'element_id': element.element_id,
                               'other_namespaces': [row[0] for row in others]})
        result.shared_element_ids = shared

        conn.execute(
            'UPDATE import_batches SET element_versions=?, source_versions=?, unchanged_elements=?,'
            ' unresolved_relations=? WHERE id=?',
            (result.element_versions, result.source_versions, result.unchanged_elements,
             len(result.unresolved_relations) + len(result.ambiguous_relations), batch_id),
        )
        if own_transaction:
            conn.commit()
        return result
    except BaseException:
        if own_transaction:
            conn.rollback()
        raise


def import_document(db_path, document, *, namespace=None, adapter=None):
    """整批原子导入一份采集 JSON（dict 或已解析对象）。返回 ImportResult。"""
    batch = prepare_document(document, namespace=namespace, adapter=adapter)
    conn = open_writable(db_path)
    try:
        return _ingest(conn, batch, kind='import')
    finally:
        conn.close()


def import_file(db_path, path, *, namespace=None, adapter=None, encoding='utf-8'):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise LimitExceeded('%s 超过 %d 字节上限' % (path, MAX_DOCUMENT_BYTES))
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as exc:
        raise InvalidDocument('%s 不是合法的 %s 文本：%s' % (path, encoding, exc)) from exc
    return import_document(db_path, loads_json(text), namespace=namespace, adapter=adapter)


# --------------------------------------------------------------------------- 导出 / 还原
def export_document(db_path, *, namespaces=None):
    """导出全部组、来源版本与元素版本（稳定排序，便于逐字节比较）。"""
    conn = open_readonly(db_path)
    try:
        where, params = '', []
        if namespaces:
            marks = ','.join('?' * len(namespaces))
            where = ' WHERE namespace IN (%s)' % marks
            params = list(namespaces)
        groups = []
        for row in conn.execute(
            'SELECT namespace, group_id, schema_kind, adapter, legacy_schema, status, meta_json FROM groups'
            + where + ' ORDER BY namespace', params,
        ):
            groups.append({
                'namespace': row[0],
                'group_id': row[1],
                'schema_kind': row[2],
                'adapter': row[3],
                'legacy_schema': bool(row[4]),
                'status': row[5],
                'meta': json.loads(row[6]),
            })
        sources = []
        for row in conn.execute(
            'SELECT namespace, source_id, version, payload_json, payload_hash FROM source_versions'
            + where + ' ORDER BY namespace, source_id, version', params,
        ):
            sources.append({
                'namespace': row[0],
                'source_id': row[1],
                'version': row[2],
                'payload_hash': row[4],
                'payload': json.loads(row[3]),
            })
        elements = []
        for row in conn.execute(
            'SELECT namespace, element_id, version, content_hash, payload_json, schema_kind, adapter, legacy_schema,'
            ' name, review_status, detail_status, details_json, details_map_json, details_extra_json'
            ' FROM element_versions' + where + ' ORDER BY namespace, element_id, version', params,
        ):
            namespace, element_id, version = row[0], row[1], row[2]
            tags = [item[0] for item in conn.execute(
                'SELECT tag FROM element_tags WHERE namespace=? AND element_id=? AND version=? ORDER BY tag',
                (namespace, element_id, version),
            )]
            names = [{'kind': item[0], 'value': item[1]} for item in conn.execute(
                'SELECT kind, value FROM element_names WHERE namespace=? AND element_id=? AND version=?'
                ' ORDER BY kind DESC, rowid', (namespace, element_id, version),
            )]
            relations = []
            for item in conn.execute(
                'SELECT rel_kind, target_id FROM element_relations WHERE namespace=? AND element_id=? AND version=?'
                ' ORDER BY rel_kind, target_id', (namespace, element_id, version),
            ):
                target_namespace, status = _relation_status(conn, namespace, item[1])
                relations.append({'rel_kind': item[0], 'target_id': item[1],
                                  'target_namespace': target_namespace, 'status': status})
            sources_for_element = [
                {'source_id': item[0], 'source_namespace': item[1],
                 'source_version': item[2], 'status': item[3]}
                for item in conn.execute(
                    'SELECT source_id, source_namespace, source_version, status FROM element_sources'
                    ' WHERE namespace=? AND element_id=? AND version=? ORDER BY source_id',
                    (namespace, element_id, version),
                )
            ]
            elements.append({
                'namespace': namespace,
                'element_id': element_id,
                'version': version,
                'content_hash': row[3],
                'schema_kind': row[5],
                'adapter': row[6],
                'legacy_schema': bool(row[7]),
                'name': row[8],
                'review_status': row[9],
                'detail_status': row[10],
                'details': json.loads(row[11]),
                'details_map': json.loads(row[12]),
                'details_extra': json.loads(row[13]),
                'tags': tags,
                'names': names,
                'relations': relations,
                'source_refs': sources_for_element,
                'payload': json.loads(row[4]),
            })
        return {
            'format': EXPORT_FORMAT,
            'export_version': EXPORT_VERSION,
            'schema_version': SCHEMA_VERSION,
            'exported_at': _now(),
            'scope': {'namespaces': list(namespaces) if namespaces else 'all'},
            'counts': {
                'groups': len(groups),
                'source_versions': len(sources),
                'element_versions': len(elements),
            },
            'groups': groups,
            'sources': sources,
            'elements': elements,
        }
    finally:
        conn.close()


def restore_document(db_path, document):
    """把一个导出文件原样写回空库或已有库：保留原版本号、校验 content_hash。"""
    if not isinstance(document, dict):
        raise InvalidDocument('导出文件必须是 JSON 对象')
    if document.get('format') != EXPORT_FORMAT:
        raise InvalidDocument('不是百科导出文件（format=%r）' % document.get('format'))
    if document.get('export_version') != EXPORT_VERSION:
        raise InvalidDocument('导出格式版本不支持：%r' % document.get('export_version'))
    groups = document.get('groups')
    elements = document.get('elements')
    sources = document.get('sources') or []
    if not isinstance(groups, list) or not groups:
        raise InvalidDocument('导出文件没有 groups')
    if not isinstance(elements, list) or not elements:
        raise InvalidDocument('导出文件没有 elements')

    adapters = {}
    for group in groups:
        if not isinstance(group, dict):
            raise InvalidDocument('groups 里的每一项必须是对象')
        namespace = _check_id(group.get('namespace'), '导出 group 的 namespace')
        adapter = group.get('adapter')
        if adapter not in ADAPTERS:
            raise InvalidDocument('导出 group %s 的 adapter 非法：%r' % (namespace, adapter))
        adapters[namespace] = adapter

    by_namespace = {}
    for raw in elements:
        if not isinstance(raw, dict):
            raise InvalidDocument('elements 里的每一项必须是对象')
        namespace = _check_id(raw.get('namespace'), '导出元素的 namespace')
        if namespace not in adapters:
            raise InvalidDocument('导出元素 %r 的命名空间不在 groups 里' % raw.get('element_id'))
        by_namespace.setdefault(namespace, []).append(raw)

    conn = open_writable(db_path)
    try:
        existing = conn.execute(
            'SELECT id FROM import_batches WHERE namespace=? AND batch_hash=?',
            ('*restore*', payload_hash(document)),
        ).fetchone()
        if existing is not None:
            return ImportResult(namespace='*restore*', group_id='*restore*', adapter='*restore*',
                                batch_id=int(existing[0]), batch_hash=payload_hash(document),
                                idempotent=True, elements=len(elements), sources=len(sources))
        results = []
        # 整个导出文件是一个重建单元：所有命名空间共用一个事务，要么全写入要么零写入。
        conn.execute('BEGIN IMMEDIATE')
        # 预检：每个导出元素的 source_refs 必须存在、带合法 source_version，
        # 且指向本文档里真实存在的来源版本。导出即证据快照，缺 pin 就不是合法导出。
        document_sources = set()
        for raw in sources:
            if not isinstance(raw, dict):
                raise InvalidDocument('sources 里的每一项必须是对象')
            document_sources.add((raw.get('namespace'), raw.get('source_id'), raw.get('version')))
        pins_by_key = {}
        for group in sorted(groups, key=lambda item: item['namespace']):
            namespace = group['namespace']
            legacy = adapters[namespace] == ADAPTER_CATALOG
            for raw in by_namespace.get(namespace, []):
                if 'payload' not in raw:
                    raise InvalidDocument('导出元素 %s 缺少 payload' % raw.get('element_id'))
                refs = raw.get('source_refs')
                if not isinstance(refs, list):
                    raise InvalidDocument('导出元素 %s 缺少 source_refs（导出格式必须固定来源版本）'
                                          % raw.get('element_id'))
                pinned = _prepare_element(raw['payload'], legacy, adapters[namespace])
                pin_map = {}
                for pin in refs:
                    if not isinstance(pin, dict):
                        raise InvalidDocument('元素 %s 的 source_refs 项必须是对象' % pinned.element_id)
                    key = (pin.get('source_namespace'), pin.get('source_id'), pin.get('source_version'))
                    if not isinstance(key[2], int) or isinstance(key[2], bool) or key[2] < 1:
                        raise InvalidDocument('元素 %s 的 source_refs 缺少合法 source_version'
                                              % pinned.element_id)
                    if key not in document_sources:
                        raise InvalidDocument('元素 %s 固定的来源 %s/%s v%s 不在导出文件里'
                                              % (pinned.element_id, key[0], key[1], key[2]))
                    pin_map[key[1]] = (key[0], key[2], pin.get('status') or 'resolved')
                if sorted(pin_map) != sorted(pinned.source_ids):
                    raise InvalidDocument('元素 %s 的 source_refs 与 payload.source_ids 不一致'
                                          % pinned.element_id)
                version = raw.get('version')
                if not isinstance(version, int) or version < 1:
                    raise InvalidDocument('导出元素 %s 的 version 非法' % pinned.element_id)
                pins_by_key[(namespace, pinned.element_id, version)] = pin_map
        for group in sorted(groups, key=lambda item: item['namespace']):
            namespace = group['namespace']
            adapter = adapters[namespace]
            legacy = adapter == ADAPTER_CATALOG
            batch_sources = []
            for raw in sorted((item for item in sources if item.get('namespace') == namespace),
                              key=lambda item: (item.get('source_id'), item.get('version') or 0)):
                if not isinstance(raw, dict) or 'payload' not in raw:
                    raise InvalidDocument('导出来源缺少 payload')
                source = _prepare_source(raw['payload'])
                version = raw.get('version')
                if not isinstance(version, int) or version < 1:
                    raise InvalidDocument('导出来源 %s 的 version 非法' % source.source_id)
                source.version = version
                batch_sources.append(source)
            prepared = []
            for raw in sorted(by_namespace.get(namespace, []),
                              key=lambda item: (item.get('element_id'), item.get('version') or 0)):
                if 'payload' not in raw:
                    raise InvalidDocument('导出元素 %s 缺少 payload' % raw.get('element_id'))
                element = _prepare_element(raw['payload'], legacy, adapter)
                digest = raw.get('content_hash')
                if digest is not None and digest != element.content_hash:
                    raise Conflict('导出元素 %s 的 content_hash 与 payload 不符（文件被改过？）' % element.element_id)
                version = raw.get('version')
                if not isinstance(version, int) or version < 1:
                    raise InvalidDocument('导出元素 %s 的 version 非法' % element.element_id)
                element.version = version
                element.source_pins = pins_by_key[(namespace, element.element_id, version)]
                prepared.append(element)
            batch = PreparedBatch(
                namespace=namespace,
                group_id=group.get('group_id') or namespace,
                adapter=adapter,
                schema_kind=group.get('schema_kind') or ('element-catalog' if legacy else 'human'),
                legacy_schema=legacy,
                status=group.get('status'),
                meta=group.get('meta') or {},
                sources=batch_sources,
                elements=prepared,
                batch_hash=payload_hash({'restore': namespace, 'group': group}),
                verify_pins_against_db=False,
            )
            results.append(_ingest(conn, batch, kind='restore', own_transaction=False))
        total = ImportResult(namespace='*restore*', group_id='*restore*', adapter='restore',
                             batch_id=results[0].batch_id if results else 0,
                             batch_hash=payload_hash(document), idempotent=False)
        for item in results:
            total.elements += item.elements
            total.element_versions += item.element_versions
            total.unchanged_elements += item.unchanged_elements
            total.sources += item.sources
            total.source_versions += item.source_versions
            total.unchanged_sources += item.unchanged_sources
            total.relations += item.relations
            total.unresolved_relations.extend(item.unresolved_relations)
            total.ambiguous_relations.extend(item.ambiguous_relations)
        # 提交前最后一道间：每个 pin 必须在库里能找到对应来源版本（跨命名空间也算）。
        missing = conn.execute(
            'SELECT es.namespace, es.element_id, es.version, es.source_namespace, es.source_id, es.source_version'
            ' FROM element_sources es'
            ' LEFT JOIN source_versions sv'
            '   ON sv.namespace = es.source_namespace AND sv.source_id = es.source_id'
            '  AND sv.version = es.source_version'
            ' WHERE sv.version IS NULL'
        ).fetchall()
        if missing:
            head = missing[0]
            raise InvalidDocument('固定的来源版本不存在：元素 %s/%s v%s → %s/%s v%s（共 %d 处）'
                                  % (head[0], head[1], head[2], head[3], head[4], head[5], len(missing)))
        conn.execute(
            'INSERT INTO import_batches (namespace, group_id, batch_hash, kind, adapter, schema_kind, legacy_schema,'
            ' element_count, source_count, element_versions, source_versions, unchanged_elements,'
            ' unresolved_relations, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('*restore*', '*restore*', total.batch_hash, 'restore', 'restore', 'restore', 0,
             total.elements, total.sources, total.element_versions, total.source_versions,
             total.unchanged_elements, len(total.unresolved_relations) + len(total.ambiguous_relations), _now()),
        )
        conn.commit()
        return total
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def restore_file(db_path, path):
    raw = Path(path).read_bytes()
    return restore_document(db_path, loads_json(raw.decode('utf-8')))


# --------------------------------------------------------------------------- 只读查询
def _element_namespaces(conn, element_id):
    return [row[0] for row in conn.execute(
        'SELECT namespace FROM elements WHERE element_id=? ORDER BY namespace', (element_id,)
    )]


def _element_head(conn, namespace, element_id):
    return conn.execute(
        'SELECT namespace, element_id, group_id, current_version, name, review_status, detail_status'
        ' FROM elements WHERE namespace=? AND element_id=?', (namespace, element_id),
    ).fetchone()


def _element_version_row(conn, namespace, element_id, version):
    return conn.execute(
        'SELECT namespace, element_id, version, content_hash, payload_json, schema_kind, adapter, legacy_schema,'
        ' name, summary, review_status, detail_status, details_json, details_map_json, details_extra_json'
        ' FROM element_versions WHERE namespace=? AND element_id=? AND version=?',
        (namespace, element_id, version),
    ).fetchone()


def _tags_of(conn, namespace, element_id, version):
    return [row[0] for row in conn.execute(
        'SELECT tag FROM element_tags WHERE namespace=? AND element_id=? AND version=? ORDER BY tag',
        (namespace, element_id, version),
    )]


def _names_of(conn, namespace, element_id, version):
    name = None
    aliases = []
    for kind, value in conn.execute(
        'SELECT kind, value FROM element_names WHERE namespace=? AND element_id=? AND version=?'
        ' ORDER BY kind DESC, rowid', (namespace, element_id, version),
    ):
        if kind == 'name':
            name = value
        else:
            aliases.append(value)
    return name, aliases


def _sources_of(conn, namespace, element_id, version, include_payload=True):
    """该元素版本引用的来源，**按写入当时固定的版本**读取。

    绝不去读 ``sources.current_version``：来源后来升级到 v2，元素 v1 仍只能看到
    v1 的 title/url/access/payload。这就是「证据不变」的实现点。
    """
    rows = []
    for source_id, source_namespace, source_version, status in conn.execute(
        'SELECT source_id, source_namespace, source_version, status FROM element_sources'
        ' WHERE namespace=? AND element_id=? AND version=? ORDER BY source_id',
        (namespace, element_id, version),
    ):
        pinned = conn.execute(
            'SELECT payload_json, payload_hash FROM source_versions'
            ' WHERE namespace=? AND source_id=? AND version=?',
            (source_namespace, source_id, source_version),
        ).fetchone()
        current = conn.execute(
            'SELECT current_version FROM sources WHERE namespace=? AND source_id=?',
            (source_namespace, source_id),
        ).fetchone()
        payload = None if pinned is None else json.loads(pinned[0])
        row = {
            'source_id': source_id,
            'source_namespace': source_namespace,
            'source_version': source_version,
            'status': status,
            'title': None if payload is None else payload.get('title'),
            'url': None if payload is None else payload.get('url'),
            'access': None if payload is None else payload.get('access'),
            'payload_hash': None if pinned is None else pinned[1],
            'is_current_source_version': bool(current is not None and int(current[0]) == source_version),
        }
        if include_payload:
            row['payload'] = payload
        rows.append(row)
    return rows


def _relations_of(conn, namespace, element_id, version):
    rows = []
    for rel_kind, target_id in conn.execute(
        'SELECT rel_kind, target_id FROM element_relations'
        ' WHERE namespace=? AND element_id=? AND version=? ORDER BY rel_kind, target_id',
        (namespace, element_id, version),
    ):
        target_namespace, status = _relation_status(conn, namespace, target_id)
        rows.append({'rel_kind': rel_kind, 'target_id': target_id,
                     'target_namespace': target_namespace, 'status': status})
    return rows


def get(db_path, element_id, *, namespace=None, version=None, include_payload=True):
    """单项详情，可指定历史版本。仅词法读取，不写库。"""
    _check_id(element_id, 'element id')
    conn = open_readonly(db_path)
    try:
        namespaces = _element_namespaces(conn, element_id)
        if not namespaces:
            raise NotFound('条目不存在：%s' % element_id)
        if namespace is None:
            if len(namespaces) > 1:
                raise Ambiguous('条目 %s 在多个命名空间存在（%s），请显式指定 namespace'
                                % (element_id, ', '.join(namespaces)))
            namespace = namespaces[0]
        elif namespace not in namespaces:
            raise NotFound('条目 %s 不在命名空间 %s（现有：%s）'
                           % (element_id, namespace, ', '.join(namespaces)))
        head = _element_head(conn, namespace, element_id)
        if head is None:
            raise NotFound('条目不存在：%s/%s' % (namespace, element_id))
        target_version = head[3] if version is None else int(version)
        row = _element_version_row(conn, namespace, element_id, target_version)
        if row is None:
            raise NotFound('条目 %s/%s 没有版本 %s（当前版本 %d）'
                           % (namespace, element_id, target_version, head[3]))
        name, aliases = _names_of(conn, namespace, element_id, target_version)
        payload = json.loads(row[4])
        pinned_sources = _sources_of(conn, namespace, element_id, target_version,
                                    include_payload=include_payload)
        result = {
            'namespace': row[0],
            'element_id': row[1],
            'group_id': head[2],
            'version': row[2],
            'current_version': head[3],
            'is_current': row[2] == head[3],
            'content_hash': row[3],
            'schema_kind': row[5],
            'adapter': row[6],
            'legacy_schema': bool(row[7]),
            'name': name or row[8],
            'aliases': aliases,
            'summary': row[9],
            'review_status': row[10],
            'detail_status': row[11],
            'details': json.loads(row[12]),
            'details_map': json.loads(row[13]),
            'details_extra': json.loads(row[14]),
            'tags': _tags_of(conn, namespace, element_id, target_version),
            'source_ids': [item['source_id'] for item in pinned_sources],
            'sources': pinned_sources,
            'relations': _relations_of(conn, namespace, element_id, target_version),
        }
        if include_payload:
            result['payload'] = payload
        return result
    finally:
        conn.close()


def versions(db_path, element_id, *, namespace=None):
    conn = open_readonly(db_path)
    try:
        namespaces = _element_namespaces(conn, element_id)
        if not namespaces:
            raise NotFound('条目不存在：%s' % element_id)
        if namespace is None and len(namespaces) > 1:
            raise Ambiguous('条目 %s 在多个命名空间存在（%s），请显式指定 namespace'
                            % (element_id, ', '.join(namespaces)))
        namespace = namespace or namespaces[0]
        head = _element_head(conn, namespace, element_id)
        if head is None:
            raise NotFound('条目不存在：%s/%s' % (namespace, element_id))
        rows = []
        for row in conn.execute(
            'SELECT version, content_hash, name, review_status, detail_status, batch_id, created_at'
            ' FROM element_versions WHERE namespace=? AND element_id=? ORDER BY version',
            (namespace, element_id),
        ):
            rows.append({'version': row[0], 'content_hash': row[1], 'name': row[2],
                         'review_status': row[3], 'detail_status': row[4],
                         'batch_id': row[5], 'created_at': row[6], 'is_current': row[0] == head[3]})
        return {'namespace': namespace, 'element_id': element_id, 'current_version': head[3], 'versions': rows}
    finally:
        conn.close()


def search(db_path, *, text=None, tags_any=(), tags_all=(), namespace=None, group_id=None,
           review_status=None, detail_status=None, limit=DEFAULT_PAGE_SIZE, offset=0,
           include_payload=False):
    """检索：中文名/别名子串 + 多标签 AND/OR + 分页。总数单独返回，便于判断边界。"""
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise EncyclopediaError('limit 必须是整数')
    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise EncyclopediaError('limit 必须在 1..%d 之间（得到 %r）' % (MAX_PAGE_SIZE, limit))
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise EncyclopediaError('offset 必须是整数')
    if offset < 0:
        raise EncyclopediaError('offset 不能为负（得到 %r）' % offset)
    tags_any = list(tags_any or ())
    tags_all = list(tags_all or ())
    for tag in tags_any + tags_all:
        _check_tag(tag)
    if namespace is not None:
        _check_id(namespace, 'namespace')

    clauses = []
    params = []
    if namespace is not None:
        clauses.append('e.namespace=?')
        params.append(namespace)
    if group_id is not None:
        clauses.append('e.group_id=?')
        params.append(group_id)
    if review_status is not None:
        clauses.append('e.review_status=?')
        params.append(review_status)
    if detail_status is not None:
        clauses.append('e.detail_status=?')
        params.append(detail_status)
    if text:
        _check_text(text, '检索文本', MAX_NAME_CHARS)
        needle = '%' + _like_escape(norm_text(text)) + '%'
        clauses.append(
            'EXISTS (SELECT 1 FROM element_names n WHERE n.namespace=e.namespace'
            ' AND n.element_id=e.element_id AND n.version=e.current_version'
            " AND n.norm LIKE ? ESCAPE '\\')"
        )
        params.append(needle)
    if tags_any:
        marks = ','.join('?' * len(tags_any))
        clauses.append(
            'EXISTS (SELECT 1 FROM element_tags t WHERE t.namespace=e.namespace'
            ' AND t.element_id=e.element_id AND t.version=e.current_version AND t.tag IN (%s))' % marks
        )
        params.extend(tags_any)
    for tag in tags_all:
        clauses.append(
            'EXISTS (SELECT 1 FROM element_tags t WHERE t.namespace=e.namespace'
            ' AND t.element_id=e.element_id AND t.version=e.current_version AND t.tag=?)'
        )
        params.append(tag)

    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    conn = open_readonly(db_path)
    try:
        total = conn.execute(
            'SELECT COUNT(*) FROM elements e' + where, params
        ).fetchone()[0]
        page_params = list(params) + [limit, offset]
        rows = conn.execute(
            'SELECT e.namespace, e.element_id, e.group_id, e.current_version, e.name, e.review_status,'
            ' e.detail_status, v.summary FROM elements e'
            ' JOIN element_versions v ON v.namespace=e.namespace AND v.element_id=e.element_id'
            ' AND v.version=e.current_version' + where + ' ORDER BY e.namespace, e.element_id LIMIT ? OFFSET ?',
            page_params,
        ).fetchall()
        items = []
        for row in rows:
            namespace_value, element_id, _, version = row[0], row[1], row[2], row[3]
            item = {
                'namespace': namespace_value,
                'element_id': element_id,
                'group_id': row[2],
                'version': version,
                'name': row[4],
                'review_status': row[5],
                'detail_status': row[6],
                'summary': row[7],
                'aliases': _names_of(conn, namespace_value, element_id, version)[1],
                'tags': _tags_of(conn, namespace_value, element_id, version),
            }
            if include_payload:
                payload_row = _element_version_row(conn, namespace_value, element_id, version)
                item['payload'] = json.loads(payload_row[4])
            items.append(item)
        return {
            'total': total,
            'limit': limit,
            'offset': offset,
            'returned': len(items),
            'has_more': offset + len(items) < total,
            'items': items,
        }
    finally:
        conn.close()


def list_tags(db_path, *, namespace=None, limit=MAX_PAGE_SIZE, offset=0):
    clauses, params = [], []
    if namespace is not None:
        _check_id(namespace, 'namespace')
        clauses.append('t.namespace=?')
        params.append(namespace)
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    conn = open_readonly(db_path)
    try:
        rows = conn.execute(
            'SELECT t.tag, COUNT(*) FROM element_tags t' + where + ' GROUP BY t.tag'
            ' ORDER BY COUNT(*) DESC, t.tag LIMIT ? OFFSET ?', params + [limit, offset],
        ).fetchall()
        total = conn.execute('SELECT COUNT(DISTINCT t.tag) FROM element_tags t' + where, params).fetchone()[0]
        return {'total': total, 'limit': limit, 'offset': offset,
                'tags': [{'tag': row[0], 'count': row[1]} for row in rows]}
    finally:
        conn.close()


def stats(db_path, *, namespace=None):
    conn = open_readonly(db_path)
    try:
        namespaces = [row[0] for row in conn.execute('SELECT namespace FROM groups ORDER BY namespace')]
        scope = [namespace] if namespace else namespaces
        if namespace and namespace not in namespaces:
            raise NotFound('命名空间不存在：%s' % namespace)
        mark = ','.join('?' * len(scope)) if scope else "''"
        groups = []
        for name in scope:
            row = conn.execute(
                'SELECT group_id, schema_kind, adapter, legacy_schema, status FROM groups WHERE namespace=?',
                (name,),
            ).fetchone()
            elements = conn.execute('SELECT COUNT(*) FROM elements WHERE namespace=?', (name,)).fetchone()[0]
            versions = conn.execute('SELECT COUNT(*) FROM element_versions WHERE namespace=?', (name,)).fetchone()[0]
            sources = conn.execute('SELECT COUNT(*) FROM sources WHERE namespace=?', (name,)).fetchone()[0]
            source_versions = conn.execute('SELECT COUNT(*) FROM source_versions WHERE namespace=?', (name,)).fetchone()[0]
            tags = conn.execute('SELECT COUNT(DISTINCT tag) FROM element_tags WHERE namespace=?', (name,)).fetchone()[0]
            batches = conn.execute('SELECT COUNT(*) FROM import_batches WHERE namespace=?', (name,)).fetchone()[0]
            unresolved = 0
            for element_id, version in conn.execute(
                'SELECT element_id, version FROM element_versions WHERE namespace=?', (name,)
            ).fetchall():
                for relation in _relations_of(conn, name, element_id, version):
                    if relation['status'] != 'resolved':
                        unresolved += 1
            review = {row[0]: row[1] for row in conn.execute(
                'SELECT review_status, COUNT(*) FROM elements WHERE namespace=? GROUP BY review_status', (name,))}
            detail = {row[0]: row[1] for row in conn.execute(
                'SELECT detail_status, COUNT(*) FROM elements WHERE namespace=? GROUP BY detail_status', (name,))}
            groups.append({
                'namespace': name,
                'group_id': row[0],
                'schema_kind': row[1],
                'adapter': row[2],
                'legacy_schema': bool(row[3]),
                'status': row[4],
                'elements': elements,
                'element_versions': versions,
                'sources': sources,
                'source_versions': source_versions,
                'tags': tags,
                'batches': batches,
                'unresolved_relations': unresolved,
                'review_status': review,
                'detail_status': detail,
            })
        totals = {
            'groups': len(groups),
            'elements': sum(item['elements'] for item in groups),
            'element_versions': sum(item['element_versions'] for item in groups),
            'sources': sum(item['sources'] for item in groups),
            'source_versions': sum(item['source_versions'] for item in groups),
            'unresolved_relations': sum(item['unresolved_relations'] for item in groups),
        }
        return {'schema_version': SCHEMA_VERSION, 'totals': totals, 'groups': groups}
    finally:
        conn.close()
