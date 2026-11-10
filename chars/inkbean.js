// chars/inkbean.js — THE character. Option B, "Ink Bean": a capsule body with a fused head, flat
// colour, hand-inked outline and a warm rim. This file is the single source of truth for the look;
// every project imports it rather than carrying its own copy, because two copies is how a series
// drifts. Nothing here touches engine/ — it is drawn on top of the engine's primitives.
//
// Face control is CONTINUOUS, not a list of presets. A turn of the face has to interpolate, and
// picking between 18 named expressions snaps. `face` takes:
//   brow       0..1  raised (1 = up/alarmed, 0 = level, negative = lowered/dreading)
//   browTilt  -1..1  inner ends down (anger) .. up (sad/worried)
//   eyeWide    0..1  sclera radius
//   mouthOpen  0..1  vertical gape
//   mouthCurve -1..1  frown .. smile
//   look      [x,y]  gaze direction, screen space
//   blink      0..1  1 = shut
//   talk       0..1  speech amplitude, only used when mouthOpen is not set explicitly
import { E, V, mood, S, rr, seg, circle, ring, alpha, shade, mix, rng, linGrad } from '/engine/core.js';
import { POSES } from '/engine/rig2d.js';
import { sketchSeg, sketchCircle } from '/chars/sketch.js';
import { drawMarker } from '/chars/markers.js';

const P = (pose, k) => pose[k] || [0, 0];
const INK = '#15131a';
const HEAD_INK = '#1d1a24';   // lifted from #101018: warm-dark so it separates from cool navy

// body geometry — fixed numbers, so the silhouette is identical everywhere
const BW = 64;
const HEAD_R = 47;

// The mark travels with the character object, not the shot: cast.js declares it once and every
// render of that character gets it, in wide shots and close-ups alike. A shot may still override
// `back` when it knows which way the character is turned.
function markerOf(o) {
  const m = (o.outfit && o.outfit.marker) || o.marker;
  if (!m) return null;
  return typeof m === 'string' ? { kind: m } : m;
}

function faceOf(o) {
  const f = o.face || {};
  const m = o.expr || 'neutral';
  const preset = { neutral:   { brow: 0.15, browTilt: 0,    eyeWide: 0.10, mouthOpen: 0.05, mouthCurve: 0.15 },
                  surprised: { brow: 0.85, browTilt: 0.35, eyeWide: 0.85, mouthOpen: 0.70, mouthCurve: 0.00 },
                  shocked:   { brow: 1.00, browTilt: 0.45, eyeWide: 1.00, mouthOpen: 0.90, mouthCurve: -0.10 },
                  sad:       { brow: 0.30, browTilt: -0.75, eyeWide: 0.05, mouthOpen: 0.05, mouthCurve: -0.60 },
                  worried:   { brow: 0.55, browTilt: -0.55, eyeWide: 0.35, mouthOpen: 0.10, mouthCurve: -0.35 },
                  smirk:     { brow: 0.20, browTilt: 0.10, eyeWide: 0.05, mouthOpen: 0.05, mouthCurve: 0.55 },
                  angry:     { brow: 0.10, browTilt: 0.85, eyeWide: 0.20, mouthOpen: 0.10, mouthCurve: -0.55 } }[m]
               || { brow: 0.15, browTilt: 0, eyeWide: 0.10, mouthOpen: 0.05, mouthCurve: 0.15 };
  const out = {};
  for (const k in preset) out[k] = (k in f) ? f[k] : preset[k];
  out.look = f.look || o.look || [0, 0];
  out.blink = f.blink !== undefined ? f.blink : (o.blink ? 1 : 0);
  out.mouthOpen = Math.max(out.mouthOpen, (o.talk || 0) * 0.5);
  return out;
}

// the head, drawn once and reused at any scale — a close-up is literally the same face
function drawHead(g, cx, cy, R, f, M, seed, rimSide, marker, col) {
  // A marker is either BEHIND the skull (a bun, which the head must occlude) or OVER the face
  // (spectacles, which sit on it). Ordering is the marker's business, not the shot's.
  const mk = marker ? { back: marker.back === undefined ? -1 : marker.back, kind: marker.kind, col } : null;
  if (mk) drawMarker(g, mk.kind, cx, cy, R, mk.col, mk.back, 'behind');
  sketchCircle(g, cx, cy, R, R * 0.13, INK, seed, HEAD_INK);
  // A dark head on a dark set has almost no edge. A faint full-circle rim lifts the
  // whole silhouette without brightening the face, which would break the ink style.
  g.save(); g.strokeStyle = alpha(M.rim, 0.22); g.lineWidth = R * 0.05;
  g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.stroke(); g.restore();
  g.save(); g.strokeStyle = M.rim; g.lineWidth = R * 0.12; g.lineCap = 'round';
  // radius R, not R*1.09 — the rim straddles the silhouette instead of floating off it as a banana
  g.beginPath(); g.arc(cx, cy, R, rimSide < 0 ? -2.35 : -0.85, rimSide < 0 ? -0.75 : 0.75); g.stroke();
  g.restore();

  const ey = cy - R * 0.16, sep = R * 0.33;        // centre-to-centre half distance, was 0.21R
  const eyeR = R * (0.150 + 0.085 * f.eyeWide);   // sized so two eyes + gap always fit inside the head
  const lid = R * 0.115 * (1 - f.blink);
  for (const dx of [-sep, sep]) {
    const px = cx + dx + f.look[0] * R * 0.09, py = ey + f.look[1] * R * 0.07;
    circle(g, px, py, eyeR, '#ffffff');
    if (lid > eyeR * 0.25) {
      circle(g, px + eyeR * 0.30, py - eyeR * 0.32, eyeR * 0.30, alpha('#ffffff', 0.92));
      circle(g, px - eyeR * 0.22, py + eyeR * 0.26, eyeR * 0.13, alpha('#ffffff', 0.45));
    }
    if (f.blink > 0.02) {                       // lid sweeps down over the eye, it is not erased
      g.save();
      g.beginPath(); g.arc(px, py, eyeR * 1.02, 0, 7); g.clip();
      const drop = eyeR * 2.1 * f.blink;
      g.fillStyle = HEAD_INK; g.fillRect(px - eyeR * 1.1, py - eyeR * 1.1, eyeR * 2.2, drop);
      g.strokeStyle = alpha('#ffffff', 0.55); g.lineWidth = eyeR * 0.10; g.lineCap = 'round';
      g.beginPath(); g.moveTo(px - eyeR * 0.86, py - eyeR * 1.1 + drop);
      g.quadraticCurveTo(px, py - eyeR * 1.1 + drop + eyeR * 0.30, px + eyeR * 0.86, py - eyeR * 1.1 + drop);
      g.stroke();
      g.restore();
    }
  }
  // brows: height plus inner/outer tilt, both continuous
  const bh = cy - R * (0.30 + 0.20 * f.brow);
  const tilt = f.browTilt * R * 0.10;
  for (const sgn of [-1, 1]) {
    const bx = cx + sgn * (sep * 1.02 + R * 0.05);   // brow sits just outside each eye
    sketchSeg(g, [bx - sgn * R * 0.16, bh + tilt],
                     [bx + sgn * R * 0.16, bh - tilt], R * 0.075, '#ffffff', seed + sgn, 0.35);
  }
  // mouth: an ellipse whose height is mouthOpen and whose top/bottom arc carries the curve.
  // Speech must stay WIDER than tall — an oval taller than it is wide reads as a scream, not a word.
  const my = cy + R * 0.42, mw = R * (0.30 + 0.10 * (1 - f.mouthOpen));
  if (f.mouthOpen > 0.22) {
    const mh = R * (0.05 + 0.26 * f.mouthOpen);
    g.beginPath(); g.ellipse(cx - R * 0.02, my, mw * 0.78, mh * 0.62, 0, 0, 7);
    g.fillStyle = alpha('#ffffff', 0.94); g.fill();
    g.strokeStyle = INK; g.lineWidth = R * 0.055; g.stroke();
  } else {
    const c = f.mouthCurve * R * 0.20;
    g.strokeStyle = '#ffffff'; g.lineWidth = R * 0.07; g.lineCap = 'round';
    g.beginPath();
    g.moveTo(cx - mw * 0.7, my - c * 0.35);
    g.quadraticCurveTo(cx - R * 0.02, my + c, cx + mw * 0.7, my - c * 0.35);
    g.stroke();
  }
  if (mk) drawMarker(g, mk.kind, cx, cy, R, mk.col, mk.back, 'over');
}

export function drawInkBean(g, o) {
  const pose = o.pose || POSES.stand, s = o.s || 1, f = o.facing === undefined ? 1 : o.facing;
  const yx = o.yx === undefined ? 1 : o.yx;   // horizontal squash for a turn: 0.3 = facing away, 1 = front
  const M = mood(o.moodName || 'dusk'), col = (o.outfit && o.outfit.color) || '#2f9e8f';
  const seed = Math.round((o.seedBase || 0) * 131 + (o.x || 0) * 7 + (o.y || 0) * 3 + 11);
  const face = faceOf(o);
  g.save(); g.translate(o.x, o.y); g.scale(f * s * yx, s);
  const head = P(pose, 'head'), sh = P(pose, 'sh'), hip = P(pose, 'hip');
  const BH = Math.abs(hip[1] - sh[1]) + 80, cy = (sh[1] + hip[1]) / 2 - 8;

  g.fillStyle = alpha('#000000', 0.35); g.beginPath(); g.ellipse(hip[0], 6, 56, 13, 0, 0, 7); g.fill();

  // legs: ink under-stroke first, so two legs that overlap still read as two legs. The rim sits on
  // the OUTER edge of the stroke (±17.5 of a 29-wide limb), not inside it, or it looks like a stripe.
  for (const [k, a, b] of [[0, hip, P(pose, 'kB')], [1, P(pose, 'kB'), P(pose, 'fB')],
                           [2, hip, P(pose, 'kF')], [3, P(pose, 'kF'), P(pose, 'fF')]]) {
    sketchSeg(g, a, b, 40, INK, seed + 20 + k, 0.4);
    sketchSeg(g, a, b, 29, shade(col, k >= 2 ? -0.40 : -0.50), seed + 20 + k, 0.4);
    sketchSeg(g, [a[0] - 17.5, a[1]], [b[0] - 17.5, b[1]], 3.5, alpha(M.rim, 0.75), seed + 40 + k, 0.4);
  }
  // back arm is behind the torso: not drawn at all
  sketchSeg(g, sh, P(pose, 'eF'), 19, shade(col, -0.20), seed + 23, 0.45);
  sketchSeg(g, P(pose, 'eF'), P(pose, 'hF'), 17, shade(col, -0.20), seed + 24, 0.45);

  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.fillStyle = col; g.fill();
  g.save(); g.beginPath(); rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.clip();
  g.fillStyle = alpha('#000000', 0.15); g.fillRect(-BW / 2, cy - BH / 2, BW * 0.30, BH); g.restore();
  rr(g, -BW / 2, cy - BH / 2, BW, BH, BW / 2); g.strokeStyle = INK; g.lineWidth = 9; g.stroke();

  sketchCircle(g, P(pose, 'hF')[0], P(pose, 'hF')[1], 15, 8, INK, seed + 25, col);   // mitten hand

  drawHead(g, head[0], head[1] - 6, HEAD_R, face, M, seed + 30, f, markerOf(o), col);
  g.restore();
}

// Giant close-up: the same drawHead at frame size, so a close-up cannot disagree with a wide shot.
export function beanFace(g, cx, cy, R, o) {
  const M = mood(o.moodName || 'dusk');
  const seed = Math.round((o.seedBase || 0) * 131 + 7);
  // The head is drawn UNMIRRORED here, so the rear of the skull is not always local -x — it is the
  // side opposite whichever way the character faces. A close-up that leaves this at the default
  // puts the bun on the wrong side of the head, which is the exact drift this file exists to stop.
  const mk = markerOf(o);
  if (mk && mk.back === undefined) mk.back = -(o.facing === undefined ? -1 : o.facing);
  const lit = o.rimSide === undefined ? -1 : o.rimSide;
  // Behind the head, so the chin occludes the neck. Drawing the bust afterwards
  // pressed a flat slab over the jaw — the "bar of soap" close-up.
  if (o.shoulders) drawBust(g, cx, cy, R, (o.outfit && o.outfit.color) || '#2f9e8f', M, lit);
  drawHead(g, cx, cy, R, faceOf(o), M, seed, lit, mk,
           (o.outfit && o.outfit.color) || '#2f9e8f');
}

// A close-up bust: neck in shadow, sloped shoulders, collar, and a key-to-shadow
// gradient. A rounded rectangle reads as a slab; a shoulder line reads as a body.
function drawBust(g, cx, cy, R, col, M, lit) {
  g.save();
  g.fillStyle = shade(col, -0.55);                       // neck, under the chin
  g.beginPath();
  g.moveTo(cx - R * 0.30, cy + R * 0.60);
  g.lineTo(cx + R * 0.30, cy + R * 0.60);
  g.lineTo(cx + R * 0.34, cy + R * 1.08);
  g.lineTo(cx - R * 0.34, cy + R * 1.08);
  g.closePath(); g.fill();

  g.beginPath();                                          // torso + shoulder slope
  g.moveTo(cx - R * 1.90, cy + R * 3.60);
  g.lineTo(cx - R * 1.44, cy + R * 1.86);
  g.quadraticCurveTo(cx - R * 1.30, cy + R * 1.20, cx - R * 0.74, cy + R * 1.06);
  g.quadraticCurveTo(cx - R * 0.36, cy + R * 0.98, cx - R * 0.33, cy + R * 0.80);
  g.lineTo(cx + R * 0.33, cy + R * 0.80);
  g.quadraticCurveTo(cx + R * 0.36, cy + R * 0.98, cx + R * 0.74, cy + R * 1.06);
  g.quadraticCurveTo(cx + R * 1.30, cy + R * 1.20, cx + R * 1.44, cy + R * 1.86);
  g.lineTo(cx + R * 1.90, cy + R * 3.60);
  g.closePath();
  g.fillStyle = linGrad(g, cx + lit * R * 1.5, cy + R * 1.0, cx - lit * R * 1.5, cy + R * 3.2,
                        [shade(col, 0.12), col, shade(col, -0.44)]);
  g.fill();
  g.strokeStyle = INK; g.lineWidth = R * 0.075; g.stroke();

  g.strokeStyle = shade(col, -0.50); g.lineWidth = R * 0.07; g.lineCap = 'round';
  for (const sgn of [-1, 1]) {                            // collar / lapels
    g.beginPath();
    g.moveTo(cx + sgn * R * 0.33, cy + R * 0.86);
    g.lineTo(cx + sgn * R * 0.60, cy + R * 1.32);
    g.stroke();
  }
  g.strokeStyle = alpha(M.rim, 0.55); g.lineWidth = R * 0.055;   // lit shoulder edge
  g.beginPath();
  g.moveTo(cx + lit * R * 0.74, cy + R * 1.06);
  g.quadraticCurveTo(cx + lit * R * 1.30, cy + R * 1.20, cx + lit * R * 1.44, cy + R * 1.86);
  g.stroke();
  g.restore();
}
