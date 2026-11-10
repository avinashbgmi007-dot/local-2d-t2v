# ADR: frame_qa constants and calibration

## Status
Accepted. Constants frozen as of 2026-11-10.

## Constants

| Constant | Value | Source |
|----------|-------|--------|
| Resolution | 32x18 | 8x8 too coarse (small animation averages away); 32x18 catches s006 freeze |
| SAD_FREEZE | 50 | p5 of SAD distribution: cine_release p5=58, one-more-night p5=61. Threshold sits just below 5th percentile of normal motion |
| SAD_POP | 2000 | Near p90 of cine_release (2037). Return-to-prior-level check (sad_ba < 1000) does real filtering |
| Freeze frames | 12 | ≥12 identical frames = "frozen" finding; 3-11 = info only |
| Black luma | < 8 | Calibrated on cine_release (black frames luma 0.2-7.4) |
| White luma | > 247 | Calibrated on cine_release |
| End-tail cap | 0.5s | Longer trailing black flagged as finding |
| Fade ramp | ≤20 levels/frame, 3+ frames | Distinguishes gradual fade from instant flicker |
| Flicker | instant drop + instant rise, ≤3 frames | Hard cut to black and back |

## Validation

- 16 projects with videos: 0 findings (all PASS)
- Synthetic controls: freeze (15 frames, SAD 5-22) detected; flicker (2 black frames) detected; pop (1 spike frame) detected; subtle motion (SAD 40-120) not flagged
- Real-frame freeze: held frame through H.264, SAD 5-22, detected as 15-frame finding
- Second SAD distribution (one-more-night): p5=61, confirming threshold margin

## Known limitations

- **Whole-frame freezes only.** frame_qa detects frames where the entire 32x18 downscale is static (SAD < 50). A freeze with parallax planes, practical light, or minor drift (SAD >= 50) is not detected. The s006 freeze in cine_release (~14 frames, 0.58s) shows only 3-frame static runs because the set keeps moving. frame_qa does NOT verify that the freeze feature works; it only catches whole-frame freezes.
- **Fast fades (<=4 frames) classified as flicker.** The ramp test requires 3+ rising frames at <=20 levels/step. A deliberate dip or fade of 4 frames or fewer would be classed as flicker. The ramp cap is tuned to the fades observed in cine_release (5-9 frame runs).
- **Flicker detection requires both instant drop AND instant rise within <=3 frames.** A 4+ frame black run with instant transitions is not classified as flicker.
- **SAD_FREEZE=50 against p5=58-61 leaves thin margin.** One noisy frame in a real freeze resets the run (false-negative risk).
- **Pop detection needs both neighbors;** 2-frame spikes at video boundaries are missed.
- **frame_qa is report-only (warning level), not fatal.** Promotion to fatal deferred until known-bad corpus is complete.
- **End-tail cap: 0.5s.** Trailing black beyond 0.5s is flagged as finding.