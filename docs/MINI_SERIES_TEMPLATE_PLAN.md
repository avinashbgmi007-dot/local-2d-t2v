# Mini-Series Template Plan — story → season → episodes → ship

**Purpose.** A reusable, fill-in template for turning any public-domain story corpus into a serialized, code-drawn animated mini-series using the local `aitrends-2d-studio` pipeline. It is deliberately format-agnostic: the story layer is swapped per season, the production and decision layers stay fixed.

**Status.** Planning document, 8 Nov 2026. It does not modify the studio. Fields marked `PROPOSED` do not exist yet and depend on the template-interpreter engineering task described in `MINI_SERIES_MARKET_RESEARCH_2026-11-08.md` §4.3.

---

## 0. How to use this document

1. Copy §1 (constants), §2 (season bible) and §3 (episode grid) into `projects/<slug>/story/`.
2. Fill §2 once per season. Fill §3 once per episode.
3. Feed §3 into `beats.py`, then into the `template` + `params` interpreter.
4. Run §6's gate chain unchanged for every episode.
5. §7–§9 define the only human checkpoints. If a step needs a new checkpoint, that is a design regression.

---

## 1. Fixed constants (change only between seasons)

| Constant | Pilot value | Market-aligned value | Reason |
|---|---|---|---|
| Aspect | 9:16 primary | 9:16 primary + 16:9 compilation | Shorts/Reels feed; compilations carry higher RPM |
| Resolution | 1080p | 1080p | 4K is ~8× slower; no measured retention benefit |
| FPS | 24 | 24 | Existing baseline |
| Episode duration | **30–45 s** | **60–75 s** | 60–120 s is the market band; 58–90 s is the 2026 convergence |
| Shots / episode | 8–12 | 15–25 | 15–25 shots/min from `style-bible.md` |
| Words / episode | ~85–125 | ~170–210 | ~2.8 spoken words/second |
| Episodes / season | **7** | 12 | Meta's own social-native microdrama used 7, alternate-day |
| Release cadence | every 2 days | every 2 days | Only verified cadence; also fits batched weekly approval |
| Style | `midnight` | rotate per season | Both shipped `report.json` already use `midnight` |
| Voice | `af_heart` / `am_michael` | per-character fixed | `voice2.py` for dialogue; never change a character's voice mid-season |
| Signature colours | fixed in `cast.js` | fixed | Continuity rule; `style_lock.py` protects it |
| Music | generated, own numpy bed | generated | No licensed track → 100% of revenue into the Creator Pool |
| Captions | on (9:16) | on | Default for vertical |

**Hard rule:** do not exceed 3 minutes. Square/vertical uploads after 15 Oct 2024 up to 3 min are Shorts and are monetisable in the Shorts revenue-sharing model.

---

## 2. Season bible template

```markdown
# Season <N> — <Title>

## Source & rights
- Source text: <name, author/compiler, century>
- Edition used: <public-domain translation + year + URL>
- Rights basis: <public-domain reasoning; e.g. India Copyright Act 1957 s.22, life + 60 years>
- NOT used as source: <modern retellings, comics, TV serials, films — list them explicitly>
- Attribution line shown on screen: <"Adapted from <PD text>, <year> translation">
- Fact-check owner: <name>; source for every claim: <citation>

## One-sentence film
<What the whole season is about, in one sentence.>

## Frame / engine
- Frame story: <the recurring situation that forces each episode to exist>
- Reset mechanism: <what returns the world to its starting state each episode>
- Season payoff: <the one thing revealed in the final episode>
- Cliffhanger device: <the recurring question type>

## Cast (signature colour NEVER changes)
| id | name | voice | signature colour | default pose | default expression |
|----|------|-------|------------------|--------------|--------------------|
| VIKRAM | ... | am_michael | ... | stand | determined |
| VETALA | ... | bm_george | ... | crouch | smirk |

## Sets (anchored to GY and CX)
| set id | description | mood | key light | atmosphere |
|--------|-------------|------|-----------|------------|
| forest_night | ... | midnight | rim | FX.dust |

## Visual variety budget (protects monetisation)
- 12 named archetypes, no archetype used twice in adjacent episodes
- 3–5 hand-written hero shots per film
- Opening image, dominant visual mode, transition signature and ending device must differ from the previous episode
- Distinct storyline per episode — never "another instance of the same template"

## Knowledge payload
- One verifiable fact or unfamiliar detail per episode, stated on screen
- Source for each fact recorded in `story/facts.md`
- No doctrinal claims, no sectarian comparisons, no depiction of a deity in a realistic form

## Music plan
| start | end | mood | intensity |
|-------|-----|------|-----------|
| 0 | ... | mystery | 0.4 |
Valid moods only: mystery, tension, action, wonder, hopeful, sad, triumph, playful, calm, dark, epic
```

---

## 3. Episode grid template

Fill one row per episode before any code is written.

| ep | logline | knowledge fact + source | set | beats (3–5) | cliffhanger | archetypes used | hero shot? |
|----|---------|-------------------------|-----|-------------|-------------|-----------------|------------|
| 01 | ... | ... | forest_night | ... | ... | establish, two-shot, bigFace | yes (1) |

**Per-episode script template** (`script.txt`, one line per cut, not per sentence):

```
<HOOK: a question or contradiction, spoken in the first 3–5 s>
<context card line: names the obscure source in one short clause>
<beat 1 — what the picture changes on>
<beat 2>
<beat 3>
<one surprising fact, literally illustrated>
<unresolved question / riddle>
<"Part N" end-card line — do not resolve>
```

Target ~2.8 words/second. Keep the narration intact once the voiceover is generated — never rewrite, add, drop or reorder spoken words.

---

## 4. `shots.json` contract

**Existing fields** (from `beats.py` and the engine): `id, start, end, line, scene, set, bars, in, sfx, amb, captions, grade, notes, acting, cut_intent`, plus a top-level `music` list.

**`PROPOSED` fields** (require `scenes/templates.js`; `engine/player.js:74` already spreads `shot.params` into `info`):

```json
{
  "id": "s001",
  "start": 0.00,
  "end": 4.20,
  "line": "The king lifted the corpse onto his shoulder.",
  "scene": "establish the night forest, two figures on the ground line",
  "set": "forest_night",
  "template": "establish-push",
  "params": {
    "who": ["VIKRAM", "VETALA"],
    "pose": ["stand", "crouch"],
    "expr": ["determined", "smirk"],
    "gaze": "down",
    "push": [1.0, 1.06],
    "drift_x": -24,
    "gesture_on": 2.10,
    "rim": true,
    "atmos": "dust"
  },
  "bars": 2,
  "in": { "type": "cut" },
  "sfx": ["footstep", "wind"],
  "amb": ["night"],
  "grade": "midnight",
  "cut_intent": "establish",
  "notes": ""
}
```

**Template registry (12 named archetypes, from `style-bible.md` proportions):**
`establish-push`, `medium-two-shot`, `over-shoulder`, `giant-face`, `insert-object`, `blueprint-diagram`, `lowpoly-3d`, `pull-out-bookend`, `freeze-frame`, `title-card`, `end-card`, `transition-whip`.

**Slot vocabulary is closed** — validate against the engine enums before writing:
- 27 poses, 18 expressions, 8 base moods, 5 styles (`dusk, midnight, golden, neon, storybook`)
- 11 music moods, ~33 sfx names, 5 transition types actually used in `shots.json`
- No `Math.random()` / `Date.now()`; use `rng(seed)`
- Gradient stops are `[offset, colour]`, never `[colour, offset]`
- Every lit figure needs `rim`; every shot needs a camera move; nearly every shot needs atmosphere

**Quota rule:** templates may cover ~70–80% of shots. The remaining 3–5 hero shots stay hand-written. A small, named library protects against YouTube's "mass-produced, generic, repetitive" ineligibility rule.

---

## 5. Worked example — Season 1, Episode 01 (Vetala Panchavimshati)

| Field | Value |
|---|---|
| Title | "The King and the Question" |
| Duration | 45 s (pilot) / ~125 words |
| Frame | Vikram must carry the Vetala in silence; a tale is told; a riddle is posed |
| Hook (0–4 s) | "A king was asked to carry a corpse through a forest — and told not to speak." |
| Knowledge fact | The Vetala cycle is a 25-tale frame narrative; source: Somadeva / *Kathasaritsagara* and the *Vetala Panchavimshati* recension, PD 19th-c. translation |
| Beats | 1 arrival / 2 the load / 3 first tale opens / 4 the riddle / 5 silence breaks |
| Cliffhanger | "Which answer keeps him silent?" → Part 2 |
| Archetypes | `establish-push`, `medium-two-shot`, `giant-face`, `insert-object`, `end-card` |
| Hero shot | The first lift: hand-written, with anticipation and follow-through |
| Sets | `forest_night` (reusable all season), `tale_clearing` (episode-specific) |
| Cast | VIKRAM (`am_michael`, fixed colour), VETALA (`bm_george`, fixed colour) |
| Music | `mystery` 0–30 s, `tension` 30–45 s |
| Sfx | `footstep`, `wind`, `whoosh` |
| End card | "Part 2 — the answer" + series title + one-line source attribution |

---

## 6. Production gate chain (unchanged every episode)

Set up once per shell (Windows / Git Bash):

```bash
STUDIO=~/video-studio/aitrends-2d-studio
FH=~/video-studio/faceless-shorts
PY=~/.faceless-shorts/venv/Scripts/python.exe
cd "$STUDIO"
```

> As of 8 Nov 2026 the `~/video-studio` relocation in guide §2 was **never done**; the kits still live at
> `E:\Local_Mis_WS\_yt_stickman\aitrends-2d-studio` and `E:\Local_Mis_WS\_yt_a6zA\fs\faceless-shorts`.
> Either perform the copy or point `STUDIO`/`FH` at those paths. Using bare system Python causes
> `doctor.py` to report numpy / scipy / faster-whisper as MISSING.

| # | Gate | Command | Pass condition |
|---|------|---------|----------------|
| 0 | Environment | `python tools/verify_kit.py` · `python tools/doctor.py` | "29/29 files verified." · every line OK |
| 1 | **Commit headroom** | PowerShell `Get-CimInstance Win32_OperatingSystem` free virtual memory | ≥6 GB; local LLM server **stopped** |
| 2 | Voice | `"$PY" "$FH/scripts/voice2.py" <vo dir>` | `narration.wav`, `lines.json`, `script.txt` |
| 3 | Project | `"$PY" tools/new_project.py --name <slug> --voice ... --script ... --aspect 9:16 --resolution 1080p --title ...` | project created |
| 4 | Alignment | `"$PY" tools/transcribe.py --project projects/<slug> --script ... --lang en --model small` | **≥90%** |
| 5 | Beats | `"$PY" tools/beats.py --project projects/<slug>` | draft `story/shots.json` |
| 6 | Directing | LLM writes `cast.js`, `sets/*.js`, `shots/*.js`; or `template`+`params` data | no invented names |
| 7 | **Contact sheet** | `node render.mjs --project projects/<slug> --sheet --scale 0.5` | zero `SHOT ERROR`; **human opens `sheet_01.png`** |
| 8 | Cut carrier | `"$PY" tools/seam_gate.py --project projects/<slug> --auto` | no WARN, or declared `cut_intent` |
| 9 | Render | `node render.mjs --project projects/<slug>` | must exit non-zero on error (**fix required today**) |
| 10 | Mix | `"$PY" audio/mix.py --project projects/<slug>` | audio stream present, −14 LUFS |
| 11 | Dead frame | `"$PY" tools/motion_audit.py projects/<slug>/out/*.mp4` | exit 0 |
| 12 | Drift | `"$PY" tools/style_lock.py check --project <slug>` | byte-for-byte match; re-baseline once after templates land |
| 13 | Audit record | `"$PY" tools/render_report.py --project <slug>` | `approved_by` populated |
| 14 | **Human approval** | watch the MP4 | recorded in `report.json` — **technical checks are not acceptance** |
| 15 | Verify | `ffmpeg -i <mp4>` + `volumedetect` | duration correct, audio present, mean ≈ −20 to −15 dB |
| 16 | Publish | `videos.insert` with `status.publishAt`, `privacyStatus=private` until approved | scheduled, not immediate public |
| 17 | Retro | append shape line + 3-line retro to `docs/LESSONS.md` | one rule change per episode |

---

## 7. Automation architecture

```
[ONE-TIME]  template registry + params interpreter
            hard-fail render exit code
            LLM load/unload orchestration + headroom check
            style_lock baseline + approved_by
            YouTube OAuth + publishAt scheduler + private staging
                        |
[WEEKLY BATCH]  agent drafts N episodes from a fixed story grid
            -> voice / timing / beats / templates / render / mix / gates (unattended)
            -> contact sheets + N preview MP4s + one annotated review pack
                        |
[ONE HUMAN SESSION, 15–45 min]  watch the pack, approve / reject,
            record approval, adjust params, decide topic for next batch
                        |
[AUTOMATIC]  scheduled publish, analytics capture, retro generated
                        |
[MONTHLY, 30–60 min]  metrics review, template additions,
            lock re-baseline, quota/OAuth/policy audit
```

**Only three recurring decision points:** season/topic approval, weekly batch approval, monthly metrics/policy check. Escalations (a failed gate, a fact dispute, a policy change) are the fourth, event-driven case.

**Kill switches:** any `SHOT ERROR` > 0, alignment < 90%, a `style_lock` mismatch, a failed motion audit, a copyright claim on a >1 min Short, or an unverified factual claim must stop the batch before publish.

---

## 8. Monetisation ladder and review cadence

| Stage | Gate | Review |
|---|---|---|
| Fan funding | 500 subs + 3,000 h/12 mo or 3M Shorts views/90 d | enable early |
| Shorts ad share | YPP + **10M qualified Shorts views / 90 d from 1 Feb 2027** | monthly |
| Long-form compilations | recut 7–12 episodes into 8–12 min videos; RPM ~$2–6/1K vs $0.01–$0.20 for Shorts | per season |
| Sponsorship / licensing | once retention is demonstrated | per quarter |
| Direct guides / reading lists | no platform gate | per season |

**Go / no-go for the pilot season (decide after 7 episodes):**
- Median completion rate and 3-second hold trend (measure in YouTube Analytics; do not guess)
- Episodes shipped per week vs the 15–45 min/week human-time target
- Zero published episodes with errors or unapproved `report.json`
- At least one distinct storyline per episode, verified against `production-qa.md §10`
- No copyright or sensitivity incident
- If completion stalls or human time exceeds 60 min/week, stop and fix the template layer before Season 2

---

## 9. Risks and standing rules

1. **No daily reading or writing** — the engineered state must deliver a single batched review pack. If a daily check appears, the automation is incomplete.
2. **Zero human decisions is not a goal** — `report.json` and `production-qa.md §9` mandate a human watching the film; YouTube's inauthentic-content policy penalises the repetitive output that zero-touch volume produces.
3. **Revenue is a hypothesis** — no verified solo-creator profit data exists. Validate with the bounded pilot. Do not scale on projection.
4. **Facts are a compliance measure** — every on-screen claim needs a recorded source. The pipeline will render a wrong fact with total confidence.
5. **Public-domain discipline** — adapt a PD source text only; never script from a modern retelling; keep `THIRD_PARTY.md` provenance current.
6. **Never run the local LLM and the render together** — ≥6 GB commit headroom, unload → render → reload.
7. **Protected paths stay untouched** — `engine/`, `audio/sfx.py`, `audio/mix.py`, `render.mjs`. Any change to them is a deliberate, recorded decision, not a convenience.
8. **Templates stay small and named** — 12 archetypes, 3–5 hero shots per film, distinct storylines per episode.
