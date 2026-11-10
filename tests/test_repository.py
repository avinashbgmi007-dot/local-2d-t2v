import contextlib
import io
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

from tools import repo_scan, validate_project as vp
from tools import director, render_cached, review_frames, narrate, new_project, parse_script


def png(width=2, height=2):
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    raw = b"".join(b"\0" + b"\xff\0\0\xff" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class ScannerTests(unittest.TestCase):
    def test_png_includes_chunk_type_in_crc(self):
        self.assertEqual(repo_scan.png_check(png()), {"width": 2, "height": 2})

    def test_png_detects_real_corruption(self):
        data = bytearray(png())
        data[40] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC"):
            repo_scan.png_check(data)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json.loads('{"fps":24,"fps":30}', object_pairs_hook=repo_scan.unique_object)

    def test_ogg_crc(self):
        page = bytearray(b"OggS" + b"\0" * 22 + b"\1\4data")
        crc = 0
        for byte in page:
            crc ^= byte << 24
            for _ in range(8):
                crc = ((crc << 1) ^ (0x04c11db7 if crc & 0x80000000 else 0)) & 0xffffffff
        struct.pack_into("<I", page, 22, crc)
        self.assertEqual(repo_scan.ogg_check(page), {"pages": 1})
        page[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC"):
            repo_scan.ogg_check(page)


class ContractTests(unittest.TestCase):
    def config(self):
        return {"aspect": "16:9", "fps": 24, "style": "midnight"}

    def story(self):
        return {"duration": 2, "shots": [{"id": "s1", "start": 0, "end": 1}, {"id": "s2", "start": 1, "end": 2}]}

    def test_valid_contract(self):
        self.assertEqual(vp.validate_data(self.config(), self.story())[0], [])

    def test_rejects_gap_overlap_duplicate_and_unsafe_id(self):
        for shot in [{"id": "s2", "start": 1.1, "end": 2}, {"id": "s1", "start": .9, "end": 2},
                     {"id": "s1", "start": 1, "end": 2}, {"id": "../escape", "start": 1, "end": 2}]:
            story = self.story()
            story["shots"][1] = shot
            self.assertTrue(vp.validate_data(self.config(), story)[0])
        self.assertTrue(vp.validate_data(self.config(), {"shots": []})[0])
        self.assertTrue(vp.validate_data({"fps": 0}, self.story())[0])

    def test_word_order(self):
        self.assertEqual(vp.validate_words([{"word": "a", "start": 0, "end": .5}]), [])
        self.assertTrue(vp.validate_words([{"word": "a", "start": 1, "end": .5}]))


class DirectorTests(unittest.TestCase):
    def story(self):
        return {"title": "Test", "aspect": "9:16", "cast": {"MAX": {"color": "#c2553d"}},
                "shots": [{"id": "s1", "size": "wide", "line": "Hello.", "hold": 1, "who": "MAX"}]}

    def test_invalid_source_does_not_touch_existing_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            sentinel = project / "keep.txt"
            sentinel.write_text("original")
            story = self.story()
            story["shots"][0]["size"] = "typo"
            with self.assertRaises(ValueError):
                director.compile_project(story, project)
            self.assertEqual(sentinel.read_text(), "original")
            self.assertFalse((project / "config.json").exists())

    def test_cast_cannot_inject_javascript(self):
        story = self.story()
        story["cast"] = {"MAX};globalThis.pwned=1;//": {}}
        with self.assertRaises(ValueError):
            director.compile_project(story, Path(tempfile.gettempdir()) / "unused")

    def test_recompile_removes_only_stale_generated_shots(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            story = self.story()
            story["shots"].append({"id": "s2", "size": "close", "line": "", "hold": 1})
            director.compile_project(story, project)
            hand = project / "scenes/shots/custom.js"
            hand.write_text("// hand authored")
            story["shots"].pop()
            director.compile_project(story, project)
            self.assertFalse((project / "scenes/shots/s2.js").exists())
            self.assertTrue(hand.exists())
            self.assertEqual(vp.validate_project(project)[0], [])


class CacheTests(unittest.TestCase):
    def test_concat_apostrophe(self):
        line = render_cached.concat_line(Path("/tmp/it's/a.mp4"))
        self.assertIn("'\\''", line)

    def test_word_timings_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, project = Path(tmp) / "studio", Path(tmp) / "project"
            for directory in [root / "engine", root / "chars", project / "scenes/shots", project / "timeline", project / "story"]:
                directory.mkdir(parents=True)
            (root / "render.mjs").write_text("render")
            (root / "player.html").write_text("player")
            (project / "config.json").write_text("{}")
            (project / "story/shots.json").write_text("{}")
            (project / "scenes/shots/s1.js").write_text("scene")
            words = project / "timeline/words.json"
            words.write_text('{"words":[{"word":"a","start":0,"end":1}]}')
            first = render_cached.fingerprint(root, project)
            words.write_text('{"words":[{"word":"a","start":0,"end":2}]}')
            self.assertNotEqual(first, render_cached.fingerprint(root, project))


class ReviewTests(unittest.TestCase):
    def test_ffmpeg_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(review_frames, "probe", return_value=(2, 1920, 1080)), \
                mock.patch.object(review_frames, "extract_frame", side_effect=RuntimeError("extraction failed")), \
                contextlib.redirect_stdout(io.StringIO()):
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"test")
            args = mock.Mock(project=None, video=str(video), count=1, out=tmp, aspect="16:9", allow_dark=False)
            self.assertNotEqual(review_frames.cmd_review(args), 0)


class NarrationTests(unittest.TestCase):
    def test_no_retime_preserves_declared_starts(self):
        story = {"shots": [{"start": 0, "end": 1}, {"start": 2, "end": 3}]}
        result = narrate.retime(story, [1, 1], no_retime=True)
        self.assertEqual([s["start"] for s in result["shots"]], [0, 2])
        self.assertEqual(result["duration"], 3)


class ProjectCreationTests(unittest.TestCase):
    def test_rejects_path_traversal_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            self.assertNotEqual(new_project.create("../escape", root=root), 0)
            (root / "projects/existing").mkdir(parents=True)
            self.assertNotEqual(new_project.create("existing", root=root), 0)




class TemplateTests(unittest.TestCase):
    def story(self):
        return json.loads((director.Path(__file__).resolve().parents[1] / "examples/template-showcase.json").read_text())

    def test_all_twelve_compile_and_validate(self):
        from tools.story_schema import REGISTRY, validate_story
        story = self.story()
        self.assertEqual(len(REGISTRY), 12)
        self.assertEqual({s["template"] for s in story["shots"]}, set(REGISTRY))
        self.assertEqual(validate_story(story)[0], [])
        with tempfile.TemporaryDirectory() as tmp:
            director.compile_project(story, tmp)
            self.assertEqual(vp.validate_project(tmp)[0], [])

    def test_unknown_template_param_pose_and_cast_fail(self):
        for key, value in [("template", "typo"), ("params", {"who": ["NOBODY"]}),
                           ("params", {"pose": ["typo"]}), ("params", {"typo": 1})]:
            story = self.story()
            story["shots"][0][key] = value
            with self.assertRaises(ValueError):
                director.compile_project(story, Path(tempfile.gettempdir()) / "unused-template")

    def test_fractional_cache_boundaries(self):
        shots = [(0, .345), (.345, .701), (.701, 1.2)]
        bounds = [render_cached.frame_bounds(a, b, 24) for a, b in shots]
        self.assertEqual(bounds, [(0, 9), (9, 17), (17, 29)])

    def test_engine_enum_mirrors(self):
        import subprocess
        from tools import story_schema as schema
        script = "import {POSES,EXPR} from './engine/rig2d.js'; import {PRESETS} from './chars/acting.js'; import {BASE_MOODS,STYLE_IDS} from './engine/styles.js'; console.log(JSON.stringify([Object.keys(POSES),Object.keys(EXPR),Object.keys(PRESETS),Object.keys(BASE_MOODS),STYLE_IDS]))"
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
        actual = json.loads(result.stdout)
        for got, expected in zip(actual, [schema.POSES, schema.EXPRESSIONS, schema.FACES, schema.MOODS, schema.STYLES]):
            self.assertEqual(set(got), expected)




class SeamTests(unittest.TestCase):
    def test_template_manifest_entities(self):
        from tools import seam_gate
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "story").mkdir()
            (project / "story/shots.json").write_text(json.dumps({"shots": [
                {"id": "s1", "template": "establish-push", "params": {"who": ["MAX", "JAKE"], "set": "room"}},
                {"id": "s2", "template": "insert-object", "params": {"object": {"kind": "book"}, "set": "room"}},
            ]}))
            entities = seam_gate.declared_cast(project)
            self.assertEqual(entities["s1"], {"max", "jake", "room"})
            self.assertEqual(entities["s2"], {"book", "room"})


class ReportTests(unittest.TestCase):
    def test_motion_failure_does_not_reuse_stale_report(self):
        from tools import render_report
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "build").mkdir()
            stale = project / "build/motion.json"
            stale.write_text(json.dumps({"windows": [{"mean_motion": 1.0}], "issues": []}))
            with mock.patch.object(render_report.subprocess, "run", return_value=mock.Mock(returncode=2, stdout="", stderr="decode failed")):
                result = render_report.motion("video.mp4", str(project))
            self.assertEqual(result["verdict"], "NOT RUN")
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()


class DialogueCastingTests(unittest.TestCase):
    """Shot-level speaker casting and the template-mode sound-design crash."""

    def _story(self, **over):
        st = {"title": "t", "aspect": "9:16", "cast": {"NILA": {}, "ARUN": {}},
              "shots": [{"id": "s1", "size": "med", "dur": 2, "line": "Hello.",
                         "speaker": "NILA", "who": "NILA"}], "music": []}
        st.update(over)
        return st

    def test_speaker_and_voices_are_accepted(self):
        from tools.story_schema import validate_story
        errors, _ = validate_story(self._story(voices={"NILA": "af_heart"}))
        self.assertEqual(errors, [])

    def test_unknown_speaker_is_rejected(self):
        from tools.story_schema import validate_story
        st = self._story()
        st["shots"][0]["speaker"] = "GHOST"
        errors, _ = validate_story(st)
        self.assertTrue(any("unknown speaker" in e for e in errors))

    def test_unknown_voice_key_is_rejected(self):
        from tools.story_schema import validate_story
        errors, _ = validate_story(self._story(voices={"GHOST": "x"}))
        self.assertTrue(any("unknown speaker" in e for e in errors))

    def test_line_without_speaker_warns(self):
        from tools.story_schema import validate_story
        st = self._story()
        del st["shots"][0]["speaker"]
        _, warnings = validate_story(st)
        self.assertTrue(any("no speaker" in w for w in warnings))

    def test_sound_design_handles_list_valued_pose(self):
        # Regression: template projects put a LIST in params.pose; .lower() on it
        # raised AttributeError and killed the entire foley pass.
        import json, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "story"), exist_ok=True)
            shots = {"duration": 4, "shots": [
                {"id": "a", "start": 0, "end": 2, "params": {"pose": ["stand", "walk"]}},
                {"id": "b", "start": 2, "end": 4, "params": {"pose": ["relaxed"]}}]}
            path = os.path.join(d, "story", "shots.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(shots, fh)
            r = subprocess.run([sys.executable, "tools/sound_design.py", "--project", d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("footstep", r.stdout)

    def test_parse_script_preserves_speaker_tags(self):
        import json, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "timeline"), exist_ok=True)
            with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as fh:
                json.dump({"title": "t", "aspect": "9:16", "fps": 24}, fh)
            src = os.path.join(d, "words.json")
            with open(src, "w", encoding="utf-8") as fh:
                json.dump({"words": [{"word": "Hi.", "start": 0, "end": .5, "speaker": "NILA"}]}, fh)
            r = subprocess.run([sys.executable, "tools/parse_script.py", "--project", d,
                                "--script", src], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.load(open(os.path.join(d, "timeline", "words.json"), encoding="utf-8"))
            words = data["words"] if isinstance(data, dict) else data
            self.assertEqual(words[0]["speaker"], "NILA")


class PropContinuityTests(unittest.TestCase):
    """Shot-level prop ownership: the schema half of the contact hard gate."""

    def _story(self, prop):
        return {"title": "t", "aspect": "9:16", "cast": {"NILA": {}, "ARUN": {}},
                "shots": [{"id": "s1", "size": "med", "dur": 2, "who": "ARUN", "prop": prop}],
                "music": []}

    def test_valid_prop_passes(self):
        from tools.story_schema import validate_story
        e, w = validate_story(self._story({"kind": "book", "who": "ARUN", "color": "#b8452f"}))
        self.assertEqual(e, [])
        self.assertEqual(w, [])

    def test_unknown_holder_rejected(self):
        from tools.story_schema import validate_story
        e, _ = validate_story(self._story({"kind": "book", "who": "GHOST"}))
        self.assertTrue(any("unknown prop holder" in x for x in e))

    def test_unknown_kind_rejected(self):
        from tools.story_schema import validate_story
        e, _ = validate_story(self._story({"kind": "sword", "who": "ARUN"}))
        self.assertTrue(any("unknown prop kind" in x for x in e))

    def test_holderless_prop_warns(self):
        from tools.story_schema import validate_story
        e, w = validate_story(self._story({"kind": "book"}))
        self.assertEqual(e, [])
        self.assertTrue(any("no holder" in x for x in w))

    def test_bad_colour_and_field_rejected(self):
        from tools.story_schema import validate_story
        e, _ = validate_story(self._story({"kind": "book", "who": "ARUN",
                                           "color": "red", "grip": 3}))
        self.assertTrue(any("prop.color" in x for x in e))
        self.assertTrue(any("unknown prop field" in x for x in e))

    def test_prop_survives_compilation(self):
        from tools.director import compile_project
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "proj")
            story = self._story({"kind": "book", "who": "ARUN", "color": "#b8452f"})
            compiled = compile_project(story, out)
            self.assertEqual(compiled["shots"][0]["prop"]["who"], "ARUN")

    def test_reach_low_pose_is_in_both_mirrors(self):
        # story_schema mirrors the engine's pose vocabulary; a preset added to one
        # and not the other makes every story using it fail validation.
        from tools.story_schema import POSES
        self.assertIn("reachLow", POSES)
        self.assertIn("reachLow:", Path("engine/rig2d.js").read_text(encoding="utf-8"))


class PropTransferTests(unittest.TestCase):
    """Mid-shot prop transfer (prop.from + prop.at): the schema half."""

    def _story(self, prop):
        return {"title": "t", "aspect": "9:16", "cast": {"NILA": {}, "ARUN": {}},
                "shots": [{"id": "s1", "size": "med", "dur": 2, "prop": prop}], "music": []}

    def test_transfer_fields_valid(self):
        from tools.story_schema import validate_story
        e, w = validate_story(self._story({"kind": "book", "who": "NILA", "from": "ARUN",
                                           "at": 0.65, "color": "#b8452f"}))
        self.assertEqual(e, [])

    def test_bad_at_rejected(self):
        from tools.story_schema import validate_story
        e, _ = validate_story(self._story({"kind": "book", "who": "NILA", "from": "ARUN", "at": 1.5}))
        self.assertTrue(any("prop.at" in x for x in e))

    def test_unknown_from_rejected(self):
        from tools.story_schema import validate_story
        e, _ = validate_story(self._story({"kind": "book", "who": "NILA", "from": "GHOST", "at": 0.5}))
        self.assertTrue(any("prop.from" in x for x in e))
