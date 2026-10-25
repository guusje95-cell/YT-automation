"""Render the timeline to frames, pipe to ffmpeg, mux with the final mix."""
from __future__ import annotations

import json
import subprocess
import time

import numpy as np

from ytauto.core import config
from ytauto.core.log import get_logger
from ytauto.video import timeline
from ytauto.visuals import frames as fr

log = get_logger(__name__)


def _renderer(beat: dict, dur: float, assets: dict, sources: dict):
    t = beat["type"]
    if t == "image":
        a = assets[beat["asset"]]
        return fr.image_beat(a["file"], dur, motion=beat.get("motion", "in"),
                             focus=tuple(beat.get("focus", (0.5, 0.5))), fit=beat.get("fit", "auto"),
                             zoom=beat.get("zoom", 0.12))
    if t == "video":
        a = assets[beat["asset"]]
        return fr.video_beat(a["file"], dur, start=beat.get("from", 0), speed=beat.get("speed", 1.0),
                            zoom=beat.get("zoom", 1.0))
    if t == "title":
        return fr.title_beat(dur, beat["text"], beat.get("kicker", ""))
    if t == "fact":
        src = sources.get(beat.get("source"), {})
        label = beat.get("source_label") or src.get("publisher") or ""
        return fr.fact_beat(dur, beat["big"], beat.get("small", ""), label)
    if t == "list":
        return fr.list_beat(dur, beat.get("title", ""), beat["items"], beat.get("highlight"))
    if t == "scale":
        return fr.scale_beat(dur, beat.get("mode", "circles"), beat.get("title", ""), beat.get("labels"),
                             beat.get("items"), beat.get("highlight"), beat.get("bounds"))
    if t == "end":
        return fr.end_beat(dur, beat.get("text", ""))
    raise ValueError(f"unsupported beat type {t}")


def render(spec, preview: bool = False) -> dict:
    timings = json.loads((spec.build / "timings.json").read_text())
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    beats = timeline.build(spec, timings)
    (spec.build / "timeline.json").write_text(json.dumps(beats, indent=1))
    total = timings["duration"]
    fps = fr.FPS
    vcfg = config.get("video")
    out_video = spec.build / ("video_preview.mp4" if preview else "video.mp4")
    scale = ["-vf", "scale=1280:720"] if preview else []
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{fr.W}x{fr.H}",
           "-r", str(fps), "-i", "-", *scale, "-c:v", "libx264", "-preset",
           "veryfast" if preview else vcfg["preset"], "-crf", str(23 if preview else vcfg["crf"]),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ov = fr.Overlays()
    trans = vcfg.get("transition_s", 0.5)
    n_frames = int(round(total * fps))
    t0 = time.time()
    prev_last = None
    bi = 0
    cur = None
    cur_idx = -1
    for i in range(n_frames):
        t = i / fps
        while bi < len(beats) - 1 and t >= beats[bi]["end"]:
            bi += 1
        b = beats[bi]
        if bi != cur_idx:
            if cur is not None and hasattr(cur, "close"):
                cur.close()
            cur = _renderer(b, b["end"] - b["start"] + 1.0 / fps, manifest, spec.sources)
            cur_idx = bi
        lt = t - b["start"]
        frame = cur(lt)
        if frame.base is not None or not frame.flags.writeable:
            frame = frame.copy()
        # overlays for media beats
        if b["type"] in ("image", "video"):
            frame = fr.apply_vignette(frame)
            credit = fr.short_credit(manifest[b["asset"]]["credit"])
            ov.credit(credit).draw(frame, 0.85)
            if b.get("label"):
                ov.label(b["label"]).draw(frame, fr.fade_window(lt, 0.5, b["end"] - b["start"] - 0.3))
        if b.get("first_in_scene") and b.get("chapter") and b["scene_index"] > 0 and b["type"] in ("image", "video"):
            ov.chapter(b["chapter"]).draw(frame, fr.fade_window(lt, 0.3, 4.0))
        # cross-dissolve from the previous beat's last frame
        if prev_last is not None and lt < trans and bi > 0:
            a = fr.ease(lt / trans)
            frame = (prev_last.astype(np.float32) * (1 - a) + frame.astype(np.float32) * a).astype(np.uint8)
        if i + 1 < n_frames and (i + 1) / fps >= b["end"] and bi < len(beats) - 1:
            prev_last = frame
        proc.stdin.write(frame.tobytes())
        if i % (fps * 30) == 0 and i:
            el = time.time() - t0
            log.info("rendered %d/%d frames (%.1f fps, ETA %.0fs)", i, n_frames, i / el, (n_frames - i) / (i / el))
    if cur is not None and hasattr(cur, "close"):
        cur.close()
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg video encode failed")
    log.info("video rendered in %.0fs", time.time() - t0)
    return {"video": str(out_video), "beats": len(beats), "frames": n_frames, "render_s": round(time.time() - t0)}


def storyboard(spec, cols: int = 6, thumb_w: int = 384) -> str:
    """Render the mid-frame of every beat (with overlays) into one contact sheet for quick review."""
    from PIL import Image, ImageDraw
    timings = json.loads((spec.build / "timings.json").read_text())
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    beats = timeline.build(spec, timings)
    ov = fr.Overlays()
    th = int(thumb_w * fr.H / fr.W)
    rows = (len(beats) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (th + 22)), (12, 12, 16))
    d = ImageDraw.Draw(sheet)
    f = fr.font("medium", 15)
    for k, b in enumerate(beats):
        dur = b["end"] - b["start"]
        r = _renderer(b, dur, manifest, spec.sources)
        lt = dur * 0.6
        frame = r(lt).copy()
        if hasattr(r, "close"):
            r.close()
        if b["type"] in ("image", "video"):
            frame = fr.apply_vignette(frame)
            ov.credit(fr.short_credit(manifest[b["asset"]]["credit"])).draw(frame, 0.85)
            if b.get("label"):
                ov.label(b["label"]).draw(frame, 1.0)
        im = Image.fromarray(frame).resize((thumb_w, th), Image.LANCZOS)
        x, y = (k % cols) * thumb_w, (k // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + th + 2), f"{k:02d} {b['scene']} {b['start']:.0f}-{b['end']:.0f}s {b['type']}",
               fill=(255, 190, 90), font=f)
    out = spec.out / "storyboard.jpg"
    sheet.save(out, quality=82)
    return str(out)


def mux(spec, preview: bool = False) -> str:
    vid = spec.build / ("video_preview.mp4" if preview else "video.mp4")
    out = spec.out / (f"{spec.id}_preview.mp4" if preview else f"{spec.id}.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(vid), "-i", str(spec.build / "mix.wav"), "-map", "0:v",
           "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "96k" if preview else "256k", "-ar", "48000",
           "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    log.info("muxed %s", out)
    return str(out)
