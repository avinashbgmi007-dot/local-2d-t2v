// chars/sketch.js  — hand-inked drawing primitives, seeded so every frame of a shot agrees.
// The seed must key off the CHARACTER/shape identity, never the frame number, or the lines boil.
import { V, alpha, rng } from '/engine/core.js';

export function sketchSeg(g, a, b, w, col, seed, rough = 1) {
  const r = rng(seed);
  const n = Math.max(4, Math.round(Math.hypot(b[0] - a[0], b[1] - a[1]) / 26));
  const nx = -(b[1] - a[1]), ny = (b[0] - a[0]);
  const len = Math.hypot(nx, ny) || 1;
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const amp = Math.sin(t * Math.PI) * 2.6 * rough;
    const off = (i === 0 || i === n) ? 0 : (r() * 2 - 1) * amp;
    pts.push([a[0] + (b[0] - a[0]) * t + nx / len * off, a[1] + (b[1] - a[1]) * t + ny / len * off]);
  }
  g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.stroke();
}

export function sketchCircle(g, x, y, rad, w, col, seed, fill) {
  const r = rng(seed);
  const n = 26;
  g.beginPath();
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    const wob = (i === 0 || i === n) ? 1 : 1 + (r() * 2 - 1) * 0.035;
    const px = x + Math.cos(a) * rad * wob, py = y + Math.sin(a) * rad * wob;
    i ? g.lineTo(px, py) : g.moveTo(px, py);
  }
  g.closePath();
  if (fill) { g.fillStyle = fill; g.fill(); }
  g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.stroke();
}

export function hatch(g, x, y, w, h, col, seed, gap = 9) {
  const r = rng(seed);
  g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip();
  g.strokeStyle = col; g.lineWidth = 2.4;
  for (let i = -h; i < w; i += gap) {
    const j1 = (r() * 2 - 1) * 2, j2 = (r() * 2 - 1) * 2;
    g.beginPath(); g.moveTo(x + i + j1, y + h + j2); g.lineTo(x + i + h + j1, y + j2); g.stroke();
  }
  g.restore();
}
