# 拉丁美洲菜系（cuisine-latin-american 组）

对应 `cuisine-latin-american.json`。状态：**候选资料**，不是数据库记录，也不是任何故事包已采纳的正典。本文件只提供扫读视图、呼应清单与已知不足；完整字段（summary / details 七节 / source_ids 等）**以 JSON 为准**。

- 顶层：`schema_version: 1`、`status: candidate`、`group: cuisine-latin-american`、`genres: ["real_world"]`，条目 ID 前缀 `cuisine_latam_`。
- 共 **24 项**元素（category：item 22、institution 2）；全部 `review_status: needs_review`、`detail_status: needs_detail`。
- 每条带顶层 `primary` 与 `evidence_grade`，没有手写 `primary:` / `evidence:` / `genre:` / `category:` 标签。
- 来源 **27 条**：`access: read` **20 条**、`unavailable` **7 条**（失败如实登记，**零引用**）。已读来源中被元素引用的有 20 条。
- 每条含 `details` 七节，全部为非空字符串。**不做可执行食谱**：只写技法与工序顺序，不给克数配比；不写宰杀与长期保存的操作参数。

## 一、这个组在收集什么

服务小说与游戏的世界构建（美洲原生作物与旧大陆物种交会、殖民与移民、街头饮食）。取舍标准：

1. 只收**成品菜、酱与饮品、制作技法和饮食制度**，不收食材物种。
2. 重点是「它为什么长成这样」：玉米碱化、木薯去毒、冻干保存、辣椒与可可、牛与小麦的引入、街头摊贩经济。
3. **食材级零重复**：玉米、马铃薯、木薯、菜豆、藜麦、番茄、煮食蕉、辣椒、可可、蔗糖、牛猪鸡肉、奶酪、石灰、石磨盘等均已在各食材／材料／工具组立条，本组只写菜品如何依赖它们，并用 `related_catalog_ids` 指向。
4. **与既有菜系组不重名、不重菜**，见 1.1。
5. 来源不足的菜不删，但 `evidence_grade` 定为 `inferred`，并在第七节写明「未取证」。

### 1.1 与既有菜系组的重合核对

| 既有文件 | 核对结果 |
|---|---|
| `docs/human-encyclopedia/cuisine.json`（24 条） | 其中塔可、tortilla、腌鱼（ceviche）、塔马利四条属拉美菜，**本组不重复立条**，只用 `related_catalog_ids` 指向 `cuisine_taco` / `cuisine_tortilla` / `cuisine_ceviche` / `cuisine_tamale`。本组 `cuisine_latam_nixtamalization` 是玉米碱化处理本身，与 tortilla（饼的成品）分开，见第八节。其余 20 条无同名、无同菜。 |
| `cuisine-british.json`（16） / `cuisine-french.json`（33） / `cuisine-chinese.json`（33） | 无同名、无同菜。 |
| `cuisine-european.json`（32） | 无同名条目。该组的玉米糊（polenta）与腌鳕鱼（bacalhau）与交换话题相邻，但不同菜。`cuisine_latam_empanada` 提到它见于西班牙与葡萄牙，不与欧陆组塔帕斯等重合。 |

## 二、扫读表（24 条）

| ID | 名称 | primary | evidence | 价格档 | 一句话 |
|---|---|---|---|---|---|
| `cuisine_latam_mole` | 莫莱酱（mole） | sauce | sourced | shilling | 墨西哥中部与南部的煮制辣椒酱：干辣椒烘过、磨细，再与其它料同煮，酱本身就是这道菜的定义。它与跟在菜旁边的 salsa 不同，更像浓稠的肉汁。 |
| `cuisine_latam_pozole` | 波佐雷汤（pozole） | soup | inferred | groat | 以去壳玉米粒（hominy）为主料、加肉炖成的墨西哥汤或炖菜，上桌时配生菜或甘蓝、辣椒等现加的佐料。 |
| `cuisine_latam_cochinita_pibil` | 尤卡坦烤乳猪（cochinita pibil） | dish | inferred | shilling | 墨西哥东南部尤卡坦一带的腌制慢烹猪肉，传统上与地下坑灶（pib）联系在一起，常包在叶中烹制。 |
| `cuisine_latam_guacamole` | 鳄梨酱（guacamole） | sauce | mixed | groat | 以捣碎的鳄梨和盐为底、常加青柠汁、香菜、洋葱与辣青椒的酱，不经烹煮；名字来自纳瓦特尔语。 |
| `cuisine_latam_atole_champurrado` | 阿托莱与恰姆普拉多（atole / champurrado） | beverage | sourced | groat | 墨西哥的玉米面热饮；加巧克力的版本叫 champurrado，常和 tamal 同食，亡灵节与圣诞季尤其常见。 |
| `cuisine_latam_churro` | 吉事果（churro） | snack | sourced | penny | 挤入热油炸成带棱的长条、裹肉桂糖的点心。起源于西班牙，在墨西哥流行到常被误以为是墨西哥的发明。 |
| `cuisine_latam_nixtamalization` | 玉米碱化处理（nixtamalization） | cooking_technique | sourced | penny | 把玉米放进碱液里煮，去掉外壳并改变质地的处理。它是 tortilla、tamal、atole、pozole 共同的前一道工序，UNESCO 称其提高营养价值。 |
| `cuisine_latam_street_stall_system` | 街头小吃摊体系（拉美） | institution | mixed | priceless | 拉丁美洲城镇里靠街头摊贩卖现做小吃的日常体系。三篇来源（吉事果、阿雷帕、恩帕纳达）都把摊贩写成这些食物的主要销路。 |
| `cuisine_latam_arepa` | 阿雷帕（arepa） | bread | sourced | penny | 哥伦比亚与委内瑞拉流行的扁圆玉米面饼，可烤可炸，夹奶酪、黄油或肉当三明治吃。 |
| `cuisine_latam_empanada` | 恩帕纳达（empanada） | snack | sourced | groat | 面皮折过馅料封口后烤或炸的馅饼，便宜、便携，面皮和馅各地不同。 |
| `cuisine_latam_chuno` | 冻干马铃薯（chuño） | preserved_food | sourced | penny | 安第斯高原用夜间霜冻加白天日晒反复制成的马铃薯干，轻、耐放，可存数年，印加时代已被运往帝国各地。 |
| `cuisine_latam_quinoa_porridge` | 藜麦粥（quinoa porridge） | dish | mixed | groat | 用安第斯主粮藜麦煮成的粥。藜麦不是真正的谷类，种子富含蛋白质与纤维，在秘鲁和玻利维亚产量最大。 |
| `cuisine_latam_dulce_de_leche` | 杜尔塞德莱切（dulce de leche） | sauce | sourced | groat | 把牛奶与糖熬到焦糖色的黏稠甜酱，阿根廷和乌拉圭尤其痴迷，用作抹酱和夹心。 |
| `cuisine_latam_mate` | 马黛茶（mate） | beverage | sourced | penny | 用冬青近缘灌木的干叶浸泡，用金属吸管轮流共饮的南美茶饮，阿根廷、乌拉圭、巴拉圭和巴西南部最流行。 |
| `cuisine_latam_jerk` | 牙买加烟熏烤肉（jerk） | cooking_technique | sourced | shilling | 牙买加的腌制慢烤法：肉裹以多香果与苏格兰帽辣椒为主的腌料，在铺着多香果木的炭火上烤，烟是风味的关键。 |
| `cuisine_latam_sancocho` | 加勒比与美洲炖菜（sancocho） | soup | mixed | groat | 鱼或肉加根茎蔬菜与芭蕉，用芫荽或刺芫荽调味的炖菜，是巴拿马与多米尼加的国菜之一。 |
| `cuisine_latam_cassava_casabe` | 木薯面饼与木薯粉（casabe / farinha） | bread | mixed | penny | 美洲热带的木薯加工食品：木薯要先去毒才能当主食，成品有面饼与粗粉。巴西的木薯粗粉 farinha 是 farofa 的原料。 |
| `cuisine_latam_feijoada` | 巴西黑豆炖肉（feijoada） | dish | inferred | groat | 巴西常被称为国菜的黑豆加腌熏肉炖菜，配木薯粗粉 farofa。 |
| `cuisine_latam_asado` | 阿萨多烤肉（asado） | dish | inferred | shilling | 阿根廷与乌拉圭以明火和炭火烤牛肉等肉类的聚餐传统，既是做法也是社交场合。 |
| `cuisine_latam_chimichurri` | 奇米丘里酱（chimichurri） | sauce | sourced | groat | 阿根廷起源的香草酱：欧芹、牛至、大蒜与红酒醋为基础，配烤肉。文献要到 1950 年代末才见于食谱。 |
| `cuisine_latam_columbian_exchange` | 哥伦布大交换对饮食的影响 | institution | mixed | priceless | 1492 年之后美洲、欧洲、非洲之间动植物与疾病的大规模流动。拉美菜的许多面貌——牛肉与猪肉、小麦、蔗糖——由此而来，玉米、马铃薯、木薯也由此走向全球。 |
| `cuisine_latam_tostones` | 二次油炸青芭蕉片（tostones） | snack | inferred | penny | 用未熟的煮食蕉切段，炸过、压扁、再炸一次的咸味小食。成菜名称与做法只有项目归纳，煮食蕉本身有来源。 |
| `cuisine_latam_lomo_saltado` | 秘鲁炒牛肉（lomo saltado） | dish | inferred | shilling | 秘鲁的炒牛肉条，配洋葱、番茄与辣椒，常与米饭和炸薯条同盘；一般认为带有华人移民带来的炒法。本次没有取得来源。 |
| `cuisine_latam_pao_de_queijo` | 巴西奶酪面包（pão de queijo） | bread | inferred | penny | 用木薯淀粉与奶酪揉成小球烤成的巴西小面包。成品本身没有读到来源，只有木薯可制淀粉这一层。 |

## 三、与已有食材条目呼应

下表列出每条通过 `related_catalog_ids` 指向的既有目录条目（均已核对真实存在）。

| ID | 指向的既有条目 |
|---|---|
| `cuisine_latam_mole` | `flavors_chili_pepper`、`flavors_cocoa`、`produce_tomato`、`tools_saddle_quern`、`cuisine_tamale` |
| `cuisine_latam_pozole` | `staples_maize`、`materials_lime`、`animal_food_pork`、`animal_food_chicken`、`flavors_chili_pepper` |
| `cuisine_latam_cochinita_pibil` | `animal_food_pork`、`flavors_chili_pepper`、`cuisine_taco`、`cuisine_tortilla`、`produce_onion` |
| `cuisine_latam_guacamole` | `food_supp_avocado`、`produce_lemon_lime`、`produce_onion`、`flavors_chili_pepper`、`tools_mortar_pestle`、`cuisine_tortilla` |
| `cuisine_latam_atole_champurrado` | `staples_maize`、`flavors_cocoa`、`flavors_vanilla`、`flavors_cinnamon`、`flavors_cane_sugar`、`cuisine_tamale` |
| `cuisine_latam_churro` | `staples_wheat`、`flavors_cane_sugar`、`flavors_cinnamon`、`flavors_cocoa` |
| `cuisine_latam_nixtamalization` | `staples_maize`、`materials_lime`、`tools_saddle_quern`、`cuisine_tortilla`、`cuisine_tamale` |
| `cuisine_latam_street_stall_system` | `cuisine_taco`、`cuisine_tamale` |
| `cuisine_latam_arepa` | `staples_maize`、`animal_food_cheese`、`animal_food_butter`、`animal_food_egg`、`cuisine_tortilla` |
| `cuisine_latam_empanada` | `staples_wheat`、`staples_maize`、`staples_cassava`、`produce_banana`、`animal_food_beef`、`animal_food_cheese`、`animal_food_rendered_fat` |
| `cuisine_latam_chuno` | `staples_potato` |
| `cuisine_latam_quinoa_porridge` | `staples_quinoa`、`animal_food_milk`、`flavors_cane_sugar` |
| `cuisine_latam_dulce_de_leche` | `animal_food_milk`、`flavors_cane_sugar`、`flavors_vanilla`、`animal_food_cattle` |
| `cuisine_latam_mate` | `flavors_tea`、`flavors_cane_sugar`、`animal_food_milk` |
| `cuisine_latam_jerk` | `flavors_chili_pepper`、`animal_food_chicken`、`animal_food_pork`、`staples_sweet_potato`、`produce_banana`、`materials_charcoal`、`materials_wood` |
| `cuisine_latam_sancocho` | `produce_banana`、`staples_cassava`、`staples_sweet_potato`、`staples_potato`、`staples_maize`、`produce_squash_pumpkin`、`animal_food_beef`、`animal_food_pork`、`animal_food_chicken`、`food_supp_avocado` |
| `cuisine_latam_cassava_casabe` | `staples_cassava` |
| `cuisine_latam_feijoada` | `staples_common_bean`、`animal_food_pork`、`animal_food_ham_bacon`、`staples_rice`、`staples_cassava` |
| `cuisine_latam_asado` | `animal_food_beef`、`materials_charcoal`、`materials_salt`、`animal_food_cattle` |
| `cuisine_latam_chimichurri` | `produce_garlic`、`flavors_vinegar`、`staples_olive`、`flavors_chili_pepper` |
| `cuisine_latam_columbian_exchange` | `staples_maize`、`staples_potato`、`staples_cassava`、`staples_wheat`、`flavors_cane_sugar`、`animal_food_cattle`、`animal_food_pig` |
| `cuisine_latam_tostones` | `produce_banana`、`animal_food_rendered_fat`、`materials_salt` |
| `cuisine_latam_lomo_saltado` | `animal_food_beef`、`produce_onion`、`produce_tomato`、`flavors_chili_pepper`、`staples_rice`、`staples_potato` |
| `cuisine_latam_pao_de_queijo` | `staples_cassava`、`animal_food_cheese`、`animal_food_egg`、`animal_food_milk` |

元素之间的相互引用（`related_ids`）只指向本组 `cuisine_latam_*` 条目，已逐条核对均存在。

## 四、标签与分布统计

- primary：dish 5；sauce 4；snack 3；bread 3；soup 2；beverage 2；cooking_technique 2；institution 2；preserved_food 1
- evidence_grade：sourced 11；inferred 7；mixed 6
- 价格档：groat 9；penny 8；shilling 5；priceless 2
- region：mexico 9；caribbean 6；andes 5；rio_de_la_plata 5；northern_south_america 4；central_america 3；brazil 3
- terrain：workshop 21；farmland 10；tropical_dry_forest 4；import 3；plateau 3；orchard 2；pasture 2；mountain 1；rainforest 1；ocean 1
- sold_by：street_vendor 18；market 9；tavern 4；baker 3；farmer 3；none 2；grocer 2；butcher 2；noble_kitchen 1；confectioner 1；dairy 1；inn_kitchen 1

价格全部是游戏行情估计（各条 `game.note` 已注明），不是史料；`priceless` 的是制度条目。

## 五、已读来源（access=read，20 条）

| ID | 标题 | URL | 被引用 |
|---|---|---|---|
| `cuisine_latam_src_01` | Mole — Encyclopaedia Britannica | https://www.britannica.com/topic/mole-sauce | 是 |
| `cuisine_latam_src_02` | Traditional Mexican cuisine - ancestral, ongoing community culture, the Michoacán paradigm — UNESCO Intangible Cultural Heritage | https://ich.unesco.org/en/RL/traditional-mexican-cuisine-ancestral-ongoing-community-culture-the-michoacan-paradigm-00400 | 是 |
| `cuisine_latam_src_03` | Hominy — Encyclopaedia Britannica | https://www.britannica.com/topic/hominy | 是 |
| `cuisine_latam_src_04` | Guacamole — Encyclopaedia Britannica | https://www.britannica.com/topic/guacamole | 是 |
| `cuisine_latam_src_05` | Atole — Encyclopaedia Britannica | https://www.britannica.com/topic/atole | 是 |
| `cuisine_latam_src_06` | Churro — Encyclopaedia Britannica | https://www.britannica.com/topic/churro | 是 |
| `cuisine_latam_src_07` | Jerk chicken — Encyclopaedia Britannica | https://www.britannica.com/topic/jerk-chicken | 是 |
| `cuisine_latam_src_08` | A Brief History of Jamaican Jerk — Smithsonian Magazine | https://www.smithsonianmag.com/arts-culture/brief-history-jamaican-jerk-180976597/ | 是 |
| `cuisine_latam_src_09` | Sancocho — Encyclopaedia Britannica | https://www.britannica.com/topic/sancocho | 是 |
| `cuisine_latam_src_10` | Plantain — Encyclopaedia Britannica | https://www.britannica.com/plant/plantain | 是 |
| `cuisine_latam_src_11` | Cassava — Encyclopaedia Britannica | https://www.britannica.com/plant/cassava | 是 |
| `cuisine_latam_src_12` | Arepa — Encyclopaedia Britannica | https://www.britannica.com/topic/arepa | 是 |
| `cuisine_latam_src_13` | Empanada — Encyclopaedia Britannica | https://www.britannica.com/topic/empanada | 是 |
| `cuisine_latam_src_14` | Preserved Potatoes Discovered in Inca Site in Southern Peru — Archaeology Magazine | https://archaeology.org/news/2026/06/16/preserved-potatoes-discovered-in-inca-site-in-southern-peru/ | 是 |
| `cuisine_latam_src_15` | Farinha — Encyclopaedia Britannica | https://www.britannica.com/topic/farinha | 是 |
| `cuisine_latam_src_16` | Chimichurri — Encyclopaedia Britannica | https://www.britannica.com/topic/chimichurri | 是 |
| `cuisine_latam_src_17` | Dulce de leche — Encyclopaedia Britannica | https://www.britannica.com/topic/dulce-de-leche | 是 |
| `cuisine_latam_src_18` | Mate — Encyclopaedia Britannica | https://www.britannica.com/topic/mate-beverage | 是 |
| `cuisine_latam_src_19` | Quinoa — Encyclopaedia Britannica | https://www.britannica.com/plant/quinoa | 是 |
| `cuisine_latam_src_20` | Columbian Exchange — Encyclopaedia Britannica | https://www.britannica.com/topic/Columbian-exchange | 是 |

说明：Britannica 若干页面含站内 AI 摘要段，相关条目的证据等级已降为 `mixed`；Archaeology Magazine 的 chuño 报道为转述，其中个别数字只当线索。

## 六、失败来源（unavailable，7 条，零引用）

| ID | 标题 | URL | 失败情况 |
|---|---|---|---|
| `cuisine_latam_src_un_01` | Feijoada — Encyclopaedia Britannica | https://www.britannica.com/topic/feijoada | 返回 HTTP 404，未取得正文。另见搜索摘要，仅作线索，未读正文，零引用。 |
| `cuisine_latam_src_un_02` | Pozole / Asado / Churrasco / Lomo saltado / Cochinita pibil / Tostones 的 Britannica 地址 | https://www.britannica.com/topic/pozole | 逐一尝试均为 HTTP 404 或 403（人机校验），未取得正文；零引用。 |
| `cuisine_latam_src_un_03` | Wikipedia 与 Wikiwand（Feijoada、Asado、Lomo saltado、Chuño、Cochinita pibil、Pozole、Pão de queijo、Guinea pig as food、Tostones、Jerk、Casabe） | https://en.wikipedia.org/ | 本机网络连接超时或被拒，全部未取得正文；仅见到搜索结果摘要，不当作已读来源，零引用。 |
| `cuisine_latam_src_un_04` | Peruvian cuisine — UNESCO Intangible Cultural Heritage | https://ich.unesco.org/en/RL/peruvian-cuisine-00894 | 抓到的只有站点公告与导航，没有条目正文，未取得内容；零引用。 |
| `cuisine_latam_src_un_05` | In Brazil, a meal without beans is incomplete — BBC Travel | https://www.bbc.com/travel/article/20210614-in-brazil-a-meal-without-beans-is-incomplete | 连接超时，未取得正文；零引用。 |
| `cuisine_latam_src_un_06` | Feijoada and Hoppin’ John — Southern Cultures | https://www.southerncultures.org/article/feijoada-and-hoppin-john/ | 请求超时，未取得正文；零引用。 |
| `cuisine_latam_src_un_07` | Pão de queijo / Cuy / Lomo saltado 的机构或大学页面 | https://www.britannica.com/ | 检索只返回餐饮博客、食谱站与 Wikipedia 摘要，未找到可读的机构或博物馆页面；这三条在文中按「无已读来源」处理。 |

## 七、验证输出

- `tools.game_fields.check_element_tags`：24 条全部通过，0 个问题。
- JSON 为 UTF-8 无 BOM、2 空格缩进、末尾换行。
- `app.encyclopedia.import_file` 导入一次性临时 sqlite：elements=24、sources=27、relations=159、ambiguous_relations=[]；再次导入 idempotent=True、unchanged_elements=24。
- 单独导入时 `unresolved_relations` 共 112 条，全部是 `catalog_related`（指向 staples / produce / flavors / animal-foods / materials / tools / cuisine 各组），原因是临时库里只导了本组。这 112 个目标 id 已逐个核对，均存在于 `docs/human-encyclopedia/*.json` 或 `docs/element-catalog/*.json`；`related_ids`（组内引用）无 unresolved。
- `python -X utf8 -m tools.catalog_overlay --check`：输出里**未出现**本组，因为该脚本按 `build.groups_for(...)` 列举已登记的分区，本组尚未登记（见第八节）。本组元素自带 `primary` / `evidence_grade`，不需要旁挂 sidecar。

## 八、待裁定点

1. **分区未登记**：本组文件尚未进入 `build.groups_for` 与 catalog_overlay 的检查列表，需主管决定登记位置与分区名。
2. **primary 词表的归类**：词表里有 `sauce` / `beverage` / `snack` / `cooking_technique` / `institution` / `preserved_food`，本组据此分配。需要确认两处：`dulce_de_leche` 记为 `sauce`（也可视作糖果甜品，词表没有 confection）；`jerk` 记为 `cooking_technique`（它是烹法兼调味体系）。
3. **nixtamalization 与 tortilla 的边界**：本组把玉米碱化作为技法单独立条；若主管希望只在 tortilla 里说明，可删本条，其 related 引用需同步清理。
4. **inferred 的 7 条**：pozole、cochinita pibil、feijoada、asado、tostones、lomo saltado、pão de queijo。其中 lomo saltado 的 `source_ids` 为空，其余只挂有部分原料来源。是否保留，或待补来源后再升级，请裁定。
5. **来源缺口**：Wikipedia / Wikiwand 全站连不上；Britannica 的 feijoada、pozole、asado、churrasco、lomo saltado、cochinita pibil、tostones 地址返回 404 或 403；UNESCO 秘鲁菜页只取到导航；BBC Travel 与 Southern Cultures 超时。
6. **未立条的候选**：churrasco、cuy（豚鼠）、ceviche 的深入条（已有 `cuisine_ceviche`）。cuy 涉及宰杀，且无机构来源，故不立；churrasco 与 asado 近似，也无来源，暂不立。
7. **价格与产地**：`game` 字段（价格、地形、销售者）是游戏行情估计，没有史料依据。

## 九、边界

- 本组是候选资料，未被任何故事包采纳；条目存在不等于当前世界存在，也不自动生成配方、库存或市场价格。
- 不做可执行食谱：无克数、油温、时间、火候；不写宰杀、灌制、长期保存的操作参数。
- 涉及殖民、奴役与原住民人口剧减的条目（jerk、columbian_exchange 等）只引用来源所述层级，不把单一叙述写成定论。
- 国别与地区归属只说「流行地」，不断言起源，除非来源明说。
