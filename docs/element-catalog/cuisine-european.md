# 欧陆西餐分区（cuisine-european）

- 对应 JSON：`docs/element-catalog/cuisine-european.json`
- 状态：candidate；group=`cuisine-european`；genres=`real_world`；id 前缀 `cuisine_eu_`
- 元素 32 条；来源 49 条（access=read 39 条，unavailable 10 条）；全部 `review_status=needs_review`、`detail_status=needs_detail`
- 七节 details 全部非空；每条自带 `game`、`primary`、`evidence_grade`，不用旁挂文件
- 做法只写工序顺序与原理，不给克数配比、精确温度与时长

## 一、这个组在收集什么

欧陆（不含法国、英国）有名的面食、腌肉、面包、甜点、汤、乳酪与饮食制度，重点是中世纪到近代奇幻酒馆能用的平民菜。平民菜（单价 max ≤ 11 便士）共 22 条，占 32 条中的一半以上。

### 与既有分区的重合核对

| 候选 | 处理 | 理由 |
|---|---|---|
| 披萨 | 不立条 | 已有 `cuisine_pizza` |
| 炖饭 | 不立条 | 已有 `cuisine_risotto` |
| 西班牙海鲜饭 | 不立条 | 已有 `cuisine_paella` |
| 酸菜猪肘（Eisbein / Schweinshaxe）及酸菜炖肉 | 不立条 | 酸菜加熏肉香肠的整道菜本质是 `cuisine_fr_choucroute`；本组只立酸菜这一腌制品（`cuisine_eu_sauerkraut`），猪肘没有读到专门来源 |
| 波兰饺子 pierogi | 立条，并区分 | 与 `cuisine_dumpling` 不同：未发酵面皮、半月形、水煮后可再煎，保留为波兰近亲，条内写明区分 |
| 意式腌肉 | 立条，并区分 | 与 `cuisine_fr_charcuterie_lyon` 并行，不合并；关联已建立 |
| 葡式蛋挞 | 立条，并区分 | 与 `cuisine_fr_quiche_lorraine`、`cuisine_fr_creme_caramel_brulee` 不同，关联已建立 |
| 腌鳕鱼 | 立条，并区分 | 与 `cuisine_uk_kippers`（熏鲱）不同处理，关联已建立 |
| 塔帕斯 | 立条，并区分 | 与 `cuisine_uk_pub_counter_snack` 同属酒馆小食习俗，关联已建立 |
| 黑森林蛋糕、瑞典肉丸、开放三明治（smørrebrød）、腌鲱鱼、gravlax | 未立条 | 本次没有读到可用正文来源（维基百科超时，Britannica 对应页 404 或只有摘要壳），宁缺勿凑；见第六节 |

## 二、扫读表

| ID | 名称 | 国别 / 地区 | 主标签 | 价格（便士） | 证据 | 摘要 |
|---|---|---|---|---|---|---|
| `cuisine_eu_dried_pasta` | 干面 | italian / italy | noodle | 1–3 / 一碗 | mixed | 以硬粒小麦胚乳磨成的粗粉加温水揉成硬面团，挤过模孔成型再干燥的面食。形状最初都是为保温或挂酱设计的，干燥后能远运与仓储，所以它既是平民口粮，… |
| `cuisine_eu_lasagne` | 千层面 | italian / emilia_romagna | dish | 3–6 / 一份 | sourced | 宽面片与酱料交替叠放再烘烤的意大利面食。艾米利亚-罗马涅的肉酱加白酱版本是现代形态，那不勒斯和热那亚各有自己的馅和酱，名称本身就带着地域差异… |
| `cuisine_eu_gnocchi` | 马铃薯团子 | italian / veneto | dish | 1–3 / 一盘 | mixed | 以蒸熟的马铃薯泥加面粉、蛋和盐揉成团，切段煮到浮起的意大利北部小团。它是「新作物进入旧菜」的例子：在凉爽的威尼托能种马铃薯，才有这道用薯代面… |
| `cuisine_eu_polenta` | 玉米糊 | italian / northern_italy | dish | 0–1 / 一碗 | mixed | 把谷粉在盐水里煮成稠粥，趁热吃或冷却后切块再烤、煎、炸。它是北意的穷人主食，也是「同一结构换主料」的例子：玉米、栗粉、大麦粉都能做。 |
| `cuisine_eu_italian_salumi` | 意式腌肉 | italian / northern_italy | preserved_food | 6–18 / 一磅 | sourced | 用盐和空气把猪肉变成能放几个月到几年的肉：整腿生火腿、腌猪腩 pancetta 和风干发酵的萨拉米。它们是意大利的冷盘主角，也是做汤底和面酱… |
| `cuisine_eu_focaccia` | 佛卡夏 | italian / liguria | bread | 1–2 / 一块 | mixed | 意大利最古老的面包之一，最早是压平在石板上、埋在炉火余烬下烤的无酵饼。现在的做法加酵母和橄榄油，表面有凹点和盐粒，各地叫法不同。 |
| `cuisine_eu_panettone` | 潘娜托尼 | italian / lombardy | pastry | 12–36 / 一只 | mixed | 用发酵面种发起来的富化面包，含黄油、蛋、糖、葡萄干、糖渍果和柑橘皮，是意大利圣诞和新年的节令糕点。它的圆顶靠倒挂冷却而成，现代法律规定了果料… |
| `cuisine_eu_tiramisu` | 提拉米苏 | italian / veneto_friuli | pastry | 8–12 / 一份 | sourced | 浸过浓咖啡和酒的海绵手指饼，与马斯卡彭奶酪夹层，面上撒可可粉。它是近现代才出现的甜点，起源地存在争议，放进中世纪或近代早期的酒馆会露馅。 |
| `cuisine_eu_gazpacho` | 冷汤 | spanish / andalusia | dish | 1–2 / 一碗 | mixed | 用面包屑、油、醋和生蔬菜拌成的冷汤，原是干活人在热天里补水补盐的食物。番茄和青椒是美洲传入后才进入现代配方，更早的版本用面包、蒜和杏仁。 |
| `cuisine_eu_bacalhau` | 腌鳕鱼 | portuguese / iberia | preserved_food | 4–8 / 一磅 | mixed | 把北大西洋的鳕鱼盐渍晒干，用时反复泡水去盐再烹饪。它是葡萄牙和西班牙的斋日主菜，也是远洋渔业与海外贸易把北海的鱼送到南欧餐桌的证据。 |
| `cuisine_eu_pastel_de_nata` | 葡式蛋挞 | portuguese / lisbon | pastry | 1–3 / 一只 | mixed | 酥皮塔壳里烤凝的奶蛋羹，表面带焦斑。传说它由里斯本贝伦热罗尼莫斯修道院的修士创制，用多余的蛋黄做成，修道院关闭后配方流入民间面包坊。 |
| `cuisine_eu_tapas` | 塔帕斯 | spanish / spain | institution | 1–3 / 一小碟 | mixed | 在酒馆里随酒一起上的小份食物，一碟接一碟，不成正餐。名字意为「盖子」，常见传说是一片面包或火腿盖住酒杯防虫尘，后来演变成一整套站着喝酒、边吃… |
| `cuisine_eu_jamon_iberico` | 西班牙火腿 | spanish / iberia | preserved_food | 12–36 / 一磅 | mixed | 西班牙的整腿风干火腿，高等级的来自在栎林牧场（dehesa）吃橡果的黑蹄猪。它与意大利生火腿同属盐腌风干，区别在猪种、饲养和更长的熟成。 |
| `cuisine_eu_wurst` | 香肠体系 | german / central_europe | preserved_food | 2–6 / 一根 | mixed | 把绞碎的肉、盐和香料灌进肠衣的一大类食品。中欧城市和乡村各有名品，有的鲜煎，有的煮熟，有的风干，是屠宰季之后把零碎肉变成可存可卖的口粮的办法… |
| `cuisine_eu_pretzel` | 椒盐卷饼 | german / southern_germany | bread | 1–2 / 一只 | mixed | 把面绳折成结，先在水中短暂煮一下，刷蛋液撒盐后烤成的咸面包。外皮紧实带光泽，是啤酒馆和街头小贩的常备食物。 |
| `cuisine_eu_wiener_schnitzel` | 炸肉排 | austrian / austria_germany | dish | 6–12 / 一份 | mixed | 把去骨的薄肉片捶薄，裹粉、蛋液和面包屑，用黄油或油煎成金黄的肉排。严格意义的维也纳炸肉排在德奥受法律保护，必须用小牛肉，其他肉要另标。 |
| `cuisine_eu_sauerkraut` | 酸菜 | german / central_europe | preserved_food | 1–2 / 一碗 | mixed | 把切细的白甘蓝与盐分层压进陶缸或木桶，压重物发酵而成的酸菜。它是中欧冬季储存蔬菜的办法，常与烟熏肉和香肠一起上桌。 |
| `cuisine_eu_waffle` | 华夫饼 | belgian / low_countries | pastry | 1–3 / 一块 | mixed | 面糊倒进有格纹的双面铁盘里烤成的饼。比利时与法国的做法加酵母。来源提到 12 世纪的法语诗里已有，它长期是集市和教会节日上的街头小吃。 |
| `cuisine_eu_stroopwafel` | 糖浆华夫 | dutch / gouda | pastry | 1–3 / 一块 | mixed | 把两片薄华夫饼夹上糖浆做成的点心，来源称起于荷兰高达，可能在 18 世纪末出现。它用的是边角料般的原料，是荷兰街头小吃。 |
| `cuisine_eu_gouda` | 高达奶酪 | dutch / gouda | preserved_food | 8–24 / 一磅 | mixed | 荷兰高达一带的半硬质牛奶奶酪，来源称可能始于 12 世纪。扁圆轮形便于码放和运输，表面涂黄色蜡层，市集上以轮计价，是荷兰奶酪贸易的象征。 |
| `cuisine_eu_smorgasbord` | 自助冷餐 | swedish / sweden | institution | 12–36 / 一席 | mixed | 瑞典的自助式宴席：许多冷热小菜摆在一张桌上，客人自取。它源自乡村宴会里每位客人带一份菜的习惯，18 世纪起正餐前有配烈酒和鲱鱼的前菜桌。 |
| `cuisine_eu_surstromming` | 发酵鲱鱼 | swedish / northern_sweden | preserved_food | 2–6 / 一份 | mixed | 波罗的海鲱春季捕捞后盐渍两个月，再装罐继续发酵的瑞典食品。气味强烈，传统上在八月第三个星期四开卖，配杏仁薯、洋葱和薄饼。 |
| `cuisine_eu_borscht` | 罗宋汤 | ukrainian / eastern_europe | soup | 1–3 / 一碗 | mixed | 以甜菜为主料的斯拉夫汤，常说起源于乌克兰。可热可冷，用酸味压住甜菜的甜，配酸奶油和小馅饼，是东欧农家和旅店里最典型的一锅根菜汤。 |
| `cuisine_eu_goulash` | 匈牙利牛肉汤 | hungarian / carpathian_basin | dish | 2–6 / 一碗 | mixed | 匈牙利的锅炖肉菜，经典做法是牛肉或羊肉块与洋葱一起在猪油里煎，再加红椒粉和水炖。传说中它源于牧人，但红椒粉是 18 世纪才加入的，所以早期版… |
| `cuisine_eu_pierogi` | 波兰饺子 | polish / poland | dish | 1–3 / 一盘 | mixed | 波兰的半月形馅饺：未发酵面皮包馅、捏边、水煮，吃时常再煎一下。传说由一位圣徒从基辅带回，也可能经丝路而来，它与中国饺子只是同类形态，不当作同… |
| `cuisine_eu_moussaka` | 穆萨卡 | greek / greece_balkans | dish | 3–8 / 一份 | mixed | 巴尔干和中东的茄子砂锅菜，希腊版把油煎茄片、羊肉番茄酱和奶酪白酱叠在一起烤熟。阿拉伯语里的 musakkʾa 则是一道不含肉的茄子鹰嘴豆炖菜… |
| `cuisine_eu_feta` | 菲达奶酪 | greek / greece | dairy | 2–6 / 一块 | mixed | 希腊用羊奶或山羊奶做的白软奶酪，泡在盐水里存放。《奥德赛》里独眼巨人的羊奶奶酪可能是它的前身；今天它入菠菜酥派和希腊沙拉。 |
| `cuisine_eu_baklava` | 果仁蜜饼 | greek / eastern_mediterranean | pastry | 4–12 / 一块 | mixed | 薄如纸的面皮一层层刷黄油，夹坚果碎，烤脆后浇上蜜和柠檬糖浆。土耳其、希腊和巴尔干都有，是节庆才摆出来的甜点。 |
| `cuisine_eu_kvass` | 卡瓦斯 | russian / russia | beverage | 0–1 / 一杯 | mixed | 用黑麦面包和麦芽发酵出的低度饮料。16 到 19 世纪的俄国很常见，是农民的日常饮品，也是 okroshka 冷汤的底汤，还能当罗宋汤的酸味… |
| `cuisine_eu_mediterranean_diet` | 地中海饮食 | mediterranean / mediterranean | institution | 不可购买 | sourced | 联合国教科文组织把地中海饮食列为非物质文化遗产，强调的不是一张菜单，而是围绕共餐、款待、节庆、集市和手艺传承形成的一套社会习惯。 |
| `cuisine_eu_geographical_indication` | 产地名称保护 | european_union / european_union | institution | 不可购买 | sourced | 欧盟用法律保护产品名称：受保护的原产地名称（PDO）要求整个生产过程都在产地，受保护的地理标志（PGI）只要求至少一个阶段在产地，传统特色保… |
| `cuisine_eu_belgian_beer_culture` | 比利时啤酒文化 | belgian / belgium | institution | 2–6 / 一杯 | mixed | 教科文组织在 2016 年把比利时啤酒文化列入非遗名录。比利时约有一千五百种啤酒，包括特拉普派修道院啤酒；啤酒不仅用来喝，也用来配餐和入菜，… |

## 三、与已有食材条目的呼应

各条 `related_catalog_ids` 只指向已存在的元素，共 61 个不同 id，累计引用 200 次。引用最多的前 12 项：

| 元素 id | 引用次数 |
|---|---|
| `staples_wheat` | 15 |
| `materials_salt` | 15 |
| `animal_food_egg` | 10 |
| `animal_food_cheese` | 10 |
| `animal_food_butter` | 10 |
| `staples_olive` | 8 |
| `animal_food_pork` | 7 |
| `animal_food_milk` | 7 |
| `staples_potato` | 7 |
| `flavors_cane_sugar` | 6 |
| `animal_food_ham_bacon` | 5 |
| `produce_onion` | 5 |

另有指向既有菜品条目的关联（`cuisine_fr_*`、`cuisine_uk_*`、`cuisine_dumpling`、`cuisine_kimchi`、`cuisine_pizza`）与本组内部互指，均已在临时库中解析为 0 未决。

## 四、标签统计

- kind：dish×8、preserved×7、pastry×6、system×3、bread×2、custom×2、soup×1、stew×1、cheese×1、drink×1
- cuisine：italian×8、spanish×3、german×3、greek×3、portuguese×2、belgian×2、dutch×2、swedish×2、austrian×1、ukrainian×1、hungarian×1、polish×1、russian×1、mediterranean×1、european_union×1
- price：penny×14、groat×8、shilling×8、not_for_sale×2
- season：all_year×23、autumn×5、winter×5、summer×4
- sold_by：tavern×17、market×10、street_vendor×10、inn_kitchen×9、baker×8、grocer×7、noble_kitchen×5、farmer×4、butcher×3、fishmonger×2、dairy×2、none×2
- terrain：workshop×31、farmland×19、pasture×14、orchard×7、coast×5、mountain×2、import×2、ocean×2、temperate_forest×2、taiga×1
- primary：dish×8、preserved_food×7、pastry×6、institution×5、bread×2、noodle×1、soup×1、dairy×1、beverage×1
- evidence_grade：mixed×27、sourced×5
- 价格档：penny×14、groat×8、shilling×8、not_for_sale×2

## 五、实际读过并使用的来源（access=read）

| ID | 标题 | URL | 被引用条数 |
|---|---|---|---|
| `cuisine_eu_src_01` | Pasta — Encyclopaedia Britannica | https://www.britannica.com/topic/pasta | 2 |
| `cuisine_eu_src_02` | Lasagna — Encyclopaedia Britannica | https://www.britannica.com/topic/lasagna | 1 |
| `cuisine_eu_src_03` | Gnocchi — Encyclopaedia Britannica | https://www.britannica.com/topic/gnocchi | 1 |
| `cuisine_eu_src_04` | Polenta — Encyclopaedia Britannica | https://www.britannica.com/topic/polenta | 1 |
| `cuisine_eu_src_05` | Prosciutto — Encyclopaedia Britannica | https://www.britannica.com/topic/prosciutto-ham | 2 |
| `cuisine_eu_src_06` | Pancetta — Encyclopaedia Britannica | https://www.britannica.com/topic/pancetta | 1 |
| `cuisine_eu_src_07` | Salami — Encyclopaedia Britannica | https://www.britannica.com/topic/salami | 1 |
| `cuisine_eu_src_08` | Focaccia — Encyclopaedia Britannica | https://www.britannica.com/topic/focaccia | 1 |
| `cuisine_eu_src_09` | Panettone — Encyclopaedia Britannica | https://www.britannica.com/topic/panettone | 1 |
| `cuisine_eu_src_10` | Tiramisu — Encyclopaedia Britannica | https://www.britannica.com/topic/tiramisu | 1 |
| `cuisine_eu_src_11` | Italian cuisine — Encyclopaedia Britannica | https://www.britannica.com/topic/Italian-cuisine | 2 |
| `cuisine_eu_src_12` | Mediterranean diet — UNESCO 非物质文化遗产名录 | https://ich.unesco.org/en/RL/mediterranean-diet-00884 | 3 |
| `cuisine_eu_src_13` | Gazpacho — Encyclopaedia Britannica | https://www.britannica.com/topic/gazpacho | 1 |
| `cuisine_eu_src_14` | Pretzel — Encyclopaedia Britannica | https://www.britannica.com/topic/pretzel | 1 |
| `cuisine_eu_src_15` | Wiener schnitzel — Encyclopaedia Britannica | https://www.britannica.com/topic/Wiener-schnitzel | 1 |
| `cuisine_eu_src_16` | Sauerkraut — Encyclopaedia Britannica | https://www.britannica.com/topic/sauerkraut | 1 |
| `cuisine_eu_src_17` | Sausage — Encyclopaedia Britannica | https://www.britannica.com/topic/sausage | 1 |
| `cuisine_eu_src_18` | Kielbasa — Encyclopaedia Britannica | https://www.britannica.com/topic/kielbasa | 1 |
| `cuisine_eu_src_19` | Waffle — Encyclopaedia Britannica | https://www.britannica.com/topic/waffle | 1 |
| `cuisine_eu_src_20` | Stroopwafel — Encyclopaedia Britannica | https://www.britannica.com/topic/stroopwafel | 1 |
| `cuisine_eu_src_21` | Gouda cheese — Encyclopaedia Britannica | https://www.britannica.com/topic/Gouda-cheese | 1 |
| `cuisine_eu_src_22` | Smorgasbord — Encyclopaedia Britannica | https://www.britannica.com/topic/smorgasbord | 1 |
| `cuisine_eu_src_23` | Surströmming — Encyclopaedia Britannica | https://www.britannica.com/topic/surstromming | 1 |
| `cuisine_eu_src_24` | Borscht — Encyclopaedia Britannica | https://www.britannica.com/topic/borscht | 2 |
| `cuisine_eu_src_25` | Goulash — Encyclopaedia Britannica | https://www.britannica.com/topic/goulash | 1 |
| `cuisine_eu_src_26` | Pierogi — Encyclopaedia Britannica | https://www.britannica.com/topic/pierogi | 1 |
| `cuisine_eu_src_27` | Moussaka — Encyclopaedia Britannica | https://www.britannica.com/topic/moussaka | 1 |
| `cuisine_eu_src_28` | Feta — Encyclopaedia Britannica | https://www.britannica.com/topic/feta | 1 |
| `cuisine_eu_src_29` | Baklava — Encyclopaedia Britannica | https://www.britannica.com/topic/baklava | 1 |
| `cuisine_eu_src_30` | Kvass — Encyclopaedia Britannica | https://www.britannica.com/topic/kvass | 2 |
| `cuisine_eu_src_31` | Sweden: Daily life and social customs — Encyclopaedia Britannica | https://www.britannica.com/place/Sweden/Daily-life-and-social-customs | 2 |
| `cuisine_eu_src_32` | Belgian beer culture — UNESCO 非物质文化遗产名录 | https://ich.unesco.org/en/RL/belgian-beer-culture-01062 | 1 |
| `cuisine_eu_src_33` | Lutefisk — Encyclopaedia Britannica（摘录页） | https://www.britannica.com/topic/lutefisk | 1 |
| `cuisine_eu_src_34` | Iberian ham from Spain — spain.info（西班牙旅游局） | https://www.spain.info/en/discover-spain/jamon-iberico/ | 1 |
| `cuisine_eu_src_35` | The most popular gastronomic routes and tapas in Spain — spain.info | https://www.spain.info/en/top/art-of-tapas-spain/ | 1 |
| `cuisine_eu_src_36` | From Monastery to Mainstream: The Story Behind Portugal’s Iconic Custard Tart — Baking Heritage | https://bakingheritage.com/history/from-monastery-to-mainstream-the-story-behind-portugals-iconic-custard-tart | 1 |
| `cuisine_eu_src_37` | Cod is king in Portugal at Christmas — France 24 / AFP | https://www.france24.com/en/live-news/20241220-cod-is-king-in-portugal-at-christmas | 1 |
| `cuisine_eu_src_38` | Geographical indications and quality schemes explained — European Commission, Agriculture | https://agriculture.ec.europa.eu/farming/geographical-indications-and-quality-schemes/geographical-indications-and-quality-schemes-explained_en | 3 |
| `cuisine_eu_src_39` | Paprika — Encyclopaedia Britannica | https://www.britannica.com/topic/paprika | 1 |

说明：Britannica 条目均只作事实核对与自行转述。葡式蛋挞与盐鳕的新闻、商业网页来源强度较低，条内已按“单一商业网页 / 新闻稿”标注，且保持 needs_review。

## 六、失败来源（零引用）

| ID | 标题 | URL | 情况 |
|---|---|---|---|
| `cuisine_eu_src_un_01` | Pastel de nata — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Pastel_de_nata | 连接超时，对端未响应；同页的 en.m 与 wikiwand 镜像亦失败。未取得正文。 |
| `cuisine_eu_src_un_02` | Bacalhau — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Bacalhau | 连接超时，wikiwand 镜像亦失败。未取得正文。 |
| `cuisine_eu_src_un_03` | Tapas — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Tapas | 连接超时，wikiwand 镜像亦失败。未取得正文。 |
| `cuisine_eu_src_un_04` | Jamón ibérico — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Jam%C3%B3n_ib%C3%A9rico | 连接超时。未取得正文。 |
| `cuisine_eu_src_un_05` | Bratwurst — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Bratwurst | 连接超时。未取得正文。 |
| `cuisine_eu_src_un_06` | Black Forest gateau — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Black_Forest_gateau | 连接超时。未取得正文；因此黑森林蛋糕未立条。 |
| `cuisine_eu_src_un_07` | Swedish meatballs — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Swedish_meatballs | 连接超时。未取得正文；因此瑞典肉丸未立条。 |
| `cuisine_eu_src_un_08` | Smørrebrød — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Sm%C3%B8rrebr%C3%B8d | 连接超时，wikiwand 镜像亦失败。未取得正文；因此开放三明治未立条。 |
| `cuisine_eu_src_un_09` | Gravlax — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Gravlax | 连接超时。未取得正文。 |
| `cuisine_eu_src_un_10` | Stroopwafel — Wikipedia（英文版） | https://en.wikipedia.org/wiki/Stroopwafel | 连接超时。未取得正文（荷兰糖浆华夫改用 Britannica）。 |

另：Britannica 的 `topic/tapas` 讲的是印度宗教苦行，`topic/stollen` 讲的是诗歌曲式，均与食物无关，未使用。

## 七、验证输出

```
BOM False
group cuisine-european ['real_world'] elements 32 sources 49
problems []   # check_element_tags、七节非空、前缀、禁用标签、状态、primary/evidence_grade、正文来源编号逐条检查
unavailable cited []
imported existing 34   # docs/human-encyclopedia 与 docs/element-catalog 其他分区先全部导入
new import: elements 32 sources 49 relations 248 unresolved 0 ambiguous 0
idempotent True   # 重复导入无变化
```

## 八、待裁定

- `tools/encyclopedia_build.py` 的分区清单尚未登记本文件，由主代理处理。
- 西班牙火腿、塔帕斯、盐鳕、葡式蛋挞四条的来源是旅游局页面、新闻稿与商业网页，强度不足，保持 mixed。
- 德语区少了黑森林蛋糕、猪肘，北欧少了开放三明治、肉丸、腌鲱鱼：缺来源，待后续补读。
- 2 条制度类（地中海饮食、产地名称保护）按规范记为 `not_for_sale`；比利时啤酒文化按“一杯”记价。
