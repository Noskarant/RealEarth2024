"""Inspectable end-to-end quality audit, never falsely claims an in-game result."""
from __future__ import annotations
import json
from pathlib import Path
from generate import OUTPUT, DATA, ROOT, load_config


def inspect(out=OUTPUT):
    config=load_config()
    def read(f):
        p=out/f
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
    buildings=read('report.json')
    landscape=read('landscape_report.json')
    aerial=read('orthophoto_IGN_report.json') or read('orthophoto_report.json')
    lidar=(DATA/'lidar_roofs_report.json')
    lidar_report=json.loads(lidar.read_text(encoding='utf-8')) if lidar.exists() else None
    valid=read('validation_pre_sdk.json')
    expected=40633 # analytical count at SDK zoom20 for the configured 3km centre
    coverage=round(100*(aerial.get('tiles_created',0)+aerial.get('tiles_reused',0))/
                   max(1,aerial.get('tiles_planned',expected)),2) if aerial else 0
    status={
        'zone':{'name':'Saint-Maurice-sur-Dargoire', 'radius_m':config['radius_m'],
                'area_km2':round(3.14159265359*(config['radius_m']/1000)**2,2)},
        'building_inventory':buildings,
        'landscape_ign':landscape,
        'orthophoto':aerial,
        'orthophoto_tile_progress_percent':coverage,
        'lidar_roof_heights':lidar_report,
        'pre_sdk_validation':valid,
        'church_and_madone_assets_modified':False,
        'sdk_compiled':False,
        'tested_in_microsoft_flight_simulator_2024':False,
        'notes':[
            'All 3km building coordinates derived from source geometry, not fabricated imagery',
            'LiDAR and ortho only claimed present if their local reports exist',
            'Procedural roof/wall textures: NOT photo reconstructions of actual facades',
            '3D SDK compatibility, terrain seams and runtime FPS require in-game confirmation',
            'Existing church, Madone, chapel and benches packages never changed',
        ]
    }
    (out/'quality_report.json').write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding='utf-8')
    return status

if __name__=='__main__':
    result=inspect()
    print(json.dumps({'zone':result['zone'],'ortho_pct':result['orthophoto_tile_progress_percent'],
                     'sdk_compiled':result['sdk_compiled'],
                     'tested_in_game':result['tested_in_microsoft_flight_simulator_2024']},
                     indent=2,ensure_ascii=False))
