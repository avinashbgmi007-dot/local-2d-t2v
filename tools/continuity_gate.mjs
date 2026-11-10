// tools/continuity_gate.mjs — hard gate: a held prop must be IN THE HOLDER'S HAND.
//
// "Broken prop contact" is a delivery-blocking defect, and it is a few pixels wide.
// This draws every frame headlessly and reads window.PROP_FRAME (written by
// holdProp) to prove, geometrically:
//
//   1. the prop is only ever drawn for its declared holder — never in the wrong
//      person's hand, and never duplicated;
//   2. the hand actually touches the object's silhouette (gap <= tolerance),
//      rather than hovering beside it;
//   3. the prop is present whenever its holder is on screen in a wide/med/insert
//      (a close-up legitimately crops the hands, so it is exempt);
//   4. ownership changes are reported as a timeline for editorial review.
//
//   node tools/continuity_gate.mjs --project build/quality/v1 [--out report.json]
//
// Exit 1 on any violation. Geometry, not taste: this cannot judge whether a
// handoff is well acted, only that contact and ownership are not broken.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from '../render-utils.mjs';
import { withPlayer, readProject, logicalStage } from './audit_host.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.project) {
  console.error('usage: node tools/continuity_gate.mjs --project DIR [--out report.json]');
  process.exit(2);
}
const { cfg, story } = readProject(args.project);
const fps = cfg.fps || 24;
const stage = logicalStage(cfg);

// Half-extent of each prop's gripable silhouette, in prop units. The mug includes
// its handle, because that is what a hand holds.
const HALF = { mug: 15.5, book: 13, phone: 6 };
const TOL = 2.0;   // in prop units (k): a hand radius worth of slack

const shots = story.shots.map(s => {
  const who = (s.params || {}).who;
  const list = Array.isArray(who) ? who : (who ? [who] : []);
  const prop = s.prop || null;
  const size = s.size || 'med';
  const ownerOnScreen = size === 'insert' ? true : (prop ? list.includes(prop.who) : false);
  return { id: s.id, start: s.start, end: s.end, size, prop, list,
           required: !!prop && ['wide', 'med', 'insert'].includes(size) && ownerOnScreen };
});

const report = await withPlayer(args.project, page => page.evaluate(({ fps, shots, HALF, TOL, stageW, stageH }) => {
  const total = window.TOTAL_FRAMES;
  const wrongHolder = [], noContact = [], missing = [], offFrame = [];
  const seen = {}, timeline = [];
  let lastOwner = null;
  for (let f = 0; f < total; f++) {
    window.renderFrame(f);
    const t = f / fps;
    const shot = shots.find(s => t >= s.start - 1e-9 && t < s.end - 1e-9) || shots[shots.length - 1];
    const entries = window.PROP_FRAME || [];
    const prop = shot.prop;
    const sdur = shot.end - shot.start, slt = t - shot.start;
    const effWho = prop && prop.from != null && prop.at != null && slt < prop.at * sdur
      ? prop.from : (prop && prop.who);
    if (prop && effWho !== lastOwner) {
      timeline.push({ t: +t.toFixed(3), shot: shot.id, from: lastOwner, to: effWho });
      lastOwner = effWho;
    }
    if (entries.length) {
      seen[shot.id] = (seen[shot.id] || 0) + 1;
      if (entries.length > 1 && wrongHolder.length < 40) {
        wrongHolder.push({ f, shot: shot.id, reason: 'prop drawn more than once', count: entries.length });
      }
      for (const e of entries) {
        if (prop && e.who && e.who !== effWho && wrongHolder.length < 40) {
          wrongHolder.push({ f, shot: shot.id, reason: 'wrong holder', got: e.who, want: effWho });
        }
        const half = (HALF[e.kind] != null ? HALF[e.kind] : 8) * e.k;
        const gap = Math.max(0, Math.abs(e.cx - e.handX) - half);
        if (gap > TOL * e.k && noContact.length < 40) {
          noContact.push({ f, shot: shot.id, kind: e.kind, gap: +(gap / e.k).toFixed(2),
                           tol: TOL, who: e.who });
        }
        if ((e.cx < 0 || e.cx > stageW || e.cy < 0 || e.cy > stageH) && offFrame.length < 40) {
          offFrame.push({ f, shot: shot.id, cx: Math.round(e.cx), cy: Math.round(e.cy) });
        }
      }
    } else if (shot.required && missing.length < 40) {
      missing.push({ f, shot: shot.id, size: shot.size, holder: prop && prop.who });
    }
  }
  return { total, fps, wrongHolder, noContact, missing, offFrame, seen, timeline, errors: window.ERRORS };
}, { fps, shots, HALF, TOL, stageW: stage.W, stageH: stage.H }));

report.stage = stage;
const violations = [];
if (report.errors && report.errors.length) violations.push(`player errors: ${report.errors.join('; ')}`);
if (report.wrongHolder.length) violations.push(`${report.wrongHolder.length} frame(s) drew the prop in the wrong hand or twice`);
if (report.noContact.length) violations.push(`${report.noContact.length} frame(s) had NO hand contact with the prop`);
if (report.missing.length) violations.push(`${report.missing.length} frame(s) omitted a prop whose holder was on screen`);

console.log(`continuity gate: ${report.total} frames @ ${fps}fps`);
console.log(`  prop drawn on frames: ${JSON.stringify(report.seen)}`);
console.log('  ownership timeline:');
for (const e of report.timeline) console.log(`    ${e.t.toFixed(2)}s ${e.shot}: ${e.from || '(none)'} -> ${e.to}`);
if (report.wrongHolder.length) console.log('  WRONG HOLDER sample:', JSON.stringify(report.wrongHolder.slice(0, 5)));
if (report.noContact.length) console.log('  NO CONTACT sample:', JSON.stringify(report.noContact.slice(0, 5)));
if (report.missing.length) console.log('  MISSING sample:', JSON.stringify(report.missing.slice(0, 5)));
if (args.out) {
  fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify(report, null, 1));
}
if (violations.length) { console.log('FAIL:\n  ' + violations.join('\n  ')); process.exit(1); }
console.log('PASS — prop ownership and hand contact verified.');
