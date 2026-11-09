"""Discover genuine IGN LiDAR-HD MNT/MNS 1km tiles for a circular study area.

Only WFS lookup is automatic; actual 0.5 m GeoTIFF downloads are optional,
resumable and local. No file from a prior scene/package is changed.

WFS layers and bbox semantics follow the public CEREMA LiDAR-HD downloader.
https://data.geopf.fr/wfs
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from urllib.parse import urlparse

import requests
from pyproj import Transformer

from generate import ROOT, load_config

WFS = "https://data.geopf.fr/wfs"
LAYERS = {"mnt": "IGNF_LIDAR-HD_TA:mnt-dalle", "mns": "IGNF_LIDAR-HD_TA:mns-dalle"}
TILE_M = 1000


def tile_grid(center_lon: float, center_lat: float, radius_m: float, buffer_m: float = 25.0):
    """Return only 1km Lambert-93 cells intersecting the actual circle."""
    if radius_m <= 0 or radius_m > 10000:
        raise ValueError("Invalid circular area")
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform(center_lon, center_lat)
    r = radius_m + buffer_m
    cells = []
    ix0 = math.floor((x-r)/TILE_M); ix1 = math.floor((x+r)/TILE_M)
    iy0 = math.floor((y-r)/TILE_M); iy1 = math.floor((y+r)/TILE_M)
    for ix in range(ix0, ix1+1):
        for iy in range(iy0, iy1+1):
            left=ix*TILE_M; bottom=iy*TILE_M
            nearest_x = min(max(x,left),left+TILE_M)
            nearest_y = min(max(y,bottom),bottom+TILE_M)
            if math.hypot(x-nearest_x,y-nearest_y) <= r:
                cells.append((left, bottom))
    return cells


def fetch_tile(layer: str, x: int, y: int, *, session=None, retry_delay: float = 1.0):
    """Fetch one tile URL/name; absence is different from transport failure."""
    if layer not in LAYERS:
        raise ValueError("Unsupported LiDAR product")
    sess = session or requests.Session()
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeName": LAYERS[layer], "outputFormat": "json", "count": 10,
        "bbox": f"{x+1},{y+1},{x+TILE_M-1},{y+TILE_M-1}",
    }
    for attempt in range(3):
        try:
            res = sess.get(WFS, params=params, timeout=65)
            res.raise_for_status()
            doc = res.json()
            if not isinstance(doc, dict) or not isinstance(doc.get("features"), list):
                raise ValueError("IGN WFS returned an unexpected response")
            for ft in doc["features"]:
                props=ft.get("properties") or {}
                url=props.get("url")
                name=props.get("name")
                if url and isinstance(url,str):
                    parsed=urlparse(url)
                    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
                        continue
                    if not name or not isinstance(name,str):
                        name=Path(parsed.path).name
                    if not str(name).lower().endswith((".tif", ".tiff", ".zip")):
                        continue
                    return {"url":url,"name":Path(name).name,"grid":[x,y]}
            return None
        except (requests.RequestException, ValueError) as exc:
            if attempt==2:raise RuntimeError(f"IGN LiDAR WFS unavailable ({layer}, {x}, {y}): {exc}") from exc
            time.sleep(retry_delay*(attempt+1))


def discover(center, radius_m, out: Path, *, session=None, delay:float=.12,
             overwrite:bool=False, max_cells:int=100):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    index_file=out/"index_lidar_hd.json"
    if index_file.is_file() and not overwrite:
        doc=json.loads(index_file.read_text(encoding="utf-8"))
        if (doc.get("radius_m")==radius_m and doc.get("centre_wgs84")==list(center)
                and not any(doc.get("failures",{}).values())):
            for key in LAYERS:
                links=[e["url"] for e in doc["products"].get(key,[]) if e.get("url")]
                (out/f"{key}_urls.txt").write_text("\n".join(links)+"\n" if links else "",encoding="utf-8")
            return doc
    cells=tile_grid(center[0], center[1], radius_m)
    if len(cells)>max_cells:
        raise ValueError(f"LiDAR study area has {len(cells)} cells > {max_cells}")
    products={k:[] for k in LAYERS}
    missing={k:[] for k in LAYERS}
    failures={k:[] for k in LAYERS}
    for layer in LAYERS:
        seen=set()
        consecutive_network_errors=0
        for n,(x,y) in enumerate(cells,1):
            try:
                tile=fetch_tile(layer,x,y,session=session)
            except RuntimeError as exc:
                failures[layer].append({"cell":[x,y],"error":str(exc)})
                consecutive_network_errors+=1
                if consecutive_network_errors>=4:
                    failures[layer].append({"error":"4 consecutive WFS failures: remaining cells not queried"})
                    break
                continue
            consecutive_network_errors=0
            if tile is None:
                missing[layer].append([x,y])
            elif tile["url"] not in seen:
                products[layer].append(tile)
                seen.add(tile["url"])
            if delay:time.sleep(delay)
            if n%15==0:print(f"LiDAR HD {layer}: {n}/{len(cells)} 1km cells consulted",flush=True)
        links=[e["url"] for e in products[layer]]
        (out/f"{layer}_urls.txt").write_text("\n".join(links)+"\n" if links else "",encoding="utf-8")
    result={"centre_wgs84":list(center),"radius_m":radius_m,"cells_tested":len(cells),
            "products":products,"missing":missing,"failures":failures,
            "counts":{k:len(v) for k,v in products.items()},
            "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
            "source":"IGN LiDAR HD WFS, licence ouverte 2.0",
            "status":"URL index only; LiDAR not downloaded or installed in FS2024"}
    index_file.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser(description="Discover official LiDAR HD GeoTIFF MNT/MNS tiles via IGN WFS")
    parser.add_argument("action",choices=["discover","download"],default="discover",nargs="?")
    parser.add_argument("--output",type=Path,default=ROOT/"data"/"lidar")
    parser.add_argument("--refresh",action="store_true")
    a=parser.parse_args()
    cfg=load_config()
    report=discover(cfg["centre_wgs84"],cfg["radius_m"],a.output,overwrite=a.refresh)
    print(json.dumps({"cellules_km2":report["cells_tested"],"dalles_MNT":report["counts"]["mnt"],
                      "dalles_MNS":report["counts"]["mns"],
                      "manquantes":{k:len(v) for k,v in report["missing"].items()},
                      "erreurs_reseau":{k:len(v) for k,v in report["failures"].items()}},ensure_ascii=False,indent=2))
    if a.action=="download":
        from lidar_download import download_list
        for key in LAYERS:
            links=a.output/f"{key}_urls.txt"
            if not links.is_file() or not links.read_text().strip():
                print(f"No LiDAR HD {key} URLs for this scene; skipping.")
                continue
            paths=download_list(links,a.output/key)
            print(f"LiDAR HD {key} downloaded/reused: {len(paths)}")

if __name__=="__main__":main()
