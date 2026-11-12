# ADR 0003 — Dark-background styles (PROPOSED, not implemented)

**Status:** Proposed (2026-11-10). Implementation blocked pending this decision.

## Context
The fresh palette (`tools/fresh/palette.py`) can select `background: "dark"` and
the style vocabulary includes moods that imply dark scenes (night, void, storm).
However, the ink outline colour used by the character rig is hard-coded in two
places:

- `tools/fresh/core.py`: `INK = "#15131a"` (used for contrast checks in the palette).
- `chars/inkbean.js`: the outline colour is hard-coded (see `INK` constant / `ink` usage).

Every generated character, prop and set outline relies on this single dark ink.
A dark background would make dark-ink outlines invisible, breaking readability
and the visual-review gate (`review_frames.py` black/white frame checks).

## Decision (proposed)
1. Promote `INK` to a parameter threaded through `drawInkBean` / `drawFigure` /
   `chars/inkbean.js`, sourced from the project config (`config.json` → `ink`)
   instead of a module-level constant.
2. When a project's style pack declares `background: "dark"`, emit
   `ink: "#e8e4dc"` (or a palette-derived light ink) into `config.json` and use
   it in the character rig and the frame-QA luminance threshold.
3. `tools/fresh/core.py`'s `_readable_color` and contrast checks must use the
   project ink, not the module constant, so palette generation validates against
   the correct background.

## Consequences
- Touches protected paths (`chars/inkbean.js`) — requires explicit approval and
  a `style_lock` re-baseline.
- Affects `frame_qa.py` thresholds (black-frame detection assumes dark ink on
  light-ish backgrounds).
- Cannot be done behind `--fresh` alone; needs a config-level change + migration.

## Not yet implemented
This ADR records the decision surface only. No code changes are made here.
Candidate remains PROPOSED until approved.
```

Now Phase 5: 20-second preview stage with separate preview approval. Let me add a `--preview` flag to generate.py that renders only first 20s? Actually render is full. A preview stage would render a shorter video. This is complex (render.mjs supports frame ranges?). Let me check render.mjs.<|end|><|start|>start to=run_terminal_command<|channel|>analysis <|constrain|>xml<|message|><rfl:parameter name="command">
cd "E:/Local_Mis_WS/_yt_stickman/aitrends-2d-studio" && grep -n "preview\|--from\|--to\|frames\|duration" render.mjs | head -30