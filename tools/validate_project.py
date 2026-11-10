#!/usr/bin/env python3
"""Validate a project's render contract without importing the audio/model stack.

  python tools/validate_project.py --project projects/my-video [--strict]

Errors are invalid contracts (bad intervals, IDs, dimensions or scene coverage).
Warnings are portable-checkout limitations, such as intentionally ignored audio.
This is a technical check, not visual approval. Used by repo_scan and render_gate.
"""
import argparse
import json
import math
import re
from pathlib import Path

ASPECTS = {"16:9", "9:16"}
RESOLUTIONS = {"720p", "1080p", "1440p", "2160p", "4k"}
STYLES = {"dusk", "midnight", "golden", "neon", "storybook"}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
REGISTER_RE = re.compile(r"\bregisterShot\(\s*(['\"])(.*?)\1", re.S)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as fh:
        return json.load(fh)


def validate_data(cfg, story):
    errors, warnings = [], []
    if not isinstance(cfg, dict) or not isinstance(story, dict):
        return ["config and story must be JSON objects"], warnings
    if cfg.get("aspect", "16:9") not in ASPECTS:
        errors.append("config.aspect must be 16:9 or 9:16")
    if cfg.get("resolution", "1080p") not in RESOLUTIONS:
        errors.append("unsupported config.resolution")
    if cfg.get("style", "dusk") not in STYLES:
        errors.append("unknown config.style")
    fps = cfg.get("fps", 24)
    if not number(fps) or not 1 <= fps <= 240 or int(fps) != fps:
        errors.append("config.fps must be an integer in 1..240")
    shots = story.get("shots")
    if not isinstance(shots, list) or not shots:
        return errors + ["story.shots must be a non-empty list"], warnings
    ids = set()
    previous = 0.0
    for i, shot in enumerate(shots):
        label = f"shots[{i}]"
        if not isinstance(shot, dict):
            errors.append(label + " must be an object")
            continue
        sid = shot.get("id")
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid):
            errors.append(label + ".id must match " + ID_RE.pattern)
        elif sid in ids:
            errors.append(f"duplicate shot id {sid}")
        else:
            ids.add(sid)
            label = sid
        start, end = shot.get("start"), shot.get("end")
        if not number(start) or not number(end) or start < 0 or end <= start:
            errors.append(f"{label}: need finite 0 <= start < end")
            continue
        if abs(start - previous) > 0.002:
            errors.append(f"{label}: timeline gap/overlap at {start:.3f}s (expected {previous:.3f})")
        previous = end
        transition = shot.get("in", {"type": "cut"})
        if not isinstance(transition, dict) or transition.get("type", "cut") not in {
                "cut", "fade", "dip", "dipWhite", "flash", "whip", "zoom"}:
            errors.append(f"{label}: unknown transition")
        elif "dur" in transition and (not number(transition["dur"]) or transition["dur"] <= 0):
            errors.append(f"{label}: transition.dur must be positive")
        cues = shot.get("sfx", [])
        if not isinstance(cues, list):
            errors.append(f"{label}: sfx must be a list")
        else:
            for cue in cues:
                if not isinstance(cue, dict) or not isinstance(cue.get("name"), str) or not cue["name"]:
                    errors.append(f"{label}: invalid SFX cue")
                elif "at" in cue and (not number(cue["at"]) or not 0 <= cue["at"] <= end - start):
                    errors.append(f"{label}: SFX cue outside shot")
    duration = story.get("duration", previous)
    if not number(duration) or duration <= 0 or abs(duration - previous) > 0.002:
        errors.append("story.duration must equal the last shot end")
    if number(fps) and fps > 0 and number(duration) and duration > 0 and duration * fps < 1:
        errors.append("film contains no complete frame")
    for key in ("voiceover", "script"):
        if key in cfg and key in story and cfg[key] != story[key]:
            warnings.append(f"config/story disagree on {key}")
    return errors, warnings


def validate_words(data):
    errors = []
    words = data.get("words") if isinstance(data, dict) else data
    if not isinstance(words, list):
        return ["timeline words must be a list or an object with a words list"]
    previous = 0.0
    for i, word in enumerate(words):
        if not isinstance(word, dict) or not isinstance(word.get("word"), str):
            errors.append(f"word {i}: missing text")
            continue
        start, end = word.get("start"), word.get("end")
        if not number(start) or not number(end) or start < 0 or end < start:
            errors.append(f"word {i}: invalid interval")
            continue
        if start < previous:
            errors.append(f"word {i}: timestamps are not ordered")
        previous = start
    return errors


def validate_project(project, check_scenes=True):
    project = Path(project)
    errors, warnings = [], []
    try:
        cfg, story = read_json(project / "config.json"), read_json(project / "story/shots.json")
    except (OSError, ValueError) as exc:
        return [str(exc)], warnings
    e, w = validate_data(cfg, story)
    errors += e
    warnings += w
    for key in ("voiceover", "script"):
        rel = cfg.get(key)
        if rel:
            if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts:
                errors.append(f"config.{key} must be a project-relative path")
            elif not (project / rel).is_file():
                warnings.append(f"missing optional/ignored asset: {rel}")
    words_path = project / "timeline/words.json"
    if words_path.exists():
        try:
            errors += validate_words(read_json(words_path))
        except (OSError, ValueError) as exc:
            errors.append(f"timeline: {exc}")
    if check_scenes:
        registered = {}
        files = sorted((project / "scenes").rglob("*.js")) if (project / "scenes").is_dir() else []
        for path in files:
            if path.name.startswith("_"):
                continue
            for match in REGISTER_RE.finditer(path.read_text(encoding="utf-8")):
                registered.setdefault(match.group(2), []).append(str(path.relative_to(project)))
        for shot in story.get("shots", []):
            sid = shot.get("id") if isinstance(shot, dict) else None
            if sid not in registered:
                errors.append(f"{sid}: no registered scene")
            elif len(registered[sid]) > 1:
                errors.append(f"{sid}: registered more than once: {registered[sid]}")
        expected = {s.get("id") for s in story.get("shots", []) if isinstance(s, dict)}
        for sid in sorted(set(registered) - expected):
            warnings.append(f"orphan scene registration: {sid}")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True)
    ap.add_argument("--strict", action="store_true", help="make warnings fatal")
    ap.add_argument("--no-scenes", action="store_true")
    args = ap.parse_args()
    errors, warnings = validate_project(args.project, not args.no_scenes)
    for item in errors:
        print("ERROR", item)
    for item in warnings:
        print("WARN ", item)
    print(f"validate: {len(errors)} error(s), {len(warnings)} warning(s)")
    return int(bool(errors) or (args.strict and bool(warnings)))


if __name__ == "__main__":
    raise SystemExit(main())
