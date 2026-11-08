# Self-improvement loop

A lightweight version of the useful idea in `google-research/harness2` (Apache-2.0): improve the
**harness** around the model — prompts, skills, checks, tool use — from evidence, not from a feeling.
Harness² does this with a Propose–Probe–Compose loop and a persistent improvement harness. This
pipeline does the same thing with a shape line, three retro lines and one rule change per episode.

Do **not** install the framework for this. It is Python/uv/Vertex benchmark infrastructure, it is not
in the render path, and it would add a dependency without adding a frame. The method is the useful
part.

## After every episode

Open `docs/LESSONS.md` and add one shape line plus exactly three retro lines:

0. **Shape** — structure / opening image / dominant visual mode / transition signature / ending device.
   This is the variety log; the next episode reads it before choosing a shape.
1. **Worked** — one thing that made the episode better, in concrete terms.
2. **Failed** — one thing that cost a re-render, a bad cut, or a weak beat.
3. **Rule** — one change to the process, written as an instruction the next run can follow.

“The acting was good” is not a lesson. “Staggering the mouth 0.25 s behind the eyes made s008 read as
a thought” is.

## Before the next episode

Read the last five entries. If the same “Failed” line appears twice, the “Rule” did not work — change
the rule, not the line.

Apply at most **one** rule change per episode. Changing five things at once means you cannot tell
which one helped.

## What belongs in a rule

A rule must be checkable before publishing:

- “Every new episode gets a `story/treatment.md` before `shots.json`.”
- “Run `seam_gate.py --auto`; every WARN is fixed, declared with `cut_intent`, or waived in one line
  with a reason.”
- “No two consecutive episodes use the same opening image and dominant visual mode.”
- “A close-up gets a blink or a breath; a held face with neither is a freeze-frame by accident.”

A rule that says “make it more cinematic” is not a rule.

## What not to do

- Do not rewrite the whole skill after one bad episode. One rule at a time.
- Do not add a new tool when a checklist line would do.
- Do not copy a lesson from another channel’s process without testing it on one episode.
- Do not let the lessons file become a diary. One shape line and three retro lines, then stop.
- Do not change `engine/`, `audio/`, `render.mjs` or the approved character to satisfy a lesson. If a
  lesson seems to require that, it is a project-level change and needs a test render and the owner’s
  sign-off.

## Template

```md
## YYYY-MM-DD — <project>
- Shape: <structure> / <opening image> / <dominant visual mode> / <transition signature> / <ending device>
- Worked:
- Failed:
- Rule:
```

The file lives at `docs/LESSONS.md` in the studio, next to `MOTION_BASELINE.md`.
