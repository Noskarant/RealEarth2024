"""Duplicate-footprint and coverage checks on the final placements."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from config import BUILDINGS, LAT0, LON0, M_PER_DEG_LAT, M_PER_DEG_LON
from PIL import Image, ImageDraw

PLACEMENTS = BUILDINGS / "placements.json"
OUT_PNG = Path(r"D:\RealEarth2024\logs\qa_coverage.png")

CELL = 2.0  # metres


def main() -> None:
    pl = json.loads(PLACEMENTS.read_text(encoding="utf-8"))
    grid: dict[tuple[int, int], list] = defaultdict(list)
    for p in pl:
        e = (p["lon"] - LON0) * M_PER_DEG_LON
        n = (p["lat"] - LAT0) * M_PER_DEG_LAT
        grid[(int(e // CELL), int(n // CELL))].append(p["model"])

    dups = {k: v for k, v in grid.items() if len(v) > 1}
    print(f"placements={len(pl)} duplicate_cells={len(dups)}")
    for k, v in list(dups.items())[:5]:
        print("  ", k, v)

    # Coverage image from placement bounding boxes.
    xs, ys = [], []
    for p in pl:
        bx = p.get("bbox")
        if not bx:
            continue
        xs.extend([bx[0], bx[2]])
        ys.extend([bx[1], bx[3]])
    print(f"scene extent east [{min(xs):.0f}, {max(xs):.0f}] m "
          f"north [{min(ys):.0f}, {max(ys):.0f}] m")

    w, h = 1100, 1000
    pad = 20
    sx = (w - 2 * pad) / max(1.0, max(xs) - min(xs))
    sy = (h - 2 * pad) / max(1.0, max(ys) - min(ys))
    s = min(sx, sy)
    img = Image.new("RGB", (w, h), (18, 22, 28))
    dr = ImageDraw.Draw(img)
    for p in pl:
        bx = p.get("bbox")
        if not bx:
            continue
        x0 = pad + (bx[0] - min(xs)) * s
        x1 = pad + (bx[2] - min(xs)) * s
        y0 = h - pad - (bx[3] - min(ys)) * s
        y1 = h - pad - (bx[1] - min(ys)) * s
        colour = (240, 170, 70) if p["kind"] == "core" else (90, 170, 240)
        dr.rectangle([x0, y0, x1, y1], fill=colour)
    dr.text((pad, 6), f"{len(pl)} models - orange=detailed core, blue=cluster",
            fill=(230, 230, 230))
    img.save(OUT_PNG)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
