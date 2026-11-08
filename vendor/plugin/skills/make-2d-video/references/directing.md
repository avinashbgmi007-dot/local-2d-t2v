# Directing an episode

Read this before Stage 4. The pipeline can render anything; this file decides whether the episode is
worth watching. It is a method, not a template: the point is to make each episode differently good,
not to make every episode the same.

Method adapted from `lemomo-ai/lemo-opuscar` `DIRECTOR.md` (MIT), rewritten for this pipeline. See
`aitrends-2d-studio/THIRD_PARTY.md`.

## 1. Say the film in one sentence

Before any shot: “A ___ wants ___, but ___, so ___.” If that sentence is boring, the episode is
boring. Fix the sentence, not the lighting.

The film needs one subject, one goal and one turn. A topic is not a story. “Why doesn’t your stomach
digest itself?” is a question; the film is the turn from “my body is trying to kill me” to “my body
is protecting me.”

## 2. Pick a benchmark before you write shots

Choose one or two works — a film, a title sequence, a game, an ad — that set the bar for this topic
and this look. Write two lines:

- **Learn:** composition, pacing, camera grammar, colour logic, score structure.
- **Don’t take:** characters, designs, melodies, specific shots, logos, fonts, voices.

The benchmark is not there to copy. It is there to stop the first obvious idea from becoming the
episode. Never use a creator’s face, voice, footage, logo or show name.

## 3. Draft three structures, then choose one

Write three candidate shapes in a few lines each, for example:

1. **A single journey** — one character moves through one place, and the place changes around them.
2. **Before / after** — the same image twice, with one thing altered.
3. **A countdown or list that turns** — the items are ordinary until the last one re-reads the first.

Choose the one that makes the turn land without narration explaining it. The first idea is usually
the genre’s default; the second is usually the same with a different set. The third is often the
episode.

## 4. Write `story/treatment.md` before `story/shots.json`

Keep it short:

- Logline and arc: setup → turn → ending.
- Benchmark: learn / don’t take.
- Shot list: framing (wide / full / medium / close / insert), angle, one action per shot.
- **One native move:** a moment only this medium can do — a line that becomes a wall, a shadow that
  becomes the next set, a freeze that lets an object finish the sentence. Put it at the emotional
  peak. One per film.
- **Ending echo:** how the last image answers the first. Bookend, reveal the scale, or let the
  character do the opening action again with a different meaning.
- Music plan: three sections at most, with the turn marked.

The treatment is allowed to be wrong. It is much cheaper to be wrong here than in 400 lines of
scene code.

## 5. Cut the extras

One gag the viewer can read at thumbnail size beats three they cannot. If a beat needs a caption to
explain it, remove the beat or change the picture. Every shot must answer: what does this shot do that
the previous shot did not?

## 5a. Design the boundary, not just the shots

A cut is a design object, not the absence of one. Before you write shot B, decide what survives from
shot A: a person, a prop, a gaze, a shape, a colour, a camera move. The strongest boundary is one
where the carrier **transforms** — a ring becomes a door handle, a hand becomes a branch, a close-up
becomes the next wide. If nothing survives, the film is a slideshow with better lighting.

When the live studio's `tools/seam_gate.py` is present, `python tools/seam_gate.py --project <p> --auto`
reports, for each boundary, the shared candidate carrier or the lack of one. It is a presence test,
not a taste test: a `PASS` only means something is on both sides, and the tool cannot see whether it
transforms. That judgement is yours. A `WARN` is
either fixed by carrying something across or declared with `"cut_intent": "reverse"` on the incoming
shot when the discontinuity is the point (a hard reverse, a match cut on shape, a deliberate jump).
Declaring it does not make it good; it records that the cut was chosen.

## 6. The variety rule

This is the monetisation rule, not a taste rule. YouTube’s inauthentic-content policy targets
mass-produced, repetitive material, and a series that uses the same structure, opening, set and
transition every time is exactly that shape.

For every new episode, check against the previous **two**:

- [ ] Different opening image. Not “wide establishing shot with a push-in” every time.
- [ ] Different structure. If the last one was a list, this one is a journey or a before/after.
- [ ] Different dominant visual mode. If the last one was mostly kitchen dialogue, this one uses a
      diagram, a close-up, a 3D space or a different set.
- [ ] Different transition signature. Do not use the same flash/dip/freeze pattern every episode.
- [ ] Different ending device. The echo can be a bookend, a reveal or a reversal — rotate them.

Same style is fine; that is the channel. Same template is not.

Keep the one-line `Shape` entry in `docs/LESSONS.md`: date, episode, structure, opening image,
dominant mode, transition signature, ending device. Read the last two before choosing the next.

## 7. Rights and monetisation

- The script is original or properly licensed. Do not paraphrase a creator’s video and call it
  research.
- No real person’s face, voice, logo or signature shot without permission.
- No non-commercial code in the revenue path. `aitrends-2d-studio/THIRD_PARTY.md` is the ledger; if
  it is not there, it does not go in.
- Keep the pipeline local and $0 per video. A new paid API is a business decision, not a technical
  one.
- A human watches the finished film before publishing. Machine checks are not acceptance.

## 8. Hand-off checklist

- [ ] One-sentence film written.
- [ ] Benchmark and “don’t take” written.
- [ ] Three structures considered; one chosen and why.
- [ ] `story/treatment.md` written before shot code.
- [ ] One native move at the peak.
- [ ] Ending echoes the opening.
- [ ] Every cut has a carrier, or a declared `cut_intent` under `--auto` when the discontinuity is
      deliberate.
- [ ] Variety rule checked against the last two episodes.
- [ ] No copied face, voice, logo, shot or non-commercial code.
