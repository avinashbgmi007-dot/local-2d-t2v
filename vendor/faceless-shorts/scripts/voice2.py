"""Two-voice dialogue narration: reuses voice.py's model loading, trimming and sample rate,
but speaks each line in its own Kokoro voice. Writes narration.wav + lines.json in the same
schema, so the rest of the pipeline (words.py / aiTrends transcribe) is unchanged."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).parent))
from voice import ensure_models, trim, KDIR, SR

PROJ = Path(sys.argv[1])
S = json.loads((PROJ / 'dialogue.json').read_text())

ensure_models()
from kokoro_onnx import Kokoro
k = Kokoro(str(KDIR / 'kokoro-v1.0.onnx'), str(KDIR / 'voices-v1.0.bin'))

def say(text, voice, speed):
    lang = 'en-gb' if voice.startswith('b') else 'en-us'
    return trim(np.asarray(k.create(text, voice=voice, speed=speed, lang=lang)[0], dtype=np.float64))

out = [np.zeros(int(S.get('lead', 0.4) * SR))]
t = len(out[0]) / SR
lines = []
for i, ln in enumerate(S['lines']):
    voice = ln['voice'] or S['voice']
    x = say(ln['text'], voice, S.get('speed', 1.0))
    lines.append({'i': i, 'text': ln['text'], 'voice': voice,
                  'start': round(t, 3), 'end': round(t + len(x) / SR, 3)})
    print(f'{i:2d} {lines[i]["start"]:6.2f}-{lines[i]["end"]:6.2f}  [{voice:9s}] {ln["text"]}', flush=True)
    gap = float(ln.get('gap', S.get('gap', 0.28)))
    out += [x, np.zeros(int(gap * SR))]
    t += (len(x) + gap) / SR

out.append(np.zeros(int(S.get('outro', 0.9) * SR)))
y = np.concatenate(out)
y = y / (np.abs(y).max() + 1e-9) * 0.9
(PROJ / 'data').mkdir(exist_ok=True)
wavfile.write(PROJ / 'data/narration.wav', SR, (y * 32767).astype(np.int16))
dur = len(y) / SR
(PROJ / 'data/lines.json').write_text(json.dumps(
    {'duration': round(dur, 3), 'voice': 'dialogue', 'speed': S.get('speed', 1.0), 'lines': lines}, indent=1))
(PROJ / 'data/script.txt').write_text('\n'.join(ln['text'] for ln in S['lines']) + '\n')
print(f'data/narration.wav ({dur:.2f} s, {len(lines)} lines, two voices)')
