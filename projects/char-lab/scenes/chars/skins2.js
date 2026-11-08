// chars/skins2.js — options B and C, built from the v1 feedback.
// B · INK BEAN   : the bean silhouette that read well, but hand-inked outline + flat colour, no hatch.
// C · INKLING V2 : a real ink illustration — paper ground under the line, hatch used only as shadow-side
//                  shading, and rim light so the silhouette separates from a dark set.
import { E, V, mood, S, rr, seg, circle, ring, poly, glow, alpha, shade, mix, rng } from '/engine/core.js';
import { POSES, breathe, posesAt, drawFigure } from '/engine/rig2d.js';
import { sketchSeg, sketchCircle, hatch } from './sketch.js';

const P = (pose, k) => pose[k] || [0, 0];


// ── signature accessory: a scarf. Chosen because it is the only marker that MOVES — the tail
//    swings on turns and at rest, so it adds life instead of only colour. Identity colour is fixed
//    here and is deliberately NOT the outfit colour, so a style change cannot erase it.
export const SCARF = '#f2b26b';
export function drawScarf(g, pose, t, seed, ink) {
  const head = P(pose, 'head');
  const ny = head[1] + 44, nx = head[0] - 4;                 // neck ring, just under the head
  const sway = Math.sin(t * 2.1) * 8 + Math.sin(t * 0.87) * 4;
  const len = 62 + Math.sin(t * 1.3) * 6;                    // short: hangs, never crosses the body
  // collar band across the neck
  g.strokeStyle = SCARF; g.lineCap = 'round'; g.lineWidth = 20;
  g.beginPath(); g.arc(nx, ny - 8, 30, 0.35, Math.PI - 0.35); g.stroke();
  // tail down the near side only
  const pts = [[nx + 20, ny + 4], [nx + 24 + sway * 0.35, ny + len * 0.4],
               [nx + 18 + sway * 0.8, ny + len * 0.78], [nx + 10 + sway, ny + len]];
  g.lineWidth = 19; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.stroke();
  g.strokeStyle = shade(SCARF, -0.28); g.lineWidth = 5;
  g.beginPath(); g.moveTo(pts[1][0] + 5, pts[1][1]); g.lineTo(pts[3][0] + 4, pts[3][1]); g.stroke();
  for (const dx of [-6, 2, 9])
    sketchSeg(g, [pts[3][0] + dx, ny + len], [pts[3][0] + dx + sway * 0.1, ny + len + 15], 4, SCARF, seed + 61 + dx, 1.2);
}

export function drawInkBean(g, o) {
  const pose = o.pose || POSES.stand, s = o.s || 1, f = o.facing || 1;
  const M = mood(o.moodName || 'dusk');
  const ink = '#15131a', col = (o.outfit && o.outfit.color) || '#2f9e8f';
  const seed = Math.round((o.x || 0) * 7 + (o.y || 0) * 3 + 11);
  g.save(); g.translate(o.x, o.y); g.scale(f * s, s);
  const head = P(pose, 'head'), sh = P(pose, 'sh'), hip = P(pose, 'hip');
  const BW = 64, BH = Math.abs(hip[1] - sh[1]) + 80, cy = (sh[1] + hip[1]) / 2 - 8;
  g.fillStyle = alpha('#000000', 0.35); g.beginPath(); g.ellipse(hip[0], 6, 56, 13, 0, 0, 7); g.fill();

  for (const [a, b] of [[hip, P(pose, 'kF')], [P(pose, 'kF'), P(pose, 'fF')],
                        [hip, P(pose, 'kB')], [P(pose, 'kB'), P(pose, 'fB')]]) {
    sketchSeg(g, a, b, 24, shade(col, -0.55), seed + 20, 0.5);
    sketchSeg(g, [a[0] - 9, a[1]], [b[0] - 9, b[1]], 5, M.rim, seed + 21, 0.5);
  }

  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.fillStyle = col; g.fill();
  g.save(); g.beginPath(); rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.clip();
  g.fillStyle = alpha('#000000', 0.15); g.fillRect(-BW / 2, cy - BH / 2, BW * 0.32, BH); g.restore();
  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.strokeStyle = ink; g.lineWidth = 9; g.stroke();

  for (const [a, b] of [[sh, P(pose, 'eF')], [P(pose, 'eF'), P(pose, 'hF')]])
    sketchSeg(g, a, b, 19, shade(col, -0.2), seed + 23, 0.5);
  sketchCircle(g, P(pose, 'hF')[0], P(pose, 'hF')[1], 15, 8, ink, seed + 24, col);
  const HR = 47, ey = head[1] - 12, look = o.look || [0, 0];
  sketchCircle(g, head[0], head[1] - 6, HR, 9, ink, seed + 26, '#101018');
  g.strokeStyle = M.rim; g.lineWidth = 6; g.lineCap = 'round';
  g.beginPath(); g.arc(head[0], head[1] - 6, HR + 4, -2.35, -0.75); g.stroke();
  for (const dx of [-19, 11]) {
    circle(g, head[0] + dx + look[0] * 5, ey + look[1] * 4, 6.2, '#ffffff');
    circle(g, head[0] + dx + look[0] * 5 + 2, ey + look[1] * 4 - 2, 2.1, alpha('#ffffff', 0.85));
  }
  if (o.scarf !== false) drawScarf(g, pose, o.t || 0, seed, ink);
  const m = o.expr || 'neutral';
  if (m === 'surprised' || m === 'shocked') {
    sketchCircle(g, head[0] - 4, head[1] + 14, 9, 6, '#ffffff', seed + 27);
    for (const dx of [-24, 8]) sketchSeg(g, [head[0] + dx, ey - 17], [head[0] + dx + 14, ey - 21], 5, '#ffffff', seed + 29);
  } else {
    sketchSeg(g, [head[0] - 16, head[1] + 13], [head[0] + 2, head[1] + (m === 'smirk' ? 9 : 13)], 5.5, '#ffffff', seed + 28);
    if ((o.brow || 0) > 0.4)
      for (const dx of [-24, 8]) sketchSeg(g, [head[0] + dx, ey - 15], [head[0] + dx + 14, ey - 19], 5, '#ffffff', seed + 29);
  }
  g.restore();
}

export function drawInkling2(g, o) {
  const pose = o.pose || POSES.stand, s = o.s || 1, f = o.facing || 1;
  const M = mood(o.moodName || 'dusk');
  const ink = '#1b1915', paper = '#efe7d6', col = (o.outfit && o.outfit.color) || '#e0894a';
  const seed = Math.round((o.x || 0) * 7 + (o.y || 0) * 3 + 11);
  g.save(); g.translate(o.x, o.y); g.scale(f * s, s);
  const head = P(pose, 'head'), sh = P(pose, 'sh'), hip = P(pose, 'hip');
  const BW = 66, BH = Math.abs(hip[1] - sh[1]) + 82, cy = (sh[1] + hip[1]) / 2 - 8;
  g.fillStyle = alpha('#000000', 0.4); g.beginPath(); g.ellipse(hip[0], 6, 58, 14, 0, 0, 7); g.fill();

  for (const [a, b] of [[hip, P(pose, 'kF')], [P(pose, 'kF'), P(pose, 'fF')],
                        [hip, P(pose, 'kB')], [P(pose, 'kB'), P(pose, 'fB')]]) {
    sketchSeg(g, a, b, 22, paper, seed + 30, 0.7);
    sketchSeg(g, a, b, 8, shade(col, -0.45), seed + 31, 0.7);
  }

  g.save(); g.beginPath(); rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.clip();
  g.fillStyle = alpha(paper, 0.93); g.fillRect(-BW / 2, cy - BH / 2, BW, BH);
  g.fillStyle = alpha(col, 0.42); g.fillRect(-BW / 2, cy - BH / 2, BW, BH);
  hatch(g, BW * 0.16, cy - BH / 2, BW * 0.34, BH, alpha(ink, 0.3), seed + 35, 16);
  g.restore();
  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.strokeStyle = ink; g.lineWidth = 9; g.stroke();

  for (const [a, b] of [[sh, P(pose, 'eF')], [P(pose, 'eF'), P(pose, 'hF')]]) {
    sketchSeg(g, a, b, 20, paper, seed + 36, 0.7);
    sketchSeg(g, a, b, 8, ink, seed + 37, 0.7);
  }
  sketchCircle(g, P(pose, 'hF')[0], P(pose, 'hF')[1], 15, 8, ink, seed + 38, paper);
  const HR = 48, ey = head[1] - 12, look = o.look || [0, 0];
  sketchCircle(g, head[0], head[1] - 6, HR, 9, ink, seed + 40, paper);
  g.strokeStyle = M.rim; g.lineWidth = 5; g.lineCap = 'round';
  g.beginPath(); g.arc(head[0], head[1] - 6, HR + 5, -2.3, -0.8); g.stroke();
  for (const dx of [-19, 11]) circle(g, head[0] + dx + look[0] * 5, ey + look[1] * 4, 6.5, ink);
  const m = o.expr || 'neutral';
  if (m === 'surprised' || m === 'shocked') {
    sketchCircle(g, head[0] - 4, head[1] + 15, 9, 6, ink, seed + 41);
    for (const dx of [-25, 7]) sketchSeg(g, [head[0] + dx, ey - 18], [head[0] + dx + 15, ey - 22], 5, ink, seed + 42);
  } else {
    sketchSeg(g, [head[0] - 16, head[1] + 14], [head[0] + 2, head[1] + (m === 'smirk' ? 10 : 14)], 5.5, ink, seed + 43);
    if ((o.brow || 0) > 0.4)
      for (const dx of [-25, 7]) sketchSeg(g, [head[0] + dx, ey - 16], [head[0] + dx + 15, ey - 20], 5, ink, seed + 42);
  }
  g.restore();
}
