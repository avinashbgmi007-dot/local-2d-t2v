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
              "wake", "wakes", "pillow", "window", "bathroom")),
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
