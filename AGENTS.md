# Agent working rules

Read this at the start of every turn. These are standing instructions from the user,
not suggestions.

## 1. Tool-call budget — HARD LIMIT 68

**Never exceed 68 tool calls in a single turn.** Arena's harness force-interrupts the
turn when its cap is reached, which cuts the work off mid-edit and wastes the
remainder of the budget on a hand-back message.

Operate to this schedule instead:

| Calls used | What to do |
| --- | --- |
| 0–50 | Normal implementation work. |
| 50–58 | Finish the current edit; start no new investigation threads. |
| 58–64 | Verify what is already changed, write the summary, plan the next turn. |
| 65–68 | **Emergency only.** Summary + hand-back. Do not start work. |

Practical rules:

- **Count as you go.** Keep a running tally; do not discover the ceiling by hitting it.
- **Batch reads.** One `bash` call with several `sed`/`grep`/`cat` sections beats six
  separate calls. Never spend a call to read 20 lines.
- **Batch edits.** Multiple related edits to one file go in a single scripted patch
  (`python3 - <<'PY'` with asserted replacements), not N `edit_file` calls.
- **Parallelise independent calls** in one response.
- **Renders are cheap in calls, expensive in time**: `start_process` + one
  `get_process_output(wait_for='exit')`, never a polling loop.
- If a task cannot fit, **do the smallest complete, renderable slice** and hand back
  with the remainder explicitly planned. A finished small slice beats a half-applied
  large one.

## 2. Every iteration ships a SHORT video, presented to the user

For **every** change to the video-generation flow — no exceptions:

1. Render a **short** clip (the fixed 12.2 s benchmark, or shorter for a focused check).
2. Extract frames and actually look at them.
3. Self-review against the previous iteration and fix what the review exposes.
4. **`present_file` the video** so the user can watch it and give direction. Do not
   keep the result to yourself or describe it only in prose — the user has explicitly
   asked to see the progression each iteration and steer from it.

Use the SAME benchmark across iterations so progress is comparable, and report what
changed versus the last clip. Tests passing is not review. A green gate is not visual
approval. State plainly what the render proved and what it did not.

## 3. Honesty

Brutal, specific assessments. No sugarcoating, no claiming a quality number that was
not measured against a reference. A loudness pass is not cinematic quality.

## 4. Runtime does not survive between turns

`node_modules`, pip packages, `build/`, `out/` and `/tmp` are wiped. Restore with:

```bash
bash tools/setup_runtime.sh
```

Then prefix render/audio commands with:

```bash
export PATH=/home/user/.local/bin:$PATH \
       LD_LIBRARY_PATH=/tmp/al2023/lib:/tmp \
       PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/tmp/chromium
```

## 5. Known dead ends — do not retry

- **Kokoro via HF/GitHub-release assets is unreachable** (those hosts are
  blocked), BUT a fully local Kokoro-82M q8 route EXISTS via allowlisted hosts
  (proven 2026-11-08): npm `kokoro-q8-shards` (reassemble 6 parts, sha256
  fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478) +
  voices from npm `kokoro-local-runtime` + vocab from pypi `kokoro-onnx`
  config.json + IPA from pypi `piper-phonemize`/`espeakng_loader` + inference
  via `onnxruntime-web` wasm (install npm pkgs with `--ignore-scripts
  --strict-ssl=false`; onnxruntime-node's postinstall fetches blocked GitHub
  release binaries — do not use it). Until SLICE-4 ships, `tools/test_voice.py`
  (espeak-ng) remains a TEST FIXTURE ONLY — robotic, never production narration.
- `@sparticuz/chromium` must be `require(...).default`; `require.resolve` of its
  `package.json` throws. v153 has **no `inflate()`** — extract `al2023.tar.br`
  manually (the setup script does this).
- pip is PEP 668 managed: use `--user --break-system-packages`.
- The installed ffmpeg is a 2018 static build; check filter availability before use.
- Renders must use `start_process`, never `bash` (they outlive the bash timeout).

## 6. Autonomous quality loop — docs/QUALITY_ROADMAP.md is the driver

Every turn: read the STATE section of `docs/QUALITY_ROADMAP.md`, run the
iteration protocol on the first non-DONE backlog item (self-critique -> implement
-> gates/tests -> render short video -> frame-sheet self-review -> fix ->
`present_file` the video -> update STATE/LESSONS -> commit), as many full
iterations as fit inside the 68-call budget, then summarize + conclude with the
next queued step. Do NOT stop to ask "what next?" — proceed autonomously. Ask the
user only when genuinely blocked or when the choice is theirs (voice pick,
style lock, reference approval). A turn ends early only at the call budget.
