# YT-automation — Parsec Notes (working name)

An automated, quality-gated production system for a faceless YouTube channel of **space explainers built from real
mission imagery and sourced numbers**.

- **Why space?** See `strategy/decision_report.md` (23 niches scanned with real YouTube data; space scored 8.15/10 and
  showed the most small-channel breakouts).
- **Status, decisions, costs, next steps:** `PROJECT_STATUS.md`
- **Your setup steps (~45 min once):** `docs/SETUP.md`
- **How it works:** `docs/ARCHITECTURE.md`, `docs/VIDEO_SPEC.md`, `docs/STYLE_GUIDE.md`

```bash
pip install -r automation/requirements.txt && ./scripts/fetch_models.sh
cd automation
python -m ytauto produce juno-jupiter      # spec -> finished video, captions, thumbnails, metadata, QA report
python -m ytauto monitor                   # competitor outlier report
python -m ytauto publish juno-jupiter --dry-run
```

| Folder | Contents |
|---|---|
| `research/` | niche scans (raw data + metrics), market report, policy research, competitor outliers |
| `strategy/` | decision report, financial model |
| `automation/` | the `ytauto` Python package + tests |
| `content/<id>/` | episode specs (source of truth); `build/` is regenerable |
| `output/<id>/` | deliverables: video (1080p master is git-ignored; 480p preview committed), captions, thumbnails, metadata, QA, licensing |
| `analytics/` | weekly reports, Studio CSV imports |
| `config/` | non-secret settings; `config/secrets/` is git-ignored |
| `docs/` | setup, architecture, spec reference, style guide |
