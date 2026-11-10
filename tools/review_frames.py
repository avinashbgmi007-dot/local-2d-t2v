#!/usr/bin/env python3
"""Extract review frames and fail on technical review errors.

  python tools/review_frames.py --project projects/foo [--count 6]
  python tools/review_frames.py --video build/video_silent.mp4 --aspect 9:16

This is a review AID, not human acceptance. Average luma is a coarse blank-frame
signal, not a proof that a frame contains the intended subject. Intentional fades
may need human review; use --allow-dark only when that is an explicit decision.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ffmpeg_exe():
    return os.environ.get("FFMPEG_BINARY") or "ffmpeg"


def probe(video):
    result = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                  "format=duration:stream=width,height", "-of", "json", str(video)])
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("no video stream")
    duration = float(data["format"]["duration"])
    if duration <= 0:
        raise RuntimeError("video has no positive duration")
    return duration, int(streams[0]["width"]), int(streams[0]["height"])


def extract_frame(video, ts, out_png):
    image = run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{ts:.3f}", "-i", str(video),
                 "-frames:v", "1", str(out_png)])
    if image.returncode or not Path(out_png).is_file():
        raise RuntimeError(f"frame extraction at {ts:.3f}s failed: {image.stderr.decode(errors='replace')}")
    avg = run([ffmpeg_exe(), "-v", "error", "-ss", f"{ts:.3f}", "-i", str(video), "-frames:v", "1",
               "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
    if avg.returncode or len(avg.stdout) < 3:
        raise RuntimeError(f"luma extraction at {ts:.3f}s failed: {avg.stderr.decode(errors='replace')}")
    r, g, b = avg.stdout[:3]
    return .299 * r + .587 * g + .114 * b


def cmd_review(args):
    video = args.video or (Path(args.project) / "build/video_silent.mp4" if args.project else None)
    if not video or not Path(video).is_file():
        print("ERROR: supply an existing --video or --project with build/video_silent.mp4")
        return 2
    if args.count < 1 or args.count > 100:
        print("ERROR: --count must be 1..100")
        return 2
    out = Path(args.out or (Path(args.project) / "build/review" if args.project else Path(video).parent / "review"))
    try:
        duration, width, height = probe(video)
        out.mkdir(parents=True, exist_ok=True)
        frames = []
        for i in range(args.count):
            ts = duration * (i + .5) / args.count
            png = out / f"frame_{i + 1:02d}.png"
            luma = extract_frame(video, ts, png)
            frames.append({"t": round(ts, 3), "file": str(png), "luma": round(luma, 2),
                           "flag": "BLACK" if luma < 8 else "WHITE" if luma > 247 else "ok"})
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print("REVIEW FAILED:", exc)
        return 1
    orientation = "9:16" if height > width else "16:9" if width > height else "1:1"
    aspect_ok = args.aspect is None or orientation == args.aspect
    dark = [f for f in frames if f["flag"] != "ok"]
    technical_pass = aspect_ok and (not dark or args.allow_dark)
    report = {"schema": "aitrends-frame-review-v2", "video": str(video), "duration_s": duration,
              "width": width, "height": height, "actual_aspect": orientation,
              "expected_aspect": args.aspect, "aspect_ok": aspect_ok,
              "frames": frames, "blank_candidates": len(dark), "allow_dark": args.allow_dark,
              "technical_pass": technical_pass, "human_review": "required; technical checks are not acceptance"}
    (out / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"REVIEW: {width}x{height}, {duration:.3f}s, {len(frames)} frames -> {out}")
    print(f"  aspect {'PASS' if aspect_ok else 'FAIL'}; blank candidates {len(dark)}")
    print("  Human checklist: subjects, identity, composition, text, style, intentional holds/fades, audio.")
    print("  Technical checks are not acceptance. Open the frames before approving.")
    return 0 if technical_pass else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video")
    ap.add_argument("--project")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--out")
    ap.add_argument("--aspect", choices=["16:9", "9:16"])
    ap.add_argument("--allow-dark", action="store_true", help="explicitly allow sampled dark/white frames for human review")
    return cmd_review(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
