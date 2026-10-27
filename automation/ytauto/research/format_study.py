"""Format study: what do winning small-channel videos in a niche *look* like?

Searches viewer-style queries (uploads from the past year, long-form >= 4 min), keeps videos with >= 100k views,
looks up channel size, and writes a contact sheet of thumbnails (numbered) plus a JSON list, so each winner can be
classified by visual format (real footage, photos + graphics, 2D/stickman animation, 3D animation, game footage,
presenter on camera). Public search pages and public thumbnail images only.

  python -m ytauto.research.format_study --config topic_formats_cars.yaml --tag cars
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

import cv2
import numpy as np
import requests
import yaml

from ytauto.core.log import ROOT, get_logger
from ytauto.research import youtube_public as yp

log = get_logger(__name__)
MIN_VIEWS = 100_000
SMALL = 100_000


def collect(queries: list[str]) -> list[dict]:
    seen, out, subs = set(), [], {}
    for q in queries:
        try:
            res = yp.search(q, yp.SP_VIDEO_THIS_YEAR)
        except Exception as e:  # noqa: BLE001
            log.warning("search failed %r: %s", q, e)
            continue
        for v in res:
            if v.video_id in seen or (v.duration_s or 0) < 240 or (v.views or 0) < MIN_VIEWS:
                continue
            seen.add(v.video_id)
            if v.channel_url and v.channel_url not in subs:
                try:
                    subs[v.channel_url] = yp.channel(v.channel_url).subscribers
                except Exception as e:  # noqa: BLE001
                    log.warning("channel lookup failed %s: %s", v.channel_url, e)
                    subs[v.channel_url] = None
            out.append({"id": v.video_id, "title": v.title, "views": v.views, "channel": v.channel,
                        "subs": subs.get(v.channel_url), "query": q, "duration_s": v.duration_s})
    out.sort(key=lambda r: -(r["views"] or 0))
    return out


def sheet(rows: list[dict], path, cols: int = 4) -> None:
    tiles = []
    for i, r in enumerate(rows):
        try:
            b = requests.get(f"https://i.ytimg.com/vi/{r['id']}/mqdefault.jpg", timeout=30).content
            img = cv2.resize(cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR), (480, 270))
        except Exception:  # noqa: BLE001
            img = np.zeros((270, 480, 3), np.uint8)
        tile = np.zeros((300, 480, 3), np.uint8)
        tile[:270] = img
        small = "S" if (r["subs"] or 10**9) < SMALL else ""
        cv2.putText(tile, f"{i} {small} {r['views'] // 1000}k", (6, 292), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (80, 220, 255) if small else (255, 255, 255), 2)
        tiles.append(tile)
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(path), np.vstack([np.hstack(tiles[k:k + cols]) for k in range(0, len(tiles), cols)]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--max", type=int, default=48)
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config" / a.config).read_text())
    rows = collect(cfg["queries"])[: a.max]
    stamp = f"{dt.date.today().isoformat()}_{a.tag}" if a.tag else dt.date.today().isoformat()
    out = ROOT / "research" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"format_study_{stamp}.json").write_text(json.dumps(rows, indent=1))
    for k in range(0, len(rows), 16):
        sheet(rows[k:k + 16], out / f"format_study_{stamp}_{k // 16}.jpg")
    for i, r in enumerate(rows):
        print(f"{i:2d} {r['views']:>10,} {str(r['subs']):>10} {r['channel'][:22]:22} {r['title'][:80]}")


if __name__ == "__main__":
    main()
