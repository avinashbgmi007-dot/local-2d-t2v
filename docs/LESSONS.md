# Lessons

One entry per episode: one shape line and three retro lines, written after the film is watched and
before the next project starts. Read the last five before choosing the next episode’s structure.

The method is in the plugin at `plugin/skills/make-2d-video/references/self-improve.md` (paths from the
workspace root). Keep entries concrete and checkable; “make it better” is not a lesson.

## Template

```md
## YYYY-MM-DD — <project>
- Shape: <structure> / <opening image> / <dominant visual mode> / <transition signature> / <ending device>
- Worked:
- Failed:
- Rule:
```

## 2026-11-06 — acting-pass / One More Night (example, replace when a real retro is written)

- Shape: single-scene dialogue / wide night-kitchen two-shot / kitchen two-shot and giant-face close-up /
  hard cuts with one flash on the keys / bookend pull-out to the opening wide.
- Worked: staggering the face turn (eyes first, mouth 0.25 s later) made s008 read as a thought
  arriving rather than a switch being flipped.
- Failed: the 16:9 cut was built without a style lock (`build/report.json` records
  `"style_lock": null`), and the 9:16 re-cut has the same unset lock; the character was approved in
  `char-lab` but never pinned on the episode.
- Rule: snapshot the style lock on the first finished cut of an episode, before the aspect re-cut,
  and verify it again on the re-cut.

## 2026-11-08 — quality-benchmark / The Book (dialogue slice)

- Shape: two-hander argument / wide night room two-shot / giant-face close-ups plus one prop insert /
  hard cuts / bookend pull-out.
- Worked: measuring the mouth envelope from the actual recording and gating it by word windows made
  routing provable — `tools/speech_audit.mjs` draws all 293 frames and asserts 0 wrong-speaker mouths
  and 0 mouths open in silent beats. Two real sync bugs fell out of that assertion, not out of watching.
- Failed: the insert prop. Scaling it up 4x cropped it off both edges, and the underlying drawing was a
  landscape rect with a cream centre that read as a picture frame at any size. Scale was the symptom;
  the drawing was the disease. Also shipped a caption card reading "THAT IS NOT THE" because a 4-word
  cap fired before the sentence ended — a word count is not a phrase.
- Rule: when a prop or a caption looks wrong, fix the thing that makes it identifiable (geometry,
  phrase boundary) before touching its size. And never assert a quality number against a reference
  that does not exist yet — the rubric is defined, the scoring is not done.

## 2026-11-08 — quality-benchmark / The Book (prop continuity slice)

- Shape: unchanged benchmark; added shot-level prop ownership across all 8 shots.
- Worked: making the prop a property of a PERSON rather than of a shot. One declaration then drove
  the figure's hand, the insert, and a geometry gate that measures the hand-to-object gap on all 293
  frames. Also: sharing one pose object between figure and prop makes drift structurally impossible.
- Failed: the first pass passed the gate and still looked wrong — the book was ~4% of frame width, so
  continuity was "verified" while the audience could not see the book at all. A geometry gate cannot
  judge readability. Second failure: `reach` aims at head height, so the offer/receive beat played to
  empty air until a hip-height preset existed.
- Rule: a gate proves the property it measures, nothing more. After every green gate, still ask "can a
  viewer see it?" — and stage a gesture against where the object actually is, not where the preset
  happens to put the hand.

## 2026-11-08 — quality-benchmark / The Book (close-up body + separation)

- Shape: unchanged benchmark; close-ups rebuilt as a bust behind the head, plus a silhouette rim and
  a motivated bounce from the room practical.
- Worked: diagnosing "dark-on-dark" as a SEPARATION problem rather than an exposure problem. Lifting
  the face would have broken the ink-bean identity; a faint full-circle rim plus background bounce
  took head-vs-background luminance from near zero to a measured 29.5–37.4 without changing the style.
- Failed: the first bust stopped at cy+2.7R and left a beige strip of set visible under it — a shape
  that is correct in isolation still has to be framed. Caught only by looking at the render.
- Rule: before changing exposure, ask whether the subject has an EDGE. And draw a body behind the
  head, never over it — occlusion order is what makes a neck read as a neck.

## 2026-11-08 — SLICE-4: local Kokoro voices shipped (espeak fixture retired for narration)

- Worked: the "Kokoro weights unreachable" dead-end was WRONG in general — only HF and
  GitHub-release-asset routes are blocked. npm (`kokoro-q8-shards` with a sha256-pinned
  6-part reassembly, `kokoro-local-runtime` voices), pypi (`kokoro-onnx` vocab,
  `piper-phonemize`+`espeakng_loader` IPA) and `onnxruntime-web` WASM (ships inside its
  npm tarball) cover everything. Fully offline, ~3s/line on CPU.
- Worked: keeping test_voice.py's output contract (voice.wav/stems/words.json) meant
  zero downstream changes; espeak stays ONLY as the word-clock (its WORD events are
  measured, then stretched per-line to the Kokoro duration) — the speech audit
  (420/0) proves the stretch is sound.
- Learned: onnxruntime-node's postinstall fetches blocked GitHub binaries — always
  `--ignore-scripts`; ESM imports resolve from the SCRIPT's dir, so import
  onnxruntime-web via absolute pathToFileURL into the asset dir.
- Learned: Kokoro is slower than espeak per line, so shots sized for espeak overflow —
  auto-fit `speed` (clamped <=1.9) per line, and re-run for lines that need it.
- Caveat: gates prove sync, not pleasantness — voice quality is judged by ear, by the user.

## 2026-11-08 — SLICE-5: full-figure torso shading

- Worked: replacing the flat capsule + hard 30% shadow strip with a sloped-shoulder
  path and a 3-stop key-to-shadow gradient made wide shots read as bodies, not tubes.
  Keeping EVERY joint coordinate (sh/hip/eF/hF) identical meant the prop-contact gate
  stayed green with zero contact fixes — change fills, never anchors, when a gate
  depends on geometry.
- Worked: light direction in local -x for the full figure matches both the leg rims
  (always at -17.5) and the close-up bust (lit=-1) — one consistent key light.
- Watch: at wide scale (1.45x) fine details (collar V) vanish — design for the smallest
  scale the asset appears at; 3 gradient stops, no banding observed.

## 2026-11-08 — SLICE-6: set lighting pass

- Worked: two motivated sources (cool window moonlight + warm pendant) with soft wide
  glows and floor pools made the room read at night; wall/floor luminance separation
  measured ~53 vs ~18. Lighting the ENVIRONMENT (never the ink-bean faces) preserves
  the dark-on-dark identity while fixing murk.
- Rule: raise glow radius together with alpha — small+bright reads as halo, wide+soft
  reads as light. Close-up veil stays; separation there comes from the slice-3 rim+bounce.

## 2026-11-08 — SLICE-7+8: aimed gestures + on-screen prop transfer

- Aimed reach: compute the target from the OTHER figure's pose (hand world position),
  not from a preset. Combined with prop.from/at, the reach lands exactly where the
  book is, so the mid-shot swap is pixel-seamless.
- Gotcha: templates receive LOCAL shot time (player.js drawShot passes lt). Assuming
  global t double-subtracts and silently breaks time-based logic — the continuity
  gate caught it (wrong-holder frames), which is exactly what the gate is for.
- Mid-shot ownership needs all three of: schema fields, interpreter effective-owner,
  gate effective-owner. Missing any one -> gate FAIL, not silent corruption.

## 2026-11-08 — SLICE-9: sound post

- Identical whoosh on every cut is a stuck record: vary seed/pitch/gain per cut.
- Story beats deserve story foley: an on-screen prop transfer gets a paper swish at
  exactly prop.at*dur (measured: -17.2 -> -12.0 dB peak in the otherwise silent shot).
- Music loop -> motifs: rotate the key per plan segment (render_score key + i*5).
- Kenney CC0 audio is unreachable from the allowlist (kenney.nl blocked, no github
  audio mirror) — do not retry; audio/sfx.py synthesis is the local foley source.

## 2026-11-08 — SLICE-10: prose -> manifest (text-in/film-out)

- Worked: a deterministic documented mini-grammar beats an LLM prompt here — testable,
  offline, and every output is schema-validated before anything is written.
- Learned (gate-caught): director's generated size-'insert' scene draws a FLY, not the
  prop — insert beats must compile to template 'insert-object'. A green parse + red gate
  caught it; the gate is the spec.
- Learned: legacy size shots use top-level scalar who/who2/pose/pose2 (params is for
  template shots only); bg must be a MOODS entry ('night'), not 'midnight'.
- Prose props flow through the SAME ownership machinery as authored stories — "takes"
  emits prop.from/at and the handoff renders on screen (JAY->MIRA at 11.42s).

## 2026-11-08 — two user-requested micro dramas from prose (Prompt + The Last Entry)

- The SLICE-10 grammar is enough for real hook structure: cold-open wide -> accusation ->
  excuse -> object held -> seized ON SCREEN (from/at) -> smoking-gun close-up -> insert
  of the object -> button line -> wide bookend. For the thriller the reveal is simply the
  LAST spoken line before the button — structure over effects.
- Distinct Kokoro voices per role work well (af_nova/am_eric for the AI-trend pair,
  bm_george/bf_emma British for noir). Voice casting is a story beat, not a detail.
- Caption word-highlight tracks the measured word clock — the stressed word lights up.
- Still weak: facial expressions are static presets per shot; the acting reads through
  dialogue + framing, not faces. That is the next acting slice if wanted.
