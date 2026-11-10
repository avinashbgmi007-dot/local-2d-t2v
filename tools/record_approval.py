#!/usr/bin/env python3
"""
tools/record_approval.py -- record a HUMAN acceptance into an existing report.

This is the counterpart to tools/approval_gate.py and the ONLY sanctioned way to
set approval state. It updates build/report.json only; it does NOT re-probe,
re-encode or otherwise touch any video file. Use it AFTER the owner has watched
the delivered MP4, with their verbatim words.

  python tools/record_approval.py --project projects/<slug> \
      --words "I watched the whole film. Publish it."

It binds the approval to the delivered bytes by copying the report's
video_sha256 into approved_video_sha256. If the film is re-rendered,
render_report.py resets approval to pending and approval_gate.py refuses it.

IMPORTANT: running this tool is an act of approval. An agent must never call it
on the owner's behalf or invent the words. An approved style-lock manifest must
already exist (approval_gate.py checks it separately).
"""
import argparse
import datetime
import json
import os
import sys


def record(project, words, reviewer=None, report=None):
    """Write approval fields into build/report.json. Returns the path."""
    if not isinstance(words, str) or not words.strip():
        raise ValueError("approval words must be non-empty and verbatim")
    path = report or os.path.join(project, "build", "report.json")
    if not os.path.exists(path):
        raise FileNotFoundError("no render report yet: " + path)
    with open(path, encoding="utf-8") as fh:
        rep = json.load(fh)
    vhash = rep.get("video_sha256")
    if not vhash:
        raise ValueError("report has no video_sha256; measure the delivered file first")
    rep["approved_by"] = words.strip()
    rep["approved_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    rep["approval_state"] = "approved"
    rep["approved_video_sha256"] = vhash
    if reviewer:
        rep["approved_reviewer"] = reviewer
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--words", required=True, help="the owner's exact acceptance words")
    ap.add_argument("--reviewer", default="")
    a = ap.parse_args()
    try:
        path = record(a.project, a.words, a.reviewer)
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as e:
        sys.exit("RECORD APPROVAL: refused -- " + str(e))
    print("RECORD APPROVAL: wrote", path)
    print("  approved_by:", a.words.strip())
    print("  NOTE: this records acceptance, NOT a re-check of the MP4. Run")
    print("        tools/approval_gate.py --verify-bytes at publish time (owner).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
