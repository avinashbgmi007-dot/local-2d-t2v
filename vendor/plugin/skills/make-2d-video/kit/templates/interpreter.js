// Data-driven shot archetypes. The engine remains the drawing/timing authority.
// Project-specific cast/sets are injected by scenes/templates.js; no global project paths here.
import { E, V, S, clamp, ease, prog, lerp, alpha, text, measure, glow, blurLayer, veil, circle, seg, FONTS, shade } from '/engine/core.js';
import { pose, breathe } from '/engine/rig2d.js';
import * as FX from '/engine/fx2d.js';
import * as UI from '/engine/ui2d.js';

export const TEMPLATE_IDS = Object.freeze([
  'establish-push', 'medium-two-shot', 'over-shoulder', 'giant-face', 'insert-object',
  'blueprint-diagram', 'lowpoly-3d', 'pull-out-bookend', 'freeze-frame', 'title-card',
  'end-card', 'transition-whip',
]);

export function normalizeParams(template, input = {}) {
  if (!TEMPLATE_IDS.includes(template)) throw new Error(`unknown template ${template}`);
  const p = { ...input };
  const names = Array.isArray(p.who) ? p.who : p.who ? [p.who] : [];
  const poses = Array.isArray(p.pose) ? p.pose : p.pose ? [p.pose] : [];
  if (template === 'lowpoly-3d') { p.templateWho = names; p.templatePose = poses; }
  if (template === 'end-card') p.endWho = names;
  const expressions = Array.isArray(p.expr) ? p.expr : p.expr ? [p.expr] : [];
  names.forEach((who, i) => {
    const n = i ? String(i + 1) : '';
    p['who' + n] = who;
    if (poses[i]) p['pose' + n] = poses[i];
    if (expressions[i]) p['expr' + n] = expressions[i];
  });
  // Keep scalar aliases for the first figure: legacy baseDraw and helpers read p.who/p.expr.
  if (names.length) p.who = names[0]; else delete p.who;
  if (poses.length) p.pose = poses[0]; else delete p.pose;
  if (expressions.length) p.expr = expressions[0]; else delete p.expr;
  if (template === 'lowpoly-3d' && !names.length) delete p.templateWho;
  if (template === 'end-card' && !names.length) delete p.endWho;
  if (p.push) { p.camZ0 = p.push[0]; p.camZ1 = p.push[1]; delete p.push; }
  if (p.drift_x != null) { p.camX1 = p.drift_x; delete p.drift_x; }
  if (Array.isArray(p.x)) { p.x = p.x[0]; p.x2 = p.x[1]; }
  if (Array.isArray(p.facing)) { p.facing = p.facing[0]; p.facing2 = p.facing[1]; }
  if (template === 'freeze-frame') { p.freeze = { u: p.freeze_at ?? .65 }; delete p.freeze_at; }
  return p;
}

export function shotFor(templates, name) {
  if (!templates[name]) throw new Error(`unknown template ${name}`);
  const def = templates[name];
  const expand = info => ({ ...info, ...normalizeParams(name, info.shot.params || {}) });
  return {
    ...(def.kind ? { kind: def.kind } : {}),
    ...(def.init ? { init: (T, info) => def.init(T, expand(info)) } : {}),
    draw: (...args) => def.kind === '3d' ? def.draw(args[0], args[1], expand(args[2]), args[3]) : def.draw(args[0], args[1], expand(args[2])),
  };
}

export function createTemplates({ cast, person, outfitOf, speak, faceAt, blinkAt, holdProp, sets, baseDraw, groundY }) {
  const keys = Object.keys(cast);
  const first = p => p.who || keys[0];
  const setOf = p => sets[p.set] || sets.room;
  const GY = () => groundY();
  const figure = (g, p, t, info, i = 0, overrides = {}) => {
    const n = i ? String(i + 1) : '', who = p['who' + n] || keys[i] || keys[0];
    const fx = E.W * (p['x' + n] ?? (i ? .68 : .34)), fy = GY();
    // A wide and a medium that draw the cast at the same size are the same shot.
    // Match the legacy S_WIDE/S_MED scales so shot size actually reads on screen.
    const wide = info.shot && info.shot.size === 'wide';
    const fs = wide ? V(1.45, 2.20) : V(1.75, 2.7), fc = p['facing' + n] ?? (i ? -1 : 1);
    // ONE pose object for the figure and anything it holds, so the hand and the
    // prop cannot drift apart during a breath or a gesture.
    const po = breathe(pose(p['pose' + n] || 'stand'), t, 1, i + 1);
    // Target-directed reach: a canned 'reach' preset aims at a fixed height, not at the
    // object. If this figure reaches and the on-screen prop belongs to the OTHER figure,
    // aim the hand at that figure's actual hand — which is where the prop is held.
    const shotProp0 = p.prop || (info.shot && info.shot.prop);
    if (shotProp0 && shotProp0.who && shotProp0.who !== who && /reach/i.test(String(p['pose' + n] || '')) && i === 0) {
      const fx2 = E.W * (p.x2 ?? .68), fy2 = GY();
      const fs2 = wide ? V(1.45, 2.20) : V(1.75, 2.7), fc2 = p.facing2 ?? -1;
      const h2 = (pose(p.pose2 || 'stand').hF) || [0, 0];
      const dx = (fx2 + h2[0] * fs2 * fc2) - fx, dy = (fy2 + h2[1] * fs2) - fy;
      po.hF = [dx / (fs * fc), dy / fs];
      po.eF = [dx * 0.5 / (fs * fc) - 8, dy * 0.5 / fs - 16];
    }
    const out = person(g, who, { x: fx, y: fy, s: fs, facing: fc, pose: po,
      face: faceAt(t, p.at, p['expr' + n] || 'neutral', p['exprTo' + n]),
      // Mouth routing: the shot names its speaker; only that figure may talk.
      // Untagged shots keep the legacy first-figure behaviour.
      expr: p['expr' + n] || 'neutral',
      talk: speak(info, t, .05, info.dur - .12, who, i === 0),
      blink: blinkAt(t, p.at), moodName: p.bg || 'midnight', seedBase: i + 1,
      rim: { color: '#ffd9a8', dir: [i ? -.7 : .7, -.6], w: 6 }, shadow: true, ...overrides });
    // A prop is owned by a person, not by a shot: it is drawn only in its holder's
    // hand, and only when that holder is actually on screen.
    const prop = p.prop || (info.shot && info.shot.prop);
    // Mid-shot transfer: prop.from holds until prop.at (a fraction of the shot), then
    // prop.who takes over — the handoff can happen ON SCREEN instead of across a cut.
    const lt = t;   // templates receive LOCAL shot time (see player.js drawShot)
    const effWho = prop && prop.from != null && prop.at != null && lt < prop.at * (info.dur || 1)
      ? prop.from : (prop && prop.who);
    if (prop && effWho === who) {
      holdProp(g, prop, { x: overrides.x ?? fx, y: overrides.y ?? fy,
                          s: overrides.s ?? fs, facing: overrides.facing ?? fc,
                          pose: po, owner: effWho });
    }
    return out;
  };
  const plate = (g, p, t) => { setOf(p)(g, t, { z: 1.04 }); FX.dust(g, t, { count: 12, a: .12 }); };
  const two = { draw(g, t, info) { const p = info; setOf(p)(g, t, { z: lerp(p.camZ0 ?? 1.02, p.camZ1 ?? 1.065, ease.inOut(info.p)) }); figure(g, p, t, info, 0); figure(g, { ...p, who2: p.who2 || keys[1] || keys[0] }, t, info, 1); plateAfter(g, p, t); } };
  function plateAfter(g, p, t) { FX.dust(g, t, { count: 12, a: .12 }); }
  const base = (size, extra = {}) => ({ draw(g, t, info) {
    const p = { ...info, ...extra };
    if (size === 'wide' || size === 'med') { setOf(p)(g, t, { z: lerp(p.camZ0 ?? 1, p.camZ1 ?? 1.045, ease.inOut(info.p)) }); }
    if (size === 'insert') {
      blurLayer(g, 16, gg => setOf(p)(gg, t, { z: 1.4 }), null, 1); veil(g, '#070a14', .38);
      // An INSERT exists to show the object. A 14-unit base rendered the book as a
      // postage stamp in an empty frame; the prop is the subject, so size it like one.
      const shotProp = (info.shot && info.shot.prop) || null;
      // The insert must show the SAME object the character holds, not a second
      // spec that can drift out of sync with it.
      const spec = shotProp
        ? { ...(p.object || {}), kind: shotProp.kind, color: shotProp.color || (p.object || {}).color }
        : (p.object || { kind: 'mug' });
      const scale = V(14, 17) * (p.scale || 1), k = scale * (spec.scale || 1);
      const cx = E.W * (p.x ?? .5), cy = E.H * (p.y ?? .44) + Math.sin(t * 1.2) * 3;
      glow(g, cx, cy, 220 * scale / 14, '#9fb6e0', .2);
      // An object floating in an empty room tells the viewer nothing about whose
      // it is. A forearm in the HOLDER's colour enters from below and grips it,
      // so the insert carries ownership as well as detail.
      const owner = (shotProp && shotProp.who) || null;
      const GRIP = { mug: 17, book: 14, phone: 7.5 };
      const grip = (GRIP[spec.kind] != null ? GRIP[spec.kind] : 12) * k;
      const hx = cx - grip, hy = cy + 2 * k;
      if (p.held !== false) {
        const col = (owner && cast[owner] && cast[owner].color) || '#6b5a4a';
        // A 4.6k limb beside a 26k book read as a POLE, not an arm. Size the
        // forearm and mitten against the object they are holding.
        const ax = cx - 22 * k, ay = E.H + 60;
        g.save(); g.lineCap = 'round';
        g.strokeStyle = 'rgba(8,8,12,.85)'; g.lineWidth = 9.5 * k;
        g.beginPath(); g.moveTo(ax, ay); g.lineTo(hx, hy); g.stroke();
        g.strokeStyle = shade(col, -0.38); g.lineWidth = 7.5 * k;
        g.beginPath(); g.moveTo(ax, ay); g.lineTo(hx, hy); g.stroke();
        circle(g, hx, hy, 5.8 * k, 'rgba(8,8,12,.85)');
        circle(g, hx, hy, 4.5 * k, shade(col, -0.12));
        g.restore();
      }
      holdProp(g, spec, { x: hx, y: hy, s: scale, facing: 1, pose: { hF: [0, 0] }, owner });
      FX.dust(g, t, { count: 10, a: .12 }); return;
    }
    if (size === 'close') return baseDraw(g, t, { ...p, shot: { ...info.shot, size } });
    const count = p.who2 ? 2 : 1;
    for (let i = 0; i < count; i++) figure(g, p, t, info, i);
    plateAfter(g, p, t);
  } });
  const ots = { draw(g, t, info) {
    const p = info, left = p.side !== 'right', who = p.who2 || keys[1] || keys[0];
    setOf(p)(g, t, { z: 1.12 });
    figure(g, { ...p, who, x: left ? .64 : .36, facing: left ? -1 : 1 }, t, info);
    blurLayer(g, 14, gg => person(gg, first(p), { x: E.W * (left ? .12 : .88), y: GY() + V(210, 260),
      s: V(4.8, 5.6), facing: left ? 1 : -1, pose: pose('stand'), outfit: outfitOf(first(p)),
      face: faceAt(t, null, 'listening'), moodName: p.bg || 'midnight', seedBase: 9 }), null, 1);
    veil(g, '#070a14', .12); FX.dust(g, t, { count: 10, a: .1 });
  } };
  const blueprint = { draw(g, t, info) {
    const p = info, labels = p.labels || ['INPUT', 'PROCESS', 'RESULT'];
    UI.blueprint(g); const color = S().ui.blueprint, gold = S().ui.gold;
    text(g, p.title || info.shot.line || 'HOW IT WORKS', E.W / 2, E.H * .22, { size: V(62, 66), color: S().ui.cream });
    const vertical = E.vertical, n = labels.length;
    const points = labels.map((_, i) => vertical ? [E.W / 2, E.H * (.34 + i * .30 / Math.max(1, n - 1))] : [E.W * (.2 + i * .6 / Math.max(1, n - 1)), E.H * .48]);
    points.forEach((point, i) => {
      const a = ease.out(prog(t, i * .35, i * .35 + .45));
      if (i) { const prev = points[i - 1]; seg(g, [prev, [lerp(prev[0], point[0], a), lerp(prev[1], point[1], a)]], 4, alpha(color, .8)); }
      circle(g, point[0], point[1], V(48, 54) * a, alpha(color, .12));
      text(g, String(i + 1), point[0], point[1], { size: V(38, 42), color: gold, alpha: a, font: FONTS.ui, weight: 900 });
      text(g, labels[i], point[0], point[1] + V(86, 92), { size: V(30, 34), color: S().ui.cream, alpha: a, font: FONTS.ui, weight: 800 });
    });
    if (p.fact) text(g, p.fact, E.W / 2, E.H * .84, { size: V(30, 34), color: gold });
    FX.dust(g, t, { count: 8, color, a: .08 });
  } };
  const title = { draw(g, t, info) {
    const p = info; blurLayer(g, 12, gg => setOf(p)(gg, t, { z: 1.05 + .02 * info.p }), null, 1); veil(g, '#070a14', .5);
    const lines = p.lines || String(info.shot.line || 'UNTITLED').toUpperCase().match(/.{1,24}(?:\s|$)|.{1,24}/g)?.map(s => s.trim()).filter(Boolean) || ['UNTITLED'];
    UI.titleCard(g, t, { lines, sub: p.sub, dur: info.dur, y: E.H * .46 });
  } };
  const end = { draw(g, t, info) {
    const p = info, a = ease.out(prog(t, .15, .65));
    glow(g, E.W / 2, E.H * .65, E.W * .6, S().ui.accent, .22);
    veil(g, '#090b16', .82);
    const question = p.question || 'What happens next?';
    const size = Math.min(V(70, 76), E.W * .86 / Math.max(1, measure(g, question, V(70, 76)) / V(70, 76)));
    text(g, question, E.W / 2, E.H * .3, { size, font: FONTS.serif, italic: true, weight: 900, color: S().ui.cream, alpha: a });
    const names = Array.isArray(p.endWho) ? p.endWho : keys;
    names.forEach((who, i) => person(g, who, { x: E.W * (.5 + (i - (names.length - 1) / 2) * .18), y: E.H * .7,
      s: V(1.05, 1.8), pose: pose('relaxed'), face: faceAt(t, null, 'hopeful'), moodName: 'night',
      rim: { color: '#ffd9a8', dir: [0, -1], w: 5 }, alpha: a, shadow: true }));
    if (p.attribution) text(g, p.attribution, E.W / 2, E.H * .82, { size: V(26, 30), color: S().ui.cream, alpha: .7 * a, font: FONTS.ui, weight: 800 });
    FX.dust(g, t, { count: 10, a: .1 });
  } };
  const freeze = { draw(g, t, info) {
    const p = info, at = (p.freeze?.u ?? .65) * info.dur, tv = Math.min(t, at);
    const frozen = { ...info, globalT: info.shot.start + tv, p: clamp(tv / info.dur) };
    base('med').draw(g, tv, frozen);
    if (t >= at) { veil(g, '#9bbcff', .08); UI.badge(g, { str: p.badge || 'HOLD', x: E.W - V(100, 80), y: V(150, 240) }); }
  } };
  const threeD = { kind: '3d', init(T, info) {
    const p = info, st = T.stage({ mood: p.mood || 'night', fov: 38 });
    st.add(T.ground(40, 40, st.M.dark));
    const names = p.templateWho || keys.slice(0, 2), poses = p.templatePose || [];
    const figures = names.map((who, i) => { const f = T.figure3D(cast[who] || {}, { pose: poses[i] || 'stand' }); f.position.set((i - (names.length - 1) / 2) * 2, 0, 0); st.add(f); return f; });
    return { ...st, figures };
  }, draw(st, t, info, T) { const orbit = info.orbit || [-.5, .25]; T.orbit(st.camera, t, { radius: 8, height: 3, from: orbit[0], to: orbit[1], dur: info.dur }); } };
  return {
    'establish-push': base('wide'), 'medium-two-shot': two, 'over-shoulder': ots,
    'giant-face': base('close'), 'insert-object': base('insert'), 'blueprint-diagram': blueprint,
    'lowpoly-3d': threeD, 'pull-out-bookend': base('wide'), 'freeze-frame': freeze,
    'title-card': title, 'end-card': end, 'transition-whip': base('wide'),
  };
}
