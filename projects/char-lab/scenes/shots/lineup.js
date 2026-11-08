// shots/lineup.js — character line-up: one armature, three skins, same acting beats.
import { E, V, registerShot, mood, layer, ease, prog, clamp, wordTime, talkAmount, alpha, shade, glow, text } from '/engine/core.js';
import { POSES, posesAt, breathe } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import { SKINS } from '../chars/lineup.js';

const COLS = () => [E.W * 0.24, E.W * 0.5, E.W * 0.76];
const OUTFIT = { top: 'tshirt', color: '#d64a33', head: 'none' };
const OUTFIT_BEAN = { color: '#2f9e8f' };
const OUTFIT_INK = { color: '#e0894a' };

function label(g, x, y, str, hot) {
  g.save(); g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = `800 ${Math.round(V(46, 40))}px Nunito`;
  g.fillStyle = hot ? '#ffd43b' : alpha('#ffffff', 0.72);
  g.fillText(str, x, y);
  g.restore();
}

// s001 · three of them, standing, breathing — silhouette comparison
registerShot('s001', { draw(g, t, info) {
  const cam = { z: 1 + 0.05 * ease.inOut(prog(t, 0, info.dur)) };
  const M = mood('midnight'), GY = E.H * V(0.80, 0.70), cols = COLS();
  layer(g, cam, 0.5, (g) => {
    g.fillStyle = M.sky[1]; g.fillRect(-E.W, -E.H, E.W * 4, GY);
    FX.floorLines(g, GY, GY + 500, 'rgba(0,0,0,.3)', 0.09);
    g.fillStyle = shade(M.floor, -0.2); g.fillRect(-E.W, GY, E.W * 4, E.H);
  });
  layer(g, cam, 1, (g) => {
    SKINS.forEach((sk, i) => {
      const pose = breathe(POSES.relaxed, t, 1, i + 1);
      const outfit = i === 0 ? OUTFIT : i === 1 ? OUTFIT_BEAN : OUTFIT_INK;
      sk.draw(g, { x: cols[i], y: GY, s: V(2.9, 2.4), facing: 1, pose, outfit, t, scarf: false, expr: 'neutral',
        rim: { color: M.rim, dir: [-1, -0.3], w: 4 }, look: [0, 0] });
      label(g, cols[i], GY + V(70, 60), sk.name, false);
    });
  });
  FX.dust(g, t, { count: 26, color: '#cfe0ff', a: 0.22 });
} });

// s002 · identical gesture, landed on the same spoken word — does the armature carry it?
registerShot('s002', { draw(g, t, info) {
  const GY = E.H * V(0.80, 0.70), cols = COLS(), M = mood('midnight');
  const t0 = info.globalT - t;
  const gt = wordTime('gesture', 2.5);
  const point = gt === null ? 1.2 : gt - t0;
  const cam = { z: 1.02 + 0.04 * ease.inOut(prog(t, 0, info.dur)), x: -14 * ease.inOut(prog(t, 0, info.dur)) };
  layer(g, cam, 0.5, (g) => {
    g.fillStyle = M.sky[1]; g.fillRect(-E.W, -E.H, E.W * 4, GY);
    g.fillStyle = shade(M.floor, -0.2); g.fillRect(-E.W, GY, E.W * 4, E.H);
    FX.floorLines(g, GY, GY + 500, 'rgba(0,0,0,.3)', 0.09);
  });
  layer(g, cam, 1, (g) => {
    SKINS.forEach((sk, i) => {
      const pose = posesAt(t, [[0, POSES.stand], [point + 0.15, POSES.point]]);
      const outfit = i === 0 ? OUTFIT : i === 1 ? OUTFIT_BEAN : OUTFIT_INK;
      const brow = clamp((t - point) * 2.5);
      sk.draw(g, { x: cols[i], y: GY, s: V(2.9, 2.4), facing: 1, pose, outfit, t, scarf: false,
        expr: t > point ? 'surprised' : 'neutral', talk: talkAmount(info.globalT, 2.58, 5.16),
        brow, rim: { color: M.rim, dir: [-1, -0.3], w: 4 }, look: [0.2, -0.1] });
      label(g, cols[i], GY + V(70, 60), sk.name, i === 1);
    });
  });
  FX.dust(g, t, { count: 20, color: '#cfe0ff', a: 0.2 });
} });

// s003 · faces only, big — which face survives 50 episodes?
registerShot('s003', { draw(g, t, info) {
  const cols = COLS(), M = mood('midnight');
  const cam = { z: 1.05 + 0.05 * ease.inOut(prog(t, 0, info.dur)) };
  layer(g, cam, 0.4, (g) => { g.fillStyle = M.sky[0]; g.fillRect(-E.W, -E.H, E.W * 4, E.H * 3); });
  layer(g, cam, 1, (g) => {
    SKINS.forEach((sk, i) => {
      const outfit = i === 0 ? OUTFIT : i === 1 ? OUTFIT_BEAN : OUTFIT_INK;
      const fs = V(3.2, 2.8);
      sk.draw(g, { x: cols[i], y: E.H * V(0.52, 0.48) + 214 * fs, s: fs, facing: 1, t, scarf: false,
        pose: breathe(POSES.stand, t, 1, i + 1), outfit,
        expr: t > 1.6 ? 'surprised' : 'neutral', talk: talkAmount(info.globalT, 5.46, 7.83),
        brow: clamp((t - 1.6) * 2), look: [0, -0.1], rim: { color: M.rim, dir: [-1, -0.3], w: 4 } });
      label(g, cols[i], E.H * V(0.90, 0.86), sk.name, i === 2);
    });
  });
  FX.godRays(g, E.W * 0.5, -100, { count: 5, len: E.H * 0.8, spread: 0.5, color: '#9fb6e0', a: 0.05, angle: 1.57 });
} });
