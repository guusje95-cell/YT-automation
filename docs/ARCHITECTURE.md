# Architecture

```
research (topics, competitors)  ──►  content/<id>/research.md  ──►  draft (LLM, optional)
                                                                       │
                                            content/<id>/spec.yaml  ◄──┘   ← single source of truth per video
                                                       │
   assets ─► narration ─► audio mix ─► captions ─► thumbnails ─► storyboard ─► render ─► mux ─► metadata ─► QA
     │           │            │            │            │                         │                     │
 licence gate  per-sentence  −14 LUFS    SRT/VTT     3 variants              1080p30 H.264     qa_report.md (gate)
 + provenance  TTS + timings  ducked bed  from timings                                                  │
                                                                                                publish (OAuth, private)
                                                                                                         │
                                                                                     analytics → weekly report → next topics
```

## Design choices
- **Spec-driven.** Each episode is one YAML file (`docs/VIDEO_SPEC.md`): sources, licensed assets, scenes with narration,
  claim→source links and visual beats. Every stage is a pure function of the spec plus cached outputs in
  `content/<id>/build/`, so any stage can be re-run alone and editing one sentence re-synthesises only that sentence.
- **Replaceable providers.** TTS (`voice/tts.py`: Kokoro local, ElevenLabs optional), assets (`assets/fetch.py`:
  NASA Images, NASA SVS, Openverse, direct URL with stated licence, local), LLM (`scripting/draft.py`), research backend
  (public pages or Data API). Adding a provider = one class/function + a config value.
- **No paid editor.** The compositor (`visuals/frames.py`) renders frames with OpenCV/PIL (sub-pixel Ken Burns, text
  layers, data diagrams) and pipes raw frames to ffmpeg.
- **Safety in code, not in docs.** Licence gate blocks NC/ND/unknown-licence assets; QA FAIL blocks publishing;
  public uploads need an explicit environment flag; default privacy is private.
- **Honest QA.** Script lint (banned phrases, sourced numbers, time-sensitive claims), licence audit, ffprobe format
  checks, black-frame and silence detection, EBU R128 loudness, and a speech-recognition round trip to catch
  mispronunciations.

## Module map (`automation/ytauto/`)
| Module | Role | Tested |
|---|---|---|
| `research/youtube_public.py` | public search/channel page parser (rate-limited) | unit + live scans |
| `research/niche_scan.py` | niche opportunity metrics | live (2 scans, 27 niches) |
| `research/monitor.py` | competitor outliers, topic scoring | live |
| `scripting/draft.py` | LLM drafting with validation/repair + asset query resolution | offline only (no API key) |
| `assets/fetch.py` | asset providers, licence gate, provenance manifest | unit + live (43 assets) |
| `voice/tts.py`, `voice/narrate.py` | TTS providers, sentence timing | live (Kokoro) |
| `audio/music.py`, `audio/mix.py` | generated music bed, ducking, loudness, limiter | live, measured |
| `visuals/frames.py` | beat renderers and overlays | live renders |
| `video/timeline.py`, `video/assemble.py` | beat timing, render, mux, storyboard | unit + live |
| `captions.py`, `thumbnail.py`, `metadata.py` | packaging, licensing checklist | unit + live |
| `qa.py` | automated QA report | live |
| `publish/youtube.py` | OAuth upload, thumbnail, captions, playlist, schedule | gate unit-tested; upload **untested** (needs your OAuth) |
| `analytics/report.py` | Analytics API collection, baseline report | mock data only |
| `strategy/economics.py` | scenario model | run |
| `cli.py` | `python -m ytauto <command>` | used for all productions |

## Failure handling
- Network calls: retry with exponential backoff + jitter (`core/retry.py`).
- Asset problems fail loudly at the assets stage with the reason (e.g. "restrictive licence marker 'CC BY-NC'").
- Too-short video clips: start offset is clamped and a warning logged.
- Every production run appends stage timings/status to `output/<id>/production_log.json`; logs in `logs/ytauto.log`.
