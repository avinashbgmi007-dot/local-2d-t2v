import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { parseArgs, numeric, frameRange, splitFrames, contained, staticPath, concatLine } from '../render-utils.mjs';

test('CLI rejects unknown flags and invalid numbers', () => {
  assert.deepEqual(parseArgs(['--project', 'p', '--sheet']), { project: 'p', sheet: true });
  assert.throws(() => parseArgs(['--projct', 'p']));
  assert.throws(() => numeric({ scale: 'NaN' }, 'scale', 1, .1, 1));
  assert.throws(() => numeric({ workers: '1.5' }, 'workers', 1, 1, 32, true));
  assert.equal(numeric({ scale: '.5' }, 'scale', 1, .1, 1), .5);
});

test('fractional shot boundaries partition every frame exactly once', () => {
  const shots = [[0, .345], [.345, .701], [.701, 1.2], [1.2, 2.003]];
  const ranges = shots.map(([a, b]) => frameRange(a, b, 24));
  assert.deepEqual(ranges, [[0, 9], [9, 17], [17, 29], [29, 49]]);
  const frames = ranges.flatMap(([a, b]) => Array.from({ length: b - a }, (_, i) => a + i));
  assert.deepEqual(frames, Array.from({ length: 49 }, (_, i) => i));
});

test('worker chunks cover a range without overlap', () => {
  for (const workers of [1, 2, 3, 8, 32]) {
    const chunks = splitFrames(7, 19, workers);
    assert.equal(chunks[0][0], 7);
    assert.equal(chunks.at(-1)[1], 19);
    for (let i = 1; i < chunks.length; i++) assert.equal(chunks[i][0], chunks[i - 1][1]);
  }
  assert.throws(() => splitFrames(3, 3, 2));
});

test('HTTP containment rejects sibling-prefix and encoded traversal', () => {
  const root = path.resolve('/studio');
  assert.equal(contained(root, path.resolve('/studio-other/file')), false);
  assert.equal(staticPath(root, path.resolve('/project'), '/../../etc/passwd'), null);
  assert.equal(staticPath(root, path.resolve('/project'), '/%2e%2e/%2e%2e/etc/passwd'), null);
  assert.equal(staticPath(root, path.resolve('/project'), '/.git/config'), null);
  assert.equal(staticPath(root, path.resolve('/project'), '/project/scenes/../config.json'), path.resolve('/project/config.json'));
  assert.equal(staticPath(root, path.resolve('/project'), '/engine/core.js'), path.resolve('/studio/engine/core.js'));
});

test('concat escaping handles apostrophes', () => {
  assert.ok(concatLine("/tmp/it's.mp4").includes("'\\''"));
});
