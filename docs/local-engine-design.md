# 本地规则与内容生成内核 · 技术细则

配套文档：`织梦_TextileDream_策划案.md` §12–§14。本文只写**已确认设计**与**当前实现事实**，不写代码，不改工程说明。

版本：2026-10-25

> **修订 2026-10-25**：本文已按主审意见收敛阶段 1 边界。阶段 1 = 严格参数/约束 + 固定白名单派生 + 奖励原子幂等 + 会话快照内账本 + 公开投影/重启/回滚闭环。可编程派生公式、永久审计表、别名表均列为后续。
>
> **同日收官**：阶段 1 **已实现并通过验收**。代码 `app/rewards.py`（配置来自 `story.mechanics.rewards`），测试 `tests/test_rewards.py`（38 项全过）；浏览器桌面与 390 宽共 34 项检查 0 失败；主代理最终全量回归含原 120 + 奖励 38，exit 0（3 skip）。示例入口：`docs/examples/rewards-demo.story-fragment.json` 与 `docs/examples/rewards-使用说明.md`。阶段 2/3 仍未实现。

## 0. 一句话定位

织梦不训练语言模型。引擎是本地规则与内容生成内核：**本地裁定发生什么，DeepSeek 负责把它写成文字**。影响存档的每一个判断都必须由声明式数据 + 固定公式算出来，可重放、可审计、可回滚。

## 1. 与现有实现的关系

| 已有能力 | 位置 | 本文档做什么 |
|---|---|---|
| 声明式资源/日程/作息，会话内 `local.resources` 与 `local.ledger` | `app/local_rules.py` | 扩展为通用物品与奖励账本，不推翻结构 |
| 确定性掷点：seed = 旅程 + 事件 + 动作，sha256 取小数，写 `rules_version=attribute_v1` | `app/drama.py` | 奖励与物品派生沿用同一 seed 链与版本标记 |
| 模型失败整轮不提交；客观事实/信念/所闻分表 | `app/service.py`、`app/storage.py` | 账本条目与状态同事务，不分家 |
| `state_version` 乐观并发 + `BEGIN IMMEDIATE` | `app/storage.py` | 账本与实例存放在会话快照里，同事务写入 |
| 故事包事务提交（日志 + 暂存 + 换目录） | `app/package_transaction.py` | 不变；物品模板属于故事包内容，走版本化 |

## 2. 物品模型

### 2.1 模板与实例

- 模板（template）：`template_id`、材质、形制、品质、可选覆盖的 `weight`/`durability`/`mana_capacity`、附魔清单、未鉴定标签。模板属于故事包内容（`mechanics.rewards.templates`），版本化编辑；**模板不能携带自定义公式**，派生公式属于代码。
- 实例（instance）：`instance_id`、`template_id`、所属、附魔列表（带等级）、鉴定状态、来源与创建时间。初始化时写一份 `stats_cache`，但标 `authoritative: false`，只供审计。
- 一个模板可产生任意多实例；实例不共享可变状态。物品奖励产**实例**，不改模板。
- 模板与实例的配置边界：模板在 `mechanics.rewards.templates`（故事包内容），实例在 `session['rewards']['items']`（旅程快照）。

### 2.2 四层（本版实际落地）

| 层 | 本版实际字段 | 谁能写 | 说明 |
|---|---|---|---|
| 基础 base | 材质 `damage_bonus`/`value_percent`/`weight_percent`、形制 `base_damage`/`base_value`/`base_weight`/`base_durability`/`mana_capacity`、品质 `value_percent`/`durability_percent`/`enchant_budget`、附魔 `damage_per_level`/`value_percent_per_level`/`group`/`hidden` | 故事包配置 | 版本化编辑 |
| 实例 instance | `id`、`template`、`name`、`material`、`shape`、`quality`、`enchantments[{id,level}]`、`identified`、`owner`、`location`、`rules_version`、`origin_result_id`、`origin_source`、`created_time`、`stats_cache` | 规则裁定 | `stats_cache` 不权威 |
| 动态 dynamic | **本版没有**。耐久与魔力不消耗、不修理、不充能，`mana` 恒为 0 | — | 列为后续 |
| 派生 derived | `weight`、`durability`、`damage`、`value`、`mana_capacity` | **无人可写** | 每次读取按固定公式重算 |

### 2.3 本版实际支持的参数维度

材质 material、形制 shape、品质 quality、附魔 enchantment（含互斥组与 `hidden`）、重量 weight、价值 value、耐久 durability（静态）、魔力容量 mana_capacity（静态）、鉴定状态 identified、隐藏属性 hidden。

**本版未实现、不得写作已支持**：尺寸 size、时代 era、制造者 maker、来源谱系 provenance、磨损 wear、绑定 binding、损坏/维修 broken/repair、充能。也没有战斗/负重/交易执行器。

### 2.4 派生：阶段 1 是固定公式集（不是可编程算子树）

- **阶段 1 形态（已实现）**：派生值由 `app/rewards.py` 里写死的固定公式计算，全整数运算（`base * percent // 100` 与加法），并按 `max(0/1, …)` 做上下限。公式集合有界、随 `rules_version = 'rewards_v1'` 发布。故事包与作者**只能选参数，不能写公式**。
- **具体公式**：`weight = 模板覆盖 或 形制基础重量 * 材质重量百分比 // 100`；`durability = 模板覆盖 或 形制基础耐久 * 品质耐久百分比 // 100`；`damage = 形制基础伤害 + 材质伤害加成 + Σ(已公开附魔.每级伤害 * 等级)`；`value = (形制基础价值 * 品质价值百分比 // 100) * 材质价值百分比 // 100 + Σ(公开附魔部分价值 * 每级百分比 * 等级 // 100)`；`mana_capacity = 模板覆盖 或 形制魔力容量`。
- **缓存不权威**：实例里的 `stats_cache` 标了 `authoritative: false`，只供审计；**每次读取都重算**，故意改缓存也不会改变玩家看到的数字（测试覆盖）。
- **无表达式层**：没有表达式解析、没有算子树、没有 lookup 查表、没有 when 条件分支、没有派生缓存；这些是**后续扩展**，不得列为阶段 1 待验收项。
- **仍不用 eval**：正因为阶段 1 根本没有可执行公式层，所以更不存在 `eval`/`exec`。后续若引入算子树，仍必须是声明式数据 + 算子白名单。
- **隐藏附魔不参与可见数值**：`hidden: true` 的附魔既不出现在列表，也不计入玩家可见的 damage/value，所以无法从数字反推。

### 2.5 严格参数/约束（已实现）

- 全部配置为严格 Pydantic（`extra='forbid'`）：多余字段直接拒绝。
- 每个数值带 `strict=True` 与上下界：布尔、NaN、小数、字符串数字都被拒绝，不静默夹取。
- 引用完整性在提交时校验：材质→形制、模板→材质/形制/品质/附魔、附魔互斥组、附魔等级不超品质预算、含附魔必须有正魔力容量、奖励表→奖励条目、奖励条目→货币/账户/模板/能力、能力 `requires` 成环直接拒绝。
- 行动声明校验：`rewards` 只支持 `success`/`failure`，每个分支至多 6 个 ID，引用未定义条目或表拒绝。
- **未配置就声明奖励 = 拒绝**：没有 `mechanics.rewards` 时，行动 `rewards` 与 `op=reward` 都报错，而不是默默不生效。
- 预算与声明矛盾在提交时拒绝（比如奖品最小值高于单次预算），不留下必然失败的配置。

## 3. 统一奖励计算（已实现）

金币 / 物品 / 能力 走同一条路径，由 `app/rewards.py` 根据 `story.mechanics.rewards` 裁定，不调模型、不执行任意代码。（**本版范围**：仅这三类；知识/关系/通行许可尚未接入。）

输入：

- `source`：行动 `rewards: {success: [...], failure: [...]}` 或 `op=reward` 声明；来源标识形如 `事件:动作`。
- `budget`：`max_value_per_grant`（单次硬预算，物品价值与货币数量共用同一整数单位）、`max_grants_per_event`（**本事件累计**，不是每轮清零）、`max_items`、每种货币 `maximum`。超限**整批拒绝**。
- `requirement`：能力 `requires`（含成环检测）与 `flags`（旅程里必须已成立的标记）。不满足整批拒绝。
- `payer`：仅货币奖励可用，引用 `accounts` 中**同币种**的作者侧账户，在同一批扣款；余额不足整批拒绝。不填即引擎侧发放，不表示 NPC 已付钱。

确定性 ID（实际形式）：

```
grant_id = sha256(f"{旅程 seed}:{来源事件动作}:{奖励条目 ID}")[:24]
```

- 不读时钟、不用 Python 内置 `hash`、**不含轮次计数、不含列表位置**（测试覆盖）。
- 因此同一旅程的同源事件动作条目只发一次；重复声明、重试、事件关闭后再调用都是 no-op。
- **模板候选**：物品奖励带 `templates` 候选集，用确定性流抽模板；**加权表**：行动写表 ID 时按 `entries` 权重抽恰好一条。
- **幂等**：账本在当前旅程的 `grants`/`ledger` 里按 `grant_id` 去重，同一笔在当前状态只生效一次。
- **回滚后重获**：回滚会连同 `grants` 一起恢复，所以重做同一动作会确定性重抽到同一金额/物品/附魔等级——是“允许再拿”，不是“二次发奖”。
- **已知局限**：当前事件节点只会完成一次（`completed` 去重 + 分支 key 由节点与已完成次数派生），**不承诺同节点可重复进入并每实例发奖**；循环奖励需拆成不同事件节点。
- **无独立命令 ID、无持久 pending 结果**；模型失败时整轮不提交，重试靠确定性重算。
- 记录：每笔奖励写一条 `grants` + 一条同内容 `ledger`（`grant`/`reward`/`kind`/`object`/`before`/`after`/`source`/`branch`/`time`/`rules_version`，付费时额外带 author 侧 `account` 扣款前后值）。

## 4. 持久化（已实现：`session['rewards']` 内）

- **当前状态**：继续用 SQLite 文档 + `facts`/`beliefs`/`heard` 分层表，服务「此刻是什么」的精确查询。
- **奖励状态位置**：全部在 `session['rewards']` 里——`wallet`、`accounts`、`items`、`abilities`、`grants`、`ledger`，跟随现有 `save_session` 的同一个 `BEGIN IMMEDIATE` 事务写入。**没有第二张权威表、没有独立永久审计表**。未配置奖励的旅程**不会多出这个状态键**（读路径不写状态，旧存档不被重写）。
- **原子提交**：`apply()` 在深拷贝上按序模拟整批，全部合法才写回；任一条失败整批拒绝，不留半批。奖励、状态、分层表同事务；沿用 `state_version` 乐观并发检查，陈旧写入报错且不发奖。
- **回滚**：恢复事件起点快照，**`rewards` 块随之恢复**（被撤销分支的 `grants`/`ledger`/实例都不存在）。不保留跨分支历史。
- **快照语义**：快照是**恢复状态的依据**，不是给人看的事实陈述，也不代表任何角色知情；不进模型上下文。
- **实体 ID**：实例 ID 由 `grant_id` 派生（`itm_` 前缀），跨旅程不撞号；改名不改 ID。**别名表属后续阶段**。
- **知情投影**：分 `player` / `author` 两个受众。player 只得到钱包、可见物品与公开能力；`accounts`、隐藏附魔、非公开能力仅 author 可见，且**不进表层提示词与模型输入**（测试覆盖）。未鉴定物品对玩家只给标签与重量。
- **后续演进（不在阶段 1）**：跨分支永久审计表、补偿事件、别名表。

## 5. 长线上下文目标（百万 / 千万 token）

设计原则：**不把摘要当事实，不每轮全历史，不承诺零幻觉。**

1. **当前状态精确查询**：位置、时间、持有、资源、进行中事件直接读状态。
2. **混合检索**：结构化过滤（时间/地点/实体/来源/规则版本）+ 全文检索 + 实体索引，阶段 2 叠加语义检索。每路结果带证据原文。
3. **剧情线程**：承诺、伏笔、未完成任务独立成表（发起方、对象、内容、期限、状态 open/pending/fulfilled/broken、证据引用），每轮按相关性挑选注入。
4. **证据优先**：摘要只用于导航；摘要与证据冲突时以证据为准。

## 6. 生成前后事实校验

- 生成前装配**事实包**：当前状态（机器可读）、本轮裁定结果、命中证据原文、未完成线程、允许表达的边界（不能宣称未裁定的成功、不能泄露隐藏字段）。
- 生成后**检查**：正文是否引入与事实包冲突的新事实、是否宣称未裁定的成功、是否泄露隐藏字段。
- 有影响的新事实**不直接入库**：必须走作者审核或「结构化提案 + 校验」，通过后才成为状态变更。
- **模型文本永不直接修改状态**；状态只由本地规则写入。
- 模型超时/报错不得重新掷骰、不得重复发奖。

## 7. 现状与后续演进

| 项 | 状态 |
|---|---|
| 本地资源/日程/作息 + 资源账本 | 已实现（`app/local_rules.py`） |
| 确定性掷点 + `rules_version` | 已实现（`app/drama.py`） |
| 模型失败整轮不提交 | 已实现（`app/service.py`） |
| 三张信息分表 + 表层投影 + `state_version` | 已实现（`app/storage.py`、`app/runtime.py`） |
| 物品模板/实例分层 + 固定派生公式 | **已实现并通过验收** |
| 严格参数校验 + 零写入拒绝 | **已实现并通过验收** |
| 统一奖励 + `grant_id` 幂等（含模板候选与加权表、同币种 `payer` 扣款） | **已实现并通过验收** |
| `session['rewards']` 内钱包/实例/`grants`/`ledger`（现有 SQLite 事务） | **已实现并通过验收** |
| 玩家/作者双受众投影（隐藏附魔不进数值与模型输入） | **已实现并通过验收** |
| 可编程派生公式（算子树/lookup/when/循环检测/缓存） | 阶段 2，未实现 |
| 永久跨分支审计表 + 补偿事件 | 阶段 2，未实现 |
| 实体别名表 | 阶段 2，未实现 |
| 动态耐久/魔力（磨损、修理、充能）与战斗/负重/交易执行器 | 后续，未实现 |
| 知识/关系/通行许可类奖励 | 后续，未实现 |
| 剧情线程 + 混合检索 | 阶段 2，未实现 |
| 上下文装配 + 一致性审查 + 百万/千万 token 评测 | 阶段 3，未实现 |

**阶段 1 验收证据（2026-10-25）**：`tests/test_rewards.py` 38 项全过；浏览器桌面与 390 宽共 34 项检查 0 失败；主代理最终全量回归含原 120 + 奖励 38，exit 0（3 skip）。

**当前工程失败处理的事实**：模型调用失败时整个回合不提交，状态与账本都停在回合之前。因此不存在「先持久化 pending 结果再幂等重试」的机制——那是后续演进（阶段 2 起）。目前幂等只保证**同一 `grant_id` 在同旅程多次提交尝试中最多生效一次**，不保证失败回合能保留半成品。

**其它已知局限**：当前事件节点只会完成一次，不承诺同节点重复进入时每实例发奖；无独立命令 ID；无别名表；未配置奖励的故事包与旧存档行为完全不变。

## 8. 阶段 1 验收结果（2026-10-25，全部通过）

| 验收项 | 结果 | 对照测试（`tests/test_rewards.py`） |
|---|---|---|
| 确定性种子：重试/重启/回滚后重做同骰点同奖励，账本带 seed 与 `rules_version` | 通过 | `test_same_seed_same_items_different_seed_differs`、`test_rollback_and_replay_regenerate_identical_rewards`、`test_reward_survives_restart_and_rollback` |
| 严格参数拒绝，零写入 | 通过 | `test_strict_numbers_reject_bool_nan_and_overlaps`、`test_reward_amount_must_fit_the_grant_budget`、`test_whole_batch_rejected_on_late_failure` |
| 固定派生正确、缓存不权威 | 通过 | `test_instance_value_cap`、派生重算相关断言 |
| 奖励原子幂等（重复提交/重试不二次发奖，并发不重复不丢） | 通过 | `test_repeat_action_does_not_pay_twice`、`test_ledger_records_before_after_and_is_idempotent`、`test_cas_conflict_does_not_pay_out` |
| 回滚：回到事件起点后一致，重做可再获 | 通过 | `test_rollback_and_replay_regenerate_identical_rewards` |
| 重启：仅凭会话快照重建一致结果 | 通过 | `test_reward_survives_restart_and_rollback` |
| 公开投影不泄露（隐藏附魔不从数字泄漏，也进不了模型输入） | 通过 | `test_hidden_enchantment_and_abilities_stay_author_only`、`test_hidden_enchantment_does_not_leak_through_numbers`、`test_model_input_has_no_reward_audit`、`test_identified_item_still_hides_hidden_enchantment_from_model` |
| 旧包兼容（旧故事包与旧旅程照常运行、不被改写） | 通过 | `test_no_reward_keys_and_no_state_block`、`test_legacy_save_not_rewritten_by_reads`、`test_journey_query_when_current_package_has_no_rewards` |

**汇总**：专项 38 项全过；浏览器桌面与 390 宽共 34 项检查 0 失败；主代理最终全量回归含原 120 + 奖励 38，exit 0（3 skip）。

## 8.1 接入入口

- 配置：`story.mechanics.rewards`；示例片段 `docs/examples/rewards-demo.story-fragment.json`，接入说明 `docs/examples/rewards-使用说明.md`（示例不会自动启用，也不改动 `StoryPackage/玄陆`）。
- 行动声明：`"rewards": {"success": ["条目ID"], "failure": []}`，或效果 `{"op":"reward","entry":"条目ID或表ID"}`。
- 作者查看：里层 `GET /api/inner/rewards`，返回作者投影、`grants`、`ledger` 与公式说明，并不向玩家暴露。

## 9. 不做什么

- 不训练或微调语言模型。
- 不用 `eval`/`exec` 跑规则或公式。
- 阶段 1 不实现可编程派生公式（算子树/lookup/when/循环检测/缓存）、永久审计表、别名表。
- 不声称支持动态耐久/魔力、磨损/修理/充能、战斗/负重/交易执行器，也不声称知识/关系/通行许可已接入奖励链路。
- 不让模型文本直接写状态，不把不经过校验的新事实入库。
- 不自动升级旧旅程绑定的故事包版本。
- 不声称已具备百万/千万 token 规模验证，不承诺零幻觉。
- 不在本阶段做多用户权限隔离（仍为本机单作者工作台）。
