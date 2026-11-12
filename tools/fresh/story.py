"""fresh.story - concept -> story JSON using the fresh palette.

Produces a director.py-compatible story dict with deterministic visual
distinctness derived from the concept string.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .palette import generate_palette
from .core import Rng
from .audio import derive_music, derive_amb, derive_accent_sfx, mood_for
from .cast import derive_cast_names, derive_cast_size, SERIES_CAST
from .location import (derive_location, derive_top, derive_roles,
                        derive_prop)


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
    series_pal = (generate_palette(series_seed, series_id, None,
                                   set_name=loc["set"], bg_mood=loc["mood"])
                  if series_id else None)
    ep_pal = generate_palette(concept, series_id, episode,
                              set_name=loc["set"], bg_mood=loc["mood"])
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
    cast = {}
    for i, nm in enumerate(names):
        entry = {"color": colors[i % len(colors)], "top": tops[i % len(tops)],
                 "legs": colors[(i + 1) % len(colors)], "head": heads[i % len(heads)]}
        if entry["head"] != "none":
            entry["headColor"] = colors[(i + 1) % len(colors)]
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
    insert_kind = insert_for(concept)
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
             "in": {"type": "cut"}}
        if i == 0:
            s["in"] = {"type": "fade", "dur": 0.5}
        if b.get("intent"):
            s["cut_intent"] = b["intent"]
        if b["who"] == "A":
            s.update(who=names[0], x=0.40, pose="stand", facing=1)
        elif b["who"] == "B":
            s.update(who=names[1], x=0.62, pose="stand", facing=-1)
        elif b["who"] == "AB":
            s.update(who=names[0], x=0.36, pose="stand", facing=1,
                     who2=names[1], x2=0.68, pose2="stand", facing2=-1)
            # A group story puts the third figure in the wide two-hander. Wide
            # only: at med/close three bodies collide (measured on the office
            # still, where two already hid the desk).
            if len(names) > 2 and b["size"] == "wide":
                s.update(who3=names[2], x3=0.86, pose3="stand", facing3=-1,
                         scale3=0.94)
        if b.get("expr"):
            s["expr"] = b["expr"]
        if b.get("exprTo"):
            s["exprTo"] = b["exprTo"]
            s["at"] = round(b["hold"] + 0.35, 2)
        if b.get("insert"):
            s["insertKind"] = insert_kind
            s.pop("bg", None)
            s.pop("set", None)
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
