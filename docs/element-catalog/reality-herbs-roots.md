# 现实基础库 · 根与根茎类药材（reality-herbs-roots）

对应 [reality-herbs-roots.json](reality-herbs-roots.json)。状态：**候选资料**（`schema_version: 1`、`status: candidate`），全部条目 `review_status: needs_review`、`detail_status: needs_detail`、`knowledge_kind: mixed`。不是用药资料，不是数据库实现，也没有被任何故事包采纳为正典。

> **性质声明（请先读这三行）**
> 1. 这是**游戏与小说的设定 / 史料素材库**，不是用药资料。本文件与 JSON **不含任何剂量、配伍比例、煎煮温度与时长、炮制火候参数、服用方法、疗程、频次、适应症指导**，也不写「可治某病」。
> 2. 每条的 `summary` 与 `details` 至少一处明写「本条为文献与设定资料，不构成医疗建议，不可据此用药」。
> 3. 有毒药材只写**毒性类别与历史教训**（如「含乌头碱类生物碱、误用可致心律紊乱乃至骤停」），**绝不写减毒做法、安全用量或解救方法**。

规范见 [collection-spec.md](collection-spec.md)（第 62—68 行「现实基础库」一节）。本页只做扫读索引、来源与限制说明，**完整内容以 JSON 为准**，此处不复制七节正文。

## 一、实测规模

| 项 | 实测（由 JSON 实时统计） |
|---|---|
| 元素 | **42** |
| 来源 | **54**（`read` 53 / `unavailable` 1 / `search_only` 0） |
| 标签 | 149 个去重标签（含导入端自动追加的 `category:life` 42 次） |
| `details` 覆盖 | **42/42**，七节均非空 |
| `details` 体量 | 每条 946—1600 字，均值 1281，合计约 **5.4 万字** |
| `source_ids` 悬空 | **0**；所有被引用的来源均 `access: read` |
| 实际阅读页面 | **11 个不同站点/语种**：Britannica（英）、美国 NCCIH（政府）、百度百科（中）、iPlant 植物智（中） |

## 二、这个文件在收什么

用户要求的是「现实中药材·根与根茎类」候选资料，约 40 味。因此取的不是「药材清单」，而是**能进入剧情因果的机制**。七节的写作方向固定为：

1. **definition** — 定义与药用部位（并逐条注明植物学部位，见第三节）
2. **mechanism** — 文献所载性味与功用脉络；**可核的部分另起一层**（多为形态、生长、加工、市场机制）
3. **conditions** — 生境、栽培年限、采收季节与产地
4. **exceptions** — 例外与常见误解（同名异物、易混品、伪品）
5. **story_uses** — 社会史与剧情用途（药材市场、行会、贡赋、走方医、囤积与价格战、走私、执法冲突）
6. **historical_scope** — 时代与地域限定、改编边界（含「不得写什么」）
7. **evidence_and_uncertainty** — 证据分层（典籍记载 vs 现代研究 vs 本项目归纳）与不确定性

**反复出现的六条结构性主题**（这是本批最可复用的部分）：

- **加工即分类**：生地黄/熟地黄、白芍/赤芍、干姜/生姜/姜炭、天冬与麦冬——同一原料走两条工序就变成两个药名、两套价签。传统分类的对象不是植物，而是**处理过的成品**。
- **同名异物**：当归（伞形科二十余种 + 五科同名）、天南星（李时珍把「天南星」与「虎掌」合二为一，吴其濬沿袭其误，近代基原不下二十种）、续断（历代注家互相否定）、川贝母（清末仍混乱）、白芍（网络百科曾把该名直接指向有毒的青羊参）。
- **濒危—盗采—执法**：甘草（二级保护、专营与采集证）、肉苁蓉（4 月即盗采高峰、与执法者正面冲突）、天麻（IUCN 易危 + CITES 附录Ⅱ + 二级）、川贝母（IUCN 近危）、黄连（二级）。
- **价格周期**：知母（来源直述「影响生产的主要因素就是价位」）、桔梗（「周期性强，所以价格波动较大」）、当归（抽苔率 30%—50%、个别 70%）、黄芩（四年后枯心、八年后全废）。
- **毒性与致命误认**：附子/川乌（乌头碱类、古代亦作箭毒「射罔」）、半夏、天南星、雷公藤（「断肠草」这一俗称在多地指向不同植物）。
- **传说如何制造商品**：何首乌（唐代李翱《何首乌传》＋一千年后的 MHRA 肝损害报告与标签规定）、人参（Panax 释为「包治百病」属词源传说）、甘草（辛弃疾以「甘国老」讽刺逢迎之臣）。

## 三、标签口径（重要）

- `kind:herb` 42/42。
- **`tradition` 一条只取一个**：以中医脉络为主的用 `tradition:eastern`（**37 条**）；以植物、商品、生态或贸易为主要框架、药用只是其中一面的用 `tradition:real_world`（**5 条**：甘草、大黄、生姜、山药、肉苁蓉）。
- **`part` 只用 `part:root` 或 `part:rhizome`**（题目规定）。实测 `part:root` 31、`part:rhizome` 11，**互斥，无一条同时带两个**。
- 另用 `habitat:` / `trait:` / `role:` / `trade:` 作检索面。
- **不手写 `genre:` / `category:`**——`category:life` 与 `genre:real_world` 由导入端按 `category`、`genres` 字段自动追加（已验证：库内 `category:life` 42 次）。

> **部位口径的一个必要说明**：题目要求部位标签统一为 `part:root` / `part:rhizome`，但植物学上有几味的药用部位并非根或根状茎——**半夏、天南星（块茎）、天麻（块茎）、川贝母（鳞茎）、肉苁蓉（肉质茎）、大黄（根与根状茎兼有）**。本文件一律在 `definition` 与 `exceptions` 内**明确写出「植物学上是 X，不是根」**，标签则按采集口径归入根茎类。**这是采集口径，不是植物学结论**，须主审确认是否接受。

## 四、扫读表

`part` 列取标签；`trad` 列取 tradition 标签。

| ID | 名称 | part | trad | 一句话要点 |
|---|---|---|---|---|
| `herb_root_ginseng` | 人参 | root | eastern | 贵重药材的原型：5—7 年栽培、按年限分档、美洲参经香港转口 |
| `herb_root_codonopsis` | 党参 | root | eastern | 「廉价替代品」如何自成道地体系（贡潞/奎潞/秃潞） |
| `herb_root_astragalus` | 黄芪 | root | eastern | 根形记录土层（鞭竿芪 vs 鸡爪形）；野生资源急剧减少 |
| `herb_root_licorice` | 甘草 | root | real_world | 药/食/烟/化工同抢一原料；二级保护＋专营＋采集证；「国老」政治隐喻 |
| `herb_root_danggui` | 当归 | root | eastern | 同名异物最全（跨五科）；抽苔即废；归头/归身/归尾分价 |
| `herb_root_chuanxiong` | 川芎 | rhizome | eastern | 京芎/川芎/台芎/抚芎按产地分等；山区育苗—平原栽种的两地分工 |
| `herb_root_baishao` | 白芍 | root | eastern | 加工即定义；「白芍」俗名曾被指向有毒的青羊参 |
| `herb_root_chishao` | 赤芍 | root | eastern | 同源双品：不水煮去皮者为赤芍；天气即品相 |
| `herb_root_rehmannia_raw` | 生地黄 | root | eastern | 鲜/生/熟三态同源异名；贡品与外销史 |
| `herb_root_rehmannia_prepared` | 熟地黄 | root | eastern | 蒸制把「清」改成「补」；作坊即权力中心 |
| `herb_root_atractylodes_macrocephala` | 白术 | rhizome | eastern | 道地载体；两年周期；燃料决定品级 |
| `herb_root_atractylodes_lancea` | 苍术 | rhizome | eastern | 撞皮/火燎决定外观等级；南北两条价线；「辟山川瘴疠」 |
| `herb_root_yam` | 山药 | root | real_world | 主粮＋仪式中心（西非/新几内亚）；真正的薯蓣≠甘薯 |
| `herb_root_aconite_zi` | **附子** | root | eastern | **剧毒（乌头碱类）**；一物七名按形定价；射罔 |
| `herb_root_aconite_mu` | **川乌** | root | eastern | 母根；同株异位；箭毒与土农药 |
| `herb_root_dried_ginger` | 干姜 | rhizome | eastern | 干姜/姜炭分档；与生姜共用原料的价格跷跷板 |
| `herb_root_fresh_ginger` | 生姜 | rhizome | real_world | 香料航线（1 世纪入地中海、1547 出圣地亚哥）；无性繁殖的种源脆弱 |
| `herb_root_pinellia` | **半夏** | root | eastern | **有毒**；数十跨省俗名；块茎易被误当芋头 |
| `herb_root_arisaema` | **天南星** | root | eastern | **有毒**；李时珍把「天南星」与「虎掌」合二为一，吴其濬沿袭其误 |
| `herb_root_tripterygium` | **雷公藤** | root | eastern | **有大毒、高致命**；「断肠草」多地指涉不同植物 |
| `herb_root_heshouwu` | 何首乌 | root | eastern | 一篇唐传造一个品牌；人形根骗局；MHRA 7 例肝损害报告 |
| `herb_root_coptis` | 黄连 | rhizome | eastern | 唐代已比较蜀道与江东货；宋代按州附图；二级保护 |
| `herb_root_scutellaria` | 黄芩 | root | eastern | 四年后枯心、八年后全废——与「越陈越贵」相反 |
| `herb_root_rheum` | 大黄 | rhizome | real_world | 商品形态学最发达（蛋吉/狗头/马蹄/锦纹/星点）；西汉已外销 |
| `herb_root_salvia` | 丹参 | root | eastern | 别名极多且跨科撞名；「红即血」的联想经济 |
| `herb_root_scrophularia` | 玄参 | root | eastern | 蒸制转黑；文献对它褒贬并存（含直接的批评） |
| `herb_root_ophiopogon` | 麦冬 | root | eastern | 冲积阶地依赖；同一属兼药材/地被/观赏 |
| `herb_root_asparagus` | 天冬 | root | eastern | 名称层累（虋冬→大当门根→天冬）；半透明即等级 |
| `herb_root_gastrodia` | 天麻 | root | eastern | 无光合、靠蜜环菌；繁殖机制到 1981 年才被写清；IUCN 易危＋CITESⅡ |
| `herb_root_pueraria` | 葛根 | root | eastern | 淀粉＝救荒粮；本草内部「分寸之争」 |
| `herb_root_bupleurum` | 柴胡 | root | eastern | 北/南柴胡；旧说自带严格条件（「四日后方可用」） |
| `herb_root_saposhnikovia` | 防风 | root | eastern | 「屏风者，防风隐语也」；根头叶基与环纹是防伪证据 |
| `herb_root_notopterygium` | 羌活 | rhizome | eastern | 名始载于「独活」项下——一名从另一名析出 |
| `herb_root_angelica_pubescens` | 独活 | root | eastern | 名字被借走又被借出；双向替代链 |
| `herb_root_angelica_dahurica` | 白芷 | root | eastern | 抽苔即报废、干燥不可中断——两个不可逆；杭白芷的药材名是「川白芷」 |
| `herb_root_platycodon` | 桔梗 | root | eastern | 「一株一苗」决定根形；药食两用；价格周期性强 |
| `herb_root_achyranthes` | **牛膝**（未完成） | root | eastern | **证据缺口**：直接来源为零，仅川牛膝旁证 |
| `herb_root_dipsacus` | 续断 | root | eastern | 用一千年写成的打假史（雷公炮炙论→唐本草→本草图经→纲目） |
| `herb_root_morinda` | 巴戟天 | root | eastern | 肠状缢缩＝形态防伪；扦插 5—7 年故与木薯生姜间种 |
| `herb_root_cistanche` | 肉苁蓉 | rhizome | real_world | 寄生梭梭、每千株仅 7 株；4 月盗采高峰与执法冲突；西域贡品 |
| `herb_root_fritillaria` | 川贝母 | rhizome | eastern | 鳞茎（非根）；基原从 4 种加到 6 种用了 33 年；清末仍混乱；IUCN 近危 |
| `herb_root_anemarrhena` | 知母 | rhizome | eastern | 两年滞后期＋价格周期；安国/亳州两大基地 |

## 五、按风险与保护状态分组（写作时的快速索引）

**有毒（`trait:toxic`，5 条）**：附子、川乌、半夏、天南星、雷公藤。
> 写法限制：只作定性风险与历史教训；**不写减毒做法、安全用量、解救方法**；不得让角色「少量尝试」而无不可逆后果。

**濒危 / 受保护（`trait:conservation_protected`、`trait:endangered`、`trait:endangered_near_threatened`，4 条）**：甘草（国家二级）、黄连（国家二级）、天麻（IUCN 易危 + CITES 附录Ⅱ + 国家二级）、川贝母（IUCN 近危）、肉苁蓉（濒危 + 采集证制度）。
> 写法限制：一律写明**现代交易受法律与公约禁止或受严格许可约束**，属**历史与伦理问题条目**；**不写获取或使用方式**。

**含明确监管/安全事件（2 条）**：何首乌（MHRA 7 例肝损害报告、2014 年标签要求）、附子/川乌（受管制的毒性药材）。
**含明确掺假—公共卫生事件（1 条）**：姜黄——本批实际读到的 Britannica 条目记有孟加拉国 30 余年以铬酸铅染色的完整链条；但**姜黄本身不属于「根与根茎类」的题目范围**（其为根状茎，然本批 42 味已定，姜黄仅作为 `herb_root_src_17` 的方法论旁证，未列为元素）。**这一点须主审确认**：是否要把该来源保留在 sources 中（当前状态：已读、已登记、未被任何元素引用）。

## 六、来源与方法

**实际检索并读到正文的页面（11 个站点/语种，共 54 条来源登记，其中 53 条 `read`、1 条 `unavailable`）**：

| 站点 | 语种 | 条数 | 用途 |
|---|---|---|---|
| Britannica | 英 | 13（`_01`,`_03`,`_05`,`_09`,`_10`,`_15`,`_17`,`_18`,`_19`,`_20`,`_26`,`_30`,`_36`） | 植物学、贸易史、药典制度、掺假事件、根状茎定义 |
| 美国 NCCIH（NIH） | 英 | 2（`_02`,`_07`） | 红参/白参为同物异法、甘草糖替代、甘草甜素风险类别 |
| 百度百科 | 中 | 38 | 产地、栽培、商品规格、史料引文、基原考证、保护状态 |
| iPlant 植物智 | 中 | 1（`_54`，**正文未取到 → unavailable**） | 曾拟用于名—学名核对，失败后零引用 |

**抓取失败如实记录**：`herb_root_src_54`（iPlant 牛膝页）页面可达但正文未抽取，仅得目录骨架。已标 `access: unavailable` 并**从所有元素的 `source_ids` 中移除**，因此「牛膝」条目成为本批**唯一未完成条目**。

**未读到 / 未采用的页面（不登记为来源，不计入 54）**：Wikipedia（连接超时）、WHO 传统医学实况报道（连接超时）、CITES 名录页（Cloudflare 403）、Kew 药用植物页（404）、Britannica Aconitum/Astragalus 正条（404）、百度百科「苍术」早期路径（403）、「牛膝」「续断」多义项页（404/骨架）。**这些均未用于任何陈述**。

**证据分层规矩**（每条 `evidence_and_uncertainty` 均按此写）：
- 「来源支持（可核）」→ 只放典籍原文、形态、产地、制度、事件等可核对项。
- 「本项目归纳」→ 所有社会机制推演（贡赋、囤积、走私、行会、认知鸿沟等）明确标为推演。
- 「不确定」→ 比例、规模、种级归属、各家所指物种等未核项逐条列出。

## 七、临时库导入验证（未改动的 `app.encyclopedia`）

用**未修改的** `app.encyclopedia.import_file` 在系统临时目录建一次性库（`tempfile.mkdtemp`，非 `data/`）：

```
=== 0. adapter 识别（不指定 adapter）===
detect_adapter -> human-encyclopedia

=== 1. 首次导入 ===
adapter=human-encyclopedia elements=42 sources=54 element_versions=42 idempotent=False
unresolved_relations = 0
ambiguous_relations  = 0
shared_element_ids   = []

=== 2. 复导幂等 ===
idempotent=True element_versions=0 unchanged_elements=42 batch_id_same=True

=== 3. 标签可检索 ===
kind:herb -> 42
  tradition:eastern                  -> 37
  tradition:real_world               -> 5
  part:root                          -> 31
  part:rhizome                       -> 11
  trait:toxic                        -> 5
  trait:conservation_protected       -> 2
  trait:endangered                   -> 1
  trade:conservation_regulated       -> 6
  role:tonic_tradition               -> 10
  trait:naming_confusion             -> 6
  part:root AND part:rhizome -> 0
  text=人参 -> 2 ['肉苁蓉', '人参']
  text=川贝 -> 1 ['川贝母']
  list_tags total distinct tags = 149
  top10: [('category:life', 42), ('kind:herb', 42), ('tradition:eastern', 37),
          ('trade:bulk_commodity', 34), ('part:root', 31), ('trade:regional_appellation', 24),
          ('part:rhizome', 11), ('role:tonic_tradition', 10), ('trait:processing_defined', 7),
          ('trade:conservation_regulated', 6)]

=== 4. 七节非空（从库中读回）===
checked: 42 problems: []

=== 5. 状态字段 ===
review_status: {'needs_review': 42}
detail_status: {'needs_detail': 42}
```

**结论**：adapter 自动识别为 `human-encyclopedia`（因每条都有 `tags`）；导入 42 条、54 来源；**未解析关联 0、歧义关联 0**（本批不设 `related_ids` / `related_catalog_ids`，故必然为零，这是设计选择而非通过检查）；复导幂等（第二次 `element_versions=0`、`unchanged_elements=42`、`batch_id` 相同）；标签可检索且 `part:root` 与 `part:rhizome` 互斥；七节从库中读回全部非空、42 条全部挂有来源。

> 验证脚本另跑了一遍**红线扫描**（正则匹配 `数字+克/两/钱/枚`、`煎服`、`每日…次`、`疗程`、`适应症`），命中 3 处均为**「不得写任何用量、服用方法…」这类禁令句**本身，已逐句核对确认为限制语而非建议语。

## 八、须主审裁定的点

1. **`part` 标签的植物学妥协**（最重要）。六味药用部位并非根或根状茎（半夏、天南星、天麻 = 块茎；川贝母 = 鳞茎；肉苁蓉 = 肉质茎；大黄 = 根兼根状茎）。当前按采集口径归入 `part:root` / `part:rhizome`，并在正文逐条注明。**是否接受这一妥协，还是要求新增 `part:tuber` / `part:bulb` / `part:stem` 等标签？** 后者会违反题目「统一 part:root 或 part:rhizome」的字面要求。
2. **「牛膝」条目未完成**。直接来源为零（iPlant 页正文未抽取），仅能借川牛膝旁证。建议：**补来源重写，或暂时剔除**。当前保留是因为它已被写入并在七节中如实自陈缺口。
3. **姜黄的处理**。`herb_root_src_17`（Britannica Turmeric）是本次唯一读到完整「掺假—公共卫生」因果链的来源，但姜黄不在题目给定的 40 味之列。当前状态：来源登记为 `read` 但**零引用**。**是保留作方法论旁证，还是按「零引用来源应删除」的规矩清掉？**
4. **tradition 标签的两套口径并存**。严格说，42 味全部落在中医脉络内，`tradition:real_world` 与本目录的其它 5 味（甘草、大黄、生姜、山药、肉苁蓉）之所以取 real_world，是因为我把「以植物/商品/生态/贸易为主要框架」当作判据。**这是本项目自定的口径，不是规范里的既有规定**，需主审确认或改判。
5. **`knowledge_kind` 全部为 `mixed`**。理由是每条都同时含「文献性味表述（historical/belief）」与「植物学或经济事实（empirical）」。**是否要求拆分出部分 `historical` 条目？**
6. **芍药类的来源薄弱**。白芍、赤芍两味的性味与加工分野属中医体系内通行说法，本文件**未取得专门的原典或药典来源**（Britannica 芍药属条目只给植物学），已在两条的 `evidence_and_uncertainty` 中标为待补。**是否接受以「待补」状态入候选？**
7. **`herb_root_src_23` 的保护级别口径冲突**。该页称黄芪为「国家三级保护植物」，与 2021 年名录的现行二分法不一致。本文件已在条目内标注「须以现行名录为准」，**但未修改来源原文**。
8. **`related_catalog_ids` 全为空**。与 `reality-human`（113 个引用）不同，本批**刻意不建关联**，因为药材与既有 `society`/`eastern` 条目之间尚无可确证的一对一对应。**是否要求补关联？**
