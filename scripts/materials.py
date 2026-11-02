"""Procedural PBR-ish texture generation for the Valmorel buildings.

All textures are tileable (or tile safely) at the world scales defined in
config.py: 4 m per wall tile, 3 m per roof tile.  Windows are baked into the
wall textures used by distant/merged buildings; the individually modelled core
buildings use the plain variants plus real window geometry.
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from config import TEXTURES

SIZE = 512
OUT = TEXTURES / "buildings_src"


def _noise(size, color, sigma=6.0, seed=0):
    rng = np.random.default_rng(seed)
    base = np.array(color, dtype=np.float32)
    arr = np.clip(base[None, None, :] + rng.normal(0, sigma, (size, size, 1)), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def _wrap_rect(d, x, y, w, h, fill):
    """Rectangle that wraps horizontally so the texture tiles."""
    d.rectangle([x, y, x + w, y + h], fill=fill)
    if x + w > SIZE:
        d.rectangle([x - SIZE, y, x + w - SIZE, y + h], fill=fill)
    if x < 0:
        d.rectangle([x + SIZE, y, x + w + SIZE, y + h], fill=fill)


def wall_stone(seed=1, tint=(146, 140, 128)):
    img = _noise(SIZE, tint, 7.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    row_h = 56
    for row, y in enumerate(range(-row_h, SIZE + row_h, row_h)):
        x = -rng.randint(20, 90)
        while x < SIZE:
            w = rng.randint(54, 120)
            shade = rng.randint(-16, 14)
            c = tuple(max(0, min(255, tint[i] + shade)) for i in range(3))
            _wrap_rect(d, x + 2, y + 2, w - 4, row_h - 4, c)
            # mortar shadow at the bottom edge
            d.line([x + 2, y + row_h - 2, x + w - 2, y + row_h - 2], fill=(105, 100, 92))
            x += w
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img


def wall_wood(seed=2, tint=(118, 80, 50)):
    img = _noise(SIZE, tint, 5.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    plank = 46
    for y in range(-plank, SIZE + plank, plank):
        shade = rng.randint(-14, 16)
        c = tuple(max(0, min(255, tint[i] + shade)) for i in range(3))
        d.rectangle([0, y + 1, SIZE, y + plank - 2], fill=c)
        d.line([0, y + plank - 1, SIZE, y + plank - 1], fill=(62, 40, 24))
        d.line([0, y + 1, SIZE, y + 1], fill=(150, 108, 72), width=1)
        if rng.random() < 0.5:
            kx = rng.randint(0, SIZE)
            d.ellipse([kx - 7, y + plank // 2 - 3, kx + 7, y + plank // 2 + 3],
                      outline=(86, 56, 34), width=1)
    return img


def wall_plaster(seed=3, tint=(226, 218, 202)):
    img = _noise(SIZE, tint, 8.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    for _ in range(90):
        x, y = rng.randint(0, SIZE), rng.randint(0, SIZE)
        r = rng.randint(8, 44)
        c = (tint[0] - 8, tint[1] - 8, tint[2] - 10)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    img = img.filter(ImageFilter.GaussianBlur(3.5))
    return img


def wall_brick(seed=4, tint=(142, 78, 62)):
    img = _noise(SIZE, (198, 186, 170), 5.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    bh, bw = 32, 92
    for row, y in enumerate(range(0, SIZE, bh)):
        offset = (bw // 2) if row % 2 else 0
        for x in range(-bw, SIZE + bw, bw):
            shade = rng.randint(-18, 16)
            c = tuple(max(0, min(255, tint[i] + shade)) for i in range(3))
            _wrap_rect(d, x + offset + 2, y + 2, bw - 4, bh - 4, c)
    return img


def wall_concrete(seed=5, tint=(158, 156, 150)):
    img = _noise(SIZE, tint, 4.0, seed)
    d = ImageDraw.Draw(img)
    for x in range(0, SIZE, 128):
        d.line([x, 0, x, SIZE], fill=(132, 130, 126), width=2)
    for y in range(0, SIZE, 128):
        d.line([0, y, SIZE, y], fill=(140, 138, 133), width=1)
    return img.filter(ImageFilter.GaussianBlur(0.4))


def wall_metal(seed=6, tint=(126, 132, 134)):
    img = _noise(SIZE, tint, 4.0, seed)
    d = ImageDraw.Draw(img)
    for x in range(0, SIZE, 64):
        d.line([x, 0, x, SIZE], fill=(96, 102, 104), width=3)
        d.line([x + 3, 0, x + 3, SIZE], fill=(158, 162, 162), width=1)
    return img


def add_windows(img, seed=7, shutter=True, count=2):
    """Bake a row of windows into a wall texture (one floor per tile)."""
    img = img.copy()
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    win_w, win_h = 76, 132
    centers = [SIZE * (i + 0.5) / count for i in range(count)]
    for cx in centers:
        x0, x1 = int(cx - win_w / 2), int(cx + win_w / 2)
        y0, y1 = 196, 328
        if shutter:
            d.rectangle([x0 - 26, y0 - 4, x0 - 4, y1 + 4], fill=(74, 48, 30))
            d.rectangle([x1 + 4, y0 - 4, x1 + 26, y1 + 4], fill=(74, 48, 30))
            for sy in range(y0 + 6, y1, 10):
                d.line([x0 - 24, sy, x0 - 6, sy], fill=(52, 33, 20))
                d.line([x1 + 6, sy, x1 + 24, sy], fill=(52, 33, 20))
        d.rectangle([x0 - 9, y0 - 9, x1 + 9, y1 + 9], fill=(238, 232, 220))
        d.rectangle([x0, y0, x1, y1], fill=(44, 62, 78))
        # glass reflection gradient
        for i in range(win_h):
            t = i / max(1, win_h - 1)
            c = (int(96 - 50 * t), int(120 - 58 * t), int(140 - 62 * t))
            d.line([x0, y0 + i, x1, y0 + i], fill=c)
        d.line([x0 + win_w // 2, y0, x0 + win_w // 2, y1], fill=(232, 228, 216), width=5)
        d.line([x0, y0 + win_h // 2, x1, y0 + win_h // 2], fill=(232, 228, 216), width=5)
        d.rectangle([x0, y0, x1, y1], outline=(70, 58, 44), width=2)
    return img


def roof_slate(seed=10):
    img = _noise(SIZE, (66, 70, 76), 6.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    sw, sh = 58, 30
    for row, y in enumerate(range(-sh, SIZE + sh, sh)):
        offset = (sw // 2) if row % 2 else 0
        for x in range(-sw, SIZE + sw, sw):
            shade = rng.randint(-12, 14)
            c = (66 + shade, 70 + shade, 77 + shade)
            _wrap_rect(d, x + offset + 1, y + 1, sw - 2, sh - 2, c)
            d.line([x + offset + 1, y + sh - 2, x + offset + sw - 2, y + sh - 2],
                   fill=(38, 41, 46))
    return img


def roof_metal(seed=11):
    img = _noise(SIZE, (116, 122, 126), 5.0, seed)
    d = ImageDraw.Draw(img)
    for x in range(0, SIZE, 52):
        d.line([x, 0, x, SIZE], fill=(78, 84, 88), width=4)
        d.line([x + 5, 0, x + 5, SIZE], fill=(156, 160, 160), width=2)
    for y in range(0, SIZE, 128):
        d.line([0, y, SIZE, y], fill=(96, 100, 102), width=1)
    return img


def roof_tile(seed=12):
    img = _noise(SIZE, (150, 80, 56), 6.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    tw, th = 62, 38
    for row, y in enumerate(range(-th, SIZE + th, th)):
        offset = (tw // 2) if row % 2 else 0
        for x in range(-tw, SIZE + tw, tw):
            shade = rng.randint(-18, 20)
            c = (150 + shade, 80 + shade // 2, 56 + shade // 2)
            d.rounded_rectangle([x + offset + 1, y + 1, x + offset + tw - 3, y + th - 1],
                                radius=10, fill=c)
            d.line([x + offset + 2, y + th - 3, x + offset + tw - 4, y + th - 3],
                   fill=(108, 55, 40))
    return img


def roof_flat(seed=13):
    img = _noise(SIZE, (104, 104, 100), 9.0, seed)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    for _ in range(500):
        x, y = rng.randint(0, SIZE), rng.randint(0, SIZE)
        r = rng.randint(1, 4)
        v = rng.randint(60, 150)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, v - 2))
    return img


def glass(seed=14):
    # Power-of-two square: the MSFS DDS conversion is happiest with POT
    # textures, a non-POT source can be rejected and render magenta.
    size = 256
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        c = (int(120 - 70 * t), int(150 - 90 * t), int(174 - 100 * t))
        d.line([0, y, size, y], fill=c)
    mid = size // 2
    d.line([mid, 0, mid, size], fill=(226, 222, 210), width=14)
    d.line([0, mid, size, mid], fill=(226, 222, 210), width=14)
    d.rectangle([0, 0, size - 1, size - 1], outline=(70, 58, 44), width=8)
    return img


def flat_color(color, seed=15, sigma=3.0):
    return _noise(SIZE, color, sigma, seed)


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    mats: dict[str, Path] = {}

    def save(key, img):
        p = OUT / f"{key}.png"
        img.save(p, optimize=True)
        mats[key] = p

    wall_variants = {
        "stone": wall_stone(),
        "wood": wall_wood(),
        "plaster": wall_plaster(),
        "brick": wall_brick(),
        "concrete": wall_concrete(),
        "metal": wall_metal(),
    }
    for key, img in wall_variants.items():
        save(f"wall_{key}", img)
        save(f"wall_{key}_win", add_windows(img, seed=hash(key) % 9999))

    save("roof_slate", roof_slate())
    save("roof_metal", roof_metal())
    save("roof_tile", roof_tile())
    save("roof_flat", roof_flat())
    save("roof_thatch", flat_color((96, 78, 52), seed=16, sigma=10))

    save("stone_base", wall_stone(seed=21, tint=(128, 122, 112)))
    save("glass", glass())
    save("frame", flat_color((238, 233, 222), seed=17, sigma=2))
    save("balcony_wood", wall_wood(seed=22, tint=(92, 62, 38)))
    save("chimney", wall_stone(seed=23, tint=(136, 128, 116)))
    save("door_wood", wall_wood(seed=24, tint=(74, 50, 32)))
    return mats


if __name__ == "__main__":
    result = generate()
    for k, v in sorted(result.items()):
        print(f"{k:22s} {v.stat().st_size:7d}  {v}")
