# 经济系统：中间档的商人与集市

> **规则规格（2026-11-08 整理）**：结算规则仍以本文和代码为准。展示货币以 [units.md](units.md) 的整数铜币为准；正文里的便士是遗留示例。接入范围见 [现状.md](现状.md)。

范围：比「只给提示词一份规矩」多一层，但不做完整经济模拟。引擎负责价格和结算，模型只负责演。
实现见 `app/economy.py`（规则与价格）、`app/trade.py`（结算），测试见 `tests/test_economy.py`、`tests/test_trade.py`。
示例见 `docs/examples/economy-demo.story-fragment.json` 与 `docs/examples/economy-使用说明.md`。

## 一、三种经济形态

作者可在 `mechanics.economy.regime` 指定；没指定时按世界设定的科技档位推断（古典、中世纪 → 封建；文艺复兴 → 早期资本主义；蒸汽、近现代 → 工业资本主义）。

| | 封建 `feudal` | 早期资本主义 `early_capitalism` | 工业资本主义 `market` |
|---|---|---|---|
| 商人卖价（基准价） | 130% | 120% | 115% |
| 收购价 | 50% | 55% | 60% |
| 讨价还价最低能压到 | 105% | 102% | 100% |
| 外地货倍率 | 200% | 150% | 125% |
| 以物易物 | 常见 | 常见 | 只在乡下或困境 |
| 营业 | 默认只在集市日 | 天天 | 天天 |
| 货币 | 足值金属铸币 | 金银币，大额用汇票 | 纸币为主 |

`quote(基准价, 形态, 外地货)` 保证 开价 ≥ 底价 > 收购价（高买低卖）。典型特征与价格锚点（便士口径，沿用 `docs/element-catalog/game-fields-spec.md`）进入提示词。

## 二、配置

在 `story.mechanics.economy` 下，全部可省。声明商人需要同时声明 `mechanics.rewards`（货币与商人付款账户）。

```json
"economy": {
  "regime": "feudal",
  "currency": "pence",
  "note": "盐由领主专卖",
  "market_day": {"every_days": 7, "offset": 0},
  "polities": {"home": {"customs": 20}, "far": {"customs": 0}},
  "places": {"market": {"polity": "home", "produces": ["wool"], "lacks": ["salt"], "town_location": ""}},
  "season_pct": {"grain": {"winter": 110}},
  "merchants": [{
    "id": "smith", "name": "老铁匠", "location": "market", "npc": "smith",
    "account": "smith_purse", "haggle_difficulty": 0.3,
    "sells": [{"id": "grain", "name": "干麦", "base": 12, "unit": "袋", "resource": "grain",
               "season_class": "grain", "stock": 5}],
    "buys":  [{"id": "wool", "name": "羊毛", "base": 20, "unit": "捆"}]
  }]
}
```

商品字段：`base` 基准价（整数便士）；`item` 指向故事包唯一物品（进背包，否则是可数货物，进货物袋）；`resource` 对齐城镇资源，用于出产/缺货；`season_class` 季节类别；`origin: imported` + `origin_polity` 外国货；`stock` 每天现货；`always` 封建经济里不受集市日限制。
商人字段：`schedule`（`regime`/`market`/`daily`）、`barter`、`haggle`、`haggle_difficulty`（0–1）。
上限：12 个商人，每人每侧 24 种商品。

## 三、价格修正顺序

每一步都是整数运算 `价格 × 百分比 // 100`，无随机：

1. 基准价
2. 本地出产 85% / 本地缺货 125%
3. 关税：外国货按 `polities[来源].customs` 加价
4. 季节：内置 `grain`（粮）、`fuel`（燃料）、`produce`（果蔬）三类，`season_pct` 可增补或覆盖
5. 形态报价：外地货倍率，再算出开价 / 底价 / 收购价

集市日：`(第几天 − 1 − offset) % every_days == 0`。季节：按 `mechanics.calendar.start_day_of_year`（默认 80）和游戏天数算年内日序。

出产与缺货有两个来源：`places` 手填，或自动读取已采用到该地点的城镇快照（产业链产出和出口贸易品为出产，进口贸易品和主粮缺口为缺货）。

## 四、动作与流程

动作 id：`trade:buy|sell|haggle:<商人>:<商品>[:<数量>]`，`trade:barter:<商人>:<要的>:<付出的>`。

流程与其他本地行动一致：入口取预览（`GET /sessions/{id}/confirm/{id}`）→ 玩家确认 → `POST /chat` 带 confirm → `trade.settle` 在候选副本上结算 → 成功后一次性保存。任何一步失败都在写入前抛错，不留半截。模型说「你买到了」不改变状态。

状态：`session['trade'] = {version, bag, sold, bargain, haggles, log}`，只在第一次成交时创建。钱走 `session['rewards']`：玩家钱包与商人账户。商人收购从他的账户付钱，余额不足就收不了。商人账户玩家不可见，`surface` 里不含底价。

## 五、讨价还价

调用 `app/checks.py` 的 `plan` / `resolve`（纯函数，未改 checks.py）。需要故事包开启 checks v2；未开启时买、卖、易货照常，只是没有讨价还价入口。种子为 `seed:haggle:商人:商品:n`，回滚后同一步结果不变。

| 判定档 | 拿到「开价 → 底价」差额的比例 |
|---|---|
| 大成功 critical | 100%（压到底价） |
| 成功 success | 50% |
| 成功但有代价 partial | 25% |
| 失败 / 失败有代价 | 不成交，当天不再谈价，仍可按开价买 |
| 大失败 disaster | 不成交，当天商人不再卖这件货给你 |

## 六、刻意不做

通胀、借贷与利息、汇率、全世界价格联动、商人之间的资金流转、贸易路线模拟。

## 七、限制

- 城镇数据只对已采用到精确 `location_id` 的城镇库条目有效；集市是城里子地点时用 `places.<id>.town_location` 指过去。
- civ-atlas 探索包的 `city_N` 没有对应的地点映射，需要在 `places` 手填出产与缺货。
- 没有配置 `merchants` 时，提示词只有形态规矩，与旧版一致，不写任何 session 键。
