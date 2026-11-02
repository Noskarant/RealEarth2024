"""Download authoritative open geodata for the Valmorel scene.

Sources:
  * IGN BD TOPO v3 via the Geoplateforme WFS (Licence Ouverte 2.0 / Etalab 2.0)
  * IGN ADMINEXPRESS commune boundaries
All raw payloads are stored unchanged under data/raw with a provenance manifest.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(r"D:\RealEarth2024")
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)

WFS = "https://data.geopf.fr/wfs/ows"
# lon_min, lat_min, lon_max, lat_max (EPSG:4326)
BBOX = (6.3900, 45.4120, 6.5000, 45.5050)
BBOX_STR = f"{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]},EPSG:4326"

LAYERS = {
    "batiment": "BDTOPO_V3:batiment",
    "routes": "BDTOPO_V3:troncon_de_route",
    "vegetation": "BDTOPO_V3:zone_de_vegetation",
    "hydro_surface": "BDTOPO_V3:surface_hydrographique",
    "hydro_ligne": "BDTOPO_V3:troncon_hydrographique",
    "constructions_lineaires": "BDTOPO_V3:construction_lineaire",
    "constructions_surfaciques": "BDTOPO_V3:construction_surfacique",
    "constructions_ponctuelles": "BDTOPO_V3:construction_ponctuelle",
    "sports": "BDTOPO_V3:terrain_de_sport",
    "reservoirs": "BDTOPO_V3:reservoir",
    "toponymie": "BDTOPO_V3:toponymie",
    "routes_nommees": "BDTOPO_V3:route_numerotee_ou_nommee",
    "commune": "ADMINEXPRESS-COG-CARTO.LATEST:commune",
}

PAGE = 1000


def fetch_layer(key: str, typename: str) -> dict:
    out = RAW / f"{key}.geojson"
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": typename,
        "SRSNAME": "EPSG:4326",
        "OUTPUTFORMAT": "application/json",
        "COUNT": PAGE,
    }
    if key == "commune":
        params["CQL_FILTER"] = "code_insee='73024'"
    else:
        params["BBOX"] = BBOX_STR

    features = []
    start = 0
    while True:
        params["STARTINDEX"] = start
        for attempt in range(4):
            try:
                r = requests.get(WFS, params=params, timeout=180)
                r.raise_for_status()
                # Decode explicitly: the Geoplateforme does not always send a
                # charset, and requests' fallback mangles the French accents
                # ("Résidentiel" -> "R�sidentiel"), which breaks attribute logic.
                payload = json.loads(r.content.decode("utf-8"))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    raise
                print(f"  retry {key} start={start}: {exc}")
                time.sleep(2 + attempt * 2)
        batch = payload.get("features", [])
        features.extend(batch)
        print(f"  {key}: {len(features)} / {payload.get('totalFeatures', '?')}")
        if len(batch) < PAGE:
            break
        start += PAGE

    fc = {
        "type": "FeatureCollection",
        "name": key,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    return {
        "key": key,
        "typename": typename,
        "path": str(out.relative_to(ROOT)),
        "features": len(features),
        "bytes": out.stat().st_size,
        "url": WFS,
        "bbox": BBOX,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "license": "Licence Ouverte 2.0 (Etalab) - IGN",
    }


def main():
    manifest = []
    for key, typename in LAYERS.items():
        print(f"downloading {key} ({typename})")
        manifest.append(fetch_layer(key, typename))
    (DATA / "sources.json").write_text(json.dumps({
        "dataset": "RealEarth Valmorel HD",
        "bbox_wgs84": BBOX,
        "sources": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
