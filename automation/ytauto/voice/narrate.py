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


def _synth_checked(provider, text: str, tries: int = 4):
    best = None
    words = max(len(text.split()), 1)
    for k in range(tries if provider.name == "chatterbox" else 1):
        x, sr = provider.synthesize(text)
        x = tts.trim_silence(x, sr)
        ratio = len(x) / sr / (words * SEC_PER_WORD + 0.4)
        if best is None or abs(ratio - 1) < abs(best[2] - 1):
            best = (x, sr, ratio)
        if 0.45 < ratio < MAX_RATIO:
            break
        log.warning("clip length off (ratio %.2f) for %r; retrying with a new seed", ratio, text[:60])
    return best[0], best[1]


def build(spec) -> dict:
    vcfg = dict(config.get("voice", {}))
    vcfg.update(spec.data.get("voice") or {})
    gaps = {k: vcfg.pop(k) for k in ("sentence_gap_s", "paragraph_gap_s", "scene_gap_s") if k in vcfg}
    provider = tts.get_provider(vcfg)
    lexicon = spec.data.get("lexicon") or {}
    cache = spec.build / "tts"
    cache.mkdir(exist_ok=True)
    sig = json.dumps(vcfg, sort_keys=True)

    sr = tts.SR
    pieces, t = [], 0.0
    lead_in = 0.4
    pieces.append(np.zeros(int(lead_in * sr), np.float32))
    t += lead_in
    scenes_out = []
    for si, sc in enumerate(spec.scenes):
        sentences = tts.split_sentences(sc["narration"])
        s_start = t
        sent_out = []
        for k, text in enumerate(sentences):
            spoken = tts.pronounce(text, lexicon)
            key = hashlib.sha1((sig + "|" + spoken).encode()).hexdigest()[:16]
            clip_path = cache / f"{key}.wav"
            if clip_path.exists():
                x, csr = sf.read(clip_path, dtype="float32")
            else:
                x, csr = _synth_checked(provider, spoken)
                tts.write_wav(clip_path, x, csr)
            if csr != sr:
                raise RuntimeError(f"unexpected sample rate {csr}")
            sent_out.append({"text": text, "start": round(t, 3), "end": round(t + len(x) / sr, 3)})
            pieces.append(x)
            t += len(x) / sr
            if k < len(sentences) - 1:
                gap = gaps.get("sentence_gap_s", 0.28)
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
