// 独立构建入口：把宿主打成 `dream-host.js` 模块，由 FastAPI 静态目录供应。
//
// 上游源码 AGPL-3.0-only，此产物因此同为 AGPL-3.0-only。
import { createRoot } from 'react-dom/client';
import { DreamMapHost } from './host';
import type { BridgeMode } from './bridge';
import { ErrorBoundary } from '../ui/ErrorBoundary';

export { DreamMapHost };
export type { BridgeMode };

/**
 * 把宿主挂到一个元素上。页只用一句：
 *
 * ```js
 * import { mountDreamHost } from '/static/dream/dream-host.js';
 * mountDreamHost(document.getElementById('dream-map'), { mode: 'author' });
 * ```
 *
 * `mode` 由页自己决定（作者页 / 玩家页）；宿主不会自己探测。
 */
export function mountDreamHost(element: Element | null,
                                options: { mode?: BridgeMode } = {}) {
  if (!element) throw new Error('挂载宿主需要目标元素');
  const root = createRoot(element);
  root.render(<ErrorBoundary><DreamMapHost mode={options.mode ?? 'author'} /></ErrorBoundary>);
  return root;
}
