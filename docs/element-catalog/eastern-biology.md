# 东方玄幻 / 仙侠 · 动植物专项候选组（eastern-biology）

状态：**候选素材收集**，不是数据库实现，不是任何故事包的已采纳正典，未进入 `data/` 或任何 StoryPackage。
配套机读文件：[`eastern-biology.json`](eastern-biology.json)（`schema_version: 1` / `status: candidate` / `group: eastern-biology`）。
规范依据：[`collection-spec.md`](collection-spec.md)。

- 元素数量：**21**（动物 `kind:fauna` 10 / 植物与菌类 `kind:flora` 10 / 精怪 `kind:spirit` 1）
- 题材标签：`eastern_fantasy`、`xianxia`，**21 条全部同时标两题材**（本组是新 schema，`genre:` 标签由导入器按 `genres` 自动追加，文件里不手写）
- 来源：登记 **9** 条，其中实际读过正文 **7** 条（`access: read`），**2** 条抓取失败并如实标注（`unavailable`）
- 详细程度：21 条全部含 `details` 七节，`detail_status` 一律 `needs_detail`，`review_status` 一律 `needs_review`（未经主审，不冒充 `reviewed_detail`）
- `details` 七节合计每条 **1047—1623 字**（均值约 1266 字），不设上限，未为压篇幅删掉机制、例外或条件
- 类别：21 条全部 `category: life`

## 先读这一节：本组与 `eastern.json` 的分工

同目录的 [`eastern.json`](eastern.json)（54 条）已经覆盖组织、制度、能力、物品与经济主干，其中已有 `eastern_spirit_beast`（灵兽与契约）、`eastern_yao_cultivator`（妖修与化形）、`eastern_spirit_agriculture`（灵植与灵田）。本组**不复制**这些条目的组织学与制度内容，只补它们没有的部分：

| 已有条目（eastern.json） | 本组补的是 | 不重复的部分 |
|---|---|---|
| `eastern_spirit_beast` | `eastern_bio_spirit_beast_husbandry`：豢养／收服／契约三种关系的成本差、供养瓶颈、兽殁归谁 | 契约「不必是绝对控制」的合法变体已在原条目，此处只引用不重写 |
| `eastern_spirit_agriculture` | `eastern_bio_spirit_moss_rice`：作物本身的生长条件、留种、连作、储藏损失 | 灵田分级与佃户关系不动 |
| `eastern_alchemy` / 道教内丹 | `eastern_bio_demon_core_hunt`：妖兽被「资源化」的那一层 | 外丹五步、内丹四阶段不再展开 |
| `eastern_yao_cultivator` | `eastern_bio_fox_spirit`、`eastern_bio_mountain_specter`：不走阶梯修行的狐与精怪 | 化形、妖修社会不动 |

`eastern_bio_lingzhi_fungus` 与 `eastern_bio_ginseng_root` 的「名山产芝草」「入山合药」观念，直接指向 `eastern.json` 的 `eastern_src_dongtian`，本组不另立来源。

## 三条必须先说清的边界

1. **传统记述与现代设计归纳，逐条分列。** 每条 `evidence_note` 与 `details.evidence_and_uncertainty` 都把材料分两堆：有古籍／词条可核的（《山海经》《说文》《白虎通德论·封禅》《朝野佥载》，以及灵芝、人参、竹、石蒜的生物学记述），与本项目为可玩性补出的（尾数＝修为、丹核经济、契约条款、灵果成熟窗口、净化上限等）。后者一律标明「本项目设计归纳」，**不得当古说或科学事实引用**。
2. **仙侠不等于真实道教。** 本组不用「道教」解释任何一条的机制；「内丹」一词在道教语境中指内修工夫，与「妖兽体内有颗可挖的核」不是同一概念，本文件在 `eastern_bio_demon_core_hunt.background` 与 `historical_scope` 里明写了这一点。
3. **不用作品独占名词。** 全部条目的 `name`／`aliases` 都是可脱离具体作品理解的通用称法（狐妖、龙属、灵兽、灵谷、蛊虫……），未取任何小说、游戏、影视的专有名词、专有境界名或专有人名。

## 本轮主审修订（五项要求已逐条落实）

1. **山精归 `kind:spirit`**：其本体可为木、石、器物或祠庙，不属动物也不属植物，已从 `kind:fauna` 改为 `kind:spirit`，并增 `origin:wood_stone_object` 指明本体类型。现分布：动物 10 / 植物与菌类 10 / 精怪 1，**动物仍 ≥ 8**。
2. **`eastern_bio_demon_core_hunt` 改名与限缩**：显示名由「妖兽与内丹」改为「**妖兽丹核**」，`aliases` 保留「妖兽内丹」「内丹」「兽核」「妖丹」「妖核」等限定词以便检索。并在 `summary`、`excludes`、`definition`、`exceptions`、`historical_scope` 五处明确：**仅适用于无智慧兽型**；已开智、能言、可立约、有社会的智慧妖族**不入本条、不得当作丹核矿产开采**；若世界允许对智慧者下手，则属争战或罪行，应另设条目并给出对等后果。
3. **摘要里的绝对断言改为可选设定/制度解读**（消除 summary 与 details 边界矛盾），涉四条：
   - 麒麟：不再写「见之则天下安宁，伤之则天下失序」，改为「若采纳瑞应设定（可选）：见麟被读作治世评语、伤麟被读作失序征兆——这是某类世界设定下的**制度解读**，非麒麟自身属性，也未经验证」；`story_roles`、`definition`、`mechanism` 同步改为条件式。
   - 灵谷：不再写「无论境界多高，都得有人种地」，改为「若某世界采用『修士仍需进食』这一制度解读（与辟谷设定互斥，需二选一）；否则本条可整体降为凡俗粮食」。
   - 灵禽：不再写「一只能载人的鹤，吃掉的是一座小庄园」，改为「在本条设定的一档饲养开销下……（数值为设计示例，非来源数据）」。
   - 凤属（连带处理）：不再写「见则天下安宁」，改为「在瑞应设定下见则被读作安宁之兆」。
   - 另外，灵果、山精、瑞禽、妖兽的 `summary` 均补上「候选设定」前缀，明确神话/灵气效力属候选设定。
4. **四项灵植改为明确的玄幻变体（原创设计已标注）**：人参→灵参（人参的玄幻变体）、灵芝→灵菌芝（灵芝的玄幻变体）、石蒜→幽花（石蒜的玄幻变体）、竹→灵竹（竹的玄幻变体）。`name` 均带「某某的玄幻变体」限定；`summary` 开头即声明「候选设定中的 X：以 Y 为形态蓝本的东方玄幻变体（原创设计）」，并各自至少保留一个现实约束（人参的慢生苛境、灵芝的腐木生境、石蒜的形态与季节窗口、竹的速生与一开花即死），其余部分为新增设定；四条 `definition` 首句均冠以「**本条是玄幻变体，不是现实物种记录。**」。**ID 全部未变**（`eastern_bio_ginseng_root`、`eastern_bio_lingzhi_fungus`、`eastern_bio_lycoris_bloom`、`eastern_bio_bamboo_grove`）。
5. **不以生态学证明民俗**：石蒜/幽花条改为三层分离——形态与季节窗口（可核）→ 有微毒（可核）→ 与死亡相关（文化联想，未核源流）；并在 `summary`、`background`、`definition`、`mechanism`、`exceptions`、`story_uses`、`historical_scope`、`evidence_and_uncertainty` 八处反复声明「不得说成由生态习性导出」「不是民俗的生态学证据」「『长在墓旁』只是可选叙事与栽植习惯」。
6. **菌类不属植物的标注**：灵菌芝条目与本文档均注明 `kind:flora` 只是「草木与菌类」一并检索的口径，**不代表分类学**；条目另标 `taxon:fungus`。

所有修订均在原 21 条内完成，未新增或删除任何条目，**ID 与数量均未变**，状态仍全部为 `needs_review` / `needs_detail`（候选）。修订后用未改动的 `app.encyclopedia.import_file` 在临时库重跑，见文末验证结果。

## 灵药与「长生」的硬约束

本文件对以下四种写法一律不默认成立，并在各条目 `excludes`／`adaptation_limits` 里逐条落成文字：

- **不给现实处方。** 灵芝与人参条目的来源页含大量药用主治、剂量、加工工艺与病虫害药剂参数；本文件**明确声明不采用**，只取生境、生长节律、繁殖方式与资源史。石蒜同理，只保留「鳞茎有小毒」这一风险定性。蛊虫条目**完全不写任何配制、投毒、饲养或解毒做法**。
- **长生不默认成立。** 没有一条写成可稳定获得的长生物；「千年芝」「芝王」「仙桃」被明确限定为传说层或神话层。
- **无限量产不默认成立。** 灵果设「多年一熟、数日即落」；人参设「连片采绝后需数十年至上百年且森林未被破坏才可能恢复」；古木设「成材以百年计，非人一生所能补」；灵禽设「食量大到养得起本身就是筛选器」。
- **物产不等于世界库存。** `eastern_bio_spirit_moss_rice.evidence_and_uncertainty` 明写「某地有灵田不等于世界有富余灵谷，物产不构成库存」；芝场、参场、竹场、藤域的产权与运输成本各自单独成立，不能因为目录里有一条就认为哪都能买到。

## 扫读表

类别列全为 `life`；题材列 `东`=eastern_fantasy、`仙`=xianxia（21 条皆两者兼标，不再逐行重复）。
`kind` 列：fauna=动物性，flora=植物与菌类检索口径，spirit=精怪（本体非生物）。**注意 `flora` 不表示分类学上的植物**：真菌（灵菌芝）不属植物，只是为了检索并入口径。

### 动物（10）

| # | ID | 名称 | 题材 | kind | 主要剧情功能 | 证据状态 |
|---|---|---|---|---|---|---|
| 1 | `eastern_bio_fox_spirit` | 狐妖与多尾狐 | 东/仙 | fauna | 真伪辨识、旧约清算、信仰与官府摩擦 | 古籍较实（《山海经》三处、郭璞注、《白虎通》等） |
| 2 | `eastern_bio_dragon_kin` | 龙属与蛟类 | 东/仙 | fauna | 水权、旱涝与祭祀、敕封合法性 | 古籍较实（《说文》《管子》《论衡》《尔雅翼》《广雅》） |
| 3 | `eastern_bio_phoenix_kin` | 凤属与鸾鸟 | 东/仙 | fauna | 瑞现真伪、服色僭越、空中通路 | **缺口**：无凤/鸾/朱雀专条 |
| 4 | `eastern_bio_qilin` | 麒麟 | 东/仙 | fauna | 不可猎的红线、苑囿财政、伪麟欺君 | **缺口**：仅得瑞应清单并列 |
| 5 | `eastern_bio_mountain_specter` | 山精与老物成精 | 东/仙 | **spirit** | 开发与禁忌、归因政治、材料诱惑 | 观念史可循，无志怪原文 |
| 6 | `eastern_bio_demon_core_hunt` | 妖兽丹核 | 东/仙 | fauna | 猎场经济、垄断禁猎、兽潮（**仅无智兽型**） | **纯设计归纳** |
| 7 | `eastern_bio_spirit_beast_husbandry` | 灵兽驯养与契约 | 东/仙 | fauna | 契约纠纷、继承配给、供养危机 | **纯设计归纳** |
| 8 | `eastern_bio_giant_serpent` | 巨蟒与蟒蛟 | 东/仙 | fauna | 无人区标尺、商路兴废、水源禁忌 | 文献存在性，「巴蛇」原文未核 |
| 9 | `eastern_bio_long_lived_tortoise` | 灵龟与长寿龟 | 东/仙 | fauna | 占卜行业、禁令走私、跨代见证 | 间接（四灵脉络），无龟类专条 |
| 10 | `eastern_bio_immortal_crane` | 仙鹤与灵禽坐骑 | 东/仙 | fauna | 航线关禁、饲养财政、仪仗僭越 | 间接，无鹤类专条 |
| 11 | `eastern_bio_gu_insects` | 蛊虫与毒虫 | 东/仙 | fauna | 无法举证的中毒、冤案、污名 | **重大缺口**：无任何专门研究 |

### 植物与菌类（10）

| # | ID | 名称 | 题材 | kind | 主要剧情功能 | 证据状态 |
|---|---|---|---|---|---|---|
| 12 | `eastern_bio_spirit_lotus` | 灵莲与灵池水生 | 东/仙 | flora | 护池与排污、禁采偷采、仪式失仪 | 仅生态类比 |
| 13 | `eastern_bio_lingzhi_fungus` | 灵菌芝（灵芝的玄幻变体） | 东/仙 | flora（菌类） | 采药行业、误采责任、栽培冲击 | **生物学较实**（生境、腐生、杂菌虫害） |
| 14 | `eastern_bio_ginseng_root` | 灵参（人参的玄幻变体） | 东/仙 | flora | 山场产权、绝产、作伪鉴定 | **生物学与资源史较实**（含濒危与产区绝产） |
| 15 | `eastern_bio_peach_wood` | 桃木与桃林 | 东/仙 | flora | 量产防护与伪造、聚落边界、仙桃骗局 | **缺口**：无桃木辟邪专条 |
| 16 | `eastern_bio_immortal_fruit` | 灵果与增益果实 | 东/仙 | flora | 成熟窗口压缩时间、分配政治、信息战 | **纯设计归纳**（仅周期类比） |
| 17 | `eastern_bio_demon_vine` | 妖藤与食人草木 | 东/仙 | flora | 地形废置、清除工程、栽培失控 | 仅类比；「食人」属文学夸张 |
| 18 | `eastern_bio_bamboo_grove` | 灵竹（竹的玄幻变体） | 东/仙 | flora | 大宗物资、开花即死的灾难、竹林扩张 | **生物学较实**（Britannica 竹条） |
| 19 | `eastern_bio_lycoris_bloom` | 幽花（石蒜的玄幻变体） | 东/仙 | flora | 季节与地点标记、误食、投毒诬告 | **生物学较实**（形态、花期、生境、有小毒） |
| 20 | `eastern_bio_ancient_timber` | 神木与古木 | 东/仙 | flora | 伐与禁、促枯暗害、灵脉与镇物 | 间接（长生命周期类比） |
| 21 | `eastern_bio_spirit_moss_rice` | 灵谷与灵田作物 | 东/仙 | flora | 农时与战事、水权、配给制 | 仅类比（人参/竹/石蒜的条件约束） |

## 标签设计

新 schema 每项自带 `tags`，本组统一三层：

- **本体层**（21/21 各有一个）：`kind:fauna`（10）、`kind:flora`（10）、`kind:spirit`（1，仅山精与老物成精）；`tradition:eastern`（21/21）。
  - `kind:spirit` 用于**本体不是生物**的精怪（木、石、器物、废祠），不归入动物也不归入植物；另附 `origin:wood_stone_object` 说明其本体类型。
  - `kind:flora` 仅作「草木与菌类」检索口径，**不代表分类学**：真菌（灵菌芝）不属植物，已在条目内另标 `taxon:fungus`。
- **实用检索层**：`habitat:`（栖地，如 `habitat:deep_water`、`habitat:grave_site`、`habitat:cultivated_field`）、`trait:`（性状，如 `trait:polymorph`、`trait:slow_growth`、`trait:venom`、`trait:auspice`）、`role:`（剧情功能，如 `role:omen`、`role:resource_source`、`role:divination_tool`、`role:depletion_case`）。
- **导入器追加**：`category:life` 与 `genre:eastern_fantasy`、`genre:xianxia` 由 `app/encyclopedia.py` 在导入时自动生成（`_prepare_element` 对 `category` 与 `genres` 各追加一条），文件里**不手写**，避免重复来源混淆。

标签全部符合 `_TAG_RE`（小写 snake_case，允许 `.` `:` `-`）。导入后该组共 **92** 个去重标签。

## 七节 `details` 的写法

规范七节键（`app/encyclopedia.py` 的 `DETAIL_SECTIONS`，顺序即规范顺序，已逐条核验完全一致、且每节均为字符串）：

`definition` → `mechanism` → `conditions` → `exceptions` → `story_uses` → `historical_scope` → `evidence_and_uncertainty`

对应本组的中文分工：定性 → 机制与参数维度 → 前提条件 → 不被排除的合法变体 → 推到社会层面的后果 → 时期／地域限定与改编边界 → 证据分层与不确定处。

每条都实际交代了这四件具体事：

- **栖地**（`conditions` 首项，具体到潭渊/林相/坡向/墓域/田块，并写清不适合之处）；
- **灵气／食物或生长条件**（分血食型与食灵型、分慢生与速生、给出温度与湿度的越界后果）；
- **繁殖与更新**（卵生／胎生／分球／孢子／竹的开花即死，并据此推出「猎杀与采挖强度超过补充率会怎样」）；
- **采集与驯养限制**（取丹须杀、取甲须杀、取蜕要冒风险、幼兽难驯、活捕几无可能、囚养失灵与否）。

`exceptions` 一节刻意不做装饰：每条都列出 3—5 种**合法但常被省略**的变体，以及 2—3 条**反例**（「不能默认……」「不能默认……必得善报」），以免目录一旦存在某项就被当成题材通例。

## 来源与阅读记录（只写实际发生的）

实际抓取并读到正文的 7 页（`access: read`）：

| 来源 ID | 页面 | 得到什么 |
|---|---|---|
| `eastern_bio_src_shanhaijing` | 山海经（百度百科） | 成书争议（非一时非一人）、十八篇结构、以四方山川为纲记草木鸟兽与神怪并夹祯祥评语、约四百余神怪畏兽、山川虚实争议与四库列小说家、「食者不蛊」式效用记述体例、名山物产写法 |
| `eastern_bio_src_long` | 龙（百度百科） | 《说文》「鳞虫之长…春分而登天，秋分而潜渊」、《管子·水地》、《论衡》、《广雅》蛟应虬螭四种、宋《尔雅翼》九似、《本草纲目》引王符「龙无尺木不能升天」、苍龙七宿星象说与扬子鳄原型说**两说并存**、龙王庙/舞龙/龙舟民俗、佛教龙王观并入 |
| `eastern_bio_src_fox` | 九尾狐（百度百科） | 《山海经》南山/海外东/大荒东三处青丘记述、郭璞注「太平则出而为瑞」、《白虎通德论·封禅》瑞应清单与「子孙繁息」、《孝经》援神契、《说文》、《朝野佥载》「无狐魅不成村」、《儒林公议》讥奸佞、明清小说脉络、汉画像西王母身侧、魏晋巫风与物老成精推动由瑞转妖 |
| `eastern_bio_src_lingzhi` | 灵芝（百度百科） | 属种与学名、菌盖木质有漆样光泽与同心环沟、分布、腐生于栎/松木桩与根际、需散射光与湿度、生于偏酸环境、杂菌污染几乎无补救、虫害（尺蠖/菌蝇/白蚁/蜗牛）、生长期与采收判别 |
| `eastern_bio_src_ginseng` | 人参（百度百科） | 五加科属、喜冷凉忌强光、针阔混交林下与微酸性砂壤土、三年开花五六结果、10℃/30℃ 休眠与耐寒越冬、种子需层积催芽、野山参/移山参/园参之分、**野生种群极危与历史产区绝产** |
| `eastern_bio_src_bamboo` | Bamboo（Encyclopaedia Britannica） | 115 属 1400 种、东亚东南亚最集中、每日可长 30 厘米、有节中空茎与地下茎、高度范围、**多数竹一生开花结籽一次且需 12—120 年**、繁殖靠营养体、强扩散形成单优下层、从笋/种/叶/纤维/板材/脚手架到节内硅质药用的一材多用 |
| `eastern_bio_src_lycoris` | 石蒜（百度百科） | 学名与鳞茎尺寸、秋季出叶、花茎与伞形花序 4—7 朵鲜红色反卷、花期 8—9 月、阴湿山坡与溪沟边、喜阴耐寒、**日均 24℃ 为高温上限**、夏季休眠、偏酸腐殖质土、分球为主、实生苗到开花 4—5 年、**鳞茎含生物碱有小毒**、花叶不相见 |

抓取失败并如实记录的 2 条（`access: unavailable`，本文件**未引用其任何内容**）：

| 来源 ID | 地址 | 失败情况 |
|---|---|---|
| `eastern_bio_src_zhwiki_fail` | zh.wikipedia.org 相关动物条目 | 443 端口连接超时（dial tcp connectex 无响应），未取到正文；爬虫类条目因此改以设计归纳与《山海经》记述体例支撑 |
| `eastern_bio_src_baike_404` | baike.baidu.com「龙 /1395」 | 返回 HTTP 404 与百科错误页；随后改读正确条目 `/13027234` 成功 |

未采用但已登记的内容边界：灵芝与人参页含大量**栽培操作参数、药剂配比、药用主治与用量**，石蒜页含药理主治与病害药剂，这些一律**不转录**（`rights_note` 已逐条声明），只取生态与形态层面的定性事实。蛊虫条目未取得任何专门研究，因此只写「像什么、造成什么社会后果」，不写任何做法，并明确声明不将蛊术等同于现实任何民族或地区的实际习俗。

## 关联

`related_ids` **只用本组实际存在的 ID**（21 条内部互链，共 63 条关系）；本组来源里没有对 `eastern.json` 或 `western` 等的可核依赖，故未使用 `related_catalog_ids`。跨组协作（与 `eastern_spirit_beast`、`eastern_spirit_agriculture` 的衔接）以正文文字指向，不写假 ID。

## 验证结果（本轮修订后重跑；在 `temp://scratch/` 中做的，未改 CLI、未建库）

用临时脚本把本文件交给未改动的 `app.encyclopedia.import_file` 做完整 schema 校验与试导入，数据库落在系统临时目录、验完即弃：

- `detect_adapter` 自动识别为 `human-encyclopedia`（新 schema，全部条目都有 `tags`）
- 导入成功：`elements 21 / element_versions 21 / sources 9 / source_versions 9 / relations 63`
- `unresolved_relations: []`、`ambiguous_relations: []`（关联目标全部可解析）
- `review_status` 全为 `needs_review`、`detail_status` 全为 `needs_detail`（导入器不自动升格，符合预期）
- 该组统计：21 元素、92 标签、`schema_kind: human`、`legacy_schema: false`
- 结构自检全部通过：21 个 ID 唯一；`details` 键序与 `DETAIL_SECTIONS` 完全一致且全为字符串；`summary`/`aliases`/`source_ids`/`review_status`/`detail_status` 齐备；标签全部符合 `_TAG_RE`；`related_ids` 无组外目标

## 待审点（给主审看的，不是结论）

1. ~~山精标 fauna~~ **本轮已按主审意见改为 `kind:spirit`**（详见上节第 1 条），此点结清。若将来需要更细的本体分类，可在 `kind:spirit` 下再用 `origin:` 细分（现已标 `origin:wood_stone_object`）。
2. **证据强度的三段差**：灵菌芝、灵参、灵竹、幽花（四条的现实底子可核，但已明确标为玄幻变体）— 狐狸、龙、山海经体例（古籍较实）— 凤、麒麟、桃木、龟、鹤、蛊、精怪（专条缺口）。第三段在 `evidence_note` 里逐条写了「本组未取得…专条来源」，**不是已核**，正式入库前应优先补这几条的专门文献。
3. **`eastern_bio_gu_insects` 证据最弱、伦理风险最高**：只有「食者不蛊」一类早期表述的存在可依。条目已采取「只写不可举证与社会后果、不写做法、不把虚构等同于现实族群」的写法，若主审认为风险仍高，可整条降为 `summary_only` 或剔除。
4. **`historical_scope` 的长度**：这一节在本组承担「时期地域限定 + 改编边界」两个职责，因此普遍偏长，个别条目（龙、狐、蛊）读起来更像两段合成。是否拆分属格式取舍，未擅自改七节结构。
5. ~~「妖兽与内丹」用词风险~~ **本轮已改名为「妖兽丹核」**，`aliases` 仍保留「内丹」等检索词。前提与责任归类已在 `background`、`definition`、`historical_scope` 三处写明；若主审仍觉得风险偏高，可进一步从 `aliases` 中删掉裸「内丹」一项。
