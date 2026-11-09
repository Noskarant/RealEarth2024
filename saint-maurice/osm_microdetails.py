"""Georeferenced close-range details from OpenStreetMap Overpass.

Data are NOT fabricated: only explicitly mapped walls/hedges/trees are used.
Wall and hedge placements have procedural shapes and estimated dimensions.
Native species-specific Tree placement needs a real SDK Tree model GUID supplied
by the scenery author; no GUID is guessed. All monument buffers are excluded.
OSM: © OpenStreetMap contributors, ODbL. Source is saved for reproducibility.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer
import requests
from shapely.geometry import Point, LineString, box, mapping
from shapely.ops import transform
import trimesh

from generate import DATA, OUTPUT, NAMESPACE, load_config
from sdk_export import emit_scene
from materials_hd import texture, uv_from_vertices

OVERPASS = 'https://overpass-api.de/api/interpreter'
TO_L93 = Transformer.from_crs('EPSG:4326','EPSG:2154',always_xy=True)
TO_WGS = Transformer.from_crs('EPSG:2154','EPSG:4326',always_xy=True)


def query_osm(center: tuple[float,float], radius: int, session=None, endpoint=OVERPASS):
    lon,lat=center
    r=int(radius)+100
    query=f'''[out:json][timeout:150];(
      node["natural"="tree"](around:{r},{lat},{lon});
      way["barrier"~"^(wall|retaining_wall|hedge|fence)$"](around:{r},{lat},{lon});
      way["natural"="tree_row"](around:{r},{lat},{lon});
      way["landuse"~"^(orchard|vineyard)$"](around:{r},{lat},{lon});
      node["historic"~"^(wayside_cross|memorial|monument)$"](around:{r},{lat},{lon});
    );out geom;'''
    client=session or requests.Session()
    response=client.post(endpoint,data={'data':query},timeout=210)
    response.raise_for_status()
    parsed=response.json()
    if not isinstance(parsed.get('elements'),list):
        raise RuntimeError('Malformed Overpass response')
    return parsed


def _subdivide(line:LineString, spacing=7.0):
    if line.length < 0.5:
        return
    steps=max(1,math.ceil(line.length/spacing))
    for i in range(steps):
        a=line.interpolate(i/steps,normalized=True)
        b=line.interpolate((i+1)/steps,normalized=True)
        if a.distance(b) >= 0.4:
            yield (a.x,a.y,b.x,b.y)


def _mesh_segment(ax,ay,bx,by,center,typ):
    """Return mesh with bottom slightly below ground to conceal minor slope errors."""
    length=math.hypot(bx-ax,by-ay)
    if length < 0.4:return None
    angle=math.atan2(by-ay,bx-ax)
    thickness=1.0 if typ=='hedge' else 0.45
    top=1.7 if typ=='hedge' else 1.15
    btm=-0.9 if typ=='hedge' else -0.8
    # Box defined in glTF coordinate convention; local X along wall, Y vertical.
    item=trimesh.creation.box(extents=(length,top-btm,thickness))
    item.apply_translation((0,(top+btm)/2,0))
    # Transform X east and Z negative north around vertical axis.
    # local X -> (+cos angle east, -sin angle gltf Z)
    c=math.cos(angle);s=math.sin(angle)
    rot=np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]],dtype=float)
    item.apply_transform(rot)
    cx=(ax+bx)/2-center[0];cy=(ay+by)/2-center[1]
    item.apply_translation((cx,0,-cy))
    return item


def build_osm_details(raw:dict,cfg:dict,out:Path,max_segments:int=15000):
    lon,lat=cfg['centre_wgs84']
    cx,cy=TO_L93.transform(lon,lat)
    radius=float(cfg['radius_m'])
    disk=Point(cx,cy).buffer(radius,quad_segs=96)
    protected=[Point(*TO_L93.transform(a['lon'],a['lat'])).buffer(float(a['radius_m'])+4)
               for a in cfg.get('monuments_proteges',[])]
    segments=[]
    audit=[]
    trees=[]
    for e in raw.get('elements',[]):
        tags=e.get('tags') or {}
        category = tags.get('barrier') or tags.get('natural') or tags.get('landuse') or tags.get('historic')
        if e.get('type')=='node' and e.get('lat') is not None and e.get('lon') is not None:
            x,y=TO_L93.transform(e['lon'],e['lat'])
            if not disk.covers(Point(x,y)) or any(p.distance(Point(x,y))<0.01 for p in protected):
                continue
            item={'source_id':f"node/{e['id']}",'category':category,'tags':tags,
                  'lon':e['lon'],'lat':e['lat']}
            audit.append(item)
            if category=='tree':trees.append(item)
        elif e.get('type')=='way' and e.get('geometry'):
            points=[TO_L93.transform(p['lon'],p['lat']) for p in e['geometry']]
            if len(points)<2:continue
            line=LineString(points)
            clip=line.intersection(disk)
            if clip.is_empty:continue
            audit.append({'source_id':f"way/{e['id']}",'category':category,'tags':tags,
                          'length_m':round(clip.length,1)})
            if category not in ('wall','retaining_wall','hedge','tree_row'):
                continue
            # Only mapped wall/hedge linework becomes 3D; fences, gardens and
            # vineyards remain in the audit until their physical form is known.
            if clip.geom_type=='LineString':lines=[clip]
            elif clip.geom_type=='MultiLineString':lines=list(clip.geoms)
            else:continue
            for segment_line in lines:
                for seg in _subdivide(segment_line):
                    midpoint=Point((seg[0]+seg[2])/2,(seg[1]+seg[3])/2)
                    if any(area.intersects(midpoint.buffer(4.0)) for area in protected):continue
                    if len(segments)>=max_segments:
                        raise RuntimeError(f'OSM > {max_segments} wall/hedge pieces, increase explicit limit')
                    typ='hedge' if category in ('hedge','tree_row') else 'wall'
                    segments.append((typ,seg,f"way/{e['id']}"))
    sc_xml=ET.Element('FSData',version='9.0')
    model_dir=out/'PackageSources'/'Scenery'/'saintmaurice'/'modellib'
    sc_dir=out/'PackageSources'/'Scenery'/'saintmaurice'/'scenery'
    if not sc_dir.exists():
        raise FileNotFoundError('Build buildings before OSM micro-details')
    # Group in 15-m cells to avoid one model and draw call for every hedge twig.
    cells=defaultdict(list)
    for typ,seg,source in segments:
        mx=(seg[0]+seg[2])/2;my=(seg[1]+seg[3])/2
        cells[(typ,math.floor(mx/15),math.floor(my/15))].append(seg)
    wall_tri=0
    for (typ,ix,iy),parts in sorted(cells.items()):
        ref_x=sum((p[0]+p[2])/2 for p in parts)/len(parts)
        ref_y=sum((p[1]+p[3])/2 for p in parts)/len(parts)
        meshes=[_mesh_segment(*part,(ref_x,ref_y),typ) for part in parts]
        meshes=[m for m in meshes if m is not None]
        if not meshes:continue
        joined=trimesh.util.concatenate(meshes)
        if typ=='wall':
            material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=(1,1,1,1),baseColorTexture=texture('wall_stone'),
                metallicFactor=0.0,roughnessFactor=0.92,doubleSided=True)
            joined.visual=trimesh.visual.TextureVisuals(
                uv=uv_from_vertices(joined.vertices,'wall'),material=material)
        else:
            joined.visual=trimesh.visual.TextureVisuals(
                material=trimesh.visual.material.PBRMaterial(
                    baseColorFactor=(0.22,0.34,0.16,1),
                    roughnessFactor=0.97,metallicFactor=0,doubleSided=True))
        name=f'smd_{typ}_{ix}_{iy}'
        scene=trimesh.Scene();scene.add_geometry(joined)
        meta=emit_scene(scene,name,model_dir,NAMESPACE)
        longitude,latitude=TO_WGS.transform(ref_x,ref_y)
        so=ET.SubElement(sc_xml,'SceneryObject',{
            'instanceId':'{'+str(uuid.uuid5(NAMESPACE,'inst:'+name)).upper()+'}',
            'lat':f'{latitude:.9f}','lon':f'{longitude:.9f}',
            'alt':'0','pitch':'0','bank':'0','heading':'0',
            'imageComplexity':'VERY_SPARSE','altitudeIsAgl':'TRUE',
            'snapToGround':'TRUE','snapToNormal':'FALSE'})
        ET.SubElement(so,'LibraryObject',name=meta['guid'],scale='1.0')
        wall_tri+=len(joined.faces)
    # TreeObject uses an SDK installed modelGUID; never invent an identifier.
    # Once a valid model GUID is supplied, precisely mapped OSM trees may be
    # placed with an actual native MSFS2024 species, snapped to terrain.
    model_guid = str(cfg.get('osm_tree_model_guid') or '').strip()
    tree_objects = 0
    if model_guid:
        try:
            parsed = uuid.UUID(model_guid.strip('{}'))
        except ValueError as exc:
            raise ValueError('osm_tree_model_guid must be a valid real SDK tree GUID') from exc
        valid_name = str(cfg.get('osm_tree_species_name') or '').strip()
        if not valid_name:
            raise ValueError('osm_tree_species_name required with osm_tree_model_guid')
        for tree in trees:
            ET.SubElement(sc_xml, 'Tree', displayName=f"OSM tree {tree['source_id']}",
                         specieName=valid_name,
                         modelGUID='{'+str(parsed).upper()+'}',
                         lat=f"{tree['lat']:.9f}",lon=f"{tree['lon']:.9f}",
                         scale='1.0',snapToGround='TRUE')
            tree_objects += 1
    sc_dir.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(sc_xml).write(sc_dir/'saint_maurice_osm_details.xml',encoding='utf-8',xml_declaration=True)
    out_dir=out/'audit_geographique';out_dir.mkdir(parents=True,exist_ok=True)
    (out_dir/'osm_micromapping.json').write_text(
        json.dumps(audit,ensure_ascii=False,indent=1),encoding='utf-8')
    report={'source':'© OpenStreetMap contributors ODbL via Overpass',
            'sampled_at_utc':datetime.now(timezone.utc).isoformat(),
            'source_elements':len(raw.get('elements',[])),
            'source_placed_wall_and_hedge_segments':len(segments),
            'model_clusters':len(cells),'triangles':wall_tri,
            'isolated_trees_mapped':len(trees),
            'isolated_trees_generated':tree_objects,
            'tree_limitation':('Actual FS2024 tree GUID set; validate model in simulator' if tree_objects else
                               'A real FS2024 tree modelGUID must be selected in Scenery Editor before precise Tree XML placement.'),
            'vertical_limitation':'No LiDAR elevation per micro-segment: snapped to native terrain, verify slopes.'}
    (out/'osm_microdetails_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['fetch','build','all'])
    p.add_argument('--source',type=Path,default=DATA/'osm_microdetails.json')
    p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();cfg=load_config()
    if a.action in ('fetch','all'):
        data=query_osm(tuple(cfg['centre_wgs84']),int(cfg['radius_m']))
        a.source.parent.mkdir(parents=True,exist_ok=True)
        a.source.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    if a.action in ('build','all'):
        data=json.loads(a.source.read_text(encoding='utf-8'))
        print(json.dumps(build_osm_details(data,cfg,a.output),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
