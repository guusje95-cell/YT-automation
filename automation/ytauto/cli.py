"""Command-line entry point.

  python -m ytauto produce <video_id>        full pipeline: assets -> voice -> audio -> captions -> thumbnails
                                             -> render -> mux -> metadata -> QA
  python -m ytauto storyboard <video_id>     quick visual review sheet (seconds)
  python -m ytauto preview <video_id>        fast 720p render for review
  python -m ytauto qa <video_id>             rerun QA only
  python -m ytauto research [--niches ...]   niche/competitor scan (public pages or Data API)
  python -m ytauto monitor                   competitor outlier report for the chosen niche
  python -m ytauto publish <video_id> [--dry-run] [--privacy private|unlisted] [--publish-at ISO]
  python -m ytauto analytics [--days 28]     pull channel analytics and write the weekly report
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time

from ytauto import spec as spec_mod
from ytauto.core.log import get_logger

log = get_logger("cli")


def _stage(name: str, fn, plog: dict):
    t0 = time.time()
    log.info("== stage %s", name)
    try:
        out = fn()
        plog["stages"].append({"stage": name, "seconds": round(time.time() - t0, 1), "status": "ok"})
        return out
    except Exception as e:
        plog["stages"].append({"stage": name, "seconds": round(time.time() - t0, 1), "status": f"error: {e}"})
        raise


def produce(video_id: str, skip_render: bool = False, preview: bool = False) -> dict:
    from ytauto import captions, metadata, qa, thumbnail
    from ytauto.assets import fetch
    from ytauto.audio import mix
    from ytauto.video import assemble
    from ytauto.voice import narrate

    s = spec_mod.load(video_id)
    plog = {"video_id": s.id, "started": dt.datetime.now().isoformat(timespec="seconds"), "stages": []}
    try:
        _stage("assets", lambda: fetch.fetch_all(s), plog)
        _stage("narration", lambda: narrate.build(s), plog)
        _stage("audio_mix", lambda: mix.build(s), plog)
        _stage("captions", lambda: captions.build(s), plog)
        _stage("thumbnails", lambda: thumbnail.build(s), plog)
        _stage("storyboard", lambda: assemble.storyboard(s), plog)
        if not skip_render:
            _stage("render", lambda: assemble.render(s, preview=preview), plog)
            _stage("mux", lambda: assemble.mux(s, preview=preview), plog)
        _stage("metadata", lambda: metadata.build(s), plog)
        if not skip_render and not preview:
            res = _stage("qa", lambda: qa.run(s), plog)
            plog["qa"] = res["summary"]
    finally:
        plog["finished"] = dt.datetime.now().isoformat(timespec="seconds")
        plog["total_seconds"] = round(sum(x["seconds"] for x in plog["stages"]), 1)
        plog["cost_eur"] = {"tts": 0.0, "assets": 0.0, "music": 0.0, "llm": 0.0,
                            "note": "all local/free providers; LLM cost applies only when scripts are drafted via API"}
        hist = s.out / "production_log.json"
        prev = json.loads(hist.read_text()) if hist.exists() else []
        prev.append(plog)
        hist.write_text(json.dumps(prev, indent=1))
    return plog


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ytauto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("produce"); p.add_argument("video_id"); p.add_argument("--skip-render", action="store_true")
    p.add_argument("--preview", action="store_true")
    p = sub.add_parser("storyboard"); p.add_argument("video_id")
    p = sub.add_parser("preview"); p.add_argument("video_id")
    p = sub.add_parser("qa"); p.add_argument("video_id"); p.add_argument("--no-asr", action="store_true")
    p = sub.add_parser("research"); p.add_argument("rest", nargs=argparse.REMAINDER)
    p = sub.add_parser("monitor"); p.add_argument("--config", default="competitors.yaml")
    p = sub.add_parser("publish"); p.add_argument("video_id"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--privacy", default=None); p.add_argument("--publish-at", default=None)
    p = sub.add_parser("analytics"); p.add_argument("--days", type=int, default=28)
    p.add_argument("--mock", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "produce":
        print(json.dumps(produce(a.video_id, a.skip_render, a.preview), indent=1))
    elif a.cmd == "storyboard":
        from ytauto.video import assemble
        print(assemble.storyboard(spec_mod.load(a.video_id)))
    elif a.cmd == "preview":
        print(json.dumps(produce(a.video_id, preview=True), indent=1))
    elif a.cmd == "qa":
        from ytauto import qa
        print(json.dumps(qa.run(spec_mod.load(a.video_id), intelligibility=not a.no_asr)["summary"]))
    elif a.cmd == "research":
        from ytauto.research import niche_scan
        niche_scan.main(a.rest)
    elif a.cmd == "monitor":
        from ytauto.research import monitor
        print(monitor.run(a.config))
    elif a.cmd == "publish":
        from ytauto.publish import youtube
        print(json.dumps(youtube.publish(spec_mod.load(a.video_id), dry_run=a.dry_run, privacy=a.privacy,
                                         publish_at=a.publish_at), indent=1))
    elif a.cmd == "analytics":
        from ytauto.analytics import report
        print(report.run(days=a.days, mock=a.mock))


if __name__ == "__main__":
    sys.exit(main())
