"""app/map_source/cache.py: 结果缓存只复用成功加载，并用目录快照判断产品是否还是当前的那个。

夹具是一个小的 terragenesis-fast-relief-v1 目录产品（与真实 fast 世界层同布局：
manifest.json + layers/*.npy + 一个过程子目录），用于验证缓存命中/失效语义，不验证算法。
"""
import gc
import hashlib
import json
import os
import threading
from pathlib import Path

import numpy as np
import pytest

from app import play_map_world as pmw
from app.map_source import load_source
from app.map_source.cache import ProductCache, UncacheableProduct, directory_snapshot, is_link_path
from app.terrain_source import TerrainSourceError

SCHEMA = 'terragenesis-fast-relief-v1'
SPACING = 2000.0
NZ, NX = 4, 5


@pytest.fixture(autouse=True)
def _clean_cache():
    """缓存是模块全局的：每个用例前后都显式清空，用例之间不互相污染。"""
    pmw.clear_source_cache()
    yield
    pmw.clear_source_cache()


def _seal(manifest):
    payload = json.dumps({k: v for k, v in manifest.items() if k not in ('identity', 'source_path')},
                         sort_keys=True, separators=(',', ':'), allow_nan=False)
    manifest['identity'] = hashlib.sha256(payload.encode()).hexdigest()
    return manifest['identity']


def _write_bytes(path, data):
    """写文件并显式推进 mtime：粗时间戳文件系统上瞬时改写可能落在同一刻度。"""
    path.write_bytes(data)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


def build_product(root, name='web-test', seed=20261020, elevation=None):
    """在 ``<root>/artifacts/fast-world/<name>`` 构造一个可加载的冻结产品。"""
    product = Path(root) / 'artifacts' / 'fast-world' / name
    (product / 'layers').mkdir(parents=True, exist_ok=True)
    (product / 'world-processes').mkdir(exist_ok=True)
    bed = np.arange(NZ * NX, dtype=np.float32).reshape(NZ, NX) * 10.0 if elevation is None else elevation
    status = np.full((NZ, NX), 5, np.uint8)
    status[0, 0] = 3
    arrays = {'elevation_m': bed, 'status': status}
    layers = {}
    for layer, array in arrays.items():
        relative = 'layers/' + layer + '.npy'
        np.save(product / relative, array)
        layers[layer] = dict(file=relative, sha256=hashlib.sha256((product / relative).read_bytes()).hexdigest(),
                             dtype=str(array.dtype), unit='1' if layer == 'status' else 'm',
                             meaning='test bed' if layer == 'elevation_m' else 'test', nodata=None)
    _write_bytes(product / 'world-processes' / 'manifest.json', '{"note":"过程子目录里的旁证文件"}'.encode('utf-8'))
    manifest = {
        'schema': SCHEMA, 'world_seed': seed, 'producer': 'test', 'algorithm_version': '1',
        'lineage': [], 'subseed_method': 'test', 'subseeds': {'test': 19}, 'ready': True,
        'declared_generated': ['test surface'], 'limitations': ['test only'],
        'grid': {'first_sample_xz_m': [0, 0], 'spacing_m': SPACING, 'shape_zx': [NZ, NX],
                 'semantics': 'cell-centre', 'axes': 'X east, Z south; arrays [z,x]',
                 'length_unit': 'm', 'sea_level_m': 0},
        'layers': layers, 'vectors': {},
        'files': {spec['file']: spec['sha256'] for spec in layers.values()},
    }
    _seal(manifest)
    (product / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return product, manifest


def link_for(product, identity, spacing=SPACING):
    return dict(kind=pmw.KIND, product_path=str(product.relative_to(product.parents[2])).replace('\\', '/'),
                product_identity=identity, spacing_m=spacing, reveal_radius_km=100)


def counting_loads(monkeypatch):
    """统计真正走进 ``load_source`` 的次数（缓存命中时它一次也不该被调到）。"""
    calls = []
    real = pmw.load_source

    def wrapper(kind, path, *, expected_identity=None, **kwargs):
        calls.append((kind, str(path), expected_identity))
        return real(kind, path, expected_identity=expected_identity, **kwargs)

    monkeypatch.setattr(pmw, 'load_source', wrapper)
    return calls


# ------------------------------------------------------------------ 命中

def test_first_load_hits_loader_once_then_reuses_same_source(tmp_path, monkeypatch):
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)

    first, first_path = pmw.resolve_product(tmp_path, link)
    second, second_path = pmw.resolve_product(tmp_path, link)
    third, _ = pmw.resolve_product(tmp_path, link)

    assert len(calls) == 1, calls
    assert first is second is third and first_path == second_path == product
    assert first.info.identity == manifest['identity'] and first.info.spacing_m == SPACING
    # 缓存给的是只读数组，多次读取不会互相污染
    assert first.sample(0.0, 0.0)['status'] == 3
    assert np.allclose(second.sample(0.0, 0.0)['elevation_m'], 0.0)


def test_hit_survives_unlisted_file_content_change(tmp_path, monkeypatch):
    """过程子目录里的文件不在 manifest 哈希表里：改它不影响产品有效性，但必须让缓存失效。"""
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 1

    before = directory_snapshot(product)
    _write_bytes(product / 'world-processes' / 'manifest.json', '{"note":"换了一份旁证"}'.encode('utf-8'))
    assert directory_snapshot(product) != before
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 2


# ------------------------------------------------------------------ 失效

def test_file_stat_change_invalidates_entry_and_reloads(tmp_path, monkeypatch):
    """真实路径：只推进一个文件的 mtime（不改内容）也必须让缓存失效并重新加载。"""
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    first, _ = pmw.resolve_product(tmp_path, link)
    assert len(calls) == 1

    manifest_path = product / 'manifest.json'
    stat = manifest_path.stat()
    os.utime(manifest_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    second, _ = pmw.resolve_product(tmp_path, link)
    assert len(calls) == 2, '文件 stat 变了却还命中了旧条目'
    assert second.info.identity == first.info.identity == manifest['identity']


def test_added_file_or_folder_invalidates_entry(tmp_path, monkeypatch):
    """产品目录里多出一个文件/目录（都不在 manifest 哈希表里）也算变化。"""
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    pmw.resolve_product(tmp_path, link)

    (product / 'layers' / 'empty-extra').mkdir()
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 2

    _write_bytes(product / 'world-processes' / 'stray.txt', b'x')
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 3


def test_tampered_or_deleted_layer_drops_entry_and_load_refuses(tmp_path):
    """篡改/删除图层：缓存条目必须丢掉，重新加载仍按哈希拒绝（默认全量校验不变）。

    真实 source 持有 mmap（Windows 上会锁住对应文件），所以先释放旧 source 再改盘上文件——
    这也是产品只能整目录换版、不能就地改写的原因。
    """
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    first, _ = pmw.resolve_product(tmp_path, link)
    assert first.info.identity == manifest['identity']
    del first
    gc.collect()
    pmw.clear_source_cache()

    np.save(product / 'layers' / 'elevation_m.npy', np.full((NZ, NX), 7.0, np.float32))
    with pytest.raises(TerrainSourceError, match='hash'):
        pmw.resolve_product(tmp_path, link)

    # 删除图层文件：同样不会被旧条目掩盖
    (product / 'layers' / 'status.npy').unlink(missing_ok=True)
    with pytest.raises(TerrainSourceError):
        pmw.resolve_product(tmp_path, link)


def test_stale_entry_is_dropped_even_when_reload_would_fail(tmp_path):
    """缓存不看内容只看快照：快照变了就先丢掉旧条目，失败由 loader 自己报。"""
    product, manifest = build_product(tmp_path)
    seen = []

    def loader(kind, path, *, expected_identity=None):
        seen.append(Path(path).name)
        return 'loaded'

    cache = ProductCache(4)
    key = dict(kind='world-map-product', expected_identity=manifest['identity'])
    assert cache.load(product, loader=loader, **key) == 'loaded'
    assert len(cache) == 1

    (product / 'layers' / 'gone.txt').write_text('x', encoding='utf-8')
    assert cache.load(product, loader=loader, **key) == 'loaded'
    assert seen == ['web-test', 'web-test']
    assert len(cache) == 1, '新快照应当重新入缓存'

    (product / 'layers' / 'gone.txt').unlink()
    assert cache.load(product, loader=loader, **key) == 'loaded'
    assert seen == ['web-test'] * 3


def test_cached_source_paints_identical_png_bytes(tmp_path):
    """命中缓存拿到的 source 与一次全新 ``load_source`` 画出的 PNG 字节必须一致。"""
    from app import play_map
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    places = [{'lon': 4000.0, 'lat': 2000.0, 'radius_km': 6.0, 'state': 'current'}]

    def dimensions(box):
        return 64, 48

    def paint(source):
        return pmw.basemap_png(source, places, link, cache={}, cache_put=lambda key, value: None,
                               crop_dimensions=dimensions)

    play_map.clear_cache()
    cached_source, _ = pmw.resolve_product(tmp_path, link)
    hot = paint(cached_source)
    cold_source = load_source('world-map-product', product, expected_identity=manifest['identity'])
    cold = paint(cold_source)
    assert hot is not None and hot == cold, '缓存命中与完全重新加载的底图像素必须逐字节相等'
    del cached_source, cold_source


def test_manifest_rewrite_invalidates_entry(tmp_path, monkeypatch):
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    pmw.resolve_product(tmp_path, link)

    manifest['limitations'] = ['test only', '重写一行']
    _seal(manifest)
    _write_bytes(product / 'manifest.json', json.dumps(manifest).encode())
    pmw.resolve_product(tmp_path, link_for(product, manifest['identity']))
    assert len(calls) == 2


# ------------------------------------------------------------------ 失败 / 身份

def test_failure_is_not_cached_and_identity_still_enforced(tmp_path, monkeypatch):
    product, manifest = build_product(tmp_path)
    calls = counting_loads(monkeypatch)
    wrong = link_for(product, 'f' * 64)
    with pytest.raises(TerrainSourceError, match='identity'):
        pmw.resolve_product(tmp_path, wrong)
    assert len(calls) == 1
    # 失败没被记住：修好身份后马上就能加载（且没有多余的旧失败条目）
    source, _ = pmw.resolve_product(tmp_path, link_for(product, manifest['identity']))
    assert source.info.identity == manifest['identity']
    assert len(calls) == 2
    # 错身份再来一次仍然报错，而不是拿到别人的结果
    with pytest.raises(TerrainSourceError, match='identity'):
        pmw.resolve_product(tmp_path, wrong)
    assert len(calls) == 3


def test_same_path_different_identity_are_separate_entries(tmp_path):
    product, manifest = build_product(tmp_path)
    seen = []

    def loader(kind, path, *, expected_identity=None):
        seen.append(expected_identity)
        return ('product', str(path), expected_identity)

    cache = ProductCache(4)
    a = cache.load(product, kind='world-map-product', expected_identity=manifest['identity'], loader=loader)
    b = cache.load(product, kind='world-map-product', expected_identity=manifest['identity'], loader=loader)
    c = cache.load(product, kind='world-map-product', expected_identity='a' * 64, loader=loader)
    d = cache.load(product, kind='world-relief-pilot', expected_identity=manifest['identity'], loader=loader)
    assert a is b and a is not c and a is not d
    assert seen == [manifest['identity'], 'a' * 64, manifest['identity']]
    assert len(cache) == 3


def test_spacing_and_path_checks_are_unchanged(tmp_path):
    product, manifest = build_product(tmp_path)
    with pytest.raises(ValueError, match='spacing_m'):
        pmw.resolve_product(tmp_path, link_for(product, manifest['identity'], spacing=SPACING * 2))
    outside = tmp_path / 'elsewhere' / 'product'
    with pytest.raises(ValueError, match='artifacts'):
        pmw.resolve_product(tmp_path, dict(kind=pmw.KIND, product_path='elsewhere/product',
                                           product_identity=manifest['identity'], spacing_m=None))
    with pytest.raises(FileNotFoundError):
        pmw.resolve_product(tmp_path, dict(kind=pmw.KIND, product_path='artifacts/fast-world/none',
                                           product_identity=manifest['identity'], spacing_m=None))
    assert not outside.exists()


# ------------------------------------------------------------------ 容量 / 并发 / 不缓存的情形

def test_capacity_is_bounded_and_evicts_least_recently_used(tmp_path):
    dirs = []
    for index in range(3):
        product, _ = build_product(tmp_path, name='p%d' % index)
        dirs.append(product)
    seen = []

    def loader(kind, path, *, expected_identity=None):
        seen.append(Path(path).name)
        return seen[-1]

    cache = ProductCache(2)
    assert cache.capacity == 2
    for product in dirs:
        cache.load(product, kind='world-map-product', expected_identity='a' * 64, loader=loader)
    assert len(cache) == 2, '容量必须封顶'
    assert seen == ['p0', 'p1', 'p2']
    # p1 仍在（最近用过），p0 被淘汰 → 再访问 p0 重新加载
    cache.load(dirs[1], kind='world-map-product', expected_identity='a' * 64, loader=loader)
    assert seen == ['p0', 'p1', 'p2']
    cache.load(dirs[0], kind='world-map-product', expected_identity='a' * 64, loader=loader)
    assert seen == ['p0', 'p1', 'p2', 'p0']


def test_load_that_changes_the_directory_is_not_cached(tmp_path):
    product, manifest = build_product(tmp_path)
    counter = []

    def loader(kind, path, *, expected_identity=None):
        counter.append(1)
        # 加载过程中产品目录被改写：这份结果不能被当成当前产品
        _write_bytes(Path(path) / ('scratch-%d.txt' % len(counter)), b'x')
        return 'loaded-%d' % len(counter)

    cache = ProductCache(4)
    a = cache.load(product, kind='world-map-product', expected_identity=manifest['identity'], loader=loader)
    b = cache.load(product, kind='world-map-product', expected_identity=manifest['identity'], loader=loader)
    assert (a, b) == ('loaded-1', 'loaded-2')
    assert len(cache) == 0 and cache.unstable == 2


def test_single_file_product_bypasses_cache(tmp_path):
    archive = tmp_path / 'product.npz'
    archive.write_bytes(b'not a real product')
    seen = []

    def loader(kind, path, *, expected_identity=None):
        seen.append(str(path))
        return 'npz'

    cache = ProductCache(4)
    assert cache.load(archive, kind='world-map-product', expected_identity=None, loader=loader) == 'npz'
    assert cache.load(archive, kind='world-map-product', expected_identity=None, loader=loader) == 'npz'
    assert len(seen) == 2 and len(cache) == 0


def _make_dir_link(target, link):
    """造一个目录链接：优先 symlink，无权限时退到 Windows junction（同属 reparse point）。"""
    import subprocess
    try:
        os.symlink(target, link, target_is_directory=True)
        return 'symlink'
    except (OSError, NotImplementedError):
        pass
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                             capture_output=True, text=True)
    return 'junction' if created.returncode == 0 else None


def test_symlink_anywhere_below_product_bypasses_cache(tmp_path, monkeypatch):
    """产品目录里任何一层出现链接：不缓存（lstat 看不到链接指向的内容，快照不完整）。

    链接本身能被创建时才做真实链接；两者都造不出来就跳过。
    """
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    outside = tmp_path / 'outside-target'
    outside.mkdir()
    if _make_dir_link(outside, product / 'layers' / 'linked') is None:
        pytest.skip('此环境无法创建 symlink 或 junction')

    assert is_link_path(product) is False
    with pytest.raises(UncacheableProduct, match='link'):
        directory_snapshot(product)

    calls = counting_loads(monkeypatch)
    pmw.resolve_product(tmp_path, link)
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 2, '含链接的产品不得被缓存'


def test_linked_product_root_bypasses_cache(tmp_path):
    """产品根目录本身就是链接：即便不看内部，也必须绕过缓存。"""
    product, manifest = build_product(tmp_path)
    linked_root = tmp_path / 'artifacts' / 'fast-world' / 'via-link'
    if _make_dir_link(product, linked_root) is None:
        pytest.skip('此环境无法创建 symlink 或 junction')

    assert is_link_path(linked_root) is True
    seen = []

    def loader(kind, path, *, expected_identity=None):
        seen.append(str(path))
        return 'loaded'

    cache = ProductCache(4)
    key = dict(kind='world-map-product', expected_identity=manifest['identity'])
    cache.load(linked_root, loader=loader, **key)
    cache.load(linked_root, loader=loader, **key)
    assert len(seen) == 2 and len(cache) == 0

    # 同一产品的真实路径本身没链接，仍然可缓存（绕过只针对链接那一条路径）
    cache.load(product, loader=loader, **key)
    cache.load(product, loader=loader, **key)
    assert len(seen) == 3 and len(cache) == 1


def test_real_windows_junction_bypasses_cache(tmp_path):
    """真实的 Windows junction 必须当成链接：``os.path.islink`` 对它返回 False，只查 symlink 会漏。"""
    import subprocess

    product, manifest = build_product(tmp_path)
    target = tmp_path / 'junction-target'
    target.mkdir()
    junction = product / 'layers' / 'via-junction'
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)],
                             capture_output=True, text=True)
    if created.returncode != 0:
        pytest.skip('此环境不允许创建 junction：%s' % created.stdout.strip())

    # 前提：islink 看不见它，所以必须靠 isjunction 才能识别
    assert os.path.islink(junction) is False
    assert os.path.isjunction(junction) is True
    assert is_link_path(junction) is True
    with pytest.raises(UncacheableProduct, match='link'):
        directory_snapshot(product)

    cache = ProductCache(4)
    seen = []
    for _ in range(2):
        cache.load(product, kind='world-map-product', expected_identity=manifest['identity'],
                   loader=lambda kind, path, *, expected_identity=None: seen.append(path) or 'loaded')
    assert len(seen) == 2 and len(cache) == 0

    os.rmdir(junction)


def test_junction_is_treated_as_a_link(tmp_path, monkeypatch):
    """Windows junction（reparse point）同样算链接，即使环境造不出来也把分支掩住。"""
    import app.map_source.cache as cache_mod

    product, manifest = build_product(tmp_path)
    real_scandir = os.scandir

    class FakeEntry:
        def __init__(self, entry, junction):
            self._entry, self._junction = entry, junction
            self.name, self.path = entry.name, entry.path

        def is_symlink(self):
            return self._junction

        def is_junction(self):
            return self._junction

        def is_dir(self, follow_symlinks=True):
            return self._entry.is_dir(follow_symlinks=follow_symlinks)

        def stat(self, follow_symlinks=True):
            return self._entry.stat(follow_symlinks=follow_symlinks)

    def fake_scandir(path):
        # 与 os.scandir 一样支持 with：返回一个可关闭的迭代器
        real = real_scandir(path)
        entries = [FakeEntry(entry, entry.name == 'world-processes') for entry in real]
        real.close()

        class _Scan:
            def __enter__(self):
                return iter(entries)

            def __exit__(self, *exc):
                return False

        return _Scan()

    monkeypatch.setattr(cache_mod.os, 'scandir', fake_scandir)
    with pytest.raises(UncacheableProduct, match='link'):
        directory_snapshot(product)

    seen = []
    cache = ProductCache(4)
    for _ in range(2):
        cache.load(product, kind='world-map-product', expected_identity=manifest['identity'],
                   loader=lambda kind, path, *, expected_identity=None: seen.append(path) or 'loaded')
    assert len(seen) == 2 and len(cache) == 0 and cache.uncacheable == 2


def test_snapshot_still_records_empty_directories(tmp_path):
    """不含链接时快照正常：新增空目录仍能失效（与链接检测互不干扰）。"""
    product, _ = build_product(tmp_path)
    before = directory_snapshot(product)
    (product / 'layers' / 'empty-new').mkdir()
    after = directory_snapshot(product)
    assert after != before
    assert any(name.endswith('empty-new') for name in after[1])


def test_clear_source_cache_drops_entries(tmp_path, monkeypatch):
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    pmw.resolve_product(tmp_path, link)
    pmw.clear_source_cache()
    pmw.resolve_product(tmp_path, link)
    assert len(calls) == 2


def test_concurrent_requests_share_one_cached_source(tmp_path, monkeypatch):
    product, manifest = build_product(tmp_path)
    link = link_for(product, manifest['identity'])
    calls = counting_loads(monkeypatch)
    warm, _ = pmw.resolve_product(tmp_path, link)

    results, errors = [], []
    start = threading.Barrier(8)

    def worker():
        try:
            start.wait(timeout=10)
            results.append(pmw.resolve_product(tmp_path, link)[0])
        except BaseException as error:  # noqa: BLE001 - 报回主线程断言
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, errors
    assert len(results) == 8 and all(source is warm for source in results)
    assert len(calls) == 1


def test_registry_load_source_still_hashes_every_time(tmp_path):
    """缓存只活在 resolve_product 里：直接调 registry.load_source 仍逐次全量校验。"""
    product, manifest = build_product(tmp_path)
    assert load_source('world-map-product', product, expected_identity=manifest['identity']).info.identity == manifest['identity']
    np.save(product / 'layers' / 'status.npy', np.zeros((NZ, NX), np.uint8))
    with pytest.raises(TerrainSourceError, match='hash'):
        load_source('world-map-product', product, expected_identity=manifest['identity'])
