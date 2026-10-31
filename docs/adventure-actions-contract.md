# 冒险行动（adventure actions）契约

`app/adventure_actions.py`：把**作者已配置的目标**变成有界、可复核的行动方案。
纯规则模块，不执行、不保存、不发奖、不推进时钟。接线由 Runtime / Service 负责。

状态：**已接进运行期**（`Runtime` / `free_actions`），无新 API、未改 web/static。
所谓「八类通用行动」指下面这张表里的目标解析；缺口（物品实例效果、转交）已如实标注。

接线点（全部可回退，旧包逐字节不变）：

* `Runtime.validate_package` → `_reject_reserved_action_ids` + `adventure_actions.validate`；
* `Runtime.resolve_action`：静态动作优先，其次当前算出的运行时方案；**动态方案必须带确认凭据**，
  全部校验在 `communicate` / `charge` / `effects` 之前；
* `Runtime.surface['adventure']`：只放 `public()` 白名单字段；只有 
  `action` 存在且 `supported` 才附 `confirm`；事件未结束时旅行标 `blocked_active_event`；
* `Runtime.move / travel_hours / require_travel`：真实移动，仍然只走 `pressure.advance` 一个时钟，
  作者声明的 `route.hours` 会真正生效，已知但被封锁的路线不能靠直接调 move 绕过去；
* `free_actions.suggest / describe / verify` 新增可选 `plans` / `characters`：不传时若包声明了
  本块则**现算**，因此 `/intent`、`/confirm/{id}` 不改 web 也能拿到动态候选与凭据。

## 1. 分工（不重复任何引擎）


| 责任 | 由谁做 |
|---|---|
| 目标是否存在、玩家是否看得到 | 本模块（作者数据 + 旅程已知） |
| 成本扣费、时间推进、压力阶段 | `local_rules.charge` / `pressure.advance`（既有单时钟） |
| 属性检定与掷骰 | `drama.resolve_check`（`Runtime.prepare_turn` 里） |
| 效果落地（flag/resource/status/health/information/fact/take） | `Runtime._apply_effects`（既有 op） |
| 奖励发放 | `rewards.apply` / `Runtime.effects` |
| 确认凭据与 CAS | `free_actions.confirm_token` / `verify`（既有，本模块不另造） |
| 页面渲染、接口 | 尚无 |

本模块没有任何 `store` / `rewards` / 网络 / 时钟调用；`build` / `refusals` / `describe` /
`public` / `suggest` 都是纯函数，测试断言调用前后 session（含 `state_version`）逐字节不变。

## 2. 作者声明：`story.mechanics.adventure`

没有这个键时本模块整体 no-op（`config()` 返回 `None`，老故事包一字不变）。
结构校验用 `adventure_actions.validate(story, characters)`；`version` 必须是 `1`，
未知字段一律拒绝。

```json
{
  "version": 1,
  "clues": [
    {"id": "clue_waterline",
     "target": {"kind": "place", "id": "ferry_landing"},
     "action_kinds": ["observe"],
     "requires": {"all_flags": {"dockside": true}},
     "public_obstruction": "石阶上还没看出什么。",
     "effects": [{"op": "information", "text": "石阶上有一道新水痕。",
                  "known_by": ["player"], "confirmed": true}]}
  ],
  "topics": [
    {"id": "ask_price", "kind": "ask",
     "target": {"kind": "npc", "id": "grain_broker"},
     "requires": {},
     "public_obstruction": "他不肯谈这个。",
     "answers": [{"when": {"all_flags": {"trusted": true}},
                  "success_text": "他把价钱说了一遍。",
                  "effects": [{"op": "information", "text": "三日内涨了两成。",
                               "known_by": ["player"]}]}]}
  ],
  "routes": [
    {"origin": "ferry_landing", "destination": "market_row", "kind": "causeway",
     "hours": 2, "import_id": "mi_abc123",
     "requires": {"not_flags": ["road_flooded"]},
     "public_obstruction": "路被水漫了，今天过不去。"}
  ],
  "templates": [
    {"kind": "rest", "label": "原地歇 {hours} 小时", "intent_aliases": ["休息"]},
    {"kind": "use", "target": {"kind": "object", "id": "tow_rope"},
     "label": "用{target}借力", "duration_hours": 1,
     "effects": [{"op": "flag", "id": "rope_used", "value": true}]},
    {"kind": "give", "target": {"kind": "object", "id": "grain_sample"},
     "recipients": ["grain_broker"], "label": "把{target}交给{npc}"}
  ],
  "rest_hours": 8,
  "max_rest_hours": 168
}
```

### 2.1 字段

* **Target**：`{"kind": "place"|"object"|"npc", "id": ...}`。`object` 指 `story['items']`
  里的条目（地点对象）。引用不存在的目标在 `validate` 里直接报错。
* **Condition**：只有 `{"all_flags": {name: bool}, "not_flags": [name]}`，编译结果就是
  `Runtime.prepare_turn` 检查的那个 `requires` 字典；同一标记不能同时出现在两侧。
* **Effect**：只允许 `information` / `flag` / `resource` / `status` / `health` / `fact`
  —— 与 `Runtime._apply_effects` 的既有 op 逐个对齐（`take` 由本模块自己生成，`rumor`
  未收进来）。`information.known_by` 只接受 `player` 与已声明的角色 id。
* **Template**：一条「已声明动作」的模板，字段与既有故事动作一一对应，只差目标由本模块
  填。`check.attribute` 必须是六项属性之一（可用中文别名），难度 0..1，`costs` 只能引用
  `mechanics.local.resources`。`intent_aliases` 走 `free_actions.validate_action_aliases`。
* **Route**：`destination` 必须是 `origin` 的邻接（`locations[].neighbors`），否则 `Runtime.move`
  本来就会拒绝，`validate` 提前拦住。`hours` 可选；`import_id` 可选，写了就参与同世界判断。
* **give 模板**必须用 `recipients` 点名接收人（不给「交给任何在场者」这种万能转交）。

## 3. 八类行动：目标从哪来

| kind | 合法目标 | 效果来源 | 执行方式 |
|---|---|---|---|
| `observe` | 当前地点 | 绑定该地点、`action_kinds` 含 observe 的线索 | 既有 action 管线 |
| `investigate` | 当前地点的物品 | 绑定该物品、`action_kinds` 含 investigate 的线索 | 既有 action 管线 |
| `ask` | 同地点在场人物 | `topics[kind=ask]` 的**首个**条件成立分支 | 既有 action 管线 |
| `negotiate` | 同地点在场人物 | `topics[kind=negotiate]` 的首个分支 | 既有 action 管线 |
| `travel` | 当前地点的邻接且玩家已知的地点 | 邻接表 + 可选 `routes` | **交给 `Runtime.move`**，不动 `action` |
| `rest` | 自己 | 模板声明的 effects（不声明就只有时间推进） | 既有 `/wait` 或既有 action 管线 |
| `take` | 当前地点的物品 | 既有 `take` op + 模板 effects | 既有 action 管线 |
| `use` | 已持有的 legacy 物品 | 模板 effects（不声明就不产生方案） | 既有 action 管线 |
| `give` | 已持有物品 × 作者点名的在场人物 | 无 → `supported: false` | 无执行器（待 p5） |

* 「已有 declared action 可复用模板填参数」：所有 kind 共用 `_action_dict` / `_plan`，
  只有「目标从哪来」和「效果从哪来」按类分开；不存在八套并列逻辑。
* 物品实例（`session['rewards']['items']`）的 `use` / `give` 一律
  `supported: false`、`unsupported: ['instance_effect']` / `['inventory_handover']`，
  **不生成任何 op**。等 p5 的物品转移执行器，不是在建议里假装能确认成功。
* legacy `session['inventory']` 与 `rewards.items` 实例用 `source` 字段区分：
  `legacy_inventory` / `reward_instance` / `world_item`。

## 4. 可见性 ≠ 可进入

* 地点：沿用 `play_map.visible_places`（当前 ∪ 已探索 ∪ 当前邻接，再按
  `visibility: 'author'` / `reveal_flag` 收窄）。未公开地点**不出现在方案里，
  也不出现在拒绝理由里，更不计数**。
* 物品 / 人物：`visibility: 'author'` 与未成立的 `reveal_flag` 同样排除；
  人物还必须此刻与主角同地点。**角色 id 存在于包里不等于玩家看得见他。**
* 已知但被条件封锁的目标 → 只返回作者写的 `public_obstruction`（或一句通用文本），
  绝不返回条件名、秘密分支内容、阈值，也不报告被挡住的条数。
* 模板自带的 `requires` 也参与这一步：条件不成立就不发方案（否则调用方会拿到一个必被
  Runtime 拒的死按钮），只给公开阻碍。
* 没写 `public_obstruction` 的秘密话题**完全不出现**（连「有什么问不出来」都不说）。

## 5. 旅行：civ-atlas 同世界、不伪造道路

* 只处理**邻接**边的移动，不重算全球导航图、不按经纬度算距离，也不把直线当道路。
* 耗时来源必须显式写在 `duration_source` / `travel.hours_source`：
  `route`（作者声明 `hours`）→ `template`（模板 `duration_hours`）→
  `local.travel_hours`（`mechanics.local` 的既有默认）。落到默认时 `notes` 里明说
  「这条邻接没有作者声明的路线数据，不代表这里有一条已绘制的道路」。
* 地点没有 `coordinates` 时 `travel.position` 对应端为 `null`，`position_source:
  'unrecorded'`，仍然只给声明时长。
* 同世界判断：`route.import_id` 与本旅程 `mechanics.map.import_id` 不一致 →
  `world_mismatch`；旅程完全没有 `mechanics.map` 却遇到带 `import_id` 的路线 →
  `world_unverified`。两种情况都拒绝，不给方案。地图「知道」与「能进」始终分开。
* `travel.charges` 恒为 `false`：本模块不扣费、不推进时钟。声明了费用的路线标
  `unsupported: ['route_cost']`，`action` 为空 —— **绝不把 flag effect 塞进 action 冒充
  一次移动**，也不在 action 里加第二套时钟/现金账。实际移动只走 `Runtime.move`，
  全流程仍然只有 `pressure.advance` 一个时钟。

## 6. 休息

* `0..max_rest_hours`（上限 168，`rest_hours` 是默认值），只接受真正的 `int`：
  `True` / `1.5` / 负数一律 `ValueError`。
* 未声明 effects 时 `action` 里没有 `effects` 键，`notes` 明说「只有时间推进，不回血，
  不恢复疲劳」。**建议不会让人回血**。
* 模板声明了 costs 时，钱粮不足 → 只有拒绝（`reason: resource`），不出现免费休息。
* 模板声明了 effects 或 costs 时，眼下只有 `/wait`（无费用、无效果）可执行，
  方案标 `supported: false`、`unsupported: ['rest_effects']`，等接线层走既有 action 管线。

## 7. 公开摘要 vs 引擎内部定义

* `public(plan, story)` 是**白名单**投影：`action_id` / `label` / `costs` /
  `duration_hours` / `check` / `ends_event` / `intent_aliases` / `kind` / `target` /
  `supported` / `unsupported` / `duration_source`，以及 `travel` / `wait` / `source` /
  `recipient`。`success_text` / `failure_text` / `narrative_cues` / 线索正文 / 分支正文
  **一律不出现**，`notes` 也不外露。
* `describe(session, story, action_id, characters)` 返回完整方案（含 `action` 的
  `success_text` 等），**归引擎内部**，不得直接回给玩家。
* 分支命中依赖 NPC 秘密信念或未知 flag 时，`build` 只产出方案本身，`public` 不透露
  命中依据；被挡住的只给公开阻碍。

## 8. 建议（suggest）

* 复用 `free_actions` 的弱匹配（`tokens` / `score` / `alias_hits` / 否定处理 /
  `MAX_CANDIDATES`），只匹配**公开文本**：`label` + 作者声明的 `intent_aliases`。
* 返回结构与 `free_actions.suggest` 同形：`{matched, ambiguous, unjudged, note, confirm_state}`。
* 只推荐 `supported: true` 且能交给既有管线的方案（有 `action`，或 `travel` / `wait`）。
  缺口方案（give / 实例 use / 带路费的 travel / 带效果的 rest）**不进建议**。
* 没匹配上 → `matched: []`、`unjudged: true`，明确「引擎不裁定未声明的行动」。

## 9. 确认：已接线，复用既有凭据

`free_actions.confirm_token` 只认当前事件里的 `action_id`，所以接线分两层，不另算哈希：

* `free_actions.resolve_action(session, story, node, action_id, plans, characters)`：
  **先静态、后动态**。动态 id 一律 `adventure:` 前缀，新机制包里作者静态动作不得占用它
  （`Runtime.validate_package` 在打包时拒），所以同一 id 不会同时指两个动作。
* `Runtime.resolve_action`：动态方案**必须**带 `confirm`；凭据用同一个
  `free_actions.confirm_token`（CAS 仍是 `state_version`），且与后续执行用的是**同一次**
  扫描结果，不会出现“凭据验了却找不到动作”。静态动作不传凭据仍是旧的直接按钮行为。
* `/intent`、`/confirm/{id}`未改：`free_actions` 在包声明本块时内部现算方案，所以它们
  直接拿到动态候选与 `confirm`；已由 `tests/test_adventure_execution.py` 跑真实入口验证。

## 9.1 重复语义

| 类型 | 语义 |
|---|---|
| 静态事件动作 | 本事件内一次（`actions_done`），回滚回事件起点后可重做 |
| 动态观察/调查/交涉/取物 | 同上（与静态一致，不另开账本） |
| 休息 / 旅行 | **可重复**：不进 `actions_done`，因为他们本身就是时间推进 |
| 奖励 | 沿用既有 `grant_id` 幂等（种子+来源+条目），重试不重复发放 |

## 10. 已知缺口（作者必须知道）

| 缺口 | 标记 | 等待 |
|---|---|---|
| rewards 物品实例的使用效果 | `unsupported: ['instance_effect']` | 物品效果执行器（p5） |
| 物品转交（legacy 与实例） | `unsupported: ['inventory_handover']` | 物品转移执行器（p5） |
| 声明了路费的旅行 | `unsupported: ['route_cost']` | 接线层在 `move` 前扣费 |
| 声明了效果/费用的休息 | `unsupported: ['rest_effects']` | 接线层走既有 action 管线 |

确认凭据已接线（见 §9），不再列为缺口。


## 11. 测试

`tests/test_adventure_actions.py`（24 项，全部离线、夹具写死在文件内）：

1. 无声明块 → 全部 no-op；版本/未知字段/交叉引用/非邻接路线/未点名接收人/非法检定拒绝。
2. 八类行动各自：合法方案、非法目标、条件未成立的公开阻碍。
3. 隐藏地点 / 隐藏物品 / 隐藏人物既不出现也不计数，拒绝理由里也不出现。
4. 建议零副作用：调用前后 session 逐字节一致、`state_version` 不变。
5. 公开摘要不含未发生的结果与线索/分支正文；字段集合受白名单约束。
6. 旅行：已知邻接、无路线落回 `local.travel_hours` 并注明、条件封锁只给公开阻碍、
   异世界/未关联网拒绝、无坐标只给声明时长、路费标记 unsupported。
7. 休息：默认无效果（不回血）、越界/布尔/负数拒绝、钱粮不足只拒绝不免费。
8. 模板自带的条件不成立时不发方案，只给公开阻碍（不给一个必被 Runtime 拒的死按钮）。
9. 物品：legacy 与实例分开、owner 过滤、缺执行器的方案不产生 op。
10. 映射到既有 schema：效果 op 都在 Runtime 支持集合内、`free_actions.summarise` 能直接吃。
11. 一处**真跑**的对接：动态动作**不写回故事包**，凭据用既有算法算得出，`prepare_turn`
    把线索写进 `facts` / `heard`（走 `Runtime._apply_effects`，不是 mock）；另有一条断言
    静态动作不得占用 `adventure:` 前缀。

`tests/test_adventure_execution.py`（23 项，真实 Store + `Service.turn` + `Runtime.move`）：

1. 观察/调查/交涉各真实执行一次：时钟 +1、成本进 `local.ledger`、线索按
   `confirmed`/`known_by` 分落 `facts`/`heard`；调查未确认的只进 `heard`，不进 `facts`。
2. 隐藏目标、秘密分支正文、`author` 人物都不进入玩家视图。
3. 确认凭据：过期/换 session/无凭据一律拒，且 `state_version` 与全状态逐字节未变。
4. 未知/被封锁目标（含 `adventure:observe:vault`）在副作用前被拒。
5. 重试不重复扣费（`actions_done` + 既有 ledger 只记一次）。
6. 静态事件动作仍可不带 `confirm` 直接执行（旧按钮兼容）。
7. 旅行：事件未结束→拒；`route.hours=3` 与 `local.travel_hours=2` 不同，`move` 真实推进 3h；
   条件封锁的路线直接调 `move` 也被拒并给公开阻碍；异世界路线拒。
8. 真实 `/intent` → `/confirm` → `/chat`：不改 web 也能拿到动态候选与凭据并执行成功。
9. 旧包（无 `mechanics.adventure`）：`surface` 无 `adventure` 键、`move` 仍取 `local.travel_hours`、
   `/intent` 只返回静态候选。
