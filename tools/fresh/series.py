"""fresh.series - series bible / cast generator from a fresh palette.

Produces a schemas.validate_series-compatible dict: series_id, character, voice,
sfx_palette, wardrobe. Deterministic per series_id.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept
from .palette import generate_palette
from .schemas import validate_series, require_valid

VOICES = ["am_michael", "am_puck", "am_fenrir", "am_onyx", "af_heart", "af_bella",
          "af_nicole", "bm_george", "bm_fable", "bf_emma"]
SFX_NAMES = ["whoosh", "swish", "hit", "tick", "ding", "pop", "footstep",
             "phonebuzz", "glitch", "flash", "shimmer", "stinger"]
TOPS = ["hoodie", "labcoat", "trench", "jersey", "tshirt", "suit", "dress",
        "tracksuit"]
HEADS = ["cap", "capBack", "beanie", "fedora", "headband", "visor", "hood",
         "ponytail", "bun", "curly", "spiky", "none"]
FACES = ["glasses", "sunglasses", "none"]


def generate_series(series_id, concept=None, title=None):
    # Seed from the SERIES ID, not the episode concept: a bible that changes
    # every episode is not a bible. story.py:24 uses series_id the same way.
    seed = seed_from_concept(series_id, series_id, None)
    rng = Rng(seed)
    pal = generate_palette(series_id, series_id, None)
    ident = pal["identity"]
    colors = ident["colors"]
    tops = ident["tops"]
    heads = ident["heads"]
    faces = ident["faces"]

    # character identity from the first color (stable per series)
    base_color = colors[0]
    head_color = colors[1] if len(colors) > 1 else colors[0]
    head = heads[0] if heads else "none"
    top = tops[0] if tops else "tshirt"
    face = faces[0] if faces else "none"

    voice_id = rng.pick(VOICES)
    sfx_palette = rng.sample(SFX_NAMES, 4)
    if not sfx_palette:
        sfx_palette = ["whoosh"]

    # wardrobe variants
    wardrobe = []
    for i in range(3):
        wardrobe.append({
            "top": rng.pick(TOPS),
            "color": _readable(rng),
            "legs": _readable(rng),
        })
    # ensure first wardrobe matches character signature
    wardrobe[0] = {"top": top, "color": base_color, "legs": colors[1] if len(colors) > 1 else base_color}

    name = title if title else str(series_id).replace("_", " ").title()
    char_id = str(series_id).upper().replace("-", "_")[:12] or "CHAR"

    series = {
        "series_id": _slug(series_id),
        "character": {
            "id": char_id,
            "name": name,
            "base_color": base_color,
            "head_color": head_color,
            "head": head,
            "top": top,
            "face": face,
        },
        "voice": {"id": voice_id},
        "sfx_palette": sfx_palette,
        "wardrobe": wardrobe,
    }
    errs = validate_series(series)
    if errs:
        raise ValueError("series invalid: " + "; ".join(errs))
    return series


def _slug(s):
    import re
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s or not s[0].isalpha():
        s = "series_" + s
    return s[:40]


def _readable(rng):
    for _ in range(20):
        h = rng.range(0, 360)
        s = rng.range(0.4, 0.8)
        l = rng.range(0.35, 0.75)
        c = _hsl(h, s, l)
        # accept any
        return c
    return "#808080"


def _hsl(h, s, l):
    import colorsys
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    return "#%02x%02x%02x" % (max(0, min(255, int(round(r * 255)))),
                              max(0, min(255, int(round(g * 255)))),
                              max(0, min(255, int(round(b * 255)))))


def write_series(series_id, out_path, concept=None, title=None):
    series = generate_series(series_id, concept, title)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    import json
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(series, fh, indent=1)
    return out_path


# ── series pin ───────────────────────────────────────────────────────────────
# A series must keep ONE location, style and mood across episodes. Until now
# those were re-derived from the series ID string, so a series called "ep1"
# (no location keyword in it) fell through to the seeded random draw and could
# move house between episodes -- and a series called "dragon" only got `outdoor`
# because a creature noun happens to be a location hint. The resolved story of
# the FIRST episode is the only honest source, so it is written once and read
# back. Stored per studio, not per project: each episode is its own --out.
def pin_path(studio, series_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(series_id or "series"))[:60]
    return os.path.join(studio, "series", "%s.json" % safe)


def read_pin(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def write_pin(path, story, series_id=None):
    """Persist what episode 1 RESOLVED, not what its ID happened to imply."""
    shots = story.get("shots") or [{}]
    mood = None
    for sh in shots:
        if sh.get("bg"):
            mood = sh["bg"]
            break
    pin = {"series_id": series_id, "set": story.get("set"),
           "style": story.get("style"), "mood": mood,
           # Without this a series re-drew its wall every episode: the seed
           # contains the episode number, so the wallpaper changed weekly.
           "palette": story.get("palette")}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pin, fh, indent=1)
    return pin
