"""Read-only parser for a civ-atlas ``Snapshot`` that the author exported themselves.

The world data lives in the browser's IndexedDB (``civ-atlas:results``); upstream has no
"download the snapshot" button. ``tools/civ_atlas_export.js`` is our own read-only
extractor: the author runs it in the civ-atlas page and gets one ``*.civsnap`` file. This
module reads that file.

Two layers, both purely ours:

1. ``CASNAP01`` container (defined by ``tools/civ_atlas_export.js``): magic + uint32LE
   manifest length + JSON manifest + padding to 8 + the part bytes, unchanged.
2. Upstream's own part encoding ``CIVSNAP1`` (``src/gen/snapshot.ts:153-232``): magic +
   uint32LE structure length + UTF-8 JSON structure + padding to 8 + raw array bytes, each
   array padded to 8 and referenced from the structure as
   ``{"$$":"a","t":"F32","o":offset,"n":count}``. Other tags: ``o`` object, ``u``
   undefined, ``n`` NaN/±Inf/-0, ``r`` back-reference, ``m`` Map, ``s`` Set.

Untrusted input is assumed throughout: every length, offset and count is checked against
its own budget, JSON depth and node count are capped, typed-array spans must be inside the
part and 8-aligned, ``o``/``n`` must be non-negative integers (never bools), back-references
must point backwards, and unknown tags are refused. ``$$`` objects carry data only --- they
are never evaluated as anything executable.

Domain checks happen after decoding, on the arrays actually used: ``water`` must be 0/1/2,
``biome`` must be a known code, ``elevation``/``temperature``/``precipitation`` must be
finite, and every per-cell array must have exactly ``mesh.n`` entries. Unknown
``format``/``generator`` combos are refused rather than guessed at.

What the per-cell data is (read from ``src/gen/world.ts``): ``elevation`` metres,
``water`` 0 land / 1 ocean / 2 lake, ``temperature`` °C annual, ``precipitation`` mm/year,
``biome`` an index into ``src/gen/biomes.ts`` (0..15). Region-level "物产" exists only in
the *civ* part as a 0-3 reserve **tier per region** (``civ/types.ts`` ``Development``) ---
not an amount, not a stock, not per cell --- so it is reported as blocked, not imported.
"""
import hashlib
import json
import math
import re
import struct
import zlib

from .map_import import MapImportError, import_dir

# --------------------------------------------------------------------- contract
FORMAT = 'civ_atlas_snapshot_v1'
CONTAINER_MAGIC = b'CASNAP01'
CONTAINER_SCHEMA = 1
PART_MAGIC = b'CIVSNAP1'
SPEC_COMMIT = '0939c5f1622a5e45cfc16f645ea3845993ab3985'

# ---------------------------------------------------------------- hard bounds
MAX_CONTAINER_BYTES = 96 * 1024 * 1024
MAX_PARTS = 8
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_NODES = 3_000_000
MAX_CELLS = 400_000
MAX_ARRAY_ELEMENTS = 8 * MAX_CELLS
MAX_PART_DECODED = 128 * 1024 * 1024
#: upstream ``Biome`` enum, src/gen/biomes.ts:5-22 (0 ocean … 15 wetland)
BIOME_NAMES = ('海洋', '湖泊', '海冰', '冰原', '苔原', '针叶林', '寒漠', '温带荒漠', '草原',
               '温带森林', '温带雨林', '热带荒漠', '稀树草原', '热带季雨林', '热带雨林', '湿地')
WATER_NAMES = {0: '陆地', 1: '海洋', 2: '湖泊'}
#: Present in the world but not importable as a town resource (see module docstring).
BLOCKED_FIELDS = ('resources', 'faction', 'settlement')
#: Why the ``civ`` part's resources cannot become town resources, in the authors' words.
#: Upstream ``src/gen/civ/development.ts:5``: each prefecture gets one 0–3 tier per
#: commodity (none / little / medium / plenty) worked out from terrain, biome, climate and
#: plates — a *standing reserve* that attrition, discovery and technology then whittle
#: down over centuries. It is not annual output, not a surveyed deposit, and not a stock
#: the author may draw down; and it belongs to a whole prefecture, not to a 3-px window.
BLOCKED_REASON = {
    'resources': ('上游「物产」是州级 0–3 档储量（无/少/中/多），会随发现、技术与采空变化，'
                  '既不是年产量也不是库存，也不是逐地块勘探结果；本工程不把它当矿藏候选'),
    'faction': '上游势力属于推演出的历史，本工程不建第二套势力权威',
    'settlement': '上游城镇由推演产生，其人口与年份不能当本工程的城镇普查',
}

_ITEMSIZE = {'F32': 4, 'F64': 8, 'I8': 1, 'U8': 1, 'U8C': 1, 'I16': 2, 'U16': 2,
             'I32': 4, 'U32': 4}
_STRUCT = {'F32': 'f', 'F64': 'd', 'I8': 'b', 'U8': 'B', 'U8C': 'B', 'I16': 'h', 'U16': 'H',
           'I32': 'i', 'U32': 'I'}
_TAGS = {'a', 'o', 'u', 'n', 'r', 'm', 's'}
#: The exporter's fixed-width offset field: exactly 12 decimal digits, nothing else.
_OFFSET_TEXT = re.compile(r'[0-9]{12}')
_LENGTH_TEXT = re.compile(r'[0-9]{1,12}')


def _pad8(value):
    return (value + 7) & ~7


# ================================================================== container
def _part_offset(part, name, body_start, data_len):
    """Read one part's ``offset``/``length`` strictly.

    Two encodings are accepted, and nothing else:

    * the current exporter writes ``offset`` as a **fixed-width 12-digit decimal string**
    (that is what keeps the manifest's byte length independent of the numbers, see
    ``tools/civ_atlas_export.js``); a string must be exactly 12 digits, so the loose
    ``int('123junk')`` reading is refused;
    * older exports wrote a plain JSON integer.

    Booleans and negative numbers are refused in both cases, as are offsets before the
    payload area, misaligned offsets and spans past the end of the file.
    """
    offset, length = part.get('offset'), part.get('length')

    if isinstance(offset, str):
        if not _OFFSET_TEXT.fullmatch(offset):
            raise MapImportError('数据块 %s 的 offset 不是 12 位十进制串：%r'
                                 % (name, offset[:24]))
        offset = int(offset, 10)
    if isinstance(length, str):
        if not _LENGTH_TEXT.fullmatch(length):
            raise MapImportError('数据块 %s 的 length 不是十进制整数：%r'
                                 % (name, length[:24]))
        length = int(length, 10)
    for value, label in ((offset, 'offset'), (length, 'length')):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MapImportError('数据块 %s 的 %s 不是非负整数' % (name, label))
    if offset < body_start or offset + length > data_len:
        raise MapImportError('数据块 %s 越界（offset %d, length %d, 文件 %d 字节）'
                             % (name, offset, length, data_len))
    if offset % 8:
        raise MapImportError('数据块 %s 没有按 8 字节对齐（offset %d）' % (name, offset))
    return offset, length


def parse_container(data):
    """Validate our own CASNAP01 wrapper and return ``(manifest, parts)``."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise MapImportError('导入内容必须是文件字节')
    data = bytes(data)
    if len(data) > MAX_CONTAINER_BYTES:
        raise MapImportError('原件文件超过 %d MB 上限' % (MAX_CONTAINER_BYTES // (1024 * 1024)))
    if len(data) < len(CONTAINER_MAGIC) + 4:
        raise MapImportError('文件太短，不是本工具导出的原件')
    if data[:len(CONTAINER_MAGIC)] != CONTAINER_MAGIC:
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            raise MapImportError('这是 PNG（高度图），请用高度图入口导入')
        raise MapImportError('不是 tools/civ_atlas_export.js 导出的 .civsnap 文件')
    head_len = struct.unpack('<I', data[8:12])[0]
    if head_len == 0 or head_len > MAX_JSON_BYTES:
        raise MapImportError('原件清单长度不合理：%d' % head_len)
    if 12 + head_len > len(data):
        raise MapImportError('原件清单被截断')
    try:
        manifest = json.loads(data[12:12 + head_len].decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MapImportError('原件清单不是合法 JSON：%s' % error)
    if not isinstance(manifest, dict):
        raise MapImportError('原件清单不是对象')
    if manifest.get('container') != CONTAINER_MAGIC.decode('ascii'):
        raise MapImportError('原件清单的容器标记不对')
    if manifest.get('schema') != CONTAINER_SCHEMA:
        raise MapImportError('原件容器版本 %r 不认识（本工程只认 %d）'
                             % (manifest.get('schema'), CONTAINER_SCHEMA))
    parts = manifest.get('parts')
    if not isinstance(parts, list) or not parts:
        raise MapImportError('原件清单里没有数据块')
    if len(parts) > MAX_PARTS:
        raise MapImportError('原件数据块过多：%d' % len(parts))
    body_start = _pad8(12 + head_len)
    seen_names = set()
    spans = []
    for part in parts:
        if not isinstance(part, dict):
            raise MapImportError('原件清单的数据块不是对象')
        name = part.get('name')
        if not isinstance(name, str) or not name:
            raise MapImportError('原件数据块缺名字')
        if name in seen_names:
            raise MapImportError('原件数据块重名：%s' % name)
        seen_names.add(name)
        offset, length = _part_offset(part, name, body_start, len(data))
        spans.append((offset, offset + length))
        part['_bytes'] = data[offset:offset + length]
    spans.sort()
    for (a_start, a_end), (b_start, _) in zip(spans, spans[1:]):
        if b_start < a_end:
            raise MapImportError('原件数据块互相重叠')
    return manifest, parts


def _inflate(blob, limit=MAX_PART_DECODED):
    """Bounded gzip: stop at the budget, never decompress whole then measure."""
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = inflater.decompress(blob, limit + 1)
    except zlib.error as error:
        raise MapImportError('数据块解压失败：%s' % error)
    if len(out) > limit or inflater.unconsumed_tail:
        raise MapImportError('数据块解压后超过 %d MB 上限' % (limit // (1024 * 1024)))
    if not inflater.eof:
        raise MapImportError('数据块 gzip 流不完整')
    return out


# ======================================================================= part
class _Budget:
    __slots__ = ('nodes',)

    def __init__(self):
        self.nodes = 0

    def spend(self):
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise MapImportError('原件结构节点数超过上限')


def _decode_structure(node, payload, depth=0, budget=None, refs=None):
    """Turn one ``CIVSNAP1`` structure node into ordinary Python values.

    Typed arrays become ``array`` objects holding the raw numbers; nothing is ever
    interpreted as code.
    """
    if budget is None:
        budget = _Budget()
        refs = []
    if depth > MAX_JSON_DEPTH:
        raise MapImportError('原件结构嵌套超过 %d 层' % MAX_JSON_DEPTH)
    budget.spend()
    if node is None or isinstance(node, (str, bool, int, float)):
        return node
    if isinstance(node, list):
        out = []
        refs.append(out)
        for item in node:
            out.append(_decode_structure(item, payload, depth + 1, budget, refs))
        return out
    if not isinstance(node, dict):
        raise MapImportError('原件结构里出现不认识的类型')
    tag = node.get('$$')
    if tag is None:
        out = {}
        refs.append(out)
        for key, item in node.items():
            if not isinstance(key, str):
                raise MapImportError('原件结构的键不是字符串')
            out[key] = _decode_structure(item, payload, depth + 1, budget, refs)
        return out
    if tag not in _TAGS:
        raise MapImportError('原件结构里的标记 %r 不认识（不当作代码执行）' % (tag,))
    if tag == 'u':
        return None
    if tag == 'n':
        label = node.get('v')
        return {'NaN': float('nan'), 'Inf': float('inf'), '-Inf': float('-inf'),
                '-0': -0.0}.get(label, float('nan'))
    if tag == 'r':
        index = node.get('i')
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise MapImportError('原件引用的编号不是非负整数')
        if index >= len(refs):
            raise MapImportError('原件引用指向尚未出现的对象（编号 %d）' % index)
        return refs[index]
    if tag == 'o':
        inner = node.get('v')
        if not isinstance(inner, dict):
            raise MapImportError('原件 o 标记的内容不是对象')
        out = {}
        refs.append(out)
        for key, item in inner.items():
            out[key] = _decode_structure(item, payload, depth + 1, budget, refs)
        return out
    if tag == 'm':
        pairs = node.get('v')
        if not isinstance(pairs, list):
            raise MapImportError('原件 m 标记的内容不是数组')
        out = {}
        refs.append(out)
        for pair in pairs:
            if not isinstance(pair, list) or len(pair) != 2:
                raise MapImportError('原件 Map 的项不是键值对')
            key = _decode_structure(pair[0], payload, depth + 1, budget, refs)
            out[str(key)] = _decode_structure(pair[1], payload, depth + 1, budget, refs)
        return out
    if tag == 's':
        items = node.get('v')
        if not isinstance(items, list):
            raise MapImportError('原件 s 标记的内容不是数组')
        out = []
        refs.append(out)
        for item in items:
            out.append(_decode_structure(item, payload, depth + 1, budget, refs))
        return out
    # tag == 'a': a typed array living in the payload
    kind = node.get('t')
    offset, count = node.get('o'), node.get('n')
    if kind not in _ITEMSIZE:
        raise MapImportError('原件数组种类 %r 不认识' % (kind,))
    for value, label in ((offset, 'o'), (count, 'n')):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MapImportError('原件数组的 %s 必须是非负整数' % label)
    if count > MAX_ARRAY_ELEMENTS:
        raise MapImportError('原件数组元素数超过上限：%d' % count)
    if offset % 8:
        raise MapImportError('原件数组没有按 8 字节对齐（偏移 %d）' % offset)
    size = _ITEMSIZE[kind]
    end = offset + size * count
    if end > len(payload):
        raise MapImportError('原件数组越界（需要到 %d，实际 %d）' % (end, len(payload)))
    values = struct.unpack_from('<%d%s' % (count, _STRUCT[kind]), payload, offset)
    out = list(values)
    # A typed array is an *object* for back-reference numbering: upstream pushes it into
    # ``objs`` too (snapshot.ts:285), so it takes the next index like any other container.
    # Without this, any block where one array is referenced twice (e.g. the shared
    # ``religion.faiths[].color`` in a real ``civ`` part) shifts every later ``{"$$":"r"}``
    # index and the whole part is refused. Registering the *same* list we return keeps a
    # repeated reference identical by identity.
    refs.append(out)
    return out


def parse_part(blob, name=''):
    """Decode one part (decompressing it when the manifest says gzip)."""
    raw = blob
    if len(raw) < len(PART_MAGIC) + 4:
        raise MapImportError('数据块 %s 太短' % name)
    if raw[:len(PART_MAGIC)] != PART_MAGIC:
        raise MapImportError('数据块 %s 不是 CIVSNAP1 原件' % name)
    head_len = struct.unpack('<I', raw[8:12])[0]
    if head_len == 0 or head_len > MAX_JSON_BYTES:
        raise MapImportError('数据块 %s 的结构长度不合理：%d' % (name, head_len))
    if 12 + head_len > len(raw):
        raise MapImportError('数据块 %s 的结构被截断' % name)
    try:
        structure = json.loads(raw[12:12 + head_len].decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MapImportError('数据块 %s 的结构不是合法 JSON：%s' % (name, error))
    payload_start = _pad8(12 + head_len)
    payload = raw[payload_start:]
    return _decode_structure(structure, payload)


# ====================================================================== world
class World:
    """The per-cell arrays this project is willing to read, plus their own geometry."""

    __slots__ = ('cells', 'lon', 'lat', 'elevation', 'water', 'temperature',
                 'precipitation', 'biome', 'neighbours', 'max_elevation', 'meta',
                 'warnings')

    def __init__(self, **fields):
        for name in self.__slots__:
            setattr(self, name, fields.get(name))


def _require_array(part, key, cells, warnings, allow_missing=True):
    value = part.get(key)
    if value is None:
        if allow_missing:
            warnings.append('原件里没有 %s 这一项' % key)
            return None
        raise MapImportError('原件里缺少 %s' % key)
    if not isinstance(value, list):
        raise MapImportError('原件里的 %s 不是数组' % key)
    if len(value) != cells:
        raise MapImportError('原件里 %s 的长度 %d 与地块数 %d 不符'
                             % (key, len(value), cells))
    return value


def read_world(manifest, parts):
    """Extract the cell arrays from the ``map`` part and validate them."""
    by_name = {part.get('name'): part for part in parts}
    if 'map' not in by_name:
        raise MapImportError('原件里没有地图那块（parts: %s）'
                             % '、'.join(sorted(by_name)))
    part_meta = by_name['map']
    blob = part_meta['_bytes']
    if part_meta.get('zip') == 'gzip':
        blob = _inflate(blob)
    decoded = parse_part(blob, 'map')
    if not isinstance(decoded, dict):
        raise MapImportError('地图那块解出来不是对象')

    warnings = []
    mesh = decoded.get('mesh')
    if not isinstance(mesh, dict):
        raise MapImportError('地图那块里没有网格（mesh）')
    cells = mesh.get('n')
    if isinstance(cells, bool) or not isinstance(cells, int) or cells <= 0:
        raise MapImportError('网格地块数不是正整数')
    if cells > MAX_CELLS:
        raise MapImportError('地块数 %d 超过上限 %d' % (cells, MAX_CELLS))
    mesh_width, mesh_height = mesh.get('width'), mesh.get('height')
    for value, label in ((mesh_width, 'width'), (mesh_height, 'height')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise MapImportError('网格的 %s 不是正数' % label)

    xs = _require_array(mesh, 'x', cells, warnings, allow_missing=False)
    ys = _require_array(mesh, 'y', cells, warnings, allow_missing=False)
    adj_start = _require_array(mesh, 'adjStart', cells + 1, warnings)
    adj = mesh.get('adj')
    if adj is not None and not isinstance(adj, list):
        raise MapImportError('网格的 adj 不是数组')

    lon = [-180.0 + 360.0 * xs[i] / mesh_width for i in range(cells)]
    lat = [90.0 - 180.0 * ys[i] / mesh_height for i in range(cells)]
    for value in lon:
        if not math.isfinite(value) or not -180.0001 <= value <= 180.0001:
            raise MapImportError('网格里有经度不合法（%r）' % value)
    for value in lat:
        if not math.isfinite(value) or not -90.0001 <= value <= 90.0001:
            raise MapImportError('网格里有纬度不合法（%r）' % value)

    elevation = _require_array(decoded, 'elevation', cells, warnings)
    if elevation is None:
        warnings.append('原件里没有 elevation：只能按海陆与气候取样，海拔留空')

    def finite(values, label, low, high):
        if values is None:
            return None
        out = []
        for value in values:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise MapImportError('%s 里有非数字' % label)
            if not math.isfinite(value):
                raise MapImportError('%s 里有 NaN/Inf，拒绝（原件本不该含这些）' % label)
            if not low <= value <= high:
                raise MapImportError('%s 里有一项 %r 超出 %r…%r' % (label, value, low, high))
            out.append(float(value))
        return out

    water = _require_array(decoded, 'water', cells, warnings)
    if water is not None:
        for value in water:
            if value not in (0, 1, 2):
                raise MapImportError('water 里出现 %r；只认 0 陆地 / 1 海洋 / 2 湖泊'
                                     % (value,))
    temperature = finite(_require_array(decoded, 'temperature', cells, warnings),
                         'temperature', -120.0, 80.0)
    precipitation = finite(_require_array(decoded, 'precipitation', cells, warnings),
                           'precipitation', 0.0, 20000.0)
    biome = _require_array(decoded, 'biome', cells, warnings)
    if biome is not None:
        for value in biome:
            if isinstance(value, bool) or not isinstance(value, int):
                raise MapImportError('biome 里有非整数')
            if not 0 <= value < len(BIOME_NAMES):
                raise MapImportError('biome 里有未知编号 %r（只认 0…%d）'
                                     % (value, len(BIOME_NAMES) - 1))

    neighbours = None
    if adj_start is not None and adj is not None:
        if len(adj_start) != cells + 1:
            raise MapImportError('网格邻接表的起始表长度不对')
        if adj_start[0] != 0 or adj_start[-1] != len(adj):
            raise MapImportError('网格邻接表的首尾不闭合')
        for index in range(cells):
            if adj_start[index] > adj_start[index + 1]:
                raise MapImportError('网格邻接表的起始编号不是递增的')
        neighbours = adj_start

    max_elevation = decoded.get('maxElevation')
    if not isinstance(max_elevation, (int, float)) or isinstance(max_elevation, bool):
        max_elevation = None
    elif not math.isfinite(max_elevation):
        max_elevation = None
    return World(cells=cells, lon=lon, lat=lat, elevation=elevation, water=water,
                 temperature=temperature, precipitation=precipitation, biome=biome,
                 neighbours=(neighbours, adj), max_elevation=max_elevation,
                 meta={'mesh_width': mesh_width, 'mesh_height': mesh_height},
                 warnings=warnings)


# ==================================================================== sampling
def _ring_east_west_km(world, cells, radius_km):
    """Largest great-circle distance between two sampled cells, in km.

    ``span_km`` used to report ``4*sqrt(cell_area/pi)`` for every window size — a cell
    diameter, not the span of the sampled region — and an earlier attempt used
    ``max(lat) - min(lat)``, which is 0 for any window inside one latitude band.
    Measuring the widest pair of the actual cells is well defined in both directions and
    does grow with the window.
    """
    if not cells or len(cells) < 2:
        return 0.0
    best = 0.0
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            d = _angular_distance(world.lon[a], world.lat[a],
                                  world.lon[b], world.lat[b]) * radius_km
            if d > best:
                best = d
    return best



def _angular_distance(lon_a, lat_a, lon_b, lat_b):
    ra, rb = math.radians(lat_a), math.radians(lat_b)
    dl = math.radians(lon_b - lon_a)
    cos = (math.sin(ra) * math.sin(rb)
           + math.cos(ra) * math.cos(rb) * math.cos(dl))
    return math.acos(max(-1.0, min(1.0, cos)))


def _ring(world, start, steps):
    """Cells within ``steps`` hops of ``start`` (falls back to the cell itself)."""
    adj_start, adj = world.neighbours
    if adj_start is None:
        return [start]
    seen = {start}
    frontier = [start]
    for _ in range(max(0, steps)):
        nxt = []
        for cell in frontier:
            for index in range(adj_start[cell], adj_start[cell + 1]):
                other = adj[index]
                if isinstance(other, bool) or not isinstance(other, int):
                    raise MapImportError('网格邻接表里有非整数')
                if not 0 <= other < world.cells:
                    raise MapImportError('网格邻接表指向不存在的地块 %r' % (other,))
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
        if not frontier:
            break
    return sorted(seen)


def sample_region(world, lon, lat, window_px=3, radius_km=6371.0088):
    """Nearest-cell sample with the same return shape as the heightmap sampler."""
    if isinstance(window_px, bool) or not isinstance(window_px, int):
        raise MapImportError('窗格必须是整数')
    if window_px < 3 or window_px > 15 or window_px % 2 == 0:
        raise MapImportError('窗格必须是 3…15 之间的奇数')
    if isinstance(radius_km, bool) or not isinstance(radius_km, (int, float)):
        raise MapImportError('星体半径必须是数字')
    radius_km = float(radius_km)
    if not 1000.0 <= radius_km <= 20000.0:
        raise MapImportError('星体半径必须在 1000…20000 km 之间')
    if isinstance(lat, bool) or not isinstance(lat, (int, float)) or not math.isfinite(lat):
        raise MapImportError('纬度必须是有限数字')
    if isinstance(lon, bool) or not isinstance(lon, (int, float)) or not math.isfinite(lon):
        raise MapImportError('经度必须是有限数字')
    if not -90.0 <= lat <= 90.0:
        raise MapImportError('纬度必须在 −90…90 之间')
    if abs(lat) > 89.5:
        raise MapImportError('取样点太靠近极点（|纬度| > 89.5），该处地块畸变，不取样')

    lon = ((lon + 180.0) % 360.0) - 180.0
    center, best = 0, -2.0
    for cell in range(world.cells):
        cos = (math.sin(math.radians(lat)) * math.sin(math.radians(world.lat[cell]))
               + math.cos(math.radians(lat)) * math.cos(math.radians(world.lat[cell]))
               * math.cos(math.radians(world.lon[cell] - lon)))
        if cos > best:
            center, best = cell, cos
    cells = _ring(world, center, max(1, window_px // 2))
    if len(cells) < 3:
        raise MapImportError('取样窗里的地块太少，无法计算地形')

    warnings = list(world.warnings)
    # 球面泊松盘网格的地块近似等面积；这里的 cell_area 是**球面均分近似**（4πR²/n），
    # 不是逐地块实测面积。用它算出来的区域面积也只能当近似值读。
    cell_area = 4.0 * math.pi * radius_km * radius_km / world.cells

    # 水体分三种：0 陆地 / 1 海洋 / 2 湖泊。只有 **0（干陆地）** 能当聚落中心——
    # 湖面、海面都不能建镇，哪怕周边陆地很多。窗内的水面也不计入可耕地面积。
    center_water = None if world.water is None else world.water[center]
    if center_water is None:
        # 高度图导入没有水体数组：只能按海/陆灰度判，湖泊无从分辨，如实标 unknown。
        dry_land = list(cells)
        lake_cells = []
        ocean_cells = []
        unknown_water = True
    else:
        dry_land = [cell for cell in cells if world.water[cell] == 0]
        lake_cells = [cell for cell in cells if world.water[cell] == 2]
        ocean_cells = [cell for cell in cells if world.water[cell] == 1]
        unknown_water = False
        if center_water == 1:
            raise MapImportError('选点落在海面上：城镇要建在陆地上，请在陆地上选点')
        if center_water == 2:
            raise MapImportError('选点落在湖面上：湖泊不能建镇，请选湖岸的陆地'
                                 '（湖的存在不代表可用水量）')
    land = dry_land + lake_cells            # 有陆地性质的地块（湖面也在地面上）
    water_cells = len(lake_cells) + len(ocean_cells)
    if not cells:
        raise MapImportError('取样窗里的地块太少，无法计算地形')
    sea_fraction = len(ocean_cells) / len(cells)
    lake_fraction = len(lake_cells) / len(cells)
    dry_fraction = len(dry_land) / len(cells)
    if dry_land and len(dry_land) / len(cells) < 0.5:
        raise MapImportError('窗格内可用陆地只占 %.0f%%（海 %.0f%%、湖 %.0f%%），不能在这里建镇'
                             % (dry_fraction * 100, sea_fraction * 100, lake_fraction * 100))
    if sea_fraction > 0.1:
        warnings.append('窗格内海面占 %.0f%%，聚落可用陆地偏少' % (sea_fraction * 100))
    if lake_fraction > 0:
        warnings.append('窗格内湖面占 %.0f%%：湖只说明有水面，不代表取水能力' % (lake_fraction * 100))
    if not dry_land:
        raise MapImportError('窗格内没有干陆地地块，不能建镇')

    # 面积只算干陆地；水面（海/湖）单列，不当可耕地，也不计入 TownInput 的 area_km2。
    area_km2 = cell_area * len(dry_land)
    # 不在这里按 TownInput 的 20000 km² 上限拒收：本网格的单个地块就可能已经大于它
    # （34097 格、R=6371 时单格约 14959 km²），按面积提前拒会让这类世界永远无法取样。
    # 面积语义说清楚：这是「干陆地面积」，且是球面均分近似；是否适合建镇由取样窗大小
    # 与下层的城镇规则决定，上层需要时会看到真实数值。

    elevations = [world.elevation[cell] for cell in land] if world.elevation else []
    if elevations:
        for value in elevations:
            if not math.isfinite(value) or not -12000.0 <= value <= 12000.0:
                raise MapImportError('高程 %r 不在 −12000…12000 米之内' % (value,))
        mean_elevation = sum(elevations) / len(elevations)
    else:
        mean_elevation = 0.0
        warnings.append('原件没有高程，elevation_m 暂记 0，不能用于判水源或坡度')

    slopes = []
    for cell in land:
        for other in _ring(world, cell, 1):
            if other == cell or (world.water is not None and world.water[other] == 1):
                continue
            if not world.elevation:
                continue
            metres = (_angular_distance(world.lon[cell], world.lat[cell],
                                        world.lon[other], world.lat[other]) * radius_km * 1000.0)
            if metres < 1.0:
                continue
            dz = world.elevation[other] - world.elevation[cell]
            slopes.append(math.degrees(math.atan(abs(dz) / metres)))
    if not slopes:
        raise MapImportError('窗格内没有可算坡度的相邻陆地地块，请调大窗格')

    def mean_of(values):
        if values is None:
            return None
        picked = [values[cell] for cell in land]
        return sum(picked) / len(picked) if picked else None

    temperature = mean_of(world.temperature)
    precipitation = mean_of(world.precipitation)
    biome = world.biome[center] if world.biome else None
    climate = None
    if temperature is not None and precipitation is not None:
        climate = {'temperature_c': round(temperature, 2),
                   'precipitation_mm': round(precipitation, 1),
                   'biome': biome,
                   'biome_name': BIOME_NAMES[biome] if biome is not None else None,
                   'measured': True}
    lon_top = max(world.lat[cell] for cell in cells)
    lon_bottom = min(world.lat[cell] for cell in cells)
    return {
        'lon': round(lon, 4),
        'lat': round(lat, 4),
        'window_px': window_px,
        'cell': {'index': center, 'cells': cells, 'cell_count': len(cells)},
        'pixel': {'x': center, 'y': 0, 'x0': center, 'y0': 0,
                  'columns': len(cells), 'rows': 1},
        'lat_top': round(lon_top, 4),
        'lat_bottom': round(lon_bottom, 4),
        # 实际取样区的跨度：取窗内任意两格的最大球面距离，东西/南北两向都能反映真实范围。
        # 旧写法对所有窗格返回同一个「单格直径」，后面一版又用 lat 差（同纬度带恒为 0），
        # 两种都不对，所以这里只用实测的格间距离。
        'span_km': {'north_south': round((lon_top - lon_bottom) / 360.0 * 2.0 * math.pi
                                         * radius_km, 1),
                    'east_west': round(_ring_east_west_km(world, cells, radius_km), 1),
                    'widest_pair_km': round(_ring_east_west_km(world, cells, radius_km), 1),
                    'typical_cell_km': round(math.sqrt(cell_area), 2),
                    'note': ('north_south 取取样格的纬度包络；east_west/widest_pair 取窗内任意两格的'
                             '最大球面距离；typical_cell_km 是均分面积开方的典型格径，不是取样区宽度')},
        'elevation_m': {'min': round(min(elevations), 1) if elevations else 0.0,
                        'max': round(max(elevations), 1) if elevations else 0.0,
                        'mean': round(mean_elevation, 1)},
        'sea_fraction': round(sea_fraction, 4),
        'land_km2': round(cell_area * len(land), 1),
        'sea_km2': round(cell_area * len(cells) - cell_area * len(ocean_cells), 1),
        'area_km2': round(cell_area * len(dry_land), 1),
        'dryland_km2': round(cell_area * len(dry_land), 1),
        'lake_km2': round(cell_area * len(lake_cells), 1),
        'ocean_km2': round(cell_area * len(ocean_cells), 1),
        'slope_deg': {'p50': round(sorted(slopes)[len(slopes) // 2], 2),
                      'max': round(max(slopes), 2)},
        'vertical_m': 0.0,
        'radius_km': round(radius_km, 4),
        'cell_area_km2': round(cell_area, 1),
        'dry_fraction': round(dry_fraction, 4),
        'lake_fraction': round(lake_fraction, 4),
        'water_known': not unknown_water,
        'climate': climate,
        'derived': ['elevation_m', 'area_km2', 'land_km2', 'slope_deg', 'sea_fraction',
                    'temperature_c', 'precipitation_mm', 'biome'],
        'blocked': list(BLOCKED_FIELDS),
        'blocked_reason': dict(BLOCKED_REASON),
        'warnings': warnings,
    }


# ===================================================================== import
def create_import(store, root, data, declared=None):
    """Validate a ``.civsnap`` and record bounded metadata + the per-cell inventory.

    The file itself is stored by content hash; the document keeps only numbers, names and
    the arrays' source (a hash and a manifest), never a copy of the arrays.
    """
    declared = dict(declared or {})
    manifest, parts = parse_container(data)
    world = read_world(manifest, parts)
    digest = hashlib.sha256(bytes(data)).hexdigest()
    identifier = 'sn_' + digest[:12]
    existing = store.get('map_import', identifier)
    target = import_dir(root) / ('%s.civsnap' % digest[:32])
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(data))
    elif target.stat().st_size != len(bytes(data)):
        raise MapImportError('同名哈希的文件已存在但大小不同，拒绝覆盖')
    if existing:
        return existing

    snapshot = manifest.get('snapshot') or {}
    record = {
        'id': identifier,
        'format': FORMAT,
        'created': None,
        'source': {
            'project': 'civ-atlas',
            'repo': 'https://github.com/guaner-334/civ-atlas',
            'commit': (str(declared.get('commit') or '').strip() or None),
            'spec_commit': SPEC_COMMIT,
            'license': ('upstream code AGPL-3.0-only; the exported world data is the '
                        "author's own. Read here by an independent parser."),
            'generator_version': snapshot.get('generator'),
            'snapshot_format': snapshot.get('format'),
            'recipe': str(snapshot.get('recipe') or ''),
            'world_id': (manifest.get('world') or {}).get('id'),
            'world_app': (manifest.get('world') or {}).get('app'),
            'exported_at': manifest.get('exported_at'),
            'extractor': manifest.get('exported_by'),
        },
        'file': target.name,
        'sha256': digest,
        'bytes': len(bytes(data)),
        'pixels': world.cells,
        'width': world.cells,
        'height': 1,
        'seed': None,
        'lo_m': None,
        'hi_m': None,
        'sea_gray': None,
        'parts': [{'name': part.get('name'), 'bytes': part.get('bytes'),
                   'zip': part.get('zip'), 'length': part.get('length'),
                   # 服务端在解析时真算的 SHA-256，口径与上游一致：
                   # 对**解压后**的字节算（manifest 的 sum 就是这个口径）。
                   'sum': hashlib.sha256(_inflate(part['_bytes'])
                                         if part.get('zip') == 'gzip' else bytes(part['_bytes'])
                                         ).hexdigest(),
                   'sum_verified_by': 'server'}
                  for part in parts],
        'units': {
            'elevation': 'metre (World.elevation, positive on land)',
            'water': '0 land / 1 ocean / 2 lake (World.water)',
            'temperature': 'degC annual mean (World.temperature)',
            'precipitation': 'mm/year (World.precipitation)',
            'biome': 'index 0…15 of src/gen/biomes.ts',
            'area': ('sphere area / cell count (Poisson-disc mesh cells are near-equal '
                     'area), radius declared: %.4f km' % (declared.get('radius_km')
                                                          or 6371.0088)),
            'vertical_m': 0.0,
        },
        'stats': {
            'cells': world.cells,
            'sea_cells': sum(1 for value in (world.water or []) if value == 1),
            'lake_cells': sum(1 for value in (world.water or []) if value == 2),
            'has_elevation': world.elevation is not None,
            'has_temperature': world.temperature is not None,
            'has_precipitation': world.precipitation is not None,
            'has_biome': world.biome is not None,
        },
        'derived': ['elevation_m', 'area_km2', 'land_km2', 'slope_deg', 'sea_fraction',
                    'temperature_c', 'precipitation_mm', 'biome'],
        'blocked': list(BLOCKED_FIELDS),
        'note_text': '',
        'warnings': list(world.warnings),
    }
    store.put('map_import', identifier, record)
    return record


def load_world(root, record):
    """Re-read the persisted ``.civsnap`` and rebuild the cell arrays."""
    target = import_dir(root) / record['file']
    if not target.exists():
        raise MapImportError('导入的原件文件已不在（%s），请重新导出' % record['file'])
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.get('sha256'):
        raise MapImportError('导入的原件文件校验失败（内容与记录的哈希不符）')
    manifest, parts = parse_container(data)
    return read_world(manifest, parts)


def preview_grid(world, max_side=180):
    """Coarse lon/lat raster of the real per-cell arrays, for the author canvas.

    Returns ``{'width','height','land','water','elevation','temperature',
    'precipitation','biome'}``. Every field is a plain list of numbers, one entry per grid
    cell, filled from the cell that lands in that box; ``cells[index]`` says whether any
    cell was seen (so a caller can tell an empty box from a real 0 m). Nothing here is a
    new measurement: it is the exported world's own values, coarsened.
    """
    width = min(max_side, 360)
    height = max(2, width // 2)
    size = width * height
    land = [0] * size
    water = [-1] * size
    cells_seen = [0] * size
    elevation = [0.0] * size
    temperature = [0.0] * size
    precipitation = [0.0] * size
    biome = [-1] * size
    for cell in range(world.cells):
        x = int((world.lon[cell] + 180.0) / 360.0 * width) % width
        y = min(height - 1, int((90.0 - world.lat[cell]) / 180.0 * height))
        index = y * width + x
        cells_seen[index] = 1
        if world.water is not None:
            water[index] = world.water[cell]
        if world.water is not None and world.water[cell] == 1:
            land[index] = 0
        else:
            land[index] = 1
            if world.elevation is not None:
                elevation[index] = round(world.elevation[cell], 1)
        if world.temperature is not None:
            temperature[index] = round(world.temperature[cell], 1)
        if world.precipitation is not None:
            precipitation[index] = round(world.precipitation[cell], 0)
        if world.biome is not None:
            biome[index] = world.biome[cell]
    return {'width': width, 'height': height, 'land': land, 'water': water,
            'cells': cells_seen, 'elevation': elevation, 'temperature': temperature,
            'precipitation': precipitation, 'biome': biome}


#: Layer ids the author canvas can ask for, and what each one paints.
PREVIEW_LAYERS = ('elevation', 'water', 'temperature', 'precipitation', 'biome')


def _ramp(stops, value):
    """Linear interpolation across ``[(v, r, g, b), …]``; clamped at both ends."""
    if value is None:
        return (26, 32, 38)
    if value <= stops[0][0]:
        return stops[0][1:]
    for (v0, r0, g0, b0), (v1, r1, g1, b1) in zip(stops, stops[1:]):
        if value <= v1:
            span = (v1 - v0) or 1.0
            t = (value - v0) / span
            return (int(r0 + (r1 - r0) * t), int(g0 + (g1 - g0) * t),
                    int(b0 + (b1 - b0) * t))
    return stops[-1][1:]


_ELEVATION_STOPS = [(-200, 46, 84, 120), (0, 90, 132, 110), (200, 121, 176, 110),
                    (500, 179, 206, 124), (1500, 225, 219, 145), (3000, 223, 187, 120),
                    (4500, 201, 146, 93), (6000, 243, 238, 229)]
_TEMPERATURE_STOPS = [(-30, 61, 92, 120), (-10, 92, 127, 140), (5, 159, 184, 166),
                      (20, 216, 207, 166), (30, 201, 143, 106), (45, 168, 92, 71)]
_PRECIPITATION_STOPS = [(0, 138, 122, 82), (200, 127, 154, 106), (600, 95, 154, 138),
                        (1200, 74, 127, 168), (2500, 58, 95, 154), (5000, 44, 70, 118)]
#: One colour per upstream biome code (src/gen/biomes.ts:5-22), in enum order.
_BIOME_RGB = ((26, 42, 62), (42, 76, 108), (214, 226, 233), (243, 238, 229), (185, 179, 160),
              (79, 111, 74), (139, 138, 118), (201, 176, 114), (143, 160, 106), (86, 122, 74),
              (63, 122, 82), (196, 154, 96), (168, 158, 90), (74, 122, 74), (47, 96, 58),
              (86, 122, 106))
_WATER_RGB = {1: (29, 43, 52), 2: (63, 111, 138)}


def preview_rgb(grid, layer='elevation'):
    """Paint one layer of :func:`preview_grid` as flat RGB bytes (3 per grid cell).

    This is a picture for the author to aim at, not a data channel: numbers come from
    :func:`sample_region` / the import record, never from these bytes.
    """
    if layer not in PREVIEW_LAYERS:
        raise MapImportError('没有这个图层：%s（可选 %s）' % (layer, '、'.join(PREVIEW_LAYERS)))
    width, height = grid['width'], grid['height']
    out = bytearray(width * height * 3)
    for index in range(width * height):
        if not grid['cells'][index]:
            rgb = (18, 24, 30)                      # a box no cell landed in
        elif layer == 'water':
            rgb = _WATER_RGB.get(grid['water'][index], (159, 179, 168))
        elif layer == 'biome':
            code = grid['biome'][index]
            rgb = _BIOME_RGB[code] if isinstance(code, int) and 0 <= code < len(_BIOME_RGB) else (18, 24, 30)
        elif not grid['land'][index]:
            rgb = _WATER_RGB.get(grid['water'][index], (29, 43, 52))
        elif layer == 'elevation':
            rgb = _ramp(_ELEVATION_STOPS, grid['elevation'][index] if grid['elevation'] else None)
        elif layer == 'temperature':
            rgb = _ramp(_TEMPERATURE_STOPS, grid['temperature'][index])
        else:
            rgb = _ramp(_PRECIPITATION_STOPS, grid['precipitation'][index])
        base = index * 3
        out[base], out[base + 1], out[base + 2] = rgb
    return bytes(out)
