#!/usr/bin/env python
"""织梦一键安装 / 启动 / 停止的入口。

    python tools/bootstrap.py check
    python tools/bootstrap.py install [--with-map] [--build-encyclopedia]
    python tools/bootstrap.py start [--port N] [--no-browser]
    python tools/bootstrap.py stop

只依赖标准库，所以「用系统 Python 跑这个脚本」本身不需要先装任何东西。
详细说明见 docs/one-click-start.md。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from launcher.core import main  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(main())
