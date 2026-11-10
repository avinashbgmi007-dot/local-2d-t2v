// Pure render scheduling/path helpers. No browser or filesystem side effects.
import path from 'node:path';

export function parseArgs(argv) {
  const flags = new Set(['project', 'from', 'to', 'frame-from', 'frame-to', 'workers', 'scale', 'style', 'styles', 'format', 'crf', 'preset', 'gl', 'out', 'stills', 'at', 'sheet', 'debug']);
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) throw new Error(`unexpected argument ${argv[i]}`);
    const key = argv[i].slice(2);
    if (!flags.has(key)) throw new Error(`unknown option --${key}`);
    if (Object.hasOwn(args, key)) throw new Error(`duplicate option --${key}`);
    args[key] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  }
  return args;
}

export function numeric(args, key, fallback, min, max, integer = false) {
  if (args[key] == null) return fallback;
  const value = Number(args[key]);
  if (!Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value)))
    throw new Error(`--${key} must be ${integer ? 'an integer ' : ''}in [${min}, ${max}]`);
  return value;
}

// A shot owns frames whose timestamps lie in [start,end). Ceil at both ends
// partitions fractional boundaries without duplicated or dropped frames.
export function frameRange(start, end, fps) {
  const eps = 1e-9;
  return [Math.max(0, Math.ceil(start * fps - eps)), Math.max(0, Math.ceil(end * fps - eps))];
}

export function splitFrames(first, last, workers) {
  if (!Number.isInteger(first) || !Number.isInteger(last) || last <= first) throw new Error('empty frame range');
  if (!Number.isInteger(workers) || workers < 1) throw new Error('invalid worker count');
  const count = Math.min(workers, last - first), size = Math.ceil((last - first) / count);
  return Array.from({ length: count }, (_, i) => [first + i * size, Math.min(last, first + (i + 1) * size)]).filter(([a, b]) => a < b);
}

export function contained(root, candidate) {
  const rel = path.relative(path.resolve(root), path.resolve(candidate));
  return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel));
}

export function staticPath(root, project, requestUrl) {
  const url = decodeURIComponent(requestUrl.split('?')[0]);
  if (url.includes('\0')) return null;
  const base = url.startsWith('/project/') ? project : root;
  const suffix = url.startsWith('/project/') ? url.slice('/project/'.length) : url.replace(/^\/+/, '');
  const candidate = path.resolve(base, suffix);
  if (!contained(base, candidate)) return null;
  const rel = path.relative(path.resolve(base), candidate);
  return rel.split(path.sep).some(p => p.startsWith('.') && p !== '.') ? null : candidate;
}

export function concatLine(file) {
  return `file '${path.resolve(file).replace(/\\/g, '/').replace(/'/g, "'\\''")}'`;
}
