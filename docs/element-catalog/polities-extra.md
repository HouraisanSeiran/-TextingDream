# 国家与政体模板（补充）：polities-extra

本文件说明 `polities-extra.json`（group `polities_extra`）。它补充 `polities.json` 的 9 种政体，不改动它，也不与它重复 id 或名称。每条是可改写的政体模板，不是具体国家。

## 1. 条目清单（18 条）

`magic_tier` 一列为空表示非奇幻政体（JSON 中为 null）。

| # | 名称 | id | tech_tier | magic_tier | genres |
|---|---|---|---|---|---|
| 1 | 选侯制与选举君主国 | polity_elective_monarchy | medieval | | western_fantasy, historical |
| 2 | 绝对君主制 | polity_absolute_monarchy | medieval | | western_fantasy, historical, steampunk |
| 3 | 开明专制 | polity_enlightened_despotism | steam | | historical, steampunk, western_fantasy |
| 4 | 宗藩与朝贡体系 | polity_tributary_suzerainty | classical | | eastern_fantasy, historical |
| 5 | 游牧汗国 | polity_steppe_khaganate | classical | | eastern_fantasy, western_fantasy, historical |
| 6 | 幕府式军政 | polity_military_shogunate | medieval | | eastern_fantasy, historical |
| 7 | 贵族寡头共和国 | polity_oligarchic_republic | medieval | | western_fantasy, historical |
| 8 | 联邦国家 | polity_federation | steam | | steampunk, modern, historical |
| 9 | 邦联 | polity_confederation | medieval | | western_fantasy, historical, steampunk |
| 10 | 特许公司领地 | polity_chartered_company_colony | medieval | | historical, steampunk, western_fantasy |
| 11 | 教团骑士国 | polity_knightly_order_state | medieval | | western_fantasy, historical, dark_fantasy |
| 12 | 哈里发式政教结构 | polity_caliphal_state | medieval | | historical, eastern_fantasy, western_fantasy |
| 13 | 革命公社 | polity_revolutionary_commune | steam | | historical, steampunk |
| 14 | 军政府 | polity_military_junta | steam | | historical, steampunk, modern |
| 15 | 军阀割据 | polity_warlord_fragmentation | classical | | historical, eastern_fantasy, western_fantasy |
| 16 | 龙主统治 | polity_dragon_dominion | classical | rare | western_fantasy, dark_fantasy, eastern_fantasy |
| 17 | 宗门治国 | polity_sect_realm | classical | common | eastern_fantasy, xianxia |
| 18 | 亡灵君主国与诅咒领地 | polity_undead_realm | medieval | common | dark_fantasy, western_fantasy, folk_horror |

档位说明：

- 绝对君主制与特许公司领地的典型形态接近 `world-setting.md` 的 renaissance 档，但 `tools/catalog_overlay.TECH_TIERS` 没有该档，所以按“拿不准取更低一档”写 medieval，理由写在各条 `conditions`。
- 军政府取 steam，是按常备军与政变的现实条件取最早档，没有写 early_modern。
- 议会君主国的“宪政君主”部分已由 `polity_parliamentary_monarchy` 覆盖，本批不单立。

## 2. 新增的 `polity:*` 值

`world-setting.md` 现有值为 monarchy、empire、republic、city_state、theocracy、tribal、merchant。本批新增 18 个：

| 值 | 对应条目 |
|---|---|
| `polity:elective_monarchy` | 选侯制与选举君主国 |
| `polity:absolute_monarchy` | 绝对君主制 |
| `polity:enlightened_despotism` | 开明专制 |
| `polity:tributary_system` | 宗藩与朝贡体系 |
| `polity:khanate` | 游牧汗国 |
| `polity:shogunate` | 幕府式军政 |
| `polity:oligarchy` | 贵族寡头共和国 |
| `polity:federation` | 联邦国家 |
| `polity:confederation` | 邦联 |
| `polity:chartered_colony` | 特许公司领地 |
| `polity:knightly_order_state` | 教团骑士国 |
| `polity:caliphate` | 哈里发式政教结构 |
| `polity:commune` | 革命公社 |
| `polity:junta` | 军政府 |
| `polity:warlordism` | 军阀割据 |
| `polity:dragon_dominion` | 龙主统治 |
| `polity:sect_realm` | 宗门治国 |
| `polity:undead_realm` | 亡灵君主国与诅咒领地 |

管线 `polity_templates()` 取 `kind:polity` 条目，`forms` 为其 `polity:*` 值，所以 `form_hint` 若要命中新条目，需使用上表的新值。

## 3. 与旧 9 条的区分

- 游牧汗国：有常设汗庭、世袭汗家和征服后的定居附庸；部族联盟的首领多是战时共推。
- 贵族寡头共和国：靠家族出身与封闭议事会，不以海上贸易为基础；商业共和国由商人财富与贸易网络决定。
- 教团骑士国：统治层是发愿的军事修会，职能是征服与驻防；神权国由祭司集团治理民众。
- 宗门治国：宗门掌握一国政权并向国民征税征兵；`eastern_sect` 等条目只描述修行团体本身，不涉及治国。
- 邦联与联邦：邦联是主权国家的联盟，联邦是一个主权国家。
- 封建王国描述土地与效忠，选侯制描述王位如何产生，两者可叠加。

## 4. 来源

access=read（实际读过正文，共 15 条）：

- `docs/world-setting.md`（项目内部设计文档）。
- 百度百科 14 条，页面由无头 Edge 抓取：选帝侯、君主专制政体（绝对君主制）、开明专制、朝贡体系、突厥汗国、幕府、联邦制、邦联制国家、不列颠东印度公司、德意志骑士团、哈里发、巴黎公社、军政府、藩镇割据。
- 朝贡体系与哈里发只读到词条正文已加载的部分或摘要级内容，各来源 `supports` 已写明。
- 军政府词条后半部分的具体案例没有采用。

access=unavailable（读取失败，零引用）：

- 中文维基百科《神圣罗马帝国》：连接超时（`dial tcp 31.13.88.26:443`）。
- 百度百科《圣约翰骑士团》：只取得安全验证页。

龙主、宗门、亡灵三条奇幻政体没有史料来源，贵族寡头共和国是结构归纳，这 4 条 `evidence_grade=inferred`；其余 14 条为 `mixed`。

## 5. 校验结果（均已通过，脚本退出码 0）

1. `app.encyclopedia.import_file` 导入系统临时目录的一次性库：先导入 polities、western、society、eastern、steam-tech、steam-horror、fantasy-races 以解析 `related_ids`，再导入本文件。首次导入 18 条元素、17 条来源、66 条关系，`unresolved_relations` 与 `ambiguous_relations` 均为空；再导入一次 `idempotent=True`，18 条元素与 17 条来源均为 unchanged。临时库已删除。
2. 按 `tools/catalog_overlay` 规则自查：`primary` 在 `PRIMARY`，`evidence_grade` 在 `EVIDENCE_GRADES`，`tech_tier` / `magic_tier` 在词表或为 null；`validate_entry` 对四个叠加字段逐条通过；tags 里的 `tech:` / `magic:` 与字段一致，没有手写 `primary:` / `evidence:`；`genre:` 标签与 `genres` 一致且在 `GENRES` 内。
3. 与 `polities.json` 的 id、name 无重复，与 `docs/element-catalog/*.json` 其他分组也无 id 冲突；没有任何元素引用 unavailable 来源。

注：`tools/` 里的分组登记（如 `encyclopedia_build`）是否需要新增 `polities_extra`，本任务未改 `tools/`，未验证。

## 6. civ-atlas lineage 建议映射

civ-atlas 只给 lineage（republic / realm / khanate）。下表给出各 lineage 可映射到的模板，“首选”是默认匹配，“备选”用于科技、地理或题材提示明确时。

| lineage | 首选 | 备选（旧 9 条） | 备选（新条目） |
|---|---|---|---|
| republic | polity_industrial_republic（steam 及以上）、polity_merchant_republic（medieval，沿海或商路） | polity_city_state_league、polity_mage_council_state（奇幻且魔法 common 以上） | polity_oligarchic_republic、polity_federation、polity_confederation、polity_revolutionary_commune |
| realm | polity_feudal_kingdom（medieval）、polity_bureaucratic_empire（classical，大国） | polity_parliamentary_monarchy（steam）、polity_theocratic_state | polity_absolute_monarchy、polity_elective_monarchy、polity_enlightened_despotism、polity_tributary_suzerainty、polity_military_shogunate、polity_warlord_fragmentation、polity_caliphal_state、polity_knightly_order_state、polity_chartered_company_colony、polity_military_junta、polity_dragon_dominion、polity_sect_realm、polity_undead_realm |
| khanate | polity_steppe_khaganate（classical） | polity_tribal_confederation | polity_tributary_suzerainty（作为向定居大国称臣的一方）、polity_warlord_fragmentation（汗国分裂后）、polity_dragon_dominion（非人领主统领游牧或山地部族时） |

使用提示：

- realm 的备选很多，建议按科技档、题材和邻国关系过滤。例如 steam 以前不选军政府和公社，东方题材优先宗藩、幕府、军阀割据，黑暗奇幻再启用亡灵君主国与教团骑士国。
- 同一 lineage 内，首选条目作兜底，新条目作变体。
- 奇幻三条（龙主、宗门、亡灵）要求世界魔法档不低于各自 `magic_tier`。
