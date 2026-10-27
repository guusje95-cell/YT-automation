"""Licensed visual asset fetching with provenance.

Providers:
  nasa_images  images.nasa.gov (NASA media: generally not copyrighted in the US;
               credit NASA; no endorsement; insignia excluded)
  nasa_svs     NASA Scientific Visualization Studio (svs.gsfc.nasa.gov) media files
  openverse    api.openverse.org aggregator (only CC0 / PDM / CC BY / CC BY-SA accepted)
  url          a direct URL with licence + credit stated in the spec (e.g. ESA/Webb CC BY 4.0)
  local        a file already in content/<id>/assets (e.g. generated)

Every fetched file gets a provenance record in content/<id>/build/asset_manifest.json:
source page, file URL, licence, credit line, retrieval time and SHA-256.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
from pathlib import Path

import requests

from ytauto.core import config
from ytauto.core.log import get_logger
from ytauto.core.retry import retry

log = get_logger(__name__)

# Wikimedia's robot policy asks for a descriptive agent with a contact point
UA = {"User-Agent": "ytauto/0.1 (educational video production; https://github.com/guusje95-cell/yt-automation) "
                    "python-requests/" + requests.__version__}


class AssetError(RuntimeError):
    pass


@retry(attempts=4, base_delay=2.0, exceptions=(requests.RequestException,))
def _get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=kw.pop("timeout", 60), **kw)
    r.raise_for_status()
    return r


def _download(url: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return hashlib.sha256(dest.read_bytes()).hexdigest()
    h = hashlib.sha256()
    with _get(url, stream=True, timeout=300) as r, open(dest.with_suffix(dest.suffix + ".part"), "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
            h.update(chunk)
    dest.with_suffix(dest.suffix + ".part").rename(dest)
    return h.hexdigest()


# ---------------------------------------------------------------- NASA images
def nasa_search(q: str, media_type: str = "image", n: int = 10) -> list[dict]:
    r = _get("https://images-api.nasa.gov/search", params={"q": q, "media_type": media_type, "page_size": n})
    items = []
    for it in r.json()["collection"]["items"][:n]:
        d = it["data"][0]
        items.append({"nasa_id": d["nasa_id"], "title": d.get("title"), "center": d.get("center"),
                      "date": d.get("date_created"), "description": (d.get("description") or "")[:300],
                      "preview": (it.get("links") or [{}])[0].get("href")})
    return items


def _nasa_image(a: dict, dest_dir: Path) -> dict:
    nid = a["nasa_id"]
    files = _get(f"https://images-api.nasa.gov/asset/{nid}").json()["collection"]["items"]
    hrefs = [f["href"] for f in files]
    # prefer ~orig jpg/png, then ~large
    pick = None
    for suffix in ("~orig.jpg", "~orig.png", "~orig.tif", "~large.jpg", "~large.png", "~medium.jpg"):
        pick = next((h for h in hrefs if h.lower().endswith(suffix)), None)
        if pick:
            break
    if not pick:
        raise AssetError(f"no usable image for {nid}")
    pick = pick.replace("http://", "https://")
    meta = {}
    try:
        meta = _get(next(h for h in hrefs if h.endswith("metadata.json")).replace("http://", "https://")).json()
    except Exception:
        pass
    ext = Path(pick).suffix.lower()
    dest = dest_dir / f"{a['id']}{ext}"
    sha = _download(pick, dest)
    title = meta.get("AVAIL:Title") or nid
    lic = nasa_license_check(nid, meta, a)
    return {"file": str(dest), "source_page": f"https://images.nasa.gov/details/{nid}", "file_url": pick,
            "license": lic["license"], "title": title, "credit": a.get("credit") or lic["credit"],
            "sha256": sha, "flags": lic["flags"]}


_NC = re.compile(r"\bCC[- ]?(BY[- ])?N[CD]\b|\bN[CD][- ]SA\b|\bBY[- ]NC\b|non-?commercial|no ?derivatives|"
                 r"all rights reserved", re.I)
_OPEN = re.compile(r"\bCC[- ]?BY\b(?![- ]?N[CD])|\bCC0\b|public domain", re.I)
_CITIZEN = re.compile(r"(?i:citizen scientists?|enhanced image by|image processing(?: by)?:?|processed by|"
                      r"created by)\s+([A-Z][\w.À-ſ'-]*(?:\s+[A-Z][\w.À-ſ'-]*){0,3})")


def nasa_license_check(nid: str, meta: dict, a: dict | None = None) -> dict:
    """Decide whether a NASA-hosted image is usable in a monetized video.

    NASA's own imagery is generally not copyrighted, but many JunoCam/Photojournal items are
    processed by citizen scientists under their own licences (often CC BY-NC-SA). Rules:
      - any non-commercial / no-derivatives / all-rights-reserved marker anywhere -> blocked
      - citizen-processed without an explicit CC BY / CC0 / public-domain statement -> blocked
      - otherwise allowed, credited with NASA's own credit line
    A spec may set `license_override: "<reason>"` after a manual check.
    """
    a = a or {}
    fields = [str(meta.get(k) or "") for k in
              ("AVAIL:Description", "AVAIL:SecondaryCreator", "AVAIL:Photographer", "AVAIL:Keywords")]
    text = re.sub(r"<[^>]+>", " ", " | ".join(fields))
    flags = []
    if a.get("license_override"):
        flags.append(f"license override: {a['license_override']}")
    else:
        m = _NC.search(text)
        if m:
            raise AssetError(f"{nid}: restrictive licence marker {m.group(0)!r}; not usable in a monetized video")
        cit = _CITIZEN.search(text)
        if cit and not _OPEN.search(text):
            raise AssetError(f"{nid}: processed by {cit.group(1)} with no stated open licence; "
                             "verify manually and set license_override, or pick another image")
        if cit:
            flags.append(f"citizen-processed by {cit.group(1)} under an open licence: credit by name")
        if re.search(r"©|copyright", text, re.I) and not _OPEN.search(text):
            flags.append("copyright mention: verify")
    secondary = (meta.get("AVAIL:SecondaryCreator") or "").strip()
    credit = secondary or "NASA/JPL-Caltech"
    if not secondary:
        m = re.search(r"((?:Enhanced )?image (?:processing )?by .+?based on images provided courtesy of "
                      r"[A-Za-z/ -]+)", text, re.I)
        if m:
            credit = m.group(1).strip()
    return {"license": "nasa-media", "credit": credit, "flags": flags}


def nasa_usable(q: str, n: int = 25) -> list[dict]:
    """Search NASA images and return only items that pass the licence check (for automated selection)."""
    out = []
    for it in nasa_search(q, n=n):
        try:
            meta = _get(f"https://images-assets.nasa.gov/image/{it['nasa_id']}/metadata.json").json()
            lic = nasa_license_check(it["nasa_id"], meta)
            out.append(it | {"credit": lic["credit"], "flags": lic["flags"],
                             "width": meta.get("File:ImageWidth"), "height": meta.get("File:ImageHeight")})
        except Exception as e:
            log.debug("skip %s: %s", it["nasa_id"], e)
    return out


# ---------------------------------------------------------------- NASA SVS
def _nasa_svs(a: dict, dest_dir: Path) -> dict:
    sid = a["svs_id"]
    page = _get(f"https://svs.gsfc.nasa.gov/api/{sid}").json()
    media = []

    def walk(o):
        if isinstance(o, dict):
            if "url" in o and isinstance(o.get("url"), str) and o.get("media_type") in ("Movie", "Image"):
                media.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(page)
    want = a.get("file_hint", "")
    kind = "Movie" if a.get("kind", "video") == "video" else "Image"
    cands = [m for m in media if m.get("media_type") == kind and (want in m["url"])]
    if kind == "Movie":
        cands = [m for m in cands if m["url"].lower().endswith((".mp4", ".mov", ".webm"))]
        # prefer 1080p-ish, not 4K (size), not huge
        cands.sort(key=lambda m: (abs((m.get("height") or 1080) - 1080), m.get("filesize") or 0))
    else:
        cands.sort(key=lambda m: -(m.get("width") or 0))
    if not cands:
        raise AssetError(f"SVS {sid}: no {kind} matching '{want}'")
    m = cands[0]
    url = m["url"].replace("http://", "https://")
    dest = dest_dir / f"{a['id']}{Path(url).suffix.lower()}"
    sha = _download(url, dest)
    credit = a.get("credit") or (page.get("credits") and "NASA's Scientific Visualization Studio") or "NASA SVS"
    return {"file": str(dest), "source_page": f"https://svs.gsfc.nasa.gov/{sid}", "file_url": url,
            "license": "nasa-media", "title": page.get("title"), "credit": credit, "sha256": sha, "flags": []}


# ---------------------------------------------------------------- Openverse
_OV_LICENSES = {"cc0": "cc0", "pdm": "pdm", "by": "cc-by", "by-sa": "cc-by-sa"}


def openverse_search(q: str, n: int = 10) -> list[dict]:
    r = _get("https://api.openverse.org/v1/images/",
             params={"q": q, "license": ",".join(_OV_LICENSES), "page_size": n})
    return r.json()["results"]


WIKIMEDIA_THUMB_WIDTHS = (2560, 1920, 1280)   # standard thumbnail steps; Wikimedia asks bulk users to use these


def _wikimedia_thumbs(url: str, width: int | None) -> list[str]:
    """Standard-size thumbnail URLs for a Wikimedia Commons original, largest first (never upscaled)."""
    m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w/\w\w)/([^/]+)$", url)
    if not m:
        return []
    name = m.group(2)
    return [f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{name}/{w}px-{name}"
            for w in WIKIMEDIA_THUMB_WIDTHS if not width or w < width]


def _openverse(a: dict, dest_dir: Path) -> dict:
    for attempt in range(5):   # the detail endpoint returns sporadic 500s; space out the retries
        try:
            r = _get(f"https://api.openverse.org/v1/images/{a['openverse_id']}/").json()
            break
        except requests.HTTPError as e:
            if attempt == 4:
                raise
            log.warning("openverse %s unavailable (%s); waiting before retry", a["openverse_id"], e)
            time.sleep(30 * (attempt + 1))
    lic = _OV_LICENSES.get(r["license"])
    if not lic:
        raise AssetError(f"openverse {a['openverse_id']}: licence {r['license']} not allowed")
    dest = dest_dir / f"{a['id']}{Path(r['url']).suffix.lower() or '.jpg'}"
    url = r["url"]
    for cand in _wikimedia_thumbs(url, r.get("width")) + [url]:
        try:
            sha = _download(cand, dest)
            url = cand
            break
        except Exception as e:  # noqa: BLE001  (try the next size; the last candidate re-raises)
            if cand == url:
                raise
            log.warning("openverse %s: %s failed (%s)", a["openverse_id"], cand, e)
    credit = r.get("attribution") or f"{r.get('title')} by {r.get('creator')} ({r['license']})"
    return {"file": str(dest), "source_page": r.get("foreign_landing_url"), "file_url": url, "license": lic,
            "license_url": r.get("license_url"), "title": r.get("title"), "credit": credit, "sha256": sha, "flags": []}


# ---------------------------------------------------------------- direct URL / local
def _url(a: dict, dest_dir: Path) -> dict:
    for k in ("license", "credit", "source_page"):
        if not a.get(k):
            raise AssetError(f"asset {a['id']}: provider 'url' requires '{k}'")
    dest = dest_dir / f"{a['id']}{Path(a['url'].split('?')[0]).suffix.lower() or '.jpg'}"
    sha = _download(a["url"], dest)
    return {"file": str(dest), "source_page": a["source_page"], "file_url": a["url"], "license": a["license"],
            "title": a.get("title"), "credit": a["credit"], "sha256": sha, "flags": []}


def _local(a: dict, dest_dir: Path) -> dict:
    p = Path(a["path"])
    if not p.is_absolute():
        p = dest_dir.parent.parent / p
    if not p.exists():
        raise AssetError(f"local asset missing: {p}")
    return {"file": str(p), "source_page": None, "file_url": None, "license": a.get("license", "generated"),
            "title": a.get("title"), "credit": a.get("credit", ""),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "flags": []}


PROVIDERS = {"nasa_images": _nasa_image, "nasa_svs": _nasa_svs, "openverse": _openverse, "url": _url, "local": _local}


def fetch_all(spec) -> dict:
    """Fetch every asset in the spec; returns {asset_id: provenance}. Fails loudly on licence problems."""
    dest_dir = spec.build / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = spec.build / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    allowed = set(config.get("assets.allowed_licenses", []))
    for aid, a in spec.assets.items():
        if aid in manifest and Path(manifest[aid]["file"]).exists() and manifest[aid].get("spec") == a:
            continue
        prov = PROVIDERS[a["provider"]](a, dest_dir)
        lic = prov["license"].lower().replace(" 4.0", "").replace(" ", "-")
        if lic not in allowed:
            raise AssetError(f"asset {aid}: licence '{prov['license']}' not in allowed list {sorted(allowed)}")
        prov.update({"id": aid, "provider": a["provider"], "spec": a,
                     "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        manifest[aid] = prov
        log.info("asset %s <- %s (%s)", aid, prov.get("source_page"), prov["license"])
        manifest_path.write_text(json.dumps(manifest, indent=1))
    return manifest
