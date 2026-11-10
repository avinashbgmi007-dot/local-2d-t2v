#!/usr/bin/env node
// Deterministic Canvas/Three.js -> Chromium frames -> ffmpeg. Drawing lives in engine/.
// Safety changes are deliberate and recorded in docs/REPOSITORY_AUDIT.md; the visual engine is untouched.
//   node render.mjs --project P [--from S --to S] [--frame-from N --frame-to N]
//   node render.mjs --project P --sheet | --stills 1,2,3 | --styles dusk,midnight --at 1,2
// Options: --workers N --scale .1..1 --style ID --debug --format png|jpeg --crf 0..51
//          --preset PRESET --gl auto|gpu|swiftshader --out FILE
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { parseArgs, numeric, frameRange, splitFrames, staticPath, concatLine } from './render-utils.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
let server;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const fmtT = s => `${Math.floor(s / 60)}m${String(Math.round(s % 60)).padStart(2, '0')}s`;
function listScenes(dir, base) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) out.push(...listScenes(p, `${base}/${f}`));
    else if (f.endsWith('.js') && !f.startsWith('_')) out.push(`${base}/${f}`);
  }
  return out;
}
function runProcess(cmd, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: 'inherit' });
    child.once('error', reject);
    child.once('close', code => code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`)));
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (typeof args.project !== 'string') throw new Error('usage: node render.mjs --project projects/<name> [options]');
  const PROJECT = path.resolve(args.project), BUILD = path.join(PROJECT, 'build');
  const CFG = JSON.parse(fs.readFileSync(path.join(PROJECT, 'config.json'), 'utf8'));
  const STORY = JSON.parse(fs.readFileSync(path.join(PROJECT, 'story/shots.json'), 'utf8'));
  const FPS = numeric(CFG, 'fps', 24, 1, 240, true);
  const DURATION = Number(STORY.duration ?? STORY.shots?.at(-1)?.end);
  if (!Number.isFinite(DURATION) || DURATION <= 0 || !Array.isArray(STORY.shots) || !STORY.shots.length) throw new Error('invalid story duration/shots');
  const total = Math.ceil(DURATION * FPS - 1e-9);
  const scale = numeric(args, 'scale', 1, .1, 1);
  const requestedWorkers = numeric(args, 'workers', Math.max(1, Math.min(8, Math.floor(os.cpus().length / 2))), 1, 32, true);
  const crf = numeric(args, 'crf', 18, 0, 51, true);
  const gl = args.gl || (process.platform === 'linux' ? 'swiftshader' : 'auto');
  if (!['auto', 'gpu', 'swiftshader'].includes(gl)) throw new Error('--gl must be auto, gpu or swiftshader');
  if (args.format && !['png', 'jpeg'].includes(args.format)) throw new Error('--format must be png or jpeg');
  const FORMAT = args.format || 'png';
  const stillMode = !!(args.sheet || args.stills || args.styles);
  const LAUNCH = { args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage', ...(gl === 'swiftshader' ? ['--use-angle=swiftshader'] : []), ...(gl === 'gpu' ? ['--enable-gpu', '--use-angle=default'] : [])] };
  // Optional explicit browser path is useful for managed CI/containers; default remains Playwright's install.
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) LAUNCH.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  fs.mkdirSync(BUILD, { recursive: true });
  server = http.createServer((req, res) => {
    try {
      if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); return res.end(); }
      if (req.url.split('?')[0] === '/__manifest') {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        return res.end(JSON.stringify(listScenes(path.join(PROJECT, 'scenes'), '/project/scenes')));
      }
      const p = staticPath(ROOT, PROJECT, req.url);
      if (!p || !fs.existsSync(p) || !fs.statSync(p).isFile()) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      if (req.method === 'HEAD') return res.end();
      const stream = fs.createReadStream(p); stream.on('error', () => res.destroy()); stream.pipe(res);
    } catch { res.writeHead(400); res.end(); }
  });
  // Internal asset server: loopback only, never a public preview surface.
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const PORT = server.address().port;

  async function openPlayer(browser, style) {
    const qs = new URLSearchParams({ scale: String(scale) });
    if (style || args.style) qs.set('style', style || args.style);
    if (args.debug) qs.set('debug', '1');
    const page = await browser.newPage({ viewport: { width: 640, height: 360 } });
    const pageErrors = [];
    page.on('pageerror', e => { pageErrors.push(e.message); console.log('[pageerror]', e.message); });
    page.on('console', m => { const t = m.text(); if (/ERROR|missing/i.test(t)) { pageErrors.push(t); console.log('[page]', t); } });
    await page.goto(`http://127.0.0.1:${PORT}/player.html?${qs}`);
    await page.waitForFunction('window.READY === true || !!window.BOOT_ERROR', null, { timeout: 120000 });
    const boot = await page.evaluate('window.BOOT_ERROR');
    if (boot) throw new Error('Player failed to boot: ' + boot);
    const errors = [...pageErrors, ...(await page.evaluate('window.ERRORS'))];
    const missing = (await page.evaluate('window.SHOT_LIST')).filter(s => !s.ok);
    if (missing.length) errors.push(`missing scene(s): ${missing.map(s => s.id).join(', ')}`);
    if (errors.length) throw new Error('Player errors: ' + [...new Set(errors)].join('; '));
    const [w, h] = await page.evaluate('window.OUT');
    if (!(w >= 2 && h >= 2 && w % 2 === 0 && h % 2 === 0)) throw new Error(`invalid output dimensions ${w}x${h}`);
    await page.setViewportSize({ width: w, height: h });
    page.__errors = pageErrors;
    return page;
  }
  async function shot(page, f) {
    if (!Number.isInteger(f) || f < 0 || f >= total) throw new Error(`frame ${f} outside 0..${total - 1}`);
    await page.evaluate(i => window.renderFrame(i), f);
    const errors = [...page.__errors, ...(await page.evaluate('window.ERRORS'))];
    if (errors.length) throw new Error('shot error: ' + [...new Set(errors)].join('; '));
    return page.screenshot({ type: FORMAT, ...(FORMAT === 'jpeg' ? { quality: 94 } : {}) });
  }
  async function withBrowser(fn) { const browser = await chromium.launch(LAUNCH); try { return await fn(browser); } finally { await browser.close(); } }

  async function renderVideo() {
    let f0 = args['frame-from'] != null ? numeric(args, 'frame-from', 0, 0, total, true) : Math.round(numeric(args, 'from', 0, 0, DURATION) * FPS);
    let f1 = args['frame-to'] != null ? numeric(args, 'frame-to', total, 0, total, true) : args.to != null ? Math.round(numeric(args, 'to', DURATION, 0, DURATION) * FPS) : total;
    f0 = Math.min(total, f0); f1 = Math.min(total, f1);
    if (f1 <= f0) throw new Error('empty render range');
    if ((args['frame-from'] != null || args['frame-to'] != null) && (args.from != null || args.to != null)) throw new Error('use seconds OR exact frame bounds, not both');
    const chunks = splitFrames(f0, f1, requestedWorkers);
    const partsDir = fs.mkdtempSync(path.join(BUILD, 'parts-'));
    const out = path.resolve(args.out || path.join(BUILD, args.from != null || args.to != null || args['frame-from'] != null || args['frame-to'] != null ? 'preview.mp4' : 'video_silent.mp4'));
    const partial = path.join(partsDir, 'output.mp4');
    let done = 0; const t0 = Date.now();
    console.log(`Rendering frames ${f0}-${f1} (${((f1 - f0) / FPS).toFixed(1)} s) with ${chunks.length} worker(s)…`);
    try {
      const work = async (k, [a, b]) => withBrowser(async browser => {
        const page = await openPlayer(browser);
        const file = path.join(partsDir, `part_${String(k).padStart(3, '0')}.mp4`);
        const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', args.preset || 'medium', '-crf', String(crf), '-pix_fmt', 'yuv420p', '-r', String(FPS), file], { stdio: ['pipe', 'inherit', 'inherit'] });
        const finished = new Promise((resolve, reject) => { ff.once('error', reject); ff.once('close', code => code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}`))); });
        ff.stdin.on('error', () => {}); // finished carries the actionable process error
        try {
          for (let f = a; f < b; f++) {
            const img = await shot(page, f);
            if (!ff.stdin.write(img)) await Promise.race([once(ff.stdin, 'drain'), finished]);
            done++;
            if (done % 48 === 0) { const el = (Date.now() - t0) / 1000; process.stdout.write(`  ${done}/${f1 - f0} frames ${(done / el).toFixed(2)} fps elapsed ${fmtT(el)} eta ${fmtT(el / done * (f1 - f0 - done))}\n`); }
          }
          ff.stdin.end(); await finished;
        } catch (error) { ff.kill('SIGKILL'); ff.stdin.destroy(); await finished.catch(() => {}); throw error; }
        return file;
      });
      const parts = await Promise.all(chunks.map((range, k) => work(k, range)));
      const list = path.join(partsDir, 'list.txt'); fs.writeFileSync(list, parts.map(concatLine).join('\n') + '\n');
      await runProcess('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', partial]);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      // Publish only a complete, error-free encode. An existing deliverable survives failure.
      fs.renameSync(partial, out);
      console.log(`\nDone: ${out} (${fmtT((Date.now() - t0) / 1000)})`);
    } finally { fs.rmSync(partsDir, { recursive: true, force: true }); }
  }

  async function contactSheet(browser, items, outFile, cols = 4, cellW = 480) {
    const page = await browser.newPage({ viewport: { width: cols * (cellW + 12) + 12, height: 400 } });
    try {
      const escape = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
      const html = `<html><body style="margin:0;background:#111;font:600 15px sans-serif;color:#eee"><div style="display:grid;grid-template-columns:repeat(${cols},${cellW}px);gap:12px;padding:12px">${items.map(it => `<div><img src="data:image/${FORMAT};base64,${it.img.toString('base64')}" style="width:${cellW}px;display:block;border-radius:4px"><div style="padding:5px 2px">${escape(it.label)}</div></div>`).join('')}</div></body></html>`;
      await page.setContent(html); await page.screenshot({ path: outFile, fullPage: true });
    } finally { await page.close(); }
  }
  async function renderStills() {
    await withBrowser(async browser => {
      const styles = args.styles ? String(args.styles).split(',') : [args.style || null];
      const dir = path.join(BUILD, args.styles ? 'styles' : args.sheet ? 'sheets' : 'stills');
      fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
      const all = [];
      for (const st of styles) {
        const page = await openPlayer(browser, st);
        try {
          let targets;
          if (args.sheet) targets = (await page.evaluate('window.SHOT_LIST')).map(s => ({ t: s.start + (s.end - s.start) * .45, label: `${s.id} ${s.start.toFixed(1)}s` }));
          else targets = String(args.stills || args.at || '1').split(',').map(value => { const t = Number(value); if (!Number.isFinite(t) || t < 0 || t >= DURATION) throw new Error(`still time ${value} outside film`); return { t, label: `${t}s` }; });
          for (const tg of targets) {
            const img = await shot(page, Math.min(total - 1, Math.round(tg.t * FPS)));
            const name = `${st ? st + '_' : ''}${tg.label.split(' ')[0].replace(/[^\w.]/g, '')}_${tg.t.toFixed(2)}.${FORMAT}`;
            fs.writeFileSync(path.join(dir, name), img); all.push({ img, label: `${st ? `[${st}] ` : ''}${tg.label}` });
          }
        } finally { await page.close(); }
      }
      if (args.styles) await contactSheet(browser, all, path.join(dir, 'style_grid.png'), Math.ceil(all.length / styles.length), 420);
      else for (let i = 0; i < all.length; i += 24) await contactSheet(browser, all.slice(i, i + 24), path.join(dir, `sheet_${String(i / 24 + 1).padStart(2, '0')}.png`), 4, 440);
      console.log(`Wrote ${all.length} stills + contact sheet(s) to ${dir}`);
    });
  }
  if (stillMode) await renderStills(); else await renderVideo();
}
try { await main(); }
catch (error) { console.error('RENDER FAILED:', error.message); process.exitCode = 1; }
finally { if (server) await new Promise(resolve => server.close(resolve)); }
