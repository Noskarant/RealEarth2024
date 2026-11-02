"""Valmorel 0.1.7: roof slopes must meet at the centre ridge.

Runs with the existing Python venv (SDK not required). Catches the old
0.1.6 defect where each slope crossed the entire building width.
"""
from __future__ import annotations
import math
from building_gen import Building, _rect_frame, add_roof, load_buildings
from fsgltf import MeshBuilder


def check_roof(angle_degrees: float) -> None:
    theta = math.radians(angle_degrees)
    ca, sa = math.cos(theta), math.sin(theta)

    def rotate(x: float, y: float):
        return x * ca - y * sa, x * sa + y * ca

    ring = [rotate(-12, -6), rotate(12, -6), rotate(12, 6), rotate(-12, 6)]
    b = Building(
        bid="qa_roof_v017", ring=ring, ground=0, ground_max=0,
        eave=10, ridge=14, wall_h=10, rise=4,
        roof_type="gable", area=288, floors=3,
        nature="Indifferenciee", usage="Residentiel",
        wall_code="", roof_code="", lat=45.46, lon=6.44,
        east=0, north=0, length=24, width=12,
        orientation=angle_degrees,
        roof_mat="roof_slate", wall_mat="wall_stone",
    )
    frame = _rect_frame(b)
    mesh = MeshBuilder()
    add_roof(mesh, b, y_eave=10.0, frame=frame)
    assert mesh.triangle_count() >= 8, "Roof mesh missing"
    group = mesh.groups.get("roof_slate")
    assert group and group["idx"], "No roof faces emitted"
    ridge = [p for p in group["pos"] if abs(p[1] - 14.0) < 1e-5]
    eaves = [p for p in group["pos"] if abs(p[1] - 10.0) < 1e-5]
    assert ridge and eaves, "Ridge/eaves not present"
    center, axis_u, axis_v, _L, _W, width = frame

    def cross_offset(p):
        east, north = p[0], -p[2]  # glTF X=east, -Z=north
        return (east - center[0]) * axis_v[0] + (north - center[1]) * axis_v[1]

    assert max(abs(cross_offset(p)) for p in ridge) < 1e-4, (
        "Roof slopes do not meet at centre ridge", angle_degrees
    )
    assert min(cross_offset(p) for p in eaves) < -width
    assert max(cross_offset(p) for p in eaves) > width
    assert all(n[1] > 0.01 for n in group["nrm"]), (
        "Inverted roof face normal", angle_degrees
    )
    print("ROOF PLANES OK:", angle_degrees, "deg,", mesh.triangle_count(), "triangles")


def check_resort_detail_budget() -> None:
    buildings = load_buildings()
    near = [b for b in buildings if math.hypot(b.east, b.north) <= 1800]
    candidates = [
        b for b in near if b.area <= 3000 and b.rect_fill >= 0.45
        and (b.area >= 85 or b.heritage or b.meta.get("resort_residence_style"))
    ]
    detailed = [b for b in near if b.core]
    assert len(detailed) >= min(420, len(candidates)), (
        "Detailed centre budget not applied", len(detailed), len(candidates)
    )
    styled = [b for b in near if b.meta.get("resort_residence_style")]
    assert styled, "Alpine residence styling missing"
    print("VALMOREL CENTRE:", len(near), "buildings,", len(detailed),
          "detailed,", len(styled), "residences with alpine styling")


if __name__ == "__main__":
    for degrees in (0, 25, 90, 147):
        check_roof(degrees)
    check_resort_detail_budget()
    print("VALMOREL 0.1.7 QA: PASS (geometry and inventory only)")
    print("Official SDK compilation + visual confirmation remain necessary")
