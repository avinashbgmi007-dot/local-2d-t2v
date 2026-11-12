"""Acting — what the BODY does, derived from the beat.

Why this exists
  Every generated film wrote `pose="stand"` for every character in every shot,
  so the only movement in the picture was the mouth. The renderer already had
  the whole vocabulary and nothing asked for it:

    engine/rig2d.js:8   20 poses (point, shrug, cheer, think, facepalm, ...)
    director.py:135     walkAt() — a walk whose phase is driven by DISTANCE, so
                        the feet do not skate when the shot is retimed
    director.py:128     poseAt(t, base, gAt, gPose) — a gesture that lands ON a
                        word, via `gesture: {word, pose}` and `atWord`
    director.py:1081    footfalls computed from the walk geometry

  This module decides those three things from the beat role and the line, the
  same way location/cast/audio/style are decided: from the story, deterministically,
  with no constant that ignores the scene.

Determinism
  Seeded from the beat role plus the line, so the same story always renders the
  same performance. A QC failure has to be reproducible.
"""
import re

from .core import Rng

# role -> base pose. Chosen so the body says what the beat means:
# a problem is thought about, an opposition shrugs, an action braces.
# Covers EVERY role in every shape (fresh/shapes.py has four shapes and their
# roles differ: two_hander uses claim/counter/doubt/concession/decision/shared,
# countdown uses urgency/stakes/obstacle/attempt). A role that is missing here
# silently falls back to one pose, which is exactly the bug this replaces — so
# a test pins the vocabulary against SHAPES.
_ROLE_POSE = {
    # mystery_beat / cold_open / countdown
    "establish": "relaxed",
    "hook": "talk",
    # `evidence` is the insert beat: no body is drawn, so this pose is never
    # used. It is present so the vocabulary covers every role in every shape
    # rather than falling through to a silent default.
    "evidence": "relaxed",
    "problem": "think",
    "turn": "point",
    "opposition": "shrug",
    "reveal": "explain",
    "action": "ready",
    "payoff": "explain",
    "bookend": "relaxed",
    "countdown": "ready",
    "urgency": "ready",
    "stakes": "think",
    "obstacle": "crossArms",
    "attempt": "reach",
    # two_hander
    "claim": "talk",
    "counter": "crossArms",
    "doubt": "think",
    "concession": "relaxed",
    "decision": "point",
    "shared": "relaxed",
}

# role -> the gesture that lands on a word. None = no gesture for this beat.
_ROLE_GESTURE = {
    "establish": None,
    "hook": "talk",
    "problem": "handsOnHead",
    "turn": "point",
    "opposition": "shrug",
    "reveal": "explain",
    "action": "cheer",
    "payoff": "pointUp",
    "bookend": "wave",
    "countdown": "ready",
    "urgency": "pointUp",
    "stakes": "handsOnHead",
    "obstacle": "facepalm",
    "attempt": "reach",
    "claim": "talk",
    "counter": "crossArms",
    "doubt": "shrug",
    "concession": "relaxed",
    "decision": "point",
    "shared": "wave",
}

# Words that carry no gesture: a hand does not point at "the".
_STOPWORDS = frozenset("""a an the and or but if then so to of in on at for with
from by as is are was were be been am do does did not no it its it's this that
these those i me my we us our you your he she they them his her their there
here what which who whom when where why how all just very really""".split())

# role -> (from, to) frame fractions. Only the FIRST figure moves; the second
# stays put, so a two-hander never swaps sides mid-shot.
_ROLE_WALK = {
    "establish": (0.12, 0.34),   # walks in and settles
    "action": (0.30, 0.46),      # steps forward
    "bookend": (0.40, 0.78),     # leaves frame
    "shared": (0.34, 0.52),      # closes the distance between the two
    "attempt": (0.28, 0.44),     # moves on the obstacle
}

_WALKABLE_SIZES = ("wide",)

# role -> transition INTO the shot. A new scene deserves a dip; a reaction is a
# hard cut. Only 'cut' was ever emitted before.
_ROLE_TRANSITION = {
    "establish": ("dip", 0.28),
    "reveal": ("dip", 0.26),
    "hook": ("zoom", 0.24),
    "turn": ("whip", 0.22),
    "action": ("flash", 0.18),
    "decision": ("whip", 0.20),
    "urgency": ("zoom", 0.22),
    "shared": ("dip", 0.24),
}


def _norm(word):
    return re.sub(r"[^a-z0-9']", "", str(word or "").lower())


def derive_pose(role, line=None):
    """Base pose for a beat. Always a legal rig pose."""
    return _ROLE_POSE.get(str(role or ""), "talk")


# A `close` shot crops to the head and torso, so an arm gesture is off-screen.
# Measured on the rendered film: the close-up frame showed only the face. Those
# beats carry an expression change instead, which is what a close-up is for.
_GESTURE_SIZES = ("wide", "med")


def derive_gesture(role, line, seed=None, size=None):
    """A gesture that lands on a word of this line, or None.

    `director.py:794` resolves `gesture.word` through `wordAt()`, which matches
    a word whose start is at or after the cue — so the word must appear in the
    line verbatim. It is picked here, not left to the renderer.
    """
    if size is not None and str(size) not in _GESTURE_SIZES:
        return None
    text = str(line or "").strip()
    if not text:
        return None
    pose = _ROLE_GESTURE.get(str(role or ""))
    if not pose:
        return None
    words = [w for w in text.split() if _norm(w)]
    content = [w for w in words if _norm(w) not in _STOPWORDS] or words
    if not content:
        return None
    # A gesture on the FIRST word is indistinguishable from a static pose: it is
    # already blended in when the shot starts (measured — the handsOnHead cue
    # landed on "something", the opening word, and the arm never appeared to
    # move). Prefer a content word in the back half of the line, so the arm
    # travels while the line is being spoken.
    half = max(0, len(words) // 2)
    late = [w for w in content if words.index(w) >= half]
    rng = Rng("%s|gesture|%s" % (seed or "acting", text))
    word = rng.pick(late or content)
    return {"word": _norm(word), "pose": pose, "blend": 0.26}


def derive_walk(role, size, seed=None):
    """A walk for a wide shot, or None. from != to, so it actually travels.

    Only `wide` shots walk: at med/close the figure already fills the frame and
    a walk would just slide out of it.
    """
    if str(size or "") not in _WALKABLE_SIZES:
        return None
    span = _ROLE_WALK.get(str(role or ""))
    if not span:
        return None
    rng = Rng("%s|walk|%s" % (seed or "acting", role))
    a, b = span
    # jitter so two films with the same beat do not walk the same path
    a = round(min(0.95, max(0.05, a + rng.range(-0.02, 0.02))), 3)
    b = round(min(0.95, max(0.05, b + rng.range(-0.02, 0.02))), 3)
    if abs(b - a) < 0.05:
        b = round(min(0.95, a + 0.12), 3)
    return {"from": a, "to": b, "u0": 0.0, "u1": 0.82,
            "stride": 30, "lift": 13, "bob": 3, "arm": 18}


def derive_transition(role, index):
    """The transition INTO a shot. The first shot always fades up."""
    if int(index) == 0:
        return {"type": "fade", "dur": 0.5}
    kind = _ROLE_TRANSITION.get(str(role or ""))
    if not kind:
        return {"type": "cut"}
    return {"type": kind[0], "dur": kind[1]}
