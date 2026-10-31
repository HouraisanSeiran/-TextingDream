// 快速探针：只验证“宿主能不能真的在浏览器里把世界生成出来”。
//
// 主入口 E2E 跑得久（要等完整生成），定位问题时要快——这个脚本只做一件事：
// 打开 `/`，点「生成并登记」，把 worker 加载结果、控制台报错、阶段进度全打出来。
//
// 用法： node tools/dream_worker_probe.mjs <baseUrl> [cells] [seconds]
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const UPSTREAM = join(HERE, '..', 'external', 'civ-atlas');
const { chromium } = createRequire(join(UPSTREAM, 'package.json'))('playwright');
const read = (p) => { try { return readFileSync(p); } catch { return null; } };
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const BASE = (process.argv[2] || '').replace(/\/$/, '');
const CELLS = Number(process.argv[3] || 6000);
const SECONDS = Number(process.argv[4] || 120);
if (!BASE) { console.error('用法：dream_worker_probe.mjs <baseUrl> [cells] [seconds]'); process.exit(2); }

const t0 = Date.now();
const log = (t) => process.stderr.write(`[+${((Date.now() - t0) / 1000).toFixed(1)}s] ${t}\n`);

const browser = await chromium.launch(read(EDGE) ? { executablePath: EDGE } : {});
const out = { base: BASE, cells: CELLS, workers: [], failed: [], console: [], steps: [], states: [] };
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('worker', (w) => { out.workers.push(w.url()); log('worker: ' + w.url()); });
  page.on('requestfailed', (r) => {
    out.failed.push({ url: r.url().slice(0, 160), why: r.failure() && r.failure().errorText });
    log('REQFAIL ' + r.url().slice(0, 160) + ' ' + (r.failure() || {}).errorText);
  });
  page.on('console', (m) => {
    const text = m.text().slice(0, 300);
    out.console.push(m.type() + ': ' + text);
    if (m.type() === 'error' || m.type() === 'warning') log(m.type() + ': ' + text);
  });
  page.on('pageerror', (e) => { out.console.push('pageerror: ' + String(e).slice(0, 300)); log('pageerror: ' + String(e).slice(0, 300)); });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => !!document.querySelector('#native-map-host .dream-host'),
    undefined, { timeout: 60000, polling: 250 });
  log('宿主机已挂上');

  await page.evaluate((cells) => {
    const form = document.querySelector('#native-map-host .dream-create');
    if (!form) return;
    const setVal = (node, v) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(node, String(v));
      node.dispatchEvent(new Event('input', { bubbles: true }));
    };
    for (const label of form.querySelectorAll('label')) {
      if ((label.textContent || '').trim() === '地块数') setVal(label.querySelector('input'), cells);
    }
  }, CELLS);
  await page.evaluate(() => {
    const form = document.querySelector('#native-map-host .dream-create');
    [...form.querySelectorAll('button')].find((b) => (b.textContent || '').includes('生成并登记')).click();
  });
  log('已点生成，观察 ' + SECONDS + 's');

  const deadline = Date.now() + SECONDS * 1000;
  while (Date.now() < deadline) {
    const state = await page.evaluate(() => {
      const bar = document.querySelector('#native-map-host .dream-host-bar');
      const c = document.querySelector('#native-map-host .dream-host-stage canvas');
      const alert = document.querySelector('#native-map-host [role=alert]');
      return {
        status: bar ? ((bar.querySelector('[role=status]') || {}).textContent || '').trim() : '',
        alert: alert ? (alert.textContent || '').trim().slice(0, 300) : '',
        canvas: c ? [c.width, c.height] : null,
      };
    });
    out.states.push(state);
    log(JSON.stringify(state));
    if (state.canvas && state.canvas[0] > 0) { out.ok = true; break; }
    if (state.alert) { out.ok = false; break; }
    await new Promise((r) => setTimeout(r, 4000));
  }
  const final = await page.evaluate(() => {
    const c = document.querySelector('#native-map-host .dream-host-stage canvas');
    if (!c || !c.width) return null;
    const ctx = c.getContext('2d');
    const data = ctx.getImageData(0, 0, c.width, c.height).data;
    const colors = new Set();
    const stride = Math.max(1, Math.floor(Math.min(c.width, c.height) / 100));
    for (let y = 0; y < c.height; y += stride) {
      for (let x = 0; x < c.width; x += stride) {
        const at = (y * c.width + x) * 4;
        colors.add((data[at] << 16) | (data[at + 1] << 8) | data[at + 2]);
      }
    }
    return { bitmap: [c.width, c.height], colors: colors.size };
  });
  out.final = final;
  if (final && final.colors > 30) out.ok = true;
} finally {
  await browser.close();
}
out.seconds = Math.round((Date.now() - t0) / 1000);
console.log(JSON.stringify(out));
process.exit(out.ok ? 0 : 1);
