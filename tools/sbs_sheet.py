#!/usr/bin/env python3
"""sbs_sheet.py -- side-by-side reference comparison sheet.

Stitches two frames (ours vs reference) horizontally with a thin divider so a
human reviewer (or vision model) can compare them at a glance. Uses ffmpeg only.

USAGE
    # single pair
    python tools/sbs_sheet.py --ours a.png --ref b.png --out sbs.png
    # batch: every PNG in --ours-dir matched by basename to --ref-dir
    python tools/sbs_sheet.py --ours-dir out/ours --ref-dir out/ref --out-dir out/sbs

Exit: 0 on success, 1 on any ffmpeg failure or missing input.
"""
import argparse
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def stitch(ours, ref, out):
    if not os.path.exists(ours):
        return f"missing ours: {ours}"
    if not os.path.exists(ref):
        return f"missing ref: {ref}"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    # hstack with a 4px black divider between the two frames.
    r = run(["ffmpeg", "-y", "-i", ours, "-i", ref,
             "-filter_complex",
             "[0:v][1:v]hstack=inputs=2,format=yuv420p[v]",
             "-map", "[v]", out])
    if r.returncode != 0:
        return r.stderr.decode(errors="ignore")[-300:]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours")
    ap.add_argument("--ref")
    ap.add_argument("--out")
    ap.add_argument("--ours-dir")
    ap.add_argument("--ref-dir")
    ap.add_argument("--out-dir")
    args = ap.parse_args()

    if args.ours and args.ref and args.out:
        err = stitch(args.ours, args.ref, args.out)
        if err:
            print("SBS FAIL:", err, file=sys.stderr)
            return 1
        print("SBS OK:", args.out)
        return 0

    if args.ours_dir and args.ref_dir and args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        names = sorted(f for f in os.listdir(args.ours_dir)
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))
        n = 0
        for name in names:
            err = stitch(os.path.join(args.ours_dir, name),
                         os.path.join(args.ref_dir, name),
                         os.path.join(args.out_dir, name))
            if err:
                print("SBS FAIL", name, ":", err, file=sys.stderr)
                return 1
            n += 1
        print(f"SBS OK: {n} sheet(s) -> {args.out_dir}")
        return 0

    print("ERROR: provide --ours/--ref/--out OR --ours-dir/--ref-dir/--out-dir",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
