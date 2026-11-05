#!/usr/bin/env python3
"""Independent Saint-Maurice church scenery: prepare, SDK-build and optional safe install.

Requires Python 3 stdlib only; no action touches other add-ons.
Source project is bundled so this can be run standalone, outside RealEarth2024.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'config.json'
PACKAGE = 'realearth-saint-maurice-eglise'
PROJECT = ROOT / 'project'
PROJECT_XML = PROJECT / (PACKAGE + '.xml')
SCENERY = PROJECT / 'PackageSources' / 'Scenery' / 'saint_maurice_eglise' / 'scenery'
MODELLIB = PROJECT / 'PackageSources' / 'Scenery' / 'saint_maurice_eglise' / 'modellib'
OUTPUT = PROJECT / 'Packages' / PACKAGE
DIST = ROOT / 'dist' / PACKAGE
MODEL_GUID = '{1FEB53CB-518C-55EA-A216-AE1ED4F3BB65}'
INSTANCE_GUID = '{B8956246-4A30-5311-8DA7-3F52AA9CD4AC}'
VERSION = '0.1.0'

# Footprint approximations in model coordinates, after centering, meters (x,z).
# Deliberately limited to built structure; never excluding vegetation or heightmaps.
FOOTPRINT_ZONES = [
    (-15.8, 9.9, -6.4, 6.6),   # nave
    (7.3, 15.0, -11.6, -3.7), # bell tower
    (8.0, 15.9, -6.3, 6.5),   # apse
    (-0.6, 15.8, 3.8, 11.2),  # side annex
]
POLY_GUID_NAMESPACE = uuid.UUID('5bd51463-febb-5d3c-aae5-a6614df664aa')


def die(message: str) -> None:
    raise RuntimeError(message)


def load_config():
    d = json.loads(CONFIG.read_text(encoding='utf-8'))
    lat, lon = float(d['latitude']), float(d['longitude'])
    heading, agl = float(d['heading_degrees']), float(d['agl_offset_m'])
    if not all(map(math.isfinite, (lat, lon, heading, agl))):
        die('Non-finite GPS/heading/height in config.json')
    if not (45.55 < lat < 45.61 and 4.60 < lon < 4.67):
        die('GPS outside Saint-Maurice-sur-Dargoire - refusing to compile')
    if not -15 <= agl <= 15:
        die('AGL offset outside the safe range (-15 to +15m)')
    if d.get('modify_vegetation', False) or d.get('modify_terrain', False):
        die('Vegetation/terrain modifications are FORBIDDEN in this independent package')
    return d, lat, lon, heading, agl


def to_geo(x: float, z: float, lat: float, lon: float, heading: float):
    # Local approximation adequate for ~30m footprint. Verify orientation in scenery editor.
    a = math.radians(heading)
    east = x * math.cos(a) - z * math.sin(a)
    north = x * math.sin(a) + z * math.cos(a)
    return (lat + north / 111132.0, lon + east / (111320.0 * math.cos(math.radians(lat))))


def corners(zone, lat, lon, heading):
    xmin, xmax, zmin, zmax = zone
    return [to_geo(x,z,lat,lon,heading) for x,z in
            ((xmin,zmin),(xmax,zmin),(xmax,zmax),(xmin,zmax))]


def prep():
    cfg, lat, lon, heading, agl = load_config()
    if not (MODELLIB/'eglise_saint_maurice.gltf').is_file():
        die('Missing pre-exported church glTF (provided in ZIP)')
    gltf = json.loads((MODELLIB/'eglise_saint_maurice.gltf').read_text(encoding='utf-8'))
    scene_idx = gltf.get('scene', 0)
    roots = gltf['scenes'][scene_idx]['nodes']
    names = [gltf['nodes'][i].get('name','') for i in roots]
    if any(s.lower() == 'sol' for s in names):
        die('Ground slab is still enabled in active GLTF scene')
    if not any('eglise' in x.lower() for x in names):
        die('Expected centred church model root missing')
    if len(gltf.get('images', [])) < 5:
        die('Missing external church photo texture images')
    for t in gltf['images']:
        f = MODELLIB / t['uri']
        if not f.is_file() or not f.with_name(f.name + '.xml').is_file():
            die('Missing texture or MSFS sidecar: '+str(f))
    if not (MODELLIB/'eglise_saint_maurice.bin').is_file():
        die('Missing source mesh binary')

    SCENERY.mkdir(parents=True, exist_ok=True)
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             '<FSData version="9.0">',
             f'  <SceneryObject instanceId="{INSTANCE_GUID}" lat="{lat:.9f}" lon="{lon:.9f}" '
             f'alt="{agl:.3f}" pitch="0" bank="0" heading="{heading%360:.4f}" '
             'altitudeIsAgl="TRUE" snapToGround="TRUE" snapToNormal="FALSE" imageComplexity="NORMAL">',
             f'    <LibraryObject name="{MODEL_GUID}" scale="1.000000"/>',
             '  </SceneryObject>']

    if cfg.get('remove_default_buildings', True):
        for i, zone in enumerate(FOOTPRINT_ZONES):
            pts = corners(zone,lat,lon,heading)
            poly_guid = '{'+str(uuid.uuid5(POLY_GUID_NAMESPACE,'church zone '+str(i))).upper()+'}'
            parts.extend([
                f'  <Polygon version="0.4.0" displayName="Eglise: bati natif seulement {i+1}">',
                f'    <Attribute name="UniqueGUID" guid="{{359C73E8-06BE-4FB2-ABCB-EC942F7761D0}}" type="GUID" value="{poly_guid}"/>',
                '    <Attribute name="ExcludeDetectedBuildings" guid="{5C1A2387-1F07-47DF-A569-962CF6258E55}" type="UINT8" value="1"/>',
                '    <Attribute name="ExcludeOSMBuildings" guid="{F3C2635D-9F2F-458F-8663-90B3837BED09}" type="UINT8" value="1"/>',
                # Deliberately DO NOT set ExcludeTIN, vegetation, flatten, roads, tree objects.
            ])
            for p_lat,p_lon in pts:
                parts.append(f'    <Vertex lat="{p_lat:.9f}" lon="{p_lon:.9f}"/>')
            parts.append('  </Polygon>')
            if cfg.get('exclude_placed_buildings', True):
                minlat,maxlat=min(v[0] for v in pts),max(v[0] for v in pts)
                minlon,maxlon=min(v[1] for v in pts),max(v[1] for v in pts)
                parts.append(f'  <ExclusionRectangle displayName="Eglise: objets batiments {i+1}" '
                             f'latitudeMinimum="{minlat:.9f}" latitudeMaximum="{maxlat:.9f}" '
                             f'longitudeMinimum="{minlon:.9f}" longitudeMaximum="{maxlon:.9f}" '
                             'excludeAllObjects="FALSE" excludeGenericBuildingObjects="TRUE" '
                             'excludeLibraryObjects="TRUE" excludeTreeObjects="FALSE"/>')
    parts.append('</FSData>')
    scenery_xml = SCENERY / 'eglise_placement.xml'
    scenery_xml.write_text('\n'.join(parts)+'\n',encoding='utf-8')

    definitions = PROJECT / 'PackageDefinitions'
    definitions.mkdir(parents=True,exist_ok=True)
    (definitions/(PACKAGE+'.xml')).write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<AssetPackage Version="{VERSION}">
 <ItemSettings><ContentType>SCENERY</ContentType>
  <Title>Saint-Maurice-sur-Dargoire - Eglise seule</Title>
  <Manufacturer>RealEarth</Manufacturer><Creator>RealEarth2024</Creator>
 </ItemSettings>
 <Flags><VisibleInStore>false</VisibleInStore><CanBeReferenced>false</CanBeReferenced></Flags>
 <PackageOrderHint>CUSTOM_SCENERY_PATCH</PackageOrderHint>
 <AssetGroups>
  <AssetGroup Name="saint_maurice_eglise_modellib"><Type Version="1">ModelLib</Type>
   <Flags><FSXCompatibility>false</FSXCompatibility></Flags>
   <AssetDir>PackageSources\\Scenery\\saint_maurice_eglise\\modellib\\</AssetDir>
   <OutputDir>Scenery\\saint_maurice_eglise\\modellib\\</OutputDir>
  </AssetGroup>
  <AssetGroup Name="saint_maurice_eglise_placement"><Type Version="0">BGL</Type>
   <Flags><FSXCompatibility>false</FSXCompatibility></Flags>
   <AssetDir>PackageSources\\Scenery\\saint_maurice_eglise\\scenery\\</AssetDir>
   <OutputDir>Scenery\\saint_maurice_eglise\\scenery\\</OutputDir>
  </AssetGroup>
 </AssetGroups>
</AssetPackage>
''',encoding='utf-8')
    PROJECT_XML.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Project Version="2" Name="{PACKAGE}" FolderName="Packages" MetadataFolderName="PackagesMetadata">
 <OutputDirectory>.</OutputDirectory><TemporaryOutputDirectory>_PackageInt</TemporaryOutputDirectory>
 <Packages><Package>PackageDefinitions\\{PACKAGE}.xml</Package></Packages>
 <PublishingGroups/>
</Project>
''',encoding='utf-8')
    for f in (scenery_xml,PROJECT_XML,definitions/(PACKAGE+'.xml'),MODELLIB/'eglise_saint_maurice.xml'):
        ET.parse(f)
    xml=scenery_xml.read_text(encoding='utf-8')
    if ('VegetationDensity' in xml or 'ExcludeTIN' in xml or 'excludeAllObjects="TRUE"' in xml or
        'excludeTreeObjects="TRUE"' in xml or 'FlattenMode' in xml):
        die('Unsafe scene edits detected: abort')
    print('PREPARATION OK: church only; 8 textures; artificial ground slab disabled')
    print(f'GPS: {lat:.8f}, {lon:.8f}; heading {heading:.1f} deg; AGL {agl:+.1f}m')
    print('Default building exclusion:',cfg.get('remove_default_buildings',True))
    print('Vegetation/terrain changes: NONE')


def find_sdk(given: str | None):
    paths = [given,os.environ.get('FSPACKAGETOOL'),
             r'D:\RealEarth2024\build\tools\fspackagetool.exe',
             r'C:\MSFS SDK\Tools\bin\fspackagetool.exe']
    for p in paths:
        if p and Path(p).is_file():
            return Path(p)
    die('SDK fspackagetool.exe not found. Use --sdk "C:\\path\\fspackagetool.exe" '
        'or set FSPACKAGETOOL. This ZIP is not a precompiled Community addon.')


def validate_package(p: Path):
    manifest=p/'manifest.json';layout=p/'layout.json'
    if not manifest.is_file() or not layout.is_file():
        die('SDK output is missing manifest.json/layout.json')
    mf=json.loads(manifest.read_text(encoding='utf-8-sig'))
    ly=json.loads(layout.read_text(encoding='utf-8-sig'))
    if mf.get('package_version')!=VERSION:
        die(f'Unexpected package version: {mf.get("package_version")}')
    entries=ly.get('content')
    if not isinstance(entries,list) or len(entries)<3:
        die('SDK layout too small / missing compiled assets')
    for f in entries:
        path=p/f['path']
        if not path.is_file() or path.stat().st_size!=f['size']:
            die('Layout mismatch: '+f['path'])
    bgl=[f for f in p.rglob('*') if f.suffix.lower()=='.bgl' and f.stat().st_size>0]
    ktx=[f for f in p.rglob('*') if f.suffix.lower()=='.ktx2' and f.stat().st_size>0]
    if len(bgl)<2 or len(ktx)<1:
        die(f'SDK compilation incomplete: {len(bgl)} BGL and {len(ktx)} KTX2')
    if not any(f.name.lower()=='modellib.bgl' and f.stat().st_size>1000 for f in bgl):
        die('Invalid / empty model library')
    print('COMPILATION OK:',len(bgl),'BGL,',len(ktx),'KTX2; layout verified')


def build(given_sdk=None):
    sdk=find_sdk(given_sdk)
    # Remove only our own stale SDK outputs to prevent accidental old install.
    if OUTPUT.is_dir():
        shutil.rmtree(OUTPUT)
    subprocess.run([str(sdk),str(PROJECT_XML)],cwd=PROJECT,check=True)
    validate_package(OUTPUT)
    if DIST.is_dir():
        shutil.rmtree(DIST)
    DIST.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(OUTPUT,DIST)
    print('Independent compiled package:',DIST)


def sim_running():
    if os.name != 'nt':return False
    p=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,check=False)
    val=p.stdout.lower()
    return 'flightsimulator2024.exe' in val or 'flightsimulator.exe' in val


def find_community(user_input):
    if user_input:
        p=Path(user_input)
        if p.is_dir() and p.name.lower() in {'community','community2024'}:
            return p
        die('Invalid Community path: '+str(p))
    home=Path.home()
    local=Path(os.environ.get('LOCALAPPDATA',str(home/'AppData/Local')))
    appdata=Path(os.environ.get('APPDATA',str(home/'AppData/Roaming')))
    locations=[local/'Packages/Microsoft.Limitless_8wekyb3d8bbwe/LocalCache/UserCfg.opt',
               appdata/'Microsoft Flight Simulator 2024/UserCfg.opt']
    choices=[]
    import re
    for f in locations:
        if f.is_file():
            m=re.search(r'^\s*InstalledPackagesPath\s+"([^"]+)"',f.read_text(errors='replace'),re.M)
            if m:
                base=Path(os.path.expandvars(m.group(1)))
                choices.extend([base/'Community',base/'Community2024'])
    choices.extend([local/'Packages/Microsoft.Limitless_8wekyb3d8bbwe/LocalCache/Packages/Community',
                    appdata/'Microsoft Flight Simulator 2024/Packages/Community'])
    found=list(dict.fromkeys(x for x in choices if x.is_dir()))
    existing=[x for x in found if (x/PACKAGE).is_dir()]
    if len(existing)==1:return existing[0]
    if len(found)==1:return found[0]
    print('Please provide a specific --community "...\\Community" path.')
    for p in found:print(' candidate:',p)
    die('Community path missing or ambiguous; nothing installed')


def install(community):
    if sim_running():die('Close FS2024 before installation; no files changed')
    validate_package(DIST)
    targetdir=find_community(community)
    otherdir=targetdir.parent/('Community2024' if targetdir.name.lower()=='community' else 'Community')
    if (otherdir/PACKAGE).is_dir():
        die('Duplicate church package in the other Community folder: '+str(otherdir))
    target=targetdir/PACKAGE
    tag=uuid.uuid4().hex[:10]
    staging=targetdir/('.'+PACKAGE+'.stage_'+tag)
    old=targetdir/('.'+PACKAGE+'.old_'+tag)
    moved=False;installed=False
    try:
        shutil.copytree(DIST,staging)
        validate_package(staging)
        if sim_running():die('FS2024 started while copying; cancelling')
        if target.is_dir():
            backup=ROOT/'backups'/(PACKAGE+'_'+time.strftime('%Y%m%d_%H%M%S')+'_'+tag)
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(target,backup)
            print('Previous CHURCH-only package backup:',backup)
            target.rename(old);moved=True
        elif target.exists():die('Destination exists but is not a directory')
        staging.rename(target);installed=True
        if old.exists():shutil.rmtree(old)
        print('SUCCESS. Installed the church package ONLY:',target)
        print('Madone, benches, trees and all other packages were NOT touched.')
    except Exception:
        if moved and not installed and old.exists():old.rename(target)
        raise
    finally:
        if staging.is_dir():shutil.rmtree(staging,ignore_errors=True)


def main():
    parser=argparse.ArgumentParser(description='Standalone church scene for MSFS 2024')
    parser.add_argument('--build',action='store_true',help='Compile using MSFS 2024 SDK')
    parser.add_argument('--install',action='store_true',help='Compile then install this church only')
    parser.add_argument('--community',help='Exact active Community directory')
    parser.add_argument('--sdk',help='Exact fspackagetool.exe path')
    args=parser.parse_args()
    prep()
    if args.build or args.install:
        build(args.sdk)
    if args.install:
        install(args.community)
    if not args.build and not args.install:
        print('Preparation/static checks only. To build: --build. To install: --install')

if __name__ == '__main__':
    try:
        main()
    except (OSError,KeyError,ValueError,RuntimeError,subprocess.CalledProcessError) as ex:
        print('ERROR:',ex,file=sys.stderr)
        sys.exit(1)
