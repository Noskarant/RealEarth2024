import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate import build_scene, fetch_ign, load_config, to_buildings

FIXTURE=Path(__file__).resolve().parents[1]/'data'/'fixture_buildings.geojson'


def test_inventory_reads_real_geographic_footprints():
    fc=json.loads(FIXTURE.read_text())
    b=to_buildings(fc,load_config())
    assert len(b)==3
    assert b[0]['distance_core_m']<=b[1]['distance_core_m']
    assert all(x['area_m2']>6 for x in b)
    assert sum(x['height_source']=='IGN' for x in b)==2
    assert sum(x['height_source']=='estimée' for x in b)==1


def test_scene_builds_sdk_xml_and_valid_gltf(tmp_path):
    fc=json.loads(FIXTURE.read_text())
    report=build_scene(fc,load_config(),tmp_path,limit=0)
    assert report['buildings_exported']==3
    assert report['triangles']>20
    xmlfile=tmp_path/'PackageSources'/'Scenery'/'saintmaurice'/'scenery'/'saint_maurice_buildings.xml'
    root=ET.parse(xmlfile).getroot()
    assert len(root.findall('SceneryObject'))==3
    assert len(root.findall('ExclusionRectangle'))==3
    libs=tmp_path/'PackageSources'/'Scenery'/'saintmaurice'/'modellib'
    for file in libs.glob('*.gltf'):
        content=json.loads(file.read_text())
        assert content['asset']['version']=='2.0'
        assert len(content['meshes'])==2
        model_xml=file.with_suffix('.xml')
        assert ET.parse(model_xml).getroot().attrib['guid'].startswith('{')
    assert len(list(libs.glob('*.gltf')))==3
    assert (tmp_path/'realearth-saint-maurice-hd.xml').exists()
    assert (tmp_path/'PackageDefinitions'/'realearth-saint-maurice-hd.xml').exists()
    assert (tmp_path/'inventory.csv').exists()
    assert (tmp_path/'footprints.geojson').exists()


class FakeResponse:
    def __init__(self,body):self.body=body
    def raise_for_status(self):pass
    def json(self):return self.body


class FakeSession:
    def get(self,url,params,timeout):
        start=params['STARTINDEX']
        feats=json.loads(FIXTURE.read_text())['features']
        return FakeResponse({'type':'FeatureCollection','features':feats[start:start+params['COUNT']]})


def test_ign_fetch_paginates(tmp_path):
    fc=fetch_ign(load_config()['bbox_wgs84'],tmp_path/'buildings.geojson',page_size=2,session=FakeSession())
    assert len(fc['features'])==3
    assert json.loads((tmp_path/'provenance.json').read_text())['features']==3
