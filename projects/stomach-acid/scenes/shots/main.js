// shots/main.js — "Why Doesn't Your Stomach Digest Itself?" · 10 shots over 29.9 s.
// Every shot carries a camera move and atmosphere (bible: "no static shots").
import { E, V, registerShot, mood, layer, blurLayer, veil, ease, prog, key, clamp, lerp, seg, circle, ring, rr, poly, glow, alpha, shade, linGrad, radGrad, text, shake, talkAmount, wordTime, rng } from '/engine/core.js';
import { drawFigure, POSES, posesAt, breathe, bigFace, headPos } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import * as UI from '/engine/ui2d.js';
import { kitchen, gutWall, GY, CX, ACID, TISSUE } from '../sets/body.js';
import { YOU } from '../cast.js';

const rimOf = (M, dir) => ({ color: M.rim, dir, w: 4 });

// s001 · "Why doesn't your stomach digest itself?" — wide kitchen, slow push
registerShot('s001', { draw(g, t, info) {
  const cam = { z: 1 + 0.07 * ease.inOut(prog(t, 0, info.dur)), x: -26 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY: gy, M } = kitchen(g, t, cam);
  layer(g, cam, 1, (g) => {
    drawFigure(g, { x: CX() - V(140, 90), y: gy, s: 1.15, facing: 1, outfit: YOU,
      pose: breathe(posesAt(t, [[0, POSES.stand], [1.1, POSES.think]]), t),
      expr: 'neutral', look: [0.1, 0.2], rim: rimOf(M, [-1, -0.3]) });
  });
  FX.dust(g, t, { count: 34, color: '#cfe0ff', a: 0.3 });
} });

// s002 · "It's bathed in acid around pH one point five," — blueprint body + meter
registerShot('s002', { draw(g, t, info) {
  const cam = { z: 1 + 0.05 * ease.inOut(prog(t, 0, info.dur)), x: 18 * ease.inOut(prog(t, 0, info.dur)) };
  UI.blueprint(g, { grid: 60, a: 0.08 });
  layer(g, cam, 1, (g) => {
    UI.lineFigure(g, { x: E.W * 0.32, y: E.H * 0.86, s: V(1.5, 1.2), pose: POSES.stand, color: '#e8f0ff' });
    const sx = E.W * 0.34, sy = E.H * 0.52;
    g.strokeStyle = ACID; g.lineWidth = 9; g.beginPath();
    g.moveTo(sx - 40, sy - 120); g.bezierCurveTo(sx + 120, sy - 100, sx + 110, sy + 90, sx - 30, sy + 110);
    g.bezierCurveTo(sx - 120, sy + 60, sx - 110, sy - 60, sx - 40, sy - 120); g.stroke();
    glow(g, sx, sy, 260, ACID, 0.22 + 0.06 * Math.sin(t * 3));
    UI.callout(g, t, { at: [sx, sy], to: [sx + V(360, 200), sy - V(180, 160)], str: 'GASTRIC ACID', start: 0.5 });
  });
  UI.meter(g, t, { x: E.W * 0.52, y: E.H * 0.78, w: E.W * 0.36, ticks: 26, label: 'pH', color: ACID, start: 0.8, speed: 1.4 });
} });

// s003 · "strong enough to dissolve metal." — a steel nail eaten from the tip up
registerShot('s003', { draw(g, t, info) {
  const cam = { z: 1.15 + 0.05 * t, y: -8 * t };
  const { wallY, cx } = gutWall(g, t, cam, { cells: 9 });
  const ny = wallY - V(150, 120), melt = ease.inOut(prog(t, 0.5, info.dur));
  const shaft = 210 * (1 - melt * 0.7);
  layer(g, cam, 1.2, (g) => {
    g.save(); g.translate(cx, ny); g.rotate(-0.12);
    g.fillStyle = '#cfd8e4'; g.fillRect(-46, -150, 92, 16);                       // flat head
    g.fillStyle = linGrad(g, -9, 0, 9, 0, ['#e6edf6', '#9aa8ba', '#6f7d8f']);     // eaten from the tip
    g.fillRect(-9, -134, 18, shaft);
    poly(g, [[-9, -134 + shaft], [9, -134 + shaft], [0, -134 + shaft + 26]], '#8f9dae');
    g.restore();
    for (let i = 0; i < 16; i++) {
      const a = rng(i * 7 + 3)() * 6.28, d = 30 + rng(i * 13)() * 110 * melt;
      const px = cx + Math.cos(a) * d, py = ny - 134 + shaft + Math.sin(a) * d * 0.5 + melt * 40;
      FX.sparkle(g, px, py, 14 * (1 - melt * 0.7), ACID, 0.85 * (1 - melt));
    }
    glow(g, cx, ny - 134 + shaft, 200 * (0.4 + melt), ACID, 0.35);
    UI.callout(g, t, { at: [cx + 60, ny - 134 + shaft], to: [cx + V(430, 330), ny - V(240, 200)], str: 'STEEL NAIL', start: 0.3 });
  });
  UI.badge(g, { str: 'pH 1.5', a: ease.out(prog(t, 0.3, 0.7)) });
  FX.rings(g, cx, ny - 130 + shaft, t, { count: 2, r0: 40, r1: 240, speed: 0.9, color: ACID, a: 0.3 });
} });

// s004 · "So what protects it?" — giant face, the question lands
registerShot('s004', { draw(g, t, info) {
  blurLayer(g, 12, (g) => kitchen(g, 0, { z: 1.7, x: -140, y: -180 }));
  veil(g, '#0a0d1c', 0.4);
  const M = mood('night'), r = V(300, 330) * (1 + 0.05 * t);
  const talk = talkAmount(info.globalT, 8.68, 10.1);
  bigFace(g, CX(), E.H * V(0.58, 0.52), r, { outfit: YOU, expr: 'surprised', talk,
    rimColor: M.rim, rimSide: -1, blink: (t % 2.6) > 2.5 });
  FX.rings(g, CX(), E.H * V(0.58, 0.52), t, { count: 3, r0: r * 1.1, r1: r * 1.7, color: '#cfe0ff', a: 0.2 });
} });

// s005 · "A lining that rebuilds constantly." — the barrier wall, wide reveal
registerShot('s005', { draw(g, t, info) {
  const cam = { z: 1.12 - 0.1 * ease.inOut(prog(t, 0, info.dur)), x: 40 * (1 - ease.inOut(prog(t, 0, info.dur))) };
  gutWall(g, t, cam, { cells: 9 });
  UI.callout(g, t, { at: [CX() + V(300, 200), E.H * 0.55], to: [CX() + V(620, 420), E.H * 0.34], str: 'MUCOSAL LINING', start: 0.4 });
  FX.dust(g, t, { count: 26, color: ACID, a: 0.2 });
} });

// s006 · "Every few days, your stomach grows a brand new surface, cell by cell," — cells dividing
registerShot('s006', { draw(g, t, info) {
  const cam = { z: 1 + 0.04 * t };
  const { wallY, cx, span, r } = gutWall(g, t, cam, { cells: 9 });
  layer(g, cam, 1.1, (g) => {
    for (let i = 0; i < 9; i++) {
      const x = cx - span / 2 + (i + 0.5) * (span / 9);
      const born = clamp((t - 0.2 - i * 0.22) / 0.5);
      if (born <= 0) continue;
      const y = wallY + r * 2.3;
      circle(g, x, y, r * 0.85 * ease.outBack(born), alpha('#ffd9e0', 0.85));
      ring(g, x, y, r * 0.85 * ease.outBack(born), 4, shade(TISSUE, 0.2));
      if (born < 1) FX.rings(g, x, y, t - 0.2 - i * 0.22, { count: 1, r0: r, r1: r * 2.2, speed: 1.2, color: '#ffffff', a: 0.4 });
    }
  });
  UI.callout(g, t, { at: [cx - span / 2 + 4.5 * (span / 9), wallY + r * 2.3], to: [cx + V(430, 320), wallY - V(150, 130)], str: 'NEW CELL', start: 1.0 });
} });

// s007 · "and sheds the old one." — old cells lift off and drift into the acid
registerShot('s007', { draw(g, t, info) {
  const { wallY, cx, span, r } = gutWall(g, t, { z: 1.02, x: -20 * ease.inOut(prog(t, 0, info.dur)) }, { cells: 9 });
  layer(g, { z: 1.02 }, 1.2, (g) => {
    for (let i = 0; i < 11; i++) {
      const seed = i * 31 + 5, x0 = cx - span / 2 + rng(seed)() * span;
      const p = prog(t, 0.1 + rng(seed + 1)() * 1.2, 2.6);
      if (p <= 0) continue;
      const x = x0 + Math.sin(p * 3 + seed) * 60, y = wallY + r - p * V(420, 340);
      g.save(); g.globalAlpha = 1 - p * 0.85; circle(g, x, y, r * 0.7, shade(TISSUE, -0.1)); g.restore();
    }
  });
  FX.drops(g, t, { count: 22, color: ACID, rMax: 7, drift: 4 });
} });

// s008 · "But when that rebuild slows, an ulcer, or too many painkillers," — the gap opens
registerShot('s008', { draw(g, t, info) {
  const cam = { z: 1 + 0.05 * ease.inOut(prog(t, 0, info.dur)), r: -0.015 + 0.01 * t };
  gutWall(g, t, cam, { cells: 9, breach: 4 });
  const open = ease.out(prog(t, 0.2, 0.9));
  UI.callout(g, t, { at: [CX(), E.H * 0.58], to: [CX() - V(430, 300), E.H * 0.34], str: 'BARRIER BREACHED', color: '#ff8fa0', start: 0.6 });
  layer(g, cam, 1.3, (g) => {
    for (let i = 0; i < 5; i++) {                                     // pills falling in
      const p = prog(t, 0.3 + i * 0.18, 1.9);
      if (p <= 0 || p >= 1) continue;
      const x = CX() + (i - 2) * V(70, 50), y = E.H * 0.1 + p * V(560, 460);
      g.save(); g.translate(x, y); g.rotate(p * 3 + i);
      rr(g, -26, -11, 52, 22, 11); g.fillStyle = alpha('#f2efe6', 0.9 * (1 - p)); g.fill(); g.restore();
    }
  });
  FX.rings(g, CX(), E.H * 0.58, t, { count: 2, r0: 90, r1: 340, speed: 0.6, color: '#d62839', a: 0.3 * open });
} });

// s009 · "the acid reaches the tissue underneath." — tight on the breach, acid pours, damage spreads
registerShot('s009', { draw(g, t, info) {
  const hit = 0.75, cam = { z: 1.75, x: 150, y: -60 };
  const { wallY, cx, span, r } = gutWall(g, t, cam, { cells: 9, breach: 4 });
  const bx = cx - span / 2 + 4.5 * (span / 9);
  const [sx, sy] = shake(t, t > hit ? 14 * Math.exp(-(t - hit) * 2.0) : 0, 26);
  g.save(); g.translate(sx, sy);
  layer(g, cam, 1.2, (g) => {
    const top = wallY - V(300, 240), depth = r * 3.6 * ease.in(prog(t, hit, hit + 1.2));
    const spread = V(150, 120) + ease.out(prog(t, hit, hit + 1.6)) * V(330, 260);
    seg(g, [[bx, top], [bx, wallY + depth]], 74, alpha(ACID, 0.9));                 // wide column
    seg(g, [[bx, top], [bx, wallY + depth]], 26, alpha('#f4ffc0', 0.95));           // hot core
    for (let i = 0; i < 26; i++) {
      const p = (t * 1.7 + i * 0.07) % 1;
      circle(g, bx + Math.sin(i * 5.1) * 34, top + p * (wallY - top + depth), 7, alpha(ACID, 0.85 - p * 0.3));
    }
    g.fillStyle = radGrad(g, bx, wallY + depth, 0, spread, [[0, alpha('#d62839', 0.75)], [0.55, alpha('#8c1b2a', 0.5)], [1, alpha('#170d16', 0)]]);
    g.fillRect(bx - spread, wallY + depth - spread, spread * 2, spread * 2);         // burned tissue
    glow(g, bx, wallY + depth, spread * 1.3, '#d62839', 0.55 * clamp((t - hit) * 1.3));
    FX.rings(g, bx, wallY + depth, t - hit, { count: 3, r0: 60, r1: 420, speed: 1.3, color: '#ff6b7d', a: 0.55 * clamp((t - hit) * 2) });
  });
  g.restore();
  FX.speedLines(g, t, { cx: bx, cy: wallY, count: 34, a: 0.35 * clamp((t - hit) * 3) });
  UI.callout(g, t, { at: [bx, wallY + r * 2], to: [bx - V(430, 340), wallY + V(330, 260)], str: 'LIVING TISSUE', color: '#ff8fa0', start: hit + 0.4 });
} });

// s010 · "And then it does what you'd expect. It digests you." — face, then the question
registerShot('s010', { draw(g, t, info) {
  const M = mood('midnight');
  if (t < 2.2) {
    blurLayer(g, 14, (g) => gutWall(g, 0, { z: 1.9, y: -E.H * 0.2 }, { cells: 9, breach: 4 }));
    veil(g, '#0b0a14', 0.45);
    const r = V(310, 340) * (1 + 0.04 * t);
    const talk = talkAmount(info.globalT, 25.44, 27.2);
    bigFace(g, CX(), E.H * V(0.56, 0.5), r, { outfit: YOU, expr: t > 1.4 ? 'scared' : 'neutral', talk,
      rimColor: '#ff9a86', rimSide: 1, blink: (t % 2.4) > 2.3 });
    if (t > 1.9) FX.speedLines(g, t, { cx: CX(), cy: E.H * 0.5, count: 30, a: 0.4 });
  } else {
    const cam = { z: 1 + 0.05 * ease.inOut(prog(t, 2.2, info.dur)) };
    layer(g, cam, 1, (g) => {
      drawFigure(g, { x: CX() - V(260, 180), y: E.H * 0.86, s: 1.1, facing: 1, outfit: YOU,
        pose: breathe(POSES.crossArms, t), expr: 'neutral', rim: rimOf(M, [-1, -0.3]) });
    });
    FX.dust(g, t, { count: 24, color: '#cfe0ff', a: 0.22 });
    UI.endScreen(g, t - 2.2, { question: 'Would you trust that lining today?', cast: [YOU] });
  }
} });
