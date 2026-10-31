# -*- coding: utf-8 -*-
"""临时回环服务：只给 `tools/dream_main_entry.mjs` 的真实浏览器验证用。

它做两件事，都不碰正式数据：

* 用 **临时 sqlite** 建 app（`create_app(<temp>/probe.sqlite3)`），不读也不写 `data/`；
* 绑定 `127.0.0.1` + 随机高位端口，进程结束时整个临时目录一起删。

用法： python tools/serve_for_probe.py <port> <temp_root>
"""
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.web import create_app  # noqa: E402  (路径要先插好)


def main():
    port = int(sys.argv[1])
    temp_root = Path(sys.argv[2])
    temp_root.mkdir(parents=True, exist_ok=True)
    app = create_app(temp_root / 'probe.sqlite3')
    # offline：验证不需要任何模型调用，也不该把作者的 key 带进来
    app.state.service.provider.configure({'offline': True})
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning', access_log=False)


if __name__ == '__main__':
    main()
