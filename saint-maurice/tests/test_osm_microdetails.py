import sys
from pathlib import Path
import json
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate import DATA,build_scene,load_config
from osm_microdetails import build_osm_details, query_osm
from sdk_export import validate_gltf_files


def test_osm_walls_hedges_and_protection(tmp_path):
    cfg=load_config()
    # Small OSM way near (but outside) protected church/madone buffers.
    lon,lat=cfg['centre_wgs84']
    base_lon=lon+.0020
    raw={'elements':[
      {'type':'way','id':51,'tags':{'barrier':'wall'},
       'geometry':[{'lon':base_lon,'lat':lat+.0010},{'lon':base_lon+.001,'lat':lat+.0010}]},
      {'type':'way','id':52,'tags':{'barrier':'hedge'},
       'geometry':[{'lon':base_lon,'lat':lat+.0013},{'lon':base_lon+.0006,'lat':lat+.0013}]},
      {'type':'node','id':99,'lat':lat+.0010,'lon':base_lon+.0013,'tags':{'natural':'tree'}}
    ]}
    build_scene(json.loads((DATA/'fixture_buildings.geojson').read_text()),cfg,tmp_path,0)
    report=build_osm_details(raw,cfg,tmp_path)
    assert report['source_placed_wall_and_hedge_segments']>0
    assert report['isolated_trees_mapped']==1
    root=ET.parse(tmp_path/'PackageSources/Scenery/saintmaurice/scenery/saint_maurice_osm_details.xml').getroot()
    assert len(root.findall('SceneryObject'))==report['model_clusters']
    lib=tmp_path/'PackageSources/Scenery/saintmaurice/modellib'
    assert validate_gltf_files(lib)['gltf_checked']>=3


def test_query_osm_uses_real_radius_and_returns_empty():
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'elements':[]}
    class Session:
        def post(self,url,data,timeout):
            assert 'around:3100' in data['data']
            assert 'barrier' in data['data']
            return Response()
    assert query_osm((4.63,45.58),3000,Session())['elements']==[]
