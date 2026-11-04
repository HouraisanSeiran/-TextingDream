/* 界面风格预设：同步切换样式表（放在 <head> 里、所有 <link> 之后加载，避免闪烁）。
 *   classic  = 原森林绿 atelier 风格（不加皮肤）
 *   retro    = 现代复古（retro.css）
 *   medieval = 中世纪魔幻（retro.css 结构 + medieval.css 变量与装饰）
 * 选择只存在浏览器 localStorage，不碰后端偏好（后端 theme 仍只认 dark/light）。 */
(function () {
  'use strict';
  var KEY = 'textiledream-ui-theme';
  var PRESETS = [
    { id: 'retro', name: '现代复古', sheets: ['retro'] },
    { id: 'medieval', name: '中世纪魔幻', sheets: ['retro', 'medieval'] },
    { id: 'classic', name: '森林手记（原版）', sheets: [] },
  ];
  function find(id) {
    for (var i = 0; i < PRESETS.length; i++) if (PRESETS[i].id === id) return PRESETS[i];
    return PRESETS[0];
  }
  function read() {
    // ?ui-theme=medieval 可临时指定（便于分享与截图），不写入 localStorage。
    var q = /[?&]ui-theme=([a-z]+)/.exec(location.search);
    if (q) return q[1];
    try { return localStorage.getItem(KEY) || 'retro'; } catch (e) { return 'retro'; }
  }
  function apply(id) {
    var preset = find(id);
    var links = document.querySelectorAll('link[data-theme-sheet]');
    for (var i = 0; i < links.length; i++) {
      links[i].disabled = preset.sheets.indexOf(links[i].getAttribute('data-theme-sheet')) < 0;
    }
    document.documentElement.setAttribute('data-ui-theme', preset.id);
    return preset.id;
  }
  function set(id) {
    var applied = apply(id);
    try { localStorage.setItem(KEY, applied); } catch (e) { /* 无痕模式忽略 */ }
    var pickers = document.querySelectorAll('.ui-theme-picker select');
    for (var i = 0; i < pickers.length; i++) pickers[i].value = applied;
  }
  apply(read());

  function picker() {
    var wrap = document.createElement('label');
    wrap.className = 'ui-theme-picker';
    var text = document.createElement('span');
    text.textContent = '风格';
    var select = document.createElement('select');
    select.setAttribute('aria-label', '界面风格预设');
    PRESETS.forEach(function (p) {
      var o = document.createElement('option');
      o.value = p.id; o.textContent = p.name;
      select.append(o);
    });
    select.value = document.documentElement.getAttribute('data-ui-theme') || 'retro';
    select.onchange = function () { set(select.value); };
    wrap.append(text, select);
    return wrap;
  }
  function mount() {
    var anchor = document.getElementById('api-toggle');
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(picker(), anchor);
    var back = document.getElementById('back-to-play');
    if (back && back.parentNode) back.parentNode.insertBefore(picker(), back);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
  window.TextileDreamTheme = { presets: PRESETS.map(function (p) { return p.id; }), set: set, get: read };
})();
