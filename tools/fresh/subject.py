"""fresh.subject - what the film is ABOUT, as something the renderer can draw.

Defect this closes (owner report 2026-11-13): the concept "a fairy tale about
three kids who find a dragon" produced eight shots of two adults in an office
saying the word "dragon". `fresh/shapes.py:subject_of` had already put the noun
in the dialogue -- nothing ever put it on screen, because the renderer's only
vocabularies were people (`chars/inkbean.js`) and hand props (`rig2d.js`).

The vocabulary here is CLOSED and must equal `KINDS` in chars/creature.js.
`DerivedSubjectTests.test_vocabulary_matches_the_renderer` reads the JS and
fails if the two drift -- the same class of bug that made `chars/markers.js`
throw on an advertised-but-missing marker.

`None` is the honest answer for most concepts. An abstract subject ("regret",
"the algorithm") is NOT a creature: inventing a bear for it would be worse than
showing nothing, so the caller falls back to the prop/insert path.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must equal chars/creature.js KINDS, in the same order. The module draws the
# SUBJECT, which is a creature OR a thing: "a jar that never empties" is a real
# short, and the old pipeline answered it with a mug.
CREATURE_KINDS = ("dragon", "wolf", "bird", "fish", "horse", "cat", "bear",
                  "jar", "lantern", "chest", "sword")

# Objects are subjects too, but they are not BODIES: a jar is a tabletop thing
# and must not loom in the foreground the way a dragon does. Measured on
# projects/jar_check: a 3.4x foreground jar cropped by the frame edge read as a
# teal box, not a jar; the same jar at 1.35x beside the cast read correctly.
OBJECT_KINDS = ("jar", "lantern", "chest", "sword")
ANIMAL_KINDS = tuple(k for k in CREATURE_KINDS if k not in OBJECT_KINDS)

# kind -> words. Matched on WORD BOUNDARIES (substring matching once made
# "happens" match "app" in fresh/audio.py).
CREATURE_WORDS = (
    ("dragon", ("dragon", "dragons", "wyrm", "drake", "wyvern", "serpent")),
    ("wolf", ("wolf", "wolves", "hound", "dog", "dogs", "puppy", "coyote",
              "fox", "jackal")),
    ("bird", ("bird", "birds", "eagle", "crow", "raven", "owl", "sparrow",
              "pigeon", "hawk", "parrot", "chicken", "duck", "goose")),
    ("fish", ("fish", "shark", "whale", "eel", "salmon", "trout", "octopus")),
    ("horse", ("horse", "horses", "pony", "stallion", "mare", "unicorn",
               "donkey", "camel")),
    ("cat", ("cat", "cats", "kitten", "tiger", "lion", "panther", "leopard",
             "lynx")),
    ("bear", ("bear", "bears", "monster", "beast", "creature", "giant", "troll",
              "ogre", "yeti", "elephant", "cow", "bull", "pig", "sheep", "goat")),
    # Objects. A story about a jar, a lamp or a blade is a story about a THING,
    # and the thing has to be in the picture.
    ("jar", ("jar", "pot", "urn", "vase", "bottle", "flask")),
    ("lantern", ("lantern", "lamp", "candle", "torch", "beacon")),
    ("chest", ("chest", "trunk", "box", "crate", "suitcase", "coffer")),
    ("sword", ("sword", "blade", "knife", "dagger", "axe", "spear")),
)

# Scale words. A "giant" that is the size of a dog is a wrong picture, and the
# renderer's creature units are already character-sized.
_BIG = ("giant", "huge", "enormous", "massive", "colossal", "towering", "big")
_SMALL = ("tiny", "small", "little", "baby", "mini", "young", "newborn")


def _match(text, words):
    low = str(text or "").lower()
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words)


def creature_kind(concept):
    """Return a drawable creature kind named by the concept, or None."""
    for kind, words in CREATURE_WORDS:
        if _match(concept, words):
            return kind
    return None


def creature_scale(concept):
    """1.0 unless the concept says the thing is outsized or small."""
    if _match(concept, _BIG):
        return 1.30
    if _match(concept, _SMALL):
        return 0.66
    return 1.0


def derive_subject(concept, noun=None):
    """Return the story-level `subject` block, or None.

    `noun` is the spoken noun (`shapes.subject_of`) so the picture and the
    dialogue cannot name different things.
    """
    kind = creature_kind(concept)
    if kind is None:
        return None
    return {"kind": kind, "scale": creature_scale(concept),
            "noun": (noun or kind)}
