# 生活工艺补充组（craft-supplement）候选元素

状态：**candidate / 收集中**。本组是候选素材，不是数据库实现，不是任何故事包的已采纳正典，也未进入 `data/` 或任何 StoryPackage。

- 数据文件：[`craft-supplement.json`](craft-supplement.json)（`schema_version: 1` / `status: candidate` / `group: craft-supplement`）
- 规范依据：[`collection-spec.md`](collection-spec.md)
- 元素数量：**24**
- 来源：登记 **34** 条，其中 `access: read` **31** 条、`access: search_only` **3** 条（awl、antler、bone-carving，只能取到摘要页或索引式片段）；无 `unavailable` 记录（未能取到正文的尝试见第六节）。**每一条元素的机制支撑都至少有一条 read 来源**；3 条 search_only 仅作背景/定义线索，已在各条的 `evidence_and_uncertainty` 里逐条标明“仅背景、不支撑机制与年代”
- 审查状态：全部 24 条 `review_status` 均为 **`needs_review`**（未自升）
- 七节齐全：`definition` / `mechanism` / `conditions` / `exceptions` / `story_uses` / `historical_scope` / `evidence_and_uncertainty`
- 标签：全组 **36** 个不同 `snake_case` 标签，单条 4—6 个；标签仅用于检索，不是权限或兼容性证明
- 边界：本组只写原理、因果、前置与例外，**不提供任何危险配方、配比、温度、时长或制造步骤**，也不含医疗用途推荐

## 一、这一组补的是什么缺口

原有六组（staples / produce / flavors / animal-foods / materials / tools，共 207 条）在谷物、矿石、农具、纺锤/织机等层面已经铺开，但**纤维—纱—布这条链是断的**，**动物皮到革、植物纤维到纸、脂到烛、油到皂这几条日用化学品链也缺**，工具层缺少锹铲、锉、风箱、针剪与骨角材料。本组按“缺什么补什么”的原则填这些缺口，不重新列一遍已有条目。

## 二、四条必须先说清的边界

1. **原料 ≠ 成品。** 本组刻意把同一物质链上的不同阶段拆成不同条目：棉纤维 / 棉织物，羊毛 / 毛织物 / 毡，蚕丝 / 丝织物，韧皮纤维 / 亚麻织物，皮革。纤维不能当布用，布也不能反推为“有纤维就有布”。亚麻作物已在 staples 组（`staples_flax`），本组**不重复作物条目**，只写离析后的纤维与织物。
2. **会用 ≠ 能制造。** 每条的 `conditions` 写前置（材料、工具、燃料、水体、场地、熟练工、可维护性），`exceptions` 反复点明常见误推：有油脂与灰不等于会制皂，有鹿角不等于会雕刻，知道风箱原理不等于能做出气密的皮囊或木箱。
3. **不把单一欧洲技术史当全球事实。** 多处明确拆解“欧洲叙述”的局限：风箱条目直接标注“发明于欧洲中世纪”的单一地区叙事与其他地区早期鼓风器具的冲突；丝、纸、鞣革、剪刀都给出分地区的多条时间线，而不是一条直线。
4. **不绝对化“必须现代设备”。** 手工纺与机器纺、手工抄纸与连续抄纸机、植物鞣与铬盐鞣都是同一原理的不同实现；本组写清各自的代价（耗时、尺寸限制、水质要求），而不写成“落后即被取代”。

## 三、条目索引

| ID | 名称 | 层 | 关键点 |
|---|---|---|---|
| `craft_supp_cotton_lint` | 棉纤维（皮棉与棉短绒） | 纤维 | 轧棉只完成去籽，不完成纤维排列；长绒/中绒/短绒用途差异大 |
| `craft_supp_cotton_cloth` | 棉织物（棉布） | 织物 | 组织与整理决定手感；机器棉纺是特定地区的过程 |
| `craft_supp_wool_fleece` | 羊毛（原毛与洗净毛） | 纤维 | 角蛋白；卷曲—弹性—锁气保暖；湿态强度下降、强碱高温有害 |
| `craft_supp_woollen_cloth` | 毛织物（缩绒、精纺/粗纺） | 织物 | 缩绒需水+温+机械+助剂四者共同作用 |
| `craft_supp_felt` | 毡（非织造） | 织物（旁路） | 不经纺与织；少量羊毛可带动非毡化纤维 |
| `craft_supp_silk_filament` | 蚕丝（生丝与脱胶丝） | 纤维 | 天然长丝；丝胶既是保护层也是缫丝的前提 |
| `craft_supp_silk_cloth` | 丝织物 | 织物 | 长丝使纱细而强；湿态强度下降、怕汗与久晒 |
| `craft_supp_bast_fibre` | 韧皮纤维（麻纤维） | 纤维 | 果胶黏结，沤麻或剥皮离析；各麻种分工不同 |
| `craft_supp_linen_cloth` | 亚麻织物（麻布） | 织物 | 强度高、干得快、凉；弹性低易皱（不是“不皱”） |
| `craft_supp_leather` | 皮革 | 材料 | 三层结构只用真皮；三类鞣剂成品差异大，不能当等级高低 |
| `craft_supp_paper` | 纸 | 材料 | 解纤—滤层—压干；与莎草纸、羊皮纸不同物 |
| `craft_supp_parchment` | 羊皮纸与犊皮纸 | 材料 | 拉伸刮削使双面书写可行，推动册页书；与皮革同源不同用途 |
| `craft_supp_ink` | 墨 | 材料 | 颗粒型靠附着，铁盐—鞣质型靠化学变深；不含配方 |
| `craft_supp_wax` | 蜡 | 材料 | 比脂肪硬而脆、不皂化；蜂蜡/植物蜡/矿物蜡不可互换 |
| `craft_supp_candle` | 蜡烛 | 器物 | 关键在芯与毛细作用，“有脂无芯”不成立为烛 |
| `craft_supp_soap` | 肥皂 | 材料 | 皂化脂肪酸盐；硬水生皂垢是硬约束 |
| `craft_supp_bone_horn_antler` | 骨、角（角质鞘）与鹿角 | 原料 | 三种不同组织：骨与鹿角为骨组织（胶原+磷酸钙）；真角**典型形态**为骨芯外包角蛋白鞘、**通常**不分叉且角鞘一般终生保留（不写作普适定律）；犀角为角质化毛状表皮 |
| `craft_supp_ivory` | 象牙与类牙材料 | 原料 | 属牙本质，**不是骨**：比骨硬但比牙釉质软，主为磷灰石；1990 年 CITES 禁止贸易 |
| `craft_supp_needle` | 缝针 | 工具 | 骨/角/金属跨度两万年以上；针眼非一开始就有 |
| `craft_supp_awl` | 锥子 | 工具 | 常见机制是挤压成孔，但**不是所有材料都绝不去材**；与有刃钻具属谱系而非二分 |
| `craft_supp_scissors` | 剪刀与大剪 | 工具 | 支点式与弹簧式；两刃只两点接触 |
| `craft_supp_ax` | 斧 | 工具 | 刃口垂直柄轴；与锛、锹、锯的施力方向不同 |
| `craft_supp_file` | 锉刀 | 工具 | 固定齿形切削，与砂磨不同；齿粗细分级 |
| `craft_supp_bellows` | 风箱 | 工具 | 阀+喷嘴的构造原理；**不给全球起源年代**（原“欧洲中世纪发明”已删） |

## 四、关联到原六组的真实 ID

`related_ids` 只引用实际存在的条目，主要用到：`staples_flax`、`animal_food_sheep`、`animal_food_cattle`、`animal_food_rendered_fat`、`flavors_honey`、`materials_lime`、`materials_steel`、`materials_wrought_iron`、`materials_charcoal`、`materials_iron_metal`、`tools_spindle_whorl`、`tools_spinning_wheel`、`tools_loom`、`tools_rope`、`tools_adze`、`tools_saw`、`tools_kitchen_knife`、`tools_forge_anvil`、`tools_hand_drill`。这些原文件未被修改，也未在内添加重复条目。

## 五、已知的弱项与待补

1. **证据强度分层不均。** `awl`、`antler`、`bone carving` 三条来源只能读到摘要与引文片段（已按实标为 `search_only`），因此只作背景线索：锥与骨角两条的**机制支撑已改由 `drilling-and-boring tools`、`needle`、`bone-anatomy`、`horn-zoology`、`keratin`、`dentin` 这六条 read 来源担任**；剩下的未核实点已在条目内逐条点名。
2. **“兽角可加热软化、可切片压平”已不再当已核实说法。** 这是第一版里被主审核出的关键点：已读的 horn-zoology 与 keratin 两页只说了角蛋白的分布、二硫键稳定性与吸湿行为，**没有**直接描述受热成形；因此条目现在只保留“角质部分对水热与干湿循环敏感”这一条件性表述，具体成形工艺列为未核实。
3. **风箱的年代叙述已删。** 已读页面只有“出现于欧洲中世纪”一句断言，无年代依据与跨地区比较，因此已从 `definition` 与 `historical_scope` 中移除，改成“构造成面”与“不给全球起源年代”；仍属未核实项，而不是暂挂待核却同时在定义里肯定。
4. **锥子的绝对表述已改掉。** “穿孔而不去材”现写作“常见机制为挤压成孔、结果因材而异”：磨铝的尖、硬而脆的材、干湿不同的皮都会让实际表现偏向剔削或压裂。
5. **两处普遍性措辞已收口（二级复审）。** ① 真角不再写“不分叉、从不脱落”这类普遍定律，改为“典型形态…通常不分叉、角鞘一般终生保留”，并明说本条**未核对到具体例外物种**，因此不列物种、不引入未核对的来源；鹿角同样改为“常见特征”，并交代并非所有鹿科物种都长角、性别与年龄会带来差异。② 角蛋白“不被蛋白酶分解”改为“对许多普通蛋白酶较耐受”，并补上专一降解者（角蛋白酶、某些微生物与昆虫）存在这一边界，这也解释了角质制品会遭虫蛀。
6. **锹铲未单立条目。** 多个 Britannica 入口（spade、shovel 各拼写）均返回 404，未能取得可引用的正文；为避免拿摘要当全文，本组**没有**写锹铲条目，而是把锹与斧、锛、锯的区别写在 `craft_supp_ax` 的 `definition` 与 `exceptions` 中。这是本组明确承认的缺口。
7. **胶类被移除。** 胶最初成条，但 Britannica 的 glue 条目过短（仅定义与一句埃及早期证据），无法支撑七节所需的机理与例外，故整条连同来源记录一并删除，不拿常识填空当来源证据。留待以后找到博物馆或修复领域的完整资料再补。
8. **古代手工纺与手工抄纸的具体器具未逐项核对。** 本组只写原理与前置，未给器具形制、规格或操作参数——这既是安全边界，也是证据边界。
9. **地域覆盖仍偏欧亚。** 南亚棉织、非洲冶铁与鼓风、美洲骨角工艺的专门文献本条未检索，属下一轮补强方向。

## 六、实际检索记录（可核）

本轮实际 `read` 的页面共 **35** 个（含不同 URL 的全部尝试），其中 31 个取到完整正文、3 个取到摘要页（awl、antler、bone carving）、1 个为 The Met 的教育性文章（可归入正文类）：

- Britannica cotton、wool、silk、sericulture、linen、bast fibre、leather、tanning、papermaking、paper、parchment、wax、candle、soap、ink、needle、scissors、ax、file、bellows、felt、yarn、weaving、ivory、hand tool —— 均读到完整正文
- Britannica **bone-anatomy、horn-zoology、keratin、dentin、hand-tool 的 drilling-and-boring-tools 子页** —— 主审补充轮新读，用于把骨/角/鹿角/象牙/锥子的机制从 search_only 来源上换下来
- Britannica awl、antler、bone carving —— 只返回摘要与交叉引文，标为 `search_only`
- The Met（Heilbrunn Timeline）silk trade 页 —— 读到正文，但内容为贸易网络而非织造工艺，故只用作“丝绢属远距离贸易品”的背景
- 尝试但不可用（记录在案，未当证据）：Britannica spade / spade-tool / spade-and-shovel / spade-farming、shovel / shovel-tool（404）；parchment-animal-skin-product（404）；soap-and-detergent、printing-ink、ink-printing、ink（短路径）（404）；needle（404）；glue 条目可读但过短；Smithsonian wool（403）、Kew cotton（403/反爬）、Met 另两个 TOAH 路径（404）、Canada.ca 铁胆墨页（404）、Britannica mattock 与 hoe（只有 Quick Facts，无正文）、antler 以外的 bone/antler 考古类页未命中
   > 注：第一轮曾把 horn / horn-anatomy / horn-animal-anatomy 记为 404，补充轮已改用 `science/horn-zoology` 成功取到正文，旧记录只保留作为路径尝试记录。
- 搜索工具局限：通用 web 搜索多次被词典、编程与商品页淹没（如“cotton”“spool”“soap”），因此改用直接读取已知机构 URL 的方式取得正文；这也意味着本轮**未**构建完整的检索式覆盖，证据是“读到什么写什么”，而不是穷尽式文献综述。

## 七、检索提示

- 按阶段检索：`fibre` / `textile` / `processed_material` / `tool` / `raw_material`
- 按工艺检索：`weaving` / `spinning` / `textile_finishing` / `leatherworking` / `sewing` / `metalworking` / `woodworking` / `abrading`
- 按材料检索：`plant_fiber` / `animal_fiber` / `animal_product` / `plant_product`
- 注意：标签只帮助找条目，**不能**用来证明两种材料可互换（例如所有纤维都带 `fibre`，但棉与丝的性质与工艺前提差异极大）。
