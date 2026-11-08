---
name: make-2d-video
description: >
  This skill should be used when the user wants a narrated animated video in the aiTrends 2D style
  (cinematic stick figures with rim light, moody 2.5D sets, giant face close-ups, freeze-frames,
  data overlays, blueprint diagrams and low-poly 3D shots), e.g. "make a 2D video from this voiceover",
  "animate my script", "turn this narration into a stick figure video", "make a What If video",
  "create an animated explainer from my audio", or "do the whole video". It runs the full pipeline:
  install, timestamps (Whisper), story breakdown, style choice, scene building, rendering, music, SFX and
  final MP4 in 16:9 or 9:16 at 720p to 4K.
metadata:
  version: "0.1.0"
  author: aiTrends
---

# aiTrends 2D Studio: full video pipeline

Turn a voiceover (plus an optional script) into a finished MP4 where every frame is drawn by code (HTML canvas + Three.js), captured frame by frame in headless Chromium and encoded with ffmpeg. No image or video generation models are used, so characters stay consistent and text stays crisp. Invent the visuals fresh for every script; only the style is fixed.

**Bundled resources (this skill's base directory):**
- `kit/`: the tested studio (renderer, engine, tools, audio, the `examples/reaction-time` reference project). Install it into the workspace as `aitrends-2d-studio/` (see `references/install.md`).
- `references/install.md`: install, dependency table, doctor, self-test.
- `references/style-bible.md`: **the look** (characters, sets, light, camera, editing, graphics, 9:16 rules, don'ts). Read it fully before designing any shot.
- `references/story-breakdown.md`: writing `story/bible.md` and `story/shots.json`, plus pacing rules.
- `references/engine-api.md`: the scene API, config and shots.json schemas, and the three-kit reference.
- `references/sound-design.md`: the music plan, SFX library, ambience and levels.
- `references/render-qc.md`: preview and final render, speed guide, QC checklist, troubleshooting.
- `references/directing.md`: treatment-first directing, benchmark rule, three structures, the
  variety rule that protects monetisation, and the rights checklist.
- `references/style-recipes.md`: six looks beyond the five built-ins, written as directions rather
  than untested engine changes.
- `references/self-improve.md`: the shape line and three-line retro, plus the one-rule-change loop, adapted from Harness².

Stage commands from this plugin re-run one stage: `/new-video` (stages 1–4), `/video-styles` (5), `/render-video` (6 and 8), `/video-sound` (7). When running end to end, follow this file and load references as each stage needs them.

## Two ways to drive this

**A. Compiled (fast path, no voiceover needed).** `tools/director.py` is a deterministic template
compiler: a story JSON becomes a complete project — cast, blocking helpers, a parametric set, and one
shot file per shot. Narration is synthesised from each shot's `line` with Kokoro, and **every shot is
retimed to its measured speech**, so there is no fixed-duration grid and no dead air.

```bash
python tools/generate.py --story story.json --out projects/<slug> --audio [--strict]
```

It chains director -> narrate -> sound design -> render gate -> mix -> review -> seam gate -> report,
and stops on the first failure. `--strict` makes a dead cut fatal. Use this when the film fits what the
compiler can express: wide / med / close / insert, one parametric set, one or two characters,
continuous expressions, and cut / zoom / flash / dip / fade transitions.

Minimal story JSON:
```json
{"title":"Three In The Morning","aspect":"9:16","style":"midnight","chars":"inkbean",
 "cast":{"MAX":{"color":"#c2553d","top":"trench"},"JAKE":{"color":"#2f9e8f","top":"tshirt","head":"cap"}},
 "shots":[{"id":"s001","size":"wide","line":"Three in the morning.","hold":0.5,
           "who":"MAX","x":0.36,"expr":"neutral","exprTo":"worried","at":1.05,
           "who2":"JAKE","x2":0.68,"expr2":"sleepy","facing2":-1,
           "in":{"type":"fade","dur":0.5},
           "sfx":[{"at":0.05,"name":"whoosh","gain":-26}]}]}
```
- `size`: `wide | med | close | insert` — each carries its own eased camera move.
- `expr` / `exprTo` blend **continuously** across `at` seconds; the mouth is driven by real word timings.
- `hold`: seconds of air after the line. A shot with an empty `line` is a designed silent beat.
- `sfx` names come from `python audio/sfx.py --list`; `amb` takes a loopable bed.
- `chars`: `inkbean` (hand-drawn, continuous faces) or `stick` (rig2d stick figures).
- `cut_intent`: declare an eyeline or match cut that carries no shared object, or `seam_gate` warns.

**B. Hand-written (full control).** Stages 1–8 below. Reach for this when the film needs props in
hand, a real walk cycle, more than two characters, a bespoke set, or a device the compiler has no
vocabulary for. A hand-written project can beat the compiler — `projects/one-more-night-9x16/` is the
bar to clear.

Do not hand-write shot code for something the compiler already expresses: you will reproduce its
template by hand and drift from it on the next episode.

## Golden rules
1. **Keep the narration intact.** Never rewrite, add, drop or reorder spoken words. Every shot illustrates the words spoken while it is on screen.
2. **Same style, new pictures.** Invent sets, props, characters and actions from this script. Use `examples/reaction-time` only to learn the API.
3. **Show what is said, literally and specifically.** Abstract lines become visual metaphors, diagrams or close-up reactions.
4. **Draft, look, fix, then render.** Open contact sheets and stills yourself (read the PNGs) before any full render. Rendering is slow; looking is fast.
5. **Three user checkpoints:** setup choices, style choice from rendered samples, and the preview before the final render. If the user is away, take the defaults, state what was assumed, and continue.
6. **Files are the truth.** Each video lives in `aitrends-2d-studio/projects/<slug>/`, and `story/shots.json` owns all timing.
7. **Vary the episode, not just the topic.** Consecutive videos must differ in opening image, structure, dominant visual mode, transition signature and ending device. Keep the channel style; do not keep the same template. See `references/directing.md`.

## Stage 1: Intake
Ask once (AskUserQuestion when available) for:
- **Voiceover file** (required on the hand-written path; the compiled path synthesises narration
  from each shot's `line`).
- **Script:** timestamped (SRT/VTT/JSON/TXT with `[mm:ss]`), plain text (best: aligned to the audio, keeping exact wording), or none (transcribed).
- **Aspect:** 16:9 or 9:16.
- **Resolution:** 720p / 1080p (recommended) / 1440p / 2160p (4K). Mention that higher resolutions take much longer to render.
- **Captions:** default on for 9:16, off for 16:9.
- **Music:** generated, the user's own file, or none. **SFX:** on or off.
- **Title.**

Don't ask about style yet. Defaults: 16:9, 1080p, 24 fps, generated music + SFX, style `dusk`.

## Stage 2: Install or check the studio
Follow `references/install.md`: copy `kit/` to `aitrends-2d-studio/` in the workspace (skip if already present), install dependencies, run `python tools/verify_kit.py` and `python tools/doctor.py`, then run the example self-test. Report what was installed in one short list.

## Stage 3: Project + timeline
Run inside `aitrends-2d-studio/`. Use `python3` where `python` isn't Python 3.
```bash
python tools/new_project.py --name <slug> --voice "<voiceover path>" [--script "<script path>"] --aspect 16:9 --resolution 1080p --title "<title>" [--captions]
```
- Timestamped script: `python tools/parse_script.py --project projects/<slug> --script projects/<slug>/input/script.<ext>`
- Plain script: `python tools/transcribe.py --project projects/<slug> --script projects/<slug>/input/script.txt --lang en --model small`. The match must be ≥ 90%; if it's lower, tell the user the script and audio differ.
- No script: `python tools/transcribe.py --project projects/<slug> --lang en --model small` (`base` on slow machines, `large-v3` for hard audio).

Check `timeline/transcript.txt` (its end should be near the voiceover length), then run `python tools/beats.py --project projects/<slug>` to get the beat sheet and a draft `story/shots.json`.

## Stage 4: Story breakdown
Read `references/style-bible.md`, `references/directing.md` and `references/story-breakdown.md`. First write `story/treatment.md` (one-sentence film, benchmark learn/don’t-take, three structures, the chosen one, one native move, ending echo). Then write `story/bible.md` (logline, cast with one signature colour each, locations with moods and key lights, motifs, music plan). Write `scenes/cast.js`. Rewrite `story/shots.json`: contiguous shots, cut on phrase boundaries 0.1–0.2 s early, a median of 2–3.5 s, an establishing shot per new location, and a concrete `scene` description for each. Send the user a 5–10 line plan summary and continue unless they object.

## Stage 5: Style choice
Build the 1–2 most-used sets plus 3 representative shots (a wide shot with ≥ 2 characters, a `bigFace` close-up, a data/blueprint or 3D shot). Then render:
```bash
node render.mjs --project projects/<slug> --styles dusk,midnight,golden,neon,storybook --at <t1>,<t2>,<t3> --scale 0.5
```
Open `build/styles/style_grid.png`, then show it with one line per style: **dusk** (mauve shadows, amber key, cream rim), **midnight** (cold navy, blue-white rims, sodium practicals), **golden** (warm orange and teal), **neon** (deep blacks, magenta and teal), **storybook** (soft pastel, low contrast). Save the pick in `config.json` → `style`. If none fits, read `references/style-recipes.md` and choose a recipe before touching code. For tweaks, add a custom entry to `STYLES` in `engine/styles.js` (moods overrides plus the `grade` lift/gamma/gain, sat, contrast, vignette, grain, bloom) and re-render that row. A new `STYLES` entry is a deliberate customisation; test one shot before committing.

## Stage 6: Build every shot
**Skip this stage on the compiled path** — `director.py` writes `scenes/sets/*` and
`scenes/shots/*` from the story JSON. Only hand-write shots on path B.

Read `references/engine-api.md` and the example scenes in `examples/reaction-time/scenes/` once. Work in batches of 8–12 shots:
1. Write `scenes/sets/<location>.js` (reusable, anchored to `GY = E.H * V(0.8, 0.68)` and `CX = E.W/2`, with walls, floor and sky extended past the frame) and `scenes/shots/NN_<name>.js` with `registerShot('<id>', {...})` for the ids in shots.json.
2. Run `node render.mjs --project projects/<slug> --sheet --scale 0.5`. Open every `build/sheets/sheet_XX.png` and check it against the QC checklist in `references/render-qc.md`. Fix any MISSING shots, errors printed by the renderer, and composition problems.
3. Check motion with `--stills t1,t2,t3` or `--from A --to B --scale 0.5` (writes `build/preview.mp4`).
4. If `tools/seam_gate.py` is present (the live studio ships it; the minimal kit does not), run `python tools/seam_gate.py --project projects/<slug> --auto`. Fix every `WARN` by carrying a person/prop across, declare a deliberate discontinuity with `cut_intent`, or waive it in one line with a reason. The gate is a presence test, not a taste test.

Non-negotiables from the style bible:
- Rim light on every lit figure.
- Colours from `mood()`/`S()`.
- A camera move in every shot.
- Atmosphere (dust, rain, glows).
- Moody value structure.
- Graphics synced to words with `wordTime()`.
- `V()` for every aspect-dependent value.
- No `Math.random`/`Date.now`.

## Stage 7: Sound
Read `references/sound-design.md`. Fill `story/shots.json` → `music` (contiguous mood sections) and add per-shot `sfx` cues and `amb` beds. Mixing happens after the final render (Stage 8), or run `python audio/mix.py --project projects/<slug>` now to audition `build/mix.wav`.

## Stage 8: Render and deliver
Read `references/render-qc.md`.
1. Preview: `node render.mjs --project projects/<slug> --from 0 --to 30 --scale 0.5`. Show the user the preview or a contact sheet before the long render.
2. Final: prefer `python tools/render_gate.py --project projects/<slug>` over a bare
   `node render.mjs` — `render.mjs` prints shot errors but **exits 0**, so an unattended run
   reports success on a broken video. The gate scrapes the error signals and fails non-zero.
   Run it in the background for long videos and poll the log. The log prints fps and ETA, so share the estimate.
3. Run `python audio/mix.py --project projects/<slug>`, which generates music and SFX, ducks the music under the voice, normalises to −14 LUFS and muxes `out/<title>.mp4`.
4. QC the final file: duration matches, audio is present, and a 1-frame-per-10-s contact sheet looks right. Deliver the MP4 (send the file), then give the location in plain words and one line on what to tweak next if needed.
5. Write the shape line and three-line retro in `docs/LESSONS.md` (worked / failed / one rule), creating it from the template in `references/self-improve.md` if missing. Read the last five before the next episode. One rule change at a time.

## Defaults and judgement calls
- When unsure about a visual, choose the more literal, more cinematic option: a close-up for emotion, an insert for objects, a blueprint for mechanisms, 3D for big spaces.
- Keep about 15–25 shots per minute. Use 1–3 freeze-frames per video and about one 3D shot per minute.
- Keep each character's outfit colour fixed for the whole video, and keep screen direction consistent within a scene.
- Prefer re-rendering a fixed shot range over the whole video only when the user is comfortable splicing. Otherwise re-render everything.
