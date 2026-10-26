# Project status — YouTube automation business

_Last updated: 2026-10-26 (session 2: quality overhaul). Labels: **Fact** = observed/tested; **Est** = estimate; **Assumption**._

## Where we are
Stages A–E done; Stage F (validation with real uploads) is **blocked on your one-time setup** (`docs/SETUP.md`, ~45 min).

| Stage | Status |
|---|---|
| A Research | ✅ 23 niches + 4 deep dives scanned with real YouTube data; policy, licensing, NL/EU, economics |
| B Decision | ✅ Space & astronomy explainers ("real images, real numbers"); backup: business case studies |
| C Architecture | ✅ `docs/ARCHITECTURE.md` |
| D Implementation | ✅ `automation/ytauto` — 16 modules, CLI, 23 unit tests passing |
| E Pilot + batch | ✅ 3 finished episodes (below) |
| F Validation | ⛔ needs channel + OAuth (you) |
| G Optimisation / H Scaling | not started (needs real performance data) |

## Finished episodes (all private-by-default, not uploaded)
| Episode | Length | QA | Compute | Files |
|---|---|---|---|---|
| What NASA's Juno Found Inside Jupiter (pilot) | 9:02 | 0 FAIL · 1 WARN (time-sensitive mission status, intentional) · 28 PASS | 16.9 min | `output/juno-jupiter/` |
| What's Actually Inside the Sun | 7:19 | 0 FAIL · 0 WARN · 29 PASS | 20.6 min | `output/inside-the-sun/` |
| The First Photos of Black Holes, Explained | 6:04 | 0 FAIL · 0 WARN · 29 PASS | 11.1 min (narration pre-cached) | `output/black-hole-photos/` |

Each folder: 1080p master `<id>.mp4` (git-ignored, regenerate with `python -m ytauto produce <id>`), `*_preview480.mp4`
(committed), `.en.srt/.vtt`, `thumbnail_1-3.jpg`, `metadata.json`, `description.txt`, `script.md` (script with
claims→sources), `qa_report.md`, `licensing_checklist.md`, `storyboard.jpg`, `production_log.json`.

## Session 2 — quality overhaul (after feedback: "boring voice, bad images, no storyline")
New flagship episode **Falling Into Jupiter** (`content/falling-into-jupiter/`), built with a new cinematic layer:
| Problem | What changed | Evidence |
|---|---|---|
| No storyline | Journey structure: the Galileo probe's 58-minute plunge (cold open → entry → clouds → signal lost), then Juno data down to the core; callbacks (radiation belt → dynamo; 58 minutes → ending) | `content/falling-into-jupiter/script.md`, 11 sources, every number in a sourced claim |
| Static, flat images | Ray-traced 3D renderer (`visuals/render3d.py`) with NASA-derived textures + JunoCam detail; 11 shot presets (orbit, entry with plasma, cloud dive through real JunoCam imagery, cutaways, interior fluid, polar orbit, collision); parallel pre-render cache | `visuals/shots.py`, `video/prerender.py` |
| Bland editing | Telemetry HUD with live counters, chapter cards, glitch "SIGNAL LOST", atmosphere profile, fact list, cinematic titles/end card | `visuals/editorial.py` |
| Flat sound | Licensed score per scene (ESO Music Archive, zero-project, CC BY 4.0, credited) with ducking and a hard cut to silence at "signal lost"; procedural SFX (roar, wind, thunder synced to on-screen lightning, static, flat-line) | `audio/music.py`, `audio/sfx.py` |
| Boring voice | Expressive local Chatterbox voice (MIT) cloned from a *synthetic* reference (no real person); automatic retry of clips that repeat words | `voice/tts.py`, `voice/narrate.py` |

**Honest limits (Fact):** the voice is still synthetic; I can measure intelligibility (Whisper) and pacing but cannot judge
timbre by ear. Best paid upgrade: ElevenLabs Creator (~$22/month) — **not purchased, needs your approval**.
Compute: ~1.5 h narration + ~1 h 3D render on 4 CPU cores for a 7-minute episode (cached afterwards).

## Tests performed and results (facts)
- Niche scanner: 2 live scans, ~1,000 videos and ~400 channel pages parsed, 0 errors.
- Licence gate: caught 7 non-commercial or unlicensed images in the pilot that a naïve NASA search would have used
  (e.g. PIA21775 is CC BY-NC-SA); replaced with CC BY / NASA-produced images.
- Audio: all three mixes measured at −14.0 LUFS integrated, true peak −1.2 dBFS (ffmpeg EBU R128).
- Speech intelligibility (Whisper round-trip): 2.1% (Juno), 3.8% (Sun) and 1.4% (black holes) word error rate, almost entirely
  spelling/number formatting; two suspected mispronunciations were checked with a larger model and were ASR errors.
- Video: H.264 1080p30 yuv420p, A/V lengths within 0.1 s, no black segments > 1 s, no silences > 2.5 s.
- Publish gate: unit-tested (blocks public without authorisation, blocks on QA FAIL). **Actual upload untested** — needs your OAuth.
- Analytics report: tested on clearly-labelled mock data only.
- LLM drafting: request building, YAML extraction, asset resolution tested offline; **no live API call** (no key).

## Decisions and evidence
| Decision | Evidence | Where |
|---|---|---|
| Niche: space explainers | Score 8.15 (robust to weight changes); 18 small-channel breakouts; NullSpace 7 videos → 1.18M median; free licensed imagery (NASA PD, ESA/ESO CC BY) | `strategy/decision_report.md` |
| Plan for 8,000 watch hours | Official page confirms Feb-2027 YPP update; 8,000 h figure from several secondary sources | `research/policy_research.md` |
| Long-form 7–12 min, ~2/week, Shorts later | Watch-hours rule; quality-over-volume pattern in space niche | decision report |
| Local Kokoro voice (free) | Apache-2.0, ~2.5× real-time on 4 CPU cores, low WER | `automation/ytauto/voice/` |
| Generated music bed | Zero licence / Content ID risk | `automation/ytauto/audio/music.py` |
| Default model for drafting: Claude Opus 5.5 | Quality of factual scripts matters most; ~€0.30–0.60/script **(Est)** | `config/settings.yaml` |

## Actual costs so far
**€0.** No subscriptions, no purchases, no API spend. (This session's compute is not billed to the project.)

## Blockers / what I need from you
1. **Create the channel and pick the name** (recommended: Parsec Notes — handle was free on 2026-10-25). 
2. **Google Cloud OAuth client** + run `python -m ytauto.publish.youtube authorize` once (`docs/SETUP.md` §2–3).
3. **Review the three episodes** (480p previews, `script.md`, `qa_report.md`) and say "upload" — I'll keep uploads private
   until you approve publishing.
4. Optional: an Anthropic API key with a spend cap (~$10/month) for unattended script drafting.

## Known limitations / honest caveats
- Episodes run 6–9 min, shorter than the 10–12 min target; future scripts should aim for 1,400–1,700 words with more sources.
- Visual variety per topic is limited by available licensed imagery; some images repeat with different framing.
- Kokoro voice is good but not top-tier; a paid voice A/B test is planned once there is retention data.
- No impressions/CTR via API; requires a weekly Studio CSV export (2 min).
- RPM for space content is unmeasured (assumption $2.50–$8.00).
- Public-page research parsing can break if YouTube changes its HTML; the Data API path (free key) is the fallback.

## Next highest-priority actions
1. You: setup steps above → I upload pilot privately → you review in Studio.
2. Publish cadence: 2 episodes/week for 6 weeks (12 videos), Test & Compare thumbnails on each.
3. Next topics from data: black holes "that shouldn't exist" (9.2× outlier at Bluntly Explained), Saturn's rings,
   Webb's earliest galaxies (needs ESA/Webb `url` assets), Great Red Spot shrinking (sequel to the pilot).
4. Add Shorts: auto-cut a 45 s vertical clip from each episode's strongest section.
5. Week-6 checkpoint: go / adjust / switch on the validation targets (median ≥1,000 views, AVP ≥35%, CTR ≥4%).
