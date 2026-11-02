"""Shared configuration for the RealEarth Valmorel pipeline."""
from __future__ import annotations

import math
import uuid
from pathlib import Path

ROOT = Path(r"D:\RealEarth2024")
RAW = ROOT / "data" / "raw"
BUILDINGS = ROOT / "buildings"
TEXTURES = ROOT / "textures"
SCRIPTS = ROOT / "scripts"
PROJECT = ROOT / "project"
MODEL_SRC = PROJECT / "PackageSources" / "Scenery" / "valmorel" / "modellib"
SCENERY_SRC = PROJECT / "PackageSources" / "Scenery" / "valmorel" / "scenery"
DIST = ROOT / "dist"
LOGS = ROOT / "logs"
DOCS = ROOT / "docs"

# Local tangent plane origin (WGS84). All scenery is generated in metres
# around this point using a local equirectangular approximation.
LAT0 = 45.461698
LON0 = 6.442483
M_PER_DEG_LAT = 111132.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))

# Scene selection around the Valmorel resort / commune core.
BBOX = (6.3900, 45.4120, 6.5000, 45.5050)

# MSFS glTF axes (documented glTF right-handed, Y-up convention):
#   glTF +X = East, glTF +Y = Up, glTF -Z = North.
# Geometry is authored in a right-handed ENU frame (east, north, up) and
# rotated at export, which preserves triangle winding.
TILE_SIZE_M = 500.0
# Buildings are merged into small clusters that share both a spatial cell and
# an altitude band: a single MSFS object has ONE anchor altitude, so merging
# across a slope would leave buildings floating or buried.
CLUSTER_CELL_M = 100.0
CLUSTER_BAND_M = 2.5
FOUNDATION_DEPTH_M = 4.0
WALL_TEX_M = 4.0
ROOF_TEX_M = 3.0

# Deterministic GUID namespace for models and placements.
GUID_NS = uuid.UUID("6f1b2a44-3c1d-4e7a-9b2f-2b7c7a1d9e01")


def enu_to_gltf(east: float, north: float, up: float):
    """Rotate right-handed ENU into MSFS glTF axes."""
    return (east, up, -north)


def local_to_ll(east: float, north: float):
    return (LAT0 + north / M_PER_DEG_LAT, LON0 + east / M_PER_DEG_LON)


def ll_to_local(lon: float, lat: float):
    return ((lon - LON0) * M_PER_DEG_LON, (lat - LAT0) * M_PER_DEG_LAT)


def deterministic_int(key: str) -> int:
    return int(uuid.uuid5(GUID_NS, key).hex[:8], 16)


def model_guid(name: str) -> str:
    return "{" + str(uuid.uuid5(GUID_NS, "model:" + name)).upper() + "}"


def instance_guid(key: str) -> str:
    return "{" + str(uuid.uuid5(GUID_NS, "inst:" + key)).upper() + "}"
