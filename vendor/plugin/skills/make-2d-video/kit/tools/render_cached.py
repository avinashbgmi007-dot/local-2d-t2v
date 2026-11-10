#!/usr/bin/env python3
"""Shot-range cache with conservative full-input fingerprints and atomic publication.

  python tools/render_cached.py --project projects/foo [--scale .5] [--report|--clear]
Writes build/video_cached.mp4 (silent). Any engine/project/word-timing/dependency change
invalidates the project conservatively; correctness is preferred over maximal reuse.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from .validate_project import validate_project
except ImportError:
    from validate_project import validate_project

ROOT = Path(__file__).resolve().parents[1]
CODE_EXT = (".js", ".mjs", ".html", ".json", ".css", ".png", ".jpg", ".svg", ".woff2", ".ttf", ".otf")


def h_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_tree(h, base, rels):
    base = Path(base)
    for rel in sorted(rels):
        path = base / rel
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in CODE_EXT) if path.is_dir() else []
        for file in files:
            key = file.relative_to(base).as_posix()
            h.update(key.encode() + b"\0" + h_file(file).encode() + b"\0")


def fingerprint(root=ROOT, project=None):
    h = hashlib.sha256(b"cache-schema-v3\0")
    hash_tree(h, root, ["engine", "chars", "templates", "render.mjs", "render-utils.mjs", "player.html", "package.json", "package-lock.json"])
    if project is not None:
        hash_tree(h, project, ["scenes", "story/shots.json", "config.json", "story/style-lock.json", "timeline/words.json"])
    return h.hexdigest()


def engine_fingerprint():
    return fingerprint()[:12]


def project_fingerprint(project):
    return fingerprint(project=project)[:12]


def frame_bounds(start, end, fps):
    import math
    return max(0, math.ceil(start * fps - 1e-9)), max(0, math.ceil(end * fps - 1e-9))


def concat_line(path):
    value = os.path.abspath(path).replace("\\", "/").replace("'", "'\\''")
    return "file '" + value + "'\n"


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height,nb_frames,r_frame_rate", "-of", "json", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        raise RuntimeError("cached clip has no video stream")
    return streams[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True)
    ap.add_argument("--scale", type=float, default=1)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--style")
    ap.add_argument("--format", choices=["png", "jpeg"], default="png")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--gl", choices=["auto", "gpu", "swiftshader"])
    args = ap.parse_args()
    project = Path(args.project).resolve()
    if not .1 <= args.scale <= 1 or not 0 <= args.crf <= 51:
        ap.error("scale must be .1..1 and crf 0..51")
    errors, warnings = validate_project(project)
    if errors:
        print("CACHE INVALID:\n  " + "\n  ".join(errors)); return 2
    for warning in warnings:
        print("WARN", warning)
    cache = project / "build/cache"
    if args.clear:
        shutil.rmtree(cache, ignore_errors=True)
        print("cleared", cache); return 0
    cfg = json.loads((project / "config.json").read_text(encoding="utf-8"))
    story = json.loads((project / "story/shots.json").read_text(encoding="utf-8"))
    fps = cfg.get("fps", 24)
    fp = fingerprint(ROOT, project)
    options = {k: getattr(args, k) for k in ("scale", "style", "format", "crf", "preset", "gl")}
    short = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:10]
    print("fingerprint", fp[:16], "options", short)
    plan = []
    for i, shot in enumerate(story["shots"]):
        a, b = frame_bounds(shot["start"], shot["end"], fps)
        # Incoming transitions and interpolated bars read the previous shot.
        payload = {"shot": shot, "previous": story["shots"][i - 1] if i else None,
                   "frames": [a, b], "fps": fps, "fingerprint": fp, "options": options}
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
        clip = cache / f"{shot['id']}_{key}.mp4"
        plan.append((shot, a, b, clip))
        print(f"  {shot['id']} frames {a}:{b} {'HIT' if clip.is_file() else 'MISS'} {key}")
    if args.report:
        return 0
    cache.mkdir(parents=True, exist_ok=True)
    short_side = {"720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160, "4k": 2160}[cfg.get("resolution", "1080p")]
    vertical = cfg.get("aspect") == "9:16"
    width = round((short_side if vertical else round(short_side * 16 / 9 / 2) * 2) * args.scale / 2) * 2
    height = round((round(short_side * 16 / 9 / 2) * 2 if vertical else short_side) * args.scale / 2) * 2
    for shot, a, b, clip in plan:
        expected = {"width": str(width), "height": str(height), "nb_frames": str(b - a)}
        if clip.is_file():
            try:
                actual = probe(clip)
                if all(str(actual.get(k)) == v for k, v in expected.items()):
                    continue
            except (RuntimeError, ValueError):
                pass
            print("  discarding invalid cache entry", shot["id"])
            clip.unlink(missing_ok=True)
        partial = clip.with_name(clip.stem + ".partial.mp4")
        partial.unlink(missing_ok=True)
        cmd = [sys.executable, "-u", str(ROOT / "tools/render_gate.py"), "--project", str(project), "--",
               "--frame-from", str(a), "--frame-to", str(b), "--scale", str(args.scale),
               "--format", args.format, "--crf", str(args.crf), "--preset", args.preset, "--out", str(partial)]
        if args.style:
            cmd += ["--style", args.style]
        if args.gl:
            cmd += ["--gl", args.gl]
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode:
            partial.unlink(missing_ok=True); return result.returncode
        try:
            actual = probe(partial)
            if not all(str(actual.get(k)) == v for k, v in expected.items()):
                raise RuntimeError(f"expected {expected}, got {actual}")
            os.replace(partial, clip)
        except (RuntimeError, ValueError, OSError) as exc:
            partial.unlink(missing_ok=True); print("CACHE REJECTED:", exc); return 1
    listing = cache / "concat.txt"
    listing.write_text("".join(concat_line(clip) for _, _, _, clip in plan), encoding="utf-8")
    output = project / "build/video_cached.mp4"
    partial = output.with_name("video_cached.partial.mp4")
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                             "-c", "copy", "-movflags", "+faststart", str(partial)])
    if result.returncode:
        partial.unlink(missing_ok=True); return result.returncode
    os.replace(partial, output)
    print("wrote", output, f"({len(plan)} shots, {story['duration']:.3f}s target)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
