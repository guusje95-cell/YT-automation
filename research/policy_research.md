# Policy, licensing and legal research

Checked 2026-10-25. Confidence: **High** = official primary source read; **Medium** = multiple
consistent secondary sources; **Low** = single secondary source.

## YouTube Partner Program (YPP)

| Claim | Confidence | Source |
|---|---|---|
| Current ad-revenue tier: 1,000 subs + 4,000 public watch hours (12 mo) **or** 10M Shorts views (90 days) | High | support.google.com/youtube/answer/72851 |
| A YPP update takes effect **2027-02-01**; partners must accept new terms by 2027-01-31 | High | same page |
| From 2027-02-01 new applicants need **8,000 watch hours** or **20M Shorts views**; 1,000 subs unchanged; existing partners unaffected | Medium (Metricool 2026-08-14, Socialday, AIR, OutlierKit; links to an official YouTube blog post that was unreachable from here) | metricool.com/youtube-partner-program-2027-changes |
| Shorts revenue for partners would require 10M Shorts views in trailing 90 days | Low–Medium | Metricool, AIR |
| Also required: no active Community Guidelines strikes, 2-Step Verification, linked AdSense, living in an eligible country | Medium | tella.com and others |

**Planning decision:** a new channel cannot realistically reach 4,000 hours before 2027-01-31, so the plan
assumes the **8,000-hour bar**. This favours long-form videos with strong retention over Shorts.

## Monetization content policies (official, support.google.com/youtube/answer/1311392)

- **Inauthentic content** (renamed from "repetitious", 2025-07-15): mass-produced or repetitive content is
  ineligible, e.g. "image slideshows, templated storylines, or scrolling text with minimal or no narrative" and
  "AI-generated content made with generic or unoriginal templates". Similar formats are fine when each video has a
  distinct storyline, focus or concept. YouTube evaluates the **channel as a whole**.
- **Reused content**: taking others' content with minimal changes is ineligible *even with permission*.
- **Automation is allowed** if "the final product must still demonstrate your creative vision and provide
  educational or entertainment value".
- **AI personas**: channels using AI personas presenting as experts giving medical, financial, legal or political
  advice cannot monetize. → Avoid finance-advice niches with an AI narrator; our space narrator is a narrator, not a persona claiming expertise.
- **Unsatisfying/off-putting content**: shock-driven formulas, fake disasters (e.g. "realistic visuals tricking viewers
  into believing a … natural disaster has occurred") are ineligible. → No fake "asteroid is coming" framing.

### Altered or synthetic content disclosure (since March 2024)
Creators must disclose *realistic* altered/synthetic content (e.g. a realistic event that didn't happen, a real
person's synthetic voice/face). Not required for clearly unrealistic/animated content or for AI used as production
assistance (e.g. scripts, captions). **Our approach:** synthetic narration is not a real person's voice; but if we
include any realistic AI-generated imagery we tick the disclosure. The API exposes `status.containsSyntheticMedia`;
our uploader sets it from the video manifest. We state "narration voice is synthetic" in every description (trust, low cost).

## YouTube Data API (developers.google.com/youtube/v3)
- Default quota 10,000 units/day. `videos.insert` listed at 1 unit with a separate 100-calls/day limit;
  `thumbnails.set` 50; `captions.insert` 400; `playlistItems.insert` 50. (High; quota cost page, fetched 2026-10-25.)
- `status.publishAt` enables scheduled publishing (video must be private until then).
- The `videos.insert` page currently states uploads from unverified API projects are **not** restricted to private
  (historically they were). We will still verify on the first upload, which we make as **private**.
- OAuth 2.0 (installed-app flow) is required for uploads; an API key alone suffices for read-only research.

## Asset licensing (primary sources)
| Source | Licence | Conditions |
|---|---|---|
| NASA images/video (images.nasa.gov, NASA SVS) | Generally not copyrighted in the US | Credit NASA; no implied endorsement; NASA insignia/logos protected; third-party-marked items excluded; identifiable astronauts need care. nasa.gov/nasa-brand-center/images-and-media |
| ESA/Webb, ESA/Hubble | CC BY 4.0 | Full credit line unaltered, visible; no endorsement; logos excluded; note significant modifications. esawebb.org/copyright |
| ESO | CC BY 4.0 (per ESO copyright page) | Credit "ESO" — verify per image |
| Openverse / Wikimedia Commons | Per-file (CC0, PD, CC BY, CC BY-SA) | Pipeline only accepts CC0/PD/CC BY/CC BY-SA and records attribution |
| Music | Procedurally generated in-house (no licence) | Optional: FreePD (public domain) — note spurious Content ID claims are possible |
| Narration | Kokoro-82M weights, Apache-2.0 | Commercial use permitted |
| Fonts | Inter (SIL OFL) | Free for commercial use |

## Netherlands / EU (general information — **not legal or tax advice**)
- **KvK registration** and **tax status** are separate questions. Whether ad income is "winst uit onderneming" or
  "resultaat uit overige werkzaamheden" depends on scale, continuity and intent (Belastingdienst decides; use the
  Belastingdienst OndernemersCheck / KvK Adviesteam). Source: kvk.nl, rabobank.nl, knab.nl.
- **VAT (btw):** Google Ireland pays you; services are typically reverse-charged; secondary sources say you still report
  the turnover. If registered, the KOR (small-business exemption, turnover ≤ €20k/yr) may apply. Verify with an adviser.
- **US withholding:** submit tax info (W-8BEN) in AdSense; otherwise up to 30% withholding on US-viewer revenue. A
  community table lists the NL–US treaty royalty rate at 0% (unverified — check IRS Publication 901).
- **Mediawet / Commissariaat voor de Media:** rules for "video uploaders" (advertising disclosure, protection of minors)
  apply to monetized creators registered with KvK; the former 500k-follower threshold has reportedly been dropped (NOS).
  Practical implication: label any sponsorship clearly ("reclame"/"paid promotion" flag), which we do anyway.
- **GDPR:** the pipeline stores no viewer personal data beyond aggregated YouTube Analytics.
- **Recommendation:** once revenue approaches ~€1,000/yr, a one-off session with a Dutch tax adviser (≈ €100–200) is worth it.
