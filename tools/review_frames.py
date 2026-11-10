#!/usr/bin/env python3
"""
review_frames.py -- visual review gate for the stick-figure pipeline.

WHY THIS EXISTS
    ffprobe/motion_audit prove a video is *structurally* valid. They prove
    nothing about whether the scene LOOKS right. This tool extracts evenly-spaced
    frames, runs cheap automated checks, then emits a REVIEW CHECKLIST for a
    human to eyeball the things automation cannot judge.

    It is a REVIEW AID, not a substitute for human eyes. The repo's per-episode
    review gate (human_review="required") remains the acceptance authority.

CHANGED 2026-11-10 (read-only audit findings):
  * With --project, review the DELIVERED out/*.mp4, not build/video_silent.mp4.
  * BLACK/WHITE frames and an aspect mismatch now exit 1.
  * CORRECTION (loop 2, independent falsifier): the first version ignored
    ffmpeg return codes, so a FAILED frame extraction produced (0,0,0) and was
    reported as a false BLACK frame. Both ffmpeg passes are now checked. It also
    labelled ANY portrait ratio "9:16"; a 2:3 frame would have passed. The
    aspect is now reduced by gcd and compared to the expected ratio string.

USAGE
    python tools/review_frames.py --project projects/my_episode [--aspect 9:16]
    python tools/review_frames.py --video build/video_silent.mp4 [--count 6]

Exit: 0 = measurable checks pass; 1 = black/white frame, aspect mismatch,
      ambiguous deliverable, or a failed frame extraction. The human checklist
      is NEVER auto-checked.

DEPENDS ONLY ON: ffmpeg + ffprobe on PATH (no numpy needed).
"""
import argparse
import json
import math
import os
import subprocess
import sys

EXPECTED_ASPECTS = {"9:16": "vertical (h>w)", "16:9": "horizontal (w>h)"}


def aspect_label(w, h):
    """Reduced ratio string, e.g. 1080x1920 -> '9:16'. Any odd ratio stays exact."""
    g = math.gcd(int(w), int(h)) or 1
    return "%d:%d" % (int(w) // g, int(h) // g)


def pick_video(project):
    """Pure filesystem choice: review the DELIVERED out/*.mp4, not a pre-mux take.

    Returns (path, is_delivered, note). Raises ValueError when the deliverable is
    ambiguous. Never opens a video (safe to unit-test with synthetic files).
    """
    outdir = os.path.join(project, "out")
    cands = sorted(f for f in os.listdir(outdir) if f.lower().endswith(".mp4")) \
        if os.path.isdir(outdir) else []
    if len(cands) == 1:
        return (os.path.join(outdir, cands[0]), True, "delivered out/ MP4")
    if len(cands) > 1:
        raise ValueError("multiple delivered MP4s in %s: %s -- pass --video explicitly"
                         % (outdir, cands))
    silent = os.path.join(project, "build", "video_silent.mp4")
    if os.path.exists(silent):
        return (silent, False,
                "FALLBACK: no out/ deliverable; reviewing the pre-mux silent take")
    return (None, False, "no video found in out/ or build/video_silent.mp4")


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ffprobe_json(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=width,height", "-of", "json", path])
    if r.returncode != 0:
        sys.exit(f"ffprobe failed: {r.stderr.decode(errors='ignore')}")
    return json.loads(r.stdout.decode())


def extract_frame(video, ts, out_png):
    """Write a PNG for human eyes and return 1x1 mean luma.

    A failed ffmpeg pass is a HARD error. The old code defaulted to (0,0,0) and
    reported a fabricated BLACK frame, hiding the real failure.
    """
    png = run(["ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", video,
               "-frames:v", "1", out_png])
    if png.returncode != 0:
        sys.exit("frame extraction FAILED at t=%.3f: %s"
                 % (ts, png.stderr.decode(errors="ignore")[-300:]))
    avg = run(["ffmpeg", "-ss", f"{ts:.3f}", "-i", video, "-frames:v", "1",
               "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
    if avg.returncode != 0 or len(avg.stdout) < 3:
        sys.exit("luma probe FAILED at t=%.3f (exit %d, %d bytes) -- refusing to "
                 "invent a BLACK frame" % (ts, avg.returncode, len(avg.stdout)))
    r, g, b = avg.stdout[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b  # 0..255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--project", help="project dir; prefers the delivered out/*.mp4")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--out", default=None)
    ap.add_argument("--aspect", default=None, help="expected aspect, e.g. 9:16")
    args = ap.parse_args()

    video = args.video
    is_delivered = None
    selection_note = "explicit --video"
    if not video and args.project:
        try:
            video, is_delivered, selection_note = pick_video(args.project)
        except ValueError as e:
            sys.exit("ERROR: " + str(e))
    if not video or not os.path.exists(video):
        sys.exit("ERROR: supply --video <mp4> or --project <dir> with a built video.")
    print("REVIEW TARGET:", video, "|", selection_note)

    out = args.out or (os.path.join(args.project, "build", "review")
                       if args.project else os.path.dirname(video) + "/review")
    os.makedirs(out, exist_ok=True)

    info = ffprobe_json(video)
    dur = float(info["format"]["duration"])
    # A muxed deliverable may list the audio stream first: pick a video stream.
    st = next((s for s in info["streams"] if "width" in s), info["streams"][0])
    w, h = st["width"], st["height"]
    actual_aspect = aspect_label(w, h)
    aspect_ok = (args.aspect is None) or (actual_aspect == args.aspect)

    frames = []
    for i in range(args.count):
        ts = dur * (i + 0.5) / args.count
        png = os.path.join(out, f"frame_{i+1:02d}.png")
        lum = extract_frame(video, ts, png)
        flag = "BLACK" if lum < 8 else ("WHITE" if lum > 247 else "ok")
        frames.append({"t": round(ts, 2), "file": png,
                       "luma": round(lum, 1), "flag": flag})

    black = [f for f in frames if f["flag"] == "BLACK"]
    white = [f for f in frames if f["flag"] == "WHITE"]

    report = {
        "video": video, "selection_note": selection_note,
        "is_delivered_file": is_delivered,
        "duration_s": round(dur, 3),
        "width": w, "height": h, "actual_aspect": actual_aspect,
        "expected_aspect": args.aspect, "aspect_ok": aspect_ok,
        "frame_count_checked": args.count,
        "black_frames": len(black), "white_frames": len(white),
        "frames": frames,
    }
    with open(os.path.join(out, "review.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # ---- Human/vision review checklist (the part automation CANNOT judge) ----
    print(f"\n=== VISUAL REVIEW GATE: {os.path.basename(video)} ===")
    print(f"  size        : {w}x{h}  aspect={actual_aspect}"
          + (f"  (expected {args.aspect})" if args.aspect else ""))
    print(f"  duration    : {dur:.3f}s")
    print(f"  frames pulled: {args.count} -> {out}")
    print(f"  auto checks : black={len(black)} white={len(white)}  | aspect_ok = {aspect_ok}")
    print("\n  --- MANUAL / VISION CHECKLIST (automation cannot judge these) ---")
    print("  [ ] Characters present as the script/shot-list requires?")
    print("  [ ] Character identity consistent (signature colours from cast.js)?")
    print("  [ ] Composition balanced; nothing cut off or floating?")
    print("  [ ] Captions / on-screen text legible and not overlapping?")
    print("  [ ] Visual style matches config (e.g. 'dusk') across shots?")
    print("  [ ] No unintended black/blank stretches? (auto: "
          + ("PASS" if not black else f"FAIL {len(black)}") + ")")
    print("  [ ] Aspect correct for target platform? (auto: "
          + ("PASS" if aspect_ok else "FAIL") + ")")
    print("  [ ] MUSIC present & at target loudness? (only if audio stream;")
    print("       N/A for silent video -- re-run after enabling music + mix.py)")
    print(f"\n  Written: {os.path.join(out, 'review.json')}")
    print("  >>> Eyeball the pulled frames; a human (or vision model) must")
    print("      confirm the unchecked items before this is 'accepted'.")

    if is_delivered is False:
        print("  WARNING: this is NOT the delivered out/ MP4. Approval of these "
              "frames does NOT approve the muxed deliverable.")

    # A review aid that cannot fail is not a gate. Fatal on defects it CAN
    # measure; the checklist above remains a human act.
    failures = []
    if black:
        failures.append(f"{len(black)} BLACK frame(s)")
    if white:
        failures.append(f"{len(white)} WHITE frame(s)")
    if not aspect_ok:
        failures.append(f"aspect {actual_aspect} != expected {args.aspect}")
    if failures:
        print("\nVISUAL REVIEW GATE: FAIL -- " + "; ".join(failures))
        return 1
    print("VISUAL REVIEW GATE: automated checks PASS (human checklist still unchecked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
