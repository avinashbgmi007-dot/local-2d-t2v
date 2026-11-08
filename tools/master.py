#!/usr/bin/env python3
"""
master.py — hit the loudness target with a true-peak ceiling, and prove it.

WHY THIS EXISTS
    audio/mix.py normalises with a SINGLE-PASS `loudnorm`. Two problems:
      1. single-pass cannot know its own result, so it lands off target;
      2. it defaults to `normalization_type: dynamic`, which is a time-varying
         gain, not a fixed offset.
    Measured on projects/cine_mug: delivered -15.72 LUFS against a -14 target,
    with true peak at -1.40 dBTP — i.e. 1.72 dB too quiet AND 0.1 dB over the
    ceiling at the same time.

    mix.py is a PROTECTED file (tools/verify_kit.py pins it), so this is a
    wrapper. It never edits the mixer; it re-masters the mixer's own output.

WHY NOT JUST ADD GAIN
    The material's crest factor is the binding constraint, not the code. On
    mix.wav: I=-15.67, TP=-1.48 -> 14.2 dB peak-to-loudness. Reaching -14 with
    TP <= -1.5 allows only 12.5 dB, so ~1.7 dB of peak control is unavoidable.
    Pure gain would push true peak to +0.32 dBTP and clip on decode.

CHAIN
    1. measure the input                       (loudnorm pass 1, JSON)
    2. two-pass loudnorm with those measurements
       (linear=false: only dynamic mode can hold a TP ceiling when crest binds)
    3. measure again; if still off, apply the RESIDUAL gain plus a limiter,
       recomputed from the base each time so corrections never compound
    4. remux: video stream COPIED, audio re-encoded once to AAC
    5. write build/master_report.json and print the achieved numbers

    Audio is sourced from build/mix.wav (lossless) rather than the AAC already
    muxed into the MP4, so there is exactly ONE lossy generation either way.

EXIT CODES
    0  within tolerance
    1  could not converge (the report says by how much) — an unattended run must
       not ship a mis-levelled master and call it success

USAGE
    python tools/master.py --project projects/foo
    python tools/master.py --project projects/foo --target -14 --tp -1.5
    python tools/master.py --project projects/foo --report-only
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

TOL_SOFT = 0.35   # apply a corrective pass beyond this
TOL_HARD = 0.80   # give up and fail beyond this


def _json_block(text):
    """loudnorm's print_format=json block is the last {...} in ffmpeg's stderr."""
    hits = re.findall(r"\{[^{}]*\}", text, re.S)
    for h in reversed(hits):
        try:
            d = json.loads(h)
        except Exception:
            continue
        if "input_i" in d:
            return d
    return None


def measure(path):
    """Integrated loudness + true peak of `path`, via loudnorm's analyser."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    d = _json_block(p.stderr or "")
    if not d:
        raise RuntimeError("could not measure %s:\n%s" % (path, (p.stderr or "")[-800:]))
    return {
        "i": float(d["input_i"]),
        "tp": float(d["input_tp"]),
        "lra": float(d["input_lra"]),
        "thresh": float(d["input_thresh"]),
        "offset": float(d.get("target_offset") or 0.0),
        "mode": d.get("normalization_type"),
    }


def two_pass(src, dst, target, tp, m):
    """loudnorm pass 2, using pass-1 measurements. linear=false is deliberate."""
    af = ("loudnorm=I=%s:TP=%s:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
          "measured_thresh=%s:offset=%s:linear=false" %
          (target, tp, m["i"], m["tp"], m["lra"], m["thresh"], m["offset"]))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af,
                    "-ar", "48000", dst], check=True)
    return af


def corrective(src, dst, gain_db, sample_limit_db):
    """Residual gain then a sample-peak limiter.

    alimiter is a SAMPLE-peak limiter, not a true-peak one, so inter-sample
    overshoot lands a little above the sample limit. Measured on this material:
    limit -1.8 dBFS -> true peak -1.74 dBTP, i.e. ~0.06 dB of overshoot. The
    caller passes a limit already below the true-peak ceiling to absorb that.
    """
    lim = 10 ** (sample_limit_db / 20.0)
    af = "volume=%.3fdB,alimiter=limit=%.6f:level=false:attack=5:release=60" % (gain_db, lim)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af,
                    "-ar", "48000", dst], check=True)
    return af


def video_of(project):
    """The delivered mp4 (mix.py writes out/<title>.mp4)."""
    outdir = os.path.join(project, "out")
    if not os.path.isdir(outdir):
        return None
    mp4s = [os.path.join(outdir, f) for f in os.listdir(outdir)
            if f.lower().endswith(".mp4") and not f.startswith("_")]
    if not mp4s:
        return None
    return max(mp4s, key=os.path.getmtime)


def duration_of(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float((p.stdout or "").strip().split(",")[0])
    except Exception:
        return 0.0


def frames_of(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return int((p.stdout or "").strip().split(",")[0])
    except Exception:
        return 0


def first_frame_hash(path):
    """Pixel hash of frame 0 — proves two files came from the same render."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1",
                        "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                       capture_output=True)
    return hashlib.sha256(p.stdout or b"").hexdigest()


def pick_video(P, delivered):
    """Prefer the renderer's own output when it holds MORE frames than the delivery.

    mix.py muxes with `-shortest`, so it trims the video to the audio length and
    drops the renderer's final frame (measured: 259 -> 258, 42 ms). mix.py is
    pinned by verify_kit, so this recovers the frame here instead.

    The guard is strict: only ever ADD frames back, and only when frame 0 is
    pixel-identical — which proves it is the same render and not a stale file.
    """
    cand = os.path.join(P, "build", "video_silent.mp4")
    if not os.path.exists(cand):
        return delivered, "delivered file (no render to recover from)"
    fc, fd = frames_of(cand), frames_of(delivered)
    if fc <= fd:
        return delivered, "delivered file (%d frames; render had %d)" % (fd, fc)
    if first_frame_hash(cand) != first_frame_hash(delivered):
        return delivered, "delivered file (render frame 0 differs — not the same take)"
    return cand, "render output (%d frames, recovering %d dropped by -shortest)" % (fc, fc - fd)


def remux(video, audio_wav, dst, dur=None):
    """Swap the audio, copy the video bit-for-bit. One AAC generation.

    No `-shortest`: that is what truncated the video in the first place. `-t` caps
    the output at the VIDEO length instead, so a shorter audio track simply ends
    early rather than shortening the picture.
    """
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", video, "-i", audio_wav,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-ar", "48000"]
    if dur:
        cmd += ["-t", "%.6f" % dur]
    cmd += ["-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)


def has_audio(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return bool((p.stdout or "").strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--target", type=float, default=None,
                    help="integrated LUFS target (default: config.loudness or -14)")
    ap.add_argument("--tp", type=float, default=-1.5, help="true-peak ceiling dBTP")
    ap.add_argument("--report-only", action="store_true",
                    help="measure and report; change nothing")
    a = ap.parse_args()

    P = os.path.abspath(a.project)
    cfgp = os.path.join(P, "config.json")
    cfg = json.load(open(cfgp, encoding="utf-8")) if os.path.exists(cfgp) else {}
    target = a.target if a.target is not None else float(cfg.get("loudness", -14))

    # build/ may not exist: it is gitignored, and prune.py removes it. Every
    # intermediate this tool writes goes there, so create it up front rather
    # than crashing on a delivery whose build/ was cleaned.
    os.makedirs(os.path.join(P, "build"), exist_ok=True)

    video = video_of(P)
    if not video:
        sys.exit("MASTER: no mp4 in %s/out — run mix.py first" % P)
    if not has_audio(video):
        sys.exit("MASTER: %s has NO audio stream — refusing to master a silent file"
                 % os.path.basename(video))

    # prefer the lossless mixer output over the AAC already in the mp4
    src = os.path.join(P, "build", "mix.wav")
    if not os.path.exists(src):
        src = os.path.join(P, "build", "_master_src.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn",
                        "-acodec", "pcm_s16le", src], check=True)
        print("MASTER: build/mix.wav missing — extracted audio from the mp4")

    print("MASTER %s" % os.path.basename(P))
    print("  target   : %.1f LUFS, true peak <= %.1f dBTP" % (target, a.tp))
    print("  source   : %s" % os.path.relpath(src, P).replace("\\", "/"))
    print("  video    : %s (stream will be COPIED)" % os.path.basename(video))

    if a.report_only:
        # Measure what was DELIVERED, not the pre-master source. Reporting mix.wav
        # here would call a correctly-mastered project "OFF TARGET", because
        # mix.wav still holds the un-mastered mix — a diagnostic describing a
        # different file than the one shipped is worse than no diagnostic.
        md = measure(video)
        d = md["i"] - target
        print("  delivered: %.2f LUFS, TP %.2f dBTP, LRA %.2f" %
              (md["i"], md["tp"], md["lra"]))
        print("  error    : %+.2f LU (%s)" %
              (d, "within tolerance" if abs(d) <= TOL_SOFT else "OFF TARGET"))
        return 0 if abs(d) <= TOL_HARD else 1

    m0 = measure(src)
    print("  before   : %.2f LUFS, TP %.2f dBTP, LRA %.2f (%s)" %
          (m0["i"], m0["tp"], m0["lra"], m0["mode"]))

    build = os.path.join(P, "build")
    base = os.path.join(build, "_master_base.wav")
    master_wav = os.path.join(build, "master.wav")

    vsrc, vnote = pick_video(P, video)
    print("  picture  : %s" % vnote)
    # cap at the VIDEO length, not the audio length. Fall back to the delivered
    # file's duration if ffprobe fails, otherwise `-t` is silently omitted and the
    # output is uncapped.
    dur = duration_of(vsrc) or duration_of(video)
    if not dur:
        print("  WARNING  : could not read a duration — output is NOT length-capped")

    # Never leave the delivery worse than we found it: a failed master must not
    # overwrite a working file with a louder-but-clipping one.
    backup = video + ".premaster"
    shutil.copyfile(video, backup)

    # DESIGN FOR THE ENCODED FILE, NOT THE WAV.
    # AAC adds inter-sample overshoot, so a wav sitting at exactly the ceiling ships
    # ABOVE it. Measured on real material: +0.03 dB on one project, +0.23 dB on
    # another. Pay the headroom up front, then verify on the delivered mp4, and buy
    # more headroom if the codec ate it.
    CODE_HEADROOM = 0.30
    chosen, shipped = None, None
    for attempt in range(1, 4):
        tp_design = a.tp - CODE_HEADROOM * attempt
        two_pass(src, base, target, tp_design, m0)
        mb = measure(base)
        wav, gain, limit, af = base, 0.0, None, "two-pass loudnorm"
        if abs(target - mb["i"]) > TOL_SOFT:
            # only correct loudness when it is actually off; the corrective stage
            # is a sample-peak limiter and can cost true peak for little gain
            gain = target - mb["i"]
            limit = tp_design
            cand = os.path.join(build, "_master_c.wav")
            af = corrective(base, cand, gain, limit)
            wav = cand
        shutil.copyfile(wav, master_wav)
        tmp = video + ".mastering.mp4"
        remux(vsrc, master_wav, tmp, dur)
        os.replace(tmp, video)

        shipped = measure(video)
        err = abs(target - shipped["i"])
        ok = err <= TOL_HARD and shipped["tp"] <= a.tp + 0.02
        print("  attempt%d : design TP %.2f -> wav %.2f LUFS / %.2f dBTP -> "
              "shipped %.2f LUFS / %.2f dBTP  %s"
              % (attempt, tp_design, mb["i"], mb["tp"],
                 shipped["i"], shipped["tp"], "OK" if ok else "retry"))
        chosen = {"mb": mb, "gain": gain, "limit": limit, "af": af,
                  "tp_design": tp_design, "ok": ok, "attempt": attempt}
        if ok:
            break

    if not chosen["ok"]:
        os.replace(backup, video)
        os.remove(backup)
        print("MASTER: no attempt met the spec (%.1f LUFS, TP <= %.1f dBTP). "
              "ORIGINAL RESTORED — nothing was shipped."
              % (target, a.tp), file=sys.stderr)
        return 1

    def vinfo(pth):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name,width,height,nb_frames",
                            "-show_entries", "format=duration",
                            "-of", "json", pth], capture_output=True, text=True)
        return json.loads(r.stdout or "{}")

    shipped_v = vinfo(video)   # the file that ships (video is copied, so equal)
    report = {
        "project": os.path.basename(P),
        "file": os.path.basename(video),
        "target_lufs": target,
        "true_peak_ceiling": a.tp,
        "input": m0,
        "two_pass": chosen["mb"],
        "pre_mux": chosen["mb"],
        "final": shipped,
        "attempts": chosen["attempt"],
        "codec_headroom_db": CODE_HEADROOM,
        "design_true_peak": chosen["tp_design"],
        "corrective": {"gain_db": chosen["gain"], "sample_limit_db": chosen["limit"],
                       "filter": chosen["af"]},
        "error_lu": round(shipped["i"] - target, 3),
        "passed": True,
        "video": shipped_v.get("streams", [{}])[0] if shipped_v.get("streams") else {},
        "video_source": vnote,
        "duration": float(shipped_v.get("format", {}).get("duration") or 0),
        "note": ("loudness and true peak measured on the DELIVERED mp4 (ffmpeg loudnorm, "
                 "BS.1770), not on the pre-encode wav; video stream copied, not re-encoded"),
    }
    rp = os.path.join(build, "master_report.json")
    json.dump(report, open(rp, "w", encoding="utf-8"), indent=2)

    print("  shipped  : %.2f LUFS, TP %.2f dBTP  (error %+.2f LU, PASS)"
          % (shipped["i"], shipped["tp"], shipped["i"] - target))
    print("  report   : %s" % os.path.relpath(rp, P).replace("\\", "/"))
    for f in (base, os.path.join(build, "_master_c.wav"), backup):
        os.path.exists(f) and os.remove(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
