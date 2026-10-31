# 桌面游玩 UI 与地图投影契约

本文件只写**已经实现**的接口与**明确约定**，不把计划写成现状。

分界（不要混读）：

- **阶段 1（p1）— 已实现、已验收**：两栏游玩壳与左侧四页签、顶部 API 弹层、玩家侧只读
  地图路由（`play-map` / `play-map/basemap.png`）、服务器侧迷雾掩膜、倒三角与标记的投影、
  旧页面全部收进「其他」且行为不变。下文 1–5 节写的都是这一层。
- **阶段 2（p2）— 未实现**：世界基础落盘、`world_basis` 生成流程、空间草稿保存、
  以及「由作者工具把 `mechanics.map` 写进故事包」的自动化接线。
  本文件只固定 p1 消费的那份**最小稳定接口形状**，不声称 p2 已经能产出它。

---

## 1. 布局（桌面优先，最小 1366×768）

```
┌─────────────────────────────────────────────────────────────────┐
│ #topbar  织梦·TextingDream │ ⌁ API 配置 │ 连接状态 │ 世界名 │ ＋ 新的旅程 │
├─────────────────────────┬───────────────────────────────────────┤
│ #play-left（默认 40%）   │ #play-right（默认 60%）                │
│  #play-badge + #play-place│  唯一一张 civ-atlas 底图（服务端掩膜）  │
│  #play-tabs 横向四页签：  │  倒三角 = 服务器给的当前位置            │
│   对话 │ 历史 │ 物品 │ 其他│  已探索 / 已知未到 标记                │
│  └ 对话框：正文独立滚动   │  缩放·平移（视角不每回合重置）          │
│    + #chat-form 固定底部 │                                       │
│  └ 历史：存档列表 + 章节  │                                       │
│  └ 物品 / 其他            │                                       │
└─────────────────────────┴───────────────────────────────────────┘
```

- 顶部只有四样东西：品牌名、`#api-toggle`（打开 API 弹层）、`#conn-state`（连接状态）、
  `#world-label`（当前世界名）与 `#play-new`（新的旅程）。**顶部没有「其他」下拉**——
  旧功能入口在左栏「其他」页签里（见下）。
- 左栏是**横向四个页签**（`#play-tabs`，`role=tablist`）：对话 / 历史 / 物品 / 其他。
  对话页签的内容是 `#surface`；历史 / 物品 / 其他各自是 `#panel-history` / `#panel-items` /
  `#panel-other`。页签选择存在 `localStorage['textiledream-play-tab']`。
- 分隔条 `#column-splitter` 可拖拽，比例存在浏览器 `localStorage['textiledream-play-split']`，
  区间 28–64%，默认 40。**不写服务端**（因此任何打开地图的动作都不会改 `state_version`）。
- 历史页签里装的是 `#surface-journeys`（由 `app.js` 在运行时创建，包含 `#new-session`、
  「旅程存档」标签与 `#sessions`、`#conversations` 章节列表）；它与正文区、物品栏都在左列
  内部滚动。输入框 `#chat-form` 是对话页签的尾部元素（`position:static`），
  **不覆盖**正文（不是 `position:fixed/sticky` 压在内容上）。
- 「其他」页签 `#panel-other` 收进**全部**旧功能入口：知识点记录簿、旅程地图 · 旧图册、
  世界创作、世界地图工具、城镇创作、元素装配、里层创作、模型输入输出、API 配置、设置；
  另带一个「玩法与地图帮助」折叠块（雾的口径、缩放说明等长解释放这里，不占主画面）。
  点任一行走 `showPage(page)` → `TDNav.show`，`#play` 隐藏、`<main id="legacy">` 显示；
  旧页面的 DOM id 一律保留。从旧页返回用 `#back-to-play`。
- 桌面优先：不新增手机断点。`style.css` 里既有的 `@media(max-width:800px)` 规则原样保留，
  但**不作为验收标准**，p1 只对 1440×900 与 1366×768 负责。

## 2. DOM 契约（旧 id 一律保留）

| 保留 | 说明 |
|---|---|
| `#surface` | 移到左列（对话页签）；内部 id 全部不变：`#story-text` `#actions` `#status-line` `#chat-form` `#message` |
| `#surface-journeys` `#conversations` | 由 `app.js` 在运行时创建后**追加到 `#panel-history`**（历史页签），不在 `#surface` 里 |
| `#notebook` `#inner` `#map` `#api` `#settings` | 仍在 `<main id="legacy">`，`showPage` 语义不变 |
| `#traces` `#map-tools` `#towns` `#elements` `#world-workshop` `#generator-*` | 仍由各旧脚本动态创建并追加到 `<main id="legacy">` |
| `#new-dialog` `#notice` | 位置不变（`#notice` 为 body 级 `position:fixed` 提示，右上角） |
| `#map-overlay` `#map-canvas` `#show-fog` | 旧图册页仍在，供文字兼容；**不再是常驻第二地图** |
| `#play-tabs` `#panel-history` `#panel-items` `#panel-other` `#column-splitter` | p1 新增的游玩壳结构（左栏页签与分隔条） |
| `#api-pop` `#api-pop-host` `#api-toggle` `#conn-state` `#world-label` | p1 新增的顶栏与 API 弹层 |
| `#play-map-wrap` `#play-map-img` `#play-map-overlay` `#play-map-empty` `#play-map-bar` `#play-map-legend` `#play-map-note` | p1 新增的右栏地图（唯一一张底图 + SVG 叠层 + 图例/状态行） |
| `#back-to-play` `#page-title` | 旧页头部（从旧页回到游玩壳的入口） |

导航统一走 `window.TDNav`（`app.js` 内定义）：

```js
TDNav.register(id, {title, play, enter})   // 声明页面与其进入动作
TDNav.alias(from, id => ({page, before}))  // 旧 id 重定向（generator-world → world-workshop）
TDNav.show(id)                             // 唯一的页面切换入口
TDNav.pages()                              // 已注册页面
```

旧脚本里「层层包 `showPage`」的写法改为 `TDNav.register/alias`；`showPage` 仍是全局函数，
内部转调 `TDNav.show`，因此任何还没改写的旧调用点行为不变。

## 3. 地图数据来源（session / 坐标 / source ID）

玩家侧唯一接口（**只读 GET**，不写任何文档，不改 `state_version`）：

```
GET /api/sessions/{session_id}/play-map              → JSON 投影
GET /api/sessions/{session_id}/play-map/basemap.png  → 已按迷雾掩膜的 PNG
```

成功的 `basemap.png` 带 `Content-Type: image/png` 与 `X-Play-Map: fog-masked` 头；
非 `ok` 或还没有带经纬度的地点时返回 `404` + `{detail}`（不是空图）。

来源链，逐层都由**服务器**决定，客户端无法指定：

```
session.id → store.session(id).revision
           → runtime.package(revision)['story']
           → story.mechanics.map = {'kind':'civ_atlas','import_id':'sn_…/mi_…',
                                     'world_basis_id':'wb_…'?,      # 可选
                                     'fog':{'reveal_radius_km':300}} # 可选，默认 300
           → play_map.parse_link() 严格校验（未知字段直接拒，不静默忽略）
           → store.get('map_import', import_id)
           → <store 所在目录>/map_imports/<file>  （复用 civ_atlas_snapshot / map_import 解析）
```

- **两条路由都没有任何客户端可选参数**：不接 `import_id`、不接经纬度、不接 `layer`、
  不接尺寸，也不看 query string。玩家路由从旅程绑定的版本里读 `mechanics.map`，
  多传的 query 参数被忽略而不会改变结果（`tests/test_play_map.py` 有专门的只读用例）。
- `source` 已经脱敏：它只给 `{map:'civ_atlas', world, opaque_id, format, cells, note}`，
  **不含 `import_id`、不含文件名、不含路径、不含内部错误文本**。`import_id` 只出现在服务器
  日志/作者侧；玩家侧看到的 `opaque_id` 是 `sha256(记录 sha256)` 的前 12 位，
  只作为稳定不透明标识，不提供任何可达入口。
- `story.mechanics.map` 是 p1 消费的**最小稳定接口形状**（**p2 尚未实现自动写入**，
  目前由作者工具/验收脚本显式写入）：
  `{kind:'civ_atlas', import_id:str, world_basis_id?:str, fog?:{reveal_radius_km:number}}`。
  `kind` 只接受 `'civ_atlas'`；`import_id` 必须是 `sn_`/`mi_` + 6–32 位十六进制；
  `world_basis_id` 可为空，非空时必须是 `wb_` + 8–32 位十六进制。
- 状态共五种，**任何一种都不会回退到别的底图**：

  | `status` | 何时 |
  |---|---|
  | `ok` | 链接有效、导入记录在、原件能读且哈希一致 |
  | `not_linked` | 故事包没声明 `mechanics.map`（旧旅程走这里） |
  | `import_missing` | 声明了，但 store 里没有这条 `map_import` 记录 |
  | `import_unreadable` | 记录在，但原件文件缺失/读不出/校验失败 |
  | `import_mismatch` | 记录在，但它与自身声明的内容哈希不一致（拒绝使用） |

  非 `ok` 时 JSON 额外给 `reason` 与 `author_entry={page:'map-tools', label:…}`，
  `basemap.available=false`、`basemap.url=null`、`bbox=null`；
  `basemap.png` 也**不返回图**，直接 `404` + `{detail: reason}`（不回退到任何其它底图）。
- 坐标身份：地点纬度经度来自 `story.locations[*].coordinates`（civ-atlas 导出同样是
  等距圆柱 lon/lat，`civ_atlas_snapshot.read_world` 把它算成逐格 lon/lat），因此
  `projection` 用同一帧：`x = (lon + 180) / 360`，`y = (90 − lat) / 180`。
  倒三角与已知标记都用这个公式定位，和掩膜后底图逐格对齐。经度先归一化到 [−180,180)，
  跨日界的地点只画一个标记，不会在对侧复制一个幽灵。
- 旧旅程（玄陆/河港等）在 `story.` 里没有 `mechanics.map`：给明确的「未关联」状态 +
  作者入口（打开「世界地图工具」），**不默认接无关地图**；旧 `atlas` 仍只作文字/旧图册兼容。
- 地点没有经纬度（如河港汛期的 6 个地点）时 `player.lon/lat = null`，标记不画，
  文案写「该地点未记录经纬度」，不伪造位置。

## 4. 迷雾权限（服务器白名单，不是 CSS 遮罩）

- 可见集合 = `explored` ∪ 当前地点的 `neighbors`，且当前地点自身始终为 `current`——
  与 `Runtime.surface()` 同一口径（`visible = set(s['explored']) | set(current['neighbors'])`），
  所以地图与地点列表不会互相矛盾。
- 只下发三种状态：`current` / `explored` / `known`（已知未到）。其它地点**整个丢掉**：
  没有 id、没有名字、没有坐标，也**没有数量**，响应里**没有 `more_unknown` 这个字段也不给计数**
  （它是首审文档里的旧设想，实现里已不存在；`tests/test_play_map.py` 有专门断言）。
  另外，作者可用 `visibility:'author'` 或 `reveal_flag` 把地点对玩家遮住——即使它就在旁边。
- 底图不“发给玩家再盖住”：`basemap.png` 由服务器逐格判定——只有落在已探索/已知地点
  的可见半径内的格子才绘制真实高程/水体颜色，其余格子**直接画成雾色**（`(17,20,24)`）。
  像素里没有隐藏地形，截图也拿不到。作者侧全图接口 `/api/inner/map-imports/{id}/preview.png`
  保持独立代码路径，玩家侧不复用它。
- 半径口径（`app/play_map.py`）：
  - `reveal_radius_km` 默认 **300**，允许 **10…2000**，作者可在 `fog` 里改。
  - `current` / `explored` 地点用 `reveal_radius_km` 本身；
  - `known` 地点用 **`0.5 × reveal_radius_km`**（`KNOWN_FRACTION=0.5`），
    对任何允许的 r 都满足 `known ≤ visited`，所以「听说过」永远不会比「去过」看得更远。
  - 写进 `fog.basis='gameplay_travel_reach'`、`fog.masked_by='server'`，两者与实际行为一致；
    响应同时给 `fog.known_radius_km` 供 UI 解释。UI 在主画面只留一行简短状态，
    「不是真实视线、不含地形遮蔽」的口径放在 `#play-map-note` 的 `title` 与
    「其他 → 玩法与地图帮助」里（不占主画面）。
- 当前视距内也不下发**实体**：没有人物、没有矿藏、没有城镇、没有知识条目。
- 底图尺寸有上限（`MAX_BASEMAP_WIDTH=640`、`MAX_BASEMAP_PIXELS=240000`、
  `BBOX_MARGIN=0.25` 度垫边，编码结果有界缓存 `CACHE_LIMIT=8`）；
  这些是服务器行为，不是客户端参数。

## 5. 密钥与连接状态

- 顶部只显示「离线模式 / 密钥已配置 / 未配置」+ 模型名，**不显示密钥**，不回填值
  （`placeholder` 为 `********`）。
- 密钥仍只走 `PUT /api/settings/api` 的 JSON body（请求头 token），不进 URL、不进日志、
  不进 trace（`Provider.trace` 已有替换逻辑）。
- 可见品牌文案是 **TextingDream**；`TextileDream` 只允许留在内部标识（`localStorage` 键、
  `X-TextileDream-Token` 请求头、导出文件名），不得出现在页面可见文本里。

## 6. 本阶段验收（可复现、已真实跑过）

```powershell
# 1) 纯服务侧（临时 Store，不碰 data/ 与旧包）——25 条
d:\anaconda\python.exe -m unittest tests.test_play_map -v

# 2) 语法
foreach ($f in Get-ChildItem app\static\*.js) { node --check $f.FullName }

# 3) 真实 Edge 两视口（1440×900 / 1366×768）+ 截图
d:\anaconda\python.exe tools\p1_ui_check.py     # 退出码 0 = 全过，非 0 = 有 FAIL
```

- 浏览器侧用 `external/civ-atlas/node_modules` 已有的 playwright + 本机 Edge，不装新依赖。
  `tools/p1_ui_check.py` 在临时目录建 sqlite、现画一张 16 位高度图当 fixture（**不是用户世界，
  也不绑旧故事包**），只监听 `127.0.0.1:8977`，跑完 `should_exit`；探测器的进程退出码
  就是门禁：`failed > 0` 一定非 0 退出。guard 把异常记成 FAIL，不会因捕获而变绿。
- 截图在 `docs/ui-shots/p1/`，报告是 `p1-ui-report.json`（126 条、0 失败）。
  **截图里的底图是 fixture 矩形色块，不是最终 civ-atlas 画风**，只用于验布局与锚点。

### 已断言的验收项（都写在 `tools/p1_ui_probe.cjs` 里，按行为断言而非元素存在）

1. 底部图真加载：`play-map` JSON 200 且 `basemap.png` 200 是 PNG 字节、`naturalWidth > 0`；
   **先**断 canvas 尺寸 > 0 与当前位置像素在图内，**再**断「当前位置不是雾」——
   避免取不到像素（-1,-1,[0,0,0]）时假通过。角落像素必须等于雾色 `(17,20,24)`。
2. 倒三角尖端落在经纬度对应的**屏幕**位置，容差 ≤ 1 屏幕像素；默认 / 放大 / 真实鼠标平移后 /
   复位后各验一次（只比 SVG 用户单位会被缩放骗过）。
3. 左栏 40%：首次在全新 context 量（不读旧偏好）；另存 52% 后 reload 要读回 52%。
4. 分隔条用**真实鼠标**拖（合成的 `PointerEvent` 没有 active pointer，`setPointerCapture`
   抛异常是测试造物）；拖完宽度真变、写进 `localStorage`、退出 `resizing` 状态。
5. 长正文在左列独立滚动，滚到底时输入框不压内容、底边不越左栏。
6. 四个页签（对话 / 历史 / 物品 / 其他）都能切；「其他」收全部旧入口；进旧页再回来
   `current` 不丢；从旧页回来底图与标记自动恢复。
7. API 弹层：打开时可见、在屏内、有尺寸、表单在 `#api-pop-host`、密钥框 `type=password`
   且值为空；再点入口 / `Escape` / 点外部三种方式都能关闭，并把**同一份**表单搬回 `#api`
   （旧页不是空壳），密钥始终不回填。
8. 会话不串源：一段 `ok` + bbox，一段 `not_linked` + `source=null`；切到未关联时旧底图收起、
   倒三角清零、出未关联文案与作者入口；再切回时图与倒三角重新出现。
9. 所有 `/api` 响应体与 header 都不回显密钥；无未捕获脚本异常；无横向溢出。

### UI 当前状（p1 收尾）

p1 的 UI 源码（`app/static/play-ui.js`、`index.html`、`map-tools.css`、`style.css`）已验收完毕，
视为**本阶段定稿**：请不要在没有具体 bug 的情况下反复微调。它**不是流程硬锁**——
发现真问题（含主审复现的）照常修代码，只需同步更新本契约里对应的句子。
