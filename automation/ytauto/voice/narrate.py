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


_NUMBER_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                    "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety "
                    "hundred thousand million billion and a".split())
_SPELLING = {"kilometres": "kilometers", "metres": "meters", "centre": "center", "tonnes": "tons"}


def _asr_words(text: str, numbers: bool) -> list[str]:
    import re
    ws = re.findall(r"[a-z']+|\d[\d,.]*", text.lower().replace("-", " "))
    ws = [_SPELLING.get(w, w) for w in ws]
    if numbers:  # drop numerals and number words: ASR writes "170,000" for "one hundred and seventy thousand"
        ws = [w for w in ws if not w[0].isdigit() and w not in _NUMBER_WORDS]
    return ws


class AsrJudge:
    """Checks each synthesised clip with Whisper: a clip the recogniser can't follow is re-synthesised.
    Catches mumbled short lines and invented words, which duration checks alone miss."""

    def __init__(self, model_size: str = "small.en"):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(model_size, device="cpu", compute_type="int8",
                              download_root=str(config.MODELS_DIR / "whisper"))

    def score(self, x: np.ndarray, sr: int, text: str) -> float:
        import difflib
        from scipy.signal import resample_poly
        a = resample_poly(np.concatenate([np.zeros(sr // 5, np.float32), x, np.zeros(sr // 5, np.float32)]),
                          16000 // 8000, sr // 8000).astype(np.float32)
        hyp = " ".join(z.text for z in self.m.transcribe(a, language="en", beam_size=3)[0])
        ref_w, hyp_w = _asr_words(tts.strip_tags(text), True), _asr_words(hyp, True)
        if not ref_w:
            return 1.0
        return difflib.SequenceMatcher(a=ref_w, b=hyp_w, autojunk=False).ratio()


def _synth_checked(provider, text: str, tries: int = 4, judge: "AsrJudge | None" = None, ref: str | None = None,
                   **over):
    """`ref` is the written form the judge listens for (the lexicon respells names for the TTS only)."""
    best = None
    words = max(len(tts.strip_tags(text).split()), 1)
    for k in range(tries if provider.name == "chatterbox" else 1):
        x, sr = provider.synthesize(text, **over) if over else provider.synthesize(text)
        x = tts.trim_silence(x, sr)
        ratio = len(x) / sr / (words * SEC_PER_WORD + 0.4)
        length_ok = 0.45 < ratio < MAX_RATIO
        heard = judge.score(x, sr, ref or text) if judge and length_ok else (1.0 if length_ok else 0.0)
        quality = heard - (0 if length_ok else 1)
        if best is None or quality > best[2]:
            best = (x, sr, quality)
        if length_ok and heard >= 0.8:
            break
        log.warning("clip rejected (length ratio %.2f, ASR match %.2f) for %r; retrying with a new seed",
                    ratio, heard, text[:60])
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
    from ytauto.spec import lines
    vcfg = dict(config.get("voice", {}))
    vcfg.update(spec.data.get("voice") or {})
    gaps = {k: vcfg.pop(k) for k in ("sentence_gap_s", "paragraph_gap_s", "scene_gap_s", "speaker_gap_s") if k in vcfg}
    asr_check = vcfg.pop("asr_check", True)
    provider = tts.get_provider(vcfg)
    judge = None
    if asr_check and provider.name == "chatterbox":
        try:
            judge = AsrJudge()
        except ImportError:
            log.warning("faster-whisper not installed: clips are not ASR-checked")
    voices = spec.data.get("voices") or {}
    emotions = spec.data.get("emotions") or {}
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
        sentences = [(who, text, emo) for who, seg, emo in lines(sc["narration"]) for text in tts.split_sentences(seg)]
        for k, (who, text, emo) in enumerate(sentences):
            vo = dict(voices.get(who) or {})
            fx = vo.pop("radio", False)
            over = {kk: v for kk, v in vo.items() if kk in SPEAKER_KEYS}
            prefix = ""
            if emo:
                if emo not in emotions:
                    raise ValueError(f"unknown emotion [{emo}] in scene {sc['id']}")
                emo_cfg = dict(emotions[emo])
                prefix = emo_cfg.pop("tag", "")      # Turbo style tag, e.g. "[fear]"
                over.update({kk: v for kk, v in emo_cfg.items() if kk in SPEAKER_KEYS})
            sig = json.dumps({**vcfg, **over}, sort_keys=True)
            spoken = (prefix + " " if prefix else "") + tts.pronounce(text, lexicon)
            key = hashlib.sha1((sig + "|" + spoken).encode()).hexdigest()[:16]
            clip_path = cache / f"{key}.wav"
            if clip_path.exists():
                x, csr = sf.read(clip_path, dtype="float32")
                ok_mark = clip_path.with_suffix(".ok")
                if judge and not ok_mark.exists():   # audit clips made before the ASR check existed
                    if judge.score(x, csr, text) < 0.6:
                        log.warning("cached clip fails ASR check, re-synthesising: %r", spoken[:60])
                        x, csr = _synth_checked(provider, spoken, judge=judge, ref=text, **over)
                        tts.write_wav(clip_path, x, csr)
                    ok_mark.touch()
            else:
                x, csr = _synth_checked(provider, spoken, judge=judge, ref=text, **over)
                tts.write_wav(clip_path, x, csr)
                if judge:
                    clip_path.with_suffix(".ok").touch()
            if csr != sr:
                raise RuntimeError(f"unexpected sample rate {csr}")
            n_clip += 1
            if fx:
                x = radio(x, sr, seed=n_clip)
            sent_out.append({"text": tts.strip_tags(text), "who": who, "emotion": emo, "start": round(t, 3), "end": round(t + len(x) / sr, 3)})
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
