"""Atlassian opportunity scan: demand (votes on unresolved feature requests) vs. supply (Marketplace apps).

Demand: public Atlassian issue tracker (jira.atlassian.com), Suggestions that are unresolved, sorted by votes.
Supply: Atlassian Marketplace REST API v2, cloud apps that match the request's keywords.
An unmet request with many votes and few or weak cloud apps = an app opportunity.

Run: python income_lab/models/atlassian_opportunity_scan.py [--n 60]
Output: income_lab/research/atlassian_opportunities_<date>.csv + .md
No login required; read-only public endpoints; ~1 request/second.
"""
import argparse
import csv
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "income-lab-research/0.1"}
STOP = set("""a an the to of in on for and or with by from as at be is are can should allow ability option
support add new when not into its it this that per all any via jira confluence cloud issue issues page pages
field fields project projects team managed user users formerly""".split())
PRODUCTS = {"JRACLOUD": "jira", "CONFCLOUD": "confluence", "JSDCLOUD": "jira"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def suggestions(project, n):
    jql = f"project={project} AND issuetype=Suggestion AND resolution=Unresolved ORDER BY votes DESC"
    url = ("https://jira.atlassian.com/rest/api/2/search?" +
           urllib.parse.urlencode({"jql": jql, "maxResults": n, "fields": "summary,votes,created"}))
    return get(url).get("issues", [])


def keywords(summary, k=4):
    words = [w for w in re.findall(r"[a-zA-Z]{3,}", summary.lower()) if w not in STOP]
    return " ".join(words[:k])


def supply(app, text):
    url = ("https://marketplace.atlassian.com/rest/2/addons?" +
           urllib.parse.urlencode({"application": app, "hosting": "cloud", "text": text, "limit": 5}))
    d = get(url)
    addons = d.get("_embedded", {}).get("addons", [])
    if not addons:
        return d.get("count", 0), 0, ""
    inst = lambda a: a.get("_embedded", {}).get("distribution", {}).get("totalInstalls", 0) or 0  # noqa: E731
    top = max(addons, key=inst)  # biggest app among the 5 most relevant hits
    return d.get("count", 0), inst(top), top["name"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="suggestions per project")
    args = ap.parse_args()
    rows = []
    for proj, app in PRODUCTS.items():
        for it in suggestions(proj, args.n):
            s = it["fields"]["summary"]
            votes = it["fields"]["votes"]["votes"]
            kw = keywords(s)
            try:
                cnt, top_inst, top_name = supply(app, kw)
            except Exception as e:  # noqa: BLE001 - research script, keep going
                cnt, top_inst, top_name = -1, -1, f"error: {e}"
            # opportunity: high demand, weak supply (heuristic [E])
            opp = votes / (1 + cnt) / (1 + top_inst / 5000)
            rows.append(dict(key=it["key"], product=app, votes=votes, summary=s, query=kw,
                             cloud_apps_matching=cnt, top_app_installs=top_inst, top_app=top_name,
                             created=it["fields"]["created"][:10], opportunity=round(opp, 1)))
            time.sleep(1)
    rows.sort(key=lambda r: r["opportunity"], reverse=True)
    out = Path(__file__).resolve().parents[1] / "research"
    stamp = dt.date.today().isoformat()
    with open(out / f"atlassian_opportunities_{stamp}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = [f"# Atlassian opportunity scan ({stamp})", "",
          "Demand = votes on unresolved Atlassian Suggestions. Supply = matching cloud apps (keyword search, "
          "rough). Opportunity = votes / (1+apps) / (1+top installs/5000) [heuristic]. "
          "**Check every hit manually**: keyword matching misses synonyms, and some requests are core features "
          "Atlassian may still build itself.", "",
          "| # | Key | Product | Votes | Request | Matching apps | Top app (installs) | Score |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows[:40], 1):
        md.append(f"| {i} | {r['key']} | {r['product']} | {r['votes']} | {r['summary'][:90]} | "
                  f"{r['cloud_apps_matching']} | {r['top_app'][:40]} ({r['top_app_installs']}) | {r['opportunity']} |")
    (out / f"atlassian_opportunities_{stamp}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
