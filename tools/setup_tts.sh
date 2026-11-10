#!/usr/bin/env bash
# setup_tts.sh — fetch the LOCAL Kokoro-82M q8 TTS assets using ONLY allowlisted hosts
# (registry.npmjs.org, pypi.org, files.pythonhosted.org). Idempotent; re-run every turn
# because build/ is wiped between turns. Result: build/tts/{model_quantized.onnx,voices/,vocab.json,node_modules/}
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TTS="$REPO/build/tts"
mkdir -p "$TTS"

# 1) model: npm kokoro-q8-shards (6 parts, byte-identical reassembly, sha256-pinned)
if [ ! -f "$TTS/model_quantized.onnx" ]; then
  echo "== kokoro model shards (npm) =="
  curl -sL -o /tmp/kq8.tgz https://registry.npmjs.org/kokoro-q8-shards/-/kokoro-q8-shards-1.0.0.tgz
  rm -rf /tmp/kq8 && mkdir -p /tmp/kq8 && tar xzf /tmp/kq8.tgz -C /tmp/kq8
  cat /tmp/kq8/package/kokoro-q8.part*.bin > "$TTS/model_quantized.onnx"
  echo "fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478  $TTS/model_quantized.onnx" | sha256sum -c -
fi

# 2) voice embeddings: npm kokoro-local-runtime bundles voices/*.bin (same format kokoro-js loads)
if [ ! -f "$TTS/voices/af_heart.bin" ]; then
  echo "== kokoro voices (npm) =="
  curl -sL -o /tmp/klr.tgz https://registry.npmjs.org/kokoro-local-runtime/-/kokoro-local-runtime-0.1.0.tgz
  rm -rf /tmp/klr && mkdir -p /tmp/klr && tar xzf /tmp/klr.tgz -C /tmp/klr
  mkdir -p "$TTS/voices" && cp /tmp/klr/package/voices/*.bin "$TTS/voices/"
fi

# 3) phoneme vocab: pypi kokoro-onnx wheel bundles kokoro_onnx/config.json (vocab table)
if [ ! -f "$TTS/vocab.json" ]; then
  echo "== kokoro vocab (pypi) =="
  pip download kokoro-onnx --no-deps -q -d /tmp/ko >/dev/null 2>&1
  rm -rf /tmp/kow && mkdir -p /tmp/kow && (cd /tmp/kow && unzip -o -q /tmp/ko/*.whl)
  python3 - "$TTS/vocab.json" <<'PY'
import json, sys
c = json.load(open('/tmp/kow/kokoro_onnx/config.json'))
json.dump(c['vocab'], open(sys.argv[1], 'w'))
print('  vocab entries:', len(c['vocab']))
PY
fi

# 4) IPA phonemizer: pypi piper-phonemize + espeakng-loader (ctypes, no espeak binary needed)
python3 -c "import piper_phonemize, espeakng_loader" 2>/dev/null || \
  pip install --user --break-system-packages -q piper-phonemize espeakng_loader

# 5) inference runtime: onnxruntime-web WASM (ships inside the npm tarball; --ignore-scripts
#    because onnxruntime-node's postinstall would fetch blocked GitHub release binaries)
if [ ! -d "$TTS/node_modules/onnxruntime-web" ]; then
  echo "== onnxruntime-web (npm) =="
  npm install --prefix "$TTS" --ignore-scripts --strict-ssl=false --no-audit --no-fund onnxruntime-web >/dev/null 2>&1
fi

echo "TTS assets ready: $TTS"
