# TextingDream · 织梦

> **2026-11-12 当前状态**：先读 [docs/工程进度.md](docs/工程进度.md) 与 [docs/模块.md](docs/模块.md)。详细结构见 [工程结构报告](docs/工程结构详细报告_2026-11-12.md)，规格索引见 [docs/文档地图.md](docs/文档地图.md)。旧交接与评估在 [docs/archive/](docs/archive/README.md)，一般情况下不调用。

文字驱动的开放世界探索游戏。本地运行：Python/FastAPI + SQLite 后端，浏览器前端。

项目概念统一见 [CONTEXT.md](CONTEXT.md)；新增或修改文案、命名及交接说明时遵循 [术语与用词规范](docs/术语与用词规范.md)。已有叫法与简化建议见 [工程术语清单](docs/工程术语清单_2026-11-12.md)。
查找现有文档见[文档地图](docs/文档地图.md)与[逐文件总清单](docs/现有文档总清单_2026-11-13.md)；准备处理旧文档时见[过时文档核对清单](docs/过时文档核对清单_2026-11-13.md)。
玩家旅程地图默认支持 Terragenesis 冻结产品 `world_map_product`；[civ-atlas](https://github.com/guaner-334/civ-atlas) 默认关闭，设置 `TEXTILE_CIV_ATLAS=1` 可开启。作者同源地图通过 `config/map-bundles.json` 单独登记，不自动切换玩家默认产品；见 [地图策略](docs/map-backends.md)。

- 仓库：<https://github.com/HouraisanSeiran/-TextingDream.git>（仓库地址；本次是本地开发快照，**不承诺已经推送发布**）
- 暂用项目名：**TextingDream**（中文“织梦”；旧英文标识 TextileDream 作兼容保留）。**工程名后续可能更换。**

> ## ⚠ 这是开发快照，不是稳定发行
>
> 当前提交记录的是**进度快照**，不是完成版 Release。接口、数据格式与 UI 都会变。
> 凡本文没写「已实测」的，都不要当成已验证（详见 §5 进度表与 §6 已知问题）。

---

## 1. 现在能做什么

2026-11-12 补充：玩家地图已有默认 `world_map_product` 路径，作者地图已登记六组地形/环境/气候/水文/洋流/月湖河来源，文明历史已有候选到采纳链路。接入边界以 [工程进度](docs/工程进度.md) 为准；下表保留 2026-11-08 功能验收记录，不代表本轮重验。

| 能力 | 状态 |
|---|---|
| 核心事件链（起点 → 事件节点 → 分支结局） | 可用 |
| 奖励 / 物品 / 钱货（引擎侧发放，不靠模型正文） | 可用 |
| 角色特质（百科命名空间 `character-traits`，随包快照固定版本） | 可用 |
| 单包起点 Demo（当前 `StoryPackage/world_short_tavern`，起点由引擎原子写入） | 可用 |
| 本地百科候选库（`--with-traits` → 15 组 / 551 元素 / 505 来源） | 可用 |
| civ-atlas 接入（固定 commit 安装、真实 `.civsnap` 导出/导入、5 图层） | 可用（见 §4） |
| 原生地图宿主（`dist-dream/dream-host.js`：上游 `rasterize`+`drawMapTerrain`/`drawMapCiv` 真画） | 作者模式可用（真浏览器验过，见 [docs/civ-atlas-host.md](docs/civ-atlas-host.md)）；玩家模式仍为 `not_ready` |
| 玩家地图投影（服务端掩膜底图 + 迷雾） | 后端可用 |
| 旅程天气（只读投影 + 6/24 小时预报） | 后端接口可用；前端未接（按要求本轮不改前端） |
| 地理 + 百科 → 故事包（单地区） | 作者 HTTP 可用；前端面板未接（按要求本轮不改前端） |
| 新双栏游玩 UI（前端） | **仅静态检查过，未做真实浏览器布局验收** |
| 空间草稿（作者圈建筑范围、存草稿、转 TownInput） | 作者 API 可用；玩家地图交互未接 |
| 正式地图多边形圈选 / 按年历史回放 | **未实现** |

这条 Demo 的目标不是「通用叙事引擎」，而是把已经存在的规则资产（百科命名空间、本地资源与日程、
奖励、城镇快照、检定）串成一条可从起点走到不同阶段结局的短篇。
「30–60 分钟可玩」是**设计目标，没有做时长实测**。

---

## 2. 环境与安装

要求 **Python >= 3.11**（本机开发环境实测 3.11/3.12）。依赖以 `requirements.txt` 与 `pyproject.toml` 为准；
两者当前包含同一组核心依赖（`fastapi` `uvicorn[standard]` `pydantic` `httpx` `jinja2` `numpy` `scipy` `pillow`）。

```bash
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# Linux / macOS
.venv/bin/pip install -r requirements.txt
```

依赖：`fastapi` `uvicorn[standard]` `pydantic` `httpx` `jinja2` `numpy` `scipy` `pillow`。
`numpy` / `scipy` 只用于地形与世界生成路线；`pillow` 用于 civ-atlas 适配器解 16 位高度图
（`app/map_import.py`）和地图预览。只跑叙事与地图投影时，它们不是必需路径。
可选开发依赖：`pip install pytest ruff`。

### 2.1 启动

```bash
# 通用（任意机器）：从仓库根目录起，绑定回环地址
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 <http://127.0.0.1:8000>。API Key 在网页里填写，只保留在当前服务内存中。

Windows 上另有 [启动.cmd](启动.cmd) / [新安装并启动.cmd](新安装并启动.cmd) / [start_zhiyem.bat](start_zhiyem.bat)：
`启动.cmd` 与 `新安装并启动.cmd` 跑 `tools/bootstrap.py`，会自动探测 `python` / `py -3` 并挑端口；
`start_zhiyem.bat` 作为兼容文件名使用相同的 bootstrap 启动流程，支持 `--port`、`--no-browser` 和 `--dry-run`。
首次安装仍使用 `新安装并启动.cmd`，日常启动优先使用 `启动.cmd`。

> 仓库不自带常驻服务。需要看界面时按上面命令启动；实际端口与进程状态由本机启动器检查。

### 2.2 存档

正式数据在 `saves/textiledream.sqlite3`，导入地图在 `saves/map_imports/`，笔记锁在 `saves/.notes-locks/`（`saves/` 与旧 `data/` 均已在 `.gitignore` 里忽略）。
**安装、跑测试、构库都不碰它**：测试一律写临时库，构库默认写到 `artifacts/`。
升级代码前请备份整个 `saves/`。本机已从旧 `data/` 安全迁移；原 `data/` 保留作回退参考，不再作为默认存档读取，确认后再由用户处理。迁移报告在 `artifacts/saves-migration/REPORT.md`。

---

## 3. Demo 与百科

世界背景作者链现已接通地图与资料、文明模拟、背景审核发布、国家内聚落与道路规划、单镇细化及王国版本发布。操作见[世界背景生成](docs/world-background-pipeline.md)和[城镇生成](docs/town-generation.md)；道路是规划，新背景与王国版本暂不直接启动旅程。

### 3.1 跑通当前 Demo

1. 启动服务（§2.1）；
2. 打开左上「其他 → 里层创作 → 故事包」，**显式切换到 `world_short_tavern`**（或调
   `POST /api/inner/packages/world_short_tavern/activate`）；
   **不会自动切换**——作者不点就不会改 pointer；
3. 新建旅程时选择该包提供的起点；
4. 起点带来的物品/钱/关系/已知信息由引擎原子写入，任一条校验失败则整条拒绝、零写入。

`StoryPackage/world_short_tavern/` 与它引用的角色包（`story.json` 的 `character_package_id`）是一对，
走既有作者包发现机制，不改任何现有包。仓库里的 `导入_*` 包是地图/历史流程生成的作者包，不是默认 Demo。

### 3.2 构建百科候选库

```bash
# 基础组 + 特质的选定范围：15 组 / 551 元素；不代表启用其他分区后的总库
python -m tools.encyclopedia_build --with-traits
# 只核对现有库与显式名单是否一致，不写库
python -m tools.encyclopedia_build --check --with-traits
```

默认输出 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（`artifacts/` 已忽略，需自己生成）。
导入是幂等增量，**不要另建第二个库**。

> 库里有 ≠ 世界里有，更 ≠ 人物知道。**全部条目 `review_status` 均为 `needs_review`**：
> 没有一条做过逐条事实核验，也没有任何一条被提升为 `reviewed_detail`。

---

## 4. civ-atlas 可选地图后端

默认玩家地图使用 Terragenesis `world_map_product`，统一读取接口位于 `app/map_source/`。
civ-atlas 保留快照导入、原生宿主和历史适配能力，需显式开启；下文为该后端的安装与历史验证记录。

| 项 | 值 |
|---|---|
| 上游 | <https://github.com/guaner-334/civ-atlas>（v1.3.0，AGPL-3.0-only） |
| 固定 commit | `0939c5f1622a5e45cfc16f645ea3845993ab3985` |
| 源码包 SHA-256 | `8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC`（30 256 136 B） |
| 安装位置 | `external/civ-atlas`，**整个目录被 `.gitignore` 忽略**，不进主仓 |
| 本工程对上游的改动 | `docs/civ-atlas-patch/`（三个改动文件 + AGPL 原文副本，共 4 个文件，可重建） |

安装、启动（`127.0.0.1:5188`）、拿到 `.civsnap` 的正确顺序、已知缺口见
[docs/civ-atlas-install.md](docs/civ-atlas-install.md)；契约与许可边界见
[docs/civ-atlas-integration.md](docs/civ-atlas-integration.md)。

**已跑通（真实文件，不是模拟）**：上游侧生成世界 → 保存 → 推演 → 用 `tools/civ_atlas_export.js`
导出 `CASNAP01` 容器（实测 4 609 307 B、`map`/`eras`/`civ` 三块、34097 地块）→ 织梦导入 →
五图层（高程/海陆/气温/降水/群系）各自 PNG 有效 → 取样。
**未完成**：正式地图多边形圈选、按年历史回放；空间草稿已有作者侧 HTTP 与存储
（`app/spatial_draft.py`），但还没有接进玩家地图交互。上游 `resources`（0–3 档）尚未映射，
未接入前一律按「缺失」处理。

---

## 5. 功能验收记录（2026-11-08）

| 项 | 状态 | 证据 |
|---|---|---|
| 核心事件 / 奖励 / 特质 / 当前 Demo | 完成 | 专项测试离线全绿；当前 `world_short_tavern` 走真实 Runtime |
| 551 百科库（`--with-traits`） | 完成 | 构库命令实测 15/551/505、0 未解析 |
| civ-atlas 真实安装 + 固定 commit | 完成 | 包 SHA-256 与三副本哈希已核 |
| 真实 `.civsnap` 导出 → 导入 → 五图层 | 完成 | 4 609 307 B 文件、五图层互不相同 |
| 世界基础版本化 / 空间三层 / 取样语义 | 完成 | 交接文档记为 85 项全过（本轮未重跑） |
| 空间草稿（作者 HTTP + 存储 + 转 TownInput） | 可用 | `app/spatial_draft.py`；`tests/test_spatial_draft.py` 等 |
| 正式地图多边形圈选 / 按年历史回放 | **未完成** | `REPLAY_IMPLEMENTED` 全 `False` |
| 新双栏 UI 前端 | **当时仅语法检查**（325 个 JS）；该批未做真实浏览器布局验收 | §6 |
| 后端玩家地图投影 | 专项测试通过（只读 GET 不改 `state_version`） | §5.2 |
| 计划中的四大优先功能 | **没有全部完成** | 逐项状态见 §5 与 §6 |

### 5.1 测试数字怎么读

历次验收跑的是**不同文件集**，数字**不能相加**，也不要按旧口径引用：

- 2026-11-12 结构梳理执行 `pytest --collect-only -o addopts='' -q`，收集 **2938 项**；只收集，未执行全量测试。
- 2026-11-08 的收集记录为 2208 项，是历史数量。
- 早期全量、地图适配、世界基础、玩家投影等批次是不同文件集，不能相加；本 README 不再保留
  旧的“25 项 / 128 项”作为现行结论。
- 2026-11-08 复查只跑到 38%（约 10 分钟）即停止，未完成全量，因此**不给出当前通过总数**。

仓库里没有「全部一起跑」的现行总数。要自己确认就按 §5.2 跑，**不要把任何批次数字当总测试数**。

### 5.2 自己跑测试

```bash
# 全部（离线，写临时库，不碰 saves/）
python -m unittest discover -s tests -t . -v
# 或 pytest
python -m pytest
# 只跑地图相关这一批
python -m unittest tests.test_play_map tests.test_civ_atlas_import tests.test_world_basis tests.test_land_footprint -v
```

不需要 API Key；测试里会把 provider 换成会抛错的东西，确认一次远程调用都没发生。

---

## 6. 已知问题与明确未做的

1. **API 配置旧页表单被移走**：顶部「⌁ API 配置」弹层会把 `#api-form` 整个搬到弹层里，
   而旧页面 `#api` 里的表单因此**留下空壳**（只剩标题与说明文字）。这是已知待修项，
   **不是已修复**；旧页入口与弹层共用同一份表单，字段没有复制。
2. **整体前端验收需按界面批次区分**：2026-11-08 新双栏 UI 的记录是语法检查（当时 325 个 JS、顶层 29 个）；后续作者地图有专项 HTTP/Edge 证据，见 [工程进度](docs/工程进度.md)。专项验收和旧截图不代表当前主站全部布局已验收。
3. **「四大优先功能」没有全部完成**：正式地图多边形圈选、按年历史回放、服务端强制供给校验
   仍在未完成清单里；空间草稿已有作者侧 API/存储，但未接入玩家地图交互（见
   [docs/工程进度.md](docs/工程进度.md)）。
4. **civ-atlas 既有样例的地图尺度与城镇阈值存在冲突**：该样例单格 ≈ 14 959 km²，最小 3 格取样窗 ≈ 44 878 km²，
   而 `TownInput.terrain.area_km2` 上限是 20 000 km²。因此腹地必须由作者显式声明，
   不自动 clamp、不给默认值。
5. **气候不能从高度图得到**：16 位高度图本身没有气温/降水；civ-atlas 快照或已声明的 TG 气候/环境产品可分别提供相应数据。消费者按来源与图层读取，缺值不按纬度补猜；TG 月气候尚未自动接到旅程天气。
6. **百科内容全部 `needs_review`**：候选素材，不是已认证事实。
7. **手机端适配暂停**：桌面优先，`@media(max-width:800px)` 旧规则保留但不再作为验收标准。
8. **`temp_dl/` 是本地下载临时目录**：未跟踪、不入库，也不属于本快照的交付产物。

---

## 7. 目录速览

```
app/            FastAPI 服务与静态前端（app/static/*.js|css|html）
tools/          构库、导出器、制图脚本
tests/          离线测试（标准库 unittest / pytest 均可）
docs/           设计、契约、安装、交接与补丁（含 docs/civ-atlas-patch/）
StoryPackage/   故事包（总概.md / 知识点 / story.json）
character_packages/  角色包
assets/maps/    测试底图（Natural Earth 公共领域 + GMT Earth Relief）
external/       civ-atlas 本体（**被 .gitignore 忽略**，按 docs/civ-atlas-install.md 重建）
```

---

## 8. 许可

- **本工程自有代码：MIT**，全文见 [LICENSE](LICENSE)（`Copyright (c) 2026 TextingDream contributors`）。
  `pyproject.toml` 里用 `license = { file = "LICENSE" }` 指向同一个文件（已用 `tomllib` + setuptools 读取校验，无警告）。
- **第三方来源不被重新授权**：MIT 只覆盖本工程自己写的代码，**不覆盖**任何第三方源码、
  字体、数据或二进制依赖。逐项归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 要点（**读之前请先看第三方清单，不要用 MIT 一句话概括整包**）：
  - `external/civ-atlas`（civ-atlas，© 2026 guaner-334）为 **AGPL-3.0-only**，整目录不入本仓；
  - `docs/civ-atlas-patch/` 里的 `index.html` 是**来自上游的完整替换文件**，仍按 AGPL-3.0-only 处理，
    **不能以 MIT 重新授权**；同目录随附上游 AGPL 原文 `LICENSE`；
  - 上游第三方字体 SIL OFL 1.1、`mediabunny` MPL-2.0 等，各按其自带 notice / 许可保留；
  - `assets/maps/` 下的 Natural Earth 为公共领域，GMT Earth Relief 按其数据门户条款。
- 本 README 与第三方清单描述的是**工程事实与来源范围**，**不是法律意见**，也不构成任何许可结论或保证。

---

## 9. 延伸阅读

- [docs/工程进度.md](docs/工程进度.md) — 当前完成度
- [docs/模块.md](docs/模块.md) — 代码模块与职责
- [docs/文档地图.md](docs/文档地图.md) — 现行规格索引
- [综合游玩建议](docs/综合游玩建议_2026-11-12.md) — 探索、人物、战斗、魔法和生活经营的连接，供负责人规划
- [资料采集交接](docs/element-database/agent-handoff.md) — 向采集智能体分派专题、文件范围与交付要求
- [docs/one-click-start.md](docs/one-click-start.md) — Windows 安装与启动
- [docs/civ-atlas-install.md](docs/civ-atlas-install.md) — civ-atlas 安装与重建
- [docs/weather.md](docs/weather.md) — 天气规则与只读投影
- [docs/world-package-pipeline-使用说明.md](docs/world-package-pipeline-使用说明.md) — 地理 + 百科生成故事包
- [docs/archive/README.md](docs/archive/README.md) — 旧交接与评估（默认不读）
