import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, mapping
from shapely.ops import transform
from generate import TO_WGS
from lidar_roofs import enrich


def test_lidar_updates_height_without_touching_original(tmp_path):
    x,y=TO_WGS.inverse if False else (798000,6512000)
    poly=transform(TO_WGS.transform,box(x+10,y+10,x+24,y+24))
    fc={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'cleabs':'test'},
                                              'geometry':mapping(poly)}]}
    source=tmp_path/'source.geojson';source.write_text(json.dumps(fc))
    tr=from_origin(x,y+50,1,1)
    for f,v in [('ground.tif',485),('roof.tif',493)]:
        with rasterio.open(tmp_path/f,'w',driver='GTiff',height=50,width=50,
                             count=1,dtype='float32',crs='EPSG:2154',
                             transform=tr,nodata=-9999) as ds:
            ds.write(np.full((50,50),v,dtype='float32'),1)
    out=tmp_path/'out.geojson'
    r=enrich(source,tmp_path/'ground.tif',tmp_path/'roof.tif',out)
    assert r['lidar_heights']==1
    assert json.loads(out.read_text())['features'][0]['properties']['hauteur']==8.0
    assert 'hauteur' not in json.loads(source.read_text())['features'][0]['properties']
