"""MSFS 2024 Polygon writer for detected/OSM buildings and vegetation.

Attribute GUIDs are from the official 2024 SDK Scenery XML Properties.
The writer intentionally does NOT use ExclusionRectangle as a substitute for
procedural building exclusion. It never touches LibraryObject instances.
"""
from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform, triangulate
from pyproj import Transformer

TO_LL = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
ATTRIBUTES = {
    "ExcludeDetectedBuildings": ("{5C1A2387-1F07-47DF-A569-962CF6258E55}", "UINT8"),
    "ExcludeOSMBuildings": ("{F3C2635D-9F2F-458F-8663-90B3837BED09}", "UINT8"),
    "VegetationScale": ("{6A043F59-E6F2-4117-A2E4-D510E7317C29}", "UINT32"),
    "VegetationDensity": ("{41EFF715-C392-4B31-A457-50A504353A90}", "UINT32"),
    "VegetationFalloff": ("{E82ABE17-FB4C-4F67-A28C-ED41969AEAD6}", "FLOAT32"),
    "BiomeName": ("{E5FA1B20-BB2F-40D5-913B-480C547CC9B8}", "STRING"),
}


def add_polygon(root: ET.Element, geometry: Polygon, name: str, attributes: dict):
    """Append precise polygon in EPSG:2154, never rectangles or blanket exclusions."""
    if geometry.is_empty or geometry.area <= 0:
        return None
    if not isinstance(geometry, Polygon):
        raise TypeError("A single Polygon is required; split MultiPolygons first")
    ring = list(geometry.exterior.coords)[:-1]
    if len(ring) < 3 or len(ring) > 65536:
        raise ValueError("Polygon must have between 3 and 65536 vertices")
    tag = ET.SubElement(root, "Polygon", displayName=name[:96])
    for key, val in attributes.items():
        gid, typ = ATTRIBUTES[key]
        ET.SubElement(tag, "Attribute", name=key, guid=gid, type=typ, value=str(val))
    for east, north in ring:
        lon, lat = TO_LL.transform(east, north)
        ET.SubElement(tag, "Vertex", lat=f"{lat:.9f}", lon=f"{lon:.9f}")
    return tag


def exclude_autogen(root: ET.Element, footprint: Polygon, name: str):
    """Exclude detected and OSM procedural houses, not user library objects."""
    return add_polygon(root, footprint, name, {
        "ExcludeDetectedBuildings": 1,
        "ExcludeOSMBuildings": 1,
    })


def add_forest(root: ET.Element, geom: Polygon, name: str,
               density: int = 30, scale: int = 155, falloff: float = 7.0,
               biome: str = "Deciduous_2024"):
    settings={
        "BiomeName": biome,
        "VegetationScale": max(0, min(255, int(scale))),
        "VegetationDensity": max(0, min(62, int(density))),
        "VegetationFalloff": max(0.0, float(falloff)),
    }
    # Polygon XML has no interior rings; triangulate forests with holes so
    # the Madone/church protected buffers remain FREE OF NEW VEGETATION.
    if geom.interiors:
        count=0
        for idx,tri in enumerate(triangulate(geom)):
            if geom.covers(tri) and tri.area>=10:
                add_polygon(root,tri,f'{name} partie {idx}',settings);count+=1
        return count
    add_polygon(root,geom,name,settings)
    return 1
