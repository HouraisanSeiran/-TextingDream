# 任务与地方后果契约（`story.mechanics.quests`）

实现：`app/quests.py`　测试：`tests/test_quests.py`

**定位**：给作者一套**有限的因果**——一个委托人、一个需求、一组完成证据、一组后果。
不是 NPC 循环，不是势力模拟，不做巨大经济 tick。没有声明就没有任何行为（旧包一字不变）。

---

## 1. 复用而不新建

| 已有 | 本模块怎么用 |
|---|---|
| `LocalState.flags` | 地方后果的开关（`flag` op），不另建标记表 |
| `local_rules` 资源 | `resource` op，不另建库存账 |
| `rewards` 账户/模板 | 报酬只能引用**已声明**的 `account` / `template` |
| `Runtime.effects` | 唯一执行器；本模块只产出它吃得下的 effect 列表 |
| `pressure` 时钟 | 期限只用游戏时刻（`session['time']`），不建第二时钟 |
| `session` 快照 | 任务状态住 `session['quests']`，跟既有回滚 |
| `facts` / `beliefs` / `heard` | 知情用既有 `information` op |

**没有**第二个账本、第二个时钟、第二个确认 token。

## 2. 声明结构

```json
{"mechanics": {"quests": {"version": 1, "quests": [{
  "id": "escort",
  "giver": "miller",
  "location": "square",
  "title": "送柴去磨坊",
  "public_summary": "把一捆柴火送到磨坊。",
  "secret_objective": "（作者侧，绝不进玩家投影）",
  "known_by": ["player"],
  "reveal_flag": "heard_rumour",
  "objectives": ["把柴火送到"],
  "evidence": [{"kind": "flag", "id": "firewood_delivered"}],
  "costs": [{"kind": "resource", "id": "plank", "amount": 2}],
  "rewards": [{"kind": "currency", "id": "coin", "amount": 30, "payer": "miller"}],
  "effects": [{"op": "flag", "id": "mill_refurbished", "value": true},
               {"op": "resource", "id": "plank", "delta": 2},
               {"op": "information", "text": "旧粮仓的地板朽了",
                "confirmed": true, "known_by": ["player"]}],
  "on_failure": "fallback_quest",
  "duration": 10
}]}}
```

### 字段

| 字段 | 含义 |
|---|---|
| `id` | 稳定 id（`^[A-Za-z0-9_-]{1,60}$`）。引用、发奖、回滚都靠它 |
| `giver` | 委托人（已声明的人物/组织 id） |
| `location` | 绑定的地点；不在该处或不曾到过就不提供 |
| `title` | 作者侧标题（也用于 action 标签） |
| `public_summary` | **玩家可见的一句话。留空 = 整个任务不上台面** |
| `secret_objective` | 隐藏目标，只进 `authority_view` |
| `known_by` | 受众门禁；空 = 不限受众 |
| `reveal_flag` | 需已置位的 flag 才提供 |
| `objectives` | 作者描述的目标（判定完成靠 `evidence`） |
| `evidence[]` | 完成证据：`flag` / `resource`(≥`at_least`) / `visited` |
| `costs[]` | 完成要付的成本：`resource` / `item` |
| `rewards[]` | `currency`（必填 `payer`）/ `item`（必填已声明 `template`）/ `relationship` / `clue` |
| `effects[]` | 后果，只允许 `flag` / `resource` / `information` |
| `on_failure` | 失败后接哪条已声明任务（不能指向自己、不能成环） |
| `deadline` **或** `duration` | 二者只能选一个；都以 `session['time']` 计 |

## 3. 三条硬边界

### 3.1 报酬必须有来源

- `currency` → `payer` 必须是 **已声明** 的 `mechanics.rewards.accounts` 里的账户，
  且 `amount ≤ account.initial`（上限，不是现有余额）；受理时由 `rewards.apply` 真实扣款。
- `item` → `id` 必须是已声明的 `rewards.templates`。
- `relationship` / `clue` → 必须写清 `text`（非财物收益不能是空的）。
- **模型无法造钱造物**：模块只把“已声明的引用”翻译成 claim。

### 3.2 完成必须有证据

`evidence` 声明的是**已经存在的状态**。证据不足 → `apply_completion` 拒收并说明缺什么；
不会把“玩家说完成了”当完成。

### 3.3 知情是分级制的

`public_summary` / `known_by` / `location` / `reveal_flag` 四个字段共同决定谁能看到什么。
**被救的人知道、不等于全天下知道**。未公开的任务连数量都不进玩家侧。

## 4. 状态机

```
proposed ──accept──→ accepted ──start──→ active ──complete──→ completed
   │                    │                  │
   └────────────── cancel ────────────────┘→ cancelled
                        └── expire（到期）──→ failed ──on_failure──→ 后继任务 proposed
```

- 只有 `active` 可以完成。
- `expire` 只由**显式的时间推进 hook** 调用（`runtime_hooks()['on_time_advance']`），
  任何读接口（`state` / `due_at` / `available` / `public_view` / `actions`）都不推进状态。
- 失败与取消**不死档**：旅程继续，后继任务可接上。

## 5. 调用面

```python
rules(story) -> Quests | None        # 无 key = None，一切 no-op
validate(story) -> Quests | None     # 拒收无来源报酬 / 无证据 / 成环 / 未知键
state(session, cfg) -> {entries}     # 纯读，缺块当空，不写
ensure(session, story) -> cfg|None   # 只在候选会话上建块，读接口不调

propose / accept / start / cancel    # 状态迁移
expire(session, story, quest_id=None)   # 只由时间推进调用
due_at(session, quest_id, story)     # 纯读
completion(session, story, quest_id)    # 干跑：缺什么、将要发什么
apply_completion(session, story, quest_id, effects_fn=, source=)   # 原子完成

available(session, story, audience)      # 可见任务（无秘密）
public_view(session, story, audience)    # 玩家投影 + 计数
authority_view(session, story, quest_id=None)  # 作者视图（含秘密/付款方）
context_snippet(session, story)          # 有界一行，给 prompt
actions(session, story, audience)        # 既有 action 形状的候选
apply_transition(session, story, id, transition, effects_fn=, source=)
runtime_hooks()                          # 给 Runtime 的四个接点名
```

## 6. 原子性与幂等

`apply_completion` 在 **深拷副本** 上执行成本/后果/发奖，全部成功后才 `session.clear(); update(work)`。
所以“成本不够”整批零写（有测试逐字对比前后 session）。

重复完成是 no-op：任务已 `completed`；reward claim 的 source 是稳定的 `quest:<id>`，
`rewards.apply` 本身就对同一 source 只发一次。

## 7. 回滚

任务状态住在 `session['quests']`，跟着story快照回滚——没有第二份要同步的状态。

## 8. Runtime 接点（本轮不改 runtime）

```python
# 1) 打包校验（紧跟 towns_store / world_history_store 之后）
quests.validate(story)

# 2) 时间推进（唯一时钟推进处）
quests.expire(session, story)

# 3) action 确认路径
quests.apply_transition(session, story, quest_id, transition,
                        effects_fn=rt.effects, source='quest:' + quest_id)

# 4) surface / context
surface['quests'] = quests.public_view(session, story)
```

## 9. 明确不做

- 不做 NPC 自主循环、势力全模拟、战斗系统（p5）。
- 不做巨大经济 tick，不做第二套账本/时钟/凭据。
- 不凭模型制造财物、造目标、造知识。
- 不用 traits/关系做 `argmax` 自动叛变——它们只能作为合法输入。
- 不在读接口里推进任务或发奖。
