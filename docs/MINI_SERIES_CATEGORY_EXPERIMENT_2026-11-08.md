# Multi-Category Audience Experiment — Decision Document
**8 November 2026 · team-lead synthesis · companion to `MINI_SERIES_MARKET_RESEARCH_2026-11-08.md` and `MINI_SERIES_TEMPLATE_PLAN.md`**

---

## 0. Direct answers

**"Can we run 3–4 categories × 5 videos in parallel to see what people actually like, instead of guessing?"**
Yes — the instinct is correct and better than guessing. **But the proposed design as stated will not produce trustworthy data.** Three changes are required: (1) measure retention, not views; (2) randomise and hold everything else constant; (3) stage the test so you spend 4 videos before spending 20.

**"Can you still explore them [the other topics]?"**
Yes. That is exactly what the experiment does. Vetala Panchavimshati becomes **one arm, not the whole bet**. It remains the recommended lead on prior evidence, but it must earn its place against real alternatives rather than being assumed.

**"Why didn't you load a relevant expert?"**
I tried properly this turn: loaded the `recommend-experts` skill and called the expert-discovery service twice. It returned `search_failed` both times (and had failed three times in the previous session — five failures total). Plugin IDs must come from that service and may never be invented, so **no expert card can be shown**. You can select one manually from the Expert Center in the left sidebar. As a working substitute I created a real agent team (see §6).

---

## 1. The two attached PDFs — assessment

Both were read in full via the `workbuddy-pdf` extraction path (23 and 38 pages). One filename contained an emoji (`✨`) that breaks Git-Bash argument encoding; I copied it to an ASCII path first. This is a read-only note — the originals were not touched.

### 1.1 `Ai Micro Drama MASTER PROMPT ✨.pdf` — usefulness **2/10**

**What it is:** a 23-page ChatGPT/Claude system prompt for generating *photorealistic Korean-drama-style* micro dramas with AI video generators. Five strict phases (10 Hindi titles → Hindi story → character turnaround sheets → scene breakdown → AI video prompts in batches of 10), each requiring explicit user approval before the next.

**Decisive finding:** this file is **already in your workspace** — it is byte-equivalent in content to `_yt_microdrama/prompts.txt` (1,201 lines, same header `MASTER SYSTEM PROMPT ✨ AI KOREAN-STYLE REALISTIC MICRO DRAMA PRODUCTION SYSTEM`, same Phase 1–5 structure, 70 occurrences of "KOREAN"). **It contains zero new information.**

**Direct conflicts with your pipeline:**

| Document says | Your pipeline | Verdict |
|---|---|---|
| "Photorealistic live-action appearance", "Do not create anime, cartoon, illustrated people" | Code-drawn stick figures; no AI image/video generation by design | Hard conflict |
| "Never use narration", "Never use a voice-over narrator", "Never write subtitles or captions" | Kokoro TTS narration + word-synced captions | Hard conflict |
| "Never include music instructions", "Never include sound effects" | `audio/mix.py` is a core stage | Hard conflict |
| "Realistic lip synchronization", "8K", "Netflix-style cinematic" | `STICKMAN_VIDEO_GUIDE.md §8`: no viseme lip-sync, no photoreal humans | Impossible |
| 5 approval gates **per video** | Owner requires no daily work; batched weekly approval only | Hard conflict |
| Scenes of 6–8 s, ~2 min total | 15–25 shots/min ⇒ ~2.4–4 s shots; proven 30–45 s | Misaligned pacing |
| "All instructions and questions in Hindi", "Story titles: Hindi" | Hindi is a genuinely useful signal (66% of Indian micro-drama viewing per Meta–Ormax) | **Adopt as a language decision**, but source it to the survey, not to this prompt |

** salvageable:** the character-consistency discipline (turnaround views, signature details repeated in every scene prompt, "never change costume/face/hairstyle without a recorded reason") maps cleanly onto `scenes/cast.js` + `style_lock.py`; the hook list (unexpected rejection, shocking discovery, secret identity, public confrontation) is usable in the Vetala episode grid. That is all. **Recommendation: IGNORE as a production system; keep two ideas.**

### 1.2 `THE ULTIMATE YOUTUBE NICHE FLIPPING MASTER PROMPT V3(1).pdf` — usefulness **6–7/10** (team-lead 7, `prompt-auditor` 6)

**What it is:** three separate prompts bundled into one 38-page file.
- **A. Niche Flipping (pp. 1–13):** 9 stages — competitor "Viral DNA" reverse engineering → universal formula → 7 discovery lenses → competition/gap investigation → 30-title stress test → weighted scoring (demand 20%, competition 20%, differentiation 15%, packaging 15%, repeatability 10%, feasibility 10%, monetisation 10%) → originality/saturation audit → channel blueprint including a **3-video pilot validation** → three final recommendations.
- **B. Script Retention Blueprint (pp. 15–27):** reverse-engineer a reference script's hook, pacing, open loops, retention beats, midpoint refresh and payoff; write an original script with those structural properties. Explicit factual-accuracy and originality rules.
- **C. Universal YouTube Visual Production (pp. 28–38):** visual DNA → style bible → character consistency → environment system → script-to-visual breakdown → AI image prompts → image-to-video animation prompts → continuity control → quality audit.

**Why it is genuinely useful:**
- Its methodology matches your new question almost exactly. Stage 8I says: *"PILOT VALIDATION — Design a small test using the first three videos … which metrics to monitor … how to interpret weak performance … when to reconsider the niche"*, and *"Avoid arbitrary universal CTR or retention benchmarks. Compare performance against relevant context."* That is the correct instinct you just described, written down before you asked.
- Strong epistemic guardrails: *"Never invent performance data, competitors, or market evidence"*, *"Low competition does not automatically mean high opportunity — a niche with no competitors may simply have no audience"*, *"Do not confuse the opportunity score with the confidence level"*, *"Never guarantee virality, growth, or earnings"*, *"If browsing is unavailable, explicitly mark competition and demand assessments as unverified"*. These align with the labelling convention already used in our research.
- The **30-title stress test** (Stage 5) is a zero-cost paper pre-test for "can this category sustain 30 genuinely distinct episodes" — directly applicable to Vetala (25 tales) and to the three other arms.
- Prompt C's **Phase 8 continuity control** and **Phase 5 script-to-visual breakdown** (10 fields per scene) are structurally the same as our `cast.js` / `sets/*.js` / `shots.json`. The *medium* is wrong (AI image generation), the *data model* is right.

**Limits:** all three prompts target long-form YouTube (Prompt B assumes "2,500 words / 15 minutes"; Stage 1 analyses views vs channel median, thumbnails, subscriber counts). Prompt C assumes AI image/video generators, which our pipeline excludes. It is a reasoning scaffold, **not market research** — it contains no verified statistics, no 2026 data, and no Shorts-specific mechanics. It also assumes a *single* niche decision, not a parallel multi-arm test.

**Recommendation: ADOPT Stage A's scoring/audit/pilot logic and Prompt B's retention blueprint (adapted to 30–90 s); ADAPT Prompt C's continuity data model; IGNORE all AI-image/video generation phases.**

**Nuance from the `prompt-auditor` review (artifact `research/2026-11-08-pilot-lab/01-prompt-audit.md`, 194 lines):** neither PDF *conflicts* with mandatory human approval — both add text-level approval gates — but **neither provides the mandatory rendered-frame watch**. Both are long-form-YouTube prompts repurposable as checklists, not as production systems. The auditor independently verified the 15 Jul 2025 inauthentic-content wording and the 1 Feb 2027 YPP change on primary YouTube Help pages, and found no evidence the PDFs' "Hindi-interface" rule is evidence-based (it is a design choice, not a demand signal).

**Combined bottom line:** neither PDF is market evidence. The first is a duplicate of a file you already have and describes a pipeline you explicitly rejected. The second is a useful *thinking tool* for exactly the experiment you now want — use it as a checklist, not as a source of facts.

---

## 2. Why "5 videos per category, then compare views" fails

Short-form view counts are heavy-tailed. One video that catches the feed can out-view the other 19 combined, so a mean (or even a median) of 5 draws per arm mostly measures luck.

**Monte Carlo check (illustrative model, `[estimate]`, 20,000 runs, log-normal views, seed 20261108 — not measured platform data):**

| True difference between the better and worse category | P(pick the correct winner) using 5-video **median views**, σ=1.2 |
|---|---|
| 1.5× | **0.68** |
| 2.0× | **0.78** |
| 3.0× | **0.89** |

With heavier dispersion (σ=1.6), even a genuine 2× advantage is detected only **71%** of the time — near a coin flip. Switching from mean to median barely helps, because the problem is sample size, not the estimator.

**But a bounded retention metric is far more informative.** With per-video average-percentage-viewed sd = 0.10 and a true +0.10 gain, n=5/arm gives **0.94** probability of picking the right arm; n=8 gives **0.98**. At sd = 0.15 it drops to 0.86 at n=5.

**Design conclusion:** pre-register **median average percentage viewed (or 3-second hold rate)** as the primary metric. Use views/engaged views only as a secondary scale signal. 5 episodes per arm is *adequate for a large retention gap* but underpowered for a subtle one; plan for 8 if the first wave is close.

---

## 3. Recommended experiment design

### 3.1 One channel or four?

**Recommendation: ONE channel, randomised interleaved release.** Reasoning:
- Separate channels isolate the topic signal but each starts with zero audience, zero history and its own OAuth/approval overhead — 4× the setup, and cold-start noise dominates a 5-video sample.
- One channel confounds less than it would for long-form: the Shorts feed distributes largely on **interest signals per video**, not subscriber history. Interleaving is therefore defensible for a first pass.
- Countervailing risk: channel-theme dilution and YouTube's "inauthentic content" policy. Mitigate with distinct storylines per episode, named archetypes, a small template library, and 3–5 hand-written hero shots per film.

### 3.2 Confounds to hold constant

Posting day/time; title template (one formula across all arms); thumbnail composition and colour; episode length; caption font/placement; hashtag set; voice; music mood; hook type; end-card format; release order; and **video age** (earlier uploads accumulate more views — compare at a fixed age, e.g. day 14 after publish, never raw lifetime views). Randomise the arm order with a fixed seed and publish on a fixed cadence.

### 3.3 Pre-registered decision rule (write it down before publishing)

- **Primary:** median **average percentage viewed** at day 14, per arm. `[primary]` The exact YouTube Reporting API metric is `average_view_duration_percentage` — "The average percentage of a video watched during a video playback", which has excluded *looping clips* traffic since 13 Dec 2021. Verified on `developers.google.com/youtube/reporting/v1/reports/metrics`, 8 Nov 2026. There is **no** `average_percentage_viewed` metric under that name.
- **Guardrails:** `engaged_views` ("viewed past the first frame, or the user clicks/taps to play"); likes+shares+comments per 1,000 engaged views; subscriber conversion; zero policy/copyright incidents. ⚠️ **Correction:** the Reporting API exposes **no 3-second-hold or Shorts retention-curve metric** `[primary]`. A "3-second hold" figure is a Studio-UI convenience at best and could not be verified as an exportable metric — do **not** make it a pre-registered primary or guardrail.
- **Double down:** winner's primary metric ≥ 2nd place **+ 0.08 absolute** AND ≥ a pre-set floor agreed before launch (e.g. 45% APV) AND at least 3 of its 5 episodes above the arm's median.
- **Kill:** arm's primary metric below the floor by ≥0.08, or 4 of 5 episodes below floor.
- **Inconclusive:** gap < 0.08 → extend the leading two arms to 8 episodes each; do **not** reinterpret secondary metrics to force a winner.
- **Read metrics only twice:** day 14 and day 28. No daily dashboard — this preserves your "no daily work" requirement.

### 3.4 Stage it: spend 4 videos before spending 20

| Wave | Cost | What it answers |
|---|---|---|
| **0 — paper pre-test (0 videos)** | ~1 session | Use the PDF's 7 lenses + 30-title stress test + weighted scoring to shortlist arms. Kill any category that cannot sustain 30 distinct, sourced episodes. |
| **1 — hook prototypes (4 videos, 1 per arm)** | ~870 lines of scene code, ~8 min render, ~1 h human approval | Does the *opening* of each category hold attention? Cheap elimination. |
| **2 — full arms (4 × 5 = 20 videos)** | ~4,340 lines at 40 s / 10 shots, ~38 min render, ~5 h human QC | Which category sustains retention across a season arc? |
| **3 — scale the winner** | templates amortise the cost | Continue on the winning track. |

Wave 1 is the single highest-value change to your proposal: it converts a 20-video bet into a 4-video bet with most of the information.

### 3.5 The four arms (all public domain, low sensitivity)

| Arm | Category | Why it is a real alternative | 30-title sustainability |
|---|---|---|---|
| **A** | **Vetala Panchavimshati** (Vikram–Vetala) | Native riddle/cliffhanger, two recurring stick figures, frame-story season payoff, recommended lead | 25 core tales + frame episodes; tight but viable |
| **B** | **Regional epic variants** (Kamba Ramayanam, Sarala Mahabharata, Pampa Bharata, Villiputhurar, Kashiram Das, Ramakien) | "Familiar IP, fresh angle" — recognition plus genuine novelty; tests whether familiarity beats obscurity | Deep; dozens of divergent episodes |
| **C** | **Kathasaritsagara / Jataka / Panchatantra / Jain avadana** | Moral puzzles and animal casts — cheapest to draw, tests whether fable structure beats frame-story suspense | Very deep; anthology risk (weak arc) |
| **D** | **Non-Indian obscure epics** (Gilgamesh, Kalevala, Popol Vuh, Shahnameh side-tales) | Control arm: tests whether the *Indian mythology* framing itself is the draw, or simply "obscure knowledge" | Deep; weaker cultural pull in India |

Five-episode grids per arm are specified in the team artifact `research/2026-11-08-pilot-lab/02-experiment-design.md`.

---

## 4. What it costs — measured and estimated

**Measured from the repo** (`projects/*/story/shots.json` + `scenes/shots/*.js`, 8 Nov 2026):

| Project | Shots | Duration | Scene-code lines | Lines/shot |
|---|---|---|---|---|
| acting-pass | 13 | 17.99 s | 327 | 25.2 |
| char-lab | 3 | 8.73 s | 75 | 25.0 |
| dialogue-call | 7 | 13.61 s | 120 | 17.1 |
| one-more-night-9x16 | 13 | 17.99 s | 328 | 25.2 |
| stomach-acid | 10 | 29.91 s | 158 | 15.8 |

Mean **21.7 lines/shot**. Render rate ~21 s of finished video per machine-minute (`STICKMAN_VIDEO_GUIDE.md §6`).

**`[estimate]` illustrative cost:**

| Design | Videos | Scene-code lines | Render | Human QC @ 15 min/ep |
|---|---|---|---|---|
| 4 arms × 1 (wave 1) | 4 | ~870 | ~8 min | ~1 h |
| 4 arms × 5 @ 40 s / 10 shots | 20 | **~4,340** | **~38 min** | **~5 h** |
| 4 arms × 5 @ 65 s / 20 shots | 20 | **~8,680** | ~62 min | ~5 h |

**The machine is not the bottleneck.** Rendering 20 episodes takes about an hour; authoring 4,300–8,700 lines of scene code and watching 20 films is the cost. This is the strongest possible argument for building the template + `params` interpreter **first**: `engine/player.js:74` already injects `shot.params` and **zero projects use it**. With a 12-archetype registry, the boilerplate ~70–80% of shots become one JSON entry each, and cross-arm reuse (one cast, one night-forest set, one voice pair, one music palette) collapses the marginal cost of arms B/C/D.

**"In parallel" technically:** `render.mjs` already uses parallel workers. Concurrent *renders of separate projects* are risky because of the commit-headroom rule (a loaded 15 GB GGUF `llama-server` reserves ~26.56 GB and breaks ffmpeg/MKL; need ≥6 GB). Use a **cloud LLM for authoring** to remove that conflict entirely, then render episodes **sequentially in one batch** — 38 minutes is short enough that concurrency buys nothing.

### Must exist before wave 2

1. `scenes/templates.js` — 12 named archetypes driven by `template` + `params`. Zero edits to protected paths.
2. **Hard-fail `render.mjs`** — today it prints `SHOT ERROR` and still exits 0; an unattended batch could ship ERROR-painted frames.
3. `style_lock` + `approved_by` populated (both shipped `report.json` currently `null`).
4. Batched approval review pack (contact sheets + previews), so 20 films need one sitting, not 20.
5. Scheduled upload with `privacyStatus=private` until approved.
6. Distinct storyline per episode, to stay clear of the "mass-produced, generic, repetitive" ineligibility rule.

---

## 5. Risks to accept explicitly

- **Policy:** 15–20 templated uploads in a short window is the exact pattern the 15 Jul 2025 "inauthentic content" update names. Distinct stories and visual variety are a monetisation control, not decoration.
- **Statistics:** a 5-video arm can only detect large effects. If wave 2 is close, extend to 8 per arm rather than declaring a winner.
- **Time:** 20 episodes still means ~5 hours of human watching, batched. That is compatible with "no daily work" but not with "zero work".
- **Money:** none of this tests monetisation. YPP thresholds are separate (from 1 Feb 2027: 8,000 watch hours or 20M Shorts views for new applicants; 10M qualified views/90 days for Shorts Creator Pool earnings). The experiment measures **interest**, not revenue.
- **Data honesty:** record the randomisation seed, the pre-registered rule, and all raw per-episode metrics in `research/2026-11-08-pilot-lab/` before looking at results. Do not change the rule afterwards.

---

## 6. Capabilities actually loaded this turn

| Category | What was loaded | Result |
|---|---|---|
| Skills | `recommend-experts`, `workbuddy-office-routing`, `workbuddy-pdf`, `agent-team-orchestration`; previously `deep-research`, `audit-claim-validation` | Used for routing, PDF extraction, expert discovery, team setup |
| Expert | `search_plugins` type=expert, 2 calls | **Service failed (`search_failed`), 5 failures across the session. No card shown — IDs cannot be invented.** Manual selection via Expert Center remains open |
| Connectors | `list_installed_plugins` (none installed), `mcp.json` (`mcpServers: {}`) | No connector fits; deliberately no card |
| Agent team | `TeamCreate` → team `miniseries-pilot-lab`; 3 named teammates: `prompt-auditor`, `experiment-designer`, `pipeline-analyst`, each with a distinct artifact path | Running; artifacts in `research/2026-11-08-pilot-lab/` |
| Verification | Both PDFs read in full; primary YouTube Help pages verified in the prior research pass; local file inventory recomputed; Monte Carlo power check run locally | Documented above |

Deliberately **not** loaded: AI image/video generation, deployment/publishing plugins, and engine-replacement frameworks — all contradict the code-drawn, offline design.

---

## 7. Decisions needed from you

1. **Approve the staged design** (wave 1 = 4 videos before wave 2 = 20), or insist on the full 20 immediately.
2. **Approve the four arms**, or swap arm D for a non-mythology knowledge control.
3. **Fix the pre-registered floor** (e.g. 45% average percentage viewed) before any video is published.
4. **Order of work:** build the template interpreter first (recommended), or hand-write wave 1's four episodes to get data sooner.
5. **Language:** Hindi-first (66% of Indian micro-drama viewing per Meta–Ormax) vs English — the first PDF's Hindi mandate is a useful prompt, but the survey is the evidence.
