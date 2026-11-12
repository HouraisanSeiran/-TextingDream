# 公制与十进制货币：移交清单

> **历史移交（2026-11-08 整理）**：这是当时还没改完的清扫清单。现行约定以 [units.md](units.md) 为准，哪些界面仍留着便士见 [现状.md](现状.md)。

约定见 `docs/units.md`。下面是写这份清单时本分支没有改、留给其他负责人的地方。
本分支已改的：`app/economy.py`（价格锚点、币制说明、提示词里的公制规矩）、`app/trade.py`（默认货币名「铜币」）、`app/rewards.py`（重量注明为克）、`app/static/world-systems.js`（重量按克 / 千克显示）。

## 1. 元素库（负责元素库的 AI）

| 位置 | 现状（2026-11-05 扫描） | 要做的事 |
|---|---|---|
| `docs/element-catalog/**/*.json`、`docs/human-encyclopedia/*.json` 的 `game.price.per` | 「一磅」约 60 处 | 改为「一千克」或「500 克」，并把 `min` / `max` 按新计价单位重算（1 磅 ≈ 0.45 千克，即「一千克」价格 ≈ 原价 × 2.2，取整） |
| 同上，条目正文 | 磅 89、盎司 30、英寸 14、英尺 6、加仑 4、品脱 3、英里 3、夸脱 2、蒲式耳 1 处 | 换成公制（1 盎司 ≈ 28 克，1 英寸 ≈ 2.5 厘米，1 英尺 ≈ 30 厘米，1 英里 ≈ 1.6 公里，1 加仑 ≈ 4.5 升，1 品脱 ≈ 0.57 升，1 蒲式耳 ≈ 36 升）。引用原文的句子可保留原单位，但要括注公制 |
| 同上，正文里的便士、先令、镑 | 未统计 | 改写为铜币：1 先令 = 12 铜币，1 镑 = 240 铜币 |
| `game.price.tier` 的 farthing / penny / groat / shilling / pound | 全库 | 按 `docs/units.md` 的新档位表改为 copper_low / copper / silver / gold |
| `docs/element-catalog/game-fields-spec.md` 第 32–40 行 | 币制、计价单位举例「一磅」、旧档位表 | 按 `docs/units.md` 重写 |
| `tools/game_fields.py` 的 `PRICE_TIERS`、`tools/price_audit.py` | 旧档位名 | 换新档位名，审计规则同步 |
| `app/ai_drafts.py` 第 124–125、189、200 行 | 生成元素时的提示词与默认值用便士、旧档位 | 改为铜币、新档位、公制计价单位 |

改完需要重新构库导入（走 `tools/encyclopedia_build.build`，不要用 `import_file`，以免丢 overlay 标签），并跑 `tests/test_encyclopedia_game_fields.py`、`tests/test_price_audit.py`。

## 2. 故事包与短场景（负责可玩场景的 AI）

| 位置 | 现状 | 要做的事 |
|---|---|---|
| `StoryPackage/*/story.json` 等 | 便士相关 94 处 / 12 个文件；货币配置 `"unit": "便士"` | 货币名改为「铜币」，数值不变；正文里的先令、镑按 12 / 240 换算 |
| `docs/playable-scenes/` | 便士相关 192 处 / 7 个文件 | 同上 |
| `docs/examples/economy-demo.story-fragment.json` | 1 处 | 同上 |
| 故事包里的物品重量 | 目前没有故事包填写 `weight` / `base_weight` | 以后一律按整数克填写 |

## 3. 前端（负责 `playable-demo.js` 的 AI）

| 位置 | 现状 | 要做的事 |
|---|---|---|
| `app/static/playable-demo.js` 第 565 行 | 旅费按「镑 / 先令 / 便士」拆分显示（÷240、÷12） | 改为十进制：金币 = ÷100，银币 = ÷10 余数，铜币 = ÷1 余数；或直接显示「共 N 铜币」 |
| `app/static/dice-demo.js` 第 7、12 行 | 演示文案「多塞两便士」 | 改为「多塞两枚铜币」 |

## 4. 测试（随上面各项一起改）

| 文件 | 现状 |
|---|---|
| `tests/test_checks_v2.py` 第 84、97 行 | 测试数据里货币叫「便士」 |
| `tests/test_trade.py` 第 42 行 | 同上 |
| `tests/test_tavern_element_pilot.py` 第 134 行 | 断言标签里含「%d便士」，场景文本改后要同步 |
| `tests/test_npc_cards.py` 第 23 行 | 「七十镑」是剧情文本，可改为「一万六千八百铜币」或改写剧情 |
