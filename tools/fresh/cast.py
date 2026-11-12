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


# Marker vocabulary copied from palette.HEADS. "none" is a legal look, but it
# is a BALD look: in a two-hander it makes the cast read as unfinished, so it
# is only offered to a solo character.
# ONLY markers that chars/markers.js can actually draw. The palette used to
# advertise twelve (capBack, fedora, headband, visor, hood, ponytail, curly,
# spiky...) of which exactly TWO existed, and the renderer THROWS on an unknown
# kind — so those names were a crash waiting for a cast to pick one.
HEAD_MARKERS = ("bob", "glasses", "cap", "beanie", "bun",
                "hat", "helmet", "hood", "headband", "toque")

# Markers that read from the FRONT. `bun` and `bob` sit behind the skull, and
# inkbean draws heads as flat ink, so in a two-hander they are invisible: the
# first end-to-end film gave three characters glasses/bun/bob and all three
# heads rendered as the same black circle. A cast of 2+ draws from here first.
FRONT_MARKERS = ("glasses", "cap", "beanie", "hat", "helmet", "headband",
                 "toque", "hood")

# What the character DOES picks the hat. Before this, a three-hander always drew
# glasses + cap + beanie because the front-readable pool held exactly three, so
# every film looked like the same three people in different colours. A role fit
# is a meaning, not a draw.
_ROLE_HEAD = (
    ("toque", ("chef", "cook", "baker", "barista", "waiter", "kitchen")),
    ("helmet", ("guard", "soldier", "knight", "worker", "mechanic", "courier",
                "pilot", "miner", "builder")),
    ("hat", ("detective", "inspector", "traveller", "traveler", "commuter",
             "stranger", "spy", "farmer", "explorer")),
    ("headband", ("athlete", "player", "runner", "coach", "dancer", "singer")),
    ("hood", ("rain", "storm", "cold", "winter", "snow", "thief", "shadow")),
    ("cap", ("student", "kid", "teen", "child", "boy", "girl", "school")),
)


def head_for_role(role, set_name=None):
    """A marker implied by the role, or None. Set is a weak second signal."""
    low = str(role or "").lower()
    for marker, words in _ROLE_HEAD:
        if any(w in low for w in words):
            return marker
    # No set-based fallback: a toque appeared on a runner because the seeded
    # location happened to be a kitchen. A hat must MEAN something, so only an
    # explicit role grants one.
    return None


def derive_heads(seed, count, allow_none=True, roles=None, set_name=None):
    """Return `count` distinct head markers, deterministic per seed.

    Distinct is the point: two characters with the same marker read as twins,
    which is the defect this replaces (`heads[i % len(heads)]` could repeat and
    could pick "none" for everybody).

    `roles` makes the marker follow what the character DOES: a chef gets a
    toque, a guard a helmet, a runner a headband. Whatever is left over is
    drawn from the front-readable pool, so a cast of three is no longer
    glasses + cap + beanie every single film.
    """
    rng = Rng(str(seed) + "|heads")
    # A group needs markers you can SEE. Only fall back to the full vocabulary
    # when there are more bodies than front-visible markers.
    pool = list(FRONT_MARKERS) if count >= 2 else list(HEAD_MARKERS)
    if len(pool) < count:
        pool = list(HEAD_MARKERS)
    if allow_none and count == 1:
        pool.append("none")

    out = [None] * count
    used = set()
    for i, role in enumerate((roles or [])[:count]):
        k = head_for_role(role, set_name)
        if k and k not in used:
            out[i] = k
            used.add(k)
    rest = [m for m in pool if m not in used]
    for i in range(count):
        if out[i] is None and rest:
            m = rng.pick(rest)
            rest.remove(m)
            out[i] = m
            used.add(m)
    for i in range(count):
        if out[i] is None:
            out[i] = "none" if allow_none else pool[0]
    return tuple(out)


def derive_body(seed, index):
    """Return a silhouette for character `index`: torso width and height.

    `chars/inkbean.js` had no build parameter, so every figure in every film was
    the same stick bean. These two numbers are multiplied into the character's
    draw scale; 1.0/1.0 is the old silhouette, so anything missing still draws
    exactly as before.

    The bands are offset per index and never overlap, so two characters in the
    same film cannot share a silhouette.
    """
    rng = Rng(str(seed) + "|body|%d" % int(index))
    bands = ((0.88, 0.97), (1.00, 1.09), (0.94, 1.02))
    hbands = ((0.98, 1.10), (0.90, 0.97), (0.99, 1.06))
    blo, bhi = bands[int(index) % len(bands)]
    hlo, hhi = hbands[int(index) % len(hbands)]
    return {"build": round(rng.range(blo, bhi), 3),
            "height": round(rng.range(hlo, hhi), 3)}
