/* 主入口 → 原生 civ-atlas 地图的**唯一挂载点**，按模式严格分离作者与玩家。
 *
 * 这个文件是本工程自己写的静态集成（MIT），**不 import 上游任何模块**：它只按 URL
 * 动态加载 AGPL 构建产物 `/native-map/dream-host.js`。
 *
 * 模式来源与边界：
 *   app.js 在确定“有没有旅程”后调 `setNativeMode('author'|'player')`，并派发
 *   `td-native-mode` 事件（window.__tdNativeMode 是同步可读的副本）。本文件只认这个事件，
 *   **不自己 bootstrap、不轮询**。
 *
 *   author  = 空态，作者在准备世界 → 挂载宿主（mode:'author'，请求 native-worlds）
 *   player  = 已在某段旅程里 → **完全卸下作者宿主**，只显示独立的
 *             /api/sessions/{id}/play-map 服务端掩膜底图与玩家位置；不请求作者全图。
 *             这是“这幅图属于谁”的契约，不是权限开关：token 不是看全图的理由。
 *
 * 失败一律在位报真实原因 + 重试按钮。玩家图仅从服务端掩膜接口读取，不回退到作者全图。
 */
(function () {
  'use strict';

  const host = document.getElementById('native-map-host');
  const playerHost = document.getElementById('player-map-host');
  if (!host) return;

  const BASE = '/native-map/';
  let root = null;            // mountDreamHost 返回的 React root
  let module = null;          // 已加载的宿主模块（只加载一次）
  let mode = null;            // 当前已挂载的模式
  let applySerial = 0;     // 同模式重试也使先前的异步加载失效
  ensureCss('/dreamterra/civ-atlas.css');

  /** 在位报错，并给一个真的能用的重试按钮（重试会重跑当前模式的挂载）。 */
  function fail(title, detail) {
    host.replaceChildren();
    const box = document.createElement('div');
    box.className = 'native-map-note';
    box.dataset.state = 'failed';
    box.setAttribute('role', 'alert');
    const head = document.createElement('p');
    head.className = 'native-map-error-title';
    head.textContent = title;
    const body = document.createElement('p');
    body.textContent = detail;
    box.append(head, body);
    const again = document.createElement('button');
    again.type = 'button';
    again.textContent = '重新加载原生地图';
    again.onclick = () => {
      again.disabled = true;
      again.textContent = '重新加载中…';
      void apply(window.__tdNativeMode || mode || 'author', true);
    };
    box.append(again);
    host.append(box);
  }

  function note(text, state) {
    host.replaceChildren();
    const box = document.createElement('div');
    box.className = 'native-map-note';
    box.dataset.state = state || 'loading';
    box.setAttribute('role', 'status');
    box.textContent = text;
    host.append(box);
  }

  /** 动态加载一个 CSS；已存在就不重复插。 */
  function ensureCss(href) {
    if (document.querySelector('link[data-native-map="' + href + '"]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.dataset.nativeMap = href;
    document.head.append(link);
  }

  /** 卸下宿主：必须 unmount，不能只清 DOM（否则 React 还活着、还会请求）。 */
  function unmount() {
    if (root) {
      try { root.unmount(); } catch (error) { /* 已卸载 */ }
      root = null;
    }
    mode = null;
    host.replaceChildren();
    window.__nativeMapRoot = null;
  }

  /** 加载一次构建产物（token 已就绪）。 */
  async function load() {
    if (module) return module;
    try {
      const probe = await fetch(BASE + 'dream-host.js', { method: 'HEAD' });
      if (!probe.ok) throw new Error('HTTP ' + probe.status);
    } catch (error) {
      throw new Error('原生地图尚未构建：' + BASE + 'dream-host.js 不可用（' + error.message
        + '）。构建命令：在仓库根执行 npx --prefix external/civ-atlas vite build '
        + '--config vite.dream.config.ts（见 docs/civ-atlas-host.md）。');
    }
    ensureCss(BASE + 'dream-host.css');
    let loaded;
    try {
      loaded = await import(BASE + 'dream-host.js');
    } catch (error) {
      throw new Error('原生地图加载失败：' + (error && error.message ? error.message : String(error)));
    }
    if (!loaded || typeof loaded.mountDreamHost !== 'function') {
      throw new Error('构建产物不对：模块里没有 mountDreamHost 导出。');
    }
    module = loaded;
    return module;
  }

  /** 按模式落地：player 一律不挂宿主。 */
  async function apply(next, retry = false) {
    if (next === mode && !retry) return;
    const serial = ++applySerial;
    unmount();
    if (playerHost) playerHost.hidden = next === 'author';
    host.hidden = next !== 'author';

    if (next !== 'author') {
      // 玩家模式仅显示服务端已遮罩的旅程地图；绝不挂作者宿主或请求作者原件。
      mode = next;
      if (window.PlayUI && typeof window.PlayUI.refreshMap === 'function') void window.PlayUI.refreshMap();
      return;
    }

    mode = next;
    note('正在加载原生地图…');
    let loaded;
    try {
      loaded = await load();
    } catch (error) {
      if (serial === applySerial) fail('原生地图不可用', error.message || String(error));
      return;
    }
    // 加载期间模式又变了，或同模式重新加载了：迟到的结果不能覆盖新宿主。
    if (serial !== applySerial || mode !== 'author') return;
    try {
      host.replaceChildren();
      const mount = document.createElement('div');
      mount.className = 'native-map-mount';
      host.append(mount);
      root = loaded.mountDreamHost(mount, { mode: 'author' });
      window.__nativeMapRoot = root;
    } catch (error) {
      fail('原生地图挂载失败', (error && error.message ? error.message : String(error)));
    }
  }

  // 模式只从这个显式事件来（app.js: setNativeMode）。事件到之前先不挂任何东西。
  window.addEventListener('td-native-mode', (event) => {
    const next = event && event.detail && event.detail.mode;
    if (next) void apply(next);
  });

  // 事件可能在本文件执行前就已派发过（script 顺序无关）：那就在启动时补一次。
  if (window.__tdNativeMode) {
    void apply(window.__tdNativeMode);
  } else {
    note('正在等应用状态…');
  }
})();
