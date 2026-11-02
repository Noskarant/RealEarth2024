import math, statistics, sys
sys.path.insert(0, r'D:\RealEarth2024\scripts')
from building_gen import load_buildings
bs = load_buildings()
core = [b for b in bs if b.core]
rest = [b for b in bs if not b.core]
print("total", len(bs), "core", len(core), "tiled", len(rest))
for size in (500, 300, 200, 150, 100, 75, 50):
    tiles = {}
    for b in rest:
        k = (math.floor(b.east/size), math.floor(b.north/size))
        tiles.setdefault(k, []).append(b.ground)
    spreads = sorted(max(v)-min(v) for v in tiles.values())
    n = len(spreads)
    p50 = spreads[n//2]; p90 = spreads[int(n*0.9)]; p99 = spreads[min(n-1,int(n*0.99))]
    print(f"tile {size:>3} m -> groups={n:>5}  p50={p50:6.2f}  p90={p90:6.2f}  p99={p99:6.2f}  max={spreads[-1]:7.2f}  groups>6m={sum(1 for s in spreads if s>6)}")
