# 雪 / 雾 / 沙暴 天气叠层（Canvas 2D；尚未接入游戏）

规范：`docs/weather-spec.md` 第 1、3 节。三个模块接口相同：

```js
var layer = WeatherFX_snow.create({ seed, noise: window.WeatherNoise });  // 另有 WeatherFX_fog、WeatherFX_sand
layer.resize(wCss, hCss, dpr); layer.setScene(scene); layer.update(state, dt); layer.draw(ctx, pass); layer.dispose();
```

调用方先 `ctx.setTransform(dpr,0,0,dpr,0,0)`，模块按 CSS 像素画。各模块只在自己负责的 kind 下出图，其余 kind 淡出到不画，所以三个都挂上、每个 pass 依次调用即可（`preview.html` 就是这么做的）。

| 文件 | 全局 | kind | pass |
|---|---|---|---|
| `snow.js` | `WeatherFX_snow` | `snow` `blizzard` `sleet`（雪部分） | `ground` `precip` `fog` |
| `fog.js` | `WeatherFX_fog` | `fog`，以及任何 `state.fog > 0` | `fog` |
| `sand.js` | `WeatherFX_sand` | `sandstorm` | `ground` `precip` `fog` |
| `preview.html` | — | 规范第 6 节：`layout-samples.js` + `town-render.js` 画生成好的城镇（下拉切换全部 75 个样例，默认 `port/west/common/1`，`?town=` 可指定）；scene 从布局算出（道路格→ground、水格→water、建筑 viewBox 包围盒→buildings、窗/篝火/稀疏路灯→lights），另把建筑、城墙、树的 symbol 栅格化成 `scene.occluder` | — |

读取的 state 字段：`kind` `intensity` `wind.{dir_deg,speed,gust}` `visibility` `fog` `temperature_c` `ground.snow_cover` `time.{hour,sunrise,sunset}`（仅雾里灯晕用）。

## snow.js
- **precip**：四层对象池（远 650 / 中 300 / 近 90 / 失焦 14），数量、下落速度随 intensity；远层小慢淡、近层大快，0.15 以上才出近层，0.4 以上才出失焦大雪片。每片雪用 `noise2(ph + t)` 一维噪波轨迹左右飘摆；风横推按层乘不同系数（近层受风大，形成视差）；阵风 = `fbm2(t)` 调制。blizzard：中近景改画顺风短线（一次 `stroke` 批量），失焦雪片沿风拉长成糊镜雪痕。sleet：数量减半、下落加快、颜色偏灰、近层画短线。
- **ground**：积雪遮罩在 `snow_cover` / 气温 / 场景 / 尺寸变化时才重烘（半分辨率）。势场 = 域扭曲（两张 `tile` 低频噪波偏移坐标）后的大块 fbm + 中频 + 高频星点（cover 低时星点权重高）；道路被踩减分。阈值按**分位数**取，`snow_cover` 直接对应覆盖面积；边缘薄雪偏蓝，用势场梯度做背光面。
  - 屋顶积雪：若 `scene.occluder`（可选，与场景同尺寸的前景剪影画布）存在，就按剪影抠掉地面积雪，并沿剪影上沿逐列堆雪（屋脊、烟囱、树冠顶都积雪，厚度带噪波，下方一道冷色阴影）；没有时退回沿 `buildings[].roofY` 画一条噪波起伏的雪带（高积雪带雪檐下垂）。
  - 水面结冰：`ice = smoothstep(0.35,0.75,cover) × smoothstep(1℃,-5℃,temp)`；预烘冰色 fbm 纹理 + 随机折线裂纹（环绕绘制保证可平铺），外缘描一圈薄雪。
- **fog**：雪天轻微提亮偏冷；能见度低时自上而下的白茫渐变 + 两张预烘雾团纹理（大慢、小快）随风平移。

## fog.js
- 低分辨率雾场（10 px 一格），`fbm3(x/260, y/120, z)`，第三维是时间，雾带横向拉长；叠加「低洼度」（水边最高、道路居中、建筑上半部最低，屋顶从雾里露出）。
- 雾场每 0.7 s 分帧算完一张，两张之间用 `lighter` 叠加做精确交叉淡化，不跳变；同时随风平移。
- 四分之一分辨率离屏合成，再用一张预烘噪波纹理以两种速度 `destination-out` 挖出丝缕，最后整屏放大。
- 远处（画面上方）按能见度整体发白；`scene.lights` 处画暖色柔光圈（`lighter`），夜间强、白天弱，雾越浓晕越大，篝火闪烁。

## sand.js
- **fog**：先 `multiply` 黄褐染色，再盖自上而下的尘雾渐变，再叠三层预烘 fbm 尘幕（横向不等比放大，速度 0.45 / 0.8 / 1.35 倍风速）随风高速平移。
- **precip**：900 粒细沙对象池，按景深分三批，每批一次 `stroke` 画运动拖影；纵向用噪波上下颠簸。另有至多 70 条贴地流沙线，噪波扭动、淡入淡出。
- **ground**：薄黄土 + 噪波扭曲的沙痕纹理，道路积沙更多，水面与建筑立面挖掉；按 intensity 量化 20 档，变档才重烘。规范的 `ground` 里没有沙尘累积量，这里用 intensity 近似。

## 强度
| intensity | 雪 | 雾 | 沙暴 |
|---|---|---|---|
| 0–0.3 | 稀疏远中层慢落，地面星点 | 低洼处薄雾带，地面清楚 | 薄黄褐、细沙粒、零星流沙线 |
| 0.3–0.7 | 雪花分层出近景，积雪成片，屋顶积雪，水面开始结冰 | 雾带连片，远处发白，灯晕 | 尘幕明显流动，近景模糊 |
| 0.7–1 | blizzard：横飞雪线、糊镜雪痕、白茫、厚积雪 | 只剩近处轮廓 | 能见度很低，只剩近处轮廓 |

预览页的「联动」勾选时，切天气/拖强度会自动给出自洽的积雪、雾、能见度、气温（只为预览方便，模块本身只读 state）。URL 参数 `?dpr=2` 强制 dpr。

## 性能
只用 Canvas 2D；粒子全用对象池，不在帧内分配；积雪、雾团、尘幕都是预烘纹理放大平移；积雪遮罩只在 cover/气温/场景变化时重烘（1400×900 约数十毫秒，拖滑杆时会有短暂卡顿）。
