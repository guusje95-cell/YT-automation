"""Captions (SRT + WebVTT) from per-sentence narration timings.

Sentences are packed into lines of at most 42 characters, two lines per cue;
cue time is shared in proportion to characters.
"""
from __future__ import annotations

import json
import re

MAX_LINE = 42


def _lines(text: str) -> list[str]:
    """Greedy-pack words into lines of at most MAX_LINE characters."""
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if len(trial) > MAX_LINE and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _cues_for_sentence(text: str) -> list[str]:
    """Two lines per cue; avoid a lone short last line by rebalancing the final pair."""
    ls = _lines(text)
    cues = ["\n".join(ls[i:i + 2]) for i in range(0, len(ls), 2)]
    if len(ls) % 2 == 1 and len(ls) > 2 and len(ls[-1]) < 12:
        # merge the orphan into the previous cue by re-packing the last three lines into two
        tail = " ".join(ls[-3:])
        rel = _lines(tail)
        if len(rel) <= 2:
            cues = cues[:-2] + ["\n".join(rel)]
    return cues


def _ts(t: float, sep: str = ",") -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)) % 1000:03d}"


def cues(timings: dict) -> list[tuple[float, float, str]]:
    out = []
    for sc in timings["scenes"]:
        for s in sc["sentences"]:
            parts = _cues_for_sentence(s["text"])
            total = sum(len(p) for p in parts)
            t = s["start"]
            for p in parts:
                d = (s["end"] - s["start"]) * len(p) / total
                out.append((t, t + d, p))
                t += d
    return out


def build(spec) -> dict:
    timings = json.loads((spec.build / "timings.json").read_text())
    cs = cues(timings)
    srt = "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cs, 1))
    vtt = "WEBVTT\n\n" + "\n".join(f"{_ts(a, '.')} --> {_ts(b, '.')}\n{txt}\n" for a, b, txt in cs)
    (spec.out / f"{spec.id}.en.srt").write_text(srt)
    (spec.out / f"{spec.id}.en.vtt").write_text(vtt)
    return {"cues": len(cs), "srt": str(spec.out / f"{spec.id}.en.srt")}
