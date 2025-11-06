# utils/roles.py
# Role ladder + color utilities (purple → Zephyra cyan)

from __future__ import annotations
from typing import List, Tuple

# Start/end of the gradient (RGB ints)
PURPLE_START = 0x7A2CF0  # rich discord-ish purple
CYAN_END     = 0x00E6F6  # Zephyra storm-cyan

def _hex_to_rgb(c: int) -> Tuple[int, int, int]:
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF

def _rgb_to_hex(r: int, g: int, b: int) -> int:
    return (r << 16) | (g << 8) | b

def gradient_color(start_hex: int, end_hex: int, t: float) -> int:
    """Linear RGB gradient. t in [0,1]."""
    sr, sg, sb = _hex_to_rgb(start_hex)
    er, eg, eb = _hex_to_rgb(end_hex)
    r = round(sr + (er - sr) * t)
    g = round(sg + (eg - sg) * t)
    b = round(sb + (eb - sb) * t)
    return _rgb_to_hex(max(0, min(255, r)),
                       max(0, min(255, g)),
                       max(0, min(255, b)))

# 10 bands: 1–10, 11–20, …, 91–100
ROLE_NAMES = [
    "Newcomer",      # 1–10
    "Member",        # 11–20
    "Regular",       # 21–30
    "Contributor",   # 31–40
    "Active",        # 41–50
    "Veteran",       # 51–60
    "Elite",         # 61–70
    "Champion",      # 71–80
    "Mythic",        # 81–90
    "Legend",        # 91–100
]

def role_ladder() -> List[dict]:
    """
    Returns 10 role specs:
      { "min": int, "max": int, "name": str, "color": int }
    Colors are evenly spaced from PURPLE_START → CYAN_END.
    """
    out: List[dict] = []
    total = len(ROLE_NAMES)
    for i, name in enumerate(ROLE_NAMES):
        t = i / max(1, total - 1)
        col = gradient_color(PURPLE_START, CYAN_END, t)
        out.append({
            "min": i * 10 + 1,
            "max": (i + 1) * 10,
            "name": name,
            "color": col
        })
    return out
