# 跨题材元素候选总目录（第一批）

> ## ⚠ 状态：六组 `details` 已齐备，但**全库没有一条通过内容主审**
>
> **本轮（第二轮收尾）只做：结构层核对 + 授权范围内的四类勘误（引用链补齐、两条定义补全、一条证据注释改写）。不做事实核验，不新增/删除条目，不升 `reviewed_detail`。** 下面数字均由本环节直接读六组 JSON **逐项重算**，不是照抄各组自述。
>
> - **候选总数 274 条**：四个虚构题材组 54 / 54 / 53 / 50（合计 **211**，ID 集合未变，无新增无删除）＋ 现实基础库 `reality-physical` **32** ＋ `reality-human` **31**。
> - **`details` 覆盖 274/274**，七节均非空；`western` 另加可选 `parameter_dimensions`（54/54）。
> - **`detail_status` 274/274 = `needs_detail`，`reviewed_detail` 为 0**。七节齐备 **≠** 事实已核，本轮**未升格任何一条**。
> - **来源引用链已修复**：`society` 21 条 + `steam-horror` 38 条把正文已引的 `read` 来源补进 `source_ids`（共 59 条元素 / 74 处）；**全库仍无一条引用 `search_only` / `unavailable` 来源**。
> - **现实库两分区均已交付、均未封版**；`reality-physical` 四条点名勘误的文案层要求已补齐（重力载荷、测量术语、食物保存、饮水 WHO 定义），但**未重抓来源正文复校**，见 §11.3。
>
> 仍然成立的一句话：**原 211 个条目固定不变**，「`details` 已补齐」与「证据已核实」是两件事；本目录的任何统计与报告**都不是全内容认证**。

本目录是一片**候选资料的集成视图**，不是任何东西的正式实现。请先把以下三条读三遍：

- **不是世界正典**：没有任何一条被任何 StoryPackage 采纳。目录里存在一个元素，不等于任何一个世界里有它。
- **不是数据库**：没有建表、没有 schema 约束、没有迁移。`shared-themes.json` 只是人写出来的聚类清单，不被代码读取。
- **不是可执行规则**：`requires` / `excludes` / `introduction_limits` 都是自然语言条件，引擎不认它们，也不会因为写了就生效。

### 审查状态（重要）

按已定稿的审查标准：

- **`reviewed_detail` 仅由主代理逐条实质核验后才能升格**，采集代理一律保持 `needs_detail`。
- **写了 `details` 七节 ≠ 事实已核**。七节只是把「机制、前提、例外、后果、跨题材边界、来源与不确定性」写全了，不代表其中断言被验证过。
- 在逐条核验之前，任何条目**保留候选状态**。本目录的任何统计与报告**都不是全量认证**。
- 可以用文字区分「详情已补齐」与「证据待核」，但**不擅自改 schema 的状态字段**。

另：本目录的每个条目都是**首批候选摘要**（`summary` 只做到「能让人快速认出这是什么、为何影响剧情」，实测 42—109 字），**不承担完整定义**。按现行规范，`200—350 中文字符` 只作为**扫读摘要的参考**，对完整条目**不设篇幅上限**；完整定义靠 `details`（定义／机制／前提／例外／后果／跨题材边界／来源与不确定性分节）与 `detail_status`（summary_only / needs_detail / reviewed_detail）。

**原 211 条在详细化开始前均无 `details` 字段**；现已六组全部补齐七节（274/274），但在未逐条实质核验前**仍为候选**（`needs_detail`），绝不因为「摘要写得长」或「七节齐了」就标 `reviewed_detail`。还剩哪些证据缺口，逐条列在 `detail-gaps.md`。

## 一、文件清单

| 文件 | 作用 | 可否修改 |
|---|---|---|
| `collection-spec.md` | 采集规范（用户定的范围与规则） | 本环节不动 |
| `eastern.json` / `.md` | 组 1：东方玄幻 + 仙侠／修真 | 本环节不动 |
| `western.json` / `.md` | 组 2：西方奇幻 + 黑暗／哥特奇幻 | 本环节不动 |
| `society.json` / `.md` | 组 3：历史／架空历史 + 现代都市／现实社会 | 本环节不动 |
| `steam-horror.json` / `.md` | 组 4：蒸汽朋克 + 灵异／民俗恐怖 | 本环节不动 |
| `shared-themes.json` | 25 个跨组共享母题的聚类索引（只引用真实 element id） | **本环节未改**（引用校验全通过） |
| `README.md` | 本文件：总目录、统计与本轮审阅范围 | 本环节维护 |
| `detail-gaps.md` | 逐条列出证据缺口与待审风险，区分「证据缺口」与「字数可选优化」 | 本环节维护 |
| `review-notes.md` | 整合发现的问题、引用链缺口、待主审决定事项 | 本环节维护 |
| `reality-physical.json` / `.md` | 现实基础库—物理与自然侧（**32 条，已交付，已过一轮主审返修**） | 采集侧交付 |
| `reality-human.json` / `.md` | 现实基础库—人与制度侧（**31 条，已交付**） | 采集侧交付 |
| `reality-physical/` / `reality-human/` | 两分区的说明与口径（本环节按当前 JSON 实测刷新） | 本环节维护 |

## 二、统计（本环节实测，六组逐项重算）

> 本节数字**不是照抄各组自述**，而是本环节直接读取六个 JSON 逐项累加的实测值。统计口径：元素数= `elements` 数组长度；来源数= `sources` 数组长度；`details` 覆盖= `details` 对象内七个必需节均非空。

### 2.1 按组（含现实两分区）

| 组 | 元素 | 来源 | 已读正文 `read` | 仅检索摘要 `search_only` | 抓取失败 `unavailable` | `details` 七节 | `needs_detail` | `reviewed_detail` |
|---|---|---|---|---|---|---|---|---|
| eastern | 54 | 17 | 16 | 0 | 1 | 54/54 | 54 | 0 |
| western | 54 | 34 | 33 | 1 | 0 | 54/54（+ 可选 `parameter_dimensions`） | 54 | 0 |
| society | 53 | 31 | 30 | 0 | 1 | 53/53 | 53 | 0 |
| steam-horror | 50 | 46 | 41 | 0 | 5 | 50/50 | 50 | 0 |
| **四个虚构组小计** | **211** | **128** | **120** | **1** | **7** | **211/211** | **211** | **0** |
| reality-physical | 32 | 36 | 33 | 0 | 3 | 32/32 | 32 | 0 |
| reality-human | 31 | 55 | 44 | 0 | 11 | 31/31 | 31 | 0 |
| **全库合计** | **274** | **219** | **197** | **1** | **21** | **274/274** | **274** | **0** |

核对结论（均可重算）：

- **element id 全库唯一**：274 个 id，无重复、无跨组撞 id；`name` 也无重名。
- **`source_ids` 无悬空引用**：274 条的 `source_ids` 全部能在本文件 `sources` 内找到。
- **非 `read` 来源零引用**：全库没有任何一条元素把 `search_only` / `unavailable` 来源写进 `source_ids`（此结论比旧基线时更严）。
- ⚠ **「未被引用」不等于「未出现」，且本轮已修复元素侧部分**：
  - 第二轮收尾已将 `society`（21 条）与 `steam-horror`（38 条）正文里已明确引用的 **15 个 `read` 来源**补进对应元素的 `source_ids`（共 74 处，详见 §10.2）。
  - **仍未被任何 `source_ids` 引用的来源为 28 个**：`unavailable` 21 个（本就不应被引）+ `search_only` 1 个（`western_src_britannica_inquisition`）+ **`read` 6 个**（`western_src_britannica_germanic_mythology_detail`、`society_src_31`、`sh_src_31`、`sh_src_41`、`sh_src_42`、`reality_human_src_50`）——这 6 个是真正的「登记了但从未使用」，**待主审定口径**（补引还是从 sources 删）。

### 2.2 `details` 体量（小节字数，不含 `summary` 与扫描字段）

| 组 | 最短 | 均值 | 最长 | 七节合计 |
|---|---|---|---|---|
| eastern | 817 | 941 | 1252 | 约 5.1 万字 |
| western | 566 | 684 | 1019 | 约 3.7 万字（仅七节，不含 `parameter_dimensions`） |
| society | 731 | 877 | 1077 | 约 4.6 万字 |
| steam-horror | 418 | 535 | 652 | 约 2.7 万字 |
| reality-physical | 766 | 905 | 1721 | 约 2.9 万字（第二轮补写饮水/测量定义后略增） |
| reality-human | 808 | 1017 | 1890 | 约 3.2 万字 |

字数只作参考：**长度不代表完整，更不代表已核**。各组自述的均值（eastern 941 / society 约 880 / steam 约 535 / western 约 680）与本环节实测**一致**（reality-physical 因第二轮补写两条定义，均值由 875 增至 905）。

### 2.3 按八类别 × 六组

| 类别 | eastern | western | society | steam-horror | **四组小计** | reality-physical | reality-human | 全库合计 |
|---|---|---|---|---|---|---|---|---|
| life 生命物种 | 4 | 9 | 0 | 0 | 13 | 0 | 0 | 13 |
| power 力量技术 | 13 | 9 | 0 | 5 | 27 | 8 | 1 | 36 |
| item 物品资源 | 6 | 5 | 0 | 4 | 15 | 6 | 0 | 21 |
| place 地点探索 | 8 | 7 | 0 | 10 | 25 | 9 | 1 | 35 |
| institution 社会制度 | 5 | 10 | 22 | 9 | 46 | 3 | 15 | 64 |
| organization 组织信仰 | 6 | 5 | 18 | 8 | 37 | 0 | 8 | 45 |
| economy 经济生产 | 4 | 4 | 12 | 4 | 24 | 5 | 6 | 35 |
| conflict 冲突事件 | 8 | 5 | 1 | 10 | 24 | 1 | 0 | 25 |
| **合计** | **54** | **54** | **53** | **50** | **211** | **32** | **31** | **274** |

四个虚构组内部：制度／组织／经济三项合计 107 条（占 211 的 51%），说明本批没有堆成「能力装备清单」；代价是 society 组完全没有 life／power／item／place 四类（该组按设计只收制度面）。

现实两分区的类别分布与上表一致（`reality-physical`：place 9、power 8、item 6、economy 5、institution 3、conflict 1；`reality-human`：institution 15、organization 8、economy 6、place 1、power 1）。**两分区不入「八题材标签」体系，其类别数单列，不与四个虚构组混统。**

### 2.4 按八题材标签覆盖

**这些数字会交叉，不能相加。** 一条元素可同时标两个题材（甚至跨组概念重叠），八个数加起来是 329，比四组总量 211 大 118。现实两分区统一标 `real_world`，不参与本表。

| 题材标签 | 所属组 | 可适用条数 | 该组总数 | 其中跨标签共用 |
|---|---|---|---|---|
| `eastern_fantasy` 东方玄幻 | eastern | 47 | 54 | 组内 45 项同时标两题材 |
| `xianxia` 仙侠／修真 | eastern | 52 | 54 | 同上 |
| `western_fantasy` 西幻／剑与魔法 | western | 51 | 54 | 组内 51 项同时标两题材 |
| `dark_fantasy` 黑暗／哥特奇幻 | western | 54 | 54 | 同上（见 §5 警告） |
| `historical` 历史／架空历史 | society | 41 | 53 | 组内 16 项同时标两题材 |
| `modern` 现代都市／现实社会 | society | 28 | 53 | 同上 |
| `steampunk` 蒸汽朋克 | steam-horror | 32 | 50 | 组内 6 项同时标两题材 |
| `folk_horror` 灵异／民俗恐怖 | steam-horror | 24 | 50 | 同上 |

「可适用」是**标签命中**，不是「该题材的核心代表」。尤其 `dark_fantasy` 的 54/54 是宽标签兜底的结果（见 §5），不能读成「黑暗奇幻的全部要素已收齐」。

> **本轮新增的可细分手段**：`western` 组 54 条全部新增了 `genre_relevance`（每个题材一个 `core` / `common` / `compatible_only` 等级 + 说明）。实测分布：`western_fantasy` = core 26 / common 26 / compatible_only 2；`dark_fantasy` = core 22 / common 31 / compatible_only 1。因此「标签真假」问题现在有了可核查的二级信号：**`dark_fantasy` 真正标 core 的只有 22 条，而非 54 条**。其他五组**没有**这个字段，仍只有布尔式标签命中。

## 三、题材标签 → 重要示例

每题材 6—10 条，按「若只选一条先看哪条」排序，不是重要性排名。完整字段以各组 JSON 为准。

### `eastern_fantasy` 东方玄幻（47 条）

| ID | 名称 | 一句话 |
|---|---|---|
| `eastern_cultivator_strata` | 修士与凡俗的分层 | 谁能修行本身就是治理问题 |
| `eastern_realm_system` | 境界体系 | 可复用的类型装置，不是道教教义 |
| `eastern_spirit_root` | 灵根（修行资质） | 天赋分级决定社会流动上限 |
| `eastern_sect` | 宗门 | 兼营产业与教学的门派 |
| `eastern_cultivator_clan` | 修真世家 | 家族即武装集团 |
| `eastern_bloodline_inheritance` | 血脉传承 | 力量可继承的社会后果 |
| `eastern_spirit_stone_currency` | 灵石本位与通货 | 可检验矿物被当成货币后的通缩与伪币 |
| `eastern_secret_realm` | 秘境与洞府 | 周期性开启的准入制空间 |

### `xianxia` 仙侠／修真（52 条）

| ID | 名称 | 一句话 |
|---|---|---|
| `eastern_realm_system` | 境界体系 | 十余种互不相同的网络小说体系 |
| `eastern_spirit_qi` | 灵气与天地元气 | 资源化改写后的超自然介质 |
| `eastern_sect_rules` | 门规与清规 | 戒律—凭证—处置的制度骨架 |
| `eastern_immortal_register` | 仙籍与名录登记 | 被登记才算有修行资格 |
| `eastern_dao_lineage` | 道门与教派 | 历史宗教组织，不等于小说道门 |
| `eastern_dongtian_fudi` | 洞天福地 | 有主权的分级圣地 |
| `eastern_tribulation` | 天劫 | 晋升的代价节点 |
| `eastern_ascension` | 飞升与上界 | 强者退出舞台的清场机制 |
| `eastern_sword_cultivation` | 剑修与剑意 | 职业化的战斗路线 |
| `eastern_thunder_ritual` | 雷法与召雷 | ⚠ 证据链最弱的一条（见 §5） |

### `western_fantasy` 西幻／剑与魔法（51 条）

| ID | 名称 | 一句话 |
|---|---|---|
| `western_dragon` | 巨龙 | 守宝、缔约、骑乘的多种可能 |
| `western_dwarf` | 矮人 | 住山腹、擅金属工艺的地灵 |
| `western_elf` | 精灵 | 已补 Britannica elf 专条全读（不再是设计归纳），**证据内容待审** |
| `western_arcane_spellcraft` | 奥术施法 | 效力取决于言辞、材料与状态 |
| `western_kingdom_monarchy` | 王国与君主 | 封建王权的制度容器 |
| `western_feudal_fief` | 封建封授与效忠 | 土地与军役的双向义务 |
| `western_guild_charter` | 行会与城市特许状 | 组织＋法律特许的复合体 |
| `western_knighthood_chivalry` | 骑士道与骑士团 | 身份、伦理与军事职能三合一 |
| `western_apprenticeship` | 学徒制与技艺传承 | 行会垄断下的经济契约 |

### `dark_fantasy` 黑暗／哥特奇幻（54 条）

⚠ 本标签 54/54 全命中，属**宽标签适用**而非「核心普遍」。下列 10 条是本组实际最靠黑暗／哥特的一端。

| ID | 名称 | 一句话 |
|---|---|---|
| `western_vampire` | 吸血鬼 | 文学定型过程本身可作素材 |
| `western_werewolf` | 狼人与兽化者 | 15—17 世纪狼人审判史 |
| `western_restless_dead` | 亡灵与游魂 | 可平息／仅可摧毁／可役使 |
| `western_necromancy` | 死灵术 | 通死、圆阵自保、尸骸材料 |
| `western_inquisition_heresy` | 异端审判 | 已补西班牙宗教裁判所专条，细节不再依赖 search_only 条目 |
| `western_taboo_forbidden_lore` | 禁忌与禁书 | 教会垄断解释权的产物 |
| `western_haunted_manor` | 荒废宅邸与古宅 | 哥特氛围的建筑装置 |
| `western_crypt_catacomb` | 地下墓室与陵寝 | 已改引死灵术 / 哥特建筑 / 采矿三条支撑 |
| `western_witch_trial` | 巫术审判 | 近代早期欧洲猎巫 |
| `western_plague_famine` | 瘟疫与饥荒 | 天谴叙事与人口崩溃 |

### `historical` 历史／架空历史（41 条）

| ID | 名称 | 一句话 |
|---|---|---|
| `society_palace_court` | 宫廷与朝仪 | 内廷是官署之外的决策通道 |
| `society_fief_succession` | 封土继承与世袭化 | 继承即政治 |
| `society_manor_labor_rent` | 庄园与劳役地租 | 剩余如何被抽走 |
| `society_lineage_clan` | 宗族与族产 | 家族承担部分基层治理 |
| `society_craft_guild` | 手工业行会与学徒制 | 准入与排他 |
| `society_urban_charter` | 城市特许状与公社自治 | ⚠ 来源未覆盖欧陆（见 §5） |
| `society_religious_order` | 修会与教团 | 戒律转为日常秩序 |
| `society_coinage_mint` | 铸币权与成色管制 | 货币是主权行为 |
| `society_medieval_university` | 大学与特许讲学 | 有自治司法权的法人 |
| `society_household_register` | 户籍与人口登记 | 漏登即失去资格 |

### `modern` 现代都市／现实社会（28 条）

⚠ 现代条目的制度依据多来自**中国当代法条类词条**，地域性极强，不能当作「现代社会的通例」。

| ID | 名称 | 一句话 |
|---|---|---|
| `society_employment_contract` | 劳动合同与试用期 | ⚠ 中国法条口径 |
| `society_labor_union` | 工会与集体协商 | ⚠ 中国法条口径 |
| `society_social_insurance` | 社会保险与统筹账户 | ⚠ 中国法条口径 |
| `society_limited_company` | 公司与有限责任 | 把所有权拆成可转让份额 |
| `society_police_force` | 警察与执法程序 | ⚠ 中国法条口径 |
| `society_compulsory_school` | 义务教育与学区 | ⚠ 中国法条口径 |
| `society_consumer_credit` | 消费信贷与征信 | 未来收入贴现 |
| `society_mass_media` | 大众传媒与舆情 | 信息渠道即权力 |
| `society_healthcare_access` | 就医与医疗保障 | 准入门槛与排队 |

### `steampunk` 蒸汽朋克（32 条）

| ID | 名称 | 一句话 |
|---|---|---|
| `steam_reciprocating_engine` | 往复式蒸汽机 | 动力起点，须与燃料、材料同现 |
| `steam_high_pressure_boiler` | 高压锅炉与动力密度 | 功率密度的瓶颈 |
| `steam_coal_fuel_chain` | 煤—蒸汽燃料链 | 没有煤就没有这套技术 |
| `steam_factory_discipline` | 工厂制度与工时纪律 | 机器的社会配套 |
| `steam_trunk_railway` | 干线铁路与时刻表 | 运输速度重构地理 |
| `steam_patent_monopoly` | 专利与特许垄断 | 谁能合法造 |
| `steam_standard_time` | 标准时间与调度纪律 | 时间被统一才可调度 |
| `steam_industrial_city` | 工业城市与贫民街区 | 人口聚集的代价 |
| `steam_rigid_airship` | 硬式飞艇与航空运输 | 浮升气体是易燃代价 |

### `folk_horror` 灵异／民俗恐怖（24 条）

⚠ 本组**未找到可读的「folk horror」类型学专文**，因此不写「民俗恐怖必须包含 X」这类论断（见 §5）。

| ID | 名称 | 一句话 |
|---|---|---|
| `horror_restless_dead` | 未得安顿的亡者 | 丧仪残缺导致的滞留 |
| `horror_vengeful_grudge` | 怨念与索报 | 无法用武力解决的威胁 |
| `horror_omitted_rites` | 丧仪残缺与失序的死亡 | 关注「该做的没做」 |
| `horror_taboo_breach` | 禁忌与违约 | 后果是超自然而非法律性的 |
| `horror_local_shrine` | 地方神祠与地祇 | 地方性崇拜的场所与管辖权 |
| `horror_village_calendar_rite` | 村落节令祭仪 | 周期性仪式切分公共时间 |
| `horror_ancestral_hall` | 祠堂与祖先牌位 | 祭祀与记忆的承担者 |
| `horror_exorcist_office` | 驱邪职与仪式专家 | 仪式职能的制度化 |
| `horror_rumour_chain` | 传闻链与口传变体 | 信息在传递中变形 |
| `horror_second_burial` | 二次葬与骨骸处理 | 死亡是需要被「再处理」的过程 |

## 四、跨组共享母题

`shared-themes.json` 里有 **25 个**主题，共引用 **103 条**不同元素（**108 个成员位**）。每个主题都带 `relation: shared_motif_or_distinct_variants`、`shared_points`（共同点）与 `non_merge_reason`（为何不可合并）。

> **数据范围必须读清（避免误读）**：这 25 个主题**只聚类原四个虚构题材组的 211 条候选中的 103 条**；而**整个目录是 274 条**（含 `reality-physical` 32 与 `reality-human` 31）。所以：
> - 108 个成员位 / 103 条不同元素是“主题成员数”，**不是目录存量**，也不是覆盖率。
> - 主题**完全不覆盖** `reality` 两分区（共 63 条）；四组内还有 **108 条**（eastern 29 / western 28 / society 28 / steam-horror 23）未入任何主题。
> - `shared-themes.json` 的 `purpose` / `counting_note` 字段仍只写“四组共 211 条”，**该文件本轮未修改**（引用验证全过）；本节的说明以本段为准。

**本轮引用验证（逐项重算，全部通过）**：

- 25 个主题 id 无重复；108 个成员位指向的 id **全部存在**，零悬空。
- 每个主题声明的 `groups` 字段与实际成员所属组**逐主题一致**，零不符。
- 同一主题内无重复成员；25 个主题 `relation` 统一，`shared_points` 与 `non_merge_reason` 无缺失。
- 103 条被引元素中，**98 条只属 1 个主题、5 条属 2 个主题**（`society_craft_guild`、`society_noble_precedence`、`western_kingdom_monarchy`、`western_secret_cult`、`eastern_dao_lineage`）——与旧的“5 条重叠”记录完全一致。
- 按组分布：society 25、western 26、eastern 25、steam-horror 27（合 103）。主题规模：3 人 **5 个**、4 人 **9 个**、5 人 **10 个**、7 人 **1 个**。

按参与组数分布：2 组交集 **4 个**、3 组交集 **18 个**、四组全包 **3 个**（`theme_master_apprentice`、`theme_rite_festival_calendar`、`theme_money_credit_debt`）。真正的全题材母题很少，这本身就是个结论。

⚠ **覆盖空白（如实记录，本轮不处理）**：主题索引**只覆盖四个虚构组的 211 条**，`reality-physical` 与 `reality-human` 共 **63 条零覆盖**；四个虚构组内也有 **108 条**（eastern 29 / western 28 / society 28 / steam-horror 23）未入任何主题。按任务约束，**不为“扩大主题”而强行合并，不为凑覆盖率拆或并主题**；这是已知缺口而非错误。

覆盖方向与用户关心的四点对应：

| 关心方向 | 对应主题 |
|---|---|
| 宗门／宗教 | `theme_monastic_order_rule`、`theme_school_sect_college`、`theme_heresy_orthodoxy`、`theme_divination_medium`、`theme_rite_festival_calendar` |
| 社会制度 | `theme_guild_charter_craft`、`theme_kin_lineage_clan`、`theme_inheritance_succession`、`theme_status_stratification`、`theme_urban_autonomy`、`theme_register_census`、`theme_standardization_regulation` |
| 普遍重要元素 | `theme_master_apprentice`、`theme_oath_contract_enforcement`、`theme_money_credit_debt`、`theme_labour_collective`、`theme_plague_collective_death`、`theme_burial_improper_dead`、`theme_restless_dead`、`theme_taboo_forbidden_lore`、`theme_secret_society`、`theme_monster_frontier`、`theme_kingship_court_patronage` |
| 科技背景 | `theme_mining_extraction`、`theme_energy_supply_chain`、`theme_standardization_regulation` |

**两个刻意保留的「防误合并」主题**：

- `theme_energy_supply_chain`：灵气／奥术／蒸汽动力的可比性只到「供给—转化—损失—控制」这个提问框架。**不能把灵气魔力电力直接等同**——灵气是设定性超自然介质（量化与枯竭属小说改写），蒸汽是可测量可核算的热机工程。
- `theme_monastic_order_rule`：修道会（基督教制度史）、道门（道教史）、宗门（小说类型装置）三者**不能互相等同**，共享的只有「戒律—凭证—处置」的制度骨架。

去重的定位：这是**检索聚类**，不是抹平差异。211 条全部保留，没有任何一条被物理删除、合并或改写；同一母题下的多个条目是「并列可比较」而非「同一件事」。

## 五、证据强度与已知弱项（如实记录）

### 5.1 「已读」是什么意思

`access: read` 记录的是**采集代理自述的阅读状态**：它声称抓取到了该页正文。它**不是**许可授权，也**不是**准确性保证。本轮整合**没有重新逐条核验任何来源正文**（只核了字段、引用链、ID 与统计自洽）。

主审至今只抽核了 4 条（记在这里以保留口径，均为采集阶段的抽核）：

| 抽查对象 | 结果 |
|---|---|
| 百度百科「修真境界」（`eastern_src_realm`） | ✅ 成功 |
| 百度百科「采邑制」（`society_src_03`） | ✅ 成功 |
| Britannica「steam engine」（`sh_src_01`） | ⚠ 超时，未取到 |
| Britannica「dragon」（`western_src_britannica_dragon`） | ⚠ 超时，未取到 |

**因此不能宣称「所有来源已由主审逐一核实」。** 两条 Britannica 抽核失败是复核侧的网络超时，它既不能证明采集代理读错，也不能证明它读对——只能记作**未复核**。

⚠ **引用链完整性（本轮第二轮已修复）**：全库 `source_ids` 零悬空、且无一条元素引用非 `read` 来源（严格）。`society` 21 条与 `steam-horror` 38 条正文里已明确引用的 15 个 `read` 来源，已在第二轮补进对应 `source_ids`（共 74 处），**元素级引用链缺口现为 0**。仅剩 6 个 `read` 来源**两端都未使用**（`western_src_britannica_germanic_mythology_detail`、`society_src_31`、`sh_src_31`、`sh_src_41`、`sh_src_42`、`reality_human_src_50`），需主审定口径。

### 5.2 分组弱项

| 组 | 弱项（按当前 JSON 实测） |
|---|---|
| eastern | **来源层级偏低**：17 条来源全部是百科／问答类汇编（无学术专著、无一手道经原文）。`eastern_src_alchemy` 词条极短，只够界定术语。`eastern_src_zhihu_realm_discuss` 为 `unavailable`，未被引用。**`eastern_thunder_ritual` 仍是证据链最弱的一条**：已补读神霄派词条（`eastern_src_shenxiao`）可支撑「历史存在＋内修—外用结构」，但**雷部神将谱系与具体仪轨仍无一手文献**，条目自述仍标待补。另有 3 条在 `evidence_note` 里仍自述缺口：雷法仪轨、丹药重金属中毒病理（`eastern_mortal_plague`）、香火会社组织形态（`eastern_pilgrimage_festival`）；`eastern_mortal_city` 已补明代里甲词条作制度参考（限明代，不可照搬）。 |
| western | 34 条来源、33 `read`。**精灵已补专页**：`western_elf` 现有 Britannica elf 专条全读，`western_fey_folk` 也有 fairy 专条，两条的 `evidence_note` 已声明不再借矮人／哥布林旁证——**但证据内容本身未审**（见 `detail-gaps.md`）。`western_src_britannica_inquisition`（`search_only`）**已从所有 `source_ids` 里移出**（零引用）。`western_src_britannica_germanic_mythology_detail`（`read`）则**零引用且正文也未提**（登记了没用，属反向小缺口）。**`dark_fantasy` 仍 54/54 宽标签**，但新增的 `genre_relevance` 把它拆开了（core 22 / common 31 / compatible_only 1）。 |
| society | 31 条来源、30 `read`、1 `unavailable`（`society_src_26`，零引用）。**城市自治来源局限仍在**（`society_src_08` 只讲英国 city status，`society_src_09` 只有书目介绍），细节属本项目归纳。**现代制度多中国当代法条**（劳动合同、社保、警察、义务教育、居委会），地域性极强，不能代表全世界。农奴制在西欧／俄国／旧西藏差别极大，不可混用。⚠ 另有 4 个 `read` 级来源（`_27` 汉萨同盟、`_28` 萨利克法典、`_29` 封建等级、`_30` 社会救助）此前只在正文被引、未进 `source_ids`；**第二轮已补进 21 条元素的 `source_ids`（23 处）**，仍未被使用的是 `_26`（`unavailable`）与 `_31`（临时约法，`read`，两端都未用）。 |
| steam-horror | 46 条来源、41 `read`、**5 `unavailable`**（`_28`、`_43`—`_46`，均零引用）。**仍缺 folk horror 专门类型学**（BFI 专题页、英文维基、期刊页均失败），因此依旧不写「民俗恐怖必须包含 X」这类论断。⚠ 引用链方面，11 个 `read` 来源（`_29`—`_40` 中的钢铁/魔法/幽灵/仪式/恐怖影视等 Britannica 条目）**已在第二轮补进 38 条元素的 `source_ids`（51 处）**；仍未被使用的是 `_28`/`_43`—`_46`（均 `unavailable`）与 `_31`（Bessemer）、`_41`（Horror film）、`_42`（Fantasy）三条 `read`（两端都未出现）。 |
| reality-physical | 36 条来源、33 `read`、3 `unavailable`（`_33`/`_34`/`_37`，零引用）。已过一轮主审返修（见 `review-notes.md` §8 与本文 §11.3）。剩余弱项：强度类来源只支撑定性结论，**不提供可作工程使用的承载/摩擦/吸程数值**；`rp_src_09`、`rp_src_23` 仅得导言段；`rp_src_16`、`rp_src_22` 为短条目；`rp_src_36`（JCGM 目录页）确认未读正文。 |
| reality-human | 55 条来源、44 `read`、**11 `unavailable`**（均零引用）。自述有 **5 条为导言/摘要级**（`_01`/`_21`/`_34`/`_35`/`_50`），不能支撑全文细节；`_50` 为 FAO 目录页且未被引用。 |

### 5.3 信仰叙述的处置

涉及道教（符箓召遣鬼神、雷法役使雷部、炼度施食）、欧洲民俗（狼人供词、巫术效力）、祖先崇拜（亡灵滞留）的内容，一律**不作为经验证实事实**。史料中被追诉者的供词多由刑求取得，未被当作已发生的超自然现象。

## 六、开局锁定与引入许可

这一节描述的是**将来怎么用它**的规则设计，本环节没有实现任何代码。

### 6.1 开局前选定并锁定

按现行规范（`collection-spec.md` 「最新决策」节）：

- 开局前由作者／玩家选择元素与**允许的发展方向**，展开依赖、做兼容检查，**固定版本**与必要详细内容，形成**世界元素清单**。
- **开局后不得从全局元素库检索并新增未绑定类型。**
- 预绑定**不要求开局公开全部内容**：已存在但未知的对象、尚未实现的技术、未掌握的能力都可列为**潜在元素**。
- 预绑定 ≠ 已发现 ≠ 已普及。
- 禁止的是「运行中重新挑选外部元素」，**不禁止**读取开局固定的本地状态、完整资料与对话证据（这些是长篇一致性的必要上下文）。

⚠ 这是**待实现设计**，当前引擎尚未实现锁定清单。本目录只记录口径。

### 6.2 三类状态必须分开

现行规范重新定义了 `entry_modes` 的含义：它们**不是三个允许运行时跳库导入的入口**，而是描述**已预绑定元素在世界内的显现方式**：

| `entry_modes` 值 | 含义（新规范口径） |
|---|---|
| `existing` | 开局就存在 |
| `discovery` | 开局已绑定，但之后才被发现 |
| `player_proposal` | 开局已绑定，玩家在已许可边界内提出实现／使用 |

三种都基于「已预绑定」这个前提，因此**没有一个能用来引入开局没绑定的东西**。

与「世界内状态」的对应关系：

| 状态 | 含义 | 是否触碰外部库 |
|---|---|---|
| 存在于绑定设定 | 世界设定里成立，可能无人知晓 | 否（已预绑定） |
| 被发明／被发现／被解锁 | 世界内状态变化：有人造出来了、有人找到了 | 否（只改预绑定元素的世界内状态） |
| 新增元素 | 往世界里加一个开局没绑的东西 | **不允许静默发生** |

### 6.3 玩家提案的边界

- 玩家可以在**开局时**主动选择外题材候选元素（跨度大的审核更严）。
- 中途提案只在**预绑定许可范围内**做本地判定：范围内按既有条件（材料、知识、工艺、能源、成本、制度）判定可行性。
- **超范围**的处理是明确的：**不静默补库**；提示超出本局范围，由作者另建版本及新旅程／显式分支后采用。

## 七、默认适用 vs 可迁入：五级阶梯

「设定了这个元素的世界能不能用它」和「能不能把它搬进来」是两个问题。本目录只给后者一个**建议阶梯**，不实现兼容性算法、不打分、不做自动判定。

| 级别 | 名称 | 含义 | 例（蒸汽动力进入一个历史向世界） |
|---|---|---|---|
| L0 | 默认适用 | 与背景条件天然相符，可直接存在 | 采矿、冶炼、行会、庄园、驿传 |
| L1 | 概念 | 只作为传闻、图纸、理论设想出现，无实物、无产业链 | 有人提出「用蒸汽顶起活塞」的设想，无人造出可用机器 |
| L2 | 原型 | 单件可运转的装置，成本极高、可靠性差、无法复制 | 一台漏气、常爆、只有一位工匠会修的样机 |
| L3 | 局部 | 在特定地点／行业稳定使用，需配套（燃料、零件、技工、维修） | 一处矿井的排水泵，靠专人和专线煤维持 |
| L4 | 复制 | 可批量制造、可培训操作者、有维修与零件供应体系 | 多家工场造同类机器，出现技工行当与零件规格 |
| L5 | 普及 | 重构了运输、城市、劳动与军事，并催生监管制度 | 干线铁路＋时刻表＋标准时间＋工厂纪律 |

使用要点：

- **原型不等于量产，局部发现不等于全球普及。** 跨级必须有材料、知识、工艺、能源、成本与制度条件同时到位。
- 阶梯是**单向渐进**的：可以有 L1 而没有 L2（设想始终没造出来），但不能跳过 L2 直接到 L4。
- 这套梯子只服务于人工审核与写作判断；它**不是**运行时算法，也不产生数值。
- 跨题材幅度越大，默认的起评级别越低（外题材通常从 L1 起，而非 L0）。

## 八、现实基础库（reality-physical / reality-human）

按现行规范，现实基础库分两个**独立分区**，题材标签用 `real_world`，与四个虚构题材组**分开存放、分开统计**：

| 分区 | 范围 | 条数 | 状态 |
|---|---|---|---|
| `reality-physical` | 自然与地理、物理化学／能源材料、农业生态／公共卫生、生产交通通信 | **32** | **已交付**；均带 `details`，全部 `needs_detail`；**已过一轮主审点名返修（2026-10-26）** |
| `reality-human` | 历史制度、宗教与信仰实践、家庭组织、法律经济 | **31** | **已交付**；均带 `details`，全部 `needs_detail`；未见主审点名返修记录 |

两分区**均已不再标为「采集中」**：`reality-human.json` 现有 31 条、`reality-human.md` 已与之对齐。但**均未封版**，条数仍可能变动，以 JSON 实时为准。

### 8.1 两分区实测对照

| 项 | reality-physical | reality-human |
|---|---|---|
| 元素 | 32 | 31 |
| 来源 | 36（`read` 33 / `unavailable` 3 / `search_only` 0） | 55（`read` 44 / `unavailable` 11 / `search_only` 0） |
| 题材标签 | 全部 `real_world`（无其他标签） | 全部 `real_world`（无其他标签） |
| 类别分布 | place 9、power 8、item 6、economy 5、institution 3、conflict 1 | institution 15、organization 8、economy 6、place 1、power 1 |
| `details` 覆盖 | 32/32 | 31/31 |
| `detail_status` | 全部 `needs_detail` | 全部 `needs_detail` |
| `knowledge_kind` | empirical 25、mixed 6、historical 1（belief_description 0） | historical 16、mixed 10、belief_description 5（empirical 0） |
| `related_catalog_ids` | 97 个引用，覆盖 32/32 条，**零悬空、零自指** | 113 个引用，覆盖 31/31 条，**零悬空、零自指** |

`related_catalog_ids` 的指向分布（实测）：`reality-physical` → steam-horror 46 / society 22 / western 19 / eastern 9 / reality-human 1；`reality-human` → society 51 / steam-horror 26 / western 18 / eastern 6 / reality-physical 6。**与四组及彼此的交叉全部用真实 id**，无同名条目（两分区与四组之间零重名）。

⚠ 两分区 `knowledge_kind` 分布差异极大不是错误：physical 侧基本上不该有 `belief_description`（实测 0），human 侧基本上不该有纯 `empirical`（实测 0），这与已定稿的职责划分一致。

注意：本分区**不沿用**前面的「八题材标签」，与四个虚构组**不在同一张表里相加**。

原则（先立下，现已随交付落实）：

- **不重复造已有变体**：已有社会制度变体以引用／关联为主，不重建一遍。
- 现实条目保留统一 14 字段，**增加** `knowledge_kind`（empirical / historical / belief_description / mixed）、`details` 分节与 `detail_status`，**不设完整内容字数上限**。
- 区分四件事：可检验的现实机制、带地域时期的历史事实、信仰／传统的记述、争议与本项目创作适配。**不把神迹、修行或灵异效力当科学事实。**
- 现实条目可作为**默认候选**，但仍须开局选择适用版本／条件；架空世界若覆盖现实规律，应**显式声明覆盖范围**，不悄悄混用。
- 不是完整百科，也不是把现实一切自动装进每局。

当前状态：**两个分区均已交付、均未封版**。上表为本环节实测值；若后续有增删，以两部分区 JSON 实时为准。

## 九、审查标准（已定稿）

下面是主代理已定稿的审查口径，也是后续验收的唯一依据。本整合环节只负责把它记下来，**不代替主审执行验收**。

### 9.1 验收分两层

| 层 | 覆盖 | 内容 |
|---|---|---|
| **结构层（100%）** | 全部条目 | 结构、引用、ID、`details` 七节是否齐、**跨字段矛盾与绝对断言扫描** |
| **内容层（风险分层抽查）** | 抽样 | 每题材至少 3 条；**所有已知弱证据项与历史／技术精确断言项必抽** |

两条硬要求：

- **记录审了哪些 ID／来源、结果如何**。不写“已检查”这种无记录的结论。
- **不以抽检代替全量事实核实**。抽查通过 ≠ 全库正确。

### 9.2 `reviewed_detail` 的升格权

- **仅主代理逐条实质核验后可升格**。采集代理一律保持 `needs_detail`。
- **已写 `details` 七节 ≠ 事实已核。**
- 未逐条核验的条目**保留候选状态**；本目录的任何报告都**不是全量认证**。
- 可用文字区分「详情已补齐」与「证据待核」，但**不擅改 schema 状态字段**。

### 9.3 纯设计归纳怎么写

允许纯设计归纳条目进候选，**不要求伪造历史原型或假引文**。写法约定：

- 证据节写「**本项目建议**」或「**类型母题归纳**」。
- 必须明确：自选的世界规则、不同常见变体、适用理由与**反例**、以及**不可推论什么**。
- **通用性证据不足时不得称为普遍事实。**
- `source_ids` **只支持相关背景，不证明该机构／制度在历史上存在过**。

这条直接适用于 `western_magic_regulation`（魔法执照）、`western_mage_college`（法师学院）、`western_underworld_guild`（盗贼公会）、`western_monster_hunter`（猎魔人）这类条目。

### 9.4 reality 两分区的分工

| 分区 | 负责 | 例子 |
|---|---|---|
| `reality-physical` | **可验证的物理／生物／生态机制与工程条件** | 病原传播、饮水、食物 |
| `reality-human` | **社会应对与组织制度** | 医院、保险、检疫授权、交通治理、经济法律 |

交叉处**用真实 ID 关联**，不重复造两份权威（同一个事实不在两边各写一遍）。

## 十、本轮审阅范围（说清做了什么、没做什么）

### 10.1 做了的结构层核对（100%）

全部 274 条，逐条机器核验，可重算（第二轮修改后已**全量重跑**，六组均 PASS）：

| 检查项 | 结果 |
|---|---|
| element id 全库唯一 | ✅ 274/274，无重复、无跨组撞 id |
| `name` 全库不重名 | ✅ 274/274（含 reality 与四组之间也不重名） |
| 14 个统一字段非空 | ✅ 274/274（reality 两分区额外带 `knowledge_kind` / `related_catalog_ids`，均 100% 覆盖） |
| `category` 合法值 | ✅ 全库仅 8 个合法值，零非法 |
| `entry_modes` 合法值 | ✅ 仅 existing / discovery / player_proposal |
| `genres` 合法值 + 无越组串标签 | ✅ 零非法、零越组 |
| `detail_status` 合法值 | ✅ 274/274 **均为 `needs_detail`，`reviewed_detail` = 0** |
| `details` 七节齐备且非空 | ✅ 274/274（另 western 有可选第 8 节） |
| `source_ids` 悬空 / 重复 / 非 read | ✅ 0 / 0 / 0（第二轮新增的 74 处加入项亦 100% 为 `read`） |
| `related_catalog_ids` 悬空 / 自指 / 重复 | ✅ 0 / 0 / 0（210 个引用） |
| `shared-themes.json` 引用真实性 | ✅ 25 主题 / 108 成员位 / 103 条，零悬空，groups 逐主题一致 |
| 各组 `.md` 是否覆盖本组全部元素 id | ✅ 六组 100% 覆盖，零漏项 |
| 本文与 `detail-gaps` / `review-notes` 里的 id 引用 | ✅ 零悬空（除 `eastern_fantasy` / `western_fantasy` 两个题材标签属于合法 genre 值） |
| 文件编码 | ✅ 六个 json + 五个文档均 **UTF-8 无 BOM**，LF 换行未被改动 |

### 10.2 做了什么、没做什么

**本轮（第二轮收尾）已做的勘误（授权范围内，不改动无关内容）：**

1. **引用链补齐**：`society` 与 `steam-horror` 两组正文/`evidence_note` 里明确点名引用的**有效 `read` 来源**，已逐条取并集、去重后同步进对应元素的 `source_ids`，既有来源全部保留。具体数量：
   - `society`：**21 条元素**、共 **23 处** source_ids 新增、涉 **11 个**不同来源（`_27`/`_28`/`_29`/`_30`/`_01`/`_05`/`_13`/`_14`/`_18`/`_20`/`_24`）。
   - `steam-horror`：**38 条元素**、共 **51 处**新增、涉 **20 个**不同来源（`sh_src_29/30/32/33/34/35/36/37/38/39/40/05/06/07/08/11/17/24/25/…`）。
   - 合计 **59 条元素 / 74 处新增**；**无一条 `search_only` 或 `unavailable` 来源被加入**（逐条校验：加入项 100% 为 `read`，且均在本文 `sources` 登记）。
2. **`western_secret_cult.evidence_note` 改写**：明确区分「旧版 `search_only` 的 Britannica Inquisition 条目（`western_src_britannica_inquisition`，已移出本条 `source_ids`、不支撑任何细节）」与「新增的西班牙宗教裁判所条目（`western_src_britannica_spanish_inquisition`，本次已读取正文）」，不再笼统写成「裁判所条目仅读到导言」。
3. **`reality_phys_drinking_water_sanitation.definition` 补全 WHO 定义**：写明 safely managed 需**同时**成立（经改善水源 / 位于处所内 / 需要时可得 / 且不受粪便及优先关注化学物质污染），不再把「无污染」省略。也同步改写其 `evidence_and_uncertainty`，明记“本轮未重抓来源正文复校，不得声称已全改正”。
4. **`reality_phys_measurement_precision`**：`background` 与 `exceptions` 补明重复性条件 / 中间精密度条件 / 再现性条件三层的区别与“不可互相代替”，并注明依据是本条已有 `rp_src_35`（VIM3 2.15）`supports` 字段的已有记载，**未重新抓取来源正文，不标事实审核通过**。

**仍然没有做的事（不得被读成已做）：**

- **没有核验任何一条的事实断言**。全部 274 条仍为 `needs_detail`，`reviewed_detail` 为 0，本轮**未升格任何一条**。
- **没有新抓取任何来源正文**（包括上述两条 reality 定义的依据来源）；也没有新增或删除任何条目、没有改任何 `detail_status`。
- **未改**：`eastern` / `reality-human` 两组 json/md、`collection-spec.md`、`shared-themes.json`（其 `purpose` 字段本轮未改，另见 `review-notes.md` §6 第 8 项）。
- **没有对 `needs_detail` 候选做逐项主审**——只做了下文 §11 的「风险点名」，**点名不是审阅结论**。

### 10.3 待主审风险 ID 汇总（只列名，不下结论）

按风险类型归并（**只去重于同类，不合并跨类重复**；一个 id 可以同时出现在多类），**不是审阅结论**。各类条数（本轮重算）：证据缺口 **8 条**、强断言 **11 句 / 9 个 id**、引用链 **已在第二轮补齐（0 条遗留）**、待复验 **4 条**、纯设计 **4 条**、字段/文字不一致 **0 条**（`western_secret_cult` 已修）。

| 风险类型 | 涉及 ID |
|---|---|
| 自述证据缺口（A 类） | `eastern_thunder_ritual`、`eastern_mortal_plague`、`eastern_mortal_city`、`eastern_pilgrimage_festival`、`western_elf`、`western_fey_folk`、`western_inquisition_heresy`、`western_secret_cult` |
| 强断言候选（§11.2 窄口径） | **11 句，涉 9 个 id**（`eastern_immortal_register` 与 `western_usury_finance` 各 2 句）：`eastern_dongtian_fudi`、`eastern_immortal_register`、`eastern_outer_realm`、`western_witchcraft`、`western_usury_finance`、`society_land_survey_tax`、`society_tax_farm`、`reality_human_weights_measures_local`、`reality_human_pilgrimage_route` |
| 引用链缺口 | ~~已补齐~~：`society` 21 条 + `steam-horror` 38 条已在第二轮同步进 `source_ids`（详见 §10.2）；**剩余 0 条元素级缺口** |
| 本地现实中已点名返修、待复验（§11.3） | `reality_phys_gravity_load`、`reality_phys_measurement_precision`、`reality_phys_food_preservation`、`reality_phys_drinking_water_sanitation` |
| 纯设计归纳、需核“自选规则＋反例” | `western_magic_regulation`、`western_mage_college`、`western_underworld_guild`、`western_monster_hunter` |
| 文字与字段不一致 | ~~已修~~：`western_secret_cult` 的 `evidence_note` 已在第二轮改写（见 §10.2） |

## 十一、过强绝对词扫描（只记候选，不等同于错）

> 这是结构层要求里的一项（`跨字段矛盾与绝对断言扫描`）。方法：对每条元素的 `summary` / `background` / `introduction_limits` / `requires` / `excludes` / `variants` / `story_roles` / `evidence_note` 与 `details` 七节做词面扫描，再用句内否定词做一次去噪。

### 11.1 扫描结果

- 词面原始命中（含被否定、含“不等于 / 不得 / 不应”等正确用法）：`等于` 类 154、`完全` 143、`任何` 136、`所有` 111、`普遍` 63、`必然` 59、`唯一` 41、`等同于` 37、`一定` 26、`绝对` 20、`一律` 20、`毫无` 13、`均` 9、`总是` 8、`无条件` 7、`不可能` 5、`从不` 5、`永远` 4、`始终` 3、`全都` 1。
- 去噪后（含强断言词的句子、且句内无否定/限定词）**命中元素 145 条**，分布：eastern 27、western 25、society 32、steam-horror 17、reality-physical 20、reality-human 24。
- 再进行一次**窄口径**扫描（只看 `summary` / `background` / `definition` / `story_consequences` / `introduction_limits` 这五个“事实陈述位”，且句内无任何限定或否定词）→ **只剩 11 句**，列在 §11.2。

### 11.2 窄口径 11 句 / **9 个 id**（真正值得主审看一眼的）

> 句数与 id 数不同，因为其中 2 个条目各有 2 句命中：`eastern_immortal_register`（#2、#3）、`western_usury_finance`（#6、#7）。分布：eastern 4 句 / 3 id、western 3 句 / 2 id、society 2 句 / 2 id、reality-human 2 句 / 2 id、steam-horror 0、reality-physical 0。

| # | 元素 | 字段 | 原句要点 | 为何列在这 |
|---|---|---|---|---|
| 1 | `eastern_dongtian_fudi` | background | 「道门、地方官与民间香火会社**必然**围绕圣地收益发生摩擦」 | 三方摩擦是合理推测，但不是必然 |
| 2 | `eastern_immortal_register` | background | 「名册**必然**被争夺、伪造与查封」 | 同上；可能有低冲突社会 |
| 3 | `eastern_immortal_register` | definition | 「核心洞察：名册的价值来自它带来的实际好处，因此**必然**被争夺」 | 同一断言在 definition 又出现一次 |
| 4 | `eastern_outer_realm` | definition | 「一旦存在稳定通路，就**必然**出现守方、税吏、走私者与流亡者」 | “必然”可换为“通常”，但此句作为内置断言可接受 |
| 5 | `western_witchcraft` | definition | 「必须同时容纳两种可能，否则社会反应**必然**失真」 | 写作指导句，“必然失真”过硬 |
| 6 | `western_usury_finance` | summary | 「在货币经济中**必然**出现的信贷与利息实践」 | 事实上存在无利息信贷社会，建议降为“普遍出现” |
| 7 | `western_usury_finance` | definition | 「指在货币经济中**必然**出现的信贷实践」 | 与 #6 同一断言 |
| 8 | `society_land_survey_tax` | background | 「每一次标准化都会重新分配负担，**必然**遭到既得利益者抵制」 | 抵制常见但非必然 |
| 9 | `society_tax_farm` | background | 「承包者为回收成本**必然**向纳税人多取」 | 包税不必然导致多取，视监督条件 |
| 10 | `reality_human_weights_measures_local` | summary | 「交易、赋税与工程因此**永远**需要换算、校准与仲裁」 | “永远”过硬；统一度量后仍可能局部换算，但非“永远” |
| 11 | `reality_human_pilgrimage_route` | summary | 「**因此必然**长出旅舍、向导、护路团体与沿途的收费者」 | 朝圣路线确有此类经济，但非必然 |

**重要声明**：上面 11 句是**扫描候选**，不是错误结论。其中 #6/#7、#9、#10 在现实侧最容易被读到，**建议主审优先看一眼**；其余多为可辩护的强表述。**本环节未修改任一条**。

### 11.3 四条点名 reality 条目的对照复核（仅文案层，未回溯来源）

任务要求核对主审指出的错误是否已改正。本环节只对照当前 JSON 文案，**不验证其是否与来源原文一致**：

| 条目 | 要求检查的点 | 当前文案状态 |
|---|---|---|
| `reality_phys_gravity_load` | E=mgh 恒 g、能量正比高度 | ✅ 已写「忽略空气阻力、g 视为常数时下落高度加倍则释放的势能加倍（E=mgh）」；同句否定“冲击力也只翻倍”，明写“落地速度只增至约 1.41 倍”“实际冲击力还取决于减速距离/时间、姿态与材料” |
| 同上 | 引力按距**中心** r 而非“离地高度” | ✅ 已写“与到天体中心距离的平方成反比……**这里加倍的是到中心的距离，不是「离地高度」**；地表附近升高几十米，重力变化微乎其微” |
| `reality_phys_measurement_precision` | precision / repeatability / accuracy / uncertainty 区分 | ✅ **已补齐（仅文案层）**：已区分精密度（规定条件下重复测量的一致程度）、**其规定条件的三层**（重复性条件 / 中间精密度条件 / 再现性条件，并明写三者不可互相代替）、准确度（与真值一致程度、不可赋值）、正确度（与系统误差相关）、不确定度（分散性）；`summary` 已写“不是同一件事”。⚠ **未重抓 VIM3 正文复核**，故**不称“已通过事实审核”** |
| `reality_phys_food_preservation` | 密封 ≠ 杀菌 | ✅ 已写“密封则隔绝再污染”、“**「密封」本身不等于杀菌**：密闭容器内能否安全保存，取决于食品性质、加热或其它处理是否充分、以及容器是否真正密封，这些条件不成立时密封反而会创造适合某些厌氧微生物的环境” |
| 同上 | 发酵非天然安全 | ✅ 已写“**发酵食品并不天然更安全**：发酵同样可能失控或被杂菌占据，在某些地区的传统发酵食品中，毒素风险已有记载” |
| `reality_phys_drinking_water_sanitation` | WHO safely managed 完整定义（improved source / on premises / available when needed / free from fecal & priority chemical contamination） | ✅ **已补齐（仅文案层）**：`definition` 现明写四个必须**同时**成立的条件（经改善水源、位于处所内、需要时可得、且不受粪便及优先关注化学物质污染），三层服务降级（基本 / 有限）已说明，“安全饮水”与“服务”已拆开；不再将“无污染”省略。⚠ **未重抓 WHO fact sheet 正文逐字复校**，故**不称“已全部改正”或“已审”** |

**结论**：四条中 **4 条的文案层要求均已补齐**（重力载荷、测量术语、食物保存、饮水定义）；但这只是“写法与要求不再矛盾”，**不等于已与原始来源逐字对齐**，也不等于事实审核通过。另：`reality-physical.md` 第七节已有完整的返修记录，六项点名错误均逐条列出“原先的问题 / 改为 / 依据”。
