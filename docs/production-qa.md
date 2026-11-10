# Production QA checklist

Run this against the contact sheet and the finished video **before** you call a render done. It is a
checklist, not advice: every line is something that has actually gone wrong in this pipeline, or a
rule adapted from the reference kit in `../THIRD_PARTY.md` (marked §2/§5, ClaudeAnimationBase, MIT).

Order matters. Do the cheap visual checks first — rendering is slow, looking is free.

## 1. Does it render at all
- [ ] `node render.mjs --project <p> --sheet --scale 0.5` prints **no** `SHOT ERROR` lines.
- [ ] No `MISSING` shots in the renderer output.
- Common causes we have hit: gradient stops written `[colour, offset]` instead of `[offset, colour]`;
  a constant declared inside a `layer()` callback but returned or used outside it; a name missing from
  the `import { … } from '/engine/core.js'` list; an invented expression, pose, mood or sfx name.

## 2. Character
- [ ] **One** signature marker, identical in every shot. Colour alone is not enough if the style
      theme can recolour it.
- [ ] Outfit colour never changes between shots.
- [ ] Screen direction is consistent — in a two-shot the same character stays on the same side.
- [ ] Proportions match the approved frame. Compare against `story/style-lock/` references.
- [ ] No floating figures: every character sits on the ground line with a contact shadow.
- [ ] A back limb that is behind the torso is **not drawn over it**. (We shipped this bug twice.)
- [ ] Legs read as two legs, not one column.
- [ ] Nobody is frozen: `breathe()` on every standing or sitting figure.
- [ ] Faces act, they never snap: mood changes ramp through the continuous face params (brow,
      eyeWide, mouthCurve); no expression pops between two frames.
- [ ] Contacts: a held thing touches the hand that holds it, a thrown thing leaves from the hand.
      (The detached bag and the lollipop keys were both caught on the sheet, not in code review.)
- [ ] Every move eases in and out; a plain linear lerp reads as mechanical.
- [ ] Big moves anticipate (a small opposite move first) and settle with follow-through; all the
      parts do not start and stop on the same frame.
- [ ] No twinning: both arms do not mirror one angle, two characters do not move in sync; offset
      phases and seeds.
- [ ] Key poses read as stills, pushed far enough to read at phone size. If the pose doesn't read
      on the sheet, the motion will not fix it.

## 3. Light and depth
- [ ] Rim light on every lit figure. Without it, dark figures vanish into dark sets.
- [ ] One key light per shot, and it is visible in frame (lamp, window, sun).
- [ ] Atmosphere present in nearly every shot — dust, rain, god rays, lens streak.
- [ ] Something soft in the foreground on medium shots (glassware, a shoulder, a railing).
- [ ] Moody value structure: no flat white background except a deliberate flash.

## 4. Camera
- [ ] **No static shot.** Every shot has a push, drift, roll, pull-out or shake.
- [ ] Cuts land on phrase boundaries, roughly 0.1–0.2 s early so the picture changes just before the line.
- [ ] 15–25 shots per minute. A 30-second film wants 8–12 shots, not 2.

## 5. Does the picture match the words at that second
- [ ] For each frame, ask: is this what is being *said* right now?
- [ ] Reveals land on their word — check against `timeline/words.json`, not against your memory.
- [ ] Numbers and data appear as they are spoken.
- [ ] Nothing appears before its cause. Props move with whatever holds them.
- [ ] One visual mode per shot. If the body is x-ray, the whole body is x-ray.
- [ ] Every shot has an event: something differs between its first and last frame beyond camera
      drift. A drifting camera over a static scene is not a shot.
- [ ] Write the reads: per shot, list what the viewer must understand, in order. Each read gets
      frames to be found and understood; no two important reads share the same frames.
- [ ] Fast action, held meaning: after the important beat, hold long enough for it to land before
      the next thing starts. A read that flashes by in a few frames is missed.

## 6. Graphics and text
- [ ] Nothing collides with a label, a pill, or the caption zone.
- [ ] Spelling checked on every on-screen word, including names.
- [ ] Captions: 1–3 words per chunk, one highlighted word, readable on a phone.
- [ ] No wall of text. No emoji, clip-art or stock icons.

## 7. Continuity across the film
- [ ] Same set geometry for every shot inside one scene.
- [ ] A character does not stand up between shots without it being shown.
- [ ] Freeze-frames used 1–3 per film at most; 3D shots about one per minute.
- [ ] `python tools/seam_gate.py --project <p> --auto` has no unexplained `WARN`. Every `WARN` is
      either fixed by carrying a person/prop across, declared with `"cut_intent": "reverse"` (or
      `"match"`) on the incoming shot, or waived in one line with a reason (for example: a character
      test with no named cast). A declared or waived cut is a statement, not a fix — check the picture.
- [ ] The default `seam_gate.py` report is unchanged for projects that have not opted into `--auto`;
      a changed default report means the fixed vocabulary drifted.

## 8. Sound
- [ ] Voice is clearly above the music bed.
- [ ] Effects are soft — no harsh ticks or beeps.
- [ ] `mean_volume` roughly −20 to −15 dB, and an audio stream actually exists.
- [ ] Recorded foley used where the sound is a physical object (`audio/foley/`, CC0 Kenney);
      synthesised cues are fine for whooshes and transitions, not for footsteps.

## 9. Machine checks, and what they do not mean
- [ ] `python tools/motion_audit.py <video>` — catches a genuinely dead stretch. It measures
      **change rate**, not liveliness; a bright flat video with popping captions scores higher than a
      dark cinematic one. See `docs/MOTION_BASELINE.md`. Never treat a pass as "this looks alive".
- [ ] `python tools/render_report.py --project <p>` — writes the per-episode record.
- [ ] `python tools/style_lock.py check --project <p>` — refuses to proceed if the character drifted.
- [ ] **A green machine check is not acceptance.** Approval is a human watching the film. Record the
      approver's actual words in the report or lock manifest, not a paraphrase.

## 10. Before publishing
- [ ] Every factual claim checked against a real source and cited in `script.json`.
- [ ] Not framed as an authority on health, legal, financial or political matters.
- [ ] Distinct story, not another instance of the same template — see
      `plugin/skills/make-2d-video/references/directing.md` and the monetisation notes in the
      handover guide.
- [ ] The episode differs from the previous **two** in opening image, structure, dominant visual
      mode, transition signature and ending device. Same style is fine; same shape is not.
- [ ] No real person’s face, voice, logo or signature shot was copied. No footage or character from
      a reference film was reused.
- [ ] Every adapted source is listed in `../THIRD_PARTY.md`, and nothing from a non-commercial source
      is in the revenue path.
- [ ] `story/treatment.md` exists and names the one native move and the ending echo. If it was
      written after the shot code, treat that as a warning: the film was assembled, not directed.

## 11. Readability traps (visual review) — checklist
Automation cannot judge these; eyeball the pulled frames (`tools/review_frames.py`)
and the side-by-side sheets (`tools/sbs_sheet.py`) against a reference.

- [ ] **A swing drawn as one rope that disappears behind the figure reads as a
      HANGING.** Use two ropes to a wide plank with the figure between them; frame
      whose legs clear the arc.
- [ ] **Props or flotsam closer than ~2 m to the lens become huge cut-off blobs**
      when the camera moves. Re-check every near prop after a camera move.
- [ ] **A foreground element cut by the frame edge reads as a "ball"/blob.** A
      foreground prop must be recognisable or removed.
- [ ] **Flags:** red + yellow star/diamond reads as Vietnam's. Use a
      period-correct flag.
- [ ] **Painted signs lit by a side sun go grey-blue and unreadable.** Give the
      sign face an unlit material.
- [ ] **Golden rim light done as an offset outer copy turns every hat into a
      picture frame.** Inner rim only, head/torso only.
- [ ] **Balcony/railing rails at chest height through characters.** Put the lens
      ~2.5 m up so rails cross legs, not torsos.
- [ ] **Flat holds read as freezes in QA (frozen span >= 12 frames).** Every hold
      needs a creeping push-in.
- [ ] **Intentional freezes** (`freeze` in shots.json) must be declared; an
      undeclared freeze is a defect, not a feature.
- [ ] **Aspect mismatch / black / white frames** are measured by
      `tools/review_frames.py` and `tools/frame_qa.py` — treat any flag as FAIL.
