// chars/lineup.js — one armature, three skins.
// The point of this file: POSES is an 11-point skeleton (head, sh, hip, eF, hF, eB, hB, kF, fF, kB, fB).
// A "look" is what you draw ON that skeleton, so the same pose can be rendered three ways and still be
// a fair comparison. Prototype only — nothing here is merged into engine/ or rig2d.js.
import { E, V, mood, S, rr, seg, circle, ring, poly, glow, alpha, shade, mix, rng } from '/engine/core.js';
import { sketchSeg, sketchCircle, hatch } from './sketch.js';
import { POSES, breathe, posesAt, drawFigure } from '/engine/rig2d.js';

import { drawInkBean, drawInkling2 } from './skins2.js';

const P = (pose, k) => pose[k] || [0, 0];

// limb as a round-capped stroke between two pose points
function limb(g, a, b, w, col) { seg(g, [a, b], w, col); }

// ── skin 1: the stock stickman, via the engine's own rig ───────────────────
export function drawStickman(g, o) {
  drawFigure(g, o);
}

// ── skin 2: THE BEAN — capsule body, head fused into it, no neck, no nose ──
// Proportions are fixed numbers on purpose: that is what makes a character repeatable.
export function drawBean(g, o) {
  const pose = o.pose || POSES.stand, s = o.s || 1, f = o.facing || 1;
  const M = mood(o.moodName || 'dusk');
  const ink = S().ink, col = (o.outfit && o.outfit.color) || '#d64a33';
  g.save(); g.translate(o.x, o.y); g.scale(f * s, s);
  const head = P(pose, 'head'), sh = P(pose, 'sh'), hip = P(pose, 'hip');
  const BW = 62, BH = Math.abs(hip[1] - sh[1]) + 78;          // body width/height: fixed
  const cy = (sh[1] + hip[1]) / 2 - 8;
  // shadow, then body capsule, then head fused on top
  g.fillStyle = alpha('#000000', 0.32); g.beginPath();
  g.ellipse(hip[0], 6, 54, 13, 0, 0, 7); g.fill();
  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.fillStyle = col; g.fill();
  rr(g, BW / 2 - 20, cy - BH / 2, 20, BH, 10); g.fillStyle = shade(col, -0.26); g.fill();   // form shadow
  // rim on the lit side
  g.strokeStyle = M.rim; g.lineWidth = 5; g.lineCap = 'round';
  g.beginPath(); g.arc(0, cy, BW / 2 + 1, -1.15, 0.55); g.stroke();
  // legs and arms from the same armature, but as tapered capsules, not lines
  for (const [a, b] of [[hip, P(pose, 'kF')], [P(pose, 'kF'), P(pose, 'fF')],
                        [hip, P(pose, 'kB')], [P(pose, 'kB'), P(pose, 'fB')]])
    limb(g, a, b, 22, shade(col, -0.5));
  for (const [a, b] of [[sh, P(pose, 'eF')], [P(pose, 'eF'), P(pose, 'hF')],
                         [sh, P(pose, 'eB')], [P(pose, 'eB'), P(pose, 'hB')]])
    limb(g, a, b, 17, shade(col, -0.34));
  // mitten hands — no fingers, by design
  circle(g, P(pose, 'hF')[0], P(pose, 'hF')[1], 15, ink);
  circle(g, P(pose, 'hB')[0], P(pose, 'hB')[1], 13, shade(ink, 0.18));
  // head: a disc sitting ON the capsule, no neck gap
  const HR = 46;
  circle(g, head[0], head[1] - 6, HR, ink);
  g.strokeStyle = M.rim; g.lineWidth = 4.5;
  g.beginPath(); g.arc(head[0], head[1] - 6, HR + 1, -2.3, -0.7); g.stroke();
  // face: two dots + one glint each, one mouth. No nose, no ears.
  const ex = head[0] + 16, ey = head[1] - 12;
  const look = o.look || [0, 0];
  for (const dx of [-20, 12]) {
    circle(g, head[0] + dx + look[0] * 5, ey + look[1] * 4, 5.4, '#ffffff');
    circle(g, head[0] + dx + look[0] * 5 + 1.6, ey + look[1] * 4 - 1.6, 1.9, alpha('#ffffff', 0.85));
  }
  const m = o.expr || 'neutral';
  if (m === 'surprised' || m === 'shocked') circle(g, ex - 4, head[1] + 12, 8, alpha('#ffffff', 0.9));
  else if (m === 'smirk') seg(g, [[ex - 16, head[1] + 12], [ex - 2, head[1] + 15]], 5, '#ffffff');
  else if (m === 'talk' || o.talk > 0.3) {
    const h = 4 + o.talk * 11; rr(g, ex - 13, head[1] + 6, 22, h, h / 2); g.fillStyle = alpha('#ffffff', 0.92); g.fill();
  } else seg(g, [[ex - 15, head[1] + 12], [ex + 1, head[1] + 12]], 5, '#ffffff');
  if (m === 'surprised' || m === 'shocked' || (o.brow || 0) > 0.4) {
    const b = o.brow || 1;
    for (const dx of [-22, 10]) seg(g, [[head[0] + dx, ey - 13 - b * 5], [head[0] + dx + 12, ey - 16 - b * 5]], 4.5, '#ffffff');
  }
  g.restore();
}

// ── skin 3: THE INKLING — same bean geometry, drawn as ink on paper ────────
export function drawInkling(g, o) {
  const pose = o.pose || POSES.stand, s = o.s || 1, f = o.facing || 1;
  const ink = '#1c1a17', col = (o.outfit && o.outfit.color) || '#e0894a';
  const seed = Math.round((o.x || 0) * 7 + (o.y || 0) * 3 + 11);   // per-CHARACTER, never per frame
  g.save(); g.translate(o.x, o.y); g.scale(f * s, s);
  const head = P(pose, 'head'), sh = P(pose, 'sh'), hip = P(pose, 'hip');
  const BW = 64, BH = Math.abs(hip[1] - sh[1]) + 80, cy = (sh[1] + hip[1]) / 2 - 8;
  hatch(g, -BW / 2 + 6, cy - BH / 2 + 6, BW - 12, BH - 12, alpha(col, 0.3), seed + 1, 17);
  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2);
  g.strokeStyle = ink; g.lineWidth = 5; g.stroke();
  for (const [a, b] of [[hip, P(pose, 'kF')], [P(pose, 'kF'), P(pose, 'fF')],
                        [hip, P(pose, 'kB')], [P(pose, 'kB'), P(pose, 'fB')]])
    sketchSeg(g, a, b, 9, ink, seed + 2);
  for (const [a, b] of [[sh, P(pose, 'eF')], [P(pose, 'eF'), P(pose, 'hF')],
                         [sh, P(pose, 'eB')], [P(pose, 'eB'), P(pose, 'hB')]])
    sketchSeg(g, a, b, 7, ink, seed + 3);
  sketchCircle(g, P(pose, 'hF')[0], P(pose, 'hF')[1], 14, 6, ink, seed + 4, alpha(col, 0.35));
  sketchCircle(g, P(pose, 'hB')[0], P(pose, 'hB')[1], 12, 6, ink, seed + 5, alpha(col, 0.3));
  sketchCircle(g, head[0], head[1] - 6, 47, 8, ink, seed + 6, '#f8f4ea');
  const ey = head[1] - 12;
  for (const dx of [-19, 11]) circle(g, head[0] + dx, ey, 6.5, ink);
  const m = o.expr || 'neutral';
  if (m === 'surprised' || m === 'shocked') sketchCircle(g, head[0] - 4, head[1] + 14, 8, 5, ink, seed + 7);
  else sketchSeg(g, [head[0] - 16, head[1] + 13], [head[0] + 2, head[1] + (m === 'smirk' ? 9 : 13)], 5, ink, seed + 8);
  if (m === 'surprised' || m === 'shocked') {
    for (const dx of [-24, 8]) sketchSeg(g, [head[0] + dx, ey - 16], [head[0] + dx + 14, ey - 20], 4.5, ink, seed + 9);
  }
  g.restore();
}

export const SKINS = [
  { id: 'stickman', name: 'STICKMAN (control)', draw: (g, o) => drawStickman(g, o) },
  { id: 'inkbean', name: 'B · INK BEAN', draw: (g, o) => drawInkBean(g, o) },
  { id: 'inkling2', name: 'C · INKLING V2', draw: (g, o) => drawInkling2(g, o) },
];
