"""tools/verify_kit.py — confirm every studio file was written exactly (run right after installing).

  python tools/verify_kit.py
Prints MISMATCH/MISSING for any file that differs from the tested version; copy those files again from the plugin kit folder.
(Line endings and leading/trailing blank lines are ignored. Files you customise later, e.g. engine/styles.js, will of course differ.)
"""
import hashlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = {
    "tools/speech_track.py": "d858269bb4540a91",
    "tools/speech_audit.mjs": "3844513ce1abcadf",
    "tools/test_voice.py": "caaf1e01755c911e",
    "tools/continuity_gate.mjs": "385051d8134aaaf2",
    "tools/audit_host.mjs": "e16a1353147b7bb0",
    "render-utils.mjs": "a65cc85fc59e9e76",
    "templates/interpreter.js": "4ca5971089aef88f",
    "templates/registry.json": "f6b193b2eb10eecd",
    "tools/story_schema.py": "770571e228a895cb",
    "tools/validate_project.py": "7faf15e2fdbf87ac",
    "tools/repo_scan.py": "b3be17bbd91517f9",
    "tools/render_gate.py": "e31a82b751eca34a",
    "tools/render_cached.py": "bb92cc54d7847d6c",
    "tools/render_report.py": "854350e26de64f57",
    "tools/review_frames.py": "3c11964244a5ee04",
    "tools/seam_gate.py": "ddf83566e32e0b92",
    "tools/style_lock.py": "6e8bc8038f9bbff3",
    "tools/generate.py": "3edcbb6204c8feea",
    "tools/director.py": "35d9ffbbd9337367",
    "tools/narrate.py": "33eb0e904109b4f0",
    "audio/dsp.py": "589d305d94d8acc3",
    "audio/mix.py": "a48273c523b68c3b",
    "audio/music.py": "2fb3ce1df2fe5c7d",
    "audio/sfx.py": "2fa56141e2423718",
    "engine/core.js": "f440d7e30a972934",
    "engine/fx2d.js": "d09f93f6d44366fa",
    "engine/player.js": "c40c4d13b7f7dfdb",
    "engine/rig2d.js": "d40c82d440365717",
    "engine/styles.js": "66b00b1b5f87326f",
    "engine/three-kit.js": "02e249e302b95420",
    "engine/ui2d.js": "2cbfd82c84568400",
    "examples/reaction-time/config.json": "9ee341c65b3cfe9a",
    "examples/reaction-time/scenes/cast.js": "e4faad3c508a5cf5",
    "examples/reaction-time/scenes/sets/cafe.js": "fb9adaa553e87b74",
    "examples/reaction-time/scenes/sets/lab.js": "a2da3ca0fff2d8c4",
    "examples/reaction-time/scenes/shots/01_cafe.js": "931e9c360ba052b3",
    "examples/reaction-time/scenes/shots/02_orbit3d.js": "77897bcae80a501e",
    "examples/reaction-time/scenes/shots/03_explain.js": "c22f0e7a8f505c78",
    "examples/reaction-time/story/bible.md": "e22b689a54461b41",
    "examples/reaction-time/story/shots.json": "9b1921e8e42c2498",
    "package.json": "1b6662823bf93df7",
    "player.html": "5ffdd7da4a48cd4b",
    "render.mjs": "d2700ac8bd78651d",
    "tools/beats.py": "eb42a8aef4d87584",
    "tools/common.py": "e237321f2f12416e",
    "tools/doctor.py": "ce17e8e1bfcb9b86",
    "tools/new_project.py": "b8acca0be8576485",
    "tools/parse_script.py": "8da843677c28656c",
    "tools/transcribe.py": "ecd48d05a6655d13",
}
bad = 0
for rel, want in EXPECTED.items():
    p = os.path.join(ROOT, *rel.split("/"))
    if not os.path.exists(p):
        print(f"MISSING   {rel}"); bad += 1; continue
    got = hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n").strip()).hexdigest()[:16]
    if got != want:
        print(f"MISMATCH  {rel}"); bad += 1
print(f"{len(EXPECTED) - bad}/{len(EXPECTED)} files verified." + ("" if not bad else "  Copy the files listed above again from the plugin's kit folder, then run this again."))
sys.exit(1 if bad else 0)
