"""Build glTF model library: merged 500 m tiles + individually modelled core."""
from __future__ import annotations

import json
import math
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

from building_gen import add_building, load_buildings
from config import (BUILDINGS, CLUSTER_BAND_M, CLUSTER_CELL_M, MODEL_SRC,
                    local_to_ll, model_guid)
from fsgltf import MeshBuilder, write_gltf
from materials import generate
from pack_textures import pack_map
from ski_assets import build_assets
from ski_placements import prepare_decorations

ROOF_ROUGH = {"roof_slate": 0.72, "roof_metal": 0.38, "roof_tile": 0.82,
              "roof_flat": 0.95, "roof_thatch": 0.9, "stone_base": 0.9}
ROUGH = {"glass": 0.12, "frame": 0.55, "balcony_wood": 0.75, "chimney": 0.9}


def write_model_xml(path: Path, name: str) -> None:
    guid = model_guid(name)
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<ModelInfo guid="{guid}" version="1.1">\n'
        '    <LODS>\n'
        f'        <LOD minSize="0" ModelFile="{name}.gltf"/>\n'
        '    </LODS>\n'
        '</ModelInfo>\n', encoding="utf-8")


def clean_previous() -> None:
    for pat in ("bld_*", "core_*", "ski_*", "valmorel_test_building.*", "test_*.png",
                "*.png"):
        for p in MODEL_SRC.glob(pat):
            if p.is_file():
                p.unlink()
    # No texture assets are shipped: MSFS 2024 only accepts KTX2 produced by
    # its own build step, which does not run here (see fsgltf.write_gltf).
    tex_dir = MODEL_SRC / "texture"
    if tex_dir.is_dir():
        for p in tex_dir.iterdir():
            if p.is_file():
                p.unlink()


def main() -> None:
    MODEL_SRC.mkdir(parents=True, exist_ok=True)
    clean_previous()
    textures = generate()
    pack = pack_map()

    buildings = load_buildings()
    print(f"buildings loaded: {len(buildings)}")

    # Rebuild CC0 assets as standard MSFS-compatible uncompressed glTF.
    assets = build_assets(MODEL_SRC)
    chalet_replacements, ski_props = prepare_decorations(buildings, assets)
    if not chalet_replacements or not ski_props:
        raise RuntimeError("Empty ski augmentation; refusing partial build")

    # One MSFS placement = one rigid object with one anchor altitude.
    # Merge only buildings inside the same 100 m cell AND the same 2.5 m
    # altitude band, so the residual vertical error stays under the
    # foundation depth instead of leaving buildings hanging on the slope.
    clusters: dict[tuple[int, int, int], list] = defaultdict(list)
    core = []
    for b in buildings:
        if b.bid in chalet_replacements:
            # This IGN footprint is replaced by a chalet, not duplicated.
            continue
        if b.core:
            core.append(b)
        else:
            key = (math.floor(b.east / CLUSTER_CELL_M),
                   math.floor(b.north / CLUSTER_CELL_M),
                   math.floor(b.ground / CLUSTER_BAND_M))
            clusters[key].append(b)

    placements = []
    total_tris = 0
    total_models = 0
    tile_report = []
    roughness = dict(ROUGH)
    roughness.update(ROOF_ROUGH)

    for (ix, iy, ib), group in sorted(clusters.items()):
        oe = statistics.fmean(b.east for b in group)
        on = statistics.fmean(b.north for b in group)
        anchor = statistics.median(b.ground for b in group)
        spread = max(b.ground for b in group) - min(b.ground for b in group)
        mesh = MeshBuilder()
        for b in group:
            add_building(mesh, b, oe, on, anchor)
        if mesh.triangle_count() == 0:
            continue
        name = f"bld_c{ix}_{iy}_{ib}"
        write_gltf(MODEL_SRC, name, mesh, pack, roughness=roughness,
                   use_textures=True)
        write_model_xml(MODEL_SRC / f"{name}.xml", name)
        lat, lon = local_to_ll(oe, on)
        xs = [e for b in group for e, _n in b.ring]
        ys = [n for b in group for _e, n in b.ring]
        placements.append({
            "model": name, "guid": model_guid(name), "lat": round(lat, 8),
            "lon": round(lon, 8), "kind": "cluster", "count": len(group),
            "alt": 0.0, "heading": 0.0,
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "ground_spread": round(spread, 2),
        })
        total_tris += mesh.triangle_count()
        total_models += 1
        tile_report.append({"model": name, "buildings": len(group),
                            "triangles": mesh.triangle_count(),
                            "ground_spread": round(spread, 2)})

    for i, b in enumerate(core):
        name = f"core_{i:04d}"
        oe, on = b.east, b.north
        mesh = MeshBuilder()
        add_building(mesh, b, oe, on, b.ground)
        if mesh.triangle_count() == 0:
            continue
        write_gltf(MODEL_SRC, name, mesh, pack, roughness=roughness,
                   use_textures=True)
        write_model_xml(MODEL_SRC / f"{name}.xml", name)
        xs = [e for e, _n in b.ring]
        ys = [n for _e, n in b.ring]
        placements.append({
            "model": name, "guid": model_guid(name),
            "lat": round(b.lat, 8), "lon": round(b.lon, 8),
            "kind": "core", "count": 1, "alt": 0.0, "heading": 0.0,
            "building_id": b.bid,
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "ground_spread": 0.0,
        })
        total_tris += mesh.triangle_count()
        total_models += 1

    # Append accurate IGN footprint replacements and grounded ski props.
    placements.extend(chalet_replacements.values())
    placements.extend(ski_props)
    total_models += len(assets)

    # MSFS 2024 requires a BitmapConfiguration sidecar for every source PNG.
    # Without it the ModelLib builds, but the runtime texture is not emitted.
    texture_dir = MODEL_SRC / "texture"
    source_pngs = sorted(texture_dir.glob("*.png"))
    for png in source_pngs:
        png.with_suffix(png.suffix + ".xml").write_text(
            "<BitmapConfiguration>\n"
            "\t<BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot>\n"
            "</BitmapConfiguration>\n", encoding="utf-8")

    (BUILDINGS / "placements.json").write_text(
        json.dumps(placements, ensure_ascii=False, indent=1), encoding="utf-8")
    stats = {
        "buildings_total": len(buildings),
        "cc0_asset_types": len(assets),
        "cc0_chalet_replacements": len(chalet_replacements),
        "cc0_resort_props": len(ski_props),
        "cc0_import_triangles": sum(asset["triangles"] for asset in assets.values()),
        "core_models": len(core),
        "cluster_models": len(tile_report),
        "tile_models": len(tile_report),
        "models_written": total_models,
        "placements": len(placements),
        "triangles_total": total_tris,
        "cluster_cell_m": CLUSTER_CELL_M,
        "cluster_band_m": CLUSTER_BAND_M,
        "max_ground_spread_m": max((t["ground_spread"] for t in tile_report),
                                   default=0.0),
        "tile_details": tile_report,
    }
    (BUILDINGS / "models_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "tile_details"},
                     ensure_ascii=False, indent=2))
    print("SDK texture sources:", len(source_pngs), "PNG + XML sidecars")


if __name__ == "__main__":
    main()
