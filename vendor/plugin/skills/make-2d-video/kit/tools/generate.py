#!/usr/bin/env python3
"""Story -> validated project -> optional narration/audio -> render -> QC report.

Every required stage's exit code is checked. --strict additionally fails unjudged
seams and motion warnings. Human style/episode approval is never manufactured.
  python tools/generate.py --story examples/template-showcase.json --out projects/demo
  python tools/generate.py --story story.json --out projects/episode --audio --strict
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    print("\n$", " ".join(map(str, cmd)), flush=True)
    return subprocess.run(list(map(str, cmd)), cwd=ROOT).returncode


def fail(stage, code):
    print(f"GENERATE FAILED: {stage} (exit {code})")
    return code or 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--story", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--aspect", choices=["16:9", "9:16"], help="override the story aspect before compilation")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    py, here = sys.executable, ROOT / "tools"
    out = Path(args.out).resolve()
    try:
        story = json.loads(Path(args.story).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return fail("read story", str(exc))
    if args.aspect:
        story["aspect"] = args.aspect
    # Compile from a temporary source so --aspect changes the actual project, not just review.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="generate-") as tmp:
        source = Path(tmp) / "story.json"
        source.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
        code = run([py, here / "director.py", "--story", source, "--out", out])
    if code:
        return fail("director", code)
    venv = Path.home() / ".faceless-shorts/venv/Scripts/python.exe"
    runner = str(venv) if venv.exists() else py
    if args.audio:
        for stage, cmd in [
            ("narration", [runner, here / "narrate.py", "--project", out]),
            ("sound design", [py, here / "sound_design.py", "--project", out]),
        ]:
            code = run(cmd)
            if code:
                return fail(stage, code)
    code = run([py, "-u", here / "render_gate.py", "--project", out])
    if code:
        return fail("render gate", code)
    if args.audio:
        for stage, cmd in [
            ("mix", [runner, ROOT / "audio/mix.py", "--project", out]),
            ("master", [py, here / "master.py", "--project", out]),
        ]:
            code = run(cmd)
            if code:
                return fail(stage, code)
    cfg = json.loads((out / "config.json").read_text(encoding="utf-8"))
    video = out / "build/video_silent.mp4"
    if args.audio:
        candidates = sorted((out / "out").glob("*.mp4")) if (out / "out").exists() else []
        if len(candidates) != 1:
            return fail("delivery selection", f"expected one mixed mp4, found {candidates}")
        video = candidates[0]
    # Style check validates the manifest AND compares current renders, before the report.
    code = run([py, here / "style_lock.py", "check", "--project", out])
    if code == 1:
        return fail("style lock drift/invalid manifest", code)
    if code == 2:
        print("GENERATE: no human-approved style lock; visual acceptance remains pending.")
    elif code:
        return fail("style lock", code)
    code = run([py, here / "review_frames.py", "--project", out, "--video", video, "--aspect", cfg["aspect"]])
    if code:
        return fail("frame review", code)
    code = run([py, here / "seam_gate.py", "--project", out, "--auto", "--json", out / "build/seams.json"]
               + (["--strict"] if args.strict else []))
    if args.strict and code:
        return fail("seam gate", code)
    code = run([py, here / "render_report.py", "--project", out, "--video", video]
               + (["--strict-motion"] if args.strict else []))
    if code:
        return fail("render report / motion QC", code)
    print("\nGENERATE: technical pipeline complete ->", video)
    print("Human review is still required; no approval was inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
