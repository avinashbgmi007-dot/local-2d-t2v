"""tools/render_report.py — write an auditable record for every finished episode.

Why: when episode 34 looks wrong you need to diff it against episode 12, not guess. The report
records what was produced, how it measures, and — critically — that a machine pass is NOT acceptance.

Adopted as an idea from https://github.com/kaomei/stickman-video-director (its renderer emits a
report with `human_review: "required; technical checks are not acceptance"`). Reimplemented for our
engine; nothing in engine/ was modified.

  python tools/render_report.py --project projects/<slug> [--video out/<Title>.mp4]

Writes projects/<slug>/build/report.json and prints a one-screen summary.

CHANGED 2026-11-12 (Phase A, motion gate can now fail):
  * main() used to print motion ISSUES and fall off the end, so it ALWAYS
    exited 0 -- while generate.py:169 treats a non-zero as fatal. Added the
    pure helper motion_exit_code(mo, fail_on_issues), an opt-in
    --fail-on-issues flag, and sys.exit(main()) so the exit code is real.
  * Default behaviour is UNCHANGED (exit 0). 'NOT RUN' never blocks: an absent
    audit tool is not a failed film. Activation is deliberately not wired into
    generate.py --strict yet; the motion metric counts camera drift as motion
    and needs calibration against real clips first.

CHANGED 2026-11-10 (independent falsifier):
  * `--approved-by` is REFUSED. The old flag let any generation run forge a
    passing approval. Only tools/record_approval.py may set approval state.
  * An existing approval is PRESERVED only when the new video_sha256 equals the
    hash that was approved. Re-rendering resets approval to pending, so an old
    acceptance can never be reused for different bytes.
  * probe() now selects a video stream rather than streams[0] (a muxed MP4 can
    list audio first), and all file handles are closed.
"""
import argparse, hashlib, json, os, re, subprocess, sys

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
    st = next((s for s in d['streams'] if 'width' in s), d['streams'][0])
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


def lufs(video):
    """Integrated loudness (BS.1770) and true peak — what platforms normalise to.

    `loudness()` above reports volumedetect mean/max dBFS, which is not a
    loudness standard: it cannot tell you whether a master hits -14 LUFS.
    Measured on the file that ships, not on an intermediate, so the number
    cannot go stale when a project is re-mastered.
    """
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', video,
                        '-af', 'loudnorm=I=-14:TP=-1.5:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True)
    hits = re.findall(r'\{[^{}]*\}', p.stderr or '', re.S)
    for h in reversed(hits):
        try:
            d = json.loads(h)
        except Exception:
            continue
        if 'input_i' in d:
            return {'integrated_lufs': float(d['input_i']),
                    'true_peak_dbtp': float(d['input_tp']),
                    'lra_lu': float(d['input_lra']),
                    'standard': 'ITU-R BS.1770-4 via ffmpeg loudnorm'}
    return {'error': 'could not measure loudness'}


def motion(video):
    """Reuse the shipped audit rather than reimplementing its metric."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # motion_audit needs numpy; a bare system interpreter usually lacks it, so prefer the kit venv.
    venv = os.path.expanduser('~/.faceless-shorts/venv/Scripts/python.exe')
    py = venv if os.path.exists(venv) else sys.executable
    p = subprocess.run([py, os.path.join('tools', 'motion_audit.py'), video, '--json',
                        os.path.join(os.path.dirname(video) if os.path.dirname(video) else '.', 'motion.json')],
                       cwd=root, capture_output=True, text=True)
    j = os.path.join(root, os.path.dirname(video), 'motion.json') if os.path.dirname(video) else None
    d = {}
    if j and os.path.exists(j):
        with open(j, encoding='utf-8') as fh:
            d = json.load(fh)
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


def prior_approval(dst, new_hash):
    """Keep a recorded approval ONLY if the delivered bytes are unchanged."""
    if not os.path.exists(dst):
        return {}
    try:
        with open(dst, encoding='utf-8') as fh:
            old = json.load(fh)
    except (ValueError, OSError):
        return {}
    if (old.get('approval_state') == 'approved'
            and old.get('approved_by')
            and old.get('approved_at')
            and old.get('approved_video_sha256') == new_hash):
        return {k: old[k] for k in ('approved_by', 'approved_at', 'approval_state',
                                    'approved_video_sha256', 'approved_reviewer')
                if k in old}
    return {}


def motion_exit_code(mo, fail_on_issues):
    """Return 1 only when motion issues should block the calling pipeline.

    Pure and side-effect free so the decision can be unit-tested without a
    video. 'NOT RUN' means the audit tool was unavailable, not that the film
    failed -- it must never masquerade as a failure. Activation is opt-in:
    the motion metric counts camera drift as motion and is not yet calibrated,
    so callers must ask for enforcement explicitly.
    """
    if fail_on_issues and mo.get('verdict') not in (None, 'NOT RUN') and mo.get('issues'):
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--fail-on-issues', action='store_true',
                    help='exit 1 when motion_audit reports issues (opt-in; metric not calibrated)')
    ap.add_argument('--video', help='defaults to the single mp4 in <project>/out')
    ap.add_argument('--character', default='')
    ap.add_argument('--approved-by', default='',
                    help='DEPRECATED and refused; use tools/record_approval.py')
    a = ap.parse_args()
    if a.approved_by:
        sys.exit('REFUSED: --approved-by can forge an approval from a generation run. '
                 'A human must watch the film, then use tools/record_approval.py.')
    P = a.project
    vid = a.video
    if not vid:
        outdir = os.path.join(P, 'out')
        cands = [f for f in os.listdir(outdir) if f.endswith('.mp4')] if os.path.isdir(outdir) else []
        if len(cands) != 1:
            sys.exit(f'could not pick one video from {outdir} (found {cands}); pass --video')
        vid = os.path.join(outdir, cands[0])

    with open(os.path.join(P, 'config.json'), encoding='utf-8') as fh:
        cfg = json.load(fh)
    with open(os.path.join(P, 'story', 'shots.json'), encoding='utf-8') as fh:
        story = json.load(fh)
    lock = None
    lpath = os.path.join(P, 'story', 'style-lock.json')
    if os.path.exists(lpath):
        with open(lpath, encoding='utf-8') as fh:
            m = json.load(fh)
        lock = {'character': m.get('character'), 'style': m.get('style'),
                'references': len(m.get('references', [])), 'approved_by': m.get('approved_by'),
                'status': m.get('status')}

    voice = cfg.get('voiceover') or story.get('voiceover')
    vpath = os.path.join(P, voice) if voice and not os.path.isabs(voice) else voice
    info = probe(vid)
    vhash = sha256(vid)
    rep = {
        'schema': 'aitrends-render-report-v1',
        'project': os.path.basename(P), 'title': cfg.get('title'),
        'video': os.path.relpath(vid, P).replace('\\', '/'),
        'video_sha256': vhash,
        'voice_sha256': sha256(vpath) if vpath and os.path.exists(vpath) else None,
        'voice_rate': 'unchanged; leading/trailing padding only',
        'aspect': cfg.get('aspect'), 'resolution': cfg.get('resolution'), 'style': cfg.get('style'),
        'codec': info['codec'], 'width': info['width'], 'height': info['height'],
        'fps': info['fps'], 'frames': info['frames'], 'duration': info['duration'],
        'bytes': info['bytes'], 'shot_count': len(story.get('shots', [])),
        'music_plan': [s.get('mood') for s in story.get('music', [])],
        'sfx_cues': sum(len(s.get('sfx', [])) for s in story.get('shots', [])),
        'audio': loudness(vid), 'lufs': lufs(vid), 'motion': motion(vid), 'style_lock': lock,
        'character': a.character or (lock or {}).get('character'),
        'human_review': 'required; technical checks are not acceptance',
        'approved_by': None, 'approval_state': 'pending',
        'approved_at': None, 'approved_video_sha256': None,
    }
    dst = os.path.join(P, 'build', 'report.json')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rep.update(prior_approval(dst, vhash))
    with open(dst, 'w', encoding='utf-8') as fh:
        json.dump(rep, fh, indent=1)

    print(f'{dst}\n  {rep["title"]}')
    print(f'  {rep["width"]}x{rep["height"]} {rep["fps"]:.2f} fps · {rep["frames"]} frames · '
          f'{rep["duration"]:.2f}s · {rep["bytes"]/1e6:.1f} MB · style {rep["style"]}')
    print(f'  shots {rep["shot_count"]} · sfx {rep["sfx_cues"]} · music {rep["music_plan"]}')
    print(f'  audio mean {rep["audio"].get("mean_volume")} dB / peak {rep["audio"].get("max_volume")} dB')
    lu = rep.get('lufs') or {}
    if 'integrated_lufs' in lu:
        tgt = cfg.get('loudness', -14)
        err = lu['integrated_lufs'] - tgt
        print(f'  loudness {lu["integrated_lufs"]:.2f} LUFS (target {tgt}) · '
              f'TP {lu["true_peak_dbtp"]:.2f} dBTP · LRA {lu["lra_lu"]:.1f} LU · '
              f'error {err:+.2f} LU')
    else:
        print(f'  loudness NOT MEASURED — {lu.get("error") or "unavailable"}')
    mo = rep['motion']
    if mo['verdict'] == 'NOT RUN':
        print(f'  motion NOT RUN — {mo.get("error") or "motion_audit unavailable"}')
    else:
        print(f'  motion {mo["verdict"]} ({mo["windows"]} windows, min {mo["min_motion"]})')
    print(f'  style lock: {rep["style_lock"] or "none — not yet approved"}')
    print(f'  approval  : {rep["approval_state"]} (approved_by={rep["approved_by"]})')
    print(f'  human_review: {rep["human_review"]}')
    if mo['issues']:
        for i in mo['issues'][:6]:
            print('  ISSUE ' + i)
    return motion_exit_code(mo, a.fail_on_issues)


if __name__ == '__main__':
    sys.exit(main())
