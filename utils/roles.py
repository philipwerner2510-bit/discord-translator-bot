# utils/roles.py
# Helpers for level-role names and colors (centralized) + compatibility shim

from __future__ import annotations

# Default gradient: purple -> Zephyra cyan
START_HEX = "#7D2EE6"   # purple
END_HEX   = "#00E6F6"   # cyan

# Neutral, Discord-ish names (not Zephyra-branded)
ROLE_NAMES = [
    "Newbie", "Regular", "Member+", "Active", "Veteran",
    "Elite", "Epic", "Legendary", "Mythic", "Ascendant"
]

def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))

def clamp01(t: float) -> float:
    return 0.0 if t < 0 else 1.0 if t > 1 else t

def hex_to_rgb(h: str) -> tuple[int,int,int]:
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = "".join(c*2 for c in h)
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def rgb_to_int(r:int,g:int,b:int) -> int:
    return (r<<16) + (g<<8) + b

def gradient_color(start_hex: str, end_hex: str, t: float) -> int:
    """Return a Discord color int at position t (0..1) along the hex gradient."""
    t = clamp01(t)
    r1,g1,b1 = hex_to_rgb(start_hex)
    r2,g2,b2 = hex_to_rgb(end_hex)
    return rgb_to_int(lerp(r1,r2,t), lerp(g1,g2,t))

def level_bucket(index: int) -> tuple[int,int]:
    """
    Index 0..9 -> (lvl_start, lvl_end):
    0 => 1-10, 1 => 11-20, ..., 9 => 91-100
    """
    index = max(0, min(9, index))
    ls = index*10 + 1
    le = (index+1)*10
    return ls, le

def role_name_for_index(index: int, custom_names: list[str] | None = None) -> str:
    names = custom_names if (custom_names and len(custom_names) == 10) else ROLE_NAMES
    ls, le = level_bucket(index)
    return f"{names[index]} (Lv {ls}-{le})"

def make_level_role_specs(
    start_hex: str = START_HEX,
    end_hex: str = END_HEX,
    custom_names: list[str] | None = None
) -> list[tuple[int,int,str,int]]:
    """
    Returns a list of 10 specs:
    (lvl_start, lvl_end, role_name, color_int)
    """
    specs: list[tuple[int,int,str,int]] = []
    for i in range(10):
        ls, le = level_bucket(i)
        t = 0.0 if i == 0 else i/9.0
        color = gradient_color(start_hex, end_hex, t)
        name = role_name_for_index(i, custom_names)
        specs.append((ls, le, name, color))
    return specs

# ---- COMPAT SHIM (for older cogs importing `role_ladder`) ----
def role_ladder(
    start_hex: str = START_HEX,
    end_hex: str = END_HEX,
    custom_names: list[str] | None = None
) -> list[tuple[str, int]]:
    """
    Legacy API expected by some cogs:
    Returns list of 10 tuples (role_name, color_int).
    """
    specs = make_level_role_specs(start_hex, end_hex, custom_names)
    return [(name, color) for (_ls, _le, name, color) in specs]

# Optional constant if anyone wants it precomputed
ROLE_SPECS = make_level_role_specs()
