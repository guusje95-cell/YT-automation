"""Procedural sound design, synthesised from code (no licences, no Content ID risk).

`design(beats, total_s)` returns a stereo 48 kHz effects track laid out on the edit timeline:
  approach / orbit streak   rising whoosh
  entry                     plasma roar (band-limited noise swelling with the heating curve) + low rumble
  cloud_dive                wind bed, thunder synced to the shot's lightning flashes
  glitch                    static burst, then a fading telemetry flat-line tone
  black                     near silence: a distant low settle
  fluid                     deep pressure hum; `metallic` adds sparse electric crackle
  collision                 impact boom at the flash
  title (cinematic / overlay) sub-boom hit
  HUD status appears        a soft telemetry blip
Levels are relative (peak ~0.5); the mixer sets the bus level.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _noise(n, rng, ch=2):
    return rng.standard_normal((n, ch)).astype(np.float32)


def _bp(x, lo, hi):
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def _lp(x, f, order=2):
    sos = butter(order, f, btype="low", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def _hp(x, f, order=2):
    sos = butter(order, f, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def _env(n, attack, release):
    a, r = int(attack * SR), int(release * SR)
    e = np.ones(n, np.float32)
    if a:
        e[:a] = np.linspace(0, 1, min(a, n), dtype=np.float32)[: min(a, n)]
    if r and r < n:
        e[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
    return e[:, None]


def _norm(x, peak=0.5):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def whoosh(dur, rng, rise=True):
    n = int(dur * SR)
    x = _noise(n, rng)
    # sweep a band-pass by filtering in chunks with a moving centre
    out = np.zeros_like(x)
    chunk = int(0.05 * SR)
    for i in range(0, n, chunk):
        u = i / n
        u = u if rise else 1 - u
        c = 200 + 3000 * u ** 2
        out[i:i + chunk] = _bp(x[i:i + chunk], c * 0.6, min(c * 1.6, SR / 2 - 100))
    env = np.sin(np.linspace(0, math.pi, n, dtype=np.float32)) ** 2
    return _norm(out * env[:, None], 0.35)


def roar(dur, rng, curve=None):
    """Entry plasma: dense low/mid noise with a heating swell, plus sub rumble and crackle."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    swell = (np.sin(np.minimum(t * 1.2, 1.0) * math.pi) ** 2) if curve is None else curve
    body = _lp(_noise(n, rng), 900, 4) * 1.2 + _bp(_noise(n, rng), 900, 3500) * 0.35
    sub = _lp(_noise(n, rng), 70, 4) * 4.0
    crack = (_noise(n, rng) * (rng.random((n, 1)) < 0.0015)).astype(np.float32)
    crack = _hp(crack, 1500) * 3
    x = (body + sub + crack) * swell[:, None]
    return _norm(x, 0.6) * _env(n, 0.3, 0.6)


def wind(dur, rng, strength=1.0):
    n = int(dur * SR)
    x = _bp(_noise(n, rng), 250, 1400)
    lfo = 0.6 + 0.4 * np.sin(np.linspace(0, dur * 0.7 * 2 * math.pi, n) + rng.uniform(0, 6))
    gust = 0.7 + 0.3 * np.sin(np.linspace(0, dur * 0.23 * 2 * math.pi, n) + rng.uniform(0, 6))
    low = _lp(_noise(n, rng), 120, 2) * 1.5
    return _norm((x * (lfo * gust)[:, None] + low) * strength, 0.4) * _env(n, 1.2, 1.2)


def thunder(rng, dur=4.0, near=True):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    crack = _hp(_noise(n, rng), 1200) * np.exp(-t * 18)[:, None] * (1.0 if near else 0.3)
    rumble = _lp(_noise(n, rng), 160, 4) * 5 * (np.exp(-t * 1.1) * (1 - np.exp(-t * 12)))[:, None]
    roll = _lp(_noise(n, rng), 400, 2) * (0.5 + 0.5 * np.sin(t * 9 + 1)) [:, None] * np.exp(-t * 1.6)[:, None]
    return _norm(crack + rumble + roll, 0.65)


def static_burst(dur, rng):
    n = int(dur * SR)
    x = _noise(n, rng)
    # bit-crush / sample-hold for a digital feel
    hold = 6
    x = np.repeat(x[::hold], hold, 0)[:n]
    x = np.round(x * 6) / 6
    gate = (rng.random(n // 1200 + 1) > 0.25).astype(np.float32)
    gate = np.repeat(gate, 1200)[:n][:, None]
    return _norm(_hp(x, 400) * gate * _env(n, 0.01, 0.25), 0.4)


def flatline(dur, f=1000.0):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    x = np.sin(2 * np.pi * f * t) * 0.12
    return np.stack([x, x], 1).astype(np.float32) * _env(n, 0.01, dur * 0.7)


def blip(f=1800.0, dur=0.07):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 40) * 0.12
    return np.stack([x, x], 1).astype(np.float32)


def boom(rng, dur=3.0, f0=55.0):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = f0 * (1 + 1.5 * np.exp(-t * 8))
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 1.4)
    hit = _lp(_noise(n, rng), 300, 2)[:, 0] * np.exp(-t * 6) * 0.6
    x = (sub + hit)
    return _norm(np.stack([x, x], 1).astype(np.float32), 0.7)


def hum(dur, rng, metallic=False):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    x = (np.sin(2 * np.pi * 38 * t) * 0.6 + np.sin(2 * np.pi * 57.3 * t) * 0.25)
    x = np.stack([x, x * 0.97], 1).astype(np.float32)
    x += _lp(_noise(n, rng), 200, 2) * 0.8
    x *= (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t))[:, None]
    if metallic:
        clicks = (rng.random((n, 1)) < 0.0004).astype(np.float32) * _noise(n, rng)
        x += _bp(clicks, 2500, 9000) * 8
    return _norm(x, 0.4) * _env(n, 1.5, 1.5)


def groan(rng, dur=3.0):
    """Hull stress: a low metallic groan (resonant filtered noise with a slowly bending pitch)."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 70 + 25 * np.sin(t * 1.3 + rng.uniform(0, 6)) + 40 * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.5 * np.sin(2.01 * ph) + 0.3 * np.sin(3.03 * ph)) * (0.6 + 0.4 * rng.random(n) ** 4)
    x = _bp(np.stack([tone, tone * 0.95], 1).astype(np.float32), 50, 900)
    env = np.clip(np.sin(np.linspace(0, np.pi, n, dtype=np.float32)), 0, 1) ** 1.5
    return _norm(x * env[:, None], 0.45)


def heartbeat(dur, bpm=96):
    """Low double-thump heartbeat for tension (lub-dub)."""
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    t = np.arange(int(0.25 * SR), dtype=np.float32) / SR
    thump = (np.sin(2 * np.pi * 48 * t) * np.exp(-t * 22)).astype(np.float32)
    period = 60.0 / bpm
    k = 0.0
    while k < dur:
        for off, g in ((0.0, 1.0), (0.22, 0.6)):
            i0 = int((k + off) * SR)
            i1 = min(i0 + len(thump), n)
            if i0 < n:
                out[i0:i1] += (thump[: i1 - i0] * g)[:, None]
        k += period
    return _norm(out, 0.5) * _env(n, 0.8, 1.0)


def riser(rng, dur=1.6):
    """Tension riser: noise + tone sweeping up and swelling, cut dead at the end (the reveal lands on silence+hit)."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    u = t / dur
    f = 180 * (1 + 5 * u ** 2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.4 + np.sin(ph * 1.5) * 0.2
    x = np.stack([tone, tone], 1).astype(np.float32)
    noise = _noise(n, rng)
    out = np.zeros_like(noise)
    chunk = int(0.04 * SR)
    for i in range(0, n, chunk):
        c = 400 + 5000 * (i / n) ** 2
        out[i:i + chunk] = _bp(noise[i:i + chunk], c * 0.7, min(c * 1.4, SR / 2 - 100))
    env = (u ** 2.2)[:, None]
    return _norm((x + out * 0.8) * env, 0.45)


def impact(rng, dur=2.5):
    """Cinematic hit for reveals: sub drop + short transient + airy tail."""
    b = boom(rng, dur, 50.0)
    n = len(b)
    t = np.arange(n, dtype=np.float32) / SR
    trans = _hp(_noise(n, rng), 2000) * np.exp(-t * 40)[:, None] * 0.6
    tail = _bp(_noise(n, rng), 300, 2500) * np.exp(-t * 2.2)[:, None] * 0.15
    return _norm(b + trans + tail, 0.7)


def _add(track, clip, at_s, gain=1.0):
    i0 = int(at_s * SR)
    if i0 >= len(track):
        return
    i1 = min(i0 + len(clip), len(track))
    track[i0:i1] += clip[: i1 - i0] * gain


def design(beats: list[dict], total_s: float, seed: int = 11) -> np.ndarray:
    from ytauto.visuals import shots
    rng = np.random.default_rng(seed)
    out = np.zeros((int(total_s * SR) + SR, 2), np.float32)
    prev_status = None
    for b in beats:
        st, en = b["start"], b["end"]
        dur = en - st
        typ, shot = b["type"], b.get("shot")
        p = b.get("params") or {}
        if typ == "r3d":
            if shot in ("approach",) or (shot == "orbit" and p.get("streak")):
                _add(out, whoosh(min(dur, 6.0), rng), st + max(dur - 6.0, 0) * 0.5, 0.7)
            if shot == "entry":
                _add(out, roar(dur + 0.5, rng), st, 2.2)
            if shot == "cloud_dive":
                _add(out, wind(dur + 1.0, rng, 1.0), st - 0.3, 0.8)
                for ft in shots.lightning_times(dur, **p):
                    delay = rng.uniform(0.15, 0.6)   # sound arrives just after the flash
                    _add(out, thunder(rng, near=rng.random() < 0.6), st + ft + delay, 0.9)
            if shot == "fluid":
                _add(out, hum(dur + 1.0, rng, metallic=p.get("mode") == "metallic"), st - 0.3, 0.8)
                if b.get("shake"):
                    _add(out, groan(rng, min(dur, 3.5)), st + 0.3, 0.9)
            if shot == "collision":
                _add(out, boom(rng, 4.0, 42.0), st + 0.7 * dur, 1.0)
                _add(out, whoosh(min(0.7 * dur, 4.0), rng), st + 0.7 * dur - min(0.7 * dur, 4.0), 0.5)
            if b.get("title"):
                _add(out, boom(rng, 3.5), st + 0.35, 0.8)
        elif typ == "glitch":
            _add(out, static_burst(1.1, rng), st, 1.0)
            _add(out, flatline(min(dur - 1.0, 3.5)), st + 1.0, 1.0)
        elif typ == "title" and b.get("style") == "cinematic":
            _add(out, boom(rng, 3.5), st + 0.35, 0.8)
        elif typ == "black":
            _add(out, boom(rng, 4.0, 30.0) * 0.3, st + 0.3, 0.6)
        # reveals: riser into fact cards, landing on an impact; a deep hit on every new chapter
        if typ == "fact":
            _add(out, riser(rng, 1.4), max(st - 1.4, 0), 0.8)
            _add(out, impact(rng), st, 0.9)
        if b.get("first_in_scene") and b.get("chapter"):
            _add(out, impact(rng, 3.0) * 0.8, st + 0.2, 0.8)
        elif typ in ("r3d", "image", "video") and not b.get("first_in_scene"):
            _add(out, whoosh(0.9, rng), max(st - 0.45, 0), 0.25)
        if b.get("heartbeat"):
            _add(out, heartbeat(dur + 0.5, 92 + 20 * float(b.get("heartbeat"))), st, 1.0)
        status = (b.get("hud") or {}).get("status")
        if status and status != prev_status:
            _add(out, blip(), st + 0.2, 1.0)
            _add(out, blip(2400.0), st + 0.32, 0.8)
        prev_status = status
    return np.nan_to_num(out[: int(total_s * SR)])
