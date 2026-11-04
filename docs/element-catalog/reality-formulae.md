# 现实基础库·现实经典方剂（方书条目）（reality-formulae 组）

对应 `reality-formulae.json`。状态：**候选资料**，不是数据库记录，也没有被任何故事包采纳为正典。

> **本条为文献与设定资料，不构成医疗建议，不可据此配制或服用。**

## 零、安全边界（先读这一节）

本组把方剂当作**文献现象与文化史对象**收录，不当作可照抄的处方。全组遵守以下硬约束，违反即须返工：

1. **只列药味名称，不写剂量**。不出现任何剂量、比例、重量、枚数、克数、钱数、升合之数。
2. **不写操作**。不写煎煮温度与时长、先煎后下次序、服用方法与频次、疗程、将息护理的具体做法。
3. **不写主治、不写适应症指导**。典籍功用若必须提及，一律改写为「《某书》原文列此方用于某类证候（历史文献记述，不构成诊疗建议，且此类辨证须由执业中医师判断）」的句式；不写「某方治某病」、不写「某方最有效」「某方可替代某治疗」。
4. **涉及毒性药味的条目**（附子、细辛、朱砂、雄黄、半夏、蜀椒等）在 summary、details.definition 与 exceptions 三处明写「含毒性药味，误用可致严重后果」，**不写任何减毒、炮制、解毒或替代方法**。
5. 每条 `details.definition` 与本文顶部都带同一句免责声明。

因此本组**不能**当作方剂学教材、药品说明书、药典摘录使用。它回答的问题是「这首方在历史与文本中是什么」，不是「这首方怎么用」。

## 一、口径说明（tradition 标签为什么是 eastern）

- 顶层 `genres: ["real_world"]`，与 `reality-human` / `reality-physical` 两个现实分区一致。
- 每条 `tags` 里放的是 `tradition:eastern`，**一条一个，不混用**：本组全部 35 首方都属中国传统医学方书系统，没有一首需要 `tradition:western`。此处的 `tradition` 指**方剂所属的文献传统（汉文方书系统）**，不是题材标签，也不表示把它当「东方玄幻」素材。
- `genre:` / `category:` 由导入器生成（`category=item` → `category:item`；`genres` → `genre:real_world`），本组**不手写**这两个前缀。
- `category` 统一为 `item`：在元素库里，一首方是一个可被记载、引用、交易、假冒的「物」，而不是一套制度或能力。

## 二、规模与构成

- 共 **35 项**元素，ID 前缀 `formula_`；全部 `detail_status: "needs_detail"`、`review_status: "needs_review"`。
- 来源 **60 条**：`access: "read"` **49 条**、`unavailable` **11 条**（失败如实记录，**零引用**，未出现在任何元素的 `source_ids` 里）。
- `knowledge_kind` 分布：`historical` 26、`mixed` 9。
- 每条含：`id / name / aliases / summary / category / tags / details`（七节全部非空字符串）/ `source_ids / knowledge_kind / review_status / detail_status`。

七节对应 `app.encyclopedia.DETAIL_SECTIONS`：`definition`（定义与出处）→ `mechanism`（组成与配伍结构，只用君臣佐使，不给量）→ `conditions`（适用记载的历史语境与剂型）→ `exceptions`（例外、加减、同名异方）→ `story_uses`（社会史与剧情用途）→ `historical_scope`（时代地域限定与改编边界）→ `evidence_and_uncertainty`（证据分层与不确定性）。

## 三、来源（49 条 read / 11 条 unavailable）

实际打开并读到正文的 49 页，可分为四类：

| 类型 | 代表页面 | 提供了什么 |
|---|---|---|
| 外部百科（英文） | Britannica：traditional Chinese medicine、Zhang Zhongjing、Treatise on Febrile and Other Diseases、aconite、ephedrine | 张仲景与《伤寒杂病论》的年代与二书分合；《本草纲目》载药 1892 种、成方约 11000 首；药铺柜屉的形态；乌头属为有毒植物；麻黄碱的现代药物史 |
| 政府／机构科普 | NCCIH《Traditional Chinese Medicine: What You Need To Know》 | 现代证据分层（复方研究质量参差、无法定论）与安全事实（重金属、农药、抓错药材可致器官损害） |
| 古籍书目页 | 古诗文网《伤寒论》 | 十卷、3 世纪初成书、二十余篇篇目结构，用于定位方剂的篇第归属 |
| 中文百科（方剂与方书条目） | 麻黄汤、桂枝汤、大青龙汤、小柴胡汤、半夏泻心汤、大承气汤、四逆汤、理中丸、五苓散、四君子汤、四物汤、六味地黄丸、金匮肾气丸、乌梅丸、独活寄生汤、逍遥散、补中益气汤、归脾汤、平胃散、二陈汤、藿香正气散、龙胆泻肝汤、黄连解毒汤、白虎汤、银翘散、桑菊饮、安宫牛黄丸、苏合香丸、失笑散、血府逐瘀汤、桃红四物汤、玉屏风散、生脉散、八珍汤（同名戏曲）、太平惠民和剂局方、温病条辨、医林改错、串雅、小儿药证直诀、备急千金要方、同仁堂 | 药味名单、君臣佐使结构、方族与合方关系、原文主治段、历史沿革与制度（局方、CITES、非遗） |

**失败并如实标注的 11 条**（`access: unavailable`，正文写明失败原因，零引用）：

- 中文／英文维基百科（`zh.wikipedia.org`、`en.wikipedia.org`）：连接超时/失败。因此本组**不声称读过任何维基百科条目**，也就不满足「至少读过一个维基页面」这一条——以 Britannica 与机构页替代。
- ctext.org《伤寒论》全文、墨书院《伤寒论》全文：均连接失败。**故本组不逐字引用任何《伤寒论》条文**，所有条文层面的表述都只到「该篇载有此类条款」为止。
- 苏合香丸、失笑散、炙甘草汤、温疫论、太平惠民局、本草纲目（百度百科）：HTTP 403 / 404。其中前三条直接影响药味清单的可溯源性（后以 `/0` 路径补读成功两条，炙甘草汤始终未取得）。
- WHO 传统医学 fact sheet、NCBI Bookshelf、FDA 马兜铃酸页：连接失败 / 验证拦截 / 404。这使乌头类毒理与马兜铃酸—木通关系的**独立权威支撑缺失**，相关处只写到「有毒性／存疑待核实」。

## 四、35 首方与出处（按主要典籍分块）

### 4.1 《伤寒论》系统（12 首）

| ID | 方名 | 典籍依据（主要） | 方族/加减 | 标记 |
|---|---|---|---|---|
| `formula_mahuangtang` | 麻黄汤 | 《伤寒论·辨太阳病》 | 麻黄加术汤、麻杏苡甘汤、大青龙、三拗汤、华盖散 | contains_active_alkaloid |
| `formula_guizhitang` | 桂枝汤 | 《伤寒论·辨太阳病》 | 桂枝加葛根/厚朴杏子/桂/芍药汤 | — |
| `formula_daqinglongtang` | 大青龙汤 | 《伤寒论》 | 与麻黄汤、小青龙互为参照 | contains_active_alkaloid、mineral_herb |
| `formula_xiaochaihutang` | 小柴胡汤 | 《伤寒论·辨少阳病》 | 大柴胡、柴胡桂枝、柴胡加龙骨牡蛎 | — |
| `formula_banxiaxiexintang` | 半夏泻心汤 | 《伤寒论·辨太阳病》 | 生姜/甘草泻心汤、黄连汤；另有同名「泻心汤」 | 同名异方 |
| `formula_dachengqitang` | 大承气汤 | 《伤寒论·辨阳明病》 | 小承气、调胃承气、复方大承气 | — |
| `formula_sinitang` | 四逆汤 | 《伤寒论·辨少阴/霍乱病》 | 通脉四逆、四逆加人参、茯苓四逆 | **contains_toxic_herb** |
| `formula_lizhongwan` | 理中丸 | 《伤寒论》＋宋代局方系统 | 附子理中、桂枝人参汤 | 组成待复核 |
| `formula_wulingsan` | 五苓散 | 《伤寒论·辨太阳病》 | 四苓散、胃苓汤、茵陈五苓散 | — |
| `formula_zhigancaotang` | 炙甘草汤 | 《伤寒论·辨太阳病》 | 异名复脉汤 | **组成待复核（来源全失败）** |
| `formula_wumeiwan` | 乌梅丸 | 《伤寒论·辨厥阴病》 | — | **contains_toxic_herb**、组成待复核 |
| `formula_baihutang` | 白虎汤 | 《伤寒论》＋《温病条辨》分级 | 白虎加人参/桂枝/苍术 | mineral_herb |

### 4.2 《金匮要略》1 首

| `formula_jinkuishenqiwan` | 金匮肾气丸 | 《金匮要略》肾气丸（八味）→ 今市售常见十味 | 六味地黄丸、桂附地黄丸、济生肾气丸 | **contains_toxic_herb** |

### 4.3 唐代方书 1 首

| `formula_duhuojishengtang` | 独活寄生汤 | 《备急千金要方》卷八（十五味大复方） | 三痹汤 | composition_size:large |

### 4.4 宋代局方系统与宋代方书（9 首）

| `formula_sijunzitang` | 四君子汤 | 《太平惠民和剂局方》卷三 | 异功散、六君子、香砂六君子、保元汤 |
| `formula_siwutang` | 四物汤 | 晚唐《仙授理伤续断秘方》→《局方》（首用于妇产科） | 桃红四物、八珍、十全大补；孙中山版同名异方 |
| `formula_xiaoyaosan` | 逍遥散 | 《太平惠民和剂局方》 | 丹栀逍遥散、黑逍遥散 | 组成有版本矛盾 |
| `formula_pingweisan` | 平胃散 | 《简要济众方》卷五 | 不换金正气散、柴平汤、胃苓汤 |
| `formula_erchengtang` | 二陈汤 | 《太平惠民和剂局方》卷四 | 导痰汤、涤痰汤、金水六君煎 |
| `formula_huoxiangzhengqisan` | 藿香正气散 | 《太平惠民和剂局方》卷二（十一味） | 六和汤 |
| `formula_suhexiangwan` | 苏合香丸 | 《太平惠民和剂局方》＋今成药（十五味） | 与安宫牛黄丸构成温开／凉开 | **contains_toxic_herb** |
| `formula_shixiaosan` | 失笑散 | 《太平惠民和剂局方》卷六（两味） | 与桃红四物合方；五灵脂—人参配伍禁忌 |
| `formula_guipitang` | 归脾汤 | 宋《济生方》→ 元《世医得效方》→ 明薛己 → 清《医宗金鉴》（层累扩用） | 与补中益气汤分工 |

### 4.5 金元医家方（2 首）

| `formula_buzhongyiqitang` | 补中益气汤 | 李杲《内外伤辨惑论》（《脾胃论》一系互见） | 升阳益胃汤、升陷汤、举元煎 |
| `formula_shengmaisan` | 生脉散 | 《医学启源》／《内外伤辨》 | 与炙甘草汤并列比较；注疏谱系跨八部著作 |

### 4.6 明代方书与明代补入（3 首）

| `formula_bajiantang` | 八珍汤 | 四君子＋四物合方（首次著录待核） | 十全大补汤、人参养荣汤 | 同名戏曲 |
| `formula_taohongsiwutang` | 桃红四物汤 | 《玉机微义》（原名加味四物汤） | 四物家族 | 方源待复核 |
| `formula_liuweidihuangwan` | 六味地黄丸 | 宋钱乙《小儿药证直诀》地黄丸 → 今成药 | 金匮肾气丸、知柏、杞菊 | 方源待复核 |

（八珍汤与六味地黄丸的方源分属宋、明两段，因合方逻辑归在此处，`dynasty` 字段已按各自依据分别标注并注明待复核。）

### 4.7 清代温病与活血方（7 首）

| `formula_yinqiaosan` | 银翘散 | 《温病条辨》卷一（辛凉**平**剂） | 与桑菊饮、白虎汤三级序列 | 组成待复核 |
| `formula_sangjuyin` | 桑菊饮 | 《温病条辨》卷一（辛凉**轻**剂） | 同上 | 组成有 8/10 味矛盾 |
| `formula_angongniuhuangwan` | 安宫牛黄丸 | 《温病条辨》1798 年定型；1993 后改水牛角 | 温病三宝、牛黄清心丸 | **contains_toxic_herb**、非遗 |
| `formula_xuefuzhuyutang` | 血府逐瘀汤 | 《医林改错》卷上 | 五逐瘀汤 | composition_size:large |
| `formula_longdanxiegantang` | 龙胆泻肝汤 | 清《医方集解》一系（各家著录小异） | 泻青丸、当归芦荟丸 | 木通名实存疑 |
| `formula_huanglianjiedutang` | 黄连解毒汤 | 《肘后备急方》 | 泻心汤、栀子金花汤 | 纯泻方 |
| `formula_yupingfengsan` | 玉屏风散 | 《究原方》／《丹溪心法》一系（**待核**） | — | 方源待复核 |

（`formula_duhuojishengtang` 已在 4.3 计；`formula_jinkuishenqiwan` 已在 4.2 计。）

## 五、标签统计（tags 只用本组自定词表）

合计 35 条元素、321 个标签实例（另有导入器自动追加的 category:item 35 个，不在手写统计内）。

**本体层**

- `kind:formula` 35/35
- `tradition:eastern` 35/35（一条一个，见第一节口径）

**出处层 `source_text:`**（按主要典籍）

- `shanghanlun` 12、`hejijufang` 8、`wenbingtiaobian` 3、`qianjinyaofang` 1、`jinkuiyaolue` 1、`jishengfang` 1、`jianyaojizhongfang` 1、`neiwaishangbianhuolun` 1、`yixueqiyuan` 1、`zhouhoubeijifang` 1、`yifangjijie` 1、`yilingaocuo` 1、`yujiweiyi` 1、`xiaoer_yaozheng_zhijue` 1、`jiuyuanfang` 1

**朝代层 `dynasty:`**

- `han` 13、`song` 9、`qing` 5、`tang` 2、`ming` 2、`jin_yuan` 2、`jin` 1、`yuan` 1

**角色层 `role:`**

- `formula_family_head` 22、`teaching_exemplar` 19、`official_standard` 9、`commercial_product` 6、`gendered_repertoire` 5、`emergency_item` 3、`school_founder_text` 3、`epidemic_repertoire` 2、`large_compound_formula` 2、`composite_formula` 1、`derivative_formula` 1、`layered_text` 1、`commentary_chain` 1、`anatomy_reform_text` 1、`intangible_heritage` 1、`metaphor_name` 1、`story_poison_plot` 1

**经济层 `trade:`**

- `pharmacy_shelf` 20（可预制、可上架销售的成药路径）、`apothecary_counter` 15（需现配、按方抓取的柜台路径）

**性质层 `trait:`**

- `literature_warns_danger` 19、`contains_toxic_herb` 5、`contains_active_alkaloid` 2、`mineral_herb` 2、`name_collision` 3、`name_ambiguity` 1

**体量层 `composition_size:`**（按药味数分档，**不给数字**）

- `small` 16、`medium` 11、`large` 8

## 六、含毒性药味的 5 首（最高优先级复核项）

| 方 | 毒性药味 | 条目内写了什么 |
|---|---|---|
| `formula_sinitang` 四逆汤 | 附子 | 三处写「含毒性药味，误用可致严重后果」；引 Britannica 乌头属为有毒植物；不写炮制、减毒、解毒 |
| `formula_jinkuishenqiwan` 金匮肾气丸 | 附子 | 同上；并标「古方八味 vs 今方十味」不可互换 |
| `formula_wumeiwan` 乌梅丸 | 细辛、附子、蜀椒 | 转述成药条目对细辛与肾功能的警示，**不作进一步推断**（FDA／NCBI 材料均失败） |
| `formula_angongniuhuangwan` 安宫牛黄丸 | 朱砂（HgS）、雄黄（As₄S₄） | 只写化学成分身份与「药典列毒性药品、设占比上限」，不写任何用量与处理 |
| `formula_suhexiangwan` 苏合香丸 | 朱砂 | 同上；另记过敏性休克病例报告的存在，不给处理办法 |

## 七、已知不足（须在下一轮裁定）

1. **七首方的组成仅有间接或二手支撑**，已在 `definition` 与 `evidence_and_uncertainty` 内明写「待复核」：`zhigancaotang`（来源全失败）、`yinqiaosan`（只读到说明书）、`lizhongwan`（只读到说明书）、`yupingfengsan`（只读到书目页目录）、`xiaoyaosan`（条目内部矛盾）、`sangjuyin`（8/10 味矛盾）、`wumeiwan`（方义段只列数味）。
2. **无一条《伤寒论》条文经逐字核对**（ctext、墨书院均失败），所有条文层表述止于「该篇载有此类条款」。
3. **百科转录层较厚**：中文方剂条目本身即二手汇编，其内部的方论引语（柯琴、吴昆、汪昂、张秉成、唐宗海等）未经原书核对，条目里已逐处标明为「经百科转引」。
4. **现代毒性文献缺失**：NCBI、FDA、WHO 三处失败，故乌头类毒理、马兜铃酸—木通关系只能停在「有毒性／存疑」层面，`formula_longdanxiegantang` 的木通名实问题尤其需要专门补证。
5. **维基百科零覆盖**：原计划的维基页面全部不可达，本组实际以 Britannica 与机构页替代，与「至少读过一个维基页面」的要求不符，如实记录。
6. **`dynasty` 与 `source_text` 待核项**：`bajiantang`（首次著录）、`yupingfengsan`（方源）、`taohongsiwutang`（《玉机微义》）、`liuweidihuangwan`（《小儿药证直诀》地黄丸）、`longdanxiegantang`（方源书名多家不一）。
