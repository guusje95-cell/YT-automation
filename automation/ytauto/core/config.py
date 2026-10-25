"""Project configuration: non-secret settings from config/settings.yaml,
secrets only from environment variables (optionally loaded from a local,
git-ignored .env file)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

from ytauto.core.log import ROOT

CONFIG_DIR = ROOT / "config"
CONTENT_DIR = ROOT / "content"
OUTPUT_DIR = ROOT / "output"
ANALYTICS_DIR = ROOT / "analytics"
MODELS_DIR = ROOT / "models"
CACHE_DIR = ROOT / ".cache"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


@lru_cache
def settings() -> dict:
    return yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())


def secret(name: str, required: bool = False) -> str | None:
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(f"Missing secret {name}. Set it in the environment or .env (see docs/SETUP.md).")
    return val


def get(path: str, default=None):
    """settings lookup with dotted path, e.g. get('voice.provider')."""
    node = settings()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
