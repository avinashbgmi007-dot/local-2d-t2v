#!/usr/bin/env python3
"""
review_frames.py — visual review gate for the stick-figure pipeline.

WHY THIS EXISTS
    ffprobe/motion_audit prove a video is *structurally* valid (dims, duration,
    motion present). They prove nothing about whether the scene LOOKS right:
    are characters present, is composition balanced, is text legible, is the
    style consistent. This tool extracts evenly-spaced frames and runs cheap
    automated checks (black/dead frames, aspect), then emits a REVIEW CHECKLIST
    for a human (or vision model) to eyeball the things automation cannot judge.

    It is a REVIEW AID, not a substitute for human eyes. The repo's per-episode
    review gate (human_review="required") remains the acceptance authority.

USAGE
    python tools/review_frames.py --video build/video_silent.mp4 [--count 6]
                                  [--out build/review] [--aspect 9:16]

    For a project dir instead of a bare video:
    python tools/review_frames.py --project projects/my_episode

DEPENDS ONLY ON: ffmpeg + ffprobe on PATH (no numpy needed).
"""
import argparse
import json
import os
import subprocess
import sys

EXPECTED_ASPECTS = {"9:16": "vertical (h>w)", "16:9": "horizontal (w>h)"}


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ffprobe_json(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=width,height", "-of", "json", path])
    if r.returncode != 0:
        sys.exit(f"ffprobe failed: {r.stderr.decode(errors='ignore')}")
    return json.loads(r.stdout.decode())


def extract_frame(video, ts, out_png):
    # Extract one frame AND capture its 1x1 average colour in the same pass.
    cmd = ["ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", video, "-frames:v", "1",
           "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", out_png]
    # We need both the PNG (for eyeballing) and the avg colour.
    # Do the PNG first, then a separate tiny rawvideo pass for the average.
    run(["ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", video, "-frames:v", "1",
         out_png])
    avg = run(["ffmpeg", "-ss", f"{ts:.3f}", "-i", video, "-frames:v", "1",
               "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
    r, g, b = avg.stdout[:3] if len(avg.stdout) >= 3 else (0, 0, 0)
    lum = 0.299 * r + 0.587 * g + 0.114 * b  # 0..255
    return lum


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--project", help="project dir; uses its build/video_silent.mp4")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--out", default=None)
    ap.add_argument("--aspect", default=None, help="expected aspect, e.g. 9:16")
    args = ap.parse_args()

    video = args.video
    if not video and args.project:
        video = os.path.join(args.project, "build", "video_silent.mp4")
    if not video or not os.path.exists(video):
        sys.exit("ERROR: supply --video <mp4> or --project <dir> with a built video.")

    out = args.out or (os.path.join(args.project, "build", "review")
                       if args.project else os.path.dirname(video) + "/review")
    os.makedirs(out, exist_ok=True)

    info = ffprobe_json(video)
    dur = float(info["format"]["duration"])
    st = info["streams"][0]
    w, h = st["width"], st["height"]
    actual_aspect = "9:16" if h > w else "16:9"

    frames = []
    for i in range(args.count):
        ts = dur * (i + 0.5) / args.count
        png = os.path.join(out, f"frame_{i+1:02d}.png")
        lum = extract_frame(video, ts, png)
        flag = "BLACK" if lum < 8 else ("WHITE" if lum > 247 else "ok")
        frames.append({"t": round(ts, 2), "file": png,
                       "luma": round(lum, 1), "flag": flag})

    black = [f for f in frames if f["flag"] == "BLACK"]
    aspect_ok = (args.aspect is None) or (actual_aspect == args.aspect)

    report = {
        "video": video, "duration_s": round(dur, 3),
        "width": w, "height": h, "actual_aspect": actual_aspect,
        "expected_aspect": args.aspect, "aspect_ok": aspect_ok,
        "frame_count_checked": args.count,
        "black_frames": len(black),
        "frames": frames,
    }
    with open(os.path.join(out, "review.json"), "w") as f:
        json.dump(report, f, indent=2)

    # ---- Human/vision review checklist (the part automation CANNOT judge) ----
    print(f"\n=== VISUAL REVIEW GATE: {os.path.basename(video)} ===")
    print(f"  size        : {w}x{h}  aspect={actual_aspect}"
          + (f"  (expected {args.aspect})" if args.aspect else ""))
    print(f"  duration    : {dur:.3f}s")
    print(f"  frames pulled: {args.count} -> {out}")
    print(f"  auto checks : black/dead frames = {len(black)}  | aspect_ok = {aspect_ok}")
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
    print("       N/A for silent video — re-run after enabling music + mix.py)")
    print(f"\n  Written: {os.path.join(out, 'review.json')}")
    print("  >>> Eyeball the pulled frames; a human (or vision model) must")
    print("      confirm the unchecked items before this is 'accepted'.")


if __name__ == "__main__":
    main()
