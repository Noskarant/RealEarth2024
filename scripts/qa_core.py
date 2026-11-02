import sys, math
sys.path.insert(0, r'D:\RealEarth2024\scripts')
from building_gen import load_buildings
from building_gen import _rect_frame
bs = load_buildings()
core = [b for b in bs if b.core]
core.sort(key=lambda b: -b.area)
print('core', len(core))
for b in core[:10]:
    c, u, v, L, W, Ww = _rect_frame(b)
    print(b.bid, 'area', round(b.area, 1), 'len/wid', b.length, b.width, 'wall_h', b.wall_h,
          'rise', b.rise, 'roof', b.roof_type, 'rect', round(2*L), round(2*W), 'nature', b.nature, b.usage)
print('--- area max all ---')
allb = sorted(bs, key=lambda b: -b.area)
for b in allb[:10]:
    print(b.bid, round(b.area,1), b.length, b.width, b.wall_h, b.rise, b.roof_type, b.core)
print('--- core_0000 ---')
b = core[0]
print(b.__dict__)
