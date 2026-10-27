# 整合审查笔记（review-notes）

> ## ⚠ 状态：第二轮收尾已处理引用链与两处定义（2026-10-26）
>
> 本轮在原有四组 211 条之外，把 `reality-physical`（32）与 `reality-human`（31）一并纳入，**共 274 条**。
>
> **本轮已处理（改动了源 json，仅限授权勘误）：**
> - `society` 21 条 + `steam-horror` 38 条元素，已将正文已明确引用的 `read` 来源补进 `source_ids`（共 59 条元素 / 74 处，涉 15 个不同来源）——§8 的**元素级引用链缺口已清零**。
> - `western_secret_cult.evidence_note` 已重写，区分旧 `search_only` 条目与新增西班牙裁判所正文（§3.2）。
> - `reality_phys_drinking_water_sanitation` 补全 WHO safely managed 四要素（含“不受粪便与优先关注化学物质污染”）；`reality_phys_measurement_precision` 补全重复性/中间精密度/再现性三层。二者均**未重抓来源复校**。
> - **未变**：274 条仍全为 `needs_detail`，`reviewed_detail` = 0；**未新增/删除条目**，未升格任何一条；`shared-themes.json` 与 `collection-spec.md` 未改。
>
> **仍然成立**：§1 的核对结果、§3.3（`dark_fantasy` 宽标签，但有 `genre_relevance`）、§3.5（城市自治来源）、§3.6（现代制度单地域）、§3.7（缺 folk horror 类型学）、§4（主题划分与覆盖局限）。
>
> **本文件仍不做内容级事实审查**：任何统计与“已修”都不等于事实已核实。

整合环节对六组 274 条候选做的核对，以及需要主审拿主意的问题。本文件不代替主审判断。

## 一、本次实际核了什么

| 检查项 | 方法 | 结果 |
|---|---|---|
| 全局 element id 唯一 | 汇总六组 JSON 去重 | ✅ 274 个，无重复（旧 211 结论仍成立） |
| `name` 全库不重名 | 汇总六组比对 | ✅ 274 个，零重名（含 reality 与四组之间） |
| 字段完整性 | 逐条检查 14 个统一字段非空 | ✅ 274/274 |
| reality 额外字段 | `knowledge_kind` / `related_catalog_ids` 覆盖 | ✅ 63/63 条均带 |
| `category` 合法性 | 比对 8 个合法值 | ✅ 零非法 |
| `entry_modes` 合法性 | existing/discovery/player_proposal | ✅ 零非法 |
| `genres` 合法性 | 9 个合法题材值，并检查未跨组串标签 | ✅ 零非法、零越组 |
| `detail_status` 合法性 | 比对三个合法值 | ✅ 274/274 均为 `needs_detail` |
| `details` 七节齐备 | 逐条检查七个键均非空 | ✅ 274/274（western 另有可选第 8 节） |
| `source_ids` 悬空引用 | 逐条比对同文件 sources | ✅ 零悬空（旧结论仍成立） |
| 元素无 `source_ids` | 逐条检查 | ✅ 零条 |
| 引用到非 read 来源 | 统计 access ≠ read 的被引情况 | ✅ **0 条**（旧基线时的 2 条已消失，见 §3.2） |
| 未被引用的来源 | 反向统计（未出现在任何 `source_ids`） | **28 个** = 21 个 `unavailable`（全部失败项）+ 1 个 `search_only` + **6 个 `read`**（`western_src_britannica_germanic_mythology_detail`、`society_src_31`、`sh_src_31`、`sh_src_41`、`sh_src_42`、`reality_human_src_50`）——均属“两端都未使用”，与已修复的引用链缺口不同 |
| `related_catalog_ids` 有效性 | 悬空/自指/重复 | ✅ 210 个引用，0 / 0 / 0 |
| 统计自洽 | 类别纵向合计、题材交叉、各组 md 自述数字 | ✅ 均一致（含现实两分区） |
| `shared-themes.json` 引用真实性 | 逐条比对 274 个 id 全集 | ✅ 25 主题 / 108 成员位 / 103 条不同元素，零悬空 |
| 主题跨组性 | 校验每个主题 `groups` 与实际成员一致 | ✅ 25 个全部满足 |
| 各组 `.md` 与 `.json` 对齐 | 检查 md 是否含本组全部元素 id | ✅ 六组 100% 覆盖，零漏项 |

### 关键核对：采集代理自报的读数是否属实

旧回合一已经验证四个虚构组的 97 条来源读数属实。本轮再次重算（四组已涨到 read 120），并补上现实两区：

| 组 | 自述 | 实测 | 一致 |
|---|---|---|---|
| eastern | 17 条（16 read + 1 unavailable） | read=16, search_only=0, unavailable=1（共 17） | ✅ |
| western | 34 条（33 read + 1 search_only） | read=33, search_only=1, unavailable=0（共 34） | ✅ |
| society | 31 条（30 read + 1 unavailable） | read=30, search_only=0, unavailable=1（共 31） | ✅ |
| steam-horror | 46 条（41 read + 5 unavailable） | read=41, search_only=0, unavailable=5（共 46） | ✅ |
| reality-physical | 36 条（33 read + 3 unavailable） | read=33, search_only=0, unavailable=3（共 36） | ✅ |
| reality-human | 55 条（44 read + 11 unavailable） | read=44, search_only=0, unavailable=11（共 55） | ✅ |

**结果：六组自述读数与实测全部一致。** 全库共 219 条来源 = 197 read + 1 search_only + 21 unavailable。

## 二、统计结果（已入 README）

- 总数 **274** = 四个虚构组 211（54+54+53+50）+ reality-physical 32 + reality-human 31。
- 四组八类别：life 13、power 27、item 15、place 25、institution 46、organization 37、economy 24、conflict 24（合 211）。
- 六组八类别（含现实两分区）：life 13、power 36、item 21、place 35、institution 64、organization 45、economy 35、conflict 25（合 274）。
- 四组制度+组织+经济 = 107 条，占 51%。
- 八题材标签（仅四组）分别 47/52/51/54/41/28/32/24，**相加=329，不可当存量**（交叉 118）。
- 共享母题 25 个，引 103 条不同元素（108 成员位；98 条只属 1 个主题、5 条属 2 个）。

## 三、发现的问题

### 3.1 篇幅口径：已由规范更新解决（保留记录）

采集阶段的 `collection-spec.md:42` 原写「每条正文控制在约 200—350 中文字符」。实测：**211 条 `summary` 没有任何一条达到 200 字**（最短 42、中位约 55、最长 109）。

**这一条在本次整合期间已被规范更新解决**：现行 `collection-spec.md:42` 改为「200—350 中文字符只作为扫读摘要的参考，取消对完整条目的篇幅限制；不能为了压缩删掉机制、例外或适用条件。已有四组是首批候选摘要，不能称为完整定义」，并新增 `details` 分节与 `detail_status`（`summary_only` / `needs_detail` / `reviewed_detail`）。

因此我的处置是：

- **不改任何条目、不凑字数**。
- 四组一律标为**首批候选摘要**。
- 当时的 211 条全都没有 `details` 字段，**全部按 `needs_detail` 处理**，无一条可标 `reviewed_detail`。
- 缺什么逐条记在 `detail-gaps.md`。

**本轮更新**：现在六组 274 条**全部已带 `details` 七节**（274/274，本环节逐条校验非空），但 `detail_status` **仍全部为 `needs_detail`**——因为七节齐备是结构完备，不是事实已核。本轮仍未做内容审查。

另外，六组实测 `summary` 长度已刷新到最新（最短 42 仍在 western，中位 50—93 分题材差异很大，最长 109 在 society），详见 `detail-gaps.md` §1。

实际文本长度只作为「哪几条特别薄」的参考输入，不再当作达标判据。

### 3.2 弱来源能否进 `source_ids`：**已解决**

旧轮次记录：`western_inquisition_heresy` 与 `western_secret_cult` 的 `source_ids` 都含 `western_src_britannica_inquisition`（`access: search_only`）。

**本轮重算：`search_only` / `unavailable` 来源现已零引用。** 上述两条的 `source_ids` 已改为全 `read` 来源（heresy + spanish_inquisition + witchcraft）。`western_src_britannica_inquisition` 现在留在 `sources` 里但**不被任何元素引用**。

⚠ **但遗留一处文字不一致**：`western_secret_cult` 的 `evidence_note` 仍写着「宗教裁判所条目仅读到导语」，而它的 `source_ids` 已不再包含该条目。**这会让读者以为它还在依赖一个 search_only 来源，实际不是。建议采集侧改文案**（本环节不改条目）。

### 3.3 `dark_fantasy` 宽标签问题：**已部分缓解**

western 组 54 条仍全部带 `dark_fantasy` 标签（54/54），`western_fantasy` 是 51/54。

**新变化**：本轮 54 条全部新增了 `genre_relevance` 字段（每个题材一个 `core` / `common` / `compatible_only` 等级 + 说明）。实测：

- `western_fantasy`：core 26 / common 26 / compatible_only 2
- `dark_fantasy`：core 22 / common 31 / compatible_only 1

因此标签不再只有布尔值：**想区分“黑暗奇幻核心”时可以用 `genre_relevance.dark_fantasy == "core"`（22 条）替代标签本身**。建议 README 的衍生使用方改用这个字段。其余五组**没有**该字段。

### 3.4 精灵 / fey 缺直接依据：**已解决（仅来源层面）**

**本轮实测：这是旧结论里变化最大的一条。**

| 条目 | 旧状态 | 当前状态 |
|---|---|---|
| `western_elf` | 无专门条目，全属设计归纳，只借矮人／哥布林旁证 | `source_ids` 含 `western_src_britannica_elf`，`evidence_note` 明写“本次已实际读取全文”，并声明“不再借矮人证明精灵” |
| `western_fey_folk` | fairy 条目正文抽取失败，依据哥布林／侏儒推论 | `source_ids` 含 `western_src_britannica_fairy` + changeling + leprechaun + elf，`evidence_note` 明写“旧版的未读到专门妖精条目已不成立” |

⚠ **但这不等于内容已审**：本环节只确认“来源已进 `source_ids` 且自述已读全文”，**没有核验这些来源内容是否被正确转述**。两条仍在 `detail-gaps.md` A 类名单里，但归类从“缺专页”改为“待内容审”。

另：`western_src_britannica_germanic_mythology_detail`（`read`）进了 `western_dragon` / `western_elf` 的 `source_ids`，但正文里**从未点名引用**它——这是一个反向的小缺口（来源登记了但正文没用）。

### 3.5 城市自治的来源局限

society 组自述：「城市自治」词条实际只讲英国 `city status`，未覆盖欧陆公社与帝国自由市；「中世纪城市」只有书目介绍。因此 `society_urban_charter` 的细节属本项目归纳，`theme_urban_autonomy` 主题已标「概念可对照、证据不可互撑」。

### 3.6 现代制度多中国当代法条

`society_employment_contract`、`society_labor_union`、`society_social_insurance`、`society_police_force`、`society_compulsory_school` 等依据中国法条类百科词条，**地域性极强，不能代表全世界**。README 与 `theme_labour_collective` 均已标注。

补充一个更隐蔽的同类问题：`society_customary_law`、`society_court_hierarchy` 这类条目同标 `historical+modern`，但历史侧与当代侧的制度前提完全不同，一个条目同时覆盖两边容易变粗。

### 3.7 steam-horror 缺 folk horror 类型学（**未变**）

本组自述未找到可读的类型学专文（`sh_src_43` 电报、`sh_src_44` BFI 专题、`sh_src_45` 英文维基、`sh_src_46` 期刊页均为 `unavailable`，零引用），因此**不写「民俗恐怖必须包含 X」**。诚实处置，但也意味着无法回答「某个元素算不算民俗恐怖」。已在 README 与 `detail-gaps.md` E 类标注。

### 3.8 society 组四类空白（**部分被 reality 库补上**）

society 组 53 条只分布在 institution 22 / organization 18 / economy 12 / conflict 1，**life/power/item/place 全为零**。但本轮新增的现实库两分区补了部分：`reality-physical` 提供 place 9 / power 8 / item 6，`reality-human` 提供 place 1 / power 1。**还剩的空白**：历史向的**器物与日常技术**仍主要在 western / steam-horror 侧，society 自身仍为零。

### 3.9 `eastern.md` 与 JSON 口径一致，但两题材几乎同义（**未变**）

东方组 54 条中 45 条同时标两个题材，仅 9 条单标。文件自己引了「二者几乎可以画上约等号」的措辞。所以 `eastern_fantasy` 与 `xianxia` 在本批中**实际上是同一个题材的两个检索入口，不是两种风格**。README 的题材表已按「标签命中」措辞，未写成「两种题材各有 47/52 条独立元素」。

### 3.10 reality 两分区的实测（新增）

两项容易误读的事，先写清：

1. **`knowledge_kind` 分布两端极不对称，但不是错误**。`reality-physical`：empirical 25 / mixed 6 / historical 1，`belief_description` = 0；`reality-human`：historical 16 / mixed 10 / belief_description 5，`empirical` = 0。这正好对应“物理侧不该有信仰记述、人文侧不该有纯实验机制”的职责划分，**不建议为了分布好看而互调**。
2. **`related_catalog_ids` 是真实交叉引用而非空壳**。实测 `reality-physical` 97 个引用指向 steam-horror 46 / society 22 / western 19 / eastern 9 / reality-human 1；`reality-human` 113 个指向 society 51 / steam-horror 26 / western 18 / eastern 6 / reality-physical 6。**零悬空、零自指、零同名冲突**（与四组 211 条也无重名）。

另一件仍待观察的事：两个分区的 `related_catalog_ids` 是**单向**的（reality → 虚构组），四个虚构组的条目**没有反向指向 reality 的字段**（它们根本没有 `related_catalog_ids` 这个键）。这与“不做反向依赖”的声明一致，但如果将来要做双向导航，需要为四组新增字段。

## 四、共享母题的判断说明（供复核）

25 个主题全部 `relation: shared_motif_or_distinct_variants`，每个都写了 `shared_points` 与 `non_merge_reason`。本轮做了逐项引用验证（结果全部通过，详见 README §4）。要点：

- **明确做成「防误合并」主题的两个**：`theme_energy_supply_chain`（灵气/奥术/蒸汽）、`theme_monastic_order_rule`（修会/道门/宗门）。任务里点名不能直接等同的那两件事，就是这两个主题的中心。
- **跨全部四组的主题只有 3 个**：`theme_master_apprentice`（师徒）、`theme_rite_festival_calendar`（祭祀节令）、`theme_money_credit_debt`（货币信用）。分布是：2 组交集的 4 个、3 组交集的 18 个、4 组全包的 3 个。这说明真正的全题材母题很少，大部分是 2—3 组交集——这本身就是一个结论。
- **被多个主题引用的元素有 5 条**（各属 2 个主题）：`society_craft_guild`、`society_noble_precedence`、`western_kingdom_monarchy`、`western_secret_cult`、`eastern_dao_lineage`。重叠是故意的，`counting_note` 已声明。

**局限（本轮重算后的量化）**：成员划分仍是人工语义判断，**未经第二人复核**。覆盖面上：主题只覆盖四个虚构组的 103/211 条，**108 条四组元素未入任何主题**；`reality-physical` 32 条与 `reality-human` 31 条**零覆盖**。这是已知空白，按任务约束**不为凑覆盖率而强行合并或新立主题**；所有 25 个主题的 `member_ids` 也都已核实“含跨组真实共性的理由”，不存在只为一个组服务的空壳（最小成员数 3，组数最少 2）。

若主审认为某个主题拉得太宽（最可能被质疑的是 `theme_status_stratification`，它把五种不同分层依据放在一起），只需删 `member_ids` 里的条目或拆主题，不影响六组原始文件。

## 五、审查标准（已由主代理定稿）

以下四项已定稿，记在此以备验收时避照。它们**不改变**前面 §1—§4 的核对结果，但明确了后续口径。

### 5.1 验收两层（决策一）

- **结构层 100%**：全部条目的结构、引用、ID、`details` 七节、**跨字段矛盾与绝对断言扫描**。
- **内容层按风险分层抽查**：每题材至少 3 条 + **所有已知弱证据项** + 所有**历史／技术精确断言项**重点抽。
- **记录审了哪些 ID／来源与结果**；**不以抽检代替全量事实核实**。

推论（我的理解，供校对）：§3.4 精灵、§3.5 城市自治、§3.6 现代制度、以及 eastern 侧雷法与丹药病理、steam 侧的技术参数，都属于「必抽」而非「可抽」。

### 5.2 `reviewed_detail` 仅主代理可升格（决策二）

- 采集代理一律保持 `needs_detail`；**已写七节不等于事实已核**。
- 未逐条核验则保留候选状态；**任何统计与报告不是全量认证**。
- 可用文字区分「详情已补齐」与「证据待核」，**但不擅改 schema 状态字段**。

这同时回答了我先前提的「升格权归谁」：不归采集代理，也不归本整合环节，**归主代理逐条核验**。

### 5.3 纯设计归纳的写法（决策三）

不需要伪造历史原型或假引文；证据节写「本项目建议」或「类型母题归纳」，并交代：自选世界规则、常见变体、适用理由与**反例**、**不可推论什么**。通用性证据不足**不得称普遍事实**；`source_ids` 只支持相关背景，**不证明该机构历史上存在**。

→ 这直接作废了我先前在 `detail-gaps.md` C 类里隐含的预设（“没有史料就是个问题”）。按新口径，**没有史料不是缺陷，写成“有史料”才是**。C 类的「问题」应重述为：「需补：自选规则的边界与反例」，而不是「需补史料」。

### 5.4 reality 两分区分工（决策四）

| 分区 | 负责 |
|---|---|
| `reality-physical` | 可验证的物理／生物／生态机制与工程条件（病原传播、饮水、食物） |
| `reality-human` | 社会应对与组织制度（医院、保险、检疫授权、交通治理、经济法律） |

交叉处**用真实 ID 关联**，不重复造双权威。

→ 这回答了我先前提的「公共卫生归哪边」：按管辖对象切——**机制在 physical，应对制度在 human**。

## 六、仍待主审明确的事项

主代理已定稿四条（§5），以下是本轮新查到或仍悬着的缺口（**不自行决**）：

1. ~~引用链缺口~~ **已修复（第二轮）**：`society` 21 条 + `steam-horror` 38 条元素的 `source_ids` 已补齐（59 条 / 74 处，涉 15 个 `read` 来源）；元素级缺口归零。剩下 6 个 `read` 来源两端都未使用（§8.3），需定口径：补引还是从 `sources` 删。
2. ~~`western_secret_cult.evidence_note` 文字残留~~ **已修复**：已改写并区分旧 `search_only` 条目与新增西班牙裁判所正文（§3.2）。
3. **四条点名 reality 条目的复验**（README §11.3）：文案层 **4 条要求均已补齐**；但本环节**未回溯来源原文**，`reviewed_detail` 仍为 0。需主审决定是否启动逐条复验。
4. **`dark_fantasy` 是否重新收窄**（§3.3）：现在有了 `genre_relevance`（core 22），可以不改标签而靠字段过滤；但**其余五组没有这个字段**，口径不统一。
5. **society 四类空白**（§3.8）：`reality` 库补了部分，但历史向器物/日常技术仍缺。
6. **现代制度是否要求多地域并置**（§3.6）：society 组当前多中国当代法条口径。
7. **主题覆盖率**（§4）：25 主题只覆盖 103/211，两分区零覆盖。建议保持现状（不为覆盖率而扩主题），但需主审确认。
8. **`shared-themes.json` 的 `purpose`/`counting_note` 字段只写“四组共 211 条 / 全部保留 211”**：该文件**本轮主动未改**（引用验证全过、无需改，且任务只要求“在文档里说清”）。需主审注意读法：**25 个主题只聚类原四组 211 条中的 103 条；整个目录是 274 条**。主题成员数（108 位 / 103 条）**不是目录存量，也不覆盖 reality 两分区**——不得把“25 个主题”读成“覆盖全库 274”。若要让文件本身也带上这句，再由主审授权改它。

已解决、不再需要决定：篇幅口径（规范已更新）、`entry_modes` 语义（已重新定义）、`details` 验收口径与升格权（已定稿）、纯设计归纳写法（已定稿）、reality 两分区边界（已定稿）、**弱来源进 `source_ids`（实测已归零，§3.2）**、**精灵/fey 缺专页（已补，§3.4）**。

## 七、本轮边界声明

- **修改的文件（第二轮）**：源 json：`society.json`（仅 `source_ids` 行）、`steam-horror.json`（仅 `source_ids` 行）、`western.json`（仅 `western_secret_cult.evidence_note`）、`reality-physical.json`（仅两条的 `background`/`exceptions`/`definition`/`evidence_and_uncertainty`）；文档：`README.md`、`detail-gaps.md`、`review-notes.md`、`reality-physical/README.md`、`reality-human/README.md`。
- **未改**：`eastern.json`/`.md`、`reality-human.json`/`.md`、`shared-themes.json`、`collection-spec.md`；未改任何组 `.md` 正文（`society.md`/`steam-horror.md` 的 `source_ids` 表述不矛盾，未动）。
- **未动**：源码、`data/`、任何 StoryPackage、`TOWN_GENERATION_V1_PLAN.md`、`工程说明.md` 及其它非本目录文件。
- **未改**任何 `detail_status`、未新增/删除条目（仍 274 条）。
- 未建库、未写 schema、未实现兼容性算法。未做 git 提交。
- **未重新抓取任何来源正文**（含本轮引用的 WHO fact sheet 与 VIM3 词条）——两条 reality 定义的补充依据是条目已有 `source_ids` 的 `supports` 记载，不是新一轮核验。
- **未做任何内容级事实审查**，未给任何条目升格（`reviewed_detail` 仍为 0）；本目录任何统计**不是全内容认证**。

## 八、引用链缺口（已修复，保留记录）

### 8.1 现象与处置（修复前 → 修复后）

全库 `source_ids` 始终 **零悬空、零非 read 引用**；本条记录的是另一种不一致：「正文点名引了某个 `read` 来源，但该 id 没进该元素的 `source_ids`」。

| 组 | 修复前：只进正文、未进 `source_ids` 的 read 来源 | 涉元素 | 修复后 |
|---|---|---|---|
| society | `society_src_27`、`_28`、`_29`、`_30` | 21 条 | ✅ 已补 23 处（涉 11 个来源，含正文还引了 `_01/_05/_13/_14/_18/_20/_24` 的情形） |
| steam-horror | `sh_src_29`、`_30`、`_32`、`_33`、`_34`、`_35`、`_36`、`_37`、`_38`、`_39`、`_40` | 38 条 | ✅ 已补 51 处（涉 20 个来源） |

**修复规则（已执行）**：逐条取「正文已点名的有效来源 ∪ 原 `source_ids`」去重；**只接受 `access: read`**，`search_only` / `unavailable` 一律不加入（实测不存在这类待加项）；既有来源全部保留，未删任何 id。

典型核对例子（修复后两个 id 都已在内）：

- `steam_reciprocating_engine`：`source_ids` 现为 `[sh_src_01, sh_src_02, sh_src_04, sh_src_33]`，与 `details.evidence_and_uncertainty` 里“1775—1800 年约产 500 台见 sh_src_33”一致。
- `society_fief_succession`：`source_ids` 现为 `[society_src_03, society_src_01, society_src_28, society_src_29]`，与正文引的 src_28（萨利克法典）、src_29（封建等级）一致。

### 8.2 遗留：6 个 `read` 来源两端都未使用（需主审定口径）

| 来源 | 状态 | 问题 |
|---|---|---|
| `society_src_31`（中华民国临时约法） | `read` | 未进 `source_ids`，正文也未点名；自述「含全文」，是本组少有的全文级来源 |
| `western_src_britannica_germanic_mythology_detail` | `read` | 同上（与 `..._germanic_myth` 是两个不同 id） |
| `sh_src_31`（Bessemer process） | `read` | 同上；内容与 `steam_coal_fuel_chain` 直接相关 |
| `sh_src_41`（Horror film）、`sh_src_42`（Fantasy） | `read` | 同上；本可支撑 `folk_horror` 侧的题材界定 |
| `reality_human_src_50`（FAO 目录页） | `read` | 零引用；自述为目录页，本来就不能支撑细节 |

→ 这 6 个属于「登记了但未被使用」，**不能自动猜它们该归哪个元素**，所以本轮**未强行添加**（避免为了消数字而乱挂引用）。与 §1 表的 28 个未引用来源完全对应（21 unavailable + 1 search_only + 6 read）。
