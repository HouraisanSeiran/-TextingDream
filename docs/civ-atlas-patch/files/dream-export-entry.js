/**
 * 织梦导出入口（civ-atlas 侧的唯一改动，见 SOURCE-CHANGES.md）
 *
 * 上游页面本身没有「把原件下载成文件」的入口，作者得开 F12 到 Console 粘脚本。
 * 这里在右下角放一个小按钮，替作者跑同一段只读脚本：仍然只读 IndexedDB 的
 * results/heads，不联网、不写库、不碰 localStorage / API Key。
 *
 * 本文件是**本工程原创代码**，不 import 上游模块，因此不构成对上游代码的衍生；
 * 但它与上游同仓分发，整仓按 AGPL-3.0-only 处理（上游 LICENSE 原文保留）。
 *
 * 导出逻辑本身来自 public/dream-export-tool.js——那就是 tools/civ_atlas_export.js 的
 * 同内容副本（SHA-256 相同），由本工程的检查处保持同步，避免两处各改一份。
 */
let loading = null;

/** 把导出器以 <script> 加载进来（它自己会把 window.__civAtlasExport 挂上） */
function loadTool() {
  if (window.__civAtlasExport) return Promise.resolve(true);
  if (loading) return loading;
  loading = new Promise((resolve) => {
    const s = document.createElement('script');
    s.src = new URL('dream-export-tool.js', document.baseURI).href;
    s.onload = () => resolve(Boolean(window.__civAtlasExport));
    s.onerror = () => resolve(false);
    document.head.append(s);
  });
  return loading;
}
const STYLE = `
#dream-export{position:fixed;right:14px;bottom:14px;z-index:2147483000;font:12px/1.4 system-ui,'Microsoft YaHei',sans-serif}
#dream-export > button{border:1px solid #6b7a86;background:#1d2b34;color:#e8eef2;border-radius:10px;
  padding:8px 12px;cursor:pointer;box-shadow:0 4px 16px #0006}
#dream-export > button:hover{background:#26404d}
#dream-export.open > button{border-color:#c9d6a7}
#dream-export .dx-panel{position:absolute;right:0;bottom:42px;width:min(340px,calc(100vw - 28px));
  background:#17222b;color:#e8eef2;border:1px solid #3b4b57;border-radius:12px;padding:12px;
  box-shadow:0 8px 28px #0008;display:none}
#dream-export.open .dx-panel{display:block}
#dream-export .dx-panel h4{margin:0 0 6px;font-size:13px;font-weight:600}
#dream-export .dx-panel p{margin:0 0 8px;color:#a9bcc8;font-size:11.5px;line-height:1.6}
#dream-export .dx-row{display:flex;gap:6px;flex-wrap:wrap}
#dream-export .dx-row button{flex:1 1 auto;border:1px solid #3b4b57;background:#22303a;color:#e8eef2;
  border-radius:8px;padding:6px 10px;cursor:pointer;font-size:12px}
#dream-export .dx-row button:hover{background:#2c3d49}
#dream-export .dx-row button:disabled{opacity:.5;cursor:default}
#dream-export .dx-log{margin:8px 0 0;max-height:150px;overflow:auto;font:11px/1.5 Consolas,monospace;
  color:#a9bcc8;white-space:pre-wrap;word-break:break-all}
`;

function ensureStyle() {
  if (document.getElementById('dream-export-style')) return;
  const tag = document.createElement('style');
  tag.id = 'dream-export-style';
  tag.textContent = STYLE;
  document.head.append(tag);
}

function log(box, line) {
  const p = document.createElement('div');
  p.textContent = line;
  box.append(p);
  box.scrollTop = box.scrollHeight;
}

async function mount() {
  ensureStyle();
  const root = document.createElement('div');
  root.id = 'dream-export';
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = '导出给织梦';
  btn.title = '把这个世界从浏览器里原样导出成 .civsnap 文件，交给织梦的地图工具';
  const panel = document.createElement('div');
  panel.className = 'dx-panel';
  panel.innerHTML = '<h4>导出给织梦</h4>'
    + '<p>选择一个世界里存着的原件，原样打包下载。只读浏览器的 IndexedDB，不联网、不写库，'
    + '也不读 API Key。</p>'
    + '<div class="dx-row"><button type="button" data-dx="list">看有哪些</button>'
    + '<button type="button" data-dx="export" disabled>导出第一个</button></div>'
    + '<div class="dx-log"></div>';
  root.append(panel, btn);
  document.body.append(root);
  const box = panel.querySelector('.dx-log');
  const exportBtn = panel.querySelector('[data-dx="export"]');

  btn.onclick = () => root.classList.toggle('open');

  let count = 0;
  panel.querySelector('[data-dx="list"]').onclick = async () => {
    box.replaceChildren();
    log(box, '正在读原件清单…');
    if (!(await loadTool())) {
      log(box, '导出器没能加载（检查 public/dream-export-tool.js 在不在）。');
      return;
    }
    try {
      const heads = await window.__civAtlasExport.list();
      count = heads.length;
      exportBtn.disabled = !count;
      if (!count) {
        log(box, '这台浏览器里还没有原件：先在 civ-atlas 里生成一个世界。');
      } else {
        heads.slice(0, 6).forEach((h, i) => log(box, `#${i} 世界 ${h.id} · g${h.generator} · ${h.at}`));
        log(box, `共 ${count} 个；点「导出第一个」下载 #0。`);
      }
    } catch (error) {
      log(box, '读不出来：' + (error && error.message ? error.message : String(error)));
    }
  };

  exportBtn.onclick = async () => {
    exportBtn.disabled = true;
    log(box, '正在打包…');
    try {
      if (!(await loadTool())) throw new Error('导出器没能加载');
      const r = await window.__civAtlasExport.export(0);
      log(box, `已下载 ${r.name}（${r.parts.join('、')}）`);
    } catch (error) {
      log(box, '导出失败：' + (error && error.message ? error.message : String(error)));
    } finally {
      exportBtn.disabled = false;
    }
  };
}

mount();
