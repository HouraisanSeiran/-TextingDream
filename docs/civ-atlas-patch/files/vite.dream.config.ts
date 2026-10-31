// 织梦原生宿主的**独立**构建：产出 `dream-host.js`，不动现有生产构建。
//
// 为什么单独一份：上游的 `vite.config.ts` 带着 banner、备案号、加载屏、假 AI 服务、
// mediabunny 分块等一整套官网构建行为。宿主只需要把 React + 我们的 host/bridge 打成
// 一个能挂到 FastAPI 的模块，不应该影响也不应该被那个构建影响。
//
// 许可：上游源码 AGPL-3.0-only，产物因此同样是 AGPL-3.0-only；分发时保留上游 LICENSE。
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // 产物不是放在站点根，而是挂在 `/native-map/` 下（FastAPI 静态托管）。
  // 不写 base 的话，worker 里 `new URL('/assets/worker-….js', import.meta.url)` 会算成
  // `/assets/...`——那个路径没挂，worker 直接 404，表现就是“生成线程报错”且没有详情。
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
