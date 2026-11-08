// blocking.js — one place that knows who the characters are, so no shot can invent its own version.
import { V, ease, prog, clamp, lerp, wordTime, talkAmount } from '/engine/core.js';
import { drawInkBean, beanFace } from '/chars/inkbean.js';
import { RAE, NILS } from './cast.js';

const WHO = { rae: { outfit: RAE, seed: 1 }, nils: { outfit: NILS, seed: 2 } };

export function person(g, who, o) {
  const w = WHO[who];
  drawInkBean(g, { ...o, outfit: o.outfit || w.outfit, seedBase: o.seedBase ?? w.seed });
}
export function face(g, who, cx, cy, R, o) {
  const w = WHO[who];
  beanFace(g, cx, cy, R, { ...o, outfit: o.outfit || w.outfit, seedBase: o.seedBase ?? w.seed });
}

// global word time converted to time-within-this-shot, with a fallback when Whisper mangles a token
export function on(info, t, word, after, fb) {
  const gt = wordTime(word, after);
  return gt === null ? fb : gt - (info.globalT - t);
}

// talk amount for a line that occupies [from,to] in SHOT-local time. talkAmount is keyed on global
// time, so passing shot-local numbers straight through silently mutes every shot after the first.
export function speak(info, t, from, to) {
  const g0 = info.globalT - t;                      // this shot's start, in global seconds
  return talkAmount(info.globalT, g0 + from, g0 + to);
}

// a face built from continuous values; anything unset falls back to the named expression
export function faceOf(base, over) {
  return { ...base, ...(over || {}) };
}

// Vertical: a 1080x1920 frame has 78% more height than 1920x1080, so the landscape scales make a
// head 7.3% of frame height instead of 12.6% — unreadable on a phone. These scales restore it.
export const S_MED = () => V(1.75, 2.55);
export const S_WIDE = () => V(1.45, 2.05);
export const S_CLOSE = () => V(2.6, 3.15);
