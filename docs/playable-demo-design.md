# 可试玩 Demo · 设计说明（河港汛期）

本文件描述本轮要落地的六个模块与其边界。目标不是「通用叙事引擎」，而是把**已经存在的规则资产**
（百科命名空间/固定版本、本地资源与日程、奖励、城镇快照、检定）串成一条可从三种起点走到
不同阶段结局的短篇。设计时长 30–60 分钟是**设计目标**，不是实测承诺；本轮不接外部地图、
不接降雨资源，也不做经营/势力经济 tick。

## 0. 一句话结构

`角色特质模板（百科特性命名空间）` → `start_profiles（三种起点，原子初始化）` →
`pressure（时间+条件推进的压力）` → `自由行动确认（候选+成本+CAS）` → `原创短篇故事包（分支阶段结局）`
→ 前端与测试。

## 1. 角色特质模板：复用百科的命名空间与固定版本

- **源文件**：`docs/playable-demo/character-traits.json`，格式与 `docs/human-encyclopedia/*.json`
  相同（`group` / `sources` / `elements` / 七节 `details` / `tags` / `source_ids` / `review_status`），
  命名空间 `character-traits`。
- **七节语义映射**（本分区专用，写在每个条目的 `details` 里，正文自证，不靠猜字段名）：

  | 百科节名 | 本分区里的含义 |
  |---|---|
  | `definition` | 这个特质是什么：一句可判定的描述 + 常见表现 |
  | `mechanism` | 它如何影响行为：**可观察**的倾向、取舍顺序、说话方式 |
  | `conditions` | 什么时候才显现：前提、场景、可见条件 |
  | `exceptions` | 反例与**不能推断**的东西（不得由它推出道德、能力、秘密） |
  | `story_uses` | 剧情用法：可支撑的冲突、可作为检定难度的来源 |
  | `historical_scope` | 适用边界：本项目**原创玩法设计**，不是心理学结论，不做跨文化断言 |
  | `evidence_and_uncertainty` | 证据缺口：没有测量、没有样本、没有量表；只是设计文字 |

- **内容规模**：实际落盘 23 个模板：七个分类各 3 个 —— 稳定倾向 / 价值底线 / 动机 / 表达习惯 /
  经历身份 / 优势弱点 / 社会牵连（其中 2 条标记 `trait.hidden`）。分类只落在 `tags`
  （如 `trait.stable`），另有 `trait.public`（可公开）等标签；不引入新的分类字段。
- **来源不编造**：`sources` 只有本项目自己的设计文档与既有工程文档（`url` 写仓库内相对路径），
  `rights_note` 明确「本项目原创设计文字」；`review_status` 一律 `needs_review`，
  表示「未经实证审核」，不是「已核实」。**不写论文、不写量表、不写统计数据**。
- **加入构库名单的方式**：`tools/encyclopedia_build.py` 增加**独立的显式名单**
  `TRAIT_GROUPS = ('docs/playable-demo/character-traits.json',)`、
  `LATEST_GROUPS = GROUPS + TRAIT_GROUPS` 与 `groups_for(with_traits)`，CLI 多了 `--with-traits`
  （`--check --with-traits` 也生效）。
  - **默认口径不变**：`GROUPS` 仍是历史 14 组 / 528 条，旧测试与旧交付口径照旧（旧集作为回归基线保留）。
  - **交付口径**：`--with-traits` → 15 组 / 551 元素 / 505 来源 / 0 未解析（本机实测；
    历史 14 组实测为 528 / 502 / 0）。交付库**就用同一个库文件**，直接再跑一次
    `--with-traits`（导入是幂等增量，历史元素与 source pin 不会被重写）；
    不需要、也不要另建第二个库。
- **故事包固定版本**：模板快照随故事包走，落在 `story.mechanics.traits`
   （`version` / `namespace` / `templates[]`（含 `payload` 与 `payload_hash`）/ `locked_note`）。
   快照里 `name`/`summary`/`details`/`tags` 全由 `payload` 派生；读取时逐字段比对，
   所以改外层不去改 payload 会被直接拒绝。
  旅程只读**自己绑定的那个包版本**里的快照，不再查库；库更新/删库都不影响已开局存档。
- **角色实例**：角色包新增 `trait_refs`：

  ```json
  {"template": "trait_stable_methodical", "version": 1, "visibility": "public" | "hidden",
   "personal": "他自己的说法：……", "evidence": ["opening", "事件id"]}
  ```

  `personal` 是**个人化解释**（必需，长度有界），`template` + `version` 必须能在包内快照里
  精确命中，否则提交即拒绝。旧角色包没有该字段 → 行为完全不变（`None` 时整条链路不动），
  `personality` 一个字也不改。
- **临时情绪 vs 人格**：特质模板读取的是**稳定层**；临时情绪仍只走
  `development.emotion` + `emotion_expires_after_turn`，两者不合并、不写入同一字段。
- **不单数值决定行为**：`traits.influence()` 只产出两类东西——可观察的表达提示（cue）
  与明确的边界（不能由特质推出的结论），**不产出倾向分值**。引擎现有的
  「按 personality 权重取最大值」逻辑保持不变，特质不参与 argmax，也不改写权重。
- **公开 / 隐藏与投影隔离**：`visibility: public` 的特质会进玩家投影与玩家上下文；
  `hidden` 只进该角色自己的视角与作者视图。NPC 视角不继承玩家特质，玩家也看不到
  NPC 的隐藏特质；`traits.context()` 对两个受众分别裁剪，整条丢弃、不切片。
- **模型上下文有界预算**：`TRAITS_CONTEXT_ENTRIES = 4`、`TRAITS_CONTEXT_CHARS = 900`，
  超预算时从末尾整条丢弃。

## 2. start_profiles：三种起点

配置在 `story.mechanics.start_profiles`（`app/start_profiles.py`，严格 Pydantic，`extra='forbid'`）：

- `version`、`profiles[]`（最多 6 条）、每条：

  | 字段 | 含义 | 校验 |
  |---|---|---|
  | `id` / `title` / `summary` | 标识与公开说明 | ID 形如 `[a-z0-9_-]+` |
  | `identity` | 身份描述（写进开局 facts，公开） | 1–120 字 |
  | `location` | 开局地点 | 必须是本包地点 |
  | `items` | 开局物品（世界物品 id 列表） | 必须存在且地点绑定可绕过；只允许作者声明的 id |
  | `wallet` | 开局钱货 `{货币id: 整数}` | 货币必须在 `mechanics.rewards` 里声明，额度≤上限 |
  | `reward_items` | 开局物品实例（奖励模板 id 列表） | 模板必须存在；**引擎发放，不靠模型正文** |
  | `relations` | 开局关系 `{角色id: {"trust": 0..1, "note": 文本}}` | 角色必须存在 |
  | `known` | 开局已知信息（`text` + `source` + `public`） | 文本≤300 字；`public=false` 只给作者与指定角色 |
  | `goal` | 个人目标（玩家可见） | 1–200 字 |
  | `traits` | 给主角追加的特质引用（同 §1 的 `trait_refs` 结构） | 必须命中包内快照 |
  | `entry_event` | 入口事件 id | 必须存在且地点匹配；引擎按它强制进入 |

- **原子初始化**：`runtime.new_session()` 里先构造完整候选快照，再把 start profile 的全部
  写入（物品/钱/关系/已知/特质/目标/入口）都在**同一份深拷贝**上完成；任一条失败
  （未知货币、超额、未知物品/角色/模板/事件）→ 整条开局拒绝、**零写入**。成功时只调用
  一次既有 `store.save_session()`（单事务），不存在半套开局。
- **不经模型发奖**：开局的物品与钱由 `rewards.seed_start()`（白名单整数）在引擎侧写入，
  与模型正文完全无关；模型即使写「你得到一袋米」也不会改变 `rewards`/`inventory`。
- **旧行为**：`NewSession` 不传 `profile`（或包没配 `start_profiles`）→ 与原来一字不差。
- **版本与重启/回滚**：start 写在 `session['start']`（`profile_id` / `applied_at` / `state_version`），
  随存档一起持久化；重启后从同一 revision 重建，不重复应用（`applied` 幂等键）。
  回滚到事件起点时，快照里的开局状态原样恢复，不会二次发钱。

## 3. 统一轻量剧情压力

配置在 `story.mechanics.pressure`（`app/pressure.py`）：

```
{"version": 1,
 "clock": {"note": "复用 local_rules 的 s['time']，不建第二个时钟"},
 "pressures": [
   {"id": "...", "title": "...", "public": true|false,
    "stages": [
      {"id": "...", "at_hours": 12, "kind": "warning|escalation|trigger|resolution|aftermath",
       "when": {"all_flags": {...}, "any_flags": {...}, "not_flags": {...}},
       "effects": [{"op": "flag|resource|notice|information|fact", ...}],
       "known_by": ["player", "<char id>"],
       "public_text": "只给已知者的一句话"}
    ]}
 ]}
```

- **只有一个时钟**：`pressure` 不自己推进时间；所有推进仍走 `local_rules.advance()`。
  `pressure.advance(s, story, hours)` 先调 `local_rules.advance`，再用新的 `s['time']`
  计算本轮应生效的阶段。这样日程（`mechanics.local.schedules`）与压力**共用同一次 tick**，
  不存在两个互相冲突的时钟。
- **确定性 + 幂等**：阶段是否生效只由「`at_hours` 已达 / `when` 条件 / 是否已应用」决定；
  `s['pressure']['applied'][stage_key]` 记录已应用的时刻，同一阶段永不多发效果。
- **跨多阶段**：一次大幅推进（旅行 4 小时、等待 12 小时）跨过多个阈值时，按 `at_hours`
  升序**逐个**应用，每个阶段仍只应用一次，并在 `s['pressure']['log']` 留下有序记录。
- **解除**：某个阶段可被后续 `resolution` 阶段的 `when` 命中，或玩家用配置动作
  （标记/开闸/撤离）设置 `not_flags`/`all_flags` 使其后续阶段**语义上失效**：
  失效的阶段不产生灾难性效果，只写一条 `lifted` 记录，结局判定读的是标记而不是「是否发生过」。
- **允许干预/绕开/拒绝**：压力阶段从不强制玩家进入主线，也不改 `s['active']`；
  它只改标记/资源/已知信息，玩家可以完全不处理（承担后果）或绕开（南浅滩旧纤道）。
- **不按聊几轮强制灾难**：阈值是**游戏小时**（本 demo 最短 12h、高潮 54h），
  且同时要求条件成立；`turn_hours` 只影响时间流逝，不单独构成触发条件。
- **只有已知的预警进上下文**：`pressure.context(story, session, audience)` 只返回
  `known_by` 含该受众、且 `public_text` 非空的阶段；玩家视角拿不到 NPC 私有预警，
  NPC 视角也拿不到玩家的私有预警。整条返回，上限 600 字符。
- **模型失败无半写**：压力评估发生在 `prepare_turn()` 的内存态上，只有
  `finish_turn()`→`save_session()` 才落库；模型报错时整轮不写（与既有奖励/效果同一条路径）。
- **回滚**：`s['pressure']` 在事件 `before` 快照里，回滚到事件起点后 `applied` 回到旧值，
  重做同一动作得到同一结果（无重复效果）。

## 4. 自由行动确认

`app/free_actions.py` + `POST /api/sessions/{id}/intent` + `Turn.confirm`。

- **有界结构化候选**：{当前事件里未执行、前置满足、资源付得起的 `actions`} × 确定性匹配
  （`label` + 作者公开的 `intent_aliases` 与意图的字符重叠 + 动作顺序稳定排序），最多 3 条。
  每条**只**给出：`action_id`、`label`、`costs`（资源名与数量）、`duration_hours`（**有效时长**）、
  `check`（`attribute` + `difficulty`）、`ends_event`、`intent_aliases`，以及**确认凭据** `confirm`。
- **候选不看“未发生的结果”**：`success_text` / `failure_text` / `narrative_cues` 不进候选、
  不进确认摘要、也不参与匹配。它们是作者写的“做了会发生什么”，提前给玩家等于泄露陷阱与检定分支；
  而且如果把它们算进匹配，玩家拿猜测词打一次 `/intent` 就能当代信道探出隐藏文本。
  作者侧不改：真正执行后仍按检定分支用这两段文本叙事（`prepare_turn` 的 `outcome`）。
- **公开意图别名**：动作可选 `intent_aliases`（≤6 条、每条 1..30 字、去重、非空），
  它是**公开**文本：玩家可见、参与匹配。本轮只给 `StoryPackage/河港汛期` 的关键动作加了少量别名，
  `玄陆` / `灰烬海` 一个字未加（它们本来也没有）。
- **有效时长只有一个口径**：`effective_duration(action, story)` 用**键是否存在**取默认——
  `duration_hours: 0` 就是 0，缺键才落回 `mechanics.local.turn_hours`；
  候选/确认弹窗/surface/凭据四处用的是同一个值（不用 `or`，否则 0 小时会被吞成默认时长）。
- **必须确认**：执行仍走既有 `/chat`（`action_id`），新增可选 `confirm`。给了就必须与
  当前状态算出的凭据逐字相等，否则在**任何副作用之前**拒绝（CAS：种子+state_version+
  事件分支键+动作 id+成本+有效时长+完整检定（属性+难度））。UI 一律先展示成本再发确认，
  因此玩家确认的是「具体 action 与成本」；同难度换属性、或 0 小时↔缺省，都会让旧凭据失效。
  不传 `confirm` 时保持旧行为（旧界面/旧脚本仍可用），这是有意的兼容，不是语义放宽。
- **未知行动明确不裁定**：没有匹配到配置动作时返回 `matched: []` + `unjudged: true` +
  一句说明（「引擎不裁定未配置的行动，这句话只作为台词/描述，不改变状态」）。
- **不把自然语言变 effect**：候选只引用**已声明**的 action；`intent` 文本不会写进
  effects、不会生成标记、不会授予物品。模型可以叙述「我翻过了墙」，但 `flags`/`inventory`/
  `rewards` 不变。
- **普通对话不受影响**：`speech` / `thought` / `note` 与自由输入仍按原路径工作，
  不强制走候选确认，也不把所有自由输入封死。
- **边界诚实**：匹配是字符重叠 + 动作清单的交集，不是语义理解；同义改写可能不命中，
  这时引擎**说什么都没匹配**，而不是猜。

## 5. 原创西幻短篇：河港汛期 · 失联粮队

- 位置：`StoryPackage/河港汛期/`（`story.json` / `总概.md` / `知识点/*.md`），
  独立角色包 `character_packages/riverport-demo-characters-001.json`。
  走既有作者包发现机制（`runtime.list_packages()` 扫库目录），**不改任何现有包**，
  **不自动导入、不动 pointer**；作者在「里层 · 故事包」里显式启用。
- 地点 6 个、事件 10 个（9 段主线 + 1 段同地点旁支小事，用来验证「入口不被第一根节点抢占」）、
  物品 6 件、货币 1 种、奖励条目 5 条、压力 2 条、起点 3 个、结局 4 个。
- 剧本骨架（每个节点都有**无前置、无花费**的结束出口，因此不会软锁）：
  `渡口封航告示` →（`米市街的两种价` / `行会堂的委托` / `囤粮洲的空仓`）→
  `上闸守闸人` →（`南浅滩旧纤道` 绕开）→ `洪水夜` → `善后与结算`。
- 三种阶段结局（由标记判定，不是由模型文本判定）：
  1. `ending_saved_grain` 保粮：闸门压到最后一刻，下游田亩被淹；
  2. `ending_opened_sluice` 开闸：人保住，粮损大半；
  3. `ending_lost_convoy` 全失（**失败后继续**）：粮队与仓都没保住，进入 `aftermath_rebuild`，
     仍可继续调查与重建，只是资源与关系更差；
  4. 额外：`ending_negotiated_split` 谈判分流（信息充分 + 关系达标）。
- 城镇快照：`mechanics.towns` 里绑定一座 `wet_valley` 预置城镇（固定 seed）到 `market_row`，
  走既有 `GET /api/sessions/{id}/towns` 与 `towns.context_summary` 的公开白名单，
  玩家侧仍受「已知范围」过滤。**不接外部地图，也不声称已接降雨资源。**
- 作者显式启用：`POST /api/inner/packages/河港汛期/activate`（既有接口），
  或界面「里层 · 故事包 · 切换到该目录」。本轮不替用户切 pointer。

## 6. API（新增，全部沿用既有 token 与同源检查）

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/api/start-profiles` | 当前包声明的起点（无配置 → `[]`，前端整段隐藏） |
| POST | `/api/sessions` | 新增可选 `profile`；不传时旧行为 |
| GET | `/api/sessions/{id}/traits` | 玩家可见特质（公开引用 + 个人化解释） |
| GET | `/api/sessions/{id}/openings` | 起点回执（本人选了什么、何时应用） |
| POST | `/api/sessions/{id}/intent` | 自由行动 → 有界候选（**不写库**） |
| GET | `/api/sessions/{id}/confirm/{action_id}` | 取单个动作的确认凭据与成本（**不写库**） |
| POST | `/api/sessions/{id}/chat` | 新增可选 `confirm`（给了就校验） |
| GET | `/api/sessions/{id}/pressure` | 玩家已知的预警（不返回私有阶段） |

## 7. 测试清单（全部离线、临时库）

1. 非法输入零写入：未知货币/超额钱、未知物品/角色/模板/事件、隐藏特质引用缺失版本、
   压力阶段引用未知标记/未知受众、候选确认凭据过期。
2. 多起点差异 + 旧包兼容：三种开局的地点/物品/钱/关系/已知/目标/入口不同；未传 profile
   与旧包（无 `start_profiles` / 无 `traits`）产物逐字节等于旧行为。
3. 精确时间阈值 / 跨阶段 / 化解 / 重试回滚：`at_hours` 前后各 1 小时、一次跨 3 个阶段、
   用动作解除、回滚后重做完全相同、无重复效果。
4. 多角色秘密投影：NPC 隐藏特质不进玩家视图与玩家上下文，反之亦然。
5. 词条更新不改旧实例：库内模板升到 v2，已有旅程与角色实例仍读 v1 快照。
6. 自由动作：建议不写库（`state_version` 不变）、确认 CAS（凭据过期拒绝）、未知行动
   `unjudged`、自然语言不产生 effect、普通 speech/thought/note 仍正常。
7. 三条开局到不同结局的离线 E2E（无 API Key，走 `offline_surface`）。
8. 浏览器：真实 Edge，1440×1000 与 390×844，覆盖「新建旅程选择起点 → 确认 → 公开内容」，
   断言无 `pageerror`、无横向 overflow，并记录实际发出的请求（`page.on('response')`）。

## 8. 明确不做 / 边界

- 不接外部地图、不解析降雨资源格式（等待用户提供后另开）。
- 不做经营/势力/经济 tick：钱与资源只在被动作/压力改变时变化，没有每回合结算的经济模拟。
- 特质是**玩法设计文字**，不是心理学量表，也不做人格测量；不声称预测真实人类行为。
- 自由行动匹配是字符重叠，不声称通用语义理解；未命中就是不裁定。
- 压力不强制主线、不写 `active`、不按对话轮数触发灾难。
- 不更新 528 交付库、不改 `StoryPackage/玄陆`、`StoryPackage/灰烬海`、正式 `data/`。

## 9. 实现现状与可核对的证据（本机实测，不代替主代理验收）

### 9.1 落盘文件

| 层面 | 文件 |
|---|---|
| 特质 | `app/traits.py`、`docs/playable-demo/character-traits.json`（23 条） |
| 起点 | `app/start_profiles.py` |
| 压力 | `app/pressure.py` |
| 结局 | `app/endings.py` |
| 自由行动 | `app/free_actions.py` |
| 接入 | `app/runtime.py`、`app/web.py`、`app/contracts.py`、`app/rewards.py`（`seed_start`） |
| 故事包 | `StoryPackage/河港汛期/{story.json,总概.md}`（含 `mechanics.traits` 与 `mechanics.towns` 快照） |
| 角色包 | `character_packages/riverport-demo-characters-001.json` |
| 前端 | `app/static/playable-demo.js`（挂到已有表层页）、`style.css` 末尾样式、`index.html` 一行 script |
| 测试 | `tests/test_playable_demo.py`（特质/起点/压力/自由行动/结局）、`tests/test_riverport_demo.py`（包自包含 + 三起点 E2E）、`tests/test_encyclopedia_traits.py`（特质入统一库） |
| 构库 | `tools/encyclopedia_build.py`：新增 `TRAIT_GROUPS` / `LATEST_GROUPS` / `--with-traits`（默认口径不变） |

快照里两个算出来才知道对不对的值由脚本生成（脚本没有入库，只落在临时目录）：
`mechanics.traits[*].payload_hash` 用 `app.traits.build_template()` 算，`mechanics.towns[*].content_hash`
用 `towns_store.content_hash()` 算；两边都以引擎自己的校验函数为准，没有手写哈希。

### 9.2 三处语义修订（比初版说明更严格，也更诚实）

1. **结局可达性**：`endings.py` 只做 `flag_sources()`（标记**来源覆盖**：动作/压力/日程/起点有没有写过这个标记）。
   没来源 ⇒ 永不可能成立，所以拒绝可以；有来源 ≠ 走到得了。**真正的可达性只由
   `tests/test_riverport_demo.py` 的三条真实 Runtime 路线证明**，不由模块自称。
2. **互斥判定**：`conditions_overlap()` 在有界标记集内**精确枚举**（≤ `EXHAUSTIVE_FLAGS` 个标记）；
   超过上限明确报错，不冒充“已验证互斥”；`any_flags {a:true}` 与 `{a:false}` 不再误判为重叠。
3. **压力时间粒度**：`pressure.advance(N)` 与连续 N 次 `advance(1)` 等价 —— 每小时先跑
   `local_rules.advance(1)`，再应用此刻到期的阶段；`lift` 阶段生效后会终止**同一压力**里尚未
   生效的阶段（记 `cancelled`）。已经发生的阶段不回滚，作者写的 `when.not_flags` 仍是第二道锁。

4. **旧包 surface 不变**：行动候选里的 `costs` / `duration_hours` / `check` / `ends_event`
   只在包里声明了 `start_profiles` / `pressure` / `endings` / `traits` 任一项时才会出现；
   旧包仍然只返回 `{id, label}`，`opening` / `warnings` / `ending` 也一样不出现
   （`tests/test_playable_demo.py` 的 `LegacyCompatTests` 逐字段断言）。

5. **裁剪（`trim_context`）契约**：只给基线列表块（`TRIM_LIST_KEYS`）补齐空容器；
   新机制块（`current_pressure` / `current_traits` / `current_elements`）缺键就**保持缺键**，
   旧包 prompt 不多一个字；dict 块只在它本来存在时整条丢弃（不切句）；
   按 `TRIM_ORDER` 级联，`knowledge`（世界正典）最后一个被动。

### 9.3 测试与真实计数

本机没有 pytest（Python 3.11 与 anaconda base 都没装，README 里的 `.venv` 不存在），因此用标准库入口：

```
D:\anaconda\python.exe -X utf8 -m unittest tests.test_playable_demo tests.test_riverport_demo
# Ran 54 tests ... OK（exit 0）
```

分模块：`tests/test_playable_demo.py` 45 例（特质 / 起点 / 压力 / 自由行动 / 结局 / 旧包兼容）、
`tests/test_riverport_demo.py` 9 例（包体自包含 + 三起点 E2E + 投影不泄漏）。
`tests/test_encyclopedia_traits.py` 9 例（显式名单 / 实测总量 / 旧 14 组不变 / 标签 / 检索 /
固定版本 / 幂等 / source pin / 导出回环 / 包快照与库 payload 一致），只用临时库。
`tests/test_context_trim.py` 7 例（旧包缺键保持缺键 / 基线列表空键保留 / 先清对话派生再动世界正典 /
级联到最后才动 `knowledge` / dict 块整条裁剪不切句 / 摘要先去原文段）。

回归：`tests.test_event_summary` 9 例全过（本轮 `trim_context` 曾把清空的键删掉，
造成 `trimmed['dialogue_knowledge']` KeyError；已恢复基线的「键保留 + 级联」契约）；
`tests.test_encyclopedia_supplement` 30 例全过（旧 14 组口径未动）。

全部离线：`provider.configure({'offline': True})`，测试里把 `provider.complete` 换成会抛错的东西，确认一次远程调用都没发生。

### 9.4 真实 Edge 验收（系统 `channel=msedge`，非 headless=False 的桌面窗口）

驱动脚本只访问本机隔离实例（临时库 + 临时 `StoryPackage` 副本，不碰正式 `data/`），截图在
`docs/playable-demo/evidence/`：

| 文件 | 内容 |
|---|---|
| `01-start-profiles-1440x1000.png` | 新建旅程弹窗里的三个起点 |
| `02-journey-1440x1000.png` | 起点回执（身份/目标/开局已知）+ 带成本的行动候选 |
| `03-confirm-cost-1440x1000.png` | 确认弹窗：成本、时长、检定、是否结束事件 |
| `04-after-confirm-1440x1000.png` | 确认后事件推进 |
| `05-intent-1440x1000.png` | 自由意图 → “不裁定”的明确提示 |
| `06-journey-390x844.png` / `07-start-profiles-390x844.png` | 390 宽窄屏 |
| `08-ending-and-warnings-1440x1000.png` | 已记录的「全失」结局 + 已知预警面板 |
| `browser-evidence.json` / `api-route-ending.json` / `browser-isolation-evidence.json` | 响应列表、溢出像素、面板文本、结局与预警原文；后者的“泄露漏检”两项必须为空 |
| `09-old-package-dialog-1440x1000.png` | 旧包新建旅程弹窗：起点区域整个隐藏 |
| `10-intent-candidate-1440x1200.png` / `11-confirm-no-result-1440x1200.png` | 意图候选与确认弹窗均只有成本/时长/检定，**不含成功与失败描述** |
| `12-after-execution-1440x1200.png` | 确认执行后作者侧分支文本正常出现（隔离没削弱叙事） |

实测结果：两个视口横向溢出均为 0px，无 `pageerror`；控制台只有一条 `/favicon.ico` 的 404
（记下来但**没有**去猜根因、也没有顺带改）。API 侧证据：`/api/start-profiles` 返回 3 条，
`/api/sessions/{id}` 的 `opening`/`warnings`/`ending` 与截图一致。

### 9.5 明确没做的事

- 未接外部地图与降雨资源（等你提供后再单独开一轮，不猜格式）。
- 未做经营/势力/经济 tick；钱与资源只在动作或压力改变时变化。
- 未改动 `StoryPackage/玄陆`、`灰烬海` 与正式 `data/`；交付库
  `artifacts/human-encyclopedia/encyclopedia.sqlite3` 未动，需验收方跑 `--with-traits` 重建
  （15 组 / 551 元素 / 505 来源）。
- 「30–60 分钟可玩」是设计目标，**没有**做时长实测。
