"""Regression checks for Valmorel residence visibility and facade UVs.

Run before importing ski GLBs. Tests are source/model-only; only the
official Windows SDK + in-game screenshot verify MSFS 2024 final appearance.
"""
from __future__ import annotations

import math

from building_gen import add_building, load_buildings, wall_ring
from fsgltf import MeshBuilder


def main() -> None:
    buildings = load_buildings()
    near = [b for b in buildings if math.hypot(b.east, b.north) < 1800]
    core = [b for b in near if b.core]
    residences = [b for b in near if b.meta.get("resort_residence_style")]
    detailed = [b for b in residences if b.core]

    assert len(buildings) > 4300, "IGN building inventory incomplete"
    assert len(near) > 250, "Valmorel scene core is missing"
    assert len(core) >= 80, "Too few downtown detailed models"
    assert len(residences) >= 25, "Residential styling did not select any major blocks"
    assert len(detailed) >= 20, "Most Alpine residences still have no mesh details"
    assert all(b.area <= 3000 for b in core), "Unsafe oversized detail building"
    print("VALMOREL RESIDENCE QA:", len(near), "nearby",
          len(core), "core detailed", len(residences),
          "Alpine residences", len(detailed), "detailed residences")

    # Old partial UVs cropped the centre window entirely when a wall
    # panel's U/V span ended before the centre of the image. Every glazed
    # panel must instead reference the entire 0..1 texture tile.
    wall = MeshBuilder()
    wall_ring(wall, [(0, 0), (3, 0), (3, 3), (0, 3)],
              0, 3, "wall_plaster_cream_win")
    group = wall.groups.get("wall_plaster_cream_win")
    assert group is not None and group["uv"], "Expected glazed facade"
    bounds = [max(v[axis] for v in group["uv"]) for axis in (0, 1)]
    assert abs(bounds[0] - 1.0) < 1e-6 and abs(bounds[1] - 1.0) < 1e-6, (
        "Glazed wall UV is cropped", bounds
    )

    # Narrow details are too small for an entire window; use plain plaster
    # instead of stretching one window into a metre-wide sliver.
    narrow = MeshBuilder()
    wall_ring(narrow, [(0, 0), (1, 0), (1, 1), (0, 1)],
              0, 3, "wall_plaster_cream_win")
    assert "wall_plaster_cream_win" not in narrow.groups, (
        "Narrow wall incorrectly receives giant squeezed window"
    )

    candidate = min(
        (b for b in detailed if 160 <= b.area <= 800),
        key=lambda b: (math.hypot(b.east, b.north), b.bid),
        default=None,
    )
    assert candidate is not None, "No detailed Alpine apartment sample"
    m = MeshBuilder()
    add_building(m, candidate, candidate.east, candidate.north, candidate.ground)
    assert m.triangle_count() > 40, "Residence has no usable geometry"
    assert ("balcony_wood" in m.groups and
            m.groups["balcony_wood"]["idx"]), (
        "Residence does not include visible timber balcony geometry"
    )
    print("GLAZED UV QA: OK; Alpine residence sample:", candidate.bid,
          "triangles:", m.triangle_count())
    print("MSFS SDK and in-game visual checks: NOT RUN")


if __name__ == "__main__":
    main()
