"""fresh.audio - derive music mood, ambience and theme accents from the concept.

Owner rule (2026-11-12): a video that does not name its audio must have it
DERIVED from the story/theme, not fall through to one constant. Before this
module `story.py:96` always wrote `music: []`, so `audio/music.py:154
default_plan()` returned `mood: "mystery"` for every film ever generated.

Determinism is mandatory: the same concept must produce the same plan, because
`FreshStoryTests` and the whole QA story depend on reproducible output.

Vocabularies are copied from source, not invented:
  MUSIC_MOODS  <- audio/music.py:19-30 MOODS keys        (11)
  AMB_NAMES    <- audio/sfx.py @sfx names that loop cleanly
  ACCENT_SFX   <- audio/sfx.py @sfx names usable as one-shots
`DerivedAudioTests` is the drift alarm for all three.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept

# audio/music.py:19 MOODS
MUSIC_MOODS = frozenset("""mystery tension action wonder hopeful sad triumph
playful calm dark epic""".split())

# audio/sfx.py -- loopable beds (mix.py places these under a whole shot)
AMB_NAMES = frozenset("roomtone city rain wind murmur clock".split())

# audio/sfx.py -- one-shots usable as a single theme accent
ACCENT_SFX = frozenset("""phonebuzz phonering carpass kick whistle cheer applause
ding shimmer stinger footstep pop tick heartbeat thunder""".split())

# Keyword -> music mood. Ordered: the first hit wins, so put specific before
# generic. All values must be in MUSIC_MOODS.
_THEME_MOOD = (
    (("phone", "text", "notif", "social", "scroll", "app", "feed"), "playful"),
    (("proposal", "engage", "wedding", "love", "date", "romance", "crush"), "hopeful"),
    (("detective", "letter", "secret", "clue", "mystery", "missing", "clue"), "mystery"),
    (("chase", "run", "escape", "race", "hunt", "flee"), "action"),
    (("space", "star", "ocean", "dream", "magic", "wonder", "galaxy"), "wonder"),
    (("battle", "fight", "war", "army", "boss"), "epic"),
    (("ghost", "monster", "fear", "dark", "haunt", "nightmare"), "dark"),
    (("money", "deal", "business", "job", "interview", "exam", "deadline"), "tension"),
    (("win", "goal", "achieve", "champion", "victory"), "triumph"),
    (("chef", "restaurant", "cook", "food", "bakery", "coffee"), "hopeful"),
    (("bus", "train", "lost", "late", "alone", "goodbye", "last"), "sad"),
    (("rain", "quiet", "calm", "sleep", "morning", "home"), "calm"),
)

# engine/styles.js mood keys -> music mood. The fallback when the concept has no
# keyword at all, so a wordless concept still gets a fitting score.
_BG_MOOD = {
    "day": "hopeful", "golden": "playful", "dusk": "calm", "night": "mystery",
    "storm": "tension", "interiorWarm": "calm", "interiorCool": "mystery",
    "void": "dark",
}

# The second half of the film resolves somewhere related but not identical --
# a film that ends on exactly the mood it opened on reads as a loop.
_RESOLVE = {
    "mystery": "wonder", "tension": "dark", "action": "triumph",
    "wonder": "hopeful", "hopeful": "triumph", "sad": "hopeful",
    "triumph": "hopeful", "playful": "hopeful", "calm": "hopeful",
    "dark": "mystery", "epic": "triumph",
}

# Keyword -> one-shot accent. Kept small on purpose: an accent that fires on
# every film is the same defect as one constant mood.
_ACCENT = (
    (("phone", "ring", "notif", "text"), "phonebuzz"),
    (("car", "drive", "road", "taxi", "bus"), "carpass"),
    (("ball", "kick", "match", "football"), "kick"),
    (("whistle", "referee", "coach"), "whistle"),
    (("crowd", "stadium", "party", "market", "school"), "cheer"),
    (("rain", "storm", "thunder"), "thunder"),
    (("door", "knock", "arrive"), "footstep"),
    (("reveal", "magic", "surprise", "twist"), "shimmer"),
)


def _matcher(words):
    """Word-start matcher. `\\b` prevents "app" matching inside "happens" and
    "run" inside "brunch"; the missing trailing boundary lets "ring" match
    "ringing", which is what a theme keyword needs."""
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + ")")


_THEME_RE = tuple((_matcher(words), mood) for words, mood in _THEME_MOOD)
_ACCENT_RE = tuple((_matcher(words), name) for words, name in _ACCENT)


def mood_for(concept, bg_mood=None):
    """Pick a music mood. A theme keyword wins; the background mood is fallback."""
    low = str(concept or "").lower()
    for rx, mood in _THEME_RE:
        if rx.search(low):
            return mood
    return _BG_MOOD.get(bg_mood, "mystery")


def derive_music(concept, total, bg_mood=None, seed=None, series_mood=None):
    """Return a contiguous music plan spanning [0, total].

    `series_mood` pins the opening mood so every episode of a series shares its
    sonic identity; without it the mood is derived from the concept.
    """
    total = round(float(total), 3)
    if total <= 0:
        total = 1.0
    mood = series_mood or mood_for(concept, bg_mood)
    rng = Rng((seed or seed_from_concept(concept)) + "|music")
    split = round(total * rng.range(0.55, 0.70), 3)
    if split <= 0 or split >= total:
        split = round(total / 2.0, 3)
    return [
        {"start": 0.0, "end": split, "mood": mood,
         "intensity": round(rng.range(0.38, 0.52), 2)},
        {"start": split, "end": total, "mood": _RESOLVE.get(mood, "hopeful"),
         "intensity": round(rng.range(0.55, 0.78), 2)},
    ]


_AMB_RAIN = _matcher(("rain", "storm", "thunder", "monsoon"))
_AMB_WIND = _matcher(("sea", "ocean", "wind", "mountain", "desert", "beach",
                        "garden", "park", "forest", "woods", "meadow", "field",
                        "countryside", "hill", "hills"))
_AMB_CROWD = _matcher(("crowd", "party", "market", "school", "stadium"))


def derive_amb(concept, set_name=None, bg_mood=None):
    """Return the ambience bed name for a location. Always a real SFX name."""
    low = str(concept or "").lower()
    if _AMB_RAIN.search(low):
        return "rain"
    if _AMB_WIND.search(low):
        return "wind"
    if _AMB_CROWD.search(low):
        return "murmur"
    if set_name == "outdoor":
        return "city" if bg_mood in ("night", "dusk", "golden") else "wind"
    return "roomtone"


def derive_accent_sfx(concept):
    """Return one theme accent SFX name, or None when the theme has no match."""
    low = str(concept or "").lower()
    for rx, name in _ACCENT_RE:
        if rx.search(low):
            return name if name in ACCENT_SFX else None
    return None
