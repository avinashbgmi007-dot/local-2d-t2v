# Style recipes — range without changing the engine

The five built-in styles in `engine/styles.js` are the tested looks. This file adds **recipes** for
episodes that need to feel different without touching the renderer, the character or the audio path.

A recipe is a direction, not code. Use it in one of two ways:

1. **Mood-only (no file edit):** choose the nearest built-in `style` in `config.json` and the closest
   built-in `mood`. Treat the recipe's palette as a direction when you choose set colours and
   `shade`/`mix` values. This changes no engine file.
2. **First-class style (only after a test render):** add a new entry to `STYLES` in
   `engine/styles.js` with the recipe's `moods` overrides and `grade`. Test one shot before committing.
   That file is pinned by `tools/verify_kit.py`, so a change is a deliberate customisation, not a
   silent drift.

Every recipe below names a **starting mood**, a **grade direction**, **camera grammar** and what it
is **best for**. Treat the numbers as a direction, not a law.

---

## 1. Paper Ink

**Starting mood:** `interiorWarm` or `dusk` with the sky removed.
**Palette:** warm paper `#e8ddc8` / `#d9cbb2`, soft black ink `#1a1714`, one faded red accent.
**Grade:** contrast 0.95, sat 0.75, lift `[0.06, 0.05, 0.04]`, vignette 0.25, grain 0.08, bloom 0.25.
**Camera:** slow lateral drift, almost no zoom; cuts land like page turns.
**Best for:** memory, letters, childhood, a story told at a table.
**Avoid:** neon, rain, hard sci-fi surfaces. The paper ground kills them.

## 2. Blueprint Noir

**Starting mood:** `void` with a navy `#0b1324` ground.
**Palette:** navy ground, cyan `#8fd8ff` lines, one warm amber callout, no green.
**Grade:** contrast 1.12, sat 0.65, lift `[0.0, 0.02, 0.07]`, vignette 0.7, grain 0.03, bloom 0.6.
**Camera:** locked diagrams with a slow push; reveal by drawing, not by cutting.
**Best for:** mechanisms, the body, systems, “how it works” explanations.
**Avoid:** faces in close-up for long; the blueprint mode flattens acting.

## 3. Sodium Night

**Starting mood:** `night` or `interiorCool`.
**Palette:** deep brown-black `#120d0a`, sodium amber `#ffb45e`, cold blue rim `#9fc4ff`.
**Grade:** contrast 1.18, sat 0.9, lift `[0.04, 0.015, 0.0]`, gamma `[1.05, 1.0, 0.95]`,
vignette 0.72, grain 0.05, bloom 0.8.
**Camera:** handheld-adjacent drift, small roll, practicals in frame.
**Best for:** streets, late-night kitchens, a conversation that should have ended.
**Avoid:** daylight and clean white rooms; the sodium key looks dirty there.

## 4. Cold Archive

**Starting mood:** `interiorCool` or `storm`.
**Palette:** desaturated teal-grey `#3a4a50`, bone `#d8d4c8`, one rust accent `#a45a3a`.
**Grade:** contrast 0.92, sat 0.55, lift `[0.05, 0.06, 0.06]`, vignette 0.35, grain 0.07,
bloom 0.3.
**Camera:** locked-off or very slow dolly; let the frame feel like a record.
**Best for:** documentary, evidence, a true story, an archive or a file.
**Avoid:** comedy and big action; the grade deliberately removes heat.

## 5. High-Key Graphic

**Starting mood:** `day` with the sky flattened to cream `#f2ead8`.
**Palette:** cream ground, black `#111111`, one saturated red `#e23b2e`, one blue `#2f6fd0`.
**Grade:** contrast 1.2, sat 1.15, lift `[0.04, 0.03, 0.02]`, vignette 0.1, grain 0.02, bloom 0.2.
**Camera:** snap zooms, hard cuts, graphic match cuts; movement is deliberate, not floaty.
**Best for:** opinion, money, a thesis, a video that argues.
**Avoid:** slow emotional holds; the palette wants a beat.

## 6. Faded Film

**Starting mood:** `golden` or `dusk`.
**Palette:** warm grey-green shadows, cream highlights, muted rust and teal.
**Grade:** contrast 0.88, sat 0.7, lift `[0.07, 0.065, 0.06]`, gamma `[1.08, 1.04, 0.98]`,
vignette 0.45, grain 0.09, bloom 0.4.
**Camera:** slow push, shallow foreground blur, long-ish holds.
**Best for:** nostalgia, a relationship, a memory that is not quite reliable.
**Avoid:** data diagrams and crisp UI; the softness fights readable numbers.

---

## Choosing a recipe

| Episode is… | Try |
|---|---|
| A personal story or memory | Paper Ink or Faded Film |
| A mechanism / body explainer | Blueprint Noir |
| A late-night dialogue | Sodium Night |
| Evidence, a case, a record | Cold Archive |
| An argument or a list with a thesis | High-Key Graphic |
| A quiet relationship turn | Faded Film or Paper Ink |

## Anti-sameness rules

- Do not use the same recipe twice in a row, even if it tested well. Rotate at least two.
- Do not combine two recipes into a “best of both”; that is how every episode becomes the same
  mid-tone look.
- Change at least one of these per episode: recipe, opening image, dominant shot size, transition
  signature, ending device.
- A recipe is a starting point. If the episode needs a colour that is not in it, add one accent and
  remove one existing colour; do not add a third.
