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
