"""Convert public IGN LiDAR HD .LAZ tiles into 1m MNT/roof DSM GeoTIFF.

LAS classes 2=ground and 6=building according to LAS classification. Files with
other / unclassified conventions need manual review; do not invent roof heights.
Processes LAS/LAZ in chunks to fit in ~32GB RAM; accepts several .laz paths.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin
import rasterio
from scipy.ndimage import distance_transform_edt

from generate import load_config, DATA, TO_L93


def convert_laz(files:list[Path],out_dir:Path,*,resolution_m:float=1.,radius_m:float=3000.,
                center_wgs84:tuple[float,float]|None=None,fill_ground_m:float=25.0)->dict:
    import laspy
    if not files:raise ValueError('No LiDAR tiles specified')
    if not .5<=resolution_m<=3:raise ValueError('Resolution must be between 0.5 and 3m')
    cfg=load_config()
    lon,lat=center_wgs84 or tuple(cfg['centre_wgs84'])
    cx,cy=TO_L93.transform(lon,lat)
    margin=25
    side=2*(radius_m+margin)
    size=math.ceil(side/resolution_m)
    left=cx-side/2; top=cy+side/2
    n=size*size
    # 1m, 6.05km side: ~300 MB initial accumulator arrays, plus temporary buffers.
    ground_sum=np.zeros(n,dtype=np.float64)
    ground_count=np.zeros(n,dtype=np.uint32)
    roof_max=np.full(n,-np.inf,dtype=np.float32)
    classes={'ground':0,'building':0,'other':0}
    total=0
    for fp in files:
        fp=Path(fp)
        with laspy.open(fp) as reader:
            src_crs=reader.header.parse_crs()
            if src_crs is None:raise ValueError(f'{fp}: missing LAS CRS')
            to_l93=Transformer.from_crs(src_crs,'EPSG:2154',always_xy=True)
            for points in reader.chunk_iterator(1_000_000):
                xs,ys=to_l93.transform(points.x,points.y)
                zs=np.asarray(points.z,dtype=np.float64)
                cls=np.asarray(points.classification,dtype=np.uint8)
                cols=np.floor((xs-left)/resolution_m).astype(np.int64)
                rows=np.floor((top-ys)/resolution_m).astype(np.int64)
                valid=(cols>=0)&(cols<size)&(rows>=0)&(rows<size)&(np.isfinite(zs))
                flat=rows[valid]*size+cols[valid]
                vals=zs[valid];codes=cls[valid]
                total+=len(vals)
                ground=(codes==2);building=(codes==6)
                classes['ground']+=int(ground.sum());classes['building']+=int(building.sum())
                classes['other']+=int(len(codes)-ground.sum()-building.sum())
                if ground.any():
                    ground_sum+=np.bincount(flat[ground],weights=vals[ground],minlength=n)
                    ground_count+=np.bincount(flat[ground],minlength=n).astype(np.uint32)
                if building.any():
                    np.maximum.at(roof_max,flat[building],vals[building].astype(np.float32))
    if classes['ground']==0 or classes['building']==0:
        raise ValueError('LiDAR tiles have no class 2 ground or class 6 buildings; validate classification')
    ground=np.full(n,np.nan,dtype=np.float32)
    valid=ground_count>0
    ground[valid]=(ground_sum[valid]/ground_count[valid]).astype(np.float32)
    grid=ground.reshape(size,size)
    # A light nearest-ground fill supports building footprints with no ground hits.
    # The fill is bounded; gaps beyond 25m remain unavailable, never invented.
    nodata=~np.isfinite(grid)
    if nodata.any():
        dist,nearest=distance_transform_edt(nodata,return_indices=True)
        fill=(nodata)&(dist*resolution_m<=fill_ground_m)
        grid[fill]=grid[tuple(idx[fill] for idx in nearest)]
        del nearest,dist
    roof=roof_max.reshape(size,size)
    t=from_origin(left,top,resolution_m,resolution_m)
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    for name,a in [('mnt_lidar_1m.tif',grid),('mns_toitures_lidar_1m.tif',roof)]:
        arr=np.where(np.isfinite(a),a,-9999.).astype('float32')
        with rasterio.open(out_dir/name,'w',driver='GTiff',height=size,width=size,
                           count=1,dtype='float32',crs='EPSG:2154',
                           transform=t,nodata=-9999.,compress='deflate',
                           predictor=3,tiled=True,blockxsize=256,blockysize=256) as ds:
            ds.write(arr,1)
    report={'source_files':[str(x) for x in files],'resolution_m':resolution_m,
            'raster_size_px':[size,size],'counts':classes,'points_in_envelope':total,
            'outputs':{'mnt':str(out_dir/'mnt_lidar_1m.tif'),
                       'mns':str(out_dir/'mns_toitures_lidar_1m.tif')},
            'warning':'Only LAS class 2 ground and class 6 buildings; roof accuracy must be inspected'}
    (out_dir/'lidar_rasterization_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description='IGN LiDAR HD LAZ tiles -> MNT/MNS 1m')
    p.add_argument('files',type=Path,nargs='+')
    p.add_argument('--output',type=Path,default=DATA/'lidar')
    p.add_argument('--resolution',type=float,default=1.)
    a=p.parse_args()
    print(json.dumps(convert_laz(a.files,a.output,resolution_m=a.resolution),indent=2,ensure_ascii=False))

if __name__=='__main__':main()
