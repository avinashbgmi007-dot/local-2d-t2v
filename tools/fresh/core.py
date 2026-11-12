"""fresh.core - deterministic RNG + color math. Stdlib only.

The RNG is a sha256 stream, so the same seed gives the same numbers on every
OS and Python version (random.Random helpers have changed between versions).
"""
import colorsys
import hashlib
import re

INK = "#15131a"  # chars/inkbean.js outline color (hard-coded in the rig)
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class Rng:
    def __init__(self, seed):
        self._seed = str(seed)
        self._n = 0
        self._buf = b""

    def _take(self, k):
        while len(self._buf) < k:
            self._buf += hashlib.sha256(f"{self._seed}|{self._n}".encode()).digest()
            self._n += 1
        out, self._buf = self._buf[:k], self._buf[k:]
        return out

    def u(self):
        """Float in [0, 1). 48 bits so the division is exact in a double."""
        return int.from_bytes(self._take(6), "big") / float(1 << 48)

    def range(self, lo, hi):
        return lo + (hi - lo) * self.u()

    def int(self, lo, hi):
        """Integer in [lo, hi] inclusive."""
        return lo + int(self.u() * (hi - lo + 1))

    def pick(self, seq):
        seq = list(seq)
        if not seq:
            raise ValueError("pick from empty sequence")
        return seq[int(self.u() * len(seq))]

    def sample(self, seq, k):
        pool, out = list(seq), []
        for _ in range(min(k, len(pool))):
            out.append(pool.pop(int(self.u() * len(pool))))
        return out


def seed_from_concept(concept, series_id=None, episode=None):
    norm = " ".join(str(concept).lower().split())
    raw = f"{series_id or '-'}|{episode if episode is not None else '-'}|{norm}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def is_hex(s):
    return isinstance(s, str) and bool(_HEX.match(s))


def hex_to_rgb(h):
    if not is_hex(h):
        raise ValueError(f"bad hex color: {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(r, g, b):
    c = lambda v: max(0, min(255, int(round(v))))
    return "#%02x%02x%02x" % (c(r), c(g), c(b))


def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    return rgb_to_hex(r * 255, g * 255, b * 255)


def rel_luminance(h):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_luminance(a), rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hex_to_lab(h):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in hex_to_rgb(h))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b):
    """CIE76 color difference. ~2 is barely visible, 30+ is clearly different."""
    la, lb = hex_to_lab(a), hex_to_lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5
