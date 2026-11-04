# 英国菜系与「抽象」传统菜（cuisine-british 组）

对应 `cuisine-british.json`。状态：**候选资料**，不是数据库记录，也不是任何故事包已采纳的正典。本文件只提供扫读视图、呼应清单与已知不足；完整字段（summary / details 七节 / source_ids 等）**以 JSON 为准**。

- 顶层：`schema_version: 1`、`status: candidate`、`group: cuisine-british`、`genres: ["real_world"]`，条目 ID 前缀 `cuisine_uk_`。
- 共 **16 项**元素，全部 `category: item`；全部 `review_status: needs_review`、`detail_status: needs_detail`。
- 来源 **67 条**：`access: read` **43 条**、`unavailable` **24 条**（失败如实登记，**零引用**，未出现在任何元素的 `source_ids` 中）。
- 每条含 `details` 七节（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty），全部为非空字符串。
- **不做可执行食谱**：只写技法与工序顺序，不给克数配比；不写宰杀、灌制与长期保存的操作参数。

## 一、这个组在收集什么

服务小说与游戏的世界构建（阶级、战后配给、工业城市、地方怪俗）。取舍标准四条：

1. 只收**成品菜、保存制品与饮食制度**，不收食材物种。
2. **重点是「有历史依据的抽象菜」**：每一条都必须能解释「它为什么长成这样」——配给制、工业化与城市贫民饮食、阶级羞耻、地方节庆怪俗、航海与烟熏保存、宗教斋期与血食禁忌。据此排除纯笑话式猎奇，也排除无来源的网络段子。
3. **食材级零重复**：小麦、燕麦、大麦、马铃薯、豌豆、乳、禽蛋、黄油、奶酪、鳕、鲱与小型群游鱼、猪肉、牛肉、羊肉、香肠、火腿与腌熏猪肉、熬炼动物脂肪、干腌鱼、盐、醋、芥末、肉豆蔻、胡椒、啤酒、茶、蔗糖、洋葱、甘蓝、芜菁、胡萝卜、陶制炊具、厨刀、储藏罐、镀锡铁皮、玻璃等均已在 `staples` / `produce` / `flavors` / `animal-foods` / `food-supplement` / `materials` / `tools` 各组立条，本组**只写菜品如何依赖它们**，并用 `related_catalog_ids` 指向。
4. **与 `cuisine.json`、`cuisine-french.json` 无重合**：见第二节。

### 1.1 与既有两组的重合核对

| 既有文件 | 核对结果 |
|---|---|
| `docs/human-encyclopedia/cuisine.json`（24 条） | 24 条全为非英式菜（寿司、饺子、拉面、泡菜、豆腐、比尔亚尼、鹰嘴豆泥、法拉费、库斯库斯、英吉拉、乔洛夫饭、披萨、炖饭、海鲜饭、塔可、tortilla、腌鱼、越南粉、馕、咖喱、萨莫萨、塔马利、北京烤鸭、卡巴布）。**逐条比对：无同名、无同菜。** |
| `docs/element-catalog/cuisine-french.json`（33 条） | 无同名条目。**唯一需要点名的技术同源处**：本组 `cuisine_uk_moulded_gelatin`（模具凝胶冷盘与果冻沙拉，英式家庭／中产餐桌的社会史）与 `cuisine_fr_aspic`（法式咸冻与冻釉技法体系）都涉及明胶成冻。两者**分属不同的社会史与来源**，故分开立条，仅以 `related_ids` 单向引用，不合并、不互相改写。 |

### 1.2 「抽象」成因的一句话总纲

这 16 道菜之所以看起来「怪」，几乎都能归到四条硬约束上：**（a）副产物必须吃掉**（黑布丁用血、哈吉斯用肺、马麦酱用废酵母、鳗鱼冻用河鱼）；**（b）蛋白不足时用碳水与脂扩容**（蟾蜍在洞的面糊、约克郡布丁的滴油盘、卡伦石龙子的薯）；**（c）保存技术决定形态**（烟熏、罐藏、腌渍、成冻）；**（d）地方需要一个可反复表演的仪式**（仰望星空的鱼头、掷黑布丁、Burns Night、涂抹顺序之争）。

## 二、扫读表（16 条）

### 2.1 渔港、保存与「副产物必须吃掉」（6 条）

| ID | 名称 | 地域 | 做法要点 | 为什么长成这样（一句话） |
|---|---|---|---|---|
| `cuisine_uk_stargazy_pie` | 仰望星空派 | 康沃尔 Mousehole | 热盘热脂起酥皮 + 预熟馅 + 整鱼穿皮定位 + 短时高温烤 | 一个村社需要一个每年重演「饥荒被渔获终结」的仪式，鱼头是最省钱的舞台道具 |
| `cuisine_uk_jellied_eels` | 鳗鱼冻 | 伦敦东部 | 切段 + 醋与香料同煮 + 连汤冷却靠自身胶质成冻 | 城市河流曾提供近乎免费的蛋白，成冻是不用冷凝设备的保存法 |
| `cuisine_uk_kippers` | 烟熏鲱鱼与芬南黑线鳕 | 英格兰北部／马恩岛／苏格兰 | 开背 + 盐渍 + 冷熏 + 临食复热 | 鲱鱼离水即腐，所以熏房必须建在港口；浅铜色 vs 染色是唯一的品质判据 |
| `cuisine_uk_cullen_skink` | 卡伦石龙子鱼汤 | 苏格兰东北 | 烟熏鱼另锅以乳煮 + 薯作增稠 + 洋葱不上色 | 熏房、薯田、牧场三样在同一市集能凑齐，才有这碗汤；鱼只是调味级用量 |
| `cuisine_uk_canned_meat` | 罐装肉与午餐肉式制品 | 帝国供应链／英格兰 | 腌制或绞碎调味 + 装罐 + 排气 + 封罐 + 高压蒸汽杀菌 | 军队与远洋需要不靠冷藏的蛋白；同一种技术先当军需、再当配给底牌、最后成为羞耻记忆 |
| `cuisine_uk_black_pudding` | 黑布丁 | 不列颠群岛 | 取血防凝 + 谷物黏结 + 灌肠 + 水煮定型 + 切片煎 | 屠宰当天必须处理掉的副产物，只能就地变成可存放数日的肠 |

### 2.2 碳水扩容、阶级与国族象征（5 条）

| ID | 名称 | 地域 | 做法要点 | 为什么长成这样（一句话） |
|---|---|---|---|---|
| `cuisine_uk_haggis` | 哈吉斯 | 苏格兰 | 内脏剁碎 + 板油与燕麦拌馅 + 装胃袋 + 长时水煮 | 整只羊都要吃掉的资源条件下，下水加燕麦是最经济的正经主食；18 世纪后被一首诗改写成国族象征 |
| `cuisine_uk_toad_in_the_hole` | 蟾蜍在洞 | 英格兰（北方） | 盘脂烧至近冒烟 + 香肠定型 + 倒稀面糊 + 高热短烤 | 一根香肠要喂饱四个人，体积与饱足靠面糊和油补上 |
| `cuisine_uk_yorkshire_pudding` | 约克郡布丁 | 英格兰北部 | 滴油盘预热 + 稀面糊 + 高热短烤 + 出炉即食 | 它是烤肉的副产物：一块肉能喂多少人，取决于这盘面糊能膨多高 |
| `cuisine_uk_steak_kidney_pie` | 牛肉腰子派 / 牛排腰子布丁 | 全英 | 上色 + 肉汁微沸 + 酥皮烤（派）或板油皮蒸（布丁） | 便宜部位长煮 + 内脏与肌肉同馅 + 外壳决定食用场景：皮能携带，皮也能当主食 |
| `cuisine_uk_scotch_egg` | 苏格兰蛋 | 不列颠群岛 | 煮蛋 + 香肠肉无缝包覆 + 粉液屑三重裹 + 油炸或烘烤 | 蛋—肉—壳三层装配，做成可以冷食携带的一餐；三种起源说至今无一方成立 |

### 2.3 工业副产物、餐桌制度与「体面」（5 条）

| ID | 名称 | 地域 | 做法要点 | 为什么长成这样（一句话） |
|---|---|---|---|---|
| `cuisine_uk_marmite` | 马麦酱 | 英国（澳洲 Vegemite 为同族对照） | 酵母自溶浓缩 + 高盐 + 熬至膏状 | 把啤酒废酵母变成耐存放的国民涂抹酱：不占耕地、不与口粮竞争 |
| `cuisine_uk_scone_cream_tea` | 司康与凝脂奶油茶 | 康沃尔／德文郡 | 化学膨松短揉面饼 + 加热静置撇取高脂奶油 + 果酱 | 奶油只能在乳最丰时做、必须隔夜静置，因此它天生是夏季与产乳区的食物 |
| `cuisine_uk_moulded_gelatin` | 模具凝胶冷盘与果冻沙拉 | 英国（兼及北美同型） | 明胶溶胶—凝胶 + 模具倒做 + 温度窗口 | 要冰、要模具、要时间而不是昂贵原料；明胶变廉价粉末后从宴席下沉为家庭甜点 |
| `cuisine_uk_welsh_rarebit` | 威尔士兔子 | 威尔士标签／英格兰餐桌 | 奶酪 + 麦酒 + 酸 + 芥末乳化成酱 + 猛火炙 | 一道「用名字冒充肉」的无肉菜：以奶酪顶肉的经济逻辑确实长期成立，词源则至今不明 |
| `cuisine_uk_pub_counter_snack` | 酒吧柜台小食 | 英格兰 | 腌渍（醋盐香料）+ 油炸淀粉 + 常备化 | 一个只卖酒的场所靠几罐酸的与几袋脆的就能自称「供食」；19 世纪酒吧的分隔让「点单即阶级」成立 |

## 三、与已有食材条目的呼应清单（已有元素 → 菜品如何依赖它）

下表由 JSON 的 `related_catalog_ids` 反向汇总（共 156 条关联，其中 `related_catalog_ids` 111 条指向 34 个不同食材／工具／材料目标，`related_ids` 45 条指向 17 个组内及组外菜品）。单条内部无重复引用；**本组不新建任何食材条目**。

| 已有元素（ID） | 引用次数 | 被哪些菜品依赖 |
|---|---|---|
| `materials_salt`（食盐） | 10 | 仰望星空、鳗鱼冻、黑布丁、哈吉斯、苏格兰蛋、约克郡布丁、马麦酱、烟熏鲱鱼、罐装肉、酒吧小食 |
| `staples_wheat`（小麦，含面粉与面包） | 8 | 仰望星空、蟾蜍在洞、腰子派、苏格兰蛋、约克郡布丁、马麦酱、司康、威尔士兔子 |
| `animal_food_egg`（禽蛋） | 7 | 仰望星空、蟾蜍在洞、苏格兰蛋、约克郡布丁、司康、威尔士兔子、酒吧小食（腌蛋） |
| `produce_onion`（洋葱） | 7 | 鳗鱼冻、黑布丁、哈吉斯、蟾蜍在洞、腰子派、卡伦石龙子、酒吧小食（腌洋葱） |
| `staples_potato`（马铃薯） | 6 | 仰望星空、鳗鱼冻（配薯泥）、哈吉斯（tatties）、罐装肉、卡伦石龙子、酒吧小食（薯片） |
| `animal_food_rendered_fat`（熬炼动物脂肪） | 6 | 黑布丁（板油）、哈吉斯（板油）、蟾蜍在洞、腰子派（板油皮）、约克郡布丁（滴油）、模具冻 |
| `animal_food_butter`（黄油） | 5 | 马麦酱（涂抹平衡）、司康、烟熏鲱鱼、卡伦石龙子、威尔士兔子 |
| `flavors_vinegar`（醋，含麦芽醋） | 4 | 鳗鱼冻、马麦酱（防腐与风味）、威尔士兔子、酒吧小食（腌渍） |
| `flavors_black_pepper`（胡椒） | 4 | 鳗鱼冻、哈吉斯、腰子派、卡伦石龙子 |
| `animal_food_pork`（猪肉） | 4 | 黑布丁（血与肠衣）、腰子派、苏格兰蛋（香肠肉）、罐装肉 |
| `animal_food_milk`（乳） | 4 | 蟾蜍在洞、约克郡布丁、司康（凝脂奶油）、卡伦石龙子 |
| `flavors_beer`（啤酒，含麦酒与麦芽醋基底） | 4 | 腰子派（stout 入肉汁）、马麦酱（酵母来源）、威尔士兔子（麦酒）、酒吧小食 |
| `animal_food_dried_salted_fish`（干腌鱼） | 3 | 仰望星空、烟熏鲱鱼、卡伦石龙子 |
| `animal_food_mutton_lamb`（羊肉） | 3 | 鳗鱼冻（pie-and-mash 的羊肉派）、哈吉斯、腰子派（羊腰子） |
| `staples_oats`（燕麦） | 3 | 黑布丁、哈吉斯、司康（燕麦片配方） |
| `animal_food_sausage`（香肠） | 3 | 黑布丁（同族血肠）、蟾蜍在洞、苏格兰蛋 |
| `animal_food_beef`（牛肉） | 3 | 腰子派、约克郡布丁（配烤牛肉）、罐装肉（腌牛肉） |
| `flavors_cane_sugar`（蔗糖） | 3 | 司康、罐装肉（配方含糖）、模具冻 |
| `animal_food_herring`（鲱与小型群游鱼） | 2 | 仰望星空（pilchard 一类）、烟熏鲱鱼（kipper 主料） |
| `tools_pottery_cooking_pot`（陶制炊具） | 2 | 仰望星空（深盘）、鳗鱼冻（煮锅与容器） |
| `staples_barley`（大麦） | 2 | 黑布丁（大麦黏结支线）、司康（大麦粉配方） |
| `animal_food_ham_bacon`（火腿与腌熏猪肉） | 2 | 腰子派（可加培根）、罐装肉（SPAM 含火腿、爱尔兰培根对照） |
| `flavors_tea`（茶） | 2 | 司康（饮茶制度）、烟熏鲱鱼（可配茶） |
| `animal_food_cod`（鳕与白肉底栖鱼） | 2 | 烟熏鲱鱼（finnan haddie 为黑线鳕）、卡伦石龙子 |
| `tools_storage_jar`（储罐与陶质容器） | 2 | 模具冻（模具与容器）、酒吧小食（腌渍罐） |
| `flavors_mustard`（芥末） | 2 | 威尔士兔子、酒吧小食 |
| `flavors_nutmeg_mace`（肉豆蔻与肉豆蔻衣） | 1 | 黑布丁（香料） |
| `food_supp_turnip`（芜菁） | 1 | 哈吉斯（neeps） |
| `produce_lemon_lime`（柠檬与来檬） | 1 | 烟熏鲱鱼（配柠檬） |
| `materials_tinplate`（镀锡铁皮） | 1 | 罐装肉（罐身与接缝） |
| `produce_apple`（苹果） | 1 | 模具冻（高果胶果汁促凝） |
| `produce_citrus_orange`（柑橘与甜橙） | 1 | 模具冻（高果胶果汁促凝） |
| `materials_glass`（玻璃） | 1 | 模具冻（模具与展示） |
| `animal_food_cheese`（奶酪） | 1 | 威尔士兔子（切达为主料） |

### 3.1 与已有菜式条目的呼应

| 已有条目 | 关系 |
|---|---|
| `cuisine_fr_aspic`（法餐组，咸冻与冻釉体系） | 本组 `cuisine_uk_moulded_gelatin` 单向引用它，说明技术同源而社会史不同。**非重复。** |
| `cuisine.json` 全部 24 条 | 无任意一条与本组同名或同菜。**非重复。** |

## 四、标签统计（实测）

`tags` 只写本组自定的检索前缀，**不手写 `genre:` / `category:`**——`category:item` 由 `app.encyclopedia` 在导入时按 `category` 字段自动追加（导入后实测 16 条）。注意：`genres: ["real_world"]` 写在**文档顶层**，只进入 group meta，**不产生元素级 `genre:` 标签**（实测导入后 16 条元素均无 `genre:` 标签，与法餐组的 md 表述存在口径差异，列为待裁定点）。

自写标签 **297 项**，加自动 `category:item` 16 项共 **313 项**，去重后 **102 个不同标签**。前缀分布（自写部分）：

| 前缀 | 项数 | 说明 |
|---|---|---|
| `kind:` | 18 | dish 14 / bread 1 / condiment 1 / institution 1 / preserved_product 1（两个条目带双 `kind:`） |
| `tradition:` | 16 | 全部 `tradition:western` |
| `cuisine:` | 16 | 全部 `cuisine:british` |
| `era:` | 46 | contemporary 12 / industrial 11 / victorian 8 / interwar 5 / postwar_rationing 5 / early_modern 4 / medieval 1 |
| `role:` | 43 | preservation 7 / daily_staple 5 / pub_food 4 / national_symbol 3 / status_display 3 / tourism_spectacle 3，其余单次 |
| `technique:` | 40 | bake 5 / boil 3 / chill 2 / curing 2 / deep_fry 2 / emulsify 1 / ferment 2 / gelatinize 2 / grill 2 / pastry 2 等 |
| `occasion:` | 29 | everyday 11 / festival 6 / tavern 4 / sunday_dinner 2，其余单次（含 afternoon_tea、postwar 语境下的 famine 等） |
| `trade:` | 28 | butcher 8 / baker 4 / dairy_farmer 4 / fisher 4 / brewer 2 / egg_farmer 2 / merchant 2 等 |
| `class_marker:` | 25 | common 16 / poverty_food 6 / elite 3 |
| `course:` | 25 | main 8 / snack 4 / breakfast 3 / starter 3 / dessert 2 / side 2 / bread 1 / condiment 1 / lunch 1 |
| `region:` | 11 | northern_england 3 / scotland 3 / cornwall 1 / london 1 / wales 1 / southwest_england 1 / northern_europe 1 |

## 五、实际读过并使用的来源（access=read，43 条）

43 条的构成为：**Britannica 40 条**（其中 src_26 `Pickling` 与 src_30 `Burns Night` 为策展／摘录页，其余 38 条为正文条目）、**Atlas Obscura 编辑条目 2 条**（src_38、src_39）、**BBC Good Food 食谱页 1 条**（src_40）。逐条支撑内容已写入 JSON 的 `sources[].supports`，此处只列条目与实际用途。**维基系来源零引用**（全部连接超时，见第六节 un_01／un_02／un_03／un_23）。

### 5.1 菜品与技法（22 条）

| ID | 来源 | 实际支撑 |
|---|---|---|
| src_01 | Britannica **Haggis** | 成分与灌胃煮法；18 世纪起的苏格兰归属；Markham 1615 的英格兰记载；古典渊源；词源不明；Burns 与 Burns Night／Hogmanay；neeps 与 tatties、威士忌 |
| src_02 | Britannica **Black pudding** | 含血香肠与早餐定位；1400 年代起的记录；配方与燕麦／大麦黏结；地方血源；Manchester egg；1652 年 Barlow 的血食主张与 Methodists；掷布丁轶事（来源自标「或属传闻」）与 Ramsbottom 锦标赛；健康与代际差异 |
| src_03 | Britannica **Yorkshire pudding** | 滴油盘做法全流程；18 世纪约克郡食谱书；「刚烈性情」本质化说法不被接受；Hooton 1836「像铅饼」；南北差异；今日烤箱参数（仅记述，不作配方） |
| src_04 | Britannica **Scotch egg** | 三层结构与冷食；三种起源说并列 |
| src_05 | Britannica **Welsh rarebit** | 配方构成；buck rarebit；1725/1785 两个拼写年份；「穷人替代肉」的传说 |
| src_06 | Britannica **Bubble and squeak** | 18 世纪起源、原含肉、剩菜再用、薯为关键、名称由来（**本条未立条，见待裁定点**） |
| src_07 | Britannica **Fish and chips** | 配食地域差异；与工业革命同期；Sephardic 犹太炸鱼渊源；Malin 1863；二战不受配给与 Churchill 的理由（**本条未立条，见待裁定点**） |
| src_08 | Britannica **Scone** | 速发面包、大麦／燕麦、铁板烤、乡间铸铁锅、饮茶制度、加料与切形 |
| src_09 | Britannica **Cornish clotted cream** | 乳脂 55%、加热静置撇取、受保护名称与乳源要求、奶油茶组合、腓尼基传入说（来源自标无证据） |
| src_10 | Britannica **Gelatin** | 溶胶—凝胶可逆、浓度与温度效应、aspic 与模具甜点、果胶对照 |
| src_11 | Britannica **Aspic** | 骨汤天然明胶、可加商品明胶、镀面挂冻与装饰模具、chaud-froid |
| src_12 | Britannica **Pudding** | 英国「布丁」的通称与咸味板油布丁一支、黑／白布丁、约克郡布丁 |
| src_13 | Britannica **Pie** | 派的结构；联合王国自中世纪起以肉、野味、鱼派为主食；tart/flan 之别 |
| src_14 | Britannica **Steak and kidney pie** | 成分、19 世纪、国菜地位、押韵别称 |
| src_15 | Britannica **Steak and kidney pudding** | 板油皮、蒸制、1860 年代首个付印食谱、押韵别称 |
| src_16 | Britannica **Kippers** | 开背盐渍冷熏、浅铜色 vs 染色、产地、配食 |
| src_33 | Britannica **Haddock** | 黑线鳕与 finnan haddie 一句 |
| src_34 | Britannica **Salad** | 「明胶常用于水果或蔬菜沙拉」一句；蔬菜沙拉与 coleslaw |
| src_35 | Britannica **Chowder** | 鱼＋乳＋薯的浓汤结构（仅作技法对照，不作史源） |
| src_36 | Britannica **Batter** | 面糊的液体比例、靠容器成形、蒸汽与气泡膨发、作裹层 |
| src_41 | Britannica **Jelly** | 果汁加甜煮沸慢煨凝结、果胶／明胶／agar、茶点配食 |
| src_42 | Britannica **Pickle** | 北欧冷凉气候的醋调腌液构成、腌渍蔬菜清单 |

### 5.2 保存、工业与制度（12 条）

| ID | 来源 | 实际支撑 |
|---|---|---|
| src_17 | Britannica **Smoking** | 烟的干燥与化学防腐、必须硬木、软木致苦、熏后冷藏、人工烟熏无效 |
| src_18 | Britannica **Canning** | Appert 1809、Durand 1810 与皇家海军、流程七步、约 116℃ 与低酸 120℃、胖罐不可食、营养保留 |
| src_19 | Britannica **SPAM** | 1937 年、命名、猪肩肉、二战量与赫鲁晓夫评价、服役人员来信、销量、配方、夏威夷／菲律宾／韩国、英军俚语与 Monty Python |
| src_20 | Britannica **Rationing** | 配给的五种类型与消费者被劝导购债储蓄；**该页不含英国年份** |
| src_21 | Britannica **Corned beef** | corn 的词源、腌渍与煮制、**英式 salt beef vs 罐装 corned**、爱尔兰牛肉稀缺与爱尔兰培根、美国爱尔兰移民与犹太肉铺、英苏以牛肉为主食与南美进口、爱尔兰盐税 |
| src_22 | Britannica **Potato chip** | 定义、1853 Crum 故事、19 世纪末商业化、1926 Scudder 蜡纸袋、1920 年代机械与连续油炸、Lay 行销、现代调味与压模成形 |
| src_23 | Britannica **Sausage** | 词源与分类、肠衣类型、干／鲜香肠的气候分野、加工法与冷藏要求 |
| src_24 | Britannica **Offal** | 各畜种内脏清单、猪血为黑布丁成分、猪肠作肠衣、内脏的阶级位置与高级菜用法 |
| src_25 | Britannica **Public house** | 普通法的接待义务、都铎马厩与邮政、17 世纪私铸钱币、1800 年代内部分隔与阶级、店名讹变与 Arms、产权结构演变 |
| src_26 | Britannica **Pickling** | 盐与发酵控制、肉可干腌或腌液保存、腌渍蔬菜清单、腌鱼以强腌液密封桶保存 |
| src_27 | Britannica **Vinegar** | 两步发酵、麦芽醋来源、约 4% 乙酸、用途（调味与保存） |
| src_43 | Britannica **Food preservation** | 三路防腐机制、水活度阈值、温度分组 |

### 5.3 地方、人群与叙事（9 条）

| ID | 来源 | 实际支撑 |
|---|---|---|
| src_28 | Britannica **Oatmeal** | 燕麦形态分级、罗马人带入不列颠、1500 年已成重要谷物、苏格兰用于 oatcakes 与 haggis |
| src_29 | Britannica **Vegemite** | **英国 Marmite 的名称来源、酵母与蔬菜提取物、20 世纪初主导预制汤底市场、耐存**；Vegemite 1922/1923、二战海运与 1942 配给（**仅作同族对照，不移到英国 Marmite 上**） |
| src_30 | Britannica **Burns Night** | 1 月 25 日、Burns Supper 与 haggis、风笛与《To a Haggis》、祝酒与《Auld Lang Syne》、威士忌 |
| src_31 | Britannica **Cornwall** | 最偏远郡、渔港与旅游、第二住宅改变乡村社会结构、气候与牧场、锡矿与世界遗产 |
| src_32 | Britannica **Eel** | 只有淡水鳗科具重要经济意义、欧洲鳗约十年成熟、幼鳗上溯 10 月—3 月、皮肤呼吸 |
| src_37 | Britannica **Cuisine** | 气候／经济／宗教法塑造菜系、燃料影响刀工与火候、保存技法靠风味存活、主食跨越阶级 |
| src_38 | Atlas Obscura **Stargazy Pie** | Tom Bawcock's Eve 与 Mousehole、薯与蛋、整鱼头（有时鱼尾）、pilchard、16 世纪传说与猫、点灯活动 |
| src_39 | Atlas Obscura **Jellied Eels** | 18 世纪伦敦的廉价营养餐、pie-and-mash 店的供应、切段与醋／洋葱／胡椒粒／月桂／盐同煮、胶片冻、热辣椒醋与 liquor、二战配给高峰与 100 家以上、泰晤士污染与 1957 年「生物性死亡」 |
| src_40 | BBC Good Food **Cullen skink** | 原料构成与工序顺序（**只取顺序，不转抄克数／容量／时长**） |

## 六、失败并如实登记（access=unavailable，24 条，零引用）

| ID | 目标 | 失败情形 | 缺口如何被缓解 |
|---|---|---|---|
| un_01 | en.wikipedia **Stargazy pie** | 连接超时 | 由 Atlas Obscura + Cornwall 支撑；**地方史细节缺口仍在** |
| un_02 | zh.wikipedia **哈吉斯** | 连接超时 | 由 Britannica haggis／Burns Night／oatmeal 支撑 |
| un_03 | en.wikipedia **Jellied eels** | 连接超时 | 由 Atlas Obscura + Britannica eel／gelatin／aspic 支撑 |
| un_04 | Britannica **Toad in the hole** | HTTP 404 | 技法由 batter + Yorkshire pudding + sausage 支撑；**菜名史与最早文献仍缺（本条最弱处）** |
| un_05 | Britannica **Marmite**（及 -food-product 路径） | HTTP 404 | **英国 Marmite 发明人、年代、厂址、公司史全缺**；仅剩 Vegemite 条目中的英国 Marmite 记述 |
| un_06 | BBC Food 食谱页 | 连接超时 | BBC 域名整体不可达；相关条目改为不给任何配方级参数 |
| un_07 | BBC History **Victorians** | 连接超时 | 维多利亚城市贫民饮食的一手叙述缺位 |
| un_08 | **British Museum** 官网 | 请求超时 | 饮食考古材料缺位 |
| un_09 | **English Heritage** 官网 | 域名解析失败 | 地方史与节庆材料缺位 |
| un_10 | **National Trust** 官网 | 域名解析失败 | — |
| un_11 | **IWM** 英国战时配给专页 | 域名解析失败 | **英国配给的起止年份与逐项配额全缺**，本组所有涉配给处一律不写年份 |
| un_12 | **National Museums Scotland** | HTTP 403（人机校验） | 苏格兰饮食收藏材料缺位 |
| un_13 | **Historic England** | 域名解析失败 | — |
| un_14 | TasteAtlas **Stargazy pie** | HTTP 403（人机校验） | 食谱聚合站配方未被使用 |
| un_15 | Wikibooks **Cookbook: Stargazy Pie** | 连接超时 | 因此本组不给该派任何配方级参数 |
| un_16 | **Alimentarium** 食品博物馆 | HTTP 500 | 博物馆口径的菜式史缺位 |
| un_17 | **The Guardian** 饮食栏目 | 连接超时 | — |
| un_18 | **Historic UK** Stargazy Pie | 连接超时 | 地方节庆的英方通俗叙述缺位，只剩 Atlas Obscura 单一来源 |
| un_19 | Britannica **Cullen skink** 等 | HTTP 404 | **名称语源与地方史仍缺**；仅 BBC Good Food 工序页 + haddock 条目 |
| un_20 | Britannica **clotted cream / British cuisine / afternoon tea** | HTTP 404 | 奶油茶制度史缺位；由 clotted cream + scone + Cornwall 支撑 |
| un_21 | Britannica **jellied eels / jelly dessert / Jell-O / pickled onion / blood sausage / meat pie / whitebait** | HTTP 404 | 各条改由相邻条目承担，正文已点名缺口 |
| un_22 | encyclopedia.com **Rationing** | 连接被远端关闭 | 配给机制改由 Britannica rationing 支撑 |
| un_23 | Wikipedia（simple／m.wikipedia）、Wikiwand、Newworld Encyclopedia 等镜像 | 全部连接超时 | **维基系来源在本组零引用** |
| un_24 | britishfoodhistory.com | HTTP 403（人机校验） | 英国饮食史博客未取得正文 |

## 七、验证输出（未改动的 `app.encyclopedia.import_file`，临时库）

验证脚本位于 `temp://scratch/verify_uk3.py`（一次性脚本，不属于工程代码）。`app/encyclopedia.py` **未作任何改动**，使用其公开 API：`initialize_schema` / `open_writable` / `open_readonly` / `import_file` / `stats` / `search` / `DETAIL_SECTIONS`。

### 7.1 空库单独导入（`scratch/uk_verify1.sqlite3`）

```
=== 6.1 empty-db import ===
adapter=human-encyclopedia namespace=cuisine-british schema_kind=human legacy=False status=candidate
elements=16 element_versions=16 sources=67 source_versions=67 relations=156 unresolved=112 ambiguous=0 idempotent=False
stats(all): {"groups": 1, "elements": 16, "element_versions": 16, "sources": 67, "source_versions": 67, "unresolved_relations": 112}
stats(ns): {"namespace": "cuisine-british", ..., "tags": 102, "batches": 1,
            "review_status": {"needs_review": 16}, "detail_status": {"needs_detail": 16}}
```

`unresolved_relations=112` 是**预期**：空库中 `related_catalog_ids` 指向的 `staples_*` / `produce_*` / `animal_food_*` / `materials_*` / `tools_*` / `flavors_*` 目标尚未导入，按该模块语义记为 `pending`，不写死、不报错。

### 7.2 复导幂等（同一空库再导同一文件）

```
=== 6.1b re-import same file (idempotency) ===
idempotent=True elements=16 element_versions=0 unchanged=16 sources=67 source_versions=0 unresolved=0
stats after re-import: {"elements": 16, "element_versions": 16, "sources": 67, "batches": 1, ...}
```

即：内容哈希一致 → 不新增版本、`unchanged=16`、批次数仍为 1。

### 7.3 七节非空与标签检索

```
seven-section check: rows=16 empty=[]

cuisine:british           total=16  （全部 16 条）
era:postwar_rationing     total=5   canned_meat、jellied_eels、marmite、moulded_gelatin、toad_in_the_hole
class_marker:poverty_food total=6   black_pudding、canned_meat、haggis、jellied_eels、toad_in_the_hole、welsh_rarebit
class_marker:elite        total=3   kippers、moulded_gelatin、scone_cream_tea
role:preservation         total=7   black_pudding、canned_meat、haggis、kippers、marmite、moulded_gelatin、pub_counter_snack
tradition:western         total=16
kind:dish                 total=14
technique:smoke           total=1   kippers
region:scotland           total=3   cullen_skink、haggis、scotch_egg
role:national_symbol      total=3   haggis、marmite、steak_kidney_pie
occasion:tavern           total=4   pub_counter_snack、scotch_egg、steak_kidney_pie、welsh_rarebit

text search 鱼: ['cuisine_uk_cullen_skink', 'cuisine_uk_jellied_eels', 'cuisine_uk_kippers', 'cuisine_uk_stargazy_pie']
```

### 7.4 全库导入后再导入本文件（`scratch/uk_verify2.sqlite3`）

先按文件名顺序导入 `docs/human-encyclopedia/*.json` 与 `docs/element-catalog/*.json`（跳过 `shared-themes.json`）共 **29 份**，再把本文件导入同一库：

```
--- cuisine-british re-imported into full db ---
adapter=human-encyclopedia elements=16 element_versions=16 unchanged=0 sources=67
relations=156 unresolved=0 ambiguous=0 idempotent=False
stats(all): {"groups": 30, "elements": 918, "element_versions": 918, "sources": 1117,
             "source_versions": 1117, "unresolved_relations": 0}
```

即：**在完整库中本组 156 条关联全部 resolved，无一 pending、无一 ambiguous**。

逐份导入时各组的 `unresolved` 数值随**导入顺序**变化（例如 `craft-supplement` 26、`cuisine` 92、`food-supplement` 91、`reality-human` 101、`reality-physical` 87、`cuisine-french` 2、本组在 DB1 空库中 112），这是因为该模块把「目标此刻是否存在」记为 `pending` 而不写死；待目标在同一库中全部就位后，末态 `stats(all).unresolved_relations = 0`（实测）。

> 说明：`element_versions=16`（而非 `unchanged=16`）是因为本组在 DB2 中是**首次**导入；幂等性已由 7.2 单独验证（`idempotent=True`、`element_versions=0`、`unchanged=16`）。

### 7.5 静态校验

- 16 条元素 ID 唯一，全部匹配 `^[a-z0-9][a-z0-9_.:-]*$`（`_ID_RE`）。
- 全部 `tags` 匹配 `_TAG_RE`（无中文、无空格、无大写）；`category` 一律为 `item`；无手写 `genre:` / `category:`。
- 全部 `source_ids` 可解析到本文件 `sources`；**无任何 `access: unavailable` 来源被引用**（实测 `unavailable sources used=[]`）。
- `details` 七节齐备、顺序与 `DETAIL_SECTIONS` 一致、全为非空字符串。
- `related_ids` / `related_catalog_ids` 共 156 条，指向的 34 个 `related_catalog_ids` 目标与 17 个 `related_ids` 目标**全部在现有库中存在**（含跨组的 `cuisine_fr_aspic`）；单条内部无重复。

## 八、待裁定点（需主审决定，未擅自处理）

1. **`cuisine_uk_toad_in_the_hole` 的证据等级最低**：Britannica 无该条目（un_04，404），BBC 亦不可达（un_06），因此**菜名最早用例、年代、以及它与 18 世纪「肉藏面糊」做法的传承关系全部缺来源**。本条的做法机制由约克郡布丁（src_03）与面糊（src_36）的同类机制**移用**而成，已在 `evidence_and_uncertainty` 明写「属本项目归纳」。请裁定：接受「机制可溯、命名不可溯」的中间状态，还是建议把该条降级为 `summary_only` 或移出本组。

2. **英国 Marmite 的公司史完全缺失**：Britannica 的 Marmite 条目路径与 `-food-product` 路径均 404（un_05），唯一可用的 src_29 是 Vegemite 条目，其中关于英国 Marmite 只有四句（名称来自法语 marmite、酵母与蔬菜提取物、20 世纪初主导预制汤底市场、耐存）。因此本条**不写发明人、不写年代、不写伯顿厂址**。若主审认为「无公司史的 Marmite 条目不可用」，建议改为中立题名「酵母提取物涂抹酱（yeast extract）」。

3. **涂抹顺序之争只写「相反」，不指定谁先**：德文郡与康沃尔各自「先奶油／先果酱」的对应关系本次**未取得任何来源**，故 `exceptions` 只写两地相反、并自认正统。若主审要求写清，需补英国地方来源。

4. **英国配给年份一律留空**：IWMs 专页域名解析失败（un_11）、Britannica 的 rationing 页不含英国数据（src_20）。本组所有涉配给的表述均只写「战时／战后配给年代」不写年份。若故事需要时间锚点，需另找可核来源（如 The National Archives 的 Ministry of Food 档案）。

5. **`cuisine_uk_moulded_gelatin` 与 `cuisine_fr_aspic` 的立条边界**：两条技术同源、社会史不同，本组只做单向 `related_ids` 引用。是否需要在 `cuisine-french.json` 的 `cuisine_fr_aspic` 一侧补反向引用？**本任务禁止改动其他文件**，故未做。

6. **`genre:` 标签的口径差异**：`genres: ["real_world"]` 写在文档顶层，导入后只进 group meta，**不产生元素级 `genre:real_world` 标签**（实测 16 条元素均无 `genre:`）。`cuisine-french.md` 第 147 行的表述与此不同（称导入后实测有 `genre:real_world` 33 条）。本组按**实测**写，未改法餐组的 md。是否需要统一（把 genres 写进每个元素，或修正法餐组表述），请主审定。

7. **`kind:` / `role:` / `trade:` 词表扩容**：本组新增 `kind:preserved_product`、`kind:condiment`、`kind:bread`、`kind:institution`，以及 `role:byproduct_use`、`role:meat_substitute`、`role:stretch_protein`、`role:social_lubricant`、`role:military_ration`、`role:postwar_staple`、`role:taboo_food`、`role:contested_symbol`、`role:ceremonial_food`、`role:famine`，与 `trade:publican`、`trade:fishmonger`。任务只规定了 `kind:dish`，其余为补足检索需要而加；若希望收敛请指示。

8. **两条已读全文但未立条的候选**：`src_06`（Britannica **Bubble and squeak**）与 `src_07`（Britannica **Fish and chips**）本次均**实际读过正文并已登记为 `access: read`**，但为控制在 14—16 条区间、且任务清单未列，暂未立条。两条都是有充分来源的英国「阶级／配给」菜（fish and chips 的二战免配给与 Churchill 理由、bubble and squeak 的剩菜再用结构），若需补齐建议下批优先加入——**来源已在本文件中，可直接引用**。

9. **未覆盖的其他候选**（来源不足或未检索成功）：腌蛋（pickled egg）无独立来源，只并入 `pub_counter_snack`；黑布丁的地方变体（Stornoway、Bury、Stockport）只有别名、正文未展开；果冻沙拉的美国中西部／摩门教地方史未取得来源故未写；Cullen skink 的 `skink` 语源缺；凯尔特边缘地区的燕麦菜（oatcake、porridge）未立条以免与 `staples_oats` 重复。

## 九、边界与不做的事

- 只新建本文件与同名 `.json`；不改动任何其它文件；不建实际数据库（验证库建在 `temp://scratch/`）；不改 CLI；不碰 Terragenesis；不改地图／故事／玩家数据库。
- 不写可执行食谱：无克数配比、无温度时长参数（来源给出的工艺参数只在 `sources[].supports` 中作为「来源记述」保留，并注明不构成操作指南）；不写宰杀、灌制、长期保存的操作细节。
- 不把「菜名存在」当作「当前世界存在」，也不据此生成配方、库存或市场价格。
- 全部条目保持 `needs_review` / `needs_detail`；`access: read` 只表示采集侧读过正文，**不代表事实已审定**。
