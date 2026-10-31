# -*- coding: utf-8 -*-
"""原生宿主数据桥 + 宿主渲染的**真实行为**测试。

不是源码字符串断言，而是真的把上游 JS 跑起来：

1. `tools/dream_bridge_behavior.mjs` 用 tsx 真跑 `src/dream/bridge.ts`——切 CASNAP01、
   逐块校验、上游 `unpackValue` 解码、上游 `rasterize` 现算栅格；并用本地 fetch 桩把
   `/api/inner/native-worlds*` 的真实形状喂进去，分别验证安全上下文（有 `crypto.subtle`）
   与非安全上下文（跨机 HTTP、无 `crypto.subtle`）两条路。
2. `tools/dream_host_render.mjs` 用真浏览器（Playwright + 已装的 Chromium）加载
   构建好的 `dist-dream/dream-host.js`，用 page.route 拦截两个作者路由返回真实形状，
   验证：地图真的画出了像素、canvas 居中摆了、换原件时旧图被清掉且迟到响应不回来、
   玩家模式不请求作者路由。

真实样本（4.6 MB `.civsnap`）不在时，跑真数据的用例都 **skip 并明写未验真**。
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'external' / 'civ-atlas'
DREAM = UPSTREAM / 'src' / 'dream'
TOOLS = ROOT / 'tools'
NODE = shutil.which('node')
BUNDLE = UPSTREAM / 'dist-dream' / 'dream-host.js'
REAL = Path(r'D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0'
            r'/scratch/real-verify-data/map_imports'
            r'/2f364872015835be5a905876c6bdf5ae.civsnap')


def _tsx():
    """上游 node_modules 里的 tsx（台本 import 了 .ts 源文件，node 自己跑不了）。"""
    for name in ('tsx.cmd', 'tsx'):
        candidate = UPSTREAM / 'node_modules' / '.bin' / name
        if candidate.exists():
            return str(candidate)
    return None


def run_probe(script, *args, timeout=600, typescript=False):
    """跑一个 JS 探针脚本，把它 stdout 最后一行当 JSON 读回来。

    `typescript=True` 时用上游的 tsx 启动（台本里直接 import 了 `.ts` 源文件）。
    """
    if typescript:
        launcher = _tsx()
        if launcher is None:
            raise unittest.SkipTest('上游 node_modules 里没有 tsx（**未验真**）')
        command = [launcher]
    else:
        if NODE is None:
            raise unittest.SkipTest('未安装 node（**未验真**）')
        command = [NODE]
    result = subprocess.run(
        [*command, str(TOOLS / script), *map(str, args)],
        cwd=str(UPSTREAM), capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode != 0:
        raise AssertionError('%s 失败（exit %d）\nstderr:\n%s\nstdout:\n%s'
                             % (script, result.returncode,
                                result.stderr[-4000:], result.stdout[-3000:]))
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError('%s 没有任何输出' % script)
    return json.loads(lines[-1])


class BridgeBehaviorTests(unittest.TestCase):
    """真跑 `src/dream/bridge.ts`（上游解码 + 上游 rasterize）。"""

    @classmethod
    def setUpClass(cls):
        if not REAL.exists():
            raise unittest.SkipTest('真实 .civsnap 不在预期路径（**未验真**）')
        cls.report = run_probe('dream_bridge_behavior.mjs', REAL, typescript=True)

    # ---------------------------------------------------------- 容器与解码
    def test_container_is_split_the_same_way_as_the_python_parser(self):
        split = self.report['split']
        self.assertEqual(split['names'], ['map', 'eras', 'civ'])
        self.assertEqual(split['manifestWorldId'], 'wmvrpuwi29m3yi')
        self.assertEqual(split['manifestGenerator'], 45)
        for part in split['parts']:
            self.assertGreater(part['bytes'], 0, part['name'])
            self.assertGreater(part['length'], 0, part['name'])
            self.assertEqual(part['zip'], 'gzip', part['name'])

    def test_every_part_decodes_and_matches_the_server_side_sum(self):
        """服务端（导入时真算）的逐块 sum 与 JS 解出来的字节完全一致。"""
        declared = {p['name']: p['sum'] for p in self.report['split']['parts']}
        sizes = {p['name']: p['bytes'] for p in self.report['split']['parts']}
        for part in self.report['serverParts']:
            self.assertEqual(part['sum'], declared[part['name']], part['name'])
            self.assertEqual(part['sum_verified_by'], 'server')
            self.assertEqual(part['bytes'], sizes[part['name']], part['name'])

    def test_map_part_carries_no_raster_so_host_must_rasterize(self):
        """实测：map 块只有 mesh 与逐格数组，栅格只能现算。"""
        self.assertFalse(self.report['mapHasRasterField'])
        secure = self.report['secure']
        self.assertEqual(secure['raster'], [2048, 1024])
        self.assertEqual(secure['rasterPixels'], 2048 * 1024)
        self.assertEqual(secure['cells'], 34097)

    def test_raster_is_real_pixels_not_blank(self):
        secure = self.report['secure']
        self.assertTrue(secure['elevationFinite'], '栅格海拔里有 NaN/Infinity')
        self.assertGreater(secure['waterLand'], 0)
        self.assertLess(secure['waterLand'], 2048 * 1024, '整张图都是陆地，像是没铺成功')

    def test_civ_part_is_decoded_and_matches_the_mesh(self):
        secure = self.report['secure']
        self.assertTrue(secure['hasCiv'])
        self.assertEqual(secure['civRegions'], 870)
        self.assertEqual(secure['civEndYear'], 3000)

    # ---------------------------------------------------------- 来源身份
    def test_identity_comes_from_the_server_not_the_browser(self):
        secure = self.report['secure']
        self.assertEqual(secure['identitySha'], self.report['wholeSum'])
        self.assertEqual(len(secure['identitySha']), 64)
        self.assertEqual(secure['importId'], 'sn_2f3648720158')

    def test_can_save_requires_author_mode_and_full_server_identity(self):
        secure = self.report['secure']
        self.assertTrue(secure['canSaveAuthor'])
        self.assertFalse(secure['canSavePlayer'], '玩家模式不能拿作者原件绑草稿')
        self.assertFalse(secure['canSaveWithoutSha'], '缺 sha256 不能保存')

    def test_only_the_two_author_routes_are_called(self):
        asked = self.report['secure']['askedRoutes']
        self.assertEqual(asked, ['/api/inner/native-worlds/sn_2f3648720158',
                                 '/api/inner/native-worlds/sn_2f3648720158/snapshot'])

    # ---------------------------------------------------------- 非安全上下文
    def test_insecure_context_reads_through_the_server_witness(self):
        """跨机 HTTP（没有 crypto.subtle）时，有服务端见证也能读出同一张栅格。"""
        insecure = self.report['insecure']
        witness = insecure.get('withWitness')
        self.assertIsNotNone(witness, '非安全上下文里读不出来：%r' % insecure)
        self.assertEqual(witness['raster'], self.report['secure']['raster'])
        self.assertEqual(witness['cells'], self.report['secure']['cells'])
        self.assertTrue(witness['sameIdentity'])

    def test_missing_witness_is_refused_not_silently_downgraded(self):
        message = self.report['insecure'].get('withoutWitness') or ''
        self.assertIn('服务端逐块校验见证', message)

    def test_tampered_metadata_is_refused(self):
        insecure = self.report['insecure']
        self.assertIn('校验和与服务端记录不一致', insecure.get('wrongSum') or '')
        self.assertIn('长度与服务端记录不一致', insecure.get('wrongLength') or '')
        self.assertIn('世界编号与服务端记录不一致', insecure.get('wrongWorld') or '')


class HostRenderTests(unittest.TestCase):
    """真浏览器加载构建好的 `dream-host.js`：地图真的画得出来、摆得对。"""

    @classmethod
    def setUpClass(cls):
        if not REAL.exists():
            raise unittest.SkipTest('真实 .civsnap 不在预期路径（**未验真**）')
        if not BUNDLE.exists():
            raise unittest.SkipTest('dist-dream/dream-host.js 未构建'
                                    '（先跑 npx vite build --config vite.dream.config.ts）'
                                    '（**未验真**）')
        cls.report = run_probe('dream_host_render.mjs', REAL, BUNDLE)

    def test_bundle_boots_without_process_or_subtle_crashes(self):
        boot = self.report['boot']
        self.assertEqual(boot['errors'], [], '浏览器控制台报错：%r' % boot['errors'])

    def test_map_actually_drawn(self):
        draw = self.report['drawn']
        self.assertEqual(draw['canvasBitmap'], [2048, 1024])
        self.assertEqual(draw['canvasCss'], [draw['box'][0], draw['box'][1]])
        self.assertGreater(draw['distinctColors'], 50,
                           '画布颜色数太少，像没画上手绘风地形：%r' % draw)
        self.assertGreater(draw['opaqueRatio'], 0.99, '画布有没画到的透明像素')

    def test_box_is_centred_in_the_stage(self):
        """非 2:1 舞台上地图框必须居中（与 `mapWrap.ts` 的 boxLeft/boxTop 一致）。"""
        draw = self.report['drawn']
        left, top, sw, sh = draw['boxLeft'], draw['boxTop'], draw['stage'][0], draw['stage'][1]
        self.assertAlmostEqual(left, (sw - draw['box'][0]) / 2, delta=1)
        self.assertAlmostEqual(top, (sh - draw['box'][1]) / 2, delta=1)
        self.assertNotEqual((left, top), (0, 0),
                            '非 2:1 舞台上左上角对齐 0,0 就是错位')

    def test_switching_world_clears_the_old_picture_and_drops_late_responses(self):
        switch = self.report['switched']
        self.assertTrue(switch['clearedWhileLoading'], '换原件时旧图没被清掉')
        self.assertTrue(switch['lateResponseDropped'],
                        '迟到的旧响应把新图画掉了：%r' % switch.get('after'))
        self.assertEqual(switch['finalImportId'], 'sn_aaaaaaaaaaaa')

    def test_player_mode_never_touches_author_routes(self):
        player = self.report['player']
        self.assertEqual(player['authorRequests'], [], '玩家模式请求了作者路由')
        self.assertIn('not_ready', player['text'])


class PackagingTests(unittest.TestCase):
    """构建配置与源码镜像（这几项本来就是配置事实，不是算法行为）。"""

    def test_lib_entry_points_at_the_real_file(self):
        config = (UPSTREAM / 'vite.dream.config.ts').read_text(encoding='utf-8')
        self.assertIn("entry: 'src/dream/entry.tsx'", config)
        self.assertTrue((DREAM / 'entry.tsx').exists())

    def test_root_config_is_an_equivalent_copy(self):
        """仓库根那份也必须能把同一入口构建出来（只差路径基准）。"""
        root_config = (ROOT / 'vite.dream.config.ts').read_text(encoding='utf-8')
        self.assertIn("entry: 'src/dream/entry.tsx'", root_config)
        self.assertIn("root: UPSTREAM", root_config)
        for marker in ("'process.env.NODE_ENV'", "formats: ['es']", "fileName: () => 'dream-host.js'",
                       "target: 'es2022'"):
            self.assertIn(marker, root_config, '根目录配置与上游那份不一致：%s' % marker)
            self.assertIn(marker, (UPSTREAM / 'vite.dream.config.ts').read_text(encoding='utf-8'),
                          '上游那份配置缺 %s' % marker)

    def test_worker_chunk_path_carries_the_static_prefix(self):
        """worker 必须从 `/native-map/assets/…` 加载。

        产物的静态挂载点是 `/native-map`；vite 默认会把 worker 算成站点根的
        `/assets/worker-….js`，那条路径没挂 → worker 404 → 生成直接失败（实测过）。
        所以两份配置都必须写 `base: '/native-map/'`。
        """
        if not BUNDLE.exists():
            raise unittest.SkipTest('dist-dream/dream-host.js 未构建（**未验真**）')
        text = BUNDLE.read_text(encoding='utf-8')
        self.assertIn('/native-map/assets/', text, '构建产物里的 worker 路径缺少 /native-map/ 前缀')
        for name in ('vite.dream.config.ts',):
            self.assertIn("base: '/native-map/'",
                          (UPSTREAM / name).read_text(encoding='utf-8'), name)
        self.assertIn("base: '/native-map/'",
                      (ROOT / 'vite.dream.config.ts').read_text(encoding='utf-8'),
                      '仓库根那份配置也要写同一个 base')

    def test_upload_does_not_send_a_strict_query_int(self):
        """`generator_version` 是后端的 strict int query，字符串形式必 422。

        版本号本来就在容器清单的 `snapshot.generator` 里，客户端不该传这个 query。
        """
        bridge = (DREAM / 'bridge.ts').read_text(encoding='utf-8')
        self.assertNotIn("query.set('generator_version'", bridge)
        self.assertIn('不传 `generator_version`', bridge)

    def test_author_player_modes_are_separated_in_the_entry(self):
        """主入口必须按模式挂卸，玩家模式不许留在作者宿主上。"""
        entry = (ROOT / 'app' / 'static' / 'native-map.js').read_text(encoding='utf-8')
        self.assertIn('unmount()', entry)
        self.assertIn("next !== 'author'", entry)
        self.assertIn('player-map-host', entry, '玩家地图已有独立宿主，不再使用未接入占位')
        self.assertNotIn("mode: 'player'", entry, '玩家模式不该挂载作者宿主')
        app = (ROOT / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("setNativeMode('player')", app, 'loadSession 必须切到玩家模式')
        self.assertIn("setNativeMode('author')", app, '空态必须切到作者模式')

    def test_production_config_is_untouched(self):
        config = (UPSTREAM / 'vite.config.ts').read_text(encoding='utf-8')
        self.assertNotIn('dream-host', config, '独立构建不应影响现有生产构建')

    def test_dream_sources_are_mirrored_in_the_patch_directory(self):
        """`docs/civ-atlas-patch/files/` 必须是当前源码的逐字节副本。"""
        mirror = ROOT / 'docs' / 'civ-atlas-patch' / 'files'
        for name in ('bridge.ts', 'generate.ts', 'host.tsx', 'entry.tsx',
                     'landOverlay.tsx', 'landOverlay.css', 'WorldMapCanvas.tsx',
                     'WorldGenerationForm.tsx', 'useNativeWorlds.ts', 'parameters.ts',
                       'hostApi.ts', 'host.module.css', 'mapPicking.ts'):
            target = mirror / 'src' / 'dream' / name
            self.assertTrue(target.exists(), '镜像缺 %s' % name)
            self.assertEqual(target.read_bytes(), (DREAM / name).read_bytes(),
                             '镜像与源码不一致：%s' % name)
        self.assertTrue((mirror / 'vite.dream.config.ts').exists(),
                        '镜像缺 vite.dream.config.ts')
        for relative in ('src/main.tsx', 'src/ui/App.tsx', 'src/ui/appLocation.ts',
                         'src/ui/ErrorBoundary.tsx', 'src/ui/ErrorBoundary.module.css',
                         'tests/dream-frontend.test.ts'):
            self.assertEqual((mirror / relative).read_bytes(), (UPSTREAM / relative).read_bytes(), relative)


if __name__ == '__main__':
    unittest.main()
