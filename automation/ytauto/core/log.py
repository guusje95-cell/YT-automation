import logging
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = ROOT / "logs"

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        LOG_DIR.mkdir(exist_ok=True)
        level = os.environ.get("YTAUTO_LOG_LEVEL", "INFO").upper()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        root = logging.getLogger("ytauto")
        root.setLevel(level)
        fh = logging.FileHandler(LOG_DIR / "ytauto.log")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(fh)
        root.addHandler(sh)
        _configured = True
    if not name.startswith("ytauto"):
        name = "ytauto." + name
    return logging.getLogger(name)
