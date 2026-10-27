# 现实基础库·人文历史宗教社会（reality-human 组）

对应 `reality-human.json`。状态：**候选资料**，不是数据库记录，也没有被任何故事包采纳为正典。本文件只提供扫读视图、来源说明与已知不足；完整字段（summary / variants / requires / excludes / entry_modes / introduction_limits / evidence_note / details 七节）以 JSON 为准。

- 顶层：`spec` 统一格式，`genres: ["real_world"]`，`group: "reality-human"`，条目 ID 前缀 `reality_human_`。
- 共 **31 项**元素，全部 `detail_status: "needs_detail"`（未经详细审查，不得标 reviewed_detail）。
- 来源 **55 条**，其中 `access: "read"` **44 条**、`unavailable` **11 条**（失败如实记录，未作为任何元素的 source_ids）。其中 **5 条为导言/摘要级**（src_01、src_21、src_34、src_35、src_50：仅有导言、目录或摘录拼合），已在 `supports` 与 `rights_note` 中明写「不能支撑全文细节」，**不当作正文完整阅读**。
- 每条含统一 14 字段 + `knowledge_kind` + `details` 七分节（definition / mechanism / conditions / exceptions / story_consequences / adaptation_limits / evidence_and_uncertainty）。

## 一、这个组在收集什么

用户要求「现实基础库，包含能参与故事的科学历史宗教等」，本组负责人文、历史、宗教、社会一侧；明确**不做百科全书、不建 DB、不写代码**。因此取舍标准是：

1. 只收**能影响人物行动、世界构建或事件因果**的现实知识，不收冷知识陈列。
2. **不与已有四组复制同名条目**。与 `society` 组（历史/现代制度）、`eastern`（仙侠）、`western`（西幻）、`steam-horror`（蒸汽与灵异）重叠的母题，本组只保留「现实机制的通用视角」，其余用 `related_catalog_ids` 指向已有真实 ID。校验结果：**113 条关联引用，0 条指向不存在的 ID**（其中 6 条跨指 `reality-physical` 分区），与其它四组**无同名冲突**。
3. 每条并置四类陈述且不混同：可检验的现实机制、限定地域时期的历史事实、信仰/传统的记述、本项目创作归纳。`knowledge_kind` 分布：historical 16、mixed 10、belief_description 5。

### 与 society 组的分工（刻意回避重复）

| 母题 | society 组已有 | 本组处理 |
|---|---|---|
| 户籍、保甲、编户 | `society_household_register`、`society_military_household` | **不另立条目**。原拟「人口统计与流动控制」条目在核对后删除，相关机制并入 `reality_human_migration_voluntary_forced` 并关联到该条 |
| 习惯法、审级、领主司法 | `society_customary_law`、`society_court_hierarchy`、`society_lord_jurisdiction` | 本组只写**证据形态**（神判/助誓/形式证据/口供）与**法源竞合**，不重复审级与习惯法本身 |
| 契约、票据、铸币、钱庄 | `society_customary_law`、`society_bill_of_exchange`、`society_coinage_mint`、`society_deposit_house` | 本组只写**货币作为约定如何失效**，不写票据与铸币制度 |
| 宗族、修会、堂区、异端审判 | `society_lineage_clan`、`society_religious_order`、`society_parish_clergy`、`society_heresy_inquisition` | 本组写**祭祀组织**与**信仰实践如何组织社群**，组织程序本身不重复 |
| 大学、私塾、义务教育 | `society_medieval_university`、`society_private_academy`、`society_compulsory_school` | 本组写**识字门槛的层次**与**知识交流制度**（社团/通信/可复现报告），不写学校制度 |
| 行会、商团、贸易同盟 | `society_craft_guild`、`society_merchant_guild`、`western_trade_league` | 本组写**商队与中转的物质约束**（载重/速度/补给），不写商人组织章程 |

## 二、扫读表

类别沿用采集规范的 snake_case：institution / organization / economy / place / power。知识类型：混=混合、史=历史事实、信=信仰记述。

### 2.1 时间、计量与货币（6 项）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_calendar_lunisolar_types | 历法类型与阴阳合历 | institution | 混 | 把太阳年与朔望月拼成可用日期系统，决定节令、租期与节庆落在哪天 | src_01/02/03/04 |
| reality_human_intercalation_calendar_reform | 置闰、改历与颁历权 | institution | 史 | 用闰月闰日拉回天象并由权威公布，改历是高风险的知识与政治行动 | src_01/02/03 |
| reality_human_era_year_counting | 纪年：年号、干支与纪元 | institution | 史 | 给年份编号的方式，决定文书的「哪一年」能否被异地读懂并换算 | src_03/04 |
| reality_human_weights_measures_local | 度量衡的地方差异与换算 | institution | 史 | 同名单位在不同城镇指不同大小，交易与赋税永远需要校准与仲裁 | src_05 |
| reality_human_metrology_standardization | 统一计量：政令、原器与执行 | institution | 史 | 技术难点不在宣布，而在复制原器、巡检与让人真的照做 | src_05/01 |
| reality_human_money_as_convention | 货币作为社会约定与信用崩塌 | economy | 混 | 价值来自共同预期而非材质；预期崩掉后出现实物、外币与黑市计价 | src_06 |

### 2.2 人口、亲属与继承（4 项）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_migration_voluntary_forced | 迁移：自愿、强制与难民 | institution | 史 | 居住地永久改变；落地后能否定居取决于身份而非抵达本身 | src_07/11 |
| reality_human_kinship_descent_terminology | 继嗣规则与亲属称谓 | institution | 史 | 规定谁算「自己人」并据此分配义务与财产；称谓是权利地图 | src_08/10 |
| reality_human_marriage_alliance_dowry | 婚姻缔结、聘财与嫁妆 | institution | 史 | 被承认的结合同时是两家的资源交换，媒人与聘财把私事变成可追索的契约 | src_09/08 |
| reality_human_inheritance_partition | 继承、分家与遗嘱 | economy | 混 | 财产如何转移、遗嘱自由到什么程度；分家决定家业集中还是切碎 | src_10/08 |

### 2.3 文书、证据与知识传播（6 项）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_document_archive_record | 文书、档案与记录的保管 | institution | 史 | 档案保留的是办事过程本身，因此能证明「当时谁说了什么」 | src_11/13/33 |
| reality_human_evidence_ordeal_confession | 证据：神判、宣誓与口供 | institution | 史 | 审判方式规定了「谁的话算数」，也规定了冤案如何被制造与推翻 | src_12/24 |
| reality_human_literacy_scribal_training | 识字门槛与书吏培养 | institution | 混 | 能读、能写、能按格式起草公文是三种能力，各自对应不同社会位置 | src_13/14 |
| reality_human_interpreter_contact_language | 通译、接触语言与贸易共同语 | institution | 混 | 语言不通时人们造出简化共同语；掌握中介语言者握有议价与欺骗空间 | src_16/13 |
| reality_human_scripture_translation_canon | 经典翻译与正典形成 | organization | 混 | 译经过程同时决定哪些书算经典，译本反过来塑造礼仪与权力 | src_15/18/13 |
| reality_human_printing_reproduction | 印刷与文本复制 | economy | 史 | 改变的不是「有没有书」，而是「谁能读同一版本、错误多快传遍所有人」 | src_32/33/13 |

### 2.4 信仰实践与宗教组织（6 项，均为信仰记述）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_ancestral_rites_household | 祖先祭祀与家祭组织 | organization | 信 | 把死者中的一部分立为祖先；谁能主祭决定谁算这个家、这个族的人 | src_21/26/08 |
| reality_human_daoist_ritual_ordination | 道教教团、科仪与授箓（限汉代至清） | organization | 信 | 靠师徒授箓、斋醮科仪与宫观经济维持；道派与朝代差别极大 | src_19/35 |
| reality_human_buddhist_sangha_lay | 佛教僧团与在家众（限南亚至东亚） | organization | 信 | 出家众依戒律聚居、在家众以供养换教法；寺院兼为地主与教育节点 | src_18/17 |
| reality_human_christian_parish_sacrament | 基督教教区与圣事（限中世纪西欧） | organization | 信 | 以堂区为基层、以圣事为常规服务，同时是户籍、救济与舆情节点 | src_24/17/26 |
| reality_human_islamic_practice_community | 伊斯兰礼仪实践与社群（限7世纪后） | organization | 信 | 念礼课斋朝把分散信众组织成可协调社群，也生成学者权威与争议 | src_20/04/22/25 |
| reality_human_festival_annual_cycle | 节庆与年度仪式周期 | organization | 混 | 规定何时停工、聚众、祭祀与结算，是劳工、市场与权力共同的时间表 | src_27/26/01/03 |

### 2.5 宗教法、基金与朝圣（3 项）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_religious_law_secular_forum | 宗教法与世俗法的竞合 | institution | 史 | 同一件事可能落在两个法庭管辖里；选哪个法庭、由谁执行更决定结果 | src_25/24/12 |
| reality_human_waqf_endowment | 宗教基金与永久捐赠（瓦克夫） | economy | 史 | 资产永久捐出后不可变卖抵债没收；既供养公益，也把不动产锁出市场 | src_23/25 |
| reality_human_pilgrimage_route | 朝圣路线与沿线供给 | place | 混 | 定期把人流导向圣地，必然长出旅舍、向导、护路团体与沿途收费者 | src_22/29/28 |

### 2.6 贸易、水利、资源与技术（6 项）

| ID | 名称 | 类别 | 知识 | 一句话 | 主要来源 |
|---|---|---|---|---|---|
| reality_human_caravan_trade_route | 商队、中转与长途贸易 | economy | 史 | 无人走完全程，货物分段转手，价差与风险在一站站被分摊与转嫁 | src_29/28/30/34 |
| reality_human_irrigation_water_rights | 水利设施与用水权 | economy | 混 | 渠系建成后上下游被物理绑定，必须有人按次序放水、按份额摊派维护；大型渠系的用水者常只有对『供水服务』的权利 | src_45/46/47/48/49 |
| reality_human_slavery_debt_bondage | 奴役、债役与人身依附的层级 | institution | 史 | 与农奴制、契约仆役的差别在法律人格、束缚对象与生产资料归属 | src_42/07/43 |
| reality_human_resource_endowment_polity | 资源禀赋与政治组织的形成 | institution | 混 | 资源的可集中/可运输/可征税性影响权力结构，但资源不决定制度 | src_30/29/28 |
| reality_human_science_institution_exchange | 科学社团、通信与可复现报告 | organization | 史 | 靠聚会、通信与论文建立「别人能否重复」的标准，而非靠个人权威 | src_31/32/17 |
| reality_human_technical_diffusion | 技术扩散的路径与阻滞 | power | 史 | 靠人和物走通的路，不靠原理高明；落地取决于材料、工艺、需求与组织 | src_33/32/30/31 |

## 三、地域与时期限定（写作时必须守住）

本组不把任何一地制度当作全球通则。各条的地域/时期范围已在 `name`、`introduction_limits` 与 `details.adaptation_limits` 中明写，汇总如下：

| 条目 | 限定范围 | 不可外推之处 |
|---|---|---|
| calendar_lunisolar_types | 阴阳合历详例限中国传统历法；太阴历例限伊斯兰教历的宗教用途 | 不得把十九年七闰当作「古代历法通则」；伊斯兰历条目不表示所有穆斯林地区民用历一致 |
| intercalation_calendar_reform | 改历实例限中国历代；格里历改革限欧洲 | 不得让改历在没有观测与颁历网络的世界里一次成功 |
| era_year_counting | 干支与年号限中国；希吉拉纪元限伊斯兰 | 未取得年号制度专门来源，相关表述较略 |
| weights_measures_local / metrology_standardization | 中国度量衡史（秦、隋、1928/1984）＋现代 SI（BIPM） | 不得把中国单位体系当「东方通用」，也不得假定所有统一运动都成功；SI 是近现代国际约定制，不能倒推古代 |
| money_as_convention | 一般机制；实例含战后德国、高通胀国家 | 机制解释带经济学分析立场，不当作史料；不对任何现代国家货币政策作普适断言 |
| migration_voluntary_forced | 定义与分类为通则；数据为近代以来估计值 | 不用于任何具体国别政策的普适断言 |
| kinship_descent_terminology | 术语与分类为学科综述；易洛魁例为个案 | 19 世纪进化阶段说（群婚、母权、原始杂交）已被来源明确视为缺乏证据的推测，本组不采信 |
| marriage_alliance_dowry | 兼含现代法律与跨文化材料 | 不用于推断任何地区「历来如此」；中国六礼、欧洲教会婚姻法演变未细述 |
| inheritance_partition | 技术结构为通则；例外含塞尔维亚、苏联、以色列等团体共有制 | 不得把长子继承当作所有农业社会通则（均分、幼子继承、兄弟共有都真实存在） |
| document_archive_record | 制度叙述以近代欧美（1789/1796 法国）为主线 | 中国古代架阁库、寺院文书、教会档案的具体形态未取得来源，标为本项目归纳 |
| evidence_ordeal_confession | 以欧洲法制史为主（神判废止 13 世纪、决斗至 14—15 世纪、罗马—教会法形式证据） | 不表示其他法系同构；中国勘验、五听、众证定罪未取得来源，只作机制类比 |
| literacy_scribal_training | 通则；纸与印刷年代为物质条件 | 「记账式/公文式/经典式」三层分法为**本项目归纳**，非学界通行分类；不给任何历史识字率百分比 |
| interpreter_contact_language | 接触语例证跨文化（Tok Pisin、尼日利亚、比斯拉马、奇努克、Hiri Motu） | 皮钦与克里奥尔的起源关系学界仍有争论，两种意见并列；具体通译制度（四译馆、dragoman）未取得来源 |
| scripture_translation_canon | 七十士译本限埃及希腊语犹太社群（前3—前2世纪）；佛教经典传播限南亚至东亚 | 信仰层面（译本是否「正确传达神意」）不作判定，不比较诸译本优劣 |
| printing_reproduction | 东亚活字（至迟750年已知 / 现存最古印本1377年）、欧洲机械化（1439诉讼、1455圣经） | 三处来源年代口径不同，并列保留不合并；中国雕版兴衰与欧洲印坊行会未取得来源 |
| ancestral_rites_household | 中国（新石器晚期至帝制时期）为主；另及古希腊罗马家内神龛 | **src_21 是专题摘要页而非完整条目**，细节不足；宋以后宗族形态（祠堂、祭田、族规）由 society 组承担 |
| daoist_ritual_ordination | 汉代至清，中国 | 不把道教等同于道家哲学；不把道教当作单一整体；不把修真小说功法体系当作现实宗教 |
| buddhist_sangha_lay | 南亚至东亚，公元前6—前4世纪起源至近世 | 上座部/大乘/金刚乘差别极大不可互推；佛陀生卒年代学界有分歧，照来源并列 |
| christian_parish_sacrament | **限中世纪西欧** | 不适用于东正教地区；不把天主教会制度当作「基督教默认形态」 |
| islamic_practice_community | 7 世纪后；逊尼与什叶分类不同 | 不把某一地区实施方式当作全体穆斯林实践；天课不等于现代税制 |
| festival_annual_cycle | 中国新年为详例；斋期漂移限纯太阴历 | 民俗与禁忌按信仰记述处理，**不表示禁忌有实际因果效力** |
| religious_law_secular_forum | 跨传统机制比较（伊斯兰、基督教欧洲） | 未核实任何具体国家现行制度，故不对当代法律适用作断言；中国历代僧道事务管辖未涉及 |
| waqf_endowment | 伊斯兰世界；奥斯曼例 | 具体不动产占比未核实；不与基督教教产（benefice）作过度类比 |
| pilgrimage_route | 世界各宗教的朝圣通则；商队数据限亚洲与北非沙漠 | 不写具体地名与年代（未取得具体路线专门史） |
| caravan_trade_route | 亚洲与北非沙漠；丝路自长安至黎凡特 | 载重与速度为历史常见值，不等于所有路线定额；具体商路年代分段未核实 |
| irrigation_water_rights | 水权形态分属罗马法/民法/普通法/美国西部/现代行政特许，**不得互推** | **FAO 为法律与制度分析，不等于任一具体历史地区实情**；渠边农户「只有服务权」是概括，适用到某地需再核；中国古代渠堰具体组织形式仍无来源 |
| slavery_debt_bondage | 跨文化比较（希腊罗马、伊斯兰、加勒比、非洲等） | 学界对定义无共识（来源明说），本组不采单一界定；不为任何强制劳动作正当化叙述 |
| resource_endowment_polity | 无地域断言，仅分析框架 | **明确排除资源决定论**；未取得任何地区的资源—政体关系专门研究 |
| science_institution_exchange | 16—17 世纪欧洲；1662/1666 社团 | 「科学革命」作为分期概念本身受史学批评，来源亦指出以欧洲为中心的问题 |
| technical_diffusion | 史例限造纸（751 中亚、793 巴格达、14 世纪欧洲）、坎儿井、印刷 | 「四要件」（载体/材料/工装/需求）为**本项目归纳**，非既有理论 |

### 3.1 与 reality-physical 分区的边界（已互为引用）

`reality-physical` 在本次交付过程中同时到货（32 条，均带 `details`），且其中的 `reality_phys_measurement_precision` **已主动引用本组的 `reality_human_metrology_standardization`**。为免 ID 变动牵连对方，本组这三条 ID 保持不动，并在两处写入分工：

| 本组条目 | physical 侧对应条目 | 分工 |
|---|---|---|
| `weights_measures_local` / `metrology_standardization` | `reality_phys_measurement_precision` | physical 写测量误差、精度与准确度之别、校准链的物理性质；本组写单位的地方差异、进位不一、换算仲裁与统一的政治执行 |
| `irrigation_water_rights` | `reality_phys_river_flood`、`reality_phys_groundwater_well` | physical 写河流水文、洪水、航道与地下水补给与井的物理机制；本组写水权分配、清淤劳役与水案的制度面 |
| `caravan_trade_route` | `reality_phys_road_transport` | physical 写路面、坡度、桥涵与维护水平对运量与速度的约束；本组写商队组织与分段转手的经济后果 |
| `resource_endowment_polity` | `reality_phys_carrying_capacity` | physical 写给定技术下的土地承载力上限；本组写收益的可集中/可运输/可征税性如何转为政治权力 |

**共同分担的缺口（本组已缓解一半）**：本组已通过 FAO（src_45—src_49）拿到水权与灌溉制度的权威机构正文，通过 BIPM（src_44）拿到测量体系正文；但 `reality-physical` 侧仍标注 NIST 页面超时未取得，且本组的 NIST/USGS 尝试均失败（src_51—src_53）。**测量这条线上本组仅有 BIPM 一个机构来源**（足够支撑 SI 的制度结构，但不支撑误差与不确定度），需`reality-physical` 侧补齐。

### 3.2 聚焦补证记录（测量/标准化 与 水利/灌溉）

按验收意见，只对「测量/标准化」与「水利/灌溉」两处做了一次聚焦补证，实际尝试并成功读到以下**权威机构原页正文**（不是搜索摘要、不是目录页）：

| 来源 | URL | 实际读到的支撑内容 |
|---|---|---|
| src_44 BIPM（国际计量局）SI 页 | https://www.bipm.org/en/measurement-units | SI 七基本单位；定义（固定定义常数）/实现（实验方法）/实用实现指引三层；CGPM—CIPM—BIPM 协调与国际比对、溯源与可比性 |
| src_45 FAO 立法研究 84 第 2 章 | https://www.fao.org/3/y5692e/y5692e03.htm | 水权的法律构造、自然水源范围、现代水权为限期行政用益权、可对第三方主张、执行责任在国家、水文循环前提、化石地下水例外 |
| src_46 FAO 立法研究 84 第 3 章 | https://www.fao.org/3/y5692e/y5692e04.htm | 土地不动/水流动导致水权更难管理；权利期限与安全（15—20 年、重大投资 50—70 年、西班牙 75 年、墨西哥 5—50 年、南非 40 年）；水权可中止且不补偿；条件与义务清单；美国西部先占原则的优先规则 |
| src_47 FAO 立法研究 84 第 4 章 | https://www.fao.org/3/y5692e/y5692e05.htm | 罗马法流水不可私有；法国民法典 1804 公私水之分；西班牙 1886 水法；英美临河权与「通常/非常使用」界限；加拿大草原省份年降水约 28 厘米与 1894 年另立水法 |
| src_48 FAO 立法研究 84 第 6 章 | https://www.fao.org/3/y5692e/y5692e07.htm | 渠系分级（干—支—斗—地块）；渠道非自然水源故渠边土地者无普通法水权；灌溉者常只有对「服务」的权利与年度合同；轮灌规则；灌溉管理转移（IMT）与用水户协会；国有工程上条件性不可转让使用权 |
| src_49 FAO 灌溉与排水论文集 29 | https://www.fao.org/4/t0234e/t0234e01.htm | 灌溉水质四类问题（盐分与淋洗、入渗率、离子毒性、杂项）；浅地下水位与排水前提；症状累积缓慢 |

**失败并如实登记（未用于任何条目）**：NIST 两个路径（404 / 超时，src_51、src_52）；USGS 两个路径（HTTP 405 跳到人机校验，src_53）；BIPM 三个子页（404，src_54）；BIPM About us（可达但无正文，src_55）；FAO 目录页（src_50，只证明文献存在与版本）。主代理提示的 NIST Technical Note 1297 目录页本次未采用——目录不能支撑机制。

**由此产生的实质修改**：`reality_human_irrigation_water_rights` 从「核心机制无来源」改为**四层来源支持**（工程形态／水权法律构造／历史路径／灌溉制度），`variants` 由「河渠/井灌/水册」改写为四种可辨识的水权制度形态（临河权、先占、行政特许、用水户协会份额）。`reality_human_metrology_standardization` 增加 SI 这第三条统一路径与 BIPM 来源。

**仍属本项目归纳、写作时只能当设计建议的部分**（已在条目内逐条标注）：清淤劳役作为征发人手的合法理由；水册可继承、可买卖、可伪造；「按规矩就能把一家人推到绝境」的具体因果；古代中国渠堰的具体组织形式。

### 3.3 三对相邻条目的分工（验收决定：全部保留，不合并）

| 对照 | 分工 |
|---|---|
| `calendar_lunisolar_types` ↔ `intercalation_calendar_reform` | 前者写天文机制（月长、闰法、年首、日界为何必须取舍）；后者写制度与政治协调（颁历权、观测队、反对者与责任） |
| `weights_measures_local` ↔ `metrology_standardization` | 前者写差异本身与换算仲裁；后者写把差异收拢成一套的治理过程（颁令、原器或定义、巡检、中央或国际协调） |
| `printing_reproduction` ↔ `technical_diffusion` | 前者写印刷这一媒介自身的技术路线与成本结构；后者写跨地跨群传播的条件（载体、材料、工装、需求）与阻断 |

三对均已在两条里**互相写入 `related_catalog_ids`**，并在各自的 `adaptation_limits` 中写明「两条不合并」。按验收意见，不因相关而删条目。

### 特别声明：现代国别法律不作全世界默认

本组涉及法制的条目（证据、继承、宗教法竞合、瓦克夫、奴役）都以**历史制度与比较机制**为主，不对任何现代国家的现行法作普适断言。涉及中国当代法条的内容（劳动合同、社保、义务教育、警察、居委会等）**不在本组**，由 `society` 组承担并在该组文件中注明「地域性极强，不能当作现代社会通例」。本组同样拒绝把「中世纪西欧」「古典伊斯兰」「中国帝制」任一种经验写成全人类默认。

## 四、宗教条目的处理原则

用户要求宗教可以含道教、佛教、基督教、伊斯兰传统、祖先祭祀等分条，但**必须限定分支与时代，不以一个教义代表全部信徒，不把神迹当经验事实，不作价值排序**。本组的落实方式：

1. **分条且限定**：五条宗教条目全部在 `name` 里写明范围（「限汉代至清」「限南亚至东亚」「限中世纪西欧」「限7世纪后」），祖先祭祀条目在 variants 中区分家户内祭、宗族祠堂祭、家神家灵、国家性祭祀。
2. **不神迹化**：`knowledge_kind` 全部标为 `belief_description`。`details.exceptions` 与 `adaptation_limits` 中明确写出「属信仰记述，不作经验判断」；若故事设定中法术/神迹确有实效，必须**显式声明为超自然改写**，并与信仰记述分开标注。
3. **不价值排序**：五条的 `evidence_note` 与 `details.evidence_and_uncertainty` 中均写明「不判定真伪，也不在道教、佛教、基督教、伊斯兰等传统之间作高低排序」；不比较诸译本优劣。
4. **不用一个教义代表全部信徒**：道教的「正一与全真不能互推」、佛教的「上座部/大乘/金刚乘差别极大」、伊斯兰的「逊尼五功与什叶五信条十实践分类不同」、基督教的「新教拒斥罗马教会法而英格兰教会保留」都写进 `exceptions`／`variants`。
5. **排除两种常见混同**：不把道教等同于道家哲学（`excludes` 明写）；不把佛教等同于单一教义体系（`excludes` 明写）。
6. **来源可靠性声明**：道教条目的主要来源（百度百科）含明显的编者贬斥性表述（关于张修、张鲁立教来源），已在 `rights_note` 与 `evidence_note` 中明确「不采信为定论」。伊斯兰与基督教条目主要依据 Britannica，但同样只作背景核对。

## 五、来源说明

### 5.0 本次聚焦修订新增的来源（src_44—src_55）

| ID | 来源 | access | 级别 |
|---|---|---|---|
| src_44 | BIPM — The International System of Units（SI）https://www.bipm.org/en/measurement-units | read | 机构原页正文（制度结构） |
| src_45 | FAO Legislative Study 84 第 2 章 https://www.fao.org/3/y5692e/y5692e03.htm | read | 机构出版物章节正文 |
| src_46 | FAO Legislative Study 84 第 3 章 https://www.fao.org/3/y5692e/y5692e04.htm | read | 同上 |
| src_47 | FAO Legislative Study 84 第 4 章 https://www.fao.org/3/y5692e/y5692e05.htm | read | 同上 |
| src_48 | FAO Legislative Study 84 第 6 章（灌溉） https://www.fao.org/3/y5692e/y5692e07.htm | read | 同上 |
| src_49 | FAO Irrigation and Drainage Paper 29 Rev.1 第 1 章 https://www.fao.org/4/t0234e/t0234e01.htm | read | 同上（机制，不含操作配方） |
| src_50 | FAO Legislative Study 84 目录页 https://www.fao.org/3/y5692e/y5692e00.htm | read | **仅目录**，只证明文献存在与版本，未支撑任何机制 |
| src_51 | NIST metric-SI measurement concepts | unavailable | 404 |
| src_52 | NIST weights-and-measures / metric-SI | unavailable | 超时 |
| src_53 | USGS Water Science School（两条路径） | unavailable | HTTP 405，人机校验页 |
| src_54 | BIPM traceability / CGPM / SI revision | unavailable | 三个路径均 404 |
| src_55 | BIPM About us | unavailable | 页面可达但无正文（仅导航骨架） |

**许可声明**：FAO 各出版物**不是公有领域**。其声明为教学等非商业用途可复制传播但须完整注明出处、商业用途须事先书面许可。本项目只作要点改写与归纳，**不整篇转录、不复制原文段落、不存整篇原文**。BIPM 页为机构介绍性说明，同样只作机制与结构核对。

### 5.1 实际读到正文的页面：44 个（access: read）

优先机构/教育/可靠参考/百科；本组未使用官方法条（法条类内容由 society 组承担）。

| ID | 来源 | 访问 | 支撑范围（节选） |
|---|---|---|---|
| src_01 | Calendar（Britannica） | read | 历法定义与用途、日月年不整除、阴阳阳三分、埃及—儒略—格里历、日界与时辰、季节时与机械钟、市场周期长短不一；**正文末尾被截断** |
| src_02 | 农历（百度百科） | read | 阴阳合历、29.53 日朔望月、354—355 日、十九年七闰、无中气置闰、节气与月建、干支生肖、改历实例、1912/1929 推行公历、紫金山天文台编算与 GB/T 33661-2017；**夹带民俗叙述与编者判断** |
| src_03 | Chinese calendar（Britannica） | read | 阴阳合历结构、甲骨文所见 365.25/29.5、十九年七闰至迟春秋、节气每15度定闰、干支三千余年、历正竞争与罪责、102 种历书 |
| src_04 | Islamic calendar（Britannica） | read | 纯太阴历、30 年周期调十二月、354/355 日、不置闰月故节期约 32.5 年遍历四季、622 希吉拉、639 欧麦尔立纪元 |
| src_05 | 度量衡（百度百科） | read | 度/量/衡三分、人体基准、陶量与商代牙尺、汉书律历志五度五量五权与进位、商鞅方升、秦汉一尺约23cm、隋大小尺、1928 万国公制与市用制、1984 法定计量单位 |
| src_06 | Money（Britannica） | read | 货币定义与三功能、社会约定的强度、战后德国价格管制下的失效与香烟替代、1948 改革、外币计价、多种实物货币 |
| src_07 | Human migration（Britannica） | read | 迁移定义与排除项、自愿/强制/难民、推力拉力、大西洋大迁移与西伯利亚数据、奴隶贸易约两千万、二战驱逐与印巴分治、乡城迁移、移民权利缺失 |
| src_08 | Kinship（Britannica） | read | 血缘/姻亲/拟制、单系与双系、分类式与描述式称谓（易洛魁）、亲属制度承担生产与决策、继承为亲属制度附带结果、19 世纪阶段说缺乏证据 |
| src_09 | Marriage（Britannica） | read | 婚姻的法律功能、一夫一妻/多妻/多夫/群婚、内婚外婚、扩大家庭经媒人安排并伴聘财或嫁妆、核心家庭自择 |
| src_10 | Inheritance（Britannica） | read | 继承定义与前提、团体共有下无继承（扎德鲁加、集体农庄、基布兹）、法定顺序、遗嘱要件与争议、特留份、欧陆与英美术语差异 |
| src_11 | Archives（Britannica） | read | 档案定义与与图书馆之别、原始次序与完整性、法国 1789/1796、各国中央与地方分立体例、处置三问题、新载体 |
| src_12 | Evidence（Britannica） | read | 证据类型与鉴真、纠问式与对抗式、早期要求被告自证、神判与决斗、助誓人、13 世纪神判废止、罗马—教会法形式证据与拷问取供 |
| src_13 | Literacy（Britannica） | read | 识字依赖教学与社会约定、算术先于文字、古代识字限于少数且用于记账、两种理论、书写表面演进、文字系统多源 |
| src_14 | Oral tradition（Britannica） | read | 口传的规则性与表演性、Parry 与 Lord 的田野、荷马与吉尔伽美什与贝奥武甫的口传根底、阿尔巴尼亚口传保存法典、转录改变文本 |
| src_15 | Septuagint（Britannica） | read | 七十士译本的背景与年代、72 译者传说与其所据书信不可靠、译本风格不一、成为多种后续译本底本、基督徒使用与犹太社群停用、哲罗姆 382、正典与次经差异、抄本年代 |
| src_16 | Pidgin（Britannica） | read | 接触语定义与场景、简化特征、无母语者、可扩展为克里奥尔（Tok Pisin 等）、1807 广州词源、原住民接触语、生命周期模型与反驳 |
| src_17 | Monasticism（Britannica） | read | 修道制度定义、独身常见但非普遍、须有成文教义传统、本笃与巴西尔规则、佛教依律与在家众共生、抄写与教育医疗功能、5—8 世纪保存书籍 |
| src_18 | Buddhism（Britannica） | read | 起源时间与地域、佛陀年代分歧、四圣谛八正道涅槃、三宝、结集、部派与大乘与金刚乘、传播路线与王朝供养 |
| src_19 | 道教（百度百科） | read | 本土宗教以道为最高信仰、承袭方仙道黄老道、奉老子与道德经、太平道与五斗米道、寇谦之与陆修静整理仪范、陶弘景神仙谱系、唐代崇道与内丹、道士与宫观、修炼方式；**含编者立场段落，不采信** |
| src_20 | Pillars of Islam（Britannica） | read | 五功细节与减免规则、现金四十分之一与起征额、斋期与例外、朝觐时限、逊尼五功与什叶五信条十实践的分类差异 |
| src_21 | Ancestor worship（Britannica 摘要页） | read | 祖灵崇拜定义与目的、成为祖先的条件、中国新石器晚期与历史时期的普遍性、家长主祭、古希腊罗马家内神龛；**专题摘要页，非完整正文** |
| src_22 | Pilgrimage（Britannica） | read | 朝圣定义与跨宗教分布、动机、分离与圣地圣时相连、圣地内部仪式性移动、圣物回流、圣地叠合与等级 |
| src_23 | Waqf（Britannica） | read | 瓦克夫结构、所有权归属之争、管理人、不可变卖抵债没收、公共事业供给、家属受益、奥斯曼不动产、现代监管 |
| src_24 | Canon law（Britannica） | read | 教会法主体与范围、与世俗法分工、1054 分化、宗教改革后分化、格拉提安 1140、对世俗法各部门的影响 |
| src_25 | Sharia（Britannica） | read | 沙里亚的范围与伦理评价、《古兰经》约十分之一涉法律、卡迪与法律借用、fiqh 成文化、19 世纪后解释权威受挑战、多数国家限于家事领域 |
| src_26 | Rite of passage（Britannica） | read | 定义与普遍性、van Gennep 三阶段、常见类型、净化与死亡再生象征、娱乐与展演功能、考古证据 |
| src_27 | Chinese New Year（Britannica） | read | 15 天节期与日期区间、节前扫除与爆竹红色、红包龙舞元宵、饮食象征、禁忌、1990 年代中期七天假、生肖十二年 |
| src_28 | Silk Road（Britannica） | read | 路线与长度、商队通道、货物与宗教双向传播、无人走完全程与分段转手、兴衰节点、鼠疫西传说 |
| src_29 | Caravan（Britannica） | read | 商队定义与骆驼优势、载重与速度、驼队编组、规模实例、出发受水草与朝觐日期约束、商队旅舍结构、衰落原因 |
| src_30 | Qanāt（Britannica） | read | 坎儿井引水原理、隧道长度、起源约 2500—3000 年前于伊朗、东西传播、今日使用状况 |
| src_31 | Scientific Revolution（Britannica） | read | 16—17 世纪科学思想剧变的具体内容、科学独立、信息激增与报告规范、1662/1666 社团、哥白尼/第谷/开普勒/伽利略的具体节点 |
| src_32 | Printing press（Britannica） | read | 东亚活字与最古印本 1377、1439 斯特拉斯堡诉讼、1455 古腾堡、木制机每小时 250 张、金属机与滚筒与动力、轮转机 8000 张、胶印与数字印刷 |
| src_33 | Paper（Britannica） | read | 纸的定义与工艺、放马滩前 2 世纪纸片与 105 年记载、751 中亚与 793 巴格达与 14 世纪欧洲纸坊、1450 后需求激增、19 世纪木材浆 |
| src_34 | UNESCO Silk Roads Programme（项目主页） | read | 仅确认「对话之路」旗舰计划的机构背景；**不含史实内容** |
| src_35 | Taoism（Britannica） | read | 仅取得条目前段（本土宗教—哲学传统、两千余年、与儒家互补、对秘术态度）；**正文被截断** |
| src_42 | Slavery（Britannica） | read | 奴隶制定义与特征清单、定义争议、来源、存在条件、家内与生产性两型、奴隶社会与蓄奴社会之别、与农奴制/契约仆役/债役的区别 |
| src_43 | Contract（Britannica） | read | 契约定义与商业前提、非商业社会的替代担保、罗马法契约分类与西罗马解体后的失传、商人法庭 13 世纪、英陆路径分化；**本批条目未直接引用，留作后续细化** |

### 5.2 抓取失败（access: unavailable，11 条，均未作为任何元素的 source_ids）

| ID | 目标 | 失败原因 | 影响 |
|---|---|---|---|
| src_36 | Islamic law（Britannica） | HTTP 404 | 伊斯兰法改由 src_25（Sharia）支撑 |
| src_37 | Weights and measures / Measurement system（Britannica） | 前者仅一句释义、后者被订阅墙截断 | 度量衡改由 src_05 支撑；缺英文独立参照 |
| src_38 | History of science（Britannica） | 仅得导语，其余订阅墙 | 科学史改由 src_31 支撑 |
| src_39 | Irrigation（Britannica） | 抽取器报「正文重复」 | 水利已改由 src_45—src_49（FAO）支撑，该缺口已缓解 |
| src_40 | Festival（Britannica，拟) | HTTP 404 | 节庆改由 src_27、src_26 支撑 |
| src_41 | U.S. Naval Observatory — Introduction to Calendars | DNS 解析失败 | 历法缺一个官方天文机构的独立参照 |
| src_51 | NIST metric-SI measurement concepts | HTTP 404 | 计量机制改由 src_44（BIPM）支撑 |
| src_52 | NIST weights-and-measures / metric-SI | 超时 | 同上；NIST TN-1297 目录页未采用（目录不能支撑机制） |
| src_53 | USGS Water Science School（两路径） | HTTP 405 人机校验 | 水利机制改由 src_45—src_49（FAO）支撑 |
| src_54 | BIPM traceability / CGPM / SI revision | 三路径均 404 | SI 已由 src_44 同站实质页支撑 |
| src_55 | BIPM About us | 可达但无正文 | 机构定位改由 src_44 支撑 |

### 5.3 evidence_note 的写法约定

每条 `evidence_note` 都分两半写：**来源支持了什么**（带 src 编号，可直接核对）与**哪部分是本项目归纳**。另有三条硬约定：

1. **历史事实 / 信仰记述 / 设计归纳三分**，并在 `details.evidence_and_uncertainty` 里再复述一次归属。
2. **来源只作有限支持**，不当作对所有推演的证明。典型例子：坎儿井条目（src_30 只有工程形态，古代渠堰组织仍为归纳）、祖先祭祀条目（src_21 是摘要页）、资源禀赋条目（来源只有地理事实，制度分析全是归纳）、技术扩散条目（史例只能证明单次传播，不能证明四要件是普遍规律）。
3. **不虚构专著页码、不假装读过未读的文献**。所有 source 都是实际抓取到的网页；抓取失败 11 条如实登记并说明替代来源。**目录页与摘要页不算读过全文**：src_50（FAO 目录）只用于确认文献身份与使用条款，src_34（UNESCO 项目页）不支撑任何机制，src_21（祖先崇拜摘要页）最薄，src_01/src_35（Britannica 被订阅墙截断）只读到前段。

## 六、已知不足（必须交代，不是免责套话）

**来源结构层面**

1. **英文来源集中在 Britannica 一家**（其余为百度百科两条）＋此次新增 BIPM 与 FAO。缺少博物馆藏品说明、学术专著与一手史料，因此「机制清楚、细部存疑」。**博物馆与教育机构来源本组仍未取得**，属未达标项。
2. 美国海军天文台（官方天文机构）页面 DNS 解析失败，历法条目因此缺一个独立的天文机构参照。
3. **抓取失败共 11 条（均未用于任何条目）**。其中**水利条的缺口已在聚焦补证中解决**：原 irrigation 页面抓取失败，但 FAO 四个章节正文已补上；仍存在的失败是 NIST 两路径、USGS 两路径、BIPM 四页、天文台一页与 FAO 目录页。
4. Britannica 多个词条被订阅墙截断（Calendar、Taoism、History of science、Measurement system），实际只读到前段；另有 5 条来源本身就是导言/摘要级（src_01、src_21、src_34、src_35、src_50），已在 `rights_note` 明写不能支撑全文细节，**未把它们当正文完整阅读**。
5. `Ancestor worship` 是摘要页而非完整条目，内容由关联条目摘录拼合，细节最薄。

**内容覆盖层面**

6. **中国材料偏多，其他文明偏少**：度量衡、历法、纪年、道教、祖先祭祀、节庆均以中国为主；南亚、非洲、美洲、大洋洲只在迁移、亲属、奴役、朝圣条目中以通则或个案出现。这是本批的实际偏差。
7. **欧洲中世纪材料的细部靠 society 组**：庄园、什一税、教区经济、封土继承等具体制度不在本组，本组只写通用机制。
8. 多条目的**关键机制标为「本项目归纳」而未取得来源**，须后续补证：水利的水册与清淤劳役（水权主体已补上）、档案的「办事过程副产品」论、继承的「分家细碎化致家道中落」、节庆的「债务以节期为结算界」、天课的「征收名单即政治名单」、科学社团的「优先权与保密对立」。
9. 未取得任何**量化数据**：不给历史识字率百分比、不给瓦克夫占不动产比例、不给历法精度数值、不给统一计量的公差范围。这符合「不虚构」的约束，但也意味着这些条目不能直接支撑需要精确数字的情节。
10. **三对相邻条目曾有边界模糊**——已按验收决定处理：**全部保留、不合并**，并在两条里互相写入 `related_catalog_ids` 与分工说明（见 3.3）。
11. `reality_human_migration_voluntary_forced` 原拟另立「人口统计与流动控制」条目，核对后发现与 `society_household_register`／`society_military_household` 高度重叠，**已删除该条目**，其机制要点并入迁移条目的 `related_catalog_ids` 与文字说明。这是本组唯一一次主动删条，特此记录。
12. **未通读 `reality-physical` 全部 32 条**：只在发现它引用本组 ID 后，逐个比对了与本组相邻的 5 条（measurement_precision / river_flood / groundwater_well / road_transport / carrying_capacity）。其余 27 条可能仍有潜在重叠（如农业起源、食物保存与节庆、轮作与赋役），本组未逐条比对。这是跨分区去重的一个未完成项。

**流程与状态层面**

13. **验收状态：仍为 `needs_detail`**。本次只做了聚焦补证与分工标注，未做全面详细化，也未改 `detail_status`；主审前不得升为 `reviewed_detail`。宗教 5 条的 `belief_description` 标签保留不动。
14. 本组**未做**依赖展开、兼容性检查与版本固定；`requires` / `excludes` 目前是自然语言，尚未结构化。这与采集规范「候选阶段」的定位一致，但入库前必须补做。
15. `entry_modes` 只描述开局绑定后的显现方式（existing / discovery / player_proposal），**不是运行中重新选库的入口**。本组 31 条中：单一 existing 17 条、existing+player_proposal 6 条、existing+discovery 6 条、三者兼有 2 条（`printing_reproduction`、`technical_diffusion`）。没有条目被标为「可运行中跨库导入」。

## 七、下一步（供主代理决定，本组不代做）

- **补来源层级**：优先补博物馆藏品说明（度量衡、造纸、印刷）、教育机构页面（历法、宗教实践）、以及一手史料选段（汉《律历志》、教会法汇纂、教法手册）。这是把条目从 needs_detail 提到 reviewed_detail 的前提。测量与水利已补上 BIPM 与 FAO，但仍缺博物馆与大学来源。
- **补失败方向**：水利（水权与水册）、中国宗族与服制、中国僧道事务管辖、堂区登记与告解实践、天课征收史与朝觐组织史。其中水利的水权主体已补，仍缺中国古代渠堰制度与水册实物；其余四项仍是空白。
- **三对相邻条目已按验收决定保留不合并**（见 3.3），不再列为待决项。
- **与 society 组做一次人工去重**：机器校验已确认无同名冲突、113 条关联全部有效，但「同一母题多形态」是否该在总目录标注，需人工判断。
- **与 reality-physical 分区的边界已逐条写入**（见 3.1）：测量/水利/道路/承载力四处已互为引用，但 `reality-physical` 交付后我未能通读其全部 32 条，细节分工需主代理复核一遍。
- 本组**未**做 git 提交、未动 `data/`、未动 StoryPackage、未改任何源码；除本文件与 `reality-human.json` 外未修改其他文件。
