# 人类百科素材库 · 数据库与 CLI 使用说明

> **批次验收记录（2026-11-08 整理）**：开篇的 12 组 / 481 条和「341 项 exit 0」停在当时那一次构库。现行组数以 `tools/encyclopedia_build.py` 为准，工程边界见 [../现状.md](../现状.md)。

当时记录的状态：候选素材数据库已生成并通过那一轮技术验收。 交付文件为 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（schema 2 / export 2，12 组、481 条资料条目、438 条来源记录）。主代理独立完整回归341项：338通过、3项符号链接权限跳过，退出码0；数据库完整性、来源版本固定、幂等导入与导出恢复已验证。内容仍为待审候选，不代表全部事实已经核实；不自动接入故事或旅程。

> **本轮（增补两组）**：构库名单从 12 组扩到 **14 组**，新增 `food-supplement`（23 条 / 30 来源）与 `craft-supplement`（24 条 / 34 来源），共 **+47 条**；全名单预期为 **528 条资料条目、502 条来源记录**。两个增补组是新增 namespace，**不改动**旧 12 组的任何行（同库导入旧内容逐字段不变，见 §11）；交付库仍待主编验收后显式生成，本环节只用临时库。

- 代码：`app/encyclopedia.py`（库与导入/查询实现）、`tools/encyclopedia_cli.py`（CLI）、`tools/encyclopedia_build.py`（按显式 14 组名单构库，可选 `--with-traits` / `--with-cuisine` / `--with-attributes` / `--with-culture` / `--with-fantasy-biology`）
- 测试：`tests/test_encyclopedia.py`（库与 CLI 本体）、`tests/test_encyclopedia_supplement.py`（14 组名单扩展与两个增补组集成）、`tests/test_encyclopedia_traits.py`（特质分区）、`tests/test_encyclopedia_cuisine.py`（饮食分区）、`tests/test_culture_catalog.py`（文化／姓名分区）、`tests/test_encyclopedia_attributes.py`（属性分区）、`tests/test_encyclopedia_fantasy_biology.py`（奇幻生物分区：种族／西幻动植物／东方玄幻动植物）
- 数据来源：`docs/human-encyclopedia/*.json`（新七节 schema，含 food-supplement / craft-supplement 两个增补组）、`docs/element-catalog/*.json`（原六组 274 资料条目）。**本模块只读它们，从不改写。**

> **后面的分区是显式开关，不默认入库**：特质在 `TRAIT_GROUPS`（`--with-traits`），
> 饮食在 `CUISINE_GROUPS`（`--with-cuisine`，可与前者组合）。不带任何开关时仍是历史 14 组，
> 旧测试里的 14 / 528 / 502 与 15 / 551 / 505 断言全部保留未改。
> 饮食分区还在增补，它的条数会变，**本文不写它的固定数字**：要当前值就自己跑一句
> `--with-traits --with-cuisine --check`（读源文件重算）。
>
> **奇幻生物分区（本轮新增）**：种族／西幻动植物／东方玄幻动植物在另一份显式名单
> `FANTASY_BIOLOGY_GROUPS`，对应开关 `--with-fantasy-biology`，同样默认不进库，
> 可与其他开关任意组合。三份内容文件由采集侧定稿，**本文不写它们的固定条数**。

---

## 1. 边界（先说清楚它不是什么）

| 是 | 不是 |
|---|---|
| 独立的本地 SQLite 素材库，路径由 `--db` 显式指定 | 不是旅程数据库 `saves/textiledream.sqlite3`，两者零关联 |
| 候选资料 + 来源 + 多标签 + 审查状态的存放处 | 不是故事正典：库里有 ≠ 世界里有，更 ≠ 人物知道 |
| 只读查询工具（search / get / versions / tags / stats / export） | 不参与 app 启动、不自动填库、不进故事 prompt、不碰旧存档 |
| 显式 CLI 导入 | 不提供运行时从全局库取资料条目的入口；开局绑定仍是后续独立设计 |
| 词法检索（SQL `LIKE` + 标签表） | 不做向量/embedding 检索，不调用远程模型，不新增依赖 |

`app/main.py` 与 `launch.py` 都没有引用本模块（`tests/test_encyclopedia.py::IsolationTests` 会断言这一点）。

---

## 2. 库结构（schema_version = 2）

固定有限 schema，不做任意文档存储。**原始对象整份存在 `payload_json`**，提升成列的只是少数可查询字段，因此「原字段无损」不依赖字段清单的完备性。

> **schema 2 相对 schema 1 的变化**：`element_sources` 新增 `source_version`（证据版本固定点，见 §3.5）。schema 1 的库**不支持就地升级**——旧库没有记录过 pin，无法反推历史证据，强行补一个等于编造。遇到 schema 1 会明确报错并要求用新路径重建、重新导入采集 JSON。导出格式同步升到 `export_version = 2`（`source_refs` 必填 `source_version`）。

| 表 | 作用 |
|---|---|
| `meta` | `schema_version=2`、`created_at` |
| `groups` | 每个命名空间一行：`group_id`、`schema_kind`（human / element-catalog）、`adapter`、`legacy_schema`、`status`、`meta_json`（文档级非 elements/sources 字段） |
| `sources` | 每个命名空间内每个来源的当前版本指针 + 标题/URL/access |
| `source_versions` | 来源的不可变版本；`UNIQUE(namespace, source_id, payload_hash)` |
| `elements` | 每个命名空间内每个条目的当前版本指针（`current_version`）、名称、两种状态 |
| `element_versions` | 条目的不可变版本：`content_hash`、完整 `payload_json`、七节 `details_json`、`details_map_json`、`details_extra_json`、批次号；`UNIQUE(namespace, element_id, content_hash)` |
| `element_tags` | 每版本的多标签（英文小写） |
| `element_names` | 每版本的名称与别名 + 归一化检索键（`norm`） |
| `element_sources` | 每版本 → 来源，记 `source_namespace`、**`source_version`（固定的证据版本）** 与解析状态 |
| `element_relations` | 每版本的关联（`related` / `catalog_related`），状态在查询时按目标是否存在计算 |
| `import_batches` | 导入/还原批次台账，`UNIQUE(namespace, batch_hash)` 即幂等闸门 |

主键是 `(namespace, element_id)`：**不同命名空间允许出现同一个 element_id**，各存各的，不互相覆盖。

---

## 3. 版本与幂等策略

1. **内容哈希**：`content_hash = sha256(canonical_json(原 element 对象))`（键排序、紧凑分隔、拒绝 NaN）。
2. **资料条目级幂等**：同一 `(namespace, element_id)` 下同哈希已存在 → **不新增版本、不重写行**。内容只要变一个字节 → `version+1`，旧版本永久可读（`get --version N`）。
3. **批次级幂等**：`batch_hash = sha256(namespace + adapter + 整份文档)`。重复导入同一文件直接返回 `idempotent=True`，零写入。只改文档级字段（如 `updated`）也算新批次，但资料条目同哈希仍不新增版本。
4. **不可变**：`element_versions` / `source_versions` 只插入。恢复导出时若同一版本号已存在且内容不同 → `Conflict`，拒绝覆盖历史。
5. **来源版本**：来源同样带版本。同名来源内容变了 → 新版本，资料条目按 `source_namespace` 指回真实来源，不会串组。

### 3.5 证据版本固定（pin）

资料条目版本写入时，把「当时看到的那一版来源」写进 `element_sources.source_version`：

| 场景 | 行为 |
|---|---|
| 资料条目 v1 引用来源 v1，之后来源升到 v2 | 资料条目 v1 **仍读 v1** 的 title/url/access/payload；`is_current_source_version=false` 只作提示 |
| 只改来源、资料条目 payload 不变 | 不新增资料条目版本（`element_versions_written=0`），**不重写历史关联**，也不静默把证据换成 v2 |
| 需要新证据 | 必须**显式写一个新资料条目版本**（内容变了 → 新 `content_hash` → 新 version），新版本 pin 当时的来源版本 |
| 同批导入 | 按来源内容哈希精确定位刚写入的版本号，不拿 `current_version` 猜 |
| 导出/还原 | `source_refs` 必带 `source_version`；还原时校验 pin 指向导出文件里真实存在的来源版本，缺失或越界**整份拒绝** |

`get(element, version=N)` 与 CLI `get --version N` 返回的就是该版本的固定证据，不受之后任何来源更新影响。

---

## 4. 来源、关联与状态

### 来源解析（否则整批拒绝）
资料条目 `source_ids` 按顺序解析：**同批 → 本命名空间 → 全局唯一**。找不到 → 拒绝；多个命名空间都有同名来源 → 拒绝（歧义）。

`access: read` 只表示采集侧声称读过正文，**不表示已事实核实**。库里只记录原值。

### 关联（不允许假称有效）
`related_ids` / `related_catalog_ids` 的目标可能属于后续批次或别的组。关联**原样保存**，状态在查询/导出时按「目标此刻是否存在」实时计算：

| 状态 | 含义 | 能否当成有效关联 |
|---|---|---|
| `resolved` | 目标已入库（同命名空间或多个命名空间里的唯一一个） | 可以 |
| `pending` | 目标还没入库 | **不可以**，只是待解析 |
| `ambiguous` | 目标在多个命名空间都有 | **不可以**，必须显式指定 |

后续批次把目标导进来后，同一条关联自然变成 `resolved`，不需要改写历史。跨命名空间不会“猜”一个目标。

### 审查状态（绝不自动升格）
- `review_status` / `detail_status` 只记录 payload 里**显式写下的值**；缺失时派生 `needs_review` / `needs_detail`。
- 派生逻辑不可能产出 `reviewed_detail`；本模块**没有任何升格路径**（CLI 也没有）。
- 原六组 274 条全部保持 `needs_detail` + `needs_review`（测试逐条断言）。

---

## 5. 两种 schema 与旧六组适配

| | 新 schema（`docs/human-encyclopedia`） | 旧 schema（`docs/element-catalog` 六组 274 条） |
|---|---|---|
| 识别 | 资料条目都带 `tags` | 资料条目都带 `category` |
| 七节 | `definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty` | `… / story_consequences / adaptation_limits / evidence_and_uncertainty` |
| 映射 | 同名直通 | **显式 adapter**，映射记在 `details_map`：`story_uses ← story_consequences`、`historical_scope ← adaptation_limits` |
| 标签 | 保留原 `tags`，另加 | `category:X`、`genre:Y` 命名空间化标签 |

要点：

- `adaptation_limits → historical_scope` 只是**七节命名对齐的语义近似**：原字段讲的是「跨题材改编边界」，不是现实史实。原字段名和原文都留在 `payload.details` 里，`details_map` 会明确标出来（`get` 的文本输出也会打印「原字段 …」）。
- 其他分节（如 `western` 的 `parameter_dimensions`，是对象而非字符串）原样进 `details_extra`，**不强制统一类型、不丢弃**。
- `variants / story_roles / requires / excludes / background / entry_modes / introduction_limits / evidence_note / genre_relevance / related_catalog_ids` 等全部保留在 payload 中，`get` 可直接读回。
- `shared-themes.json` 是聚类索引，**不是资料条目**；导入会被明确拒绝（`InvalidDocument`）。

---

## 6. 上限与拒绝（半批零写入）

单批次先在内存里全量校验，再在**一个 `BEGIN IMMEDIATE` 事务**里写入；任何异常 → `ROLLBACK`，库里一行都不留。

| 上限 | 值 |
|---|---|
| 单份 JSON 文本 | 32 MiB |
| 单批资料条目 / 来源 | 5000 / 5000 |
| 单个元素/来源 payload | 96 KiB |
| 单个文本字段 | 20000 字符 |
| 名称 / 别名 | 200 字符 / 64 项 |
| id | 96 字符，`^[a-z0-9][a-z0-9_.:-]*$` |
| 标签 | 64 字符 / 64 项，小写 snake_case（可含 `:` `.` `-`） |
| source_ids / 关联 | 64 / 64 |
| details 分节数 | 32 |
| 检索分页 | `limit` 1..200，`offset ≥ 0` |

其他拒绝原因：`NaN`/`Infinity`（解析与入库两处都拦）、同文档内重复 id、缺/空七节、七节不是字符串、悬空来源、无法识别的 schema、schema_version 不是 1、把非本模块建的库当目标。

参数一律走 SQL 占位符，不做字符串拼接。

---

## 7. CLI 用法

必须给 `--db`，没有默认库位置。

```powershell
# 导入（整批原子；可一次给多个文件）
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_cli import --db temp.sqlite3 `
  docs/human-encyclopedia/staples.json docs/element-catalog/eastern.json

# 只建空库，不导数据
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_cli init --db temp.sqlite3

# 中文名/别名检索 + 标签 OR/AND + 分页
... search --db temp.sqlite3 --text 小麦 --tag cereal --all-tag crop --limit 10 --offset 0

# 单项详情（可看历史版本），--json 输出结构化结果
... get --db temp.sqlite3 staples_wheat
... get --db temp.sqlite3 staples_wheat --version 1 --no-payload

# 版本列表、标签、统计
... versions --db temp.sqlite3 eastern_cultivator_strata
... tags --db temp.sqlite3
... stats --db temp.sqlite3 --json

# 导出（全部版本）与再导入
... export --db temp.sqlite3 --out dump.json
... export --db temp.sqlite3 --out only-beta.json --namespace beta
... restore --db copy.sqlite3 dump.json
```

| 子命令 | 会写库 | 说明 |
|---|---|---|
| `init` | 是（建 schema） | 只建空库 |
| `import` | 是 | 整批原子导入 |
| `restore` | 是 | 把导出文件写回（保留原版本号） |
| `search` / `get` / `versions` / `tags` / `stats` / `export` | **否** | 以 `mode=ro` 只读打开，且不执行建表；库不存在就报错，不会顺手建一个空库 |

`get` 的文本输出会把每个来源写成 `source_id v版本 (命名空间, status) 标题 | access`；若该资料条目版本 pin 的不是来源当前版本，会在行末标注「来源已有更新版本，但此证据版本固定不变」。

退出码：`0` 成功；`1` 领域错误（校验失败、找不到、冲突、超限）；`2` 参数用法错误（argparse）。

### 7.1 构库开关（`tools.encyclopedia_build`）

不带任何开关时仍是**历史 14 组 / 528 条 / 502 来源**；其余分区全部是显式开关、默认不入库：

```powershell
# 只加成奇幻生物（种族 / 西幻动植物 / 东方玄幻动植物）
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --with-fantasy-biology

# 叠加：特质 + 饮食 + 属性 + 文化 + 奇幻生物（顺序固定）
... -m tools.encyclopedia_build --with-traits --with-cuisine --with-attributes --with-culture --with-fantasy-biology

# 先核对不带这些分区的旧库（不改库、不改源 JSON）
... -m tools.encyclopedia_build --check
```

| 开关 | 名单常量 | 文件 |
|---|---|---|
| （无） | `GROUPS` | 历史 14 组 |
| `--with-traits` | `TRAIT_GROUPS` | `docs/playable-demo/character-traits.json` |
| `--with-cuisine` | `CUISINE_GROUPS` | `docs/human-encyclopedia/cuisine.json` |
| `--with-attributes` | `ATTRIBUTE_GROUPS` | `docs/playable-demo/character-attributes.json` |
| `--with-culture` | `CULTURE_GROUPS` | 叙事传统 + 亚洲/欧洲姓名池（3 份） |
| `--with-fantasy-biology` | `FANTASY_BIOLOGY_GROUPS` | `fantasy-races.json` / `western-biology.json` / `eastern-biology.json` |
| `--with-alchemy` | `FANTASY_ALCHEMY_GROUPS` | `western-alchemy.json` / `eastern-alchemy.json` |

追加顺序固定为「14 组 → 特质 → 饮食 → 属性 → 文化 → 奇幻生物 → 魔药」，同一文件不会被重复构入。
`--with-fantasy-biology` 与 `--with-alchemy` **互不隐含**：只要生物不自动带药，反之亦然。
所有名单都**逐文件写死、不用通配**；`shared-themes.json`（聚类索引）始终不进名单。
这两个开关**不改动引擎、世界包与 API**，也不自动导入运行期；库里的新组仍是待审候选。
魔药分区是游戏与小说素材，**不是任何现实用药依据**，也不含配方与剂量。

奇幻生物分区用**标签**做检索入口，而不是给引擎加分类逻辑：

```powershell
# 种族（kind:race）、兽类（kind:fauna）、草木类（kind:flora）
... search --db temp.sqlite3 --all-tag kind:race --limit 20
# 按题材/传统维度（tradition:eastern / tradition:western）
... search --db temp.sqlite3 --all-tag tradition:western --limit 20
# 魔药与方剂统一是物品（kind:item），药效与代价是检索维度
... search --db temp.sqlite3 --all-tag kind:item --limit 30
... search --db temp.sqlite3 --all-tag role:legend_tier --limit 20
```

### 7.2 重合归并（`tools.encyclopedia_merge`）

新分区里与**已有资料条目重名或同别名**的条目（例：西方草药里的“鼠尾草”与已有香料条目、法餐菜品与已有食材），不要新建重复资料条目，而是并到原资料条目上：

```powershell
# 先干跑看计划（默认不写任何文件）
... -m tools.encyclopedia_merge --candidate docs/element-catalog/reality-herbs-western.json
# 确认无误再写：追加【补充条目】块、并检索标签、记 merged_from
... -m tools.encyclopedia_merge --candidate docs/element-catalog/reality-herbs-western.json --apply
```

规则：

- 名字比较忽略括号限定语与空白（「胡椒（黑胡椒）」≡「胡椒」），命中后追加到 `--section` 指定的详情分节（默认 `story_uses`），形成一次**新版本**，原分节不清空。
- 只并 `part:` / `trait:` / `role:` / `trade:` / `effect:` / `habitat:` / `origin:` / `taxon:` / `source_text:` 这些检索前缀；`kind:` 与 `tradition:` **不并**（一个资料条目只取一个传统），`genre:` / `category:` 由导入器派生。
- 旧 schema 的资料条目（没有 `tags` 键）**不会**被添上 `tags`，因为引擎会丢弃这类原生标签；内容仍会并进 `details`。
- `merged_from` 记录「分区/元素 id」，便于追溯哪条补充来自哪个采集分区。
- 未命中的条目不处理，它们该留在自己的新分区里。

新组的条数随采集侧定稿变化，**本文不写固定数字**；要当前值就跑
`--with-fantasy-biology --with-alchemy --check`。注意：`--check` 只核对**已存在**的库与名单是否一致，
不会替你把新组导进旧库——旧库要包含这些组，得重新构库或显式 `import` 对应 JSON。

---

## 8. 导出文件格式

```json
{
  "format": "human-encyclopedia-export",
  "export_version": 2,
  "schema_version": 2,
  "exported_at": "…",
  "scope": {"namespaces": "all"},
  "counts": {"groups": 14, "source_versions": 502, "element_versions": 528},
  "groups":   [{"namespace", "group_id", "schema_kind", "adapter", "legacy_schema", "status", "meta"}],
  "sources":  [{"namespace", "source_id", "version", "payload_hash", "payload"}],
  "elements": [{"namespace", "element_id", "version", "content_hash", "payload",
                "tags", "names", "details", "details_map", "details_extra",
                "source_refs", "relations"}]
}
```

- 导出**含全部历史版本**，按 `(namespace, id, version)` 稳定排序 → 同一库的两次导出可逐字节比较。
- 还原时校验 `content_hash` 与 `payload` 是否一致：被手改过的导出文件会被拒绝（`Conflict`），不静默接受。
- 单命名空间导出时，只含该组的来源；组内资料条目引用同一命名空间外的来源会被拒绝（导出本身是自洽的，不会造出悬空引用）。
- `relations` 在导出里带 `status`，但这个状态不算契约：还原后按目标是否已入库重新计算，`pending` 不会因为导出过就变成 `resolved`。
- `source_refs` 每项必有 `source_id` / `source_namespace` / **`source_version`**：导出是证据快照，缺 pin 或 pin 指向文件外的来源版本都整份拒绝（`InvalidDocument`）。`relations` 里的 `status` 则不是契约。
- 整个导出文件是一个重建单元：**所有命名空间共用一个事务**，任何一个组非法（引用了不存在的来源等）都整份拒绝，不会只还原前几组。

---

## 9. 已知限制（如实）

1. **仅词法检索**：中文名称与别名是 `LIKE '%子串%'` 匹配（NFKC + casefold 归一化后比较）。没有分词、没有近义、没有拼音。FTS5 在本机可用，但当前实现没用它——274 条规模下基础 SQL 足够，避免额外虚表与触发器带来的一致性风险。
2. **不做兼容性判定**：标签只用于检索，不构成「这个资料条目能进那个世界」的证明；依赖/排除条件仍是自然语言，引擎不读。
3. **不做事实核验**：库只记录 `access` / `review_status` / `detail_status` 原值，不评判内容真假。
4. **不做版本分支**：`current_version` 单调前移，没有「回退到旧版本作为当前」的操作（历史永远可读）。
5. **构库遇到半份文件会明确报错，不静默跳过**：`tools.encyclopedia_build` 在源 JSON 缺失、JSON 不可解析或校验失败时直接退 1，并在 stderr 点名缺哪份文件（`缺少采集 JSON，未建库` / `拒绝：…`），**不会**跳过后继续建一份“看起来成功”的库。
   - 已进入正式交付的三份奇幻生物分区文件（§12）还更进一步：缺文件 / 坏 JSON / 空 `elements`还会使测试**失败**（`ContentNotDeliverable`），不再是“准备中跳过”。
   - 其他仍在采集中的候选分区（例如还在增补的饮食）仍不把条数写死：条数从源文件现算，本说明不给固定数字。
6. 资料条目归属改不了命名空间：同一 namespace 一旦按某个 adapter/group 建过，就不能改挂到别处（`Conflict`）。
7. **不支持 schema 1 升级**：旧库没记录 pin，无法反推历史证据（见 §2）。只能重建库并重新导入采集 JSON。

---

## 10. 本环节的验证范围

`D:\anaconda\python.exe -X utf8 -m unittest tests.test_encyclopedia` —— 81 个测试，全部通过（exit 0）。

覆盖：schema 版本与建库、原字段无损、版本不可变与历史可读、同 payload 幂等（资料条目级与批次级）、内容变更新增版本、中文名称/别名检索、多标签 AND/OR/组合、分页边界与 limit 上限、单项详情与指定版本、命名空间隔离与同 ID 共存、来源跨组解析、半批零写入（9 类拒绝）、NaN 拒绝、上限拒绝、未解析关联 pending → 后续批次 resolved、导出再导入逐字段往返、多命名空间恢复全有或全无、导出哈希篡改拒绝、只读连接不建库、外部库拒绝、CLI 全部子命令与退出码、原六组 274 条完整导入与逐条 payload 比对、274 条状态不升格、原 JSON 文件哈希不变、与游戏 runtime/data 隔离。

其与证据固定相关的回归（`SourcePinTests`，10 个）：资料条目 v1 引来源 v1 → 来源升 v2 后 `get(version=1)` 仍 v1（url/access/title/payload 都不变）、`is_current_source_version=false`、资料条目不新增版本且不重写历史关联；只改来源时 `element_versions_written=0`；需要新证据必须新资料条目版本且新版本可 pin 新来源；pin 导出/还原不丢；同 `source_id` 跨命名空间不串；pin 指向不存在/文件外版本、缺 `source_refs`、`export_version=1` 均整份拒绝且零写入；schema 1 库明确拒绝不隐式升级；全库不变量「每条 `element_sources` 都能 join 到真实来源版本」。

临时库实测（本环节最后一次全量跑，位于系统临时目录，已删）：

| 组 | adapter | 资料条目 | 来源 |
|---|---|---|---|
| animal-foods / flavors / materials / produce / staples / tools | human-encyclopedia | 28 / 33 / 36 / 37 / 33 / 40（共 207） | 32 / 37 / 24 / 49 / 39 / 38 |
| eastern / western / society / steam-horror / reality-physical / reality-human | element-catalog | 54 / 54 / 53 / 50 / 32 / 31（共 274） | 17 / 34 / 31 / 46 / 36 / 55 |
| **合计** | | **481** | **438** |

- 481 条全部 `needs_review` + `needs_detail`，`reviewed_detail` = 0。
- **证据版本固定实测**：`staples_wheat` 的 v1 引用 4 个来源（均为 v1）；把 `staples_src_brit_durum` 的 URL 改成新地址升到 v2 后，资料条目仍 `element_versions_written=0`，`get(version=1)` 仍返回 v1 的 `https://www.britannica.com/plant/durum-wheat`，`is_current_source_version=false`；重新导出要带 `export_version=2`。
- `element_sources` 共 1280 行，孤岛 0、`source_version` 为 NULL 0（全库 pin 完整）。
- 481 条导出→还原→再导出，`groups` / `sources` / `elements` 三部分逐字段相等。
- 12 组合计库大小约 5.5 MiB，导入 + 导出 + 还原 + 比对约 2 秒。
- 跨组关联（`related_catalog_ids`，如 `reality_physical_* → steam_*`）在目标组导入后全部 `resolved`，未解析 0。

**没有做的事**：没有生成正式 `artifacts/human-encyclopedia/encyclopedia.sqlite3`；没有对任何条目做事实核验；没有把百科接进故事 prompt、旧存档或经营模拟。

以上为 **12 组 481 条** 阶段（已随 commit `1398466` 发布）的实测记录，保持原样不改写。

---

## 11. 本轮：名单扩到 14 组（+47 条）

### 11.1 变了什么、没变什么

| | 旧（已发布） | 本轮 |
|---|---|---|
| 构库名单 | 显式 12 组 | 显式 **14 组**（新增 food-supplement / craft-supplement） |
| 资料条目 / 来源 | 481 / 438 | **528 / 502** |
| 库 schema / 导出格式 | schema 2 / export 2 | 不变（仍是 2 / 2） |
| 旧 12 组的行 | — | **零改动**（同库追加新 namespace，旧组导出逐字段相等） |
| `review_status` | 全部 `needs_review` | 不变，新条目也都是 `needs_review` |

变更点只在 `tools/encyclopedia_build.py` 的 `GROUPS` 常量与相应措辞：两个增补组**逐组显式登记**，不引入 `docs/human-encyclopedia/*.json` 通配——同目录以后还会有别的候选文件，通配会把它们默默带进交付库；`shared-themes.json` 仍在 `EXCLUDED` 里，没有进名单。`app/encyclopedia.py` 内部未改动（不需要改：增补组走的就是已有的人类七节 schema 与 `source_ids` / `related_ids` 解析路径）。

### 11.2 两个增补组（本轮冻结值）

| 组 | 资料条目 | 来源 | 来源 access 构成 | 跨组关联 |
|---|---|---|---|---|
| food-supplement | 23 | 30 | `read` 30 条（其中 1 条为策展摘要/索引页，已在组内说明） | 65 个目标指向 staples / produce / flavors / animal-foods / materials / tools |
| craft-supplement | 24 | 34 | `read` 31 + `search_only` 3（awl / antler / bone-carving 只取到摘要与引文片段） | 19 个目标指向六组 |
| **合计** | **47** | **64** | | 与六组合并后未解析关联 0 |

两组的候选状态、七节齐全、id 前缀（`food_supp_` / `craft_supp_`）、无 id 与来源冲突、`search_only` 的诚实标注，均在本轮测试中逐条断言。**这不等于事实已核实。**

### 11.3 与已发布旧库的兼容

同库追加新 namespace 是受支持的路径，不需要重建：

1. 旧 12 组的库（12 组 / 481）可以直接导入两个增补组，得到 14 组 / 528；
2. 旧 12 组的 `groups` / `sources` / `elements` 导出在追加前后**逐字段相等**（三部分都断言）；
3. 旧组条目仍可读、仍是 `needs_review` + `needs_detail`、仍各自只有 1 个版本（没有重写历史）；
4. 全量导出仍可用 `export_version=2` 还原到空库，计数不再是硬编码的 12/438/481。

反过来：**旧的已生成库文件不会自动长出新组**，需要重新导入两个增补文件（或整体重建）才会包含它们；已导出的旧 dump 也不会凭空多出这两组。

### 11.4 本环节的测试

| 范围 | 命令 | 结果 |
|---|---|---|
| 库与 CLI 本体（旧基线） | `python -X utf8 -m unittest tests.test_encyclopedia` | 81 个用例 |
| 14 组名单扩展与两个增补组集成（新增） | `python -X utf8 -m unittest tests.test_encyclopedia_supplement` | 30 个用例，exit 0 |
| 特质分区（新增） | `python -X utf8 -m unittest tests.test_encyclopedia_traits` | 断言 15 组 / 551 / 505（那一轮口径） |
| 饮食分区（新增） | `python -X utf8 -m unittest tests.test_encyclopedia_cuisine` | 14 个用例，exit 0；数量断言从源文件动态算 |
| 库 + 装配相关四模块一起跑 | `unittest tests.test_encyclopedia tests.test_element_assembly tests.test_element_assembly_integration` | **161 个用例，全部通过（OK），exit 0**，288.6s |

四模块合计 191 个用例（81 + 41 + 39 + 30）。四模块那次实测里包含旧 81 项与 80 项装配相关回归（其中出现一条 starlette 关于 `httpx` → `httpx2` 的弃用警告，与本事无关）。

`tests/test_encyclopedia.py` 里的 **12 组 / 481 / 274 基线断言全部保留未改**——它们验的是旧库行为，机械改成 528 反而会弱化回归。扩展后的数字只在 `tests/test_encyclopedia_supplement.py` 里断言（14 组 / 528 / 502）。

新增测试覆盖：名单是显式 14 项且不允许通配、两个增补组按名登记、`shared-themes.json` 仍被排除、`build()` + `--check` 跑出 14 组 528 条、`--check` 缺组时退 1、增补组整批导入与 payload 逐字节回读、状态不升格、`access` 原值入库、跨组 `related_ids` 先 pending 后 resolved（目标组缺失时不假称解析）、多标签 AND/OR/复合与命名空间限定、重复导入零新版本且库文件哈希不变、`element_sources` 全 pin 且可 join、导出/还原保留（含单组导出后关联仍 pending）、旧库追加后旧行不变、扩展库导出可还原到空库。

### 11.5 临时库实测（本轮，位于系统临时目录，已删）

| 组 | adapter | 资料条目 | 来源 |
|---|---|---|---|
| staples / produce / flavors / animal-foods / materials / tools | human-encyclopedia | 33 / 37 / 33 / 28 / 36 / 40（共 207） | 39 / 49 / 37 / 32 / 24 / 38（共 219） |
| food-supplement / craft-supplement | human-encyclopedia | 23 / 24（共 47） | 30 / 34（共 64） |
| eastern / western / society / steam-horror / reality-physical / reality-human | element-catalog | 54 / 54 / 53 / 50 / 32 / 31（共 274） | 17 / 34 / 31 / 46 / 36 / 55（共 219） |
| **合计** | | **528** | **502** |

- `build()` 与 `--check` 均 exit 0，逐组“库内 == 源”一致，未解析关联 0。
- 528 条全部 `needs_review` + `needs_detail`，`reviewed_detail` = 0。
- 旧 12 组库追加两组后，旧组三段导出逐字段相等；全库计数变为 14 / 528 / 502。

**本环节没有做的**：没有生成或覆写 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（留给主代理验收后显式导入）；没有改写两个增补源 JSON（它们由采集侧定稿）；没有动 `app/encyclopedia.py` 内部、`data/`、`StoryPackage/` 或游戏 runtime；没有做 git 提交。

附：本环节末尾以**只读**方式核对当时已存在的 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（由主代理生成，本环节未写入），得到 14 组 / 528 资料条目版本 / 502 来源版本 / 未解析关联 0，命名空间含 `food-supplement` 与 `craft-supplement`；`food_supp_water_chestnut` 的标签已为 `aquatic_food`（旧 `root_tuber` 已移除），增补条目仍均 `needs_review` + `needs_detail`，craft 条目来源 pin 为 v1 且关联全 `resolved`。库内容的验收与交付决定权在主编。

---

## 12. 本轮：奇幻生物分区（种族 / 西幻动植物 / 东方玄幻动植物）

本节只记**构库侧接入**这一层。三份内容文件由采集侧定稿，本环节**不写、不改**它们，也不写正式数据库。

### 12.1 改动点（只有两处代码 + 两处文档）

| 文件 | 改动 |
|---|---|
| `tools/encyclopedia_build.py` | 新增 `FANTASY_BIOLOGY_GROUPS`（三份逐文件显式登记）；`groups_for` 末尾新增 `with_fantasy_biology=False`；新增 `--with-fantasy-biology`；docstring / description 同步 |
| `tests/test_encyclopedia_fantasy_biology.py` | 新增（名单/flag 兼容、三组导入、`kind:*` / `tradition:*` 检索、来源 pin、幂等、状态不升格、`--check`） |
| `docs/human-encyclopedia/database-使用说明.md` | §7.1 构库开关表 + 本节 |

**没有改**：`app/encyclopedia.py`（引擎不需要改——“三组”走的就是现有新七节 schema 与 `source_ids` 解析路径）、世界包、API、`data/`、`StoryPackage/`、游戏 runtime；没有安装依赖、没有启动服务、没有碰 Terragenesis；没有动文化/姓名/特质/饮食/属性各分区已有的数据与来源问题。

### 12.2 向后兼容的硬约束（已逐条断言）

- 不给开关 = 历史 14 组 / 528 / 502，一字节不变。
- `groups_for(True, True, True)`、`groups_for(with_culture=True)` 等**旧的位置传参**含义不变（新参数在末尾且默认 `False`）。
- 追加顺序固定：`14 组 → 特质 → 饮食 → 属性 → 文化 → 种族 → 西幻生物 → 东方生物`，同一文件不重复构入。
- 三份文件既不在 `GROUPS`，也不在任何其他名单里，更不在 `EXCLUDED`（它们是资料条目文档，不是聚类索引）。
- 名单逐文件写死、不使用通配。

### 12.3 检索入口：靠标签，不靠引擎分类

新组用条目自带的标签检索，引擎不读标签做判定：

| 标签 | 含义 |
|---|---|
| `kind:race` | 种族（种族组每条都是它） |
| `kind:fauna` | 兽/动物（两份生物组）|
| `kind:flora` | 草木/植物（两份生物组）|
| `kind:<其它>` | 允许的扩展分类（如 `kind:spirit`）；必须是合法小写 token |
| `tradition:eastern` / `tradition:western` | 题材/传统维度 |

`search --all-tag kind:race`、`search --all-tag tradition:western` 均可直接使用；命名空间限定（`--namespace fantasy-races` 等）照旧。

**`kind` 不是封闭枚举**：库只把它当检索标签，不参与“资料条目能不能进某个世界”的判定。
所以内容侧把某条从 `kind:fauna` 改成 `kind:spirit`（如东方山精）**不需要改代码或引擎**，
只影响该条计入 fauna / flora 的计数；测试因此不写死 kind 的完整取值集，而是要求：
每条恰有一个格式合法的 `kind:*`、种族组全为 `kind:race`、两份生物组的 `fauna` 与
`flora` 各不少于 8 条。

### 12.4 内容可交付的最低约束（正式交付口径）

**缺文件、JSON 坏成半份、`elements` 为空、没有任何 `sources`，一律测试失败**——
不再有“准备中就 skip”的模式。理由：库要能建、名单要能核对，内容没齐就是没齐。
读取阶段先抛 `ContentNotDeliverable`（`AssertionError` 子类），把具体哪份文件、
哪个位置坏了直接报出来。

三份内容文件还需要同时满足：

| 约束 | 口径 |
|---|---|
| kind 分类 | 每条恰 1 个 `kind:*` 且格式合法；种族组全为 `kind:race` |
| 生物覆盖 | 西幻、东方两份生物组的 `kind:fauna` / `kind:flora` **各 ≥ 8** |
| tradition | 种族组按条目分 `tradition:eastern` / `tradition:western`（两者都要有），两份生物组各自单传统 |
| 七节正文 | 七个分节都存在且**非空**（`legacy_schema` 用旧七节口径） |
| 来源引用 | 被引用的来源必须真实存在于本文档；且必须 `access: read` |
| 无来源条目 | 允许（纯原创新生态/类型模板），但 `source_ids` 为空时 `evidence_and_uncertainty` 必须写明“来源：无”，且库里不得凭空多出来源行 |
| 审查状态 | 全部 `needs_review` + `needs_detail`；导入不升格 |

> `access: read` 只表示采集侧**声称读过正文**，**不等于事实已核验**。测试能验的是：引用不悬空、
> 来源版本 pin 可追溯、`access` 如实入库、状态未被提升。事实核验仍是后续人工审阅的事。

### 12.5 本环节的测试范围

| 范围 | 命令 |
|---|---|
| 新增奇幻生物测试 | `python -X utf8 -m unittest tests.test_encyclopedia_fantasy_biology` |
| 库与 CLI 本体 + 14 组增补（基线回归） | `python -X utf8 -m unittest tests.test_encyclopedia tests.test_encyclopedia_supplement` |
| 特质/饮食/文化/属性（基线回归） | `python -X utf8 -m unittest tests.test_encyclopedia_traits tests.test_encyclopedia_cuisine tests.test_culture_catalog tests.test_encyclopedia_attributes` |

新增测试分四组：

1. **名单与兼容**（不依赖内容）：显式三文件、非通配、不被旧开关带入、默认 14 组与旧位置传参等价、叠加顺序、flag 解析。
2. **交付守卫**：缺文件 / 坏 JSON / 空 `elements` / 无 `sources` 必须失败（用临时副本验守卫本身，不动真文件）。
3. **内容与库**：三组真导入、kind/tradition 约束、七节非空、来源 `access=read` 与 pin 完整、复导幂等、`--check` 遇缺组退 1。
4. **合成自检**：用临时合成文档跑「三组 → 导入 → 标签检索 → 命名空间隔离 → 幂等 → 状态不升格」，把“接入代码坏了”与“内容变了”分开。

> 本轮**不写最终测试数字**（条数与用例数会随内容修订变动）：具体运行结果由主代理跑后回填。

### 12.6 交付库怎么办

本文**不写三组的固定条数**（内容仍可能微调）。要导进正式库，主代理显式跑：

```powershell
# 只加成奇幻生物
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --with-fantasy-biology
# 或与已有分区叠加
... --with-traits --with-cuisine --with-attributes --with-culture --with-fantasy-biology
# 核对
... --with-fantasy-biology --check
```

注意：`--check` 只核对**已存在**的库与名单是否一致，不会把新组补进旧库；旧库要包含这三组得重新构库或显式 `import` 三份 JSON。本环节**没有**生成或覆写 `artifacts/human-encyclopedia/encyclopedia.sqlite3`。
