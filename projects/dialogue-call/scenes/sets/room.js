// sets/room.js — night kitchen, two figures at the counter. One warm practical is the key light.
// Reusable: room(g, t, cam) returns { GY, CX, M, seats }.
import { E, V, mood, layer, backdrop, rr, seg, circle, poly, linGrad, radGrad, glow, alpha, shade, mix } from '/engine/core.js';
import * as FX from '/engine/fx2d.js';

export const GROUND = () => E.H * V(0.80, 0.70);
export function room(g, t, cam, o = {}) {
  const M = mood('night'), GY = GROUND(), CX = E.W / 2;
  const wall = shade(M.wall, -0.3), dark = shade(M.wall, -0.62);
  const seats = { l: CX - V(300, 250), r: CX + V(300, 250) };
  layer(g, cam, 0.14, (g) => {
    backdrop(g, M.sky);
    FX.stars(g, t, { count: 30, a: 0.45 });
    FX.moon(g, CX + V(700, 340), E.H * V(0.16, 0.1), 46);
  });
  layer(g, cam, 0.5, (g) => {                                        // back wall + window
    g.fillStyle = linGrad(g, 0, 0, 0, GY, [[0, wall], [1, dark]]);
    g.fillRect(-E.W, -E.H, E.W * 4, GY + E.H);
    const wx = CX - V(760, 560), wy = E.H * V(0.14, 0.09), ww = V(330, 300), wh = V(280, 360);
    FX.windowFrame(g, { x: wx, y: wy, w: ww, h: wh, cols: 2, rows: 2, frame: dark, bar: 8 }, (g, x, y, w, h) => {
      g.fillStyle = linGrad(g, 0, y, 0, y + h, [[0, mix(M.sky[1], '#22284a', 0.5)], [1, M.sky[0]]]); g.fillRect(x, y, w, h);
    });
    glow(g, wx + ww / 2, wy + wh / 2, V(380, 460), '#93a9d8', 0.09);
    FX.godRays(g, wx + ww / 2, wy + wh / 2, { count: 6, len: V(820, 1000), spread: 0.42, color: '#9fb6e0', a: 0.055, angle: 1.25 });
  });
  layer(g, cam, 0.86, (g) => {                                       // counter + pendant + floor
    const ch = V(120, 110), cy = GY - ch;
    g.fillStyle = shade(dark, 0.12); g.fillRect(CX - V(820, 620), cy, V(1640, 1240), ch);
    g.fillStyle = shade(dark, 0.36); g.fillRect(CX - V(820, 620), cy, V(1640, 1240), 14);
    g.fillStyle = linGrad(g, 0, GY, 0, GY + 460, [[0, shade(M.floor, -0.05)], [1, shade(M.dark, -0.3)]]);
    g.fillRect(-E.W, GY, E.W * 4, E.H * 2);
    FX.floorLines(g, GY, GY + 480, 'rgba(0,0,0,.28)', 0.085);
    const px = CX + V(60, 40), py = E.H * V(0.2, 0.14);
    seg(g, [[px, 0], [px, py]], 6, dark);
    poly(g, [[px - 54, py], [px + 54, py], [px + 34, py + 40], [px - 34, py + 40]], shade(dark, 0.22));
    glow(g, px, py + 46, V(460, 560), M.practical, 0.55);
    FX.lightCone(g, px, py + 46, { w: V(520, 400), h: cy - py, color: M.practical, a: 0.11 });
    FX.pool(g, px, GY, V(300, 230), V(56, 42), M.practical, 0.2);
    for (const sx of [seats.l, seats.r]) FX.chair(g, sx, GY, V(1.05, 0.95), '#241c26');
    rr(g, CX - V(120, 90), cy - V(46, 34), V(240, 180), V(46, 34), 10); g.fillStyle = shade(dark, 0.3); g.fill();
  });
  return { GY, CX, M, seats, counterY: GY - V(120, 110) };
}
