"""Write the BGL scenery XML: one placement per model + autogen exclusions."""
from __future__ import annotations

import json
from pathlib import Path

from config import (BUILDINGS, LAT0, LON0, M_PER_DEG_LAT, M_PER_DEG_LON,
                    SCENERY_SRC, instance_guid)

OUT = SCENERY_SRC / "valmorel_buildings.xml"


def main() -> None:
    placements = json.loads((BUILDINGS / "placements.json").read_text(encoding="utf-8"))
    SCENERY_SRC.mkdir(parents=True, exist_ok=True)
    for old in SCENERY_SRC.glob("valmorel_test_scenery.xml*"):
        old.unlink()

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<FSData version="9.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:noNamespaceSchemaLocation="bglcomp.xsd">',
        '    <!-- RealEarth Valmorel HD: IGN BD TOPO building massing -->',
    ]
    for i, p in enumerate(placements):
        gid = instance_guid(f"valmorel:{p['model']}:{i}")
        snap = "TRUE" if p.get("snap_to_ground", True) else "FALSE"
        lines.append(
            f'    <SceneryObject instanceId="{gid}" lat="{p["lat"]:.9f}" '
            f'lon="{p["lon"]:.9f}" alt="{p.get("alt", 0.0):.6f}" pitch="0.000000" bank="0.000000" '
            f'heading="{p.get("heading", 0.0):.6f}" imageComplexity="NORMAL" altitudeIsAgl="TRUE" '
            f'snapToGround="{snap}" snapToNormal="FALSE">')
        lines.append(
            f'        <LibraryObject name="{p["guid"]}" scale="{p.get("scale", 1.0):.6f}"/>')
        lines.append('    </SceneryObject>')

    # Autogen building exclusion, one rectangle per model's real footprint
    # bounding box (plus a small margin) instead of a fixed-radius guess.
    margin = 6.0
    for p in placements:
        if p.get("exclude_autogen") is False:
            # Ground props never wipe out neighbouring buildings.
            continue
        bx = p.get("bbox")
        if bx is None:
            e = (p["lon"] - LON0) * M_PER_DEG_LON
            n = (p["lat"] - LAT0) * M_PER_DEG_LAT
            e0, e1, n0, n1 = e - 15, e + 15, n - 15, n + 15
        else:
            e0, n0, e1, n1 = bx[0] - margin, bx[1] - margin, bx[2] + margin, bx[3] + margin
        lat0, lon0 = LAT0 + n0 / M_PER_DEG_LAT, LON0 + e0 / M_PER_DEG_LON
        lat1, lon1 = LAT0 + n1 / M_PER_DEG_LAT, LON0 + e1 / M_PER_DEG_LON
        lines.append(
            f'    <ExclusionRectangle latitudeMinimum="{lat0:.9f}" '
            f'latitudeMaximum="{lat1:.9f}" longitudeMinimum="{lon0:.9f}" '
            f'longitudeMaximum="{lon1:.9f}" excludeAllObjects="FALSE" '
            f'excludeGenericBuildingObjects="TRUE"/>')

    lines.append('</FSData>')
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes), {len(placements)} objects")


if __name__ == "__main__":
    main()
