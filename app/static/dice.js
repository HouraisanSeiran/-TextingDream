/* ===== TDDiceCore: polyhedral dice geometry, oblique camera, Canvas2D renderer and
 * an approximate rigid-body stepper. No dependencies. The game (TDDice.roll) only
 * uses scripted tumbles ending on the server's face; free physics is used by the
 * local sandbox page only. */
(function () {
  'use strict';
  if (window.TDDiceCore) return;
  const PHI = (1 + Math.sqrt(5)) / 2;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const scl = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const len = (a) => Math.hypot(a[0], a[1], a[2]);
  const unit = (a) => { const n = len(a) || 1; return [a[0] / n, a[1] / n, a[2] / n]; };
  // Rotation matrices are row-major 3x3; apply(m, v) = m·v.
  const apply = (m, v) => [dot(m[0], v), dot(m[1], v), dot(m[2], v)];
  const mul = (a, b) => a.map((r) => [0, 1, 2].map((j) => r[0] * b[0][j] + r[1] * b[1][j] + r[2] * b[2][j]));
  const transpose = (m) => [[m[0][0], m[1][0], m[2][0]], [m[0][1], m[1][1], m[2][1]], [m[0][2], m[1][2], m[2][2]]];
  const ID = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  function axisAngle(axis, angle) {
    const [x, y, z] = unit(axis);
    const c = Math.cos(angle), s = Math.sin(angle), t = 1 - c;
    return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
      [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
      [t * x * z - s * y, t * y * z + s * x, t * z * z + c]];
  }
  function orthonormal(m) {
    const a = unit(m[0]);
    const b = unit(sub(m[1], scl(a, dot(a, m[1]))));
    return [a, b, cross(a, b)];
  }
  // Rotation taking unit vector a onto unit vector b.
  function align(a, b) {
    const c = dot(a, b);
    if (c > 0.999999) return ID;
    if (c < -0.999999) {
      const p = Math.abs(a[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
      return axisAngle(cross(a, p), Math.PI);
    }
    return axisAngle(cross(a, b), Math.acos(c));
  }

  // ---------------------------------------------------------------- geometry
  // Convex hull faces from vertices: brute force planes, merge coplanar points.
  function hull(verts) {
    const faces = [];
    const n = verts.length;
    const seen = new Set();
    for (let i = 0; i < n; i += 1) for (let j = i + 1; j < n; j += 1) for (let k = j + 1; k < n; k += 1) {
      let nrm = cross(sub(verts[j], verts[i]), sub(verts[k], verts[i]));
      if (len(nrm) < 1e-9) continue;
      nrm = unit(nrm);
      let d = dot(nrm, verts[i]);
      if (d < 0) { nrm = scl(nrm, -1); d = -d; }
      if (verts.some((v) => dot(nrm, v) > d + 1e-6)) continue;
      const on = verts.map((v, idx) => [v, idx]).filter(([v]) => Math.abs(dot(nrm, v) - d) < 1e-6).map(([, idx]) => idx);
      const key = on.slice().sort((a, b) => a - b).join(',');
      if (seen.has(key)) continue;
      seen.add(key);
      const c = scl(on.reduce((s, idx) => add(s, verts[idx]), [0, 0, 0]), 1 / on.length);
      const ref = unit(sub(verts[on[0]], c));
      const ref2 = cross(nrm, ref);
      on.sort((a, b) => {
        const pa = sub(verts[a], c), pb = sub(verts[b], c);
        return Math.atan2(dot(pa, ref2), dot(pa, ref)) - Math.atan2(dot(pb, ref2), dot(pb, ref));
      });
      faces.push({ idx: on, c, n: nrm });
    }
    return faces;
  }
  function build(kind) {
    let verts;
    if (kind === 6) {
      verts = [];
      [-1, 1].forEach((x) => [-1, 1].forEach((y) => [-1, 1].forEach((z) => verts.push([x, y, z]))));
    } else if (kind === 8) {
      verts = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
    } else if (kind === 12) {
      verts = [];
      [-1, 1].forEach((x) => [-1, 1].forEach((y) => [-1, 1].forEach((z) => verts.push([x, y, z]))));
      const a = 1 / PHI;
      [-1, 1].forEach((p) => [-1, 1].forEach((q) => {
        verts.push([0, p * a, q * PHI], [p * a, q * PHI, 0], [q * PHI, 0, p * a]);
      }));
    } else {
      verts = [];
      [-1, 1].forEach((a) => [-1, 1].forEach((b) => verts.push([0, a, b * PHI], [a, b * PHI, 0], [b * PHI, 0, a])));
    }
    // Normalise so the circumradius is 1.
    const r = Math.max(...verts.map(len));
    verts = verts.map((v) => scl(v, 1 / r));
    const faces = hull(verts);
    // Number faces so opposite faces sum to N + 1 (standard dice convention).
    let next = 1;
    faces.forEach((f) => {
      if (f.value) return;
      const twin = faces.find((g) => !g.value && g !== f && dot(g.n, f.n) < -0.999);
      f.value = next;
      if (twin) twin.value = kind + 1 - next;
      next += 1;
    });
    faces.forEach((f) => {
      // Text "up" direction inside the face plane: towards the first vertex for
      // triangles, towards an edge midpoint for squares/pentagons looks more natural.
      const tip = f.idx.length === 3 ? verts[f.idx[0]]
        : scl(add(verts[f.idx[0]], verts[f.idx[1]]), 0.5);
      f.up = unit(sub(tip, f.c));
      f.side = cross(f.up, f.n);
      f.inr = Math.min(...f.idx.map((i, k) => {
        const a = verts[i], b = verts[f.idx[(k + 1) % f.idx.length]];
        const e = unit(sub(b, a));
        const p = sub(f.c, a);
        return len(sub(p, scl(e, dot(p, e))));
      }));
    });
    const inradius = dot(faces[0].n, faces[0].c);
    // Real dice proportions: scale so all kinds look comparable on the table.
    const size = { 6: 0.78, 8: 1.02, 12: 0.98, 20: 1.0 }[kind];
    return { kind, verts, faces, inradius, size };
  }
  const SOLIDS = {};
  function solidOf(kind) {
    kind = Number(kind);
    if (![6, 8, 12, 20].includes(kind)) kind = 20;
    if (!SOLIDS[kind]) SOLIDS[kind] = build(kind);
    return SOLIDS[kind];
  }
  // Orientation (body→world) with `value` face pointing straight up (+Y), its
  // number reading "up" away from the camera (towards -Z), resting on the table.
  function restPose(kind, value, yaw) {
    const s = solidOf(kind);
    const f = s.faces.find((x) => x.value === value) || s.faces[0];
    // Rows = world X,Y,Z expressed in body coords: face normal → +Y, numeral
    // "up" → -Z (away from the camera), so it reads upright from the viewer.
    const m = [f.side, f.n, scl(f.up, -1)];
    return yaw ? mul(axisAngle([0, 1, 0], yaw), m) : m;
  }
  // Which face points up, and how decisively. tilt = angle (rad) off vertical.
  function readUp(kind, R) {
    const s = solidOf(kind);
    let best = null, second = -2;
    s.faces.forEach((f) => {
      const y = apply(R, f.n)[1];
      if (!best || y > best.y) { if (best) second = Math.max(second, best.y); best = { f, y }; }
      else second = Math.max(second, y);
    });
    return { value: best.f.value, tilt: Math.acos(Math.min(1, best.y)), margin: best.y - second };
  }

  // ---------------------------------------------------------------- camera
  // Fixed oblique camera looking down at the table (world Y up, table at y=0).
  function camera(w, h, opts) {
    opts = opts || {};
    const pitch = opts.pitch != null ? opts.pitch : 0.92;     // rad below horizontal
    const dist = opts.dist || 9;
    const target = opts.target || [0, 0, 0];
    const eye = [target[0], target[1] + Math.sin(pitch) * dist, target[2] + Math.cos(pitch) * dist];
    const fwd = unit(sub(target, eye));
    const right = unit(cross(fwd, [0, 1, 0]));
    const up = cross(right, fwd);
    const focal = (opts.focal || 1.9) * Math.min(w, h * 1.2) / 2;
    const cx = w / 2, cy = h * (opts.cy != null ? opts.cy : 0.5);
    return {
      eye, fwd, right, up, w, h,
      project(p) {
        const d = sub(p, eye);
        const z = dot(d, fwd);
        const k = focal / Math.max(0.05, z);
        return [cx + dot(d, right) * k, cy - dot(d, up) * k, z];
      },
      // Screen → point on the plane y = planeY.
      unproject(sx, sy, planeY) {
        const dir = unit(add(add(fwd, scl(right, (sx - cx) / focal)), scl(up, -(sy - cy) / focal)));
        const t = (planeY - eye[1]) / (dir[1] || -1e-6);
        return add(eye, scl(dir, t));
      },
    };
  }

  // ---------------------------------------------------------------- render
  function rgb(v, fb) {
    const hex = String(v || '').trim().replace('#', '');
    if (/^[0-9a-f]{6}$/i.test(hex)) return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
    return fb;
  }
  function palette(node) {
    const st = node ? getComputedStyle(node) : null;
    const g = (k, fb) => rgb(st && st.getPropertyValue(k), fb);
    return { ink: g('--forest', [37, 72, 62]), deep: g('--forest-deep', [27, 56, 47]),
      paper: g('--paper-light', [251, 250, 245]), cloth: g('--parchment', [235, 231, 217]),
      brass: g('--brass', [184, 132, 79]),
      font: (st && st.fontFamily) || 'serif' };
  }
  const css = (c, a) => a == null ? 'rgb(' + c.map(Math.round).join(',') + ')' : 'rgba(' + c.map(Math.round).join(',') + ',' + a + ')';
  const lerp = (a, b, t) => [0, 1, 2].map((i) => a[i] + (b[i] - a[i]) * t);
  const LIGHT = unit([-0.55, 1, 0.35]);
  // Materials only change how faces are painted. Geometry, face numbering and
  // the up-face reading are identical for every material.
  const MATERIALS = {
    ivory: { label: '象牙' },
    metal: { label: '金属', body: [178, 142, 90], edge: [70, 50, 26], ink: [40, 27, 12],
      hi: [255, 246, 220], spec: 0.95, power: 70 },
    wood: { label: '木质', body: [160, 106, 62], edge: [70, 40, 20], ink: [48, 25, 10],
      hi: [252, 228, 160], spec: 0.08, power: 12 },
    crystal: { label: '水晶', body: [156, 200, 230], edge: [56, 100, 148], ink: [16, 42, 82],
      hi: [214, 140, 30], spec: 0.9, power: 90, alpha: 0.42 },
  };
  const MATERIAL_KEY = 'td-dice-material';
  let materialId = 'ivory';
  try {
    const saved = window.localStorage && localStorage.getItem(MATERIAL_KEY);
    if (saved && MATERIALS[saved]) materialId = saved;
  } catch (err) { /* storage blocked: keep default */ }
  function material() { return materialId; }
  // A view preference only: stored in this browser, never sent to the server.
  function setMaterial(id) {
    if (!MATERIALS[id]) return materialId;
    materialId = id;
    try { localStorage.setItem(MATERIAL_KEY, id); } catch (err) { /* ignore */ }
    try { window.dispatchEvent(new CustomEvent('td-dice-material', { detail: id })); } catch (err) { /* ignore */ }
    return id;
  }
  function facePath(ctx, f, scr) {
    ctx.beginPath();
    f.idx.forEach((i, k) => (k ? ctx.lineTo(scr[i][0], scr[i][1]) : ctx.moveTo(scr[i][0], scr[i][1])));
    ctx.closePath();
  }
  // Wood grain drawn in face-local coordinates so it bends with the face.
  function grain(ctx, f, scr, m, edge) {
    ctx.save();
    facePath(ctx, f, scr);
    ctx.clip();
    ctx.transform(m[0], m[1], m[2], m[3], m[4], m[5]);
    const phase = f.value * 1.7;
    ctx.lineWidth = 3;
    for (let y = -170; y <= 170; y += 30) {
      ctx.strokeStyle = css(edge, 0.12 + 0.1 * ((Math.abs(y) / 30 + f.value) % 2));
      ctx.beginPath();
      for (let x = -220; x <= 220; x += 20) {
        const yy = y + 9 * Math.sin(x / 45 + phase + y / 60) + 4 * Math.sin(x / 13 + phase);
        if (x === -220) ctx.moveTo(x, yy); else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
  // Default material: warm ivory body with forest-ink numerals. `body` overrides.
  function drawDie(ctx, cam, die, colors, style) {
    style = style || {};
    const matId = MATERIALS[style.material] ? style.material : materialId;
    const mat = MATERIALS[matId];
    const plain = matId === 'ivory';
    const s = solidOf(die.kind);
    const R = die.R, pos = die.pos, size = (die.scale || 1) * s.size;
    const world = s.verts.map((v) => add(pos, scl(apply(R, v), size)));
    const scr = world.map((p) => cam.project(p));
    const body = plain ? (style.body || colors.paper) : mat.body;
    const edge = plain ? (style.edge || colors.deep) : mat.edge;
    const ink = plain ? (style.ink || colors.ink) : mat.ink;
    const hiColor = plain ? colors.brass : mat.hi;
    const rows = s.faces.map((f) => {
      const n = apply(R, f.n);
      const c = add(pos, scl(apply(R, f.c), size));
      return { f, n, c, facing: dot(n, sub(cam.eye, c)) };
    });
    const vis = rows.filter((r) => r.facing > 1e-4);
    vis.sort((a, b) => dot(sub(b.c, cam.eye), cam.fwd) - dot(sub(a.c, cam.eye), cam.fwd));
    const lw = Math.max(1, size * cam.w / 260);
    ctx.save();
    // Unused die of a pair: non-ivory materials fade instead of recolouring.
    if (!plain && style.dim) ctx.globalAlpha *= 0.42;
    ctx.lineJoin = 'round';
    if (matId === 'crystal') {
      // Far side seen through the glass: faint facets and edges only. Back
      // numerals are never drawn, so they can not be misread as the result.
      rows.filter((r) => r.facing <= 1e-4).forEach(({ f }) => {
        facePath(ctx, f, scr);
        ctx.fillStyle = css(lerp(edge, body, 0.55), 0.16);
        ctx.fill();
        ctx.strokeStyle = css(lerp(body, [255, 255, 255], 0.5), 0.32);
        ctx.lineWidth = lw * 0.8;
        ctx.stroke();
      });
    }
    vis.forEach(({ f, n, c }) => {
      const lam = Math.max(0, dot(n, LIGHT));
      const view = unit(sub(cam.eye, c));
      const half = unit(add(LIGHT, view));
      const spec = Math.pow(Math.max(0, dot(n, half)), plain ? 40 : mat.power) * (plain ? 0.35 : mat.spec);
      const shade = 0.42 + 0.58 * lam;
      let base = lerp(lerp(edge, body, 0.25), body, shade);
      if (matId === 'metal') {
        // Environment reflection: bright sky above, dark floor below.
        const env = 0.5 + 0.5 * n[1];
        base = lerp(lerp(edge, body, 0.15), lerp(body, [255, 250, 236], 0.4),
          Math.min(1, env * 0.65 + lam * 0.5));
      } else if (matId === 'wood') {
        base = lerp(base, edge, (f.value % 3) * 0.04);
      }
      const fill = lerp(base, [255, 255, 255], Math.min(1, spec));
      facePath(ctx, f, scr);
      ctx.fillStyle = matId === 'crystal' ? css(fill, mat.alpha + 0.3 * spec) : css(fill);
      ctx.fill();
      // Face-plane affine map (face coords to screen) for grain and numerals.
      const p0 = cam.project(c);
      const e = 0.02;
      const u = apply(R, f.side), v = apply(R, f.up);
      const pu = cam.project(add(c, scl(u, e * size)));
      const pv = cam.project(add(c, scl(v, e * size)));
      // Face-local text unit: glyph height ≈ 0.95 × inradius of face.
      const glyph = f.inr * size * (die.kind === 6 ? 1.05 : die.kind === 12 ? 0.95 : die.kind === 8 ? 0.9 : 1.05);
      const k = glyph / e / 100;
      const ax = (pu[0] - p0[0]) * k, ay = (pu[1] - p0[1]) * k;
      const bx = -(pv[0] - p0[0]) * k, by = -(pv[1] - p0[1]) * k;
      if (matId === 'wood') grain(ctx, f, scr, [ax, ay, bx, by, p0[0], p0[1]], edge);
      facePath(ctx, f, scr);
      // Edge line per material: bevel highlight on metal, bright rim on glass.
      if (matId === 'metal') ctx.strokeStyle = css(lerp(edge, [255, 248, 225], 0.3 + lam * 0.5), 0.95);
      else if (matId === 'crystal') ctx.strokeStyle = css(lerp(body, [255, 255, 255], 0.6 + lam * 0.3), 0.9);
      else ctx.strokeStyle = css(lerp(edge, body, 0.15 + lam * 0.3), 0.9);
      ctx.lineWidth = lw;
      ctx.stroke();
      // Skip numerals only on faces seen almost edge-on (scale-independent:
      // view cosine, not screen-space area, so small/mobile canvases still
      // print every readable face).
      if (dot(n, unit(sub(cam.eye, c))) < 0.12) return;
      ctx.save();
      ctx.transform(ax, ay, bx, by, p0[0], p0[1]);
      const label = String(f.value);
      const fs = label.length > 1 ? 74 : 86;
      ctx.font = '700 ' + fs + 'px ' + (colors.font || 'serif');
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const offset = die.kind === 20 || die.kind === 8 ? 10 : 4;
      const highlighted = style.highlightValue === f.value;
      if (!highlighted && (matId === 'metal' || matId === 'wood')) {
        // Engraved look: a light lip below the dark cut.
        ctx.fillStyle = css(mat.hi, matId === 'metal' ? 0.45 : 0.3);
        ctx.fillText(label, 0, offset + 4);
      }
      if (matId === 'crystal') ctx.fillStyle = css(ink, 0.95);
      else ctx.fillStyle = css(lerp(ink, edge, 0.2 * (1 - lam)), 0.55 + 0.45 * Math.min(1, n[1] * 0.5 + 0.7));
      if (highlighted) ctx.fillStyle = css(hiColor);
      ctx.fillText(label, 0, offset);
      if ((f.value === 6 || f.value === 9) && s.kind !== 6) ctx.fillRect(-18, offset + 40, 36, 6);
      ctx.restore();
    });
    ctx.restore();
  }
  // Soft contact shadow under the die: footprint of hull projected onto table,
  // tighter and darker the closer the die is to the table.
  function drawShadow(ctx, cam, die, colors) {
    const s = solidOf(die.kind);
    const size = (die.scale || 1) * s.size;
    const lowest = Math.min(...s.verts.map((v) => apply(die.R, v)[1] * size + die.pos[1]));
    const h = Math.max(0, lowest);
    const c = cam.project([die.pos[0], 0, die.pos[2]]);
    const edge = cam.project([die.pos[0] + size, 0, die.pos[2]]);
    const r = Math.abs(edge[0] - c[0]) * (1.05 + h * 0.25);
    const alpha = Math.max(0.06, 0.34 - h * 0.12);
    const g = ctx.createRadialGradient(c[0], c[1], r * 0.1, c[0], c[1], r);
    g.addColorStop(0, css(colors.deep, alpha));
    g.addColorStop(0.55, css(colors.deep, alpha * 0.55));
    g.addColorStop(1, css(colors.deep, 0));
    ctx.save();
    ctx.translate(c[0], c[1]);
    ctx.scale(1, 0.55);
    ctx.translate(-c[0], -c[1]);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(c[0], c[1], r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // ---------------------------------------------------------------- rigid body
  // Approximate rigid body: sphere-ish inertia, vertex contacts against table
  // (y=0) and four walls, sequential impulses with restitution and Coulomb
  // friction, linear/angular damping, sleep when slow. NOT a precision solver.
  function body(kind, opts) {
    opts = opts || {};
    const s = solidOf(kind);
    return { kind: s.kind, R: opts.R || ID, pos: opts.pos || [0, 2, 0], vel: opts.vel || [0, 0, 0],
      ang: opts.ang || [0, 0, 0], scale: opts.scale || 1, asleep: false, still: 0 };
  }
  const WORLD = { g: 24, restitution: 0.36, friction: 0.42, linDamp: 0.18, angDamp: 0.55, maxSpeed: 26, maxSpin: 34 };
  function step(b, dt, bounds, P) {
    P = P || WORLD;
    const s = solidOf(b.kind);
    const size = b.scale * s.size;
    // Inertia of a solid sphere of radius ~size (approximation for all shapes).
    const invMass = 1, invI = 1 / (0.4 * size * size * (b.kind === 6 ? 1.15 : 1));
    b.vel[1] -= P.g * dt;
    b.vel = scl(b.vel, Math.max(0, 1 - P.linDamp * dt));
    b.ang = scl(b.ang, Math.max(0, 1 - P.angDamp * dt));
    const sp = len(b.vel); if (sp > P.maxSpeed) b.vel = scl(b.vel, P.maxSpeed / sp);
    const sw = len(b.ang); if (sw > P.maxSpin) b.ang = scl(b.ang, P.maxSpin / sw);
    b.pos = add(b.pos, scl(b.vel, dt));
    if (sw > 1e-9) b.R = orthonormal(mul(axisAngle(b.ang, sw * dt), b.R));
    // Contact planes: table y=0 (normal +Y) and walls.
    const planes = [[[0, 1, 0], 0]];
    if (bounds) {
      planes.push([[1, 0, 0], bounds.minX], [[-1, 0, 0], -bounds.maxX], [[0, 0, 1], bounds.minZ], [[0, 0, -1], -bounds.maxZ]);
    }
    let touching = false;
    for (let iter = 0; iter < 3; iter += 1) {
      planes.forEach(([n, d]) => {
        let deepest = 0;
        const contacts = [];
        s.verts.forEach((v) => {
          const r = scl(apply(b.R, v), size);
          const p = add(b.pos, r);
          const depth = d - dot(n, p);
          if (depth > -1e-4) { contacts.push({ r, depth }); deepest = Math.max(deepest, depth); }
        });
        if (!contacts.length) return;
        if (n[1] === 1) touching = true;
        // Positional correction (no tunnelling through the table/walls).
        if (deepest > 0) b.pos = add(b.pos, scl(n, deepest * 0.9));
        const share = 1 / contacts.length;
        contacts.forEach(({ r }) => {
          const vp = add(b.vel, cross(b.ang, r));
          const vn = dot(vp, n);
          if (vn >= 0) return;
          const rn = cross(r, n);
          const kN = invMass + invI * dot(rn, rn);
          const e = Math.abs(vn) > 1.2 ? P.restitution : 0;
          const jn = -(1 + e) * vn / kN * share;
          b.vel = add(b.vel, scl(n, jn * invMass));
          b.ang = add(b.ang, scl(cross(r, scl(n, jn)), invI));
          // Friction along tangential velocity, clamped by Coulomb cone.
          const vp2 = add(b.vel, cross(b.ang, r));
          const vt = sub(vp2, scl(n, dot(vp2, n)));
          const vtl = len(vt);
          if (vtl > 1e-6) {
            const t = scl(vt, 1 / vtl);
            const rt = cross(r, t);
            const kT = invMass + invI * dot(rt, rt);
            const jt = Math.min(vtl / kT * share, P.friction * jn);
            b.vel = sub(b.vel, scl(t, jt * invMass));
            b.ang = sub(b.ang, scl(cross(r, scl(t, jt)), invI));
          }
        });
      });
    }
    // Rolling resistance when resting on the table.
    if (touching) {
      b.ang = scl(b.ang, Math.max(0, 1 - 2.2 * dt));
      b.vel[0] *= Math.max(0, 1 - 1.4 * dt);
      b.vel[2] *= Math.max(0, 1 - 1.4 * dt);
    }
    const slow = touching && len(b.vel) < 0.12 && len(b.ang) < 0.25;
    b.still = slow ? b.still + dt : 0;
    if (b.still > 0.35) {
      b.asleep = true;
      b.vel = [0, 0, 0];
      b.ang = [0, 0, 0];
    }
    return touching;
  }

  // ------------------------------------------------- scripted (server) throws
  // A server-decided die still moves with simulated motion: we run the
  // approximate rigid body from a fixed throw, then relabel the solid with one
  // of its own symmetry rotations so the face that ended on top carries the
  // server's value. The relabelling maps the polyhedron onto itself, so the
  // motion is unchanged; only which numeral is printed where changes.
  function symmetries(kind) {
    const s = solidOf(kind);
    if (s.syms) return s.syms;
    const out = [];
    const key = (v) => v.map((x) => Math.round(x * 1e4) + 0).join(',');
    const set = new Set(s.verts.map(key));
    const a0 = s.verts[0];
    const dmin = Math.min(...s.verts.filter((w) => w !== a0).map((w) => len(sub(w, a0))));
    const b0 = s.verts.find((v) => v !== a0 && Math.abs(len(sub(v, a0)) - dmin) < 1e-6);
    const frame = (p, q) => { const x = unit(p); const y = unit(sub(q, scl(x, dot(x, q)))); return [x, y, cross(x, y)]; };
    const F0 = frame(a0, b0);
    s.verts.forEach((a) => s.verts.forEach((b) => {
      if (a === b || Math.abs(len(sub(a, b)) - dmin) > 1e-6) return;
      const M = mul(transpose(frame(a, b)), F0);
      if (s.verts.every((v) => set.has(key(apply(M, v))))) out.push(M);
    }));
    s.syms = out;
    return out;
  }
  const THROWS = [
    { pos: [-1.5, 1.6, -0.5], vel: [3.4, 1.2, 0.9], ang: [9, 4, -13] },
    { pos: [1.5, 1.5, -0.6], vel: [-3.3, 1.4, 1.0], ang: [-11, -3, 12] },
    { pos: [-1.4, 1.8, 0.6], vel: [3.6, 1.0, -0.8], ang: [12, -6, 8] },
    { pos: [1.3, 1.9, 0.6], vel: [-3.0, 0.8, -1.0], ang: [-7, 9, -14] },
    { pos: [-1.6, 1.4, 0], vel: [3.8, 1.6, 0.2], ang: [3, 12, -10] },
    { pos: [0.3, 2.1, -1.4], vel: [-0.6, 0.6, 3.2], ang: [14, -2, 5] },
    { pos: [-1.2, 1.7, -0.9], vel: [2.8, 1.0, 1.6], ang: [-6, 10, 11] },
    { pos: [1.2, 1.7, 0.9], vel: [-2.9, 1.2, -1.4], ang: [10, 7, -9] },
  ];
  const DT = 1 / 240;
  const TRAY = { minX: -1.9, maxX: 1.9, minZ: -1.5, maxZ: 1.5 };
  function simulate(kind, t, bounds) {
    const b = body(kind, { pos: t.pos.slice(), vel: t.vel.slice(), ang: t.ang.slice(),
      R: orthonormal(mul(axisAngle([0.3, 1, 0.2], 0.7), axisAngle([1, 0, 0.4], 1.1))) });
    const frames = [{ t: 0, pos: b.pos.slice(), R: b.R.map((r) => r.slice()) }];
    let time = 0;
    while (time < 2.6) {
      for (let k = 0; k < 4; k += 1) step(b, DT, bounds);
      time += DT * 4;
      frames.push({ t: time, pos: b.pos.slice(), R: b.R.map((r) => r.slice()) });
      if (b.asleep) break;
    }
    return { frames, asleep: b.asleep, time, R: b.R, pos: b.pos };
  }
  // Cached per kind/slot: a throw that settles flat within the time budget.
  const TRACKS = {};
  function track(kind, slot) {
    if (slot > 0 && !TRACKS[kind + ':0']) track(kind, 0);
    const id = kind + ':' + slot;
    if (TRACKS[id]) return TRACKS[id];
    let best = null;
    const taken = slot > 0 && TRACKS[kind + ':0'] ? TRACKS[kind + ':0'].throwIndex : -1;
    for (let i = 0; i < THROWS.length; i += 1) {
      const index = (slot * 3 + i) % THROWS.length;
      if (index === taken) continue;
      const t = THROWS[index];
      const sim = simulate(kind, t, TRAY);
      const up = readUp(kind, sim.R);
      const score = (sim.asleep ? 0 : 10) + up.tilt * 20 + Math.max(0, Math.abs(sim.time - 1.3) - 0.2) * 4;
      if (!best || score < best.score) best = { score, sim, up, throwIndex: index };
      if (sim.asleep && up.tilt < 0.03 && sim.time > 1.0 && sim.time < 1.6) break;
    }
    TRACKS[id] = best;
    return best;
  }
  // Pick a symmetry S so `value` ends on top and a world yaw so its numeral ends
  // upright for the camera; the yaw rotates the whole trajectory about the
  // tray centre, so nothing snaps at the end.
  function scripted(kind, value, slot) {
    const s = solidOf(kind);
    const tr = track(kind, slot);
    const endR = tr.sim.R;
    const topFace = s.faces.find((f) => f.value === tr.up.value);
    const target = s.faces.find((f) => f.value === value) || topFace;
    let pick = null;
    symmetries(kind).forEach((S) => {
      if (dot(apply(S, target.n), topFace.n) < 0.999) return;
      const up = apply(mul(endR, S), target.up);
      const yaw = Math.atan2(up[0], -up[2]);
      if (!pick || Math.abs(yaw) < Math.abs(pick.yaw)) pick = { S, yaw };
    });
    const Y = axisAngle([0, 1, 0], pick.yaw);
    const end = tr.sim.pos;
    const frames = tr.sim.frames.map((f) => ({ t: f.t,
      pos: apply(Y, [f.pos[0] - end[0], f.pos[1], f.pos[2] - end[2]]),
      R: mul(Y, mul(f.R, pick.S)) }));
    return { frames, duration: tr.sim.time, asleep: tr.sim.asleep, value: target.value,
      rest: restPose(kind, target.value), restPos: [0, s.inradius * s.size, 0] };
  }
  // Pose at time ms; the last 180 ms ease onto the exact rest pose so the
  // final frame equals the static rendering pixel for pixel.
  function sample(script, ms) {
    const t = ms / 1000;
    const fr = script.frames;
    if (t >= script.duration) return { pos: script.restPos, R: script.rest, done: true };
    let i = 0;
    while (i < fr.length - 2 && fr[i + 1].t < t) i += 1;
    const a = fr[i], b = fr[i + 1] || a;
    const k = b.t > a.t ? Math.max(0, Math.min(1, (t - a.t) / (b.t - a.t))) : 0;
    let pos = [0, 1, 2].map((j) => a.pos[j] + (b.pos[j] - a.pos[j]) * k);
    let R = a.R.map((r, j) => r.map((x, c) => x + (b.R[j][c] - x) * k));
    const blend = Math.max(0, 1 - (script.duration - t) / 0.18);
    if (blend > 0) {
      const q = blend * blend * (3 - 2 * blend);
      pos = pos.map((x, j) => x + (script.restPos[j] - x) * q);
      R = R.map((r, j) => r.map((x, c) => x + (script.rest[j][c] - x) * q));
    }
    return { pos, R: orthonormal(R), done: false };
  }

  window.TDDiceCore = { PHI, add, sub, scl, dot, cross, len, unit, apply, mul, transpose, axisAngle, align, orthonormal, ID,
    solidOf, restPose, readUp, camera, palette, css, lerp, drawDie, drawShadow, body, step, WORLD,
    symmetries, simulate, track, scripted, sample, THROWS, TRAY, MATERIALS, material, setMaterial };
})();

/* Public d20 projections only; no client-side resolution or random outcome.
 * The tumble is replayed from a precomputed approximate rigid-body track and is
 * relabelled so that the face which lands on top is exactly the server's die. */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const C = window.TDDiceCore;
  // Legacy five-tier labels (d20_v2) and the four-tier margin mode (d20_margin_v3).
  // tier_label from the server always wins; these are display fallbacks only.
  const legacyTiers = { critical: '大成功', success: '成功', partial: '成功但有代价', setback: '失败但前进', disaster: '失败且恶化', blocked: '未掷骰' };
  const fourTiers = { critical: '大成功', success: '成功', failure: '失败', disaster: '大失败' };
  const positions = { controlled: '稳妥', risky: '冒险', desperate: '孤注一掷' };
  const effects = { limited: '有限', standard: '标准', great: '显著' };
  function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function svg(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  function fourMode(r) {
    return r.tier_mode === 'margin_four' || r.rules_version === 'd20_margin_v3' || r.tier === 'failure';
  }
  function tierLabel(r) {
    if (r.tier_label) return r.tier_label;
    if (r.tier == null) return '';
    return (fourMode(r) ? fourTiers : legacyTiers)[r.tier] || legacyTiers[r.tier] || fourTiers[r.tier] || '判定结果';
  }
  function isRefused(r) { return r.status === 'refused' || r.tier === 'refused' || Boolean(r.refused); }
  function isBlocked(r) { return r.status === 'blocked' || r.tier === 'blocked' || Boolean(r.blocked); }
  function factors(rows) {
    const group = el('div', undefined, 'check-factors');
    (rows || []).forEach((row) => {
      const unfavorable = row.sign === '-';
      group.append(el('span', (unfavorable ? '不利 · ' : '有利 · ') + row.label,
        'check-factor ' + (unfavorable ? 'is-negative' : 'is-positive')));
    });
    return group;
  }
  // Stage marks come only from the server's player-visible `stages`; without them
  // (older data) the clock is drawn exactly as before.
  function clockStages(row, segments) {
    if (!Array.isArray(row.stages)) return [];
    return row.stages.map((stage) => {
      if (!stage || typeof stage !== 'object') return null;
      const at = Number(stage.at);
      if (!Number.isFinite(at)) return null;
      return { at: Math.max(0, Math.min(segments, at)),
        label: typeof stage.label === 'string' ? stage.label : '', reached: stage.reached === true };
    }).filter(Boolean);
  }
  function stageMark(stage, segments, gapAngle) {
    const angle = (-90 + stage.at * 360 / segments) * Math.PI / 180 - gapAngle / 2;
    const point = (radius) => [Number((32 + Math.cos(angle) * radius).toFixed(2)),
      Number((32 + Math.sin(angle) * radius).toFixed(2))];
    const inner = point(19.5);
    const outer = point(stage.reached ? 29.5 : 30.5);
    const mark = svg('g', { class: 'clock-stage' + (stage.reached ? ' is-reached' : '') });
    const hint = svg('title', {});
    hint.textContent = (stage.label || '阶段') + (stage.reached ? '（已到达）' : '（未到达）');
    mark.append(hint,
      svg('line', { x1: inner[0], y1: inner[1], x2: outer[0], y2: outer[1], class: 'clock-stage-halo' }),
      svg('line', { x1: inner[0], y1: inner[1], x2: outer[0], y2: outer[1], class: 'clock-stage-tick' }));
    if (stage.reached) mark.append(svg('circle', { cx: outer[0], cy: outer[1], r: 2, class: 'clock-stage-dot' }));
    return mark;
  }
  function clock(row) {
    const segments = Math.max(1, Math.floor(Number(row.segments) || 1));
    const filled = Math.max(0, Math.min(segments, Number(row.filled) || 0));
    const label = (row.label || '钟') + ' ' + filled + '/' + segments;
    const stages = clockStages(row, segments);
    const stageLabel = typeof row.stage_label === 'string' ? row.stage_label.trim() : '';
    const group = el('div', undefined, 'check-clock' + (row.kind === 'danger' ? ' is-danger' : '')
      + (stages.length ? ' has-stages' : ''));
    const spoken = label + (stageLabel ? '，阶段：' + stageLabel : '');
    const ring = svg('svg', { viewBox: '0 0 64 64', role: 'img', 'aria-label': spoken });
    const title = svg('title', {});
    title.textContent = spoken;
    ring.append(title);
    const circumference = 2 * Math.PI * 25;
    const step = circumference / segments;
    for (let i = 0; i < segments; i += 1) {
      ring.append(svg('circle', { cx: 32, cy: 32, r: 25, fill: 'none', 'stroke-width': 7,
        'stroke-dasharray': Math.max(step - Math.min(4, step * 0.2), 0.1) + ' ' + circumference,
        transform: 'rotate(' + (-90 + i * 360 / segments) + ' 32 32)',
        class: i < filled ? 'clock-filled' : 'clock-empty' }));
    }
    const gapAngle = Math.min(4, step * 0.2) / 25;
    stages.forEach((stage) => ring.append(stageMark(stage, segments, gapAngle)));
    if (stageLabel) {
      const text = el('span', label, 'check-clock-text');
      text.append(el('small', '阶段：' + stageLabel, 'clock-stage-name'));
      group.append(ring, text);
    } else {
      group.append(ring, el('span', label));
    }
    return group;
  }
  function clocks(container, rows) {
    container.replaceChildren();
    container.classList.add('check-clocks');
    (rows || []).forEach((row) => container.append(clock(row)));
  }
  function refusal(v2) {
    if (v2.refused) return typeof v2.refused === 'string' ? v2.refused : '这触到了对方的底线';
    if (v2.status === 'refused') return typeof v2.reason === 'string' && v2.reason ? v2.reason : '这触到了对方的底线';
    if (v2.blocked) return typeof v2.blocked === 'string' ? v2.blocked :
      '同样的办法刚失败过：换个方法、找帮手、做准备或等局面变化';
    return '';
  }
  function preview(container, v2, options) {
    options = options || {};
    const box = el('section', undefined, 'check-preview');
    const badges = el('div', undefined, 'check-badges');
    if (v2.position) badges.append(el('span', '处境 · ' + (positions[v2.position] || v2.position), 'check-badge'));
    if (v2.effect) badges.append(el('span', '效果 · ' + (effects[v2.effect] || v2.effect), 'check-badge'));
    box.append(badges, factors(v2.factors));
    const odds = [];
    if (v2.chance) odds.push('把握：' + v2.chance);
    if (v2.dc != null) odds.push('DC ' + v2.dc);
    if (v2.auto || v2.status === 'auto') odds.push('无需掷骰');
    if (odds.length) box.append(el('p', odds.join(' · '), 'check-odds'));
    if (v2.push_options && v2.push_options.length) {
      const field = el('fieldset', undefined, 'check-push');
      field.append(el('legend', '加码'));
      [{ id: '', label: '不加码' }].concat(v2.push_options).forEach((row) => {
        const label = el('label');
        const input = el('input');
        input.type = 'radio';
        input.name = options.name || 'check-push';
        input.value = row.id;
        input.checked = (options.push || '') === row.id;
        input.addEventListener('change', () => { if (input.checked && options.onPush) options.onPush(row.id); });
        label.append(input, el('span', row.label + (row.cost_text ? ' · ' + row.cost_text : '')));
        field.append(label);
      });
      box.append(field);
    }
    if (v2.clock) box.append(clock(v2.clock));
    const reason = refusal(v2);
    if (reason) box.append(el('p', reason, 'check-refusal'));
    container.append(box);
    return box;
  }
  // Flat SVG fallback (no canvas, or a value outside 1..20).
  function die(value, kept) {
    const item = el('div', undefined, 'd20-die' + (kept ? ' is-kept' : ' is-discarded'));
    item.setAttribute('aria-label', '骰面 ' + value + (kept ? '，采用' : '，未采用'));
    const image = svg('svg', { viewBox: '0 0 120 132', 'aria-hidden': 'true' });
    image.append(svg('path', { d: 'M60 4 112 34 112 96 60 128 8 96 8 34Z', class: 'd20-outline' }),
      svg('path', { d: 'M60 4 30 48 8 34M60 4 90 48 112 34M30 48 90 48 60 98ZM8 96 30 48 60 128 90 48 112 96M8 96 60 98 112 96M60 98 60 128', class: 'd20-facets' }));
    const face = svg('text', { x: 60, y: 72, 'text-anchor': 'middle', class: 'd20-value' });
    face.textContent = value;
    image.append(face);
    item.append(image, el('small', kept ? '采用' : '未采用', 'd20-kept-label'));
    return item;
  }

  // ------------------------------------------------------------ solid d20 stage
  // One canvas per result: a fixed oblique camera over the table, every die an
  // opaque icosahedron with shaded faces, edges, numerals and a contact shadow.
  const STAGE = { 1: { w: 260, h: 196 }, 2: { w: 360, h: 196 } };
  const SPOTS = { 1: [[0, 0]], 2: [[-1.35, 0.05], [1.35, -0.05]] };
  const DELAY = 110;
  function stage(values, keptIndex, mode) {
    if (!C || values.length < 1 || values.length > 2) return null;
    if (!values.every((v) => Number.isInteger(v) && v >= 1 && v <= 20)) return null;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext && canvas.getContext('2d');
    if (!ctx) return null;
    const size = STAGE[values.length];
    const dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
    canvas.width = Math.round(size.w * dpr);
    canvas.height = Math.round(size.h * dpr);
    canvas.className = 'd20-stage';
    canvas.style.maxWidth = size.w + 'px';
    canvas.setAttribute('aria-hidden', 'true');
    const tray = el('div', undefined, 'd20-tray d20-tray-solid');
    const labels = el('div', undefined, 'd20-labels');
    labels.style.maxWidth = size.w + 'px';
    values.forEach((value, i) => {
      const kept = i === keptIndex;
      const item = el('div', undefined, 'd20-die d20-solid' + (kept ? ' is-kept' : ' is-discarded'));
      item.setAttribute('role', 'img');
      item.setAttribute('aria-label', '骰面 ' + value + (kept ? '，采用' : '，未采用'));
      item.append(el('small', kept ? '采用' : '未采用', 'd20-kept-label'));
      labels.append(item);
    });
    tray.append(canvas, labels);
    const cam = C.camera(size.w, size.h, { pitch: 1.13, dist: 10, focal: 4.6, cy: 0.56 });
    const spinning = mode === 'spin';
    const scripts = values.map((v, i) => spinning
      ? { rest: C.restPose(20, v), restPos: [0, 1.1, 0], duration: 1.4 }
      : C.scripted(20, v, i));
    const spots = SPOTS[values.length];
    const total = spinning ? 1400 : Math.max(...scripts.map((s, i) => s.duration * 1000 + i * DELAY));
    let colors = null;
    function render(ms) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, size.w, size.h);
      const dice = [];
      scripts.forEach((script, i) => {
        let pose;
        if (ms == null) pose = { pos: script.restPos, R: script.rest, done: true };
        else if (spinning) {
          const remaining = 1 - Math.min(1, Math.max(0, ms / total));
          const angle = (i ? -1 : 1) * 6 * Math.PI * remaining ** 3;
          pose = { pos: script.restPos, R: C.mul(C.axisAngle([0.7, 1, 0.35], angle), script.rest) };
        } else {
          const local = ms - i * DELAY;
          if (local < 0) return;
          pose = C.sample(script, local);
        }
        const pos = [pose.pos[0] + spots[i][0], pose.pos[1], pose.pos[2] + spots[i][1]];
        dice.push({ i, die: { kind: 20, R: pose.R, pos }, settled: ms == null });
      });
      dice.forEach((d) => C.drawShadow(ctx, cam, d.die, colors));
      dice.sort((a, b) => C.dot(C.sub(b.die.pos, cam.eye), cam.fwd) - C.dot(C.sub(a.die.pos, cam.eye), cam.fwd));
      dice.forEach((d) => {
        const dim = d.settled && d.i !== keptIndex;
        const hi = d.settled && d.i === keptIndex ? { highlightValue: values[d.i] } : {};
        ctx.save();
        C.drawDie(ctx, cam, d.die, colors, dim ? {
          dim: true,
          body: C.lerp(colors.paper, colors.cloth, 0.75),
          edge: C.lerp(colors.deep, colors.paper, 0.4),
          ink: C.lerp(colors.ink, colors.paper, 0.38) } : hi);
        ctx.restore();
      });
    }
    return {
      tray, total,
      prepare(container) { colors = C.palette(container); },
      frame(ms) { render(ms); },
      settle() { render(null); tray.classList.add('is-settled'); },
    };
  }
  const motion = new WeakMap();
  function stop(container) {
    const cancel = motion.get(container);
    if (cancel) cancel();
  }
  function details(result) {
    const box = el('div', undefined, 'check-result-details');
    if (isRefused(result)) {
      // Execution status, not a fifth tier: nothing was rolled or spent.
      box.append(el('strong', '未执行 · 已拒绝', 'check-tier check-status'));
      box.append(el('p', typeof result.refused === 'string' ? result.refused
        : result.reason || result.refusal_text || '这触到了对方的底线', 'check-refusal'));
    } else if (isBlocked(result)) {
      box.append(el('strong', result.tier_label || '未掷骰', 'check-tier check-status'));
      box.append(el('p', typeof result.blocked === 'string' ? result.blocked
        : result.reason || '同样的办法刚失败过：换个方法、找帮手、做准备或等局面变化', 'check-refusal'));
    } else {
      box.append(el('strong', tierLabel(result) || '判定结果', 'check-tier'));
      if (result.rolled === false || result.status === 'auto') {
        box.append(el('p', '无需掷骰', 'check-auto'));
        if (result.reason) box.append(el('p', result.reason));
      }
    }
    const equation = [];
    if (result.rolled && result.kept != null) equation.push('骰面 ' + result.kept);
    if (result.modifier != null) equation.push((result.modifier < 0 ? '− ' : '+ ') + Math.abs(result.modifier));
    if (result.total != null) equation.push('= ' + result.total);
    if (result.dc != null) equation.push('对 DC ' + result.dc);
    if (equation.length) box.append(el('p', equation.join(' '), 'check-equation'));
    if (result.margin != null && fourMode(result)) {
      box.append(el('p', '差值 ' + (result.margin > 0 ? '+' : result.margin < 0 ? '−' : '±') + Math.abs(result.margin), 'check-margin'));
    }
    if (result.advantage) box.append(el('p', result.advantage === 'disadvantage' ? '劣势' : result.advantage === 'advantage' ? '优势' : result.advantage, 'muted'));
    box.append(factors(result.factors));
    if (result.push) box.append(el('p', '加码：' + (result.push.label || result.push), 'check-result-push'));
    if (result.noticed) box.append(el('p', result.noticed, 'check-noticed'));
    if (result.clock) {
      const row = result.clock;
      box.append(el('p', (row.label || '钟') + '：' + row.from + ' → ' + row.to + ' / ' + row.segments, 'check-clock-change'),
        clock(Object.assign({}, row, { filled: row.to })));
    }
    return box;
  }
  function roll(container, result, options) {
    options = options || {};
    stop(container);
    container.replaceChildren();
    container.classList.remove('is-rolling');
    container.classList.add('check-result');
    container.dataset.tier = result.tier || '';
    container.dataset.status = isRefused(result) ? 'refused' : isBlocked(result) ? 'blocked'
      : result.status || (result.rolled === true ? 'rolled' : 'auto');
    container.setAttribute('aria-live', 'polite');
    const summary = details(result);
    let solid = null;
    if (result.rolled === true && !isRefused(result)) {
      const values = Array.isArray(result.dice) && result.dice.length ? result.dice : [result.kept];
      let keptIndex = values.indexOf(result.kept);
      if (keptIndex < 0) keptIndex = 0;
      solid = stage(values, keptIndex, options.mode);
      if (solid) container.append(solid.tray);
      else {
        const tray = el('div', undefined, 'd20-tray');
        values.forEach((value, i) => tray.append(die(value == null ? '?' : value, i === keptIndex)));
        container.append(tray);
      }
    }
    container.append(summary);
    if (!solid) return Promise.resolve();
    solid.prepare(container);
    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || options.animate === false) {
      solid.settle();
      return Promise.resolve();
    }
    container.classList.add('is-rolling');
    summary.hidden = true;
    solid.frame(0);
    return new Promise((resolve) => {
      let frame = 0, timer = 0, done = false;
      const finish = (reveal) => {
        if (done) return;
        done = true;
        cancelAnimationFrame(frame);
        clearTimeout(timer);
        document.removeEventListener('visibilitychange', visibility);
        if (motion.get(container) === cancel) motion.delete(container);
        // A later roll in the same host must not be revealed by this one.
        if (reveal && summary.parentNode === container) {
          solid.settle();
          container.classList.remove('is-rolling');
          summary.hidden = false;
        }
        resolve();
      };
      const cancel = () => finish(false);
      const visibility = () => { if (document.hidden) finish(true); };
      document.addEventListener('visibilitychange', visibility);
      motion.set(container, cancel);
      let start = null;
      const step = (now) => {
        if (!container.isConnected || summary.parentNode !== container) return finish(false);
        if (start === null) start = now;
        const ms = now - start;
        if (ms >= solid.total) return finish(true);
        solid.frame(ms);
        frame = requestAnimationFrame(step);
      };
      if (document.hidden) return finish(true);
      frame = requestAnimationFrame(step);
      // Background tabs pause rAF; never leave the result hidden for long.
      timer = setTimeout(() => finish(true), solid.total + 1500);
    });
  }
  window.TDDice = { roll, stop, preview, clocks, refusal, tierLabel };
})();
