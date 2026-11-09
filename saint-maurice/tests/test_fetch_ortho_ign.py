from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from PIL import Image

from fetch_ortho_ign import build_ortho_ign, selected_tiles, _fetch_wms
from prepare_ortho import quadkey
from generate import load_config, write_sdk_project

class DummyResponse:
    def __init__(self):
        img=Image.new('RGB',(1024,1024),color=(75,160,205))
        buf=BytesIO();img.save(buf,format='PNG')
        self.content=buf.getvalue()
    def raise_for_status(self):pass
class DummySession:
    def __init__(self):self.calls=[]
    def get(self,url,params,timeout):
        self.calls.append(params)
        return DummyResponse()


def test_full_zone_ortho_is_lod20_and_circle():
    c=load_config()
    items=list(selected_tiles(*c['centre_wgs84'],3000))
    assert 30000<len(items)<55000
    assert all(len(quadkey(x,y))==20 for x,y in items)


def test_ign_wms_tiles_are_real_16bit_png(tmp_path):
    cfg=load_config()
    write_sdk_project(tmp_path,cfg)
    c=cfg['centre_wgs84']
    items=list(selected_tiles(*c,35))[:7]
    client=DummySession()
    report=build_ortho_ign(tmp_path,tuple(c),35,tiles_override=items,
                            session=client,delay=0)
    assert report['tiles_created']>0
    assert len(client.calls)>=1
    assert client.calls[0]['LAYERS']=='HR.ORTHOIMAGERY.ORTHOPHOTOS'
    assert client.calls[0]['WIDTH']=='1024'
    imgs=list((tmp_path/'PackageSources/CGL/aerial_images').glob('*.png'))
    assert imgs
    px=cv2.imread(str(imgs[0]),cv2.IMREAD_UNCHANGED)
    assert px.dtype==np.uint16 and px.shape==(256,256,4)
    assert (px[:,:,3]>0).any()
    assert ET.parse(tmp_path/'PackageSources/CGL/saintmaurice_aerial.xml').getroot().tag=='CGLBuilder'
    # Resumable: should not make WMS requests when all tiles exist.
    report2=build_ortho_ign(tmp_path,tuple(c),35,tiles_override=items,
                            session=client,delay=0)
    assert report2['wms_requests']==0
