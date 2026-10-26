"""Automated quality assurance. Produces output/<id>/qa_report.md and qa.json.

Each check returns (status, detail) with status in PASS / WARN / FAIL.
FAIL blocks publishing; WARN needs a human glance (listed at the top of the report).
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image

from ytauto.core import config
from ytauto.core.log import ROOT, get_logger
from ytauto.voice.tts import split_sentences

log = get_logger(__name__)

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _banned() -> tuple[list[str], list[str]]:
    err, warn = [], []
    for line in (ROOT / config.get("qa.banned_phrases_file")).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        (warn if line.startswith("warn:") else err).append(line.removeprefix("warn:").lower())
    return err, warn


# ----------------------------------------------------------------- script checks
def check_script(spec) -> list[tuple]:
    res = []
    err, warn = _banned()
    text_all = " ".join(sc["narration"] for sc in spec.scenes)
    low = text_all.lower()
    hits_e = [p for p in err if re.search(rf"\b{re.escape(p)}\b", low)]
    hits_w = [p for p in warn if re.search(rf"\b{re.escape(p)}\b", low)]
    res.append(("script.banned_phrases", FAIL if hits_e else PASS, ", ".join(hits_e) or "none"))
    res.append(("script.hype_words", WARN if len(hits_w) > 3 else PASS, ", ".join(hits_w) or "none"))
    words = len(text_all.split())
    sents = [s for sc in spec.scenes for s in split_sentences(sc["narration"])]
    longest = max(sents, key=lambda s: len(s.split()))
    res.append(("script.length", PASS if 900 <= words <= 3200 else WARN, f"{words} words, {len(sents)} sentences"))
    res.append(("script.longest_sentence", WARN if len(longest.split()) > 38 else PASS,
                f"{len(longest.split())} words: {longest[:90]}..."))
    openers = [" ".join(s.split()[:2]).lower() for s in sents]
    rep = {o: openers.count(o) for o in set(openers) if openers.count(o) >= 4}
    res.append(("script.repetitive_openers", WARN if rep else PASS, str(rep) if rep else "none"))
    # numbers must be backed by a claim in the same scene
    unbacked = []
    for sc in spec.scenes:
        claims_text = " ".join(c["text"] for c in sc.get("claims", [])).replace(",", "")
        for num in re.findall(r"\b\d[\d,.]*\b", sc["narration"]):
            n = num.rstrip(".").replace(",", "")
            if n not in claims_text:
                unbacked.append(f"{sc['id']}:{num}")
        if not sc.get("claims"):
            unbacked.append(f"{sc['id']}: no claims listed")
    res.append(("script.numbers_sourced", WARN if unbacked else PASS,
                ", ".join(unbacked) if unbacked else "every number appears in a sourced claim"))
    cited = {s for sc in spec.scenes for c in sc.get("claims", []) for s in c.get("sources", [])}
    unused = set(spec.sources) - cited
    res.append(("script.sources_used", WARN if unused else PASS, f"uncited sources: {sorted(unused)}" if unused
                else f"{len(cited)} sources cited"))
    ts = spec.data.get("time_sensitive") or []
    res.append(("script.time_sensitive", WARN if ts else PASS, " | ".join(ts) if ts else "none declared"))
    return res


# ----------------------------------------------------------------- assets
def check_assets(spec) -> list[tuple]:
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    allowed = set(config.get("assets.allowed_licenses"))
    bad = [k for k, v in manifest.items() if v["license"] not in allowed]
    flags = [f"{k}: {f}" for k, v in manifest.items() for f in v.get("flags", []) if "citizen" not in f]
    used = {b.get("asset") for sc in spec.scenes for b in sc["beats"] if b.get("asset")}
    thumb_assets = {v.get("asset") for v in (spec.data.get("thumbnail") or {}).get("variants", [])}
    unused = set(manifest) - used - thumb_assets
    missing_credit = [k for k, v in manifest.items() if not v.get("credit")]
    return [
        ("assets.licences", FAIL if bad else PASS, f"not allowed: {bad}" if bad else f"{len(manifest)} assets, all allowed"),
        ("assets.credits", FAIL if missing_credit else PASS, str(missing_credit) if missing_credit else "all credited"),
        ("assets.flags", WARN if flags else PASS, "; ".join(flags) if flags else "no open flags"),
        ("assets.unused", PASS, f"unused (fine): {sorted(unused)}" if unused else "all used"),
    ]


# ----------------------------------------------------------------- media probes
def _probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True)
    return json.loads(out.stdout or "{}")


def _ffmpeg_detect(path: Path, flt: str) -> str:
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af" if "silence" in flt or "ebur" in flt
                          else "-vf", flt, "-f", "null", "-"], capture_output=True, text=True)
    return out.stderr


def check_video(spec) -> list[tuple]:
    res = []
    vid = spec.out / f"{spec.id}.mp4"
    if not vid.exists():
        return [("video.exists", FAIL, f"{vid} missing")]
    p = _probe(vid)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"]["duration"])
    q = config.get("qa")
    res.append(("video.format", PASS if (v["width"], v["height"]) == (1920, 1080) and v["codec_name"] == "h264"
                and v.get("pix_fmt") == "yuv420p" else FAIL, f"{v['codec_name']} {v['width']}x{v['height']} "
                f"{v.get('pix_fmt')} {v.get('r_frame_rate')}"))
    res.append(("video.audio_stream", PASS if a and a["codec_name"] == "aac" else FAIL,
                f"{a['codec_name']} {a.get('sample_rate')} Hz {a.get('channels')} ch" if a else "missing"))
    res.append(("video.duration", PASS if q["min_duration_s"] <= dur <= q["max_duration_s"] else WARN,
                f"{dur:.1f}s ({dur / 60:.1f} min)"))
    vdur, adur = float(v.get("duration", dur)), float(a.get("duration", dur)) if a else 0
    res.append(("video.av_sync_length", PASS if abs(vdur - adur) < 0.5 else FAIL, f"video {vdur:.2f}s / audio {adur:.2f}s"))
    log.info("QA: black frame scan")
    bl = _ffmpeg_detect(vid, f"blackdetect=d={q['max_black_s']}:pix_th=0.06")
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl)
    blacks = [(float(s), float(e)) for s, e in blacks if float(s) < dur - 3]  # the end-card fade is intended
    tl = spec.build / "timeline.json"
    intended = [(b["start"] - 0.5, b["end"] + 0.5) for b in (json.loads(tl.read_text()) if tl.exists() else [])
                if b["type"] in ("black", "glitch")]   # deliberate 'into the dark' / signal-lost beats
    blacks = [(s_, e_) for s_, e_ in blacks if not any(a <= s_ and e_ <= b for a, b in intended)]
    res.append(("video.black_frames", FAIL if blacks else PASS,
                f"black segments: {blacks}" if blacks else f"none longer than {q['max_black_s']}s"))
    log.info("QA: loudness + silence scan")
    eb = _ffmpeg_detect(vid, "ebur128=peak=true")
    m = re.search(r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS.*?True peak:\s+Peak:\s+(-?[\d.]+) dBFS", eb, re.S)
    if m:
        lufs, tp = float(m.group(1)), float(m.group(2))
        ok = abs(lufs - config.get("audio.target_lufs")) <= q["lufs_tolerance"] and tp <= -0.5
        res.append(("audio.loudness", PASS if ok else WARN, f"{lufs} LUFS integrated, true peak {tp} dBFS"))
    else:
        res.append(("audio.loudness", WARN, "could not parse ebur128 output"))
    si = _ffmpeg_detect(vid, f"silencedetect=n=-45dB:d={q['max_silence_s']}")
    sil = re.findall(r"silence_start: ([\d.]+)", si)
    sil = [float(s) for s in sil if 2 < float(s) < dur - 4]
    res.append(("audio.long_silences", WARN if sil else PASS, f"at {sil}" if sil else "none"))
    return res


# ----------------------------------------------------------------- narration intelligibility
def _norm_words(text: str) -> list[str]:
    text = text.lower().replace("-", " ")
    text = re.sub(r"(\d),(\d)", r"\1\2", text)
    return re.findall(r"[a-z0-9']+", text)


def check_intelligibility(spec, model_size: str = "small.en") -> list[tuple]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return [("voice.intelligibility", WARN, "faster-whisper not installed; skipped")]
    model = WhisperModel(model_size, device="cpu", compute_type="int8",
                         download_root=str(config.MODELS_DIR / "whisper"))
    import soundfile as sf
    from scipy.signal import resample_poly
    x, sr = sf.read(spec.build / "narration.wav", dtype="float32")
    audio16 = resample_poly(x, 16000 // 8000, sr // 8000).astype("float32")  # avoid PyAV decode (version issues)
    segs, _ = model.transcribe(audio16, language="en", beam_size=1)
    hyp = " ".join(s.text for s in segs)
    (spec.build / "asr_transcript.txt").write_text(hyp)
    ref_w = _norm_words(" ".join(sc["narration"] for sc in spec.scenes))
    hyp_w = _norm_words(hyp)
    sm = difflib.SequenceMatcher(a=ref_w, b=hyp_w, autojunk=False)
    errors = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    wer = errors / max(len(ref_w), 1)
    diffs = [f"'{' '.join(ref_w[i1:i2])}' -> '{' '.join(hyp_w[j1:j2])}'" for op, i1, i2, j1, j2 in sm.get_opcodes()
             if op != "equal"][:25]
    (spec.build / "asr_diffs.txt").write_text("\n".join(diffs))
    status = PASS if wer < 0.06 else WARN if wer < 0.12 else FAIL
    return [("voice.intelligibility", status, f"ASR word error rate {wer:.1%} (lower is better; includes number "
                                              f"formatting differences). Top diffs: {'; '.join(diffs[:8])}")]


# ----------------------------------------------------------------- captions / packaging
def check_packaging(spec) -> list[tuple]:
    res = []
    srt = spec.out / f"{spec.id}.en.srt"
    if srt.exists():
        lines = [l for l in srt.read_text().splitlines() if l and not l[0].isdigit()]
        too_long = [l for l in lines if len(l) > 42]
        res.append(("captions.line_length", WARN if too_long else PASS, f"{len(too_long)} lines > 42 chars"))
    else:
        res.append(("captions.exists", FAIL, "missing"))
    meta_p = spec.out / "metadata.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text())
        res.append(("meta.title_length", PASS if len(meta["title"]) <= 70 else WARN if len(meta["title"]) <= 100 else FAIL,
                    f"{len(meta['title'])} chars: {meta['title']}"))
        res.append(("meta.description_length", PASS if len(meta["description"]) <= 5000 else FAIL,
                    f"{len(meta['description'])} chars"))
        tag_chars = sum(len(t) + 1 for t in meta["tags"])
        res.append(("meta.tags", PASS if tag_chars <= 500 else FAIL, f"{len(meta['tags'])} tags, {tag_chars} chars"))
        res.append(("meta.chapters", PASS if meta["chapters"] else WARN, f"{len(meta['chapters'])} chapters"))
        res.append(("meta.privacy_default", PASS if meta["privacy_status"] == "private" else WARN, meta["privacy_status"]))
    else:
        res.append(("meta.exists", FAIL, "metadata.json missing"))
    thumbs = sorted(spec.out.glob("thumbnail_*.jpg"))
    for t in thumbs:
        im = Image.open(t)
        ok = im.size == (1280, 720) and t.stat().st_size < 2_000_000
        res.append((f"thumbnail.{t.stem}", PASS if ok else FAIL, f"{im.size}, {t.stat().st_size // 1024} KB"))
    if not thumbs:
        res.append(("thumbnail.exists", FAIL, "no thumbnails"))
    return res


def run(spec, intelligibility: bool = True) -> dict:
    results = check_script(spec) + check_assets(spec) + check_packaging(spec) + check_video(spec)
    if intelligibility:
        results += check_intelligibility(spec)
    summary = {s: sum(1 for r in results if r[1] == s) for s in (PASS, WARN, FAIL)}
    lines = [f"# QA report — {spec.id}", "",
             f"**{summary[FAIL]} FAIL · {summary[WARN]} WARN · {summary[PASS]} PASS**  "
             f"({'BLOCKED: fix FAIL items before publishing' if summary[FAIL] else 'publishable after human review of WARN items'})",
             "", "| Check | Status | Detail |", "|---|---|---|"]
    order = {FAIL: 0, WARN: 1, PASS: 2}
    for name, st, detail in sorted(results, key=lambda r: order[r[1]]):
        lines.append(f"| {name} | {st} | {str(detail).replace('|', '/')} |")
    (spec.out / "qa_report.md").write_text("\n".join(lines) + "\n")
    (spec.out / "qa.json").write_text(json.dumps({"summary": summary, "results": results}, indent=1))
    log.info("QA %s", summary)
    return {"summary": summary, "results": results}
