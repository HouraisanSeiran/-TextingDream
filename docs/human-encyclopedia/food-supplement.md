# 人类生产生活百科 · 可食物产增补（food-supplement）

对应 [`food-supplement.json`](food-supplement.json)。状态：**候选资料**（`schema_version: 1`、`status: candidate`、`group: food-supplement`），全部条目 `review_status: needs_review`。

**这是一个独立的增补文件**，不属于既有六组（staples / produce / flavors / animal-foods / materials / tools）。它不改动那六组的数据、不改正式 `data`、不改 StoryPackage、不改 build 名单，也不自行建库；等待主编审阅后决定是否以及与如何并入。

> 百科中存在 ≠ 当前世界存在，更不等于人物知道。本页只做扫读索引、来源说明与已知限制，**完整七节内容以 JSON 为准**，此处不复制正文。

- 元素总数 **23**，id 全部以 `food_supp_` 开头
- 来源 **30** 条，全部 `access: read`；按机构拆开是 **Britannica 23 + FAO 3 + 大学推广（Extension）4**。其中 **1 条（src_21）是策展摘要/索引页**，只能用于术语与物种名对应，**不得把这 30 条一律称作「三十页全正文」**——实际是全文 29 条 + 摘要页 1 条。
- 全部条目 `details` 七节齐全（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty），无固定长度
- 全部条目的 `tags` 取自既有六组已用的标签词汇表，未新增标签；未改动原六组条目的任何标签
- 校验结果见第八节

## 一、这个组在收什么

本组只做一件事：**补原六组没有的可食物产缺口**，不新扩题材，不重立他组已有的物种。取舍标准三条：

1. **先查重再立条**。先把六组 216 个条目的 `id`、`name`、`aliases` 全部抽出比对，已有的物种一律不重复立条——花生、芝麻、扁桃/巴旦木（含「美国大杏仁」）、兵豆（小扁豆）、菠萝（凤梨，且其条目已把「菠萝蜜」列为误称别名）、甘蓝类、洋葱、大蒜、胡萝卜、甜菜糖（糖用甜菜）、番茄、茄子等，都不在本组。
2. **同种不同用途不重复立条，但必须把用途边界写清**。典型是食用甜菜与 flavors 组的「甜菜糖」：同是 *Beta vulgaris*，一个进腌菜缸、一个进糖厂，本组只收**食用线**，并在定义与例外里明确「糖工业部分归 flavors」。反之萝卜与芜菁、菱角与荸荠这类**外形或译名相近但不同物**的，本组并列立条并把区分写进 `exceptions`。
3. **只收能影响人物行动与事件因果的物产**：耐贮与否、加工门槛、水路与水利需求、采收期与劳力、毒性或致敏带来的操作约束。不罗列品种、不凑数。

### 有意不收的（并说明理由）

- **黍之外再立「小粒谷」分支时不重立已有粟类**：狐尾粟、珍珠粟、黍属的狐尾粟、苔麸、藜麦、荞麦均已在 staples；本组只补 **黍（proso）** 与 **指状粟（finger millet）** 两个确实缺位的物种。
- **黑麦草（*Lolium*）不作食物条目**：它是饲草与草坪草，不是人类主食作物，不宜混入可食物产。
- **蘑菇只收栽培类群，不做野采鉴定**：见第九节风险边界。
- **腰果、杏、樱桃、莓果类**：都已核对，六组中没有对应条目，故补入；其中「莓果类」实际只落了 **草莓**（有真实 read 全文支撑），而 **树莓/黑莓（悬钩子类）因拿不到可读来源而未立条**（见第六节第 7 条）。

## 二、扫读表

「类型」列为本组内部分类，用于扫读，不是分类学结论。

### 2.1 谷物与小粒谷替代（2）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_proso_millet | 黍（糜子/黍米） | 播后 60—80 天成熟，最耐旱耐瘠也最能挤进短生长季；稃壳难脱故粉粗；今在亚洲东欧作粮食、别处作鸟食饲料 | src_22 / src_20 / src_21 |
| food_supp_finger_millet | 指状粟（䅟子/ragi） | 东非高原与印度南部的当家小谷；可长期存放不易生虫，故在荒年顶上；可制麦芽酿酒 | src_22 / src_24 / src_23 / src_20 |

### 2.2 根菜、茎菜与叶柄菜（5）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_turnip | 芜菁 | 冷凉季、不需长生育期，可填轮作空隙；根叶兼用也作饲料；常被与 rutabaga 混称（后者另属 *B. napus*） | src_02 / src_04 |
| food_supp_radish | 萝卜（含大根） | 庭园型 3—5 周即收、大根型可长到约 1 kg 并鲜存约两个月；辛味随逆境增强 | src_03 / src_27 |
| food_supp_leek | 韭葱 | 不结真鳞茎，靠培土养成白段；生育期 120—150 天，耐寒可延收 | src_05 / src_26 |
| food_supp_celery | 芹菜（含根芹） | 三个变种分走叶柄/胚轴/叶与果实三条线；肥厚叶柄的栽培型出现很晚（1623 年法国首记作食物） | src_10 / src_12 |
| food_supp_table_beet | 食用甜菜 | 与糖用甜菜同种不同用途；紫红色素水溶、煮制掉色；缺硼致根肉黑斑 | src_11 |

### 2.3 水生与湿地（3）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_water_chestnut | 菱角与荸荠 | 一个英文名罩住两类不同植物：菱的坚果状果（四刺角）与荸荠的球茎（煮后仍脆） | src_28 |
| food_supp_lotus | 莲（藕与莲子） | 全株可食：藕、莲子、嫩叶、花瓣雄蕊；种子硬种皮可在河泥中存活数百年 | src_29 |
| food_supp_sago | 西米（西谷椰淀粉） | 不是谷物：伐倒约 15 年生的棕榈取茎髓淀粉；几乎纯淀粉，须搭配其他食物 | src_16 |

### 2.4 水果（含主食替代型）（8）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_breadfruit | 面包果 | 淀粉质主食果、极少生食；无籽型只能靠根蘖繁殖；不耐霜 | src_01 |
| food_supp_jackfruit | 菠萝蜜 | 世界最大树上果实（可达约 60 cm、18 kg）；青果作蔬菜、熟果生食、种子另食 | src_06 |
| food_supp_persimmon | 柿 | 多数品种软熟前强涩，采收期与可食期不重合；美洲柿至今大量野采 | src_07 |
| food_supp_cherry | 樱桃 | 甜樱桃鲜食、酸樱桃进罐藏；需冬季低温、花期早，适栽区被气候压窄 | src_08 |
| food_supp_apricot | 杏 | 原初驯化于中国（学名 *armeniaca* 只是旧命名）；花芽比桃更早开易遭晚霜；种仁须烤制 | src_09 |
| food_supp_avocado | 鳄梨 | 果肉含油可达约 25%；A/B 两型花错时开放，须混栽才稳产 | src_13 |
| food_supp_papaya | 番木瓜 | 一年内结果、快回收；未熟果乳汁含蛋白酶；环斑病毒后主栽多为转基因品种 | src_14 |
| food_supp_quince | 榅桲 | 香气强但生食极涩，几乎只能做酱与胶冻；曾在欧洲庭院常见、后商业栽培大幅退场 | src_18 |

### 2.5 坚果（1）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_cashew | 腰果 | 假果（cashew apple）大、真果小；两层壳间夹苛性树脂，故从不去壳出售；去壳是危险工序 | src_30 |

### 2.6 豆类（1）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_mung_bean | 绿豆 | 生育期短、根瘤固氮；干豆可贮、磨粉可制粉丝、发芽成豆芽（两极化的流通形态） | src_15 |

### 2.7 其他（3）

| ID | 名称 | 一句话要点 | 主要来源 |
|---|---|---|---|
| food_supp_strawberry | 草莓 | 典型「假果」：食用部分是花托；极不耐运 + 需人工采摘，故天然绑定近郊与加工带 | src_17 |
| food_supp_cultivated_mushroom | 栽培食用菌 | 真菌子实体而非植物；技术门槛在灭菌与洁净；共生型（松茸类）无法简单栽培 | src_19 |
| food_supp_grain_amaranth | 籽粒苋 | 美洲原产双用途苋：叶当菠菜、种子可代谷物或爆开；晚熟限制其在北方的推广 | src_25 |

## 三、与六组的分工与交叉点

| 本组条目 | 交叉到他组的条目 | 分工方式 |
|---|---|---|
| food_supp_proso_millet | staples_millet_foxtail / staples_millet_pearl / staples_teff | 同属俗名集合「粟类」但不同属；本组只补缺位的 *Panicum miliaceum* |
| food_supp_finger_millet | 同上 + flavors_beer / tools_granary | 谷物本体在此，酿酒与粮仓另在他组 |
| food_supp_table_beet | flavors_beet_sugar | **同种不同用途**：食用线在本组，糖工业线在 flavors，两边都写清边界 |
| food_supp_turnip / radish / table_beet | produce_cabbage / produce_carrot / produce_chinese_cabbage / staples_rapeseed | 同科不同物种/变种，各自独立 |
| food_supp_breadfruit / jackfruit | produce_pineapple / produce_banana / staples_taro / staples_yam | 热带淀粉与水果体系；且 jackfruit 与 pineapple 的「菠萝蜜」误称关系已在两处标明 |
| food_supp_cashew / apricot / cherry | produce_almond / walnut / hazelnut / pistachio / peach / plum | 坚果与核果的同科对照，不互相替代 |
| food_supp_water_chestnut / lotus | staples_taro / staples_rice / tools_irrigation_canal | 水生可食部位在此，水利设施在 tools |
| food_supp_sago | staples_cassava / food_supp_breadfruit | 同为热带淀粉源，但取淀粉方式（伐树 vs 挖根）不同 |

## 四、来源清单（JSON 实计 30 条：read 30，其中策展摘要页 1、全文 29）

机构构成按 JSON 实际统计（非估算）：**Britannica 23 + FAO 3 + 大学推广 4 = 30**。

| id | 来源 | 机构类型 | 用途定位 |
|---|---|---|---|
| src_01 | Breadfruit — Encyclopaedia Britannica | 百科 | 定义/形态/传播/加工 |
| src_02 | Turnip — Encyclopaedia Britannica | 百科 | 定义/物种边界 |
| src_03 | Radish — Encyclopaedia Britannica | 百科 | 定义/多样性 |
| src_04 | Growing turnips and rutabagas — Univ. of Minnesota Extension | 大学推广 | 栽培与贮藏条件 |
| src_05 | Leek — Encyclopaedia Britannica | 百科 | 定义/历史/培土 |
| src_06 | Jackfruit — Encyclopaedia Britannica | 百科 | 定义/多用途 |
| src_07 | Persimmon — Encyclopaedia Britannica | 百科 | 两物种/涩味/分布 |
| src_08 | Cherry — Encyclopaedia Britannica | 百科 | 三类樱桃/气候约束 |
| src_09 | Apricot — Encyclopaedia Britannica | 百科 | 驯化地/加工/种仁 |
| src_10 | Celery — Encyclopaedia Britannica | 百科 | 三变种/驯化不确定 |
| src_11 | Beet — Encyclopaedia Britannica | 百科 | 四种栽培形态/土壤 |
| src_12 | Celeriac — Encyclopaedia Britannica | 百科 | 胚轴部位/传播 |
| src_13 | Avocado — Encyclopaedia Britannica | 百科 | A/B 花型/含油/产业史 |
| src_14 | Papaya — Encyclopaedia Britannica | 百科 | 起源不确定/病毒与转基因 |
| src_15 | Mung bean — Encyclopaedia Britannica | 百科 | 固氮/多用途 |
| src_16 | Sago — Encyclopaedia Britannica | 百科 | 取淀粉工序/成分 |
| src_17 | Strawberry — Encyclopaedia Britannica | 百科 | 假果结构/易腐与布局 |
| src_18 | Quince — Encyclopaedia Britannica | 百科 | 生涩/加工/退场 |
| src_19 | Mushroom — Encyclopaedia Britannica | 百科 | 真菌学基础/野采风险 |
| src_20 | Millet — Encyclopaedia Britannica | 百科 | 粟类总览/proso |
| src_21 | Proso — Britannica 策展摘要与索引页 | 摘要页 | **仅术语与物种对应**，不单独支撑细节 |
| src_22 | Sorghum and millets in human nutrition, Ch.1 — FAO（1995） | FAO | 起源表/各粟形态与利用 |
| src_23 | 同上 Ch.2 | FAO | 1990 年产量与区域格局（总量） |
| src_24 | 同上 Ch.4 | FAO | 成分与加工特性 |
| src_25 | Amaranthus hypochondriacus — NC State Extension | 大学推广 | 形态/食用部位/硝酸盐提示 |
| src_26 | Growing leeks — Univ. of Minnesota Extension | 大学推广 | 生育期/培土/清洗 |
| src_27 | Growing radishes — Univ. of Minnesota Extension | 大学推广 | 两类萝卜/贮藏 |
| src_28 | Water chestnut — Encyclopaedia Britannica | 百科 | 菱与荸荠分述 |
| src_29 | Sacred lotus — Encyclopaedia Britannica | 百科 | 各部位利用/种子寿命 |
| src_30 | Cashew — Encyclopaedia Britannica | 百科 | 假果/壳间树脂/工序 |

### 优先信源的落实与不足

- **FAO**：实际读了 FAO《Sorghum and millets in human nutrition》的 3 个章节页（Ch.1 起源与形态、Ch.2 产量、Ch.4 成分），是本组唯一的多地区权威机构来源。
- **大学推广机构**：实际是 **4 条**（先前报告误计为3）——明尼苏达 Extension 三页（芜菁/rutabaga、韭葱、萝卜）+ 北卡州立 Extension 植物库一页（籽粒苋），提供栽培与贮藏的操作性条件；语境均为北美，已在各条第七节注明不可外推。
- **Kew / 植物园 / 博物馆**：**本轮未取到实际可引用的全文**。尝试过的 `powo.science.kew.org` 具体 taxon 页返回的是别的分类单元（Telipogon）或 404，Missouri Botanical Garden 的 PlantFinder 因证书过期失败，USDA PLANTS 页只抽出标题。按「来源没读到的不编造」原则，这些**一律未列入 sources**，也不再无限补源。
- **未使用维基百科**：`en.wikipedia.org` 本轮持续连接失败（dial tcp connectex），因此本组没有任何维基来源。

## 五、证据等级说明（重要）

本组条目**并非同一证据强度**，主编导入前应按下列三档区别对待：

**A 档（定义 + 条件 + 历史三层都有独立 read 来源支撑）**
proso_millet、finger_millet、turnip、radish、leek、celery、table_beet、strawberry、quince、breadfruit、jackfruit、persimmon、cherry、apricot、avocado、papaya、cashew、mung_bean、sago、water_chestnut、lotus、cultivated_mushroom、grain_amaranth

这些条目的 `exceptions` 与 `evidence_and_uncertainty` 都写明了「哪些是来源实际支撑的」「哪些是没有读到来源因而留白的」。

**B 档（来源为摘要/索引页，仅用于术语核对）**
- `food_supp_proso_millet` 的 src_21：Britannica 无独立全文条目时给出的策展摘要与相关段落索引。它只用于确认「proso = *Panicum miliaceum*」与「栽培黍的野生祖先尚未确定」这两点，定义与条件主要靠 src_22。**不能把它当全文**。

**C 档（无）**

本轮无 C 档条目。需要说明的是：计划中的「树莓/黑莓（悬钩子类）」最终**没有立条**——Britannica 的 raspberry / blackberry 条目本轮未能读取成功，而按「来源没读到的不编造」的原则，不能拿草莓条目的来源去撑一整条聚合果条目。该缺口已记入第六节第 7 条，留给主编补源后再决定是否增立。

## 六、已知缺口（逐条记录，未用推测填补）

1. **驯化年代与地点**：绝大多数条目只能给「推测起源地/范围」，不能给年份。这是有意为之：FAO 只给「suggested origin」的区域，Britannica 多数条目不给年代。
2. **传入各地的时间线**：除杏（18 世纪入加州）、腰果（16 世纪后期入东非与印度）、番木瓜（20 世纪病毒史）等少数有明确记载者外，其他条目的传播时间均标为缺口。
3. **工艺参数一律不给**：腌渍盐量、干制温度与时长、腰果去壳加热条件、蘑菇灭菌与出菇参数、草莓与樱桃的冷链温度——这些要么来源未覆盖，要么属危险工序，本组**有意留白**，只在正文里说明「需要什么条件」，不写「怎么做到数值」。
4. **产量与经济占比**：只有 FAO Ch.2 给了 1990 年粟类总量与国别占比，且是「粟类合计」，**不能据此拆分到黍或指状粟**。其他作物一律无产量数据。
5. **Kew / 植物园来源缺失**：如第五节所述，本轮未能取到可引用的 Kew POWO 或植物园全文，因此物种分类学名均以 Britannica 与 FAO 的写法为准，并已保留学名不一致的情况（如韭葱 *Allium porrum* / *Allium ampeloprasum* var. *porrum* 两种写法并列）。
6. **中文名的地方性**：糜子/黍、䅟子/龙爪稷、莱菔/萝卜、马蹄/荸荠等名称在不同地区所指不同，条目内已加限定，但未做方言级调查。
7. **树莓/黑莓（悬钩子类）未立条**：Britannica 的 raspberry / blackberry 条目本轮读取失败，而这类「软质小浆果」的聚合果结构、枝条二年生修剪、采后极不耐运等要点必须有直接来源才写。现仅在本文记录缺口，**JSON 中无此条目**，待补源后由主编决定是否增立。

## 七、语言与内容边界

- **不给医疗或营养功效**。凡来源中出现「助消化」「延年」「抗炎」「利尿」等说法，本组一律标注为「传统药学记载或商业说法」，不作功效断言；草莓、甜菜等条目中出现的维生素/抗氧化物表述只作**成分记录**。
- **不给危险食品的处理参数**。涉及三类：腰果壳间树脂（可致皮肤起疱）、苏铁来源「西米」的 cycasin 去毒、野生蘑菇。三处都只做定性说明并明确「本条不提供操作参数」。
- **不做野采鉴定**。栽培食用菌条目只写栽培类群，`exceptions` 里明确引 Britannica 的立场：野生蘑菇没有简易判定规则，许多毒菌与可食种形态相近，毒性还随生态条件与地域变化，只能食用经权威确认者可食、最稳妥是用栽培种。**本组不提供任何形态特征组合用于野外判食。**
- **不复制来源大段文本**。所有 `supports` 与 `details` 均为自行转述与压缩，未逐句搬运原文。

## 七之二、聚焦定义复核（第二轮，主代理指定 5 点）

本轮仅做定义与过强数字复核，**未补来源、未扩项、未改其他组**。5 个问题均属真实缺陷，已逐条修正：

| # | 复核点 | 原缺陷 | 修正方式 |
|---|---|---|---|
| 1 | 双孢蘑菇与香菇生态条件不相同 | 原 `conditions` 把「秸秆/粪肥」与「木屑菌袋」并列成一套工序，`definition` 也未分开，读者可能套用同一组参数 | `definition` 明确二者分属堆肥/粪草类发酵基质与木质基质两大路线；`conditions` 改为「基质路线按菌种分开、不可互换」，只保留三道共通前提（灭菌/发酵—接种—控温湿通风出菇） |
| 2 | 菱属果实与荸荠球茎不是同种 | 原 `exceptions` 已说不同物，但 `tags` 共用 `root_tuber` 而未界定层级，易被误读为一类 | （第二次修正，见七之三）首版曾保留 `root_tuber` 并靠文字界定，但仅从语义上保留错误类别并不够：**已直接移除该标签**，改用跨部位上位标签。`exceptions` 首句改为器官层级声明（菱为菱科坚果状果、荸荠为莎草科地下匍匐茎球茎），`summary` 同步改为「不同科、不同食用部位」 |
| 3 | 西米传统棕榈淀粉 vs 商品木薯「珍珠西米」 | 原 `definition` 把木薯一句带过作「命名混淆」，未说清原料与工序差别；改写中还曾误删两条重要限制 | `definition` 新增一段：商品名「西米」≠棕榈淀粉，木薯那类原料是块根、经磨浆沉泥制粒，与西谷椰在原料/工序/产地体系均不同；`exceptions` 改为三条原料线并列（棕榈 / 木薯 / 苏铁）；**并补回一度被删的两条限制**：纯淀粉长期单食的营养缺口、「先伐树后取粉」不可逆 |
| 4 | 杏果肉 vs 苦杏仁风险，不混扁桃 | 原条把风险笼统写成「种仁有毒须烤制」，未区分果肉与仁；与扁桃的边界也仅一句 | `conditions` 拆开两条风险线（果肉正常食用 / 风险只在核内仁，且苦、甜两类程度不同）；`exceptions` 改为**命名层级 / 物种边界 / 可食部位与风险**三点分述，明确「果肉可食≠整果可食」、杏仁≠扁桃仁，不提供去苦去毒参数 |
| 5 | 同一甜菜 species 食用/糖用属用途层 | 原条只说「同种不同用途」，未明写「不是新物种」，导语还有语病 | `definition` 补「四个栽培形态同属 *Beta vulgaris*，是 variety/cultivar group 层的关系、**不是分类层级的新物种**」；`exceptions` 同步强调「不是四个物种、也不是新驯化」；导语语病已改 |

复核后各项均保持 `review_status: needs_review`，未自升、未新增来源、未改动其他组。

## 七之三、标签勘误（第三轮，最后一处）

主代理指出：**果实不能用块根类标签扩大检索面**。该判断成立，前一轮「保留 `root_tuber` 并用文字定界」是错的——`root_tuber` 是器官级类别标签，不是「食用类型相似」的模糊标签；只要它挂在这条上，任何基于 tags 的检索或自动处理都会把菱角当成块根类。**已直接移除，不靠文字打补丁。**

| 项 | 修正前 | 修正后 |
|---|---|---|
| `tags` | `living_organism, crop, food, agriculture, water_management, root_tuber` | `living_organism, crop, food, agriculture, water_management, aquatic_food` |
| `definition` | 「取其坚果状的果」「取其地下球茎」 | 改为「**坚果状的果（不是地下茎，也不是块根）**」「**地下匍匐茎末端膨大的球茎**」，并补一句：因为可食部位分属不同器官，本条不用 `root_tuber` / `fruit` 这类器官级标签，只征用跨部位上位标签 |
| `exceptions` | 首句为「共用 `root_tuber` 仅表示食用类型相似」 | 首句改为**器官层级声明**：本条不用 `root_tuber`、也不用 `fruit`；单一器官级标签套在聚合条目上会让检索把一方误当另一方的类别；列明保留的六个上位标签 |

两点需要说明：

1. **没有加 `fruit`**。主代理建议「增加 fruit / aquatic_plant 等适用 tag」，但 `fruit` 对荸荠的球茎同样是错误类别，加了只是把错误反向重犯一次。`aquatic_plant` 不在既有六组词表内，加它属于新增标签。因此取保守方案：**只用已在词表内的跨部位上位标签**（`aquatic_food` 已存在于原六组标签词表中，非新造）。
2. **schema 无 `tag_scope` 字段**。`collection-spec.md` 的 element 结构未定义按子类分别标注标签作用域的字段，本次不发明新字段，改由 `definition` / `exceptions` 写明部位细节，这也是主代理给出的备选路径。

检索面受损的补偿：**未删除任何 `aliases`**（菱角、菱、乌菱、荸荠、马蹄、water chestnut、water caltrop、Trapa natans、Trapa bicornis、Eleocharis dulcis 全部保留），名称与俗名检索不受影响；减少的只是「按块根类检索到菱角」这条本就不正确的路径。

本轮只改这一条的 `tags` 与对应 MD 叙述，**七节语义未删减、未扩项、未补源、未动其他组**，完成即冻结。

## 八、校验结果（本轮实施）

| 校验项 | 结果 |
|---|---|
| JSON 严格解析（PowerShell ConvertFrom-Json + UTF-8 无 BOM 读取） | 通过 |
| 顶层字段 schema_version / group / status=candidate / sources / elements | 通过（group=`food-supplement`，另有 `note` 说明分工） |
| 元素条数 | 23 |
| 全局 id 唯一（与六组 216 个 id 及本组内部比对） | 通过，无冲突 |
| id 前缀 `food_supp_` | 23/23 通过 |
| source_ids 均可解析到本组 sources | 通过（30 个来源全部被引用，无悬空） |
| related_ids 可引用六组真实 id 与本组 id | 通过（跨组引用已逐条核对存在） |
| tags 全部取自既有词汇表（82 个既有标签） | 通过，**未新增标签** |
| details 七节齐全且非空（键数恰为 7） | 23/23 通过 |
| review_status 全为 needs_review | 23/23 通过 |
| 本页 MD 覆盖全部 23 条 | 通过（第二节扫读表逐条列出） |
| 第二轮定义复核（5 点）后重跑上述全部项 | 通过（23 条 / 30 来源不变，无新增标签、无新增条目） |

校验脚本通过 shell 只读执行（`[IO.File]::ReadAllText` + `ConvertFrom-Json`），**未用 shell 重写任何文件**；两个交付文件均由 `vantaloom_edit` 以 UTF-8 写入。

## 九、未做的事（有意为之）

- 未修改 `staples.json` / `produce.json` / `flavors.json` / `animal-foods.json` / `materials.json` / `tools.json` 及其 `.md`。
- 未修改 `collection-spec.md`。
- 未改动正式 `data` 目录、StoryPackage、任何源码与 build 名单。
- 未建库、未导库：JSON 是候选文件，导入路径由主编决定。
- 未擅自给原六组条目重标 `tags` 或 `review_status`。

发布基线保持在既有 commit `1398466` 之上不动，本组仅新增两个独立文件待审。
