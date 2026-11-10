#!/usr/bin/env python3
"""
prose_to_manifest.py — SLICE-10: plain prose -> schema-valid story.json (text-in/film-out).

Deterministic mini-grammar (no LLM, fully testable). One non-empty line = one beat = one shot.

  # comment
  Title: The Mug                       -> story title
  Set: kitchen | room                  -> story set (default room)
  Cast: MIRA #2f9e8f bob, JAY #c2553d glasses   -> cast (optional; actors are discovered from
                                      "NAME says:" / "NAME holds|takes|reaches ..." otherwise,
                                      colours from a default palette)
  Voices: MIRA=af_heart, JAY=am_adam    -> story voices (Kokoro ids; default af_heart/am_adam/...)

  [wide|med|close|insert] optional shot-size tag (default med)
  NAME says: <text>                    -> dialogue shot (line + speaker); dur sized from words
  NAME and NAME2 ...                   -> `who` = names mentioned in the sentence
  NAME holds the <mug|book|phone>      -> prop created/kept, holder = NAME
  NAME takes the <prop>                -> ON-SCREEN transfer in this shot: prop.who=NAME,
                                          prop.from=previous holder, prop.at=0.65
  NAME reaches for the <prop>         -> that figure's pose = reachLow (aims at the prop)
  ... for N seconds                    -> explicit dur (silent beats)

Output is validated with tools/story_schema.validate_story before anything is written.

  python tools/prose_to_manifest.py --prose examples/quality-benchmark/prose_mug.txt \
      --out build/quality/prose/story.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from story_schema import validate_story

PROP_WORDS = {"mug": "mug", "book": "book", "phone": "phone"}
PROP_COLOR = {"mug": "#8a6f4d", "book": "#b8452f", "phone": "#3a3f4a"}
PALETTE = ["#2f9e8f", "#c2553d", "#8f6fc2", "#c2a13d", "#4d7fc2", "#c25d8f"]
MARKERS = ["bob", "glasses", "bun", "cap", "band", "earring"]
DEFAULT_VOICES = ["af_heart", "am_adam", "af_bella", "am_eric", "bf_emma", "bm_george"]

SAY = re.compile(r"^([A-Z][A-Za-z0-9_]*)\s+says?\s*:\s*(.+)$")
HOLDS = re.compile(r"^([A-Z][A-Za-z0-9_]*)\s+(?:holds|is holding|carries)\s+(?:the\s+)?(\w+)", re.I)
TAKES = re.compile(r"^([A-Z][A-Za-z0-9_]*)\s+(?:takes|grabs|takes over)\s+(?:the\s+)?(\w+)", re.I)
REACH = re.compile(r"^([A-Z][A-Za-z0-9_]*)\s+reaches?\s+for\s+(?:the\s+)?(\w+)", re.I)
SIZE_TAG = re.compile(r"^\[(wide|med|close|insert)\]\s*(.*)$", re.I)
DUR_FOR = re.compile(r"^(.*?)\s+for\s+([0-9.]+)\s*(?:s|sec|seconds)?\s*$", re.I)
HEADER = re.compile(r"^(Title|Set|Cast|Voices)\s*:\s*(.+)$", re.I)
CAST_ITEM = re.compile(r"([A-Z][A-Za-z0-9_]*)(?:\s+#([0-9a-fA-F]{6}))?(?:\s+(\w+))?")
SKIP_WORDS = {"THE", "AND", "FOR", "A", "AN", "AT", "IN", "ON", "STANDS", "STAND"}


def prop_kind(word):
    return PROP_WORDS.get(word.lower().strip(".,!?"))


def names_in(text, cast):
    out = []
    for w in re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", text):
        if w not in SKIP_WORDS and w in cast and w not in out:
            out.append(w)
    return out


def parse_prose(text):
    title, set_name, cast, voices = "Untitled scene", "room", {}, {}
    beats = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = HEADER.match(line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "title":
                title = val
            elif key == "set":
                set_name = val.lower()
                if set_name not in ("room", "kitchen"):
                    raise SystemExit(f"Set: unknown set {set_name!r} (room|kitchen)")
            elif key == "cast":
                for item in val.split(","):
                    cm = CAST_ITEM.match(item.strip())
                    if not cm:
                        raise SystemExit(f"Cast: cannot parse {item!r}")
                    name, color, marker = cm.group(1), cm.group(2), cm.group(3)
                    cast[name] = {"color": "#" + color if color else PALETTE[len(cast) % len(PALETTE)],
                                  "marker": marker or MARKERS[len(cast) % len(MARKERS)],
                                  "top": "tshirt", "legs": "#243244"}
            elif key == "voices":
                for part in val.split(","):
                    who, _, v = part.partition("=")
                    voices[who.strip()] = v.strip()
            continue
        beats.append(line)
    if not beats:
        raise SystemExit("no beats found in prose")

    # discover actors from the beats when there is no Cast: header
    for b in beats:
        for rx in (SAY, HOLDS, TAKES, REACH):
            m = rx.match(b)
            if m and m.group(1) not in cast:
                cast[m.group(1)] = {"color": PALETTE[len(cast) % len(PALETTE)],
                                    "marker": MARKERS[len(cast) % len(MARKERS)],
                                    "top": "tshirt", "legs": "#243244"}
    for name in names_in(" ".join(beats), {k: 1 for k in cast}):
        pass  # names_in already covered via regex below
    for b in beats:
        for n in names_in(b, cast):
            pass
    if not cast:
        raise SystemExit("no cast: add a 'Cast:' header or use 'NAME says: ...'")
    names = list(cast)
    for i, name in enumerate(names):
        voices.setdefault(name, DEFAULT_VOICES[i % len(DEFAULT_VOICES)])

    shots = []
    prop = None          # {"kind","who","color"} — the object currently in play
    for i, b in enumerate(beats):
        size, body = "med", b
        m = SIZE_TAG.match(body)
        if m:
            size, body = m.group(1).lower(), m.group(2).strip()
        dur = None
        m = DUR_FOR.match(body)
        if m:
            body, dur = m.group(1).strip(), float(m.group(2))

        sm, hm, tm, rm = SAY.match(body), HOLDS.match(body), TAKES.match(body), REACH.match(body)
        who, pose, line, speaker = [], [], "", None
        shot_prop = None

        if sm:
            speaker, line = sm.group(1), sm.group(2).strip()
            who = [speaker]
            pose = ["talk"]
            if len(names) > 1:
                who.append(next(n for n in names if n != speaker))
                pose.append("relaxed" if i % 2 else "stand")
        elif tm and prop_kind(tm.group(2)):
            kind = prop_kind(tm.group(2))
            taker = tm.group(1)
            prev = prop["who"] if prop and prop["kind"] == kind else None
            prop = {"kind": kind, "who": taker, "color": PROP_COLOR[kind]}
            shot_prop = {"kind": kind, "who": taker, "color": PROP_COLOR[kind]}
            if prev and prev != taker:
                shot_prop["from"] = prev
                shot_prop["at"] = 0.65
            who = [taker] + ([prev] if prev and prev != taker else []) + [n for n in names if n not in (taker, prev)][:2]
            who = who[:2]
            pose = ["reachLow"] + ["holdFront"] * (len(who) - 1)
            if size == "close":
                size = "med"
        elif hm and prop_kind(hm.group(2)):
            kind = prop_kind(hm.group(2))
            holder = hm.group(1)
            prop = {"kind": kind, "who": holder, "color": PROP_COLOR[kind]}
            shot_prop = dict(prop)
            who = [holder] + [n for n in names if n != holder][:1]
            pose = ["holdFront"] + ["stand"] * (len(who) - 1)
        elif rm and prop_kind(rm.group(2)):
            who = [rm.group(1)] + ([prop["who"]] if prop and prop["who"] != rm.group(1) else [])
            who += [n for n in names if n not in who][:2 - len(who)]
            pose = ["reachLow"] + ["holdFront"] * (len(who) - 1)
            shot_prop = dict(prop) if prop else None
        else:
            who = names_in(body, cast)[:2] or names[:1]
            pose = ["relaxed" if i % 2 else "stand"] * len(who)
            shot_prop = dict(prop) if prop else None
        if size == "insert":
            who, pose = [], []
            shot_prop = dict(prop) if prop else shot_prop

        if dur is None:
            words = len(line.split()) if line else 0
            dur = max(1.4, 0.5 * words + 0.5) if line else 1.2

        # size-based shots take LEGACY TOP-LEVEL fields (director lifts them into params at
        # compile): scalar who/who2 + pose/pose2, not arrays. EXCEPT insert: the size-'insert'
        # path in director's generated scenes draws a decorative fly and never the prop, so
        # insert beats must use the proven 'insert-object' TEMPLATE (benchmark b04 path).
        if size == "insert":
            shot = {"id": f"s{i+1:02d}", "template": "insert-object", "dur": round(dur, 2),
                    "params": {"object": {"kind": prop["kind"], "color": prop["color"]} if prop else {"kind": "mug"},
                               "x": 0.5, "y": 0.44, "bg": "night", "set": set_name}}
        else:
            shot = {"id": f"s{i+1:02d}", "size": size, "dur": round(dur, 2),
                    "bg": "night", "set": set_name}
        if size != "insert":
            if who:
                shot["who"] = who[0]
                if len(who) > 1:
                    shot["who2"] = who[1]
            if pose:
                shot["pose"] = pose[0]
                if len(pose) > 1:
                    shot["pose2"] = pose[1]
        if line:
            shot["line"] = line
            shot["speaker"] = speaker
        if shot_prop:
            shot["prop"] = shot_prop
        shots.append(shot)

    total = round(sum(s["dur"] for s in shots), 2)
    return {"title": title, "aspect": "9:16", "resolution": "720p", "fps": 24,
            "style": "midnight", "chars": "inkbean", "set": set_name,
            "purpose": "Generated from prose by tools/prose_to_manifest.py",
            "cast": cast, "music": [{"start": 0, "end": total, "mood": "sad", "intensity": 0.3}],
            "voices": voices, "shots": shots}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prose", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    story = parse_prose(Path(a.prose).read_text(encoding="utf-8"))
    errors, warnings = validate_story(story)
    for w in warnings:
        print("WARNING:", w)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(f"{len(errors)} schema error(s) — nothing written")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(story, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    nd = sum(1 for s in story["shots"] if s.get("line"))
    print(f"OK: {len(story['shots'])} shots, {nd} dialogue, "
          f"{sum(1 for s in story['shots'] if s.get('prop'))} prop shots, "
          f"total {sum(s['dur'] for s in story['shots']):.1f}s -> {out}")
    for s in story["shots"]:
        print(f"  {s['id']} {s.get('size') or s.get('template'):<14} {s['dur']:>4.2f}s who={s.get('who')}/{s.get('who2')} "
              f"pose={s.get('pose')}/{s.get('pose2')} prop={s.get('prop')} line={s.get('line', '')!r} spk={s.get('speaker')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
