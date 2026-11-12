# 天气美术待办与界面修复交接（2026-11-06）

> **历史复核（2026-11-08 整理）**：这是 2026-11-06 的天气画面待办。旅程里天气只接到只读接口，见 [现状.md](现状.md)。

用户验收反馈：天气只覆盖画面一块，出现染色矩形边界、积雪错位等；代码问题由当时那一轮修复，美术表现留给后续。此文件记录待办，不代表已通知或唤醒其他智能体。

## 已修复的代码问题

1. **DPR 坐标不统一**：总预览的底图为 `1400*dpr × 900*dpr`，但每个 pass 后把 context 重置成单位矩阵。snow/fog/sand/fantasy 等继承调用方坐标，结果只覆盖左上 `1400 × 900` 个设备像素。DPR1.5 时仅覆盖 2/3 宽高（面积约 4/9），DPR2 时为 1/2 宽高（面积 1/4）。积雪和遮挡剪影也随之相对建筑缩小错位。
2. **HTTP 安全策略不兼容**：可选 aurora/ice/wind/sky 加载器使用 `new Function(code)` 和内联脚本文本。服务的 `script-src 'self'` 阻止这两种执行方式，页面误报“素材语法错误”。现在用同源外部 script 标签加载，保留缺文件/缺导出/创建失败状态提示，没有放宽服务安全策略。

总预览现在以 `drawLayer()` 为每次天气绘制建立 DPR 变换，并 save/restore 隔离状态。底图继续按设备像素 1:1 合成；模块内部已有的 `setTransform(dpr)` 不会叠乘。没有改美术模块的颜色、纹理、粒子样式和模型。

## 留给美术的复核项

下表是修复坐标后仍需判断的画面表现，不应再把上面的矩形覆盖和整体错位当作素材画风问题。

| 优先级 | 观察/待复核 | 后续工作 |
|---|---|---|
| P1 | 大雪的地面白块较均匀，边缘和屋檐雪带部分呈直线/规则锯齿；当前 roofY 为近似接口 | 在保持正确 CSS 坐标和 occluder 对齐的基础上，调整积层形状与厚度；若需要精确屋脊/坡面，先提出 scene 元数据契约再协同代码实现 |
| P1 | 夜间窗光、路灯、门火光晕较亮，亮点较密；原用户第二张图中尤其明显 | 校对灯种尺度、亮度、窗位和雪地反光；当前预览窗位由建筑包围盒估算，偏位处应记录具体建筑 ID/目标坐标，避免无依据整体平移 |
| P1 | 灰烬雨全屏暖红调色已恢复；港口水面仍见较白、方形的倒影区 | 复核水域格与倒影的视觉融合、透明度和边缘。先判断是否符合实际水域范围；若几何越界或 DPR 相关，请按代码 bug 回报，不用改纹理掩盖 |
| P1 | 可选 ice/wind/sky/aurora 之前在 HTTP 页面根本没有运行 | 必须在 HTTP 页面重新目视冻雨/霰/霜/雾凇、台风/风眼/龙卷、热浪/彩虹、极光，不能沿用被跳过时的结论 |
| P2 | 合成范围修正后，高 DPR 的绘制工作量增加 | 用普通浏览器在 DPR1/1.5/2 检查动画流畅度；截图右上无头 FPS 只作线索，不能宣称完成性能验收 |

## 截图与复现入口

用户原图已复制到项目 artifacts，避免依赖临时剪贴板路径：

- [原灰烬雨截图](../artifacts/weather-preview-fix/user-ashfall-before.png)
- [原夜间雪截图](../artifacts/weather-preview-fix/user-snow-before.png)
- [修复后灰烬雨 DPR1.5](../artifacts/weather-preview-fix/ashfall-dpr1.5.png)
- [修复后暴风雪 DPR1.5](../artifacts/weather-preview-fix/snow-dpr1.5.png)
- [修复后夜间小雪 DPR1.5](../artifacts/weather-preview-fix/snow-night-dpr1.5.png)

服务验收入口：

- [灰烬雨 DPR1.5](http://127.0.0.1:8000/static/weather-fx/index.html?dpr=1.5&preset=ashfall)
- [夜间小雪 DPR1.5](http://127.0.0.1:8000/static/weather-fx/index.html?dpr=1.5&preset=light-snow&hour=23)

素材本身不是本轮重画范围。代码后续有变化时，继续保留固定种子、时刻、DPR 与场景进行复核。

## 回归证据

`node tests/weather_preview_browser.cjs` 使用真实 HTTP 服务、原 CSP、本机 Edge，无头遍历 DPR1/1.5/2。检查可选模块加载、CSP violation、每层 DPR 变换、真实灰烬雨渲染前后画布四角的像素变化，以及手动 28 种天气、16 个预设、生成器状态校验。输出在 `artifacts/weather-preview-fix/browser-report.json`。

修复前最小复现命令 `node tests/weather_preview_browser.cjs`（初始只跑 DPR1.5）失败：4 个模块被 `script-src:eval` 拒绝，snow/fog/sand/fantasy 的入参 context 缩放为 1，预期 1.5。修复后补充了四角像素检查，避免仅检查“页面没报错”。
