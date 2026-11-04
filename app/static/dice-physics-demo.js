/* Local dice physics sandbox. Test only: writes no save, decides no story.
 * Approximate rigid body from TDDiceCore; the reading comes from the face that
 * actually points up after the die sleeps. No random numbers decide a value. */
(function () {
  'use strict';
  const C = window.TDDiceCore;
  const canvas = document.getElementById('lab-canvas');
  const ctx = canvas.getContext('2d');
  const readout = document.getElementById('lab-readout');
  const pauseBtn = document.getElementById('lab-pause');
  const staticBox = document.getElementById('lab-static');
  const BOUNDS = null; // Infinite ground plane; sandbox only.
  const fixedBox = document.getElementById('lab-fixed');
  const seedInput = document.getElementById('lab-seed');
  const MAX_THROW = 14;          // cap on release speed (world units / s)
  const MAX_SPIN = 30;
  const FLAT = 0.05;             // rad (~2.9°): flatter than this reads as a clean face
  let kind = 20;
  let die = null;
  let cam = null;
  let colors = null;
  let paused = false;
  let frame = 0;
  let last = 0;
  let acc = 0;
  let drag = null;
  let w = 0, h = 0, dpr = 1;
  const state = { throws: 0, lastReading: null, phase: 'idle', frames: 0, sleeps: 0 };
  window.__lab = state;

  function restAt(x, z) {
    const s = C.solidOf(kind);
    return C.body(kind, { pos: [x, s.inradius * s.size, z], R: C.restPose(kind, 1, 0.5) });
  }
  function reset() {
    cancel();
    // Drop any in-progress drag and its pointer capture, and leave pause mode,
    // so reset / kind switch mid-drag never leaves a held die behind.
    if (drag) {
      const id = drag.id;
      drag = null;
      if (canvas.hasPointerCapture(id)) canvas.releasePointerCapture(id);
    }
    canvas.classList.remove('is-holding');
    paused = false;
    pauseBtn.setAttribute('aria-pressed', 'false');
    pauseBtn.textContent = '暂停';
    die = restAt(0, 0.4);
    die.asleep = true;
    state.phase = 'idle';
    state.lastReading = null;
    state.initial = null;
    state.simulatedSeconds = 0;
    state.wallContacts = 0;
    state.resultText = null;
    readout.textContent = '无围墙地面：拖动投出，停稳后保留结果。';
    draw();
  }
  function resize() {
    const box = canvas.parentElement.getBoundingClientRect();
    w = Math.max(240, Math.floor(box.width));
    h = Math.round(Math.min(460, Math.max(260, w * 0.62)));
    dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = h + 'px';
    follow();
    colors = C.palette(canvas);
    draw();
  }
  function reading() {
    const r = C.readUp(kind, die.R);
    if (r.tilt > FLAT) return { value: null, tilt: r.tilt };
    return { value: r.value, tilt: r.tilt };
  }
  function follow() {
    const pos = die ? die.pos : [0, 0, 0];
    cam = C.camera(w, h, { pitch: 1.05, dist: 11, focal: w < 420 ? 3 : 3.7,
      cy: 0.56, target: [pos[0], Math.max(0, pos[1] - 1), pos[2]] });
  }
  function draw() {
    if (!cam || !die) return;
    // Freeze the camera while held so unprojection stays tied to the gesture.
    if (!drag) follow();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    // Unbounded ground: no rim or wall graphics.
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, C.css(C.lerp(colors.cloth, colors.ink, 0.06)));
    g.addColorStop(1, C.css(C.lerp(colors.paper, colors.cloth, 0.4)));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    if (drag && drag.path.length > 1) {
      ctx.strokeStyle = C.css(colors.brass, 0.6);
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      drag.path.forEach((p, i) => (i ? ctx.lineTo(p.sx, p.sy) : ctx.moveTo(p.sx, p.sy)));
      ctx.stroke();
      ctx.setLineDash([]);
    }
    C.drawShadow(ctx, cam, die, colors);
    const r = die.asleep && state.phase === 'settled' ? reading() : null;
    C.drawDie(ctx, cam, die, colors, r && r.value ? { highlightValue: r.value } : {});
    state.frames += 1;
  }
  function settled() {
    const r = reading();
    state.phase = 'settled';
    state.sleeps += 1;
    state.lastReading = r.value;
    readout.textContent = r.value
      ? 'd' + kind + ' 停在 ' + r.value + '（朝上的面倾斜 ' + (r.tilt * 180 / Math.PI).toFixed(1) + '°）'
      : 'd' + kind + ' 卡边 / 未定：朝上的面倾斜 ' + (r.tilt * 180 / Math.PI).toFixed(0) + '°，没有面完全朝上。可以重投。';
    state.resultText = readout.textContent;
    draw();
  }
  function loop(now) {
    frame = 0;
    if (paused || !die) return;
    const dt = Math.min(0.05, (now - (last || now)) / 1000);
    last = now;
    if (staticBox.checked) {
      // Reduced motion skips intermediate painting, never the physical result.
      for (let n = 0; n < 4800 && !die.asleep; n += 1) {
        C.step(die, 1 / 240, BOUNDS);
        state.simulatedSeconds += 1 / 240;
      }
      if (die.asleep) return settled();
    }
    acc += dt;
    const h = 1 / 240;
    let n = 0;
    while (acc >= h && n < 24) {
      C.step(die, h, BOUNDS);
      state.simulatedSeconds += h;
      acc -= h; n += 1;
      if (die.asleep) break;
    }
    draw();
    if (die.asleep) return settled();
    frame = requestAnimationFrame(loop);
  }
  function wake() {
    if (frame || paused) return;
    last = 0;
    acc = 0;
    frame = requestAnimationFrame(loop);
  }
  function cancel() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
  }
  function launch(vel, ang) {
    const sp = C.len(vel);
    if (sp > MAX_THROW) vel = C.scl(vel, MAX_THROW / sp);
    const sw = C.len(ang);
    if (sw > MAX_SPIN) ang = C.scl(ang, MAX_SPIN / sw);
    die.vel = vel;
    die.ang = ang;
    state.lastSpeed = +C.len(vel).toFixed(2);
    state.simulatedSeconds = 0;
    state.wallContacts = 0;
    state.initial = { kind, pos: die.pos.slice(), R: die.R.map((r) => r.slice()),
      vel: vel.slice(), ang: ang.slice(), seed: state.buttonSeed ?? null,
      source: state.buttonSeed == null ? 'gesture' : fixedBox.checked ? 'fixed' : 'sampled' };
    state.buttonSeed = null;
    die.asleep = false;
    die.still = 0;
    state.throws += 1;
    state.phase = 'moving';
    state.lastReading = null;
    state.resultText = null;
    readout.textContent = 'd' + kind + ' 翻滚中…';
    wake();
  }
  // ---------------------------------------------------------------- pointer
  function hit(sx, sy) {
    if (!die) return false;
    const c = cam.project(die.pos);
    const e = cam.project(C.add(die.pos, [C.solidOf(kind).size * 1.15, 0, 0]));
    return Math.hypot(sx - c[0], sy - c[1]) <= Math.abs(e[0] - c[0]) + 6;
  }
  function local(ev) {
    const r = canvas.getBoundingClientRect();
    return [ev.clientX - r.left, ev.clientY - r.top];
  }
  canvas.addEventListener('pointerdown', (ev) => {
    if (ev.button !== 0 && ev.pointerType === 'mouse') return;
    const [sx, sy] = local(ev);
    if (!hit(sx, sy)) return;          // No die under pointer: let the page scroll normally.
    ev.preventDefault();
    canvas.setPointerCapture(ev.pointerId);
    cancel();
    // Picking up the die leaves pause: the throw that follows must simulate.
    if (paused) { paused = false; pauseBtn.setAttribute('aria-pressed', 'false'); pauseBtn.textContent = '暂停'; }
    const lift = 0.9 + C.solidOf(kind).size;
    drag = { id: ev.pointerId, lift, path: [{ sx, sy, t: performance.now() }],
      previous: { body: { ...die, pos: die.pos.slice(), R: die.R.map((r) => r.slice()),
        vel: die.vel.slice(), ang: die.ang.slice() }, phase: state.phase,
        text: readout.textContent } };
    die.asleep = true;
    die.vel = [0, 0, 0];
    die.ang = [0, 0, 0];
    die.pos = cam.unproject(sx, sy, lift);
    state.phase = 'held';
    state.pointerId = ev.pointerId;
    if (!state.resultText) readout.textContent = '拿起 d' + kind + '：拖动后松开就投出，越快越用力。';
    canvas.classList.add('is-holding');
    draw();
  });
  canvas.addEventListener('pointermove', (ev) => {
    if (!drag || ev.pointerId !== drag.id) return;
    ev.preventDefault();
    const [sx, sy] = local(ev);
    const t = performance.now();
    drag.path.push({ sx, sy, t });
    while (drag.path.length > 2 && t - drag.path[0].t > 140) drag.path.shift();
    const before = die.pos;
    die.pos = cam.unproject(sx, sy, drag.lift);
    // Turn the held die slightly as it is dragged, like rolling it in the hand.
    const mv = C.sub(die.pos, before);
    if (C.len(mv) > 1e-4) die.R = C.orthonormal(C.mul(C.axisAngle(C.cross([0, 1, 0], mv), C.len(mv) * 1.6), die.R));
    draw();
  });
  function release(ev, cancelled) {
    if (!drag || ev.pointerId !== drag.id) return;
    const path = drag.path;
    const previous = drag.previous;
    drag = null;
    canvas.classList.remove('is-holding');
    if (canvas.hasPointerCapture(ev.pointerId)) canvas.releasePointerCapture(ev.pointerId);
    if (cancelled) {
      // No throw occurred: restore the held body and its existing result.
      state.cancelled = (state.cancelled || 0) + 1;
      die = previous.body;
      state.phase = previous.phase;
      readout.textContent = previous.text;
      draw();
      if (!die.asleep) wake();
      return;
    }
    const a = path[0], b = path[path.length - 1];
    const dt = Math.max(0.016, (b.t - a.t) / 1000);
    const pa = cam.unproject(a.sx, a.sy, 0), pb = cam.unproject(b.sx, b.sy, 0);
    const v = C.scl(C.sub(pb, pa), 1 / dt);
    const speed = Math.min(MAX_THROW, C.len([v[0], 0, v[2]]));
    const vel = [v[0], 1.5 + speed * 0.28, v[2]];
    // Spin from the throw direction (roll forward) plus a little twist.
    const roll = C.cross([0, 1, 0], [v[0], 0, v[2]]);
    const ang = C.add(C.scl(roll, 1.7), [0, (b.sx - a.sx) * 0.02, 0]);
    launch(vel, C.len(ang) < 1 ? C.add(ang, [2, 0.5, 1.5]) : ang);
  }
  canvas.addEventListener('pointerup', (ev) => release(ev, false));
  canvas.addEventListener('pointercancel', (ev) => release(ev, true));
  canvas.addEventListener('lostpointercapture', (ev) => { if (drag && ev.pointerId === drag.id) release(ev, true); });

  // ---------------------------------------------------------------- controls
  document.querySelectorAll('input[name="kind"]').forEach((input) => input.addEventListener('change', () => {
    if (!input.checked) return;
    kind = Number(input.value);
    reset();
  }));
  function sampledThrow(seed) {
    let bits = seed >>> 0;
    const random = () => {
      bits += 0x6D2B79F5;
      let t = Math.imul(bits ^ bits >>> 15, 1 | bits);
      t ^= t + Math.imul(t ^ t >>> 7, 61 | t);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
    const range = (a, b) => a + (b - a) * random();
    // Uniform rotation quaternion, independent of face numbering or final value.
    const u = random(), a = range(0, 2 * Math.PI), b = range(0, 2 * Math.PI);
    const x = Math.sqrt(1 - u) * Math.sin(a), y = Math.sqrt(1 - u) * Math.cos(a);
    const z = Math.sqrt(u) * Math.sin(b), q = Math.sqrt(u) * Math.cos(b);
    const R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * q), 2 * (x * z + y * q)],
      [2 * (x * y + z * q), 1 - 2 * (x * x + z * z), 2 * (y * z - x * q)],
      [2 * (x * z - y * q), 2 * (y * z + x * q), 1 - 2 * (x * x + y * y)]];
    const pos = [range(-4.6, 4.6), range(1.8, 3), range(-2.7, 2.7)];
    const angle = Math.atan2(-pos[2], -pos[0]) + range(-0.65, 0.65);
    const speed = range(5, 11);
    return { pos, R, vel: [Math.cos(angle) * speed, range(1, 4), Math.sin(angle) * speed],
      ang: [range(-18, 18), range(-12, 12), range(-18, 18)] };
  }
  document.getElementById('lab-throw').addEventListener('click', () => {
    if (fixedBox.checked && !seedInput.reportValidity()) return;
    const seed = fixedBox.checked ? Number(seedInput.value) >>> 0
      : crypto.getRandomValues(new Uint32Array(1))[0];
    if (!fixedBox.checked) seedInput.value = String(seed);
    const initial = sampledThrow(seed);
    reset();
    state.buttonSeed = seed;
    die = C.body(kind, { pos: initial.pos, R: initial.R });
    launch(initial.vel, initial.ang);
  });
  pauseBtn.addEventListener('click', () => {
    paused = !paused;
    pauseBtn.setAttribute('aria-pressed', String(paused));
    pauseBtn.textContent = paused ? '继续' : '暂停';
    if (paused) { cancel(); if (!state.resultText) readout.textContent = '已暂停。'; }
    else if (die && !die.asleep) { readout.textContent = 'd' + kind + ' 翻滚中…'; wake(); }
  });
  document.getElementById('lab-reset').addEventListener('click', reset);
  staticBox.addEventListener('change', () => { if (staticBox.checked && die && !die.asleep) wake(); });
  // Reduced motion: offer static viewing by default, but never fake a reading;
  // the user can still untick it to watch the simulation.
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) staticBox.checked = true;
  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 80); });
  resize();
  reset();
  state.api = { setKind(k) { const r = document.querySelector('input[name="kind"][value="' + k + '"]'); r.checked = true; r.dispatchEvent(new Event('change')); },
    get die() { return die; }, get running() { return Boolean(frame); }, bounds: BOUNDS, project: (p) => cam.project(p) };
})();
