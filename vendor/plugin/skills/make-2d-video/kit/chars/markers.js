// chars/markers.js — the per-character identity mark.
//
// Three rules, each learned from a bug this replaces:
//   1. It is drawn inside the head pass, not per shot. Anything a shot has to remember to draw is
//      a thing one shot will forget — that is how s008 ended up with its own copy of RAE's colour.
//   2. It must never be a COLOUR-ONLY difference. Body colour comes from the style theme, so a
//      theme swap would change "who" the character is. Colour may ride on a silhouette, never be
//      the silhouette itself.
//   3. A mark declares which PASS it belongs to. Hair has to be both BEHIND the skull (the mass
//      falls past the shoulders) and OVER it (the fringe), and a shot must never pick for it.
import { circle, ring, seg, rr, alpha, shade } from '/engine/core.js';

const INK = '#15131a';

// pass is 'behind' (occluded by the skull) or 'over' (sits on the face).
export function drawMarker(g, kind, cx, cy, R, col, back, pass) {
  if (!kind) return;
  const m = MARKERS[kind];
  if (!m) throw new Error('unknown character marker: ' + kind);
  if (m[pass]) m[pass](g, cx, cy, R, col, back);
}

export const MARKER_NAMES = () => Object.keys(MARKERS);
export const isBehind = (kind) => !!(MARKERS[kind] && MARKERS[kind].behind);

const MARKERS = {
  // A bob: hair falling past the shoulders behind the head, with a crown above the hairline.
  // The hairline is deliberately kept ABOVE cy - 0.50R, because the brows live at
  // cy - R*(0.30 + 0.20*brow) and brow tilt is what carries almost all of this character's acting.
  // A fringe that reaches the brows is a fringe that deletes the performance.
  bob: {
    behind: (g, cx, cy, R, col, back) => {
      const hair = shade(col, -0.46), lit = shade(col, -0.18);
      // the mass falls BELOW the skull toward the shoulders; ringing the head read as a hood
      g.fillStyle = hair;
      g.beginPath(); g.ellipse(cx + back * R * 0.12, cy + R * 0.62, R * 0.94, R * 0.98, 0, 0, 7);
      g.fill();
      for (const sgn of [-1, 1]) {
        rr(g, cx + sgn * R * 0.90 - R * 0.20, cy - R * 0.42, R * 0.40, R * 1.46, R * 0.19);
        g.fillStyle = hair; g.fill();
        g.strokeStyle = INK; g.lineWidth = R * 0.09; g.stroke();
      }
      g.strokeStyle = alpha(lit, 0.50); g.lineWidth = R * 0.05; g.lineCap = 'round';
      for (const sgn of [-1, 1]) {
        g.beginPath();
        g.moveTo(cx + sgn * R * 0.84, cy - R * 0.14);
        g.quadraticCurveTo(cx + sgn * R * 0.95, cy + R * 0.52, cx + sgn * R * 0.86, cy + R * 0.94);
        g.stroke();
      }
    },
    over: (g, cx, cy, R, col, back) => {
      const hair = shade(col, -0.46);
      g.save(); g.beginPath(); g.arc(cx, cy, R * 0.995, 0, 7); g.clip();
      g.fillStyle = hair; g.beginPath();
      g.moveTo(cx - R, cy - R * 0.50);
      g.quadraticCurveTo(cx - R * 0.45, cy - R * 0.72, cx, cy - R * 0.68);
      g.quadraticCurveTo(cx + R * 0.55, cy - R * 0.64, cx + R, cy - R * 0.48);
      g.lineTo(cx + R, cy - R * 1.30); g.lineTo(cx - R, cy - R * 1.30); g.closePath(); g.fill();
      g.restore();
    },
  },

  // Round wire spectacles: a facial detail, so it still reads in a tight close-up.
  glasses: {
    over: (g, cx, cy, R) => {
      const ey = cy - R * 0.16, sep = R * 0.33, er = R * 0.29, cream = '#f2e6c8';
      for (const dx of [-sep, sep]) {
        circle(g, cx + dx, ey, er, alpha('#cfe0ff', 0.10));
        ring(g, cx + dx, ey, er, R * 0.07, cream);
      }
      seg(g, [[cx - sep + er, ey - R * 0.03], [cx + sep - er, ey - R * 0.03]], R * 0.055, cream);
    },
  },
};
