# TD 粗模型山脉走向场：运行规范

日期：2026-11-05。状态：用户确认。代码：`app/world_gen/td_coarse.py`、`tools/td_coarse_ridges.py`、`tests/test_td_coarse.py`。

## 1. 用途

只跑 Terrain Diffusion 的粗模型（coarse_model，约 7.68 km 一格），以板块骨架为条件，输出世界尺度的山脉大体形状和走向：

- `elevation_m`、`mountain_mask`、`ridge_angle_rad`、`ridge_coherence`、`coarse_channels`；
- 用来验收快速世界层或骨架的山脉走向，之后也可以参与确定山脉形状（是否参与由用户另定）。

不跑 latent 主模型和 30 m 解码器。

## 2. 运行设备规则

- **正式的世界尺度运行（5000 km、万公里）放到独立显卡上跑。** 用户通知有显卡之前，不在 CPU 上做万公里全量运行。
- **当前（无独立显卡）只验证思路：** CPU 运行限于 1600 km 世界、或 5000 km 上不超过约 500 km 的窗口，用于对比走向和测速。
- 运行前检查可用内存（低于 2 GiB 不启动），记录设备、线程数、每块耗时、峰值内存，写进 `runtime-stats.json`，不进产品身份。
- 集成显卡（AMD Radeon，约 512 MB）PyTorch 不识别，不使用；不为此安装新驱动或 DirectML。

## 3. 计算规则

- 分块方式沿用 TD 的粗模型推理：64 格块、线性权重窗混合；步长、批大小、线程数、跳过深海等是可调参数，写进 manifest。
- 跳过的块（如远离陆地的深海）必须在 manifest 里列出跳过规则和块数，产品中对应位置标为"未计算"，不填假值。
- 种子：`SHA256("{world_seed}:dream-world-gen:td-coarse-ridges")` 前 8 字节；同骨架、同参数结果必须确定性一致（显卡上混合精度的末位差异需注明）。
- 改动任何会影响数值的参数（步数、步长、精度、跳过规则），须在 1600 km 上与已冻结的 `world1600-v4-shaped/td-coarse-ridges`（身份 `6d5d2c4e…750e`）对比，主脊方向偏差中位数变化 ≤ 2°、1000 m 山地 IoU 下降 ≤ 0.03 才算可接受。

## 4. 显卡上运行的耗时估算

估算方法：块数 × 每块显卡耗时 + 模型加载。块数由 `tools/td_coarse_ridges.py --plan-only` 给出；每块显卡耗时在有显卡后用 `--benchmark` 实测替换。估算值和依据写进 `estimate.json`，标明"推算"或"实测"。

## 5. 不做的事

- 不在 CPU 上硬跑万公里全量。
- 不改 Terragenesis 文件，只 import。
- 不用 D8。


## 6. 优化结论与设备开关（2026-11-05 更新）

- **推荐参数：** 跳过离陆地 120 km 以外的深海块，去噪步数 20 → 15；步长 48、fp32、批大小 1 不变。1600 km 上对冻结产品：主脊方向偏差中位数 0.2°，1000 m 山地 IoU 0.987，达标。加大步长（52/56）、步数降到 10 都会让 IoU 跌破阈值，不采用。
- **设备开关：** `--device` 默认 `cpu`，只用 CPU；`auto` 才会自动选显卡。`--benchmark` 在没有可用显卡时直接报错退出，不在 CPU 上跑。
- **PowerShell 屏蔽显卡：** 要设 `$env:CUDA_VISIBLE_DEVICES='-1'`。设成空字符串等于删掉这个变量，不起屏蔽作用（2026-11-05 曾因此误用一次显卡）。
- **显卡耗时估算（推算，未实测）：** 见 `artifacts/td-coarse-opt/estimate.json`。万公里约 441–620 块，约 2–30 分钟；5000 km 155 块，约 1–8 分钟。有显卡后用 `--benchmark` 实测替换。
