# 城镇生成与现有素材接入

**2026-11-13 更新**：城镇生成是[故事包](story-package-definition.md)下一级的独立系统。现已连接“已发布背景→国家疆域内聚落选址与道路规划→单镇四阶段→王国城镇版本发布”。道路表示作者确认的规划，尚不表示已建成或曾在历史上存在。下文保留单镇能力与旧验收记录，新流程见下一节。

## 从世界背景生成王国城镇

在「世界背景」发布背景后打开「王国城镇与道路」，选择背景版本与国家，填写种子、聚落数量和最小间距。规划复用冻结地图陆地、高程与坡度：首府候选保留在模拟首都州，其他位置按间距和覆盖选择；数量不足会明确提示。候选名称只是可编辑的规划标签，不是AI新造的历史地名或建城年份。

道路按国家疆域内四邻接陆地格寻找路径，以距离和高差形成规划成本，保留完整米制折线与源网格。不同岛屿不自动架桥或生成航线；州连接边不会当作实际道路。地图分辨率不足以决定桥梁、微观路基或施工可行性，发布的是作者规划。

逐个选择聚落，核对JSON城镇条件。高程、坡度及能识别单位的完整气候观测直接固定；各气候字段按自身网格查询，缺月或缺值不填零。温度的月均合并、降水的年合计会记录具体来源与口径。供水量、土壤、洪水风险、建设范围、材料、技术、文化及体型条件缺失时要求作者填写，不把预置样本当作地图实测。种族／魔法与制度资料来自固定背景，君主、王朝、国祀和历史人物从该年文明记录读取，不从历史叙述猜测。

生成该镇后，可进入原有城镇阶段编辑和布局预览，再发布单镇版本。所有候选均有已发布城镇、且没有未发布修改后，发布王国城镇版本；文件保存到 `StoryPackage/<背景目录>/kingdoms/<ksv_id>.json`，内含原背景身份、国家条件、选址、规划道路和全部单镇版本快照。重新打开时可从文件读取，不依赖用量／草稿索引。旧版本不随随后编辑变化。

新城镇输入可选 `background` 来源字段；旧单镇输入无需增加该字段。新流程的平面米制位置保存在背景来源中，不能填进旧 `terrain.coordinates` 经纬度字段。背景城镇不能直接采纳到另一个旧可玩包；仍不自动创建开局或启动旅程。

## 王国城镇接口

以下路径均位于 `/api/inner`，要求既有作者令牌。

| 方法和路径 | 用途 |
|---|---|
| `GET /world-package/backgrounds/{version_id}/settlements` | 列出该背景的聚落规划 |
| `POST /world-package/backgrounds/{version_id}/settlements?polity_id=…` | 创建可复现规划；请求含 `seed`、`count`（1～24）、`min_distance_m` |
| `GET /settlement-plans/{plan_id}` | 规划及当前修订 |
| `GET /settlement-plans/{plan_id}/sites/{site_id}/town-input` | 固定来源输入模板、实际观测、缺项和文明背景 |
| `POST /settlement-plans/{plan_id}/sites/{site_id}/town` | 提交 `input` 与 `expected_revision`，走既有单镇生成器 |
| `POST /towns/{draft_id}/publish` | 按既有接口发布单镇，使用该镇修订号 |
| `POST /settlement-plans/{plan_id}/publish` | 核对全部已发布城镇并发布王国版本，使用规划修订号 |
| `GET /world-package/backgrounds/{version_id}/kingdom-versions` | 列出王国城镇发布版本 |
| `GET /kingdom-versions/{version_id}` | 读取固定快照；不随新草稿变化 |

相同背景、国家和规划参数重复创建返回同一规划。来源变化、修改了冻结观测、采用条目或版本不符、过期编辑会明确拒绝。规划已发布后使用新种子建立新的规划，不覆盖既有发布文件。新流程与旧可玩包采纳并列，未实现道路施工或城镇经营的回合结算。

可移植回归：

```powershell
& ./.venv/Scripts/python.exe -m pytest tests/test_kingdom_settlements.py tests/test_kingdom_settlements_http.py -o addopts='' -q
node tests/kingdom_settlements_ui.cjs
```

真实浏览器验收要求独立安装的Playwright和本机Edge，可将依赖放到临时目录，不依赖被忽略的civ-atlas运行环境：

```powershell
$browserDeps = Join-Path $env:TEMP 'textiledream-browser-deps'
npm install --prefix $browserDeps --no-save playwright@1.63.0
$env:TEXTILEDREAM_PLAYWRIGHT_MODULE = Join-Path $browserDeps 'node_modules/playwright'
$env:TEXTILEDREAM_BROWSER_CHANNEL = 'msedge'
node tests/kingdom_settlements_browser.cjs
```

2026-11-13真实Edge通过：3个聚落、1条陆地规划道路及SVG、3个单镇发布、原阶段编辑与布局入口、王国发布及刷新后同版重读；页面错误和CSP违规均为0。验收使用临时Service根、百科与SQLite，以及小型固定地图、离线模型和明确的作者条件；不修改正式故事包或指针。实际结果在`artifacts/test-results/kingdom-settlements-browser-20261113.json`。另以已登记六组真实地图完成2镇、1条规划道路、王国发布与Service重启重读，约140.24秒，记录在`artifacts/kingdom-generation-20261113/real-map-result.json`。两类验收不代表在线AI文字质量已通过。


> **作者能力说明（2026-11-08 整理）**：下面的流程和「73 项通过」是作者端验收。正式旅程没有城镇布局图，见 [现状.md](现状.md)。

2026-11-06：已把固定规则四阶段生成、真实草稿/不可变版本、局部布局生成器和 SVG 素材连成作者端可操作流程。

## 验收入口

打开 `http://127.0.0.1:8000/`，进入「城镇创作」。选择河谷农业、山地矿业或绿洲商路，生成四阶段草稿后，「城镇地图」自动生成该草稿的实际布局。

- 可切换西式、东方、阿拉伯风格及种族素材、墙形、工事、地标数和布局种子。自动风格按屋面选择：平土顶→阿拉伯，庑殿顶→东方，其余→西式；它是展示规则，不推断居民文化或种族。
- 每个规则设施都对应已放置结果或明确失败原因。展开「设施放置清单」，点击有坐标的设施可高亮占地。墙体和城门作为基础设施统一计入覆盖清单。
- 可放大至 150%/200% 并滚动查看。悬停显示草稿设施名称。
- 「周边资源点」复用现有资源地块、主体和摆件，沿用规则核心的勘探、可采、技术和燃料闭包。未勘探矿脉不显示为开采地块；进口货物不变成本地矿产。
- 发布后可从「已发布版本」查看对应地图。布局选项不会改写不可变版本；导出地图 JSON 含源版本/草稿修订号、内容哈希、选项、实际种子、布局、设施覆盖和资源点，可据此重现。
- 修改上游阶段后，旧地图立即清空；必须推进失效阶段再生成。切换草稿或快速变更参数时，迟到响应不会覆盖新选择。

墙形、附加工事只对本来带城墙的城镇生效。开放聚落请求工事会显示提示；地形无法形成闭合城墙时也会显式记录降级。设施受空间约束而未放置属于布局提示，不应归为素材文件缺失。

## 实现接口

作者端接口均要求 `X-TextileDream-Token`，不会提供给玩家地图或模型上下文：

| 接口 | 行为 |
|---|---|
| `POST /api/inner/towns/{draft_id}/layout` | 完整校验当前草稿；缺阶段或失效即拒绝 |
| `POST /api/inner/town-versions/{version_id}/layout` | 从已发布快照重现，不写版本 |

请求体示例：

```json
{"style":"east","race":"common","wall_shape":"irregular","fortification":"auto","seed":null,"landmarks":null}
```

`PlanOptions` 拒绝未知字段，种子最长 64 字，地标限制为 0–2。接口不接受任意地形尺寸、目录或 SVG 内容。生成运行在线程池中的同步路由，不持有全局写锁，不调用语言模型，不运行经营结算，也不更改存档。

入口为 `app/town_plan.py`，复用 `towns.generate_all` 既有草稿链路和 `town_layout.layout/site_layout`。前端 `town-plan-ui.js` 按需加载本地 `town-catalog.js` 和 `town-render.js`，兼容现行 `script-src 'self'`，不使用 eval 或内联脚本。

## 素材与边界

当前 23 目录、1606 个唯一 symbol，覆盖全部 28 类规则设施。东西阿拉伯基础建筑、三族西式变体、地标、工事、城堡、道路/水岸/地面、资源点均从已有目录选取。

五种新要塞中文映射已补齐；重新生成的百科候选文件 `docs/human-encyclopedia/town-buildings.json` 为 **753 条、1606 个 symbol**。本次未导入正式百科数据库，避免改变已锁定的内容版本。

仍须美术复核：阿拉伯缺独立资源点与棱堡/外堡，资源点当前明确回落西式/东方；东方和阿拉伯缺异族变体，西式异族部分设施回落人族；部分资源地面硬边、密集屋顶遮挡和小摆件辨识度。见 `docs/town-art-review-2026-11-06.md`，没有另画新素材。

局部地图为示意，不按每个民居图标对应一户，也不按每格计算真实耕地、库存和产量。建筑经营参数尚未标定。此次未把布局挂到正式旅程地图，也未替换 civ-atlas 世界位置引用。

## 验证

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_town_plan.py tests/test_town_art_elements.py tests/test_town_layout.py tests/test_building_economy.py tests/test_towns.py -q --tb=short -o addopts=''
node tests/town_plan_browser.cjs
```

专项合计 73 项通过，另含 123 项子测试。真实 HTTP 浏览器验收使用临时数据库与离线模式，覆盖三个预置生成、所有素材引用可解析、种族回落、设施定位、放大、JSON 导出、发布版本预览和失效地图清除；无 CSP 违规或 pageerror。浏览器证据在 `artifacts/town-plan/`。
