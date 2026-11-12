"""fresh.story - concept -> story JSON using the fresh palette.

Produces a director.py-compatible story dict with deterministic visual
distinctness derived from the concept string.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .palette import generate_palette
from .core import Rng, shade_hex
from .audio import derive_music, derive_amb, derive_accent_sfx, mood_for
from .cast import (derive_cast_names, derive_cast_size, derive_heads,
                   derive_body, SERIES_CAST)
from .location import (derive_location, derive_top, derive_roles,
                        derive_prop, derive_style)
from .acting import (derive_pose, derive_gesture, derive_walk,
                     derive_transition)
from .subject import derive_subject


def concept_to_story(concept, series_id=None, episode=None, title=None):
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
    loc = derive_location(theme)
    look = derive_style(theme, loc["set"], loc["mood"])
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
    tops = [derive_top(set_used, r, i)
            for i, r in enumerate(derive_roles(theme, len(names)))]
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
    cast_heads = derive_heads(cast_seed, len(names),
                             allow_none=(len(names) == 1))
    cast = {}
    for i, nm in enumerate(names):
        entry = {"color": colors[i % len(colors)], "top": tops[i % len(tops)],
                 "legs": shade_hex(colors[i % len(colors)], -0.42),
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
        xs = {"a": 0.30, "b": 0.52, "ab": (0.30, 0.52)} if subject_blk else \
             {"a": 0.40, "b": 0.62, "ab": (0.36, 0.68)}
        if b["who"] == "A":
            s.update(who=names[0], x=xs["a"], pose=pose_a, facing=1)
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
                    s.update(who3=names[2], x3=0.10, pose3="stand", facing3=1,
                             scale3=0.94)
                else:
                    s.update(who3=names[2], x3=0.86, pose3="stand", facing3=-1,
                             scale3=0.94)
        # The subject stands in the wide shot, facing the cast. Wide only: at
        # med it would sit behind a single face, and at close it would be a
        # texture rather than a character.
        if subject_blk and b["size"] == "wide":
            s["subject"] = {"kind": subject_blk["kind"], "x": 0.84,
                            "facing": -1, "scale": subject_blk["scale"],
                            "color": creature_color}
        if walk and b["who"] in ("A", "AB"):
            s["walk"] = walk
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
            s["freeze"] = {"at": round(b["hold"] * 0.4, 2)}
            s["sfx"] = [{"at": 0.0, "name": "hit", "gain": -10},
                        {"at": round(b["hold"] * 0.4, 2), "name": "freeze", "gain": -18}]
        elif i == 0:
            s["sfx"] = [{"at": 0.05, "name": "whoosh", "gain": -26}]
        if accent and not accent_done and "set" in s:
            s.setdefault("sfx", []).append({"at": 0.35, "name": accent, "gain": -22})
            accent_done = True
        shots.append(s)

    story = {"title": title, "aspect": "9:16", "resolution": "1080p", "fps": 24,
             "style": style_used, "set": set_used, "chars": "inkbean",
             "cast": cast, "shots": shots, "music": music}
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


def write_story(concept, out_path, series_id=None, episode=None, title=None):
    story = concept_to_story(concept, series_id, episode, title)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(story, fh, indent=1)
    return out_path
