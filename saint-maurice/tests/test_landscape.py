from pathlib import Path
import json,sys,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Point, box, mapping, Polygon
from shapely.ops import transform
from generate import load_config,TO_WGS,TO_L93
from landscape import build_landscape
from sdk_polygons import add_forest


def test_hole_in_forest_cannot_spawn_trees_at_madone():
    c=load_config()
    cx,cy=TO_L93.transform(*c['centre_wgs84'])
    forest=Point(cx,cy).buffer(80).difference(Point(cx,cy).buffer(30))
    root=ET.Element('FSData')
    count=add_forest(root,forest,'forest')
    assert count>2
    for tag in root.findall('Polygon'):
        ring=[TO_L93.transform(float(v.get('lon')),float(v.get('lat'))) for v in tag.findall('Vertex')]
        assert not Polygon(ring).intersects(Point(cx,cy).buffer(20))


def test_landscape_clips_to_three_km_and_protected_landmarks(tmp_path):
    c=load_config()
    x,y=TO_L93.transform(*c['centre_wgs84'])
    data=tmp_path/'data';data.mkdir()
    forest=box(x-500,y-500,x+500,y+500)
    fc={'type':'FeatureCollection','features':[{'type':'Feature','id':'forest',
        'properties':{'nature':'Forêt'},'geometry':mapping(transform(TO_WGS.transform,forest))}]}
    for kind in ('vegetation','routes','hydro','eau'):
        (data/f'{kind}.geojson').write_text(json.dumps(fc if kind=='vegetation' else
                                          {'type':'FeatureCollection','features':[]}))
    out=tmp_path/'out'
    (out/'PackageSources/Scenery/saintmaurice/scenery').mkdir(parents=True)
    report=build_landscape(c,out,data)
    assert report['forest_polygons']>=1
    xml=ET.parse(out/'PackageSources/Scenery/saintmaurice/scenery/saint_maurice_vegetation.xml').getroot()
    assert xml.findall('Polygon')
    for m in c['monuments_proteges']:
        px,py=TO_L93.transform(m['lon'],m['lat'])
        for tag in xml.findall('Polygon'):
            ring=[TO_L93.transform(float(v.get('lon')),float(v.get('lat'))) for v in tag.findall('Vertex')]
            assert not Polygon(ring).intersects(Point(px,py).buffer(m['radius_m']))
