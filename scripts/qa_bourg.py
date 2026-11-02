"""Fast source and mesh QA for the reference-informed Valmorel Bourg edit.

Runs without the MSFS 2024 SDK. SDK packaging and in-game appearance still
need checking separately on the Windows machine.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from building_gen import add_building, load_buildings
from fsgltf import MeshBuilder, write_gltf
from pack_textures import pack_map


def main() -> None:
    source_pack = pack_map()
    for slot, texture in source_pack.items():
        assert texture.is_file(), f"{slot}: missing {texture}"
    buildings = load_buildings()
    bourg = [b for b in buildings if b.meta.get("bourg_reference_area")]
    detailed = [b for b in bourg if b.core]
    commercial = [b for b in detailed if "commercial" in b.usage.lower()]
    assert bourg, "No candidates found near Hotel du Bourg"
    assert detailed, "No detailed Bourg buildings selected"
    assert commercial, "No inventoried Bourg commerce to test"

    source = min(detailed, key=lambda b: b.meta["bourg_distance_m"])
    print("inventory buildings:", len(buildings))
    print("Bourg reference candidates:", len(bourg),
          "detailed:", len(detailed), "commercial detailed:", len(commercial))
    print("nearest model:", source.bid, source.wall_mat, source.roof_mat)
    with tempfile.TemporaryDirectory(prefix="valmorel_bourg_") as tmp:
        out = Path(tmp)
        for label, building in (("bourg_building", source),
                                ("bourg_commerce", commercial[0])):
            mesh = MeshBuilder()
            add_building(mesh, building, building.east, building.north,
                         building.ground)
            assert mesh.triangle_count() > 0, label
            gltf_path = write_gltf(out, label, mesh, source_pack,
                                   use_textures=True)
            gltf = json.loads(gltf_path.read_text(encoding="utf-8"))
            images = gltf.get("images", [])
            assert images, f"{label}: no textured materials"
            for image in images:
                uri = image["uri"]
                assert uri.startswith("texture/"), (label, uri)
                assert (out / uri).is_file(), (label, uri)
            textures = gltf.get("textures", [])
            assert textures, f"{label}: glTF textures list empty"
            assert any("baseColorTexture" in m["pbrMetallicRoughness"]
                       for m in gltf["materials"]), label
            print(label, "triangles:", mesh.triangle_count(),
                  "referenced PNG:", len(images),
                  "materials:", len(gltf["materials"]))

    print("SOURCE GEOMETRY / PNG REFERENCE QA: OK")
    print("SDK KTX2 compilation and in-game visual checks: NOT RUN")


if __name__ == "__main__":
    main()
