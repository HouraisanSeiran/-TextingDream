// 织梦宿主：可拖动的独立配置窗口（本工程写，随 src/dream 一起按 AGPL-3.0-only 分发）。
// 只负责「放在哪、怎么拖、怎么关」，里面放什么由调用方决定；不碰任何生成逻辑。
import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

export function FloatingWindow({ title, subtitle, onClose, closeDisabled, children }: {
  title: string; subtitle?: string; onClose: () => void; closeDisabled?: boolean; children: React.ReactNode;
}) {
  const [pos, setPos] = useState(() => ({
    x: Math.max(16, Math.round(window.innerWidth / 2 - 220)),
    y: Math.max(16, Math.round(window.innerHeight * 0.14)),
  }));
  const drag = useRef<{ dx: number; dy: number } | null>(null);
  const box = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && !closeDisabled) onClose(); };
    window.addEventListener('keydown', onKey);
    box.current?.querySelector<HTMLElement>('input, button')?.focus({ preventScroll: true });
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, closeDisabled]);

  const clamp = (x: number, y: number) => {
    const w = box.current?.offsetWidth ?? 440;
    return { x: Math.min(Math.max(8, x), window.innerWidth - Math.min(w, 120)), y: Math.min(Math.max(8, y), window.innerHeight - 48) };
  };

  return createPortal(
    <div ref={box} className="dream-window" role="dialog" aria-modal="false" aria-label={title}
         style={{ left: pos.x, top: pos.y }}>
      <div className="dream-window-bar"
           onPointerDown={(event) => {
             if ((event.target as Element).closest('button')) return;
             event.currentTarget.setPointerCapture(event.pointerId);
             drag.current = { dx: event.clientX - pos.x, dy: event.clientY - pos.y };
           }}
           onPointerMove={(event) => {
             const held = drag.current;
             if (held) setPos(clamp(event.clientX - held.dx, event.clientY - held.dy));
           }}
           onPointerUp={() => { drag.current = null; }}
           onPointerCancel={() => { drag.current = null; }}>
        <span className="dream-window-title">{title}{subtitle ? <small>{subtitle}</small> : null}</span>
        <button type="button" className="dream-window-close" aria-label={`关闭${title}`}
                disabled={closeDisabled} onClick={onClose}>×</button>
      </div>
      <div className="dream-window-body">{children}</div>
    </div>,
    document.body,
  );
}
