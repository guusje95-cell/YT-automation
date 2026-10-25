"""Background music.

Default: a procedurally generated ambient pad (slow chord progression of
detuned, low-passed sine/triangle voices). It is synthesized locally from
code, so there is no licence to track and no Content ID claim risk. Licensed
tracks can be used instead via `music.track` in a video spec, but must carry a
provenance entry (see visuals/assets.py manifest).
"""
from __future__ import annotations

import numpy as np

SR = 48000

# Chord progressions as semitone offsets from the root (minor-ish, calm, documentary).
PROGRESSIONS = {
    "calm": [[0, 7, 15, 19], [-4, 3, 8, 15], [-7, 0, 5, 12], [-2, 5, 10, 14]],
    "wonder": [[0, 7, 14, 16], [-3, 4, 9, 16], [-5, 2, 7, 14], [-7, 0, 9, 12]],
    "tension": [[0, 3, 7, 10], [-1, 3, 6, 11], [-4, 0, 3, 8], [-2, 1, 5, 10]],
}


def ambient_bed(duration_s: float, mood: str = "calm", root_hz: float = 110.0,
                chord_s: float = 8.0, seed: int = 7) -> np.ndarray:
    """Return a stereo float32 array (n, 2) at 48 kHz, peak-normalised to -1 dBFS."""
    rng = np.random.default_rng(seed)
    prog = PROGRESSIONS.get(mood, PROGRESSIONS["calm"])
    n = int(duration_s * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    n_chords = int(np.ceil(duration_s / chord_s)) + 1
    xfade = chord_s * 0.5
    for c in range(n_chords):
        start = c * chord_s - xfade / 2
        end = start + chord_s + xfade
        i0, i1 = max(int(start * SR), 0), min(int(end * SR), n)
        if i0 >= i1:
            continue
        tt = t[i0:i1]
        local = (tt - start) / (end - start)
        env = np.sin(np.pi * np.clip(local, 0, 1)) ** 1.5  # smooth swell per chord
        chord = prog[c % len(prog)]
        for k, semi in enumerate(chord):
            f = root_hz * 2 ** (semi / 12)
            for side, det in ((0, -0.15), (1, 0.15)):
                ph = rng.uniform(0, 2 * np.pi)
                wave = np.sin(2 * np.pi * (f + det) * tt + ph)
                wave += 0.25 * np.sin(2 * np.pi * 2 * (f + det) * tt + ph)  # soft 2nd harmonic
                trem = 0.85 + 0.15 * np.sin(2 * np.pi * (0.07 + 0.02 * k) * tt + ph)
                out[i0:i1, side] += (wave * env * trem / (k + 1.5)).astype(np.float32)
    # gentle sub drone on root
    drone = 0.35 * np.sin(2 * np.pi * root_hz / 2 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.03 * t))
    out += drone[:, None].astype(np.float32)
    # air: very quiet filtered noise
    noise = rng.normal(0, 1, (n // 8 + 1, 2)).astype(np.float32)
    noise = np.repeat(noise, 8, axis=0)[:n] * 0.01
    out += noise
    # fade in/out
    fade = min(int(3 * SR), n // 4)
    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    out[:fade] *= ramp
    out[-fade:] *= ramp[::-1]
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak * 0.89).astype(np.float32)
