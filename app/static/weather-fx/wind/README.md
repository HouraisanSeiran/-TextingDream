# 强风天气叠层：台风 / 龙卷风（`WeatherFX_wind`）

规范：`docs/weather-spec.md` 第 3、7、8 节。尚未接入游戏，只有素材和预览页。

| 文件 | 内容 |
|---|---|
| `wind.js` | 叠层模块，挂 `window.WeatherFX_wind`（Node 下 `module.exports`，只用于 `rainState / daylightState`） |
| `preview.html` | 预览页：城镇底图 + daylight + rain + wind 合成 |
| `preview-town.js` | 城镇底图（`layout-samples.js` + `town-render.js`）、算 `scene`、栅格化 `scene.occluder` 与整图 `scene.townImage` |
| `preview-main.js` | 控件 → 天气状态、主循环、测试钩子 `window.__wind` |

## 接口（同 3.1）

```js
var wind = WeatherFX_wind.create({ seed, noise: window.WeatherNoise });
wind.resize(1400, 900, dpr);
wind.setScene(scene);            // 用 water、buildings；有 scene.occluder 时取剪影上沿做摆动光带
wind.update(state, dt);          // kind = typhoon / tornado；其他 kind 淡出到不画
wind.draw(ctx, pass);            // 只响应 reflect / precip / fog，其余 pass 直接返回
wind.stats(); wind.dispose();

WeatherFX_wind.rainState(state)      // → 给 WeatherFX_rain 的状态（不改原对象）
WeatherFX_wind.daylightState(state)  // → 给 WeatherFX_daylight 的状态（不改原对象）
```

读的字段：`kind`、`intensity`、`wind{dir_deg,speed,gust}`、`cloud_cover`、`cyclone{category,phase}`（台风）、`vortex`（龙卷，为 0 或缺省时退回 `intensity`）。
`draw` 内部 `setTransform(dpr)`，坐标全是 CSS 像素。所有随机由 `seed` 派生（mulberry32 + `WeatherNoise`）。

## 和 rain / daylight 的组合（8.4：台风 = 自己的强风层 + `WeatherFX_rain` 大雨）

风层不画雨。预览页同时建三个模块，每帧：

```js
dl.update(WeatherFX_wind.daylightState(st), dt);
rain.update(WeatherFX_wind.rainState(st), dt);   // rain 用 tint:false，调色统一交给 daylight（同 index.js）
wind.update(st, dt);
// 城镇栅格先画进同一张 canvas，再按 ground → reflect → precip → fog → light → flash 逐 pass 调 dl / rain / wind
```

`rainState` 的改写：

| 输入 | 给 rain 的 kind | intensity | lightning（state 没给时） |
|---|---|---|---|
| typhoon outer | `storm` | (0.40 + 0.55·I)·(0.9 + 0.05·(等级−1)) | 0.12 |
| typhoon eyewall | `storm` | (0.78 + 0.22·I)·同上 | 0.25 |
| typhoon eye | `clear`（雨骤停；地面湿度是累积量，rain 照画湿地） | 0 | — |
| tornado | `storm` | max(I, 0.45 + 0.45·vortex) | 0.45 + 0.4·vortex |

台风的 `wind.speed` 在给 rain 时至少 0.7（8.2）；风眼时乘 0.12。
`daylightState`：台风外围 / 眼墙和龙卷都当 `storm`、`cloud_cover=1` 压暗去饱和；风眼改成 `cloudy`、`cloud_cover=0.4`，天空转亮。

**合成注意**：daylight 的 `light` pass 用 `multiply` / `soft-light`，必须画在已含城镇像素的同一张 canvas 上。
如果城镇是 canvas 下面的 DOM/SVG，透明画布上的 multiply 会变成一整片乘色（第一轮截图就是这样整屏发灰、风眼整屏发白）。
预览页因此把城镇整图栅格化成 `scene.townImage` 先画进 fx 画布，DOM 里的 SVG 只用来算布局。

## 做法与噪波（全部用 `WeatherNoise`，逐像素的只算低分辨率缓冲）

| 效果 | pass | 做法 |
|---|---|---|
| 快速低云影 | fog | 96×62 缓冲，`fbm3`（第三维 = 时间），坐标转到「沿风 / 横风」坐标系里沿风拉长，偏移每秒 0.3–1.3 个噪波单位（普通云影约 0.02），每 2 帧重算，放大铺满 |
| 眼墙白茫雨幕 | fog | 同尺寸缓冲，`fbm3` 沿风高频、横风低频，形成向下风扫过的白色条带 + 一层底雾 |
| 风眼 | fog | 云影与碎屑降到约 5%，整屏暖色提亮，四角径向渐变压着眼墙暗云；rain 改成 `clear`，水面保留约 45% 的白浪余涌 |
| 水面白浪 | reflect | 两张预烘可平铺噪波（`tile`，256 / 128 px）旋到风向、沿风拉长 2–3 倍、随风推移；一张深色噪波压暗翻涌；按水面面积撒浪尖短弧（对象池 380），强风时背风拖出飞沫 |
| 树冠 / 屋顶摆动 | precip | `scene.occluder` 降到 1/3 分辨率取上沿点（不透明且上方透明，最多 2600 点），每点按自己的相位沿风抖出一小段亮线；再画一张半分辨率浅色剪影，顺风来回错位成淡残影。不改底图。没有 occluder 时退回建筑包围盒屋顶线 |
| 碎叶 / 树枝 / 碎屑 / 尘 | precip | 对象池 900，从上风边缘吹入（另有 35% 在画面内淡入），速度 = 风速 × 阵风；`noise3` 湍流给横向扰动和上下翻飞；按种类和色桶批量描边 |
| 阵风 | — | `fbm2` 随时间起伏；按种子间隔 5–16 秒来一阵大风（约 0.25 秒冲上、1.2 秒退下），碎屑密度 ×2.6、白沫变亮 |
| 风线 | precip | 对象池 240，顺风细长淡白线，分 4 档亮度批量描边 |
| 龙卷漏斗 | precip | 24×40 粗网格 `fbm3` 沿「漏斗正面角度 θ × 高度」采样（θ 减自转角、随高度扭转，得到螺旋条纹），双线性插到 84×150 缓冲，再放大到漏斗包围盒；圆柱明暗、左侧亮边、噪波粗糙边，底部混入尘色 |
| 龙卷碎屑环 / 尘环 | precip | 极坐标对象池 420：向内螺旋、角速度 ∝ 1/r、靠近时被抬升；后半圈画在漏斗后面，前半圈在前面。尘环 80 个径向渐变团块 + 地面扁平尘裙 |
| 吸入风场 | precip | 着地后普通碎屑叠加一个朝漏斗底部的「向心 + 切向」速度场，近处被抬起后消失 |
| 龙卷位置 | — | 按种子选画面左或右（离中心 18%–33%），用两个低频正弦缓慢漂移、顶部倾斜摆动 |

高 dpr（>1.25）下 precip 先画进 CSS 分辨率离屏缓冲再一次放大（同 rain.js）。

## 三档（8.3）

| intensity | 台风 | 龙卷风 |
|---|---|---|
| 0.0–0.3 | 外围雨带：rain 中雨斜雨，云影快速掠过，零星碎叶，水面轻微白沫 | 远处一道细漏斗，灰蓝半透明、不着地；天色只是阴雨 |
| 0.3–0.7 | 暴雨横飞（rain storm），碎屑成群、偶有一大阵，树冠屋顶摆动光带明显，水面白沫条纹 + 浪尖 | 漏斗着地，底部尘裙、尘环、碎屑环绕，周围碎屑向漏斗汇聚；天色压成雷暴 |
| 0.7–1.0 | 等级 5 + `eyewall`：白茫雨幕、碎屑横飞、满水面白浪飞沫；`eye`：风雨骤停、天空转亮，只剩水面余涌 | 粗大楔形漏斗、碎屑云、强吸入风场、频繁闪电 |

`cyclone.category` 1–5 把风力乘 0.8–1.2；`phase` 切换在约 1 秒内平滑过渡。

## fps（无头 Edge，1400×900，daylight + rain + wind 全开，最重档：台风 5 级眼墙 0.9 / 龙卷 0.9）

| | dpr=1 | dpr=2 |
|---|---|---|
| 台风 0.9 eyewall | 51–64 | 44–53（早期版本 26–30） |
| 龙卷 0.9 | 44–58 | 34–50（早期版本 15–18） |
| 龙卷 0.9 只开风层 | 60 | 60 |

同一配置多次测量相差 10 fps 以上（无头模式 rAF 抖动），dpr=2 偶尔比 dpr=1 还快，只能当量级看。
分模块计时（`__wind.profile`，含 getImageData 同步，偏大）：风层 draw 里 precip 和 fog 各占一半；
龙卷 precip 主要是碎屑环批量描边，fog 主要是两张整屏缓冲放大与径向渐变。

## 测试钩子

`window.__wind`：`set({kind,intensity,cat,phase,vortex,dir,speed,gust,hour,rainOn,dayOn})`、`warm(秒)`、`pause(bool)`、`stats()`、`profile(n)`、`fps(ms)`；
`window.__occluderReady` 在城镇栅格与 occluder 都就绪后为 true。

## 已知问题

- 台风 0.2 与 0.5 的整体亮度几乎相同（像素均值 78 / 77，晴天 155）：两档的区别主要靠碎屑数量（约 60 / 320）、风线、浪尖和雨量，压暗程度没有拉开；0.2 偏暗，城镇细节对比降到晴天的 40% 左右。
- 龙卷 0.2 比台风 0.2 还暗（均值 65）：wind 的壁云压顶 + daylight 阴雨 + rain storm 云影三者叠加。
- 眼墙 0.9 均值 108、细节对比只剩晴天的 19%，白茫是否过重需要人看。
- 港口样例水面只有 9 格，白浪 / 浪尖面积小；更大水面的样例未测。
- dpr=2 下 precip 在 CSS 分辨率画再放大，碎屑与亮线略软。
- 预览页把 DOM 里的城镇 SVG 栅格化后画进 fx 画布（daylight 的 multiply 需要），SVG 仍留在 DOM 下层只用来算布局。
