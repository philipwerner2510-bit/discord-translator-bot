# utils/roles.py
# Level-role helpers + safe color utilities + legacy shim

from __future__ import annotations

START_HEX = "#7D2EE6"   # purple
END_HEX   = "#00E6F6"   # Zephyra cyan

ROLE_NAMES = [
    "Newbie", "Regular", "Member+", "Active", "Veteran",
    "Elite", "Epic", "Legendary", "Mythic", "Ascendant"
]

def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))

def clamp01(t: float) -> float:
    return 0.0 if t < 0 else 1.0 if t > 1 else t

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rgb_to_int(*args) -> int:
    """
    Flexible: accepts (r,g,b) OR (r,g) -> b=0 OR single iterable (r,g,b).
    Prevents TypeError when older code passes 2 args or a tuple.
    """
    r = g = b = None
    if len(args) == 1 and hasattr(args[0], "__iter__"):
        vals = list(args[0])
    else:
        vals = list(args)
    if len(vals) == 3:
        r, g, b = vals
    elif len(vals) == 2:
        r, g = vals
        b = 0
    else:
        raise TypeError("rgb_to_int expects (r,g,b), (r,g), or iterable of length 3")
    return (int(r) << 16) + (int(g) << 8) + int(b)

def color_from_hex(h: str) -> int:
    return rgb_to_int(hex_to_rgb(h))

def gradient_color(start_hex: str, end_hex: str, t: float) -> int:
    t = clamp01(t)
    r1, g1, b1 = hex_to_rgb(start_hex)
    r2, g2, b2 = hex_to_rgb(end_hex)
    return rgb_to_int(
        lerp(r1, r2, t),
        lerp(g1, g2, t),
        lerp(b1, b2, t),
    )

def level_bucket(index: int) -> tuple[int, int]:
    index = max(0, min(9, index))
    ls = index * 10 + 1
    le = (index + 1) * 10
    return ls, le

def role_name_for_index(index: int, custom_names: list[str] | None = None) -> str:
    names = custom_names if (custom_names and len(custom_names) == 10) else ROLE_NAMES
    ls, le = level_bucket(index)
    return f"{names[index]} (Lv {ls}-{le})"

def make_level_role_specs(
    start_hex: str = START_HEX,
    end_hex: str = END_HEX,
    custom_names: list[str] | None = None,
) -> list[tuple[int, int, str, int]]:
    """
    Returns 10 tuples: (lvl_start, lvl_end, role_name, color_int)
    """
    specs: list[tuple[int, int, str, int]] = []
    for i in range(10):
        ls, le = level_bucket(i)
        t = 0.0 if i == 0 else i / 9.0
        color = gradient_color(start_hex, end_hex, t)
        name = role_name_for_index(i, custom_names)
        specs.append((ls, le, name, color))
    return specs

# Legacy shim for older imports
def role_ladder(
    start_hex: str = START_HEX,
    end_hex: str = END_HEX,
    custom_names: list[str] | None = None,
) -> list[tuple[str, int]]:
    specs = make_level_role_specs(start_hex, end_hex, custom_names)
    return [(name, color) for (_ls, _le, name, color) in specs]

ROLE_SPECS = make_level_role_specs()
