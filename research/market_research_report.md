# Market research report — Stage A

Scan date: **2026-10-25**. Raw data: `research/raw/niche_scan_2026-10-25.json`,
`research/raw/niche_scan_deep_2026-10-25.json`. Per-niche metrics:
`research/niche_metrics_2026-10-25.csv`, `research/niche_metrics_deep_2026-10-25.csv`.
Reproduce with `python -m ytauto.research.niche_scan` (from `automation/`).

## Method

For each of 23 niches, 3 evergreen queries were run on public YouTube search twice:
relevance-sorted and filtered to "uploaded this year" (≈ last 12 months). For each niche, the
channels behind this year's best-performing results (≥30k views) plus the top relevance
channels (14–20 per niche) were fetched to read subscriber counts and their ~30 most recent
uploads. A second, broader pass (6–8 queries each) covered the four strongest candidates.

Metrics: median views of last-year uploads, median views/day, count of last-year videos
≥100k views, **small-channel hits** (last-year videos ≥50k views from channels <100k subs),
share of last-year results from small channels, competitor median views per recent upload,
upload frequency, typical duration.

### Limitations (important)
- Public counts are rounded ("1.2M", "3 weeks ago"), so views/day are approximate.
- Search results are a sample of what ranks for a logged-out US-English user, not the full market.
- YouTube's bot check blocks watch-page metadata from this environment; exact upload dates, likes and
  comments were not collected. A YouTube Data API key (free) removes this limitation.
- No impressions, CTR or retention exists for other channels; these are only visible in their own Studio.
- Subscriber counts are a weak proxy for channel age. "Videos" count and oldest of the last 30 uploads were used as age hints.
- Third-party revenue figures are not verified earnings and were not used as evidence.

## Niches investigated (23) — first-pass results (observed)

| Niche | Median views, last-yr uploads | Videos ≥100k (of ~60) | Small-channel hits ≥50k | Small-channel share | Median competitor subs | Typical length (min) |
|---|---|---|---|---|---|---|
| Nature & animals | 580,640 | 39 | 5 | 15% | 222k | 121 |
| History documentaries | 381,104 | 50 | 1 | 2% | 1.05M | 85 |
| Engineering megaprojects | 285,861 | 38 | 6 | 10% | 1.47M | 21 |
| Aviation accidents | 197,339 | 36 | 5 | 16% | 849k | 43 |
| Tech / AI explainers | 177,129 | 35 | 5 | 8% | 454k | 13 |
| Space & astronomy | 175,756 | 37 | 13 | 26% | 521k | 60 |
| Ambient / sleep sounds | 173,396 | 37 | 11 | 18% | 61k | 635 |
| Business case studies | 153,129 | 33 | 17 | 32% | 251k | 16 |
| Mythology | 142,111 | 31 | 6 | 12% | 433k | 73 |
| Sleep history | 119,204 | 27 | 22 | 68% | 95k | 148 |
| General science | 107,454 | 29 | 3 | 7% | 1.91M | 23 |
| Software tutorials | 99,836 | 29 | 4 | 7% | 625k | 20 |
| Maritime disasters | 75,235 | 23 | 8 | 20% | 144k | 41 |
| Personal finance (US) | 72,836 | 27 | 3 | 5% | 585k | 15 |
| Economics explainers | 61,904 | 28 | 2 | 3% | 1.14M | 14 |
| Reddit stories | 45,851 | 19 | 3 | 35% | 226k | 50 |
| True crime | 40,294 | 23 | 11 | 30% | 62k | 50 |
| Philosophy / stoicism | 35,783 | 21 | 8 | 25% | 87k | 34 |
| Data/size comparisons | 20,729 | 16 | 14 | 27% | 41k | 6 |
| Geography / geopolitics | 13,446 | 18 | 0 | 3% | 394k | 12 |
| Learn Dutch | 5,209 | 4 | 7 | 52% | 24k | 23 |
| Psychology | 4,724 | 21 | 7 | 13% | 227k | 12 |
| Personal finance (Dutch) | 3,438 | 6 | 7 | 22% | 39k | 9 |

Deep pass (broader query sets):

| Niche | Last-yr results | Median views | Videos ≥100k | Small-channel hits ≥50k |
|---|---|---|---|---|
| Space explainers (8 queries) | 155 | 105,813 | 80 | **18** |
| Business cases (8 queries) | 157 | 22,020 | 63 | 7 |
| Single-event history (6 queries) | — | 116,859 | 60 | 6 |
| How-things-work science (6 queries) | — | 7,026 | 34 | 8 |

## Strongest competitor evidence (observed, 2026-10-25)

### Space — small channels break out with few, high-quality uploads
| Channel | Subs | Videos | Median views (recent long-form) | Uploads/mo | Notable outlier |
|---|---|---|---|---|---|
| NullSpace | 53.2k | 7 | **1,179,000** | 0.7 | "TON 618: The Black Hole That Breaks the Universe" 2.44M |
| The Astro Explainer | 9.9k | 9 | **313,500** | 1.3 | "The STRANGEST Planets In The Universe" 489k |
| Territory | 130k | 43 | 245,500 | 4.7 | — |
| Astral Curiosity | 51.7k | 35 | 196,000 | 2.7 | 1.8M (uses a famous scientist's name — an impersonation pattern we avoid) |
| Bluntly Explained | 45k | 24 | **151,500** | 5.0 | "Every Type Of Black Hole Explained in 11 Minutes" 1.86M |
| Actual Space | 56.3k | 79 | 118,500 | 1.0 | "The true Scale of the Universe" 1.04M |
| Tracer Project | 2.9k | 29 | 575 | 9.7 | one 4.37M breakout in 9 days ("What If Asteroid Apophis Hit Earth?") |

**Counter-evidence (also observed):** mass-producers that post ≥10 long "sleep" videos a month
have low medians: Space Before After (222 videos) 773; Cosmicus (183) 9,000; Boring Space 3,750;
Sleep On Science (387) 33,000. **Volume is not the winning strategy; distinct, well-packaged topics are.**

Large incumbents (Kurzgesagt 25.8M, What If 9.0M, PBS Space Time 3.5M, Astrum 2.9M) still
dominate the top, so the opportunity is in specific curiosity questions and packaging, not in
out-producing them.

### Business case studies (backup)
| Channel | Subs | Median views | Uploads/mo | Notable outlier |
|---|---|---|---|---|
| The Invisible Game | 56.4k | 184,000 | 4.3 | "The (Overdue) Collapse of Bullsh*t Companies" 2.99M |
| Modern Business | 90k | 263,500 | dormant | "Quiznos Deserves Their Failure" 3.77M |
| Capital Case | 10.6k | 69,500 | 1.3 | — |
| Crayon Capital | 287k | 441,500 | 3.0 | — |
| Fortune & Fall | 1.5k (5 videos) | — | 1.7 | "WTF Happened to Labubu?" 392k in 3 days |

Several large business channels (Think School, HinExp, Abhi and Niyu) serve Indian audiences,
which typically monetize at far lower RPM; the Western-audience segment is thinner but has higher value.

### Sleep history (rejected despite 68% small-channel share)
Nearly every channel uploads ≥10 videos/month of 2–3 h narration; medians are mostly
5–8k views. This is precisely the "mass-produced / templated" pattern YouTube's inauthentic-content
policy targets, and ad value per view is low (much playback happens while viewers sleep).

## Sources
- YouTube public search & channel pages (scan above), 2026-10-25.
- YPP eligibility: https://support.google.com/youtube/answer/72851 (fetched 2026-10-25).
- Monetization policies: https://support.google.com/youtube/answer/1311392 (fetched 2026-10-25).
- RPM dataset: AIR Media-Tech, "YouTube RPM in 2026: real data from 300 channels" https://air.io/en/air-data-findings/how-much-does-youtube-really-pay-in-2026-real-rpm-data-from-300-channels
- See `research/policy_research.md` for the full policy source list.
