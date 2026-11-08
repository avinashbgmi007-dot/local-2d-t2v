"""tools/style_lock.py — refuse to proceed when the character has drifted.

Why this exists: over a 50-episode series, "keep the look consistent" is not achievable by
discipline. It is achievable by a gate that fails loudly. This pins approved reference frames by
content hash; any change to a pinned asset becomes a build failure instead of a surprise you spot
after upload.

Mechanism taken from https://github.com/kaomei/stickman-video-director (`b4-style-lock.mjs`) and
reimplemented for our Python tooling. No file in engine/ was modified.

  python tools/style_lock.py snapshot --project projects/<slug> --frames 1.0,4.2,7.2 \\
      --character inkbean --approved-by "<the owner's exact words>" [--note "..."]
  python tools/style_lock.py verify --project projects/<slug>
  python tools/style_lock.py check  --project projects/<slug>

snapshot  render the named times, store them as the approved set, write the manifest
verify    validate the manifest: schema, approval record, distinct paths, PNG signature, dimensions
check     re-render the same times and fail if any frame no longer matches byte for byte

A lock is only meaningful once a human has approved the frames, so snapshot refuses to run without
--approved-by and stores those words verbatim. Technical checks are not acceptance.
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, time

SCHEMA = 'aitrends-style-lock-v1'
STILLS = os.path.join('build', 'stills')          # render.mjs writes stills here and nowhere else
LOCKED = os.path.join('story', 'style-lock')      # where approved references are stored


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def png_dims(path):
    with open(path, 'rb') as fh:
        head = fh.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'{path} is not a PNG')
    w, h = struct.unpack('>II', head[16:24])
    return int(w), int(h)


def manifest_path(P):
    return os.path.join(P, 'story', 'style-lock.json')


def render_times(P, times):
    """Ask the engine to render stills at these global seconds; return [(t, path)]."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(['node', 'render.mjs', '--project', P, '--stills', ','.join(times)],
                   cwd=root, check=True, capture_output=True)
    d = os.path.join(P, STILLS)
    have = []
    for f in sorted(os.listdir(d)):
        if not f.endswith('.png') or 'sheet' in f:
            continue
        try:                                    # label is sanitised: "1.0" arrives as 1s_1.00.png
            have.append((float(f.split('s_')[0].rstrip('s')), os.path.join(d, f)))
        except ValueError:
            continue
    got = []
    for t in times:
        near = [h for h in have if abs(h[0] - float(t)) < 0.05]
        if not near:
            sys.exit(f'no still produced for t={t}s; render.mjs gave {sorted(h[0] for h in have)}')
        got.append((t, near[0][1]))
    return got


def cmd_snapshot(a):
    if not a.approved_by:
        sys.exit('refusing to lock unapproved frames.\n'
                 'Re-run with --approved-by "<the owner\'s exact words>" once you have accepted them.')
    P, times = a.project, a.frames.split(',')
    os.makedirs(os.path.join(P, LOCKED), exist_ok=True)
    refs = []
    for t, cand in render_times(P, times):
        rel = os.path.join('story', 'style-lock', f'{float(t):.2f}s.png').replace('\\', '/')
        dst = os.path.normpath(os.path.join(P, rel))
        shutil.copyfile(cand, dst)
        data = open(dst, 'rb').read()
        w, h = png_dims(dst)
        refs.append({'time': float(t), 'path': rel, 'sha256': sha256(data), 'width': w, 'height': h})
    cfg = json.load(open(os.path.join(P, 'config.json'), encoding='utf-8'))
    m = {'schema': SCHEMA, 'status': 'approved', 'character': a.character,
         'project': os.path.basename(P), 'style': cfg.get('style'),
         'resolution': cfg.get('resolution'), 'aspect': cfg.get('aspect'),
         'required': len(refs), 'approved_by': a.approved_by, 'note': a.note,
         'snapshotted_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'references': refs}
    json.dump(m, open(manifest_path(P), 'w', encoding='utf-8'), indent=1)
    print(f'wrote {manifest_path(P)} — {len(refs)} approved references')
    for r in refs:
        print(f"  t={r['time']:>5.2f}s  {r['sha256'][:16]}  {r['width']}x{r['height']}")


def cmd_verify(a):
    P = a.project
    m = json.load(open(manifest_path(P), encoding='utf-8'))
    bad = []
    if m.get('schema') != SCHEMA:
        bad.append(f'schema {m.get("schema")!r}, expected {SCHEMA!r}')
    if m.get('status') != 'approved':
        bad.append(f'status {m.get("status")!r} — locking unapproved frames is not a lock')
    if not m.get('approved_by'):
        bad.append('no approved_by record')
    refs = m.get('references', [])
    if len(refs) != len({r['path'] for r in refs}):
        bad.append('reference paths are not distinct')
    if len(refs) < m.get('required', 1):
        bad.append(f'{len(refs)} references present, manifest requires {m.get("required")}')
    root = os.path.abspath(P)
    for r in refs:
        fp = os.path.normpath(os.path.join(root, r['path']))
        if not fp.startswith(root + os.sep) or not os.path.isfile(fp):
            bad.append(f'{r["path"]}: escapes the project or is missing'); continue
        try:
            w, h = png_dims(fp)
        except ValueError as e:
            bad.append(str(e)); continue
        if (w, h) != (r['width'], r['height']):
            bad.append(f'{r["path"]}: now {w}x{h}, declared {r["width"]}x{r["height"]}')
        if sha256(open(fp, 'rb').read()) != r['sha256']:
            bad.append(f'{r["path"]}: FINGERPRINT MISMATCH — restore the approved resource')
    if bad:
        print('STYLE LOCK INVALID')
        for x in bad:
            print('  ' + x)
        sys.exit(1)
    print(f'STYLE LOCK OK — {len(refs)} references, character {m["character"]!r}, '
          f'style {m.get("style")!r}, approved_by {m["approved_by"]!r}')


def cmd_check(a):
    P = a.project
    m = json.load(open(manifest_path(P), encoding='utf-8'))
    drift = []
    times = [str(x['time']) for x in m['references']]
    for r, (t, cand) in zip(m['references'], render_times(P, times)):
        now = sha256(open(cand, 'rb').read())
        if now != r['sha256']:
            drift.append((t, r['sha256'][:16], now[:16]))
    if drift:
        print('STYLE DRIFT DETECTED — refusing to proceed')
        for t, was, now in drift:
            print(f'  t={t}s  approved {was}  now renders as {now}')
        print('\nEither restore the approved look, or re-snapshot deliberately with a fresh '
              'approval record. Do not quietly update the lock.')
        sys.exit(1)
    print(f'STYLE LOCK HELD — {len(m["references"])} frames match the approved set exactly')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('verify'); v.add_argument('--project', required=True)
    s = sub.add_parser('snapshot'); s.add_argument('--project', required=True)
    s.add_argument('--frames', required=True, help='comma-separated global seconds')
    s.add_argument('--character', required=True); s.add_argument('--approved-by', default='')
    s.add_argument('--note', default='')
    c = sub.add_parser('check'); c.add_argument('--project', required=True)
    a = ap.parse_args()
    {'verify': cmd_verify, 'snapshot': cmd_snapshot, 'check': cmd_check}[a.cmd](a)


if __name__ == '__main__':
    main()
