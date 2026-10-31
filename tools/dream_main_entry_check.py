# -*- coding: utf-8 -*-
"""主入口的真浏览器验收：`/` 页面里能不能真的看到原生地图、作者能不能生成并登记。

它不 mock 自己的后端：

* 起一个**临时回环服务**（`tools/serve_for_probe.py`，临时 sqlite，不碰 data/）；
* 真实浏览器打开 `/`，页面自己走 `/static/native-map.js` → `/native-map/dream-host.js`；
* 作者点「生成并登记」→ 上游 worker 生成 → 打包 → `POST /api/inner/map-imports`
  → 页面读回并画出地图。本地图不看任何假数据。

用法： python tools/dream_main_entry_check.py [--keep]
返回一行 JSON，非 0 退出码只在“主入口真的没成”时出现。
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'external' / 'civ-atlas'


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_ready(port, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/api/bootstrap' % port, timeout=3) as res:
                if res.status == 200:
                    return True
        except Exception:  # noqa: BLE001  —— 启动期的连接错误都算还没就绪
            time.sleep(0.4)
    return False


def main():
    keep = '--keep' in sys.argv
    temp = tempfile.mkdtemp(prefix='dream-probe-')
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(ROOT / 'tools' / 'serve_for_probe.py'), str(port), temp],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    browser = None
    try:
        if not wait_ready(port):
            output = ''
            if server.poll() is not None:
                output = server.stdout.read()[-4000:]
            raise SystemExit(json.dumps({'ok': False, 'why': '服务没起来', 'server': output}))
        # browser 由台本自己起，这里只把地址交出去
        script = ROOT / 'tools' / 'dream_main_entry.mjs'
        node = shutil_which('node')
        if node is None:
            raise SystemExit(json.dumps({'ok': False, 'why': '没有 node'}))
        # 台本的 stderr 里是逐步进度：一实时写到 artifacts/（不随临时目录删掉，失败后能看）
        log_dir = ROOT / 'artifacts'
        log_dir.mkdir(parents=True, exist_ok=True)
        progress_path = log_dir / 'dream-main-entry-progress.log'
        with open(progress_path, 'w', encoding='utf-8') as progress:
            result = subprocess.run(
                [node, str(script), 'http://127.0.0.1:%d' % port],
                cwd=str(UPSTREAM), stdout=subprocess.PIPE, text=True,
                encoding='utf-8', errors='replace', timeout=900, stderr=progress)
        tail = progress_path.read_text(encoding='utf-8', errors='replace')[-4000:] \
            if progress_path.exists() else ''
        if tail:
            sys.stderr.write(tail)
            sys.stderr.flush()
        lines = [line for line in (result.stdout or '').splitlines() if line.strip()]
        report = json.loads(lines[-1]) if lines else {'ok': False, 'why': '台本没有输出'}
        if result.returncode != 0 and report.get('ok'):
            report['ok'] = False
            report['why'] = '台本退出码 %d' % result.returncode
        report['stderr'] = '' if report.get('ok') else tail[-1500:]
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report.get('ok') else 1
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
        if not keep:
            shutil_rmtree(temp)


def shutil_which(name):
    from shutil import which
    return which(name)


def shutil_rmtree(path):
    from shutil import rmtree
    for _ in range(5):
        try:
            rmtree(path, ignore_errors=False)
            return
        except OSError:
            time.sleep(0.3)


if __name__ == '__main__':
    sys.exit(main())
