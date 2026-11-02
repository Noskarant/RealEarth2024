import sys, statistics, math
sys.path.insert(0, r'D:\RealEarth2024\scripts')
from building_gen import load_buildings
bs = load_buildings()
bad = [b for b in bs if b.ground < 0 or b.ground > 3000 or b.eave < 0 or b.ridge < 0]
print('bad', len(bad))
from collections import Counter
print(Counter(round(b.ground) for b in bad).most_common(10))
print('ground range', min(b.ground for b in bs), max(b.ground for b in bs))
print('eave range', min(b.eave for b in bs), max(b.eave for b in bs))
# distribution by area
print('bad area total', sum(b.area for b in bad))
for b in bad[:5]:
    print(b.bid, b.ground, b.eave, b.ridge, b.wall_h, b.area, b.lat, b.lon)
