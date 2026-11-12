"""Caption grouping — where a caption line is allowed to start and end.

Why this exists
  `engine/ui2d.js` used to group the karaoke words by FIXED INDEX:

      const st = Math.floor(i / max) * max;

  `i` is the index of the word being spoken, so the group is simply "the four
  words around it". Nothing told it where a sentence ended, so a group could
  hold the tail of one line and the head of the next. In the delivered joke
  film a frame read "COMEBACK. TOO MUCH EFFORT." while the punch line had not
  been spoken yet — the closing caption leaked into the setup shot and spoiled
  the joke. That is the defect this module removes.

What it does
  Assigns each word a group id `g`, breaking on the three things that actually
  end a caption line:
    1. sentence-final punctuation (. ! ? and their quote variants),
    2. a real pause between words (>= GAP_BREAK seconds) — how narrate.py
       already separates shots, since it writes gap-split timings,
    3. the maximum words per group.
  The renderer then only has to read `w.g`; it no longer guesses.

Deterministic and stdlib-only on purpose: the same words always group the same
way, because a QC failure has to be reproducible.
"""
import re

MAX_WORDS = 4
GAP_BREAK = 0.30

# . ! ? optionally followed by closing quotes/brackets, at the end of the token
_SENTENCE_END = re.compile(r"[.?!][\"'\u201d\u2019)\]]*$")


def ends_sentence(word):
    """True if this token closes a sentence. 'One sentence.' -> True."""
    return bool(_SENTENCE_END.search(str(word or "").strip()))


def assign_groups(words, max_words=MAX_WORDS, gap_break=GAP_BREAK):
    """Return the word list with a `g` (group) key added to each entry.

    A group breaks BEFORE a word when the previous word ended a sentence, when
    the silence between them is at least `gap_break`, or when the current group
    is already full.
    """
    out = []
    g = 0
    count = 0
    prev = None
    for w in words or []:
        item = dict(w)
        brk = False
        if prev is not None:
            if count >= int(max_words):
                brk = True
            elif ends_sentence(prev.get("word")):
                brk = True
            else:
                try:
                    brk = (float(item.get("start", 0.0))
                           - float(prev.get("end", 0.0))) >= float(gap_break)
                except (TypeError, ValueError):
                    brk = False
        if brk:
            g += 1
            count = 0
        item["g"] = g
        count += 1
        out.append(item)
        prev = item
    return out


def group_of(words, index, max_words=MAX_WORDS):
    """Return the words that share a caption line with `words[index]`.

    Falls back to the old fixed-width grouping when the words carry no `g`
    (every film narrated before this change), so those projects still render
    instead of raising.
    """
    if not words or index < 0 or index >= len(words):
        return []
    if "g" in words[index]:
        gid = words[index]["g"]
        return [w for w in words if w.get("g") == gid]
    st = (index // int(max_words)) * int(max_words)
    return list(words[st:st + int(max_words)])
