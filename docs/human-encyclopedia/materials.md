# 人类生产生活百科 · materials（天然矿物、矿石、燃料与人工材料）

状态：candidate / 收集中。本组为候选素材，**不代表完整人类材料史，不自动加入故事**。全部条目 `review_status=needs_review`，未自升。

- 数据文件：`docs/human-encyclopedia/materials.json`（36 条目／24 条来源记录：22 read + 1 search_only + 1 unavailable；全部条目均为待审候选，未经审核定稿）
- 本文档为人类可读的导读与索引；条目全文（七节细节、来源绑定）以 JSON 为准；JSON 只是**候选素材的当前版本**，全部条目待审，不得当作已定稿的定论性依据引用。
- 编号前缀统一 `materials_`。未改动 `data/`、StoryPackage、其他组目录或源码。

## 一、本组的核心边界（务必先读）

材料条目最容易出的错是把不同层级混为一谈。本组按下列层级严格区分，并在每个条目的 `tags` 与 `definition` 中写明：

| 层级 | 含义 | 本组条目 |
| --- | --- | --- |
| 矿物 mineral | 具特定成分与结构的天然晶质/非晶质物质 | 赤铁矿、磁铁矿、黄铜矿、自然铜、锡石、方铅矿、闪锌矿、石膏、石墨、食盐（兼作调味与食材，故另标 condiment/food） |
| 物料类型（非单一矿物） | 按粒径/成因定义的材料集合，往往是多矿物混合物 | 石英砂（另标 aggregate、industrial_mineral）、黏土（另标 industrial_mineral） |
| 岩石 / 石料 stone | 矿物的集合体，或按用途划分的石材类别 | 石灰石、建筑石材 |
| 矿石 ore | **经济地质概念**：富集到可开采利用程度的岩体 | 铁矿石、铜矿石 |
| 天然资源 natural_resource | 直接取自自然、未加工的材料（与矿物/石料/燃料标签可共存） | 煤、木材（另标加工材料与燃料）、石灰石、建筑石材、铁矿石与铜矿石（另标 ore） |
| 燃料 fuel | 燃烧放热的材料（天然或加工） | 煤、木炭、焦炭 |
| 加工材料 / 合金 processed_material / alloy / metal | 必须经人工工序才能得到的材料 | 木炭、焦炭、铁、生铁、熟铁、钢、铜、锡、铅、青铜、黄铜、玻璃、陶瓷、砖、石灰、石膏胶凝材料、水泥、镀锡铁皮 |

五条必须守住的判断：

1. **钢与铁不是矿藏。** 它们是加工材料；钢是铁碳合金（碳上限约 2%）。矿藏/矿石是它们的原料一侧。
2. **矿物 ≠ 矿床。** 有赤铁矿露头不等于有可采铁矿；矿床是可经济开采获利的富集体，取决于品位、规模、开采与运输成本、市价。
3. **资源量 ≠ 可采储量 ≠ 实际库存。** 本组不给任何产量、储量、品位数字——原因见下节「证据缺口」。
4. **元素天然存在 ≠ 只能靠冶炼获得。** 自然铜、陨铁、自然铅都是天然金属，只是不作为常规工业供材；说「工业供铜/铁来自冶炼」不等于否认自然产出。
5. **现代工业路线 ≠ 历史必经路线。** 高炉—转炉—电解那一套只是近现代形态；块炼法、坩埚法、土法焙烧—熔炼都是真实存在过的替代路径，不能写成「必经」或「唯一」。

## 二、标签用法

实际使用的标签（英文 snake_case，仅用于检索，不是权限或兼容性证明）：

`mineral`(10)、`natural_resource`(18)、`metal`(11)、`ore`(2)、`stone`(2)、`fuel`(4)、`processed_material`(19)、`alloy`(5)、`condiment`(1)、`food`(1)、`aggregate`(1)、`industrial_mineral`(2)

规范给出的其他标签（`tool`、`facility`、`agriculture`、`cooking`、`metalworking`、`textile`、`woodworking`、`transport`）属工具组与本组的下游用途，本组未滥用到材料条目上，以免「材料 ≡ 工艺能力」的误读。

`stone` 属规范允许范围内的扩展标签，用于岩石层级（避免把岩石标成 `mineral`）。`aggregate`、`industrial_mineral` 同理：用于说明石英砂、黏土这类物料集合不是单一矿物，避免「矿物—物料—矿床」三层混用。石英砂与黏土因此**不再带 `mineral` 标签**（它们是物料集合，不是某一固定矿物），与上表「物料类型（非单一矿物）」一行自述一致。

## 三、来源与证据缺口（重要）

本组实际 `read` 了 6 个以上不同的可靠页面，以 Encyclopaedia Britannica 学术条目为主（铁/铜/锡/钢/生铁/熟铁/青铜/黄铜/煤/玻璃/水泥/石灰石/黏土/石膏/石墨/食盐/木炭/木材/砖瓦/陶瓷/矿床），另有 National Geographic Society 教育资源页（矿石概念）。

**未能取得的来源（如实记录）**：

- USGS（美国地质调查局）矿物统计页与矿产品摘要 PDF：多次尝试返回 HTTP 405 人机校验拦截，或 PDF 抽取为二进制乱码，**未取得正文**。`sources` 中以 `access: "unavailable"` 单列一条说明。
- Britannica「Pottery」条目全文被订阅墙拦截，仅取得导语，按 `access: "search_only"` 记录，且**不用于支撑任何工艺细节**。
- 其他失败尝试：Smithsonian（HTTP 403）、Corning 玻璃博物馆（404）、Science Museum（域名解析失败）、Utah 地质调查（连接超时）、Wikipedia（连接超时）。

因此：**本组不填任何产量、储量、品位或价格数字**。温度、配比等参数均按上述已读来源表述，属可复现的工艺/材料学内容；但**不宣称所有科学事实均已可靠验证**——具体矿床是否可采、古代窑温与工艺细节、出土器物的矿料来源，一律标注需实测或存在争论。

**来源计数核对（与 JSON 一致）**：总数 24 = 22 条 `read` + 1 条 `search_only` + 1 条 `unavailable`。其中 `search_only`（Pottery）与 `unavailable`（USGS）**均未被任何条目的 source_ids 引用**：前者虽能读到导言，但导言不能支撑技术细节，已从 clay 与 ceramic 中删除；后者无正文，仅作访问失败记录保留。

## 四、条目索引

| # | 条目 | id | 主要标签 |
| --- | --- | --- | --- |
| 1 | 赤铁矿 | `materials_hematite` | mineral, natural_resource |
| 2 | 磁铁矿 | `materials_magnetite` | mineral, natural_resource |
| 3 | 黄铜矿 | `materials_chalcopyrite` | mineral, natural_resource |
| 4 | 自然铜 | `materials_native_copper` | mineral, natural_resource, metal |
| 5 | 锡石 | `materials_cassiterite` | mineral, natural_resource |
| 6 | 方铅矿 | `materials_galena` | mineral, natural_resource |
| 7 | 闪锌矿 | `materials_sphalerite` | mineral, natural_resource |
| 8 | 铁矿石 | `materials_iron_ore` | ore, natural_resource |
| 9 | 铜矿石 | `materials_copper_ore` | ore, natural_resource |
| 10 | 石英砂 | `materials_quartz_sand` | natural_resource, aggregate, industrial_mineral |
| 11 | 石灰石 | `materials_limestone` | natural_resource, stone |
| 12 | 黏土 | `materials_clay` | natural_resource, industrial_mineral |
| 13 | 石膏 | `materials_gypsum` | mineral, natural_resource |
| 14 | 石墨 | `materials_graphite` | mineral, natural_resource |
| 15 | 建筑石材 | `materials_building_stone` | natural_resource, stone |
| 16 | 食盐 | `materials_salt` | mineral, natural_resource, condiment, food |
| 17 | 煤 | `materials_coal` | natural_resource, fuel |
| 18 | 木炭 | `materials_charcoal` | fuel, processed_material |
| 19 | 焦炭 | `materials_coke` | fuel, processed_material |
| 20 | 铁 | `materials_iron_metal` | metal, processed_material |
| 21 | 生铁 | `materials_pig_iron` | metal, alloy, processed_material |
| 22 | 熟铁 | `materials_wrought_iron` | metal, alloy, processed_material |
| 23 | 钢 | `materials_steel` | metal, alloy, processed_material |
| 24 | 铜 | `materials_copper_metal` | metal, processed_material |
| 25 | 锡 | `materials_tin_metal` | metal, processed_material |
| 26 | 铅 | `materials_lead_metal` | metal, processed_material |
| 27 | 青铜 | `materials_bronze` | metal, alloy, processed_material |
| 28 | 黄铜 | `materials_brass` | metal, alloy, processed_material |
| 29 | 玻璃 | `materials_glass` | processed_material |
| 30 | 陶瓷 | `materials_ceramic` | processed_material |
| 31 | 砖 | `materials_brick` | processed_material |
| 32 | 石灰 | `materials_lime` | processed_material |
| 33 | 石膏胶凝材料 | `materials_plaster` | processed_material |
| 34 | 水泥 | `materials_cement` | processed_material |
| 35 | 木材 | `materials_wood` | natural_resource, processed_material, fuel |
| 36 | 镀锡铁皮 | `materials_tinplate` | processed_material, metal |

## 五、主要生产链（可用于构造剧情中的依赖关系）

- **钢铁链**：铁矿石（赤铁矿/磁铁矿）→ 破碎选矿 → 熔剂（石灰石）+ 还原剂与燃料（木炭 → 焦炭）→ 高炉铁水/生铁 → 炼钢（氧化脱碳）→ 钢；或 生铁 → 搅拌脱碳 → 熟铁 → 锻打成型。
- **铜链**：铜矿石（黄铜矿/氧化矿/自然铜）→ 破碎磨矿 → 浮选 → 熔炼（冰铜）→ 吹炼（粗铜）→ 电解精炼 → 铜。
- **青铜链**：铜 + 锡（锡石冶炼）→ 熔合铸造 → 青铜；瓶颈常是**锡的远距离供应**。
- **黄铜链**：铜 + 锌矿共同还原（可绕过纯锌）→ 黄铜；或 铜 + 精炼锌 → 黄铜。
- **玻璃链**：石英砂 + 石灰石 + 纯碱（助熔）+ 燃料 → 熔制 → 成型 → 退火；铁杂质使玻璃泛绿。
- **建材链**：石灰石 → 煅烧 → 石灰；石灰石 + 黏土 → 煅烧熟料 + 石膏 → 水泥 → 砂浆/混凝土；黏土 → 成型干燥 → 日晒砖 / 烧结砖；石膏 → 煅烧 → 建筑石膏。
- **能源链**：木材 → 木炭（限氧炭化）；煤 → 焦炭（隔绝空气干馏）；两者决定冶金规模上限。

## 六、跨条目的常见误读（写作时可主动纠偏）

1. 铅笔不含铅（石墨 + 黏土）；石墨曾被当作铅与辉钼矿。
2. 黄铜不含金，青铜不等于黄铜，古文献 brass/bronze 常混称。
3. 日晒砖 ≠ 烧结砖；石膏 ≠ 石灰 ≠ 水泥；水泥 ≠ 混凝土。
4. 铁器取代青铜不是性能胜出，而是原料更广布。
5. 锡疫被夸大：合金元素会显著抑制，并非所有锡器必碎。
6. 磁石受热超过居里点（约 580 °C）会失磁性——「魔石」有可检验的物理边界。
7. 玻璃的三种原料缺一不可：只加纯碱则玻璃溶于水，只加砂则熔不动。

## 七、返修记录（主审意见落实，仍全部 needs_review）

本轮按主审意见修订，条目数不变（36 条），未新增条目、未改动其他组文件。逐项对应：

**1. 措辞与计数**
- 删除自述中把本组称作定论性依据的表述，改为「候选素材的当前版本，全部待审」。
- 来源计数核对：24 = 22 `read` + 1 `search_only` + 1 `unavailable`，与 JSON 逐项一致。

**2. 钢：历史工艺与现代工业要求分离**（`materials_steel`）
- `conditions` 拆成两段：前工业条件（木炭/煤供热、坩埚与炉膛耐火度、锻打炉砧、凭火色判碳）与工业规模化条件（约 1600 °C 量级熔炼、转炉/电弧炉吹氧、成分分析与温控、连铸轧制、废钢与合金元素供应），并明确后者是「大批量成分一致」的条件，**不是能否得到钢的前提**；古代无这些设备仍产出了钢。
- `mechanism` 改为四条路线并列：固态渗碳、坩埚熔炼、生铁脱碳、现代转炉/电弧炉吹氧，不再只写「氧化脱碳」。
- 删除「接近钢的性能」表述：古代渗碳钢、坩埚钢在含碳量上就是钢，局限只在成分均匀性、夹杂物与批次一致性。
- 具体起始年代与传播路径改为「仍有争论，不给单一年代断言」。
- 别名去掉泛称「钢铁」（保留「碳钢（常见类型）」「steel」），并在 definition 说明「钢铁」是铁与钢的泛称，作检索词时不等同于本条目。

**3. 生铁别名与关系**（`materials_pig_iron`）
- 别名删除「铸铁（相关但不同）」「铁水」这两项非同义项，只保留「猪铁（传统称呼）」「pig iron」。
- 「铁水（出炉液态）vs 生铁（冷却铸块）」「生铁（中间产品）vs 铸铁（调质后浇铸成品，灰口/白口）」两处关系改写在 `definition` 与 `exceptions` 中，并注明本组未单列铸铁条目、因此不以别名混查。
- `mechanism` 补一句：块炼法可得低碳铁团但得不到生铁，高炉并非唯一路径。

**4. 元素自然存在 ≠ 只能冶炼**（`materials_iron_metal`、`materials_copper_metal`、`materials_lead_metal`、`materials_tin_metal`）
- 明确区分「元素天然存在」（自然铜、陨铁、少量自然铅）与「工业供材主要由冶炼精炼取得」；删除「是提炼产物」式的一刀切表述。
- `iron_metal.mechanism` 补块炼法（不经液态铁水）与陨铁直接锻打两条非高炉路线。
- `copper_metal` 补：早期可直接锤打自然铜、或用木炭低温还原富氧化矿；现代电解只是达到电工级纯度的手段，古代铜器不依赖电解铜。
- 同步修正 `copper_ore`、`chalcopyrite`：把「浮选→冰铜→吹炼→电解」明确标注为**现代工业对硫化矿的常用路线**，不得写成必经流程；补历史路线与「以木炭与土炉即可小规模出铜」。
- `cassiterite`、`tin_metal`：火法精炼标为历史与工业共用手段，电解标为现代高纯工艺。

**5. 矿物分类复核**（`materials_quartz_sand`、`materials_clay`、`materials_salt`）
- 石英砂：去掉会误导的别名「石英」；`definition` 明确它是原料/商品分类、多为多矿物混合物（可含长石、云母、黏土、铁氧化物），不能一概作单一矿物；新增标签 `aggregate`、`industrial_mineral`。
- 黏土：明确它是按粒径与成因定义的**物料集合**（高岭石/伊利石/蒙脱石等均可为主），非固定矿物；去掉「高岭土（特定种类）」别名以免混查；新增 `industrial_mineral`。
- 食盐：`definition` 拆成矿物层（岩盐 halite，有晶形解理杂质）与产品层（经开采提纯分级的商品，可加碘或防结块剂）；别名标注「岩盐（矿物形态）」「海盐（产品）」；`exceptions` 补岩盐/海盐/池盐/井盐来源差异。

**6. search_only 来源的支撑边界**（`materials_clay`、`materials_ceramic`）
- 两者 `source_ids` 中的 `materials_src_britannica_pottery` 已删除：该来源全文被订阅墙拦截，仅有导言，不能支撑烧成温度、釉料或工艺细节。
- 该来源仍保留在 `sources` 中作背景线索记录，`supports` 显式写明「当前无任何条目引用本来源」。
- 校验规则已加入：非 `read` 来源不得被任何条目 `source_ids` 引用，现为 0 违规。

**7. 其余扫查到的同类绝对化表述**
- `materials_iron_ore.mechanism`：拆为「现代工业链」与「历史块炼路线」两条。
- `materials_brick.conditions`：补「烘烧并非获得砌块的唯一途径」（版筑、土坯、草泥抹面）。
- `materials_wood.mechanism`：把「干燥是必经工序」改为「多数木作会干燥，可大幅减少开裂，但非绝对必需」。
- `materials_gypsum.mechanism`：补副产（化学）石膏替代天然石膏的路线。
- 27 条 `evidence_and_uncertainty` 中「……可靠」改为「可复现/按已读来源表述」，「属确定知识」改为「按已读来源表述」，并删除「属材料科学定论」这类以定论代替证据的措辞。

**未做与遗留**
- 未新增任何来源（受限于本轮只能读既有已读页面），因此具体年代、量值仍维持「不给数字 / 需实测」的处理，未补新引证。
- 全部 36 条仍为 `needs_review`，不自升。

## 八、本轮复核记录（内容审查 / 最小修订）

本轮只做残留条件性表述、标签层级、来源有效性与 MD–JSON 一致性的复核，**未扩条目、未新增来源、未改其他组文件或源码**。条目数仍为 36，来源仍为 24（22 `read` + 1 `search_only` + 1 `unavailable`），`review_status` 36/36 均为 `needs_review`。

**已修（修改 ID）**

| 修改对象 | 问题 | 处理 |
| --- | --- | --- |
| `materials_quartz_sand`、`materials_clay` | 标签为 `mineral`，与两份文件自述的「物料类型（非单一矿物）」层级相互矛盾 | 去掉 `mineral`（保留 `natural_resource` + `industrial_mineral`，石英砂另留 `aggregate`），MD 索引与标签计数同步 |
| `materials_coal` | `conditions` 写「用于冶金则**必须**先把煤炼成焦炭」，把近代高炉前提当成冶金普遍前提 | 改为「用于高炉一类大型冶金时通常需先炼成焦炭」，并补木炭长期是主要冶金燃料与还原剂、部分窑炉可直烧煤 |
| `materials_iron_metal` | 摘要「工程上几乎**总是**以含碳合金形式使用」＋「作为工业供材则是提炼产物」一刀切 | 改为「多以含碳的铁基合金形式使用」，并把「作为元素天然存在（陨铁为主，另少量自然铁）」与「作为工业供材主要经冶炼精炼」两种身份分开 |
| `materials_hematite` | 「**必须**在高温下用碳或一氧化碳把氧夺走」把还原剂写死为碳系 | 改为「需要在高温下用碳或一氧化碳还原（或用氢等还原剂）」 |
| `materials_brick` | 「成型后**必须**缓慢干燥」把常规做法写成硬前提 | 改为「通常需缓慢干燥以避免收缩开裂」 |
| `materials_cement` | 「水泥**必须**与砂配成砂浆/混凝土才能形成结构材料」忽略了净浆用途 | 改为「通常需……（也有净浆用于灌浆与粘结等少数用途）」 |
| `materials_tin_metal` | 摘要「几乎**总是**以合金或镀层形式使用」 | 改为「以合金或镀层形式使用」 |
| `materials_building_stone` | 「石材不是不坏材料」字面矛盾 | 改为「石材并非不可损坏」 |
| `materials_native_copper` | 「从来没有成为常规铜来源」绝对化 | 改为「未曾成为常规的大宗铜来源」 |
| `materials_copper_metal` | `related` 文本引用 `natural_copper` 而非本组规范 ID | 改为 `materials_native_copper` |

**核对通过（未改）**

- 钢（`materials_steel`）：`mechanism` 四条路线（固态渗碳 / 坩埚熔炼 / 生铁脱碳 / 现代转炉与电弧炉）并列，`conditions` 前工业条件与现代大批量条件已分开，并明写后者不是「能否得到钢」的前提；别名无「钢铁」泛称。
- 生铁（`materials_pig_iron`）：别名仅「猪铁（传统称呼）」「pig iron」，未把「铸铁」「铁水」当同义词；两者关系写在 `definition` 与 `exceptions`。
- 自然铜与工业供材：`materials_copper_metal` 与 `materials_native_copper` 已分层，未把自然产出当常规供材，也未否认其存在。
- 食盐（`materials_salt`）：`definition` 分矿物层（岩盐 halite）与产品层（食盐商品），别名均带层级标注。
- 来源有效性：`materials_src_britannica_pottery`（`search_only`）与 `materials_src_usgs_nmic`（`unavailable`）均未被任何条目 `source_ids` 引用，非 `read` 来源支撑细节的违规为 0；每条至少含 1 条 `read` 来源。

**仍待证据（如实保留，未靠改写绕过）**

- 本组全部来源仍以 Britannica 与 National Geographic 教育页为主，USGS 官方统计始终未取得正文，故产量、储量、品位、价格数字继续留空。
- 古代钢铁与坩埚钢的起始年代、传播路径；青铜时代锡料产地；早期黄铜是否已用纯锌；古代窑温与砂浆配方——均维持「存在争论 / 需实测」表述，不做定论化收敛。
- 石英砂与黏土去掉 `mineral` 标签只是层级修正，**不构成**对其具体产地适用性的任何结论。
- 本节只说明结构、层级与措辞层面的核对结果，**不等于事实认证**；36 条仍需主审逐条复核。
