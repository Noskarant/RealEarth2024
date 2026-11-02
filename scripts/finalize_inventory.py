"""Link every inventoried building to the model that represents it.

Outputs a delivery CSV + summary used by the final report, so each building
can be traced from IGN BD TOPO source data to a compiled model.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

from building_gen import load_buildings
from config import BUILDINGS, CLUSTER_BAND_M, CLUSTER_CELL_M, DOCS

OUT_CSV = DOCS / "valmorel_buildings_delivery.csv"
OUT_SUM = DOCS / "delivery_summary.json"


def main() -> None:
    buildings = load_buildings()
    rows = {r["id"]: r for r in csv.DictReader(
        (BUILDINGS / "buildings_inventory.csv").open(encoding="utf-8-sig"),
        delimiter=";")}

    core_names = {}
    core_i = 0
    for b in buildings:
        if b.core:
            core_names[b.bid] = f"core_{core_i:04d}"
            core_i += 1

    recs = []
    for b in buildings:
        if b.core:
            model = core_names[b.bid]
            level = "detailed_core"
        else:
            ix = math.floor(b.east / CLUSTER_CELL_M)
            iy = math.floor(b.north / CLUSTER_CELL_M)
            ib = math.floor(b.ground / CLUSTER_BAND_M)
            model = f"bld_c{ix}_{iy}_{ib}"
            level = "cluster_massing"
        src = rows.get(b.bid, {})
        recs.append({
            "id": b.bid,
            "lat": f"{b.lat:.8f}",
            "lon": f"{b.lon:.8f}",
            "nature": b.nature,
            "usage": b.usage,
            "area_m2": f"{b.area:.1f}",
            "height_m": f"{b.eave - b.ground:.1f}",
            "wall_material": b.wall_mat,
            "roof_material": b.roof_mat,
            "fidelity": src.get("fidelity", ""),
            "model": model,
            "modelling_level": level,
            "source": "IGN BD TOPO v3 (WFS, Licence Ouverte 2.0)",
        })

    fields = list(recs[0].keys())
    DOCS.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(recs)

    summary = {
        "buildings": len(recs),
        "models": len({r["model"] for r in recs}),
        "by_level": dict(Counter(r["modelling_level"] for r in recs)),
        "by_fidelity": dict(Counter(r["fidelity"] for r in recs)),
        "by_roof": dict(Counter(r["roof_material"] for r in recs)),
        "by_wall": dict(Counter(r["wall_material"] for r in recs)),
        "csv": str(OUT_CSV),
    }
    OUT_SUM.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
