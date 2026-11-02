"""Build the georeferenced building inventory from IGN BD TOPO."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

ROOT = Path(r"D:\RealEarth2024")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "buildings"
OUT.mkdir(parents=True, exist_ok=True)

TO_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
TO_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
LAT0, LON0 = 45.461698, 6.442483
M_LAT = 111132.0
M_LON = 111320.0 * math.cos(math.radians(LAT0))


def ring_area(ring):
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def poly_parts(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []


def local_xy(lon, lat):
    return ((lat - LAT0) * M_LAT, (lon - LON0) * M_LON)


def main():
    fc = json.loads((RAW / "batiment.geojson").read_text(encoding="utf-8"))
    rows = []
    geo_features = []
    stats = Counter()
    for f in fc["features"]:
        p = f["properties"]
        geom = shape(f["geometry"])
        parts = poly_parts(geom)
        if not parts:
            stats["invalid_geometry"] += 1
            continue
        # keep the largest part (BD TOPO multipart buildings are rare)
        poly = max(parts, key=lambda g: g.area)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.is_empty:
                stats["invalid_geometry"] += 1
                continue
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        poly_m = transform(TO_L93.transform, poly)
        area = poly_m.area
        if area < 4.0:
            stats["too_small"] += 1
            continue
        ll = poly
        cx, cy = poly_m.centroid.x, poly_m.centroid.y
        lon, lat = TO_WGS.transform(cx, cy)
        x, z = local_xy(lon, lat)

        # footprint ground altitudes from BD TOPO 3D rings (Z in IGN69)
        ring = list(poly.exterior.coords)
        zs = [c[2] for c in ring if len(c) > 2 and c[2] is not None]
        ground_min = min(zs) if zs else p.get("altitude_minimale_sol")
        ground_max = max(zs) if zs else p.get("altitude_maximale_sol")
        eave = p.get("altitude_minimale_toit")
        ridge = p.get("altitude_maximale_toit")
        hauteur = p.get("hauteur")

        if eave is None and ridge is not None and hauteur is not None:
            eave = ridge - hauteur
        if ridge is None and eave is not None and hauteur is not None:
            ridge = eave + hauteur
        if ridge is None and ground_min is not None and hauteur is not None:
            ridge = ground_min + hauteur
        if eave is None and ridge is not None:
            eave = ridge - 1.0
        if eave is None:
            eave = (ground_min or 0) + 3.0
        if ridge is None:
            ridge = eave + 1.0

        rise = max(0.0, ridge - eave)
        wall_h = eave - (ground_min if ground_min is not None else eave - 3.0)
        if wall_h <= 0.5:
            wall_h = hauteur if hauteur and hauteur > 0.5 else 3.0
            eave = (ground_min or 0) + wall_h
            ridge = max(ridge, eave + 1.0)

        rect = poly_m.minimum_rotated_rectangle
        if rect.geom_type == "Polygon" and len(rect.exterior.coords) >= 4:
            rc = list(rect.exterior.coords)
            d1 = math.dist(rc[0][:2], rc[1][:2])
            d2 = math.dist(rc[1][:2], rc[2][:2])
            length = max(d1, d2)
            width = min(d1, d2)
            ang = math.degrees(math.atan2(rc[1][1] - rc[0][1], rc[1][0] - rc[0][0]))
            if d2 > d1:
                ang += 90.0
            ang = ang % 180.0
        else:
            length = width = math.sqrt(area)
            ang = 0.0

        materials_wall = (p.get("materiaux_des_murs") or "").strip() or "Inconnu"
        materials_roof = (p.get("materiaux_de_la_toiture") or "").strip() or "Inconnu"
        nature = (p.get("nature") or "Indifférenciée").strip()
        usage = (p.get("usage_1") or "Indifférencié").strip()
        floors = p.get("nombre_d_etages")
        dwellings = p.get("nombre_de_logements")

        # Fidelity category (honest, data-driven)
        has_3d = bool(zs) and ridge is not None and ground_min is not None
        plausible = (ridge - ground_min) > 2.0 and area > 8.0 and rise < 40
        if has_3d and plausible:
            category = "B"
        elif plausible:
            category = "C"
        else:
            category = "D"
        stats[f"cat_{category}"] += 1

        props = {
            "id": p.get("cleabs") or f.get("id"),
            "name": "",
            "nature": nature,
            "usage": usage,
            "usage2": p.get("usage_2") or "",
            "lat": round(lat, 8),
            "lon": round(lon, 8),
            "local_x_north_m": round(x, 3),
            "local_z_east_m": round(z, 3),
            "ground_min_m": round(ground_min, 2) if ground_min is not None else "",
            "ground_max_m": round(ground_max, 2) if ground_max is not None else "",
            "eave_m": round(eave, 2),
            "ridge_m": round(ridge, 2),
            "height_m": round(ridge - ground_min, 2) if ground_min is not None else "",
            "wall_height_m": round(wall_h, 2),
            "roof_rise_m": round(rise, 2),
            "roof_type": "flat" if rise < 0.35 else ("gable" if length / max(width, 0.1) >= 1.45 else "hip"),
            "floors": floors if floors is not None else "",
            "dwellings": dwellings if dwellings is not None else "",
            "area_m2": round(area, 2),
            "perimeter_m": round(poly_m.length, 2),
            "length_m": round(length, 2),
            "width_m": round(width, 2),
            "orientation_deg": round(ang, 1),
            "wall_material": materials_wall,
            "roof_material": materials_roof,
            "light_structure": bool(p.get("construction_legere")),
            "state": p.get("etat_de_l_objet") or "",
            "source": "IGN BD TOPO v3 (WFS)",
            "source_id": p.get("cleabs") or "",
            "source_date": p.get("date_modification") or "",
            "fidelity": category,
            "real_name_available": False,
        }
        rows.append(props)
        geo_features.append({
            "type": "Feature",
            "geometry": mapping(ll),
            "properties": props,
        })

    fields = list(rows[0].keys())
    with (OUT / "buildings_inventory.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    (OUT / "buildings_inventory.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": geo_features,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    }, ensure_ascii=False), encoding="utf-8")

    summary = {
        "count": len(rows),
        "categories": {k: v for k, v in stats.items()},
        "nature": dict(Counter(r["nature"] for r in rows).most_common()),
        "usage": dict(Counter(r["usage"] for r in rows).most_common()),
        "wall_materials": dict(Counter(r["wall_material"] for r in rows).most_common()),
        "roof_materials": dict(Counter(r["roof_material"] for r in rows).most_common()),
        "roof_types": dict(Counter(r["roof_type"] for r in rows).most_common()),
        "height_min": min(r["height_m"] for r in rows if r["height_m"] != ""),
        "height_max": max(r["height_m"] for r in rows if r["height_m"] != ""),
        "height_median": sorted(r["height_m"] for r in rows if r["height_m"] != "")[len(rows) // 2],
        "floors_known": sum(1 for r in rows if r["floors"] != ""),
        "area_total_m2": round(sum(r["area_m2"] for r in rows), 1),
    }
    (OUT / "inventory_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

