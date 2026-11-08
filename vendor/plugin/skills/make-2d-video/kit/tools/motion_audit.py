"""tools/motion_audit.py — measure whether a finished video is actually moving.

What this measures, and what it does NOT.

It measures **change rate** between consecutive frames, per one-second window. Used on this
pipeline's own footage it reliably finds a genuinely dead stretch (motion collapses to ~0.0000
against a normal 0.001-0.008), so it is a **dead-frame detector**.

It is NOT a perceived-liveliness metric, and that was measured, not assumed. Ranking five renders
from this pipeline by this metric put the two clips the owner called "static" ABOVE the cinematic
ones (Inside Out 0.0083-0.0104 vs aiTrends 0.0021-0.0030 on the raw scale), because a caption
popping on screen is a large pixel change while a slow camera drift with breathing and dust is a
small one. Contrast-normalising the frames did not fix it (0.0475 static vs 0.0219 cinematic), and
neither did Farneback optical flow (0.0031 static vs 0.0006 cinematic). Change rate and perceived
motion are different things; frequent discrete change can feel MORE static than continuous small
motion. Do not use this tool to judge whether a video feels alive. Judge that by looking.

Method: decode the output video to grayscale, take the mean absolute pixel difference between
consecutive frames, and aggregate it into 1-second windows. Also report the fraction of near-frozen
frames in each window, and the min/max mean brightness (a black or white stretch is not motion).

Metric scale: pixels are normalised to 0..1. Thresholds below are calibrated on this pipeline's own
renders (grayscale, 160px tall). The upstream project this idea came from used floors of 0.2/0.3 —
those are roughly 60x above our entire measured range and would fail every video we make, so they
were deliberately not carried over. See docs/MOTION_BASELINE.md.

  python tools/motion_audit.py projects/<slug>/out/<Title>.mp4
  python tools/motion_audit.py <video> --min-motion 0.02 --max-frozen 0.10
  python tools/motion_audit.py <video> --sym 12.0-18.0 --sym-min 0.03   # stricter bar for symbolic beats
  python tools/motion_audit.py <video> --json build/motion.json

Exit code 1 if any window fails, so this can gate a batch.
"""
import argparse, json, subprocess, sys
import numpy as np


def frames(path, target_h=180):
    """Decode video -> (n, h, w) float32 in 0..1, grayscale.

    The scaled dimensions are computed here and used for the reshape. Deriving them from the
    *source* stream instead is a silent bug: the frame count comes out wrong by the scale ratio.
    """
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height,r_frame_rate",
                            "-of", "json", path], capture_output=True)
    st = json.loads(probe.stdout)["streams"][0]
    sw, sh = int(st["width"]), int(st["height"])
    num, den = st["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    h = target_h
    w = max(2, int(round(sw * h / sh / 2)) * 2)

    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h},format=gray",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg could not decode {path}: {p.stderr.decode()[-500:]}")
    a = np.frombuffer(p.stdout, dtype=np.uint8).astype(np.float32) / 255.0
    n = a.size // (w * h)
    if a.size % (w * h):
        print(f"note: {a.size % (w*h)} trailing bytes dropped (partial frame)", file=sys.stderr)
    return a[:n * w * h].reshape(n, h, w), fps, w, h


def parse_ranges(specs):
    out = []
    for s in specs or []:
        a, b = s.split("-")
        out.append((float(a), float(b)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--min-motion", type=float, default=0.0006,
                    help="fail a window whose mean inter-frame difference is below this (dead stretch)")
    ap.add_argument("--sym-min", type=float, default=0.0006, help="floor for --sym windows")
    ap.add_argument("--sym", action="append", default=[], metavar="A-B",
                    help="symbolic-beat time range in seconds; repeatable")
    ap.add_argument("--max-frozen", type=float, default=0.10,
                    help="fail a window if more than this fraction of frames are near-frozen")
    ap.add_argument("--frozen-thresh", type=float, default=0.0004,
                    help="a frame pair below this mean difference counts as frozen")
    ap.add_argument("--skip-start", type=float, default=0.6, help="ignore this many seconds of opening fade")
    ap.add_argument("--json", help="also write a machine-readable report here")
    a = ap.parse_args()

    fr, fps, w, h = frames(a.video)
    if len(fr) < int(fps) + 2:
        sys.exit(f"too few frames ({len(fr)}) at {fps} fps — nothing to measure")

    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))          # mean |Δpixel| per frame pair
    bright = fr.mean(axis=(1, 2))
    win = int(round(fps))
    start = int(a.skip_start * fps)

    rows, issues = [], []
    i = start
    while i + win <= len(d):
        seg = d[i:i + win]
        m, fz = float(seg.mean()), float((seg < a.frozen_thresh).mean())
        t0, t1 = i / fps, (i + win) / fps
        sym = any(lo <= t0 and t1 <= hi for lo, hi in parse_ranges(a.sym))
        floor = a.sym_min if sym else a.min_motion
        rows.append({"t": round(t0, 2), "mean_motion": round(m, 4), "frozen": round(fz, 3),
                     "symbolic": sym, "floor": floor,
                     "brightness": round(float(bright[i:i + win].mean()), 3)})
        if m < floor:
            issues.append(f"still window at {t0:.1f}s — mean motion {m:.4f} < {floor}"
                          + (" (symbolic bar)" if sym else ""))
        if fz > a.max_frozen:
            issues.append(f"frozen window at {t0:.1f}s — {fz:.0%} of frames below {a.frozen_thresh}")
        i += win

    if not rows:
        sys.exit(f"no whole 1-second window after the {a.skip_start}s fade — video too short to audit")
    lo = min(rows, key=lambda r: r["mean_motion"])
    print(f"{a.video}\n  {len(fr)} frames @ {fps:.2f} fps · {len(fr)/fps:.2f}s · {w}x{h} · "
          f"{len(rows)} one-second windows")
    print(f"  motion  min {lo['mean_motion']:.4f} @ {lo['t']:.1f}s · "
          f"median {np.median([r['mean_motion'] for r in rows]):.4f} · "
          f"max {max(r['mean_motion'] for r in rows):.4f}")
    print(f"  brightness range {bright.min():.3f} – {bright.max():.3f}"
          f" · frozen threshold {a.frozen_thresh} · floors {a.min_motion}/{a.sym_min}")
    print("  per window: " + " ".join(f"{r['t']:.0f}s:{r['mean_motion']:.3f}{'S' if r['symbolic'] else ''}"
                                       for r in rows))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"video": a.video, "frames": len(fr), "fps": fps, "duration": len(fr) / fps,
                       "windows": rows, "issues": issues,
                       "thresholds": {"min_motion": a.min_motion, "sym_min": a.sym_min,
                                      "max_frozen": a.max_frozen, "frozen_thresh": a.frozen_thresh}},
                      fh, indent=1)
    for s in issues:
        print("ISSUE  " + s)
    if issues:
        print(f"\n{len(issues)} issue(s). Fix them, or state why a flagged window is intended "
              f"(a held reaction, a passing vehicle, a fade).")
        sys.exit(1)
    print("\nMOTION OK — every window clears its floor.")


if __name__ == "__main__":
    main()
