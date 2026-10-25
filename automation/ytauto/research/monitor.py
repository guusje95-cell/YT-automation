"""Competitor monitoring and topic scoring.

monitor.run(): fetch each configured competitor's recent uploads, flag outliers
(>= N x that channel's own median) and write research/competitor_outliers_<date>.md.

score_topics(): rank candidate topics for the next episodes by
  demand      median views of last-year search results for the topic query
  freshness   share of last-year results (is the topic still being watched?)
  gap         share of results from small channels (can a newcomer rank?)
  assets      number of licence-clean NASA images available (can we illustrate it truthfully?)
Scores are relative within the candidate batch (0-10). A decision aid, not a verdict.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st

import yaml

from ytauto.core.log import ROOT, get_logger
from ytauto.research import youtube_public as yp

log = get_logger(__name__)


def run(config_name: str = "competitors.yaml") -> str:
    cfg = yaml.safe_load((ROOT / "config" / config_name).read_text())
    mult, max_age = cfg.get("outlier_multiple", 3.0), cfg.get("max_age_days", 120)
    rows = []
    for handle in cfg["channels"]:
        try:
            ch = yp.channel(handle)
        except Exception as e:
            log.warning("monitor: %s failed: %s", handle, e)
            continue
        vids = [v for v in ch.recent_videos if v.views and (v.duration_s or 600) >= 180]
        if len(vids) < 4:
            continue
        med = st.median(v.views for v in vids)
        for v in vids:
            if v.age_days is not None and v.age_days <= max_age and v.views >= mult * med:
                rows.append({"channel": ch.title, "subs": ch.subscribers, "title": v.title, "views": v.views,
                             "age_days": round(v.age_days), "x_median": round(v.views / med, 1),
                             "url": f"https://www.youtube.com/watch?v={v.video_id}"})
    rows.sort(key=lambda r: -r["x_median"])
    today = dt.date.today().isoformat()
    lines = [f"# Competitor outliers — {today}", "",
             f"Uploads ≤{max_age} days old with ≥{mult}× their channel's recent median views (public counts).", "",
             "| × median | Views | Age (d) | Channel (subs) | Title |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['x_median']} | {r['views']:,} | {r['age_days']} | {r['channel']} ({(r['subs'] or 0):,}) | "
                     f"[{r['title']}]({r['url']}) |")
    if not rows:
        lines.append("| – | – | – | – | no outliers this period |")
    out = ROOT / "research" / f"competitor_outliers_{today}.md"
    out.write_text("\n".join(lines) + "\n")
    (ROOT / "research" / "raw" / f"competitor_outliers_{today}.json").write_text(json.dumps(rows, indent=1))
    return str(out)


def score_topics(topics: list[dict], with_assets: bool = True) -> list[dict]:
    """topics: [{"topic": "...", "query": "...", "asset_query": "..."}] -> same dicts with scores, sorted."""
    from ytauto.assets.fetch import nasa_usable
    for t in topics:
        year = yp.search(t["query"], yp.SP_VIDEO_THIS_YEAR)
        views = [v.views for v in year if v.views]
        t["demand_raw"] = st.median(views) if views else 0
        t["n_100k"] = sum(1 for v in views if v >= 100_000)
        t["assets_raw"] = len(nasa_usable(t.get("asset_query", t["topic"]), n=25)) if with_assets else None
    def rel(key):
        vals = [t[key] for t in topics if t[key] is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0, 1)
        for t in topics:
            t[key.replace("_raw", "_score")] = round(10 * (t[key] - lo) / (hi - lo), 1) if t[key] is not None and hi > lo else 5.0
    rel("demand_raw")
    if with_assets:
        rel("assets_raw")
    for t in topics:
        t["score"] = round(0.6 * t["demand_score"] + 0.4 * t.get("assets_score", 5.0), 2)
    topics.sort(key=lambda t: -t["score"])
    return topics
