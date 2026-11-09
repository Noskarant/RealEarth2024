import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest
rasterio=pytest.importorskip("rasterio")
from rasterio.transform import from_bounds
from pyproj import Transformer
cv2=pytest.importorskip("cv2")

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_ortho import quadkey, tile_range, build_cgl, lonlat_tile
from generate import build_scene, load_config

FIXTURE=Path(__file__).resolve().parents[1]/'data'/'fixture_buildings.geojson'


def test_quadkey_is_fixed_20_digits_and_tile_range():
    assert quadkey(*lonlat_tile(4.6312222,45.5829444)).isdigit()
    assert len(quadkey(*lonlat_tile(4.6312222,45.5829444)))==20
    x,y=tile_range(4.6312222,45.5829444,25)
    assert len(x)>0 and len(y)>0


def test_ortho_16bit_alpha_and_cgl_group(tmp_path):
    cfg=load_config()
    fc=json.loads(FIXTURE.read_text(encoding='utf-8'))
    out=tmp_path/'sdk'
    build_scene(fc,cfg,out,limit=3)
    lon,lat=cfg['centre_wgs84']
    tx,ty=Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform(lon,lat)
    tif=tmp_path/'test_ortho.tif'
    rgb=np.zeros((3,512,512),dtype=np.uint8)
    rgb[0,:,:]=175;rgb[1,:,:]=112;rgb[2,:,:]=72
    with rasterio.open(tif,'w',driver='GTiff',width=512,height=512,count=3,
                        dtype='uint8',crs='EPSG:3857',
                        transform=from_bounds(tx-180,ty-180,tx+180,ty+180,512,512)) as f:
        f.write(rgb)
    result=build_cgl(tif,out,lon,lat,radius_m=25,max_tiles=100,fade_m=8)
    assert result['tiles']>0
    group=ET.parse(out/'PackageDefinitions'/f"{cfg['scene']}.xml").getroot()
    assert any(g.get('Name')=='saintmaurice_ortho' for g in group.findall('.//AssetGroup'))
    pngs=list((out/'PackageSources'/'CGL'/'aerial_images').glob('*.png'))
    assert len(pngs)==result['tiles']
    decoded=cv2.imread(str(pngs[0]),cv2.IMREAD_UNCHANGED)
    assert decoded.dtype==np.uint16
    assert decoded.shape[2]==4
    assert (out/'PackageSources'/'CGL'/'saintmaurice_aerial.xml').exists()
