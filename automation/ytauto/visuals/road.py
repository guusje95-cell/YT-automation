"""Procedural driving shots for the car channel (no footage rights needed).

`road_beat`  low POV down an empty desert highway: perspective lane markings, reflector posts, mountain ridge,
             dusk or night sky; speed builds over the beat, optional speedometer readout.
`landmark_beat`  top-down illustration of timing a car between two road landmarks against the speed shown on screen.

Renderers follow the frames.py contract: `render(t) -> (H, W, 3) uint8` for t in [0, duration).
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from ytauto.visuals import frames as fr
from ytauto.visuals.editorial import AMBER, DIM, RED, place, tracked
from ytauto.visuals.frames import H, TEXT, W, ease, ease_out

SKIES = {   # zenith, horizon, horizon glow, ground near, ground far
    "dusk": ((22, 26, 48), (238, 132, 70), (255, 190, 120), (58, 44, 36), (120, 86, 66)),
    "night": ((4, 6, 14), (30, 34, 60), (70, 60, 90), (14, 13, 16), (28, 26, 32)),
    "day": ((70, 120, 190), (200, 214, 226), (235, 235, 230), (150, 120, 92), (196, 170, 140)),
}


def _ridge(seed: int, n: int = W) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, n)
    y = np.zeros(n)
    for k, amp in ((3, 0.55), (7, 0.25), (17, 0.12), (41, 0.06)):
        y += amp * np.sin(2 * np.pi * (k * x + rng.random()))
    return (y - y.min()) / (y.max() - y.min() + 1e-9)


def road_beat(duration: float, sky: str = "dusk", speed=(0.6, 1.0), hud=None, label: str = "", heat: bool = True,
              seed: int = 3):
    """`speed` is the visual speed multiplier at start/end; `hud` = {"from": 0, "to": 400, "unit": "km/h"}
    draws a speedometer readout counting over the beat."""
    zen, hor, glow, g_near, g_far = (np.array(c, np.float32) for c in SKIES[sky])
    hy = int(H * 0.47)                       # horizon line
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    # sky
    u = np.clip(yy[:hy] / hy, 0, 1)
    sky_img = zen * (1 - u[..., None] ** 1.6) + hor * (u[..., None] ** 1.6)
    sun = np.exp(-(((xx - W * 0.58) / (W * 0.30)) ** 2) - (((yy[:hy] - hy) / (H * 0.10)) ** 2))
    sky_img = sky_img + glow * 0.45 * sun[..., None]
    if sky == "night":
        rng = np.random.default_rng(seed)
        for _ in range(500):
            x, y = int(rng.integers(0, W)), int(rng.integers(0, int(hy * 0.85)))
            sky_img[y, x] += rng.uniform(40, 160)
    # mountains
    far = _ridge(seed) * H * 0.07 + H * 0.012
    near = _ridge(seed + 7) * H * 0.045
    sky_rgb = np.clip(sky_img, 0, 255)
    mtn_far = hor * 0.45 + zen * 0.25
    mtn_near = zen * 0.6 + g_far * 0.15
    for col_h, colr in ((far, mtn_far), (near, mtn_near)):
        top = (hy - col_h).astype(int)
        mask = yy[:hy] >= top[None, :]
        sky_rgb = np.where(mask[..., None], colr, sky_rgb)
    # ground perspective tables
    ry = np.arange(hy + 1, H, dtype=np.float32)
    depth = 1.0 / (ry - hy)                                   # proportional to distance
    dn = depth / depth.max()
    g_rows = g_far * (1 - (1 - dn[:, None]) ** 0.5) + g_near * ((1 - dn[:, None]) ** 0.5)
    g_rows = g_rows * 0.85
    rng = np.random.default_rng(seed + 1)
    grain_tile = rng.normal(0, 1, (256, W)).astype(np.float32)
    road_half = 0.55                                           # half width of the road (lateral units)
    xw = (xx - W / 2) * depth[:, None]                         # lateral position per pixel
    near = np.clip((ry - hy) / (H - hy) * 6, 0, 1)[:, None, None]   # fades markings out toward the horizon
    lane = np.abs(xw)
    road_mask = lane < road_half * 1.0
    centre = lane < 0.012
    edge = (np.abs(lane - road_half * 0.94) < 0.012)
    asphalt = np.array([46, 46, 50], np.float32) if sky != "day" else np.array([88, 86, 86], np.float32)
    posts_x = road_half * 1.25
    unit_l = place(tracked(hud.get("unit", "km/h").upper(), "mono_medium", 26, DIM, 0.2), W - 150, H - 70, "mm") \
        if hud else None
    lab_l = place(tracked(label.upper(), "mono", 22, DIM, 0.25), 90, H - 60, "lm") if label else None
    total_dist = [0.0]
    last_t = [0.0]

    def render(t):
        u_ = t / duration
        v = speed[0] + (speed[1] - speed[0]) * ease(u_)
        # integrate distance so speed changes never jump the markings
        dt = max(t - last_t[0], 0) if t >= last_t[0] else 0
        if t < last_t[0]:
            total_dist[0] = 0.0
            dt = t
        total_dist[0] += dt * v * 60.0
        last_t[0] = t
        s = total_dist[0]
        f = np.empty((H, W, 3), np.float32)
        f[:hy] = sky_rgb
        f[hy] = hor * 0.9
        zrow = depth[:, None] * 2000.0                        # distance down the road per row
        phase = (zrow + s) % 3.0
        dash = (phase < 1.4) & centre
        gshift = int(s * 6) % 256
        grain = np.take(grain_tile, (np.arange(len(ry)) + gshift) % 256, axis=0)
        ground = g_rows[:, None, :] + grain[..., None] * 5 * (1 - dn[:, None, None])
        rd = asphalt + grain[..., None] * 3.5
        img = np.where(road_mask[..., None], rd, ground)
        img = np.where(dash[..., None], img * (1 - near) + np.array([236, 196, 80], np.float32) * near, img)
        img = np.where(edge[..., None], img * (1 - near * 0.9) + np.array([220, 220, 216], np.float32) * near * 0.9,
                       img)
        # reflector posts every 8 units on both sides
        posts = ((zrow + s) % 8.0 < 0.3) & (np.abs(lane - posts_x) < 0.035)
        img = np.where(posts[..., None], img * (1 - near) + np.array([250, 240, 230], np.float32) * near, img)
        f[hy + 1:] = img
        if heat and sky != "night":   # heat shimmer just above the road at the horizon
            shift = (np.sin(np.arange(32) * 0.9 + t * 9) * 2.0).astype(int)
            for i, sh in enumerate(shift):
                f[hy - 10 + i] = np.roll(f[hy - 10 + i], sh, axis=0)
        out = np.clip(f, 0, 255).astype(np.uint8)
        # speed blur on the lower part grows with speed
        k = int(3 + 10 * (v - 0.5))
        if k > 3:
            lower = out[hy + int(H * 0.18):]
            out[hy + int(H * 0.18):] = cv2.blur(lower, (1, k))
        out = fr.apply_vignette(out)
        if hud:
            val = hud.get("from", 0) + (hud["to"] - hud.get("from", 0)) * ease_out(min(u_ / 0.9, 1))
            num = tracked(f"{val:,.0f}", "display", 96, AMBER, 0.02)
            place(num, W - 150, H - 120, "mb").draw(out, fr.fade_window(t, 0.2, duration, 0.4))
            unit_l.draw(out, fr.fade_window(t, 0.3, duration, 0.4))
        if lab_l:
            lab_l.draw(out, fr.fade_window(t, 0.4, duration, 0.5))
        return out
    return render


def landmark_beat(duration: float, claimed: str = "533 km/h on screen", note: str = "Illustration",
                  title: str = "Distance ÷ time = real speed"):
    """Top-down road: two landmarks, a 'claimed speed' ghost racing ahead and the car the video actually shows,
    with a stopwatch between the landmarks."""
    bg = np.zeros((H, W, 3), np.uint8)
    bg[:] = (20, 20, 22)
    ry0, ry1 = int(H * 0.44), int(H * 0.62)
    cv2.rectangle(bg, (0, ry0), (W, ry1), (52, 52, 56), -1)
    for x in range(0, W, 120):
        cv2.line(bg, (x, (ry0 + ry1) // 2), (x + 60, (ry0 + ry1) // 2), (220, 186, 80), 4)
    cv2.line(bg, (0, ry0 + 6), (W, ry0 + 6), (210, 210, 205), 3)
    cv2.line(bg, (0, ry1 - 6), (W, ry1 - 6), (210, 210, 205), 3)
    lx0, lx1 = int(W * 0.22), int(W * 0.78)
    for x, name in ((lx0, "LANDMARK A"), (lx1, "LANDMARK B")):
        cv2.line(bg, (x, ry0 - 70), (x, ry1 + 70), (200, 200, 210), 2, cv2.LINE_AA)
        place(tracked(name, "mono", 22, DIM, 0.2), x, ry0 - 95, "mm").draw(bg, 0.95)
    title_l = place(tracked(title.upper(), "semibold", 34, TEXT, 0.2), W // 2, int(H * 0.14), "mm")
    ghost_l = place(tracked(claimed.upper(), "mono_medium", 24, RED, 0.15), 0, 0, "lm")
    car_l = place(tracked("WHAT THE VIDEO SHOWS", "mono_medium", 24, AMBER, 0.15), 0, 0, "lm")
    note_l = fr.text_layer(note, "regular", 22, DIM, W - 36, H - 30, anchor="rb")

    def car(f, x, y, col, filled=True):
        pts = np.array([[x - 46, y - 18], [x + 30, y - 18], [x + 50, y], [x + 30, y + 18], [x - 46, y + 18]], np.int32)
        if filled:
            cv2.fillPoly(f, [pts], col, cv2.LINE_AA)
        else:
            cv2.polylines(f, [pts], True, col, 3, cv2.LINE_AA)

    def render(t):
        f = bg.copy()
        u = t / duration
        x_ghost = -80 + (W + 200) * ease(min(u / 0.45, 1))
        x_car = -80 + (W + 200) * ease(min(u / 0.95, 1))
        yg, yc = ry0 + 30, ry1 - 30
        car(f, int(x_ghost), yg, RED, filled=False)
        car(f, int(x_car), yc, AMBER)
        ghost_l.x, ghost_l.y = 40, ry0 - 40 - ghost_l.rgb.shape[0] // 2      # lane labels stay put
        car_l.x, car_l.y = 40, ry1 + 40 - car_l.rgb.shape[0] // 2
        ghost_l.draw(f, 0.95)
        car_l.draw(f, 0.95)
        # stopwatch: runs while the real car is between the landmarks
        t_in = min(max(x_car - lx0, 0) / (lx1 - lx0), 1.0)
        ang = -math.pi / 2 + 2 * math.pi * t_in * 1.6
        cx, cy, r = W // 2, int(H * 0.80), 62
        cv2.circle(f, (cx, cy), r, (210, 210, 215), 3, cv2.LINE_AA)
        cv2.line(f, (cx, cy), (int(cx + r * 0.85 * math.cos(ang)), int(cy + r * 0.85 * math.sin(ang))), AMBER, 4,
                 cv2.LINE_AA)
        cv2.rectangle(f, (cx - 10, cy - r - 18), (cx + 10, cy - r - 4), (210, 210, 215), -1)
        title_l.draw(f, fr.fade_window(t, 0.2, duration, 0.5))
        note_l.draw(f, 0.8)
        return f
    return render
