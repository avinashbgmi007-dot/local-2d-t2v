#!/usr/bin/env python3
"""
tools/approval_gate.py -- make human acceptance a MACHINE-CHECKABLE STATE, not merely prose.

WHY THIS EXISTS
    Every shipped report says human_review="required; technical checks are not
    acceptance", but approved_by was null on every finished video: the rule was
    prose, not a gate. Any publish/scheduling step MUST call this tool and treat
    a non-zero exit as a hard block.

ENFORCEMENT BOUNDARY (stated plainly)
    This tool enforces WHEN IT IS CALLED. No publish/scheduling code exists in
    this repo, and generate.py invokes it only under --require-approval. Claiming
    "approval is enforced" without naming the caller is inaccurate: the state is
    verifiable, but end-to-end enforcement still needs a publish-time caller.
    It checks JSON fields, not signatures or identities; direct edits to
    report.json / style-lock.json remain possible. This is a gate, not a notary.

CORRECTION 2026-11-10 (independent falsifier)
    The first version checked only field presence, so a generation run could
    forge approval with `render_report.py --approved-by`, and an empty
    style-lock.json passed. It also did not bind the approval to the bytes that
    were approved. All three are now closed:
      * approval_state must be "approved" AND approved_at must be present;
      * approved_video_sha256 must equal the report's current video_sha256, so
        re-rendering invalidates the approval;
      * the on-disk lock manifest must be valid, approved and carry references;
      * --approved-by has been REMOVED from generate.py and is REFUSED by
        render_report.py. Only tools/record_approval.py can set approval.

DELIBERATE LIMIT / OWNER-RUN OPTION
    By default this reads JSON only; it never opens a video. --verify-bytes is
    an OPTIONAL owner-run publish-time check that re-hashes the delivered MP4
    and compares it to the report. It is NOT executed by any agent in the
    pipeline and was NOT executed when these tools were built.

USAGE
    python tools/approval_gate.py --project projects/<slug>
    python tools/approval_gate.py --project projects/<slug> --verify-bytes  # owner only
    python tools/approval_gate.py --selftest

Exit: 0 = approved; 1 = NOT APPROVED (block publish); 2 = bad arguments.
"""
import argparse
import hashlib
import json
import os
import sys

# Project value object (single source of truth for paths)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from project import Project

HUMAN_RULE = "technical checks are not acceptance"


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def evaluate(project, report=None, lock=None, verify_bytes=False):
    """Return (approved: bool, issues: list[str], state: dict).

    No video I/O unless verify_bytes=True, which is reserved for an owner-run
    publish-time check.
    """
    P = project if isinstance(project, Project) else Project(project)
    report = report or os.path.join(P.build, "report.json")
    lock = lock or os.path.join(P.story, "style-lock.json")
    issues, state = [], {}

    if not os.path.exists(report):
        return False, [f"no render report at {report}"], state
    try:
        rep = _load(report)
    except (ValueError, OSError) as e:
        return False, [f"could not read render report: {e}"], state

    approved_by = rep.get("approved_by")
    vhash = rep.get("video_sha256")
    state = {
        "project": os.path.basename(os.path.normpath(P.root)),
        "video": rep.get("video"),
        "approved_by": approved_by,
        "approval_state": rep.get("approval_state"),
        "approved_at": rep.get("approved_at"),
        "video_sha256": vhash,
        "approved_video_sha256": rep.get("approved_video_sha256"),
    }

    if not isinstance(approved_by, str) or not approved_by.strip():
        issues.append("approved_by is empty -- no human has recorded acceptance")
    if str(rep.get("approval_state", "")).lower() != "approved":
        issues.append("approval_state is not 'approved' -- use tools/record_approval.py")
    if not rep.get("approved_at"):
        issues.append("approved_at absent -- approval was not recorded by the tool")
    if HUMAN_RULE not in str(rep.get("human_review", "")).lower():
        issues.append("report is missing the standing human_review rule")
    if not vhash:
        issues.append("video_sha256 absent -- the delivered file was never measured")
    if rep.get("approved_video_sha256") != vhash:
        issues.append("approved_video_sha256 != video_sha256 -- the approved bytes "
                      "are not the current deliverable (re-render invalidates approval)")

    lock_state = rep.get("style_lock")
    if not isinstance(lock_state, dict):
        issues.append("style_lock is null -- no approved visual reference")
    else:
        if str(lock_state.get("status", "")).lower() != "approved":
            issues.append("style_lock status is not 'approved'")
        if not lock_state.get("approved_by"):
            issues.append("style_lock has no approver")

    # A stale report alone is not proof: the manifest must be real and complete.
    if not os.path.exists(lock):
        issues.append(f"no style-lock manifest at {lock}")
    else:
        try:
            m = _load(lock)
            if not isinstance(m, dict) or str(m.get("status", "")).lower() != "approved":
                issues.append("style-lock manifest is empty or not approved")
            if not m.get("approved_by"):
                issues.append("style-lock manifest has no approver")
            if not m.get("references"):
                issues.append("style-lock manifest has no fingerprinted references")
        except (ValueError, OSError) as e:
            issues.append(f"style-lock manifest unreadable: {e}")

    if verify_bytes and vhash:
        rel = rep.get("video") or ""
        path = rel if os.path.isabs(rel) else os.path.join(P.root, rel)
        if not os.path.exists(path):
            issues.append(f"delivered video missing at {path}")
        else:
            actual = sha256(path)
            state["verified_bytes_sha256"] = actual
            if actual != vhash:
                issues.append("delivered MP4 bytes no longer match video_sha256")

    return (not issues), issues, state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify-bytes", action="store_true",
                    help="OWNER-RUN publish-time check: re-hash the delivered MP4")
    a = ap.parse_args()

    if a.selftest:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "build"))
            os.makedirs(os.path.join(d, "story"))
            rpath = os.path.join(d, "build", "report.json")
            lpath = os.path.join(d, "story", "style-lock.json")
            base = {"video": "out/film.mp4", "video_sha256": "deadbeef",
                    "human_review": "required; technical checks are not acceptance",
                    "approved_by": None, "style_lock": None,
                    "approval_state": "pending"}
            json.dump(base, open(rpath, "w", encoding="utf-8"))
            assert not evaluate(d)[0], "null approval must fail"

            # A hand-written approved_by + approved dict, without the record tool,
            # must NOT pass (the forge path the falsifier found).
            base.update({"approved_by": "publish it", "approval_state": "approved",
                         "style_lock": {"status": "approved", "approved_by": "yes"}})
            json.dump(base, open(rpath, "w", encoding="utf-8"))
            json.dump({"status": "approved", "approved_by": "yes", "references": [1]},
                      open(lpath, "w", encoding="utf-8"))
            assert not evaluate(d)[0], "forged approval must fail"

            # Byte binding: approval for old bytes must not approve new bytes.
            base.update({"approved_at": "2026-11-10T10:00:00",
                         "approved_video_sha256": "OLD"})
            json.dump(base, open(rpath, "w", encoding="utf-8"))
            assert not evaluate(d)[0], "stale byte binding must fail"

            base["approved_video_sha256"] = "deadbeef"
            json.dump(base, open(rpath, "w", encoding="utf-8"))
            ok, issues, _ = evaluate(d)
            assert ok, "complete recorded approval must pass: %s" % issues

            # An empty manifest must not pass.
            json.dump({}, open(lpath, "w", encoding="utf-8"))
            assert not evaluate(d)[0], "empty lock manifest must fail"
            json.dump({"status": "approved", "approved_by": "yes", "references": [1]},
                      open(lpath, "w", encoding="utf-8"))

            base["human_review"] = "machine checks passed"
            json.dump(base, open(rpath, "w", encoding="utf-8"))
            assert not evaluate(d)[0], "removing the standing rule must fail"
        print("SELFTEST PASS -- null / forged / stale-bytes / complete / "
              "empty-manifest / rule-removed")
        return 0

    if not a.project:
        sys.exit("ERROR: --project <dir> is required (or --selftest).")
    ok, issues, state = evaluate(a.project, verify_bytes=a.verify_bytes)
    if a.json:
        print(json.dumps({"approved": ok, "issues": issues, "state": state}, indent=1))
    else:
        print("APPROVAL GATE:", a.project)
        for k in ("video", "approved_by", "approval_state", "video_sha256"):
            print("  %-22s %s" % (k + ":", state.get(k)))
        for i in issues:
            print("  FAIL  " + i)
    if not ok:
        print("APPROVAL GATE: NOT APPROVED -- publish/scheduling must be blocked")
        print("  After watching the film, record the owner's exact words:")
        print('    python tools/record_approval.py --project %s --words "<exact words>"' % a.project)
        return 1
    print("APPROVAL GATE: APPROVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
