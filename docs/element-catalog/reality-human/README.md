# 现实基础库 · 人与制度（reality-human）—— 分区说明

本分区存放**现实基础库—人与制度侧**候选：历史制度、宗教与信仰实践、家庭组织、法律经济。

数据文件：`../reality-human.json` 与 `../reality-human.md`（题材标签 `real_world`）。

## 当前状态

**已交付，但尚未封版。** 下表为本环节直接读取 `../reality-human.json` 的实测值，**以该 JSON 实时为准**。

> 注：旧版本文写作「31 条，采集中」。当前 JSON 与 `../reality-human.md` 已对齐为 31 条，**不再标为采集中**；但仍不排除后续扩充。

与 `reality-physical` **分开存放、分开统计**，两者不混成一张表，也不与四个虚构题材组相加。

> 职责划分（已定稿）：`reality-human` 负责**社会应对与组织制度**（医院、保险、检疫授权、交通治理、经济法律）；可验证的物理／生物／生态机制与工程条件归 `reality-physical`。交叉处用真实 ID 关联，不重复造双权威。

| 项 | 实测 |
|---|---|
| 元素 | **31** |
| 来源 | **55**（`read` 44 / `unavailable` 11 / `search_only` 0） |
| 题材标签 | 全部 `real_world`，无其他标签 |
| 类别分布 | institution 15、organization 8、economy 6、place 1、power 1 |
| `details` 覆盖 | **31/31**（七节均非空） |
| `detail_status` | 全部 `needs_detail`（**无一条 `reviewed_detail`**） |
| `knowledge_kind` | historical 16、mixed 10、belief_description 5（`empirical` 0） |
| `related_catalog_ids` | **113** 个引用，覆盖 31/31 条，**零悬空、零自指** |

指向分布：society 51 / steam-horror 26 / western 18 / eastern 6 / reality-physical 6。

「已交付」只意味着文件到了、`details` 七节齐备；**不意味着已审核**。本分区**未见主审逐条点名返修记录**（不同于 `reality-physical`），因此它比另一分区**更少经过人工复查**。

## 与 society 组的关系（重要）

已有 society 组已覆盖大量历史／当代制度（行会、宗族、采邑、科层官僚、劳动合同等）。本分区**不重复创建已有变体**，以**引用／关联**为主：

- 需要的制度细节已在 society 组里的，直接引 `society_*` 的 id，不另起一条。
- 本分区只收 society 组未覆盖、且能影响人物行动、世界构建或事件因果的现实知识。
- **实测验证**：113 个 `related_catalog_ids` 中指向 `society` 的 51 个；与四组及 `reality-physical` **零同名冲突**。

## 已先立下的原则

1. **要分四类**：用 `knowledge_kind` 区分 `empirical` / `historical` / `belief_description` / `mixed`。宗教类条目几乎总是 `belief_description` 或 `mixed`，不写「仪式真能驱邪」。当前 31 条里 `empirical` 为 **0**——人文侧本来就不该有纯实验机制，**不是缺陷**。
2. **限地域与时期**：历史制度条目必须带地域与时间范围，不能当作世界通例（这也是 society 组已暴露的弱项，见 `../review-notes.md` §3.6）。
3. **不是只有游戏机制**：要能提供制度运作、权力分配、争议与失败模式，而不只是数值。
4. **安全边界**：不写现实伤害、违法或操控他人的操作教程。
5. **来源失败如实记录**：11 条 `unavailable`（占来源总数 55 的 20%）**一律未进 `source_ids`**，未拿失败来源充数。

## 字段口径

保留统一 14 字段，**增加** `knowledge_kind`、`related_catalog_ids`、`details` 分节与 `detail_status`，**不设完整内容字数上限**。

七节固定为 `definition` / `mechanism` / `conditions` / `exceptions` / `story_consequences` / `adaptation_limits` / `evidence_and_uncertainty`，**31/31 均齐备、均非空**。实测体量：每条 808—1890 字，均值 1017，合计约 3.2 万字。

## 已知弱项

- **来源总量最大但失败率也最高**：55 条里 11 条 `unavailable`（`_36`—`_41`、`_51`—`_55`）。虽均零引用，但意味着本分区有大量拟定词条未取到。
- **5 条自述为导言/摘要级**（`_01`/`_21`/`_34`/`_35`/`_50`），不能支撑全文细节；其中 `_50`（FAO 目录页）**未被任何元素引用**。
- 本分区**未见主审逐条点名返修记录**（对比 `reality-physical` 已过一轮），因此未被人工复查的条目占比比另一分区高。

## 待主审决定

- 与 `reality-physical` 的边界：公共卫生 vs 医疗制度、生产交通通信 vs 法律经济。（已定：按管辖对象切）
- 现代制度条目是否要求**多地域并置**（而不只是中国当代法条口径）。
- 宗教类条目的「信仰 vs 事实」边界，是否需要一个统一句式模板。（当前 5 条 `belief_description` 在 `evidence_and_uncertainty` 内部各自表述，口径不统一）
- 是否需要对本分区做一轮与 `reality-physical` 同规格的主审点名复查。

以上问题已同步记在 `../review-notes.md` §6。
