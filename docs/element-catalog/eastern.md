# 东方玄幻 / 仙侠·修真 候选元素组（eastern）

状态：**候选素材收集**，不是数据库实现，不是任何故事包的已采纳正典，也未进入 `data/` 或任何 StoryPackage。
配套机读文件：[`eastern.json`](eastern.json)（`schema_version: 1` / `status: candidate` / `group: eastern`）。
规范依据：[`collection-spec.md`](collection-spec.md)、[`../narrative-element-library.md`](../narrative-element-library.md)。

- 元素数量：**54**
- 题材标签：`eastern_fantasy`（东方玄幻）、`xianxia`（仙侠／修真）
- 来源：登记 **17** 条，其中实际读过正文 **16** 条（`access: read`），**1** 条抓取失败并如实标注（`unavailable`）
- 详细程度：全部 **54** 条均已添加 `details` 七分节，`detail_status` 均为 **needs_detail**（尚未经主审，不冒充 `reviewed_detail`）
- 详细正文体量：每条 817—1252 字（均值 941），合计约 5.1 万字（不含简短 `summary` 与扫描字段）
- **开局锁定**：两者均为预绑定清单；`existing`/`discovery`/`player_proposal` 只描述元素在本世界内的显现方式，**不是三个可从库里新增元素的入口**

## 三条必须先说清的边界

1. **两个题材高度重叠，不是一个题材。** 现代网络文学语境里「玄幻」与「修真」几乎被当作同义词（`eastern_src_xuanhuan` 原文措辞为「二者几乎可以画上约等号」），本组 54 项中有 45 项同时标两个题材标签；只标其一的 9 项是特征更靠一端的（血脉传承偏玄幻；符箓、道门、飞升、仙籍、剑修、雷法偏修真／仙侠）。标两个标签不等于两种题材通用，只是检索入口。
2. **现代小说母题不是全题材硬规则。** 灵根、境界阶梯、天劫、灵石本位等，都是某一批作品确立、被后来者反复借用的**类型惯例**，各作品的名称、层级与规则互相不一致。`eastern_src_realm` 词条就并列了十余种互不相同的境界体系并注明所出作品，同时明确「小说修真的名词和境界不具备任何可行性，仅为小说家言」。因此本组的每一条都给了 `variants`（2—4 项常见变体）而不是唯一正解。
3. **不等于真实道教。** 「修真」在道教语境中确有来源（内丹、炼精化气—炼气化神—炼神还虚的次第、五仙与七候等），但小说把「得道成仙」改写成可量化、可竞争的等级赛道，属文学改造。本组的道教材料只用于**组织形态、科仪逻辑、传承凭证**等制度性对照，并逐条在 `evidence_note` 中区分「来源支持」与「本项目设计归纳」。

## 详情阅读索引（每条 details 七分节：definition / mechanism / conditions / exceptions / story_consequences / adaptation_limits / evidence_and_uncertainty）

不要把 `details` 当摘要读。它是一个「能直接拿去写世界设置」的规格：`definition` 定性，`mechanism` 给结构与参数维度，`conditions` 写前置，`exceptions` 列不被排除的合法变体，`story_consequences` 推到社会层面，`adaptation_limits` 写不可怎么做，`evidence_and_uncertainty` 分层证据。

重点推荐先读以下 12 条（信息密度最高、对全局约束最强）：

| 优先读 | ID | 为什么先读 |
|---|---|---|
| 1 | `eastern_realm_system` | 定下了「等级制不是必然」这一基调；它的 `exceptions` 列了五种非阶梯体系 |
| 2 | `eastern_spirit_root` | 资质装置的完整闭环；也是「小说设定≠道教概念」的最佳实例 |
| 3 | `eastern_spirit_stone_currency` | 最有价值的反面教材：`exceptions` 列了五种不靠灵石的合法经济 |
| 4 | `eastern_thunder_ritual` | 证据分层最细致的一条：历史实践 vs 战斗属性严格切开 |
| 5 | `eastern_sect` | 组织—经济耦合的主干，串起 7 条下游元素 |
| 6 | `eastern_cultivator_strata` | 修士/凡俗分层的三种格局与四种例外 |
| 7 | `eastern_alchemy` | 外丹五步 vs 内丹四阶段，两套完全不同的资源结构 |
| 8 | `eastern_spirit_qi` | 源—流—汇模型；也是异体系能量不互换的硬约束所在 |
| 9 | `eastern_dao_lineage` | 历史道教组织逻辑，并显式声明不等于小说「道门」 |
| 10 | `eastern_forbidden_technique` | 「知识不可收回」→ 治理从焚书转向管人的推论链 |
| 11 | `eastern_ascension` | 飞升的「清场功能」解释为何世界不会被长生者锁死 |
| 12 | `eastern_mortal_city` | 凡俗基层；与明代里甲制度对照，但明写不可照搬 |

## 重要变体与可选配置（不能当定律的那些）

以下均为**可选**，不得因本目录存在某项就认为它是题材通例：

- **非阶梯境界**：无层级制、网状多轴体系、可逆（降境）、只有少数大境界、各派名目无法换算——五种均合法（`eastern_realm_system.exceptions`）。
- **无灵根修行**：体修、剑修、符道、丹道、香火、契约、借力、苦行；代价是慢/上限低/额外损耗（`eastern_spirit_root.exceptions`）。
- **非灵石经济**：物物交换、灵石不可交易（战略物资）、灵石不可吸收（只是矿石）、多币并行不互兑、以票据/贡献点为主（`eastern_spirit_stone_currency.exceptions`）。
- **天劫不必是雷**：心魔劫、业力劫、可分次渡的劫、无外显征兆的隐秘渡劫（`eastern_tribulation.exceptions`）。
- **飞升可以不存在**：无上界（飞升即消散）、上界为虚、名额固定、末法时代无法飞升（`eastern_ascension.exceptions`）。
- **妖兽不必都想变人**：永不化形的高智妖类、只能短期化形、被强制维持人形（`eastern_yao_cultivator.exceptions`）。
- **契约不必是绝对控制**：只认领地不认人、多主共养、灵兽为主导方、临时借用（`eastern_spirit_beast.exceptions`）。
- **灵兽/傀儡并存**时需区分活物与造物的伦理地位，否则两者互相消解。

## 扫读表（按类别）

类别 ID 取值：`life` / `power` / `item` / `place` / `institution` / `organization` / `economy` / `conflict`。
题材列：`东` = `eastern_fantasy`，`仙` = `xianxia`。

| # | ID | 名称 | 类别 | 题材 | 主要剧情功能（摘要） |
|---|---|---|---|---|---|
| 1 | `eastern_cultivator_strata` | 修士与凡俗的分层 | life | 东·仙 | 跨阶层庇护与效忠；决定谁能获得灵物与知识 |
| 2 | `eastern_yao_cultivator` | 妖修与化形 | life | 东·仙 | 把「异类」写成可谈判的一方，牵动登记与招抚政策 |
| 3 | `eastern_spirit_beast` | 灵兽与契约 | life | 东·仙 | 战力与侦查的延伸；契约可背叛、可继承、可争夺 |
| 4 | `eastern_yin_ghost` | 阴灵与鬼修 | life | 东·仙 | 把死亡变成有代价的延续；接祭祀制度与旧案 |
| 5 | `eastern_spirit_root` | 灵根（修行资质） | power | 东·仙 | 天赋可测量→筛选与排斥；可被伪造与争夺 |
| 6 | `eastern_special_constitution` | 特殊体质 | power | 东·仙 | 角色成为被觊觎的资源而非单纯强者 |
| 7 | `eastern_bloodline_inheritance` | 血脉传承 | power | 东 | 出身即力量，制造世族垄断与寒门对立 |
| 8 | `eastern_realm_system` | 境界体系 | power | 东·仙 | 可比较的力量刻度，把尊卑编码进等级 |
| 9 | `eastern_cultivation_method` | 功法与传承 | power | 东·仙 | 知识垄断与师承资格；残缺功法做长期目标 |
| 10 | `eastern_spirit_qi` | 灵气与天地元气 | power | 东·仙 | 把地理差异转成力量差异；末法与灵潮的物质基础 |
| 11 | `eastern_talisman` | 符箓 | power | 仙 | 可制作、可携带、可伪造的封装力量 |
| 12 | `eastern_formation_array` | 阵法与禁制 | power | 东·仙 | 把地点变成可破解的工程结构；权限体系 |
| 13 | `eastern_alchemy` | 炼丹术 | power | 东·仙 | 有配方、有失败率的加工链；丹师兼具医者与风险源 |
| 14 | `eastern_artifact_craft` | 炼器与法器制作 | power | 东·仙 | 战斗力变成可生产可交易之物；矿源与匠人地缘 |
| 15 | `eastern_sword_cultivation` | 剑修与剑意 | power | 仙 | 高杀伤低容错的风格；心性受损式挫折 |
| 16 | `eastern_thunder_ritual` | 雷法与召雷 | power | 仙 | 专门对抗阴邪；「代天行罚」的合法性争议 |
| 17 | `eastern_divine_power` | 神通与天赋异术 | power | 东·仙 | 不可传授的单点破局手段；知识不平等 |
| 18 | `eastern_pill_elixir` | 丹药 | item | 东·仙 | 可囤积、可掺假、可耐药的商品化提升 |
| 19 | `eastern_treasure` | 法宝 | item | 东·仙 | 可夺取的强力资产；认主条件筛使用者 |
| 20 | `eastern_flying_sword` | 飞剑与御剑 | item | 东·仙 | 压缩距离→改写城防、追缉与刺杀 |
| 21 | `eastern_storage_artifact` | 储物法器 | item | 东·仙 | 取消负重→改写贸易、后勤与查缉 |
| 22 | `eastern_heavenly_material` | 天材地宝 | item | 东·仙 | 稀缺来自地理与时间，争夺先于加工 |
| 23 | `eastern_puppet` | 傀儡与造物 | item | 东 | 劳力与炮灰；「承魂容器」引出身份与伦理争议 |
| 24 | `eastern_secret_realm` | 秘境与洞府 | place | 东·仙 | 有闸门的高回报探险；名额即政治资源 |
| 25 | `eastern_dongtian_fudi` | 洞天福地 | place | 仙 | 有主权的分级圣地；朝圣与收益之争 |
| 26 | `eastern_spirit_vein` | 灵脉与灵矿 | place | 东·仙 | 可枯竭可截流的地缘资源，长期冲突根源 |
| 27 | `eastern_market_fangshi` | 坊市与交易地 | place | 东·仙 | 交易、情报、委托集散；庇护与抽成即地方权力 |
| 28 | `eastern_sect` | 宗门 | organization | 东·仙 | 兼学校、雇主、军阀与宗族；内部即可产生产权纠纷 |
| 29 | `eastern_master_disciple` | 师徒与传承谱系 | institution | 东·仙 | 知识人格化→「谁是谁的弟子」成为政治身份 |
| 30 | `eastern_cultivator_clan` | 修真世家 | organization | 东·仙 | 族产与继承纠纷；「血统 vs 师承」对立 |
| 31 | `eastern_court_patronage` | 王朝与供奉 | institution | 东·仙 | 把修行势力卷入政争与合法性交换 |
| 32 | `eastern_dao_lineage` | 道门与教派 | organization | 仙 | 科仪与度亡服务；以正统性裁定他人合法性 |
| 33 | `eastern_rogue_cultivator` | 散修与散修聚落 | organization | 东·仙 | 体系外流动人口，情报与灰色委托来源 |
| 34 | `eastern_demonic_path` | 魔道与邪修 | organization | 东·仙 | 越界行为与追缉；「谁是魔」的话语权之争 |
| 35 | `eastern_alliance_pact` | 仙盟与盟约 | organization | 东·仙 | 大规模动员；席位与配额分配埋下裂痕 |
| 36 | `eastern_sect_rules` | 门规与清规 | institution | 东·仙 | 提供可援引的规则；执法者本身成为问题 |
| 37 | `eastern_immortal_register` | 仙籍与名录登记 | institution | 仙 | 身份验证与追责；黑户、冒籍与伪造 |
| 38 | `eastern_spirit_stone_currency` | 灵石本位与通货 | economy | 东·仙 | 统一价格尺度；通缩、掺假与挤兑 |
| 39 | `eastern_contribution_points` | 贡献点与宗门配给 | economy | 东·仙 | 把服从变成资产；记账权即权力 |
| 40 | `eastern_spirit_agriculture` | 灵植与灵田 | economy | 东·仙 | 修行社会的粮食层；歉收与地力衰退 |
| 41 | `eastern_retainer` | 客卿、供奉与雇佣修行者 | economy | 东·仙 | 忠诚外包；契约条款制造背叛张力 |
| 42 | `eastern_tribulation` | 天劫 | conflict | 东·仙 | 高风险破境节点；渡劫地点成为破绽 |
| 43 | `eastern_sect_war` | 宗门战争与灵地争夺 | conflict | 东·仙 | 格局重组；检验盟约与门规的实际效力 |
| 44 | `eastern_orthodoxy_dispute` | 正统之争与异端裁定 | conflict | 东·仙 | 知识分歧升级为生存冲突；禁令与清洗的理由 |
| 45 | `eastern_demonic_calamity` | 魔潮与外患 | conflict | 东·仙 | 迫使敌对势力合作；镇守成本引发推诿 |
| 46 | `eastern_secret_contest` | 秘境试炼与宗门大比 | conflict | 东·仙 | 把资源分配公开化；赛制与裁判成为争夺对象 |
| 47 | `eastern_mortal_plague` | 瘟疫、丹毒与灵灾 | conflict | 东·仙 | 以封锁隔离制造治理困境；法术不能替代公共卫生 |
| 48 | `eastern_inheritance_strife` | 夺嫡与衣钵之争 | conflict | 东·仙 | 继承规则制造悬念；胜者清算改变组织路线 |
| 49 | `eastern_forbidden_technique` | 禁术与禁忌知识 | conflict | 东·仙 | 高风险选择；治理从焚书转向管人 |
| 50 | `eastern_ascension` | 飞升与上界 | place | 仙 | 给顶尖强者合理退场，维持力量平衡 |
| 51 | `eastern_outer_realm` | 界域与通道 | place | 东·仙 | 通道即关口；走私、流亡与法律真空 |
| 52 | `eastern_ruin_relic` | 上古遗迹与遗物 | place | 东·仙 | 技术断层的物证；能用不能造 |
| 53 | `eastern_mortal_city` | 凡俗城镇与胥吏 | place | 东·仙 | 粮食与人力来源；让冲突产生可计算的平民代价 |
| 54 | `eastern_pilgrimage_festival` | 庙会、香火与节庆 | institution | 东·仙 | 跨阶层共处的公开场景；香火收入即地方实权 |

## 类别覆盖

| 类别 | 数量 | 说明 |
|---|---|---|
| power | 13 | 力量与能力：资质、境界、功法、灵气、符阵、丹器、剑修、雷法、神通 |
| conflict | 8 | 天劫、宗门战争、正统之争、魔潮、试炼、瘟疫、夺嫡、禁术 |
| place | 8 | 秘境、洞天福地、灵脉、坊市、飞升上界、界域通道、遗迹、凡俗城镇 |
| organization | 6 | 宗门、修真世家、道门、散修、魔道、仙盟 |
| item | 6 | 丹药、法宝、飞剑、储物器、天材地宝、傀儡 |
| institution | 5 | 师徒谱系、王朝供奉、门规清规、仙籍登记、庙会节庆 |
| life | 4 | 修士分层、妖修、灵兽、阴灵 |
| economy | 4 | 灵石本位、贡献点配给、灵植灵田、客卿雇佣 |

按题材计数：同时标两题材 45，含 `eastern_fantasy` 47，含 `xianxia` 52；仅玄幻 2（血脉传承、傀儡造物），仅修真／仙侠 7（符箓、剑修、雷法、道门、仙籍、飞升、洞天福地）。两题材各自可适用元素均远超 20 项的下限要求。

## 组合限制（怎么用，别怎么用）

`requires` / `excludes` 是**自然语言条件**，不是已实现的外部依赖 ID；本目录没有向任何数据库注册这些条目。

几个必须成组出现的搭配：

- `eastern_spirit_stone_currency` + 检验手段 + `eastern_market_fangshi`：可消耗物作通货，缺了验真与信誉机构就会立刻沦为伪币泛滥，而不是"方便的货币"。
- `eastern_sect` + `eastern_spirit_agriculture` / `eastern_spirit_vein` / `eastern_contribution_points`：宗门要养人，就必须有田、有矿或有供奉；三者全无的大宗门不成立。
- `eastern_realm_system` + `eastern_tribulation` + `eastern_ascension`：等级制必须有天花板与退场机制，否则强者永不离场，世界格局被长生者锁死。
- `eastern_talisman` / `eastern_thunder_ritual` + `eastern_dao_lineage` / `eastern_immortal_register`：符与雷法的效力绑定"有职者方能行法"，资格与程序是前提，不是装饰。
- `eastern_spirit_root` + `eastern_cultivation_method` + `eastern_sect`：资质判定要与功法适配、与入门筛选同时存在，否则"资质"只是数值标签。

明确互斥或需要额外铺垫的：

- `eastern_storage_artifact` 普及 vs `eastern_mortal_city` 的运输业、关卡与仓储：储物器一旦廉价普及，脚夫、镖运、仓房就应当衰退，须交代这一过程，不能两者共存而无摩擦。
- `eastern_flying_sword` 普及 vs 城防与关隘：飞行常态化就必须重写城防与通缉体系。
- `eastern_cultivator_strata` 的强隔离 vs `eastern_secret_contest` 的公开竞争：若凡俗完全不知修行界存在，跨门大比就不能成为公共事件，二者需择一。
- `eastern_mortal_plague` 不能用一次法事或一颗丹药全数解决；`eastern_ruin_relic` 不能发现即仿制量产。

## 跨组共享与题材外引入

- 与其它组可能重叠的母题（由主代理统一去重，本组不擅自删除变体）：
  - `eastern_cultivator_strata`、`eastern_mortal_city` 与 society 组的阶层／基层治理母题同构。
  - `eastern_mortal_plague` 的矿物中毒与 steam-horror 组的工业污染、公共卫生母题相邻。
  - `eastern_forbidden_technique` 与 dark_fantasy 组的禁忌知识母题相邻。
  - `eastern_alliance_pact`、`eastern_market_fangshi`、`eastern_retainer` 与 western 组的公会／雇佣兵母题相邻（但本组的行会来源以西欧为主要背景，已在 `rights_note` 中注明，不据此断言东方同类组织形态相同）。
- 本组未引入任何题材外的技术元素（火药、蒸汽、火器等），因此不涉及材料／能源／工艺／制度前置条件问题；若后续引入，须按规范要求逐项核对材料、知识、工艺、能源、成本与制度，且**原型不等于量产**。
- 一条硬约束：**不得用"灵力万能"抹掉前置条件**。`eastern_spirit_qi` 的 `excludes` 明确写了灵气不能与电力、魔力等异体系能量直接换算——这正是 `narrative-element-library.md` 强调的"不能因带相同能量标签就自动换算为同一资源"。

## 变体与限制的写法约定

- 每条 `variants` 为 2—4 项，全部以"某类作品常见做法"的口气书写，**不声称所有作品都遵守**。例如境界体系给了三变体（少层大差距／多层细碎／各门名目不同需换算），因为来源显示各作品层级本就不一致。
- 每条都含 `excludes`，用于提前挡住"无代价"设定（无材料成丹、无阵眼绝对防御、无衰减灵脉、无副作用丹药等）。
- `introduction_limits` 统一要求：先局部原型、后规模；先概念与传闻、后普及；发现不等于掌握，掌握不等于量产。
- `entry_modes` 统计：`existing` 53、`discovery` 51、`player_proposal` 20——只有确实允许玩家提出的条目才标 `player_proposal`（如灵根改造、傀儡承魂、禁术、遗迹逆向）。

## 来源说明

登记 17 条，**16 条实际读过正文**（`access: read`）。全部为百科类汇编条目，属"可靠参考"的**下限**，正式入库前应替换为专著或一手文献。

本轮新增 2 条（均为 `read`，已实际抽取正文）：

- `eastern_src_shenxiao`（神霄派）——用于 `eastern_thunder_ritual` 的历史证据：北宋末兴起、王文卿与林灵素、五雷符法、内丹与符箓融合、天人感应理论基础、「内而修之…外而用之」两段结构、明代周思得为明成祖行祈雨类仪式、南宋分派繁多而「讹舛失真」「互生谤惑」。
- `eastern_src_lijia`（里甲制度）——用于 `eastern_mortal_city`、`eastern_immortal_register`、`eastern_contribution_points`、`eastern_secret_contest`、`eastern_rogue_cultivator` 的制度类推：一百十户为一里、丁粮多者十户任里长、十年一轮、黄册与鱼鳞图册、里老人制与粮长制、地区差异（华北/江南/华南型）、晚明衰落与保甲替代。**时期限明代，不得照搬。**

| 来源 ID | 页面 | 状态 | 主要支撑范围 |
|---|---|---|---|
| `eastern_src_xiuzhen` | 修真（道教理论之一） | read | 修真在道教语境中的用法；内丹门派与次第；剑仙之说；外丹没落时间 |
| `eastern_src_realm` | 修真境界 | read | 十余种互不相同的网络小说境界体系；道教五仙、七候、五时；静功方法 |
| `eastern_src_daoism` | 道教 | read | 全真／正一两派组织形态；斋醮分类；外丹内丹符箓定义；戒律与禁忌 |
| `eastern_src_daoism_history` | 道教历史 | read | 形成于公元2世纪；政教关系；寇谦之、陆修静、陶弘景改革；唐代崇道与道举 |
| `eastern_src_dongtian` | 洞天福地 | read | 洞天／福地分级与"多系实指"；十大洞天、三十六小洞天、七十二福地；入山合药 |
| `eastern_src_clan` | 宗族 | read | 父系单系集团；宗子与支线；族谱；械斗；聚居防御 |
| `eastern_src_menfa` | 门阀（士族） | read | 东汉形成；九品中正；田庄与依附人口；士庶婚姻壁垒；科举后衰落 |
| `eastern_src_exam` | 科举制度 | read | 分科、自由报考、以成绩定取舍；糊名誊录；三级考试；后期束缚 |
| `eastern_src_guild` | 行会 | read | 同业组织；行规与纠纷调解；排他；兼生产、军事、宗教、互助 |
| `eastern_src_fengshui` | 风水 | read | 形势派与理气派方法；罗盘；山环水抱；龙脉地脉观念 |
| `eastern_src_alchemy` | 炼丹术 | read | 金丹与内丹的统称；外丹火炼水炼；以身为炉鼎 |
| `eastern_src_xuanhuan` | 玄幻小说 | read | 「玄幻」词源与泛化；玄幻≈修真的类型评估；修真重境界描写；融合东西要素 |
| `eastern_src_spirit_root` | 灵根 | read | 明确所指为《从前有座灵剑山》设定：资质、天然／人造、五行与品级 |
| `eastern_src_lingshi` | 灵石（汉语词语） | read | 最早见于道教典籍；万载灵气凝结之矿物、多产名山；《云笈七签》验真法 |
| `eastern_src_shenxiao` | 神霄派（新增） | read | 北宋末雷法支派；五雷符法；内修—外用；符箓与仪式；分派与真伪混杂 |
| `eastern_src_lijia` | 里甲制度（新增） | read | 明代基层编制与赋役；黄册、鱼鳞图册；里老人、粮长；地区差异；衰落 |
| `eastern_src_zhihu_realm_discuss` | 知乎：四类命名区别 | **unavailable** | 抓取 HTTP 403，未获正文；**未据其形成任何结论**，仅登记失败 |

### 事实与设计归纳的分界（节选，完整版见 JSON 各条 `evidence_note`）

- **有来源支撑的事实性陈述**：道教形成于公元2世纪；全真出家受戒／正一受箓并发给戒牒、箓牒；斋醮分清醮与幽醮；外丹以丹砂、铅、汞、云母入炉；洞天福地分三级且"多系实指"；宗族为父系单系集团；门阀以经学与婚姻维持；科举以糊名誊录防弊；行会订行规并排外。
- **属类型惯例（有来源确认其"是小说设定"）**：灵根即修行资质；境界阶梯；修魔／修妖各成体系；妖魔鬼神诸界并存；玄幻类型无统一硬规则。
- **纯属本项目设计归纳（无史料/无来源对应）**：灵石作为一般等价物与通货；贡献点配给制；储物法器对贸易与治安的连带影响；坊市"庇护—抽成—验货—禁则"治理结构；宗门战争的"目标—动员—后勤—战后重排"链条；飞升的"清场"功能；魔潮的镇守成本分摊。
- **信仰叙述，不作经验事实**：符箓召遣鬼神、雷法役使雷部、鬼修与炼度施食的效力、灵石的神异性质。涉及历史与民俗处已限定地域与时期（如行会以西欧为主、门阀限东汉至唐、泰山石敢当定于宋元之际）。

## 已知不足（供主代理决定是否补采）

1. **来源层级偏低**：16 条全部是百科汇编或词条，无学术专著、无一手道经原文核对。`eastern_src_alchemy` 词条极短，只够界定术语；丹方、药物配伍与毒性病理需另找医药史／化学史材料。
2. **仍然待补的知识点**（已在对应 `evidence_note` 中标出）：
   - 雷部神将谱系与具体仪轨细节（本轮已补神霄派词条，但仍无一手道经或科仪书）；
   - 胥吏/里甲以外的基层治理（已补明代里甲，但其他朝代仍缺）；
   - 香火会社的具体组织形态（无专门来源）；
   - 丹药重金属中毒的病理与剂量（无医药史/化学史专门来源）；
   - 宫观田产与庄园经济的一手资料。
3. **`eastern_thunder_ritual` 仍是证据链最弱的一条**：本轮补入神霄派后，已能支撑「雷法作为历史宗教实践存在」与「内修—外用两段结构」；但仍**无法**支撑雷部神将谱系、具体仪轨流程，更不能支撑雷电可被召役。「雷法作为雷系战斗属性」在条目中已明确标为**虚构变体**。
4. **篇幅**：规范已取消完整条目字数上限，故不再按 200—350 字要求。本轮 54 条 `details` 实测 817—1252 字/条（均值 941），属有效信息密度而非凑长；扫读摘要字段（`summary` 等）仍保持简短。
5. **旧 `requires`/`excludes` 中的武断陈述已逐条审视**：对原先写得过于绝对的条件（如「丹药无副作用」「灵石必为通货」「境界必为阶梯」），已在 `details.conditions` / `details.exceptions` / `adaptation_limits` 中改为可选玩法或世界配置项，并把一种网文设置降为「变体」。
6. **`eastern_src_zhihu_realm_discuss` 抓取失败**（HTTP 403），若需该角度须换可访问来源。
7. **未登记为来源的失败访问**（未取到实质正文，故不列入 `sources`，此处一并披露）：`道观` 词条抓取返回 HTTP 403；`内丹` 词条为多义词导航页、无实质正文；国家宗教事务局「道教」栏目页仅返回导航文字。三者均未被引用。
8. 未做的事（按任务边界）：未改源码、未改 `data/` 或任何 StoryPackage、未建数据库、未与其他组文件交叉去重、未 git commit。
