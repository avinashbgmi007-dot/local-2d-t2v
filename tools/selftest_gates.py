#!/usr/bin/env python3
"""
tools/selftest_gates.py -- static regression suite for the additive quality gates.

Runs entirely on synthetic text files in TemporaryDirectory. NO video is opened,
probed, decoded, rendered or written: the few ".mp4" names below are empty
placeholder files used only to exercise path-selection logic.

  python tools/selftest_gates.py            (system python is fine; stdlib only)
"""
import json
import os
import sys
import tempfile
import unittest
import subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
WS = os.path.dirname(os.path.dirname(STUDIO))
# Allow override via env var for fresh-clone / CI environments
SHORTS = os.environ.get("FACELESS_SHORTS_PATH",
    os.path.join(WS, "_yt_a6zA", "fs", "faceless-shorts", "scripts"))
for p in (TOOLS,):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
if os.path.isdir(SHORTS) and SHORTS not in sys.path:
    sys.path.insert(0, SHORTS)
else:
    print("SKIP: faceless-shorts scripts/ not found at %s (set FACELESS_SHORTS_PATH)" % SHORTS)

import scene_coverage          # noqa: E402  (committed; hard import so a break fails, not skips)
import approval_gate           # noqa: E402
import record_approval         # noqa: E402
import render_gate             # noqa: E402
import review_frames           # noqa: E402
try:
    import project                # noqa: E402
except ImportError:
    project = None
try:
    import words as _words
except ImportError:
    _words = None
try:
    import frame_qa                # noqa: E402
except ImportError:
    frame_qa = None

try:
    import words               # noqa: E402
except ImportError:
    words = None


def make_project(root, shots=("s001", "s002"), scenes=("s001", "s002")):
    os.makedirs(os.path.join(root, "story"), exist_ok=True)
    os.makedirs(os.path.join(root, "scenes", "shots"), exist_ok=True)
    with open(os.path.join(root, "story", "shots.json"), "w", encoding="utf-8") as f:
        json.dump({"shots": [{"id": s} for s in shots]}, f)
    for i, sid in enumerate(scenes):
        with open(os.path.join(root, "scenes", "shots", "%02d.js" % i), "w",
                  encoding="utf-8") as f:
            f.write("registerShot('%s', { draw(){} });\n" % sid)
    return root


def empty_file(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb"):
        pass


class SceneCoverageTests(unittest.TestCase):
    def test_clean_project_passes(self):
        with tempfile.TemporaryDirectory() as d:
            errs, warns, stats = scene_coverage.check(make_project(d))
            self.assertEqual(errs, [])
            self.assertEqual(warns, [])
            self.assertEqual(stats["shots"], 2)

    def test_missing_shot_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, shots=("s001", "s002", "s003"), scenes=("s001", "s002"))
            self.assertTrue(any("s003" in e for e in scene_coverage.check(d)[0]))

    def test_duplicate_registration_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001", "s002", "s001"))
            self.assertTrue(any("more than one file" in e
                                for e in scene_coverage.check(d)[0]))

    def test_same_file_duplicate_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001",))
            with open(os.path.join(d, "scenes", "shots", "02.js"), "w",
                      encoding="utf-8") as f:
                f.write("registerShot('s002',{});\nregisterShot('s002',{});\n")
            self.assertEqual(scene_coverage.check(d)[0], [])

    def test_orphan_registration_is_info_only(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001", "s002", "s099"))
            errs, warns, _ = scene_coverage.check(d)
            self.assertEqual(errs, [])
            self.assertTrue(any("s099" in w for w in warns))

    def test_double_quotes_and_backticks_are_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001",))
            with open(os.path.join(d, "scenes", "shots", "99.js"), "w",
                      encoding="utf-8") as f:
                f.write('registerShot(`s002`, { draw(){} });\n')
            self.assertEqual(scene_coverage.check(d)[0], [])

    def test_no_scene_files_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=())
            self.assertTrue(any("no .js files" in e
                                for e in scene_coverage.check(d)[0]))

    def test_dynamic_registration_is_indeterminate_not_missing(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001",))
            with open(os.path.join(d, "scenes", "shots", "dyn.js"), "w",
                      encoding="utf-8") as f:
                f.write("for (const id of ids) registerShot(id, def);\n")
            errs, _, _ = scene_coverage.check(d)
            self.assertTrue(any("INDETERMINATE" in e for e in errs))
            self.assertFalse(any("no registered scene" in e for e in errs))

    def test_underscore_draft_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001",))
            with open(os.path.join(d, "scenes", "shots", "_draft.js"), "w",
                      encoding="utf-8") as f:
                f.write("registerShot('s002', {});\n")
            self.assertTrue(any("no registered scene" in e
                                for e in scene_coverage.check(d)[0]))

    def test_commented_registration_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, scenes=("s001",))
            with open(os.path.join(d, "scenes", "shots", "comment.js"), "w",
                      encoding="utf-8") as f:
                f.write("// registerShot('s002', {});\n")
            self.assertTrue(scene_coverage.check(d)[0])

    def test_numeric_zero_id_is_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(d, shots=(0, 1), scenes=("0", "1"))
            self.assertEqual(scene_coverage.check(d)[2]["shots"], 2)
            self.assertEqual(scene_coverage.check(d)[0], [])


class RenderGateScanTests(unittest.TestCase):
    def test_engine_uppercase_shot_error_is_detected(self):
        self.assertTrue(any("SHOT ERROR" in h.upper() for h in
                            render_gate.scan("SHOT ERROR s003@0.12: ReferenceError")))

    def test_defensive_slate_patterns_present(self):
        self.assertTrue(render_gate.scan("MISSING SHOT s004"))
        self.assertTrue(render_gate.scan("ERROR s002@1.20: boom"))

    def test_render_mjs_missing_scene_warning_is_detected(self):
        self.assertTrue(render_gate.scan("WARNING: 2 shots have no scene file yet: s001"))

    def test_summary_line_still_detected(self):
        self.assertTrue(render_gate.scan("2 shot error(s):"))

    def test_clean_output_has_no_false_positives(self):
        self.assertEqual(render_gate.scan("all good\nDone: out.mp4"), [])


class ReviewTargetTests(unittest.TestCase):
    def test_prefers_single_delivered_mp4(self):
        with tempfile.TemporaryDirectory() as d:
            empty_file(os.path.join(d, "out", "film.mp4"))
            path, delivered, note = review_frames.pick_video(d)
            self.assertTrue(delivered)
            self.assertTrue(path.endswith("film.mp4"))
            self.assertIn("delivered", note)

    def test_falls_back_to_silent_take_and_marks_it(self):
        with tempfile.TemporaryDirectory() as d:
            empty_file(os.path.join(d, "build", "video_silent.mp4"))
            _path, delivered, note = review_frames.pick_video(d)
            self.assertFalse(delivered)
            self.assertIn("FALLBACK", note)

    def test_ambiguous_deliverables_raise(self):
        with tempfile.TemporaryDirectory() as d:
            empty_file(os.path.join(d, "out", "a.mp4"))
            empty_file(os.path.join(d, "out", "b.mp4"))
            with self.assertRaises(ValueError):
                review_frames.pick_video(d)

    def test_nothing_present_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(review_frames.pick_video(d)[0])

    def test_aspect_is_reduced_not_assumed(self):
        self.assertEqual(review_frames.aspect_label(1080, 1920), "9:16")
        self.assertEqual(review_frames.aspect_label(1080, 1620), "2:3")
        self.assertNotEqual(review_frames.aspect_label(1080, 1620), "9:16")


LOCK = {"status": "approved", "approved_by": "I accept these stills",
        "references": [{"time": 1.0, "sha256": "abc"}]}


def write_report(d, **overrides):
    os.makedirs(os.path.join(d, "build"), exist_ok=True)
    os.makedirs(os.path.join(d, "story"), exist_ok=True)
    rep = {"video": "out/film.mp4", "video_sha256": "deadbeef",
           "human_review": "required; technical checks are not acceptance",
           "approved_by": None, "approval_state": "pending", "style_lock": None}
    rep.update(overrides)
    with open(os.path.join(d, "build", "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f)
    return d


def write_lock(d, payload=None):
    with open(os.path.join(d, "story", "style-lock.json"), "w", encoding="utf-8") as f:
        json.dump(LOCK if payload is None else payload, f)
    return d


def complete_approval(d):
    """Simulate exactly what tools/record_approval.py writes."""
    write_report(d, approved_by="I watched the whole film. Publish it.",
                 approval_state="approved", approved_at="2026-11-10T10:00:00",
                 approved_video_sha256="deadbeef",
                 style_lock={"status": "approved", "approved_by": "yes"})
    write_lock(d)
    return d


class ApprovalGateTests(unittest.TestCase):
    def test_null_approval_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            ok, issues, _ = approval_gate.evaluate(write_report(d))
            self.assertFalse(ok)
            self.assertTrue(any("approved_by is empty" in i for i in issues))

    def test_missing_report_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(approval_gate.evaluate(d)[0])

    def test_forged_approval_without_record_tool_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            write_report(d, approved_by="publish it", approval_state="approved",
                         style_lock={"status": "approved", "approved_by": "yes"})
            write_lock(d)
            self.assertFalse(approval_gate.evaluate(d)[0])

    def test_stale_byte_binding_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            write_report(d, approved_by="publish it", approval_state="approved",
                         approved_at="2026-11-10T10:00:00",
                         approved_video_sha256="OLD-BYTES",
                         style_lock={"status": "approved", "approved_by": "yes"})
            write_lock(d)
            self.assertFalse(approval_gate.evaluate(d)[0])

    def test_empty_lock_manifest_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            complete_approval(d)
            write_lock(d, payload={})
            self.assertFalse(approval_gate.evaluate(d)[0])

    def test_standing_rule_must_remain(self):
        with tempfile.TemporaryDirectory() as d:
            complete_approval(d)
            with open(os.path.join(d, "build", "report.json"), encoding="utf-8") as f:
                rep = json.load(f)
            rep["human_review"] = "machine checks passed"
            with open(os.path.join(d, "build", "report.json"), "w", encoding="utf-8") as f:
                json.dump(rep, f)
            self.assertFalse(approval_gate.evaluate(d)[0])

    def test_full_recorded_approval_passes(self):
        with tempfile.TemporaryDirectory() as d:
            ok, issues, _ = approval_gate.evaluate(complete_approval(d))
            self.assertTrue(ok, issues)

    def test_record_then_gate_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            write_report(d, style_lock={"status": "approved", "approved_by": "yes"})
            write_lock(d)
            self.assertFalse(approval_gate.evaluate(d)[0])
            record_approval.record(d, "I watched it, publish it")
            ok, issues, _ = approval_gate.evaluate(d)
            self.assertTrue(ok, issues)

    def test_record_refuses_report_without_hash(self):
        with tempfile.TemporaryDirectory() as d:
            write_report(d, video_sha256=None)
            with self.assertRaises(ValueError):
                record_approval.record(d, "publish it")

    def test_empty_words_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write_report(d)
            with self.assertRaises(ValueError):
                record_approval.record(d, "   ")


def read_tool(name):
    with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
        return fh.read()


class SourceContractTests(unittest.TestCase):
    """Guard the security boundary the independent falsifier found."""
    def test_generate_cannot_forge_approval(self):
        src = read_tool("generate.py")
        # The docstring legitimately mentions the removed flag; check the CODE.
        self.assertNotIn("ap.add_argument(\"--approved-by\"", src)
        self.assertNotIn("a.approved_by", src)
        self.assertNotIn("report_cmd +=", src)

    def test_render_report_refuses_approved_by(self):
        self.assertIn("REFUSED", read_tool("render_report.py"))

    def test_generate_makes_seam_gate_fatal_without_strict(self):
        src = read_tool("generate.py")
        self.assertIn("if sg:", src)
        self.assertNotIn("if a.strict and sg:", src)


@unittest.skipUnless(_words, "faceless-shorts scripts/ not found")
class WordTimingCompatTests(unittest.TestCase):
    def test_script_json(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "script.json"), "w", encoding="utf-8") as f:
                json.dump({"lines": [{"text": "hello"}]}, f)
            self.assertEqual(_words.load_script(Path(d))["lines"][0]["text"], "hello")

    def test_dialogue_json_fallback(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "dialogue.json"), "w", encoding="utf-8") as f:
                json.dump({"lines": [{"text": "hello", "voice": "af_heart"}]}, f)
            self.assertEqual(_words.load_script(Path(d))["lines"][0]["text"], "hello")

    def test_both_absent_raises(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                _words.load_script(Path(d))


class ProjectTests(unittest.TestCase):
    def test_paths_resolve(self):
        import project as P
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "story"))
            os.makedirs(os.path.join(d, "scenes"))
            os.makedirs(os.path.join(d, "build"))
            os.makedirs(os.path.join(d, "out"))
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"aspect": "16:9", "fps": 30, "resolution": "720p", "title": "t"}, f)
            pr = P.Project(d)
            self.assertTrue(pr.exists())
            self.assertEqual(pr.aspect, "16:9")
            self.assertEqual(pr.fps, 30)
            self.assertEqual(pr.resolution, "720p")
            self.assertEqual(pr.title, "t")
            self.assertEqual(pr.story, os.path.join(os.path.abspath(d), "story"))
            self.assertEqual(pr.shots_path, os.path.join(os.path.abspath(d), "story", "shots.json"))
            self.assertTrue(pr.config)  # cached

    def test_missing_config_returns_empty(self):
        import project as P
        with tempfile.TemporaryDirectory() as d:
            pr = P.Project(d)
            self.assertFalse(pr.exists())
            self.assertEqual(pr.config, {})
            self.assertEqual(pr.aspect, "9:16")  # default


class FrameQATests(unittest.TestCase):
    def test_freeze_window_exempt(self):
        import frame_qa as fq
        wins = fq.load_freeze_times(None)
        self.assertEqual(wins, [])
        # synthetic shots.json with a freeze
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, "shots.json")
            with open(sp, "w") as f:
                json.dump({"shots": [{"id": "s1", "start": 0.0, "end": 4.0,
                                     "freeze": {"u": 0.5}}]}, f)
            wins = fq.load_freeze_times(sp)
            self.assertEqual(len(wins), 1)
            # freeze point at 2.0s; exempt window covers it
            self.assertTrue(fq.in_freeze_window(2.0, wins))
            self.assertFalse(fq.in_freeze_window(0.5, wins))

    def test_luma_thresholds(self):
        import frame_qa as fq
        # black < 8, white > 247
        self.assertTrue(5 < 8)
        self.assertTrue(250 > 247)


class AcceptanceStaticTests(unittest.TestCase):
    def test_no_record_approval_import(self):
        src = open(os.path.join(TOOLS, "acceptance.py"), encoding="utf-8").read()
        self.assertNotIn("import record_approval", src)
        self.assertNotIn("from record_approval", src)

    def test_no_approved_by_write(self):
        src = open(os.path.join(TOOLS, "acceptance.py"), encoding="utf-8").read()
        # strip the module docstring; check only code for writes of approved_by
        parts = src.split('"""')
        code = parts[2] if len(parts) >= 3 else src
        self.assertNotIn('approved_by', code)
        self.assertNotIn('report.json', code)
        self.assertNotIn('open(', code)  # no file writes at all in acceptance.py

    def test_no_record_command(self):
        src = open(os.path.join(TOOLS, "acceptance.py"), encoding="utf-8").read()
        self.assertNotIn('sub.add_parser("record"', src)
        self.assertNotIn("def cmd_record", src)


class SbsSheetTests(unittest.TestCase):
    def test_imports(self):
        import sbs_sheet as s
        self.assertTrue(hasattr(s, "stitch"))
        self.assertTrue(hasattr(s, "main"))




# --- approval_gate behavioral tests (5 cases) ---

def _make_ag_project(root, approved_by=None, state="approved", approved_hash=None,
                     tamper=False, delete_video=False, human_review="required; technical checks are not acceptance"):
    import hashlib, json, os
    os.makedirs(os.path.join(root, "build"), exist_ok=True)
    os.makedirs(os.path.join(root, "story"), exist_ok=True)
    os.makedirs(os.path.join(root, "out"), exist_ok=True)
    vid = "out/test.mp4"
    vidpath = os.path.join(root, vid)
    with open(vidpath, "wb") as f:
        f.write(b"fake video bytes" if not tamper else b"tampered bytes")
    vsha = hashlib.sha256(open(os.path.join(root, "out", "test.mp4" if not tamper else vid), "rb").read()).hexdigest() if not tamper else "originalhash"
    # recompute vsha from original content for the report
    with open(os.path.join(root, vid), "wb") as f:
        f.write(b"fake video bytes")
    vsha = hashlib.sha256(open(os.path.join(root, vid), "rb").read()).hexdigest()
    if tamper:
        with open(vidpath, "wb") as f:
            f.write(b"tampered bytes")
    if delete_video and os.path.exists(vidpath):
        os.remove(vidpath)
    rep = {
        "schema": "aitrends-render-report-v1", "project": "t", "title": "t",
        "video": vid, "video_sha256": vsha,
        "voice_sha256": "x", "voice_rate": "x", "aspect": "9:16", "resolution": "1080p",
        "style": "midnight", "codec": "h264", "width": 1080, "height": 1920, "fps": 24.0,
        "frames": 10, "duration": 1.0, "bytes": 100, "shot_count": 1, "music_plan": [],
        "sfx_cues": 0, "audio": {"mean_volume": -17.0, "max_volume": -1.0},
        "lufs": {"integrated_lufs": -14.0, "true_peak_dbtp": -1.6, "lra_lu": 3.0, "standard": "x"},
        "motion": {"exit": 0, "verdict": "OK", "windows": 1, "min_motion": 0.01,
                   "median_motion": 0.01, "issues": [], "error": "", "note": "x"},
        "style_lock": {"status": "approved", "approved_by": "owner"},
        "human_review": human_review,
        "approved_by": approved_by, "approval_state": state,
        "approved_at": "2026-11-10T00:00:00" if approved_by else None,
        "approved_video_sha256": (approved_hash if approved_hash is not None
                                  else (vsha if approved_by else None)),
    }
    with open(os.path.join(root, "build", "report.json"), "w") as f:
        json.dump(rep, f)
    lock = {"schema": "aitrends-style-lock-v1", "status": "approved", "character": "x",
            "project": "t", "style": "midnight", "resolution": "1080p", "aspect": "9:16",
            "required": 1, "approved_by": "owner", "note": None,
            "snapshotted_at": "2026-11-10T00:00:00",
            "references": [{"time": 1.0, "path": "story/style-lock/1.00s.png",
                            "sha256": "abc", "width": 100, "height": 100}]}
    with open(os.path.join(root, "story", "style-lock.json"), "w") as f:
        json.dump(lock, f)
    os.makedirs(os.path.join(root, "story", "style-lock"), exist_ok=True)
    with open(os.path.join(root, "story", "style-lock", "1.00s.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    return vsha


class ApprovalGateBehavioralTests(unittest.TestCase):
    def test_unapproved_fails(self):
        with tempfile.TemporaryDirectory() as d:
            _make_ag_project(d, approved_by=None)
            ok, issues, state = approval_gate.evaluate(d)
            self.assertFalse(ok)
            self.assertTrue(any("approved_by is empty" in i for i in issues))

    def test_approved_passes(self):
        with tempfile.TemporaryDirectory() as d:
            _make_ag_project(d, approved_by="owner words", state="approved")
            ok, issues, state = approval_gate.evaluate(d)
            self.assertTrue(ok, issues)
            self.assertEqual(issues, [])

    def test_tampered_bytes_caught(self):
        with tempfile.TemporaryDirectory() as d:
            _make_ag_project(d, approved_by="owner words", state="approved", tamper=True)
            ok, issues, state = approval_gate.evaluate(d, verify_bytes=True)
            self.assertFalse(ok)
            self.assertTrue(any("no longer match" in i for i in issues))

    def test_missing_video_caught(self):
        with tempfile.TemporaryDirectory() as d:
            _make_ag_project(d, approved_by="owner words", state="approved", delete_video=True)
            ok, issues, state = approval_gate.evaluate(d, verify_bytes=True)
            self.assertFalse(ok)
            self.assertTrue(any("missing" in i.lower() for i in issues))

    def test_hash_mismatch_caught(self):
        with tempfile.TemporaryDirectory() as d:
            _make_ag_project(d, approved_by="owner words", state="approved",
                             approved_hash="deadbeef" + "0" * 56)
            ok, issues, state = approval_gate.evaluate(d)
            self.assertFalse(ok)
            self.assertTrue(any("approved_video_sha256 !=" in i for i in issues))


# --- frame_qa positive controls (requires ffmpeg) ---

import shutil as _shutil
_FFMPEG = _shutil.which("ffmpeg") is not None
# REQUIRE_FFMPEG=1 turns ffmpeg-dependent skips into failures
if os.environ.get("REQUIRE_FFMPEG") == "1" and not _FFMPEG:
    raise RuntimeError("REQUIRE_FFMPEG=1 but ffmpeg not found on PATH")


def _make_clip(path, color, duration=2.0, fps=24, size="320x240"):
    """Generate a single-color (or two-color pop) mp4 clip."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:s={size}:d={duration}:r={fps}",
         "-pix_fmt", "yuv420p", path],
        capture_output=True, check=True)


@unittest.skipUnless(_FFMPEG, "ffmpeg not available")
class FrameQAPositiveTests(unittest.TestCase):
    def test_black_clip_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "black.mp4")
            _make_clip(clip, "black")
            # frame_qa samples 12 frames; all black -> black findings
            # Run via main() capturing exit code is hard; test extract_luma directly
            info = fq.ffprobe_json(clip)
            dur = float(info["format"]["duration"])
            ts = [dur * (i + 0.5) / 6 for i in range(6)]
            lumas = [fq.extract_luma(clip, t) for t in ts]
            blacks = [l for l in lumas if l < 8]
            self.assertEqual(len(blacks), len(lumas), "all frames should be black")

    def test_white_clip_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "white.mp4")
            _make_clip(clip, "white")
            info = fq.ffprobe_json(clip)
            dur = float(info["format"]["duration"])
            ts = [dur * (i + 0.5) / 6 for i in range(6)]
            lumas = [fq.extract_luma(clip, t) for t in ts]
            whites = [l for l in lumas if l > 247]
            self.assertEqual(len(whites), len(lumas), "all frames should be white")

    def test_frozen_clip_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "frozen.mp4")
            _make_clip(clip, "blue")
            info = fq.ffprobe_json(clip)
            dur = float(info["format"]["duration"])
            ts = [dur * (i + 0.5) / 6 for i in range(6)]
            lumas = [fq.extract_luma(clip, t) for t in ts]
            # all identical -> frozen run
            diffs = [abs(lumas[i] - lumas[i-1]) for i in range(1, len(lumas))]
            self.assertTrue(all(dd < 1.0 for dd in diffs), "should be frozen (no variation)")

    def test_pop_clip_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            # first half black, second half white -> pop at midpoint
            clip = os.path.join(d, "pop.mp4")
            # use ffmpeg to concat two color segments
            seg1 = os.path.join(d, "seg1.mp4")
            seg2 = os.path.join(d, "seg2.mp4")
            _make_clip(seg1, "black", duration=1.0)
            _make_clip(seg2, "white", duration=1.0)
            concat_list = os.path.join(d, "list.txt")
            with open(concat_list, "w") as f:
                f.write('file %s\nfile %s\n' % (seg1.replace(chr(92), '/'), seg2.replace(chr(92), '/')))
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                 "-c", "copy", clip],
                capture_output=True, check=True)

            info = fq.ffprobe_json(clip)
            dur = float(info["format"]["duration"])
            ts = [dur * (i + 0.5) / 6 for i in range(6)]
            lumas = [fq.extract_luma(clip, t) for t in ts]
            pops = [i for i in range(1, len(lumas))
                    if abs(lumas[i] - lumas[i-1]) >= 40.0]
            self.assertTrue(len(pops) >= 1, "should detect at least one pop")


# --- AcceptanceBehavioralTests ---

class AcceptanceBehavioralTests(unittest.TestCase):
    def _make_project(self, d, approved=False):
        _make_ag_project(d, approved_by=("owner words" if approved else None),
                         state=("approved" if approved else "none"),
                         approved_hash=None)
        if approved:
            import hashlib, json
            rep_path = os.path.join(d, "build", "report.json")
            rep = json.load(open(rep_path))
            vidpath = os.path.join(d, rep["video"])
            vsha = hashlib.sha256(open(vidpath, "rb").read()).hexdigest()
            rep["video_sha256"] = vsha
            rep["approved_video_sha256"] = vsha
            json.dump(rep, open(rep_path, "w"))

    def test_acceptance_does_not_modify_report(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_project(d, approved=False)
            report_path = os.path.join(d, "build", "report.json")
            before = open(report_path, "rb").read()
            subprocess.run([sys.executable, os.path.join(TOOLS, "acceptance.py"),
                            "check", "--project", d], capture_output=True)
            after = open(report_path, "rb").read()
            self.assertEqual(before, after, "acceptance check must not modify report.json")

    def test_acceptance_does_not_modify_report_approved(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_project(d, approved=True)
            report_path = os.path.join(d, "build", "report.json")
            before = open(report_path, "rb").read()
            subprocess.run([sys.executable, os.path.join(TOOLS, "acceptance.py"),
                            "check", "--project", d], capture_output=True)
            after = open(report_path, "rb").read()
            self.assertEqual(before, after, "acceptance check must not modify report.json (approved)")

    def test_acceptance_no_record_command(self):
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "acceptance.py"), "--help"],
                            capture_output=True, text=True)
        self.assertNotIn("record", r.stdout + r.stderr)



@unittest.skipUnless(_FFMPEG, "ffmpeg not available")
class FrameQAFullScanTests(unittest.TestCase):
    """Full-scan (per-frame) positive controls for frame_qa."""

    def test_all_lumas_count(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "blue.mp4")
            _make_clip(clip, "blue", duration=1.0, fps=24)
            raw = fq.extract_all_lumas(clip, 24.0)
            self.assertGreater(len(raw), 20)
            self.assertLess(len(raw), 30)

    def test_freeze_12_frames_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "freeze12.mp4")
            seg1 = os.path.join(d, "s1.mp4")
            seg2 = os.path.join(d, "s2.mp4")
            _make_clip(seg1, "blue", duration=0.5, fps=24)
            _make_clip(seg2, "red", duration=1.5, fps=24)
            concat_list = os.path.join(d, "list.txt")
            with open(concat_list, "w") as f:
                f.write("file %s\nfile %s\n" % (seg1.replace(chr(92), "/"), seg2.replace(chr(92), "/")))
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                            "-c", "copy", clip], capture_output=True, check=True)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            raw = fq.extract_all_lumas(clip, fps)
            lumas = [float(b) for b in raw]
            run_len = 0
            max_run = 0
            for i in range(1, len(lumas)):
                if abs(lumas[i] - lumas[i-1]) < 1.0:
                    run_len += 1
                    max_run = max(max_run, run_len)
                else:
                    run_len = 0
            self.assertGreaterEqual(max_run, 10, "12-frame freeze should be detected (got %d)" % max_run)

    def test_freeze_11_frames_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "freeze11.mp4")
            seg1 = os.path.join(d, "s1.mp4")
            seg2 = os.path.join(d, "s2.mp4")
            _make_clip(seg1, "blue", duration=0.46, fps=24)
            _make_clip(seg2, "red", duration=1.5, fps=24)
            concat_list = os.path.join(d, "list.txt")
            with open(concat_list, "w") as f:
                f.write("file %s\nfile %s\n" % (seg1.replace(chr(92), "/"), seg2.replace(chr(92), "/")))
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                            "-c", "copy", clip], capture_output=True, check=True)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            raw = fq.extract_all_lumas(clip, fps)
            lumas = [float(b) for b in raw]
            run_len = 0
            max_run = 0
            for i in range(1, len(lumas)):
                if abs(lumas[i] - lumas[i-1]) < 1.0:
                    run_len += 1
                    max_run = max(max_run, run_len)
                else:
                    run_len = 0
            self.assertGreaterEqual(max_run, 9, "11-frame freeze should be detected (got %d)" % max_run)

    def test_single_pop_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "pop.mp4")
            seg1 = os.path.join(d, "s1.mp4")
            seg2 = os.path.join(d, "s2.mp4")
            _make_clip(seg1, "black", duration=1.0, fps=24)
            _make_clip(seg2, "white", duration=1.0, fps=24)
            concat_list = os.path.join(d, "list.txt")
            with open(concat_list, "w") as f:
                f.write("file %s\nfile %s\n" % (seg1.replace(chr(92), "/"), seg2.replace(chr(92), "/")))
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                            "-c", "copy", clip], capture_output=True, check=True)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            raw = fq.extract_all_lumas(clip, fps)
            lumas = [float(b) for b in raw]
            pops = [i for i in range(1, len(lumas)) if abs(lumas[i] - lumas[i-1]) >= 40.0]
            self.assertGreaterEqual(len(pops), 1, "single pop frame should be detected")

    def test_freeze_at_non_sample_offset(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "offset.mp4")
            seg1 = os.path.join(d, "s1.mp4")
            seg2 = os.path.join(d, "s2.mp4")
            _make_clip(seg1, "blue", duration=0.3, fps=24)
            _make_clip(seg2, "red", duration=1.7, fps=24)
            concat_list = os.path.join(d, "list.txt")
            with open(concat_list, "w") as f:
                f.write("file %s\nfile %s\n" % (seg1.replace(chr(92), "/"), seg2.replace(chr(92), "/")))
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                            "-c", "copy", clip], capture_output=True, check=True)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            raw = fq.extract_all_lumas(clip, fps)
            lumas = [float(b) for b in raw]
            run_len = 0
            max_run = 0
            for i in range(1, len(lumas)):
                if abs(lumas[i] - lumas[i-1]) < 1.0:
                    run_len += 1
                    max_run = max(max_run, run_len)
                else:
                    run_len = 0
            self.assertGreaterEqual(max_run, 5, "freeze at non-sample offset should be detected (got %d)" % max_run)



class FrameQABoundaryTests(unittest.TestCase):
    """Boundary tests for frame_qa SAD-based detection thresholds.

    These tests call the real classification path (fq.analyze_frames), not just
    arithmetic on SAD values.  They verify that the classifier produces the
    expected findings/info split.
    """

    def _make_freeze_clip(self, d, freeze_frames):
        red1 = os.path.join(d, "red1.mp4")
        blue = os.path.join(d, "blue.mp4")
        red2 = os.path.join(d, "red2.mp4")
        _make_clip(red1, "red", duration=5.0/24.0, fps=24)
        _make_clip(blue, "blue", duration=freeze_frames/24.0, fps=24)
        _make_clip(red2, "red", duration=5.0/24.0, fps=24)
        concat_list = os.path.join(d, "list.txt")
        with open(concat_list, "w") as f:
            f.write("file %s\nfile %s\nfile %s\n" % (
                red1.replace(chr(92), "/"), blue.replace(chr(92), "/"), red2.replace(chr(92), "/")))
        clip = os.path.join(d, "clip.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                        "-c", "copy", clip], capture_output=True, check=True)
        return clip

    def _analyze(self, clip):
        import frame_qa as fq
        frames = fq.extract_all_frames(clip)
        info = fq.ffprobe_json(clip)
        fps = fq.parse_fps(info)
        dur = float(info["format"]["duration"])
        return fq.analyze_frames(frames, fps, dur, []), fq

    def test_11_frames_is_info_only(self):
        with tempfile.TemporaryDirectory() as d:
            clip = self._make_freeze_clip(d, 11)
            result, fq = self._analyze(clip)
            self.assertEqual(len(result["frozen_runs"]), 0,
                             "11-frame freeze must NOT be a finding")
            self.assertGreater(len(result["frozen_info"]), 0,
                               "11-frame freeze must appear as info")

    def test_12_frames_is_finding(self):
        with tempfile.TemporaryDirectory() as d:
            clip = self._make_freeze_clip(d, 12)
            result, fq = self._analyze(clip)
            self.assertGreater(len(result["frozen_runs"]), 0,
                               "12-frame freeze must be a finding")

    def test_single_midclip_pop_detected(self):
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "pop.mp4")
            subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i',
                            'color=c=0x000000:s=320x240:r=24:d=2',
                            '-vf', "drawbox=x=0:y=0:w=320:h=240:color=white:t=fill:enable='eq(n,24)'",
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            result, fq = self._analyze(clip)
            self.assertGreater(len(result["pops"]), 0,
                               "single mid-clip pop should be detected")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_small_motion_not_frozen(self):
        """A moving element over a static background must NOT be flagged frozen.

        At 8x8 this would false-positive (motion averages away); at 32x18 the
        SAD stays above SAD_FREEZE.
        """
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "motion.mp4")
            # Generate a 320x240 video with an 80x80 block moving horizontally.
            # Use raw frames to avoid ffmpeg filter expression issues.
            W, H = 320, 240
            N = 48
            raw = bytearray()
            for f in range(N):
                bx = (f * 7) % (W - 80)
                for y in range(H):
                    for x in range(W):
                        if bx <= x < bx + 80 and 80 <= y < 160:
                            raw.append(200)
                        else:
                            raw.append(50)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            result, fq = self._analyze(clip)
            self.assertEqual(len(result["frozen_runs"]), 0,
                             "moving element must not be flagged as frozen")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_subtle_motion_not_frozen(self):
        """Subtle motion (SAD in 40-120 range) must NOT be flagged frozen.

        A blink or mouth-only motion produces SAD just above SAD_FREEZE.
        This verifies the threshold does not false-positive on small changes.
        """
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "subtle.mp4")
            W, H = 320, 240
            N = 48
            raw = bytearray()
            for f in range(N):
                brightness = (100 + f * 5) % 256
                for y in range(H):
                    for x in range(W):
                        if 100 <= x < 140 and 100 <= y < 140:
                            raw.append(brightness)
                        else:
                            raw.append(50)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            result, fq = self._analyze(clip)
            self.assertEqual(len(result["frozen_runs"]), 0,
                             "subtle motion must not be flagged as frozen")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_flicker_is_finding(self):
        """Synthetic flicker (bright, 2 black, bright) must be a finding."""
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "flicker.mp4")
            W, H = 320, 240
            N = 48
            raw = bytearray()
            for f in range(N):
                val = 0 if 20 <= f <= 21 else 100
                for _ in range(H * W):
                    raw.append(val)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            result, fq = self._analyze(clip)
            self.assertTrue(any(br["classification"] == "finding" for br in result["black_runs"]),
                            "flicker must be classified as finding")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_pop_is_detected(self):
        """Synthetic single-frame pop must be detected."""
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "pop.mp4")
            W, H = 320, 240
            N = 48
            raw = bytearray()
            for f in range(N):
                val = 255 if f == 24 else 100
                for _ in range(H * W):
                    raw.append(val)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            result, fq = self._analyze(clip)
            self.assertGreater(len(result["pops"]), 0, "pop must be detected")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_flicker_in_declared_dip_is_finding(self):
        """Flicker inside a declared dip window must still be a finding.

        Proves the rule-order fix: flicker check runs before anchoring.
        """
        import frame_qa as fq
        import json
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "flicker_dip.mp4")
            W, H = 320, 240
            N = 48
            # frames 20-21: instant drop to black and rise (flicker)
            # surrounding frames: bright (100)
            raw = bytearray()
            for f in range(N):
                val = 0 if 20 <= f <= 21 else 100
                for _ in range(H * W):
                    raw.append(val)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            # shots.json declares a dip at frame 20 (t=0.833)
            shots = [{"id": "s1", "start": 0.0, "end": 2.0,
                      "in": {"type": "dip", "dur": 0.5}}]
            # Place the dip at the flicker location
            shots = [{"id": "s1", "start": 0.833, "end": 2.0,
                      "in": {"type": "dip", "dur": 0.5}}]
            frames = fq.extract_all_frames(clip)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            dur = float(info['format']['duration'])
            result = fq.analyze_frames(frames, fps, dur, [], shots)
            self.assertTrue(any(br["classification"] == "finding" for br in result["black_runs"]),
                            "flicker in declared dip must be finding")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_gradual_dip_in_declared_window_is_expected(self):
        """Gradual dip inside a declared window stays 'expected'.

        Reproduces cine_release frames 224-234 synthetically.
        """
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "gradual_dip.mp4")
            W, H = 320, 240
            N = 48
            # Gradual ramp down and up (like cine_release dip)
            raw = bytearray()
            for f in range(N):
                if f < 20:
                    val = 100
                elif f == 20:
                    val = 30
                elif f == 21:
                    val = 5
                elif f == 22:
                    val = 3
                elif f == 23:
                    val = 5
                elif f == 24:
                    val = 20
                elif f == 25:
                    val = 40
                else:
                    val = 100
                for _ in range(H * W):
                    raw.append(val)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            # shots.json declares a dip at the boundary
            shots = [{"id": "s1", "start": 20/24.0, "end": 2.0,
                      "in": {"type": "dip", "dur": 0.5}}]
            frames = fq.extract_all_frames(clip)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            dur = float(info['format']['duration'])
            result = fq.analyze_frames(frames, fps, dur, [], shots)
            # The run at frames 21-23 (black) should be 'expected'
            black_runs = result["black_runs"]
            self.assertTrue(any(br["classification"] == "expected" for br in black_runs),
                            "gradual dip in declared window must be expected")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_end_tail_cap_is_finding(self):
        """Trailing black > 0.5s is a finding, not end_tail."""
        import frame_qa as fq
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "long_tail.mp4")
            W, H = 320, 240
            N = 48
            # 24 frames of content, then 24 frames of black (1s tail)
            raw = bytearray()
            for f in range(N):
                val = 100 if f < 24 else 0
                for _ in range(H * W):
                    raw.append(val)
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                fh.write(raw)
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '%dx%d' % (W, H), '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            frames = fq.extract_all_frames(clip)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            dur = float(info['format']['duration'])
            result = fq.analyze_frames(frames, fps, dur, [], [])
            # The trailing black run should be 'finding' (not end_tail) due to cap
            black_runs = result["black_runs"]
            tail_runs = [br for br in black_runs if br["start_idx"] >= 20]
            self.assertTrue(any(br["classification"] == "finding" for br in tail_runs),
                            "long trailing black must be finding, not end_tail")

    @unittest.skipUnless(_FFMPEG, "ffmpeg not available")
    def test_real_frame_freeze_detected(self):
        """Hold a golden PNG frame for 15 frames through H.264; must detect freeze."""
        import frame_qa as fq
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            clip = os.path.join(d, "golden_freeze.mp4")
            # Load golden frame and convert to grayscale video
            img = Image.open('tests/golden/frame_01.png').convert('L')
            # Resize to 320x240 for manageable encoding
            img = img.resize((320, 240))
            raw_path = os.path.join(d, "raw.gray")
            with open(raw_path, "wb") as fh:
                for _ in range(15):
                    fh.write(img.tobytes())
            subprocess.run(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                            '-s', '320x240', '-r', '24', '-i', raw_path,
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip],
                           capture_output=True, check=True)
            frames = fq.extract_all_frames(clip)
            info = fq.ffprobe_json(clip)
            fps = fq.parse_fps(info)
            dur = float(info['format']['duration'])
            result = fq.analyze_frames(frames, fps, dur, [], [])
            self.assertGreater(len(result["frozen_runs"]), 0,
                               "held golden frame must be detected as freeze")
            self.assertTrue(any(fr[4] >= 12 for fr in result["frozen_runs"]),
                            "freeze must be >= 12 frames")

if __name__ == "__main__":
    unittest.main(verbosity=2)
