"""Text-to-speech providers.

Each provider turns a list of sentences into per-sentence WAV clips so that
captions and visual cuts can be timed exactly from clip durations (no forced
alignment needed). Add a provider by implementing `synthesize(text) -> (samples, sr)`.

- kokoro   : local Kokoro-82M ONNX (Apache-2.0 weights). Free, runs on CPU.
- elevenlabs: optional paid upgrade (needs ELEVENLABS_API_KEY). Not used unless configured.
"""
from __future__ import annotations

import io
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

from ytauto.core import config
from ytauto.core.log import get_logger
from ytauto.core.retry import retry

log = get_logger(__name__)

SR = 24000


class KokoroTTS:
    name = "kokoro"

    def __init__(self, voice: str = "bm_george", speed: float = 1.0, lang: str = "en-gb"):
        from kokoro_onnx import Kokoro
        m = config.MODELS_DIR
        if not (m / "kokoro-v1.0.onnx").exists():
            raise RuntimeError("Kokoro model missing; run scripts/fetch_models.sh")
        self.k = _kokoro(str(m / "kokoro-v1.0.onnx"), str(m / "voices-v1.0.bin"))
        self.voice, self.speed, self.lang = voice, speed, lang

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        samples, sr = self.k.create(text, voice=self.voice, speed=self.speed, lang=self.lang)
        return samples.astype(np.float32), sr


@lru_cache
def _kokoro(model: str, voices: str):
    from kokoro_onnx import Kokoro
    return Kokoro(model, voices)


class ElevenLabsTTS:
    name = "elevenlabs"

    def __init__(self, voice: str, model: str = "eleven_multilingual_v2", **_):
        self.key = config.secret("ELEVENLABS_API_KEY", required=True)
        self.voice, self.model = voice, model

    @retry(attempts=4, base_delay=2.0)
    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        import requests
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}?output_format=pcm_24000",
            headers={"xi-api-key": self.key}, json={"text": text, "model_id": self.model}, timeout=120)
        r.raise_for_status()
        pcm = np.frombuffer(r.content, dtype="<i2").astype(np.float32) / 32768.0
        return pcm, 24000


class ChatterboxTTS:
    """Expressive local TTS (Resemble AI Chatterbox, MIT) via a persistent worker in its own venv.

    `ref` is a reference clip whose timbre is cloned. We use a *synthetic* reference (generated with
    Kokoro) so the channel voice never imitates a real person.
    """
    name = "chatterbox"

    def __init__(self, ref: str | None = None, exaggeration: float = 0.5, cfg_weight: float = 0.35,
                 temperature: float = 0.75, python: str = "/root/venvs/cbx/bin/python", seed: int = 1234, **_):
        import json as _json
        import os
        import subprocess
        self.exaggeration, self.cfg_weight, self.temperature, self.seed = exaggeration, cfg_weight, temperature, seed
        env = dict(os.environ)
        if ref:
            ref_path = Path(ref) if Path(ref).is_absolute() else config.ROOT / ref
            env["CBX_REF"] = str(ref_path)
        env["CBX_EXAG"] = str(exaggeration)
        worker = Path(__file__).with_name("chatterbox_worker.py")
        self.proc = subprocess.Popen([python, str(worker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, env=env, bufsize=1)
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("chatterbox worker failed to start (is the venv installed? see docs/SETUP.md)")
            try:
                if _json.loads(line).get("ready"):
                    break
            except ValueError:
                continue
        self._json = _json
        self._n = 0

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        import tempfile
        self._n += 1
        out = Path(tempfile.gettempdir()) / f"cbx_{os.getpid()}_{self._n}.wav"
        req = {"text": text, "out": str(out), "exaggeration": self.exaggeration, "cfg_weight": self.cfg_weight,
               "temperature": self.temperature, "seed": self.seed + self._n}
        self.proc.stdin.write(self._json.dumps(req) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("chatterbox worker exited")
            try:
                res = self._json.loads(line)
                break
            except ValueError:
                continue
        if not res.get("ok"):
            raise RuntimeError(res.get("error"))
        x, sr = sf.read(out, dtype="float32")
        out.unlink(missing_ok=True)
        if x.ndim > 1:
            x = x.mean(1)
        return x, sr

    def __del__(self):
        try:
            self.proc.stdin.close()
            self.proc.terminate()
        except Exception:
            pass


PROVIDERS = {"kokoro": KokoroTTS, "elevenlabs": ElevenLabsTTS, "chatterbox": ChatterboxTTS}


_NON_PROVIDER_KEYS = {"sentence_gap_s", "paragraph_gap_s", "scene_gap_s"}


def get_provider(spec_voice: dict | None = None):
    """Build the TTS provider from settings.yaml `voice`, overridden by a spec's `voice` block."""
    cfg = dict(config.get("voice", {}) or {})
    cfg.update(spec_voice or {})
    for k in _NON_PROVIDER_KEYS:
        cfg.pop(k, None)
    name = cfg.pop("provider", "kokoro")
    return PROVIDERS[name](**cfg)


_ABBREV = re.compile(r"\b(Mr|Mrs|Ms|Dr|St|vs|etc|e\.g|i\.e|approx|Jr|Sr|No)\.$", re.I)


def split_sentences(text: str) -> list[str]:
    """Sentence splitter that keeps abbreviations and decimals intact."""
    text = re.sub(r"\s+", " ", text.strip())
    parts, buf = [], ""
    for tok in re.split(r"(?<=[.!?])\s+", text):
        buf = f"{buf} {tok}".strip() if buf else tok
        if _ABBREV.search(buf):
            continue
        parts.append(buf)
        buf = ""
    if buf:
        parts.append(buf)
    return [p for p in parts if p]


def pronounce(text: str, lexicon: dict[str, str]) -> str:
    """Apply a spoken-form lexicon (e.g. 'km' -> 'kilometres') before synthesis."""
    for k, v in lexicon.items():
        text = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", v, text)
    return text


def trim_silence(x: np.ndarray, sr: int, thresh: float = 0.01, pad_s: float = 0.04) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(pad_s * sr)
    return x[max(idx[0] - pad, 0): min(idx[-1] + pad, len(x))]


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, x, sr, subtype="PCM_16")
