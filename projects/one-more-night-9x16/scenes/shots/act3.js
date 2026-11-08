// shots/act3.js — s009..s011: she answers, he admits, and the decision is told by an object.
// s011 carries the film's signature device: a freeze-frame on the impact of the keys.
import { E, V, registerShot, mood, layer, blurLayer, veil, ease, prog, clamp, lerp,
         glow, circle, ring, linGrad, shade, alpha } from '/engine/core.js';
import { POSES, breathe } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import * as UI from '/engine/ui2d.js';
import { kitchen, SEATS, DOOR_X, COUNTER_Y, keys, wornBag, counterFace, keysHand, nilsAtCounter } from '../sets/kitchen.js';
import { person, on, speak, S_WIDE, S_MED } from '../blocking.js';

const IMPACT = 0.62;      // the keys touch the counter
const THAW = 1.30;        // time resumes

// s009 · "That's not a reason." — two-shot from the door. She has turned back and is saying it
// while still finishing the turn: the words and the body contradict each other on purpose.
registerShot('s009', { draw(g, t, info) {
  const cam = { z: 1.02 + 0.02 * ease.inOut(prog(t, 0, info.dur)), x: 96 - 26 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);
  const turn = ease.inOut(prog(t, 0.18, 1.20));          // 0.82 = three-quarters away, 1 = facing him
  const yx = lerp(0.82, 1.0, turn);                      // squash kept under 1.25x so the turn never reads as weight gain
  const raeX = DOOR_X() - V(250, 220);

  layer(g, cam, 1, (g) => {
    person(g, 'nils', { x: seats.nils, y: GY, s: S_WIDE() * 0.92, facing: 1,
      pose: breathe(POSES.sit, t, 1, 2), expr: 'neutral', look: [0.30, -0.10], moodName: 'midnight' });
    person(g, 'rae', { x: raeX, y: GY, s: S_MED() * 1.06, facing: -1, yx,
      pose: breathe(POSES.relaxed, t, 0.7, 5), expr: 'neutral',
      face: { brow: 0.30, browTilt: -0.18, eyeWide: 0.26, mouthOpen: 0.06, mouthCurve: -0.26,
              look: [lerp(-0.75, -0.30, turn), -0.04] },
      talk: speak(info, t, 0.05, 1.22), moodName: 'midnight' });
    wornBag(g, raeX, GY, S_MED() * 1.06, -1, { yx });
  });
  counterFace(g, cam, GY);

  FX.dust(g, t, { count: 18, color: '#cfe0ff', a: 0.18 });
  FX.lensStreak(g, E.W * 0.5, E.H * 0.2, E.W * 1.05, '#ffe0b0', 0.12);
} });

// s010 · "It's the only one I've got." — medium on him. He looks away first, down to the counter,
// on 'only one'. The admission is in the gaze break, not the face.
registerShot('s010', { draw(g, t, info) {
  const cam = { z: 1.06 + 0.02 * ease.inOut(prog(t, 0, info.dur)), x: 20 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);
  const away = on(info, t, 'only', 0.42, 0.42);
  const drop = ease.inOut(prog(t, away, away + 0.30));

  nilsAtCounter(g, cam, seats, GY, {
    s: S_MED(),
    face: { brow: 0.26, browTilt: -0.42, eyeWide: 0.20, mouthOpen: 0.06, mouthCurve: -0.34,
            look: [lerp(0.42, 0.06, drop), lerp(-0.06, 0.86, drop)],
            blink: drop > 0.15 && drop < 0.45 ? Math.sin((drop - 0.15) / 0.30 * Math.PI) : 0 },
    look: [lerp(0.42, 0.06, drop), lerp(-0.06, 0.86, drop)],
    talk: speak(info, t, 0.04, 0.80),
  });

  // her shoulder stays where the geography put it: soft, foreground, right of frame
  blurLayer(g, 15, (g) => person(g, 'rae', { x: E.W * 1.07, y: GY + V(250, 200), s: V(3.2, 3.4),
    facing: -1, pose: POSES.relaxed, expr: 'neutral', moodName: 'midnight' }));

  FX.dust(g, t, { count: 12, color: '#ffe2bd', a: 0.15 });
} });

// s011 · SILENCE 1.84s — the decision, told by an object. The keys land and the film freezes on the
// impact: dust and lamp-motes hang, the grade goes cool, a badge marks the factor, rings crawl out.
registerShot('s011', { draw(g, t, info) {
  // the clock itself is remapped: everything downstream reads ft, so the freeze is one line, not a
  // special case in each element
  const ft = t <= IMPACT ? t : (t < THAW ? IMPACT : IMPACT + (t - THAW));
  const frozen = t > IMPACT && t < THAW;

  const cam = { z: 1.10 + 0.06 * ease.inOut(prog(t, 0, info.dur)) };   // camera keeps moving; action stops
  const M = mood('midnight'), dark = shade(M.wall, -0.66);
  blurLayer(g, 13, (g) => {
    g.fillStyle = linGrad(g, 0, 0, 0, E.H, [[0, shade(M.wall, -0.52)], [1, shade(M.wall, -0.74)]]);
    g.fillRect(-E.W, -E.H, E.W * 4, E.H * 4);
    glow(g, E.W * 0.72, E.H * 0.14, V(560, 460), M.practical, 0.15);
    // the counter top is the stage for this shot, so it is painted flat, not derived from the set
    g.fillStyle = shade(dark, 0.52); g.fillRect(-E.W, COUNTER_Y(), E.W * 4, 14);
    g.fillStyle = linGrad(g, 0, COUNTER_Y(), 0, COUNTER_Y() + V(122, 112), [[0, shade(dark, 0.26)], [1, shade(dark, 0.02)]]);
    g.fillRect(-E.W, COUNTER_Y() + 14, E.W * 4, V(122, 112));
  });
  veil(g, '#080b18', 0.26);

  const K = V(1, 0.9);
  const topY = COUNTER_Y();
  const hx = E.W * 0.46;
  const hy = lerp(topY - V(250, 230) * K, topY - V(96, 90) * K, ease.in(prog(ft, 0.05, IMPACT)));
  const lift = frozen ? 0 : ease.out(prog(ft, THAW, info.dur));
  const handY = hy - lift * V(300, 280) * K;
  const open = prog(ft, 0.30, IMPACT);                       // fingers release on the way down

  layer(g, cam, 1, (g) => {
    const { kx, ky } = keysHand(g, hx, handY, K, (1 - open) * Math.sin(ft * 2.4) * 0.06 + lerp(0, -1.30, open), {
      arm: [[560, -430], [250, -150], [96, 20]], ry: 96 + lift * 40, ks: 3.2,
    });
    if (frozen) {                                            // rings crawl out of the impact point
      FX.rings(g, kx, ky + 30 * K, (t - IMPACT) * 0.22, { count: 3, r0: 40, r1: 260, color: '#cfe0ff', a: 0.34, speed: 0.5, w: 2.5 });
    }
  });

  // the impact itself: one hot frame, then a cool grade for the whole freeze
  const hit = prog(t, IMPACT, IMPACT + 0.06);
  if (t >= IMPACT && t < IMPACT + 0.22) {
    glow(g, hx - 52 * K, topY - 6, V(300, 260) * (1 + hit), '#ffffff', 0.34 * (1 - prog(t, IMPACT, IMPACT + 0.22)));
  }
  if (frozen) {
    veil(g, '#4a6ea8', 0.12 + 0.05 * ease.inOut(prog(t, IMPACT, THAW)));
    // y must clear the wide letterbox: the default badge row (y=110) is inside the black bar, so
    // the marker renders and is simply never visible
    UI.badge(g, { str: '1/4x', x: E.W - V(150, 120), y: E.H * 0.19, color: '#cfe0ff',
                  a: ease.inOut(prog(t, IMPACT, IMPACT + 0.12)) * (1 - prog(t, THAW - 0.12, THAW)) });
  }

  // motes are drawn at ft, so during the freeze they hang in the air instead of drifting
  FX.dust(g, ft, { count: frozen ? 26 : 20, color: '#cfe0ff', a: frozen ? 0.30 : 0.20 });
  FX.lensStreak(g, E.W * 0.5, E.H * 0.19, E.W * 1.05, '#ffe0b0', 0.12);
} });
