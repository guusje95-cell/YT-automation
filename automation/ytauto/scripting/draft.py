"""Unattended script drafting with Claude (Anthropic API).

Input : content/<id>/research.md — the topic, viewer question, and source notes with URLs
        (written by a person or produced by the research step; facts must come from here).
Output: content/<id>/spec.yaml (status: draft) — then the normal pipeline + human review gate.

The model is instructed to use only facts present in the research notes, attach every claim
to a source id, and propose asset *queries*; queries are resolved here to licence-checked
NASA images, so the model never invents asset IDs or licences.

Needs ANTHROPIC_API_KEY (the owner's key). Cost per draft is logged to content/<id>/build/llm_usage.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ytauto import spec as spec_mod
from ytauto.core import config
from ytauto.core.log import ROOT, get_logger

log = get_logger(__name__)

PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00)}  # USD per MTok in/out

STYLE = (ROOT / "docs" / "STYLE_GUIDE.md")
EXAMPLE = (config.CONTENT_DIR / "juno-jupiter" / "spec.yaml")

SYSTEM_TEMPLATE = """You write scripts for "{channel}", a YouTube channel of space explainers for curious adults.
Promise to viewers: real images, real numbers, no hype. Output a single video spec in YAML.

Hard rules:
- Use ONLY facts stated in the research notes. If a fact is not in the notes, leave it out.
- Every number or specific factual claim in narration must appear in that scene's `claims`, each claim citing
  source ids from `sources`. Hypotheses must be framed as hypotheses.
- Never claim anything about the present status of a mission or object unless the notes give a dated source;
  list such statements under `time_sensitive`.
- No fake urgency, no "scientists are terrified", no invented quotes, no celebrity names as bait.
- Write for the ear: short sentences, concrete comparisons, one idea per sentence, British spelling.
- Structure: hook (state the question and the payoff in under 40 seconds), 4-6 numbered sections, a short
  outro with a plain subscribe line. Target {words} words.
- Visual beats: types image, video, fact, list, title, scale, end. For image beats give `asset` ids that you
  declare under `assets` with `provider: nasa_query` and a `query` (2-5 words describing the exact picture);
  never invent NASA ids. Use `label` only for factual captions of what the image shows.
- Titles: 3 options, <= 70 characters, accurate to the content. Thumbnail: 3 variants of <= 4 words.

Style guide:
{style}

Example of a finished spec (format reference only; do not reuse its facts):
```yaml
{example}
```
Return only the YAML inside one ```yaml fenced block."""


def _system() -> str:
    return SYSTEM_TEMPLATE.format(channel=config.get("channel.name"), words="1300-1700",
                                  style=STYLE.read_text() if STYLE.exists() else "",
                                  example=EXAMPLE.read_text() if EXAMPLE.exists() else "")


def build_request(video_id: str, research: str, feedback: str | None = None) -> dict:
    user = f"Video id: {video_id}\n\nResearch notes:\n\n{research}"
    if feedback:
        user += f"\n\nYour previous draft failed validation. Fix these problems and return the full spec:\n{feedback}"
    return dict(
        model=config.get("llm.model", "claude-opus-5-5"),
        max_tokens=config.get("llm.max_tokens", 32000),
        # stable, cacheable prefix: channel rules + style guide + example spec
        system=[{"type": "text", "text": _system(), "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )


def _call(req: dict):
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    with client.beta.messages.stream(**req) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        cat = msg.stop_details.category if msg.stop_details else None
        raise RuntimeError(f"model declined the request (category {cat})")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("draft truncated at max_tokens; raise llm.max_tokens")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return text, msg.usage


def extract_yaml(text: str) -> dict:
    m = re.search(r"```yaml\s*\n(.*?)```", text, re.S)
    return yaml.safe_load(m.group(1) if m else text)


def resolve_assets(data: dict) -> dict:
    """Replace provider: nasa_query assets with concrete, licence-checked NASA ids."""
    from ytauto.assets.fetch import nasa_usable
    used: set[str] = set()
    for a in data.get("assets", []):
        if a.get("provider") != "nasa_query":
            continue
        cands = [c for c in nasa_usable(a["query"], n=25) if c["nasa_id"] not in used
                 and (c.get("width") or 0) >= 1000]
        if not cands:
            raise RuntimeError(f"no licence-clean NASA image for query {a['query']!r}")
        pick = cands[0]
        used.add(pick["nasa_id"])
        aid, query = a.get("id") or pick["nasa_id"], a["query"]
        a.clear()
        a.update({"id": aid, "provider": "nasa_images", "nasa_id": pick["nasa_id"], "picked_from_query": query})
    return data


def draft(video_id: str, max_repairs: int = 2) -> Path:
    d = config.CONTENT_DIR / video_id
    research = (d / "research.md").read_text()
    usage_log, feedback = [], None
    for attempt in range(max_repairs + 1):
        text, usage = _call(build_request(video_id, research, feedback))
        usage_log.append({"input": usage.input_tokens, "output": usage.output_tokens,
                          "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
                          "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0})
        try:
            data = resolve_assets(extract_yaml(text))
            data["id"], data["status"] = video_id, "draft"
            (d / "spec.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110))
            spec_mod.load(video_id)  # validation
            break
        except Exception as e:
            feedback = str(e)
            log.warning("draft attempt %d invalid: %s", attempt + 1, e)
    else:
        raise RuntimeError(f"draft still invalid after repairs: {feedback}")
    model = config.get("llm.model", "claude-opus-5-5")
    pin, pout = PRICES.get(model, (4.0, 20.0))
    cost = sum((u["input"] + 1.25 * u["cache_write"] + 0.1 * u["cache_read"]) * pin + u["output"] * pout
               for u in usage_log) / 1e6
    (d / "build").mkdir(exist_ok=True)
    (d / "build" / "llm_usage.json").write_text(json.dumps({"model": model, "calls": usage_log,
                                                            "est_cost_usd": round(cost, 3)}, indent=1))
    log.info("draft written for %s (est. $%.2f)", video_id, cost)
    return d / "spec.yaml"
