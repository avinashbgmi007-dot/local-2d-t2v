# Quality contract

Target: **≥95/100 overall** against an approved reference for this stylised 2D look.
Efficiency is measured separately and never bought with quality. Picture locks to
the performance; the performance is never squeezed to fit a shot grid.

This file records what is **measured**, not what is hoped for. A loudness pass is
not cinematic quality, and a green test suite is not a watched film.

## Scoring rubric

| Domain | Weight |
| --- | --- |
| Story / beat adaptation | 20 |
| Acting, staging, continuity | 20 |
| Dialogue, lip-sync, captions | 15 |
| Cinematography, lighting, editing | 15 |
| SFX, ambience, score, mix | 20 |
| Technical delivery | 10 |

## Hard gates (any failure blocks delivery regardless of score)

1. No wrong-speaker mouth movement.
2. No broken prop contact (a held object must be in a hand).
3. Dialogue intelligible.
4. No clipping; loudness and true peak inside target.
5. No missing shots or frames.
6. No continuity jumps.
7. Captions never cover a face.

## Benchmark

`examples/quality-benchmark/story.json` — "The Book", 8 shots, 12.20 s,
9:16 720p 24 fps, two speakers (NILA / ARUN), three silent beats.

Run it end to end:

```bash
bash tools/setup_runtime.sh
export PATH=/home/user/.local/bin:$PATH LD_LIBRARY_PATH=/tmp/al2023/lib:/tmp \
       PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/tmp/chromium

python3 tools/test_voice.py --story examples/quality-benchmark/story.json \
        --out build/quality/voice --voices 'NILA=en-us+f3,ARUN=en-us+m2'
python3 tools/director.py --story examples/quality-benchmark/story.json --out build/quality/v1
# set config: voiceover, voiceStems, captions, captionStyle, loudness
python3 tools/parse_script.py --project build/quality/v1 --script build/quality/voice/words.json
python3 tools/speech_track.py --project build/quality/v1
python3 tools/sound_design.py --project build/quality/v1
node   tools/speech_audit.mjs     --project build/quality/v1   # gate: must PASS
node   tools/continuity_gate.mjs  --project build/quality/v1   # gate: must PASS
node   render.mjs --project build/quality/v1 --workers 2
python3 audio/mix.py --project build/quality/v1
python3 tools/master.py --project build/quality/v1
```

### Measured results

| Metric | Baseline | Slice 1 |
| --- | --- | --- |
| Frames / duration | 293 / 12.20 s | 293 / 12.20 s |
| Render wall time (2 workers) | 2 m 02 s @ 2.45 fps | 2 m 01 s @ 2.45 fps |
| Shipped loudness | −14.32 LUFS | −14.12 LUFS |
| Shipped true peak | −1.78 dBTP | −1.76 dBTP |
| SFX cues | **0** (tool crashed) | 7 + 1 ambience bed |
| Word transcription | garbled fragments | 19 correct words |
| Mouth clock | sine, first figure only | measured envelope, per speaker |
| Wrong-speaker mouth frames | not measured | **0 / 293** |
| Mouth open in silent beats | not measured | **0 / 293** |
| Envelope-driven vs sine figure-frames | all sine | **420 / 0** |
| Speaking frames vs mouth-open frames | n/a | NILA 68/68, ARUN 50/50 |
| Prop in the wrong hand / duplicated | not measured | **0 / 293** |
| Frames with no hand contact on the prop | not measured | **0 / 293** |
| Frames omitting a prop whose holder is on screen | not measured | **0 / 293** |
| Book held by anyone | **never** | ARUN b01–b06, NILA b07–b08 |
| Close-up silhouette separation (head vs bg luminance) | near zero | **Δ29.5–37.4** |

Automated by `tools/speech_audit.mjs` and `tools/continuity_gate.mjs`, which draw
every frame headlessly and read `window.SPEECH_FRAME` / `window.PROP_FRAME`. These
are routing and geometry proofs, **not** a visual approval.

## What slice 1 actually fixed

- **Speaker casting.** `speaker` per shot and a `voices` map flow through the schema,
  compiler and manifest. Only the declared speaker's mouth may open.
- **Measured mouth clock.** `tools/speech_track.py` derives a per-speaker RMS
  envelope from the real recording, gated by that speaker's word windows. It
  refuses to fabricate an envelope when no recording exists.
- **Per-speaker stems** from both `narrate.py` and the test fixture, because a
  mixdown cannot separate overlapping speakers.
- **Two real sync bugs** found by the audit and fixed:
  frame-quantised gating opened mouths in consonant gaps; a hardcoded 50 ms
  lead-in muted the start of every line.
- **Phrase-aware captions.** Cards break on sentence/clause boundaries and speaker
  changes, wrap instead of shrinking, and never end on a determiner. Fixed a
  40 ms card-overlap bug and the "THAT IS NOT THE" mid-phrase break.
- **`sound_design.py` crash** on list-valued `params.pose` (template mode) — this had
  been silently killing the entire foley layer for every template project.
- **The book prop** was a landscape rect with a cream centre that read as a picture
  frame. Redrawn portrait with spine, page block and title rules; insert scale
  corrected.

## What slice 2 fixed (prop contact + staging)

Hard gate 2 (broken prop contact) **now passes**, geometrically and on screen.

- **Shot-level `prop` ownership.** A prop belongs to a person, not a shot, so it
  works uniformly across every template and can be checked across cuts.
- **The template path never drew props at all** — only legacy shots did. Figures now
  draw their own prop using the *same* pose object, so hand and object cannot drift.
- **Kind-aware grip.** A fixed 18-unit offset put the hand ~9 units off a book's
  spine. The grip now matches each object's silhouette; the gate measures the gap.
- **The insert shows a hand.** A forearm in the holder's colour enters frame and
  grips the object, so the insert carries ownership as well as detail. It also
  derives its spec from the shot's prop, so it cannot show a different item.
- **Book sized for readability.** At the first attempt the book was technically
  held but only ~4% of frame width — continuity verified, audience unable to see it.
- **`reachLow` preset.** `reach` fires at head height while an offered object sits at
  hip/chest height, so the handoff beat did not read. b06 now stages offer + reach.
- **Shot size changes figure scale.** Wide and medium drew the cast identically, so
  consecutive shots looked like the same frame. Now matches S_WIDE/S_MED.

## What slice 3 fixed (close-up body + separation)

- **Shoulders were literally one rounded rectangle** (`rr(...)` with a flat fill),
  drawn *after* the head so the slab overlapped the chin. Replaced with a bust:
  neck in shadow, sloped shoulder line, collar, key-to-shadow gradient, lit-edge
  rim — drawn behind the head so the jaw occludes the neck.
- **Separation, not exposure.** The dark head on a veiled navy set had almost no
  edge. Brightening the face would have destroyed the ink-bean identity, so the fix
  is a faint full-silhouette rim plus a motivated bounce from the room's practical,
  lifted only around the head. Measured head-vs-background luminance delta is now
  **29.5–37.4** across the three close-ups (was near zero).
- **Bust framing.** The first attempt stopped short of the frame bottom and left a
  beige strip of set visible underneath; it now extends out of frame.

## Review findings still open (watched, not fixed)

Ordered by damage to the film:

1. **Wide/medium bodies are still flat tubes.** The bust fix applies to close-ups
   only; the full-figure rig has no comparable torso shaping or shading.
2. **Gestures are still canned presets.** `reachLow` makes this beat read, but nothing
   aims a limb at a target; a different blocking would miss again.
4. **The handoff completes across a cut**, not on screen. Legitimate film grammar,
   but an on-screen transfer would be stronger.
5. **Score is a mood loop**, not a motif; SFX is still whoosh-on-every-cut, which is
   a heuristic, not sound design. The Kenney CC0 foley library remains unused.

## Not verified — do not claim otherwise

- **The voice is a TEST FIXTURE.** `tools/test_voice.py` uses espeak-ng (formant
  synthesis): intelligible but robotic. It exists because Kokoro's weights are
  unreachable from this environment. **Real-voice quality is unverified.**
- No human-approved style lock or reference film exists, so **no overall /100 score
  can honestly be asserted yet.** The rubric is defined; the scoring is not done.
- Overlapping dialogue is untested (the benchmark has no overlaps).
- The Hindi/Telugu path is untouched.

## Next slices

1. Prose → beat/shot adaptation and a validated manifest (the actual text-to-video
   gap; deferred twice now to clear hard gates first).
2. Full-figure torso shading and a set-lighting pass (close-ups are now solved).
3. Performance pass: per-character casting, takes, forced alignment as the clock,
   animatic approval before final animation.
4. Target-directed gestures and on-screen transfers.
5. Sound post: event-driven foley from the CC0 library, continuous ambience,
   motif-based score.
6. Throughput and QC automation.
