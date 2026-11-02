"""Offline round-trip test of glTF KHR_mesh_quantization -> MSFS native glTF."""
from __future__ import annotations
import json
import struct
import tempfile
from pathlib import Path

import numpy as np

from ski_assets import convert_glb

def make_fixture(path: Path):
    # A 4x4 quantized vertex grid -> 18 non-degenerate triangles.
    # The converter deliberately rejects tiny meshes with fewer than ten
    # triangles, so the regression fixture must exercise the REAL success
    # path rather than being rejected by the converter's size guard.
    pos = np.array(
        [[x * 100, (x + z) * 5, z * 100]
         for z in range(4) for x in range(4)],
        dtype="<u2",
    )
    faces = []
    for z in range(3):
        for x in range(3):
            i = z * 4 + x
            faces.extend([(i, i + 1, i + 4),
                          (i + 1, i + 5, i + 4)])
    idx = np.asarray(faces, dtype="<u2").ravel()
    binary = pos.tobytes() + idx.tobytes()
    doc = {
        "asset":{"version":"2.0"},
        "extensionsUsed":["KHR_mesh_quantization"],
        "extensionsRequired":["KHR_mesh_quantization"],
        "scene":0, "scenes":[{"nodes":[0]}],
        "nodes":[{"mesh":0, "scale":[0.01,0.01,0.01]}],
        "meshes":[{"primitives":[{
            "attributes":{"POSITION":0}, "indices":1, "material":0,
            "mode":4
        }]}],
        "materials":[{"pbrMetallicRoughness":{
            "baseColorFactor":[0.5,0.2,0.1,1.0],
            "roughnessFactor":0.8,"metallicFactor":0.0
        }}],
        "accessors":[
            {"bufferView":0,"componentType":5123,"count":len(pos),"type":"VEC3"},
            {"bufferView":1,"componentType":5123,"count":len(idx),"type":"SCALAR"}
        ],
        "bufferViews":[
            {"buffer":0,"byteOffset":0,"byteLength":len(pos.tobytes())},
            {"buffer":0,"byteOffset":len(pos.tobytes()),"byteLength":len(idx.tobytes())}
        ],
        "buffers":[{"byteLength":len(binary)}]
    }
    json_bytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    binary += b"\x00" * ((-len(binary)) % 4)
    length = 12 + 8 + len(json_bytes) + 8 + len(binary)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, length)
                     + struct.pack("<I4s", len(json_bytes), b"JSON")
                     + json_bytes
                     + struct.pack("<I4s", len(binary), b"BIN\x00")
                     + binary)

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src = root / "sample.glb"
        make_fixture(src)
        stats = convert_glb(src, root, "ski_test_fixture")
        assert stats["triangles"] == 18, stats
        result = json.loads((root / "ski_test_fixture.gltf").read_text())
        assert result["asset"]["version"] == "2.0"
        # A proper quantized source with node scale must turn into floats
        # and retain its transformed dimensions (300*0.01 = 3 metres).
        bounds = result["accessors"][0]
        assert bounds["min"] == [0.0, 0.0, 0.0], bounds
        assert all(abs(a - b) < 1e-5 for a, b in zip(
            bounds["max"], [3.0, 0.3, 3.0]
        )), bounds

        assert "KHR_mesh_quantization" not in result.get("extensionsUsed", [])
        assert result["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"] == [
            0.5, 0.2, 0.1, 1.0
        ]
        assert result["accessors"][0]["componentType"] == 5126
        assert result["buffers"][0]["byteLength"] == (
            root / "ski_test_fixture.bin"
        ).stat().st_size
        assert "texture" not in str(result).lower()
        assert (root / "ski_test_fixture.xml").is_file()
    print("CC0 GLB CONVERTER QA: OK (quantized vertices, PBR color, native glTF)")

if __name__ == "__main__":
    main()
