"""Conservative, optional close-range facade detail for otherwise generic houses.

All openings are procedural estimates; they do not claim the exact door/window
positions of real Saint-Maurice buildings. No source building/landmark is edited.
"""
from __future__ import annotations
import math
import numpy as np
from shapely.geometry import Polygon


def facades_for_building(poly: Polygon, height: float, roof_rise: float,
                         *, floors: int | None = None, max_windows: int = 8):
    """Return batched (vertices, faces) meshes: glass, pale stone trim, doors.

    Vertices are local glTF +X east, +Y up, -Z north; the caller places the
    geometry at the building centroid. Panels are offset from the walls by
    5 cm to avoid z-fighting. No windows on agricultural/industrial buildings.
    """
    eave = height - roof_rise
    if eave < 3.4:
        return {}
    floors = int(floors) if floors is not None and floors >= 1 else max(1,int((eave-0.9)/3.1))
    floors = min(4, floors)
    centroid = poly.centroid
    sets: dict[str, tuple[list, list]] = {
        'glass': ([], []), 'trim': ([], []), 'door': ([], [])
    }
    coords=list(poly.exterior.coords)
    is_ccw = poly.exterior.is_ccw

    def add_quad(kind, along_x, along_y, tangent, outward, center_h, halfwidth, halfheight, offset=0.055):
        vertices,faces=sets[kind]
        origin=np.array([along_x,along_y],dtype=float)+offset*np.array(outward)
        for sign_x,sign_h in ((-1,-1),(1,-1),(1,1),(-1,1)):
            xy=origin+sign_x*halfwidth*np.array(tangent)
            vertices.append((xy[0]-centroid.x,center_h+sign_h*halfheight,-(xy[1]-centroid.y)))
        start=len(vertices)-4
        faces.extend([(start,start+1,start+2),(start,start+2,start+3)])

    longest=sorted(((math.hypot(b[0]-a[0],b[1]-a[1]), i)
                     for i,(a,b) in enumerate(zip(coords[:-1],coords[1:]))),reverse=True)
    door_edge=longest[0][1] if longest else -1
    for i,(a,b) in enumerate(zip(coords[:-1],coords[1:])):
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        if length < 3.6:
            continue
        tangent=((b[0]-a[0])/length,(b[1]-a[1])/length)
        outward=((tangent[1],-tangent[0]) if is_ccw
                 else (-tangent[1],tangent[0]))
        # Leave 1.2m at either end to avoid windows turning corners.
        number=max(1,min(max_windows,int((length-1.0)/3.0)))
        for slot in range(number):
            t=(slot+1)/(number+1)
            x=a[0]+(b[0]-a[0])*t
            y=a[1]+(b[1]-a[1])*t
            for floor in range(floors):
                z=2.0+floor*3.0
                if z+0.65>=eave:
                    continue
                if i==door_edge and floor==0 and slot==number//2:
                    add_quad('door',x,y,tangent,outward,1.12,0.53,1.01,offset=0.062)
                    # Top lintel: 1.15 m wide and 0.12 m high.
                    add_quad('trim',x,y,tangent,outward,2.18,0.64,0.065,offset=0.072)
                    continue
                # Colored glass as a close-up visual cue, not actual measured openings.
                add_quad('glass',x,y,tangent,outward,z,0.46,0.56,offset=0.06)
                # Four stone border strips outside the glass rectangle.
                add_quad('trim',x-0.52*tangent[0],y-0.52*tangent[1],tangent,outward,z,0.06,0.65,offset=0.072)
                add_quad('trim',x+0.52*tangent[0],y+0.52*tangent[1],tangent,outward,z,0.06,0.65,offset=0.072)
                add_quad('trim',x,y,tangent,outward,z+0.62,0.58,0.065,offset=0.072)
                add_quad('trim',x,y,tangent,outward,z-0.62,0.58,0.065,offset=0.072)
    return {key:(np.asarray(v,dtype=np.float32).reshape((-1,3)),
                 np.asarray(f,dtype=np.int64).reshape((-1,3)))
            for key,(v,f) in sets.items() if f}
