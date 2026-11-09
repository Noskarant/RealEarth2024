from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon, Point
from generate import _faces_for_polygon

def test_real_courtyard_not_filled():
    b=Polygon([(0,0),(20,0),(20,20),(0,20)],holes=[[(7,7),(7,13),(13,13),(13,7)]])
    v,f,rv,rf=_faces_for_polygon(b,b.centroid,6,2,3)
    assert len(f)==16  # 4 outer + 4 inner wall segments, 2 triangles each
    assert len(rf)>0
    # All roof triangle centroids must fall in the *actual building area*, not yard.
    for i,j,k in rf:
        center=((rv[i]+rv[j]+rv[k])/3)
        x=center[0]+b.centroid.x;y=b.centroid.y-center[2]
        assert b.covers(Point(x,y))
