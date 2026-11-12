#!/usr/bin/env python3
"""tools/variety_gate.py -- reject two consecutive films that look the same.

Owner rule (2026-11-12): derive variety by default, keep continuity only when a
series is named. The failure this guards against is real and measured: 17 of 31
projects in this repo were `room` + `midnight` + `midnight`, and the market
research flagged identical opening images across consecutive uploads as the
"mass-produced" signal that hurts a monetised channel.

Semantics follow the other gates in this repo: it PRINTS findings and exits 0
unless `--strict` is passed, so wiring it can never block an existing run.
A "duplicate look" means the same location AND the same cast AND the same style.
Same location alone, or same opening music mood alone, is a note, not a block.

No video is opened: it reads two story JSON files.
"""
import argparse
import json
import os
import sys


def signature(story):
    """The parts of a film a returning viewer would recognise as 'the same'."""
    story = story or {}
    cast = tuple(sorted((story.get("cast") or {}).keys()))
    music = story.get("music") or []
    opening = music[0].get("mood") if music and isinstance(music[0], dict) else None
    ambs = sorted({(s.get("amb") or {}).get("name")
                   for s in (story.get("shots") or [])
                   if isinstance(s, dict) and (s.get("amb") or {}).get("name")})
    return {
        "set": story.get("set") or "room",
        "style": story.get("style"),
        "cast": cast,
        "music": opening,
        "amb": tuple(ambs),
    }


def compare(prev, cur):
    """Return human-readable findings. Empty list means 'no repeat detected'."""
    a, b = signature(prev), signature(cur)
    issues = []
    if a["set"] == b["set"]:
        issues.append("same location: set=%r in both films" % a["set"])
    if a["cast"] == b["cast"]:
        issues.append("same cast: %s in both films" % (", ".join(a["cast"]) or "none"))
    if a["style"] and a["style"] == b["style"]:
        issues.append("same style: %r in both films" % a["style"])
    if a["music"] and a["music"] == b["music"]:
        issues.append("same music: opening mood %r in both films" % a["music"])
    if a["amb"] and a["amb"] == b["amb"]:
        issues.append("same ambience: %s in both films" % ", ".join(a["amb"]))
    if a["set"] == b["set"] and a["cast"] == b["cast"] and a["style"] == b["style"]:
        issues.append("duplicate look: same location, cast and style -- a viewer "
                      "would read the second film as the first one again")
    return issues


def verdict(issues, strict):
    """Exit code. Only a duplicate look is fatal, and only under --strict."""
    if strict and any(i.startswith("duplicate look") for i in issues):
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", required=True, help="earlier story JSON")
    ap.add_argument("--cur", required=True, help="later story JSON")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when the two films are a duplicate look")
    a = ap.parse_args(argv)
    prev = json.load(open(a.prev, encoding="utf-8"))
    cur = json.load(open(a.cur, encoding="utf-8"))
    issues = compare(prev, cur)
    for i in issues:
        print("VARIETY:", i)
    if not issues:
        print("VARIETY: OK -- the two films differ in location, cast and style")
    return verdict(issues, a.strict)


if __name__ == "__main__":
    sys.exit(main())
