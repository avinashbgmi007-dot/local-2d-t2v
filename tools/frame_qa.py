#!/usr/bin/env python3
import argparse, json, os, subprocess, sys

FRAME_W, FRAME_H = 8, 8
FRAME_SIZE = FRAME_W * FRAME_H
SAD_FREEZE = 200
SAD_POP = 2000

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def ffprobe_json(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate", "-of", "json", path])
    if r.returncode != 0:
        sys.exit("ffprobe failed: " + r.stderr.decode(errors="ignore"))
    return json.loads(r.stdout.decode())

def parse_fps(info):
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

def extract_all_frames(video):
    r = run(["ffmpeg", "-i", video, "-vf", "scale=%d:%d,format=gray" % (FRAME_W, FRAME_H), "-f", "rawvideo", "-pix_fmt", "gray8", "-"])
    if r.returncode != 0 or len(r.stdout) == 0:
        sys.exit("frame extraction FAILED: " + r.stderr.decode(errors="ignore")[:200])
    n = len(r.stdout) // FRAME_SIZE
    return [r.stdout[i * FRAME_SIZE:(i + 1) * FRAME_SIZE] for i in range(n)]

def extract_luma(video, ts):
    r = run(["ffmpeg", "-ss", "%.3f" % ts, "-i", video, "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
    if r.returncode != 0 or len(r.stdout) < 3:
        sys.exit("luma probe FAILED at t=%.3f" % ts)
    rr, gg, bb = r.stdout[:3]
    return 0.299 * rr + 0.587 * gg + 0.114 * bb

def extract_all_lumas(video, fps=None):
    frames = extract_all_frames(video)
    return [sum(f) / len(f) for f in frames]

def compute_sad(a, b):
    return sum(abs(a[i] - b[i]) for i in range(len(a)))

def load_freeze_times(shots_path):
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
        if at < s: at = s
        if at > e: at = e
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
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--strict", action="store_true")
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
        ts_list = [dur * (i + 0.5) / args.count for i in range(args.count)]
        lumas = []
        for t in ts_list:
            r = run(["ffmpeg", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
            if r.returncode != 0 or len(r.stdout) < 3:
                sys.exit("luma probe FAILED at t=%.3f" % t)
            rr, gg, bb = r.stdout[:3]
            lumas.append(0.299 * rr + 0.587 * gg + 0.114 * bb)
        ts_list_out = ts_list
        sads = []
        frames = None
    else:
        frames = extract_all_frames(video)
        n_frames = len(frames)
        lumas = [sum(f) / len(f) for f in frames]
        ts_list_out = [i / fps for i in range(n_frames)]
        ts_list_out = [min(t, dur) for t in ts_list_out]
        sads = [compute_sad(frames[i], frames[i - 1]) for i in range(1, n_frames)]

    black = [(i, ts_list_out[i], lumas[i]) for i in range(len(lumas)) if lumas[i] < 8]
    white = [(i, ts_list_out[i], lumas[i]) for i in range(len(lumas)) if lumas[i] > 247]

    pops = []
    if frames is not None and len(sads) > 2:
        for i in range(1, len(sads) - 1):
            if sads[i] >= SAD_POP:
                if i + 1 < len(frames):
                    sad_ba = compute_sad(frames[i - 1], frames[i + 1])
                    if sad_ba < SAD_POP // 2:
                        pops.append((i + 1, ts_list_out[i + 1], lumas[i], lumas[i + 1]))

    frozen_runs = []
    frozen_info = []
    run_start = None
    if len(sads) > 0:
        for i in range(len(sads)):
            if sads[i] < SAD_FREEZE:
                if run_start is None:
                    run_start = i
            else:
                if run_start is not None:
                    run_len = i - run_start + 1
                    if run_len >= 3:
                        run_ts = ts_list_out[run_start:run_start + run_len]
                        exempt = all(in_freeze_window(t, freeze_wins) for t in run_ts)
                        if not exempt:
                            if run_len >= 12:
                                frozen_runs.append((run_start, run_start + run_len - 1, run_ts[0], run_ts[-1], run_len))
                            else:
                                frozen_info.append((run_start, run_start + run_len - 1, run_ts[0], run_ts[-1], run_len))
                    run_start = None
        if run_start is not None:
            run_len = len(sads) - run_start + 1
            if run_len >= 3:
                run_ts = ts_list_out[run_start:]
                exempt = all(in_freeze_window(t, freeze_wins) for t in run_ts)
                if not exempt:
                    if run_len >= 12:
                        frozen_runs.append((run_start, len(sads), run_ts[0], run_ts[-1], run_len))
                    else:
                        frozen_info.append((run_start, len(sads), run_ts[0], run_ts[-1], run_len))

    n = len(lumas)
    print("FRAME QA: %s  (dur=%.2fs, frames=%d, fps=%.1f)" % (os.path.basename(video), dur, n, fps))
    print("  black frames : %d" % len(black))
    print("  white frames : %d" % len(white))
    print("  pop frames   : %d" % len(pops))
    print("  frozen runs  : %d  (freeze exemptions loaded: %d)" % (len(frozen_runs), len(freeze_wins)))
    if frozen_info:
        print("  frozen info  : %d (3-11 frame runs, not findings)" % len(frozen_info))
    if black:
        for i, t, l in black[:10]:
            print("    BLACK  t=%.2f luma=%.1f" % (t, l))
    if white:
        for i, t, l in white[:10]:
            print("    WHITE  t=%.2f luma=%.1f" % (t, l))
    if pops:
        for i, t, a, b in pops[:10]:
            print("    POP    t=%.2f luma %.1f->%.1f" % (t, a, b))
    if frozen_runs:
        for s, e, ts, te, rl in frozen_runs[:10]:
            print("    FROZEN t=%.2f..%.2f (%d frames)" % (ts, te, rl))
    if frozen_info:
        for s, e, ts, te, rl in frozen_info[:5]:
            print("    info: short freeze t=%.2f..%.2f (%d frames)" % (ts, te, rl))

    findings = len(black) + len(white) + len(pops) + len(frozen_runs)
    if findings == 0:
        print("FRAME QA: PASS (no unexplained findings)")
        return 0
    print("FRAME QA: %d finding(s)" % findings + (" (strict -> FAIL)" if args.strict else " (report-only)"))
    return 1 if args.strict else 0

if __name__ == "__main__":
    sys.exit(main())
