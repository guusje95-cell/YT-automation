"""Topic scan: which subject should the next episode be about?

For each candidate topic, one YouTube search filtered to uploads from the past year; Shorts and clips under
4 minutes are dropped. Per topic:
  demand      median views of the 8 best-performing results (the ceiling a good video on the topic reaches; the
              median of *all* results mostly measures how many tiny uploads the search mixes in)
  hits        results with >=100k views
  velocity    median views per day of those top 8
  breakouts   results with >=100k views from channels under 100k subscribers (can a newcomer win here?)
  big_hits    results with >=1M views
  assets      licence-clean NASA images for the topic (can we illustrate it truthfully?)
Scores are percentile ranks within the batch (robust to one viral outlier). Weights: demand 25%, hits 20%,
breakouts 25%, velocity 15%, assets 15%. Each topic is searched with every query in `queries` and results are pooled. A decision aid from public counts, not a forecast.

  python -m ytauto.research.topic_scan            # uses config/topic_candidates.yaml
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st

import yaml

from ytauto.core.log import ROOT, get_logger
from ytauto.research import youtube_public as yp

log = get_logger(__name__)

WEIGHTS = {"demand": 0.25, "hits": 0.20, "breakouts": 0.25, "velocity": 0.15, "assets": 0.15}
TOP_N = 8
SMALL_CHANNEL = 100_000
MIN_DURATION = 240


def _pct_rank(values: list[float]) -> list[float]:
    """Percentile rank 0..10 (ties share the average rank)."""
    order = sorted(values)
    n = len(values)
    out = []
    for v in values:
        lo = order.index(v)
        hi = n - 1 - order[::-1].index(v)
        out.append(round(10 * ((lo + hi) / 2) / max(n - 1, 1), 2))
    return out


def scan(topics: list[dict], with_assets: bool = True) -> list[dict]:
    from ytauto.assets.fetch import nasa_usable
    subs_cache: dict[str, int | None] = {}
    for t in topics:
        pooled = {}
        for q in t.get("queries") or [t["query"]]:
            for v in yp.search(q, yp.SP_VIDEO_THIS_YEAR):
                if v.views and (v.duration_s or 0) >= MIN_DURATION:
                    pooled[v.video_id] = v
        res = list(pooled.values())
        top = sorted(res, key=lambda v: -v.views)[:TOP_N]
        views = [v.views for v in res]
        vpd = [v.views_per_day() for v in top if v.views_per_day()]
        breakouts = []
        for v in res:
            if v.views >= 100_000 and v.channel_url:
                if v.channel_url not in subs_cache:
                    try:
                        subs_cache[v.channel_url] = yp.channel(v.channel_url).subscribers
                    except Exception as e:  # keep scanning; unknown size is not counted as small
                        log.warning("channel lookup failed for %s: %s", v.channel_url, e)
                        subs_cache[v.channel_url] = None
                subs = subs_cache[v.channel_url]
                if subs is not None and subs < SMALL_CHANNEL:
                    breakouts.append({"title": v.title, "views": v.views, "channel": v.channel, "subs": subs,
                                      "url": f"https://www.youtube.com/watch?v={v.video_id}"})
        t.update({
            "n_results": len(res),
            "demand_raw": st.median([v.views for v in top]) if top else 0,
            "hits_raw": sum(1 for x in views if x >= 100_000),
            "velocity_raw": round(st.median(vpd), 1) if vpd else 0,
            "breakouts_raw": len(breakouts),
            "big_hits": sum(1 for x in views if x >= 1_000_000),
            "top": sorted(({"title": v.title, "views": v.views, "channel": v.channel} for v in res),
                          key=lambda x: -x["views"])[:3],
            "breakout_examples": sorted(breakouts, key=lambda x: -x["views"])[:3],
            "assets_raw": len(nasa_usable(t.get("asset_query", t["topic"]), n=25)) if with_assets else 0,
        })
        log.info("topic %-45s median %8.0f  vpd %7.1f  breakouts %d  assets %d", t["topic"], t["demand_raw"],
                 t["velocity_raw"], t["breakouts_raw"], t["assets_raw"])
    for k in WEIGHTS:
        for t, s in zip(topics, _pct_rank([t[f"{k}_raw"] for t in topics])):
            t[f"{k}_score"] = s
    for t in topics:
        t["score"] = round(sum(WEIGHTS[k] * t[f"{k}_score"] for k in WEIGHTS), 2)
    topics.sort(key=lambda t: -t["score"])
    return topics


def report(topics: list[dict]) -> str:
    today = dt.date.today().isoformat()
    lines = [f"# Topic scan — {today}", "",
             "Past-year YouTube search results per topic (two queries pooled), long-form only (≥4 min). Demand = median "
             "views of the top 8 results. Breakout = ≥100k views from a channel under 100k subscribers. Scores are "
             "percentile ranks within this batch; weights: demand 25%, ≥100k results 20%, breakouts 25%, velocity 15%, "
             "assets 15%. Public counts at scan time; a decision aid, not a forecast.", "",
             "| # | Topic | Score | Top-8 median views | ≥100k results | Views/day (top 8) | Breakouts | ≥1M | NASA assets |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, t in enumerate(topics, 1):
        lines.append(f"| {i} | {t['topic']} | **{t['score']}** | {t['demand_raw']:,.0f} | {t['hits_raw']} | "
                     f"{t['velocity_raw']:,.0f} | {t['breakouts_raw']} | {t['big_hits']} | {t['assets_raw']} |")
    lines += ["", "## Evidence per topic (top results and small-channel breakouts)", ""]
    for t in topics:
        qs = ", ".join(f"`{q}`" for q in (t.get("queries") or [t["query"]]))
        lines.append(f"**{t['topic']}** (queries: {qs}; {t['n_results']} long-form results)")
        for x in t["top"]:
            lines.append(f"- top: {x['views']:,} — {x['title']} ({x['channel']})")
        for x in t["breakout_examples"]:
            lines.append(f"- breakout: {x['views']:,} — [{x['title']}]({x['url']}) ({x['channel']}, {x['subs']:,} subs)")
        lines.append("")
    out = ROOT / "research" / f"topic_scan_{today}.md"
    out.write_text("\n".join(lines))
    (ROOT / "research" / "raw" / f"topic_scan_{today}.json").write_text(json.dumps(topics, indent=1))
    return str(out)


def main():
    cands = yaml.safe_load((ROOT / "config" / "topic_candidates.yaml").read_text())["topics"]
    print(report(scan(cands)))


if __name__ == "__main__":
    main()
