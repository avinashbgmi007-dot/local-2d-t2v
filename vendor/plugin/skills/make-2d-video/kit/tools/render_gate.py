#!/usr/bin/env python3
"""Validate a project, stream a render, and fail on any error signal.

render.mjs now also hard-fails natively; this wrapper remains defense in depth and
keeps long renders observable instead of buffering all progress until completion.
  python tools/render_gate.py --project P -- --scale .5
  python tools/render_gate.py --selftest
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    from .validate_project import validate_project
except ImportError:
    from validate_project import validate_project

ROOT = Path(__file__).resolve().parents[1]
ERROR_PATTERNS = [re.compile(p, re.I | re.M) for p in [
    r"\bshot error(?:\(s\))?:", r"\[pageerror\]", r"\[page\].*(?:ERROR|missing)",
    r"Player failed to boot", r"RENDER FAILED:", r"IMPORT ERROR", r"WARNING:.*no scene file"]]


def scan(text):
    return [m.group(0).strip() for pat in ERROR_PATTERNS for m in pat.finditer(text or "")]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project")
    ap.add_argument("--selftest", action="store_true")
    args, extra = ap.parse_known_args()
    if args.selftest:
        sample = "2 shot error(s):\n shot error: boom\n[pageerror] nope\nRENDER FAILED: fatal\nIMPORT ERROR x\n[page] font missing"
        hits = scan(sample)
        assert len(hits) >= 6, hits
        assert not scan("all good\nDone: out.mp4")
        print("SELFTEST PASS:", hits); return 0
    if not args.project:
        ap.error("--project required (or --selftest)")
    errors, warnings = validate_project(args.project)
    for warning in warnings:
        print("WARN", warning)
    if errors:
        print("GATE INVALID:\n  " + "\n  ".join(errors)); return 2
    cmd = ["node", str(ROOT / "render.mjs"), "--project", args.project] + [a for a in extra if a != "--"]
    print("GATE RUN:", " ".join(cmd), flush=True)
    hits = []
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            sys.stdout.write(line); sys.stdout.flush()
            hits.extend(scan(line))
        code = proc.wait()
    except OSError as exc:
        print("GATE FAILED:", exc); return 1
    if code or hits:
        print(f"GATE FAIL (exit {code}, {len(hits)} error signals)"); return 1
    print("GATE PASS (exit 0, no error signals)"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
