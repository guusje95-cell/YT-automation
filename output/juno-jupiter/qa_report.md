# QA report — juno-jupiter

**0 FAIL · 1 WARN · 28 PASS**  (publishable after human review of WARN items)

| Check | Status | Detail |
|---|---|---|
| script.time_sensitive | WARN | Juno's mission status after September 2025 is not confirmed by NASA as of 2026-10-25; script avoids claiming it is still operating. |
| script.banned_phrases | PASS | none |
| script.hype_words | PASS | none |
| script.length | PASS | 1255 words, 86 sentences |
| script.longest_sentence | PASS | 37 words: One idea, published in Nature in 2019, is a head-on collision early in Jupiter's history, ... |
| script.repetitive_openers | PASS | none |
| script.numbers_sourced | PASS | every number appears in a sourced claim |
| script.sources_used | PASS | 11 sources cited |
| assets.licences | PASS | 29 assets, all allowed |
| assets.credits | PASS | all credited |
| assets.flags | PASS | no open flags |
| assets.unused | PASS | all used |
| captions.line_length | PASS | 0 lines > 42 chars |
| meta.title_length | PASS | 37 chars: What NASA's Juno Found Inside Jupiter |
| meta.description_length | PASS | 4896 chars |
| meta.tags | PASS | 9 tags, 88 chars |
| meta.chapters | PASS | 9 chapters |
| meta.privacy_default | PASS | private |
| thumbnail.thumbnail_1 | PASS | (1280, 720), 192 KB |
| thumbnail.thumbnail_2 | PASS | (1280, 720), 113 KB |
| thumbnail.thumbnail_3 | PASS | (1280, 720), 242 KB |
| video.format | PASS | h264 1920x1080 yuv420p 30/1 |
| video.audio_stream | PASS | aac 48000 Hz 2 ch |
| video.duration | PASS | 542.0s (9.0 min) |
| video.av_sync_length | PASS | video 541.93s / audio 541.99s |
| video.black_frames | PASS | none longer than 1.0s |
| audio.loudness | PASS | -14.0 LUFS integrated, true peak -1.2 dBFS |
| audio.long_silences | PASS | none |
| voice.intelligibility | PASS | ASR word error rate 2.1% (lower is better; includes number formatting differences). Top diffs: 'nasa's' -> 'nasa'; 'fifth' -> '5th'; 'fourth' -> '4th'; 'four percent' -> '4'; 'nine' -> '9'; 'watched' -> 'watch'; 'nasa's' -> 'nasa'; 'weather' -> 'where they're' |
