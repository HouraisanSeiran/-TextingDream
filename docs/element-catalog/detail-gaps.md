# 待补 detail 清单（detail-gaps）

> ## ⚠ 状态：已按当前 JSON 重算；本文件现在区分「字数缺口」与「证据缺口」两类
>
> 六个 JSON 已全部补齐 `details` 七节（274/274），所以"缺 `details`"这一类缺口**已经不存在**。剩下的两类是：
>
> 1. **证据缺口**：七节写了，但条目自己就声明某个知识面没拿到专门来源。这一类**补字数补不上**，也不能因为它"看起来完整"就升格。
> 2. **摘要偏薄**：`summary` 不足 55 字——按现行规范，`summary` 不受 200—350 字约束，所以这是**可选优化**，不是硬缺口。
>
> 本文件**不做内容主审**，不给任何条目升格。全部 274 条仍为 `needs_detail`。

本文件回答一个具体问题：**274 条里，哪些仍不能直接当完整定义用，缺什么。**

不是泛泛的「以后还会补充」。每条都点名，并标出它缺的是哪一类。

## 一、先说清一个标准问题

现行 `collection-spec.md:42` 的措辞已经明确：

> 200—350 中文字符只作为扫读摘要的参考，取消对完整条目的篇幅限制；不能为了压缩删掉机制、例外或适用条件。已有四组是首批候选摘要，不能称为完整定义。

实测六组 `summary` 长度（本环节重算）：

| 组 | 最短 | 中位 | 最长 |
|---|---|---|---|
| eastern | 56 | 64 | 72 |
| western | 42 | 50 | 55 |
| society | 66 | 93 | 109 |
| steam-horror | 52 | 63 | 85 |
| reality-physical | 54 | 66 | 81 |
| reality-human | 47 | 57 | 80 |

结论：

- `summary` **只是扫读字段**，**不受 200—350 字约束**，也不靠字数判完整。
- 真正的完整定义靠 `details`（七节）＋ `detail_status`。**现在六组 274 条的 `details` 七节全部齐备**（本环节逐条校验，七节均非空）。
- **七节齐备 ≠ 事实已核**。全部 274 条仍为 `needs_detail`，没有一条可标 `reviewed_detail`。
- 长度本身不代表完整；本环节**未做任何内容审查**，所以也不标 `reviewed_detail`。

下面把「特别薄、或已知有硬缺口」的挑出来点名。

## 二、A 类：证据侧硬缺口（条目自己声明缺依据）

> 这一类的判定标准是「缺依据」，不是「缺字数」。**已经补上 `details` 七节了，但没有新的来源支撑，所以这几条仍不应标 `reviewed_detail`。**
>
> 下表由本环节扫描全部 274 条的 `evidence_note` 得出（匹配「待补 / 未取得 / 未读到 / 仅读到 / 缺专门 / 未找到 / 未覆盖」等自述标记）：**共 8 条**。

| ID | 名称 | 仍缺什么（据当前 evidence_note） | 与旧清单的差异 |
|---|---|---|---|
| `eastern_thunder_ritual` | 雷法与召雷 | 雷部神将谱系、雷法仪轨细节仍无一手文献 | **部分改善**：已补读神霄派词条（`eastern_src_shenxiao`），可支撑「雷法历史存在＋内修—外用结构」；谱系与仪轨仍标待补 |
| `eastern_mortal_plague` | 瘟疫、丹毒与灵灾 | 丹药重金属中毒的病理与流行病学细节 | 未变 |
| `eastern_mortal_city` | 凡俗城镇与胥吏 | 其他朝代的基层治理专门来源 | **部分改善**：已补明代里甲词条（限明代，不可直接照搬）；其他朝代仍缺 |
| `eastern_pilgrimage_festival` | 庙会、香火与节庆 | 「香火会社」的具体组织形态 | 未变 |
| `western_elf` | 精灵 | **原缺口已解决**：现有 Britannica elf 专条全读 | **已补专页**；但证据内容本身**仍待审**（本环节未核） |
| `western_fey_folk` | 妖精与仙境 | **原缺口已解决**：fairy 专条全读 + 替身儿 + 小妖精 | **已补专页**；证据内容仍待审 |
| `western_inquisition_heresy` | 异端审判 | 不再依赖 `search_only` 条目（已移出 `source_ids`） | **已改引** 西班牙宗教裁判所等 `read` 来源；内容仍待审 |
| `western_secret_cult` | 秘密教派 | 与该条同类 | ✅ **已修（第二轮）**：`evidence_note` 已重写，区分旧 `search_only` 条目与新增西班牙裁判所 `read` 正文，不再笼统写「仅读到导语」；内容仍待审 |

另：eastern 的 `eastern_src_zhihu_realm_discuss`、`society_src_26`、steam 的 `sh_src_28`/`_43`—`_46`、reality-physical 的 `rp_src_33`/`_34`/`_37`、reality-human 的 11 条 `unavailable`——**均为 `unavailable` 且零引用**，不构成 A 类。

## 三、B 类：摘要偏薄（< 55 字）——**已降为可选优化，不是硬缺口**

> 重算后共 **62 条**（旧清单只统计了四组的 52 条，漏了现实两分区）。按现行规范 `summary` 不受字数约束，本类**不影响“能不能用”**，也不影响 `detail_status`；仅当作者希望扫读更直观时再改。

### western 组（49 条）

western 组 54 条中只有 5 条达到 55 字，其余 49 条在 42—53 字：

`western_dragon`(52)、`western_elf`(51)、`western_dwarf`(52)、`western_gnome_goblin`(47)、`western_fey_folk`(47)、`western_vampire`(49)、`western_demon_possession`(52)、`western_arcane_spellcraft`(53)、`western_magic_price`(51)、`western_alchemy`(53)、`western_necromancy`(43)、`western_curse_oath`(46)、`western_divination`(44)、`western_enchanting`(50)、`western_witchcraft`(44)、`western_enchanted_armament`(51)、`western_holy_relic`(44)、`western_potion_elixir`(49)、`western_arcane_material`(50)、`western_treasure_hoard`(48)、`western_dungeon_ruin`(50)、`western_castle_keep`(47)、`western_gothic_cathedral`(53)、`western_monastery_scriptorium`(48)、`western_crypt_catacomb`(53)、`western_haunted_manor`(52)、`western_free_city`(52)、`western_kingdom_monarchy`(51)、`western_manor_serfdom`(51)、`western_knighthood_chivalry`(51)、`western_guild_charter`(47)、`western_church_hierarchy`(49)、`western_inquisition_heresy`(50)、`western_monastic_order`(48)、`western_taboo_forbidden_lore`(48)、`western_magic_regulation`(44)、`western_mage_college`(45)、`western_underworld_guild`(46)、`western_secret_cult`(51)、`western_pilgrimage_order`(52)、`western_trade_league`(50)、`western_mining_smelting`(47)、`western_usury_finance`(44)、`western_apprenticeship`(44)、`western_siege_warfare`(42)、`western_tournament`(47)、`western_monster_incursion`(51)、`western_plague_famine`(51)、`western_witch_trial`(42)

**为什么整组偏薄**：western 组把篇幅写在了 `evidence_note`（区分「来源支持」与「设计归纳」）上，那部分反而比 summary 长且更扎实。这是有意选择，不建议为了字数把 `evidence_note` 删短。

### steam-horror 组（3 条）

`steam_station_yard`(54)、`steam_workshop_apprentice`(52)、`horror_ancestral_hall`(54)

### reality-physical（1 条）

`reality_phys_drinking_water_sanitation`(54)

### reality-human（9 条）

`reality_human_metrology_standardization`(47)、`reality_human_money_as_convention`(50)、`reality_human_migration_voluntary_forced`(50)、`reality_human_literacy_scribal_training`(50)、`reality_human_weights_measures_local`(53)、`reality_human_kinship_descent_terminology`(53)、`reality_human_inheritance_partition`(53)、`reality_human_marriage_alliance_dowry`(54)、`reality_human_festival_annual_cycle`(54)

eastern（最短 56）与 society（最短 66）**零缺口**。

## 四、C 类：纯设计归纳条目（按定稿口径重述）

这四条的共同点：**历史上并不存在同名机构**。它们的 `details` 七节现已齐备，但**能不能用仍需主审判「自选规则是否写清」**，而不是判「有没有史料」。

> **口径修正（据审查标准§9.3）：没有史料不是缺陷，把它写成有史料才是。**
> 以下四条**允许保留在候选里**，不要求伪造历史原型或假引文。需核的是「自选规则的边界与反例」是否到位，而不是「有没有史料」。

| ID | 纯设计内容 | 主审需核什么（按新口径） |
|---|---|---|
| `western_magic_regulation` | 魔法管制与执照 | 自选规则：管制对象如何界定、发证权在谁、无证使用的后果分级；**反例**：什么情况下管制反而不成立 |
| `western_mage_college` | 法师学院 | 自选规则：经费来源、招生与毕业资格、与世俗政权的授权关系；**反例**：竞争性传承机制（如师徒制）为何仍存在 |
| `western_underworld_guild` | 盗贼公会 | 自选规则：收入来源、与治安机构的共存机制；**反例**：严打环境下为何不会必然地下化 |
| `western_monster_hunter` | 猎魔人 | 自选规则：谁付钱、如何验证猎物、误杀的责任；**反例**：无酬或义务型应对（民兵、驱魔职）为何也常见 |

另有一条写法硬要求：证据节必须写「本项目建议」或「类型母题归纳」，并交代**不可推论什么**。`source_ids` 只支持相关背景，**不证明该机构历史上存在过**。

## 五、D 类：跨题材引用未落到具体条目

`western_elf`、`western_fey_folk`、`eastern_spirit_beast`、`eastern_yao_cultivator` 都涉及「非人智慧族类与人类共处」这一带，但四者分别在两个组内各自成条，**没有任何一条承担跨组的接口说明**（例如：西幻精灵与东方妖修在「长寿／生育率／继承后果」上是否可对照）。

这不是错误——按规范不应擅自跨组合并。但若将来要做跨题材混搭，这是已知的**空白点**。已在 `shared-themes.json` 里用 `theme_restless_dead`、`theme_kin_lineage_clan` 等主题做了部分间接串联，但非人族的跨组对照尚不存在。⚠ **本轮重算：`shared-themes.json` 的 25 个主题确实一条也没涉及非人族对照**，此空白仍未填补，且按任务约束**不为了补空白去新立主题**。

而且两分区（`reality-physical` / `reality-human`，共 63 条）**与任何主题零关联**，也是同一类空白。

## 六、E 类：整组级缺口（按当前 JSON 实测）

| 组 | 缺口 |
|---|---|
| eastern | **17 条来源全部是百科／问答类汇编**（无学术专著、无一手道经），层级只到「可靠参考」的下限。另 `eastern_src_zhihu_realm_discuss` 为 `unavailable`，未被引用。 |
| western | `dark_fantasy` 标签打到 54/54（全部），**单靠标签不能区分**「黑暗奇幻特有」与「奇幻通用」；**但已新增 `genre_relevance` 字段把等级拆开**（core 22 / common 31 / compatible_only 1），比旧版可用了，但只在 western 组有。 |
| society | 完全没有 life／power／item／place 四类。modern 侧多依据中国当代法条，**非世界通例**。 |
| steam-horror | **没有 folk horror 类型学专文**（BFI 专题、英文维基、期刊页均失败），所以无法回答「民俗恐怖的边界在哪里」这类问题。 |
| reality-physical | 强度类来源只支撑定性结论，**不提供可作工程使用的数值**；`rp_src_09`/`rp_src_23` 仅得导言段。 |
| reality-human | 11 条 `unavailable`（占其来源总数 55 的 20%），且有 5 条自述为导言/摘要级。 **但 `unavailable` 均零引用，不构成引未读来源。** |

## 七、优先级建议（供主审参考，不代替决定）

1. **先做 A 类中的未解决项**：`eastern_thunder_ritual`（雷部谱系）、`eastern_mortal_plague`（丹药病理）、`eastern_pilgrimage_festival`（香火会社）、`eastern_mortal_city`（其他朝代基层）——它们缺的是依据，不是字数。
2. **精灵／fey / 异端审判三条需重新归类**：它们的「缺专页」问题已解决，现在缺的是**内容审阅**，应归入内容层抽查而非证据层。
3. **C 类与 B 类降级处理**：C 类只核「自选规则＋反例＋不可推论什么」是否写清；B 类不影响可用性，可留待以后。
4. **E 类整组缺口属采集阶段决策**，不建议在整合环节动，应交回收集环节或主审。
5. **引用链缺口（已修复）**：`society` 4 个 + `steam-horror` 11 个 `read` 来源只在正文里被引、未进 `source_ids`，涉 59 条元素——**已在第二轮补入（59 条 / 74 处）**；剩下 6 个 `read` 来源两端都未使用（清单见 `review-notes.md` §8.2），需定口径。
6. **两条 reality 定义已补齐文案层但未复校**：`reality_phys_measurement_precision`（重复性/中间精密度/再现性）、`reality_phys_drinking_water_sanitation`（safely managed 四要素）——依据的是已有 `source_ids` 的 `supports` 记载，**未重抓 VIM3/WHO 正文**，不得视为已审。

## 八、本次未做的事

- 没有为任何一条补写或修改 `details` 正文（不扩写、不虚构）。本文件只做**缺口分类与计数刷新**；第二轮实际改写的是 `source_ids` 与两条 reality 定义（详见 `README.md` §10.2）。
- 未改：`eastern.json`/`.md`、`reality-human.json`/`.md`、`shared-themes.json`、`collection-spec.md`。
- 没有引入新来源。
- **没有做任何内容主审，没有给任何条目升格。** 全部 274 条仍为 `needs_detail`。
- 本文件列出的全部 ID 已与六个 JSON 实际 id 逐一核对，**零悬空**。
