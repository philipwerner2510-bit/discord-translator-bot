# utils/config.py
import os

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

# General
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# XP tuning (env overrides)
XP_MSG = _int("XP_MSG", 5)                    # XP per message
XP_TRANSLATION = _int("XP_TRANSLATION", 10)   # XP per successful translation
VOICE_GRANULARITY = _int("VOICE_GRANULARITY", 30)  # seconds per write
VOICE_XP_PER_MIN = _int("VOICE_XP_PER_MIN", 1)     # XP per minute in voice (0 to disable)

# Leaderboard page size
LEADERBOARD_PAGE = _int("LEADERBOARD_PAGE", 10)
