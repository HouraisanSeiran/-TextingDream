# 店铺分区规范 shops

状态：设计口径。用户决定：铁匠铺、盔甲铺等各类店铺作为独立分类进库，并加上关联标签。

## 1. 文件

`docs/element-catalog/shops.json`，`group: "shops"`，新 schema（每条带 tags），七节 details、`source_ids`、`review_status: needs_review`、`detail_status: needs_detail` 与其他分区相同。

## 2. 每条店铺的额外字段

```json
{
  "id": "shop_blacksmith",
  "name": "铁匠铺",
  "primary": "shop",
  "evidence_grade": "mixed",
  "shop": {
    "key": "blacksmith",
    "sells": ["tool", "metal", "weapon"],
    "services": ["修补农具", "钉马掌"],
    "settlement_min": "hamlet",
    "staff": ["铁匠", "学徒"]
  },
  "tags": ["kind:shop", "tradition:western", "shop:blacksmith", "sells:tool", "sells:metal",
           "sells:weapon", "settlement:hamlet", "trade:smith"],
  "related_catalog_ids": ["materials_iron", "tools_hammer"]
}
```

- `shop.key` 必须是 `tools/game_fields.py` 的 `SOLD_BY` 词表之一（`none`、`farmer`、`noble_kitchen`、`street_vendor` 除外，它们不是店铺），每个 key 恰好一条店铺。这样元素的 `game.sold_by` 就能直接连到店铺。
- `shop.sells` 取 `primary-tags-spec.md` 的主标签词表，表示这家店主要卖哪几类东西（1–5 个）。
- `settlement_min`：`hamlet` 村 / `town` 镇 / `city` 城 / `capital` 都，对应 civ-atlas 城镇四级，表示多大的聚落才养得起这家店。
- 标签：`shop:<key>`、每个 `sells:<主标签>`、`settlement:<级>` 必须与 `shop` 对象一致。
- 东西方差异大的店铺（茶馆 vs 咖啡馆、钱庄 vs 兑换商）用正文与 variants 说明，不拆成两个 key。

## 3. 边界

- 写店铺的经营方式、行会与执照、学徒制、典型顾客与纠纷，不写现实历史物价。
- 来源规则同其他分区：实际读过正文才标 `access=read`，未读的零引用。
