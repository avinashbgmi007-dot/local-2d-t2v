#!/usr/bin/env python3
"""frame_qa.py -- per-frame quality assurance for rendered videos.

Report-only: never wired into generate.py. Checks black/white frames, pop (transient
spike) frames, and frozen runs (SAD-based frame difference).

Resolution: 32x18 (576 px). 8x8 was too coarse -- small animation averaged away.
Thresholds calibrated on cine_release SAD distribution (see --diag).

Pop detection LIMITATIONS:
  - Needs both neighbours (i-1 and i+1): first and last frames cannot be pops.
  - A 2-frame spike is missed (second spike frame has high SAD from first spike,
    not from prior level).
  - Only flags spikes where before-after SAD < SAD_POP // 2 (returns to prior level).
"""
import argparse, json, os, subprocess, sys

FRAME_W, FRAME_H = 32, 18
FRAME_SIZE = FRAME_W * FRAME_H
# Calibrated on cine_release at 32x18: true freeze SAD~0, small anim p5=58
SAD_FREEZE = 50
# Significant change; pop if the spike returns to prior level (sad_ba < SAD_POP//2)
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

def load_shots(shots_path):
    if not shots_path or not os.path.exists(shots_path):
        return []
    try:
        data = json.load(open(shots_path, encoding="utf-8"))
    except Exception:
        return []
    return data.get("shots", data if isinstance(data, list) else [])

def nearest_shot(t, shots):
    for sh in shots:
        s = float(sh.get("start", 0))
        e = float(sh.get("end", s))
        if s - 0.05 <= t <= e + 0.05:
            return sh, "in-shot"
    best = None
    best_dist = float("inf")
    for sh in shots:
        for b in (float(sh.get("start", 0)), float(sh.get("end", 0))):
            if abs(b - t) < best_dist:
                best_dist = abs(b - t)
                best = sh
    return best, "boundary"

def shot_transition_type(sh):
    if not sh:
        return "unknown"
    t = sh.get("in", {})
    if isinstance(t, dict):
        return t.get("type", "cut")
    return "cut"

def shot_transition_dur(sh):
    """Return the declared transition duration (seconds) for a shot, or 0.0."""
    if not sh:
        return 0.0
    t = sh.get("in", {})
    if isinstance(t, dict):
        d = t.get("dur")
        if d is not None:
            try:
                return float(d)
            except (TypeError, ValueError):
                pass
    # Default durations for transitions without explicit dur
    typ = shot_transition_type(sh)
    if typ in ("fade", "dip"):
        return 0.5
    if typ == "flash":
        return 0.1
    return 0.0

def analyze_black_runs(black_frames, ts_list, shots, dur=None, lumas=None):
    """Classify black frame runs as expected (declared transition), end_tail,
    undeclared_fade (ramp at shot start, not declared), or finding (hard cut).

    A run is 'expected' only if it is anchored to a shot START boundary and that
    shot declares a non-cut transition (fade/dip/flash) whose duration covers
    the run.  A run at the very end of the video is 'end_tail'.  A run at a shot
    start that ramps in luma (fade pattern) but is declared as 'cut' is
    'undeclared_fade' (info, not a quality finding).  Otherwise 'finding'.
    """
    if not black_frames:
        return []
    if dur is None:
        dur = ts_list[-1] if ts_list else 0.0
    if lumas is None:
        lumas = [0.0] * (ts_list[-1] + 1 if ts_list else 0)
    runs = []
    current = [black_frames[0]]
    for bf in black_frames[1:]:
        if bf[0] == current[-1][0] + 1:
            current.append(bf)
        else:
            runs.append(current)
            current = [bf]
    runs.append(current)
    result = []
    for run in runs:
        mid_t = run[len(run) // 2][1]
        run_start_t = run[0][1]
        run_end_t = run[-1][1]
        sh, loc = nearest_shot(mid_t, shots)
        trans = shot_transition_type(sh)
        shot_id = sh.get("id", "?") if sh else "?"
        trans_dur = shot_transition_dur(sh)

        # End tail: run is within the last 1.5s of the video
        is_end_tail = (run_end_t >= dur - 1.5) and (dur > 0)

        # Anchored expected: run must be near a shot START boundary
        # and within the declared transition duration
        is_anchored_expected = False
        if sh and trans in ("fade", "dip", "flash"):
            shot_start = float(sh.get("start", 0))
            if abs(run_start_t - shot_start) <= trans_dur + 0.2:
                is_anchored_expected = True

        # Undeclared fade: run at shot start with ramping luma (fade pattern)
        # but shot declares 'cut' (or no transition)
        is_undeclared_fade = False
        if not is_anchored_expected and sh:
            shot_start = float(sh.get("start", 0))
            if abs(run_start_t - shot_start) <= 0.3:
                # Check if luma ramps after the run (fade pattern)
                next_idx = run[-1][0] + 1
                if next_idx < len(lumas):
                    post_luma = lumas[next_idx]
                    last_black_luma = run[-1][2]
                    if post_luma > last_black_luma + 3:
                        is_undeclared_fade = True

        if is_anchored_expected:
            classification = "expected"
        elif is_undeclared_fade:
            classification = "undeclared_fade"
        elif is_end_tail:
            classification = "end_tail"
        else:
            classification = "finding"

        result.append({
            "start_idx": run[0][0],
            "end_idx": run[-1][0],
            "start_t": run[0][1],
            "end_t": run[-1][1],
            "n_frames": len(run),
            "shot_id": shot_id,
            "transition": trans,
            "location": loc,
            "classification": classification,
        })
    return result

def analyze_frames(frames, fps, dur, freeze_wins, shots=None):
    """Analyze frames and return a findings dict."""
    n_frames = len(frames)
    lumas = [sum(f) / len(f) for f in frames]
    ts_list = [min(i / fps, dur) for i in range(n_frames)]
    sads = [compute_sad(frames[i], frames[i - 1]) for i in range(1, n_frames)]

    black = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] < 8]
    white = [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] > 247]

    pops = []
    if len(sads) > 2:
        for i in range(1, len(sads) - 1):
            if sads[i] >= SAD_POP:
                if i + 1 < len(frames):
                    sad_ba = compute_sad(frames[i - 1], frames[i + 1])
                    if sad_ba < SAD_POP // 2:
                        pops.append((i + 1, ts_list[i + 1], lumas[i], lumas[i + 1]))

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
                        run_ts = ts_list[run_start:run_start + run_len]
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
                run_ts = ts_list[run_start:]
                exempt = all(in_freeze_window(t, freeze_wins) for t in run_ts)
                if not exempt:
                    if run_len >= 12:
                        frozen_runs.append((run_start, len(sads), run_ts[0], run_ts[-1], run_len))
                    else:
                        frozen_info.append((run_start, len(sads), run_ts[0], run_ts[-1], run_len))

    black_runs = analyze_black_runs(black, ts_list, shots or [], dur, lumas)

    return {
        "black": black,
        "white": white,
        "pops": pops,
        "frozen_runs": frozen_runs,
        "frozen_info": frozen_info,
        "black_runs": black_runs,
        "lumas": lumas,
        "sads": sads,
        "ts_list": ts_list,
    }

def sad_distribution(sads):
    import statistics
    s = sorted(sads)
    lines = []
    lines.append("  SAD distribution (%d transitions):" % len(sads))
    lines.append("    min=%d max=%d mean=%.0f median=%.0f" % (min(sads), max(sads), statistics.mean(sads), statistics.median(sads)))
    lines.append("    p5=%d p10=%d p25=%d p50=%d p75=%d p90=%d p95=%d" % (
        s[int(len(s)*0.05)], s[int(len(s)*0.1)], s[int(len(s)*0.25)],
        s[int(len(s)*0.5)], s[int(len(s)*0.75)], s[int(len(s)*0.9)],
        s[int(len(s)*0.95)]))
    buckets = [0, 10, 25, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    lines.append("    histogram (transitions >= threshold):")
    for b in buckets:
        c = sum(1 for v in sads if v >= b)
        lines.append("      >= %6d: %d" % (b, c))
    return "\n".join(lines)

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
    ap.add_argument("--diag", action="store_true", help="print SAD distribution")
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
    shots = load_shots(shots_path)

    if args.count and args.count > 0:
        ts_list = [dur * (i + 0.5) / args.count for i in range(args.count)]
        lumas = []
        for t in ts_list:
            r = run(["ffmpeg", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
            if r.returncode != 0 or len(r.stdout) < 3:
                sys.exit("luma probe FAILED at t=%.3f" % t)
            rr, gg, bb = r.stdout[:3]
            lumas.append(0.299 * rr + 0.587 * gg + 0.114 * bb)
        # build minimal result for count mode
        result = {"black": [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] < 8],
                  "white": [(i, ts_list[i], lumas[i]) for i in range(len(lumas)) if lumas[i] > 247],
                  "pops": [], "frozen_runs": [], "frozen_info": [], "black_runs": [],
                  "lumas": lumas, "sads": [], "ts_list": ts_list}
        frames = None
    else:
        frames = extract_all_frames(video)
        result = analyze_frames(frames, fps, dur, freeze_wins, shots)

    black = result["black"]
    white = result["white"]
    pops = result["pops"]
    frozen_runs = result["frozen_runs"]
    frozen_info = result["frozen_info"]
    black_runs = result["black_runs"]
    lumas = result["lumas"]
    ts_list_out = result["ts_list"]
    sads = result["sads"]

    n = len(lumas)
    print("FRAME QA: %s  (dur=%.2fs, frames=%d, fps=%.1f, res=%dx%d)" % (os.path.basename(video), dur, n, fps, FRAME_W, FRAME_H))
    print("  black frames : %d" % len(black))
    print("  white frames : %d" % len(white))
    print("  pop frames   : %d" % len(pops))
    print("  frozen runs  : %d  (freeze exemptions loaded: %d)" % (len(frozen_runs), len(freeze_wins)))
    if frozen_info:
        print("  frozen info  : %d (3-11 frame runs, not findings)" % len(frozen_info))
    if args.diag and sads:
        print(sad_distribution(sads))
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
    if black_runs:
        print("  black runs:")
        for br in black_runs:
            cls = br["classification"]
            if cls == "expected":
                status = "expected"
            elif cls == "undeclared_fade":
                status = "undeclared_fade (info)"
            elif cls == "end_tail":
                status = "end_tail"
            else:
                status = "FINDING"
            print("    %s: frames %d-%d t=%.2f..%.2f (%d fr) shot=%s transition=%s" % (
                status, br["start_idx"], br["end_idx"], br["start_t"], br["end_t"],
                br["n_frames"], br["shot_id"], br["transition"]))

    # findings: black runs classified as "finding" + white + pops + frozen_runs
    # end_tail runs are reported but not findings (they are expected at video end)
    black_findings = sum(1 for br in black_runs if br["classification"] == "finding")
    findings = black_findings + len(white) + len(pops) + len(frozen_runs)
    if findings == 0:
        print("FRAME QA: PASS (no unexplained findings)")
        return 0
    print("FRAME QA: %d finding(s)" % findings + (" (strict -> FAIL)" if args.strict else " (report-only)"))
    return 1 if args.strict else 0

if __name__ == "__main__":
    sys.exit(main())