// sets/kitchen.js — the one location. Night, one pendant lamp, door at frame RIGHT.
// Screen direction: NILS frame-LEFT facing right, seated at the counter. RAE frame-RIGHT facing left,
// standing nearer the door at 0.90W than she is to him — so her three-step exit fits the 1.64 s
// of silence at a walk, not a run (160 units/s x s, per the style bible).
import { E, V, mood, layer, backdrop, rr, seg, circle, ring, poly, linGrad, radGrad, glow, alpha, shade, mix } from '/engine/core.js';
import { POSES } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import { person } from '../blocking.js';

export const GROUND = () => E.H * V(0.80, 0.70);
export const LAMP = () => [E.W * 0.5 + V(70, 50), E.H * V(0.17, 0.13)];
export const COUNTER_Y = () => GROUND() - V(122, 112);
export const SEATS = () => ({ nils: E.W * 0.28, rae: E.W * 0.62 });
export const DOOR_X = () => E.W * 0.90;

// One definition, used by the set AND by the repaint after the cast — two copies is how a seam
// appears at the counter edge. The panel runs 46 below GROUND so a figure standing behind it
// cannot leak feet or a ground shadow under the base.
function counterPanel(g, GY, M, dark) {
  // The counter is an island on the LEFT of the room, not a trench across the frame: it has to end
  // before RAE's door lane, or she reads as standing behind it while she is walking out.
  const ch = V(122, 112), cy = GY - ch, CX = E.W / 2, x = CX - V(780, 580), w = V(980, 760);
  const [lx] = LAMP();
  g.fillStyle = shade(dark, 0.05); g.fillRect(x, cy, w, ch + 46);            // plinth to the floor
  g.fillStyle = linGrad(g, 0, cy, 0, cy + ch, [[0, shade(dark, 0.26)], [1, shade(dark, 0.02)]]);
  g.fillRect(x, cy, w, ch);
  g.fillStyle = shade(dark, 0.52); g.fillRect(x, cy, w, 14);                 // lit top edge
  glow(g, lx, cy + ch * 0.55, V(430, 340), M.practical, 0.055);              // warm bounce
}

export function kitchen(g, t, cam, o = {}) {
  const M = mood(o.moodName || 'midnight'), GY = GROUND(), CX = E.W / 2;
  const wall = shade(M.wall, -0.35), dark = shade(M.wall, -0.66);
  const [lx, ly] = LAMP(), s = SEATS();

  layer(g, cam, 0.14, (g) => {
    backdrop(g, M.sky);
    FX.stars(g, t, { count: 26, a: 0.4 });
    FX.moon(g, CX - V(700, 520), E.H * V(0.15, 0.1), 44);
  });

  layer(g, cam, 0.5, (g) => {                                    // back wall, window, door
    g.fillStyle = linGrad(g, 0, 0, 0, GY, [[0, wall], [1, dark]]);
    g.fillRect(-E.W, -E.H, E.W * 4, GY + E.H);
    const wx = CX - V(880, 640), wy = E.H * V(0.13, 0.09), ww = V(340, 300), wh = V(300, 380);
    FX.windowFrame(g, { x: wx, y: wy, w: ww, h: wh, cols: 2, rows: 2, frame: dark, bar: 8 }, (g, x, y, w, h) => {
      g.fillStyle = linGrad(g, 0, y, 0, y + h, [[0, mix(M.sky[1], '#1d2440', 0.55)], [1, M.sky[0]]]);
      g.fillRect(x, y, w, h);
    });
    glow(g, wx + ww / 2, wy + wh / 2, V(400, 480), '#8fa8d8', 0.08);
    FX.godRays(g, wx + ww / 2, wy + wh / 2, { count: 6, len: V(760, 900), spread: 0.4, color: '#9fb6e0', a: 0.05, angle: 1.22 });
    const dw = V(230, 200), dh = V(430, 560), dx = DOOR_X();
    FX.door(g, { x: dx, y: GY, w: dw, h: dh, color: shade(dark, -0.15), open: o.doorOpen || 0, light: '#2a3554' });
    g.strokeStyle = shade(dark, 0.22); g.lineWidth = 7;
    g.strokeRect(dx - dw / 2, GY - dh, dw, dh);
    circle(g, dx - dw * 0.32, GY - dh * 0.46, V(11, 9), '#c9b48a');          // handle
  });

  layer(g, cam, 0.86, (g) => {                                   // counter, pendant, floor
    counterPanel(g, GY, M, dark);
    g.fillStyle = linGrad(g, 0, GY, 0, GY + 460, [[0, shade(M.floor, -0.05)], [1, shade(M.dark, -0.32)]]);
    g.fillRect(-E.W, GY, E.W * 4, E.H * 2);
    FX.floorLines(g, GY, GY + 470, 'rgba(0,0,0,.3)', 0.085);
    seg(g, [[lx, 0], [lx, ly]], 6, dark);
    poly(g, [[lx - 52, ly], [lx + 52, ly], [lx + 32, ly + 40], [lx - 32, ly + 40]], shade(dark, 0.24));
    glow(g, lx, ly + 46, V(470, 570), M.practical, 0.52);
    FX.lightCone(g, lx, ly + 46, { w: V(540, 420), h: COUNTER_Y() - ly, color: M.practical, a: 0.10 });
    FX.pool(g, lx, GY, V(330, 250), V(58, 44), M.practical, 0.2);
    FX.chair(g, s.nils + V(20, 16), GY, V(1.05, 0.95), '#241c26');
  });
  return { GY, CX, M, seats: s, counterY: COUNTER_Y(), lamp: [lx, ly], doorX: DOOR_X() };
}

// ── props ───────────────────────────────────────────────────────────────────
// Repaints the counter front AFTER the cast, so a figure seated behind it is occluded from the
// waist down. layer() tracks parallax depth, not paint order, so the set cannot do this itself —
// without this call the seated character's legs are drawn on the wrong side of the counter.
export function counterFace(g, cam, GY, o = {}) {
  const M = mood(o.moodName || 'midnight');
  layer(g, cam, 0.86, (g) => counterPanel(g, GY, M, shade(M.wall, -0.66)));
}

// The prop that ends the relationship. Reads at s=1.2 on the counter and s=4.4 in an insert:
// a split ring with two fanned keys hanging from it, blades pointing down.
export function keys(g, x, y, s = 1, rot = 0) {
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s);
  const brass = '#e6c68a', dim = shade(brass, -0.50), ink = '#15131a';
  for (const [i, dx] of [[0, -8], [1, 9]]) {                  // two keys, fanned
    const c = i ? dim : brass;
    g.save(); g.translate(dx, 12); g.rotate(i ? 0.17 : -0.13);
    seg(g, [[0, 4], [0, 40]], 6, c, 'butt');                   // blade
    seg(g, [[0, 29], [8, 29]], 5, c, 'butt');                  // teeth
    seg(g, [[0, 37], [6, 37]], 5, c, 'butt');
    circle(g, 0, 0, 9.5, c); ring(g, 0, 0, 9.5, 4, ink);       // bow
    circle(g, 0, 0, 3.4, '#0d0b12');
    g.restore();
  }
  ring(g, 0, 0, 16, 4.5, brass);                               // the ring they hang from
  glow(g, 0, 16, 52, '#ffe9b8', 0.26);
  g.restore();
}

// Worn shoulder bag. (x, y) is the figure's FEET, s its scale, f its facing (±1) — so it is placed
// in the figure's own space and cannot drift off the body the way a world-space offset did.
// Draw AFTER the figure: strap across the torso, case hanging at the hip on the back side.
export function wornBag(g, x, y, s, f, o = {}) {
  const col = o.col || '#4a4468', ink = '#15131a';
  g.save(); g.translate(x, y); g.scale(f * s, s);
  // strap lives on the EXPOSED torso only: the fused head occupies y -254..-160, so anything
  // above -155 is drawn across the face
  seg(g, [[24, -148], [-18, -116]], 12, shade(col, 0.26));
  g.save(); g.translate(-44, -92);
  rr(g, -32, -38, 64, 76, 10); g.fillStyle = col; g.fill();
  g.strokeStyle = ink; g.lineWidth = 7; g.stroke();
  rr(g, -20, -12, 40, 22, 6); g.fillStyle = shade(col, 0.16); g.fill();
  g.restore(); g.restore();
}

// The same bag off the shoulder, hanging from a hand at (x, y).
export function heldBag(g, x, y, s = 1, col = '#4a4468') {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = shade(col, 0.26); g.lineWidth = 8; g.lineCap = 'round';
  g.beginPath(); g.arc(0, 28, 28, Math.PI * 1.04, Math.PI * 1.96); g.stroke();
  g.translate(0, 58);
  rr(g, -32, -38, 64, 76, 10); g.fillStyle = col; g.fill();
  g.strokeStyle = '#15131a'; g.lineWidth = 7; g.stroke();
  rr(g, -20, -12, 40, 22, 6); g.fillStyle = shade(col, 0.16); g.fill();
  g.restore();
}

// Her hand holding the keys, shared by the two inserts (s004 holds them up, s011 puts them down).
// (x, y) is the PALM CENTRE in world space and K the insert scale, so a shot only has to say where
// the hand is — the arm, mitten, fingers and ring all follow from that.
export function keysHand(g, x, y, K, swing, o = {}) {
  const ink = '#15131a', outfit = o.col || '#2f9e8f';
  const p = (fx, fy) => [x + fx * K, y + fy * K];
  const arm = (o.arm || [[560, -420], [250, -120], [96, 40]]).map(([a, b]) => p(a, b));
  seg(g, arm, 118 * K, ink);
  seg(g, arm, 92 * K, outfit);
  circle(g, x, y, 78 * K, ink);
  circle(g, x, y, 70 * K, outfit);
  for (const [fx, fy] of [[-46, 66], [-2, 80]]) {
    seg(g, [p(-4, 26), p(fx, fy)], 34 * K, ink);
    seg(g, [p(-4, 26), p(fx, fy)], 22 * K, outfit);
  }
  const [kx, ky] = p(o.rx === undefined ? -52 : o.rx, o.ry === undefined ? 104 : o.ry);
  keys(g, kx, ky, (o.ks === undefined ? 3.6 : o.ks) * K, swing);
  return { kx, ky, p };
}

// NILS at the counter, used by every shot that frames him. The body, the counter repaint and the
// hands-on-top are three calls that MUST stay in this order — split them and either his legs poke
// through the counter or the repaint amputates the hands resting on it.
export function nilsAtCounter(g, cam, seats, GY, o = {}) {
  const s = o.s || V(1.75, 1.8), ink = '#15131a', col = '#c2553d';
  const flat = { ...POSES.sit, eF: [46, -130], hF: [78, -124], eB: [26, -128], hB: [56, -124] };
  layer(g, cam, 1, (g) => person(g, 'nils', {
    x: seats.nils, y: GY, s, facing: 1, pose: flat, expr: 'worried',
    face: o.face, look: o.look, talk: o.talk || 0, moodName: 'midnight' }));
  counterFace(g, cam, GY);
  layer(g, cam, 1, (g) => {
    const q = (fx, fy) => [seats.nils + fx * s, GY + fy * s];
    for (const [ex, ey, mx, my] of [[46, -130, 78, -124], [26, -128, 56, -124]]) {
      seg(g, [q(1, -146), q(ex, ey), q(mx, my)], 30, ink);
      seg(g, [q(1, -146), q(ex, ey), q(mx, my)], 20, shade(col, -0.20));
      circle(g, q(mx, my)[0], q(mx, my)[1], 16 * s, ink);
      circle(g, q(mx, my)[0], q(mx, my)[1], 13 * s, col);
    }
  });
}
