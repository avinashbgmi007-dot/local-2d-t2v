#!/usr/bin/env python3
"""
render_gate.py — hard-fail wrapper around render.mjs.

WHY: render.mjs collects per-shot exceptions into window.ERRORS and PRINTS them
("N shot error(s):") but does NOT set a non-zero exit code for shot errors
(only uncaught exceptions hit `catch` -> "RENDER FAILED:" -> exitCode=1).
For unattended / CI / "any AI, input->output" use that is unsafe: a broken
render would look successful. This wrapper runs render.mjs, scrapes its output
for every error signal, and exits 1 if ANY is found.

It does NOT modify render.mjs (that file is protected by the merge ledger).

USAGE
    python tools/render_gate.py --project projects/foo
    python tools/render_gate.py --project projects/foo -- --scale 0.5 --workers 4
    python tools/render_gate.py --selftest          # verify detection logic
Exit: 0 = clean; 1 = render failed OR shot errors printed.
"""
import argparse
import re
import subprocess
import sys

ERROR_PATTERNS = [
    re.compile(r"\bshot error\(s\):"),
    re.compile(r"^\s*shot error:", re.M),
    re.compile(r"\[pageerror\]"),
    re.compile(r"Player failed to boot"),
    re.compile(r"RENDER FAILED:"),
    re.compile(r"WARNING:.*no scene file"),
]


def scan(text):
    hits = []
    for pat in ERROR_PATTERNS:
        for m in pat.finditer(text or ""):
            hits.append(m.group(0).strip())
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--selftest", action="store_true")
    args, extra = ap.parse_known_args()

    if args.selftest:
        sample = ("ok\n2 shot error(s):\n  ReferenceError: x is not defined\n"
                  "  shot error: boom\n[pageerror] nope\nRENDER FAILED: fatal")
        hits = scan(sample)
        print("SELFTEST detected:", hits)
        assert len(hits) >= 4, f"expected >=4 signals, got {hits}"
        assert scan("all good\nDone: out.mp4") == [], "false positive on clean output"
        print("SELFTEST PASS")
        return 0

    if not args.project:
        sys.exit("ERROR: --project <dir> is required (or use --selftest).")

    cmd = ["node", "render.mjs", "--project", args.project] + [a for a in extra if a != "--"]
    print("GATE RUN:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = proc.stdout or ""
    sys.stdout.write(out)
    sys.stdout.flush()

    hits = scan(out)
    if proc.returncode != 0:
        print(f"\nGATE: render.mjs exited {proc.returncode} -> FAIL")
        sys.exit(1)
    if hits:
        print(f"\nGATE: {len(hits)} error signal(s) printed despite exit 0 "
              f"-> FAIL (silent-failure case)")
        for h in hits[:12]:
            print("   -", h)
        sys.exit(1)
    print("\nGATE: clean (exit 0, no error signals) -> PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
