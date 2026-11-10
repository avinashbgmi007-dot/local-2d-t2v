// tools/audit_host.mjs — shared headless player host for the frame audits.
// Boots the real player against a project so gates inspect what actually renders,
// not a reimplementation of it. Loopback only; never a public preview surface.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { chromium } from 'playwright';
import { staticPath } from '../render-utils.mjs';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.wav': 'audio/wav' };

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

export function readProject(project) {
  const dir = path.resolve(project);
  return {
    dir,
    cfg: JSON.parse(fs.readFileSync(path.join(dir, 'config.json'), 'utf8')),
    story: JSON.parse(fs.readFileSync(path.join(dir, 'story/shots.json'), 'utf8')),
  };
}

export function logicalStage(cfg) {
  const vertical = (cfg.aspect || '16:9') === '9:16';
  return { W: vertical ? 1080 : 1920, H: vertical ? 1920 : 1080 };
}

/** Start the asset server + Chromium, open the player, run fn(page), clean up. */
export async function withPlayer(project, fn, { scale = 0.2 } = {}) {
  const dir = path.resolve(project);
  const server = http.createServer((req, res) => {
    try {
      if (req.url.split('?')[0] === '/__manifest') {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        return res.end(JSON.stringify(listScenes(path.join(dir, 'scenes'), '/project/scenes')));
      }
      const p = staticPath(ROOT, dir, req.url);
      if (!p || !fs.existsSync(p) || !fs.statSync(p).isFile()) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      fs.createReadStream(p).pipe(res);
    } catch { res.writeHead(400); res.end(); }
  });
  await new Promise((res, rej) => { server.once('error', rej); server.listen(0, '127.0.0.1', res); });
  const PORT = server.address().port;
  const LAUNCH = { args: ['--no-sandbox', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader',
    '--disable-dev-shm-usage', '--use-angle=swiftshader'] };
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) LAUNCH.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const browser = await chromium.launch(LAUNCH);
  try {
    const page = await browser.newPage({ viewport: { width: 400, height: 720 } });
    await page.goto(`http://127.0.0.1:${PORT}/player.html?scale=${scale}`);
    await page.waitForFunction('window.READY === true || !!window.BOOT_ERROR', null, { timeout: 120000 });
    const boot = await page.evaluate('window.BOOT_ERROR');
    if (boot) throw new Error('player boot failed: ' + boot);
    return await fn(page);
  } finally {
    await browser.close();
    server.close();
  }
}
