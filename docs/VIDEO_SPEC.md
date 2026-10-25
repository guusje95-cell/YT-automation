# Video spec reference (`content/<id>/spec.yaml`)

See `content/juno-jupiter/spec.yaml` for a complete example.

| Key | Meaning |
|---|---|
| `id` | folder name and output name |
| `title_options` | 3 titles; the first is uploaded, others for later tests |
| `description_summary` | first paragraph of the description |
| `thumbnail.variants` | list of `{text, asset, focus: [x, y], zoom, side: left|right}` |
| `voice` | `{provider, voice, lang, speed}` overrides `config/settings.yaml` |
| `music` | `{mood: calm|wonder|tension, seed, gain_db, enabled}` |
| `lexicon` | spoken-form replacements, e.g. `"Io": "Eye-oh"` |
| `time_sensitive` | statements that need a human check before publishing (shown as QA WARN) |
| `sources` | `{id, title, publisher, url, accessed}` |
| `assets` | see providers below |
| `scenes` | `{id, chapter, narration, claims: [{text, sources: [ids]}], beats: [...]}` |

## Asset providers
```yaml
- {id: x, provider: nasa_images, nasa_id: PIA21032}
- {id: x, provider: nasa_svs, svs_id: 13007, kind: video, file_hint: "1080", credit: "..."}
- {id: x, provider: openverse, openverse_id: <uuid>}
- {id: x, provider: url, url: ..., license: cc-by, credit: "ESA/Webb, NASA & CSA, ...", source_page: ...}
- {id: x, provider: local, path: assets/my_chart.png, license: generated}
```
Add `license_override: "<reason and date>"` only after a manual licence check.

## Beat types
| type | fields |
|---|---|
| `image` | `asset`, `motion: in|out|pan_left|pan_right|up|down`, `focus`, `zoom`, `fit: auto|cover|contain`, `label` |
| `video` | `asset`, `from` (seconds into the clip), `speed`, `zoom`, `label` |
| `fact` | `big`, `small`, `source` (id) or `source_label` |
| `title` | `text`, `kicker` |
| `list` | `title`, `items`, `highlight` (index) |
| `scale` | `mode: circles` with `items: [{label, value, color, note}]` (true relative sizes) · `mode: layers` with `labels`, `bounds` (outer radius fractions), `highlight` · `mode: core` |
| `end` | `text` |

Every beat may set `sentences: n` — its share of the scene's narration time; cuts snap to sentence pauses.
