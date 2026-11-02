"""Small offline QA renderer: glTF -> orthographic shaded PNG.

Not a simulator substitute, but it catches gross geometry/orientation errors
before compiling.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

MODEL_DIR = Path(r'D:\RealEarth2024\project\PackageSources\Scenery\valmorel\modellib')


def load_model(name):
    d = json.loads((MODEL_DIR / f'{name}.gltf').read_text(encoding='utf-8'))
    blob = (MODEL_DIR / f'{name}.bin').read_bytes()
    prims = []
    for prim in d['meshes'][0]['primitives']:
        acc = d['accessors'][prim['attributes']['POSITION']]
        bv = d['bufferViews'][acc['bufferView']]
        pos = np.frombuffer(blob, dtype='<f4', count=acc['count'] * 3,
                            offset=bv.get('byteOffset', 0) + acc.get('byteOffset', 0)).reshape(-1, 3)
        iacc = d['accessors'][prim['indices']]
        ibv = d['bufferViews'][iacc['bufferView']]
        idx = np.frombuffer(blob, dtype='<u4', count=iacc['count'],
                            offset=ibv.get('byteOffset', 0) + iacc.get('byteOffset', 0))
        mat = d['materials'][prim['material']]
        pbr = mat.get('pbrMetallicRoughness', {})
        color = np.array(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3])
        tex = pbr.get('baseColorTexture')
        if tex is not None:
            uri = d['images'][d['textures'][tex['index']]['source']]['uri']
            with Image.open(MODEL_DIR / uri) as im:
                avg = np.asarray(im.convert('RGB').resize((1, 1), Image.BOX)).reshape(3) / 255.0
            color = color * avg
        prims.append((pos.astype(np.float64), idx, color))
    return prims


def render(name, out, mode='oblique', size=(1200, 900), margin=0.05):
    prims = load_model(name)
    allp = np.concatenate([p[0] for p in prims])
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    center = (lo + hi) / 2
    if mode == 'top':
        d = np.array([0.0, 1.0, 0.0])
    else:
        az = math.radians(315)
        el = math.radians(32)
        d = np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])
    d = d / np.linalg.norm(d)
    right = np.cross(np.array([0.0, 1.0, 0.0]), d)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(d, right)
    light = np.array([0.4, 0.8, 0.3])
    light /= np.linalg.norm(light)

    rel = allp - center
    sx = rel @ right
    sy = rel @ up
    scale = min(size[0] * (1 - 2 * margin) / max(1e-6, sx.max() - sx.min()),
                size[1] * (1 - 2 * margin) / max(1e-6, sy.max() - sy.min()))
    ox = size[0] / 2 - (sx.min() + sx.max()) / 2 * scale
    oy = size[1] / 2 + (sy.min() + sy.max()) / 2 * scale

    tris = []
    for pos, idx, color in prims:
        p = pos - center
        a = p @ right
        b = p @ up
        depth = p @ d
        for i in range(0, len(idx), 3):
            ii = idx[i:i + 3]
            pts = [(ox + a[j] * scale, oy - b[j] * scale) for j in ii]
            n = np.cross(pos[ii[1]] - pos[ii[0]], pos[ii[2]] - pos[ii[0]])
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n /= ln
            if np.dot(n, d) <= 0:
                continue
            shade = 0.42 + 0.58 * max(0.0, float(np.dot(n, light)))
            c = tuple(int(max(0, min(255, v * 255 * shade))) for v in color)
            tris.append((float(depth[ii].mean()), pts, c))
    tris.sort(key=lambda t: t[0])
    img = Image.new('RGB', size, (188, 204, 219))
    dr = ImageDraw.Draw(img)
    for _, pts, c in tris:
        dr.polygon(pts, fill=c, outline=None)
    out = Path(out)
    img.save(out)
    print('rendered', out, 'tris', len(tris), 'bbox', [round(v, 1) for v in (hi - lo)])


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'core_0000'
    out = sys.argv[2] if len(sys.argv) > 2 else f'D:/RealEarth2024/logs/qa_{name}.png'
    mode = sys.argv[3] if len(sys.argv) > 3 else 'oblique'
    render(name, out, mode)
