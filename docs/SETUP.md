# Setup — the minimum you need to do

Everything else is automated. These are the steps only you can do (accounts, consent, money).
Estimated time: **~45 minutes once**, then ~15–30 min/week.

## 0. Run the pipeline on your machine (or a small server)
Requirements: Python 3.11+, ffmpeg, ~6 GB disk, 4+ CPU cores, 16 GB RAM. On 4 CPU cores a 9-minute cinematic
episode takes roughly 1.5 h of narration (Chatterbox on CPU) plus ~1 h of 3D pre-rendering; both are cached, so later
edits only redo what changed.
```bash
git clone https://github.com/guusje95-cell/YT-automation && cd YT-automation
pip install -r automation/requirements.txt
./scripts/fetch_models.sh                 # local voice model (~350 MB, free, Apache-2.0)
# expressive narrator voice (Chatterbox, MIT licence) in its own virtualenv — it pins its own torch version
python3 -m venv /root/venvs/cbx && /root/venvs/cbx/bin/pip install chatterbox-tts==0.1.7 \
    torch==2.6.0 torchaudio==2.6.0 --extra-index-url https://download.pytorch.org/whl/cpu
#   (another venv location? set `python:` in the spec's voice block)
cd automation && python -m pytest -q tests # all tests should pass
python -m ytauto produce juno-jupiter      # rebuilds the pilot end-to-end into output/juno-jupiter/
```

## 1. Create the channel (5 min)
1. Pick the name (recommended **Parsec Notes**; alternatives in `strategy/decision_report.md`). Claim the handle immediately.
2. Create a **Brand Account** channel (lets you add a manager later without sharing your Google password).
3. Turn on **2-Step Verification** on the Google account (required for the Partner Program).
4. Verify the channel by phone (YouTube Studio → Settings → Channel → Feature eligibility) — needed for custom thumbnails and videos over 15 minutes.
5. Set `channel.name` in `config/settings.yaml` if you chose a different name.

## 2. Google Cloud project for the YouTube API (15 min, free)
1. https://console.cloud.google.com → New project (e.g. `parsec-notes`).
2. APIs & Services → Library → enable **YouTube Data API v3** and **YouTube Analytics API**.
3. OAuth consent screen → External → add your own Google account as a **test user**.
4. Credentials → Create credentials → **OAuth client ID** → type **Desktop app** → download the JSON.
5. Save it as `config/secrets/client_secret.json` (this folder is git-ignored; never commit it).
6. Optional for research: Credentials → API key → put it in `.env` as `YT_API_KEY=...` (read-only, 10,000 units/day).

## 3. One-time authorisation (2 min)
```bash
cd automation && python -m ytauto.publish.youtube authorize
```
A browser opens; sign in with the channel's account and approve. A token is stored in
`config/secrets/youtube.token.json` (git-ignored, file mode 600).

## 4. First upload — private, for your review (5 min)
```bash
python -m ytauto publish juno-jupiter --dry-run   # shows exactly what will be sent
python -m ytauto publish juno-jupiter             # uploads as PRIVATE (default) with thumbnail + captions
```
Watch it in YouTube Studio. If it's good, either click Publish in Studio, or schedule it:
```bash
python -m ytauto publish inside-the-sun --publish-at 2026-11-03T16:00:00Z   # private until then
```
Public uploads from the command line are blocked unless you set `YTAUTO_ALLOW_PUBLIC=1` — deliberately, so nothing
goes public without your say-so.

In Studio, for each video: **Monetisation** (once eligible) and **Test & Compare** with `thumbnail_2.jpg`/`thumbnail_3.jpg`.

## 5. Optional: unattended script drafting (~€0.30–0.60 per script)
Create an Anthropic API key (console.anthropic.com), set a monthly spend limit (e.g. $10), then put
`ANTHROPIC_API_KEY=...` in `.env`. Then: write `content/<id>/research.md` (topic, sources) and run
`python -c "from ytauto.scripting.draft import draft; draft('<id>')"` followed by `python -m ytauto produce <id>`.
Without a key, scripts are written in-session (as done for the first episodes).

## 6. Weekly routine (15–30 min)
1. `python -m ytauto analytics` → read `analytics/weekly_report_<date>.md`.
2. Export Studio → Analytics → Advanced mode → Content table (impressions + CTR) as CSV into `analytics/imports/`
   (the API does not expose impressions/CTR).
3. Review the next two drafted videos: open `output/<id>/storyboard.jpg`, `qa_report.md`, skim the 480p preview.
4. Approve → schedule upload.

## Money and legal (see `research/policy_research.md`)
- Nothing in this project spends money without you adding a key or approving a purchase.
- Before monetisation: AdSense account, W-8BEN tax info in AdSense, and a check with the Belastingdienst
  OndernemersCheck / KvK about registration. A one-off tax adviser session is worth it once revenue starts.
