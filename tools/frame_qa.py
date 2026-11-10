#!/usr/bin/env python3
"""frame_qa.py -- frame-level quality gate for the stick-figure pipeline.

Detects, per sampled frame of a video:
  * BLACK  (luma < 8)
  * WHITE  (luma > 247)
  * FROZEN (consecutive sampled frames with near-identical luma for a long run)
  * POP    (sudden luma jump between consecutive sampled frames)

Intentional freezes declared in shots.json (`freeze` field) are EXEMPT from the
FROZEN check only. Black/white/pop are never exempted.

USAGE
    python tools/frame_qa.py --project projects/my_episode [--count 12]
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
             "format=duration:stream=width,height", "-of", "json", path])
    if r.returncode != 0:
        sys.exit("ffprobe failed: " + r.stderr.decode(errors="ignore"))
    return json.loads(r.stdout.decode())


def extract_luma(video, ts):
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
    ap.add_argument("--count", type=int, default=12)
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
    freeze_wins = load_freeze_times(shots_path)

    ts_list = [dur * (i + 0.5) / args.count for i in range(args.count)]
    lumas = [extract_luma(video, t) for t in ts_list]

    black = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] < 8]
    white = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] > 247]

    # pop: sudden jump between consecutive sampled frames
    pop_thresh = 40.0
    pops = []
    for i in range(1, len(lumas)):
        if abs(lumas[i] - lumas[i - 1]) >= pop_thresh:
            pops.append((i, ts_list[i], lumas[i - 1], lumas[i]))

    # frozen: run of consecutive sampled frames with near-identical luma.
    # A declared freeze exempts the frozen check for those timestamps.
    frozen_runs = []
    run_start = None
    for i in range(1, len(lumas)):
        if abs(lumas[i] - lumas[i - 1]) < 1.0:
            if run_start is None:
                run_start = i - 1
        else:
            if run_start is not None and (i - 1 - run_start + 1) >= 3:
                # check exemption: if all timestamps in run are in freeze windows
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

    print(f"FRAME QA: {os.path.basename(video)}  (dur={dur:.2f}s, samples={len(lumas)})")
    print(f"  black frames : {len(black)}")
    print(f"  white frames : {len(white)}")
    print(f"  pop frames   : {len(pops)}")
    print(f"  frozen runs  : {len(frozen_runs)}  (freeze exemptions loaded: {len(freeze_wins)})")
    if black:
        for i, t, l in black:
            print(f"    BLACK  t={t:.2f} luma={l:.1f}")
    if white:
        for i, t, l in white:
            print(f"    WHITE  t={t:.2f} luma={l:.1f}")
    if pops:
        for i, t, a, b in pops:
            print(f"    POP    t={t:.2f} luma {a:.1f}->{b:.1f}")
    if frozen_runs:
        for s, e, ts, te in frozen_runs:
            print(f"    FROZEN t={ts:.2f}..{te:.2f}")

    findings = len(black) + len(white) + len(pops) + len(frozen_runs)
    if findings == 0:
        print("FRAME QA: PASS (no unexplained findings)")
        return 0
    print(f"FRAME QA: {findings} finding(s)"
          + (" (strict -> FAIL)" if args.strict else " (report-only)"))
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
