# civ-atlas 本体安装（external/civ-atlas）

本文件记录「把 civ-atlas 装进本仓并在本机跑起来」这件事的**事实**：从哪来、装了什么、
怎么启动、许可边界、以及哪些是已知缺口。凡本文没写「已实测」的，都不当作已验证。

## 1. 来源与固定版本

| 项 | 值 |
|---|---|
| 上游仓库 | <https://github.com/guaner-334/civ-atlas> |
| 固定 commit | `0939c5f1622a5e45cfc16f645ea3845993ab3985` |
| 获取方式 | 官方 `codeload` 源码包（`/tar.gz/<commit>`）。`git clone` 在本机网络不通，未使用任何第三方镜像 |
| 包大小 | `30 256 136` 字节 |
| 包 SHA-256 | `8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC` |
| 解包审计 | `tar -tzf` exit 0；1935 个条目；**无绝对路径、无 `..` 穿越、无 symlink 条目** |
| 落地目录 | `external/civ-atlas`（1895 个文件，`src/` 610 个） |
| 许可证 | `LICENSE` = GNU **AGPL-3.0** 全文（34 523 B）；`package.json` 为 `"license": "AGPL-3.0-only"`、`"version": "1.3.0"` |

## 1.1 重建一份逐字相同的树（不依赖 `external/` 入库）

`external/` 在根 `.gitignore` 里**整个忽略**（上游 1895 个文件 + 节点依赖，不该把根仓变成半个 vendor 仓）。
重建靠三样东西，都在仓里：

1. 官方 tar 快照：`https://codeload.github.com/guaner-334/civ-atlas/tar.gz/0939c5f1622a5e45cfc16f645ea3845993ab3985`
   （`30 256 136` 字节，SHA-256 `8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC`）
2. 本工程改动：`docs/civ-atlas-patch/files/` 保存按原目录排列的完整补丁，包括导出入口、原生地图宿主、共享错误边界、App URL 解析拆分及测试。
3. 安装与启动命令：本文第 3 节

```powershell
$c='0939c5f1622a5e45cfc16f645ea3845993ab3985'
Invoke-WebRequest "https://codeload.github.com/guaner-334/civ-atlas/tar.gz/$c" -OutFile civ-atlas.tar.gz
(Get-FileHash civ-atlas.tar.gz -Algorithm SHA256).Hash    # 必须等于上面那个
New-Item -ItemType Directory external\_x | Out-Null
tar.exe -xzf civ-atlas.tar.gz -C external\_x
Move-Item "external\_x\civ-atlas-$c" external\civ-atlas
# 按相对路径应用全部补丁（也供一键安装器使用）
python -c "import sys; sys.path.insert(0, 'tools'); from launcher.core import apply_patch; apply_patch()"
# 装依赖（见第 3 节）后构建宿主
cd external/civ-atlas; npx vite build --config vite.dream.config.ts   # → dist-dream/dream-host.js
```

核对是否逐字相同：补丁文件应与安装后对应路径逐字节相同。历史 README 中的哈希只描述当时版本。
2026-10-30 前端改进还修改了 `src/main.tsx`、`src/ui/App.tsx`，新增 `src/ui/appLocation.ts`、`src/ui/ErrorBoundary.tsx` 和对应 CSS Module；不能再用“src/dream 以外完全未改”作为判断。
（`tests/test_civ_native_contract.py` 的 `test_dream_sources_are_mirrored_in_the_patch_directory`
每次跑都会核一次「镜像与源码逐字节相同」。）

因为是用 tar 快照而不是 `git clone`，`external/civ-atlas` **不是 git 工作树**（没有 `.git`），
所以无法用 `git diff` 追踪我们对上游的改动。因此上游侧的改动一律记在
`external/civ-atlas/SOURCE-CHANGES.md`（如有），并在本文件列出改动文件清单。

## 2. 环境（实测）

| 项 | 值 |
|---|---|
| Node | `v22.23.2`（上游 `engines.node: ">=22"`，满足） |
| 全局 pnpm 包 | `C:\Users\Huang\AppData\Roaming\npm\node_modules\pnpm`，其 `package.json` 为 **11.22.0** |
| **实际执行安装的 pnpm** | 自报 **11.24.0**（与上游 `packageManager: pnpm@11.24.0` 一致）；`LOCALAPPDATA\node\corepack` 不存在，来源**未能证明**，如实记录为「未知途径」 |
| pnpm store | `D:\.pnpm-store\v11`（约 149 MB，pnpm 正常的内容寻址 store） |

**没有**做的：全局 `npm i -g`、corepack 下载新管理器、修改系统 Node、放开依赖安装脚本。

## 3. 安装与启动（可复现命令）

```powershell
cd external\civ-atlas
$env:CI='true'
pnpm install --ignore-scripts --frozen-lockfile --config.manage-package-manager-versions=false
```

- `--ignore-scripts`：**没有**执行任何依赖的 lifecycle 脚本（上游 scripts 只有 vite/tsc/vitest/tsx，
  且 `pnpm-workspace.yaml` 只允许 `esbuild` 一个包的 build）。
- `--frozen-lockfile`：锁文件 `lockfileVersion 9.0` 未被改写；安装末尾上游工具报
  `✓ Lockfile passes supply-chain policies (197 entries)`。
- 结果：125 个包；运行时依赖 `d3-delaunay 6.0.4`、`mediabunny 1.61.3`、`react 18.3.1`、
  `react-dom 18.3.1`、`simplex-noise 4.0.3`、`uqr 0.1.3`；开发依赖 `vite 5.4.21`、
  `typescript 5.6.3`、`vitest 2.1.9`、`tsx 4.23.15`、`playwright 1.63.0`、`pngjs 7.0.0`。

启动（**不经 pnpm 分派**，直接用本地已装的 vite，绑定回环地址）：

```powershell
cd external\civ-atlas
node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5188 --strictPort
```

打开 <http://127.0.0.1:5188/>。

### 3.1 拿到 .civsnap 的正确顺序（很容易踩坑）

页面上「生成完地图」不等于原件已经存进浏览器：

1. 新建世界 → 第 1 步「下一步」→ 第 2 步「开始」，等生成结束（几十秒）；
2. **必须点左下角「保存地图」**，把它存进「我的世界」。
   草稿状态下的世界**不写原件**，此时去导出会看到「没有原件」；
3. 想拿完整气候/biome，还要让这个世界有历史：在「我的世界」里对该地图点「打造文明」
   → 调推演年数（300 年就够）→「开始推演」→ 确认框点「开始」。
   推演完成后，上游才把 `map`/`eras`/`civ` 三块原件写进 IndexedDB；
4. 点右下角「导出给织梦」→「看有哪些」→「导出第一个」，得到 `civ-atlas-<id>-g<gen>.civsnap`；
5. 回到织梦（默认 <http://127.0.0.1:8898/> → 地图工具 → 导入文件）导入它。

> 只做第 2 步（只存地图、不推演）时，导出会失败告你「没有原件」——这是上游的设计，不是 bug。
> 织梦这边接受两种东西：`.civsnap`（有气候）与 16 位高度图 PNG（只有高程与海陆）。

`vite.config.ts` 里 `base: './'`、`server: { port: 5188, strictPort: true }`；**没有**写 `host`，
所以默认只监听本机回环。显式加 `--host 127.0.0.1` 是为了避免任何「监听 0.0.0.0」的可能。

停止：结束该 node 进程即可（`Ctrl+C`，或停掉对应的后台命令）。

### esbuild 说明
`--ignore-scripts` 使 esbuild 的 postinstall 未运行，于是 `node_modules/.bin/esbuild` 不存在；
但平台二进制已经随依赖装好：
`node_modules/.pnpm/@esbuild+win32-x64@0.21.5/node_modules/@esbuild/win32-x64/esbuild.exe`。
vite 直接 require `@esbuild/win32-x64`，不读 `.bin`，所以**不需要**放开任何安装脚本。

## 4. 许可边界（只引用上游原文，不下法律结论）

- `README.md:200`：「代码以 GNU AGPL-3.0（仅第 3 版）发布…**将修改后的版本作为网络服务提供给他人使用时，
  也必须以同样的协议公开修改后的完整源代码**」。
- `README.md:202`：「用这个工具做出来的世界…都归你所有…**AGPL-3.0 只约束代码本身，不约束用它生成的地图和文字**」。
- `README.md:204`：第三方依赖 MIT / ISC / Unlicense；`mediabunny` 为 MPL-2.0（未修改）；字体 SIL OFL 1.1；
  `public/portraits` 为 CC0 1.0。

本仓的处置：

1. **上游源码整份保留**在 `external/civ-atlas`，未裁剪、未改许可、随附 `LICENSE` 原文。
   它与本仓 `app/`（Python 服务）**不互相 import**，通过**文件**交换数据。
2. 本仓自己的代码（`app/`、`app/static/`、`tools/civ_atlas_export.js`）是独立实现：
   只读上游**导出的数据**，不复制、不 vendor、不链接上游源码。**这不是法律保证，只是工程隔离**。
3. 如果将来在 `external/civ-atlas` 里放了**修改上游**的代码（例如一个导出入口，或直接 import 上游模块的
   原生地图宿主 `src/dream/*`），那些改动按 AGPL-3.0-only 处理：保留完整源码、记录改动、可下载
   ——见 `SOURCE-CHANGES.md` 与 `THIRD_PARTY_NOTICES.md` §1.2。
4. **不擅自**把本仓整体改成 AGPL；本仓的许可完全不变。

## 5. 已知缺口（诚实清单）

- 上游 `resources`（州 × `RESOURCE_COUNT` 的 0–3 档）**尚未映射**到本仓的资源候选；
  它不是产量也不是库存，未接入前一律按「缺失」处理，不生成默认矿产。
- 面积是「球面均分近似」（`4πR²/地块数`），不是逐地块真实面积；UI 与记录都这样标注。
- 气温/降水只有在导入 `.civsnap` 时才有实测值；16 位高度图**没有**气候，只能作者填或拒收。
- 本机网络对 GitHub 很慢（单流约 200 KB/s），源码包下载耗时约 8 分钟，属实测吞吐而非估计。
