"""IGN BD TOPO vegetation, roads, water: high-fidelity GIS layers for 3 km.

Vegetation: SDK Polygon overrides within real recorded forest polygons. Roads and
water are exported as QA GeoJSON for review; never delete existing sim roads,
water or traffic automatically. Nothing touches existing landmark packages.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from pyproj import Transformer
from shapely.geometry import shape, Point, Polygon, MultiPolygon, GeometryCollection, mapping
from shapely.ops import transform, unary_union

from generate import load_config, fetch_ign, DATA, OUTPUT
from sdk_polygons import add_forest

WFS_LAYERS = {
    'vegetation': 'BDTOPO_V3:zone_de_vegetation',
    'routes': 'BDTOPO_V3:troncon_de_route',
    'hydro': 'BDTOPO_V3:troncon_hydrographique',
    'eau': 'BDTOPO_V3:surface_hydrographique',
}
TO_L93 = Transformer.from_crs('EPSG:4326', 'EPSG:2154', always_xy=True)
TO_WGS = Transformer.from_crs('EPSG:2154', 'EPSG:4326', always_xy=True)


def _polygons(g):
    if isinstance(g,Polygon):
        yield g
    elif isinstance(g,(MultiPolygon,GeometryCollection)):
        for sub in g.geoms:
            yield from _polygons(sub)


def fetch_layers(cfg: dict, target: Path=DATA/'landscape', session=None):
    target.mkdir(parents=True, exist_ok=True)
    results={}
    for key, layer in WFS_LAYERS.items():
        dest=target/f'{key}.geojson'
        if dest.exists() and dest.stat().st_size>100:
            fc=json.loads(dest.read_text(encoding='utf-8'))
        else:
            fc=fetch_ign(cfg['bbox_wgs84'],dest,session=session,layer=layer)
        results[key]=len(fc['features'])
    return results


def build_landscape(cfg:dict, output:Path=OUTPUT, source_dir:Path=DATA/'landscape',
                    *, enforce_vegetation:bool=True)->dict:
    lon,lat=cfg['centre_wgs84']
    x,y=TO_L93.transform(lon,lat)
    circle=Point(x,y).buffer(float(cfg['radius_m']), quad_segs=128)
    protected=unary_union([
        Point(*TO_L93.transform(m['lon'],m['lat'])).buffer(m['radius_m']+5)
        for m in cfg.get('monuments_proteges',[])])
    src=ET.Element('FSData',version='9.0')
    report={'radius_m':cfg['radius_m'],'layers':{},'forest_polygons':0,
            'forest_area_ha':0,'sources_fetched':False,
            'status':'source polygons created; SDK compilation and in-sim rendering not tested'}
    for kind in WFS_LAYERS:
        path=source_dir/f'{kind}.geojson'
        if not path.exists():
            raise FileNotFoundError(f'Données IGN manquantes: {path}. Lancer landscape.py fetch')
        fc=json.loads(path.read_text(encoding='utf-8'))
        types=Counter()
        output_features=[]
        for idx,f in enumerate(fc.get('features',[])):
            try:
                geom=shape(f['geometry'])
                if geom.is_empty:continue
                metric=transform(TO_L93.transform,transform(lambda a,b,c=None:(a,b),geom))
                if not metric.intersects(circle):continue
                clipped=metric.intersection(circle)
                if clipped.is_empty:continue
                if kind=='vegetation':
                    props=f.get('properties') or {}
                    nature=str(props.get('nature') or props.get('nature_detaillee') or '').lower()
                    types[nature]+=1
                    # IGN classification can vary by dataset release; only clear
                    # wooded classes are enforced. Hedgerows/other vegetation stay
                    # in the GeoJSON audit until verified in sim.
                    recognized=any(t in nature for t in ('forêt','foret','bois','arborée','arboree'))
                    if not recognized:
                        continue
                    clipped=clipped.difference(protected)
                    if clipped.is_empty:continue
                    for j,area in enumerate(_polygons(clipped)):
                        area=area.simplify(0.7,preserve_topology=True)
                        if area.area<180 or len(area.exterior.coords)>1200:continue
                        if enforce_vegetation:
                            add_forest(src,area,f'IGN forêt {idx}-{j}',density=31,scale=160,
                                       falloff=5.0,biome='Deciduous_2024')
                        report['forest_polygons']+=1
                        report['forest_area_ha']+=area.area/10000
                        output_features.append({'type':'Feature',
                            'geometry':mapping(transform(TO_WGS.transform,area)),
                            'properties':{'id':str(f.get('id') or idx), 'nature':nature,
                                          'source':'IGN BD TOPO'}})
                else:
                    output_features.append({'type':'Feature',
                        'geometry':mapping(transform(TO_WGS.transform,clipped)),
                        'properties':{'id':str(f.get('id') or idx),
                                      'nature':str((f.get('properties') or {}).get('nature') or ''),
                                      'source':'IGN BD TOPO'}})
            except Exception as exc:
                raise RuntimeError(f'Objet IGN {kind}/{idx} invalide: {exc}') from exc
        target=output/'audit_geographique'
        target.mkdir(parents=True,exist_ok=True)
        (target/f'{kind}_3km.geojson').write_text(json.dumps({'type':'FeatureCollection',
            'features':output_features},ensure_ascii=False),encoding='utf-8')
        report['layers'][kind]={'output_features':len(output_features),'nature_counts':dict(types)}
    if enforce_vegetation and report['forest_polygons']:
        scene=output/'PackageSources'/'Scenery'/'saintmaurice'/'scenery'
        if not scene.exists():
            raise ValueError('Générer les bâtiments avant le paysage: generate.py all --limit 0')
        ET.ElementTree(src).write(scene/'saint_maurice_vegetation.xml',encoding='utf-8',xml_declaration=True)
    report['forest_area_ha']=round(report['forest_area_ha'],1)
    report['sources_fetched']=True
    (output/'landscape_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description='IGN BD TOPO paysages réels sur rayon 3 km')
    parser.add_argument('action',choices=['fetch','build','all'])
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--source-dir',type=Path,default=DATA/'landscape')
    parser.add_argument('--audit-only',action='store_true',help='Ne pas produire les polygones de végétation dans le BGL')
    args=parser.parse_args()
    cfg=load_config()
    if args.action in ('fetch','all'):
        print('Téléchargements IGN:',fetch_layers(cfg,args.source_dir))
    if args.action in ('build','all'):
        print(json.dumps(build_landscape(cfg,args.output,args.source_dir,
                    enforce_vegetation=not args.audit_only),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
