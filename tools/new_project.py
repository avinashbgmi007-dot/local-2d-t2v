"""Create a project beside the studio, never relative to an arbitrary caller cwd.

  python tools/new_project.py --name my-video --voice /path/voiceover.mp3 [--script path]
Existing projects are never overwritten. Names are single safe path components.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import probe_duration, save_json

ROOT = Path(__file__).resolve().parents[1]


def create(name, voice=None, script=None, aspect="16:9", resolution="1080p", style="dusk",
           fps=24, title="", captions=False, root=ROOT):
    root = Path(root).resolve()
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        print("ERROR: name must be one safe folder name (letters, digits, _ or -).")
        return 2
    destination = root / "projects" / name
    if destination.exists():
        print(f"ERROR: {destination} already exists; choose a new name.")
        return 2
    if not voice or not Path(voice).is_file():
        print("ERROR: --voice must name an existing audio file.")
        return 2
    if script and not Path(script).is_file():
        print("ERROR: --script does not exist.")
        return 2
    if aspect not in {"16:9", "9:16"} or resolution not in {"720p", "1080p", "1440p", "2160p", "4k"} or not 1 <= fps <= 240:
        print("ERROR: invalid aspect, resolution or fps.")
        return 2
    # Stage everything before exposing a project directory. No partial project on failure.
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".new-project-", dir=destination.parent))
    try:
        for folder in ["input", "timeline", "story", "scenes/sets", "scenes/shots", "build", "out", "audio"]:
            (staging / folder).mkdir(parents=True, exist_ok=True)
        voice_dst = "input/voiceover" + Path(voice).suffix.lower()
        shutil.copy2(voice, staging / voice_dst)
        script_dst = None
        if script:
            script_dst = "input/script" + Path(script).suffix.lower()
            shutil.copy2(script, staging / script_dst)
        duration = probe_duration(str(staging / voice_dst))
        if duration <= 0:
            raise ValueError("voiceover has no positive duration")
        cfg = {"title": title or name, "aspect": aspect, "resolution": resolution, "fps": fps,
               "style": style, "voiceover": voice_dst, "script": script_dst, "duration": round(duration, 3),
               "captions": bool(captions), "bars": None, "fadeIn": .5, "fadeOut": .8,
               "music": {"enabled": True, "gainDb": -17}, "sfx": {"enabled": True, "gainDb": -6}, "loudness": -14}
        save_json(str(staging / "config.json"), cfg)
        if destination.exists():
            raise FileExistsError(destination)
        os.replace(staging, destination)
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        print(f"ERROR: project not created: {exc}")
        return 1
    print(f"created {destination} ({duration:.1f}s, {aspect} {resolution} @ {fps}fps)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True)
    ap.add_argument("--voice", required=True)
    ap.add_argument("--script")
    ap.add_argument("--aspect", default="16:9", choices=["16:9", "9:16"])
    ap.add_argument("--resolution", default="1080p", choices=["720p", "1080p", "1440p", "2160p", "4k"])
    ap.add_argument("--style", default="dusk", choices=["dusk", "midnight", "golden", "neon", "storybook"])
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--title", default="")
    ap.add_argument("--captions", action="store_true")
    a = ap.parse_args()
    return create(a.name, a.voice, a.script, a.aspect, a.resolution, a.style, a.fps, a.title, a.captions)


if __name__ == "__main__":
    raise SystemExit(main())
