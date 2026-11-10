#!/usr/bin/env python3
"""
test_voice.py — TEST-FIXTURE speech for verifying the audio/lip-sync path offline.

NOT PRODUCTION NARRATION. The voice is eSpeak NG (formant synthesis): intelligible,
robotic, and deliberately NOT the sound this studio should ship. It exists because
the production voice (Kokoro) needs model weights that are not always reachable,
and the dialogue/lip-sync/timing path still has to be testable and measurable.

Why it is still a useful test signal: eSpeak reports the exact audio position of
every word as it synthesizes, so word timings here are MEASURED, not estimated from
word length. That makes it a valid clock for testing speaker routing, mouth
envelopes, caption timing and retiming — the things that must be right before a
better voice is dropped in.

  python tools/test_voice.py --story examples/quality-benchmark/story.json \
      --out build/quality/voice --voices NILA=en-us+f3,ARUN=en-us+m2

Writes into --out:
  voice.wav            all lines placed at their shot starts (native sample rate)
  words.json           {"words": [{word,start,end}], ...} in GLOBAL seconds
  lines.json           per-line measured speech duration + the voice used
  duration_report.txt  suggested shot durations (speech + hold) for the story

Feed the timings to the existing importer:
  python tools/parse_script.py --project P --script <out>/words.json

Requires: pip install espeakng-loader numpy scipy   (no model download, no network)
"""
import argparse
import ctypes
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

# t_espeak_OUTPUT
AUDIO_OUTPUT_RETRIEVAL = 1
# espeak_SetParameter identifiers
RATE, VOLUME, PITCH, RANGE = 1, 2, 3, 4
# espeak_Synth flags
CHARS_UTF8 = 1
ENDPAUSE = 0x1000
# event types
EV_LIST_TERMINATED, EV_WORD, EV_SENTENCE, EV_MARK, EV_PLAY, EV_END = 0, 1, 2, 3, 4, 5
EV_MSG_TERMINATED, EV_PHONEME, EV_SAMPLERATE = 6, 7, 8


class _EventId(ctypes.Union):
    # espeak-ng speak_lib.h: union { int number; const char *name; char string[8]; }
    # -> 8 bytes, NOT 40. With a 40-byte name the struct stride became 72 instead of
    # 40, so every second event was skipped and the others were read from garbage
    # (word text came out as "hat"/"hing." and timings collapsed to ~1 ms).
    _fields_ = [("number", ctypes.c_int), ("name", ctypes.c_void_p),
                ("string", ctypes.c_char * 8)]


class Event(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("unique_identifier", ctypes.c_uint),
        ("text_position", ctypes.c_int),
        ("length", ctypes.c_int),
        ("audio_position", ctypes.c_int),
        ("sample", ctypes.c_int),
        ("user_data", ctypes.c_void_p),
        ("id", _EventId),
    ]


CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int,
                            ctypes.POINTER(Event))


class ESpeak:
    """Minimal synchronous eSpeak NG binding: text -> (samples, sr, word events)."""

    def __init__(self):
        import espeakng_loader

        self._loader = espeakng_loader
        data = Path(espeakng_loader.get_data_path())
        self.lib = ctypes.CDLL(espeakng_loader.get_library_path())
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.lib.espeak_Initialize.restype = ctypes.c_int
        self.lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        self.lib.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.espeak_SetSynthCallback.argtypes = [CALLBACK]
        self.lib.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint,
                                          ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
                                          ctypes.POINTER(ctypes.c_uint), ctypes.c_void_p]
        self.lib.espeak_Synchronize.restype = ctypes.c_int
        # path is the directory CONTAINING espeak-ng-data
        sr = self.lib.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0,
                                        str(data.parent).encode("utf-8"), 0)
        if sr <= 0:
            raise RuntimeError("espeak_Initialize failed (%s)" % sr)
        self.sr = int(sr)
        self._chunks = []
        self._events = []
        self._cb = CALLBACK(self._on_audio)  # keep alive for the process lifetime
        self.lib.espeak_SetSynthCallback(self._cb)

    def _on_audio(self, wav, n, events):
        if wav and n:
            self._chunks.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
        i = 0
        if events:
            while True:
                ev = events[i]
                if ev.type == EV_LIST_TERMINATED:
                    break
                self._events.append((ev.type, ev.text_position, ev.length, ev.audio_position))
                i += 1
                if i > 100000:
                    break
        return 0

    def say(self, text, voice="en-us", rate=155, pitch=50, volume=100):
        self._chunks, self._events = [], []
        for ident, value in ((RATE, rate), (PITCH, pitch), (VOLUME, volume), (RANGE, 50)):
            self.lib.espeak_SetParameter(ident, int(value), 0)
        if self.lib.espeak_SetVoiceByName(voice.encode("utf-8")) != 0:
            raise RuntimeError("unknown espeak voice %r" % voice)
        buf = ctypes.create_string_buffer(text.encode("utf-8"))
        rc = self.lib.espeak_Synth(buf, ctypes.sizeof(buf), 0, 1, 0,
                                   CHARS_UTF8 | ENDPAUSE, None, None)
        if rc != 0:
            raise RuntimeError("espeak_Synth failed (%s)" % rc)
        self.lib.espeak_Synchronize()
        x = np.concatenate(self._chunks) if self._chunks else np.zeros(0, np.int16)
        return x.astype(np.float32) / 32768.0, [e for e in self._events if e[0] == EV_WORD]


def trim(x, sr, rel=0.02, pad=0.02):
    """Trim leading/trailing silence; returns (samples, seconds_removed)."""
    if not len(x):
        return x, 0.0
    peak = float(np.abs(x).max())
    if peak <= 0:
        return x, 0.0
    idx = np.where(np.abs(x) > peak * rel)[0]
    if not len(idx):
        return x, 0.0
    s = max(0, int(idx[0] - pad * sr))
    e = min(len(x), int(idx[-1] + pad * sr))
    return x[s:e], s / sr


def word_spans(text, events, lead, speech):
    """Measured word windows from eSpeak WORD events (audio_position is ms).

    eSpeak reports text_position 1-BASED and `length` without trailing punctuation,
    so the token is recovered from the source text (start = pos-1, then extend over
    any attached punctuation). Timings are the synthesizer's own, minus the silence
    trimmed off the front, so they line up with the trimmed samples exactly.
    """
    raw = text.encode("utf-8")
    toks = []
    for _, tpos, length, ams in events:
        start = max(0, tpos - 1)
        end = min(len(raw), start + max(length, 1))
        while end < len(raw) and not raw[end:end + 1].isspace():
            end += 1
        chunk = raw[start:end].decode("utf-8", "replace").strip()
        if not chunk:
            continue
        at = max(0.0, ams / 1000.0 - lead)
        if toks and at <= toks[-1][1]:
            continue                      # duplicate/rewound event: never go backwards
        toks.append((chunk, at))
    if not toks:
        return []
    spans = []
    for i, (word, start) in enumerate(toks):
        end = toks[i + 1][1] if i + 1 < len(toks) else speech
        end = min(end, speech)
        if end <= start:
            end = min(speech, start + 0.05)
        # close the mouth for the last 12% of every window (a visible consonant gap)
        spans.append({"word": word, "start": round(start, 3),
                      "end": round(start + (end - start) * 0.88, 3)})
    return spans


def parse_voices(spec):
    out = {}
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise SystemExit("--voices entries must be SPEAKER=voice")
        who, voice = part.split("=", 1)
        out[who.strip()] = voice.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voices", default="", help="SPEAKER=espeak-voice, comma separated")
    ap.add_argument("--default-voice", default="en-us")
    ap.add_argument("--rate", type=int, default=150)
    ap.add_argument("--pitch", type=int, default=50)
    ap.add_argument("--json", action="store_true", help="also print the report as JSON")
    a = ap.parse_args()

    story = json.loads(Path(a.story).read_text(encoding="utf-8-sig"))
    voices = parse_voices(a.voices)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    es = ESpeak()
    sr = es.sr
    shots = story["shots"]
    cursor, placed = 0.0, []
    lines, words = [], []
    pitch_of = {}
    for i, who in enumerate(sorted(voices)):
        pitch_of[who] = a.pitch + (12 if i % 2 else -6)

    for s in shots:
        start = float(s.get("start", cursor))
        dur = float(s.get("dur", float(s.get("end", start + 3)) - start))
        cursor = start + dur
        text = (s.get("line") or "").strip()
        if not text:
            lines.append({"id": s["id"], "start": round(start, 3), "speech": 0.0,
                          "shot": round(dur, 3), "speaker": None, "voice": None})
            continue
        speaker = s.get("speaker")
        voice = voices.get(speaker, a.default_voice)
        x, events = es.say(text, voice=voice, rate=a.rate,
                           pitch=pitch_of.get(speaker, a.pitch))
        x, lead = trim(x, sr)
        speech = len(x) / sr
        if speech > dur + 0.001:
            raise SystemExit("%s: speech %.3fs exceeds shot %.3fs — raise dur to %.2f"
                             % (s["id"], speech, dur, speech + 0.35))
        placed.append((start, x, speaker))
        for w in word_spans(text, events, lead, speech):
            words.append({"word": w["word"], "start": round(start + w["start"], 3),
                          "end": round(start + w["end"], 3), "speaker": speaker})
        lines.append({"id": s["id"], "start": round(start, 3), "speech": round(speech, 3),
                      "shot": round(dur, 3), "speaker": speaker, "voice": voice})

    total = cursor
    buf = np.zeros(int(round(total * sr)), np.float32)
    cast = sorted({sp for _, _, sp in placed if sp})
    stems = {sp: np.zeros_like(buf) for sp in cast} if len(cast) > 1 else {}
    for start, x, sp in placed:
        at = int(round(start * sr))
        n = min(len(x), len(buf) - at)
        buf[at:at + n] += x[:n]
        if sp in stems:
            stems[sp][at:at + n] += x[:n]
    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.85
    wavfile.write(str(out / "voice.wav"), sr, (buf * 32767).astype(np.int16))
    # Per-speaker stems so the mouth envelope is measured from one voice only.
    if stems:
        (out / "stems").mkdir(exist_ok=True)
        for sp, stem in stems.items():
            wavfile.write(str(out / "stems" / (sp + ".wav")), sr,
                          (np.clip(stem / peak * 0.85, -1, 1) * 32767).astype(np.int16))

    payload = {"schema": "test-voice-words-v1", "engine": "espeak-ng (TEST FIXTURE, not production narration)",
               "sample_rate": sr, "duration": round(total, 3), "words": words}
    (out / "words.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    (out / "lines.json").write_text(json.dumps(
        {"sample_rate": sr, "duration": round(total, 3), "lines": lines}, indent=1) + "\n",
        encoding="utf-8")

    report = ["TEST FIXTURE VOICE — eSpeak NG. Not production narration.",
              "sample rate %d Hz · total %.2fs · %d words" % (sr, total, len(words)), ""]
    for ln in lines:
        if ln["speech"]:
            report.append("  %-4s @%5.2f  shot %4.2fs  speech %4.2fs  tail %4.2fs  %-5s %s"
                          % (ln["id"], ln["start"], ln["shot"], ln["speech"],
                             ln["shot"] - ln["speech"], ln["speaker"] or "-", ln["voice"]))
        else:
            report.append("  %-4s @%5.2f  shot %4.2fs  SILENT" % (ln["id"], ln["start"], ln["shot"]))
    text = "\n".join(report)
    (out / "duration_report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print("\nwrote", out / "voice.wav", "and words.json")
    if a.json:
        print(json.dumps(payload["words"][:6], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
