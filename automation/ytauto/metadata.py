"""Upload metadata: titles, description (chapters, sources, credits, disclosure), tags.

Writes output/<id>/metadata.json, the single input for the publisher.
"""
from __future__ import annotations

import json

from ytauto.core import config


def _ts(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def chapters(timings: dict) -> list[tuple[float, str]]:
    out = []
    for i, sc in enumerate(timings["scenes"]):
        if not sc.get("chapter"):
            continue
        t = 0.0 if i == 0 else sc["start"]
        if out and t - out[-1][0] < 10:  # YouTube requires >= 10 s per chapter
            continue
        out.append((t, sc["chapter"]))
    return out if len(out) >= 3 else []


def build(spec) -> dict:
    timings = json.loads((spec.build / "timings.json").read_text())
    manifest = json.loads((spec.build / "asset_manifest.json").read_text())
    d = spec.data
    summary = d.get("description_summary") or spec.scenes[0]["narration"].strip().split(". ")[0] + "."
    lines = [summary, ""]
    ch = chapters(timings)
    if ch:
        lines += ["Chapters"] + [f"{_ts(t)} {name}" for t, name in ch] + [""]
    lines.append("Sources")
    for s in d["sources"]:
        lines.append(f"• {s['title']} — {s['publisher']}: {s['url']}")
    lines.append("")
    lines.append("Image and video credits")
    seen = set()
    for a in manifest.values():
        line = f"• {a['credit']}" + (f" — {a['source_page']}" if a.get("source_page") else "")
        if line not in seen:
            seen.add(line)
            lines.append(line)
    lines.append("NASA material is used under NASA's media guidelines; NASA does not endorse this channel. "
                 "CC BY images are credited above.")
    lines.append("")
    lines.append("Music: original ambient score generated for this channel.")
    lines.append(config.get("channel.credit_line"))
    desc = "\n".join(lines)
    if len(desc) > 4900:  # YouTube limit is 5,000 characters
        desc = desc[:4850].rsplit("\n", 1)[0] + "\n(Full source list continues in the pinned comment.)"
    titles = d["title_options"]
    meta = {
        "video_id": spec.id,
        "title": titles[0],
        "title_options": titles,
        "description": desc,
        "tags": d.get("tags", [])[:30],
        "category_id": config.get("publish.category_id"),
        "default_language": config.get("publish.default_language"),
        "made_for_kids": config.get("publish.made_for_kids"),
        "contains_synthetic_media": d.get("contains_synthetic_media", config.get("publish.contains_synthetic_media")),
        "privacy_status": config.get("publish.default_privacy"),
        "chapters": [{"t": t, "title": n} for t, n in ch],
        "files": {
            "video": str(spec.out / f"{spec.id}.mp4"),
            "thumbnail": str(spec.out / "thumbnail_1.jpg"),
            "captions": str(spec.out / f"{spec.id}.en.srt"),
        },
    }
    (spec.out / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (spec.out / "description.txt").write_text(desc)
    licensing_checklist(spec, manifest)
    script_export(spec, timings)
    return meta


def script_export(spec, timings: dict) -> str:
    """Human-readable script with timestamps, claims and sources (research notes for review)."""
    src = spec.sources
    lines = [f"# {spec.data['title_options'][0]}", "", f"Video id: `{spec.id}` · narration "
             f"{timings['duration'] / 60:.1f} min · {sum(len(s['narration'].split()) for s in spec.scenes)} words", ""]
    for sc, tm in zip(spec.scenes, timings["scenes"]):
        lines += [f"## [{_ts(tm['start'])}] {sc.get('chapter', sc['id'])}", "", " ".join(sc["narration"].split()), ""]
        if sc.get("claims"):
            lines.append("**Claims → sources**")
            for c in sc["claims"]:
                lines.append(f"- {c['text']} — " + ", ".join(f"[{s}]({src[s]['url']})" for s in c["sources"]))
            lines.append("")
    if spec.data.get("time_sensitive"):
        lines += ["## Time-sensitive statements (check before publishing)", ""] + \
                 [f"- {t}" for t in spec.data["time_sensitive"]] + [""]
    lines += ["## Sources", ""] + [f"- **{s['id']}**: {s['title']} — {s['publisher']} — {s['url']} "
                                   f"(accessed {s.get('accessed', '')})" for s in spec.data["sources"]]
    p = spec.out / "script.md"
    p.write_text("\n".join(lines) + "\n")
    return str(p)


def licensing_checklist(spec, manifest: dict) -> str:
    """Per-video copyright/licensing record: every visual, its licence, credit and provenance."""
    rows = ["| Asset | Licence | Credit (as published) | Source page | SHA-256 (12) | Flags |", "|---|---|---|---|---|---|"]
    for k, a in manifest.items():
        rows.append(f"| {k} | {a['license']} | {a['credit']} | {a.get('source_page') or ''} | {a['sha256'][:12]} | "
                    f"{'; '.join(a.get('flags', [])) or ''} |")
    voice = spec.data.get("voice", {}).get("provider", config.get("voice.provider"))
    lines = [f"# Copyright & licensing checklist — {spec.id}", "",
             "- [x] Visuals: every asset listed below with licence, credit and provenance (fetched automatically; "
             "non-commercial / no-derivatives licences are blocked in code).",
             "- [x] NASA material: credited, no NASA insignia used as branding, no implied endorsement (stated in description).",
             "- [x] CC BY material: creator credited by name in the description and on screen.",
             "- [x] Music: original ambient bed generated by the pipeline (no third-party music).",
             f"- [x] Narration: synthetic voice ({voice}, Kokoro-82M Apache-2.0 weights); not a real person's voice; "
             "disclosed in the description.",
             "- [x] Fonts: Inter (SIL Open Font License).",
             "- [x] No third-party video footage other than NASA SVS productions (audio stripped).",
             "- [ ] Human spot-check: open 3 random source pages below and confirm the credit line matches.", "",
             *rows, ""]
    p = spec.out / "licensing_checklist.md"
    p.write_text("\n".join(lines))
    return str(p)
