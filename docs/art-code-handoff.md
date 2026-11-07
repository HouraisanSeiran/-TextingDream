# 地图与城镇美术交接：素材、代码需求与验收缺口

状态日期：2026-11-06。本阶段停止唤醒美术子代理；后续代码由用户另派智能体完成。

## 1. 交付状态

- 迷雾：东西两套素材已保存，未接入正式迷雾。
- 城镇：`app/static/map-art/town/` 共 23 个带元数据的素材目录，1606 个 symbol，当前 symbol id 无重复。包含西式/东方/阿拉伯人族建筑、精灵/矮人/兽人建筑、道路、城墙、防御工事、地标、水域、地面、资源点、青金石与农牧细分。
- 天气：10 个效果叠层的 JS、独立预览和总预览已经落盘，语法检查通过；不是完整气象模拟，也不是全部效果已通过美术验收。
- 严格区别：有文件、语法通过、截图已生成，不等于实际目视验收通过。强风和天色模块原作者明确没有看见截图；冰冻模块的 README 自检结果段尚未完成。

## 2. 现有入口

| 内容 | 文件 |
|---|---|
| 迷雾素材与接入边界 | `app/static/map-art/fog-brushes/README.md`、`preview.html` |
| 建筑规范 | `docs/town-art-spec.md` |
| 全部建筑图册 | `app/static/map-art/town/index.html` |
| 合并建筑目录 | `app/static/map-art/town/build-index.js` → `town-catalog.js` |
| 城镇布局 v2 | `app/town_layout.py`、`town_layout_art.py`、`town_layout_wall.py`、`town_layout_fort.py`、`town_layout_terrain.py`、`town_layout_site.py` |
| v2 渲染与预览 | `app/static/town-render.js`、`app/static/map-art/town/layout-preview-v2.html`、`layout-preview-v2.js`、`layout-samples-v2.js` |
| 天气规范 | `docs/weather-spec.md` |
| 天气总预览 | `app/static/weather-fx/index.html`、`index.js`、`index.css` |
| 天气生成（11-06 后续已补齐，未接正式地图） | `app/weather.py`、`app/static/weather-fx/weather-gen.js`、`docs/weather.md` |
| 建筑经营预设 | `app/building_economy.py` |
| 建筑元素生成 | `tools/town_art_elements.py`、`tools/encyclopedia_build.py` |

## 3. 天气美术代码

`app/static/weather-fx/` 下：

| 文件 | 全局对象 | 效果 |
|---|---|---|
| `rain/rain.js` | `WeatherFX_rain` | 雨、雷暴、冰雹 |
| `snow/snow.js` | `WeatherFX_snow` | 雪、暴风雪、雨夹雪的雪部分 |
| `snow/fog.js` | `WeatherFX_fog` | 雾 |
| `snow/sand.js` | `WeatherFX_sand` | 沙暴 |
| `daylight/daylight.js` | `WeatherFX_daylight` | 昼夜调色、灯光、星月与极光的水面倒影 |
| `fantasy/fantasy.js` + 四个 `fantasy-*.js` | `WeatherFX_fantasy` | 魔力风暴、灵雾、瘴气、灰烬雨 |
| `aurora/aurora.js` | `WeatherFX_aurora` | 写意极光帘幕，不是实际天空几何 |
| `ice/ice.js` | `WeatherFX_ice` | 冻雨、霰、霜、雾凇 |
| `wind/wind.js` | `WeatherFX_wind` | 台风、龙卷风；雨由 rain 组合绘制 |
| `sky/sky.js` | `WeatherFX_sky` | 霾、浮尘、扬沙、热浪、太阳雨、彩虹 |

共同接口：`create({seed, noise})`、`resize(widthCss,heightCss,dpr)`、`setScene(scene)`、`update(state,dtSeconds)`、`draw(ctx,pass)`、`dispose()`。共用 `noise.js` 的 `WeatherNoise`。

pass 顺序：`ground → reflect → precip → fog → light → bow → aurora → flash`。

## 4. 代码需求，按优先级

### P0：修复被打断的天气生成扩展

**11-06 后续修复状态**：在原生成器上补齐，天气专项两文件 **84 passed（31.78 秒）**；原有 33 项测试保留。Python/JS 全字段一致、28 种天气及 11 项累积量可用，`ground.graupel` 纳入正式契约。低纬/极地西移、中纬东移及日界线周期、有界缓存已实现；枚举覆盖校验已修。自然台风要求显式 `coast_distance_km <= 200`，未输入距离时不猜沿海。下面清单保留为本批要求和故障历史，接口与限制见 `docs/weather.md`。

上下文缓存上限 128，64 格实测首次 4.41 秒、重复 5.50 毫秒、下一小时 24.61 毫秒；大区域冷启动仍需要预计算策略。Edge 无头检查遍历 28 种手动天气、16 个预设、生成模式和台风风眼，无脚本异常，10 模块就绪。总预览补积霰控件、预设零值及风眼参数到生成器的传递。运行检查不代表各天气目视、DPR2、移动端性能或无障碍验收完成。未接正式地图和游戏状态。

- 不要从零重写。原中断状态为 `_step()` 返回 6 项地面状态，但 `GROUND_NAMES` 已是 10 项，`_state()` 在组装状态时 `IndexError`，导致 `tests.test_weather` 33 项中的 30 项报错；后续已修复。
- 完整对齐 Python 和 JS 的状态字段、累积积分、校验和 overrides：旧六项加 `glaze/frost/rime/dust_cover`；明确 `ice.js` 可选的 `ground.graupel` 是否纳入正式契约，不允许各模块默默使用不同字段。
- 第四批 11 种天气见 weather-spec 第 8 节。保证自然生成与手动指定都能出合法状态；奇幻天气仅在世界明确允许时进入随机池。
- 不能通过删除测试或只补零值来掩盖未实现的累积逻辑；新增累计、消退、矛盾参数和 Python/JS 一致性测试。
- 台风的沿海条件不能仅用低海拔冒充海岸距离；上层暖层、污染来源等没有输入时，只能声明为游戏近似。
- 原风锋全球恒速东移、跨 180° 经线不连续，后续已修经度周期、风带和有界缓存。首次新地点仍回看约 216 小时，正式大地图的采样与冷启动策略仍待集成。

### P1：天气总预览合成与视觉验收

- 总预览默认晴天已能本地启动，10 模块就绪、无 pageerror；仍须验证所有天气、各档强度、自动播放和生成器模式，不能把手动代理状态当作生成器完成。
- 底图必须先栅格化到同一 canvas：multiply 调色和热浪回读需要真实底图像素，不能只在透明 canvas 上乘色。
- 台风/龙卷通过 wind 的 `rainState()`、`daylightState()` 适配，避免风层、雨层、昼夜三次压暗；风眼应能明显转亮。
- 雨雪局部积层、屋檐滴水、结冰、倒影只能落在对应场景区域；`scene.occluder`、water、ground、lights 与画面坐标/DPR/缩放严格一致。
- 暂以旧城镇样例测试；迁移到 v2 布局时同步 scene 提取与剪影，不改世界地图。切场景或销毁页面要 dispose、取消 RAF、释放离屏缓冲。
- 加 reduced-motion、暂停与闪电减弱/关闭设置。性能目标只是目标：组合效果需在普通浏览器桌面/移动端、DPR1/2 实测，不能用无头高刷新率认定达标。

### P2：城镇布局 v2 收官

- 本次复跑 18 项布局测试全部通过，v2 预览本地打开能出图、无脚本错误；仍须逐风格目视验收，不再声称仅有最早的方形布局。
- 保留 `layout()` 兼容签名；支持不规则/方形城墙、terrain 输入、fortification/landmarks 参数、`site_layout()`、经营档案 id。
- 渲染必须遵守 meta 的 anchor/viewBox/pad_x/sort_offset，不能假设所有 viewBox 原点为零。东方节点选择、两遍护城河、棱堡 `attach_cells/joins_spokes` 替换墙段均按各目录 README。
- 道路是四角状态双网格，不是完整独立八向道路网；城墙另有 8 向辐条。若玩法要求真 45° 道路，需要另立需求，不要把双网格 16 组合称为八向道路。
- 建筑占地不重叠、道路连通、城门在正交直段、缺失设施明确记录、地标不越界。世界位置继续取 civ-atlas 的稳定引用，不另建默认地图引擎；terrain 适配层为未来换源保留。

### P3：元素库与经营接口整理

- `town-buildings` 源 JSON 和正式库当前均 748 条；晚出的 race-fort-2 新要塞需重新覆盖核对与增量导入。
- `tests.test_town_art_elements` 5 项中 1 项失败：KIND_NAMES 缺 `stone_bastion/terraced_mountain_city/canopy_fortress/thorn_bastion/stake_warcamp` 五个中文名。补映射、重跑生成和测试。
- 用 encyclopedia 的现有增量版本化导入接口，先备份；构库开关用 README 的完整显式清单加 `--with-town-buildings`，不覆盖其他分区。当前全库 50 分区/2198 元素含其他会话增补，不把它们归成本次产物。
- 经营接口仅为草案，7 项测试通过不代表经营逻辑正确：禁止直接启用占位日产量/税收/水量。仓储容量不等于可用水，行政厅不凭空产币，矿井未指定矿种不得默认铁矿，烧炭窑不得映成开采煤矿，牙料作坊不等于天然产象牙，酒坊/丝坊等应区分种养与加工。
- 后续补明确计量单位与货物/配方选择规则，支持同资源多用途，不按 resource 一项误判整条产业链；遵守 `docs/units.md`（公制、整数铜币）。

## 5. 剩余美术验收项（不是要求重画整套素材）

**11-06 用户验收追加**：HTTP 总预览的部分覆盖与雪层缩小错位已修复 DPR 合成坐标；aurora/ice/wind/sky 已改同源脚本加载，解决 CSP 拒绝执行。后续美术智能体请读 `docs/weather-art-review-2026-11-06.md`，含用户原图、修复后截图、待复核的积雪/灯光/倒影问题及复现参数。此次没有重画素材，不把修复后的代码覆盖问题继续列为美术缺陷。

- 冰冻模块代码已有，但 README 结果段只有占位标记，需补截图与验收记录。
- wind/sky 作者未能目视截图；重点看漏斗云、弱台风过暗、眼墙过白、彩虹位置、热浪折射与扬沙性能。
- 奇幻天气夜间截图未核对；强极光地面染绿偏重，俯视帘幕压在房顶上属于写意。
- 雨洼偏深像污渍、轻雨过淡；中雾偏平、沙暴偏糊；港口旧样例窄水面限制倒影展示。
- 建筑主要是可用素材，小动物和摆件细节偏小；部分资源点地面仍硬边；斜向防御工事有伸出本格的几何，必须按元数据摆放，不能强裁。

## 6. 验证命令与本阶段边界

```powershell
.venv/Scripts/python -m unittest tests.test_weather
.venv/Scripts/python -m unittest tests.test_town_layout tests.test_building_economy tests.test_town_art_elements
.venv/Scripts/python -m ruff check app/weather.py tests/test_weather.py
node app/static/map-art/town/build-index.js
```

完成后在已生成城镇上验收：晴昼/晴夜、雨雪三档、台风风眼、冰冻、奇幻夜景、极光云遮和彩虹；DPR1/2，无未知 symbol 引用、无运行错误，画面非空且动画推进。

本阶段不接入 civ-atlas、play_map、map-fog、play-ui、runtime/web 或旅程存档，不启停用户服务。正式接入地图、旅行判定、经营结算需要另一次明确授权。原有他人改动不回退；Terragenesis 仅只读参考。

## 11-06 城镇真实生成接入追加（用户授权复用现有资源）

此前「主要离线样例」「五种中文映射缺失」的状态已更新：

- 用户最新要求完善城镇生成系统，本次已接真实草稿与不可变版本的在线布局接口及城镇创作面板，复用现有 1606 个 symbol；支持风格、种族、工事、墙形、地标、种子、设施定位、覆盖清单、资源地块、缩放和地图 JSON 导出。
- 资源点沿用同一个技术与燃料闭包，不显示未勘探矿脉为开采地块；失效草稿拒绝生成且清除旧图；异族与文化回落及地形取消城墙均有提示。
- 五类要塞中文名已补齐，重生成候选 JSON 为 753 条 / 1606 个 symbol。本次未导入正式百科数据库，正式库锁定版本保持原状。
- 规则、布局、经营接口、美术候选及新增接入专项共 73 项通过、123 项子测试；真实 HTTP / 现行 CSP 浏览器检查通过，无 pageerror 或 CSP 违规。证据：artifacts/town-plan/。
- 经营参数仍未标定，正式旅程地图接入仍待独立实施。美术缺项与复核记录为 docs/town-art-review-2026-11-06.md，具体操作与接口为 docs/town-generation.md。

