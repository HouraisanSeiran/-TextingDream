# civ-atlas 本工程改动补丁（可重建）

基线：`https://github.com/guaner-334/civ-atlas` @ `0939c5f1622a5e45cfc16f645ea3845993ab3985`（v1.3.0，AGPL-3.0-only）
源码包：`codeload.github.com/guaner-334/civ-atlas/tar.gz/0939c5f1622a5e45cfc16f645ea3845993ab3985`
包 SHA-256：`8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC`（30 256 136 字节）

本目录把「我们改了什么」完整存在仓里，`external/civ-atlas` 本身不入库。
重建步骤见 `docs/civ-atlas-install.md`「重建一份逐字相同的树」。

## 2026-10-31 城址与地形一致性修复

本次补丁增加 `src/gen/raster.ts`（陆地核心约束）、`src/dream/mapPicking.ts`（按实际可见城镇及点击像素查询）、两个 `dream-*.test.ts` 回归和 `scripts/dream-coast-check.ts`，并更新宿主与画布。必须一并应用，不能只复制 `src/dream/`。现有世界重新读取会重铺地形，不修改原始存档。原件检查从 113/558 个水面城址降到 0/558。详细证据见工程根的 `工程交接与工作进度_2026-10-31.md`。

## 2026-10-30 前端核对改进

当前补丁还包括 `src/main.tsx`、`src/ui/App.tsx`、`src/ui/appLocation.ts`、`src/ui/ErrorBoundary.tsx`、对应 CSS Module，以及拆分后的 `src/dream/` 和 `tests/dream-frontend.test.ts`。`files/` 中的文件内容和镜像测试为当前依据；下方早期文件清单、哈希及“src 不改”描述只记录历史版本。

安装器现按相对路径递归复制全部补丁。不要只复制旧的三个导出文件。核对结果、已落实与剩余项见 [`../frontend-review-20261030.md`](../frontend-review-20261030.md)。

## 1. 文件清单

| 文件 | 相对上游 | SHA-256 | 许可处理 |
|---|---|---|---|
| `index.html` | 修改（新增一个 `<script>` 标签；见 §3） | `2415B55910D339343AC6D4D20B235B1DAC7FC1FFD7BE0991F80A23497D2E3131` | **上游原文的完整替换文件 → AGPL-3.0-only，不得以 MIT 重新授权** |
| `dream-export-entry.js` | 新增（本工程写） | `70EFB8A71F32EDD2427B34C6C66902BAAAC97BFFA933A4D0DEC0EF54E9BE3895` | 与上游同仓分发 → 本目录内按 AGPL-3.0-only 处理（见 §2） |
| `public/dream-export-tool.js` | 新增（与 `tools/civ_atlas_export.js` **逐字节相同**） | `2264D2000ED1A26BD82DB2BE75241B6EB13F323F059B67BD3B533D4A3FEF8A67` | 同上 |
| `src/dream/bridge.ts` | 【实】新增（本工程写） | 见 §5 的实算清单 | 与上游同仓分发且直接 import 上游模块 → AGPL-3.0-only |
| `src/dream/host.tsx` | 【实】新增（本工程写） | 同上 | 同上 |
| `src/dream/entry.tsx` | 【实】新增（本工程写） | 同上 | 同上 |
| `src/dream/landOverlay.tsx` | 【实】新增（本工程写） | 同上 | 同上 |
| `src/dream/landOverlay.css` | 【实】新增（本工程写） | 同上 | 同上 |
| `vite.dream.config.ts` | 【实】新增（本工程写；仓库根另有一份等价副本，见 §5） | 同上 | 同上 |
| `LICENSE` | 新增（上游 `LICENSE` 原文副本） | `0D96A4FF68AD6D4B6F1F30F713B18D5184912BA8DD389F86AA7710DB079ABCB0`（34 523 B） | **GNU AGPL-3.0 全文**，与 `external/civ-atlas/LICENSE` 逐字节相同 |

> 带【实】的六项是原生地图宿主（`dist-dream/dream-host.js`）的源码。它们**直接 import 上游
> `src/gen/*`、`src/render/*` 模块**（不是通过文件交换数据），所以属于「修改后的上游版本」，
> 分发时必须与上游完整源码一起提供。重建时要先把它们放到 `external/civ-atlas` 的对应位置。

> `dream-export-tool.js` 的哈希随导出工具的两处修复而更新（定宽 offset + payload 填充）。
> 它必须与 `tools/civ_atlas_export.js` 完全一致；核对：
> `(Get-FileHash tools\civ_atlas_export.js).Hash -eq (Get-FileHash docs\civ-atlas-patch\files\public\dream-export-tool.js).Hash`。

## 2. 许可与来源范围（重要）

**本目录不是 MIT。** 本工程自有代码按根目录 `LICENSE`（MIT）发布，但**不适用于本目录**，
也不构成对 civ-atlas 的任何重新授权。总说明见仓库根 `THIRD_PARTY_NOTICES.md`。

- **上游原有、被我们替换的整份文件：** `index.html`。它是上游文件的完整替换，绝大部分内容仍是上游代码，
  因此**整文件按 AGPL-3.0-only 处理**，不得删除上游版权/许可声明。
- **本工程新写的：** `dream-export-entry.js`（右下角按钮入口）与 `public/dream-export-tool.js`（IndexedDB 只读导出器）。
  两者源码头注释声明“本工程原创代码，不 import 上游模块”，**但本轮未逐行比对是否含上游片段**，
  因此：
  1. 本工程**不**对它们主张 MIT；
  2. 在本目录（与上游同仓分发）里一律**按 AGPL-3.0-only 处理**；
  3. 若将来要把它们单独归入 MIT，需先做逐行出处核对——**本轮没做，所以不宣称它们是 MIT**。
- **AGPL 原文随本目录提供：** `LICENSE` 是从 `external/civ-atlas/LICENSE` 原文复制的逐字节副本
  （`0D96A4FF…BCB0`，34 523 B），不是重写、不是摘要。
- **分发时的义务：** 分发含 civ-atlas 源码或其修改版时，应同时提供 AGPL-3.0-only 的完整对应源码、
  保留 `LICENSE` 与版权声明、标明改动；把修改后的版本作为网络服务提供时，上游要求以同样协议公开
  修改后的完整源代码。这是对上游原文的转述与工程安排，**不构成法律意见**。

## 3. `index.html` 的改动量（口径以本页为准）

- 可核事实：本目录的 `index.html` 共 797 字符（UTF-8、LF 换行），其与上游的差异是新增了一个
  `<script type="module" src="/dream-export-entry.js"></script>` 标签，位置紧跟在
  `<script type="module" src="/src/main.tsx"></script>` 之前；`src/` 未改。
- 因此本文档只说“**新增了一个 `<script>` 标签**”，**不拿行数当验收口径**。
- `external/civ-atlas/index.html` 是**已打过补丁的树**，所以它与本目录文件逐字节相同；
  这只能证明“补丁已应用”，**不能反推出上游原文件的行数**。
- 旧版本本文件写的“+4 行”与本次实测不一致；在没有未打补丁的上游原件做逐行对比前，**不声称具体改了 N 行**。

## 4. 重建

见 `docs/civ-atlas-install.md` 第 1.1 节：下载固定 commit 的 tar 快照（核对包 SHA-256）→ 解包到
`external/civ-atlas` → 按上表把全部文件覆盖/放入对应位置 → 用上表 SHA-256 逐项核对。
`external/` 整个目录被根 `.gitignore` 忽略，这是有意为之（见 `.gitignore` 里的注释）。

## 5. 原生地图宿主（vite.dream.config.ts 的两份）

| 位置 | 用途 |
|---|---|
| `external/civ-atlas/vite.dream.config.ts` | 正式一份：在**上游树里**执行 `npx vite build --config vite.dream.config.ts`，`entry`/`outDir` 相对上游树 |
| `vite.dream.config.ts`（仓库根） | 等价副本：`root` 指向 `external/civ-atlas`，**不用 cd** 就能从仓库根构建 |

两份的配置本体（插件、`define: process.env.NODE_ENV`、`lib.formats`、`target`）必须一致，
否则两条构建路径会产出不同的包。根目录那份用 `createRequire` 从上游 `package.json` 解析
`@vitejs/plugin-react`——仓库根没有 `node_modules`，也不该为这件事引入一份。

构建产物：`external/civ-atlas/dist-dream/dream-host.js`（约 607 kB，`dream-host.css` 约 1.4 kB）。
用法与验收命令见 [`../civ-atlas-host.md`](../civ-atlas-host.md)。

## 2026-10-30 DreamTerra ? civ ????

????????/?????/??????????????????????????????????????????????? `DreamTerra/static/civ-atlas.css` ???????????????????? `DreamTerra/README.md`?

?? host.tsx SHA-256?`35cb9520afada314ff48edf3c434f7808d43fca7925acf04c59a592c830d1568`?
