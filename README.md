# TextingDream · 织梦

> **2026-10-31 当前交接**：请先阅读 [工程交接与工作进度](工程交接与工作进度_2026-10-31.md)。本次修复海岸细化淹没城址、海面详情误选和隐藏城镇点选；文档列出实际测试结果、已知阻塞及稳定 Demo 的剩余工作。以下历史进度表与旧故事入口不应直接当成当前验收结论。

中文跑团（TRPG 式）叙事工作台。本地运行：Python/FastAPI + SQLite 后端，浏览器前端；
地图基础统一使用 [civ-atlas](https://github.com/guaner-334/civ-atlas)。

- 仓库：<https://github.com/HouraisanSeiran/-TextingDream.git>（仓库地址；本次是本地开发快照，**不承诺已经推送发布**）
- 项目名：**TextingDream**（中文“织梦”；旧英文标识 TextileDream 作为兼容称呼保留）

> ## ⚠ 这是开发快照，不是稳定发行
>
> 当前提交记录的是**进度快照**，不是完成版 Release。接口、数据格式与 UI 都会变。
> 凡本文没写「已实测」的，都不要当成已验证（详见 §5 进度表与 §6 已知问题）。

---

## 1. 现在能做什么

| 能力 | 状态 |
|---|---|
| 核心事件链（起点 → 事件节点 → 分支结局） | 可用 |
| 奖励 / 物品 / 钱货（引擎侧发放，不靠模型正文） | 可用 |
| 角色特质（百科命名空间 `character-traits`，随包快照固定版本） | 可用 |
| 单包多起点 Demo（三起点、原子初始化、「河港汛期」短篇） | 可用 |
| 本地百科候选库（`--with-traits` → 15 组 / 551 元素 / 505 来源） | 可用 |
| civ-atlas 接入（固定 commit 安装、真实 `.civsnap` 导出/导入、5 图层） | 可用（见 §4） |
| 原生地图宿主（`dist-dream/dream-host.js`：上游 `rasterize`+`drawMapTerrain`/`drawMapCiv` 真画） | 作者模式可用（真浏览器验过，见 [docs/civ-atlas-host.md](docs/civ-atlas-host.md)）；玩家模式仍为 `not_ready` |
| 玩家地图投影（服务端掩膜底图 + 迷雾） | 后端可用 |
| 新双栏游玩 UI（前端） | **仅静态检查过，未做真实浏览器布局验收** |
| 空间草稿端点（只圈建筑范围） | **未实现** |
| 地图多边形圈选 / 按年历史回放 | **未实现** |

这条 Demo 的目标不是「通用叙事引擎」，而是把已经存在的规则资产（百科命名空间、本地资源与日程、
奖励、城镇快照、检定）串成一条可从三种起点走到不同阶段结局的短篇。
「30–60 分钟可玩」是**设计目标，没有做时长实测**。

---

## 2. 环境与安装

要求 **Python >= 3.11**（本机开发环境实测 3.11.11）。依赖**只以 `requirements.txt` 为准**
（`pyproject.toml` 的正依赖列表比它少一个 `pillow`；两者不一致处一律按 `requirements.txt` 装）。

```bash
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# Linux / macOS
.venv/bin/pip install -r requirements.txt
```

依赖：`fastapi` `uvicorn[standard]` `pydantic` `httpx` `jinja2` `pillow`。
`pillow` 只用于 civ-atlas 适配器解 16 位高度图（`app/map_import.py`），不装则该条导入路线不可用。
可选开发依赖：`pip install pytest ruff`。

### 2.1 启动

```bash
# 通用（任意机器）：从仓库根目录起，绑定回环地址
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 <http://127.0.0.1:8000>。API Key 在网页里填写，只保留在当前服务内存中。

Windows 上另有 `启动织梦.cmd` / `start_zhiyem.bat`：它们跑 `launch.py`，自动挑端口、打开浏览器。
**这两个脚本里写死了开发机的解释器路径 `D:\anaconda\python.exe`**，换一台机器跑之前必须改成自己的
Python 路径（或直接用上面的 `python -m uvicorn`）。同样，本文出现的任何 `D:\...` 路径都只是开发机
的历史记录，**不是唯一可行命令**。

> **当前服务是关闭的**：仓库交付时不带任何常驻监听（8000 / 8897 / 8898 / 5188 均无监听）。
> 需要看界面时请读者自己按上面命令启动，不要假设某台机器上已经在跑。

### 2.2 存档

正式数据在 `data/textiledream.sqlite3`（`data/` 已在 `.gitignore` 里忽略）。
**安装、跑测试、构库都不碰它**：测试一律写临时库，构库默认写到 `artifacts/`。
升级代码后若要保留旧旅程，先自行备份 `data/`；本快照没有做数据迁移的承诺。

---

## 3. Demo 与百科

### 3.1 跑通三起点 Demo

1. 启动服务（§2.1）；
2. 打开左上「其他 → 里层创作 → 故事包」，**显式切换到 `河港汛期`**（或调
   `POST /api/inner/packages/河港汛期/activate`）；
   **不会自动切换**——作者不点就不会改 pointer；
3. 新建旅程时选择三个起点之一；
4. 起点带来的物品/钱/关系/已知信息由引擎原子写入，任一条校验失败则整条拒绝、零写入。

`StoryPackage/河港汛期/` + `character_packages/riverport-demo-characters-001.json` 是一对，
走既有作者包发现机制，不改任何现有包。

### 3.2 构建百科候选库

```bash
# 最新交付口径：15 组 / 551 元素 / 505 来源（本机实测；默认 14 组为历史口径，供旧集回归）
python -m tools.encyclopedia_build --with-traits
# 只核对现有库与显式名单是否一致，不写库
python -m tools.encyclopedia_build --check --with-traits
```

默认输出 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（`artifacts/` 已忽略，需自己生成）。
导入是幂等增量，**不要另建第二个库**。

> 库里有 ≠ 世界里有，更 ≠ 人物知道。**全部条目 `review_status` 均为 `needs_review`**：
> 没有一条做过逐条事实核验，也没有任何一条被提升为 `reviewed_detail`。

---

## 4. civ-atlas 地图基础

本工程所有与地图关联的玩法（城镇/地点选址、稀疏用地、资源空间分布、势力领地、旅行路线、
区域事件与历史地理）**默认以 civ-atlas 为地图基础**，不另建平行地图引擎。

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
**未完成**：空间草稿（只圈建筑范围）端点、地图多边形圈选、按年历史回放；
上游 `resources`（0–3 档）尚未映射，未接入前一律按「缺失」处理。

---

## 5. 进度表（本轮）

| 项 | 状态 | 证据 |
|---|---|---|
| 核心事件 / 奖励 / 特质 / 三起点 Demo | 完成 | 专项测试离线全绿；三起点 E2E 走真实 Runtime |
| 551 百科库（`--with-traits`） | 完成 | 构库命令实测 15/551/505、0 未解析 |
| civ-atlas 真实安装 + 固定 commit | 完成 | 包 SHA-256 与三副本哈希已核 |
| 真实 `.civsnap` 导出 → 导入 → 五图层 | 完成 | 4 609 307 B 文件、五图层互不相同 |
| 世界基础版本化 / 空间三层 / 取样语义 | 完成 | 交接文档记为 85 项全过（本轮未重跑） |
| 空间草稿端点（`POST .../spatial-draft`） | **未完成** | `app/spatial_draft.py` 不存在 |
| 多边形圈选 / 按年历史回放 | **未完成** | `REPLAY_IMPLEMENTED` 全 `False` |
| 新双栏 UI 前端 | **仅 `node --check` 通过**（13 个 JS，本机实测 0 失败）；**未做真实浏览器布局验收** | §6 |
| 后端玩家地图投影 | `tests/test_play_map.py` 25 项**本次主代理独立复跑全过**（exit 0） | 只读 GET 不改 `state_version` |
| 计划中的四大优先功能 | **没有全部完成** | 逐项状态见 §5 与 §6 |

### 5.1 测试数字怎么读

历次验收跑的是**不同文件集**，数字**不能相加**，也不要按旧口径引用：

- **主审历史口径**：早期全量回归一次是 521 项；最后一次主审是 128 项，地图适配主审是 33 项。
- **后续代理阶段**：civ-atlas 导入 + 世界基础 + 空间三层专项 85 项；玩家地图投影 25 项；
  另有一批代理侧回归 119 项记录为通过（本速度快照未重跑）。
- **本轮新增**：上面那 25 项已由主代理**独立复跑**（不是只据代理自报），结果全过、exit 0。

仓库里没有「全部一起跑」的现行总数。要自己确认就按 §5.2 跑，**不要把任何批次数字当总测试数**。

### 5.2 自己跑测试

```bash
# 全部（离线，写临时库，不碰 data/）
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
2. **前端未做真实浏览器布局验收**：新双栏 UI（左对话/右地图）只做了 `node --check` 静态检查
   （13 个 `app/static/*.js` 全部通过），**没有**真实浏览器下的布局、截屏或交互验收。
   旧页面仍有历史截图，但**旧截图不代表当前布局**。
3. **「四大优先功能」没有全部完成**：地图圈选、空间草稿落盘、按年历史回放、服务端强制供给校验
   仍在未完成清单里（详见 [docs/handoff-spatial-and-world-basis.md](docs/handoff-spatial-and-world-basis.md)
   第 4 节）。
4. **地图尺度与城镇阈值存在结构性冲突**：单格 ≈ 14 959 km²，最小 3 格取样窗 ≈ 44 878 km²，
   而 `TownInput.terrain.area_km2` 上限是 20 000 km²。因此腹地必须由作者显式声明，
   不自动 clamp、不给默认值。
5. **气候不能从高度图得到**：只在导入 `.civsnap` 时有实测值；16 位高度图没有气温/降水，
   作者不填就拒绝生成，**不会「按纬度估一个」**。
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

- [docs/civ-atlas-install.md](docs/civ-atlas-install.md) — civ-atlas 装什么、怎么装、怎么重建
- [docs/civ-atlas-host.md](docs/civ-atlas-host.md) — **原生地图宿主**：数据桥、两种模式、居中/投影约束、怎么验
- [docs/civ-atlas-integration.md](docs/civ-atlas-integration.md) — 适配器契约、缺失字段与诚实标记
- [docs/play-ui-contract.md](docs/play-ui-contract.md) — 桌面 UI 与地图投影接口
- [docs/playable-demo-design.md](docs/playable-demo-design.md) — Demo 六个模块及其边界
- [docs/handoff-spatial-and-world-basis.md](docs/handoff-spatial-and-world-basis.md) — 交接：哪些做完、哪些没做
- [docs/world-basis-and-history.md](docs/world-basis-and-history.md) — 世界基础与历史能恢复什么、不能恢复什么
