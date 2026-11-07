// 渲染元素图标样张：app/static/item-art/element-icons.json → artifacts/game-icons/element-icons-sheet.png
// 用法：node tools/element_icons_sheet.cjs （复用 external/civ-atlas 的 playwright 与本机 Edge）
const {chromium} = require(require.resolve('playwright', {paths: [require('path').resolve('external/civ-atlas')]}));
const fs = require('node:fs');
const path = require('node:path');

const dir = 'app/static/item-art';
const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'element-icons.json'), 'utf8'));
const sprites = Object.fromEntries(Object.entries(manifest.sprites)
  .map(([key, file]) => [key, fs.readFileSync(path.join(dir, file), 'utf8')]));
const outDir = 'artifacts/game-icons';
fs.mkdirSync(outDir, {recursive: true});

function elementName(group, id) {
  for (const base of ['docs/element-catalog', 'docs/human-encyclopedia']) {
    // 分区名可能用下划线（professions_fantasy），文件名用连字符（professions-fantasy.json）。
    const file = [group, group.replace(/_/g, '-')].map(stem => path.join(base, stem + '.json')).find(f => fs.existsSync(f));
    if (file) {
      const doc = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
      const hit = (doc.elements || []).find(e => e.id === id);
      if (hit) return hit.name;
    }
  }
  return '（未找到）';
}

const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
// 每个 sprite 单独内联在自己的 <svg> 里；同名 symbol（如 res-*）在不同 sprite 间重复，按 sprite 前缀改名避免串用。
const inline = Object.entries(sprites).map(([key, text]) =>
  text.replace(/id="([^"]+)"/g, `id="${key}--$1"`).replace(/url\(#([^)]+)\)/g, `url(#${key}--$1)`)).join('');
const use = (sprite, symbol, px) =>
  `<svg width="${px}" height="${px}"><use href="#${sprite}--${symbol}" width="${px}" height="${px}"/></svg>`;

const groups = {};
for (const [key, item] of Object.entries(manifest.entries)) {
  const [group, id] = key.split('/');
  (groups[group] = groups[group] || []).push({id, ...item, name: elementName(group, id)});
}
const titles = {polities: '政体', 'races-supplement': '补充种族', western: '改判为种族', 'steam-tech': '蒸汽与近现代技术', shops: '店铺招牌',
  professions: '职业（现实与历史）', professions_fantasy: '职业（奇幻）'};
const sections = Object.entries(groups).map(([group, items]) => `
  <h2>${esc(titles[group] || group)}<small>${esc(group)}</small></h2>
  <div class="grid">${items.map(item => `
    <div class="cell">
      <div class="row">${use(item.sprite, item.symbol, 56)}<span class="small">${use(item.sprite, item.symbol, 24)}</span></div>
      <div class="label">${esc(item.name)}</div>
      <div class="key">${esc(item.symbol)}${item.reuse ? ' · 复用' : ''}</div>
    </div>`).join('')}</div>`).join('');

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#efe3c4;font-family:"Songti SC","SimSun","Noto Serif SC",serif;color:#3b2a1e}
  .sheet{margin:18px;padding:22px 34px 18px;border:2px solid #3b2a1e;outline:1px solid #3b2a1e;outline-offset:-8px;
    background:radial-gradient(ellipse at 30% 20%,#f4ead0,#e9dbb8)}
  h1{text-align:center;font-weight:normal;font-size:32px;letter-spacing:4px;margin:6px 0 2px}
  .lead{text-align:center;font-size:12px;color:#6b5a48;margin-bottom:8px}
  h2{font-weight:normal;font-size:21px;border-bottom:1px solid #a3472f;padding-bottom:4px;margin:20px 0 12px}
  h2 small{font-size:12px;color:#6b5a48;margin-left:14px;font-family:Consolas,monospace}
  .grid{display:grid;grid-template-columns:repeat(7,1fr);gap:14px 10px}
  .row{display:flex;align-items:flex-end;gap:8px}
  .label{font-size:14px;margin-top:4px}
  .key{font-family:Consolas,monospace;font-size:10px;color:#7d6c58}
  .foot{text-align:center;font-size:12px;color:#6b5a48;margin-top:20px}
</style></head><body><div style="position:absolute;width:0;height:0;overflow:hidden">${inline}</div><div class="sheet">
  <h1>织梦 · 元素图标 · 样张</h1>
  <div class="lead">新画 sprite：app/static/item-art/element-icons.svg · 映射 element-icons.json · 标「复用」的取自 map-art 地图图示 · 大图 56 px，旁为 24 px 实尺</div>
  ${sections}
  <div class="foot">织梦 · 西式手绘 · 本工程原创图示</div>
</div></body></html>`;

(async () => {
  const browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1300, height: 900}, deviceScaleFactor: 1});
    await page.setContent(html, {waitUntil: 'load'});
    const missing = await page.evaluate(() => [...document.querySelectorAll('use')]
      .map(node => node.getAttribute('href')).filter(href => !document.getElementById(href.slice(1))));
    if (missing.length) throw new Error('样张引用了不存在的 symbol：' + missing.join(', '));
    const out = path.join(outDir, 'element-icons-sheet.png');
    await page.locator('.sheet').screenshot({path: out});
    console.log('样张已写出：' + out);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
