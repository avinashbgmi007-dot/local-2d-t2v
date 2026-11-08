// shots/act2.js — s005..s007: she crosses to the door and he finally speaks.
// s005 is the physical-action test (a real gait, not a slide); s006 refuses the exchange; s007 has
// to be delivered quiet or the whole scene tips.
import { E, V, registerShot, layer, blurLayer, veil, ease, prog, clamp, lerp,
         glow, seg, circle, shade } from '/engine/core.js';
import { POSES, breathe, walkPose, blendPose } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import { kitchen, SEATS, DOOR_X, wornBag, counterFace, nilsAtCounter } from '../sets/kitchen.js';
import { person, face, speak, S_WIDE, S_MED } from '../blocking.js';

const DOOR_W = () => V(230, 200), DOOR_H = () => V(430, 560);
const HANDLE = () => [DOOR_X() - DOOR_W() * 0.32, E.H * V(0.80, 0.70) - DOOR_H() * 0.46];
const WALK_END = () => DOOR_X() - V(164, 150);      // feet land here; her hand then finds the latch
const STEP_T = 1.42;                                 // four footfalls, then the reach

// s005 · SILENCE 1.64s — she crosses to the door. Four footsteps, hand on the latch, no look back.
registerShot('s005', { draw(g, t, info) {
  const cam = { z: 1.0 + 0.014 * ease.inOut(prog(t, 0, info.dur)), x: -9 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);

  // x is driven by the gait, not by a separate tween, so feet and body agree
  const gp = clamp(t / STEP_T);
  const gait = walkPose(gp * 4 * Math.PI, { stride: 26, lift: 13, bob: 3.4 });   // 2 cycles = 4 steps
  const x = lerp(seats.rae, WALK_END(), gp);
  const touch = { ...POSES.reach, eF: [42, -152], hF: [62, -137] };              // hF lands on the latch
  const pose = t > STEP_T ? blendPose(gait, touch, ease.inOut(prog(t, STEP_T, STEP_T + 0.16))) : gait;

  layer(g, cam, 1, (g) => {
    person(g, 'nils', { x: seats.nils, y: GY, s: S_WIDE(), facing: 1,
      pose: breathe(POSES.sit, t, 1, 2), expr: 'neutral', look: [0.1, 0.75], moodName: 'midnight' });
    person(g, 'rae', { x, y: GY, s: S_WIDE(), facing: 1, pose, expr: 'neutral',
      look: [0.55, 0.05], moodName: 'midnight' });
    wornBag(g, x, GY, S_WIDE(), 1);
  });
  counterFace(g, cam, GY);

  // the latch catches the lamp exactly when her hand arrives — the beat is marked with light, not a cut
  const [hx, hy] = HANDLE();
  const arrive = prog(t, STEP_T, STEP_T + 0.20);
  if (arrive > 0) glow(g, hx, hy, V(120, 110) * (0.6 + 0.4 * arrive), '#ffe9b8', 0.30 * arrive);

  FX.dust(g, t, { count: 20, color: '#cfe0ff', a: 0.20 });
  FX.lensStreak(g, E.W * 0.55, E.H * 0.2, E.W * 1.05, '#ffe0b0', 0.12);
} });

// s006 · "So?" — close on her at the door. The chin lifts toward him; the eyes stay on the door.
registerShot('s006', { draw(g, t, info) {
  const cam = { z: 1.06 + 0.02 * ease.inOut(prog(t, 0, info.dur)) };
  blurLayer(g, 16, (g) => kitchen(g, 0, { z: 1.45, x: -560, y: -40 }));
  veil(g, '#080b18', 0.34);

  const lift = ease.inOut(prog(t, 0.30, 0.62));      // the word lands at 0.30 in this shot
  const cx = E.W * 0.545 + lerp(0, -18, lift);
  const cy = E.H * 0.52;
  const R = V(286, 320) * (1 + 0.015 * ease.inOut(prog(t, 0, info.dur)));

  glow(g, cx + V(120, 90), cy, V(520, 500), '#5f7bc4', 0.18);

  g.save();
  g.translate(cx, cy); g.rotate(lerp(0.055, -0.045, lift)); g.translate(-cx, -cy);
  face(g, 'rae', cx, cy, R, {
    moodName: 'midnight', rimSide: -1, shoulders: true, facing: 1,   // she faces the door, not him
    face: { brow: 0.34, browTilt: 0.18, eyeWide: 0.30,
            mouthOpen: 0.10 + 0.50 * prog(t, 0.28, 0.44) * (1 - prog(t, 0.46, 0.66)),
            mouthCurve: -0.22, look: [0.72, -0.12],
            blink: (t > 0.70 && t < 0.84) ? Math.sin(prog(t, 0.70, 0.84) * Math.PI) : 0 },
  });
  g.restore();

  FX.dust(g, t, { count: 10, color: '#cfe0ff', a: 0.14 });
} });

// s007 · "Last time you left, you left your keys." — medium on him, turned fully to her.
// Even light, no push.
registerShot('s007', { draw(g, t, info) {
  const cam = { z: 1.05 + 0.015 * ease.inOut(prog(t, 0, info.dur)), x: 14 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);

  // hands flat on the counter — see kitchen.nilsAtCounter for why the three passes are one call
  nilsAtCounter(g, cam, seats, GY, {
    s: S_MED(),
    face: { brow: 0.30, browTilt: -0.30, eyeWide: 0.24, mouthOpen: 0.06, mouthCurve: -0.30,
            look: [0.42, -0.06], blink: (t % 3.1) > 3.0 ? 0.9 : 0 },
    look: [0.42, -0.06], talk: speak(info, t, 0.06, 1.18),
  });

  FX.dust(g, t, { count: 12, color: '#ffe2bd', a: 0.16 });
  FX.lensStreak(g, E.W * 0.52, E.H * 0.19, E.W * 1.0, '#ffe0b0', 0.10);
} });
