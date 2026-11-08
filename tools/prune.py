#!/usr/bin/env python3
"""
prune.py — reclaim disk from regenerable project artifacts, without guessing.

WHY THIS EXISTS
    projects/ grows without bound: every render leaves frames, wav intermediates and
    an mp4, and nothing removes them. It reached ~800 MB across ~20 projects, of
    which only a small part is worth keeping.

WHAT IT WILL AND WILL NOT TOUCH
    Everything here is inside projects/<slug>/build or projects/<slug>/out, i.e.
    regenerable output. Source (config.json, story/, scenes/, timeline/) is NEVER
    a candidate — those are the only things a re-render cannot recreate.

    debug          build/rv*, build/review*, build/stills, build/critique
                   frame dumps made for eyeballing; regenerable in seconds
    intermediates  build/*.wav, build/video_silent.mp4, build/*.json
                   mixer/render by-products; regenerable in one pipeline run
    products       out/*.mp4
                   the actual deliverables — deleted only when you name what to keep

SAFETY
    Dry run is the DEFAULT. `--apply` is required to delete anything, and `--only`
    must be named explicitly. Deletion is per-file (never a recursive wipe of a
    directory it did not enumerate itself), and every path is re-checked to be under
    projects/ before it is removed.

USAGE
    python tools/prune.py                                  # report only
    python tools/prune.py --apply --only debug             # reclaim frame dumps
    python tools/prune.py --apply --only intermediates
    python tools/prune.py --apply --only products --keep cine_all
    python tools/prune.py --apply --only all --keep cine_all
"""
import argparse
import os
import shutil
import sys

DEBUG_DIRS = ("rv", "rv2", "rv3", "rv4", "review", "review2", "review3", "stills", "critique")
INTERMEDIATE_EXT = (".wav", ".part")


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return "%.1f %s" % (n, u) if u != "B" else "%d B" % n
        n /= 1024.0


def size_of(paths):
    t = 0
    for p in paths:
        if os.path.isfile(p):
            t += os.path.getsize(p)
        else:
            for root, _, files in os.walk(p):
                for f in files:
                    try:
                        t += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
    return t


def collect(projects):
    """Return {category: [(path, is_dir)]} for every project."""
    out = {"debug": [], "intermediates": [], "products": []}
    for slug in sorted(os.listdir(projects)):
        P = os.path.join(projects, slug)
        if not os.path.isdir(P):
            continue
        b = os.path.join(P, "build")
        o = os.path.join(P, "out")

        if os.path.isdir(b):
            for d in sorted(os.listdir(b)):
                if d in DEBUG_DIRS:
                    out["debug"].append((os.path.join(b, d), True))
            for f in sorted(os.listdir(b)):
                fp = os.path.join(b, f)
                if os.path.isfile(fp) and (f.lower().endswith(INTERMEDIATE_EXT)
                                           or f == "video_silent.mp4"
                                           or f.endswith(".json")):
                    out["intermediates"].append((fp, False))
        if os.path.isdir(o):
            for f in sorted(os.listdir(o)):
                fp = os.path.join(o, f)
                if os.path.isfile(fp) and f.lower().endswith(".mp4"):
                    out["products"].append((fp, False))
    return out


def guard(projects, path):
    """Refuse anything that is not a build/out artifact inside projects/."""
    rp = os.path.realpath(path)
    root = os.path.realpath(projects)
    if not rp.startswith(root + os.sep):
        return False
    parts = rp[len(root) + 1:].replace("\\", "/").split("/")
    return len(parts) >= 3 and parts[1] in ("build", "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete (default: report only)")
    ap.add_argument("--only", choices=["debug", "intermediates", "products", "all"])
    ap.add_argument("--keep", default="", help="project slug whose out/ mp4s survive")
    a = ap.parse_args()

    studio = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects = os.path.join(studio, "projects")
    if not os.path.isdir(projects):
        sys.exit("prune: no projects/ directory at %s" % projects)

    cat = collect(projects)
    total = sum(size_of([p for p, _ in v]) for v in cat.values())

    print("projects: %s" % projects)
    print("total:    %s across %d projects\n" % (human(total), len(os.listdir(projects))))
    for k in ("debug", "intermediates", "products"):
        n = len(cat[k])
        print("  %-14s %4d items  %s" % (k, n, human(size_of([p for p, _ in cat[k]]))))

    if not a.apply:
        print("\nDRY RUN — nothing deleted.")
        print("  debug items are frame dumps this tooling wrote; safe to remove.")
        print("  intermediates are regenerable in one pipeline run.")
        print("  products are deliverables: name one with --keep before deleting them.")
        if cat["products"]:
            print("\n  deliverables currently present:")
            for p, _ in cat["products"]:
                print("    %s  %s" % (human(os.path.getsize(p)),
                                      os.path.relpath(p, projects).replace("\\", "/")))
        print("\nto reclaim, e.g.:  python tools/prune.py --apply --only debug")
        return 0

    if not a.only:
        sys.exit("prune: --apply needs --only debug|intermediates|products|all")

    targets = []
    if a.only in ("debug", "all"):
        targets += cat["debug"]
    if a.only in ("intermediates", "all"):
        targets += cat["intermediates"]
    if a.only in ("products", "all"):
        if not a.keep:
            sys.exit("prune: refusing to delete deliverables without --keep <slug>. "
                     "Name the project whose mp4s must survive.")
        keepdir = os.path.join(projects, a.keep, "out")
        targets += [(p, d) for p, d in cat["products"]
                    if os.path.realpath(os.path.dirname(p)) != os.path.realpath(keepdir)]

    if not targets:
        print("\nnothing to do.")
        return 0

    freed, failed = 0, []
    for path, is_dir in targets:
        if not guard(projects, path):
            failed.append((path, "outside projects/*/build|out"))
            continue
        try:
            n = size_of([path])
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
            freed += n
        except OSError as e:
            failed.append((path, str(e)))

    print("\nremoved %d items, freed %s" % (len(targets) - len(failed), human(freed)))
    for p, why in failed:
        print("  FAILED %s — %s" % (p, why), file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
