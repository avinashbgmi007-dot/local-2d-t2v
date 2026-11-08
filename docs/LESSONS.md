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
