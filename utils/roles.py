# utils/roles.py
from typing import List, Dict

# Gradient endpoints
PURPLE = 0x9B59B6  # start
CYAN   = 0x00E6F6  # end (Zephyra brand color)

# 10 tiers covering 1..100 (inclusive), step 10
# Names: neutral & Discord-appropriate (no brand terms)
TIER_SPECS = [
    (1,   "Rookie"),
    (10,  "Member"),
    (20,  "Regular"),
    (30,  "Skilled"),
    (40,  "Advanced"),
    (50,  "Expert"),
    (60,  "Veteran"),
    (70,  "Elite"),
    (80,  "Champion"),
    (90,  "Legend"),   # covers 90-99; Level 100 still falls here (last tier)
]

def _lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))

def _int_to_rgb(x: int):
    return (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF

def _rgb_to_int(r: int, g: int, b: int) -> int:
    return (r << 16) | (g << 8) | b

def _gradient(n: int) -> List[int]:
    sr, sg, sb = _int_to_rgb(PURPLE)
    er, eg, eb = _int_to_rgb(CYAN)
    cols = []
    if n <= 1:
        return [_rgb_to_int(sr, sg, sb)]
    for i in range(n):
        t = i / (n - 1)
        r = _lerp(sr, er, t)
        g = _lerp(sg, eg, t)
        b = _lerp(sb, eb, t)
        cols.append(_rgb_to_int(r, g, b))
    return cols

def role_ladder() -> List[Dict]:
    colors = _gradient(len(TIER_SPECS))
    ladder = []
    for (i, (min_level, name)) in enumerate(TIER_SPECS):
        ladder.append({
            "min_level": min_level,   # inclusive
            "name": name,
            "color": colors[i],
        })
    return ladder

def best_role_for_level(level: int) -> Dict:
    tiers = role_ladder()
    best = tiers[0]
    for t in tiers:
        if level >= t["min_level"]:
            best = t
    return best
