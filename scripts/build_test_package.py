"""Build a minimal but real FS2024 package to validate the toolchain."""
from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

import sys
sys.path.insert(0, str(Path(__file__).parent))
from fsgltf import MeshBuilder, write_gltf

ROOT = Path(r"D:\RealEarth2024")
PROJ = ROOT / "project"
LAT0, LON0 = 45.461698, 6.442483
M_PER_DEG_LAT = 111132.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))

MODEL_GUID = "{6F1B2A44-3C1D-4E7A-9B2F-2B7C7A1D9E01}"


def make_texture(path: Path, base, accent, kind):
    img = Image.new("RGB", (256, 256), base)
    d = ImageDraw.Draw(img)
    if kind == "wood":
        for y in range(0, 256, 16):
            d.rectangle([0, y, 255, y + 7], fill=accent)
            d.line([0, y + 8, 255, y + 8], fill=(70, 45, 25))
    elif kind == "roof":
        for y in range(0, 256, 24):
            for x in range(-24, 256, 48):
                d.rectangle([x + (24 if (y // 24) % 2 else 0), y, x + 46 + (24 if (y // 24) % 2 else 0), y + 22], fill=accent)
    else:
        for y in range(0, 256, 8):
            d.line([0, y, 255, y], fill=accent)
    img.save(path)


def tex(name, base, accent, kind):
    p = PROJ / "PackageSources" / "Scenery" / "valmorel" / "modellib" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    make_texture(p, base, accent, kind)
    return p


def main():
    modellib = PROJ / "PackageSources" / "Scenery" / "valmorel" / "modellib"
    scenery = PROJ / "PackageSources" / "Scenery" / "valmorel" / "scenery"
    pkgdef = PROJ / "PackageDefinitions"
    content = pkgdef / "realearth-valmorel-hd" / "ContentInfo"
    for d in (modellib, scenery, pkgdef, content):
        d.mkdir(parents=True, exist_ok=True)

    wood = tex("test_wood.png", (120, 78, 48), (146, 98, 60), "wood")
    roof = tex("test_roof.png", (88, 42, 34), (112, 55, 44), "roof")
    plaster = tex("test_plaster.png", (232, 226, 212), (222, 214, 198), "plaster")

    mesh = MeshBuilder()
    # 18 m (N-S) x 11 m (E-W), walls 6 m, gable roof +3.5 m
    nx, nz = 18.0, 11.0
    h = 6.0
    # footprint corners (x=north, z=east), origin at building centre
    pts = [(-nx / 2, -nz / 2), (nx / 2, -nz / 2), (nx / 2, nz / 2), (-nx / 2, nz / 2)]
    for i in range(4):
        a = pts[i]
        b = pts[(i + 1) % 4]
        mesh.add_quad("wood", (a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], h, b[1]), (a[0], h, a[1]))
    # gable roof, ridge along X (north-south)
    ridge = 3.5
    e0 = (0, h, -nz / 2)
    e1 = (0, h, nz / 2)
    r0 = (0, h + ridge, 0)
    # south slope
    mesh.add_quad("roof", (-nx / 2, h, -nz / 2), (nx / 2, h, -nz / 2), (nx / 2, h + ridge, 0), (-nx / 2, h + ridge, 0))
    # north slope
    mesh.add_quad("roof", (nx / 2, h, nz / 2), (-nx / 2, h, nz / 2), (-nx / 2, h + ridge, 0), (nx / 2, h + ridge, 0))
    # gable ends
    mesh.add_triangle("plaster", (-nx / 2, h, -nz / 2), (-nx / 2, h, nz / 2), (-nx / 2, h + ridge, 0))
    mesh.add_triangle("plaster", (nx / 2, h, nz / 2), (nx / 2, h, -nz / 2), (nx / 2, h + ridge, 0))
    # windows (simple recessed dark quads on west/east facades) - symbolic for the test
    for k in range(3):
        z = -nz / 2 + 2.5 + k * 3.0
        for side in (-1, 1):
            x = side * (nx / 2 + 0.02)
            mesh.add_quad("plaster", (x, 1.2, z - 0.6), (x, 1.2, z + 0.6), (x, 2.4, z + 0.6), (x, 2.4, z - 0.6))

    gltf_path = write_gltf(modellib, "valmorel_test_building", mesh,
                           {"wood": wood, "roof": roof, "plaster": plaster},
                           base_color_factors={"wood": [1, 1, 1, 1], "roof": [1, 1, 1, 1],
                                               "plaster": [1, 1, 1, 1]},
                           roughness={"wood": 0.85, "roof": 0.9, "plaster": 0.95})
    print("wrote", gltf_path, "tris", mesh.triangle_count())

    model_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<ModelInfo guid="{MODEL_GUID}" version="1.1">
    <LODS>
        <LOD minSize="0" ModelFile="valmorel_test_building.gltf"/>
    </LODS>
</ModelInfo>
'''
    (modellib / "valmorel_test_building.xml").write_text(model_xml, encoding="utf-8")

    # Local offset of the test building: 60 m north, 20 m east of Valmorel centre
    lat = LAT0 + 60.0 / M_PER_DEG_LAT
    lon = LON0 + 20.0 / M_PER_DEG_LON
    scene_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<FSData version="9.0">
    <SceneryObject lat="{lat:.9f}" lon="{lon:.9f}" alt="0.000000" pitch="0.000000" bank="0.000000" heading="0.000000" altitudeIsAgl="TRUE" snapToGround="TRUE" snapToNormal="FALSE">
        <LibraryObject name="{MODEL_GUID}" scale="1.000000"/>
    </SceneryObject>
</FSData>
'''
    (scenery / "valmorel_test_scenery.xml").write_text(scene_xml, encoding="utf-8")

    # ContentInfo thumbnail
    img = Image.new("RGB", (512, 512), (30, 46, 60))
    d = ImageDraw.Draw(img)
    d.text((24, 24), "RealEarth\nValmorel HD", fill=(255, 255, 255))
    img.save(content / "thumbnail.jpg", quality=92)

    pkg = f'''<?xml version="1.0" encoding="utf-8"?>
<AssetPackage Version="0.1.0">
    <ItemSettings>
        <ContentType>SCENERY</ContentType>
        <Title>RealEarth Valmorel HD</Title>
        <Manufacturer>RealEarth</Manufacturer>
        <Creator>RealEarth2024</Creator>
    </ItemSettings>
    <Flags>
        <VisibleInStore>false</VisibleInStore>
        <CanBeReferenced>false</CanBeReferenced>
    </Flags>
    <PackageOrderHint>CUSTOM_SCENERY_PATCH</PackageOrderHint>
    <AssetGroups>
        <AssetGroup Name="ContentInfo">
            <Type Version="0">ContentInfo</Type>
            <Flags><FSXCompatibility>false</FSXCompatibility></Flags>
            <AssetDir>PackageDefinitions\\realearth-valmorel-hd\\ContentInfo\\</AssetDir>
            <OutputDir>ContentInfo\\realearth-valmorel-hd\\</OutputDir>
        </AssetGroup>
        <AssetGroup Name="valmorel_modellib">
            <Type Version="1">ModelLib</Type>
            <Flags><FSXCompatibility>false</FSXCompatibility></Flags>
            <AssetDir>PackageSources\\Scenery\\valmorel\\modellib\\</AssetDir>
            <OutputDir>Scenery\\valmorel\\modellib\\</OutputDir>
        </AssetGroup>
        <AssetGroup Name="valmorel_scenery">
            <Type Version="0">BGL</Type>
            <Flags><FSXCompatibility>false</FSXCompatibility></Flags>
            <AssetDir>PackageSources\\Scenery\\valmorel\\scenery\\</AssetDir>
            <OutputDir>Scenery\\valmorel\\scenery\\</OutputDir>
        </AssetGroup>
    </AssetGroups>
</AssetPackage>
'''
    (pkgdef / "realearth-valmorel-hd.xml").write_text(pkg, encoding="utf-8")

    proj = f'''<?xml version="1.0" encoding="utf-8"?>
<Project Version="2" Name="realearth-valmorel-hd" FolderName="Packages" MetadataFolderName="PackagesMetadata">
    <OutputDirectory>.</OutputDirectory>
    <TemporaryOutputDirectory>_PackageInt</TemporaryOutputDirectory>
    <Packages>
        <Package>PackageDefinitions\\realearth-valmorel-hd.xml</Package>
    </Packages>
    <PublishingGroups/>
</Project>
'''
    (PROJ / "realearth-valmorel-hd.xml").write_text(proj, encoding="utf-8")
    print("package definition written")


if __name__ == "__main__":
    main()
