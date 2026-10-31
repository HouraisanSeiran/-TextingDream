# 人类生产生活百科 · 总索引

本轮文化扩充：`--with-culture` 追加 3 个显式分区、33 条元素和 23 条来源；本地交付库核对为 20 组、614 条元素、577 条来源。默认构库仍保持历史 14 组口径。

状态：**候选素材库**。角色特质与美食这一批的基线为 **16 组、575 条元素、552 条来源记录**。最新只读核对时，库内另有 `character-attributes` 分区（6 条元素、2 条来源），合计 **17 组、581 条元素、554 条来源记录**，未解析关联为 0。本次仅同步美食勘误：24 条美食中 8 条产生新版本，历史版本保留，其余分区未改。默认历史名单仍为 14 组、528 条元素、502 条来源；新增分区需显式开关，不自动进入故事或旅程。

> 库里有 ≠ 世界里有，更 ≠ 人物知道。所有条目的 `review_status` 均为 `needs_review`，没有任何一条做过逐条事实核验，也没有任何一条被提升为 `reviewed_detail`。本页只做索引导航，正文以 JSON 为准。

## 一、量与构成

| 来源目录 | 组数 | 元素 | 说明 |
|---|---|---|---|
| `docs/human-encyclopedia/`（生活八组） | 8 | **254** | 现实生产生活的具体物产与工艺 |
| `docs/element-catalog/`（题材与现实六组） | 6 | **274** | 机制 / 制度 / 题材母题，外加现实基础两分区 |
| **合计** | **14** | **528** | 构库名单逐组显式登记，不走通配 |

本轮（增补两批）新增 **47 条**：`food-supplement` 23 + `craft-supplement` 24；此前已发布的旧库为 12 组 481 条。

### 1.1 角色特质分区（第 15 组，需显式构入）

`docs/playable-demo/character-traits.json`（**23 条 / 3 条来源**）是一个独立分区，命名空间 `character-traits`，
每条同样是七节 `details` + `tags` + `needs_review`。它**不在默认 14 组里**：

| 构库命令 | 组数 | 元素 | 来源 |
|---|---|---|---|
| `python -m tools.encyclopedia_build` | 14 | 528 | 502 |
| `python -m tools.encyclopedia_build --with-traits` | **15** | **551** | **505** |

两行都是那一轮的实测（同一批源文件，`0` 条未解析关联）。**551 / 505 是“加特质分区”那一轮的基线，不是当前上限**：
之后新增了饮食分区（见 §1.2），本批为 24 条元素、47 条来源记录。

对现有那个库文件直接再跑一次即可（导入是幂等增量，已有元素与 source pin 不会被重写，
**不另建第二个库**）。默认 14 组那一行只是向后兼容的命令，供旧集回归用。
特质分区同样不用通配：文件名写死在 `tools/encyclopedia_build.py` 的 `TRAIT_GROUPS` 里，
避免将来同目录新增的候选文件被默默带进交付库。

### 1.2 饮食／烹饪分区（需显式构入：`--with-cuisine`）

`docs/human-encyclopedia/cuisine.json`（命名空间 `cuisine`）是又一个独立分区，**不在默认 14 组里**，
需要显式开关。它可与特质同时构入：

| 构库命令 | 组数 |
|---|---|
| `python -m tools.encyclopedia_build` | 14（历史基线） |
| `python -m tools.encyclopedia_build --with-traits` | 14 + 特质 |
| `python -m tools.encyclopedia_build --with-cuisine` | 14 + 饮食 |
| `python -m tools.encyclopedia_build --with-traits --with-cuisine` | 14 + 特质 + 饮食 |

### 1.3 文化与姓名分区（需显式构入：`--with-culture`）

| 命名空间 | 元素 | 来源 | 内容 |
|---|---:|---:|---|
| `culture-literature` | 15 | 7 | 抒情诗、叙事诗、史诗、挽歌、民谣、俳句式瞬景诗、流浪汉/哥特/书信体/框架/成长/社会现实主义小说结构、宫廷赞助、翻译、民间故事母题 |
| `names-asian` | 9 | 8 | 汉语、日语、韩语、南亚、阿拉伯语、波斯语、突厥语、越南语、蒙古语姓名池 |
| `names-european` | 9 | 8 | 英语、法语、德语/日耳曼、意大利语、伊比利亚、斯拉夫、希腊语、凯尔特、北日耳曼姓名池 |

示例姓名保存在条目的 `aliases` 与 `summary`，供元素页检索；具体地区、时代、读法和转写必须由角色卡固定。姓名资料不能单独推断身份，文化资料不能替代故事设定。

**本批定稿并已入库：24 条美食、47 条来源（21 条 Britannica、26 条英文 Wikipedia）。** 独立技术测试 44 项通过，定向勘误后美食专项 14 项复验通过；旧 15 分区导出逐字段不变、重复导入零写入、SQLite 完整性正常。内容经分层抽查，不等于全部事实审定，仍保留 `needs_review`。核对当前交付库：

```powershell
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --with-traits --with-cuisine --with-culture --check
```

名单同样不用通配：文件名写死在 `tools/encyclopedia_build.py` 的 `CUISINE_GROUPS` 里，
与 `GROUPS` / `TRAIT_GROUPS` 并列且互不交叉。库里条目的 `review_status` 仍然全是 `needs_review`。

## 二、生活八组（254）

### 2.1 原六组（207）

| 组 | 文件 | 元素 | 来源 | 收什么 |
|---|---|---|---|---|
| staples | [staples.json](staples.json) / [md](staples.md) | 33 | 39 | 谷物、豆类、块根与油料作物 |
| produce | [produce.json](produce.json) / [md](produce.md) | 37 | 49 | 蔬菜、水果、坚果 |
| flavors | [flavors.json](flavors.json) / [md](flavors.md) | 33 | 37 | 香料、调味、饮料、糖源 |
| animal-foods | [animal-foods.json](animal-foods.json) / [md](animal-foods.md) | 28 | 32 | 畜禽、水产、乳蛋等动物性食品 |
| materials | [materials.json](materials.json) / [md](materials.md) | 36 | 24 | 天然矿物矿石燃料与人工材料 |
| tools | [tools.json](tools.json) / [md](tools.md) | 40 | 38 | 农业、厨房、纺织、木石金工、运输工具 |

### 2.2 增补两组（47，本轮新增）

| 组 | 文件 | 元素 | 来源 | 补的缺口 |
|---|---|---|---|---|
| food-supplement | [food-supplement.json](food-supplement.json) / [md](food-supplement.md) | 23 | 30 | 原六组里缺位的可食物产（黍、指状粟、根茎叶菜、水生作物、面包果/菠萝蜜等热带果、腰果等） |
| craft-supplement | [craft-supplement.json](craft-supplement.json) / [md](craft-supplement.md) | 24 | 34 | 纤维→纱→布与革、纸、烛、皂、骨角材料、锹铲/锉/风箱/针剪等工艺链缺环 |

两组都是**独立增补文件**，不改动原六组的任何条目、标签或状态；分组前缀分别是 `food_supp_` / `craft_supp_`，不与原六组撞 id。

## 三、题材与现实六组（274）

| 组 | 文件 | 元素 | 收什么 |
|---|---|---|---|
| eastern | [eastern.json](../element-catalog/eastern.json) | 54 | 东方玄幻 / 仙侠母题 |
| western | [western.json](../element-catalog/western.json) | 54 | 西方奇幻 / 黑暗奇幻母题 |
| society | [society.json](../element-catalog/society.json) | 53 | 历史 / 现代都市的制度与组织 |
| steam-horror | [steam-horror.json](../element-catalog/steam-horror.json) | 50 | 蒸汽朋克 / 民俗恐怖 |
| reality-physical | [reality-physical.json](../element-catalog/reality-physical.json) | 32 | 现实物理基础 |
| reality-human | [reality-human.json](../element-catalog/reality-human.json) | 31 | 现实人文基础 |

这六组是旧 schema（元素带 `category` 与 `genres`，七节里的两节叫 `story_consequences` / `adaptation_limits`），导入时由显式 adapter 映射到新七节，原字段整份保留。详见 [database-使用说明.md](database-使用说明.md) 第 5 节。

## 四、来源与证据（诚实范围）

- 每条元素至少引一个来源；来源的 `access` 原值入库，只表示**采集侧声称读了正文**（`read`）或只取到摘要/片段（`search_only`），`unavailable` 则明说没拿到。**`access: read` 不是事实核实结论**，库里不做真伪判定。
- 本轮两个增补组的来源构成：`food-supplement` 30 条全部 `read`（其中 1 条为策展摘要/索引页，已在组内 `supports` 与本组 md 中注明范围）；`craft-supplement` 34 条中 31 条 `read`、3 条 `search_only`（摘要页与引文片段，证据强度较低，已在条目内标注）。具体清单以各组 `.md` 与 JSON 为准，本页不复述。
- 来源优先 FAO / 植物园 / 博物馆 / USGS / 教育机构 / 专业参考；summary 只写能支撑定义与背景的范围，创作推演与来源证据分开。**不把摘要当全文，也不把来源的说法当成已核事实。**
- 所有 `details` 七节（definition / mechanism / conditions / exceptions / story_uses / historical_scope / evidence_and_uncertainty）齐全，但「写得长」不等于核实过。

## 五、怎么用

```powershell
# 按显式 14 组名单建一份候选库（临时路径，不碰交付库）
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --out temp/encyclopedia.sqlite3
# 核对现有库与名单条数是否一致
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --check --out temp/encyclopedia.sqlite3
# 带特质 + 饮食分区
D:\anaconda\python.exe -X utf8 -m tools.encyclopedia_build --with-traits --with-cuisine --with-culture --out temp/encyclopedia.sqlite3
```

构库名单写在 `tools/encyclopedia_build.py` 里，逐组显式登记：历史 14 组在 `GROUPS`，
特质在 `TRAIT_GROUPS`（`--with-traits`），饮食在 `CUISINE_GROUPS`（`--with-cuisine`）；
`docs/element-catalog/shared-themes.json` 是聚类索引、不是元素，故意不入名单。
查询、检索、导出与还原用 `tools/encyclopedia_cli.py`，完整用法见 [database-使用说明.md](database-使用说明.md)。

## 六、明确没做的事

1. 没有对任何条目做事实核验，也没有升 `review_status` / `detail_status`。
2. 没有把百科接进故事 prompt、旧存档或经营模拟；百科中存在不等于当前世界里存在。
3. 没有改写 `data/`、`StoryPackage/` 或任何游戏 runtime。
4. 当前工作区的 `artifacts/human-encyclopedia/encyclopedia.sqlite3` 已生成并含文化分区；其他机器仍应按显式名单重建，不把忽略的 SQLite 文件当作唯一依赖。
5. 组内数字、来源数均以本环节现读 JSON 为准；若采集侧后续勘误，本页与 `tools/encyclopedia_build.py --check` 应同步重算。

## 七、模型 token 统计

模型请求的 token 使用量不由百科库直接决定：只有元素装配后，选中的条目才可能进入故事包，再由运行时按需检索。查看实际消耗请使用 [token-usage-evaluation.md](../token-usage-evaluation.md)；文化资料不会整体注入 prompt。
