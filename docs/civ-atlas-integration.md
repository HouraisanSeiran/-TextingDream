# civ-atlas 地形接入：实测契约、许可边界与适配设计

更新：2026-10-28。本文只记录**已从上游源码实读核对**的事实，以及本工程据此实现的有界适配器。
凡本文没有写「已实读」的内容，都不作为实现依据。

上游：<https://github.com/guaner-334/civ-atlas>
实测版本：`main` @ `0939c5f1622a5e45cfc16f645ea3845993ab3985`（2026-10-28T04:06:32Z，提交信息 `chore: 两个最慢的单测文件按内容拆开…(#334)`）。
源码只下载到会话临时目录（`temp://scratch/civ-atlas/`）用于阅读，**没有**执行、没有安装依赖、没有放进本仓库。

---

## 1. 结论（先说能做什么、不能做什么）

| 上游产物 | 是否可离线解析 | 能得到什么 | 本项目处置 |
| --- | --- | --- | --- |
| **16 位灰度高度图 PNG**（导出菜单「高度图 16 位」） | **可以**（格式已实读，见 §3） | 全球等距圆柱的**海拔（米）** + 海/陆掩码 | **实现导入适配器**（本文 §6） |
| 8 位高度图 PNG（Azgaar 刻度） | 可以，但有损 | 海拔只能反推、且依赖非线性指数 | 拒收，提示改用 16 位 |
| 存档文件 JSON（「存成文件」） | **不可以** | 只有 `seed + params + edits`，**不含地形** | 拒收，见 §4 |
| 浏览器内「原件」二进制 Snapshot | 不可以（不是导出物） | 内部 Float32 数组（含气温/降水） | 无法取得，见 §4 |
| 地图图片 / 图例 / 编年史 / 视频 / 故事长图 | 是图片与文本 | **没有逐格数值** | 不使用 |
| 气温、年降水、biome、物产、河流湖泊、cell id、势力、城镇 | **没有任何文件导出** | —— | **标记为缺失**，不臆造，见 §5 |

一台机器上只要能读到一张 16 位高度图 PNG，本项目就能据此产出一份**可校验、可溯源、字段级标注来源**的 `TownInput` 草稿，并走现有城镇管线生成/发布/采纳。**气温与降水不由地图提供**，必须由作者给值或显式选择「估算」，否则拒绝生成。

---

## 2. 许可边界（依据原文，不推断）

证据：

- `LICENSE`（34 523 字节）= GNU **Affero** General Public License **Version 3, 19 November 2007** 全文。
- `package.json`：`"license": "AGPL-3.0-only"`，`"version": "1.3.0"`，`"private": true`。
- `README.md:200`：「代码以 **GNU AGPL-3.0**（**仅第 3 版**）发布，© 2026 guaner-334。…**将修改后的版本作为网络服务提供给他人使用时，也必须以同样的协议公开修改后的完整源代码**。」
- `README.md:202`：「用这个工具做出来的世界（起的名字、干预、改过的地形、标记和人物）、导出的地图图片、AI 为你写的书，都归你所有，我们不主张任何权利，可以自由使用，包括商业用途。**AGPL-3.0 只约束代码本身，不约束用它生成的地图和文字**。」
- `README.md:204`：第三方依赖各为 MIT / ISC / Unlicense，`mediabunny` 为 MPL-2.0（未修改），字体为 SIL OFL 1.1。

本项目据此定下的边界：

1. **适配器是独立原创代码**：只解析作者从 civ-atlas **导出**的文件（数据产物），不复制、不 vendor、不 import、不 fork 上游任何源码，不链接其运行时。依据 `README.md:202`，生成出来的地图数据不受 AGPL 约束。
2. **本仓与既有产物继续按现状发布**，不因为接入 civ-atlas 数据而整体改许可证。civ-atlas 代码本身不进入 `app/`，适配器与上游通过**文件**交换数据。**这是工程隔离的描述，不是法律意见，也不构成任何许可结论。**
3. **不在 `app/` 里执行上游代码**：不 `pnpm install`（在 `app/` 范围内）、不跑其 TS/Worker、不在 `app/` 引入 Node 运行时依赖。
4. **上游本体单独安装并保留完整源码**：`external/civ-atlas`（见 `docs/civ-atlas-install.md`），按 AGPL-3.0-only 处理，随附 `LICENSE` 原文、改动账本 `SOURCE-CHANGES.md`、可重建补丁 `docs/civ-atlas-patch/`。**修改后的完整源码随仓可提供。**
5. **不冒名**：本项目**没有**重新实现 civ-atlas 的生成算法。不会出现「同一个 seed 用 Python 自己算一遍，算出另一张图冒充上游地图」。适配器只做：读文件 → 校验 → 单位换算 → 局部取样 → 标注缺失。

---

## 3. 已实读的 16 位高度图导出格式（实现依据）

来源：`src/gen/heightmap.ts`、`src/gen/png.ts`、`tests/export.test.ts`（同 commit）。

### 3.1 文件形态（`src/gen/png.ts:136-168`）

- PNG，签名标准；第一个块 `IHDR`，之后若干 `tEXt`，**一个** `IDAT`，`IEND`。
- `IHDR`：`bitDepth` 8 或 16；**`colorType = 0`（灰度）**；compression 0、filter 0、**interlace 0（无隔行）**（`png.ts:143-147`）。
- 16 位像素**大端序**（`png.ts:66-71`，PNG 规范）。
- 每行用 PNG 五种滤波（0 无 / 1 Sub / 2 Up / 3 Average / 4 Paeth）里「字节绝对值和最小」的那种（`png.ts:78-124`）。→ **解码器必须实现全部五种滤波**。
- `IDAT` 为 zlib/deflate 流（`CompressionStream('deflate')`，`png.ts:128-131`）。
- `tEXt` 块为 Latin-1（非 Latin-1 字符替换为 `?`，`png.ts:50-57`）；键值对以 `0x00` 分隔。

### 3.2 语义（`src/gen/heightmap.ts:1-30, 57-109`）

- 投影：**全球等距圆柱**，宽高比 2:1；纬度沿纵向均匀，**上边 = 北纬 90°，下边 = 南纬 90°**；**正中是 0° 经线**；最右列与最左列相邻（东西无缝）。
- 尺寸与该世界「主图」的 raster 一致（`Raster.w`, `Raster.h`）。
- 16 位：整个世界的海拔**线性**铺满 `0–65535`：
  - `lo = min(minSea, -1)`，`hi = max(maxLand, 1)`（米）；`k = 65535 / (hi - lo)`；`S = round(-lo * k) = round(65535 * (-lo) / (hi - lo))` = **海平面（0 米）所在的灰度**。
  - 海拔换算：`elev_m = lo + gray / 65535 * (hi - lo)`。
  - 海（`water === 1`）灰度 `≤ S-1`；陆（含湖，湖取湖面高度）灰度 `≥ S+1`。`S` 本身不会被写出（`heightmap.ts:84-90`），所以**海/陆判定是精确的整数比较**，不靠海拔正负猜。
- `S`、`lo`、`hi` 写进 PNG 的 `tEXt` 块（`heightmap.ts:112-126`）：
  - `Software` = `Wenming Ditu (civilization map generator)`
  - `Description`（16 位）= `16-bit grayscale heightmap, equirectangular (latitude linear top to bottom), 2:1. Gray 0 = <lo> m, 65535 = <hi> m, linear. Sea level (0 m) = gray <S>; land is brighter, sea is darker.`
  - `Source` = `seed <N>`（仅当调用方传了 seed）
  - **注意**：`lo` / `hi` 在文本里是 `Math.round()` 取整后的值，原始浮点不可恢复 → 换算有 ≤1 米量级的取整误差（§6.3）。
- 同名 `.txt` 说明（`heightmap.ts:131-168`）另含：文件名、种子与参数串、尺寸、`minElev/maxElev`、逐级米数、换算公式。该文件是**可选**输入：有则作为作者声明的旁证收下，无则按 PNG 的 `tEXt` 走。

### 3.3 上游自己的不变量（`tests/export.test.ts:76-160`，已实读）

- 16 位 PNG 读回 `width/height = 2`、`depth = 16`、`colorType = 0`；
- 海像素灰度 `< S`，陆像素 `≥ S`（含湖）；`d16[0] = 0`、最高峰 `= 65535`；
- 同一世界每次编码一致（确定性）。

本适配器把上面每一条都当成**可测试的断言**，见 §9。

---

## 4. 为什么「完整存档」无法直接解析（实读结论）

`src/gen/savefile.ts:1-3`（文件头原文）：

> 存档文件(阶段 4):一个世界 = 种子 + 参数 + 用户的修改(gen/edits.ts 的 WorldEdits)。
> 同种子 + 参数 = 同一个世界,**所以不存地形、历史**,文件只有几 KB;读档时先按参数重新生成,再套上修改。

`SaveFile`（`savefile.ts:115-135`）字段全集：`app`、`format`、`generator`、`seed`、`params`、`edits`、`check`、`title?`、`view?`、`origin?`、`moment?`、`savedAt`。
`SAVE_FORMAT = 1`（`savefile.ts:113`），单文件上限 `MAX_BYTES = 8 MiB`（`savefile.ts:498`），`GENERATOR_VERSION = 45`（`src/gen/edits.ts:534`）。

→ 存档里**没有任何逐格数值**。要用它还原地形，只能跑它的生成器（Node 22 + pnpm + TS/Worker），也就是本仓库不做的那件事（§2.3）。因此：

- 存档 JSON **拒收**，错误信息里直接说明原因并指向「高度图 16 位」导出；
- 浏览器内「原件」`Snapshot`（`src/gen/snapshot.ts:1-33`：`SNAPSHOT_FORMAT = 1`，`map`/`eras`/`civ` 三块 Float32 结构体）**不是上游 UI 的导出物**：上游页面没有把它下载成文件的入口。但它确实含 `temperature` / `precipitation`（`src/gen/climate.ts`）。
  → 本工程钉的导出器 `tools/civ_atlas_export.js`（已在上游侧挂成右下角按钮，见 `docs/civ-atlas-patch/`）
  只读 IndexedDB 把三块 part 原样打包成 `CASNAP01` 容器，所以**气温/降水/biome 是可得的实测值**，由 `app/civ_atlas_snapshot.py` 读取。

---

## 5. 缺失字段与诚实标记

高度图**只有**海拔与海陆。下列 `TownInput` 字段**上游没有文件导出**，一律不得声称「读出来了」：

| TownInput 字段 | 处置 |
| --- | --- |
| `terrain.elevation_m` | **实测换算**（§6.3），带 ±误差 |
| `terrain.coordinates` | **实测**（作者选点，经度/纬度） |
| `terrain.area_km2` | **按取样窗真实球面面积计算**（需声明星体半径，§6.4） |
| `terrain.slope_deg` | **按取样窗梯度计算**，并标注这是「约 N km 尺度的区域梯度」，不是城镇尺度坡度 |
| `terrain.temperature_c` / `precipitation_mm` | **缺失**：作者填值，或显式勾选「按纬度带粗估」（§6.5）。默认拒绝 |
| `terrain.freshwater` / `soil_fertility` / `flood_risk` | **不从地图推导**（湖在高度图里与陆地同值，取不到淡水；土壤/洪涝上游无此字段）：作者给值，默认 `0.5/0.5/0.2` 且标注 `author_default` |
| `water.*` | 作者填。海格不能当水源（`source='none'` 时 `daily_capacity_l` 必须 0） |
| `resources[]` | **不导入**。上游的「物产」不是矿藏量，也没有勘探/技术/燃料/库存语义 → 矿藏只能作**候选**，`surveyed=false`，永不产出 |
| 河流/湖泊、cell id、biome、势力、城镇 | **不支持**。理由是上游没有这些字段的文件导出；`cell id` 是内部网格编号，导出物里不存在 |

---

## 6. 适配器设计（本项目新代码，不改上游）

模块 `app/map_import.py`（纯函数，无 FastAPI、不调模型）：

### 6.1 导入

```
POST /api/inner/map-imports        {format:'civ_atlas_heightmap_v1', png_base64, note_text?}
```
- 有界：`png_base64` ≤ 24 MiB（解码后 ≤ 18 MiB），`note_text` ≤ 4000 字符；`width*height ≤ 16 777 216`（4096×4096 等价上限，2:1 下即 ≤ 8192×4096）；`IDAT` 解压上限 = `(w*2+1)*h` 字节 + 1 MiB 余量（防压缩炸弹）。
- 严格：签名、`IHDR`（灰度/无隔行/位深 16/宽高>0/2:1）、每块 CRC、`IDAT` 解压长度精确匹配、`tEXt` 里 `Description` 必须可解析出 `lo`/`hi`/`S` 且 `lo < 0 < hi`、`0 < S < 65535`。
- 一致性自检：重算 `sea/land` 像素数与 `lo/hi` 灰度区间，要求「所有海灰度 < S」且「所有陆灰度 > S」（与上游不变量一致），否则拒收；`min(gray) = 0` 且 `max(gray) = 65535` 才认「线性铺满」，否则警告。
- 落地：PNG 按内容寻址存 `data/map_imports/<sha256>.png`；文档（`store.put('map_import', id, ...)`）只存元数据 + 有界统计 + 作者声明，**不存整图数组**。同内容重复导入 = 幂等（同 id，不重写文件）。
- 记录来源：`commit`（作者声明）、`generator_version`（作者声明，可空）、`seed`（PNG `tEXt`）、`png_sha256`、尺寸、`lo/hi/S`、单位语义、`note_text`、`warnings`。

### 6.2 选点取样（球面经纬度，不是 cell id）

```
POST /api/inner/map-imports/{id}/sample   {lon, lat, window_px}
GET  /api/inner/map-imports/{id}/preview.png      # 降采样 16 位灰图，给 canvas 显示
```
- `lon ∈ [-180, 180]`（越界按模回绕 180 圈，因为图东西无缝）、`lat ∈ [-89.5, 89.5]`（极点像素区不算）、`window_px ∈ [3, 15]` 奇数。
- 取样返回有界数字集：`elevation_m{min,max,mean}`、`sea_fraction`、`land_km2`、`area_km2`、`slope_deg{p50,max}`、`sample_span_km`、`uncertainty`、`missing[]`、`warnings[]`。
- **海格拒**：`sea_fraction ≥ 0.5` 直接拒绝（不能在海上建镇）；`> 0.1` 警告。
- 面积越界（`< 0.5` 或 `> 20000` km²，沿用 `TerrainSample` 的界）拒绝并提示调 `window_px`。

### 6.3 单位与换算（逐个写清）

| 项 | 换算 | 误差/说明 |
| --- | --- | --- |
| 海拔 | `elev_m = lo + gray/65535*(hi-lo)`，`lo/hi` 取自 `tEXt Description` 的**取整值** | 取整带入 ≤ 1.0 m；另 PNG 量化 1 级 ≈ `(hi-lo)/65535` 米。二者相加记作 `vertical_m` 误差，不隐瞒 |
| 海/陆 | `gray < S` 为海、`gray > S` 为陆（整数比较） | **精确**，不受取整影响 |
| 经纬度 | `lon = -180 + 360*(x+0.5)/w`，`lat = 90 - 180*(y+0.5)/h` | 像素中心；比上游 `latitudeAt` 差半个像素，记入 `horizontal_note` |
| 水平距离/面积 | 球面公式，半径取**声明的** `planet_radius_km`（默认 6371.0088，地球） | 上游 `WorldParams`（`src/gen/params.ts:9-30`）**没有半径字段**，导出物也没有 → 这是本项目声明的假设，写进记录，改了要重算 |
| 坡度 | 窗内相邻像素中心连线的高差/水平距，取梯度模长的 `atan` | 像素间距 ~20 km 量级（2048 宽时赤道 19.6 km/px）→ 只能算**区域坡度**，不是工地坡度 |

### 6.4 生成 `TownInput`

```
POST /api/inner/map-imports/{id}/town-input   {...selection + 作者字段 + climate_source}
```
- 产出 `TownInput`（`app/town_schema.py`），**不写库、不改正式 data、不自动 pointer**。
- `map.source = 'external_adapter'`（该枚举已存在，`town_schema.py:110`）、`map.input_version = 'civ_atlas_heightmap_v1'`、`map.coordinate_system = '等距圆柱全球经纬度（经度在前、纬度在后）'`、`map.scale = '取样窗 X 像素 ≈ N×M km（半径按 6371 km 假设）'`。
- 溯源写进 `notes`（≤600 字符，含 commit/seed/hash/换算式/缺失声明），完整溯源留在 `map_import` 文档里。
- 生成草稿复用现有 `POST /api/inner/towns`（`web.py:208-211`）+ 现有四阶段生成/发布/采纳，管线零改动。

### 6.5 气候的两种口径（默认拒绝）

| `climate_source` | 行为 |
| --- | --- |
| `missing`（默认） | 拒绝生成 `TownInput`，返回缺哪些字段 |
| `author` | 用作者填的 `temperature_c` / `precipitation_mm`，标 `author_supplied` |
| `measured` | 只用于 `.civsnap`：雨温/群系取自原件的逐格数组，标为上游生成器算出的值 |

**没有「按纬度估一下」这个选项**：本项目**不做**纬度带粗估，也不提供任何“我帮你填”的隐式默认值。
高度图导入若作者不填气候，就拒绝生成，而不是先给个数字再声称它来自地图。

**永不**把作者填的值或任何估算说成“从地图读出来的”。

---

## 7. 作者侧 UI（`app/static/map-import.js` + `app/static/map-tools.css`）

实际实现（不是设想）：

- 新页面「**地图工具**」（侧边栏◈ 地图工具）——地图占主画面，右栏才是操作与读数，不做落地页。
- 导入：文件框直接发裸 body 到 `POST /api/inner/map-imports`（带 token 头），`.civsnap` 与 16 位 PNG 自动分流。
- 图层：按钮由服务端 `stats` 决定能列出哪些——`.civsnap` 有高程/海陆/气温/降水/群系，高度图**只有**高程/海陆；
  图例跟随当前层；文案注明「该世界生成器算出的逐格数值，不是现实观测」。
- 预览：`fetch` + `X-TextileDream-Token` 头取 `blob` → `ObjectURL`（**token 不进 URL**），带序号防旧响应覆盖、
  `onload` 后才 `revokeObjectURL`。图片只是看的，数值只来自 `/sample` 与导入记录。
- 选点：点地图或填经纬度 → `POST .../sample` → 显示海拔区间、海面占比、面积、跨度、区域坡度、气温降水生物群系；
  面积明写「球面均分近似，不是精确地块面积」。
- 建镇：「创建草稿」→ `POST .../town-input` → 直接把返回的 `input` 交给现有 `POST /api/inner/towns`，四阶段/发布/采纳零改动；
  另给「去城镇创作 ›」入口，不靠包装 `showPage`（`towns.js` 也包了它，多层包裹会互相吞）。
- 窄屏：≤900px 单列、≤520px 再压一档；容器 `min-width:0`、图片 `max-width:100%`，实测 390px 无横向溢出。
- 不引入内联脚本，不引外部图标库（现行 CSP `script-src 'self'`）。

---

## 8. 导出器（已实装，见 `docs/civ-atlas-patch/`）

上游页面没有把原件下载成文件的入口，所以本工程在上游侧挂了一个只读导出器：

- `tools/civ_atlas_export.js`（本仓正本）：只读 IndexedDB `civ-atlas:results` 的 `results`/`heads`，
  把三块 part 原样打包成 `CASNAP01` 容器下载。不联网、不写库、不读 localStorage / API Key、不自动挑世界。
- `external/civ-atlas/public/dream-export-tool.js`：与上面**逐字节相同**的副本（SHA-256 可核）。
- `external/civ-atlas/dream-export-entry.js`：页面右下角小按钮，加载上面那个副本，走同样的 list/export。
- `external/civ-atlas/index.html`：只多一行 `<script>` 引用。**`src/` 未改。**

本文不实现该 bridge。

---

## 9. 测试计划（见 `tests/test_civ_atlas_import.py`，当前 34 项）

1. **跨语言容器契约**（真实导出器的偏移编码 ↔ Python 解析器）：定宽 offset 往返、旧整数 offset
   仍可读、payload 跨 9 999 999→10 000 000 字节（offset 位数变化）仍能解析、三块 part 各自可寻址。
2. **篡改拒收**：offset 尾部带垃圾、11 位短串、负数、布尔、未 8 字节对齐、越界、两块重叠 —— 一律拒。
3. **隔离**：导入写在临时库旁边，仓库 `data/map_imports` 一个字节都不多；公开摘要不含绝对路径。
4. **图层**：五层各自 PNG 有效、两两不同、不是同一张灰度图换标签；未知图层拒收。
5. **采样诚实性**：高度图 `climate=null` 且 `missing` 列气温降水；`missing`/`measured` 口径在
   不适用的数据上被拒；经度回绕与极点拒收；偶数窗格拒收。
6. **严格请求体**：未知字段、bool 冒充数字、字符串冒充数字、窗格越界、非法 commit 全部拒。
7. **事件循环**：故意放慢解析时，另一个读请求仍在 2 秒内返回（证明解析在 worker 线程）。

---

## 10. 融合方向（已由用户确认，**尚未实施**，不阻塞当前交付）

用户已确认：**civ-atlas 推演出的历史可以作为该世界的「历史基础」**。下面是据此记录的设计方向与边界，
供后续阶段实施；本轮只落实到「来源元数据能带上这些信息」，不改历史系统。

### 10.1 选什么、记什么
作者选定：**世界 + 历史分支 + 基准年份**。导入时必须留住：

| 元数据 | 来源 |
|---|---|
| 地形 seed | 上游 `params.seed`（`.civsnap` manifest 的 world/snapshot） |
| 文明 seed | 上游 `edits.civSeed` |
| generator 版本 | `snapshot.generator`（改变它就换一个世界） |
| 内容哈希 | 导出的 `.civsnap` SHA-256 + 每块 part 的 sum |

### 10.2 基准年份怎么用
- 基准年份**以前**的事件、政区、城市、民族与信仰，作为该世界的历史基础导入。
- 导入后**不在运行期继续由上游改写**：历史在那一刻冻结为「既定事实」。
- 基准年份**之后**的游戏时间由织梦自己接管（不再引用上游推演）。

### 10.3 事实与知情必须分开
- 编年史是**作者侧事实**，不会自动变成所有人的常识：谁在哪一年知道什么，仍由织梦的知识/传闻层决定。
- 上游的「AI 扩写史书」与**结构化模拟事件**不是同一等级的依据：前者是叙述，后者才可当史实；
  两者都要在记录里标明来源，不得混为一谈。

### 10.4 与已锁定设定的冲突
- 与已锁题材/元素冲突的条目，交由**作者逐条审核**，不静默新增未绑定的超自然或技术项。

### 10.5 重推历史 = 新分支
- 重新推演产生的是**新分支**，不覆盖已有旅程；
- 旧旅程继续绑定它当初那一版历史与故事包版本。

> 本轮**没有**实施任何一项；本节只是把方向与元数据要求固定下来，避免以后靠记忆重建。


---

## 10. 明确的「不做」

- 不 vendor、不 fork、不 import、不执行 civ-atlas 代码；不 `pnpm install`；不引入 Node 依赖。
- 不把存档 JSON 当数据源；不猜它的 `check`/`params` 能还原地形。
- 不用 Python 重实现生成器去「复现同一个 seed」。
- 不把高度图归一值当米（都是显式线性换算 + 误差）；不把河流/流量/矿藏当供水/库存/勘探结论。
- 不导入上游势力、城镇、人口，不建两套时间/人口权威。
- 不改 `data/`、不改正式故事包 pointer；导入全部落在 `map_import` + 城镇草稿。
- 不把整图塞进模型上下文：预览走降采样 PNG 给 canvas，取样只返回窗口统计。

---

## 11. 待作者/主代理确认

1. **星体半径假设**：默认按地球 6371.0088 km 折算面积与坡度（上游无半径字段）。若作者的世界尺寸另有设定，请在导入表单里改，记录会跟着变。
2. **气候口径**：默认「缺失即拒绝」。是否允许作者勾选纬度带粗估？（已实现为显式勾选，默认关。）
3. **是否需要逐格气温/降水**：需要则要先有 §8 的上游 bridge（AGPL 义务、由作者本机运行）。
