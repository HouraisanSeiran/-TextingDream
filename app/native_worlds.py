# -*- coding: utf-8 -*-
"""原生宿主（civ-atlas）只读数据桥：列出/查/取作者原件字节。

这不是一个新的 map codec，也不重新排列任何 World/Civ/raster 数组：

* 容器格式、数据块解析、单元格语义全部属于 `civ_atlas_snapshot`（上游口径）。
* 这里只做三件事：**筛出原生快照**、**核对来源**、**把原件字节原样交出去**。
* 宿主自己用上游 `readPart` 解外壳，本模块不提供第二种 shape。

三条硬边界：

1. **只认 CASNAP01**：只有 ``format == civ_atlas_snapshot.FORMAT`` 的记录会出现在列表里；
   高度图 PNG 导入（`map_import`）不属于这个数据桥。
2. **来源必须自己对得上**：读字节之前重算磁盘文件 SHA-256，与记录不符就拒，且不返回
   任何字节。
3. **路径不接受注入**：文件名只取自记录自身的 ``file`` 字段（服务端生成的内容哈希名），
   不接 URL / query / path；解析后还必须落在 ``store.parent/map_imports`` 之内。

权限不在本模块里判断：调用方（``app/web.py``）用作者 token 保护这些 route，并且
**不存在**一个客户端参数能把玩家路由升级成读原件。玩家仍走既有的受限
``/api/sessions/{id}/play-map`` JSON/PNG。
"""
import hashlib
from pathlib import Path

from . import civ_atlas_snapshot
from .map_import import MapImportError, import_dir

#: 这个桥只处理这一种记录（其余导入格式不在这里露面）。
NATIVE_FORMAT = civ_atlas_snapshot.FORMAT

#: 原件字节的 Content-Type：故意不是 image/* —— 它是容器文件，不是可直接渲染的图。
SNAPSHOT_MEDIA_TYPE = 'application/octet-stream'


def _is_native(record):
    return isinstance(record, dict) and record.get('format') == NATIVE_FORMAT


def _identity(record):
    source = record.get('source') or {}
    return {
        'import_id': record.get('id'),
        'sha256': record.get('sha256'),
        'bytes': record.get('bytes'),
        'file': record.get('file'),
        'world_id': source.get('world_id'),
        'world_app': source.get('world_app'),
        'snapshot_format': source.get('snapshot_format'),
        'generator_version': source.get('generator_version'),
        'exported_at': source.get('exported_at'),
        'extractor': source.get('extractor'),
        'spec_commit': source.get('spec_commit'),
        'license': source.get('license'),
    }


def _parts(record):
    """每个数据块的清单字段（服务端算的 sum 也在内）；不含字节本身。"""
    rows = []
    for part in record.get('parts') or []:
        if not isinstance(part, dict):
            continue
        rows.append({key: part.get(key) for key in
                     ('name', 'bytes', 'zip', 'length', 'sum', 'sum_verified_by')})
    return rows


def listing(store):
    """所有原生快照的安全 metadata（不含字节、不含任何作者私密内容）。

    没有注册任何原生快照时返回 ``[]`` —— 空世界也能正常调用。
    列表里的 ``sha256`` 是**短值**（前 16），仅用于显示；完整 64 位哈希在
    :func:`detail` 的 ``identity.sha256``。
    """
    rows = []
    for record in store.all('map_import'):
        if not _is_native(record):
            continue
        source = record.get('source') or {}
        rows.append({
            'import_id': record.get('id'),
            'created': record.get('created'),
            'sha256': str(record.get('sha256') or '')[:16],
            'bytes': record.get('bytes'),
            'world_id': source.get('world_id'),
            'world_app': source.get('world_app'),
            'snapshot_format': source.get('snapshot_format'),
            'generator_version': source.get('generator_version'),
            'exported_at': source.get('exported_at'),
            'parts': _parts(record),
            'stats': dict(record.get('stats') or {}),
        })
    rows.sort(key=lambda row: (row.get('created') or '', row.get('import_id') or ''))
    return rows


def link_of(story):
    """这个故事版本声明的世界基础来源，没有就 ``None``。

    只读已有的 ``mechanics.map`` 声明（与 ``play_map.parse_link`` 同一字段）：
    没有声明就不猜、不绑当前包。读失败也当作没有关联。
    """
    try:
        from . import play_map
        return play_map.parse_link(story)
    except ValueError:
        return None


def detail(store, runtime, import_id):
    """一个原生快照的完整**非字节**信息；未知 id / 非原生格式都明确拒绝。

    ``story_revision`` **只在当前故事版本确实把这个快照当作世界基础时**才给：
    判定看 ``mechanics.map.import_id`` 是否等于本条记录的 id，并且（声明了的话）
    ``source_sha256`` 与记录的哈希一致。否则一律 ``null`` —— 不能把一个无关的
    当前故事声称成来自这个原件。
    """
    record = _record(store, import_id)
    story_revision = story_id = None
    if runtime is not None and runtime.has_world():
        package = runtime.package()
        link = link_of(package['story'])
        if (link is not None and link.get('import_id') == record.get('id')
                and _pinned(record)):
            story_revision = package['id']
            story_id = package['story'].get('id')
    return {
        'identity': _identity(record),
        'story_revision': story_revision,
        'story_id': story_id,
        'parts': _parts(record),
        'available': _present(record, store),
    }


def _pinned(record):
    """复用 ``play_map._record_pinned``：id 的 hash 前缀必须与内容 sha256 自洽。

    这是既有的来源固定判定，不新增 schema、也不新算一套哈希规则。
    """
    from . import play_map
    return play_map._record_pinned(record)


def _present(record, store):
    """原件现在是否真的在：只做存在检查，不重解整图。"""
    root = Path(store.path).resolve().parent
    name = record.get('file')
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        return False
    return (import_dir(root) / name).is_file()


def snapshot_bytes(store, storage_root, import_id):
    """原样返回磁盘上那份 ``.civsnap`` 字节；任何不符都在返回前拒。

    三步，顺序不能换：

    1. 记录必须是原生快照（格式不符就不属于这个桥）；
    2. 文件名只取记录自己的 ``file``，并强制解析到 ``<storage_root>/map_imports``；
    3. 重算 SHA-256 与记录比对 —— 不符即拒，且**不**返回字节。
    """
    record = _record(store, import_id)
    directory = import_dir(Path(storage_root).resolve()).resolve()
    name = record.get('file')
    if not isinstance(name, str) or not name or '/' in name or '\\' in name or name.startswith('.'):
        raise MapImportError('导入记录的文件名不合法，拒绝读取')
    target = (directory / name).resolve()
    # 不接任何客户端路径：即使记录被手工改过，也只能落在 map_imports 里。
    if target.parent != directory:
        raise MapImportError('导入记录的文件路径越界，拒绝读取')
    if not target.exists():
        raise MapImportError('原件文件已不在（%s），请重新导出' % name)
    data = target.read_bytes()
    expected = record.get('sha256')
    if hashlib.sha256(data).hexdigest() != expected:
        raise MapImportError('原件校验失败：内容与记录的哈希不符，已拒绝返回')
    return data, record


def _record(store, import_id):
    """取一条原生快照记录；格式不符或不存在都抬可读错误。"""
    import re
    if not re.fullmatch(r'(mi|sn)_[0-9a-f]{6,32}', str(import_id or '')):
        raise MapImportError('导入编号格式不对')
    record = store.get('map_import', import_id)
    if not record:
        raise MapImportError('找不到这个地图导入')
    if not _is_native(record):
        raise MapImportError('这个导入不是原生快照（CASNAP01），不属于原生宿主数据桥')
    return record
