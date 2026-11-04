# 东方玄幻 / 仙侠 · 丹药专项候选组（eastern-alchemy）

状态：**候选素材收集**，不是数据库实现，不是任何故事包已采纳的正典，未进入 `data/` 或任何 StoryPackage。
配套机读文件：[`eastern-alchemy.json`](eastern-alchemy.json)（`schema_version: 1` / `status: candidate` / `group: eastern-alchemy`）。
规范依据：[`collection-spec.md`](collection-spec.md)。

- 元素数量：**20**
- 题材标签：`eastern_fantasy`、`xianxia`，**20 条全部同时标两题材**（`genre:` 标签由导入器按 `genres` 自动追加，文件里不手写）
- 来源：登记 **15** 条 → `access: read` **12** 条、`access: unavailable` **3** 条。12 条 read 里 **11 条被实际引用**，另有 1 条（`eastern_alc_src_zhihu_dandu`）读到了但主题不符、**如实登记且不采用**（见「来源清单」）
- 详细程度：20 条全部含 `details` 七节且**每节均为字符串**，`detail_status` 一律 `needs_detail`，`review_status` 一律 `needs_review`
- `details` 七节合计每条 **1259—2197 字**（均值约 1660 字），未为压篇幅删掉机制、例外或条件
- 类别：20 条全部 `category: item`；ID 前缀 `eastern_alc_`

---

## 先读这一节：本组与既有文件的分工（不重写、只指向）

同目录已有两份与本组直接相邻的候选文件。**本组不复制它们的任何机制**，只在需要处用文字指向：

| 已有条目 / 文件 | 它已经写了什么 | 本组补什么 | 不重复什么 |
|---|---|---|---|
| [`eastern.json`](eastern.json) 之 `eastern_alchemy`（炼丹术） | 外丹五步（选料→炮制→配比→火候→成丹与分丹）、内丹四阶段、火候不可文字化、丹师行会与副产物链条 | 落到**具体丹品**与**生产条件**：单味丹的用途、门槛、成丹率、服用条件、副作用、供应与垄断 | 不重写外丹五步与内丹次第；`eastern_alc_furnace_fire` 只写「炉／火／控／验」这四件实物与产权，工序原理一律指回 `eastern_alchemy` |
| [`eastern.json`](eastern.json) 之 `eastern_pill_elixir`（丹药） | 成品的社会生命四要素：药效、剂量与耐受、保存、真伪；价格、囤积、投毒、耐药 | 把四要素拆成 20 条可检索的**丹品与制度**，各带自己的代价 | 不再综述一遍「丹药是商品」；`eastern_alc_pill_grading` 与 `eastern_alc_pill_toxin` 是把该条的两个要素单独展开 |
| [`eastern-biology.json`](eastern-biology.json) 之 `eastern_bio_demon_core_hunt`（妖兽丹核） | 妖兽被「资源化」的那一层，且已限定**仅无智慧兽型** | `eastern_alc_beast_core_refine`：核如何**变成药**（破核／转性／成丹、品级错配、兽性累积、核籍追溯） | 不重写猎场经济与兽潮；「仅限无智慧兽型」的限定原样沿用 |
| `eastern-biology.json` 之 `eastern_bio_ginseng_root`（灵参）、`eastern_bio_lingzhi_fungus`（灵菌芝） | 两种「某某的玄幻变体」，含生境、慢生、采集三难、栽培冲击 | 本组只把它们当作**药材来源**在正文里文字呼应（不可保证有货、老芝属传说层） | 不立生物条目、不追加药效、不写任何用法 |
| `eastern-biology.json` 之 `eastern_bio_bamboo_grove`（灵竹）、`eastern_bio_spirit_moss_rice`（灵谷） | 灵竹／灵谷的生长条件、产量与佃户关系 | 本组把它们当作**赋形料与代粮料**（辟谷丹、解毒丹的载体） | 不重复灵田分级与种植条件；指回 `eastern.json` 之 `eastern_spirit_agriculture` |

关联写法：`related_ids` **只指向本组 20 条内部实际存在的 ID**（导入后 52 条关联全部 `resolved`，未解析 0）。指向 `eastern.json` / `eastern-biology.json` 的条目一律**只写文字、不写 ID**——两个文件的命名空间不同，跨文件硬引用会在此刻的库里变成 `pending`，属未解析关联。

---

## 三条必须先说清的边界

1. **传统记述 vs 本项目设计归纳，逐条分列。** 每条 `details.evidence_and_uncertainty` 都把材料分两堆：有可核来源的（《抱朴子》篇目结构与炼丹条件清单、外丹的火炼水炼与唐代服丹中毒致死、《本草纲目》的「正误」体例与对水银「成仙」说的批判、《神农本草经》的三品与七情、宋代官办药局的成药配本、汞化合物的毒理），与本项目为可玩性补出的（成丹率、耐药曲线、时间窗、丹毒蓄积量、丹纹、核籍、炉房产权等）。后者一律写明「本项目设计归纳」。
2. **仙侠丹药 ≠ 现实中药，也 ≠ 道教修炼的实际效果。** 本文件**不给任何现实处方、剂量、配伍、炮制温度与时长、有毒药材的处理或解毒方法**，不写任何现实医疗主张，也不用「古已有之」为虚构丹效背书。凡引用传统文献，只支撑「历史上有此说法／此制度／此批判」，不支撑任何效力。
3. **长生 / 飞升 / 起死回生 / 无限增产一律不默认成立**，且在 `excludes`、`adaptation_limits`、`details.historical_scope` 三处落成文字：

| 写法 | 本组的处理 | 落在哪一条 |
|---|---|---|
| 服之成仙、长生不死 | 不成立；延寿丹压到**传说层**，上限十数年量级、逐次递减、材料绝产、必然带毒 | `eastern_alc_longevity_pill` |
| 起死回生 / 复活 | 不成立；续命丹只买**一到三日**的时间窗，且不能重复续期 | `eastern_alc_life_sustaining_pill` |
| 无限堆药变强 | 不成立；吸收率、耐药、丹毒蓄积三闸门同时存在 | `eastern_alc_qi_gathering_pill`、`eastern_alc_breakthrough_pill`、`eastern_alc_pill_toxin` |
| 无限量产 | 不成立；高阶丹的瓶颈是**料源与炉房**，不是丹师手艺 | `eastern_alc_furnace_fire`、`eastern_alc_beast_core_refine`、`eastern_alc_longevity_pill` |
| 以活人炼丹 / 以智慧妖族入药 | **明确为罪行**，并要求写出追诉者与后果；化形丹与兽核转炼两条写死了这一点 | `eastern_alc_shape_change_pill`、`eastern_alc_beast_core_refine`、`eastern_alc_healing_pill`、`eastern_alc_marrow_wash_pill`、`eastern_alc_pill_grading` |

---

## 扫读表

题材列省略（20 条皆同时标 `eastern_fantasy` + `xianxia`）；类别列全为 `item`。

| # | ID | 名称 | 一句话用途 | effect / grade | 证据状态 |
|---|---|---|---|---|---|
| 1 | `eastern_alc_healing_pill` | 疗伤丹 | 最底一档、唯一真正量产的丹：把痊愈变成可买的物件，也因此最易掺假 | healing / common | 来源支持「药分草木金石、按毒性分等」；量产与掺假链属设计归纳 |
| 2 | `eastern_alc_life_sustaining_pill` | 续命丹 | 不治病不长生，只把濒危者的时间往后拖一到三日，且逐次递减 | life_sustaining / rare | 来源只支持「古人以矿物丹求长生并中毒身死」；时间窗属设定 |
| 3 | `eastern_alc_antidote_pill` | 解毒丹 | 越专一越有效、越通用越弱；真正稀缺的是「知道中的是什么毒」 | antidote / common | 来源支持「七情」中的「相杀」与本草「正误」体例；三路线与耐药属设定 |
| 4 | `eastern_alc_grain_avoidance_pill` | 辟谷丹 | 把口粮换成更小更难获得的东西；价值在运输，不在生命 | fasting / common | **来源较实**：辟谷分服气／服药两类、服药辟谷仍须进食、葛洪反对单行辟谷成仙 |
| 5 | `eastern_alc_qi_gathering_pill` | 聚气丹 | 修行界的日常口粮，也是耐药最先出现的地方 | qi_gain / common | 纯类型设定（仅有「服食求养身」的诉求旁证） |
| 6 | `eastern_alc_breakthrough_pill` | 破境丹 | 只把一次冲关的成功率往上推，并把失败后果一起放大 | breakthrough / rare | 来源支持「炼丹被高度条件化」；境界阶梯属类型惯例 |
| 7 | `eastern_alc_foundation_pill` | 固基丹 | 压实已有根基，境界不动；与破境丹互为反面 | foundation / uncommon | 来源支持「上药养命、可久服」的分工；三段与浮基丹属设定 |
| 8 | `eastern_alc_marrow_wash_pill` | 洗髓淬体丹 | 以剧痛与不可逆改造换体质，失败者留下终身残疾 | body_refining / rare | 来源支持「矿物猛药有真实器官损伤」；三阶段属设定 |
| 9 | `eastern_alc_longevity_pill` | 延寿丹 | 传说层的麦高芬：上限十余年、逐次递减、材料绝产 | longevity / **legendary** | **史实最硬**：方仙道求不死药、《本草纲目》批水银成仙、唐代服丹致死 |
| 10 | `eastern_alc_face_retaining_pill` | 驻颜丹 | 只改外观不改寿数，停服即回退；卖的是身份信号 | appearance / uncommon | 来源仅支持「悦泽类诉求成类」；机制全属设定 |
| 11 | `eastern_alc_breath_conceal_pill` | 敛息丹 | 压气息与灵压而非隐身，一动即破，多属管制物 | stealth / uncommon | 来源支持《抱朴子》有「隐沦」一类方术；效力全属虚构 |
| 12 | `eastern_alc_climate_ward_pill` | 御寒御火丹 | 两系互斥，各买几个时辰的耐受窗口，借的是自身储备 | climate_resist / common | 来源支持入山诸术与「佩药服丸」诉求；机制属设定 |
| 13 | `eastern_alc_lightness_pill` | 轻身丹 | 减重减坠带来高机动，**不是飞行**；飞举是坊间讹传 | lightness / uncommon | 来源支持「身轻」是修行话语用语；效果属设定 |
| 14 | `eastern_alc_ward_evil_pill` | 驱邪丹 | 护体醒神而非杀敌；最难验真，因此养活真需者与骗子两类人 | exorcism / common | 来源支持《抱朴子·登涉》的辟邪诸术清单；效力不成立 |
| 15 | `eastern_alc_shape_change_pill` | 化形丹 | 限时人形外观，是妖修入世的通行证；**伦理最重**的一条 | polymorph / rare | 来源支持「变化」类方术与志怪化形母题；伦理判定为本项目选择 |
| 16 | `eastern_alc_spirit_calm_pill` | 定神丹 | 压症状不治根源，便宜、易依赖，也天然是审讯工具 | calm / common | 来源支持「存思／守一」类实践；药效属虚构 |
| 17 | `eastern_alc_beast_core_refine` | 兽核转炼 | 把丹核变成药的工艺：产量由猎场决定，品级不可超越核 | qi_gain / uncommon | 来源支持「动物药自成一部」与「修治」体例；丹核本身属设定 |
| 18 | `eastern_alc_pill_toxin` | 丹毒与废丹 | 给所有丹品统一加上的代价项，把炼丹业与公共卫生连起来 | toxicity / side_effect | **史实最硬**：唐代服丹致死者、汞毒理、《本草纲目》批水银、五石散含砷 |
| 19 | `eastern_alc_pill_grading` | 丹药品级与鉴伪 | 分级与鉴伪两条腿；标准一旦成型即成为垄断门槛 | appraisal / grading_scheme | 来源支持宋代官药局配本、本草「正误」、三品分等；制度形态属设计 |
| 20 | `eastern_alc_furnace_fire` | 丹炉与火候 | 炉／火／控／验四要素，是固定资产，因此产生产权、垄断与污染 | production_capacity / infrastructure | 来源支持炼丹须名山吉日等条件、金丹部方药部文献；器物分级属设定 |

## 需求覆盖核对（用户点名的 18 项 → 落点）

| 要求覆盖 | 落点 |
|---|---|
| 疗伤与续命 | 1 `healing_pill`、2 `life_sustaining_pill` |
| 解毒 / 解毒驱邪 | 3 `antidote_pill`、14 `ward_evil_pill` |
| 辟谷 | 4 `grain_avoidance_pill` |
| 聚气或助修 | 5 `qi_gathering_pill`、7 `foundation_pill` |
| 破境 / 筑基类 | 6 `breakthrough_pill`、7 `foundation_pill` |
| 洗髓淬体 | 8 `marrow_wash_pill` |
| 延寿（限定传说层） | 9 `longevity_pill`（`grade:legendary`） |
| 驻颜 | 10 `face_retaining_pill` |
| 隐匿气息 | 11 `breath_conceal_pill` |
| 御火御寒 | 12 `climate_ward_pill` |
| 飞行或轻身 | 13 `lightness_pill`（明确不产生飞行，飞行指回 `eastern_flying_sword`） |
| 化形 | 15 `shape_change_pill` |
| 定神 / 宁心 | 16 `spirit_calm_pill` |
| 兽核炼化 | 17 `beast_core_refine` |
| 丹毒与耐药 | 18 `pill_toxin`（耐药、积毒、经脉损伤三分） |
| 丹药品级与真伪鉴定 | 19 `pill_grading` |
| 炼丹炉火与丹成率 | 20 `furnace_fire`（成丹率与废丹在 1、2、6、8 各自的 mechanism 里分述） |

---

## 每一条都写了这七件事（用户硬性要求 4）

| 要求 | 本组怎么落 |
|---|---|
| 药材来源与替代品 | 每条 `details.conditions` 开头必写「来源＋替代品」两段，替代品必带代价（加量、减半方、缓方、食补版、装备替代）；替代品不成立者也明说（延寿丹：凡替代者皆伪方） |
| 炼制门槛（炉、火、时辰、丹师等级） | 统一指回 `eastern_alc_furnace_fire` 的四要素分级；各条只写自己的最低门槛（凡俗药堂可制 / 需正式丹师 / 需懂修行次第的丹师 / 需高阶丹师＋场地与护法） |
| 成丹率与废丹 | 每条 `mechanism` 都给出成丹率档位与**废丹的形态与危害**（碎丹、漏气丹、助毒丹、逆冲丹、浮基丹、燥丹、错形丹、滞神丹、聚阴丹、腥丹、滞颜丹、闭息丹） |
| 服用条件与境界/体质限制 | 每条 `conditions` 末段：境界太低浪费甚至成毒、太高无效（**药力与境界不匹配**是本组通用硬规则）、经脉已损者禁服、心境浮乱者失败率反升 |
| 副作用（丹毒、抗药、经脉损伤） | 各条自带本味副作用，另由 `eastern_alc_pill_toxin` 统一收口：耐药可逆 / 积毒不可逆 / 经脉损伤视程度，且**蓄积量不可测量**是本组全部社会后果的根源 |
| 供应与垄断 | 宗门（配额、贡献点、长老控制弟子、禁售）、药堂（行会、保票、评级机构）、官府（军需征丹、管制物、官验）三类主体在各条 `story_uses` 分别出现 |
| 法律与伦理处境 | **以活人炼丹（药人、死囚、买来的流民、儿童）与以智慧妖族之核／血入药，在本组一律明确为罪行**，并要求写出追诉者（官府／宗门戒律／受害族群）、罪名与后果；不写成中性生产流程 |

---

## 标签设计

每项自带 `tags`，统一四层（`genre:` 与 `category:` 由导入器追加，文件里不手写）：

- **本体层**：`kind:item`（20/20）、`tradition:eastern`（20/20）
- **效果层** `effect:`：19 个去重值（`qi_gain` 出现 2 次）
- **品级层** `grade:`：7 个值 —— `common` 7、`uncommon` 5、`rare` 4、`legendary` 1，另有三个**非丹品档位**用同一前缀标明对象性质：`grade:grading_scheme`（制度）、`grade:infrastructure`（生产基础）、`grade:side_effect`（代价项）
- **路径层** `route:`：11 个值，标明主料路线（`herbal` 7、`mineral_herbal` 3、`beast_derived` 2，以及 `qi_condensed` / `mineral_toxic` / `ritual_herbal` / `herbal_mineral` / `accumulation` / `furnace` / `market` / `lost_formula` 各 1）
- **成本层** `cost:`：10 个值，从 `common_reagent` 6 一路到 `taboo_reagent` 1（含 `extinct_reagent`、`hunting_yield`、`capital_cost`、`verification_cost`、`cumulative_damage` 等）
- **功能层** `role:`：36 个值，标明该条在剧情里的职能，含 `political_asset`（`life_sustaining`）、`crime_object`（`shape_change`）、`taboo_edge`（`beast_core_refine`）、`monopoly_asset`／`production_basis`（`furnace_fire`）、`public_health`／`hazard`（`pill_toxin`）、`institution`／`dispute_source`（`pill_grading`）、`macguffin`／`legend`（`longevity`）

文件内共 **85 个去重标签 / 158 个标签实例**；导入后（追加 `category:item` 与 `genre:eastern_fantasy`、`genre:xianxia`）共 **88 个去重标签**。全部符合 `_TAG_RE`（`^[a-z0-9][a-z0-9_.:-]*$`），未出现手写 `genre:` / `category:`。

---

## 七节 `details` 的写法

规范七节键（`app/encyclopedia.py` 的 `DETAIL_SECTIONS`，顺序即规范顺序，已逐条核验完全一致、且每节均为字符串）：
`definition` → `mechanism` → `conditions` → `exceptions` → `story_uses` → `historical_scope` → `evidence_and_uncertainty`

对应本组的中文分工：定性（含「本条不给什么」） → 机制与参数维度（含成丹率与废丹形态） → 药材来源／替代品／门槛／服用条件 → 合法变体与反例 → 推到社会层面的后果（垄断、司法、公共卫生、罪行） → 时期限定与改编边界（长生不成立、不给处方） → 证据分层与不确定处（来源支持 / 设计归纳 / 待补）。

本组用的是**新 schema**（`DETAIL_SECTIONS` 原键），不是旧 element-catalog 的 `story_consequences` / `adaptation_limits` 映射；`adaptation_limits` 与 `excludes` 作为**额外顶层字段**保留并参与导入（`details_extra` 为空，全部字段被校验器接受）。

---

## 来源清单（真读过才标 read）

`access: read` **12** 条（其中 11 条被实际引用，最后 1 条读了但不采用）：

| ID | 标题 | 本组用它支撑什么（可核部分） |
|---|---|---|
| `eastern_alc_src_baopuzi` | 抱朴子 · 百度百科 | 内篇 20 篇／外篇 50 篇的结构；《金丹》篇「金丹为仙道之极」并记炼制须**盟约、结伴、祭神、药物、经典、名山、吉日**；《仙药》《黄白》《极言》《祛惑》《遐览》各篇主旨；今本非完帙（原 116 篇，佚 40 余篇） |
| `eastern_alc_src_waidan` | 外丹 · 百度百科 | 金丹＝金液＋还丹，分水炼／火炼，火炼以砂汞最有名；秦汉起、魏晋为升仙之要、**唐代达高峰后衰落**；柳泌、赵归真主铅汞说，制含毒氧化汞与氧化铅，「使不少服丹的贵族、官僚、皇帝被毒死」；丹药成分含硫化汞、氧化汞、氧化铅、氧化砷、汞的氯化物；明代分天元／地元／人元三等；后世黄白术沦为烧银骗财 |
| `eastern_alc_src_fushi` | 服食 · 百度百科 | 服食又名服饵；《史记·封禅书》求不死药与李少君「祠灶化丹砂为黄金」；葛洪引《神农四经》分上／中／下三等药；药分**草木与金石**两大类并列名；**五石散＝五种未炼石药合研、主成分属砷类**；《抱朴子·遐览》著录《木芝图》《菌芝图》《石芝图》《服食禁忌经》《采神药治作秘法》等；服食术「已属历史陈迹」 |
| `eastern_alc_src_bencao` | 本草纲目 · 百度百科 | 52 卷／1892 种／11096 方／16 部 60 类；每药分**释名·集解·正误·修治·气味·主治·发明·附方**八项；**批判水银「无毒」「久服成仙长生」**之说，书商因而不敢刊行；1596 金陵版 2010 入选世界记忆亚太名录；亦自承收有今人视为迷信的内容 |
| `eastern_alc_src_bigu` | 辟谷 · 百度百科 | 别名却谷／绝粒／休粮；《庄子·逍遥游》「不食五谷，吸风饮露」；分**服气辟谷与服药辟谷**，服药者仍须进食杂食与药饵；《大戴礼记·易本命》「食气者神明而寿」；马王堆帛书《却谷食气篇》；**葛洪反对单行辟谷可致仙，称其为「一家之偏说」**，但仍称断谷者「身轻色好」 |
| `eastern_alc_src_shennong` | 神农本草经 · 百度百科 | 托名神农、实成书汉代；载药 365 种；**三品分类法**（上药 120 无毒久服不伤人／中药 120 有毒无毒斟酌其宜／下药 125 多毒不可久服）；**君臣佐使**与**七情和合**（单行／相须／相使／相畏／相恶／相反／相杀）；序录论剂型「宜丸宜散宜水煮宜酒渍宜膏煎」；原书早佚 |
| `eastern_alc_src_hanshisan` | 寒食散 · 百度百科 | **只**用于确认「寒食散／五石散」在医籍中的归属与存在；该页含组成、用量、服法、主治、加减，**完整不采用** |
| `eastern_alc_src_yunji` | 云笈七签 · 百度百科 | 张君房 1019 编《大宋天宫宝藏》、1025—1029 辑成此书；「三洞四辅」七部故称七签；原 120 卷、通行本 122 卷；**「大都摘录原文，不加论说」**；卷六十三至七十三「金丹部」、七十四至七十八「方药部」；人称小道藏 |
| `eastern_alc_src_hjfang` | 太平惠民和剂局方 · 百度百科 | 宋代太医局所属药局的**成药处方配本**，1078 年后初刊；崇宁间拟定制剂规范、大观时校正成五卷 21 门 279 方；绍兴十八年（1148）改称后增补为十卷 14 门 788 方；载主治、配伍与修制法——**只取「官方标准化成药确曾存在」这一制度事实**，方名与修制法一概不采用 |
| `eastern_alc_src_britannica_alchemy` | Alchemy · Britannica | alchemy 的目标包括「变贱金属为金银」与**寻找治病之方与延寿之法**；12 世纪拉丁欧洲命名；中国炼丹术主要保存在道教正集约 100 种「书」中；希腊／中国／印度以「The Art」或变化之词称之 |
| `eastern_alc_src_britannica_mercury` | Mercury poisoning · Britannica | 汞化合物对组织与功能有明确损害；急性（误服可溶汞盐）→ 消化道严重炎症、肾损伤、尿毒症；慢性（蒸气／经皮）→ 金属味、唾液过多、口腔炎、齿摇、牙龈蓝线、肢端麻木与震颤、抑郁等精神改变；有机汞主损中枢（水俣病），神经损伤可为永久；汞为神经毒物。**只作毒理风险定性，不采用其任何治疗／检测／防护方法** |
| `eastern_alc_src_zhihu_dandu` | 丹毒（现代医学病名）· 百度百科 | **读了但不采用**：该词条讲的是皮肤细菌感染病，与炼丹之「丹毒」不是同一概念。登记在此是为了防止后人把两个「丹毒」当成同一词条引用；本文件不引用其病理与治疗 |

`access: unavailable` **3** 条（如实登记，未引用其任何内容）：

| ID | 目标 | 失败原因 |
|---|---|---|
| `eastern_alc_src_zhwiki_fail` | 中文维基百科「中国炼丹术」 | 443 端口连接超时（dial tcp connectex 无响应）；维基搜索 API 亦同样超时 |
| `eastern_alc_src_baike_wushisan_ambiguous` | 五石散 · 百度百科 | 抓回的**是多义词消歧义页**（义项：寒食散／2014 年音乐专辑），未取到正文；改读 `..._hanshisan` 成功，五石散的成分说明改由 `..._fushi` 支撑 |
| `eastern_alc_src_baike_404` | 和剂局方 · 百度百科 | HTTP 404 与百科错误页；另「雷公炮炙论」条目亦 404；改读 `..._hjfang` 成功 |

检索说明（受限于本机网络）：中文维基 `zh.wikipedia.org` 全程不可达（连接超时），英文维基搜索 API 亦超时；Britannica 中文版正文为付费墙截断，故 Britannica 只引用了可读的英文条目。可核部分因此以百度百科（汇编性二手资料）为主，已在每条 `rights_note` 注明「正式入库应替换为点校本与专门研究」。**没有一条来源被编造，失败的 3 条原样登记为 `unavailable`。**

---

## 验证结果（用未改动的 `app.encyclopedia.import_file`，临时库）

验证脚本放在 `temp://scratch/`（一次性，不落进工作区），临时库在系统 temp 目录，**未触碰 `data/`、地图／故事／玩家数据库**。`app/encyclopedia.py` **未做任何修改**。

```
adapter 识别（detect_adapter）：human-encyclopedia
   （因全部条目带 tags；category 与 genres 仍会被导入器追加 category:/genre: 标签）
schema_version=1  status=candidate  group=eastern-alchemy  genres=[eastern_fantasy, xianxia]
elements=20  sources=15

七节自检：details_missing=[]  details_nonstring=[]  all_seven_str=true
状态：review_status 唯一值 [needs_review]；detail_status 唯一值 [needs_detail]；category 唯一值 [item]
关联自检：dangling_related_ids=[]（只指向本组 ID）  dangling_source_ids=[]
标签自检：bad_tag_format=[]  handwritten_genre_category_tags=[]
        kind:item 20/20、tradition:eastern 20/20、effect: 20/20、grade: 20/20、route: 20/20、cost: 20/20、role: 20/20

第 1 次导入（新建库）：
  namespace=eastern-alchemy  group_id=eastern-alchemy  adapter=human-encyclopedia
  batch_id=1  batch_hash=f5f3ff39…30a793  idempotent=false
  elements=20  element_versions_written=20  sources=15  source_versions_written=15
  relations=52  unresolved_relations=[]  ambiguous_relations=[]

第 2 次导入（同一文件、同一库）：
  batch_id=1（同一批次）  idempotent=true
  element_versions_written=0  unchanged_elements=20
  source_versions_written=0  unchanged_sources=15
  relations=0  unresolved_relations=[]  ambiguous_relations=[]
  → 复导幂等 ✔

第 3 次导入：idempotent=true，batch_id 仍为 1 ✔

库内核对：
  elements=20  element_versions=20  sources=15  import_batches=1
  groups: [(eastern-alchemy, eastern-alchemy, human-encyclopedia, human, legacy_schema=0)]
  element_sources.status 全部为 batch（60 条引用全部在同批解析，无跨库 pin）
  关联目标 19 个，_relation_status 全部 resolved → 未解析关联 0 ✔

标签检索（导入器追加后共 88 个去重标签）：
  tag=kind:item           → 20 条
  tag=effect:healing      → [eastern_alc_healing_pill]
  tag=grade:legendary     → [eastern_alc_longevity_pill]
  tag=cost:taboo_reagent  → [eastern_alc_shape_change_pill]
  tag=role:political_asset→ [eastern_alc_life_sustaining_pill]
  tag=genre:xianxia       → 20 条
  tag=category:item       → 20 条
  名称检索：element_names 103 行（20 name + 83 alias），别名归一化正常
            （示例：`还魂丹（坊间讹称）` 作为别名收录，可直接按 norm 命中）

导出与往返：
  export_document counts = {groups:1, source_versions:15, element_versions:20}
  export 中 52 条关联状态全部 resolved
  details_map 全为规范键自映射（k==v），details_extra 全空，无 legacy_schema
  export → restore 到空库 → 再 export：
    counts 相等 ✔  content_hash 相等 ✔  tags 相等 ✔  关联状态相等 ✔
```

安全约束自检（正则扫描整份 JSON，结果全部为 0 处）：

```
剂量数字（克/g/毫克/mg/钱/两/方寸匕）   0 处
温度数字（℃/度/摄氏度）                0 处
时长数字（分钟/小时/时辰/天）          0 处
配比数字（x:y）                        0 处
「建议服用」「配方为」「加水」「煎服」「泡服」  各 0 处
```

「可治 / 治疗 / 疗效 / 解毒方法」等处命中（合计 24 处）**逐条人工复核后确认全部是否定式表述**——即写在 `excludes`、`adaptation_limits`、`historical_scope`、`rights_note` 里的「**不**可治……」「**不**提供任何……治疗、处置方法」「不作任何现实疗效主张」。没有一处是正面主张或可照做的指引。

---

## 待主审裁定点

1. **adapter 走的是 `human-encyclopedia`（新 schema），不是 element-catalog（旧 schema）。** 因为全部条目带 `tags`，`detect_adapter` 按「全部有 tags → human」判定。旧组（`eastern.json` 等）走的是 `element-catalog` + `story_consequences`/`adaptation_limits` 的七节映射。**这是刻意选择**：用户要求的 `tags` 与 `details` 七节（`story_uses` / `historical_scope`）都是新 schema 的字段。是否要在全库统一口径，请主审决定；若要改回旧 schema，需把 `tags` 迁走并把七节改回旧键名，属一次结构性改动。
2. **`adaptation_limits` / `excludes` 等旧式字段作为顶层额外字段保留**。它们不写进 `details`，因此导入后**不进入 `details_extra`（实测为空），而是原样留在元素的 `payload` 里**（`payload` 逐字节保留原始 JSON）。好处是「长生不成立」「不给处方」这类边界既能被人读到、又不污染七节；代价是它们不在 `details` 的检索面上。若未来严格禁止额外顶层字段，需先定 schema。
3. **20 条 vs 目标 18—20**：落在上限。`固基丹`（把「筑基类」独立成条，与 `破境丹` 互为反面）与 `兽核转炼`（把「兽核炼化」从药材层独立成工艺条）是两条可能被认为可与 `聚气丹`／`beast_core` 物产条合并的条目。若要压到 18 条，建议并这两条，并保留其内容作为对应条目的分节。
4. **`category` 全为 `item`**（用户指定），因此「丹药品级与鉴伪」与「丹炉与火候」这两条**制度性内容也被归到 `item`**。若主审认为它们更接近 `institution` / `economy`，需改 `category` 并同步调整 `genre:`／`category:` 自动标签。
5. **`grade:` 前缀被复用于三个非丹品档位**（`grading_scheme` / `infrastructure` / `side_effect`）。这样能让「品级」成为统一检索轴，但语义上 `grade:infrastructure` 读起来略别扭。备选方案：拆成 `class:` 前缀，代价是检索要查两个轴。
6. **伦理判定的力度**：本组把「以智慧妖族之核或血入药」「以活人试丹（含儿童、死囚、流民）」一律写成**罪行**，并要求写出追诉者与后果。这比 `eastern-biology.json` 的 `eastern_bio_demon_core_hunt` 更硬（那边只是「不入本条、不得当作矿产开采」）。若某个故事包想让「猎妖炼丹」成为常态，须另立条目并给出对等后果，**不得以本条默认**。
7. **「丹毒」一词的歧义**：本文件的「丹毒」一律指设定层的服丹蓄积损伤，与现代医学同名疾病无关，已在 `eastern_alc_src_zhihu_dandu` 与该条 `definition` 双向声明。若入库时要做全文检索，建议加一条词典式说明，避免与医学词条撞名。
8. **证据强度的分布不均**：`eastern_alc_pill_toxin`、`eastern_alc_longevity_pill`、`eastern_alc_furnace_fire`、`eastern_alc_grain_avoidance_pill` 四条史实层较实；`eastern_alc_qi_gathering_pill`、`eastern_alc_breakthrough_pill` 基本是类型惯例，来源仅作「诉求存在」的旁证。若主审要求统一证据强度，需给后两条补专门的类型研究来源（本组未取得）。
9. **未取得的研究缺口**（各条已标「待补」）：古代丹炉的实际形制与控温手段（考古／技术史）、古代服丹中毒的临床记录（医学史）、古代丹药市场的实际分级与验真方式、民间伤药的实际流通规模与价格、「丹毒」在文献中的具体所指。
