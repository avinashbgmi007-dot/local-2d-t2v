"""fresh.cast - derive character names from the concept.

Owner rule (2026-11-12): a standalone video must not reuse the same characters.
Before this module `story.py:36` hardcoded `names = ["MAX", "JAKE"]`, so every
generated film starred the same two people and every spoken line named them.

Names reach the viewer only through `fresh/shapes.py:185`, which substitutes
`{a}` / `{b}` into a line template. Exactly ONE shape currently uses `{a}`, so
in most films the names stay internal labels and the visible variation comes
from the shape skeleton plus colour/top/head, which already varied per concept.
Deriving names is therefore a correctness fix, not the main source of variety:
do not claim a viewer will hear the difference.

Series continuity is the opposite requirement: an episode of a series must keep
its cast, so `derive_cast_names` is only called when there is no `series_id`
(`story.py`). `FreshStoryTests.test_series_cast_is_stable_across_episodes` pins
that behaviour.

The pool is deliberately plain and short: these names are spoken by TTS and sit
in a caption, so they must be unambiguous to pronounce and cheap to read.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core import Rng, seed_from_concept

# No entry may collide with the banned-word list in FreshStoryTests, and none
# may be a theme keyword in fresh/audio.py (a name would then pick the score).
NAME_POOL = (
    "AVA", "BEN", "CARA", "DEV", "ELI", "FINN", "GUS", "HANA", "IVY", "JON",
    "KAI", "LUNA", "MILO", "NORA", "OMAR", "PIA", "QUINN", "RAVI", "SANA",
    "THEO", "UMA", "VERA", "WES", "YARA", "ZANE", "ABEL", "BEA", "COLE",
    "DARA", "EZRA", "FELIX", "GIA", "HUGO", "INES", "JADE", "KIRA", "LEO",
    "MAYA", "NIKO", "OLIVE", "PABLO", "RHEA", "SOL", "TARA", "VIKRAM",
    "WILLA", "YASH", "ZOE",
)

# The cast the series bible was written against. Kept for continuity only.
SERIES_CAST = ("MAX", "JAKE")


def derive_cast_names(concept, seed=None, count=2):
    """Return `count` distinct names, deterministic per concept.

    Two is the ceiling today: `fresh/shapes.py` only ever places figures A and B
    (`fill(shape, subject, name_a, name_b)`), so a third cast member would be
    dead data. The parameter exists so a shape with a C role can pass 3 later.
    """
    count = max(1, min(int(count), len(NAME_POOL)))
    rng = Rng((seed or seed_from_concept(concept)) + "|cast")
    return tuple(rng.sample(NAME_POOL, count))

# A group scene needs a third body on screen. These are the words that imply
# one; everything else stays a two-hander. director.py supports who3, so the
# only missing piece was the story layer placing it.
_GROUP_WORDS = ("crowd", "family", "team", "wedding", "party", "friends",
                "group", "everyone", "village", "class", "crew", "trio",
                "three", "gang", "audience", "queue", "neighbours", "neighbors")


def derive_cast_size(concept):
    """2 by default, 3 when the concept implies a group."""
    low = str(concept or "").lower()
    return 3 if any(w in low for w in _GROUP_WORDS) else 2
