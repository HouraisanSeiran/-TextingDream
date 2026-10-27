# 现实基础库 · 物理与自然（reality-physical）—— 分区说明

本分区存放**现实基础库—物理与自然侧**候选：自然与地理、物理化学／能源材料、农业生态／公共卫生、生产交通通信。

数据文件：`../reality-physical.json` 与 `../reality-physical.md`（题材标签 `real_world`）。

## 当前状态

**已交付、已过一轮主审点名返修（2026-10-26）、仍未封版。** 下表为本环节直接读取 `../reality-physical.json` 的实测值，**以该 JSON 实时为准**。

与 `reality-human` **分开存放、分开统计**，两者不混成一张表，也不与四个虚构题材组相加。

> 职责划分（已定稿）：本分区负责**可验证的物理／生物／生态机制与工程条件**（病原传播、饮水、食物等）；**社会应对与组织制度**（医院、保险、检疫授权、交通治理、经济法律）归 `reality-human`。交叉处用真实 ID 关联，不重复造双权威。

| 项 | 实测 |
|---|---|
| 元素 | **32** |
| 来源 | **36**（`read` 33 / `unavailable` 3 / `search_only` 0） |
| 题材标签 | 全部 `real_world`，无其他标签 |
| 类别分布 | place 9、power 8、item 6、economy 5、institution 3、conflict 1 |
| `details` 覆盖 | **32/32**（七节均非空） |
| `detail_status` | 全部 `needs_detail`（**无一条 `reviewed_detail`**） |
| `knowledge_kind` | empirical 25、mixed 6、historical 1（`belief_description` 0） |
| `related_catalog_ids` | **97** 个引用，覆盖 32/32 条，**零悬空、零自指** |

指向分布：steam-horror 46 / society 22 / western 19 / eastern 9 / reality-human 1。

「已交付」只意味着文件到了、`details` 七节齐备；**不意味着已审核**。主审点名返修只改了 `reality-physical.json` 与 `reality-physical.md`，**未升格任何一条**。

## 主审返修与待复验

`../reality-physical.md` 第七节已逐条列出「原先的问题 / 改为 / 依据」。四条点名条目（`reality_phys_gravity_load`、`reality_phys_measurement_precision`、`reality_phys_food_preservation`、`reality_phys_drinking_water_sanitation`）的**文案层面对照结果见 `../README.md` §11.3**。

⚠ **关键保留**：本环节只对照了文案，**没有回溯任何来源原文**。尤其是：

- 重力条目的 E=mgh 与平方反比——已确认为正确写法。
- **测量条与饮水条已在第二轮补全定义**：测量条补入重复性/中间精密度/再现性三层；饮水条补入 safely managed 四要素（含“不受粪便及优先关注化学物质污染”）。**这两处改动的依据只是条目已有 `source_ids` 的 `supports` 字段记载，本轮未重新抓取 VIM3 / WHO 正文复核**，因此**不得声称“已通过事实审核”或“已全改正”**。
- `rp_src_35`（VIM3 四个词条页）与 `rp_src_36`（JCGM 目录页，**自述未读正文**）的支撑强度仍未复核。

## 已立下的原则

1. **不混统**：现实条目与虚构条目不共用同一张表、不共用同一套「引入阶梯」默认值。
2. **要分四类**：用 `knowledge_kind` 区分 `empirical`（可检验机制）/ `historical`（带地域时期的史实）/ `belief_description`（信仰与传统的记述）/ `mixed`（争议或混合）。当前 32 条里 `belief_description` 为 **0**——物理侧本来就不该有，**不是缺陷**，不建议为分布好看而互调。
3. **不当事实**：不把神迹、修行或灵异效力当科学事实。
4. **不是只有游戏机制**：要能提供可核对的背景（工艺、地理、生态、能源链），而不只是数值。
5. **安全边界**：事实精确度与操作细节以故事用途为限，**避免危险实验、医疗处方或现实伤害操作教程**。
6. **来源**：优先机构／博物馆／教育与可靠参考；未核实处如实标注。

## 字段口径

保留统一 14 字段，**增加** `knowledge_kind`、`related_catalog_ids`、`details` 分节与 `detail_status`，**不设完整内容字数上限**。

七节固定为 `definition` / `mechanism` / `conditions` / `exceptions` / `story_consequences` / `adaptation_limits` / `evidence_and_uncertainty`，**32/32 均齐备、均非空**。实测体量：每条 766—1721 字，均值 905，合计约 2.9 万字（第二轮补写饮水/测量定义后略增）。

## 已知弱项

- **强度类来源只支撑定性结论**（材料强度、压强、重力载荷），**不提供可作工程使用的数值**；其中 `rp_src_09`（strength of materials）、`rp_src_23`（food preservation）**仅得导言段**。
- `rp_src_16`（geomorphology）、`rp_src_22`（carrying capacity）为短条目／导言级。
- 3 个 `unavailable`（`rp_src_33` USGS、`rp_src_34` NIST、`rp_src_37` food spoilage）**均零引用**，且已改换支撑来源。
- 反复出现的绝对词已在本组做过一轮双向排查；遗留的强断言候选列在 `../README.md` §11.2（本组为 0 句）。

## 待主审决定

- 与四个虚构组是「单向引用」还是「双向交叉索引」？（当前是**单向**：本组指题材库，题材库无 `related_catalog_ids` 字段）
- 是否允许直接承载具体数值（如煤热值、人口密度），还是只给区间与条件？（当前**刻意不给**）
- 与 `reality-human` 的边界如何切（例：公共卫生算物理侧还是人权侧）？（已定：**机制在 physical，应对制度在 human**）

以上问题已同步记在 `../review-notes.md` §6。
