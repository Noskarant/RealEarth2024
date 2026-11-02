"""Optional, data-grounded static Pierrafort gondola line.

Never create a fantasy lift route: require a real OSM aerialway geometry
near independently published Pierrafort endpoints and IGN terrain
elevations. Support locations along the mapped centreline are interpolated
for visualisation and are NOT surveyed tower coordinates.

ODbL OpenStreetMap contributors; IGN RGE ALTI (open public service).
"""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from config import ROOT, ll_to_local, local_to_ll, enu_to_gltf, model_guid
from fsgltf import MeshBuilder, write_gltf

CACHE = ROOT / "build" / "ski_lift_routes"
CABLE_KEY = "ski_pierrafort_static_cables"
# Lower stop: Valmorel Tourism listing.
BOTTOM_REFERENCE = (45.458987, 6.44331)
# Top stop: Valmorel Tourism / Roche Blanche route (1,835m).
TOP_REFERENCE = (45.442458, 6.44112)
BBOX = (45.437, 6.425, 45.466, 6.46)


def distance(a, b) -> float:
    return math.hypot((a[0] - b[0])*111132, (a[1] - b[1])*78100)


OVERPASS_SERVERS = (
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
)


def _fetch_osm_lifts() -> dict:
    """Try multiple current OSM mirrors; a transient 502 is not bad data."""
    query = ('[out:json][timeout:35];'
             'way["aerialway"~"^(gondola|chair_lift|mixed_lift)$"]'
             f'({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});out geom;')
    failures = []
    for endpoint in OVERPASS_SERVERS:
        for attempt in range(2):
            try:
                # Small, rate-limited query; do not retry forever or
                # treat HTTP 502/429/504 as evidence that a lift is absent.
                body = urllib.parse.urlencode({"data": query}).encode("utf-8")
                request = urllib.request.Request(
                    endpoint, data=body,
                    headers={
                        "User-Agent": "RealEarth2024 MSFS scenery (OSM/ODbL)",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=32) as response:
                    content = response.read(2_000_001)
                if len(content) > 2_000_000:
                    raise ValueError("Overpass returned an oversized payload")
                obj = json.loads(content)
                if not isinstance(obj, dict) or not isinstance(obj.get("elements"), list):
                    raise ValueError("Overpass returned an invalid JSON schema")
                print("Overpass OK:", endpoint, len(obj["elements"]), "mapped ways")
                return obj
            except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                    ValueError, TimeoutError) as exc:
                failures.append(f"{endpoint}: {type(exc).__name__} {exc}")
                if attempt == 0:
                    time.sleep(1.5)
    raise RuntimeError(
        "All Overpass mirrors failed: " + " | ".join(failures[-3:])
    )


def osm_route() -> list[tuple[float, float]]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / "pierrafort_osm.json"
    if cached.is_file():
        try:
            payload = json.loads(cached.read_text(encoding="utf-8"))
            if not isinstance(payload.get("elements"), list):
                raise ValueError("Cached route schema invalid")
        except (OSError, ValueError, AttributeError):
            cached.unlink(missing_ok=True)
            payload = _fetch_osm_lifts()
    else:
        payload = _fetch_osm_lifts()

    routes = []
    for w in payload.get("elements", []):
        geom = w.get("geometry") or []
        if w.get("type") != "way" or len(geom) < 2:
            continue
        pts = [(float(p["lat"]), float(p["lon"])) for p in geom]
        ends = (pts[0], pts[-1])
        bottom_d = min(distance(e, BOTTOM_REFERENCE) for e in ends)
        top_d = min(distance(e, TOP_REFERENCE) for e in ends)
        if bottom_d > 420 or top_d > 420:
            continue
        name = str((w.get("tags") or {}).get("name", "")).casefold()
        ptslen = sum(distance(a, b) for a, b in zip(pts, pts[1:]))
        if not (1200 <= ptslen <= 2800):
            continue
        rank = (0 if "pierrafort" in name else 1,
                bottom_d + top_d)
        routes.append((rank, pts, w.get("id"), name))
    if not routes:
        raise ValueError("OSM has no aerialway matching BOTH Pierrafort endpoints")
    routes.sort(key=lambda item: item[0])
    pts = routes[0][1]
    if distance(pts[-1], BOTTOM_REFERENCE) < distance(pts[0], BOTTOM_REFERENCE):
        pts = list(reversed(pts))
    # Cache only confirmed route data, never an erroneous service response.
    if not cached.is_file():
        cached.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("Verified OSM Pierrafort route:", routes[0][2],
          routes[0][3], len(pts), "geometry vertices")
    return pts


def resample(route: list[tuple[float, float]], count: int = 65):
    coords = [ll_to_local(p[1], p[0]) for p in route]
    cumulative = [0.]
    for (x0,y0), (x1,y1) in zip(coords, coords[1:]):
        cumulative.append(cumulative[-1] + math.hypot(x1-x0,y1-y0))
    length = cumulative[-1]
    if length < 1200 or length > 2800:
        raise ValueError("Invalid ski lift line length")
    result = []
    seg = 0
    for i in range(count):
        target = i * length / (count - 1)
        while seg + 1 < len(cumulative)-1 and cumulative[seg+1] < target:
            seg += 1
        interval = cumulative[seg+1] - cumulative[seg]
        q = 0 if interval < 1e-8 else (target - cumulative[seg])/interval
        e = coords[seg][0]*(1-q) + coords[seg+1][0]*q
        n = coords[seg][1]*(1-q) + coords[seg+1][1]*q
        lat, lon = local_to_ll(e,n)
        result.append((e,n,lat,lon))
    return result


def ign_elevations(samples: list[tuple[float, float, float, float]]):
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / "pierrafort_ign_alti.json"
    if cache.is_file():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if payload.get("points") == [[round(p[2], 7), round(p[3], 7)]
                                      for p in samples]:
            elevations = payload["elevations"]
            if len(elevations) == len(samples):
                return [float(z) for z in elevations]

    params = {
        "lon": "|".join(f"{p[3]:.7f}" for p in samples),
        "lat": "|".join(f"{p[2]:.7f}" for p in samples),
        "resource": "ign_rge_alti_wld", "delimiter": "|",
        "indent": "false", "zonly": "true", "measures": "false",
    }
    url = ("https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?"+
           urllib.parse.urlencode(params))
    request = urllib.request.Request(url, headers={
        "User-Agent": "RealEarth2024/0.1.5 (IGN terrain altitudes)"
    })
    with urllib.request.urlopen(request, timeout=55) as r:
        response = json.loads(r.read(180_000))
    elev = response.get("elevations", [])
    if len(elev) != len(samples):
        raise ValueError("IGN elevations do not match requested positions")
    z = [float(x) for x in elev]
    if not all(math.isfinite(x) and 900 < x < 2600 for x in z):
        raise ValueError("IGN returned invalid elevation for gondola line")
    if not 180 <= z[-1] - z[0] <= 900:
        raise ValueError("Lift terrain height rise is implausible")
    cache.write_text(json.dumps({
        "resource": "ign_rge_alti_wld",
        "points": [[round(p[2],7),round(p[3],7)] for p in samples],
        "elevations": z,
    }), encoding="utf-8")
    return z


def cable_model(samples, elevations, model_dir: Path):
    """Two narrow, visible non-animated rope cables ~9m above IGN terrain."""
    mesh = MeshBuilder()
    first_e, first_n = samples[0][:2]
    first_z = elevations[0]
    line = [(s[0],s[1],float(z)) for s,z in zip(samples,elevations)]
    offset = 1.6
    thickness = 0.027
    # Place two cables 3.2m apart, with a four-sided section for visibility.
    for direction in (-1,1):
        for idx in range(len(line)-1):
            a,b = line[idx],line[idx+1]
            dx,dy = b[0]-a[0],b[1]-a[1]
            leng = math.hypot(dx,dy)
            if leng <= .1:
                continue
            pe,pn = -dy/leng,dx/leng
            off = direction*offset
            def ring(point):
                e,n,z = point
                e += pe*off
                n += pn*off
                alt = (z-first_z) + 9.0
                return (
                    enu_to_gltf(e-first_e+pe*thickness,n-first_n+pn*thickness,alt),
                    enu_to_gltf(e-first_e-pe*thickness,n-first_n-pn*thickness,alt),
                    enu_to_gltf(e-first_e,n-first_n,alt+thickness),
                    enu_to_gltf(e-first_e,n-first_n,alt-thickness),
                )
            ring_a,ring_b = ring(a),ring(b)
            for k,j in ((0,2),(2,1),(1,3),(3,0)):
                mesh.add_quad("ski_lift_cable_steel",ring_a[k],ring_a[j],
                              ring_b[j],ring_b[k])
    if not 200 <= mesh.triangle_count() <= 3000:
        raise ValueError("Cable geometry budget invalid")
    write_gltf(model_dir,CABLE_KEY,mesh,{},
               base_color_factors={"ski_lift_cable_steel":[.18,.20,.22,1]},
               metallic={"ski_lift_cable_steel":.70},
               roughness={"ski_lift_cable_steel":.45},
               use_textures=False)
    (model_dir / f"{CABLE_KEY}.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<ModelInfo guid="{model_guid(CABLE_KEY)}" version="1.1">'
        f'<LODS><LOD minSize="0" ModelFile="{CABLE_KEY}.gltf"/></LODS>'
        '</ModelInfo>\n',encoding="utf-8")


def build_pierrafort(model_dir: Path, assets: dict[str, dict]) -> list[dict]:
    route = osm_route()
    samples = resample(route)
    elevations = ign_elevations(samples)
    required = ["Gondola Tower", "Gondola Cabin"]
    if any(k not in assets for k in required):
        raise ValueError("Missing actual gondola model assets")
    cable_model(samples,elevations,model_dir)
    e0,n0,lat0,lon0 = samples[0]
    all_places = [{
        "model": CABLE_KEY, "guid": model_guid(CABLE_KEY),
        "lat": round(lat0,8), "lon": round(lon0,8),
        "kind": "ski_lift_cables", "count":1, "alt":0,
        "heading":0,"scale":1.0, "exclude_autogen":False,
        "placement_precision":"mapped OSM way + IGN terrain elevations",
        "bbox":[min(p[0] for p in samples),min(p[1] for p in samples),
                max(p[0] for p in samples),max(p[1] for p in samples)],
    }]
    # Supports are interpolated along the mapped line and are therefore
    # visually plausible but not an exact inventory of existing pylons.
    for i in range(5,len(samples)-4,7):
        e,n,lat,lon=samples[i]
        dx=samples[i+1][0]-samples[i-1][0]
        dy=samples[i+1][1]-samples[i-1][1]
        heading=(math.degrees(math.atan2(dx,dy)) % 360)
        all_places.append({
            "model":assets["Gondola Tower"]["key"],
            "guid":model_guid(assets["Gondola Tower"]["key"]),
            "lat":round(lat,8),"lon":round(lon,8),
            "kind":"ski_lift_tower","count":1,"alt":0,
            "scale":1.0,"heading":heading,
            "exclude_autogen":False,
            "placement_precision":"interpolated on mapped OSM Pierrafort route",
        })
    for i in range(8,len(samples)-5,8):
        e,n,lat,lon=samples[i]
        dx=samples[i+1][0]-samples[i-1][0]
        dy=samples[i+1][1]-samples[i-1][1]
        heading=(math.degrees(math.atan2(dx,dy)) % 360)
        all_places.append({
            "model":assets["Gondola Cabin"]["key"],
            "guid":model_guid(assets["Gondola Cabin"]["key"]),
            "lat":round(lat,8),"lon":round(lon,8),
            "kind":"ski_lift_cabin","count":1,"alt":5.0,
            "scale":1.0,"heading":heading,
            "snap_to_ground":False,"exclude_autogen":False,
            "placement_precision":"illustrative static cabin on mapped route",
        })
    print("PIERRAFORT GONDOLA: OSM+IGN route verified;",
          len(all_places)-1,"static towers/cabins, 2 cable ropes")
    return all_places
