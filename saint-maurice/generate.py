"""Prototype générateur FS2024 pour Saint-Maurice-sur-Dargoire.

Pipeline: IGN BD TOPO WFS -> footprints/altitudes -> glTF + ModelInfo XML ->
placements SDK Scenery XML. Aucun fichier du jeu n'est modifié.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
import requests
from shapely.geometry import Point, Polygon, LineString, box, shape, mapping
from shapely.ops import transform, split, triangulate
import trimesh
from sdk_polygons import exclude_autogen
from materials_hd import texture, choose_kind, uv_from_vertices

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
WFS = "https://data.geopf.fr/wfs/ows"
LAYER = "BDTOPO_V3:batiment"
NAMESPACE = uuid.UUID("fa623a36-e1d8-4210-8ca6-ac39e199469c")
TO_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
TO_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def fetch_ign(bbox: list[float], out: Path, *, page_size: int = 500, session=None, layer: str = LAYER) -> dict:
    """Télécharge toutes les pages WFS sans limiter arbitrairement le nombre d'immeubles."""
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise ValueError("BBOX attendue : lon_min,lat_min,lon_max,lat_max")
    client = session or requests.Session()
    params = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": layer, "SRSNAME": "EPSG:4326",
        "OUTPUTFORMAT": "application/json", "COUNT": page_size,
        "BBOX": ",".join(map(str, bbox)) + ",EPSG:4326",
    }
    seen: set[str] = set()
    features = []
    for start in range(0, 500000, page_size):
        params["STARTINDEX"] = start
        # IGN may transiently throttle long downloads. Retry without duplicating pages.
        import time
        for attempt in range(4):
            try:
                response = client.get(WFS, params=params, timeout=120)
                response.raise_for_status()
                body = response.json()
                break
            except (requests.RequestException, ValueError):
                if attempt == 3:
                    raise
                time.sleep(1.5 * (attempt + 1))
        if body.get("type") != "FeatureCollection":
            raise RuntimeError(f"Réponse IGN inattendue : {str(body)[:300]}")
        batch = body.get("features", [])
        for feat in batch:
            fid = str(feat.get("id") or feat.get("properties", {}).get("cleabs") or "")
            if not fid:
                fid = hashlib.sha1(json.dumps(feat, sort_keys=True).encode()).hexdigest()
            if fid not in seen:
                seen.add(fid)
                features.append(feat)
        print(f"IGN : {len(features)} bâtiments, page {start // page_size + 1}")
        if len(batch) < page_size:
            break
    else:
        raise RuntimeError("Plus de 500 000 objets : vérifier la pagination IGN")
    result = {"type": "FeatureCollection", "features": features}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    (out.parent / f"provenance_{out.stem}.json").write_text(json.dumps({
        "source": "IGN Géoplateforme, BD TOPO v3, WFS",
        "url": WFS, "layer": layer, "bbox_wgs84": bbox,
        "licence": "Licence Ouverte 2.0 - attribution IGN",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "features": len(features),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def num(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def polygons(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []


def to_buildings(fc: dict, config: dict) -> list[dict]:
    """Conserve les empreintes 2D réelles ; hauteur exacte si attribut fiable."""
    core_lon, core_lat = config["centre_wgs84"]
    core_x, core_y = TO_L93.transform(core_lon, core_lat)
    rows = []
    # Zones de protection fondées sur les coordonnées des MODS existants.
    # Les géométries touchant ces zones sont volontairement ignorées :
    # aucun remplacement, masquage ni exclusion automatique des monuments.
    protected = []
    for m in config.get("monuments_proteges", []):
        mx, my = TO_L93.transform(m["lon"], m["lat"])
        protected.append((m["name"], Point(mx, my).buffer(float(m["radius_m"]))))
    radius = float(config.get("radius_m", math.inf))
    for f in fc.get("features", []):
        p = f.get("properties") or {}
        try:
            ll = shape(f["geometry"])
        except (KeyError, ValueError, TypeError):
            continue
        for part_idx, poly in enumerate(polygons(ll)):
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            for piece_idx, part in enumerate(polygons(poly)):
                # Force to 2D: some 3D BD TOPO polygons have Z coordinates.
                xy = transform(lambda x, y, z=None: (x, y), part)
                metric = transform(TO_L93.transform, xy)
                if metric.area < config["minimum_footprint_m2"]:
                    continue
                # Rayon métrique réel : la BBOX de téléchargement n'est qu'une enveloppe.
                if metric.centroid.distance(Point(core_x, core_y)) > radius:
                    continue
                # Une maison dont l'emprise touche l'église ou la Madone n'est
                # pas générée, même si son centroïde est à l'extérieur.
                if any(box(*metric.bounds).buffer(1.3).intersects(zone) for _, zone in protected):
                    continue
                simpl = metric.simplify(config["simplify_tolerance_m"], preserve_topology=True)
                if not isinstance(simpl, Polygon) or simpl.is_empty or len(simpl.exterior.coords) < 4:
                    continue
                # Preserve inner courtyards: walls and roof triangulation account
                # for holes instead of filling real openings with fake roofs.
                centroid = simpl.centroid
                lon, lat = TO_WGS.transform(centroid.x, centroid.y)
                height = num(p.get("hauteur"))
                ground = num(p.get("altitude_minimale_sol"))
                roofmax = num(p.get("altitude_maximale_toit"))
                roofmin = num(p.get("altitude_minimale_toit"))
                if height is None and ground is not None and roofmax is not None:
                    height = roofmax - ground
                height_source = "IGN" if height is not None and 2 <= height <= 90 else "estimée"
                if height_source == "estimée":
                    height = 7.0 if metric.area < 150 else 6.5
                roof_rise = (roofmax-roofmin) if (roofmax is not None and roofmin is not None) else None
                roof_source = "IGN" if roof_rise is not None and 0.0 <= roof_rise <= 7.0 else "estimée"
                if roof_source == "estimée":
                    roof_rise = min(2.4, max(0.6, height*0.22))
                if "plat" in str(p.get("materiaux_de_la_toiture") or "").lower() or height < 3:
                    roof_rise = 0.0
                raw_id = str(p.get("cleabs") or f.get("id") or f"{lon:.7f}_{lat:.7f}")
                bid = hashlib.sha1(f"{raw_id}/{part_idx}/{piece_idx}".encode()).hexdigest()[:14]
                rows.append({
                    "id": bid, "source_id": raw_id, "lon": lon, "lat": lat,
                    "height_m": round(height, 2), "height_source": height_source,
                    "roof_rise_m": round(min(roof_rise, height*.65), 2), "roof_source": roof_source,
                    "ground_m": ground, "area_m2": round(metric.area, 2),
                    "distance_core_m": round(math.hypot(centroid.x-core_x, centroid.y-core_y), 1),
                    "polygon": simpl, "had_holes": len(metric.interiors) > 0,
                    "nature": str(p.get("nature") or ""),
                    "roof_material": str(p.get("materiaux_de_la_toiture") or ""),
                    "wall_material": str(p.get("materiaux_des_murs") or ""),
                })
    # Closest houses first so a limited test targets the village, not first WFS pages.
    rows.sort(key=lambda r: (r["distance_core_m"], r["id"]))
    return rows


def _faces_for_polygon(poly: Polygon, centroid, roof_eave: float, roof_rise: float,
                       foundation_depth: float):
    """Meshes triangle + coord. locales glTF x/height/-north, en mètres."""
    coords = list(poly.exterior.coords)[:-1]
    walls = []
    wall_faces = []
    for ring in [poly.exterior, *list(poly.interiors)]:
        loop=list(ring.coords)[:-1]
        for i, (x1, y1) in enumerate(loop):
            x2, y2 = loop[(i + 1) % len(loop)]
            base = len(walls)
            # Interior rings have opposite winding, hence face into courtyard.
            walls.extend([(x1-centroid.x, -foundation_depth, -(y1-centroid.y)),
                          (x2-centroid.x, -foundation_depth, -(y2-centroid.y)),
                          (x2-centroid.x, roof_eave, -(y2-centroid.y)),
                          (x1-centroid.x, roof_eave, -(y1-centroid.y))])
            wall_faces.extend([(base,base+2,base+1),(base,base+3,base+2)])
    # Roof ridge through the middle of the minimum rotated rectangle.
    rect = list(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    edges = [(rect[(i+1)%4][0]-rect[i][0], rect[(i+1)%4][1]-rect[i][1]) for i in (0,1)]
    major = max(edges, key=lambda v: math.hypot(*v))
    major_len = math.hypot(*major)
    dx, dy = (major[0]/major_len, major[1]/major_len) if major_len > 0 else (1,0)
    nx, ny = -dy, dx
    half_width = max(0.01, max(abs((x-centroid.x)*nx+(y-centroid.y)*ny) for x,y in coords))
    span = max(poly.bounds[2]-poly.bounds[0],poly.bounds[3]-poly.bounds[1]) * 4
    cutter = LineString([(centroid.x-dx*span,centroid.y-dy*span),
                         (centroid.x+dx*span,centroid.y+dy*span)])
    try:
        parts = list(split(poly,cutter).geoms)
    except Exception:
        parts = [poly]
    roof_verts = []
    roof_faces = []
    for part in parts:
        for t in triangulate(part):
            # Shapely Delaunay may include triangles outside concave outlines.
            if not part.covers(t.representative_point()) or not part.covers(t):
                continue
            pts = list(t.exterior.coords)[:3]
            ii = len(roof_verts)
            for x,y in pts:
                across = abs((x-centroid.x)*nx+(y-centroid.y)*ny)
                h = roof_eave + roof_rise*max(0.0,1.0-across/half_width)
                roof_verts.append((x-centroid.x,h,-(y-centroid.y)))
            roof_faces.append((ii,ii+2,ii+1))
    return (np.asarray(walls, dtype=np.float32), np.asarray(wall_faces, dtype=np.int64),
            np.asarray(roof_verts, dtype=np.float32),np.asarray(roof_faces, dtype=np.int64))


def _mesh(vertices, faces, rgba, *, surface=None, material_hint="", textures_enabled=False):
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    kwargs=dict(baseColorFactor=rgba, metallicFactor=0.0,
                roughnessFactor=0.91 if surface=='roof' else 0.84,
                doubleSided=True)
    if textures_enabled and surface in ('roof','wall'):
        kwargs['baseColorTexture']=texture(choose_kind(material_hint,surface))
        mesh.visual=trimesh.visual.TextureVisuals(
            uv=uv_from_vertices(np.asarray(vertices),surface),
            material=trimesh.visual.material.PBRMaterial(**kwargs))
    else:
        mesh.visual=trimesh.visual.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(**kwargs))
    return mesh


def export_model(b: dict, model_dir: Path, cfg: dict) -> dict:
    name = "sm_" + b["id"]
    model_dir.mkdir(parents=True, exist_ok=True)
    rise = b.get("roof_rise_m", min(2.4, max(0.6, b["height_m"]*0.22)))
    eave = b["height_m"]-rise
    v1,f1,v2,f2 = _faces_for_polygon(b["polygon"],b["polygon"].centroid,eave,rise,cfg["foundation_depth_m"])
    if not len(f2):
        raise ValueError("Impossible de trianguler toiture : " + b["id"])
    seed = int(b["id"][:6],16)
    walls = [[214,200,178,255],[195,185,164,255],[223,215,194,255],[180,170,152,255]][seed%4]
    roofs = [[172,87,64,255],[184,99,69,255],[150,78,58,255]][seed%3]
    sc = trimesh.Scene()
    use_tex=bool(cfg.get('experimental_pbr_textures', True))
    sc.add_geometry(_mesh(v1,f1,walls,surface='wall',material_hint=b['wall_material'],
                          textures_enabled=use_tex),geom_name=name+"_walls")
    sc.add_geometry(_mesh(v2,f2,roofs,surface='roof',material_hint=b['roof_material'],
                          textures_enabled=use_tex),geom_name=name+"_roof")
    payloads = sc.export(file_type="gltf")
    gltf_key = next((key for key in payloads if key.endswith(".gltf")),None)
    if gltf_key is None:
        raise ValueError("Export trimesh inattendu : aucun glTF")
    gltf_doc = json.loads(payloads[gltf_key].decode("utf-8") if isinstance(payloads[gltf_key],bytes) else payloads[gltf_key])
    for buffer in gltf_doc.get("buffers",[]):
        old_uri = buffer.get("uri")
        if not old_uri or old_uri not in payloads:
            raise ValueError("Buffer glTF absent : " + str(old_uri))
        new_uri = f"{name}_{old_uri}"
        data = payloads[old_uri]
        (model_dir/new_uri).write_bytes(data if isinstance(data,bytes) else data.encode("utf-8"))
        buffer["uri"] = new_uri
    target = model_dir / f"{name}.gltf"
    target.write_text(json.dumps(gltf_doc,ensure_ascii=False),encoding="utf-8")
    # Model XML must point at a real glTF. No textures are required.
    guid = "{" + str(uuid.uuid5(NAMESPACE, "model:"+name)).upper() + "}"
    modelinfo = ET.Element("ModelInfo",guid=guid, version="1.1")
    lods = ET.SubElement(modelinfo,"LODS")
    ET.SubElement(lods,"LOD",minSize="0",ModelFile=target.name)
    ET.ElementTree(modelinfo).write(model_dir / f"{name}.xml", encoding="utf-8",xml_declaration=True)
    return {"name": name,"guid": guid,"path": str(target),"triangles": len(f1)+len(f2)}


def write_sdk_project(out: Path, config: dict) -> None:
    """Structure d'un projet autonome inspirée du projet RealEarth2024 existant."""
    slug = config["scene"]
    pkgdef = out / "PackageDefinitions" / f"{slug}.xml"
    pkgdef.parent.mkdir(parents=True,exist_ok=True)
    project = ET.Element("Project",{
        "Version":"2", "Name":slug, "FolderName":"Packages",
        "MetadataFolderName":"PackagesMetadata"})
    ET.SubElement(project,"OutputDirectory").text="."
    ET.SubElement(project,"TemporaryOutputDirectory").text="_PackageInt"
    packages=ET.SubElement(project,"Packages")
    ET.SubElement(packages,"Package").text=f"PackageDefinitions\\{slug}.xml"
    ET.SubElement(project,"PublishingGroups")
    ET.ElementTree(project).write(out/f"{slug}.xml",encoding="utf-8",xml_declaration=True)
    pkg=ET.Element("AssetPackage",Version="0.1.3")
    settings=ET.SubElement(pkg,"ItemSettings")
    for k,v in {
        "ContentType":"SCENERY","Title":"RealEarth Saint-Maurice-sur-Dargoire HD",
        "Manufacturer":"RealEarth","Creator":"RealEarth2024"}.items():
        ET.SubElement(settings,k).text=v
    flags=ET.SubElement(pkg,"Flags")
    ET.SubElement(flags,"VisibleInStore").text="false"
    ET.SubElement(flags,"CanBeReferenced").text="false"
    ET.SubElement(pkg,"PackageOrderHint").text="CUSTOM_SCENERY_PATCH"
    groups=ET.SubElement(pkg,"AssetGroups")
    for groupname,typ,version,subpath,outputdir in [
        ("saintmaurice_modellib","ModelLib","1","modellib","Scenery\\saintmaurice\\modellib\\"),
        ("saintmaurice_scenery","BGL","0","scenery","Scenery\\saintmaurice\\scenery\\")]:
        group=ET.SubElement(groups,"AssetGroup",Name=groupname)
        ET.SubElement(group,"Type",Version=version).text=typ
        gflags=ET.SubElement(group,"Flags")
        ET.SubElement(gflags,"FSXCompatibility").text="false"
        ET.SubElement(group,"AssetDir").text=f"PackageSources\\Scenery\\saintmaurice\\{subpath}\\"
        ET.SubElement(group,"OutputDir").text=outputdir
    ET.ElementTree(pkg).write(pkgdef,encoding="utf-8",xml_declaration=True)


def _cluster_key(b: dict, cfg: dict) -> tuple:
    """Buildings near the center remain individually placed and recognizable."""
    if b["distance_core_m"] <= cfg.get("core_radius_m", 900):
        return ("core", b["id"])
    # Unknown ground: keep individual to avoid suspended houses on steep hills.
    ground = b["ground_m"]
    if ground is None:
        return ("unknown_height", b["id"])
    cell = float(cfg.get("cluster_cell_m", 75))
    band = float(cfg.get("cluster_alt_band_m", 1.5))
    cx, cy = b["polygon"].centroid.coords[0]
    return ("cluster", math.floor(cx/cell), math.floor(cy/cell), math.floor(ground/band))


def export_cluster(group: list[dict], model_dir: Path, cfg: dict) -> dict:
    """Combine nearby buildings on the same height band into a few meshes.

    Saves draw calls without merging entire hillsides into one floating object.
    Every building keeps its own footprint and approximate relative elevation.
    """
    ids = ",".join(sorted(b["id"] for b in group))
    name = "sml_" + hashlib.sha1(ids.encode()).hexdigest()[:16]
    model_dir.mkdir(parents=True, exist_ok=True)
    x0 = sum(b["polygon"].centroid.x for b in group) / len(group)
    y0 = sum(b["polygon"].centroid.y for b in group) / len(group)
    alts = sorted(b["ground_m"] for b in group if b["ground_m"] is not None)
    z0 = alts[len(alts)//2] if alts else None
    collections = defaultdict(list)
    for b in group:
        rise = b["roof_rise_m"]
        eave = max(1.0, b["height_m"] - rise)
        v1, f1, v2, f2 = _faces_for_polygon(
            b["polygon"], b["polygon"].centroid, eave, rise, cfg["foundation_depth_m"])
        shift = np.asarray([b["polygon"].centroid.x-x0,
                            (b["ground_m"]-z0) if z0 is not None and b["ground_m"] is not None else 0.0,
                            -(b["polygon"].centroid.y-y0)], dtype=np.float32)
        seed = int(b["id"][:6], 16)
        collections[("wall", seed%4)].append((v1+shift, f1))
        collections[("roof", seed%3)].append((v2+shift, f2))
    wall_colors = [[214,200,178,255],[195,185,164,255],[223,215,194,255],[180,170,152,255]]
    # Tuiles de terre cuite dominantes autour du bourg (variantes estimées).
    roof_colors = [[172,87,64,255],[184,99,69,255],[150,78,58,255]]
    scene = trimesh.Scene()
    total_tri = 0
    for (typ,variant), parts in sorted(collections.items()):
        verts = []; faces=[]; offset=0
        for v,f in parts:
            if len(f)==0:continue
            verts.append(v)
            faces.append(f+offset)
            offset += len(v)
        if not verts:continue
        colors = wall_colors[variant] if typ=="wall" else roof_colors[variant]
        # Textured tile atlas; these are generic PBR materials, not photographs.
        joined = _mesh(np.concatenate(verts),np.concatenate(faces),colors,
                       surface=typ,textures_enabled=bool(cfg.get('experimental_pbr_textures',True)))
        total_tri += len(joined.faces)
        scene.add_geometry(joined,geom_name=f"{name}_{typ}_{variant}")
    _write_gltf_scene(name,scene,model_dir)
    lon,lat=TO_WGS.transform(x0,y0)
    return {"name":name,"guid":"{"+str(uuid.uuid5(NAMESPACE,"model:"+name)).upper()+"}",
            "triangles":total_tri,"lon":lon,"lat":lat,"kind":"cluster", "count":len(group)}


def _write_gltf_scene(name, scene: trimesh.Scene, model_dir: Path) -> None:
    """Write one self-contained ModelLib asset from Trimesh's GLTF export."""
    payloads=scene.export(file_type="gltf")
    key=next((k for k in payloads if k.endswith(".gltf")),None)
    if key is None:raise ValueError("Export glTF manquant")
    document=json.loads(payloads[key].decode("utf-8") if isinstance(payloads[key],bytes) else payloads[key])
    for buf in document.get("buffers",[]):
        old=buf.get("uri")
        if not old or old not in payloads:raise ValueError("Buffer glTF manquant: "+str(old))
        new=f"{name}_{old}"
        raw=payloads[old]
        (model_dir/new).write_bytes(raw if isinstance(raw,bytes) else raw.encode("utf-8"))
        buf["uri"]=new
    (model_dir/f"{name}.gltf").write_text(json.dumps(document,ensure_ascii=False),encoding="utf-8")
    guid="{"+str(uuid.uuid5(NAMESPACE,"model:"+name)).upper()+"}"
    modelinfo=ET.Element("ModelInfo",guid=guid,version="1.1")
    lods=ET.SubElement(modelinfo,"LODS")
    ET.SubElement(lods,"LOD",minSize="0",ModelFile=f"{name}.gltf")
    ET.ElementTree(modelinfo).write(model_dir/f"{name}.xml",encoding="utf-8",xml_declaration=True)


def build_scene(fc: dict, cfg: dict, out: Path, limit: int = 200) -> dict:
    buildings = to_buildings(fc,cfg)
    if not buildings:
        raise ValueError("Aucun bâtiment valide dans le rayon et hors zones protégées")
    if limit > 0:
        buildings = buildings[:limit]
    out.mkdir(parents=True,exist_ok=True)
    modeldir = out/"PackageSources"/"Scenery"/"saintmaurice"/"modellib"
    scenerydir = out/"PackageSources"/"Scenery"/"saintmaurice"/"scenery"
    # Clean only models previously generated by this project (never other mods).
    if modeldir.exists():
        for pattern in ("sm_*.gltf", "sm_*.bin", "sm_*.xml",
                        "sml_*.gltf", "sml_*.bin", "sml_*.xml"):
            for old in modeldir.glob(pattern):old.unlink()
    scenerydir.mkdir(parents=True,exist_ok=True)
    write_sdk_project(out,cfg)
    src = ET.Element("FSData", version="9.0")
    audit=[]
    footprints=[]
    groups=defaultdict(list)
    for b in buildings:
        # Full 3 km build: cluster distant objects, keep all center houses separate.
        key=_cluster_key(b,cfg) if limit==0 else ("pilot",b["id"])
        groups[key].append(b)
    placement_count=0
    tri_count=0
    for key,group in groups.items():
        if len(group)==1:
            b=group[0]
            model=export_model(b,modeldir,cfg)
            model["lat"],model["lon"]=b["lat"],b["lon"]
        else:
            model=export_cluster(group,modeldir,cfg)
        gid="{"+str(uuid.uuid5(NAMESPACE,"inst:"+model["name"])).upper()+"}"
        obj=ET.SubElement(src,"SceneryObject",{
            "instanceId":gid,"lat":f'{model["lat"]:.9f}',"lon":f'{model["lon"]:.9f}',
            "alt":"0.0","pitch":"0.0","bank":"0.0","heading":"0.0",
            "imageComplexity":"NORMAL","altitudeIsAgl":"TRUE",
            "snapToGround":"TRUE","snapToNormal":"FALSE"})
        ET.SubElement(obj,"LibraryObject",name=model["guid"],scale="1.0")
        placement_count+=1
        tri_count+=model["triangles"]
        for b in group:
            # FS2024: these Polygon attributes exclude BOTH native detected
            # and OSM buildings, unlike generic ExclusionRectangle alone.
            # The bounding box is already verified outside landmark buffers.
            exclude_autogen(src, b["polygon"], "Maison IGN " + b["id"])
            audit.append({
                "id":b["id"],"source_id":b["source_id"],
                "latitude":f'{b["lat"]:.8f}',"longitude":f'{b["lon"]:.8f}',
                "distance_core_m":b["distance_core_m"],
                "area_m2":b["area_m2"],"height_m":b["height_m"],
                "height_source":b["height_source"],"ground_m":b["ground_m"],
                "roof_rise_m":b["roof_rise_m"],"roof_source":b["roof_source"],
                "has_inner_courtyard":b["had_holes"],"model":model["name"],
                "placement_kind":model.get("kind","individual"),
            })
            footprints.append({"type":"Feature","geometry":mapping(transform(TO_WGS.transform,b["polygon"])),
                               "properties":{"id":b["id"],"height_m":b["height_m"],
                                             "height_source":b["height_source"],
                                             "model":model["name"]}})
    ET.ElementTree(src).write(scenerydir/"saint_maurice_buildings.xml",encoding="utf-8",xml_declaration=True)
    with (out/"inventory.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(audit[0].keys()),delimiter=";")
        writer.writeheader();writer.writerows(audit)
    (out/"footprints.geojson").write_text(json.dumps({"type":"FeatureCollection","features":footprints},ensure_ascii=False),encoding="utf-8")
    report={
        "scene":cfg["scene"],"source":"IGN BD TOPO (ou fixture si test)",
        "radius_m":cfg.get("radius_m"),
        "buildings_exported":len(audit),
        "heights_ign":sum(x["height_source"]=="IGN" for x in audit),
        "heights_estimated":sum(x["height_source"]=="estimée" for x in audit),
        "roofs_ign":sum(x["roof_source"]=="IGN" for x in audit),
        "triangles":tri_count,
        "with_inner_courtyards_simplified":sum(bool(x["has_inner_courtyard"]) for x in audit),
        "models":len(groups),"placements":placement_count,
        "clusters":sum(len(g)>1 for g in groups.values()),
        "protected_landmarks":[m["name"] for m in cfg.get("monuments_proteges",[])],
        "limits":[
            "Nécessite compilation avec SDK MSFS2024 + validation en jeu",
            "Relief natif MSFS2024 conservé ; pas de LiDAR ni orthophoto embarqués",
            "Toitures simplifiées : géométrie estimée si mesures IGN manquantes",
            "Textures PBR procédurales, pas de photographies de chaque maison ; compilation KTX2 à vérifier",
            "Polygones SDK 2024 : OSM et bâtiments détectés exclus ; résultat à valider en Scenery Editor",
            "Cours intérieures conservées dans le maillage lorsque la géométrie IGN les décrit",
            "La position GPS et altitude exactes des objets existants ne sont pas modifiées"
        ]}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

def main():
    parser=argparse.ArgumentParser(description="Saint-Maurice-sur-Dargoire vers glTF/FS2024")
    parser.add_argument("command",choices=["fetch","build","all"])
    parser.add_argument("--source",type=Path,default=DATA/"ign_buildings.geojson")
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--limit",type=int,default=None,help="0 = tous ; valeur par défaut = prototype")
    args=parser.parse_args()
    cfg=load_config()
    if args.command in ("fetch","all"):
        fetch_ign(cfg["bbox_wgs84"],args.source)
    if args.command in ("build","all"):
        if not args.source.exists():
            parser.error(f"Fichier manquant : {args.source} ; lancer d'abord 'fetch' ou 'all'")
        fc=json.loads(args.source.read_text(encoding="utf-8"))
        report=build_scene(fc,cfg,args.output,
                           cfg["max_buildings_prototype"] if args.limit is None else args.limit)
        print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
