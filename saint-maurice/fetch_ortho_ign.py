"""Full 3km, LOD20, 16-bit RGBA CGL source images from IGN public WMS.

No Google/Bing tiles are downloaded or redistributed. IGN attribution and source
terms are written to a provenance manifest. WMS blocks contain 4x4 CGL tiles.
Resumable. The resulting 3 km disk footprint can be several gigabytes.

SDK: https://docs.flightsimulator.com/msfs2024/flighting/devmode/editors/project-editor/file-formats/cgl-files/
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
import json
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image
import requests

from prepare_ortho import lonlat_tile, tile_bounds_3857, quadkey, _register_cgl, MERC_HALF, ZOOM, TILE_PX
from generate import load_config, OUTPUT
from pyproj import Transformer

WMS = 'https://data.geopf.fr/wms-r/wms'
LAYER = 'HR.ORTHOIMAGERY.ORTHOPHOTOS'
BLOCK = 4


def selected_tiles(lon: float, lat:float, radius_m:float, fade_m:float=25.0, zoom:int=ZOOM):
    """Conservative circular selection in Web Mercator, with real-world scale."""
    cx,cy=Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform(lon,lat)
    pixel_width=2*MERC_HALF/(2**zoom)
    scale=math.cos(math.radians(lat))
    radius_merc=(radius_m+fade_m)/scale
    nx=math.floor((cx+MERC_HALF-radius_merc)/pixel_width)
    xx=math.ceil((cx+MERC_HALF+radius_merc)/pixel_width)
    ny=math.floor((MERC_HALF-cy-radius_merc)/pixel_width)
    yy=math.ceil((MERC_HALF-cy+radius_merc)/pixel_width)
    for tx in range(nx,xx+1):
        for ty in range(ny,yy+1):
            a,b,c,d=tile_bounds_3857(tx,ty,zoom)
            nearest_x=max(a,min(cx,c))
            nearest_y=max(b,min(cy,d))
            if math.hypot(nearest_x-cx,nearest_y-cy)*scale <= radius_m+fade_m:
                yield tx,ty


def _fetch_wms(block_x:int,block_y:int,session,delay:float,
               block_size:int=BLOCK,zoom:int=ZOOM)->Image.Image:
    a,b,_,d=tile_bounds_3857(block_x,block_y,zoom)
    # Bounds of bottom-right tile supply the EAST edge and its SOUTH edge.
    _,b, c,_ = tile_bounds_3857(block_x+block_size-1,block_y+block_size-1,zoom)
    params={'SERVICE':'WMS','VERSION':'1.3.0','REQUEST':'GetMap',
            'LAYERS':LAYER,'STYLES':'','CRS':'EPSG:3857',
            'BBOX':f'{a:.4f},{b:.4f},{c:.4f},{d:.4f}',
            'WIDTH':str(TILE_PX*block_size),'HEIGHT':str(TILE_PX*block_size),
            'FORMAT':'image/png','TRANSPARENT':'FALSE'}
    for attempt in range(5):
        try:
            r=session.get(WMS,params=params,timeout=120)
            r.raise_for_status()
            if not r.content.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('IGN WMS not PNG: '+r.content[:180].decode('utf-8','replace'))
            img=Image.open(BytesIO(r.content)).convert('RGB')
            if img.size != (TILE_PX*block_size,TILE_PX*block_size):
                raise ValueError('WMS incorrect dimensions: '+str(img.size))
            if delay>0:time.sleep(delay)
            return img
        except (requests.RequestException,ValueError,OSError):
            if attempt==4:raise
            time.sleep(2*(attempt+1))
    raise RuntimeError('unexpected')


def build_ortho_ign(out:Path,center:tuple[float,float],radius_m:float=3000,
                    *,max_tiles:int=60000,session=None,delay:float=0.3,
                    fade_m:float=25,block_size:int=BLOCK,
                    dry_run:bool=False,tiles_override=None)->dict:
    import cv2
    lon,lat=center
    if not 0<radius_m<=3000:raise ValueError('radius must be <= 3000m')
    cfg=load_config()
    if not dry_run and not (out/'PackageDefinitions'/f'{cfg["scene"]}.xml').exists():
        raise FileNotFoundError('Build buildings before aerial; missing project XML')
    tiles=list(tiles_override) if tiles_override is not None else list(selected_tiles(lon,lat,radius_m,fade_m))
    if len(tiles)>max_tiles:raise ValueError(f'{len(tiles)} tiles > {max_tiles} limit')
    groups=defaultdict(list)
    for tx,ty in tiles:groups[(tx//block_size*block_size,ty//block_size*block_size)].append((tx,ty))
    report={'source':'IGN Geoplateforme WMS BD ORTHO 20 cm',
        'url':WMS,'layer':LAYER,'license':'IGN Licence Ouverte 2.0; credit © IGN',
        'quadkey_zoom':ZOOM,'tile_pixels':256,'tile_format':'PNG 16-bit RGBA',
        'tiles_planned':len(tiles),'wms_requests_max':len(groups),
        'radius_m':radius_m,'fade_m':fade_m,'output':str(out),
        'status':'dry run' if dry_run else 'source images generated; CGL SDK build / in-game validation pending'}
    if dry_run:return report
    dst=out/'PackageSources'/'CGL'/'aerial_images';dst.mkdir(parents=True,exist_ok=True)
    cx,cy=Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform(lon,lat)
    scale=math.cos(math.radians(lat))
    px_width=2*MERC_HALF/(2**ZOOM)/TILE_PX
    client=session or requests.Session()
    built=0;skipped=0;wms_calls=0
    for n,((bx,by),pieces) in enumerate(sorted(groups.items()),1):
        pending=[(x,y) for x,y in pieces if not (dst/f'{quadkey(x,y)}.png').exists()]
        skipped+=len(pieces)-len(pending)
        if not pending:continue
        img=_fetch_wms(bx,by,client,delay,block_size=block_size)
        wms_calls+=1
        for tx,ty in pending:
            start_x=(tx-bx)*TILE_PX;start_y=(ty-by)*TILE_PX
            pixel=np.asarray(img.crop((start_x,start_y,start_x+TILE_PX,start_y+TILE_PX)),dtype=np.uint8)
            west,south,east,north=tile_bounds_3857(tx,ty)
            gx=west+(np.arange(TILE_PX)+.5)*px_width
            gy=north-(np.arange(TILE_PX)+.5)*px_width
            # Web Mercator ground distance approximation for clipping only;
            # the source ortho itself is georeferenced exactly in EPSG3857.
            distance=np.sqrt((gx[None,:]-cx)**2+(gy[:,None]-cy)**2)*scale
            alpha=(np.clip((radius_m+fade_m-distance)/max(1.,fade_m),0.,1.)*65535).astype(np.uint16)
            if not alpha.any():continue
            rgba16=(pixel.astype(np.uint16)*257)
            bgra=np.dstack((rgba16[:,:,2],rgba16[:,:,1],rgba16[:,:,0],alpha))
            file=dst/f'{quadkey(tx,ty)}.png'
            if not cv2.imwrite(str(file),bgra,[cv2.IMWRITE_PNG_COMPRESSION,4]):
                raise OSError(f'PNG write failed: {file}')
            built+=1
        if n%50==0:
            print(f'IGN orthophoto: WMS blocks {n}/{len(groups)}, PNG new {built}, reused {skipped}',flush=True)
    _register_cgl(out,cfg['scene'])
    report.update({'tiles_created':built,'tiles_reused':skipped,
                   'wms_requests':wms_calls,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()})
    (out/'orthophoto_IGN_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description='IGN BD ORTHO WMS -> full-radius FS2024 CGL tiles')
    p.add_argument('--output',type=Path,default=OUTPUT)
    p.add_argument('--radius',type=float,default=3000)
    p.add_argument('--max-tiles',type=int,default=60000)
    p.add_argument('--delay',type=float,default=.3)
    p.add_argument('--dry-run',action='store_true',help='Estimate required tiles, no internet or files')
    a=p.parse_args();cfg=load_config()
    r=build_ortho_ign(a.output,tuple(cfg['centre_wgs84']),a.radius,
                      max_tiles=a.max_tiles,delay=a.delay,dry_run=a.dry_run)
    print(json.dumps(r,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
