# -*- coding: utf-8 -*-
"""起一个「存档库副本」临时实例，给 tools/p1_ui_probe.cjs 做会改数据的验收（重命名 / 删除存档）。

为什么要有它：
  * 探针里的「存档管理」要真的 PATCH / DELETE /api/sessions/{id}，这些只能打在临时实例上，
    绝不能碰用户正在用的 8000 端口服务；
  * tools/p1_ui_check.py 起的是空库，没有真实的故事包 / 角色包 / 地图导入；这里改为复制
    saves/textiledream.sqlite3（用 sqlite 在线备份 API，只读打开源库，不影响 8000 服务）、
    StoryPackage/、character_packages/、saves/map_imports/ 到一个临时目录再起服务。

用法（先起服务，再跑探针）：
  python tools/p1_ui_serve_copy.py <副本目录>            # 默认监听 127.0.0.1:8979，前台阻塞
  # 探针：设 TD_BASE=http://127.0.0.1:8979/ TD_ALLOW_MUTATE=1 TD_SHOTS=... TD_FIXTURE=<副本目录>/fixture.json 的内容
  # 用完停掉本进程。

安全边界：
  * 端口等于 8000 直接拒绝；只监听回环；
  * 副本目录若已存在会先清空（只允许清空名字里带 uiprobe / td-ui 的目录，防误删）；
  * 只读源库与源目录，不写工程里的 saves/ StoryPackage/ character_packages/。
fixture 会往副本库里追加两段测试旅程（一段关联 fixture 地图、一段未关联）与一个故事包版本。
"""
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

PORT = int(os.environ.get('TD_PORT', '8979'))


def copy_store(dest: Path):
    source = ROOT / 'saves' / 'textiledream.sqlite3'
    if not source.is_file():
        raise SystemExit('找不到存档库：' + str(source))
    dest.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    dst = sqlite3.connect(str(dest / 'textiledream.sqlite3'))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    for name, target in (('StoryPackage', 'StoryPackage'), ('character_packages', 'character_packages'),
                         ('saves/map_imports', 'map_imports')):
        folder = ROOT / name
        if folder.is_dir():
            shutil.copytree(folder, dest / target, dirs_exist_ok=True)


def main():
    if PORT == 8000:
        raise SystemExit('拒绝：8000 是正在使用的服务端口')
    if len(sys.argv) < 2:
        raise SystemExit('用法：python tools/p1_ui_serve_copy.py <副本目录>')
    dest = Path(sys.argv[1]).resolve()
    if dest.exists():
        if not any(k in dest.name.lower() for k in ('uiprobe', 'td-ui')):
            raise SystemExit('拒绝清空名字里不含 uiprobe / td-ui 的已存在目录：' + str(dest))
        shutil.rmtree(dest)
    copy_store(dest)

    import uvicorn
    from app.web import create_app
    from p1_ui_check import build_fixture

    app = create_app(dest / 'textiledream.sqlite3')
    fixture = build_fixture(app)
    (dest / 'fixture.json').write_text(json.dumps(fixture, ensure_ascii=False), encoding='utf-8')
    print('FIXTURE', json.dumps(fixture, ensure_ascii=False), flush=True)
    print('副本目录:', dest, flush=True)
    uvicorn.run(app, host='127.0.0.1', port=PORT, log_level='warning')


if __name__ == '__main__':
    main()
