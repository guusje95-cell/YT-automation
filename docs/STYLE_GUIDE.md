# Editorial style guide — Parsec Notes (working name)

## Promise
Real images. Real numbers. One clear question per video, answered properly.

## Voice
- Calm, precise, curious. A good teacher, not a hype channel.
- British spelling (narrator is a British English voice).
- Short sentences written for the ear. One idea per sentence. Read aloud test: no sentence over ~30 words.
- Concrete comparisons over adjectives ("wider than Earth", not "unimaginably huge").
- Avoid: "delve", "tapestry", "buckle up", "mind-blowing", "scientists are terrified/baffled", "in this video we will".
  The banned list lives in `config/banned_phrases.txt` and is enforced by QA.

## Structure (10–16 min)
1. **Hook (≤40 s):** the question, why it's surprising, what the viewer will know by the end.
2. **Context (≤90 s):** only what's needed to follow the rest.
3. **4–6 numbered sections**, each with one discovery/idea, its evidence, and why it matters.
   Vary section openers; re-show the numbered list card between sections.
4. **Outro (≤45 s):** tie the sections to the opening question; one plain subscribe line; no begging.

## Accuracy rules
- Every number on screen or in narration maps to a claim with a cited source (QA checks this).
- Hypotheses are labelled as hypotheses ("one idea is…", "a proposed model").
- Time-sensitive statements (mission status, records, "currently") need a dated source or are cut;
  list them under `time_sensitive` in the spec.
- Prefer primary sources: NASA/ESA/JPL releases, peer-reviewed papers, mission pages.
- Round numbers in narration ("about 1,000 km") but keep exact values in claims.

## Visual rules
- Real mission imagery first (NASA, ESA/Webb, ESA/Hubble, ESO); artist's concepts must be labelled as such.
- Never label an image as something it isn't (check what the image actually shows).
- Labels state facts about the image: object, instrument, date.
- No non-commercial (NC/ND) licences. Citizen-processed JunoCam images only with an explicit CC BY/CC0 statement.
- Credits on screen (bottom right) and in the description.

## Packaging
- Titles ≤70 characters, accurate; the video must deliver what the title promises in the first minute.
- Thumbnails: one real object, ≤4 words, high contrast, no fake arrows/faces/shock imagery.
- Three title options and three thumbnail variants per video for Test & Compare.
