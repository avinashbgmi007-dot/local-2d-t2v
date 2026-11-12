"""tools/script_frame_check.py - compare the SCRIPT to the FRAMES that were drawn.

Every other gate reads one side only. The story contract reads the JSON; the
frame review reads pixels. Neither can answer the question the owner actually
asks: "the line says dragon -- is there a dragon in this frame?"

This tool answers it by colour. Every figure and every subject is drawn from a
known hex (cast colours, subject colour), so a declared body that never reached
the frame is a measurable absence, not an opinion:

  * a shot that DECLARES a subject must contain the subject's colour;
  * a line that NAMES the subject noun must be in a shot that shows it --
    otherwise the character talks about something the viewer cannot see;
  * a named character must be in the frame they speak in;
  * an insert is a prop, so no character's colour may dominate it.

Exit 0 when the frames agree with the script, 1 otherwise. Warnings never fail.

  python tools/script_frame_check.py --project projects/<name> [--strict]
"""
import argparse
import glob
import json
import os
import sys

# A body is shaded, rim-lit and veiled by the shot, so exact hex matching is
# useless. 48 is measured: the same creature reads within 30 of its base hex
# under the night veil and within 44 under the golden insert.
TOL = 48
# 0.2% of a 9:16 frame is ~1000 px: smaller than any real figure (a wide-shot
# person is ~5%) and larger than a stray antialiased edge.
MIN_FRAC = 0.002


def hex_rgb(h):
    h = str(h).lstrip("#")
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def find_video(project):
    for pat in ("out/*.mp4", "build/video_silent.mp4"):
        hits = sorted(glob.glob(os.path.join(project, pat)))
        if hits:
            return hits[-1]
    return None


def extract_at(video, ts, png):
    """One frame at `ts` from the DELIVERED video. ffmpeg only, no Chromium."""
    import subprocess
    os.makedirs(os.path.dirname(png), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-ss", "%.3f" % ts, "-i", video,
                        "-frames:v", "1", png],
                       capture_output=True)
    return png if r.returncode == 0 and os.path.exists(png) else None


def load_still(project, shot, video=None):
    """The frame for a shot: a --sheet still if one exists, else from the video.

    Checking the DELIVERED video is the stronger test: a still re-render can
    differ from what was encoded (retiming, fades, the master pass).
    """
    sid = shot.get("id")
    for pat in ("build/sheets/%s_*.png" % sid, "build/stills/%s_*.png" % sid,
                "build/sheets/*%s*.png" % sid):
        hits = sorted(glob.glob(os.path.join(project, pat)))
        if hits:
            return hits[0]
    if video is None:
        return None
    mid = (float(shot.get("start", 0)) + float(shot.get("end", 0))) / 2.0
    return extract_at(video, mid, os.path.join(project, "build", "sfcheck",
                                               "%s.png" % sid))


def colour_fraction(path, rgb, tol=TOL):
    """Fraction of pixels within `tol` of `rgb` (Euclidean, per channel)."""
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.int16)
    d = np.abs(a - np.array(rgb, dtype=np.int16)).max(axis=2)
    return float((d <= tol).mean())


def check(project, strict=False):
    sp = os.path.join(project, "story", "shots.json")
    if not os.path.exists(sp):
        return ["no story/shots.json in %s" % project], []
    story = json.load(open(sp, encoding="utf-8"))
    shots = story.get("shots") or []
    cast = story.get("cast") or {}
    cast_rgb = {k: hex_rgb(v.get("color")) for k, v in cast.items()}

    errs, warns = [], []
    if not shots:
        return ["story has no shots"], []
    video = find_video(project)

    for s in shots:
        sid = s.get("id")
        line = (s.get("line") or "")
        p = s.get("params") or {}
        still = load_still(project, s, video)
        if still is None:
            errs.append("%s: no still and no video frame -- the script cannot be "
                        "checked against a picture that was never drawn" % sid)
            continue
        try:
            # A body colour present in the frame is the cheapest proof that the
            # body the script asked for was actually drawn.
            def has(rgb):
                return rgb is not None and colour_fraction(still, rgb) >= MIN_FRAC

            subj = p.get("subject") or {}
            if subj.get("kind"):
                rgb = hex_rgb(subj.get("color") or "#4a4458")
                if not has(rgb):
                    errs.append("%s: declares a %s but the frame has no %s pixels "
                                "-> the subject is in the script, not in the picture"
                                % (sid, subj["kind"], subj["kind"]))

            who = p.get("who")
            if who and who in cast_rgb and not has(cast_rgb[who]):
                errs.append("%s: %s speaks this shot but their colour is absent"
                            % (sid, who))
            if p.get("insertKind") and p.get("insertKind") != "creature":
                present = [k for k, v in cast_rgb.items() if has(v)]
                if present:
                    warns.append("%s: an insert of a prop also contains %s -- a "
                                 "person is standing in the object shot"
                                 % (sid, ", ".join(present)))
        except Exception as e:                                  # noqa: BLE001
            errs.append("%s: could not read %s (%s)" % (sid, os.path.basename(still), e))

    # The script half, before any pixels: a line that names a creature and a
    # story that never declares one. This is what the original dragon film
    # would have failed on -- it is readable from the JSON alone, so it does not
    # need a render to catch it.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fresh.subject import creature_kind
    except ImportError:
        creature_kind = None
    if creature_kind:
        declared = None
        for s in shots:
            k = ((s.get("params") or {}).get("subject") or {}).get("kind")
            if k:
                declared = k
                break
        spoken = set()
        for s in shots:
            k = creature_kind(s.get("line") or "")
            if k:
                spoken.add(k)
        if spoken and declared is None:
            errs.append("the script names %s but no shot declares a subject -> "
                        "the film talks about it and never draws it"
                        % ", ".join(sorted(spoken)))

    # The semantic half: a line that NAMES the subject must show it. A pronoun
    # ("it", "that") is a reaction and is allowed to stay on a face.
    subj_noun = None
    for s in shots:
        sub = ((s.get("params") or {}).get("subject") or {})
        if sub.get("kind"):
            subj_noun = sub["kind"]
            break
    if subj_noun:
        for s in shots:
            line = (s.get("line") or "").lower()
            if subj_noun not in line:
                continue
            p = s.get("params") or {}
            if (p.get("subject") or {}).get("kind") == subj_noun:
                continue
            if s.get("size") == "close":
                warns.append("%s: says %r in a close-up -> the noun is spoken "
                             "but only a face is on screen" % (s.get("id"), subj_noun))
            else:
                errs.append("%s: says %r but the shot shows no %s -> the character "
                            "names something the viewer cannot see"
                            % (s.get("id"), subj_noun, subj_noun))
    return errs, warns


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="warnings also fail (default: only errors do)")
    a = ap.parse_args(argv)
    errs, warns = check(a.project, a.strict)
    for w in warns:
        print("  SCRIPT/FRAME warn :", w)
    for e in errs:
        print("  SCRIPT/FRAME ERROR:", e)
    bad = len(errs) + (len(warns) if a.strict else 0)
    print("SCRIPT/FRAME: %d error(s), %d warning(s) -> %s"
          % (len(errs), len(warns), "FAIL" if bad else "aligned"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
