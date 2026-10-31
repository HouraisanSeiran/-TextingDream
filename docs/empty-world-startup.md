# 空世界启动（无预制故事）

用户已删除全部旧故事包与旅程存档。系统现在从**空世界**启动，不再自动导入任何预制世界。

## 事实（已核实）

* `StoryPackage/` 只剩 README 与说明文档；`world_packages/`、`story_packages/`、`character_packages/` 均为空。
* 正式库 `documents` 仅 `corpus×2`、`settings×1`。
* 启动后库目录仍是空的，**没有重建任何旧预制目录**。

## 改了什么（`app/runtime.py`）

删除旧启动时硬写的行为：

* `StoryPackage/玄陆` 自动 `copytree`；
* `world_packages/玄陆_世界包.json` fallback；
* `character_packages/xuanlu_初始角色包.json` 强制读取；
* 无 pointer 时自动 `commit_package` 导入初始世界。

换成：

* 无 pointer → `self.files = None`（**没有世界**），不构造隐藏默认故事，也不提交空包；
* 有 pointer 但目录/`story.json` 缺失 → 明确 `ValueError`（可读原因，不静默降级）；
* 启动回填笔记会跳过 revision 已不存在的旧旅程（不删数据、不崩）；
* `package()` 无 pointer 时抬 `还没有可用的世界：请先创建或采纳一个世界，再开始旅程`；
* 新增 `has_world()` / `empty_state()`；
* `new_session()` 无世界直接拒（同一句原因），不去 `reload_documents()`；
* `commit_package()` 在 `self.files is None` 时自己认领一个目录：`world_<slug>`（`revision_folder_slug`，只留 ASCII 字母数字下划线）；
* `session_files()` / `list_packages()` 不再把 `玄陆` 当默认目录名。

## 契约变化（`app/web.py`）

`GET /api/bootstrap` 新增四个字段，旧字段不变：

```json
{"world": null, "packages": [], "can_start": false,
 "world_reason": "还没有可用的世界：请先创建或采纳一个世界，再开始旅程"}
```

有世界时 `world = {revision, title, story_id, places}`（只有公开标识）。`sessions` 只列 revision 仍存在的旅程。

`GET /api/inner/history/imports` 在空态返回 `story_revision: null` / `story_id: null`，地图导入与历史预览本身不依赖已有世界。

`POST /api/sessions` 在空态返回 400 + 上述原因。

## 测试

`tests/test_empty_world_startup.py`（5 项，空 temp 根 + temp 库，TestClient）：

1. 空根空库能建 app；bootstrap 空态字段正确；settings/corpus/history-imports 仍可用。
2. 新旅程被拒并给原因，拒后没有多出旅程。
3. 两次重启不重建旧目录（`StoryPackage` 无子目录、`world_packages` 不存在）。
4. 只有显式采纳世界后才 `can_start` 并能建旅程（真实 `commit_package`，不伪造 civ 生成端点）。
5. `Service` 单独启动也是空态，`package()` / `new_session()` 都抬可读的 `ValueError`。

## 明确未做

* **没有** civ 世界生成端点（不编造）；空态保留创建入口。
* 未改前端与静态资源；`empty-ui` 需要主代理再分配。
* 旧依赖 `StoryPackage/玄陆` 的历史测试仍会红，属迁移兼容，留最终阶段统一处理。
* 未启正式服务、未跑全量。
