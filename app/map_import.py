"""Bounded adapter for terrain data *exported* from civ-atlas.

Scope, deliberately narrow:

* This module reads **exported data files only**, and it is an independent implementation:
  it does not copy, vendor, link or execute any civ-atlas source. The heightmap format
  implemented here was read from the upstream source, not guessed; every claim carries a
  ``file:line`` reference in ``docs/civ-atlas-integration.md``.
* The world save file (``src/gen/savefile.ts``) is **refused**: it carries only
  ``seed + params + edits`` and no terrain, so nothing can be reconstructed from it
  without running the upstream generator.
* Per-cell temperature/precipitation/biome/elevation live in the browser's ``Snapshot``,
  which is read by :mod:`app.civ_atlas_snapshot` from a file the author exports with
  ``tools/civ_atlas_export.js``. This module handles the *heightmap* fallback, where only
  elevation and a sea/land mask exist; anything else stays marked missing rather than
  estimated.
* Elevation is converted with the linear mapping the export declares
  (``gray 0 = lo m``, ``65535 -> hi``), so no normalised value is ever called "metres".
* Numbers this adapter needs that the export does *not* carry (the planet radius, the
  pixel-centre convention) are declared assumptions carried through into the record.

Entry points: :func:`create_import`, :func:`sample_region`, :func:`build_town_input`,
:func:`preview_png`.
"""
import hashlib
import io
import json
import math
import re
import struct
import zlib
from array import array

try:                                    # the one pixel decoder, declared in requirements.txt
    from PIL import Image as _PILImage
except Exception:                       # pragma: no cover - reported when actually needed
    _PILImage = None

# --------------------------------------------------------------------- contract
FORMAT = 'civ_atlas_heightmap_v1'
SPEC_REPO = 'https://github.com/guaner-334/civ-atlas'
#: The upstream revision every format claim here was read from.
SPEC_COMMIT = '0939c5f1622a5e45cfc16f645ea3845993ab3985'
SPEC_FILES = ('src/gen/heightmap.ts', 'src/gen/png.ts', 'src/gen/world.ts',
              'tests/export.test.ts', 'src/gen/savefile.ts')
SPEC_LICENSE = ('upstream code is AGPL-3.0-only; upstream states that worlds it generates '
                'and the maps it exports belong to the author. This adapter is independent '
                'code that only reads such exported data and does not import or bundle '
                'upstream source. Nothing here is a statement of legal permission.')

# ---------------------------------------------------------------- hard bounds
MAX_PNG_BYTES = 18 * 1024 * 1024
MAX_PNG_B64 = 24 * 1024 * 1024
#: 4096 x 2048 = the "2x" export scale; bigger files are refused rather than chewed on.
MAX_PIXELS = 4096 * 2048
MAX_TEXT_BYTES = 64 * 1024
MAX_NOTE_CHARS = 4000
MAX_WINDOW_PX = 15
MIN_WINDOW_PX = 3
#: Declared assumption: upstream ``WorldParams`` (src/gen/params.ts:9-30) has **no** planet
#: radius field and the export carries none, so horizontal distance needs one.
DEFAULT_RADIUS_KM = 6371.0088
SEA_REJECT_FRACTION = 0.5
SEA_WARN_FRACTION = 0.1
#: The heightmap has no file-level source for these; they are reported, never guessed.
MISSING_FIELDS = ('temperature_c', 'precipitation_mm', 'biome', 'resources', 'river',
                  'lake', 'flux', 'cell_id', 'faction', 'settlement')
#: Fields this adapter actually derives from the exported integers.
DERIVED_FIELDS = ('elevation_m', 'area_km2', 'land_km2', 'slope_deg', 'sea_fraction')

_SIGNATURE = b'\x89PNG\r\n\x1a\n'
_DESC_BITS = '16-bit grayscale heightmap'
_DESC_LO = re.compile(r'Gray 0 = (-?\d+) m')
_DESC_HI = re.compile(r'65535 = (-?\d+) m')
_DESC_SEA = re.compile(r'Sea level \(0 m\) = gray (\d+)')
_DESC_SOURCE = re.compile(r'seed\s+(-?\d+)')
_NOTE_LO = re.compile(r'灰度\s*0\s*=\s*(-?[\d,]+)\s*米')
_NOTE_HI = re.compile(r'灰度\s*65535\s*=\s*(-?[\d,]+)\s*米')
_NOTE_SEA = re.compile(r'海平面（0 米）=\s*灰度\s*(\d+)')
_NOTE_SEED = re.compile(r'世界:\s*种子\s*(-?\d+)')
_NOTE_SIZE = re.compile(r'尺寸:\s*(\d+)\s*×\s*(\d+)')


class MapImportError(ValueError):
    """A refused import/sample/build. One sentence, and no partially written record."""


# ================================================== PNG container (strict, bounded)
def _crc_table():
    table = []
    for n in range(256):
        c = n
        for _ in range(8):
            c = (0xEDB88320 ^ (c >> 1)) if c & 1 else (c >> 1)
        table.append(c)
    return table


_CRC = _crc_table()


def crc32(data, crc=0):
    c = (~crc) & 0xFFFFFFFF
    for byte in data:
        c = _CRC[(c ^ byte) & 0xFF] ^ (c >> 8)
    return (~c) & 0xFFFFFFFF


def scan_png(data):
    """Validate the PNG *container* and return its header, tEXt pairs and IDAT payload.

    Runs before any pixel decoding, so every resource limit is enforced on the declared
    dimensions and on the compressed stream, never after an unbounded decompress.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise MapImportError('导入内容必须是文件字节')
    data = bytes(data)
    if len(data) > MAX_PNG_BYTES:
        raise MapImportError('文件超过 %d MB 上限' % (MAX_PNG_BYTES // (1024 * 1024)))
    if len(data) < 8 + 25 + 12:
        raise MapImportError('文件太短，不像 PNG')
    if data[:8] != _SIGNATURE:
        raise MapImportError('不是 PNG 文件（文件签名不符）')

    pos = 8
    header = None
    idat = bytearray()
    text = {}
    text_bytes = 0
    saw_end = False
    while pos + 8 <= len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        if length > len(data) - pos - 12:
            raise MapImportError('PNG 数据块长度越界（文件可能被截断）')
        body = data[pos + 8:pos + 8 + length]
        want = struct.unpack('>I', data[pos + 8 + length:pos + 12 + length])[0]
        if crc32(ctype + body) != want:
            raise MapImportError('PNG 数据块 %s 校验失败（文件损坏）' % ctype.decode('latin-1'))
        pos += 12 + length
        if header is None and ctype != b'IHDR':
            raise MapImportError('PNG 第一个数据块必须是 IHDR')
        if ctype == b'IHDR':
            if header is not None:
                raise MapImportError('PNG 出现两个 IHDR')
            if length != 13:
                raise MapImportError('IHDR 长度不是 13')
            width, height = struct.unpack('>II', body[0:8])
            header = {'width': width, 'height': height, 'bit_depth': body[8],
                      'color': body[9], 'comp': body[10], 'filt': body[11],
                      'interlace': body[12]}
            if width <= 0 or height <= 0:
                raise MapImportError('PNG 尺寸为零')
            if width != 2 * height:
                raise MapImportError('高度图必须是等距圆柱 2:1（宽 = 2 × 高），这个文件是 %d×%d'
                                     % (width, height))
            if width * height > MAX_PIXELS:
                raise MapImportError('图像 %d×%d 超过上限（最多 %d 像素，即 4096×2048）'
                                     % (width, height, MAX_PIXELS))
        elif ctype == b'IDAT':
            idat += body
            if len(idat) > MAX_PNG_BYTES:
                raise MapImportError('PNG 图像数据超过上限')
        elif ctype == b'tEXt':
            text_bytes += length
            if text_bytes > MAX_TEXT_BYTES:
                raise MapImportError('PNG 文字块总长度超过上限')
            key, _, value = body.partition(b'\x00')
            if not key or len(key) > 79:
                raise MapImportError('PNG tEXt 关键字长度不合法')
            text[key.decode('latin-1', 'replace')] = value.decode('latin-1', 'replace')
        elif ctype == b'IEND':
            saw_end = True
            break
        # Any other chunk (gAMA, sRGB, iCCP …) cannot change the numbers, so it is skipped.

    if header is None:
        raise MapImportError('PNG 缺少 IHDR')
    if not saw_end:
        raise MapImportError('PNG 缺少 IEND（文件不完整）')
    if pos != len(data):
        raise MapImportError('PNG 结束后还有多余字节')
    if header['color'] != 0:
        raise MapImportError('高度图必须是灰度图（colorType 0），这个文件是 %d'
                             % header['color'])
    if header['interlace'] != 0:
        raise MapImportError('不支持隔行（interlaced）PNG')
    if header['comp'] != 0 or header['filt'] != 0:
        raise MapImportError('PNG 压缩/滤波方式不是标准值')
    if header['bit_depth'] != 16:
        raise MapImportError('请使用导出的「高度图 16 位」；8 位高度图是有损的 Azgaar 刻度，'
                             '本项目不按它反推海拔')
    if not idat:
        raise MapImportError('PNG 没有图像数据（IDAT）')
    header['text'] = text
    header['idat'] = bytes(idat)
    return header


def decode_gray_png(data):
    """Strict container scan, then a bounded 16-bit pixel decode through Pillow.

    Pillow is the single declared pixel decoder (``requirements.txt``). Because
    :func:`scan_png` runs first, every size limit is enforced on the declared dimensions and
    on the compressed stream before Pillow is handed the bytes. A host without Pillow gets a
    plain instruction instead of a second, subtly different decoder nobody compares against.
    """
    header = scan_png(data)
    width, height = header['width'], header['height']
    if _PILImage is None:
        raise MapImportError('缺少 Pillow：请在运行织梦的 Python 环境里安装 Pillow'
                             '（requirements.txt 已列出），否则无法读取 16 位高度图')
    try:
        image = _PILImage.open(io.BytesIO(bytes(data)))
        if image.size != (width, height):
            raise MapImportError('PNG 像素尺寸与 IHDR 声明不一致')
        if image.mode not in ('I;16', 'I;16B', 'I;16L', 'I'):
            raise MapImportError('PNG 不是 16 位灰度（Pillow 读出 %s）' % image.mode)
        image.load()
        gray = array('H', image.getdata())
    except MapImportError:
        raise
    except Exception as error:
        raise MapImportError('PNG 像素解码失败：%s' % error)
    if len(gray) != width * height:
        raise MapImportError('PNG 像素数与尺寸不符')
    if min(gray) < 0 or max(gray) > 65535:
        raise MapImportError('PNG 出现超出 16 位范围的灰度值')
    return {'width': width, 'height': height, 'bit_depth': 16,
            'gray': gray, 'text': header['text'], 'decoder': 'pillow'}


def encode_gray_preview(pixels, width, height):
    """8-bit grayscale PNG with filter 0 on every row (a picture, not a data channel)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += bytes(pixels[y * width:(y + 1) * width])
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
    return b''.join([_SIGNATURE, _chunk(b'IHDR', ihdr),
                     _chunk(b'IDAT', zlib.compress(bytes(raw), 6)), _chunk(b'IEND', b'')])


def encode_rgb_preview(pixels, width, height):
    """8-bit RGB PNG with filter 0 on every row (a picture, not a data channel)."""
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += bytes(pixels[y * stride:(y + 1) * stride])
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b''.join([_SIGNATURE, _chunk(b'IHDR', ihdr),
                     _chunk(b'IDAT', zlib.compress(bytes(raw), 6)), _chunk(b'IEND', b'')])


def _chunk(ctype, body):
    return (struct.pack('>I', len(body)) + ctype + body
            + struct.pack('>I', crc32(ctype + body)))


# ================================================================== the export
class Heightmap:
    """A validated civ-atlas heightmap plus the conversions it declares."""

    __slots__ = ('width', 'height', 'lo_m', 'hi_m', 'sea_gray', 'gray', 'text', 'seed',
                 'software', 'warnings', 'sha256', 'note_text', 'linear_fill', 'decoder',
                 'sea_clamped_low', 'sea_clamped_high')

    def __init__(self, **fields):
        for name in self.__slots__:
            setattr(self, name, fields.get(name))

    @property
    def pixels(self):
        """Total pixel count. Kept as a property so every construction path has it."""
        return (self.width or 0) * (self.height or 0)

    def is_sea(self, gray):
        """Upstream's own split: only ``water === 1`` is sea; lakes (2) take the land branch.

        The encoder clamps sea to ``<= S-1`` and land to ``>= S+1`` (heightmap.ts:84-90), so
        for ``0 < S < 65535`` the level ``S`` never appears and this integer test is exact.
        At the two extremes the clamp *does* emit ``S``: with ``S == 0`` the ``max(0, …)``
        floor turns sea pixels into 0, and with ``S == 65535`` the ``min(65535, …)``
        ceiling turns land pixels into 65535. Both cases are handled here and recorded.
        """
        if gray < self.sea_gray:
            return True
        if gray > self.sea_gray:
            return False
        return self.sea_gray == 0            # only reachable through the clamp

    def elev_m(self, gray):
        return self.lo_m + (gray / 65535.0) * (self.hi_m - self.lo_m)

    @property
    def quantization_m(self):
        return (self.hi_m - self.lo_m) / 65535.0

    @property
    def vertical_m(self):
        """± uncertainty of one converted elevation.

        ``lo``/``hi`` reach the file only as ``Math.round()`` integers, so reading them back
        costs at most 0.5 m for any gray (the two half-metre terms cannot both be maximal),
        plus half a quantisation step from the 16-bit grid. The coastline is resolved by the
        integer sea-level test, but the *height* next to it is only good to about a metre ---
        which is why this is reported instead of being called exact.
        """
        return 0.5 + self.quantization_m / 2.0


def _int_from(pattern, source):
    if not source:
        return None
    found = pattern.search(source)
    return int(found.group(1).replace(',', '')) if found else None


def parse_heightmap(png_bytes, note_text=''):
    """Validate an exported heightmap and return a :class:`Heightmap`.

    The three numbers that make the file interpretable (``lo``, ``hi``, sea-level gray) come
    from the PNG's own ``tEXt`` block, with the sidecar ``.txt`` note as a fallback. If
    neither declares them the file is refused rather than guessed at.
    """
    note_text = (note_text or '').strip()
    if len(note_text) > MAX_NOTE_CHARS:
        raise MapImportError('说明文本超过 %d 字符上限' % MAX_NOTE_CHARS)
    decoded = decode_gray_png(png_bytes)
    width, height, gray, text = (decoded['width'], decoded['height'],
                                 decoded['gray'], decoded['text'])
    warnings = []

    description = text.get('Description', '')
    lo = _int_from(_DESC_LO, description)
    hi = _int_from(_DESC_HI, description)
    sea = _int_from(_DESC_SEA, description)
    if lo is None or hi is None or sea is None:
        lo = _int_from(_NOTE_LO, note_text)
        hi = _int_from(_NOTE_HI, note_text)
        sea = _int_from(_NOTE_SEA, note_text)
        if lo is not None:
            warnings.append('海拔刻度取自说明 .txt（PNG 里没有 tEXt Description）')
    if lo is None or hi is None or sea is None:
        raise MapImportError('这个 PNG 没有声明海拔刻度（缺 tEXt Description，也没给说明 .txt），'
                             '无法换算回米；请用 civ-atlas 的「导出 → 高度图 16 位」重新导出')
    if description and _DESC_BITS not in description:
        raise MapImportError('PNG 说明不是 16 位高度图（没有 “16-bit grayscale heightmap”）')
    if not (lo < 0 < hi):
        raise MapImportError('海拔刻度不合理：灰度 0 = %d 米、65535 = %d 米，必须一负一正'
                             % (lo, hi))
    if not 0 <= sea <= 65535:
        raise MapImportError('海平面灰度 %d 不在 0…65535 之间' % sea)

    seed = _int_from(_DESC_SOURCE, text.get('Source', ''))
    if seed is None:
        seed = _int_from(_NOTE_SEED, note_text)
    if note_text:
        size = _NOTE_SIZE.search(note_text)
        if size and (int(size.group(1)), int(size.group(2))) != (width, height):
            warnings.append('说明 .txt 的尺寸 %s×%s 与图片 %d×%d 不一致，按图片为准'
                            % (size.group(1), size.group(2), width, height))

    min_gray, max_gray = 65535, 0
    ambiguous = 0
    for value in gray:
        if value < min_gray:
            min_gray = value
        if value > max_gray:
            max_gray = value
        if value == sea and 0 < sea < 65535:
            ambiguous += 1
    if ambiguous:
        raise MapImportError('有 %d 个像素正好等于海平面灰度 %d；0 < S < 65535 时导出的高度图'
                             '不会写出这个值，文件可能被改过或不是同一格式' % (ambiguous, sea))
    sea_clamped_low = sea == 0
    sea_clamped_high = sea == 65535
    if sea_clamped_low:
        warnings.append('海平面灰度 = 0：这个世界的海被压到灰度 0（编码器下限），海的深浅'
                        '不可分辨；海陆仍按上游的整数规则判定')
    if sea_clamped_high:
        warnings.append('海平面灰度 = 65535：陆地被压到灰度 65535（编码器上限），陆地高低'
                        '不可分辨')

    expected_sea = round(-lo / (hi - lo) * 65535.0)
    if abs(expected_sea - sea) > 1:
        warnings.append('声明的海平面灰度 %d 与按刻度算出的 %d 差得多（刻度可能被取整过两次）'
                        % (sea, expected_sea))
    linear_fill = (min_gray == 0 and max_gray == 65535)
    if not linear_fill:
        warnings.append('灰度没有铺满 0…65535（实测 %d…%d），海拔换算仍按声明的线性式，'
                        '但两端可能被截断' % (min_gray, max_gray))

    return Heightmap(width=width, height=height, lo_m=lo, hi_m=hi, sea_gray=sea, gray=gray,
                     text=text, seed=seed, software=text.get('Software'),
                     warnings=warnings,
                     sha256=hashlib.sha256(bytes(png_bytes)).hexdigest(),
                     note_text=note_text, linear_fill=linear_fill,
                     decoder=decoded.get('decoder'),
                     sea_clamped_low=sea_clamped_low, sea_clamped_high=sea_clamped_high)


# ================================================================ imports store
def import_id(sha256_hex):
    return 'mi_' + sha256_hex[:12]


def import_dir(root):
    """Where imported payloads live, relative to the data root the caller declares.

    The root is supplied by the caller (the running service passes the directory that holds
    its database), so a temporary or sandboxed store never writes into the real project.
    """
    return root / 'map_imports'


def png_path(root, sha256_hex):
    # Content-addressed from a digest we computed ourselves: no caller-supplied path, name
    # or URL ever reaches the filesystem.
    return import_dir(root) / ('%s.png' % re.sub(r'[^0-9a-f]', '', sha256_hex)[:32])


def summary(record):
    """What lists and the author UI need; never the pixel array."""
    return {key: record.get(key) for key in
            ('id', 'created', 'format', 'width', 'height', 'lo_m', 'hi_m', 'sea_gray',
             'seed', 'source', 'stats', 'warnings', 'missing', 'blocked', 'derived')}


def create_import(store, root, png_bytes, note_text='', declared=None):
    """Validate, persist the PNG by content hash, and record bounded metadata.

    Idempotent on content: the same bytes twice give the same ``id`` and do not rewrite the
    file. The document holds numbers and declarations only --- the pixel array stays in the
    PNG on disk.
    """
    declared = dict(declared or {})
    heightmap = parse_heightmap(png_bytes, note_text)
    identifier = import_id(heightmap.sha256)
    target = png_path(root, heightmap.sha256)
    existing = store.get('map_import', identifier)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(png_bytes))
    elif target.stat().st_size != len(png_bytes):
        raise MapImportError('同名哈希的文件已存在但大小不同，拒绝覆盖')

    commit = str(declared.get('commit') or '').strip()
    if commit and not re.fullmatch(r'[0-9a-f]{7,40}', commit):
        raise MapImportError('commit 必须是 7–40 位十六进制')
    generator_version = declared.get('generator_version')
    if generator_version is not None and (isinstance(generator_version, bool)
                                          or not isinstance(generator_version, int)):
        raise MapImportError('generator_version 必须是整数或留空')
    if existing:
        return existing

    sea_px = sum(1 for value in heightmap.gray if heightmap.is_sea(value))
    record = {
        'id': identifier,
        'format': FORMAT,
        'created': None,                      # stamped by the caller's clock
        'source': {
            'project': 'civ-atlas',
            'repo': SPEC_REPO,
            'commit': commit or None,
            'commit_note': ('作者导入时声明的上游提交；本项目按 %s 读出的格式解析，'
                            '无法从文件本身核对该提交' % SPEC_COMMIT),
            'spec_commit': SPEC_COMMIT,
            'spec_files': list(SPEC_FILES),
            'license': SPEC_LICENSE,
            'generator_version': generator_version,
            'seed': heightmap.seed,
            'software': heightmap.software,
        },
        'width': heightmap.width,
        'height': heightmap.height,
        'lo_m': heightmap.lo_m,
        'hi_m': heightmap.hi_m,
        'sea_gray': heightmap.sea_gray,
        'seed': heightmap.seed,
        'sha256': heightmap.sha256,
        'bytes': len(bytes(png_bytes)),
        'pixels': heightmap.width * heightmap.height,
        'file': target.name,
        'decoder': heightmap.decoder,
        'units': {
            'elevation': 'metre, linear: elev_m = lo_m + gray/65535*(hi_m - lo_m)',
            'sea_land': ('integer test on the declared sea-level gray: gray < S is sea, '
                         'gray > S is land (lakes take the land branch)'),
            'projection': ('equirectangular 2:1; +90 deg at the top row edge, -90 at the '
                           'bottom, 0 deg meridian at the centre column, seam-free in '
                           'longitude'),
            'pixel_centre': 'lon = -180 + 360*(x+0.5)/w, lat = 90 - 180*(y+0.5)/h',
            'quantization_m': round(heightmap.quantization_m, 4),
            'vertical_m': round(heightmap.vertical_m, 3),
            'radius_assumption_km': DEFAULT_RADIUS_KM,
        },
        'stats': {
            'sea_px': sea_px,
            'land_px': heightmap.pixels - sea_px,
            'sea_fraction': round(sea_px / (heightmap.pixels or 1), 6),
            'linear_fill': heightmap.linear_fill,
            'sea_level_clamped_low': heightmap.sea_clamped_low,
            'sea_level_clamped_high': heightmap.sea_clamped_high,
            'elev_min_m': round(heightmap.elev_m(min(heightmap.gray)), 1),
            'elev_max_m': round(heightmap.elev_m(max(heightmap.gray)), 1),
        },
        'derived': list(DERIVED_FIELDS),
        'missing': list(MISSING_FIELDS),
        'note_text': heightmap.note_text[:MAX_NOTE_CHARS],
        'warnings': list(heightmap.warnings),
    }
    store.put('map_import', identifier, record)
    return record


def list_imports(store):
    return sorted(store.all('map_import'),
                  key=lambda row: (row.get('created') or '', row.get('id') or ''))


def get_import(store, identifier):
    if not re.fullmatch(r'(mi|sn)_[0-9a-f]{6,32}', str(identifier or '')):
        raise MapImportError('导入编号格式不对')
    record = store.get('map_import', identifier)
    if not record:
        raise MapImportError('找不到这个地图导入')
    return record


def load_heightmap(root, record):
    """Re-read the persisted PNG (used by sampling and preview)."""
    target = import_dir(root) / record['file']
    if not target.exists():
        raise MapImportError('导入的原始文件已不在（%s），请重新导入' % record['file'])
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.get('sha256'):
        raise MapImportError('导入的原始文件校验失败（内容与记录的哈希不符）')
    return parse_heightmap(data, record.get('note_text') or '')


# ==================================================================== sampling
def _wrap_lon(lon):
    return ((lon + 180.0) % 360.0) - 180.0


def _lat_at(row, height):
    """Latitude of a row *edge*; row 0 is +90 and row ``height`` is -90."""
    return 90.0 - 180.0 * row / height


def _cell_area_km2(row, width, height, radius_km):
    """Exact spherical area of one pixel: R²·Δλ·(sin lat_north − sin lat_south).

    Used instead of "pixel count × one equatorial area", so a window that straddles
    latitudes, the dateline or a pole is still weighted correctly.
    """
    dlon = 2.0 * math.pi / width
    return (dlon * radius_km * radius_km
            * (math.sin(math.radians(_lat_at(row, height)))
               - math.sin(math.radians(_lat_at(row + 1, height)))))


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapImportError('%s 必须是数字' % name)
    if not math.isfinite(value):
        raise MapImportError('%s 不能是 NaN 或无穷' % name)
    return float(value)


def _percentile(values, share):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(share * (len(ordered) - 1)))))
    return ordered[index]


def sample_region(heightmap, lon, lat, window_px=MIN_WINDOW_PX,
                  radius_km=DEFAULT_RADIUS_KM):
    """Bounded statistics for one author-chosen point.

    Everything returned is either measured from the exported integers or explicitly marked
    as an assumption (planet radius, pixel-centre convention). The slope is a **regional**
    slope: neighbouring pixel centres are tens of kilometres apart, so it is not a
    building-site gradient and says so.
    """
    radius_km = _number(radius_km, '星体半径')
    if not 1000.0 <= radius_km <= 20000.0:
        raise MapImportError('星体半径必须在 1000…20000 km 之间')
    lon = _number(lon, '经度')
    lat = _number(lat, '纬度')
    if not -90.0 <= lat <= 90.0:
        raise MapImportError('纬度必须在 −90…90 之间')
    if abs(lat) > 89.5:
        raise MapImportError('取样点太靠近极点（|纬度| > 89.5），该处像素严重拉伸，不取样')
    if isinstance(window_px, bool) or not isinstance(window_px, int):
        raise MapImportError('窗格必须是整数')
    if window_px < MIN_WINDOW_PX or window_px > MAX_WINDOW_PX or window_px % 2 == 0:
        raise MapImportError('窗格必须是 %d…%d 之间的奇数' % (MIN_WINDOW_PX, MAX_WINDOW_PX))
    width, height, gray = heightmap.width, heightmap.height, heightmap.gray
    if window_px > width or window_px > height:
        raise MapImportError('窗格比图片还大')

    warnings = list(heightmap.warnings)
    if abs(lon) > 180.0:
        warnings.append('经度超出 ±180，已按东西无缝回绕到 %.4f°' % _wrap_lon(lon))
    lon = _wrap_lon(lon)

    cx = min(width - 1, int((lon + 180.0) / 360.0 * width))
    cy = min(height - 1, max(0, int((90.0 - lat) / 180.0 * height)))
    half = window_px // 2
    columns = []
    for step in range(-half, half + 1):
        x = (cx + step) % width
        if x not in columns:
            columns.append(x)
    rows = []
    for step in range(-half, half + 1):
        y = min(height - 1, max(0, cy + step))
        if y not in rows:                       # only collapses at the poles
            rows.append(y)

    sea_cells = {}
    land_values = []
    land_km2 = 0.0
    area_km2 = 0.0
    for y in rows:
        cell_area = _cell_area_km2(y, width, height, radius_km)
        for x in columns:
            area_km2 += cell_area
            value = gray[y * width + x]
            sea = heightmap.is_sea(value)
            sea_cells[(x, y)] = sea
            if sea:
                continue
            land_values.append(heightmap.elev_m(value))
            land_km2 += cell_area
    total = len(sea_cells)
    sea_fraction = (total - len(land_values)) / total
    if sea_fraction >= SEA_REJECT_FRACTION:
        raise MapImportError('选点在海上或紧贴海岸（窗格内海面占 %.0f%%），不能在这里建镇'
                             % (sea_fraction * 100))
    if sea_fraction > SEA_WARN_FRACTION:
        warnings.append('窗格内海面占 %.0f%%，聚落可用陆地偏少' % (sea_fraction * 100))
    if not land_values:
        raise MapImportError('窗格内没有陆地像素')
    if not 0.5 <= area_km2 <= 20000.0:
        raise MapImportError('取样窗面积 %.1f km² 超出城镇输入允许的 0.5…20000 km²，'
                             '请调小或调大窗格' % area_km2)

    lat_top = _lat_at(rows[0], height)
    lat_bottom = _lat_at(rows[-1] + 1, height)
    km_per_row = math.pi * radius_km / height

    # Regional slope: centred differences between neighbouring pixel centres, in metres per
    # metre. East-west spacing follows cos(latitude) row by row.
    slopes = []
    for y in rows:
        lat_row = (_lat_at(y, height) + _lat_at(y + 1, height)) / 2.0
        dx_m = (2.0 * math.pi * radius_km
                * max(1e-9, math.cos(math.radians(lat_row))) / width * 1000.0)
        dy_m = 2.0 * km_per_row * 1000.0
        for x in columns:
            if sea_cells[(x, y)]:
                continue
            north = (x, min(height - 1, max(0, y - 1)))
            south = (x, min(height - 1, max(0, y + 1)))
            west = ((x - 1) % width, y)
            east = ((x + 1) % width, y)
            # A neighbour can sit just outside the sampling window (the window is at most
            # 15 px wide), and a sea pixel there still means "no land slope through here".
            # So test the pixels themselves rather than looking the neighbour up in the
            # window's own sea map, which raised KeyError at the edge of a window.
            neighbours = (north, south, west, east)
            if any(heightmap.is_sea(gray[ny * width + nx]) for nx, ny in neighbours):
                continue
            if dx_m < 1.0:                      # near the poles the east-west term blows up
                continue
            dz_ns = (heightmap.elev_m(gray[north[1] * width + north[0]])
                     - heightmap.elev_m(gray[south[1] * width + south[0]]))
            dz_ew = (heightmap.elev_m(gray[east[1] * width + east[0]])
                     - heightmap.elev_m(gray[west[1] * width + west[0]]))
            slopes.append(math.degrees(math.atan(math.hypot(dz_ew / dx_m, dz_ns / dy_m))))
    if not slopes:
        raise MapImportError('窗格内没有可算坡度的相邻陆地像素，请调大窗格')

    mean_elev = sum(land_values) / len(land_values)
    if not -500.0 <= mean_elev <= 9000.0:
        raise MapImportError('窗格陆地均海拔 %.0f 米超出城镇输入允许的 −500…9000 米' % mean_elev)
    center_lat = (lat_top + lat_bottom) / 2.0
    km_per_col = (2.0 * math.pi * radius_km
                  * max(1e-6, math.cos(math.radians(center_lat))) / width)
    return {
        'lon': round(lon, 4),
        'lat': round(lat, 4),
        'window_px': window_px,
        'pixel': {'x': cx, 'y': cy, 'x0': columns[0], 'y0': rows[0],
                  'columns': len(columns), 'rows': len(rows)},
        'lat_top': round(lat_top, 4),
        'lat_bottom': round(lat_bottom, 4),
        'span_km': {'north_south': round(km_per_row * len(rows), 1),
                    'east_west': round(km_per_col * len(columns), 1),
                    'km_per_pixel': round(km_per_row, 2)},
        'elevation_m': {'min': round(min(land_values), 1), 'max': round(max(land_values), 1),
                        'mean': round(mean_elev, 1)},
        'sea_fraction': round(sea_fraction, 4),
        'land_km2': round(land_km2, 1),
        'sea_km2': round(area_km2 - land_km2, 1),
        'area_km2': round(area_km2, 1),
        'slope_deg': {'p50': round(_percentile(slopes, 0.5), 2), 'max': round(max(slopes), 2)},
        'vertical_m': round(heightmap.vertical_m, 2),
        'radius_km': round(radius_km, 4),
        'climate': None,                     # a heightmap carries no climate at all
        'derived': list(DERIVED_FIELDS),
        'missing': list(MISSING_FIELDS),
        'warnings': warnings,
    }


# ================================================================ TownInput
#: Filled in when the author leaves a social/physical field out; every key actually filled
#: is reported back in ``assumed_from_template`` so a reviewer can tell an authored choice
#: from a placeholder.
IMPORT_TEMPLATE = {
    'materials': ['timber', 'stone', 'clay_brick', 'thatch'],
    'technology': ['timber_frame', 'kiln'],
    'cultures': [{'id': 'cu_import', 'name': '本地文化（导入占位，作者待写）',
                  'roof': 'gable_thatch', 'heating': 'open_hearth',
                  'household': 'nuclear', 'note': '来自导入模板，未按本地史实核对'}],
    'peoples': [{'id': 'pe_import', 'name': '本地人', 'average_height_cm': 170,
                 'min_ceiling_m': 2.4, 'space_factor': 1.0}],
    'social_mode': 'artistic_extrapolation',
    'artistic': {'prototypes': ['作者导入的地图局部'],
                 'inventions': ['（作者尚未填写创作归纳）'],
                 'design_goal': '先用地图实测的地形起一座可玩的城镇，社会细节由作者后续补写',
                 'counterexamples': '不把导入模板当成历史结论'},
    'water': {'source': 'river', 'reliability': 0.8, 'daily_capacity_l': 200000,
              'storage': 'none', 'distance_km': 1.0},
    'freshwater': 0.6, 'soil_fertility': 0.5, 'flood_risk': 0.2,
}
_TEMPLATE_KEYS = ('materials', 'technology', 'cultures', 'peoples', 'social_mode',
                  'artistic', 'realistic', 'water', 'freshwater', 'soil_fertility',
                  'flood_risk', 'transport', 'resources', 'imports', 'bindings')


def default_seed(record_id, pixel_x, pixel_y):
    digest = hashlib.sha256(('%s:%d:%d' % (record_id, pixel_x, pixel_y)).encode('ascii'))
    return 'map_' + digest.hexdigest()[:12]


#: Fields a town genuinely cannot be built without, and which the map does not provide.
#: They must come from the author (or from an explicit "use the template" acknowledgement)
#: — the adapter will not quietly fill them and then present the result as map-derived.
REQUIRED_AUTHOR_FIELDS = ('water', 'transport', 'materials', 'technology')


def missing_author_fields(author):
    """Which required fields the caller did NOT state."""
    author = author or {}
    return [key for key in REQUIRED_AUTHOR_FIELDS if key not in author]


def build_town_input(record, sample, author, story_revision):
    """Assemble a :class:`app.town_schema.TownInput` from measured facts + author fields.

    ``climate_source`` must be stated:

    * ``measured`` — the sample came from :mod:`app.civ_atlas_snapshot` and carries per-cell
      ``temperature``/``precipitation``/``biome`` read out of the exported snapshot;
    * ``author`` — the author typed ``temperature_c`` and ``precipitation_mm`` themselves;
    * ``missing`` (the default) — refuse to build. Nothing is estimated on the author's
      behalf: a heightmap has no climate, and inventing one would look like data.
    """
    from .town_schema import TownInput

    author = dict(author or {})
    source = author.get('climate_source', 'missing')
    if source not in ('missing', 'author', 'measured'):
        raise MapImportError('climate_source 只能是 missing / author / measured')
    if source == 'missing':
        raise MapImportError(
            '这次导入的数据里没有气温和降水。要么自己填 temperature_c 与 '
            'precipitation_mm（climate_source=author），要么用 .civsnap 原件导入'
            '（climate_source=measured）。本项目不替你估算')
    if source == 'measured' and not (sample.get('climate') or {}).get('measured'):
        raise MapImportError('这次取样没有实测气候；实测气候只来自 .civsnap 原件')

    if author.get('selection') is not None:
        picked = author['selection']
        try:
            pair = (round(float(picked.get('lon')), 4), round(float(picked.get('lat')), 4))
        except (TypeError, ValueError):
            raise MapImportError('selection 的经纬度不是数字')
        if pair != (round(sample['lon'], 4), round(sample['lat'], 4)):
            raise MapImportError('选点与取样结果不一致：请先取样再生成')

    assumed = [key for key in _TEMPLATE_KEYS if key not in author and key in IMPORT_TEMPLATE]
    merged = {**IMPORT_TEMPLATE, **{k: v for k, v in author.items() if k in _TEMPLATE_KEYS}}
    # Which values the author actually stated, and which are the import template's
    # defaults. The caller (and the record) must be able to tell them apart: a template
    # default is NOT an author statement and NOT a fact about the map, so it cannot be
    # reported as "the author filled this in".
    stated = sorted(k for k in _TEMPLATE_KEYS if k in author)
    template_used = [k for k in _TEMPLATE_KEYS if k not in author and k in IMPORT_TEMPLATE]
    # Social/physical fields that must not be silently invented for a real place.
    needs_confirmation = [k for k in template_used
                          if k in ('water', 'transport', 'materials', 'technology',
                                   'cultures', 'peoples', 'resources', 'freshwater',
                                   'soil_fertility', 'flood_risk')]

    # A map does not know the town's water works, roads, building materials or craft.
    # Those must be stated by the author, or the caller must explicitly say it accepts
    # the template placeholders for a first draft. Silently substituting them and then
    # handing back a town that "has" water and trade routes would present template
    # guesses as facts about the place.
    if needs_confirmation and not author.get('confirm_template'):
        raise MapImportError(
            '还缺作者声明的水源/通路/材料/技术等：%s。请补齐后再生成，或显式传 '
            'confirm_template=true 表示“先用模板占位出一版草稿”，'
            '这样生成的字段会标成模板默认值，不会被当作地图事实'
            % '、'.join(needs_confirmation))

    if source == 'measured':
        climate = sample['climate']
        temperature = float(climate['temperature_c'])
        precipitation = float(climate['precipitation_mm'])
        biome = climate.get('biome_name')
    else:
        temperature = _number(author.get('temperature_c', None), '气温')
        precipitation = _number(author.get('precipitation_mm', None), '年降水')
        biome = None
    if not -55.0 <= temperature <= 55.0:
        raise MapImportError('气温必须在 −55…55 °C 之间')
    if not 0.0 <= precipitation <= 6000.0:
        raise MapImportError('年降水必须在 0…6000 mm 之间')

    site_name = str(author.get('site_name') or '').strip()
    region = str(author.get('region') or '').strip()
    if not site_name or not region:
        raise MapImportError('请填写地点名与所属区域')
    # 城镇腹地：
    #   · 作者画了建筑范围 → footprint 单独存放，**不进 area_km2**（那边是粮食腹地）；
    #   · 作者圈了农田/牧场 → 这些「已声明的生产用地」才是 area_km2 的来源；
    #   · 两者都没给、也没填 hinterland_km2 → 允许先存为空间草稿，
    #     但 supply 标 unconfigured，上层不得拿它当可运行城镇。
    footprint_raw = author.get('footprint')
    land_use_raw = author.get('land_use')
    supply = 'unconfigured'
    footprint = None
    land_use_summary = None
    productive_km2 = None
    if footprint_raw is not None or land_use_raw is not None:
        from . import land_footprint as land
        if footprint_raw is not None:
            vertices = footprint_raw.get('vertices') if isinstance(footprint_raw, dict) \
                else footprint_raw
            footprint = land.parse_footprint(vertices)
        entries = land.parse_land_use(land_use_raw)
        land_use_summary = land.summarize_land_use(entries)
        productive_km2 = land_use_summary['productive_declared_km2']

    raw_hinterland = author.get('hinterland_km2')
    if footprint is None and land_use_summary is None and raw_hinterland is None:
        raise MapImportError(
            '请圈出建筑范围（footprint），和/或圈出农田/矿山等用地（land_use）；'
            '不想规划也能只圈建筑范围，但那样会先保存为「供给未配置」的空间草稿')

    if raw_hinterland is not None:
        area_source_value = 'author_declared_hinterland'
        half = _number(raw_hinterland, '城镇腹地')
        if not 0.5 <= half <= 20000.0:
            raise MapImportError('城镇腹地必须在 0.5…20000 km² 之间（收到 %.2f）' % half)
        if half > float(sample['area_km2']) + 1e-9:
            raise MapImportError(
                '城镇腹地 %.1f km² 超过了本次选点覆盖的干陆地 %.1f km²；'
                '请调大窗格或调小腹地' % (half, sample['area_km2']))
        supply = 'configured'
    elif productive_km2:
        # 已声明的农田/牧场就是腹地来源；仍可能小于 GRAIN_MIN，由城镇规则自己判断
        half = float(productive_km2)
        area_source_value = 'declared_productive_land_use'
        if half > 20000.0:
            raise MapImportError(
                '已声明的生产用地 %.1f km² 超出城镇输入允许的 20000 km²；'
                '请把农田/牧场拆小一些' % half)
        supply = 'configured'
    else:
        # 只有建筑范围（或只有矿山/荒地）→ 没有任何已声明的供给。
        # **不能**把建筑面积塞进 terrain.area_km2 去过 schema：那是粮食腹地。
        # 这类情况只能存“空间草稿”（见 app/spatial_draft.py），不生成 TownInput。
        raise MapImportError(
            '还没有可用的供给：目前的建筑范围/矿山/荒地都不产出粮食。'
            '请圈出农田或牧场（land_use），或显式填 hinterland_km2，'
            '或先存成「空间草稿」——草稿不能发布成可运行城镇')

    seed = str(author.get('seed') or default_seed(record['id'], sample['pixel']['x'],
                                                  sample['pixel']['y']))
    mapping = {
        'input_version': record.get('format') or FORMAT,
        'coordinate_system': '等距圆柱全球经纬度（经度在前、纬度在后；0° 在本图中心）',
        'scale': ('取样 %d 单元 ≈ 南北 %.0f km × 东西 %.0f km（面积按半径 %.0f km 假设折算）'
                  % (sample['window_px'], sample['span_km']['north_south'],
                     sample['span_km']['east_west'], sample['radius_km'])),
        'source': 'external_adapter',
    }
    payload = {
        'story_revision': story_revision,
        'seed': seed,
        'site': 'selected_location',
        'site_name': site_name[:80],
        'site_location_id': '%s#%d,%d' % (record['id'], sample['pixel']['x'],
                                          sample['pixel']['y']),
        'region': region[:80],
        'founded_period': str(author.get('founded_period') or '未定（作者未提供时期）')[:120],
        'map': mapping,
        'terrain': {
            'elevation_m': sample['elevation_m']['mean'],
            'slope_deg': sample['slope_deg']['p50'],
            'precipitation_mm': precipitation,
            'temperature_c': temperature,
            'freshwater': merged['freshwater'],
            'soil_fertility': merged['soil_fertility'],
            'flood_risk': merged['flood_risk'],
            'area_km2': half,
            'coordinates': [sample['lon'], sample['lat']],
        },
        'water': merged['water'],
        'transport': merged.get('transport') or {
            'road': 'track', 'water_route': False, 'portage': False,
            'seasonal_closed_days': 20, 'nearest_market_days': 2},
        'resources': merged.get('resources') or [],
        'materials': merged['materials'],
        'technology': merged['technology'],
        'cultures': merged['cultures'],
        'peoples': merged['peoples'],
        'social_mode': merged['social_mode'],
        'artistic': (merged.get('artistic')
                     if merged['social_mode'] == 'artistic_extrapolation' else None),
        'realistic': (merged.get('realistic')
                      if merged['social_mode'] == 'realistic_reference' else None),
        'imports': merged.get('imports') or [],
        'bindings': merged.get('bindings') or [],
        'notes': _compose_notes(record, sample, assumed, temperature, precipitation,
                                source, biome),
    }
    warnings = list(sample.get('warnings') or [])
    # 按原件实际有没有水体来说，而不是笼统说“不含地表水”：.civsnap 的 water 数组能分
    # 陆/洋/湖，只是本工程不把它折算成“每日可供水量”。
    stats = record.get('stats') or {}
    has_lakes = (stats.get('lake_cells') or 0) > 0
    has_water_array = record.get('format') == 'civ_atlas_snapshot_v1'
    if has_water_array:
        warnings.append(
            '水源、材料、技术与文化尚未由作者确认：本次只有地点名、区域与气候被声明；'
            '其余字段取自导入模板，已列入 provenance.assumed_from_template，'
            '需要作者在城镇面板逐项核对或改写')
        warnings.append(
            '原件里有逐格水体分类（海/湖/陆）%s，但分类不等于可用水量：'
            '本工程没有把湖的存在折算成 daily_capacity_l，也没验证该点能否取水'
            % ('（该世界有 %d 个湖泊地块）' % stats['lake_cells'] if has_lakes else '（该世界没有湖泊地块）'))
    else:
        warnings.append(
            '这份导入只有高程与海陆，没有气候也没有水体分类；水源、材料、技术与文化'
            '均需作者填写，程序不代填')
    return {
        'input': TownInput(**payload),
        'provenance': {
            'format': record.get('format'),
            'import_id': record['id'],
            'source_sha256': record.get('sha256'),
            'spec_commit': SPEC_COMMIT,
            'declared_commit': (record.get('source') or {}).get('commit'),
            'seed': record.get('seed'),
            'map_seed': seed,
            'conversions': {
                'elevation_m': (record.get('units') or {}).get('elevation'),
                'lo_m': record.get('lo_m'), 'hi_m': record.get('hi_m'),
                'sea_gray': record.get('sea_gray'),
                'vertical_m': sample.get('vertical_m'),
                'radius_km': sample.get('radius_km'),
            },
            'measured': list(sample.get('derived') or []),
            'assumed_from_template': assumed,
            'author_stated': stated,
            'hinterland': {
                'km2': half,
                'source': area_source_value,
                'supply': supply,
                'sampled_dryland_km2': sample['area_km2'],
                'note': ('area_km2 是已声明的生产用地或作者填的腹地；'
                         '建筑范围不计入粮食面积；取样覆盖的真实干陆地单独保留'),
            },
            'footprint': footprint,
            'land_use': land_use_summary,
            'template_defaults': template_used,
            'needs_author_confirmation': needs_confirmation,
            'climate': source,
            'blocked': list(sample.get('blocked') or sample.get('missing') or MISSING_FIELDS),
        },
        'warnings': warnings,
    }


def _compose_notes(record, sample, assumed, temperature, precipitation, source, biome):
    if source == 'measured':
        climate = ('雨温与群系为原件实测（气温 %.1f °C、年降水 %.0f mm%s）'
                   % (temperature, precipitation, '、%s' % biome if biome else ''))
    else:
        climate = '雨温为作者填写（%.1f °C / %.0f mm），不是上游数据' % (temperature,
                                                                     precipitation)
    text = ('地形取自 civ-atlas %s（规格 %s，声明提交 %s，seed %s，sha256 %s）：'
            '海拔 %s 米，海陆按海平面灰度的整数比较判定；取样 %d 单元 ≈ %.0f×%.0f km，'
            '面积按半径 %.0f km 假设逐格球面加权；坡度是区域尺度梯度。%s。'
            '物产与势力未导入：上游的物产只有州级 0–3 储量档，不是产量也不是库存。%s'
            % (record.get('format'), SPEC_COMMIT[:8],
               (record.get('source') or {}).get('commit') or '未声明',
               record.get('seed'), (record.get('sha256') or '')[:12],
               sample['elevation_m']['mean'], sample['window_px'],
               sample['span_km']['north_south'], sample['span_km']['east_west'],
               sample['radius_km'], climate,
               '；部分社会字段取自导入模板' if assumed else ''))
    return text[:600]


# ==================================================================== preview
def preview_png(heightmap, max_width=512):
    """Downsample to an 8-bit picture for the author canvas.

    Sea and land are split with the exact integer test *before* downsampling, so the
    coastline the author clicks on matches the mask the sampler uses. This is a picture:
    elevation numbers come from :func:`sample_region`, never from these bytes.
    """
    width, height, gray = heightmap.width, heightmap.height, heightmap.gray
    step = max(1, int(math.ceil(width / float(max_width))))
    out_w = max(1, width // step)
    out_h = max(1, height // step)
    pixels = bytearray(out_w * out_h)
    for oy in range(out_h):
        base = oy * step * width
        for ox in range(out_w):
            value = gray[base + ox * step]
            if heightmap.is_sea(value):
                deep = (heightmap.sea_gray - value) / float(max(1, heightmap.sea_gray))
                pixels[oy * out_w + ox] = int(round(96 * (1.0 - min(1.0, deep * 1.3))))
            else:
                top = max(1, 65535 - heightmap.sea_gray)
                tall = min(1.0, (value - heightmap.sea_gray) / float(top) * 3.0)
                pixels[oy * out_w + ox] = 128 + int(round(127 * tall))
    info = {'width': out_w, 'height': out_h, 'step': step, 'sea_gray': heightmap.sea_gray,
            'lo_m': heightmap.lo_m, 'hi_m': heightmap.hi_m,
            'legend': 'sea 0…96 (darker is deeper), land 128…255 (brighter is higher)'}
    return encode_gray_preview(pixels, out_w, out_h), info


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
