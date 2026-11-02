"""Conservative placement of CC0 ski scenery in the real Valmorel geometry.

Measured IGN building footprints/altitudes remain the source of truth.
Generic chalets replace only some simple, small existing building meshes;
we NEVER overlay a chalet on top of the same IGN building.
Resort props are placed on free terrain near published real access points.
The decorative placement offsets are explicitly approximate, NOT surveyed.
"""
from __future__ import annotations

import math
from pathlib import Path

from shapely.geometry import Point, Polygon

from config import (M_PER_DEG_LAT, M_PER_DEG_LON,
                    ll_to_local, local_to_ll, model_guid)

# Source: https://www.cirkwi.com/fr/point-interet/2628998-telecabine-de-pierrafort
PIERRAFORT_BASE = (45.458987, 6.44331)
# Source: https://www.explore-savoie.com/trains-et-remontees-mecaniques/telebourg-178060/
TELEBOURG_ACCESS = (45.462095, 6.445026)
# Source: https://hoteldubourg.com/fr/acces.html
BOURG_REFERENCE = (45.461427, 6.443471)

MAX_CHALETS = 26
MIN_SPACING_M = 13.0


def _asset(name: str, assets: dict[str, dict]) -> dict:
    if name not in assets:
        raise ValueError(f"Missing resort GLB: {name}")
    return assets[name]


def choose_chalets(buildings: list, assets: dict[str, dict]) -> dict[str, dict]:
    """Return IGN building ID -> replacement model and size.

    Replacement selection is deliberately restrictive and easy to revert.
    No shopping halls, large residential blocks, churches or heritage sites.
    """
    choices = {}
    pairs = []
    center = ll_to_local(BOURG_REFERENCE[1], BOURG_REFERENCE[0])
    for b in buildings:
        distance = math.hypot(b.east - center[0], b.north - center[1])
        if not (240 < distance < 1350):
            continue
        if b.complex or b.heritage or b.rect_fill < 0.84:
            continue
        if b.core or b.meta.get("bourg_reference_area"):
            continue
        if not (28 <= b.area <= 115 and 1 <= b.floors <= 3):
            continue
        if b.wall_h > 10 or b.roof_type == "flat" or b.rise < 0.75:
            continue
        if "commercial" in b.usage.lower() or "industri" in b.nature.lower():
            continue
        ratio = max(b.length, b.width) / max(0.5, min(b.length, b.width))
        if ratio > 1.55:
            continue
        pairs.append((distance, b))
    pairs.sort(key=lambda p: (p[0], p[1].bid))
    selected = []
    for dist, b in pairs:
        if any(math.hypot(b.east-other.east, b.north-other.north) < MIN_SPACING_M
               for other in selected):
            continue
        selected.append(b)
        asset_title = ("Mountain Guesthouse" if b.floors >= 3
                       else "Chalet Evergreen")
        spec = _asset(asset_title, assets)
        # Source CC0 chalet footprints are 5.26x5.29 and 6.56x5.45 m.
        source_area = 35.75 if asset_title == "Mountain Guesthouse" else 27.82
        scale = max(0.72, min(1.72, math.sqrt(b.area / source_area)))
        choices[b.bid] = {
            "model": spec["key"], "guid": model_guid(spec["key"]),
            "lat": round(b.lat, 8), "lon": round(b.lon, 8),
            "kind": "cc0_chalet_replacement", "count": 1,
            "alt": 0, "heading": round(b.orientation % 360, 2),
            "scale": round(scale, 4), "building_id": b.bid,
            "source": spec["source"], "source_title": spec["title"],
            "placement_precision": "IGN footprint centre, generic chalet geometry",
            "bbox": [min(p[0] for p in b.ring), min(p[1] for p in b.ring),
                     max(p[0] for p in b.ring), max(p[1] for p in b.ring)],
        }
        if len(selected) >= MAX_CHALETS:
            break
    if len(choices) < 8:
        raise RuntimeError("Too few suitable chalet footprints; no unsafe substitutions")
    return choices


def _open_ground(east: float, north: float, buildings: list, min_clearance: float) -> bool:
    point = Point(east, north)
    for b in buildings:
        if math.hypot(east-b.east, north-b.north) > 140:
            continue
        poly = Polygon(b.ring)
        if poly.distance(point) < min_clearance:
            return False
    return True


def _place_near(point: tuple[float, float], buildings: list,
                used: list[tuple[float, float]], clearance: float,
                separation: float = 7.0) -> tuple[float, float]:
    """Find open terrain near a genuine point-of-interest, not its rooftop."""
    cx, cy = ll_to_local(point[1], point[0])
    # Offsets based only on space availability; the exact prop position is
    # explicitly NOT a source-verified ski infrastructure coordinate.
    offsets = (
        (12, 12), (21, -9), (-19, 12), (13, -23), (-27, -12),
        (35, 9), (-9, 34), (9, -39), (44, -18), (-42, 15),
        (-18, -44), (53, 0), (0, 54), (-54, 0), (0, -54),
        (62, 25), (-58, 28), (30, -65), (-26, -64),
        (65, -30), (-65, -27),
    )
    for dx, dy in offsets:
        e, n = cx+dx, cy+dy
        if not _open_ground(e, n, buildings, clearance):
            continue
        if any(math.hypot(e-ex, n-ny) < separation for ex,ny in used):
            continue
        used.append((e,n))
        return (e,n)
    raise RuntimeError(f"No verified open terrain around reference point {point}")


def props_placements(buildings: list, assets: dict[str, dict]) -> list[dict]:
    """Publicly grounded anchors, with approximate free-terrain prop offsets.

    No invented ski lift alignments, floating cable spans or year-round snow
    terrain meshes are inserted. Lift-line equipment is imported to ModelLib
    for later use after real route surveys.
    """
    sites = (
        ("Pierrafort", PIERRAFORT_BASE, (
            ("Lift Bottom Station", 9.0),
            ("Ticket Office", 3.4),
            ("Snow Groomer", 4.3),
            ("Snowmaking Gun", 3.1),
            ("Snowmobile", 3.0),
            ("Trail Sign Post", 2.5),
            ("Piste Marker Pole", 2.0),
            ("Snow Fence", 3.2),
        )),
        ("Telebourg", TELEBOURG_ACCESS, (
            ("Trail Sign Post", 2.4),
            ("Piste Marker Pole", 2.0),
            ("Snowmobile", 3.0),
            ("Snowmaking Gun", 3.1),
        )),
        ("Bourg", BOURG_REFERENCE, (
            ("Seven Bay Ski Rack", 3.8),
            ("Carved Village Bench", 2.7),
            ("Twin Lantern Streetlight", 2.7),
            ("Mountain Wayfinding Post", 2.6),
        )),
    )
    placed, used = [], []
    for site, anchor, specs in sites:
        for n, (title, clearance) in enumerate(specs):
            spec = _asset(title, assets)
            east, north = _place_near(anchor, buildings, used, clearance)
            lat, lon = local_to_ll(east, north)
            placed.append({
                "model": spec["key"], "guid": model_guid(spec["key"]),
                "lat": round(lat, 8), "lon": round(lon, 8),
                "kind": "ski_station_prop", "count": 1,
                "scale": 1.0, "heading": 0,
                "site": site, "source_title": spec["title"],
                "source": spec["source"],
                "anchor_reference": {"lat": anchor[0], "lon": anchor[1]},
                "placement_precision": "illustrative offset on free terrain",
                "alt": 0,
                "bbox": [east-3, north-3, east+3, north+3],
                "exclude_autogen": False,
            })
    if len(placed) < 12:
        raise RuntimeError("Too few ski resort props to build a useful scene")
    return placed


def prepare_decorations(buildings: list, assets: dict[str, dict]):
    chalets = choose_chalets(buildings, assets)
    props = props_placements(buildings, assets)
    print("CC0 station assets:", len(assets), "model types")
    print("IGN chalet replacements:", len(chalets))
    print("Ski resort ground props:", len(props))
    return chalets, props
