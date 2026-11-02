"""Reference-informed architectural treatment for the Valmorel Bourg area.

The Hotel du Bourg GPS position is published by the hotel:
https://hoteldubourg.com/fr/acces.html (45.461427, 6.443471).

The radius is an *approximate visual-editing zone*, not an asserted parcel
boundary or an exact street / commercial-building classification. Do not
claim that these heuristic finishes match an individual building. Preserve
the measured IGN footprint, height, altitude and recorded roof type.

Architecture reference:
https://www.valmorel.com/la-destination/histoire/
https://patrimoines.savoie.fr/upload/docs/application/pdf/2021-02/la-rubrique-n46-mail_2021-02-04_14-38-44_678.pdf
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from config import M_PER_DEG_LAT, M_PER_DEG_LON, deterministic_int

if TYPE_CHECKING:
    from building_gen import Building

HOTEL_DU_BOURG_LAT = 45.461427
HOTEL_DU_BOURG_LON = 6.443471
BOURG_REFERENCE_RADIUS_M = 165.0

# Existing textures in assets/valmorel_complete, not downloaded photos.
BOURG_PLASTER_SLOTS = (
    "wall_plaster_ochre",
    "wall_plaster_cream",
    "wall_plaster_rose",
    "wall_plaster_warm_white",
)


def distance_to_bourg_reference_m(lat: float, lon: float) -> float:
    east = (lon - HOTEL_DU_BOURG_LON) * M_PER_DEG_LON
    north = (lat - HOTEL_DU_BOURG_LAT) * M_PER_DEG_LAT
    return math.hypot(east, north)


def apply_bourg_reference_style(b: "Building") -> None:
    """Apply a *plausible*, source-informed resort-centre style, not a survey.

    Data-derived shape, altitude and measured/declared roof stay unchanged.
    Explicit wall-material codes take priority over the visual heuristic.
    """
    distance = distance_to_bourg_reference_m(b.lat, b.lon)
    if distance > BOURG_REFERENCE_RADIUS_M:
        return
    if b.area < 45 or b.floors < 2 or b.complex:
        return
    if any(s in (b.nature + " " + b.usage).lower()
           for s in ("industri", "hangar", "agricol", "religieux", "chapelle")):
        return

    b.meta["bourg_reference_area"] = True
    b.meta["bourg_distance_m"] = round(distance, 1)
    b.meta["finish_confidence"] = "illustrative_not_surveyed"

    # Use a restrained warm plaster palette for Bourg. Keep an identified
    # stone/wood/plaster material from the inventory when one is present.
    if not b.wall_code.strip():
        choice = deterministic_int(b.bid + ":bourg_finish") % 100
        if choice < 73:
            b.wall_mat = BOURG_PLASTER_SLOTS[
                deterministic_int(b.bid + ":bourg_plaster") % len(BOURG_PLASTER_SLOTS)
            ]
        elif choice < 90:
            b.wall_mat = "wall_wood_honey"
        else:
            b.wall_mat = "wall_stone"

    # Upper-storey timber facing, common in the architecture, is a visual
    # hypothesis for unknown individual facade details.
    b.meta["bourg_upper_wood"] = (
        not b.wall_code.strip()
        and b.wall_mat.startswith("wall_plaster")
        and b.wall_h >= 6.5
        and deterministic_int(b.bid + ":bourg_upper") % 100 < 65
    )
    if not b.roof_code.strip() and b.rise >= 0.5:
        b.roof_mat = "roof_slate"
