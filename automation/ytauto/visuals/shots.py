"""Cinematic shot presets built on render3d.

Each preset returns `render(t) -> uint8 frame` for t in [0, duration). Parameters come
from the spec beat (`type: r3d`, `shot: <name>`). All camera moves are eased.
Jupiter-centred scenes use radius 1.0 at the origin.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from ytauto.visuals import render3d as r3
from ytauto.visuals.frames import ease, ease_out, W, H


def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


BODY_PRESETS = {
    "jupiter": dict(tex="8k_jupiter.jpg", radius=1.0, tilt=math.radians(3.1), limb_dark=0.35, wrap=0.18,
                    falloff=1.45, atmosphere=(0.34, 0.26, 0.18), atmo_height=0.02, atmo_strength=0.8,
                    detail_tex="detail_barge.jpg", detail_scale=90.0, detail_strength=1.2),
    "earth": dict(tex="8k_earth_daymap.jpg", radius=1.0, tilt=math.radians(23.4), gain=1.6, falloff=1.1,
                  night_tex="8k_earth_nightmap.jpg", clouds_tex="8k_earth_clouds.jpg",
                  atmosphere=(0.25, 0.45, 1.0), atmo_height=0.03, atmo_strength=1.3),
    "saturn": dict(tex="8k_saturn.jpg", radius=1.0, tilt=math.radians(26.7), limb_dark=0.3, wrap=0.12,
                   falloff=1.4, rings={"tex": "8k_saturn_ring_alpha.png", "inner": 1.24, "outer": 2.27, "gain": 1.2}),
    "moon": dict(tex="8k_moon.jpg", radius=1.0, falloff=1.2),
    "mars": dict(tex="8k_mars.jpg", radius=1.0, falloff=1.2, atmosphere=(0.6, 0.35, 0.2), atmo_height=0.015,
                 atmo_strength=0.4),
}

# relative radii (Jupiter = 1)
REL_RADIUS = {"jupiter": 1.0, "earth": 6371.0 / 69911.0, "saturn": 58232.0 / 69911.0}


def body(name: str, **over) -> r3.Body:
    cfg = dict(BODY_PRESETS[name])
    cfg.update(over)
    return r3.Body(**cfg)


def _cam_orbit(dist, az, el, target=(0, 0, 0), fov=40, roll=0.0):
    x = dist * math.cos(el) * math.sin(az)
    y = dist * math.sin(el)
    z = dist * math.cos(el) * math.cos(az)
    tx, ty, tz = target
    return r3.Camera(pos=(x + tx, y + ty, z + tz), target=target, fov=fov, roll=roll)


def sun_rel(cam: r3.Camera, yaw_deg: float, pitch_deg: float = 15.0):
    """Sun direction defined relative to the camera view: yaw 0 = behind the camera (front-lit),
    90 = from the right (side-lit), 180 = behind the subject (back-lit crescent)."""
    pos = np.array(cam.pos, np.float32)
    fwd = pos - np.array(cam.target, np.float32)
    fwd /= np.linalg.norm(fwd)
    right = np.cross(np.array(cam.up, np.float32), fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    y, p_ = math.radians(yaw_deg), math.radians(pitch_deg)
    v = fwd * math.cos(y) * math.cos(p_) + right * math.sin(y) * math.cos(p_) + up * math.sin(p_)
    return tuple(float(x) for x in v)


def surface_cam(lon_deg: float, lat_deg: float, alt: float, heading_deg: float, pitch_deg: float, fov=60.0,
                roll=0.0):
    """Camera hovering `alt` (planet radii) above a surface point, looking along `heading`
    (0 = east) and `pitch` degrees below the local horizon; 'up' is the local vertical."""
    lo, la = math.radians(lon_deg), math.radians(lat_deg)
    n = np.array([math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)], np.float32)
    east = np.array([math.cos(lo), 0.0, -math.sin(lo)], np.float32)
    north = np.cross(n, east)
    h, p_ = math.radians(heading_deg), math.radians(pitch_deg)
    tang = east * math.cos(h) + north * math.sin(h)
    fwd = tang * math.cos(p_) - n * math.sin(p_)
    pos = n * (1.0 + alt)
    return r3.Camera(pos=tuple(pos), target=tuple(pos + fwd), up=tuple(n), fov=fov, roll=roll)


def _post(frame, t, bloom=0.3, grain=3.0):
    if bloom:
        frame = r3.bloom(frame, bloom)
    if grain:
        frame = r3.film_grain(frame, grain, seed=int(t * 1000) % 100000)
    return frame


# ----------------------------------------------------------------- presets
def orbit(duration, planet="jupiter", dist=(3.2, 2.8), az=(0.2, -0.15), el=(0.15, 0.1), fov=(38, 36),
          spin=(0.0, 0.25), light=(60, 15), target=(0, 0, 0), bg_rot=0.0, streak=False, **_):
    """light = (yaw, pitch) relative to the camera at the start of the shot (60 = dramatic side light).
    `streak` draws the probe as a glowing point falling toward the planet across the shot."""
    b = body(planet)
    sun = sun_rel(_cam_orbit(dist[0], az[0], el[0], target, fov[0]), *light)

    def render(t):
        u = _smooth(t / duration)
        mix = lambda p: p[0] + (p[1] - p[0]) * u
        b.spin = mix(spin)
        cam = _cam_orbit(mix(dist), mix(az), mix(el), target, mix(fov))
        f = r3.render(r3.Scene(bodies=[b], sun_dir=sun, bg_rotation=bg_rot), cam, W, H)
        if streak:
            pos = np.array(cam.pos, np.float32)
            n_ = pos / np.linalg.norm(pos)
            left = np.cross(n_, np.array([0, 1, 0], np.float32))
            left /= np.linalg.norm(left)
            hit = n_ * 0.55 - left * 0.8 + np.array([0, 0.18, 0], np.float32)
            hit = hit / np.linalg.norm(hit) * 1.02
            pe = r3.project(cam, tuple(hit), W, H)
            if pe:
                e = (pe[0] / W, pe[1] / H)
                st = (e[0] - 0.42, e[1] - 0.30)
                k = min(t / duration / 0.85, 1.0)
                f = _probe_streak(f, k, start=st, end=e)
        return _post(f, t)
    return render


def crescent(duration, planet="jupiter", dist=(3.0, 2.6), az=(0.3, 0.15), el=(0.05, 0.08), fov=(40, 38), **kw):
    """Back-lit view: the sun is behind the planet, leaving a thin lit crescent and glowing limb."""
    kw.setdefault("light", (118, 12))
    return orbit(duration, planet, dist, az, el, fov, **kw)


def scale_compare(duration, big="jupiter", small="earth", **_):
    """Earth beside Jupiter at TRUE relative size: both centres lie in the same plane facing the
    camera, so perspective does not distort the comparison. Camera pulls back from Earth to reveal Jupiter."""
    jb = body(big)
    er = REL_RADIUS[small]
    eb = body(small, radius=er, center=(1.35, 0.0, 0.0))
    sun = (-0.55, 0.25, 0.8)

    def render(t):
        u = _smooth(t / duration)
        jb.spin = 0.4 + 0.08 * u
        eb.spin = 1.5 + 0.3 * u
        # start framed on Earth, end with both in frame (camera on +z, looking along -z)
        cx = 1.35 * (1 - u) + 0.62 * u
        dist = 0.55 * (1 - u) + 3.6 * u
        cam = r3.Camera(pos=(cx, 0.05, dist), target=(cx, 0.0, 0.0), fov=40)
        f = r3.render(r3.Scene(bodies=[jb, eb], sun_dir=sun), cam, W, H)
        return _post(f, t)
    return render


def approach(duration, planet="jupiter", dist=(9.0, 2.2), az=(0.5, 0.1), el=(0.25, 0.08), fov=(30, 42),
             light=(55, 15), **_):
    return orbit(duration, planet, dist, az, el, fov, spin=(0.3, 0.45), light=light)


def starfield(duration, rot=(0.0, 0.06), fov=50, look=(0.3, 0.1, -1.0), streak=False, **_):
    """Deep space; optional probe streak (bright head + plasma trail) crossing the frame."""
    def render(t):
        u = t / duration
        sc = r3.Scene(bodies=[], sun_dir=(0.0, -1.0, 0.0), bg_rotation=rot[0] + (rot[1] - rot[0]) * u,
                      sun_visible_glow=False, bg_gain=0.45)
        cam = r3.Camera(pos=(0, 0, 0), target=look, fov=fov)
        f = r3.render(sc, cam, W, H)
        if streak:
            f = _probe_streak(f, u)
        return _post(f, t, bloom=0.25)
    return render


def _probe_streak(f, u, start=(0.15, 0.25), end=(0.75, 0.62), hot=True):
    """A meteor-like point: white-hot head, tapered orange trail that fades toward the tail."""
    x0, y0 = start[0] * W, start[1] * H
    x1, y1 = end[0] * W, end[1] * H
    hx, hy = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
    layer = np.zeros((H, W, 3), np.float32)
    n = 24
    tail = 0.18
    for k in range(n):
        a0, a1 = k / n, (k + 1) / n
        p0 = (hx - (x1 - x0) * tail * (1 - a0), hy - (y1 - y0) * tail * (1 - a0))
        p1 = (hx - (x1 - x0) * tail * (1 - a1), hy - (y1 - y0) * tail * (1 - a1))
        w = a1 ** 1.5
        col = (255 * w, (110 + 120 * w) * w, (40 + 160 * w ** 3) * w)
        cv2.line(layer, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), col, max(1, int(1 + 2 * w)), cv2.LINE_AA)
    glow = cv2.GaussianBlur(layer, (0, 0), 5) * 1.5
    cv2.circle(layer, (int(hx), int(hy)), 3, (255, 250, 240), -1, cv2.LINE_AA)
    head = np.zeros((H, W), np.float32)
    cv2.circle(head, (int(hx), int(hy)), 2, 1.0, -1, cv2.LINE_AA)
    head = cv2.GaussianBlur(head, (0, 0), 9) * 60
    layer += glow + head[..., None] * np.array([1.0, 0.75, 0.45], np.float32) * 255
    return np.clip(f.astype(np.float32) + layer, 0, 255).astype(np.uint8)


def entry(duration, plasma=True, lon=10.0, lat=8.0, sustain=False, **_):
    """Diving at the equatorial cloud tops: the curved horizon flattens and rushes up, plasma at the edges."""
    b = body("jupiter", spin=0.0)
    rng = np.random.default_rng(3)

    def render(t):
        u = _smooth(t / duration)
        alt = 0.8 * (1 - u) ** 1.7 + 0.10     # stop well above the cloud tops: the 4K map blurs when closer
        pitch = 62 * (1 - u) + 14 * u
        jitter = rng.normal(0, 0.25 * (0.2 + u), 2) if plasma else (0, 0)
        cam = surface_cam(lon - 6 * u, lat, alt, heading_deg=180, pitch_deg=pitch + jitter[0], fov=58 + 12 * u,
                          roll=math.radians(jitter[1] + 2.5 * math.sin(t * 2.1) * u))
        sun = sun_rel(cam, 35, 35)
        f = r3.render(r3.Scene(bodies=[b], sun_dir=sun), cam, W, H)
        if plasma:
            glow = (1.0 - 0.55 * (t / duration) if sustain     # continuing deceleration: start hot
                    else math.sin(min(1.0, (t / duration) * 1.2) * math.pi) ** 2)
            f = _plasma(f, glow, t)
        return _post(f, t, bloom=0.45)
    return render


def _plasma(f, amount, t):
    if amount <= 0.01:
        return f
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.55) / H) ** 2)
    edge = np.clip((r - 0.28) * 2.4, 0, 1) ** 2
    flicker = 0.85 + 0.15 * math.sin(t * 37) * math.sin(t * 13)
    col = np.array([255, 120, 40], np.float32)
    g = (edge * amount * flicker)[..., None] * col * 1.2
    streaks = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(int(t * 30))
    for _ in range(int(40 * amount)):
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(0.25, 0.5) * W
        x0, y0 = W / 2 + r0 * math.cos(a), H * 0.55 + r0 * math.sin(a)
        x1, y1 = W / 2 + (r0 + rng.uniform(80, 260)) * math.cos(a), H * 0.55 + (r0 + rng.uniform(80, 260)) * math.sin(a)
        cv2.line(streaks, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, 2, cv2.LINE_AA)
    streaks = cv2.GaussianBlur(streaks, (0, 0), 2)
    g += streaks[..., None] * np.array([255, 200, 140], np.float32) * amount
    return np.clip(f.astype(np.float32) + g * 0.8, 0, 255).astype(np.uint8)


def flyover(duration, alt=(0.05, 0.03), lon=(20.0, 8.0), lat=(-18.0, -20.0), heading=(175.0, 182.0),
            pitch=(14.0, 10.0), light=(30, 12), **_):
    """Skimming above the cloud tops toward a curved horizon (wide, cinematic); default passes the
    Great Red Spot latitude band."""
    b = body("jupiter", spin=0.0)

    def render(t):
        u = _smooth(t / duration)
        mix = lambda p: p[0] + (p[1] - p[0]) * u
        cam = surface_cam(mix(lon), mix(lat), mix(alt), mix(heading), mix(pitch), fov=64)
        f = r3.render(r3.Scene(bodies=[b], sun_dir=sun_rel(cam, *light)), cam, W, H)
        return _post(f, t, bloom=0.35)
    return render


JUPITER_LAYERS = [
    # (outer radius fraction, outer colour, inner colour) — schematic palette
    (1.00, (0.85, 0.66, 0.44), (0.62, 0.44, 0.30)),   # molecular hydrogen atmosphere / fluid
    (0.80, (0.36, 0.42, 0.70), (0.28, 0.33, 0.62)),   # liquid metallic hydrogen
    (0.55, (0.95, 0.60, 0.28), (1.00, 0.86, 0.58)),   # dilute ("fuzzy") core region
]


def cutaway(duration, layers=None, marker=None, az=(0.25, 0.05), el=(0.32, 0.28), dist=(3.0, 2.7), fov=(38, 36),
            sun=(-0.45, 0.6, 0.65), fuzzy=True, target=(0, -0.05, 0), **_):
    """Rotating cutaway; optional `marker` = (r_from, r_to) draws a falling dot at that radius.
    `target` moves the look-at point (e.g. toward the rim to show thin outer layers close up)."""
    layers = layers or JUPITER_LAYERS
    facing = math.degrees((az[0] + az[1]) / 2)
    b = body("jupiter", cutaway={"layers": layers, "wedge": 100, "facing": facing})

    def render(t):
        u = _smooth(t / duration)
        mix = lambda p: p[0] + (p[1] - p[0]) * u
        b.spin = 0.0
        tg = tuple(target[0]) if isinstance(target[0], (list, tuple)) else tuple(target)
        if isinstance(target[0], (list, tuple)):
            tg = tuple(a + (b_ - a) * u for a, b_ in zip(target[0], target[1]))
        cam = _cam_orbit(mix(dist), mix(az), mix(el), tg, mix(fov))
        f = r3.render(r3.Scene(bodies=[b], sun_dir=sun), cam, W, H)
        if fuzzy:  # soften the core boundary into a glow
            f = _core_glow(f, cam, layers[-1][0])
        if marker:
            rr = marker[0] + (marker[1] - marker[0]) * u
            # marker on the cut face, along the wedge bisector, slightly above the equator
            fa = math.radians(facing + 50)   # on one cut face
            p3 = (rr * math.sin(fa) * 0.98, rr * 0.08, rr * math.cos(fa) * 0.98)
            p = r3.project(cam, p3, W, H)
            if p:
                f = _marker(f, p)
        return _post(f, t, bloom=0.3)
    return render


def _core_glow(f, cam, core_r):
    p = r3.project(cam, (0, 0, 0), W, H)
    if not p:
        return f
    edge = r3.project(cam, (core_r * 0.7071, 0, core_r * 0.7071), W, H)
    rad = math.hypot(edge[0] - p[0], edge[1] - p[1]) if edge else 200
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - p[0]) ** 2 + (yy - p[1]) ** 2) / max(rad, 1)
    g = np.exp(-d ** 2 * 2.2) * 70
    return np.clip(f.astype(np.float32) + g[..., None] * np.array([1.0, 0.75, 0.4], np.float32), 0, 255).astype(np.uint8)


def _marker(f, p):
    f = f.copy()
    x, y = int(p[0]), int(p[1])
    cv2.circle(f, (x, y), 22, (255, 176, 59), 2, cv2.LINE_AA)
    cv2.circle(f, (x, y), 7, (255, 240, 220), -1, cv2.LINE_AA)
    return f


def polar_orbit(duration, sun=(0.35, 0.3, 0.9), **_):
    """Jupiter with Juno's elongated polar orbit drawn in 3D and a spacecraft dot moving along it."""
    b = body("jupiter")
    # ellipse in the y-z plane: perijove just above the north pole region, apojove far out
    ts = np.linspace(0, 2 * math.pi, 400)
    a_, e_ = 3.2, 0.82
    rr = a_ * (1 - e_ ** 2) / (1 + e_ * np.cos(ts))
    pts = np.stack([np.zeros_like(ts), rr * np.sin(ts + 0.4), rr * np.cos(ts + 0.4) * -1], -1)

    def render(t):
        u = _smooth(t / duration)
        b.spin = 0.2 + 0.4 * u
        cam = _cam_orbit(6.5 - 1.0 * u, 0.9 - 0.2 * u, 0.25, (0, 0.6, 0), 44)
        f = r3.render(r3.Scene(bodies=[b], sun_dir=sun), cam, W, H).astype(np.float32)
        proj = [r3.project(cam, p, W, H) for p in pts]
        line = np.zeros_like(f)
        for p, q, P in zip(proj, proj[1:], pts):
            if p and q:
                behind = np.dot(P, np.array(cam.pos) / np.linalg.norm(cam.pos)) < 0 and np.linalg.norm(P[:2]) < 1
                col = (90, 140, 255) if not behind else (40, 60, 110)
                cv2.line(line, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), col, 2, cv2.LINE_AA)
        k = int((t / duration * 0.9 + 0.55) % 1.0 * len(pts))
        pd = proj[k]
        if pd:
            cv2.circle(line, (int(pd[0]), int(pd[1])), 8, (255, 240, 220), -1, cv2.LINE_AA)
        f = np.clip(f + cv2.GaussianBlur(line, (0, 0), 3) * 1.2 + line, 0, 255).astype(np.uint8)
        return _post(f, t)
    return render


def collision(duration, sun=(-0.8, 0.35, 0.5), **_):
    """Hypothesis visual: a proto-planet ~ (10 Earth masses) falls into young Jupiter; flash on contact."""
    b = body("jupiter")
    imp = body("mars", radius=0.22, center=(3.5, 0.9, 1.0))

    def render(t):
        u = t / duration
        k = min(u / 0.7, 1.0)
        kk = k * k
        imp.center = (3.5 * (1 - kk) + 0.7 * kk, 0.9 * (1 - kk) + 0.25 * kk, 1.0 * (1 - kk) + 0.6 * kk)
        bodies = [b] + ([imp] if k < 1 else [])
        cam = _cam_orbit(3.6, 0.55, 0.12, (0.6, 0.15, 0.2), 44)
        f = r3.render(r3.Scene(bodies=bodies, sun_dir=sun), cam, W, H).astype(np.float32)
        if u > 0.68:
            fl = math.exp(-(u - 0.7) * 9) if u >= 0.7 else (u - 0.68) / 0.02
            p = r3.project(cam, (0.75, 0.22, 0.6), W, H)
            if p:
                yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                d = np.sqrt((xx - p[0]) ** 2 + (yy - p[1]) ** 2)
                f += (np.exp(-d / 90) * 255 + np.exp(-d / 400) * 120)[..., None] * fl * np.array([1, 0.85, 0.6])
                f += 255 * fl * 0.35
        return _post(np.clip(f, 0, 255).astype(np.uint8), t, bloom=0.4)
    return render


PRESETS = {"orbit": orbit, "crescent": crescent, "scale_compare": scale_compare, "approach": approach,
           "starfield": starfield, "entry": entry, "flyover": flyover, "cutaway": cutaway,
           "polar_orbit": polar_orbit, "collision": collision}


def make(shot: str, duration: float, **params):
    return PRESETS[shot](duration, **params)


# ----------------------------------------------------------------- 2.5D cloud dive (real JunoCam imagery)
DIVE_LAYERS = [  # (file, crop fractions x0, y0, x1, y1) — corner-free regions of CC BY JunoCam images
    ("detail_swift.jpg", (0.0, 0.0, 0.8, 0.75)),
    ("dive_tkachenko.jpg", (0.0, 0.0, 1.0, 0.75)),
    ("detail_barge.jpg", (0.45, 0.0, 1.0, 0.45)),
    ("dive_oval.jpg", (0.0, 0.05, 1.0, 0.95)),
    ("detail_barge.jpg", (0.0, 0.45, 0.45, 1.0)),
]


def _load_layer(name, crop, width=2600):
    import cv2 as _cv
    t = r3.texture(name, 8192)[..., :3]
    h, w = t.shape[:2]
    x0, y0, x1, y1 = crop
    t = t[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    sc = width / t.shape[1]
    t = _cv.resize(t, (width, int(t.shape[0] * sc)), interpolation=_cv.INTER_AREA)
    if t.shape[0] < 1500:  # make tall enough to cover 16:9 when zoomed
        t = _cv.resize(t, (int(width * 1500 / t.shape[0]), 1500), interpolation=_cv.INTER_CUBIC)
    lum = t.mean(-1)
    alpha = np.clip((lum - 0.30) / 0.30, 0, 1) ** 1.2    # bright cloud tops opaque, dark gaps see-through
    return (t * 255).astype(np.uint8), alpha.astype(np.float32)


def _fractal_noise(size: int, seed: int, octaves: int = 6, persistence: float = 0.55) -> np.ndarray:
    """Seamless-ish fractal value noise in 0..1 (cv2 upscaling of random grids)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 4 * 2 ** o
        g = rng.random((cells + 1, cells + 1)).astype(np.float32)
        g[-1, :], g[:, -1] = g[0, :], g[:, 0]
        up = cv2.resize(g, (size, size), interpolation=cv2.INTER_CUBIC)
        out += up * amp
        total += amp
        amp *= persistence
    out /= total
    return (out - out.min()) / (out.max() - out.min())


_NOISE_CACHE: dict = {}


def _mist(seed: int, size: int = 1536) -> np.ndarray:
    if seed not in _NOISE_CACHE:
        n = _fractal_noise(size, seed)
        _NOISE_CACHE[seed] = np.clip((n - 0.42) / 0.38, 0, 1) ** 1.6
    return _NOISE_CACHE[seed]


def _flashes(rng, duration, lightning):
    flashes = sorted(rng.uniform(0.15, 0.92, max(int(lightning * duration / 2.2), 1 if lightning else 0)) * duration)
    return flashes, [(rng.uniform(0.25, 0.75) * W, rng.uniform(0.3, 0.7) * H) for _ in flashes]


def lightning_times(duration, lightning=0.0, seed=7, **_):
    """Flash times (s) a cloud_dive shot will show; the sound design syncs thunder to these."""
    return _flashes(np.random.default_rng(seed), duration, lightning)[0]


def cloud_dive(duration, layers=None, decks: int = 2, depth_tint=((1.0, 0.97, 0.92), (0.78, 0.58, 0.42)),
               lightning=0.0, hail=0.0, seed=7, mist_color=(235, 220, 200), **_):
    """Falling through the clouds: real JunoCam backdrops with a slow push-in, procedural mist
    layers rushing past the camera, a mist 'whiteout' at each cloud deck that hides the cut to the
    next (deeper, darker) backdrop, optional lightning inside the mist and falling hail streaks."""
    specs = (layers or DIVE_LAYERS)[: decks + 1]
    backs = [_load_layer(nm, cr)[0] for nm, cr in specs]
    nb = len(backs)
    rng = np.random.default_rng(seed)
    mists = [_mist(seed * 10 + k) for k in range(4)]
    flashes, flash_pos = _flashes(rng, duration, lightning)
    hail_pts = rng.uniform(0, 1, (int(260 * hail), 3))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def backdrop(k, local_u):
        img = backs[k]
        ih, iw = img.shape[:2]
        cover = max(W / iw, H / ih)
        sc = cover * (1.05 + 0.35 * local_u)
        M = cv2.getRotationMatrix2D((iw / 2, ih / 2), 4 * (local_u - 0.5) * (1 if k % 2 else -1), sc)
        M[0, 2] += W / 2 - iw / 2
        M[1, 2] += H / 2 - ih / 2
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)

    def render(t):
        u = t / duration
        seg = min(u * nb, nb - 1e-6)
        k = int(seg)
        lu = seg - k
        depth_frac = u
        tint = np.array(depth_tint[0], np.float32) * (1 - depth_frac) + np.array(depth_tint[1], np.float32) * depth_frac
        light = 1.0 - 0.38 * depth_frac
        frame = backdrop(k, lu) * tint * light
        # mist layers: each grows (moves toward the camera) and wraps; denser near deck crossings
        deck = 0.0
        for j in range(1, nb):
            deck = max(deck, math.exp(-((u - j / nb) / 0.045) ** 2))
        mcol = np.array(mist_color, np.float32) * (1 - 0.35 * depth_frac)
        for m_i, mist in enumerate(mists):
            phase = (t * (0.18 + 0.07 * m_i) + m_i * 0.27) % 1.0
            scale = 1.0 + phase * 2.5
            alpha_ph = math.sin(phase * math.pi)          # fade in when far, out as it passes
            ms = mist.shape[0]
            M = cv2.getRotationMatrix2D((ms / 2, ms / 2), m_i * 37 + t * 3, scale * max(W, H) / ms * 1.2)
            M[0, 2] += W / 2 - ms / 2
            M[1, 2] += H / 2 - ms / 2
            a = cv2.warpAffine(mist, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            a = a * (0.18 * alpha_ph + 0.65 * deck)
            frame = frame * (1 - a[..., None]) + mcol * a[..., None]
        # lightning glows inside the mist
        for ft, (fx, fy) in zip(flashes, flash_pos):
            dt = t - ft
            if 0 <= dt < 0.5:
                pulse = math.exp(-dt * 13) + 0.7 * math.exp(-max(dt - 0.13, 0) * 16) * (dt > 0.13)
                d = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2)
                glow = (np.exp(-d / 320) * 210 + 35) * pulse
                frame = frame + glow[..., None] * np.array([0.78, 0.87, 1.0], np.float32)
        if hail:
            for idx, (hx, hy, hz) in enumerate(hail_pts):
                yv = ((hy + t * (0.9 + hz) * 1.3) % 1.0) * H
                xv = hx * W + math.sin(t * 2 + idx) * 5
                ln = 20 + 50 * hz
                cv2.line(frame, (int(xv), int(yv - ln)), (int(xv - 4), int(yv)), (225, 215, 200), 1 + int(hz * 2),
                         cv2.LINE_AA)
        # grade: local-contrast + saturation so the JunoCam cloud structure reads through the haze
        lum = frame.mean(-1, keepdims=True)
        frame = lum + (frame - lum) * 1.35
        m = lum.mean()
        frame = m + (frame - m) * 1.25
        f = np.clip(frame, 0, 255).astype(np.uint8)
        return _post(f, t, bloom=0.3, grain=4.0)
    return render


PRESETS["cloud_dive"] = cloud_dive


# ----------------------------------------------------------------- deep interior (schematic, procedural)
FLUID_MODES = {
    # base colour (dark), glow colour (bright), particle colour, filament colour or None
    "liquid": ((26, 14, 8), (190, 105, 45), (255, 190, 120), None),
    "metallic": ((6, 9, 22), (70, 110, 210), (190, 215, 255), (150, 200, 255)),
}


def fluid(duration, mode="liquid", darker=False, seed=5, rain=0.0, **_):
    """Sinking through Jupiter's interior: dense, glowing, slowly churning fluid (domain-warped
    fractal noise), out-of-focus particles streaking upward as we sink. `metallic` adds flickering
    current filaments and a sheen to suggest an electrically conducting liquid. Schematic, not a measurement."""
    base, glow, pcol, fil = FLUID_MODES[mode]
    dim = 0.55 if darker else 1.0
    lw, lh = W // 2, H // 2
    n1 = cv2.resize(_fractal_noise(1024, seed, 6, 0.6), (lw * 2, lh * 2))
    n2 = cv2.resize(_fractal_noise(1024, seed + 1, 5, 0.55), (lw * 2, lh * 2))
    n3 = cv2.resize(_fractal_noise(512, seed + 2, 4, 0.5), (lw * 2, lh * 2))
    n4 = cv2.resize(_fractal_noise(1024, seed + 3, 7, 0.62), (lw * 2, lh * 2))
    yy, xx = np.mgrid[0:lh, 0:lw].astype(np.float32)
    rng = np.random.default_rng(seed)
    parts = rng.uniform(0, 1, (140, 3))
    rain_pts = rng.uniform(0, 1, (int(220 * rain), 3))
    base_a, glow_a = np.array(base, np.float32), np.array(glow, np.float32)
    heat = np.clip(0.35 + 0.65 * (yy / lh) ** 1.3, 0, 1)   # glow rising from the deep (bottom of frame)
    refl = cv2.BORDER_REFLECT

    def render(t):
        ox = 0.06 * lw * math.sin(t * 0.11)
        oy = 40 + t * 22.0                       # pattern scrolls up as the camera sinks
        wx = (cv2.remap(n2, xx + ox, yy + oy * 0.5, cv2.INTER_LINEAR, borderMode=refl) - 0.5) * 140
        wy = (cv2.remap(n3, xx - ox, yy + oy * 0.8, cv2.INTER_LINEAR, borderMode=refl) - 0.5) * 140
        v = cv2.remap(n1, xx + wx + t * 3.0, yy + wy + oy, cv2.INTER_LINEAR, borderMode=refl)
        v = np.clip((v - 0.3) / 0.45, 0, 1) ** 1.8
        lum = (0.15 + 0.85 * v) * heat * dim
        img = base_a + (glow_a - base_a) * lum[..., None]
        if fil is not None:
            # ridged noise -> thin branching veins; brightness pulses travel along them
            r = cv2.remap(n4, xx + wx * 0.6, yy + wy * 0.6 + oy * 0.9, cv2.INTER_LINEAR, borderMode=refl)
            vein = np.exp(-((r - 0.5) / 0.010) ** 2)
            pulse = 0.5 + 0.5 * np.sin(xx * 0.02 + yy * 0.013 - t * 4.0)
            vein = cv2.GaussianBlur(vein * (0.25 + 0.75 * pulse ** 3), (0, 0), 0.8)
            halo = cv2.GaussianBlur(vein, (0, 0), 6)
            img = img + (vein[..., None] * 0.9 + halo[..., None] * 1.1) * np.array(fil, np.float32) * dim
            img = img + (v ** 8)[..., None] * np.array([60, 75, 95], np.float32) * dim   # metallic sheen
        f = cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (W, H), interpolation=cv2.INTER_CUBIC)
        f = f.astype(np.float32)
        near, far = np.zeros((H, W, 3), np.float32), np.zeros((H, W, 3), np.float32)
        for px, py, pz in parts:
            sp = 0.05 + 0.30 * pz
            y = ((py - t * sp) % 1.2 - 0.1) * H
            x = px * W + 18 * math.sin(t * 0.7 + px * 20)
            ln = sp * H / 30 * 1.5                 # motion streak length per frame-ish
            r_ = max(int(1 + 4 * pz ** 2), 1)
            a = (0.35 + 0.65 * pz) * dim
            tgt = near if pz > 0.7 else far
            cv2.line(tgt, (int(x), int(y)), (int(x), int(y + ln)), [c * a for c in pcol], r_, cv2.LINE_AA)
        f += cv2.GaussianBlur(far, (0, 0), 1.2) + cv2.GaussianBlur(near, (0, 0), 5) * 1.6
        if rain:  # helium 'rain': bright droplets falling faster than we sink, so they streak downward past us
            drops = np.zeros((H, W, 3), np.float32)
            for px, py, pz in rain_pts:
                y = ((py + t * (0.35 + 0.6 * pz)) % 1.2 - 0.1) * H
                x = px * W
                ln = 30 + 120 * pz
                cv2.line(drops, (int(x), int(y - ln)), (int(x), int(y)), [230 * (0.4 + 0.6 * pz)] * 3,
                         max(1, int(1 + 3 * pz ** 2)), cv2.LINE_AA)
            f += cv2.GaussianBlur(drops, (0, 0), 1.5) * 0.9 + cv2.GaussianBlur(drops, (0, 0), 8) * 0.8
        return _post(np.clip(f, 0, 255).astype(np.uint8), t, bloom=0.5, grain=4.0)
    return render


PRESETS["fluid"] = fluid


# ----------------------------------------------------------------- attribution for rendered shots
SSS_CREDIT = ("Planet and star-field textures: Solar System Scope (solarsystemscope.com/textures), CC BY 4.0 "
              "— based on NASA imagery")


def _junocam_credit(stem: str) -> tuple[str, str]:
    import json
    prov = json.loads((r3.TEX_DIR / "detail_provenance.json").read_text())
    p = prov[stem]
    return p["credit"], p["source_page"]


def shot_sources(shot: str, params: dict | None = None) -> list[str]:
    """Texture/image stems a shot draws from (for on-screen and description credits)."""
    params = params or {}
    if shot == "cloud_dive":
        layers = params.get("layers") or DIVE_LAYERS
        decks = params.get("decks", 2)
        return sorted({nm.rsplit(".", 1)[0] for nm, _ in layers[: decks + 1]})
    if shot in ("fluid",):
        return []
    return ["sss", "detail_barge"]


def onscreen_credit(shot: str, params: dict | None = None) -> str:
    stems = shot_sources(shot, params)
    if not stems:
        return "Visualization (schematic)"
    names = []
    for s in stems:
        if s == "sss":
            continue
        c = _junocam_credit(s)[0]
        import re as _re
        m = _re.search(r"(?:Enhanced image by|processing:?)\s*([A-Z][\w.]*(?: [A-Z][\w.]*)*)", c)
        if m:
            names.append(m.group(1))
    if shot == "cloud_dive":
        return "Visualization from JunoCam images · NASA/JPL-Caltech/SwRI/MSSS · " + ", ".join(dict.fromkeys(names))
    return "Visualization · textures: Solar System Scope (CC BY 4.0), JunoCam/K. M. Gill (CC BY)"


def description_credits(beats: list[dict]) -> list[str]:
    stems = set()
    for b in beats:
        if b.get("type") == "r3d":
            stems.update(shot_sources(b["shot"], b.get("params")))
    out = []
    if "sss" in stems:
        out.append(SSS_CREDIT)
    for s in sorted(stems - {"sss"}):
        c, page = _junocam_credit(s)
        out.append(f"{c} (used as texture/backdrop in rendered visualizations) — {page}")
    return out
