// chars/acting.js — named acting states for Ink Bean, on top of the continuous face parameters.
//
// Why this exists: `beanFace`/`drawInkBean` already take continuous numbers, which is right — a turn
// has to interpolate. But writing those numbers from scratch in every shot is slow and drifts. This
// file gives a small, fixed vocabulary of STATES plus a `beat()` helper that moves between them with
// the timing offset that makes a face read as a thought instead of a switch.
//
// Method adapted from JohnHeibel/ClaudeAnimationBase (MIT): eyes lead, brows follow, mouth lands
// last; faces act instead of snapping. No code was copied — this is a clean-room implementation for
// this engine. See THIRD_PARTY.md.
//
// FIXED (2026-11-08): `browTilt` in `chars/inkbean.js` used to tilt only the left brow; the right
// brow's endpoints resolved to the same y. The inner endpoint now uses `bh + tilt` for both brows, so
// the 12 presets below read symmetrically in close-up. Eyes and mouth were never affected.
//
// Usage:
//   import { actingFace, beat, blink } from '/chars/acting.js';
//
//   // a held state, with one override
//   face: actingFace('hurt', { eyeWide: 0.22 })
//
//   // a turn: eyes arrive first, brows 0.10 s later, mouth 0.25 s later
//   face: beat(t, [
//     { at: 0.00, face: 'neutral' },
//     { at: 0.60, face: 'hurt' },
//   ])
//
//   // blink at 0.7 s and 1.9 s
//   face: { ...actingFace('listening'), blink: blink(t, [0.7, 1.9]) }
//
// The returned object is exactly the `face` object `drawInkBean`/`beanFace` expect. It never sets
// `talk`, and it only carries `blink` if you pass one as an override. Blinks are transients, not
// states to interpolate between cues: use `blink()` separately and spread it in.

const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
const clamp01 = (x) => clamp(x, 0, 1);
const lerp = (a, b, u) => a + (b - a) * u;
const smooth = (u) => u * u * (3 - 2 * u);
const copyLook = (v) => [clamp(Number(v && v[0]) || 0, -1, 1), clamp(Number(v && v[1]) || 0, -1, 1)];

// Twelve states. Values are deliberately conservative: the style bible's faces are minimal, and a
// giant close-up amplifies every extra unit. Override per shot rather than adding more presets.
export const PRESETS = {
  neutral:    { brow: 0.15, browTilt:  0.00, eyeWide: 0.10, mouthOpen: 0.05, mouthCurve:  0.15, look: [ 0.00,  0.00] },
  listening:  { brow: 0.25, browTilt:  0.10, eyeWide: 0.18, mouthOpen: 0.02, mouthCurve:  0.05, look: [ 0.15,  0.00] },
  curious:    { brow: 0.55, browTilt:  0.15, eyeWide: 0.35, mouthOpen: 0.05, mouthCurve:  0.20, look: [ 0.35, -0.05] },
  worried:    { brow: 0.55, browTilt: -0.55, eyeWide: 0.35, mouthOpen: 0.10, mouthCurve: -0.35, look: [-0.10,  0.05] },
  hurt:       { brow: 0.30, browTilt: -0.75, eyeWide: 0.10, mouthOpen: 0.12, mouthCurve: -0.55, look: [-0.25,  0.10] },
  angry:      { brow: 0.05, browTilt:  0.85, eyeWide: 0.20, mouthOpen: 0.10, mouthCurve: -0.55, look: [ 0.20, -0.05] },
  surprised:  { brow: 0.85, browTilt:  0.35, eyeWide: 0.85, mouthOpen: 0.65, mouthCurve:  0.00, look: [ 0.00,  0.00] },
  relieved:   { brow: 0.30, browTilt:  0.10, eyeWide: 0.05, mouthOpen: 0.15, mouthCurve:  0.45, look: [ 0.00,  0.10] },
  hopeful:    { brow: 0.50, browTilt:  0.05, eyeWide: 0.25, mouthOpen: 0.05, mouthCurve:  0.40, look: [ 0.10, -0.15] },
  tired:      { brow: 0.10, browTilt: -0.25, eyeWide: 0.02, mouthOpen: 0.08, mouthCurve: -0.15, look: [ 0.00,  0.25] },
  ashamed:    { brow: 0.20, browTilt: -0.60, eyeWide: 0.05, mouthOpen: 0.02, mouthCurve: -0.30, look: [-0.30,  0.25] },
  determined: { brow: 0.15, browTilt:  0.45, eyeWide: 0.15, mouthOpen: 0.05, mouthCurve:  0.05, look: [ 0.25, -0.05] },
};

const KEYS = ['brow', 'browTilt', 'eyeWide', 'mouthOpen', 'mouthCurve'];
// The ranges `drawInkBean`/`beanFace` document. Clamp here so a bad override pins to the documented
// limit instead of drawing a negative eyelid or an eye outside the skull.
const RANGE = {
  brow: [-1, 1], browTilt: [-1, 1], eyeWide: [0, 1], mouthOpen: [0, 1], mouthCurve: [-1, 1],
};

// One named state, with optional overrides. Always returns a fresh object, so a shot can mutate it
// without changing the vocabulary for the next shot.
export function actingFace(name = 'neutral', over = {}) {
  const base = PRESETS[name];
  if (!base) throw new Error(`unknown acting preset: ${name}`);
  const out = { ...base, ...over };
  out.look = over.look ? copyLook(over.look) : copyLook(base.look);
  for (const key of KEYS) {
    const v = out[key] === undefined || out[key] === null ? base[key] : out[key];
    out[key] = clamp(Number(v) || 0, RANGE[key][0], RANGE[key][1]);
  }
  if ('blink' in out) out.blink = clamp01(Number(out.blink) || 0);
  return out;
}

// Resolve a cue to a full face object. A cue may name a preset (with optional overrides), carry a
// partial face, or carry the parameters directly: { at: 1.2, brow: 0.8 }.
function cueFace(cue) {
  const { at, face, ...rest } = cue;
  if (typeof face === 'string') return actingFace(face, rest);
  if (face && typeof face === 'object') return actingFace('neutral', { ...face, ...rest });
  return actingFace('neutral', rest);
}

function sample(cues, t, key) {
  if (t <= cues[0].at) return cues[0].vals[key];
  const last = cues[cues.length - 1];
  if (t >= last.at) return last.vals[key];
  for (let i = 0; i < cues.length - 1; i++) {
    const a = cues[i], b = cues[i + 1];
    if (t >= a.at && t <= b.at) {
      const span = b.at - a.at;
      const u = span <= 0 ? 1 : smooth(clamp01((t - a.at) / span));
      return lerp(a.vals[key], b.vals[key], u);
    }
  }
  return last.vals[key];
}

// Move through a list of cues. `lag` shifts a parameter's whole interpolation later: with the
// defaults, the eyes reach the cue target on the beat, the brows 0.10 s later and the mouth 0.25 s
// later — and the mouth starts moving later as well. A cue at the same time as the previous one is
// treated as an instant change.
export function beat(t, cues, opts = {}) {
  if (!Array.isArray(cues) || cues.length === 0) throw new Error('beat() needs at least one cue');
  const T = Number(t);
  if (!Number.isFinite(T)) throw new Error('beat() needs a finite time');
  const lag = {
    brow: 0.10,
    browTilt: 0.10,
    mouthOpen: 0.25,
    mouthCurve: 0.25,
    look: 0.00,
    ...(opts.lag || {}),
  };
  const ordered = cues
    .map((c) => ({ at: Number(c.at) || 0, vals: cueFace(c) }))
    .sort((a, b) => a.at - b.at);
  const out = {};
  for (const k of KEYS) out[k] = clamp(sample(ordered, T - (lag[k] || 0), k), RANGE[k][0], RANGE[k][1]);
  // `look` is a pair, not a scalar; sample its two components from the resolved cue faces.
  const lookT = T - (lag.look || 0);
  const lx = ordered.map((c) => ({ at: c.at, vals: { v: c.vals.look[0] } }));
  const ly = ordered.map((c) => ({ at: c.at, vals: { v: c.vals.look[1] } }));
  out.look = [
    clamp(sample(lx, lookT, 'v'), -1, 1),
    clamp(sample(ly, lookT, 'v'), -1, 1),
  ];
  return out;
}

// A blink at one or more absolute times. Returns 0 outside a blink, and a 0..1 lid value inside it.
export function blink(t, times, dur = 0.12) {
  const d = Number(dur);
  if (!(d > 0)) return 0;
  let v = 0;
  for (const at of times || []) {
    const a0 = Number(at);
    if (!Number.isFinite(a0)) continue;
    if (t >= a0 && t <= a0 + d) {
      v = Math.max(v, Math.sin(clamp01((t - a0) / d) * Math.PI));
    }
  }
  return v;
}

// Blend two face objects. Useful when a shot hands a face between two states without cue times.
export function mixFaces(a, b, u = 0.5) {
  const k = clamp01(u);
  const out = {};
  for (const key of KEYS) {
    out[key] = clamp(lerp(a[key] ?? 0, b[key] ?? 0, k), RANGE[key][0], RANGE[key][1]);
  }
  out.look = [
    clamp(lerp((a.look || [0, 0])[0], (b.look || [0, 0])[0], k), -1, 1),
    clamp(lerp((a.look || [0, 0])[1], (b.look || [0, 0])[1], k), -1, 1),
  ];
  return out;
}
