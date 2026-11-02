import math, statistics, sys
sys.path.insert(0, r'D:\RealEarth2024\scripts')
from building_gen import load_buildings
from collections import defaultdict
from config import TILE_SIZE_M

bs = load_buildings()
tiles = defaultdict(list)
for b in bs:
    if not b.core:
        tiles[(math.floor(b.east / TILE_SIZE_M), math.floor(b.north / TILE_SIZE_M))].append(b)
for key in [(-8, 2), (0, -2), (4, -8)]:
    g = tiles[key]
    anchor = statistics.median(b.ground for b in g)
    ys = sorted((b.ground - anchor, b.ground, b.wall_h, b.bid, b.east, b.north) for b in g)
    print(key, 'n', len(g), 'anchor', anchor)
    print(' min', ys[0])
    print(' max', ys[-1])
    extremes = [b for b in g if abs(b.ground - anchor) > 100]
    for b in extremes[:10]:
        print('  extreme', b.bid, b.ground, b.east, b.north, b.wall_h, b.area, b.core)
    print(' heights', min(b.wall_h for b in g), max(b.wall_h for b in g))
