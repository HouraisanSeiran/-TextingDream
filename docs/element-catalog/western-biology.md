# western-biology：西方奇幻动植物候选素材（21 条）

> **状态：候选（`status: candidate`），不是世界正典，不是数据库实现，不是可执行规则。**
> 与同目录 `western.json`（54 条：龙、精灵、矮人、妖精、狼人、吸血鬼、制度与能力主干）与 `fantasy-races.json`（族群与核心机制）分工：本文件只记**可被猎捕、驯养、采集、种植、供奉或误认的具体动植物与菌类**，同一物只记一次，跨文件时用文字指向而不复制。全部 `detail_status` 为 `needs_detail`、`review_status` 为 `needs_review`；**没有任何一条通过内容主审**。
> 所有超自然机制一律标注为**本项目创作归纳**，不是史料结论；传说叙述不当作现实事实；资源不默认无限再生，治疗不默认万能。

- 元素：**21 条**（`kind:fauna` **10** / `kind:flora` **11**），原 ID 全部不变
- 来源：**25 条**（`read` 20 / `search_only` 1 / `unavailable` 4）
- 类别：全部 `category: life`；题材：全部含 `western_fantasy`，**11 条**另带 `dark_fantasy`
- **21/21 条含 `trait:original_setting`**：每条都有明确标注的西幻特有变体（见 §二）

---

## 一、`kind:flora` 是检索分组，不是分类学断言

**蘑菇是真菌，不是植物**（真菌在生物学上独立成界）。本文件把真菌归入 `kind:flora`，只是按「可采集的静止生长物」成组检索，**不构成任何分类主张**，条目内已逐条声明。同理 `kind:fauna` 收了被写成**智慧族群**的人鱼与山怪，也不表示它们属于可猎取的兽类。

顶层字段 `element_kind_note` 与 `tag_conventions.kind` 已写明这一口径。

## 二、西幻特有变体：保留现实生态为基础，另加明确标注的原创设定

主审要求「不是只把普通树木归到西幻」。做法：**每条现实条目保留可核生态作为底板，并新增至少一条以 `【原创设定】` 开头的西幻特有变体**；这些设定全部在 `trait:original_setting` 标签、`excludes` 与 `evidence_and_uncertainty` 中声明为**本项目创作，不伪称民俗**。

| ID | 名称 | 现实底板 | 新增的西幻特有变体（原创） |
|---|---|---|---|
| `western_bio_raven` | 渡鸦与纹章鸦群 | 食腐／囤物／学语／长寿 | 纹章鸦群（活的门第凭证）、以鸦群在场作立誓见证 |
| `western_bio_deer_herd` | 鹿群与角林禁猎 | 选择性取食／鹿角年脱 | 角林（鹿角作实物税、拾角权按户）、追角礼 |
| `western_bio_wolf_pack` | 狼群与悬赏牧区 | 家庭群／领域／牲畜冲突 | 狼账（验伤—悬赏—赔偿账册）、狼道（迁徙路线作公共地役） |
| `western_bio_mandrake` | 曼德拉草与人形根圃 | 有毒茄科／麻醉致幻 | 人形根圃（按形似度分级定价）、代拔仪（可买卖的替罪劳务） |
| `western_bio_yew` | 紫杉与弓材禁伐林 | 慢生／有毒／宜弓 | 世代许可（补植＋等材期押金，按代转让）、守林役 |
| `western_bio_oak` | 橡树与界树诉讼 | 长寿命／橡实／单宁 | 界树诉讼（老树作法定物证）、伐桩萌蘖权（独立可售权益） |
| `western_bio_mistletoe` | 槲寄生与除治义务 | 半寄生／吸器／反复清除 | 除治义务（法定年度劳役＋复查）、誓约树（除治与守誓冲突） |
| `western_bio_hawthorn` | 山楂与活篱役 | 刺篱／耐修剪／病害 | 活篱役（按户摊派、可折银）、篱籍（地权纠纷凭据） |
| `western_bio_ash_wood` | 白蜡木与材种专供 | 弹性木／专性害虫 | 材种专供（军需官造专用）、疫年禁运（查验与假印灰线） |
| `western_bio_willow` | 柳与割条轮休 | 插条易活／割条再生 | 割条轮休制（分段轮割入册）、插条争界（活体改写界线） |
| `western_bio_fern` | 蕨丛与弃耕标记 | 孢子繁殖／分型扩张 | 蕨籍（以蕨丛类型判定弃耕年数与复耕成本） |
| `western_bio_mushroom_ring` | 蘑菇与仙环标尺 | 菌丝体／仙环年扩 | 仙环纪年（反推事件年份）、采菇禁令（禁采圈与饥年开禁） |
| `western_bio_lamp_moss` | 灯藓（原创） | 无（纯设计） | 全部为原创：地下弱光苔、养护工艺、枯死条件 |
| `western_bio_iron_rust_vine` | 锈蚀藤（原创） | 无（纯设计） | 全部为原创：地带性腐蚀液滴、残渣禁区 |

**神话母题条目**（独角兽、狮鹫、鸡蛇、不死鸟、海蛇）同样新增了原创变体，例如：角杯检定所、巢市授证、封锁令与检疫、周期司、采信法庭——均标为原创设定，不冒充制度史或民俗。

### 全部 21 条一览（ID · 名称 · 原创西幻变体）

| ID | 名称 | kind | 原创西幻变体（要点） |
|---|---|---|---|
| `western_bio_unicorn` | 独角兽与角材传说 | fauna | 角杯检定所（验角职司、错判与贿赂） |
| `western_bio_griffin` | 狮鹫 | fauna | 巢市授证（攀崖取卵需特许与附保人） |
| `western_bio_cockatrice` | 鸡蛇与石化蜥 | fauna | 封锁令与检疫（封锁本身成为可滥用的权力） |
| `western_bio_phoenix` | 不死鸟 | fauna | 周期司（推算显现周期、校准历法、错算即失位） |
| `western_bio_sea_serpent` | 海蛇与巨物目击 | fauna | 采信法庭（裁定目击是否成立，决定执照与保险） |
| `western_bio_mermaid` | 人鱼群体与浅海生态 | fauna | 育幼湾（封闭育幼区成为沿岸政治议题） |
| `western_bio_troll` | 山怪栖地与冬牧场 | fauna | 冬牧冲突（年度边境事件与轮守、诱离、补偿） |
| `western_bio_raven` | 渡鸦与纹章鸦群 | fauna | 纹章鸦群、以鸦群在场作立誓见证 |
| `western_bio_deer_herd` | 鹿群与角林禁猎 | fauna | 角林（鹿角作实物税、拾角权按户）、追角礼 |
| `western_bio_wolf_pack` | 狼群与悬赏牧区 | fauna | 狼账（验伤—悬赏—赔偿账册）、狼道（迁徙路线作公共地役） |
| `western_bio_mandrake` | 曼德拉草与人形根圃 | flora | 人形根圃（按形似度分级定价）、代拔仪（可买卖的替罪劳务） |
| `western_bio_yew` | 紫杉与弓材禁伐林 | flora | 世代许可（补植＋等材期押金）、守林役 |
| `western_bio_oak` | 橡树与界树诉讼 | flora | 界树诉讼（老树作法定物证）、伐桩萌蘖权 |
| `western_bio_mistletoe` | 槲寄生与除治义务 | flora | 除治义务（法定年度劳役＋复查）、誓约树 |
| `western_bio_hawthorn` | 山楂与活篱役 | flora | 活篱役（按户摊派、可折银）、篱籍 |
| `western_bio_ash_wood` | 白蜡木与材种专供 | flora | 材种专供（军需官造专用）、疫年禁运 |
| `western_bio_willow` | 柳与割条轮休 | flora | 割条轮休制（分段轮割入册）、插条争界 |
| `western_bio_fern` | 蕨丛与弃耕标记 | flora | 蕨籍（判定弃耕年数与复耕成本） |
| `western_bio_mushroom_ring` | 蘑菇与仙环标尺 | flora | 仙环纪年（反推事件年份）、采菇禁令 |
| `western_bio_lamp_moss` | 灯藓（原创） | flora | 全部原创：地下弱光苔、养护工艺、枯死条件、层位指示 |
| `western_bio_iron_rust_vine` | 锈蚀藤（原创） | flora | 全部原创：地带性腐蚀液滴、残渣禁区、找矿指示 |

## 三、人鱼与山怪：转向生态，不复写核心机制

主审指出这两条与 `fantasy-races.json` 重复。已确认为：

- `fantasy_race_merfolk_bargain`（人鱼与海陆婚姻赎回）——已完整处理**「婚姻靠被藏物件维持」**机制
- `fantasy_race_troll_daylight`（巨怪与日光限制者）——已完整处理**受光爆裂／石化**机制，含石化可逆、个体不畏光等变体

因此本文件这两条**改向生境／食物／繁殖／迁徙／照料生态**，并在 `excludes`、`requires`、`historical_scope`、`evidence_and_uncertainty` 四处显式声明不重复：

| ID | 新名称 | 本条只写 | 明确不复写 |
|---|---|---|---|
| `western_bio_mermaid` | 人鱼群体与浅海生态 | 栖地形态、食性、繁殖育幼节律、洄游路线、幼体照料；与沿岸渔场／育幼湾的资源竞争 | 婚姻物件赎回、见之则船难、塞壬谱系 |
| `western_bio_troll` | 山怪栖地与冬牧场 | 巢址忠诚与领地、杂食食腐、繁殖分巢、季节性下移与冬牧场冲突 | 日光致毁与石化 |

**智慧族群处理**：人鱼明确禁止按素材采集或驯养处理——`excludes` 写明「没有取泪、取鳞、圈养繁殖一类的资源化处理」，与人打交道只能走交涉、贸易、共居、冲突四条。山怪同样写为「活体不可驯，材料取自遗落物与巢址堆积，而非猎取本体器官」。

## 四、传说层与现实的区分（主审第 3 点）

| 条目 | 必须区分的点 |
|---|---|
| 独角兽 | **「角可防毒」是传说与候选设定，不是现实事实**；`summary`／`mechanism`／`excludes`／`evidence_note` 均明写，并指出来源本身记载流通角材实为犀角与独角鲸牙 |
| 曼德拉草 | **「尖叫致死」属传说层**，与可核的托烷生物碱毒性分层陈述；不提供任何剂量、处方与采收操作 |
| 紫杉 | **不给任何可食／不食判断或去毒指引**，只说明「叶与种子含毒、假种皮不含」；不据此推断任何部位可食 |

## 五、已纠正的过度概括（主审第 3 点）

| 原表述 | 改为 | 依据 |
|---|---|---|
| 蘑菇：摘取子实体对本体绝无影响 | 摘取**通常不直接杀死**菌丝体，但反复剥离、撕断基质、踩实土壤或伤及共生树根仍会损害，且种类差异大 | 来源只支持「子实体是孢子果、菌丝体在地下」 |
| 蕨：所有蕨类都靠根状茎横行蔓延 | **只有部分强蔓延型**（如欧洲蕨）如此；另分丛生型／直立型／浮水型，扩张方式不同 | 来源的根状茎扩散表述是就特定种类而言 |
| 狼：以老弱病畜为主要猎物 | 被杀者中「**很大比例**」为幼、老或体弱者，**但不等于只猎老弱**，健康个体同样会被杀 | 按来源原话口径修正 |

三处均在 `details.evidence_and_uncertainty` 中留下「对过度概括的自我修正」记录。

## 六、其余保留设定

**21/21** 条 `details` 使用 `app/encyclopedia.py` 的七规范键（字符串、齐备、无多余键）：`definition` / `mechanism` / `conditions` / `exceptions` / `story_uses` / `historical_scope` / `evidence_and_uncertainty`。⚠ 与 `western.json` 旧键（`story_consequences` / `adaptation_limits`）不同，不可互拷。

标签：`kind:` + `tradition:western` + `trait:original_setting` + `habitat:`/`trait:`/`role:`；**不手写 `genre:`／`category:`**（由导入器按字段追加）。全部无 `related_ids`／`related_catalog_ids`。

## 七、来源（25 条，未重新采集，全部沿用上一轮已读）

`read` 20（Britannica：unicorn、bestiary、griffin、cockatrice、phoenix、sea serpent、mermaid、troll、raven、wolf、deer、mandrake、yew、oak、mistletoe、hawthorn、ash、willow、fern、mushroom）／`search_only` 1（Physiologus，零引用）／`unavailable` 4（basilisk 404、monkshood 403、kraken 抽取失败、wyvern+roc 404，均零引用）。

**本轮修订未新取任何来源**：主审明确「读过 sources 不需重采」，故全部改动限于条目文本层的分层、限定与新增原创变体。

## 八、验证结果

```
count: 21 | ids unchanged: True
fauna: 10  flora: 11  dark_fantasy: 11
structural issues: []
IMPORT: 21 elements / 25 sources / relations 0 | unresolved []
```

| 检查项 | 结果 |
|---|---|
| 条数 21、原 ID 与顺序完全不变 | ✅ |
| `details` 七规范键齐备、字符串、无多余键 | ✅ 21/21 |
| `category=life` / `review_status=needs_review` / `detail_status=needs_detail` | ✅ 21/21（待审标记全部保留） |
| 标签无手写 `genre:`／`category:` | ✅ 0 |
| 每条带 `tradition:western` 与 `habitat:`/`trait:`/`role:` | ✅ 21/21 |
| `trait:original_setting` | ✅ 21/21 |
| `source_ids` 悬空 / 引用非 `read` 来源 / 未被引用的 `read` | ✅ 0 / 0 / 0 |
| 含 `related_ids`／`related_catalog_ids` | ✅ 0 |
| 人鱼含婚姻物件机制 / 山怪以日照为主机制 | ✅ 均无（各在 excludes 显式声明不重复） |
| 三处过度概括措辞 | ✅ 已清除 |
| UTF-8 无 BOM | ✅ |

## 九、边界声明

1. 仅修改 `western-biology.json` 与 `.md` 两个文件；未改 `fantasy-races.json`、`western.json`、`collection-spec.md`、`README.md` 或任何源码；未动实际库；未运行服务、地图、Terragenesis；未装依赖。
2. 原创设定一律以 `【原创设定】` 标注并配 `trait:original_setting`，**不伪称民俗或史料**。
3. 不默认成立：无限资源、万能治疗（含角材解毒）、可随意繁殖或驯养。
