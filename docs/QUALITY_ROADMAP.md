# Autonomous quality roadmap — local 2D text-to-video

This file IS the loop driver. Read its STATE section at the start of every turn,
execute the first non-DONE item by the protocol below, and update STATE before
the turn ends. Do not ask "what next?" — proceed. Ask the user only when
honestly blocked or when the choice is genuinely theirs (voice pick, style
lock, reference approval).

Standing rules (see AGENTS.md): hard 68-tool-call cap per turn with the
0-50/50-58/58-64/65-68 schedule; EVERY iteration ships a short rendered video
that is `present_file`-ed to the user; brutal honesty; runtime restored via
`tools/setup_runtime.sh` each turn.

## STATE

- Last commit: 7997f5d (slices 1-3 + hardening). Branch: arena/1f5cc873-local-2d-t2v.
- Last delivered video: build/quality/v1/out/Quality_benchmark_-_The_Book.mp4
  (12.21s, 720x1280@24, -14.14 LUFS / -1.75 dBTP). Live link:
  https://8000-i2prvlwadzexco7mls8kp.e2b.app/Quality_benchmark_-_The_Book.mp4
  (serve with: python3 -m http.server 8000 --bind 0.0.0.0 --directory build/quality/v1/out)
- Gates: speech_audit PASS, continuity_gate PASS, verify_kit 49/49, tests 34 py + 15 node.
- Component-proven but NOT yet in the video: fully local Kokoro-82M q8 TTS
  (npm kokoro-q8-shards reassembled sha256 fbae9257..., voices from npm
  kokoro-local-runtime, vocab from pypi kokoro-onnx config.json, IPA via pypi
  piper-phonemize+espeakng_loader, onnxruntime-web wasm). 5/5 fixture lines OK.
- Next item: SLICE-4 (Kokoro voices wired into the benchmark render).

## Definition of "significant change" (loop stop per item)

An item is DONE when ALL of: (a) short benchmark video re-rendered and
`present_file`-ed, (b) all applicable gates green, (c) at least one measured or
visually confirmed improvement recorded with numbers/frames, (d) STATE +
LESSONS.md updated, kit re-pinned if kit files changed, (e) work committed.

## Iteration protocol (loop body, per item)

0. Read STATE; pick first non-DONE item.
1. SELF-CRITIQUE FIRST: write 3-5 lines in the item notes — what could go
   wrong, what a viewer would see, what the gates will NOT catch. Then proceed
   with the best fix, don't ask permission to try.
2. Implement with batched edits (one python heredoc patch per file), syntax-check.
3. Fast checks: unittest, node --test, verify_kit, applicable gates.
4. Render via start_process (render.mjs --workers 2 -> audio/mix.py -> tools/master.py),
   ONE get_process_output(wait_for='exit').
5. Extract the standard 8-frame sheet (0.50/2.20/4.20/6.00/7.00/8.60/9.70/11.20)
   + objective probes; read_file the sheet and actually judge it.
6. Self-review vs previous iteration: improved / regressed / still wrong. Fix
   cheap regressions immediately.
7. present_file the video; report the delta vs the last clip.
8. Update STATE + LESSONS.md; commit. If calls used >= 58: stop, summarize, conclude.

Budget: ~12-16 calls per iteration -> expect 3-4 iterations per turn. Always
keep >= 4 calls in reserve for verify + summary + commit + hand-back.

## Backlog (ordered by perceptual impact; each item: goal / acceptance / risks)

### SLICE-4 — Real neural voices (Kokoro) in the video — IN FLIGHT
- Goal: benchmark speaks with af_heart (NILA) / am_adam (ARUN) instead of espeak.
- Build: extend tools/setup_runtime.sh to fetch+cache the npm shards + runtime
  voices into a stable path (e.g. build/tts-cache, gitignored), reassemble and
  sha256-verify the model; new tools/kokoro_voice.py: phonemize (piper-phonemize)
  -> kokoro-clean -> ids -> onnxruntime-web run -> voice.wav + per-speaker stems;
  keep espeak word EVENT timings, scaled to Kokoro durations, for words.json
  (lip-sync + captions). Swap into the test_voice.py slot in the rebuild chain.
- Acceptance: speech_audit PASS on Kokoro audio, continuity PASS, master PASS,
  video presented, user listens and judges voice quality.
- Risks: word-timing drift vs audio (audit catches mouth errors); wasm speed
  (~3s/line CPU, fine); /tmp wiped per turn -> everything must live under
  repo build/ cache restored by setup_runtime.sh.
- Notes: _(fill during iteration)_

### SLICE-5 — Full-figure torso shading (wide/medium)
- Goal: extend the close-up bust treatment to the full-figure rig (torso shape,
  key/shadow gradient, collar) so wides stop reading as flat tubes.
- Acceptance: 0.50s/2.20s/8.60s/11.20s frames reviewed; no slab look; gates green.
- Risks: rig is parametric — keep pose math untouched; test all POSES.
- Notes: _(fill during iteration)_

### SLICE-6 — Set lighting pass
- Goal: room gets motivated light (window moonlight pool, practical lamp glow,
  floor bounce, contact shadows under figures) instead of flat murky veil.
- Acceptance: measured separation + frame review; bounce must not read as halo.
- Risks: dark-on-dark identity of the style — do NOT brighten faces.
- Notes: _(fill during iteration)_

### SLICE-7 — Target-directed gestures
- Goal: reach/point aim at the actual prop position (from PROP_FRAME) instead of
  canned heights; generalize reachLow.
- Acceptance: b06 frame shows hand meeting book; continuity gate still PASS.
- Risks: new blocking can miss again — measure hand-to-prop distance in the gate.
- Notes: _(fill during iteration)_

### SLICE-8 — On-screen prop transfer
- Goal: re-block so the handoff is visible (insert or two-shot) rather than
  completing across a cut.
- Acceptance: continuity gate ownership segment appears mid-shot on screen.
- Risks: shot timing budget (12.2s fixed benchmark) — may need shot length edits.
- Notes: _(fill during iteration)_

### SLICE-9 — Sound post
- Goal: replace mood loop with a 2-3 motif score with variation; real foley from
  Kenney CC0 (fetch via github.com/KenneyNL or codeload, which ARE allowlisted)
  instead of whoosh-per-cut.
- Acceptance: cue list + loudness PASS; spectral sanity (not just noise).
- Risks: ffmpeg 2018 static build — check filters before use.
- Notes: _(fill during iteration)_

### SLICE-10 — prose -> manifest (text-in / film-out)
- Goal: natural-language scene description -> schema-valid story.json draft for
  human approval. The biggest PRODUCT gap (deferred twice).
- Acceptance: python test: prose -> valid story.json passing story_schema
  validation; render one short scene end-to-end.
- Risks: scope creep — keep to: parse beats/dialogue/props/sizes, emit JSON.
- Notes: _(fill during iteration)_

### BACKLOG (smaller)
- Render the pending dust additions on blueprint/end-card.
- Overlapping-dialogue test + gate.
- Hindi/Telugu voice + captions path (Kokoro multilingual check; espeak fallback).
- Throughput/QC: cache reuse already exists; add a frame-QC report to master.py.
- Publish/schedule/analytics: confirmed product gaps, out of scope for local QC.

## Explicitly NOT claimed
- No /100 score (no approved reference). Voices were espeak fixture until SLICE-4
  ships. Technical gates do not establish cinematic quality.
