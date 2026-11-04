# western-alchemy：西方奇幻魔药候选素材（20 条）

> **状态：候选（`status: candidate`），不是世界正典，不是数据库实现，不是可执行规则。**
> 全部 20 条 `review_status = needs_review`、`detail_status = needs_detail`；**没有任何一条通过内容主审**。
>
> ## ⚠️ 安全声明（请先读这一条）
> **本文件是游戏／小说设定素材，不是医药资料。** 全部条目刻意不写任何现实可操作的配方、配伍、剂量、浓度、服用量、炮制温度与时间，也不写有毒植物的处理方式或解毒做法。文中出现的「剂量」一律只作**维度名称**（起效时间量级、有效次数、累积上限等），不给任何数值。文中不出现任何「可治疗某病」的现实医疗主张：一切效力都是虚构世界的设定，不是被验证的事实。若需要现实医药信息，本文件不适用也不应被援引。

---

## 一、与同目录其他文件的分工（同一物只记一次）

| 文件 | 记什么 | 本文件如何对待它 |
|---|---|---|
| `western.json`（54 条） | 已记「药剂与灵药」「炼金术」「魔法材料与稀有矿草」「魔法的代价与反噬」四条**主干框架**（经济、制度、代价分类） | **不复写框架**，只记具体用途分型；需要时以文字指向（如「价格与产地归『魔法材料与稀有矿草』管」） |
| `western-biology.json`（21 条） | 药材的具体生态、采集禁忌、栽培条件、原创生态模板 | **只以文字呼应来源**（曼德拉草、颠茄类、紫杉、柳、槲寄生、蕨丛、蘑菇、灯藓、狼／鹿／渡鸦、不死鸟、独角兽角材、鸡蛇），**不复制其条目内容，不写任何假 ID** |
| 本文件 | 20 条**具体用途分型**的魔药 | — |

药材呼应一律以中文名 + 该文件的名称指认（如「同目录 `western-biology.json` 所记的曼德拉草」），**没有写任何跨组 `related_ids` / `related_catalog_ids`**——本组元素之间的关联也为 0，全部条目无关联字段，因此导入时未解析关联必然为 0。

---

## 二、覆盖矩阵（题目要求的 17 个面向，全部落实）

| 要求面向 | 条目 |
|---|---|
| 治疗 | `clotting_draught` 止血药酒、`healing_unction` 外敷愈伤膏 |
| 止血 | `clotting_draught` |
| 解毒 | `universal_antidote`（**宣称型，明确「万能」不成立**） |
| 催眠睡眠 | `soporific_draught` |
| 记忆或遗忘 | `oblivion_draught` |
| 变形 | `shapeshift_draught` |
| 飞行药膏 | `flying_unguent` |
| 隐身 | `invisibility_oil` |
| 爱情药（philter） | `love_philtre` |
| 力量 | `strength_draught` |
| 狂战 | `berserk_draught` |
| 抗火 | `ember_ward_unguent` |
| 抗寒 | `winter_draught` |
| 水下呼吸 | `water_breathing_draught` |
| 解除石化 | `petrifaction_release` |
| 真话剂 | `truth_draught` |
| 生长或缩小 | `growth_shrink_powder` |
| 抗魔力 | `magic_ward_elixir`（**纯原创设定，无历史／民俗依据，已明写**） |
| 复活类（**限定传说层**） | `revivifying_elixir` 复生灵药、`longevity_elixir` 长生灵药 |

全部名称均为可脱离具体作品理解的**通用类型名**，未使用任何作品的专有药名。

---

## 三、20 条一览（ID · 名称 · 一句话用途 · 主要来源支撑）

| # | ID | 名称 | 一句话用途 | 主要来源 |
|---|---|---|---|---|
| 1 | `western_alc_clotting_draught` | 止血药酒 | 内服药酒，让伤口尽快凝止、把「撑到有人处理」这段时间买下来 | magic, poison, antidote |
| 2 | `western_alc_healing_unction` | 外敷愈伤膏 | 涂在伤口上让口子合拢、生新肉，管「合不合得上」，不管失血 | magic, poison, mandrake |
| 3 | `western_alc_universal_antidote` | 万应解毒剂（宣称型） | 号称解百毒，实际「万能」是它的社会身份而非效力——主线是误判与行骗 | antidote, poison, magic, aphrodisiac |
| 4 | `western_alc_soporific_draught` | 催眠安神药 | 使人昏睡、痛觉迟钝；战场接骨、暗巷劫财、宫廷治失眠是同一味药的三种东西 | magic, mandrake, belladonna, poison |
| 5 | `western_alc_oblivion_draught` | 忘忧药（记忆抹除剂） | 把一段经历本身取走，既是止痛药也是最彻底的暴力，且不可精确到「只删那一件事」 | Lethe, mandrake |
| 6 | `western_alc_shapeshift_draught` | 变形药剂 | 暂时取得另一种形体；核心不是「变成什么」，而是「还回不回得来」 | werewolf, witchcraft, Circe, Proteus |
| 7 | `western_alc_flying_unguent` | 飞行药膏 | 涂身便能离地赴会；重点是这个说法从哪来——记载只到「供称」，从未给出膏方 | witches' sabbath, witchcraft, torture, mandrake |
| 8 | `western_alc_invisibility_oil` | 隐身油 | 使人不被看见；刻意写成有缺陷的隐身，破口就是剧情 | amulet, magic, Gorgon, Medusa |
| 9 | `western_alc_love_philtre` | 爱情药（致爱饮） | 使人爱上饮者；无效则是欺骗，有效则是人身侵夺，没有第三种可能 | aphrodisiac, mandrake, magic, amulet |
| 10 | `western_alc_berserk_draught` | 狂战药 | 战前服下不畏痛不畏死；代价从不在战场结算，而「我当时在药里」不构成免责 | berserker, Odin, Valhalla, werewolf |
| 11 | `western_alc_strength_draught` | 力量药 | 短时提高力气与耐受；不提高技术与判断，多毁在肌腱与后背 | magic, poison, berserker |
| 12 | `western_alc_ember_ward_unguent` | 抗火油膏 | 涂抹后暂时不畏火焰；最实用的场合是作坊，最危险的滥用是蹈火神判 | torture, magic, salamander |
| 13 | `western_alc_winter_draught` | 御寒药酒 | 使人长时间不觉寒冷；不觉冷不等于不失温，因此它是「安静的杀手」 | magic, poison |
| 14 | `western_alc_water_breathing_draught` | 水下呼吸药 | 水下呼吸，把水从边界变成通道，因此它改的不是能力而是地图 | magic, Proteus |
| 15 | `western_alc_petrifaction_release` | 解石药 | 把石化者恢复原状；石化一旦可逆，就从死亡降级为监禁 | Medusa, Gorgon, amulet |
| 16 | `western_alc_truth_draught` | 真话剂 | 使人无法说谎；核心争点是「靠药剂得到的供词算不算证据」 | torture, mandrake, belladonna, poison |
| 17 | `western_alc_growth_shrink_powder` | 增减药（生长与缩小） | 使身体或物件暂时变大变小；价值全在尺度改变的物理后果上 | magic, salamander |
| 18 | `western_alc_magic_ward_elixir` | 抗魔药 | 使法术难以附着；纯原创设定，一旦存在就重画魔法秩序 | amulet, magic, Circe |
| 19 | `western_alc_revivifying_elixir` | 复生灵药（传说层） | 据说能把死人唤回；**默认不成立**，必付不可逆代价，绝不能成为消耗品 | resurrection, immortality, Asclepius, Valhalla |
| 20 | `western_alc_longevity_elixir` | 长生灵药（传说层） | 与哲人石／`elixir vitae` 相关的延寿灵药；**默认不成立**，先摧毁的是继承制度 | alchemy, philosopher's stone, elixir, immortality, Asclepius |

---

## 四、标签统计（208 个标签实例）

统一两标签：`kind:item` **20/20**、`tradition:western` **20/20**。**未手写任何 `genre:` 或 `category:` 标签**（由导入器按字段追加，实测追加项为 `category:item` 与 `genre:western_fantasy` / `genre:dark_fantasy`）。

| 分组 | 标签数 | 明细（次数） |
|---|---|---|
| `effect:` | 27 个 / 28 次 | healing(2)、antidote、bleeding_control、wound_closure、sleep、sedation、analgesia、memory_erasure、forgetting、transformation、shapeshifting、flight、invisibility、compelled_affection、frenzy、pain_immunity、strength、endurance、fire_resistance、cold_resistance、water_breathing、petrification_release、compelled_speech、size_change、magic_resistance、resurrection、longevity |
| `route:` | 3 个 / 23 次 | ingested(16)、topical(6)、inhaled(1) |
| `cost:` | 20 个 / 78 次 | scarce_reagent(13)、rapid_failure(7)、dosage_risk(6)、timing_window(6)、narrow_specificity(5)、short_duration(5)、consent_violation(4)、irreversible_loss(4)、social_stigma(4)、tolerance(4)、self_harm(3)、addiction(2)、aftermath_collapse(2)、equivalent_exchange(2)、fraud_risk(2)、identity_risk(2)、long_brewing(2)、reversibility_risk(2)、unreliable_output(2)、torture_adjacent(1) |
| `role:` | 11 个 / 39 次 | plot_device(7)、contraband(6)、quest_object(6)、tool(5)、taboo_marker(4)、medical_supply(3)、control_mechanism(2)、legend_tier(2)、transport_tool(2)、interrogation_tool(1)、weapon(1) |

---

## 五、硬性边界如何逐条落实

1. **不写配方**：全部 20 条的 `conditions` 均以「本文件只写来源与门槛，不写部位、配伍、剂量与炮制」收束其材料段；无一处出现可操作说明。
2. **只给维度**：`生效条件与剂量维度（只给维度）` 一段在 20 条中统一出现，列的都是维度名，无数值。
3. **历史观念 vs 项目归纳**：`historical_scope` 一律分两段写——「历史与民俗层（可引来源）」点名具体已读来源及其支持范围，「本项目设计归纳（不可引来源）」列出全部由本项目添补的部分。纯原创设定（抗魔药、水下呼吸药、增减药、隐身油）在条目内直接声明「无历史或民俗依据」。
4. **痊愈／复活／长生／万能解毒不默认成立**：`universal_antidote` 的支点就是「五条互斥解毒路径使『一味解百毒』结构上不成立」；`revivifying_elixir` 与 `longevity_elixir` 均明写「不默认成立」＋「必有不可逆代价」＋「绝不能成为消耗品」，并指出代价与例外（等价交换、时限、回来的人不再相同、继承制度失效）。
5. **每味药都写清六项**：材料来源（呼应 `western-biology.json`）、制备门槛（知识／器具／火候／施术者状态）、生效条件与剂量维度、副作用与滥用后果、谁控制供应（行会／教会／王室／黑市四家格局为默认骨架）、法律与道德处境（爱情药与真话剂、忘忧药、催眠药均标明同意问题；真话剂与抗火膏明文接酷刑／神判）。
6. **来源分层**：`access=read` 只给**真的看到正文**的 26 页；17 处失败如实登为 `unavailable` 且**零引用**（脚本已核对 `non-read referenced: []`）。

---

## 六、实际读过的来源（26 页 `read`，逐一列出支撑内容）

### 6.1 炼金术／灵药主干（5 页）

| 来源 | 实际支撑的内容（本文件引用处） |
|---|---|
| Britannica: **alchemy** | 炼金术目标含贱金属转金银与**寻找治病、延寿之法**；12 世纪拉丁欧洲开始用此词；各文化证据丰俭不均（希腊仅靠单一约八万字手稿、中国存于道藏约百部书、印度与伊斯兰从未系统汇集）；「炼金术究竟是什么」本身仍有争议 → 用于 `longevity_elixir` |
| Britannica: **philosopher's stone** | 哲人石是所求的未知物质，别称「酊剂」「粉末」；**相信可由它制出长生灵药**；关涉灵魂之完善故被认为能治病延寿；梨形坩埚（赫尔墨斯之瓶／哲人蛋）与黑→白→红的颜色次序；追求自中世纪延续至 17 世纪末并外溢为化学／冶金／药理学 → 用于 `longevity_elixir` |
| Britannica: **elixir** | elixir 指能变金之物；更完整作 **_elixir vitae_（长生灵药）**，指可无限延寿之物、被认为与哲人石相关；中国道教徒既求「不死之药」也发展内丹；药学语境下 elixir 为加甜水醇溶液 → 用于 `longevity_elixir` |
| Britannica: **immortality** | 不朽＝个人心理／精神／肉体存在的无限延续；各传统设想差异极大；「相信者众」不能证明为真；柏拉图 vs 亚里士多德 vs 伊壁鸠鲁派的分歧 → 用于 `revivifying_elixir`、`longevity_elixir` |
| Britannica: **resurrection** | 复活＝从死里起来且仍保有自身位格；肉身复活主要与基督教相联，亦见后期犹太教与伊斯兰教，琐罗亚斯德教另有终末复活；希腊罗马有灵魂不朽而无肉身复活；复活后**不是单纯复苏的尸体而是实质性转变** → 用于 `revivifying_elixir` |

### 6.2 毒／药／解毒的原理层（3 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **poison**（science/poison-biochemistry） | 毒物定义；**剂量决定性质**、「剂量足够时连水也有毒」；形态影响吸收（颗粒越小溶得越快而相对毒性越高）；有机／无机、金属／非金属的差异；帕拉塞尔苏斯提出剂量概念、Orfila 关联毒素化学与生物效应 → 用于 `clotting_draught`、`healing_unction`、`universal_antidote`、`soporific_draught`、`truth_draught`、`strength_draught`、`winter_draught` |
| Britannica: **antidote** | 解毒剂的**五条互斥作用路径**（中和／相反效应／结合阻止吸收或失活或占受体／阻断受体／中断体内转化）；可经口、静脉或经皮给药；**该条目未列任何具体药方、剂量或制备法** → 用于 `universal_antidote`（本条的核心支点）、`clotting_draught` |
| Britannica: **magic** | 魔法＝借不可见之力影响事件的思维方式；效力取决于**施术者状态与表演**；材料三分（真有效如罂粟麻醉／柳皮止痛／大蒜洋葱抗菌；本身即毒物如蟾蜍提取物；只靠象征如羊肩胛骨占卜、蜡像害人）；剂量是药与毒的分界 → 用于几乎全部条目（尤其 `healing_unction`、`soporific_draught`、`invisibility_oil`、`magic_ward_elixir`、`growth_shrink_powder`） |

### 6.3 危险与禁忌（4 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **witchcraft** | maleficium 与「害人」的核心义；近代早期（15—17 世纪）大规模巫术审判；**交感巫术**（指甲、头发、排泄物）与人偶插针；「巫能飞行」见于近代早期欧洲及北美、撒哈拉以南非洲、南亚、美拉尼西亚，欧洲有骑扫帚之说；多地变形信仰（古吉拉特 Dang 化虎、阿普列乌斯《变形记》化鸟） → 用于 `flying_unguent`、`shapeshift_draught` |
| Britannica: **witches' sabbath** | 巫魔会概念始于 14 世纪中叶、最早见于宗教裁判所记录；**「以涂抹特制油膏而能凌空赴会」这一供述说法**；会址（布罗肯峰、基辅秃山、Blocula、奥弗涅）与日期（4/30、10/31 等）；一名认罪者供称万人与会；**该条目未提供任何膏方** → 用于 `flying_unguent` |
| Britannica: **torture** | 酷刑定义与施行者；有效性自罗马时期即被批评为**促使受害者说谎**；古希腊罗马对非公民与奴隶用刑取证；中世纪早期以**神判（ordeal）本身作为审判**；中世纪后期「供词为证据之王」；苏格兰 1708／法国 1798 废除，19 世纪初欧洲多数废弃 → 用于 `truth_draught`（核心）、`ember_ward_unguent`（神判）、`flying_unguent`（供述可信度） |
| Britannica: **aphrodisiac** | 催情物两类（心理生理／内服）；**几乎无科学研究，多数著作只是民俗汇编**；未鉴定出直接生理反应物质，名声基于民俗；「形似即有力」的归因（人参根、犀角粉）；斑蝥素接触皮肤起疱、**内服作催情物被认为极其危险**；育亨宾的临床变化多归因于暗示 → 用于 `love_philtre`（核心）、`universal_antidote`（旁证：名声可完全建立在民俗与暗示上） |

### 6.4 草木（4 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **mandrake** | 茄科 Mandragora 属六种**致幻**植物；根粗大常分叉略似人形；**全株含托烷生物碱、被认为有毒**；古代作麻醉剂与**催情物**；月光下由黑狗代拔、人手不可触、拔出时尖叫杀人的**传说层**；离土后方可用于治病、**致爱**、助孕与安眠；今仍见于顺势疗法与现代巫术 → 用于 `soporific_draught`、`love_philtre`、`oblivion_draught`、`truth_draught`、`flying_unguent` |
| Britannica: **belladonna** | 颠茄（deadly nightshade）茄科灌木状草本，原产中欧南欧林地荒地；**全株剧毒**；栽培以取天仙子胺／东莨菪碱／阿托品用于镇静、兴奋、解痉；**因天然生物碱毒性与副作用才开发合成替代品** → 用于 `soporific_draught`、`truth_draught`（「效果与危险同源」） |
| Britannica: **salamander**（生物学条目） | 有尾两栖约 740 种／10 科；多居淡水与潮湿林地、北半球温带；体长 10—15 厘米，中国大鲵可长逾 1.5—2 米；幼体具外鳃、**幼态延续**；经皮肤吸水、需潮湿栖地、低温冬眠；多数成体昼伏夜出。**该条目完全不涉「火中不死」** → 用于 `ember_ward_unguent`、`growth_shrink_powder` |
| Britannica: **Circe** | 喀耳刻以变形术闻名，**借药物与咒语**把人变成狼、狮，把奥德修斯同伴变猪；其魅惑源于**草药知识**，既用于变形也用于治疗性药剂；奥德修斯依赫尔墨斯之劝先服 **moly** 而免于变形；她养着一群可能是变形者的野兽 → 用于 `shapeshift_draught`、`magic_ward_elixir` |

### 6.5 石化／隐形／庇护的母题（4 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **Medusa** | 对视者即刻化为石头；唯一有死者故可被斩；奥维德版本（本以美发著称，因波塞冬在雅典娜神庙侵犯而遭诅咒）；珀尔修斯以磨亮盾面反照而不直视；首级归雅典娜置于神盾；赫拉克勒斯得一绺同样有石化之力的头发护特革亚城；**其血右侧能活人、左侧有毒** → 用于 `petrifaction_release`、`invisibility_oil` |
| Britannica: **Gorgon** | 荷马单一戈耳工→赫西俄德三姐妹；古风艺术形貌；珀尔修斯借**哈得斯之帽（盔）隐形**逃脱；首级有使观者化石之力；gorgoneion 被广泛用作辟邪护符 → 用于 `petrifaction_release`、`invisibility_oil` |
| Britannica: **amulet** | 护符之力可来自自然力关联、宗教联系，或**在有利时辰以仪式方式制作**；天然与人造护符的类别；古埃及 MacGregor 纸草列 75 种、圣甲虫最常见；咒文后来被刻写并佩戴 → 用于 `invisibility_oil`、`magic_ward_elixir`、`love_philtre`（反制） |
| Britannica: **Lethe** | 忘川（希腊语「遗忘」）＝厄里斯之女、遗忘的化身，亦为冥府一河／平原；俄耳甫斯教：新死者饮之失掉前生全部记忆，入教者被引向 **Mnemosyne（记忆之河）** 以终结轮回；特罗福尼乌斯神谕处有 Lethe 与 Mnemosyne 两泉；阿里斯托芬《蛙》提到忘川平原；柏拉图《理想国》第十卷「无忆之河」；拉丁诗人笔下冥府五河之一 → 用于 `oblivion_draught`（核心） |

### 6.6 战士／再生／变形（5 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **berserker** | 崇拜奥丁的桀骜战士团，受雇为卫队与突击队；兽皮装束与凶暴促成欧洲狼人传说；**披兽皮或赤膊两说并存**；在东道社群随意奸杀（即「发狂」），萨迦中常作反派；9 世纪古诺斯诗歌记其为金发哈拉尔一世亲卫 → 用于 `berserk_draught`（核心）、`strength_draught` |
| Britannica: **Odin** | 塔西佗记条顿人拜墨丘利、dies Mercurii 与 Wednesday（Woden）相合；早期为战神、英雄保护者、阵亡者入瓦尔哈拉；**狼与渡鸦归于他**；八足斯莱普尼尔能驰过空中与海上、齿刻鲁纳；奥丁是诸神中的大魔法师并与鲁纳相联；独眼（一眼换智慧） → 用于 `berserk_draught` |
| Britannica: **Valhalla** | 阵亡战士之殿，盾为顶；每日食一头被宰后**每晚又完复如初的野猪**；每日互相厮杀为其乐事；活到 Ragnarök 时从 540 道门出战；奥丁需要他们 → 用于 `berserk_draught`、`revivifying_elixir`（**明确标注：再生母题，不是可复制的药剂机制**） |
| Britannica: **werewolf** | 变形为狼或狼人混合形态；成因含诅咒、被同类咬伤、饮狼爪印水、新月受孕、与魔鬼立约、**魔法斗篷或狼皮腰带**；古希腊「食狼肉混人肉不可逆变狼」；罗马称 versipellis；16 世纪法国数名男子自称持**可变狼的魔法油膏**而遭火刑；1589 年 Peter Stubbe 在**酷刑下**供称持变形腰带；另说以驱魔、放血、催吐或饮醋「治愈」 → 用于 `shapeshift_draught`（核心）、`berserk_draught` |
| Britannica: **Proteus** | 海上老者与海畜牧者；知过去现在未来却不愿吐露；欲问者须在其正午睡时突袭并缚住；**即便被捉仍化作各种形状，若捉者握紧不放才恢复本形并作答**；protean 一词源此 → 用于 `shapeshift_draught`（强制回归条件）、`water_breathing_draught`（立约结构） |

### 6.7 医神（1 页）

| 来源 | 支撑内容 |
|---|---|
| Britannica: **Asclepius** | 医神，阿波罗之子，喀戎授医术；**宙斯因怕他使所有人不死而以雷霆击杀他**；崇拜起于色萨利，埃皮达鲁斯睡祷治病；前 293 年传入罗马；缠蛇之杖是唯一真正的医学象征，商神杖与之无关 → 用于 `revivifying_elixir`、`longevity_elixir`（「使人不死必遭天罚」＝必有代价的母题依据） |

### 6.8 抓取失败、如实登记为 `unavailable`（17 处，**零引用**，脚本已核）

`theriac` 404、`panacea` 404、`philtre` 404、`love potion` 404、`truth serum` 404、`mithridatium` 404、`topic/poison` 404（改由 science/poison-biochemistry 取得）、`invisibility` 404、`homunculus` 404、`nepenthe` 404、`moly` 404、`Heimdall` 404、`salamander-mythology` 404；Met Museum `toah/hd/alch` 与 `toah/hd/alcm` 均 404；World History Encyclopedia `alchemy` 传输层失败（malformed HTTP response）；Wikipedia `Theriac` 与 `Love potion` 连接超时。

**这些失败直接造成了本文件的三个已知缺口**：万应解毒剂（theriac）、爱情药（philtre）、真话剂（truth serum）三条都没有独立词条正文，相关段落只能靠邻近条目（antidote / aphrodisiac / torture）旁证，并已在条目内逐处标明。**方法学局限也如实记录**：本轮通用网页搜索对英文母题词的召回质量很差（把 Britannica、elixir、World History、love、flying 等当作导航词与词典条目返回），因此改为直接指定已知 Britannica 条目地址抓取正文。

---

## 七、验证结果（用**未改动**的 `app.encyclopedia.import_file`，一次性临时库）

脚本：`temp://scratch/verify_alc.py`（临时库建于系统 temp 目录，验证后已删除；**工作区未新增任何数据库文件**）。

```
DETAIL_SECTIONS: ['definition', 'mechanism', 'conditions', 'exceptions',
                  'story_uses', 'historical_scope', 'evidence_and_uncertainty']
elements: 20   sources: 43
PROBLEMS: none

sources read: 26   unavailable: 17
unreferenced sources: 17 项（全部为 unavailable，本就不得被引用）
non-read referenced: []

adapters: human-encyclopedia
IMPORT1: {"group_id":"western-alchemy","adapter":"human-encyclopedia","idempotent":false,
          "elements":20,"element_versions_written":20,"unchanged_elements":0,
          "sources":43,"source_versions_written":43,"unchanged_sources":0,
          "relations":0,"unresolved_relations":[],"ambiguous_relations":[],
          "shared_element_ids":[]}
IMPORT2: {"group_id":"western-alchemy","adapter":"human-encyclopedia","idempotent":true,
          "elements":20,"element_versions_written":0,"unchanged_elements":20,
          "sources":43,"source_versions_written":0,"unchanged_sources":43,
          "relations":0,"unresolved_relations":[],"ambiguous_relations":[]}

SEARCH tags_any=[effect:healing]                        -> 2
SEARCH tags_all=[kind:item, tradition:western, role:legend_tier] -> 2
SEARCH text="真话剂"                                     -> 1
EXPORT bytes: 191469   TMPDB removed: True
```

| 检查项 | 结果 |
|---|---|
| adapter 自动识别 | ✅ `human-encyclopedia`（未传 adapter 参数） |
| 导入条数 | ✅ 元素 20 / 来源 43，全部版本写入成功 |
| 未解析关联 / 歧义关联 | ✅ 0 / 0（本组无 `related_ids`、无 `related_catalog_ids`） |
| 跨命名空间同名 | ✅ `shared_element_ids: []` |
| 标签可检索 | ✅ `effect:`、组合 `tags_all`、中文名子串三种检索均命中 |
| 复导幂等 | ✅ 第二次 `idempotent: true`，`element_versions_written: 0`、`unchanged_elements: 20` |
| `details` 七节齐备、全为字符串、无多余键 | ✅ 20/20（脚本逐条比对 `DETAIL_SECTIONS` 顺序与类型） |
| `category=item` / `needs_review` / `needs_detail` | ✅ 20/20 |
| 每条含 `kind:item` + `tradition:western` | ✅ 20/20 |
| 手写 `genre:` / `category:` 标签 | ✅ 0 |
| `source_ids` 悬空 / 引用非 `read` 来源 | ✅ 0 / 0 |
| 文件编码 | ✅ UTF-8 无 BOM |

---

## 八、边界声明

1. **只新增两个文件**：`docs/element-catalog/western-alchemy.json` 与 `.md`。未改 `collection-spec.md`、`README.md`、`western.json` / `.md`、`western-biology.json` / `.md`、任何源码、任何故事包或数据库；未建实际库；未改 CLI；未装依赖；未启动服务；未触碰 Terragenesis 与地图／故事／玩家数据。
2. 临时验证库建在系统 temp 目录并在验证后删除，工作区无残留。
3. 本项目立场（如「爱情药在道德上恒等于人身侵夺」「万应解毒剂不成立」「复活默认不成立」）均标为**本项目设计归纳／立场**，不冒充历史结论，也不要求其他作品遵守，只作为本文件使用口径下的默认前提。

---

## 九、仍需主审裁定的点（采集侧不能自行决定）

1. **条目数取 20 还是压到 18**：题目允许 18—20，我按 20 交，因为「治疗／止血」被拆成内服与外敷两条（`clotting_draught` / `healing_unction` 分工明确、不可互换），「力量／狂战」也拆成两条（前者改力气、后者改判断力）。若主审认为这属于凑数，可把 `healing_unction` 与 `strength_draught` 降为附录或合并，压到 18。
2. **`magic_ward_elixir`（抗魔药）是全组唯一**完全没有**历史／民俗依据**的条目（已读来源中最近的只有「护符赋力」与「材料三分」）。保留它可以补齐题材清单，但它实质上是对世界魔法规则的一次**立法**。请裁：保留 / 降为附录 / 删除。
3. **「宣称型」这一写法是否越界**：`universal_antidote` 与 `love_philtre` 都采取「先否定效力、再写社会后果」的结构（前者说万能不成立，后者说致爱不成立）。若主审希望候选资料保持更中立的描述语气，这两条需要改写。
4. **三处来源缺口的处置**：theriac / philtre / truth serum 三条 404，使万应解毒剂、爱情药、真话剂**没有独立词条正文**。可选：(a) 维持现状（已逐处标注缺口）；(b) 主审另批一次取源预算，用博物馆／大学数据库或纸本参考补证；(c) 把这三条整体降为 `summary_only`。
5. **「火中蝾螈」母题的归属**：`salamander-mythology` 404、生物学条目完全不涉，因此我在 `ember_ward_unguent` 里把它明确写成「有此一说而未取得来源」。若主审认为该母题的证据其实充分（例如可在别处取到），本条的抗火材料段可以写实一档。
6. **`role:` 标签的粒度**：目前 `role:` 用了 11 个值、`cost:` 用了 20 个值，偏细。若后续要与 `western.json` / `western-biology.json` 的 role 词表统一（那两份的 role 值更少），需要一次批量收敛——本轮未擅自改动其他组的词表。
7. **`route:inhaled` 只用了 1 次**（催眠安神药的烟熏用法）。若烟雾／熏香路线后续要展开（如熏香型真话剂、迷香型隐身），建议在开局绑定阶段显式列出，因为它与「投递方式」这一整套社会设定直接相关。
8. **与 `western.json` 四条主干条目的重复度**：我已刻意只写用途分型、框架部分用文字指向，但 `universal_antidote`（解毒机制）与 `western_alchemy`／`western_arcanic_material` 仍有概念交叠。请主审确认这个交叠度可接受，还是需要在 `shared-themes.json` 里加一条聚类标注（本轮未改该文件）。
