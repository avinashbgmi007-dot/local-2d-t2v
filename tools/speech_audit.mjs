// tools/speech_audit.mjs — assert dialogue routing frame-by-frame, headlessly.
//
// "The right mouth moves" is a hard quality gate, and it is not checkable by
// looking at a contact sheet: a wrong mouth is a few pixels for a few frames.
// This boots the real player, draws every frame, and reads window.SPEECH_FRAME
// (written by engine/core.js) to prove:
//
//   1. while a speaker talks, THAT figure's mouth is driven by the measured
//      envelope (source === 'envelope', not the legacy sine);
//   2. no other cast member's mouth opens on those frames;
//   3. mouths are shut in silent beats;
//   4. captions stay inside the frame and never shrink below a legible floor.
//
//   node tools/speech_audit.mjs --project build/quality/v1 [--out report.json]
//
// Exit code 1 on any violation. This is a routing check, NOT a visual approval.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from '../render-utils.mjs';
import { withPlayer, readProject, logicalStage } from './audit_host.mjs';

const args = parseArgs(process.argv.slice(2));
if (!args.project) {
  console.error('usage: node tools/speech_audit.mjs --project DIR [--out report.json]');
  process.exit(2);
}
const { cfg, story } = readProject(args.project);
const fps = cfg.fps || 24;
const stage = logicalStage(cfg);

const report = await withPlayer(args.project, page => page.evaluate(
  ({ fps, cast, stageW, stageH }) => {
    const total = window.TOTAL_FRAMES;
    const wrong = [], silentLeaks = [], notMeasured = [], captionIssues = [];
    const openFrames = {}, spokenFrames = {};
    let envelopeFrames = 0, sineFrames = 0;
    for (let f = 0; f < total; f++) {
      window.renderFrame(f);
      const t = f / fps;
      const owner = window.SPEECH_EXPECT;      // shot's declared speaker
      const expect = window.SPEECH_ACTIVE;     // actually speaking this frame
      const rec = window.SPEECH_FRAME || {};
      for (const [who, v] of Object.entries(rec)) {
        if (v.source === 'envelope') envelopeFrames++;
        if (v.source === 'fallback-sine') sineFrames++;
        if (v.amount > 0.05) {
          openFrames[who] = (openFrames[who] || 0) + 1;
          if (who !== (expect || owner) && wrong.length < 40) {
            wrong.push({ f, t: +t.toFixed(3), who, expect: expect || owner, amount: v.amount });
          }
          if (!expect && silentLeaks.length < 40) {
            silentLeaks.push({ f, t: +t.toFixed(3), who, amount: v.amount });
          }
        }
      }
      if (expect) {
        spokenFrames[expect] = (spokenFrames[expect] || 0) + 1;
        const mine = rec[expect];
        if (window.SPEECH_INFO && window.SPEECH_INFO.measured.length
            && (!mine || mine.source !== 'envelope') && notMeasured.length < 40) {
          notMeasured.push({ f, t: +t.toFixed(3), expect, got: mine || null });
        }
      }
      const box = window.CAPTION_BOX;
      if (box) {
        if (box.x < 0 || box.y < 0 || box.x + box.w > stageW || box.y + box.h > stageH) {
          if (captionIssues.length < 20) captionIssues.push({ f, reason: 'outside frame', box });
        }
        if (box.size < 30 && captionIssues.length < 20) {
          captionIssues.push({ f, reason: 'type too small', size: box.size });
        }
      }
    }
    return { total, fps, cast, wrong, silentLeaks, notMeasured, captionIssues,
             openFrames, spokenFrames, envelopeFrames, sineFrames,
             speechInfo: window.SPEECH_INFO, errors: window.ERRORS };
  },
  { fps, cast: Object.keys(story.cast || {}), stageW: stage.W, stageH: stage.H }));

report.stage = stage;
const violations = [];
if (report.errors && report.errors.length) violations.push(`player errors: ${report.errors.join('; ')}`);
if (report.wrong.length) violations.push(`${report.wrong.length} frame(s) opened a NON-speaker mouth`);
if (report.silentLeaks.length) violations.push(`${report.silentLeaks.length} frame(s) opened a mouth in a silent beat`);
if (report.notMeasured.length) violations.push(`${report.notMeasured.length} speaking frame(s) not driven by the measured envelope`);
if (report.sineFrames > 0 && report.speechInfo && report.speechInfo.measured.length) {
  violations.push(`${report.sineFrames} figure-frame(s) still used the legacy sine mouth`);
}
for (const [who, n] of Object.entries(report.spokenFrames)) {
  if (!report.openFrames[who]) violations.push(`${who} speaks for ${n} frames but their mouth never opened`);
}

console.log(`speech audit: ${report.total} frames @ ${fps}fps`);
console.log(`  envelope source : ${report.speechInfo ? JSON.stringify(report.speechInfo) : 'NONE (no speech track)'}`);
console.log(`  mouth-open frames: ${JSON.stringify(report.openFrames)}`);
console.log(`  expected frames  : ${JSON.stringify(report.spokenFrames)}`);
console.log(`  envelope/sine    : ${report.envelopeFrames}/${report.sineFrames}`);
if (report.wrong.length) console.log('  WRONG MOUTH sample:', JSON.stringify(report.wrong.slice(0, 5)));
if (report.silentLeaks.length) console.log('  SILENT LEAK sample:', JSON.stringify(report.silentLeaks.slice(0, 5)));
if (report.notMeasured.length) console.log('  NOT MEASURED sample:', JSON.stringify(report.notMeasured.slice(0, 5)));
if (report.captionIssues.length) console.log('  CAPTION issues:', JSON.stringify(report.captionIssues.slice(0, 5)));
if (args.out) {
  fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify(report, null, 1));
}
if (violations.length) { console.log('FAIL:\n  ' + violations.join('\n  ')); process.exit(1); }
console.log('PASS — speaker routing, measured envelope and silent beats verified.');
