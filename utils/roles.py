# utils/roles.py
# Role ladder generator and gradient utilities (purple -> Zephyra cyan)
from typing import List, Dict

# Start: purple, End: Zephyra cyan
START = 0x8A2BE2  # purple-ish
END   = 0x00E6F6  # Zephyra primary

BANDS = [
    (1, 10,  "Rookie I"),
    (11, 20, "Rookie II"),
    (21, 30, "Challenger"),
    (31, 40, "Adept"),
    (41, 50, "Expert"),
    (51, 60, "Elite"),
    (61, 70, "Master"),
    (71, 80, "Grandmaster"),
    (81, 90, "Legend"),
    (91, 100,"Mythic"),
]

def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)

def gradient_color(index: int, total: int) -> int:
    """Inclusive index (0..total-1)."""
    if total <= 1:
        return END
    t = index / (total - 1)
    sr, sg, sb = (START >> 16) & 0xFF, (START >> 8) & 0xFF, START & 0xFF
    er, eg, eb = (END >> 16) & 0xFF, (END >> 8) & 0xFF, END & 0xFF
    r = _lerp(sr, er, t)
    g = _lerp(sg, eg, t)
    b = _lerp(sb, eb, t)
    return (r << 16) | (g << 8) | b

def role_ladder() -> List[Dict]:
    """
    Returns an array of 10 role specs with name + color, fading purple->cyan.
    """
    total = len(BANDS)
    roles = []
    for i, (_, _, name) in enumerate(BANDS):
        roles.append({
            "name": name,
            "color": gradient_color(i, total)
        })
    return roles
