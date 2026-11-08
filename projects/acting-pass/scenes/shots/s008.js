// shots/s008.js — THE TEST SHOT. 2.04 s of silence on her face. No words, no cut, no gesture.
// Everything else in this film can be mediocre and still work; this one cannot.
//
// The turn is built from CONTINUOUS face parameters, staggered on purpose:
//   eyes narrow first, brows follow ~0.1 s later, the mouth is last at ~0.25 s.
// Simultaneous movement reads as a switch being flipped. Offset movement reads as a thought arriving.
import { E, V, registerShot, mood, layer, blurLayer, veil, ease, prog, clamp, lerp, glow } from '/engine/core.js';
import * as FX from '/engine/fx2d.js';
import { beanFace } from '/chars/inkbean.js';
import { RAE } from '../cast.js';

const HOLD = 1.10;                       // 1.10 s of nothing, then the turn

function doorPlate(g, t, cam) {
  const M = mood('midnight'), GY = E.H * V(0.80, 0.70);
  layer(g, cam, 0.2, (g) => {
    g.fillStyle = M.sky[0]; g.fillRect(-E.W, -E.H, E.W * 4, E.H * 3);
    const dx = E.W * 0.62, dy = GY - V(620, 520), dw = V(300, 260), dh = V(560, 520);
    g.fillStyle = '#0d1226'; g.fillRect(dx - dw / 2, dy, dw, dh);
    g.strokeStyle = '#26304f'; g.lineWidth = 8; g.strokeRect(dx - dw / 2, dy, dw, dh);
    glow(g, dx - dw * 0.1, dy + dh * 0.55, V(180, 150), '#c8d8ff', 0.10);
    g.fillStyle = '#141a33'; g.fillRect(-E.W, GY, E.W * 4, E.H);
    FX.floorLines(g, GY, GY + 400, 'rgba(0,0,0,.35)', 0.1);
  });
}

registerShot('s008', { draw(g, t, info) {
  const cam = { z: 1.02 + 0.02 * ease.inOut(prog(t, 0, info.dur)) };   // almost still, never quite

  blurLayer(g, 16, (g) => doorPlate(g, t, { z: 1.55, x: -120, y: -90 }));
  veil(g, '#080b18', 0.40);

  // FIX 3b — a soft pool behind her head, so the silhouette separates without touching the design
  glow(g, E.W / 2 + V(30, 20), E.H * V(0.50, 0.46), V(560, 520), '#5f7bc4', 0.22);
  glow(g, E.W / 2 + V(30, 20), E.H * V(0.50, 0.46), V(300, 280), '#8fa8e0', 0.14);

  const turn = ease.inOut(prog(t, HOLD, HOLD + 0.70));
  // a blink immediately before the softening — it is what sells the switch as internal
  const blink = (t > 0.98 && t < 1.16) ? Math.sin(prog(t, 0.98, 1.16) * Math.PI) : 0;

  const face = {
    brow:       lerp(0.72, 0.18, ease.inOut(prog(t, HOLD + 0.10, HOLD + 0.62))),
    browTilt:   lerp(0.30, -0.42, ease.inOut(prog(t, HOLD + 0.10, HOLD + 0.62))),
    eyeWide:    lerp(0.55, 0.18, ease.inOut(prog(t, HOLD + 0.00, HOLD + 0.45))),
    mouthOpen:  lerp(0.06, 0.13, ease.inOut(prog(t, HOLD + 0.25, HOLD + 0.80))),
    mouthCurve: lerp(-0.30, 0.24, ease.out(prog(t, HOLD + 0.25, HOLD + 0.80))),
    look:       [lerp(-0.45, 0.12, ease.inOut(prog(t, HOLD + 0.05, HOLD + 0.75))),
                 lerp(-0.15, 0.02, ease.inOut(prog(t, HOLD + 0.05, HOLD + 0.75)))],
    blink,
  };

  // the head drifts a few pixels toward him as the gaze arrives — body agrees with face late
  const R = V(300, 330) * (1 + 0.03 * ease.inOut(prog(t, 0, info.dur)));
  const cx = E.W / 2 + V(30, 20) + lerp(14, -10, turn);
  const cy = E.H * V(0.54, 0.50) + lerp(0, -8, turn);

  beanFace(g, cx, cy, R, {
    moodName: 'midnight', outfit: RAE, face, rimSide: -1, shoulders: true, seedBase: 1,
    facing: -1 });                       // she turns toward him, frame left, so her rear is frame right

  FX.dust(g, t, { count: 14, color: '#cfe0ff', a: 0.16 });
} });
