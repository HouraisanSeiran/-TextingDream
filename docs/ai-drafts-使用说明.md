# AI 草稿：按名字、标签和方向补全元素 / NPC 角色卡 / 故事包

代码：`app/ai_drafts.py`（服务 `service.ai_drafts`），界面：`app/static/ai-drafts.js`（作者侧“AI 草稿”页），测试：`tests/test_ai_drafts.py`。

## 1. 规则（用户已拍板）

1. 生成结果**一律只存为草稿**（旅程库 `documents` 表，`kind='ai_draft'`）。游戏进行中也可以生成。
2. 生成、编辑、确认、拒绝都**不修改**任何故事包的 `story.mechanics.element_manifest`，也不改运行中旅程的 NPC 绑定。旅程只读自己绑定的包版本。
3. 草稿必须经作者**显式确认**才能使用；可以拒绝。确认前：元素不进百科库，NPC 卡不进任何故事包。
4. “开局后不从库里补新类型”这条规则本次不动（见 §7）。

## 2. 流程

```
填名字/标签/方向 → 生成（模型或离线模板）→ 规范化（强制口径）→ 校验
   ├─ 不通过：带错误回传模型重试一次 → 仍不通过：整体拒绝，零写入（不存草稿）
   └─ 通过：存草稿 status=draft
草稿 → 查看 / 编辑（编辑后重新校验，不通过则草稿不变）→ 确认 或 拒绝
```

- 离线（`provider.config()['offline']` 为真）时用确定性模板，记一条 `offline_trace`，不重试。
- 草稿状态：`draft` / `confirmed` / `rejected`。记录 `request`、每次尝试的模型输出与错误（`attempts`）、`validation`、`created`/`updated`、`offline`、`usage`、`history`。
- 已确认的草稿再编辑会回到 `draft`，需要再次确认；元素再确认得到库里的新版本。
- 已拒绝的草稿不能编辑或确认；已确认的草稿不能拒绝（拒绝不撤回已入库版本）。

## 3. 接口（全部在 `/api/inner/`，受作者 token 头 `X-TextileDream-Token` 保护）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/inner/ai-drafts/elements` | 生成元素草稿。体：`name`（必填）、`tags`、`direction`、可选 `primary`（须在 PRIMARY 词表）、可选 `tradition`（小写英文） |
| POST | `/api/inner/ai-drafts/npcs` | 生成 NPC 卡草稿。体：`name`、`tags`、`direction`、可选 `character_id`、`location_id`（须在当前故事包里） |
| POST | `/api/inner/ai-drafts/stories` | 故事包简化入口。体：`title`（可选）、`tags`、`direction`（必填）、`kind`=`worldview`/`complete`、可选 `historical_reference`、`city_count`、`output_tokens`。返回 `world_generator` 的草稿 |
| GET | `/api/inner/ai-drafts?type=element\|npc` | 草稿列表（摘要） |
| GET | `/api/inner/ai-drafts/{id}` | 草稿全文 |
| PUT | `/api/inner/ai-drafts/{id}` | 修改。体：`{revision, content}`；重新规范化 + 校验，不通过 400 且不改动 |
| POST | `/api/inner/ai-drafts/{id}/confirm` | 确认。体：`{revision?}`；NPC 还需 `character_id`（或生成时给过）与 `package_revision`（当前故事包版本） |
| POST | `/api/inner/ai-drafts/{id}/reject` | 拒绝。体：`{revision?}` |
| POST | `/api/inner/ai-drafts/restore-confirmed` | 把存储里全部已确认元素幂等重新导入百科库 |

另外，`PUT /api/inner/npc-cards/{character_id}` 现在调用 `npc_cards.save_card`，与 AI 草稿确认走同一条保存路径，行为不变。

## 4. 元素：强制口径与校验

**代码覆盖、不信任模型**（`normalize_element`）：

- `id` = `player_` + 随机串，由代码生成；`name` 用玩家给的名字。
- `evidence_grade='inferred'`，`source_ids=[]`，**不生成任何 sources**；模型写的 sources / source_ids / evidence_grade / review_status / id 一律丢弃。
- `review_status='needs_review'`，`detail_status='needs_detail'`。
- `evidence_and_uncertainty` 开头强制写“本条由 AI 按玩家方向生成，为设定推演，未经来源核实。”
- 标签：模型写的 `price:`/`terrain:`/`season:`/`sold_by:`/`restriction:` 丢弃，按 `game` 由 `validate_game` 重新派生；追加 `origin:ai_player_draft`；给了 `tradition` 就强制为 `tradition:<值>`。
- `origin` 字段记录 `kind=ai_player_draft`、原始请求与是否离线。

**校验**（`validate_element`）：`primary` 在 `tools/catalog_overlay.PRIMARY`；summary 与七节非空、限长；全部标签匹配 `_TAG_RE`；不许 `primary:`/`evidence:`；至少一个 `kind:`；`game_fields.check_element_tags`；药材/方剂（`medicinal_*`、`formula`）不得出现剂量、用法、疗效类词（服用、外敷、主治、疗效、功效……）或“数字+克/钱/两/毫升”；最后包成 `group: player-created` 的文档走 `enc.prepare_document`。

玩家给的中文标签由模型映射成规范英文标签，映射不了的写进 aliases 或正文；含中文/大写/空格的标签会让校验失败并重试。

**确认**：库路径用 `service.elements.library()`（与元素装配相同的定位与允许目录策略）。库不存在时报错、不自动建库，草稿保持未确认。确认 = `enc.import_document(..., namespace='player-created')`：

- 同内容重复确认幂等（`idempotent: true`，不新增版本）；改后再确认得到 v2、v3……旧版本仍可读。
- 每个确认过的版本在旅程库留一份完整副本（`kind='ai_confirmed_element'`）。`tools.encyclopedia_build` 重建库后，调用 `restore-confirmed`（或 `service.ai_drafts.restore_confirmed()`）按确认顺序幂等重导。
- 入库后可在元素装配页按 `primary:<键>` 或 `origin:ai_player_draft` 检索，再由作者按现有流程采纳进故事包清单。

## 5. NPC 角色卡

- 模型补全 `npc_cards.FIELDS` 的全部十个字段（`identity`、`experiences`、`values`、`goal`、`pressure`、`boundaries`、`bargaining`、`social_context`、`emotion`、`failure_response`，各 `{text, visibility}`）与 1–8 条 `knowledge`。
- 校验：`npc_cards.NPCCard` 结构校验；十个字段全部非空；至少一条 knowledge；knowledge 不得是 `observation`，正文/来源不得含“亲眼、亲见、目睹”等措辞（AI 草稿不声称人物亲见任何事）。同样重试一次，失败零写入。
- 确认走 `npc_cards.save_card`：基于 `package_revision` 提交新故事包版本；版本过期则拒绝。**不自动绑进已开始的旅程**，已有旅程继续用旧版本的卡。

## 6. 故事包简化入口

`generate_story` 把标签与方向拼成 `instruction`，组装 `GenerateWorldRequest(kind=worldview|complete, ...)` 后调用 `world_generator.generate`。之后的编辑、校验、保存、发布全部用现有 `/api/inner/generators/...` 接口。元素清单仍由生成器按现有规则固定（缺省为当前包快照），本入口不传 `elements`，不会从库里补新条目。

## 7. 以后放开“开局后从库里补新类型”时要改的地方

- `app/element_assembly.py`：`context_elements` 运行期只读旅程绑定版本的清单快照；放开要在这里定义旅程中途新增元素的来源与审批。
- `app/ai_drafts.py` 的 `_confirm_element`：目前只入库，不碰任何清单；放开后若要“确认即加入当前旅程”，应另走 `ElementAssembly` 的草稿 → commit 流程，并明确是否只影响新旅程。
- `npc_cards.save_card` 与 `runtime.new_session`：已有旅程绑旧包版本；若要运行中换卡，需要新增旅程级的绑定迁移。
- `tests/test_ai_drafts.py::test_generate_and_confirm_leave_locked_manifest_and_journey_alone` 守着现规则，放开时要同步改。
