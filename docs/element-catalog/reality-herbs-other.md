# 现实基础库·中药材专题（皮木脂、菌藻、矿物与动物类）

> **状态：候选资料，不是数据库，不是任何故事包已采纳的正典。**
> 本文件与 `reality-herbs-other.json` 同时交付，两者内容一致（JSON 为结构化字段，本文件便于扫读与审阅）。未改任何其他文件，未建实际库，未改 CLI。

---

## 一、这份文件要解决什么

第一批已交付的四个现实分区（`reality-physical` 32 条、`reality-human` 31 条）与四个虚构题材组（eastern / western / society / steam-horror）覆盖了制度、物理机制、社会史，但缺一类很具体的素材：**药材这个对象本身**——一种东西怎么被认定、被分级、被掺假、被替代、被禁、被写成故事里的道具。

本文件补的就是这一层，共 **37 条**，按四条线成组：

| 组 | 条数 | 内容 |
|---|---|---|
| 皮与木 | 7 | 肉桂、杜仲、黄柏、牡丹皮、地骨皮、桑白皮、苦楝皮 |
| 树脂与胶 | 5 | 乳香、没药、阿魏、血竭、松脂 |
| 菌藻 | 6 | 灵芝、茯苓、猪苓、冬虫夏草、海藻、昆布 |
| 矿物 | 7 | 朱砂、雄黄、石膏、滑石、龙骨、磁石、代赭石 |
| 动物与动物制品 | 12 | 珍珠、牡蛎、蝉蜕、僵蚕、地龙、蛤蚧、鹿茸、阿胶，以及四条**纯制度条目**：穿山甲、熊胆、虎骨、麝香 |

> 合计：7 + 5 + 6 + 7 + 12 = 37。

---

## 二、三条安全红线（本文件是怎么执行的）

这一节是整个文件的“防火墙”，先读它。

### 2.1 只做设定与史料，不做医疗内容

**不写**：剂量、配伍比例、煎煮温度与时长、炮制火候参数、服用方法、疗程、频次、适应症指导、`可治某病`。

**只写**：「汉代文献把它归为……一类」「方书把它记作『温』」「传统认为它属『补』一类」——即把传统医学当作**文献现象**记录，而不当作现实效力。

机械检查：37/37 条的 `evidence_and_uncertainty` **首句**均为固定句：

> 本条为文献与设定资料，不构成医疗建议，不可据此用药。

并对全文做了禁忌词扫描（剂量/煎/煮/服用/疗程/频次/主治/可治/减毒/解毒/安全用量/配伍比例 等）—— 所有命中均为**否定式与声明式表述**（如「不写减毒」「不给剂量」），无一例为指导。

### 2.2 矿物与重金属类：只写毒性后果与历史教训

**朱砂**与**雄黄**两条是本文件最严的一条线。具体做法：

- 写**毒性后果**：汞可经吸入蒸气、摄入可溶化合物或经皮肤吸收而中毒；含朱砂的中成药过量服用致汞中毒已有实例（尿频尿急、尿汞升高、神情呆滞等）。
- 写**历史教训**：毒性很早就被认识，而主要用途曾是医疗；从新石器彩陶到炼丹到中成药，同一物质被用了几千年。
- **不写**减毒、炮制去毒、水飞、安全用量、解救方法。`historical_scope` 里明确写：「**绝对不得**写任何减毒、炮制去毒、安全用量、解毒或救治方法」。

雄黄另有一个可核的物理事实值得单记：**长期见光会自行崩解为雌黄**，所以它雕的摆件会自己坏——这是本文件里最干净的「不需要虚构的悲剧素材」。

### 2.3 动物类：只作历史、伦理与制度问题条目

穿山甲、熊胆、虎骨、麝香四条，标题里就带“仅存为制度条目”。写法：

- **只写**：保护等级（IUCN）、国际公约（CITES 附录一名录与商业贸易禁止）、致危原因、伦理争议、圈养与养殖的问题。
- **不写**：获取、加工、炮制、配伍、服用、使用方式。一条也不写。
- 另：**犀角**本应同列，但本组拟定引用的两个页面均抓取失败（WWF 物种页 403、英文百科条目 404），因此**未设犀角独立条目**，只在虎骨条目内以旁注说明缺口，不引用其内容。这是缺口，不是省略。

### 2.4 菌藻类：真菌不是植物

灵芝、茯苓、猪苓、冬虫夏草、僵蚕五条均在 `definition` 里明写：真菌界独立于植物界与动物界，无叶绿素、以菌丝体在体外消化有机物后吸收。

`kind:herb` 对这些条目**仅为检索口径**（按「可采集的静止生长物」成组），**不是分类学断言**。海藻、昆布两条另声明藻类也不是一个自然分类群。

---

## 三、字段与标签口径

### 3.1 字段

每条：`id`（前缀 `herb_other_`）、`name`、`aliases`、`summary`、`category`、`tags`、`details`（七节，均字符串且非空）、`source_ids`、`knowledge_kind`、`review_status`（全为 `needs_review`）、`detail_status`（全为 `needs_detail`）。

七节固定为 `definition` / `mechanism` / `conditions` / `exceptions` / `story_uses` / `historical_scope` / `evidence_and_uncertainty`，与 `app/encyclopedia.py` 的 `DETAIL_SECTIONS` 逐字一致。

### 3.2 `category` 划分依据（用户要求说明）

`category` 只用了两个值，划分依据是「**该条目的叙事主体是一个还在生长的活物，还是一个被取下来的物件**」：

| 值 | 条数 | 判定 |
|---|---|---|
| `life` | 14 | 叙事主体是**植株或生物本身**：肉桂（树）、杜仲（树）、黄柏（树）、牡丹（花＋根）、地骨皮（枸杞）、桑白皮（桑）、苦楝皮（楝）、灵芝、茯苓、猪苓、冬虫夏草（真菌＋蜱）、海藻、昆布 |
| `item` | 23 | 叙事主体是**可入库、可交易、可储存的物件**：树脂类全部（乳香、没药、阿魏、血竭、松脂）、矿物类全部（朱砂、雄黄、石膏、滑石、龙骨、磁石、代赭石）、动物制品类全部（珍珠、牡蛎壳、蝉蜕、僵蚕、地龙、蛤蚧、鹿茸、阿胶、穿山甲、熊胆、虎骨、麝香） |

**边界例（容易争议处，逐个说明）**：

- **苦楝皮**：树是活的，但条的叙事主体是「剥下来就有毒的那块皮」与它的可及性风险，故 `life`（它与植物体的生命史绑得太紧，不宜当成商品）。
- **僵蚕**：家蚕已完全驯化（野外不存在），条的叙事主体是「被真菌感染后僵死的全体」，属死亡后的物，故 `item`。
- **地龙**：蚯蚓是活的，但条的叙事是「捉了就死」的活体原料与土壤生态功能，故 `life`（它的生态价值就在“活着”这件事上）。
- **鹿茸**：鹿角是可再生器官，但条的叙事主体是“取下来的那一截”与它的时间窗，故 `item`。
- **珍珠 / 牡蛎壳**：都是动物产物，但一个是体内结核、一个是壳，都是物件，故 `item`（牡蛎的**动物**本身归 `reality-physical` 与已有的海洋生物条目，不在本条）。

### 3.3 `tradition` 划分依据（用户要求说明）

只用了两个值，口径是「**该条的主干史料落在哪一传统里**」，不是「这个物体在哪里有」：

| 值 | 条数 | 口径 |
|---|---|---|
| `tradition:eastern` | 35 | 主干史料、商品体系与写作价值主要来自汉文本草与中药材商品传统 |
| `tradition:real_world` | 2 | 主干史料来自**非汉文传统**（乳香、没药属近东—地中海—欧洲脉络） |

**为何不全用 `real_world`**：本目录的 `reality-physical` 与 `reality-human` 两分区统一用 genres `real_world`，但它们的 `tags` 里**不带** tradition 标签。本文件是**药材专题**，药材的“传统归属”本身就是一个有意义的检索维度（同一个物体在汉文传统与地中海传统里是两套话语），所以保留了 `tradition:` 前缀，并在 `mechanism` 一节里逐条说明两套话语的边界。这是一个**待主审决定的点**（见第六节）。

**边界例**：

- **肉桂、血竭、松脂**：同一个物体在两套传统里都有，但主干史料分居汉文与欧洲，且两者**不可互证**。肉桂取 `eastern`（汉文本草与东亚产区为主干），在 `mechanism` 里另写香料线。
- **乳香、没药**：汉文本草里也有（熏陆香、末药），但本组取得的**可读来源只有英文百科**，因此主干史料归 `real_world`，并在条内明写“汉文一系的源流未取得来源”。
- **灵芝、冬虫夏草**：虽然现代国际市场很大，但主干史料是汉文文献与道教，故 `eastern`。

### 3.4 其他标签

- `kind:`：`herb` 18 / `mineral` 6 / `animal_product` 13（每条恰一个）。
- `part:`：`bark` 3、`root_bark` 4、`resin` 5、`sclerotium` 2、`fruiting_body` 1、`thallus` 2、`ore` 6、`shell` 1、`scale` 1、`gallbladder` 1、`antler` 1、`hide` 1、`bone` 1、`exuvia` 1、`infected_larva` 1、`concretion` 1、`gland_secretion` 1、`whole_body` 2、`fungus_insect_complex` 1。
- `trait:`：`toxic` 3（朱砂、雄黄、苦楝皮）、`heavy_metal` 1、`arsenic` 1、`endangered` 3、`trade_banned` 2、`ethically_contested` 4、`counterfeit_prone` 5 等。
- `role:` / `trade:`：检索用，如 `role:medicine_stock` 30、`role:conservation_case` 4、`role:ritual_material` 5、`trade:long_distance` 6、`trade:regional` 14。
- **不手写 `genre:` / `category:`**：这两个前缀由 `app/encyclopedia.py` 在导入时自动追加（实测已生成 `category:item` 等）。

---

## 四、来源与证据分层

### 4.1 实际读取的页面（48 条来源登记，其中 `read` **39**、`unavailable` **9**）

**已读（access=read）—— 39 条**，其中可分三档：

| 档次 | 代表来源 | 可支撑什么 |
|---|---|---|
| 完整正文 | Britannica 的 cinnabar / mercury / realgar / gypsum / talc / hematite / magnetite / fungus / Ganoderma / Cordyceps / kelp / pearl / oyster / cicada / earthworm / gecko / antler / donkey / pangolin / rosin / frankincense / myrrh / cinnamon / mulberry / TCM；WWF 的 CITES / tiger | 矿物学、生物学、贸易史、保护等级 |
| 中文百科（选段） | 辰砂、杜仲、黄柏、牡丹皮、茯苓、阿魏、熊胆 | 基质、产地、采收、性状、历史应用、伪品类别 |
| **摘要/导言级** | `hro_src_britannica_wolfberry`（Quick Summary）、`hro_src_baike_zhuling`（导言） | **只能支撑两三句，不能支撑细节** |

**抓取失败（access=unavailable）—— 9 条，均零引用**（如实登记，不当已读）：

| id | 页面 | 失败原因 |
|---|---|---|
| `hro_src_fail_wikipedia_cinnabar` | Wikipedia — Cinnabar | 请求超时 |
| `hro_src_fail_britannica_cites` | Britannica — CITES | HTTP 404（路径不存在） |
| `hro_src_fail_wwf_rhino` | WWF — Rhino | HTTP 403（人机验证拦截） |
| `hro_src_fail_britannica_rhino` | Britannica — Rhinoceros | HTTP 404 |
| `hro_src_fail_baike_xuejie` | 中文百科 — 血竭 | HTTP 403 |
| `hro_src_fail_baike_kulianpi` | 中文百科 — 苦楝皮 | HTTP 403 |
| `hro_src_fail_baike_longgu` | 中文百科 — 龙骨 | HTTP 404 |
| `hro_src_fail_britannica_asafoetida` | Britannica — Asafoetida | HTTP 404（topic 与 plant 两路径） |
| `hro_src_fail_britannica_silkworm_bombyx` | Britannica — Melia azedarach | HTTP 404 |


> 失败的后果是实质性的：**苦楝皮与麝香两条 `source_ids` 为空**，正文全部标为“本项目据一般文献常识的归纳，未经来源核实”。这不是编造，而是诚实标注的缺口。

### 4.2 三层证据（每条都分开写）

1. **可核事实**：矿物成分与硬度、生物分类与生活史、贸易禁令与保护等级——有 `source_ids` 支撑。
2. **文献记述**：性味、归经、主治词群、古代用法——**只作为历史记载转述**，`source_ids` 只支撑“文献里确实这么写”，不支撑其效力。
3. **本项目推演**：行会验货、贡赋的生态代价、珠户的债、蚕种垄断——在每个 `evidence_and_uncertainty` 末尾以「设计归纳」或「本项目推演」标记。

---

## 五、验证（用未修改的 `app.encyclopedia.import_file`）

在 `temp://scratch/verify_db/verify.sqlite3`（临时库，**不碰 `data/`**）上执行，全部通过：

```
=== import reality-herbs-other ===
namespace   reality-herbs-other
adapter     human-encyclopedia
elements    37
element_versions_written  37
sources     48
source_versions_written  48
relations   0
idempotent  false

=== 第二次导入（幂等） ===
idempotent = True

=== 同库导入同级 reality-physical（验证命名空间不撞） ===
ns=reality-physical  elements=32  idempotent=False
```

检索抽查（同一临时库）：

```
tags_all=[kind:mineral]           → 6 条（朱砂、石膏、磁石、代赭石、雄黄、滑石）
text=“朱砂”                       → 1 条（herb_other_cinnabar）
tags_all=[role:conservation_case] → 4 条（穿山甲、熊胆、虎骨、麝香）
```

结构自检（37/37 全过）：id 前缀、id/name 唯一、14 个必填字段非空、七节齐且非空、无多余分节、review_status/detail_status 值正确、`kind:` 与 `tradition:` 各恰一个、无 `genre:`/`category:` 手写、所有 `source_ids` 均在本文件 sources 内且均 `access=read`。

---

## 六、待裁定点

这些是该由主审决定、我不应自行定调的：

1. **`category` 只用 life/item，未用 place/economy 等**。一条药材完全可以被当作 `economy`（商品链）或 `place`（产区）来写。当前选择「活物 vs 物件」的划分，优点是直观，缺点是与已有四个虚构组里 `item` 包含“资源”与 `life` 包含“物种”的惯例**略有偏差**（本文件的 `item` 更偏“商品”）。需确认是否接受。
2. **`tradition:real_world` 只有两条，且两分区惯例是「不带 tradition 标签」**。本文件引入了 tradition 维度以区分汉文与地中海两套话语，但这与 `reality-physical` / `reality-human` 的做法不一致。是否统一，请裁定。
3. **四条制度条目（穿山甲、熊胆、虎骨、麝香）算不算“元素”**。它们在 `elements` 数组里，但没有可用内容，只有制度与伦理内容。若未来 schema 要求每条都能作为世界内物件使用，这四条可能需要移到其他分区。
4. **苦楝皮与麝香两条 `source_ids` 为空**。是否接受零来源条目入库？（当前已可以导入，`source_ids` 为空只是缺引用，不违反 schema。）
5. **犀角条目缺失**。拟取的两个来源均失败（403/404），因此未设条。是否要补取一次，或直接放弃？
6. **`knowledge_kind` 分布**：`mixed` 30 / `historical` 7 / `empirical` **0**。这与 `reality-physical`（empirical 25）和 `reality-human`（empirical **0**）都不同。药材本质上是“自然物＋文献用法”二合一，因此尽为 `mixed` 是口径选择而非缺陷；但若主审要求每条都能归到单一类型，则需重新划分。
7. **本目录未修改 `collection-spec.md` 与 `README.md`**。是否要把本文件登记进 `README.md` 的组清单与统计表？（按任务约束，本次未改其他文件。）
8. **汉文本草一系的全面缺失**。本组没有取得任何一手本草原文（《本草纲目》《神农本草经》等），所有“性味、归经、主治”均为**二手概括**。若后续要做内容层主审，这一层需优先补源。

---

## 七、逐条索引

| id | 名称 | 类别 | 核心事实来源 |
|---|---|---|---|
| `herb_other_cinnamon_bark` | 肉桂（桂皮） | life | Britannica cinnamon |
| `herb_other_eucommia_bark` | 杜仲 | life | 中文百科 杜仲 |
| `herb_other_phellodendron_bark` | 黄柏（黄檗） | life | 中文百科 黄柏 |
| `herb_other_moutan_bark` | 牡丹皮 | life | 中文百科 牡丹皮 |
| `herb_other_wolfberry_root_bark` | 地骨皮 | life | Britannica wolfberry（摘要级） |
| `herb_other_mulberry_root_bark` | 桑白皮 | life | Britannica mulberry |
| `herb_other_melia_root_bark` | 苦楝皮 | life | **无（抓取均失败）** |
| `herb_other_frankincense` | 乳香 | item | Britannica frankincense |
| `herb_other_myrrh` | 没药 | item | Britannica myrrh |
| `herb_other_asafoetida` | 阿魏 | item | 中文百科 阿魏 |
| `herb_other_dragons_blood` | 血竭 | item | Britannica dragon's blood |
| `herb_other_pine_rosin` | 松脂 | item | Britannica rosin |
| `herb_other_ganoderma` | 灵芝 | life | Britannica Ganoderma + fungus |
| `herb_other_fuling` | 茯苓 | life | 中文百科 茯苓 + Britannica fungus |
| `herb_other_zhuling` | 猪苓 | life | 中文百科 猪苓（导言级） |
| `herb_other_ophiocordyceps` | 冬虫夏草 | life | Britannica Cordyceps |
| `herb_other_seaweed` | 海藻 | life | Britannica kelp |
| `herb_other_kelp` | 昆布 | life | Britannica kelp |
| `herb_other_cinnabar` | 朱砂 | item | Britannica cinnabar + mercury；中文百科 辰砂 |
| `herb_other_realgar` | 雄黄 | item | Britannica realgar |
| `herb_other_gypsum` | 石膏 | item | Britannica gypsum |
| `herb_other_talc` | 滑石 | item | Britannica talc |
| `herb_other_oracle_bone` | 龙骨（甲骨） | item | Britannica oracle bone |
| `herb_other_magnetite` | 磁石 | item | Britannica magnetite + hematite |
| `herb_other_hematite` | 代赭石 | item | Britannica hematite；中文百科 辰砂（伪品） |
| `herb_other_pearl` | 珍珠 | item | Britannica pearl + oyster |
| `herb_other_oyster_shell` | 牡蛎（壳） | item | Britannica oyster |
| `herb_other_cicada_slough` | 蝉蜕 | item | Britannica cicada |
| `herb_other_silkworm_white_stiff` | 僵蚕 | item | Britannica silkworm + fungus + mulberry |
| `herb_other_earthworm` | 地龙 | life | Britannica earthworm |
| `herb_other_gecko` | 蛤蚧 | item | Britannica gecko |
| `herb_other_deer_antler` | 鹿茸 | item | Britannica antler |
| `herb_other_donkey_hide_gelatin` | 阿胶 | item | Britannica donkey |
| `herb_other_pangolin_scale` | 穿山甲 | item | Britannica pangolin + WWF CITES |
| `herb_other_bear_bile` | 熊胆 | item | 中文百科 熊胆 + WWF CITES |
| `herb_other_tiger_bone` | 虎骨 | item | WWF tiger + CITES |
| `herb_other_musk` | 麝香 | item | **无（抓取均失败）** |

---

## 八、来源清单（48 条，含失败 9 条）

完整字段（`title` / `url` / `access` / `supports` / `rights_note`）以 `reality-herbs-other.json` 的 `sources` 数组为准。这里只给扫读指引：

- **全部 `read` 来源的 `rights_note` 都写明了「本目录只取哪一部分、不采用哪一部分」**，尤其是中文百科含大量配伍、剂量与炮制参数，已逐条声明不采用。
- **9 条 `unavailable` 均标在 `hro_src_fail_*` 命名下**，`supports` 首句为「（无）」，并写明失败原因（403/404/超时），零引用。

---

## 九、一句话总结

本文件把「药材」当作一个**自然物 + 商品 + 文献对象 + 制度对象**的四合一东西来写，而不是当作药物来写：一株树如何被四条价值链索取，一种矿石如何同时做颜料与药，一种真菌如何既是瑞草也是病原，一个被禁的动物制品如何变成一个世纪伦理课题。全部 37 条都没有跨过安全红线；跨不过的地方（苦楝皮、麝香、犀角）一律标注为缺口而不是补写。
