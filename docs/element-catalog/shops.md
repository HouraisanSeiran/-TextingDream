# 店铺分区（shops 组）

对应 `shops.json`，规范见 `shops-spec.md`。状态：**候选资料**，不是数据库记录。本文件只提供扫读视图；完整字段（details 七节、来源、标签）**以 JSON 为准**。

- 共 37 条，每条 `shop.key` 恰好对应 `tools/game_fields.py` 的 `SOLD_BY` 里一个店铺值（none、farmer、noble_kitchen、street_vendor 不是店铺）。
- 全部 `primary: shop`，`review_status: needs_review`，`detail_status: needs_detail`；不含现实历史物价，不带 `game` 对象。
- 来源 13 条，均为 Britannica 概述页，`access: read`；证据等级见下表。

## 食物与日用

| key | 中文名 | 卖什么（主标签） | 最小聚落 | 证据 | 东方对应 |
|---|---|---|---|---|---|
| `tavern` | 酒馆 | 饮品、酒类、菜肴 | 村（hamlet） | mixed | 酒肆、酒家、酒楼（规模和菜单更偏饭庄）；茶楼另见 tea_house |
| `inn_kitchen` | 客栈厨房 | 菜肴、汤羹、面包 | 村（hamlet） | mixed | 客栈、驿馆、旅舍的灶房 |
| `market` | 集市 | 谷物、蔬菜、水果、牲畜、纤维织物 | 镇（town） | mixed | 集、墟、市、庙会（见 eastern_pilgrimage_festival） |
| `grocer` | 杂货铺 | 谷物、香料、调味品、腌熏保存食品、糖与甜味 | 镇（town） | mixed | 杂货铺、粮油店、南货店、酱园 |
| `greengrocer` | 蔬果店 | 蔬菜、水果、薯芋根茎、食用菌、坚果籽实 | 镇（town） | inferred | 菜行、菜摊、果行、菜市场 |
| `butcher` | 肉铺 | 肉类、禽类、腌熏保存食品、皮革骨角 | 镇（town） | mixed | 肉铺、屠户、肉案 |
| `fishmonger` | 鱼铺 | 水产、腌熏保存食品 | 镇（town） | inferred | 鱼行、鱼摊、咸鱼铺 |
| `baker` | 面包房 | 面包、糕点酥点、小吃点心 | 村（hamlet） | mixed | 烧饼铺、馒头铺、蒸饼铺、点心铺 |
| `confectioner` | 糖果点心铺 | 糖与甜味、糕点酥点、小吃点心 | 镇（town） | inferred | 糕点铺、蜜饯铺、糖坊 |
| `cookshop` | 熟食铺 | 菜肴、小吃点心、汤羹、面食 | 镇（town） | inferred | 熟食铺、卤味铺、小吃店、食肆 |
| `dairy` | 乳品铺 | 乳品、蛋类 | 村（hamlet） | inferred | 乳品铺（奶牛养殖区）、酪坊、奶酥铺 |
| `miller` | 磨坊 | 谷物 | 村（hamlet） | inferred | 磨坊、碾坊、水碓 |
| `brewer` | 酿酒坊 | 酒类、饮品 | 村（hamlet） | inferred | 酒坊、烧坊、酿酒作坊、醪糟铺 |
| `wine_merchant` | 酒商 | 酒类 | 镇（town） | inferred | 酒行、酒庄代理、酒栈 |
| `tea_house` | 茶馆 | 饮品、小吃点心、糕点酥点 | 镇（town） | inferred | 茶馆就是东方本体；西式对应是咖啡馆（coffeehouse）、茶室 |
| `chandler` | 蜡烛杂货铺 | 燃料、油料、工具 | 镇（town） | inferred | 蜡烛铺、油坊、灯烛铺、香烛店 |
| `spice_merchant` | 香料商 | 香料、香草、调味品、糖与甜味、药材（植物） | 城（city） | inferred | 香料行、香药铺、药材行 |

## 药与采集

| key | 中文名 | 卖什么（主标签） | 最小聚落 | 证据 | 东方对应 |
|---|---|---|---|---|---|
| `apothecary` | 药铺 | 药材（植物）、药材（矿物）、药材（动物）、方剂、香料 | 镇（town） | mixed | 药铺、药房、药堂、医馆附设药房 |
| `herbalist` | 草药铺 | 药材（植物）、植物（非食用为主）、香草 | 村（hamlet） | inferred | 草药铺、郎中摊、采药人、药农 |
| `alchemist` | 炼金工坊 | 魔药、丹药、药材（矿物）、玻璃陶瓷 | 城（city） | inferred | 丹房、炼丹炉、丹铺（见 eastern_alchemy、eastern_pill_elixir） |

## 手工与装备

| key | 中文名 | 卖什么（主标签） | 最小聚落 | 证据 | 东方对应 |
|---|---|---|---|---|---|
| `blacksmith` | 铁匠铺 | 工具、金属、兵器 | 村（hamlet） | mixed | 铁匠铺、打铁铺、铁炉；东方也有专门的兵器坊（见 weaponsmith） |
| `armorer` | 盔甲铺 | 甲胄、金属、皮革骨角 | 镇（town） | mixed | 甲铺、铠甲坊；官营军器监下的甲作坊 |
| `weaponsmith` | 兵器铺 | 兵器、金属、工具 | 镇（town） | mixed | 兵器铺、刀剑铺；官营军器监与兵工厂 |
| `bowyer` | 弓匠铺 | 兵器、木材 | 镇（town） | inferred | 弓箭铺、弓坊、箭作；官营军器监的弓箭作 |
| `carpenter` | 木匠铺 | 木材、建材、工具 | 村（hamlet） | mixed | 木匠铺、木作、细木作；营造匠人（营造大作另见建筑行业） |
| `cooper` | 箍桶铺 | 木材、工具 | 镇（town） | inferred | 桶匠、木桶铺、盆桶作；酒坊自带的桶作 |
| `tanner` | 制革坊 | 皮革骨角 | 镇（town） | inferred | 制革坊、熟皮坊、皮匠作；硝皮 |
| `saddler` | 鞍具铺 | 皮革骨角、工具 | 镇（town） | inferred | 鞍具铺、马具铺、皮货作 |
| `tailor` | 裁缝铺 | 纤维织物 | 镇（town） | inferred | 裁缝铺、成衣铺、绣坊；东方另有绣庄和绸缎庄（见 draper） |
| `draper` | 布庄 | 纤维织物 | 镇（town） | inferred | 布庄、绸缎庄、布行、呢绒店 |
| `cobbler` | 鞋铺 | 皮革骨角 | 村（hamlet） | inferred | 鞋铺、鞋匠摊、补鞋摊；布鞋与草鞋作坊另有传统 |
| `potter` | 陶窑 | 玻璃陶瓷 | 村（hamlet） | mixed | 陶窑、窑坊、瓷窑；景德镇一类名窑已是产业 |
| `jeweler` | 金银匠铺 | 金属、石料与土 | 城（city） | mixed | 金银铺、银楼、首饰楼、珠宝店 |

## 金融、书籍、车马

| key | 中文名 | 卖什么（主标签） | 最小聚落 | 证据 | 东方对应 |
|---|---|---|---|---|---|
| `moneychanger` | 兑换铺 | 经济与贸易 | 城（city） | inferred | 钱庄、钱铺、票号；东方更强调汇兑和存放（见 society_deposit_house） |
| `pawnshop` | 当铺 | 经济与贸易 | 镇（town） | mixed | 当铺、典当行、质库 |
| `bookseller` | 书铺 | 文学与叙事 | 镇（town） | mixed | 书肆、书坊、书铺；刻书坊（见 reality_human_printing_reproduction） |
| `stable` | 驿马厩 | 牲畜、车船 | 村（hamlet） | mixed | 驿站、车马店、马厩；官营驿传（见 society_postal_relay） |

## 已知不足

- 来源集中在 Britannica 概述，抄本时代书铺、钱庄、茶馆、驿站等的细节多为推演，证据等级已降到 inferred 或 mixed。
- 书铺、金匠、陶三条只读到摘要或导语（页面付费墙或摘要段），不能当作完整依据。
- 最小聚落是本项目设计口径（对应 civ-atlas 城镇四级），不是历史统计。
