from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import rasterio
from rasterio.transform import from_origin
from lidar_mosaic import make_mosaic

def test_mosaic_tiles_without_destroying_sources(tmp_path):
    tiles=[]
    for i in range(2):
        f=tmp_path/f'{i}.tif'
        with rasterio.open(f,'w',driver='GTiff',width=10,height=10,
                           count=1,crs='EPSG:2154',transform=from_origin(700000+i*10,6500000,1,1),
                           dtype='float32',nodata=-9999) as ds:
            ds.write(np.full((10,10),i+100,dtype='float32'),1)
        tiles.append(f)
    target=tmp_path/'out'/'mosaic.tif'
    info=make_mosaic(tiles,target)
    assert info['shape']==[1,10,20]
    with rasterio.open(target) as src:
        a=src.read(1)
        assert a[3,3]==100 and a[3,15]==101
    assert all(f.exists() for f in tiles)
