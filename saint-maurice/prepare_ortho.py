"""OPTIONNEL : GeoTIFF légalement réutilisable -> overlay CGL (MSFS2024).

Entrée : BD ORTHO / GeoTIFF géoréférencé, bandes RGB (ou RGBA).
Sortie : tuiles LOD20, 256x256 pixels, RGBA 16 bits (PNG quadkey),
         XML CGLBuilder et AssetGroup CGL ajouté au projet indépendant.
Ne télécharge pas d'imagerie automatiquement et ne touche pas à Community.

Validation sur FS2024 à effectuer : ce module génère les sources SDK,
mais ne peut pas vérifier le CGL compilé sur cette machine.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parent
MERC_HALF = 20037508.342789244
ZOOM = 20
TILE_PX = 256


def lonlat_tile(lon, lat, zoom=ZOOM):
    lat = min(85.05112878, max(-85.05112878, lat))
    n=2**zoom
    x=int((lon+180)/360*n)
    y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
    return x,y


def tile_bounds_3857(x,y,zoom=ZOOM):
    width=(2*MERC_HALF)/(2**zoom)
    west=-MERC_HALF+x*width
    north=MERC_HALF-y*width
    return west,north-width,west+width,north


def quadkey(x,y,zoom=ZOOM):
    result=[]
    for i in range(zoom,0,-1):
        d=0; mask=1<<(i-1)
        if (x&mask)!=0:d+=1
        if (y&mask)!=0:d+=2
        result.append(str(d))
    return ''.join(result)


def tile_range(lon,lat,radius_m,zoom=ZOOM):
    from pyproj import Transformer
    metric=Transformer.from_crs('EPSG:4326','EPSG:2154',always_xy=True)
    back=Transformer.from_crs('EPSG:2154','EPSG:4326',always_xy=True)
    xx,yy=metric.transform(lon,lat)
    west,south=back.transform(xx-radius_m,yy-radius_m)
    east,north=back.transform(xx+radius_m,yy+radius_m)
    tx1,ty1=lonlat_tile(west,north,zoom)
    tx2,ty2=lonlat_tile(east,south,zoom)
    return range(tx1,tx2+1),range(ty1,ty2+1)


def _register_cgl(out:Path,scene:str)->None:
    cgl_dir=out/'PackageSources'/'CGL'
    cgl_dir.mkdir(parents=True,exist_ok=True)
    builder=ET.Element('CGLBuilder')
    ET.SubElement(builder,'CGL',type='SecondaryAerialImage',input='Tiles',directory='aerial_images')
    ET.ElementTree(builder).write(cgl_dir/'saintmaurice_aerial.xml',encoding='utf-8',xml_declaration=True)
    pkgdef=out/'PackageDefinitions'/f'{scene}.xml'
    if not pkgdef.exists():
        raise FileNotFoundError(f'Projet bâtiments absent: {pkgdef} ; lancer generate.py all --limit 0 avant.')
    tree=ET.parse(pkgdef)
    groups=tree.getroot().find('AssetGroups')
    assert groups is not None
    if not any(g.attrib.get('Name')=='saintmaurice_ortho' for g in groups.findall('AssetGroup')):
        group=ET.SubElement(groups,'AssetGroup',Name='saintmaurice_ortho')
        ET.SubElement(group,'Type',Version='0').text='CGL'
        flags=ET.SubElement(group,'Flags')
        ET.SubElement(flags,'FSXCompatibility').text='false'
        ET.SubElement(group,'AssetDir').text='PackageSources\\CGL\\'
        ET.SubElement(group,'OutputDir').text='CGL\\'
        tree.write(pkgdef,encoding='utf-8',xml_declaration=True)


def build_cgl(geotiff:Path,out:Path,lon:float,lat:float,radius_m:float=450,
              max_tiles:int=2500,fade_m:float=40.0)->dict:
    # These large optional packages need two extra dependencies, deliberately
    # excluded from the basic buildings-only installation.
    import cv2
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_bounds
    from pyproj import Transformer
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    if not 0 < radius_m <= 3000:raise ValueError('Le rayon orthophoto doit être entre 0 et 3000 m')
    if not geotiff.is_file():raise FileNotFoundError(geotiff)
    if not (out/f"PackageDefinitions/{config['scene']}.xml").exists():
        raise ValueError('Générer la scène bâtiment avant l’ortho : generate.py all --limit 0')
    X,Y=tile_range(lon,lat,radius_m+fade_m)
    cx,cy=Transformer.from_crs('EPSG:4326','EPSG:3857',always_xy=True).transform(lon,lat)
    # Approximates the circle in EPSG3857 (corrected by the cos(latitude) factor).
    local_scale=1.0/math.cos(math.radians(lat))
    width=(2*MERC_HALF)/(2**ZOOM)
    selected=[]
    for xx in X:
        for yy in Y:
            x0,y0,x1,y1=tile_bounds_3857(xx,yy)
            dist=math.hypot(max(x0-cx,0,cx-x1),max(y0-cy,0,cy-y1))/local_scale
            if dist<=radius_m+fade_m:
                selected.append((xx,yy))
    if len(selected)>max_tiles:
        raise ValueError(f'{len(selected)} tuiles requises ; augmenter --max-tiles ({max_tiles}) en connaissance des coûts disque.')
    target=out/'PackageSources'/'CGL'/'aerial_images'
    target.mkdir(parents=True,exist_ok=True)
    # WGS/metric per pixel improves the exact circular alpha mask.
    to_l93=Transformer.from_crs('EPSG:3857','EPSG:2154',always_xy=True)
    church_x,church_y=Transformer.from_crs('EPSG:4326','EPSG:2154',always_xy=True).transform(lon,lat)
    produced=0
    with rasterio.open(geotiff) as src:
        if src.crs is None or src.count<3:raise ValueError('GeoTIFF RGB géoréférencé (au moins 3 bandes) requis')
        if src.dtypes[0] not in ('uint8','uint16'):
            raise ValueError('GeoTIFF RGB 8/16 bits requis ; convertir les bandes pour ce module')
        for tx,ty in selected:
            quad=quadkey(tx,ty)
            outfile=target/f'{quad}.png'
            if outfile.exists():
                produced+=1
                continue
            a,b,c,d=tile_bounds_3857(tx,ty)
            transf=from_bounds(a,b,c,d,TILE_PX,TILE_PX)
            rgb=[]
            for band in range(1,4):
                dst=np.zeros((TILE_PX,TILE_PX),dtype=np.uint16)
                reproject(source=rasterio.band(src,band),destination=dst,
                          src_transform=src.transform,src_crs=src.crs,
                          dst_transform=transf,dst_crs='EPSG:3857',
                          resampling=Resampling.bilinear,dst_nodata=0)
                if src.dtypes[0]=='uint8':dst=dst*257
                rgb.append(dst)
            ys,xs=np.mgrid[0:TILE_PX,0:TILE_PX]
            xx=a+(xs+.5)*(c-a)/TILE_PX
            yy=d-(ys+.5)*(d-b)/TILE_PX
            mx,my=to_l93.transform(xx,yy)
            dist=np.sqrt((mx-church_x)**2+(my-church_y)**2)
            alpha=(np.clip((radius_m-dist)/max(1.0,fade_m),0.0,1.0)*65535).astype(np.uint16)
            alpha[(rgb[0]==0)&(rgb[1]==0)&(rgb[2]==0)]=0
            if not np.any(alpha):continue
            # OpenCV PNG expects BGRA channel order and writes true uint16 PNG.
            bgra=np.dstack((rgb[2],rgb[1],rgb[0],alpha))
            if not cv2.imwrite(str(outfile),bgra,[cv2.IMWRITE_PNG_COMPRESSION,4]):
                raise OSError(f'Échec PNG: {outfile}')
            produced+=1
    if produced==0:raise RuntimeError('Aucune tuile : GeoTIFF couvre-t-il Saint-Maurice ?')
    _register_cgl(out,config['scene'])
    report={'geotiff_local':str(geotiff),'lod':ZOOM,'tiles':produced,
            'radius_m':radius_m,'edge_fade_m':fade_m,
            'valid_16bit_rgba':True,
            'sdk_status':'sources CGL seulement, compilation/validation FS2024 non effectuées',
            'license_check':'réutilisation et redistribution des images source à vérifier'}
    (out/'orthophoto_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description='GeoTIFF IGN vers CGL orthophoto FS2024')
    p.add_argument('geotiff',type=Path,help='chemin vers orthophoto géoréférencée')
    p.add_argument('--output',type=Path,default=ROOT/'output')
    p.add_argument('--radius',type=float,default=450)
    p.add_argument('--max-tiles',type=int,default=2500)
    args=p.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    print(json.dumps(build_cgl(args.geotiff,args.output,*cfg['centre_wgs84'],
                               radius_m=args.radius,max_tiles=args.max_tiles),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
