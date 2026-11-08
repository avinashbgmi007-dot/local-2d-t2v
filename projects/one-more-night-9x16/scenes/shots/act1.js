// shots/act1.js — s001..s004: the setup. She has already started leaving; he has not looked up.
// Geography from sets/kitchen.js: NILS frame-left facing right, RAE frame-right facing left,
// door at 0.90W behind her.
import { E, V, registerShot, mood, layer, blurLayer, ease, prog, clamp, lerp,
         glow, seg, circle, linGrad, shade, alpha } from '/engine/core.js';
import { POSES, posesAt, breathe } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import { kitchen, SEATS, wornBag, counterFace, keysHand } from '../sets/kitchen.js';
import { person, on, speak, S_WIDE, S_MED } from '../blocking.js';

// s001 · "I'm leaving." — wide two-shot, flat delivery, she is already half-turned to the door
registerShot('s001', { draw(g, t, info) {
  const cam = { z: 1 + 0.07 * ease.inOut(prog(t, 0, info.dur)), x: -20 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, M, seats } = kitchen(g, t, cam);
  layer(g, cam, 1, (g) => {
    person(g, 'nils', { x: seats.nils, y: GY, s: S_WIDE(), facing: 1,
      pose: breathe(POSES.sit, t, 1, 2), expr: 'neutral', look: [0.1, 0.75], moodName: 'midnight' });
    // bag is worn, so it is placed in HER space (feet + scale + facing) and drawn after the body
    person(g, 'rae', { x: seats.rae, y: GY, s: S_WIDE(), facing: -1,
      pose: breathe(POSES.relaxed, t), expr: 'neutral', look: [-0.30, 0.05],
      talk: speak(info, t, 0.05, 0.9), moodName: 'midnight' });
    wornBag(g, seats.rae, GY, S_WIDE(), -1);
  });
  counterFace(g, cam, GY);                                     // he is BEHIND it, not in front
  FX.dust(g, t, { count: 24, color: '#cfe0ff', a: 0.22 });
  FX.lensStreak(g, E.W * 0.57, E.H * 0.2, E.W * 1.1, '#ffe0b0', 0.14);
} });

// s002 · "You said that already." — medium on him; his gaze lifts only on the last word
registerShot('s002', { draw(g, t, info) {
  const cam = { z: 1.04 + 0.05 * ease.inOut(prog(t, 0, info.dur)), x: 26 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);
  const lookUp = on(info, t, 'already', 1.5, 0.38);
  layer(g, cam, 1, (g) => {
    person(g, 'nils', { x: seats.nils, y: GY, s: S_MED(), facing: 1,
      pose: posesAt(t, [[0, POSES.sit], [lookUp, POSES.relaxed]]),
      expr: t > lookUp ? 'worried' : 'neutral',
      look: t > lookUp ? [0.35, -0.10] : [0.05, 0.85],
      talk: speak(info, t, 0.05, 1.0), moodName: 'midnight' });
  });
  counterFace(g, cam, GY);
  // her shoulder, close and out of focus at frame right — geography says who he is looking at
  blurLayer(g, 15, (g) => person(g, 'rae', { x: E.W * 1.06, y: GY + V(250, 200), s: V(3.2, 3.4),
    facing: -1, pose: POSES.relaxed, expr: 'neutral', moodName: 'midnight' }));
} });

// s003 · "This time I mean it." — medium on her; hand up on 'mean', brow lifts on 'it'
registerShot('s003', { draw(g, t, info) {
  const cam = { z: 1.05 + 0.04 * ease.inOut(prog(t, 0, info.dur)), x: -22 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);
  const mean = on(info, t, 'mean', 2.8, 0.46);
  const it = on(info, t, 'it', 3.3, 0.78);
  layer(g, cam, 1, (g) => {
    person(g, 'rae', { x: seats.rae, y: GY, s: S_MED(), facing: -1,
      pose: posesAt(t, [[0, POSES.relaxed], [mean, POSES.point]]),
      face: { brow: 0.20 + 0.62 * clamp((t - it) * 3), browTilt: 0.25,
              eyeWide: 0.22 + 0.30 * clamp((t - it) * 3), mouthCurve: -0.15, mouthOpen: 0.10,
              look: [-0.42, -0.05], blink: (t % 3.4) > 3.3 ? 0.9 : 0 },
      talk: speak(info, t, 0.05, 1.1), moodName: 'midnight' });
    wornBag(g, seats.rae, GY, S_MED(), -1);
  });
  blurLayer(g, 15, (g) => person(g, 'nils', { x: E.W * -0.06, y: GY + V(250, 200), s: V(3.2, 3.4),
    facing: 1, pose: POSES.sit, expr: 'neutral', moodName: 'midnight' }));
  FX.dust(g, t, { count: 16, color: '#ffe2bd', a: 0.18 });
} });

// s004 · "You took your keys." — insert on her hand, centre-frame. No acting; the object carries it.
registerShot('s004', { draw(g, t, info) {
  const cam = { z: 1.10 + 0.06 * ease.inOut(prog(t, 0, info.dur)) };
  // An insert gets a DELIBERATELY flat background. Blurring the whole kitchen here threw god-rays
  // and lamp glow into a shape that read as a ghost figure behind the hand.
  blurLayer(g, 13, (g) => {
    const M = mood('midnight');
    g.fillStyle = linGrad(g, 0, 0, 0, E.H, [[0, shade(M.wall, -0.52)], [1, shade(M.wall, -0.74)]]);
    g.fillRect(-E.W, -E.H, E.W * 4, E.H * 4);
    glow(g, E.W * 0.80, E.H * 0.16, V(560, 460), M.practical, 0.16);
    g.fillStyle = alpha('#000000', 0.22); g.fillRect(-E.W, E.H * 0.74, E.W * 4, E.H);   // counter edge
  });
  const ink = '#15131a', outfit = '#2f9e8f';
  const hx = E.W * 0.42, hy = E.H * 0.40, K = V(1, 0.9);      // insert scale, portrait slightly smaller
  const swing = Math.sin(t * 2.4) * 0.05;
  layer(g, cam, 1, (g) => {
    const { kx, ky } = keysHand(g, hx, hy, K, swing);
    glow(g, kx, ky + 52 * K, 260 * K, '#ffe9b8', 0.13);
  });
  FX.sparkle(g, hx - 26 * K, hy + 140 * K, V(30, 26), '#ffe9b8', 0.45);
} });
