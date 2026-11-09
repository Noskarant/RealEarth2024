import json
import sys
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate import DATA, build_scene, load_config
from sdk_export import validate_gltf_files
from facades_hd import facades_for_building


def test_external_sdk_textures_are_shared(tmp_path):
    fc=json.loads((DATA/'fixture_buildings.geojson').read_text())
    build_scene(fc,load_config(),tmp_path,0)
    model_dir=tmp_path/'PackageSources/Scenery/saintmaurice/modellib'
    stats=validate_gltf_files(model_dir)
    assert stats['gltf_checked']==3
    assert 1<=stats['shared_png_textures']<=6
    for f in (model_dir/'texture').glob('*.png'):
        img=Image.open(f)
        assert img.size==(256,256)
        assert ET.parse(f.with_suffix('.png.xml')).getroot().tag=='BitmapConfiguration'


def test_procedural_facades_not_outside_core(tmp_path):
    fc=json.loads((DATA/'fixture_buildings.geojson').read_text())
    cfg=load_config();cfg['facades_radius_m']=0
    build_scene(fc,cfg,tmp_path,0)
    model_dir=tmp_path/'PackageSources/Scenery/saintmaurice/modellib'
    for p in model_dir.glob('*.gltf'):
        doc=json.loads(p.read_text())
        assert len(doc['meshes'])==2
