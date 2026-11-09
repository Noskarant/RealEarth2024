"""Export real 3 km radius and monument protection envelopes for QGIS QA."""
from pathlib import Path
import json
from shapely.geometry import Point, mapping
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
TO_L93=Transformer.from_crs('EPSG:4326','EPSG:2154',always_xy=True)
TO_WGS=Transformer.from_crs('EPSG:2154','EPSG:4326',always_xy=True)

def feature(name, lon, lat, radius, kind):
    x,y=TO_L93.transform(lon,lat)
    circle=Point(x,y).buffer(radius,quad_segs=90)
    return {'type':'Feature','properties':{'name':name,'kind':kind,'radius_m':radius},
            'geometry':mapping(transform(TO_WGS.transform,circle))}

def main():
    lon,lat=C['centre_wgs84'];radius=C['radius_m']
    output=ROOT/'data'/'cartographie'
    output.mkdir(parents=True,exist_ok=True)
    outputs={
        'zone_3km.geojson':[feature('Saint-Maurice + 3 km',lon,lat,radius,'scene')],
        'monuments_a_preserver.geojson':[feature(m['name'],m['lon'],m['lat'],m['radius_m'],'protection') for m in C['monuments_proteges']]
    }
    for name,features in outputs.items():
        target=output/name
        target.write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,indent=2),encoding='utf-8')
        print(target)

if __name__=='__main__':main()
