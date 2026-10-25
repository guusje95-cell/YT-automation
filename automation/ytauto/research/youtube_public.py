"""Read-only access to public YouTube search and channel pages.

Parses the `ytInitialData` JSON embedded in public HTML pages. Used for
market research and competitor monitoring when no YouTube Data API key is
configured. It does not download videos, bypass sign-in/bot checks, or touch
watch pages. Keep request volume low (a few hundred pages per run at most).

When YT_API_KEY is set, prefer `youtube_api.py` (official, quota-based).
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field, asdict

import requests

from ytauto.core.log import get_logger
from ytauto.core.retry import retry

log = get_logger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_COOKIES = {"CONSENT": "YES+1"}

# Search filter tokens (the `sp` URL parameter).
SP_VIDEO = "EgIQAQ%3D%3D"            # type: video
SP_VIDEO_THIS_YEAR = "EgQIBRAB"      # upload date: this year, type: video
SP_VIDEO_THIS_MONTH = "EgQIBBAB"     # upload date: this month, type: video

_MIN_INTERVAL = 0.8
_last_request = 0.0


@dataclass
class Video:
    video_id: str
    title: str
    views: int | None
    age_days: float | None
    duration_s: int | None = None
    channel: str | None = None
    channel_id: str | None = None
    channel_url: str | None = None
    query: str | None = None

    def views_per_day(self) -> float | None:
        if self.views is None or not self.age_days:
            return None
        return self.views / max(self.age_days, 1.0)


@dataclass
class Channel:
    channel_id: str | None
    url: str
    title: str | None
    subscribers: int | None
    video_count: int | None
    recent_videos: list[Video] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


_lock = threading.Lock()


def _throttle() -> None:
    global _last_request
    with _lock:
        wait = _MIN_INTERVAL - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()


@retry(attempts=3, base_delay=2.0, exceptions=(requests.RequestException, ValueError))
def _initial_data(url: str) -> dict:
    _throttle()
    r = requests.get(url, headers=_HEADERS, cookies=_COOKIES, timeout=25)
    r.raise_for_status()
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S)
    if not m:
        raise ValueError(f"ytInitialData not found at {url}")
    return json.loads(m.group(1))


def _walk(obj, key: str, out: list) -> list:
    if isinstance(obj, dict):
        if key in obj:
            out.append(obj[key])
        for v in obj.values():
            _walk(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, key, out)
    return out


def _text(node) -> str | None:
    if not node:
        return None
    if isinstance(node, str):
        return node
    if "simpleText" in node:
        return node["simpleText"]
    if "runs" in node:
        return "".join(r.get("text", "") for r in node["runs"])
    if "content" in node:
        return node["content"]
    return None


_MULT = {"K": 1e3, "M": 1e6, "B": 1e9}


def parse_count(s: str | None) -> int | None:
    """'29,581,142 views' -> 29581142; '4.9M' -> 4900000; 'No views' -> 0."""
    if not s:
        return None
    s = s.replace(",", "").strip()
    if s.lower().startswith("no "):
        return 0
    m = re.search(r"([\d.]+)\s*([KMB])?", s, re.I)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2):
        n *= _MULT[m.group(2).upper()]
    return int(n)


_UNIT_DAYS = {"s": 1 / 86400, "second": 1 / 86400, "mi": 1 / 1440, "minute": 1 / 1440,
              "h": 1 / 24, "hour": 1 / 24, "d": 1, "day": 1, "w": 7, "week": 7,
              "mo": 30.44, "month": 30.44, "y": 365.25, "year": 365.25}


def parse_age_days(s: str | None) -> float | None:
    """'10y ago' / '3 weeks ago' / 'Streamed 2 days ago' -> days."""
    if not s:
        return None
    m = re.search(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?|months?|years?|mo|mi|s|h|d|w|y)\b",
                  s.lower())
    if not m:
        return None
    unit = m.group(2)
    unit = unit.rstrip("s") if len(unit) > 2 else unit
    return int(m.group(1)) * _UNIT_DAYS.get(unit, 1)


def parse_duration(s: str | None) -> int | None:
    if not s or ":" not in s:
        return None
    parts = [int(p) for p in s.split(":") if p.isdigit()]
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def search(query: str, sp: str = SP_VIDEO) -> list[Video]:
    url = ("https://www.youtube.com/results?search_query="
           + urllib.parse.quote_plus(query) + "&sp=" + sp)
    data = _initial_data(url)
    vids = []
    for v in _walk(data, "videoRenderer", []):
        owner = (v.get("ownerText") or {}).get("runs", [{}])[0]
        be = owner.get("navigationEndpoint", {}).get("browseEndpoint", {})
        vids.append(Video(
            video_id=v.get("videoId"),
            title=_text(v.get("title")) or "",
            views=parse_count(_text(v.get("viewCountText"))),
            age_days=parse_age_days(_text(v.get("publishedTimeText"))),
            duration_s=parse_duration(_text(v.get("lengthText"))),
            channel=owner.get("text"),
            channel_id=be.get("browseId"),
            channel_url=be.get("canonicalBaseUrl"),
            query=query,
        ))
    log.debug("search %r -> %d videos", query, len(vids))
    return vids


def channel(url_or_id: str, tab: str = "videos") -> Channel:
    """Fetch channel header stats plus the most recent ~30 uploads on a tab."""
    if url_or_id.startswith("UC"):
        base = f"https://www.youtube.com/channel/{url_or_id}"
    elif url_or_id.startswith("/"):
        base = "https://www.youtube.com" + url_or_id
    elif url_or_id.startswith("@"):
        base = "https://www.youtube.com/" + url_or_id
    else:
        base = url_or_id.rstrip("/")
    data = _initial_data(f"{base}/{tab}")
    meta = (data.get("metadata") or {}).get("channelMetadataRenderer", {})
    header_texts = [m.group(1) for m in re.finditer(
        r'"content": "([^"]{0,80})"', json.dumps(data.get("header", {})))]
    subs = vids_n = None
    for t in header_texts:
        if re.fullmatch(r"[\d.,]+[KMB]? subscribers?", t.strip()):
            subs = parse_count(t)
        elif re.fullmatch(r"[\d.,]+[KMB]? videos?", t.strip()):
            vids_n = parse_count(t)
    ch = Channel(channel_id=meta.get("externalId"), url=base, title=meta.get("title"),
                 subscribers=subs, video_count=vids_n)
    for lv in _walk(data, "lockupViewModel", []):
        vid = lv.get("contentId")
        md = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
        title = _text(md.get("title"))
        parts = [p.get("text", {}).get("content")
                 for plist in _walk(md, "metadataParts", []) for p in plist]
        views = age = None
        for p in parts:
            if not p:
                continue
            if "ago" in p:
                age = parse_age_days(p)
            elif re.search(r"\d", p):
                views = parse_count(p)
        dur = None
        for b in _walk(lv, "thumbnailBadgeViewModel", []):
            dur = parse_duration(b.get("text")) or dur
        ch.recent_videos.append(Video(video_id=vid, title=title or "", views=views, age_days=age,
                                      duration_s=dur, channel=ch.title, channel_id=ch.channel_id,
                                      channel_url=base))
    log.debug("channel %s: subs=%s videos=%d", base, subs, len(ch.recent_videos))
    return ch
