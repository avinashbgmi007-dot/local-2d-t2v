// Dialogue routing + caption phrasing regressions. Pure module tests, no browser.
//   node --test tests/speech.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { E, speechAmount, activeSpeakerAt, speakerAt, talkAmount } from '../engine/core.js';
import { captionChunks } from '../engine/ui2d.js';

const reset = () => { E.words = []; E.shots = []; E.speech = null; E.fps = 24; };

test('envelope routes the mouth to the speaker only', () => {
  reset();
  E.speech = { fps: 24, tracks: { NILA: [0, .8, .8, 0], ARUN: [0, 0, 0, 0] } };
  assert.ok(speechAmount(1 / 24, 'NILA') > 0.5);
  assert.equal(speechAmount(1 / 24, 'ARUN'), 0);
});

test('a measured envelope is not clipped by the legacy line guard', () => {
  // Regression: templates pass from=0.05, which muted the first 50 ms of every
  // line once speech started exactly on the cut.
  reset();
  E.speech = { fps: 24, tracks: { NILA: [.9, .9, .9] } };
  assert.ok(speechAmount(0, 'NILA', 0.05, 10) > 0.5);
});

test('mouth is shut between words and in the tail hold', () => {
  reset();
  E.words = [{ word: 'You', start: 0, end: 0.115, speaker: 'NILA' },
             { word: 'kept', start: 0.131, end: 0.541, speaker: 'NILA' }];
  E.shots = [{ id: 'b01', start: 0, end: 1.7, speaker: 'NILA' }];
  assert.equal(activeSpeakerAt(0.125), null, 'consonant gap is not speech');
  assert.equal(activeSpeakerAt(1.0), null, 'tail hold is not speech');
  assert.equal(speakerAt(1.0), 'NILA', 'shot still declares its owner');
  assert.equal(activeSpeakerAt(0.05), 'NILA');
});

test('without an envelope a tagged word never opens another mouth', () => {
  reset();
  E.words = [{ word: 'I', start: 0, end: 0.2, speaker: 'ARUN' }];
  E.shots = [{ id: 's', start: 0, end: 1, speaker: 'ARUN' }];
  assert.equal(speechAmount(0.1, 'NILA'), 0);
  assert.ok(speechAmount(0.1, 'ARUN') > 0);
});

test('legacy untagged projects still animate', () => {
  reset();
  E.words = [{ word: 'hello', start: 0, end: 1 }];
  assert.ok(talkAmount(0.5) > 0);
});

test('captions break at punctuation, not mid-phrase', () => {
  reset();
  const w = (word, start, end) => ({ word, start, end });
  const chunks = captionChunks([w('Then', 0, .2), w('take', .2, .4), w('it.', .4, .6),
                                w('I', .7, .8), w('will.', .8, 1)], 4, 24);
  assert.deepEqual(chunks.map(c => c.words.map(x => x.text).join(' ')), ['Then take it.', 'I will.']);
});

test('captions never mix two speakers in one card', () => {
  reset();
  const chunks = captionChunks([{ word: 'Yes', start: 0, end: .3, speaker: 'NILA' },
                                { word: 'No', start: .35, end: .6, speaker: 'ARUN' }], 4, 24);
  assert.equal(chunks.length, 2);
  assert.equal(chunks[0].words[0].speaker, 'NILA');
  assert.equal(chunks[1].words[0].speaker, 'ARUN');
});

test('caption windows do not overlap and respect the hard budget', () => {
  reset();
  const words = Array.from({ length: 9 }, (_, i) => ({ word: 'w' + i, start: i * .3, end: i * .3 + .25 }));
  const chunks = captionChunks(words, 4, 200);
  // `max` is a preference; wrapping handles width, so the hard cap is 2x max.
  assert.ok(chunks.every(c => c.words.length <= 8));
  for (let i = 1; i < chunks.length; i++) assert.ok(chunks[i].in >= chunks[i - 1].out - 1e-9);
});

test('a short sentence is never split mid-phrase', () => {
  // Regression: the 4-word cap produced "THAT IS NOT THE" + "SAME THING."
  reset();
  const txt = ['That', 'is', 'not', 'the', 'same', 'thing.'];
  const words = txt.map((word, i) => ({ word, start: i * .25, end: i * .25 + .22 }));
  const chunks = captionChunks(words, 4, 24);
  assert.equal(chunks.length, 1);
  assert.equal(chunks[0].words.map(w => w.text).join(' '), 'That is not the same thing.');
});

test('an over-long sentence never breaks on a determiner', () => {
  reset();
  const txt = ('we walked into the room and found the old book that nobody ever opened.').split(' ');
  const words = txt.map((word, i) => ({ word, start: i * .22, end: i * .22 + .2 }));
  const chunks = captionChunks(words, 4, 24);
  assert.ok(chunks.length > 1);
  for (const c of chunks.slice(0, -1)) {
    const last = c.words[c.words.length - 1].text.toLowerCase().replace(/[^a-z']/g, '');
    assert.ok(!['the', 'a', 'an', 'of', 'and', 'that'].includes(last), `card ended on "${last}"`);
  }
});
