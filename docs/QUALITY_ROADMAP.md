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
- SLICE-4 DONE (commit pending): Kokoro-82M q8 local voices shipped in the video.
  tools/setup_tts.sh fetches model (npm shards, sha256-verified), voices (npm),
  vocab (pypi), IPA (pypi piper-phonemize+espeakng_loader); tools/kokoro_voice.py
  keeps test_voice.py's output contract; tools/kokoro_run.mjs runs onnxruntime-web
  WASM. Auto speed-fit per line (1.0-1.34) keeps speech inside shots. Gates PASS
  (envelope 420/0, continuity PASS); master -14.38 LUFS/-1.71 dBTP PASS; per-shot
  RMS: speaking shots -17..-18 dB, silent shots -25..-31 dB. 19 words.
  Notes/self-critique: word timings are espeak-measured stretched to Kokoro
  durations (audit-verified, but listen-check belongs to the user); b07 runs at
  speed 1.34 and may sound rushed; loudness error widened to -0.38 LU (was -0.14).
- SLICE-5 DONE (commit pending): full-figure torso = sloped-shoulder path + 3-stop
  key-to-shadow linGrad (key at local -x, matching leg rims) + hem AO + collar V +
  lit edge rim; anchors (sh/hip/hF) untouched so prop contact is unchanged.
  Gates PASS (continuity contact intact), review10 sheet: wides read as bodies now.
  Notes/self-critique: fill/shading only, zero joint-coordinate changes (contact gate
  proves it); gradient stops kept to 3 to avoid banding at wide 1.45x scale; collar V
  barely visible at wide scale (accepted); shadow side vs background is SLICE-6.
- SLICE-6 DONE (commit pending): set lighting — stronger window glow (0.12) + god
  rays (0.075), pendant bloom on the wall, lighter floor at the wall line, lamp cone
  0.13 / pool 0.27, plus a cool moonlight pool from the window. Environment only;
  characters untouched. review11: wall mean lum ~53 vs floor ~18 (separation),
  two motivated sources read, no halo. Gates PASS, master -14.38 LUFS PASS.
  Notes/self-critique: kept glows wide+soft; close-up veil/bounce untouched (slice 3).
- SLICE-7 DONE: reach poses now AIM at the other figure's actual hand (where the prop
  is held) instead of a canned height — computed per shot in interpreter.figure().
  review12: at 8.40-9.00s NILA's mitten lands on the book. Gate PASS.
- SLICE-8 DONE: on-screen handoff via prop.from/prop.at (fraction of shot). b06:
  ARUN holds until 65%, NILA takes over AT 9.00s mid-shot, right where her aimed
  reach lands -> seamless swap. Gate timeline: (none)->ARUN @0.00, ARUN->NILA @9.00
  inside b06; 0 wrong-holder / no-contact frames. Schema+gate+tests updated (37 py).
  Notes/self-critique: templates receive LOCAL shot time (player drawShot) — the
  first version double-subtracted shot.start and the gate caught it (10 wrong-holder
  frames). The gate is what makes a mid-shot transfer safe to ship.
- SLICE-9 DONE: sound post — per-cut whoosh variation (seed 40+i*7, pitch 0.9-1.26,
  gain steps) instead of one stuck whoosh; paper 'swish' at the on-screen handoff
  (b06 prop.from/at -> cue at 0.78s local = 9.00s global; measured peak bump -17.2 ->
  -12.0 dB in the silent shot); music render_score now rotates the key per plan
  segment (+5 semitones) so segments are motifs, not one loop. Kenney CC0 files are
  NOT reachable (kenney.nl not allowlisted; no audio repo under github KenneyNL org)
  — foley stays synthesized in audio/sfx.py. Gates PASS, master -14.34 LUFS PASS.
  Notes/self-critique: could not A/B-listen; evidence is cue list + measured
  transients + loudness, not ear. Score pleasantness remains user-judged.
- SLICE-10 DONE (commit pending): tools/prose_to_manifest.py — deterministic mini-grammar
  (Title/Set/Cast/Voices headers; [size] tags; "X says:", "X holds/takes/reaches for the
  <prop>", "for N seconds") -> schema-valid story.json -> full pipeline. Demo
  examples/quality-benchmark/prose_mug.txt -> build/quality/prose/out/The_Mug.mp4 (14.2s,
  kitchen set, mug prop, on-screen transfer JAY->MIRA at 11.42s via from/at, insert-object
  shot). Gates PASS both projects; master -14.22 LUFS PASS; 41 py tests.
  Notes/self-critique: size-'insert' in director's generated scenes draws a decorative FLY
  and never the prop — insert beats MUST use template 'insert-object' (learned via gate
  MISSING failure). Legacy size shots take top-level scalar who/who2/pose/pose2 (params is
  template-only). Generator puts the prop-relevant actor in `who` (figure 1 holds the prop
  in the generated size path).
- USER DELIVERABLES DONE (commit pending): two prose-written micro dramas rendered via
  SLICE-10 pipeline —
  1) examples/quality-benchmark/prose_prompt.txt -> drama1/out/Prompt.mp4 (20.0s,
     AI-trend scene "you let the AI write our fight?", phone seized on screen SAM->LEX
     @10.21s, insert, button line; -14.12 LUFS PASS)
  2) examples/quality-benchmark/prose_detective.txt -> drama2/out/The_Last_Entry.mp4
     (23.2s noir, diary RUTH->DET @9.92s, torn-page clue, REVEAL as last line "It was
     you. I read it." then wide button; gates PASS)
  Both: speech audit PASS, continuity PASS, captions highlight stressed words, British
  voices bm_george/bf_emma for the noir. Served at port 8000 as /Prompt.mp4 and
  /The_Last_Entry.mp4.
  Critique: expressions are still static presets (neutral/talk) — acting is the weakest
  remaining link; insert frames verified by gate counts (drawn every frame) though my
  sheet sampling missed the insert windows.
- Backlog: end-card dust render; overlapping-dialogue gate; hi/te TTS; frame-QC report.

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
