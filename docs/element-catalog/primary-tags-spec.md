# 主标签与证据等级规范 catalog_overlay_v1

状态：设计口径。用户决定：**每个资料条目只能有一个主标签，其余都是次标签**。例：白菜的主标签是「蔬菜」，次标签有 crop、food、season:winter 等。

## 1. 字段

| 字段 | 取值 | 说明 |
|---|---|---|
| `primary` | `tools/catalog_overlay.py` 的 `PRIMARY` 词表，恰好一个 | 引擎派生为标签 `primary:<值>` |
| `evidence_grade` | `sourced` / `mixed` / `inferred` | 引擎派生为 `evidence:<值>` |
| `related_add` | 资料条目 id 数组（可省略） | 追加到 `related_catalog_ids`，不删已有关联 |

- `primary:` 与 `evidence:` **不许手写在 tags 里**，只能经字段给出（引擎会拒绝）。这样旧 schema 的 14 组（原生 tags 被丢弃）也能拿到主标签。
- 其他所有标签（`kind:`、`part:`、`season:` 等）都是次标签。`kind:` 保留作细分，不再承担“主类”含义。

## 2. 主标签怎么选

按「玩家或作者最先会怎么叫它」选，不按生物分类学：

- 白菜 → `vegetable`；苹果 → `fruit`；小麦 → `grain`；大豆 → `legume`；胡椒 → `spice`；鼠尾草（厨房用） → `culinary_herb`。
- 同一实物兼作药与食物时，按它在**本分组**里的主要角色：flavors 里的桂皮 → `spice`；药材分区里的黄芪 → `medicinal_herb`。
- 家牛 → `livestock`；牛肉 → `meat`；奶酪 → `dairy`；香肠、火腿 → `preserved_food`；熬炼的猪油、牛油 → `fat_oil`。
- 粮仓、水井、水渠、水车磨坊、风车、锻炉 → `facility`（固定设施，不是可携带的工具）。
- 菜品：汤类 → `soup`；面条 → `noodle`；面包 → `bread`；酥点蛋糕 → `pastry`；点心小吃 → `snack`；其余 → `dish`；技法条目 → `cooking_technique`；制度条目 → `institution`。
- 奇幻：种族 → `race`；奇幻兽 → `beast`；精怪 → `spirit`；魔药 → `potion`；丹药 → `elixir_pill`；法宝、神器、傀儡 → `artifact`；灵材、天材地宝、奥术材料 → `magic_material`。
- 词表里实在没有合适项时，在报告里提出，不要硬塞。

### 2.1 非人知性体归 `race`

用户决定（2026-11-04）：**非人但有智慧的生物单开为种族**，主标签取 `race`，思路类似月亮计划（Project Moon）游戏里“非人知性体”的设定：判定看有没有心智，不看长得像不像人。例：西幻的龙算种族，不算动物。

判为 `race` 的条件（满足任意两条即可）：

1. 有语言，或能和人互相理解意图；
2. 能谈判、立约、守约或背约；
3. 有自己的群体、谱系或社会（不只是独一个体）；
4. 本条正文已写明不可当野兽采集、驯养或圈养。

不改为 `race` 的情况：

- 无智的兽、只凭本能的怪物（狮鹫、鸡蛇、巨蟒、狼群）→ 仍是 `beast`。
- 独一无二的个体或征兆（不死鸟、麒麟、凤属）：没有群体，仍是 `beast`；世界设定若给它们群体与语言，可在开局另行改判。
- 木石器物成精、亡灵、附体恶魔这类**不是生物**的存在，保留 `spirit` / `undead_demon`。
- 由人变成的（狼人、吸血鬼、鬼修）本身就是人，按状态保留原主标签。
- 无自主思考的造物（魔偶、傀儡）不算知性体；它们若出现在种族分区，正文须写明“这是劳役造物，不是有心智的族群”。

检索：`primary:race` 列出全部种族（含人类族群与非人知性体）；原有的 `kind:` 次标签保留不动，`primary:race` 且 `kind:` 不是 `race` 的就是从动物、精怪改判过来的非人知性体。改判理由写在叠加文件该条的 `note` 里。

2026-11-04 已按本节改判 9 条：西幻龙、妖精族、侏儒与哥布林、人鱼群体、山怪、狐妖、龙属与蛟类、炉火裔、煤灯下的妖精；魔偶劳役种按“劳役造物”归 `artifact`。

## 3. 证据等级

- `sourced`：主要断言都有 `access=read` 来源支撑。
- `mixed`：有来源，但机制、玩法或社会后果有相当部分是本项目推演。
- `inferred`：基本是设计推演（原创设定、零来源条目、纯游戏规则）。

拿不准就选更低一档。证据等级**不改变** `review_status` / `detail_status`。

## 3.1 科技 / 魔法档位（2026-11-04 补档）

档位定义见 `docs/world-setting.md` §2–3。叠加文件每条加两个键，**两键都必须出现**（值可为 `null`），表示“已经判定过”；引擎把非空值派生为 `tech:<值>` / `magic:<值>` 标签，旧 schema 也生效。

| 字段 | 取值 | 含义 |
|---|---|---|
| `tech_tier` | `classical` / `medieval` / `steam` / `early_modern` / `null` | 该资料条目**最早**能在哪一档科技的世界里出现。`null` = 不受科技约束（自然物、多数食物药材、种族、古已有之的工具与制度） |
| `magic_tier` | `rare` / `common` / `abundant` / `null` | 该资料条目要求世界**至少**达到的魔法档位。`null` = 不需要魔法（现实事物、传说只作民俗记述的条目） |

判定口径：

- 只在确有门槛时才标科技档：火药、印刷、钟表 → `medieval`；蒸汽机、罐头、铁路、工厂、近代餐馆制度 → `steam`；内燃机、电网、无线电、飞机 → `early_modern`。古典时代就有的东西写 `null`（等同 `classical`，不会越档）；已手写为 `classical` 的旧标签保留。
- 美洲作物（马铃薯、玉米、番茄、可可、辣椒）是地理与交流问题，不是科技门槛，写 `null`。
- 魔法档按“若这条在世界里**真实生效**需要多少魔法”判：单个奇幻生灵、隐秘仪式、单件遗物 → `rare`；有学院行会、可买卖的魔药丹药、修士门派 → `common`；魔导基础设施、浮空城、魔力能源 → `abundant`。
- 现实草药、方剂、民俗信仰条目按**记述**收录，写 `null`；若某条正文把超自然效力写成世界事实，才标魔法档。
- `magic:none` 不使用：它等于“不需要魔法”，统一写 `null`。
- 拿不准时科技取更低一档、魔法取更低一档，并在 `note` 写理由。

校验：`python -X utf8 -m tools.catalog_overlay --check --require-tiers`。

## 4. 旁挂文件

`docs/element-catalog/overlays/<group>.json`：

```json
{
  "schema": "catalog_overlay_v1",
  "group": "produce",
  "entries": {
    "produce_cabbage": {"primary": "vegetable", "evidence_grade": "sourced", "note": ""}
  }
}
```

`entries` 必须覆盖该组全部资料条目、不多不少。新建分区可以直接在资料条目里写 `primary` / `evidence_grade`，不用旁挂。

校验：`python -X utf8 -m tools.catalog_overlay --check`；测试：`tests/test_catalog_overlay.py`。
