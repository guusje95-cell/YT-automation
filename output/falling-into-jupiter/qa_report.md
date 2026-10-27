# QA report — falling-into-jupiter

**0 FAIL · 1 WARN · 28 PASS**  (publishable after human review of WARN items)

| Check | Status | Detail |
|---|---|---|
| voice.intelligibility | WARN | ASR word error rate 8.1% (lower is better; includes number formatting differences). Top diffs: 'fifty eight' -> '58'; 'ten' -> '10'; 'noor' -> 'nor'; 'a hundred and seventy thousand kilometres' -> '170000 kilometers'; 'braking' -> 'breaking'; 'two hundred and twenty eight' -> '228'; 'forty six' -> '46'; 'braking' -> 'breaking' |
| script.banned_phrases | PASS | none |
| script.hype_words | PASS | none |
| script.length | PASS | 976 words, 120 sentences |
| script.longest_sentence | PASS | 24 words: A heat shield designed to burn away as it fell, and braking so violent it felt two hundred... |
| script.repetitive_openers | PASS | none |
| script.numbers_sourced | PASS | every number appears in a sourced claim |
| script.sources_used | PASS | 16 sources cited |
| script.time_sensitive | PASS | none declared |
| assets.licences | PASS | 15 assets, all allowed |
| assets.credits | PASS | all credited |
| assets.flags | PASS | no open flags |
| assets.unused | PASS | unused (fine): ['galileo_orbiter', 'grs_closeup', 'grs_slices', 'probe_painting2', 'white_oval'] |
| captions.line_length | PASS | 0 lines > 42 chars |
| meta.title_length | PASS | 44 chars: Falling Into Jupiter (Based on a True Story) |
| meta.description_length | PASS | 4706 chars |
| meta.tags | PASS | 10 tags, 134 chars |
| meta.chapters | PASS | 7 chapters |
| meta.privacy_default | PASS | private |
| thumbnail.thumbnail_1 | PASS | (1280, 720), 108 KB |
| thumbnail.thumbnail_2 | PASS | (1280, 720), 129 KB |
| thumbnail.thumbnail_3 | PASS | (1280, 720), 153 KB |
| video.format | PASS | h264 1920x1080 yuv420p 30/1 |
| video.audio_stream | PASS | aac 48000 Hz 2 ch |
| video.duration | PASS | 441.4s (7.4 min) |
| video.av_sync_length | PASS | video 441.27s / audio 441.35s |
| video.black_frames | PASS | none longer than 1.0s |
| audio.loudness | PASS | -14.4 LUFS integrated, true peak -1.9 dBFS |
| audio.long_silences | PASS | none |
