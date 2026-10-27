# 蒸汽朋克 · 灵异/民俗恐怖 跨题材元素候选（steam-horror）

状态：**候选资料**（`status: candidate`, `schema_version: 1`）。不是元素数据库实现，也不是任何故事包已经采纳的设定。
规范见 [collection-spec.md](collection-spec.md)；设计方向见 [../../narrative-element-library.md](../../narrative-element-library.md)。

- 元素总数：**50**（纯蒸汽 **26**、纯灵异 **18**、两题材共用标签 **6**；按题材计：蒸汽朋克可适用 **32** = 26+6，灵异/民俗恐怖可适用 **24** = 18+6）
- 表格行数 52 ≠ 元素数：`horror_seance_sitting` 与 `horror_inquest_evidence` 因与蒸汽侧相关，在第二、三节各列一次（去重后仍为 50）
- 两题材**分开采集、分表呈现**，不把「蒸汽」与「灵异」强行混搭为一套世界规则；共用标签只表示同一母题在两个题材下分别成立，**不表示两者的设定可以互换或互证**
- 完整字段（requires / excludes / background / introduction_limits / evidence_note 等）以 [steam-horror.json](steam-horror.json) 为准；本页只做快速扫读

## 零、详细化说明（本轮扩充）

每条元素在 JSON 中新增了两个字段：

- **`details`**：固定七节 —— `definition`（定义与边界）/ `mechanism`（因果链）/ `conditions`（原型→局部→复制→普及的条件）/ `exceptions`（例外与反例）/ `story_consequences`（剧情后果）/ `adaptation_limits`（跨题材与改编边界）/ `evidence_and_uncertainty`（来源支持 / 类型常见变体 / 项目设计三分）。
- **`detail_status`**：全部为 **`needs_detail`** —— 即「已完成详细化但未经主审 review」，**不得**当作 `reviewed_detail` 使用。

篇幅：七节合计约 **26,700 字**，均摊每条约 **535 字**（无硬字数下限，不靠搜模板凑量）。

写作约束（本轮遵守）：

1. 短 `summary` **保留不改**，详细内容只进 `details`，不重复模板灌水。
2. 技术条只讲**因果与工程限制**，不写制作、医疗或仪式操作指南。
3. 原型→局部→复制→普及四阶段逐条写明条件；**不把「十年」一类的设计节奏当历史定律**——原先 10 条带固定年数的 `introduction_limits` 已全部改为「取决于条件、不预设年数」。
4. 旧 `requires`/`excludes` 过强处已**软化为特定变体**：义务人不再默认是宗族（家族/同乡/雇主/行会/教区皆可），禁忌不再以民俗为前提，纪念性建筑不限宗族。
5. 灵异条一律区分**信仰记录**与**实际事实**：`evidence_and_uncertainty` 均以「作为社会事实可成立 / 作为超自然机制须本故事设定确认」双轨表述。
6. 现实自然基础（物理、化学、能源）属另一个 `reality-physical` 库，本组**不复制**其普遍原理，只在必要时点到因果为止。

## 一、蒸汽朋克元素（本表 26 项纯蒸汽；另有 6 项两题材共用的蒸汽侧见第三节）

| ID | 名称 | 类别 | 一句话要点 | 主要限制 |
|---|---|---|---|---|
| steam_reciprocating_engine | 往复式蒸汽机 | power | 通用原动机；能否铺开取决于维护与技工 | 缸体需精密镗削；出力受锅炉压力与燃料硬约束 |
| steam_high_pressure_boiler | 高压锅炉与动力密度 | power | 让动力变小变可移动的关键 | 需耐压材料、铆/焊工艺与操作纪律；无检测手段不得普及 |
| steam_condenser_efficiency | 分置冷凝器与热效率 | power | 同量燃料出更多功 | 需冷却水；缺水严寒处难维持 |
| steam_coal_fuel_chain | 煤—蒸汽燃料链 | economy | 真正的瓶颈常在煤能否按价到位 | 无矿无运力处不能维持工业；煤不是免费资源 |
| steam_mine_drainage | 矿井排水与深井开采 | power | 蒸汽机最早的实用用途 | 井深受排水能力限制；瓦斯与粉尘是常驻风险 |
| steam_precision_boring | 精密镗缸与机床工装 | power | 技术门槛的具象化 | 需技工、刀具钢、量具与稳定动力；不能随身携带机床 |
| steam_interchangeable_parts | 互换零件与批量生产 | economy | 维修从「配做」变「换件」 | 缺公差体系时只是宣传；手工件与量产件不同档 |
| steam_factory_discipline | 工厂制度与工时纪律 | institution | 动力集中带来的人身约束 | 无集中动力需求的行当不必工厂化 |
| steam_industrial_city | 工业城市与贫民街区 | place | 阶层与污染的空间分区 | 不能在无燃料无运力处凭空出现 |
| steam_trunk_railway | 干线铁路与时刻表 | place | 同时是运输网与权力工具 | 山地沼泽造价不同；无线无信号不得高密度运营 |
| steam_station_yard | 车站、货场与编组场 | place | 检查点与调度枢纽 | 小站无大站仓储能力；无单据不能追责 |
| steam_paddle_steamer | 蒸汽轮船与河海航线 | place | 首次能稳定逆流上行 | 需加煤站；风帆与蒸汽长期并存 |
| steam_rigid_airship | 硬式飞艇与航空运输 | item | 类型标志物，也最易被写成奇迹 | 遇风暴结冰脆弱，不能全天候；成本与事故使其难普及 |
| steam_lifting_gas_risk | 浮升气体的易燃代价 | item | 氢气便宜易爆、氦气安全难得 | 稀有气体不是随手可得；不能既廉价又绝对安全 |
| steam_patent_monopoly | 专利与特许垄断 | institution | 把「谁会造」变成「谁有权造」 | 专利不等于已量产；跨国须逐国申请 |
| steam_joint_stock_capital | 股份公司与工业资本 | economy | 重资产工程的集资形态 | 无产权保障只能靠亲族合伙；融资≠技术 |
| steam_labour_union | 工会与集体谈判 | organization | 劳资冲突的组织形式 | 分散外包工人难组织；内部并非铁板 |
| steam_mutual_aid_society | 互助社与工伤风险分担 | organization | 无社保年代最贴近的安全网 | 赤贫者被排除；不能替代强制保险 |
| steam_imperial_resource_flow | 殖民原料与倾销市场 | economy | 本土账目好看，代价由当地承担 | 不得把殖民地写成空白地；须写抵抗与治理成本 |
| steam_gauge_standard | 规格、轨距与标准之争 | institution | 标准改动牵动既有投资 | 多方割据时无法自发生效；非一夜完成 |
| steam_standard_time | 标准时间与调度纪律 | institution | 时间变成可核对追责的对象 | 无通信无法全网校时；不得假设立刻接受 |
| steam_safety_regulation | 安全监管与事故调查 | institution | 多是死亡倒逼出的制度 | 早期几乎无监管；监管不能消灭事故 |
| steam_lone_inventor_prototype | 孤独发明家与原型机 | conflict | 最典型的起点，也最易被误认作产能 | **原型≠可复制≠量产**；不能从图纸一跳进工厂 |
| steam_workshop_apprentice | 工坊学徒与技艺传承 | organization | 比机器更难复制的技艺上限 | 培养以年计；技工不是可批量购买的工具 |
| steam_coaling_station_port | 加煤站与港口补给 | place | 可达范围由补给点间距决定 | 无补给点的远程航线不成立 |
| steam_deskilling_craft | 去技化与手艺人的没落 | conflict | 机器拆解工序，削弱匠人议价 | 非所有行业同步；机器化≠质量提升 |

## 二、灵异/民俗恐怖元素（本表 20 项 = 18 项纯灵异 + 2 项共用重复列出；其余共用见第三节）

| ID | 名称 | 类别 | 一句话要点 | 主要限制 |
|---|---|---|---|---|
| horror_restless_dead | 未得安顿的亡者 | conflict | 未被安顿者被视为滞留致祸 | 须限定汉文化影响圈；**不得当作已证实的超自然事实** |
| horror_vengeful_grudge | 怨念与索报 | conflict | 提供因果：有账要算、有条件可谈 | 不得写成无差别随机杀戮；索报规则须设定明写 |
| horror_possession_state | 附身与身心异常 | conflict | 诊断权之争的场域 | 不得等同精神疾病、也不得反向归因；不写操作步骤 |
| horror_medium_go_between | 灵媒与中介者 | organization | 不可靠却掌握关键信息的证人 | **萨满一词严格限北亚语境**，不得泛用 |
| horror_seance_sitting | 降神会与通灵研究 | organization | 把「与死者说话」变成可围观可质疑 | 现象不得当作已证实；不提供可照做流程 |
| horror_haunted_dwelling | 凶宅与不洁居所 | place | 空间记忆＋产权纠纷叠加 | 「凶」非房屋普遍属性；霉变缺氧等不得直接写成超自然 |
| horror_grave_disturbance | 墓葬、掘扰与随葬 | place | 随葬标示身份，也招来觊觎 | 不得把各地葬式混为一种；掘墓必有社会后果 |
| horror_second_burial | 二次葬与骨骸处理 | conflict | 把「死亡是过程」制度化 | 不适用于以即时入土/火葬为终的社群 |
| horror_omitted_rites | 丧仪残缺与失序的死亡 | conflict | 死者未得位置，活人背上义务 | 简葬≠失序；仪式功效未被证实 |
| horror_taboo_breach | 禁忌与违约 | institution | 违约后社群对违约者的重新定位 | **不得合并各地禁忌为单一规则集**；后果非物理定律 |
| horror_amulet_ward | 护符与辟邪物 | item | 效力归于来源与制作，而非材质 | 不是万能护盾；不得跨文化套用形式 |
| horror_exorcist_office | 驱邪职与仪式专家 | organization | 授权来自制度，故本身是权力问题 | 不是高成功率技术；**不写现实危险仪式** |
| horror_boundary_place | 边界地带与路口 | place | 「之间」的空间易出事也宜处置 | 不得把路口一律写成凶地 |
| horror_local_shrine | 地方神祠与地祇 | organization | 管辖有限、交换关系明确 | 不得写成全知全能；不得混并各地祠神体系 |
| horror_ancestral_hall | 祠堂与祖先牌位 | place | 族权的物理载体：入祠/除名 | 不得假定所有地区以宗族为基层组织 |
| horror_lineage_elders | 宗族长老与祭祀组织 | organization | 能把「犯忌」变成可执行裁决 | 不得写成必然保守或必然公正；须注意性别与外来户位置 |
| horror_village_calendar_rite | 村落节令祭仪 | institution | 把一年切成可预期段落 | 不合并各地节令；不把仪式写成奇观 |
| horror_rumour_chain | 传闻链与口传变体 | conflict | 说法本身就能造成后果 | 传闻≠事实；都市传说形态不可套用到前工业社会 |
| horror_case_dossier | 案卷、族谱与地契 | item | 能证明归属，也能被抽走伪造 | 无文字传统只能依赖口传；文书≠事实 |
| horror_inquest_evidence | 验尸、勘验与口供 | institution | 把「怎么死的」变成文书结论 | 不得等同于现代法医学；文书结论未必为真 |

## 三、两题材共用标签的 6 项（有条件共用，不是混搭）

| ID | 名称 | 两侧各自成立的方式 |
|---|---|---|
| steam_gaslight_telegraph_city | 煤气灯与电报网 | 蒸汽侧：管网/线路＋抄报员＋技工；灵异侧：由本故事设定的地方观念。缺一侧即退化为普通城市设施 |
| steam_smoke_pollution | 烟尘、污水与工业病 | 先作为可查证的工业公害成立；「被当地人解释成超自然」是叙事层误读，是否真有超自然成分由故事设定确认 |
| steam_telegraph_evidence | 电报、档案与技术取证 | 技术取证只给「可核对的事实」，不能自动证明或否证超自然解释；两套判据的冲突由作者裁定 |
| horror_seance_sitting | 降神会与通灵研究 | 需城市通信与印刷条件＋当地亡灵观念与宗教裁断；缺后者时只是骗局或沙龙娱乐 |
| horror_inquest_evidence | 验尸、勘验与口供 | 文书死因与社群说法可并存；**不得默认官方文书更真**，孰为真相由故事设定裁定 |
| horror_mass_fatality_industry | 工业事故的集体死亡 | 先有可信技术成因与处置记录，再有本故事明确设定的亡灵观念与安顿规则；不得「所以一定闹鬼」直接接续 |

## 四、组合限制（把两题材放进同一个故事包时必须先满足）

1. **不自动换算资源。** 煤、蒸汽压力、电力、灵力、怨气、香火不是同一种可互换的「能量」。任一跨界转换都须在故事包里写明来源、载体、损耗与上限。
2. **动力先于奇观。** 任何移动式机械、飞艇、巨型装置，先要回答燃料从哪来、谁来修、坏了怎么办；补给点间距决定可达范围（见 `steam_coaling_station_port`）。
3. **原型不等于量产。** 蒸汽侧允许「西幻世界中被发现的原型机」，但必须带材料、知识、工艺、能源、成本与制度条件；单台样机 = 孤例，不是工业体系（见 `steam_lone_inventor_prototype`）。
4. **民俗规则须由本故事设定确认后才生效。** 本文件记录的是**信仰与习俗的记述**（谁相信、如何行动、如何处置），不是超自然事实的证明。任何「鬼确实存在／禁忌确实会索命」的机制，必须在故事包中另行写明可辨识条件、解除代价与失效方式。
5. **地域与时期必须限定。** 每条民俗类元素的 `evidence_note` 已标注地域范围；跨越文化圈的借用（例如把北亚萨满、汉文化宗族、欧美唯灵论混为同一套体系）没有依据，须逐条重设。
6. **不得把所有地区民俗合并成单一规则。** 中国民间实践并不存在单一宇宙论可统摄（见 `sh_src_24`）；禁忌、葬式、护符形式在各地差异大于共性。
7. **恐怖不能代替调查。** 「有鬼」不能成为跳过取证、责任归属与制度批判的万能解释；反之，纯技术解释也不能强行否证作者已设定的超自然层。
8. **跨题材玩家提案要更严格。** 跨度大的引入（如把灵异规则直接用于驱动蒸汽机械）须记录：提案者、知识与材料条件、实验过程、失败结果、资源消耗、传播范围与对势力/经济/宗教的后果（依 collection-spec 第 51 行）。
9. **不提供现实危险操作。** 本组刻意不写驱邪、通灵、禁忌仪式的可执行步骤或配方；相关元素只描述社会角色与制度位置。

## 五、来源说明

本次实际联网 `read` 抓取成功的页面：**41 个不同 URL**（`sh_src_01`—`sh_src_42` 中的 read 项），另有 **5 个记录为不可用**（`sh_src_28`/`sh_src_43`/`sh_src_44`/`sh_src_45`/`sh_src_46`），**任何元素都未引用这些失败来源**。本组共 46 个 source 条目。

本轮新增（第二轮）可读来源：

| ID | 来源 | 访问 | 支持的方面 |
|---|---|---|---|
| sh_src_29 | Steam turbine (Britannica) | read | 涡轮原理、热耗率、锅炉管道结垢与耐火内衬是主要维护项、军舰装舰时间 |
| sh_src_30 | Boiler (Britannica) | read | 锅炉三要素、火管/水管两路线、安全阀必备、给水处理与结垢、帕潘 1679、水管式随涡轮需求出现 |
| sh_src_31 | Bessemer process (Britannica) | read | 首个廉价量产钢、贝塞麦/凯利同时独立、碱性炉衬解决高磷、氮残留至 1950s、平炉后起取代 |
| sh_src_32 | Iron processing (Britannica) | read | 高炉还原化学、焦炭替代木炭、蒸汽鼓风提升产量、含碳量与钢/铸铁性能 |
| sh_src_33 | History of technology — Industrial Revolution (Britannica) | read | 「工业革命」术语不精确；蒸汽长期属例外；瓦特构想受加工水平限制、需博尔顿资本；1775—1800 约产 500 台；瓦特专利压制高压、1800 到期后高压兴起；1804 机车压裂铸铁轨；复胀/康沃尔机/涡轮 1884 |
| sh_src_34 | Ghost (Britannica) | read | 鬼的定义、葬仪可阻止作祟的信念、闹鬼与强烈情绪/未了旧事关联、视听表现清单 |
| sh_src_35 | Poltergeist (Britannica) | read | 间歇不可预测、集中于某成员、有外人时停止、部分被指为歇斯底里、多被解释为自然现象 |
| sh_src_36 | Ghoul (Britannica) | read | 阿拉伯/北非特定传统的 jinn 类别、可变形、一击致死的民间说法 |
| sh_src_37 | Magic (Britannica) | read | 象征性因果、咒语/材料/仪式三要素、交感观念、施术者地位因社会而异 |
| sh_src_38 | Occultism (Britannica) | read | 19 世纪欧洲建构的谱系、与唯灵论相互贬斥 |
| sh_src_39 | Divination (Britannica) | read | 三类分法、中国占卜无单一宇宙论、占卜师身份多样、欧洲态度从恐惧到沙龙娱乐 |
| sh_src_40 | Ritual (Britannica) | read | 仪式的象征性与功能性、过渡与周期性之分、维系社群与缓解紧张 |
| sh_src_41 | Horror film (Britannica) | read | 恐怖是大类，含多个子类型（不能据此等同 folk horror） |
| sh_src_42 | Fantasy (Britannica) | read | 类型标签是当代分类而非历史范畴 |

第一轮可读来源（`sh_src_01`—`sh_src_27`）与上版相同，不再重复列出。

| ID | 来源 | 访问 | 支持的方面 |
|---|---|---|---|
| sh_src_01 | Steam engine (Britannica) | read | 蒸汽机部件、纽科门→瓦特分置冷凝器、机车与汽船节点 |
| sh_src_02 | Steam power (Britannica) | read | 用途演变、效率与压力/冷凝温度、涡轮 |
| sh_src_03 | Airship (Britannica) | read | 三类结构、氢气/氦气、1852 蒸汽飞艇、退出商业原因 |
| sh_src_04 | Machine tool (Britannica) | read | 镗缸、丝杠车床、夹具量规与互换件、出口禁令 |
| sh_src_05 | Railroad (Britannica) | read | 系统组成、选址权衡、调度与信号、定价权力 |
| sh_src_06 | Coal mining (Britannica) | read | 排水限制、通风与安全灯、瓦斯粉尘与尘肺 |
| sh_src_07 | Industrial Revolution (Britannica) | read | 技术/社会经济/文化特征、区域起点不同 |
| sh_src_08 | Trade union (Britannica) | read | 集体谈判、起源与被诉、英美路线差异 |
| sh_src_09 | Patent (Britannica) | read | 有限期排他权、先申请/先发明、19 世纪末多国并存 |
| sh_src_10 | What Is Steampunk? (The Steampunk Explorer) | read | 类型定义争议、非皆有蒸汽机、欧洲中心批评、时代下限 |
| sh_src_11 | 蒸汽朋克（百度百科） | read | 中文语境的类型表征归纳（先进/落后共存、拼凑美学等） |
| sh_src_12 | Ancestor worship (Britannica) | read | 祖先资格、奖惩与中介、地区差异、二次葬与洗骨 |
| sh_src_13 | Exorcism (Britannica) | read | 驱邪定义、驱邪品级出现、教规管理 |
| sh_src_14 | Possession (Britannica) | read | 附身表现、媒介型/侵害型、与医学解释关系 |
| sh_src_15 | Spiritualism (Britannica) | read | 1848 起源、降神会、通灵研究、大量揭伪 |
| sh_src_16 | Burial (Britannica) | read | 葬式类型、墓室阶层差异、二次葬、公墓出现 |
| sh_src_17 | Cremation (Britannica) | read | 火葬的地区与宗教差异、19 世纪复兴、骨灰处置 |
| sh_src_18 | Witchcraft (Britannica) | read | 恶意巫术的多地区分布、交感观念、猎巫的特定时空 |
| sh_src_19 | Animism (Britannica) | read | 多灵信仰、以实际事务为中心、禁忌与安抚、地方性 |
| sh_src_20 | Shamanism (Britannica) | read | 语源与严格适用范围、受职与磨难、鼓与服饰、与他类治疗者区别 |
| sh_src_21 | Amulet (Britannica) | read | 护符效力来源、天然/人工类型、宗教差异 |
| sh_src_22 | Folklore (Britannica) | read | 民俗学对象、变体与传播、语境转向、都市传说 |
| sh_src_23 | Ghost Festival (Britannica) | read | 中元/盂兰盆的地区与历法、供养超度 |
| sh_src_24 | Chinese religion (Britannica) | read | 三教与民间信仰混合、孤魂致祸、无单一宇宙论、祖先牌位 |
| sh_src_25 | Horror story (Britannica) | read | 恐怖文体定义、哥特脉络、现实环境支撑恐怖 |
| sh_src_26 | Spirit (Britannica) | read | 灵性存在的地方性、与媒介和祖先的关系 |
| sh_src_27 | The Folklore Society（机构首页） | read | 民俗学学科定位与研究范围 |
| sh_src_28 | Steampunk (English Wikipedia) | **unavailable** | 连接超时未获正文，**任何元素均未引用** |
| sh_src_43 | Telegraph (Britannica) | **unavailable** | 仅有导言，正文在付费墙后；**不用它支撑任何断言** |
| sh_src_44 | BFI folk horror 专页（多次尝试） | **unavailable** | 多个 features/lists 路径均 404 或超时，未获正文 |
| sh_src_45 | Folk horror (English Wikipedia) | **unavailable** | 主站/移动版/REST API/镜像均连接失败 |
| sh_src_46 | 研究型期刊页（Taylor & Francis） | **unavailable** | 403 人机校验，未获正文 |

补充说明（如实记录本次采集的不足）：

- 英文维基百科与部分 Britannica 子条目多次连接超时（`sh_src_28` 及 `factory-system`/`telegraph`/`cemetery` 等页），已放弃并改抓其他可读来源，未拿搜索摘要充当全文。
- 中文搜索渠道（含必应）对「蒸汽朋克」「民俗恐怖」「onryō/yūrei」等关键词返回大量无关或作品向结果，因此**没有**采用中文百科作为技术史或民俗规则的主要依据；`sh_src_11` 仅用于类型表征归纳。
- 另有一次抓取事故：Britannica 的 `taboo` 词条 URL 实际返回的是同名**电视剧**条目，与禁忌概念无关，已弃用、未记入 sources。
- **Folk horror 类型学仍是证据空白（本轮重点尝试失败）**。已专为本轮尝试 BFI（`where-begin-folk-horror`、`10-folk-horror-films`、`folk-horror`、`10-great-folk-horror-films`、`folk-horror-genre-guide` 等）、英文维基（主站/移动版/REST/wikiwand 镜像）、The Conversation、Literary Hub、Senses of Cinema、Offscreen、Taylor & Francis 等，均为 404/超时/403。**因此本组没有任何一条元素声称「folk horror 必须包含 X」**，也没有以 BFI 名义引述。`sh_src_41`（恐怖片）只能说明恐怖是大类，**不能用它推出 folk horror = horror**。这是本组最大的证据空白。
- 灵异侧多数来源是**百科条目**而非田野民族志；其价值在于核对「存在哪些观念与实践」，不足以支撑任何具体地区的细节规则。凡涉及具体地区，`evidence_and_uncertainty` 均已限定并声明为信仰记述。
- 部分**具体制度沿革**（验尸制度、工会立法年表、锅炉监管立法、电报史）未在已读来源中核实，已在对应 `details.evidence_and_uncertainty` 中明写为**证据空白**，未编造年表。
- 所有 `evidence_and_uncertainty` 均按三分结构撰写：**来源支持（带 sh_src_xx 引用）/ 类型常见变体 / 本项目设计归纳**；设计归纳部分明确标注未经来源证实。

## 六、索引：按类别与题材快速定位

**力量技术 power（5）**：steam_reciprocating_engine、steam_high_pressure_boiler、steam_condenser_efficiency、steam_mine_drainage、steam_precision_boring

**经济生产 economy（4）**：steam_coal_fuel_chain、steam_interchangeable_parts、steam_joint_stock_capital、steam_imperial_resource_flow

**社会制度 institution（9）**：steam_factory_discipline、steam_patent_monopoly、steam_gauge_standard、steam_standard_time、steam_safety_regulation、steam_telegraph_evidence、horror_taboo_breach、horror_village_calendar_rite、horror_inquest_evidence

**地点探索 place（10）**：steam_industrial_city、steam_trunk_railway、steam_station_yard、steam_paddle_steamer、steam_gaslight_telegraph_city、steam_coaling_station_port、horror_haunted_dwelling、horror_grave_disturbance、horror_boundary_place、horror_ancestral_hall

**物品资源 item（4）**：steam_rigid_airship、steam_lifting_gas_risk、horror_amulet_ward、horror_case_dossier

**组织信仰 organization（8）**：steam_labour_union、steam_mutual_aid_society、steam_workshop_apprentice、horror_medium_go_between、horror_seance_sitting、horror_exorcist_office、horror_local_shrine、horror_lineage_elders

**冲突事件 conflict（10）**：steam_lone_inventor_prototype、steam_deskilling_craft、steam_smoke_pollution、horror_restless_dead、horror_vengeful_grudge、horror_possession_state、horror_second_burial、horror_omitted_rites、horror_rumour_chain、horror_mass_fatality_industry

**起点建议**（从可操作性看，建议按此顺序读）：

- 蒸汽侧：`steam_coal_fuel_chain` → `steam_precision_boring` → `steam_reciprocating_engine` → `steam_lone_inventor_prototype`（先看瓶颈，再看机器，最后看人）
- 灵异侧：`horror_restless_dead` → `horror_possession_state` → `horror_taboo_breach` → `horror_rumour_chain`（先看观念，再看诊断权，最后看传播）
- 跨题材：`horror_mass_fatality_industry` → `steam_telegraph_evidence` → `horror_inquest_evidence`（技术代价 → 取证 → 两套判据冲突）

## 七、仍待补问题（未解决，需后续处理）

1. **Folk horror 类型学专文缺失**（最高优先）。本组关于「民俗恐怖」的类型学没有任何可靠可读来源，只能借用「恐怖文体」与「民俗学」两条外围线索。需后续换渠道（图书馆库、开放获取期刊、实体书）获取 Scovell 等人的论述，再回填到 `horror_*` 系列元素的 `evidence_and_uncertainty`。
2. **验尸/勘验制度沿革未核实**（`horror_inquest_evidence`）。目前只写到「依赖证词与外部检验、系统化尸检较晚」，具体司法程序与年代属空白。
3. **工会与劳动立法年表未核实**（`steam_labour_union`、`steam_safety_regulation`）。已读到「早期被起诉、法律承认滞后」，但具体法案与年份未获可读来源确认。
4. **电报史与标准时间推行细节未核实**（`steam_standard_time`、`steam_gaslight_telegraph_city`、`steam_telegraph_evidence`）。Telegraph 条目在付费墙后（`sh_src_43`），这部分全靠铁路条目与工业革命条目的侧面支持。
5. **中文与东亚地区材料偏薄**。灵异侧可读来源几乎全是 Britannica 英文条目，汉文化圈的具体材料只靠 `sh_src_12`/`sh_src_23`/`sh_src_24`。具体到某一地区（如江南、闽南、华北）的葬俗与祠庙细节，本组无法支撑，需另找地方志或民俗学专著。
6. **蒸汽侧非欧洲技术路线缺位**。目前几乎全部以英国/欧美为背景，没有涉及其他地区的早期蒸汽尝试或替代动力路线。若需要非欧洲中心的世界，须另行采集。
7. **`details` 全部仍为 `needs_detail`**：未经主审，**不得**在正式元素库或故事包中当作定稿使用。需主审逐条核对 `mechanism` 的因果链与 `exceptions` 的反例是否成立。

## 八、本文件的边界

- 只新增本目录下 `steam-horror.json` 与 `steam-horror.md` 两个文件；**未改动** `collection-spec.md`、正式 `data/`、StoryPackage、源码或其他组（`eastern`/`western`/`society`）的文件。
- 未执行任何 git 提交。
- 入库、去重合并与正式 schema 适配须后续另行验收；本文件是候选交换格式，不保证符合未来元素数据库的 schema。
