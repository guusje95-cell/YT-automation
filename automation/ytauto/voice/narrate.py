"""Build the narration track and the timing map.

Output (in content/<id>/build/):
  narration.wav   mono, 24 kHz, unnormalised
  timings.json    {"sr", "duration", "scenes": [{id, start, end, sentences: [{text, start, end}]}]}

Per-sentence clips are cached by a hash of (text, voice settings) so editing one
sentence only re-synthesises that sentence.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import soundfile as sf

from ytauto.core import config
from ytauto.core.log import get_logger
from ytauto.voice import tts

log = get_logger(__name__)


# Expressive (sampling) TTS models occasionally repeat a phrase or ramble. A clip far longer than its word
# count predicts is re-synthesised with a new seed; deterministic providers are trusted as-is.
SEC_PER_WORD = 0.36
MAX_RATIO = 1.75


def _synth_checked(provider, text: str, tries: int = 4, **over):
    best = None
    words = max(len(text.split()), 1)
    for k in range(tries if provider.name == "chatterbox" else 1):
        x, sr = provider.synthesize(text, **over) if over else provider.synthesize(text)
        x = tts.trim_silence(x, sr)
        ratio = len(x) / sr / (words * SEC_PER_WORD + 0.4)
        if best is None or abs(ratio - 1) < abs(best[2] - 1):
            best = (x, sr, ratio)
        if 0.45 < ratio < MAX_RATIO:
            break
        log.warning("clip length off (ratio %.2f) for %r; retrying with a new seed", ratio, text[:60])
    return best[0], best[1]


def radio(x: np.ndarray, sr: int, seed: int = 0) -> np.ndarray:
    """Spacecraft-radio voice: band-limited, lightly saturated, with a faint hiss and squelch clicks at both ends."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(seed)
    sos = butter(4, [320, 3300], btype="band", fs=sr, output="sos")
    y = sosfilt(sos, x).astype(np.float32)
    y = np.tanh(y * 2.2) / np.tanh(2.2)
    hiss = sosfilt(butter(2, [1500, 6000], btype="band", fs=sr, output="sos"), rng.standard_normal(len(y)))
    y = y * 0.9 + (hiss * 0.012).astype(np.float32)
    click = (rng.standard_normal(int(0.03 * sr)) * np.exp(-np.linspace(0, 6, int(0.03 * sr))) * 0.25).astype(np.float32)
    pad = np.zeros(int(0.05 * sr), np.float32)
    return np.concatenate([click, pad, y, pad, click * 0.7]).astype(np.float32)


SPEAKER_KEYS = {"ref", "exaggeration", "cfg_weight", "temperature"}


def build(spec) -> dict:
    from ytauto.spec import segments
    vcfg = dict(config.get("voice", {}))
    vcfg.update(spec.data.get("voice") or {})
    gaps = {k: vcfg.pop(k) for k in ("sentence_gap_s", "paragraph_gap_s", "scene_gap_s", "speaker_gap_s") if k in vcfg}
    provider = tts.get_provider(vcfg)
    voices = spec.data.get("voices") or {}
    lexicon = spec.data.get("lexicon") or {}
    cache = spec.build / "tts"
    cache.mkdir(exist_ok=True)

    sr = tts.SR
    pieces, t = [], 0.0
    lead_in = 0.4
    pieces.append(np.zeros(int(lead_in * sr), np.float32))
    t += lead_in
    scenes_out = []
    n_clip = 0
    for si, sc in enumerate(spec.scenes):
        s_start = t
        sent_out = []
        sentences = [(who, text) for who, seg in segments(sc["narration"]) for text in tts.split_sentences(seg)]
        for k, (who, text) in enumerate(sentences):
            vo = dict(voices.get(who) or {})
            fx = vo.pop("radio", False)
            over = {kk: v for kk, v in vo.items() if kk in SPEAKER_KEYS}
            sig = json.dumps({**vcfg, **over}, sort_keys=True)
            spoken = tts.pronounce(text, lexicon)
            key = hashlib.sha1((sig + "|" + spoken).encode()).hexdigest()[:16]
            clip_path = cache / f"{key}.wav"
            if clip_path.exists():
                x, csr = sf.read(clip_path, dtype="float32")
            else:
                x, csr = _synth_checked(provider, spoken, **over)
                tts.write_wav(clip_path, x, csr)
            if csr != sr:
                raise RuntimeError(f"unexpected sample rate {csr}")
            n_clip += 1
            if fx:
                x = radio(x, sr, seed=n_clip)
            sent_out.append({"text": text, "who": who, "start": round(t, 3), "end": round(t + len(x) / sr, 3)})
            pieces.append(x)
            t += len(x) / sr
            if k < len(sentences) - 1:
                gap = gaps.get("sentence_gap_s", 0.28)
                if sentences[k + 1][0] != who:   # a beat of air when the speaker changes
                    gap += gaps.get("speaker_gap_s", 0.35)
                pieces.append(np.zeros(int(gap * sr), np.float32))
                t += gap
        scenes_out.append({"id": sc["id"], "chapter": sc.get("chapter"), "start": round(s_start, 3),
                           "end": round(t, 3), "sentences": sent_out})
        gap = gaps.get("scene_gap_s", 0.9) if si < len(spec.scenes) - 1 else 1.5
        pieces.append(np.zeros(int(gap * sr), np.float32))
        t += gap
        log.info("narrated scene %s: %d sentences, %.1fs", sc["id"], len(sentences), scenes_out[-1]["end"] - s_start)
    audio = np.concatenate(pieces)
    sf.write(spec.build / "narration.wav", audio, sr, subtype="PCM_16")
    timings = {"sr": sr, "duration": round(len(audio) / sr, 3), "scenes": scenes_out}
    (spec.build / "timings.json").write_text(json.dumps(timings, indent=1))
    log.info("narration total %.1fs", timings["duration"])
    return timings
