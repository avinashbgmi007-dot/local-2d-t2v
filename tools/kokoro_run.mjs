// kokoro_run.mjs — run local Kokoro-82M q8 ONNX (onnxruntime-web WASM) on a jobs file.
//   node tools/kokoro_run.mjs --tts build/tts --jobs jobs.json
// jobs.json: [{id, voice, ids:[...], speed, out:"/abs/path.wav"}]
// Model inputs: input_ids int64[1,N], style float32[1,256], speed float32[1] -> waveform @24kHz
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '..');
const args = process.argv.slice(2);
function arg(name, dflt) { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : dflt; }
const TTS = path.resolve(repo, arg('tts', 'build/tts'));
// resolve onnxruntime-web from the TTS asset dir, not from this script's location
const ort = await import(pathToFileURL(path.join(TTS, 'node_modules/onnxruntime-web/dist/ort.node.min.mjs')).href);

ort.env.wasm.wasmPaths = path.join(TTS, 'node_modules/onnxruntime-web/dist') + path.sep;
ort.env.wasm.numThreads = 1;

const session = await ort.InferenceSession.create(fs.readFileSync(path.join(TTS, 'model_quantized.onnx')),
  { executionProviders: ['wasm'] });

const SR = 24000;
function voiceStyle(voice, nTokens) {
  const buf = fs.readFileSync(path.join(TTS, 'voices', voice + '.bin'));
  const all = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const l = 256 * Math.min(Math.max(nTokens - 2, 0), 509);
  return all.slice(l, l + 256);
}
function writeWav(file, pcm, sr) {
  const n = pcm.length, data = Buffer.alloc(n * 2);
  for (let i = 0; i < n; i++) data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, pcm[i])) * 32767), i * 2);
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8);
  h.write('fmt ', 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(sr, 24); h.writeUInt32LE(sr * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write('data', 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(file, Buffer.concat([h, data]));
}

const jobs = JSON.parse(fs.readFileSync(arg('jobs', '/dev/stdin'), 'utf8'));
for (const j of jobs) {
  const inputIds = new ort.Tensor('int64', BigInt64Array.from(j.ids.map(BigInt)), [1, j.ids.length]);
  const style = new ort.Tensor('float32', voiceStyle(j.voice, j.ids.length), [1, 256]);
  const speed = new ort.Tensor('float32', new Float32Array([j.speed ?? 1]), [1]);
  const out = await session.run({ input_ids: inputIds, style, speed });
  writeWav(j.out, out.waveform.data, SR);
  console.log(`${j.id}: ${(out.waveform.data.length / SR).toFixed(3)}s  voice=${j.voice} speed=${j.speed ?? 1} -> ${j.out}`);
}
