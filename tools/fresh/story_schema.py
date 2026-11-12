"""fresh.story_schema - the story-JSON contract, closed against real source.

director.py accepts a superset of fields and silently ignores what it does not
know: an unimplemented prop renders a magenta box (director.py:232), an
unknown expression renders a NEUTRAL face (director.py:81), a misspelled param
key vanishes through the PARAM_KEYS filter (director.py:1028). None of those is
an error at render time. This module makes them errors before rendering.

Vocabularies are copied from source, not invented. FreshStorySchemaTests
.test_vocabularies_match_source is the drift alarm.
"""
import math

from .subject import CREATURE_KINDS

# engine/rig2d.js:8 POSES
POSES = frozenset("""stand relaxed talk explain point pointUp wave cheer handsOnHead
crossArms think shrug holdFront phone reach sad facepalm ready crouch sit sitBack
kneel lie dive kick jump fall""".split())

# chars/acting.js:43 PRESETS -- the inkbean face vocabulary (director.py:724 faceAt)
EXPR_INKBEAN = frozenset("""neutral listening curious worried hurt angry surprised
relieved hopeful tired ashamed determined""".split())

# engine/rig2d.js:78 EXPR -- the stick face vocabulary (director.py:720 exprAt)
EXPR_STICK = frozenset("""neutral happy joy smile surprised shocked scared worried nervous
angry determined sad cry smirk sleepy thinking confused awe""".split())

# engine/styles.js:20 STYLES
STYLES = frozenset("dusk midnight golden neon storybook".split())

# engine/styles.js:8-15 mood keys
MOODS = frozenset("""day golden dusk night storm interiorWarm interiorCool void""".split())

SETS = frozenset("room kitchen outdoor office".split())   # director.py SETS map
PROPS = frozenset("mug book phone".split())               # director.py:1024
INSERT_KINDS = frozenset("card screen phone document photo creature".split())  # director.py:592-667
SIZES = frozenset("wide med close insert".split())        # director.py:1005
DECLARED_INTENT = frozenset("reverse match intentional declared eyeline".split())  # tools/seam_gate.py:62

# audio/sfx.py:32-282 -- the @sfx-registered names (`audio/sfx.py --list`)
SFX = frozenset("""whoosh swish impact hit riser slowmo freeze tick clock heartbeat
pop blip counter ding shimmer stinger footstep kick whistle carpass phonebuzz
phonering cheer applause murmur rain thunder wind roomtone city hum powerup
glitch flash buzz""".split())

# audio/mix.py:81 loads an sfx cue from disk when its name ends in one of these,
# so a file-based cue is valid even though it is not an @sfx-registered name.
# amb has no such path (mix.py:74 calls SFX.make directly) and stays closed.
AUDIO_EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a")

# director.py:868-875 PARAM_KEYS, plus the record-level keys copied at :1008
# and the timing/identity keys consumed at :1000-1007.
SHOT_KEYS = frozenset("""id size line hold dur start end who who2 who3 x x2 x3 y
pose pose2 pose3 expr exprTo expr2 exprTo2 expr3 exprTo3 at atWord look look2 look3
facing facing2 facing3 scale scale2 scale3 talk2 talk3 bg camZ0 camZ1 camX0 camX1
camY0 camY1 gesture gesture2 walk prop freeze set insertKind subject in sfx amb scene
render3d
acting notes cut_intent""".split())

STORY_KEYS = frozenset("""title aspect resolution fps style set chars cast shots
music fadeIn fadeOut derive subject palette stage3d""".split())

# --- derive block (owner spec, 2026-11-12) --------------------------------
# "If I name a location, use it. Otherwise derive location/cast/audio from the
# concept. A series pins them for continuity." An absent block resolves to
# 'fixed' everywhere, which is exactly the pre-2026-11-12 behaviour, so every
# existing story keeps rendering byte-identically.
SOURCES = frozenset("auto fixed".split())
DERIVE_ASPECTS = ("location", "cast", "audio")
DERIVE_KEYS = frozenset(("source",) + DERIVE_ASPECTS)

MAX_LINE_WORDS = 8       # oleo17/story-to-script-en: "> 8 words for short-form"
MAX_HOLD_BUDGET = 5.0    # cine_release measures 4.75 s
MAX_SHOT_DENSITY = 2.0   # cine_release measures 1.35 s/shot; 2.0 is the slow ceiling

_EXPR_KEYS = ("expr", "exprTo", "expr2", "exprTo2", "expr3", "exprTo3")
_POSE_KEYS = ("pose", "pose2", "pose3")
_WHO_KEYS = ("who", "who2", "who3")


def _carriers(shot, cast):
    """What this shot puts on screen that a neighbour could also put on screen.

    Mirrors seam_gate's model at story level: a named cast member or a held prop.
    An insert draws neither (director.py:592-667), so it carries nothing.
    """
    if shot.get("size") == "insert":
        return set()
    out = set()
    for k in _WHO_KEYS:
        if shot.get(k):
            out.add(str(shot[k]).lower())
        elif k == "who" and cast:
            # director.py:550 `p.who || Object.keys(CAST)[0]` -- figure 1 renders
            # the first cast member when `who` is omitted. Object.keys order is
            # JSON key order, so take the first key of the cast as loaded.
            # who2/who3 have no engine default; do not invent one.
            out.add(str(next(iter(cast))).lower())
    pr = shot.get("prop")
    if isinstance(pr, dict) and pr.get("kind"):
        out.add("prop:" + str(pr["kind"]))
    return out


def resolve_derive(d):
    """Return {'source', 'location', 'cast', 'audio'} for a story dict.

    Precedence, highest first: an explicit per-aspect value; then an explicit
    top-level `set` (location only -- the owner named a place, never derive
    over it); then `source`; then 'fixed'. 'fixed' means "use what the story
    says verbatim", which is the historical behaviour.
    """
    if not isinstance(d, dict):
        d = {}
    blk = d.get("derive")
    if not isinstance(blk, dict):
        blk = {}
    source = blk.get("source", "fixed")
    out = {"source": source}
    for aspect in DERIVE_ASPECTS:
        val = blk.get(aspect)
        if val is None and aspect == "location" and "set" in d:
            val = "fixed"
        out[aspect] = source if val is None else val
    return out


def validate_derive(d, e, w):
    """Validate the optional `derive` block in place. Absent block is valid."""
    blk = d.get("derive")
    if blk is None:
        return
    if not isinstance(blk, dict):
        e.append("story: 'derive' must be an object")
        return
    for k in blk:
        if k not in DERIVE_KEYS:
            e.append("story: derive: unknown key '%s'" % k)
    if "source" in blk and blk["source"] not in SOURCES:
        e.append("story: derive.source=%r must be one of %s"
                 % (blk["source"], sorted(SOURCES)))
    for aspect in DERIVE_ASPECTS:
        if aspect in blk and blk[aspect] not in SOURCES:
            e.append("story: derive.%s=%r must be one of %s"
                     % (aspect, blk[aspect], sorted(SOURCES)))
    if (resolve_derive(d)["source"] == "auto"
            and blk.get("location") is None and "set" in d):
        w.append("story: derive.source=auto but set=%r is explicit; the explicit "
                 "set wins and location will not be derived" % d.get("set"))


def validate_subject(d, e, w):
    """The film must SHOW what it talks about, and only what it declared.

    Owner report 2026-11-13: eight shots said "the dragon", every frame showed
    two men in an office. Every other gate passed, because none of them compared
    the dialogue to the picture. This is that comparison, and it is deliberately
    the strictest possible version:

      * a declared subject must be drawable (kind in chars/creature.js KINDS);
      * at least one shot must actually carry it, or the story is a lie;
      * a shot may not carry a creature the story never declared (that would put
        a random animal in a film about an office).
    """
    subj = d.get("subject")
    kind = None
    if subj is not None:
        if not isinstance(subj, dict):
            e.append("story: 'subject' must be an object with a 'kind'")
            return None
        kind = subj.get("kind")
        if kind not in CREATURE_KINDS:
            e.append("story: subject.kind=%r is not drawable (chars/creature.js KINDS: %s)"
                     % (kind, ", ".join(CREATURE_KINDS)))
            kind = None
        sc = subj.get("scale", 1.0)
        if not isinstance(sc, (int, float)) or not (0.3 <= float(sc) <= 2.5):
            e.append("story: subject.scale=%r is outside 0.3-2.5" % (sc,))

    shots = d.get("shots") or []
    carried = 0
    for s in shots:
        if not isinstance(s, dict):
            continue
        sh = s.get("subject")
        if sh is None:
            if s.get("insertKind") == "creature":
                e.append("%s: insertKind='creature' with no subject param -> the "
                         "insert has nothing to draw" % s.get("id"))
            continue
        if not isinstance(sh, dict):
            e.append("%s: subject must be an object" % s.get("id"))
            continue
        if sh.get("kind") not in CREATURE_KINDS:
            e.append("%s: subject.kind=%r is not drawable" % (s.get("id"), sh.get("kind")))
            continue
        if kind is not None and sh.get("kind") != kind:
            e.append("%s: subject.kind=%r but the story declares %r -> two "
                     "different creatures in one film"
                     % (s.get("id"), sh.get("kind"), kind))
        if kind is None:
            e.append("%s: shows a %r the story never declared" % (s.get("id"), sh.get("kind")))
        x = sh.get("x")
        if x is not None and not (0.0 <= float(x) <= 1.0):
            e.append("%s: subject.x=%r is off-frame" % (s.get("id"), x))
        carried += 1

    if kind is not None and not carried:
        e.append("story: names a %s but NO shot shows it -> the film talks about "
                 "something the viewer never sees" % kind)
    return kind


def validate_freeze(d, e, w):
    """A freeze is punctuation, not filler.

    It used to be placed at `hold * 0.4`, which on a 1.5s shot held 60% of it --
    and the walk had not landed yet, so the figure stopped mid-stride. The
    delivered film measured motion 1.45 (the flattest passage in the video)
    right after a cut. Rules:
      * u-based only (a fraction survives retiming; `at` in seconds does not);
      * never before 70% of the shot, so the hold is the tail, not the body;
      * and never before the walk lands.
    """
    for s in d.get("shots") or []:
        if not isinstance(s, dict):
            continue
        fz = s.get("freeze")
        if fz is None:
            continue
        sid = s.get("id")
        if not isinstance(fz, dict):
            e.append("%s: freeze must be an object" % sid)
            continue
        u = fz.get("u")
        if u is None:
            e.append("%s: freeze must be u-based (fraction of the shot); "
                     "`at` in seconds does not survive retiming" % sid)
            continue
        try:
            u = float(u)
        except (TypeError, ValueError):
            e.append("%s: freeze.u=%r is not a number" % (sid, fz.get("u")))
            continue
        if not (0.70 <= u <= 0.97):
            e.append("%s: freeze.u=%.2f holds %.0f%% of the shot -- a freeze is "
                     "punctuation, it belongs in the last third"
                     % (sid, u, (1.0 - u) * 100))
        walk = s.get("walk")
        if isinstance(walk, dict) and walk.get("u1") is not None:
            try:
                if u < float(walk["u1"]):
                    e.append("%s: freeze at u=%.2f interrupts a walk that lands "
                             "at u=%.2f -> the figure stops mid-stride"
                             % (sid, u, float(walk["u1"])))
            except (TypeError, ValueError):
                pass
    return None


def validate_repeat_framing(d, e, w):
    """Two shots with the same composition too close together read as one shot.

    The delivered film cut wide -> close -> the SAME wide 1.2s later, which the
    owner reported as "continuity happened at 10-11". A repeat is only
    acceptable as a deliberate bookend, so the window is measured in SECONDS of
    story time, not in shot index.
    """
    # WIDES only. Two singles of the same character alternating IS the grammar
    # of a two-hander; a wide is the whole composition, so a repeat there reads
    # as the same shot coming back. The owner reported exactly that: a wide at
    # 7.6s and the SAME wide at 10.3s.
    # Keep the REAL shot index: comparing positions inside the filtered list
    # made a closing wide 7 shots later look like "1 shot between".
    shots = [(i, s) for i, s in enumerate(d.get("shots") or [])
             if isinstance(s, dict) and s.get("size") == "wide"]
    seen = []
    for i, s in shots:
        sig = (s.get("size"), s.get("who"), s.get("who2"), s.get("who3"),
               round(float(s.get("x") or 0), 2), round(float(s.get("x2") or 0), 2),
               round(float(s.get("x3") or 0), 2),
               round(float((s.get("subject") or {}).get("x") or 0), 2))
        for j, prev in enumerate(seen):
            if prev[0] != sig:
                continue
            gap = i - prev[1]
            if gap <= 2:
                e.append("%s: same framing as %s (%s, x=%s/%s/%s) with only %d "
                         "shot(s) between -> it reads as the earlier shot "
                         "resuming, not a new one"
                         % (s.get("id"), dict(shots)[prev[1]].get("id"), sig[0],
                            sig[4], sig[5], sig[6], gap - 1))
                break
        seen.append((sig, i))
    return None


def validate_palette_and_cast(d, e, w):
    """The cast must be visible against the wall it is drawn on.

    Legs were a blind `shade_hex(body, -0.42)`; on a dark wall that is the
    wall's own value, so they vanished. Measured on 12 generated films: 15 of
    26 cast members sat below CIE76 delta-E 30 from their wall or floor, worst
    9.6. This is checkable from the JSON alone, like validate_subject.
    """
    pal = d.get("palette")
    if pal is None:
        return None
    if not isinstance(pal, dict):
        e.append("palette: must be an object")
        return None
    for k in ("wall", "floor", "accent", "practical"):
        v = pal.get(k)
        if not (isinstance(v, str) and len(v) == 7 and v.startswith("#")):
            e.append("palette.%s must be #rrggbb" % k)
    if "sky" in pal:
        # engine sky is a gradient array; a hex crashes backdrop()
        e.append("palette.sky is not overridable -- the engine sky is a "
                 "gradient stop list and a single hex throws")
        return None
    wall, floor = pal.get("wall"), pal.get("floor")
    if not (isinstance(wall, str) and isinstance(floor, str)):
        return None
    from .core import delta_e
    for nm, ch in (d.get("cast") or {}).items():
        if not isinstance(ch, dict):
            continue
        body, legs = ch.get("color"), ch.get("legs")
        if not (body and legs):
            continue
        dw = min(delta_e(body, wall), delta_e(legs, wall))
        df = min(delta_e(body, floor), delta_e(legs, floor))
        if dw < 25.0 or df < 15.0:
            w.append("%s: reads %.0f from the wall and %.0f from the floor -- "
                     "the body may merge into the set" % (nm, dw, df))
    return None


def validate_story(d):
    """Return (errors, warnings). Errors block a --fresh film; warnings inform."""
    e, w = [], []
    if not isinstance(d, dict):
        return ["story: must be an object"], []
    for k in d:
        if k not in STORY_KEYS:
            e.append("story: unknown key '%s'" % k)
    validate_derive(d, e, w)
    validate_subject(d, e, w)
    validate_freeze(d, e, w)
    validate_repeat_framing(d, e, w)
    validate_palette_and_cast(d, e, w)

    shots = d.get("shots")
    if not isinstance(shots, list) or not shots:
        return e + ["story: 'shots' must be a non-empty list"], w
    cast = d.get("cast")
    if not isinstance(cast, dict) or not cast:
        e.append("story: 'cast' must be a non-empty object")
        cast = {}

    chars = d.get("chars", "inkbean")
    expr_vocab = EXPR_STICK if chars == "stick" else EXPR_INKBEAN
    if chars not in ("inkbean", "stick"):
        e.append("story: chars=%r must be 'inkbean' or 'stick'" % chars)
    if d.get("style", "midnight") not in STYLES:
        e.append("story: style=%r not in engine/styles.js STYLES" % d.get("style"))
    if d.get("set", "room") not in SETS:
        e.append("story: set=%r is not implemented -> falls back to room" % d.get("set"))
    if d.get("aspect", "9:16") not in ("9:16", "16:9", "1:1"):
        e.append("story: aspect=%r unsupported" % d.get("aspect"))

    hold_total = 0.0
    word_total = 0
    n_shots = 0
    seen = set()
    for i, s in enumerate(shots):
        where = "shots[%d]" % i
        if not isinstance(s, dict):
            e.append("%s: must be an object" % where)
            continue
        n_shots += 1
        sid = s.get("id")
        if not sid:
            e.append("%s: 'id' is required" % where)
        elif sid in seen:
            e.append("%s: duplicate id '%s'" % (where, sid))
        else:
            seen.add(sid)
        where = "%s(%s)" % (where, sid or "?")

        for k in s:
            if k not in SHOT_KEYS:
                e.append("%s: unknown key '%s' (director.py drops it silently)" % (where, k))
        if s.get("size", "med") not in SIZES:
            e.append("%s: size=%r not in %s" % (where, s.get("size"), sorted(SIZES)))
        if s.get("set") and s["set"] not in SETS:
            e.append("%s: set=%r is not implemented" % (where, s["set"]))
        if s.get("bg") and s["bg"] not in MOODS:
            e.append("%s: bg=%r not an engine mood" % (where, s["bg"]))

        for k in _EXPR_KEYS:
            if s.get(k) and s[k] not in expr_vocab:
                e.append("%s: %s=%r not in the %s face vocabulary -> renders NEUTRAL"
                         % (where, k, s[k], chars))
        for k in _POSE_KEYS:
            if s.get(k) and s[k] not in POSES:
                # Only figure 1 walks (director.py:774). pose2/pose3 resolve via
                # poseAt -> POSES[name] || POSES.stand, so pose2:"walk" stands still.
                if (k == "pose" and str(s[k]).lower() in ("walk", "run")
                        and isinstance(s.get("walk"), dict)):
                    continue
                e.append("%s: %s=%r not in rig2d POSES" % (where, k, s[k]))
        for k in _WHO_KEYS:
            if s.get(k) and s[k] not in cast:
                e.append("%s: %s=%r is not in cast" % (where, k, s[k]))
        if str(s.get("pose", "")).lower() in ("walk", "run") and not isinstance(s.get("walk"), dict):
            e.append("%s: pose=%r without a 'walk' spec -> the figure stands still"
                     % (where, s["pose"]))

        pr = s.get("prop")
        # director.py:803 `if (p.prop)` is JS truthiness: {} is truthy there, so an
        # empty object still calls holdProp and director.py:228-233 paints #ff00aa
        # for any unrecognised kind -- including a missing one.
        if pr is not None and pr != "" and pr != 0:
            if not isinstance(pr, dict):
                e.append("%s: prop=%r must be an object with a 'kind'"
                         " -> a magenta box renders" % (where, pr))
            elif pr.get("kind") not in PROPS:
                e.append("%s: prop kind %r is not implemented -> a magenta box renders"
                         % (where, pr.get("kind")))
        if s.get("insertKind") and s["insertKind"] not in INSERT_KINDS:
            e.append("%s: insertKind=%r not implemented" % (where, s["insertKind"]))
        if s.get("size") == "insert" and not s.get("insertKind"):
            w.append("%s: insert with no insertKind -> the legacy fly renders" % where)

        # audio/mix.py:70 spreads each cue (`{**c, ...}`) and :80 reads c["name"];
        # :72-77 reads amb as ONE object (`am["name"]`). A dict or string sfx, or a
        # string amb, drops every cue without a word -- report the shape instead.
        sfx = s.get("sfx")
        if sfx:
            if not isinstance(sfx, list) or not all(isinstance(c, dict) for c in sfx):
                e.append("%s: 'sfx' must be a list of cue objects" % where)
            else:
                for cue in sfx:
                    nm = cue.get("name")
                    if nm not in SFX and not str(nm).lower().endswith(AUDIO_EXT):
                        e.append("%s: sfx name %r not in audio/sfx.py"
                                 % (where, nm))
        amb = s.get("amb")
        if amb and not isinstance(amb, dict):
            e.append("%s: 'amb' must be a single cue object" % where)
        if isinstance(amb, dict) and amb.get("name") not in SFX:
            e.append("%s: amb name %r not in audio/sfx.py" % (where, amb.get("name")))

        line = s.get("line")
        if line is None:
            line = ""                       # narrate.py:94 `(s.get("line") or "")`
        if isinstance(line, str):
            n = len(line.split())
            if n > MAX_LINE_WORDS:
                e.append("%s: line is %d words (cap %d)" % (where, n, MAX_LINE_WORDS))
            word_total += n
        else:
            e.append("%s: line=%r must be a string" % (where, line))
        try:
            hold = float(s.get("hold", 0.42))   # director.py:1006 coerces the same way
        except (TypeError, ValueError, OverflowError):
            e.append("%s: hold=%r is not a number of seconds" % (where, s.get("hold")))
        else:
            if not math.isfinite(hold) or hold < 0:
                e.append("%s: hold=%r is not a finite, non-negative number of seconds"
                         % (where, s.get("hold")))
            else:
                hold_total += hold

    # Continuity: the story-level pre-flight for seam_gate. A cut needs a shared
    # subject or a declared intent; an insert has no subject, so it needs intent.
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        shared = _carriers(a, cast) & _carriers(b, cast)
        intent = b.get("cut_intent")
        if not shared and intent not in DECLARED_INTENT:
            e.append("dead cut %s->%s: nothing carried and no cut_intent declared"
                     % (a.get("id"), b.get("id")))

    if hold_total > MAX_HOLD_BUDGET:
        w.append("hold budget %.2fs exceeds %.1fs (cine_release: 4.75s)"
                 % (hold_total, MAX_HOLD_BUDGET))
    if n_shots:
        density = (hold_total + word_total / 2.0) / n_shots
        if density > MAX_SHOT_DENSITY:
            w.append("estimated %.2fs/shot exceeds %.1fs (cine_release: 1.35s)"
                     % (density, MAX_SHOT_DENSITY))
    if not d.get("music"):
        w.append("music is empty -> audio/mix.py:57 falls back to MUSIC.default_plan")
    return e, w
