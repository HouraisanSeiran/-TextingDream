# 人类生产生活百科 · 人类美食（cuisine）

对应 [`cuisine.json`](cuisine.json)。状态：**候选资料**（`schema_version: 1`、`status: candidate`、`group: cuisine`），全部条目 `review_status: needs_review`。

**这是一个独立增补分区**。原有食材与工艺分区不改写；本组通过 `--with-cuisine` 显式构入独立百科库，不写旅程 `data` 或 StoryPackage。正文以 JSON 为准，状态仍为候选资料。

> 百科中存在 ≠ 当前世界存在，更不等于人物知道。食品条目尤其如此：**菜存在于百科，不代表它会在你的世界里被做出来**；本组不自动生成配方、不自动加入库存、不推导经济或人口参数。完整七节内容以 JSON 为准，此处只做扫读索引与来源说明。

- 元素总数 **24**，id 全部以 `cuisine_` 开头
- 来源 **47** 条，全部 `access: read`：**21 条 Encyclopaedia Britannica**（首轮）+ **26 条 Wikipedia（en）**（第二轮实际抓取正文后新增）
- 全部条目的 `details` 七节齐全（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty）
- 全部 `tags` 取自既有组已在用的标签词汇表，**未新增标签**

## 一、这个组在收什么

本组收**成品菜肴与烹饪成品**，不重立原料。取舍标准三条：

1. **先把原料组查一遍再立条**。小麦、水稻、玉米、大麦、燕麦、黑麦、藜麦、荞麦、木薯、薯蓣、马铃薯、大豆、菜豆、鹰嘴豆、兵豆、蚕豆、芝麻、油菜、橄榄；洋葱、大蒜、辣椒、番茄、茄子、甘蓝、白菜、黄瓜、鳄梨、柠檬等；盐、酱油、鱼露、味噌、醋、酒、茶、蜂蜜、蔗糖；乳、蛋、奶酪、黄油、发酵乳、火腿、香肠、干腌鱼等——**全部已在原组，本组一条不重立**。
2. **一道菜不等于一种原料**。本组每条都写清「这道菜的主料、工艺与成败条件」，因为同一批原料能做出完全不同的菜，也能因缺少一个环节而要不成。
3. **只收能影响人物行动与事件因果的菜**：拿不拿得到当日鲜鱼、有没有专用炉具、发酵要等多久、需不需要一大锅与多人手——这些才是能进故事的约束。不罗列餐厅品牌、不凑国家榜单。

### 有意不收的

- **小麦、水稻、鸡蛋、醋、酱油等原料本身**：已在 staples / flavors / animal-foods 组，本组只在 `related_ids` 里引用。
- **单纯的饮品与调味品**：茶、咖啡、啤酒、葡萄酒、蒸馏酒、酱油、鱼露、醋、蜂蜜、蔗糖均在 flavors 组；本组只在需要时作配料引用。
- **无已读来源支撑的现代快餐品牌与国际连锁**：不在本组，也未把它们的地方变体当独立条。
- **未确立起源的单一「发明人」叙事**：披萨的 Margherita 传说、炖饭的 Frederick I 传说在本组里被明确标为传说，不当事实。

## 二、地域分布（不凑国家榜单）

条数按「烹饪传统区域」分布，而不是按国家数平均：

| 区域 | 条数 | 条目 |
|---|---|---|
| 东亚 | 6 | 寿司、饺子类、拉面、泡菜、豆腐、北京烤鸭 |
| 南亚 | 4 | 比尔亚尼、咖喱、萨莫萨、馕 |
| 西亚北非 | 4 | 鹰嘴豆泥、法拉费、库斯库斯、烤肉串 |
| 撒哈拉以南非洲 | 2 | 英吉拉、乔洛夫饭 |
| 欧洲 | 3 | 披萨、炖饭、西班牙海鲜饭 |
| 美洲 | 4 | 塔可、tortilla、腌鱼、塔马利 |
| 东南亚 | 1 | 越南粉 |

说明两点：

1. **不平均分**。东亚与南亚条目多，是因为这两个传统的成品菜体系在全球流通度与可查证度都高；撒哈拉以南只 2 条，是因为本组只收了能用正文直接支撑的英吉拉与乔洛夫饭，**不为凑数另立无源条目**。
2. **跨区域条目按主源归区**。越南粉归东南亚，但其起源与法国殖民相关，这一点写进了 `historical_scope`；腌鱼归美洲，但与该菜并置的「生食不加热」传统（日本刺身、北欧腌渍鱼）在 `exceptions` 里明确区分。

## 三、条目扫读表

| id | 名称 | 一句话 | 主要支撑来源 |
|---|---|---|---|
| `cuisine_sushi` | 寿司 | 醋饭为现代定义性成分，配料可生可熟；narezushi→namanare→haya-zushi 三段历史，不等于刺身 | src_01、22 |
| `cuisine_dumpling` | 饺子类 | 小团面团大类，可包馅也可不包；加热方式含煮、蒸、煎、炸，不限煮蒸；发酵不是共同前提 | src_02、23 |
| `cuisine_ramen` | 拉面 | 碱水 kansui 弹面 + 长熬汤底；词借自 lāmiàn 但工艺近南方中华面食 | src_03、24、25、26 |
| `cuisine_kimchi` | 泡菜 | 盐渍发酵蔬菜；辣椒在许多现代配方中常见，但白泡菜不辣，储存条件依具体做法 | src_04、27 |
| `cuisine_tofu` | 豆腐 | 大豆磨浆煮浆后钙镁盐或酸凝固；汉代起源只是「被认为」；不冷藏仅限来源所指脱水制品，不泛指中式含水豆干 | src_05、28 |
| `cuisine_biryani` | 比尔亚尼 | 常见分层焖制，但预处理与辣度依配方；起源存在多说 | src_06、29 |
| `cuisine_hummus` | 鹰嘴豆泥 | 黎凡特酱泥；tahini 定义不可省；起源有争议，13 世纪食谱地点两说不一 | src_07、30 |
| `cuisine_falafel` | 法拉费 | 埃及起源的炸豆丸子；埃及与阿拉伯半岛用蚕豆，黎凡特用鹰嘴豆 | src_08、31 |
| `cuisine_couscous` | 库斯库斯 | semolina 手搓成粒 + couscousière 双层蒸；马格里布五国主食 | src_09、32 |
| `cuisine_injera` | 英吉拉 | 苔麸面糊发酵（时长两说不一）；陶制 mitad 90—95℃ 烙；兼作皿与餐具 | src_10、33 |
| `cuisine_jollof_rice` | 乔洛夫饭 | 塞内加尔起源，番茄辣椒洋葱一锅焖；与 thiéboudienne 同源不同菜 | src_11、34 |
| `cuisine_pizza` | 披萨 | 发酵面饼 + 高温速烤；pizza 一词 997 年首见，番茄不早于 16 世纪 | src_12、35 |
| `cuisine_risotto` | 炖饭 | 伦巴第起源；tostatura + 分次高汤不停搅拌 + mantecatura | src_13、36 |
| `cuisine_paella` | 西班牙海鲜饭 | 瓦伦西亚自治区起源；valenciana/mixta/de marisco 三型，双耳浅锅不搅拌 | src_14、37 |
| `cuisine_taco` | 塔可 | tortilla 盛馅对折徒手食用；馅料跨两大洲 | src_15、16、38 |
| `cuisine_tortilla` | tortilla | 石灰水煮玉米（nixtamalization）+ masa + 煎盘 | src_16、15、39 |
| `cuisine_ceviche` | 腌鱼 | 枸橼酸「腌熟」不等于杀菌；需当日鲜鱼与柑橘 | src_17、40 |
| `cuisine_pho` | 越南粉 | 米制扁面 + 香料汤底 + 配料后上；19 世纪末—20 世纪初，起源仍有争论 | src_18、41 |
| `cuisine_naan` | 馕 | 发酵单层面包，贴 tandoor 内壁（可达 480℃）烤 | src_19、42 |
| `cuisine_curry` | 咖喱 | 做法类别而非单一配方；masala ≠ curry powder | src_20、43 |
| `cuisine_samosa` | 萨莫萨 | 印度次大陆油炸填馅面点；形制可为三角/锥/月牙，非只三角 | src_21、44 |
| `cuisine_tamale` | 塔马利 | 玉米面团常见包叶蒸制；便于携带不等于干粮或可长期存放 | src_45 |
| `cuisine_peking_duck` | 北京烤鸭 | 与北京饮食传统相关的烤鸭菜；脆皮片鸭配薄饼卷食为常见呈现，挂炉与焖炉并列；65 日龄与三段上菜属特定店家做法 | src_46 |
| `cuisine_kebab` | 卡巴布 | 中西亚等地区肉菜大类，串烤只是部分形式，肉种与器具依地方做法 | src_47 |

## 四、来源与访问情况（必须如实说明）

**两轮实际读页，均为正文实取，不是搜索摘要。**

- **第一轮（Britannica）**：`britannica.com/topic/<slug>` 已知 slug 直链，逐条抽取正文；21 条全部 `access: read`。`britannica.com/topic/tamale` 曾返回 HTTP 404，`dosa` 亦 404，因此首轮未立塔马利与多萨。
- **第二轮（Wikipedia en，本轮新增）**：主代理告知 Wiki 已恢复后，本代理经**现有系统代理**（`127.0.0.1:7890`，只读使用，未改任何网络配置）用 `en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1` 拉取正文并落盘后逐条核对：
  - 21 条既有条目的对应页全部拿到正文（Sushi / Dumpling / Ramen / Kimchi / Tofu / Biryani / Hummus / Falafel / Couscous / Injera / Jollof rice / Pizza / Risotto / Paella / Taco / Tortilla / Ceviche / Pho / Naan / Curry / Samosa）。
  - 另读 Cup Noodles 与 Instant noodles 两页，用于核定杯面年份（见下「已修正的过强事实」）。
  - 为新增条目实读 Tamale、Peking duck、Kebab 三页。
  - 抓取期间 Wiki 对连续请求返回 **HTTP 429 Too Many Requests**；已改为限速 + 退避重试后全部成功。正文均写入临时目录后逐条读取，未把被截断的摘要当全文：`supports` 只写实际读到的段落。
  - 未使用中文维基，也未使用任何未经实读的页面。
- 首轮曾记述 «Wiki 主站不可达»；本轮已实际成功读页，该说法作废（见 git 前的行文历史）。

### 已修正的过强事实（两来源冲突时收窄或删精确值）

| 条目 | 修正前 | 修正后 | 依据 |
|---|---|---|---|
| 拉面 | 「1966 年推出杯面」 | 即食面 1958（Chikin Ramen）、**杯面 1971**；1966 只是安藤在美国得到想法的年份 | Cup Noodles、Instant noodles |
| 豆腐 | 「干豆腐不需冷藏」泛化 | 只有来源所指的脱水制品在脱水状态下的储运说法；不引申为中式含水豆干或鲜豆腐；旧说「不排水就是嫩豆腐」已改为列举压榨与不压榨两类工艺 | Wikipedia Tofu |
| 饺子类 | 「小团**发酵**面团」且限于水煮/蒸制 | 发酵不是共同前提：baozi 发酵，chuchvara/pelmeni/馄饨不发酵；加热方式含煮蒸煎炸；删去「煮到浮起即熟」当作通用火候判据 | Wikipedia Dumpling |
| 英吉拉 | 「制作约一周」当确数 | 两来源时长不一致（Britannica 约一周；Wikipedia 主发酵 24—72h + 二次 30—120min），**不取单一时长** | Wikipedia Injera |
| 英吉拉 | 「约 6000 年前驯化」当唯一年代 | 改记苔麸自**公元前第 4 千纪**已栽培，且**英吉拉本身起源不明**（民俗前 100 年说无法证实） | Wikipedia Injera |
| 比尔亚尼 | 「波斯起源」定论 | 起源有争议：可能源于波斯 pilau/birinj biryan 并在莫卧儿宫廷成形，也有莫卧儿之前经旅人传入德干说 | Wikipedia Biryani |
| 法拉费 | 无起源地 | 埃及起源（Wikipedia 明说），但**年代未给**，不反推谁更早 | Wikipedia Falafel |
| 鹰嘴豆泥 | 「13 世纪开罗食谱」定说 | 两来源地点不一（Britannica 开罗 / Wikipedia 归于 Ibn al-Adim 的阿勒颇），只记「13 世纪某部阿拉伯食谱」 | 两页对比 |
| 馕 | 词源作 nân-e sangak | 词源为波斯语 nân（面包通称）；英语入词年份记 1799—1803 两说 | Wikipedia Naan |
| 萨莫萨 | 「传统为三角形」 | 形制随地区为三角/锥/月牙；起源中世纪初或更早，名称来自中古波斯语 sambosag | Wikipedia Samosa |
| 寿司 | 只有四种形制，无历史 | 补醋饭为定义性成分、配料可生可熟可素、三阶段发酵史与 1824 年握寿司；删去「一桌寿司可反推鲜鱼与冰源」 | Wikipedia Sushi |
| 泡菜 | 无限地贮存细节 | 补 gimjang 越冬制作与 onggi 陶瓮半埋/jangdokdae 台、辣椒 17 世纪初才传入韩国 | Wikipedia Kimchi |
| 越南粉 | 「19 世纪末」定论 | 两来源不完全一致（19 世纪末 vs 20 世纪初书面记载），只记区间并保留「起源仍有争论」 | Wikipedia Pho |
| 塔马利 | —（新立） | 玉米 masa 包叶蒸制；便于携带不等于耐储干粮；不把未经交叉核定的极早年代与文明归属当结论 | Wikipedia Tamale |
| 北京烤鸭 | —（新立） | 育鸭日龄、皮肉分离与三段上菜属特定店家做法，不当整类菜必要条件；企业名不作食物别名 | Wikipedia Peking duck |
| 卡巴布 | —（新立） | 中西亚等地区的烤肉菜大类不限于串烤；签具与木炭非所有品种前提；döner 可叠片也可绞肉；新疆串与 satay 不作别名 | Wikipedia Kebab |

### 版权与署名

- Britannica 部分：第三方商业百科（非 CC BY-SA），**仅事实核对与自行转述，不复制原文段落**。
- Wikipedia 部分：正文实测授权为 **CC BY-SA 4.0**（本轮用 `action=query&meta=siteinfo&siprop=rightsinfo` 实测），`rights_note` 已逐条声明；对外分发需署名并链回原页面。

## 五、已知缺口（不自行补全）

逐条列在各自的 `evidence_and_uncertainty` 里，汇总共性四类：

1. **起源年代与地点**：寿司、饺子类、泡菜、法拉费、萨莫萨、库斯库斯、披萨、西班牙海鲜饭、塔马利等条目，已读来源只给了「一般认为」或给多个互不一致的说法，本组一律不作确切断代；塔马利的「最早年代」自相不一之处只列不选。
2. **原料传入时间**：番茄、辣椒、八角等的外来属性已在条内标明，但具体传入年月与路径未由已读来源覆盖；本组只写「是后来传入」。
3. **各地变体的源流关系**：同菜异名（如 thiéboudienne 与 jollof）的源流、各地配方的地方差异，未做系统比较。
4. **食品安全与营养参数**：本条目不提供。腌鱼、寿司等生食类只写工艺前提（鲜活、低温），不给温度、时长阈值或健康声称；Britannica 条目里的益生菌、心血管等段落未引用。

## 六、校验结果

| 校验项 | 结果 |
|---|---|
| JSON 严格解析（Node `JSON.parse`，UTF-8 无 BOM） | 通过 |
| 顶层 schema_version / group=cuisine / status=candidate / sources / elements | 通过 |
| 元素条数 | 24（21 条旧 + 3 条本轮新增） |
| 全局 id 唯一（与其余全部组比对） | 通过，无冲突 |
| id 前缀 `cuisine_` | 24/24 通过 |
| source_ids 均可解析到本组 sources | 通过（47 个来源全部被引用，无悬空、无未引用） |
| related_ids 可引用其他组真实 id 与本组 id | 通过（逐个比对全部 9 个组文件的 id 集合，无悬空） |
| tags 全部取自既有词汇表 | 通过，**未新增标签**（逐个标签反查其他组文件确认） |
| details 七节齐全且非空（键数恰为 7） | 24/24 通过 |
| review_status 全为 needs_review | 24/24 通过 |
| sources 全部 `access: read` | 47/47（无 search_only、无 unavailable） |
| 未写其他文件 | 仅改 `cuisine.json` / `cuisine.md` |
| 本页 MD 覆盖全部 24 条 | 通过（第三节扫读表逐条列出） |

## 本批入库验收

本批 24 条已增量导入独立百科库，来源 47 条（26 条为实际读取的 Wikipedia 页面）。主审对代表性条目作定向勘误：便携不等于耐储干粮；寿司不能证明鲜鱼、冰源或生食安全；泡菜不必辣；地方菜配方不当作全球固定规格；菜名不能自动推定产业、宗教或交通条件。完整正文与来源分歧以 JSON 为准。

独立测试：cuisine 与 supplement 合计 44 项通过；定向勘误后 cuisine 14 项复验通过。入库验证：旧分区逐字段不变、重复导入零写入、检索正常、完整性 ok、关联无悬空。全部条目仍为 needs_review，本批不构成逐条完整事实认证。旅程数据库及存档未修改。
