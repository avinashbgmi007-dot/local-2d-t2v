# Motion audit — calibration record

Measured on this machine, 2026-11-06, with `tools/motion_audit.py` (grayscale, 160 px tall).
These numbers are why the thresholds are what they are. Do not carry thresholds in from another
project without re-measuring.

## Change-rate, raw scale (mean |Δpixel|, pixels in 0..1)

| render | style | median | note |
|---|---|---|---|
| stomach-lining 5.9 s | Inside Out flat 2D | 0.0083 | **owner called this "static"** |
| inside-out selftest draft | Inside Out flat 2D | 0.0104 | |
| stick-story selftest draft | Stick Story | 0.0027 | |
| dialogue-call 13.6 s | aiTrends cinematic | 0.0021 | |
| stomach-acid 29.9 s | aiTrends cinematic | 0.0030 | |

## Same five, contrast-normalised per frame

static Inside Out **0.0475** and 0.0385 vs cinematic aiTrends **0.0219** and 0.0264 — ordering unchanged.

## Same five, Farneback optical flow (frame-widths per frame)

static Inside Out **0.0031** vs cinematic aiTrends **0.0006** — ordering unchanged again.

## Conclusion

All three metrics rank the clips the owner described as static **above** the cinematic ones. That is
not a bug in the measurement; it is what these metrics measure. A caption popping on screen or a cut
flash is a large discrete change; a slow camera push with breathing, rim light and drifting dust is a
small continuous one. **Change rate is not perceived liveliness.**

What the metric *is* good for: a genuinely dead stretch collapses to ~0.0000 against a normal
0.001–0.008. Validated by concatenating a 4 s held frame into `stomach-acid`:

| file | result |
|---|---|
| `build/frozen_test.mp4` (4 s injected still) | 8 issues, exit 1 |
| `Why_Doesnt_Your_Stomach_Digest_Itself.mp4` (real) | MOTION OK |
| `She_Asked_About_You.mp4` (real) | MOTION OK |

Zero false positives on real footage; catches dead frames. That is the whole claim.

## Upstream thresholds that were rejected

The source project (`stickman` by michxlai) floors of **0.2 normal / 0.3 symbolic** with a frozen
sub-threshold of 0.05. On our footage those sit ~60× above the entire measured range — every window
of every video we make would fail. Their `frozen` fraction at 0.004 also saturated to 1.00 on all our
real renders, so that sub-metric was dropped rather than tuned.

Use: `--min-motion 0.0006 --frozen-thresh 0.0004 --max-frozen 0.90` (defaults).
