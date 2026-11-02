"""Build an isolated one-building SDK texture probe."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from building_gen import add_building, load_buildings
from fsgltf import MeshBuilder, write_gltf
from pack_textures import pack_map

ROOT = Path(r"D:\RealEarth2024\build\texture_probe_official")
MODEL = ROOT / "PackageSources" / "modellib"


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    MODEL.mkdir(parents=True)
    bourg_buildings = [
        b for b in load_buildings()
        if b.core and b.meta.get("bourg_reference_area")
    ]
    if not bourg_buildings:
        raise RuntimeError("No detailed Bourg reference building found in inventory")
    building = min(bourg_buildings, key=lambda b: b.meta["bourg_distance_m"])
    print("Bourg test:", building.bid, building.meta["bourg_distance_m"],
          "m from hotel, finish:", building.wall_mat)
    mesh = MeshBuilder()
    add_building(mesh, building, building.east, building.north, building.ground)
    write_gltf(MODEL, "texture_probe", mesh, pack_map(), use_textures=True)

    texture_dir = MODEL / "texture"
    for png in texture_dir.glob("*.png"):
        png.with_suffix(png.suffix + ".xml").write_text(
            "<BitmapConfiguration>\n"
            "\t<BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot>\n"
            "</BitmapConfiguration>\n", encoding="utf-8")

    (MODEL / "texture_probe.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ModelInfo guid="{ed7cdce1-6bf7-4fea-91a3-55b3110c5a25}" version="1.1">\n'
        '  <LODS><LOD minSize="0" ModelFile="texture_probe.gltf"/></LODS>\n'
        '</ModelInfo>\n', encoding="utf-8")
    package_defs = ROOT / "PackageDefinitions"
    package_defs.mkdir()
    (package_defs / "realearth-texture-probe.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<AssetPackage Version="0.0.1"><ItemSettings>'
        '<ContentType>SCENERY</ContentType><Title>Texture Probe</Title>'
        '<Manufacturer>RealEarth</Manufacturer><Creator>RealEarth2024</Creator>'
        '</ItemSettings><Flags><VisibleInStore>false</VisibleInStore>'
        '<CanBeReferenced>false</CanBeReferenced></Flags>'
        '<PackageOrderHint>CUSTOM_SCENERY_PATCH</PackageOrderHint><AssetGroups>'
        '<AssetGroup Name="probe_modellib"><Type Version="1">ModelLib</Type>'
        '<Flags><FSXCompatibility>false</FSXCompatibility></Flags>'
        '<AssetDir>PackageSources\\modellib\\</AssetDir>'
        '<OutputDir>Scenery\\texture-probe\\modellib\\</OutputDir>'
        '</AssetGroup></AssetGroups></AssetPackage>\n', encoding="utf-8")
    (ROOT / "realearth-texture-probe.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Project Version="2" Name="realearth-texture-probe" FolderName="Packages" MetadataFolderName="PackagesMetadata">'
        '<OutputDirectory>.</OutputDirectory><TemporaryOutputDirectory>_PackageInt</TemporaryOutputDirectory>'
        '<Packages><Package>PackageDefinitions\\realearth-texture-probe.xml</Package></Packages>'
        '<PublishingGroups/></Project>\n',
        encoding="utf-8")
    gltf = json.loads((MODEL / "texture_probe.gltf").read_text(encoding="utf-8"))
    print("probe images:", [i["uri"] for i in gltf.get("images", [])])
    print("sidecars:", len(list(texture_dir.glob("*.png.xml"))))
    if not gltf.get("images"):
        raise RuntimeError("Probe glTF has no PNG texture references")
    for img in gltf["images"]:
        if not (MODEL / img["uri"]).is_file():
            raise RuntimeError("Missing referenced PNG: " + img["uri"])



if __name__ == "__main__":
    main()
