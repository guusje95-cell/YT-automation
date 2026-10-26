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


# ----------------------------------------------------------------- licensed score (cue sheet)
MUSIC_DIR_NAME = "music"
ESO_URL = "https://www.eso.org/public/archives/music/wav/{id}.wav"
ESO_PAGE = "https://www.eso.org/public/products/music/{id}/"


def track_path(track_id: str):
    from ytauto.core import config
    return config.CACHE_DIR / MUSIC_DIR_NAME / f"{track_id}.wav"


def ensure_track(track_id: str):
    """Download an ESO Music Archive track (CC BY 4.0) into the cache if missing."""
    import requests
    p = track_path(track_id)
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(ESO_URL.format(id=track_id), timeout=120)
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def track_credit(track_id: str) -> str:
    """Credit line for a track. Only ESO's zero-project tracks are supported (CC BY 4.0, ESO Music Archive)."""
    if not track_id.startswith("zero-project-"):
        raise ValueError(f"no licence record for music track {track_id}")
    name = track_id.removeprefix("zero-project-").replace("-", " ").title()
    return (f"\"{name}\" by zero-project (zero-project.gr), via the ESO Music Archive, CC BY 4.0 "
            f"(edited: excerpted, faded, mixed under narration) — {ESO_PAGE.format(id=track_id)}")


def _load_track(track_id: str, sr: int) -> np.ndarray:
    import soundfile as sf
    from scipy.signal import resample_poly
    x, tsr = sf.read(ensure_track(track_id), dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    if tsr != sr:
        from math import gcd
        g = gcd(sr, tsr)
        x = resample_poly(x, sr // g, tsr // g, axis=0).astype(np.float32)
    return x[:, :2]


def cue_bed(cues: list[dict], scene_starts: dict[str, float], total_s: float, sr: int = SR,
            xfade_s: float = 3.0) -> tuple[np.ndarray, list[dict]]:
    """Assemble a stereo score from a cue sheet.

    Each cue: {scene, track, offset (s into the track), gain_db (LU relative to the voice target)}.
    A cue starts at its scene's start and plays until the next cue; `track: silence` makes a hard stop
    (used for dramatic beats). Tracks shorter than their slot loop with a crossfade. Returns (bed, placed)
    where `bed` is NOT loudness-normalised per cue: each cue carries its own `gain_db` applied by the mixer
    through the returned per-sample gain track in placed[i]['gain_db'].
    """
    import pyloudnorm as pyln
    n = int(total_s * sr)
    bed = np.zeros((n, 2), np.float32)
    meter = pyln.Meter(sr)
    placed = []
    starts = []
    for c in cues:
        st = 0.0 if not starts else scene_starts[c["scene"]]
        starts.append(st)
    for k, c in enumerate(cues):
        st = starts[k]
        en = starts[k + 1] if k + 1 < len(cues) else total_s
        if c["track"] == "silence":
            placed.append({**c, "start": st, "end": en})
            continue
        silent_next = k + 1 < len(cues) and cues[k + 1]["track"] == "silence"
        tail = 0.08 if silent_next else xfade_s
        seg_len = int((en - st + tail) * sr)
        x = _load_track(c["track"], sr)
        off = int(c.get("offset", 0) * sr)
        src = x[off:]
        while len(src) < seg_len:  # loop with a crossfade
            f = int(2.0 * sr)
            r = np.linspace(0, 1, f, dtype=np.float32)[:, None]
            src = np.concatenate([src[:-f], src[-f:] * (1 - r) + x[off:off + f] * r, x[off + f:]])
        seg = src[:seg_len].copy()
        lufs = meter.integrated_loudness(seg) if len(seg) > sr * 0.5 else -30.0
        seg *= 10 ** ((c.get("gain_db", -22.0) - (lufs + 14.0)) / 20)  # relative to a -14 LUFS voice
        fin = int((0.05 if k == 0 and c.get("offset", 0) == 0 else (xfade_s if k else 1.5)) * sr)
        fin = min(fin, len(seg) // 3)
        fo = min(int(tail * sr), len(seg) // 3)
        if fin:
            seg[:fin] *= np.linspace(0, 1, fin, dtype=np.float32)[:, None]
        if fo:
            seg[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
        i0 = int(st * sr)
        i1 = min(i0 + len(seg), n)
        bed[i0:i1] += seg[: i1 - i0]
        placed.append({**c, "start": st, "end": en})
    # end of film: fade the score out over the last 4 s
    f = min(int(4 * sr), n)
    bed[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    return bed, placed
