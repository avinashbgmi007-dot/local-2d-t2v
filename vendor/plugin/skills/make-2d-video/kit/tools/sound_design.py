#!/usr/bin/env python3
"""
sound_design.py — add the foley layer a picture editor would add, automatically.

Cinema is not just images; it is the interval filled with sound. A cut with no
whoosh feels like a slideshow. A walk with no footsteps feels like a slide.

This reads story/shots.json and, without touching authored cues:
  * a soft whoosh on every hard cut (except the first shot)
  * footsteps under any shot whose pose is a walk
  * a riser in the shot BEFORE a flash / zoom transition
  * one ambience bed on the opening shot (room tone by default)
  * an impact when a shot is tagged  "beat": "impact"

Authored `sfx` entries always win; this only fills the gaps.

  python tools/sound_design.py --project projects/foo [--dry]
"""
import argparse
import json
import os

WHOOSH_GAIN = -27.0     # subtle: felt, not heard
FOOT_GAIN = -17.0
RISER_GAIN = -24.0
AMB_DEFAULT = {"name": "roomtone", "gain": -34}
WALK_POSES = ("walk", "run", "ready")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry", action="store_true", help="report only, do not write")
    a = ap.parse_args()

    path = os.path.join(a.project, "story", "shots.json")
    st = json.load(open(path, encoding="utf-8"))
    shots = st["shots"]

    added = {"whoosh": 0, "footstep": 0, "riser": 0, "amb": 0}

    for i, s in enumerate(shots):
        cues = s.setdefault("sfx", [])
        has = {c.get("name") for c in cues}
        dur = float(s["end"]) - float(s["start"])
        pos = ((s.get("params") or {}).get("pose") or "").lower()

        # a cut needs a transition sound or the edit reads as a slide change
        if i > 0 and (s.get("in") or {}).get("type", "cut") == "cut" and dur > 0.55:
            if "whoosh" not in has and "swish" not in has:
                cues.append({"at": 0.04, "name": "whoosh", "gain": WHOOSH_GAIN})
                added["whoosh"] += 1

        # a walk with no footsteps is the classic "sliding character" tell
        if any(w in pos for w in WALK_POSES) and dur > 0.8:
            if "footstep" not in has:
                n = max(2, int(dur / 0.30))
                for k in range(n):
                    cues.append({"at": round(0.10 + k * 0.30, 2),
                                 "name": "footstep", "gain": FOOT_GAIN,
                                 "seed": 20 + k})
                added["footstep"] += 1

        # a hard reveal wants a riser in the shot BEFORE it
        if (s.get("in") or {}).get("type") in ("flash", "zoom") and i > 0:
            prev = shots[i - 1]
            pcues = prev.setdefault("sfx", [])
            if not any(c.get("name") == "riser" for c in pcues):
                pdur = float(prev["end"]) - float(prev["start"])
                pcues.append({"at": round(max(0.0, pdur - 0.75), 2),
                              "name": "riser", "gain": RISER_GAIN})
                added["riser"] += 1

        # a tagged impact beat
        if s.get("beat") == "impact" and "hit" not in has:
            cues.append({"at": 0.05, "name": "hit", "gain": -9})
            added["whoosh"] += 0

        cues.sort(key=lambda c: float(c.get("at", 0)))

    # one ambience bed is enough for a single-location piece
    if not any(s.get("amb") for s in shots):
        shots[0]["amb"] = dict(AMB_DEFAULT)
        added["amb"] += 1

    total_cues = sum(len(s.get("sfx") or []) for s in shots)
    print("sound design: %d cues total (+%d whoosh, +%d footstep groups, +%d riser, +%d amb)"
          % (total_cues, added["whoosh"], added["footstep"], added["riser"], added["amb"]))
    for s in shots:
        names = ", ".join("%s@%.2f" % (c["name"], float(c.get("at", 0)))
                          for c in (s.get("sfx") or [])[:5])
        amb = ("  amb=%s" % s["amb"]["name"]) if s.get("amb") else ""
        print("  %-5s %4.2fs  %s%s" % (s["id"], float(s["end"]) - float(s["start"]),
                                       names or "-", amb))

    if not a.dry:
        json.dump(st, open(path, "w", encoding="utf-8"), indent=1)
        print("  wrote", path)


if __name__ == "__main__":
    main()
