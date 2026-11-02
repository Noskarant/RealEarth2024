import math, sys
from collections import defaultdict
sys.path.insert(0, r'D:\RealEarth2024\scripts')
from building_gen import load_buildings
bs = load_buildings()
rest = [b for b in bs if not b.core]
for cell, band in ((100,2.0),(100,2.5),(75,2.0),(50,2.0)):
    cl = defaultdict(list)
    for b in rest:
        k = (math.floor(b.east/cell), math.floor(b.north/cell), math.floor(b.ground/band))
        cl[k].append(b)
    spreads = [max(x.ground for x in v)-min(x.ground for x in v) for v in cl.values()]
    print(f"cell={cell} band={band} -> clusters={len(cl)}  max_spread={max(spreads):.2f}  mean_bld={len(rest)/len(cl):.2f}")
