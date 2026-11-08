# Mini-Series Market Research — 8 November 2026

**Commissioned question.** A creator with a working, fully local, code-drawn stick-figure animation pipeline wants to know: (1) what episode length the market currently uses and whether it is "in sync with humans"; (2) what is trending and whether the mini-series market is doable; (3) whether a near-passive, monetised operation is achievable with a one-time setup effort and only occasional decisions; (4) whether to open with Ramayana/Mahabharata or with lesser-known epics/mythology carrying a knowledge payload.

**Method.** Four parallel research agents (episode length + market size; trends + monetisation + policy; content/IP; automation + local pipeline audit), one delegated multi-source market synthesis, and direct verification of four primary YouTube Help pages. No renders, installs or source edits were performed.

**Confidence labels used throughout.**
- `[primary]` — read directly on the platform's own help page or statute text, 8 Nov 2026.
- `[measured]` — a stated sample, methodology and result from a named study.
- `[industry]` — trade/industry figure relayed by a named research firm or press outlet; not independently auditable.
- `[estimate]` — reasoned projection by us, assumptions stated.
- `[unverified]` — widely repeated claim we could not substantiate.

---

## 0. Executive verdict

1. **Episode length:** the market has converged on **60–120 seconds**, with 2026 pressure toward **58–90 seconds**. That is an *algorithmic and unit-economics optimum*, not a biological attention-span fact. The "8-second attention span" is debunked; the "3-second rule" is vendor guidance, not a measured retention law.
2. **Your pipeline is proven at 13.6 s and 29.9 s, not 60–90 s.** At 15–25 shots/minute, a 60 s episode needs ~15–25 shots, i.e. roughly 380–630 lines of hand-written scene code at your measured 25.2 lines/shot. **The template + `params` interpreter is a prerequisite, not an optimisation.**
3. **Market:** genuinely large and fast-growing (global ~$11B in 2025 → ~$14B projected 2026), but **India is a traffic market, not a revenue market**. India-specific size estimates disagree by ~4× depending on definition. App-scale economics (paid acquisition, 80–90% of titles failing to recoup) do **not** describe a solo creator with $0 marginal production cost — but neither do they guarantee revenue.
4. **Monetisation is the weak link, not production.** Shorts ad RPM is roughly $0.01–$0.20 per 1,000 views (~$30–$200 per 1M monthly views `[estimate]`). From **1 Feb 2027**, earning from the Shorts Creator Pool requires **10M qualified Shorts views in the trailing 90 days** `[primary]` — about 111,000 views/day sustained. Shorts alone are unlikely to produce meaningful passive income. A ladder to long-form, fan funding and licensing is required.
5. **Automation:** **partially achievable, not "set it up once and walk away".** After a concentrated engineering block, a **batched weekly approval session of ~15–45 minutes** is a realistic floor. Zero recurring human decisions is not achievable — your own repo mandates human approval, and YouTube demonetises the template mill that zero-touch volume produces.
6. **Content:** **do not open with a straight Ramayana/Mahabharata retelling.** Open with an obscure, public-domain **frame-tale cycle — Vetala Panchavimshati (Vikram–Vetala)** — then use regional epic variants as Season 2. Rationale: built-in cliffhangers, two recurring stick figures, low saturation, low religious sensitivity, and a natural "you learned something obscure" knowledge hook that aligns with YouTube's own "enjoyment or education" wording.

---

## 1. Episode length and the "in sync with humans" question

### 1.1 What creators actually ship

| Format | Episode length | Episodes / season | Source / label |
|---|---|---|---|
| Chinese duanju / app micro-drama | 1–2 min (60–120 s) | 20–100 (ReelShort typically 70–80) | Wikipedia *Duanju*; TenSquared Capital, 2026 `[industry]` |
| 2026 convergence | 58–90 s | 60–100 | DataEye/industry summaries, 2026 `[industry]` |
| India (Meta–Ormax definition) | 60–180 s | — | *Micro Dramas: The India Story*, Nov 2025–Jan 2026 `[measured]` |
| India (Kuku TV product definition) | ~2 min | 45–50 per 90–100 min story | Redseer/Lumikai relay `[industry]` |
| Meta's own social-native microdrama | short Reels | **7 episodes**, alternate-day release from 4 Sep 2025 | Meta Newsroom, 2 Sep 2025 `[primary/industry]` |
| Social-native "Part 1 / Part 2" series | bounded by platform cap, usually <3 min | no verified distribution | `[unverified]` |

**Douyin's 2026 rule** `[industry]`: vertical live-action episodes capped at 3 minutes, with a *recommendation* of ~90 seconds. The cited internal Q1 2026 test claims ~90 s episodes were **2.7× more likely to be watched to completion** than >3 min episodes, with ~40% higher paid-traffic ROI. This is platform-internal commercialisation data relayed by trade press — directional, not an independent study.

**India viewing behaviour** `[measured]`: Meta–Ormax surveyed 2,000 personal interviews + 50 depth interviews across 14 states, ages 18–44, Nov 2025–Jan 2026. Median **3.5 h/week** across **7–8 short sessions**, median session **~30 min**, **8 pm–midnight** peak (60% of weekday viewing), **90% watch solo**, and **89% discover the category through social feeds** rather than search. Casual viewers reportedly need a strong **first 10–20 seconds** — a qualitative survey interpretation, not a retention curve.

### 1.2 Are humans "synced" to these lengths? No — and that matters

- **The "8-second attention span" is a myth.** King's College London's Policy Institute / Centre for Attention Studies calls it "thoroughly debunked", states "there being no real evidence that this is the case", and notes a "lack of long-term studies means we can't tell whether attention spans have actually declined". Survey: 2,093 UK adults, 24–26 Sept 2021. 50% of UK adults believed the myth; 25% correctly rejected it `[measured]`.
- **The "3-second rule" is not measured.** We found no primary measured 3-second or 6-second drop-off percentage. It is vendor guidance (e.g. Sprout Social's 2026 TikTok algorithm guide). A widely circulated "50–70% of drop-off happens in 3 seconds / 6-second completion 27% vs 12%" set comes from Chinese paid-acquisition benchmarks `[industry]` — real to media buyers, not a human universal.
- **The real constraint is economic, not cognitive.** The industry benchmarks that matter are *completion rate and payback*: first-episode completion below ~75% breaks paid-acquisition economics; paywall conversion averages 2–5% `[industry]`. Shorter episodes produce more completion events per minute of footage — a platform-incentive arbitrage, not an attention limit.
- **Counter-evidence:** a National Geographic headline claims an average attention span of "roughly 40 seconds" `[unverified]`; the underlying study could not be verified and the claim conflicts with KCL. Do not use it as a planning number.

**Conclusion:** pick 60–90 s because the *feed algorithm and the completion metric* reward it, not because viewers cannot concentrate longer. This also means a knowledge series can safely use a 3–5 s context card and a slightly slower reveal without violating any human limit.

### 1.3 Platform caps — verified from primary pages

| Platform | Cap | Verification |
|---|---|---|
| YouTube Shorts | Square/vertical videos **up to 3 minutes** uploaded on/after **15 Oct 2024** are categorised as Shorts and **can be monetised in the Shorts revenue-sharing model** | `[primary]` support.google.com/youtube/answer/15424877 |
| YouTube Shorts | A Short **over 1 minute with any active copyright claim** is blocked globally and is not monetisable | `[primary]` same page |
| Instagram Reels | ~3 min | `[industry]` secondary, re-confirm before launch |
| TikTok | up to 10 min | `[industry]` secondary, re-confirm before launch |

**Two consequences specific to your pipeline:**
1. Your `audio/mix.py` generates music and SFX locally with numpy. With **no licensed music track**, **100% of the revenue associated with your engaged views goes into the Creator Pool** (YouTube splits it away only when partner music is used) `[primary]`. That is a structural advantage over music-backed Shorts.
2. Because you generate all audio yourself, the ">1 min + claimed content = blocked" rule should not trigger. Keep `THIRD_PARTY.md` provenance intact to prove it.

### 1.4 The gap between the market and your renderer

Your measured baseline: 13.6 s / 7 shots and 29.9 s / 10 shots, rendered in 41 s and 84 s respectively at 1080p. Your style bible requires **15–25 shots per minute**. Therefore:

| Target | Shots needed | Scene code at 25.2 lines/shot | Numeric literals at 30–110/shot |
|---|---|---|---|
| 30 s (proven) | 8–12 | ~200–300 lines | 240–1,320 |
| 60 s | 15–25 | ~380–630 lines | 450–2,750 |
| 90 s | 23–38 | ~580–960 lines | 690–4,180 |

Rendering cost is roughly linear and cheap (~21 s of finished video per machine-minute). **Authoring and QC are the bottleneck**, not the render. A 60–90 s series at 3 episodes/week is not sustainable with hand-written scene code. This is precisely why the template interpreter is the first engineering task.

---

## 2. Market size, trends, and "is it doable?"

### 2.1 Size — with the contradictions left visible

| Figure | Base year | Source / label |
|---|---|---|
| Global micro-drama revenue **~$11B → ~$14B projected 2026** | 2025 | Omdia via TenSquared Capital / Sensor Tower relays `[industry]` |
| China **~83%** of global revenue | 2025 | TenSquared `[industry]` |
| Ex-China **$1.4B (2024) → $9.5B (2030)**, 28.4% CAGR | 2024 | Media Partners Asia via Variety, 16 Sep 2025 `[industry]` |
| Ex-China **$3.6B (2026) → $9.5B (2031)** | 2026 | MPA via Goldscene `[industry]` |
| ReelShort revenue **$97M (2023) → $400M (2024) → $785M (2025) → ~$1.05B projected (2026)** | — | MPA `[industry, forecast]` |
| Short-drama apps added **5.78B viewing hours** and **$2.98B IAP** in 2025 (+115% YoY) | 2025 | Sensor Tower *State of Mobile 2026* `[industry]` |
| India **crossed $300M in 2025**, 450M downloads, 100M MAU, **→ $4.5B by 2030** | 2025 | Lumikai *State of India Interactive Media 2025*, via Mint, Mar 2026 `[industry]` |
| India **₹650 crore in 2025 → ₹2,320 crore by 2028** (>50% CAGR) | 2025 | FICCI-EY, via The Videshi `[industry]` |
| India **₹2,300 crore FY26 → ₹4,600 crore FY27** | FY26 | Redseer `[industry]` |
| India **~$300M (2025) → $4.5B (2030)**, ~31% CAGR | 2025 | Lumikai `[industry]` |

⚠️ **Do not add or compare these directly.** ₹650 crore (~$78M) and $300M differ by ~3.8× for the same year — different definitions (subscription revenue vs total category spend, calendar year vs fiscal year). All market sizes are industry estimates, not audited figures. MPA said in Sept 2025 that India "remains in an exploratory phase" while Lumikai describes a $300M market; both can be true under different scopes.

### 2.2 India: traffic, not revenue

- India was **11% of global micro-drama app downloads in Q1 2025** but the US was ~3% of downloads and **37% of IAP revenue** `[industry]`. In 2026 Q1, South-East Asia + LatAm + India supplied **77% of global downloads**.
- **99% of FY26 Indian micro-drama revenue is subscription / per-episode payment**; advertising revenue was negligible and ad infrastructure is immature (fill rate ~24–28%) `[industry, Redseer]`.
- Kuku Technologies FY26: revenue ~₹1,484 crore, subscription 99.3%, **marketing spend ~74% of revenue**, EBITDA margin ~5.6% `[industry]`. Pocket FM's Pocket TV shut down after ~6 months; its founder said acquisition was not the problem, **retention was**.
- Audience: ~70% male, ~80% aged 18–34, 60–75% from non-metro, **>75% of consumption from Tier-2/3**, ~50% preferring regional-language content `[industry]`. Hindi 66%, Tamil 9%, Telugu 8%, Kannada 7%, Bengali 3% in the Meta–Ormax language split `[measured]`.
- Supply: 40–45 competing platforms, ~500 new episodes/month, ~800 hours of originals in 2025; **funding fell ~70% in 2026** with tail-platform consolidation `[industry]`.

### 2.3 What is actually trending

- **Genre mix (overseas top-100 tags, July–Aug 2026):** romance/emotion **72%**, underdog comeback 30%, urban 14%, revenge 12%, werewolf 10%, CEO 10% `[industry, CAAIP]`. CEO/urban romance is **saturating** ("sweet-pet" romance downloads down 37% in North America); the formula is shifting to "CEO + X" and supernatural.
- **Monetisation mix is flipping:** in China, free/ad-supported (IAA) is now ~**71% of monetisation** and ~**2/3 of market size**; overseas still ~**85–90% IAP/subscription** `[industry]`. Owl & Co. reports free ad-supported apps rose from 15% of global short-drama watch time (2025 Q1) to 83% (2026 Q2) `[industry]` — treat as a single-source claim.
- **AI supply flood:** 2026's first 8 months in China saw 430,000 new micro-dramas, >90% AI-involved; ~50,000 AI micro-dramas on Douyin in March 2026 alone `[industry]`. The stated consequence across multiple sources: **the bottleneck has moved from production to taste and retention**.
- **Format renaming and institutional entry:** "vertical series" is becoming the umbrella term; Fox/Hartbeat announced 25 vertical titles, Peacock opened a vertical section, SAG-AFTRA/WGA reached vertical-format agreements `[industry]`.
- **Mythology / epics:** **no reliable 2026 trend data found.** This is an evidence gap, not proof of an open niche. Only tangential signals: ReelShort's "fantasy/mythology" shelf rated moderate and under-served because live-action fantasy is expensive; costume/fantasy flagged as a growth direction; and a big-budget *Ramayana – Part I* releasing **5 Nov 2026** — a mainstream attention peak that cuts both ways.

### 2.4 Is it doable?

**As a category: yes. As an app business: no.** The dominant cost in the market is customer acquisition (70–90% of recharge revenue in China; ~74% of revenue at India's Kuku), and 80–90% of titles reportedly fail to recoup `[industry]`. You cannot and should not compete there.

**As a solo, zero-marginal-cost creator with organic social distribution: conditionally yes**, because your cost structure is inverted — no cast, no sets, no licensing, no paid acquisition, no per-episode fee. But three conditions are hard:
1. You must reach a monetisation threshold. The Shorts route now requires 10M qualified views/90 days from Feb 2027 `[primary]`.
2. You must survive the "inauthentic content" review (§3.4). A high-volume template mill is the *named* violation.
3. You must sustain retention across episodes. Every source agrees that hooking is easy and sustaining an arc is where series collapse.

---

## 3. Monetisation and platform policy — verified from primary pages

### 3.1 YPP thresholds `[primary]`

| | Now (until 31 Jan 2027) | From 1 Feb 2027 (new applicants) |
|---|---|---|
| YPP ads/Premium entry | 1,000 subs + 4,000 watch hours/12 mo **or** 10M Shorts views/90 days | 1,000 subs + **8,000** watch hours/365 days **or** **20M** Shorts views/90 days |
| Fan funding (unchanged) | 500 subs + 3,000 watch hours/12 mo **or** 3M Shorts views/90 days | unchanged |
| Shorts Creator Pool monthly earnings | — | **10M qualified Shorts views in trailing 90 days**; missing it does not remove YPP status |
| Channel activity | — | 1,000 watch hours/365 d **or** 1M Shorts views/90 d **or** 2 long-form / **5 Shorts per 90 days** |

Existing YPP members are **not affected** by the entry-threshold change, but all must **accept the updated terms in YouTube Studio by 31 Jan 2027** or stop earning from the associated features. Sources: `support.google.com/youtube/answer/12843009` and `/12504220`, read 8 Nov 2026.

⚠️ One inconsistency remains on the official Shorts page: one section states the 10M/90-day earnings requirement without a date, another states "Starting February 1, 2027". Both pages point to 1 Feb 2027; plan for that date.

**Arithmetic `[estimate]`:** 10M views / 90 days = **~111,000 engaged views per day, sustained**. At $0.05–$0.20 RPM that is roughly **$500–$2,000 per 90-day qualifying window** from Shorts ads — before the 45% share and music-pool effects described below. This is why Shorts alone is a weak passive-income engine.

### 3.2 Shorts revenue mechanics `[primary]`

1. Pool all Shorts Feed ad revenue.
2. Allocate into the **Creator Pool** by engaged views and music usage: **no music → 100%** into the pool; 1 partner track → half; 2 tracks → one third.
3. Distribute the pool by your share of engaged views per country.
4. **Creators keep 45%**, regardless of music.

Official worked example: $100,000 feed revenue, 100M engaged views, $90,000 pool, your 1M views → $900 allocated → **$405 earned**. Ineligible: non-original Shorts, artificial views, non-ad-friendly views. "Engaged views" is the metric (YouTube changed the Shorts view count to engaged views on 31 Mar 2025 `[industry]`).

**RPM reality `[estimate/industry]`:** Shorts ~$0.01–$0.20 per 1,000 views; long-form $2–6 per 1,000. We found **no verified, dated, creator-reported earnings** for a social-native mini-series channel, and no official YouTube RPM. Treat any "passive income" figure from a course or tool vendor as marketing.

### 3.3 Instagram / TikTok

- **Instagram Reels monetisation in India is `[unverified]`.** We found no 2026 official Meta statement that Reels ad-share, bonuses or Gifts are available to Indian creators. Play Bonus is reported discontinued. Your local guide (§11) additionally notes Instagram Bonuses unavailable in India and subscriptions requiring 10,000 followers.
- **TikTok Creator Rewards eligibility and RPM are `[unverified]`** from primary pages; widely cited figures are 2023-era vendor claims.

**Platform strategy therefore defaults to YouTube as the monetised home, with Reels/TikTok as discovery funnels** — not the reverse.

### 3.4 Policy risk for your exact pipeline `[primary]`

**Inauthentic content** — `support.google.com/youtube/answer/1311392`, update dated **15 July 2025**:
> "We're making a minor update to our 'repetitious content' policy to better clarify this includes content that is **repetitive or mass-produced**. We are also renaming this policy … to 'inauthentic content.' This type of content has always been ineligible for monetization … There is no change to our reused content policy."

The page also states content should "Be your original creation", "**Not be mass-produced, generic, repetitive, or manipulative**", and "should be made for **the enjoyment or education of viewers**, rather than for the sole purpose of getting views". Reviewers may focus on main theme, most-viewed videos, newest videos, largest watch-time share, metadata and the About section.

**AI disclosure** — `support.google.com/youtube/answer/14328491`: disclosure is required only for content that "**seems realistic**" (real person appearing to say/do something unreal, altered real footage/events, a realistic scene that did not occur, AI music as the main focus). "Realistic AI content and meaningful changes require disclosure, while **non-realistic or minor edits don't**." Labels for non-photorealistic or animated AI content may appear in the expanded description. Crucially: "**Disclosing AI content alone won't limit a video's audience or impact its eligibility to earn money.**"

**Reading for your pipeline `[estimate, inference — not a platform statement]`:** a deterministic code-drawn animation pipeline produces no generative-AI media, so the disclosure duty is unlikely to apply at all; and even if a label were applied, monetisation is unaffected. **But the inauthentic-content policy is medium-agnostic.** A near-identical templated episode run at volume is exactly the "mass-produced, generic, repetitive" pattern, regardless of how the frames were drawn. There is **no explicit exemption for animation or code-drawn content** anywhere on that page.

Two design consequences, both already in your own docs:
- `production-qa.md §10` requires "Distinct story, not another instance of the same template" — that is a monetisation control, not just taste.
- The knowledge/education framing of an obscure-epic series directly matches the policy's "enjoyment or education" language. That is a genuine, defensible advantage over pure romance-template volume.

### 3.5 Realistic monetisation ladder `[estimate]`

Shorts ads are the *floor*, not the business. Build upward:

1. **Fan funding** — lowest gate (500 subs + 3M Shorts views/90 d), unchanged in 2027.
2. **Shorts ad share** — requires YPP + 10M views/90 d from Feb 2027.
3. **Long-form compilations** — same episode assets recut into 8–12 min compilations; RPM ~$2–6/1K vs $0.01–$0.20 for Shorts `[industry]`. This is the single highest-leverage revenue move and requires no new animation.
4. **Sponsorship / licensing / brand-custom episodes** — Indian brands already use micro-dramas for recall campaigns `[industry]`.
5. **Direct products** (PDF episode guides, source-text reading lists) — no platform gate, but requires an audience.

---

## 4. Automation and the "let it go" question

### 4.1 Stage-by-stage

| Stage | Fully automated today | One-time setup | Recurring human touch |
|---|---|---|---|
| Environment / install | Yes | `verify_kit.py`, `doctor.py`, venv path | Re-verify after kit updates |
| Topic + script | **No** | — | Topic/tone + **factual verification** |
| Voice (Kokoro), Whisper timing, `beats.py` | Yes | `voice.py`/`voice2.py` schema | Only if alignment <90% |
| Story breakdown / cast / sets | Skeleton only | — | Season-level plan checkpoint |
| Style choice | Yes (defaultable) | Fix one style | Variety decision |
| **Scene code / directing** | **No — core blocker** | **Template + `params` interpreter** | Hero shots (3–5 per film) |
| **Visual QC + approval** | **No — mandatory** | Sheet/preview tooling | Final watch + recorded approval |
| Render | Yes, unsafe unattended | Fix `render.mjs` exit code; orchestrate LLM load/unload | None once orchestrated |
| Music/SFX/mix | Yes | Valid-name whitelist | None |
| Gates (motion / style_lock / seam / report) | Yes | Populate `style_lock` + `approved_by` | Re-baseline when templates change pixels |
| Fact-check + distinct-story check | **No** | — | Per episode |
| Upload / schedule / publish | Yes | OAuth, API project, `publishAt`, private-until-approved | None |

### 4.2 Local blockers found in your repo

- **`engine/player.js:74`** already injects `shot.params` into `info`; **zero projects use it** `[measured]`. The cheapest real throughput win is therefore additive, with zero edits to protected paths.
- **`render.mjs` prints "N shot error(s)" but still exits 0** `[measured]`; `engine/player.js` paints `ERROR s00X` into the frame instead of throwing. An unattended run can ship a broken video that reports success.
- **Commit headroom:** a loaded 15 GB GGUF `llama-server` reserves ~26.56 GB of commit address space, leaving ~2.6 GB; ffmpeg/MKL then fail with `Cannot allocate memory` / `mkl_malloc`. Need ≥6 GB. Rule: **unload → render → reload, never both**.
- **Approval state:** both `report.json` files carry `style_lock: null`, `approved_by: null`, `human_review: "required; technical checks are not acceptance"`. `LESSONS.md` records acting-pass was built without a style lock. The mandatory approval is a *rule*, not an enforced state.
- **Measured authoring cost:** 25.2 non-comment lines/shot for acting-pass (17.1 / 15.8 / 15.8 for the others), 109–181 numeric literals per shot file, 17% of imported names unused, cross-project shot-code similarity 0.08–0.16, ~10–12K tokens of generator context before any example.
- **Your own research doc's verdict:** "the session wasn't consumed by typing 327 lines — it was consumed by write→render→look→change→look cycles". And "a green machine check is not acceptance".

### 4.3 One-time engineering block (the concentrated effort you are willing to spend)

1. **`scenes/templates.js`** — a registry of the 12 named shot archetypes from `style-bible.md`, driven by `shots.json` `template` + `params`. Zero edits to `engine/`, `render.mjs`, `player.html`, `audio/`.
2. **Hard-fail gate** — make `render.mjs` exit non-zero on `SHOT ERROR`; required before any unattended run.
3. **Commit orchestration** — automatic local-LLM unload before render, reload after; plus a check for ≥6 GB headroom. Using a cloud LLM for authoring removes this problem entirely.
4. **Populate `style_lock` + `approved_by`** and re-baseline once (templates change pixels).
5. **Approval tooling** — a single-shot scrub over `params` and an annotated contact sheet, so judgement passes are cheap.
6. **Publish pipeline** — YouTube Data API `videos.insert` with `status.publishAt` and `privacyStatus=private` until approved; upload quota and OAuth one-time. **Note** `[industry, verify]`: a revision-history entry dated 2 Nov 2026 says uploads from unverified API projects are no longer forced private and now default to public — so a private-staging step is a safety requirement, not an optional nicety.
7. **Small, named template library** — cap hero shots at 3–5 hand-written per film to avoid the "mass-produced" pattern.

### 4.4 Time budget `[estimate — no timed trial exists in the repo]`

Assumptions: 60 s / 15–25 shots per episode, 3 episodes/week, cloud LLM for authoring (no resident model), agent does all drafting and sheet iteration, human attention batched into one weekly session.

| | Today, as-is | After one-time engineering |
|---|---|---|
| Per episode | 15–40 min | 5–15 min |
| Per week | 45–120 min | **15–45 min, in one batched session** |
| Additional | ad-hoc troubleshooting | ~monthly: template additions, lock re-baseline, quota/OAuth/policy audit, metrics review |

**No daily reading or writing is required** in the engineered state. That part of your requirement is achievable.

### 4.5 Verdict on "settle it, push on track, then let go"

**Partially achievable.** Fully automatable: install, voice, timing, render, mix, technical gates, upload and scheduling. Not automatable: topic/script judgement, factual verification, scene code for hero shots, final visual approval, distinct-story variety.

- If "let go" means **no daily work, one batched weekly approval session, and decisions only at 3–4 defined checkpoints** → **achievable** after the engineering block.
- If "let go" means **zero recurring human decisions** → **no**, for two independent reasons: (a) your own repo and `production-qa.md §9` mandate a human watching the film, and `report.json` records that technical checks are not acceptance; (b) YouTube's inauthentic-content policy demonetises the repetitive output that fully unattended volume tends to produce.
- **"Passive income" specifically:** treat it as an **uncertain upside**, not a plan. No verified solo-creator profit data exists; Shorts RPM is low; the 10M/90-day gate is steep; "passive income" claims found were vendor marketing. The automation is a real asset you can build; the revenue is a hypothesis you should validate with a bounded pilot before scaling.

---

## 5. Content / IP choice

### 5.1 Option matrix

| Option | Demand signal | Saturation | Sensitivity | Season arc | Fit with stick-figure pipeline |
|---|---|---|---|---|---|
| Straight Ramayana / Mahabharata retelling | **Highest** — Doordarshan 2020 re-telecast drew "tremendous and unprecedented public" response (MIB Annual Report 2020-21, qualitative); big-budget *Ramayana Part I* released 5 Nov 2026 | **Highest** — mainstream studios, OTT, comics, TV | **Highest** — living worship, BNS s.299, active 2025–26 FIRs | Strong but well known | Weak — deity depiction, expectation of grandeur, no novelty |
| Ramcharitmanas / major Puranas | High (Hindi belt) | High | High | Moderate | Weak |
| **Regional epic variants** (Kamba Ramayanam, Sarala Mahabharata, Pampa Bharata / Vikramarjuna Vijaya, Villiputhurar Bharatam, Kashiram Das, Ramakien, Kakawin Ramayana) | Medium — "familiar epic, fresh angle" | Low | Medium–high (still epic deities) | Strong, episode-sized divergent episodes | Good — recognition + genuine novelty |
| **Vetala Panchavimshati / Baital Pachisi** (Vikram + Vetala) | Low recognition, but *Vikram Aur Betaal* cultural memory | **Low** | **Low** | **Excellent** — frame quest, a riddle + escape-and-return cliffhanger every episode, season payoff | **Best** — two recurring stick figures, one set per tale, native 60–90 s structure |
| Kathasaritsagara (Somadeva) | Very low | Very low | Low | Excellent — nested frame quest | Very good, deep story bank |
| Jataka / Panchatantra / Jain & Buddhist avadana | Medium (Panchatantra well known) | Medium | Low | Weak (anthology, no arc) | Good (animal casts, cheap to draw) |
| Non-Indian (Gilgamesh, Kalevala, Popol Vuh) | Low in India | Low | Low | Moderate | Good, but weaker cultural pull |

### 5.2 Recommendation

**Season 1: Vetala Panchavimshati**, framed as "the stories you were never told". Each episode = King Vikramaditya carries the Vetala, the Vetala tells one tale and poses a riddle, Vikram answers (or fails), the cycle resets. That is a **native cliffhanger**, a fixed two-character cast (signature colours never change), one reusable night/forest set plus one tale set per episode, and a revealed frame story that pays off the season. It maps directly onto your 8–12 shot / 30 s pilot and scales to 15–25 shots / 60 s.

**Season 2: regional Mahabharata variants** — "the Mahabharata you don't know" — once the channel has trust and a sourcing routine. This converts familiarity into acquisition while keeping novelty. On-screen "regional retelling" attribution is required.

**Reserve Jataka/Panchatantra** for shorter filler or a children's spin-off; their anthology structure does not sustain a season arc.

### 5.3 Copyright and legal position (not legal advice)

- `[primary]` India Copyright Act 1957 **s.22**: copyright in a published literary/dramatic/musical/artistic work subsists until **60 years from the beginning of the calendar year after the author's death**. Ancient Sanskrit/Pali/Prakrit/Tamil/Odia originals are therefore public domain in India `[estimate]`.
- `[primary]` Duke CSPD: as of **1 Jan 2026**, US works published/registered in **1930** entered the US public domain (95-year pre-1978 term). Other countries' terms differ.
- `[industry]` *R.G. Anand v. Delux Films* (1978): "no copyright in an idea, subject matter, themes, plots or historical or legendary facts"; infringement is confined to "form, manner and arrangement and expression".
- **Modern retellings remain protected**: C. Rajagopalachari's *Ramayana*/*Mahabharata*, Amar Chitra Katha comics, Devdutt Pattanaik's books, TV serial scripts, music and character designs. Modern critical editions and 20th-century translations are separate copyrighted works; exact status `[unverified]`.
- **Practical rule:** adapt only a public-domain source text (e.g. a 19th-century translation), write an original script in your own words, draw original code-based art, generate your own audio, and avoid any dialogue, ordering, invented scenes or visual designs from a modern retelling. Characters and plots as facts/ideas are free; a specific retelling's expression is not.
- `[primary]` **BNS s.299** — "Deliberate and malicious acts, intended to outrage religious feelings of any class by insulting its religion or religious beliefs"; BNS in force **1 July 2024**. Case law quoted on IPC 295A requires "deliberate and malicious intention"; unwitting or careless insult falls outside it. `Indian Kanoon` listings show 2025–26 FIRs pairing BNS 299 with IT Act s.67 / s.66(c).
- `[estimate]` Good-faith knowledge framing is relevant to intent and to s.52 fair dealing, but grants **no statutory immunity**; platform guidelines and blocking orders can remove content without prosecution. Stick-figure abstraction reduces depiction-of-deity risk relative to realistic imagery. **Factual accuracy and attribution are a compliance measure, not just a quality measure** — your guide §11 already warns the pipeline "will happily render a wrong fact with total confidence".

### 5.4 What could not be verified

No subscriber/view counts for any mythology short-form channel; no Google Trends or platform search-volume series; no 2025–26 published survey on mythology shorts; no numeric BARC/MIB viewership; Rajagopalachari's death date and exact copyright expiry; BORI critical-edition copyright; specific PD translation publication years; any peer-reviewed retention study on "learn something obscure" hooks; any measured 2026 mythology/epics short-form trend. **The absence of data is not evidence of an open niche** — it is an evidence gap. Validate with a bounded pilot, not with a full season.

---

## 6. Confidence register and contradictions

| Claim | Status |
|---|---|
| YPP 2027 thresholds, 10M/90-day Shorts gate, 45% share, 3-min Shorts monetisation, inauthentic-content wording, AI-disclosure scope | **Verified from primary YouTube Help pages, 8 Nov 2026** |
| 8-second attention span myth debunked (KCL, 2,093 adults, 2021) | **Verified, named study** |
| India Meta–Ormax viewing behaviour (2,000 + 50 interviews, 14 states, Nov 2025–Jan 2026) | **Measured**, reached via secondary compilation, not the primary PDF |
| Global $11B (2025) → $14B (2026), China 83% | **Industry estimate**, multiple relays, not audited |
| India $300M (2025) vs ₹650 crore (2025) | **Contradiction** — ~3.8× gap from differing scope; do not combine |
| "133 engine exports" / "≈40 KB generator docs" in your own research doc | **Stale** — recomputed at 126 exports and 28.5 KB at the doc's own quoted sizes (31.1 KB today) |
| "Cross-episode reuse 0.08–0.16" in your own research doc | **Now contradicted** — `one-more-night-9x16` is a near-verbatim copy of `acting-pass` (added 8 Nov 2026) |
| 3-second / 6-second retention percentages | **Unverified** — vendor / paid-acquisition benchmarks only |
| Instagram Reels monetisation in India; TikTok Creator Rewards eligibility | **Unverified** |
| Mythology/obscure-epic short-form audience trend | **No evidence found** |
| Solo-creator profit, per-episode cost, hit rate for social-native series | **No verified data found** |
| Expert-plugin discovery | **Tool failed 3×**; no expert recommendation made, nothing invented |
| Connector discovery | 10+ candidates returned, **none fit**; no connector card shown. Kling AI is an AI video generator, explicitly excluded by this pipeline's design. |

---

## 7. Primary sources consulted

**Platform (read directly):**
- YouTube Help — Changes to the YouTube Partner Program: https://support.google.com/youtube/answer/12843009
- YouTube Help — YouTube Shorts monetization policies: https://support.google.com/youtube/answer/12504220
- YouTube Help — Understand three-minute YouTube Shorts: https://support.google.com/youtube/answer/15424877
- YouTube Help — Channel monetization policies (inauthentic content): https://support.google.com/youtube/answer/1311392
- YouTube Help — Disclosing use of GenAI content: https://support.google.com/youtube/answer/14328491
- YouTube Help — YPP overview & eligibility: https://support.google.com/youtube/answer/72851
- Meta Newsroom — Five Years On, Reels Reigns as India's Top Short-Form Video Platform (11 Sep 2025): https://about.fb.com/news/2025/09/five-years-on-reels-reigns-as-indias-top-short-form-video-platform/
- Meta Newsroom — Instagram Launches A Microdrama Series (2 Sep 2025): https://about.fb.com/news/2025/09/instagram-launches-a-microdrama-series-to-encourage-gen-z-to-take-creative-chances/

**Research / press:**
- King's College London, Policy Institute — Are attention spans really collapsing? (16 Feb 2022): https://www.kcl.ac.uk/news/are-attention-spans-really-collapsing-data-shows-uk-public-are-worried-but-also-see-benefits-from-technology
- BBC — Busting the attention span myth (2017): https://www.bbc.co.uk/news/health-38896790
- TenSquared Capital — The Microdrama Thesis (2026): https://tensquared.com/research/research-26-06-the-microdrama-thesis-ai-taste-and-the-next-entertainment-platform.html
- Variety / Media Partners Asia — Microdramas Emerge as Multi-Billion Dollar Global Phenomenon (16 Sep 2025): https://variety.com/2025/tv/news/microdramas-global-entertainment-billions-1236521194/
- Mint — Short drama boom sends new wave of startups knocking on VC doors (Lumikai India figures): https://www.livemint.com/industry/media/microdrama-startups-india-vc-fundraising-boom-mobilefirst-11778560180661.html
- The Videshi — Microdramas Emerge as India's Fastest-Growing Entertainment Format (Meta–Ormax, FICCI-EY): https://www.thevideshi.com/articles/microdramas-emerge-india-fastest-growing-entertainment-format
- The Paper — DataEye/Meta–Ormax India micro-drama compilation (25 Mar 2026): https://www.thepaper.cn/newsDetail_forward_32827058
- The Paper — Douyin 3-minute rule and 90-second completion data: https://m.thepaper.cn/newsDetail_forward_33373003
- Wistia — State of Video 2026: https://wistia.com/learn/marketing/video-marketing-statistics
- Metricool — Short-Form Video Report 2026: https://metricool.com/short-video-report/
- Wikipedia — Duanju: https://en.wikipedia.org/wiki/Duanju

**Law (read directly):**
- Indian Kanoon — Copyright Act 1957 s.52: https://indiankanoon.org/doc/1013176/
- Indian Kanoon — BNS s.299: https://indiankanoon.org/doc/152296772/
- Duke CSPD — Public Domain Day 2026: https://web.law.duke.edu/cspd/publicdomainday/2026/
- MIB Annual Report 2020-21: http://www.mib.gov.in/sites/default/files/2024-08/annual-report-2020-21.pdf

**Local project evidence:**
- `E:\Local_Mis_WS\STICKMAN_VIDEO_GUIDE.md`, `RESEARCH_SCENE_CODE_THROUGHPUT.md`
- `_yt_stickman\plugin\skills\make-2d-video\SKILL.md`, `references\style-bible.md`, `references\directing.md`, `references\self-improve.md`
- `_yt_stickman\aitrends-2d-studio\docs\production-qa.md`, `docs\LESSONS.md`, `projects\*\build\report.json`, `engine\player.js:74`, `render.mjs:71-78`

---

## 8. The decisions to make next

1. **Pilot length:** 30 s (proven, 8–12 shots) or 60 s (market-aligned, 15–25 shots, requires the template interpreter first).
2. **Season scope:** 7 episodes (Meta's social-native precedent) or 12 (better arc, more authoring).
3. **Source:** Vetala Panchavimshati (recommended), Kathasaritsagara, or a regional Mahabharata variant.
4. **Engineering order:** template interpreter + hard-fail exit code **before** any episode production, or ship a manual 3-episode pilot first to validate retention.
5. **Monetisation route:** Shorts-first with a long-form compilation ladder, or long-form-first with Shorts as discovery.

The companion file `MINI_SERIES_TEMPLATE_PLAN.md` turns whichever choices you make into a fill-in template.
