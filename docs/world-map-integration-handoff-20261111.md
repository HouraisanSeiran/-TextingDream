# 现世界地图接入交接（2026-11-11）

状态：现有作者「世界地图」已接登记产品的存图、月份与地点点检；不新增页面或导航。数据与接口以 `config/map-bundles.json`、`app/map_bundle.py`、`app/map_bundle_routes.py` 为准。**真实 HTTP、Edge浏览器与旧玩家链回归已通过**；证据在 `artifacts/map-integration-20261111/`，不以 Node DOM 测试代替视觉验收。

## 2026-11-12增量：月湖河已保存并接入第六组

原5组的HTTP/Edge记录保留，**本次第六组另有真实验收**。`surface_water` 已实际加入config的原地图id，不新增页面；新atlas按1/7/12月提供真实湖河图，数值可选全12月。新产品 `artifacts/climate-lakes-rivers-20261112/surface-water-csr-year/` identity `7c4da2ca737de3baa0b30c576af7adfca08e268b69cd9dc9dc243e33ca7be0a8` 已完成真实12月物理与水账检查；terrain/climate/hydrology/environment/ocean旧源均不变。最终交接入口与证据索引见 [本批README](../artifacts/climate-lakes-rivers-20261112/README.md) 和 [算法复用表](../artifacts/climate-lakes-rivers-20261112/algorithm-reuse-table.md)。

`atlas-monthly/` 首次source-kind失败保留；修复后 `atlas-monthly-final/` 的1/7/12月PNG已生成并主看图，第六组显式注册及HTTP/Edge零pageerror验收通过。新证据在本批http-browser-validation.json、bundle-data-validation.json和界面截图。下文原5组、18382旧河段/503潜在湖是历史几何，不是当前实际湖面和有流河线；当前月向量用surface-rivers/surface-spills。有限一年有流分类不是永久河道认证，0.1m显示阈隐藏的浅水不是不存在；奇偶月wet交替含月初ET/粗岸线operator-split离散，不是自然季节认证。

## 1. 接手入口与边界

- 注册 id：`terragenesis-world-20261111`，schema `dream-map-bundles-1`，producer **Terragenesis**。
- 后端：`app/map_bundle.py` 负责同源绑定、冻结文件校验、只读数组缓存和查询；`app/map_bundle_routes.py` 安装 `/api/inner/map-bundles`。
- 前端：`app/static/native-map.js` 在原 `native-map-host` 挂 `map-bundle.js`；`map-bundle.css` 是现地图内部样式，`index.html` 只增加脚本/CSS。UI 不展示「数据包」概念，也不做多源选择器。
- 作者可切存图、选择 1–12 月、放大/复位后滚动平移、点击地点、查看来源/限制。预览为**已保存 PNG**，在线不重绘气候；窗查询与分页矢量是 API 能力，当前 UI 不自动拉取/重画全部矢量。
- 进入 player 模式先卸载作者组件/旧宿主、取消图像请求并回收 ObjectURL；迟到结果不得挂回。玩家仍使用原 `/api/sessions/{id}/play-map` 与后端掩膜/fog，**本次不换玩家默认、不迁 saves、不改故事或 restart**。不能因为有作者 token 就向玩家请求全幅图。
- civ-atlas 接口/宿主保留；`TEXTILE_CIV_ATLAS=1` 启用时才显示可选旧来源，显式选择才加载；禁用时不强拉宿主。

## 2. 原数据、身份与源链

所有路径相对织梦仓库根目录，原件在 **`artifacts/`**；线上接口不接受任意路径。登记只引用，不复制或改写这些源。

| 分组 | 主路径 | 完整身份 / 定位 |
|---|---|---|
| terrain | `artifacts/mountain-glacier-hydrology-20261111/world/` | `6d99aafd0b11d83e6af1358195dcab5b3c437771e9f5466fa7ceb7eb8dd514e4` |
| climate | `artifacts/world-climate-integration-20261111/climate-dry-continuous-year/` | `70d36369e89eaef26b79ac19c250fff164df022f3268844b731c5325d412ae4c` |
| hydrology | `artifacts/world-climate-integration-20261111/hydrology-dry-continuous-year/` | `61783b0ada6bcb1f4d513e46fe320288cbf62355331d20ff88a4b091d1c3e129` |
| environment | `artifacts/world-climate-integration-20261111/environment-world/` | `9fda7cc802e509c154662edcfc2e6f8c5dc4dd135d9d052527f87681cbbef0c1` |
| ocean | `artifacts/ocean-current-overlay-20261111/` | 无自有产品 identity（登记值 `null`）；manifest SHA-256 `abf72e6a825ce2b1d8270e854ba65fbdbd28cbfddd76ae66ebfd40123efc0f2c`；另 pin 全部数组/路线/图像 |

源链：冻结骨架 → 已发布岛群/地形 → 宽山群 → 原 H20 / 冻结排水世界（terrain）→ 已选气候年 → 新生雪冰水文年 → environment；ocean 独立读取同一 terrain、climate、reference，并绑定 environment 底图，不反馈气候。

| 上游/关联 | 完整身份 |
|---|---|
| 骨架（terrain.source_identity） | `a2324cb90d5454f91cb8cdb6dabad214b84f9be069be35f815879ca3682e1ee1` |
| 山地前冻结世界（mountain_binding.source.product_identity） | `df03ea1fdd72c2bb34fabeaa4c6b9c5759a6189a3aea98e6135bb08c2a323331` |
| 山地检查点（`artifacts/mountain-glacier-hydrology-20261111/mountains-revised/`） | `814fb13e3f8d97370052a8ac27c257d6804f7ce27f88431ac44ce7ee9b7a1fc0` |
| 原 H20 区 01 | `d16c52cde11999c92e1ecec81c7200ad6124088e5e8d9e36b69b2d4a2a5d0aa4` |
| 原 H20 区 02 | `002c8ca41146132463e09ce01307d7777187e453cae5fbf25ea48100def7a5dc` |
| 气候/海洋 reference | `49f90337fc2bc658abe69cc7c2f6fb586ba1a58b761b933ed632fd03870b6bad` |
| ocean forcing | `5bc80559d2a97d878fbafb229e354f19ad575f882fbb4cf1762a23140f414bba` |

注册还 pin 各 manifest SHA-256；完整逐文件值直接查配置，身份不得截短后用于校验。区域新年动态求解绑定与初 H SHA 在 `hydrology-dry-continuous-year/regions.json`；原 H20 来源/模型/供给/物理时窗在登记 `history` 和原世界 manifest。旧源码批准修订记录见本批气候目录 README，不覆盖原 manifest。

## 3. 当前可读内容（先看 detail 的 queryable）

`detail.groups.GROUP.fields.FIELD` 声明 `unit/time_semantics/shape/queryable`。只有形状正好为该组 `[z,x]` 或 `[12,z,x]` 才进入 point/query；不能将登记描述等同于可空间查询。字段不存在不补算。

| 分组/内容 | 已接字段或载体 | 可用方式与解释 |
|---|---|---|
| 地形/海陆/海岸 | terrain 的 `elevation_m/status` | 点/窗；海岸由原海陆格与存图表达，无单独 coastline 矢量接口。以 status 判海，不以负高程判海 |
| 岛屿/潟湖保护 | `protected_fraction/registered_lagoon/frozen_island_land_fraction/frozen_island_lagoon_fraction` | 点/窗；land_fraction 含大陆，不能当独立岛屿支持范围；不是岛峰 30 m 已完成证明 |
| 冻结地表排水 | `routing_surface_m/hydro_bed_m/water_surface_m/drainage_area_m2/receiver/lake_id` | 点/窗；receiver 是冻结接收格索引，不随选月推进。汇水面积不是流量，水面不是永久水库存 |
| 河/潜在湖 | environment 继承的 `rivers/lakes` 矢量 | vector 分页保稳定 ID、米制几何/上下游或湖岸属性；18382 河段、503 轮廓不等于503个水量平衡湖。栅格 Q 未归属到每条河，符号河宽非物理河宽 |
| 当前动态 H | environment 的 `glacier_ice_thickness_m/glacier_ice_surface_m/glacier_ice_volume_m3/glacier_coverage_fraction/glacier_simulated_fraction` | 点/窗；**本气候年第1年末**，只在两明确动力区有 H。域外 NaN/未提供，不是0冰；静态底图使用保存的当前 H |
| 历史 H20 | 原 terrain 的 glacier 字段、旧累计融水及旧平均融水诊断 | **不作为 terrain 点/窗字段公开**（本适配层剔除 `glacier_*`）；经 history 描述与冰川对照 panel 查阅，不能混进当年月输入 |
| 月气候 | climate 的 `monthly_temperature_c/monthly_precipitation_mm/monthly_wind_x_m_s/monthly_wind_z_m_s/monthly_pet_mm` | 1–12 月点/窗；40 km 大气母场映射至10 km产品并做原生高程修正，非10 km独立大气求解 |
| 群系/静态参数 | climate 的 `biome_id/biome_override_reason`、坡度、土壤容量、ET/入渗/快流比例、valid/ocean/wetland掩膜、模型诊断latitude/longitude；environment 的 `biome` | 点/窗；保整数群系 ID；经纬字段是模型诊断参数，地图坐标仍是米。群系是潜在规则类别，不是实际森林/资源库存 |
| 新生雪冰水文 | hydrology 的 `monthly_snow_swe_mm/monthly_ice_swe_mm/monthly_soil_water_mm/monthly_liquid_input_mm/monthly_actual_et_mm/monthly_sublimation_mm/monthly_runoff_mm/monthly_routed_volume_m3/monthly_discharge_m3_s` | 全12月点/窗；有 initial/final SWE/soil 与 `dynamic_glacier_mask/receiver`。选区 TG 新液水替换当地入口，不再加P/旧累计/pending |
| 气候内液水诊断 | climate 自带的月 ET/soil/runoff/routed/Q | 仍可点/窗，但它是 **liquid-only climate diagnostic**，不是新版雪冰水文；真实本年雪冰耦合值选 hydrology，年 Q 选 environment |
| 年末环境 | environment 的年 T/P/biome、`discharge_m3_s/soil_water_mm/snow_swe_mm/year_end_ice_swe_mm` | 点/窗；末态存量非月通量；区外 ice SWE 非全域动态冰川 H |
| 独立上层海洋 | ocean 的 `ocean_mask/basin_id/wet_area_fraction`；12月 `monthly_current_x_m_s/monthly_current_z_m_s/monthly_sea_temperature_c/monthly_reference_sst_c/monthly_sst_anomaly_c` | 独立40 km格点/窗，干格/原生陆地不冒充SST或洋流。暖冷依同纬参考SST距平，不由绝对海温判断 |
| 海洋面拓扑/排序 | ocean `face_open_x:[200,249]`、`face_open_z:[199,250]`；hydrology `order:[800000]` | detail **descriptor-only，queryable=false**；无点/窗语义，强查返回422，不隐式改形 |
| 洋流路线 | `routes.json`，kind `ocean-currents` | 只保存1/7月共36条 flow-to 路线；其他月份该月路线为空，不生成。路线类型是沿线平均距平分类，不保证每段同符号；名称仅工作名 |

## 4. 格网、时间与单位

- seed `20260903`；有限世界10000×8000 km，不环绕。native产品800×1000、10 km cell-centre，首中心 `[-4995000,-3995000] m`；外边界 `[xmin,zmin,xmax,zmax]=[-5000000,-4000000,5000000,4000000] m`。
- 海洋 macro 200×250、40 km，首中心 `[-4980000,-3980000] m`；大气同尺度母场，但 climate API 数组已映射到 native10 km。**ocean 不得与 native 混一个窗口请求。**
- 坐标 X 向东、Z 向南、数组 `[z,x]`；点检各组独立取最近保存格，无插值。边界按格覆盖半开域；正向最外边缘可能返回界外，不把图例/空白当坐标。
- 当前年日历 `noleap365`、1–12月，天数31/28/31/30/31/30/31/31/30/31/30/31。T/SST 为℃、风流m/s、海拔/H为m、比例/分类为1；月P/PET/ET/径流/液水为mm/month，SWE和土壤水为月末mm水当量，路由体积m³/month，Q为m³/s。
- 年 Q =全年月路由体积之和 / `(365*86400)`，不是12个均Q简单平均；年末雪/冰/土壤水不是全年累计。原 H20 是另一高度供雪20×365.25日情景，不冒充本年续算；旧累计融水与pending是同一笔水，不能相加或输入本年。

## 5. 存图清单与坐标点检

预览根路径见第2节；UI只用 detail 提供的 `georeferenced/image_size/map_rect/world_extent_m`，不能硬编码此批边距或混用旧 lon/lat SVG。由 DOM `naturalWidth/naturalHeight` 与当前 bounding rect 还原像素，缩放/滚动后仍按地图框映射。透明层按两图各自 map_rect 对齐。

| preview key | 保存路径（相对该批主目录） | 月份 / 点检 |
|---|---|---|
| `atlas` | 气候批 `atlas-final/simple-atlas.png` | 静态全年/年末自然总览，可点；1962×1727 |
| `relief` | 气候批 `atlas-final/relief-only.png` | 静态地形，可点；1962×1602（高度不同，不按整图拉齐） |
| `climate-topics` | 气候批 `topics/climate-topics.png` | 静态专题panel，禁点检 |
| `water-snow-topics` | 气候批 `topics/water-snow-topics.png` | 静态专题panel，禁点检 |
| `glacier-year-comparison` | 气候批 `topics/glacier-year-comparison.png` | 旧H20 / 当前H1历史对照panel，禁点检 |
| `ocean-overlay` | 海洋批 `overlay-month-01.png/overlay-month-07.png` | 仅1/7月透明复选层，panel上禁用 |
| `ocean-composite` | 海洋批 `natural-map-month-01.png/natural-map-month-07.png` | 仅1/7月洋流自然叠图，可点 |
| `ocean-theme` | 海洋批 `ocean-theme-month-01.png/ocean-theme-month-07.png` | 仅1/7月洋流专题地理图，可点 |

本批地理图 map_rect 恰为 `{x:81,y:81,width:1800,height:1440}`，只是登记事实，不是后续产品常量。`months:[]` 表示静态存图，不是12幅月图；换月只改变数值点检。洋流月数组有12月不代表12月都有图/路线；缺存图明确禁用/提示，不替代成1月或7月。

## 6. API 与认证（作者范围）

沿用已有 `api()` 和 `X-TextileDream-Token`；令牌不放URL。PNG先带头fetch→Blob→ObjectURL，卸载/换层必须revoke；CSP `img-src` 已允许 `blob:`（本任务未改原CSP）。服务端 `/inner` 认证边界与前端作者/玩家模式所有权是两件事，本次不新增玩家全幅接口。

公共前缀 `B=/api/inner/map-bundles/terragenesis-world-20261111`：

| 方法 | 路径 / body | 返回 / 限制 |
|---|---|---|
| GET | `/api/inner/map-bundles` | `{bundles:[{id,title,status}]}`；仅登记目录，不代表源已通过加载验证 |
| GET | `B` | detail 含5 groups字段描述/单位/时间/grid/queryable、previews/frame、warnings/history/limits、`author_only:true/default_story_publication:false` |
| POST | `B/point`，`{"x_m":0,"z_m":0,"month":7}` | `{bundle_id,point,month,groups:{G:{values,units,cell_zx,sampling,status}},warnings}`；月份严格整数1–12，坐标有限数 |
| POST | `B/query`，`{"fields":["environment.elevation_m","hydrology.monthly_discharge_m3_s"],"window":[0,0,2,3],"months":[1,7]}` | `{arrays,units,grid,months,window,value_count,bundle_id}`；窗口半开 **[z0,x0,z1,x1]格索引**，不是米制矩形；1–64唯一字段，至多65536个标量 |
| POST | `B/query`，`{"fields":["ocean.monthly_sea_temperature_c"],"window":[0,0,2,3],"months":[1,7]}` | 海洋独立请求；静态数组不人为复制月轴，月数组保所选月轴 |
| GET | `B/preview/{key}?month=7` | 已登记PNG FileResponse，`Cache-Control:no-store`；非存图月份404 |
| GET | `B/vectors/{kind}?month=7&offset=0&limit=100` | kind=`rivers/lakes/ocean-currents`，`{items,total,offset,limit,month,status,bundle_id,kind}`；默认100、最大500，须分页才是全量 |

- 路由禁止 body 额外字段；字段用 `group.field`，同一 query 必须相同格网。历史记录、模型参数和面拓扑描述不是任意文件下载口。
- 缺登记/文件/图/月/矢量kind为404；身份或冻结源改变为409；越界、错格网、descriptor-only、超限等为422；沿原中间件处理认证错误。
- 非有限数组/nodata转JSON `null`，UI显示「未提供」，不改成0、不回退别的源或月份。海洋陆格月值为null；静态掩膜仍可有值。湖vector附 `status:potential/unvalidated, permanent:false`，**false 是未作为常年湖发布，不是证明永久无水**。

## 7. 工程限制与历史候选（必须随交接保留）

1. **现登记旧湖与新侧车分开**：原5组仍使用31356格潜在填洼水面，占陆地9.6125%（约9.6%）；该旧链没有湖库存/蓄水动力，仅标potential/unvalidated。2026-11-12新侧车已保存真实月库存与有限导通交换，12月wet 2487格/248700km²，其中depth>0.1m显示775格/77500km²；但尚未注册，且空湖/空土壤初态一年、PET代理和工程月步不构成常年水量、调洪或自然湖面认证。不能将“新库存已完成”写成旧潜在图已切换，也不能将隐藏浅水说成消失。
2. **极干工程气候**：用户已接受连续纬度季节项、原k=1e-5情景；61.193%（UI约61.2%）陆地年雨<1mm。闭边水汽/迎风经验集中/未标定理想风等限制仍在，不是自然全球气候完成。
3. **初H暂态**：旧高度供雪H仅作本年初冰，新年融水实际消耗初H，年内水文包含该初态暂态。动力H只覆盖两窗口 `[158,483,239,564]`、`[336,407,389,460]`；域外非动态雪冰诊断不是全球冰流。
4. **route geometry保留**：terrain/environment原床、海陆、receiver、河湖矢量及 `routing_surface_m/hydro_bed_m` 沿冻结旧几何，未按当年H重建；Q是原receiver上的新年液水汇流，不是新河槽/真实水力宽。
5. **海洋首年候选**：max_cycles=1，尚未长期收敛；1月参考SST初始化，中性路线不能与7月差异一起解释成成熟季节暖冷转换。暖冷阈值为距平±0.3℃；40km split块/端口保守关闭会损失小海峡，不跨陆平滑；无深海/上升流/潮汐/海冰/标定航速，也不反馈大气。
6. **先有源再可用**：登记不是生成。缺失、身份不符、未完成或不同源组应拒绝，不启动numba、TG子进程、GPU、planner或生成器补齐。当前注册状态不是天气/文明/道路/资源库存已自动接入；也不是默认故事发布。

登记 `history`：原H20两区（全身份见第2节）及旧累计融水仅历史；`climate-liquid-year` identity `afac74ce377105a6e3a0d1b1c74cffb582d57a18c0d1a3c4cbd53438f09ac8d4`、`probe` identity `6be3489102e08e899646566f20e060da89a3f49d97b23df36a4482a308af7dcd` 均在 `artifacts/world-climate-integration-20261111/`，`history-reference-only/selectable:false`。该目录 `climate-correction-check/` 的低k对照、旧液水诊断图/成本日志也保留，但不是正式可选源。不得覆盖失败候选来制造唯一成功历史。

## 8. 注册维护、缓存与验收

- 已冻结产品不可原地改；新产品先发布完整源/manifest/数组/矢量/存图，再核同源链、格网、时间和单位，最后登记独立新id/路径及manifest、文件pins。不要只把旧hash替成新hash绕过同源验证；旧记录/产物保留。
- 修改登记项时更新对应描述、图像尺寸、有效框、坐标范围和可用月份；当前UI正式id是内部常量，换正式源须显式评审该常量，不自动挑“最新”。`preview_metadata` pin `atlas-source.json` 防图框来源漂移。
- `BundleRegistry` 最多缓存2个完整记录（记录内容作key）；数组mmap只读，首次消费校验文件sha/shape/dtype；每请求检查已跟踪文件size/mtime/ctime。已缓存源变化拒409、缺文件拒404，不能把新文件与旧兄弟缓存拼用，也不会按月反复求解或重算全部文件hash。
- 在线加载复用 `SavedClimateMap` 与静态水文绑定验证（包括receiver/order/region/calendar），不走会引入numba的水文生成planner；不import/运行TG求解子进程，不改原数据。读取/校验拓扑不等于重建水系。

| 验收项 | 当前记录 |
|---|---|
| JS语法 | 已通过 `node --check app/static/map-bundle.js`、`node --check app/static/native-map.js` |
| UI DOM mock | 已通过 `node tests/map_bundle_ui.cjs`：挂卸载、token/blob/revoke、初始player无作者请求、迟到detail/blob隔离、自然像素缩放坐标、panel禁点、月份与null/0区分 |
| 主定向回归 | `test_map_bundle.py`、`test_map_bundle_routes.py`、`test_map_policy.py`、`test_play_map_world.py`：31项通过，命令`cmd-20261111160604-8eebe3801c`；首轮真实fixture误选西北陆点的SST非空断言已纠正为实际海点非空＋陆点null，未放松支持域 |
| 源接口兼容回归 | bundle/routes＋旧map_source_contract、terrain_source、world_climate_adapter：执行代理181通过、2跳过；与主组重叠，不相加、不称全库通过 |
| 真实HTTP | 织梦`.venv`、scratch临时DB独立服务通过5组数据（90字段描述、87可格点查询；跨组含重复字段，非90种独立物理量）、8类白名单图、保存值/月顺序逐位、海陆SST支持、18382河段/503潜在湖和1/7月各18洋流路线分页；token/Origin、缺图404/混grid422均通过。见`artifacts/map-integration-20261111/http-smoke.json` |
| 真实浏览器 | 实际Edge通过自然图/洋流图切换、不同PNG高度的透明层地图框配准、点检、中文图层与数值显示、panel禁点、缺3月洋流图不替换、player卸载作者图；零pageerror。见`browser-api-smoke.json`和`world-map-integrated.png`、`world-map-ocean.png`、`world-map-transparent-overlay.png` |

后续验收只补本节实际结论/证据，不把历史批次通过数相加成全库通过。源产品内容与先前生成验证见 `artifacts/mountain-glacier-hydrology-20261111/README.md`、`artifacts/world-climate-integration-20261111/README.md`、`artifacts/ocean-current-overlay-20261111/README.md`；本交接不重跑生成，不改原README或产物。

验收临时服务127.0.0.1:8873和scratch临时数据库已停止使用；未重启用户服务、未写用户saves、未提交Git。代码及注册在下一次正常启动的应用中生效：若仍运行旧Python进程，新后端路由需正常重启后加载，仅刷新静态页面不保证旧进程已有新API。本次不擅自重启。
