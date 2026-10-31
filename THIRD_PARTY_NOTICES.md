# 第三方来源与许可清单（THIRD PARTY NOTICES）

本文件记录 TextingDream（织梦）仓库里**不属于本工程自有代码**的内容、它们的来源与许可。

- 本工程**自有代码**按根目录 [LICENSE](LICENSE) 的 MIT 许可发布。
- **MIT 不适用于本文件列出的任何第三方内容**，也不构成对这些内容的重新授权。
- 本文件只陈述**来源与许可事实**（尽量给原文引用与可核对的值），
  **不是法律意见**，不做任何许可结论或保证。遇到边界不清的地方，本文件写“未核实”，不编结论。

最后核对：本轮文档交付时（见 §7 的核对记录）。

---

## 1. civ-atlas（地图基础，AGPL-3.0-only）

| 项 | 值 |
|---|---|
| 项目 | civ-atlas（“文明地图”世界生成器） |
| 作者/版权 | © 2026 guaner-334 |
| 上游 URL | <https://github.com/guaner-334/civ-atlas> |
| 固定 commit | `0939c5f1622a5e45cfc16f645ea3845993ab3985`（`package.json` version `1.3.0`） |
| 许可声明 | `package.json`: `"license": "AGPL-3.0-only"`；`LICENSE` = GNU Affero General Public License v3（34 523 B）全文 |
| 在本仓的位置 | `external/civ-atlas/`，**整个目录被根 `.gitignore` 忽略，不进入主仓** |
| 重建方式 | `docs/civ-atlas-install.md`（官方 codeload tar 快照 + 本仓补丁） |

上游 README「许可」节原文摘录（`README.md:200`、`README.md:202`）：

> 代码以 GNU AGPL-3.0（仅第 3 版）发布，© 2026 guaner-334。…将修改后的版本作为网络服务提供给他人使用时，
> 也必须以同样的协议公开修改后的完整源代码。
>
> 用这个工具做出来的世界…都归你所有…AGPL-3.0 只约束代码本身，不约束用它生成的地图和文字。

### 1.1 分发时的义务（按分发实际情况说明，不做法律绝对保证）

- 只要分发包含 **civ-atlas 源码或其修改版本**（例如把 `external/civ-atlas` 连同改动一起打包给出），
  就应同时提供 **AGPL-3.0-only 的完整对应源码**、保留上游 `LICENSE` 原文与版权声明，并标明改动。
- 如果把**修改后的版本作为网络服务**提供给别人使用，上游 README 要求以同样协议公开修改后的完整源代码。
- 本仓库把这部分拆成可重建的两半：**未改动的上游**按固定 commit 重新下载，**改动**放在
  `docs/civ-atlas-patch/`（三个文件 + AGPL 原文）。这样“对应的完整源码”始终可得。
- **本仓主仓不含 civ-atlas 源码**（`external/` 被忽略），所以克隆本仓库本身不会把 AGPL 代码带进来；
  但一旦你按安装文档把它装进 `external/` 并**再分发**，上面的义务就是你自己的了。
- 上述是对上游原文的转述与工程安排，**不构成法律意见，也不保证在任何法域下充分**。

### 1.2 本工程与上游的关系（工程隔离，不是 license 结论）

**两条路，隔离程度不同，分开说：**

1. **Python 服务（`app/`）↔ civ-atlas：不 import，只走文件。**
   `app/` 与上游不互相 import，只通过**文件**交换数据（导出的 `.civsnap`）。
   本工程自己写的解析器（`app/civ_atlas_snapshot.py`）只读写这些文件，不复制、不 vendor、不 fork 上游源码。
2. **原生地图宿主（`src/dream/*`）：直接 import 上游模块。**
   `bridge.ts` import `gen/snapshot`、`gen/raster`；`host.tsx` import `render/export`；
   `landOverlay.tsx` import `ui/mapWrap`、`render/globe`。它跑在**浏览器里**、用上游自己
   的解码器 `readPart`/`unpackValue` 与铺像素 `rasterize`，并把上游 `drawMapTerrain`/`drawMapCiv`
   当作唯一的画法。这些文件因此属于**修改后的上游版本**（AGPL-3.0-only），
   随上游完整源码一起提供（`docs/civ-atlas-patch/files/src/dream/` + `external/civ-atlas`）。

两者都不把本仓整体改成 AGPL：`app/`、`app/static/`、`tools/`（除宿主台本）仍是本工程独立代码。
**这是对工程事实的描述，不是许可结论。**

---

## 2. `docs/civ-atlas-patch/`（对上游的改动，按 AGPL-3.0-only 处理）

这个目录是为了“重建一份逐字相同的 civ-atlas 树”而必备的，**不是本工程自有代码**。

| 文件 | 相对上游 | SHA-256 | 许可处理 |
|---|---|---|---|
| `files/index.html` | **修改**（新增一个 `<script>` 标签） | `2415B55910D339343AC6D4D20B235B1DAC7FC1FFD7BE0991F80A23497D2E3131` | **来自上游的完整替换文件**，按 **AGPL-3.0-only**。**不能以 MIT 重新授权** |
| `files/dream-export-entry.js` | 新增 | `70EFB8A71F32EDD2427B34C6C66902BAAAC97BFFA933A4D0DEC0EF54E9BE3895` | 见下面的出处说明 |
| `files/public/dream-export-tool.js` | 新增（与 `tools/civ_atlas_export.js` **逐字节相同**） | `2264D2000ED1A26BD82DB2BE75241B6EB13F323F059B67BD3B533D4A3FEF8A67` | 见下面的出处说明 |
| `files/src/dream/{bridge,host,entry,landOverlay}.ts(x)`、`landOverlay.css` | 【实】新增（本工程写，**直接 import 上游模块**） | 见 §2.3 的实算清单 | **修改后的上游版本 → AGPL-3.0-only** |
| `files/vite.dream.config.ts` | 【实】新增（本工程写） | 见 §2.3 | 同上 |
| `LICENSE` | 新增（上游原文副本） | `0D96A4FF68AD6D4B6F1F30F713B18D5184912BA8DD389F86AA7710DB079ABCB0`（34 523 B） | **GNU AGPL-3.0 全文**，与 `external/civ-atlas/LICENSE` 逐字节相同 |

### 2.3 原生地图宿主的四个源码（逐字节镜像）

这四项与其他补丁一样，`docs/civ-atlas-patch/files/` 里的副本与 `external/civ-atlas/` 里的
当前文件**逐字节相同**（`tests/test_civ_native_contract.py` 的
`test_dream_sources_are_mirrored_in_the_patch_directory` 每次都会核这一条）：

| 文件 | 说明 |
|---|---|
| `src/dream/bridge.ts` | 取原件 + 切 CASNAP01 + 逐块校验 + 上游 `unpackValue`/`rasterize` |
| `src/dream/host.tsx` | 地图主画面（上游 `drawMapTerrain`/`drawMapCiv`）+ 挂载叠加层 |
| `src/dream/entry.tsx` | 独立构建入口 `mountDreamHost(el, {mode})` |
| `src/dream/landOverlay.tsx` / `.css` | 建筑范围/用地规划叠加层 |
| `vite.dream.config.ts` | 独立构建配置（仓库根也有一份副本） |

### 2.1 来源范围标识（哪些是上游、哪些是我们加的）

- **上游原有、我们改动过的：** `index.html`。它是上游文件的**完整替换**，内容绝大部分仍是上游代码，
  因此整个文件按 AGPL-3.0-only 分发，**不得删除或替换上游版权/许可声明**。
- **本工程新写的：** `dream-export-entry.js`（右下角按钮入口）与 `dream-export-tool.js`（IndexedDB 只读导出器）。
  两者源码头部都自带说明：原创、不 import 上游模块。但它们**与上游同仓分发**（必须放进上游目录才能运行），
  所以**在本目录下按 AGPL-3.0-only 处理**更保守。

### 2.2 关于「原创的只读导出器是不是 MIT」——**需要逐文件核对出处，不做统一宣称**

- 事实：`tools/civ_atlas_export.js` 与 `docs/civ-atlas-patch/files/public/dream-export-tool.js`
  **逐字节相同**（同一个 SHA-256），源码头注释声明“本工程原创代码，只调用浏览器 IndexedDB API，
  不 import、不复制上游源码”。
- 事实：`dream-export-entry.js` 同样是新写的入口文件，头部注明“本工程原创代码”，不 import 上游模块。
- **未逐行比对过**这两个文件是否含有从上游抄来的片段（例如字符串、容器字节序约定等）。
  **本文件不把“声明原创”直接当成“已核实无上游代码衍生”**，也不把“放在 AGPL 目录下”
  直接当成“必然衍生”。
- 结论口径：
  - 本工程**不**对这两个文件主张 MIT；在 `docs/civ-atlas-patch/` 内一律**按 AGPL-3.0-only 处理**；
  - 若将来要单独把它们移到 MIT 范围，需先做逐行出处核对（谁写的、有无上游片段），
    **本轮没有做这个核对，因此不宣称它们是 MIT**。
- 兜底：该导出器也可以完全不放进上游目录使用（在上游页面 Console 直接粘贴），
  那种用法下它不进入上游源码树；**这仍然不是法律结论**。

### 2.3 为什么这里不复制上游整棵树

`external/` 被忽略（1895 个文件 + 节点依赖）。可重建的三样东西都落在仓里：固定 commit + 包 SHA-256、
本目录的补丁、安装文档。**上游 `LICENSE` 全文已随本目录提供**，不需要读者再去找。

---

## 3. civ-atlas 自带的第三方依赖（随上游分发，不入本仓，各按自带许可）

下列内容由 civ-atlas 引入（`external/civ-atlas/package.json`、`public/fonts/`），**本仓库不含有它们**，
但如果你在 `external/civ-atlas` 里装了依赖或把其产物分发出去，它们的 notice 要跟着保留。

| 内容 | 版本/文件 | 许可（上游原文所述） | notice 文件 |
|---|---|---|---|
| react / react-dom | 18.3.1 | MIT（npm 包自带） | 各包内 `LICENSE` |
| d3-delaunay | 6.0.4 | ISC（npm 包自带） | 包内 |
| simplex-noise | 4.0.3 | MIT（npm 包自带） | 包内 |
| uqr | 0.1.3 | MIT（npm 包自带） | 包内 |
| **mediabunny** | 1.61.3 | **MPL-2.0（未修改）** | 包内 |
| vite / typescript / vitest / tsx / playwright / pngjs / subset-font | 见 `package.json` devDependencies | 各自许可（npm 包自带） | 包内 |
| 字体：霞鹜文楷 GB Medium、Noto Serif SC（500/700） | `public/fonts/*.woff2`（子集） | **SIL OFL 1.1** | `public/fonts/OFL-LXGW-WenKai-GB.txt`、`OFL-Noto-Serif-SC.txt`、`SOURCES.txt` |
| `public/portraits/` | 上游头像素材 | 上游 README 记为 **CC0 1.0** | 上游 README |

- 上游 README:204 的原话是「第三方依赖各有许可（MIT / ISC / Unlicense；导出视频用的 mediabunny 是 MPL-2.0，
  未作修改）；字体使用 SIL Open Font License 1.1」。
- **字体子集的注意点**：霞鹜文楷的许可附加条款允许为网页字体裁剪/转成 WOFF2 后沿用原名
  （见 `SOURCES.txt:3`）。**不要把 OFL 字体以 MIT 再分发**，也不要删除其许可证文件。
- 上面每一行都以**各包自带的 `LICENSE` / notice 为准**；本表不替代它们，也不重新授权它们。

---

## 4. 本工程直接使用的第三方组件（Python 运行时）

| 包 | `requirements.txt` 约束 | 本机实测版本 | 许可（该包元数据） |
|---|---|---|---|
| fastapi | `>=0.115` | 0.141.1 | MIT（`License-Expression: MIT`） |
| uvicorn | `[standard]>=0.30` | 0.53.0 | BSD-3-Clause（`License-Expression`） |
| pydantic | `>=2.8` | 2.10.3 | MIT（classifier `License :: OSI Approved :: MIT License`） |
| httpx | `>=0.27` | 0.28.1 | BSD-3-Clause（`License: BSD-3-Clause`） |
| jinja2 | `>=3.1` | 3.1.6 | BSD（classifier `License :: OSI Approved :: BSD License`） |
| pillow | `>=10` | 12.0.0 | MIT-CMU（`License-Expression: MIT-CMU`） |
| python 本体 | `>=3.11` | 3.11.11（开发机） | PSF License |

可选的开发依赖（不进运行时）：`pytest`（MIT）、`ruff`（MIT）。
上述许可取自各已安装包的分发元数据（`importlib.metadata`），**以各包随附的许可文件为准**。
它们通过依赖安装获得，**不在本仓库内**，也不因本仓 MIT 而改变许可。

---

## 5. 数据与地图素材（`assets/maps/`）

| 内容 | 来源 | 许可 / 状态 |
|---|---|---|
| `world.svg`、`ne_50m_*.geojson`、`natural-earth-land.geojson` | Natural Earth（1:110m / 1:50m） | **公共领域（Public domain）**，见 `assets/maps/SOURCE.md` |
| `earth_relief_10m_g.grd`、`world-hypsometric.png` 及其 source.json | GMT IGPP Earth Relief 10 arc-minute（SRTM15+V2.7 降采样） | 按其数据门户条款，见 `HYPSOMETRIC.md` 与 `world-hypsometric-source.json` 的 `license_documentation`；**10 角分，仅作测试底图，不用于精细测绘** |
| `world-detailed.svg` / `world-terrain.svg` | 由上述数据转换 | 同上，随数据来源 |

---

## 6. 内容素材（本工程原创，仍按 MIT）

- `docs/human-encyclopedia/`、`docs/element-catalog/`、`docs/playable-demo/character-traits.json` 等候选素材库：
  **本工程组织与撰写的设计文字**，随本工程 MIT。
  但其**事实性内容全部 `review_status: needs_review`，没有做过逐条事实核验**；
  其中的外部参考链接（FAO / 植物园 / 博物馆 / USGS 等）只表示来源，不对第三方内容主张任何权利。
- `StoryPackage/`、`character_packages/` 下的故事包与角色包：**本工程原创设定文字**。
- 上述内容若引用第三方文本、图片或数据，**该部分的许可仍归原权利人**，MIT 不覆盖它。

---

## 7. 核对记录（本轮，可重跑）

| 核对项 | 命令 | 结果 |
|---|---|---|
| 三副本导出器一致 | `Get-FileHash tools\civ_atlas_export.js, docs\civ-atlas-patch\files\public\dream-export-tool.js, external\civ-atlas\public\dream-export-tool.js` | 三个都是 `2264D200…8A67` |
| `index.html` 补丁与已打补丁的树一致 | 对比 `external\civ-atlas\index.html` 与 `docs\civ-atlas-patch\files\index.html` | 相同（`2415B559…3131`），797 字符（UTF-8、LF） |
| 入口文件一致 | `Get-FileHash docs\civ-atlas-patch\files\dream-export-entry.js, external\civ-atlas\dream-export-entry.js` | 都是 `70EFB8A7…3895` |
| 补丁目录 AGPL 全文 | `Get-FileHash external\civ-atlas\LICENSE, docs\civ-atlas-patch\LICENSE` | 都是 `0D96A4FF…BCB0`，34 523 B |
| 宿主五个源码与镜像逐字节相同 | `python -m unittest tests.test_civ_native_contract.PackagingTests.test_dream_sources_are_mirrored_in_the_patch_directory` | 通过（`bridge.ts` `DC74E7FB…` / `host.tsx` `914AD518…` / `entry.tsx` `8D79BC83…` / `landOverlay.tsx` `D1D6BFA6…` / `landOverlay.css` `2CDB5E4D…`） |
| 宿主真行为（数据桥 + 真浏览器） | `python -m unittest tests.test_civ_native_contract` | 20 项通过（真实 4.6 MB 样本；非 secure 上下文四条拒绝路径全正确） |

关于 `index.html` 的改动量：`external/civ-atlas` 里的是**已打过补丁的树**，所以它与补丁目录里的文件
逐字节相同，这只能证明“补丁文件与已应用的树一致”，**不能反推出原始上游文件的行数**。
可核的事实是：补丁版文件 797 字符（UTF-8、LF），比上游多出的内容只是新增了一个
`<script type="module" src="/dream-export-entry.js"></script>` 标签（紧跟在 `src/main.tsx` 之前）。
旧文档写的“+4 行”与本次实测不一致，本次**不声称具体改动行数**，只说“新增了一个 `<script>` 标签”。

---

## 8. 本文件明确不做的事

- 不代替任何许可原文，不重新授权任何第三方内容，不给法律结论或保证。
- 不把“在 AGPL 目录里”直接等同于“必然衍生”，也不把“源码写着原创”直接等同于“已核实无衍生”。
- 不声称本工程对上游生成地图/文字的权利主张已被法律确认。
