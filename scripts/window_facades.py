"""Bake inexpensive window motifs into the existing Valmorel wall textures.

Almost all MSFS 2024 models are grouped buildings without individual window
geometry. Previously every *_win material referenced the *same* bare-wall PNG
as its non-window counterpart; those facades appeared as featureless boxes.

This module composes one window from the already-shipped windows_atlas.png
onto a copy of each source wall texture. Original sources under assets/ are
NEVER overwritten. Derived PNGs are saved in ignored build/ and subsequently
converted by the MSFS SDK using the normal PNG + XML sidecar pipeline.

Artwork is illustrative. This is not a claim of exact surveyed windows.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _window_motif(pack_dir: Path, size: int = 1024) -> Image.Image:
    atlas_path = pack_dir / "windows_atlas.png"
    if not atlas_path.is_file():
        raise FileNotFoundError(f"missing windows atlas: {atlas_path}")
    with Image.open(atlas_path) as im:
        atlas = im.convert("RGB")
        if atlas.size != (1024, 1024):
            raise ValueError(f"windows_atlas.png must be 1024x1024: {atlas.size}")
        # One window in the upper-left of the 3-column, 2-row atlas.
        source = atlas.crop((0, 0, 341, 512))
        pixels = np.asarray(source, dtype=np.uint8)
        # The supplied atlas is RGB and uses black as *background*, not alpha.
        # Remove that black and retain the frame, mullions and glass.
        opaque = (pixels.max(axis=2) > 20).astype(np.uint8) * 255
        rgba = np.dstack((pixels, opaque))
        motif = Image.fromarray(rgba, mode="RGBA")
        bbox = motif.getbbox()
        if bbox is None:
            raise ValueError("window atlas does not contain a window")
        motif = motif.crop(bbox)
        # One full window + surround per 4m facade texture tile. Avoid extra
        # mesh triangles on the ~2,000 distant/clustered models.
        box_width = int(size * 0.47)
        box_height = int(size * 0.54)
        motif.thumbnail((box_width, box_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size))
        x = (size - motif.width) // 2
        y = (size - motif.height) // 2
        canvas.alpha_composite(motif, (x, y))
        return canvas


def bake_window_facades(
    original_slots: dict[str, Path], pack_dir: Path, output_dir: Path
) -> dict[str, Path]:
    """Return a copy of slot mapping with unique baked *_win facade PNGs.

    The new PNG names differ from their source images, ensuring the glTF
    writer and MSFS SDK can distinguish glazed and plain wall materials.
    """
    window_slots = {
        slot: Path(source)
        for slot, source in original_slots.items()
        if slot.startswith("wall_") and slot.endswith("_win")
    }
    if not window_slots:
        return dict(original_slots)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = dict(original_slots)
    for slot, source in window_slots.items():
        with Image.open(source) as img:
            size = img.size
            if size[0] != size[1] or size[0] < 256:
                raise ValueError(f"{source.name}: wall tile must be square >= 256px")
            base = img.convert("RGBA")
        motif = _window_motif(pack_dir, size[0])
        rendered = Image.alpha_composite(base, motif).convert("RGB")
        derived = output_dir / f"{slot}_basecolor.png"
        rendered.save(derived, format="PNG", optimize=True)
        result[slot] = derived
    return result
