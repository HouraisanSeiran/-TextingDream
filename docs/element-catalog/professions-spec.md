# 职业分区规范 professions

状态：设计口径（2026-11-05）。用户要求补充职业元素。

## 1. 文件

- `docs/element-catalog/professions.json`（group `professions`）：现实与历史职业，西方与东方、中世纪到近现代。
- `docs/element-catalog/professions-fantasy.json`（group `professions_fantasy`）：奇幻、仙侠、蒸汽奇幻职业。

新 schema（每条带 tags），七节 details、`source_ids`、`review_status: needs_review`、`detail_status: needs_detail`，与其他分区相同。每条直接写 `primary: "profession"`、`evidence_grade`、`tech_tier`、`magic_tier`（两键都要出现，值可为 null），不用叠加文件。

## 2. 每条的 `profession` 对象

```json
"profession": {
  "shop_key": "blacksmith",
  "wage": {"min": 8, "max": 16, "per": "日"},
  "class": "artisan",
  "settlement_min": "hamlet",
  "guild": true
}
```

| 字段 | 取值 |
|---|---|
| `shop_key` | `tools/game_fields.py` 的 `SOLD_BY` 里的店铺键（`none`、`farmer`、`noble_kitchen`、`street_vendor` 除外）；不开店的职业写 `null` |
| `wage` | 整数便士，`per` 取 `日` / `周` / `年` / `件`；拿不到固定收入的（乞丐、修士）写 `null`。游戏行情，不是史实 |
| `class` | `laborer` 劳力 / `artisan` 匠人 / `merchant` 商人 / `professional` 读书或专门职业 / `clergy` 神职 / `military` 军人 / `official` 官吏 / `noble` 贵族 / `outcast` 贱业或边缘 |
| `settlement_min` | `hamlet` / `town` / `city` / `capital`，多大的聚落养得起 |
| `guild` | 是否通常有行会、门派或执照管辖 |

工资锚点（不得冲突）：半日短工 6–12 便士；麦酒一杯 2 便士；12 便士 = 1 先令，240 便士 = 1 镑。熟练匠人日薪通常高于短工，学徒低于短工。

标签：`kind:profession`、`tradition:western|eastern`（东西通用可两个）、`class:<值>`、`settlement:<值>`，有店铺时加 `shop:<shop_key>`。`tech:` / `magic:` / `primary:` / `evidence:` / `genre:` / `category:` 不手写，由字段派生。

## 3. 边界

- 写职业的日常、技能、学徒与晋升、典型顾客与纠纷、社会地位、违法边界，不写现实可操作的危险技术细节（制毒、开锁、伪造）。
- 与店铺分区（`shops.json`）、已有 6 条职业主标签条目不重复立条；相关的用 `related_ids` / `related_catalog_ids` 指向。
- 来源规则同其他分区：读过正文才标 `access=read`，未读的零引用。
