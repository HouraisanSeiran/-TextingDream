# 河网流向：禁止新用 D8（2026-11-05，用户决定）

**结论：今后任何新的河网、汇流、侵蚀代码都不得使用 D8（每格只流向 8 邻格之一）。** 一律改用 Terragenesis 的非规则图汇流。

## 为什么

织梦世界层河网 v1–v5 都用 D8，图上反复出现同一类缺陷，靠调参数和画法修不掉：

- 河道只能走 0°/45°/90°/135°，平地和缓坡上出现几十公里的长直段；
- 河口一排平行线（梳齿）；
- 湖内平地上的 45° 平行束；
- 坡面上成片平行短沟。

根因是方向只有 8 个，不是参数问题。v3–v5 的平地收敛、噪声弯曲、显示层合并都只是补救，湖外缓坡直线始终消不掉（见 `artifacts/td-world/world-960m-v5/README.md`）。

## 用什么

| 用途 | 模块（Terragenesis，只 import 不改） |
| --- | --- |
| 非规则图汇流 + 汇水累计 | `terrain_pipeline/surface_rivers/drainage.py` 的 `route`；底层 `terrain_pipeline/irregular_drainage.py`、`irregular_grid.py`（`grid_mesh`） |
| 河道中心线平滑 | `terrain_pipeline/channel_centerline.py` |

依赖 numba：织梦 `.venv` 没有，需用 Terragenesis 的 `runtime/venv/Scripts/python.exe` 运行，或另行安装。

## 现有 D8 代码（保留，只供旧产物复现）

不要在新任务里 import、复制或扩展下面这些：

- `app/world_relief/drainage.py`（`route(..., area_mode='d8'|'mfd')`）
- `app/world_relief/erosion.py`、`product.py`（world-relief-pilot v1/v2）
- `app/world_relief/td_flats.py`（D8 平地收敛）
- `app/world_relief/td_freeze.py`、`td_freeze_v2.py` … `td_freeze_v5.py`
- `app/world_relief/td_hydro.py` 中依赖 D8 receiver 的挖穿（`breach`）
- `tools/eval_td_speedup.py` 里的 D8 流域标记（仅作评估指标）

保留原因：冻结产品 `world-relief-pilot`、`world-relief-pilot-v2`、`td-world/world-960m` 至 `world-960m-v5` 的身份与复现依赖它们，测试也覆盖它们。删除会让这些产物无法复验。新产品稳定在非规则图汇流上之后，可以再整体归档。

## 给子代理的规则

- 派发河网/汇流/侵蚀任务时，prompt 里写明"不得使用 D8，用非规则图汇流"，并引用本文。
- 发现自己要写 `8 邻格最陡下降`、`receiver = 8 方向之一` 之类逻辑时，停下，改用上面的模块。
- 评估指标里可以统计河段方向分布，用来证明**没有**锁在 45° 倍数上。
