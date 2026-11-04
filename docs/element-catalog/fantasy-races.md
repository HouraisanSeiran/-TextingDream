# 跨题材智慧族群（race）候选组 · fantasy-races

> **状态：候选，未审。** 本组 22 条元素全部 `review_status=needs_review`、`detail_status=needs_detail`。七节齐备 **≠** 事实已核。没有任何一条被任何 StoryPackage 采纳，也**不是数据库实现**（`data/`、正式库、build 名单、源码均未改动）。
>
> - **不是世界正典**：库里存在一个族群，不等于任何世界里有它。
> - **不是可执行规则**：`requires` / `excludes` / `introduction_limits` 是自然语言条件，引擎不认。
> - **不写死平衡值**：本组不给任何体量、战力、寿命、人口数值，只给方向与约束。
> - **不做种族决定论**：不把生物族群写成性格、道德、智力、职业或文化的决定因素；**智慧族群 ≠ 可采集资源**。
>
> ### ⚠ 关于 `kind:race` 标签（重要）
>
> `kind:race` 是**检索用聚类标签**，意为「与族群／类人族群／可交涉的非人群体相关」，**不是生物物种定义**。本组含若干非生物模板条目：
>
> - `fantasy_race_orc_ethnonym` —— 词源与命名学条目，不提供任何族群设定；
> - `fantasy_race_huli_symbolic` —— 符号层条目，写「同一形象如何被不同时代征用」；
> - `fantasy_race_asura_buddhist` —— 佛教六道中的**果报类别**，不是血统、不可世袭。
>
> 它们的共同点只是「常被当作种族写入幻想世界」，而非在生物学或神学上属同一类。保留在本组是为了检索便利，**不要**把它们的 `life` 分类或 `kind:race` 标签读成物种断言。
>
> ### ⚠ 摘要限定（本轮修订）
>
> 摘要一律写成**有地域／传统限定的候选变体**，不把单一来源的母题定为全族必然。例如：「曝日光即石化」只是斯堪的纳维亚传统的一支；「无灵魂」只是欧洲民俗中的一支且属基督教语境判断；「人鱼以藏物成婚」只是部分故事的异文；「龙原为雨神」是该来源的表述且其年代分层未载。凡设计推演均在句内标明，不写成史实。

## 一、本组与既有组的边界（为什么另建一组）

`docs/element-catalog/` 原六组里的 `life` 类已有 13 条：eastern 4（妖修与化形、灵兽与契约、阴灵与鬼修、+ 修士分层）、western 9（巨龙、精灵、矮人、侏儒与哥布林类小妖、妖精与仙境之民、狼人与兽化者、吸血鬼、亡灵与游魂、恶魔与附体）。

本组**不重复**这些条目，只收两类内容：

1. **有明确区别的社会／生理变体**——例如同是水中族群，`fantasy_race_merfolk_bargain` 的机制是「可被藏匿的物件绑定婚姻」，`fantasy_race_jiaoren_weaver` 的机制是「以鲛绡换取陆上关系」，两者不可互换；同是巨类，`fantasy_race_giant_scale` 只处理尺寸的制度后果，`fantasy_race_ogre_predatory` 只处理掠食关系，`fantasy_race_cyclops_smith` 只处理三传统并置。
2. **跨题材适配资料**——明确同一母题在两题材里的不同读法（如 western 的 mermaid ≠ eastern 的鲛人 ≠ 希腊 siren），并逐条写明改编边界。

**刻意不收**：`western_dragon` / `western_elf` / `western_dwarf` / `eastern_yao_cultivator` 等的改写版；也不收纯文体的「异族编目形态」条目（曾拟一条，因不构成族群、且会与《山海经》的成书问题纠缠，已删除；要点并入本文 §五 的编写提示）。

## 二、22 条一览

| # | ID | 名称 | 传统 | 一句话内核 |
|---|---|---|---|---|
| 1 | `fantasy_race_giant_scale` | 巨人：体量与基础设施 | western | 尺度本身就是制度问题（粮食、器物、税赋、司法） |
| 2 | `fantasy_race_troll_daylight` | 巨怪与日光限制者 | western | 见光即毁 → 昼夜规则改写军事与运输 |
| 3 | `fantasy_race_ogre_predatory` | 食人巨魔与掠食性邻居 | western | 日常掠食关系 → 看护、宵禁、悬赏制度 |
| 4 | `fantasy_race_centaur_herder` | 半人马：四足游牧与骑乘关系倒置 | western | 人与坐骑合一 → 马政、畜力经济失效 |
| 5 | `fantasy_race_satyr_revel` | 萨堤尔与山林狂欢群体 | western | 「被制度容纳的越界」——节庆与秘仪的固定角色 |
| 6 | `fantasy_race_nymph_locality` | 宁芙与处所绑定精灵 | western | 一地即有主 → 水权、林权、禁伐令 |
| 7 | `fantasy_race_merfolk_bargain` | 人鱼与海陆婚姻赎回 | western | 藏起物件即可留住对方 → 占有与自由的伦理 |
| 8 | `fantasy_race_siren_hazard` | 塞壬与声学航行危险 | western | 听觉型致命性 → 航海规程与防护用品 |
| 9 | `fantasy_race_cyclops_smith` | 独眼巨人的工匠传统与牧者传统 | western | 同名三传统并置（神匠／牧者／建城） |
| 10 | `fantasy_race_orc_ethnonym` | 兽人：作为他称的敌人类别 | western | 纯命名学条目：敌人如何被命名 |
| 11 | `fantasy_race_long_rain_sovereign` | 龙与水域雨权 | eastern | 降雨是职务而非能力 → 可追责的气象行政 |
| 12 | `fantasy_race_naga_subterranean` | 那伽与地下王权 | eastern | 王室自称源于人与那伽的结合 → 族群即合法性来源 |
| 13 | `fantasy_race_yaksha_hoard` | 药叉与地下宝藏监护 | eastern | 宝藏与地方管辖权绑在同一批存在身上 |
| 14 | `fantasy_race_rakshasa_ritual` | 罗刹与仪式破坏者 | eastern | 敌对仪式而非吃人 → 护法职业与时间窗 |
| 15 | `fantasy_race_asura_rival` | 阿修罗与半同胞对立 | eastern | 与神为半同胞 → 家产与名分之争（词义分层未定，非「恶族」） |
| 16 | `fantasy_race_asura_buddhist` | 阿修罗道：六道中的果报类别 | eastern | 按业因划分的果报类，不可世袭；判摄不一 |
| 17 | `fantasy_race_oni_convertible` | 鬼（oni）：日本民俗中的超自然类属 | eastern | 身份可转变（可归依）→ 宗教与行政选项 |
| 18 | `fantasy_race_tengu_martial` | 天狗与武艺传承谱系 | eastern | 非人作为师承来源 → 门派正统性问题 |
| 19 | `fantasy_race_kappa_contract` | 河童与取水契约 | eastern | 弱点与承诺绑定 → 一次遭遇变长期契约 |
| 20 | `fantasy_race_kitsune_shrine` | 狐与社祠使者 | eastern | 社祠职务 → 神人之间的信息与利益中介 |
| 21 | `fantasy_race_huli_symbolic` | 狐魅与祥瑞转妖的符号层 | eastern | 同一形象被不同时代用于不同政治与道德目的 |
| 22 | `fantasy_race_jiaoren_weaver` | 鲛人与海底织造 | eastern | 以不可复制的织物换取陆上关系 |

分布：`tradition:western` 10 条 / `tradition:eastern` 12 条。题材标签（由导入器追加为 `genre:`）交叉：`western_fantasy` 10、`dark_fantasy` 4、`eastern_fantasy` 12、`xianxia` 4。

## 三、标签约定（检索用，不构成权限或兼容性证明）

统一前缀，全部小写 snake_case：

| 前缀 | 含义 | 本组实测数量 |
|---|---|---|
| `kind:` | 条目类型。**本组一律 `kind:race`**（22/22） | 22 |
| `tradition:` | 母题来源传统，`tradition:western` / `tradition:eastern`，**每条恰一个，不与 genre 混用** | 22 |
| `habitat:` | 栖居环境（`sea` `river` `montane` `underground` `shrine` `wildland` `upland` 等） | 33 |
| `trait:` | 可操作特征（`daylight_ban` `shape_shift` `place_bound` `promise_bound` `rain_office` 等） | 60 |
| `role:` | 剧情功能（`navigation_hazard` `treasure_keeper` `technique_transmitter` `label` 等） | 43 |

`category:life`（22）与 `genre:*`（30）由导入器按 `category` / `genres` **自动追加**，因此**不写进 `tags` 数组**——JSON 里 `genres` 与 `tags` 严格分离，避免同一信息两处维护、来源不一。

## 四、来源与阅读证据（本环节实测）

26 个登记来源：`read` 23 / `search_only` 1 / `unavailable` 2。**被引用的 23 个全部是 `read`**，非 `read` 来源零引用（其中 `_12` `_25` `_26` 三个仅作失败／摘录记录，不支撑任何条目）。

### 4.1 实际读取成功的页面（23）

| 来源 ID | 页面 | 支撑的主要条目 |
|---|---|---|
| `fantasy_race_src_01` | Britannica **giant** | giant_scale |
| `fantasy_race_src_02` | Britannica **troll** | troll_daylight |
| `fantasy_race_src_03` | Britannica **ogre** | ogre_predatory |
| `fantasy_race_src_04` | Britannica **Centaur** | centaur_herder |
| `fantasy_race_src_05` | Britannica **Satyr and Silenus** | satyr_revel |
| `fantasy_race_src_06` | Britannica **nymph** | nymph_locality、satyr_revel |
| `fantasy_race_src_07` | Britannica **mermaid** | merfolk_bargain |
| `fantasy_race_src_08` | Britannica **Siren** | siren_hazard |
| `fantasy_race_src_09` | Britannica **Cyclops** | cyclops_smith、ogre_predatory |
| `fantasy_race_src_10` | Britannica **orc** | orc_ethnonym |
| `fantasy_race_src_11` | Britannica **long** | long_rain_sovereign |
| `fantasy_race_src_13` | Britannica **naga** | naga_subterranean |
| `fantasy_race_src_14` | Britannica **yaksha** | yaksha_hoard |
| `fantasy_race_src_15` | Britannica **rakshasa** | rakshasa_ritual |
| `fantasy_race_src_16` | Britannica **asura** | asura_rival |
| `fantasy_race_src_17` | Britannica **oni** | oni_convertible |
| `fantasy_race_src_18` | Britannica **tengu** | tengu_martial |
| `fantasy_race_src_19` | Britannica **kappa** | kappa_contract |
| `fantasy_race_src_20` | Britannica **kitsune** | kitsune_shrine |
| `fantasy_race_src_21` | 百度百科 **山海经** | huli_symbolic、jiaoren_weaver |
| `fantasy_race_src_22` | 百度百科 **九尾狐** | huli_symbolic |
| `fantasy_race_src_23` | 百度百科 **鲛人** | jiaoren_weaver |
| `fantasy_race_src_24` | 百度百科 **阿修罗** | asura_buddhist |

### 4.2 非 `read` 记录（如实标注，零引用）

| 来源 ID | access | 说明 |
|---|---|---|
| `fantasy_race_src_12` | `search_only` | Britannica **Longwang** 只有指向 long 条目的摘录式跳转，未获独立全文；因此龙王庙制、地方差异、职能细节一律未写 |
| `fantasy_race_src_25` | `unavailable` | English Wikipedia **Naga**：连接超时，零正文 |
| `fantasy_race_src_26` | `unavailable` | ctext.org **山海经** 原文：请求头等待超时。**后果：本组所有古籍引文都只是转引，未与原文校勘** |

另有若干页面**尝试后失败、未登记为来源**（避免把失败当作依据）：`britannica.com/topic/centaur`（404）、`/topic/brownie-folklore`（404）、`/topic/goblin`（成功，但内容已被既有 western 组覆盖，本组未立条）、`/topic/dragon-mythology`（404）、`/topic/dragon`（404）、`/topic/yokai`（403）、`/topic/kappa-Japanese-folklore`（404）、`/topic/naga-Asian-mythology`（404）、`/topic/oni-Japanese-folklore`（404）、`/topic/centaur-Greek-mythology`（403）、`baike.baidu.com/item/龙/5905`（403 安全验证）、`baike.baidu.com/item/四海龙王`（仅多义词选择页，无正文）。**这些不计入「已读 4 个页面」的证据。**

### 4.3 「已读」是什么意思

`access: read` 记录的是**本轮确实抓取到该页正文并据其撰写**，不是许可授权，也不是准确性保证。本组**没有**做逐条事实核验，全部 22 条仍为 `needs_detail`，`reviewed_detail` 为 0。

## 五、编写提示（从本组抽出的通用约束）

1. **先定层，再写族**。精灵、萨堤尔、独眼巨人、阿修罗在来源中都是「一个名字下并存多个互不兼容的传统」；写之前先决定取哪一层，否则会把民俗层与文学层无代价地混用。
2. **尺寸、寿命、变形、日光、誓言这类属性必须带后果**。没有后果的属性只是换了个数字。
3. **同名不同源要显式拒绝合并**：Chinese `long` ≠ European `dragon` ≠ Indian `naga`；Greek `siren` ≠ `mermaid`；Japanese `tengu` ≠ 中国天狗；`orc` 是英语他称而非族群自称。
4. **宗教叙述不作为经验事实**：本组涉及印度教、佛教、道教外缘与日本民俗的内容，一律按「信仰／文本如何记载」处理，不判断其真伪。
5. **古籍原文未校勘**（见 §4.2）：凡引《山海经》《搜神记》《述异记》等，都注明是转引自百科页。
6. **不写种族决定论**：来源里大量出现的「残忍」「愚笨」「淫邪」「惑人」都是文本定型（且常带性别与阶层偏见），改编时应显式处理，而不是当作族群属性照搬。本条同样适用于 `role:` 标签——本轮已把 `role:violent_but_redeemable` 改为 `role:conflict_with_devas`、`role:punitive_force` 改为 `role:local_hazard`，避免用角色标签将群体道德化。
7. **不要把族群写成资源**：本组只用「与谁交涉／由谁管辖／谁来守护」这类关系描述，不写「可采集」「可猎取」的物产口径。

## 六、验证（可重跑）

用 `app/encyclopedia.py`（未改动该模块与 build CLI）在临时库上验证：

```
detected adapter = human-encyclopedia
namespace = fantasy-races | group_id = fantasy-races | schema_kind = human | legacy = False | status = candidate
elements = 22 | sources = 26
import -> {"namespace": "fantasy-races", "adapter": "human-encyclopedia", "batch_id": 1,
           "elements": 22, "element_versions_written": 22, "sources": 26,
           "source_versions_written": 26, "relations": 54,
           "unresolved_relations": [], "ambiguous_relations": [], "shared_element_ids": []}
PROBLEMS: 0
```

自检覆盖：`id` 唯一、`details` 七节齐且均为非空字符串、`category` 全为 `life`、`review_status` 全为 `needs_review`、`detail_status` 全为 `needs_detail`、`source_ids` 零悬空且零非 `read` 引用、`related_ids` 全部可在本组内解析、`genres` 未被重复写进 `tags`、标签前缀仅限约定集合。

`related_ids` 共 54 条关系，全部指向本组元素（不引用其他组未实现的 ID）。

## 七、本次改动范围

- 新增：`docs/element-catalog/fantasy-races.json`、`docs/element-catalog/fantasy-races.md`（本文件）。
- **未改**：`collection-spec.md`、`README.md`、`detail-gaps.md`、`review-notes.md`、其他六组 json/md、`app/encyclopedia.py`、任何 build CLI、`data/`、`StoryPackage`、世界存档、地图、civ-atlas、Terragenesis。未安装依赖、未启动服务、未做 git 提交。
- 验证脚本写在会话临时目录（`temp://scratch/`），不在工作区内。

## 八、已知缺口（待主审）

1. **古籍原文未校勘**：`fantasy_race_src_26` 读取失败，涉及《山海经》《搜神记》《述异记》《太平御览》的引文全部为转引。
2. **两条中文来源为百科汇编**：`_21`「山海经」与 `_23`「鲛人」页面均把古籍与现代创作设定混排，条内已逐项排除现代部分，但排除本身也是人工判断，需复核。
3. **东亚/南亚覆盖偏窄**：本组无朝鲜半岛、无东南亚本土母题（仅有扶南、Mon-Khmer 作为那伽的例证），也无非洲、美洲母题。
4. **多条来源为 Britannica 短条目**（troll / ogre / oni / kappa / tengu / orc / yaksha 均极短），未给年代与地域分层，条内凡涉分层均已明确标为「来源未载」而非填猜。
5. **`fantasy_race_src_20`（kitsune）页面含 AI 生成问答块**，条内只采与正文一致的部分，但「一致」由本环节判断，需复核。
6. **`fantasy_race_src_12`（Longwang）仅为摘录页**：中国龙条目的「雨权职务」一条因此建立得比其余条目薄。

### 本轮修订记录（主审返回后的改动）

依据主审意见，仅改 `fantasy-races.json` / `.md`，**22 条与 ID 集合不变**：

| 项 | 修订前 | 修订后 |
|---|---|---|
| 巨怪摘要 | 「受光而毁……硬规则」 | 明写「曝日光爆裂或石化」是斯堪的纳维亚传统的一支记载 |
| 人鱼摘要 | 「长寿但会死、无灵魂」作定语 | 「其中一支称其……」，并标为特定地域与文本的变体 |
| 人鱼 definition / mechanism | 「欧洲民俗明确」「核心可操作机制」 | 「来源中有一支」「非全部故事皆有」 |
| 半人马摘要 / mechanism | 「马政……全部失效」「极高」「强行筛选」 | 改为「会失效或被改写」，并标注设计推演 |
| 罗刹摘要 | 「憎恶献祭与祈祷的恶魔族群」 | 「其中一支传统称其……」，并点明并非全部罗刹皆恶 |
| 龙摘要 | 「原为雨神的威兽」 | 「该来源称其「原为雨神」」，并注年代分层未载 |
| 狐（kitsune）摘要 | 「社祠编制」作全族通例 | 「两支并存」，明确不将社祠编制当通例 |
| 兽人摘要 | 「从来缺乏自称依据」 | 改为「来源未提供任何族群自称的记载」 |
| 巨人摘要 | 「社会影响主要来自尺度」为断言 | 「本条只把尺寸当单一变量」，推演标为设计归纳 |
| 定名 | 「阿修罗道与可归类的恶」 | 「阿修罗道：六道中的果报类别」 |
| 定名 | 「鬼（oni）与可归依的恶类」 | 「鬼（oni）：日本民俗中的超自然类属」 |
| 标签 | `role:violent_but_redeemable`、`role:punitive_force` | 改为 `role:conflict_with_devas`、`role:local_hazard` |
| 顶层 `note` | 未说明 race 含义 | 补写：`kind:race` 为检索聚类标签、非物种定义，并列明三条非生物模板条目 |
| kappa / oni 正文 | 「类吸血鬼的淫邪存在」「残忍恶毒」直书 | 标明为文本定型、非族群属性 |

验证：本轮修订后重新临时导入，`elements=22`、`relations=54`、`unresolved_relations=[]`、`PROBLEMS: 0`（见 §六）。
