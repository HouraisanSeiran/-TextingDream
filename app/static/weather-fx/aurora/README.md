# aurora：可直接看见的极光叠层（尚未接入游戏）

规范：`docs/weather-spec.md` 第 1 节（`aurora: {strength, hue}`）、3.1–3.3 节（接口 / scene / pass）、第 5 节（极光规则与三档）、第 6–7 节（测试方式、`scene.occluder`）。

`daylight/` 只把极光画在水面倒影里。城镇是 3/4 斜俯视，画面里没有天空，所以这个模块把极光直接画在画面上部，并给整个城镇染一层环境光。

## 文件
| 文件 | 内容 |
|---|---|
| `aurora.js` | 叠层模块，挂 `window.WeatherFX_aurora`（Node 下 `module.exports`） |
| `preview.html` | 预览页：城镇样例（村落 / 城镇 / 城市 / 港口 / 要塞）、风格、强度、色相、云量、时刻、叠 daylight 开关、暂停；角落显示 fps |
| `preview-town.js` | 底图：`layout-samples.js` + `town-render.js` 画城镇，分「地面+水」「建筑/树」两张栅格化，建筑那张同时当 `scene.occluder`。只调用 `daylight/preview-town.js` 的 `DaylightTown.raster / symbolText`，不改 daylight 的文件 |
| `preview-main.js` | 主循环 |

## 接口
```js
var layer = WeatherFX_aurora.create({ seed, noise: window.WeatherNoise });
layer.resize(w, h, dpr);
layer.setScene(scene);          // 可为空；有 scene.occluder 时屋顶朝上部分额外加亮
layer.update(state, dt);
layer.draw(ctx, 'aurora');      // 其他 pass 名不画
layer.dispose();
layer.info();                   // { s, hue, vis, night, curtains }，调试用
WeatherFX_aurora.auroraCol(hue), WeatherFX_aurora.nightness(hour, sunrise, sunset)
```
坐标都用 CSS 像素，`draw` 内部自己 `setTransform(dpr)`。

## pass：新增 `aurora`
顺序：`ground → reflect → precip → fog → light → aurora → flash`。
极光要盖在 `light` 的夜间调色之上才亮，所以必须画在 `light` 之后；闪电闪白仍在最上层。**总预览页 `index.html` 合成时要在 light 与 flash 之间调用 `layer.draw(ctx, 'aurora')`。**

## 参数规则（与 `daylight.auroraParams` 一致）
- 强度 `s = state.aurora.strength`；没给 aurora 且 `kind === 'aurora'` 时用 `intensity`（缺省 0.6）；否则 0。色相 `state.aurora.hue`，缺省 0。
- 可见度 `vis = night × (1 − smoothstep((cloud_cover − 0.35)/0.5)) × (1 − 0.8·fog)`；降水类（drizzle / rain / storm / sleet / snow / blizzard / sandstorm）再 ×0.15。
- `night` 是 daylight `palette()` 的「天黑程度」一栏，关键帧、昼夜压缩规则与午夜帧逐项照搬，两个模块在任何时刻给出的值相同。白天为 0，什么都不画。
- 颜色：hue 0 绿 (70,255,140) → 0.5 青紫 (110,150,255) → 1 品红 (255,90,210)，与 daylight 的 `auroraCol` 相同。

## 画法
1. **帘幕**：1/4 分辨率缓冲（1400×900 时 350×149，覆盖画面上方 66%）。每帧逐列算：
   - 下沿高度 = 超低频 fbm2（整条大幅弯折）+ 低频 fbm2（褶皱）+ 中频 noise2 + 小正弦，相位 `ph` 按 `0.3 + 1.5·s²` 积分，强度越高摆得越快，调强度时画面不会跳；
   - 射线亮度 = fbm3（第三维为时间），射线随褶皱横移；褶子侧看处（下沿斜率大）加亮；
   - 横向断续用 fbm2 包络，明暗脉动用 noise2，射线长度也用噪波变化；
   - 竖向条纹取预烘的 128² 平铺纹理；云量 > 0.08 时用另一张平铺纹理挡掉部分帘幕。
   逐像素按「离下沿的距离」查 64 级色表累加，`putImageData` 后放大 4 倍 `lighter` 叠上，再叠一遍略放大的副本当辉光。
2. **分层色**：色表下沿是品红 / 紫边（`s > 0.5` 起出现，0.85 满），上部偏绿，下沿一道淡亮芯。强档三条帘幕分别用主色、主色与副色的中间色、副色。
3. **光弧**：画面上缘一道压扁的椭圆环径向渐变，弱档时它是主角，强档时减半。
4. **地面环境光**：整屏 soft-light 淡染极光色，再叠一层自上而下变淡的 lighter 渐变，两者都随强度上升。有 `scene.occluder` 时，用「剪影减去下移 5px / 11px 的自身」得到每个剪影顶部的一条带（屋顶朝上部分），染色后 lighter 加亮。这一步只做合成，不读像素，场景或色相变了才重烘。

## 三档
| s | 效果 |
|---|---|
| 0.0–0.3 | 只有画面上缘一道淡绿光弧，地面几乎不染色（帘幕从 0.2 起淡入，0.3 前很弱） |
| 0.3–0.7 | 一条帘状光幕横贯上部，下沿缓慢起伏，竖向射线可见 |
| 0.7–1.0 | 三条多色光幕铺满上半屏，下沿品红边、上部偏绿，摆动更快，地面染色明显 |
云量 0.35 起被压暗，0.85 以上基本消失；云团斑块会先挡掉部分帘幕。

## 性能
每帧逐列约 350 × 3 条 × 6 次噪波调用，再逐像素查表累加（最多约 350×149×3），一次 `putImageData`（约 52k 像素），之后是几次全屏 drawImage / fillRect。实测 fps 见下节。

## 自检记录
- `node --check` aurora.js / preview-town.js / preview-main.js：退出码 0。
- 截图脚本（Playwright + 本机 Edge，1400×900，`?pause=1&t=12` 固定画面，叠 daylight）：`artifacts/weather/aurora-0.2.png`、`aurora-0.5.png`、`aurora-0.9.png`、`aurora-0.9-cloud0.8.png`、`aurora-noon.png`、`aurora-0.9-hue1-city.png`。pageerror / console error 为 0。
- fps（港口样例、强度 0.9、23:00，headless Edge，两次实测）：dpr 1 约 93–107，dpr 2 约 55–66；每帧 JS 工作量约 7–8.5 ms（最大约 14 ms，含 daylight 叠层）。

## 已知问题
- 3/4 斜俯视画面没有真正的天空，帘幕直接盖在画面上部的房子上，是「抬头看见的天光」的写意画法，不是透视正确的天空。
- 弱档光弧盖在城镇顶部，顶部是房子而不是地平线，空间关系不完全对。
- 帘幕颜色用 lighter 叠加，叠在本来就亮的灯光、屋顶上会偏白。
- 云遮挡只用一张平铺噪波斑块近似，和 daylight 的云影位置不对应。
