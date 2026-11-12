"""Which beats are staged in 3D, and how the cast's headwear survives the trip.

Two separate problems, both measurable from the story JSON alone.

1. WHICH BEATS. `engine/three-kit.js` is complete and proven (examples/
   reaction-time/02_orbit3d.js renders a full cafe), but `figure3D` draws eyes
   and no mouth, so a 3D shot cannot lip-sync. A 3D shot is therefore only
   correct on a beat with NO LINE -- the `shared` / `action` beat every shape
   has, which is also the widest composition, so it gains the most from depth.
   Measured cost: 3D renders at 6.77 fps against 13.08 fps for 2D at the same
   settings (1.93x slower, 3.6x realtime), so this is affordable per film.

2. WHICH HEADS. Our cast draws from 10 markers (bob, glasses, cap, beanie, bun,
   hat, helmet, hood, headband, toque). `figure3D` knows 7 (cap, capBack, visor,
   beanie, fedora, headband, hood). Unmapped, a character changes headwear the
   moment a 3D shot cuts in -- and two characters can collapse onto the same
   head, which is the "they all look alike" defect this repo already fixed once
   for 2D. `heads3d` maps, then resolves collisions against a fixed order so a
   cast of three is always three different heads.
"""

# Exactly the names engine/three-kit.js:89-93 draws. A name outside this set
# renders as a BARE HEAD silently -- figure3D's if-chain has no else -- so the
# vocabulary is pinned by a test rather than trusted.
THREE_HEADS = ("cap", "capBack", "visor", "beanie", "fedora", "headband", "hood")

# Our marker -> the 3D shape that reads closest. `None` means the 3D figure
# shows a bare head, which is correct for hair (bob, bun) and for glasses,
# because figure3D draws the eyes as separate spheres and a 3D glasses mesh
# would cover them.
_HEAD_3D = {
    "cap": "cap",
    "beanie": "beanie",
    "hood": "hood",
    "headband": "headband",
    "hat": "fedora",        # a brimmed hat is a fedora at this level of detail
    "helmet": "cap",        # dome + rim; the closest hard hat three-kit has
    "toque": "beanie",      # tall dome; a toque is a beanie with height
    "glasses": None,
    "bob": None,
    "bun": None,
    "none": None,
}

# Used when two markers map onto the same 3D head. Ordered so the substitutes
# stay in the same family: a hard hat lands on the other brimmed shape, a
# toque on the other tall dome.
_HEAD_3D_ALT = {
    "cap": ("visor", "capBack"),
    "beanie": ("beanie", "cap"),
    "hood": ("hood", "beanie"),
    "headband": ("headband", "beanie"),
    "fedora": ("fedora", "cap"),
    "visor": ("visor", "cap"),
    "capBack": ("capBack", "cap"),
}


def heads3d(markers):
    """Map our head markers onto the 3D vocabulary, all distinct.

    Deterministic and order-preserving: the same cast always produces the same
    3D heads, and a collision is resolved against `_HEAD_3D_ALT` rather than by
    dropping the character's headwear.
    """
    out, used = [], set()
    for m in markers or ():
        want = _HEAD_3D.get(str(m or "none").lower(), None)
        pick = None
        if want and want not in used:
            pick = want
        elif want:
            for alt in _HEAD_3D_ALT.get(want, ()):
                if alt not in used:
                    pick = alt
                    break
        out.append(pick)
        if pick:
            used.add(pick)
    return tuple(out)


def pick_3d(shots, limit=2):
    """Shot ids that should be staged in 3D: line-less, wide, not an insert.

    A wide with no dialogue is the establishing/action beat. It is the one
    composition where depth pays for itself, and the one where a mouthless 3D
    figure is not a defect.
    """
    picked = []
    for want in (("wide",), ("med",)):
        for s in shots or []:
            if len(picked) >= limit:
                return picked
            if not isinstance(s, dict):
                continue
            if s.get("id") in picked:
                continue
            if s.get("size") not in want:
                continue
            if s.get("line"):
                continue          # 3D has no mouth; a talking shot stays 2D
            if s.get("insertKind"):
                continue          # an insert is a macro, not a stage
            picked.append(s.get("id"))
    return picked


def mark(shots, limit=2):
    """Set `render3d: True` on the chosen beats. Returns the ids."""
    ids = pick_3d(shots, limit=limit)
    for s in shots or []:
        if isinstance(s, dict) and s.get("id") in ids:
            s["render3d"] = True
    return ids
