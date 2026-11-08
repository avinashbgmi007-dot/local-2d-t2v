# Third-party ledger

Everything outside this studio that was read, adapted or deliberately rejected. The rule for a
monetised channel: **if it is not in this file, it does not go into the revenue path.**

This is a record of provenance, not a list of dependencies. The studio still runs on the same local
stack: Node, Playwright, Three.js, ffmpeg, Python, Kokoro and Whisper. No new runtime package was
added for the items below.

## Adapted

| Source | Licence | What was taken | Where it lives | Code copied? |
|---|---|---|---|---|
| [`JohnHeibel/ClaudeAnimationBase`](https://github.com/JohnHeibel/ClaudeAnimationBase) | MIT | Acting method: staggered face changes and emotion vocabulary; QA rules: reads/holds timing, contacts, anticipation, no twinning, key poses as stills | `chars/acting.js`, `plugin/skills/make-2d-video/references/engine-api.md`, `docs/production-qa.md` §2/§5 | No. `acting.js` is a clean-room implementation for this engine; the QA lines are rewritten rules, not copied text. |
| [`lemomo-ai/lemo-opuscar`](https://github.com/lemomo-ai/lemo-opuscar) | MIT (code) / CC BY 4.0 (demo films) | Directing method: benchmark first, treatment first, three structures, one native move, ending echo; style-range idea from the styles catalogue | `plugin/skills/make-2d-video/references/directing.md`, `plugin/skills/make-2d-video/references/style-recipes.md` | No. The docs are rewritten for this pipeline. No demo film, footage, character or asset was used. |
| [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) | Apache-2.0 | Method: the boundary as a design object | `tools/seam_gate.py`, `plugin/skills/make-2d-video/references/directing.md` | No. The CLI, the Pro templates and the DOM/CDP verifier are not used. |
| [`feitangyuan/onetake`](https://github.com/feitangyuan/onetake) | PolyForm Noncommercial 1.0.0 | Method only: every beat is carried across the boundary | `tools/seam_gate.py` docstring | **No.** The licence is non-commercial, so no code, template or asset from this repo is present. |
| [`google-research/harness2`](https://github.com/google-research/harness2) | Apache-2.0 | Concept only: Propose–Probe–Compose, persistent lessons, one harness change at a time | `plugin/skills/make-2d-video/references/self-improve.md`, `docs/LESSONS.md` | No. The framework is not installed; it is benchmark infrastructure, not a renderer. |

## Read and rejected

| Source | Licence | Why it is not here |
|---|---|---|
| [`layabox/LayaAir`](https://github.com/layabox/LayaAir) | MIT | It is a game engine and IDE. Adopting it would replace the renderer, not add to it. |
| [`acamposuribe/p5.brush`](https://github.com/acamposuribe/p5.brush) | MIT | It requires p5 and a different drawing model. The brush *idea* is noted; no dependency was added. |
| HyperFrames Pro templates / style packs | Commercial | Paid, account-bound, and they replace the look. Not used. |
| Lemo demo films and stills | CC BY 4.0 | Reusable with attribution, but they are other people’s films. The method is enough; the assets stay out. |

## Existing credits

The Kenney foley pack is CC0 and already recorded in `audio/foley/KENNEY-CREDITS.txt`. It is not repeated
here.

## MIT notices

The notices below are reproduced for attribution. The implementations in this repository are
clean-room; no source code from these projects is present.

### ClaudeAnimationBase

```
MIT License

Copyright (c) 2026 John Heibel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### lemo-opuscar

```
MIT License

Copyright (c) 2026 LemoLab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Apache-2.0 sources

HyperFrames and Harness² are Apache-2.0. No source code was copied, so no `NOTICE` file is
reproduced. Their licence text is available at:

- https://github.com/heygen-com/hyperframes/blob/main/LICENSE
- https://github.com/google-research/harness2/blob/main/LICENSE

## Non-commercial source

`feitangyuan/onetake` is PolyForm Noncommercial 1.0.0. Its **method** is credited in
`tools/seam_gate.py`; its code is not used anywhere in this repository. If a future change wants to
use any part of it, that change is blocked until a commercial licence is obtained.
