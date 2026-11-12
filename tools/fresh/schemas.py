"""fresh.schemas - hand-rolled validators (stdlib only). Each returns a list of
error strings; empty list means valid. Unknown keys are errors, so typos
('colour') fail loudly instead of being silently ignored.
"""
import re

from .core import is_hex

# Closed vocabularies from the Phase 0 audit of engine/rig2d.js. If rig2d.js
# changes, update these (Phase 0c asks the agent to diff them against source).
TOPS = {"hoodie", "labcoat", "trench", "jersey", "tshirt", "suit", "dress",
        "tracksuit", "none"}
# Mirrors chars/markers.js. The old twelve-name set advertised markers that do
# not exist; drawMarker throws on an unknown kind, so those names were a crash.
HEADS = {"bob", "glasses", "cap", "beanie", "bun", "none"}
FACES = {"glasses", "sunglasses", "none"}

BACKGROUNDS = {"light", "mid", "dark"}
SCHEMES = {"analogous", "complementary", "split", "triad"}
# Roles a project may re-skin. `sky` is excluded on purpose (see validate_set_spec).
OVERRIDE_ROLES = ("wall", "floor", "accent", "practical", "dark")

ROLES = ("wall", "floor", "sky", "accent", "practical", "dark")

# A set module is imported as `import { <name> } from '../sets/<name>.js'`, so
# the name must be a valid JS identifier (no hyphens, no leading digit).
SET_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _unknown(d, allowed, where):
    return [f"{where}: unknown key '{k}'" for k in d if k not in allowed]


def _band(v, where, lo=0.0, hi=1.0):
    if (not isinstance(v, list) or len(v) != 2
            or not all(isinstance(x, (int, float)) for x in v)
            or not (lo <= v[0] <= v[1] <= hi)):
        return [f"{where}: must be [min, max] within {lo}..{hi}"]
    return []


def validate_style_pack(d):
    e = []
    if not isinstance(d, dict):
        return ["style pack: must be an object"]
    allowed = {"id", "label", "background", "hues", "schemes", *ROLES, "times",
               "bg_by_time", "locations", "ink_contrast_min", "fill_min_de",
               "floor_wall_min_de"}
    e += _unknown(d, allowed, "style pack")
    if not SET_NAME_RE.match(str(d.get("id", ""))):
        e.append("style pack: 'id' must match [a-z][a-z0-9_]*")
    if d.get("background") not in BACKGROUNDS:
        e.append(f"style pack: 'background' must be one of {sorted(BACKGROUNDS)}")
    hues = d.get("hues")
    if not isinstance(hues, list) or not hues:
        e.append("style pack: 'hues' must be a non-empty list of [lo, hi] degrees")
    else:
        for i, h in enumerate(hues):
            e += _band(h, f"hues[{i}]", 0, 360)
    sch = d.get("schemes")
    if not isinstance(sch, list) or not sch or not set(sch) <= SCHEMES:
        e.append(f"style pack: 'schemes' must be a non-empty subset of {sorted(SCHEMES)}")
    for role in ROLES:
        spec = d.get(role)
        if not isinstance(spec, dict):
            e.append(f"style pack: '{role}' must be an object with s/l bands")
            continue
        e += _unknown(spec, {"h", "s", "l"}, f"style pack.{role}")
        e += _band(spec.get("s"), f"{role}.s")
        e += _band(spec.get("l"), f"{role}.l")
        if "h" in spec:
            e += _band(spec["h"], f"{role}.h", 0, 360)
    times = d.get("times")
    if not isinstance(times, list) or not times:
        e.append("style pack: 'times' must be a non-empty list")
    else:
        bg = d.get("bg_by_time", {})
        for t in times:
            if not isinstance(bg, dict) or not isinstance(bg.get(t), str) or not bg.get(t):
                e.append(f"style pack: 'bg_by_time' needs an engine mood name for '{t}'")
    locs = d.get("locations")
    if not isinstance(locs, list) or not locs:
        e.append("style pack: 'locations' must be a non-empty list")
    else:
        for i, loc in enumerate(locs):
            w = f"locations[{i}]"
            if not isinstance(loc, dict):
                e.append(f"{w}: must be an object")
                continue
            e += _unknown(loc, {"id", "props", "min_props", "max_props"}, w)
            if not SET_NAME_RE.match(str(loc.get("id", ""))):
                e.append(f"{w}: 'id' must match [a-z][a-z0-9_]*")
            props = loc.get("props")
            mn, mx = loc.get("min_props"), loc.get("max_props")
            if not isinstance(props, list) or not props:
                e.append(f"{w}: 'props' must be a non-empty list")
            elif not (isinstance(mn, int) and isinstance(mx, int)
                      and 0 <= mn <= mx <= len(props)):
                e.append(f"{w}: need 0 <= min_props <= max_props <= len(props)")
    for k in ("ink_contrast_min", "fill_min_de", "floor_wall_min_de"):
        if k in d and not (isinstance(d[k], (int, float)) and d[k] >= 0):
            e.append(f"style pack: '{k}' must be a number >= 0")
    return e


def validate_series(d):
    e = []
    if not isinstance(d, dict):
        return ["series: must be an object"]
    e += _unknown(d, {"series_id", "character", "voice", "sfx_palette",
                      "wardrobe"}, "series")
    if not SET_NAME_RE.match(str(d.get("series_id", ""))):
        e.append("series: 'series_id' must match [a-z][a-z0-9_]*")
    ch = d.get("character")
    if not isinstance(ch, dict):
        e.append("series: 'character' must be an object")
    else:
        e += _unknown(ch, {"id", "name", "base_color", "head_color", "head",
                           "top", "face"}, "character")
        for k in ("id", "name"):
            if not isinstance(ch.get(k), str) or not ch.get(k):
                e.append(f"character: '{k}' is required")
        for k in ("base_color", "head_color"):
            if not is_hex(ch.get(k)):
                e.append(f"character: '{k}' must be #rrggbb")
        for k, vocab in (("head", HEADS), ("top", TOPS), ("face", FACES)):
            if k in ch and ch[k] not in vocab:
                e.append(f"character: '{k}'={ch[k]!r} not in rig vocabulary")
    voice = d.get("voice")
    if not (isinstance(voice, dict) and isinstance(voice.get("id"), str)
            and voice.get("id")):
        e.append("series: 'voice.id' is required")
    sfx = d.get("sfx_palette")
    if not (isinstance(sfx, list) and sfx and all(isinstance(s, str) for s in sfx)):
        e.append("series: 'sfx_palette' must be a non-empty list of names")
    wr = d.get("wardrobe")
    if not isinstance(wr, list) or not wr:
        e.append("series: 'wardrobe' must be a non-empty list")
    else:
        for i, w in enumerate(wr):
            where = f"wardrobe[{i}]"
            if not isinstance(w, dict):
                e.append(f"{where}: must be an object")
                continue
            e += _unknown(w, {"top", "color", "legs"}, where)
            if w.get("top") not in TOPS:
                e.append(f"{where}: 'top'={w.get('top')!r} not in rig vocabulary")
            for k in ("color", "legs"):
                if not is_hex(w.get(k)):
                    e.append(f"{where}: '{k}' must be #rrggbb")
    return e


def validate_set_spec(d):
    e = []
    if not isinstance(d, dict):
        return ["set spec: must be an object"]
    e += _unknown(d, {"set", "location", "seed", "pack", "palette", "props",
                      "time", "bg", "dressing"}, "set spec")
    if not SET_NAME_RE.match(str(d.get("set", ""))):
        e.append("set spec: 'set' must be a valid JS identifier "
                 "[a-z][a-z0-9_]* (it becomes scenes/sets/<set>.js)")
    pal = d.get("palette")
    if not isinstance(pal, dict):
        e.append("set spec: 'palette' must be an object")
    else:
        # `sky` is a gradient ARRAY in the engine mood, so a single hex here
        # crashed the renderer ("stops.forEach is not a function"). Sky varies
        # through the background mood; only these roles may be overridden.
        if "sky" in pal:
            e.append("set spec: palette.sky must not be set — the engine's sky "
                     "is a gradient array; it varies via the background mood")
        for r in OVERRIDE_ROLES:
            if not is_hex(pal.get(r)):
                e.append(f"set spec: palette.{r} must be #rrggbb")
    if "dressing" in d and not isinstance(d["dressing"], dict):
        e.append("set spec: 'dressing' must be an object")
    if not isinstance(d.get("props"), list):
        e.append("set spec: 'props' must be a list")
    for k in ("location", "seed", "pack", "time", "bg"):
        if not isinstance(d.get(k), str) or not d.get(k):
            e.append(f"set spec: '{k}' is required")
    return e


class SpecError(ValueError):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def require_valid(errors):
    if errors:
        raise SpecError(errors)
