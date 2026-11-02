"""Minimal, deterministic glTF 2.0 writer for MSFS 2024 scenery.

MSFS 2024 conventions used here:
  * glTF is Y-up.
  * local +X = North, local +Z = East (heading 0).
  * one material per mesh primitive, plain PBR colours (see write_gltf).
  * no sparse accessors, no custom tangents, triangles only.
"""
from __future__ import annotations

import base64
import json
import struct
from functools import lru_cache
from pathlib import Path

import numpy as np


class MeshBuilder:
    """Accumulate triangles grouped by material key."""

    def __init__(self):
        self.groups: dict[str, dict] = {}

    def add_triangle(self, material: str, p0, p1, p2, uv0=(0, 0), uv1=(0, 0), uv2=(0, 0)):
        g = self.groups.setdefault(material, {"pos": [], "nrm": [], "uv": [], "idx": []})
        base = len(g["pos"])
        # compute face normal (counter-clockwise winding = front face)
        a = np.asarray(p1, dtype=np.float64) - np.asarray(p0, dtype=np.float64)
        b = np.asarray(p2, dtype=np.float64) - np.asarray(p0, dtype=np.float64)
        n = np.cross(a, b)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            return
        n = n / ln
        for p, uv in ((p0, uv0), (p1, uv1), (p2, uv2)):
            g["pos"].append((float(p[0]), float(p[1]), float(p[2])))
            g["nrm"].append((float(n[0]), float(n[1]), float(n[2])))
            g["uv"].append((float(uv[0]), float(uv[1])))
        g["idx"].extend((base, base + 1, base + 2))

    def add_quad(self, material, p0, p1, p2, p3, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
        self.add_triangle(material, p0, p1, p2, uvs[0], uvs[1], uvs[2])
        self.add_triangle(material, p0, p2, p3, uvs[0], uvs[2], uvs[3])

    def triangle_count(self):
        return sum(len(g["idx"]) // 3 for g in self.groups.values())

    def bounds(self):
        pts = np.array([p for g in self.groups.values() for p in g["pos"]], dtype=np.float64)
        if len(pts) == 0:
            return None
        return pts.min(axis=0), pts.max(axis=0)


def _png_size(path: Path):
    from PIL import Image

    with Image.open(path) as im:
        return im.size


@lru_cache(maxsize=64)
def _average_srgb(path: Path) -> tuple[float, float, float]:
    """Mean colour of a texture, converted from sRGB to linear for glTF."""
    from PIL import Image

    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    mean = arr.reshape(-1, 3).mean(axis=0)

    def to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(round(to_linear(float(c)), 5) for c in mean)  # type: ignore[return-value]


def write_gltf(out_dir: Path, name: str, mesh: MeshBuilder, textures: dict[str, Path],
               base_color_factors: dict[str, list] | None = None,
               roughness: dict[str, float] | None = None,
               metallic: dict[str, float] | None = None,
               alpha_modes: dict[str, str] | None = None,
               use_textures: bool = False) -> Path:
    """Write <name>.gltf + <name>.bin.

    When ``use_textures`` is False (the default) every material is a plain
    PBR colour sampled from the reference texture. MSFS 2024 only consumes
    KTX2 textures produced by its own build step, and that step does not run
    in this headless pipeline: external PNGs are silently dropped and the
    models render with the magenta "missing texture" material. Solid colours
    sampled from the real texture keep the palette without that risk.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    blob = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    gltf_textures = []
    gltf_images = []
    gltf_samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
    material_index = {}

    def add_view(data: bytes, target=None):
        offset = len(blob)
        blob.extend(data)
        while len(blob) % 4:
            blob.append(0)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target:
            view["target"] = target
        buffer_views.append(view)
        return len(buffer_views) - 1, offset

    for mkey, g in mesh.groups.items():
        if not g["idx"]:
            continue
        pos = np.asarray(g["pos"], dtype=np.float32)
        nrm = np.asarray(g["nrm"], dtype=np.float32)
        uv = np.asarray(g["uv"], dtype=np.float32)
        idx = np.asarray(g["idx"], dtype=np.uint32)

        vb, off = add_view(pos.tobytes(), 34962)
        nb, _ = add_view(nrm.tobytes(), 34962)
        tb, _ = add_view(uv.tobytes(), 34962)
        ib, _ = add_view(idx.tobytes(), 34963)

        accessors.append({"bufferView": vb, "componentType": 5126, "count": len(pos),
                          "type": "VEC3", "min": pos.min(axis=0).tolist(),
                          "max": pos.max(axis=0).tolist()})
        accessors.append({"bufferView": nb, "componentType": 5126, "count": len(nrm), "type": "VEC3"})
        accessors.append({"bufferView": tb, "componentType": 5126, "count": len(uv), "type": "VEC2"})
        accessors.append({"bufferView": ib, "componentType": 5125, "count": len(idx), "type": "SCALAR"})

        pbr = {
            "baseColorFactor": (base_color_factors or {}).get(mkey, [1, 1, 1, 1]),
            "metallicFactor": (metallic or {}).get(mkey, 0.0),
            "roughnessFactor": (roughness or {}).get(mkey, 0.85),
        }
        tex_path = textures.get(mkey) if use_textures else None
        if tex_path is not None:
            tex_path = Path(tex_path)
            # MSFS resolves model-library textures from a "texture" sub-folder
            # next to the glTF; images left at the root are silently dropped by
            # the package builder, which is why the models showed magenta.
            tex_dir = out_dir / "texture"
            tex_dir.mkdir(parents=True, exist_ok=True)
            if tex_path.parent != tex_dir:
                import shutil

                shutil.copy2(tex_path, tex_dir / tex_path.name)
            uri = f"texture/{tex_path.name}"
            img_index = None
            for i, img in enumerate(gltf_images):
                if img["uri"] == uri:
                    img_index = i
            if img_index is None:
                gltf_images.append({"uri": uri, "name": tex_path.stem,
                                    "mimeType": "image/png"})
                img_index = len(gltf_images) - 1
            tex_index = None
            for i, t in enumerate(gltf_textures):
                if t["source"] == img_index:
                    tex_index = i
            if tex_index is None:
                gltf_textures.append({"sampler": 0, "source": img_index})
                tex_index = len(gltf_textures) - 1
            pbr["baseColorTexture"] = {"index": tex_index, "texCoord": 0}
        elif mkey in textures and mkey not in (base_color_factors or {}):
            # No texture: use the mean colour of the reference texture so the
            # palette (slate, larch, lime plaster, granite...) is preserved.
            pbr["baseColorFactor"] = [*_average_srgb(Path(textures[mkey])), 1.0]

        mat = {"name": mkey, "pbrMetallicRoughness": pbr,
               "doubleSided": bool((alpha_modes or {}).get(mkey) == "BLEND")}
        if (alpha_modes or {}).get(mkey) == "MASK":
            mat["alphaMode"] = "MASK"
            mat["alphaCutoff"] = 0.5
        elif (alpha_modes or {}).get(mkey) == "BLEND":
            mat["alphaMode"] = "BLEND"
        materials.append(mat)
        material_index[mkey] = len(materials) - 1

        prim = {"attributes": {"POSITION": len(accessors) - 4, "NORMAL": len(accessors) - 3,
                               "TEXCOORD_0": len(accessors) - 2},
                "indices": len(accessors) - 1, "material": material_index[mkey], "mode": 4}
        # store primitives by material order; a single mesh with several primitives
        mesh.setdefault("prims", []) if False else None
        g["prim"] = prim

    prims = [g["prim"] for g in mesh.groups.values() if "prim" in g and g["idx"]]

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "RealEarth2024 pipeline",
            "extensions": {"ASOBO_normal_map_convention": {"tangent_space_convention": "DirectX"}},
        },
        "extensionsUsed": ["ASOBO_normal_map_convention", "ASOBO_unique_id"],
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0,
                   "extensions": {"ASOBO_unique_id": {"id": name}}}],
        "meshes": [{"name": name, "primitives": prims}],
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob), "uri": f"{name}.bin"}],
    }
    if gltf_images:
        gltf["images"] = gltf_images
        gltf["textures"] = gltf_textures
        gltf["samplers"] = gltf_samplers

    (out_dir / f"{name}.bin").write_bytes(bytes(blob))
    path = out_dir / f"{name}.gltf"
    path.write_text(json.dumps(gltf, separators=(",", ":")), encoding="utf-8")
    return path


def box_mesh(mesh: MeshBuilder, material: str, cx, cy, cz, sx, sy, sz, uv_scale=1.0):
    """Axis-aligned box centred at (cx,cy,cz) with full sizes."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    x0, x1 = cx - hx, cx + hx
    y0, y1 = cy - hy, cy + hy
    z0, z1 = cz - hz, cz + hz
    # +X
    mesh.add_quad(material, (x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0))
    # -X
    mesh.add_quad(material, (x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1))
    # +Z
    mesh.add_quad(material, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    # -Z
    mesh.add_quad(material, (x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0))
    # +Y
    mesh.add_quad(material, (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))
    # -Y
    mesh.add_quad(material, (x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0))
