# 天气系统规范（生成 + 美术效果；生成已接旅程只读投影，Canvas 特效未接）

用户需求：天气随机生成，也能按给定参数生成；美术做雨天、雪天、风暴等，按天气强度调整效果；按 24 小时实时时间变化景色。参考 B 站 Mushreb 的《2D 游戏中的雨天效果》《雪天效果》《夜空倒影效果》（Godot，大量用噪波）。只参考思路，不复制素材。

## 1. 天气状态（生成系统输出、美术系统输入的唯一契约）

```json
{
  "seed": 12345,
  "time":  { "hour": 13.5, "day_of_year": 120, "sunrise": 5.9, "sunset": 18.4, "moon_phase": 0.42 },
  "kind": "rain",
  "intensity": 0.65,
  "precipitation": { "type": "rain", "rate": 0.6 },
  "cloud_cover": 0.85,
  "fog": 0.1,
  "wind": { "dir_deg": 250, "speed": 0.4, "gust": 0.2 },
  "lightning": 0.0,
  "temperature_c": 14,
  "humidity": 0.9,
  "visibility": 0.7,
  "ground": { "wetness": 0.7, "puddles": 0.4, "snow_cover": 0.0 },
  "season": "spring",
  "climate": "temperate"
}
```

- `kind`：`clear` 晴、`cloudy` 多云、`overcast` 阴、`fog` 雾、`drizzle` 毛毛雨、`rain` 雨、`storm` 雷暴、`snow` 雪、`blizzard` 暴风雪、`sleet` 雨夹雪、`sandstorm` 沙暴。
- 所有 0–1 的量都夹在 [0,1]。`hour` 是 0–24 的小数小时。`wind.dir_deg` 是风**吹向**的方位（0 = 北/屏幕上方，90 = 东/右）。
- `ground` 是**累积量**：雨停后地面湿度、水洼要慢慢退；雪停后积雪慢慢化。所以它依赖前几小时的天气，不是瞬时值。
- 美术只读这个对象，不自己推断天气。

## 2. 生成系统（后端 `app/weather.py`，前端镜像 `app/static/weather-fx/weather-gen.js`）

- **随机生成**：`weather_at(seed, day, hour, climate, season=None, overrides=None)`。由种子派生，同参数结果一致。天气按小时连续变化（天气锋面持续数小时到数天，不逐小时乱跳），用低频噪波或马尔可夫链加持续时间。
- **气候**：至少 `temperate` 温带、`continental` 大陆性、`maritime` 海洋性、`mediterranean` 地中海、`subtropical_monsoon` 亚热带季风、`tropical` 热带、`arid` 干旱（沙暴）、`highland` 高原、`polar` 寒带。每种气候按季节给出各天气的出现倾向和气温范围。可以从 civ-atlas 群系 / 纬度映射到气候（给一张对照表即可，不改 civ-atlas）。
- **按参数生成**：`overrides` 可以指定 `kind`、`intensity`、`wind`、`temperature_c` 等任意字段；指定后的字段固定，其余字段与之自洽（例如指定 `kind=snow` 时气温自动 ≤ 1℃，`precipitation.type=snow`）。
- **时间**：`time.sunrise/sunset/day_of_year` 优先调用 `app/geography.py` 的 `solar()`（需要经纬度和日历），没有时回落到 6:00 / 18:00。`moon_phase` 按 29.53 天周期从 day 推算。
- **前端镜像**：`weather-gen.js` 是同一算法的 JS 版本，给美术预览页的「随机天气」按钮用；测试里用 node 跑同一组参数，与 Python 输出逐字段比对（浮点容差 1e-6）。
- **不接入游戏**：不改 `runtime.py`、`web.py`、存档；只提供函数和测试。

## 3. 美术效果（前端 canvas 叠层，`app/static/weather-fx/`）

### 3.1 叠层接口
每个效果模块挂一个全局对象 `window.WeatherFX_<name>`（Node 不需要），形如：

```js
var layer = WeatherFX_rain.create({ seed, noise: window.WeatherNoise });
layer.resize(widthCss, heightCss, dpr);     // 画布尺寸变化
layer.setScene(scene);                       // 场景描述（见 3.2），可为空
layer.update(state, dtSeconds);              // 推进动画；state = 第 1 节的天气状态
layer.draw(ctx, pass);                       // 往给定 2D context 画；pass 见 3.3
layer.dispose();
```

- 只用 Canvas 2D（不引外部库、不用 WebGL），粒子数和噪波开销随 `intensity` 缩放，1400×900、dpr=1 下目标 60 fps，dpr=2 下不低于 30 fps。
- 噪波统一用 `app/static/weather-fx/noise.js`（`WeatherNoise`）：值噪波、fbm、域扭曲、可平铺纹理预烘。逐像素噪波要预烘成纹理或低分辨率缓冲再放大，不要每帧全屏逐像素计算。
- 所有随机由 `seed` 派生。

### 3.2 场景描述 `scene`
由预览页 / 将来的游戏从城镇布局算出：

```js
{ width, height, cell: 48,
  water:     [[x, y, w, h], ...],              // 水面格的像素矩形（可做倒影、雨点涟漪）
  buildings: [{ x, y, w, h, roofY }, ...],     // 建筑屏幕包围盒；roofY = 屋顶上沿（做屋顶积雪、檐下滴水）
  lights:    [{ x, y, kind: 'window'|'lamp'|'fire' }, ...],  // 夜间亮灯点
  ground:    [[x, y, w, h], ...] }             // 地面（道路、空地），做湿地反光、水洼、积雪
```

### 3.3 绘制顺序（pass）
1. `ground`：地面状态——湿地变暗与高光、水洼、积雪覆盖、沙尘积层。
2. `reflect`：水面倒影——天空颜色、星星、月亮、灯光在水面的倒影与扰动。
3. `precip`：降水与飘尘粒子——雨丝、溅水、雪花、沙粒；风吹斜。
4. `fog`：雾层、低云影、暴风雪白茫。
5. `light`：24 小时调色（正片叠底 / 叠加），晨昏色温，夜间暗部 + 灯光加亮（`lighter` 混合）。
6. `flash`：闪电全屏闪白与远处闪电枝。

### 3.4 强度分级（每种天气至少这三档要明显不同）
| intensity | 雨 | 雪 | 风暴 |
|---|---|---|---|
| 0.0–0.3 | 毛毛雨：细短雨丝，偶尔涟漪，地面微湿 | 小雪：稀疏慢落，地面星点积雪 | 阴风：云影快速掠过，偶有远雷光 |
| 0.3–0.7 | 中雨：雨丝加密、溅水、水洼扩大 | 中雪：雪花大小分层、屋顶积雪 | 雷雨：斜雨、阵风、间歇闪电 |
| 0.7–1.0 | 暴雨：密集斜雨、水雾、能见度下降 | 暴风雪：横飞雪、白茫、积雪厚 | 强雷暴：持续强风、频繁闪电、暗色天空 |

### 3.5 24 小时景色
按 `time.hour` 与 `sunrise/sunset` 连续插值，不分段跳变：深夜（蓝紫低亮）→ 黎明（灰蓝转粉）→ 日出（暖橙）→ 白天（中性）→ 黄昏（金橙）→ 日落（品红紫）→ 入夜（亮灯）。天气改变调色：阴雨天整体去饱和偏冷，雪天提亮偏冷，沙暴偏黄褐。夜空倒影：水面倒映星空和月亮，按月相画月亮，雨天倒影被涟漪打碎。

## 4. 目录
| 目录 / 文件 | 负责 |
|---|---|
| `app/static/weather-fx/noise.js` | 主代理（已写） |
| `app/weather.py`、`tests/test_weather.py`、`app/static/weather-fx/weather-gen.js`、`docs/weather.md` | 生成子代理 |
| `app/static/weather-fx/rain/` | 雨与风暴子代理 |
| `app/static/weather-fx/snow/` | 雪、雾、沙暴子代理 |
| `app/static/weather-fx/daylight/` | 24h 光照、夜空倒影子代理 |
| `app/static/weather-fx/index.html` | 主代理最后合成的总预览页 |

每个美术目录：`<name>.js`（模块）、`preview.html`（独立预览：用 `../../map-art/town/town-catalog.js` 拼一块城镇做底，带天气种类 / 强度 / 时间 / 风的滑杆）、`README.md`。


## 5. 第二批天气：冰雹、极光、奇幻天气（用户已确认要做，之后接入地图系统）

### 5.1 新增 `kind`
| kind | 中文 | 类型 | 说明 |
|---|---|---|---|
| `hail` | 冰雹 | 自然 | 多伴随强对流（雷暴）；`precipitation.type = "hail"`；地面散落冰粒、弹跳，之后慢慢化 |
| `aurora` | 极光 | 自然 | 只在夜间、高纬度（`polar`、`continental` 冬季、`highland`）出现；可与 `clear` / `cloudy` 叠加，见 5.2 |
| `mana_storm` | 魔力风暴 | 奇幻 | 紫青色发光云团、悬浮符文碎光、电弧状魔力闪；地面残留发光晶屑 |
| `spirit_mist` | 灵雾 | 奇幻（东方） | 带淡金 / 青白光点的流动雾带，有祥云般的卷涡 |
| `miasma` | 瘴气 | 奇幻 | 低洼处贴地的黄绿浊雾，缓慢翻滚，能见度低 |
| `ashfall` | 灰烬雨 | 奇幻 / 火山 | 灰黑飘落物 + 偶尔的火星，天色昏红，地面积灰 |

- 奇幻天气（`mana_storm`、`spirit_mist`、`miasma`、`ashfall`）**默认不出现**，只有世界设定声明了对应条件时才进入随机池（与 `mana`、`dragonbone` 资源同理）。生成函数加参数 `fantasy=()`，传入允许的奇幻天气列表；按参数生成（`overrides.kind`）时不受限制。
- 新增状态字段（其他天气为 0 或省略）：
  - `aurora`: `{ "strength": 0–1, "hue": 0–1 }`（hue 0 = 绿，0.5 = 青紫，1 = 品红）
  - `magic`: `{ "strength": 0–1, "hue": 0–1, "pulse": 0–1 }`（奇幻天气的发光强度、色相、脉动频率）
  - `ground` 增加 `hail_cover`、`ash_cover`、`mana_residue`（都是累积量，规则同第 1 节）

### 5.2 叠加规则
- `aurora` 是**天空层叠加**：`kind` 仍可以是 `clear` / `cloudy`，只要 `aurora.strength > 0` 且是夜间，就画极光；`cloud_cover` 高时极光被遮。`kind = "aurora"` 只是"以极光为主要天气"的写法。
- 冰雹可与 `storm` 同时出现：`kind = storm` 时 `precipitation.type` 可以是 `hail`。

### 5.3 强度三档
| intensity | 冰雹 | 极光 | 魔力风暴 | 灵雾 / 瘴气 | 灰烬雨 |
|---|---|---|---|---|---|
| 0.0–0.3 | 零星小冰粒 | 地平线一道淡绿光弧 | 天边紫光、稀疏光点 | 薄雾带、少量光点 / 贴地薄瘴 | 稀疏灰屑 |
| 0.3–0.7 | 冰雹密、落地弹跳、屋顶积冰粒 | 帘状光幕缓慢摆动 | 发光云团、符文碎光漂浮、间歇魔力闪 | 雾带成卷涡、遮挡远景 / 瘴气翻滚漫过道路 | 灰屑成片、天色昏红 |
| 0.7–1.0 | 大冰雹、溅冰、白色击打痕 | 满天多色光幕、倒映水面 | 旋转魔力漩涡、电弧连地、地面晶屑发光 | 能见度极低、光点成群 / 浓瘴只露屋顶 | 浓灰、火星、地面厚灰 |

### 5.4 接入地图系统的准备（生成系统负责）
- 天气要能**按地图位置**算：`weather_at(..., lon=None, lat=None)` 之外，再提供 `region_weather(seed, cells, day, hour)`，`cells` 是 `[{id, lon, lat, climate, elevation?}]`，返回每格的天气状态。
- **空间连续**：相邻格子共享同一天气锋面（用以经纬度为坐标的低频噪波驱动锋面位置并随时间平移），不能每格独立乱跳；锋面移动方向与盛行风一致。
- 只依赖经纬度、气候、高程这几个输入，不绑定具体地图源，换源后只需重新提供这几项。
- 地图层的美术（大地图上的云影、雨区、极光带）以后再做；本批只保证数据接口就绪。

### 5.5 目录
| 内容 | 负责 |
|---|---|
| 5.1–5.4 的生成与测试 | 天气①生成系统（追加） |
| 冰雹 | 天气②雨与风暴（追加，放 `rain/`） |
| 极光 | 天气④昼夜与夜空倒影（追加，放 `daylight/`，含水面倒影） |
| 魔力风暴、灵雾、瘴气、灰烬雨 | 新子代理 天气⑤奇幻天气（`app/static/weather-fx/fantasy/`） |


## 6. 本阶段的测试方式（用户已确认）

- 天气系统之后会接入地图系统，**本阶段不改地图系统**（civ-atlas、`play_map.py`、`map-fog.js`、`play-ui.js` 都不动），`region_weather` 只作为数据接口备好。
- 效果测试一律叠在**已做好的城镇上**：总预览页 `app/static/weather-fx/index.html` 用 `app/town_layout.py` 导出的布局样例（`app/static/map-art/town/layout-samples.js`）加 `app/static/town-render.js` 画出城镇，再从布局算出 3.2 节的 `scene`（水面、建筑包围盒、灯光点、地面），把全部天气叠层盖上去。
- 可切换：城镇样例（村落 / 城镇 / 城市 / 港口 / 要塞，五种风格）、天气类型、强度、时刻（含加速播放）、风向风速、随机天气按钮。


## 7. 第三批补充（主代理验收后定）

- **`scene.occluder`（可选）**：与场景同尺寸的前景剪影画布（建筑、城墙、树的 symbol 栅格化而成，不透明处 = 被前景遮住）。雪模块用它抠掉地面积雪、沿屋檐堆雪；没有时退回包围盒 + `roofY` 近似。其他模块可以用它判断「屋顶 / 地面」，不强制。
- **生成系统模型调整**（天气①b 实现，已随测试固定）：`kind=hail` 不带闪电（雷暴夹冰雹写作 `kind=storm` + `precipitation.type=hail`）；大陆性气候只在冬季出极光；降水使气温下降至多 1.5℃；积雪只在冰点下向气候基准增长；融雪对地面湿度贡献 0.4 倍；积冰每小时消退 `0.02 + 0.004*温度`；锋面东移速度恒定。
- **原第三批限制（2026-11-06 后端补齐后更新）**：现已加入经度周期空间噪声、随纬度变化的风带及有界缓存，跨 180° 经线连续。首次查询新地点仍从约 216 小时前积分；大地图整体实时性能尚未验收，详见第 9 节。
- **总预览页** `app/static/weather-fx/index.html`：见第 6 节，把 rain / snow / fog / sand / daylight / fantasy 六个叠层按第 3.3 节的 pass 顺序合成在一张 canvas 上。


## 8. 第四批天气：补齐地球常见天气（用户已确认全部补上）

### 8.1 新增 `kind`
| kind | 中文 | 出现条件（生成系统） | `precipitation.type` |
|---|---|---|---|
| `freezing_rain` | 冻雨 / 雨凇 | 近地面气温 −4～0℃、上层有暖层；温带、大陆性、亚热带季风冬季，少见 | `freezing_rain` |
| `graupel` | 霰 | 气温 −2～3℃ 的对流天，常见于冬春、高原 | `graupel` |
| `frost` | 霜 | 晴、风小、夜间到清晨、气温 ≤ 0℃；日出后 1–3 小时消退 | `none` |
| `rime` | 雾凇 | 有雾且气温 ≤ −2℃；大陆性、高原、寒带冬季 | `none` |
| `haze` | 霾 | 静风、湿度中等、多日无降水累积；温带、大陆性、亚热带季风冬季多 | `none` |
| `dust` | 浮尘 | 干旱区下风方向，风速中等；`arid`、`continental` 春季 | `none` |
| `blowing_sand` | 扬沙 | 干旱区，风速较大但不到沙暴；介于浮尘和沙暴之间 | `none` |
| `typhoon` | 台风 / 飓风 | `tropical`、`subtropical_monsoon` 夏秋，显式 `coast_distance_km <= 200`；48–72 小时，分外围 / 眼墙 / 风眼 | `rain`，风眼可为 `none` |
| `tornado` | 龙卷风 | `continental`、`temperate` 春夏，只在 `storm` 过程中短时出现（数十分钟到 1–2 小时），很少见 | `rain` 或 `hail` |
| `heatwave` | 热浪 | 晴、气温超过该气候夏季上限 + 若干度，持续多日 | `none` |
| `sunshower` | 太阳雨 | 云量低于 0.5 时的短时阵雨，多在热带、亚热带季风、海洋性 | `rain` |

### 8.2 新增状态字段（其他天气为 0 或省略）
- `aerosol`: `{ "type": "none"|"haze"|"dust"|"sand", "density": 0–1 }`：霾、浮尘、扬沙、沙暴共用；美术按它调天色和能见度。
- `rainbow`: `0–1`：雨刚停或太阳雨、太阳高度角较低（早晨、傍晚）、太阳在画面背后时出现；生成系统给强度，美术决定位置。
- `heat`: `0–1`：热浪的地面热气扭曲强度。
- `cyclone`: `{ "category": 1–5, "phase": "outer"|"eyewall"|"eye" }`：台风等级与所处位置（外围雨带 / 眼墙 / 风眼，风眼时风雨骤停、天空转亮）。非台风统一返回 `{ "category": 0, "phase": "none" }`。
- `vortex`: `0–1`：龙卷风强度；画面位置由美术按种子决定。
- `ground` 增加：`glaze`（冻雨结冰壳）、`frost`（霜）、`rime`（雾凇挂枝）、`dust_cover`（浮尘积灰）、`graupel`（地面积霰）。都是正式累积量；连同旧字段共 11 项，规则同第 1 节。
- 叠加规则：`rainbow` 和 `heat` 可以叠在允许的 kind 上（如 `clear` + `heat`、雨停后 `clear/cloudy` + `rainbow`、`sunshower` + `rainbow`）；持续的 `rain` 不直接带彩虹。`tornado` 伴随强对流的云和雨；`typhoon` 外围/眼墙 `wind.speed` 至少 0.7，风眼允许 0–0.3，默认无降水。

### 8.3 强度三档
| intensity | 冻雨 | 霰 | 霜 / 雾凇 | 霾 / 浮尘 / 扬沙 | 台风 | 龙卷风 | 热浪 | 太阳雨 / 彩虹 |
|---|---|---|---|---|---|---|---|---|
| 0.0–0.3 | 细雨、地面零星亮冰点 | 稀疏白色小粒，落地即停 | 草地、屋顶边缘一层白霜 / 树梢少量白絮 | 远景发灰黄 / 天色微黄 / 地面零星流沙 | 外围雨带：阵风、斜雨、云快速掠过 | 远处一道细漏斗云 | 远景轻微抖动 | 稀疏亮雨丝，淡彩虹 |
| 0.3–0.7 | 地面、屋檐结透明冰壳，檐下挂冰凌 | 白粒成片、弹跳、地面积一层 | 地面普遍发白、霜花纹 / 树枝全挂白 | 天色昏黄，能见度明显下降 / 扬沙成带 | 暴雨横飞，树木猛烈摇摆，水面白浪 | 漏斗云着地，周围卷起碎屑尘环 | 地面热气扭曲明显，天色发白 | 阳光下金色雨丝，完整彩虹弧 |
| 0.7–1.0 | 厚冰壳反光、树枝挂冰、冰凌粗长 | 密集霰粒，屋顶积白 | 厚霜 / 雾凇满树、屋檐冰晶 | 浓霾只见近处 / 浓尘灰黄 / 接近沙暴 | 眼墙：白茫雨幕、碎屑横飞；风眼时短暂放晴 | 粗大漏斗、碎屑云、强吸入风场 | 强烈扭曲、远景融成色带 | 双彩虹（副虹颜色反序、更淡） |

### 8.4 分工与目录
| 内容 | 负责 | 目录 |
|---|---|---|
| 8.1–8.2 的生成与测试 | 天气⑧生成系统第四批 | `app/weather.py`、`app/static/weather-fx/weather-gen.js`、`tests/test_weather.py` |
| 冻雨、霰、霜、雾凇 | 天气⑨冰冻天气 | `app/static/weather-fx/ice/`（`WeatherFX_ice`） |
| 台风、龙卷风 | 天气⑩强风天气 | `app/static/weather-fx/wind/`（`WeatherFX_wind`） |
| 霾、浮尘、扬沙、热浪、太阳雨与彩虹 | 天气⑪天色天气 | `app/static/weather-fx/sky/`（`WeatherFX_sky`） |

- 新模块接口同 3.1，pass 名沿用 3.3；彩虹画在 `light` 之后、`aurora` 之前，用新 pass 名 `bow`，最终顺序为 `ground → reflect → precip → fog → light → bow → aurora → flash`。
- 不改已有的 rain / snow / fog / sand / daylight / fantasy / aurora 模块；需要雨、雪粒子时，在自己的预览页里同时创建这些模块来组合（例如台风 = 自己的强风层 + `WeatherFX_rain` 的大雨）。
- 第 6 节的约束照旧：只在已有城镇上测试，不改地图系统和游戏代码。

## 9. 2026-11-06 后端实现状态

- `weather_at`、`forecast`、`region_weather` 已覆盖 28 种天气、全部第四批字段和 11 项地面累积；Python 与 `weather-gen.js` 镜像逐字段回归。字段始终返回，未激活效果使用零值或 `none`。
- 新输入 `coast_distance_km=None` 放在单点/预报的尾参数，也支持每个 region cell 传入。缺省不自然生成台风；低海拔不代替海岸距离。手动指定台风用于预览时不受沿海条件限制。
- 地面按小时回看 216–240 小时，冻雨结壳、霰堆积、晴冷夜间生霜、冷湿雾中生雾凇、扬沙积尘；升温、日照、降雨使对应覆盖消退。不会持久保存历史沉积。`overrides` 会把指定条件视为整个回看窗口持续，以提供可复现的预览。
- 经纬度使用周期三维噪声，低纬/极地向西、中纬向东，风带过渡平滑；未传完整经纬度时仍可按气候和时间生成。需同时提供经纬度和 `calendar` 才采用地理日出日落，否则为 06:00/18:00。
- 上下文 LRU 上限 128；每上下文自然状态上限 2048、日出日落 128、地面前缀 32。淘汰后重新生成，结果不变。`clear_cache`、`cache_info` 只用于内存缓存观测。批量接口单次最多 4096 格，保持输入顺序。
- 参数矛盾抛 `ValueError`，如冻雨配 20℃、太阳雨配厚云、`none` 降水配正速率。显式指定字段不会被静默改写。风眼允许手动少量雨，但类型和速率必须一致。
- 当前模型用于游戏表现：没有上层温度剖面、污染源输送、气压/雨影、台风真实轨迹或完整流体求解。霾、冻雨及龙卷风寿命等使用气候表和噪声近似；彩虹不求解相机与太阳几何。首次大区域查询成本仍高，缓存超过容量时会重算。
- 2026-11-08 起，生成器已通过 `app/weather_view.py` 与 `GET /api/sessions/{id}/weather` 接入旅程只读投影；
  按用户要求本轮不改前端，玩家 UI、正式地图天气层、Canvas 特效合成、旅程资源/结算均未接。
  接口示例、素材清单和验证结果见 `docs/weather.md`。
