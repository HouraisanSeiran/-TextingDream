# 词条分区规范 fantasy-affixes（affix_fields_v1）

状态：设计口径（2026-11-11）。用户要求：为数据库补充西幻与游戏里常见的**词条属性元素**
（如「强壮」「邪神眷顾」），作为人物或物品的词条补充，带属性点相关影响或其他影响。

本分区是**候选素材**，不是已生效的规则：库里有 ≠ 世界里有 ≠ 引擎会按它改数。

## 1. 文件与命名空间

- 源文件：`docs/element-catalog/fantasy-affixes.json`，`group` = `fantasy-affixes`，命名空间同名。
- 新 schema（每条带 `tags`）、七节 `details`、`source_ids`、`review_status: needs_review`、
  `detail_status: needs_detail`，与其他新分区一致。
- 构库名单是**独立显式名单** `AFFIX_GROUPS`，只有显式传 `--with-affixes` 才进库；
  不靠通配，也不被 `--with-traits` 等旧开关隐含。

## 2. 与既有分区的分工（必读）

| 既有分区 | 它管什么 | 与本分区的关系 |
|---|---|---|
| `character-attributes`（六项属性） | 天赋/力量/敏捷/智慧/社交/韧性的定义与量程 0–100 | 本分区只**引用**这六个 ID 做加减，不新增第七项能力 |
| `character-traits`（角色特质模板） | 可观察的行为倾向，**明确不产出倾向分值、不承担能力数值** | 本分区相反：它是**数值词条**，不与行为特质合并，也不进 `personality` |
| `mechanics.rewards.enchantments`（附魔） | 物品模板上的伤害/价值加成，由奖励配置消费 | 物品词条只给**候选数值口径**，不改奖励配置；作者要生效需自己在故事包里写进附魔或模板 |

因此：**不得**把这些词条写进 `mechanics.traits`、`personality`，也不得让引擎假装已经应用它们。

## 3. 每条的 `affix` 对象

```json
"affix": {
  "schema": "affix_fields_v1",
  "applies_to": ["character"],
  "polarity": "boon",
  "grade": "common",
  "stacking": "unique",
  "visibility": "public",
  "attribute_mods": {"strength": 8},
  "hp_mod": 0,
  "narrative": ["……"]
}
```

| 字段 | 取值 | 说明 |
|---|---|---|
| `schema` | 必须是 `affix_fields_v1` | 版本口径 |
| `applies_to` | `character` / `item`，1–2 项 | 词条能挂在哪类东西上 |
| `polarity` | `boon` 增益 / `bane` 减益 / `mixed` 有得有失 | 必须与数值正负号自洽（见 §4） |
| `grade` | `common` / `uncommon` / `rare` / `legendary` | 稀有度，同时限制数值幅度（见 §5） |
| `stacking` | `unique` 同类只取一次 / `stack` 可叠 / `exclusive` 组内互斥 | `exclusive` 时**必须**写 `exclusive_group` |
| `exclusive_group` | 小写 ID；`stacking=exclusive` 时必填，其余情况不写 | 例：`affix.curse` |
| `visibility` | `public` 旁人可察觉 / `hidden` 只有作者视图可见 | 与 `character-traits` 同一套可见性口径 |
| `attribute_mods` | 六项属性 ID → 整数，**可省略** | 幅度上限随 `grade` 变化；值为 0 一律拒绝（要么写、要么不写） |
| `hp_mod` | 整数，可省略 | 直接改最大血量；血量公式仍是 `round(50 + 2×韧性)`，本字段是**公式外加减** |
| `item_mods` | `damage` / `value_percent` / `weight_percent` / `durability_percent` 的整数，可省略 | 只有 `applies_to` 含 `item` 才能写；量程与 `app/rewards.py` 的材质、附魔同口径，作者可原样抄进去 |
| `narrative` | 1–3 条短句，可省略 | 不落地成数值的影响（社会反应、气味、梦、记号等）；**引擎不解释它** |
| `note` | 最多 120 字 | 给作者的口径说明（例如「这条为什么是 rare」） |

`attribute_mods` 的键只能是 `talent` / `strength` / `agility` / `wisdom` / `social` / `resilience`。
写成 `charisma`、`intelligence` 等其他名字一律拒绝——那会造出平行属性体系。

## 4. 正负号自洽（防止「增益词条扣属性」这类笔误）

判定前先把每项数值折算成「对持有者是好还是坏」：

- 属性加值、`hp_mod`、`item_mods.damage`：正数有利、负数不利。
- `durability_percent` / `value_percent`：高于 100 有利。
- `weight_percent`：**低于 100 有利**（更轻）。

然后：

- `boon`：不允许出现不利项，且至少一个有利项。
- `bane`：不允许出现有利项，且至少一个不利项。
- `mixed`：允许两边都有（典型：高伤害但沉重、锋利但脆）。
- 数值全为空时只允许 `mixed`，且 `narrative` 必须有内容（否则这条词条什么都没说）。

百分比方向是**口径约定**：这件东西轻了、贵了、结实了算好事。如果某个物品世界里「越重越有牌面」
或「越旧越值钱」，那是世界设定，不是机器能推的，作者应写进 `narrative`，不要指望校验器理解。

## 5. 幅度上限（按 grade）

| grade | `attribute_mods` 单轴 | 单轴合计绝对值 | `hp_mod` |
|---|---|---|---|
| `common` | ≤ 6 | ≤ 10 | ≤ 10 |
| `uncommon` | ≤ 10 | ≤ 18 | ≤ 20 |
| `rare` | ≤ 15 | ≤ 26 | ≤ 35 |
| `legendary` | ≤ 20 | ≤ 34 | ≤ 50 |

这些上限是**设计口径**，不是平衡实测结果。它们的唯一用途是拦住明显跑偏的值
（例如 0–100 量程上写 +60 力量）。

**不要重复计算血量**：`resilience` 已经通过 `round(50 + 2×韧性)` 影响血量上限，所以
同一张词条不要既写 `resilience` 又写 `hp_mod` 去表达「更耐打」。二选一：

- 主题是「扛得住损耗」→ 只写 `resilience`（血量随公式走）；
- 主题就是「血更厚」→ 只写 `hp_mod`，不动 `resilience`。

作者若要两层都加，必须在 `note` 里写明这是刻意叠加，并接受它比同档词条强一档。

## 6. 标签（必须与 `affix` 对象一致，一个不多一个不少）

`affix:<名字>` 前缀由 `tools/affix_fields.py` 派生，**源文件里必须原样写全**，
构库时逐个比对；不一致直接报错，不静默补：

- `affix:character` / `affix:item`：每个 `applies_to` 一项
- `affix:boon` / `affix:bane` / `affix:mixed`：来自 `polarity`
- `affix:grade:<值>`：来自 `grade`
- `affix:hidden`：`visibility=hidden` 时出现（`public` 时不出标签）
- `affix:attr:<属性ID>`：`attribute_mods` 的每个键一项（正负都算，符号看数值）
- `affix:hp`：出现 `hp_mod` 时一项

其余检索标签手写：`kind:affix`、`tradition:western`、`domain:body|mind|social|fate|craft`（见 §8）。

## 7. 主标签与证据等级

新分区元素**自带** `primary: "affix"`、`evidence_grade: "inferred"`、`tech_tier`、`magic_tier`
（两键都出现，值可为 `null`），不写叠加文件。`inferred` 的理由：本分区全部是本项目
玩法设计文字，没有外部来源可引。

## 7.1 命名风格（词条显示名）

以已认可的 27 条人物词条为准，新词条的 `name` 只落在两种形态里：

- **2 字**：状态或性质词——强壮、迅捷、锐目、铁胃、巧舌、威仪、迟钝、笨拙、虚弱、惊惶、失声、目盲、惜身、识途。
- **4 字**：四字复合词、成语或固定搭配——体魄坚韧、过目成诵、临危不乱、见多识广、声名在外、人缘不佳、失约之人、神恩眷顾、邪神眷顾、诅咒烙印、力大无巧、天命所钟、灵力透支。

既有两条不在 2/4 字里，属**已认可的例外**，新条目不要再效仿：**铁意志**（3 字）、**被标记之人**（5 字）。

禁止：

- **口语短语**（「听得进」「力气大」「会说话」）；
- **生造词**（「灵息」「引动」「稳手」这类不是现成词的组合）；
- 把数值写进名字（「加力量」「力量+6」）；
- 用对持有者的评价代替词条本身。

旧名只能进 `aliases`，不要靠改名清理历史。

## 8. `domain` 分类（只落在标签上，不新增字段）

| 值 | 含义 |
|---|---|
| `domain:body` | 体格、力气、耐受、伤势 |
| `domain:mind` | 感知、专注、学识、意志 |
| `domain:social` | 威仪、口舌、名声、关系 |
| `domain:fate` | 神恩、诅咒、血脉、气运 |
| `domain:craft` | 器物本身的做工与性情 |

## 9. 来源

`sources` 只登记**本项目自己的文档与实现文件**（`url` 写仓库内相对路径）：
`docs/playable-demo-design.md`、`docs/playable-demo/character-attributes.md`、
`app/attributes.py`、`app/rewards.py`、`docs/check-system-v2.md`、本文件。
`rights_note` 写明「本项目原创设计文字」。**不伪造外部文献、不写论文与量表**。

## 10. 边界（明确不做）

- 不由引擎自动应用：这些数值不改角色属性、不改奖励配置、不进检定公式，
  除非作者把等价内容写进故事包（角色包的 `attributes`、`mechanics.rewards` 的材质/附魔）。
- 不与 `character-traits`（行为特质）合并，也不做人格测量。
- 不设「词条等级/成长」：本条只描述一个静态词条，不描述升级曲线。
- 不承诺平衡：数值是设计起点，不是实测结论。
