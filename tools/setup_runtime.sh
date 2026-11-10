#!/usr/bin/env bash
# tools/setup_runtime.sh — restore the render/test runtime after a workspace reset.
#
# node_modules, pip packages and /tmp do not survive between agent turns. This
# script is idempotent: run it at the start of any turn that needs to render.
#
#   bash tools/setup_runtime.sh
#
# Afterwards:
#   export PATH=/home/user/.local/bin:$PATH \
#          LD_LIBRARY_PATH=/tmp/al2023/lib:/tmp \
#          PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/tmp/chromium
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "== npm =="
if [ ! -d node_modules/playwright ]; then
  npm ci --no-audit --no-fund
fi
if [ ! -d node_modules/@sparticuz/chromium ]; then
  # --no-save: these are sandbox-only render deps, not project requirements.
  npm install --no-save --no-audit --no-fund \
    @sparticuz/chromium @ffmpeg-installer/ffmpeg @ffprobe-installer/ffprobe
fi

echo "== python =="
python3 -c "import numpy, scipy, soundfile, PIL, espeakng_loader" 2>/dev/null || \
  python3 -m pip install --user --break-system-packages -q \
    numpy scipy pillow soundfile espeakng-loader

echo "== chromium =="
node -e "require('@sparticuz/chromium').default.executablePath().then(p=>console.log('  binary', p))"
# v153 dropped inflate(); unpack the Amazon Linux 2023 shared libs by hand.
if [ ! -d /tmp/al2023/lib ]; then
  node -e "
    const z=require('zlib'), fs=require('fs');
    fs.writeFileSync('/tmp/al2023.tar',
      z.brotliDecompressSync(fs.readFileSync('$ROOT/node_modules/@sparticuz/chromium/bin/al2023.tar.br')));
  "
  mkdir -p /tmp/al2023
  tar -xf /tmp/al2023.tar -C /tmp/al2023
  rm -f /tmp/al2023.tar
fi

echo "== ffmpeg =="
mkdir -p "$HOME/.local/bin"
ln -sf "$(node -e "console.log(require('@ffmpeg-installer/ffmpeg').path)")" "$HOME/.local/bin/ffmpeg"
ln -sf "$(node -e "console.log(require('@ffprobe-installer/ffprobe').path)")" "$HOME/.local/bin/ffprobe"

echo "== smoke =="
export PATH="$HOME/.local/bin:$PATH" LD_LIBRARY_PATH=/tmp/al2023/lib:/tmp
ffmpeg -version 2>&1 | head -1
python3 -c "import numpy, scipy, soundfile, PIL, espeakng_loader; print('  python deps OK')"
node -e "
const {chromium}=require('playwright');
(async()=>{
  const b=await chromium.launch({executablePath:'/tmp/chromium',
    args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage();
  await p.setContent('<canvas id=c width=8 height=8></canvas>');
  const v=await p.evaluate(()=>{const g=document.getElementById('c').getContext('2d');
    g.fillStyle='#f00'; g.fillRect(0,0,8,8); return [...g.getImageData(0,0,1,1).data].join(',')});
  await b.close();
  if (v !== '255,0,0,255') throw new Error('canvas readback wrong: '+v);
  console.log('  chromium canvas OK');
})().catch(e=>{console.error('  SMOKE FAIL', e.message); process.exit(1)});
"
echo "runtime ready"
