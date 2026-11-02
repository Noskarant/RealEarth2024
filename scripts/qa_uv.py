import json, glob, os
from pathlib import Path
M = Path(r'D:\RealEarth2024\project\PackageSources\Scenery\valmorel\modellib')
files = sorted(M.glob('*.gltf'))
worst = []; bad = 0; mats=set(); imgs=set()
for f in files:
    d = json.loads(f.read_text(encoding='utf-8'))
    for img in d.get('images', []): imgs.add(img['uri'])
    for m in d.get('materials', []): mats.add(m.get('name'))
    for prim in d['meshes'][0]['primitives']:
        acc = d['accessors'][prim['attributes']['TEXCOORD_0']]
        mn = acc.get('min'); mx = acc.get('max')
        if not mn or not mx: continue
        over = max(0.0, max(mx[0],mx[1]) - 1.0) + max(0.0, -min(mn[0],mn[1]))
        worst.append((over, f.name))
worst.sort(reverse=True)
print('models', len(files), 'textures', len(imgs), 'materials', len(mats))
print('UV out-of-tile worst 5:', worst[:5])
print('models with UV>1 by >1e-3:', sum(1 for o,_ in worst if o > 1e-3))
from PIL import Image
for p in sorted(M.glob('*.png')):
    try:
        with Image.open(p) as im: print(f'  {p.name:24s} {im.size} {im.mode} {p.stat().st_size//1024} KiB')
    except Exception as e: print(p.name, 'ERR', e)
