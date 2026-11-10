# ADR 0001 — Protected paths and the unforgable approval invariant

**Status:** Accepted (2026-11-10)
**Scope:** aitrends-2d-studio pipeline (Python tools + JS engine + render.mjs)

## Context

Two invariants have emerged from production use and must be recorded rather than
left as tribal knowledge:

1. Certain files are **protected** and must not be edited as a convenience.
2. Human approval is **bound to delivered bytes** and can only be written by one tool.

## Decision

### Protected paths (untouched unless a deliberate recorded decision)

- `engine/` (all files)
- `audio/sfx.py`
- `audio/mix.py`
- `render.mjs`

Any change to these is a **deliberate, recorded decision**, not a convenience.
Rationale: these are the rendering and audio core; an unreviewed edit can silently
change every project's output and invalidate prior approvals.

### The unprotect process

To touch a protected path, **all** of the following must hold:

1. **Who approves:** the project owner (the human who owns the repo and the
   shipped videos). No agent or subagent may self-approve.
2. **Where it is recorded:** a new ADR entry in `docs/adr/` (e.g.
   `000N-unprotect-<path>.md`) **and** a commit message whose body states the
   rationale and references the ADR number.
3. **What justifies it:** the change must be a deliberate capability or
   correctness fix, never a refactor convenience, never "while I'm in there."
4. **Verification:** the change must be backed by a test or a measured
   before/after on at least one real project, and `verify_kit.py` must still
   pass (protected files are pinned by it).

Until (1)–(4) are satisfied, candidates that require protected-path edits stay
**excluded**. They are not "postponed"; they are blocked.

### Unforgable approval invariant

- `tools/record_approval.py` is the **sole writer** of `report.json.approved_by`,
  `approval_state`, `approved_at`, and `approved_video_sha256`.
- `tools/generate.py` (and any other tool) **must not** accept an
  `--approved-by` (or equivalent) flag. `render_report.py --approved-by` is
  REFUSED by design.
- Approval is bound to `video_sha256`: `approval_gate.py` refuses unless the
  approved hash equals the current deliverable's hash. A re-render invalidates
  approval.
- `approval_gate.py` (read/check) and `style_lock.py` (visual reference) may be
  consolidated on the **read side only**. The **writer** (`record_approval.py`)
  must remain a separate module that `generate.py` cannot import as a callable
  approval shortcut.

## Consequences

- Candidates touching protected paths (e.g. audio restructuring, expression
  registry) are excluded by default; they require an ADR + owner approval.
- Refactors that would merge `check`/`snapshot`/`record` into one module are
  allowed only if the writer stays isolated.
- Any future report or plan must include a "constraints" section listing these
  invariants and rate candidates against them.

## Appendix — 0d evidence pass (2026-11-10)

Measured on the current tree:

- **Path recomputation:** 14 tools reference project paths (`project_root`,
  `story/`, `scenes/`, `build/`); 18 tools define their own `--project` argparse;
  path strings are rebuilt with `os.path.join` in ~10 tools. Config loading is
  centralized (`common.load_json`, `generate.load_cfg`), but path resolution is
  not. **Conclusion:** Candidate 2 (Project value object) is justified by real,
  measured pain — promote from "held" to "ready to design."
- **QC orchestration:** 8 distinct gate tools (`render_gate`, `scene_coverage`,
  `motion_audit`, `review_frames`, `seam_gate`, `render_report`, `style_lock`,
  `approval_gate`) with heterogeneous arg shapes, orchestrated by `generate.py`
  via `run()`. **Conclusion:** Candidate 3 (Gate protocol) is justified —
  promote from "held" to "ready to design."
- **Shot-body divergence:** `SHOT_JS` (director.py, lines 457–697, 241 lines)
  and `BODY_STAGE` (template_interpreter.py, lines 42–242, 201 lines) differ
  by design: the interpreter carries parameter slots (`ARCH.camZ0 ??`,
  `SETS[p.set]`, freeze combining `ARCH.freeze`+`p.freeze`) that director's
  fixed version lacks. Both were introduced in commit `33439ce` and co-evolved
  across 8 commits. **Conclusion:** Candidate 1 is a parameterization decision,
  not a copy-paste extraction. Design decision required before coding.
- **Protected files** (`engine/`, `audio/sfx.py`, `audio/mix.py`, `render.mjs`)
  are pinned by `tools/verify_kit.py` (29/29 files). Any change must follow
  the unprotect process above.

## Appendix B — Candidate 1 design decision (PROPOSED 2026-11-10, awaiting owner sign-off)

**Status: PROPOSED (not decided).** This records a recommendation, not a decision.
Owner must accept before implementation.

**Proposed decision:** Parameterize `director.py`'s `SHOT_JS` body to carry the same slots the
interpreter's `BODY_STAGE` already uses (`ARCH`, `SETS`, freeze-combining), so both
codegen paths share one body. Director keeps its richer comments; the slot lines
adopt the interpreter's form.

**Why not "extract and keep identical":** the two bodies have diverged by design
(8 co-evolution commits). The interpreter carries parameter slots (`ARCH.camZ0 ??`,
`SETS[p.set]`, freeze combining `ARCH.freeze`+`p.freeze`) that director's fixed
version lacks. Sharing requires choosing one form. Parameterizing director's body
is recommended because the interpreter is the newer, more general track, and
director becomes a thin emitter with default params (`ARCH = {}`, `SETS = {room, kitchen}`).

**Safety net (NOT byte-identical JS):** adding slots changes the emitted text, so
the golden check is **rendered-frame hashes**, not byte-identical JS. Golden
frames captured at `/tmp/golden_frames/` (6 PNGs, hashes in
`/tmp/golden_frames.sha256`) from `projects/cine_release` before any edit.
Implementation must re-render and confirm frame hashes match before merging.

**Implementation steps (for supervised execution):**
1. Capture golden rendered frames (done).
2. In `director.py` `SHOT_JS`: add `const ARCH = {};` and `const SETS = { room, kitchen };`
   after imports; replace the `SET` line, cam lines, and freeze line with the
   interpreter's slot-bearing form.
3. Re-run `director.py` on a copy of an existing project; confirm no runtime
   errors.
4. Re-render; compare frame hashes against golden. Any mismatch = regression.
5. Only after (4) passes, apply to real projects.

**Status:** PROPOSED. Implementation deferred to a supervised session
because it requires rendered-frame verification that cannot be automated safely
in an autonomous run.

## Appendix C — Render determinism & timing (2026-11-10)

- Rendered `projects/cine_release` stills twice (times 1.0, 4.2). Hashes identical
  across both runs (see tests/golden/ or /tmp/render1, /tmp/render2). **Rendering is
  deterministic** for this project, so rendered-frame hashes are a valid safety net
  for Candidate 1.
- Render time: ~3.1–4.8 s for 2 stills (2 runs). Measured, not estimated.
- Golden frames stored in repo at `tests/golden/` (6 PNGs + sha256.txt).

## Appendix D � Efficiency & determinism scope (2026-11-10)

**Efficiency:** `frame_qa.py` now does a FULL per-frame scan (not sparse sampling). Extracts
all frame lumas in a single ffmpeg pass (~0.6s on an 18s/432-frame video). Full scan
catches short freezes (>=3 frames) and single-frame pops that sparse sampling missed.
Cost is accepted: runs only at review time, not in the render path. Does NOT share
`motion_audit`'s frame scan; if profiling shows a bottleneck, `motion_audit` can emit
per-frame luma to a JSON sidecar that `frame_qa` reads instead.

**Determinism:** Confirmed only for **stills** (identical frame hashes across 2 renders on
the same machine and ffmpeg version). Candidate 1's safety net (hash comparison) is
valid only under that constraint. Full-video determinism is not claimed and is not needed
for Candidate 1 (which compares individual frames).
