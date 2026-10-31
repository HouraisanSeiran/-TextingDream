// 从**仓库根**构建原生宿主：不先 cd 进上游树也能一条命令跑。
//
//   npx --prefix external/civ-atlas vite build --config vite.dream.config.ts
//
// 配置本体与 `external/civ-atlas/vite.dream.config.ts` 必须一致（插件、define、lib、target）：
// 两份分别服务「根目录一条命令」和「cd 进上游树」，任何一项不同都会产出不同的包。
// 唯一差异是路径基准：这里 `root` 指到上游树，entry / outDir 相对这个 root 解析。
//
// 为什么插件用 createRequire 而不是 `import react from '@vitejs/plugin-react'`：
// 仓库根没有 `node_modules`（根 `.gitignore` 也不该为这件事引入一份），
// 插件只装在上游树里。createRequire 从上游的 `package.json` 出发解析，才能拿到它。
//
// 前提：`external/civ-atlas` 已按 `docs/civ-atlas-install.md` 重建（整目录被根 `.gitignore` 忽略），
// 且 `pnpm install --ignore-scripts` 已跑过。上游源码 AGPL-3.0-only，产物同为 AGPL-3.0-only。
import { createRequire } from 'node:module';
import path from 'node:path';
import { defineConfig } from 'vite';

const UPSTREAM = 'external/civ-atlas';

// vite 加载 `.ts` 配置时这里是 CJS，所以 `__dirname` 可用（ESM 下不存在）。
const upstreamRequire = createRequire(
  path.join(__dirname, UPSTREAM, 'package.json'),
);
const react = upstreamRequire('@vitejs/plugin-react').default;

export default defineConfig({
  root: UPSTREAM,
  // 产物挂在 `/native-map/` 下（FastAPI 静态托管），与上游那份配置保持同口径。
  // 不写 base 的话 worker 里 `new URL('/assets/worker-….js', import.meta.url)`
  // 会被算成站点根的 `/assets/...`，那个路径没挂，worker 直接 404。
  base: '/native-map/',
  plugins: [react()],
  // Library mode does not apply Vite's usual `process.env.NODE_ENV` replacement, so React's
  // dev branch would be bundled and blow up on `process` in a plain browser. Replace the
  // exact expression (not a fake `process` global) — anything else touching `process`
  // should fail loudly rather than silently get a stub.
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
  build: {
    // 相对 root 解析，所以产物落在 external/civ-atlas/dist-dream
    outDir: 'dist-dream',
    emptyOutDir: true,
    // 一个普通 ES 模块，由作者/玩家页面自己 import；不是 IIFE，也不是全局变量。
    lib: {
      entry: 'src/dream/entry.tsx',
      formats: ['es'],
      fileName: () => 'dream-host.js',
    },
    rollupOptions: {
      // React 要打进来：产物会挂在 FastAPI 静态目录下，没有 node_modules 可用。
      external: [],
      output: {
        assetFileNames: 'dream-host[extname]',
      },
    },
    target: 'es2022',
    sourcemap: false,
  },
});
