# Repository audit and reliability pass

Date: 2026-11-08 (UTC). Branch: `arena/1f5cc873-local-2d-t2v`.

## Scope and method

The request was to scan the full repository, critique the proposed path, then execute the
recommended order. The original checkout contained **728 tracked files / 22,758,690 bytes**.
Every tracked file was inventoried and hashed; Python, JavaScript/ESM, JSON, shell, PNG, Ogg and
font files received structural checks. Source and documentation were reviewed manually where
combined output was not truncated; this is not a claim that every line was read in one pass.

The original plan put the 12-template interpreter first. Self-review changed the order to:

1. reproducible scan + regression tests;
2. render/pipeline/cache safety;
3. templates on that safer foundation;
4. real browser/video/audio-path checks, kit/pin synchronization, and this report.

Reason: a template layer that can silently publish error-painted frames or reuse stale cache
entries would multiply the existing failure modes. The visual engine (`engine/`, `chars/`) and
the protected audio DSP/mixer were left unchanged. `render.mjs` was changed deliberately for
failure handling; that decision is recorded here and in the guide's merge ledger.

## Reproducible commands

```bash
npm ci
npx playwright install chromium       # plus ffmpeg/ffprobe on PATH
python -m pip install numpy scipy pillow
npm test                              # 5 Node unit + 21 Python unit tests
node --test tests/render-integration.mjs   # 3 real Chromium/ffmpeg tests
python tools/repo_scan.py --json build/audit/repo-scan.json
python tools/verify_kit.py            # 44/44 pinned runtime files
python tools/render_gate.py --selftest
```

`tools/repo_scan.py` scans tracked files plus untracked non-ignored files, skipping Git internals,
dependencies and generated build/out/cache directories. It checks UTF-8, Python AST, JSON with
duplicate-key rejection, JS syntax via Node, local import resolution, PNG chunk CRC/decompression,
Ogg page CRC, font tables, project contracts and the vendored plugin kit. It does not execute
project code or infer visual acceptance.

## Final structural scan

Final working-tree scan (`build/audit/repo-scan-final.json`):

- **746 files / 486 unique contents** (original 728 tracked + new audit/test/template files, including
  this report). Byte totals drift slightly as the report itself is edited; the JSON artifact records the
  exact scan-time total.
- **27 projects** checked (26 under `projects/` + `examples/reaction-time`).
- **57 mirrored kit files** checked against the live studio.
- 65 Python AST parses, 338 JavaScript syntax checks, 121 JSON parses, 3 shell syntax checks.
- 9/9 PNGs decode with valid chunk CRCs; 122/122 Ogg page CRCs pass; 12/12 font table directories pass.
- **0 structural errors. 22 warnings**, all missing optional/ignored media assets
  (voiceovers/scripts or generated `build/voice.wav` files absent from this checkout).

The first scanner run reported nine PNG CRC failures. That was a scanner bug: CRC-32 must cover
the chunk type as well as the payload. Corrected checks and Pillow decoding confirmed all nine
PNGs are valid. No image was "repaired" or altered.

## What changed

### Reproducible audit and tests

- `tools/repo_scan.py`, `tools/validate_project.py`: read-only inventory/structural scan and
  project contract validation (intervals, IDs, dimensions, transitions, SFX cues, word order,
  scene registration, missing-media warnings).
- `tests/render.test.mjs`, `tests/test_repository.py`, `tests/render-integration.mjs`:
  frame partitioning, path containment, concat escaping, cache fingerprints, compiler safety,
  template vocabulary, seam entities, stale-motion-report handling, and real render failure modes.
- `package.json`: `test`, `test:js`, `test:python`, `scan`, `verify:kit` scripts.

### Render and pipeline safety

- `render.mjs` + `render-utils.mjs`: strict CLI/numeric validation; loopback-only asset server with
  resolved-path containment and dotfile rejection; boot/import/missing-scene/shot errors fail;
  exact integer frame ranges (`--frame-from/--frame-to`) partition fractional shot boundaries
  without duplicate/dropped frames; ffmpeg exit/error propagation; per-run parts directory;
  output published by rename only after a complete encode; browsers closed on failure.
- `tools/render_gate.py`: validates the project first, streams render output, keeps defense-in-depth
  error-pattern detection.
- `tools/generate.py`: every required stage's exit code is checked; `--aspect` overrides the compiled
  story rather than only review; style-lock check runs before the report; review/report failures abort;
  `--strict` also fails unjudged/dead seams and motion warnings.
- `tools/render_cached.py`: full SHA-256 fingerprints include engine, chars, templates, renderer,
  player, package lock, project scenes/assets, word timings and render options; exact frame ranges;
  ffprobe validation of cached and newly rendered clips; atomic clip/output publication; correct
  concat apostrophe escaping.
- `tools/review_frames.py`: extraction/probe failures are fatal; aspect and blank-candidate checks
  affect exit code; explicit `--allow-dark` for intentional fades; report states human review required.
- `tools/style_lock.py`: `check` validates the manifest before re-rendering; malformed reference
  records are rejected.
- `tools/render_report.py`: selects the video stream explicitly; silent videos report audio/LUFS as
  not applicable instead of inventing measurements; motion audit writes/reads a project-local path
  and cannot reuse a stale report after failure; `--strict-motion` fails non-OK motion.
- `tools/seam_gate.py`: understands double-quoted registrations and data-driven template shots;
  `--strict` fails unjudged/missing scene code as well as WARN boundaries.
- `tools/narrate.py`: `--no-retime` preserves declared starts and rejects speech longer than its slot;
  template shots without `size` no longer crash the report. Word timings remain heuristic, not
  measured alignment.
- `tools/new_project.py`: creates beside the studio, rejects unsafe names and existing projects,
  stages files before publication.

### Template layer

- `templates/registry.json`, `templates/interpreter.js`: the 12 named archetypes from the plan:
  `establish-push`, `medium-two-shot`, `over-shoulder`, `giant-face`, `insert-object`,
  `blueprint-diagram`, `lowpoly-3d`, `pull-out-bookend`, `freeze-frame`, `title-card`, `end-card`,
  `transition-whip`.
- `tools/story_schema.py`: closed vocabulary mirrored from engine enums (tests assert the mirrors),
  closed per-template parameter sets, cast/pose/expression/mood/style/SFX/music validation.
- `tools/director.py`: validates before touching output; stages compilation; preserves hand-authored
  scenes and build/out/timeline; removes only stale director-generated shot files; emits
  `scenes/templates.js` and thin per-shot registrations for template stories. Legacy top-level shot
  fields still compile. Unknown template/param/pose/cast values fail instead of falling back.
- `examples/template-showcase.json`: technical capability showcase, explicitly not a finished episode.

The interpreter reuses engine drawing/timing helpers and the existing close-up base draw. It does
not replace the visual engine. `insert-object` now draws the declared mug/book/phone prop instead
of the legacy hardcoded fly. `end-card` does not add a subscribe pill or fabricated attribution.

### Kit and documentation synchronization

- Vendored kit updated for every changed mirrored runtime file, plus new required files
  (`render-utils.mjs`, `templates/`, `tools/story_schema.py`, `tools/validate_project.py`,
  `tools/repo_scan.py`, showcase example).
- `tools/verify_kit.py` pins updated deliberately; now **44/44** verified.
- Guide/install/render-QC references updated to describe native hard-fail behavior and the new pin count.

## Real verification performed

Environment: Node v22.22.3, Python 3.11.2, Playwright 1.56.0 with extracted Chromium 153 and bundled
AL2023 libraries, static ffmpeg/ffprobe, numpy/scipy/pillow. No GPU; SwiftShader CPU rendering.

- `npm test`: **5 Node + 21 Python tests pass**.
- `node --test tests/render-integration.mjs`: **3/3 pass** — real encode has exact dimensions/frame
  count; an intentional shot exception exits nonzero and preserves an existing deliverable; a missing
  scene fails even in contact-sheet mode.
- `python tools/verify_kit.py`: **44/44**.
- `python tools/repo_scan.py`: **0 errors / 22 missing-media warnings**.
- Full silent template pipeline (`tools/generate.py` on the 12-shot showcase): render gate PASS,
  frame review PASS (720x1280, 24.000 s, 0 blank candidates), report written. Encode: 576 frames,
  24.00 fps, 24.00 s, 4,566,757 bytes; SHA-256
  `eef991f90b39534b6c815906b055391b2578bd2cf4e682afadd66c2a9519dedc`.
  Render took about 6m47s at ~1.4 fps on this 2-CPU sandbox.
- Contact sheet opened and inspected: all 12 archetypes draw; no ERROR/MISSING frames. This is a
  technical/assistant inspection, not owner acceptance.
- Audio path fixture (synthetic speech-like WAV, **not Kokoro narration**): render → `audio/mix.py`
  → `tools/master.py` → report. Muxed H.264/AAC, 640x360, 12 fps, 72 frames, 6.000 s; measured
  **-14.20 LUFS, -6.36 dBTP**, target -14 LUFS. This proves the mix/master/mux path, not voice quality.
- Cached render: first run MISS/MISS then concatenates 72 frames; second run HIT/HIT and reuses both
  clips. A cache-validation type bug found during this run was fixed and retested.

## Known limits and remaining work

- **Human approval is still required.** No style lock was fabricated. The showcase has no approved
  style reference; `style_lock.py check` correctly reports NONE.
- The showcase is a capability reel, not a story. Seam gate reports 5 dead cuts by design between
  unrelated archetype demos; motion audit flags near-static diagram/end-card windows. `--strict`
  would fail those, which is correct. A real episode needs editorial carriers/holds and review.
- Kokoro narration and Whisper alignment were not run: model files are absent. Narration word times
  remain heuristic. The audio fixture used a synthetic signal.
- 22 project warnings are missing ignored/optional media in this checkout, not corrupt files.
- Historical market/performance claims in older docs remain unverified here. The measured sandbox
  speed (~1.4 fps at 720x1280) is not a universal production estimate.
- `engine/`, `chars/`, `audio/dsp.py`, `audio/music.py`, `audio/sfx.py`, `audio/mix.py` were not
  modified. Future changes to them need explicit pins, kit sync and visual regression approval.

## Recommended next order

1. Have the owner review the showcase contact sheet and a real short episode; create a style lock only
   from accepted frames with verbatim approval.
2. Run one real Kokoro-narrated episode end-to-end with `--strict`, fix editorial seam/motion issues,
   and record the result in `docs/LESSONS.md`.
3. Add measured word alignment (Whisper) before relying on word-anchored beats for production.
4. Only then scale to a season/batch; keep hero shots hand-authored and templates for the reusable bulk.
