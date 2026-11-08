#!/usr/bin/env python3
"""
generate.py — one command: story.json -> video + QC.

Chains the whole pipeline deterministically:
  1. director.py     story JSON  -> project (config/cast/shots/scene code)
  2. render_gate.py  render.mjs  -> mp4, HARD-FAIL on any shot error
  3. mix.py          (optional, --audio) music+sfx+loudnorm+mux (needs config.voiceover)
  4. review_frames.py visual-review frames + checklist

Any stage failing aborts with a non-zero exit (no silent success).

USAGE
  python tools/generate.py --story examples/director-demo/story.json --out projects/foo
  python tools/generate.py --story story.json --out projects/foo --audio --aspect 9:16
"""
import argparse
import json
import os
import subprocess
import sys


def run(cmd, cwd):
    print("\n$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--aspect", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="fail the run on QC warnings (dead cuts)")
    a = ap.parse_args()

    py = sys.executable
    here = os.path.dirname(os.path.abspath(__file__))
    studio = os.path.dirname(here)
    story = os.path.abspath(a.story)
    out = os.path.abspath(a.out)

    venv = os.path.expanduser("~/.faceless-shorts/venv/Scripts/python.exe")
    runner = venv if os.path.exists(venv) else py

    # 1. director
    if run([py, os.path.join(here, "director.py"), "--story", story, "--out", out], studio):
        sys.exit("GENERATE: director failed")

    # 2. narration FIRST (so words.json exists when we render -> word-synced captions)
    #    narrate also RETIMES every shot to its measured speech (no dead air).
    if a.audio:
        if run([runner, os.path.join(here, "narrate.py"), "--project", out], studio):
            sys.exit("GENERATE: narration (Kokoro) failed")

    # 2b. sound design — fills the foley layer (cuts, walks, risers, ambience).
    #     Runs after narrate because it needs the RETIMED shot lengths.
    if a.audio:
        if run([py, os.path.join(here, "sound_design.py"), "--project", out], studio):
            sys.exit("GENERATE: sound design failed")

    # 3. render through the hard-fail gate
    if run([py, "-u", os.path.join(here, "render_gate.py"), "--project", out], studio):
        sys.exit("GENERATE: render gate failed (shot error / render failure)")

    # 4. audio mix (music + sfx + loudness normalise + mux)
    if a.audio:
        cfg = json.load(open(os.path.join(out, "config.json"), encoding="utf-8"))
        if not cfg.get("voiceover"):
            sys.exit("GENERATE: no voiceover after narration")
        if run([runner, os.path.join(studio, "audio", "mix.py"), "--project", out], studio):
            sys.exit("GENERATE: mix failed")

    # 4. visual review
    cfg = json.load(open(os.path.join(out, "config.json"), encoding="utf-8"))
    aspect = a.aspect or cfg.get("aspect", "9:16")
    run([py, os.path.join(here, "review_frames.py"), "--project", out, "--aspect", aspect], studio)

    # 5. QC gates — seam continuity + a written report. Reported every run; fatal under --strict.
    sg = run([py, os.path.join(here, "seam_gate.py"), "--project", out, "--auto"]
             + (["--strict"] if a.strict else []), studio)
    run([py, os.path.join(here, "render_report.py"), "--project", out], studio)
    if a.strict and sg:
        sys.exit("GENERATE: seam_gate failed — a cut carries no shared subject")

    print("\nGENERATE: DONE ->", out)
    print("  video :", os.path.join(out, "build", "video_silent.mp4"))
    if a.audio and cfg.get("voiceover"):
        print("  final :", os.path.join(out, "out"))
    print("  review:", os.path.join(out, "build", "review"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
