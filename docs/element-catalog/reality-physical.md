# 现实基础库 · 物理、自然与生产（reality-physical）

对应 [reality-physical.json](reality-physical.json)。状态：**候选资料**（`status: candidate`, `schema_version: 1`），全部条目 `detail_status: needs_detail`。不是数据库实现，也不是任何故事包已采纳的设定。

> 返修状态（主审抽查后，2026-10-26）：已针对重力条目的事实错误、测量术语、食物保存与饮水的过度断言做了订正，并对全部 32 条按「错误比例/物理词义」「因果绝对化」「把技术依赖当现实定律」「无来源支撑的社会结论」四类风险做了定向扫查与改写（详见第七节）。**这属于逐条语法层面的人工复查，不是完整的科学审核**——引用具体数值前仍需逐条回溯来源原文。

规范见 [collection-spec.md](collection-spec.md)（第 62—68 行「现实基础库」一节与「最新决策：开局绑定」一节），设计方向见 [../../narrative-element-library.md](../../narrative-element-library.md)。本页只做扫读索引、来源与限制说明，**完整内容以 JSON 为准**，此处不复制正文。

- 元素总数 **32**；来源条目 **36**（其中 **33 个实际 read 成功**、3 个如实记为 `unavailable`）
- 题材标签统一 `real_world`，分组 `reality-physical`
- 本组**不新增**社会制度、组织信仰类条目；涉及制度处一律以 `related_catalog_ids` 指向 `society` / `western` / `eastern` / `steam-horror` 的既有 id
- 刻意**不与** `steam-horror` 的蒸汽机、锅炉、飞艇、码头等具体技术元素重复；本组只写其背后的现实规律（压强、热传递、浮力、摩擦、材料强度等）

## 一、这个组在收什么

用户要求：只收**能参与故事构建与行动因果**的现实元素，不做完整百科、不写代码、不建数据库。因此本组的取舍标准是「它能否给行动设定代价、给世界设定约束」：

- **力与运动**：重力与载荷、简单机械、摩擦与牵引、浮力
- **流体与热**：压强与流体平衡、热传递与保温、相变与潜热
- **能量与火**：燃烧、能量守恒与做功预算
- **材料**：材料强度与失效、腐蚀、金属冶炼与合金可得性、测量精度
- **水与地形**：水循环、地下水与井、河流与洪水、地形与侵蚀、气候与季节
- **土地与作物**：土壤与地力、轮作、农业起源与驯化
- **食物链后端**：食物腐败、食物保存、发酵
- **生态与人口**：生态系统能量流、环境容纳量
- **公共卫生**：清洁饮水与卫生、传染与传播链、疫情判定与调查
- **移动与定居**：道路与陆上运输、通信距离与信息延迟、栖身建造

**刻意不做的**：不写「火球术如何制造」「黑火药配比」「爆炸装置」「用药与诊疗方案」「水质限量值」。本组只给**原理与因果边界**，不给可执行的危险操作细节。

## 二、扫读表

类别沿用 spec 的八类 id（power/item/place/institution/economy/conflict）。「知识类型」列：emp=empirical 可检验机制，mix=mixed 机制＋历史归纳，his=historical 带地域时期的历史事实。

| ID | 名称 | 类别 | 知识类型 | 一句话要点 | 主要限制 |
|---|---|---|---|---|---|
| reality_phys_gravity_load | 重力与静载荷 | power | emp | 重量逐层下传，最弱一环定上限 | 重力非处处地球常数；超载即事故 |
| reality_phys_lever_pulley | 杠杆、滑轮与简单机械 | power | emp | 省力必多走距离，实际值受摩擦削减 | 支点、绳索与绑扎比示意图更关键 |
| reality_phys_friction_traction | 摩擦与牵引 | power | emp | 与载荷成正比、与接触面积近似无关；静大于动 | 摩擦既是阻力也是行走与制动的前提 |
| reality_phys_pressure_fluid | 压强与流体平衡 | power | emp | 静止流体各向等压，吸程受大气压硬顶 | 泵不能把水提到任意高度 |
| reality_phys_heat_transfer | 热传递与保温 | power | emp | 传导/对流/辐射三路同时散热 | 保温只减缓流失，不产热；湿材料失效 |
| reality_phys_phase_change | 相变与潜热 | power | emp | 恒温下大量吸放热；沸腾段最耗燃料 | 蒸发降温需干燥通风；高海拔沸点低 |
| reality_phys_buoyancy | 浮力与密度 | power | emp | 浮力等于排开流体重；形状让重物浮起 | 吃水受干舷限制；超载即倾覆 |
| reality_phys_combustion_fire | 燃烧与火 | power | emp | 燃料+热+氧三者齐备才自持 | 火不凭空生能；密闭燃烧产一氧化碳 |
| reality_phys_energy_budget | 能量守恒与做功预算 | economy | emp | 能量守恒但逐级以热损耗 | 无输入不能持续输出；效率达不到百分之百 |
| reality_phys_material_strength | 材料强度与失效 | item | emp | 强度取决于形状与节点，不只材料名 | 疲劳与脆断常无预兆；补强效果常低于预期 |
| reality_phys_corrosion | 腐蚀与防护 | item | emp | 金属自发变回稳定化合物 | 点蚀与晶间腐蚀表面无迹；涂覆破损处更危险 |
| reality_phys_metal_supply | 金属冶炼与合金可得性 | item | mix | 矿＋燃料＋炉＋匠人四关合一 | 知道合金名≠掌握配比与热处理 |
| reality_phys_measurement_precision | 测量精度与标准化 | item | emp | 精度≠准确度；校准链断则稳定地错 | 单位不一制造纠纷；高精度可稳定地错 |
| reality_phys_water_cycle | 水循环与可用水 | place | emp | 总量恒定，可用水取决于地点与季节 | 年降水量不足以描述可用水 |
| reality_phys_groundwater_well | 地下水与井 | place | emp | 补给慢、流动极慢、污染难清除 | 超采致水位下降与咸水入侵 |
| reality_phys_river_flood | 河流、洪水与航道 | place | emp | 灌溉/航道/防洪三者互相牵制 | 筑堤不等于消灾；泥沙持续抬高河床 |
| reality_phys_terrain_erosion | 地形、侵蚀与滑坡 | place | emp | 地形是仍在进行的进程，不是静背景 | 开挖坡脚最易诱发滑动 |
| reality_phys_climate_season | 气候带与季节 | place | emp | 气候含极值与频率，须标注年份 | 单年天气不等于气候；旧经验会失效 |
| reality_phys_soil_fertility | 土壤与地力 | place | emp | 成土以百年计，流失以一季计 | 连作耗竭特定养分；施肥不解决涝与盐渍 |
| reality_phys_food_spoilage | 食物腐败 | item | emp | 含水、温度与洁净决定腐败速度 | 霉变非局部问题；冷藏非万能 |
| reality_phys_food_preservation | 食物保存方法谱系 | item | emp | 干燥/盐渍/烟熏/发酵/冷藏/密封各有代价 | 保存不改善原料；方法不可通用 |
| reality_phys_fermentation | 发酵与微生物加工 | economy | emp | 缺氧下糖转酒精/酸/气体，兼保存与加工 | 失控即腐败；配方≠能做出来 |
| reality_phys_crop_rotation | 轮作与农事安排 | economy | mix | 维持地力、断病虫害、摊薄风险 | 部分病原长期存活使轮作失效 |
| reality_phys_agriculture_origin | 农业起源与驯化 | economy | his | 多地独立起源，带来定居与阶层也带来脆弱 | 驯化以世纪计；农业非必然更优 |
| reality_phys_ecosystem_flow | 生态系统的能量流与养分循环 | place | emp | 能量单向逐级损耗，养分在系统内循环 | 顶级捕食者生物量必然最小 |
| reality_phys_carrying_capacity | 环境容纳量与人口压力 | economy | mix | 天花板随技术与贸易移动，不是自然常数 | 可用消耗存量超载一段，代价更陡 |
| reality_phys_drinking_water_sanitation | 清洁饮水与卫生 | institution | emp | 水与排污的距离决定发病率 | 清澈≠安全；供水改善≠卫生改善 |
| reality_phys_disease_transmission | 传染与传播链 | conflict | emp | 特定病原＋可行路径＋易感人群 | 无症状排菌；同一病原多路径 |
| reality_phys_outbreak_investigation | 疫情判定与调查 | institution | emp | 需流行病学关联，环境样本只能加强 | 常无果；结论自带不确定性 |
| reality_phys_road_transport | 道路与陆上运输 | place | mix | 修路不难，难在常年可用 | 无养护数年内即不可用；雨季中断 |
| reality_phys_communication_distance | 通信距离与信息延迟 | institution | mix | 每种媒介都有延迟与容量上限 | 线路可断、信使可截；从不绝对保密 |
| reality_phys_shelter_building | 栖身建造与环境控制 | place | mix | 一顶帐篷已含控温挡风控光全部问题 | 建造不等于可长期居住；维护是持续成本 |

知识类型分布：empirical 25、mixed 6、historical 1。

## 三、来源（实际抓取情况）

全部来源列在 JSON 的 `sources` 中，含 `url` / `access` / `supports` / `rights_note`。要点：

- **33 个页面实际 read 成功**（Britannica 28 个条目 + WHO 2 份 fact sheet + CDC 1 份方法说明 + BIPM/JCGM 计量词汇 4 个词条页与 1 份出版物目录页），`access: "read"`。优先机构与教育参考，与 spec 第 68 行的来源偏好一致。
- **3 个如实记为不可用**，并因此改换支撑来源，未假称抽取成功：
  - `rp_src_33` USGS Water Science School 水循环页 → HTTP 405（站点人机验证）→ 水循环条目改以 Britannica 水循环＋地下水支撑，`evidence_and_uncertainty` 中已注明
  - `rp_src_34` NIST 测量不确定度页 → 两次尝试均请求超时 → 测量条目改以 Britannica measurement **加** BIPM/JCGM 的 VIM3 术语词条（`rp_src_35`）支撑；本文件因此不引用 NIST 的不确定度评定方法
  - `rp_src_37` Britannica food spoilage → HTTP 404 → 腐败条目改以 food preservation / fermentation / WHO food safety 支撑
- 新增计量术语来源（主审返修时补）：`rp_src_35` = VIM3 的 2.13（accuracy）/2.15（precision）/2.26（uncertainty）/2.39（calibration）四个词条页，逐页读取；`rp_src_36` = BIPM 的 JCGM 出版物目录页，仅用于确认 GUM 与 VIM 文件的存在与版本，**未读其正文**。
- 两个来源仅取得导言段，已在 `rights_note` 与相关条目的 `evidence_and_uncertainty` 中标明：`rp_src_09`（strength of materials）、`rp_src_23`（food preservation）。
- `rp_src_16`（geomorphology）与 `rp_src_22`（carrying capacity）为导言级／短条目，相关条目已注明「概念级支撑」。

## 四、证据强度与已知弱项

必须明说，以免被误当成可引证的定论：

1. **强度类条目（材料、压强、重力载荷）的来源只支撑定性结论**（如「强度取决于形状与节点」），具体的承载、吸程、摩擦系数数值来源未给。本组**刻意不提供任何可用于实际工程的参数**，JSON 中多处写明「不作数值承诺」。
2. **historical 类只有 1 项**（农业起源），其年代与地区属考古学共识范围，学界对部分作物的驯化时间仍有争论，已并列而非取单一结论。
3. **mixed 类 6 项**（冶炼、轮作、容纳量、道路、通信、建造）中，「历史演进」部分有来源支撑，「与制度/政治的因果」部分是本项目设计归纳，已在各条 `evidence_note` 与 `details.evidence_and_uncertainty` 中标出。
4. **容纳量的社会模型**（压力→饥荒/迁徙/战争）是本项目推演；来源条目本身仅给出生态学定义，学界对人口与农业的因果方向仍有争论。使用时应视作叙事框架，而非史实断言。
5. **公共卫生三条目**只采用其机制与风险类别，**不引用任何水质限量、消毒配比、用药或隔离时长**——这是 spec「避免医疗处方与现实伤害操作教程」的直接落实。

## 五、使用限制（与 spec 第 54—68 行一致）

- **开局绑定，运行中不选库**：本组条目的 `entry_modes` 只描述预绑定元素在世界内的显现方式。绝大多数字段是 `existing`（现实规律在世界中已生效）；技术应用（如滑车组、深井、密封容器、铺装路面）可在开局被预绑定为「允许研发」，但不得在故事中途从库外新增。
- **不是每局全装**：现实基础是默认候选，仍须按该局背景选择适用版本与条件；架空世界若覆盖现实规律，必须显式声明覆盖范围与后果（重力、燃烧、浮力、病原、生态容量各自都写了「若改写须交代什么」）。
- **原理知识不等于工艺**：本组多处强调「知道机制」与「能做出来」之间的差距（发酵、冶炼、测量、建造尤甚），这直接对应 spec 的「发现原型不等于量产」。
- **魔法不能当万能兜底**：每条的 `details.adaptation_limits` 都写明了「若以魔法替代这一环，须交代什么」，避免用魔法抹掉前置条件。
- **不提供可执行危险信息**：无火器/爆炸/化学配比、无武器制造、无医疗处方、无消毒与净水操作规范。

## 六、与题材库的关联

真实 id 见各条 `related_catalog_ids`，均为既有四组中的实际 id（校验通过）：

- 蒸汽朋克侧：`steam_reciprocating_engine`、`steam_high_pressure_boiler`、`steam_condenser_efficiency`、`steam_coal_fuel_chain`、`steam_paddle_steamer`、`steam_rigid_airship`、`steam_lifting_gas_risk`、`steam_trunk_railway`、`steam_station_yard`、`steam_precision_boring`、`steam_interchangeable_parts`、`steam_gauge_standard`、`steam_mine_drainage`、`steam_coaling_station_port`、`steam_standard_time`、`steam_telegraph_evidence`、`steam_smoke_pollution`、`steam_industrial_city`、`steam_gaslight_telegraph_city`
- 社会制度侧：`society_manor_labor_rent`、`society_corvee_service`、`society_land_survey_tax`、`society_postal_relay`、`society_market_duty`、`society_coinage_mint`、`society_craft_guild`、`society_healthcare_access`、`society_administrative_service`
- 西幻侧：`western_castle_keep`、`western_siege_warfare`、`western_mining_smelting`、`western_gothic_cathedral`、`western_plague_famine`
- 东方玄幻／修真侧：`eastern_spirit_agriculture`、`eastern_spirit_beast`、`eastern_heavenly_material`、`eastern_mortal_plague`、`eastern_pill_elixir`
- 灵异侧：`horror_inquest_evidence`、`horror_case_dossier`、`horror_mass_fatality_industry`

关联方式统一为「现实规律 → 题材元素的技术/制度前提」，**不做反向依赖**：本组条目不要求题材库存在，题材库条目也不把本组当已实现依赖。

另与同批的 `reality-human` 组做分担，避免重复：`reality_phys_measurement_precision` 只写测量误差、精度与校准链的**物理性质**，度量衡的地方差异与统一计量的政令、原器执行属制度史，指向 `reality_human_weights_measures_local` / `reality_human_metrology_standardization`（仅测量一条做了该区分）。

## 七、主审返修记录（2026-10-26）

主审抽查发现事实错误后，只改了 `reality-physical.json` 与本页，条目数未变（仍 32 条），仍全部 `needs_detail`。下面列出改了哪些 ID 与依据。

### 7.1 四项点名错误的修正

| ID | 原先的问题 | 改为 | 依据 |
|---|---|---|---|
| `reality_phys_gravity_load` | mechanism 写「高度翻倍带来的冲击远不止翻倍」 | 改为：忽略空气阻力、g 视为常数时 E=mgh 随高度正比、落地速度按 √h 增长（加倍高度约为 1.41 倍）；冲击力还看减速距离/时间、姿态与材料吸能 | 本项目力学核对；rp_src_01 仅支持 g 与平方反比 |
| 同上 | exceptions「离地加倍引力四分之一」 | 改为「到**天体中心**距离加倍（球对称、外部牛顿近似）」，并说明地表附近升高几十米变化极小 | rp_src_01 |
| 同上 | 静载被写成严格不随时间变化；疲劳混入静载；「每一环都承受压力与弯曲」「最弱一环决定全部」过强；「橡子传檩」错字 | 静载改为「不随时间明显变化」的近似并指出活载/温度/沉降会改变受力；疲劳单列为非静载问题；改为「各构件受力类型不同，哪一环先失效取决于荷载路径、尺寸与节点」；改为「椽传檩」 | rp_src_31；其余为工程常识归纳 |
| 同上 | story_consequences 说主角独力搬重物就一定「不守物理」 | 改为由世界设定的实际质量、结构承载与人物力量量级三者共同判定；真正破坏可信度的是同一重量时而搬得动时而搬不动 | 设计判断，已在正文标明 |
| `reality_phys_measurement_precision` | summary 把 precision 等同于重复性；「永远伴随误差」 | 改为「结果需连同不确定度一并评估；精密度、正确度与准确度不是同一件事」；精密度需**规定条件**（可为重复性/中间精密度/再现性），准确度本身不是可赋值的量；并区分分辨率、偏移与不确定度 | **rp_src_35**（VIM3 2.13/2.15/2.26/2.39） |
| 同上 | 中文里混入英文词 `inspector` | 改为「行政执行与查验」 | — |
| 同上 | 原依赖 NIST 目录页作为证据 | 改为补读 VIM3 四个词条页（`rp_src_35`）；NIST 正文页仍超时，已在 `evidence_and_uncertainty` 明写不引用其评定方法 | 实际抓取结果 |
| `reality_phys_food_preservation` | 「密封加热杀灭罐内微生物」「多数做法多路径更可靠」「脏容器等于取消干燥效果」「任何设定都不应把保存写成可挽救已腐败食物」 | 密封改为「隔绝再污染，不等于杀菌」，并指出条件不成立时密封反而利于厌氧微生物；删除「多路径更可靠」的普遍排序，改为「取决于具体食品与危害」；脏容器降为「多个影响因素之一」；魔法条款改为「作者的设定选择，规则明确一致即可」 | rp_src_23 / rp_src_24 / rp_src_25 |
| `reality_phys_drinking_water_sanitation` | definition 把「安全饮水」与 WHO 的「安全管理的饮水服务」混为一谈；「清澈与安全无关」；「取水距离决定频率」；「任何一端失守」；把取水劳动与疫情写成必然 | 拆为两个概念，后者明写三要素（水源改善、处所内可及、需要时可得）；改为「不能仅凭外观判断」（并保留反向：也不能单凭清澈断定不安全）；改为「影响可行性、提高风险」；改为「水源受污染的风险上升，疫情可能更严重」；性别分工作为「很多社会中常见但差异极大，需按设定」 | rp_src_26 / rp_src_27 / rp_src_28 |

### 7.2 全 32 条的同类风险扫查

同样四类风险逐条看过，实际改写了以下条目（未改的条目已核过，保持原样）：

- **因果绝对化（「决定了 / 必然 / 最致命 / 即」→ 「很大程度上影响 / 往往 / 之一 / 可能」）**：`friction_traction`、`heat_transfer`、`water_cycle`、`river_flood`、`terrain_erosion`、`climate_season`、`soil_fertility`、`crop_rotation`、`ecosystem_flow`、`food_preservation`、`disease_transmission`、`communication_distance`、`shelter_building`、`energy_budget`、`material_strength`、`combustion_fire`、`pressure_fluid`、`road_transport`、`corrosion`、`drinking_water_sanitation`。
- **把技术/制度依赖写成现实定律**：`measurement_precision`（把「精度」的日常义当成计量学定义）、`food_preservation`（把密封当消毒）、`drinking_water_sanitation`（把服务指标当水质），均改回具体条件。
- **无来源支撑的社会结论**：`drinking_water_sanitation` 的性别劳动、「极稳定不公」改为需按设定；`carrying_capacity`、`outbreak_investigation`、`communication_distance` 中带推测性的因果已降为「往往 / 可能」。
- **物理词义与比例**：`gravity_load`（能量与速度的平方关系、平方反比的距离基准、静载与疲劳的界限）、`lever_pulley`、`buoyancy`、`phase_change` 已核过描述无错误；`energy_budget` 修正了一处中英混排与「通常是高估」的措辞。
- **魔法条款一律改为「作者可选」而非「禁止」**：`food_preservation`、`drinking_water_sanitation` 已改；其余条目原本就是「须交代代价」的建议口径，保持。

**持续说明**：本轮只做了针对性复查与措辞校正，并未将任何条目升为 `reviewed_detail`，也不声称已完成科学审核。

## 八、后续待办（不在本次范围）

- 全部 32 条仍为 `needs_detail`。升级到 `reviewed_detail` 须另行逐条回溯来源原文，尤其：重力与载荷的载荷数字、材料强度的承载数字、腐蚀速率、生态与容纳量的量化证据。
- `reality-human`（历史制度、宗教与信仰实践、家庭组织、法律经济）不在本组范围，已由同批其他工作分头采集（本组不写、不占用其 id）。
- 未提交 git，未改动 `data/`、源码或其他组文件。
