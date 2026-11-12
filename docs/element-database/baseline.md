# 元素数据库现状基线

日期：2026-11-11。本轮只读源文件、代码与现有 SQLite，未构库、未迁移、未启动服务、未修改故事包，未逐条事实核验，也未重跑游戏测试。

## 1. 统计口径

- 源文件范围：`tools/encyclopedia_build.py` 中 `GROUPS` 及独立的 `*_GROUPS` 元组名单，共 53 份文件。不是整个 docs 目录的所有 JSON。
- 源候选数：各文件 `elements` 长度之和，不代表去重后的概念数，也不代表已入库或已审核。
- 库路径：`artifacts/human-encyclopedia/encyclopedia.sqlite3`，用 SQLite `mode=ro` 查询。
- 当前元素数：`elements` 行数；历史版本数：`element_versions` 行数。不能混算。

| 显式名单 | 文件数 | 源候选数 |
|---|---:|---:|
| 默认基础 GROUPS | 14 | 528 |
| 特质 | 1 | 23 |
| 基础饮食 | 1 | 24 |
| 文化、姓名、诗歌、神话、宗教 | 9 | 249 |
| 属性 | 1 | 6 |
| 奇幻生物与种族 | 3 | 64 |
| 魔药与丹药 | 2 | 40 |
| 现实药材 | 4 | 145 |
| 方剂文献 | 1 | 35 |
| 法餐与英餐 | 2 | 49 |
| 世界设定、政体、科技 | 5 | 93 |
| 中餐、欧陆、拉美菜系 | 3 | 89 |
| 店铺 | 1 | 37 |
| 建筑 | 1 | 753 |
| 职业 | 2 | 68 |
| 文明风格与人名用字 | 2 | 7 |
| 人物/物品词条 | 1 | 37 |
| **合计** | **53** | **2247** |

源文件中的状态字段有部分省略；导入器会派生默认待审状态，不能把字段缺省解释成“审核通过”。

## 2. 本机现有库

| 指标 | 只读查询结果 |
|---|---:|
| schema_version | 2 |
| 命名空间 groups | 52 |
| 当前元素 elements | 2205 |
| 元素历史版本 element_versions | 4777 |
| 当前来源 sources | 1689 |
| 来源历史版本 source_versions | 1694 |
| 当前状态 needs_review + needs_detail | 2205 |

与显式源名单的**数量**对照：
- `fantasy-affixes` 源文件 37 条，当前库无该 namespace。
- `town-buildings` 源文件 753 条，当前库 748 条；本轮没有定位具体差异 ID，不能认定仅为新增而无修改。
- 其余组数量相同；**数量相同不证明 payload、overlay 或来源版本相同**。
- 当前库没有名单外 namespace。

## 3. 数据与代码结构

`app/encyclopedia.py:634–760` 定义 11 张业务/元数据表（另有 SQLite 自用表）：

| 表 | 职责 |
|---|---|
| meta / groups | schema、命名空间、适配器与组元数据 |
| elements / element_versions | 当前指针及完整历史 payload、详情、状态 |
| sources / source_versions | 当前来源指针及历史来源记录 |
| element_names / element_tags | 名称、别名与多维检索标签 |
| element_sources | 元素版本引用的固定来源版本 |
| element_relations | 普通关联；不是机器依赖 |
| import_batches | 导入批次记录 |

身份是 `(namespace, element_id)`，精确版本再加 `version`。原始对象信息以 canonical JSON 保存，不保留原文件排版。版本只追加由应用逻辑保证，不应宣传为数据库触发器强制不可变。

构库会在内存中叠加游戏字段与主标签 overlay，再导入；因此库内 payload 不一定逐字等于源文件对象。源 JSON、overlay、生成库必须分别说明。

## 4. 已实现与未实现

| 能力 | 当前边界 |
|---|---|
| 导入、版本、导出恢复 | 已实现；单份文档导入原子，整次多文件构库不是一个总事务 |
| 搜索 | 名称/别名子串、标签、命名空间等筛选；不搜详情全文，不是语义搜索 |
| 来源固定 | 元素历史版本固定来源记录的版本；不是自动保存外部网页全文 |
| 普通关联 | 查询时解析 resolved/pending/ambiguous；不固定目标元素版本，不代表可执行依赖 |
| 作者装配 | 选精确版本、确认候选状态、写入 story.mechanics.element_manifest |
| 开局锁定 | 完整条目与来源快照进入故事包；旧旅程不随全局库升级 |
| 机器依赖 | 作者显式声明的 typed requires/conflicts；自然语言 requires/excludes 不会自动执行 |
| 公开范围 | disclosure 白名单与受众/地点/标记控制，不直接把作者完整 payload 给玩家 |
| AI 草稿 | 作者确认元素草稿可显式写入既有候选库；这不等于采纳进故事包 |
| 审核 | 没有独立审核升格工作流；导入与采纳不自动证明事实正确 |
| 游戏规则编译 | 没有通用的百科→奖励、法术、配方规则自动映射 |

核实依据：`app/encyclopedia.py`、`app/element_assembly.py`、`app/ai_drafts.py:618–685`、`tools/encyclopedia_build.py:279–351`。

`--check` 主要核对选定分组存在及条数，不是逐项内容、来源、overlay 的完整一致性证明。标签统计还可能包括历史版本，不能当当前元素数量。

## 5. 已发现的规范债务

1. 旧说明混合 12 组/481、14 组/528、原题材 274 等不同范围；它们是历史批次，不是当前总库数量。
2. 旧文档同时存在“开局锁定待实现”和后加“已实现”段落，以代码及当前装配能力为准。
3. `docs/units.md` 已明确整数铜币、公制和十进制；但 `game-fields-spec.md` 仍写旧便士/先令/镑。本轮只读当前库发现旧价格 tier：shilling 159、groat 216、penny 101、pound 16，共 492 条；另有 not_for_sale 2、priceless 2，1709 条无 game.price.tier。**不能把无价格一概认定为缺失，制度/姓名等未必适用。**
4. 源文件新旧七节混用，`adaptation_limits → historical_scope` 只是适配器近似对齐，不能据此把跨题材适配说明理解成历史事实。
5. 当前所有元素仍待审；`access=read` 与 `evidence_grade=sourced` 都不是逐条事实审核通过。

以上仅记录问题，不授权本轮顺手迁移或改写数据库。后续修复要保留已有版本、来源 pin 和故事包快照。
