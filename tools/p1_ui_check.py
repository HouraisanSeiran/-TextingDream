# -*- coding: utf-8 -*-
"""P1 桌面验收的**服务侧**：临时 Store + 一张测试用地图，然后把浏览器交给 tools/p1_ui_probe.cjs。

不装任何依赖：
  * 服务用 venv 已有的 uvicorn（线程内跑，跑完 should_exit）；
  * 浏览器用 external/civ-atlas/node_modules 里已有的 playwright + 本机 Edge。

隔离边界（重点，不伪造）：
  * 数据库是 temp 目录里的新文件；StoryPackage 库随之指向临时目录；
  * 地图是本文现画的一张 16 位高度图，**不是用户的世界**，也不是真实 civ-atlas 导出；
  * 只监听 127.0.0.1 的临时端口，跑完关服务；
  * 不写 data/、不碰旧包，不 git。

用法：
  python tools/p1_ui_check.py            # 跑两个视口，输出 PASS/FAIL 与截图
退出码 = 探测器的退出码（有 FAIL 就非零）。
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))       # `python tools/x.py` 时仓库根不在 sys.path 上
SCRATCH = Path(os.environ.get('TD_SCRATCH') or tempfile.gettempdir()) / 'td-ui-check'
SHOTS = ROOT / 'docs' / 'ui-shots' / 'p1'
PORT = int(os.environ.get('TD_PORT', '8977'))


# ------------------------------------------------------------------ fixture map
def heightmap_png(width=1024, height=512, lo=-4000, hi=3000, sea_gray=20000):
    """16-bit grayscale heightmap in the documented envelope; left half sea, right half land."""
    rows = bytearray()
    for _y in range(height):
        rows.append(0)
        for x in range(width):
            grey = 0 if x < width // 2 else int(65535 * (x - width // 2) / max(1, width // 2 - 1))
            rows += struct.pack('>H', min(65535, grey))

    def chunk(ctype, body):
        return (struct.pack('>I', len(body)) + ctype + body
                + struct.pack('>I', zlib.crc32(ctype + body) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', width, height, 16, 0, 0, 0, 0)
    desc = ('16-bit grayscale heightmap, equirectangular (latitude linear top to bottom), '
            '2:1. Gray 0 = %d m, 65535 = %d m, linear. Sea level (0 m) = gray %d; land is '
            'brighter, sea is darker.' % (lo, hi, sea_gray))
    return b''.join([
        b'\x89PNG\r\n\x1a\n', chunk(b'IHDR', ihdr),
        chunk(b'tEXt', b'Software\x00Wenming Ditu (civilization map generator)'),
        chunk(b'tEXt', b'Description\x00' + desc.encode('latin-1', 'replace')),
        chunk(b'IDAT', zlib.compress(bytes(rows), 6)), chunk(b'IEND', b''),
    ])


def start_service(db_path):
    from app.web import create_app
    app = create_app(db_path)
    config = uvicorn.Config(app, host='127.0.0.1', port=PORT, log_level='warning', lifespan='off')
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.time() + 30
    while time.time() < deadline:
        if server.started:
            return app, server
        time.sleep(0.1)
    raise RuntimeError('uvicorn 未能在 30s 内启动')


def build_fixture(app):
    """Two journeys on one fixture map: one linked, one deliberately not linked."""
    from app import map_import
    svc = app.state.service
    # 假密钥：用它验证任何响应体/header 都不回显。值本身不需要真实。
    svc.provider.configure({'offline': True, 'api_key': 'sk-P1TESTSECRET-1234567890',
                            'base_url': 'https://api.deepseek.com', 'model': 'deepseek-flash',
                            'clear_key': False})
    root = Path(svc.store.path).parent
    record = map_import.create_import(svc.store, root, heightmap_png())
    package = svc.runtime.package()
    story = json.loads(json.dumps(package['story']))
    characters = json.loads(json.dumps(package['characters']))
    story.setdefault('mechanics', {})['map'] = {
        'kind': 'civ_atlas', 'import_id': record['id'],
        'fog': {'reveal_radius_km': 600}}
    svc.runtime.commit_package(story, characters, 'P1 验收：关联测试地图（fixture，非用户世界）')
    linked = svc.runtime.new_session('P1 验收地图旅程', 'protagonist')
    plain_story = json.loads(json.dumps(story))
    plain_story['mechanics'].pop('map', None)
    svc.runtime.commit_package(plain_story, characters, 'P1 验收：未关联地图')
    plain = svc.runtime.new_session('P1 未关联旅程', 'protagonist')
    return {'linked': linked['id'], 'plain': plain['id'], 'import': record['id'],
            'note': 'fixture 地图是验收脚本现画的 16 位高度图，不是用户世界'}


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    db_path = SCRATCH / 'p1-ui-check.sqlite3'
    for suffix in ('', '-wal', '-shm'):
        leftover = Path(str(db_path) + suffix)
        if leftover.exists():
            leftover.unlink()
    app, server = start_service(db_path)
    code = 1
    print('临时 DB:', db_path, flush=True)
    try:
        fixture = build_fixture(app)
        print('fixture:', json.dumps(fixture, ensure_ascii=False), flush=True)
        env = {**os.environ,
               'TD_BASE': 'http://127.0.0.1:%d/' % PORT,
               'TD_FIXTURE': json.dumps(fixture, ensure_ascii=False),
               'TD_SHOTS': str(SHOTS),
               'NODE_PATH': str(ROOT / 'external' / 'civ-atlas' / 'node_modules')}
        node = shutil.which('node') or 'node'
        print('服务就绪：http://127.0.0.1:%d/ （仅回环，跑完关）' % PORT, flush=True)
        code = subprocess.call([node, str(ROOT / 'tools' / 'p1_ui_probe.cjs')], env=env,
                               cwd=str(ROOT))
    finally:
        server.should_exit = True
        deadline = time.time() + 10
        while time.time() < deadline and getattr(server, 'started', False):
            time.sleep(0.1)
        print('服务已请求退出（should_exit=True）', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
