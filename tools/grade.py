#!/usr/bin/env python3
"""Colour grade -- a post pass that makes a flat canvas look photographed.

Why this exists
---------------
Measured on four delivered stills against four reference frames at the same
540x960: our films were at 0.49x the saturation, 0.67x the tonal range and
0.56x the local contrast. Nothing in the renderer was wrong; the picture simply
had no grade. A flat fill stays a flat fill.

The maths is the fitted grade from `mromidev/claude-animated-shorts`
(templates/bridge/grade.ts, MIT). It was fitted against reference stills, so
the numbers are measured rather than invented, and they are reproduced here
exactly:

  1. an RGB tone curve: monotone cubic Hermite through 7 knots at
     x = 0, .1, .25, .5, .75, .9, 1 (Fritsch-Carlson tangents);
  2. saturation around luma Y' (Rec.709), with separate weights for
     shadows / mids / highlights;
  3. a three-way split tone: zero-luma Cb/Cr offsets per zone;
  4. an elliptical vignette.

It runs on DISPLAY-REFERRED values, exactly as theirs does: the frame is
already sRGB from the encoder, so the curve is applied to the encoded values
and the result is written back out. No linear round-trip is needed here
because our renderer never hands us linear frames.

Usage
-----
    python tools/grade.py --project projects/X                 # preset from the story
    python tools/grade.py --project projects/X --preset golden --amount 0.85
    python tools/grade.py --project projects/X --dry-run        # measure only

It writes `<video>_graded.mp4` next to the input and prints the measured
saturation / tonal range / local contrast before and after, so the pass is
graded by the same numbers that motivated it.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

# ---------------------------------------------------------------- presets ----
# Fitted by the upstream project's scripts/fit2.py; reproduced verbatim.
KX = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)

GRADES = {
    "day": {
        "ky": (0.0345, 0.1828, 0.3812, 0.6605, 0.8814, 0.9631, 1.0),
        "sat": (0.9831, 1.2727, 1.4573),
        "tintS": (-0.0291, 0.0411),
        "tintM": (0.0376, -0.0104),
        "tintH": (0.0144, -0.0047),
        "vig": (0.10, 0.45),
    },
    "golden": {
        "ky": (0.0311, 0.1877, 0.4017, 0.6754, 0.8750, 0.9582, 1.0),
        "sat": (0.8316, 0.8799, 1.7061),
        "tintS": (0.0528, 0.0004),
        "tintM": (0.0583, -0.0003),
        "tintH": (0.0, 0.0),
        "vig": (0.16, 0.40),
    },
}

# BT.709 zero-luma chroma basis, in sRGB-encoded units: unit Cb and unit Cr as
# RGB offsets that leave Y' untouched.
E_CB = (0.0, -0.18733, 1.8556)
E_CR = (1.5748, -0.46813, 0.0)

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def tint_rgb(cb, cr):
    """(Cb, Cr) -> an RGB offset with zero luma, exactly as tintRGB does."""
    return np.array([cb * E_CB[i] + cr * E_CR[i] for i in range(3)],
                    dtype=np.float32)


def monoTangents(ky):
    """Fritsch-Carlson monotone tangents -- same function as theirs.

    Monotone matters: an ordinary cubic spline overshoots between the knots and
    the overshoot shows up as a banded sky. This clamps the tangents so the
    curve can never reverse direction between two knots.
    """
    n = len(KX)
    h, d = [], []
    for k in range(n - 1):
        h.append(KX[k + 1] - KX[k])
        d.append((ky[k + 1] - ky[k]) / h[k])
    m = [0.0] * n
    m[0], m[n - 1] = d[0], d[n - 2]
    for k in range(1, n - 1):
        if d[k - 1] * d[k] <= 0:
            m[k] = 0.0
            continue
        w1 = 2 * h[k] + h[k - 1]
        w2 = h[k] + 2 * h[k - 1]
        m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    return m


def _hermite(v, x0, x1, y0, y1, m0, m1):
    h = x1 - x0
    t = (v - x0) / h
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * h * m0
            + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * h * m1)


def curve_lut(ky, size=256):
    """The 7-knot curve baked to a LUT. A LUT, not per-pixel spline maths:
    287 frames x 518k pixels is 148M evaluations otherwise."""
    m = monoTangents(ky)
    xs = np.linspace(0.0, 1.0, size, dtype=np.float64)
    out = np.empty(size, dtype=np.float64)
    for i, v in enumerate(xs):
        v = min(max(v, 0.0), 1.0)
        for k in range(len(KX) - 1):
            if v <= KX[k + 1] or k == len(KX) - 2:
                out[i] = _hermite(v, KX[k], KX[k + 1], ky[k], ky[k + 1],
                                  m[k], m[k + 1])
                break
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def vignette_mask(h, w, k, r0):
    """Elliptical radius normalised so the CORNERS sit at 1, as theirs does."""
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r = np.sqrt(xx * xx + yy * yy) * 0.70710678
    return (1.0 - k * smoothstep(r0, 1.0, r)).astype(np.float32)


# ------------------------------------------------------------------ grade ----
class Grader:
    """One preset, precomputed so a frame costs a few array ops."""

    def __init__(self, name="day", amount=1.0):
        p = GRADES[name]
        self.name = name
        self.amount = float(amount)
        self.lut = curve_lut(p["ky"])
        self.sat = p["sat"]
        self.tintS = tint_rgb(*p["tintS"])
        self.tintM = tint_rgb(*p["tintM"])
        self.tintH = tint_rgb(*p["tintH"])
        self.vig = p["vig"]
        self._mask = {}

    def apply(self, rgb):
        """rgb: HxWx3 uint8 sRGB -> HxWx3 uint8."""
        h, w = rgb.shape[:2]
        src = rgb.astype(np.float32) / 255.0

        idx = (src * 255.0).astype(np.int32)
        c = self.lut[np.clip(idx, 0, 255)]

        y = c @ LUMA
        wS = 1.0 - smoothstep(0.0, 0.55, y)
        wH = smoothstep(0.45, 1.0, y)
        wM = 1.0 - wS - wH
        s = (self.sat[1] + (self.sat[0] - self.sat[1]) * wS
             + (self.sat[2] - self.sat[1]) * wH)
        c = y[..., None] + s[..., None] * (c - y[..., None])

        c = (c + wS[..., None] * self.tintS
             + wM[..., None] * self.tintM
             + wH[..., None] * self.tintH)

        key = (h, w)
        if key not in self._mask:
            self._mask[key] = vignette_mask(h, w, *self.vig)[..., None]
        c = c * self._mask[key]

        if self.amount < 1.0:
            c = src + (c - src) * self.amount
        return (np.clip(c, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


# --------------------------------------------------------------- measurement --
def frame_metrics(rgb):
    """The three numbers this pass is judged on."""
    a = rgb.astype(np.float32) / 255.0
    mx, mn = a.max(2), a.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean()
    y = a @ LUMA
    h, w = y.shape
    hb, wb = h // 16 * 16, w // 16 * 16
    blocks = y[:hb, :wb].reshape(hb // 16, 16, wb // 16, 16).std(axis=(1, 3))
    q = (a * 31).astype(np.uint8)
    uniq = len(np.unique(q.reshape(-1, 3), axis=0))
    return {"sat": float(sat), "lum_std": float(y.std()),
            "lcontrast": float(blocks.mean()), "colours": int(uniq)}


# -------------------------------------------------------------------- io ----
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate",
                        "-of", "json", path], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den)


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def read_frames(path, w, h):
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path,
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)


def pick_video(project):
    out = os.path.join(project, "out")
    if os.path.isdir(out):
        for f in sorted(os.listdir(out)):
            if f.endswith(".mp4") and not f.endswith("_graded.mp4"):
                return os.path.join(out, f)
    for name in ("build/video_silent.mp4", "build/master.mp4"):
        p = os.path.join(project, name)
        if os.path.exists(p):
            return p
    return None


def preset_for(project, explicit=None):
    """`auto` reads the story's mood instead of guessing.

    A night/warm mood wants the golden grade; everything else the day grade.
    An explicit --preset always wins, so the operator is never overruled.
    """
    if explicit and explicit != "auto":
        return explicit
    try:
        with open(os.path.join(project, "story", "shots.json"), encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        return "day"
    moods = " ".join(str(s.get("bg") or "") for s in st.get("shots") or [])
    return "golden" if any(k in moods for k in ("night", "dusk", "warm", "gold")) else "day"


def grade_video(src, dst, preset, amount=1.0, crf=16, verbose=True):
    w, h, fps = probe(src)
    g = Grader(preset, amount)
    audio = has_audio(src)
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h),
           "-r", "%.6f" % fps, "-i", "-"]
    if audio:
        cmd += ["-i", src]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-r", "%.6f" % fps]
    if audio:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "copy"]
    cmd += ["-movflags", "+faststart", dst]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    before, after, n = [], [], 0
    for f in read_frames(src, w, h):
        if n % 24 == 0:
            before.append(frame_metrics(f))
        out = g.apply(f)
        if n % 24 == 0:
            after.append(frame_metrics(out))
        enc.stdin.write(out.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    if enc.returncode:
        raise SystemExit("GRADE: encoder failed (exit %d)" % enc.returncode)

    def avg(rows, k):
        return sum(r[k] for r in rows) / max(1, len(rows))

    stats = {"frames": n, "preset": preset, "amount": amount,
             "sat": [round(avg(before, "sat"), 4), round(avg(after, "sat"), 4)],
             "lum_std": [round(avg(before, "lum_std"), 4), round(avg(after, "lum_std"), 4)],
             "lcontrast": [round(avg(before, "lcontrast"), 4), round(avg(after, "lcontrast"), 4)],
             "colours": [int(avg(before, "colours")), int(avg(after, "colours"))]}
    if verbose:
        print("GRADE %s amount=%.2f  %d frames  %dx%d" % (preset, amount, n, w, h))
        for k in ("sat", "lum_std", "lcontrast", "colours"):
            b, a = stats[k]
            print("  %-10s %8.3f -> %8.3f  (%+.0f%%)"
                  % (k, b, a, (a / b - 1) * 100 if b else 0))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Colour grade a rendered short.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--preset", default="auto", choices=("auto", "day", "golden"))
    ap.add_argument("--amount", type=float, default=1.0)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--in-place", action="store_true",
                    help="replace the deliverable; the ungraded copy is kept in "
                         "build/ungraded.mp4 so the pass is reversible")
    ap.add_argument("--dry-run", action="store_true",
                    help="measure the input only, write nothing")
    a = ap.parse_args(argv)

    src = pick_video(a.project)
    if not src:
        print("GRADE: no video in", a.project)
        return 2
    preset = preset_for(a.project, a.preset)
    if a.dry_run:
        w, h, fps = probe(src)
        rows = [frame_metrics(f) for i, f in enumerate(read_frames(src, w, h))
                if i % 24 == 0]
        print("GRADE dry-run %s  preset would be %s" % (src, preset))
        for k in ("sat", "lum_std", "lcontrast", "colours"):
            print("  %-10s %8.3f" % (k, sum(r[k] for r in rows) / len(rows)))
        return 0

    dst = os.path.splitext(src)[0] + "_graded.mp4"
    stats = grade_video(src, dst, preset, a.amount, a.crf)
    print("GRADE ->", dst)
    if a.in_place:
        # One deliverable, not two. The ungraded copy is kept so a grade that
        # looks wrong can be undone without a re-render.
        bdir = os.path.join(a.project, "build")
        os.makedirs(bdir, exist_ok=True)
        keep = os.path.join(bdir, "ungraded.mp4")
        os.replace(src, keep)
        os.replace(dst, src)
        print("GRADE: replaced %s (ungraded kept at %s)" % (src, keep))
    with open(os.path.join(a.project, "build", "grade_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
