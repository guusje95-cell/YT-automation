# Decision report — niche, business model, stack, roadmap

Date: 2026-10-25. Labels: **[Fact]** observed/verified, **[Est]** estimate, **[Assumption]** modelling input, **[Hypothesis]** to be tested.

## 1. Niches investigated (23)
Personal finance (US), personal finance (Dutch), economics explainers, business case studies, geography/geopolitics,
history documentaries, sleep history, space & astronomy, general science, engineering megaprojects, aviation accidents,
maritime disasters, mythology, true crime, psychology, nature & animals, tech/AI explainers, software tutorials,
philosophy/stoicism, data/size comparisons, Reddit stories, ambient/sleep sounds, learn Dutch.
Full data: `research/market_research_report.md`.

## 2. Top five, weighted scores (1–10; weights as briefed)

| Rank | Niche | Demand 15% | Monet. 20% | Compet. 15% | Autom. 20% | Cost 10% | Sustain. 10% | Policy 10% | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Space & astronomy explainers** | 9 | 6 | 8 | 9 | 9 | 9 | 8 | **8.15** |
| 2 | Business case studies | 8 | 8 | 6 | 7 | 8 | 6 | 7 | 7.20 |
| 3 | General science explainers | 8 | 6 | 4 | 7 | 7 | 9 | 8 | 6.80 |
| 4 | History documentaries | 9 | 5 | 4 | 7 | 7 | 9 | 7 | 6.65 |
| 5 | Sleep history | 6 | 4 | 6 | 9 | 9 | 8 | 4 | 6.50 |

Sensitivity: space stays #1 with equal weights (8.29), doubled monetization weight (7.79) and halved automation weight (8.06).
The model is a decision aid; the evidence that actually decides it is below.

**Key trade-offs**
- *Space vs business cases*: business has higher RPM potential **[Est]**, but in the broad scan only 4% of last-year
  ranking uploads came from small channels (space: 18 small-channel hits ≥50k), topics date faster, and visuals
  (company photos, logos) are harder to license. Space has a uniquely deep free, licensed asset base.
- *Sleep history*: easiest to automate and many small channels, but the field is saturated with ≥10 uploads/month, 2–3 h
  AI narrations getting 5–8k medians — the exact "mass-produced" pattern YouTube demonetizes, with low ad value per view.
- *History/science*: strong demand but dominated by million-subscriber incumbents (2–7% small-channel share).

## 3. Strongest competitor evidence [Fact, 2026-10-25]
- **NullSpace**: 53k subs, only 7 videos, median **1.18M** views; top "TON 618: The Black Hole That Breaks the Universe" 2.44M.
- **The Astro Explainer**: 9.9k subs, 9 videos, median **313k**.
- **Bluntly Explained**: 45k subs, 24 videos in ~6 months, median **151k**; "Every Type Of Black Hole Explained in 11 Minutes" 1.86M.
- **Tracer Project**: 2.9k subs; one video hit **4.37M in 9 days** while its median is 575 → topic/packaging dominate.
- Counter-evidence: high-volume "sleep space" channels (Space Before After, 222 videos, median 773; Cosmicus, 183 videos, median 9k).
- **Conclusion [Hypothesis]**: new space channels win with fewer, distinct, well-packaged topics (black holes, scale,
  strange planets, real discoveries), 8–20 min long-form. That suits a quality-gated automated pipeline.

## 4. Monetization and cost assumptions
- **YPP**: 1,000 subs + **8,000 watch hours** (stricter bar reported for applicants from 2027-02-01; planning on it).
  At ~5 min average view duration that is **~96,000 long-form views in 12 months**.
- **RPM [Assumption]**: $2.50 / $4.50 / $8.00 (conservative/base/optimistic). Anchor: AIR Media-Tech measured 2026 data
  (300 channels, Studio data) — Education & Science median $10.22, P25 $2.31. Discounted because space audiences skew
  young and global. RPM ≠ CPM: RPM is after YouTube's 45% share and includes unmonetized views; CPM is typically 1.5–2× higher.
- **Shorts**: Shorts views don't count toward watch hours; Shorts RPM is far lower. Use Shorts only as discovery (derived clips).
- **Other revenue**: sponsorships (e.g. education apps) plausible from ~50k views/month **[Est]**; affiliate (telescopes, books) minor.
- **Costs**: €0 for voice (local Kokoro), assets (NASA/ESA/Openverse), music (generated), rendering (local/CI).
  Optional: LLM API for unattended scripting ≈ €0.30–1.00/video **[Est]**; a small VPS or CI minutes ≈ €0–8/mo.
  **Validation budget: €0–15/month.**
- **Scenarios** (`strategy/financial_model_output.md`): stall → never monetizes, −€374 over 24 months; conservative →
  monetized month 14, ~€120/mo profit by month 24; base → monetized month 8, ~€2.2k/mo by month 24; optimistic → month 3,
  ~€22k/mo. These are scenarios, not forecasts; most new channels end in the stall/conservative range.

## 5. Recommendation
**Primary: space & astronomy explainers for curious adults — "real images, real numbers".**
- **Audience**: English-speaking adults 18–45 (US/UK/CA/AU/NL/Nordics) who watch Kurzgesagt/Astrum/PBS Space Time but
  want short, accurate, hype-free answers to one concrete question.
- **Proposition**: every visual is real mission imagery (NASA/ESA/ESO) or a data-accurate diagram; every number shown
  is sourced on screen and listed in the description. No fake celebrity voices, no fake-disaster bait.
- **Channel name options** (handles unclaimed at check time): **Parsec Notes** (recommended), Kepler Desk, Apoapsis
  Explained, Farlight Explained.
- **Branding**: near-black navy background, warm amber accent, white Inter type, clean data overlays; thumbnails = one
  real celestial object + ≤4 words.
- **Content pillars**: (1) Missions & discoveries ("What Juno found inside Jupiter"); (2) True scale ("How big is X
  really?"), (3) Extreme objects (black holes, magnetars, strange planets); (4) Space history moments.
- **Formats**: 10–16 min explainer (core); monthly 45–60 min compilation of our own episodes (watch-hours); 1–2 Shorts
  cut from each episode (discovery).
- **Schedule**: validation 2 long videos/week for 6 weeks (12 videos), then adjust on data. Not more until retention is proven.
- **Monetization roadmap**: ads (YPP) → sponsorship once ≥50k views/mo → affiliate links in descriptions → optional
  second language channel (e.g. Spanish/German dub via the same pipeline) only after the English channel proves out.
- **Validation test**: after 12 videos / ~6 weeks: target median ≥1,000 views/video by week 6, AVP ≥35%, CTR ≥4%.
  If missed with no single video >10k → change packaging/topics; after 24 videos with no traction → switch to backup.

**Backup: Western-company business case studies, data-driven from SEC filings** (EDGAR XBRL API is free and reachable).

## 6. Automation stack and monthly budget
| Stage | Tool | Cost | Unattended? |
|---|---|---|---|
| Topic research / competitor monitor | `ytauto.research` (public pages now; YouTube Data API with free key) | €0 | Yes |
| Fact collection | Wikipedia REST, NASA, ESA, papers (manual URLs in spec) | €0 | Partly |
| Script + fact-check | LLM (Claude API) drafting + automated validators + human 10-min review | ~€0.5/video | Draft yes; review human |
| Voice | Kokoro-82M local (Apache-2.0); optional ElevenLabs (~$5–22/mo) | €0 | Yes |
| Visuals | NASA Images API, NASA SVS, ESA/Webb, Openverse (CC0/PD/BY) + generated charts/diagrams/titles | €0 | Yes |
| Music | Procedural ambient bed generated locally | €0 | Yes |
| Edit/assembly | Python compositor (OpenCV) + ffmpeg | €0 | Yes |
| Captions | Generated from per-sentence TTS timings (SRT) | €0 | Yes |
| Thumbnail | PIL templates + real imagery, 3 variants | €0 | Yes |
| Metadata | Templates + LLM; sources & credits auto-listed | €0 | Yes |
| QA | Automated checks (loudness, duration, black frames, licences, script lint) | €0 | Yes |
| Publish | YouTube Data API (OAuth), private/scheduled upload | €0 | After one-time OAuth |
| Analytics | YouTube Analytics API → weekly report | €0 | Yes |
**Total during validation: €0–15/month.**

## 7. Key risks and uncertainties
1. **Traction risk** (largest): most new channels stall. Mitigation: packaging tests, topic selection from outlier data, kill criteria.
2. **Inauthentic-content enforcement** on AI-assisted channels. Mitigation: distinct topics, sourced facts, original
   diagrams, human editorial review, no templated filler, modest cadence.
3. **8,000-hour threshold** (if confirmed) doubles time to monetization.
4. **Voice quality**: local TTS may underperform premium voices on retention. Mitigation: A/B one batch with a paid voice.
5. **RPM uncertainty** (no space-specific data). Mitigation: measure from first monetized month.
6. **Accuracy**: an LLM-drafted script can contain errors. Mitigation: claim-level sourcing, validators, human review gate.
7. **Content ID false claims** on public-domain material (rare). Mitigation: generated music; NASA/ESA visuals.
8. **Platform/tooling drift** (public page parsing breaks). Mitigation: Data API backend.

## 8. Roadmap
- **Week 0 (now)**: build and test pipeline; produce pilot + 2 more videos (this session).
- **Week 1**: you create channel + Google Cloud project, run one OAuth command; upload pilot privately, review, publish.
- **Weeks 1–6**: 2 videos/week; weekly automated report; packaging experiments.
- **Week 6 checkpoint**: go / adjust / switch decision on the validation targets above.
- **Months 2–6**: optimise toward 8,000 h; add compilations and Shorts; add LLM API for unattended drafting.
- **Month 6+**: sponsorship outreach templates; consider second language only with proven retention.

## 9. Immediate tasks (executing now)
1. Build the modular pipeline (spec → voice → visuals → video → captions → thumbnail → metadata → QA → publish prep).
2. Research and write the pilot ("What NASA's Juno Found Inside Jupiter") with claim-level sources.
3. Render, QA, fix, and package the pilot; then two more episodes to test repeatability.
4. Prepare the YouTube uploader and analytics collector (dry-run tested), with setup docs for your one-time OAuth step.
