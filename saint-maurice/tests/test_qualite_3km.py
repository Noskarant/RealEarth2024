import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

from shapely.geometry import box, Point, mapping
from shapely.ops import transform
from pyproj import Transformer
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate import build_scene, load_config, to_buildings, TO_L93, TO_WGS


def synthetic_feature(x, y, uid, ground=480, width=12, height=9):
    polygon=box(x-width/2,y-height/2,x+width/2,y+height/2)
    return {'type':'Feature','id':uid,
            'properties':{'cleabs':uid,'hauteur':8,'altitude_minimale_sol':ground,
                          'altitude_minimale_toit':ground+6.2,'altitude_maximale_toit':ground+8},
            'geometry':mapping(transform(TO_WGS.transform,polygon))}


def test_exact_3km_circle_not_download_bbox():
    c=load_config();x,y=TO_L93.transform(*c['centre_wgs84'])
    fc={'features':[synthetic_feature(x+2990,y,'inside'),
                    synthetic_feature(x+3050,y,'outside'),
                    synthetic_feature(x,y,'church'),
                    synthetic_feature(x+200,y,'bourg')]}
    ids={b['source_id'] for b in to_buildings(fc,c)}
    assert 'inside' in ids and 'outside' not in ids
    assert 'church' not in ids and 'bourg' in ids
    assert c['radius_m']==3000


def test_existing_church_madone_benches_excluded():
    c=load_config();features=[]
    for n,m in enumerate(c['monuments_proteges']):
        x,y=TO_L93.transform(m['lon'],m['lat'])
        features.append(synthetic_feature(x,y,'monument_'+str(n)))
        features.append(synthetic_feature(x+m['radius_m']+22,y,'safe_neighbour_'+str(n)))
    b=to_buildings({'features':features},c)
    ids={x['source_id'] for x in b}
    assert all('monument_'+str(i) not in ids for i in range(len(c['monuments_proteges'])))
    assert all('safe_neighbour_'+str(i) in ids for i in range(len(c['monuments_proteges'])))


def test_full_build_clusters_distant_houses_without_modifying_core(tmp_path):
    c=load_config();x,y=TO_L93.transform(*c['centre_wgs84'])
    features=[synthetic_feature(x+180,y,'bourg'),
              synthetic_feature(x+1730,y,'hameau_1'),
              synthetic_feature(x+1742,y,'hameau_2'),
              synthetic_feature(x+1754,y,'hameau_3',ground=497)]
    b=to_buildings({'features':features},c)
    assert len(b)==4
    report=build_scene({'features':features},c,tmp_path,limit=0)
    assert report['buildings_exported']==4
    assert report['models']==3
    assert report['placements']==3
    assert report['clusters']==1
    assert report['roofs_ign']==4
    src=tmp_path/'PackageSources'/'Scenery'/'saintmaurice'
    xml=ET.parse(src/'scenery'/'saint_maurice_buildings.xml').getroot()
    assert len(xml.findall('SceneryObject'))==3
    assert len(xml.findall('ExclusionRectangle'))==4
    assert len(list((src/'modellib').glob('*.gltf')))==3
    for fp in (src/'modellib').glob('*.gltf'):
        sc=trimesh.load(fp,force='scene')
        assert len(sc.geometry)>=2
        assert sum(len(m.faces) for m in sc.geometry.values())>0
    for m in c['monuments_proteges']:
        mx,my=TO_L93.transform(m['lon'],m['lat'])
        protected=Point(mx,my).buffer(m['radius_m'])
        for r in xml.findall('ExclusionRectangle'):
            a,b=TO_L93.transform(float(r.get('longitudeMinimum')),float(r.get('latitudeMinimum')))
            d,e=TO_L93.transform(float(r.get('longitudeMaximum')),float(r.get('latitudeMaximum')))
            assert not box(a,b,d,e).intersects(protected)
