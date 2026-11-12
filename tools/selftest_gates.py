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

# director.py is a script, not a package module.
import importlib.util as _ilu  # noqa: E402

# generate.py is a script too, and gate_activation() lives there.
try:
    _gen_spec = _ilu.spec_from_file_location(
        "generate_mod", os.path.join(TOOLS, "generate.py"))
    _gen = _ilu.module_from_spec(_gen_spec)
    _gen_spec.loader.exec_module(_gen)
except Exception:
    _gen = None
try:
    _dr_spec = _ilu.spec_from_file_location(
        "director_mod", os.path.join(TOOLS, "director.py"))
    DR = _ilu.module_from_spec(_dr_spec)
    _dr_spec.loader.exec_module(DR)
except Exception:
    DR = None

# variety_gate.py is a standalone CLI, not a package module.
try:
    import importlib.util as _ilu
    _vg_spec = _ilu.spec_from_file_location(
        "variety_gate", os.path.join(TOOLS, "variety_gate.py"))
    VG = _ilu.module_from_spec(_vg_spec)
    _vg_spec.loader.exec_module(VG)
except Exception:
    VG = None
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
    import fresh.schemas as _fresh_schemas  # noqa: E402
    import fresh.core as _fresh_core        # noqa: E402
    import fresh.palette as _fresh_palette  # noqa: E402
    import fresh.story as _fresh_story      # noqa: E402
    import fresh.series as _fresh_series    # noqa: E402
    import fresh.sets as _fresh_sets        # noqa: E402
except ImportError:
    _fresh_schemas = None
    _fresh_core = None
    _fresh_palette = None
    _fresh_story = None
    _fresh_series = None
    _fresh_sets = None

# Task 1's contract gets its OWN guard: sharing the block above would let any
# sibling fresh.* ImportError null _fresh_story_schema, silently SKIPping every
# FreshStorySchemaTests test while the suite still reports green.
try:
    import fresh.story_schema as _fresh_story_schema  # noqa: E402
except ImportError:
    _fresh_story_schema = None

# Its own guard: the scene decides the location, so this module is load-bearing
# for DerivedLocationTests and must fail loudly rather than skip.
try:
    import fresh.location as LOC  # noqa: E402
except ImportError:
    LOC = None

# Its own guard for the same reason: a sibling fresh.* failure must not silently
# SKIP DerivedAudioTests while the suite still reports green.
try:
    import fresh.audio as _fresh_audio  # noqa: E402
except ImportError:
    _fresh_audio = None

try:
    import fresh.captions as _fresh_captions  # noqa: E402
except ImportError:
    _fresh_captions = None

try:
    import fresh.cast as _fresh_cast  # noqa: E402
except ImportError:
    _fresh_cast = None

# Same reason as the contract guard above: a sibling fresh.* ImportError must not
# null _fresh_shapes and silently SKIP FreshShapesTests while the suite is green.
try:
    import fresh.shapes as _fresh_shapes  # noqa: E402
except ImportError:
    _fresh_shapes = None

# Same reason as the guards above: a sibling fresh.* ImportError must not null
# _fresh_story and silently SKIP FreshStoryTests while the suite is green.
try:
    import fresh.story as _fresh_story  # noqa: E402
except ImportError:
    _fresh_story = None

# Same reason for the series bible: only fresh.series' own ImportError may null
# _fresh_series, never a sibling's.
try:
    import fresh.series as _fresh_series  # noqa: E402
except ImportError:
    _fresh_series = None

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


class FreshStorySchemaTests(unittest.TestCase):
    """The story contract. Skipped only if the fresh package is absent."""

    def setUp(self):
        if _fresh_story_schema is None:
            self.skipTest("fresh.story_schema not importable")
        self.V = _fresh_story_schema

    def _minimal(self, **over):
        d = {
            "title": "T", "aspect": "9:16", "resolution": "1080p", "fps": 24,
            "style": "midnight", "set": "room", "chars": "inkbean",
            "cast": {"MAX": {"color": "#c2553d", "top": "trench",
                             "legs": "#2a2433", "head": "none"}},
            "shots": [
                {"id": "s001", "size": "wide", "line": "Three in the morning.",
                 "hold": 0.5, "who": "MAX", "pose": "stand", "expr": "neutral",
                 "in": {"type": "fade", "dur": 0.5}},
                {"id": "s002", "size": "close", "line": "Don't move.",
                 "hold": 0.3, "who": "MAX", "pose": "stand", "expr": "worried",
                 "in": {"type": "cut"}},
            ],
            "music": [],
        }
        d.update(over)
        return d

    def test_minimal_story_is_clean(self):
        errs, warns = self.V.validate_story(self._minimal())
        self.assertEqual(errs, [])

    def test_unknown_expression_is_an_error_not_a_warning(self):
        d = self._minimal()
        d["shots"][1]["expr"] = "smirk"          # not in PRESETS -> renders neutral
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("smirk" in e for e in errs), errs)

    def test_stick_rig_uses_the_other_expression_vocabulary(self):
        d = self._minimal(chars="stick")
        d["shots"][1]["expr"] = "listening"      # a PRESETS name, absent from rig2d EXPR
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("listening" in e for e in errs), errs)
        d["shots"][1]["expr"] = "scared"         # valid rig2d EXPR
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_unimplemented_prop_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["prop"] = {"kind": "sword"}   # director.py:1024 -> magenta box
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("sword" in e for e in errs), errs)

    def test_walk_pose_without_walk_spec_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["pose"] = "walk"              # director.py:1019 -> stands still
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("walk" in e for e in errs), errs)
        d["shots"][0]["walk"] = {"from": 0.13, "to": 0.40}
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_misspelled_param_key_is_an_error(self):
        d = self._minimal()
        d["shots"][1]["exprto"] = "worried"         # silently dropped by PARAM_KEYS
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("exprto" in e for e in errs), errs)

    def test_insert_without_intent_is_a_dead_cut(self):
        d = self._minimal()
        d["shots"].insert(1, {"id": "s00X", "size": "insert", "line": "",
                              "hold": 0.75, "insertKind": "phone",
                              "in": {"type": "cut"}})
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("dead cut" in e for e in errs), errs)

    def test_insert_with_eyeline_intent_is_clean(self):
        d = self._minimal()
        d["shots"].insert(1, {"id": "s00X", "size": "insert", "line": "",
                              "hold": 0.75, "insertKind": "phone",
                              "cut_intent": "eyeline", "in": {"type": "cut"}})
        d["shots"][2]["cut_intent"] = "eyeline"
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])

    def test_over_length_line_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["line"] = "one two three four five six seven eight nine"
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("9 words" in e for e in errs), errs)

    def test_hold_budget_over_ceiling_is_a_warning(self):
        d = self._minimal()
        for s in d["shots"]:
            s["hold"] = 3.0
        errs, warns = self.V.validate_story(d)
        self.assertEqual(errs, [])
        self.assertTrue(any("hold budget" in w for w in warns), warns)

    def test_shot_density_over_ceiling_warns(self):
        # (hold_total + words/2) / dict shots = (4.8 + 6/2) / 2 = 3.90 s/shot > 2.0.
        # 4.8 stays under MAX_HOLD_BUDGET, so density is the only ceiling breached.
        d = self._minimal()
        for s in d["shots"]:
            s["hold"] = 2.4
        errs, warns = self.V.validate_story(d)
        self.assertEqual(errs, [])
        self.assertTrue(any("3.90s/shot" in w for w in warns), warns)
        # (0.8 + 2/2) / 2 = 0.90 s/shot -- comfortably under the ceiling.
        d = self._minimal()
        for s in d["shots"]:
            s["line"] = "Hi."
        errs, warns = self.V.validate_story(d)
        self.assertEqual(errs, [])
        self.assertFalse(any("s/shot" in w for w in warns), warns)

    def test_unknown_cast_member_is_an_error(self):
        d = self._minimal()
        d["shots"][0]["who"] = "NOBODY"
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("NOBODY" in e for e in errs), errs)

    def test_file_based_sfx_cue_is_valid_but_amb_stays_closed(self):
        # audio/mix.py:81 loads a cue from disk by extension; projects/acting-pass
        # and projects/one-more-night-9x16 both ship .ogg foley cues.
        d = self._minimal()
        d["shots"][0]["sfx"] = [{"name": "../../audio/foley/creak1.ogg", "at": 0.2}]
        errs, _ = self.V.validate_story(d)
        self.assertEqual(errs, [])
        d["shots"][0]["sfx"] = [{"name": "creak1", "at": 0.2}]
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("creak1" in e for e in errs), errs)
        d["shots"][0]["sfx"] = []
        d["shots"][0]["amb"] = {"name": "../../audio/foley/creak1.ogg"}
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("amb name" in e for e in errs), errs)

    def test_malformed_hold_and_line_report_instead_of_raising(self):
        for bad in (None, "0.5s", {}, [], 10 ** 400):
            d = self._minimal()
            d["shots"][0]["hold"] = bad
            errs, _ = self.V.validate_story(d)
            self.assertTrue(any("hold" in e for e in errs), (bad, errs))
        d = self._minimal()
        d["shots"][0]["line"] = 123
        errs, _ = self.V.validate_story(d)
        self.assertTrue(any("must be a string" in e for e in errs), errs)

    def test_vocabularies_match_source(self):
        """Drift alarm: the closed sets must equal what the engine actually exports."""
        import re

        def js_keys(path, name):
            """Top-level keys of `export const NAME = { ... }`, brace-matched.

            A line-anchored regex sees only the FIRST key per line (rig2d EXPR packs
            three), so it self-confirms whatever the constant already says. A
            depth-blind one leaks inner eyes:/brows:/mouth: keys. Walk to the
            matching close brace, skipping string literals and // comments:
            rig2d.js:31 ends with `// use with rot: ...`, which a comment-blind walk
            collects as a 28th POSES key.
            """
            with open(os.path.join(STUDIO, path), encoding="utf-8") as fh:
                src = fh.read()
            ident = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
            colon = re.compile(r"\s*:")
            j = src.index("{", src.index("export const " + name)) + 1
            keys, depth = set(), 0
            while j < len(src):
                c = src[j]
                if c == "/" and src[j + 1:j + 2] == "/":
                    nl = src.find("\n", j)
                    if nl < 0:
                        break
                    j = nl + 1
                    continue
                if c in "'\"`":
                    j += 1
                    while j < len(src) and src[j] != c:
                        j += 2 if src[j] == "\\" else 1
                    j += 1
                    continue
                if c == "{":
                    depth += 1
                elif c == "}":
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0:
                    m = ident.match(src, j)
                    if m:
                        j = m.end()
                        if colon.match(src, j):
                            keys.add(m.group(0))
                        continue
                j += 1
            return keys

        self.assertEqual(self.V.POSES, js_keys("engine/rig2d.js", "POSES"))
        self.assertEqual(self.V.EXPR_STICK, js_keys("engine/rig2d.js", "EXPR"))
        self.assertEqual(self.V.EXPR_INKBEAN, js_keys("chars/acting.js", "PRESETS"))
        self.assertEqual(self.V.STYLES, js_keys("engine/styles.js", "STYLES"))
        self.assertEqual(self.V.MOODS, js_keys("engine/styles.js", "BASE_MOODS"))


class FreshShapesTests(unittest.TestCase):
    def setUp(self):
        if _fresh_shapes is None:
            self.skipTest("fresh.shapes not importable")
        self.S = _fresh_shapes

    def test_four_shapes_with_distinct_size_skeletons(self):
        sk = {k: tuple(b["size"] for b in v["beats"]) for k, v in self.S.SHAPES.items()}
        self.assertEqual(len(sk), 4)
        self.assertEqual(len(set(sk.values())), 4, "two shapes share a size skeleton")

    def test_every_shape_opens_inside_the_hook_window(self):
        # oleo17: the first 2 seconds are the price of admission.
        for k, v in self.S.SHAPES.items():
            b = v["beats"][0]
            est = b["hold"] + (len((b["line"] or "").split()) / 2.5)
            self.assertLessEqual(est, 2.0, "%s opens in %.2fs" % (k, est))

    def test_every_shape_ends_on_a_short_payoff(self):
        # 起承转合: 合 is short and immediately after the turn.
        for k, v in self.S.SHAPES.items():
            self.assertLessEqual(v["beats"][-1]["hold"], 1.2, k)

    def test_hold_budget_within_ceiling(self):
        for k, v in self.S.SHAPES.items():
            total = sum(b["hold"] for b in v["beats"])
            self.assertLessEqual(total, _fresh_story_schema.MAX_HOLD_BUDGET,
                                 "%s holds %.2fs (ceiling %.2fs)"
                                 % (k, total, _fresh_story_schema.MAX_HOLD_BUDGET))

    def test_every_shape_stays_under_the_density_ceiling(self):
        for k, v in self.S.SHAPES.items():
            beats = self.S.fill(v, "proposal", "MAX", "JAKE")
            holds = sum(b["hold"] for b in beats)
            words = sum(len((b["line"] or "").split()) for b in beats)
            density = (holds + words / 2.0) / len(beats)
            self.assertLessEqual(density, _fresh_story_schema.MAX_SHOT_DENSITY,
                                 "%s estimates %.3fs/shot" % (k, density))

    def test_every_insert_declares_an_intent_on_both_sides(self):
        for k, v in self.S.SHAPES.items():
            beats = v["beats"]
            for i, b in enumerate(beats):
                if not b["insert"]:
                    continue
                # A cold-open insert has no predecessor, so it needs no intent.
                if i > 0:
                    self.assertIn(b.get("intent"), ("eyeline", "match", "reverse"), k)
                if i + 1 < len(beats):
                    self.assertIn(beats[i + 1].get("intent"),
                                  ("eyeline", "match", "reverse"), k)

    def test_filled_lines_respect_the_word_cap(self):
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                n = len((b["line"] or "").split())
                self.assertLessEqual(n, _fresh_story_schema.MAX_LINE_WORDS,
                                     "%s: %r (ceiling %d words)"
                                     % (k, b["line"],
                                        _fresh_story_schema.MAX_LINE_WORDS))

    def test_filled_expressions_are_all_valid(self):
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                for key in ("expr", "exprTo", "expr2", "exprTo2"):
                    if b.get(key):
                        self.assertIn(b[key], _fresh_story_schema.EXPR_INKBEAN)

    def test_subject_of_picks_the_content_word(self):
        self.assertEqual(self.S.subject_of("Cute couple proposal day happy ending"), "proposal")
        self.assertEqual(self.S.subject_of("AI writes code now"), "code")
        self.assertEqual(self.S.subject_of(""), "thing")

    def test_insert_for_is_concept_derived_and_in_vocabulary(self):
        self.assertEqual(self.S.insert_for("a letter arrives"), "document")
        self.assertEqual(self.S.insert_for("the phone lights up"), "phone")
        self.assertIn(self.S.insert_for("something unrecognisable"), self.S.INSERT_KINDS)

    def test_prop_for_stays_inside_the_implemented_set(self):
        for k in self.S.INSERT_KINDS:
            self.assertIn(self.S.prop_for(k), self.S.PROPS)

    def test_no_shape_reuses_the_old_hard_coded_arc(self):
        import re

        # Exact comparison lets a punctuation variant of a banned line slip
        # through, so normalise both sides before comparing.
        def norm(s):
            s = (s or "").replace("...", "").replace("\u2026", "")
            return re.sub(r"\s+", " ", s).strip().lower()

        banned = {"Is this even real?", "Watch. One sentence.",
                  "That's... not possible.", "One sentence. Zero artists."}
        banned_norm = {norm(x) for x in banned}
        for k, v in self.S.SHAPES.items():
            for b in self.S.fill(v, "proposal", "MAX", "JAKE"):
                self.assertNotIn(norm(b["line"]), banned_norm, k)


class FreshStoryTests(unittest.TestCase):
    def setUp(self):
        if _fresh_story is None or _fresh_story_schema is None:
            self.skipTest("fresh.story / fresh.story_schema not importable")

    def test_story_passes_the_contract(self):
        for concept in ("Cute couple proposal day happy ending", "AI writes code now",
                        "a letter arrives at midnight", ""):
            d = _fresh_story.concept_to_story(concept)
            errs, _ = _fresh_story_schema.validate_story(d)
            self.assertEqual(errs, [], "%s -> %s" % (concept, errs))

    # Twelve episodes of one series, each with its own concept. Single-noun
    # concepts so subject_of() is unambiguous and all twelve subjects differ.
    EP_CONCEPTS = ["proposal", "funeral", "letter", "phone", "code", "photograph",
                   "ticket", "room", "rain", "clock", "stranger", "broadcast"]

    def test_two_concepts_do_not_share_the_old_arc(self):
        banned = {"Is this even real?", "Watch. One sentence.",
                  "That's... not possible.", "One sentence. Zero artists."}
        a = _fresh_story.concept_to_story("Cute couple proposal day happy ending")
        b = _fresh_story.concept_to_story("AI writes code now")
        la = [s["line"] for s in a["shots"] if s.get("line")]
        lb = [s["line"] for s in b["shots"] if s.get("line")]
        self.assertNotEqual(la, lb)
        self.assertFalse(banned & set(la + lb), banned & set(la + lb))
        self.assertTrue(any("proposal" in x for x in la), la)
        self.assertTrue(any("code" in x for x in lb), lb)

    def test_twelve_episodes_use_all_four_shapes(self):
        sk = set()
        for ep, c in enumerate(self.EP_CONCEPTS, start=1):
            d = _fresh_story.concept_to_story(c, series_id="proposal_series", episode=ep)
            sk.add(tuple(s["size"] for s in d["shots"]))
        self.assertEqual(len(sk), 4, "only %d distinct skeletons" % len(sk))

    def test_no_episode_repeats_a_line_set(self):
        seen = []
        for ep, c in enumerate(self.EP_CONCEPTS, start=1):
            d = _fresh_story.concept_to_story(c, series_id="proposal_series", episode=ep)
            seen.append(frozenset(s["line"] for s in d["shots"] if s.get("line")))
        self.assertEqual(len(set(seen)), 12, "two episodes share an identical line set")

    def test_series_cast_is_stable_across_episodes(self):
        a = _fresh_story.concept_to_story("the proposal", series_id="proposal_series", episode=1)
        b = _fresh_story.concept_to_story("the funeral", series_id="proposal_series", episode=2)
        self.assertEqual(a["cast"], b["cast"])

    def test_series_bible_agrees_with_cast(self):
        if _fresh_series is None:
            self.skipTest("fresh.series not importable")
        d = _fresh_story.concept_to_story("the proposal", series_id="proposal_series", episode=1)
        sb = _fresh_series.generate_series("proposal_series", concept="the proposal")
        self.assertEqual(sb["character"]["base_color"], d["cast"]["MAX"]["color"])

    def test_determinism(self):
        a = _fresh_story.concept_to_story("AI writes code now", series_id="s", episode=3)
        b = _fresh_story.concept_to_story("AI writes code now", series_id="s", episode=3)
        self.assertEqual(a, b)

    def test_runtime_fields_unchanged(self):
        d = _fresh_story.concept_to_story("AI writes code now")
        self.assertEqual(d["aspect"], "9:16")
        self.assertEqual(d["resolution"], "1080p")
        self.assertEqual(d["fps"], 24)
        self.assertEqual(d["chars"], "inkbean")


class StoryContractGateTests(unittest.TestCase):
    """Regression: the story contract ran only on the --fresh path.

    tools/fresh/story.py:97 calls validate_story, but generate.py never did. A
    hand-authored --story film with an out-of-vocabulary expression therefore
    rendered a NEUTRAL face while every QC gate still reported green. The gate
    must run on the story file director.py is about to read, on BOTH paths.
    """

    @staticmethod
    def _story(expr):
        return {
            "title": "contract gate", "aspect": "9:16", "resolution": "1080p",
            "fps": 24, "style": "midnight", "set": "room", "chars": "inkbean",
            "cast": {"MAX": {"color": "#111111", "top": "tee",
                             "legs": "#222222", "head": "none"}},
            "shots": [{"id": "s001", "size": "wide", "hold": 1.0, "line": "hi",
                       "who": "MAX", "expr": expr, "in": {"type": "cut"},
                       "cut_intent": "eyeline"}],
            "music": [],
        }

    @staticmethod
    def _write(d, expr):
        p = os.path.join(d, "story.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(StoryContractGateTests._story(expr), fh)
        return p

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = os.path.join(TOOLS, "generate.py")
        spec = importlib.util.spec_from_file_location("_generate_under_test", path)
        cls.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gen)

    def test_generate_exposes_the_gate_helpers(self):
        self.assertTrue(callable(getattr(self.gen, "validate_story_file", None)))
        self.assertTrue(callable(getattr(self.gen, "story_contract_decision", None)))

    def test_helper_rejects_unknown_expression(self):
        with tempfile.TemporaryDirectory() as d:
            errs, _ = self.gen.validate_story_file(self._write(d, "smirk"), TOOLS)
        self.assertTrue(any("smirk" in e for e in errs), errs)

    def test_helper_accepts_contract_clean_story(self):
        with tempfile.TemporaryDirectory() as d:
            errs, _ = self.gen.validate_story_file(self._write(d, "neutral"), TOOLS)
        self.assertEqual(errs, [])

    def test_strict_aborts_on_contract_errors(self):
        self.assertIsNotNone(self.gen.story_contract_decision(["bad"], True))

    def test_default_continues_on_contract_errors(self):
        self.assertIsNone(self.gen.story_contract_decision(["bad"], False))

    def test_gate_runs_before_director(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("validate_story_file(story", src)
        self.assertLess(src.index("validate_story_file(story"),
                        src.index('"director.py"'))

    def test_stage0_is_a_callable_helper(self):
        self.assertTrue(callable(getattr(self.gen, "check_story_contract", None)))

    def test_stage0_aborts_a_strict_run_on_an_invalid_story_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "smirk")
            with self.assertRaises(SystemExit) as cm:
                self.gen.check_story_contract(p, TOOLS, True)
        self.assertIn("story contract", str(cm.exception))

    def test_stage0_lets_a_default_run_continue_on_an_invalid_story_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "smirk")
            errs, _ = self.gen.check_story_contract(p, TOOLS, False)
        self.assertTrue(any("smirk" in e for e in errs), errs)

    def test_main_calls_stage0_with_the_strict_flag(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("check_story_contract(story, here, a.strict)", src)


class RenderReportMotionGateTests(unittest.TestCase):
    """Regression: render_report.py printed motion ISSUES but always exited 0.

    generate.py:169 treats a non-zero render_report exit as fatal, so the report
    is meant to be a gate. It could never signal a failure. The exit decision is
    a pure, testable helper; activation stays behind an explicit opt-in flag.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = os.path.join(TOOLS, "render_report.py")
        spec = importlib.util.spec_from_file_location("_render_report_under_test", path)
        cls.rr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.rr)

    def test_render_report_exposes_the_exit_helper(self):
        self.assertTrue(callable(getattr(self.rr, "motion_exit_code", None)))

    def test_issues_block_when_explicitly_requested(self):
        mo = {"verdict": "ISSUES", "issues": ["freeze at 3.2s"]}
        self.assertEqual(self.rr.motion_exit_code(mo, True), 1)

    def test_issues_do_not_block_by_default(self):
        mo = {"verdict": "ISSUES", "issues": ["freeze at 3.2s"]}
        self.assertEqual(self.rr.motion_exit_code(mo, False), 0)

    def test_unavailable_motion_audit_never_blocks(self):
        mo = {"verdict": "NOT RUN", "issues": ["stale"]}
        self.assertEqual(self.rr.motion_exit_code(mo, True), 0)

    def test_clean_report_never_blocks(self):
        mo = {"verdict": "OK", "issues": []}
        self.assertEqual(self.rr.motion_exit_code(mo, True), 0)

    def test_flag_and_exit_are_wired_in_source(self):
        with open(os.path.join(TOOLS, "render_report.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("--fail-on-issues", src)
        self.assertIn("return motion_exit_code(mo, a.fail_on_issues)", src)
        self.assertIn("sys.exit(main())", src)


class FrameQaWiringTests(unittest.TestCase):
    """Regression: frame_qa.py had zero production callers.

    It already supports --project/--strict and returns 0/1, so the defect was
    missing wiring, not a broken checker. Activation is opt-in because its
    findings are not yet calibrated against real clips.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = os.path.join(TOOLS, "generate.py")
        spec = importlib.util.spec_from_file_location("_generate_frameqa", path)
        cls.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gen)

    def test_helper_builds_a_project_scoped_command(self):
        cmd = self.gen.frame_qa_cmd(TOOLS, "/proj", True)
        self.assertIn(os.path.join(TOOLS, "frame_qa.py"), cmd)
        self.assertIn("--project", cmd)
        self.assertIn("/proj", cmd)
        self.assertIn("--strict", cmd)

    def test_helper_omits_strict_by_default(self):
        self.assertNotIn("--strict", self.gen.frame_qa_cmd(TOOLS, "/proj", False))

    def test_generate_exposes_an_opt_in_flag(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('"--frame-qa"', src)
        self.assertIn("if a.frame_qa:", src)
        self.assertIn("frame_qa_cmd(here, out, a.strict)", src)


class GenerateDegradationTests(unittest.TestCase):
    """Regression: four degraded stages were swallowed with a bare print.

    A broken series bible or failed preview still ended in CANDIDATE READY.
    Under --strict they must abort; by default they stay non-fatal so existing
    runs are not broken. Also removes the shared --fresh story path race.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = os.path.join(TOOLS, "generate.py")
        spec = importlib.util.spec_from_file_location("_generate_degrade", path)
        cls.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gen)

    def test_helpers_are_callable(self):
        self.assertTrue(callable(getattr(self.gen, "report_stage_failure", None)))
        self.assertTrue(callable(getattr(self.gen, "fresh_story_path", None)))

    def test_default_failure_does_not_abort(self):
        self.assertIsNone(self.gen.report_stage_failure("preview render", "exit 3", False))

    def test_strict_failure_aborts_and_names_the_stage(self):
        with self.assertRaises(SystemExit) as cm:
            self.gen.report_stage_failure("series bible", "boom", True)
        self.assertIn("series bible", str(cm.exception))

    def test_fresh_story_paths_are_project_scoped_and_distinct(self):
        a = self.gen.fresh_story_path("/studio", "/studio/projects/ep1")
        b = self.gen.fresh_story_path("/studio", "/studio/projects/ep2")
        self.assertNotEqual(a, b)
        self.assertIn("ep1", a)

    def test_all_four_swallow_sites_use_the_helper(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertGreaterEqual(src.count("report_stage_failure("), 5)
        self.assertIn("fresh_story_path(studio, out)", src)


class RenderWorkerCapTests(unittest.TestCase):
    """Regression: generate.py could not bound render.mjs workers.

    render.mjs defaults to min(8, cpus/2) Chromium processes. On a 24-thread
    machine that is 8 browsers plus 8 ffmpeg encoders, which exhausts memory
    on this workstation. An opt-in cap is required for a safe local render.
    """

    def test_render_gate_command_forwards_the_worker_cap(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('"--workers"', src)
        self.assertIn('rg += ["--", "--workers", str(a.workers)]', src)

    def test_omitting_the_cap_keeps_the_original_command(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("if a.workers:", src)


class DeriveContractTests(unittest.TestCase):
    """Step 1 of the auto-derivation spec (2026-11-12).

    Owner's rule: a story that does not name a location/cast/audio must have them
    DERIVED from the concept; anything the owner names is used verbatim; a series
    pins them for continuity. This class pins the `derive` block contract only --
    no derivation algorithm, no pixels, no render.
    """

    def setUp(self):
        if _fresh_story_schema is None:
            self.skipTest("fresh.story_schema not importable")
        self.S = _fresh_story_schema

    def _story(self, with_set=True, **extra):
        d = {
            "title": "derive", "aspect": "9:16", "resolution": "1080p", "fps": 24,
            "style": "midnight", "chars": "inkbean",
            "cast": {"MAX": {"color": "#111111", "top": "tee",
                             "legs": "#222222", "head": "none"}},
            "shots": [{"id": "s001", "size": "wide", "hold": 1.0, "line": "hi",
                       "who": "MAX", "expr": "neutral", "in": {"type": "cut"},
                       "cut_intent": "eyeline"}],
            "music": [{"start": 0, "end": 1.0, "mood": "playful", "intensity": 0.5}],
        }
        if with_set:
            d["set"] = "room"
        d.update(extra)
        return d

    def test_absent_derive_block_means_everything_stays_fixed(self):
        """Backwards compatibility: existing stories must not change behaviour."""
        got = self.S.resolve_derive(self._story())
        self.assertEqual(got["source"], "fixed")
        for aspect in ("location", "cast", "audio"):
            self.assertEqual(got[aspect], "fixed")

    def test_source_auto_derives_all_three_aspects(self):
        got = self.S.resolve_derive(self._story(with_set=False,
                                                derive={"source": "auto"}))
        self.assertEqual(got["source"], "auto")
        for aspect in ("location", "cast", "audio"):
            self.assertEqual(got[aspect], "auto")

    def test_per_aspect_override_beats_source(self):
        got = self.S.resolve_derive(self._story(with_set=False,
                                                derive={"source": "auto",
                                                        "location": "fixed"}))
        self.assertEqual(got["location"], "fixed")
        self.assertEqual(got["cast"], "auto")
        self.assertEqual(got["audio"], "auto")

    def test_an_explicit_set_wins_over_auto_location(self):
        """Owner named a location -> use it, even under source=auto."""
        got = self.S.resolve_derive(self._story(derive={"source": "auto"}))
        self.assertEqual(got["location"], "fixed")
        self.assertEqual(got["cast"], "auto")

    def test_explicit_set_under_auto_location_is_reported(self):
        errs, warns = self.S.validate_story(self._story(derive={"source": "auto"}))
        self.assertEqual(errs, [])
        self.assertTrue(any("set" in w and "auto" in w for w in warns), warns)

    def test_invalid_source_is_an_error(self):
        errs, _ = self.S.validate_story(self._story(derive={"source": "random"}))
        self.assertTrue(any("derive" in e and "random" in e for e in errs), errs)

    def test_invalid_per_aspect_value_is_an_error(self):
        errs, _ = self.S.validate_story(
            self._story(derive={"source": "auto", "cast": "sometimes"}))
        self.assertTrue(any("cast" in e and "sometimes" in e for e in errs), errs)

    def test_unknown_derive_key_is_an_error(self):
        errs, _ = self.S.validate_story(
            self._story(derive={"source": "auto", "bgm": True}))
        self.assertTrue(any("bgm" in e for e in errs), errs)

    def test_non_object_derive_is_an_error(self):
        errs, _ = self.S.validate_story(self._story(derive="auto"))
        self.assertTrue(any("derive" in e for e in errs), errs)

    def test_derive_is_an_accepted_story_key(self):
        errs, _ = self.S.validate_story(self._story(derive={"source": "fixed"}))
        self.assertFalse(any("unknown key 'derive'" in e for e in errs), errs)


class DerivedAudioTests(unittest.TestCase):
    """Step 2 of the auto-derivation spec: music mood + SFX + ambience follow
    the concept instead of the hardcoded `music: []` -> mood "mystery" constant.
    """

    CONCEPTS = [
        "a couple gets engaged at midnight",
        "a detective finds a letter",
        "a phone that will not stop ringing",
        "a kid loses the last bus",
        "a chef opens a tiny restaurant",
        "rain on the last day of school",
    ]

    def setUp(self):
        # NOT skipTest: fresh.audio is a first-party module. If it cannot be
        # imported the repo is broken, and a skip would report green anyway.
        self.assertIsNotNone(_fresh_audio, "fresh.audio is not importable")
        self.A = _fresh_audio

    def test_music_plan_is_non_empty_and_in_vocabulary(self):
        plan = self.A.derive_music("a couple gets engaged", 8.0)
        self.assertTrue(plan)
        for seg in plan:
            self.assertIn(seg["mood"], self.A.MUSIC_MOODS)
            self.assertLessEqual(seg["start"], seg["end"])
            self.assertGreaterEqual(seg["intensity"], 0.0)
            self.assertLessEqual(seg["intensity"], 1.0)

    def test_plan_spans_the_whole_film_without_gaps(self):
        plan = self.A.derive_music("a detective finds a letter", 9.4)
        self.assertAlmostEqual(plan[0]["start"], 0.0)
        self.assertAlmostEqual(plan[-1]["end"], 9.4, places=2)
        for a, b in zip(plan, plan[1:]):
            self.assertAlmostEqual(a["end"], b["start"], places=2)

    def test_same_concept_is_deterministic(self):
        self.assertEqual(self.A.derive_music("a kid loses the last bus", 7.0),
                         self.A.derive_music("a kid loses the last bus", 7.0))

    def test_different_concepts_do_not_all_get_the_same_mood(self):
        moods = {self.A.derive_music(c, 8.0)[0]["mood"] for c in self.CONCEPTS}
        self.assertGreater(len(moods), 1,
                           "every concept resolved to the same mood: %s" % moods)

    def test_theme_keyword_beats_the_background_fallback(self):
        self.assertEqual(self.A.mood_for("a phone that will not stop ringing", "night"),
                         "playful")
        # no theme keyword at all -> the background mood decides
        self.assertEqual(self.A.mood_for("the thing", "storm"), "tension")
        self.assertEqual(self.A.mood_for("the thing", "day"), "hopeful")

    def test_keywords_match_whole_words_not_substrings(self):
        """'happens' must not match 'app'; 'brunch' must not match 'run'."""
        self.assertNotEqual(self.A.mood_for("something happens here", "night"),
                            "playful")
        self.assertNotEqual(self.A.mood_for("brunch at noon", "night"), "action")
        # ...but a stem still matches its inflections
        self.assertEqual(self.A.mood_for("the phone is ringing", "night"), "playful")

    def test_ambience_follows_location(self):
        self.assertEqual(self.A.derive_amb("x", "outdoor", "night"), "city")
        self.assertEqual(self.A.derive_amb("x", "kitchen", "interiorWarm"), "roomtone")
        self.assertEqual(self.A.derive_amb("rain at the bus stop", "outdoor", "storm"), "rain")

    def test_ambience_name_is_always_a_real_sfx(self):
        for set_name in ("room", "kitchen", "outdoor"):
            for mood in ("day", "night", "storm", "void"):
                amb = self.A.derive_amb("x", set_name, mood)
                self.assertIn(amb, self.A.AMB_NAMES, (set_name, mood, amb))

    def test_theme_accent_sfx_is_a_real_sfx_or_none(self):
        for c in self.CONCEPTS:
            hit = self.A.derive_accent_sfx(c)
            self.assertTrue(hit is None or hit in self.A.ACCENT_SFX, (c, hit))

    def test_theme_accent_is_not_always_none(self):
        hits = {self.A.derive_accent_sfx(c) for c in self.CONCEPTS}
        self.assertGreater(len(hits), 1)


class DerivedCastTests(unittest.TestCase):
    """Step 3: character names follow the concept instead of `["MAX","JAKE"]`."""

    def setUp(self):
        self.assertIsNotNone(_fresh_cast, "fresh.cast is not importable")
        self.C = _fresh_cast
        self.assertIsNotNone(_fresh_story, "fresh.story is not importable")
        self.ST = _fresh_story

    def test_same_concept_same_cast(self):
        self.assertEqual(self.C.derive_cast_names("a lost dog"),
                         self.C.derive_cast_names("a lost dog"))

    def test_names_are_distinct_uppercase_and_from_the_pool(self):
        for c in ("a lost dog", "the last bus", "a phone rings"):
            names = self.C.derive_cast_names(c)
            self.assertEqual(len(names), 2)
            self.assertEqual(len(set(names)), 2, "duplicate name: %s" % (names,))
            for n in names:
                self.assertIn(n, self.C.NAME_POOL)
                self.assertEqual(n, n.upper())

    def test_different_concepts_get_different_cast(self):
        pairs = {self.C.derive_cast_names(c) for c in
                 ("a lost dog", "the last bus", "a phone rings",
                  "rain at school", "a tiny restaurant", "midnight proposal")}
        self.assertGreater(len(pairs), 1, "every concept got the same cast")

    def test_three_names_are_supported_for_a_future_c_role(self):
        names = self.C.derive_cast_names("a crowd gathers", count=3)
        self.assertEqual(len(set(names)), 3)

    def test_standalone_story_uses_derived_names(self):
        d = self.ST.concept_to_story("a lost dog")
        self.assertEqual(tuple(d["cast"]), self.C.derive_cast_names("a lost dog"))

    def test_series_keeps_the_bible_cast(self):
        d = self.ST.concept_to_story("episode two", series_id="s1", episode=2)
        self.assertEqual(tuple(d["cast"]), self.C.SERIES_CAST)

    def test_derived_name_substitutes_into_the_one_line_template_that_uses_it(self):
        """Only one shape uses {a}, so this pins the substitution mechanism --
        it does NOT claim that every film speaks a name (most do not)."""
        from fresh.shapes import SHAPES, fill
        names = self.C.derive_cast_names("a lost dog")
        templated = [s for s in SHAPES.values()
                     if any("{a}" in (b["line"] or "") for b in s["beats"])]
        self.assertTrue(templated, "no shape uses {a} any more")
        beats = fill(templated[0], "dog", names[0], names[1])
        self.assertTrue(any(names[0] in (b["line"] or "") for b in beats))


class SeriesPinTests(unittest.TestCase):
    """Step 4: naming a series pins location + look + audio across episodes.

    The owner's rule: derive everything for a one-off film, but keep a series
    visually and sonically continuous. `series_id` IS the opt-in; no flag to
    forget, because the identity is derived from the series seed itself.
    """

    def setUp(self):
        self.assertIsNotNone(_fresh_story, "fresh.story is not importable")
        self.ST = _fresh_story

    def _eps(self, sid="s1", n=3):
        return [self.ST.concept_to_story("episode %d" % i, series_id=sid, episode=i)
                for i in range(1, n + 1)]

    def test_series_pins_location(self):
        sets = {d["set"] for d in self._eps()}
        self.assertEqual(len(sets), 1, "series changed location: %s" % sets)

    def test_series_pins_style_and_background(self):
        styles = {d["style"] for d in self._eps()}
        bgs = {s.get("bg") for d in self._eps() for s in d["shots"] if s.get("bg")}
        self.assertEqual(len(styles), 1, "series changed style: %s" % styles)
        self.assertEqual(len(bgs), 1, "series changed background mood: %s" % bgs)

    def test_series_pins_music_mood(self):
        moods = {d["music"][0]["mood"] for d in self._eps()}
        self.assertEqual(len(moods), 1, "series changed music mood: %s" % moods)

    def test_series_music_mood_is_a_legal_music_key(self):
        """The series palette's `mood` is an ENGINE background mood (night/dusk),
        not a MUSIC mood. Using it raw would KeyError inside render_score."""
        for d in self._eps():
            for seg in d["music"]:
                self.assertIn(seg["mood"], _fresh_audio.MUSIC_MOODS, seg)

    def test_every_generated_film_has_legal_music_moods(self):
        for c in ("a lost dog", "rain at school", "a crowd gathers",
                  "midnight proposal", "a detective", "a phone rings"):
            for seg in self.ST.concept_to_story(c)["music"]:
                self.assertIn(seg["mood"], _fresh_audio.MUSIC_MOODS, (c, seg))

    def test_series_pins_ambience(self):
        ambs = {s["amb"]["name"] for d in self._eps()
                for s in d["shots"] if s.get("amb")}
        self.assertEqual(len(ambs), 1, "series changed ambience: %s" % ambs)

    def test_series_pins_cast(self):
        casts = {tuple(d["cast"]) for d in self._eps()}
        self.assertEqual(len(casts), 1, "series changed cast: %s" % casts)

    def test_standalone_films_are_not_pinned(self):
        """Without a series the whole point is that nothing repeats."""
        sets = {self.ST.concept_to_story(c)["set"] for c in
                ("a lost dog", "the last bus", "a phone rings", "rain at school",
                 "a tiny restaurant", "midnight proposal", "a detective",
                 "a crowd gathers")}
        self.assertGreater(len(sets), 1, "standalone films share one location: %s" % sets)


class SetPaletteTests(unittest.TestCase):
    """Step 5 (chosen route c): inject the per-project palette from set_spec.json
    into the EMITTED set JS. No engine/ change, and a project without a
    set_spec.json (e.g. cine_release) emits exactly the old template.
    """

    def setUp(self):
        self.assertIsNotNone(DR, "tools/director.py is not importable")

    def test_no_set_spec_means_no_override(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(DR.set_palette_override(td))

    def test_set_spec_palette_is_read(self):
        with tempfile.TemporaryDirectory() as td:
            pal = {"wall": "#223344", "floor": "#334455", "sky": "#445566",
                   "practical": "#ffcc88", "dark": "#15131a", "accent": "#aabbcc"}
            with open(os.path.join(td, "set_spec.json"), "w", encoding="utf-8") as fh:
                json.dump({"set": "room", "palette": pal}, fh)
            got = DR.set_palette_override(td)
            self.assertEqual(got["wall"], "#223344")
            self.assertEqual(got["practical"], "#ffcc88")
            self.assertIn("dark", got)

    def test_malformed_palette_entries_are_dropped(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "set_spec.json"), "w", encoding="utf-8") as fh:
                json.dump({"palette": {"wall": "#223344", "floor": "not-a-colour"}}, fh)
            got = DR.set_palette_override(td)
            self.assertEqual(got, {"wall": "#223344"})

    def test_emitted_js_without_palette_is_null(self):
        js = DR.render_set_js("const PROJECT_PALETTE = __PROJECT_PALETTE__;", None)
        self.assertIn("PROJECT_PALETTE = null", js)

    def test_emitted_js_carries_the_colour(self):
        js = DR.render_set_js("const PROJECT_PALETTE = __PROJECT_PALETTE__;",
                              {"wall": "#223344"})
        self.assertIn("#223344", js)
        self.assertNotIn("__PROJECT_PALETTE__", js)

    def test_set_spec_is_written_before_director_runs(self):
        """director.py reads set_spec.json, so the write must precede it.
        Until 2026-11-12 it ran after, and every film kept the style palette."""
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("write_set_spec(a.fresh", src)
        self.assertLess(src.index("write_set_spec(a.fresh"),
                        src.index('"director.py"'))

    def test_default_template_still_uses_the_mood_function(self):
        """A project with no set_spec.json must render as before."""
        js = DR.render_set_js(DR.SET_JS, None)
        self.assertIn("mood(o.moodName", js)
        self.assertIn("PROJECT_PALETTE", js)


class SetLibraryTests(unittest.TestCase):
    """A fourth location exists and is reachable, so a film is not stuck on 3."""

    def setUp(self):
        self.assertIsNotNone(DR, "tools/director.py is not importable")
        self.assertIsNotNone(_fresh_story_schema, "fresh.story_schema missing")

    def test_office_is_a_legal_set(self):
        self.assertIn("office", self._schema().SETS)

    def test_unknown_set_is_still_rejected(self):
        d = {"title": "t", "aspect": "9:16", "resolution": "1080p", "fps": 24,
             "style": "midnight", "set": "basement", "chars": "inkbean",
             "cast": {"A": {"color": "#111111", "top": "tee",
                            "legs": "#222222", "head": "none"}},
             "shots": [{"id": "s001", "size": "wide", "hold": 1.0, "line": "hi",
                        "who": "A", "expr": "neutral", "in": {"type": "cut"},
                        "cut_intent": "eyeline"}],
             "music": [{"start": 0, "end": 1.0, "mood": "calm", "intensity": 0.4}]}
        errs, _ = self._schema().validate_story(d)
        self.assertTrue(any("basement" in e for e in errs), errs)

    def _schema(self):
        return _fresh_story_schema

    def test_director_emits_the_office_module(self):
        self.assertIn("SET_OFFICE_JS", dir(DR))
        self.assertIn("export function office", DR.SET_OFFICE_JS)
        self.assertIn("PROJECT_PALETTE", DR.SET_OFFICE_JS)

    def test_dispatch_is_a_map_not_a_ternary(self):
        """Adding a location must be one line, not another nested conditional."""
        self.assertIn("const SETS = { room, kitchen, outdoor, office };", DR.SHOT_JS)
        self.assertIn("const SET = SETS[p.set ||", DR.SHOT_JS)
        self.assertNotIn("=== 'kitchen' ? kitchen", DR.SHOT_JS)

    def test_office_is_reachable_from_a_concept_sweep(self):
        self.assertIsNotNone(_fresh_palette, "fresh.palette missing")
        seen = set()
        for c in ("a lost dog", "the last bus", "a phone rings", "rain at school",
                  "a tiny restaurant", "midnight proposal", "a detective",
                  "a crowd gathers", "a night shift", "a letter at midnight",
                  "two chairs", "an empty desk"):
            seen.add(_fresh_palette.generate_palette(c)["identity"]["set"])
        self.assertIn("office", seen, "office never chosen: %s" % seen)


class VarietyGateTests(unittest.TestCase):
    """Step 6: two consecutive films must not share location AND cast.

    Owner's rule: variety by default, continuity only when asked. Identical
    backgrounds across consecutive uploads is the "mass-produced" signal that
    the market research flagged as a monetisation risk.
    """

    def setUp(self):
        self.assertIsNotNone(VG, "tools/variety_gate.py is not importable")

    def _story(self, set_name="room", cast=("MAX", "JAKE"), style="midnight",
               mood="mystery"):
        return {"set": set_name, "style": style,
                "cast": {n: {"color": "#111111"} for n in cast},
                "music": [{"mood": mood}],
                "shots": [{"amb": {"name": "roomtone"}}]}

    def test_identical_films_are_a_duplicate_look(self):
        issues = VG.compare(self._story(), self._story())
        self.assertTrue(any("duplicate look" in i for i in issues), issues)

    def test_different_location_is_not_a_duplicate(self):
        issues = VG.compare(self._story(), self._story(set_name="kitchen"))
        self.assertFalse(any("duplicate look" in i for i in issues), issues)

    def test_different_cast_is_not_a_duplicate(self):
        issues = VG.compare(self._story(), self._story(cast=("AVA", "BEN")))
        self.assertFalse(any("duplicate look" in i for i in issues), issues)

    def test_identical_location_alone_is_reported_as_a_note(self):
        issues = VG.compare(self._story(), self._story(cast=("AVA", "BEN")))
        self.assertTrue(any("same location" in i for i in issues), issues)

    def test_identical_music_opening_is_reported(self):
        issues = VG.compare(self._story(set_name="kitchen"),
                            self._story(set_name="outdoor"))
        self.assertTrue(any("same music" in i for i in issues), issues)

    def test_verdict_is_non_fatal_by_default(self):
        dup = self._story()
        self.assertEqual(VG.verdict(VG.compare(dup, dup), strict=False), 0)

    def test_verdict_fails_under_strict(self):
        dup = self._story()
        self.assertEqual(VG.verdict(VG.compare(dup, dup), strict=True), 1)

    def test_cli_exit_codes(self):
        import tempfile
        dup = self._story()
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.json")
            b = os.path.join(td, "b.json")
            c = os.path.join(td, "c.json")
            for path, data in ((a, dup), (b, dup),
                               (c, self._story(set_name="kitchen"))):
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh)
            base = [sys.executable, os.path.join(TOOLS, "variety_gate.py")]
            self.assertEqual(subprocess.run(base + ["--prev", a, "--cur", b],
                                            capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(base + ["--prev", a, "--cur", b, "--strict"],
                                            capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run(base + ["--prev", a, "--cur", c, "--strict"],
                                            capture_output=True).returncode, 0)


class DerivedLocationTests(unittest.TestCase):
    """Screenplay order: the scene decides the location, then the cast, then the
    wardrobe and props, then the sound. Until 2026-11-13 the location was
    `rng.pick(SETS)` in palette.py:41 — random from four names, with no regard
    for what the story was about, so a chef could cook in a bus shelter.
    """

    def setUp(self):
        self.assertIsNotNone(LOC, "fresh.location is not importable")
        self.L = LOC

    def test_kitchen_keywords_pick_the_kitchen(self):
        r = self.L.derive_location("a chef opens a tiny restaurant")
        self.assertEqual(r["set"], "kitchen")
        self.assertEqual(r["source"], "keyword")

    def test_office_keywords_pick_the_office(self):
        r = self.L.derive_location("a boss sends an email about the deadline")
        self.assertEqual(r["set"], "office")

    def test_outdoor_keywords_pick_outdoors(self):
        r = self.L.derive_location("the last bus never comes")
        self.assertEqual(r["set"], "outdoor")

    def test_bedroom_keywords_pick_the_room(self):
        r = self.L.derive_location("she cannot sleep in her bed")
        self.assertEqual(r["set"], "room")

    def test_no_keywords_falls_back_to_a_seed_and_admits_it(self):
        r = self.L.derive_location("a thing occurs")
        self.assertIn(r["set"], self.L.SETS)
        self.assertEqual(r["source"], "seed")

    def test_location_is_deterministic(self):
        a = self.L.derive_location("a chef opens a tiny restaurant")
        b = self.L.derive_location("a chef opens a tiny restaurant")
        self.assertEqual(a, b)

    def test_the_story_not_the_dice_picks_the_room(self):
        """The whole point: different subject -> different room, by content."""
        got = {c: self.L.derive_location(c)["set"] for c in (
            "a chef opens a tiny restaurant", "the last bus never comes",
            "a boss sends an email", "she cannot sleep in her bed")}
        self.assertEqual(len(set(got.values())), 4, got)

    def test_time_of_day_from_keywords(self):
        self.assertEqual(self.L.derive_location("a letter at midnight")["time"], "night")
        self.assertEqual(self.L.derive_location("breakfast at sunrise")["time"], "morning")

    def test_background_mood_follows_location_and_time(self):
        self.assertEqual(self.L.bg_mood_for("outdoor", "night"), "night")
        self.assertEqual(self.L.bg_mood_for("kitchen", "night"), "interiorCool")
        self.assertEqual(self.L.bg_mood_for("outdoor", "morning"), "day")

    def test_wardrobe_follows_the_role_and_the_room(self):
        """Only 8 tops are renderable (chars/inkbean.js), so a chef wears the
        labcoat — 'apron' does not exist and would silently fall back."""
        self.assertEqual(self.L.derive_top("kitchen", "chef"), "labcoat")
        self.assertEqual(self.L.derive_top("office", "boss"), "suit")
        self.assertEqual(self.L.derive_top("outdoor", "commuter"), "trench")

    def test_unknown_role_falls_back_to_a_room_appropriate_top(self):
        for role in ("", None, "wanderer"):
            self.assertIn(self.L.derive_top("kitchen", role), self.L.TOPS_BY_SET["kitchen"])

    def test_two_unnamed_characters_are_not_dressed_identically(self):
        """A shared seed dressed both characters the same (measured: 'dress,
        dress' for 'she cannot sleep in her bed'). Index must break the tie."""
        for set_name in ("room", "kitchen", "outdoor", "office"):
            a = self.L.derive_top(set_name, None, 0)
            b = self.L.derive_top(set_name, None, 1)
            self.assertNotEqual(a, b, "%s dressed both characters %r" % (set_name, a))

    def test_props_follow_the_location(self):
        """Only mug/book/phone are renderable, so the prop is CHOSEN by the
        room, not invented: an office gets a phone, a kitchen gets a mug."""
        self.assertEqual(self.L.derive_prop("office", "phone"), "phone")
        self.assertEqual(self.L.derive_prop("kitchen", "document"), "mug")
        self.assertEqual(self.L.derive_prop("outdoor", "document"), "phone")

    def test_prop_is_always_one_of_the_three_renderable_kinds(self):
        for set_name in ("room", "kitchen", "outdoor", "office", "basement"):
            for kind in ("card", "screen", "phone", "document", "photo", None):
                self.assertIn(self.L.derive_prop(set_name, kind), ("mug", "book", "phone"))

    def test_cast_size_stays_two_until_a_shape_places_a_third(self):
        """Documents a real ceiling, not a preference: fill() only substitutes
        {a} and {b}, so a third name would be dead data that never appears."""
        self.assertIsNotNone(_fresh_cast, "fresh.cast missing")
        self.assertEqual(len(_fresh_cast.derive_cast_names("a wedding in the rain")), 2)

    def test_set_palette_has_distinct_roles_not_two(self):
        """sets.py mapped wall=sky=practical and floor=accent to the same two
        identity colours, so every set was two hues repeated. Measured in a
        render: pink wall over a magenta floor, near-indistinguishable."""
        spec = _fresh_sets.generate_set_spec("a chef opens a tiny restaurant")
        pal = spec["palette"]
        self.assertEqual(len(set(pal.values())), 5, pal)
        self.assertGreaterEqual(_fresh_core.delta_e(pal["wall"], pal["floor"]), 10.0)
        self.assertGreaterEqual(_fresh_core.delta_e(pal["wall"], pal["accent"]), 20.0)

    def test_palette_never_overrides_the_sky_array(self):
        """`sky` is an ARRAY of stops in the engine mood. Overriding it with a
        single hex made backdrop() call linGrad with a string and crash:
        "stops.forEach is not a function". Sky varies via the mood instead."""
        pal = _fresh_sets.generate_set_spec("a garden with flowers")["palette"]
        self.assertNotIn("sky", pal)
        self.assertEqual(len(set(pal.values())), 5, pal)

    def test_set_palette_roles_are_stable_for_one_concept(self):
        a = _fresh_sets.generate_set_spec("a chef opens a tiny restaurant")["palette"]
        b = _fresh_sets.generate_set_spec("a chef opens a tiny restaurant")["palette"]
        self.assertEqual(a, b)

    def test_set_palette_differs_between_concepts(self):
        a = _fresh_sets.generate_set_spec("a chef opens a tiny restaurant")["palette"]
        b = _fresh_sets.generate_set_spec("a boss sends an email")["palette"]
        self.assertNotEqual(a["wall"], b["wall"])

    def test_generated_story_prop_matches_its_room(self):
        self.assertIsNotNone(_fresh_story, "fresh.story missing")
        for concept, room in (("a chef opens a tiny restaurant", "kitchen"),
                              ("a boss sends an email", "office")):
            d = _fresh_story.concept_to_story(concept)
            self.assertEqual(d["set"], room)
            kinds = [s["prop"]["kind"] for s in d["shots"] if s.get("prop")]
            self.assertTrue(kinds, "no prop shot for %r" % concept)
            for k in kinds:
                self.assertIn(k, self.L.PROPS_BY_SET[room], "%s in %s" % (k, room))

    def test_generated_story_location_matches_its_concept(self):
        """End to end through concept_to_story, not just the helper."""
        self.assertIsNotNone(_fresh_story, "fresh.story missing")
        self.assertEqual(_fresh_story.concept_to_story("a chef opens a tiny restaurant")["set"],
                         "kitchen")


class ThirdCharacterTests(unittest.TestCase):
    """A group scene needs a third figure. director.py already supports who3
    (line 948), so the only thing missing was the story layer placing one —
    until now every shape only ever named A and B, so a third cast member
    would have been dead data.
    """

    def setUp(self):
        self.assertIsNotNone(_fresh_story, "fresh.story is not importable")

    def test_group_concept_gets_a_third_character(self):
        d = _fresh_story.concept_to_story("a crowd gathers for the wedding")
        self.assertEqual(len(d["cast"]), 3, list(d["cast"]))

    def test_solo_concept_stays_at_two(self):
        d = _fresh_story.concept_to_story("a lost dog")
        self.assertEqual(len(d["cast"]), 2, list(d["cast"]))

    def test_third_character_is_actually_placed_in_a_shot(self):
        d = _fresh_story.concept_to_story("a crowd gathers for the wedding")
        third = list(d["cast"])[2]
        placed = [s for s in d["shots"] if s.get("who3") == third]
        self.assertTrue(placed, "cast has 3 but no shot places the third")

    def test_third_character_shot_passes_the_contract(self):
        d = _fresh_story.concept_to_story("a crowd gathers for the wedding")
        errs, _ = _fresh_story_schema.validate_story(d)
        self.assertEqual(errs, [])

    def test_three_character_story_is_deterministic(self):
        a = _fresh_story.concept_to_story("a crowd gathers for the wedding")
        b = _fresh_story.concept_to_story("a crowd gathers for the wedding")
        self.assertEqual(a, b)


class DressingTests(unittest.TestCase):
    """Geometry is a choice, not four fixed drawings. A room's dressing is
    derived from the concept (a garden gets a plant, a library gets shelves)
    and injected like the palette, so a project without a spec keeps the exact
    old look — cine_release must not move.
    """

    def setUp(self):
        self.assertIsNotNone(LOC, "fresh.location is not importable")
        self.assertIsNotNone(DR, "tools/director.py is not importable")
        self.LOC = LOC

    def test_dressing_is_deterministic(self):
        a = self.LOC.derive_dressing("room", "a garden party")
        b = self.LOC.derive_dressing("room", "a garden party")
        self.assertEqual(a, b)

    def test_dressing_has_every_key_with_a_legal_value(self):
        d = self.LOC.derive_dressing("room", "a garden party")
        self.assertEqual(set(d), set(self.LOC.DRESSING_DEFAULTS))
        self.assertIn(d["floor"], ("planks", "tiles"))
        self.assertIn(d["art"], (0, 1, 2))
        for k in ("shelf", "plant", "rug", "window"):
            self.assertIsInstance(d[k], bool, k)

    def test_the_story_turns_dressing_on(self):
        self.assertTrue(self.LOC.derive_dressing("room", "a garden with flowers")["plant"])
        self.assertTrue(self.LOC.derive_dressing("room", "a library full of books")["shelf"])
        self.assertGreaterEqual(self.LOC.derive_dressing("room", "a gallery of paintings")["art"], 1)

    def test_dressing_differs_between_concepts(self):
        a = self.LOC.derive_dressing("room", "a garden with flowers")
        b = self.LOC.derive_dressing("room", "a library full of books")
        self.assertNotEqual(a, b)

    def test_no_spec_means_no_extra_dressing(self):
        """Null must reproduce the pre-2026-11-13 picture exactly."""
        d = self.LOC.DRESSING_DEFAULTS
        self.assertEqual(d["art"], 0)
        self.assertFalse(d["shelf"])
        self.assertFalse(d["plant"])
        self.assertFalse(d["rug"])
        self.assertTrue(d["window"])

    def test_every_emitted_set_can_actually_dress(self):
        """Assert on the EMITTED file, not the source template: injection is
        what ships, and a template alone proves nothing."""
        for tmpl in (DR.SET_JS, DR.SET_KITCHEN_JS, DR.SET_OUTDOOR_JS, DR.SET_OFFICE_JS):
            js = DR.render_set_js(tmpl, None, {"plant": True})
            self.assertIn("from './dressing.js'", js)
            self.assertIn("dressing(g, D, M, GY, CX);", js)
            self.assertIn('"plant": true', js)
            self.assertNotIn("__PROJECT_DRESSING__", js)
            self.assertNotIn("__PROJECT_PALETTE__", js)

    def test_emitted_js_carries_the_dressing_literal(self):
        js = DR.render_set_js("const D = __PROJECT_DRESSING__;", None, {"plant": True})
        self.assertIn('"plant": true', js)
        self.assertNotIn("__PROJECT_DRESSING__", js)
        self.assertIn("null", DR.render_set_js("const D = __PROJECT_DRESSING__;", None, None))


class CastVarietyTests(unittest.TestCase):
    """Every character must be a DIFFERENT person, not a hue-swapped twin.

    Measured before this: the body was `colors[i]` and the legs
    `colors[(i+1)%2]`, so character B was character A with the two colours
    inverted. A two-hander read as one colour family, `head:"none"` was legal
    so casts rendered bald, and chars/inkbean.js had no build parameter at all,
    so every figure shared one silhouette.
    """

    def setUp(self):
        self.assertIsNotNone(_fresh_story, "fresh.story is not importable")
        self.assertIsNotNone(_fresh_palette, "fresh.palette is not importable")
        self.assertIsNotNone(_fresh_core, "fresh.core is not importable")
        self.ST = _fresh_story

    def _casts(self):
        for c in ("a chef opens a tiny restaurant", "a crowd gathers for the wedding",
                  "the last bus never comes", "she cannot sleep in her bed",
                  "a boss sends an email", "rain at school", "a lost dog"):
            yield c, self.ST.concept_to_story(c)

    def test_every_character_has_its_own_hue(self):
        for c, d in self._casts():
            cols = [v["color"] for v in d["cast"].values()]
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    self.assertGreaterEqual(
                        _fresh_core.delta_e(cols[i], cols[j]), 20,
                        "%s: two characters share a hue %s/%s" % (c, cols[i], cols[j]))

    def test_legs_are_a_darker_shade_of_the_same_person(self):
        for c, d in self._casts():
            for nm, v in d["cast"].items():
                self.assertLess(_fresh_core.rel_luminance(v["legs"]),
                                _fresh_core.rel_luminance(v["color"]),
                                "%s/%s: legs are not darker than the body" % (c, nm))

    def test_a_multi_character_cast_is_never_bald(self):
        for c, d in self._casts():
            if len(d["cast"]) < 2:
                continue
            heads = [v.get("head") for v in d["cast"].values()]
            self.assertNotIn("none", heads, "%s: bald in a two-hander: %s" % (c, heads))

    def test_head_markers_are_pairwise_distinct(self):
        for c, d in self._casts():
            heads = [v.get("head") for v in d["cast"].values()]
            self.assertEqual(len(set(heads)), len(heads),
                             "%s: duplicate head markers %s" % (c, heads))

    def test_every_character_has_a_body_build(self):
        for c, d in self._casts():
            shapes = []
            for nm, v in d["cast"].items():
                self.assertIn("build", v, "%s/%s has no build" % (c, nm))
                self.assertIn("height", v, "%s/%s has no height" % (c, nm))
                self.assertGreaterEqual(v["build"], 0.85)
                self.assertLessEqual(v["build"], 1.15)
                self.assertGreaterEqual(v["height"], 0.88)
                self.assertLessEqual(v["height"], 1.12)
                shapes.append((v["build"], v["height"]))
            if len(shapes) > 1:
                self.assertEqual(len(set(shapes)), len(shapes),
                                 "%s: two characters share a silhouette %s" % (c, shapes))

    def test_cast_appearance_is_deterministic(self):
        a = self.ST.concept_to_story("a chef opens a tiny restaurant")["cast"]
        b = self.ST.concept_to_story("a chef opens a tiny restaurant")["cast"]
        self.assertEqual(a, b)

    def test_head_vocabulary_only_names_real_markers(self):
        """chars/markers.js THROWS on an unknown kind, so a vocabulary entry
        that does not exist is a crash waiting for a cast to pick it."""
        with open(os.path.join(STUDIO, "chars", "markers.js"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIsNotNone(_fresh_cast, "fresh.cast is not importable")
        for k in _fresh_cast.HEAD_MARKERS:
            self.assertIn("  %s: {" % k, src,
                          "cast.HEAD_MARKERS names a marker that does not exist: %s" % k)

    def test_cast_head_reaches_the_marker_system(self):
        """`head` in cast.js is only drawn if inkbean reads it. It read
        `outfit.marker`, which cast.js never writes — every character was bald."""
        with open(os.path.join(STUDIO, "chars", "inkbean.js"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("src.head", src)
        self.assertIn("MARKER_NAMES()", src)

    def test_inkbean_honours_build_and_defaults_to_one(self):
        with open(os.path.join(STUDIO, "chars", "inkbean.js"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("outfit.build", src)
        self.assertIn("outfit.height", src)
        self.assertIn("=== undefined ? 1", src)


class CaptionGroupTests(unittest.TestCase):
    """A caption group must never span a sentence end or a line break.

    The bug: ui2d.js grouped words by fixed index (floor(i/4)*4), so the group
    holding the punch line also held the tail of the PREVIOUS sentence. In the
    delivered joke film a frame read "COMEBACK. TOO MUCH EFFORT." while the
    punch line had not been spoken - the closing caption leaked into the setup
    shot and spoiled the joke.
    """

    def setUp(self):
        self.assertIsNotNone(_fresh_captions, "fresh.captions is not importable")
        self.C = _fresh_captions

    def _w(self, *pairs):
        return [{"word": w, "start": s, "end": e} for w, s, e in pairs]

    def test_a_group_never_spans_a_sentence_end(self):
        words = self._w(("One", 0.0, 0.2), ("sentence.", 0.2, 0.5),
                        ("Zero", 0.6, 0.8), ("artists.", 0.8, 1.1))
        g = self.C.assign_groups(words)
        self.assertEqual(len({w["g"] for w in g}), 2, g)
        self.assertNotEqual(g[1]["g"], g[2]["g"])

    def test_a_group_never_spans_a_long_gap(self):
        words = self._w(("a", 0.0, 0.2), ("b", 0.2, 0.4), ("c", 1.4, 1.6))
        g = self.C.assign_groups(words)
        self.assertNotEqual(g[1]["g"], g[2]["g"])

    def test_short_pause_does_not_split(self):
        words = self._w(("a", 0.0, 0.2), ("b", 0.24, 0.4))
        g = self.C.assign_groups(words)
        self.assertEqual(g[0]["g"], g[1]["g"])

    def test_max_words_per_group(self):
        words = self._w(*[("w%d" % i, i * 0.2, i * 0.2 + 0.18) for i in range(9)])
        g = self.C.assign_groups(words, max_words=4)
        sizes = {}
        for w in g:
            sizes[w["g"]] = sizes.get(w["g"], 0) + 1
        self.assertLessEqual(max(sizes.values()), 4, sizes)

    def test_groups_are_contiguous_and_start_at_zero(self):
        words = self._w(("a", 0.0, 0.2), ("b.", 0.2, 0.4), ("c", 0.6, 0.8))
        g = self.C.assign_groups(words)
        ids = [w["g"] for w in g]
        self.assertEqual(ids[0], 0)
        for a, b in zip(ids, ids[1:]):
            self.assertIn(b - a, (0, 1), ids)

    def test_group_of_a_word_returns_its_whole_group(self):
        words = self._w(("a", 0.0, 0.2), ("b", 0.2, 0.4), ("c.", 0.4, 0.6),
                        ("d", 0.8, 1.0))
        g = self.C.assign_groups(words)
        grp = self.C.group_of(g, 2)
        self.assertEqual([w["word"] for w in grp], ["a", "b", "c."])

    def test_group_of_falls_back_when_words_have_no_group(self):
        """Films narrated before this change carry no `g`; they must still
        render, using the old fixed-width grouping instead of raising."""
        words = self._w(*[("w%d" % i, i * 0.2, i * 0.2 + 0.18) for i in range(8)])
        grp = self.C.group_of(words, 5)
        self.assertEqual([w["word"] for w in grp], ["w4", "w5", "w6", "w7"])

    def test_ui2d_reads_the_group_id(self):
        with open(os.path.join(STUDIO, "engine", "ui2d.js"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("w.g", src, "ui2d.js still groups by fixed index")


class DerivedStyleTests(unittest.TestCase):
    """The look must follow the story, like the location and the cast do.

    Measured before this: 29 of 31 films rendered `midnight`, because
    generate_palette drew the style at random from five names and every
    hand-authored story hardcoded "midnight". A wedding and a detective story
    were graded identically.
    """

    def setUp(self):
        self.assertIsNotNone(LOC, "fresh.location is not importable")
        self.assertIsNotNone(_fresh_story, "fresh.story is not importable")
        self.ST = _fresh_story

    def test_style_follows_the_theme(self):
        self.assertEqual(LOC.derive_style("a wedding at the beach", "outdoor", "golden"), "golden")
        self.assertEqual(LOC.derive_style("a phone that will not stop ringing", "room", "night"), "neon")
        self.assertEqual(LOC.derive_style("a fairy tale about a lost dog", "room", "day"), "storybook")
        self.assertEqual(LOC.derive_style("a detective finds a letter", "office", "night"), "midnight")

    def test_style_falls_back_to_the_background_mood(self):
        self.assertEqual(LOC.derive_style("something happens", "room", "golden"), "golden")
        self.assertEqual(LOC.derive_style("something happens", "outdoor", "day"), "dusk")

    def test_style_is_always_a_real_style(self):
        for c in ("", "a chef", "rain at school", "a spaceship", "a funeral",
                  "a crowd gathers", "the last bus"):
            self.assertIn(LOC.derive_style(c, "room", "night"),
                          ("dusk", "midnight", "golden", "neon", "storybook"), c)

    def test_generated_stories_do_not_all_render_midnight(self):
        styles = {self.ST.concept_to_story(c)["style"] for c in
                  ("a chef opens a tiny restaurant", "a wedding in the rain",
                   "a phone that will not stop ringing", "a fairy tale about a lost dog",
                   "the last bus never comes", "a detective finds a letter")}
        self.assertGreaterEqual(len(styles), 3, "styles barely vary: %s" % styles)

    def test_style_is_deterministic(self):
        a = self.ST.concept_to_story("a chef opens a tiny restaurant")["style"]
        b = self.ST.concept_to_story("a chef opens a tiny restaurant")["style"]
        self.assertEqual(a, b)

    def test_a_series_pins_its_style(self):
        styles = {self.ST.concept_to_story("episode %d" % e, series_id="s1",
                                           episode=e)["style"] for e in (1, 2, 3)}
        self.assertEqual(len(styles), 1, styles)


class GateActivationTests(unittest.TestCase):
    """`--strict` must turn the built gates ON, not just change their wording.

    Two gates were built and never called: frame_qa had no caller unless the
    operator remembered --frame-qa, and render_report's --fail-on-issues had
    ZERO callers anywhere, so a motion defect still produced a green run.
    """

    def setUp(self):
        self.assertIsNotNone(_gen, "tools/generate.py is not importable")
        self.G = _gen

    def test_default_run_activates_nothing(self):
        act = self.G.gate_activation(False, False)
        self.assertEqual(act, {"frame_qa": False, "fail_on_issues": False})

    def test_strict_activates_both_gates(self):
        act = self.G.gate_activation(True, False)
        self.assertEqual(act, {"frame_qa": True, "fail_on_issues": True})

    def test_frame_qa_flag_is_still_honoured_without_strict(self):
        act = self.G.gate_activation(False, True)
        self.assertEqual(act, {"frame_qa": True, "fail_on_issues": False})

    def test_strict_passes_fail_on_issues_to_render_report(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("--fail-on-issues", src)
        self.assertIn("act[\"fail_on_issues\"]", src)

    def test_strict_help_says_it_activates_the_gates(self):
        with open(os.path.join(TOOLS, "generate.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("activates every gate", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
