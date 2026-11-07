// 渲染物品属性图示样张：app/static/item-art/game-icons.svg → artifacts/game-icons/game-icons-sheet.png
// 用法：node tools/game_icons_sheet.cjs   （复用 external/civ-atlas 的 playwright 与本机 Edge，与其他 UI 探针一致）
const {chromium} = require(require.resolve('playwright', {paths: [require('path').resolve('external/civ-atlas')]}));
const fs = require('node:fs');
const path = require('node:path');

const sprite = fs.readFileSync('app/static/item-art/game-icons.svg', 'utf8');
const manifest = JSON.parse(fs.readFileSync('app/static/item-art/game-icons.json', 'utf8'));
const outDir = 'artifacts/game-icons';
fs.mkdirSync(outDir, {recursive: true});

const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const use = (id, px) => `<svg width="${px}" height="${px}" viewBox="0 0 24 24"><use href="#${id}"/></svg>`;

function section(title, sub, family) {
  const cells = Object.entries(manifest[family]).map(([key, item]) => `
    <div class="cell">
      <div class="row">${use(item.symbol, 56)}<span class="small">${use(item.symbol, 24)}${use(item.symbol, 16)}</span></div>
      <div class="label">${esc(item.label)}</div>
      <div class="key">${esc(family)}:${esc(key)}</div>
      ${item.hint ? `<div class="hint">${esc(item.hint)}</div>` : ''}
    </div>`).join('');
  return `<h2>${esc(title)}<small>${esc(sub)}</small></h2><div class="grid">${cells}</div>`;
}

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#efe3c4;font-family:"Songti SC","SimSun","Noto Serif SC",serif;color:#3b2a1e}
  .sheet{margin:18px;padding:22px 34px 18px;border:2px solid #3b2a1e;outline:1px solid #3b2a1e;outline-offset:-8px;
    background:radial-gradient(ellipse at 30% 20%,#f4ead0,#e9dbb8)}
  h1{text-align:center;font-weight:normal;font-size:34px;letter-spacing:4px;margin:6px 0 2px}
  .lead{text-align:center;font-size:12px;color:#6b5a48;margin-bottom:8px}
  h2{font-weight:normal;font-size:22px;border-bottom:1px solid #a3472f;padding-bottom:4px;margin:22px 0 12px}
  h2 small{font-size:12px;color:#6b5a48;margin-left:14px}
  .grid{display:grid;grid-template-columns:repeat(8,1fr);gap:14px 10px}
  .cell{padding:2px}
  .row{display:flex;align-items:flex-end;gap:8px}
  .small{display:flex;align-items:flex-end;gap:5px}
  .label{font-size:15px;margin-top:4px}
  .key{font-family:Consolas,monospace;font-size:10px;color:#7d6c58}
  .hint{font-size:11px;color:#6b5a48}
  .foot{text-align:center;font-size:12px;color:#6b5a48;margin-top:20px}
</style></head><body>${sprite}<div class="sheet">
  <h1>织梦 · 物品属性图示 · 样张</h1>
  <div class="lead">sprite: app/static/item-art/game-icons.svg · 映射 game-icons.json · 大图 56 px，旁为 24 / 16 px 实尺小样 · 产地底色取 civ-atlas 群落水彩色</div>
  ${section('货币 · 价格档', '12 便士 = 1 先令，20 先令 = 1 镑；游戏行情，不是历史物价', 'price')}
  ${section('产地', '群落 14 + 地形 4 + 生产用地 6，与 civ-atlas biomes.ts 对齐', 'terrain')}
  ${section('季节', '当季上市或采收；耐储存者为全年', 'season')}
  <div class="foot">织梦 · 西式手绘 · 本工程原创图示</div>
</div></body></html>`;

(async () => {
  const browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1500, height: 1000}, deviceScaleFactor: 1});
    await page.setContent(html, {waitUntil: 'load'});
    const missing = await page.evaluate(() => [...document.querySelectorAll('use')]
      .map(node => node.getAttribute('href')).filter(href => !document.querySelector(href)));
    if (missing.length) throw new Error('样张引用了不存在的 symbol：' + missing.join(', '));
    const out = path.join(outDir, 'game-icons-sheet.png');
    await page.locator('.sheet').screenshot({path: out});
    fs.writeFileSync(path.join(outDir, 'game-icons-sheet.html'), html);
    console.log('样张已写出：' + out);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
