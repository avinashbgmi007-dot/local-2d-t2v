# Story Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `generate.py --fresh` produce a film whose story is about its own concept, whose cuts carry a shared subject, and whose shape differs per episode — without touching the engine or re-rendering any approved project.

**Architecture:** Three additive layers inside `tools/fresh/`. (1) `story_schema.py` closes the story-JSON contract against the *actual* capabilities of `director.py`, the rigs and `seam_gate.py`, so a bad story fails before it renders. (2) `shapes.py` holds a small library of distinct dramatic shapes, each a beat sequence with its own shot-size skeleton, hold profile and continuity carriers. (3) `story.py` stops authoring one hard-coded arc and instead picks a shape by seed and fills it from the concept. `generate.py` gains one fatal pre-flight call for `--fresh`, report-only for `--story` unless `--strict` — the same philosophy already used for `seam_gate` and `style_lock`.

**Tech Stack:** Python 3 stdlib only (`re`, `json`, `hashlib`, `unittest`, `tempfile`). No new dependency. No JavaScript change. No `npm`/`pip` install.

**Spec:** this document. Measured evidence below is the spec's factual basis; every number was produced by a command in this repo on 2026-11-12.

## Global Constraints

- **Protected paths are untouched:** `engine/`, `audio/sfx.py`, `audio/mix.py`, `render.mjs` (ADR 0001). No task in this plan edits them.
- **No approved project is re-rendered or edited.** `projects/cine_release/` is owner-approved (`build/report.json`, `approved_at 2026-11-10T17:39:36`, video sha256 `dbe9748…8681`). Its style lock is byte-pinned. Nothing here writes to it.
- **Style locks are per-project:** `tools/style_lock.py:44` resolves `<project>/story/style-lock.json`. Changing `tools/fresh/` cannot invalidate `cine_release`'s lock unless that project is re-rendered. This is the mechanism behind "lock-safe", not an assumption.
- **No commit without the owner asking in that turn.** Every "Commit" step below is a *proposal*; the executor stages and shows the diff, and commits only on the owner's explicit word.
- **Never mass-patch files by script.** All edits are individual `Edit` calls.
- **Line endings are MIXED in this repo — measured, not assumed.** CRLF: `tools/generate.py` (213/213), `tools/selftest_gates.py` (1121/1121), `tools/director.py` (1108/1108). LF: `tools/fresh/*.py`, `docs/*.md`, `THIRD_PARTY.md`. **Preserve each file's own convention.** New files in `tools/fresh/` and `docs/` use LF. After editing `selftest_gates.py` or `generate.py`, verify `CR count == LF count`; if the inserted lines came out LF, normalize that file back to CRLF before showing the diff.
- **Method-only borrows are clean-room.** No prose, code, asset, character name or quotation from any external repo enters this tree. Re-express the idea, then record it in `THIRD_PARTY.md`.
- **Vocabulary values are copied verbatim from source**, never invented. Each constant below carries its `file:line` provenance.
- **Runtime target:** 15 s, 9:16, 1080p, 24 fps, `chars: "inkbean"` — unchanged from the current fresh output.
- **Line cap: 8 words.** Hold budget: **≤ 5.0 s** per film. Both are test assertions, not guidance.

---

## Measured evidence (the spec's factual basis)

Command: `python tools/seam_gate.py --project projects/<name> --auto`

| film | source | shots | boundaries | **dead cuts** | owner-approved |
|---|---|---|---|---|---|
| `cine_release` | hand (`DEMO_STORY`) | 8 | 7 | **0** | **yes** |
| `proposal_day` | `--fresh` | 6 | 5 | **2** | no |
| `fresh_e2e` | `--fresh` | 6 | 5 | **2** | no |
| `micro_ai` | hand (`examples/ai-trends-story.json`) | 6 | 5 | **2** | no |
| `micro_detective` | hand (`examples/detective-story.json`) | 6 | 5 | **2** | no |

Every dead cut is an **insert boundary**. `cine_release` has zero because it declares `"cut_intent": "eyeline"` on both sides (`tools/director.py:912,919`). The insert renderers (`tools/director.py:592-667`) draw inline `g.fillRect` shapes — no cast member, no `PROP_FUNCS` helper — so nothing can carry across them unless the intent is declared.

Command: expression-slot audit against `chars/acting.js` `PRESETS`

| film | expr slots | **invalid → silently neutral** |
|---|---|---|
| `proposal_day` / `fresh_e2e` / `micro_ai` | 9 | **6 (67%)** |
| `micro_detective` | 9 | 2 |
| `cine_release` | 14 | **5 (36%)** |
| whole repo | — | **87** (`smirk`×34, `shocked`×20, `happy`×16, `sleepy`×11, `excited`×6) |

Mechanism: `tools/director.py:723-724` — when `INKBEAN` is true the face comes from `faceAt(...)`, and `faceAt` does `PRESETS[a] || PRESETS.neutral` (`tools/director.py:81`). **An unknown expression name is not an error; it is a neutral face.** In the fresh arc the three most expressive beats — s001 `excited`, s002 `smirk`, s005 `shocked` — all render neutral. The reaction shot carries no reaction.

Line comparison, `projects/*/story/shots.json`:

- `proposal_day` and `fresh_e2e` share **5 of 6 lines verbatim**; only s001's title differs.
- `micro_ai` shares **3 of 6** with them.
- Cause: `tools/fresh/story.py:67-114` hard-codes one arc. This is the pattern YouTube's *inauthentic content* policy demonetises ("generic or unoriginal templates giving the impression of mass production").

Rhythm: `cine_release` = 10.775 s / 8 shots = **1.35 s/shot**, holds total **4.75 s**. `proposal_day` = 15.277 s / 6 shots = **2.55 s/shot**, holds total **6.6 s**. The fresh films cut ~1.9× slower than the only approved film.

Identity: `projects/proposal_day/series.json` says `base_color #71c49e`; `projects/proposal_day/scenes/cast.js` says `#39d930`. Cause: `tools/fresh/series.py:26` seeds from the **episode concept**, `tools/fresh/story.py:24` seeds from the **series_id**. The "series bible" therefore changes every episode, and nothing reads it anyway.

Coverage: `tools/selftest_gates.py:50-63` imports all six `fresh.*` modules; **no test uses any of them**. The fresh pipeline has zero test coverage.

### External method sources — Tier-1 verified 2026-11-12

| repo | licence | stars | pushed | verdict |
|---|---|---|---|---|
| `oleo17/story-to-script-en` | MIT, `Copyright (c) 2026 story-to-script contributors`, **no NOTICE**, no assets | 2 | 2026-10-25 | **take** |
| `jtydhr88/screenwriting-skills` | MIT, `Copyright (c) 2026 Terry Jia`, **plus a 3,923 B NOTICE** | 2043 | 2026-10-03 | **take, original layer only** |

**Correction to my earlier recommendation:** I named `jtydhr88/screenwriting-skills` without knowing about its NOTICE. That NOTICE states *"LICENSE cannot grant rights in material that belongs to someone else"* and carves out its `reference*.md` files, which are quotation corpora from 47 books and 23 volumes of published scripts — including HBO *Succession* shooting scripts (Faber 2023) with verbatim lines and the characters Roman/Shiv/Kendall/Logan. **`reference*.md` is off limits entirely.** The MIT-covered original layer (numbered principles, checklists, workflows) is expressly granted for commercial use. Neither repo is CC BY, so a clean-room method borrow needs **no on-screen credit**.

Method taken from `oleo17/story-to-script-en` (verbatim rules, re-expressed as numbers in Task 2):
- *"Budget before craft."* Event grain = "one visible change of state"; `T_max = G × 20`, floor 15 s.
- Tier S (15–120 s): 1–6 grains, 1–3 scenes, 5–15 shots. `Script words ≈ T × 2.2`.
- *"A 3-second line at 2.5 wps is 7–8 words."* Audit field: *"Over-length lines: n (> 8 words for short-form)"*.
- *"the first 2 seconds are not part of the story — they are the price of admission."*
- *"the extra 15 seconds are a new event grain, not slower delivery."*
- **Not present:** any episode-distinctness engine. Do not claim it has one.

Method taken from `jtydhr88/screenwriting-skills` (original layer only):
- 起/承/转/合 proportion: 承 ≈ two-thirds, 合 short and immediately after the turn.
- Crisis must be a **true dilemma**, not a setback.
- *"变化就有戏"* — a beat needs a visible change; priority: character-driven > craft > accident > external force.
- Container episode: a fixed running order replaces act breaks; one core question per episode.

**Density divergence, resolved in favour of the owner's own film:** `oleo17` defaults to 3.5 s/shot. `cine_release` measures 1.35 s/shot. This plan uses **his** number, not the repo's.

---

## File Structure

| file | responsibility | action |
|---|---|---|
| `tools/fresh/story_schema.py` | the story-JSON contract: closed vocabularies + continuity + budget. Returns `(errors, warnings)`. Knows nothing about shapes or concepts. | **create** |
| `tools/fresh/shapes.py` | the shape library: 4 dramatic shapes, each a beat sequence. Also `subject_of()` and `insert_for()`. Knows nothing about validation. | **create** |
| `tools/fresh/story.py` | picks a shape by seed, fills it from the concept, emits the story dict. | **rewrite** `concept_to_story` |
| `tools/fresh/series.py` | one-line seed fix so the bible is series-stable. | **modify** :26 |
| `tools/story_check.py` | CLI wrapper: `--story <json>` → prints errors/warnings, exit 1 on error, 0 otherwise. | **create** |
| `tools/generate.py` | one pre-flight call after the story path is resolved. | **modify** ~:96 |
| `tools/selftest_gates.py` | new `FreshStory*Tests` classes; the dead `fresh.*` imports become used. | **modify** |
| `THIRD_PARTY.md` | two new ledger rows + the NOTICE carve-out. | **modify** |
| `docs/LESSONS.md` | the silent-neutral fallback lesson. | **modify** |
| `docs/adr/0004-story-contract.md` | why the contract is closed, and the LLM-authoring seam. | **create** |

**Not touched:** `engine/*`, `chars/*`, `audio/*`, `render.mjs`, `tools/director.py`, `tools/narrate.py`, `tools/seam_gate.py`, `projects/cine_release/*`, `examples/*.json`.

---

## Task 1: The story contract

**Files:**
- Create: `tools/fresh/story_schema.py`
- Test: `tools/selftest_gates.py` (new class `FreshStorySchemaTests`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `validate_story(d) -> (errors: list[str], warnings: list[str])`; module constants `POSES`, `EXPR_INKBEAN`, `EXPR_STICK`, `STYLES`, `MOODS`, `SETS`, `PROPS`, `INSERT_KINDS`, `SFX`, `DECLARED_INTENT`, `SIZES`, `MAX_LINE_WORDS = 8`, `MAX_HOLD_BUDGET = 5.0`, `MAX_SHOT_DENSITY = 2.0`.

- [ ] **Step 1: Write the failing tests**

Append to `tools/selftest_gates.py`, before the `if __name__` block:

```python
class FreshStorySchemaTests(unittest.TestCase):
    """The story contract. Skipped only if the fresh package is absent."""

    def setUp(self):
        if _fresh_story_schema is None:
            self.skipTest("fresh.story_schema not importable")
        self.V = _fresh_story_schema

    def _minimal(self, **over):
        d = {
            "title": "T", "aspect": "9:16", "resolution": "1080p", "fps": 24,
            "style": "midnight", "set": "room", "chars": "inkbean",
            "cast": {"MAX": {"color": "#c2553d", "top": "trench",
                             "legs": "#2a2433", "head": "none"}},
            "shots": [
                {"id": "s001", "size": "wide", "line": "Three in the morning.",
                 "hold": 0.5, "who": "MAX", "pose": "stand", "expr": "neutral",
                 "in": {"type": "fade", "dur": 0.5}},
                {"id": "s002", "size": "close", "line": "Don't move.",
                 "hold": 0.3, "who": "MAX", "pose": "stand", "expr": "worried",
                 "in": {"type": "cut"}},
            ],
            "music": [],
        }
        d.update(over)
        return d

    def test_minimal_story_is_clean(self):
        errs, warns = self.V.validate_story(self._minimal())
        self.assertEqual(errs, [])

    def test_unknown_expression_is_an_error_not_a_warning(self):
        d = self._minimal()
        d["shots"][1]["expr"] = "smirk"          # not in PRESETS -> renders neutral
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("smirk" in e for e in errs), errs)

    def test_stick_rig_uses_the_other_expression_vocabulary(self):
        d = self._minimal(chars="stick")
        d["shots"][1]["expr"] = "worried"        # valid for inkbean, NOT for rig2d
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("worried" in e for e in errs), errs)
        d["shots"][1]["expr"] = "scared"         # valid rig2d EXPR
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_unimplemented_prop_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["prop"] = {"kind": "sword"}   # director.py:1024 -> magenta box
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("sword" in e for e in errs), errs)

    def test_walk_pose_without_walk_spec_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["pose"] = "walk"              # director.py:1019 -> stands still
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("walk" in e for e in errs), errs)
        d["shots"][0]["walk"] = {"from": 0.13, "to": 0.40}
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_misspelled_param_key_is_an_error(self):
        d = self._minimal()
        d["shots"][1]["exprto"] = "worried"         # silently dropped by PARAM_KEYS
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("exprto" in e for e in errs), errs)

    def test_insert_without_intent_is_a_dead_cut(self):
        d = self._minimal()
        d["shots"].insert(1, {"id": "s00X", "size": "insert", "line": "",
                              "hold": 0.75, "insertKind": "phone",
                              "in": {"type": "cut"}})
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("dead cut" in e for e in errs), errs)

    def test_insert_with_eyeline_intent_is_clean(self):
        d = self._minimal()
        d["shots"].insert(1, {"id": "s00X", "size": "insert", "line": "",
                              "hold": 0.75, "insertKind": "phone",
                              "cut_intent": "eyeline", "in": {"type": "cut"}})
        d["shots"][2]["cut_intent"] = "eyeline"
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_over_length_line_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["line"] = "one two three four five six seven eight nine"
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("9 words" in e for e in errs), errs)

    def test_hold_budget_over_ceiling_is_a_warning(self):
        d = self._minimal()
        for s in d["shots"]:
            s["hold"] = 3.0
        errs, warns = self.V.validate_story(d)
        self.assertEqual(errs, [])
        self.assertTrue(any("hold budget" in w for w in warns), warns)

    def test_unknown_cast_member_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["who"] = "NOBODY"
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("NOBODY" in e for e in errs), errs)

    def test_vocabularies_match_source(self):
        """Drift alarm: the closed sets must equal what the engine actually exports."""
        import re
        def js_keys(path, name):
            s = open(os.path.join(STUDIO, path), encoding="utf-8").read()
            i = s.index("export const " + name)
            blk = s[i:s.index("\n};", i)]
            return set(re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9_]*)\s*:", blk, re.M))
        self.assertEqual(self.V.POSES, js_keys("engine/rig2d.js", "POSES"))
        self.assertEqual(self.V.EXPR_STICK, js_keys("engine/rig2d.js", "EXPR"))
        s = open(os.path.join(STUDIO, "chars/acting.js"), encoding="utf-8").read()
        i = s.index("PRESETS")
        blk = s[i:i + 4000]
        self.assertEqual(self.V.EXPR_INKBEAN,
                         set(re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9_]*)\s*:", blk, re.M)))
        self.assertEqual(self.V.STYLES, js_keys("engine/styles.js", "STYLES"))
```

Also add the import to the existing `try` block at `tools/selftest_gates.py:50-63`:

```python
    import fresh.story_schema as _fresh_story_schema  # noqa: E402
```

and `_fresh_story_schema = None` to its `except ImportError` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python tools/selftest_gates.py FreshStorySchemaTests -v`
Expected: every test ERRORs at `setUp` with `fresh.story_schema not importable` → reported as SKIP, or `AttributeError` if the import line was added but the module does not exist. Either way the class does not pass. Confirm the module is genuinely absent: `ls tools/fresh/story_schema.py` → No such file.

- [ ] **Step 3: Write the implementation**

Create `tools/fresh/story_schema.py`:

```python
"""fresh.story_schema - the story-JSON contract, closed against real source.

director.py accepts a superset of fields and silently ignores what it does not
know: an unimplemented prop renders a magenta box (director.py:1024), an
unknown expression renders a NEUTRAL face (director.py:81), a misspelled param
key vanishes through the PARAM_KEYS filter (director.py:1028). None of those is
an error at render time. This module makes them errors before rendering.

Vocabularies are copied from source, not invented. FreshStorySchemaTests
.test_vocabularies_match_source is the drift alarm.
"""
import re

# engine/rig2d.js:8 POSES
POSES = frozenset("""stand relaxed talk explain point pointUp wave cheer handsOnHead
crossArms think shrug holdFront phone reach sad facepalm ready crouch sit sitBack
kneel lie dive kick jump fall""".split())

# chars/acting.js PRESETS -- the inkbean face vocabulary (director.py:724 faceAt)
EXPR_INKBEAN = frozenset("""neutral listening curious worried hurt angry surprised
relieved hopeful tired ashamed determined brow""".split())

# engine/rig2d.js:78 EXPR -- the stick face vocabulary (director.py:720 exprAt)
EXPR_STICK = frozenset("neutral smile scared angry cry thinking".split())

# engine/styles.js:20 STYLES
STYLES = frozenset("dusk midnight golden neon storybook".split())

# engine/styles.js:8-15 mood keys
MOODS = frozenset("""day golden dusk night storm interiorWarm interiorCool void""".split())

SETS = frozenset("room kitchen outdoor".split())          # director.py:1059
PROPS = frozenset("mug book phone".split())               # director.py:1024
INSERT_KINDS = frozenset("card screen phone document photo".split())  # director.py:592-667
SIZES = frozenset("wide med close insert".split())        # director.py:1005
DECLARED_INTENT = frozenset("reverse match intentional declared eyeline".split())  # seam_gate.py:63

# audio/sfx.py --list
SFX = frozenset("""whoosh swish impact hit riser slowmo freeze tick clock heartbeat
pop blip counter ding shimmer stinger footstep kick whistle carpass phonebuzz
phonering cheer applause murmur rain thunder wind roomtone city hum powerup
glitch flash buzz""".split())

# director.py:868-875 PARAM_KEYS, plus the record-level keys copied at :1008
# and the timing/identity keys consumed at :1000-1007.
SHOT_KEYS = frozenset("""id size line hold dur start end who who2 who3 x x2 x3 y
pose pose2 pose3 expr exprTo expr2 exprTo2 expr3 exprTo3 at atWord look look2 look3
facing facing2 facing3 scale scale2 scale3 talk2 talk3 bg camZ0 camZ1 camX0 camX1
camY0 camY1 gesture gesture2 walk prop freeze set insertKind in sfx amb scene
acting notes cut_intent""".split())

STORY_KEYS = frozenset("""title aspect resolution fps style set chars cast shots
music fadeIn fadeOut""".split())

MAX_LINE_WORDS = 8       # oleo17/story-to-script-en: "> 8 words for short-form"
MAX_HOLD_BUDGET = 5.0    # cine_release measures 4.75 s
MAX_SHOT_DENSITY = 2.0   # cine_release measures 1.35 s/shot; 2.0 is the slow ceiling

_EXPR_KEYS = ("expr", "exprTo", "expr2", "exprTo2", "expr3", "exprTo3")
_POSE_KEYS = ("pose", "pose2", "pose3")
_WHO_KEYS = ("who", "who2", "who3")


def _carriers(shot):
    """What this shot puts on screen that a neighbour could also put on screen.

    Mirrors seam_gate's model at story level: a named cast member or a held prop.
    An insert draws neither (director.py:592-667), so it carries nothing.
    """
    out = set()
    for k in _WHO_KEYS:
        if shot.get(k):
            out.add(str(shot[k]).lower())
    pr = shot.get("prop")
    if isinstance(pr, dict) and pr.get("kind"):
        out.add("prop:" + str(pr["kind"]))
    return out


def validate_story(d):
    """Return (errors, warnings). Errors block a --fresh film; warnings inform."""
    e, w = [], []
    if not isinstance(d, dict):
        return ["story: must be an object"], []
    for k in d:
        if k not in STORY_KEYS:
            e.append("story: unknown key '%s'" % k)

    shots = d.get("shots")
    if not isinstance(shots, list) or not shots:
        return e + ["story: 'shots' must be a non-empty list"], w
    cast = d.get("cast")
    if not isinstance(cast, dict) or not cast:
        e.append("story: 'cast' must be a non-empty object")
        cast = {}

    chars = d.get("chars", "inkbean")
    expr_vocab = EXPR_STICK if chars == "stick" else EXPR_INKBEAN
    if chars not in ("inkbean", "stick"):
        e.append("story: chars=%r must be 'inkbean' or 'stick'" % chars)
    if d.get("style", "midnight") not in STYLES:
        e.append("story: style=%r not in engine/styles.js STYLES" % d.get("style"))
    if d.get("set", "room") not in SETS:
        e.append("story: set=%r is not implemented -> falls back to room" % d.get("set"))
    if d.get("aspect", "9:16") not in ("9:16", "16:9", "1:1"):
        e.append("story: aspect=%r unsupported" % d.get("aspect"))

    hold_total = 0.0
    seen = set()
    for i, s in enumerate(shots):
        where = "shots[%d]" % i
        if not isinstance(s, dict):
            e.append("%s: must be an object" % where)
            continue
        sid = s.get("id")
        if not sid:
            e.append("%s: 'id' is required" % where)
        elif sid in seen:
            e.append("%s: duplicate id '%s'" % (where, sid))
        else:
            seen.add(sid)
        where = "%s(%s)" % (where, sid or "?")

        for k in s:
            if k not in SHOT_KEYS:
                e.append("%s: unknown key '%s' (director.py drops it silently)" % (where, k))
        if s.get("size", "med") not in SIZES:
            e.append("%s: size=%r not in %s" % (where, s.get("size"), sorted(SIZES)))
        if s.get("set") and s["set"] not in SETS:
            e.append("%s: set=%r is not implemented" % (where, s["set"]))
        if s.get("bg") and s["bg"] not in MOODS:
            e.append("%s: bg=%r not an engine mood" % (where, s["bg"]))

        for k in _EXPR_KEYS:
            if s.get(k) and s[k] not in expr_vocab:
                e.append("%s: %s=%r not in the %s face vocabulary -> renders NEUTRAL"
                         % (where, k, s[k], chars))
        for k in _POSE_KEYS:
            if s.get(k) and s[k] not in POSES:
                e.append("%s: %s=%r not in rig2d POSES" % (where, k, s[k]))
        for k in _WHO_KEYS:
            if s.get(k) and s[k] not in cast:
                e.append("%s: %s=%r is not in cast" % (where, k, s[k]))
        if str(s.get("pose", "")).lower() in ("walk", "run") and not isinstance(s.get("walk"), dict):
            e.append("%s: pose=%r without a 'walk' spec -> the figure stands still"
                     % (where, s["pose"]))

        pr = s.get("prop")
        if isinstance(pr, dict) and pr.get("kind") not in (None, *PROPS):
            e.append("%s: prop kind %r is not implemented -> a magenta box renders"
                     % (where, pr.get("kind")))
        if s.get("insertKind") and s["insertKind"] not in INSERT_KINDS:
            e.append("%s: insertKind=%r not implemented" % (where, s["insertKind"]))
        if s.get("size") == "insert" and not s.get("insertKind"):
            w.append("%s: insert with no insertKind -> the legacy fly renders" % where)

        for cue in s.get("sfx") or []:
            if isinstance(cue, dict) and cue.get("name") not in SFX:
                e.append("%s: sfx name %r not in audio/sfx.py" % (where, cue.get("name")))
        amb = s.get("amb")
        if isinstance(amb, dict) and amb.get("name") not in SFX:
            e.append("%s: amb name %r not in audio/sfx.py" % (where, amb.get("name")))

        line = s.get("line") or ""
        n = len(line.split())
        if n > MAX_LINE_WORDS:
            e.append("%s: line is %d words (cap %d)" % (where, n, MAX_LINE_WORDS))
        hold_total += float(s.get("hold", 0.42))

    # Continuity: the story-level pre-flight for seam_gate. A cut needs a shared
    # subject or a declared intent; an insert has no subject, so it needs intent.
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        shared = _carriers(a) & _carriers(b)
        intent = b.get("cut_intent")
        if not shared and intent not in DECLARED_INTENT:
            e.append("dead cut %s->%s: nothing carried and no cut_intent declared"
                     % (a.get("id"), b.get("id")))

    if hold_total > MAX_HOLD_BUDGET:
        w.append("hold budget %.2fs exceeds %.1fs (cine_release: 4.75s)"
                 % (hold_total, MAX_HOLD_BUDGET))
    density = (hold_total + sum(len((s.get("line") or "").split()) for s in shots
                                if isinstance(s, dict)) / 2.0) / len(shots)
    if density > MAX_SHOT_DENSITY:
        w.append("estimated %.2fs/shot exceeds %.1fs (cine_release: 1.35s)"
                 % (density, MAX_SHOT_DENSITY))
    if not d.get("music"):
        w.append("music is empty -> audio/mix.py:57 falls back to MUSIC.default_plan")
    return e, w
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python tools/selftest_gates.py FreshStorySchemaTests -v`
Expected: 12 tests, all PASS (or SKIP only if `fresh` is genuinely absent — it is present, so they must run).

- [ ] **Step 5: Run the whole suite for regressions**

Run: `python tools/selftest_gates.py`
Expected: the pre-existing classes still pass. Record the total count before and after; the delta must equal exactly the number of tests added.

- [ ] **Step 6: Show the diff and propose the commit**

```bash
git add tools/fresh/story_schema.py tools/selftest_gates.py
git diff --cached --stat
```
Commit message (only on the owner's word): `feat(fresh): close the story-JSON contract against engine source`

---

## Task 2: The shape library

**Files:**
- Create: `tools/fresh/shapes.py`
- Test: `tools/selftest_gates.py` (new class `FreshShapesTests`)

**Interfaces:**
- Consumes: `story_schema.MAX_LINE_WORDS`, `SETS`, `PROPS`, `INSERT_KINDS`, `EXPR_INKBEAN` (Task 1).
- Produces: `SHAPES: dict[str, dict]` with keys `mystery_beat`, `cold_open`, `two_hander`, `countdown`; each `{"beats": [beat, ...], "grains": int}`. A beat is `{"role": str, "size": str, "hold": float, "line": str|None, "who": "A"|"B"|"AB"|None, "intent": str|None, "insert": bool, "prop": bool, "freeze": bool}`. Also `subject_of(concept) -> str`, `insert_for(concept) -> str`, `prop_for(insert_kind) -> str`, `fill(shape, subject, name_a, name_b) -> list[dict]` returning beat dicts with `line` resolved.

- [ ] **Step 1: Write the failing tests**

```python
class FreshShapesTests(unittest.TestCase):
    def setUp(self):
        if _fresh_shapes is None:
            self.skipTest("fresh.shapes not importable")
        self.S = _fresh_shapes

    def test_four_shapes_with_distinct_size_skeletons(self):
        sk = {k: tuple(b["size"] for b in v["beats"]) for k, v in self.S.SHAPES.items()}
        self.assertEqual(len(sk), 4)
        self.assertEqual(len(set(sk.values())), 4, "two shapes share a size skeleton")

    def test_every_shape_opens_inside_the_hook_window(self):
        # oleo17: the first 2 seconds are the price of admission.
        for k, v in self.S.SHAPES.items():
            b = v["beats"][0]
            est = b["hold"] + (len((b["line"] or "").split()) / 2.5)
            self.assertLessEqual(est, 2.0, "%s opens in %.2fs" % (k, est))

    def test_every_shape_ends_on_a_short_payoff(self):
        # 起承转合: 合 is short and immediately after the turn.
        for k, v in self.S.SHAPES.items():
            self.assertLessEqual(v["beats"][-1]["hold"], 1.2, k)

    def test_hold_budget_within_ceiling(self):
        for k, v in self.S.SHAPES.items():
            total = sum(b["hold"] for b in v["beats"])
            self.assertLessEqual(total, 5.0, "%s holds %.2fs" % (k, total))

    def test_every_insert_declares_an_intent_on_both_sides(self):
        for k, v in self.S.SHAPES.items():
            beats = v["beats"]
            for i, b in enumerate(beats):
                if not b["insert"]:
                    continue
                # A cold-open insert has no predecessor, so it needs no intent.
                if i > 0:
                    self.assertIn(b.get("intent"), ("eyeline", "match", "reverse"), k)
                if i + 1 < len(beats):
                    self.assertIn(beats[i + 1].get("intent"),
                                  ("eyeline", "match", "reverse"), k)

    def test_filled_lines_respect_the_word_cap(self):
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                n = len((b["line"] or "").split())
                self.assertLessEqual(n, 8, "%s: %r" % (k, b["line"]))

    def test_filled_expressions_are_all_valid(self):
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                for key in ("expr", "exprTo", "expr2", "exprTo2"):
                    if b.get(key):
                        self.assertIn(b[key], _fresh_story_schema.EXPR_INKBEAN)

    def test_subject_of_picks_the_content_word(self):
        self.assertEqual(self.S.subject_of("Cute couple proposal day happy ending"), "proposal")
        self.assertEqual(self.S.subject_of("AI writes code now"), "code")
        self.assertEqual(self.S.subject_of(""), "thing")

    def test_insert_for_is_concept_derived_and_in_vocabulary(self):
        self.assertEqual(self.S.insert_for("a letter arrives"), "document")
        self.assertEqual(self.S.insert_for("the phone lights up"), "phone")
        self.assertIn(self.S.insert_for("something unrecognisable"), self.S.INSERT_KINDS)

    def test_prop_for_stays_inside_the_implemented_set(self):
        for k in self.S.INSERT_KINDS:
            self.assertIn(self.S.prop_for(k), self.S.PROPS)

    def test_no_shape_reuses_the_old_hard_coded_arc(self):
        banned = {"Is this even real?", "Watch. One sentence.",
                  "That's... not possible.", "One sentence. Zero artists."}
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                self.assertNotIn(b["line"], banned, k)
```

Add `import fresh.shapes as _fresh_shapes` to the same `try` block, and `_fresh_shapes = None` to its `except`.

- [ ] **Step 2: Run to verify failure**

Run: `python tools/selftest_gates.py FreshShapesTests -v`
Expected: SKIP/`AttributeError` — `tools/fresh/shapes.py` does not exist.

- [ ] **Step 3: Write the implementation**

Create `tools/fresh/shapes.py`. Every line below is clean-room authored for this engine; the *numbers* come from the measured `cine_release` precedent and the MIT budget method recorded in `THIRD_PARTY.md`.

```python
"""fresh.shapes - a small library of dramatic shapes.

A shape is a beat sequence, not a topic. Two episodes of one series must differ
in SHAPE, not just in subject, or the channel reads as mass production.

Budgets are measured from the owner-approved film (projects/cine_release:
8 shots, 10.775s, 1.35s/shot, 4.75s of holds, longest line 6 words) and from the
MIT budget method in THIRD_PARTY.md. Line cap 8 words. Hook <= 2.0s.

Every expression name here is in chars/acting.js PRESETS. The old arc used
'excited', 'smirk' and 'shocked', none of which exist; faceAt() fell back to
neutral, so the reaction shot had no reaction.
"""
import re

from .story_schema import (MAX_LINE_WORDS, SETS, PROPS, INSERT_KINDS,
                           EXPR_INKBEAN)

STOP = frozenset("""a an the of for and or to in on at with without is are was were
be been this that these those it its as by from into about over after before
between during now just very really cute happy sad big small new old""".split())
VERBS = frozenset("""writes write wrote makes make made does do did goes go went
gets get got takes take took gives give gave finds find found sees see saw
says say said tells tell told comes come came runs run ran""".split())

# concept keyword -> insert kind. Deterministic, and it makes the picture about
# the concept instead of a random object.
INSERT_HINTS = (
    ("document", ("letter", "document", "paper", "report", "note", "contract", "will")),
    ("phone",    ("phone", "text", "message", "call", "app", "notification", "chat")),
    ("photo",    ("photo", "picture", "image", "photograph", "portrait")),
    ("card",     ("card", "ticket", "invitation", "ace", "playing")),
    ("screen",   ("screen", "code", "computer", "monitor", "ai", "robot", "data")),
)


def subject_of(concept):
    """Longest content word. A heuristic, not understanding -- see ADR 0004."""
    words = [w for w in re.findall(r"[a-z]+", str(concept).lower())
             if w not in STOP and w not in VERBS]
    if not words:
        return "thing"
    return max(words, key=lambda w: (len(w), -words.index(w)))


def insert_for(concept):
    low = str(concept).lower()
    for kind, hints in INSERT_HINTS:
        if any(h in low for h in hints):
            return kind
    return "screen"


def prop_for(insert_kind):
    """Only mug/book/phone are implemented (director.py:1024)."""
    if insert_kind in ("phone", "screen"):
        return "phone"
    if insert_kind in ("document", "photo", "card"):
        return "book"
    return "mug"


# Beat fields: role, size, hold, line (a template or None), who ("A"/"B"/"AB"/None),
# intent, insert, prop, freeze. {s}=subject, {a}=name A, {b}=name B.
SHAPES = {
    # The owner-approved skeleton (DEMO_STORY / cine_release): 8 beats.
    # Holds total 4.60s (cine_release: 4.75s). The opening hold is 0.35 rather
    # than 0.50 so the first beat lands inside the 2.0s hook window.
    "mystery_beat": {"grains": 2, "beats": [
        {"role": "establish", "size": "wide",   "hold": 0.35, "who": "AB",
         "line": "Nobody expected the {s}.", "intent": None},
        {"role": "problem",   "size": "med",    "hold": 0.35, "who": "A",
         "line": "Something about it is wrong.", "intent": None,
         "expr": "neutral", "exprTo": "worried"},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline", "insert": True},
        {"role": "turn",      "size": "close",  "hold": 0.30, "who": "A",
         "line": "Don't touch it.", "intent": "eyeline",
         "expr": "worried", "exprTo": "determined", "prop": True},
        {"role": "opposition","size": "med",    "hold": 0.30, "who": "B",
         "line": "It's only a {s}, {a}.", "intent": "reverse",
         "expr": "curious"},
        {"role": "action",    "size": "wide",   "hold": 1.50, "who": "AB",
         "line": None, "intent": None, "freeze": True},
        {"role": "payoff",    "size": "close",  "hold": 0.45, "who": "A",
         "line": "That's why.", "intent": None,
         "expr": "determined", "exprTo": "relieved"},
        {"role": "bookend",   "size": "wide",   "hold": 0.60, "who": "AB",
         "line": "The {s} stays.", "intent": None, "expr": "relieved"},
    ]},
    # The object before the people. 6 beats, 3.50s holds.
    "cold_open": {"grains": 2, "beats": [
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": None, "insert": True},
        {"role": "reveal",    "size": "wide",   "hold": 0.50, "who": "AB",
         "line": "It was left for us.", "intent": "reverse"},
        {"role": "problem",   "size": "med",    "hold": 0.40, "who": "B",
         "line": "A {s}. Here.", "intent": None, "expr": "curious"},
        {"role": "turn",      "size": "close",  "hold": 0.30, "who": "A",
         "line": "Someone wanted us to see.", "intent": None,
         "expr": "neutral", "exprTo": "determined"},
        {"role": "opposition","size": "med",    "hold": 0.35, "who": "B",
         "line": "Or someone wanted us gone.", "intent": "reverse",
         "expr": "worried"},
        {"role": "payoff",    "size": "wide",   "hold": 1.20, "who": "AB",
         "line": None, "intent": None, "freeze": True},
    ]},
    # Two people, one axis, crossed twice. 7 beats, 3.65s holds.
    "two_hander": {"grains": 2, "beats": [
        {"role": "claim",     "size": "med",    "hold": 0.40, "who": "A",
         "line": "The {s} is mine.", "intent": None, "expr": "determined"},
        {"role": "counter",   "size": "med",    "hold": 0.35, "who": "B",
         "line": "It was never yours.", "intent": "reverse", "expr": "angry"},
        {"role": "doubt",     "size": "close",  "hold": 0.30, "who": "A",
         "line": "Then why keep it?", "intent": None,
         "expr": "determined", "exprTo": "hurt"},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline", "insert": True},
        {"role": "concession","size": "med",    "hold": 0.40, "who": "B",
         "line": "Because I was afraid.", "intent": "reverse",
         "expr": "angry", "exprTo": "ashamed"},
        {"role": "decision",  "size": "close",  "hold": 0.45, "who": "A",
         "line": "Keep it, then.", "intent": None,
         "expr": "hurt", "exprTo": "relieved", "prop": True},
        {"role": "shared",    "size": "wide",   "hold": 1.00, "who": "AB",
         "line": None, "intent": None},
    ]},
    # Pressure from the first frame. 8 beats, 4.25s holds.
    "countdown": {"grains": 3, "beats": [
        {"role": "urgency",   "size": "close",  "hold": 0.30, "who": "A",
         "line": "Ten seconds.", "intent": None, "expr": "worried"},
        {"role": "stakes",    "size": "wide",   "hold": 0.50, "who": "AB",
         "line": "The {s} decides it.", "intent": None},
        {"role": "obstacle",  "size": "med",    "hold": 0.40, "who": "B",
         "line": "You can't reach it.", "intent": "reverse", "expr": "tired"},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline", "insert": True},
        {"role": "decision",  "size": "close",  "hold": 0.30, "who": "A",
         "line": "Watch me.", "intent": "eyeline",
         "expr": "worried", "exprTo": "determined", "prop": True},
        {"role": "attempt",   "size": "med",    "hold": 0.35, "who": "B",
         "line": "That's not possible.", "intent": "reverse", "expr": "surprised"},
        {"role": "action",    "size": "wide",   "hold": 1.20, "who": "AB",
         "line": None, "intent": None, "freeze": True},
        {"role": "payoff",    "size": "close",  "hold": 0.45, "who": "A",
         "line": "It was.", "intent": None,
         "expr": "determined", "exprTo": "hopeful"},
    ]},
}


def fill(shape, subject, name_a, name_b):
    """Resolve a shape's line templates. Returns new dicts; SHAPES is not mutated."""
    out = []
    for b in shape["beats"]:
        d = dict(b)
        d["line"] = (b["line"] or "").format(s=subject, a=name_a, b=name_b) or None
        out.append(d)
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `python tools/selftest_gates.py FreshShapesTests -v`
Expected: 11 tests PASS.

Hook-window arithmetic, so the executor can check it by hand: `mystery_beat` 0.35 + 4/2.5 = **1.95 s**; `cold_open` 0.75 + 0 = **0.75 s**; `two_hander` 0.40 + 4/2.5 = **2.00 s**; `countdown` 0.30 + 2/2.5 = **1.10 s**. All ≤ 2.0. If a future edit pushes one over, shorten the line or lower the hold — do **not** raise the ceiling.

- [ ] **Step 5: Cross-check the shapes against the Task 1 contract**

Run:
```bash
python -c "
import sys; sys.path.insert(0,'tools')
from fresh.shapes import SHAPES, fill
from fresh.story_schema import validate_story
for k,v in SHAPES.items():
    beats=fill(v,'proposal','MAX','JAKE')
    shots=[]
    for i,b in enumerate(beats):
        s={'id':'s%03d'%(i+1),'size':b['size'],'hold':b['hold'],'line':b['line'] or '',
           'in':{'type':'cut'}}
        if b.get('intent'): s['cut_intent']=b['intent']
        if b.get('insert'): s['insertKind']='phone'
        if b.get('expr'): s['expr']=b['expr']
        if b.get('exprTo'): s['exprTo']=b['exprTo']; s['at']=0.4
        if b['who']=='A': s['who']='MAX'
        elif b['who']=='B': s['who']='JAKE'
        elif b['who']=='AB': s['who']='MAX'; s['who2']='JAKE'
        shots.append(s)
    d={'title':'T','cast':{'MAX':{},'JAKE':{}},'shots':shots,'music':[]}
    e,w=validate_story(d)
    print(k,'errors',len(e),'warnings',len(w)); [print('   ',x) for x in e]
"
```
Expected: `errors 0` for all four shapes. Any error is a shape bug — fix the shape, not the validator.

- [ ] **Step 6: Show the diff and propose the commit**

```bash
git add tools/fresh/shapes.py tools/selftest_gates.py
git diff --cached --stat
```
Commit message (only on the owner's word): `feat(fresh): add four distinct dramatic shapes with measured budgets`

---

## Task 3: Rewrite `concept_to_story`, fix the series seed

**Files:**
- Modify: `tools/fresh/story.py:20-127` (`concept_to_story`), keeping `write_story` unchanged
- Modify: `tools/fresh/series.py:26`
- Test: `tools/selftest_gates.py` (new class `FreshStoryTests`)

**Interfaces:**
- Consumes: `shapes.SHAPES`, `shapes.fill`, `shapes.subject_of`, `shapes.insert_for`, `shapes.prop_for` (Task 2); `story_schema.validate_story` (Task 1); existing `palette.generate_palette`, `core.Rng`, `core.seed_from_concept`.
- Produces: `concept_to_story(concept, series_id=None, episode=None, title=None) -> dict` — **same signature and same top-level keys as today**, so `generate.py:90` and `director.py` need no change. New: the returned dict always passes `validate_story` with zero errors, and shape selection is round-robin on `episode` (seed-picked when `episode is None`).

- [ ] **Step 1: Write the failing tests**

```python
class FreshStoryTests(unittest.TestCase):
    def setUp(self):
        if _fresh_story is None or _fresh_story_schema is None:
            self.skipTest("fresh.story / fresh.story_schema not importable")

    def test_story_passes_the_contract(self):
        for concept in ("Cute couple proposal day happy ending", "AI writes code now",
                        "a letter arrives at midnight", ""):
            d = _fresh_story.concept_to_story(concept)
            errs, _ = _fresh_story_schema.validate_story(d)
            self.assertEqual(errs, [], "%s -> %s" % (concept, errs))

    # Twelve episodes of one series, each with its own concept. Single-noun
    # concepts so subject_of() is unambiguous and all twelve subjects differ.
    EP_CONCEPTS = ["proposal", "funeral", "letter", "phone", "code", "photograph",
                   "ticket", "room", "rain", "clock", "stranger", "broadcast"]

    def test_two_concepts_do_not_share_the_old_arc(self):
        banned = {"Is this even real?", "Watch. One sentence.",
                  "That's... not possible.", "One sentence. Zero artists."}
        a = _fresh_story.concept_to_story("Cute couple proposal day happy ending")
        b = _fresh_story.concept_to_story("AI writes code now")
        la = [s["line"] for s in a["shots"] if s.get("line")]
        lb = [s["line"] for s in b["shots"] if s.get("line")]
        self.assertNotEqual(la, lb)
        self.assertFalse(banned & set(la + lb), banned & set(la + lb))
        self.assertTrue(any("proposal" in x for x in la), la)
        self.assertTrue(any("code" in x for x in lb), lb)

    def test_twelve_episodes_use_all_four_shapes(self):
        sk = set()
        for ep, c in enumerate(self.EP_CONCEPTS, start=1):
            d = _fresh_story.concept_to_story(c, series_id="proposal_series", episode=ep)
            sk.add(tuple(s["size"] for s in d["shots"]))
        self.assertEqual(len(sk), 4, "only %d distinct skeletons" % len(sk))

    def test_no_episode_repeats_a_line_set(self):
        seen = []
        for ep, c in enumerate(self.EP_CONCEPTS, start=1):
            d = _fresh_story.concept_to_story(c, series_id="proposal_series", episode=ep)
            seen.append(frozenset(s["line"] for s in d["shots"] if s.get("line")))
        self.assertEqual(len(set(seen)), 12, "two episodes share an identical line set")

    def test_series_cast_is_stable_across_episodes(self):
        a = _fresh_story.concept_to_story("the proposal", series_id="proposal_series", episode=1)
        b = _fresh_story.concept_to_story("the funeral", series_id="proposal_series", episode=2)
        self.assertEqual(a["cast"], b["cast"])

    def test_series_bible_agrees_with_cast(self):
        if _fresh_series is None:
            self.skipTest("fresh.series not importable")
        d = _fresh_story.concept_to_story("the proposal", series_id="proposal_series", episode=1)
        sb = _fresh_series.generate_series("proposal_series", concept="the proposal")
        self.assertEqual(sb["character"]["base_color"], d["cast"]["MAX"]["color"])

    def test_determinism(self):
        a = _fresh_story.concept_to_story("AI writes code now", series_id="s", episode=3)
        b = _fresh_story.concept_to_story("AI writes code now", series_id="s", episode=3)
        self.assertEqual(a, b)

    def test_runtime_fields_unchanged(self):
        d = _fresh_story.concept_to_story("AI writes code now")
        self.assertEqual(d["aspect"], "9:16")
        self.assertEqual(d["resolution"], "1080p")
        self.assertEqual(d["fps"], 24)
        self.assertEqual(d["chars"], "inkbean")
```

- [ ] **Step 2: Run to verify failure**

Run: `python tools/selftest_gates.py FreshStoryTests -v`
Expected: `test_story_passes_the_contract` FAILS (the current arc uses `excited`/`smirk`/`shocked` and has 2 dead cuts); `test_two_concepts_do_not_share_the_old_arc` FAILS (5 shared lines); `test_series_bible_agrees_with_cast` FAILS (`#71c49e` vs `#39d930`).

- [ ] **Step 3: Fix the series seed first (one line)**

In `tools/fresh/series.py:24-27`, the bible must seed from the **series identity**, exactly as `story.py:24-26` does:

```python
def generate_series(series_id, concept=None, title=None):
    # Seed from the SERIES ID, not the episode concept: a bible that changes
    # every episode is not a bible. story.py:24 uses series_id the same way.
    seed = seed_from_concept(series_id, series_id, None)
    rng = Rng(seed)
    pal = generate_palette(series_id, series_id, None)
```

(`concept` stays in the signature — `generate.py:118` passes it — but no longer drives identity.)

- [ ] **Step 4: Rewrite `concept_to_story`**

Replace `tools/fresh/story.py:20-127` with:

```python
def concept_to_story(concept, series_id=None, episode=None, title=None):
    from .shapes import SHAPES, fill, subject_of, insert_for, prop_for
    from .story_schema import validate_story

    # Series identity (character colours) is stable across episodes.
    series_seed = series_id if series_id else concept
    series_pal = generate_palette(series_seed, series_id, None) if series_id else None
    ep_pal = generate_palette(concept, series_id, episode)
    ident = ep_pal["identity"]
    rng = Rng(ident["seed"] + "|shape")

    if series_id and series_pal is not None:
        colors = series_pal["identity"]["colors"]
        tops = series_pal["identity"]["tops"]
        heads = series_pal["identity"]["heads"]
    else:
        colors, tops, heads = ident["colors"], ident["tops"], ident["heads"]

    if title is None:
        title = concept.strip()[:40] if concept.strip() else "Fresh Story"
    if not title:
        title = "Fresh Story"

    names = ["MAX", "JAKE"]
    cast = {}
    for i, nm in enumerate(names):
        entry = {"color": colors[i % len(colors)], "top": tops[i % len(tops)],
                 "legs": colors[(i + 1) % len(colors)], "head": heads[i % len(heads)]}
        if entry["head"] != "none":
            entry["headColor"] = colors[(i + 1) % len(colors)]
        cast[nm] = entry

    # Round-robin by episode: consecutive episodes of a series are GUARANTEED to
    # differ in shape, which is what "mini-series episodes" needs. Without an
    # episode number, fall back to the concept seed.
    ordered = sorted(SHAPES)
    if episode is not None:
        shape_name = ordered[(int(episode) - 1) % len(ordered)]
    else:
        shape_name = rng.pick(ordered)
    shape = SHAPES[shape_name]
    subject = subject_of(concept)
    insert_kind = insert_for(concept)
    prop_kind = prop_for(insert_kind)
    beats = fill(shape, subject, names[0], names[1])

    shots = []
    for i, b in enumerate(beats):
        s = {"id": "s%03d" % (i + 1), "size": b["size"], "hold": b["hold"],
             "line": b["line"] or "", "bg": ident["mood"], "set": ident["set"],
             "in": {"type": "cut"}}
        if i == 0:
            s["in"] = {"type": "fade", "dur": 0.5}
        if b.get("intent"):
            s["cut_intent"] = b["intent"]
        if b["who"] == "A":
            s.update(who=names[0], x=0.40, pose="stand", facing=1)
        elif b["who"] == "B":
            s.update(who=names[1], x=0.62, pose="stand", facing=-1)
        elif b["who"] == "AB":
            s.update(who=names[0], x=0.36, pose="stand", facing=1,
                     who2=names[1], x2=0.68, pose2="stand", facing2=-1)
        if b.get("expr"):
            s["expr"] = b["expr"]
        if b.get("exprTo"):
            s["exprTo"] = b["exprTo"]
            s["at"] = round(b["hold"] + 0.35, 2)
        if b.get("insert"):
            s["insertKind"] = insert_kind
            s.pop("bg", None)
            s.pop("set", None)
        if b.get("prop"):
            s["prop"] = {"kind": prop_kind}
        if b.get("freeze"):
            s["freeze"] = {"at": round(b["hold"] * 0.4, 2)}
            s["sfx"] = [{"at": 0.0, "name": "hit", "gain": -10},
                        {"at": round(b["hold"] * 0.4, 2), "name": "freeze", "gain": -18}]
        elif i == 0:
            s["sfx"] = [{"at": 0.05, "name": "whoosh", "gain": -26}]
        shots.append(s)

    story = {"title": title, "aspect": "9:16", "resolution": "1080p", "fps": 24,
             "style": ident["style"], "set": ident["set"], "chars": "inkbean",
             "cast": cast, "shots": shots, "music": []}
    errs, _ = validate_story(story)
    if errs:
        raise ValueError("fresh story violates the contract: " + "; ".join(errs))
    return story
```

Keep the module docstring, the `sys.path` line, the `palette` import and `write_story` exactly as they are. Delete the now-unused `TOPS_VOCAB`/`HEADS_VOCAB` aliases only if nothing imports them — check first with `grep -rn "TOPS_VOCAB\|HEADS_VOCAB" tools/`.

- [ ] **Step 5: Run to verify pass**

Run: `python tools/selftest_gates.py FreshStoryTests -v`
Expected: 8 tests PASS.

Both distinctness tests are guaranteed by construction, not by luck: round-robin gives all four skeletons across episodes 1–12, and the twelve single-noun concepts give twelve distinct subjects. Every shape has at least one `{s}` line, so no two line sets can collide. If either test fails, the round-robin or `subject_of` is broken — fix that, do not weaken the assertion.

- [ ] **Step 6: Verify the real films would now be clean**

Run:
```bash
python -c "
import sys; sys.path.insert(0,'tools')
from fresh.story import concept_to_story
from fresh.story_schema import validate_story
import json
for c in ['Cute couple proposal day happy ending','AI writes code now']:
    d=concept_to_story(c)
    e,w=validate_story(d)
    print(c,'->',len(d['shots']),'shots, errors',len(e),'warnings',len(w))
    print('   sizes:',[s['size'] for s in d['shots']])
    print('   lines:',[s['line'] for s in d['shots'] if s['line']])
"
```
Expected: `errors 0` for both, different shot counts and different lines.

- [ ] **Step 7: Run the whole suite**

Run: `python tools/selftest_gates.py`
Expected: all pre-existing classes still pass.

- [ ] **Step 8: Show the diff and propose the commit**

```bash
git add tools/fresh/story.py tools/fresh/series.py tools/selftest_gates.py
git diff --cached --stat
```
Commit message (only on the owner's word): `fix(fresh): derive story shape and lines from the concept; make the series bible series-stable`

---

## Task 4: Wire the contract into the pipeline

**Files:**
- Create: `tools/story_check.py`
- Modify: `tools/generate.py` (insert after the story path is resolved, ~:96, before the director call at :102)
- Test: `tools/selftest_gates.py` (new class `StoryCheckTests`)

**Interfaces:**
- Consumes: `fresh.story_schema.validate_story` (Task 1).
- Produces: CLI `python tools/story_check.py --story <json> [--strict]` → exit 1 on any error, exit 1 on warnings only under `--strict`, exit 0 otherwise. `generate.py` calls it with `--strict` for `--fresh`, and without for `--story` unless the owner passed `--strict`.

- [ ] **Step 1: Write the failing tests**

```python
class StoryCheckTests(unittest.TestCase):
    def setUp(self):
        if _fresh_story_schema is None:
            self.skipTest("fresh.story_schema not importable")

    def _run(self, payload, *extra):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "story.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            r = subprocess.run([sys.executable, os.path.join(TOOLS, "story_check.py"),
                                "--story", p, *extra],
                               capture_output=True, text=True)
            return r.returncode, r.stdout + r.stderr

    def test_clean_story_exits_zero(self):
        rc, out = self._run({"title": "T", "cast": {"MAX": {}}, "music": [],
                             "shots": [{"id": "s001", "size": "wide", "who": "MAX",
                                        "line": "Hello.", "hold": 0.4,
                                        "in": {"type": "cut"}}]})
        self.assertEqual(rc, 0, out)

    def test_invalid_expression_exits_one(self):
        rc, out = self._run({"title": "T", "cast": {"MAX": {}}, "music": [],
                             "shots": [{"id": "s001", "size": "wide", "who": "MAX",
                                        "expr": "smirk", "line": "Hello.",
                                        "hold": 0.4, "in": {"type": "cut"}}]})
        self.assertEqual(rc, 1, out)
        self.assertIn("smirk", out)

    def test_warning_is_not_fatal_without_strict(self):
        payload = {"title": "T", "cast": {"MAX": {}}, "music": [],
                   "shots": [{"id": "s001", "size": "wide", "who": "MAX",
                              "line": "Hello.", "hold": 6.0, "in": {"type": "cut"}}]}
        rc, _ = self._run(payload)
        self.assertEqual(rc, 0)
        rc, _ = self._run(payload, "--strict")
        self.assertEqual(rc, 1)

    def test_missing_file_exits_one(self):
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "story_check.py"),
                            "--story", "does-not-exist.json"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `python tools/selftest_gates.py StoryCheckTests -v`
Expected: FAIL — `tools/story_check.py` does not exist, so the subprocess returns 2.

- [ ] **Step 3: Create the CLI**

```python
#!/usr/bin/env python3
"""story_check.py -- pre-flight the story JSON against the engine's real capabilities.

  python tools/story_check.py --story examples/director-demo/story.json [--strict]

Exit 1 on any error; exit 1 on warnings only under --strict; else 0.
This is a PRE-flight. seam_gate.py remains the post-render authority.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fresh.story_schema import validate_story


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--strict", action="store_true", help="warnings are fatal too")
    a = ap.parse_args()
    if not os.path.exists(a.story):
        sys.exit("story_check: no such file: %s" % a.story)
    with open(a.story, encoding="utf-8") as fh:
        d = json.load(fh)
    errs, warns = validate_story(d)
    print("story_check: %s" % a.story)
    for e in errs:
        print("  ERROR   %s" % e)
    for w in warns:
        print("  WARNING %s" % w)
    print("  %d error(s), %d warning(s)" % (len(errs), len(warns)))
    if errs or (a.strict and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `python tools/selftest_gates.py StoryCheckTests -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Report against every existing story before wiring it fatal**

Run:
```bash
for f in examples/*.json projects/cine_release/story/shots.json; do
  echo "--- $f"; python tools/story_check.py --story "$f" 2>&1 | tail -4
done
```
Expected: `examples/director-demo/story.json` reports **5 expression errors** (`sleepy`, `smirk`×2, `shocked`, `happy`) and 0 dead cuts. `examples/ai-trends-story.json` and `examples/detective-story.json` report expression errors and 2 dead cuts each. **Record the output. Do not fix these files in this task** — they are hand-authored, and one of them is the source of the owner-approved film. See "Owner decisions" below.

Note: `projects/*/story/shots.json` is the *compiled* output, not the input story; its shots carry a `params` sub-object, so the validator will report unknown keys. That is expected and is why the check runs on the **input** story only.

- [ ] **Step 6: Wire it into `generate.py`**

Insert immediately after the `story = os.path.abspath(a.story)` line (~:96) and before the director call:

```python
    # 0. story contract pre-flight. A --fresh film must be clean; a hand-authored
    #    or LLM-authored story is reported, and fatal only under --strict -- the
    #    same rule seam_gate and style_lock already follow.
    sc = [py, os.path.join(here, "story_check.py"), "--story", story]
    if a.strict or a.fresh:
        sc.append("--strict")
    if run(sc, studio):
        sys.exit("GENERATE: story contract failed -- fix the story JSON, not the gate")
```

- [ ] **Step 7: Verify the wiring without rendering**

Run: `python tools/generate.py --fresh "a letter arrives at midnight" --out projects/_contract_probe`
Expected: it prints `GENERATE: fresh story -> …/tmp/fresh_story.json`, then `story_check: … 0 error(s)`, then proceeds into `director.py`. **Stop the run after the director stage** (Ctrl-C) — this step verifies wiring, not a film. Then remove the probe directory only if it is empty of anything the owner wants; otherwise leave it and say so.

Run: `python tools/generate.py --story examples/ai-trends-story.json --out projects/_contract_probe2`
Expected: `story_check` prints errors and **exits 0** (no `--strict`), so the run continues — proving the approved/hand-authored path is not blocked. Stop it after the check.

- [ ] **Step 8: Run the whole suite**

Run: `python tools/selftest_gates.py`
Expected: all classes pass; total = baseline + 12 + 11 + 8 + 4 = baseline + 35.

- [ ] **Step 9: Show the diff and propose the commit**

```bash
git add tools/story_check.py tools/generate.py tools/selftest_gates.py
git diff --cached --stat
```
Commit message (only on the owner's word): `feat(tools): pre-flight the story contract; fatal for --fresh, report-only for --story`

---

## Task 5: Provenance and the lesson

**Files:**
- Modify: `THIRD_PARTY.md` (Adapted table + MIT notices + a new NOTICE-carve-out section)
- Modify: `docs/LESSONS.md`
- Create: `docs/adr/0004-story-contract.md`

**Interfaces:**
- Consumes: the verified licence facts in the evidence section above.
- Produces: documentation only. No code, no test.

- [ ] **Step 1: Add the two ledger rows**

In `THIRD_PARTY.md`, under `## Adapted`, add:

```markdown
| [`oleo17/story-to-script-en`](https://github.com/oleo17/story-to-script-en) | MIT | Method: budget before craft (event grain → runtime → scene/shot/word ceilings); the 8-word short-form line cap; the 2-second hook budgeted separately from story; per-genre payoff obligation | `tools/fresh/shapes.py`, `tools/fresh/story_schema.py` (`MAX_LINE_WORDS`), `docs/adr/0004-story-contract.md` | No. Clean-room; the numbers are re-derived against `projects/cine_release`. |
| [`jtydhr88/screenwriting-skills`](https://github.com/jtydhr88/screenwriting-skills) | MIT **+ NOTICE carve-out** | Method, original layer only: 起/承/转/合 proportion (承 ≈ two-thirds, 合 short); crisis as a true dilemma; a beat needs a visible change, character-driven first; container-episode running order | `tools/fresh/shapes.py` (beat roles and hold profile) | No. **`reference*.md` is excluded entirely** — see the carve-out below. |
```

- [ ] **Step 2: Add the MIT notices and the carve-out**

Append under `## MIT notices`:

````markdown
### story-to-script-en

```
MIT License

Copyright (c) 2026 story-to-script contributors
```
(Standard MIT grant and disclaimer; full text at
https://github.com/oleo17/story-to-script-en/blob/main/LICENSE)

### screenwriting-skills

```
MIT License

Copyright (c) 2026 Terry Jia
```
(Standard MIT grant and disclaimer; full text at
https://github.com/jtydhr88/screenwriting-skills/blob/main/LICENSE)
````

Then add a new section:

```markdown
## NOTICE carve-out — screenwriting-skills

`jtydhr88/screenwriting-skills` ships a `NOTICE` file (3,923 B) that qualifies its MIT
grant. It states that the LICENSE *"cannot grant rights in material that belongs to
someone else"*. Its `reference*.md` files are quotation corpora drawn from 47 books and
23 volumes of published scripts and opera scores, including HBO *Succession* shooting
scripts (Faber 2023) with verbatim dialogue and the characters Roman, Shiv, Kendall and
Logan.

**Blocked:** every `reference*.md` file, every quotation, every translated passage, and
every third-party character name from that repo. Attribution does not cure this — MIT
cannot license what its author does not own.

**Allowed:** the repo's own original layer — its numbered principles, checklists and
workflows — which the NOTICE expressly covers, commercial use included. Only that layer
was read, and only its ideas were re-expressed here. No prose was copied.

If a future change wants any `reference*.md` content, that change is blocked until the
underlying rights are cleared.
```

- [ ] **Step 3: Record the lesson**

Append to `docs/LESSONS.md`:

```markdown
## 2026-11-12 — an unknown expression name is a neutral face, not an error

`faceAt()` does `PRESETS[a] || PRESETS.neutral` (`tools/director.py:81`). `PRESETS` has
13 keys. Across the repo, 87 expression slots used names that are not among them —
`smirk`×34, `shocked`×20, `happy`×16, `sleepy`×11, `excited`×6. In the fresh films 6 of 9
slots were invalid, including the reaction shot. The films rendered a neutral face where
a reaction was written, and every gate passed.

**Rule:** a vocabulary that falls back silently is not a vocabulary. Close it in a
validator and assert the closed set equals the source (`test_vocabularies_match_source`).
The same applies to prop kinds (magenta box), sets (fallback to room) and param keys
(dropped by the `PARAM_KEYS` filter).
```

- [ ] **Step 4: Write ADR 0004**

Create `docs/adr/0004-story-contract.md`:

```markdown
# ADR 0004 — The story contract, and where authorship actually lives

**Status:** Accepted for the fresh pipeline (2026-11-12). Owner decision pending on the
hand-authored stories (see below).

## Context
`tools/fresh/story.py` hard-coded one 6-shot arc. Two concepts produced 5 of 6 identical
lines. Every insert boundary was a dead cut. 6 of 9 expression slots rendered neutral.
`director.py` warns about none of these, so the pipeline shipped them.

## Decision
1. `tools/fresh/story_schema.py` closes the story-JSON contract against real source:
   poses, both expression vocabularies, styles, moods, sets, prop kinds, insert kinds,
   SFX names, param keys, the 8-word line cap, the 5.0 s hold budget, and the
   shared-subject-or-declared-intent continuity rule.
2. `tools/fresh/shapes.py` holds four dramatic shapes with distinct size skeletons.
   Episode distinctness comes from shape × subject, not from subject alone.
3. `story_check.py` is fatal for `--fresh`, report-only for `--story` unless `--strict`.
   This mirrors the existing `seam_gate` / `style_lock` rule and does not block the
   owner-approved film.

## The honest ceiling
A deterministic Python function cannot author a genuinely distinct storyline for an
arbitrary concept. `subject_of()` is a longest-content-word heuristic. The shape library
gives structural distinctness and correct continuity; it does **not** give authored
dialogue. Lines remain template-grade.

YouTube's inauthentic-content policy allows "a series with distinct storylines per
episode". Four shapes × a keyword subject is a real improvement over one arc, but it is
not a distinct storyline. **The seam for that already exists:** `generate.py --story
<json>` accepts an authored story, and it now passes through the same contract. An LLM
(or the owner) writes the story JSON; the deterministic layer validates and renders it.
That is the automation path, and it is why the contract is built first.

## Consequences
- No protected path is touched. No approved project is re-rendered.
- Style locks are per-project (`style_lock.py:44`), so this cannot invalidate
  `cine_release`'s lock.
- `series.json` and `set_spec.json` remain write-only. Wiring them is a separate
  decision; the seed bug that made the bible episode-dependent is fixed here.

## Owner decision required (not implemented)
`examples/director-demo/story.json` is the source of the approved `cine_release`. It has
5 invalid expression slots. Fixing them changes pixels and therefore requires a
style-lock re-baseline and the owner's re-approval. Proposed mapping, for approval only:
`sleepy → tired`, `smirk → curious`, `shocked → surprised`, `happy → relieved`.
Nothing in this plan applies it.
```

- [ ] **Step 5: Verify the docs are consistent**

Run: `grep -n "reference\*.md\|NOTICE\|oleo17\|jtydhr88" THIRD_PARTY.md`
Expected: both repos present in the Adapted table, both notices present, the carve-out section present.

Run: `python tools/selftest_gates.py`
Expected: unchanged from Task 4 — documentation must not affect tests.

- [ ] **Step 6: Show the diff and propose the commit**

```bash
git add THIRD_PARTY.md docs/LESSONS.md docs/adr/0004-story-contract.md
git diff --cached --stat
```
Commit message (only on the owner's word): `docs: record the story-method provenance, the NOTICE carve-out and the silent-neutral lesson`

---

## Owner decisions required before any of this ships

1. **The approved film's expressions.** `cine_release` renders 5 of 14 expression slots as neutral. Fixing them changes the approved pixels → style-lock re-baseline + your re-approval. Proposed mapping is in ADR 0004. **Nothing here touches it.**
2. **Push hygiene, unrelated but blocking.** `docs/adr/0003-dark-background-styles.md:39-42` contains a leaked agent transcript and a raw tool-call fragment. The repo is public. That must be cleaned before any push. Also: the live tree is 14 commits ahead of origin with 15 uncommitted entries; `E:\Local_Mis_WS\aitrends-backup-durable` is a stale snapshot at `0bfb608` and would publish nothing new.
3. **`jtydhr88/screenwriting-skills` correction.** I recommended it before knowing about its NOTICE. The borrow is confined to the MIT-covered original layer; `reference*.md` is excluded. If you want that repo dropped entirely, Task 5 loses one row and Task 2 loses the 起/承/转/合 hold profile — the shapes still work, because their numbers come from your own approved film.

## Out of scope (deliberately)

- The look layer: rough.js line pass, grain, halftone, depth of field. Those change pixels and need a re-baseline.
- Wiring `series.json` / `set_spec.json` into the renderer. They are write-only today; making them authoritative is an identity decision, not a story decision.
- Caption safe-zone (`narrate.py:174`, `y: 1800`). The occlusion numbers are Tier-3 only; moving captions needs a measured reference, not a guess.
- `frame_qa.py` and `acceptance.py` are still not called by `generate.py`. Real gap, separate task.
- Music: `music: []` falls back to `MUSIC.default_plan` (`audio/mix.py:57`). Not a defect; left alone.
- `tmp/fresh_story.json` is a single shared path overwritten by every `--fresh` run. The compiled `projects/<name>/story/shots.json` is the durable record. Left alone.

### CORRECTION 2026-11-12 22:40 IST (original bullets above left visible)

Two bullets above are now out of date for the worktree (this plan file is
untracked; nothing was committed today):

- `frame_qa.py` IS now reachable from `generate.py` via the **opt-in**
  `--frame-qa` flag (`generate.py` `frame_qa_cmd()` / step 6a). It is
  report-only unless `--strict` is also passed. `acceptance.py` remains
  uncalled — that half of the bullet still stands.
- `--fresh` no longer writes one shared `tmp/fresh_story.json`.
  `fresh_story_path(studio, out)` scopes the file to the project basename.
- Also new today and not in this plan: stage-0 story-contract validation on
  BOTH entry paths; `--fail-on-issues` on `render_report.py` (capability only,
  **zero callers** — deliberately not activated); and `report_stage_failure()`
  making four previously swallowed stage failures fatal under `--strict`.
- All new behaviour is opt-in or default-preserving. Full gate suite:
  `Ran 132 tests`, `OK`, exit 0 with the managed-venv interpreter.
- Still gated and NOT done: real-clip threshold calibration (video action,
  owner go), activating `--fail-on-issues` in the pipeline (gate policy =
  Phase B), and the target-film / style-lock re-baseline decision.

---

## Self-review

**Spec coverage.** Every measured defect has a task: one hard-coded arc → Tasks 2+3; 2 dead cuts per film → Task 1 continuity rule + Task 2 intents; 87 invalid expression slots → Task 1 vocabulary + Task 2 valid names (fresh path only; approved path is an owner decision); series-bible seed mismatch → Task 3 Step 3; zero fresh test coverage → 35 new tests across Tasks 1-4; slow cutting rhythm → Task 2 hold budgets + Task 1 density warning. Provenance → Task 5.

**Placeholder scan.** No TBD/TODO. Every code step has literal code. Every test step has literal assertions. No step says "handle edge cases" or "similar to Task N".

**Type consistency.** `validate_story(d) -> (errors, warnings)` is used identically in Tasks 1, 3 and 4. `SHAPES[name]["beats"]` beat keys (`role`, `size`, `hold`, `line`, `who`, `intent`, `insert`, `prop`, `freeze`, `expr`, `exprTo`) are declared in Task 2's Interfaces and consumed with those exact names in Task 3. `fill(shape, subject, name_a, name_b)` returns new dicts and is never mutated. `subject_of`, `insert_for`, `prop_for` signatures match between Tasks 2 and 3. `_fresh_story_schema` and `_fresh_shapes` are added to the existing try/except in Tasks 1 and 2, and Task 3's `setUp` guards on both.

**Corrections made during self-review (all four were real defects in the first draft):**
1. The global constraint claimed the repo is CRLF. Measured: it is **mixed**. `generate.py` and `selftest_gates.py` are CRLF; `fresh/*` and `docs/*` are LF. The constraint is now per-file, with a post-edit CR==LF check on the two CRLF files.
2. `mystery_beat` opened at 0.50 + 4/2.5 = **2.10 s**, breaking the 2.0 s hook test. Hold lowered to 0.35 → 1.95 s. The contingency that told the executor to shorten the line was removed and replaced with the arithmetic for all four shapes.
3. `test_every_insert_declares_an_intent_on_both_sides` demanded an intent on `cold_open`'s **first** beat, which has no predecessor. Now skipped when `i == 0`.
4. Two Task 3 tests relied on random shape draws and on a subject that stripped to the same word for all twelve episodes — both could fail by luck. Shape selection is now **round-robin on `episode`**, and the tests use twelve distinct single-noun concepts. Both assertions are now guaranteed by construction.

**Known weakness, stated plainly.** The line templates are still mad-libs. Two *different* concepts that happen to draw the same shape will share their connective lines ("Don't touch it.", "That's why.") — only the `{s}` lines differ. Round-robin removes that collision for numbered episodes of a series, but not for arbitrary one-off concepts. Four shapes give structural distinctness, not authored dialogue. The plan does not claim otherwise, and ADR 0004 records the LLM-authoring seam as the real fix. If the owner's expectation is "a genuinely different story each episode", this plan is the prerequisite, not the answer.

**Not verified by execution.** No implementation code was run — the owner has not approved implementation. The vocabularies, the dead-cut counts, the expression-slot counts, the seed mismatch, the line endings and the `STYLES` parser boundary were all measured against the current tree. The test arithmetic above was checked by hand, not by running pytest.