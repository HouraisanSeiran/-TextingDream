# 地形算法台账（织梦 × Terragenesis）

更新日期：2026-11-12。范围：作者侧世界生成 + 玩家默认 `world_map_product`。civ-atlas 默认关闭（`TEXTILE_CIV_ATLAS=1` 开启）；实现隔离在 `app/civ_atlas/`。

相邻工程根目录：`../山川形意Terragenesis`（Windows 上与 `山川形意terragenesis` 同一路径）。重计算步骤默认用其 `runtime/venv/Scripts/python.exe`（见 `app/world_gen/web_jobs.py` 的 `TG_PYTHON`）。织梦服务解释器只跑 HTTP、atlas 渲染与轻量校验。

## 接入边界（织梦 × Terragenesis）

| 侧 | 负责 |
|---|---|
| Terragenesis | 板块 / 岛链 / 岛山 / 排水 / world_processes / 区域气候等物理与冻结产品写入 |
| 织梦 | 作业编排（`web_jobs`）、产物目录、`map_source` 统一读取、作者 UI、玩家雾图底图 |

单缝模块：`app/world_gen/terragenesis_bridge.py`（路径 / SHA / `probe` / 公开模块表）。岛链冻结策略：`ocean_island_adapter.FROZEN_V5_READER_STACK`（算法 `ocean-islands-volcanic-edifices-v5`）。气候侧车：`map_source` kind `terragenesis-regional-climate`（年均值）或 `SavedClimateMap`（月尺度）；玩家底图河流来自 fast 产品 `vectors.rivers`。

## 总览

```text
# pipeline=playable（默认，游玩草稿）
skeleton → islands → island-mountains → fast（无 world-processes）→ render → summary
    → 作者「导入到游玩世界地图」→ mechanics.map = world_map_product

# pipeline=full（作者完整链）
skeleton → islands → island-mountains → fast(+world_processes)
    → render → details → final-render → [可选 GPU] td + compare → summary
```

查询地图或旅程 API **不会**隐式生成地形。产物写入新目录（如 `artifacts/worldgen-jobs/web-<id>`），不覆盖旧冻结件。

## 阶段表

| 阶段 | 职责 | 织梦入口 | Terragenesis 模块 / 符号 | 典型产物 | GPU |
|---|---|---|---|---|---|
| skeleton | 有限板块骨架、大陆/海洋配额、脊网代理 | `tools/generate_world_skeleton.py` → `app/world_gen/skeleton.py` | `terrain_pipeline.tectonic`：`TectonicConfig`、`evolve`、`freeze`、`save_product` / `load_product` | `skeleton.npz`、`skeleton-run.json`；plate schema 含 `dream-world-skeleton-plate-v1`；单元格 10 / 20 / **40** km（≤2000 / ≤6000 / 万公里；矩形按最长边） | 否 |
| islands | 冻结远洋岛链；1km 资格计划侧车 | `app/world_gen/web_island_stage.py prepare` → `ocean_island_adapter.py` | `ocean_islands`：`PlateOceanSource`、`OceanIslandConfig`、`prepare_ocean_islands`、`save_product`；`ocean_island_consumers`：栅格/合成/TD 条件 | `ocean-islands/islands.npz`、`prepared.json`、`plan-*.npz` | 否 |
| island-mountains | 合格岛内陆 TD 山系或 CPU pending | `web_island_stage.py schedule` → `island_mountains.py` | `island_mountains`：`IslandMountainConfig`、`analyze_island_mountains`、`save_mountain_plan`、`peak_height_for_area`、`apply_peak_surface` | `island-mountains/world-input.json`、raw/derived local30 | 仅 `use_gpu` |
| fast | 2km 床面、岛合成、侵蚀保护、不规则图水文 | `web_island_stage.py fast` → `fast_relief.py`；CLI `tools/build_fast_relief.py` | `drainage`（`grid_mesh` / `route_graph` / `accumulate_graph`）；可选 `procedural_mountain_erosion.directional_detail`；`world_processes` | `terragenesis-fast-relief-v1` 产品目录 | 否 |
| details | 河段/湖口/河口续算 | `world_process_details.py` | `world_processes`、`world_process_detail`、`world_geology` | 细节产品目录 | 可选 |
| render / final-render | 图册 PNG | `tools/render_world_relief_atlas.py`（织梦解释器） | 不 import TG 算法核 | atlas 目录 | 否 |
| td / compare | 粗脊 TD 与 fast 走向对比 | `web_td_stage.py`、`td_fast_compare.py` | TD / torch（TG venv） | `td-dir`、`td-vs-fast.json` | 是 |
| summary | 身份与 `map_source` 可加载检查 | `web_jobs.summarize` | — | job 汇总 | 否 |

局部 30 m 另入口：`tools/prepare_local30.py`、`app/world_gen/local30.py`（显式 tile + 理由；只读 `request_local` 不生成）。

## 主线 vs 试验

| 类别 | 现行主线 | 试验 / 遗留（勿当默认世界源） |
|---|---|---|
| 岛链 | 新生成偏 v5 火山构筑产品；织梦消费经冻结 binding | v1–v4 仅 `load_product` 回放；`FROZEN_*_STACK` 管 reader SHA |
| 岛山 | `island-mountains-area-peaks-v3`；默认资格露海连通岛 **>25 km²** | 旧 100 km² / 2000 km² / 腹地宽度门槛为历史口径 |
| 世界层 | 2 km `fast_relief` + 不规则图排水 | 全域 30 m TD 世界层；D8 河网（已弃用） |
| 山体点缀 | 骨架 orogen 脊网 | `procedural_mountain_erosion` 冲沟点缀；TG `mountain_forms` 粗山带候选 |
| 运行地图 | 默认 `world_map_product`（`app.map_policy`）；无 map 时回退到 TG speed 产品；`civ_atlas` 需 `TEXTILE_CIV_ATLAS=1` | 天气：可用 `mechanics.weather` + 产品 elevation；平面米制≠lon/lat。道路：作者 `adventure.routes` 可用；`civ_routes`/陆网寻路未接 TG |

## 精度与流水线

作者 Web / API：

- `quality`：`speed`（**默认**）/ `balanced` / `precise`。控制 fast `spacing_m`，不改 `world_seed` 与骨架/岛身份。另在 `speed + playable` 下启用轻量图册：`--overview-only --width 1200`，保留总览与纯地形图，不批量渲染局部附页、预留空地演示和对比图。底层 DEM、河湖矢量与玩家地图数据不因此降精度。
- `pipeline`：`playable`（**默认**，游玩草稿）/ `full`（作者完整链）。玩家底图只读 fast 层；`playable` 跳过 `world-processes`、`details`、双份成图与世界级 TD。`balanced` / `precise` / `full` 保持完整图册行为。
- **分钟级目标**：优先 `speed + playable + use_gpu=false`，真实生成骨架、岛链和粗河湖，只简化作者图册。CPU岛山本来就记录为 `pending-gpu`，不是完成30m TD；显式 `use_gpu=true` 仍执行岛山TD，不会被速度档静默关掉。完整环境与GPU精细地形不承诺几分钟完成；5000/10000km耗时须另测。

| size_km | speed | balanced | precise |
|---|---|---|---|
| 1600 | 4000 m | 2000 m | 1000 m |
| 5000 | 8000 m | 4000 m | 2000 m |
| 10000 | 12000 m | 8000 m | 4000 m |

`POST /api/inner/worldgen/jobs/{id}/upgrade` 复用骨架与岛山，写出**新** fast 目录；同格距拒绝。玩家地图关联：成功任务点「导入到游玩世界地图」，或 `POST /api/inner/history/worldgen-map-link` → `mechanics.map.kind = world_map_product`。

### 岛群聚集布局（显式选择）

`POST /api/inner/worldgen/jobs` 新增 `island_layout: "old" | "clustered"`。省略仍为 `old`，既有世界和旧请求不静默改布局；新群岛候选使用 `clustered`。`options.island_layouts` 列出选择，`summary.world.island_layout` 读取已冻结的实际政策；upgrade继承来源布局，不按新quality重设。

- clustered对应TG `clustered-provinces-v1`，保留v5岛体/火山几何，显式声明5个热点活跃区、每区最多6条链、最多3条孤立链；区域不是圆形陆地，链尾可以沿板块运动方向离开区域。
- preset年龄上限300个离线步、链长上限600km、8个阶段、岛弧候选间距150km，洋中脊岛关闭；这些是游戏构图配置，不是已标定地质过程。热点/海山/岛弧分别统计，features不等于陆岛数。
- 当前同一万公里骨架实测：热点链232→33，清册1675→252（含41岛弧、140热点阶段、71海山），新岛准备8.63秒；世界10km格地形与河湖重新发布约114.85秒。复用旧骨架后准备+状态+世界阶段约125.21秒，不含从零骨架和出图；不是旧33分钟完整耗时的同内容无损倍率。
- 旧v5产品的完整manifest、identity及主保存局部query逐位相同后，才登记精确旧→新读取栈；不接受任意源码变化。旧世界原文件与身份保持不变，新地形另存于 `artifacts/island-cluster-improvement-20261110/fast-world-clustered`。
- 查询不生成，CPU路径继续明示TD资格pending，不为本次布局运行全域TD。岛形仍为解析v5，10km格会漏小岛细节，局部真实采样图作为补充。

### 矩形世界（独立宽高）

`POST /api/inner/worldgen/jobs` 可改用 `width_km` + `height_km`（整数 100–10000，必须成对给；`size_km` 仍是旧的方形快捷值 1600/5000/10000，两边同给时以 width/height 为准）。

- 骨架 cell 与精度档均按**最长边**取现有分档（≤2000 → 10 km 档，≤6000 → 20 km 档，其余 40 km / 12000 m 档），不是按 size 直接查表，所以 10000×8000、1200×900 都不会 KeyError。
- 矩形格距取「能整除两边的最大整米值且不超过该档目标」——`fast_relief.grid_of` 要求骨架范围是整格数，旧的 12000 m 在 10000/8000 上都不能整除。例：**10000×8000 speed → 10000 m → 1000×800 网格 = 800000 节点**。提交后 `params.spacing_m / params.fast_nodes / params.skeleton_cell_km` 与 summary 的 `world` 段给出真实值；旧方形（1600/5000/10000）格距表不变。
- 显式矩形受 fast 岛栅格预算预检（`ocean_island_consumers.rasterize` 默认 `max_cells` = 1e6 节点）：超预算直接 422 拒绝，不抬预算。所以 10000×8000 目前只有速度档（10000 m）能跑，均衡/精细档（8000/4000 m）会触预算。
- 矩形 + `speed` + `playable` + `use_gpu=false` 时岛准备额外带 `--defer-mountain-analysis`：延后 1 km 资格分析，摘要把 TD 资格记为 `pending-analysis`（不再当已算）；其它组合与旧方形路径 argv 不变。
- 同一组合且最长边 >6000 km（如 10000×8000）再附 `--island-density low`：本次默认 medium 岛清册的Unicode内存17.79MB超过冻结reader的16MiB预算，low约9.61MB可通过。岛候选使用TG已有算法，不是全域1km格逐格造岛；1km属于后置TD资格分析。low只降**候选岛密度**（数量），不降低单岛几何配置，也不放宽任何冻结reader限额；其他请求保默认medium。summary的`world.island_density`记录实际档位。
- CLI 同源：`tools/generate_world_skeleton.py --width-km 10000 --height-km 8000`（与 `--size-km` 互斥，成对校验；真实宽高写入 config 与 `skeleton-run.json`）。
- upgrade 继承矩形宽高，只换格距档并在同档内按同一规则重算可整除格距。
- upgrade 的岛复用：`params.island_density` 保持**在盘岛实际密度**（prepared.json 的 `island_density` → 旧任务 params → 都没有则 medium），不按新 quality/size 重算——换精度不会重跑 prepare；summary 的 `world.island_density / island_density_source / island_analysis_status` 一律读已存岛记录，`pending-analysis` 绝不写成已完成。

万公里骨架用 **40 km** 单元格。10000×8000km真实骨架250×200格、2线程、seed20260903实测 **432.95秒**（`artifacts/terrain-world-10000x8000-20261110/skeleton-runtime.json`）；旧“约2分钟”仅按5000km格数推算，不能继续作已测承诺。玩家开局区域可另做更细局部骨架 / `local30` 续算，不必重跑整张万公里骨架。

## 约束

1. **冻结身份**：岛产品、计划、世界层用 SHA / `expected_identity`；骨架与岛数组必须一致。
2. **不隐式生成**：点查 / 旅程 API 只读；缺页返回未准备。
3. **解释器分流**：骨架、岛、岛山、fast、details、TD → `TG_PYTHON`；atlas 渲染与部分 compare → 织梦解释器。
4. **资源调度**：内存为软建议（低于建议值仍可启动，会限线程/拉长等待）；GPU 仍按空闲门槛；空岛山计划或 dry-run 不启模型。
5. **面积双参数**：资格门槛默认 25 km²；峰高曲线锚点仍约 100 km²（25–100 km² 岛 requested 峰高约 300 m±10%）。
6. **有限域**：超分析预算的岛窗可 `pending-analysis`；不伪造域外陆地。

## 回归入口

```powershell
# 织梦 .venv：契约与不依赖 numba/psutil 的 CPU 项；缺 TG 依赖时 skip（不装进织梦 venv）
.venv\Scripts\python.exe -m pytest tests/test_ocean_island_integration.py tests/test_fast_relief.py tests/test_world_gen_tiles.py tests/test_web_worldgen.py tests/test_island_mountains.py tests/test_world_island_pipeline.py tests/test_world_gen_pipeline.py -q

# Terragenesis runtime/venv：骨架 tectonic、fast 水文、岛山→世界层合成
..\山川形意Terragenesis\runtime\venv\Scripts\python.exe -m pytest tests/test_ocean_island_integration.py::test_real_fast_compute_and_freeze_keep_lagoons_status_and_fractions tests/test_ocean_island_integration.py::test_optional_islands_preserve_closed_negative_bed_outside_support tests/test_ocean_island_integration.py::test_actual_fast_cli_passes_optional_binding tests/test_world_island_pipeline.py::test_saved_td_changes_final_world_and_map_consumer tests/test_world_gen_pipeline.py -q
```

`test_world_gen_pipeline` 已走 `terrain_pipeline.tectonic`（经 `skeleton.py`）；无 `psutil` 的解释器对依赖骨架的用例 skip。真机作者链：Web `use_gpu=false`，或 CLI（`generate_world_skeleton` → `web_island_stage prepare|schedule|fast`）。产物身份写入工程进度，不覆盖旧冻结件。

## 相关文档

- 规则：[terrain-generation-rules.md](terrain-generation-rules.md)（世界层以第 6 节为准）
- 岛链消费：[ocean-island-integration.md](ocean-island-integration.md)
- 岛山：[island-mountains.md](island-mountains.md)；TG 现行细则 `山川形意Terragenesis/docs/island-mountains-current.md`
- 读取契约：[world-map-source-contract.md](world-map-source-contract.md)
- 进度：[工程进度.md](工程进度.md)

## 自然地表总览设色（2026-11-10）

`app/world_relief/atlas.py` 在 `mpp>=2000` 时以低饱和近似群系色为主体，保留高程阴影，粗DEM坡度仅作灰色裸岩显示代理，不按海拔统一覆盖棕色。`natural_forest` 为独立显示掩码：原 `forest` 不变，按同一温湿代理在林线/坡度/非湖陆地约束内补林；四种林型分色、分尺度冠层纹理，小树点缀。没有真实气候、降水、NPP或植被数据，图例与来源记录必须明示。自然总览附图外色键，纯地形对照和小页面保留原路径。

同源图位于 `artifacts/island-cluster-improvement-20261110/atlas-natural/`。`atlas-source.json.vegetation_display` 单列原林区/补充林区及非湖陆地分母；`display-check.json` 记录冻结身份与纯地形像素对照。仅重绘，不调用世界生成或TD。

2026-11-10显示调整：`coast_ripples=false` 默认去除第二道岸线及重复装饰水纹，各尺度保留单条海陆描边和海深色。自然图 `mount_tone_alpha=0.18` 在原山域上温和加深，林内减力、雪面退让，不改山域判定和地形；设置0关闭。最新同源图为 `artifacts/island-cluster-improvement-20261110/atlas-clean-coast/`，旧装饰可显式开关回放。原自然图的逐像素对照结论仅适用于当时版本，本版纯地形页也去掉装饰岸纹。

山脊谷地增强（2026-11-10）：自然主图以原DEM的连续局部起伏/坡度权重补充细节晕渲（不是新增mountain判定）；315°主光+多向补光、32°太阳高度、显示z×4，少平滑取样与轻微局部相对高差增强。`natural_relief_strength` 默认0.6/0关闭；不引入高程噪声、不画新沟纹，旧小图与relief-only不启用。示例及局部对照在 `artifacts/island-cluster-improvement-20261110/atlas-relief/`；10km DEM不可通过显示增强恢复真实小沟壑。

## 局部山链与谷盆重组原型（2026-11-10）

`app/world_gen/mountain_sculpt.py` + `tools/prototype_mountain_sculpt.py` 是独立局部高程试验，不接默认世界流水线。读取已冻结世界及同源骨架脊网，选主脊及父子支脉，调整截面、谷底、盆地与山口，可选复用既有不规则图侵蚀；显式支持域/水域/窗口边界保护，另目录写arrays与结构JSON，不伪装正式world-map-product。belt4单窗口2000×1800km/10km成果在 `artifacts/mountain-structure-prototype-20261110/candidate/`，主测试14通过，正式局部6轮侵蚀约10.2秒；内部山脊谷地部分改善，但外围宽底座仍明显，形态尚未最终验收。未重建全域河湖，不绘旧河线，不接玩家。

2026-11-10平台轮廓修订：原型新增默认 `platform-rebuild` 与旧 `corridor` 两策略；安全域与山形包络分离，原宽平台及山麓可被降低/切退，保留同源多个主段与父子支脉，低频轮廓场+脊状分形+局部粗侵蚀重塑实际高程。主修单位错误、单调峰顶限幅与float64落盘。最新单窗口在 `artifacts/mountain-structure-prototype-20261110/candidate-platform-final/`，27项定向测试通过；较初版已有可辨链谷/轮廓变化，但仍是10km有限局部试验，不是全域形态/水文认证。`tools/render_mountain_sculpt_comparison.py` 以相同色标光照生成对照，失败版本保留。未接默认作者链/玩家。

宽山群试验（2026-11-11）：新增可选 `structure_policy=mountain-group`，保起伏的中低山背景、独立宽肩/裙层、连续浅谷盆、目标相对高差—半宽约束及支脉自由端衰减；不再仅用窄主脊替换旧平台。主修单位混用、主段遗漏、叠加高度预算与reach硬裁，旧策略仍可回放。候选 `artifacts/mountain-structure-prototype-20261110/candidate-mountain-group-final/`，45项定向测试通过，单窗口生成13.894秒；坡度和固定剖面见validation-main/cross-sections。实际有限窗仍非完整地质/全域水文，未上线作者默认或玩家。

## 山地—冰川—水文正式派生世界（2026-11-11）

批准顺序已实际执行：`world_mountain_stage`按完整有限网格逐原带从immutable床求proposal、一次融合 → `glacier_stage`只读调用TG `generate_mountain_glacier`固定床2D SIA → `world_hydrology_stage`复用TG不规则图重建河湖/发布。新目录 `artifacts/mountain-glacier-hydrology-20261111/world/`，schema world-map-product-v1，identity `6d99aafd0b11d83e6af1358195dcab5b3c437771e9f5466fa7ceb7eb8dd514e4`，10000×8000km/10km/seed20260903。源骨架岛群复用，默认世界未切换。

真实岛支持不得使用含大陆的frozen_island_land_fraction；改用protected/lagoon/feature支持。山地92025格实际变化，保海岸/岛地貌；冰川2个有限内陆区20年高度强迫情景，edgeH精确零、域外未模拟，固定床不冰蚀。水文bed与ice surface分层，ice外使用bed；新18382河段/503潜在湖轮廓，不复用旧河湖，原床湖域复核防水面埋床。融水仅所选区域时窗平均诊断分量，非总径流/某年流量，无native库存扣账。

新增工具 `apply_world_mountains.py`、`generate_world_glaciers.py`、`publish_mountain_glacier_world.py`，图册显式`--source-kind world-map-product`可显示原生冰体。实际load_source/玩家basemap试读通过，不等于默认玩家界面已全面采用自然图册美术。详细运行、失败记录、成本与局限见新目录总README。

总览河流显示（2026-11-11）：atlas mpp≥2000时默认river_overview，screen系数24代替55，宽度以固定4万km²面积锚点分级（0.55–3.4px）；更多支流但不将所有河线一起放粗。`river_overview=False`回放旧画法，小页面不变。万公里同源新图 `artifacts/mountain-glacier-hydrology-20261111/atlas-rivers/`，370→1254条显示折线，纯地形对照不变；非新增物理河宽/径流。

## 有限气候年→雪冰液水→水文→环境派生（2026-11-11）

用户20:52接受 `sine-latitude` + 原 `background_rain_rate_s_inv=1e-5` 的**极干旱工程情景**继续；不是自然全球气候标定，也不是TG二阶段全部完成。已在原 `6d99aafd…14e4` 山地冰川世界上实际运行并另存：

| 阶段 | 入口 / 实际职责 | 本批目录与身份 |
|---|---|---|
| 同源月气候 | `climate_world_stage.climate_source_from_map / plan / prepare` → TG `world_climate` 十二次月稳态雨，连续纬度季节温风；40km母场200×250映射10km世界800×1000，365日 | `artifacts/world-climate-integration-20261111/climate-dry-continuous-year/`；`70d36369e89eaef26b79ac19c250fff164df022f3268844b731c5325d412ae4c` |
| 独立新年雪冰/土壤/径流 | `climate_hydrology_stage.plan / prepare`；全陆逐格雪冰诊断，所选2区调用TG `generate_climate_slope_glacier(export_monthly=True)`实际新跑1年；唯一月液水→一次土壤桶→原saved receiver | `hydrology-dry-continuous-year/`；`61783b0ada6bcb1f4d513e46fe320288cbf62355331d20ff88a4b091d1c3e129`（同本批根目录） |
| 只读与环境发布 | `SavedClimateMap.query/point`、`SavedClimateHydrology.query`；`climate_environment_stage.publish`发布年T/P、真实原生分类ID、末雪冰土壤和年积分栅格Q | `environment-world/`；`9fda7cc802e509c154662edcfc2e6f8c5dc4dd135d9d052527f87681cbbef0c1` |

真实两冰区本年全部complete且闭边H为零；只用旧H作初冰，不导入旧累计融水/pending，不把旧20年高度供雪情景称气候年。区外冰SWE为逐格非动态库存，不是全域2D冰川H。环境年Q=`sum(月路由体积)/(365*86400)`，不是月均Q无权平均；真实月窗口、年Q积分、原生biome ID及原床/status/receiver/河湖矢量字节保留已核对，见 `environment-validation.json`。

原 `routing_surface_m/hydro_bed_m` 几何与潜在湖轮廓保留，不随新年H重建，没有湖库蓄水动力/河道演化；矢量未获得Q锚点，现有河线宽仍按面积符号，不能把栅格Q冒充逐矢量物理河宽。潜在群系是本情景规则分类，不是实测森林或植被库存。降雨继承闭壁水汽集中、单格迎风凝结、未校准海蒸发/理想风场；本次陆均68.332、中位0.10448、最大11666.626mm/年，61.193%陆地<1mm/年。

旧 `climate-liquid-year/` 与 `climate-correction-check/` 两率对照均为历史候选/诊断，不替代本次已选年链；低k候选未采用。TG月导出曾涉及旧产品源码pin，经用户20:20批准保原bytes/旧manifest另立修订，见 `tg-monthly-export-check/revision.md`。本批未改默认世界、saves、长程restart接线或提交。atlas已实际消费保存的群系ID/年末雪SWE/新年末动态H，主17项相关测试及真实逐格消费者检查通过；`atlas-final/simple-atlas.png`和`topics/`三图已生成并主看图，身份绑定见atlas-source.json/topic-source.json。独立A1–A5与完整年账见joint-acceptance.json；证据、工程限制与分组定向测试见本批README。

## 气候液水→CSR月湖河侧车（2026-11-12）

独立读取原bed `6d99aafd…14e4`、已保存月气候 `70d36369…ae4c` / 液水雪冰 `61783b0a…e129`，图像父环境仍 `9fda7cc8…f0c1`；不改上述产品或洋流，不重算气候/冰川，不加旧累计融水/pending。实际新产品 `artifacts/climate-lakes-rivers-20261112/surface-water-csr-year/`，identity `7c4da2ca737de3baa0b30c576af7adfca08e268b69cd9dc9dc243e33ca7be0a8`；完整源身份和证据见 [交接README](../artifacts/climate-lakes-rivers-20261112/README.md)。

| 环节 | 实际复用 / 织梦薄接线 | 当前边界 |
|---|---|---|
| 真实图与汇流 | TG `grid_mesh`、`accumulate_graph`；`csr_reservoir_adapter.py` 接4039 owner/9689内部face/21026外排face | 全native非终端陆格owner库容、真实CSR鞍面，不称merge树/自然出口认证 |
| 库群月交换 | `csr_reservoir_year.py` 实调TG `_ReservoirSystem.advance` 固定BE与 `_IntegratedExchange.fields` 库存几何 | 每月一步、conductance=0.6m/s，owner lumped供水，owner-local月初wet PET系数1、渗漏0；初湖/土壤0，一年非稳态/真实水动力 |
| 单池与选型对照 | TG `LakeStorage`单池实际调用；`route_pool_interval`适用小样本对照 | 不冒称全域走窄单池DAG；其他候选和历史对照逐项见 [复用表](../artifacts/climate-lakes-rivers-20261112/algorithm-reuse-table.md) |
| Q分类与显示 | `river_flow_network.py` + 既有 `graph_hydro.trace_lines`；`surface_water_map.py`读保存月wet/depth/SWE/H | 483父段/月152–201显示；Q止于wet支持，face净输水仅示意，湖内完整Q未知；一年有流分类非永久河道存在认证 |
| 地图消费 | `map_bundle.py`第六组 `surface_water`，旧5组源身份保持 | 已实际注册；1/7/12月图主看图及真实HTTP/Edge零pageerror通过，月点/窗与surface-rivers/spills可读 |

旧lower-star已暴露越干鞍/错路，弃生产；窄TG单sink认证探针1371池中277多sink池未认证，未删池硬跑该年，见 `tg-certified-geometry-probe.json`。初次调查与失败历史照留，不用成功后端美化此前盘点。

完整物理已保存于月checkpoint，显示重做仅finalize；1800px atlas固定面积阈只影响显示、不改Q/水源。真实wet与depth>0.1m显示域必须分列，隐藏浅水不称无水，奇偶月wet跳变含月初ET/整格岸线operator-split离散，不作自然季节认证。首图source-kind默认错误及超制图上限失败均保留；`atlas-monthly-final/` 1/7/12月PNG已实际生成并主看图，六组实际验收及截图见本批http-browser-validation.json。资源、水账和逐月面积不在此重复，见上述README及其validation/runtime链接。

## 可选作者地理软锚点（2026-11-12）

参考 dreamulator 的结构化地理锚定，新增显式 `geography_features` 输入，将有限域平滑陆海偏置施加于骨架初始地壳场，再复用 TG `tectonic.initialize / CrustState / evolve`；后续岛链、不规则图水文及只读消费者不换引擎。省略/空列表保持旧路径，非空输入绑定配置和产品身份；不支持修改冻结骨架或局部 overlay 后编辑。使用、来源版本与边界见 [world-geography-anchors.md](world-geography-anchors.md)。只增加 API/CLI 输入，未增加前端编辑器，不改默认世界。
