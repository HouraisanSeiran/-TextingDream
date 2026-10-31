# -*- coding: utf-8 -*-
"""一键安装/启动/停止的单元测试。

原则：**不真的联网、不改系统、不装依赖**。所有外部动作都换成假函数或临时目录，
所以这些测试可以在任何离线机器上重复跑。真实回环 readiness 只用一个本机
``http.server`` 线程验证，跑完就关。
"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

from launcher import core  # noqa: E402


class TempRootCase(unittest.TestCase):
    """把 core 的路径常量重定向到临时目录，避免碰真实 .venv / logs / external。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.saved = {}
        for name in ('ROOT', 'STATE_DIR', 'STATE_FILE', 'LOG_DIR', 'VENV_DIR',
                     'REQUIREMENTS', 'LAUNCH_SCRIPT', 'CIV_ATLAS_DIR', 'CIV_ATLAS_PATCH'):
            self.saved[name] = getattr(core, name)
        core.ROOT = self.root
        core.STATE_DIR = self.root / 'logs'
        core.STATE_FILE = core.STATE_DIR / 'launcher-state.json'
        core.LOG_DIR = core.STATE_DIR
        core.VENV_DIR = self.root / '.venv'
        core.REQUIREMENTS = self.root / 'requirements.txt'
        core.LAUNCH_SCRIPT = self.root / 'launch.py'
        core.CIV_ATLAS_DIR = self.root / 'external' / 'civ-atlas'
        core.CIV_ATLAS_PATCH = self.root / 'patch'
        core.REQUIREMENTS.write_text('fastapi>=0.115\n', encoding='utf-8')
        core.LAUNCH_SCRIPT.write_text('# stub\n', encoding='utf-8')
        # 每个测试后把被替换掉的标准库入口复原，避免互相污染（改过 urlopen 的测试
        # 一旦泄漏，后面的就绪判定就会假装有服务）。
        self._urlopen = core.urllib.request.urlopen
        self._copyfileobj = core.shutil.copyfileobj
        self._run = subprocess.run
        self._port_reachable = core.port_reachable
        # wait_ready 也会被个别测试替换成固定值（重复启动那条），必须一起复原，
        # 否则后面的「连不上就不是就绪」会读到 True。
        self._wait_ready = core.wait_ready

    def tearDown(self):
        core.urllib.request.urlopen = self._urlopen
        core.shutil.copyfileobj = self._copyfileobj
        core.subprocess.run = self._run
        core.port_reachable = self._port_reachable
        core.wait_ready = self._wait_ready
        for name, value in self.saved.items():
            setattr(core, name, value)


class FrontendPatchTests(TempRootCase):
    def test_nested_frontend_dependencies_are_installed(self):
        files = {'src/dream/host.tsx': 'host', 'src/ui/ErrorBoundary.tsx': 'boundary',
                 'src/ui/ErrorBoundary.module.css': 'style', 'tests/frontend.test.ts': 'test'}
        for name, content in files.items():
            path = core.CIV_ATLAS_PATCH / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        existing = core.CIV_ATLAS_DIR / 'src/gen/world.ts'
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text('unchanged', encoding='utf-8')
        core.apply_patch()
        for name, content in files.items():
            self.assertEqual((core.CIV_ATLAS_DIR / name).read_text(encoding='utf-8'), content)
        self.assertEqual(existing.read_text(encoding='utf-8'), 'unchanged')


class PythonDetectionTests(TempRootCase):
    def test_old_python_is_refused(self):
        # 一个「说得出版本但算不出来」的假解释器：模拟 Windows 商店占位。
        fake = self.root / 'python.exe'
        fake.write_text('@echo off\nexit /b 9009\n', encoding='utf-8')
        self.assertIsNone(core.python_version_ok(fake))

    def test_missing_python_gives_actionable_error(self):
        core.find_base_python = lambda: (None, None)
        code = core.main(['install', '--dry-run'])
        self.assertEqual(code, 1)

    def test_store_stub_style_failure_is_detected(self):
        # 返回非零退出码的解释器一律不认（商店占位就是这个表现：说得出版本、做不了事）。
        fake = self.root / 'stub.py'
        fake.write_text('raise SystemExit(1)\n', encoding='utf-8')
        self.assertIsNone(core.python_version_ok(fake))

    def test_unparseable_output_is_refused(self):
        fake = self.root / 'noisy.py'
        fake.write_text('print("not a version")\n', encoding='utf-8')
        self.assertIsNone(core.python_version_ok(fake))


class PathWithSpacesTests(TempRootCase):
    def test_state_files_work_under_chinese_space_path(self):
        odd = self.root / '中文 目录 with space' / 'logs'
        core.STATE_DIR = odd
        core.STATE_FILE = odd / 'launcher-state.json'
        core.write_state({'pid': 1, 'url': 'http://127.0.0.1:1'})
        self.assertTrue(core.STATE_FILE.exists())
        self.assertEqual(core.read_state()['pid'], 1)
        core.clear_state()
        self.assertEqual(core.read_state(), {})


class PortTests(TempRootCase):
    def test_free_port_is_used(self):
        port = core.pick_port(0)
        self.assertGreater(port, 0)

    def test_busy_port_falls_back_without_killing(self):
        import socket
        holder = socket.socket()
        holder.bind(('127.0.0.1', 0))
        holder.listen(1)
        busy = holder.getsockname()[1]
        try:
            self.assertFalse(core.port_free(busy))
            chosen = core.pick_port(busy)
            self.assertNotEqual(chosen, busy)
            # 占用者还在：没有为了拿端口去杀别人
            self.assertFalse(core.port_free(busy))
        finally:
            holder.close()


class ProcessIdentityTests(TempRootCase):
    """停止只停「自己启动的那个」：PID 存活 + 命令行指向本项目 + 创建时间一致。"""

    def test_stop_refuses_unknown_identity(self):
        core.process_alive = lambda pid: True
        core.process_info = lambda pid: {'command': 'C:\\other\\thing.exe --serve',
                                         'created': '2026-01-01T00:00:00'}
        killed = {'n': 0}
        core.terminate = lambda pid: killed.__setitem__('n', killed['n'] + 1) or True
        core.write_state({'pid': 4244, 'url': 'http://127.0.0.1:1',
                          'created': '2026-01-01T00:00:00',
                          'command': 'something else entirely'})
        with self.assertRaises(core.LauncherError):
            core.stop(dry_run=False)
        self.assertEqual(killed['n'], 0, '身份不符时绝不能杀进程')

    def test_stop_refuses_when_creation_time_differs(self):
        # PID 复用的典型场景：命令行碰巧含本项目路径，但创建时间对不上。
        core.process_alive = lambda pid: True
        core.process_info = lambda pid: {'command': str(core.LAUNCH_SCRIPT),
                                         'created': '2030-12-31T23:59:59'}
        killed = {'n': 0}
        core.terminate = lambda pid: killed.__setitem__('n', killed['n'] + 1) or True
        core.write_state({'pid': 4245, 'url': 'http://127.0.0.1:1',
                          'created': '2026-01-01T00:00:00',
                          'command': str(core.LAUNCH_SCRIPT)})
        with self.assertRaises(core.LauncherError):
            core.stop(dry_run=False)
        self.assertEqual(killed['n'], 0, '创建时间不符时不能杀进程')

    def test_stop_without_state_is_noop(self):
        self.assertEqual(core.stop(dry_run=True), 0)

    def test_stop_clears_dead_pid(self):
        core.process_alive = lambda pid: False
        core.write_state({'pid': 999999, 'url': 'http://127.0.0.1:1',
                          'command': str(core.LAUNCH_SCRIPT)})
        self.assertEqual(core.stop(dry_run=False), 0)
        self.assertEqual(core.read_state(), {})

    def test_stop_kills_matching_process(self):
        killed = {'pid': None}
        core.process_alive = lambda pid: True
        core.process_info = lambda pid: {'command': str(core.LAUNCH_SCRIPT) + ' -X utf8',
                                         'created': '2026-01-01T00:00:00'}
        core.terminate = lambda pid: killed.__setitem__('pid', pid) or True
        core.write_state({'pid': 4243, 'url': 'http://127.0.0.1:1',
                          'created': '2026-01-01T00:00:00',
                          'command': str(core.LAUNCH_SCRIPT)})
        self.assertEqual(core.stop(dry_run=False), 0)
        self.assertEqual(killed['pid'], 4243)
        self.assertEqual(core.read_state(), {})

    def test_failed_terminate_keeps_state_and_reports_failure(self):
        """停不掉就别清状态、别报成功。"""
        core.process_alive = lambda pid: True
        core.process_info = lambda pid: {'command': str(core.LAUNCH_SCRIPT),
                                         'created': '2026-01-01T00:00:00'}
        core.terminate = lambda pid: False
        core.write_state({'pid': 4246, 'url': 'http://127.0.0.1:1',
                          'created': '2026-01-01T00:00:00',
                          'command': str(core.LAUNCH_SCRIPT)})
        with self.assertRaises(core.LauncherError):
            core.stop(dry_run=False)
        self.assertEqual(core.read_state()['pid'], 4246, '状态必须保留以便重试')


class DuplicateStartTests(TempRootCase):
    def test_second_start_reuses_ready_service(self):
        core.write_state({'pid': os.getpid(), 'url': 'http://127.0.0.1:65500',
                          'command': str(core.LAUNCH_SCRIPT)})
        core.process_identity = lambda pid: True
        core.wait_ready = lambda url, timeout=90.0: True
        opened = {'n': 0}
        core.webbrowser.open = lambda url: opened.__setitem__('n', opened['n'] + 1)
        self.assertEqual(core.start(open_browser=True), 0)
        self.assertEqual(opened['n'], 1)


class NoGlobalMutationTests(TempRootCase):
    def test_install_never_calls_global_pip_or_npm(self):
        seen = []

        def fake_run(args, **kwargs):
            seen.append(args if isinstance(args, list) else [args])
            return subprocess.CompletedProcess(args, 0, '', '')

        core.subprocess.run = fake_run
        core.ensure_venv = lambda base, dry_run=False: (self.root / '.venv' /
                                                        'Scripts' / 'python.exe')
        core.install_requirements = lambda py, dry_run=False, upgrade=False: None
        core.deps_ready = lambda py: True
        code = core.cmd_install(type('A', (), {'dry_run': False, 'upgrade': False,
                                               'with_map': False,
                                               'build_encyclopedia': False})())
        self.assertEqual(code, 0)
        flat = ' '.join(' '.join(map(str, row)) for row in seen).lower()
        self.assertNotIn('npm', flat)
        self.assertNotIn('-g', flat)

    def test_deps_check_does_not_install(self):
        calls = []
        core.subprocess.run = lambda args, **kw: (calls.append(args),
                                                 subprocess.CompletedProcess(args, 1))[1]
        self.assertFalse(core.deps_ready('python'))
        flat = ' '.join(' '.join(map(str, row)) for row in calls).lower()
        self.assertNotIn('install', flat)


class SecretHandlingTests(TempRootCase):
    def test_state_and_log_never_carry_keys(self):
        core.write_state({'pid': 1, 'url': 'http://127.0.0.1:1',
                          'command': 'python launch.py'})
        text = core.STATE_FILE.read_text(encoding='utf-8')
        for harmful in ('api_key', 'sk-', 'sk_', 'Bearer', 'token'):
            self.assertNotIn(harmful, text)

    def test_log_is_utf8(self):
        core.ensure_state_dir()
        path = core.LOG_DIR / 'startup.log'
        path.write_text('启动日志 · 中文\n', encoding='utf-8')
        self.assertEqual(path.read_text(encoding='utf-8').strip(), '启动日志 · 中文')


class CivAtlasInstallTests(TempRootCase):
    def test_missing_node_refuses_with_guidance(self):
        core.node_version = lambda: None
        with self.assertRaises(core.LauncherError) as ctx:
            core.install_civ_atlas(dry_run=True, assume_yes=True)
        self.assertIn('nodejs.org', str(ctx.exception))

    def test_existing_install_is_not_overwritten(self):
        core.CIV_ATLAS_DIR.mkdir(parents=True)
        (core.CIV_ATLAS_DIR / 'package.json').write_text('{}', encoding='utf-8')
        (core.CIV_ATLAS_DIR / 'author-edit.txt').write_text('keep', encoding='utf-8')
        core.install_civ_atlas(dry_run=False, assume_yes=True)
        self.assertTrue((core.CIV_ATLAS_DIR / 'author-edit.txt').exists())

    def test_size_mismatch_refuses(self):
        """源码包大小不符时必须拒绝解包（不靠联网：直接把校验那段逻辑当真值断言）。"""
        core.node_version = lambda: 22
        core.ask = lambda q, assume_yes=False: True
        core.STATE_DIR.mkdir(parents=True, exist_ok=True)
        # 造一个长度不对的「已下载」文件，并把下载入口换成不联网的假实现。
        archive = core.STATE_DIR / 'civ-atlas.tar.gz'
        archive.write_bytes(b'x' * 16)

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size=-1):
                return b''

        core.urllib.request.urlopen = lambda url, timeout=60: FakeResponse()
        core.shutil.copyfileobj = lambda src, dst: dst.write(b'x' * 16)
        with self.assertRaises(core.LauncherError) as ctx:
            core.install_civ_atlas(dry_run=False, assume_yes=True)
        self.assertIn('大小不符', str(ctx.exception))

    def test_unsafe_tar_member_is_refused(self):
        import io
        import tarfile
        evil = self.root / 'evil.tar.gz'
        with tarfile.open(evil, 'w:gz') as bundle:
            payload = b'boom'
            info = tarfile.TarInfo('../escape.txt')
            info.size = len(payload)
            bundle.addfile(info, io.BytesIO(payload))
        with self.assertRaises(core.LauncherError) as ctx:
            core.unpack_safely(evil)
        self.assertIn('不安全', str(ctx.exception))
        self.assertFalse((self.root.parent / 'escape.txt').exists())

    def test_symlink_member_is_refused(self):
        import tarfile
        evil = self.root / 'link.tar.gz'
        with tarfile.open(evil, 'w:gz') as bundle:
            info = tarfile.TarInfo('link')
            info.type = tarfile.SYMTYPE
            info.linkname = '/etc/passwd'
            bundle.addfile(info)
        with self.assertRaises(core.LauncherError) as ctx:
            core.unpack_safely(evil)
        self.assertIn('链接', str(ctx.exception))


class ReadinessTests(unittest.TestCase):
    """真回环 HTTP：起一个最小 http.server 只服务 /openapi.json，验完就关。

    这个类**不**继承 TempRootCase：它不需要临时项目目录，也要避免和其它测试
    共享 monkeypatch 状态（那样一处泄漏就会把就绪判定搅成假成功）。
    """

    def setUp(self):
        # 只保存/恢复本类真正会改的两处；不继承 TempRootCase，减少与其它测试的耦合。
        self._port_reachable = core.port_reachable
        self._urlopen = core.urllib.request.urlopen

    def tearDown(self):
        core.port_reachable = self._port_reachable
        core.urllib.request.urlopen = self._urlopen

    def test_ready_detects_real_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/openapi.json':
                    body = b'{}'
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            self.assertTrue(core.wait_ready('http://127.0.0.1:%d' % port, timeout=10))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5.0)

    def test_ready_times_out_when_nothing_listens(self):
        """确定性验证：端口连不上时绝不判为就绪，且确实在超时窗口内重试。"""
        original = core.port_reachable
        core.port_reachable = lambda host, port, timeout=1.0: False
        try:
            began = time.time()
            ready = core.wait_ready('http://127.0.0.1:65531', timeout=0.8)
            elapsed = time.time() - began
        finally:
            core.port_reachable = original
        self.assertFalse(ready, '连不上的端口不应判为就绪')
        self.assertGreater(elapsed, 0.3, '应在超时窗口内重试，而不是立即返回')

    def test_ready_requires_http_200(self):
        """端口能连但 /openapi.json 不是 200（例如别的服务占着）时不判就绪。"""
        original_reach = core.port_reachable
        original_open = core.urllib.request.urlopen
        core.port_reachable = lambda host, port, timeout=1.0: True

        class NotOurs:
            status = 404

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        core.urllib.request.urlopen = lambda *a, **k: NotOurs()
        try:
            ready = core.wait_ready('http://127.0.0.1:65532', timeout=0.8)
        finally:
            core.port_reachable = original_reach
            core.urllib.request.urlopen = original_open
        self.assertFalse(ready, '没有 /openapi.json 200 的端口不能算就绪')


class DryRunTests(TempRootCase):
    def test_install_dry_run_does_not_touch_disk(self):
        core.find_base_python = lambda: (Path(sys.executable), (3, 12, 0))
        code = core.cmd_install(type('A', (), {'dry_run': True, 'upgrade': False,
                                               'with_map': False,
                                               'build_encyclopedia': False})())
        self.assertEqual(code, 0)
        self.assertFalse(core.VENV_DIR.exists())

    def test_check_is_read_only(self):
        code = core.cmd_check(type('A', (), {})())
        self.assertEqual(code, 0)
        self.assertFalse(core.STATE_FILE.exists())


class CommandLineTests(TempRootCase):
    def test_cli_help_and_unknown(self):
        self.assertEqual(core.main([]), 2)

    def test_check_subcommand_returns_zero(self):
        core.find_base_python = lambda: (None, None)
        self.assertEqual(core.main(['check']), 0)

    def test_install_without_python_returns_one(self):
        core.find_base_python = lambda: (None, None)
        self.assertEqual(core.main(['install', '--dry-run']), 1)

    def test_stop_subcommand_is_safe(self):
        self.assertEqual(core.main(['stop', '--dry-run']), 0)


if __name__ == '__main__':
    unittest.main()
