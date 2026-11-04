# 判定系统 v2（d20）规格

## 新玩法：四档差值模式

新作者内容显式开启 `{"version":2,"tier_mode":"margin_four"}`，审计规则版本为 `d20_margin_v3`。`version` 是声明结构版本，`tier_mode` 是分档模式，两者不能互相代替。没有 `mechanics.checks` 的包仍用 `attribute_v1`；已有 checks v2 包缺省 `tier_mode=legacy_five`，继续本文下方五档规则与 `d20_v2` 审计。旧 `partial` / `setback` 仅在旧模式可读，不迁移已有包或存档。新 `town_day()` 及对应仓库导出显式启用四档，正式库内已保存的 revision 与已绑定 revision 的旅程不会被改写。

四档模式仍按 `total = 保留d20 + 属性修正 + 疲劳修正 + 因素修正 + 加码`、`margin = total - DC` 结算，优势/劣势先取保留骰。处境只影响效果，不增加档位或改变差值边界。动作可只给严格整数 `dc`（2..30）；同时给 `difficulty` 时 DC 优先，但给出的 difficulty 仍须是 0..1 的有效数值。两者皆缺或非法 DC 拒绝提交。v1 仍要求原 difficulty 契约。

| tier | 标签 | 默认边界 |
|---|---|---|
| critical | 大成功 | margin >= 10 |
| success | 成功 | 0 <= margin < 10 |
| failure | 失败 | -10 < margin < 0 |
| disaster | 大失败 | margin <= -10 |

作者可在 checks 配置 `thresholds: {"critical":10,"success":0,"disaster":-10}`。各值必须是严格整数（拒绝 bool、字符串、小数、未知键），并满足 `disaster < success < critical`。默认天然 1 / 20 **不覆盖**差值；显式 `natural_override: true` 才令保留骰天然 20 为大成功、天然 1 为大失败。该开关必须严格布尔。旧五档模式不能设置这两项以免产生无效配置。预览把握按相同阈值、天然开关及成功集合 critical/success 精确计算。

四档的 `check.tiers` 使用以上四个 id，真实应用对应 `effects` 和 `text`，不是仅显示标签。`action.effects` 所有档位共用；critical/success 追加原 `action.success`，failure/disaster 追加原 `action.failure`，再追加对应 tier effects。四档不会自动触发旧 partial 默认代价或 setback 提示。进度钟 critical 比 success 多一格；危险钟用 `{"id":"...","failure":1,"disaster":2}`，分别在失败/大失败实际推进。作者需要不同具体后果时必须声明 tier effects。

预览 `check.v2` 携带 `tier_mode` 和 `rules_version`。四档结算的 `last_check.status` 为 `rolled` 或 `auto`；自动成功仍是 success 档，不是新增档位，`rolled=false,dice=[],kept=null,total=null,margin=null`。社交门槛拒绝为 `status=refused,tier=null,rolled=false`，`refused` 与 `reason` 保留同一公开理由字符串（不带隐藏底线条目），不扣成本、不计结果档。重试阻断继续在执行前拒绝，不掷骰、不扣成本。旧五档公开拒绝记录保持原形。

确认凭据绑定四档规则配置、完整动作检定与加码；阈值或天然开关变更会失效。结算的冻结 `plan` 保存规则配置及成本前的修正/DC，沿用 `resolve(planned=...)`，费用不会反改已确认判定。生产入口仍必须传真实 `characters`，不能依赖 50 回退。

最小原创示例见 `tools/oracle_example.py`（只返回独立字典，不写正式包）与 `docs/examples/achilles-oracle.md`。规则及真实 HTTP 测试见 `tests/test_checks_v2_four.py`。

以下章节记录旧五档的完整行为；其中“天然优先”“partial/setback”等只描述 `legacy_five`。


状态：**已实现**（v2 核心 + 后端接线 + 前端展示 + 铜杯镇试点）。与本文有偏差的地方及真实限制记在 §13「实现现状」。

核心原则不变：**规则决定发生了什么，模型只负责表达**。骰子、档位、钟、目击全部由引擎确定性结算；模型不能改结果、不能造事实/钱物。

## 0. 开启与兼容

- 故事包显式声明 `story.mechanics.checks = {"version": 2, "die": "d20", ...}` 才启用。
- 未声明：现有 `attribute_v1`（`drama.resolve_check`）**逐字节不变**，旧包、旧存档、旧凭据、旧 surface 都不变。
- 同一包内所有检定统一走 v2；v2 包里的 `check.difficulty` 仍可用（换算为 DC，见 §2）。
- 审计记录 `rules_version: "d20_v2"`，与 v1 记录并存于 `session['checks']`。

## 1. 包级配置 `mechanics.checks`

```json
{"version": 2, "die": "d20",
 "display": "transparent",                // transparent | qualitative，见 §9
 "default_position": "risky",
 "default_effect": "standard",
 "factors": [ /* 全局修正因素库，见 §5 */ ],
 "push": [ /* 加码选项，见 §7 */ ],
 "clocks": [ /* 进度钟/危险钟，见 §3 */ ],
 "social": { /* NPC 社交画像，见 §4 */ },
 "default_costs": { /* 成功但有代价的默认代价，见 §2.4 */ },
 "retry": {"same_approach": "refuse"}     // refuse | harder，见 §7
}
```

pydantic 严格校验（`extra='forbid'`），任何引用（物品、标记、人物、钟、资源）不存在即拒绝提交包。

## 2. d20 结算

### 2.1 数值

| 量 | 规则 |
|---|---|
| 属性修正 `mod` | `round((属性值 − 50) / 5)`，属性 0–100 → −10..+10（与 v1 每 0.05 一格等价） |
| 疲劳 `fatigue_pen` | `−round(疲劳 × 4)`，疲劳 0–1 → 0..−4 |
| 因素 `factors` | 适用因素 `mod` 之和，夹到 −5..+5（§5） |
| 加码 `push` | 选中的加码选项 `bonus`（§7） |
| DC | `check.dc`（整数 2..30）优先；否则 `11 + round((difficulty − 0.5) × 20)`；再叠加社交调整（§4），最终夹到 2..30 |
| 骰子 | `d = int(sha256(seed).hexdigest()[:12], 16) % 20 + 1`；优势/劣势再掷一颗，种子 `seed + ":b"`，取高/低 |
| 总值 | `total = d + mod + fatigue_pen + factors + push` |
| 差值 | `margin = total − DC` |

种子沿用现有写法（`{session.seed}:{node}:{action}`，兜底含尝试次数），保证重试/回滚掷出同一结果。

### 2.2 处境（position）与档位

五个档位：`critical` 大成功 / `success` 成功 / `partial` 成功但有代价 / `setback` 失败但前进 / `disaster` 失败且恶化。

| 处境 | critical | success | partial | setback | disaster |
|---|---|---|---|---|---|
| controlled 稳妥 | 天然 20 或 margin ≥ 10 | margin ≥ 0 | −5 ≤ margin ≤ −1 | margin ≤ −6 | 不会出现（最差 setback） |
| risky 冒险（默认） | 天然 20 或 margin ≥ 10 | margin ≥ 0 | −3 ≤ margin ≤ −1 | −9 ≤ margin ≤ −4 | margin ≤ −10 或天然 1 |
| desperate 孤注一掷 | 天然 20 或 margin ≥ 8 | margin ≥ 0 | 无 | −5 ≤ margin ≤ −1 | margin ≤ −6 或天然 1 |

天然 1 在 controlled 下为 setback。兼容布尔：`success = tier in (critical, success, partial)`。

### 2.3 效果（effect）

`limited` 有限 / `standard` 标准 / `great` 显著。决定进度钟推进格数（§3）。`desperate` 处境下 effect 自动升一级（最高 great）。

### 2.4 档位后果

动作仍用既有 `success` / `failure` 效果列表：critical/success/partial 应用 `success`，setback/disaster 应用 `failure`。另加可选 `check.tiers`：

```json
"tiers": {
  "critical": {"effects": [...], "text": "额外收获的结果文本"},
  "partial":  {"effects": [...], "text": "..."},
  "setback":  {"effects": [...], "text": "..."},
  "disaster": {"effects": [...], "text": "..."}
}
```

- 效果 op 只能是 `Runtime._apply_effects` 既有 op 加 `clock`（§3）；奖励仍走既有 rewards。
- 作者没写 `partial` 时，引擎从 `default_costs` 取一项代价，按声明顺序选第一条当前可执行的：
  `{"kind": "time", "hours": 1}` / `{"kind": "resource", "id": "pence", "amount": 2}` / `{"kind": "relationship", "target": "present", "delta": -0.05}` / `{"kind": "flag", "id": "exposed", "value": true}`。都不可执行时只写一条公开回执「做到了，但不太体面」。
- 作者没写 `setback` 时：若动作或事件声明了 `fallback_hints`（与兜底共用格式）就给下一条未给的提示，否则给通用回执「没成，但你看清了阻碍在哪」。**setback 永远不软锁**：不能写 `ends_event` 以外的阻断。
- 作者没写 `disaster` 时：危险钟 +1（若声明了 `danger_clock`），否则同 setback。
- 结果文本优先级：`tiers[tier].text` > 既有 `success_text`/`failure_text`。

## 3. 进度钟与危险钟

```json
"clocks": [{"id": "sway_guild", "label": "说服行会", "segments": 4, "kind": "progress",
            "known_by": ["player"], "on_full": [{"op": "flag", "id": "guild_convinced", "value": true}]},
           {"id": "guard_suspicion", "label": "守卫起疑", "segments": 4, "kind": "danger",
            "known_by": ["player"], "on_full": [{"op": "flag", "id": "guards_alerted", "value": true}]}]
```

- 动作 `check.clock = {"id": "sway_guild"}`：critical 填 effect 格数 +1，success 填 effect 格数，partial 填 effect 格数 −1（至少 0）。effect 格数：limited 1 / standard 2 / great 3。
- 动作 `check.danger_clock = {"id": "guard_suspicion", "setback": 1, "disaster": 2}`（数字可省，默认 1/2）。
- 新效果 op：`{"op": "clock", "id": "...", "delta": 整数}`（只在声明了 clocks 的包里合法，可正可负）。
- 状态 `session['clocks'] = {id: {"filled": n, "full_at": time|null}}`，随快照回滚。满格时 `on_full` 恰好执行一次（与 pressure 一样幂等）；满格后不再变化。
- 玩家只看到 `known_by` 含 player 的钟：label、segments、filled。

## 4. 社交难度来自人物，且只在需要时掷骰

```json
"social": {"grain_broker": {"interests": ["profit", "reputation"], "boundaries": ["family", "theft"],
                            "trust_weight": 10}}
```

动作 `check.social = {"target": "grain_broker", "appeals": ["profit"], "violates": []}`：

- `violates ∩ boundaries` 非空：**不掷骰，直接拒绝**。tier 记为 `refused`，不扣成本、不推进时间，返回公开理由（取自 social 画像的可选 `refusal_text`，否则通用「这触到了他的底线」）。不进 actions_done，可换方式再来。
- `appeals ∩ interests`：每命中一项 DC −3，最多 −6。
- 信任：`DC −= round((trust − 0.5) × trust_weight)`，trust 取 `development.<npc>.relationships.<hero>.trust`，默认 0.5；`trust_weight` 默认 10。
- 目标人物必须在场；不在场时候选不提供此动作（`public_obstruction` 说明）。

**不掷骰的门槛**：`check.auto = {"all_flags": {...}, "items": [...], "max_dc": 6}`（任一子条件可省）。条件成立或最终 DC ≤ `max_dc` 时直接判 `success`，不掷骰；审计记 `rolled: false` 与原因。默认 `max_dc` 不设，即不自动跳过。

## 5. 修正因素（封闭清单）

全局 `checks.factors` 与动作 `check.factors`（引用全局 id 或内联）：

```json
{"id": "has_manifest", "label": "你拿着运货单", "mod": 2,
 "when": {"kind": "item", "id": "manifest"}}
```

`when.kind` 只允许：
- `item`：主角持有物品 / 奖励实例模板；
- `flag`：`{"id", "value"}`；
- `companion`：某 NPC 在场且信任 ≥ `min_trust`；
- `profile`：开局 start profile id；
- `place`：当前地点 id 或地点 `tags` 包含某标签；
- `time`：游戏小时在 `[from, to)`（可跨午夜）；
- `attribute_axis`：仅当检定属性为某轴时生效（例如「天黑」只罚 wisdom 观察）。

每项 `mod` −3..+3，`advantage: true` / `disadvantage: true` 可替代 mod（同时出现优势与劣势则抵消）。是否适用**全部由引擎判定**，模型不参与，玩家也不能自称。玩家预览只给 label 与「有利 / 不利」，不给数字（`display=transparent` 时结算后给数字）。

civ-atlas 环境（群系、气候）作为 `place.tags` 由作者或原生开局写入；资源层未映射，不得以此编造因素。

## 6. 察觉检定（目击）

动作 `check.concealed = {"observers": "present", "notice_attribute": "wisdom", "notice_bonus": 0}`：

1. 先结算主检定（隐匿手法），得 `total`。
2. 当前事件参与者中**与主角同地**的每个 NPC 各掷察觉：`d20(seed + ":notice:" + npc) + mod(该 NPC 的 notice_attribute) + notice_bonus`，≥ 主检定 `total` 即察觉。
3. 目击集合 = 既有 `witnesses`（声明为必然看见的）∪ 察觉成功者。
4. 该集合替换原先「声明的 witnesses ∪ social[branch]」，交给 `npc_cards.remember_action` 和 `scene_judgment` 的 observers。没察觉的 NPC 不记忆、不作反应。
5. 玩家只看到「似乎有人注意到了 / 没人注意」，以及察觉者是否在其可见范围内；`display=transparent` 时显示察觉者的骰面。

未声明 `concealed` 时保持现有声明式目击行为。

## 7. 重试与加码

**重试**：v2 记录 `session['check_attempts'][node:action] = [{"attribute", "factors": [ids], "push", "tier"}]`。
- 静态动作仍是一次性的（actions_done），所以重试只涉及可重复动作、动态方案和兜底。
- 上一次 setback/disaster，本次属性与因素集合**完全相同**且没有加码：`retry.same_approach = "refuse"` 时候选标 `blocked: true`，提示「同样的办法刚失败过：换个方法、找帮手、做准备或等局面变化」；`"harder"` 时 DC +3（每次累加，最多 +9）。
- 回滚时随快照恢复。

**加码**：

```json
"push": [{"id": "grease", "label": "多塞两便士", "cost": {"pence": 2}, "bonus": 2},
         {"id": "strain", "label": "咬牙硬撑", "fatigue": 0.15, "advantage": true},
         {"id": "favor", "label": "动用人情", "relationship": {"target": "check_target", "delta": -0.1}, "bonus": 3}]
```

- `Turn.push: str | None`（contracts，默认 None）。每次检定最多一个加码。
- 代价在掷骰前扣除（与成本同批，付不起拒绝，零副作用）；`relationship` 的 `check_target` 指 `check.social.target`。
- 动作可用 `check.push_allowed: ["grease"]` 限制可用加码；缺省为全部。
- **确认凭据包含加码 id**：`confirm_token(..., push=None)`；`/confirm/{action_id}?push=<id>` 返回对应凭据与预览。

## 8. 一次检定的完整流程

```
意图 → 候选（free_actions，含兜底）
  → 可行性门槛：前置、成本、目标在场、社交底线（refused 不掷骰）
  → 是否需要掷骰（auto / max_dc）
  → 预览：处境、效果、适用因素（有利/不利）、大致把握、可选加码 → 玩家确认（CAS 含 push）
  → 扣成本与加码代价 → d20 结算 → 档位
  → 察觉检定（concealed）→ 目击集合
  → 档位后果 + 进度钟/危险钟
  → 人物反应（scene_judgment：模型从声明选项里选，observers = 目击集合）
  → 叙述（模型只拿已结算的公开结果）
```

## 9. 公开投影

**候选 / 确认预览**（`free_actions.summarise` 在 v2 包中追加字段；旧包不变）：

```json
"check": {"attribute": "social", "difficulty": 0.5,
          "v2": {"position": "risky", "effect": "standard",
                 "chance": "中",                     // 大 ≥65% / 中 35–65% / 小 <35%（按当前总修正与 DC 精确计算）
                 "dc": 12,                            // 仅 display=transparent
                 "factors": [{"label": "你拿着运货单", "sign": "+"}],
                 "auto": false, "refused": null, "blocked": false,
                 "push_options": [{"id": "grease", "label": "多塞两便士", "cost_text": "2 便士"}],
                 "clock": {"label": "说服行会", "segments": 4, "filled": 1}}}
```

**结算后**：`result['check_public']` 写入 surface 的 `last_check`（只保留本轮的那一条）：

```json
{"rules_version": "d20_v2", "rolled": true,
 "dice": [14], "kept": 14, "advantage": null,
 "modifier": 3, "dc": 12, "total": 17, "margin": 5,   // 数值仅 display=transparent
 "tier": "success", "tier_label": "成功",
 "factors": [{"label": "你拿着运货单", "sign": "+"}],
 "push": {"label": "多塞两便士"} ,
 "noticed": "没人注意到",
 "clock": {"label": "说服行会", "from": 1, "to": 3, "segments": 4}}
```

`display=qualitative` 时只给骰面、档位、因素标签和钟，不给 modifier/dc/total/margin。默认 `transparent`（d20 跑团惯例）；作者可改。

**surface** 追加 `clocks`（玩家可见的钟列表）与 `last_check`；旧包缺键保持缺键。

**给模型的上下文**：只给 `tier`、`tier_label`、结果文本、目击集合、钟的变化，**不给**未发生档位的文本。叙述提示加一句「档位是引擎已裁定的事实，不能反转或升级」。

## 10. 前端

- 确认弹窗：处境/效果徽记、有利/不利因素、把握（大/中/小）、DC（transparent）、加码单选（切换后重新取凭据）、钟进度、refused/blocked 时禁用确认并显示理由。
- 结算后：d20 掷骰动画（CSS/SVG 二十面体，滚动约 1 秒后落在服务端返回的骰面上；优势/劣势显示两颗，暗化未采用的一颗），随后显示总值拆解与档位文字。动画**只展示**，结果以服务器为准；`prefers-reduced-motion` 时直接显示结果。
- 场景卡：玩家可见的钟画成分段圆环（progress 用主题绿，danger 用暖红）。
- 保持现有深绿米白视觉风格与 style.css 变量。

## 11. 文件分工（实现期）

| 范围 | 文件 |
|---|---|
| 结算核心（纯函数） | 新建 `app/checks.py` |
| 运行期接线 | `app/runtime.py`（动作检定、兜底检定、`clock` op、clocks 状态、surface `last_check`/`clocks`、包校验）、`app/free_actions.py`（预览、凭据含 push）、`app/contracts.py`（`Turn.push`）、`app/npc_cards.py`（`remember_action` 接受目击集合）、`app/scene_judgment.py`（observers 用目击集合、上下文给档位） |
| HTTP | `app/web.py`：`/confirm/{action_id}` 增加可选 `push` 查询参数并透传 |
| 前端 | `app/static/*` |
| 内容试点 | `tools/playable_scenes.py` 的 `short_town_day` 开启 v2 |

## 12. 明确不做

- 不改 v1 公式、不迁移旧包旧存档。
- 不让模型提出或判定修正因素、档位、察觉。
- 不做多角色连续对抗、群体检定、伤害/血量系统改动。

## 13. 实现现状

### 13.1 文件与入口

| 范围 | 文件 | 实现要点 |
|---|---|---|
| 结算核心 | `app/checks.py` | `plan()` / `resolve()` / `consequences()` / `notice()` / `preview()` / `public_result()` 全为**纯函数**；`advance_clock()` 是唯一的钟执行器（由 `Runtime._apply_effects` 调）；`validate_all()` 是包校验单一入口 |
| 运行期 | `app/runtime.py` | `_v2_turn()` 接线（社交门槛→扣成本→掷骰→后果→钟→察觉）；`_fallback_turn()` 的 v2 分支；`_apply_effects` 新增 `clock` op；`new_session` 建 `clocks`/`check_attempts`；`surface` 追加 `clocks`/`last_check` 与 `actions[].check_v2` |
| 预览与凭据 | `app/free_actions.py` | `summarise(..., session, node, characters, push)` 追加 `check.v2`；`confirm_token(..., push=None)`、`describe(..., push=None)`、`verify(..., push=None)`；`_check_push_affordable()` 在副作用前拒绝付不起的加码 |
| 契约 | `app/contracts.py` | `Turn.push: str | None` |
| 目击 | `app/npc_cards.py` | `remember_action(..., witnesses=None)`：给了实际目击集合就用它替换声明式目击 |
| 人物反应 | `app/scene_judgment.py` | observers 用实际目击集合；模型上下文只给 `tier`/`tier_label`/结果文本，**不给** modifier/dc/total/margin |
| HTTP | `app/web.py` | `/api/sessions/{id}/confirm/{action_id}?push=<id>` |
| 内容试点 | `tools/playable_scenes.py` 的 `town_day()` + `_town_day_checks()`；导出 `docs/playable-scenes/short_town_day.json` |
| 测试 | `tests/test_checks_v2.py`（规则）、`tests/test_checks_v2_http.py`（真实 TestClient）、`tests/test_town_day.py`（适配 v2） |

### 13.2 与规格文字的差导（作者需知道）

1. **`default_costs` 是列表**（规格 §1 的示例写成了对象）。引擎按**声明顺序**取第一条当前可执行的；`kind: relationship` 的 `target` 只能是 `"present"`（对同地全体在场者），不开放点名。
2. **`check.auto` 不能是空条件**：`{}`/`{all_flags:{}, items:[]}` 一律拒绝（否则就是无条件自动成功）。
3. **`check.tiers` 的 op 白名单**沿用 `Runtime._apply_effects` 的既有 op 加 `clock`；`reward` 也允许，但仍需包内声明 `mechanics.rewards`。
4. **`clock` op 只在声明了 `mechanics.checks` 的包里合法**；v2 包里还要求引用的钟真实存在（`_validate_action_clocks`）。
5. **因素额外支持 `visibility: "hidden"`**：照常参与结算，但标签与符号不进候选、预览与结算投影（防用因素标签反推隐藏标记/隐藏 NPC）。由 `visibility: author` / 未成立 `reveal_flag` 派生的因素也会被自动标为 hidden。
6. **因素数字只在结算后出现**：预览只给 `label` + 有利/不利（约 §5）；`factors[].mod` 只在 `display=transparent` 的 `last_check` 里给。
7. **`check.concealed` 的 `observers` 只支持 `"present"`**；另一取值直接拒绝而非静默当成 present。
8. **v2 带检定的动作必须带确认凭据**：`Runtime.resolve_action` 在 v2 包里对 `check` 动作强制要求 `confirm`（旧包/无检定的动作不变）。
9. **`NOTICED_NONE` 用的是不确定语气**（「似乎没有旁人注意到」）：引擎不会宣称「确定没人看到」。作者声明了 `witnesses` 但无人察觉到时，文案退为「似乎有人注意到了」而不是「没人注意」。
10. **钟与 `pressure` 共用 `session['time']`**：钟的进度按**行动**推进（不推游戏时间），`partial` 的 `time` 默认代价并入同一个 `pressure_rules.advance` 调用，没有第二个时钟。
11. **满格后冻结**：钟一旦 `full_at` 非空，后续 `clock` op 一律返回 `changed: false`，`on_full` 不会第二次执行。
12. **作者手写 `clock` op 时引擎不再自动推同一个钟**（避免一次行动给同一钟加两次）。
13. **代价不回写已确认的判定**：确认预览算出的那一份 `plan` 会被**冻结**并原样用于结算（`checks.resolve(..., planned=)`）。疲劳、信任、金钱的变化只影响后续，不会把本次 DC/修正改掉。
14. **`characters` 参数可缺**：`preview()` / `plan()` 在没有作者人物文档时，主角属性按 50（修正 0）降级——与 v1 的 `.5` 回退同口径；NPC 的属性**不**降级（不存在的人不会被当成在场者），社交目标在传了人物文档时仍必须真实存在。
15. **生产入口必须传真实 `characters`**：`app/web.py`（`/intent`、`/confirm`）、`app/scene_judgment.intent()`（其内部 `suggest` / `available_with` / `summarise` / `describe` 四处）、`Runtime.surface` 的动作行与 `Runtime.adventure_surface` 都从 `runtime.package(session['revision'])['characters']` 取并逐层传入。第 14 条的 50 降级**只是兼容兜底**，不得成为网页预览与执行口径不一致的来源。

### 13.3 真实限制（未做或只做了一半）

- **不加码就不能重掷**：v2 的可重复动作（兜底、动态方案）每次尝试的种子带尝试序号，所以能重试；但**静态动作仍是一次性的**（`actions_done`），所以 `retry.same_approach` 的 `harder` 实际只在可重复路径上可观测。
- **`default_costs` 的 `relationship` 代价**按「同地全体在场者」写，粒度比规格细（规格只给了 `present`）。
- **察觉只覆盖 `check.concealed` 的显式声明**：没有声明时仍走既有声明式目击（`witnesses` ∪ `social[branch]`），未做「未声明也能自动察觉」的推断。
- **钟的 `known_by` 是逐钟声明的**：一个钟可以只给某个 NPC 看（试点包里 `guard_note` 就是这样），玩家侧完全不出现。
- **civ-atlas 群系/气候**目前只能作为地点 `tags` 手写进包，未做从资源层自动映射（与规格 §5 最后一段一致）。
- **未做**：多角色连续对抗、群体检定、伤害/血量系统改动（同 §12）。

