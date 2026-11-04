/* Offline fixtures based on docs/check-system-v2.md section 9. */
(function () {
  'use strict';
  const preview = { position: 'risky', effect: 'standard', chance: '中', dc: 12,
    factors: [{ label: '你拿着运货单', sign: '+' }, { label: '守卫已有戒心', sign: '-' }],
    auto: false, refused: null, blocked: false,
    push_options: [{ id: 'grease', label: '多塞两便士', cost_text: '2 便士' }],
    clock: { label: '说服行会', segments: 4, filled: 1 } };
  // Four-tier margin mode (d20_margin_v3): total = d20 + modifiers, margin = total - DC.
  const base = { rules_version: 'd20_margin_v3', tier_mode: 'margin_four', rolled: true, dice: [14], kept: 14, advantage: null,
    modifier: 3, dc: 12, total: 17, margin: 5, tier: 'success', tier_label: '成功',
    factors: [{ label: '你拿着运货单', sign: '+' }], push: { label: '多塞两便士' },
    noticed: '没人注意到', clock: { label: '说服行会', from: 1, to: 3, segments: 4 } };
  const cases = [
    ['大成功 · 优势', Object.assign({}, base, { dice: [7, 20], kept: 20, advantage: 'advantage', total: 23, margin: 11, tier: 'critical', tier_label: '大成功' })],
    ['成功', base],
    ['失败', Object.assign({}, base, { dice: [6], kept: 6, total: 9, margin: -3, tier: 'failure', tier_label: '失败', clock: { label: '守卫起疑', kind: 'danger', from: 1, to: 2, segments: 4 } })],
    ['大失败 · 劣势', Object.assign({}, base, { dice: [14, 1], kept: 1, advantage: 'disadvantage', total: 4, margin: -10, modifier: 3, dc: 14, tier: 'disaster', tier_label: '大失败', noticed: '似乎有人注意到了', clock: { label: '守卫起疑', kind: 'danger', from: 1, to: 3, segments: 4 } })],
    ['自然 20 · 单骰', Object.assign({}, base, { dice: [20], kept: 20, total: 23, margin: 11, tier: 'critical', tier_label: '大成功' })],
    ['自然 1 · 单骰（按差值，不自动大失败）', Object.assign({}, base, { dice: [1], kept: 1, modifier: 9, total: 10, margin: -2, tier: 'failure', tier_label: '失败' })],
    ['自动成功（执行状态）', { rules_version: 'd20_margin_v3', tier_mode: 'margin_four', status: 'auto', rolled: false, tier: 'success', tier_label: '成功', reason: '准备充分', factors: base.factors }],
    ['触及底线（拒绝执行）', { rules_version: 'd20_margin_v3', tier_mode: 'margin_four', status: 'refused', rolled: false, tier: null, dice: [], kept: null, refused: '这触到了他的底线' }]
  ];
  function drawPreview(push) {
    const host = document.getElementById('dice-demo-preview');
    host.replaceChildren();
    TDDice.preview(host, preview, { push, onPush: drawPreview });
  }
  function draw() {
    const host = document.getElementById('dice-demo-cases');
    host.replaceChildren();
    cases.forEach(([label, result]) => {
      const section = document.createElement('section');
      section.className = 'dice-demo-case';
      const heading = document.createElement('h2');
      heading.textContent = label;
      const body = document.createElement('div');
      section.append(heading, body);
      host.append(section);
      TDDice.roll(body, result);
    });
  }
  drawPreview('');
  TDDice.clocks(document.getElementById('dice-demo-clocks'), [
    { label: '说服行会', segments: 4, filled: 1, kind: 'progress' },
    { label: '守卫起疑', segments: 4, filled: 2, kind: 'danger' }
  ]);
  draw();
  document.getElementById('dice-demo-replay').addEventListener('click', draw);
})();
