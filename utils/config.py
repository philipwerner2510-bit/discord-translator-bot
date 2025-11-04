# utils/config.py  (NEW)
from __future__ import annotations
import json, os
from dataclasses import dataclass, field
from typing import List

_DEFAULT_LANGS = [
    "en","zh","hi","es","fr","ar","bn","pt","ru","ja",
    "de","jv","ko","vi","mr","ta","ur","tr","it","th",
    "gu","kn","ml","pa","or","fa","sw","am","ha","yo"
]

@dataclass(frozen=True)
class AppConfig:
    default_rate_limit: int = 5
    reaction_timeout: int = 300
    supported_langs: List[str] = field(default_factory=lambda: list(_DEFAULT_LANGS))

def _coerce_langs(v) -> List[str]:
    if isinstance(v, list) and all(isinstance(i, str) for i in v):
        return [i.lower() for i in v]
    return list(_DEFAULT_LANGS)

def load_config() -> AppConfig:
    path = os.getenv("BOT_CONFIG_PATH", "config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    return AppConfig(
        default_rate_limit=int(data.get("default_rate_limit", 5)),
        reaction_timeout=int(data.get("reaction_timeout", 300)),
        supported_langs=_coerce_langs(data.get("supported_langs")),
    )

CONFIG = load_config()
SUPPORTED_LANGS = CONFIG.supported_langs