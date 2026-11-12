"""fresh.palette - deterministic palette + visual-identity generation.

Uses fresh.core for color math and fresh.schemas for validation.
Produces a dict describing a distinct visual identity for a concept.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept, hsl_to_hex, contrast, delta_e, is_hex
from .schemas import validate_style_pack, require_valid


STYLES = ["dusk", "midnight", "golden", "neon", "storybook"]
MOODS = ["day", "golden", "dusk", "night", "storm", "interiorWarm", "interiorCool", "void"]
SETS = ["room", "kitchen", "outdoor", "office"]
INSERT_KINDS = ["card", "screen", "phone", "document", "photo"]
TOPS = ["hoodie", "labcoat", "trench", "jersey", "tshirt", "suit", "dress", "tracksuit"]
# Only markers chars/markers.js can draw. The old twelve-name list was a trap:/n# eight of them threw in drawMarker and none of them reached a head anyway.
# fresh/cast.py owns the vocabulary; this is kept in sync for the style pack.
HEADS = ["bob", "glasses", "cap", "beanie", "bun", "none"]
FACES = ["glasses", "sunglasses", "none"]


def _readable_color(rng, ink="#15131a", min_contrast=3.0):
    """Generate a hex color with sufficient contrast against ink."""
    for _ in range(20):
        h = rng.range(0, 360)
        s = rng.range(0.4, 0.8)
        l = rng.range(0.35, 0.75)
        c = hsl_to_hex(h, s, l)
        if contrast(c, ink) >= min_contrast:
            return c
    return hsl_to_hex(rng.range(0, 360), 0.6, 0.5)


def generate_palette(concept, series_id=None, episode=None,
                     set_name=None, bg_mood=None, style=None):
    """Return a validated style-pack dict + a compact identity dict.

    `set_name` / `bg_mood` / `style` let the caller supply what the SCENE
    implies (fresh/location.py) instead of drawing it at random. They are
    applied AFTER the draws, so the RNG stream — and therefore every colour —
    is unchanged for callers that pass nothing.
    """
    seed = seed_from_concept(concept, series_id, episode)
    rng = Rng(seed)

    drawn_style = rng.pick(STYLES)
    # An explicit, legal style wins; otherwise keep the draw so the RNG stream
    # (and therefore every colour) is unchanged for callers that pass none.
    style = style if style in STYLES else drawn_style
    mood = rng.pick(MOODS)
    drawn_set = rng.pick(SETS)
    insert_kind = rng.pick(INSERT_KINDS)

    # The scene wins over the dice. Both draws above still happen, so the RNG
    # stream (and therefore every colour below) is identical for callers that
    # pass nothing — the override only replaces the *name*.
    if bg_mood in MOODS:
        mood = bg_mood
    if set_name in SETS:
        drawn_set = set_name
    set_name = drawn_set

    # Character colors: FOUR distinct, readable colors, one per cast member.
    # It used to be two, and story.py used colors[(i+1)%2] for the legs — so
    # character B was character A with the palette inverted, and a two-hander
    # read as a single colour family. The first two draws are unchanged, so
    # existing per-concept colours do not shift.
    c1 = _readable_color(rng)
    c2 = _readable_color(rng)
    # ensure distinct
    while delta_e(c1, c2) < 20:
        c2 = _readable_color(rng)
    colors = [c1, c2]
    while len(colors) < 4:
        cand = _readable_color(rng)
        if all(delta_e(cand, c) >= 20 for c in colors):
            colors.append(cand)

    # Build style pack for validation
    hues = [[rng.range(0, 60), rng.range(60, 120)] for _ in range(2)]
    schemes = rng.sample(["analogous", "complementary", "split", "triad"], 2)
    if not schemes:
        schemes = ["analogous"]

    def role_spec(s_lo=0.3, s_hi=0.7, l_lo=0.2, l_hi=0.8):
        spec = {"s": [s_lo, s_hi], "l": [l_lo, l_hi]}
        a = rng.range(0, 300)
        b = a + rng.range(30, 60)
        if b > 360:
            b = 360
        spec["h"] = [a, b]
        return spec

    pack = {
        "id": "fresh_" + set_name,
        "label": "Fresh " + set_name.title(),
        "background": rng.pick(["light", "mid", "dark"]),
        "hues": hues,
        "schemes": schemes,
        "wall": role_spec(l_lo=0.2, l_hi=0.5),
        "floor": role_spec(l_lo=0.1, l_hi=0.35),
        "sky": role_spec(l_lo=0.5, l_hi=0.85),
        "accent": role_spec(s_lo=0.6, s_hi=0.9, l_lo=0.4, l_hi=0.7),
        "practical": role_spec(s_lo=0.5, s_hi=0.8, l_lo=0.5, l_hi=0.8),
        "dark": role_spec(l_lo=0.05, l_hi=0.2),
        "times": ["morning", "evening"],
        "bg_by_time": {"morning": mood, "evening": mood},
        "locations": [{"id": set_name, "props": ["mug", "book", "phone"], "min_props": 0, "max_props": 2}],
        "ink_contrast_min": 3.0,
        "fill_min_de": 20.0,
        "floor_wall_min_de": 10.0,
    }
    # validate (will raise if invalid)
    errs = validate_style_pack(pack)
    if errs:
        raise ValueError("style pack invalid: " + "; ".join(errs))

    identity = {
        "seed": seed,
        "style": style,
        "mood": mood,
        "set": set_name,
        "insert_kind": insert_kind,
        "colors": colors,
        "tops": [rng.pick(TOPS), rng.pick(TOPS)],
        "heads": [rng.pick(HEADS), rng.pick(HEADS)],
        "faces": [rng.pick(FACES), rng.pick(FACES)],
    }
    return {"pack": pack, "identity": identity}
