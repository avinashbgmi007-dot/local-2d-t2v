#!/usr/bin/env python3
"""Repeatable, read-only inventory and structural scan of every repository file.

  python tools/repo_scan.py
  python tools/repo_scan.py --json build/audit/repo-scan.json --markdown docs scan-report.md

Scans tracked files plus untracked non-ignored files. Skips Git internals, dependencies
and generated build/out/cache directories. Checks UTF-8, Python AST, JSON (including
 duplicate keys), JS syntax via Node, local imports, PNG chunk CRC/decompression,
Ogg page CRC, font tables, project contracts and the mirrored plugin kit.
Does not execute project code, download models, or claim visual/audio acceptance.
"""
import argparse
import ast
import collections
import hashlib
import json
import re
import struct
import subprocess
import zlib
from pathlib import Path

try:
    from .validate_project import validate_project
except ImportError:
    from validate_project import validate_project

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "node_modules", "build", "out", "__pycache__", ".venv", ".cache", "dist", "coverage"}
TEXT = {".py", ".js", ".mjs", ".json", ".md", ".html", ".txt", ".sh", ".css"}
KIT = Path("vendor/plugin/skills/make-2d-video/kit")


def inventory(root):
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    paths = {Path(p) for p in tracked.stdout.decode().split("\0") if p}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not any(p in SKIP for p in rel.parts):
            paths.add(rel)
    return sorted(paths, key=str)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def png_check(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("invalid PNG signature")
    pos, compressed, seen_end = 8, bytearray(), False
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        size = struct.unpack_from(">I", data, pos)[0]
        end = pos + 12 + size
        if end > len(data):
            raise ValueError("PNG chunk exceeds file length")
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + size]
        want = struct.unpack_from(">I", data, pos + 8 + size)[0]
        # CRC covers the chunk TYPE as well as its payload.
        if zlib.crc32(kind + payload) & 0xffffffff != want:
            raise ValueError(f"PNG CRC mismatch in {kind!r}")
        if kind == b"IHDR":
            width, height = struct.unpack(">II", payload[:8])
            if not width or not height:
                raise ValueError("empty PNG dimensions")
        if kind == b"IDAT":
            compressed += payload
        if kind == b"IEND":
            seen_end = True
        pos = end
    if not seen_end or pos != len(data):
        raise ValueError("missing IEND or trailing PNG bytes")
    zlib.decompress(compressed)
    return {"width": width, "height": height}


def ogg_check(data):
    pos, pages = 0, 0
    while pos < len(data):
        if data[pos:pos + 4] != b"OggS" or pos + 27 > len(data):
            raise ValueError("invalid/truncated Ogg page")
        count = data[pos + 26]
        head = 27 + count
        if pos + head > len(data):
            raise ValueError("truncated Ogg segment table")
        size = head + sum(data[pos + 27:pos + head])
        page = bytearray(data[pos:pos + size])
        if len(page) != size:
            raise ValueError("truncated Ogg payload")
        want = struct.unpack_from("<I", page, 22)[0]
        page[22:26] = b"\0" * 4
        value = 0  # Ogg uses polynomial 0x04c11db7, init/xor 0, non-reflected.
        for byte in page:
            value ^= byte << 24
            for _ in range(8):
                value = ((value << 1) ^ (0x04c11db7 if value & 0x80000000 else 0)) & 0xffffffff
        if value != want:
            raise ValueError(f"Ogg CRC mismatch on page {pages}")
        pos += size
        pages += 1
    if not pages:
        raise ValueError("empty Ogg file")
    return {"pages": pages}


def font_check(data):
    if data[:4] not in {b"OTTO", b"\x00\x01\x00\x00", b"true"}:
        raise ValueError("unknown font signature")
    count = struct.unpack_from(">H", data, 4)[0]
    for i in range(count):
        offset = 12 + i * 16
        if offset + 16 > len(data):
            raise ValueError("truncated font table directory")
        start, size = struct.unpack_from(">II", data, offset + 8)
        if start + size > len(data):
            raise ValueError("font table exceeds file length")
    return {"tables": count}


def local_imports(path, text, root):
    missing = []
    for match in re.finditer(r"(?:\bfrom\s*|\bimport\s*\()\s*['\"]([^'\"]+)['\"]", text):
        spec = match.group(1)
        if spec.startswith("/"):
            target = root / spec.lstrip("/")
        elif spec.startswith("."):
            target = path.parent / spec
        else:
            continue
        if not target.resolve().is_file():
            missing.append(spec)
    return missing


def scan(root=ROOT):
    root = Path(root).resolve()
    paths = inventory(root)
    rows, errors, warnings = [], [], []
    hashes = collections.defaultdict(list)
    counts = collections.Counter()
    js = []
    for rel in paths:
        path = root / rel
        data = path.read_bytes()
        ext = rel.suffix.lower() or "[none]"
        digest = hashlib.sha256(data).hexdigest()
        row = {"path": rel.as_posix(), "bytes": len(data), "sha256": digest, "extension": ext}
        hashes[digest].append(rel.as_posix())
        counts[ext] += 1
        try:
            if ext in TEXT or not ext:
                text = data.decode("utf-8")
                row["lines"] = len(text.splitlines())
                if ext == ".py":
                    ast.parse(text, filename=str(rel))
                    counts["python_ast"] += 1
                elif ext == ".json":
                    json.loads(text, object_pairs_hook=unique_object)
                    counts["json_parsed"] += 1
                elif ext in {".js", ".mjs"}:
                    js.append((rel, text))
                elif ext == ".sh":
                    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                    if result.returncode:
                        raise ValueError(result.stderr.strip())
                    counts["shell_syntax"] += 1
            elif ext == ".png":
                row.update(png_check(data))
                counts["png_verified"] += 1
            elif ext == ".ogg":
                row.update(ogg_check(data))
                counts["ogg_verified"] += 1
            elif ext in {".ttf", ".otf"}:
                row.update(font_check(data))
                counts["font_verified"] += 1
        except (ValueError, SyntaxError, struct.error, zlib.error, OSError) as exc:
            errors.append({"path": rel.as_posix(), "message": str(exc)})
        rows.append(row)
    # One Node process farms out syntax-only checks; no imports are executed.
    if js:
        script = """import {spawnSync} from 'node:child_process'; import {readFileSync} from 'node:fs';
const files=JSON.parse(readFileSync(0,'utf8')); const bad=[];
for(const f of files){const r=spawnSync(process.execPath,['--check',f],{encoding:'utf8'});if(r.status)bad.push({path:f,message:r.stderr});}
process.stdout.write(JSON.stringify(bad));"""
        try:
            result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=root,
                                    input=json.dumps([r.as_posix() for r, _ in js]),
                                    capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise ValueError(result.stderr)
            errors += json.loads(result.stdout)
            counts["javascript_syntax"] = len(js)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            errors.append({"path": "javascript", "message": str(exc)})
    for rel, text in js:
        for spec in local_imports(root / rel, text, root):
            errors.append({"path": rel.as_posix(), "message": f"unresolved local import {spec}"})
    projects = 0
    for directory in [root / "projects", root / "examples"]:
        if not directory.exists():
            continue
        for project in sorted(directory.iterdir()):
            if not (project / "config.json").is_file():
                continue
            projects += 1
            pe, pw = validate_project(project)
            errors += [{"path": str(project.relative_to(root)), "message": m} for m in pe]
            warnings += [{"path": str(project.relative_to(root)), "message": m} for m in pw]
    mirrored = 0
    if (root / KIT).exists():
        for path in sorted((root / KIT).rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root / KIT)
            mirrored += 1
            if not (root / rel).is_file() or path.read_bytes() != (root / rel).read_bytes():
                errors.append({"path": (KIT / rel).as_posix(), "message": "plugin kit differs from live studio"})
    return {
        "schema": "local-2d-t2v-repo-scan-v1", "root": str(root),
        "summary": {"files": len(rows), "bytes": sum(r["bytes"] for r in rows),
                    "unique_contents": len(hashes), "projects": projects,
                    "mirrored_files": mirrored, "checks": dict(counts),
                    "errors": len(errors), "warnings": len(warnings)},
        "errors": errors, "warnings": warnings, "files": rows,
        "limits": ["Syntax/structure only; project JS is not executed.",
                   "Missing ignored media are warnings, not corrupt-file errors.",
                   "No perceptual quality, speech alignment, rights or publication approval is inferred."],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", dest="json_path")
    ap.add_argument("--markdown", dest="markdown_path")
    ap.add_argument("--strict", action="store_true", help="make missing-media warnings fatal")
    args = ap.parse_args()
    report = scan()
    summary = report["summary"]
    print(f"Scanned {summary['files']} files ({summary['bytes']:,} bytes), {summary['projects']} projects.")
    print(json.dumps(summary["checks"], indent=2))
    for error in report["errors"]:
        print("ERROR", error["path"], error["message"])
    print(f"{summary['errors']} error(s), {summary['warnings']} warning(s).")
    if args.json_path:
        path = Path(args.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_path:
        lines = ["# Repository scan", "", "```json", json.dumps(summary, indent=2), "```", "", "## Errors"]
        lines += [f"- `{e['path']}`: {e['message']}" for e in report["errors"]] or ["None."]
        lines += ["", "## Warnings"]
        lines += [f"- `{w['path']}`: {w['message']}" for w in report["warnings"]] or ["None."]
        lines += ["", "## Limits"] + ["- " + s for s in report["limits"]]
        path = Path(args.markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return int(bool(report["errors"]) or (args.strict and bool(report["warnings"])))


if __name__ == "__main__":
    raise SystemExit(main())
