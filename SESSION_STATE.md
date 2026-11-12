# SESSION STATE — resume here

**Overwrite this file at the end of every working session.** It exists so a new
chat can pick up without re-reading 70k lines of transcript.
Architecture and vocabulary live in `CONTEXT.md`; this is only *current state*.

Last updated: 2026-11-13  ·  commit `e32eac4`  ·  branch `master` = `origin/master`

---

## First three things to do in a new session

1. Read `CONTEXT.md` (architecture) and this file (state).
2. Run the suite. It must print `OK` / `Ran 342 tests`:
   ```
   "C:/Users/Avinash-Pro/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe" tools/selftest_gates.py
   python tools/verify_kit.py        # expect 26/29 + 3 deliberate
   ```
3. Ask the owner before producing a video. See **Standing rules**.

---

## Interpreter cheat-sheet

| Task | Interpreter |
|---|---|
| anything using PIL / numpy (`grade.py`, `review_frames.py`, `script_frame_check.py`) | `C:/Users/Avinash-Pro/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe` |
| TTS / audio mix (Kokoro) | `C:/Users/Avinash-Pro/.faceless-shorts/venv/Scripts/python.exe` |
| plain `python` | fine for `director.py`, `selftest_gates.py` |

Kokoro models: `~/.faceless-shorts/kokoro/{kokoro-v1.0.onnx, voices-v1.0.bin}`.

---

## Full chain for one film (order matters)

Narration **retimes the shots**, so it must run before the render.

```
"<tts-venv>/python.exe" tools/narrate.py       --project P
python                         tools/sound_design.py --project P
"<managed>/python.exe"         tools/render_gate.py   --project P -- --workers 1 --scale 0.5
"<tts-venv>/python.exe"        audio/mix.py           --project P
python                         tools/master.py        --project P
"<managed>/python.exe"         tools/grade.py         --project P --in-place
```

One command does all of it: `python tools/generate.py --fresh "<concept>" --out P --audio`.
`--fresh` derives location, cast, wardrobe, props, audio, style and acting from
the story. Nothing is defaulted; naming something pins it.

**Memory rule:** stop any local LLM server before rendering. A loaded GGUF
reserves ~26 GB of commit space and ffmpeg then dies with `Cannot allocate
memory`. Need ≥6 GB headroom; below that render at `--scale 0.5 --workers 1`.

---

## What works (measured, not claimed)

- **Story → film, fully local.** No `fetch`, no XHR, no remote URL in the render
  path. three.js is a pinned npm dep; Chromium is headless-local.
- **342 tests**, `verify_kit` 26/29 + 3 deliberate. `engine/` is hash-pinned and
  never edited — 3D is *consumed* through `engine/three-kit.js`.
- **Delivered reference film** `projects/dragon_check`: 11.96 s, 540×960,
  h264+aac, −14.33 LUFS, TP −1.71 dBTP, mean −18.6 dB, 8/8 script/frame aligned
  on frames decoded from the MP4 itself.
- **Subject renderer** — 11 kinds (7 animals + jar/lantern/chest/sword), plus a
  semantic gate: a film that *names* a creature must *show* one.
- **Gates that bite:** `script_frame_check` (script vs frames, fails the old
  broken `acting_dragon`), `validate_freeze`, `validate_repeat_framing`,
  `validate_palette_and_cast`, `validate_subject`.
- **Cast readability** — legs chosen against the wall, not blindly darkened:
  15 of 26 cast/set pairs under ΔE 30 → **1 of 26**.
- **Colour grade** — `tools/grade.py`, fitted constants from
  `mromidev/claude-animated-shorts` (MIT). Saturation 0.214 → 0.336.
- **3D stage** — one parametric builder over a `LAYOUT` table, on the line-less
  wide only (3D figures have no mouth, so no lip-sync). Cast and subject are
  **billboards of our own 2D drawing**, unlit + alpha-tested so they keep our
  art and still cast shadows. Cost: 6.77 fps vs 13.08 fps for 2D (1.93×).
- **Series continuity** — `series/<id>.json` stores what episode 1 *resolved*
  (set, style, mood, palette); later episodes follow the pin.

## What is still wrong (do not claim these work)

- 3D interiors are sparse: bare-ish wall, no contact shadow under the dragon.
- Only **1 of 8** shots is 3D. Depth pays once per film, not throughout.
- Object subjects (a jar, a sword) are drawn but never *act*.
- 540p is the practical ceiling at ~4 GB headroom.
- `projects/cine_release` needs **owner** re-approval (25 characters gained caps).
- The 0.25 near-duplicate threshold from the third-party pack is **untested**.

## Monetisation constraint (this shapes the roadmap)

YouTube's *Inauthentic Content* policy names "characters land in the same
situation over and over with the same outcome" and "AI content from generic
templates" as non-monetisable. Six fixed shapes with a noun slotted in **is that
risk**. Structure variety is an eligibility requirement, not polish. Explicitly
allowed: "a series that follows a set of characters across episodes". Shorts
alone are a weak ladder — long-form compilations still needed.

## Standing rules (owner-set, do not relax)

1. **Never render, generate, process or upload video without an explicit ask
   AND a confirmation.** Research, reading and stills are fine.
2. **No static defaults in generation.** Location, cast, wardrobe, props, audio,
   style, dressing, acting all derive from the story unless pinned.
3. **Validate first, build later.** A feasibility question gets an assessment,
   not deliverable files.
4. **Do not agree by default.** State agreement or disagreement with reasoning.
5. **End every reply with a self-critique** (assumptions, verified vs asserted,
   what was not checked).
6. Leverage third-party material only if it enhances the flow, does not harm
   monetisation, does not degrade quality, and does not degrade efficiency.

## Where the memory lives

- Workspace log: `E:/Local_Mis_WS/.workbuddy-ai/memory/YYYY-MM-DD.md`
- Project notes: `E:/Local_Mis_WS/.workbuddy-ai/memory/MEMORY.md`
- Expert team `miniseries-lab` is **session-scoped** — re-select it in Expert
  Center at the start of every new conversation, or it silently does nothing.
