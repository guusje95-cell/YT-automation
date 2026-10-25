"""YouTube publishing via the official Data API v3 (OAuth 2.0).

Safety rules enforced in code:
  - refuses to upload when QA has any FAIL or QA has not run
  - default privacy is `private`; `public` additionally needs env YTAUTO_ALLOW_PUBLIC=1
    (the owner's explicit authorisation); scheduled publishing uses status.publishAt on a private video
  - dry-run writes the exact request to output/<id>/publish_request.json and calls nothing

One-time setup (owner): see docs/SETUP.md -> `python -m ytauto.publish.youtube authorize`
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ytauto.core import config
from ytauto.core.log import get_logger

log = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",       # captions, playlists, thumbnails
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
SECRETS_DIR = config.CONFIG_DIR / "secrets"
CLIENT_SECRETS = Path(os.environ.get("YT_CLIENT_SECRETS", SECRETS_DIR / "client_secret.json"))
TOKEN = Path(os.environ.get("YT_TOKEN_FILE", SECRETS_DIR / "youtube.token.json"))


class PublishBlocked(RuntimeError):
    pass


def credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not TOKEN.exists():
        raise PublishBlocked(f"No OAuth token at {TOKEN}. Run: python -m ytauto.publish.youtube authorize")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    return creds


def authorize() -> None:
    """Interactive one-time consent. Run on a machine with a browser."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not CLIENT_SECRETS.exists():
        raise SystemExit(f"Put the OAuth client JSON (Desktop app) at {CLIENT_SECRETS} first (docs/SETUP.md).")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json())
    os.chmod(TOKEN, 0o600)
    print(f"Saved token to {TOKEN}")


def _service(name="youtube", version="v3"):
    from googleapiclient.discovery import build
    return build(name, version, credentials=credentials(), cache_discovery=False)


def build_request(spec, privacy: str | None = None, publish_at: str | None = None) -> dict:
    meta = json.loads((spec.out / "metadata.json").read_text())
    privacy = privacy or meta["privacy_status"]
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": meta["made_for_kids"],
              "containsSyntheticMedia": bool(meta["contains_synthetic_media"]), "embeddable": True,
              "license": "youtube"}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    return {
        "body": {
            "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": meta["category_id"], "defaultLanguage": meta["default_language"],
                        "defaultAudioLanguage": meta["default_language"]},
            "status": status,
        },
        "files": meta["files"],
        "playlist_id": config.get("channel.default_playlist") or None,
    }


def _gate(spec, req: dict) -> None:
    qa_p = spec.out / "qa.json"
    if not qa_p.exists():
        raise PublishBlocked("QA has not run for this video (python -m ytauto qa <id>)")
    qa = json.loads(qa_p.read_text())
    if qa["summary"].get("FAIL"):
        raise PublishBlocked(f"QA has {qa['summary']['FAIL']} FAIL item(s); see {spec.out / 'qa_report.md'}")
    st = req["body"]["status"]
    if st["privacyStatus"] == "public" and os.environ.get("YTAUTO_ALLOW_PUBLIC") != "1":
        raise PublishBlocked("Public publishing requires the owner's authorisation: set YTAUTO_ALLOW_PUBLIC=1")
    for k, f in req["files"].items():
        if not Path(f).exists():
            raise PublishBlocked(f"missing {k} file {f}")


def publish(spec, dry_run: bool = True, privacy: str | None = None, publish_at: str | None = None) -> dict:
    req = build_request(spec, privacy, publish_at)
    (spec.out / "publish_request.json").write_text(json.dumps(req, indent=1, ensure_ascii=False))
    _gate(spec, req)
    if dry_run:
        log.info("dry run: request written, nothing uploaded")
        return {"dry_run": True, "request": str(spec.out / "publish_request.json"),
                "privacy": req["body"]["status"]["privacyStatus"]}
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    yt = _service()
    media = MediaFileUpload(req["files"]["video"], chunksize=16 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    insert = yt.videos().insert(part="snippet,status", body=req["body"], media_body=media)
    response, attempt = None, 0
    while response is None:
        try:
            status, response = insert.next_chunk()
            if status:
                log.info("upload %.0f%%", status.progress() * 100)
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and attempt < 6:
                attempt += 1
                time.sleep(2 ** attempt)
                continue
            raise
    vid = response["id"]
    log.info("uploaded video id %s", vid)
    result = {"video_id": vid, "url": f"https://youtu.be/{vid}", "privacy": req["body"]["status"]["privacyStatus"],
              "publish_at": publish_at, "steps": {}}
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(req["files"]["thumbnail"],
                                                                    mimetype="image/jpeg")).execute()
        result["steps"]["thumbnail"] = "ok"
    except HttpError as e:  # custom thumbnails need a verified channel
        result["steps"]["thumbnail"] = f"failed: {e}"
    try:
        yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "en", "name": "English",
                                                               "isDraft": False}},
                             media_body=MediaFileUpload(req["files"]["captions"], mimetype="application/octet-stream")
                             ).execute()
        result["steps"]["captions"] = "ok"
    except HttpError as e:
        result["steps"]["captions"] = f"failed: {e}"
    if req["playlist_id"]:
        try:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": req["playlist_id"], "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            result["steps"]["playlist"] = "ok"
        except HttpError as e:
            result["steps"]["playlist"] = f"failed: {e}"
    (spec.out / "publish_result.json").write_text(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "authorize":
        authorize()
    else:
        print(__doc__)
