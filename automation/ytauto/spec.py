"""Video spec: the single source of truth for one episode.

A spec is a YAML file at content/<video_id>/spec.yaml. Every stage reads it and
writes into content/<video_id>/build/ (regenerable) and output/<video_id>/ (deliverables).
See docs/VIDEO_SPEC.md for the schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ytauto.core import config

BEAT_TYPES = {"image", "video", "title", "fact", "quote", "scale", "chart", "list", "end"}


class SpecError(ValueError):
    pass


@dataclass
class Spec:
    path: Path
    data: dict

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def build(self) -> Path:
        p = self.dir / "build"
        p.mkdir(exist_ok=True)
        return p

    @property
    def out(self) -> Path:
        p = config.OUTPUT_DIR / self.id
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def scenes(self) -> list[dict]:
        return self.data["scenes"]

    @property
    def sources(self) -> dict[str, dict]:
        return {s["id"]: s for s in self.data.get("sources", [])}

    @property
    def assets(self) -> dict[str, dict]:
        return {a["id"]: a for a in self.data.get("assets", [])}


def load(path_or_id: str | Path) -> Spec:
    p = Path(path_or_id)
    if not p.exists():
        p = config.CONTENT_DIR / str(path_or_id) / "spec.yaml"
    if not p.exists():
        raise SpecError(f"spec not found: {path_or_id}")
    spec = Spec(p.resolve(), yaml.safe_load(p.read_text()))
    validate(spec)
    return spec


def validate(spec: Spec) -> None:
    d = spec.data
    errs = []
    for key in ("id", "title_options", "scenes", "sources"):
        if key not in d:
            errs.append(f"missing top-level '{key}'")
    src_ids = set(spec.sources)
    asset_ids = set(spec.assets)
    seen = set()
    for i, sc in enumerate(d.get("scenes", [])):
        sid = sc.get("id", f"#{i}")
        if sid in seen:
            errs.append(f"duplicate scene id {sid}")
        seen.add(sid)
        if not sc.get("narration", "").strip():
            errs.append(f"scene {sid}: empty narration")
        for c in sc.get("claims", []):
            for s in c.get("sources", []):
                if s not in src_ids:
                    errs.append(f"scene {sid}: claim cites unknown source '{s}'")
        if not sc.get("beats"):
            errs.append(f"scene {sid}: no beats")
        for b in sc.get("beats", []):
            if b.get("type") not in BEAT_TYPES:
                errs.append(f"scene {sid}: unknown beat type {b.get('type')}")
            if b.get("type") in ("image", "video") and b.get("asset") not in asset_ids:
                errs.append(f"scene {sid}: beat references unknown asset {b.get('asset')}")
            if b.get("source") and b["source"] not in src_ids:
                errs.append(f"scene {sid}: beat cites unknown source {b['source']}")
    if errs:
        raise SpecError("; ".join(errs))
