"""Scan candidate niches on YouTube and compute opportunity metrics.

Usage:  python -m ytauto.research.niche_scan [--niches a,b] [--channels-per-niche 10]

Writes research/raw/niche_scan_<date>.json (all observations) and
research/niche_metrics_<date>.csv (one row per niche). All numbers are
observed public counts at scan time; view counts and ages are rounded by
YouTube ("3 weeks ago", "1.2M"), so treat derived rates as approximate.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics as st
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

import yaml

from ytauto.core.log import get_logger, ROOT
from ytauto.research import youtube_public as yp

log = get_logger(__name__)

SMALL_CHANNEL_SUBS = 100_000


def _median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def channel_stats(ch: yp.Channel) -> dict:
    vids = [v for v in ch.recent_videos if v.views is not None]
    long_vids = [v for v in vids if (v.duration_s or 0) >= 180]
    views = [v.views for v in long_vids] or [v.views for v in vids]
    med = _median(views)
    last90 = [v for v in ch.recent_videos if v.age_days is not None and v.age_days <= 92]
    ages = [v.age_days for v in ch.recent_videos if v.age_days is not None]
    outliers = [v for v in long_vids if med and v.views >= 3 * med]
    return {
        "title": ch.title, "url": ch.url, "channel_id": ch.channel_id,
        "subscribers": ch.subscribers, "video_count": ch.video_count,
        "median_views_recent": med,
        "uploads_per_month": round(len(last90) / 3, 1),
        "oldest_recent_upload_days": max(ages) if ages else None,
        "median_duration_min": round((_median([v.duration_s for v in long_vids]) or 0) / 60, 1),
        "views_per_sub": round(med / ch.subscribers, 3) if med and ch.subscribers else None,
        "outliers": [{"title": v.title, "views": v.views, "age_days": v.age_days,
                      "x_median": round(v.views / med, 1)} for v in
                     sorted(outliers, key=lambda v: -v.views)[:5]],
        "top_recent": [{"title": v.title, "views": v.views, "age_days": v.age_days}
                       for v in sorted(vids, key=lambda v: -(v.views or 0))[:5]],
    }


def scan_niche(key: str, cfg: dict, channels_per_niche: int) -> dict:
    rel, year = [], []
    for q in cfg["queries"]:
        try:
            rel += yp.search(q, yp.SP_VIDEO)
            year += yp.search(q, yp.SP_VIDEO_THIS_YEAR)
        except Exception as e:  # keep scanning other queries
            log.error("search failed for %r: %s", q, e)
    # Channels behind this year's well-performing uploads are the live
    # competition (and reveal whether small channels break through).
    picked: list[str] = []
    for v in sorted(year, key=lambda v: -(v.views or 0)):
        if v.channel_url and v.channel_url not in picked and (v.views or 0) >= 30_000:
            picked.append(v.channel_url)
    weight = Counter()
    for v in rel:
        if v.channel_url:
            weight[v.channel_url] += (v.views or 0) ** 0.5
    for url, _ in weight.most_common():
        if len(picked) >= channels_per_niche + 4:
            break
        if url not in picked:
            picked.append(url)
    chans = {}
    for url in picked[:channels_per_niche + 4]:
        try:
            chans[url] = channel_stats(yp.channel(url))
        except Exception as e:
            log.error("channel fetch failed %s: %s", url, e)
    subs_of = {u: c["subscribers"] for u, c in chans.items()}

    year_uniq = {v.video_id: v for v in year}.values()
    rel_uniq = {v.video_id: v for v in rel}.values()
    small_hits = [v for v in year_uniq
                  if (v.views or 0) >= 50_000 and subs_of.get(v.channel_url) is not None
                  and subs_of[v.channel_url] < SMALL_CHANNEL_SUBS]
    known_small = [v for v in year_uniq if subs_of.get(v.channel_url) is not None
                   and subs_of[v.channel_url] < SMALL_CHANNEL_SUBS]
    metrics = {
        "niche": key, "label": cfg["label"],
        "n_videos_rel": len(rel_uniq), "n_videos_year": len(year_uniq),
        "median_views_rel": _median([v.views for v in rel_uniq]),
        "median_views_year": _median([v.views for v in year_uniq]),
        "median_vpd_year": _median([v.views_per_day() for v in year_uniq]),
        "n_year_ge_100k": sum(1 for v in year_uniq if (v.views or 0) >= 100_000),
        "small_channel_hits_50k": len(small_hits),
        "small_channel_share_year": round(len(known_small) / max(len(year_uniq), 1), 2),
        "median_subs_competitors": _median([c["subscribers"] for c in chans.values()]),
        "median_channel_median_views": _median([c["median_views_recent"] for c in chans.values()]),
        "median_duration_min_year": round((_median([v.duration_s for v in year_uniq]) or 0) / 60, 1),
        "distinct_channels_year": len({v.channel_url for v in year_uniq}),
        "rpm_low": cfg["rpm_band"][0], "rpm_high": cfg["rpm_band"][1],
    }
    log.info("niche %s: %s", key, {k: metrics[k] for k in
             ("median_views_year", "n_year_ge_100k", "small_channel_hits_50k", "median_subs_competitors")})
    return {
        "metrics": metrics,
        "channels": chans,
        "small_channel_hits": [asdict(v) | {"subs": subs_of.get(v.channel_url)} for v in
                               sorted(small_hits, key=lambda v: -(v.views or 0))[:10]],
        "videos_year": [asdict(v) for v in year_uniq],
        "videos_rel": [asdict(v) for v in rel_uniq],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--niches", default="")
    ap.add_argument("--channels-per-niche", type=int, default=10)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--config", default="niches.yaml")
    ap.add_argument("--tag", default="")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load((ROOT / "config" / a.config).read_text())["niches"]
    keys = [k for k in cfg if not a.niches or k in a.niches.split(",")]
    with ThreadPoolExecutor(a.workers) as ex:
        results = dict(zip(keys, ex.map(lambda k: scan_niche(k, cfg[k], a.channels_per_niche), keys)))
    stamp = dt.date.today().isoformat()
    raw = ROOT / "research" / "raw" / f"niche_scan{a.tag}_{stamp}.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps({"scanned_at": dt.datetime.now().isoformat(), "results": results}, indent=1))
    rows = [r["metrics"] for r in results.values()]
    out = ROOT / "research" / f"niche_metrics{a.tag}_{stamp}.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %s and %s", raw, out)


if __name__ == "__main__":
    main()
