#!/usr/bin/env python3
"""tools/speech_track.py — turn measured dialogue into a per-speaker mouth clock.

The engine used to open a mouth with `sin(t*22)` gated by a word window, on the
FIRST figure of every shot regardless of who was speaking. This builds the real
thing: a per-speaker loudness envelope sampled from the actual voice recording,
so picture follows performance instead of an invented rhythm.

  python3 tools/speech_track.py --project build/myfilm
  python3 tools/speech_track.py --project build/myfilm --words path/words.json

Inputs (either is enough):
  timeline/words.json          {"words":[{word,start,end,speaker?}]} or a bare list
  voiceover file from config   (config.json "voiceover", relative to the project)
  voice/<SPEAKER>.wav          optional per-speaker stems (preferred for overlap)

Output: timeline/speech.json
  {schema:"speech-envelope-v1", fps, speakers, tracks:{ID:[0..1 per frame]},
   words:[...], source, notes:[...]}

Rules that matter:
  * Envelope comes from the recording. If there is no recording, this REFUSES to
    invent one — a sine wave is not lip sync, and pretending otherwise hides the
    gap. Word windows alone still route mouths to the right speaker (square gate).
  * Word windows gate the envelope, so silence between words closes the mouth.
  * With one shared voice file and two speakers, the gate is the only separation.
    Overlapping speakers cannot be separated from a mixdown: pass per-speaker
    stems (voice/<ID>.wav) when dialogue overlaps. This is reported, not hidden.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json, load_audio          # noqa: E402

ENV_SR = 8000          # envelope analysis rate (plenty for mouth shapes)
ATTACK = 0.018         # s — mouths open fast
RELEASE = 0.055        # s — and close a little slower
GATE_FLOOR = 0.02      # fraction of the speaker's own peak counted as "silent"
PERCENTILE = 92        # robust loudness reference, so one plosive can't flatten speech


def _frames(total, fps):
    return int(round(float(total) * int(fps)))


def _words_of(path):
    raw = load_json(path)
    words = raw.get("words", raw) if isinstance(raw, dict) else raw
    out = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        try:
            s, e = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if e < s:
            s, e = e, s
        out.append({"word": str(w.get("word", "")).strip(), "start": round(s, 4),
                    "end": round(e, 4),
                    **({"speaker": str(w["speaker"])} if w.get("speaker") else {})})
    out.sort(key=lambda w: (w["start"], w["end"]))
    return out


def _one_pole(x, seconds, sr):
    """Asymmetric attack/release follower, vectorised via scipy's lfilter."""
    from scipy.signal import lfilter
    if not len(x):
        return x
    a = float(np.exp(-1.0 / max(1.0, seconds * sr)))
    up = lfilter([1 - a], [1, -a], x)
    dn = lfilter([1 - float(np.exp(-1.0 / max(1.0, RELEASE * sr)))],
                 [1, -float(np.exp(-1.0 / max(1.0, RELEASE * sr)))], x)
    return np.where(x > up, up, np.maximum(dn, x * 0.0))


def _rms_envelope(samples, sr, nframes, fps):
    """Per-frame RMS of the recording, smoothed with a fast attack / slow release."""
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    hop = sr / float(fps)
    env = np.zeros(nframes, dtype=np.float64)
    win = max(1, int(round(hop)))
    for f in range(nframes):
        a = int(round(f * hop))
        b = min(len(samples), a + win)
        if b > a:
            seg = samples[a:b]
            env[f] = float(np.sqrt(np.mean(seg * seg)))
    env = _one_pole(env, ATTACK, fps)
    ref = float(np.percentile(env[env > 0], PERCENTILE)) if np.any(env > 0) else 0.0
    if ref <= 1e-9:
        return env, 0.0
    env = env / ref
    env[env < GATE_FLOOR] = 0.0
    return np.clip(env, 0.0, 1.0), ref


def build(project, words_path=None, fps=None, stem_dir=None):
    project = os.path.abspath(project)
    cfg = load_json(os.path.join(project, "config.json"))
    stem_dir = stem_dir or cfg.get("voiceStems")
    if stem_dir:
        stem_dir = os.path.abspath(os.path.join(project, stem_dir))
    fps = int(fps or cfg.get("fps") or 24)
    tl = os.path.join(project, "timeline")
    words_path = words_path or os.path.join(tl, "words.json")
    if not os.path.isfile(words_path):
        sys.exit(f"no word timing at {words_path} — run narrate.py / parse_script.py first")
    words = _words_of(words_path)
    if not words:
        sys.exit(f"{words_path} has no usable words")

    scenes = load_json(os.path.join(project, "story", "shots.json"))
    shots = scenes.get("shots", [])
    total = float(scenes.get("duration") or scenes.get("total")
                  or (shots[-1].get("end", shots[-1]["start"] + shots[-1]["dur"]) if shots else 0))
    total = max(total, max(w["end"] for w in words) + 1.0 / fps)
    nframes = _frames(total, fps)

    # who exists in this film? shot-level speaker wins over cast order
    cast_obj = scenes.get("cast")
    cast = list(cast_obj) if isinstance(cast_obj, dict) else [
        c.get("id") for c in (cast_obj or []) if isinstance(c, dict)]
    speakers = []
    for w in words:
        if w.get("speaker") and w["speaker"] not in speakers:
            speakers.append(w["speaker"])
    for s in shots:
        sp = s.get("speaker") or (s.get("params") or {}).get("speaker")
        if sp and sp not in speakers:
            speakers.append(sp)
    if not speakers:
        speakers = [cast[0]] if cast else ["NARRATOR"]

    # attach a speaker to untagged words from the shot that owns the timestamp
    def owner(t):
        for s in shots:
            end = s.get("end", s["start"] + s.get("dur", 0))
            if s["start"] - 1e-6 <= t < end - 1e-6:
                p = s.get("params") or {}
                if s.get("speaker") or p.get("speaker"):
                    return s.get("speaker") or p["speaker"]
                who = p.get("who")
                if isinstance(who, list):
                    return who[0] if who else None
                return who
        return None

    untagged = 0
    for w in words:
        if not w.get("speaker"):
            w["speaker"] = owner(w["start"]) or speakers[0]
            untagged += 1

    notes = []
    if untagged:
        notes.append(f"{untagged} word(s) had no speaker tag; assigned from the owning shot.")

    # recordings: per-speaker stems preferred, else the project voiceover
    shared = cfg.get("voiceover")
    shared_path = os.path.join(project, shared) if shared else None
    if shared_path and not os.path.isfile(shared_path):
        shared_path = None
    stems = {}
    for sp in speakers:
        for cand in (os.path.join(project, "voice", f"{sp}.wav"),
                     os.path.join(project, "voice", f"{sp.lower()}.wav"),
                     os.path.join(project, "build", "voice", f"{sp}.wav"),
                     os.path.join(stem_dir, f"{sp}.wav") if stem_dir else None):
            if not cand:
                continue
            if os.path.isfile(cand):
                stems[sp] = cand
                break

    tracks, refs, measured = {}, {}, []
    for sp in speakers:
        path = stems.get(sp) or shared_path
        gate = np.zeros(nframes, dtype=np.float64)
        # Gate on the frame INSTANT (f/fps), exactly like the engine's word lookup.
        # floor(start)/ceil(end) widened every window by up to a frame, which opened
        # the mouth in the consonant gaps between words.
        instants = np.arange(nframes, dtype=np.float64) / float(fps)
        for w in words:
            if w.get("speaker") != sp:
                continue
            gate[(instants >= w["start"] - 1e-9) & (instants <= w["end"] + 1e-9)] = 1.0
        if path:
            audio = load_audio(path, sr=ENV_SR)
            env, ref = _rms_envelope(audio, ENV_SR, nframes, fps)
            tracks[sp] = [round(float(v), 4) for v in (env * gate)]
            refs[sp] = round(ref, 6)
            measured.append(sp)
        else:
            tracks[sp] = [round(float(v), 4) for v in gate]
            refs[sp] = None
        if not gate.any():
            notes.append(f"{sp}: no spoken words in the timeline.")

    if measured:
        src = "stems" if stems else "shared"
        notes.append(f"envelope measured from the {src} recording at {fps} fps.")
        if not stems and len(speakers) > 1:
            notes.append("one shared voice file: speakers are separated by word windows only. "
                         "Overlapping dialogue needs voice/<SPEAKER>.wav stems.")
    else:
        notes.append("NO RECORDING FOUND — word-window gate only (no measured mouth shape). "
                     "Render the voice first for performance-driven animation.")

    out = {"schema": "speech-envelope-v1", "fps": fps, "total": round(total, 4),
           "speakers": speakers, "tracks": tracks, "words": words,
           "measured": measured, "reference_rms": refs,
           "source": os.path.relpath(words_path, project), "notes": notes}
    save_json(os.path.join(tl, "speech.json"), out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--words")
    ap.add_argument("--fps", type=int)
    ap.add_argument("--stems", help="directory of per-speaker <SPEAKER>.wav stems")
    a = ap.parse_args()
    out = build(a.project, a.words, a.fps, a.stems)
    print(f"speech track: {len(out['speakers'])} speaker(s), {len(out['words'])} words, "
          f"{out['fps']} fps, measured={out['measured'] or 'none'}")
    for sp in out["speakers"]:
        tr = out["tracks"][sp]
        active = sum(1 for v in tr if v > 0.05)
        print(f"  {sp:10s} speaking {active / out['fps']:.2f}s  peak {max(tr):.2f}")
    for n in out["notes"]:
        print(f"  note: {n}")


if __name__ == "__main__":
    main()
