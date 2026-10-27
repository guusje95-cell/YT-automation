# What works — research notes (2026-10-27)

Goal: find what makes successful space/story videos grip viewers, and what open-source tooling can get us there.
**Fact** = verified from a source or measured by us; **Practitioner claim** = advice without published data.

## 1. Evidence from channels that win in this niche
- **Topic scan (Fact, our own data, `research/topic_scan_2026-10-26.md`)**: "biggest black hole / TON 618" has the
  most small-channel breakouts (15 videos ≥100k views from channels <100k subs). Winning packaging: extreme scale +
  fear + visual journey ("Why TON 618 is The Scariest Black Hole", 1.5M on an 8.6k-sub channel; "What TON 618 Would
  Look Like at Different Distances", 8.6M; NullSpace "The Black Hole That Breaks the Universe | 4K", 2.4M).
- **MrBeast production memo (leaked 2024; authenticity reported by former producers, not officially confirmed)**:
  the first minute decides most drop-off; the opening must prove the thumbnail's promise; plan "re-engagement"
  moments at roughly minutes 3 and 6; aim for an early "wow" spectacle (their example lands at ~30 s); track CTR,
  average view duration and average view percentage. Sources: creatorhandbook.net, alexanderjarvis.com (memo text).
- **Mario Joos (ex-MrBeast retention strategist, via Vidpros interview)**: hook → progressive new information →
  satisfying payoff; structure tells viewers where they are; strong story beats attention-span myths.
- **Cut pace is not the answer by itself (Practitioner/press)**: MrBeast's own cuts per minute fell from 38 (Mar 2023) to
  23 (Mar 2024) per AIR Media-Tech; slow, contemplative space docs (Fall of Civilizations / Cosmos style) are an
  explicit, separate genre. Contrast (fast vs. still) matters more than speed.
- **First-minute drop**: vidIQ figure cited by several guides: often 55%+ leave in the first 60 s (Practitioner).

## 2. Story-craft takeaways (applied)
| Principle | How we apply it |
|---|---|
| Hook = a true, hard-to-believe fact + an unanswered question | "In 1957 … number 618 … the heaviest black hole ever weighed … nothing should grow that big that early." |
| Open loops paid off later | Jupiter: dry air → desert hot spot; stolen neon → helium rain. TON 618: "too big too early" → born-big black hole (UHZ1). |
| Re-hooks between chapters | Every chapter ends on a forward question ("Mara has survived the easy part."). |
| Emotional stakes via a character | Mara/Noor, Jonah/Iris — fictional, disclosed smoothly at the end, facts stay real. |
| Myth-busting moments | "You get torn apart" → not at TON 618's size. |
| Honest framing | "Based on a true story" refers to the real event; dramatization disclosed at the end and in the description. |

## 3. Tooling found and adopted
- **Chatterbox Turbo (Resemble AI, MIT)** — Fact, tested here on CPU: ~3.6× real time (≈4–5× faster than the
  standard model) and it reads inline tags. Tags present in the model tokenizer: `[gasp] [sigh] [sniff] [cough]
  [laugh] [chuckle] [groan] [shush] [clear throat] [crying] [whispering] [fear] [angry] [happy] [surprised]
  [sarcastic] [dramatic] [narration] [advertisement]`. Measured: `[dramatic]` widened the narrator's pitch range from
  10.6 to 15.7 semitones and slowed delivery to ~106 wpm; `[fear]` raised Mara's pitch and range.
  Note: Turbo audio carries Resemble's PerTh watermark (inaudible; identifies AI audio — consistent with our disclosure).
- **Word-level captions (faster-whisper word timestamps + ASS/Pillow)** — common in faceless short-form tools
  (MoneyPrinterTurbo, ai-video-captions, captify). Not adopted for long-form yet: top space documentaries don't burn
  captions; we show a typed transcript only for radio lines. Candidate A/B test once we have retention data.
- **MoneyPrinterTurbo (MIT, ~50–100k stars)** — short-form only; no narrative/chapter layer. Nothing to adopt beyond
  the caption idea.
- **NASA SVS "Plunge" visualizations (Schnittman & Powell 2024)** — public NASA media, used in TON 618.
- **Fish Speech S2** — tag-controllable TTS reported as strong; licence/CPU feasibility not yet checked.

## 4. Sound design
Practitioner consensus: risers into reveals, impacts on reveals, whooshes on cuts, silence before big moments.
Implemented procedurally (`audio/sfx.py`): riser → impact on every fact card, deep hit on chapter starts, soft
whoosh on cuts, heartbeat under tension, music cut to silence at "signal lost".

## 5. What we still can't know without uploading
No controlled public data exists on shot length or captions vs. watch time. The decisive evidence will be our own
retention curves (first-minute drop, dips, re-watch spikes) once the channel is live.
