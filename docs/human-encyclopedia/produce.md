# 人类生产生活百科 · 蔬菜、水果与坚果（produce）

对应 [`produce.json`](produce.json)。状态：**候选资料**（`schema_version: 1`、`status: candidate`、`group: produce`），全部条目 `review_status: needs_review`。不是数据库实现，也没有被任何故事包采纳为正典；**百科中存在 ≠ 当前世界存在，更不等于人物知道**。

规范见 [`collection-spec.md`](collection-spec.md)。本页只做扫读索引、来源说明与已知限制，**完整七节内容以 JSON 为准**，此处不复制正文。

- 元素总数 **37**（蔬菜 15、水果 17、坚果 5）
- 来源条目 **49**，全部 `access: read`（1 条为策展摘要页，已在 `supports` 与 `rights_note` 中明写范围，见第七节）
- 全部条目 `details` 七节齐全（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty），无固定字数
- 校验结果见第八节

## 一、这个组在收什么

用户授权建立「主要人类生活百科」。本组只收**能影响人物行动、物产条件与事件因果**的蔬菜、水果与坚果，不做完整植物志，不罗列品种凑数。取舍标准是：

1. **按全球多地区的历史重要性选**，不只欧洲与中国：地中海—近东（无花果、石榴、椰枣、橄榄体系外）、南亚（芒果）、东亚（枣、白菜类）、美洲（南瓜类、番茄、辣椒体系外、菠萝）、非洲（西瓜、秋葵）、中亚（苹果、胡萝卜、大蒜）都在内。
2. **一个条目对应一条真实的物产逻辑**：耐储与不耐储、需授粉与不需授粉、需后熟与采后不再后熟、鲜食与加工分线——这些差异决定了它能否成为商品、能走多远、给谁带来收入。
3. **不重复其他组**：橄榄、花生、油菜、向日葵、芝麻、油棕等以油料为主用途者留在 `staples`；辣椒（含甜椒）、胡椒与其他调味作物留在 `flavors`。

## 二、扫读表（按类别）

「类型」列为本组内部分类，用于扫读，不是分类学结论。

### 2.1 蔬菜（15）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| produce_cabbage | 甘蓝 | 同一物种 B. oleracea 分化出叶用/结球/花球/茎用多形态；耐寒可窖藏可腌渍 | src_01/02/03/50 |
| produce_chinese_cabbage | 白菜类 | B. rapa 的叶用群：大白菜结紧实叶球宜腌渍，小白菜叶柄厚脆鲜食 | src_03/01/02 |
| produce_broccoli | 西兰花 | 甘蓝物种的花蕾形态；地中海东部起源、古罗马已有栽培、18 世纪入英美 | src_04/01 |
| produce_cauliflower | 花椰菜 | 未成熟花序形成的「花球」；需约 16 ℃ 稳定温度，干旱只结小球 | src_05/01 |
| produce_onion | 洋葱 | 长日/短日类型决定能否结球；耐储成败取决于采后晾晒（curing） | src_06/51/53 |
| produce_garlic | 大蒜 | 全靠蒜瓣无性繁殖，病害随种蒜传递；秋植越冬、需 3—4 周 curing | src_07/52 |
| produce_lettuce | 莴苣 | 四个变种分别食叶、结球叶或肥大茎；抽薹即品质崩坏 | src_08 |
| produce_spinach | 菠菜 | 耐寒叶菜，含草酸盐；「菠菜」之名被至少六个科的植物共用 | src_09 |
| produce_carrot | 胡萝卜 | 食直根；一般认为约公元 1000 年前后在中亚驯化，13 世纪已至中国与西北欧 | src_10 |
| produce_cucumber | 黄瓜 | 常见蔬菜中需热量最高；水分不匀即变苦；小果多腌渍 | src_11/12 |
| produce_tomato | 番茄 | 植物学浆果而营养按蔬菜；南美野生、墨西哥驯化，16 世纪入欧后先作观赏 | src_16/47 |
| produce_eggplant | 茄子 | 自远古即在东南亚栽培；地中海料理的核心食材；果皮一擦即伤 | src_17 |
| produce_okra | 秋葵 | 只食未熟嫩果；黏液质既是汤羹增稠剂也是口感排斥源 | src_18 |
| produce_squash_pumpkin | 南瓜类 | Cucurbita 属跨多种；夏南瓜与冬南瓜是采收期与贮藏性分野而非物种分野 | src_13/12/14 |
| produce_bottle_gourd | 葫芦 | 嫩果可食、熟果干燥成容器与乐器共鸣体，两用途互斥 | src_14/12 |

### 2.2 水果（17）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| produce_melon | 甜瓜 | C. melo 一个物种含脆皮/网纹/蜜瓜/腌渍等栽培群，多数群野生状态未知 | src_54/12 |
| produce_watermelon | 西瓜 | 原产热带非洲；梵语已有专名、埃及艺术已见其形象，农业史逾四千年 | src_15/12 |
| produce_apple | 苹果 | 原产中亚至阿富汗；几乎全靠嫁接，需异花授粉与按地区匹配需冷量 | src_48 |
| produce_pear | 梨 | 西洋梨与亚洲梨分属不同种；石细胞为属级特征；欧洲传统用榅桲作矮化砧 | src_22 |
| produce_grape | 葡萄 | 鲜食/制干/酿酒三条用途线；修剪去除九成年生长量，是最关键单项操作 | src_21 |
| produce_fig | 无花果 | 隐头花序果树；四个园艺类型按授粉需求划分，缺小蜂则某些类型不结果 | src_19 |
| produce_pomegranate | 石榴 | 食多汁假种皮；原产伊朗一带；只有成熟期高温干燥才能出好果 | src_20 |
| produce_date_palm | 椰枣 | 雌雄异株须人工授粉；四阶段分收；北非与中东可灌溉沙漠的主食与财富 | src_30/31 |
| produce_banana | 香蕉与煮食蕉 | 甜蕉与煮食蕉两条用途线；克隆繁殖致遗传一致，Gros Michel 因巴拿马病退出 | src_32/33 |
| produce_jujube | 枣 | 原产中国、栽培逾四千年；干制后成「木本粮食」；与椰枣毫无关系 | src_36 |
| produce_citrus_orange | 柑橘与甜橙 | 属内杂交频繁；甜橙采后不后熟，采收成熟度即最终品质 | src_26/27/47 |
| produce_lemon_lime | 柠檬与来檬 | 两个不同杂交种；柠檬可多次采收并长期贮藏，来檬酸与糖都更高 | src_28/29/26 |
| produce_peach | 桃 | 可能原产中国；需冷量又不能耐严寒；寿命偏短需定期更新；油桃只是无毛的桃 | src_24/23 |
| produce_plum | 李 | 欧洲李与中国李/日本李两条独立线；果肉紧实含糖高者方可不发酵制干 | src_25/23 |
| produce_mango | 芒果 | 原产南亚；单胚/多胚决定能否留种；1909 年芽接商业化才形成现代产业 | src_49 |
| produce_pineapple | 菠萝 | 多花愈合的聚花果；16 世纪经葡萄牙人传遍热带；罐藏改变其流通形态 | src_34 |
| produce_coconut | 椰子 | 椰肉/椰水/椰干/椰油四条产品线；果实易漂浮；椰棕来自果壳 | src_35 |

### 2.3 坚果（5）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| produce_walnut | 核桃 | 波斯核桃 J. regia；果实是核果而可食部分是种子；果材两用 | src_45/47 |
| produce_chestnut | 栗 | 栗属七种；富淀粉属「木本粮食」；美洲栗因 20 世纪初自亚洲传入的栗疫病近灭绝 | src_37/47 |
| produce_almond | 扁桃 | 甜/苦两个变种，苦扁桃含苦杏仁苷须去氢氰酸；中文「杏仁」名实易混 | src_38/23 |
| produce_hazelnut | 榛 | 榛属约 15 种；冬末先花后叶；filbert/hazelnut/cobnut 的旧分法被证明误导 | src_39 |
| produce_pistachio | 开心果 | 据信原产伊朗、暖温带旱地；雌雄异株需配置雄树。**仅据摘要页，证据强度最弱** | src_46 |

## 三、分组边界（刻意回避重复）

| 情形 | 处理 |
|---|---|
| 橄榄、花生、油菜、向日葵、芝麻、油棕、亚麻 | **不立条**，留在 `staples`（主用途为油料） |
| 辣椒（含甜椒）、胡椒、其他调味作物 | **不立条**，留在 `flavors`。本组不以甜椒另立全物种重复条目；甜椒与辣椒的物种归属与用途分野在 `flavors_chili_pepper` 中说明，本组只在相关条目里指出「辣椒类归 flavors」 |
| 食用盐、石灰等材料 | **不立条**，归 `materials`（`materials_salt`、`materials_lime`）。本组只在腌渍、curing、盐渍发酵类条件中提到盐的作用，不重复立条 |
| 来檬（citrus lime）vs 石灰（材料 lime） | **跨组同名，非重复条目**：`produce_lemon_lime` 与 `materials_lime` 的别名都含 "lime"，按名称检索会撞名，须按组与上下文区分，不能互相替代 |
| 椰子油、核桃油、榛子油 | 只在相应条目内以 `oil_crop` 标签与一句话点明油料用途，榨油工艺归 `staples` 与工艺类条目 |
| 甘蓝 vs 白菜类 | 同一「结球」外形分属 B. oleracea 与 B. rapa 两个物种，**分两条**，并在 `exceptions` 中互指防混 |
| 西兰花 vs 花椰菜 | 同物种不同品种群、食用器官同属花序变态，但成熟窗口与采后表现不同，**分两条** |
| 椰枣 vs 枣 | 棕榈科 vs 鼠李科，**分两条**，两条均在 definition 首段写死名称区分 |
| 扁桃（巴旦木）vs 杏的杏仁 | 不同物种，扁桃条内专设名称风险段 |
| 香蕉 vs 煮食蕉 | 合为一条，用用途线与 `staple_substitute` 标签表达，不另立物种重复条目 |
| 南瓜/西葫芦/笋瓜 | 合为一条「南瓜类」，definition 明写俗名跨 C. pepo / C. moschata / C. maxima 多个物种 |

## 四、写作口径（全组一致）

1. **物种与品种范围严谨**：能可靠确定时给学名与所属种/品种群；条目覆盖多个物种时（甘蓝、白菜类、南瓜类、甜瓜、葡萄、李、梨、栗、榛、柑橘）在 definition 首段写出边界，不把共性硬套每一个。
2. **起源、驯化、传入、普及分开写**，各段单列；来源有争议或口径不一（香蕉两套起源说、胡萝卜驯化年代、桃「可能原产中国」、无花果驯化年代）明写「有争议/可能」并并列保留，**不定死年代**。
3. **不把某时代某地区有某作物当全球默认**：欧洲—大西洋脉络与东亚脉络分别标注，不互相推断（葡萄、番茄、柠檬、芒果、菠萝、椰枣、柑橘均如此处理）。
4. **可食部位与定性限制**：写清食叶/鳞茎/直根/嫩果/种子/胚乳；生熟限制、草酸、茄碱、苦杏仁苷、霉菌毒素、树坚果过敏等只作**定性风险提示**，不提供任何去毒方法、用量、配比或医疗建议。
5. **来源支撑与创作推演分开**：`evidence_and_uncertainty` 只写来源能支撑什么与缺口；`story_uses` 只写可用于叙事的机制，不冒充史实。
6. **栽培与保存条件定性化**：给出气候带、温度/日照/土壤/水分的条件关系，以及采收、干燥、curing、贮藏、运输的必要条件与代价，不写可执行工艺参数。

## 五、来源构成

- 大学推广站 **6**：University of Minnesota Extension（甘蓝 src_50、洋葱 src_51、大蒜 src_52）、NC State Extension Plant Toolbox（苹果 src_48、Allium cepa src_53、Cucumis melo src_54）
- 专业参考书（Purdue NewCROP 网页版）**3**：Duke《Handbook of Energy Crops》椰枣；Morton《Fruits of Warm Climates》芒果、香蕉
- 国际组织 **1**：FAO Agricultural Services Bulletin 149《Handling and Preservation of Fruits and Vegetables by Combined Methods for Rural Areas》（采后处理与保存的框架性依据）
- 第三方百科（Encyclopaedia Britannica）**39**：作为植物学形态、物种范围与部分历史节点的补充来源
- 全部 49 条来源 `access` 均为 `read`；无 `search_only`、无 `unavailable` 登记
- 另：Kew POWO 曾用于名称与异名核查，但**未作为任何条目的 source_ids 登记**（未支撑具体断言），故不计入 49 条

## 六、来源清单（49 条，全部 access=read）

标题与 URL 的完整写法、以及每条具体支撑哪些陈述，见 `produce.json` 的 `sources` 数组；此处只列可扫读的一行索引。

### 6.1 栽培与采后专题参考（9）

| ID | 来源 | 性质与用途 |
|---|---|---|
| produce_src_48 | Malus domestica（苹果）— NC State Extension Plant Toolbox | 栽培事实：原产地、砧木、需冷量、授粉树 |
| produce_src_50 | Growing cabbage in home gardens — University of Minnesota Extension | 甘蓝栽培、裂球、0—4 ℃/95% 湿度窖藏 |
| produce_src_51 | Growing onions in home gardens — University of Minnesota Extension | 洋葱长日/短日、pH、收获与 curing、储藏发芽温度 |
| produce_src_52 | Growing garlic in home gardens — University of Minnesota Extension | 大蒜秋植、停氮、停水、采收判据、curing、轮作 |
| produce_src_53 | Allium cepa（洋葱）— NC State Extension Plant Toolbox | 起源地不明、5000 年记载、毒性记录（只作提示） |
| produce_src_54 | Cucumis melo（甜瓜）— NC State Extension Plant Toolbox | 栽培群体系、原产范围、传粉、种子风险提示 |
| produce_src_30 | Date palm — Encyclopaedia Britannica | 椰枣雌雄异株、人工授粉、四成熟阶段、全株用途 |
| produce_src_31 | Phoenix dactylifera L. — Duke, Handbook of Energy Crops（Purdue NewCROP） | 品种名录与成分（单一文献口径，未交叉核验） |
| produce_src_49 | Mango — Morton, Fruits of Warm Climates（Purdue NewCROP） | 芒果起源与传播链、单胚/多胚、芽接技术转折（产量数据过时未采用） |

### 6.2 国际组织与名称核查（2）

| ID | 来源 | 性质与用途 |
|---|---|---|
| produce_src_47 | FAO Agricultural Services Bulletin 149（2003）：Handling and Preservation of Fruits and Vegetables by Combined Methods for Rural Areas | 采后处理与保存的框架：成熟度、curing、预冷、包装、贮藏、腐烂控制；不转述工艺参数 |
| produce_src_02 | Head cabbage — Encyclopaedia Britannica | 结球甘蓝形态与用途；兼作与 B. rapa 的物种区分佐证 |

### 6.3 第三方百科·植物学与历史（38）

| ID | 来源 | 主要支撑 |
|---|---|---|
| produce_src_01 | Cabbage（Brassica oleracea） | 一源多形态分类、耐寒、中世纪北欧硬头结球 |
| produce_src_03 | Chinese cabbage | 大白菜/小白菜两支变种与形态用途 |
| produce_src_04 | Broccoli | 起源地、古罗马栽培、18 世纪入英美、60—150 天 |
| produce_src_05 | Cauliflower | var. botrytis、16 ℃ 稳定温度、束叶遮光、病害 |
| produce_src_06 | Onion | 物种、鳞茎成因、花茎与小球芽、商业品种类型 |
| produce_src_07 | Garlic | 原产中亚、蒜瓣数、挥发油成分、药用民俗 |
| produce_src_08 | Lettuce | 四个变种、抽薹、耐运性差异与市场格局 |
| produce_src_09 | Spinach | 耐寒叶菜、草酸盐、20 世纪 20 年代推广、同名异物清单 |
| produce_src_10 | Carrot | 野生型分布、约 1000 年驯化说、13 世纪栽培、根色多样 |
| produce_src_11 | Cucumber | 需热量最高、水分不匀致苦、pepo、病害 |
| produce_src_12 | Cucurbitaceae | 科级特征：低温敏感、pepo、养分低 |
| produce_src_13 | Squash（Cucurbita） | 新大陆起源、夏/冬南瓜分野、各类型所属物种 |
| produce_src_14 | Gourd | Lagenaria siceraria、硬壳成因、器物与乐器清单 |
| produce_src_15 | Watermelon | 原产热带非洲、梵语与埃及证据、选择导致的现代类型 |
| produce_src_16 | Tomato | 起源与驯化地、入欧后观赏阶段、北美各时间节点 |
| produce_src_17 | Eggplant | 原产东南亚、地中海料理用途、果色变异、英文名来由 |
| produce_src_18 | Okra | 只食嫩果、黏液质增稠、gumbo、种子代咖啡 |
| produce_src_19 | Fig | 隐头花序、四园艺类型、小蜂传粉、品种命名混乱 |
| produce_src_20 | Pomegranate | 假种皮、原产伊朗一带、成熟期高温干燥出好果 |
| produce_src_21 | Grape（Vitis） | 用途三分、修剪 90—95%、历史节点、根瘤蚜与砧木 |
| produce_src_22 | Pear（Pyrus） | 西洋梨/亚洲梨、石细胞、榅桲砧、病害 |
| produce_src_23 | Prunus | 属级范围与核果类关系 |
| produce_src_24 | Peach | 需冷量与耐寒下限、疏果、起源与 19 世纪商业化 |
| produce_src_25 | Plum | 欧洲李/日本李两线、可制干条件、耐贮性决定鲜销 |
| produce_src_26 | Citrus | 属与杂交学名、hesperidium 结构 |
| produce_src_27 | Orange | 采后不后熟、丰产年限、育苗流程、1920 年消费转折 |
| produce_src_28 | Lemon | 杂交种身份、传入时间、年采次数、采后分级与副产物 |
| produce_src_29 | Lime | 两类来檬、传播时间线、酸糖比较、同名类型 |
| produce_src_32 | Banana | 6500 年前新几内亚驯化、克隆脆弱性、TR4、基因组命名 |
| produce_src_33 | Banana — Morton, Fruits of Warm Climates | 印度—马来亚起源说、16 世纪入南美、太平洋路线、克隆名录 |
| produce_src_34 | Pineapple | 聚花果成因、葡萄牙传播节点、罐藏与种植密度 |
| produce_src_35 | Coconut | 胚乳结构、漂浮传播、copra 与 coir、主要生产国 |
| produce_src_36 | Jujube | 原产中国 4000 年、两栽培种、加工与「中国枣」由来 |
| produce_src_37 | Chestnut（Castanea） | 七种与分布、总苞结构、美洲栗栗疫病、同名异物清单 |
| produce_src_38 | Almond | 甜/苦变种与苦杏仁苷、授粉依赖、新旧大陆栽培形态对比 |
| produce_src_39 | Hazelnut（Corylus） | 属范围、冬末花序、总苞与旧分法的误导性 |
| produce_src_45 | English walnut（Juglans regia） | 原产伊朗、核果而非坚果、土壤要求、木材用途 |
| produce_src_46 | Pistachio（Pistacia vera） | **策展摘要页，未获全文**；只支撑概括性事实 |

## 七、已知限制（使用前必读）

1. **`produce_pistachio` 证据强度最低**：所据 Britannica 页面为策展摘要 + 旁及段落，**未取得全文**。该条 `access` 记为 `read`（采集时确实读到该页存在的内容）但可支撑范围仅限摘要内容，已在 `supports`、`rights_note` 与 `evidence_and_uncertainty` 中逐项列出；本组**没有**把摘要页当作全文条目使用，该条也只保留了摘要能支撑的字段（物种、原产地传闻、栽培带、树高、风媒传粉与配雄树、种子风味与用途），品种、年代、工艺一律留空。引用前建议补全文来源。
2. **`access: read` 表示「采集时确实读到该页正文」**，不是许可授权，也不是准确性保证。`rights_note` 已逐条注明来源性质与转述范围。
3. **多数条目的历史部分只能到「范围性表述」**：东亚传入年代、各地普及时间、驯化精确年代在多条中标注为「未获来源」。这是刻意的留白，不是遗漏——见第八节。
4. **两处来源数据已过时未采用**：Morton 的芒果与香蕉章中的产量/面积数字为 20 世纪 80 年代口径，本组不引用其数量，仅用其史实叙述。
5. **一处来源数字仅单一文献口径**：Duke 的椰枣成分数据未与其他来源交叉核验，仅在 `produce_date_palm` 中作名录与量级引用。
6. **未做的事**：不做危险野采鉴定、不提供药用与疗效结论、不提供加工配比或工艺参数。原条目中出现的民间用法（大蒜辟邪、秋葵外敷、菠菜补铁宣传）只作为「史实/民俗记述」保留，并明写不背书。

## 八、校验记录

校验脚本对 `produce.json` 逐项检查，结果 **0 问题**：

| 检查项 | 结果 |
|---|---|
| JSON 可解析（Node `JSON.parse`） | 通过，221311 字节，763 行（UTF-8 无 BOM） |
| 顶层字段 `schema_version=1` / `group=produce` / `status=candidate` | 通过 |
| 元素数 / 来源数 | 37 / 49 |
| `id` 唯一且前缀 `produce_`、符合 `^produce_[a-z0-9_]+$` | 通过，无重复 |
| 每条 `details` 七节齐全、均为非空字符串、无多余小节 | 通过（37×7=259 个字段） |
| `source_ids` 非空且全部指向已定义来源 | 通过，无悬空引用 |
| `related_ids` 全部指向本组已定义条目 | 通过，无悬空引用 |
| `review_status` 全部为 `needs_review` | 通过 |
| `tags` 全部落在规范词汇表内（含本组扩展的 leafy_green / root_vegetable / condiment_crop / beverage_crop / container_material / staple_substitute / living_organism_tree） | 通过，无同义混用 |
| 来源 `id` 前缀、`title/url/access/supports/rights_note` 齐全、`access` 取值合法 | 通过 |
| 无未被任何条目引用的孤立来源 | 通过，0 条孤儿来源 |
| 本页 MD 覆盖全部 37 条与全部 49 条来源 | 通过 |

**本次复核未触碰**：`data/`、StoryPackage、`staples.json` / `animal-foods.json` / `materials.json` / `tools.json`、`docs/element-catalog/`、任何源码；未执行 git 操作；写入仅用 `vantaloom_edit`（UTF-8），未用 shell 整文件重写。

对 `flavors.json` 的唯一改动是 `flavors_chili_pepper` 的**边界最小勘误**（与本组第三节辣椒/甜椒分工直接相关）：在其 aliases 补入「甜椒 / 灯笼椒 / bell pepper」，并在 definition 与 exceptions 写明甜椒是同属不产辣类型、归 flavors 而鲜食蔬菜的一面归 produce。不改 flavors 的条目数、来源、七节结构与其他 32 条。
