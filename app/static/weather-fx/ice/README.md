# 冰冻天气叠层 `WeatherFX_ice`（冻雨 / 雨凇、霰、霜、雾凇）

规范：`docs/weather-spec.md` 第 3 节与第 8 节。尚未接入游戏，只有模块和预览页。

## 文件
| 文件 | 内容 |
|---|---|
| `ice.js` | 模块，挂 `window.WeatherFX_ice` |
| `preview.html` + `preview.js` | 独立预览：`layout-samples.js` + `town-render.js` 画城镇，算 scene / occluder，叠 ice + `WeatherFX_daylight` |
| `README.md` | 本文 |

## 接口（同 3.1）
```js
var ice = WeatherFX_ice.create({ seed, noise: window.WeatherNoise });
ice.resize(w, h, dpr); ice.setScene(scene); ice.update(state, dt); ice.draw(ctx, pass); ice.dispose();
```
- 调用方先 `ctx.setTransform(dpr,0,0,dpr,0,0)`，模块按 CSS 像素作画。
- 用到的 pass：`ground`（冰壳、霜、霰积层、边缘层、冰凌、亮冰点）、`precip`（冻雨丝 + 冰溅、霰粒）、`fog`（雾凇淡雾；冻雨 rate > 0.6 时加一层冷色水雾）。其余 pass 不画。
- 读的字段：`kind`、`intensity`、`precipitation.type/rate`、`ground.glaze/frost/rime`、`time.hour/sunrise/sunset`、`wind`、`fog`。
  - `ground.*` 有值就按值画（例如 `kind=clear` 但 `ground.frost=0.6` 的清晨照样画霜）；缺省时用当前 kind 的 intensity 近似。
  - 降水粒子只看 `kind` 或 `precipitation.type` 是 `freezing_rain` / `graupel`，因此 `kind=storm` + `precipitation.type=graupel` 也会下霰。
  - **正式累积字段** `ground.graupel`：生成系统已提供霰的地面累积量，停霰后按温度逐步消退。仅兼容旧预览时，缺字段会在 `kind=graupel` 下按 `0.06+0.94*intensity` 近似，其他 kind 为 0；这个兼容分支不是后端累积算法。
  - 霜按太阳高度消退：`sunUp = smoothstep(sunrise-0.2, sunrise+1.5, hour)`，日照下霜变薄并退到背光处。真正的消退（累积量下降）由生成系统给 `ground.frost`。
- `scene.occluder` 可选：有就用它的剪影和颜色（树叶按「偏绿」判断）；没有就用 `buildings` 包围盒从 `roofY` 往下填出近似剪影，这时无法区分树叶，檐口按 `roofY + 0.42h` 估计。

## 各 pass 做法与所用噪波
所有逐像素工作只在烘焙时做：累积量（量化到 0.01）、太阳高度（量化到 0.1）、场景或尺寸变化时才重烘，平时每帧只是一次 `drawImage` 加粒子。

- **预烘噪波**（create 时，全部 `WeatherNoise.tile`，256²可平铺）：大块 period 4×4 oct、中频 16×3、细颗粒 48×2、两张域扭曲偏移 6×3、近逐像素颗粒 128×1、霰点阵 80×1；雾团两张 128² RGBA（4×5、8×4）。
- **地面遮罩**（1/2 分辨率）：三张势场都先过域扭曲。
  - 冰壳：大块 + 中频 + 细颗粒，路面加权；按分位数让 `glaze` 对应覆盖面积。冷蓝透明底，沿中频噪波 0.55 等值线画亮条，路面更亮。
  - 霜：大块 + 中频 + 细颗粒 + 背光场 − 道路 − 日照。背光场 = occluder 模糊后上移 10px 再叠原位，所以建筑北侧与周围一圈霜更厚。霜花纹 = 中频脉络取峰（`1-|2n-1|`）+ 高频颗粒。
  - 霰积层：大块斑块内按霰点阵取阈值，点阵阈值随密度下降，厚处连成白片，斑块边缘只剩零星粒。
  - 水面不画；被 occluder 遮住的地方用 `destination-out` 抠掉。
- **边缘层**（全分辨率，逐列扫 occluder 上沿深度）：
  - 霜：上沿 1–4.5px 霜边 + 剪影整体的霜粉。
  - 冰壳：上沿 2px 亮边 + 中频等值线高光条，树叶上加亮点。
  - 霰：上沿积白，厚度随噪波逐列起伏；屋顶上撒点阵白粒。
  - 雾凇：上沿覆白，树叶整体按中频噪波大片覆白。上沿外侧和左右两侧外侧长白絮，长度按细噪波逐列变化，再用高频颗粒打散成毛刺，越往外越稀。
- **冰凌**：在每个建筑包围盒里逐列自上而下找「屋顶色 → 墙面色（亮、低饱和）」的转折，即檐口。冰凌长度 = `(2+7·glaze+6·it·glaze)` × 随机，约 15% 粗长 1.7 倍；树叶下沿挂小冰珠。雾凇 / 厚霜时檐下改挂白色冰晶短刺。
- **亮冰点**：在冰壳区按 12px 网格哈希挑点，数量 ∝ `0.05+0.5·glaze²`，路面优先。每帧用 `noise2(时间)` 调亮度，以 `lighter` 混合，产生轻微闪烁。
- **precip**：冻雨 ≤1100 根细直雨丝分两层，各一次 `stroke`；落到各自随机着地深度处留下 0.35s 冰溅。霰 ≤900 粒，三档尺寸精灵，下落 230–400px/s（雪约 30–150，冰雹更快）；intensity ≥ 0.3 时着地弹跳 1 次（反弹系数 0.32），停 0.6–2.2s 后淡出，再从上方补充。
- **fog**：均匀冷白 + 两层雾团按风缓慢漂移。

<!--@@RESULTS@@-->
