#!/usr/bin/env python3
"""
render_gate.py -- hard-fail wrapper around render.mjs, plus a static pre-flight.

WHY: render.mjs collects per-shot exceptions into window.ERRORS and PRINTS them
("N shot error(s):") but does NOT set a non-zero exit code for shot errors
(only uncaught exceptions hit `catch` -> "RENDER FAILED:" -> exitCode=1).
For unattended / CI use that is unsafe: a broken render looks successful.

ADDED 2026-11-10:
  1. All patterns are case-insensitive. The engine prints "SHOT ERROR" in
     UPPERCASE while the original patterns were lowercase-only -- a genuine bug.
  2. A static scene-coverage pre-flight runs BEFORE render.mjs, so unregistered
     shots are caught without drawing a single frame.

    CORRECTION 2026-11-10 (independent falsifier): an earlier draft claimed a
    MISSING SHOT slate produces "no stdout signal at all" and that the two slate
    patterns below were the fix. FALSE. render.mjs:55 prints a "WARNING: N shots
    have no scene file yet" line from window.SHOT_LIST (engine/player.js:42),
    which the ORIGINAL gate already matched via `WARNING:.*no scene file`. The
    slates are drawn to canvas, not printed. The MISSING SHOT / ERROR sNNN@
    patterns are therefore retained only as DEFENSIVE matches for future engine
    versions; they are not evidence that the current engine emits them. The
    pre-flight is defence in depth, not the sole protection.

It does NOT modify render.mjs (that file is protected by the merge ledger).

USAGE
    python tools/render_gate.py --project projects/foo
    python tools/render_gate.py --project projects/foo -- --scale 0.5 --workers 4
    python tools/render_gate.py --selftest
Exit: 0 = clean; 1 = coverage failure, render failed OR shot errors printed.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ERROR_PATTERNS = [
    re.compile(r"\bshot error\(s\):", re.I),
    re.compile(r"^\s*shot error:", re.I | re.M),
    re.compile(r"\bSHOT ERROR\b", re.I),
    # Defensive only: the current engine draws these to canvas, not stdout.
    re.compile(r"\bMISSING SHOT\b", re.I),
    re.compile(r"\bERROR s\d+@", re.I),
    re.compile(r"\[pageerror\]", re.I),
    re.compile(r"Player failed to boot", re.I),
    re.compile(r"RENDER FAILED:", re.I),
    re.compile(r"WARNING:.*no scene file", re.I),
]


def scan(text):
    hits = []
    for pat in ERROR_PATTERNS:
        for m in pat.finditer(text or ""):
            hits.append(m.group(0).strip())
    return hits


def coverage(project):
    """Return (errors, warnings, stats); import is local so --selftest stays light."""
    import scene_coverage
    return scene_coverage.check(project)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-coverage", action="store_true",
                    help="EXPLICIT escape hatch for legacy/dynamic projects; "
                         "prints a loud warning and skips the static proof")
    args, extra = ap.parse_known_args()

    if args.selftest:
        sample = ("ok\n2 shot error(s):\n  ReferenceError: x is not defined\n"
                  "  shot error: boom\n[pageerror] nope\nRENDER FAILED: fatal\n"
                  "SHOT ERROR s003@0.12: ReferenceError\nMISSING SHOT s004\n"
                  "ERROR s002@1.20: boom")
        hits = scan(sample)
        print("SELFTEST detected:", hits)
        assert len(hits) >= 6, f"expected >=6 signals, got {hits}"
        assert scan("all good\nDone: out.mp4") == [], "false positive on clean output"
        assert any("SHOT ERROR" in h.upper() for h in hits), "uppercase engine line must be caught"
        assert any("WARNING" in h.upper() or "no scene file" in h
                   for h in scan("WARNING: 2 shots have no scene file yet: s001")), \
            "render.mjs missing-shot warning must be caught"
        print("SELFTEST PASS")
        return 0

    if not args.project:
        sys.exit("ERROR: --project <dir> is required (or use --selftest).")

    if args.no_coverage:
        print("GATE WARNING: static scene-coverage proof DISABLED by --no-coverage; "
              "registration is unverified before render.")
    else:
        errs, warns, stats = coverage(args.project)
        print("GATE PRE-FLIGHT: shots=%s scene_files=%s registered=%s dynamic=%s"
              % (stats.get("shots"), stats.get("scene_files"),
                 stats.get("registered"), stats.get("dynamic_calls")))
        for w in warns:
            print("  INFO " + w)
        if errs:
            for e in errs:
                print("  FAIL " + e)
            print("GATE: scene coverage FAILED -- refusing to render")
            return 1
        print("GATE PRE-FLIGHT: PASS")

    cmd = ["node", "render.mjs", "--project", args.project] + [a for a in extra if a != "--"]
    print("GATE RUN:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")
    out = proc.stdout or ""
    sys.stdout.write(out)
    sys.stdout.flush()

    hits = scan(out)
    if proc.returncode != 0:
        print(f"\nGATE: render.mjs exited {proc.returncode} -> FAIL")
        return 1
    if hits:
        print(f"\nGATE: {len(hits)} error signal(s) printed despite exit 0 "
              f"-> FAIL (silent-failure case)")
        for h in hits[:12]:
            print("   -", h)
        return 1
    print("\nGATE: clean (exit 0, no error signals) -> PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
