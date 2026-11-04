# 现实基础库 · 西方传统草药（reality-herbs-western）

对应 [reality-herbs-western.json](reality-herbs-western.json)。状态：**候选资料**（`status: candidate`, `schema_version: 1`），全部条目 `review_status: needs_review` / `detail_status: needs_detail`。不是数据库实现，也不是任何故事包已采纳的设定。

规范见 [collection-spec.md](collection-spec.md)（第 62—68 行「现实基础库」一节与「不提供医疗处方」一句）。本页只做扫读索引、来源与限制说明，**完整内容以 JSON 为准**，此处不复制正文。

- 元素 **38** 条；来源 **65** 条（`read` 57 / `unavailable` 8 / `search_only` 0）
- 题材标签统一 `real_world`，分组 `reality-herbs-western`，条目 ID 前缀 `herb_west_`
- `knowledge_kind`：historical 24、mixed 14（无 empirical、无 belief_description）
- 全部条目的 `details` 七节齐备且非空（`definition` / `mechanism` / `conditions` / `exceptions` / `story_uses` / `historical_scope` / `evidence_and_uncertainty`），合计约 7 万字符
- 每条 `details` 内均明写「**本条为文献与设定资料，不构成医疗建议，不可据此用药**」

## 一、这个文件在收什么

用户要求补「西方传统草药（西方草药学／民间药材）」候选资料。取舍标准是「它能否给人物行动、世界构建或事件因果设定代价与约束」，而不是做一份药材百科：

- **常见香草的药用层**：鼠尾草、迷迭香、百里香、牛至、罗勒、洋甘菊、薄荷类、莳萝、欧芹、月桂、杜松、薰衣草
- **英美草药学代表**：圣约翰草、紫锥菊、缬草、药蜀葵、毛蕊花、聚合草、荨麻、接骨木、蓍草、金盏花、小白菊、菊蒿、牛蒡、菊苣、琉璃苣、甘草、神香草、苦薄荷、柠檬香蜂草、欧白芷、人参属（含西洋参）
- **强毒或受管制**：毛地黄、乌头、颠茄、毒芹、苦艾

**刻意不做的**：不写剂量、配伍比例、煎煮温度与时长、酊剂浓度、服用方法、疗程、频次、适应症指导，不出现「可治某病」式表述；有毒条目只写毒性成分类别与误用后果的定性风险，以及历史上中毒与致死的教训，**不写减毒、安全用量、解毒或抢救方法**。

## 二、扫读表

「知识类型」：his=historical 史学与文献记述，mix=机制/植物学事实＋历史记述混合。

| ID | 名称 | 主要部位 | 类型 | 一句话要点 | 主要限制 |
|---|---|---|---|---|---|
| herb_west_sage | 鼠尾草 | 叶 | his | 制药圃与家圃之间最家常的一味 | 属内多个种同称 sage；「强记益智」是信念 |
| herb_west_rosemary | 迷迭香 | 叶/花 | mix | 调味、焚香与「记忆」象征三重身份 | 2017 年改属，两个学名并存；焚香≠消毒 |
| herb_west_thyme | 百里香 | 地上部 | his | 有古典文本线索的少数香草之一 | 属内多名；体外活性≠疗效 |
| herb_west_oregano | 牛至 | 叶/花 | his | 婚礼与祭墓用同一株草 | 墨西哥牛至属马鞭草科，不同科 |
| herb_west_basil | 罗勒 | 叶 | his | 极不耐霜的「娇气移民」 | 可能原产印度；与亚洲罗勒类不可互替 |
| herb_west_chamomile | 洋甘菊 | 花 | his | 罗马与德国两种洋甘菊共用一个商品名 | 商品名≠物种名；属内百余种混充 |
| herb_west_mint | 薄荷类（欧薄荷与留兰香） | 叶/花 | his | 欧薄荷本身是杂交种，靠营养繁殖 | 两种薄荷不可互换；精油≠鲜叶 |
| herb_west_dill | 莳萝 | 籽/叶 | his | 「籽」其实是干果；伞形科误采风险 | 与葛缕子、茴香易混；与毒芹同形 |
| herb_west_parsley | 欧芹 | 叶/根/籽 | mix | 最被当作无害配菜，而籽油有严重风险 | 与芫荽、毒芹混淆；风险句只作定性 |
| herb_west_bay_laurel | 月桂 | 叶 | his | 少数来自木本的香草；干叶耐储即议价权 | 三种「bay」；月桂冠传说无本条来源 |
| herb_west_juniper | 杜松 | 球果/木叶 | mix | 果进酒桶、木进橱柜、叶进香水 | 「杜松子」是球果不是浆果 |
| herb_west_lavender | 薰衣草 | 花 | his | 干花、花油、穗油三条技术线 | 花油与穗油价格差是掺伪入口 |
| herb_west_st_johns_wort | 圣约翰草 | 地上部 | mix | 草药、牧畜毒草、入侵种三重身份 | 只有有限临床证据；药物相互作用真实存在 |
| herb_west_echinacea | 紫锥菊 | 根/地上部 | mix | 美洲药材进入西方草药学的代表 | 新大陆植物，不得放进中世纪药圃 |
| herb_west_valerian | 缬草 | 根 | his | 一根两用：药材与香料代用品 | 分类由独立科改为亚科；摘要级来源 |
| herb_west_marsh_mallow | 药蜀葵 | 根/叶 | his | 棉花糖原本是用它的根做的 | 与蜀葵不同种；现代糖果已无此植物 |
| herb_west_mullein | 毛蕊花 | 花/叶 | his | 一株毛蕊花就是一处扰动的记录 | 引火/灯芯用法标为待核 |
| herb_west_comfrey | 聚合草 | 叶/根 | mix | 民间「接骨」之名 vs 现代肝损伤记录 | 不得因「用了数百年」省略风险 |
| herb_west_nettle | 荨麻 | 叶/根 | mix | 一根草养活野菜、饲料、纺织、草药四行 | 刺伤可致 12 小时皮疹，犬类有致死记录 |
| herb_west_elder | 接骨木 | 花/果/皮 | his | 花、蕾、果、汁各有用处的四季加工链 | **果需煮熟**；S. nigra 分类有争议 |
| herb_west_yarrow | 蓍草 | 地上部 | his | 止血草、茶料、占卜用具三职一身 | 阿喀琉斯传说无本条来源；三职不可混证 |
| herb_west_pot_marigold | 金盏花 | 花 | his | 能吃、能抹、能卖三件事同时成立 | 与万寿菊属混称；主要为观赏栽培 |
| herb_west_feverfew | 小白菊 | 叶/花 | his | 「退热」之名与研究方向错位 | 三个 feverfew 是三种植物 |
| herb_west_tansy | 菊蒿 | 叶/花 | his | 同属既是药草又是杀虫原料 | 属级属性不可套到种上 |
| herb_west_burdock | 牛蒡 | 根/叶 | his | 同一种植物在两个大陆两种身份 | 北美杂草、亚洲蔬菜，须交代地点 |
| herb_west_chicory | 菊苣 | 根/叶 | his | 替代品经济的典型：断供与乡愁 | 掺配不是替代；软化栽培需地窖或温室 |
| herb_west_licorice | 甘草（欧甘草） | 根 | his | 掩味剂决定了药能不能被咽下去 | 掩味≠治病；与茴香不同科 |
| herb_west_ginseng | 人参属（含西洋参） | 根 | mix | 慢生＋高值＋整株采挖＝野生压力 | 过度采挖、多州与联邦严格管制；名录等级缺口已标注 |
| herb_west_foxglove | 毛地黄（洋地黄） | 叶/全株 | mix | 观赏植物与剧毒植物是同一株 | 全株含强心苷；只写风险不写任何用法 |
| herb_west_monkshood | 乌头 | 根/全株 | mix | 刑具与药是同一种植物 | 全属剧毒；aconite 一名跨两属 |
| herb_west_belladonna | 颠茄 | 全株 | mix | 甜而光亮的黑果是误食主因 | 剧毒；污名可转移到人 |
| herb_west_poison_hemlock | 毒芹 | 全株 | mix | 苏格拉底之杯；与食用伞形科同形 | 全株含 coniine；脉序鉴别≠采集许可 |
| herb_west_wormwood | 苦艾 | 叶/地上部 | mix | 一个名字、一种饮料、一场道德恐慌 | 三个种三种命运；青蒿素与苦艾酒无关 |
| herb_west_borage | 琉璃苣 | 叶/花 | his | 酒杯里的一片叶 | 「勇气」象征无来源，标为母题 |
| herb_west_hyssop | 神香草 | 叶/花 | his | 圣经 hyssop 不是这一种 | 三种「hyssop」并存；hedge hyssop 属车前科 |
| herb_west_horehound | 苦薄荷 | 叶/花 | his | 掺伪：黑苦薄荷冒充白苦薄荷提取物 | 黑白两种同科不同属 |
| herb_west_lemon_balm | 柠檬香蜂草 | 叶 | his | 「balm」是一大批跨科植物共用的名字 | 名字混乱的极致案例 |
| herb_west_angelica | 欧白芷 | 根/果/叶 | mix | 身份不确定就不应食用 | 与毒芹同形；含呋喃香豆素可致光皮炎 |

## 三、与已有条目的重合清单（重要，交主代理合并）

以下物种**已在库中出现**，本组**未重复立条**，只在此列出「本来打算补的药用或食用信息」，供主代理合并进已有元素：

| # | 已有组名 | 已有元素 id | 现有 name | 本想补的药用／食用信息一句话摘要 |
|---|---|---|---|---|
| 1 | flavors | `flavors_fennel_seed` | 茴香籽 | 伞形科茴香的**草药学层**：古典与近代文献记其被用于驱风与助消化，且「同株叶是香草、籽是香料」这层分工在药房与厨房同时成立 |
| 2 | staples | `staples_flax` | 亚麻 | **亚麻籽（flaxseed）在欧美草药学中的传统**：被用作润滑性缓和剂与外部糊剂的历史记述；注意食用与工业亚麻仁油须分开，与现有「籽油易酸败」一条衔接 |
| 3 | produce | `produce_garlic` | 大蒜 | **古代与中世纪的药用身份**：现有条目只写「既作调味也作药用」，可补「古典本草与修道院药圃把它列为常备」这一层 |
| 4 | produce | `produce_onion` | 洋葱 | **历史上的药用身份**：现有条目已记「埃及视球状鳞茎为宇宙象征、罗马人将其带入不列颠」，可补「古希腊罗马与中世纪本草把它列为药用鳞茎」这一层（与大蒜条目同源） |
| 5 | western-biology | `western_bio_hawthorn` | 山楂与活篱役 | **山楂果的草药学传统**：近代欧洲草药文献记其被用于心脏相关不适（现条目只写生态与活篱役，无药用层） |
| 6 | western-biology | `western_bio_yew` | 紫杉与弓材禁伐林 | **毒性部位与误用史**：叶与种子（不含假种皮）含毒生物碱、对家畜有致死记录；树皮提取物属现代药物学，不作现成疗法 |
| 7 | western-biology | `western_bio_willow` | 柳与割条轮休 | **水杨苷的止痛传统**：柳皮在民间被用于退热止痛的历史记述（现条目只提「水杨苷取自某些柳树」） |
| 8 | western-biology | `western_bio_mistletoe` | 槲寄生与除治义务 | **「曾被认有药效」这一层**：现有条目已有该句，可补其与圣诞民俗、与寄主树木（苹果、杨、柳、山楂）的关系更完整表述 |
| 9 | western-biology | `western_bio_mandrake` | 曼德拉草与人形根圃 | **古代麻醉与催情用途的定性记述**（现条目已有，可核对是否足以支撑「麻醉剂」一词的分量） |
| 10 | western-biology | `western_bio_fern` | 蕨丛与弃耕标记 | **不合并**：本想补「绵马一类蕨的驱虫史」，但**本轮未取得任何来源**，不建议写入（见第五节待补项） |
| 11 | western-biology | `western_bio_mushroom_ring` | 蘑菇与仙环标尺 | **毒蕈误认与中毒冤案**一条线（现条目已写得极完整，本组无新增） |
| 12 | western-biology | `western_bio_oak` / `western_bio_ash_wood` | 橡树与界树诉讼 / 白蜡木与材种专供 | 本想补「树皮含单宁用于鞣革与收敛性外用的传统」，属**工艺与药学交叉**，建议并入现有条目而非立草药条 |

**两处需主审裁定的关系（非重复，但属跨文件归属问题）**：

1. **毛地黄**：本组新立 `herb_west_foxglove`。但 `western.json` 的妖精条目已提到「山楂、毛地黄、千里光为其所爱且破坏遭报复」，`western-biology.json` 亦有 `western_bio_src_britannica_hawthorn` 一处提到这类民俗。此处不是同名元素重复，而是**同一物种跨三个文件出现**，请主审决定是否需要在 western.json 妖精条目里加一条文字指向本文件。
2. **乌头**：`western-biology.json` 明确记载「monkshood 条目返回 HTTP 403，**本文件因此不设独立的乌头属毒草条目**，避免以未读来源支撑断言」（见其 `western_bio_src_monkshood_403`）。本轮成功读到 Britannica monkshood 与 aconite 正文，因此本组新立 `herb_west_monkshood`，**填补 western-biology 当年留下的缺口**。请主审裁定：是保留在本组，还是迁入 western-biology 与该文件既有的 `kind:flora` 体系并列。

## 四、本轮实际读过并支撑正文的来源（57 条 read）

全部为 Encyclopaedia Britannica 条目（另加 1 条大学推广站数据库页），2026-10-31 当场逐页抓取。以下按支撑面归类（详细 `supports` 见 JSON 的 `sources`）：

**本草史与制度框架**：herbal（本草文献史、图像程式化与「形象学说」）、Pedanius Dioscorides（《药物论》的地位与范围）、pharmacopoeia（药典与「标准即约束」）、apothecary（药剂师与杂货商分离、1841 年药学学会）、phytotherapy（草药学 vs 植物疗法、标准化、聚合草与卡瓦致肝损伤）、history of medicine（只读至古代埃及一节：草药起源、超自然病因观、安慰剂效应）、medicinal plant、herb（香草与香料的分界）、Nicholas Culpeper（仅得旁及段落：1649 年伪科学药典）、monasticism（修道院的自给园艺与医疗功能）、witchcraft（毒草污名与指控机制的社会史框架）。

**香草类**：sage、rosemary、thyme、oregano、basil、chamomile、dill、parsley、bay tree、juniper、lavender、peppermint、spearmint、hyssop、horehound、balm、angelica、borage、licorice、marsh mallow、elderberry、yarrow、wormwood、mugwort。

**英美草药学代表**：Hypericum（属）、common Saint-John's-wort（摘要页）、echinacea（摘要页）、coneflower、common valerian（摘要页）、Valerianoideae、Dipsacales、comfrey、stinging nettle、pot marigold（摘要页）、feverfew（摘要页）、tansy、burdock、chicory、ginseng。

**强毒**：foxglove、monkshood、aconite、belladonna、poison hemlock、hemlock（Tsuga 条，用于同名异物）。

**采集限制与保护状态**：`Panax quinquefolius — NC State Extension Plant Toolbox`（大学推广站植物数据库）。这是本轮**唯一**取得保护状态信息的来源，支撑「因作为草药之受欢迎而被过度采挖、现于许多州与联邦层面受到严格管制」这一层；其详细形态、生境、分布与物候亦一并采用。

**摘要级警示（站方明言该主题无全文条目）**：`herb`、`apothecary`、`echinacea`、`common Saint-John's-wort`、`common valerian`、`pot marigold`、`feverfew`、`medicinal plant`、`mugwort` 共 9 条。这些来源只作补充性核对，条目内已逐条标注「摘要级」，未据其写细节性断言。

## 五、抓取失败并如实登记（8 条 unavailable，零引用）

| id | 地址 | 结果 | 后果 |
|---|---|---|---|
| `herb_west_src_unavail_valerian_pages` | /plant/valerian-plant、/plant/valerian | HTTP 404 ×2 | 缬草条目改由两个摘要/正文混合源支撑，已在条目内标注 |
| `herb_west_src_unavail_thyme_mint_pages` | /plant/thyme-plant、/plant/mint | HTTP 404 ×2 | 百里香改由 /plant/thyme，薄荷改由 peppermint + spearmint |
| `herb_west_src_unavail_coltsfoot_family` | coltsfoot、meadowsweet、plantain、lady's-mantle | HTTP 404 ×4 | **款冬、绣线菊、车前、斗篷草四条未立** |
| `herb_west_src_unavail_elecampane` | /plant/elecampane | HTTP 403（反爬拦截页） | **土木香未立** |
| `herb_west_src_unavail_dandelion` | /plant/dandelion | 正文抽取失败（extracted body has been duplicated） | **蒲公英未立** |
| `herb_west_src_unavail_ginseng_protection` | fs.usda.gov ×2、cites.org、iucnredlist.org、powo.science.kew.org、plants.usda.gov、missouribotanicalgarden.org | 403 ×2、超时 ×1、404 ×1、403 ×1、仅抽取到站名、仅抽取到导航页脚 | 保护状态**只采用 NC State Extension 那一层表述**，不写 IUCN 等级与 CITES 附录编号 |
| `herb_west_src_unavail_wikipedia` | en.wikipedia.org 多页 | 连接超时（dial tcp 失败） | 本文件**不含任何维基百科内容** |
| `herb_west_src_unavail_chelsea` | chelseaphysicgarden.co.uk/history/ | HTTP/2 PROTOCOL_ERROR | 药圃制度史改由 Britannica 已读条目支撑，未引该站任何内容 |

按用户要求「约 35 条，不硬凑」：本轮交出 **38 条**。缺的 4 条（款冬、绣线菊、车前、斗篷草）与土木香、蒲公英共 6 条，**因来源抓取失败而未立**，不以无源内容补足。

## 六、安全边界（本组的硬限制）

1. **不提供任何可执行医药信息**：无剂量（克/两/钱/滴数）、无配伍比例、无煎煮温度与时长、无酊剂浓度、无服用方法、无疗程、无频次、无适应症指导。
2. **传统用途一律写成文献记述**：用「草药学传统中记其用于……（文献记述，非医疗建议）」的句式，不写「可治某病」。
3. **每条明写**「本条为文献与设定资料，不构成医疗建议，不可据此用药」——已用脚本逐条核验，38/38 均在。
4. **有毒条目只写类别与教训**：毛地黄（强心苷）、乌头（aconitine）、颠茄（托烷生物碱）、毒芹（coniine）、苦艾（苦味与「安全性与效力未知」）只写毒性成分类别、误用后果的定性风险与历史上中毒致死的教训，**绝不写减毒、安全用量、解毒或抢救方法**。
5. **采集限制与保护状态**：人参属条目明确写出「因作为草药之受欢迎而被过度采挖，现于许多州与联邦层面受到严格管制」，并**显式标注具体名录等级（IUCN／CITES 附录编号）与各州配额的取证缺口**，引用时不得升级。
6. **不写仪式步骤**：涉及猎巫、辟邪、占卜的内容只作社会史与民俗层描述，不给任何可照做的流程或护符制作法。

## 七、临时库验证（用未改动的 `app.encyclopedia.import_file`）

在 `temp://scratch/` 下建一次性库 `herbs_test.db`，**未改动 app 代码、未建正式库、未改 CLI**：

```
adapter            = human-encyclopedia
namespace/group_id = reality-herbs-western
第一次导入：elements 38, element_versions_written 38, sources 65, source_versions_written 65
            relations 0, unresolved_relations [], ambiguous_relations [], shared_element_ids []
第二次导入：idempotent=True, element_versions_written 0, unchanged_elements 38
标签检索：kind:herb 38 / tradition:western 38 / trait:toxic 4 / role:domestic_remedy 26
          trade:apothecary_commodity 14 / part:root 14 / part:leaf 28 / part:flower 17
          part:seed 6 / part:bark 1 / trait:invasive 4 / role:poison_lore 4
组合检索 kind:herb AND trait:toxic = 4（颠茄、毛地黄、乌头、毒芹）
七节完整性：缺失 0 条（38/38 均七节非空）
状态：needs_review 38、detail_status needs_detail 38（无一条标 reviewed_detail）
未解析关联 0、歧义关联 0
```

## 八、已知弱项与待裁定点

1. **9 条来源为「策展摘要页」**（站方明言无全文条目）。涉及缬草、紫锥菊、小白菊、金盏花、蓍草所用的一处补充、艾蒿、香草概念、药剂师、药用植物。这些条目的细节深度因此低于其他条目，`detail_status` 一律保持 `needs_detail`。
2. **保护状态的层级缺口**：人参属条目已取得「过度采挖＋多州及联邦严格管制」这一层（NC State Extension），但**具体名录等级（IUCN／CITES 附录编号）与各州配额未取得**——七个保护类页面的抓取全部失败（见第五节）。引用时不得升级为具体等级。
3. **维基百科本轮完全不可达**，因此除人参的保护状态一条外，其余事实断言均为单一 Britannica 口径，没有交叉印证的第二来源。这是本组最实质的方法学局限。
4. **毛地黄与乌头的跨文件归属**需主审裁定（见第三节末尾）。
5. **两处「待核」已如实标注**：毛蕊花的引火/灯芯民间用法、鼠尾草的侧柏酮安全性——两者均未取证，条目内已标为待核而非事实。
6. 建议后续补的 6 条（款冬、绣线菊、车前、斗篷草、土木香、蒲公英）需先解决抓取路径问题（换 Britannica 别名地址、或改用大学植物园／博物馆的植物志页面）。
