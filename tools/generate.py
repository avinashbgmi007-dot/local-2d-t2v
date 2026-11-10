#!/usr/bin/env python3
"""
generate.py -- one command: story.json -> video CANDIDATE + QC.

Chains the whole pipeline deterministically:
  1. director.py      story JSON -> project (config/cast/shots/scene code)
  2. narrate.py       (--audio) Kokoro TTS + speech-based shot retiming
  3. sound_design.py  (--audio) foley cues
  4. render_gate.py   scene-coverage pre-flight + render.mjs, HARD-FAIL on errors
  5. mix.py / master.py (--audio) music+sfx + two-pass LUFS mastering
  6. review_frames.py frames + checklist on the DELIVERED mp4 (fatal on defects)
  7. seam_gate.py, render_report.py, style_lock.py verify (QC records)
  8. approval_gate.py (only with --require-approval)

CHANGED 2026-11-10 (read-only audit findings):
  * Stages 6 and 7 used to have their return codes DISCARDED; all are fatal now.
  * A missing style lock is fatal under --strict instead of a printed note.
  * The final line no longer says "DONE" as if the film were accepted.

CORRECTION 2026-11-10 (loop 2, independent falsifier):
  * The first version still swallowed seam_gate's non-zero exit unless --strict.
    seam_gate.py exits unconditionally on a missing scenes/shots dir, so a
    broken project printed CANDIDATE READY and returned 0. Any non-zero is now
    fatal, irrespective of --strict.
  * The first version added an approved-by pass-through to render_report.py.
    That let a GENERATION RUN forge a passing approval. It has been REMOVED.
    Approval can only be set by the owner via tools/record_approval.py, and is
    bound to the delivered video bytes by tools/approval_gate.py.
  * style_lock.py verify used to have only exit codes 1 and 2 handled; any other
    non-zero was silently discarded. Every non-zero except 2 (missing) is fatal.

BOUNDARY (stated plainly): there is deliberately NO publish/scheduling code in
this repo. Any future publish step MUST call tools/approval_gate.py and treat
exit 1 as a block. By default nothing calls it, so approval is machine-CHECKABLE,
not enforced end-to-end. This script cannot approve its own output.

A failing stage aborts with a non-zero exit (no silent success).

USAGE
  python tools/generate.py --story examples/director-demo/story.json --out projects/foo
  python tools/generate.py --story story.json --out projects/foo --audio --aspect 9:16 --strict
"""
import argparse
import json
import os
import subprocess
import sys


def run(cmd, cwd):
    print("\n$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd).returncode


def load_cfg(out):
    with open(os.path.join(out, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--aspect", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="fail on QC warnings (dead cuts) and on a missing style lock")
    ap.add_argument("--require-approval", action="store_true",
                    help="also run approval_gate.py at the end; exit 1 if no human accepted")
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
    if a.audio:
        if run([runner, os.path.join(here, "narrate.py"), "--project", out], studio):
            sys.exit("GENERATE: narration (Kokoro) failed")

    # 2b. sound design -- needs the RETIMED shot lengths from narrate.
    if a.audio:
        if run([py, os.path.join(here, "sound_design.py"), "--project", out], studio):
            sys.exit("GENERATE: sound design failed")

    # 3. render through the hard-fail gate (includes static scene coverage)
    if run([py, "-u", os.path.join(here, "render_gate.py"), "--project", out], studio):
        sys.exit("GENERATE: render gate failed (coverage / shot error / render failure)")

    # 4. audio mix + mastering
    if a.audio:
        cfg = load_cfg(out)
        if not cfg.get("voiceover"):
            sys.exit("GENERATE: no voiceover after narration")
        if run([runner, os.path.join(studio, "audio", "mix.py"), "--project", out], studio):
            sys.exit("GENERATE: mix failed")
        if run([py, os.path.join(here, "master.py"), "--project", out], studio):
            sys.exit("GENERATE: mastering failed (loudness target not reached)")

    # 5. visual review -- fatal on measurable defects (previously ignored).
    cfg = load_cfg(out)
    aspect = a.aspect or cfg.get("aspect", "9:16")
    if run([py, os.path.join(here, "review_frames.py"), "--project", out,
            "--aspect", aspect], studio):
        sys.exit("GENERATE: visual review gate failed "
                 "(black/white frame, aspect mismatch, or ambiguous deliverable)")

    # 6. QC gates. EVERY non-zero exit is fatal, including seam_gate hard errors.
    sg = run([py, os.path.join(here, "seam_gate.py"), "--project", out, "--auto"]
             + (["--strict"] if a.strict else []), studio)
    if sg:
        sys.exit("GENERATE: seam_gate failed (exit %d) -- a cut carries no shared "
                 "subject, or the project is malformed" % sg)
    if run([py, os.path.join(here, "render_report.py"), "--project", out], studio):
        sys.exit("GENERATE: render report failed")

    # 6b. style lock. Any unexpected non-zero is fatal; 2 (missing) is a warning
    #     that becomes fatal under --strict. INVALID (1) and crashes also fatal.
    sl = run([py, os.path.join(here, "style_lock.py"), "verify", "--project", out], studio)
    if sl not in (0, 2):
        sys.exit("GENERATE: style lock INVALID or verify crashed (exit %d) -- "
                 "the approved look may have drifted" % sl)
    if sl == 2:
        msg = ("GENERATE: no style lock for this project, so style drift cannot be "
               "detected. After accepting frames, create one:\n"
               "  python tools/style_lock.py snapshot --project %s --frames 1.0,4.2 "
               '--character inkbean (pass the approver flag; see style_lock.py --help)' % out)
        if a.strict:
            sys.exit(msg)
        print(msg)

    # 7. Optional publish blocker. A generation run cannot approve its own output.
    if a.require_approval:
        if run([py, os.path.join(here, "approval_gate.py"), "--project", out], studio):
            sys.exit("GENERATE: NOT APPROVED -- a human must watch and record acceptance")

    print("\nGENERATE: CANDIDATE READY ->", out)
    print("  STATUS  : NOT APPROVED. Technical checks are not acceptance.")
    print("  video   :", os.path.join(out, "build", "video_silent.mp4"))
    if a.audio and cfg.get("voiceover"):
        print("  final   :", os.path.join(out, "out"))
    print("  review  :", os.path.join(out, "build", "review"))
    print("  next    : human watches the film, then "
          'python tools/record_approval.py --project %s --words "<exact words>"' % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
