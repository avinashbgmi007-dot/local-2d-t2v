#!/usr/bin/env python3
"""frame_qa.py -- frame-level quality gate for the stick-figure pipeline.

Detects, per frame of a video (full scan, not sparse sampling):
  * BLACK  (luma < 8)
  * WHITE  (luma > 247)
  * FROZEN (consecutive frames with near-identical luma for a long run)
  * POP    (sudden luma jump between consecutive frames)

Intentional freezes declared in shots.json (`freeze` field) are EXEMPT from the
FROZEN check only. Black/white/pop are never exempted.

USAGE
    python tools/frame_qa.py --project projects/my_episode
    python tools/frame_qa.py --video build/video_silent.mp4 [--shots story/shots.json]
    python tools/frame_qa.py ... --strict   # exit 1 on any unexplained finding

Default mode is REPORT-ONLY (exit 0) so existing projects are not broken while
the detector is being calibrated. Promote to fatal (--strict) once all existing
projects pass with zero unexplained flags.

DEPENDS ONLY ON: ffmpeg + ffprobe on PATH (no numpy).
"""
import argparse
import json
import math
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ffprobe_json(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=width,height,r_frame_rate", "-of", "json", path])
    if r.returncode != 0:
        sys.exit("ffprobe failed: " + r.stderr.decode(errors="ignore"))
    return json.loads(r.stdout.decode())


def parse_fps(info):
    """Extract fps from ffprobe output, defaulting to 30."""
    streams = info.get("streams", [])
    if streams:
        rate = streams[0].get("r_frame_rate", "30/1")
        if "/" in rate:
            num, den = rate.split("/")
            try:
                return float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass
    return 30.0


def extract_all_lumas(video, fps):
    """Extract per-frame luma for every frame using a single ffmpeg pass.

    Outputs 1 byte per frame (grayscale 1x1). Fast: ~1-3s for a 30s video.
    """
    r = run(["ffmpeg", "-i", video, "-vf", "scale=1:1,format=gray",
             "-f", "rawvideo", "-pix_fmt", "gray8", "-"])
    if r.returncode != 0 or len(r.stdout) == 0:
        sys.exit("luma extraction FAILED: " + r.stderr.decode(errors="ignore")[:200])
    return list(r.stdout)

def extract_luma(video, ts):
    """Backward-compat: extract luma at a single timestamp."""
    r = run(["ffmpeg", "-ss", f"{ts:.3f}", "-i", video, "-frames:v", "1",
             "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
    if r.returncode != 0 or len(r.stdout) < 3:
        sys.exit("luma probe FAILED at t=%.3f" % ts)
    rr, gg, bb = r.stdout[:3]
    return 0.299 * rr + 0.587 * gg + 0.114 * bb


def load_freeze_times(shots_path):
    """Return a list of (t_start, t_end) windows that are declared freezes.

    A freeze makes the visual clock clamp from `at`/`u*duration` to end of shot.
    We mark a window from the freeze point to the shot end as exempt (frozen
    check only). If shots.json is missing/unparseable, return [] (no exemptions).
    """
    if not shots_path or not os.path.exists(shots_path):
        return []
    try:
        data = json.load(open(shots_path, encoding="utf-8"))
    except Exception:
        return []
    shots = data.get("shots", data if isinstance(data, list) else [])
    wins = []
    for sh in shots:
        try:
            s = float(sh.get("start", 0))
            e = float(sh.get("end", s))
        except (TypeError, ValueError):
            continue
        fr = sh.get("freeze")
        if fr is None:
            continue
        # resolve freeze point in shot-local seconds
        if isinstance(fr, (int, float)):
            at = s + float(fr) * (e - s)
        elif isinstance(fr, dict):
            if "u" in fr:
                at = s + float(fr["u"]) * (e - s)
            elif "at" in fr:
                at = s + float(fr["at"])
            else:
                at = s
        else:
            at = s
        if at < s:
            at = s
        if at > e:
            at = e
        wins.append((at, e))
    return wins


def in_freeze_window(t, wins):
    for a, b in wins:
        if a - 0.5 <= t <= b + 0.5:
            return True
    return False


def pick_video(project):
    outdir = os.path.join(project, "out")
    if os.path.isdir(outdir):
        cands = sorted(f for f in os.listdir(outdir) if f.lower().endswith(".mp4"))
        if len(cands) == 1:
            return os.path.join(outdir, cands[0])
    silent = os.path.join(project, "build", "video_silent.mp4")
    if os.path.exists(silent):
        return silent
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--project")
    ap.add_argument("--shots", help="path to shots.json for freeze exemption")
    ap.add_argument("--count", type=int, default=0,
                    help="if >0, sample this many frames instead of full scan (default: full scan)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on unexplained findings (default: report-only)")
    args = ap.parse_args()

    video = args.video
    shots_path = args.shots
    if args.project:
        if not video:
            video = pick_video(args.project)
        if not shots_path:
            cand = os.path.join(args.project, "story", "shots.json")
            if os.path.exists(cand):
                shots_path = cand

    if not video or not os.path.exists(video):
        sys.exit("ERROR: supply --video <mp4> or --project <dir> with a built video.")

    info = ffprobe_json(video)
    dur = float(info["format"]["duration"])
    fps = parse_fps(info)
    freeze_wins = load_freeze_times(shots_path)

    if args.count and args.count > 0:
        # sparse sampling (backward compat)
        ts_list = [dur * (i + 0.5) / args.count for i in range(args.count)]
        # extract per-timestamp luma
        lumas = []
        for t in ts_list:
            r = run(["ffmpeg", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                     "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
            if r.returncode != 0 or len(r.stdout) < 3:
                sys.exit("luma probe FAILED at t=%.3f" % t)
            rr, gg, bb = r.stdout[:3]
            lumas.append(0.299 * rr + 0.587 * gg + 0.114 * bb)
    else:
        # full per-frame scan
        raw = extract_all_lumas(video, fps)
        n_frames = len(raw)
        lumas = [float(b) for b in raw]  # gray8 = luma directly
        # build timestamps
        ts_list = [i / fps for i in range(n_frames)]
        # trim to video duration
        ts_list = [min(t, dur) for t in ts_list]

    black = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] < 8]
    white = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] > 247]

    # pop: sudden jump between consecutive frames
    pop_thresh = 40.0
    pops = []
    for i in range(1, len(lumas)):
        if abs(lumas[i] - lumas[i - 1]) >= pop_thresh:
            pops.append((i, ts_list[i], lumas[i - 1], lumas[i]))

    # frozen: run of consecutive frames with near-identical luma.
    frozen_runs = []
    run_start = None
    for i in range(1, len(lumas)):
        if abs(lumas[i] - lumas[i - 1]) < 1.0:
            if run_start is None:
                run_start = i - 1
        else:
            if run_start is not None and (i - 1 - run_start + 1) >= 3:
                run_ts = ts_list[run_start:i]
                exempt = all(in_freeze_window(t, freeze_wins) for t in run_ts)
                if not exempt:
                    frozen_runs.append((run_start, i - 1, run_ts[0], run_ts[-1]))
            run_start = None
    if run_start is not None and (len(lumas) - 1 - run_start + 1) >= 3:
        run_ts = ts_list[run_start:]
        exempt = all(in_freeze_window(t, freeze_wins) for t in run_ts)
        if not exempt:
            frozen_runs.append((run_start, len(lumas) - 1, run_ts[0], run_ts[-1]))

    print(f"FRAME QA: {os.path.basename(video)}  (dur={dur:.2f}s, frames={len(lumas)}, fps={fps:.1f})")
    print(f"  black frames : {len(black)}")
    print(f"  white frames : {len(white)}")
    print(f"  pop frames   : {len(pops)}")
    print(f"  frozen runs  : {len(frozen_runs)}  (freeze exemptions loaded: {len(freeze_wins)})")
    if black:
        for i, t, l in black[:10]:
            print(f"    BLACK  t={t:.2f} luma={l:.1f}")
    if white:
        for i, t, l in white[:10]:
            print(f"    WHITE  t={t:.2f} luma={l:.1f}")
    if pops:
        for i, t, a, b in pops[:10]:
            print(f"    POP    t={t:.2f} luma {a:.1f}->{b:.1f}")
    if frozen_runs:
        for s, e, ts, te in frozen_runs[:10]:
            print(f"    FROZEN t={ts:.2f}..{te:.2f} ({e-s+1} frames)")

    findings = len(black) + len(white) + len(pops) + len(frozen_runs)
    if findings == 0:
        print("FRAME QA: PASS (no unexplained findings)")
        return 0
    print(f"FRAME QA: {findings} finding(s)"
          + (" (strict -> FAIL)" if args.strict else " (report-only)"))
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())