// shots/act4.js — s012..s013: the turn paid off, and the opening frame returned with one thing on it.
import { E, V, S, registerShot, mood, layer, blurLayer, veil, ease, prog, clamp, lerp,
         glow, seg, circle, linGrad, shade, alpha } from '/engine/core.js';
import { POSES, breathe } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import * as UI from '/engine/ui2d.js';
import { kitchen, SEATS, DOOR_X, COUNTER_Y, keys, heldBag, counterFace, nilsAtCounter } from '../sets/kitchen.js';
import { person, speak, S_WIDE, S_MED } from '../blocking.js';

const AT_DOOR = () => DOOR_X() - V(250, 220);

// s012 · "One more night." — medium on her. The bag is off the shoulder now, held. She looks at him
// for the first time since the door, and only then speaks.
registerShot('s012', { draw(g, t, info) {
  const cam = { z: 1.06 + 0.03 * ease.inOut(prog(t, 0, info.dur)), x: -40 + 18 * ease.inOut(prog(t, 0, info.dur)) };
  const { GY, seats } = kitchen(g, t, cam);
  const x = AT_DOOR();

  const arrive = ease.inOut(prog(t, 0.06, 0.46));             // the gaze comes off the door first
  const soften = ease.inOut(prog(t, 0.40, 1.05));

  layer(g, cam, 1, (g) => {
    person(g, 'rae', { x, y: GY, s: S_MED() * 1.05, facing: -1,
      pose: breathe(POSES.relaxed, t, 0.8, 5), expr: 'neutral',
      face: { brow: lerp(0.42, 0.16, soften), browTilt: lerp(0.10, -0.34, soften),
              eyeWide: lerp(0.34, 0.20, soften), mouthOpen: 0.05,
              mouthCurve: lerp(-0.26, 0.06, soften),
              look: [lerp(0.78, -0.34, arrive), lerp(-0.10, -0.04, arrive)],
              blink: (t > 0.20 && t < 0.38) ? Math.sin(prog(t, 0.20, 0.38) * Math.PI) : 0 },
      talk: speak(info, t, 0.48, 1.18), moodName: 'midnight' });
    // the bag hangs from the hand nearest him, so it is between them, not behind her
    heldBag(g, x - 20 * S_MED() * 1.05, GY - 104 * S_MED() * 1.05, S_MED() * 1.05);
  });
  counterFace(g, cam, GY);

  glow(g, E.W * 0.30, E.H * 0.50, V(520, 480), '#5f7bc4', 0.14);   // him, off-frame, as a presence
  FX.dust(g, t, { count: 16, color: '#cfe0ff', a: 0.18 });
  FX.lensStreak(g, E.W * 0.52, E.H * 0.2, E.W * 1.05, '#ffe0b0', 0.11);
} });

// s013 · "One more night." (he repeats it) — slow pull-out back to the opening wide, with the keys
// now on the counter between them. She almost smiles. The question rises over the last second.
registerShot('s013', { draw(g, t, info) {
  const pull = ease.inOut(prog(t, 0, info.dur));
  const cam = { z: lerp(1.18, 1.00, pull), x: lerp(24, -20, pull) };   // ends where s001 began
  const { GY, seats } = kitchen(g, t, cam);
  const x = lerp(AT_DOOR(), E.W * 0.66, ease.inOut(prog(t, 0.2, info.dur)));

  nilsAtCounter(g, cam, seats, GY, {
    s: S_WIDE(),
    face: { brow: 0.22, browTilt: -0.30, eyeWide: 0.18, mouthOpen: 0.05, mouthCurve: -0.14,
            look: [-0.30, -0.06], blink: (t % 3.3) > 3.2 ? 0.9 : 0 },
    look: [-0.30, -0.06], talk: speak(info, t, 0.34, 1.24),
  });

  layer(g, cam, 1, (g) => {
    const almost = ease.inOut(prog(t, 0.90, 1.72));            // it stops short of a smile on purpose
    person(g, 'rae', { x, y: GY, s: S_WIDE() * 1.02, facing: -1,
      pose: breathe(POSES.relaxed, t, 0.9, 5), expr: 'neutral',
      face: { brow: lerp(0.34, 0.14, almost), browTilt: lerp(0.06, -0.30, almost),
              eyeWide: 0.18, mouthOpen: 0.04, mouthCurve: lerp(-0.10, 0.20, almost),
              look: [-0.40, -0.05], blink: (t > 1.5 && t < 1.68) ? Math.sin(prog(t, 1.5, 1.68) * Math.PI) : 0 },
      moodName: 'midnight' });
    heldBag(g, x - 20 * S_WIDE() * 1.02, GY - 104 * S_WIDE() * 1.02, S_WIDE() * 1.02);
  });

  // the keys, lying flat on the counter between them — drawn after the repaint or the counter eats them
  const kx = (seats.nils + x) / 2 + V(30, 24), ky = COUNTER_Y() - V(6, 5);
  layer(g, cam, 0.86, (g) => {
    keys(g, kx, ky, V(1.35, 1.2), -1.32);
    glow(g, kx, ky, V(150, 130), '#ffe9b8', 0.10 + 0.08 * ease.inOut(prog(t, 0.6, 1.6)));
  });

  FX.dust(g, t, { count: 22, color: '#cfe0ff', a: 0.20 });
  FX.lensStreak(g, E.W * 0.55, E.H * 0.2, E.W * 1.1, '#ffe0b0', 0.13);

  // end card: the question arrives over the last second. It sits on the dark wall ABOVE both figures —
  // centred at mid-frame it landed on her face.
  UI.bigLine(g, t - 1.02, { str: 'IS THAT A REASON?', dur: 0.97, y: E.H * 0.275,
                            size: V(82, 70), color: S().ui.gold });
} });
