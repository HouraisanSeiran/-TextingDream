# 世界基础与历史融合：只读调研结论 + 相位方案

只读调研对象：`external/civ-atlas`（commit `0939c5f1…`）的 `src/gen/civ/types.ts`、`src/gen/snapshot.ts`，
以及我们自己已真实导出的一份 `.civsnap`（4 609 307 B，`map`/`eras`/`civ` 三块）。

**本文不改任何代码，只回答「能恢复什么、不能恢复什么、按什么接口分阶段做」。**

---

## 1. 上游历史数据到底是什么（实读结论）

`Civ`（`src/gen/civ/types.ts`）不是一个「逐年快照」，而是**一份终态 + 一条事件流 + 若干检查点**：

| 字段 | 语义 | 能否回溯到任意年 |
|---|---|---|
| `endYear` | 推演截止年（我们那份是 3000） | — |
| `culture: Int16Array` | **endYear 时**各州民族 | 只有终点，不是逐年的 |
| `polity: Int16Array` | **endYear 时**各州国家 | 同上 |
| `checkpoints: {year, culture, polity}[]` | 每 N 年一个**全量配色快照** | **可以**，但只到检查点粒度 |
| `annals: Annal[]` | 按年份排好的史事（立国、宣战、攻占、灭亡、迁都、分裂、合并…） | **可以**按年筛 |
| `log: ChangeLog` | 逐格变更日志（民族/国家层，带 year） | **可以**按年回放 |
| `settlements[]` | 城（含 `ended`、`capitalSpans` 等**带年份的区间**） | **可以**问「某年这座城在不在、人口多少」 |
| `polities[]` | 国家（`founded`、`capital` 变动史） | **可以**问「某年这个国家存在吗、首都在哪」 |
| `people[]` | 人物（生卒、在位） | **可以**按年筛存活者 |
| `religion` | 信仰/国教/教派（带年份事件） | **可以**按年筛 |
| `routes` / `places` | 道路与地名 | 部分带年份 |

**关键结论**：
1. **「第 N 年的样子」是可算的，但不是现成字段**：终态数组只给 endYear；要第 N 年必须
   ①取 `checkpoints` 里 ≤N 的最近一个快照，再 ②把 `log` 里 (checkpoint.year, N] 的变更叠上去，
   或 ③直接用 `annals` 过滤出 ≤N 的事件当「历史事实清单」。
2. **绝不能把 endYear 的城市直接当成基准年的城市**。城有 `ended`、有名有姓的 `capitalSpans`，
   这些都是带年份的，必须按基准年过滤；不过滤就会把「后来才建/早已毁掉」的城投到过去。
3. **`eras` 块不是历史**：它是「地形大事之后各段世界」+ 原段键（`snapshot.ts:9`），
   属于地形演化，与文明史无关。我们那份 `eras` 只有 190 字节，说明没有地形大事。

## 2. 版本化世界基础：字段映射（全部来自真实 manifest，不臆造）

一份导入能稳定拿到的、可当「世界基础身份」的字段：

| 世界基础字段 | 真实来源 |
|---|---|
| `world_id` | `manifest.world.id`（我们那份 `wmvrosdrr8awsz` 这类） |
| `generator_version` | `manifest.snapshot.generator`（=45） |
| `snapshot_format` | `manifest.snapshot.format`（=1） |
| `recipe`（配方指纹） | `manifest.snapshot.recipe`（已含地形种子/文明种子/年数等全部输入） |
| `terrain_seed` | **不在 manifest 顶层**，需从 `recipe` 或存档读；`.civsnap` 只带 fingerprint，**这一点必须如实标「未直接提供」** |
| `civ_seed` | 同上（`recipe` 里含，但不单独暴露） |
| `content_sha256` | 我们算的整文件 SHA-256 |
| `part_sums` | 每块 `sum`（上游对压缩前字节算的 SHA-256） |
| `exported_at` | `manifest.exported_at` |
| `extractor` | `manifest.exported_by`（我们自己的导出器标识） |

**诚实边界**：`terrain_seed` / `civ_seed` 在 `.civsnap` 里**只有 recipe 指纹**，没有明文字段。
要么去读上游存档文件（含 `params.seed` / `edits.civSeed`），要么就只能记 recipe。
**不能声称「已从原件读出种子」**。

## 3. 取样接口设计（先解决结构阻塞，再谈融合）

### 3.1 阻塞（已量化）
本网格 `mesh.n = 34097`；按容器声明的 `radius = 6371.0088 km`，
单格 = `4πR²/n` ≈ **14 959 km²**；而取样窗最小 3 格（且必须 ≥3 cells）→ 最小 **≈44 878 km²**，
`TownInput.terrain.area_km2` 上限是 **20000 km²**。
→ **绝大多数陆区取样都必然超标**。这不是「换个错误提示」能解决的**结构性冲突**。

### 3.2 方案：**环境取样** 与 **城镇腹地** 分离（不自动 clamp、不改星体半径）

```
POST /map-imports/{id}/sample            # 环境：仍按真实 mesh 尺度
  → area_km2 = 取样格覆盖的干陆地（真实值，可能远超 20000）
  → 不再因面积拒绝；只做「中心必须干陆地」与「干陆地占比」检查

POST /map-imports/{id}/town-input        # 城镇：作者显式给腹地
  author.hinterland_km2                  # 必填，0.5…20000，作者声明
  → 校验 hinterland_km2 <= sample.dryland_km2（不能超过所选干陆地覆盖）
  → TownInput.terrain.area_km2 = hinterland_km2（标 author_defined）
  → 记录里写清：这是**作者声明的有效腹地**，不是上游测量值
```

**明确不做**：不把 20000 当默认值自动 clamp（那等于编一个不存在的耕地）；
不让用户改 `radius_km` 去凑阈值（那会改变世界尺度）；不改 `GRAIN_MIN_ARABLE_KM2` 等经济常数。

> 若将来上游能导出**精细多边形边界**，可以改用其真实面积；在那之前，腹地只能是作者声明值。

## 4. 分阶段方案（每阶段可独立验收）

### 相位 A（本轮已做，待你审）
取样语义：中心必须干陆地、湖/海/陆分列、水面不计入面积、`span_km` 用真实格间距离、
高度图无水体数组时标 `water_known=false`。**测试 38 项全绿**（新增 5 项水体语义）。

### 相位 B（下一步，小接口）
1. `sample` 返回 `dryland_km2 / lake_km2 / ocean_km2 / cell_area_km2 / widest_pair_km`；
2. `town-input` 增加 `hinterland_km2`（作者声明 + ≤干陆地校验），`area_km2` 从此取它；
3. UI：选点后显示「该窗格干陆地 X km²，请填有效腹地（0.5–20000）」。
**测试点**：腹地缺省被拒、>干陆地被拒、合法值通过并标 `author_defined`、环境取样仍返回真实大值。

### 相位 C（世界基础版本化）
把 §2 的字段落成一份 `world_basis` 记录（含 `source_pin`：commit + sha256 + part sums + generator），
挂到导入记录上；**旧旅程固定用旧版本**，重导不覆盖。

### 相位 D（历史基础：只到「事件清单 + 检查点回放」）
1. 读 `civ` 块：`annals` 按年过滤 → **历史事实清单**（国家/城市/民族/信仰候选）；
2. `checkpoints` + `log` 回放 → **基准年的政区/民族快照**；
3. **不能**把 endYear 的 `settlements/polities` 直接当基准年状态；
4. 作者逐条审阅后才「固定」成故事包快照；
5. 事实与知情分离：编年史是作者侧事实，**不自动变成玩家常识**；
6. 上游 AI 扩写的史书**单独标记**，不等于结构化事件。

**明确不做**：不做经营 tick、不改经济算法、不动 `data/`/百科，
不把最终年状态冒充基准年。

用户已确认以 civ-atlas 为世界地图基础，并明确要求删除织梦原有的 `world_mapgen/`；该独立模块及其自产输出、测试已移除，不再作为当前入口。Terragenesis 工作区不受影响。

## 5. 需要你确认的两点
1. **腹地（hinterland_km2）由作者填**是否可接受？这是唯一不编造数据的办法。
2. `terrain_seed`/`civ_seed` 只存在于上游**存档**（`params.seed`/`edits.civSeed`），
   `.civsnap` 里只有 recipe 指纹。要不要把「读存档拿种子」也纳入下一阶段？
   否则世界基础只能记 recipe + generator + sha256，并**明确标注种子未直接提供**。
