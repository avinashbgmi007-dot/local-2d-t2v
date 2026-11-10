#!/usr/bin/env python3
"""
tools/scene_coverage.py -- prove every shot in shots.json has a registered scene
file BEFORE the renderer starts.

WHY THIS EXISTS
    A static, pre-render proof of shot registration. It FAILS CLOSED: a missing
    shot, a duplicate registration, an empty scene tree or an unprovable dynamic
    registration all stop the render before a single frame is drawn. It never
    edits the protected engine/ or render.mjs, and never opens a video.

    CORRECTION 2026-11-10 (independent falsifier): an earlier draft said
    "engine/player.js:75 ... no stdout signal exists at all" and claimed this
    tool was the only thing preventing a MISSING SHOT slate shipping. THAT WAS
    FALSE. render.mjs:55 prints "WARNING: N shots have no scene file yet" from
    window.SHOT_LIST (player.js:42), and the ORIGINAL render_gate.py already
    matched `WARNING:.*no scene file`. Runtime detection predates this tool.
    This pre-flight is therefore DEFENCE IN DEPTH (catch it earlier, before any
    frame is rendered), not the sole fix. The uppercase "SHOT ERROR" regex fix
    in render_gate.py remains a genuine separate bug fix.

    CORRECTION 2026-11-10 (same review): the first version globbed only
    scenes/shots/*.js and counted text matches as files. render.mjs:23 scans
    ALL .js under scenes/ recursively and skips filenames starting with "_".
    This version mirrors that, strips comments, de-duplicates per file, and
    treats dynamic registerShot(...) calls as INDETERMINATE instead of claiming
    a shot is missing.

USAGE
    python tools/scene_coverage.py --project projects/<slug>
    python tools/scene_coverage.py --selftest
    python tools/scene_coverage.py --project projects/<slug> --json

Exit: 0 = every declared shot is provably registered; 1 = missing / duplicate /
      indeterminate coverage. Orphan registrations are INFO, not a failure.
"""
import argparse
import json
import os
import re
import sys

# Handles registerShot('id'), ("id") and (`id`), with optional whitespace.
REGISTER_RE = re.compile(r"""registerShot\s*\(\s*(['"`])([^'"`]+)\1""")
CALL_RE = re.compile(r"registerShot\s*\(")


def shot_ids(project):
    """Declared shot ids from <project>/story/shots.json (id 0 is a valid id)."""
    path = os.path.join(project, "story", "shots.json")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    arr = data.get("shots", []) if isinstance(data, dict) else data
    return [str(s["id"]) for s in arr
            if isinstance(s, dict) and s.get("id") is not None]


def scene_files(project):
    """Mirror render.mjs:23 listScenes(): all .js under scenes/, recursively,
    skipping filename prefixes '_'. A _draft.js is never loaded by the player.
    """
    root = os.path.join(project, "scenes")
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if fn.endswith(".js") and not fn.startswith("_"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def strip_comments(text):
    """Drop block comments and whole-line // comments so commented-out examples
    cannot satisfy coverage. Inline trailing // comments are a known limitation.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def registered_ids(project):
    """Return ({shot_id: [distinct filenames]}, [scene files], [(file, n_dynamic)])."""
    files = scene_files(project)
    found, dynamic = {}, []
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = strip_comments(fh.read())
        calls = len(CALL_RE.findall(text))
        literals = 0
        for m in REGISTER_RE.finditer(text):
            literals += 1
            entry = found.setdefault(m.group(2), [])
            # Key by project-relative path, not basename: two same-named files in
            # different subdirectories are two distinct registrations.
            name = os.path.relpath(path, project).replace("\\", "/")
            if name not in entry:          # duplicate literal in ONE file is not a duplicate registration
                entry.append(name)
        if calls > literals:
            dynamic.append((os.path.basename(path), calls - literals))
    return found, files, dynamic


def check(project):
    """Return (errors, warnings, stats). Pure filesystem reads; no video I/O."""
    errors, warnings = [], []
    try:
        ids = shot_ids(project)
    except FileNotFoundError as e:
        return [f"no shots.json at {e}"], warnings, {}
    except (ValueError, KeyError, TypeError) as e:
        return [f"could not parse shots.json: {e}"], warnings, {}

    found, files, dynamic = registered_ids(project)
    stats = {"shots": len(ids), "scene_files": len(files),
             "registered": len(found), "dynamic_calls": sum(n for _, n in dynamic)}

    if not ids:
        errors.append("shots.json declares no shot ids")
    if not files:
        errors.append("no .js files under scenes/ -- nothing can render")
    if dynamic:
        errors.append("dynamic registerShot(...) call(s) in %s; coverage "
                      "INDETERMINATE -- cannot prove which ids resolve"
                      % ", ".join(f for f, _ in dynamic))
    elif files and not found:
        errors.append("scene files exist but contain no static registerShot(...) call; "
                      "coverage is INDETERMINATE")

    # Only claim a shot is MISSING when registration is fully provable.
    if not dynamic and found:
        missing = [i for i in ids if i not in found]
        if missing:
            errors.append("shots with no registered scene: " + ", ".join(missing))

    duplicate = {k: v for k, v in found.items() if len(v) > 1}
    if duplicate:
        errors.append("shot ids registered in more than one file: "
                      + ", ".join(f"{k} ({len(v)} files)" for k, v in duplicate.items()))
    orphan = [k for k in found if k not in ids]
    if orphan:
        warnings.append("registered but not in shots.json (INFO, not a failure): "
                        + ", ".join(orphan))
    return errors, warnings, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "story"))
            shot_dir = os.path.join(d, "scenes", "shots")
            os.makedirs(shot_dir)
            shots_path = os.path.join(d, "story", "shots.json")

            def write_shots(ids):
                with open(shots_path, "w", encoding="utf-8") as f:
                    json.dump({"shots": [{"id": i} for i in ids]}, f)

            def write_scene(name, sid, quote="'"):
                with open(os.path.join(shot_dir, name + ".js"), "w", encoding="utf-8") as f:
                    f.write("registerShot(%s%s%s, { draw(){} });\n" % (quote, sid, quote))

            write_shots(["s001", "s002"])
            write_scene("01", "s001")
            write_scene("02", "s002", quote='"')
            assert check(d)[0] == [], "clean project must pass"

            write_shots(["s001", "s002", "s003"])
            assert any("no registered scene" in e for e in check(d)[0]), "missing shot must fail"

            write_shots(["s001", "s002"])
            write_scene("dup", "s001")
            assert any("more than one file" in e for e in check(d)[0]), "duplicate must fail"
            os.remove(os.path.join(shot_dir, "dup.js"))

            write_scene("extra", "s099")
            errs, warns, _ = check(d)
            assert errs == [], "orphan registration must not fail the gate"
            assert any("s099" in w for w in warns), "orphan must be INFO"
            os.remove(os.path.join(shot_dir, "extra.js"))

            # A _draft.js is ignored by render.mjs and must not satisfy coverage.
            os.remove(os.path.join(shot_dir, "02.js"))
            with open(os.path.join(shot_dir, "_draft.js"), "w", encoding="utf-8") as f:
                f.write("registerShot('s002', { draw(){} });\n")
            assert any("no registered scene" in e for e in check(d)[0]), \
                "_draft.js must not count"
            os.remove(os.path.join(shot_dir, "_draft.js"))

            # A commented-out registration must not satisfy coverage.
            with open(os.path.join(shot_dir, "commented.js"), "w", encoding="utf-8") as f:
                f.write("// registerShot('s002', { draw(){} });\n")
            assert check(d)[0], "commented registration must not count"
            os.remove(os.path.join(shot_dir, "commented.js"))

            # Duplicate literal inside ONE file is not a duplicate registration.
            with open(os.path.join(shot_dir, "02.js"), "w", encoding="utf-8") as f:
                f.write("registerShot('s002', {});\nregisterShot('s002', {});\n")
            assert check(d)[0] == [], "same-file duplicate must not fail"
            os.remove(os.path.join(shot_dir, "02.js"))

            # Dynamic registration is INDETERMINATE, never a false 'missing'.
            with open(os.path.join(shot_dir, "dyn.js"), "w", encoding="utf-8") as f:
                f.write("for (const id of ids) registerShot(id, def);\n")
            errs, _, _ = check(d)
            assert any("INDETERMINATE" in e for e in errs)
            assert not any("no registered scene" in e for e in errs), \
                "must not claim missing when registration is unprovable"
            os.remove(os.path.join(shot_dir, "dyn.js"))

            os.remove(os.path.join(shot_dir, "01.js"))
            assert any("no .js files" in e or "INDETERMINATE" in e
                       for e in check(d)[0]), "empty scene dir must fail"

            # Numeric id 0 must not be dropped by a truthiness test.
            write_shots([0, 1])
            assert check(d)[2]["shots"] == 2
        print("SELFTEST PASS -- clean / missing / duplicate / orphan / _draft / "
              "comment / same-file dup / dynamic / empty / numeric id")
        return 0

    if not a.project:
        sys.exit("ERROR: --project <dir> is required (or --selftest).")
    errors, warnings, stats = check(a.project)
    if a.json:
        print(json.dumps({"errors": errors, "warnings": warnings, "stats": stats}, indent=1))
    else:
        print("SCENE COVERAGE:", a.project)
        print("  shots %s | scene files %s | registered ids %s | dynamic calls %s"
              % (stats.get("shots"), stats.get("scene_files"),
                 stats.get("registered"), stats.get("dynamic_calls")))
        for w in warnings:
            print("  INFO  " + w)
        for e in errors:
            print("  FAIL  " + e)
    if errors:
        print("SCENE COVERAGE: FAIL -- render must not start")
        return 1
    print("SCENE COVERAGE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
