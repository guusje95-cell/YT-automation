"""Pre-render the 3D (`r3d`) beats to cached mp4 clips, in parallel.

The ray-traced shots cost ~0.2–2 s per frame, so they are rendered once per (shot, params, duration)
on all cores and reused by every later render/preview. Clips live in .cache/r3d/<key>.mp4 (git-ignored).
Bump RENDER_VERSION after changing a shot's look to invalidate old clips.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import time
from multiprocessing import get_context

from ytauto.core import config
from ytauto.core.log import get_logger

log = get_logger(__name__)

RENDER_VERSION = 3
# Per-shot look versions: bump one entry to re-render only that shot's clips.
SHOT_VERSIONS = {"cloud_dive": 2, "entry": 2}
CACHE = config.CACHE_DIR / "r3d"


def clip_key(beat: dict, duration: float) -> str:
    from ytauto.visuals.frames import FPS, H, W
    d = {"v": RENDER_VERSION, "shot": beat["shot"], "params": beat.get("params") or {},
         "frames": frame_count(duration, FPS), "size": [W, H]}
    if SHOT_VERSIONS.get(beat["shot"], 1) > 1:
        d["sv"] = SHOT_VERSIONS[beat["shot"]]
    payload = json.dumps(d, sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def frame_count(duration: float, fps: int) -> int:
    return int(math.ceil(duration * fps)) + 3


def clip_path(beat: dict, duration: float):
    return CACHE / f"{clip_key(beat, duration)}.mp4"


def _render_job(job):
    shot, params, duration, out = job
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from ytauto.visuals import shots
    from ytauto.visuals.frames import FPS, H, W
    t0 = time.time()
    n = frame_count(duration, FPS)
    tmp = out.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    r = shots.make(shot, duration, **(params or {}))
    for i in range(n):
        proc.stdin.write(r(min(i / FPS, duration)).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"encode failed for {shot}")
    tmp.rename(out)
    return shot, round(duration, 1), round(time.time() - t0)


def run(beats: list[dict], workers: int | None = None) -> dict:
    """Render every missing r3d clip referenced by the timeline `beats`. Returns {rendered, cached}."""
    from ytauto.visuals.frames import FPS
    CACHE.mkdir(parents=True, exist_ok=True)
    jobs, seen, cached = [], set(), 0
    for b in beats:
        if b["type"] != "r3d":
            continue
        dur = b["end"] - b["start"] + 1.0 / FPS
        out = clip_path(b, dur)
        if out.exists():
            cached += 1
            continue
        if out in seen:
            continue
        seen.add(out)
        jobs.append((b["shot"], b.get("params") or {}, dur, out))
    jobs.sort(key=lambda j: -j[2])          # longest first for better load balance
    workers = workers or config.get("video.render_workers", 4)
    log.info("prerender: %d clips to render, %d cached, %d workers", len(jobs), cached, workers)
    t0 = time.time()
    if jobs:
        with get_context("fork").Pool(workers) as pool:
            for k, (shot, dur, secs) in enumerate(pool.imap_unordered(_render_job, jobs), 1):
                log.info("prerender %d/%d: %s %.1fs in %ds", k, len(jobs), shot, dur, secs)
    log.info("prerender done in %.0fs", time.time() - t0)
    return {"rendered": len(jobs), "cached": cached, "seconds": round(time.time() - t0)}
