"""Mosaic official LiDAR HD MNT/MNS 0.5m GeoTIFF tiles non-destructively."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import rasterio
from rasterio.merge import merge


def make_mosaic(files:list[Path],target:Path)->dict:
    files=[Path(f) for f in files]
    if not files:raise ValueError('No input GeoTIFF files')
    sources=[]
    try:
        sources=[rasterio.open(f) for f in files]
        if any(src.crs!=sources[0].crs for src in sources):
            raise ValueError('LiDAR tiles have different CRSs; reproject first')
        data,tr=merge(sources,masked=False,nodata=-9999.0)
        if data.shape[0]!=1:raise ValueError('Expected single-band height GeoTIFF')
        profile=sources[0].profile.copy()
        profile.update(driver='GTiff',height=data.shape[1],width=data.shape[2],
                       count=1,transform=tr,dtype='float32',nodata=-9999.,
                       compress='deflate',predictor=3,tiled=True,blockxsize=256,blockysize=256)
        target.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(target,'w',**profile) as dst:dst.write(data.astype('float32'))
        return {'mosaic':str(target),'tiles':len(files),'shape':list(data.shape),
                'source_crs':str(sources[0].crs)}
    finally:
        for x in sources:x.close()


def main():
    p=argparse.ArgumentParser(description='Mosaic LiDAR HD GeoTIFF tiles')
    p.add_argument('folder',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    files=sorted(a.folder.glob('*.tif'))
    print(json.dumps(make_mosaic(files,a.output),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
