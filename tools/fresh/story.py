"""fresh.story - concept -> story JSON using the fresh palette.

Produces a director.py-compatible story dict with deterministic visual
distinctness derived from the concept string.
"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .palette import generate_palette
from .core import Rng, shade_hex
from .audio import derive_music, derive_amb, derive_accent_sfx, mood_for
from .cast import (derive_cast_names, derive_cast_size, derive_heads,
                   legs_that_read, cast_contrast,
                   derive_body, SERIES_CAST)
from .location import (derive_location, derive_top, derive_roles,
                        derive_prop, derive_style)
from .acting import (derive_pose, derive_gesture, derive_walk,
                     derive_transition)
from .subject import derive_subject, ANIMAL_KINDS
from .stage3d import mark


def concept_to_story(concept, series_id=None, episode=None, title=None, pin=None):
    from .shapes import SHAPES, fill, subject_of, insert_for, prop_for
    from .story_schema import validate_story

    # Series identity is stable across episodes. `series_id` IS the continuity
    # opt-in: the pin lives in the series seed, so there is no flag to forget
    # and no file that can drift out of sync. Before 2026-11-12 only the cast
    # colours came from the series palette, so every episode silently changed
    # location, style and background mood.
    theme = series_id if series_id else concept
    series_seed = series_id if series_id else concept

    # SCREENPLAY ORDER (owner rule 2026-11-13): location first, because the
    # cast, the wardrobe, the props and the sound are all consequences of it.
    # Derived from `theme`, so a series keeps one location across episodes
    # without a flag to forget.
    # Episode 1 of a series is read from its OWN concept: the series ID is a
    # label, and deriving a chef's kitchen from the string "S1" was how a series
    # ended up in an arbitrary room. Later episodes follow the pin instead.
    loc_theme = theme if (isinstance(pin, dict) and pin.get("set")) else concept
    loc = derive_location(loc_theme)
    # A series keeps what episode 1 RESOLVED. `pin` comes from
    # series/<id>.json (fresh/series.pin_path). Without it, a series whose ID
    # contains no location word moves house between episodes, because the ID
    # string is the only thing being read.
    if isinstance(pin, dict) and pin.get("set"):
        loc = {"set": pin["set"], "time": loc.get("time"),
               "mood": pin.get("mood") or loc["mood"], "source": "series"}
    look = (pin.get("style") if isinstance(pin, dict) and pin.get("style")
            else derive_style(loc_theme, loc["set"], loc["mood"]))
    series_pal = (generate_palette(series_seed, series_id, None,
                                   set_name=loc["set"], bg_mood=loc["mood"],
                                   style=look)
                  if series_id else None)
    ep_pal = generate_palette(concept, series_id, episode,
                              set_name=loc["set"], bg_mood=loc["mood"],
                              style=look)
    ident = ep_pal["identity"]
    rng = Rng(ident["seed"] + "|shape")

    if series_id and series_pal is not None:
        sid = series_pal["identity"]
        colors, tops, heads = sid["colors"], sid["tops"], sid["heads"]
        set_used, style_used, mood_used = sid["set"], sid["style"], sid["mood"]
        # sid["mood"] is an ENGINE background mood (night/dusk/...), not a music
        # mood. Mapping it through mood_for is what makes it a legal MUSIC key.
        series_mood = mood_for(theme, sid["mood"])
    else:
        colors, tops, heads = ident["colors"], ident["tops"], ident["heads"]
        set_used, style_used, mood_used = ident["set"], ident["style"], ident["mood"]
        series_mood = None

    # `theme` (set above) is the series identity for a series and the concept
    # for a one-off, so ambience and accents do not drift between episodes.

    if title is None:
        title = concept.strip()[:40] if concept.strip() else "Fresh Story"
    if not title:
        title = "Fresh Story"

    # Series keeps its bible cast (continuity across episodes); a standalone
    # film gets a cast derived from the concept, so two videos do not star the
    # same two people and do not speak the same names.
    if series_id:
        names = list(SERIES_CAST)
    else:
        names = list(derive_cast_names(concept, seed=ident["seed"],
                                       count=derive_cast_size(concept)))
    # Wardrobe follows the role the story names, then the room. `theme` again,
    # so a series does not re-dress its cast between episodes.
    roles = derive_roles(theme, len(names))
    tops = [derive_top(set_used, r, i) for i, r in enumerate(roles)]
    # A cast is a set of DIFFERENT people, not one person recoloured. Until
    # 2026-11-13 the body was colors[i] and the legs colors[(i+1)%2], so the
    # second character was the first with the two colours swapped, and heads
    # could repeat or be "none" for everyone. Each member now gets its own hue,
    # legs as a darker shade of its OWN body, a distinct marker and a silhouette.
    # Seed the appearance from the SERIES when there is one: an episode may
    # change its story, not its characters' faces or silhouettes. Using the
    # episode seed here made the same two people grow and shrink between
    # episodes, which FreshStoryTests caught.
    cast_seed = series_seed if series_id else ident["seed"]
    # The head follows the ROLE, not a three-item draw: a chef gets a toque,
    # a guard a helmet. This is what stops every cast looking like the same
    # three people in caps.
    cast_heads = derive_heads(cast_seed, len(names),
                              allow_none=(len(names) == 1),
                              roles=roles, set_name=set_used)
    # The wall the renderer will actually paint, resolved from the SAME call
    # generate.py makes later, so the two cannot disagree. Legs used to be a
    # blind `shade(body, -0.42)`: on a dark wall that is the wall's own value and
    # the legs vanish (measured: 15 of 26 cast members under delta-E 30 from
    # their wall or floor, worst 9.6).
    try:
        from .sets import generate_set_spec
        _pin_pal = pin.get("palette") if isinstance(pin, dict) else None
        # Episode 1 of a series must resolve the SAME wall later episodes will
        # inherit, so it is drawn from the series seed, not the episode seed.
        # Otherwise ep1 gets a wall the pin then freezes for everyone else.
        _ep = None if (series_id and not _pin_pal) else episode
        _wall = generate_set_spec(theme, series_id, _ep,
                                  set_name=set_used, mood=mood_used,
                                  palette=_pin_pal)["palette"]
    except Exception:
        _wall = {}
    cast = {}
    for i, nm in enumerate(names):
        body = colors[i % len(colors)]
        entry = {"color": body, "top": tops[i % len(tops)],
                 "legs": legs_that_read(body, _wall.get("wall") or body,
                                        _wall.get("floor")),
                 "head": cast_heads[i % len(cast_heads)]}
        if entry["head"] != "none":
            entry["headColor"] = colors[(i + 1) % len(colors)]
        entry.update(derive_body(cast_seed, i))
        cast[nm] = entry

    # Round-robin by episode: consecutive episodes of a series are GUARANTEED to
    # differ in shape, which is what "mini-series episodes" needs. Without an
    # episode number, fall back to the concept seed.
    ordered = sorted(SHAPES)
    if episode is not None:
        shape_name = ordered[(int(episode) - 1) % len(ordered)]
    else:
        shape_name = rng.pick(ordered)
    shape = SHAPES[shape_name]
    subject = subject_of(concept)
    # The SUBJECT is the thing the film is about. `subject_of` already puts the
    # noun in the dialogue; until 2026-11-13 nothing put it on screen, so eight
    # shots said "the dragon" over an empty office. A creature is the only
    # subject the renderer can draw today (chars/creature.js); an abstract noun
    # returns None and the film keeps the insert/prop path rather than inventing
    # an animal for "regret".
    subject_blk = derive_subject(concept, subject)
    # The creature takes the fourth cast colour: the cast can use at most three
    # (A, B, who3), so this hue is always unused and the subject never reads as
    # a recoloured person.
    creature_color = colors[3 % len(colors)]
    insert_kind = "creature" if subject_blk else insert_for(concept)
    # The prop follows the room (3 kinds render), not the insert request alone.
    prop_kind = derive_prop(set_used, insert_kind)
    beats = fill(shape, subject, names[0], names[1])

    # Audio is DERIVED from the concept (owner rule 2026-11-12). Before this,
    # `music: []` always fell through to MUSIC.default_plan() -> mood "mystery"
    # for every film. `narrate.py:159` rescales the plan to the real duration,
    # so an estimate built from the beats' hold values is the right unit here.
    est_total = round(sum(float(b.get("hold", 1.0)) for b in beats), 2)
    music = derive_music(concept, est_total, mood_used, seed=ident["seed"],
                         series_mood=series_mood)
    amb_name = derive_amb(theme, set_used, mood_used)
    accent = derive_accent_sfx(theme)
    accent_done = False

    shots = []
    close_n = 0
    wide_seen = {}
    for i, b in enumerate(beats):
        s = {"id": "s%03d" % (i + 1), "size": b["size"], "hold": b["hold"],
             "line": b["line"] or "", "bg": mood_used, "set": set_used,
             "in": derive_transition(b["role"], i)}
        if b.get("intent"):
            s["cut_intent"] = b["intent"]
        # The BODY acts, from the beat. `pose="stand"` for every character in
        # every shot was the whole performance: only the mouth moved. Poses,
        # word-landed gestures and walks all existed in the renderer and nothing
        # in the story layer ever asked for them.
        pose_a = derive_pose(b["role"], b["line"])
        pose_b = derive_pose(b["role"], b["line"])
        walk = derive_walk(b["role"], b["size"], seed=ident["seed"])
        # Blocking: the subject occupies the right third of a wide frame, so the
        # cast is pulled left to leave it room. Without the shift the second
        # figure stands inside the creature.
        # Three bodies plus a creature do not fit on a 9:16 axis at the old
        # spacing: measured on the first dragon still, the third figure stood
        # inside the first. A subject shifts the cast right and opens a slot.
        # With a subject, the frame is SPLIT: the creature owns the right third
        # and the cast compresses into the left two-thirds. Sharing the axis put
        # the creature's head directly behind a person's head -- on the
        # delivered wide its horns read as growing out of the green figure.
        xs = {"a": 0.16, "b": 0.34, "ab": (0.16, 0.34)} if subject_blk else \
             {"a": 0.40, "b": 0.62, "ab": (0.36, 0.68)}
        if b["who"] == "A":
            # A shape may put two or three `close` beats on role A (countdown:
            # urgency, decision, payoff). Giant faces of the SAME character a
            # few seconds apart read as one shot reused, so a repeated close-up
            # rotates through the cast. With three people every close-up in the
            # film is a different face.
            if b["size"] == "close" and close_n and len(names) > 1:
                who_i = close_n % len(names)
                s.update(who=names[who_i],
                         x=xs["a"] if who_i == 0 else xs["b"],
                         pose=pose_b, facing=1 if who_i == 0 else -1)
            else:
                s.update(who=names[0], x=xs["a"], pose=pose_a, facing=1)
            if b["size"] == "close":
                close_n += 1
            g = derive_gesture(b["role"], b["line"], seed=ident["seed"],
                               size=b["size"])
            # A gesture whose pose IS the base pose animates nothing.
            if g and g["pose"] != pose_a:
                s["gesture"] = g
        elif b["who"] == "B":
            s.update(who=names[1], x=xs["b"], pose=pose_b, facing=-1)
            g = derive_gesture(b["role"], b["line"], seed=ident["seed"] + "|b",
                               size=b["size"])
            if g and g["pose"] != pose_b:
                s["gesture2"] = g
        elif b["who"] == "AB":
            s.update(who=names[0], x=xs["ab"][0], pose=pose_a, facing=1,
                     who2=names[1], x2=xs["ab"][1], pose2=pose_b, facing2=-1)
            # Only ONE of the two gestures: two people pointing at once reads as
            # a chorus, not a conversation.
            g = derive_gesture(b["role"], b["line"], seed=ident["seed"],
                               size=b["size"])
            if g and g["pose"] != pose_a:
                s["gesture"] = g
            # A group story puts the third figure in the wide two-hander. Wide
            # only: at med/close three bodies collide (measured on the office
            # still, where two already hid the desk). With a creature on the
            # right, the third body takes the empty left slot instead of
            # standing inside the creature.
            if len(names) > 2 and b["size"] == "wide":
                if subject_blk:
                    s.update(who3=names[2], x3=0.52, pose3="stand", facing3=1,
                             scale3=0.94)
                else:
                    s.update(who3=names[2], x3=0.86, pose3="stand", facing3=-1,
                             scale3=0.94)
        # A SECOND wide with the same bodies is a shot/reverse-shot, not a
        # repeat. Both wides used the same fixed marks (0.34 / 0.58 / 0.12 and
        # the subject at 0.95), so the film cut wide -> close -> THE SAME WIDE
        # 1.2s later, which reads as the earlier shot resuming. Mirroring the
        # composition on a repeat turns it into a reverse angle for free.
        sig = (b["size"], b["who"])
        # Alternate, do not blanket-mirror: mirroring EVERY repeat made the two
        # later wides identical to each other instead of identical to the first.
        # Odd occurrences keep the master shot, even ones are the reverse.
        mirror = b["size"] == "wide" and wide_seen.get(sig, 0) % 2 == 1
        if b["size"] == "wide":
            wide_seen[sig] = wide_seen.get(sig, 0) + 1
        if mirror:
            for k in ("x", "x2", "x3"):
                if k in s:
                    s[k] = round(1.0 - float(s[k]), 3)
            for k in ("facing", "facing2", "facing3"):
                if k in s:
                    s[k] = -int(s[k])

        # The subject stands in the wide shot, facing the cast. At `med` it is
        # only added when the LINE NAMES IT: "It's only a dragon, COLE" over a
        # frame with no dragon is the exact defect script_frame_check.py now
        # fails on. A pronoun ("Don't touch it") stays on the face, because that
        # is a reaction, not a reference.
        names_it = bool(subject_blk) and re.search(
            r"\b" + re.escape(subject_blk["noun"]) + r"\b",
            (b["line"] or "").lower()) is not None
        if subject_blk and (b["size"] == "wide" or (b["size"] == "med" and names_it)):
            # In a WIDE the subject is a FOREGROUND element: larger, lower and
            # cropped by the right edge, drawn in front of the cast. Standing it
            # between two people at character size made a dragon read as a pet
            # (measured: 90px tall next to 300px people). In a MED it stays a
            # background body, small, because the frame belongs to the face.
            wide = b["size"] == "wide"
            # Only an ANIMAL gets the foreground treatment; an object keeps
            # character scale, because a jar the size of a wall is a wall.
            loom = wide and subject_blk["kind"] in ANIMAL_KINDS
            # An animal looms at the edge and may be cropped; an object must sit
            # fully inside the frame or it reads as scenery.
            s["subject"] = {"kind": subject_blk["kind"],
                            "x": (0.90 if loom else 0.82) if wide else 0.86,
                            "facing": -1,
                            "scale": subject_blk["scale"] * (1.0 if wide else 0.8),
                            "color": creature_color}
            if loom:
                # Staged BEHIND the cast: `front` put a 2.3x quadruped on top of
                # three people. Kept as a marker so the intent is still readable
                # in the JSON, but the renderer no longer honours it for depth.
                s["subject"]["behind"] = True
            if mirror:
                # The cast was flipped for this shot, so the subject flips too:
                # it must stay on the side the camera is looking from. Clamped:
                # a literal 1-x put the foreground creature at x=0.05, where the
                # body falls outside the frame and only the neck and one leg
                # remain (measured on the mirrored wide). 0.14 keeps the mass.
                s["subject"]["x"] = round(
                    min(0.88, max(0.12, 1.0 - float(s["subject"]["x"]))), 3)
                s["subject"]["facing"] = 1
        if walk and b["who"] in ("A", "AB"):
            # A walk's from/to were absolute (0.13 -> 0.40) and ignored the
            # blocking, so a figure assigned x=0.34 walked to 0.40 and landed on
            # top of the character at 0.58. Measured: COLE's torso disappeared
            # behind NORA and only one green leg showed, which is what
            # script_frame_check.py reported as "COLE speaks but their colour is
            # absent". Re-anchor the travel so it ENDS on the assigned mark and
            # keeps its length.
            w = dict(walk)
            end = float(s.get("x", 0.40))
            d = abs(float(w["to"]) - float(w["from"])) or 0.18
            # Direction follows FACING. A mirrored shot faces -1, so anchoring
            # `from` below `to` made the figure walk right while facing left --
            # a moonwalk, which the mirror introduced.
            if int(s.get("facing", 1)) < 0:
                w["to"] = round(min(0.92, max(0.08, end)), 3)
                w["from"] = round(min(0.92, max(0.08, w["to"] + d)), 3)
            else:
                w["to"] = round(min(0.92, max(0.08, end)), 3)
                w["from"] = round(min(0.92, max(0.08, w["to"] - d)), 3)
            # The path must not pass THROUGH somebody. A group film puts the
            # third figure at x3=0.12, and YARA's walk started at 0.088 and
            # walked straight through her: measured on the first still, two
            # bodies merged into one blob at the left edge. Start on the near
            # side of the nearest blocker instead, and drop a walk too short to
            # read.
            lo, hi = sorted((w["from"], w["to"]))
            others = [float(s[k]) for k in ("x2", "x3") if s.get(k) is not None]
            for o in others:
                # Crossing, OR starting inside another body: a mirrored wide
                # began YARA's walk 0.09 from the third figure, which overlaps
                # at this scale even though the path never crosses her.
                if abs(o - w["to"]) <= 0.06:
                    continue
                if lo - 0.02 <= o <= hi + 0.02 or abs(w["from"] - o) < 0.13:
                    if w["to"] > o:
                        lo = max(lo, o + 0.15)
                    else:
                        hi = min(hi, o - 0.15)
            if hi - lo >= 0.07:
                w["from"], w["to"] = (round(lo, 3), round(hi, 3)) \
                    if w["to"] > w["from"] else (round(hi, 3), round(lo, 3))
                s["walk"] = w
            else:
                s.pop("walk", None)
        if b.get("expr"):
            s["expr"] = b["expr"]
        if b.get("exprTo"):
            s["exprTo"] = b["exprTo"]
            s["at"] = round(b["hold"] + 0.35, 2)
        if b.get("insert"):
            s["insertKind"] = insert_kind
            s.pop("bg", None)
            s.pop("set", None)
            # The insert is where the viewer gets to SEE the subject. Without
            # this param the creature insert branch has nothing to draw and the
            # old beetle returns.
            if subject_blk:
                s["subject"] = {"kind": subject_blk["kind"], "x": 0.5,
                                "facing": -1, "scale": subject_blk["scale"],
                                "color": creature_color}
        else:
            # an insert draws no set, so it must not carry a room bed either
            s["amb"] = {"name": amb_name, "gain": -26}
        if b.get("prop"):
            s["prop"] = {"kind": prop_kind}
        if b.get("freeze"):
            # The freeze is a PUNCTUATION device: the picture holds on the hit.
            # It used to sit at `hold * 0.4` = 0.6s of a 1.5s shot, so 60% of the
            # shot was a held frame -- and the walk (u1=0.82) had not landed yet,
            # so the figure stopped mid-stride and the shot died. Measured on the
            # delivered film: motion 1.45 at 7.9-9.0s, the flattest passage in
            # the whole video, immediately after a cut.
            #
            # Now: u-based (survives retiming), placed AFTER the walk lands, so
            # the hold is the last ~15% of the shot and it lands on a completed
            # action instead of interrupting one.
            fz = 0.86
            if isinstance(walk, dict):
                fz = max(fz, round(min(0.92, float(walk["u1"]) + 0.04), 3))
            s["freeze"] = {"u": fz}
            s["sfx"] = [{"at": 0.0, "name": "hit", "gain": -10},
                        {"u": fz, "name": "freeze", "gain": -18}]
        elif i == 0:
            s["sfx"] = [{"at": 0.05, "name": "whoosh", "gain": -26}]
        if accent and not accent_done and "set" in s:
            s.setdefault("sfx", []).append({"at": 0.35, "name": accent, "gain": -22})
            accent_done = True
        shots.append(s)

    # Which beats are staged in 3D. Only line-less wides: three-kit's figure3D
    # draws eyes and no mouth, so a talking beat cannot be 3D without losing the
    # lip-sync the 2D pipeline spent this session getting right.
    stage3d_ids = mark(shots)

    story = {"title": title, "aspect": "9:16", "resolution": "1080p", "fps": 24,
             "style": style_used, "set": set_used, "chars": "inkbean",
             "cast": cast, "shots": shots, "music": music}
    if stage3d_ids:
        story["stage3d"] = list(stage3d_ids)
    if _wall:
        # The story now carries the colours it will be painted with, so a
        # readability check needs no second derivation, and the series pin has
        # something to freeze.
        story["palette"] = {k: v for k, v in _wall.items() if k != "dark"}
    if subject_blk:
        # Story-level declaration: the picture and the dialogue now name the
        # same thing, and validate_story refuses a film that names a creature
        # and never shows it.
        story["subject"] = {"kind": subject_blk["kind"],
                            "scale": subject_blk["scale"],
                            "noun": subject_blk["noun"],
                            "color": creature_color}
    errs, _ = validate_story(story)
    if errs:
        raise ValueError("fresh story violates the contract: " + "; ".join(errs))
    return story


def write_story(concept, out_path, series_id=None, episode=None, title=None, pin=None):
    story = concept_to_story(concept, series_id, episode, title, pin=pin)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(story, fh, indent=1)
    return out_path
