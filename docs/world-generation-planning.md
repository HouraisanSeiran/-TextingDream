# 世界生成规划与局部 30 m 接口

所有规划与查询均为 CPU、只读；任何 GPU 生成都是显式命令，带两段式内存检查与显卡检查，门槛不下调。

## 配置 `dream-world-config-v1`
示例：`docs/examples/world-config.example.json`。代码：`app/world_gen/config.py`。
- `world_name`、`world_seed`（默认 20260903；子种子 = SHA256(`{seed}:dream-world-gen:{用途}`)[:8] 小端，记录在 manifest）。
- `world`：`width_km/height_km` 或 `size_km`（1600/5000/10000…）、`type`（multi-continent 默认/pangaea/archipelago/two-continents/inland-sea）、`ocean_fraction` 0.5–0.8、`mountain_cover`（low/medium/high=0.06/0.12/0.20，或 0.02–0.4 的陆地占比）、`origin_km`。
- `world_layer`：`spacing_m` 960|1920、`coast_buffer_km`。
- `skeleton`：`source=existing`（path + 64 位 identity）或 `new`（plates/cell_size_km/steps；格距默认 ≤2000 km→10 km，≤6000→20，否则 25）。
- `local_sites[]`：id、type(town/special_terrain/story)、center_x_m/center_z_m、radius_m 或 size_m、**reason 必填**。未登记区域不会被安排。
- `map_style`、`notes`；规范化后附 `identity`（规范 JSON SHA-256）。

## 计划 `plan.json`
`python tools/plan_world.py --config <cfg> --out <plan.json>`（`app/world_gen/planner.py`）。内容：
- 骨架：existing 则用 `load_product` 校验身份；new 则列出 Terragenesis `plan()` 预检结果，不执行。
- 世界层：页数、已有页数、GPU 时长（依据 `generation-summary.json` 实测 ≈4.76 s/页 与 `speedup-test/estimate.json` 的 s/km²）。
- 局部 30 m：登记点 → 对齐 512 native 的 tile（513×513 样点，末行列与邻块重复）→ 页数/GPU 时长（依据 `s1-benchmark.json` decoded 页）/磁盘。单次请求最多 16 tile。
- `identity` = 计划规范 JSON 的 SHA-256。

## 新骨架生成（CPU，≈1600 km 验证）
`python tools/generate_world_skeleton.py --preset <类型> --size-km 1600 --name <名>`；`--plan-only` 仅预检。产物 `artifacts/worlds/<名>/{skeleton.npz, preview.png, skeleton-run.json}`。
- 导入 Terragenesis `tectonic_evolution`（只 import）；通过 `evolve(config, initial_state)` 注入预设形状的大陆地壳场；海洋比例靠分位阈值少量迭代，山脉覆盖靠板块速度。
- `tp.freeze/save_product` 与 `plan()` 写死 world_seed=20261020，故 `skeleton.npz` 采用 TD `read_plate` 可读的版式（`manifest_json` + `final/*`，身份规则同 `app/world_relief/source.identity`），`plan()` 预检时仅替换种子。
- 深海竖条纹来自 Terragenesis 供体单元平流在洋壳厚度上留下的 1–2 格周期纹；`elevation_m` 在离陆地 ≥3 格处做回绕高斯平滑（见 manifest `deep_ocean_smoothing`），其余字段保持原样。
- 山脉覆盖是代理量：陆地格中代理高程 >1500 m 的占比，不是地质实测。

## 局部 30 m
`app/world_gen/local30.py`：
- `request_local(world_root, cx, cz, size)`：只读，未准备返回窗口描述，绝不生成。
- `prepare_tile(...)`：显式；先内存门（启动≈4.5 GiB 可用；每窗口暂存+1 GiB），再显卡门（空闲 ≥4096 MiB、无 build_td_*/eval_td_speedup 进程、利用率 ≤10%）；用 `td_resident.periodic_factory`（与世界层同一条件）；冻结为 `world-map-product` 版式（manifest + layers/*.npy），schema `terragenesis-local30-v1`，kind `terragenesis-local30`，带 purpose/reason/世界层身份/一致性检查。
- 命令：`python tools/prepare_local30.py --config <cfg> --site <id> [--dry-run]`。
- 一致性检查：30 m 解码高程块平均到 960 m，对比世界层（latent 低频）。上游实测两者 MAE 约 127 m，量级差异是预期，报告不隐藏。
- 适配器：`app/map_source/adapters.py::load_local30`，注册于 `registry.py`；契约测试已覆盖。

## 限制
- 局部产物无河湖矢量；status=4 与 3 的区分只在 tile 内判断。
- 10000 km 骨架 `plan()` 预检 `allowed=false`（超出默认 2e8 cell-plate-steps），需显式放宽预算并另行批准。
- 离线演示：`python tools/build_local30_demo.py` → `artifacts/local30-demo/index.html`。
