import json, math
from pathlib import Path
import numpy as np

ms = Path(r'D:\RealEarth2024\project\PackageSources\Scenery\valmorel\modellib')
files = sorted(ms.glob('*.gltf'))
print('gltf files', len(files))
bad = []
tot = 0
maxv = 0
for f in files:
    d = json.loads(f.read_text(encoding='utf-8'))
    bsize = f.with_suffix('.bin').stat().st_size
    if bsize != d['buffers'][0]['byteLength']:
        bad.append((f.name, 'binsize', bsize, d['buffers'][0]['byteLength']))
    for a in d['accessors'][::4]:
        mn, mx = a.get('min'), a.get('max')
        if not mn or not mx:
            bad.append((f.name, 'nobounds'))
            break
        if any(math.isnan(v) or math.isinf(v) for v in mn + mx):
            bad.append((f.name, 'nan'))
            break
        maxv = max(maxv, max(mx) - min(mn))
    for im in d.get('images', []):
        if not (ms / im['uri']).exists():
            bad.append((f.name, 'missingtex', im['uri']))
    tot += len(d['meshes'][0]['primitives'])
print('primitives', tot, 'max extent', maxv)
print('bad', bad[:10], len(bad))
f = ms / 'core_0000.gltf'
d = json.loads(f.read_text())
print(f.name, 'materials', len(d['materials']), 'prims', len(d['meshes'][0]['primitives']))
print('node', d['nodes'])
