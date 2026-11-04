# 法国菜系菜品（cuisine-french 组）

对应 `cuisine-french.json`。状态：**候选资料**，不是数据库记录，也不是任何故事包已采纳的正典。本文件只提供扫读视图、呼应清单与已知不足；完整字段（summary / details 七节 / source_ids 等）**以 JSON 为准**。

- 顶层：`schema_version: 1`、`status: candidate`、`group: cuisine-french`、`genres: ["real_world"]`，条目 ID 前缀 `cuisine_fr_`。
- 共 **33 项**元素，其中 `category: item` **31 条**、`category: institution` **2 条**（`cuisine_fr_cheese_aging_institution`、`cuisine_fr_restaurant_review`）；制度、技法与面包三类靠 `kind:` 标签再分（institution 3 / technique 5 / bread 3 / cuisine_style 1 / dish 21）。全部 `review_status: needs_review`、`detail_status: needs_detail`。
- 来源 **62 条**：`access: read` **47 条**、`unavailable` **15 条**（失败如实登记，**零引用**，未出现在任何元素的 `source_ids` 中）。
- 每条含 `details` 七节（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty），全部为非空字符串。
- **不做可执行食谱**：只写技法与工序顺序，不给克数配比；不写强制喂食、宰杀与保存的操作细节。

## 一、这个组在收集什么

服务小说与游戏的世界构建（食物、宴席、市场、阶级与地域）。取舍标准三条：

1. 只收**成品菜、技法体系与饮食制度**，不收食材物种。
2. **食材级零重复**：小麦、黑麦、荞麦、马铃薯、甘蓝、洋葱、大蒜、韭葱、芜菁、胡萝卜、番茄、茄子、苹果、梨、葡萄、樱桃、核桃、榛、乳、黄油、奶酪、蛋、牛猪羊禽、鳕、牡蛎、蛤、虾、火腿、香肠、熬炼脂肪、干腌鱼、盐、醋、芥末、藏红花、胡椒、肉豆蔻、丁香、葡萄酒、苹果酒、蒸馏酒等均已在 `staples` / `produce` / `flavors` / `animal-foods` / `food-supplement` / `materials` 各组立条，本组**只写菜品如何依赖它们**，并用 `related_catalog_ids` 指向。
3. **与 `cuisine.json` 的 24 条无重合**：已逐条核对（寿司、饺子、拉面、泡菜、豆腐、比尔亚尼、鹰嘴豆泥、法拉费、库斯库斯、英吉拉、乔洛夫饭、披萨、炖饭、海鲜饭、塔可、tortilla、腌鱼、越南粉、馕、咖喱、萨莫萨、塔马利、北京烤鸭、卡巴布），其中披萨条目的 `supports` 里提到普罗旺斯 `pissaladière`、越南粉条目提到法国殖民与 `pot-au-feu` 的影响——这两处是**原料/影响关系的提及**，不是同名菜条目，故不构成重复；本组的 `cuisine_fr_pot_au_feu` 已把「与越南粉源流有争议」写入例外节，两处不冲突。

## 二、扫读表（33 条，分四档）

### 2.1 宫廷与高级菜体系（10 条）

| ID | 名称 | 类别 | 做法要点 | 一句话 |
|---|---|---|---|---|
| `cuisine_fr_grande_cuisine` | 高级菜与宫廷宴席体系 | item（`kind:cuisine_style`） | 高汤—母酱骨架 + 形式化烹调法 + 宴席四道结构 | 一桌菜的复杂度就是权力排名 |
| `cuisine_fr_consomme` | 清汤（consommé） | item | 带骨肉长煮取胶、撇沫澄清，冷后成冻 | 全厨房唯一不能临时遮掩的东西 |
| `cuisine_fr_potage` | 浓汤与菜泥汤（potage 一类） | item | 面粉/蛋黄/菜泥三条增稠路线 | 把一份粮扩成十碗的技术 |
| `cuisine_fr_roux_white_sauce` | 面糊增稠与白汁体系 | item（`kind:technique`） | roux 焙炒程度 × 液体加入方式 | 法国厨房的通用语法 |
| `cuisine_fr_hollandaise` | 荷兰酱与贝亚恩酱 | item（`kind:technique`） | 蛋黄 + 酸 + 分次搅入极软黄油 | 温度窗口极窄，分离是常态 |
| `cuisine_fr_aspic` | 肉冻与冻釉（含 chaud-froid） | item | 明胶溶—凝可逆，模具「倒着做」 | 一桌肉冻 = 一份冷藏与人工清单 |
| `cuisine_fr_pate_terrine` | 肉批与陶罐批 | item | 陶罐（冷食）/ 酥皮（可热食）两路 | 同一名字下的三种东西 |
| `cuisine_fr_foie_gras` | 鹅肝 | item | 育肥肝 + 盐渍低温熟成 + 酥皮或陶罐 | 体面与残酷同席 |
| `cuisine_fr_truffle_cookery` | 松露入菜 | item（`kind:technique`） | 少加热、晚加入、密闭保香 | 采集经济，不是农业经济 |
| `cuisine_fr_seafood_platter` | 海鲜拼盘 | item | 保活／速冷／分批煮／现摆 | 「离海多远」的公开告白 |

### 2.2 地方菜（11 条）

| ID | 名称 | 地域 | 做法要点 | 一句话 |
|---|---|---|---|---|
| `cuisine_fr_boeuf_bourguignon` | 勃艮第红酒炖牛肉 | 东部酒区 | 上色 → 覆锅微沸 → 收汁 | 有什么酒，就有什么味道 |
| `cuisine_fr_choucroute` | 阿尔萨斯酸菜炖肉 | 阿尔萨斯（近德边境） | 甘蓝盐渍发酵 ≥1 月 + 猪肉香肠同炖 | 保存技术决定菜系 |
| `cuisine_fr_quiche_lorraine` | 洛林咸派（quiche 一类） | 洛林 | 塔皮空烤 + 蛋奶糊凝固 | 它是「咸味蛋奶糊」 |
| `cuisine_fr_bouillabaisse` | 马赛鱼汤 | 普罗旺斯／马赛 | 多鱼分层、快速同煮 + rouille | 由渔获定义、由地理限定 |
| `cuisine_fr_ratatouille` | 普罗旺斯炖菜 | 普罗旺斯／尼斯 | 分炒定型 → 合炖 → 保持可辨认 | 农家菜被提升为高级餐饮 |
| `cuisine_fr_cassoulet` | 卡苏莱砂锅 | 朗格多克（三城之争） | 分层入陶锅长烤 → 反复结壳 | 名字来自锅，不来自豆 |
| `cuisine_fr_fondue_savoyarde` | 萨瓦奶酪火锅 | 阿尔卑斯（源出瑞士） | 酒 + 淀粉 + 温度稳定乳化 | 山区冬季 + 乳品过剩 + 共食 |
| `cuisine_fr_normandy_cider_pork` | 诺曼底苹果酒炖肉 | 诺曼底／布列塔尼 | 以发酵苹果酒代葡萄酒焖煮 | 负面条件（无葡萄园）成菜系 |
| `cuisine_fr_galette_bretonne` | 布列塔尼荞麦薄饼 | 布列塔尼 | 荞麦糊摊铁板，无酵薄摊 | 没有小麦也能有主食 |
| `cuisine_fr_charcuterie_lyon` | 里昂与奥弗涅猪肉冷盘体系 | 奥弗涅／里昂／阿尔萨斯 | 盐—干—烟—时四要素 + 行会规章 | 既是保存技术，也是职业门槛 |
| `cuisine_fr_potee_auvergnate` | 奥弗涅豆焖肉（potée） | 中部山地 | 豆 + 腌肉 + 根茎同锅，一锅四样 | 以「能喂多少人」为判据的丰盛 |

### 2.3 面包与酥点（8 条）

| ID | 名称 | 类别 | 做法要点 | 一句话 |
|---|---|---|---|---|
| `cuisine_fr_baguette` | 法棍 | item（`kind:bread`） | 四料 + 时间 + 手工成型 + 划口 + 高温 | 面包不只是食物，还是出门的理由 |
| `cuisine_fr_croissant` | 可颂 | item（`kind:bread`） | 酵母面团裹脂层压，卷成月牙 | 同一柜台上的阶级差写在形状里 |
| `cuisine_fr_brioche` | 布里欧修 | item（`kind:bread`） | 高脂面团分次揉入、揉三次 | 「面包」的奢侈版本 |
| `cuisine_fr_choux_eclair` | 泡芙皮与闪电泡芙 | item（`kind:technique`） | 烫面糊化 + 加蛋 + 先高温定型后烘透 | 同一个壳可甜可咸 |
| `cuisine_fr_puff_pastry` | 千层酥与起层酥皮 | item（`kind:technique`） | 裹脂折叠 + 反复冷藏 | 所有难点都在温度 |
| `cuisine_fr_creme_caramel_brulee` | 焦糖蛋奶冻与烤糖脆壳 | item | 蛋奶凝固 + 糖在工序两端 | 家常材料 + 餐馆呈现 |
| `cuisine_fr_souffle` | 舒芙蕾 | item | 蛋白霜翻拌入基料、入模烤、即时上桌 | 成败有一半发生在客人等的那几分钟 |
| `cuisine_fr_macaron` | 马卡龙 | item | 蛋白霜 + 杏仁粉 + 结皮出裙边 | 从修院与贵族专享到摆摊售卖 |

### 2.4 奶酪制度与餐馆制度（4 条）

| ID | 名称 | 类别 | 要点 | 一句话 |
|---|---|---|---|---|
| `cuisine_fr_cheese_aging_institution` | 奶酪熟成与产地命名制度 | institution | affinage（酶与微生物的时间）+ AOP/AOC、PDO/PGI、INAO | 熟成决定风味，产地命名决定价格 |
| `cuisine_fr_restaurant_review` | 餐馆制度与美食评论 | institution | 菜单点菜 + brigade de cuisine + 指南与评论家 | 大革命把厨师赶出来，餐馆接住了他们 |
| `cuisine_fr_pot_au_feu` | 火上锅 | item | 同锅长煮、先汤后肉分食 | 名字就是它的装置 |
| `cuisine_fr_steak_frites` | 牛排配薯条 | item | 干热上色 + 油炸双温 | 简单菜考验基本功 |

## 三、与已有食材条目的呼应清单（食材 → 菜品如何依赖它）

下表由 JSON 的 `related_catalog_ids` 反向汇总（只列本组实际引用者）。**本组不新建任何食材条目**。

| 已有元素（ID） | 本组引用次数 | 被哪些菜品依赖 |
|---|---|---|
| `animal_food_ham_bacon`（火腿与腌熏猪肉） | 8 | 肉批、红酒炖牛肉、酸菜炖肉、咸派、卡苏莱、猪肉冷盘、火上锅、豆焖肉 |
| `tools_pottery_cooking_pot`（陶制炊具） | 7 | 清汤、浓汤、红酒炖牛肉、马赛鱼汤、卡苏莱、奶酪火锅、火上锅 |
| `flavors_cane_sugar`（蔗糖） | 6 | 布里欧修、泡芙、千层酥、焦糖蛋奶冻、舒芙蕾、马卡龙 |
| `animal_food_beef`（牛肉） | 5 | 清汤、肉冻、红酒炖牛肉、火上锅、牛排配薯条 |
| `staples_potato`（马铃薯） | 5 | 浓汤、酸菜炖肉、火上锅、豆焖肉、牛排配薯条 |
| `animal_food_rendered_fat`（熬炼动物脂肪） | 5 | 浓汤、肉批、卡苏莱、猪肉冷盘、千层酥 |
| `animal_food_sausage`（香肠） | 5 | 肉批、酸菜炖肉、卡苏莱、猪肉冷盘、豆焖肉 |
| `produce_onion`（洋葱） | 4 | 红酒炖牛肉、咸派、马赛鱼汤、普罗旺斯炖菜 |
| `animal_food_chicken`（家鸡） | 3 | 清汤、肉冻、苹果酒炖肉 |
| `staples_common_bean`（菜豆） | 3 | 浓汤、卡苏莱、豆焖肉 |
| `produce_cabbage`（甘蓝） | 3 | 浓汤、酸菜炖肉、豆焖肉 |
| `flavors_vinegar`（醋） | 3 | 荷兰酱、肉冻、海鲜拼盘 |
| `animal_food_cod`（鳕与白肉底栖鱼） | 3 | 肉冻、海鲜拼盘、马赛鱼汤 |
| `produce_carrot`（胡萝卜） | 3 | 红酒炖牛肉、火上锅、豆焖肉 |
| `produce_tomato`（番茄） | 3 | 马赛鱼汤、普罗旺斯炖菜、卡苏莱 |
| `flavors_cocoa`（可可与巧克力） | 3 | 可颂、泡芙、马卡龙 |
| `flavors_vanilla`（香荚兰） | 3 | 泡芙、焦糖蛋奶冻、马卡龙 |
| `flavors_nutmeg_mace`（肉豆蔻） | 2 | 白汁（作为酱汁固体调味）、奶酪火锅 |
| `produce_lemon_lime`（柠檬与来檬） | 2 | 荷兰酱、海鲜拼盘 |
| `produce_garlic`（大蒜） | 2 | 马赛鱼汤、普罗旺斯炖菜 |
| `flavors_saffron`（藏红花） | 2 | 马赛鱼汤、布里欧修（地方特产用） |
| `staples_olive`（油橄榄，含橄榄油） | 2 | 马赛鱼汤、普罗旺斯炖菜 |
| `flavors_mustard`（芥末） | 2 | 猪肉冷盘、火上锅 |
| `produce_almond`（扁桃，含杏仁粉） | 2 | 可颂（杏仁馅）、马卡龙（主料） |
| `flavors_black_pepper`（胡椒） | 2 | 红酒炖牛肉、牛排配薯条 |
| `flavors_distilled_spirit`（蒸馏酒） | 2 | 鹅肝（白兰地）、奶酪火锅（kirsch） |
| `animal_food_goose`（家鹅） | 2 | 鹅肝、卡苏莱（confit d'oie） |
| `animal_food_duck`（家鸭） | 2 | 鹅肝、卡苏莱 |
| `food_supp_cultivated_mushroom`（栽培食用菌） | 2 | 松露入菜（作为「菌」类对照）、红酒炖牛肉（配菜） |
| `animal_food_oyster`（牡蛎） | 2 | 海鲜拼盘、马赛鱼汤 |
| `animal_food_shrimp_prawn`（虾） | 2 | 海鲜拼盘、马赛鱼汤 |
| `animal_food_dried_salted_fish`（干腌鱼） | 2 | 海鲜拼盘（对照）、猪肉冷盘（斋期改售腌鱼） |
| `flavors_spice_blend`（复合香料） | 2 | 酸菜炖肉、普罗旺斯炖菜 |
| `food_supp_leek`（韭葱） | 2 | 浓汤、火上锅 |
| `food_supp_turnip`（芜菁） | 2 | 火上锅、豆焖肉 |
| `staples_lentil`（兵豆） | 1 | 豆焖肉 |
| `staples_pea`（豌豆） | 1 | 浓汤 |
| `staples_buckwheat`（荞麦） | 1 | 布列塔尼荞麦薄饼 |
| `produce_apple` / `produce_pear`（苹果／梨） | 1 / 1 | 诺曼底苹果酒炖肉（酒与配菜） |
| `produce_eggplant` / `produce_squash_pumpkin`（茄子／南瓜类） | 1 / 1 | 普罗旺斯炖菜 |
| `produce_walnut`（核桃） | 1 | 松露入菜（作为香气/脂肪介质对照） |
| `flavors_fennel_seed`（茴香籽） | 1 | 马赛鱼汤 |
| `flavors_beet_sugar`（甜菜糖） | 1 | 焦糖蛋奶冻（糖的第二来源） |
| `animal_food_salmon`（鲑鳟类） | 1 | 荷兰酱（传统搭配水波鲑鱼） |
| `animal_food_clam`（蛤与双壳类） | 1 | 海鲜拼盘 |
| `animal_food_butter`（黄油） | 见各条 | 母酱、荷兰酱、布里欧修、可颂、千层酥、泡芙、苹果酒炖肉 |
| `animal_food_cheese`（奶酪） | 见各条 | 咸派、奶酪火锅、熟成与命名制度、可颂馅 |
| `animal_food_egg`（禽蛋） | 见各条 | 清汤饰、肉冻、荷兰酱、咸派、泡芙、舒芙蕾、马卡龙、焦糖蛋奶冻、牛排配薯条酱汁 |
| `animal_food_milk`（乳） | 见各条 | 白汁、咸派、布里欧修、焦糖蛋奶冻、舒芙蕾、奶酪制度 |
| `flavors_wine`（葡萄酒） | 见各条 | 红酒炖牛肉、酸菜炖肉、马赛鱼汤（对照）、奶酪火锅、母酱、荷兰酱 |
| `materials_salt`（食盐） | 见各条 | 清汤、浓汤、酸菜（发酵）、腌腊体系、火上锅、豆焖肉、法棍 |
| `animal_food_mutton_lamb`（羊肉） | — | 卡苏莱 Carcassonne 版（羊肉）在条目正文提及，未单列 ID 关联 |
| `animal_food_pork`（猪肉） | 见各条 | 肉批、酸菜炖肉、卡苏莱、猪肉冷盘、豆焖肉、苹果酒炖肉、火上锅 |
| `tools_kitchen_knife`（厨刀） | 2 | 高级菜（分切与呈现）、白汁（酱汁岗位） |
| `tools_storage_jar`（储藏罐） | 1 | 肉冻（模具与容器） |
| `society_craft_guild` / `society_merchant_guild`（行会） | 各 1 | 餐馆制度与美食评论（与 `cuisine_fr_charcuterie_lyon` 呼应的行会机制） |

### 3.1 与已有菜式条目的呼应

| 已有 `cuisine.json` 条目 | 关系 |
|---|---|
| `cuisine_pizza` | 其 `supports` 提到利古里亚式近似普罗旺斯 `pissaladière`；本组**未建**该条，仅在说明中保留「沿海菜在异地再版本会增补原料」的对照（见 `cuisine_fr_bouillabaisse` 与 `cuisine_fr_seafood_platter` 的例外节）。**非重复。** |
| `cuisine_pho` | 其 `supports` 记有「法国牛肉炖锅 pot-au-feu 是越南粉最明显的先驱」；本组 `cuisine_fr_pot_au_feu` 引用同一来源并把「菜名也可能来自『粉』的越南读音」两说并列。**非重复，属影响关系的双向呼应。** |
| 其余 22 条 | 逐条核对，无重合（无任何西式菜式条目）。 |

## 四、标签统计（实测）

`tags` 只写本组自定的检索前缀，**不手写 `genre:` / `category:`**——这两类由 `app.encyclopedia` 在导入时按 `genres` / `category` 字段自动追加（本组导入后实测：`category:item` 31 条、`category:institution` 2 条、`genre:real_world` 33 条）。

共 33 条元素、368 个标签项，前缀分布：

| 前缀 | 项数 | 说明 |
|---|---|---|
| `kind:` | 33 | dish 21 / technique 5 / institution 3 / bread 3 / cuisine_style 1 |
| `tradition:` | 33 | 全部 `tradition:western` |
| `cuisine:` | 33 | 全部 `cuisine:french` |
| `course:` | 40 | main 17 / starter 10 / dessert 5 / sauce 3 / bread 3 / side 1 / cheese 1 |
| `technique:` | 57 | bake 11 / simmer 8 / ferment 4 / braise 3 / emulsify 3 / chill 3 / set_custard 2 / laminate 2 / foam 2，其余 clarify、puree、thicken、gelatinize、charcuterie、raw、boil_fast、saute、confit、melt、griddle、curing、smoke、enrich、steam_leaven、caramelize、age、pan_fry、deep_fry 各 1 |
| `occasion:` | 61 | tavern 25 / festival 17 / court 12 / famine 4 / fasting 3 |
| `class_marker:` | 33 | common 19 / elite 14 |
| `role:` | 36 | daily_staple 10 / status_display 5 / kitchen_hierarchy 5 / patisserie 4 / preservation 3，其余 luxury_good、foraging、portable_food、communal_meal、breakfast_food、service_theatre、regulation、critic、restaurant_staple 各 1 |
| `trade:` | 42 | butcher 10 / dairy_farmer 5 / baker 5 / guild 3 / miller 3 / poultry 2 / fisher 2 / market_gardener 2 / pastry_chef 2，其余 forager、vintner、brewer、egg_farmer、spice_trade、potter、orchard、merchant 各 1 |

## 五、实际读过并使用的来源（access=read，47 条）

| ID | 来源 | 实际支撑的内容（摘要） |
|---|---|---|
| src_01 | Britannica **French cuisine** | 法国菜的界定与代表菜；中世纪宫廷宴席与社会史；凯瑟琳入法；La Varenne / Carême 四种母酱 / Escoffier 五种母酱与 mise en place；新料理；mirepoix 等技法；阿尔萨斯酸菜炖肉的做法与调味 |
| src_02 | Britannica **Bouillabaisse** | 马赛鱼汤的地域、原料清单、必须用地中海鱼与骨多岩鱼、快速同煮、rouille、巴黎版加贻贝、Thackeray 的文学赞誉 |
| src_03 | Britannica **Ratatouille** | 词源、经典工序、蔬菜与香料、洋葱之争与 Robuchon 主张、成菜两路、最早食谱 19 世纪 / 名称 18 世纪末、尼斯代表菜、农家菜升格、2007 动画 |
| src_04 | **UNESCO ICH** 法国美食宴名录条目 | 2010 年列入；四道结构与餐前酒/餐后酒；食材选择、菜酒搭配、餐桌布置、闻与品；gastronomes 的传承角色 |
| src_05 | Britannica **Cassoulet** | 得名于 cassole d'Issel、朗格多克、三城版本差异、confit d'oie 释义、面包屑与鹅油结壳 |
| src_06 | Britannica **Croissant** | 月牙形与命名、1906 年最早配方、20 世纪大流行、黄油 vs 麦淇淋两型、以形状区分、甜咸馅 |
| src_07 | Britannica **Foie gras** | 育肥肝、斯特拉斯堡、质地色泽、pâté de foie gras 与 terrine、白兰地与松露、动物权争议与 2006 芝加哥禁令 |
| src_08 | Britannica **Soup** | 汤的定义与液体介质、长时煮取、清汤作第一道/浓汤作主菜、水果汤作甜点、冷汤（vichyssoise 等）、consommé 冷食成冻、浓汤三条增稠路线、bisque/chowder、garbure |
| src_09 | **UNESCO ICH** 法棍名录条目 | 2022 年列入；九步传统流程含划口；只用四料；小批量全天烤且随温湿度变化；每日购买与专用陈列架；技艺经工作培训传承 |
| src_10 | Britannica **Charcuterie** | 词义三层次与扩大用法、chair cuit 词源、中世纪行规限猪肉与猪脂、原指店铺、斋期兼售腌鱼、腌腊四道工序、环境决定风干或湿腌、jambon de Paris、奥弗涅与阿尔萨斯产区、saucisson sec 地区差异 |
| src_11 | Britannica **Truffle** | Tuber 属与产地、法国块菌业与出口比例、产区与政府造林、30 厘米深度与犬/母猪寻获、菌根共生、栽培流程与产出节奏、佩里格块菌与 15 世纪末、假块菌不可食 |
| src_12 | Britannica **Nouvelle cuisine** | 1960—70 年代起源与主张、1972 年命名、1973 年「十诫」、Gault/Millau 与 Le Nouveau Guide 对米其林的挑战、批评阵营 |
| src_13 | Britannica **Hollandaise sauce** | 构成与用途、诺曼底 Isigny 来源与经荷兰回流、最早配方用醋、1758 年版用 bouillon 与面粉不用蛋、19 世纪初定型、1860 Delmonico's、五大母酱、与 béarnaise 的差别 |
| src_14 | Britannica **Brioche** | 高黄油比例（面粉一半至四分之三）、揉三次、三种形制、17 世纪到巴黎、词 15 世纪已在用、「让他们吃 brioche」为误传、圣阿加莎之手地方特产 |
| src_15 | Britannica **Grande cuisine** | 高级菜的定义与审美标准、原料地理基础、凯瑟琳入法与餐桌礼仪、三厨师系统化、高汤与母酱及其变体、烹调法形式化、厨师以技法简写交流 |
| src_16 | Britannica **Cheese** | 制酪原理、约 10:1 浓缩、凝乳酶与乳酸两条路、影响凝乳的变量、熟成前后称谓、化学变化与风味物质、工厂量产的均一化与品种减少、Roquefort 需冷湿洞穴 |
| src_17 | Britannica **Sauerkraut** | 制备工艺与温度/时长、可加葛缕子胡椒粒杜松子、与烟熏肉香肠同食（choucroute garnie、Berner Platte）、罗马已知与 13 世纪再传入 |
| src_18 | Britannica **Macaron** | 原料与馅、与 macaroon 的区别与共同词源、质地与裙边、意大利杏仁饼祖先与威尼斯修院、16 世纪初入法、大革命前后阶级史与南锡 Soeurs Macarons、双片版约 1830 年代、1930 Desfontaines、地区变体 |
| src_19 | **European Commission (DG AGRI)** 地理标志与质量体系说明 | PDO/PGI/GI/TSG 的定义与差别、GI 作为知识产权、成员国保护义务、登记册与规格、2024 年新法规 |
| src_20 | Britannica **Dairy product — Cheese: Ripening** | 三类酶催化的熟成、时长（Brie 一个月 / cheddar 一年以上）、温湿度与含水量、蛋白分解、蓝纹与针刺、表面熟成与 B. linens、非熟成奶酪、按硬度或熟成方式分类 |
| src_21 | Britannica **Fondue** | 瑞士菜定位、三品种奶酪、caquelon 与蒜、白葡萄酒 + 玉米淀粉 + 肉豆蔻或 kirsch、围锅共食与锅巴分食、16 世纪休战共食的**传说** |
| src_22 | Britannica **Aspic** | 以骨汤明胶成冻、可另加商品明胶、镀面与装饰、装饰模具、chaud-froid |
| src_23 | Britannica **Pâté** | 三种含义（填馅酥皮 / en terrine / en croûte）、terrine 为英美 pâté 来源、pâté de Pâques（普瓦图复活节）、pâté de foie gras |
| src_24 | Britannica **Custard** | 蛋奶糊定义与凝固机制、flan / crème caramel、crème brûlée 与 salamander、crème anglaise、Bavarian cream、quiche 为咸味蛋奶糊最著名例子 |
| src_25 | Britannica **Pastry** | 酥皮定义、仅靠蒸汽膨发、short pastry、pâte feuilletée 反复折叠与 12 倍膨胀、酵母裹脂（wienbrod）、高筋粉用于 phyllo/strudel |
| src_26 | Britannica **Baking — Wafers and biscuits / Puff pastry / Choux pastry** | 蒸汽膨发两类、起层酥皮脂肪 ≥30%、硬软麦混用、黄油不宜因融点低、折叠流程与 10 倍膨胀、泡芙皮烫面加蛋与高温定型 |
| src_27 | Britannica **Blue cheese** | 具名品种（Stilton/Roquefort/Gorgonzola）、Roquefort 用母羊乳、三至六个月熟成、洞穴熟成、质地与风味、法国其他蓝纹 |
| src_28 | Britannica **Cider** | 定义与 perry、欧洲/北美名称差异、制作流程与熟成、甜型与干型控制、英国式 scrumpy、法国产量最大且集中在诺曼底与布列塔尼、法国须以鲜苹果汁或苹果梨混合汁发酵并按类别命名、cider apples |
| src_29 | Britannica **Buckwheat** | 蓼科与伪谷物定位、荞麦粉不适合做面包但可做烙饼、干旱丘陵与冷凉气候适应、晚季作物、蜜源/绿肥/饲料多用途 |
| src_30 | Britannica **Braising** | 定义与与炖、加盖烤的区别、先煎上色后覆锅、肉置蔬菜层上、fricasseeing 与 pot-roasting |
| src_31 | Britannica **Stew** | 定义与约 88 摄氏度微沸、褐色与白色两条路、常用根茎蔬菜、增稠方式、ragout à brun / navarin、fricassée / blanquette、法国鱼炖四例 |
| src_32 | Britannica **Sauce** | 酱汁的定义与功能、roux 的构成与作用、液体与固体添加、béchamel 与 espagnole 作为变体之基、面包屑增稠、蛋黄增稠两路、黄油类酱与 beurre noir/beurre blanc、vinaigrette、甜点酱、remoulade 与 aioli |
| src_33 | Britannica **Meringue** | 蛋白霜定义与 1720 Gasparini 的「归功」、作壳与顶、低温烘干、vacherin/dacquoise、意大利蛋白霜 |
| src_34 | Britannica **Restaurant** | 餐馆定义与法国起源、1765 Boulanger 汤铺与得名、与 table d'hôte 及咖啡馆之别、1782 首家豪华餐馆与 Beauvilliers、革命后厨师流出、1804 年 500 多家、Véry 菜单、Café Anglais 与 1867 三皇晚宴、brigade de cuisine 各职 |
| src_35 | Britannica **Auguste Escoffier** | 生平与军中经历、1890 Savoy 建 brigade 与其效率逻辑、1893 peach Melba、1920 荣誉军团、著作与五大母酱、经 Larousse Gastronomique 传播 |
| src_36 | Britannica **Gastronomy** | 美食区的划分、历史脉络（火与共食、罗马奢宴、中世纪粗豪宴席与 Taillevent 以面包增稠、文艺复兴转折）、凯瑟琳与玛丽·德·美第奇的影响、La Varenne《Le Cuisinier françois》(1652) |
| src_37 | Britannica **Marie-Antoine Carême** | 生卒、出身与职业生涯（Talleyrand 12 年、摄政王 2 年、多国宫廷、Rothschild 7 年）、著作四种、艺术与科学并举、大革命推动餐馆业 |
| src_38 | Britannica **Guild** | 行会两类与功能（垄断、质量标准、稳定价格、影响市政）、13 世纪主导市议会、手工业行会的师徒三级制与年限、行会法庭与罚金、主保圣人与会馆、罗马 collegia 与中断 |
| src_39 | Britannica **Tripe** | 反刍动物四胃与刷洗、tripes à la mode de Caen（诺曼底，含牛蹄洋葱胡萝卜）、西班牙与墨西哥对照、英格兰的阶级史 |
| src_40 | **INAO** 官网 | SIQO 制度与八十余年历史、2023 年 1232 个产品的分类数字、52 个乳制 AOP 居欧洲首位、新近承认的奶酪与西南鹅产品 |
| src_41 | Britannica **Pot-au-feu**（策展摘录页） | 字面义与形态；**明确排除**其 AI 摘要的「1791 年」；与越南粉源流的两说并列 |
| src_42 | Britannica **Seafood** | 海鲜范围、蛋白与热量对比、历史保存方式、整只活体烹制与软体动物嫩化处理、生食、避免过熟的经验法则、调味强度与鱼肉质地 |
| src_43 | Britannica **Bread** | 面包定义与 Neolithic 起源、埃及发酵与烤炉、只有小麦黑麦能形成面筋、扁面包与发酵面包分类、长棍属简单白面包、酸面团、白面包与黑面包价格关系（英国约 1865 年）、中世纪行会与 13 世纪法国 20 种面包 |
| src_44 | Britannica **Steak frites** | 法比共享、见于 bistro、部位演变（rump → porterhouse/rib eye/flank）、béarnaise 等酱汁、薯条可粗可细 |
| src_45 | Britannica **Baking** | 烘焙史（干炒 → 粥 → 扁面包 → 烤炉）、发酵的发现、小麦成为首选谷物、酿造与烘焙同源、埃及与罗马的面包师行会、19 世纪后自动化与营养强化 |
| src_46 | Britannica **Consommé**（摘录片段） | 冷食成冻一句，仅作交叉印证 |
| src_47 | Britannica **Choucroute garnie**（策展摘录页） | 以酸菜与肉同上；酸菜工艺与调味与 src_17 一致 |

### 5.1 失败并如实登记（access=unavailable，15 条，零引用）

| ID | 目标 | 失败情形 | 缺口如何被缓解 |
|---|---|---|---|
| un_01 | en.wikipedia **French cuisine** | 连接超时 | 主体由 Britannica French cuisine 承担 |
| un_02 | zh.wikipedia **法国菜** | 连接超时 | 同上 |
| un_03 | fr.wikipedia **Cuisine française** | 连接超时 | 同上 |
| un_04 | Britannica **Quiche** | HTTP 404 | 咸派由 custard + pastry + French cuisine 三页支撑；**洛林版本史仍缺** |
| un_05 | Britannica **Baguette** | HTTP 404 | 由 UNESCO 法棍条目 + bread 支撑；**起源年代仍缺** |
| un_06 | Britannica **Boeuf bourguignon** | HTTP 404 | 由 braising + stew + French cuisine 支撑；**菜名与勃艮第归属史仍缺** |
| un_07 | Britannica **Éclair** | HTTP 404 | 由 baking 的 choux pastry 一节支撑；**命名史仍缺** |
| un_08 | Britannica **Soufflé** | HTTP 404（另一拼写 HTTP 400） | 由 meringue + custard + restaurant 的三皇晚宴菜单支撑；**起源与命名仍缺** |
| un_09 | Britannica **Tarte Tatin** | HTTP 404 | 塔类由 pastry + custard 支撑 |
| un_10 | Britannica **Crêpe** | HTTP 404 | 由 buckwheat 支撑；**布列塔尼薄饼名称与年代仍缺** |
| un_11 | Britannica **Béchamel sauce** | HTTP 404 | 由 sauce + French cuisine 的母酱段落支撑；**白汁命名与人名来源仍缺** |
| un_12 | Britannica **Lent** | HTTP 403（人机校验） | 斋期影响仅由 charcuterie 的「斋期吃腌鱼」一句支撑 |
| un_13 | INAO **AOP 专页** | HTTP 404 | 制度框架由欧盟委员会页 + INAO 首页支撑 |
| un_14 | Alimentarium **Croissant**（食品博物馆） | HTTP 500 | 由 Britannica croissant 支撑 |
| un_15 | UNESCO **Gastronomy 专题页** | HTTP 404 | 由 UNESCO 名录条目支撑 |

## 六、验证输出（未改动的 `app.encyclopedia.import_file`，临时库）

### 6.1 空库单独导入（`%TEMP%\cuisine_fr_verify.sqlite3`）

```
schema_version=2
totals: groups=1  elements=33  element_versions=33  sources=62  source_versions=62  unresolved_relations=215
namespace=cuisine-french  group_id=cuisine-french  schema_kind=human  adapter=human-encyclopedia
legacy_schema=false  status=candidate
elements=33  element_versions=33  sources=62  source_versions=62  tags=82  batches=1
review_status={"needs_review": 33}
detail_status={"needs_detail": 33}
```

`unresolved_relations=215` 是**预期**：空库中 `related_catalog_ids` 指向的 `staples_*` / `produce_*` / `animal_food_*` 等目标尚未导入，按该模块语义记为 `pending`，不写死、不报错。

### 6.2 全库导入后再导入本文件（`%TEMP%\cuisine_fr_verify2.sqlite3`）

先按文件名顺序导入 `docs/human-encyclopedia/*.json` 与 `docs/element-catalog/*.json`（跳过 `shared-themes.json`；`reality-herbs-roots.json` 因无 `elements` 被模块按设计拒绝，与本文件无关），再把本文件导入同一库：

```
cuisine-french: elements=33  sources=62  relations=0  unresolved=0  ambiguous=0  unchanged=33
```

即：**在完整库中本组 215 条关联全部 resolved，无一 pending、无一 ambiguous**；`unchanged=33` 表示内容哈希与首次导入一致（幂等）。导入前的全库对照（同一次运行）：

```
animal-foods 28/32 · craft-supplement 24/34 · cuisine 24/47 · culture-literature 15/7 · flavors 33/37
food-supplement 23/30 · materials 36/24 · names-asian 9/8 · names-european 9/8 · produce 37/49
staples 33/39 · tools 40/38 · cuisine-french 33/62 · eastern-alchemy 20/15 · eastern-biology 21/9
eastern 54/17 · fantasy-races 22/26 · reality-formulae 35/60 · reality-herbs-other 37/48
reality-herbs-western 38/63 · reality-human 31/55 · reality-physical 32/36 · society 53/31
steam-horror 50/46 · western-alchemy 20/43 · western-biology 21/25 · western 54/34
```

### 6.3 静态校验

- 33 条元素 ID 唯一，全部匹配 `^[a-z0-9][a-z0-9_.:-]*$`（`_ID_RE`）。
- 全部 `tags` 匹配 `_TAG_RE`（无中文、无空格、无大写）；`category` 只取 `item` / `institution`，`genre:` 与 `category:` 由模块追加而非手写。
- 全部 `source_ids` 可解析到本文件 `sources`；**无任何 `access: unavailable` 来源被引用**（实测「unavailable sources used: []」）。
- `category` 实测分布：`item` **31 条**、`institution` **2 条**；导入后另自动追加 `category:item` 31 条、`category:institution` 2 条（本文件标签统计中已计入的总数是本组自写标签，不含这两类自动项）。
- `details` 七节齐备且全为非空字符串（缺一节即被 `_prepare_details` 拒绝）。
- 无 `aliases` 首尾空格问题（已修一处）。

## 七、待裁定点（需主审决定，未擅自处理）

1. **potage 的归属**（`cuisine_fr_potage`）：已读来源只描述「浓汤的增稠路线」，**未给 potage 一词的定义**。本条把 potage 当浓汤体系的法语通称使用，属待核。可选：改用中性题名「浓汤与菜泥汤（增稠型汤）」并删去 potage 别名。
2. **fruits de mer 的菜名来源**（`cuisine_fr_seafood_platter`）：本条据「海鲜原料 + 生食/整只烹制 + 冷链」三条来源归纳形态，**「plateau de fruits de mer」作为巴黎餐馆菜名本身未取得来源**。需补法文来源或改为「海鲜冷盘（生食贝类与甲壳类）」这类中性描述。
3. **萨瓦 vs 瑞士**（`cuisine_fr_fondue_savoyarde`）：来源明确写 fondue 为**瑞士**菜；法国一侧的 `fondue savoyarde` 未被该来源描述。当前以「萨瓦」立条并在文中保留国别差异。可选：改名去掉「萨瓦」、或补法国地方来源后再改回。
4. **多条「归纳型」条目的证据等级**（`potee_auvergnate`、`normandy_cider_pork`、`galette_bretonne`、`souffle`、`boeuf_bourguignon`、`pot_au_feu`）：这些条目的**具体菜名、年代或配方**未取得专门来源，条目内的定义由「原料属性 + 技法机制」推得，已在各条 `evidence_and_uncertainty` 中逐条标明并写「属本项目归纳」。是否可接受这种「机制可溯、命名不可溯」的中间状态，请主审裁定；若不可接受，建议另标 `evidence_grade: inferred` 一类字段（当前 schema 无此字段，故未加）。
5. **`pot-au-feu` 的年代**：该来源为 Britannica 策展摘录页，其 AI 生成摘要给出「1791 年」，本条**明确排除**。若主审希望写年代，需另找可核来源。
6. **两处同书内部口径不一**：①起层酥皮膨胀倍率（baking 页 10 倍 / pastry 页 12 倍）；②《Le Cuisinier françois》年份（1651 / 1652）。两处均并列保留、未择一；若主审要求单一值，需指定采信哪一条目。
7. **`kind:` 词表**：本组新造了 `kind:dish` / `kind:technique` / `kind:institution` / `kind:bread` / `kind:cuisine_style`，以及 `role:` / `trade:` 下若干新值（如 `role:service_theatre`、`trade:spice_trade`）。任务只规定了 `kind:dish`，其余为补足检索需要而加；若主审希望 `kind:` 收敛为单一值，需回头统一（`cuisine.json` 与其它组用的是 `food` / `cooking` 这类扁平标签，与本组风格不同，**本组未改动它们**）。
8. **与 `cuisine.json` 标签体例的差异**：`cuisine.json` 用 `["food","cooking",...]` 扁平标签，本组按要求用 `前缀:值`。两组并列入库后检索口径不一，是否需后续统一，属上层决策。
9. **未覆盖的候选菜**：因来源不足或与已定 33 条重叠度高而未立条者——塔特塔丁（tarte Tatin）、可丽饼甜味支、法式咸派的其他地方版本、鹅肝以外的内脏菜（如 andouillette）、阿尔萨斯以外的腌菜体系、法式烤肉（rôti）与野味菜、修道院与医院膳食体系。若需补齐，建议先补法国地方文化机构（Écomusée、地区博物馆）与 INAO 产品页来源。

## 八、边界与不做的事

- 不改动任何其它文件；不建实际数据库；不改 CLI；不碰 Terragenesis；不改地图 / 故事 / 玩家数据库。
- 不写可执行食谱：无克数配比、无温度时长参数、无强制喂食或宰杀操作细节。
- 不把「菜名存在」当作「当前世界存在」，也不据此生成配方、库存或市场价格。
- 全部条目保持 `needs_review` / `needs_detail`；`access: read` 只表示采集侧读过正文，**不代表事实已审定**。
