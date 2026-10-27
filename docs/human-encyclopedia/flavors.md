# flavors 组｜香料、调味、饮料与糖源（候选）

状态：**candidate（采集中，未经内容主审）**。本文件与 `flavors.json` 一一对应：**33 条元素 / 37 条来源**。
本组不宣称穷尽世界香料、调味料或饮料；条目按「在多个地区的历史重要性」挑选，不按品种数量凑数。

- 全部 33 条 `review_status = needs_review`，**没有一条**被标为已核。七节详情写完 ≠ 事实已核。
- 来源 37 条中：`read` **35** 条、`unavailable` **2** 条（未引用于任何条目）、`search_only` **0** 条。
- 其中 `flavors_src_condiment` 与 `flavors_src_beet_sugar` 为策展式摘要页、`flavors_src_fao_coffee_postharvest` 仅抓到目录页——实际取得完整正文的页面为 **32** 条，但这三条仍在 supports 中逐句限定了可支撑范围。

## 边界说明（与相邻组的分工）

| 事项 | 归属 | 本组处理 |
|---|---|---|
| 食用盐 | `materials` | **不设条目**。仅在鱼露、酱油等同条目的 conditions 中说明「盐的供应是其前提」，不重复建条 |
| 新鲜蔬菜、水果、葱蒜 | `produce` | 不设条目。辣椒与甜椒为香料/调味用途收录（干制/制粉/制酱），其作鲜食蔬菜的一面不在本组；茴香球茎、芥菜叶、芜菁等只作交叉提示 |
| 谷物、豆、块根油料、花生橄榄 | `staples` | 不设条目。啤酒/酱油/味噌的原料（大麦、大豆、小麦、米）只提及不建条 |
| 甘蔗、甜菜、蜂蜜 | `flavors`（本组） | 收录为**糖源**条目；甘蔗作为糖料作物从「制糖成品」角度写，不写田间农艺的完整细节 |
| 牲畜、水产、乳蛋 | `animal-foods` | 不设条目。蜂蜜按 `animal_product` 标签收录（蜂类产物），鱼露只写制成品 |

`related_ids` **只指向本组内部 ID**，不指向尚未交付的其他组；跨组的关联一律用文字表述，避免悬空引用。

## 条目总表（33 条）

| # | ID | 名称 | 主要标签 | 可食部位 | 来源数 |
|---|---|---|---|---|---|
| 1 | `flavors_black_pepper` | 胡椒（黑胡椒与白胡椒） | spice / condiment | 果实 | 3 |
| 2 | `flavors_cinnamon` | 肉桂（锡兰肉桂） | spice / condiment | 内层树皮 | 3 |
| 3 | `flavors_cassia` | 桂皮（中国肉桂） | spice / condiment | 树皮、未熟果 | 3 |
| 4 | `flavors_ginger` | 姜（生姜与干姜） | spice / condiment | 根茎 | 3 |
| 5 | `flavors_clove` | 丁香（花蕾） | spice / condiment | 花蕾 | 3 |
| 6 | `flavors_nutmeg_mace` | 肉豆蔻与肉豆蔻衣 | spice / condiment | 种子、假种皮 | 3 |
| 7 | `flavors_cardamom` | 小豆蔻 | spice / condiment | 蒴果、种子 | 3 |
| 8 | `flavors_cumin` | 孜然（枯茗） | spice / condiment | 分果 | 2 |
| 9 | `flavors_coriander_seed` | 芫荽籽（香菜籽） | spice / condiment | 分果（叶另计） | 3 |
| 10 | `flavors_chili_pepper` | 辣椒（含甜椒） | spice / condiment | 果实 | 3 |
| 11 | `flavors_sichuan_pepper` | 花椒 | spice / condiment | 果皮 | 3 |
| 12 | `flavors_star_anise` | 八角（大茴香） | spice / condiment | 果实 | 3 |
| 13 | `flavors_fennel_seed` | 茴香籽 | spice / condiment | 分果（球茎另计） | 3 |
| 14 | `flavors_saffron` | 藏红花（番红花柱头） | spice / condiment | 柱头 | 3 |
| 15 | `flavors_turmeric` | 姜黄 | spice / condiment | 根茎 | 3 |
| 16 | `flavors_mustard` | 芥末（芥籽与芥酱） | spice / condiment | 种子（叶另计） | 3 |
| 17 | `flavors_vanilla` | 香草（香荚兰） | spice / condiment | 未熟果荚 | 3 |
| 18 | `flavors_spice_blend` | 复合香料配方 | condiment / cooking | —（加工品） | 4 |
| 19 | `flavors_vinegar` | 醋 | condiment / processed_material | —（加工品） | 3 |
| 20 | `flavors_soy_sauce` | 酱油 | condiment / processed_material | —（加工品） | 3 |
| 21 | `flavors_fish_sauce` | 鱼露 | condiment / processed_material | —（加工品） | 3 |
| 22 | `flavors_miso` | 味噌 | condiment / processed_material | —（加工品） | 3 |
| 23 | `flavors_tea` | 茶 | beverage / crop | 嫩叶与芽 | 3 |
| 24 | `flavors_coffee` | 咖啡 | beverage / crop | 种子 | 3 |
| 25 | `flavors_cocoa` | 可可与巧克力 | beverage / sweetener | 种子 | 3 |
| 26 | `flavors_beer` | 啤酒 | beverage / processed_material | —（加工品） | 3 |
| 27 | `flavors_wine` | 葡萄酒 | beverage / processed_material | —（加工品） | 3 |
| 28 | `flavors_distilled_spirit` | 蒸馏酒 | beverage / processed_material | —（加工品） | 3 |
| 29 | `flavors_mead` | 蜂蜜酒 | beverage / sweetener | —（加工品） | 2 |
| 30 | `flavors_honey` | 蜂蜜 | sweetener / animal_product | 蜂类产物 | 3 |
| 31 | `flavors_cane_sugar` | 蔗糖（甘蔗糖） | sweetener / processed_material | 茎汁制成品 | 3 |
| 32 | `flavors_beet_sugar` | 甜菜糖 | sweetener / processed_material | 块根制成品 | 3 |
| 33 | `flavors_maple_syrup` | 枫糖浆 | sweetener / processed_material | 树干树液 | 3 |

## 分节要点（每条的完整七节见 JSON）

### 一、旧大陆香料：产地隐瞒与垄断
覆盖 `black_pepper`、`cinnamon`、`cassia`、`ginger`、`clove`、`nutmeg_mace`、`cardamom`、`saffron`。共同结构是：**原产地极度集中 → 转手者垄断信息 → 制度性限产 → 引种打破垄断**。丁香与肉豆蔻的「限缩产地以维持高价」是史料有据的制度性稀缺，不是生态必然。`saffron` 提供另一种极端：单位重量对应数万朵花，采收窗口仅数日，价格由**劳力密度**而非稀缺性决定。

### 二、香料籽与地方配方
覆盖 `cumin`、`coriander_seed`、`fennel_seed`、`star_anise`、`sichuan_pepper`、`spice_blend`。要点是**同名异物**与**同名不同物**：`cassia` 既是香料也是豆科属名；「豆蔻」「茴香」「胡椒」在中文里各覆盖多个科属。`spice_blend` 特别说明：配比、比例、工艺顺序属可执行配方，**规范禁止记录**，本条不给任何数字。

### 三、美洲来的辛辣：时间尺度完全不同
`chili_pepper` 与旧大陆香料构成对照：起源晚近（美洲）、扩散极快（15 世纪末起）。条目明确区分「作物传入」与「饮食转辣」——前者是 16 世纪，后者往往晚到 17—19 世纪且各地不一，属史学争议区。

### 四、发酵调味料：盐与时间是原料
覆盖 `vinegar`、`soy_sauce`、`fish_sauce`、`miso`。共同机制是**用盐与时间换取保存性**：醋靠醋酸菌产酸抑菌（需氧）、酱油与味噌靠曲霉分解蛋白（厌氧盐水）、鱼露靠高盐抑制腐败菌。`miso` 展示了「气候即工艺参数」——同一配方在寒冷地区熟成期被动拉长至两年以上。此组一律**不含**任何温度、盐比、菌种管理与时间配比。

### 五、饮料：工艺而非植物决定分类
`tea`（同叶不同工艺分出三类）、`coffee`（初处理与焙炒分段决定品质）、`cocoa`（发酵+焙炒形成风味，压脂改变商品类别）、`beer`/`wine`/`distilled_spirit`/`mead`（发酵与蒸馏的浓度分野）。`wine` 特意记录：欧洲葡园曾因根瘤蚜近乎全毁，今日「古老产区」的根系多为近代嫁接方案——提醒不要把当下景观当作千年不变。

### 六、糖源：从奢侈品到日用品
`honey`（古代多数地区几乎唯一甜味）、`cane_sugar`（第一个可规模化生产的「纯甜」）、`beet_sugar`（封锁催生的温带替代路线，化学上与蔗糖同一）、`maple_syrup`（以燃料换甜味，19 世纪被廉价蔗糖挤出大众市场后转为地域符号）。四条共同说明：**甜味的价格结构变化会改写整个饮食与社会结构**。

## 来源清单与支撑范围（37 条）

| 来源 ID | 标题 | access | 支撑范围（摘要） |
|---|---|---|---|
| `flavors_src_spice_trade` | spice trade (Britannica) | read | 贸易长时段结构、转手与产地隐瞒、直航竞争、东印度公司年份 |
| `flavors_src_black_pepper` | black pepper | read | 科属、原产、栽培条件、黑/白胡椒工艺差别、以胡椒征贡 |
| `flavors_src_cinnamon` | cinnamon | read | 原产、剥皮套卷与硫熏分级、与 cassia 区别、历史用途与公司贸易 |
| `flavors_src_cassia` | cassia | read | 树皮与桂子、香气更烈、卷筒、产区等级、混称、与豆科同名 |
| `flavors_src_ginger` | ginger | read | 根茎、语源链、传播节点、糖渍保存、无性繁殖不再结籽 |
| `flavors_src_clove` | clove | read | 花蕾、原产摩鹿加、汉廷记载、转口、葡荷垄断与破除、手采晒干 |
| `flavors_src_nutmeg` | nutmeg | read | 种子与假种皮、始果期、晒制六至八周、浸石灰、限产与引种 |
| `flavors_src_cardamom` | cardamom | read | 蒴果与种子、三大产区、入欧时间、绿/黑两类、硫熏漂白 |
| `flavors_src_cumin` | cumin | read | 地中海原产、分果、精油、配方地位、曾作家庭药用 |
| `flavors_src_coriander` | coriander | read | 叶与籽两种商品、原产、分果、早期使用记录 |
| `flavors_src_chili` | chili pepper | read | 美洲起源、多物种独立驯化、墨西哥驯化中心、15 世纪末入欧 |
| `flavors_src_sichuan_pepper` | Sichuan pepper | read | 果皮、物种、麻感机制、五香粉成分、检疫禁令 |
| `flavors_src_star_anise` | star anise | read | 果实结构、原产、茴香脑、近缘有毒种混淆、工业原料用途 |
| `flavors_src_fennel` | fennel | read | 原产、分果与精油、球茎作蔬菜、五香粉成分、入侵种 |
| `flavors_src_saffron` | saffron | read | 柱头、采收与烘干、产出比、主产国、色素、历史传播与染料 |
| `flavors_src_turmeric` | turmeric | read | 根茎、加工顺序、姜黄素、芥末酱着色、孟加拉掺假事件 |
| `flavors_src_mustard` | mustard | read | 白/褐芥、酶促产辣、三种形态、加醋与淀粉、贸易量地位 |
| `flavors_src_vanilla` | vanilla | read | 未熟果荚、熟成流程、授粉限制、结晶判据、与可可饮料关系 |
| `flavors_src_spice_herb` | spice and herb | read | 按部位分类的定义、热带为主、用量小、早期用途、普及过程 |
| `flavors_src_condiment` | condiment | read | **仅**支持「调味料定义」与芥末三形态一句；策展式摘要，范围极窄 |
| `flavors_src_vinegar` | vinegar | read | 两步发酵、醋酸菌、约 4% 酸度、原料风味、通气与速率、用途 |
| `flavors_src_soy_sauce` | soy sauce | read | 由酱演变、制曲与发酵期、中日式原料差、tamari、速成法、钠 |
| `flavors_src_fish_sauce` | fish sauce | read | 定义、鱼盐发酵取液、日晒陈化、各地名称、蚝油类似；条目很短 |
| `flavors_src_miso` | miso | read | 原料与曲、米/麦之分、品类规模、气候与熟成、冷藏保存、用途 |
| `flavors_src_tea` | tea | read | 物种与变种、工艺四阶段与三类、成分、中国/日本/欧洲节点 |
| `flavors_src_coffee` | coffee production | read | 两种栽培种要求、咖啡带、15 世纪引种、三种初处理、含水率、病害 |
| `flavors_src_cocoa` | cocoa | read | 种子加工链、早期证据、原住民做法与货币、传播年表、压脂法 |
| `flavors_src_beer` | beer | read | 定义、早期酿造证据、酒花传播、上下发酵、修道院与工业化 |
| `flavors_src_wine` | wine | read | 物种、发酵与陈放、颜色来源、传播路径、根瘤蚜与嫁接、容器、法规 |
| `flavors_src_distilled_spirit` | distilled spirit | read | 沸点差原理、早期记录、阿拉伯方法、原料先后、设备、管制 |
| `flavors_src_honey` | honey | read | 花蜜转化与去水、蜜源决定色香、结晶、古代甜味地位与用途 |
| `flavors_src_sugarcane` | sugarcane | read | 植物学、生长期、繁殖与宿根、制糖流程概要、副产物、焚田争议 |
| `flavors_src_beet_sugar` | beet sugar | read | **仅**支持化学同一性、温水提汁、不需骨炭、糖厂只产白糖、1808/1811 两条 |
| `flavors_src_maple_syrup` | maple syrup | read | 树种、原住民先行、冻融与开孔、固形物与得率、产季、被蔗糖取代、改良 |
| `flavors_src_fao_coffee_postharvest` | FAO: coffee post-harvest | read | **仅**支持该出版物章节议题（初加工、品质、缺陷、赭曲霉毒素、储藏）；抓取到目录页 |
| `flavors_src_mead_unavailable` | mead（抓取失败 403） | **unavailable** | 无。未引用 |
| `flavors_src_wikipedia_pepper_unavailable` | Black pepper（连接失败） | **unavailable** | 无。未引用 |

## 已核查的结构项（可重算）

- 元素 **33** 条，`id` 全部以 `flavors_` 前缀开头，**无重复**；`name` 无重名。
- 来源 **37** 条，`id` 无重复；**`source_ids` 悬空引用 = 0**（首轮校验发现 4 处 ID 拼写不一致，已修正并复验）。
- 每条元素 `source_ids` ≥ 1，且全部指向本文件 `sources` 内的 `read` 条目；**未引用任何 unavailable / search_only 来源**。
- `details` 七节（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty）**33/33 齐备且非空**。
- `related_ids` 悬空 = 0，自指 = 0；全部指向本组内部 ID。
- `review_status`：**33/33 = needs_review**，`reviewed_detail` 计数为 0。
- 每条至少 2 个标签；标签取自规范列举的 `spice` / `condiment` / `beverage` / `sweetener` / `food` / `crop` / `processed_material` / `animal_product` / `cooking`，未造同义标签。
- 本 Markdown 覆盖全部 33 个元素 ID（见上表）。

## 已知缺口与待证事项（如实记录）

1. **证据厚度不均。** 最薄的三条：`flavors_mead`（专条 403，只能依据蜂蜜与蒸馏酒两页的旁及记述，**不含年代与地区细节**）、`flavors_fish_sauce`（来源本身是短条目，不支持工艺参数与营养数据）、`flavors_spice_blend`（无专条，靠各单一香料条目间接支撑，**配比一律不给**）。
2. **`flavors_src_condiment` 与 `flavors_src_beet_sugar` 两页是策展式摘要，不是完整条目。** 已在 `supports` 中逐条限定其可支撑范围，条目正文也只在此范围内断言。若主审要求更严，这两条可降为 `search_only` 处理。
3. **`flavors_src_fao_coffee_postharvest` 只抓到目录页**，未取得正文论证，因此仅用于确认议题范围，未作为任何细节断言的依据。
4. **未做任何事实核验。** 七节写得再细也不等于已核；`review_status` 一律 `needs_review`，无权升格。
5. **年代断言的处理。** 凡来源给出确切年份（如 1610 / 1669 / 1502 / 1606 / 1657 / 1828 / 1847 / 1876 / 1808 / 1811）已照来源写入；凡来源未给（如「某香料在某地何时成为日常」）一律写明「不作断言」。争议项（谁最先蒸馏、蜂蜜酒是否最古老、某配方是否正统）明确不采用。
6. **有意不写的内容。** 所有可执行工艺参数（温度、盐比、菌种管理、发酵时长细节、蒸馏设备构造、腌制与糖渍配比）均按要求省略；功效与医疗宣称一律只记为「史料中的用法」，不作事实结论；掺假与伪品只作风险提示，不提供鉴别或操作指引。
7. **跨组关联只用文字、不用 `related_ids`。** `related_ids` 全部指向本组内部 ID（悬空=0），与 `produce`（果蔬葱蒜）、`staples`（粮油）、`materials`（盐、石灰）、`animal-foods`（蜂蜜以外的动物产品）的关系一律在正文中文字标注。说明：`staples` / `materials` / `produce` 现已有交付稿（含 `materials_salt`、`staples_olive`、`staples_peanut` 等），但本组尚未补反向链接——这是待办，不是遗漏；补链时需保持两侧同时更新。
8. **未执行 git 操作，未改动 `data/`、源码、StoryPackage 或其他组文件。**
