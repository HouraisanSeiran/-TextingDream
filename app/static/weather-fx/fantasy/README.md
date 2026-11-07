# 奇幻天气叠层（WeatherFX_fantasy）

魔力风暴 `mana_storm`、灵雾 `spirit_mist`、瘴气 `miasma`、灰烬雨 `ashfall`。规范见 `docs/weather-spec.md` 第 3、5 节。尚未接入游戏。

## 文件
| 文件 | 内容 |
|---|---|
| `fantasy.js` | 分派核心：`create/resize/setScene/update/draw/dispose`，按 `state.kind` 选子效果；共用工具（预烘纹理、域扭曲采样、低分辨率缓冲、场景权重图、发光精灵、电弧折线） |
| `fantasy-mana.js` | 魔力风暴 |
| `fantasy-mist.js` | 灵雾（东方） |
| `fantasy-miasma.js` | 瘴气 |
| `fantasy-ash.js` | 灰烬雨 |
| `preview.html` / `preview.js` | 独立预览：`town-render.js` + `layout-samples.js` 画城镇（灵雾默认配东方样例，其余配西式） |

加载顺序：`noise.js` → `fantasy.js` → `fantasy-*.js`。

```js
var layer = WeatherFX_fantasy.create({ seed: 2024, noise: window.WeatherNoise });
layer.resize(1400, 900, dpr); layer.setScene(scene);
layer.update(state, dt);                     // state.kind 不是这四种时什么都不画
['ground','reflect','precip','fog','light','flash'].forEach(function (p) { layer.draw(ctx, p); });
```

## 读取的状态字段
`kind`、`intensity`、`time.hour/sunrise/sunset`（夜间发光加强）、`wind.dir_deg/speed/gust`、
`magic.strength/hue/pulse`（缺省时 strength = 0.3 + 0.7·intensity，hue = 0，pulse = 0.4）、
`ground.mana_residue`（魔力风暴晶屑）、`ground.ash_cover`（灰烬积灰）。
`magic.hue`：0 紫 → 0.25 青蓝 → 0.5 翠绿 → 0.75 赤橙 → 1 回到紫；第二色固定偏移约 94°。

## 性能做法
- 每个种子预烘 4 张可平铺纹理（`WeatherNoise.tile`，256/128 像素，按 1%–99% 分位拉伸对比度）。
- 云团 / 雾 / 瘴气 / 积灰都在 1/8（积灰 1/6）屏的 ImageData 缓冲上算，每像素只做 3 次纹理双线性采样（域扭曲），隔帧重算，`drawImage` 平滑放大。积灰只在 `ash_cover` 变化时重算。
- 发光点用缓存的径向渐变小图 + `lighter`，不逐点建渐变。粒子数随 intensity 缩放。
- 所有随机由 seed 派生（`WeatherNoise.rng`）。

## 各 pass 用途
| kind | ground | precip | fog | light | flash |
|---|---|---|---|---|---|
| mana_storm | 晶屑本体 | 符文碎光线框 | 天幕暗化 + 发光云团（含漩涡） | 云团 / 符文 / 晶屑辉光、天边紫光 | 电弧 + 染色闪 |
| spirit_mist | — | 光点本体 | 雾带 + 重度白茫 | 光点辉光、夜间雾微光 | — |
| miasma | — | 孢子点 | 黄绿浊雾（重度挖出屋顶） | 浊色调、夜间磷光 | — |
| ashfall | 积灰 | 灰屑 + 火星本体 | 重度灰霾 | 昏红褐调色、火星辉光 | — |

`reflect` pass 本模块不画（水面倒影归 daylight）。

## 三档强度的样子（对应规范 5.3）
| kind | 0.2 | 0.5 | 0.9 |
|---|---|---|---|
| mana_storm | 天边（左上）一团淡紫光，零星符文碎片 | 发光云团盖住上半屏，符文碎光漂浮，间歇魔力闪 | 紫青旋涡占满全屏，电弧连地，地面晶屑发光，城镇明显被压暗 |
| spirit_mist | 几条薄雾带，少量金点 | 雾带成卷涡、青白色更显，上方远景被白茫罩住，城镇仍可辨 | 青白雾几乎铺满，只在缝隙露出街道和屋顶，光点成群 |
| miasma | 黄绿薄瘴沿道路连成带 | 瘴气翻滚漫出道路，盖住部分院落 | 浓瘴整片铺底，屋顶被挖出、仍可辨认，地面与道路基本看不清 |
| ashfall | 稀疏灰屑 | 灰屑成片，天色转昏红，道路上开始积灰 | 浓灰霾 + 火星，画面整体红褐，地面厚灰 |

## 自检
- `node --check` 所有 JS（退出码均为 0）。
- 预览页：`preview.html`（需经静态服务打开，例如以工作区根起服务后访问 `/app/static/weather-fx/fantasy/preview.html`）。`window.__preview.set({kind, intensity, hour, ...})` / `fps()` / `resetFps()` 供自动化使用。
- 截图：Playwright + 本机 Edge，1400×900，白天 13:00，每档稳定 3.2 s 后截 `#stage`；灵雾用东方城镇样例，其余用西式。输出 `artifacts/weather/fantasy-<kind>-<0.2|0.5|0.9>.png`，共 12 张。脚本同时统计 pageerror 与 console error（应为 0）。
- 页面带 `<link rel="icon" href="data:,">`，避免浏览器请求 `/favicon.ico` 报 404。

## 实测帧率（无头 Edge，1400×900，白天 13:00，`__preview.fps()` 3.2 s 平均）
| kind | dpr=1：0.2 / 0.5 / 0.9 | dpr=2：0.2 / 0.5 / 0.9 |
|---|---|---|
| mana_storm | 138 / 108 / 74 | 82 / 79 / 86 |
| spirit_mist | 101 / 80 / 81 | 110 / 106 / 111 |
| miasma | 69 / 73 / 74 | 109 / 118 / 118 |
| ashfall | 71 / 63 / 65 | 73 / 75 / 58 |

无头模式下帧率波动大（同一档两次运行相差 30% 以上），截图时角标的瞬时值在 33–74 fps 之间，只作量级参考，没在有界面的浏览器里实测过。

## 已知不足
- 灵雾 0.5 的远景白茫偏弱，「遮挡远景」主要靠画面边缘的雾带，上方不够明显。
- 瘴气 0.2 仍偏淡，只在道路交叉口和主路上看得出薄瘴。
- 只截了白天，夜间（磷光、发光增强）没有截图核对。
