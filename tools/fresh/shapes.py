"""fresh.shapes - a small library of dramatic shapes.

A shape is a beat sequence, not a topic. Two episodes of one series must differ
in SHAPE, not just in subject, or the channel reads as mass production.

Budgets are measured from the owner-approved film (projects/cine_release:
8 shots, 10.775s, 1.35s/shot, 4.75s of holds, longest line 6 words) and from the
MIT budget method in THIRD_PARTY.md. Line cap 8 words. Hook <= 2.0s.

Every expression name here is in chars/acting.js PRESETS. The old arc used
'excited', 'smirk' and 'shocked', none of which exist; faceAt() fell back to
neutral, so the reaction shot had no reaction.
"""
import re

from .story_schema import PROPS, INSERT_KINDS

STOP = frozenset("""a an the of for and or to in on at with without is are was were
be been this that these those it its as by from into about over after before
between during now just very really cute happy sad big small new old""".split())
VERBS = frozenset("""writes write wrote makes make made does do did goes go went
gets get got takes take took gives give gave finds find found sees see saw
says say said tells tell told comes come came runs run ran""".split())

# concept keyword -> insert kind. Deterministic, and it makes the picture about
# the concept instead of a random object.
INSERT_HINTS = (
    ("document", ("letter", "document", "paper", "report", "note", "contract", "will")),
    ("phone",    ("phone", "text", "message", "call", "app", "notification", "chat")),
    ("photo",    ("photo", "picture", "image", "photograph", "portrait")),
    ("card",     ("card", "ticket", "invitation", "ace", "playing")),
    ("screen",   ("screen", "code", "computer", "monitor", "ai", "robot", "data")),
)


def subject_of(concept):
    """Longest content word. A heuristic, not understanding -- see ADR 0004."""
    words = [w for w in re.findall(r"[a-z]+", str(concept).lower())
             if w not in STOP and w not in VERBS]
    if not words:
        return "thing"
    return max(words, key=lambda w: (len(w), -words.index(w)))


def insert_for(concept):
    low = str(concept).lower()
    for kind, hints in INSERT_HINTS:
        if any(re.search(r"\b" + re.escape(h) + r"\b", low) for h in hints):
            return kind
    return "screen"


def prop_for(insert_kind):
    """Only mug/book/phone are implemented (director.py:1024)."""
    if insert_kind in ("phone", "screen"):
        return "phone"
    if insert_kind in ("document", "photo", "card"):
        return "book"
    return "mug"


# Beat fields: role, size, hold, line (a template or None), who ("A"/"B"/"AB"/None),
# intent, insert, prop, freeze, expr, exprTo. {s}=subject, {a}=name A, {b}=name B.
SHAPES = {
    # The owner-approved skeleton (DEMO_STORY / cine_release): 8 beats.
    # Holds total 4.60s (cine_release: 4.75s). The opening hold is 0.35 rather
    # than 0.50 so the first beat lands inside the 2.0s hook window.
    "mystery_beat": {"grains": 2, "beats": [
        {"role": "establish", "size": "wide",   "hold": 0.35, "who": "AB",
         "line": "Nobody expected the {s}.", "intent": None,
         "insert": False, "prop": False, "freeze": False},
        {"role": "problem",   "size": "med",    "hold": 0.35, "who": "A",
         "line": "Something about it is wrong.", "intent": None,
         "expr": "neutral", "exprTo": "worried",
         "insert": False, "prop": False, "freeze": False},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline",
         "insert": True, "prop": False, "freeze": False},
        {"role": "turn",      "size": "close",  "hold": 0.30, "who": "A",
         "line": "Don't touch it.", "intent": "eyeline",
         "expr": "worried", "exprTo": "determined",
         "insert": False, "prop": True, "freeze": False},
        {"role": "opposition","size": "med",    "hold": 0.30, "who": "B",
         "line": "It's only a {s}, {a}.", "intent": "reverse",
         "expr": "curious",
         "insert": False, "prop": False, "freeze": False},
        {"role": "action",    "size": "wide",   "hold": 1.50, "who": "AB",
         "line": None, "intent": None,
         "insert": False, "prop": False, "freeze": True},
        {"role": "payoff",    "size": "close",  "hold": 0.45, "who": "A",
         "line": "That's why.", "intent": None,
         "expr": "determined", "exprTo": "relieved",
         "insert": False, "prop": False, "freeze": False},
        {"role": "bookend",   "size": "wide",   "hold": 0.60, "who": "AB",
         "line": "The {s} stays.", "intent": None, "expr": "relieved",
         "insert": False, "prop": False, "freeze": False},
    ]},
    # The object before the people. 6 beats, 3.50s holds.
    "cold_open": {"grains": 2, "beats": [
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": None,
         "insert": True, "prop": False, "freeze": False},
        {"role": "reveal",    "size": "wide",   "hold": 0.50, "who": "AB",
         "line": "Left for us.", "intent": "reverse",
         "insert": False, "prop": False, "freeze": False},
        {"role": "problem",   "size": "med",    "hold": 0.40, "who": "B",
         "line": "A {s}. Here.", "intent": None, "expr": "curious",
         "insert": False, "prop": False, "freeze": False},
        {"role": "turn",      "size": "close",  "hold": 0.30, "who": "A",
         "line": "Someone wanted us to see.", "intent": "reverse",
         "expr": "neutral", "exprTo": "determined",
         "insert": False, "prop": False, "freeze": False},
        {"role": "opposition","size": "med",    "hold": 0.35, "who": "B",
         "line": "Or someone wanted us gone.", "intent": "reverse",
         "expr": "worried",
         "insert": False, "prop": False, "freeze": False},
        {"role": "payoff",    "size": "wide",   "hold": 1.20, "who": "AB",
         "line": None, "intent": None,
         "insert": False, "prop": False, "freeze": True},
    ]},
    # Two people, one axis, crossed four times. 7 beats, 3.65s holds.
    "two_hander": {"grains": 2, "beats": [
        {"role": "claim",     "size": "med",    "hold": 0.40, "who": "A",
         "line": "The {s} is mine.", "intent": None, "expr": "determined",
         "insert": False, "prop": False, "freeze": False},
        {"role": "counter",   "size": "med",    "hold": 0.35, "who": "B",
         "line": "It was never yours.", "intent": "reverse", "expr": "angry",
         "insert": False, "prop": False, "freeze": False},
        {"role": "doubt",     "size": "close",  "hold": 0.30, "who": "A",
         "line": "Then why keep it?", "intent": "reverse",
         "expr": "determined", "exprTo": "hurt",
         "insert": False, "prop": False, "freeze": False},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline",
         "insert": True, "prop": False, "freeze": False},
        {"role": "concession","size": "med",    "hold": 0.40, "who": "B",
         "line": "Because I was afraid.", "intent": "reverse",
         "expr": "angry", "exprTo": "ashamed",
         "insert": False, "prop": False, "freeze": False},
        {"role": "decision",  "size": "close",  "hold": 0.45, "who": "A",
         "line": "Keep it, then.", "intent": "reverse",
         "expr": "hurt", "exprTo": "relieved",
         "insert": False, "prop": True, "freeze": False},
        {"role": "shared",    "size": "wide",   "hold": 1.00, "who": "AB",
         "line": None, "intent": None,
         "insert": False, "prop": False, "freeze": False},
    ]},
    # Pressure from the first frame. 8 beats, 4.25s holds.
    "countdown": {"grains": 3, "beats": [
        {"role": "urgency",   "size": "close",  "hold": 0.30, "who": "A",
         "line": "Ten seconds.", "intent": None, "expr": "worried",
         "insert": False, "prop": False, "freeze": False},
        {"role": "stakes",    "size": "wide",   "hold": 0.50, "who": "AB",
         "line": "The {s} decides it.", "intent": None,
         "insert": False, "prop": False, "freeze": False},
        {"role": "obstacle",  "size": "med",    "hold": 0.40, "who": "B",
         "line": "You can't reach it.", "intent": "reverse", "expr": "tired",
         "insert": False, "prop": False, "freeze": False},
        {"role": "evidence",  "size": "insert", "hold": 0.75, "who": None,
         "line": None, "intent": "eyeline",
         "insert": True, "prop": False, "freeze": False},
        {"role": "decision",  "size": "close",  "hold": 0.30, "who": "A",
         "line": "Watch me.", "intent": "eyeline",
         "expr": "worried", "exprTo": "determined",
         "insert": False, "prop": True, "freeze": False},
        {"role": "attempt",   "size": "med",    "hold": 0.35, "who": "B",
         "line": "Impossible.", "intent": "reverse", "expr": "surprised",
         "insert": False, "prop": False, "freeze": False},
        {"role": "action",    "size": "wide",   "hold": 1.20, "who": "AB",
         "line": None, "intent": None,
         "insert": False, "prop": False, "freeze": True},
        {"role": "payoff",    "size": "close",  "hold": 0.45, "who": "A",
         "line": "It was.", "intent": None,
         "expr": "determined", "exprTo": "hopeful",
         "insert": False, "prop": False, "freeze": False},
    ]},
}


def fill(shape, subject, name_a, name_b):
    """Resolve a shape's line templates. Returns new dicts; SHAPES is not mutated."""
    out = []
    for b in shape["beats"]:
        d = dict(b)
        d["line"] = (b["line"] or "").format(s=subject, a=name_a, b=name_b) or None
        out.append(d)
    return out
