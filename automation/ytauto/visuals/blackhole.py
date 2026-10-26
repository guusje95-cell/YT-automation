"""Schwarzschild black-hole renderer (geometric units: G = c = M = 1, horizon at r = 2).

Every camera ray is traced through curved space-time: each ray stays in the plane spanned by the line to the
black hole and its own direction, so its path is the photon orbit equation u'' = -u + 3u² (u = 1/r) integrated in
that plane. Rays are binned by impact parameter b and integrated together (RK4, vectorised), giving r(φ) per b.
Per pixel we then find where its orbit crosses the accretion-disk plane (thin disk, r_in..r_out), or where it
escapes (lensed star field) or falls in (black). Gives the gravitational lensing of the background, the "hump" of
the far side of the disk bent over the top, a secondary image under the hole and the photon ring.
Disk colour: thin-disk temperature profile T ∝ r^-3/4 (1 - sqrt(r_in/r))^1/4, relativistic beaming ~ D^3 with
Keplerian speed v = r^-1/2, gravitational redshift sqrt(1 - 3/r). Camera is static (no aberration).
Because every length scales with mass, the image is the same for any non-rotating black hole; only the
labels change. Schematic of physics, not a measured image.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np

from ytauto.visuals import render3d as r3


def _orbit_table(r_cam: float, b: np.ndarray, outward: bool, n_phi: int = 1400, phi_max: float = 4.0 * math.pi):
    """r(φ) for rays leaving the camera with impact parameters b. Returns (r_tab [nb, n_phi], phi_end [nb],
    captured [nb], phi_escape [nb])."""
    u0 = 1.0 / r_cam
    w0 = np.sqrt(np.maximum(1.0 / b ** 2 - u0 ** 2 + 2 * u0 ** 3, 0.0))
    if outward:
        w0 = -w0
    u = np.full_like(b, u0)
    w = w0.copy()
    dphi = phi_max / n_phi
    r_tab = np.full((len(b), n_phi), np.inf, np.float32)
    alive = np.ones(len(b), bool)
    captured = np.zeros(len(b), bool)
    phi_esc = np.full(len(b), np.nan, np.float32)

    def f(u_, w_):
        return w_, -u_ + 3.0 * np.minimum(u_, 1.0) ** 2

    for j in range(n_phi):
        r_tab[alive, j] = 1.0 / np.maximum(u[alive], 1e-9)
        k1u, k1w = f(u, w)
        k2u, k2w = f(u + 0.5 * dphi * k1u, w + 0.5 * dphi * k1w)
        k3u, k3w = f(u + 0.5 * dphi * k2u, w + 0.5 * dphi * k2w)
        k4u, k4w = f(u + dphi * k3u, w + dphi * k3w)
        un = u + dphi / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
        wn = w + dphi / 6 * (k1w + 2 * k2w + 2 * k3w + k4w)
        cap = alive & (un >= 0.5)
        esc = alive & (un <= 0.0)
        captured |= cap
        # escape angle: linear interpolation of the zero crossing of u
        frac = np.where(esc, u / np.maximum(u - un, 1e-12), 0)
        phi_esc = np.where(esc, (j + frac) * dphi, phi_esc)
        alive &= ~(cap | esc)
        u, w = un, wn
        if not alive.any():
            break
    return r_tab, captured, phi_esc, dphi


@lru_cache(maxsize=4)
def _star_tex():
    return r3.texture_lin("8k_stars_milky_way.jpg", 4096)


@lru_cache(maxsize=8)
def _disk_noise(seed: int = 1, n_r: int = 1024, n_a: int = 2048) -> np.ndarray:
    """Polar texture (radius x angle): many thin concentric gas lanes, gently modulated along the orbit."""
    rng = np.random.default_rng(seed)
    rings = np.zeros(n_r, np.float32)
    amp = 1.0
    for o in range(7):
        cells = 8 * 2 ** o
        g = rng.random(cells + 1).astype(np.float32)
        rings += np.interp(np.linspace(0, cells, n_r), np.arange(cells + 1), g) * amp
        amp *= 0.65
    rings = (rings - rings.min()) / (rings.max() - rings.min())
    ang = np.zeros((n_r, n_a), np.float32)
    amp = 1.0
    for o in range(4):
        cr, ca = 16 * 2 ** o, 6 * 2 ** o
        g = rng.random((cr, ca)).astype(np.float32)
        g = np.concatenate([g, g[:, :1]], 1)
        ang += cv2.resize(g, (n_a + n_a // ca, n_r), interpolation=cv2.INTER_CUBIC)[:, :n_a] * amp
        amp *= 0.55
    ang = (ang - ang.min()) / (ang.max() - ang.min())
    tex = rings[:, None] ** 1.3 * (0.55 + 0.45 * ang)
    tex = cv2.GaussianBlur(tex, (0, 0), sigmaX=10, sigmaY=0.4)   # smear along the orbit
    return (tex - tex.min()) / (tex.max() - tex.min())


def _blackbody_rgb(t: np.ndarray) -> np.ndarray:
    """Rough colour ramp for normalised temperature t in [0, 1]: deep red -> orange -> white -> blue-white."""
    stops = np.array([[0.0, 0.25, 0.02, 0.0], [0.25, 0.9, 0.25, 0.03], [0.5, 1.0, 0.62, 0.25],
                      [0.75, 1.0, 0.9, 0.75], [1.0, 0.85, 0.9, 1.0]], np.float32)
    out = np.zeros(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, stops[:, 0], stops[:, c + 1])
    return out


def render(cam_r: float, cam_az: float, cam_el: float, w: int, h: int, fov: float = 60.0, t: float = 0.0,
           look_offset=(0.0, 0.0), disk=True, r_in: float = 6.0, r_out: float = 20.0, disk_gain: float = 1.0,
           star_gain: float = 0.35, star_rot: float = 0.0, roll: float = 0.0, spin_speed: float = 1.0,
           tilt: float = 0.0) -> np.ndarray:
    """Linear-light float image (h, w, 3). Camera on a sphere of radius cam_r (in M) around the hole, looking at
    it (plus `look_offset` = (yaw, pitch) in degrees). Disk lies in the plane z = 0 (normal +y), optionally tilted."""
    # camera basis (world: y up)
    ce, se = math.cos(cam_el), math.sin(cam_el)
    pos = np.array([cam_r * ce * math.sin(cam_az), cam_r * se, cam_r * ce * math.cos(cam_az)], np.float64)
    fwd = -pos / np.linalg.norm(pos)
    up0 = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up0)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    if roll:
        cr, sr = math.cos(roll), math.sin(roll)
        right, up = right * cr + up * sr, -right * sr + up * cr
    yaw, pitch = map(math.radians, look_offset)
    fwd2 = fwd * math.cos(yaw) * math.cos(pitch) + right * math.sin(yaw) * math.cos(pitch) + up * math.sin(pitch)
    right2 = np.cross(fwd2, up)
    right2 /= np.linalg.norm(right2)
    up2 = np.cross(right2, fwd2)
    tan = math.tan(math.radians(fov) / 2)
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    ys = (np.arange(h, dtype=np.float32) + 0.5) / h * 2 - 1
    X, Y = np.meshgrid(xs * tan, -ys * tan * h / w)
    d = fwd2[None, None, :] + X[..., None] * right2 + Y[..., None] * up2
    d /= np.linalg.norm(d, axis=-1, keepdims=True)

    e1 = pos / cam_r                                   # from hole to camera
    cosa = -(d @ e1)                                   # cos of angle between ray and direction to hole
    sina = np.sqrt(np.clip(1 - cosa ** 2, 0, 1))
    b = cam_r * sina / np.sqrt(1 - 2 / cam_r)          # impact parameter (static observer, local angle)
    # in-plane perpendicular direction e2 (component of the ray orthogonal to e1)
    perp = d - (d @ e1)[..., None] * e1
    pn = np.linalg.norm(perp, axis=-1, keepdims=True)
    e2 = np.where(pn > 1e-9, perp / np.maximum(pn, 1e-9), np.array([0.0, 1.0, 0.0]))
    inward = cosa > 0

    out = np.zeros((h, w, 3), np.float32)
    n_b = 1600
    for outward in (False, True):
        m = (~inward) if outward else inward
        if not m.any():
            continue
        bm = b[m]
        b_max = float(bm.max()) * 1.0001 + 1e-6
        b_grid = np.linspace(1e-3, b_max, n_b).astype(np.float64)
        r_tab, captured, phi_esc, dphi = _orbit_table(cam_r, b_grid, outward)
        bi = np.clip(np.round((bm - b_grid[0]) / (b_grid[1] - b_grid[0])).astype(int), 0, n_b - 1)
        e2m = e2[m]
        # φ is measured from e1 toward e2; 3D point = r (cos φ e1 + sin φ e2)
        n_disk = np.array([math.sin(tilt), math.cos(tilt), 0.0])
        a1 = float(e1 @ n_disk)
        a2 = e2m @ n_disk
        col = np.zeros((len(bm), 3), np.float32)
        hit = np.zeros(len(bm), bool)
        if disk:
            base = np.arctan2(-a1, a2)                 # first solution of cos φ a1 + sin φ a2 = 0
            base = np.where(base < 0, base + math.pi, base)
            for k in range(4):
                phi_c = base + k * math.pi
                j = np.clip((phi_c / dphi).astype(int), 0, r_tab.shape[1] - 2)
                fr_ = phi_c / dphi - j
                r_a, r_b = r_tab[bi, j], r_tab[bi, j + 1]
                r_c = r_a * (1 - fr_) + r_b * fr_
                valid = np.isfinite(r_c) & (r_c >= r_in) & (r_c <= r_out) & ~hit & (phi_c / dphi < r_tab.shape[1] - 2)
                if valid.any():
                    p3 = (np.cos(phi_c)[:, None] * e1[None, :] + np.sin(phi_c)[:, None] * e2m) * r_c[:, None]
                    rr = r_c[valid]
                    ang = np.arctan2(p3[valid, 2], p3[valid, 0])
                    tprof = rr ** -0.75 * np.clip(1 - np.sqrt(r_in / rr), 0, 1) ** 0.25
                    tprof = tprof / (r_in ** -0.75 * 0.45)
                    # Keplerian orbital velocity (direction: counter-clockwise seen from +y)
                    v = np.clip(1 / np.sqrt(rr), 0, 0.6)
                    vdir = np.stack([-np.sin(ang), np.zeros_like(ang), np.cos(ang)], -1) * -1
                    # photon travels from disk to camera; approximate its direction by (camera - point)
                    to_cam = pos[None, :] - p3[valid]
                    to_cam /= np.linalg.norm(to_cam, axis=-1, keepdims=True)
                    beta = v * np.sum(vdir * to_cam, -1)
                    gamma = 1 / np.sqrt(1 - v ** 2)
                    D = 1 / (gamma * (1 - beta))
                    g = D * np.sqrt(np.clip(1 - 3 / rr, 0.05, 1))
                    # turbulence rotating differentially
                    nz = _disk_noise()
                    ri = np.clip(((rr - r_in) / (r_out - r_in) * (nz.shape[0] - 1)).astype(int), 0, nz.shape[0] - 1)
                    ang_rot = (ang + t * spin_speed * 0.6 * rr ** -1.5 * 10) % (2 * math.pi)
                    ai = (ang_rot / (2 * math.pi) * (nz.shape[1] - 1)).astype(int)
                    turb = 0.25 + 1.5 * nz[ri, ai]
                    temp = tprof * g                          # observed temperature (Doppler + gravity shifted)
                    flux = temp ** 4 * turb * (r_in / rr) ** 1.5   # ~T^4 plus the steep thin-disk falloff
                    tt = np.clip(temp, 0, 1.6)
                    hue = np.stack([np.ones_like(tt), 0.16 + 0.32 * tt ** 1.5, 0.02 + 0.16 * tt ** 3], -1)  # deep orange -> white-hot (linear light)
                    c = hue * (flux * disk_gain * 0.28)[:, None]
                    edge = np.clip((r_out - rr) / (0.25 * r_out), 0, 1) ** 1.5   # soft outer edge
                    c *= edge[:, None]
                    idx = np.where(valid)[0]
                    col[idx] = c * (0.85 if k > 0 else 1.0)
                    hit[idx] = True
        # background for escaped rays not blocked by the disk
        esc = ~hit & ~captured[bi] & np.isfinite(phi_esc[bi])
        if esc.any():
            # interpolate the escape angle between neighbouring impact-parameter bins (no banding in the stars)
            fb = (bm[esc] - b_grid[0]) / (b_grid[1] - b_grid[0])
            i0 = np.clip(np.floor(fb).astype(int), 0, n_b - 2)
            ff = np.clip(fb - i0, 0, 1)
            p0, p1 = phi_esc[i0], phi_esc[i0 + 1]
            pe = np.where(np.isfinite(p0) & np.isfinite(p1), p0 * (1 - ff) + p1 * ff, phi_esc[bi][esc])
            # far from the hole use the smooth weak-field deflection (4/b + 15π/4b²) instead of the table
            be = bm[esc]
            ca = cosa[m][esc] if cosa[m].ndim == 1 else cosa[m][esc]
            theta_d = np.arctan2(np.sqrt(np.clip(1 - ca ** 2, 0, 1)), -ca)
            weak = theta_d + 4.0 / be + 15 * math.pi / (4 * be ** 2)
            blend = np.clip((be - 25.0) / 15.0, 0, 1)
            pe = pe * (1 - blend) + weak * blend
            dir_out = np.cos(pe)[:, None] * e1[None, :] + np.sin(pe)[:, None] * e2m[esc]
            lon = (np.arctan2(dir_out[:, 0], dir_out[:, 2]) / (2 * math.pi) + 0.5 + star_rot) % 1.0
            lat = np.arcsin(np.clip(dir_out[:, 1], -1, 1)) / math.pi + 0.5
            tex = _star_tex()
            th, tw = tex.shape[:2]
            yf, xf = (1 - lat) * (th - 1), lon * (tw - 1)
            y0, x0 = np.clip(yf.astype(int), 0, th - 2), np.clip(xf.astype(int), 0, tw - 2)
            fy, fx = (yf - y0)[:, None], (xf - x0)[:, None]
            col[esc] += ((tex[y0, x0] * (1 - fx) + tex[y0, x0 + 1] * fx) * (1 - fy) +
                         (tex[y0 + 1, x0] * (1 - fx) + tex[y0 + 1, x0 + 1] * fx) * fy) * star_gain
        out[m] = col
    return out


def to_srgb(img_lin: np.ndarray, exposure: float = 1.0) -> np.ndarray:
    x = 1 - np.exp(-img_lin * exposure)                # soft filmic shoulder (keeps the hot inner disk from clipping)
    return (np.clip(x, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
