"""Non-destructive validation of generated SDK sources and preservation areas."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from shapely.geometry import box, Point, Polygon
from pyproj import Transformer
from sdk_export import validate_gltf_files

ROOT=Path(__file__).resolve().parent
TO_L93=Transformer.from_crs('EPSG:4326','EPSG:2154',always_xy=True)


def validate(out:Path)->dict:
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    root=out/'PackageSources'/'Scenery'/'saintmaurice'
    scxml=ET.parse(root/'scenery'/'saint_maurice_buildings.xml').getroot()
    with (out/'inventory.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f,delimiter=';'))
    models=root/'modellib'
    objs=scxml.findall('SceneryObject')
    excl=[x for x in scxml.findall('Polygon') if x.find("Attribute[@name='ExcludeOSMBuildings']") is not None]
    protected=[]
    for x in config['monuments_proteges']:
        mx,my=TO_L93.transform(x['lon'],x['lat'])
        protected.append((x['name'],Point(mx,my).buffer(x['radius_m'])))
    assert len(rows)>0,'Inventaire vide'
    assert len(excl)==len(rows),'Exclusions incohérentes'
    # Other models (OSM walls/hedges) may share the ModelLib and have their own BGL.
    available_models={file.stem for file in models.glob('*.gltf')}
    building_models={r['model'] for r in rows}
    assert len(objs)==len(building_models),'Objets bâtiments / modèles incohérents'
    assert building_models.issubset(available_models),'Modèles bâtiments manquants'
    cx,cy=TO_L93.transform(*config['centre_wgs84'])
    for row in rows:
        x,y=TO_L93.transform(float(row['longitude']),float(row['latitude']))
        assert (x-cx)**2+(y-cy)**2<=(config['radius_m']+1)**2, 'Bâtiment hors rayon'
        for name,area in protected:
            assert not area.contains(Point(x,y)),f'Bâtiment dans {name}'
        name=row['model']
        gltf=models/f'{name}.gltf'
        assert gltf.is_file(),f'Modèle manquant : {name}'
        doc=json.loads(gltf.read_text(encoding='utf-8'))
        assert doc['asset']['version']=='2.0'
        for binary in doc.get('buffers',[]):
            assert (models/binary['uri']).is_file(),f"Buffer manquant: {binary['uri']}"
    for e in excl:
        assert e.find("Attribute[@name='ExcludeDetectedBuildings']") is not None, 'Exclusion détectée absente'
        coords=[TO_L93.transform(float(v.get('lon')),float(v.get('lat')))
                for v in e.findall('Vertex')]
        poly=Polygon(coords)
        assert poly.is_valid and poly.area>0, 'Polygone auto-génération invalide'
        for name,area in protected:
            assert not poly.intersects(area),f'Exclusion entre en conflit avec {name}'
    sdk_models=validate_gltf_files(models)
    extra_xml=root/'scenery'/'saint_maurice_osm_details.xml'
    osm_placements=len(ET.parse(extra_xml).getroot().findall('SceneryObject')) if extra_xml.exists() else 0
    summary={'ok':True,'maisons':len(rows),'objets':len(objs),'exclusions':len(excl),
             'monuments_proteges':len(protected),'osm_microdetail_placements':osm_placements,
             'gltf_external_textures_checked':sdk_models, 'compilation_sdk':'non vérifiée'}
    (out/'validation_pre_sdk.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'output'
    print(json.dumps(validate(path),ensure_ascii=False,indent=2))
