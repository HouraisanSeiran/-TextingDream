# 人类百科素材库 · 数据库与 CLI 使用说明

状态：**候选素材数据库已生成并通过技术验收。** 交付文件为 `artifacts/human-encyclopedia/encyclopedia.sqlite3`（schema 2 / export 2，12 组、481 条元素、438 条来源记录）。主代理独立完整回归341项：338通过、3项符号链接权限跳过，退出码0；数据库完整性、来源版本固定、幂等导入与导出恢复已验证。内容仍为待审候选，不代表全部事实已经核实；不自动接入故事或旅程。

- 代码：`app/encyclopedia.py`（库与导入/查询实现）、`tools/encyclopedia_cli.py`（CLI）
- 测试：`tests/test_encyclopedia.py`
- 数据来源：`docs/human-encyclopedia/*.json`（新七节 schema）、`docs/element-catalog/*.json`（原六组 274 元素）。**本模块只读它们，从不改写。**

---

## 1. 边界（先说清楚它不是什么）

| 是 | 不是 |
|---|---|
| 独立的本地 SQLite 素材库，路径由 `--db` 显式指定 | 不是旅程数据库 `data/textiledream.sqlite3`，两者零关联 |
| 候选资料 + 来源 + 多标签 + 审查状态的存放处 | 不是故事正典：库里有 ≠ 世界里有，更 ≠ 人物知道 |
| 只读查询工具（search / get / versions / tags / stats / export） | 不参与 app 启动、不自动填库、不进故事 prompt、不碰旧存档 |
| 显式 CLI 导入 | 不提供运行时从全局库取元素的入口；开局绑定仍是后续独立设计 |
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
2. **元素级幂等**：同一 `(namespace, element_id)` 下同哈希已存在 → **不新增版本、不重写行**。内容只要变一个字节 → `version+1`，旧版本永久可读（`get --version N`）。
3. **批次级幂等**：`batch_hash = sha256(namespace + adapter + 整份文档)`。重复导入同一文件直接返回 `idempotent=True`，零写入。只改文档级字段（如 `updated`）也算新批次，但元素同哈希仍不新增版本。
4. **不可变**：`element_versions` / `source_versions` 只插入。恢复导出时若同一版本号已存在且内容不同 → `Conflict`，拒绝覆盖历史。
5. **来源版本**：来源同样带版本。同名来源内容变了 → 新版本，元素按 `source_namespace` 指回真实来源，不会串组。

### 3.5 证据版本固定（pin）

元素版本写入时，把「当时看到的那一版来源」写进 `element_sources.source_version`：

| 场景 | 行为 |
|---|---|
| 元素 v1 引用来源 v1，之后来源升到 v2 | 元素 v1 **仍读 v1** 的 title/url/access/payload；`is_current_source_version=false` 只作提示 |
| 只改来源、元素 payload 不变 | 不新增元素版本（`element_versions_written=0`），**不重写历史关联**，也不静默把证据换成 v2 |
| 需要新证据 | 必须**显式写一个新元素版本**（内容变了 → 新 `content_hash` → 新 version），新版本 pin 当时的来源版本 |
| 同批导入 | 按来源内容哈希精确定位刚写入的版本号，不拿 `current_version` 猜 |
| 导出/还原 | `source_refs` 必带 `source_version`；还原时校验 pin 指向导出文件里真实存在的来源版本，缺失或越界**整份拒绝** |

`get(element, version=N)` 与 CLI `get --version N` 返回的就是该版本的固定证据，不受之后任何来源更新影响。

---

## 4. 来源、关联与状态

### 来源解析（否则整批拒绝）
元素 `source_ids` 按顺序解析：**同批 → 本命名空间 → 全局唯一**。找不到 → 拒绝；多个命名空间都有同名来源 → 拒绝（歧义）。

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
| 识别 | 元素都带 `tags` | 元素都带 `category` |
| 七节 | `definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty` | `… / story_consequences / adaptation_limits / evidence_and_uncertainty` |
| 映射 | 同名直通 | **显式 adapter**，映射记在 `details_map`：`story_uses ← story_consequences`、`historical_scope ← adaptation_limits` |
| 标签 | 保留原 `tags`，另加 | `category:X`、`genre:Y` 命名空间化标签 |

要点：

- `adaptation_limits → historical_scope` 只是**七节命名对齐的语义近似**：原字段讲的是「跨题材改编边界」，不是现实史实。原字段名和原文都留在 `payload.details` 里，`details_map` 会明确标出来（`get` 的文本输出也会打印「原字段 …」）。
- 其他分节（如 `western` 的 `parameter_dimensions`，是对象而非字符串）原样进 `details_extra`，**不强制统一类型、不丢弃**。
- `variants / story_roles / requires / excludes / background / entry_modes / introduction_limits / evidence_note / genre_relevance / related_catalog_ids` 等全部保留在 payload 中，`get` 可直接读回。
- `shared-themes.json` 是聚类索引，**不是元素**；导入会被明确拒绝（`InvalidDocument`）。

---

## 6. 上限与拒绝（半批零写入）

单批次先在内存里全量校验，再在**一个 `BEGIN IMMEDIATE` 事务**里写入；任何异常 → `ROLLBACK`，库里一行都不留。

| 上限 | 值 |
|---|---|
| 单份 JSON 文本 | 32 MiB |
| 单批元素 / 来源 | 5000 / 5000 |
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

`get` 的文本输出会把每个来源写成 `source_id v版本 (命名空间, status) 标题 | access`；若该元素版本 pin 的不是来源当前版本，会在行末标注「来源已有更新版本，但此证据版本固定不变」。

退出码：`0` 成功；`1` 领域错误（校验失败、找不到、冲突、超限）；`2` 参数用法错误（argparse）。

---

## 8. 导出文件格式

```json
{
  "format": "human-encyclopedia-export",
  "export_version": 2,
  "schema_version": 2,
  "exported_at": "…",
  "scope": {"namespaces": "all"},
  "counts": {"groups": 12, "source_versions": 438, "element_versions": 481},
  "groups":   [{"namespace", "group_id", "schema_kind", "adapter", "legacy_schema", "status", "meta"}],
  "sources":  [{"namespace", "source_id", "version", "payload_hash", "payload"}],
  "elements": [{"namespace", "element_id", "version", "content_hash", "payload",
                "tags", "names", "details", "details_map", "details_extra",
                "source_refs", "relations"}]
}
```

- 导出**含全部历史版本**，按 `(namespace, id, version)` 稳定排序 → 同一库的两次导出可逐字节比较。
- 还原时校验 `content_hash` 与 `payload` 是否一致：被手改过的导出文件会被拒绝（`Conflict`），不静默接受。
- 单命名空间导出时，只含该组的来源；组内元素引用同一命名空间外的来源会被拒绝（导出本身是自洽的，不会造出悬空引用）。
- `relations` 在导出里带 `status`，但这个状态不算契约：还原后按目标是否已入库重新计算，`pending` 不会因为导出过就变成 `resolved`。
- `source_refs` 每项必有 `source_id` / `source_namespace` / **`source_version`**：导出是证据快照，缺 pin 或 pin 指向文件外的来源版本都整份拒绝（`InvalidDocument`）。`relations` 里的 `status` 则不是契约。
- 整个导出文件是一个重建单元：**所有命名空间共用一个事务**，任何一个组非法（引用了不存在的来源等）都整份拒绝，不会只还原前几组。

---

## 9. 已知限制（如实）

1. **仅词法检索**：中文名称与别名是 `LIKE '%子串%'` 匹配（NFKC + casefold 归一化后比较）。没有分词、没有近义、没有拼音。FTS5 在本机可用，但当前实现没用它——274 条规模下基础 SQL 足够，避免额外虚表与触发器带来的一致性风险。
2. **不做兼容性判定**：标签只用于检索，不构成「这个元素能进那个世界」的证明；依赖/排除条件仍是自然语言，引擎不读。
3. **不做事实核验**：库只记录 `access` / `review_status` / `detail_status` 原值，不评判内容真假。
4. **不做版本分支**：`current_version` 单调前移，没有「回退到旧版本作为当前」的操作（历史永远可读）。
5. **未导入的组**：采集侧仍在交付，`docs/human-encyclopedia/*.json` 里正在被写入的半份文件（JSON 尚不可解析）会被跳过；测试对这种文件自动 `skip` 而不是失败，也不把条数写死。正式批量导入待所有组交付后进行。
6. 元素归属改不了命名空间：同一 namespace 一旦按某个 adapter/group 建过，就不能改挂到别处（`Conflict`）。
7. **不支持 schema 1 升级**：旧库没记录 pin，无法反推历史证据（见 §2）。只能重建库并重新导入采集 JSON。

---

## 10. 本环节的验证范围

`D:\anaconda\python.exe -X utf8 -m unittest tests.test_encyclopedia` —— 81 个测试，全部通过（exit 0）。

覆盖：schema 版本与建库、原字段无损、版本不可变与历史可读、同 payload 幂等（元素级与批次级）、内容变更新增版本、中文名称/别名检索、多标签 AND/OR/组合、分页边界与 limit 上限、单项详情与指定版本、命名空间隔离与同 ID 共存、来源跨组解析、半批零写入（9 类拒绝）、NaN 拒绝、上限拒绝、未解析关联 pending → 后续批次 resolved、导出再导入逐字段往返、多命名空间恢复全有或全无、导出哈希篡改拒绝、只读连接不建库、外部库拒绝、CLI 全部子命令与退出码、原六组 274 条完整导入与逐条 payload 比对、274 条状态不升格、原 JSON 文件哈希不变、与游戏 runtime/data 隔离。

其与证据固定相关的回归（`SourcePinTests`，10 个）：元素 v1 引来源 v1 → 来源升 v2 后 `get(version=1)` 仍 v1（url/access/title/payload 都不变）、`is_current_source_version=false`、元素不新增版本且不重写历史关联；只改来源时 `element_versions_written=0`；需要新证据必须新元素版本且新版本可 pin 新来源；pin 导出/还原不丢；同 `source_id` 跨命名空间不串；pin 指向不存在/文件外版本、缺 `source_refs`、`export_version=1` 均整份拒绝且零写入；schema 1 库明确拒绝不隐式升级；全库不变量「每条 `element_sources` 都能 join 到真实来源版本」。

临时库实测（本环节最后一次全量跑，位于系统临时目录，已删）：

| 组 | adapter | 元素 | 来源 |
|---|---|---|---|
| animal-foods / flavors / materials / produce / staples / tools | human-encyclopedia | 28 / 33 / 36 / 37 / 33 / 40（共 207） | 32 / 37 / 24 / 49 / 39 / 38 |
| eastern / western / society / steam-horror / reality-physical / reality-human | element-catalog | 54 / 54 / 53 / 50 / 32 / 31（共 274） | 17 / 34 / 31 / 46 / 36 / 55 |
| **合计** | | **481** | **438** |

- 481 条全部 `needs_review` + `needs_detail`，`reviewed_detail` = 0。
- **证据版本固定实测**：`staples_wheat` 的 v1 引用 4 个来源（均为 v1）；把 `staples_src_brit_durum` 的 URL 改成新地址升到 v2 后，元素仍 `element_versions_written=0`，`get(version=1)` 仍返回 v1 的 `https://www.britannica.com/plant/durum-wheat`，`is_current_source_version=false`；重新导出要带 `export_version=2`。
- `element_sources` 共 1280 行，孤岛 0、`source_version` 为 NULL 0（全库 pin 完整）。
- 481 条导出→还原→再导出，`groups` / `sources` / `elements` 三部分逐字段相等。
- 12 组合计库大小约 5.5 MiB，导入 + 导出 + 还原 + 比对约 2 秒。
- 跨组关联（`related_catalog_ids`，如 `reality_physical_* → steam_*`）在目标组导入后全部 `resolved`，未解析 0。

**没有做的事**：没有生成正式 `artifacts/human-encyclopedia/encyclopedia.sqlite3`；没有对任何条目做事实核验；没有把百科接进故事 prompt、旧存档或经营模拟。
