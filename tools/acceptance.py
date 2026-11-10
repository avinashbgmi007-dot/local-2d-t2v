#!/usr/bin/env python3
"""acceptance.py -- unified READ-SIDE acceptance gate.

Consolidates the read/check side of acceptance:
  * check     -> runs approval_gate.evaluate + style_lock check (read-only)
  * snapshot  -> delegates to style_lock cmd_snapshot (writes style-lock.json,
                 the visual reference baseline; NOT an approval)

The WRITE side (recording human approval bound to video bytes) is intentionally
NOT here. It stays in tools/record_approval.py, which is the SOLE writer of
report.json.approved_by / approval_state / approved_at /
approved_video_sha256. generate.py must not import this module as an approval
shortcut, and this module exposes no 'record' command. See
docs/adr/0001-protected-paths-and-approval-invariant.md.

USAGE
    python tools/acceptance.py check --project projects/my_episode
    python tools/acceptance.py snapshot --project projects/my_episode
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run_tool(tool, extra):
    cmd = [PY, os.path.join(HERE, tool)] + extra
    r = subprocess.run(cmd)
    return r.returncode


def cmd_check(args):
    # Read-only: approval gate + style lock check. Both must pass.
    rc1 = run_tool("approval_gate.py", ["--project", args.project])
    rc2 = run_tool("style_lock.py", ["check", "--project", args.project])
    if rc1 != 0 or rc2 != 0:
        print("ACCEPTANCE: FAIL (approval_gate=%d, style_lock=%d)" % (rc1, rc2))
        return 1
    print("ACCEPTANCE: PASS (approval + style lock)")
    return 0


def cmd_snapshot(args):
    # Delegates to style_lock snapshot (writes the visual reference manifest).
    return run_tool("style_lock.py", ["snapshot", "--project", args.project])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="read-only acceptance check")
    c.add_argument("--project", required=True)
    c.set_defaults(func=cmd_check)
    s = sub.add_parser("snapshot", help="snapshot style-lock reference (style_lock owns the write)")
    s.add_argument("--project", required=True)
    s.set_defaults(func=cmd_snapshot)
    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
