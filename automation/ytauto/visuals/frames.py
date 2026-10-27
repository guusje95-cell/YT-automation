"""Frame renderers for each beat type.

Every renderer returns `render(t) -> np.ndarray (H, W, 3) uint8` for t in [0, duration).
Text is pre-rendered once into RGBA layers and alpha-composited per frame.
"""
from __future__ import annotations

import math
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ytauto.core import config
from ytauto.core.log import ROOT, get_logger

log = get_logger(__name__)

W = config.get("video.width", 1920)
H = config.get("video.height", 1080)
FPS = config.get("video.fps", 30)
MARGIN = config.get("video.safe_margin", 80)
BG = tuple(config.get("brand.bg"))
ACCENT = tuple(config.get("brand.accent"))
TEXT = tuple(config.get("brand.text"))
MUTED = tuple(config.get("brand.muted"))


# ----------------------------------------------------------------- helpers
@lru_cache(maxsize=64)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ROOT / config.get(f"brand.font_{kind}")), size)


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


class Layer:
    """Pre-rendered RGBA patch positioned on the canvas."""

    def __init__(self, rgba: np.ndarray, x: int, y: int):
        self.rgb = rgba[..., :3].astype(np.float32)
        self.a = rgba[..., 3:4].astype(np.float32) / 255.0
        self.x, self.y = int(x), int(y)

    def draw(self, frame: np.ndarray, opacity: float = 1.0, dx: int = 0, dy: int = 0) -> None:
        if opacity <= 0.003:
            return
        h, w = self.a.shape[:2]
        x0, y0 = self.x + dx, self.y + dy
        fx0, fy0 = max(x0, 0), max(y0, 0)
        fx1, fy1 = min(x0 + w, W), min(y0 + h, H)
        if fx1 <= fx0 or fy1 <= fy0:
            return
        sub = frame[fy0:fy1, fx0:fx1].astype(np.float32)
        a = self.a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * opacity
        c = self.rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
        frame[fy0:fy1, fx0:fx1] = (sub * (1 - a) + c * a).astype(np.uint8)


def text_layer(text: str, kind: str, size: int, color=TEXT, x: int = 0, y: int = 0, max_w: int | None = None,
               anchor: str = "lt", shadow: bool = True, line_gap: float = 1.15, bg: tuple | None = None,
               pad: int = 0, align: str = "left") -> Layer:
    f = font(kind, size)
    lines = wrap(text, f, max_w) if max_w else text.split("\n")
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * line_gap)
    widths = [f.getbbox(l)[2] for l in lines] or [0]
    tw, th = max(widths), lh * len(lines)
    sp = 12 if shadow else 0
    img = Image.new("RGBA", (tw + 2 * pad + 2 * sp, th + 2 * pad + 2 * sp), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bg:
        d.rounded_rectangle([sp, sp, sp + tw + 2 * pad, sp + th + 2 * pad], radius=10, fill=bg)
    for i, l in enumerate(lines):
        lx = sp + pad + (tw - widths[i] if align == "right" else (tw - widths[i]) // 2 if align == "center" else 0)
        ly = sp + pad + i * lh
        if shadow:
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((lx, ly + 3), l, font=f, fill=(0, 0, 0, 170))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
            d = ImageDraw.Draw(img)
        d.text((lx, ly), l, font=f, fill=color + (255,) if len(color) == 3 else color)
    arr = np.array(img)
    w, h = img.size
    ax = {"l": 0, "m": w // 2, "r": w}[anchor[0]]
    ay = {"t": 0, "m": h // 2, "b": h}[anchor[1]]
    return Layer(arr, x - ax, y - ay)


def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    out = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w_ in words:
            trial = f"{line} {w_}".strip()
            if f.getbbox(trial)[2] <= max_w or not line:
                line = trial
            else:
                out.append(line)
                line = w_
        out.append(line)
    return out


@lru_cache(maxsize=4)
def starfield(seed: int = 3) -> np.ndarray:
    """Deterministic dark gradient with faint stars, used behind text cards."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W * 0.35) / W) ** 2 + ((yy - H * 0.3) / H) ** 2)
    base = np.array(BG, np.float32)
    glow = np.array([28, 36, 64], np.float32)
    img = base + glow * np.clip(1 - r * 1.4, 0, 1)[..., None]
    n = 900
    xs, ys = rng.integers(0, W, n), rng.integers(0, H, n)
    b = rng.uniform(40, 200, n) ** 1.0
    for x, y, v in zip(xs, ys, b):
        img[y, x] = np.minimum(img[y, x] + v * (0.6 if rng.random() < 0.8 else 1.0), 255)
    img = cv2.GaussianBlur(img, (0, 0), 0.6)
    return np.clip(img, 0, 255).astype(np.uint8)


@lru_cache(maxsize=1)
def vignette() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return (1 - 0.35 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)


def apply_vignette(frame: np.ndarray) -> np.ndarray:
    return (frame.astype(np.float32) * vignette()).astype(np.uint8)


# ----------------------------------------------------------------- image beat
@lru_cache(maxsize=48)
def _load_image(path: str, max_side: int = 4200) -> np.ndarray:
    im = Image.open(path)
    if im.mode in ("I;16", "I", "F"):
        im = im.point(lambda v: v / 256)
    im = im.convert("RGB")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    return _trim_light_borders(np.array(im))


def _trim_light_borders(a: np.ndarray, thresh: int = 235) -> np.ndarray:
    """Remove near-white margins baked into some press images (e.g. figure panels)."""
    g = a.mean(axis=2)
    rows = np.where((g < thresh).mean(axis=1) > 0.02)[0]
    cols = np.where((g < thresh).mean(axis=0) > 0.02)[0]
    if len(rows) == 0 or len(cols) == 0:
        return a
    y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    if (y1 - y0) * (x1 - x0) < 0.97 * a.shape[0] * a.shape[1]:
        return np.ascontiguousarray(a[y0:y1, x0:x1])
    return a


def _dark_edges(a: np.ndarray) -> bool:
    edge = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3),
                           a[:, -8:].reshape(-1, 3)])
    return float(edge.mean()) < 22


def _blur_backdrop(img: np.ndarray) -> np.ndarray:
    ih, iw = img.shape[:2]
    s = max(W / iw, H / ih)
    small = cv2.resize(img, (max(int(iw * s / 8), 2), max(int(ih * s / 8), 2)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    big = cv2.resize(small, (int(iw * s) + 2, int(ih * s) + 2), interpolation=cv2.INTER_LINEAR)
    y0, x0 = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
    return (big[y0:y0 + H, x0:x0 + W].astype(np.float32) * 0.35).astype(np.uint8)


def image_beat(path: str, duration: float, motion: str = "in", focus=(0.5, 0.5), fit: str = "auto",
               zoom: float = 0.12, crop=None):
    img = _load_image(path)
    if crop:  # (x0, y0, x1, y1) fractions: drop borders, captions or empty margins
        ch, cw = img.shape[:2]
        img = np.ascontiguousarray(img[int(crop[1] * ch):int(crop[3] * ch), int(crop[0] * cw):int(crop[2] * cw)])
    ih, iw = img.shape[:2]
    up = max(W / iw, H / ih) * (1 + zoom)
    if up > 1.25:  # small source (e.g. 1024 px Flickr): upscale once with bicubic + gentle unsharp mask
        img = cv2.resize(img, (int(iw * up), int(ih * up)), interpolation=cv2.INTER_CUBIC)
        soft = cv2.GaussianBlur(img, (0, 0), 1.4)
        img = cv2.addWeighted(img, 1.5, soft, -0.5, 0)
        ih, iw = img.shape[:2]
    aspect, target = iw / ih, W / H
    if fit == "auto":
        fit = "cover" if 0.72 * target <= aspect <= 1.6 * target else "contain"
    fx, fy = focus
    if fit == "cover":
        s0 = max(W / iw, H / ih)
        backdrop = None
    else:
        s0 = min((W - 2 * 40) / iw, (H - 2 * 40) / ih)
        if _dark_edges(img):  # space image on black: blend seamlessly into a dark background
            s0 = min(W / iw, H / ih)
            backdrop = np.zeros((H, W, 3), np.uint8)
        else:
            backdrop = _blur_backdrop(img)
        if aspect > 2.2 * target and motion in ("in", "out"):
            motion = "pan_right"  # panoramas read best as pans
            s0 = H / ih * 1.0
            backdrop = None

    def params(t: float):
        u = ease(t / max(duration, 1e-6))
        z = 1.0
        cx, cy = fx, fy
        if motion == "in":
            z = 1.0 + zoom * u
        elif motion == "out":
            z = 1.0 + zoom * (1 - u)
        elif motion in ("pan_left", "pan_right", "up", "down"):
            z = 1.0 + zoom * 0.6
            span = 0.5
            d = (u - 0.5) * span
            if motion == "pan_left":
                cx = fx - d
            elif motion == "pan_right":
                cx = fx + d
            elif motion == "up":
                cy = fy - d
            else:
                cy = fy + d
        return z, cx, cy

    def render(t: float) -> np.ndarray:
        z, cx, cy = params(t)
        s = s0 * z
        sw, sh = iw * s, ih * s
        # top-left of the scaled image in canvas coords, so that (cx, cy) maps to centre, clamped to cover
        tx = W / 2 - cx * sw
        ty = H / 2 - cy * sh
        if fit == "cover" or backdrop is None:
            if sw >= W:
                tx = min(0, max(W - sw, tx))
            else:
                tx = (W - sw) / 2
            if sh >= H:
                ty = min(0, max(H - sh, ty))
            else:
                ty = (H - sh) / 2
        else:
            tx, ty = (W - sw) / 2, (H - sh) / 2
        M = np.float32([[s, 0, tx], [0, s, ty]])
        if backdrop is not None:
            out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT,
                                 dst=backdrop.copy())
        else:
            out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=BG)
        return out
    return render


# ----------------------------------------------------------------- video beat
@lru_cache(maxsize=32)
def media_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


class VideoReader:
    def __init__(self, path: str, start: float, duration: float, speed: float = 1.0, zoom: float = 1.0):
        self.n = int(math.ceil(duration * FPS)) + 2
        clip = media_duration(path)
        need = duration * speed
        if clip and start + need > clip:
            new = max(0.0, clip - need - 0.05)
            log.warning("clip %s too short for start=%.1f+%.1fs; using start=%.1f (frames hold if still short)",
                        Path(path).name, start, need, new)
            start = new
        zw, zh = int(W * zoom) // 2 * 2, int(H * zoom) // 2 * 2
        vf = (f"setpts={1 / speed}*PTS,fps={FPS},scale={zw}:{zh}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H}")
        self.proc = subprocess.Popen(
            ["ffmpeg", "-v", "quiet", "-ss", str(start), "-i", path, "-t", str(need + 1),
             "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.frames: list[np.ndarray] = []
        self.done = False

    def get(self, i: int) -> np.ndarray:
        while len(self.frames) <= i and not self.done:
            buf = self.proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                self.done = True
                break
            self.frames.append(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
            if len(self.frames) > 3:  # keep memory bounded; we only need sequential access
                self.frames[len(self.frames) - 4] = None  # type: ignore
        idx = min(i, len(self.frames) - 1)
        while idx >= 0 and self.frames[idx] is None:
            idx -= 1
        if idx < 0:
            return np.zeros((H, W, 3), np.uint8)
        return self.frames[idx]

    def close(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def video_beat(path: str, duration: float, start: float = 0.0, speed: float = 1.0, zoom: float = 1.0):
    reader = VideoReader(path, start, duration, speed, zoom)

    def render(t: float) -> np.ndarray:
        f = reader.get(int(t * FPS)).copy()
        if t >= duration - 1.0 / FPS:
            reader.close()
        return f
    render.close = reader.close  # type: ignore
    return render


# ----------------------------------------------------------------- cards
def title_beat(duration: float, text: str, kicker: str = ""):
    bg = starfield(5)
    t1 = text_layer(text, "display", 104, TEXT, W // 2, H // 2 - 20, max_w=W - 4 * MARGIN, anchor="mb",
                    align="center")
    t2 = text_layer(kicker, "medium", 40, MUTED, W // 2, H // 2 + 30, max_w=W - 4 * MARGIN, anchor="mt",
                    align="center") if kicker else None

    def render(t: float) -> np.ndarray:
        f = bg.copy()
        a = ease_out(t / 0.8)
        t1.draw(f, a, dy=int(30 * (1 - a)))
        cv2.rectangle(f, (W // 2 - int(120 * a), H // 2 - 4), (W // 2 + int(120 * a), H // 2), ACCENT,
                      -1)
        if t2:
            t2.draw(f, ease_out((t - 0.4) / 0.8))
        return f
    return render


def fact_beat(duration: float, big: str, small: str = "", source_label: str = ""):
    bg = starfield(11)
    tb = text_layer(big, "display", 190, ACCENT, W // 2, H // 2 + 10, max_w=W - 2 * MARGIN, anchor="mb",
                    align="center")
    ts = text_layer(small, "medium", 52, TEXT, W // 2, H // 2 + 50, max_w=W - 5 * MARGIN, anchor="mt",
                    align="center") if small else None
    tsrc = text_layer(f"Source: {source_label}", "regular", 26, MUTED, W // 2, H - MARGIN, max_w=W - 4 * MARGIN,
                      anchor="mb", align="center", shadow=False) if source_label else None

    def render(t: float) -> np.ndarray:
        f = bg.copy()
        a = ease_out(t / 0.7)
        tb.draw(f, a, dy=int(40 * (1 - a)))
        if ts:
            ts.draw(f, ease_out((t - 0.35) / 0.7))
        if tsrc:
            tsrc.draw(f, 0.9 * ease_out((t - 0.6) / 0.6))
        return f
    return render


def list_beat(duration: float, title: str, items: list[str], highlight: int | None = None):
    bg = starfield(17)
    th = text_layer(title.upper(), "bold", 34, ACCENT, MARGIN * 2, 150, shadow=False)
    rows = []
    y = 250
    for i, it in enumerate(items):
        on = highlight is None or i == highlight
        num = text_layer(f"{i + 1}", "display", 64, ACCENT if on else (90, 98, 120), MARGIN * 2, y, shadow=False)
        txt = text_layer(it, "semibold" if on else "medium", 58, TEXT if on else (110, 118, 140),
                         MARGIN * 2 + 90, y + 4, shadow=False)
        rows.append((num, txt, on))
        y += 132

    def render(t: float) -> np.ndarray:
        f = bg.copy()
        th.draw(f, ease_out(t / 0.5))
        for i, (num, txt, on) in enumerate(rows):
            a = ease_out((t - 0.12 * i) / 0.5)
            num.draw(f, a, dx=int(-30 * (1 - a)))
            txt.draw(f, a, dx=int(-30 * (1 - a)))
            if on and highlight is not None:
                ya = txt.y + 92
                cv2.rectangle(f, (txt.x + 12, ya), (txt.x + 12 + int(260 * ease_out((t - 0.6) / 0.6)), ya + 6),
                              ACCENT, -1)
        return f
    return render


def end_beat(duration: float, text: str):
    bg = starfield(23)
    name = text_layer(config.get("channel.name"), "display", 120, TEXT, W // 2, H // 2 - 10, anchor="mb",
                      align="center")
    tag = text_layer(text, "medium", 48, ACCENT, W // 2, H // 2 + 30, anchor="mt", align="center")
    src = text_layer("Sources and image credits in the description", "regular", 30, MUTED, W // 2, H - MARGIN,
                     anchor="mb", align="center", shadow=False)

    def render(t: float) -> np.ndarray:
        f = bg.copy()
        a = ease_out(t / 0.8)
        name.draw(f, a, dy=int(20 * (1 - a)))
        tag.draw(f, ease_out((t - 0.4) / 0.8))
        src.draw(f, ease_out((t - 0.8) / 0.8))
        fade = min(1.0, max(0.0, (duration - t) / 1.2))
        return (f.astype(np.float32) * fade).astype(np.uint8)
    return render


# ----------------------------------------------------------------- diagrams
def layers_disc(radius: int, bounds: list[float], colors: list[tuple], highlight: int | None, t: float) -> np.ndarray:
    """Cutaway of a body with concentric layers at true relative radii (bounds = outer radius fractions)."""
    size = radius * 2 + 8
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2
    r = np.sqrt(xx ** 2 + yy ** 2) / radius
    ang = np.arctan2(yy, xx)
    img = np.zeros((size, size, 4), np.float32)
    inner = 0.0
    for k, (b, col) in enumerate(zip(bounds, colors)):
        m = (r >= inner) & (r < b)
        col = np.array(col, np.float32)
        dim = 1.0 if highlight is None or highlight == k else 0.38
        if k == len(bounds) - 1:  # subtle convective texture on the outer layer
            tex = (1.0 + 0.07 * np.sin(ang * 40 + r * 60))[m][:, None]
            img[m, :3] = np.clip(col[None, :] * tex * dim, 0, 255)
        else:
            img[m, :3] = col * dim
        img[m, 3] = 255
        inner = b
    # boundary rings
    for b in bounds:
        ring = np.abs(r - b) < 1.6 / radius
        img[ring, :3] = 255
        img[ring, 3] = 200
    a = ease_out(t)
    img[..., 3] *= a
    return img.astype(np.uint8)


def scale_beat(duration: float, mode: str = "circles", title: str = "", labels: list[str] | None = None,
               items: list[dict] | None = None, highlight: int | None = None, bounds: list[float] | None = None):
    """Data diagrams. mode='circles': items [{label, value, color?}] drawn with true relative radii.
    mode='core': schematic of a compact vs dilute planetary core."""
    bg = starfield(29)
    tl = text_layer(title, "bold", 46, TEXT, W // 2, 120, anchor="mt", align="center") if title else None
    labels = labels or []

    def planet_disc(radius: int, core_r: int, dilute: bool, t: float) -> np.ndarray:
        size = radius * 2 + 4
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2
        r = np.sqrt(xx ** 2 + yy ** 2)
        img = np.zeros((size, size, 4), np.float32)
        body = (r <= radius).astype(np.float32)
        # envelope: banded beige-brown
        bands = 0.5 + 0.5 * np.sin(yy / radius * 9.0)
        env = np.stack([200 + 30 * bands, 170 + 25 * bands, 130 + 20 * bands], -1)
        shade = np.clip(1.1 - (r / radius) ** 2 * 0.5, 0, 1)[..., None]
        img[..., :3] = env * shade
        img[..., 3] = body * 255
        g = ease_out(t)
        if dilute:
            core = np.clip(1 - r / (core_r * 1.0), 0, 1) ** 0.8 * g
        else:
            core = (r <= core_r * g).astype(np.float32)
        core_col = np.array([120, 80, 60], np.float32)
        img[..., :3] = img[..., :3] * (1 - core[..., None]) + core_col * core[..., None]
        return img.astype(np.uint8)

    def render(t: float) -> np.ndarray:
        f = bg.copy()
        if tl:
            tl.draw(f, ease_out(t / 0.5))
        if mode == "layers":
            bnds = bounds or [0.25, 0.70, 1.0]
            cols = [(255, 244, 200), (255, 170, 60), (220, 80, 30)][: len(bnds)]
            rad = 400
            disc = layers_disc(rad, bnds, cols, highlight, t / 0.9)
            cx, cy = int(W * 0.36), int(H * 0.56)
            Layer(disc, cx - disc.shape[1] // 2, cy - disc.shape[0] // 2).draw(f, 1.0)
            inner = 0.0
            for k, (b, lab) in enumerate(zip(bnds, labels)):
                mid = (inner + b) / 2 * rad
                y_lab = int(cy - rad * 0.75 + (len(bnds) - 1 - k) * 200)  # outer layer on top: no crossing lines
                on = highlight is None or highlight == k
                a = ease_out((t - 0.4 - 0.15 * k) / 0.6)
                col = ACCENT if (on and highlight is not None) else (TEXT if on else (120, 128, 150))
                x0 = cx + int(mid * 0.7071)
                y0 = cy - int(mid * 0.7071)
                if a > 0:
                    cv2.line(f, (x0, y0), (int(W * 0.62), y_lab + 26), col, 2, cv2.LINE_AA)
                    cv2.circle(f, (x0, y0), 6, col, -1, cv2.LINE_AA)
                text_layer(lab, "semibold" if on else "medium", 44, col, int(W * 0.63), y_lab,
                           max_w=int(W * 0.34)).draw(f, a)
                inner = b
        elif mode == "core":
            for i, (cxf, dil) in enumerate(((0.3, False), (0.7, True))):
                a = ease_out((t - 0.3 * i) / 0.8)
                disc = planet_disc(300, 95 if not dil else 210, dil, (t - 0.3 * i - 0.4) / 1.2)
                Layer(disc, int(W * cxf - disc.shape[1] / 2), int(H * 0.55 - disc.shape[0] / 2)).draw(f, a)
                if i < len(labels):
                    text_layer(labels[i], "semibold", 40, ACCENT if dil else TEXT, int(W * cxf), int(H * 0.55) + 330,
                               anchor="mt", align="center").draw(f, a)
        else:
            vals = [it["value"] for it in items or []]
            if vals:
                vmax = max(vals)
                baseline = int(H * 0.86)
                rmax = int(min(H * 0.33, W * 0.8 / (2 * len(vals))))
                xs = np.linspace(W * 0.18, W * 0.82, len(vals))
                if len(vals) > 1 and max(vals) / sorted(vals)[-2] > 3:  # one dominant body: give it room on the right
                    xs = list(np.linspace(W * 0.12, W * 0.42, len(vals) - 1)) + [W * 0.72]
                for i, it in enumerate(items):
                    a = ease_out((t - 0.35 * i) / 0.8)
                    rad = max(int(rmax * it["value"] / vmax * a), 1)
                    col = tuple(it.get("color", ACCENT))
                    cx_i, cy_i = int(xs[i]), baseline - max(rad, 1)
                    cv2.circle(f, (cx_i, cy_i), rad, col, -1, lineType=cv2.LINE_AA)
                    if rad < 8 and a > 0:  # true-scale dot: ring it so it can be found
                        cv2.circle(f, (cx_i, baseline - 2), 22, ACCENT, 2, lineType=cv2.LINE_AA)
                    text_layer(it["label"], "semibold", 38, TEXT, cx_i, baseline + 24, anchor="mt",
                               align="center").draw(f, a)
                    if it.get("note"):
                        text_layer(it["note"], "regular", 28, MUTED, cx_i, baseline + 82, anchor="mt",
                                   align="center", shadow=False).draw(f, a)
        return f
    return render


# ----------------------------------------------------------------- overlays
def short_credit(credit: str) -> str:
    c = re.sub(r"\s+", " ", credit or "").strip()
    c = re.sub(r"^(JunoCam )?Image data:\s*", "", c, flags=re.I)
    c = re.sub(r"(JunoCam )?Image processing(?: by)?:?\s*", "· Processing: ", c, flags=re.I)
    c = re.sub(r"Enhanced image by (.+?) based on images provided courtesy of (.+)", r"\2 · Processing: \1", c,
               flags=re.I)
    c = c.replace(" Earth Image: NASA", "")
    return c[:110]


class Overlays:
    """Credit (bottom-right), beat label (bottom-left) and chapter title (top-left)."""

    def __init__(self):
        self.cache: dict = {}

    def credit(self, text: str) -> Layer:
        key = ("c", text)
        if key not in self.cache:
            self.cache[key] = text_layer(text, "regular", 22, (225, 228, 235), W - 36, H - 30, anchor="rb",
                                         shadow=True)
        return self.cache[key]

    def label(self, text: str) -> Layer:
        key = ("l", text)
        if key not in self.cache:
            self.cache[key] = text_layer(text, "semibold", 34, TEXT, MARGIN + 18, H - MARGIN - 40, anchor="lb",
                                         shadow=True, bg=(8, 11, 20, 150), pad=14)
        return self.cache[key]

    def chapter(self, text: str) -> Layer:
        key = ("h", text)
        if key not in self.cache:
            self.cache[key] = text_layer(text.upper(), "bold", 30, ACCENT, MARGIN, MARGIN - 10, anchor="lt",
                                         shadow=True)
        return self.cache[key]


def fade_window(t: float, start: float, end: float, ramp: float = 0.4) -> float:
    if t < start or t > end:
        return 0.0
    return min(1.0, (t - start) / ramp, (end - t) / ramp)
