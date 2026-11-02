"""Convert selected CC0 alpine/ski GLBs to uncompressed MSFS2024 glTF ModelLib.

Source packs: 3dassets.dev, CC0 1.0, AI-assisted stylised geometry.
These are NOT photogrammetry and must not be described as exact buildings.

API and GLB downloads are fetched only once and cached in build/ski_assets.
No Blender or extra pip packages required beyond the project's numpy.
The source packs are glTF with KHR_mesh_quantization: accessors and node
transforms MUST be expanded before feeding Microsoft SDK (not copied raw).
"""
from __future__ import annotations

import json
import math
import os
import re
import struct
import time
import urllib.request
from pathlib import Path

import numpy as np

from config import ROOT, model_guid
from fsgltf import MeshBuilder, write_gltf

CACHE = ROOT / "build" / "ski_assets"
PACKS = {
    "alpine-snow-village": (
        "Chalet Evergreen",
        "Mountain Guesthouse",
        "Alpine Bakery",
        "Carved Village Bench",
        "Mountain Wayfinding Post",
        "Seven Bay Ski Rack",
        "Twin Lantern Streetlight",
    ),
    "ski-resort-and-snow-park": (
        "Lift Bottom Station",
        "Lift Top Station",
        "Chairlift Tower",
        "Gondola Tower",
        "Chairlift Chair 4 Seat",
        "Gondola Cabin",
        "Lodge Hall",
        "Rental Shop Front",
        "Ticket Office",
        "Snow Groomer",
        "Snowmobile",
        "Snowmaking Gun",
        "Trail Sign Post",
        "Piste Marker Pole",
        "Snow Fence",
        "Ski Rack",
    ),
}
MAX_GLB = 3_000_000
UINTS = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4"}
DTYPES = {**UINTS, 5126: "<f4"}
SHAPE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
RUNTIME_PREFIX = "ski"


def get_bytes(url: str, max_size: int = MAX_GLB) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("Refusing insecure asset URL")
    req = urllib.request.Request(url, headers={"User-Agent": "RealEarth2024/0.1.5 (CC0 assets)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                if not response.url.startswith("https://"):
                    raise ValueError("Remote server redirected to insecure URL")
                data = response.read(max_size + 1)
            if len(data) > max_size:
                raise ValueError(f"Asset over size budget: {url}")
            return data
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError("unreachable")


def get_manifest(pack: str) -> dict:
    cached = CACHE / f"{pack}.json"
    if cached.is_file():
        obj = json.loads(cached.read_text(encoding="utf-8"))
    else:
        blob = get_bytes(f"https://3dassets.dev/api/v1/packs/{pack}", 6_000_000)
        obj = json.loads(blob)
        if not isinstance(obj, dict) or not isinstance(obj.get("data"), dict):
            raise ValueError("Unexpected pack API schema")
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    manifest = obj["data"]
    if manifest.get("slug") != pack or manifest.get("licenseLabel") != "CC0 1.0 Universal":
        raise ValueError(f"Unsupported license or pack identity for {pack}")
    if not isinstance(manifest.get("assets"), list) or len(manifest["assets"]) < 20:
        raise ValueError(f"Pack manifest is missing assets: {pack}")
    return manifest


def source_assets() -> dict[str, dict]:
    """Resolve explicitly curated pack titles to their immutable CDN GLBs."""
    selected = {}
    for pack, names in PACKS.items():
        manifest = get_manifest(pack)
        all_models = manifest["assets"]
        for name in names:
            candidates = [a for a in all_models
                          if a["title"].split(" (", 1)[0] == name]
            if not candidates:
                if name == "Ski Rack":
                    # Alpine pack already carries a seven-bay ski rack.
                    continue
                raise ValueError(f"Missing '{name}' from {pack}; no substitution")
            model = candidates[0]
            license_data = model.get("license") or {}
            if license_data.get("slug") != "cc0-1.0":
                raise ValueError("Asset license no longer CC0: " + name)
            url = str(model.get("cdnUrl", ""))
            if not url.startswith("https://cdn.3dassets.dev/assets/") or not url.endswith("/model.glb"):
                raise ValueError("Unexpected asset CDN URL for " + name)
            if (model.get("stats") or {}).get("textures", 0) != 0:
                raise ValueError("Nonzero textures: requires explicit texture conversion: " + name)
            ident = f"ski_{model['id']}"
            selected[name] = {"key": ident, "title": model["title"],
                              "source": pack, "url": url,
                              "triangles": (model.get("stats") or {}).get("triangles", 0)}
    if len(selected) < 18:
        raise ValueError("Too few validated resort models")
    return selected


def load_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    if len(data) < 28:
        raise ValueError(f"Truncated GLB: {path}")
    magic, ver, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or ver != 2 or length != len(data):
        raise ValueError("Bad GLB header")
    pos = 12
    chunks = {}
    while pos < length:
        clen, ctype = struct.unpack_from("<I4s", data, pos)
        pos += 8
        if pos + clen > length:
            raise ValueError("Invalid GLB chunk length")
        chunks[ctype] = data[pos:pos+clen]
        pos += clen
    doc = json.loads(chunks[b"JSON"].rstrip(b"\x00 \t\n"))
    raw = chunks[b"BIN\x00"]
    exts = set(doc.get("extensionsRequired", []))
    if exts - {"KHR_mesh_quantization"}:
        raise ValueError("Unsupported GLB compression/extensions: " + repr(exts))
    if doc.get("images") or doc.get("textures"):
        raise ValueError("External material textures need an explicit PNG pass")
    if doc.get("skins") or doc.get("animations"):
        raise ValueError("Animated/rigged meshes not supported")
    return doc, raw


def accessor(doc: dict, raw: bytes, idx: int) -> np.ndarray:
    a = doc["accessors"][idx]
    if "sparse" in a:
        raise ValueError("Sparse glTF accessors not supported")
    n = SHAPE[a["type"]]
    dtype = np.dtype(DTYPES[a["componentType"]])
    count = int(a["count"])
    bv = doc["bufferViews"][a["bufferView"]]
    if bv.get("buffer", 0) != 0:
        raise ValueError("Multiple GLB buffers not supported")
    offset = int(bv.get("byteOffset", 0)) + int(a.get("byteOffset", 0))
    stride = int(bv.get("byteStride", n * dtype.itemsize))
    if offset + stride * (count - 1) + n * dtype.itemsize > len(raw):
        raise ValueError("glTF accessor exceeds BIN chunk")
    if stride == n * dtype.itemsize:
        arr = np.frombuffer(raw, dtype=dtype, count=count * n, offset=offset).reshape((count, n))
    else:
        arr = np.ndarray(shape=(count, n), dtype=dtype, buffer=raw,
                         offset=offset, strides=(stride, dtype.itemsize))
    if a.get("normalized", False) and dtype.kind in "iu":
        bits = dtype.itemsize * 8
        if dtype.kind == "i":
            arr = np.maximum(arr.astype("f8") / (2 ** (bits-1) - 1), -1.0)
        else:
            arr = arr.astype("f8") / (2 ** bits - 1)
    return np.asarray(arr)


def node_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.asarray(node["matrix"], dtype="f8").reshape((4, 4), order="F")
    t = np.asarray(node.get("translation", [0, 0, 0]), dtype="f8")
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    scale = np.asarray(node.get("scale", [1, 1, 1]), dtype="f8")
    r = np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]
    ], dtype="f8")
    m = np.eye(4, dtype="f8")
    m[:3, :3] = r * scale[None, :]
    m[:3, 3] = t
    return m


def convert_glb(path: Path, dst: Path, key: str) -> dict:
    doc, raw = load_glb(path)
    mesh = MeshBuilder()
    factors: dict[str, list[float]] = {}
    rough: dict[str, float] = {}
    metallic: dict[str, float] = {}
    total = 0

    def walk(node_idx: int, parent: np.ndarray):
        nonlocal total
        node = doc["nodes"][node_idx]
        world = parent @ node_matrix(node)
        if "mesh" in node:
            for prim in doc["meshes"][node["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4:
                    raise ValueError("Only triangle primitives are supported")
                if "POSITION" not in prim["attributes"]:
                    raise ValueError("No glTF POSITION stream")
                pos = accessor(doc, raw, prim["attributes"]["POSITION"])
                if pos.shape[1] != 3:
                    raise ValueError("Bad POSITION stream")
                if "indices" in prim:
                    ids = accessor(doc, raw, prim["indices"]).reshape(-1)
                else:
                    ids = np.arange(len(pos))
                if len(ids) % 3 or np.max(ids) >= len(pos):
                    raise ValueError("Bad triangle indices")
                p = np.column_stack((pos, np.ones(len(pos)))) @ world.T
                p = p[:, :3]
                if not np.isfinite(p).all():
                    raise ValueError("Nonfinite vertex coordinates")
                if abs(np.linalg.det(world[:3, :3])) < 1e-8:
                    raise ValueError("Singular mesh transform")
                material_id = int(prim.get("material", 0))
                original = doc.get("materials", [])
                mat = original[material_id] if material_id < len(original) else {}
                pbr = mat.get("pbrMetallicRoughness", {})
                if pbr.get("baseColorTexture") or mat.get("normalTexture"):
                    raise ValueError("Unexpected textured GLB material")
                slot = f"{key}_mat_{material_id}"
                factors[slot] = list(pbr.get("baseColorFactor", [1, 1, 1, 1]))
                rough[slot] = float(pbr.get("roughnessFactor", 0.85))
                metallic[slot] = float(pbr.get("metallicFactor", 0))
                triangles = ids.reshape(-1, 3)
                if np.linalg.det(world[:3, :3]) < 0:
                    triangles = triangles[:, [0, 2, 1]]
                if total + len(triangles) > 30_000:
                    raise ValueError("Model exceeds 30k triangle budget")
                for a, b, c in triangles:
                    # The source 3dassets geometry is deliberately low-poly
                    # with color-only PBR; compute robust flat face normals.
                    mesh.add_triangle(slot, p[a], p[b], p[c])
                total += len(triangles)
        for child in node.get("children", []):
            walk(child, world)

    scene_index = int(doc.get("scene", 0))
    scenes = doc.get("scenes", [])
    if not scenes:
        raise ValueError("No glTF scene")
    for node_id in scenes[scene_index].get("nodes", []):
        walk(node_id, np.eye(4))
    if mesh.triangle_count() < 10:
        raise ValueError("Imported GLB has no usable triangles")
    output = write_gltf(dst, key, mesh, {}, base_color_factors=factors,
                        roughness=rough, metallic=metallic, use_textures=False)
    check = json.loads(output.read_text(encoding="utf-8"))
    if check.get("images") or check.get("textures"):
        raise ValueError("Unexpected runtime texture dependencies")
    if any(v["count"] > 70_000 for v in check["accessors"] if v["type"] == "VEC3"):
        raise ValueError("Too many vertices for one MSFS LOD")
    (dst / f"{key}.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<ModelInfo guid="{model_guid(key)}" version="1.1">\n'
        f' <LODS><LOD minSize="0" ModelFile="{key}.gltf"/></LODS>\n'
        '</ModelInfo>\n', encoding="utf-8")
    return {"triangles": mesh.triangle_count(),
            "materials": len(check["materials"]), "model": key}


def build_assets(out_dir: Path) -> dict[str, dict]:
    selected = source_assets()
    outputs = {}
    for title, spec in selected.items():
        item = CACHE / (spec["key"] + ".glb")
        if not item.is_file():
            CACHE.mkdir(parents=True, exist_ok=True)
            data = get_bytes(spec["url"])
            if data[:4] != b"glTF":
                raise ValueError("Downloaded content is not GLB: " + title)
            temp = item.with_suffix(".part")
            temp.write_bytes(data)
            temp.replace(item)
        else:
            if item.stat().st_size > MAX_GLB:
                raise ValueError("Cached GLB exceeds limit: " + str(item))
        converted = convert_glb(item, out_dir, spec["key"])
        outputs[title] = {**spec, **converted}
        print("CC0 GLB:", title, converted["triangles"], "triangles")
    if len(outputs) < 18:
        raise RuntimeError("Missing CC0 ski models. No partial scenery will be built.")
    return outputs


if __name__ == "__main__":
    from config import MODEL_SRC
    data = build_assets(MODEL_SRC)
    print("converted", len(data), "models")
