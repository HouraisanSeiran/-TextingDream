# 一键安装与启动（Windows 与类 Unix）

把整个目录解压到任意普通路径（**路径里可以有中文和空格**），第一次双击安装并启动，
以后只双击启动。密钥在网页里自己填，安装包不含任何密钥。

> 这是「源码 + 本机解释器」的部署方式，**不是**自带 Python/Node 的免安装版。
> 首次安装需要联网下载 pip 依赖；地图生成器（civ-atlas）另外可选安装。

---

## 1. 三个入口

| 用途 | Windows | 命令行等价 |
|---|---|---|
| 首次安装并启动 | `新安装并启动.cmd` | `python tools/bootstrap.py install` 然后 `start` |
| 以后启动 | `启动.cmd` | `python tools/bootstrap.py start` |
| 停止本项目启动的服务 | `停止服务.cmd` | `python tools/bootstrap.py stop` |
| 只查看环境（不改任何东西） | — | `python tools/bootstrap.py check` |

`.cmd` 文件正文是纯 ASCII，任何控制台代码页都能跑；中文只出现在文件名里。
所有逻辑都在 `tools/bootstrap.py` / `tools/launcher/core.py`，`.cmd` 只是转发。

已有的 `launch.py` 与 `启动织梦.cmd` **没有被覆盖**：前者仍可直接
`python launch.py`，后者保留原来写死解释器的行为。

## 2. 首次安装会做什么

1. **找 Python**：依次尝试已有 `.venv`、`TEXTILEDREAM_PYTHON` 环境变量、当前解释器、
   `python` / `py`。判定方式是让它真的算一个版本号（`python -c`），所以 Microsoft Store
   的占位程序（说得出版本、做不了事）会被拒绝，并给出 python.org 的安装指引。
   要求 **>= 3.11**。
2. **建项目独立 `.venv`**：`<项目>/.venv`，不碰系统 Python、不改 PATH。
3. **装依赖**：用**该 venv 的** `python -m pip install -r requirements.txt`。
   默认不加 `--upgrade`（不静默升级已装好的包）；需要时显式加 `--upgrade`。
   装完立刻做一次 import 检查（fastapi / uvicorn / pydantic / httpx / jinja2 / PIL）。
4. **可选**地图生成器、可选百科库：
   - `--with-map`：装 civ-atlas 本体（见第 4 节）。
   - `--build-encyclopedia`：安装后跑 `tools/encyclopedia_build.py --with-traits`
     （幂等：同样的输入重复跑结果一样）。

## 3. 启动与停止的边界

- 只监听 **127.0.0.1**，不对外网开放。
- 端口：默认 **8000**；被占用就让系统给一个空闲端口，**不会去杀别的进程腾端口**。
  实际地址会打印出来，并在就绪后才自动打开浏览器。
- 状态文件：`logs/launcher-state.json`（`logs/` 已在 `.gitignore` 里），记录
  `pid`、`url`、`port`、`started`、`command`。日志 `logs/startup.log` 为 UTF-8。
- **停止只停自己启动的那个进程**：要求 PID 存活、命令行里含本项目的 `launch.py`；
  两者不符就拒绝并说明原因。不按端口全杀，也不拿复用的 PID 误杀。
- **重复启动**：如果状态文件里的服务仍然就绪，直接复用并打开浏览器，不会起第二个。
- 没有新的守护进程/服务框架：就是 `launch.py` 一个前台进程 + 一个状态文件。

## 4. 地图生成器（civ-atlas，可选）

织梦本体不依赖它；不装也能存/读空间草稿、建城镇草稿，只是没法用地图工具里的
civ-atlas 生成器。

```powershell
python tools/bootstrap.py install --with-map --yes
```

- 需要 **Node >= 22**（`node --version`）。缺失时直接给出 nodejs.org 的安装指引，
  **不会**自动装系统运行时、不静默升级、不改 npm registry、不 `curl | sh`。
- 来源固定：官方 `codeload` 源码包，commit
  `0939c5f1622a5e45cfc16f645ea3845993ab3985`，`30256136` 字节，
  SHA-256 `8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC`。
  大小或摘要不符**拒绝解包**。
- 解包用 `tarfile`，逐个成员检查：拒绝绝对路径、`..` 穿越、符号链接/硬链接。
- 已存在 `external/civ-atlas` 时**不覆盖**（可能是作者改过的）。
- 装完把 `docs/civ-atlas-patch/files/` 的三个文件放到对应位置（织梦的导出入口）。
- 之后按 `docs/civ-atlas-install.md` 第 3 节起服务（vite，127.0.0.1:5188）：
  本启动器**不**代跑 pnpm，也不改全局 npm。地图工具用不上时就不要装。

## 5. 确认式交互

- 任何下载/安装动作第一次都要求确认；非交互环境（CI、双击带管道）必须显式
  `--yes`，否则拒绝并说明。
- `--dry-run` 只打印计划：不建 `.venv`、不装包、不下载、不启动进程。
  主审可以用它审流程：

```powershell
python tools/bootstrap.py install --with-map --dry-run
python tools/bootstrap.py start --dry-run
python tools/bootstrap.py stop --dry-run
```

## 6. 测试

```powershell
python -m unittest tests.test_bootstrap -v
```

这些测试**不联网、不装依赖、不改系统**：网络与子进程都是替身，路径用临时目录
（含「中文 空格」路径），回环就绪只用一个本机 `http.server` 线程，跑完就关。

## 7. 已知限制（如实）

- 首次安装需要联网（pip 源）；离线环境请先自行准备好 wheel 或已建好的 `.venv`。
- `requirements.txt` 只写了最低版本（`fastapi>=0.115` 等），**没有逐包锁版本**。
  要完全可复现，把实际安装后的 `pip freeze` 结果固定下来更稳——本轮没有替你猜版本。
- 安装器不代跑 civ-atlas 的 `pnpm install`；按 `docs/civ-atlas-install.md` 手动作，
  并注意那里记录的 `--ignore-scripts --frozen-lockfile` 约束。
- 若把整个仓库换成「内置 Python/Node」的发行形态，本启动器不适用。
