// shots/main.js — "She Asked About You" · 13.6 s, 7 shots, two characters.
// Blocking rules: fixed screen direction (RAE left facing right, NILS right facing left), the
// listener always looks at the speaker, gestures land on real word times from wordTime().
import { E, V, registerShot, mood, layer, blurLayer, veil, ease, prog, key, clamp, lerp, wordTime, talkAmount, seg, circle, rr, poly, glow, alpha, shade, linGrad } from '/engine/core.js';
import { drawFigure, POSES, posesAt, breathe, bigFace, headPos } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import * as UI from '/engine/ui2d.js';
import { room, GROUND } from '../sets/room.js';
import { RAE, NILS } from '../cast.js';

// local-time helper: when is `word` spoken, relative to this shot? `fb` = fallback if Whisper mangled it.
const on = (info, t, word, after, fb) => {
  const gt = wordTime(word, after);
  return gt === null ? fb : gt - (info.globalT - t);
};
const blink = (t, p = 3.1) => (t % p) > p - 0.09;
const rimOf = (M, dir) => ({ color: M.rim, dir, w: 4 });
const S = () => V(1.5, 1.6);

// s001 · two-shot: "You actually called her." / "I said I would."
registerShot('s001', { draw(g, t, info) {
  const cam = { z: 1 + 0.06 * ease.inOut(prog(t, 0, info.dur)), x: -18 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, M, seats } = room(g, t, cam);
  const s = S(), point = on(info, t, 'called', 0.5, 0.95), reply = on(info, t, 'I', 1.4, 1.53);
  layer(g, cam, 1, (g) => {
    const raePose = posesAt(t, [[0, POSES.stand], [point - 0.15, POSES.point]]);
    drawFigure(g, { x: seats.l, y: GY, s, facing: 1, outfit: RAE, pose: breathe(raePose, t),
      expr: 'neutral', talk: talkAmount(info.globalT, 0.05, 1.53), look: [0.55, -0.05],
      rim: rimOf(M, [-1, -0.3]), blink: blink(t), shadow: false });
    const nilsPose = posesAt(t, [[0, POSES.relaxed], [reply, POSES.crossArms]]);
    drawFigure(g, { x: seats.r, y: GY, s, facing: -1, outfit: NILS, pose: breathe(nilsPose, t, 1, 2),
      expr: t > reply ? 'smirk' : 'neutral', talk: talkAmount(info.globalT, reply, 2.53),
      look: t > reply ? [-0.5, -0.1] : [-0.2, 0.55], rim: rimOf(M, [-1, -0.3]), blink: blink(t, 2.7), shadow: false });
  });
  FX.dust(g, t, { count: 26, color: '#cfe0ff', a: 0.26 });
} });

// s002 · medium RAE: "You said you'd think about it."
registerShot('s002', { draw(g, t, info) {
  const cam = { z: 1.05 + 0.05 * ease.inOut(prog(t, 0, info.dur)), x: 22 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, M, seats } = room(g, t, cam);
  const think = on(info, t, 'think', 3.0, 3.61);
  layer(g, cam, 1, (g) => {
    const p = posesAt(t, [[0, POSES.relaxed], [think - 0.2, POSES.explain]]);
    drawFigure(g, { x: seats.l, y: GY, s: V(1.9, 2.0), facing: 1, outfit: RAE, pose: breathe(p, t),
      expr: 'surprised', brow: clamp((t - think) * 3), talk: talkAmount(info.globalT, 2.53, 4.45),
      look: [0.35, -0.15], rim: rimOf(M, [-1, -0.3]), blink: blink(t, 2.9), shadow: false });
  });
  blurLayer(g, 14, (gg) => {    drawFigure(gg, { x: seats.r + V(560, 430), y: GY + V(210, 170), y: GY, s: V(3.1, 3.3), facing: -1, outfit: NILS,
      pose: breathe(POSES.sit, t, 1, 2), expr: 'neutral', look: [-0.4, 0.1], rim: rimOf(M, [-1, -0.3]), alpha: 0.95 });
  });
} });

// s003 · medium NILS: "Same energy." — the shrug lands on the first word
registerShot('s003', { draw(g, t, info) {
  const cam = { z: 1.04 + 0.04 * t, x: -14 * ease.out(prog(t, 0, 0.8)) };
  const { GY, M, seats } = room(g, t, cam);
  const same = on(info, t, 'Same', 4.4, 4.45);
  layer(g, cam, 1, (g) => {
    const p = posesAt(t, [[0, POSES.sit], [same, POSES.shrug]]);
    drawFigure(g, { x: seats.r, y: GY, s: V(1.9, 2.0), facing: -1, outfit: NILS, pose: breathe(p, t, 1, 2),
      expr: 'smirk', talk: talkAmount(info.globalT, 4.45, 5.17), look: [-0.45, -0.1],
      rim: rimOf(M, [-1, -0.3]), blink: blink(t, 3.4), shadow: false });
  });
  blurLayer(g, 14, (gg) => {    drawFigure(gg, { x: seats.l - V(560, 430), y: GY + V(210, 170), y: GY, s: V(3.1, 3.3), facing: 1, outfit: RAE,
      pose: breathe(POSES.crossArms, t), expr: 'neutral', look: [0.4, 0], rim: rimOf(M, [-1, -0.3]), alpha: 0.95 });
  });
  FX.dust(g, t, { count: 18, color: '#ffe2bd', a: 0.2 });
} });

// s004 · close RAE: "That is genuinely not the same thing." — deadpan, head turns toward him
registerShot('s004', { draw(g, t, info) {
  const cam = { z: 1.12 - 0.05 * ease.inOut(prog(t, 0, info.dur)), x: 30 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, M, seats } = room(g, t, cam);
  const gen = on(info, t, 'genuinely', 5.5, 5.89);
  layer(g, cam, 1, (g) => {
    const lean = clamp((t - gen) * 2.2);
    const p = { ...posesAt(t, [[0, POSES.crossArms], [gen, POSES.point]]), head: [3 + lean * 26, -208 + lean * 6] };
    drawFigure(g, { x: seats.l, y: GY, s: V(2.1, 2.25), facing: 1, outfit: RAE, pose: breathe(p, t),
      expr: 'neutral', brow: 0.7 * clamp((t - gen) * 2),
      talk: talkAmount(info.globalT, 5.17, 7.41), look: [0.3 + lean * 0.35, -0.12],
      rim: rimOf(M, [-1, -0.3]), blink: blink(t, 4.2), shadow: false });
  });
  FX.godRays(g, seats.l - V(300, 240), E.H * V(0.2, 0.14), { count: 4, len: V(700, 800), spread: 0.3, color: '#9fb6e0', a: 0.05, angle: 1.3 });
} });

// s005 · medium NILS: "She laughed, though." — grin, glance down, back to her
registerShot('s005', { draw(g, t, info) {
  const cam = { z: 1.05 + 0.03 * t };
  const { GY, M, seats } = room(g, t, cam);
  const laughed = on(info, t, 'laughed', 7.4, 7.87);
  layer(g, cam, 1, (g) => {
    const down = clamp((t - laughed) * 3) * (1 - clamp((t - laughed - 0.25) * 3));
    drawFigure(g, { x: seats.r, y: GY, s: V(1.95, 2.05), facing: -1, outfit: NILS,
      pose: breathe(posesAt(t, [[0, POSES.relaxed], [laughed, POSES.holdFront]]), t, 1, 2),
      expr: 'grin', talk: talkAmount(info.globalT, 7.41, 8.47),
      look: [-0.45 + down * 0.15, -0.1 + down * 0.7], rim: rimOf(M, [-1, -0.3]), blink: blink(t, 2.8), shadow: false });
  });
  blurLayer(g, 14, (gg) => {    drawFigure(gg, { x: seats.l - V(580, 450), y: GY + V(210, 170), y: GY, s: V(3.2, 3.4), facing: 1, outfit: RAE,
      pose: breathe(POSES.crossArms, t), expr: 'neutral', look: [0.42, 0], rim: rimOf(M, [-1, -0.3]), alpha: 0.95 });
  });
} });

// s006 · giant face RAE over the 1.4 s silent beat, then eyes widen on "laughed?"
registerShot('s006', { draw(g, t, info) {
  blurLayer(g, 14, (g) => room(g, 0, { z: 1.8, x: -120, y: -140 }));
  veil(g, '#0a0d1c', 0.42);
  const M = mood('night'), r = V(300, 330) * (1 + 0.04 * t);
  const widen = on(info, t, 'laughed', 9.5, 10.11);
  const talk = talkAmount(info.globalT, 9.87, 10.51);
  bigFace(g, E.W / 2 + V(40, 0), E.H * V(0.58, 0.52), r, {
    outfit: RAE, expr: t > widen ? 'shocked' : 'neutral', talk,
    look: [-0.15 + 0.2 * clamp((t - widen) * 3), t > widen ? -0.05 : 0.1],
    rimColor: M.rim, rimSide: -1, blink: (t % 4.6) > 4.5, tilt: -0.03 * clamp(t / 1.4) });
  if (t > widen) FX.rings(g, E.W / 2 + V(40, 0), E.H * V(0.58, 0.52), t - widen, { count: 2, r0: r * 1.05, r1: r * 1.5, speed: 1.1, color: '#cfe0ff', a: 0.28 });
} });

// s007 · NILS "Twice." with a raised finger, then pull out to the two-shot for the button
registerShot('s007', { draw(g, t, info) {
  const out = ease.inOut(prog(t, 1.1, 2.4));
  const cam = { z: lerp(1.5, 1.02, out), x: lerp(-90, 0, out), y: lerp(-60, 0, out) };
  const { GY, M, seats } = room(g, t, cam);
  const twice = on(info, t, 'Twice', 10.4, 10.51), asked = on(info, t, 'asked', 11.2, 11.59);
  const s = lerp(V(2.0, 2.1), S(), out);
  layer(g, cam, 1, (g) => {
    drawFigure(g, { x: seats.r, y: GY, s, facing: -1, outfit: NILS,
      pose: breathe(posesAt(t, [[0, POSES.holdFront], [twice, POSES.pointUp], [asked, POSES.explain]]), t, 1, 2),
      expr: t > twice ? 'happy' : 'smirk', talk: talkAmount(info.globalT, 10.51, 12.35),
      look: t > asked ? [-0.5, -0.05] : [-0.3, 0.1], rim: rimOf(M, [-1, -0.3]), blink: blink(t, 3.0), shadow: false });
    if (out > 0.25) {
      const toCam = clamp((t - 2.4) * 2.5);
      drawFigure(g, { x: seats.l, y: GY, s, facing: 1, outfit: RAE, pose: breathe(POSES.crossArms, t),
        expr: toCam > 0.5 ? 'worried' : 'neutral', look: [0.45 - toCam * 0.45, -0.05 + toCam * 0.1],
        rim: rimOf(M, [-1, -0.3]), blink: blink(t, 3.6), shadow: false });
    }
  });
  FX.dust(g, t, { count: 24, color: '#cfe0ff', a: 0.22 });
  if (t > 2.6) UI.endScreen(g, t - 2.6, { question: 'What did you last say you would do?', cast: [RAE, NILS] });
} });
