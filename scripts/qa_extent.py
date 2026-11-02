import json
from pathlib import Path

ms = Path(r'D:\RealEarth2024\project\PackageSources\Scenery\valmorel\modellib')
rows = []
for f in sorted(ms.glob('*.gltf')):
    d = json.loads(f.read_text(encoding='utf-8'))
    for a in d['accessors'][::4]:
        mn, mx = a['min'], a['max']
        ext = [round(mx[i] - mn[i], 1) for i in range(3)]
        rows.append((max(ext), f.name, ext, [round(v, 1) for v in mn], [round(v, 1) for v in mx]))
rows.sort(reverse=True)
for r in rows[:15]:
    print(r)
