// chars/creature.js — the SUBJECT of the story, drawn as a body rather than a prop.
//
// Defect this file closes (owner report 2026-11-13): a film whose every line said
// "the dragon" showed two men in an office and no dragon. `fresh/shapes.py`
// substituted the subject noun into the dialogue and stopped there; nothing in
// the renderer could draw a noun that was not a person or a hand prop.
//
// Contract: drawCreature(g, o) draws ONE creature with its feet on o.y, side-on,
// facing o.facing. Units are the same as rig2d's stick figure (a ~120-unit tall
// adult), so a creature can be scaled with the same `s` a person uses.
//
// No imports: this file must not depend on engine internals, so it cannot break
// when a protected engine file is re-pinned by verify_kit.py.
//
// Every kind here is a silhouette a viewer can name in one frame at phone size.
// The vocabulary is CLOSED and exported (KINDS) so the story layer can only ask
// for something this file can actually draw — the same bug that made
// chars/markers.js throw on an advertised-but-missing marker.

// MUST be an array. Written as ('a','b','c') this is a comma EXPRESSION that
// evaluates to 'c', so `KINDS.indexOf('dragon')` threw and every subject fell
// back to the bear -- a bug a source-text test could not see.
export const KINDS = ['dragon', 'wolf', 'bird', 'fish', 'horse', 'cat', 'bear',
                      'jar', 'lantern', 'chest', 'sword'];

const TAU = Math.PI * 2;

function ell(g, x, y, rx, ry, rot) {
  g.beginPath();
  g.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), rot || 0, 0, TAU);
  g.fill();
}

function leg(g, x0, y0, x1, y1, w, col) {
  g.strokeStyle = col;
  g.lineWidth = w;
  g.lineCap = 'round';
  g.beginPath();
  g.moveTo(x0, y0);
  g.lineTo(x1, y1);
  g.stroke();
}

// ---- shared quadruped chassis -------------------------------------------------
// Returns the anchor points so a kind can hang its own head/tail on them.
function quadruped(g, k, col, dark, t) {
  const breathe = 1 + 0.018 * Math.sin(t * 2.1);
  // legs: front pair and back pair, splayed slightly so the body reads as weight
  for (const [fx, phase] of [[34, 0], [30, 0.4], [-34, 0.8], [-30, 1.2]]) {
    const swing = Math.sin(t * 1.6 + phase) * 2.4;
    leg(g, fx * k, -44 * k, (fx + swing) * k, -2 * k, 7 * k, dark);
  }
  // barrel body
  g.fillStyle = col;
  ell(g, 0, -46 * k, 46 * k, 24 * k * breathe, 0);
  // shoulder hump, so the front is not a symmetric oval
  ell(g, 22 * k, -56 * k, 22 * k, 17 * k * breathe, 0);
  return { neck: [40 * k, -62 * k], hip: [-40 * k, -50 * k] };
}

function tail(g, from, k, col, curl, t) {
  g.strokeStyle = col;
  g.lineWidth = 6 * k;
  g.lineCap = 'round';
  const sway = Math.sin(t * 1.9) * 3 * k;
  g.beginPath();
  g.moveTo(from[0], from[1]);
  g.quadraticCurveTo(from[0] - 26 * k, from[1] - 6 * k + sway,
                     from[0] - 40 * k, from[1] - curl * k + sway);
  g.stroke();
}

function eye(g, x, y, r, light) {
  g.fillStyle = light;
  ell(g, x, y, r, r, 0);
}

// ---- kinds -------------------------------------------------------------------
const DRAW = {
  // wings, horns, spiked tail, long snout. The default "big mythic animal".
  dragon(g, k, col, dark, light, t) {
    const { neck, hip } = quadruped(g, k, col, dark, t);
    const flap = Math.sin(t * 2.6) * 0.16;
    // Back spikes: the cheapest way to read "dragon" at phone size, and they
    // survive the wide shot where a wing can be a few pixels.
    g.fillStyle = dark;
    for (let i = 0; i < 4; i++) {
      const sx = (-26 + i * 17) * k;
      g.beginPath();
      g.moveTo(sx, -64 * k);
      g.lineTo(sx + 7 * k, -82 * k);
      g.lineTo(sx + 14 * k, -64 * k);
      g.fill();
    }
    // wing, drawn OVER the body: behind it, the fill vanished into the sky
    g.save();
    g.translate(6 * k, -70 * k);
    g.rotate(-0.42 + flap);
    g.fillStyle = dark;
    g.beginPath();
    g.moveTo(0, 0);
    g.quadraticCurveTo(-18 * k, -54 * k, -50 * k, -62 * k);
    g.quadraticCurveTo(-38 * k, -28 * k, -46 * k, -4 * k);
    g.quadraticCurveTo(-22 * k, -12 * k, 0, 0);
    g.fill();
    g.strokeStyle = light;          // a lit membrane edge, or the wing is a shadow
    g.globalAlpha = 0.45;
    g.lineWidth = 1.8 * k;
    g.stroke();
    g.globalAlpha = 1;
    g.restore();
    tail(g, hip, k, col, 16, t);
    // spiked tail tip
    g.fillStyle = dark;
    ell(g, hip[0] - 42 * k, hip[1] - 14 * k, 6 * k, 4 * k, -0.5);
    // neck + head
    g.strokeStyle = col;
    g.lineWidth = 17 * k;
    g.lineCap = 'round';
    g.beginPath();
    g.moveTo(neck[0], neck[1]);
    g.quadraticCurveTo(54 * k, -84 * k, 62 * k, -96 * k);
    g.stroke();
    g.fillStyle = col;
    ell(g, 66 * k, -100 * k, 15 * k, 10 * k, -0.22);      // skull
    ell(g, 82 * k, -96 * k, 13 * k, 7 * k, 0.10);          // snout
    // horns, long enough to survive a 160px-tall draw
    g.strokeStyle = dark;
    g.lineWidth = 5 * k;
    for (const dx of [0, 8]) {
      g.beginPath();
      g.moveTo((60 + dx) * k, -108 * k);
      g.lineTo((54 + dx) * k, -126 * k);
      g.stroke();
    }
    eye(g, 70 * k, -103 * k, 3 * k, light);
  },

  wolf(g, k, col, dark, light, t) {
    const { neck, hip } = quadruped(g, k, col, dark, t);
    tail(g, hip, k, col, 20, t);
    g.fillStyle = col;
    ell(g, neck[0] + 12 * k, neck[1] - 18 * k, 16 * k, 14 * k, -0.1);   // skull
    ell(g, neck[0] + 28 * k, neck[1] - 12 * k, 11 * k, 6 * k, 0.16);    // muzzle
    g.fillStyle = dark;                                                 // ears
    for (const dx of [-2, 12]) {
      g.beginPath();
      g.moveTo((neck[0] + dx) * k, neck[1] - 28 * k);
      g.lineTo((neck[0] + dx + 4) * k, neck[1] - 42 * k);
      g.lineTo((neck[0] + dx + 9) * k, neck[1] - 27 * k);
      g.fill();
    }
    eye(g, neck[0] + 20 * k, neck[1] - 21 * k, 2.4 * k, light);
  },

  horse(g, k, col, dark, light, t) {
    const { neck, hip } = quadruped(g, k, col, dark, t);
    tail(g, hip, k, dark, 26, t);
    g.strokeStyle = col;                       // long neck
    g.lineWidth = 15 * k;
    g.beginPath();
    g.moveTo(neck[0], neck[1]);
    g.lineTo(neck[0] + 20 * k, neck[1] - 34 * k);
    g.stroke();
    g.fillStyle = col;
    ell(g, neck[0] + 30 * k, neck[1] - 44 * k, 15 * k, 9 * k, 0.42);
    g.fillStyle = dark;                        // mane
    g.beginPath();
    g.moveTo(neck[0] - 2 * k, neck[1] - 6 * k);
    g.lineTo(neck[0] + 8 * k, neck[1] - 40 * k);
    g.lineTo(neck[0] + 18 * k, neck[1] - 34 * k);
    g.fill();
    eye(g, neck[0] + 34 * k, neck[1] - 47 * k, 2.3 * k, light);
  },

  bear(g, k, col, dark, light, t) {
    const { neck, hip } = quadruped(g, k, col, dark, t);
    g.fillStyle = col;
    ell(g, neck[0] + 8 * k, neck[1] - 10 * k, 17 * k, 16 * k, 0);       // big round skull
    ell(g, neck[0] + 22 * k, neck[1] - 4 * k, 9 * k, 7 * k, 0.1);       // muzzle
    g.fillStyle = dark;
    ell(g, neck[0] - 2 * k, neck[1] - 24 * k, 6 * k, 6 * k, 0);         // ears
    ell(g, neck[0] + 16 * k, neck[1] - 22 * k, 6 * k, 6 * k, 0);
    eye(g, neck[0] + 16 * k, neck[1] - 12 * k, 2.4 * k, light);
  },

  cat(g, k, col, dark, light, t) {
    const { neck, hip } = quadruped(g, k, col, dark, t);
    tail(g, hip, k, col, 30, t);
    g.fillStyle = col;
    ell(g, neck[0] + 10 * k, neck[1] - 12 * k, 14 * k, 13 * k, 0);
    g.fillStyle = dark;                                                 // pointed ears
    for (const dx of [0, 14]) {
      g.beginPath();
      g.moveTo((neck[0] + dx) * k, neck[1] - 22 * k);
      g.lineTo((neck[0] + dx + 2) * k, neck[1] - 36 * k);
      g.lineTo((neck[0] + dx + 8) * k, neck[1] - 22 * k);
      g.fill();
    }
    eye(g, neck[0] + 16 * k, neck[1] - 15 * k, 2.2 * k, light);
  },

  // Bipeds: drawn standing, feet on the ground line.
  bird(g, k, col, dark, light, t) {
    const bob = Math.sin(t * 3.4) * 1.6 * k;
    for (const dx of [-5, 5]) leg(g, dx * k, -26 * k, dx * k, -2 * k, 3.2 * k, dark);
    g.fillStyle = col;
    ell(g, 0, -46 * k + bob, 20 * k, 24 * k, 0);                       // body
    ell(g, 14 * k, -74 * k + bob, 12 * k, 11 * k, 0);                  // head
    g.fillStyle = dark;                                                // beak
    g.beginPath();
    g.moveTo(25 * k, -76 * k + bob);
    g.lineTo(40 * k, -72 * k + bob);
    g.lineTo(25 * k, -69 * k + bob);
    g.fill();
    g.fillStyle = dark;                                                // folded wing
    ell(g, -6 * k, -48 * k + bob, 13 * k, 9 * k, 0.3);
    eye(g, 18 * k, -77 * k + bob, 2.2 * k, light);
  },

  // ---- OBJECTS -----------------------------------------------------------
  // Not every subject is an animal. "a jar that never empties" is a real short
  // and the old pipeline drew a mug. These four stand on the ground line like
  // a body does, so the same blocking works for them.
  jar(g, k, col, dark, light, t) {
    g.fillStyle = col;
    g.beginPath();
    g.moveTo(-30 * k, -2 * k);
    g.quadraticCurveTo(-38 * k, -40 * k, -26 * k, -62 * k);
    g.lineTo(26 * k, -62 * k);
    g.quadraticCurveTo(38 * k, -40 * k, 30 * k, -2 * k);
    g.fill();
    g.fillStyle = dark;                       // lid
    g.fillRect(-30 * k, -70 * k, 60 * k, 10 * k);
    g.fillRect(-14 * k, -78 * k, 28 * k, 8 * k);
    g.strokeStyle = dark;                     // rim + a lit highlight
    g.lineWidth = 2 * k;
    g.beginPath();
    g.moveTo(-32 * k, -52 * k);
    g.lineTo(32 * k, -52 * k);
    g.stroke();
    g.fillStyle = light;
    g.globalAlpha = 0.28;
    ell(g, -14 * k, -36 * k, 4 * k, 12 * k, 0.2);
    g.globalAlpha = 1;
  },

  lantern(g, k, col, dark, light, t) {
    const glowA = 0.55 + 0.12 * Math.sin(t * 2.4);
    g.strokeStyle = dark;                     // handle
    g.lineWidth = 4 * k;
    g.beginPath();
    g.arc(0, -86 * k, 16 * k, Math.PI, 0);
    g.stroke();
    g.fillStyle = dark;                       // cap and base
    g.fillRect(-24 * k, -76 * k, 48 * k, 8 * k);
    g.fillRect(-26 * k, -6 * k, 52 * k, 8 * k);
    g.fillStyle = col;                        // glass body
    g.fillRect(-20 * k, -68 * k, 40 * k, 62 * k);
    g.fillStyle = light;                      // the flame, and it breathes
    g.globalAlpha = glowA;
    ell(g, 0, -38 * k, 11 * k, 17 * k, 0);
    g.globalAlpha = 1;
  },

  chest(g, k, col, dark, light, t) {
    g.fillStyle = col;
    g.fillRect(-44 * k, -46 * k, 88 * k, 44 * k);
    g.beginPath();                            // domed lid
    g.moveTo(-44 * k, -46 * k);
    g.quadraticCurveTo(0, -92 * k, 44 * k, -46 * k);
    g.fill();
    g.fillStyle = dark;
    g.fillRect(-46 * k, -50 * k, 92 * k, 7 * k);   // lid seam
    g.fillRect(-7 * k, -34 * k, 14 * k, 20 * k);   // lock plate
    g.strokeStyle = dark;
    g.lineWidth = 3 * k;
    g.strokeRect(-44 * k, -46 * k, 88 * k, 44 * k);
  },

  sword(g, k, col, dark, light, t) {
    g.fillStyle = light;                      // blade, planted point-down
    g.beginPath();
    g.moveTo(-6 * k, -8 * k);
    g.lineTo(-6 * k, -96 * k);
    g.lineTo(0, -112 * k);
    g.lineTo(6 * k, -96 * k);
    g.lineTo(6 * k, -8 * k);
    g.fill();
    g.fillStyle = dark;                       // guard and grip
    g.fillRect(-26 * k, -102 * k, 52 * k, 8 * k);
    g.fillRect(-5 * k, -128 * k, 10 * k, 26 * k);
    g.fillStyle = col;
    ell(g, 0, -132 * k, 7 * k, 7 * k, 0);
  },

  fish(g, k, col, dark, light, t) {
    const sway = Math.sin(t * 2.2) * 0.12;
    g.save();
    g.translate(0, -52 * k);
    g.rotate(sway);
    g.fillStyle = col;
    ell(g, 0, 0, 34 * k, 18 * k, 0);                                   // body
    g.fillStyle = dark;                                                // tail fin
    g.beginPath();
    g.moveTo(-30 * k, 0);
    g.lineTo(-52 * k, -16 * k);
    g.lineTo(-46 * k, 0);
    g.lineTo(-52 * k, 16 * k);
    g.fill();
    g.beginPath();                                                     // dorsal fin
    g.moveTo(-6 * k, -16 * k);
    g.lineTo(4 * k, -30 * k);
    g.lineTo(14 * k, -14 * k);
    g.fill();
    eye(g, 22 * k, -4 * k, 2.6 * k, light);
    g.restore();
  },
};

// Horizontal centre of each drawing in its own units. The first render put the
// anchor at the HIND FOOT, so a macro dragon's head landed 630px off-frame and
// the insert read as a blue blob. Callers pass the visual centre.
const CENTRE = { dragon: 20, wolf: 14, horse: 16, bear: 12, cat: 12, bird: 8, fish: 0,
                 jar: 0, lantern: 0, chest: 0, sword: 0 };

// ---- public entry ------------------------------------------------------------
// o = { x, y, s, kind, facing, t, color, ink, light, shadow }
export function drawCreature(g, o = {}) {
  const kind = KINDS.indexOf(o.kind) >= 0 ? o.kind : 'bear';
  const k = (o.s == null ? 1 : o.s) * (o.scale == null ? 1 : o.scale);
  const col = o.color || '#4a4458';
  const dark = o.dark || '#1b1826';
  const light = o.light || '#f4efe6';
  const t = o.t || 0;
  const facing = o.facing === -1 ? -1 : 1;

  g.save();
  g.translate(o.x || 0, o.y || 0);
  g.scale(facing * k, k);
  g.translate(-CENTRE[kind], 0);
  if (o.shadow !== false) {                       // contact shadow, same idea as person()
    g.fillStyle = 'rgba(0,0,0,0.22)';
    g.beginPath();
    g.ellipse(0, 0, 52, 7, 0, 0, TAU);
    g.fill();
  }
  (DRAW[kind] || DRAW.bear)(g, 1, col, dark, light, t);
  g.restore();
}

// A macro version for the INSERT shot: the subject, filling the frame.
// The CALLER supplies an absolute size, because only the shot knows the frame
// width; the earlier fixed x3.2 multiplier made the subject 2.5 frames wide.
export function drawCreatureMacro(g, o = {}) { drawCreature(g, o); }

export default drawCreature;
