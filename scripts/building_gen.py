"""Generate real building massing from IGN BD TOPO footprints.

Coordinate frames
-----------------
Authoring frame is right-handed ENU: (east, north, up) in metres.
fsgltf/config convert to MSFS glTF axes at export (X=East, Y=Up, -Z=North).

Fidelity
--------
Every mesh is driven by the IGN footprint, the BD TOPO 3D ground/eave/ridge
altitudes and the declared roof type.  Wall/roof materials come from the
MAJIC dmatgm/dmatto code table when present, otherwise from a deterministic
regional default.  Nothing is invented as "measured": materials and window
rhythm remain level C, geometry level B.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import mapbox_earcut as earcut
import numpy as np
from shapely.geometry import Polygon, Point, MultiPoint, shape
from shapely.ops import triangulate
from shapely.geometry.polygon import orient

from bourg_architecture import apply_bourg_reference_style
from config import (FOUNDATION_DEPTH_M, LAT0, LON0, M_PER_DEG_LAT,
                    M_PER_DEG_LON, RAW, ROOF_TEX_M, WALL_TEX_M,
                    deterministic_int, enu_to_gltf)
from fsgltf import MeshBuilder


def g(east: float, north: float, up: float):
    return enu_to_gltf(east, north, up)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
@dataclass
class Building:
    bid: str
    ring: list[tuple[float, float]]
    ground: float
    ground_max: float
    eave: float
    ridge: float
    wall_h: float
    rise: float
    roof_type: str
    area: float
    floors: int
    nature: str
    usage: str
    wall_code: str
    roof_code: str
    lat: float
    lon: float
    east: float
    north: float
    length: float
    width: float
    orientation: float
    rect_fill: float = 1.0
    complex: bool = False
    wall_mat: str = "wall_wood"
    roof_mat: str = "roof_slate"
    core: bool = False
    heritage: bool = False
    meta: dict = field(default_factory=dict)


def _largest_polygon(geom):
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        return max(geom.geoms, key=lambda p: p.area)
    return None


def load_buildings() -> list[Building]:
    fc = json.loads((RAW / "batiment.geojson").read_text(encoding="utf-8"))
    rings: dict[str, list[tuple[float, float]]] = {}
    for f in fc["features"]:
        p = f["properties"]
        cid = p.get("cleabs") or f.get("id")
        geom = _largest_polygon(shape(f["geometry"]))
        if geom is None:
            continue
        try:
            geom = orient(geom, sign=1.0)
        except Exception:
            continue
        ring = []
        for lon, lat, *_ in geom.exterior.coords:
            ring.append(((lon - LON0) * M_PER_DEG_LON, (lat - LAT0) * M_PER_DEG_LAT))
        if len(ring) >= 4:
            rings[cid] = ring

    rows = {}
    with (RAW.parent.parent / "buildings" / "buildings_inventory.csv").open(
            encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            rows[r["id"]] = r

    out: list[Building] = []
    for cid, r in rows.items():
        ring = rings.get(cid)
        if not ring:
            continue
        try:
            ground = float(r["ground_min_m"])
            ground_max = float(r["ground_max_m"] or ground)
            eave = float(r["eave_m"])
            ridge = float(r["ridge_m"])
            wall_h = float(r["wall_height_m"])
            rise = float(r["roof_rise_m"])
            area = float(r["area_m2"])
        except (ValueError, KeyError):
            continue
        if area < 4.0 or not (ring[0] == ring[-1]):
            pass
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.is_empty or poly.geom_type != "Polygon":
                continue
            ring = list(poly.exterior.coords)[:-1]
        wall_h = eave - ground
        if wall_h <= 0.5:
            wall_h = max(2.4, min(float(r["wall_height_m"] or 3.0), 30.0))
            eave = ground + wall_h
        wall_h = max(2.4, min(wall_h, 30.0))
        rise = max(0.0, min(ridge - eave, 14.0))
        if rise < 0.05:
            rise = 0.0
        floors_raw = r["floors"].strip()
        floors = int(round(float(floors_raw))) if floors_raw else max(1, round(wall_h / 2.9))
        rect_area = poly.minimum_rotated_rectangle.area if not poly.is_empty else area
        rect_fill = area / rect_area if rect_area > 0 else 1.0
        b = Building(
            bid=cid, ring=ring, ground=ground, ground_max=ground_max,
            eave=eave, ridge=ridge, wall_h=wall_h, rise=rise,
            roof_type=r["roof_type"] or "hip", area=area,
            floors=max(1, min(floors, 8)),
            nature=r["nature"] or "", usage=r["usage"] or "",
            wall_code=(r["wall_material"] or "").strip(),
            roof_code=(r["roof_material"] or "").strip(),
            lat=float(r["lat"]), lon=float(r["lon"]),
            east=float(r["local_z_east_m"]), north=float(r["local_x_north_m"]),
            length=float(r["length_m"] or 0), width=float(r["width_m"] or 0),
            orientation=float(r["orientation_deg"] or 0),
            rect_fill=round(rect_fill, 4),
            complex=bool(rect_fill < 0.62 or area > 4000.0),
        )
        _assign_style(b)
        apply_bourg_reference_style(b)
        # Large multi-storey residences around Valmorel often combine a
        # pale stone/plaster lower facade with timber upper storeys.
        # This only substitutes UNKNOWN material codes, never surveyed data.
        d_from_station = math.hypot(b.east, b.north)
        unknown_finish = (not b.wall_code.strip().isdigit()
                          or b.wall_code.strip() in ("00", "90", "99"))
        if (not b.meta.get("bourg_reference_area")
                and d_from_station < 1700
                and b.area >= 200 and b.floors >= 3
                and b.wall_h >= 7.5 and b.rise >= 0.8
                and unknown_finish):
            b.meta["alpine_apartment_style"] = True
            b.meta["finish_confidence"] = "typological_not_surveyed"
            b.wall_mat = ("wall_stone" if
                          deterministic_int(b.bid + ":alpine_apartment") % 4 == 0
                          else "wall_plaster")
            if not b.roof_code.strip().isdigit():
                b.roof_mat = "roof_slate"
        out.append(b)
    _fill_missing_altitudes(out)
    _mark_core(out)
    return out


def _fill_missing_altitudes(buildings: list[Building]) -> None:
    """BD TOPO uses -1000 as a missing-altitude sentinel; infer from neighbours."""
    valid = [b for b in buildings if 0.0 <= b.ground <= 3000.0]
    for b in buildings:
        if 0.0 <= b.ground <= 3000.0:
            continue
        near = sorted(valid, key=lambda o: (o.lat - b.lat) ** 2 + (o.lon - b.lon) ** 2)[:6]
        if not near:
            continue
        b.ground = statistics.median(o.ground for o in near)
        b.eave = b.ground + b.wall_h
        b.ridge = b.eave + b.rise
        b.meta["altitude_inferred"] = True


def _assign_style(b: Building) -> None:
    code = b.wall_code.zfill(2) if b.wall_code.isdigit() else ""
    digits = set(code)
    if "6" in digits:
        b.wall_mat = "wall_wood"
    elif "2" in digits or "1" in digits:
        b.wall_mat = "wall_stone"
    elif "4" in digits:
        b.wall_mat = "wall_brick"
    elif "3" in digits:
        b.wall_mat = "wall_concrete"
    elif "5" in digits:
        b.wall_mat = "wall_plaster"
    else:
        h = deterministic_int(b.bid + ":wall") % 100
        b.wall_mat = ("wall_wood" if h < 50 else
                      "wall_plaster" if h < 78 else "wall_stone")

    rcode = b.roof_code.zfill(2) if b.roof_code.isdigit() else ""
    rdig = set(rcode)
    if "2" in rdig:
        b.roof_mat = "roof_slate"
    elif "3" in rdig:
        b.roof_mat = "roof_metal"
    elif "1" in rdig:
        b.roof_mat = "roof_tile"
    elif "4" in rdig:
        b.roof_mat = "roof_metal"
    else:
        h = deterministic_int(b.bid + ":roof") % 100
        b.roof_mat = ("roof_slate" if h < 45 else
                      "roof_metal" if h < 85 else "roof_tile")
    if b.roof_type == "flat" or b.rise < 0.45:
        b.roof_mat = "roof_flat"


def _mark_core(buildings: list[Building]) -> None:
    heritage_words = ("Eglise", "Chapelle", "Chateau", "Tour", "Religieux")
    candidates = []
    for b in buildings:
        b.heritage = any(w in (b.nature + b.usage) for w in heritage_words)
        d = math.hypot(b.east, b.north)  # LAT0/LON0 is the resort centre
        if b.complex:
            continue
        if b.heritage or d < 520.0 and b.area >= 75.0 or b.area >= 520.0:
            candidates.append((b.area, b))
    # Prioritise visual detail along the Bourg reference corridor without
    # changing the measured footprint or geometry of other resort buildings.
    bourg = sorted(
        ((b.meta["bourg_distance_m"], -b.area, b) for _area, b in candidates
         if b.meta.get("bourg_reference_area")),
        key=lambda v: (v[0], v[1]),
    )
    selected_ids: set[str] = set()
    for _distance, _neg_area, b in bourg[:85]:
        b.core = True
        selected_ids.add(b.bid)

    candidates.sort(key=lambda t: -t[0])
    n_extra = 0
    for _area, b in candidates:
        if b.bid in selected_ids:
            continue
        if b.heritage or n_extra < 160:
            b.core = True
            selected_ids.add(b.bid)
            if not b.heritage:
                n_extra += 1


# --------------------------------------------------------------------------
# Geometry primitives (ENU)
# --------------------------------------------------------------------------
def _signed_area(ring) -> float:
    s = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        s += x1 * y2 - x2 * y1
    return s * 0.5


def wall_ring(mesh: MeshBuilder, ring, y0: float, y1: float, material: str,
              tex: float = WALL_TEX_M) -> None:
    """Vertical wall strip textured with 0..1 UV panels.

    MSFS 2024 ignores glTF sampler wrapping and always uses CLAMP_TO_EDGE, so
    every quad must stay inside the 0..1 UV range.  Each facade segment is
    therefore cut into panels of at most one texture tile (``tex`` metres),
    both horizontally and vertically, and each panel gets its own 0..1 UV.
    """
    if y1 <= y0 or len(ring) < 3:
        return
    if _signed_area(ring) < 0:
        ring = list(reversed(ring))
    height = y1 - y0
    bands = max(1, math.ceil(height / tex - 1e-6))
    band_h = height / bands
    v_span = min(1.0, band_h / tex)
    n = len(ring)
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        seg = math.hypot(bx - ax, by - ay)
        if seg < 1e-4:
            continue
        cols = max(1, math.ceil(seg / tex - 1e-6))
        u_span = min(1.0, (seg / cols) / tex)
        for c in range(cols):
            t0, t1 = c / cols, (c + 1) / cols
            xa, ya = ax + (bx - ax) * t0, ay + (by - ay) * t0
            xb, yb = ax + (bx - ax) * t1, ay + (by - ay) * t1
            for r in range(bands):
                za = y0 + band_h * r
                zb = za + band_h
                p0 = g(xa, ya, za)
                p1 = g(xb, yb, za)
                p2 = g(xb, yb, zb)
                p3 = g(xa, ya, zb)
                mesh.add_quad(material, p0, p1, p2, p3,
                              uvs=((0, 0), (u_span, 0),
                                   (u_span, v_span), (0, v_span)))


def add_box_enu(mesh: MeshBuilder, material: str, center, u, v, w,
                su: float, sv: float, sw: float) -> None:
    """Oriented box; (u,v,w) must be orthonormal and right-handed."""
    cu, cv, cw = center
    hu, hv, hw = su / 2, sv / 2, sw / 2

    def pt(iu, iv, iw):
        e = cu + u[0] * hu * iu + v[0] * hv * iv + w[0] * hw * iw
        n = cv + u[1] * hu * iu + v[1] * hv * iv + w[1] * hw * iw
        up = cw + u[2] * hu * iu + v[2] * hv * iv + w[2] * hw * iw
        return g(e, n, up)

    p000 = pt(-1, -1, -1)
    p001 = pt(-1, -1, 1)
    p010 = pt(-1, 1, -1)
    p011 = pt(-1, 1, 1)
    p100 = pt(1, -1, -1)
    p101 = pt(1, -1, 1)
    p110 = pt(1, 1, -1)
    p111 = pt(1, 1, 1)
    faces = [
        (p100, p110, p111, p101),  # +u
        (p001, p011, p010, p000),  # -u
        (p010, p011, p111, p110),  # +v
        (p000, p100, p101, p001),  # -v
        (p001, p101, p111, p011),  # +w
        (p110, p011, p010, p100),  # -w  (not visible)
    ]
    for f in faces:
        mesh.add_quad(material, *f)


def _rect_frame(b: Building, overhang: float = 0.5):
    poly = Polygon(b.ring)
    rect = poly.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        rect = poly.envelope
    pts = list(rect.exterior.coords)[:-1]
    if len(pts) < 4:
        pts = [(b.east - 3, b.north - 3), (b.east + 3, b.north - 3),
               (b.east + 3, b.north + 3), (b.east - 3, b.north + 3)]
    edges = []
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        edges.append((math.hypot(bx - ax, by - ay), ax, ay, bx, by))
    le, ax, ay, bx, by = max(edges)
    u = ((bx - ax) / le, (by - ay) / le)
    v = (-u[1], u[0])
    # Sanity: v should point from the first edge towards the opposite side.
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    mid = ((ax + bx) / 2, (ay + by) / 2)
    if (cx - mid[0]) * v[0] + (cy - mid[1]) * v[1] < 0:
        v = (-v[0], -v[1])
        u = (-u[0], -u[1])
    # Long axis = u; perpendicular extent is the width.
    ws = [abs((p[0] - cx) * v[0] + (p[1] - cy) * v[1]) for p in pts]
    ls = [abs((p[0] - cx) * u[0] + (p[1] - cy) * u[1]) for p in pts]
    L = max(ls)
    W = max(ws)
    if L < 1.5:
        L = max(2.0, b.length / 2)
    if W < 1.5:
        W = max(2.0, b.width / 2)
    return (cx, cy), u, v, L + overhang, W + overhang, W


def _flat_cap(mesh: MeshBuilder, b: Building, y_eave: float, material: str) -> None:
    ring = [(x, y) for x, y in b.ring]
    if _signed_area(ring) < 0:
        ring = list(reversed(ring))
    verts = np.array(ring, dtype=np.float64)
    idx = earcut.triangulate_float64(verts, np.array([len(verts)], dtype=np.uint32))
    z = y_eave + 0.14
    for i in range(0, len(idx), 3):
        pts = [g(ring[idx[i]][0], ring[idx[i]][1], z),
               g(ring[idx[i + 1]][0], ring[idx[i + 1]][1], z),
               g(ring[idx[i + 2]][0], ring[idx[i + 2]][1], z)]
        mesh.add_triangle(material, *pts, (0, 0), (1, 0), (1, 1))
    wall_ring(mesh, b.ring, y_eave, y_eave + 0.38, b.wall_mat)


def _complex_pitched_roof(mesh: MeshBuilder, b: Building,
                          y_eave: float, material: str) -> bool:
    """Pitched roof field constrained to an irregular IGN footprint.

    This is approximate roof geometry, NOT a surveyed roof skeleton.
    Unlike the old giant flat cap, the height rises inward from the true
    footprint boundary toward the documented BD TOPO ridge altitude.
    A capped interior point grid adds stable triangulation on L-shaped
    buildings while keeping all triangles strictly inside the footprint.
    """
    poly = Polygon(b.ring)
    if not poly.is_valid or poly.area < 15 or b.rise < 0.5:
        return False
    minx, miny, maxx, maxy = poly.bounds
    span = max(maxx-minx, maxy-miny)
    if span > 180:
        return False
    step = max(2.5, min(7.0, math.sqrt(poly.area) / 9.0))
    # Use stable, bounded sampling to avoid too many triangles in MSFS.
    points = list(b.ring)
    nx = max(1, min(30, math.ceil((maxx-minx)/step)))
    ny = max(1, min(30, math.ceil((maxy-miny)/step)))
    for ix in range(nx):
        for iy in range(ny):
            x = minx + (ix+0.5)*(maxx-minx)/nx
            y = miny + (iy+0.5)*(maxy-miny)/ny
            if poly.contains(Point(x, y)):
                points.append((x, y))
    if len(points) > 1000:
        return False
    triangles = triangulate(MultiPoint(points))
    if not triangles:
        return False
    # The recorded ridge rise remains the maximum target roof height.
    # Reaching it ~4m inward creates pitched segments, not a flat roof box.
    slope = b.rise / max(2.0, min(5.5, min(maxx-minx,maxy-miny)*0.48))
    count = 0
    for tri in triangles:
        # Delaunay is unconstrained. Clip any crossing triangles rather than
        # silently leaving holes around re-entrant corners/courtyards.
        clipped = tri if poly.covers(tri) else tri.intersection(poly)
        if clipped.is_empty:
            continue
        surfaces = ([clipped] if clipped.geom_type == "Polygon"
                    else [part for part in getattr(clipped, "geoms", ())
                          if part.geom_type == "Polygon"])
        for surface in surfaces:
            if surface.area < 0.015:
                continue
            fragments = [surface] if len(surface.exterior.coords) == 4 else triangulate(surface)
            for frag in fragments:
                if not surface.covers(frag) or frag.area < 0.008:
                    continue
                coords = []
                for x,y in list(frag.exterior.coords)[:3]:
                    d = poly.boundary.distance(Point(x,y))
                    z = y_eave + min(b.rise, max(0.0, d*slope))
                    coords.append((x,y,z))
                xs = [p[0] for p in coords]
                ys = [p[1] for p in coords]
                size = max(ROOF_TEX_M, max(xs)-min(xs), max(ys)-min(ys))
                uv = [((x-min(xs))/size, (y-min(ys))/size) for x,y,_z in coords]
                mesh.add_triangle(material, *(g(*p) for p in coords), *uv)
                count += 1
    return count > 0


def add_roof(mesh: MeshBuilder, b: Building, y_eave: float, frame,
             roof_mat: str | None = None) -> None:
    center, u, v, L, W, W_wall = frame
    cx, cy = center
    mat = roof_mat or b.roof_mat
    if b.complex or b.rect_fill < 0.78:
        # For irregular footprints, follow the true IGN contour and build
        # a conservative pitched field rather than a huge flat-topped block.
        if b.roof_type != "flat" and _complex_pitched_roof(
                mesh, b, y_eave, mat):
            return
        _flat_cap(mesh, b, y_eave, "roof_flat" if b.roof_type == "flat" else mat)
        return
    flat = (b.roof_type == "flat") or (b.rise < 0.5) or (W < 0.6)
    if flat:
        _flat_cap(mesh, b, y_eave, "roof_flat")
        return

    rise = min(b.rise, 0.82 * W)
    rise = max(0.6, rise)
    ridge_len = max(0.1, (L - W) if b.roof_type == "hip" else L)
    hill = y_eave + rise

    def p(su, sv, z):
        return g(cx + u[0] * su + v[0] * sv, cy + u[1] * su + v[1] * sv, z)

    c0 = p(-L, -W, y_eave)
    c1 = p(L, -W, y_eave)
    c2 = p(L, W, y_eave)
    c3 = p(-L, W, y_eave)
    r0 = p(-ridge_len, 0, hill)
    r1 = p(ridge_len, 0, hill)

    slope = math.hypot(W, rise)
    # Clamp-safe roof panelling: MSFS always uses CLAMP_TO_EDGE, so each slope
    # is cut into quads of at most one ROOF_TEX_M tile and UV stays in 0..1.
    n_u = max(1, math.ceil(2 * L / ROOF_TEX_M - 1e-6))
    n_v = max(1, math.ceil(slope / ROOF_TEX_M - 1e-6))
    u_span = min(1.0, (2 * L / n_u) / ROOF_TEX_M)
    v_span = min(1.0, (slope / n_v) / ROOF_TEX_M)

    def slope_pt(a: float, t: float, side: int):
        """Point on a roof slope. a in [0,1] along the eave, t in [0,1] up."""
        su_eave = -L + 2 * L * a
        su_ridge = -ridge_len + 2 * ridge_len * a
        su = su_eave + (su_ridge - su_eave) * t
        sv = (-W + 2 * W * t) if side < 0 else (W - 2 * W * t)
        return p(su, sv, y_eave + rise * t)

    for side in (-1, 1):
        for i in range(n_u):
            a0, a1 = i / n_u, (i + 1) / n_u
            for j in range(n_v):
                t0, t1 = j / n_v, (j + 1) / n_v
                if side < 0:
                    q = (slope_pt(a0, t0, side), slope_pt(a1, t0, side),
                         slope_pt(a1, t1, side), slope_pt(a0, t1, side))
                else:
                    q = (slope_pt(a1, t0, side), slope_pt(a0, t0, side),
                         slope_pt(a0, t1, side), slope_pt(a1, t1, side))
                mesh.add_quad(mat, *q, uvs=((0, 0), (u_span, 0),
                                            (u_span, v_span), (0, v_span)))

    # Gable ends / hip ends (small areas: one textured triangle each).
    tri_v = min(1.0, slope / ROOF_TEX_M)
    hip_u = min(1.0, 2 * W / ROOF_TEX_M)
    ridge_u = min(1.0, W / ROOF_TEX_M)
    if b.roof_type == "hip":
        mesh.add_triangle(mat, c3, c0, r0, (0, 0), (hip_u, 0), (ridge_u, tri_v))
        mesh.add_triangle(mat, c1, c2, r1, (0, 0), (hip_u, 0), (ridge_u, tri_v))
    else:
        gable_v = min(1.0, rise / WALL_TEX_M)
        mesh.add_triangle(b.wall_mat, c3, c0, r0,
                          (0, 0), (min(1.0, 2 * W / WALL_TEX_M), 0), (0.5, gable_v))
        mesh.add_triangle(b.wall_mat, c1, c2, r1,
                          (0, 0), (min(1.0, 2 * W / WALL_TEX_M), 0), (0.5, gable_v))


def add_core_details(mesh: MeshBuilder, b: Building, y_base: float, frame) -> None:
    # The old guard suppressed ALL 3D windows/balconies on many irregular
    # residential blocks. Their true IGN edges still support facade details.
    if b.rect_fill < 0.52 or b.area > 2500:
        return
    ring = b.ring
    n = len(ring)
    edges = []
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        le = math.hypot(bx - ax, by - ay)
        if le >= 2.2:
            edges.append((le, ax, ay, bx, by))
    edges.sort(reverse=True)
    edges = edges[:8]
    up = (0.0, 0.0, 1.0)
    n_floors = max(1, min(b.floors, int(b.wall_h / 2.7) or 1))
    win_w, win_h = 1.0, 1.3
    bourg_commerce = (
        b.meta.get("bourg_reference_area")
        and "commercial" in b.usage.lower()
    )
    for edge_i, (le, ax, ay, bx, by) in enumerate(edges):
        ux, uy = (bx - ax) / le, (by - ay) / le
        nx, ny = uy, -ux  # outward normal for a CCW ring
        usable = max(0.8, le - 1.8)
        count = max(1, int(usable / 3.2) + 1)
        for f in range(n_floors):
            if bourg_commerce and edge_i == 0 and f == 0:
                # The surveyed inventory identifies a commercial building.
                # Give its longest ground-floor frontage shop glazing rather
                # than domestic windows; exact storefronts are not surveyed.
                continue
            wy = 1.45 + f * 2.85
            if wy + win_h / 2 > b.wall_h - 0.25:
                continue
            for k in range(count):
                t = 0.9 + _useful_pos(usable, count, k)
                px, py = ax + ux * t, ay + uy * t
                u3 = (ux, uy, 0.0)
                v3 = (-nx, -ny, 0.0)
                c = (px + nx * 0.06, py + ny * 0.06, y_base + wy)
                add_box_enu(mesh, "frame", c, u3, v3, up,
                            win_w + 0.16, 0.10, win_h + 0.16)
                c2 = (c[0] + nx * 0.035, c[1] + ny * 0.035, c[2])
                add_box_enu(mesh, "glass", c2, u3, v3, up, win_w, 0.08, win_h)
                if b.meta.get("bourg_reference_area") and f > 0:
                    # Exterior wooden shutters: visible geometry, no photo
                    # decals or unlicensed signage baked into the textures.
                    for side in (-1, 1):
                        shutter_c = (
                            c[0] + side * ux * (win_w / 2 + 0.20) + nx * 0.07,
                            c[1] + side * uy * (win_w / 2 + 0.20) + ny * 0.07,
                            c[2],
                        )
                        add_box_enu(mesh, "shutter_brown", shutter_c,
                                    u3, v3, up, 0.30, 0.045, win_h)

    if bourg_commerce and edges:
        le, ax, ay, bx, by = edges[0]
        if le >= 4.0 and b.wall_h >= 3.1:
            ux, uy = (bx - ax) / le, (by - ay) / le
            nx, ny = uy, -ux
            shop_count = max(1, min(6, int((le - 1.4) / 2.8)))
            shop_w = min(2.20, max(1.2, (le - 1.4) / shop_count - 0.25))
            for i in range(shop_count):
                t = le * (i + 0.5) / shop_count
                cx = ax + ux * t + nx * 0.12
                cy = ay + uy * t + ny * 0.12
                front_y = y_base + 1.50
                u3 = (ux, uy, 0.0)
                v3 = (-nx, -ny, 0.0)
                add_box_enu(mesh, "shop_frame", (cx, cy, front_y),
                            u3, v3, up, shop_w + 0.16, 0.14, 2.30)
                add_box_enu(mesh, "glass",
                            (cx + nx * 0.08, cy + ny * 0.08, front_y),
                            u3, v3, up, shop_w, 0.06, 2.10)

    # One balcony row on the longest residential facade, on the real wall.
    if edges and not b.heritage and ("Résidentiel" in b.usage or
                                     "Commercial" in b.usage or b.area > 150):
        le, ax, ay, bx, by = edges[0]
        if le >= 4.0:
            ux, uy = (bx - ax) / le, (by - ay) / le
            nx, ny = uy, -ux
            t = le / 2
            u3 = (ux, uy, 0.0)
            v3 = (-nx, -ny, 0.0)
            width = min(4.2, le * 0.6)
            for f in range(1, n_floors):
                fy = 1.55 + f * 2.85
                if fy + 1.0 > b.wall_h:
                    continue
                c = (ax + ux * t + nx * 0.66, ay + uy * t + ny * 0.66, y_base + fy)
                add_box_enu(mesh, "balcony_wood", c, u3, v3, up, width, 1.25, 0.16)
                cr = (ax + ux * t + nx * 1.22, ay + uy * t + ny * 1.22,
                      y_base + fy + 0.55)
                if b.meta.get("bourg_reference_area"):
                    # Open timber balustrade: horizontal rails + spaced posts,
                    # rather than the opaque one-metre-high solid block.
                    for rail_height in (0.12, 0.86):
                        rail_c = (cr[0], cr[1], y_base + fy + rail_height)
                        add_box_enu(mesh, "balcony_wood", rail_c,
                                    u3, v3, up, width, 0.10, 0.10)
                    post_count = max(2, math.ceil(width / 1.05) + 1)
                    for post_i in range(post_count):
                        offset = -width / 2 + width * post_i / (post_count - 1)
                        post_c = (cr[0] + ux * offset, cr[1] + uy * offset,
                                  y_base + fy + 0.48)
                        add_box_enu(mesh, "balcony_wood", post_c,
                                    u3, v3, up, 0.10, 0.11, 0.95)
                else:
                    add_box_enu(mesh, "balcony_wood", cr, u3, v3, up,
                                width, 0.09, 1.0)

    center, u, v, L, W, W_wall = frame
    cx, cy = center
    if b.rise > 0.8 and W > 2.5:
        ch = (cx + u[0] * L * 0.3, cy + u[1] * L * 0.3,
              y_base + b.wall_h + min(b.rise, 0.8 * W) * 0.45)
        add_box_enu(mesh, "chimney", ch, (u[0], u[1], 0), (v[0], v[1], 0), up,
                    0.75, 0.75, 1.4)


def _useful_pos(usable: float, count: int, k: int) -> float:
    if count <= 1:
        return usable / 2
    return (k + 0.5) * usable / count


def add_building(mesh: MeshBuilder, b: Building, origin_e: float, origin_n: float,
                 anchor_ground: float) -> int:
    ring = [(e - origin_e, n - origin_n) for e, n in b.ring]
    y_base = b.ground - anchor_ground
    # Rebuild a local copy so all helpers work relative to the tile origin.
    local = Building(**{**b.__dict__, "ring": ring, "east": b.east - origin_e,
                        "north": b.north - origin_n})
    frame = _rect_frame(local)
    y_wall_base = y_base - FOUNDATION_DEPTH_M
    stone_top = y_base + min(1.1, max(0.5, b.wall_h * 0.18))
    wall_ring(mesh, ring, y_wall_base, stone_top, "stone_base", tex=2.5)
    main_mat = b.wall_mat if b.core else b.wall_mat + "_win"
    wall_top = y_base + b.wall_h
    if (b.meta.get("bourg_upper_wood") and b.core) or b.meta.get("alpine_apartment_style"):
        # Reference-informed, but not exact per-building upper-storey wood.
        change_y = max(stone_top + 2.6, wall_top - 3.1)
        change_y = min(change_y, wall_top)
        wall_ring(mesh, ring, stone_top, change_y, main_mat)
        upper_mat = "wall_wood" if b.core else "wall_wood_win"
        wall_ring(mesh, ring, change_y, wall_top, upper_mat)
    else:
        wall_ring(mesh, ring, stone_top, wall_top, main_mat)
    add_roof(mesh, local, wall_top, frame)
    if b.core:
        add_core_details(mesh, local, y_base, frame)
    tri = len(mesh.groups.get(main_mat, {}).get("idx", [])) // 3
    return tri


def footprint_stats(b: Building) -> tuple[float, float]:
    return b.length, b.width


__all__ = ["Building", "load_buildings", "add_building", "MeshBuilder",
           "footprint_stats", "statistics"]
