# 地形源适配层（DEM 换源 A1/A2）

> **历史适配说明（2026-11-08 整理）**：后来的读取契约是 [world-map-source-contract.md](world-map-source-contract.md)。本文是 2026-11-01 的换源笔记。

日期：2026-11-01。依据：Terragenesis `docs/handovers/rpg-world-dem-integration-20261101.md`。

## 范围

织梦是交接文档里的「另一工程（消费侧）」。本轮只做 A1–A2：

- **A1 独立适配层**：`app/terrain_source.py`。不 import、不运行 Terragenesis 代码，也不启动它的模型/GPU；按已公开的冻结格式自行复核身份后**只读**加载。数据位置由配置文件给出，**没有默认数据依赖**（未配置时目录为空，查询一律返回 `unprepared`）。
- **A2 只读查询**：点查询（双线性高程 + 最近样点分类）、半开矩形裁取、30 m 原生索引 ↔ 米坐标换算、多源目录（细源优先）。

**方向（用户 2026-11-01 确认）**：Terragenesis 世界生成将**替代 civ-atlas** 作为织梦地图基础，地图美化与玩法功能在织梦中完成。因此世界几何直接采用源产品的米制平面（X 东、Z 南、海平面 0），**不做球面/经纬度映射**，也不经 civ-atlas 的 16 位 PNG 高度图协议或 `raster.ts` 栅格化（后者会平滑、加噪、移岸线、刻谷并按 `height<0` 判海，会改变源地形）。本层**尚未接入**任何玩法与 UI。civ-atlas 接口（导入、宿主、API）保留为可选旧来源；旧 civ 存档**仅作测试夹具**，不把其文明数据迁移到新地形。A3（万公里板块骨架/5 km DEM）、A4（按需页队列）、A5（粗细水系约束）未做。

参考：Terragenesis `docs/handovers/rpg-world-dem-source-swap-advice-20261101.md`（高程/分类/有效性分离、床面≠湖面、栅格化改形、最小验收样例）。

## 支持的冻结产品

| kind | 格式 | 网格语义 | 分类 |
| --- | --- | --- | --- |
| `native-terrain-v3` | 目录：`manifest.json`（schema `new-world-terrain-v3`）+ `bed_m/valid_mask/ocean_mask/unknown_mask/closed_below_sea_mask.npy` | 首样点 = `origin_native_xz × 30` m，**不加半格** | unknown / ocean / closed_below_sea / land |
| `tectonic-macro-v2` | `product.npz`（schema `tectonic-frozen-product-v2`） | 格心 = `origin + (index+0.5)×cell` | ocean（连通海）/ closed_below_sea / land |

身份复核：manifest 规范 JSON（排序键、紧凑分隔符）的 SHA-256；native 去掉 `identity` 与 `source_path`，tectonic 去掉 `identity`。native 额外校验所用 5 个 `.npy` 的文件哈希，`climate_base` 等未加载文件列在 `unverified_files`；tectonic 校验所用两个数组的字节哈希（不重做板块材料账本验证）。

板块产品在源工程是双向周期平面；本层一律按**有限域**处理，越界返回 `out_of_bounds`，不把周期重复当成新大陆。负高程内陆洼地是 `closed_below_sea`，不算海洋。

## 状态码

`0 unprepared`（目录中无任何产品覆盖）· `1 out_of_bounds`（某一产品范围外）· `2 unknown` · `3 ocean` · `4 closed_below_sea` · `5 land`。高程在 unknown / 越界 / 未准备时为 NaN；双线性四邻任一为 unknown 时整点视为 unknown。

## 配置

```json
{"sources": [
  {"kind": "native-terrain-v3", "path": "D:/.../terrain-v3", "identity": "c751a09a…ffb72"},
  {"kind": "tectonic-macro-v2", "path": "D:/.../shaped-run-v4/product.npz", "identity": "b4c8bbdb…6af9"}
]}
```

`identity` 必填；相对路径按配置文件所在目录解析。环境变量 `DREAM_TERRAIN_SOURCES` 指向该文件后，`load_default_catalog()` 才会加载。示例：`docs/examples/terrain-sources.example.json`（本机路径，仅供参考，不随代码作为依赖）。

## 本机可用冻结样本（2026-11-01 实测）

- `terrain-v3`：4096²、30 m、首样点 (-61440, -61440) m，身份 `c751a09a6f02e8c336b6b9b8fb4b11b5dc67386e9a8470b0b1d90858bf1ffb72`；本次复算身份一致。仅 122.88 km 局部支撑域，**不能冒充万公里来源**；一阶段仍未完成，非最终图。
- 其父板块产品 `shaped-run-v4/product.npz`：160×128、10 km 格、1600×1280 km，身份 `b4c8bbdba29111b8c3ba3270e2f0d3a4fed3544655249fa07c506654b8ae6af9`；本次复算一致。

## 验证

```powershell
.venv\Scripts\python.exe -m pytest tests/test_terrain_source.py -q
# 可选：真实样本
$env:DREAM_TERRAIN_V3_FIXTURE='D:\codexwork\山川形意Terragenesis\.scratch\river-upgrade-20261101\terrain-v3'
.venv\Scripts\python.exe -m pytest tests/test_terrain_source.py -q
```

## 下一步

1. A3：在 Terragenesis 侧发布冻结的万公里板块骨架与 5 km 世界 DEM 后，按身份加入配置即可读取；本层已能读 `tectonic-frozen-product-v2`。生成本身属于源工程或需用户另行授权运行。
2. 在织梦内建地图渲染（分层设色/符号，复用 `app/static/map-art/` 资产）直接读本层，不经 civ-atlas 改形链；迁移城镇、道路、旅行等玩法的空间依据（旧 civ 存档的文明数据与新地形不兼容，需重建或明确仅作历史）。
3. 需要上游补齐：湖面高程/湖泊边界、河流中心线与稳定 ID、气候长期量（native-event 的两个 15 天事件不能当年降水）。
4. A4/A5 等待粗水系产品与按需页接口约定。
