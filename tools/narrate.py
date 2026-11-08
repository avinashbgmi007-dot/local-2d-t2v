#!/usr/bin/env python3
"""
narrate.py — synthesize each shot's `line` to a voice track aligned to shot starts,
and emit word timings for the engine's karaoke captions.

Kokoro-82M via kokoro_onnx (ONNX, CPU). No account, no API, no Whisper needed:
word times are distributed inside each line's measured speech window by length
(deterministic; within ~0.1-0.2 s of the speech). Good enough for highlight captions.

Run with the faceless-shorts venv python (has kokoro_onnx + numpy + scipy):
  <venv>/Scripts/python.exe tools/narrate.py --project projects/foo [--voice am_michael] [--speed 1.05]

Writes build/voice.wav (length = story duration), timeline/words.json ([{word,start,end}]),
and sets config.voiceover + config.captions + config.captionStyle.
"""
import argparse
import json
import os
import re
import numpy as np
from scipy.io import wavfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float)
    a = ap.parse_args()
    P = a.project
    cfg = json.load(open(os.path.join(P, "config.json"), encoding="utf-8"))
    st = json.load(open(os.path.join(P, "story", "shots.json"), encoding="utf-8"))
    total = float(st.get("duration") or st["shots"][-1]["end"])
    voice = a.voice or cfg.get("voice") or "am_michael"
    speed = a.speed or cfg.get("speed") or 1.05

    kdir = os.path.expanduser("~/.faceless-shorts/kokoro")
    model = os.path.join(kdir, "kokoro-v1.0.onnx")
    voices = os.path.join(kdir, "voices-v1.0.bin")
    if not (os.path.exists(model) and os.path.exists(voices)):
        raise SystemExit("ERROR: Kokoro model files missing in %s (run voice.py --download)." % kdir)

    from kokoro_onnx import Kokoro
    K = Kokoro(model, voices)
    lang = "en-gb" if voice.startswith("b") else "en-us"

    SR = None
    buf = None
    report = []
    words = []
    for s in st["shots"]:
        text = (s.get("line") or "").strip()
        if not text:
            continue
        samples, sr = K.create(text, voice=voice, speed=speed, lang=lang)
        samples = np.asarray(samples, dtype=np.float32)
        if SR is None:
            SR = sr
            buf = np.zeros(int(total * sr), dtype=np.float32)
        at = int(float(s["start"]) * SR)
        dur = len(samples) / SR
        end = min(len(buf), at + len(samples))
        buf[at:end] += samples[:end - at]
        report.append((s["id"], float(s["start"]), dur, float(s["end"]) - float(s["start"])))

        # distribute this line's words inside its measured speech window [at/SR, at/SR+dur]
        toks = text.split()
        wts = [max(1, len(re.sub(r"[^a-z0-9]", "", w.lower()))) + 3
               + (2 if w.endswith(",") else 4 if re.search(r"[.?!][\"')]*$", w) else 0)
               for w in toks]
        tw = sum(wts) or 1
        c = at / SR
        for w, wt in zip(toks, wts):
            d = dur * wt / tw
            words.append({"word": w, "start": round(c, 3), "end": round(c + d * 0.9, 3)})
            c += d

    if SR is None:
        raise SystemExit("ERROR: no shot has a non-empty 'line' to narrate.")

    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.9
    out = os.path.join(P, "build", "voice.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wavfile.write(out, SR, (buf * 32767).astype(np.int16))

    tl = os.path.join(P, "timeline")
    os.makedirs(tl, exist_ok=True)
    json.dump(words, open(os.path.join(tl, "words.json"), "w", encoding="utf-8"), indent=1)

    cfg["voiceover"] = os.path.relpath(out, P).replace("\\", "/")
    cfg["captions"] = True
    cfg["captionStyle"] = ({"y": 1800, "size": 56} if cfg.get("aspect") == "9:16"
                           else {"y": 1000, "size": 50})
    json.dump(cfg, open(os.path.join(P, "config.json"), "w", encoding="utf-8"), indent=2)

    print(f"voice: {voice} x{speed} -> {out} ({total:.2f}s, sr={SR})")
    for sid, start, dur, shot in report:
        flag = "OVERRUN" if dur > shot + 0.05 else "ok"
        print(f"  {sid} @{start:5.2f}s  speech {dur:.2f}s / shot {shot:.2f}s  {flag}")
    print(f"words: {len(words)} -> timeline/words.json ; captions on ; voiceover={cfg['voiceover']}")


if __name__ == "__main__":
    main()
