"""Final audio mix: narration + ducked music bed, loudness-normalised with a true-peak limiter."""
from __future__ import annotations

import json

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import resample_poly

from ytauto.audio import music
from ytauto.core import config
from ytauto.core.log import get_logger

log = get_logger(__name__)

SR = 48000


def db(x: float) -> float:
    return 10 ** (x / 20)


def _voice_activity(v: np.ndarray, sr: int) -> np.ndarray:
    """0..1 envelope of speech presence with ~80 ms attack / ~600 ms release."""
    win = int(0.05 * sr)
    rms = np.sqrt(uniform_filter1d(v ** 2, win) + 1e-12)
    active = (rms > 0.01).astype(np.float32)
    held = maximum_filter1d(active, int(0.35 * sr))  # bridge short gaps between words
    return np.clip(uniform_filter1d(held, int(0.3 * sr)), 0, 1)


def limiter(x: np.ndarray, ceiling_db: float, sr: int) -> np.ndarray:
    """Look-ahead peak limiter on 4x oversampled peaks (approximates true peak)."""
    ceiling = db(ceiling_db)
    chans = x if x.ndim == 2 else x[:, None]
    n = len(chans)
    peak = np.zeros(n, np.float32)
    for c in range(chans.shape[1]):
        up = np.abs(resample_poly(chans[:, c], 4, 1)).astype(np.float32)[: n * 4]
        peak = np.maximum(peak, up.reshape(-1, 4).max(axis=1))
    look = int(0.005 * sr)
    env = maximum_filter1d(peak, 2 * look + 1)            # look-ahead: react before the peak
    need = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))
    release = uniform_filter1d(need, int(0.05 * sr))       # smooth recovery
    gain = np.minimum(need, release)                       # never exceed what the peak requires
    return x * (gain[:, None] if x.ndim == 2 else gain)


def build(spec) -> dict:
    v, vsr = sf.read(spec.build / "narration.wav", dtype="float32")
    voice = resample_poly(v, SR // 8000, vsr // 8000).astype(np.float32)  # 24k -> 48k
    n = len(voice)
    mcfg = spec.data.get("music") or {}
    acfg = config.get("audio")
    target, tp = acfg["target_lufs"], acfg["true_peak_db"]
    meter = pyln.Meter(SR)

    # normalise voice alone to target first, so music level is relative to final speech level
    vl = meter.integrated_loudness(voice)
    voice *= db(target - vl)
    stereo_voice = np.stack([voice, voice], 1)

    mix = stereo_voice.copy()
    act = _voice_activity(voice, SR)
    credits = []
    if mcfg.get("cues"):
        timings = json.loads((spec.build / "timings.json").read_text())
        starts = {sc["id"]: sc["start"] for sc in timings["scenes"]}
        bed, placed = music.cue_bed(mcfg["cues"], starts, n / SR, SR)
        duck = db(mcfg.get("duck_db", acfg["music_duck_db"]))
        mix = mix + bed[:n] * ((1 - act) + act * duck)[:, None]
        credits = sorted({music.track_credit(c["track"]) for c in mcfg["cues"] if c["track"] != "silence"})
    elif mcfg.get("enabled", True):
        bed = music.ambient_bed(n / SR + 0.1, mood=mcfg.get("mood", "calm"), seed=mcfg.get("seed", 7))
        if music.SR != SR:
            bed = resample_poly(bed, SR, music.SR, axis=0).astype(np.float32)
        bed = bed[:n]
        bl = meter.integrated_loudness(bed)
        bed *= db(target + mcfg.get("gain_db", acfg["music_gain_db"]) - bl)
        duck = db(acfg["music_duck_db"])
        gain = (1 - act) + act * duck
        mix = stereo_voice + bed * gain[:, None]
    scfg = spec.data.get("sfx") or {}
    if scfg.get("enabled", any(b.get("type") == "r3d" for sc in spec.scenes for b in sc["beats"])):
        from ytauto.audio import sfx
        from ytauto.video import timeline
        timings = json.loads((spec.build / "timings.json").read_text())
        fx = sfx.design(timeline.build(spec, timings), n / SR)[:n]
        fx_duck = db(scfg.get("duck_db", -4.0))
        mix = mix + fx * db(scfg.get("gain_db", -6.0)) * ((1 - act) + act * fx_duck)[:, None]
    (spec.build / "music_credits.json").write_text(json.dumps(credits, indent=1))

    ml = meter.integrated_loudness(mix)
    mix *= db(target - ml)
    mix = limiter(mix, tp - 1.2, SR)   # headroom for AAC encoder overshoot
    final_lufs = meter.integrated_loudness(mix)
    peak_db = 20 * np.log10(np.max(np.abs(mix)) + 1e-12)
    out = spec.build / "mix.wav"
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    stats = {"lufs": round(float(final_lufs), 2), "sample_peak_db": round(float(peak_db), 2), "duration": round(n / SR, 3)}
    (spec.build / "mix_stats.json").write_text(json.dumps(stats))
    log.info("mix: %s", stats)
    return stats
