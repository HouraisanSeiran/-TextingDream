# 生产生活工具与小形设施（tools）候选元素组

状态：**候选素材收集**，不是数据库实现，不是任何故事包的已采纳正典，也未进入 `data/` 或任何 StoryPackage。
配套机读文件：[`tools.json`](tools.json)（`schema_version: 1` / `status: candidate` / `group: tools`）。
规范依据：[`collection-spec.md`](collection-spec.md)。

- 元素数量：**40**
- 来源：登记 **38** 条，全部为 `access: read`（实际读过正文），无 `search_only`、无 `unavailable`
- 审查状态：全部 40 条 `review_status` 均为 **`needs_review`**（未自升，等待主审）
- 每条 details 七节齐全：`definition` / `mechanism` / `conditions` / `exceptions` / `story_uses` / `historical_scope` / `evidence_and_uncertainty`
- 标签：全组共 **35** 个不同 `snake_case` 标签，单条 4—9 个，用于检索而非权限或兼容性证明
- 边界：本组是**工具与小型设施**清单，不是武器图鉴；不含任何可操作的制作流程、温度、配比或工艺参数

## 四条必须先说清的边界

1. **「知道原理」不等于「获得制造能力」。** 本组每条的 `conditions` 专门写前置（材料、燃料、工具、技能、组织、可维护性），`exceptions` 里反复点明容易被误推的地方：会挥锄不等于会做锄，看过壁刀形状不等于能做出能用的犁，有凿就能雕任何石头是错的。锻造、淬火、烧窑一类内容属危险制造知识，本组**有意只写关系与门槛，不给任何流程**。
2. **不所有时代、也不所有土壤一套标准。** 同名条目在不同地区、不同土壤/气候/材料条件下表现差异很大。典型例子：轻犁在阻力较小的地中海薄表土上效率较好，在西北欧重土上牵引阻力与成效比不划算（但不等于完全划不出沟）；长柄钐在古代世界使用很少，要到 8 世纪加洛林时代的干草与越冬饲料需求下才普及；鞍形磨与旋转磨在欧洲有长达千年的重叠期，而盘形旋转磨在亚洲部分地区沿用至今。因此本组只在**有来源支撑的节点**上给年代，且明确标注属哪条地区脉络。
3. **不把条件性现象写成硬定律。** 本组刻意避开「X 必然导致 Y」的写法，改为写清条件：盐渍化是盐分收支问题（入水盐分、蒸散、地下水位、淋洗与排水输出），并非未配人工排水就必然发生；紧实层与反复固定深度、土湿与碾压等多因素相关，不是重犁的必然产物；未玻化/未施釉的陶器贮液时倾向渗漏，但施釉、提高烧结程度、内衬等均可应对，而适度的透气渗湿又带来蒸发降温，所以不能推成「无釉不能存液」；单个定滑轮理想力比≈1、不降低张力，却通过改变方向和改善施力姿势带来真实价值。
4. **不是「工具越先进越好」的线性史。** 多项条目写明「旧技术并未退场」：锄在犁耙普及后仍是园艺与坡地主力；纺锤在纺车之后依然存在且可携带；弓钻在 20 世纪前仍在欧洲小作坊使用，在其他地区至今未废止；橇在轮轴出现后也未消失，而是收窄为雪橇一类按环境分工的形态。

## 详情阅读索引

不要把 `details` 当摘要读。它是一个「能直接拿去写世界设置」的规格：`definition` 定性，`mechanism` 给运作结构，`conditions` 写前置与维护，`exceptions` 列不被排除的合法变体与常见误推，`story_uses` 推故事用途，`historical_scope` 给有来源的年代与地域范围，`evidence_and_uncertainty` 分层证据并声明哪些是归纳。

建议先读以下 10 条（对全局约束最强）：

| 优先读 | ID | 为什么先读 |
|---|---|---|
| 1 | `tools_ard_plough` | 「同一工具在不同土壤带有效性差别巨大」的最佳实例，直接反驳按时代一刀切 |
| 2 | `tools_moldboard_plough` | 结构三件套 + 紧实层这一**条件性负面后果**（与反复同深度、过湿作业、碾压等多因素相关） |
| 3 | `tools_scythe` | 起源不明、古代使用有限、因饲料制度才普及；典型的「技术与社会需求绑定」 |
| 4 | `tools_saddle_quern` | `exceptions` 同时否掉「只能磨谷物」与「鞍形/旋转磨瞬间替换」两种误推 |
| 5 | `tools_storage_jar` | 致密度/施釉/内衬共同决定能否存液；无釉不等于一概不能贮液，蒸发降温反而是用途 |
| 6 | `tools_granary` | 仓储同时是物理设施与制度（含稳定粮价），且「有仓不等于安全」 |
| 7 | `tools_irrigation_canal` | 盐渍化是盐分收支问题（入水盐分/蒸散/地下水位/淋洗/排水输出），不等于「没人工排水就必然盐渍化」 |
| 8 | `tools_forge_anvil` | 门槛最高的一条；同时是**明确拒绝提供制作细节**的示范写法 |
| 9 | `tools_wheel_axle` | 轮同时是摩擦装置与力矩装置；`exceptions` 否掉「轮等于车」与「轮普适」 |
| 10 | `tools_rope` | 反向捻与捻度—强度反关系；作为几乎所有运输与吊装技术的隐形前提 |

## 缺口与不稳处（不假装完整）

- **年代学不是逐条核过考古报告。** 有明确来源支撑的具体年代集中在少数条目（磨石、陶器、轮与轴、水磨、风磨、钐、天平、螺旋钻、弓钻等），其余条目的年代表述一律留空或写明「各地区差异极大，不宜统一断代」。
- **部分「近亲」未单独立项。** 如锡、铲、锹、风箱、船、犁刀、铁匠钳等都有足够体量，本批为控制规模未纳入，仅在该组相关条目的 `related_ids` / 文本中提及。
- **纺轮与镰刀的专门文献未逐项核对。** 这两条的形制谱系与考古定年主要靠关联条目（纺车、钐）反推，已在 `evidence_and_uncertainty` 里写明。
- **武器与工具的边界保持模糊。** 刀的条目明确记载早期切割工具与武器同源、欧洲男子长期随身携刀；本组不尝试把「工具」与「武器」做成互斥分类。

---

## 全部 40 条

### A. 整地与耕作（5）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 1 | `tools_digging_stick` | 掘土棒 | agriculture, wood, human_power | 削尖或火烤硬化的长木棍，锄与犁的共同前身；不能推为所有地区必经的单一阶段 |
| 2 | `tools_ard_plough` | 轻型犁（耙犁/无轮犁） | agriculture, animal_power | 畜力牵引、只划表土不整片翻转；在浅松薄表土效率较好，重土上阻力大、效率低 |
| 3 | `tools_moldboard_plough` | 有壁犁（含轮式重犁） | agriculture, animal_power | 犁铧切土 + 曲面壁刀翻转土层 + 犁侧板抗侧推；在特定耕法下可能加剧压实 |
| 4 | `tools_hoe` | 锄 | agriculture, human_power | 刃与柄成直角的手持挖土除草工具；不是「犁的落后版本」 |
| 5 | `tools_harrow` | 耙 | agriculture, animal_power | 拖过田面碎土搂草覆种；与犁的分工是**层位**而非先进落后 |

### B. 收割、脱粒与清选（4）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 6 | `tools_sickle` | 镰刀 | harvest, human_power | 短柄曲刃、一手揽禾一手拉割；与钐的劳作组织不同 |
| 7 | `tools_scythe` | 长柄钐 | harvest, iron | 曲刃斜装长曲柄、大幅横扫割草；起源不明，8 世纪随干草储备才普及 |
| 8 | `tools_flail` | 连枷 | processing, leather | 两段木件皮条铰接、以甩打脱粒；铰接设计直接影响效率与伤手风险 |
| 9 | `tools_winnowing_tray` | 簸箕与扬谷器具 | processing, plant_fiber | 把谷物抛向风中、用重量差分离颖壳；看风作业的季节窗口 |

### C. 研磨与加工（3）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 10 | `tools_saddle_quern` | 鞍形磨石 | cooking, stone | 凹面石床 + 手持研磨石往复推碾；也磨香料、颜料与矿石 |
| 11 | `tools_rotary_quern` | 旋转磨石 | cooking, stone | 上石绕轴旋在下石上、谷物从孔入粉从边出；蜂巢/罐/盘三形 |
| 12 | `tools_mortar_pestle` | 臼与杵 | cooking, stone, ceramic | 以捣击而非滚碾打碎；擅少量黏性或含油物料，不擅批量磨粉 |

### D. 储藏与容器（3）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 13 | `tools_granary` | 粮仓 | storage, facility | 存已脱粒谷物；同时是稳定粮价的制度，不是单纯容器 |
| 14 | `tools_storage_jar` | 储罐与陶质容器 | ceramic, storage | 未玻化/未施釉有渗漏倾向，可用施釉、提高烧结度或内衬应对 |
| 15 | `tools_basket` | 编篮与编织容器 | plant_fiber, transport | 枝条草茎编成；兼具筛、篓、囤、鱼篓等多种形态，材料随气候带变 |

### E. 水与动力（6）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 16 | `tools_water_well` | 水井 | water_management, facility | 挖到含水层的取水孔；选址、深度与防污决定能否全年可用 |
| 17 | `tools_irrigation_canal` | 灌溉渠道与沟灌系统 | water_management, agriculture | 重力引水网络；长期维持需管住盐分收支（排水不畅时盐渍化可抵消增产） |
| 18 | `tools_shaduf` | 桔槔（配重提水杠杆） | water_management, wood | 不等臂杠杆 + 配重；适合小园圃，不产生压力也不连续供水 |
| 19 | `tools_noria` | 提水水轮（斗式水车） | water_management, water_power | 轮缘系一串容器、低位装水高位卸水；与磨粉水轮不是同一装置 |
| 20 | `tools_watermill` | 水磨（水轮驱动磨坊） | water_power, facility | 水轮经轴/齿轮带动磨石；也用于缩绒、鼓风、锯木 |
| 21 | `tools_windmill` | 风磨（含风车提水） | wind_power, facility | 斜置帆受风、经风轴齿轮驱动；波斯最早记载、欧洲 12 世纪普及 |

### F. 厨房与陶作（3）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 22 | `tools_kitchen_knife` | 厨刀 | cooking, cutting | 刃固定于柄的单手切削工具；与武器的分野在用途而非形状 |
| 23 | `tools_pottery_cooking_pot` | 陶质炊具（釜、鬲、炖罐） | cooking, ceramic | 可直接上火的陶容器；把硬的、需长时处理的食材变成可食 |
| 24 | `tools_pottery_wheel` | 陶轮（转盘） | craft, ceramic | 垂直轴使工作盘稳定旋转；解决成形，不解决干燥与烧成 |

### G. 纺织（3）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 25 | `tools_spindle_whorl` | 纺锤与纺轮 | textile, craft | 纺杆加加重轮悬垂旋转加捻；可边走边纺，与纺车是两套工艺 |
| 26 | `tools_spinning_wheel` | 纺车 | textile, craft | 大轮经绳传动水平锭子；萨克森式加线轴与脚踏解放双手 |
| 27 | `tools_loom` | 织机 | textile, craft | 经线张紧 + 开口/投纡/打绥循环；上机耗时往往超过织本身 |

### H. 木石金工（7）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 28 | `tools_hammer` | 锤与槌 | woodworking, metalworking | 以质量与速度传冲击；锤头与柄的结合是核心工程难题 |
| 29 | `tools_chisel` | 凿子 | woodworking, stoneworking | 刃口斜切、靠锤或槌冲击推进；石凿常用软锤 |
| 30 | `tools_adze` | 锛 | woodworking | 刃口与柄垂直、以镐式动作向内下方劈削；造舟与梁柱的关键 |
| 31 | `tools_saw` | 锯 | woodworking | 细齿连续划切 + 锯齿分料防夹；纵锯与横锯齿形不同 |
| 32 | `tools_hand_drill` | 手工钻具（弓钻、泵钻、手摇钻） | woodworking, craft | 手搓/皮条/弓/泵杆提供旋转；石材钻孔靠研磨砂而非刃口 |
| 33 | `tools_auger` | 螺旋钻 | woodworking, construction | 螺纹导入 + 螺旋沟排屑；带螺旋杆属中世纪，铁器时代版需反复退钻 |
| 34 | `tools_forge_anvil` | 锻炉与砧（锻打设备） | metalworking, fuel | 炉、砧、锤凿钳缺一不可；**本条有意不给任何工艺参数** |

### I. 量具（1）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 35 | `tools_balance_scale` | 等臂天平与杆秤 | measurement, trade | 等臂天平靠臂长相等的横梁；替代称量法可消除臂长误差 |

### J. 运输与机械（5）

| # | ID | 名称 | 主要标签 | 一句话 |
|---|---|---|---|---|
| 36 | `tools_wheel_axle` | 轮与轴 | transport, construction | 把滑动摩擦变滚动、或按半径比放大力的同一基础机构 |
| 37 | `tools_cart` | 畜力车与推车 | transport, animal_power | 载重上限由轮、轴、车架与**挽具**共同决定，不只靠轮子 |
| 38 | `tools_sledge` | 橇与拖运器 | transport | 无轮拖行/推动承载；无路地形比轮车可靠，石地上极耗力 |
| 39 | `tools_pulley` | 滑轮与滑轮组 | construction, transport | 单个定滑轮只改方向不省力；动滑轮参与才省力，绳行程相应变长 |
| 40 | `tools_rope` | 绳索 | transport, plant_fiber | 梳—纺纱—绞股—绞绳四阶段；反向捻是扭转稳定关键 |

---

## 标签词表（35 个，均已在本组出现）

**功能/领域**：`agriculture` `harvest` `processing` `cooking` `storage` `craft` `cutting` `woodworking` `stoneworking` `metalworking` `textile` `construction` `transport` `water_management` `measurement` `trade`
**品类**：`tool` `facility`
**材料**：`wood` `stone` `clay` `ceramic` `iron` `steel` `bronze` `leather` `plant_fiber` `animal_fiber` `earth` `fuel` `building`
**动力**：`human_power` `animal_power` `water_power` `wind_power`

标签用于检索，不构成权限或兼容性证明；本组未引入同义混用标签（如未同时使用 `carpentry` 与 `woodworking`）。

---

## 来源（38 条，全部 read）

优先选用了百科全书类与 FAO 技术手册类参考；维基百科在本机网络环境下不可达，未使用。

**Encyclopaedia Britannica（35 条专题页）**

| source id | 主题 |
|---|---|
| `tools_src_britannica_plow` | 犁：掘土棒到有壁犁、罗马轻犁局限、轮式犁与全钢犁 |
| `tools_src_britannica_agri_tech` | 农业技术：整地目标、土壤含水量窗口、紧实层成因 |
| `tools_src_britannica_hoe` | 锄：直角结构、刃材演变、被犁耙取代 |
| `tools_src_britannica_harrow` | 耙：碎土除草覆种、树枝→木耙→铁齿耙 |
| `tools_src_britannica_scythe` | 钐：曲刃长曲柄、起源不明、加洛林时代普及 |
| `tools_src_britannica_flail` | 连枷：两段木件铰接、日脱粒量、19 世纪被机械取代 |
| `tools_src_britannica_cereal_processing` | 谷物加工：不宜生食、碾磨筛分、储藏需低湿通风 |
| `tools_src_britannica_quern` | 磨石：鞍形与旋转两类、石材与凿毛维护、地区延续 |
| `tools_src_britannica_mortar_pestle` | 臼杵：定义材料、与鞍形磨并列、厨房与药房延续 |
| `tools_src_britannica_basketry` | 编篮：材料技法分类、簸箕/鱼篓/粮囤、气候带分布 |
| `tools_src_britannica_granary` | 粮仓：存已脱粒谷物、常平仓制度、印度河考古证据 |
| `tools_src_britannica_earthenware` | 陶器：未玻化吸水性、施釉二次烧成、最早陶器出处 |
| `tools_src_britannica_watermill` | 水轮：三类水磨、取水方式、Barbegal、多用途 |
| `tools_src_britannica_windmill` | 风磨：帆/风轴/齿轮/尾扇、波斯与欧洲时间线 |
| `tools_src_britannica_wheel` | 轮：约前 3500 年图像、木盘轮、辐条轮铁箍、多用途转用 |
| `tools_src_britannica_axle` | 轴：轮所转的销或轴、简单机械、机械利得 |
| `tools_src_britannica_sledge` | 橇：无轮定义、travois、亚述埃及浮雕、被轮轴收窄 |
| `tools_src_britannica_rope` | 绳：四阶段制造、反向捻、捻度与强度、绳道 |
| `tools_src_britannica_pulley` | 滑轮：绳槽、单个与组合、五种简单机械、阿基米德 |
| `tools_src_britannica_lever` | 杠杆：力臂比、桔槔配重提水、早期天平梁 |
| `tools_src_britannica_balance` | 天平：等臂原理、古埃及起源、销轴与刀口、替代称量法 |
| `tools_src_britannica_spinning_wheel` | 纺车：取代手纺、水平锭子绳传动、萨克森轮脚踏 |
| `tools_src_britannica_loom` | 织机：最早年代与经纬原理、综杆与梭、提花与背带织机 |
| `tools_src_britannica_weaving` | 织造：开口-投纡-打绥、三基础组织、上机复杂度 |
| `tools_src_britannica_hand_tool` | 手工工具：分类、装柄、石铜铁递进与三时代体系局限 |
| `tools_src_britannica_hammer` | 锤槌：形态分化、装柄两难、软锤与石凿、斧锛差异 |
| `tools_src_britannica_chisel` | 凿：刃在金属杆末端、需槌击、燧石祖型与埃及铜青铜凿 |
| `tools_src_britannica_adz` | 锛：刃与柄垂直、镐式动作、石片到埃及 T 形装柄 |
| `tools_src_britannica_saw` | 锯：分料防夹、纵锯与横锯齿形、夹背锯 |
| `tools_src_britannica_drill` | 钻：端部切削、排屑沟槽、钻头材料与装夹 |
| `tools_src_britannica_drilling` | 钻孔工具：锥子vs钻、手搓/皮条/弓/泵钻、研磨砂管钻、螺旋钻 |
| `tools_src_britannica_auger` | 螺旋钻：螺纹导入、割圈刃、螺旋排屑、弓形柄 |
| `tools_src_britannica_knife` | 刀：刃固定或铰接于柄、餐具类、材料递进、欧洲携刀习惯 |
| `tools_src_britannica_irrigation` | 灌溉：人工施水、灌法分类、盐渍化风险与排水条件 |
| `tools_src_britannica_water_supply` | 供水：浅井最早、印度河砖井、坎儿井、罗马渡槽、管材限制 |

**FAO（3 条技术手册，非商业教育用途需注明出处）**

| source id | 主题 |
|---|---|
| `tools_src_fao_irrigation_manual` | 灌溉水管理培训手册：入渗、土壤水分常数、盐碱土改良 |
| `tools_src_fao_fruit_veg_handling` | 果蔬采后处理与保存：热烫、冷却、日晒干燥、发酵、储藏 |
| `tools_src_fao_grain_storage` | 谷物储藏综合虫害管理：安全储藏要求、通风干燥、非化学防治 |

---

## 校验记录

以独立脚本（临时目录，未入库）对 `tools.json` 校验，全部通过：

- 顶层字段：`schema_version=1`、`group=tools`、`status=candidate`、`sources`/`elements` 非空
- 唯一性：40 个 element id 与 38 个 source id 均无重复
- ID 格式：element 全部匹配 `^tools_[a-z0-9_]+$`；**source 全部带组前缀** `tools_src_`（依 collection-spec 「source: id(组前缀)」），且与 element 的 `tools_` 命名空间不冲突
- 引用完整性：每条 `source_ids` 均指向已登记来源，且至少含 1 条 `access=read`；每条 `related_ids` 均指向本组已存在 ID，无自引用、无悬空引用
- 字段完整性：`name`/`aliases`/`tags`/`summary`/`details`/`source_ids`/`related_ids`/`review_status` 齐全
- 七节：40×7 = 280 个分节均为非空字符串，无过短分节（<40 字符为 0）
- 标签：全部符合 `^[a-z][a-z0-9_]*$`，单条内无重复
- `review_status`：40/40 均为 `needs_review`，无自升
- MD 与 JSON 一致：40 个 element id 与 38 个 source id 均在 MD 中出现，MD 中无指向不存在 ID 的笔误；主清单恰好 40 行；文中声明的条目数/来源数/标签数均与实际一致
- 编码：两份文件均为 UTF-8 无 BOM，无 U+FFFD 替换字符（全部经由 `vantaloom_edit` 写入，未用 shell 重编码）

本组仅写入 `docs/human-encyclopedia/tools.json` 与 `docs/human-encyclopedia/tools.md` 两个文件；未改动 `data/`、StoryPackage、其他组文件或任何源码，未使用 git。

---

## 本轮复核记录（内容审查 / 最小修订）

本轮只做残留绝对表述、字符级讹误、来源表述与 MD–JSON 一致性的复核，**未扩条目、未新增来源、未改其他组文件或源码**。条目数仍为 40，来源仍为 38（全部 `read`），`review_status` 40/40 均为 `needs_review`。

**已修：条件性表述（避免绝对化）**

| 修改 ID | 问题 | 处理 |
| --- | --- | --- |
| `tools_irrigation_canal` | MD 索引写「**必须**配排水，否则盐渍化抵消增产」，与 JSON 本体的盐分收支表述不一致 | MD 改为「长期维持需管住盐分收支（排水不畅时盐渍化可抵消增产）」，与 JSON `conditions`/`exceptions` 对齐 |
| `tools_chisel` | 「石凿则**必须**配软锤」把常见做法写成硬规则 | 改为「通常配软锤……这是常见做法而非绝对规则，硬锤加轻击、逐步推进也存在」；MD 索引同步改为「石凿常用软锤」 |
| `tools_src_britannica_earthenware` | `supports` 写「无釉**不宜**贮液」，比条目本体更绝对 | 改为「未玻化/未施釉器型贮液有渗漏倾向，非绝对不可贮液」 |
| `tools_src_britannica_agri_tech` | `supports` 写「犁底层的形成与危害」，与条目本体「叠因而非必然」不一致 | 改为「紧实层的形成条件与危害（叠因，非单一机具必然产物）」 |

**核对通过（未改）**

- 无釉陶 / 贮液：`tools_storage_jar` 明确「不应反向推成无釉陶一概不宜贮液」，并列出施釉、提高烧结程度、内衬、器壁加厚等多条路径，同时保留蒸发降温一面。
- 盐渍化与灌溉：`tools_irrigation_canal` 写明盐渍化是盐分收支问题，「并非未配人工排水就必然盐渍化」。
- 轻犁 / 重土：`tools_ard_plough` 的 `summary`、`conditions`、`historical_scope` 均写「在坚重土壤上阻力大、效率低」，并明写「并不意味着轻犁在重土上完全不能划出沟」。
- 定滑轮：`tools_pulley` 三处均写定滑轮理想力比≈约 1、不降低张力，只改变方向与姿势，且补充摩擦会略增实际拉力、动滑轮才降低张力。
- 重犁 / 紧实层：`tools_moldboard_plough.exceptions` 已否掉「重犁必然造成犁底层」，并给出减轻途径。
- 来源：38 条均为 `read`；无 `search_only`、无 `unavailable`；每条 `source_ids` 至少含 1 条 `read`，引用的来源均已在 `sources` 登记。

**已修：字符级讹误（不涉内容判断，仅纠字）**

`tools_granary`（密团→密闭、塔漏→塌漏、虫蛙→虫蛀、噸掉→烂掉）、`tools_water_well`（防塔→防污、土壁塔塌→坍塌、滲水→渗水、处理塔塌→处理塌方、滴井→淘井、滘水→溪流、黩性→慢性、辘轴→辘轳）、`tools_storage_jar` / `tools_pottery_cooking_pot` / `tools_pottery_wheel`（土坏/坏土/湿坏/坏体/泥坏/器坏/爆坏/拉坏→坯；犀和料→掺和料；未致化→未玻化；萎缩→腌渍；轣斜→倾斜；坐折→挫折）、`tools_basket`（根与蜀→根与藤、有的太到→有的大到、好壤→好坏）、`tools_chisel`（楽子→斧子、` Egyptians`→`Egyptians`）。

**仍待证据（如实保留）**

- 本组年代学未逐条核对考古报告：有明确来源支撑的年代集中在磨石、陶器、轮与轴、水磨、风磨、钐、天平、螺旋钻、弓钻等少数条目；其余维持「各地区差异极大，不宜统一断代」。
- 纺轮与镰刀的专门文献未逐项核对，形制谱系与定年靠关联条目反推；已在各自 `evidence_and_uncertainty` 写明。
- 烹饪陶器形制与热震性能、铰接与提水装置的效率数值均未核对专门文献，属一般性归纳。
- 本节只说明结构、措辞与字符层面的核对结果，**不等于事实认证**；40 条仍需主审逐条复核。
