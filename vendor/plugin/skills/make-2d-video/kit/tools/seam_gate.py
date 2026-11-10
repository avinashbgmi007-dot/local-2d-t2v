#!/usr/bin/env python
"""tools/seam_gate.py — does anything CARRY across every cut, or does the film cut between slides?

  python tools/seam_gate.py --project projects/<name> [--auto] [--json out.json] [--strict]

--auto  discover characters, props and sets from the project source in addition to the fixed alias
        layer below, and honour an optional `cut_intent` on the incoming shot. Default mode is
        unchanged, so existing projects produce exactly the same report.

Method, not code: the "every beat is carried" discipline is feitangyuan/onetake's, and the
boundary-as-design-object idea is heygen-com/hyperframes' seam-gate. Neither is copied: onetake is
PolyForm Noncommercial (unusable for a monetised channel), and hyperframes' verifier works by querying
DOM element opacity and position over CDP, which this engine has no registry for.

So this gate is deliberately NOT a perceptual metric. It answers one factual question per cut, by
reading the shot source: which named entities does shot N draw, and which does shot N+1 draw?

  PASS  at least one entity is on both sides of the cut
  WARN  nothing is shared — the two shots are unrelated pictures, which is the slideshow failure
  INFO  shared, but only the set (kitchen/door): the room carried, nobody did; or the cut is declared
        with `cut_intent` under --auto

Two honest limits, stated rather than hidden:
  1. PRESENCE IS NOT CONTINUITY. onetake's real claim is that a carrier must TRANSFORM — a bar
     collapses into a line that becomes the next scene's grid. That cannot be read off source text.
     This gate finds cuts with no candidate carrier at all; it does not certify the good ones.
  2. Entity extraction is textual. A shot that draws a character through an indirect helper this file
     does not know about will read as absent. In default mode the vocabulary table below is the whole
     contract; extend it when a new shared helper is added, or the gate silently under-reports. `--auto`
     adds source discovery, but it is still textual and still has this limit.

Exit code: 0 with no WARN, 1 with WARN under --strict, else 0.
"""
import argparse, io, json, os, re, sys

# entity name -> regexes that mean "this shot draws it". More than one label can match: keysHand()
# draws both a hand and a key. The indirect helpers MUST be listed here or the gate under-reports:
# keysHand() draws her hand and beanFace(outfit: RAE) draws her face, and neither matches a
# person()/face() call.
VOCAB = [
    ('rae',   [r"person\(\s*g\s*,\s*'rae'", r"face\(\s*g\s*,\s*'rae'",
               r"outfit:\s*RAE\b", r"keysHand\("]),
    ('nils',  [r"person\(\s*g\s*,\s*'nils'", r"face\(\s*g\s*,\s*'nils'",
               r"outfit:\s*NILS\b", r"nilsAtCounter\("]),
    # (?<!\.) matters: `Object.keys(CAST)` is ordinary JS and used to match as a "keys" carrier,
    # so every boundary PASSed with "carried: keys" on projects that have no key prop at all.
    ('keys',  [r"(?<!\.)\bkeys\(", r"keysHand\("]),
    ('bag',   [r"wornBag\(", r"heldBag\("]),
    ('latch', [r"HANDLE\(\)", r"DOOR_X\("]),
]
SET_ONLY = ('kitchen', 'door')     # shared room, not a shared subject

# --auto: functions in scenes/sets/*.js that draw a PROP or a character helper, not a room. They stay
# out of the set-only bucket so sharing one is a real carrier (PASS), not just "the room carried".
PROP_FUNCS = {
    'keys', 'keyshand', 'wornbag', 'heldbag', 'bag', 'latch',
    'phone', 'cup', 'paper', 'ball', 'pointer', 'tablet', 'flashlight', 'nail', 'meter',
}
# cut_intent values -> INFO under --auto. `eyeline` belongs here: a face -> what it sees ->
# reaction carries the GAZE, which no scan of the source can find, so it has to be declared
# or a legitimate cut is reported dead.
DECLARED = ('reverse', 'match', 'intentional', 'declared', 'eyeline')
# Helper names that draw the same thing under different spellings; keep the report readable.
CANON = {'wornbag': 'bag', 'heldbag': 'bag', 'keyshand': 'keys'}


def declared_cast(project):
    """Cast per shot, read from story/shots.json.

    A GENERATED project passes the cast as a variable — person(g, who, ...) with who = p.who —
    so no regex over the shot source can see it. Without this the shot reads as empty and a
    live cut is reported as dead. The story spec is the source of truth, so read it directly
    rather than inferring identity from text.
    """
    sj = os.path.join(project, 'story', 'shots.json')
    out = {}
    if not os.path.isfile(sj):
        return out
    try:
        with io.open(sj, encoding='utf-8') as fh:
            st = json.load(fh)
    except Exception:
        return out
    for s in st.get('shots', []):
        sid = s.get('id')
        if not sid:
            continue
        pr = s.get('params') or {}
        raw = list(pr.get(k) for k in ('who', 'who2', 'who3') if pr.get(k))
        if isinstance(pr.get('who'), list):
            raw = pr['who'] + [pr.get(k) for k in ('who2', 'who3') if pr.get(k)]
        names = {str(n).strip().lower() for n in raw if n}
        if names:
            out.setdefault(sid, set()).update(names)
        # Template shots are data-driven; their manifest is the entity source of truth.
        if s.get('template'):
            obj = pr.get('object') or {}
            if isinstance(obj, dict) and obj.get('kind'):
                out.setdefault(sid, set()).add(str(obj['kind']).lower())
            if pr.get('set'):
                out.setdefault(sid, set()).add(str(pr['set']).lower())
    return out


def shot_entities(root, project):
    """Return {shot_id: set(entities)} by scanning every file under scenes/shots/."""
    sdir = os.path.join(project, 'scenes', 'shots')
    if not os.path.isdir(sdir):
        sys.exit(f'no scenes/shots directory under {project}')
    ids = []
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith('.js'):
            continue
        text = io.open(os.path.join(sdir, fn), encoding='utf-8', errors='replace').read()
        # split on registerShot('sNNN' so each chunk belongs to exactly one shot
        parts = re.split(r"registerShot\(\s*['\"]([A-Za-z][\w-]*)['\"]", text)
        for i in range(1, len(parts) - 1, 2):
            sid, body = parts[i], parts[i + 1]
            found = set()
            for name, pats in VOCAB:
                if any(re.search(p, body) for p in pats):
                    found.add(name)
            if re.search(r"\bkitchen\(", body):
                found.add('kitchen')
            ids.append((sid, found, fn))
    out = {}
    for sid, found, fn in ids:
        out[sid] = found
    for sid, names in declared_cast(project).items():
        out.setdefault(sid, set()).update(names)
    return out, {sid: fn for sid, found, fn in ids}


def scene_funcs(project):
    """Exported function names in scenes/sets/*.js, lowercased. Used only by --auto."""
    sdir = os.path.join(project, 'scenes', 'sets')
    funcs = set()
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith('.js'):
                continue
            text = io.open(os.path.join(sdir, fn), encoding='utf-8', errors='replace').read()
            funcs.update(m.lower() for m in re.findall(r'export\s+function\s+(\w+)', text))
    return funcs


def cast_names(project):
    """Const names in scenes/cast.js, lowercased. Used only by --auto."""
    path = os.path.join(project, 'scenes', 'cast.js')
    if not os.path.isfile(path):
        return set()
    text = io.open(path, encoding='utf-8', errors='replace').read()
    return {m.lower() for m in re.findall(r'export\s+const\s+([A-Z][A-Z0-9_]*)', text)}


def auto_shot_entities(project):
    """Discover what each shot draws from the source, then merge the fixed alias layer.

    Characters: person()/face(), `outfit: CONST` for a cast const and `<name>AtCounter()`. Props: a
    short list of shared helpers. Sets: exported functions in scenes/sets/. The fixed VOCAB is kept
    because a helper such as keysHand() draws a named hand that no source scan can attribute. This is
    still a presence test, not a continuity proof — the same honest limit as the default mode.
    """
    sdir = os.path.join(project, 'scenes', 'shots')
    if not os.path.isdir(sdir):
        sys.exit(f'no scenes/shots directory under {project}')
    funcs = scene_funcs(project)
    cast = cast_names(project)
    set_only = tuple(sorted(f for f in funcs
                            if f not in PROP_FUNCS and not f.endswith('atcounter')))
    ids = []
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith('.js'):
            continue
        text = io.open(os.path.join(sdir, fn), encoding='utf-8', errors='replace').read()
        parts = re.split(r"registerShot\(\s*['\"]([A-Za-z][\w-]*)['\"]", text)
        for i in range(1, len(parts) - 1, 2):
            sid, body = parts[i], parts[i + 1]
            found = set()
            for m in re.finditer(r"(?:person|face)\(\s*g\s*,\s*'([a-z0-9_-]+)'", body):
                found.add(m.group(1).lower())
            for m in re.finditer(r"outfit:\s*([A-Z][A-Z0-9_]*)", body):
                who = m.group(1).lower()
                if who in cast:
                    found.add(who)
            for m in re.finditer(r"(\w+)AtCounter\(", body):
                who = m.group(1).lower()
                if who in cast:
                    found.add(who)
            for prop in PROP_FUNCS:
                if re.search(rf"(?<!\.)\b{re.escape(prop)}\(", body, re.I):
                    found.add(CANON.get(prop, prop))
            for s in set_only:
                if re.search(rf"(?<!\.)\b{re.escape(s)}\(", body, re.I):
                    found.add(s)
            # The fixed table is still a useful alias layer: a helper such as keysHand() draws a
            # named character's hand without naming her, and no source scan can infer that. Keep
            # its labels alongside the discovered ones; --auto adds, it does not replace.
            for name, pats in VOCAB:
                if any(re.search(p, body) for p in pats):
                    found.add(name)
            ids.append((sid, found, fn))
    out = {}
    for sid, found, fn in ids:
        out[sid] = found
    for sid, names in declared_cast(project).items():
        out.setdefault(sid, set()).update(names)
    return out, {sid: fn for sid, found, fn in ids}, set_only


def cuts(shots, ents, set_only=SET_ONLY, honour_intent=False):
    """Evaluate every consecutive boundary in the manifest.

    `honour_intent` is only true under --auto, so the default report for an existing project stays
    byte-for-byte the same even if someone adds a `cut_intent` field.
    """
    rows = []
    for a, b in zip(shots, shots[1:]):
        ea, eb = ents.get(a['id'], set()), ents.get(b['id'], set())
        shared = ea & eb
        subj = sorted(shared - set(set_only))
        kind = (b.get('in') or {}).get('type', 'cut')
        intent = b.get('cut_intent') if honour_intent else None
        if subj:
            verdict, why = 'PASS', 'carried: ' + ', '.join(subj)
        elif intent in DECLARED:
            verdict, why = 'INFO', f'declared {intent}: no shared subject'
        elif shared:
            verdict, why = 'INFO', 'only the room carried: ' + ', '.join(sorted(shared))
        else:
            verdict, why = 'WARN', f'nothing carried across this {kind}'
        row = dict(boundary=f"{a['id']}->{b['id']}", at=b['start'], transition=kind,
                   verdict=verdict, detail=why,
                   left=sorted(ea), right=sorted(eb))
        if intent:
            row['intent'] = intent
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--json', dest='json_out')
    ap.add_argument('--strict', action='store_true', help='exit 1 if any boundary is still WARN')
    ap.add_argument('--auto', action='store_true',
                    help='discover characters/props/sets from the project source; honour cut_intent')
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proj = a.project if os.path.isabs(a.project) else os.path.join(root, a.project)
    story = json.loads(io.open(os.path.join(proj, 'story', 'shots.json'), encoding='utf-8').read())
    shots = story['shots']
    if a.auto:
        ents, _, set_only = auto_shot_entities(proj)
    else:
        ents, _ = shot_entities(root, proj)
        set_only = SET_ONLY

    missing = [s['id'] for s in shots if s['id'] not in ents]
    if missing:
        print(f'NOTE  no scene code found for: {", ".join(missing)} '
              f'(registered elsewhere, or not built)')
    unjudged = a.auto and not any(ents.values())
    if unjudged:
        print('NOTE  no named entities discovered; the gate cannot judge this project. '
              'Name the cast/props in source, or waive the report with a reason.')

    rows = cuts(shots, ents, set_only, honour_intent=a.auto)
    warn = [r for r in rows if r['verdict'] == 'WARN']
    info = [r for r in rows if r['verdict'] == 'INFO']

    print(os.path.basename(proj.rstrip('/\\')))
    if a.auto:
        print('  auto entity detection')
    info_label = 'info' if a.auto else 'room-only'
    dead_label = 'unjudged' if unjudged else 'dead'
    print(f'  {len(shots)} shots, {len(rows)} boundaries, '
          f'{len(rows)-len(warn)-len(info)} carried, {len(info)} {info_label}, {len(warn)} {dead_label}')
    print()
    for r in rows:
        print(f"  {r['verdict']:<5} {r['boundary']:<13} @{r['at']:>5.2f}s  {r['transition']:<6} {r['detail']}")
    print()
    print('  presence is not continuity: a PASS only says a candidate carrier exists on both sides.')
    if unjudged:
        print('\nUNJUDGED — no named entities were discovered; the cuts above are not evidence of a '
              'slideshow.')
    elif warn:
        print(f'\n{len(warn)} DEAD CUT(S) — no shared subject. Fix by carrying a person, a prop or the '
              f'camera across, or by declaring a match cut.')
    elif any(r.get('intent') for r in rows):
        print('\nSEAM OK — every boundary has a carrier or is declared.')
    else:
        print('\nSEAM OK — every boundary has a candidate carrier.')

    if a.json_out:
        payload = dict(project=os.path.basename(proj), boundaries=rows,
                       dead=len(warn), room_only=len(info))
        if a.auto:
            declared = [r for r in rows if r['verdict'] == 'INFO' and r.get('intent')]
            payload['mode'] = 'auto'
            payload['declared'] = len(declared)
            payload['room_only'] = len(info) - len(declared)
            payload['unjudged'] = unjudged
        io.open(a.json_out, 'w', encoding='utf-8').write(json.dumps(payload, indent=1))
        print(f'wrote {a.json_out}')

    sys.exit(1 if (a.strict and (warn or unjudged or missing)) else 0)


if __name__ == '__main__':
    main()
