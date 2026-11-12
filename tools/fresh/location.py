"""fresh.location - the SCENE decides the location, then the cast, then the
wardrobe, then the sound.

Before 2026-11-13 `palette.py:41` did `set_name = rng.pick(SETS)`: the room was
drawn at random from four names before the story had any say, so a chef could
cook in a bus shelter and a commuter could wait for a bus in an office. This
module reverses that: the concept text is read first, and the location is a
consequence of it. Randomness survives only as a fallback when the text names
nothing, and the fallback is seeded, so the same concept still gives the same
film (determinism is a QC requirement — see selftest_gates determinism tests).

Screenplay order, which is also the dependency order:
    location -> cast -> wardrobe/props -> ambience/music/SFX
"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept

SETS = ["room", "kitchen", "outdoor", "office"]

# Interior vs exterior decides whether a background mood is a room palette
# (interiorWarm / interiorCool) or a sky palette (day/golden/dusk/night).
INTERIOR = ("room", "kitchen", "office")

# Keywords are matched on WORD BOUNDARIES, never as substrings: substring
# matching made "happens" match "app" in fresh/audio.py on 2026-11-12.
_LOCATION_WORDS = (
    ("kitchen", ("kitchen", "chef", "cook", "cooking", "restaurant", "cafe",
                 "diner", "bakery", "recipe", "oven", "fridge", "food", "meal",
                 "eat", "eats", "dinner", "breakfast", "lunch", "tea", "coffee",
                 "waiter", "menu")),
    ("office", ("office", "desk", "boss", "meeting", "email", "memo",
                "deadline", "cubicle", "printer", "interview", "resign",
                "colleague", "shift", "monitor", "computer", "laptop", "job",
                "promotion", "paperwork", "reception")),
    ("outdoor", ("bus", "train", "station", "platform", "street", "road",
                 "park", "garden", "rain", "snow", "walk", "walking", "outside",
                 "city", "sea", "beach", "mountain", "tree", "trees", "journey",
                 "commute", "sky", "alley", "rooftop", "field")),
    ("room", ("bed", "bedroom", "sleep", "sleeping", "home", "house",
              "apartment", "room", "sofa", "mirror", "letter", "door", "lamp",
              "wake", "wakes", "pillow", "window", "bathroom", "library",
              "study", "bookshelf", "armchair", "living")),
)

_TIME_WORDS = (
    ("night", ("midnight", "night", "tonight", "dark", "moon", "stars",
               "insomnia", "late", "3am", "2am")),
    ("morning", ("morning", "sunrise", "dawn", "breakfast", "wake", "wakes")),
    ("evening", ("evening", "dusk", "sunset", "dinner", "supper", "twilight")),
    ("afternoon", ("afternoon", "noon", "lunch")),
)

_STORM_WORDS = ("storm", "thunder", "rain", "monsoon", "downpour")

# Only these eight tops are drawable (chars/inkbean.js drawTop). Anything else
# falls back to neutral silently, which is the exact failure mode the story
# contract gate exists to prevent.
TOPS_BY_SET = {
    "room": ["tshirt", "hoodie", "dress", "tracksuit"],
    "kitchen": ["labcoat", "hoodie", "tshirt", "dress"],
    "outdoor": ["trench", "hoodie", "jersey", "tracksuit"],
    "office": ["suit", "labcoat", "tshirt", "hoodie"],
}

_ROLE_TOP = (
    ("labcoat", ("chef", "cook", "baker", "barista", "waiter", "kitchen")),
    ("labcoat", ("doctor", "nurse", "scientist", "lab", "surgeon", "chemist")),
    ("suit", ("boss", "manager", "executive", "lawyer", "banker", "ceo",
              "interview", "promotion")),
    ("trench", ("detective", "inspector", "commuter", "traveller", "traveler",
                "spy", "stranger")),
    ("jersey", ("athlete", "player", "runner", "coach", "team")),
    ("hoodie", ("student", "kid", "teen", "child", "boy", "girl", "school")),
    ("tracksuit", ("worker", "mechanic", "courier", "delivery", "guard")),
    ("dress", ("bride", "wedding", "dancer", "singer", "actress")),
)


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def _score(text_tokens, words):
    return sum(1 for w in words if w in text_tokens)


def derive_location(concept, beats=None):
    """Read the concept and return the location it implies.

    Returns {"set", "time", "mood", "source"} where `source` is "keyword" when
    the text decided it and "seed" when it had to fall back. The fallback is
    seeded from the concept, so it is stable, not per-run random.
    """
    text = str(concept or "")
    if beats:
        # Beat dialogue can name a place even when the one-line concept does not.
        text = text + " " + " ".join(str(b.get("line") or "") for b in beats)
    toks = _tokens(text)

    scores = [(name, _score(toks, words)) for name, words in _LOCATION_WORDS]
    best = max(s for _, s in scores)
    seed = seed_from_concept(concept)
    if best > 0:
        winners = [name for name, s in scores if s == best]
        set_name = winners[0] if len(winners) == 1 else Rng(seed + "|loc").pick(winners)
        source = "keyword"
    else:
        set_name = Rng(seed + "|loc").pick(SETS)
        source = "seed"

    time = None
    time_scores = [(t, _score(toks, words)) for t, words in _TIME_WORDS]
    best_t = max(s for _, s in time_scores)
    if best_t > 0:
        winners = [t for t, s in time_scores if s == best_t]
        time = winners[0] if len(winners) == 1 else Rng(seed + "|time").pick(winners)
    else:
        time = Rng(seed + "|time").pick(["morning", "afternoon", "evening", "night"])

    mood = bg_mood_for(set_name, time)
    if set_name == "outdoor" and _score(toks, _STORM_WORDS) > 0:
        mood = "storm"

    return {"set": set_name, "time": time, "mood": mood, "source": source}


def bg_mood_for(set_name, time):
    """Map (location, time of day) to a legal ENGINE background mood.

    Interior rooms get interior palettes; exteriors get sky palettes. Passing a
    sky mood to an interior set (or the reverse) is what made every film read
    the same dark blue regardless of scene.
    """
    if set_name in INTERIOR:
        return "interiorCool" if time == "night" else "interiorWarm"
    return {"morning": "day", "afternoon": "golden",
            "evening": "dusk", "night": "night"}.get(time, "dusk")


def derive_top(set_name, role=None, index=0):
    """Wardrobe follows the role first, then the room. Always a real top.

    `index` breaks the tie between characters the concept does not name: a
    shared seed dressed both of them identically, which reads as a uniform.
    """
    low = str(role or "").lower()
    for top, words in _ROLE_TOP:
        if any(w in low for w in words):
            return top
    allowed = TOPS_BY_SET.get(set_name) or TOPS_BY_SET["room"]
    return allowed[int(index) % len(allowed)]


# Only three props are drawable (director.py:1024 PROPS = mug/book/phone). The
# room narrows that set; it can never invent a fourth kind, because an
# unimplemented prop renders as nothing and no gate would notice.
PROPS_BY_SET = {
    "room": ["book", "mug"],
    "kitchen": ["mug"],
    "outdoor": ["phone"],
    "office": ["phone", "book"],
}

_PROP_FOR_INSERT = {"phone": "phone", "screen": "phone",
                    "document": "book", "photo": "book", "card": "book"}


def derive_prop(set_name, insert_kind=None, index=0):
    """Pick the prop the scene would plausibly have, from the 3 that render.

    The insert kind (what the beat wants to show) wins when the room allows it;
    otherwise the room's own list decides, so a kitchen does not hand someone a
    phone just because the shape asked for a document insert.
    """
    allowed = PROPS_BY_SET.get(set_name) or PROPS_BY_SET["room"]
    preferred = _PROP_FOR_INSERT.get(insert_kind)
    if preferred in allowed:
        return preferred
    return allowed[int(index) % len(allowed)]


def derive_roles(concept, count=2):
    """Return up to `count` role tags implied by the concept, padded with None.

    Used so the wardrobe can follow the story ("chef") instead of being drawn
    from an eight-item list with no relation to the scene.
    """
    low = str(concept or "").lower()
    found = []
    for top, words in _ROLE_TOP:
        for w in words:
            if w in low:
                found.append(w)
                break
    return (found + [None] * count)[:count]

# ---------------------------------------------------------------------------
# Dressing: geometry is a choice, not four fixed drawings.
#
# The set templates were static: the same room, the same furniture, forever.
# These toggles are derived from the concept (a garden grows a plant, a library
# grows shelves) and injected into the emitted JS as PROJECT_DRESSING, exactly
# like the palette. DEFAULTS are deliberately OFF for everything decorative, so
# a project without a spec — cine_release — reproduces the old picture exactly.
# ---------------------------------------------------------------------------
DRESSING_DEFAULTS = {
    "window": True,
    "blinds": 0,
    "art": 0,
    "shelf": False,
    "plant": False,
    "rug": False,
    "floor": "planks",
}

_DRESSING_WORDS = (
    ("plant", ("garden", "flower", "flowers", "plant", "plants", "forest",
               "spring", "greenhouse", "park", "tree", "trees")),
    ("shelf", ("book", "books", "library", "read", "reading", "shelf",
               "study", "archive", "record")),
    ("art", ("art", "painting", "paintings", "gallery", "poster", "posters",
             "museum", "picture", "portrait", "photo", "photos")),
    ("rug", ("cozy", "cosy", "home", "living", "warm", "carpet", "rug",
             "winter", "blanket")),
)


def derive_dressing(set_name, concept, seed=None):
    """Return the dressing toggles for this location, derived from the story.

    Deterministic: the same concept always yields the same room, because a QC
    failure has to be reproducible.
    """
    d = dict(DRESSING_DEFAULTS)
    low = str(concept or "").lower()
    rng = Rng(str(seed or seed_from_concept(concept)) + "|dress")

    for key, words in _DRESSING_WORDS:
        if any(w in low for w in words):
            # art is a COUNT (0/1/2), the rest are booleans
            d[key] = 2 if (key == "art" and low.count("art") > 1) else (1 if key == "art" else True)

    # A room with no window is a basement: only when the story says so.
    if any(w in low for w in ("basement", "cellar", "underground", "bunker")):
        d["window"] = False

    # A shift/office day wants blinds; otherwise the window is bare.
    if set_name in ("office",) or any(w in low for w in ("blinds", "shift")):
        d["blinds"] = 14

    # Floor material follows the room, not the dice.
    d["floor"] = "tiles" if set_name in ("kitchen", "office") else "planks"

    # An exterior has no wall, so wall dressing would float in mid-air. The
    # first end-to-end film drew a framed picture over the sky because the
    # fallback below picked art=1 for an outdoor set.
    if set_name == "outdoor":
        d["art"], d["shelf"], d["rug"], d["blinds"] = 0, False, False, 0

    # Only fill what the story did not decide, and only from the seeded stream,
    # so an unrelated concept does not silently dress like a garden.
    if not d["art"] and set_name != "outdoor":
        d["art"] = rng.pick([0, 0, 1])
    if not d["rug"] and set_name != "outdoor":
        d["rug"] = rng.pick([False, False, True]) if set_name == "room" else False
    return d

# ---------------------------------------------------------------------------
# Style: the fifth decision that was never derived.
#
# generate_palette drew the style at random from five names, and every
# hand-authored story hardcoded "midnight" — 29 of 31 films rendered the same
# grade. A wedding and a detective story looked identical. Style is a
# consequence of the story, exactly like the location, so it is derived the
# same way: theme keywords first, then the background mood as fallback.
# ---------------------------------------------------------------------------
_THEME_STYLE = (
    # whimsical first: a fairy tale must not be graded as a crime scene
    ("storybook", ("fairy", "tale", "fable", "dream", "magic", "magical", "wish",
                   "dragon", "princess", "prince", "kid", "kids", "child",
                   "children", "toy", "toys", "story", "bedtime", "wonder",
                   "cartoon", "silly", "joke", "funny", "punchline")),
    ("neon", ("phone", "screen", "computer", "code", "ai", "app", "robot",
              "machine", "digital", "cyber", "internet", "game", "arcade",
              "club", "party", "concert", "neon", "disco", "video", "wifi",
              "notification", "text", "texts", "scroll", "online")),
    ("golden", ("wedding", "sunset", "sunrise", "beach", "summer", "dawn",
                "hope", "hopeful", "proposal", "garden", "picnic", "birthday",
                "celebration", "bride", "groom", "holiday", "vacation")),
    ("midnight", ("detective", "mystery", "secret", "crime", "midnight",
                  "shadow", "shadows", "hunt", "clue", "case", "suspect",
                  "murder", "dark", "haunted", "ghost", "night")),
    ("dusk", ("rain", "rainy", "funeral", "goodbye", "memory", "memories",
              "letter", "alone", "lonely", "autumn", "winter", "evening",
              "silence", "quiet", "empty", "lost", "miss", "missing", "walk")),
)

# Fallback when the text names no theme at all: the grade follows the light.
_MOOD_STYLE = {
    "day": "dusk",
    "golden": "golden",
    "dusk": "dusk",
    "night": "midnight",
    "storm": "midnight",
    "void": "midnight",
    "interiorWarm": "golden",
    "interiorCool": "dusk",
}


def derive_style(concept, set_name=None, bg_mood=None):
    """Return the style (grade) the story implies. Always a real style name.

    Keyword hits are SCORED, not first-match: "a wedding in the rain" should be
    a warm film with bad weather, not a funeral.
    """
    toks = _tokens(concept)
    best, best_n = None, 0
    for name, words in _THEME_STYLE:
        n = _score(toks, words)
        if n > best_n:
            best, best_n = name, n
    if best:
        return best
    return _MOOD_STYLE.get(bg_mood, "midnight")
