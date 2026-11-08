"""tools/render_report.py — write an auditable record for every finished episode.

Why: when episode 34 looks wrong you need to diff it against episode 12, not guess. The report
records what was produced, how it measures, and — critically — that a machine pass is NOT acceptance.

Adopted as an idea from https://github.com/kaomei/stickman-video-director (its renderer emits a
report with `human_review: "required; technical checks are not acceptance"`). Reimplemented for our
engine; nothing in engine/ was modified.

  python tools/render_report.py --project projects/<slug> [--video out/<Title>.mp4]

Writes projects/<slug>/build/report.json and prints a one-screen summary.
"""
import argparse, hashlib, json, os, subprocess, sys

try:
    import numpy as np
except ImportError:
    np = None


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def probe(video):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=width,height,r_frame_rate,codec_name,nb_frames:format=duration,size',
                        '-of', 'json', video], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f'ffprobe failed on {video}: {p.stderr[-400:]}')
    d = json.loads(p.stdout)
    st = d['streams'][0]
    num, den = st['r_frame_rate'].split('/')
    return {'codec': st['codec_name'], 'width': int(st['width']), 'height': int(st['height']),
            'fps': float(num) / float(den), 'frames': int(st.get('nb_frames') or 0),
            'duration': float(d['format']['duration']), 'bytes': int(d['format']['size'])}


def loudness(video):
    p = subprocess.run(['ffmpeg', '-v', 'info', '-i', video, '-af', 'volumedetect', '-vn',
                        '-f', 'null', '-'], capture_output=True, text=True)
    out = {}
    for line in p.stderr.splitlines():
        for k in ('mean_volume', 'max_volume'):
            if k in line:
                out[k] = float(line.split(k + ':')[1].strip().replace(' dB', ''))
    return out


def motion(video):
    """Reuse the shipped audit rather than reimplementing its metric."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # motion_audit needs numpy; a bare system interpreter usually lacks it, so prefer the kit venv.
    # Without this the audit silently fails and the report used to cry "ISSUES" about a video that
    # passes — a QC gate that invents failures is worse than no gate.
    venv = os.path.expanduser('~/.faceless-shorts/venv/Scripts/python.exe')
    py = venv if os.path.exists(venv) else sys.executable
    p = subprocess.run([py, os.path.join('tools', 'motion_audit.py'), video, '--json',
                        os.path.join(os.path.dirname(video) if os.path.dirname(video) else '.', 'motion.json')],
                       cwd=root, capture_output=True, text=True)
    j = os.path.join(root, os.path.dirname(video), 'motion.json') if os.path.dirname(video) else None
    d = {}
    if j and os.path.exists(j):
        d = json.load(open(j, encoding='utf-8'))
    windows = d.get('windows', [])
    err = ''
    if p.returncode != 0 and not windows:
        lines = (p.stderr or p.stdout or '').strip().splitlines()
        err = lines[-1] if lines else 'motion_audit exited %d' % p.returncode
        verdict = 'NOT RUN'          # could not run != failed the check
    else:
        verdict = 'OK' if p.returncode == 0 else 'ISSUES'
    return {'exit': p.returncode, 'verdict': verdict,
            'windows': len(windows),
            'min_motion': min((w['mean_motion'] for w in windows), default=None),
            'median_motion': (sorted(w['mean_motion'] for w in windows)[len(windows) // 2]
                              if windows else None),
            'issues': d.get('issues', []),
            'error': err,
            'note': 'change rate only; see docs/MOTION_BASELINE.md — NOT a liveliness metric'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--video', help='defaults to the single mp4 in <project>/out')
    ap.add_argument('--character', default='')
    ap.add_argument('--approved-by', default='', help="the owner's verbatim acceptance, if any")
    a = ap.parse_args()
    P = a.project
    vid = a.video
    if not vid:
        outdir = os.path.join(P, 'out')
        cands = [f for f in os.listdir(outdir) if f.endswith('.mp4')] if os.path.isdir(outdir) else []
        if len(cands) != 1:
            sys.exit(f'could not pick one video from {outdir} (found {cands}); pass --video')
        vid = os.path.join(outdir, cands[0])

    cfg = json.load(open(os.path.join(P, 'config.json'), encoding='utf-8'))
    story = json.load(open(os.path.join(P, 'story', 'shots.json'), encoding='utf-8'))
    lock = None
    lpath = os.path.join(P, 'story', 'style-lock.json')
    if os.path.exists(lpath):
        m = json.load(open(lpath, encoding='utf-8'))
        lock = {'character': m.get('character'), 'style': m.get('style'),
                'references': len(m.get('references', [])), 'approved_by': m.get('approved_by'),
                'status': m.get('status')}

    voice = cfg.get('voiceover') or story.get('voiceover')
    vpath = os.path.join(P, voice) if voice and not os.path.isabs(voice) else voice
    info = probe(vid)
    rep = {
        'schema': 'aitrends-render-report-v1',
        'project': os.path.basename(P), 'title': cfg.get('title'),
        'video': os.path.relpath(vid, P).replace('\\', '/'),
        'video_sha256': sha256(vid),
        'voice_sha256': sha256(vpath) if vpath and os.path.exists(vpath) else None,
        'voice_rate': 'unchanged; leading/trailing padding only',
        'aspect': cfg.get('aspect'), 'resolution': cfg.get('resolution'), 'style': cfg.get('style'),
        'codec': info['codec'], 'width': info['width'], 'height': info['height'],
        'fps': info['fps'], 'frames': info['frames'], 'duration': info['duration'],
        'bytes': info['bytes'], 'shot_count': len(story.get('shots', [])),
        'music_plan': [s.get('mood') for s in story.get('music', [])],
        'sfx_cues': sum(len(s.get('sfx', [])) for s in story.get('shots', [])),
        'audio': loudness(vid), 'motion': motion(vid), 'style_lock': lock,
        'character': a.character or (lock or {}).get('character'),
        'human_review': 'required; technical checks are not acceptance',
        'approved_by': a.approved_by or None,
    }
    dst = os.path.join(P, 'build', 'report.json')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(rep, open(dst, 'w', encoding='utf-8'), indent=1)

    print(f'{dst}\n  {rep["title"]}')
    print(f'  {rep["width"]}x{rep["height"]} {rep["fps"]:.2f} fps · {rep["frames"]} frames · '
          f'{rep["duration"]:.2f}s · {rep["bytes"]/1e6:.1f} MB · style {rep["style"]}')
    print(f'  shots {rep["shot_count"]} · sfx {rep["sfx_cues"]} · music {rep["music_plan"]}')
    print(f'  audio mean {rep["audio"].get("mean_volume")} dB / peak {rep["audio"].get("max_volume")} dB')
    mo = rep['motion']
    if mo['verdict'] == 'NOT RUN':
        print(f'  motion NOT RUN — {mo.get("error") or "motion_audit unavailable"}')
    else:
        print(f'  motion {mo["verdict"]} ({mo["windows"]} windows, min {mo["min_motion"]})')
    print(f'  style lock: {rep["style_lock"] or "none — not yet approved"}')
    print(f'  human_review: {rep["human_review"]}')
    if mo['issues']:
        for i in mo['issues'][:6]:
            print('  ISSUE ' + i)


if __name__ == '__main__':
    main()
