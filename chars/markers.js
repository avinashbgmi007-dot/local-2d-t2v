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

  // A baseball cap: dome over the skull with a brim toward the facing side.
  cap: {
    over: (g, cx, cy, R, col, back) => {
      // The brow sits at cy - R*(0.30 + 0.20*brow), i.e. as high as cy - 0.50R.
      // A brim at eye level deletes the eyes; everything here stays above -0.62R.
      const c = shade(col, -0.10), bandY = cy - R * 0.68;
      g.save();
      g.beginPath(); g.arc(cx, cy, R * 1.02, 0, 7); g.clip();
      g.fillStyle = c;
      g.beginPath(); g.arc(cx, bandY + R * 0.10, R * 0.99, Math.PI, 0); g.fill();
      g.restore();
      g.strokeStyle = INK; g.lineWidth = R * 0.07;
      g.beginPath(); g.moveTo(cx - R * 0.98, bandY); g.lineTo(cx + R * 0.98, bandY); g.stroke();
      const dir = -back;   // brim points the way the character faces
      g.fillStyle = shade(c, -0.20);
      g.beginPath(); g.ellipse(cx + dir * R * 0.56, bandY, R * 0.58, R * 0.11, 0, 0, 7); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.06; g.stroke();
    },
  },

  beanie: {
    over: (g, cx, cy, R, col) => {
      const c = shade(col, -0.08), bandY = cy - R * 0.74;
      g.save();
      g.beginPath(); g.arc(cx, cy, R * 1.02, 0, 7); g.clip();
      g.fillStyle = c;
      g.beginPath(); g.arc(cx, bandY + R * 0.22, R * 0.98, Math.PI, 0); g.fill();
      g.restore();
      g.fillStyle = shade(c, 0.16);
      rr(g, cx - R * 0.96, bandY, R * 1.92, R * 0.22, R * 0.09); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.055; g.stroke();
      circle(g, cx, bandY - R * 0.26, R * 0.15, shade(c, 0.30));
    },
  },

  // ---- role headwear ------------------------------------------------------
  // The cast used to draw from THREE front-readable marks (glasses, cap,
  // beanie), so a three-hander was always glasses + cap + beanie and every
  // film looked like the same three people. These five are chosen by what the
  // character DOES (fresh/cast.py _ROLE_HEAD), not by a random pick.
  // Every one stays above the brow line at cy - 0.50R: a brim at eye level
  // deletes the eyes, and the eyes carry the acting.

  // A brimmed hat: a low crown and a wide brim. Detective, traveller, farmer.
  hat: {
    over: (g, cx, cy, R, col, back) => {
      const c = shade(col, -0.22), bandY = cy - R * 0.62, dir = -back;
      g.save();
      g.beginPath(); g.arc(cx, cy, R * 1.02, 0, 7); g.clip();
      g.fillStyle = c;
      g.beginPath(); g.ellipse(cx, bandY - R * 0.10, R * 0.74, R * 0.46, 0, Math.PI, 0);
      g.fill();
      g.restore();
      g.strokeStyle = INK; g.lineWidth = R * 0.06;
      g.beginPath(); g.ellipse(cx, bandY - R * 0.10, R * 0.74, R * 0.46, 0, Math.PI, 0); g.stroke();
      g.fillStyle = shade(c, -0.10);
      g.beginPath(); g.ellipse(cx, bandY, R * 1.16, R * 0.15, 0, 0, 7); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.055; g.stroke();
      g.fillStyle = shade(c, 0.22);                    // band, so it is not a flat disc
      rr(g, cx - R * 0.72, bandY - R * 0.16, R * 1.44, R * 0.11, R * 0.04); g.fill();
      void dir;
    },
  },

  // A hard helmet: dome to just above the brow, a rim and a crest.
  helmet: {
    over: (g, cx, cy, R, col, back) => {
      const c = shade(col, 0.04), bandY = cy - R * 0.58;
      g.save();
      g.beginPath(); g.arc(cx, cy, R * 1.02, 0, 7); g.clip();
      g.fillStyle = c;
      g.beginPath(); g.arc(cx, bandY + R * 0.06, R * 1.00, Math.PI, 0); g.fill();
      g.restore();
      g.strokeStyle = INK; g.lineWidth = R * 0.07;
      g.beginPath(); g.moveTo(cx - R * 1.00, bandY); g.lineTo(cx + R * 1.00, bandY); g.stroke();
      g.fillStyle = shade(c, -0.28);
      g.beginPath(); g.ellipse(cx, bandY - R * 0.52, R * 0.13, R * 0.30, 0, 0, 7); g.fill();
      g.fillStyle = shade(c, 0.26);
      rr(g, cx - R * 0.90, bandY - R * 0.02, R * 1.80, R * 0.13, R * 0.05); g.fill();
      void back;
    },
  },

  // A hood: fabric BEHIND the skull and a rim OVER it. Reads at any size.
  // A hood. First version filled a disc around the whole head and read as a
  // bowl, so the OVER pass is now a CRESCENT over the crown only: the fabric
  // must never reach eye level, for the same reason a brim must not.
  hood: {
    // A COLLAR behind the neck, not a mass around the skull: an ellipse centred
    // near the head pokes out as a ring and reads as a porthole (measured on the
    // first two renders). The hood's volume is the crescent over the crown plus
    // this collar falling to the shoulders.
    behind: (g, cx, cy, R, col, back) => {
      const c = shade(col, -0.34);
      g.fillStyle = c;
      g.beginPath(); g.ellipse(cx + back * R * 0.05, cy + R * 1.34, R * 1.34, R * 0.40, 0, 0, 7);
      g.fill();
    },
    over: (g, cx, cy, R, col) => {
      const c = shade(col, -0.26);
      g.fillStyle = c;
      g.beginPath();
      g.arc(cx, cy, R * 1.10, Math.PI * 1.12, Math.PI * 1.88);          // outer edge
      g.arc(cx, cy, R * 0.84, Math.PI * 1.88, Math.PI * 1.12, true);    // inner edge
      g.closePath();
      g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.05;
      g.beginPath(); g.arc(cx, cy, R * 1.10, Math.PI * 1.12, Math.PI * 1.88); g.stroke();
      g.strokeStyle = alpha(shade(c, 0.45), 0.50); g.lineWidth = R * 0.04;
      g.beginPath(); g.arc(cx, cy, R * 0.90, Math.PI * 1.18, Math.PI * 1.82); g.stroke();
    },
  },

  // A headband across the forehead: the cheapest "athlete / dancer" signal.
  headband: {
    over: (g, cx, cy, R, col) => {
      const c = shade(col, 0.18), bandY = cy - R * 0.54;
      g.fillStyle = c;
      rr(g, cx - R * 0.99, bandY - R * 0.10, R * 1.98, R * 0.22, R * 0.09); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.05; g.stroke();
      g.fillStyle = alpha('#ffffff', 0.35);
      rr(g, cx - R * 0.90, bandY - R * 0.06, R * 1.80, R * 0.05, R * 0.02); g.fill();
    },
  },

  // A chef's toque: a band plus a tall puffy crown. Reads instantly in a kitchen.
  toque: {
    over: (g, cx, cy, R, col) => {
      const c = shade(col, 0.10), bandY = cy - R * 0.66;
      g.fillStyle = shade(c, 0.30);
      g.beginPath(); g.ellipse(cx, bandY - R * 0.46, R * 0.86, R * 0.50, 0, 0, 7); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.055;
      g.beginPath(); g.ellipse(cx, bandY - R * 0.46, R * 0.86, R * 0.50, 0, 0, 7); g.stroke();
      g.fillStyle = c;
      rr(g, cx - R * 0.80, bandY - R * 0.16, R * 1.60, R * 0.30, R * 0.06); g.fill();
      g.strokeStyle = INK; g.lineWidth = R * 0.055; g.stroke();
    },
  },

  bun: {
    behind: (g, cx, cy, R, col, back) => {
      const c = shade(col, -0.46);
      circle(g, cx + back * R * 0.30, cy - R * 0.98, R * 0.34, c);
      g.strokeStyle = INK; g.lineWidth = R * 0.06;
      g.beginPath(); g.arc(cx + back * R * 0.30, cy - R * 0.98, R * 0.34, 0, 7); g.stroke();
    },
  },
};
