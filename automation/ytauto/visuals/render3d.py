"""Cinematic 3D renderer for planets and moons, built on real texture maps.

A vectorised ray tracer (numpy + OpenCV remap) for textured spheres, lit by a distant
sun, with soft terminators, limb darkening, atmospheric rim glow, rings (with the
planet's shadow), a Milky Way background, sun glare, and interior cutaways that show
layers at their true relative radii. ~0.1-0.2 s per 1080p frame on 4 CPU cores.

Units are arbitrary (use planet radii); y is up; the camera looks along -z by default.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ytauto.core import config

Image.MAX_IMAGE_PIXELS = None
TEX_DIR = config.CACHE_DIR / "textures"


# ----------------------------------------------------------------- textures
@lru_cache(maxsize=16)
def texture(name: str, max_w: int = 8192) -> np.ndarray:
    p = Path(name) if Path(name).is_absolute() else TEX_DIR / name
    im = Image.open(p)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    return np.ascontiguousarray(a)


@lru_cache(maxsize=16)
def texture_lin(name: str, max_w: int = 8192) -> np.ndarray:
    """Texture converted to linear light once and cached (the conversion is expensive)."""
    t = texture(name, max_w)
    out = np.empty_like(t)
    out[..., :3] = np.power(t[..., :3], 2.2)
    if t.shape[-1] == 4:
        out[..., 3] = t[..., 3]
    return out


@lru_cache(maxsize=4)
def texture_gray3(name: str) -> np.ndarray:
    g = texture_lin(name)[..., :3].mean(-1, keepdims=True)
    return np.ascontiguousarray(np.repeat(g, 3, -1))


DETAIL_CROPS = {"detail_barge.jpg": (0.45, 0.02, 1.0, 0.45), "detail_swift.jpg": (0.05, 0.05, 0.95, 0.95)}


@lru_cache(maxsize=8)
def detail_texture(name: str, sigma: float = 20.0) -> np.ndarray:
    """High-pass luminance ratio (~1.0 mean) from a real close-up image, mirrored 2x2 so it tiles
    seamlessly. Multiplying the base albedo by it adds real small-scale cloud structure."""
    t = texture(name, 4096)[..., :3]
    cx0, cy0, cx1, cy1 = DETAIL_CROPS.get(name, (0.1, 0.1, 0.9, 0.9))
    hh, ww = t.shape[:2]
    t = t[int(cy0 * hh):int(cy1 * hh), int(cx0 * ww):int(cx1 * ww)]
    lum = t.mean(-1)
    base = cv2.GaussianBlur(lum, (0, 0), sigma)
    ratio = np.clip(lum / np.maximum(base, 1e-3), 0.55, 1.6).astype(np.float32)
    tile = np.concatenate([np.concatenate([ratio, ratio[:, ::-1]], 1),
                           np.concatenate([ratio[::-1], ratio[::-1, ::-1]], 1)], 0)
    return np.ascontiguousarray(tile)


def tex_level(name: str, level: int) -> np.ndarray:
    """Pre-filtered texture at 1/2^level resolution (cheap mipmapping to avoid shimmer)."""
    full = texture_lin(name)
    w = max(full.shape[1] >> level, 256)
    return texture_lin(name, w) if level else full


def srgb_to_lin(x):
    return np.power(np.clip(x, 0, 1), 2.2)


def lin_to_srgb(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-9)


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def _rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def _rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)


# ----------------------------------------------------------------- scene objects
@dataclass
class Body:
    tex: str
    center: tuple = (0.0, 0.0, 0.0)
    radius: float = 1.0
    spin: float = 0.0               # rotation about the body's axis (radians)
    tilt: float = 0.0               # axial tilt (radians, about z)
    atmosphere: tuple | None = None  # (r, g, b) linear glow colour
    atmo_height: float = 0.04       # glow thickness as fraction of radius
    atmo_strength: float = 1.0
    night_tex: str | None = None
    limb_dark: float = 0.0          # 0 for rocky bodies, ~0.5 for gas giants
    falloff: float = 1.4            # >1 = more dramatic light falloff toward the terminator
    wrap: float = 0.0               # softens the terminator (gas giants ~0.15)
    gain: float = 1.0
    emissive: bool = False          # for the Sun
    rings: dict | None = None       # {"tex": ..., "inner": 1.24, "outer": 2.27, "gain": 1.0}
    cutaway: dict | None = None     # {"layers": [(r_frac, (r,g,b)), ...], "wedge": deg, "facing": deg}
    clouds_tex: str | None = None
    clouds_spin: float = 0.0
    detail_tex: str | None = None    # real close-up image used as small-scale detail
    detail_scale: float = 24.0       # repeats around the globe
    detail_strength: float = 0.8

    def rotation(self) -> np.ndarray:
        return (_rot_z(self.tilt) @ _rot_y(self.spin)).astype(np.float32)


@dataclass
class Camera:
    pos: tuple = (0.0, 0.0, 4.0)
    target: tuple = (0.0, 0.0, 0.0)
    up: tuple = (0.0, 1.0, 0.0)
    fov: float = 40.0
    roll: float = 0.0


@dataclass
class Scene:
    bodies: list = field(default_factory=list)
    sun_dir: tuple = (-0.6, 0.25, 0.75)   # direction from scene towards the sun
    background: str | None = "8k_stars_milky_way.jpg"
    bg_gain: float = 0.32
    bg_rotation: float = 0.0
    exposure: float = 1.0
    sun_visible_glow: bool = True
    ambient: float = 0.0008
    _fov: float = 40.0
    _w: int | None = None


# ----------------------------------------------------------------- core helpers
def _rays(cam: Camera, w: int, h: int):
    pos = np.array(cam.pos, np.float32)
    fwd = _norm(np.array(cam.target, np.float32) - pos)
    right = _norm(np.cross(fwd, np.array(cam.up, np.float32)))
    up = np.cross(right, fwd)
    if cam.roll:
        c, s = math.cos(cam.roll), math.sin(cam.roll)
        right, up = right * c + up * s, -right * s + up * c
    t = math.tan(math.radians(cam.fov) / 2)
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    ys = 1 - (np.arange(h, dtype=np.float32) + 0.5) / h * 2
    X, Y = np.meshgrid(xs * t * w / h, ys * t)
    d = fwd[None, None, :] + X[..., None] * right[None, None, :] + Y[..., None] * up[None, None, :]
    return pos, _norm(d.astype(np.float32))


def _sample_equirect(tex: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    """Sample an equirectangular map with unit direction vectors (body frame)."""
    x, y, z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(y, -1, 1))
    th, tw = tex.shape[:2]
    mx = ((lon / (2 * np.pi) + 0.5) % 1.0) * tw - 0.5
    my = (0.5 - lat / np.pi) * th - 0.5
    return cv2.remap(tex, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


def _sphere_hit(o, d, c, r):
    oc = o - np.array(c, np.float32)
    b = (d @ oc)
    cc = float(oc @ oc) - r * r
    disc = b * b - cc
    hit = disc > 0
    sq = np.sqrt(np.clip(disc, 0, None))
    t0 = -b - sq
    t1 = -b + sq
    t = np.where(t0 > 1e-4, t0, t1)
    hit &= t > 1e-4
    return hit, t, disc, -b  # -b = distance along ray to closest approach


# ----------------------------------------------------------------- render
def render(scene: Scene, cam: Camera, w: int = 1920, h: int = 1080) -> np.ndarray:
    """Return an sRGB uint8 frame (h, w, 3)."""
    o, d = _rays(cam, w, h)
    scene._fov, scene._w = cam.fov, w
    L = _norm(np.array(scene.sun_dir, np.float32))
    img = np.zeros((h, w, 3), np.float32)

    # background
    if scene.background:
        bg = texture_lin(scene.background)[..., :3]
        dd = d @ _rot_y(scene.bg_rotation).T
        img += _sample_equirect(bg, dd) * scene.bg_gain

    depth = np.full((h, w), np.inf, np.float32)

    # sun glow (behind bodies; occlusion handled by depth compositing below)
    if scene.sun_visible_glow:
        cosang = d @ L
        ang = np.arccos(np.clip(cosang, -1, 1))
        glow = 0.9 * np.exp(-(ang / 0.012) ** 2) + 0.25 * np.exp(-ang / 0.06) + 0.05 * np.exp(-ang / 0.35)
        img += glow[..., None] * np.array([1.0, 0.92, 0.8], np.float32)

    for b in sorted(scene.bodies, key=lambda b: -np.linalg.norm(np.array(b.center) - o)):
        _draw_body(img, depth, b, scene, o, d, L)

    img *= scene.exposure
    return (lin_to_srgb(_tonemap(img)) * 255).astype(np.uint8)


def _tonemap(x):
    # soft-clip highlights (filmic-ish) so glare does not burn out
    return x / (1 + np.maximum(x - 0.8, 0) * 0.9)


def _draw_body_full(img, depth, b: Body, scene: Scene, o, d, L):
    c = np.array(b.center, np.float32)
    R = b.radius
    hit, t, disc, tca = _sphere_hit(o, d, c, R)
    rot = b.rotation()
    inv = rot.T
    color = np.zeros_like(img)
    alpha = np.zeros(img.shape[:2], np.float32)

    # ---------- ring (plane through centre, normal = body axis)
    ring_rgba = None
    if b.rings:
        n = rot @ np.array([0, 1, 0], np.float32)
        denom = d @ n
        tr = ((c - o) @ n) / np.where(np.abs(denom) < 1e-6, 1e-6, denom)
        p = o + d * tr[..., None]
        rr = np.linalg.norm(p - c, axis=-1) / R
        ri, ro = b.rings["inner"], b.rings["outer"]
        onring = (tr > 0) & (rr >= ri) & (rr <= ro)
        if onring.any():
            rt = texture(b.rings["tex"], 8192)
            row = rt[rt.shape[0] // 2]
            u = ((rr - ri) / (ro - ri) * (len(row) - 1)).clip(0, len(row) - 1).astype(np.int32)
            rgba = row[u]
            rcol = srgb_to_lin(rgba[..., :3]) * b.rings.get("gain", 1.0)
            ra = rgba[..., 3] if rgba.shape[-1] == 4 else rgba[..., :3].mean(-1)
            # lighting: rings lit by the sun from either side; planet shadow
            lit = 0.35 + 0.65 * abs(float(L @ n))
            # does the ray from the ring point towards the sun hit the planet?
            oc = p - c
            bq = oc @ L
            cq = (oc * oc).sum(-1) - R * R
            sh_hit = (bq * bq - cq > 0) & (-bq - np.sqrt(np.clip(bq * bq - cq, 0, None)) > 0)
            shadow = np.where(sh_hit, 0.08, 1.0)
            ring_rgba = (rcol * (lit * shadow)[..., None], np.where(onring, ra, 0.0), tr)

    # ---------- sphere surface
    if hit.any():
        P = o + d * t[..., None]
        N = (P - c) / R
        Nb = N @ inv.T  # body frame
        # mip level from the on-screen size of one texel
        full_w = texture_lin(b.tex).shape[1]
        cam_d = float(np.linalg.norm(o - c))
        pix_ang = 2 * math.tan(math.radians(scene._fov) / 2) / max(img.shape[1] if scene._w is None else scene._w, 1)
        footprint = max(cam_d - R, R * 0.002) * pix_ang
        texel = 2 * math.pi * R / full_w
        level = int(np.clip(math.floor(math.log2(max(footprint / texel, 1e-6))), 0, 4))
        tex = tex_level(b.tex, level)[..., :3]
        albedo = _sample_equirect(tex, Nb)
        if b.detail_tex:
            near = float(np.clip((2.2 * R - (cam_d - R)) / (2.0 * R), 0, 1))
            if near > 0:
                dt = detail_texture(b.detail_tex)
                x_, y_, z_ = Nb[..., 0], Nb[..., 1], Nb[..., 2]
                lon = np.arctan2(x_, z_)
                lat = np.arcsin(np.clip(y_, -1, 1))
                dh, dw = dt.shape
                k = b.detail_scale
                mx = ((lon / (2 * np.pi) + 0.5) * k % 1.0) * dw
                my = ((0.5 - lat / np.pi) * k / 2 % 1.0) * dh
                dv = cv2.remap(dt, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_WRAP)
                albedo = albedo * (1 + (dv - 1) * b.detail_strength * near)[..., None]
        if b.emissive:
            mu = np.clip(-(N * d).sum(-1), 0, 1)
            col = albedo * (0.55 + 0.45 * mu ** 0.5)[..., None] * b.gain * 2.2
        else:
            ndl = (N @ L)
            diff = np.clip((ndl + b.wrap) / (1 + b.wrap), 0, 1)
            diff = diff ** b.falloff
            if b.rings:  # ring shadow on the planet
                n = rot @ np.array([0, 1, 0], np.float32)
                denom = float(L @ n)
                if abs(denom) > 1e-4:
                    ts = ((c - P) @ n) / denom
                    q = P + L[None, None, :] * ts[..., None]
                    rq = np.linalg.norm(q - c, axis=-1) / R
                    inring = (ts > 0) & (rq > b.rings["inner"]) & (rq < b.rings["outer"])
                    diff = np.where(inring, diff * 0.45, diff)
            mu = np.clip(-(N * d).sum(-1), 0, 1)
            limb = (1 - b.limb_dark) + b.limb_dark * mu ** 0.6
            col = albedo * (diff * limb)[..., None] * b.gain + albedo * scene.ambient
            if b.clouds_tex:
                cl = _sample_equirect(texture_gray3(b.clouds_tex), Nb @ _rot_y(b.clouds_spin).T)[..., :1]
                col = col * (1 - cl * 0.9) + cl * diff[..., None] * 1.0
            if b.night_tex:
                nt = texture_lin(b.night_tex)[..., :3]
                nights = _sample_equirect(nt, Nb)
                col += nights * np.clip(-ndl * 4, 0, 1)[..., None] * 0.6
            if b.atmosphere is not None:  # rim light on the disc
                rim = (1 - mu) ** 3 * np.clip(ndl + 0.08, 0, 1)
                col += np.array(b.atmosphere, np.float32) * (rim * b.atmo_strength * 0.8)[..., None]
        # interior cutaway: remove a wedge and show layers on the cut faces
        if b.cutaway:
            col, hitmask, t = _cutaway(b, o, d, c, R, rot, P, col, hit, t, L)
            hit = hitmask
        # anti-aliased edge from distance to silhouette
        edge = np.clip(np.sqrt(np.clip(disc, 0, None)) / (R * 0.004 + 1e-6), 0, 1)
        a_s = np.where(hit, edge if not b.cutaway else 1.0, 0.0)
        color = np.where(hit[..., None], col, color)
        alpha = np.maximum(alpha, a_s)

    # ---------- atmosphere with exponential density (scale height Hsc)
    if b.atmosphere is not None and not b.emissive:
        Hsc = R * b.atmo_height
        atm = np.array(b.atmosphere, np.float32)
        oc = o - c
        h_cam = float(np.linalg.norm(oc)) - R
        dmin = np.sqrt(np.clip(float(oc @ oc) - tca ** 2, 0, None))
        # (a) seen from outside: glow by the ray's lowest altitude (smooth, no hard shell edge)
        h_min = np.where(tca > 0, dmin - R, h_cam)
        away = np.clip(1 + tca / (R * 0.15), 0, 1)        # fades smoothly for rays pointing away
        outside = np.exp(-np.clip(h_min, 0, None) / Hsc) * away
        tp = o + d * np.clip(tca, 0, None)[..., None]
        lit = np.clip(_norm(tp - c) @ L * 0.9 + 0.25, 0, 1)
        # (b) from inside the atmosphere: optical depth ~ density(h_cam) / sin(elevation)
        n_cam = oc / max(float(np.linalg.norm(oc)), 1e-9)
        sin_el = d @ n_cam
        dens = math.exp(-max(h_cam, 0) / Hsc)
        tau = dens * Hsc * 12 / (np.clip(sin_el, 0, None) + 0.06)
        inside = (1 - np.exp(-tau)) * dens ** 0.3
        w_in = float(np.clip(1 - h_cam / (Hsc * 8), 0, 1))
        sky = (outside * (1 - w_in) * 0.9 + inside * w_in) * b.atmo_strength
        lit_cam = float(np.clip(n_cam @ L * 0.9 + 0.3, 0, 1))
        sky_lit = lit * (1 - w_in) + lit_cam * w_in
        img += atm * (sky * sky_lit * ~hit)[..., None] * (1 - alpha)[..., None]
        if hit.any() and w_in > 0:  # aerial perspective: distant cloud tops fade into haze
            fog = (1 - np.exp(-t * dens / (Hsc * 40))) * w_in * b.atmo_strength
            color = color * (1 - fog[..., None] * 0.7) + atm * (fog * lit_cam)[..., None] * 1.5

    # ---------- composite ring behind / in front of the sphere
    def comp_ring(front: bool):
        nonlocal img
        if ring_rgba is None:
            return
        rcol, ra, tr = ring_rgba
        sel = (tr < t) if front else (tr >= t) | ~hit
        a = ra * sel
        img[:] = img * (1 - a[..., None]) + rcol * a[..., None]

    comp_ring(front=False)
    img[:] = img * (1 - alpha[..., None]) + color * alpha[..., None]
    comp_ring(front=True)
    depth[hit] = np.minimum(depth[hit], t[hit])


def _draw_body(img, depth, b: Body, scene: Scene, o, d, L):
    """Render only inside the screen-space bounding box of the body (+ halo / rings)."""
    c = np.array(b.center, np.float32)
    ext = b.radius * max(1.0 + (b.atmo_height * 5 if b.atmosphere is not None else 0.01),
                         (b.rings or {}).get("outer", 0) * 1.02)
    oc = o - c
    bb = d @ oc
    disc = bb * bb - (float(oc @ oc) - ext * ext)
    mask = (disc > 0) & (-bb > 0) if float(oc @ oc) > ext * ext else np.ones(disc.shape, bool)
    if not mask.any():
        return
    rows = np.where(mask.any(1))[0]
    cols = np.where(mask.any(0))[0]
    r0, r1 = max(rows[0] - 2, 0), min(rows[-1] + 3, img.shape[0])
    c0, c1 = max(cols[0] - 2, 0), min(cols[-1] + 3, img.shape[1])
    sub_img = img[r0:r1, c0:c1]
    sub_depth = depth[r0:r1, c0:c1]
    _draw_body_full(sub_img, sub_depth, b, scene, o, np.ascontiguousarray(d[r0:r1, c0:c1]), L)


def _cutaway(b, o, d, c, R, rot, P, col, hit, t, L):
    """Remove a wedge (centred on `facing`, width `wedge` degrees) and paint the two cut faces."""
    cfg = b.cutaway
    half = math.radians(cfg.get("wedge", 90)) / 2
    face = math.radians(cfg.get("facing", 0))
    # wedge boundaries in body frame: planes containing the axis (y) at angles face +/- half
    a1 = face - half
    a2 = face + half
    n1 = rot @ np.array([math.cos(a1), 0, -math.sin(a1)], np.float32)   # plane normals
    n2 = rot @ np.array([-math.cos(a2), 0, math.sin(a2)], np.float32)

    def in_wedge(Q):
        rel = Q - c
        return ((rel @ n1) > 0) & ((rel @ n2) > 0)

    removed = hit & in_wedge(P)
    newcol = col.copy()
    newhit = hit & ~removed
    tnew = t.copy()
    layers = cfg["layers"]  # [(outer_r_frac, (r,g,b)), ...] from outside in
    best_t = np.full(t.shape, np.inf, np.float32)
    face_col = np.zeros_like(col)
    for nrm in (n1, n2):
        denom = d @ nrm
        tp = ((c - o) @ nrm) / np.where(np.abs(denom) < 1e-6, 1e-6, denom)
        Q = o + d * tp[..., None]
        rel = Q - c
        rq = np.linalg.norm(rel, axis=-1) / R
        other = n2 if nrm is n1 else n1
        on = (tp > 0) & (rq <= 1.0) & ((rel @ other) >= -1e-5)
        # colour by radius with soft blending between layers
        lc = np.zeros(col.shape, np.float32)
        for k, layer in enumerate(layers):
            rf, rgb = layer[0], layer[1]
            rgb_in = layer[2] if len(layer) > 2 else rgb
            inner = layers[k + 1][0] if k + 1 < len(layers) else 0.0
            m = (rq <= rf) & (rq > inner)
            u = ((rq - inner) / max(rf - inner, 1e-6)).clip(0, 1)[..., None]   # 1 at outer edge
            grad = np.array(rgb, np.float32) * u + np.array(rgb_in, np.float32) * (1 - u)
            lc[m] = grad[m]
        # radial glow toward the centre (hotter inside)
        heat = np.clip(1 - rq, 0, 1) ** 2
        lc = lc * (0.75 + 0.5 * heat[..., None])
        shade = 0.55 + 0.45 * abs(float(nrm @ L))
        lc *= shade
        # layer boundary lines
        for layer in layers:
            lc[np.abs(rq - layer[0]) < 0.0035] = np.array([1.0, 0.95, 0.85], np.float32) * 0.8
        upd = on & (tp < best_t) & (removed | ~hit | (tp < t))
        best_t = np.where(upd, tp, best_t)
        face_col = np.where(upd[..., None], lc, face_col)
    show_face = np.isfinite(best_t) & (removed | (best_t < t) | ~hit) & (best_t > 0)
    newcol = np.where(show_face[..., None], face_col, newcol)
    newhit = newhit | show_face
    tnew = np.where(show_face, best_t, tnew)
    return newcol, newhit, tnew


def project(cam: Camera, point, w: int = 1920, h: int = 1080):
    """Screen coordinates (x, y) of a 3D point, or None if behind the camera."""
    pos = np.array(cam.pos, np.float32)
    fwd = _norm(np.array(cam.target, np.float32) - pos)
    right = _norm(np.cross(fwd, np.array(cam.up, np.float32)))
    up = np.cross(right, fwd)
    v = np.array(point, np.float32) - pos
    z = float(v @ fwd)
    if z <= 1e-6:
        return None
    t = math.tan(math.radians(cam.fov) / 2)
    x = float(v @ right) / z / (t * w / h)
    y = float(v @ up) / z / t
    return ((x + 1) / 2 * w, (1 - y) / 2 * h)


def lerp_cam(a: Camera, b: Camera, u: float) -> Camera:
    """Smoothly interpolate two cameras (u in 0..1, eased)."""
    e = u * u * (3 - 2 * u)
    mix = lambda p, q: tuple(float(x) + (float(y) - float(x)) * e for x, y in zip(p, q))
    return Camera(pos=mix(a.pos, b.pos), target=mix(a.target, b.target), up=mix(a.up, b.up),
                  fov=a.fov + (b.fov - a.fov) * e, roll=a.roll + (b.roll - a.roll) * e)


# ----------------------------------------------------------------- post effects
def bloom(frame: np.ndarray, strength: float = 0.35, thresh: int = 200) -> np.ndarray:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (w // 4, h // 4), interpolation=cv2.INTER_AREA).astype(np.float32)
    bright = np.clip(small - thresh, 0, None)
    b = cv2.GaussianBlur(bright, (0, 0), 3) + cv2.GaussianBlur(bright, (0, 0), 10)
    b = cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(frame.astype(np.float32) + b * strength, 0, 255).astype(np.uint8)


def film_grain(frame: np.ndarray, amount: float = 4.0, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    g = rng.normal(0, amount, frame.shape[:2]).astype(np.float32)[..., None]
    return np.clip(frame.astype(np.float32) + g, 0, 255).astype(np.uint8)
