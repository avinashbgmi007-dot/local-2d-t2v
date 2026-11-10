#!/usr/bin/env python3
"""
narrate.py — Kokoro TTS narration + word timings + SHOT RETIMING.

Why this exists (and why it is not just "TTS"):
  talkAmount() in engine/core.js returns 0 whenever the current time falls
  outside a word's [start,end] window. So LIP SYNC IS ONLY AS ACCURATE AS
  timeline/words.json. Kokoro pads every utterance with 50-110 ms of silence,
  so placing raw samples at a shot's start offsets every word by that amount.
  This tool trims the head/tail, measures the real speech, then REBUILDS the
  shot timing from the measured speech instead of a fixed grid.

What it writes
  build/voice.wav          trimmed lines placed at their (new) shot starts
  timeline/words.json      [{word,start,end}] in GLOBAL seconds, gap-split
  story/shots.json         start/end retimed: shot = speech + hold
  config.json              voiceover + captions + captionStyle + duration

Run with the faceless-shorts venv python:
  <venv>/Scripts/python.exe tools/narrate.py --project projects/foo [--voice am_michael]
"""
import argparse
import json
import os
import re
import numpy as np
from scipy.io import wavfile

MIN_SHOT = 0.90          # a shot is never shorter than this
SILENT_MIN = 0.80        # shortest designed silent beat
WORD_GAP = 0.90          # a word occupies 90% of its slot; 10% gap closes the mouth


def trim_silence(x, sr, rel=0.02, pad=0.03):
    """Remove Kokoro's leading/trailing pad so speech starts on the frame."""
    a = np.abs(x)
    if a.size == 0:
        return x
    peak = float(a.max())
    if peak <= 0:
        return x
    idx = np.where(a > peak * rel)[0]
    if idx.size == 0:
        return x
    s = max(0, int(idx[0] - pad * sr))
    e = min(len(x), int(idx[-1] + pad * sr))
    return x[s:e]


def word_weights(text):
    """Rough syllable weight per token so long words get more time."""
    out = []
    for w in text.split():
        core = re.sub(r"[^a-z0-9]", "", w.lower())
        ww = max(1, len(core)) + 3
        if w.endswith(","):
            ww += 2
        elif re.search(r"[.?!][\"')]*$", w):
            ww += 4
        out.append(ww)
    return out


def retime(story, durations, no_retime=False):
    """Plan contiguous shot intervals; no-retime really preserves declared starts.

    Speech longer than its declared slot is an error in no-retime mode, not silently
    clipped or overlapped into the next line. Retime mode retains the existing hold rules.
    """
    shots = story.get("shots", [])
    if len(durations) != len(shots):
        raise ValueError("one speech duration per shot required")
    cursor, plan = 0.0, []
    for shot, speech in zip(shots, durations):
        if not number(speech) or speech < 0:
            raise ValueError("speech durations must be finite and non-negative")
        declared = float(shot["end"]) - float(shot["start"])
        hold = float(shot.get("hold", .42 if speech else .9))
        if not number(hold) or hold < 0 or declared <= 0:
            raise ValueError("shot durations/holds must be positive (holds non-negative)")
        if no_retime:
            start, duration = float(shot["start"]), declared
            if start + .001 < cursor:
                raise ValueError("no-retime requires ordered, non-overlapping shots")
            if speech > duration + .001:
                raise ValueError(f"{shot.get('id')}: speech {speech:.3f}s exceeds slot {duration:.3f}s")
            cursor = start
        else:
            start = cursor
            duration = max(MIN_SHOT, speech + hold) if speech else max(SILENT_MIN, hold)
        plan.append((shot, speech, duration, start))
        cursor += duration
    return {"shots": [{"start": round(start, 3), "end": round(start + duration, 3)}
                      for _, _, duration, start in plan], "duration": round(cursor, 3), "plan": plan}


def number(value):
    import math
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--no-retime", action="store_true",
                    help="keep the declared shot timings instead of cutting to the line")
    ap.add_argument("--no-captions", action="store_true")
    a = ap.parse_args()
    P = a.project

    cfg = json.load(open(os.path.join(P, "config.json"), encoding="utf-8"))
    st = json.load(open(os.path.join(P, "story", "shots.json"), encoding="utf-8"))
    voice = a.voice or cfg.get("voice") or "am_michael"
    speed = a.speed or cfg.get("speed") or 1.05
    # Per-speaker casting. A story may declare {"voices": {"NILA": "af_heart", ...}};
    # without it every line uses the single default voice (legacy behaviour).
    voice_map = st.get("voices") or {}

    def voice_for(shot):
        return voice_map.get(shot.get("speaker") or "", voice)

    kdir = os.path.expanduser("~/.faceless-shorts/kokoro")
    model = os.path.join(kdir, "kokoro-v1.0.onnx")
    voices = os.path.join(kdir, "voices-v1.0.bin")
    if not (os.path.exists(model) and os.path.exists(voices)):
        raise SystemExit("ERROR: Kokoro model files missing in %s (run voice.py --download)." % kdir)

    from kokoro_onnx import Kokoro
    K = Kokoro(model, voices)

    def lang_for(v):
        return "en-gb" if v.startswith("b") else "en-us"

    # ── pass 1 · synthesize and trim every line ──────────────────────────────
    clips = {}
    SR = None
    for s in st["shots"]:
        text = (s.get("line") or "").strip()
        if not text:
            continue
        v = voice_for(s)
        samples, sr = K.create(text, voice=v, speed=speed, lang=lang_for(v))
        x = np.asarray(samples, dtype=np.float32)
        x = trim_silence(x, sr)
        if SR is None:
            SR = sr
        clips[s["id"]] = (text, x)

    if SR is None:
        raise SystemExit("ERROR: no shot has a non-empty 'line' to narrate.")

    # ── pass 2 · retime: a shot lasts as long as its line, plus a hold ──────
    old_total = float(st.get("duration") or st["shots"][-1]["end"])
    durations = [len(clips[s["id"]][1]) / SR if s["id"] in clips else 0.0 for s in st["shots"]]
    timing = retime(st, durations, a.no_retime)
    plan, total = timing["plan"], timing["duration"]

    # ── pass 3 · lay the audio down at the new starts ────────────────────────
    buf = np.zeros(int(round(total * SR)), dtype=np.float32)
    # Per-speaker stems: the mouth envelope must be measured from ONE voice, or a
    # listener's mouth moves while somebody else talks. Written only when the film
    # actually casts more than one voice.
    speakers = sorted({(s.get("speaker") or "NARRATOR") for s in st["shots"]
                       if s["id"] in clips})
    stems = {sp: np.zeros_like(buf) for sp in speakers} if len(speakers) > 1 else {}
    words = []
    for s, speech, dur, start in plan:
        s["start"] = round(start, 3)
        s["end"] = round(start + dur, 3)
        if s["id"] not in clips:
            continue
        text, x = clips[s["id"]]
        at = int(round(start * SR))
        end = min(len(buf), at + len(x))
        buf[at:end] += x[:end - at]
        sp = s.get("speaker") or "NARRATOR"
        if sp in stems:
            stems[sp][at:end] += x[:end - at]

        # word times from the TRIMMED window, with a gap so the mouth closes
        toks = text.split()
        wts = word_weights(text)
        tw = sum(wts) or 1
        c = start
        for w, wt in zip(toks, wts):
            d = speech * wt / tw
            rec = {"word": w, "start": round(c, 3), "end": round(c + d * WORD_GAP, 3)}
            if s.get("speaker"):
                rec["speaker"] = s["speaker"]
            words.append(rec)
            c += d

    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.9
    out_wav = os.path.join(P, "build", "voice.wav")
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    wavfile.write(out_wav, SR, (buf * 32767).astype(np.int16))
    for sp, stem in stems.items():
        sd = os.path.join(P, "build", "voice")
        os.makedirs(sd, exist_ok=True)
        wavfile.write(os.path.join(sd, sp + ".wav"), SR,
                      (np.clip(stem / peak, -1, 1) * 32767).astype(np.int16))

    tl = os.path.join(P, "timeline")
    os.makedirs(tl, exist_ok=True)
    json.dump(words, open(os.path.join(tl, "words.json"), "w", encoding="utf-8"), indent=1)

    # ── rescale the music plan so its arc still spans the film ──────────────
    if st.get("music") and old_total > 0:
        k = total / old_total
        for m in st["music"]:
            m["start"] = round(float(m["start"]) * k, 3)
            m["end"] = round(float(m["end"]) * k, 3)
        st["music"][-1]["end"] = round(total, 3)

    st["duration"] = round(total, 3)
    json.dump(st, open(os.path.join(P, "story", "shots.json"), "w", encoding="utf-8"), indent=1)

    cfg["duration"] = round(total, 3)
    cfg["voiceover"] = os.path.relpath(out_wav, P).replace("\\", "/")
    cfg["captions"] = not a.no_captions
    if not a.no_captions:
        cfg["captionStyle"] = ({"y": 1800, "size": 56} if cfg.get("aspect") == "9:16"
                               else {"y": 1000, "size": 50})
    json.dump(cfg, open(os.path.join(P, "config.json"), "w", encoding="utf-8"), indent=2)

    # ── report ──────────────────────────────────────────────────────────────
    print("narrate: %s x%.2f -> %s (%.2fs total, sr=%d)" % (voice, speed, out_wav, total, SR))
    dead = 0.0
    for s, speech, dur, start in plan:
        if speech:
            air = dur - speech
            dead += air
            print("  %s @%5.2f  shot %4.2fs  speech %4.2fs  tail %.2fs  %s"
                  % (s["id"], start, dur, speech, air, s.get("size", s.get("template", "shot"))))
        else:
            print("  %s @%5.2f  shot %4.2fs  SILENT beat          %s"
                  % (s["id"], start, dur, s.get("size", s.get("template", "shot"))))
    print("  words: %d -> timeline/words.json" % len(words))

    # ── verify word-anchored beats resolve INSIDE their own shot ────────────
    # A shot may declare atWord / gesture.word. If that word is missing, the
    # template falls back and the beat simply never fires — a silent failure that
    # no render check can see. Timings only exist here, so this is the one place
    # that can catch it. A miss is reported, never guessed at.
    def norm(t):
        return re.sub(r"[^\w']", "", t.lower())

    anchors, misses = 0, []
    for s_ in st["shots"]:
        pr = s_.get("params") or {}
        want = []
        aw = pr.get("atWord") or s_.get("atWord")
        if aw:
            want.append(("atWord", aw))
        for gk in ("gesture", "gesture2"):
            g = pr.get(gk) or s_.get(gk)
            if isinstance(g, dict) and g.get("word"):
                want.append((gk + ".word", g["word"]))
        for label, word in want:
            anchors += 1
            m = norm(str(word))
            hit = next((w for w in words
                        if w["start"] >= s_["start"] - 0.05
                        and norm(w["word"]).startswith(m)), None)
            if hit is None or hit["start"] > s_["end"]:
                misses.append((s_["id"], label, word))
    if anchors:
        if misses:
            for sid, label, word in misses:
                print("  WARN %s %s %r did not resolve inside the shot -> beat will NOT fire"
                      % (sid, label, word))
            print("  word anchors: %d declared, %d MISSED" % (anchors, len(misses)))
        else:
            print("  word anchors: %d declared, all resolved inside their shot" % anchors)
    print("  speech: %.2fs / %.2fs = %.0f%% of runtime" %
          (sum(p[1] for p in plan), total, 100.0 * sum(p[1] for p in plan) / total))


if __name__ == "__main__":
    main()
