"""Optimise supplied 297k-vertex monument into four MSFS 2024 LODs.

Original photogrammetry geometry and 4K atlas remain untouched under source/.
Voxel/UV-aware reduction is a pragmatic visual LOD, not high-precision retopology.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

LEVELS = (
    ("LOD00", 0.05, 0.10, 20.0),
    ("LOD01", 0.10, 0.10, 6.0),
    ("LOD02", 0.20, 0.10, 2.0),
    ("LOD03", 0.40, 0.15, 0.1),
)


def _array(model, data: bytes, key: str, size: int):
    primitive = model["meshes"][0]["primitives"][0]
    idx = primitive["indices"] if key == "INDICES" else primitive["attributes"][key]
    accessor = model["accessors"][idx]
    view = model["bufferViews"][accessor["bufferView"]]
    dtype = {5126: "<f4", 5125: "<u4", 5123: "<u2"}[accessor["componentType"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    scalar_size = np.dtype(dtype).itemsize
    stride = view.get("byteStride", size * scalar_size)
    if stride == size * scalar_size:
        return np.frombuffer(data, dtype=dtype,
                             count=accessor["count"] * size,
                             offset=offset).reshape((-1, size))
    return np.ndarray((accessor["count"], size), dtype=np.dtype(dtype),
                      buffer=data, offset=offset, strides=(stride, scalar_size))


def _save(path: Path, template: dict, positions, normals, uvs, triangles):
    gltf = copy.deepcopy(template)
    model_name = path.stem
    gltf["asset"]["generator"] = "RealEarth2024 visibility-compatible statue LOD"
    gltf["asset"]["extensions"] = {
        "ASOBO_normal_map_convention": {"tangent_space_convention": "DirectX"}
    }
    gltf["extensionsUsed"] = ["ASOBO_unique_id", "ASOBO_normal_map_convention"]
    gltf["nodes"][0]["name"] = model_name
    gltf["nodes"][0].setdefault("extensions", {})["ASOBO_unique_id"] = {
        "id": model_name
    }
    gltf["meshes"][0]["name"] = model_name
    gltf["meshes"][0]["primitives"] = [{
        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
        "indices": 3, "material": 0, "mode": 4
    }]
    views, accessors = [], []
    blob = bytearray()
    chunks = (
        (np.asarray(positions, dtype="<f4").tobytes(), 34962),
        (np.asarray(normals, dtype="<f4").tobytes(), 34962),
        (np.asarray(uvs, dtype="<f4").tobytes(), 34962),
        (np.asarray(triangles.ravel(), dtype="<u4").tobytes(), 34963),
    )
    for i, (data, target) in enumerate(chunks):
        offset = len(blob)
        blob.extend(data)
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": offset,
                      "byteLength": len(data), "target": target})
        a = {"bufferView": i, "componentType": 5125 if i == 3 else 5126,
             "count": len(triangles) * 3 if i == 3 else len(positions),
             "type": ("VEC3", "VEC3", "VEC2", "SCALAR")[i]}
        if i == 0:
            a["min"] = positions.min(axis=0).astype(float).tolist()
            a["max"] = positions.max(axis=0).astype(float).tolist()
        accessors.append(a)
    gltf["bufferViews"], gltf["accessors"] = views, accessors
    gltf["buffers"] = [{"byteLength": len(blob), "uri": model_name + ".bin"}]
    (path.parent / (model_name + ".bin")).write_bytes(blob)
    path.write_text(json.dumps(gltf, separators=(",", ":")), encoding="utf-8")


def write_lods(model: dict, source_bin: Path, out_dir: Path):
    raw = source_bin.read_bytes()
    v = _array(model, raw, "POSITION", 3).astype("<f4", copy=False)
    n = _array(model, raw, "NORMAL", 3).astype("<f4", copy=False)
    uv = _array(model, raw, "TEXCOORD_0", 2).astype("<f4", copy=False)
    faces = _array(model, raw, "INDICES", 1).ravel().reshape(-1, 3)
    if len(v) != 297014 or len(faces) != 563947:
        raise ValueError(f"Unexpected photogrammetry size: {len(v)}, {len(faces)}")
    if np.any(faces >= len(v)) or not (np.isfinite(v).all() and np.isfinite(uv).all()):
        raise ValueError("Invalid 3D vertex/index data")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("monument_vierge*.gltf"):
        old.unlink()
    for old in out_dir.glob("monument_vierge*.bin"):
        old.unlink()
    levels = []
    for tag, voxel_m, uv_cell, minsize in LEVELS:
        # Keep UV islands independent: avoid joining unrelated photograph tiles.
        keys = np.hstack((np.rint(v / voxel_m).astype("<i4"),
                          np.floor(uv / uv_cell).astype("<i4")))
        _, inverse = np.unique(keys, axis=0, return_inverse=True)
        count = int(inverse.max()) + 1
        samples = np.bincount(inverse, minlength=count)
        pos = np.stack([np.bincount(inverse, weights=v[:, i], minlength=count)
                        / samples for i in range(3)], axis=1).astype("<f4")
        tex = np.stack([np.bincount(inverse, weights=uv[:, i], minlength=count)
                        / samples for i in range(2)], axis=1).astype("<f4")
        nor = np.stack([np.bincount(inverse, weights=n[:, i], minlength=count)
                        / samples for i in range(3)], axis=1).astype("<f4")
        magnitudes = np.linalg.norm(nor, axis=1)
        nor[magnitudes > 1e-6] /= magnitudes[magnitudes > 1e-6, None]
        nor[magnitudes <= 1e-6] = (0, 1, 0)
        tri = inverse[faces]
        tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2])
                  & (tri[:, 0] != tri[:, 2])]
        area2 = np.linalg.norm(np.cross(
            pos[tri[:, 1]] - pos[tri[:, 0]],
            pos[tri[:, 2]] - pos[tri[:, 0]]), axis=1)
        tri = tri[area2 > 1e-7]
        _, indices = np.unique(np.sort(tri, axis=1), axis=0, return_index=True)
        tri = tri[np.sort(indices)]
        if len(pos) > 70000 or len(tri) < 200:
            raise ValueError(f"Bad LOD vertex/triangle budget: {tag}")
        filename = f"monument_vierge_{tag}.gltf"
        _save(out_dir / filename, model, pos, nor, tex, tri)
        levels.append({"name": tag, "gltf": filename,
                       "vertices": len(pos), "triangles": len(tri),
                       "minSize": minsize})
        print(f"{tag}: {len(pos)} vertices, {len(tri)} triangles")
    return levels
