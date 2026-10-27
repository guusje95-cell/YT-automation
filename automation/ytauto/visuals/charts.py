"""Data visuals for the car channel: the animated record chart and the speed counter.

Renderers follow the frames.py contract: `render(t) -> (H, W, 3) uint8` for t in [0, duration).
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from ytauto.visuals import frames as fr
from ytauto.visuals.editorial import AMBER, DIM, RED, place, tracked
from ytauto.visuals.frames import H, MARGIN, TEXT, W, ease, ease_out

GRID = (52, 56, 66)
WHITE = (236, 238, 242)


def _backdrop(seed: int = 5) -> np.ndarray:
    """Dark graphite gradient with a faint warm glow low on the frame (no stars: this is the road, not space)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W * 0.6) / W) ** 2 + ((yy - H * 0.95) / H) ** 2)
    img = np.array([20, 21, 25], np.float32) + np.array([46, 30, 14], np.float32) * np.clip(1 - r * 1.3, 0, 1)[..., None]
    grain = np.random.default_rng(seed).normal(0, 2.2, (H, W, 1)).astype(np.float32)
    return np.clip(img + grain, 0, 255).astype(np.uint8)


def _lerp_window(a, b, u):
    return [a[i] + (b[i] - a[i]) * u for i in range(2)]


def record_chart_beat(duration: float, points: list[dict], title: str = "", unit: str = "km/h",
                      reveal=(1895, 2026), x_range=((1895, 2030), (1895, 2030)), y_range=((0, 520), (0, 520)),
                      focus: str | None = None, source_label: str = "", wall: float | None = None):
    """Speed records over time. Official records draw as a step line (a record stands until it is beaten);
    `kind: disputed` points are hollow red with a question mark, `kind: oneway` points are hollow white.
    The reveal year and the visible window (x_range/y_range: start window, end window) animate over the beat.
    `focus` names a point label that gets a pulsing ring once revealed."""
    gx0, gx1 = MARGIN + 150, W - MARGIN - 40
    gy0, gy1 = int(H * 0.20), int(H * 0.84)
    bg = _backdrop()
    t_layer = place(tracked(title.upper(), "semibold", 34, TEXT, 0.22), gx0, int(H * 0.09), "lm") if title else None
    unit_l = fr.text_layer(unit, "mono", 22, DIM, gx0 - 20, gy0 - 34, anchor="rb", shadow=False)
    src = fr.text_layer(source_label, "regular", 22, DIM, W - 36, H - 30, anchor="rb") if source_label else None
    pts = sorted(points, key=lambda p: p["year"])
    labels = {}
    for p in pts:
        if p.get("label"):
            col = RED if p.get("kind") == "disputed" else (WHITE if p.get("kind") == "oneway" else AMBER)
            labels[id(p)] = (fr.text_layer(p["label"], "semibold", 26, col, 0, 0, anchor="lb"),
                             fr.text_layer(p.get("sub", ""), "mono", 20, DIM, 0, 0, anchor="lt", shadow=False)
                             if p.get("sub") else None)
    tick_cache: dict[str, fr.Layer] = {}
    wall_l = place(tracked(f"{wall:g} {unit}".upper(), "mono_medium", 22, RED, 0.2, shadow=False), 0, 0) \
        if wall is not None else None

    def tick(text):
        if text not in tick_cache:
            tick_cache[text] = fr.text_layer(text, "mono", 20, DIM, 0, 0, anchor="mm", shadow=False)
        return tick_cache[text]

    def render(t):
        u = ease(t / duration)
        xr = _lerp_window(x_range[0], x_range[1], u)
        yr = _lerp_window(y_range[0], y_range[1], u)
        year_now = reveal[0] + (reveal[1] - reveal[0]) * ease(min(t / max(duration - 0.8, 0.1), 1.0))

        def px(year, v):
            return (int(gx0 + (year - xr[0]) / (xr[1] - xr[0]) * (gx1 - gx0)),
                    int(gy1 - (v - yr[0]) / (yr[1] - yr[0]) * (gy1 - gy0)))

        f = bg.copy()
        # grid + ticks
        ystep = _nice_step(yr[1] - yr[0])
        v = math.ceil(yr[0] / ystep) * ystep
        while v <= yr[1]:
            _, y = px(xr[0], v)
            cv2.line(f, (gx0, y), (gx1, y), GRID, 1, cv2.LINE_AA)
            lab = tick(f"{int(v)}")
            lab.x, lab.y = gx0 - 50 - lab.rgb.shape[1] // 2, y - lab.rgb.shape[0] // 2
            lab.draw(f, 0.9)
            v += ystep
        xstep = _nice_step(xr[1] - xr[0], years=True)
        yv = math.ceil(xr[0] / xstep) * xstep
        while yv <= xr[1]:
            x, _ = px(yv, yr[0])
            cv2.line(f, (x, gy1), (x, gy1 + 8), DIM, 1, cv2.LINE_AA)
            lab = tick(str(int(yv)))
            lab.x, lab.y = x - lab.rgb.shape[1] // 2, gy1 + 22
            lab.draw(f, 0.9)
            yv += xstep
        cv2.line(f, (gx0, gy1), (gx1, gy1), DIM, 1, cv2.LINE_AA)
        if wall is not None and yr[0] <= wall <= yr[1]:   # dashed red barrier line, e.g. the 500 km/h wall
            _, wy = px(xr[0], wall)
            for x0 in range(gx0, gx1, 28):
                cv2.line(f, (x0, wy), (min(x0 + 16, gx1), wy), RED, 2, cv2.LINE_AA)
            wall_l.x, wall_l.y = gx0 + 10, wy - 8 - wall_l.rgb.shape[0]
            wall_l.draw(f, 0.95)
        axes = f.copy()   # data is clipped to the plot area against this afterwards
        official = [p for p in pts if p.get("kind", "record") == "record" and p["year"] <= year_now]
        if official:
            poly = []
            for i, p in enumerate(official):
                x, y = px(p["year"], p["value"])
                if i:
                    poly.append((x, poly[-1][1]))
                poly.append((x, y))
            poly.append((px(year_now, 0)[0], poly[-1][1]))
            arr = np.array(poly, np.int32)
            glow = np.zeros((H, W), np.float32)
            cv2.polylines(glow, [arr], False, 1.0, 9, cv2.LINE_AA)
            glow = cv2.GaussianBlur(glow, (0, 0), 9)
            f[:] = np.clip(f.astype(np.float32) + glow[..., None] * np.array(AMBER, np.float32) * 0.55, 0, 255).astype(np.uint8)
            cv2.polylines(f, [arr], False, AMBER, 3, cv2.LINE_AA)
        for p in pts:
            if p["year"] > year_now:
                continue
            x, y = px(p["year"], p["value"])
            if not (gx0 - 2 <= x <= gx1 + 2):
                continue
            age = (year_now - p["year"]) / max(reveal[1] - reveal[0], 1) * duration
            pop = ease_out(min(age / 0.35, 1.0))
            kind = p.get("kind", "record")
            if kind == "disputed":
                cv2.circle(f, (x, y), int(11 * pop), RED, 3, cv2.LINE_AA)
            elif kind == "oneway":
                cv2.circle(f, (x, y), int(10 * pop), WHITE, 2, cv2.LINE_AA)
            else:
                cv2.circle(f, (x, y), int(8 * pop), AMBER, -1, cv2.LINE_AA)
                cv2.circle(f, (x, y), int(3 * pop), (255, 245, 225), -1, cv2.LINE_AA)
            if focus and p.get("label") == focus:
                ph = (t * 1.4) % 1.0
                cv2.circle(f, (x, y), int(14 + 34 * ph), RED if kind == "disputed" else AMBER, 2, cv2.LINE_AA)
            if id(p) in labels:
                # label block (name over sub line) sits above the point by default; `pos: below` puts it under,
                # and the block flips to the left of the point near the right edge (or with `side: left`)
                la, lb = labels[id(p)]
                bw = max(la.rgb.shape[1], lb.rgb.shape[1] if lb else 0)
                left = p.get("side") == "left" or (p.get("side") != "right" and x > gx1 - bw - 20)
                lx = x - 4 - bw if left else x - 8
                sub_off = la.rgb.shape[0] - 12          # name layer carries a 12 px shadow margin
                hb = (sub_off + lb.rgb.shape[0]) if lb else la.rgb.shape[0] - 12
                top = y + 8 if p.get("pos") == "below" else y - 10 - hb
                a = min(age / 0.5, 1.0)
                la.x, la.y = lx, top
                la.draw(f, a)
                if lb:
                    lb.x, lb.y = lx + 14, top + sub_off
                    lb.draw(f, a * 0.9)
        f[:, :gx0 - 2] = axes[:, :gx0 - 2]
        f[gy1 + 2:] = axes[gy1 + 2:]
        if t_layer:
            t_layer.draw(f, fr.fade_window(t, 0.15, duration, 0.5))
        unit_l.draw(f, 0.9)
        if src:
            src.draw(f, 0.8)
        return f
    return render


def _nice_step(span: float, years: bool = False) -> float:
    target = span / (6 if years else 5)
    mag = 10 ** math.floor(math.log10(max(target, 1e-9)))
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= target:
            step = m * mag
            break
    if years:
        step = max(1, round(step))
    return step


def speed_beat(duration: float, start: float, end: float, unit: str = "km/h", label: str = "", sub: str = "",
               verdict: str = "", backdrop=None, decimals: int = 0):
    """A big speed readout counting up over a motion-blurred backdrop with streaking speed lines.
    `verdict` (e.g. "NOT VERIFIED") stamps in red over the number near the end."""
    if backdrop is not None:
        k = np.zeros((1, 61), np.float32)
        k[0, :] = 1 / 61
        bg = cv2.filter2D(backdrop, -1, k)
        bg = (bg.astype(np.float32) * 0.32).astype(np.uint8)
    else:
        bg = _backdrop(7)
    rng = np.random.default_rng(9)
    n = 70
    ly = rng.uniform(0.05, 0.95, n) * H
    lspeed = rng.uniform(0.6, 1.6, n)
    lphase = rng.uniform(0, 1, n)
    llen = rng.uniform(80, 340, n)
    unit_l = place(tracked(unit.upper(), "mono_medium", 40, DIM, 0.2), W // 2, H // 2 + 110, "mm")
    lab_l = place(tracked(label.upper(), "semibold", 34, TEXT, 0.24), W // 2, int(H * 0.22), "mm") if label else None
    sub_l = place(tracked(sub.upper(), "mono", 24, DIM, 0.2), W // 2, int(H * 0.27), "mm") if sub else None
    ver_l = tracked(verdict.upper(), "semibold", 64, RED, 0.18) if verdict else None
    count_end = duration * (0.62 if verdict else 0.8)

    def render(t):
        f = bg.copy()
        u = ease_out(min(t / count_end, 1.0))
        val = start + (end - start) * u
        vel = 1.0 - u * 0.6 if t < count_end else 0.25
        streak = np.zeros((H, W), np.float32)
        for i in range(n):
            x = ((lphase[i] - t * lspeed[i] * (1.2 + 2.5 * vel)) % 1.3 - 0.15) * W
            cv2.line(streak, (int(x), int(ly[i])), (int(x + llen[i] * (0.4 + vel)), int(ly[i])), 1.0, 1, cv2.LINE_AA)
        f = np.clip(f.astype(np.float32) + streak[..., None] * 90 * (0.3 + vel), 0, 255).astype(np.uint8)
        txt = f"{val:,.{decimals}f}"
        num = tracked(txt, "display", 210, AMBER if not (verdict and t > count_end) else (230, 200, 190), 0.02)
        place(num, W // 2, H // 2 - 10, "mm").draw(f, fr.fade_window(t, 0.1, duration, 0.4))
        unit_l.draw(f, fr.fade_window(t, 0.3, duration, 0.5))
        if lab_l:
            lab_l.draw(f, fr.fade_window(t, 0.2, duration, 0.5))
        if sub_l:
            sub_l.draw(f, fr.fade_window(t, 0.5, duration, 0.5))
        if ver_l is not None and t > count_end:
            k_ = ease_out(min((t - count_end) / 0.25, 1.0))
            s = 1.6 - 0.6 * k_
            img = cv2.resize(ver_l, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
            h_, w_ = img.shape[:2]
            side = int(math.hypot(w_, h_)) + 4      # rotate on a canvas big enough to keep the corners
            M = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), 6, 1.0)
            M[:, 2] += ((side - w_) / 2, (side - h_) / 2)
            img = cv2.warpAffine(img, M, (side, side))
            place(img, W // 2, H // 2 - 10, "mm").draw(f, k_)
        return f
    return render
