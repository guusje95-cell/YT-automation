"""Thumbnail variants (1280x720 JPEG, < 2 MB) from a real image plus 2-4 words.

Each text option produces one variant; layout: image filling the frame with a
dark gradient on the text side, heavy display type, amber accent bar. The
first variant is the default upload; the rest are for Test & Compare or later swaps.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ytauto.core import config
from ytauto.visuals import frames as fr

TW, TH = 1280, 720


def _cover(img: Image.Image, focus=(0.5, 0.5), zoom: float = 1.0) -> Image.Image:
    iw, ih = img.size
    s = max(TW / iw, TH / ih) * zoom
    img = img.resize((int(iw * s) + 1, int(ih * s) + 1), Image.LANCZOS)
    x = int(min(max(focus[0] * img.width - TW / 2, 0), img.width - TW))
    y = int(min(max(focus[1] * img.height - TH / 2, 0), img.height - TH))
    return img.crop((x, y, x + TW, y + TH))


def balanced_lines(text: str, max_lines: int = 3) -> list[str]:
    """Split 1-5 words into 1-3 lines minimising the longest line (by character count)."""
    words = text.split()
    if len(words) <= 1:
        return words
    best, best_score = [text], len(text)
    import itertools
    for k in range(1, min(max_lines, len(words))):
        for cuts in itertools.combinations(range(1, len(words)), k):
            parts = [" ".join(words[a:b]) for a, b in zip((0,) + cuts, cuts + (len(words),))]
            score = max(len(p) for p in parts) + 0.5 * len(parts)
            if score < best_score:
                best, best_score = parts, score
    return best


def render_variant(img_path: str, text: str, side: str = "left", focus=(0.5, 0.5), zoom: float = 1.0) -> Image.Image:
    base = Image.open(img_path).convert("RGB")
    base = Image.fromarray(fr._trim_light_borders(np.array(base)))
    im = _cover(base, focus, zoom)
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.15)
    # gradient for legibility on the text side
    grad = np.zeros((TH, TW), np.float32)
    xs = np.linspace(1, 0, TW) if side == "left" else np.linspace(0, 1, TW)
    grad[:] = 0.18 + 0.82 * np.clip(xs * 1.9 - 0.55, 0, 1) ** 0.9
    shade = Image.fromarray((grad * 235).astype(np.uint8))
    dark = Image.new("RGB", (TW, TH), tuple(config.get("brand.bg")))
    im = Image.composite(dark, im, shade)
    d = ImageDraw.Draw(im)
    lines = balanced_lines(text.upper())
    size = 150 if len(lines) <= 2 else 118
    f = fr.font("display", size)
    while max(f.getbbox(l)[2] for l in lines) > TW * 0.52 and size > 70:
        size -= 6
        f = fr.font("display", size)
    lh = int(size * 1.02)
    total_h = lh * len(lines)
    y0 = (TH - total_h) // 2
    x0 = 64 if side == "left" else TW - 64
    shadow = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for k, l in enumerate(lines):
        w = f.getbbox(l)[2]
        x = x0 if side == "left" else x0 - w
        sd.text((x + 4, y0 + k * lh + 6), l, font=f, fill=(0, 0, 0, 220))
    im = Image.alpha_composite(im.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(8))).convert("RGB")
    d = ImageDraw.Draw(im)
    accent = tuple(config.get("brand.accent"))
    for k, l in enumerate(lines):
        w = f.getbbox(l)[2]
        x = x0 if side == "left" else x0 - w
        d.text((x, y0 + k * lh), l, font=f, fill=accent if k == len(lines) - 1 else (255, 255, 255))
    bx = x0 if side == "left" else x0 - 160
    d.rectangle([bx, y0 - 28, bx + 160, y0 - 16], fill=accent)
    return im


def build(spec) -> list[str]:
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    tcfg = spec.data.get("thumbnail") or {}
    outs = []
    for k, v in enumerate(tcfg.get("variants") or [{"text": t} for t in tcfg.get("texts", [])]):
        o = {**tcfg, **v}
        im = render_variant(manifest[o["asset"]]["file"], o["text"], side=o.get("side", "left"),
                            focus=tuple(o.get("focus", (0.5, 0.5))), zoom=o.get("zoom", 1.0))
        p = spec.out / f"thumbnail_{k + 1}.jpg"
        q = 92
        im.save(p, quality=q, optimize=True)
        while p.stat().st_size > 1_900_000 and q > 60:
            q -= 6
            im.save(p, quality=q, optimize=True)
        outs.append(str(p))
    return outs
