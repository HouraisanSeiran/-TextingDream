# 中餐（中国菜）候选资料（cuisine-chinese 组）

对应 `cuisine-chinese.json`。状态：**候选资料**，不是数据库记录，也不是任何故事包已采纳的正典。本文件只提供扫读视图、呼应清单与已知不足；完整字段（summary / details 七节 / source_ids / game 等）**以 JSON 为准**。

- 顶层：`schema_version: 1`、`status: candidate`、`group: cuisine-chinese`、`genres: ["real_world"]`，条目 ID 前缀 `cuisine_cn_`。
- 共 **33 项**元素，全部 `category: item`；全部 `review_status: needs_review`、`detail_status: needs_detail`。
- 来源 **57 条**：`access: read` **46 条**、`unavailable` **11 条**（失败如实登记，**零引用**，未出现在任何元素的 `source_ids` 中）。
- 每条含 `details` 七节（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty），全部为非空字符串；每条自带 `game` 对象与对应 `price:` / `terrain:` / `season:` / `sold_by:` 标签（无旁挂文件）。
- **不做可执行食谱**：只写工序顺序与原理，不给克数配比、精确温度与时长。

## 一、这个组在收集什么

服务小说与游戏的世界构建（酒馆、酒楼、节庆、商路、阶层）。取舍标准：

1. 只收**成品菜、点心、小吃与年节食**，不收食材物种；食材在 staples / produce / flavors / animal-foods / food-supplement / materials / tools 各组已有，本组只写菜如何依赖它们，并用 `related_catalog_ids` 指向。
2. 八大菜系覆盖：鲁、川、粤、苏、浙、闽、湘、徽各至少 2 道（徽菜第二条证据很薄，见第七节）；加北方面点与街头小吃、粤式点心、年节食。
3. **宁缺勿凑**：没有读到正文的菜不立条。未立条的候选：糖醋鲤鱼（鲁，只见索引）、白切鸡、烧乳猪、肠粉、水煮牛肉（页面已读，但与回锅肉同属川菜家常线，未入选）、担担面、小笼包（百度百科被拦，无别的正文）等。
4. 起源传说一律标为传说；`evidence_and_uncertainty` 中分开写「来源支持」与「本项目归纳」。
5. 价格是**游戏设计数值**（便士计，12 便士 = 1 先令；锚点：一杯麦酒 2 便士，半日短工 6–12 便士），不是史实价目。

### 1.1 与既有条目的重合核对

| 既有元素 | 核对结果 |
|---|---|
| `cuisine_peking_duck`（北京烤鸭） | **本质相同，不立条**。盐水鸭、烧鹅与它在 `related_catalog_ids` 中单向呼应，并在正文写明差别（不烤不熏／用鹅用挂炉，成品不卷饼）。 |
| `cuisine_dumpling`（饺子类，含馄饨） | 虾饺、烧卖、包子、汤圆与其呼应。虾饺是淀粉皮蒸点，烧卖是开口蒸点，包子是发酵厚皮蒸包，汤圆是糯米粉团甜汤，**皮与加热方式不同，作为独立条目**，不与饺子类合并。 |
| `cuisine_tofu`（豆腐） | 麻婆豆腐（菜品）与毛豆腐（微生物发酵制品）呼应；豆腐本体不重复。臭豆腐未立条。 |
| `cuisine_ramen`（拉面） | 刀削面是「削」入沸水的工艺，与拉面（拉伸碱水面）不同，**立条并在正文说明区别**；未直接引用 `cuisine_ramen`。 |
| `cuisine_pho`（越南粉）、`cuisine_kimchi` 等 | 无重合。 |
| `cuisine_naan` | 烧饼正文提到「馕」为近亲，未写入 `related_catalog_ids`，无重复。 |
| `cuisine-french.json`、`cuisine-british.json` | 无同名、无同菜。 |

## 二、扫读表（33 条）

### 2.1 鲁菜（山东）（3 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_sea_cucumber_scallion` | 葱烧海参（鲁菜宴席名菜） | 36–96 便士/一盘（宴席份）（shilling） | all_year | 山东（鲁菜）的奢华宴席菜：干海参经漫长泡发后与大量葱同烧，收成酱色浓汁 |
| `cuisine_cn_dezhou_chicken` | 德州扒鸡（酱汤扒到脱骨的整鸡） | 18–36 便士/一只（shilling） | all_year | 山东德州的整鸡名产：整鸡与香料在汤里长时间扒到酥烂脱骨，凉了也能吃，是靠铁路站台叫卖出名的路上食物 |
| `cuisine_cn_jiuzhuan_intestine` | 九转大肠（济南甜咸酱烧猪大肠） | 14–30 便士/一盘（shilling） | all_year | 清末济南饭馆把洗净的猪大肠先炸后烧，调出甜、咸、香辛带醋香的亮红酱汁 |

### 2.2 川菜（四川）（3 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_mapo_tofu` | 麻婆豆腐（成都辣豆瓣烧豆腐） | 4–8 便士/一碗（groat） | all_year | 成都名菜：豆腐配辣豆瓣酱，常加牛肉末或猪肉末，豆豉和花椒给出深度与麻香 |
| `cuisine_cn_kung_pao_chicken` | 宫保鸡丁（甜辣干香的鸡丁炒菜） | 8–24 便士/一盘（shilling） | all_year | 以清代官员丁宝桢命名的鸡丁炒菜，与山东酱爆鸡丁、贵州辣子鸡丁有渊源，后在四川定型：干辣、花生、甜酸之间走钢丝 |
| `cuisine_cn_twice_cooked_pork` | 回锅肉（先煮后炒的川味猪肉） | 8–18 便士/一盘（shilling） | all_year | 四川家家会做的先煮后炒猪肉 |

### 2.3 粤菜烧味与粤式点心（广东、香港、澳门）（6 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_char_siu` | 叉烧（粤式烧味烤猪肉） | 3–8 便士/一份（配饭）（groat） | all_year | 广东、香港烧腊店的基石：猪肉涂甜咸酱汁烤到边缘焦糖化，可配饭配面，也是叉烧包的馅 |
| `cuisine_cn_roast_goose` | 烧鹅（粤式烧味脆皮鹅） | 6–18 便士/一份（斩件）（shilling） | all_year | 烧腊店里挂起、点单现斩的脆皮烧鹅，常配酸梅酱 |
| `cuisine_cn_har_gow` | 虾饺（透明粉皮包鲜虾的蒸点心） | 3–6 便士/一笼（groat） | all_year | 粤式茶楼点心的标杆：半透明的淀粉皮包着鲜虾，蒸熟后透出虾色 |
| `cuisine_cn_siu_mai` | 烧卖（顶部开口的粤式茶楼蒸点心） | 3–6 便士/一笼（groat） | all_year | 顶部不封口的蒸饺，粤式茶楼版以猪肉与虾为馅，是全球最常见的点心 |
| `cuisine_cn_char_siu_bao` | 叉烧包（发酵面皮包叉烧馅） | 2–5 便士/一笼（groat） | all_year | 发酵面皮包叉烧丁与甜咸酱汁的蒸包，是茶楼推车的常客 |
| `cuisine_cn_egg_tart` | 蛋挞（港式与澳门式两条线） | 1–3 便士/一只（penny） | all_year | 蛋奶糊烤在酥壳里的小点心 |

### 2.4 苏菜（江苏）（2 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_lions_head` | 狮子头（淮扬大肉丸） | 6–18 便士/一只（宴席份）（shilling） | all_year | 江苏淮扬的大号猪肉丸，肥瘦搭配、细切粗斩，炖或烧到软嫩，常配青菜成狮鬃 |
| `cuisine_cn_nanjing_salted_duck` | 南京盐水鸭（盐渍后低温煮的整鸭） | 4–12 便士/半只（shilling） | all_year | 南京特产：整鸭先盐渍入味再温和煮熟，温食或常温食，与烟熏烤制的北京烤鸭不同 |

### 2.5 浙菜（浙江）（2 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_dongpo_pork` | 东坡肉（杭州方块五花肉久炖） | 6–18 便士/一块（宴席份）（shilling） | all_year | 杭州名菜：方块五花肉肥瘦相间，加绍兴酒久炖到红亮软烂 |
| `cuisine_cn_west_lake_fish` | 西湖醋鱼（杭州糖醋汁淡水鱼） | 8–24 便士/一条（宴席份）（shilling） | all_year | 杭州西湖餐馆的名菜：淡水鱼烹熟后淋上光亮的糖醋汁 |

### 2.6 闽菜（福建）（2 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_buddha_jumps_wall` | 佛跳墙（福州闽菜宴席汤） | 60–180 便士/一坛（宴席份）（shilling） | all_year | 福州闽菜的宴席汤：多种高档海味与肉类在酒香高汤里长时间煨在密封陶坛中 |
| `cuisine_cn_oyster_omelette` | 海蛎煎（闽南与台湾夜市的蚝煎饼） | 1–3 便士/一份（penny） | all_year | 鲜蚝加蛋和淀粉糊同煎成的咸饼，淋甜咸酱，是闽南沿海与台湾夜市的标志小吃 |

### 2.7 湘菜（湖南）（2 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_chopped_chili_fish_head` | 剁椒鱼头（湘菜剁椒蒸鱼头） | 6–14 便士/一盘（shilling） | all_year | 湖南招牌菜：大淡水鱼头剖开，铺厚厚的剁辣椒清蒸，红亮咸辣 |
| `cuisine_cn_mao_red_braised_pork` | 毛氏红烧肉（湘味五花肉红烧） | 4–10 便士/一碗（groat） | all_year | 湖南（韶山关联）的五花肉红烧，酱油加糖色炖烧，当地说法偏辣偏香 |

### 2.8 徽菜（安徽）（2 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_stinky_mandarin_fish` | 臭鳜鱼（徽州轻度发酵鳜鱼） | 6–14 便士/一条（shilling） | all_year | 徽州招牌菜：鳜鱼经盐渍并轻度发酵后再烧或蒸，气味强烈而肉质嫩 |
| `cuisine_cn_mao_tofu` | 毛豆腐（徽州表面长白色菌毛的发酵豆腐） | 1–3 便士/一小碟（penny） | all_year | 徽州的发酵豆腐：豆腐表面长出白色菌毛，多半先煎再吃 |

### 2.9 北方面点与街头小吃（7 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_baozi` | 包子（发酵面皮包馅的蒸点） | 1–2 便士/一只（penny） | all_year | 发酵面皮包咸或甜馅再蒸的主食，早餐铺、集市、餐馆里的日常食物 |
| `cuisine_cn_shaobing` | 烧饼（北方多层烘烤的芝麻面饼） | 1–2 便士/一个（penny） | all_year | 北方的层酥烘烤面饼，常裹芝麻，早餐摊现卖，可素吃也可夹肉、酱、蛋 |
| `cuisine_cn_knife_cut_noodles` | 刀削面（山西以刀削入沸水的厚面片） | 2–4 便士/一碗（groat） | all_year | 山西面食标志：用刀从面团上直接削入沸水的厚面片，中间厚两边薄，浇头常用西红柿鸡蛋或肉酱 |
| `cuisine_cn_roujiamo` | 肉夹馍（陕西腊汁肉夹白吉馍） | 1–3 便士/一个（penny） | all_year | 陕西街头小吃：切碎或撕开的炖肉夹在剖开的白吉馍里，肉汁润饼 |
| `cuisine_cn_jianbing_guozi` | 煎饼果子（天津早餐的蛋酱卷饼） | 1–2 便士/一个（penny） | all_year | 北方街头早餐：薄煎饼摊在铛上，卷入蛋、酱、葱香菜和「馃子」（炸面或薄脆），与天津相联 |
| `cuisine_cn_youtiao` | 油条（两条面坯叠压油炸的早点） | 1–2 便士/一根（penny） | all_year | 两条面坯压在一起炸到蓬松酥脆，配豆浆或粥的早餐 |
| `cuisine_cn_tanghulu` | 糖葫芦（竹签串山楂裹脆糖壳） | 1–2 便士/一串（penny） | winter | 北京冬季街头和庙会的小吃：山楂串在竹签上，外裹一层硬而亮的糖壳 |

### 2.10 年节食（4 条）

| ID | 名称 | 价格（游戏数值） | 季节 | 一句话 |
|---|---|---|---|---|
| `cuisine_cn_zongzi` | 粽子（端午节用叶子包裹的糯米食） | 1–3 便士/一只（penny） | summer | 端午节（农历五月初五）的节令食：糯米加甜或咸馅，用竹叶、芦苇叶包成三角或金字塔形再蒸煮 |
| `cuisine_cn_mooncake` | 月饼（中秋节的浓馅糕点） | 3–8 便士/一只（groat） | autumn | 中秋节（农历八月十五）食用并赠送的浓馅糕点，圆形，切角分食 |
| `cuisine_cn_nian_gao` | 年糕（春节取「年高」之意的糯米糕） | 1–3 便士/一块（penny） | all_year | 糯米做的糕，全年可吃、春节尤盛，名字谐音「年年高」 |
| `cuisine_cn_tangyuan` | 汤圆（元宵节和冬至的糯米粉团甜汤） | 1–3 便士/一碗（penny） | winter | 糯米粉团在甜汤里煮，圆形象征团圆，是元宵节和冬至的节令食 |

## 三、与已有食材／工具条目的呼应清单

下表由 JSON 的 `related_catalog_ids` 反向汇总，共 132 条关联，**全部指向现有库中存在的元素**；本组不新建任何食材条目。

| 已有元素（ID） | 引用次数 | 被哪些菜品依赖 |
|---|---|---|
| `flavors_soy_sauce` | 16 | 葱烧海参、德州扒鸡、九转大肠、宫保鸡丁、回锅肉、叉烧、烧鹅、叉烧包、狮子头、东坡肉、西湖醋鱼、海蛎煎、剁椒鱼头、毛氏红烧肉、臭鳜鱼、煎饼果子 |
| `animal_food_pork` | 13 | 九转大肠、麻婆豆腐、回锅肉、叉烧、烧卖、叉烧包、狮子头、东坡肉、佛跳墙、毛氏红烧肉、包子、肉夹馍、粽子 |
| `flavors_cane_sugar` | 12 | 九转大肠、宫保鸡丁、叉烧、叉烧包、蛋挞、东坡肉、西湖醋鱼、毛氏红烧肉、糖葫芦、月饼、年糕、汤圆 |
| `staples_wheat` | 9 | 叉烧包、蛋挞、包子、烧饼、刀削面、肉夹馍、煎饼果子、油条、月饼 |
| `animal_food_egg` | 6 | 蛋挞、海蛎煎、刀削面、煎饼果子、粽子、月饼 |
| `materials_salt` | 6 | 葱烧海参、德州扒鸡、南京盐水鸭、剁椒鱼头、臭鳜鱼、油条 |
| `flavors_chili_pepper` | 5 | 麻婆豆腐、宫保鸡丁、回锅肉、剁椒鱼头、毛氏红烧肉 |
| `cuisine_dumpling` | 4 | 虾饺、烧卖、包子、汤圆 |
| `animal_food_chicken` | 3 | 德州扒鸡、宫保鸡丁、佛跳墙 |
| `animal_food_rendered_fat` | 3 | 九转大肠、蛋挞、油条 |
| `flavors_sichuan_pepper` | 3 | 德州扒鸡、麻婆豆腐、宫保鸡丁 |
| `flavors_star_anise` | 3 | 德州扒鸡、南京盐水鸭、肉夹馍 |
| `flavors_vinegar` | 3 | 九转大肠、宫保鸡丁、西湖醋鱼 |
| `produce_garlic` | 3 | 麻婆豆腐、回锅肉、剁椒鱼头 |
| `staples_rice` | 3 | 粽子、年糕、汤圆 |
| `staples_sesame` | 3 | 烧饼、月饼、汤圆 |
| `tools_pottery_cooking_pot` | 3 | 狮子头、东坡肉、佛跳墙 |
| `animal_food_oyster` | 2 | 佛跳墙、海蛎煎 |
| `animal_food_shrimp_prawn` | 2 | 虾饺、烧卖 |
| `cuisine_peking_duck` | 2 | 烧鹅、南京盐水鸭 |
| `cuisine_tofu` | 2 | 麻婆豆腐、毛豆腐 |
| `flavors_cassia` | 2 | 德州扒鸡、肉夹馍 |
| `flavors_ginger` | 2 | 九转大肠、臭鳜鱼 |
| `flavors_tea` | 2 | 虾饺、烧卖 |
| `materials_charcoal` | 2 | 叉烧、烧鹅 |
| `staples_soybean` | 2 | 麻婆豆腐、毛豆腐 |
| `animal_food_beef` | 1 | 麻婆豆腐 |
| `animal_food_duck` | 1 | 南京盐水鸭 |
| `animal_food_goose` | 1 | 烧鹅 |
| `cuisine_ramen` | 1 | 刀削面 |
| `flavors_clove` | 1 | 德州扒鸡 |
| `flavors_fennel_seed` | 1 | 德州扒鸡 |
| `flavors_honey` | 1 | 叉烧 |
| `food_supp_lotus` | 1 | 月饼 |
| `food_supp_water_chestnut` | 1 | 狮子头 |
| `produce_chinese_cabbage` | 1 | 狮子头 |
| `produce_jujube` | 1 | 粽子 |
| `produce_onion` | 1 | 葱烧海参 |
| `staples_peanut` | 1 | 宫保鸡丁 |
| `staples_sweet_potato` | 1 | 海蛎煎 |
| `tools_mortar_pestle` | 1 | 年糕 |
| `tools_storage_jar` | 1 | 佛跳墙 |

## 四、标签统计（实测）

- 基础标签：`tradition:eastern` 33、`cuisine:chinese` 33（全部）。
- 类别：`kind:dish` 20、`kind:pastry` 5、`kind:snack` 8
- 菜系：`school:chuan` 3、`school:hui` 2、`school:lu` 3、`school:min` 2、`school:su` 2、`school:xiang` 2、`school:yue` 6、`school:zhe` 2
- 地域：`region:anhui` 2、`region:beijing` 1、`region:fujian` 2、`region:guangdong` 6、`region:guizhou` 1、`region:hunan` 2、`region:jiangsu` 2、`region:macau` 1、`region:north_china` 1、`region:pan_china` 5、`region:shaanxi` 1、`region:shandong` 4、`region:shanxi` 1、`region:sichuan` 3、`region:south_china` 1、`region:taiwan` 1、`region:tianjin` 1、`region:zhejiang` 2
- 阶层：`class_marker:common` 29、`class_marker:elite` 4
- 场合：`occasion:banquet` 9、`occasion:duanwu` 1、`occasion:everyday` 12、`occasion:festival` 5、`occasion:lantern` 1、`occasion:mid_autumn` 1、`occasion:new_year` 1、`occasion:night_market` 1、`occasion:temple_fair` 1、`occasion:travel` 1、`occasion:winter_solstice` 1、`occasion:yum_cha` 3
- 技法：`technique:bake` 4、`technique:boil` 4、`technique:braise` 10、`technique:candy` 1、`technique:cure` 2、`technique:deep_fry` 2、`technique:ferment` 2、`technique:glaze` 2、`technique:griddle` 1、`technique:knife_cut` 1、`technique:leaven` 1、`technique:pan_fry` 2、`technique:pastry` 1、`technique:poach` 2、`technique:rehydrate` 1、`technique:roast` 2、`technique:simmer` 2、`technique:spice` 1、`technique:steam` 6、`technique:steam_leaven` 1、`technique:stir_fry` 3、`technique:wrap` 1
- game 标签：
  - `price:groat` 8、`price:penny` 12、`price:shilling` 13
  - `season:all_year` 29、`season:autumn` 1、`season:summer` 1、`season:winter` 2
  - `sold_by:baker` 5、`sold_by:butcher` 3、`sold_by:grocer` 4、`sold_by:inn_kitchen` 4、`sold_by:market` 11、`sold_by:noble_kitchen` 6、`sold_by:street_vendor` 21、`sold_by:tavern` 20
  - `terrain:coast` 4、`terrain:farmland` 17、`terrain:lake` 2、`terrain:mountain` 2、`terrain:orchard` 1、`terrain:plateau` 1、`terrain:river` 1、`terrain:wetland` 6、`terrain:workshop` 33
- 未手写 `genre:` 与 `category:`（由引擎依 `genres` / `category` 自动生成）。
- 价格分布：penny 12 条、groat 8 条、shilling 13 条；最高为佛跳墙 60–180 便士，最低为 1–2 便士的街头小吃。
- `school:` 为本组自建的检索标签（引擎只要求标签格式合法），`region:` 取省份或区域名。

## 五、实际读过并使用的来源（access=read，46 条）

以下均被至少一个元素引用。`access: read` 只表示采集侧声称读过正文，**不等于已核实**。Chinese Food Wiki 为社区维基，可靠度中等；Britannica 的鲁菜、川菜、粤菜条目只有「Quick Summary」，页面注明由 Britannica AI 生成，权重低；UNESCO 端午条目正文只读到开头一段。

| ID | 来源 | 被引用次数 |
|---|---|---|
| `cuisine_cn_src_01` | Chinese Food Wiki：Scallion Braised Sea Cucumber | 1 |
| `cuisine_cn_src_02` | Lu cuisine (Shandong cuisine) — Encyclopaedia Britannica | 2 |
| `cuisine_cn_src_03` | Chinese Food Wiki：Dezhou Braised Chicken | 1 |
| `cuisine_cn_src_04` | Chinese Food Wiki：Jiuzhuan Dachang | 1 |
| `cuisine_cn_src_05` | Chinese Food Wiki：Mapo Tofu | 1 |
| `cuisine_cn_src_06` | 人民中国：マーポー豆腐（麻婆豆腐，日文） | 1 |
| `cuisine_cn_src_07` | Chuan cuisine (Sichuan cuisine) — Encyclopaedia Britannica | 2 |
| `cuisine_cn_src_08` | Sichuan pepper — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_09` | Chinese Food Wiki：Kung Pao Chicken | 1 |
| `cuisine_cn_src_10` | Chinese Food Wiki：Twice Cooked Pork | 1 |
| `cuisine_cn_src_11` | Chinese cuisine — Encyclopaedia Britannica | 5 |
| `cuisine_cn_src_12` | Chinese Food Wiki：Char Siu | 1 |
| `cuisine_cn_src_13` | Yue cuisine (Cantonese cuisine) — Encyclopaedia Britannica | 2 |
| `cuisine_cn_src_14` | Chinese Food Wiki：Roast Goose | 1 |
| `cuisine_cn_src_15` | Chinese Food Wiki：Har Gow | 1 |
| `cuisine_cn_src_16` | Dim sum — Encyclopaedia Britannica | 3 |
| `cuisine_cn_src_17` | Chinese Food Wiki：Siu Mai | 1 |
| `cuisine_cn_src_18` | Chinese Food Wiki：Char Siu Bao | 1 |
| `cuisine_cn_src_19` | Chinese Food Wiki：Egg Tart | 1 |
| `cuisine_cn_src_20` | Chinese Food Wiki：Lion's Head Meatballs | 1 |
| `cuisine_cn_src_21` | Chinese Food Wiki：Nanjing Salted Duck | 1 |
| `cuisine_cn_src_22` | Chinese Food Wiki：DongPo Stewed Pork | 1 |
| `cuisine_cn_src_23` | Chinese Food Wiki：West Lake Vinegar Fish | 1 |
| `cuisine_cn_src_24` | Chinese Food Wiki：Buddha Jumps Over the Wall | 1 |
| `cuisine_cn_src_25` | Chinese Food Wiki：Oyster Omelette | 1 |
| `cuisine_cn_src_26` | Chinese Food Wiki：Steamed Fish Head with Chop Bell Pepper | 1 |
| `cuisine_cn_src_27` | Chinese Food Wiki：Mao's Red-Braised Pork | 1 |
| `cuisine_cn_src_28` | Chinese Food Wiki：Stinky Mandarin Fish | 1 |
| `cuisine_cn_src_29` | Chinese Food Wiki：Anhui Cuisine | 2 |
| `cuisine_cn_src_30` | Chinese Food Wiki：Baozi | 1 |
| `cuisine_cn_src_31` | Chinese Food Wiki：Shaobing | 1 |
| `cuisine_cn_src_32` | Chinese Food Wiki：Knife-cut Noodles | 1 |
| `cuisine_cn_src_33` | Chinese Food Wiki：Roujiamo | 1 |
| `cuisine_cn_src_34` | Chinese Food Wiki：Jianbing Guozi | 1 |
| `cuisine_cn_src_35` | Chinese Food Wiki：Youtiao | 1 |
| `cuisine_cn_src_36` | Chinese Food Wiki：Tanghulu | 1 |
| `cuisine_cn_src_37` | Dragon Boat Festival — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_38` | Dragon Boat festival — UNESCO Intangible Cultural Heritage | 1 |
| `cuisine_cn_src_39` | Chinese Food Wiki：Zongzi | 1 |
| `cuisine_cn_src_40` | Mooncake — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_41` | Zhongqiu Jie (Mid-Autumn Festival) — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_42` | Chinese Food Wiki：Mooncake | 1 |
| `cuisine_cn_src_43` | Chinese New Year — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_44` | Chinese Food Wiki：Nian Gao | 1 |
| `cuisine_cn_src_45` | Lantern Festival — Encyclopaedia Britannica | 1 |
| `cuisine_cn_src_46` | Chinese Food Wiki：Tangyuan | 1 |

## 六、失败并如实登记（access=unavailable，11 条，零引用）

| ID | 来源 | 失败原因 |
|---|---|---|
| `cuisine_cn_src_un_01` | 维基百科：宫保鸡丁（中文） | 连接超时（dial tcp 无响应），未读到正文。 |
| `cuisine_cn_src_un_02` | 维基百科：麻婆豆腐（中文） | 连接超时，未读到正文。 |
| `cuisine_cn_src_un_03` | 维基百科：东坡肉（中文） | 连接超时，未读到正文。 |
| `cuisine_cn_src_un_04` | Wikipedia: Mapo doufu | 连接超时，未读到正文。 |
| `cuisine_cn_src_un_05` | 百度百科：小笼包 | 被百度安全验证拦截（HTTP 403），未读到正文。 |
| `cuisine_cn_src_un_06` | Zongzi — Encyclopaedia Britannica | 返回 HTTP 404。粽子改由 Dragon Boat Festival 条目与 Chinese Food Wiki 支撑。 |
| `cuisine_cn_src_un_07` | The Twenty-Four Solar Terms — UNESCO Intangible Cultural Heritage | 页面可取回，但抽取到的只有站点导航，没有读到条目正文；不据此立论。 |
| `cuisine_cn_src_un_08` | Chinese Food Wiki：Steamed Fish Head with Chopped Chili（错误路径） | 返回 HTTP 404（正确页名是 Steamed Fish Head with Chop Bell Pepper，已另列并读取）。 |
| `cuisine_cn_src_un_09` | Chinese Food Wiki：Huangshan Shaobing | 返回 HTTP 404，无此页。 |
| `cuisine_cn_src_un_10` | Chinese Food Wiki：Mao Tofu | 返回 HTTP 404，无独立页面；毛豆腐仅能从徽菜页的简述取证。 |
| `cuisine_cn_src_un_11` | 早稲田大学：山西刀削面随笔（日文） | 本次重新读取返回 HTTP 404，没有读到正文；不据此立论。 |

另：中文维基、英文维基的多个菜名页（八大菜系、粽子、佛跳墙、小笼包等）在采集时同样连接超时，由于没有逐条登记，**未出现在上表**，也没有被任何条目引用。

## 七、待裁定点

1. **`cuisine_cn_mao_tofu` 证据最薄**：只有 Chinese Food Wiki 徽菜总页一句话（表面长白色菌毛、常煎后食用），无专页（专页路径 404，已登记）。条目只写能确认的部分，起源、做法细节、安全要点均缺来源。请裁定保留或移出本组；徽菜因此实质只有臭鳜鱼一条证据较完整的菜。
2. **来源以社区维基为主**：约四分之三的条目只有 Chinese Food Wiki 一条来源。它的参考文献本项目未逐条核对。建议后续用地方志、烹饪专著或官方非遗名录补强。
3. **Britannica 鲁、川、粤三个菜系条目是 AI 摘要页**，只能支持总体印象。
4. **刀削面**：早稲田大学随笔页重新读取返回 404，已按 unavailable 登记并不再采信其「山西粉食约 2000 年」等说法；非遗名录一句出自 Chinese Food Wiki。
5. **宫保鸡丁、回锅肉的年代／创制人**只是页面转述的通行说法，没有档案级证据；陈麻婆饭店 1862 年创立是饭店自述。
6. **蛋挞**两条线（港式、澳门葡挞）合并为一条，若需要可拆分。
7. **terrain 词表**：刀削面用了 `terrain:plateau`（山西黄土高原）。校验时 `tools/game_fields.py` 已含 `plateau`；若入库前词表回退，需把它改为 `mountain` 或 `steppe`。
8. 价格与保存期（`keeps`）、`sold_by` 均为游戏设计取值，非史实。

## 八、验证输出（未改动的 `app.encyclopedia.import_document`，临时库 `temp/cuisine_cn_check.sqlite3`）

先按 `tools.encyclopedia_build.groups_for` 取全部现有分区共 35 份，逐份 `game_fields.overlay` 后导入，再导入本文件：

```
check_element_tags OK 33
unresolved list []
stats totals {"groups": 36, "elements": 1007, "element_versions": 1007, "sources": 1213, "source_versions": 1213, "unresolved_relations": 0}
cuisine-chinese: elements 33, sources 57, tags 116, unresolved_relations 0, needs_review 33, needs_detail 33
reimport: element_versions 0（幂等）
```

- 33 条 `game` 均通过 `game_fields.check_element_tags`。
- 33 条元素 ID 唯一；七节全为非空字符串；`related_catalog_ids` 共 132 条，全部在现有库中存在；正文里出现的 `cuisine_` / `staples_` 等 ID 也全部存在。
- 无任何 `unavailable` 来源被引用；所有 `read` 来源均被引用。
- JSON 为 UTF-8 无 BOM，用 `json.dump(ensure_ascii=False, indent=2)` 写出。
