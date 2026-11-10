"""
tools/archetypes.py — the 12-archetype template registry for aitrends-2d-studio.

This is the `template` half of the `template` + `params` interpreter described in
docs/MINI_SERIES_TEMPLATE_PLAN.md §4. It is PURE DATA + validation helpers and does
not touch engine/ or any protected file. It is consumed by tools/template_interpreter.py.

Why this exists (council gap, 2026-11-10): the pipeline has zero `template` keys and no
scenes/templates.js. engine/player.js:74 already spreads shot.params into `info`, so the
only missing piece is (a) a named-archetype registry and (b) a codegen step that turns
`template` + `params` in shots.json into registered shot JS. This file is (a).

Guards (owner rule, 2026-11-10): enhance the flow, no monetisation harm, no quality
degrade, no efficiency degrade. This module is pure data + warnings -> zero runtime cost
unless the interpreter is actually run.

Closed slot vocabularies below are extracted from the live engine (engine/rig2d.js POSES,
chars/acting.js PRESETS, engine/styles.js STYLES, engine/player.js transition handling),
NOT from the planning doc's aspirational counts, so pre-flight warnings match reality.
"""
from __future__ import annotations

# ---- closed slot vocabularies (extracted from the live engine) ----
STYLES = ['dusk', 'midnight', 'golden', 'neon', 'storybook']
# 27 pose keys from engine/rig2d.js POSES (verified: `pose(name) => POSES[name] || POSES.stand`,
# so `stand` is the canonical default and MUST be in this list).
POSES = [
    'cheer', 'crossArms', 'crouch', 'dive', 'explain', 'facepalm', 'fall', 'handsOnHead',
    'holdFront', 'jump', 'kick', 'kneel', 'lie', 'phone', 'point', 'pointUp', 'reach',
    'ready', 'relaxed', 'sad', 'shrug', 'sit', 'sitBack', 'stand', 'talk', 'think', 'wave',
]
# expression names: union of the THREE name spaces that `expr`/`exprTo` can feed —
# acting.js PRESETS (inkbean path), inkbean.js face presets, and rig2d.js discrete face
# presets. Kept permissive on purpose: a false-positive here would flag a legitimate shot.
_EXPR_ACTING = [
    'neutral', 'listening', 'curious', 'worried', 'hurt', 'angry', 'surprised',
    'relieved', 'hopeful', 'tired', 'ashamed', 'determined',
]
_EXPR_INKBEAN = ['neutral', 'surprised', 'shocked', 'sad', 'worried', 'smirk', 'angry']
_EXPR_RIG2D = [
    'neutral', 'happy', 'joy', 'smile', 'surprised', 'shocked', 'scared', 'worried',
    'nervous', 'angry', 'determined', 'sad', 'cry', 'smirk', 'sleepy', 'thinking',
    'confused', 'awe',
]
EXPRESSIONS = sorted(set(_EXPR_ACTING) | set(_EXPR_INKBEAN) | set(_EXPR_RIG2D))
# transitions actually handled by engine/player.js renderFrame
TRANSITIONS = ['cut', 'fade', 'dip', 'dipWhite', 'flash', 'whip', 'zoom']

# ---- the 12 named archetypes (docs/MINI_SERIES_TEMPLATE_PLAN.md §4) ----
# size: which draw branch the generic body uses.
# generator: True  -> tools/template_interpreter.py can emit it from the proven body.
#             False -> custom hero shot; author hand-writes it (the plan's "3-5 hero shots").
# cam:  default camera overrides, merged into params ONLY when the param is absent.
#       keys map 1:1 to the body's p.camZ0 / p.camZ1 / p.camX0 / p.camX1 / p.camY0 / p.camY1.
# freeze: default freeze fraction (number = fraction of shot); only applied if unset.
ARCHETYPES = {
    'establish-push': {
        'size': 'wide', 'generator': True, 'people': 1,
        'cam': {'camZ0': 1.00, 'camZ1': 1.045},
        'note': 'Wide establishing shot with a gentle push-in. The settle-the-world image.',
    },
    'medium-two-shot': {
        'size': 'med', 'generator': True, 'people': 2,
        'cam': {'camZ0': 1.02, 'camZ1': 1.065},
        'note': 'Medium two-character shot.',
    },
    'over-shoulder': {
        'size': 'med', 'generator': True, 'people': 2,
        'cam': {'camZ0': 1.02, 'camZ1': 1.065, 'camX1': -0.06},
        'note': 'Over-the-shoulder, slightly off-axis.',
    },
    'giant-face': {
        'size': 'close', 'generator': True, 'people': 1,
        'cam': {},
        'note': 'Giant close-up face; the set is still there, just soft.',
    },
    'insert-object': {
        'size': 'insert', 'generator': True, 'people': 0,
        'cam': {},
        'note': 'Macro insert of a prop; the object is the line.',
    },
    'pull-out-bookend': {
        'size': 'wide', 'generator': True, 'people': 1,
        'cam': {'camZ0': 1.045, 'camZ1': 1.00},
        'note': 'Pull-out bookend (zoom-out) that resets/opens a scene.',
    },
    'freeze-frame': {
        'size': 'wide', 'generator': True, 'people': 1, 'freeze': 0.70,
        'cam': {'camZ0': 1.00, 'camZ1': 1.00},
        'note': 'Freeze-frame beat: the visual clock clamps, audio keeps running.',
    },
    'title-card': {
        'size': 'card', 'generator': True, 'people': 0,
        'cam': {},
        'note': 'Title card overlay. params: title, sub, attribution.',
    },
    'end-card': {
        'size': 'card', 'generator': True, 'people': 0,
        'cam': {},
        'note': 'End card overlay. params: title, sub, attribution, part.',
    },
    'transition-whip': {
        'size': 'wide', 'generator': True, 'people': 1,
        'cam': {'camZ0': 1.00, 'camZ1': 1.02},
        'note': 'Whip-pan transition shot; also set shot.in = {type:"whip"} on the boundary.',
    },
    'blueprint-diagram': {
        'size': None, 'generator': False,
        'note': 'Custom diagram (axes, labelled nodes). Hand-write as a hero shot.',
    },
    'lowpoly-3d': {
        'size': None, 'generator': False,
        'note': '3D scene via engine three-kit. Hand-write as a hero shot.',
    },
}


def names() -> list[str]:
    return list(ARCHETYPES.keys())


def get(name: str):
    return ARCHETYPES.get(name)


def is_valid(name: str) -> bool:
    return name in ARCHETYPES


def summary() -> dict:
    return {
        n: {
            'size': a.get('size'),
            'generator': a.get('generator'),
            'people': a.get('people'),
            'note': a.get('note'),
        }
        for n, a in ARCHETYPES.items()
    }


def validate_shot(shot: dict) -> list[str]:
    """Pre-flight warnings for one shot's template + params. Warnings, not hard errors:
    the engine already fails loudly (SHOT ERROR) on bad values, so this only catches the
    typos a human author is likely to make before a (slow) render."""
    warns: list[str] = []
    tmpl = shot.get('template')
    if tmpl is None:
        return warns
    if not is_valid(tmpl):
        warns.append(f"unknown template '{tmpl}' (not in the 12-archetype registry)")
        return warns
    a = ARCHETYPES[tmpl]
    if a.get('generator') is False:
        warns.append(f"template '{tmpl}' is a hand-written hero shot; the interpreter will skip it")
    p = shot.get('params') or {}
    bg = p.get('bg') or shot.get('grade')
    if bg is not None and bg not in STYLES:
        warns.append(f"params.bg '{bg}' is not a known style {STYLES}")
    for key in ('pose', 'pose2', 'pose3'):
        v = p.get(key)
        if v is not None and v not in POSES:
            warns.append(f"params.{key} '{v}' is not a known pose {POSES}")
    for key in ('expr', 'expr2', 'expr3', 'exprTo', 'exprTo2', 'exprTo3'):
        v = p.get(key)
        if v is not None and v not in EXPRESSIONS:
            warns.append(f"params.{key} '{v}' is not a known expression {EXPRESSIONS}")
    tr = shot.get('in')
    if isinstance(tr, dict) and tr.get('type') not in TRANSITIONS:
        warns.append(f"shot.in.type '{tr.get('type')}' is not a known transition {TRANSITIONS}")
    return warns


if __name__ == '__main__':
    import json
    print(json.dumps(summary(), indent=2))
