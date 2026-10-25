"""Analytics collection and the weekly performance report.

Data sources:
  - YouTube Analytics API (views, watch time, AVD, AVP, subs, revenue, retention) — needs OAuth token
  - Studio CSV export for impressions + CTR (not exposed by the Analytics API): drop the
    "Table data.csv" from Studio > Analytics > Advanced > Content into analytics/imports/
  - production_log.json files for cost/time per video

Method: every video is compared with the channel's own baseline (median of earlier
videos at the same age), never with universal benchmarks. Recommendations require
a minimum sample; small samples are reported as "insufficient data", not as findings.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
import statistics as st
from pathlib import Path

from ytauto.core import config
from ytauto.core.log import get_logger

log = get_logger(__name__)

ADIR = config.ANALYTICS_DIR
METRICS = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
           "subscribersGained,subscribersLost,likes,shares")
MONEY = "estimatedRevenue,playbackBasedCpm"
MIN_VIDEOS_FOR_PATTERNS = 6


def _published_videos() -> list[dict]:
    out = []
    for p in config.OUTPUT_DIR.glob("*/publish_result.json"):
        r = json.loads(p.read_text())
        meta = json.loads((p.parent / "metadata.json").read_text())
        spec_p = config.CONTENT_DIR / p.parent.name / "spec.yaml"
        import yaml
        sd = yaml.safe_load(spec_p.read_text()) if spec_p.exists() else {}
        out.append({"local_id": p.parent.name, "yt_id": r["video_id"], "title": meta["title"],
                    "pillar": sd.get("pillar"), "duration_min": None})
    return out


def collect(days: int = 28) -> list[dict]:
    from googleapiclient.discovery import build
    from ytauto.publish.youtube import credentials
    creds = credentials()
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    rows = []
    for v in _published_videos():
        info = yt.videos().list(part="snippet,contentDetails,statistics", id=v["yt_id"]).execute()["items"]
        if not info:
            continue
        pub = info[0]["snippet"]["publishedAt"][:10]
        r = ya.reports().query(ids="channel==MINE", startDate=pub, endDate=end.isoformat(),
                               metrics=METRICS, filters=f"video=={v['yt_id']}").execute()
        vals = dict(zip([h["name"] for h in r["columnHeaders"]], (r.get("rows") or [[0] * 8])[0]))
        try:
            m = ya.reports().query(ids="channel==MINE", startDate=pub, endDate=end.isoformat(), metrics=MONEY,
                                   filters=f"video=={v['yt_id']}").execute()
            vals.update(dict(zip([h["name"] for h in m["columnHeaders"]], (m.get("rows") or [[0, 0]])[0])))
        except Exception as e:  # not monetized yet / no monetary scope
            log.info("no revenue data: %s", e)
        ret = ya.reports().query(ids="channel==MINE", startDate=pub, endDate=end.isoformat(),
                                 metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
                                 filters=f"video=={v['yt_id']}").execute()
        rows.append({**v, "published": pub, **vals, "retention": ret.get("rows", [])})
    snap = ADIR / "raw" / f"snapshot_{end.isoformat()}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(rows, indent=1))
    return rows


def mock_rows(n: int = 8, seed: int = 1) -> list[dict]:
    """Synthetic data for testing the report logic. Never presented as real performance."""
    rng = random.Random(seed)
    pillars = ["missions-and-discoveries", "true-scale", "extreme-objects", "space-history"]
    rows = []
    for i in range(n):
        views = int(rng.lognormvariate(7, 1.1))
        avd = rng.uniform(2.5, 5.5)
        ret = [[k / 20, max(0.05, 1.0 - 0.35 * (k > 0) - 0.03 * k + rng.uniform(-0.03, 0.03))] for k in range(21)]
        rows.append({"local_id": f"mock-{i}", "yt_id": f"MOCK{i}", "title": f"Mock video {i}",
                     "pillar": pillars[i % 4], "published": (dt.date.today() - dt.timedelta(days=7 * (n - i))).isoformat(),
                     "views": views, "estimatedMinutesWatched": views * avd, "averageViewDuration": avd * 60,
                     "averageViewPercentage": avd / 10 * 100, "subscribersGained": int(views * 0.008),
                     "subscribersLost": int(views * 0.001), "likes": int(views * 0.03), "shares": int(views * 0.004),
                     "estimatedRevenue": 0.0, "retention": ret,
                     "impressions": int(views / rng.uniform(0.03, 0.08)), "ctr": rng.uniform(3, 8)})
    return rows


def _studio_ctr() -> dict:
    """Merge impressions/CTR from Studio CSV exports in analytics/imports/ (keyed by video id)."""
    out = {}
    for p in (ADIR / "imports").glob("*.csv"):
        with p.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                vid = row.get("Content") or row.get("Video")
                if not vid:
                    continue
                try:
                    out[vid] = {"impressions": float(row.get("Impressions", 0) or 0),
                                "ctr": float(row.get("Impressions click-through rate (%)", 0) or 0)}
                except ValueError:
                    pass
    return out


def _costs() -> dict:
    out = {}
    for p in config.OUTPUT_DIR.glob("*/production_log.json"):
        runs = json.loads(p.read_text())
        last = runs[-1]
        out[p.parent.name] = {"compute_min": round(last["total_seconds"] / 60, 1),
                              "cost_eur": sum(v for v in last["cost_eur"].values() if isinstance(v, (int, float)))}
    return out


def analyse(rows: list[dict]) -> dict:
    ctr = _studio_ctr()
    for r in rows:
        r.update(ctr.get(r["yt_id"], {}))
    n = len(rows)
    findings, recs = [], []
    if n == 0:
        return {"n": 0, "findings": ["No published videos yet."], "recs": []}
    med_views = st.median(r["views"] for r in rows)
    med_avp = st.median(r["averageViewPercentage"] for r in rows)
    for r in rows:
        r["views_vs_baseline"] = round(r["views"] / med_views, 2) if med_views else None
        r["avp_vs_baseline"] = round(r["averageViewPercentage"] - med_avp, 1)
        if r.get("retention"):
            first30 = [y for x, y in r["retention"] if x <= 0.06]
            r["hook_retention"] = round(min(first30), 2) if first30 else None
    if n < MIN_VIDEOS_FOR_PATTERNS:
        findings.append(f"Only {n} videos: too few to compare topics/formats reliably (need ≥{MIN_VIDEOS_FOR_PATTERNS}). "
                        "Per-video notes only.")
    else:
        by_p: dict[str, list] = {}
        for r in rows:
            by_p.setdefault(r.get("pillar") or "unknown", []).append(r)
        for p, rs in sorted(by_p.items(), key=lambda kv: -st.median(x["views"] for x in kv[1])):
            findings.append(f"Pillar '{p}': {len(rs)} videos, median views {st.median(x['views'] for x in rs):,.0f}, "
                            f"median AVP {st.median(x['averageViewPercentage'] for x in rs):.0f}%"
                            + (" (n<3: treat as anecdotal)" if len(rs) < 3 else ""))
    for r in rows:
        if r.get("hook_retention") is not None and r["hook_retention"] < 0.6:
            recs.append(f"{r['title']}: {100 - r['hook_retention'] * 100:.0f}% of viewers leave in the first ~6% of the "
                        "video. Rework the opening: state the payoff within 15 s, cut setup.")
        if r.get("ctr") is not None and r.get("impressions", 0) > 1000 and r["ctr"] < 3.5:
            recs.append(f"{r['title']}: CTR {r['ctr']:.1f}% on {r['impressions']:,.0f} impressions — test thumbnail "
                        "variant 2/3 via Test & Compare (do not attribute changes without the test result).")
        if r["views_vs_baseline"] and r["views_vs_baseline"] >= 3:
            recs.append(f"{r['title']}: {r['views_vs_baseline']}× the channel median — queue 2 follow-up topics in the "
                        "same pillar/angle.")
    return {"n": n, "median_views": med_views, "median_avp": med_avp, "rows": rows, "findings": findings, "recs": recs}


def write_report(a: dict, mock: bool = False) -> str:
    today = dt.date.today().isoformat()
    costs = _costs()
    lines = [f"# Weekly channel report — {today}", ""]
    if mock:
        lines += ["> **MOCK DATA** — generated to test the report pipeline. Not real channel performance.", ""]
    lines += [f"Videos analysed: {a['n']}" + (f" · channel median views {a['median_views']:,.0f} · median AVP "
                                               f"{a['median_avp']:.0f}%" if a['n'] else ""), "", "## Per video", "",
              "| Video | Pillar | Views | ×median | AVP | Hook retention | CTR | Subs | Compute min | Cost € |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in a.get("rows", []):
        c = costs.get(r["local_id"], {})
        lines.append(f"| {r['title']} | {r.get('pillar') or ''} | {r['views']:,} | {r['views_vs_baseline']} | "
                     f"{r['averageViewPercentage']:.0f}% | {r.get('hook_retention', '')} | "
                     f"{(str(round(r['ctr'], 1)) + '%') if r.get('ctr') is not None else 'n/a'} | "
                     f"{r['subscribersGained'] - r['subscribersLost']} | {c.get('compute_min', '')} | {c.get('cost_eur', '')} |")
    lines += ["", "## Findings", ""] + [f"- {f}" for f in a["findings"]]
    lines += ["", "## Recommendations", ""] + ([f"- {r}" for r in a["recs"]] or ["- None this week."])
    lines += ["", "_Comparisons are against this channel's own median. Causal claims about packaging changes are only "
                  "made from YouTube Test & Compare results._"]
    out = ADIR / f"weekly_report_{today}{'_MOCK' if mock else ''}.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


def run(days: int = 28, mock: bool = False) -> str:
    rows = mock_rows() if mock else collect(days)
    return write_report(analyse(rows), mock=mock)
