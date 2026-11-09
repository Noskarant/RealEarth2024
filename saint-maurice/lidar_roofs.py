"""Upgrade IGN footprints using a georeferenced IGN LiDAR ground/building raster.

Input: MNT (terrain altitude) and MNS/roof (top of building), same vertical datum.
Output: enriched GeoJSON COPY; never overwrites the authoritative BD TOPO raw.
Quality gates prevent using trees or no-data as building height.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import median

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window, transform as window_transform
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.ops import transform
from pyproj import Transformer

from generate import DATA, ROOT


def sample_building(poly:Polygon,ground,roof,*, min_samples:int=8):
    """Return measured roof/ground altitudes, or None if raster coverage lacks data."""
    if ground.crs is None or roof.crs is None:
        raise ValueError('LIDAR rasters must declare CRS')
    gp=transform(Transformer.from_crs('EPSG:4326',ground.crs,always_xy=True).transform,poly)
    rp=transform(Transformer.from_crs('EPSG:4326',roof.crs,always_xy=True).transform,poly)
    def samples(dataset,p):
        minx,miny,maxx,maxy=p.bounds
        # Intersection before read prevents requests for out-of-extent raster windows.
        bounds=dataset.bounds
        minx=max(minx,bounds.left);maxx=min(maxx,bounds.right)
        miny=max(miny,bounds.bottom);maxy=min(maxy,bounds.top)
        if minx>=maxx or miny>=maxy:return np.array([],dtype=float)
        w=from_bounds(minx,miny,maxx,maxy,transform=dataset.transform)
        # floor index and round outward for full roof coverage
        r0=max(0,int(np.floor(w.row_off))); c0=max(0,int(np.floor(w.col_off)))
        r1=min(dataset.height,int(np.ceil(w.row_off+w.height)))
        c1=min(dataset.width,int(np.ceil(w.col_off+w.width)))
        win=Window(c0,r0,c1-c0,r1-r0)
        a=dataset.read(1,window=win,masked=True)
        if a.size==0:return np.array([],dtype=float)
        inside=geometry_mask([mapping(p)],out_shape=a.shape,
                             transform=window_transform(win,dataset.transform),invert=True)
        valid=inside & ~np.ma.getmaskarray(a) & np.isfinite(np.asarray(a))
        return np.asarray(a)[valid].astype(float)
    g=samples(ground,gp);r=samples(roof,rp)
    if len(g)<min_samples or len(r)<min_samples:return None
    base=float(np.median(g))
    # Class-6 building DSM pixels: top 95%, bottom 20% used for eave estimate.
    peak=float(np.percentile(r,95));eave=float(np.percentile(r,20))
    height=peak-base
    if not 2.0<=height<=55.0:return None
    # Protect from low samples in a partial DSM / canopy fragments.
    if eave<base+1 or eave>peak:eave=max(base+2,peak-2)
    return {'altitude_minimale_sol':round(base,2),
            'altitude_minimale_toit':round(eave,2),
            'altitude_maximale_toit':round(peak,2),
            'hauteur':round(height,2),
            'lidar_ground_samples':len(g),
            'lidar_roof_samples':len(r),
            'source_hauteur':'LiDAR HD raster - estimates from point classes'}


def enrich(source:Path,dtm:Path,dsm:Path,out:Path)->dict:
    fc=json.loads(source.read_text(encoding='utf-8'))
    total=0;enriched=0;unsupported=0
    with rasterio.open(dtm) as ground, rasterio.open(dsm) as roof:
        for f in fc.get('features',[]):
            g=shape(f.get('geometry'))
            if g.geom_type=='MultiPolygon':g=max(g.geoms,key=lambda p:p.area)
            if g.geom_type!='Polygon':continue
            total+=1
            data=sample_building(g,ground,roof)
            if data is None:
                unsupported+=1;continue
            f.setdefault('properties',{}).update(data)
            enriched+=1
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(fc,ensure_ascii=False),encoding='utf-8')
    report={'input':str(source),'ground_raster':str(dtm),'building_raster':str(dsm),
            'output':str(out),'polygons':total,'lidar_heights':enriched,
            'no_reliable_lidar_samples':unsupported,
            'caution':'DSM roof elevation is statistical, not photogrammetric façade reconstruction'}
    (out.parent/'lidar_roofs_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description='LiDAR HD ground/roof rasters -> enhanced IGN buildings')
    p.add_argument('--source',type=Path,default=DATA/'ign_buildings.geojson')
    p.add_argument('--mnt',type=Path,required=True,help='LiDAR HD ground-only GeoTIFF')
    p.add_argument('--mns',type=Path,required=True,help='LiDAR HD rooftop GeoTIFF')
    p.add_argument('--output',type=Path,default=DATA/'ign_buildings_lidar.geojson')
    a=p.parse_args()
    print(json.dumps(enrich(a.source,a.mnt,a.mns,a.output),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
