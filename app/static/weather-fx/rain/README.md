# 雨天、风暴与冰雹叠层（`WeatherFX_rain`）

2D Canvas 叠层，城镇内部地图 3/4 斜俯视用。尚未接入游戏。接口与 pass 顺序见 `docs/weather-spec.md` 第 3 节，冰雹见第 5 节。

## 文件
| 文件 | 内容 |
|---|---|
| `rain.js` | 模块，挂 `window.WeatherFX_rain`；依赖 `../noise.js`（`WeatherNoise`） |
| `preview.html` / `preview.js` | 独立预览页：底图默认是 `layout-samples.js` + `town-render.js` 画的港口样例（有水面），`?town=grid` 换成旧的手拼小镇 |

## 覆盖的天气
`kind` = `drizzle`、`rain`、`storm`、`sleet`（只画其中的雨）、`hail`；另外 `kind=storm` 且 `precipitation.type="hail"` 时，雷暴里夹冰雹。其他 kind 下 `draw` 不画降水，但 `ground.wetness` / `ground.hail_cover` 还没退掉时，`ground` pass 照常画湿地和积冰（它们是累积量）。

## 用法
```js
var layer = WeatherFX_rain.create({ seed: 123, noise: window.WeatherNoise /*, tint: false */ });
layer.resize(wCss, hCss, dpr);
layer.setScene(scene);                 // 第 3.2 节；buildings 可额外给 eaveY（檐口高度）
layer.update(state, dt);               // 第 1 节天气状态
['ground', 'reflect', 'precip', 'fog', 'flash'].forEach(function (p) { layer.draw(ctx, p); });
layer.triggerLightning();              // 预览 / 测试：立刻落一道雷
layer.stats();                         // 粒子计数
```
- 传入 `draw` 的 ctx 用画布原始像素；模块内部自己 `setTransform(dpr)`，scene 和绘制都按 CSS 像素算。
- `tint: true`（默认）表示 ground pass 先把画面压暗、压冷。与 daylight 叠层合成时，如果调色由 daylight 负责，就传 `tint: false`。
- 本模块没有 `light` pass。

## 各 pass
| pass | 内容 | 噪波 |
|---|---|---|
| `ground` | 阴雨压暗 + 云影（低分辨率 72×46 缓冲放大，随风平移，风暴时更快）；湿斑（分位数 < wetness 的格先湿，所以小湿度时一块一块出现）+ 横向拉长的湿反光；水洼（覆盖率与 puddles 成正比，映压暗的天色，上沿有亮边，外圈一道深色水边）；积冰颗粒 | 云影 `fbm3`（第三维是时间）；湿斑 `fbm2`；水洼 `warp2`，纵向压扁；反光 `tile` 预烘 128²；积冰 `fbm2` 斑块 + `hash32` 颗粒。地面场按 3px 一格算，只在 resize / setScene 时算一次，湿度或水洼变化时才重烘 |
| `reflect` | 水面雨麻点：`tile` 预烘碎纹做 pattern，每 4 帧跳一次位置；闪电时闪电所在列出一道竖向亮带，水洼用 `lighter` 混合轻微提亮 | `tile` 128² |
| `precip` | 三层雨丝：远层细、短、淡、慢，近层粗、长、亮、快；按风倾斜，阵风是 `fbm2(t)`；落点按雨帘密度取舍；按层 × 亮度档分 12 批，每批一次 stroke。落地后：地面出溅点，水面和水洼出压扁的椭圆涟漪；屋檐下有滴水。冰雹：下落速度是雨的 1.3–1.6 倍，风吹斜的程度只有雨的 0.45；落地弹跳 1–2 次后停留并慢慢变小；高档有大冰雹、白色击打痕和溅出的冰屑 | 雨帘 `fbm3` 36×24 网格，每 3 帧更新 |
| `fog` | 雨帘白纱（与雨丝密度用同一张噪波）；暴雨水雾：e > 0.62 起，画面上方（远处）发白，叠两层平铺雾团 pattern 漂移。整层画进 1/4 分辨率缓冲后放大 | `tile` 256² |
| `flash` | 每次落雷 2–4 个亮度脉冲，起亮 20ms，然后指数衰减；云层光晕 + 全屏淡闪白；闪电枝用递归中点位移，主干、一级枝、二级枝各三层描边（辉光 / 亮芯）。落雷间隔是随机的（指数分布），平均从约 16s（lightning=0）缩到约 1.6s（lightning=1）；storm 低于 0.3 时只有远处云里一闪，不出闪电枝 | — |

## 强度三档
| e（有效雨量） | 雨 | 风暴 | 冰雹 |
|---|---|---|---|
| 毛毛雨 / < 0.3 | 约 480 条短细淡雨丝，偶尔涟漪，没有水雾 | 云影掠过，偶有远雷光 | 稀疏小冰粒 |
| 0.3–0.7 | 约 1400 条，溅点多，水洼扩大，有檐滴 | 斜雨、阵风、间歇闪电 | 冰粒变密并弹跳，屋顶有积冰粒 |
| > 0.7 | 约 2800 条长雨丝，远处发白，有雨帘 | 暗天、雨很斜、闪电频繁 | 大冰雹、击打痕、溅冰；夹在雷暴里时雨量降为 0.6 倍 |

## 性能
- 粒子全部走预分配的对象池或定长数组：雨丝 3200、溅点 1800、涟漪 900、檐滴 400、冰粒 1600、落地冰粒 1800、击打痕 300。
- 逐像素噪波只在低分辨率缓冲里算，每帧只做 `drawImage` 放大。
- dpr > 1.25 时，precip 先画进 CSS 分辨率的离屏画布再放大。dpr=2 时雨丝因此会略软一点。
- 无头 Edge 实测（1400×900，含城镇 SVG 合成；只能作参考）：dpr=1 时雨类约 57 fps，hail-09 约 45；dpr=2 时雨类约 57，hail-09 约 41。

## 预览页
`preview.html?kind=storm&i=0.8&dir=120&speed=0.7&lightning=0.6&wet=0.9&puddles=0.7&hail=0.3&ptype=hail&hour=13&dpr=2&paused=1&town=45`

控件：种类、夹冰雹、强度、风向、风速、阵风、雷电频率、地面湿度、水洼量、积冰、时刻、自动湿度、城镇样例、暂停 / 单步 / 打闪电。左上角显示 fps。页面暴露 `window.rainPreview.set/advance/strike/pause/fps` 供测试脚本调用。
