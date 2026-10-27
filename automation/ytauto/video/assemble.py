"""Render the timeline to frames, pipe to ffmpeg, mux with the final mix."""
from __future__ import annotations

import json
import subprocess
import time

import numpy as np

from ytauto.core import config
from ytauto.core.log import get_logger
from ytauto.video import prerender, timeline
from ytauto.visuals import charts
from ytauto.visuals import editorial as ed
from ytauto.visuals import frames as fr
from ytauto.visuals import road
from ytauto.visuals import shots

log = get_logger(__name__)


def _renderer(beat: dict, dur: float, assets: dict, sources: dict, ctx: dict | None = None):
    ctx = ctx or {}
    t = beat["type"]
    if t == "r3d":
        if ctx.get("direct"):  # storyboard: render the requested frames straight from the shot
            return shots.make(beat["shot"], dur, **(beat.get("params") or {}))
        clip = prerender.clip_path(beat, dur)
        if not clip.exists():
            raise RuntimeError(f"r3d clip missing for {beat['shot']} ({clip.name}); run the prerender stage")
        return fr.video_beat(str(clip), dur)
    if t == "image":
        a = assets[beat["asset"]]
        return fr.image_beat(a["file"], dur, motion=beat.get("motion", "in"),
                             focus=tuple(beat.get("focus", (0.5, 0.5))), fit=beat.get("fit", "auto"),
                             zoom=beat.get("zoom", 0.12), crop=beat.get("crop"))
    if t == "video":
        a = assets[beat["asset"]]
        return fr.video_beat(a["file"], dur, start=beat.get("from", 0), speed=beat.get("speed", 1.0),
                            zoom=beat.get("zoom", 1.0))
    if t == "title":
        if beat.get("style") == "cinematic":
            return ed.title_beat(dur, beat["text"], beat.get("sub", ""))
        return fr.title_beat(dur, beat["text"], beat.get("kicker", ""))
    if t == "glitch":
        return ed.glitch_beat(dur, beat.get("text", "SIGNAL LOST"), beat.get("sub", ""), src=ctx.get("last"))
    if t == "black":
        return ed.black_beat(dur, ember=beat.get("ember", True))
    if t == "profile":
        return ed.profile_beat(dur)
    if t == "horizon_scale":
        src = sources.get(beat.get("source"), {})
        return ed.horizon_scale_beat(dur, beat.get("horizon_au", 1300.0), beat.get("title", ""),
                                     source_label=f"Source: {src['publisher']}" if src else "")
    if t == "fact_list":
        src = sources.get(beat.get("source"), {})
        label = beat.get("source_label") or (f"Source: {src['publisher']}" if src else "")
        return ed.fact_list_beat(dur, beat.get("title", ""), beat["items"], label, backdrop=ctx.get("last"))
    if t == "fact":
        src = sources.get(beat.get("source"), {})
        label = beat.get("source_label") or (f"Source: {src['publisher']}" if src else "")
        return ed.fact_beat(dur, beat["big"], beat.get("small", ""), label, backdrop=ctx.get("last"))
    if t == "record_chart":
        src = sources.get(beat.get("source"), {})
        label = beat.get("source_label") or (f"Source: {src['publisher']}" if src else "")
        return charts.record_chart_beat(dur, beat["points"], beat.get("title", ""), beat.get("unit", "km/h"),
                                        tuple(beat.get("reveal", (1895, 2026))),
                                        beat.get("x_range", ((1895, 2030), (1895, 2030))),
                                        beat.get("y_range", ((0, 520), (0, 520))), beat.get("focus"), label,
                                        beat.get("wall"))
    if t == "speed":
        return charts.speed_beat(dur, beat.get("start", 0), beat["end"], beat.get("unit", "km/h"),
                                 beat.get("label", ""), beat.get("sub", ""), beat.get("verdict", ""),
                                 backdrop=ctx.get("last"), decimals=beat.get("decimals", 0))
    if t == "road":
        return road.road_beat(dur, beat.get("sky", "dusk"), tuple(beat.get("speed", (0.6, 1.0))), beat.get("speedo"),
                              beat.get("label", ""), seed=beat.get("seed", 3))
    if t == "landmark":
        return road.landmark_beat(dur, beat.get("claimed", "533 km/h on screen"), beat.get("note", "Illustration"))
    if t == "list":
        return fr.list_beat(dur, beat.get("title", ""), beat["items"], beat.get("highlight"))
    if t == "scale":
        return fr.scale_beat(dur, beat.get("mode", "circles"), beat.get("title", ""), beat.get("labels"),
                             beat.get("items"), beat.get("highlight"), beat.get("bounds"))
    if t == "end":
        return ed.end_beat(dur, beat.get("channel") or config.get("channel.name", ""), beat.get("text", ""))
    raise ValueError(f"unsupported beat type {t}")


NO_DISSOLVE_INTO = {"glitch", "black"}


def _chapter_numbers(beats: list[dict]) -> dict:
    nums, n = {}, 0
    for b in beats:
        if b.get("first_in_scene") and b.get("chapter"):
            n += 1
            nums[b["scene"]] = n
    return nums


class Decorator:
    """Per-beat overlays drawn on top of the raw beat frame: shake, capsule window, labels, HUD, notes,
    character radio log + transcript, chapter card, title."""

    def __init__(self, manifest: dict, beats: list[dict], spec=None, timings: dict | None = None):
        self.manifest = manifest
        self.ov = fr.Overlays()
        self.chapters = _chapter_numbers(beats)
        self.cache: dict = {}
        self.pov = None
        self.char_sents = []
        self.radio = {}
        self.mission = "TELEMETRY"
        if spec is not None:
            self.mission = spec.data.get("hud_mission", "VESPER  ·  TELEMETRY" if spec.data.get("characters")
                                         else "GALILEO PROBE  ·  TELEMETRY")
        chars = (spec.data.get("characters") or {}) if spec is not None else {}
        if chars and timings:
            env = ed.voice_envelope(spec.build / "narration.wav", fr.FPS)
            self.radio = {k: ed.RadioLog(v["name"], v.get("tag", ""), env, fr.FPS) for k, v in chars.items()}
            self.char_sents = [s for sc in timings["scenes"] for s in sc["sentences"] if s.get("who") in self.radio]

    def _get(self, key, make):
        if key not in self.cache:
            self.cache[key] = make()
        return self.cache[key]

    def _speaking(self, gt: float):
        for s in self.char_sents:
            if s["start"] - 0.25 <= gt <= s["end"] + 0.6:
                return s
        return None

    def __call__(self, frame: np.ndarray, b: dict, k: int, lt: float, gt: float | None = None) -> np.ndarray:
        dur = b["end"] - b["start"]
        t = b["type"]
        gt = b["start"] + lt if gt is None else gt
        if b.get("shake"):
            frame = ed.shake(frame, lt, float(b["shake"]), seed=k)
        if t in ("image", "video"):
            frame = fr.apply_vignette(frame)
        if b.get("pov"):
            if self.pov is None:
                self.pov = ed.PovFrame()
            frame = self.pov.draw(frame, min(1.0, fr.fade_window(lt, 0.0, dur, 0.3) + (k > 0) * 0.0))
        # No on-screen credit lines (they read as clutter); every credit is in the description,
        # which satisfies CC BY's "reasonable manner for the medium" attribution.
        speaking = self._speaking(gt)
        if b.get("label") and not speaking and t not in ("road", "speed"):   # those draw their own caption
            self.ov.label(b["label"]).draw(frame, fr.fade_window(lt, 0.5, dur - 0.3))
        if b.get("hud"):
            hud = self._get(("hud", k), lambda: ed.Hud(b["hud"], dur, self.mission))
            hud.draw(frame, lt, fr.fade_window(lt, 0.15, dur + 1, 0.35))
        if b.get("note"):
            self._get(("note", k), lambda: ed.NoteOverlay(b["note"], b.get("note_big", False))).draw(frame, lt, dur)
        if b.get("title") and t == "r3d":
            title = self._get(("title", k), lambda: ed.TitleOverlay(b["title"], b.get("title_sub", "")))
            title.draw(frame, lt, dur)
        if b.get("first_in_scene") and b.get("chapter") and t not in NO_DISSOLVE_INTO:
            card = self._get(("ch", b["scene"]), lambda: ed.ChapterCard(self.chapters[b["scene"]], b["chapter"]))
            card.draw(frame, lt)
        if speaking and t not in ("glitch", "black") or (speaking and t == "black"):
            self.radio[speaking["who"]].draw(frame, gt, speaking)
        return frame


def render(spec, preview: bool = False) -> dict:
    timings = json.loads((spec.build / "timings.json").read_text())
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    beats = timeline.build(spec, timings)
    (spec.build / "timeline.json").write_text(json.dumps(beats, indent=1))
    prerender.run(beats)
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
    deco = Decorator(manifest, beats, spec, timings)
    trans = vcfg.get("transition_s", 0.5)
    n_frames = int(round(total * fps))
    t0 = time.time()
    prev_last = None
    last_raw = None
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
            cur = _renderer(b, b["end"] - b["start"] + 1.0 / fps, manifest, spec.sources, {"last": last_raw})
            cur_idx = bi
        lt = t - b["start"]
        frame = cur(lt)
        if frame.base is not None or not frame.flags.writeable:
            frame = frame.copy()
        last_raw = frame.copy() if (i + 1) / fps >= b["end"] - 1.0 / fps else last_raw
        frame = deco(frame, b, bi, lt, t)
        # cross-dissolve from the previous beat's last frame (hard cuts into glitch / black beats)
        tr = b.get("transition", 0.0 if b["type"] in NO_DISSOLVE_INTO else trans)
        if prev_last is not None and bi > 0 and lt < tr:
            a = fr.ease(lt / tr)
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


def storyboard(spec, cols: int = 6, thumb_w: int = 384, at=(0.6,)) -> str:
    """Contact sheet of every beat (with overlays) at the given fractions of each beat. 3D beats are rendered
    directly (no prerender needed), so this is the fast review loop."""
    from PIL import Image, ImageDraw
    timings = json.loads((spec.build / "timings.json").read_text())
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    beats = timeline.build(spec, timings)
    deco = Decorator(manifest, beats, spec, timings)
    th = int(thumb_w * fr.H / fr.W)
    cells = [(k, a) for k in range(len(beats)) for a in at]
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (th + 22)), (12, 12, 16))
    d = ImageDraw.Draw(sheet)
    f = fr.font("medium", 15)
    last = None
    for n, (k, at_) in enumerate(cells):
        b = beats[k]
        dur = b["end"] - b["start"]
        r = _renderer(b, dur, manifest, spec.sources, {"direct": True, "last": last})
        lt = dur * at_
        frame = r(lt).copy()
        if at_ == at[-1]:
            last = r(dur * 0.98).copy() if b["type"] not in ("glitch",) else frame
        if hasattr(r, "close"):
            r.close()
        frame = deco(frame, b, k, lt)
        im = Image.fromarray(frame).resize((thumb_w, th), Image.LANCZOS)
        x, y = (n % cols) * thumb_w, (n // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + th + 2), f"{k:02d} {b['scene']} {b['start']:.0f}-{b['end']:.0f}s {b['type']}"
               f"{' ' + b['shot'] if b['type'] == 'r3d' else ''}", fill=(255, 190, 90), font=f)
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
