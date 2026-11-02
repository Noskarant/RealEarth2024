"""Fail-closed QA of the real ski resort augmentation before SDK compilation."""
from __future__ import annotations

import json
import math
from pathlib import Path

from config import BUILDINGS, MODEL_SRC

def main() -> None:
    stats = json.loads((BUILDINGS / "models_stats.json").read_text(encoding="utf-8"))
    placements = json.loads((BUILDINGS / "placements.json").read_text(encoding="utf-8"))
    types = int(stats.get("cc0_asset_types", 0))
    chalets = [p for p in placements if p.get("kind") == "cc0_chalet_replacement"]
    props = [p for p in placements if p.get("kind") == "ski_station_prop"]
    if types < 18 or len(chalets) < 8 or len(props) < 12:
        raise RuntimeError("Missing CC0 models/chalets/props in generated scenery")
    lifts = [p for p in placements if p.get("kind", "").startswith("ski_lift_")]
    if stats.get("mapped_lift_objects", 0) != len(lifts):
        raise RuntimeError("Mapped lift object count mismatch")
    if lifts:
        rope = [p for p in lifts if p["kind"] == "ski_lift_cables"]
        towers = [p for p in lifts if p["kind"] == "ski_lift_tower"]
        cabins = [p for p in lifts if p["kind"] == "ski_lift_cabin"]
        if len(rope) != 1 or len(towers) < 5 or len(cabins) < 4:
            raise RuntimeError("Mapped gondola route has incomplete components")
        for suffix in (".gltf", ".xml", ".bin"):
            if not (MODEL_SRC / ("ski_pierrafort_static_cables"+suffix)).is_file():
                raise RuntimeError("Missing mapped Pierrafort rope model")
        if any(p.get("exclude_autogen") is not False for p in lifts):
            raise RuntimeError("Gondola supports must not exclude autogen")

    replaced_ids = [p["building_id"] for p in chalets]
    if len(replaced_ids) != len(set(replaced_ids)):
        raise RuntimeError("Same IGN building replaced twice")
    if any(p.get("exclude_autogen") is not False for p in props):
        raise RuntimeError("Ski props must not clear nearby autogen buildings")
    seen = set()
    for p in chalets + props:
        key = p["model"]
        if not key.startswith("ski_"):
            raise RuntimeError("Unexpected CC0 model key: " + key)
        if key not in seen:
            gltf_path = MODEL_SRC / (key + ".gltf")
            xml_path = MODEL_SRC / (key + ".xml")
            bin_path = MODEL_SRC / (key + ".bin")
            for path in (gltf_path, xml_path, bin_path):
                if not path.is_file() or path.stat().st_size < 50:
                    raise RuntimeError("Missing/empty compiled source: " + str(path))
            gltf = json.loads(gltf_path.read_text(encoding="utf-8"))
            if gltf.get("images") or gltf.get("textures"):
                raise RuntimeError("Unexpected unresolved source textures: " + key)
            if not gltf.get("materials") or not gltf.get("meshes"):
                raise RuntimeError("Model lacks PBR materials: " + key)
            seen.add(key)
        if not (45.44 <= p["lat"] <= 45.50 and 6.40 <= p["lon"] <= 6.48):
            raise RuntimeError("CC0 object outside the validated resort zone")
        if not math.isfinite(float(p["heading"])) or not (0.5 <= p["scale"] <= 2.0):
            raise RuntimeError("Invalid asset heading/scale")
    if len(placements) != stats["placements"]:
        raise RuntimeError("Placements and statistics disagree")
    if not (MODEL_SRC / "texture").is_dir():
        raise RuntimeError("Original Valmorel PNG texture directory missing")
    print("SKI RESORT MODEL QA: OK")
    print("CC0 library models:", types)
    print("Measured IGN building replacements:", len(chalets))
    print("Grounded ski resort props:", len(props))
    print("Mapped Pierrafort lift components:", len(lifts), "(0 means map/elevation validation skipped)")
    print("Active distinct CC0 models:", len(seen))
    print("Note: original buildings/terrain are not overridden by props.")
    print("Note: SDK BGL compilation and in-game appearance are NOT verified here.")

if __name__ == "__main__":
    main()
