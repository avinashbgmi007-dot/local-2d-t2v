// sets/body.js — two reusable environments: a night kitchen (the human beats) and
// an abstract gut-wall cross-section (the mechanism beats). Anchored to GY / CX per the bible.
import { E, V, mood, layer, backdrop, rr, seg, circle, ring, poly, linGrad, radGrad, glow, alpha, shade, mix, text } from '/engine/core.js';
import * as FX from '/engine/fx2d.js';

export const GY = () => E.H * V(0.8, 0.68);
export const CX = () => E.W / 2;

// ── kitchen at night: one cold practical over the counter, moon in the window ──────
export function kitchen(g, t, cam, o = {}) {
  const M = mood('night'), gy = GY(), cx = CX();
  const wall = shade(M.wall, -0.25), dark = shade(M.wall, -0.6);
  layer(g, cam, 0.15, (g) => {
    backdrop(g, M.sky);
    FX.stars(g, t, { count: 40, a: 0.5 });
    FX.moon(g, cx + V(680, 300), E.H * V(0.18, 0.12), 54);
  });
  layer(g, cam, 0.55, (g) => {                                       // back wall + window
    g.fillStyle = linGrad(g, 0, 0, 0, gy, [wall, dark]); g.fillRect(-E.W, -E.H, E.W * 4, gy + E.H);
    const wx = cx - V(560, 260), wy = E.H * V(0.16, 0.1), ww = V(360, 300), wh = V(300, 380);
    FX.windowFrame(g, { x: wx, y: wy, w: ww, h: wh, cols: 2, rows: 2, frame: dark, bar: 8 }, (g, x, y, w, h) => {
      g.fillStyle = linGrad(g, 0, y, 0, y + h, [mix(M.sky[1], '#20243f', 0.5), M.sky[0]]); g.fillRect(x, y, w, h);
    });
    glow(g, wx + ww / 2, wy + wh / 2, V(420, 500), '#8fa8d8', 0.1);
    FX.godRays(g, wx + ww / 2, wy + wh / 2, { count: 7, len: V(900, 1100), spread: 0.5, color: '#9fb6e0', a: 0.07, angle: 1.2 });
  });
  layer(g, cam, 0.85, (g) => {                                       // counter + floor
    const ch = V(150, 130), cy = gy - ch;
    g.fillStyle = shade(dark, 0.1); g.fillRect(cx - V(1100, 700), cy, V(2200, 1400), ch);
    g.fillStyle = shade(dark, 0.34); g.fillRect(cx - V(1100, 700), cy, V(2200, 1400), 16);
    g.fillStyle = linGrad(g, 0, gy, 0, gy + 500, [shade(M.floor, -0.05), shade(M.dark, -0.25)]);
    g.fillRect(-E.W, gy, E.W * 4, E.H * 2);
    FX.floorLines(g, gy, gy + 520, 'rgba(0,0,0,.28)', 0.09);
    const lx = cx + V(300, 180), ly = cy - V(120, 90);
    seg(g, [[lx, E.H * V(0.1, 0.06)], [lx, ly]], 8, dark);
    poly(g, [[lx - 46, ly], [lx + 46, ly], [lx + 30, ly + 30], [lx - 30, ly + 30]], shade(dark, 0.2));
    glow(g, lx, ly + 40, V(520, 620), M.practical, 0.5);
    FX.lightCone(g, lx, ly + 40, { w: V(560, 420), h: gy - ly, color: M.practical, a: 0.1 });
    FX.pool(g, lx, gy, V(320, 240), V(60, 44), M.practical, 0.22);
  });
  return { GY: gy, CX: cx, M };
}

// ── gut wall: a cross-section. acid above, a mucus line, one row of epithelial cells ──
export const ACID = '#c8e85a';
export const TISSUE = '#e57a8a';
export function gutWall(g, t, cam, o = {}) {
  const M = mood('midnight'), cx = CX(), top = E.H * V(0.30, 0.24), wallY = E.H * V(0.58, 0.52);
  const cells = o.cells ?? 9, breach = o.breach ?? null;            // breach = index of the missing cell
  const span = V(1500, 900), r = span / cells / 2.35;
  layer(g, cam, 0.3, (g) => {
    backdrop(g, ['#0b1024', '#141a3a', '#1d2246']);
    g.fillStyle = linGrad(g, 0, 0, 0, wallY, [[0.0, ACID], [0.14, ACID], [0.9, shade(ACID, -0.5)]]);
    g.fillRect(-E.W, -E.H, E.W * 4, wallY);
    for (let i = 0; i < 26; i++) {                                  // slow acid swirl
      const px = cx + Math.sin(i * 2.7 + t * 0.5) * V(820, 500), py = ((i * 137 + t * 26) % (wallY + 200)) - 100;
      circle(g, px, py, 3 + (i % 4), alpha(ACID, 0.35));
    }
    FX.godRays(g, cx, -200, { count: 5, len: wallY * 1.4, spread: 0.35, color: ACID, a: 0.06, angle: 1.57 });
  });
  layer(g, cam, 1, (g) => {
    g.fillStyle = alpha('#f6f2e6', 0.5);                             // mucus barrier line
    g.fillRect(-E.W, wallY - 12, E.W * 4, 12);
    for (let i = 0; i < cells; i++) {
      const x = cx - span / 2 + (i + 0.5) * (span / cells);
      if (breach !== null && i === breach) continue;
      const y = wallY + r + Math.sin(t * 1.4 + i) * 5;
      circle(g, x, y, r, TISSUE);
      circle(g, x - r * 0.28, y - r * 0.3, r * 0.3, alpha('#ffffff', 0.22));
      ring(g, x, y, r, 5, shade(TISSUE, -0.35));
      circle(g, x, y + r * 0.35, r * 0.34, shade(TISSUE, -0.3));      // nucleus
    }
    if (breach !== null) {                                            // the gap acid falls into
      const x = cx - span / 2 + (breach + 0.5) * (span / cells);
      g.fillStyle = shade('#1a0f18', 0.1); g.fillRect(x - r, wallY, r * 2, r * 3);
      ring(g, x, wallY + r, r * 1.15, 6, '#d62839');
      glow(g, x, wallY + r * 1.6, r * 3, '#d62839', 0.35);
    }
    g.fillStyle = linGrad(g, 0, wallY + r * 2.4, 0, E.H, [shade(TISSUE, -0.55), '#170d16']);
    g.fillRect(-E.W, wallY + r * 2.2, E.W * 4, E.H);
  });
  return { wallY, cx, cells, r, span, M };
}
