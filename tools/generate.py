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

CHANGED 2026-11-12 (story-contract wiring, Phase A):
  * fresh/story_schema.validate_story ran only inside fresh/story.py, so a
    hand-authored --story film with an out-of-vocabulary expression rendered a
    NEUTRAL face while every QC gate stayed green. Stage 0 now validates the
    story file director.py is about to read, on BOTH --story and --fresh.
  * Errors are printed on every run and are fatal under --strict. Default runs
    still render, so existing hand-authored stories are not broken. Making the
    gate unconditionally fatal is a deliberate policy change, not a bug fix.
  * Output pixels are unchanged. No approved project was modified.

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


def frame_qa_cmd(here, out, strict):
    """Build the frame_qa command. Pure, so wiring is testable without a video."""
    cmd = [sys.executable, os.path.join(here, "frame_qa.py"), "--project", out]
    if strict:
        cmd.append("--strict")
    return cmd


def report_stage_failure(label, detail, strict):
    """Report a degraded additive stage; abort only under --strict."""
    msg = "GENERATE: %s: %s" % (label, detail)
    if strict:
        sys.exit(msg + " (fatal under --strict)")
    print(msg + " (non-fatal; use --strict to make fatal)")


def fresh_story_path(studio, out):
    """Scope the --fresh story file to the project, so runs cannot overwrite it."""
    slug = os.path.basename(os.path.normpath(out)) or "fresh"
    return os.path.join(studio, "tmp", "fresh_story_%s.json" % slug)


def validate_story_file(path, here):
    """Run the story-JSON contract on the file director.py is about to read.

    Import-safe and side-effect free, so the gate can be unit-tested without
    starting a render. Raises if the file is unreadable or is not valid JSON.
    """
    if here not in sys.path:
        sys.path.insert(0, here)
    from fresh.story_schema import validate_story
    with open(path, encoding="utf-8") as fh:
        return validate_story(json.load(fh))


def story_contract_decision(errs, strict):
    """Return an abort message, or None to continue the run."""
    if errs and strict:
        return ("GENERATE: story contract has %d error(s); fix the story JSON or "
                "re-run without --strict to render anyway" % len(errs))
    return None


def check_story_contract(story, here, strict):
    """Stage 0. Print every contract finding; abort a --strict run on errors.

    Deliberately fail-closed on infrastructure faults (unreadable story, broken
    contract module): a generation run must not proceed when its own validation
    layer cannot run. Returns (errors, warnings) on a completed check.
    """
    try:
        errs, warns = validate_story_file(story, here)
    except Exception as exc:
        sys.exit("GENERATE: story contract could not run on %s: %s" % (story, exc))
    for msg in errs:
        print("  STORY ERROR :", msg)
    for msg in warns:
        print("  story note  :", msg)
    abort = story_contract_decision(errs, strict)
    if abort:
        sys.exit(abort)
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=False, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--aspect", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="fail on QC warnings (dead cuts), story-contract errors, "
                         "and on a missing style lock")
    ap.add_argument("--require-approval", action="store_true",
                    help="also run approval_gate.py at the end; exit 1 if no human accepted")
    ap.add_argument("--fresh", default=None,
                    help="concept string: generate a distinct story JSON via fresh pipeline")
    ap.add_argument("--series", default=None, help="series id for fresh generation (keeps cast consistent across episodes)")
    ap.add_argument("--episode", type=int, default=None, help="episode number for fresh generation")
    ap.add_argument("--preview", action="store_true",
                    help="also render a 20s preview clip (build/preview.mp4) for quick review")
    ap.add_argument("--frame-qa", action="store_true",
                    help="opt-in: run frame_qa.py freeze/pop detection (fatal only with --strict)")
    ap.add_argument("--workers", type=int, default=0,
                    help="cap render.mjs Chromium workers (0 = renderer default)")
    a = ap.parse_args()

    py = sys.executable
    here = os.path.dirname(os.path.abspath(__file__))
    studio = os.path.dirname(here)
    out = os.path.abspath(a.out)
    if a.fresh is None and a.story is None:
        sys.exit("GENERATE: provide --story or --fresh")
    if a.fresh:
        # Generate a distinct story JSON via the fresh pipeline before director.
        sys.path.insert(0, here)
        from fresh.story import write_story
        os.makedirs(os.path.join(studio, "tmp"), exist_ok=True)
        story_path = fresh_story_path(studio, out)
        write_story(a.fresh, story_path, series_id=a.series, episode=a.episode)
        print("GENERATE: fresh story ->", story_path)
        story = os.path.abspath(story_path)
    else:
        if a.story is None:
            sys.exit("GENERATE: --story required when --fresh not given")
        story = os.path.abspath(a.story)

    # 0. story contract -- BOTH entry paths. fresh.story validates in memory,
    #    but this re-checks the actual file director.py will read and, crucially,
    #    covers the hand-authored --story path that previously rendered NEUTRAL
    #    faces with no gate noticing. Errors are fatal under --strict; otherwise
    #    they are printed so a green QC run can no longer hide them.
    check_story_contract(story, here, a.strict)

    venv = os.path.expanduser("~/.faceless-shorts/venv/Scripts/python.exe")
    runner = venv if os.path.exists(venv) else py

    # 0c. set spec BEFORE director. director.py injects this palette into the
    #     emitted scenes/sets/*.js, so writing it after the director stage (as
    #     this did until 2026-11-12) made the reader see nothing and every film
    #     kept the five style-mood colours instead of its concept's.
    if a.fresh:
        try:
            sys.path.insert(0, here)
            from fresh.sets import write_set_spec
            ss_path = os.path.join(out, "set_spec.json")
            write_set_spec(a.fresh, ss_path, series_id=a.series, episode=a.episode)
            print("GENERATE: set spec ->", ss_path)
        except Exception as e:
            report_stage_failure("set spec", e, a.strict)

    # 1. director
    if run([py, os.path.join(here, "director.py"), "--story", story, "--out", out], studio):
        sys.exit("GENERATE: director failed")

    # 1a. template interpreter (fresh only, additive) — resolves any `template` fields in shots
    if a.fresh:
        ti = run([py, os.path.join(here, "template_interpreter.py"), "--project", out, "--check"], studio)
        if ti:
            report_stage_failure("template interpreter", "returned %d" % ti, a.strict)

    # 1b. series bible (fresh only, additive) — cast/voice/sfx identity for the series
    if a.fresh:
        try:
            sys.path.insert(0, here)
            from fresh.series import write_series
            sid = a.series if a.series else (a.fresh.strip().lower().replace(" ", "_")[:20] or "fresh")
            sb_path = os.path.join(out, "series.json")
            write_series(sid, sb_path, concept=a.fresh, title=None)
            print("GENERATE: series bible ->", sb_path)
        except Exception as e:
            report_stage_failure("series bible", e, a.strict)

    # 2. narration FIRST (so words.json exists when we render -> word-synced captions)
    if a.audio:
        if run([runner, os.path.join(here, "narrate.py"), "--project", out], studio):
            sys.exit("GENERATE: narration (Kokoro) failed")

    # 2b. sound design -- needs the RETIMED shot lengths from narrate.
    if a.audio:
        if run([py, os.path.join(here, "sound_design.py"), "--project", out], studio):
            sys.exit("GENERATE: sound design failed")

    # 3. render through the hard-fail gate (includes static scene coverage)
    rg = [py, "-u", os.path.join(here, "render_gate.py"), "--project", out]
    if a.workers:
        rg += ["--", "--workers", str(a.workers)]
    if run(rg, studio):
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

    # 6a. opt-in freeze/pop detection. frame_qa.py returns 1 only with --strict,
    #     so this is report-only by default and cannot break an existing run.
    if a.frame_qa:
        if run(frame_qa_cmd(here, out, a.strict), studio):
            sys.exit("GENERATE: frame_qa found unexplained frame defects")

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

    # Optional 20s preview clip for quick review (additive, does not affect main output).
    if a.preview:
        rc = run(["node", os.path.join(studio, "render.mjs"), "--project", out,
                  "--from", "0", "--to", "20", "--scale", "0.5"], studio)
        if rc:
            report_stage_failure("preview render", "exit %d" % rc, a.strict)
        else:
            print("GENERATE: preview ->", os.path.join(out, "build", "preview.mp4"))

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
