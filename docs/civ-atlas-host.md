# 原生宿主（civ-atlas）· 织梦侧集成

本页只说**织梦这边怎么把上游的原生地图画出来**，以及作者/玩家两种模式的边界。
上游改动清单、许可义务、逐字节核对在 [`civ-atlas-patch/README.md`](civ-atlas-patch/README.md)。
导出/导入的数据流在 [`civ-atlas-integration.md`](civ-atlas-integration.md)。

## 1. 一句话结构

```
external/civ-atlas/src/dream/          ← 宿主源码（直接 import 上游模块，AGPL-3.0-only）
  bridge.ts     取原件 + 切块 + 逐块校验 + 上游 unpackValue + 上游 rasterize + 打包/上传
  generate.ts   作者侧生成：上游 worker 生成 → packContainer → POST /api/inner/map-imports
  host.tsx      地图主画面 + 新建世界面板 + 挂载叠加层
  entry.tsx     mountDreamHost(el, {mode}) 入口
external/civ-atlas/vite.dream.config.ts  ← 独立构建（不动上游生产构建）
  ↓ npx --prefix external/civ-atlas vite build --config vite.dream.config.ts
external/civ-atlas/dist-dream/          ← dream-host.js + dream-host.css + assets/worker-*.js
  ↓ FastAPI 静态托管整个目录到 /native-map
/native-map/dream-host.js               ← 页面按 URL 动态 import（AGPL 产物）
/static/native-map.js                   ← 本工程写的集成（MIT），只负责加载与挂载
```

**目录分工不能混**：`/static` 是本工程自己的代码，`/native-map` 是 AGPL 构建产物。
`index.html` 里只有一行 `<script defer src="/static/native-map.js">`。

地图**不是我们画的**：`bridge.ts` 只负责把字节还原成上游的 `World` / `Civ`，然后
`host.tsx` 调 `render/export.ts` 的 `drawMapTerrain` / `drawMapCiv`——和上游「导出图片」
走同一条管线（`src/finderThumbDraw.ts:41-49` 是小图版的同一路径）。

## 2. 数据来源：一律以服务端为准

| 事实 | 谁决定 | 位置 |
|---|---|---|
| 整件 sha256（来源身份） | **服务端** | `app/native_worlds.py:40 _identity` → `identity.sha256` |
| 每块的 sum / bytes / length | **服务端**（导入时真算） | `app/civ_atlas_snapshot.py:749`，标 `sum_verified_by: 'server'` |
| 能不能保存草稿 | 作者模式 + 完整身份 | `bridge.ts: canSave`（`importId` + `worldId` + 64 位 sha） |
| 世界编号 / 生成器版本一致 | 清单 vs 服务端 | `bridge.ts: checkIdentity` |

浏览器**不算 hash**。原因不是省事：用户跨机器访问（`http://192.168.x.x:…`）时不是 secure
context，`crypto.subtle` **根本不存在**，而上游 `readPart`（`gen/snapshot.ts:136`）内部直接用它。

### 两条解码路（`bridge.ts: readVerifiedPart`）

1. **secure context**（`localhost` / HTTPS）：直接调上游 `readPart`，长度、SHA-256、压缩方式
   全由上游校验。
2. **非 secure context**：只有当服务端 metadata 给出该块的 `sum_verified_by === 'server'`
   **且** `bytes` / `length` 与实际一致时，才走「有界 inflate + 上游 `unpackValue`」；
   缺见证 **明确拒绝**（提示改用 HTTPS/localhost），绝不静默降级。

两条路都不自己实现 sha256、不自造容器格式、不新加依赖。

## 3. 作者在主入口里能做什么

右主图**只有一个引擎**：原生宿主。**没有** Python 掩膜地图的自动回退（那是另一条平行主流程，
用户已决定合并删除；自动顶上会让人看不出自己看的到底是哪个引擎）。原生起不来就在位报
真实原因（未构建 / 加载失败 / 挂载失败）+「重新加载原生地图」按钮。

| 作者动作 | 走什么 |
|---|---|
| 选已有世界 | `/api/inner/native-worlds`（带 `X-TextileDream-Token`）→ `readNativeWorld` 读回 |
| **新建世界** | 上游 `src/worker.ts` 生成 → `packContainer` → `POST /api/inner/map-imports` → 服务端登记 → 读回画图 |
| 圈建筑范围 / 用地 | `LandOverlay`（空间席维护）；保存走 `/api/inner/spatial-drafts` |

**新建世界不需要导出文件再导入**：生成在浏览器里跑完就直接打包上传（容器格式与
`tools/civ_atlas_export.js` 同口径），服务端重新解析、逐块重算 sum 并记 `sum_verified_by: 'server'`。
同一内容哈希重复上传是幂等的。空世界时参数面板自动展开——没有任何预制故事包。

## 4. 画布、投影与缩放

- canvas 位图尺寸 = `raster.w × raster.h`（真样本 2048×1024），CSS 等比缩到地图框。
- 地图框在舞台里**居中**：`left = (sw − bw)/2`、`top = (sh − bh)/2`，与
  `src/ui/mapWrap.ts:55 boxLeft/boxTop` 同一个定义；`LandOverlay` 的 `stageToWorld` / `worldToStage`
  就是按这个前提换算的，不居中就会整层错位。
- 只接等距圆柱（`linear: true`）。叠加层在弯边投影下会直接拒画，不拿线性公式冒充。

**缩放**：浏览上限 `k = 12`，就是上游自己的 `ui/App.tsx:4799 Math.min(12, …)`。滚轮与双击
按鼠标位置就地放大。作者圈地时另有「圈地放大 ×48」——它**只放大同一批 raster 像素**，
不增加地形细节（超过 12 倍时界面会明说），也**不改**后端 `MAX_FOOTPRINT_KM2 = 50` 的面积上限。

## 5. 两种模式

| 模式 | 走什么接口 | 能不能保存 | 说明 |
|---|---|---|---|
| `author` | `/api/inner/native-worlds`（带 `X-TextileDream-Token`） | 能（身份完整时） | 拿完整原件 |
| `player` | **不请求任何作者路由** | 不能 | 玩家路是服务端已遮罩的投影，本宿主目前只提示 `not_ready` |

模式由调用页决定（`mountDreamHost(el, { mode })`），**不存在**一个请求头能把玩家升级成作者。
切模式会清掉已加载的原件、画布、草稿形状，并作废切换前发出的请求（按序号丢弃迟到响应）。

## 6. 怎么验（都是真跑，不是字符串断言）

```powershell
# 1) 构建（产物 external/civ-atlas/dist-dream/，约 622 kB + worker 801 kB）
npx --prefix external/civ-atlas vite build --config vite.dream.config.ts

# 2) 主入口端到端：起临时回环服务 + 真浏览器，空世界 → 生成 → 登记 → 出图 → 刷新仍在
python tools/dream_main_entry_check.py

# 3) 数据桥：真跑 src/dream/bridge.ts（上游解码 + 上游 rasterize）
& external/civ-atlas/node_modules/.bin/tsx.cmd tools/dream_bridge_behavior.mjs <real.civsnap>

# 4) 宿主壳：真浏览器加载构建产物，真画一遍
node tools/dream_host_render.mjs <real.civsnap> external/civ-atlas/dist-dream/dream-host.js

# 5) 契约测试（样本或产物不在时 skip 并写明「未验真」）
python -m unittest tests.test_civ_native_contract -v
```

> 数据桥台本用 **tsx** 启动（它直接 import 了 `.ts`），其余用 **node**。
> 页面带 `script-src 'self'` 的 CSP，所以浏览器台本**不能用字符串 evaluate**（会 EvalError），
> 一律传函数。

最近一次真实结果（4.6 MB 真样本，`sn_2f3648720158`）：

| 项 | 值 |
|---|---|
| 容器 | 4 609 307 B，`map`/`eras`/`civ` 三块，全 gzip |
| 解码 | 34097 地块，870 州，endYear 3000 |
| 栅格 | 2048×1024（`map` 块里**没有** raster，是上游 `rasterize` 现算的） |
| 浏览器绘制 | 画布 2048×1024、颜色数 10165、不透明比例 1.0、控制台零报错 |
| 舞台 900×432 时地图框 | 864×432，左上角 (18, 0) —— 与 `(sw−bw)/2` 一致 |
| 非 secure 上下文 | 有服务端见证能读（栅格与 secure 一致）；缺见证、sum 不符、长度不符、世界编号不符四种都明确拒绝 |
| 玩家模式 | 作者路由请求数 **0**，页面显示 `not_ready` |

### 主入口端到端（真实浏览器，`python tools/dream_main_entry_check.py`）

临时回环服务 + 临时 sqlite（不碰 `data/`），跑完自动关、无监听残留。最近一次 `ok: true`：

| 项 | 实测值 |
|---|---|
| 空态 | 无像素（canvas 位图 0×0）、无已登记世界、新建面板自动展开 |
| 作者生成 | 24.1 s 完成 → 1987 KB（`map`/`eras`/`civ`）→ 画布 2048×1024、**8015 种颜色**、不透明 1.0 |
| 刷新 | 世界仍在（服务端已登记），像素与颜色数不变 |
| 作者→玩家 | `modeSwitch: author → player`；作者宿主**真卸下**（`hasCanvas:false`）、`hostState: 'not_ready'`、作者原件请求 **0** |

> 空世界、没有故事包时 `POST /api/sessions` 会回 400（`还没有可用的世界`），
> 所以玩家分离验的是**应用自己的切换入口**（`loadSession` 第一行就 `setNativeMode('player')`），
> 而不是另起一个独立 player 挂载来冒充。
