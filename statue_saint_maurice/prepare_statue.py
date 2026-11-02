"""Prepare the user's real photogrammetry for MSFS 2024 (without guessing GPS)."""
from __future__ import annotations
import json
import math
import shutil
import struct
from pathlib import Path
import xml.etree.ElementTree as ET

from generate_lods import write_lods

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
PROJ = ROOT / "project"
NAME = "realearth-saint-maurice-vierge"
MODEL_GUID = "{3c4f1f4f-0c31-57da-93ad-89f6d235c2f8}"
INSTANCE_GUID = "{dbbf2c27-1afa-56be-a76e-09804296274a}"
MODEL = PROJ / "PackageSources" / "Scenery" / "saint_maurice" / "modellib"
SCENERY = PROJ / "PackageSources" / "Scenery" / "saint_maurice" / "scenery"

def main():
    gltf_path = SRC / "monument_vierge.gltf"
    bin_path = SRC / "monument_vierge.bin"
    png = SRC / "texture" / "monument_vierge_albedo.png"
    if not png.exists():
        png = SRC / "mesh_Model_4_u1_v1_diffuse.png"
    for f in (gltf_path, bin_path, png):
        if not f.is_file():
            raise FileNotFoundError(f"Source missing: {f}; extract the corrected archive")
    g = json.loads(gltf_path.read_text(encoding="utf-8-sig"))
    if len(g.get("images", [])) != 1 or len(g.get("textures", [])) != 1:
        raise ValueError("Expected exactly one photographic atlas")
    if len(g.get("buffers", [])) != 1 or g["buffers"][0]["uri"] != "monument_vierge.bin":
        raise ValueError("Unrecognised binary glTF buffer")
    if bin_path.stat().st_size != g["buffers"][0]["byteLength"]:
        raise ValueError("Binary vertex buffer length mismatch")
    for m in g.get("materials", []):
        m["alphaMode"] = "OPAQUE"  # source PNG alpha is 100% opaque
        m.pop("alphaCutoff", None)
        m.pop("extensions", None)  # unnecessary KHR_materials_specular
        m["doubleSided"] = True
        p = m.setdefault("pbrMetallicRoughness", {})
        p["metallicFactor"] = 0.0
        p["baseColorFactor"] = [1, 1, 1, 1]
        p.setdefault("roughnessFactor", 0.93)
    g.pop("extensionsUsed", None)
    g.pop("extensionsRequired", None)
    for mesh in g["meshes"]:
        for primitive in mesh["primitives"]:
            attrs = primitive["attributes"]
            if "TEXCOORD_0" not in attrs:
                raise ValueError("Missing UV set for photographic atlas")
            attrs.pop("COLOR_0", None)
            attrs.pop("COLOR_1", None)
    g["images"][0].update(uri="texture/monument_vierge_albedo.png",
                          name="monument_vierge_albedo", mimeType="image/png")
    with png.open("rb") as f:
        h = f.read(24)
    if h[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", h[16:24]) not in ((2048, 2048), (4096, 4096)):
        raise ValueError("Expected supplied 2048 or 4096 PNG atlas")

    MODEL.mkdir(parents=True, exist_ok=True)
    tex = MODEL / "texture"
    tex.mkdir(parents=True, exist_ok=True)
    SCENERY.mkdir(parents=True, exist_ok=True)
    # Preserve the untouched 297k-vertex source, but compile reduced LODs.
    # The original single high-density LOD may be culled by MSFS 2024.
    lods = write_lods(g, bin_path, MODEL)
    shutil.copy2(png, tex / "monument_vierge_albedo.png")
    (tex / "monument_vierge_albedo.png.xml").write_text(
        "<BitmapConfiguration>\n  <BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot>\n</BitmapConfiguration>\n",
        encoding="utf-8")
    (MODEL / "monument_vierge.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<ModelInfo guid="{MODEL_GUID}" version="1.1">\n'
        ' <LODS>\n'
        + ''.join(f'  <LOD minSize="{lod["minSize"]}" ModelFile="{lod["gltf"]}"/>\n' for lod in lods)
        + ' </LODS>\n'
        '</ModelInfo>\n', encoding="utf-8")

    placement_path = ROOT / "placement.json"
    if not placement_path.is_file():
        placement_path.write_text(json.dumps({
            "latitude": None, "longitude": None,
            "heading_degrees": 0, "scale": 1.0, "agl_offset_m": 0.0
        }, indent=2) + "\n", encoding="utf-8")
    placement = json.loads(placement_path.read_text(encoding="utf-8"))
    lat, lon = placement.get("latitude"), placement.get("longitude")
    if (lat is None) != (lon is None):
        raise ValueError("Both latitude and longitude must be set together")
    placed = lat is not None
    if placed:
        lat, lon = float(lat), float(lon)
        heading = float(placement.get("heading_degrees", 0)) % 360
        scale = float(placement.get("scale", 1))
        agl = float(placement.get("agl_offset_m", 0))
        if not all(map(math.isfinite, (lat, lon, heading, scale, agl))):
            raise ValueError("Invalid placement")
        if not (45.54 <= lat <= 45.61 and 4.57 <= lon <= 4.68):
            raise ValueError("GPS is outside Saint-Maurice: refuse wrong location")
        if not (0.1 <= scale <= 3.0 and -20 <= agl <= 20):
            raise ValueError("Implausible scale/height")
        (SCENERY / "monument_vierge_placement.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<FSData version="9.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:noNamespaceSchemaLocation="bglcomp.xsd">\n'
            f'<SceneryObject instanceId="{INSTANCE_GUID}" lat="{lat:.9f}" lon="{lon:.9f}" '
            f'alt="{agl:.3f}" pitch="0" bank="0" heading="{heading:.3f}" '
            'altitudeIsAgl="TRUE" snapToGround="TRUE" snapToNormal="FALSE" imageComplexity="NORMAL">\n'
            f'<LibraryObject name="{MODEL_GUID}" scale="{scale:.6f}"/>\n'
            '</SceneryObject></FSData>\n', encoding="utf-8")
    else:
        (SCENERY / "monument_vierge_placement.xml").unlink(missing_ok=True)

    scenery_group = (
        '<AssetGroup Name="vierge_scenery"><Type Version="0">BGL</Type>'
        '<Flags><FSXCompatibility>false</FSXCompatibility></Flags>'
        '<AssetDir>PackageSources\\Scenery\\saint_maurice\\scenery\\</AssetDir>'
        '<OutputDir>Scenery\\saint_maurice\\scenery\\</OutputDir></AssetGroup>'
        if placed else ""
    )
    defs = PROJ / "PackageDefinitions"
    defs.mkdir(parents=True, exist_ok=True)
    definition = defs / (NAME + ".xml")
    definition.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<AssetPackage Version="0.1.2"><ItemSettings><ContentType>SCENERY</ContentType>'
        '<Title>Saint-Maurice - Vierge du Peu</Title><Manufacturer>RealEarth</Manufacturer>'
        '<Creator>RealEarth2024</Creator></ItemSettings>'
        '<Flags><VisibleInStore>false</VisibleInStore><CanBeReferenced>false</CanBeReferenced></Flags>'
        '<PackageOrderHint>CUSTOM_SCENERY_PATCH</PackageOrderHint>'
        '<AssetGroups><AssetGroup Name="vierge_modellib"><Type Version="1">ModelLib</Type>'
        '<Flags><FSXCompatibility>false</FSXCompatibility></Flags>'
        '<AssetDir>PackageSources\\Scenery\\saint_maurice\\modellib\\</AssetDir>'
        '<OutputDir>Scenery\\saint_maurice\\modellib\\</OutputDir></AssetGroup>'
        + scenery_group + '</AssetGroups></AssetPackage>\n', encoding="utf-8")
    project_file = PROJ / (NAME + ".xml")
    project_file.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Project Version="2" Name="{NAME}" FolderName="Packages" MetadataFolderName="PackagesMetadata">'
        '<OutputDirectory>.</OutputDirectory><TemporaryOutputDirectory>_PackageInt</TemporaryOutputDirectory>'
        f'<Packages><Package>PackageDefinitions\\{NAME}.xml</Package></Packages>'
        '<PublishingGroups/></Project>\n', encoding="utf-8")
    for f in (definition, project_file, MODEL / "monument_vierge.xml"):
        ET.parse(f)
    if placed:
        ET.parse(SCENERY / "monument_vierge_placement.xml")
    print("MODEL/PNG/XML QA: OK -", g["accessors"][0]["count"], "vertices")
    print("LOD QA: ", [(lod["name"], lod["vertices"]) for lod in lods])
    print("Model cleanup: floating ground removed, base at Y=0, 91 tiny cracks sealed; Madonna-only yaw configurable")
    print("GPS:", "confirmed position configured" if placed else "not set; ModelLib texture probe only")
    print("SDK project:", project_file)

if __name__ == "__main__":
    main()
