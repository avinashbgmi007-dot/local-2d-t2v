"""Closed story/template vocabulary shared by the compiler and its tests.

Engine enums are mirrored here; tests/test_repository.py checks the mirrors against
the actual JS exports so they cannot quietly drift. No browser/Node needed to compile.
"""
import json
import math
import re
from pathlib import Path

POSES = set("stand relaxed talk explain point pointUp wave cheer handsOnHead crossArms think shrug holdFront phone reach reachLow sad facepalm ready crouch sit sitBack kneel lie dive kick jump fall".split())
EXPRESSIONS = set("neutral happy joy smile surprised shocked scared worried nervous angry determined sad cry smirk sleepy thinking confused awe".split())
FACES = set("neutral listening curious worried hurt angry surprised relieved hopeful tired ashamed determined".split())
MOODS = set("day golden dusk night storm interiorWarm interiorCool void".split())
STYLES = set("dusk midnight golden neon storybook".split())
MUSIC_MOODS = set("mystery tension action wonder hopeful sad triumph playful calm dark epic".split())
SFX = set("whoosh swish impact hit riser slowmo freeze tick clock heartbeat pop blip counter ding shimmer stinger footstep kick whistle carpass phonebuzz phonering cheer applause murmur rain thunder wind roomtone city hum powerup glitch flash buzz".split())
TRANSITIONS = set("cut fade dip dipWhite flash whip zoom".split())
SIZES = set("wide med close insert".split())
PROP_KINDS = set("mug book phone".split())
PROP_KEYS = set("kind who color hand scale tilt".split())
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
CAST_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
RESERVED = set("break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof new return super switch this throw try typeof var void while with yield let static enum await implements package protected interface private public".split())
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "templates/registry.json").read_text(encoding="utf-8"))["templates"]


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def bounded(v, lo, hi):
    return num(v) and lo <= v <= hi


def pair(v, lo, hi):
    return isinstance(v, list) and len(v) == 2 and all(bounded(x, lo, hi) for x in v)


def strings(v, limit, length):
    return isinstance(v, list) and 1 <= len(v) <= limit and all(isinstance(x, str) and 0 < len(x.strip()) <= length for x in v)


def validate_template(name, p, cast, inkbean):
    if name not in REGISTRY:
        return [f"unknown template {name!r}"]
    if not isinstance(p, dict):
        return ["params must be an object"]
    errors = []
    allowed = set(REGISTRY[name]["params"])
    for key in sorted(set(p) - allowed):
        errors.append(f"{name}: unknown param {key!r}")
    faces = FACES if inkbean else EXPRESSIONS
    for key in ("who", "pose", "expr"):
        if key not in p:
            continue
        values = p[key] if isinstance(p[key], list) else [p[key]]
        vocab = cast if key == "who" else POSES if key == "pose" else faces
        if not values or len(values) > (4 if key == "who" else 3):
            errors.append(f"{key}: wrong number of values")
        for value in values:
            if not isinstance(value, str) or value not in vocab:
                errors.append(f"{key}: unknown value {value!r}")
    checks = {
        "push": lambda v: pair(v, .5, 2), "orbit": lambda v: pair(v, -6.3, 6.3),
        "x": lambda v: bounded(v, 0, 1) or pair(v, 0, 1),
        "y": lambda v: bounded(v, 0, 1), "scale": lambda v: bounded(v, .2, 3),
        "drift_x": lambda v: bounded(v, -300, 300), "at": lambda v: bounded(v, 0, 3600),
        "freeze_at": lambda v: bounded(v, 0, 1), "direction": lambda v: v in (-1, 1),
        "side": lambda v: v in ("left", "right"), "bg": lambda v: v in MOODS,
        "mood": lambda v: v in MOODS, "set": lambda v: v in ("room", "kitchen"),
        "facing": lambda v: v in (-1, 1) or (isinstance(v, list) and len(v) == 2 and all(x in (-1, 1) for x in v)),
        "look": lambda v: pair(v, -1, 1), "exprTo": lambda v: v in faces,
        "atWord": lambda v: isinstance(v, str) and 0 < len(v) <= 80,
        "labels": lambda v: strings(v, 4, 24), "lines": lambda v: strings(v, 3, 32),
        "title": lambda v: isinstance(v, str) and 0 < len(v) <= 60,
        "fact": lambda v: isinstance(v, str) and 0 < len(v) <= 60,
        "sub": lambda v: isinstance(v, str) and 0 < len(v) <= 60,
        "question": lambda v: isinstance(v, str) and 0 < len(v) <= 60,
        "attribution": lambda v: isinstance(v, str) and 0 < len(v) <= 80,
        "badge": lambda v: isinstance(v, str) and 0 < len(v) <= 16,
        "object": lambda v: isinstance(v, dict) and set(v) <= {"kind", "color", "scale", "tilt"} and v.get("kind", "mug") in ("mug", "book", "phone") and ("scale" not in v or bounded(v["scale"], .2, 3)) and ("tilt" not in v or bounded(v["tilt"], -3.14, 3.14)),
    }
    for key, value in p.items():
        if key in checks and not checks[key](value):
            errors.append(f"{name}.{key}: invalid value {value!r}")
    if name == "medium-two-shot" and "who" in p and (not isinstance(p["who"], list) or len(p["who"]) != 2):
        errors.append("medium-two-shot requires exactly two cast ids")
    if name == "over-shoulder" and len(cast) < 2:
        errors.append("over-shoulder requires two cast ids")
    return errors


def validate_story(story):
    """Validate before any output is touched. Returns (errors, warnings)."""
    if not isinstance(story, dict):
        return ["story must be an object"], []
    errors, warnings = [], []
    cast = story.get("cast")
    if not isinstance(cast, dict) or not cast:
        return ["cast must be a non-empty object"], []
    for name, outfit in cast.items():
        if not CAST_ID.fullmatch(name) or name in RESERVED or name == "CAST":
            errors.append(f"unsafe/reserved cast id {name!r}")
        if not isinstance(outfit, dict):
            errors.append(f"cast {name} must be an object")
    for key, vocab in [("aspect", {"16:9", "9:16"}), ("style", STYLES), ("set", {"room", "kitchen"}), ("chars", {"stick", "inkbean"}), ("resolution", {"720p", "1080p", "1440p", "2160p", "4k"})]:
        if key in story and story[key] not in vocab:
            errors.append(f"unknown {key} {story[key]!r}")
    if "fps" in story and (not bounded(story["fps"], 1, 240) or int(story["fps"]) != story["fps"]):
        errors.append("fps must be an integer in 1..240")
    # per-speaker casting. Keys are cast ids (or NARRATOR); values are opaque voice
    # ids for whichever TTS backend is configured, so the vocabulary stays open.
    voices = story.get("voices")
    if voices is not None:
        if not isinstance(voices, dict):
            errors.append("voices must be an object of {speaker: voice id}")
        else:
            for who, voice in voices.items():
                if who != "NARRATOR" and who not in cast:
                    errors.append(f"voices: unknown speaker {who!r}")
                if not isinstance(voice, str) or not 0 < len(voice.strip()) <= 120:
                    errors.append(f"voices[{who}]: voice id must be a non-empty string")
    shots = story.get("shots")
    if not isinstance(shots, list) or not shots:
        return errors + ["shots must be a non-empty list"], warnings
    inkbean = story.get("chars", "stick") == "inkbean"
    seen, cursor = set(), 0.0
    for i, s in enumerate(shots):
        if not isinstance(s, dict):
            errors.append(f"shots[{i}] must be an object"); continue
        sid = s.get("id")
        if not isinstance(sid, str) or not ID.fullmatch(sid) or sid in seen:
            errors.append(f"shots[{i}]: missing/unsafe/duplicate id")
        else:
            seen.add(sid)
        label = sid if isinstance(sid, str) else str(i)
        if "dur" in s and not bounded(s["dur"], .001, 3600):
            errors.append(f"{label}: dur must be positive")
        start = s.get("start", cursor)
        end = s.get("end", start + s.get("dur", 3)) if num(start) else None
        if not num(start) or not num(end) or start < 0 or end <= start:
            errors.append(f"{label}: invalid start/end"); continue
        if abs(start - cursor) > .002:
            errors.append(f"{label}: gap/overlap at {start}")
        cursor = end
        if "hold" in s and not bounded(s["hold"], 0, 3600):
            errors.append(f"{label}: invalid hold")
        if "line" in s and not isinstance(s["line"], str):
            errors.append(f"{label}: line must be a string")
        # Dialogue is cast, not implied. `speaker` is the id whose mouth may move;
        # null/absent means nobody speaks in this shot (or legacy first-figure).
        if "speaker" in s and s["speaker"] is not None:
            sp = s["speaker"]
            if not isinstance(sp, str) or (sp != "NARRATOR" and sp not in cast):
                errors.append(f"{label}: unknown speaker {sp!r}")
        # A prop belongs to a PERSON, not to a shot. Declaring the holder at shot
        # level lets continuity be checked across cuts and works for every template.
        if "prop" in s and s["prop"] is not None:
            pr = s["prop"]
            if not isinstance(pr, dict):
                errors.append(f"{label}: prop must be an object")
            else:
                if pr.get("kind") not in PROP_KINDS:
                    errors.append(f"{label}: unknown prop kind {pr.get('kind')!r}")
                for key in sorted(set(pr) - PROP_KEYS):
                    errors.append(f"{label}: unknown prop field {key!r}")
                if pr.get("who") is not None and pr["who"] not in cast:
                    errors.append(f"{label}: unknown prop holder {pr['who']!r}")
                if not pr.get("who"):
                    warnings.append(f"{label}: prop has no holder; contact cannot be verified")
                if "hand" in pr and pr["hand"] not in ("front", "back"):
                    errors.append(f"{label}: prop.hand must be front or back")
                if "scale" in pr and not bounded(pr["scale"], .2, 3):
                    errors.append(f"{label}: prop.scale out of range")
                if "tilt" in pr and not bounded(pr["tilt"], -3.14, 3.14):
                    errors.append(f"{label}: prop.tilt out of range")
                if "color" in pr and not (isinstance(pr["color"], str)
                                         and re.fullmatch(r"#[0-9a-fA-F]{6}", pr["color"])):
                    errors.append(f"{label}: prop.color must be #rrggbb")
        said = isinstance(s.get("line"), str) and s["line"].strip()
        if said and not s.get("speaker"):
            warnings.append(f"{label}: line has no speaker; mouth falls back to the first figure")
        if s.get("speaker") and not said:
            warnings.append(f"{label}: speaker {s['speaker']} has no line to say")
        if "template" in s:
            if "size" in s:
                errors.append(f"{label}: use template OR size, not both")
            errors += [f"{label}: {e}" for e in validate_template(s["template"], s.get("params", {}), cast, inkbean)]
        else:
            if s.get("size", "med") not in SIZES:
                errors.append(f"{label}: unknown size {s.get('size')!r}")
            if "params" in s:
                errors.append(f"{label}: params requires template (legacy fields are top-level)")
            for key in ("pose", "pose2", "pose3"):
                if key in s and s[key] not in POSES and not (s[key] == "walk" and isinstance(s.get("walk"), dict)):
                    errors.append(f"{label}: unknown {key} {s[key]!r}")
            for key in ("expr", "expr2", "expr3", "exprTo", "exprTo2", "exprTo3"):
                if key in s and s[key] not in EXPRESSIONS:
                    errors.append(f"{label}: unknown {key} {s[key]!r}")
                elif key in s and inkbean and s[key] not in FACES:
                    warnings.append(f"{label}: {s[key]} is a stick-face name; inkbean uses neutral")
            for key in ("who", "who2", "who3"):
                if key in s and s[key] not in cast:
                    errors.append(f"{label}: unknown cast {s[key]!r}")
            if "bg" in s and s["bg"] not in MOODS:
                errors.append(f"{label}: unknown mood {s['bg']!r}")
            if "set" in s and s["set"] not in {"room", "kitchen"}:
                errors.append(f"{label}: unknown set {s['set']!r}")
        tr = s.get("in", {"type": "cut"})
        if not isinstance(tr, dict) or tr.get("type", "cut") not in TRANSITIONS or ("dur" in tr and not bounded(tr["dur"], .001, 60)):
            errors.append(f"{label}: invalid transition")
        for cue in s.get("sfx", []) if isinstance(s.get("sfx", []), list) else []:
            if not isinstance(cue, dict) or cue.get("name") not in SFX or not bounded(cue.get("at", 0), 0, end - start):
                errors.append(f"{label}: invalid SFX cue")
        if "sfx" in s and not isinstance(s["sfx"], list):
            errors.append(f"{label}: sfx must be cue objects, not names")
        amb = s.get("amb")
        if amb is not None and (not isinstance(amb, dict) or amb.get("name") not in SFX):
            errors.append(f"{label}: unknown ambience")
    music = story.get("music", [])
    if not isinstance(music, list):
        errors.append("music must be a list")
    else:
        for m in music:
            if not isinstance(m, dict) or m.get("mood") not in MUSIC_MOODS or not num(m.get("start")) or not num(m.get("end")) or m["start"] < 0 or m["end"] <= m["start"] or m["end"] > cursor + .002 or not bounded(m.get("intensity", .5), 0, 1):
                errors.append("invalid music cue")
    return errors, warnings
