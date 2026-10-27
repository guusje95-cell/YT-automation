"""Cinematic editing layer: telemetry HUD, chapter cards, glitch / signal-lost, black beats,
cinematic titles, the atmosphere profile diagram and the fact list.

Renderers follow the frames.py contract: `render(t) -> (H, W, 3) uint8` for t in [0, duration).
Overlays (`Hud`, `ChapterCard`, `TitleOverlay`) draw in place onto an existing frame.
"""
from __future__ import annotations

import math
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw

from ytauto.visuals import frames as fr
from ytauto.visuals.frames import ACCENT, H, MARGIN, TEXT, W, Layer, ease, ease_out, font

AMBER = ACCENT
RED = (255, 84, 64)
DIM = (170, 178, 196)


# ----------------------------------------------------------------- text helpers
def tracked(text: str, kind: str, size: int, color=TEXT, tracking: float = 0.25, shadow: bool = True) -> np.ndarray:
    """RGBA image of `text` with letter spacing (`tracking` x font size between glyphs)."""
    f = font(kind, size)
    asc, desc = f.getmetrics()
    gap = size * tracking
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + gap * max(len(text) - 1, 0)) + 4
    sp = 16 if shadow else 0
    img = Image.new("RGBA", (tw + 2 * sp, asc + desc + 2 * sp), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = sp
    for c, w_ in zip(text, widths):
        d.text((x, sp), c, font=f, fill=tuple(color) + (255,))
        x += w_ + gap
    arr = np.array(img)
    if shadow:
        a = arr[..., 3].astype(np.float32)
        sh = cv2.GaussianBlur(a, (0, 0), 7) * 0.75
        out = np.zeros_like(arr)
        out[..., 3] = np.clip(np.maximum(a, sh), 0, 255).astype(np.uint8)
        k = (a / 255.0)[..., None]
        out[..., :3] = (arr[..., :3] * k).astype(np.uint8)
        arr = out
    return arr


def place(rgba: np.ndarray, x: int, y: int, anchor: str = "lt") -> Layer:
    h, w = rgba.shape[:2]
    ax = {"l": 0, "m": w // 2, "r": w}[anchor[0]]
    ay = {"t": 0, "m": h // 2, "b": h}[anchor[1]]
    return Layer(rgba, x - ax, y - ay)


def _draw_text(frame, text, xy, kind, size, color, anchor="la", alpha=1.0):
    """Small dynamic text straight onto the frame (used for per-frame changing HUD values)."""
    if alpha <= 0.01:
        return
    f = font(kind, size)
    bb = f.getbbox(text, anchor=anchor)
    x0, y0 = int(xy[0] + bb[0]) - 6, int(xy[1] + bb[1]) - 6
    w, h = bb[2] - bb[0] + 12, bb[3] - bb[1] + 12
    x0c, y0c = max(x0, 0), max(y0, 0)
    x1c, y1c = min(x0 + w, W), min(y0 + h, H)
    if x1c <= x0c or y1c <= y0c:
        return
    patch = Image.new("L", (w, h), 0)
    ImageDraw.Draw(patch).text((xy[0] - x0, xy[1] - y0), text, font=f, fill=255, anchor=anchor)
    m = np.asarray(patch, np.float32)[y0c - y0:y1c - y0, x0c - x0:x1c - x0] / 255.0 * alpha
    sh = cv2.GaussianBlur(m, (0, 0), 2.0) * 0.7
    sub = frame[y0c:y1c, x0c:x1c].astype(np.float32)
    sub = sub * (1 - sh[..., None])
    sub = sub * (1 - m[..., None]) + np.array(color, np.float32) * m[..., None]
    frame[y0c:y1c, x0c:x1c] = np.clip(sub, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- HUD telemetry
_KEY_LABELS = {"hull": "HULL INTEGRITY", "date": "DATE", "clock": "TIME (UTC)", "speed": "VELOCITY", "temp": "TEMPERATURE", "depth": "DEPTH",
               "pressure": "PRESSURE", "g": "DECELERATION", "altitude": "ALTITUDE", "distance": "DISTANCE"}
_ORDER = ["hull", "date", "clock", "distance", "altitude", "speed", "g", "temp", "pressure", "depth"]


def _decimals(*vals) -> int:
    d = 0
    for v in vals:
        if isinstance(v, float) and not float(v).is_integer():
            d = max(d, len(repr(v).split(".")[1]))
    return min(d, 2)


def _fmt_num(v: float, dec: int) -> str:
    if dec == 0:
        return f"{int(round(v)):,}"
    return f"{v:,.{dec}f}"


def _parse_clock(s: str):
    m = re.match(r"^(T\+)?(\d+):(\d+)(?::(\d+))?$", s)
    if not m:
        return None
    pre, a, b, c = m.groups()
    secs = int(a) * 3600 + int(b) * 60 + int(c) if c is not None else (int(a) * 60 + int(b)) * (60 if not pre else 1)
    return pre or "", secs, c is not None


def _fmt_clock(pre: str, secs: float, with_s: bool) -> str:
    secs = int(secs)
    if pre:  # T+mm:ss
        return f"{pre}{secs // 60:02d}:{secs % 60:02d}"
    h, m, s = secs // 3600, secs // 60 % 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if with_s else f"{h:02d}:{m:02d}"


def hud_value(key: str, spec, u: float) -> str:
    """Interpolated display string for one HUD field at progress u in [0, 1]."""
    if isinstance(spec, str):
        return spec
    if key == "clock":
        a, b = spec[0], spec[1]
        pa, pb = _parse_clock(a), _parse_clock(b)
        if not pa or not pb:
            return a
        if pa[0]:  # T+mm:ss, both strings are minutes:seconds
            sa = int(a[2:].split(":")[0]) * 60 + int(a[2:].split(":")[1])
            sb = int(b[2:].split(":")[0]) * 60 + int(b[2:].split(":")[1])
            return _fmt_clock("T+", sa + (sb - sa) * u, True)
        return _fmt_clock("", pa[1] + (pb[1] - pa[1]) * u, pa[2])
    a, b = float(spec[0]), float(spec[1])
    unit = spec[2] if len(spec) > 2 else ""
    dec = _decimals(spec[0], spec[1])
    if a > 0 and b > 0 and max(a, b) / min(a, b) > 50:   # log interpolation for huge ranges
        v = math.exp(math.log(a) + (math.log(b) - math.log(a)) * u)
    else:
        v = a + (b - a) * u
    return f"{_fmt_num(v, dec)} {unit}".strip()


class Hud:
    """Telemetry panel: mission tag top-left, live values top-right, status line bottom-centre.

    `spec` is the beat's `hud` dict, e.g. {date: "07 DEC 1995", clock: ["22:04:30", "22:04:44"],
    speed: [170590, 170590, "km/h"], status: "ENTRY"}. Numbers ease from first to second value over the beat.
    """

    def __init__(self, spec: dict, duration: float, mission: str = "GALILEO PROBE  ·  TELEMETRY"):
        self.spec, self.duration = spec, duration
        mission = spec.get("mission", mission)
        self.mission = place(tracked(mission, "mono_medium", 20, DIM, 0.12), MARGIN - 12, MARGIN - 34)
        self.keys = [k for k in _ORDER if k in spec]
        self.labels = {k: place(tracked(_KEY_LABELS[k], "mono", 19, DIM, 0.14), W - MARGIN + 12, 0, "rt")
                       for k in self.keys}
        st = spec.get("status")
        self.status = place(tracked(st, "mono_bold", 24, AMBER, 0.3), W // 2, MARGIN - 28, "mt") if st else None

    def draw(self, frame: np.ndarray, t: float, alpha: float = 1.0) -> None:
        if alpha <= 0.01:
            return
        u = ease(t / max(self.duration, 1e-6))
        # mission tag with blinking dot
        self.mission.draw(frame, alpha * 0.9)
        if (t * 1.2) % 1.0 < 0.6:
            cv2.circle(frame, (MARGIN - 30, MARGIN - 34 + 28), 6, RED, -1, cv2.LINE_AA)
        y = MARGIN - 20
        for k in self.keys:
            lab = self.labels[k]
            lab.y = y
            lab.draw(frame, alpha * 0.85)
            _draw_text(frame, hud_value(k, self.spec[k], u), (W - MARGIN, y + 32), "mono_medium", 34, TEXT,
                       anchor="ra", alpha=alpha)
            y += 86
        # thin rule left of the values
        if self.keys:
            x = W - MARGIN - 300
            ov = frame[MARGIN - 18:y - 18, x:x + 2].astype(np.float32)
            frame[MARGIN - 18:y - 18, x:x + 2] = (ov * (1 - 0.5 * alpha) + np.array(AMBER) * 0.5 * alpha).astype(np.uint8)
        if self.status:
            blink = 1.0 if (t % 1.6) < 1.25 else 0.35
            self.status.draw(frame, alpha * blink)


# ----------------------------------------------------------------- chapter card
class ChapterCard:
    """'02 — THE GIANT' with a short amber rule, bottom-left, letter-spaced; animates in from the left."""

    def __init__(self, index: int, title: str):
        self.num = place(tracked(f"{index:02d}", "mono_medium", 26, AMBER, 0.2), MARGIN - 10, MARGIN + 20)
        self.title = place(tracked(title.upper(), "semibold", 54, TEXT, 0.22), MARGIN - 14, MARGIN + 54)

    def draw(self, frame: np.ndarray, t: float, hold: float = 4.2) -> None:
        a = fr.fade_window(t, 0.25, hold, 0.5)
        if a <= 0:
            return
        slide = int((1 - ease_out(min((t - 0.25) / 0.9, 1.0))) * -40)
        # dark gradient behind for legibility
        y1 = MARGIN + 170
        grad = (1 - np.linspace(0, 1, y1, dtype=np.float32))[:, None, None] ** 1.5 * 0.5 * a
        frame[:y1] = (frame[:y1].astype(np.float32) * (1 - grad)).astype(np.uint8)
        rule_w = int(90 * ease_out(min((t - 0.25) / 0.7, 1.0)))
        cv2.rectangle(frame, (MARGIN + 52, MARGIN + 37), (MARGIN + 52 + rule_w, MARGIN + 39), AMBER, -1)
        self.num.draw(frame, a, dx=slide)
        self.title.draw(frame, a, dx=slide)


# ----------------------------------------------------------------- big cinematic title (overlay or beat)
class TitleOverlay:
    def __init__(self, text: str, sub: str = ""):
        self.text = place(tracked(text.upper(), "semibold", 92, TEXT, 0.32), W // 2, H // 2, "mm")
        self.sub = place(tracked(sub.upper(), "mono", 24, DIM, 0.3), W // 2, H // 2 + 78, "mm") if sub else None

    def draw(self, frame: np.ndarray, t: float, duration: float) -> None:
        a = fr.fade_window(t, 0.4, duration - 0.3, 1.1)
        if a <= 0:
            return
        # tracking 'breath': text drifts slightly wider over the shot
        frame[:] = (frame.astype(np.float32) * (1 - 0.35 * a)).astype(np.uint8)
        self.text.draw(frame, a, dy=int((1 - a) * 12))
        if self.sub:
            self.sub.draw(frame, a * 0.9)


def title_beat(duration: float, text: str, sub: str = ""):
    ov = TitleOverlay(text, sub)
    bg = fr.starfield(5)

    def render(t):
        f = (bg.astype(np.float32) * 0.6).astype(np.uint8)
        ov.draw(f, t, duration)
        return f
    return render


# ----------------------------------------------------------------- glitch / signal lost
def glitch_beat(duration: float, text: str = "SIGNAL LOST", sub: str = "", src: np.ndarray | None = None,
                seed: int = 9):
    """The feed breaks up: the previous frame tears, colour-splits and dissolves into static, then
    a red warning holds over near-black with faint noise."""
    rng = np.random.default_rng(seed)
    src = src if src is not None else np.zeros((H, W, 3), np.uint8)
    title = place(tracked(text, "mono_bold", 76, RED, 0.35), W // 2, H // 2 - 10, "mm")
    subl = place(tracked(sub, "mono", 26, DIM, 0.2), W // 2, H // 2 + 70, "mm") if sub else None
    small_h, small_w = H // 4, W // 4

    def static(t, amount):
        n = rng.random((small_h, small_w)).astype(np.float32)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)
        return (n * 255 * amount)[..., None].repeat(3, -1)

    def render(t):
        u = t / duration
        brk = min(t / 0.9, 1.0)                     # 0..1 over the break-up
        f = src.astype(np.float32) * (1 - brk) ** 1.5
        if brk < 1:
            # horizontal tearing: shift random bands
            for _ in range(int(6 + 20 * brk)):
                y = int(rng.uniform(0, H - 10))
                hgt = int(rng.uniform(4, 60))
                f[y:y + hgt] = np.roll(f[y:y + hgt], int(rng.normal(0, 120 * brk + 10)), axis=1)
            # RGB split
            sh = int(4 + 30 * brk)
            f[..., 0] = np.roll(f[..., 0], sh, axis=1)
            f[..., 2] = np.roll(f[..., 2], -sh, axis=1)
        st_amt = 0.55 * math.sin(min(brk, 1) * math.pi) + 0.06 + 0.05 * (rng.random() < 0.08)
        f = f * (1 - st_amt * 0.5) + static(t, st_amt) * 0.5
        # scanlines
        f[::3] *= 0.7
        out = np.clip(f, 0, 255).astype(np.uint8)
        if t > 0.8:
            flick = 1.0 if rng.random() > 0.06 else 0.3
            a = min((t - 0.8) / 0.25, 1.0) * flick * min(1.0, (duration - t) / 0.4 + 0.0)
            title.draw(out, a, dx=int(rng.normal(0, 3)) if rng.random() < 0.15 else 0)
            if subl and t > 1.4:
                subl.draw(out, min((t - 1.4) / 0.4, 1.0) * min(1.0, (duration - t) / 0.4))
        return out
    return render


def black_beat(duration: float, ember: bool = True, seed: int = 4):
    """Near-black 'into the dark' beat: faint grain and one dim ember sinking and fading away."""
    rng = np.random.default_rng(seed)

    def render(t):
        u = t / duration
        f = np.full((H, W, 3), 6, np.float32)
        f += rng.normal(0, 2.2, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
        if ember:
            y = H * (0.30 + 0.45 * u)
            a = (1 - u) ** 1.5
            g = np.zeros((H, W), np.float32)
            cv2.circle(g, (W // 2, int(y)), 3, 1.0, -1, cv2.LINE_AA)
            g = cv2.GaussianBlur(g, (0, 0), 6) * 9 + g
            f += g[..., None] * np.array([255, 150, 70], np.float32) * a
        return np.clip(f, 0, 255).astype(np.uint8)
    return render


# ----------------------------------------------------------------- atmosphere profile (schematic)
PROFILE_LAYERS = [
    # label, sub label, y fraction of the column (schematic), colour
    ("Ammonia ice", "top cloud deck (probably)", 0.30, (232, 222, 205)),
    ("Ammonium hydrosulfide", "middle deck (likely)", 0.47, (205, 160, 110)),
    ("Water ice & vapour", "deepest deck (may be)", 0.64, (160, 175, 200)),
]


def profile_beat(duration: float, title: str = "Jupiter's weather layer", marks=None, probe=(0.12, 0.92),
                 source_label: str = "Source: NASA, NSSDC Jupiter fact sheet · schematic, not to scale"):
    """Vertical slice of the upper atmosphere: three cloud decks (~71 km in total), pressure/temperature
    marks and the probe's descent marker moving down the column."""
    marks = marks or [(0.12, "0.1 bar", "−161 °C"), (0.40, "1 bar", "−108 °C"), (0.92, "22.7 bar", "signal lost")]
    x0, x1 = int(W * 0.30), int(W * 0.70)
    top, bot = int(H * 0.16), int(H * 0.90)
    col_h = bot - top
    base = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, col_h, dtype=np.float32)
    # sky gradient: pale amber at top to deep brown at the bottom
    grad = (np.array([70, 58, 52])[None] * (1 - yy[:, None]) + np.array([28, 14, 8])[None] * yy[:, None])
    base[top:bot, x0:x1] = grad[:, None, :]
    noise = cv2.resize(np.random.default_rng(2).random((60, 14)).astype(np.float32), (x1 - x0, col_h),
                       interpolation=cv2.INTER_CUBIC).clip(0, 1)
    for _, _, fy, colr in PROFILE_LAYERS:
        cy = fy * col_h
        band = np.exp(-((np.arange(col_h) - cy) / (col_h * 0.045)) ** 2).astype(np.float32)
        a = band[:, None] * (0.55 + 0.45 * noise)
        base[top:bot, x0:x1] = base[top:bot, x0:x1] * (1 - a[..., None]) + np.array(colr, np.float32) * a[..., None]
    base = np.clip(base + fr.starfield(7).astype(np.float32) * 0.35 * (base.sum(-1, keepdims=True) < 1), 0, 255)
    base = base.astype(np.uint8)
    cv2.rectangle(base, (x0, top), (x1, bot), (90, 96, 110), 1, cv2.LINE_AA)
    t_layer = place(tracked(title.upper(), "semibold", 40, TEXT, 0.2), W // 2, int(H * 0.08), "mm")
    src_l = fr.text_layer(source_label, "regular", 20, DIM, W - 36, H - 26, anchor="rb")
    deck_l = []
    for name, sub, fy, _ in PROFILE_LAYERS:
        y = top + int(fy * col_h)
        deck_l.append((fr.text_layer(name, "semibold", 30, TEXT, x1 + 70, y - 2, anchor="lb"),
                       fr.text_layer(sub, "regular", 22, DIM, x1 + 70, y + 2, anchor="lt"), y))
    bracket_y0, bracket_y1 = top + int(0.24 * col_h), top + int(0.70 * col_h)
    span_l = fr.text_layer("≈ 71 km · three cloud decks", "medium", 26, AMBER, x1 + 70, bracket_y1 + 26,
                           anchor="lt")
    mark_l = []
    for fy, a, b in marks:
        y = top + int(fy * col_h)
        mark_l.append((fr.text_layer(a, "mono_medium", 26, TEXT, x0 - 30, y - 4, anchor="rb", shadow=False),
                       fr.text_layer(b, "mono", 22, DIM, x0 - 30, y + 2, anchor="rt", shadow=False), y))

    def render(t):
        f = base.copy()
        u = t / duration
        t_layer.draw(f, fr.fade_window(t, 0.1, duration, 0.5))
        for i, (la, lb, y) in enumerate(deck_l):
            a = fr.fade_window(t, 0.5 + 0.5 * i, duration, 0.5)
            cv2.line(f, (x1, y), (x1 + 58, y), (200, 200, 210), 1, cv2.LINE_AA)
            la.draw(f, a)
            lb.draw(f, a)
        ab = fr.fade_window(t, 2.2, duration, 0.6)
        if ab > 0:
            xb = x1 + 30
            cv2.line(f, (xb, bracket_y0), (xb, bracket_y1), AMBER, 2, cv2.LINE_AA)
            cv2.line(f, (xb - 10, bracket_y0), (xb, bracket_y0), AMBER, 2, cv2.LINE_AA)
            cv2.line(f, (xb - 10, bracket_y1), (xb, bracket_y1), AMBER, 2, cv2.LINE_AA)
            span_l.draw(f, ab)
        for la, lb, y in mark_l:
            cv2.line(f, (x0 - 18, y), (x0, y), (200, 200, 210), 1, cv2.LINE_AA)
            la.draw(f, 0.95)
            lb.draw(f, 0.95)
        # probe marker sinking down the column
        py = top + int((probe[0] + (probe[1] - probe[0]) * ease(u)) * col_h)
        px = (x0 + x1) // 2
        cv2.line(f, (px, top), (px, py), (255, 176, 59), 1, cv2.LINE_AA)
        cv2.circle(f, (px, py), 16, AMBER, 2, cv2.LINE_AA)
        cv2.circle(f, (px, py), 5, (255, 240, 220), -1, cv2.LINE_AA)
        src_l.draw(f, 0.8)
        return f
    return render


# ----------------------------------------------------------------- fact list
def fact_list_beat(duration: float, title: str, items: list[str], source_label: str = "", backdrop=None):
    """Items reveal one by one over a darkened, blurred backdrop (last frame of the previous shot)."""
    if backdrop is not None:
        bg = cv2.GaussianBlur(backdrop, (0, 0), 18).astype(np.float32) * 0.35
    else:
        bg = fr.starfield(5).astype(np.float32) * 0.8
    bg = bg.astype(np.uint8)
    t_l = place(tracked(title.upper(), "semibold", 30, AMBER, 0.28), MARGIN + 140, int(H * 0.30), "lm")
    n = len(items)
    rows = []
    for i, it in enumerate(items):
        y = int(H * 0.42 + i * 110)
        rows.append((place(tracked(f"{i + 1:02d}", "mono_medium", 34, DIM, 0.1), MARGIN + 140, y, "lm"),
                     fr.text_layer(it, "semibold", 56, TEXT, MARGIN + 240, y, anchor="lm"), y))
    src = fr.text_layer(source_label, "regular", 22, DIM, W - 36, H - 30, anchor="rb") if source_label else None
    step = max(min((duration - 1.5) / max(n, 1), 2.6), 0.8)

    def render(t):
        f = bg.copy()
        t_l.draw(f, fr.fade_window(t, 0.2, duration, 0.5))
        for i, (nl, tl, y) in enumerate(rows):
            st = 0.7 + i * step
            a = fr.fade_window(t, st, duration, 0.45)
            dx = int((1 - ease_out(min(max((t - st) / 0.6, 0), 1))) * 30)
            nl.draw(f, a * 0.9, dx=dx)
            tl.draw(f, a, dx=dx)
        if src:
            src.draw(f, 0.8)
        return f
    return render


# ----------------------------------------------------------------- big number + end card (cinematic style)
def fact_beat(duration: float, big: str, small: str = "", source_label: str = "", backdrop=None):
    """One huge number over the darkened, blurred previous shot; the number scales in slightly."""
    if backdrop is not None:
        bg = (cv2.GaussianBlur(backdrop, (0, 0), 22).astype(np.float32) * 0.3).astype(np.uint8)
    else:
        bg = (fr.starfield(5).astype(np.float32) * 0.7).astype(np.uint8)
    big_rgba = tracked(big, "display", 190, AMBER, 0.02)
    small_l = place(tracked(small.upper(), "medium", 30, TEXT, 0.22), W // 2, H // 2 + 120, "mm") if small else None
    src = fr.text_layer(source_label, "regular", 22, DIM, W - 36, H - 30, anchor="rb") if source_label else None

    def render(t):
        f = bg.copy()
        a = fr.fade_window(t, 0.25, duration, 0.6)
        s = 1.0 + 0.04 * (1 - ease_out(min(t / 1.2, 1.0)))
        img = cv2.resize(big_rgba, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR) if s != 1.0 else big_rgba
        place(img, W // 2, H // 2 - 20, "mm").draw(f, a)
        if small_l:
            small_l.draw(f, fr.fade_window(t, 0.8, duration, 0.6))
        if src:
            src.draw(f, 0.8)
        return f
    return render


def end_beat(duration: float, channel: str, tagline: str = "", note: str = "Sources and credits in the description"):
    bg = fr.starfield(9)
    name = place(tracked(channel.upper(), "semibold", 64, TEXT, 0.35), W // 2, H // 2 - 30, "mm")
    tag = place(tracked(tagline.upper(), "mono", 24, AMBER, 0.3), W // 2, H // 2 + 40, "mm") if tagline else None
    nt = place(tracked(note.upper(), "mono", 18, DIM, 0.2), W // 2, H - MARGIN, "mb")

    def render(t):
        f = (bg.astype(np.float32) * 0.55).astype(np.uint8)
        fade_out = min(1.0, max(duration - t, 0) / 1.5)
        name.draw(f, fr.fade_window(t, 0.3, duration + 1, 0.9) * fade_out)
        if tag:
            tag.draw(f, fr.fade_window(t, 1.0, duration + 1, 0.9) * fade_out)
        nt.draw(f, fr.fade_window(t, 1.6, duration + 1, 0.9) * fade_out)
        return f
    return render


# ----------------------------------------------------------------- character POV + radio log overlays
def shake(frame: np.ndarray, t: float, amount: float, seed: int = 0) -> np.ndarray:
    """Camera shake: smooth random translation + tiny rotation, amplitude ~14 px per unit."""
    if amount <= 0:
        return frame
    k = seed * 13.1
    dx = amount * 14 * (math.sin(t * 23.0 + k) * 0.6 + math.sin(t * 37.0 + 1.3 + k) * 0.4)
    dy = amount * 14 * (math.sin(t * 29.0 + 2.1 + k) * 0.6 + math.sin(t * 41.0 + 0.4 + k) * 0.4)
    rot = amount * 0.35 * math.sin(t * 17.0 + k)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, 1.0 + 0.03 * amount)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(frame, M, (W, H), borderMode=cv2.BORDER_REFLECT)


class PovFrame:
    """Looking out of the capsule: dark rounded window frame, faint glass reflection, corner brackets."""

    def __init__(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        inset_x, inset_y, r = W * 0.035, H * 0.05, 120.0
        qx = np.maximum(np.abs(xx - W / 2) - (W / 2 - inset_x - r), 0)
        qy = np.maximum(np.abs(yy - H / 2) - (H / 2 - inset_y - r), 0)
        d = np.sqrt(qx ** 2 + qy ** 2) - r              # signed distance to the rounded window edge
        frame_a = np.clip((d + 6) / 12, 0, 1)            # 1 on the frame, 0 in the window
        inner_shadow = np.exp(-np.maximum(-d, 0) / 70) * 0.55 * (1 - frame_a)
        glass = np.clip(1 - np.abs((xx / W - yy / H * 0.6) - 0.15) / 0.12, 0, 1) ** 2 * 0.05
        self.a = np.clip(frame_a + inner_shadow, 0, 1)[..., None].astype(np.float32)
        col = np.array([10, 11, 14], np.float32)
        # brushed-metal hint on the frame
        noise = cv2.GaussianBlur(np.random.default_rng(1).random((H, W)).astype(np.float32), (0, 0), 1.2)
        self.col = (col + (noise[..., None] - 0.5) * 10 * frame_a[..., None]).astype(np.float32)
        self.glass = (glass[..., None] * np.array([200, 215, 235], np.float32)).astype(np.float32)
        self.edge = np.clip(1 - np.abs(d) / 2.0, 0, 1)[..., None].astype(np.float32) * 0.35

    def draw(self, frame: np.ndarray, alpha: float = 1.0) -> np.ndarray:
        f = frame.astype(np.float32)
        a = self.a * alpha
        f = f * (1 - a) + self.col * a + self.glass * alpha + self.edge * alpha * np.array([150, 150, 160], np.float32)
        return np.clip(f, 0, 255).astype(np.uint8)


class NoteOverlay:
    """Two centred mono lines (e.g. the fiction disclaimer)."""

    def __init__(self, lines: list[str], big: bool = False):
        self.big = big
        if big:  # opening card: large, centred, on screen from the first frame
            self.layers = [place(tracked(l.upper(), "semibold", 58, TEXT, 0.42), W // 2, int(H * 0.5) + i * 80, "mm")
                           for i, l in enumerate(lines)]
        else:
            self.layers = [place(tracked(l.upper(), "mono_medium" if i == 0 else "mono", 34 if i == 0 else 26,
                                         TEXT if i == 0 else AMBER, 0.3), W // 2, int(H * 0.70) + i * 52, "mm")
                           for i, l in enumerate(lines)]

    def draw(self, frame: np.ndarray, t: float, duration: float) -> None:
        if self.big:
            a = min(1.0, max(duration - 0.3 - t, 0) / 0.5)
            frame[:] = (frame.astype(np.float32) * (1 - 0.45 * a)).astype(np.uint8)
            for l in self.layers:
                l.draw(frame, a)
            return
        for i, l in enumerate(self.layers):
            l.draw(frame, fr.fade_window(t, 0.4 + 0.6 * i, duration - 0.2, 0.6))


class RadioLog:
    """While a character speaks: '● MARA VOSS · VESPER DESCENT LOG' tag with a live waveform, and the line
    typed out as a transcript at the bottom of the frame (radio audio is harder to follow, so we show it)."""

    def __init__(self, name: str, tag: str, envelope: np.ndarray, fps: int):
        self.env, self.fps = envelope, fps
        self.tag_log = place(tracked(f"{name}  ·  {tag}", "mono_medium", 22, TEXT, 0.18), W // 2 - 40, H - 168, "mm")
        self.personal = {}
        self.name = name
        self.tag = self.tag_log
        self.cache: dict = {}

    def _tag_for(self, text: str):
        """Lines addressed to someone ('Noor, ...') switch the tag to a personal channel."""
        import re as _re
        m = _re.match(r"^\s*([A-Z][a-z]+),", text)
        if m and m.group(1) not in ("Oh", "Wait", "Okay", "Vesper", "Relay"):
            who = m.group(1).upper()
            if who not in self.personal:
                self.personal[who] = place(tracked(f"{self.name}  ·  PERSONAL MESSAGE  ·  {who}", "mono_medium", 22,
                                                   (255, 214, 150), 0.18), W // 2 - 40, H - 168, "mm")
            return self.personal[who]
        return self.tag_log

    def _lines(self, text: str) -> list[str]:
        if text not in self.cache:
            self.cache[text] = fr.wrap(text, font("mono_medium", 32), 1300)
        return self.cache[text]

    def draw(self, frame: np.ndarray, gt: float, sent: dict) -> None:
        st, en = sent["start"], sent["end"]
        a = min(1.0, (gt - st + 0.25) / 0.25, (en + 0.6 - gt) / 0.3)
        if a <= 0:
            return
        # tag + blinking dot + waveform
        self.tag = self._tag_for(sent["text"]) if not sent.get("personal_to") else self.tag
        self.tag.draw(frame, a * 0.95)
        tw = self.tag.rgb.shape[1]
        x0 = self.tag.x - 26
        if (gt * 2) % 1 < 0.7:
            cv2.circle(frame, (x0, H - 168), 7, RED, -1, cv2.LINE_AA)
        bx = self.tag.x + tw + 12
        i = int(gt * self.fps)
        for k in range(16):
            j = min(max(i - 15 + k, 0), len(self.env) - 1)
            h = int(4 + 34 * self.env[j])
            cv2.rectangle(frame, (bx + k * 7, H - 168 - h // 2), (bx + k * 7 + 3, H - 168 + h // 2), AMBER, -1)
        # typewriter transcript, revealed in step with the line
        lines = self._lines(sent["text"])
        total = sum(len(l) for l in lines)
        shown = int(total * min(1.0, max(gt - st, 0) / max((en - st) * 0.85, 0.3)))
        y = H - 118
        for l in lines:
            part = l[:max(shown, 0)]
            shown -= len(l)
            if part:
                _draw_text(frame, part, (W // 2 - font("mono_medium", 32).getlength(l) / 2, y), "mono_medium", 32,
                           (255, 214, 150), anchor="la", alpha=a)
            y += 44


def voice_envelope(wav_path, fps: int) -> np.ndarray:
    """0..1 loudness per video frame of the narration (drives the radio waveform)."""
    import soundfile as sf
    x, sr = sf.read(wav_path, dtype="float32")
    hop = sr // fps
    n = len(x) // hop
    rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1))
    return np.clip(rms / (np.percentile(rms, 98) + 1e-9), 0, 1).astype(np.float32)



# ----------------------------------------------------------------- scale: event horizon vs the Solar System
def horizon_scale_beat(duration: float, horizon_au: float = 1300.0, title: str = "",
                       orbits=(("Earth", 1.0), ("Jupiter", 5.2), ("Neptune", 30.1)),
                       source_label: str = ""):
    """Zoom out from Earth's orbit until the black hole's event horizon (radius `horizon_au`) fills the frame.
    Log-scaled camera so the move feels steady; labels fade in as each orbit comes into view."""
    cx, cy = W // 2, H // 2
    bg = (fr.starfield(11).astype(np.float32) * 0.9).astype(np.uint8)
    labels = {n: fr.text_layer(n, "medium", 26, DIM, 0, 0, anchor="lm") for n, _ in orbits}
    hz_label = fr.text_layer("Event horizon", "semibold", 34, AMBER, 0, 0, anchor="mm")
    t_layer = place(tracked(title.upper(), "semibold", 36, TEXT, 0.22), W // 2, int(H * 0.09), "mm") if title else None
    src = fr.text_layer(source_label, "regular", 22, DIM, W - 36, H - 30, anchor="rb") if source_label else None
    r0, r1 = 1.6, horizon_au * 1.25          # visible half-height in AU at start / end

    def render(t):
        u = ease(t / duration)
        half = math.exp(math.log(r0) + (math.log(r1) - math.log(r0)) * u)
        px_per_au = (H * 0.45) / half
        f = bg.copy()
        # horizon: black disk with a thin amber rim and a faint glow
        rh = horizon_au * px_per_au
        if rh < 4 * W:
            glow = np.zeros((H, W), np.float32)
            cv2.circle(glow, (cx, cy), int(rh), 1.0, int(max(2, rh * 0.04)), cv2.LINE_AA)
            glow = cv2.GaussianBlur(glow, (0, 0), max(rh * 0.03, 2))
            f = np.clip(f.astype(np.float32) + glow[..., None] * np.array(AMBER, np.float32) * 0.6, 0, 255).astype(np.uint8)
            cv2.circle(f, (cx, cy), int(rh), (6, 6, 8), -1, cv2.LINE_AA)
            cv2.circle(f, (cx, cy), int(rh), AMBER, 2, cv2.LINE_AA)
            a = min(1.0, max((rh - 60) / 200, 0))
            hz_label.x, hz_label.y = cx - hz_label.rgb.shape[1] // 2, int(cy - min(rh, H * 0.42) + 40) - hz_label.rgb.shape[0] // 2
            hz_label.draw(f, a)
        # planetary orbits (drawn on top of the horizon: they all fit inside it)
        for name, au in orbits:
            ro = au * px_per_au
            if ro < 1.5:
                continue
            a = min(1.0, (ro - 1.5) / 30) * min(1.0, max(0.0, 1.2 - ro / (W * 0.9)))
            if a <= 0:
                continue
            col = tuple(int(c * a + 20 * (1 - a)) for c in (200, 210, 230))
            cv2.circle(f, (cx, cy), int(ro), col, 1, cv2.LINE_AA)
            lab = labels[name]
            lab.x, lab.y = int(cx + ro * 0.707) + 8, int(cy - ro * 0.707) - lab.rgb.shape[0] // 2
            lab.draw(f, a)
        cv2.circle(f, (cx, cy), 3, (255, 230, 170), -1, cv2.LINE_AA)   # the Sun at the centre
        if t_layer:
            t_layer.draw(f, fr.fade_window(t, 0.3, duration, 0.5))
        if src:
            src.draw(f, 0.8)
        return f
    return render
