"""fresh.sets - set spec emitter from a fresh palette.

Produces a schemas.validate_set_spec-compatible dict describing the chosen
location + palette. The actual JS set modules (scenes/sets/*.js) are still
emitted by director.py from its proven templates; this spec records the
fresh-derived identity for re-skinning work (Phase 2b) without touching them.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept, hsl_to_hex
from .palette import generate_palette
from .location import derive_dressing
from .schemas import validate_set_spec, require_valid

LOCATIONS = ["room", "kitchen", "outdoor", "office"]
BG_MOODS = ["midnight", "golden", "dusk", "night", "storm", "interiorWarm",
             "interiorCool", "void"]


def generate_set_spec(concept, series_id=None, episode=None, set_name=None,
                      mood=None, pack_id="fresh", palette=None):
    seed = seed_from_concept(concept, series_id, episode)
    rng = Rng(seed)
    pal = generate_palette(concept, series_id, episode)
    ident = pal["identity"]
    if set_name is None:
        set_name = ident["set"]
    if mood is None:
        mood = ident["mood"]
    colors = ident["colors"]

    # SIX distinct roles, not two colours repeated. Until 2026-11-13 this mapped
    # wall=sky=practical=colors[0] and floor=accent=colors[1], so every set was
    # one hue family — a rendered kitchen came out pink wall over magenta floor,
    # which reads as "no palette at all". Hue offsets are far apart (0/180/30/
    # 150/60) and each role gets its own lightness band, so wall/floor/accent
    # separate on both axes.
    pal_rng = Rng(seed + "|setpal")
    base = pal_rng.range(0, 360)

    def _role(hue_off, s_lo, s_hi, l_lo, l_hi):
        return hsl_to_hex((base + hue_off) % 360,
                          pal_rng.range(s_lo, s_hi),
                          pal_rng.range(l_lo, l_hi))

    palette = {
        "wall": _role(0, 0.12, 0.30, 0.34, 0.46),
        "floor": _role(180, 0.16, 0.40, 0.14, 0.24),
        "accent": _role(150, 0.55, 0.85, 0.48, 0.66),
        "practical": _role(60, 0.45, 0.75, 0.62, 0.80),
        "dark": "#15131a",
    }
    # A SERIES keeps the colours episode 1 resolved. The wall was re-drawn per
    # episode (the seed contains the episode number), so a series changed
    # wallpaper every week -- and, once legs are chosen against the wall, its
    # trousers with it. `palette` comes from series/<id>.json.
    if isinstance(palette, dict) and palette.get("wall"):
        for _k in ("wall", "floor", "accent", "practical", "dark"):
            if palette.get(_k):
                palette[_k] = palette[_k]
    # A collision would silently collapse two roles back into one.
    # `sky` is deliberately NOT overridden: in the engine mood it is an array
    # of gradient stops, so a single hex made backdrop() call linGrad with a
    # string and crash ("stops.forEach is not a function"). Sky varies through
    # the background mood instead, which is already derived from the scene.
    _keys = ("wall", "floor", "accent", "practical")
    for _i, _k in enumerate(_keys):
        _nudge = 0
        while palette[_k] in [palette[o] for o in _keys if o != _k] and _nudge < 24:
            _nudge += 1
            palette[_k] = hsl_to_hex((base + _i * 31 + _nudge * 13) % 360,
                                     0.5, 0.3 + 0.02 * _nudge)
    # ensure dark ink contrast: if background light, keep dark ink
    # (full re-skin of ink is ADR 0003, not implemented)

    props = rng.sample(["mug", "book", "phone", "lamp", "plant"], 2)
    if not props:
        props = ["mug"]

    spec = {
        "set": set_name,
        "location": set_name,
        # furniture is a choice, not a fixed drawing: these toggles are read by
        # director.py and injected into the emitted set JS as PROJECT_DRESSING.
        "dressing": derive_dressing(set_name, concept, seed),
        "seed": seed,
        "pack": pack_id + "_" + set_name,
        "palette": palette,
        "props": props,
        "time": "evening",
        "bg": mood,
    }
    errs = validate_set_spec(spec)
    if errs:
        raise ValueError("set spec invalid: " + "; ".join(errs))
    return spec


def write_set_spec(concept, out_path, series_id=None, episode=None, **kw):
    spec = generate_set_spec(concept, series_id, episode, **kw)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    import json
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)
    return out_path
