"""tools/render_cached.py — render a film one shot at a time and never re-render an unchanged shot.

Why: `render.mjs` renders the whole timeline. Fix one shot in a 3-minute film and you pay for all of
it. This wraps it — it does NOT modify render.mjs — by rendering each shot's own range into a cached
clip keyed by everything that could change its pixels, then concatenating.

Adopted as an idea from https://github.com/kaomei/stickman-video-director, which writes
`cache/<key>.mp4` via `<key>.partial.mp4` then renames. That atomicity is reproduced deliberately: a
killed render must never leave a half-written clip in the cache.

Cache key covers, on purpose:
  - the shot's own manifest entry (so editing one shot invalidates only that shot)
  - the ENGINE fingerprint (engine/**, chars/**, render.mjs, player.html, package.json)
  - the PROJECT CODE fingerprint (scenes/**, story/shots.json, config.json, story/style-lock.json)
  - the render scale, so a --scale 0.5 preview clip can never be reused as a full-res final
The last two matter: without them a code edit would silently reuse stale frames. That was a real bug
found by testing, not a hypothetical.

  python tools/render_cached.py --project projects/<slug> [--scale 0.5]
  python tools/render_cached.py --project projects/<slug> --report   # plan only, renders nothing
  python tools/render_cached.py --project projects/<slug> --clear

Writes projects/<slug>/build/video_cached.mp4 (silent). Run audio/mix.py on it as usual.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join('build', 'cache')
CODE_EXT = ('.js', '.mjs', '.html', '.json', '.css')


def h_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(h, base, rels):
    """Fold the named files/directories into the running hash, in a stable order."""
    for rel in sorted(rels):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            h.update(rel.encode()); h.update(h_file(p).encode())
        elif os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames.sort()
                for f in sorted(filenames):
                    if not f.endswith(CODE_EXT):
                        continue
                    fp = os.path.join(dirpath, f)
                    key = os.path.relpath(fp, base).replace('\\', '/')
                    h.update(key.encode()); h.update(h_file(fp).encode())


def engine_fingerprint():
    h = hashlib.sha256()
    hash_tree(h, ROOT, ['engine', 'chars', 'render.mjs', 'player.html', 'package.json'])
    return h.hexdigest()[:12]


def project_fingerprint(P):
    h = hashlib.sha256()
    hash_tree(h, P, ['scenes', 'story/shots.json', 'config.json', 'story/style-lock.json'])
    return h.hexdigest()[:12]


def shot_key(shot, fps, res, aspect, style, scale, engfp, projfp):
    payload = (json.dumps(shot, sort_keys=True, ensure_ascii=False)
               + f'|{fps}|{res}|{aspect}|{style}|scale:{scale}|eng:{engfp}|proj:{projfp}')
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--scale', default='1')
    ap.add_argument('--report', action='store_true', help='show the hit/miss plan without rendering')
    ap.add_argument('--clear', action='store_true')
    a = ap.parse_args()
    P = a.project
    cfg = json.load(open(os.path.join(P, 'config.json'), encoding='utf-8'))
    story = json.load(open(os.path.join(P, 'story', 'shots.json'), encoding='utf-8'))
    shots = story['shots']
    cdir = os.path.join(P, CACHE)
    if a.clear:
        shutil.rmtree(cdir, ignore_errors=True)
        print(f'cleared {cdir}')
        return
    os.makedirs(cdir, exist_ok=True)

    engfp, projfp = engine_fingerprint(), project_fingerprint(P)
    print(f'engine {engfp} · project code {projfp}')

    plan, hits = [], 0
    for s in shots:
        key = shot_key(s, cfg.get('fps', 24), cfg.get('resolution'), cfg.get('aspect'),
                       cfg.get('style'), a.scale, engfp, projfp)
        clip = os.path.join(cdir, f'{s["id"]}_{key}.mp4')
        hit = os.path.isfile(clip)
        hits += hit
        plan.append((s, clip, hit))
        print(f'  {s["id"]}  {s["start"]:6.2f}-{s["end"]:6.2f}  {key}  {"HIT" if hit else "MISS"}')
    print(f'{hits}/{len(shots)} cache hits')
    if a.report:
        return

    parts = []
    for s, clip, hit in plan:
        if hit:
            parts.append(clip); continue
        tmp = clip.replace('.mp4', '.partial.mp4')
        cmd = ['node', 'render.mjs', '--project', P, '--from', str(s['start']),
               '--to', str(s['end']), '--out', tmp]
        if a.scale != '1':
            cmd += ['--scale', a.scale]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(tmp):
            sys.exit(f'{s["id"]} failed to render:\n{(r.stderr or r.stdout)[-800:]}')
        os.replace(tmp, clip)          # atomic swap, so an interrupt cannot poison the cache
        parts.append(clip)

    out = os.path.join(P, 'build', 'video_cached.mp4')
    lst = os.path.join(cdir, 'concat.txt')
    with open(lst, 'w', encoding='utf-8') as fh:
        for p in parts:
            fh.write("file '" + os.path.abspath(p).replace('\\', '/') + "'\n")
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                        '-c', 'copy', '-movflags', '+faststart', out], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'concat failed: {r.stderr[-600:]}')
    total = sum(s['end'] - s['start'] for s in shots)
    print(f'wrote {out} — {len(shots)} shots, {hits} reused, target {total:.2f}s')
    print('next: python audio/mix.py --project ' + P)


if __name__ == '__main__':
    main()
