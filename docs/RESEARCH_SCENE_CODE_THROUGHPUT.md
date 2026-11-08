# Scene-Code Authoring Throughput — Options Survey for `aitrends-2d-studio`

**Question:** what realistically raises *scene-code authoring* throughput for a series built on exactly this
code-rendered pipeline, and which options genuinely remove the per-shot hand-written cost vs. relocate it.
**Written:** 2026-11-06. Read-only research pass. No file in the studio was modified; no render, server or
browser was run. Sources are listed at the end; every number is tagged with how I got it.

**Scope note:** the owner's brief named one candidate product — "Reanime" — that I could not find evidence
for as an animation-authoring tool (see §7, Unverified).

---

## 1. The bottleneck, quantified from this repo

Facts from the brief, plus measurements I took in this pass (`[measured]` = computed by me from the files).

| Thing | Value | How known |
|---|---|---|
| Film that cost the session | 17.99 s, 13 shots, 431 frames, 1080p24 | `[measured]` `projects/acting-pass/build/report.json` |
| Scene code for that film | 327 non-comment lines across 5 shot files = **25.2 lines/shot** | `[measured]` `projects/acting-pass/scenes/shots/*.js` |
| Same metric on easier films | dialogue-call 17.1, stomach-acid 15.8, reaction-time 15.8 lines/shot | `[measured]` |
| Per-shot shared code (set) | `sets/kitchen.js` = 131 non-comment lines, authored once per location | `[measured]` |
| Hand-tuned numbers | **109–181 numeric literals per shot file**; `s008.js` alone = 109 for one 2.04 s shot | `[measured]` |
| Render time | 55 s for 432 frames @8 workers; guide measures 41 s / 13.6 s and 84 s / 29.9 s ⇒ ~21 s of video per machine-minute | brief + `STICKMAN_VIDEO_GUIDE.md` §6 |
| Existing gates | `style_lock.py` (SHA-256 of stills, byte-for-byte `check`), `motion_audit.py`, `render_report.py`, `--sheet`, `SHOT ERROR` capture, `production-qa.md` 10-section checklist | `[read]` `tools/`, `docs/` |
| **Authoring contract already exists** | `beats.py` auto-drafts `story/shots.json` (`id/start/end/line/scene:"TODO"/set/bars/in/sfx/notes`) from Whisper word timings | `[read]` `tools/beats.py` |
| **Data channel already exists and is unused** | `engine/player.js:74`: `const info = { ...(shot.params \|\| {}), shot, dur, globalT, p, line }` — per-shot JSON params are already injected into every scene module | `[read]` `engine/player.js` |
| The param channel is used by **nobody** | zero `params` keys in any project's `shots.json` | `[measured]` grep across `projects/*/story/shots.json` |
| Shot-type archetypes already written down | a 12-type vocabulary **with target proportions** (medium two-shot 25%, over-shoulder 10%, giant face 10–15%, insert 10%, freeze 1–3/film, 3D ~1/min…), plus camera rules ("never fully static": push `z` 1.0→1.05–1.10, drift `x` ±20–60, roll ±0.02) and transition mix (cut ≥80%) | `[read]` `plugin/skills/make-2d-video/references/style-bible.md` |
| Vocabulary is already closed | 27 `POSES`, 18 `EXPR`, 8 `BASE_MOODS`, 5 transition types in the player, 33 `fx2d` + 14 `ui2d` helpers, 133 engine exports total | `[measured]` `engine/rig2d.js`, `engine/styles.js`, `engine/*.js` |
| How much shot code is already "vocabulary" | of 872 call sites in all shot files: **61% resolve to engine exports**, ~5% are raw canvas ops (`fillRect`/`save`/`translate`…), the rest are project helpers (`person`, `on`, `speak`), easing methods and control flow | `[measured]` |
| Boilerplate is measurably wrong today | **50 of 299 imported names (17%) are never referenced** in the file that imports them | `[measured]` |
| Known, enumerable failure classes | gradient stop order → `addColorStop … non-finite`; constant declared inside `layer()` used outside; missing name in the `import { … } from '/engine/core.js'` list; invented pose/expression/mood/sfx name | `[read]` `STICKMAN_VIDEO_GUIDE.md` §7, `docs/production-qa.md` §1 |
| The harness does not fail loudly today | `render.mjs` collects `window.ERRORS` and prints "N shot error(s)" but **still exits 0**; the player paints `ERROR s00X@t: …` into the frame instead of throwing | `[read]` `render.mjs:71-78`, `engine/player.js:84` |
| Cross-episode code reuse today is near zero | best-match similarity of each shot file against every other project's shot files: **0.08–0.16** | `[measured]`, difflib on non-comment lines |
| Generator context size (for cost maths) | `engine-api.md` 6.3 KB + `style-bible.md` 13 KB + `SKILL.md` 9.2 KB ≈ 40 KB ≈ **10–12K tokens**, before any example shot | `[measured]` |

**Reading of the numbers.** The cost of one shot is three different things stapled together, and they have
different fixes:

1. **Structure** (~15–25 lines): imports, camera object, `kitchen(g,t,cam)`, `layer(...)`, `person(...)`,
   foreground blur. *This is removable* — it is already 61% vocabulary and 17% dead imports.
2. **Tuning** (~30–110 numbers/shot): the staggered `prog(t, HOLD+0.10, HOLD+0.62)` curves, `look` offsets,
   `V(300,330)` radii. *This is not removable* — it is the creative content of the film. What can be cut is
   the **cost of changing a number** (write → render → look).
3. **Judgement** (whether the picture matches the line at that second). The repo itself refuses to automate
   this: `report.json` carries `human_review: "required; technical checks are not acceptance"`.

So an option only counts as "genuinely removing cost" if it deletes (1), makes (2) cheap to change, or makes
(3) need fewer full-film iterations. Options that keep all three are relocations.

---

## 2. Options table

Verdicts: **REMOVES** = deletes per-shot work; **RELOCATES** = moves it somewhere else; **NON-STARTER** =
conflicts with a stated constraint.

| # | Option | What it is | Evidence it works | Cost in *this* pipeline | What it does NOT solve | Verdict |
|---|---|---|---|---|---|---|
| 1a | **Motion Canvas** as the engine | MIT TS library, generator-based `tween()/all()/sequence()` scenes + a preview editor | 19,711 stars, MIT, pushed 2026-07 `[verified]` GitHub API; "Write animations in TypeScript with your favorite IDE; use a web-based editor to sync them with audio", "Let the execution of your code define the animation" `[verified]` motioncanvas.io | Replace the whole render path, rigs, sets, grade, audio tools. Weeks–months | Their cinematic stick-figure look, rim light, freeze-frame, word-sync — none of it exists there; the editor previews code, it does not author it. Upstream also has an open discussion about relicensing MIT→GPL, whose own summary states "These licenses do not apply to the works created with Motion Canvas" `[verified]` | **NON-STARTER** (engine replacement) |
| 1b | **Remotion** as the engine | React components + `inputProps` JSON; `renderMedia`; per-frame `useCurrentFrame()` | Docs confirm AI-ready markdown docs, per-topic agent **"skills"** packages (`npx remotion skills add <skill>`), an official coding-agent workflow (prompt → iterate → Studio review → verify), and a visual default-props editor (`Cmd/Ctrl+J`) `[verified]` remotion.dev/docs. Repo: 71,161 stars, licence field `Other (NOASSERTION)`, pushed the day of this pass `[verified]` api.github.com. Licence page quote: *"Remotion is completely free to use for any individual or small company - no catch. For bigger companies, we charge a license fee."* `[verified]` | Full rewrite, plus a licence that is **not** MIT/Apache and turns paid above a size threshold I did not pin down (see §7.5) | Same as 1a; plus a React/Node toolchain the owner cannot edit, and a docs-ecosystem advantage that only pays off if he switches engines | **NON-STARTER** |
| 1c | **Revideo** as the engine | Open-source TS "programmatic video" framework, signal-based animation, headless render | Project exists and self-describes as code-not-timeline `[verified]` re.video→midrender.com | Full rewrite | Same | **NON-STARTER** |
| 1d | **Lottie** as the shot format | Open JSON animation format (layers, shapes, keyframes) rendered by lottie-web/Skia | Format spec is public; ecosystem huge (AE+Bodymovin, LottieFiles editors) `[verified]` | Their actor model (rim light, IK walk cycle, `V()` aspect switching, `wordTime()` sync) has no Lottie equivalent; JSON is huge and machine-written, human-unreadable | Acting logic, word-synced reveals, sets, camera/parallax | **RELOCATES badly** |
| 1e | **Rive** as the shot format | GUI editor + state machines + data binding, open-source runtimes | Real, widely used for interactive animation `[verified]` rive.app docs | Default export `.riv` is **binary** (+ `.rev` backup) `[verified]` — breaks text diffing, hand-editing and the "owner reads JSON payload shapes" premise | Deterministic still-locking workflow, code-expressible cinematography | **NON-STARTER** for shots; interesting only as a UI-overlay idea |
| 1f | **Their own manifest, upgraded** (`shots.json` + `params`) | The renderer already interprets `bars/in/sfx/amb/captions/grade/params`. Extend "interpreter" to the shot body: `template` id + `params` | Not a product claim — a **code fact**: `engine/player.js:74` already injects `shot.params` into `info`, unused by all 5 projects `[measured]` | One new file under `projects/<p>/scenes/` (e.g. `templates.js`) that registers shots from data + a template registry. **Zero edits** to `engine/`, `render.mjs`, `player.html`, `audio/` | Hero shots (s008-class), brand-new blocking, new props | **REMOVES** — cheapest real win |
| 2 | **Template + slot archetype library** | Turn the 12 documented shot types into callable templates; a shot becomes `template:"ots-two-shot"` + slots (`who`,`gaze`,`gesture_on`,`push`), like `chrisaswain/stickman-animation-agent`'s `scene-schema.json` (`type` ∈ action/dialogue/reaction/establishing/montage/closeup/title-card/transition) | That repo ships a real scene JSON schema, per-scene `compositions/scene-{NN}.json`, a 120-file SVG part library and character presets `[verified]` repo tree — MIT, 8 stars (design proof, **not** a measured throughput benchmark) | Registry ≈12–15 templates ≈ 1–2 focused sessions, seeded from `style-bible.md` proportions + existing shot code. **Platform risk:** YouTube's 2025-07-15 update makes "repetitive or mass-produced" content a monetisation issue `[verified]` support.google.com/youtube/answer/1311392, and their own `production-qa.md` §10 forbids "another instance of the same template" | The 3–5 shots/film that carry the film; and it can silently produce sameness, which is the one thing that kills a channel | **REMOVES (for ~70% of shots)** with a quota |
| 3 | **LLM scene code + automated eval harness** | Model writes the shot; a checker validates timing continuity, symbol existence, non-finite `addColorStop`, per-shot render, and diffs the still against the style lock | *Domain-specific:* ManiBench evaluated 12 frontier LLMs on 100 Manim animation prompts / 4,630 rendered frames — **execution success 18.40%→97.56% by model, syntactic validity 28.43%→92.06%, best temporal-fidelity only 60.47% at ≤8% deviation** `[verified]` arXiv 2603.13251 + HF dataset card. Manimator (arXiv 2507.14306) is a working example of exactly this shape — LLM writes Manim code, static analysis + a sandboxed `manim` render gate it before the video is produced; **its reported end-to-end success percentage is the one number I could not re-read in this pass** (see §7). Agentic/RL variant: 94% render-success, 85.7% visual similarity via GRPO + doc-grounded reward on Qwen3-Coder-30B `[verified]` arXiv 2604.18364. *General:* Meta TestGen-LLM — after filtering for "builds, passes, raises coverage, not flaky", **73% accepted for production**; ACH/mutation-guided 73% acceptance `[verified]` arXiv 2402.09171 / 2501.12862; Agentless hit 27.33% on SWE-bench Lite at ~$0.70/task with a plain locate→generate→**validate** pipeline, beating agent loops `[verified]` arXiv 2407.01489 | ~80–150 lines Python/Node (regex or acorn parse + vocabulary sets from `POSES`/`EXPR`/`BASE_MOODS`/sfx/music moods + a 430p single-shot preview using existing `--from/--to --scale`). Also needs `render.mjs`-equivalent *exit-code* semantics — today errors print but exit 0 `[read]` | Whether the acting *reads*. `production-qa.md` §9 already says a green machine check is not acceptance; ManiBench's temporal number is the formal version of that. And per-shot retries are the cost: 2–4 generations per accepted shot is the realistic multiplier | **REMOVES typing, ADDS a harness + retry tax** |
| 3b | Same, **local 27B Q4** | The above, offline | 4-bit quantisation is *not* the problem — arXiv 2410.14766 finds 4-bit 7B beats FP16 sub-3B and only 2-bit collapses `[verified]`. The problems are context and speed: RULER finds "of models claiming ≥32K, only half maintain satisfactory performance at 32K" `[verified]`; arXiv 2510.05381 shows input length alone hurts even with perfect retrieval `[verified]`; a 32B open model with no scaffold resolved ~15% of 100 SWE-bench Verified samples vs ~30% for a reasoning model `[verified]` sambanova.ai blog. Qwen3-Coder-30B-A3B is documented at ~51.6% Verified *only with an agent scaffold* `[verified]` HF model-card discussion | 27B at Q4_K_M ≈ 15–16 GB of weights `[estimate: ~0.55–0.6 B/param]` — over a 16 GB ceiling before KV cache, so expect mmap swapping. Port 8080 is off-limits, so llama.cpp's per-slot prompt cache can't be reloaded with a new system prompt | Free-form JS generation with a 12–20K-token prompt is exactly the workload a prefill-bound, context-fragile local model is worst at | **Viable only for small-context data authoring** (see 4) |
| 4 | **Constrained generation** (whitelist / numeric-only) | Model may only emit whitelisted primitives, or only tune parameters of an existing template | *In-domain:* that same sticker pipeline restricts the model to a fixed vocabulary in a schema-validated JSON, with deterministic JS doing the rendering `[verified]`. *Mechanism:* InCoder measured **69.0% vs 48.2%** pass for fill-in-the-blank (slot) generation vs left-to-right writing on HumanEval-derived tasks `[verified]` — templates change the generation mode, not just the prompt. *Counterweight:* grammar-constrained decoding "can distort the LLM's distribution" (NeurIPS 2024) `[verified]` and "Let Me Speak Freely?" reports stricter format constraints → greater degradation `[verified]` arXiv 2408.02442. Caveat: he controls no decoder (8080 untouchable, cloud model identity unverified), so this must be **prompt+schema+validator**, not token-level masking | Cheap: a schema (template registry + enum lists, ~2–4K tokens) and one validator. Also makes the free cloud lane affordable: data-only ≈ 0.6–2.4M tokens/2-min episode vs ~6M+ for free-form JS with retries `[estimate, see §5]` | It cannot invent a shot type that doesn't exist yet, and it inherits the template library's sameness risk. Schema churn is the new maintenance | **REMOVES most, best cost/quality ratio here** |
| 5 | **GUI keyframe/timeline authoring → JSON** | Visual scrubber/timeline that writes JSON the renderer interprets | Real tools exist — Motionity (open-source browser motion-graphics editor with keyframing) `[verified]`, After Effects→Lottie, Rive; and Remotion Studio has a **"Edit default props visually"** panel (`Cmd/Ctrl+J`) plus a third-party `remotion-annotate` overlay ("tweak props visually, annotate for your AI agent") `[verified]` remotion.dev/docs/visual-editing | Building a scrub-over-params panel on their existing `player.html` is a *tool*, not an engine edit (1–3 sessions). Adopting an external GUI means adopting its scene graph (→ 1d/1e) | It only helps **after** shots are data. A GUI over free-form JS has nothing to grab. And it produces curves, not *intent* — the acting still has to be judged by a human | **REMOVES the tuning loop, conditionally** |
| 6 | **Reuse / derivative: next episode from last** | Copy the previous episode's scene code, author only deltas | Their own numbers say this fails today: cross-project shot-code similarity **0.08–0.16** `[measured]` — the code is prose, not structure, so there is little to diff. `render_cached.py` already gives the *rendering* half of this (per-shot cache keyed on manifest entry + engine fingerprint + project code fingerprint, atomic rename) `[read]` | Free — it's just discipline. But 4 of 5 projects already share nothing but `engine/` | It doesn't work **until** option 2 exists. After templates, the delta *is* the episode and this becomes the strongest reuse lever | **RELOCATES (today) → becomes free upside after 2** |
| 7 | **Raise the abstraction of the primitive library** (missed in the brief) | Add fewer, bigger calls that render a whole beat (`overShoulder(g, who, t, opts)`), instead of ~40 helpers that render a piece | This is the pattern their own engine already proves: `fx2d`/`ui2d`/`blocking.js` collapsed enough that 61% of shot call sites are vocabulary and only ~5% touch raw canvas `[measured]` | ~2–6 hours per new hero-level recipe, one file, additive, deterministic. No new dependency, no format change | A recipe library without a *selection* mechanism is still hand-coded per shot; combine with 2 | **REMOVES** (it's the substrate of 2 and 4) |
| 8 | **Deterministic codegen from data** (missed) | A generator expands `shots.json` → checked-in `scenes/shots/*.js`; humans/models edit data, code is a build artifact | Standard practice in every codegen ecosystem (protobuf/OpenAPI-style: generated code is accepted because the generator is tested). Also sidesteps the "non-engineer can't edit JS" rule completely | Medium; needs a canonical formatting so diffs stay stable, and a decision about whether generated code is sacred or editable | Doubles the surface if he keeps hand-written hero shots alongside — mixed ownership confuses the cache key | **REMOVES, at the price of indirection** |
| 9 | **Fix the human review loop** (missed) | Contact sheet + per-shot preview + annotation capture, so judgement passes are cheap and recorded | Their pipeline already has `--sheet`, `--styles` grids, `--stills`, `build/sheets/`; and `remotion-annotate` shows the "annotate for your agent" pattern working in a neighbouring ecosystem `[verified]` | Hours, tooling only. Zero render-path risk | Nothing about generation — it shortens *acceptance*, which is what actually ate the session | **RELOCATES judgement, cheaply, and speeds it** |
| 10 | **Puppeteering / performance capture to keyframes** (missed) | Drag a rig (or a real reference) and record the parameter stream to JSON; replay deterministically | Video Puppetry (ACM TOG 2008): "a video-based interface that allows users of all skill levels to quickly create cutout-style animations **by performing the character motions**", real-time 30 fps `[verified]` gfx.cs.princeton.edu | High in their stack (need a live interaction mode + recorder; `player.js` is frame-index-pure by design, which is actually the hard prerequisite: it has no wall clock). Then pose-tracks map onto `POSES`/`face` params | Fingers, neck rotation, visemes are physically absent from the rig (`STICKMAN_VIDEO_GUIDE.md` §8) — performance capture cannot invent DOF the rig doesn't have | **REMOVES tuning for acting shots; expensive, later** |
| 11 | **Fine-tune / RL the generator on their own shot corpus** (missed) | Post-train a small coder on (manifest → scene code) pairs from past episodes | Measured in the closest literature: GRPO + doc-grounded reward → 94% render-success on Manim code `[verified]`; the unsloth-style 14B Manim LoRA variant reported 57.14% pass `[verified]` | **Not available**: needs GPU training the machine lacks (their own guide notes torch is a CPU wheel, `cuda.is_available()==False`) and a corpus of 4 episodes ≈ 44 shots, far too small | Data scarcity, and a frozen model can't track an evolving schema | **NON-STARTER now** |
| 12 | **Reference-video pose extraction → pose keys** (missed) | Run pose/face tracking on real footage, retarget to `POSES`/`face` params, freeze to JSON | The technique is mature (media-pipe/SMPL-family literature; e.g. "Real-time Pupil Tracking from Monocular Video for Digital Puppetry", arXiv 2006.11341 `[verified]` existence) | Needs the models the CPU-torch gap currently blocks, plus a retargeting step; GPU work would compete with the RAM ceiling and the 8080 server | Their rig has 27 discrete poses and one finger angle — the mapping is lossy by construction | **Research-grade, not a throughput plan** |
| 13 | **AI-facing repo documentation** (missed, and the cheapest of all) | Publish the contract the generator must obey as small, loadable docs: engine API, shot-type enum, vocabulary lists, worked examples — i.e. their existing `references/*.md` promoted to a machine-checkable contract | Remotion does exactly this as a product feature: AI-ready markdown docs and installable per-topic **"skills"** packages for coding agents (`npx remotion skills add`), each versioned as an npm package `[verified]`. In the same niche, `stickman-animation-agent` ships its rules as `SKILL.md` files ("Use fixed vocab for poses/expressions", "LLM emits `compositions/scene-{NN}.json`") plus a `scene-schema.json` the renderer validates `[verified]`. The measured argument for keeping that contract *small* is the context literature: RULER (only half of models claiming ≥32K hold up at 32K) and arXiv 2510.05381 (input length alone hurts, even with perfect retrieval) `[verified]` | Hours. `engine-api.md` (6.3 KB) + `style-bible.md` (13 KB) already exist `[measured]`; what's missing is the machine-checkable half: an enum dump of `POSES`/`EXPR`/`BASE_MOODS`/sfx/music moods and a schema for `template`+`params`. Note the trap: prose guidance is *not* validation — `style-bible.md` states the shot-type proportions, but nothing enforces them | It changes nothing about the render or the format; docs-only leaves the code-writing step intact. It only pays off combined with 1f/2/4 | **RELOCATES intelligence into a contract; prerequisite for 4** |

---

## 3. Which options remove the cost and which relocate it

* **Genuinely removes structure:** 1f (manifest+params), 2 (templates), 7 (bigger primitives), 8 (codegen).
* **Genuinely removes the tuning loop:** 5 (scrub-over-params), 9 (review ergonomics), 10 (puppeteering).
* **Removes typing but adds a harness and a retry tax:** 3, 3b, 4.
* **Relocates only:** 1d/1e (JSON so large and machine-shaped that no human reads it), 6 (today).
* **Non-starters under the stated constraints:** 1a, 1b, 1c (engine replacement — his standing rule says an
  external repo is merge material, never a replacement, and all three would delete `engine/`, the rigs, the
  grade, `audio/`, `beats.py` and `style_lock` in favour of a foreign scene graph), 11 (no training compute),
  1e specifically (binary assets break the SHA-256-still + text-diff workflow he built his QA around).

One honest warning that applies to **every** templating option (2, 4, 1f): the platform they publish on
demonetises "repetitive or mass-produced" content `[verified]` YouTube channel-monetisation policy, 2025-07-15
update, and their own `production-qa.md` §10 lists "Distinct story, not another instance of the same template"
as a check item. So the template library must stay *small and named* (the 12 archetypes) and the hero shots
must stay hand-written, or throughput is bought with monetisation risk.

---

## 4. Ranked recommendation — the cheapest 2–3 that would actually move the needle

### 1st. Template + slot interpreter driven by `shots.json` `template` + `params` (options 1f + 2 + 7)

Why this is first: the renderer **already** interprets data and **already** passes `shot.params` into every
scene module's `info` (`engine/player.js:74`), and nobody uses that channel. The archetype vocabulary and
their usage proportions are **already written** in `style-bible.md`. The remaining work is one new additive
file per layer (a template registry + `scenes/templates.js`), which touches none of the protected paths and
keeps `draw(g, t, info)` pure — so frame f remains a function of (f, JSON), which is exactly what the
SHA-256 style locks need.

Payoff, using the measured 25.2 lines and ~30–110 numbers per shot: for the boilerplate shots that dominate
an episode (medium two-shot, over-shoulder, giant face, insert, pull-out bookend, freeze-frame, title/end
card ≈ the style bible's own 70–80% mix), structure drops from ~25 lines to one JSON entry; hero shots stay
hand-written by design. Also kills the import bookkeeping that is currently 17% dead weight, and it is the
precondition for options 4, 5 and 6 becoming useful.

Cost: one focused session (comparable to the acting-pass itself, but amortised across the series). Acceptance
test that fits their existing discipline: re-render one already-locked episode through the templates and diff
the stills — a template that reproduces `s002`/`s004`/`s013` inside the locked tolerance is done; one that
doesn't is a bug, not a style choice. (Note: templates change pixels, so the lock must be re-baselined once,
with the approval recorded via `style_lock.py snapshot --approved-by`.)

### 2nd. Data-only constrained generation against that schema (option 4)

Why second: it is the only generation mode that fits the compute ceiling. A template-tuning request costs the
model a 2–4K-token schema plus one nearest example and a 200–400-token JSON answer — which turns the local
prefill-bound problem from "write 25 lines of JS inside a 15K-token context" (where RULER-style context
degradation and a ~15 GB Q4 weight file make it fragile at best) into "fill these slots in a shape you have
seen four times". The InCoder result (69.0% slot-filling vs 48.2% write-from-scratch) is the mechanism, not a
metaphor: templates change *how* the model generates.

Non-negotiable guard rails: (i) schema validation against the fixed vocabularies (27 poses / 18 expressions /
8 moods / 5 transitions / sfx+music mood lists — all machine-enumerable from `engine/`), (ii) the existing
`SHOT ERROR` capture turned into a hard failure (today `render.mjs` prints errors and still exits 0),
(iii) `style_lock.py check` as the drift gate, (iv) a per-shot 430p preview pass instead of a full render.
And keep it honest: ManiBench's best temporal-alignment score (60.47% at ≤8% deviation) says the machine gate
can certify *validity*, never *meaning*; `production-qa.md` §9's "a green machine check is not acceptance"
stays the last line.

### 3rd. Review ergonomics: one-shot scrub + annotated contact sheet (option 9, feeding 5)

Why third: the session wasn't consumed by typing 327 lines — it was consumed by write→render→look→change→
look cycles on ~100 numbers per shot. A tool that renders a single shot at `--scale 0.5`, lets him drag
`start/end/gaze/gesture_on/push` (i.e. the `params` of a template) and writes the accepted numbers back into
`shots.json`, plus a per-shot annotated sheet, removes the loop's cost without touching the engine at all —
and it is exactly the pattern Remotion ships as "Edit default props visually" and the community extends with
`remotion-annotate`. Full GUI keyframe editors (option 5 proper) are the same idea done expensively and
somewhere else; this is the cheap local version.

**Explicitly not recommended now:** any engine swap (1a/1b/1c), Rive/Lottie as the shot format (1d/1e),
fine-tuning (11), and pose-from-video (12). Free-form LLM scene-code generation without the template layer
(3, 3b) is the most expensive way to buy the smallest improvement on this machine.

---

## 5. Cost arithmetic behind the ranking (estimates, labelled as such)

Inputs are the owner's stated facts: 100M-token pool, metered per token, no cache discount, 500K tok/min
cap; local prefill-bound; 2-min episode ≈ 100–150 shots.

| Mode | Tokens/shot (in + out, incl. retries) | Tokens/episode (150 shots) | Episodes from 100M pool |
|---|---|---|---|
| Free-form JS, 12–20K prompt + ~1.2K out, ~3 tries | ~40–65K `[estimate]` | ~6–10M | **10–16** |
| Data-only vs template schema, 3–6K prompt + 0.3K out, ~2 tries | ~7–13K `[estimate]` | ~1–2M | **50–100** |

The 40KB of generator-facing docs they already ship (`engine-api.md` 6.3KB, `style-bible.md` 13KB,
`SKILL.md` 9.2KB) `[measured]` is the whole "context tax" — Remotion's move of publishing markdown/`llms.txt`
slices and versioned per-topic "skills" packages `[verified]` is the industry form of the same idea, and
here it argues for **shrinking** the required context to a schema rather than growing the model.

Local model note (estimate, not a measured claim): a 27B Q4_K_M GGUF needs roughly 15–16 GB for weights
alone, which leaves no room for KV cache inside 16 GB — consistent with the guide's own warning that the LLM
server and the render compete for commit headroom (`STICKMAN_VIDEO_GUIDE.md` §4 and §7). That, not the
quantisation itself (arXiv 2410.14766 found 4-bit 7B beating FP16 sub-3B, with collapse only at 2-bit
`[verified]`), is why the local lane should be restricted to small-context param authoring.

---

## 6. Claims I could verify against primary sources

See §8. Marked `[verified]` above = I read the vendor doc, repo tree, spec, or the paper text itself in this
pass.

## 7. Claims I could NOT verify (stated plainly)

1. **"Reanime"** — I could not find any animation-authoring product by this name. `reanime.dev` failed to
   resolve; a GitHub repository search for `reanime` returned only anime-streaming APIs/tools. The closest
   real things are **Revideo** (open-source TS programmatic-video framework) and Motion Canvas. If "Reanime"
   is a specific tool the owner has in mind, everything I said about it is unknown, not favourable.
2. **Manimator's headline success percentage** — the paper's *pipeline shape* is confirmed from its own
   text (LLM writes Manim code → it is executed via the Manim library → static analysis and a sandbox gate
   the result); **two attempts to re-read its end-to-end success figure were blocked mid-session, so no
   number from Manimator is used anywhere in the ranking.** Its failure taxonomy is likewise unverified, and
   it is *paper→diagram* animation, not narrative acting.
3. **InCoder's 69.0% vs 48.2%** — verified as a snippet quoting the paper's HumanEval *line-infilling*
   result. It is a 2023-era model on a toy task; the *direction* supports slot-filling authoring, the
   magnitude should not be ported into a business case.
4. **"Fill-in-the-blank beats writing from scratch for modern instruct models"** — no head-to-head study on
   current frontier coders was found in this pass. My ranking assumes the direction holds; it is not
   measured here.
5. **Remotion licence employee threshold** — the licence page states "completely free to use for any
   individual or small company — no catch. For bigger companies, we charge a license fee." `[verified]`. The
   widely cited "3 or fewer employees" wording appears in Remotion docs pages but I did not read the
   definitive clause; confirm before relying on it. (Moot for him as an individual, relevant only if he hires.)
6. **Motion Canvas GPL relicensing** — the repo is currently MIT `[verified]` via GitHub API; the GPL
   discussion is real but I did not read its conclusion.
7. **Any measured *authoring-throughput* number for any option.** No source I found reports "shots authored
   per hour, before vs after adopting X". The Manim/ManiBench/TestGen/Agentless numbers are *correctness and
   cost* numbers. That is the honest state of the literature: this specific question is not benchmarked, and
   the only way to get a real number for his pipeline is to instrument one episode (lines typed, numbers
   changed, render loops per accepted shot) while building the template layer.
8. **Token figures for the paid "FreeModel Basic" lane and the local model's prefill rate** — these are his
   stated facts, not mine; the §5 arithmetic inherits them unverified.
9. **Whether templates change pixels enough to break existing locks** — I asserted a re-baseline is needed;
   it follows logically from `style_lock.py check` requiring byte-for-byte PNG equality, but I did not render
   anything to measure it (renders were out of scope for this pass).

## 8. Sources

Primary (read this pass):

* Repo-local evidence (read-only, no modification): `E:\Local_Mis_WS\_yt_stickman\aitrends-2d-studio\` —
  `engine/core.js`, `engine/player.js`, `engine/rig2d.js`, `engine/fx2d.js`, `engine/ui2d.js`,
  `engine/styles.js`, `render.mjs`, `projects/acting-pass/story/shots.json`,
  `projects/acting-pass/scenes/{blocking.js,shots/*.js,sets/kitchen.js}`, `projects/acting-pass/build/report.json`,
  `tools/{beats.py,style_lock.py,render_cached.py,render_report.py,verify_kit.py,doctor.py,motion_audit.py}`,
  `docs/{MOTION_BASELINE.md,production-qa.md,symbolic-beats.md,packaging-playbook.md}`,
  `E:\Local_Mis_WS\STICKMAN_VIDEO_GUIDE.md`,
  `E:\Local_Mis_WS\_yt_stickman\plugin\skills\make-2d-video\{SKILL.md,references/engine-api.md,references/style-bible.md}`.
* Declarative/code-authoring engines: [Motion Canvas](https://motioncanvas.io/) ("Write animations in
  TypeScript with your favorite IDE; … editor providing a real-time preview"),
  [motion-canvas/motion-canvas repo](https://github.com/motion-canvas/motion-canvas) and its
  [relicensing discussion](https://github.com/orgs/motion-canvas/discussions/1015),
  [Remotion](https://www.remotion.dev/), [Remotion licence](https://www.remotion.dev/license),
  [Remotion: Building with AI](https://www.remotion.dev/docs/ai),
  [Remotion: Prompting videos with coding agents](https://www.remotion.dev/docs/ai/coding-agents),
  [Remotion: Edit default props visually](https://www.remotion.dev/docs/visual-editing),
  [Remotion Studio CLI](https://www.remotion.dev/docs/cli/studio),
  [remotion-annotate](https://github.com/Alan-Lucena/remotion-annotate),
  [Revideo](https://re.video/) (→ https://midrender.com/revideo).
* Animation data formats: [Lottie format spec / LottieFiles docs](http://docs.lottiefiles.com/en/format/lottie-json),
  [airbnb/lottie After Effects support notes](https://github.com/airbnb/lottie/blob/master/after-effects.md),
  [Rive web runtime docs](https://rive.app/docs/runtimes/web/web-js), [Rive features](https://rive.app/features),
  [Rive issue on the binary .riv format](https://github.com/rive-app/rive-flutter/issues/371),
  [Motionity](https://github.com/alyssaxuu/motionity),
  [tomaslachmann/motion-editor](https://github.com/tomaslachmann/motion-editor),
  [OpenToonz CLI](https://morevnaproject.org/2016-11-27/use-opentoonz-cli/),
  [Blender command-line rendering](https://docs.blender.org/manual/en/latest/advanced/command_line/render.html).
* Same-niche pipelines (evidence for options 1f/2/4):
  [chrisaswain/stickman-animation-agent](https://github.com/chrisaswain/stickman-animation-agent) —
  MIT; `src/compositor/scene-schema.json` (scene `type` enum, camera `initial`+`moves`, timeline events
  `time/target/action/duration/params`, min-duration and scene-ID pattern validation),
  `skills/scene-compositor/SKILL.md` ("LLM emits `compositions/scene-{NN}.json`… fixed vocab for
  poses/expressions… deterministic JS renders final HTML/SVG/GSAP"), `character-library/presets/*.json`,
  `components/characters/tier1|tier2/**.svg`, `templates/{classic-stickman,comic-panel,whiteboard}/template.json`,
  `tests/e2e-pipeline-test.js`;
  [kaomei/stickman-video-director](https://github.com/kaomei/stickman-video-director) (MIT; Director vs
  Autopilot modes — the same fork the local `style_lock.py`/`render_cached.py`/`render_report.py` ideas were
  adopted from, per their docstrings);
  [saiedpod-bot/Stickman-Studio](https://github.com/saiedpod-bot/Stickman-Studio).
* LLM code generation + verification:
  [ManiBench, arXiv 2603.13251](https://arxiv.org/html/2603.13251v1) and its
  [dataset card](https://huggingface.co/datasets/nabin2004/ManiBench);
  [Manimator, arXiv 2507.14306](https://arxiv.org/html/2507.14306v1);
  [Training and Agentic Inference Strategies for LLM-based Manim Code Generation, arXiv 2604.18364](https://arxiv.org/html/2604.18364v2);
  [VUTE / Video-based Multimodal Explanations for LLM Theorem Explaining, arXiv 2502.19400](https://arxiv.org/html/2502.19400v2);
  [Meta TestGen-LLM, arXiv 2402.09171](https://arxiv.org/abs/2402.09171);
  [Meta ACH mutation-guided test generation, arXiv 2501.12862](https://arxiv.org/html/2501.12862v1);
  [Agentless, arXiv 2407.01489](https://arxiv.org/html/2407.01489v1);
  [Teaching LLMs to Self-Debug, arXiv 2304.05128](https://arxiv.org/html/2304.05128v2);
  [InCoder, arXiv 2204.05999](https://arxiv.org/html/2204.05999v3);
  [LiveCodeBench](https://proceedings.iclr.cc/paper_files/paper/2025/file/94074dd5a072d28ff75a76dabed43767-Paper-Conference.pdf);
  [HumanEval Pro / MBPP Pro self-invoking codegen, arXiv 2412.21199](https://arxiv.org/html/2412.21199v1).
  Counter-evidence on constraints and benchmarks:
  [Let Me Speak Freely?, arXiv 2408.02442](https://arxiv.org/abs/2408.02442);
  [Grammar-Aligned Decoding, NeurIPS 2024](https://arxiv.org/html/2405.21047v4);
  [Grammar-constrained decoding in industry, ACL 2025](https://aclanthology.org/2025.acl-industry.34.pdf);
  [How LLMs game SWE-bench Verified](https://kaitchup.substack.com/p/how-llms-game-swe-bench-verified).
* Local-model feasibility:
  [Evaluating Quantized LLMs for Code Generation, arXiv 2410.14766](https://arxiv.org/html/2410.14766v1);
  [RULER](https://openreview.net/forum?id=kIoBbc76Sy) / [NVIDIA/RULER](https://github.com/NVIDIA/RULER);
  [Context Length Alone Hurts Performance, arXiv 2510.05381](https://arxiv.org/html/2510.05381v1);
  [Qwen3-Coder-Next report](https://arxiv.org/html/2603.00729v1) and [blog](https://qwen.ai/blog?id=qwen3-coder-next);
  [Qwen3-Coder-30B-A3B SWE-bench repro discussion](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct/discussions/30);
  [SambaNova: are LLMs truly solving software problems — or are agents doing it?](https://sambanova.ai/blog/are-llms-truly-solving-software-problems).
* Performance capture / puppeteering:
  [Video Puppetry: A Performative Interface for Cutout Animation (ACM TOG 2008)](https://gfx.cs.princeton.edu/pubs/Barnes_2008_VPA/index.php);
  [Real-time Pupil Tracking from Monocular Video for Digital Puppetry, arXiv 2006.11341](https://arxiv.org/abs/2006.11341).
* Platform constraint: [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392?hl=en)
  (2025-07-15 "repetitious content" update: repetitive or mass-produced).
