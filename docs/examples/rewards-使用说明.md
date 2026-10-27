# 本地奖励使用说明

这是**示例**，不会自动启用，也不会改动 `StoryPackage/玄陆`。你把它合并进自己的故事包后，新旅程才会带上金币、物品实例与能力。

## 一、三步接入

1. 打开里层创作页最下面的「故事包与角色包」，点 `保存新版本` 前，把 `docs/examples/rewards-demo.story-fragment.json` 里 `mechanics.rewards` 整块粘进 `story` 的 `mechanics`（保留已有的 `attributes`、`local`、`calendar`）。
2. 给某个事件的行动加奖励声明：`"rewards": {"success": ["coin_small"], "failure": []}`。分支名只有 `success` 与 `failure` 两个，条目 ID 必须已在 `rewards.rewards` 里定义。
3. 保存新版本 → 新建旅程。旧旅程继续用它自己的旧版本，不会中途多出金币。

未配置 `mechanics.rewards` 时，引擎行为与旧版完全一致：不会出现奖励字段，写了奖励声明会被校验拒绝（而不是悄悄不生效）。

## 二、配置各部分

| 字段 | 说明 |
|---|---|
| `currencies` | 钱包币种。`maximum` 是持有上限，超出则整批奖励被拒。 |
| `materials` | `damage_bonus`、`value_percent`、`weight_percent` 是百分比因子；`shapes` 为空表示不限形制。 |
| `shapes` | 基础伤害/价值/重量/耐久与魔力容量上限。 |
| `qualities` | 价值与耐久百分比，`enchant_budget` 是这件物品能吃下的附魔等级总和。 |
| `enchantments` | `group` 相同的互斥（同组只能出现一次）；`hidden: true` 表示即使鉴定也不对玩家披露。 |
| `abilities` | `requires` 是前置能力，`flags` 是必须已在旅程里成立的标记，`public: false` 表示不向玩家披露。 |
| `templates` | 材质+形制+品质的组合，可选覆盖 `weight`/`durability`/`mana_capacity`，可带附魔清单。物品模板与实例是分开的：模板是配置，实例在旅程快照里。 |
| `tables` | 加权表，`entries` 里的权重为正整数。行动里直接写表 ID（如 `dock_loot`），引擎按权重抽**恰好一条**；同一条来源动作永远抽到同一条。 |
| `rewards` | 奖励条目：`currency`（`amount_min`/`amount_max`）、`item`（`templates`、`identified`）、`ability`（`ability`）。与类型无关的字段会被拒绝，不会静默忽略。 |
| `accounts` | 作者声明的资金账户（如商家的钱袋），**仅作者可见**，不进玩家钱包投影。 |
| `payer` | 可选，仅货币奖励用。引用一个 `accounts` 里的账户，且币种必须一致；在同一批里扣款，余额不足则整批拒绝。不填就是引擎侧发放，**不表示某个 NPC 已经付过钱**。 |
| `max_grants_per_event` | 本次事件累计最多生效几条奖励（不是每轮清零）。 |
| `max_value_per_grant` | 单次奖励的硬预算（同一单位：物品价值或货币数量）。配置时与运行时都会校验。 |
| `max_items` | 持有物品实例数量上限。 |

数值全部是严格整数，带上下界。布尔、NaN、小数、字符串数字都会被拒绝，没有公式求值器。

## 三、派生规则（写死在代码里）

```
weight        = template.weight       或  shape.base_weight * material.weight_percent // 100
durability    = template.durability   或  shape.base_durability * quality.durability_percent // 100
damage        = shape.base_damage + material.damage_bonus + Σ(公开附魔.damage_per_level × level)
value         = (shape.base_value * quality.value_percent // 100) * material.value_percent // 100
                + Σ(公开附魔.partial_value × value_percent_per_level × level // 100)
mana_capacity = template.mana_capacity 或 shape.mana_capacity
```

**隐藏附魔（`hidden: true`）不参与玩家可见的伤害与价值计算**，所以玩家无法从数字反推它的存在；作者视图里才会算上。耐久与魔力容量在本版是静态数值，没有损耗、修理或充能。

实例里存的 `stats_cache` 只是审计副本，标了 `authoritative: false`；每次读取都按上表重算，改了缓存也不会改变玩家看到的数字。

## 四、确定性

一次奖励的随机流种子是：

```
sha256(旅程 seed : 来源动作（如 departure:pack） : 奖励条目 ID)
```

不读时钟、不用 Python 内置 hash。所以：

- 回滚到事件起点后重做同一动作，得到**完全相同**的金额、物品与附魔等级。
- 同一条来源动作不会重复发放（grant ID 已存在就跳过）；重试、事件结束后再调用也不会二次发放。
- 换一个旅程 seed，生成结果不同。

## 五、能看到什么

- 玩家面板「我的属性与当地环境」里多一段「钱货 / 随身物品 / 已掌握」。未配置奖励时不显示这一段。
- 玩家能看到的物品信息是公开投影：`identified: false` 的物品只有标签与重量，不给伤害、价值、耐久、材质、品质、附魔，也不给模板名。
- 隐藏附魔即使已鉴定也不会出现在玩家投影与事件摘要里，也不会进入玩家看到的伤害/价值；`public: false` 的能力同理（连「多了新本事」都不写）。
- 作者看全部：`GET /api/inner/rewards` 给配置与派生规则，加 `?session=<旅程ID>` 再给完整实例、隐藏附魔、付款账户余额与 grants/ledger 账本。账本里带 `account`（账户、币种、扣款前后），作者可追溯某笔钱是哪个账户出的。这个接口只读。
- 公开投影里物品的 `damage`/`value` 标为 `visible_estimate`：**只含可见部分**，不是最终裁定值（真正结算用作者侧的完整数值）。本版没有战斗、负重或交易执行器，这些数字只供叙述参考。

## 六、本版边界

- 没有长期记忆、embedding、跨分支永久审计与别名表；账本只覆盖配置奖励，不虚报血量等旧 effect。
- 没有 NPC 资金、商店库存、价格浮动或世界稀缺模型；`payer` 只是同批扣一个配置内账户。
- 不改动现有属性检定公式；奖励输入是引擎已裁定的结果，自由输入与模型 JSON 都不会触发奖励。
- 物品的重量/价值/伤害目前只用于展示与上限校验，尚未接入战斗、负重与交易。
