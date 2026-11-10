// Opt-in real Chromium/ffmpeg regression. Run: node --test tests/render-integration.mjs
// Requires npm ci, Playwright Chromium, ffmpeg and ffprobe. Keeps artifacts in build/audit.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(new URL('.', import.meta.url)));
const audit = path.join(root, 'build/audit');
fs.mkdirSync(audit, { recursive: true });
function run(cmd, args) { return spawnSync(cmd, args, { cwd: root, encoding: 'utf8', timeout: 180000 }); }
function fixture(name, scene) {
  const project = path.join(audit, name);
  const result = run(process.env.PYTHON || 'python', ['-c', `from tools.director import compile_project; compile_project({'title':'integration','aspect':'16:9','resolution':'720p','fps':12,'cast':{'MAX':{}},'shots':[{'id':'s1','size':'wide','dur':1,'line':''}],'music':[]}, ${JSON.stringify(project)})`]);
  assert.equal(result.status, 0, result.stderr);
  if (scene) fs.writeFileSync(path.join(project, 'scenes/shots/01_s1-wide.js'), scene);
  return project;
}
test('real renderer encodes exact frame count and dimensions', () => {
  const project = fixture('integration-success');
  const result = run(process.execPath, ['render.mjs', '--project', project, '--scale', '.25', '--workers', '2']);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const video = path.join(project, 'build/video_silent.mp4');
  const probe = run('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_frames,r_frame_rate', '-of', 'json', video]);
  assert.equal(probe.status, 0, probe.stderr);
  const stream = JSON.parse(probe.stdout).streams[0];
  assert.equal(stream.width, 320); assert.equal(stream.height, 180); assert.equal(stream.nb_frames, '12'); assert.equal(stream.r_frame_rate, '12/1');
});
test('shot exception fails and preserves an existing deliverable', () => {
  const project = fixture('integration-failure', "import {registerShot} from '/engine/core.js'; registerShot('s1',{draw(){throw new Error('intentional regression')}});");
  const video = path.join(project, 'build/video_silent.mp4'); fs.mkdirSync(path.dirname(video), { recursive: true }); fs.writeFileSync(video, 'sentinel');
  const result = run(process.execPath, ['render.mjs', '--project', project, '--scale', '.25']);
  assert.notEqual(result.status, 0); assert.match(result.stdout + result.stderr, /intentional regression/);
  assert.equal(fs.readFileSync(video, 'utf8'), 'sentinel');
});
test('missing scene fails even in contact-sheet mode', () => {
  const project = fixture('integration-missing');
  fs.rmSync(path.join(project, 'scenes/shots/01_s1-wide.js'));
  const result = run(process.execPath, ['render.mjs', '--project', project, '--sheet', '--scale', '.25']);
  assert.notEqual(result.status, 0); assert.match(result.stdout + result.stderr, /missing scene/);
});
