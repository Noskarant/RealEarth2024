"""Map the pipeline's material slots to the Valmorel texture pack.

The pack (D:\\RealEarth2024\\assets\\valmorel_complete) is a set of generated,
freely reusable 1024 px materials. It is not a photographic survey: these are
stylised surfaces, so a textured building stays a category B reconstruction.

Both individual buildings and merged clusters use these source textures.
The SDK must compile their PNG + XML sidecars into runtime KTX2 files.
"""
from __future__ import annotations

from pathlib import Path

PACK = Path(__file__).resolve().parents[1] / "assets" / "valmorel_complete"

# pipeline material slot -> pack material name
SLOT_TO_PACK = {
    "wall_wood": "wood_brown_vertical",
    "wall_wood_win": "wood_brown_vertical",
    "wall_stone": "stone_grey_rubble",
    "wall_stone_win": "stone_grey_rubble",
    "wall_plaster": "plaster_cream",
    "wall_plaster_win": "plaster_cream",
    "wall_brick": "masonry_beige",
    "wall_brick_win": "masonry_beige",
    "wall_concrete": "plaster_light_grey",
    "wall_concrete_win": "plaster_light_grey",
    "roof_slate": "roof_lauze_grey",
    "roof_metal": "roof_metal_grey",
    "roof_tile": "roof_shingle_brown",
    "roof_flat": "masonry_grey",
    "roof_thatch": "wood_horizontal",
    "stone_base": "stone_warm_rubble",
    "glass": "glass_reflection",
    "frame": "window_frame_white",
    "balcony_wood": "wood_balcony_warm",
    "chimney": "chimney_stone",
    "door_wood": "door_wood_dark",
}


def pack_map() -> dict[str, Path]:
    """material slot -> basecolor PNG, raising early on a missing asset."""
    out: dict[str, Path] = {}
    missing = []
    for slot, name in SLOT_TO_PACK.items():
        png = PACK / f"{name}_basecolor.png"
        if not png.is_file():
            missing.append(png.name)
            continue
        out[slot] = png
    if missing:
        raise FileNotFoundError(f"texture pack incomplete: {sorted(set(missing))}")
    return out


if __name__ == "__main__":
    m = pack_map()
    for k, v in sorted(m.items()):
        print(f"{k:20s} -> {v.name}  {v.stat().st_size // 1024} KiB")
