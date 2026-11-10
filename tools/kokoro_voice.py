#!/usr/bin/env python3
"""
kokoro_voice.py — LOCAL NEURAL VOICE: Kokoro-82M q8, fully offline.

Replaces test_voice.py (eSpeak fixture) as the narration source. All assets come
from allowlisted hosts only (see tools/setup_tts.sh):
  model  <- npm kokoro-q8-shards (sha256-pinned reassembly)
  voices <- npm kokoro-local-runtime voices/*.bin
  vocab  <- pypi kokoro-onnx wheel config.json
  IPA    <- pypi piper-phonemize + espeakng_loader (ctypes, no binary)
  run    <- tools/kokoro_run.mjs on onnxruntime-web WASM

Output contract is IDENTICAL to test_voice.py, so nothing downstream changes:
  voice.wav            all lines placed at their shot starts (24 kHz, peak 0.85)
  stems/<SPEAKER>.wav  per-speaker mix (mouth envelope is measured from one voice)
  words.json           {"schema":"kokoro-words-v1", ..., "words":[{word,start,end,speaker}]} GLOBAL s
  lines.json           per-line speech duration + voice + speed used
  duration_report.txt  human-readable timing table

Word timing: eSpeak WORD events give MEASURED word boundaries per line; each line's
boundaries are stretched uniformly to that line's Kokoro duration, and Kokoro's
`speed` is auto-fit so speech never overflows its shot.

  python tools/kokoro_voice.py --story examples/quality-benchmark/story.json \
      --out build/quality/voice --voices NILA=af_heart,ARUN=am_adam
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import test_voice as tv  # ESpeak binding, word_spans, trim, parse_voices

SR = 24000  # Kokoro native sample rate


def kokoro_clean(ipa: str) -> str:
    """Port of kokoro-js's post-phonemization cleanup (espeak IPA -> Kokoro phonemes)."""
    s = ipa
    s = s.replace("kəkˈoːɹoʊ", "kˈoʊkəɹoʊ").replace("kəkˈɔːɹəʊ", "kˈəʊkəɹəʊ")
    s = s.replace("ʲ", "j").replace("r", "ɹ").replace("x", "k").replace("ɬ", "l")
    s = re.sub(r"(?<=[a-zɹː])(?=hˈʌndɹɪd)", " ", s)
    s = re.sub(r" z(?=[;:,.!?¡¿—…\"'«»“” ]|$)", "z", s)
    s = re.sub(r"(?<=nˈaɪn)ti(?!ː)", "di", s)  # en-us "ninety"
    return s.strip()


def phonemes(text: str, vocab: dict):
    from piper_phonemize import phonemize_espeak
    out = phonemize_espeak(text, voice="en-us")
    ipa = "".join("".join(sent) for sent in out)
    ph = kokoro_clean(ipa)
    ids = [vocab[c] for c in ph if c in vocab]
    dropped = sorted({c for c in ph if c not in vocab})
    return ph, [0] + ids + [0], dropped


def run_kokoro(tts: Path, jobs: list) -> None:
    jf = tts / "jobs.json"
    jf.write_text(json.dumps(jobs), encoding="utf-8")
    r = subprocess.run(["node", str(TOOLS / "kokoro_run.mjs"), "--tts", str(tts), "--jobs", str(jf)],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("kokoro_run.mjs failed:\n" + r.stdout + r.stderr)
    for line in r.stdout.splitlines():
        if ":" in line and "s  voice=" in line:
            print("  " + line.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voices", required=True, help="SPEAKER=kokoro-voice, comma separated (e.g. NILA=af_heart,ARUN=am_adam)")
    ap.add_argument("--tts", default=str(REPO / "build" / "tts"))
    ap.add_argument("--fit-margin", type=float, default=0.12, help="seconds of shot left free after speech")
    a = ap.parse_args()

    tts = Path(a.tts)
    for need in ("model_quantized.onnx", "vocab.json", "voices"):
        if not (tts / need).exists():
            raise SystemExit(f"missing {tts / need} — run: bash tools/setup_tts.sh")
    vocab = json.loads((tts / "vocab.json").read_text(encoding="utf-8"))
    voices = tv.parse_voices(a.voices)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    story = json.loads(Path(a.story).read_text(encoding="utf-8-sig"))
    shots = story["shots"]

    # ---- pass 1: eSpeak measured word spans + phonemes/ids per line ----
    es = tv.ESpeak()
    sr_es = es.sr
    cursor = 0.0
    lines = []
    for s in shots:
        start = float(s.get("start", cursor))
        dur = float(s.get("dur", float(s.get("end", start + 3)) - start))
        cursor = start + dur
        text = (s.get("line") or "").strip()
        speaker = s.get("speaker")
        if not text:
            lines.append({"id": s["id"], "start": start, "dur": dur, "speaker": None,
                          "text": "", "spans": [], "speech_es": 0.0, "ph": "", "ids": [],
                          "voice": None, "speed": 1.0, "dropped": []})
            continue
        voice = voices.get(speaker)
        if not voice:
            raise SystemExit(f"{s['id']}: speaker {speaker!r} has no --voices entry")
        x, events = es.say(text, voice="en-us", rate=150, pitch=50)
        x2, lead = tv.trim(x, sr_es)
        speech_es = len(x2) / sr_es
        spans = tv.word_spans(text, events, lead, speech_es)  # relative, in [0, speech_es]
        ph, ids, dropped = phonemes(text, vocab)
        if dropped:
            print(f"  {s['id']}: WARNING dropped phonemes {dropped}")
        lines.append({"id": s["id"], "start": start, "dur": dur, "speaker": speaker,
                      "text": text, "spans": spans, "speech_es": speech_es, "ph": ph,
                      "ids": ids, "voice": voice, "speed": 1.0, "dropped": dropped})

    # ---- pass 2: Kokoro synth at speed 1.0, then auto-fit speed to the shot ----
    tmp = out / "_lines"
    tmp.mkdir(exist_ok=True)
    speak = [ln for ln in lines if ln["speaker"]]
    jobs = [{"id": ln["id"], "voice": ln["voice"], "ids": ln["ids"], "speed": 1.0,
             "out": str(tmp / (ln["id"] + ".wav"))} for ln in speak]
    run_kokoro(tts, jobs)
    redo = []
    for ln in speak:
        _, x = wavfile.read(tmp / (ln["id"] + ".wav"))
        d1 = len(x) / SR
        max_d = ln["dur"] - a.fit_margin
        if d1 <= max_d:
            ln["speed"], ln["speech"] = 1.0, d1
            continue
        s = d1 / max_d
        if s > 1.9:
            raise SystemExit(f"{ln['id']}: even at speed 1.9 speech {d1 / 1.9:.2f}s exceeds shot "
                             f"{max_d:.2f}s — lengthen dur")
        ln["speed"] = round(s, 3)
        redo.append(ln)
    if redo:
        jobs = [{"id": ln["id"], "voice": ln["voice"], "ids": ln["ids"], "speed": ln["speed"],
                 "out": str(tmp / (ln["id"] + ".wav"))} for ln in redo]
        run_kokoro(tts, jobs)
        for ln in redo:
            _, x = wavfile.read(tmp / (ln["id"] + ".wav"))
            ln["speech"] = len(x) / SR
    for ln in speak:
        ln.setdefault("speech", 0.0)

    # ---- assemble voice.wav + stems at 24 kHz; stretch word spans to Kokoro duration ----
    total = cursor
    buf = np.zeros(int(round(total * SR)), np.float32)
    cast = sorted({ln["speaker"] for ln in speak})
    stems = {sp: np.zeros_like(buf) for sp in cast} if len(cast) > 1 else {}
    words = []
    for ln in speak:
        _, x = wavfile.read(tmp / (ln["id"] + ".wav"))
        x = x.astype(np.float32) / 32768.0
        at = int(round(ln["start"] * SR))
        n = min(len(x), len(buf) - at)
        buf[at:at + n] += x[:n]
        if ln["speaker"] in stems:
            stems[ln["speaker"]][at:at + n] += x[:n]
        scale = ln["speech"] / ln["speech_es"] if ln["speech_es"] > 0 else 1.0
        for w in ln["spans"]:
            words.append({"word": w["word"],
                          "start": round(ln["start"] + w["start"] * scale, 3),
                          "end": round(ln["start"] + w["end"] * scale, 3),
                          "speaker": ln["speaker"]})
    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.85
    wavfile.write(str(out / "voice.wav"), SR, (buf * 32767).astype(np.int16))
    if stems:
        (out / "stems").mkdir(exist_ok=True)
        for sp, stem in stems.items():
            wavfile.write(str(out / "stems" / (sp + ".wav")), SR,
                          (np.clip(stem / peak * 0.85, -1, 1) * 32767).astype(np.int16))

    payload = {"schema": "kokoro-words-v1",
               "engine": "kokoro-82m-q8 (local, offline; was espeak-ng test fixture)",
               "sample_rate": SR, "duration": round(total, 3), "words": words}
    (out / "words.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    lines_out = [{"id": ln["id"], "start": round(ln["start"], 3), "shot": round(ln["dur"], 3),
                  "speech": round(ln.get("speech", 0.0), 3), "speaker": ln["speaker"],
                  "voice": ln["voice"], "speed": ln["speed"]} for ln in lines]
    (out / "lines.json").write_text(json.dumps(
        {"sample_rate": SR, "duration": round(total, 3), "lines": lines_out}, indent=1) + "\n",
        encoding="utf-8")

    rep = ["KOKORO-82M q8 (local neural voice) — %d Hz, total %.2fs, %d words"
           % (SR, total, len(words)), ""]
    for ln in lines_out:
        if ln["speech"]:
            rep.append("  %-4s @%5.2f  shot %4.2fs  speech %4.2fs  speed %.2f  %-5s %s"
                       % (ln["id"], ln["start"], ln["shot"], ln["speech"], ln["speed"],
                          ln["speaker"] or "-", ln["voice"]))
        else:
            rep.append("  %-4s @%5.2f  shot %4.2fs  SILENT" % (ln["id"], ln["start"], ln["shot"]))
    (out / "duration_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))
    print("\nwrote", out / "voice.wav", "+ stems/ + words.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
