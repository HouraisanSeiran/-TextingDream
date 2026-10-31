# 空态作者空间 + civ 城市稳定引用

用户删除全部旧故事后，作者在没有世界的时候仍需要能画图、存图。同时，civ 城市必须**链接已有实体**，不能新建同名城。

## 1. 空态空间草稿

| 行为 | 空世界（无 pointer） | 有世界 |
|---|---|---|
| `POST /api/inner/spatial-drafts` | 可建，`story_base_revision: null` | 可建，= 当前 revision |
| `GET /{id}`、`GET` 列表 | 可读 | 可读 |
| `PUT`（CAS，`expected_revision`） | 可改 | 可改 |
| `GET /{id}/conversion` | `ready:false`，`missing` 含 `story_base_revision_missing` | 正常判定 |
| `POST /{id}/town-input` | 拒绝（不能凭空找当前故事） | 正常 |

`story_base_revision: null` 的含义是「画的时候还没有世界」，**不会**被静默改绑到后来出现的某个故事。

实现要点（`app/spatial_draft.py`）：`SpatialDraftService.base_revision()` 在无世界时返回 `None`（旧实现无条件 `runtime.package()['id']`，空态 POST 直接崩）；`_resolve_story()` 接受 `None`；`prepare_conversion()` 增加 `story_base_revision_missing`。

## 2. `city_ref`：链接原件里已有的 civ 城市

请求（`draft.city_ref`，可省略）：

```json
{"import_id": "sn_…", "source_sha256": "<64hex>", "city_id": "settlement:0"}
```

- **三键必填**；`import_id` 与 `source_sha256` 必须与 `environment_ref` 完全一致（同一份原件）。
- **`city_id` 的形状是 `settlement:<数字>`**：上游 civ 的 settlement 实体 id 是整数（真实样例 `id: 0`）。
**原件字节的校验不在这里复制**：走已验的 `native_worlds.snapshot_bytes(store, <store.parent>, import_id)` —— 它在返回字节前强制文件名不出 `map_imports` 目录、并重算**整件** SHA-256 与记录比对。所以「记录指向 A、磁盘实际是 B」与「record.file 被改成越界路径」都在拿到 civ 前被拒，`identity_verified` 不会在另一个文件上成立。然后才用既有 `civ_atlas_history.decode_civ_part` 解 civ、按 id 命中实体，回填 `name / region / cell / founded`，并标 `identity_verified: "snapshot_civ"`。
- 找不到就拒（`这个原件里没有这个城市实体（settlement:N）`），**不新建同名城**，也不接受只给 `site_name` 冒充城市。
- 草稿里**不保存 civ 数组副本**，只保存引用与校验结果；地图渲染仍读原件。

响应里的 `city_ref`（`summary` 也带，保证 GET→PUT 无损往返）：

```json
{"import_id": "sn_…", "source_sha256": "<64hex>", "city_id": "settlement:0",
 "name": "灰港", "region": 0, "cell": 0, "founded": -320,
 "identity_verified": "snapshot_civ"}
```

`name/region/cell/founded` 是**只读派生值**：前端 PUT 时只回传三键，不要把派生字段发回来。

## 3. 明确不做

- 不因 `city_ref` 生成经济/供给/任意 route；它只是链接。
- 不新增 map codec；读取走已审的 `parse_container` → `decode_civ_part`。
- 不把 `branch`/`year` 塞进 `city_ref`：需要时复用既有 `world_basis_ref`（它已有 `branch`/`base_year`）。

## 4. `/native-map` 前端产物托管

- 前缀 `/native-map/`（独立挂载，不会被旧壳 `/static` 遮蔽）：入口 `/native-map/dream-host.js`、`/native-map/dream-host.css`，相对资源（`fonts/`、`portraits/` 等）同前缀可取。
- 产物目录固定 `external/civ-atlas/dist-dream`（本地构建，不入源码仓）。
- 缺构建时这两个入口返回 **503 + 构建说明**，不启动崩溃、不自动装依赖、不启 Vite。

## 5. 测试

- `tests/test_spatial_empty_and_city.py`（8 项）：空态 POST/GET/PUT CAS 且不冒出 package/session；`null` 草稿不可转换；`city_ref` 命中真实实体（回填名来自原件而不是 `site_name`）；缺 `city_id` / 换来源 / 不存在的城市 / 无 `environment_ref` 均拒；`note` + `city_ref` 的三轮 GET→PUT 无损往返。
- `tests/test_native_map_static.py`（2 项）：构建产物按前缀可取（js/css/字体）；缺构建给 503 且 `/static` 取不到。
- 既有空间回归 `tests/test_spatial_draft.py` + `tests/test_spatial_integration.py`：其 `FakeRuntime` 补 `has_world`、版本核对用例自己提交最小世界（不在生产启动时造包），全部通过。
